from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import binascii
import hashlib
import json
import os
from pathlib import Path

from treeforge.android.toolchain.host_tools import AndroidHostTools
import shutil
import struct
import subprocess
import time

from treeforge.android.host_tools import (
    treeforge_adb_executable,
)
from treeforge.android.repartition.planning import (
    RepartitionError,
    RepartitionPlan,
)


_NATIVE_BLOCK = 4096
_EXPECTED_DISK_LBAS = 31_196_160
_STOCK_SUPER_BYTES = 8_531_214_336


@dataclass(frozen=True, slots=True)
class FormatterPreflight:
    userdata_fs: str
    metadata_fs: str
    fstab_path: str
    path: str
    helpers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GptSnapshot:
    primary: bytes
    backup: bytes
    block_size: int
    disk_lbas: int
    backup_start_lba: int
    primary_header: dict[str, object]
    backup_header: dict[str, object]
    entries: bytes


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_header(
    raw: bytes,
    *,
    label: str,
) -> dict[str, object]:
    if raw[:8] != b"EFI PART":
        raise RepartitionError(
            f"{label}: GPT signature missing"
        )

    (
        _signature,
        revision,
        header_size,
        stored_crc,
        _reserved,
        current_lba,
        alternate_lba,
        first_usable,
        last_usable,
        disk_guid,
        entries_lba,
        entry_count,
        entry_size,
        entries_crc,
    ) = struct.unpack_from(
        "<8sIIIIQQQQ16sQIII",
        raw,
        0,
    )

    check = bytearray(
        raw[:header_size]
    )
    struct.pack_into(
        "<I",
        check,
        16,
        0,
    )

    calculated = (
        binascii.crc32(check)
        & 0xFFFFFFFF
    )

    if calculated != stored_crc:
        raise RepartitionError(
            f"{label}: GPT header CRC mismatch"
        )

    return {
        "revision": revision,
        "header_size": header_size,
        "current_lba": current_lba,
        "alternate_lba": alternate_lba,
        "first_usable": first_usable,
        "last_usable": last_usable,
        "disk_guid": disk_guid,
        "entries_lba": entries_lba,
        "entry_count": entry_count,
        "entry_size": entry_size,
        "entries_crc": entries_crc,
    }


def _snapshot_from_regions(
    *,
    primary: bytes,
    backup: bytes,
    block_size: int,
    disk_lbas: int,
    backup_start_lba: int,
) -> GptSnapshot:
    primary_header = _parse_header(
        primary[
            block_size:
            block_size * 2
        ],
        label="primary",
    )

    backup_header_lba = int(
        primary_header["alternate_lba"]
    )

    backup_header_offset = (
        (
            backup_header_lba
            - backup_start_lba
        )
        * block_size
    )

    backup_header = _parse_header(
        backup[
            backup_header_offset:
            backup_header_offset
            + block_size
        ],
        label="backup",
    )

    if int(
        primary_header["current_lba"]
    ) != 1:
        raise RepartitionError(
            "Primary GPT header is not at LBA 1."
        )

    if int(
        primary_header["alternate_lba"]
    ) != disk_lbas - 1:
        raise RepartitionError(
            "Primary GPT alternate-LBA mismatch."
        )

    if int(
        backup_header["current_lba"]
    ) != disk_lbas - 1:
        raise RepartitionError(
            "Backup GPT header location mismatch."
        )

    if int(
        backup_header["alternate_lba"]
    ) != 1:
        raise RepartitionError(
            "Backup GPT alternate-LBA mismatch."
        )

    if (
        primary_header["entry_count"]
        != backup_header["entry_count"]
        or primary_header["entry_size"]
        != backup_header["entry_size"]
    ):
        raise RepartitionError(
            "Primary/backup GPT entry geometry differs."
        )

    entry_count = int(
        primary_header["entry_count"]
    )
    entry_size = int(
        primary_header["entry_size"]
    )
    entry_bytes = (
        entry_count
        * entry_size
    )

    primary_entry_offset = (
        int(
            primary_header["entries_lba"]
        )
        * block_size
    )

    backup_entry_offset = (
        (
            int(
                backup_header["entries_lba"]
            )
            - backup_start_lba
        )
        * block_size
    )

    primary_entries = primary[
        primary_entry_offset:
        primary_entry_offset
        + entry_bytes
    ]

    backup_entries = backup[
        backup_entry_offset:
        backup_entry_offset
        + entry_bytes
    ]

    if (
        len(primary_entries) != entry_bytes
        or len(backup_entries) != entry_bytes
    ):
        raise RepartitionError(
            "GPT partition array is truncated."
        )

    primary_crc = (
        binascii.crc32(
            primary_entries
        )
        & 0xFFFFFFFF
    )

    backup_crc = (
        binascii.crc32(
            backup_entries
        )
        & 0xFFFFFFFF
    )

    if primary_crc != int(
        primary_header["entries_crc"]
    ):
        raise RepartitionError(
            "Primary GPT partition-array CRC mismatch."
        )

    if backup_crc != int(
        backup_header["entries_crc"]
    ):
        raise RepartitionError(
            "Backup GPT partition-array CRC mismatch."
        )

    if primary_entries != backup_entries:
        raise RepartitionError(
            "Primary/backup GPT arrays differ."
        )

    if (
        primary_header["disk_guid"]
        != backup_header["disk_guid"]
    ):
        raise RepartitionError(
            "Primary/backup GPT disk GUID differs."
        )

    return GptSnapshot(
        primary=primary,
        backup=backup,
        block_size=block_size,
        disk_lbas=disk_lbas,
        backup_start_lba=backup_start_lba,
        primary_header=primary_header,
        backup_header=backup_header,
        entries=primary_entries,
    )


def _entry(
    snapshot: GptSnapshot,
    number: int,
) -> dict[str, object]:
    entry_size = int(
        snapshot.primary_header[
            "entry_size"
        ]
    )

    offset = (
        (number - 1)
        * entry_size
    )

    raw = snapshot.entries[
        offset:
        offset + entry_size
    ]

    first_lba, last_lba, attrs = (
        struct.unpack_from(
            "<QQQ",
            raw,
            32,
        )
    )

    name = (
        raw[56:128]
        .decode(
            "utf-16le"
        )
        .split(
            "\x00",
            1,
        )[0]
    )

    return {
        "number": number,
        "name": name,
        "first_lba": first_lba,
        "last_lba": last_lba,
        "attrs": attrs,
        "raw": raw,
    }


def _kernel_sector_to_lba(
    value: int,
    *,
    block_size: int,
) -> int:
    byte_offset = (
        value * 512
    )

    if (
        byte_offset
        % block_size
        != 0
    ):
        raise RepartitionError(
            "TreeForge geometry is not aligned "
            "to the device logical block size."
        )

    return (
        byte_offset
        // block_size
    )


def _validate_plan_geometry(
    snapshot: GptSnapshot,
    plan: RepartitionPlan,
    *,
    target: bool,
) -> None:
    if snapshot.block_size != _NATIVE_BLOCK:
        raise RepartitionError(
            "Unexpected logical block size."
        )

    if snapshot.disk_lbas != _EXPECTED_DISK_LBAS:
        raise RepartitionError(
            "Unexpected tangorpro disk size."
        )

    ph = snapshot.primary_header

    if (
        int(ph["first_usable"]) != 6
        or int(ph["last_usable"]) != 31_196_154
        or int(ph["entry_count"]) != 26
        or int(ph["entry_size"]) != 128
    ):
        raise RepartitionError(
            "Unsupported tangorpro GPT structure."
        )

    super_part = _entry(
        snapshot,
        25,
    )
    userdata_part = _entry(
        snapshot,
        26,
    )

    if super_part["name"] != "super":
        raise RepartitionError(
            "GPT entry 25 is not super."
        )

    if userdata_part["name"] != "userdata":
        raise RepartitionError(
            "GPT entry 26 is not userdata."
        )

    if target:
        super_start = (
            plan.new_super_start_sector
        )
        super_end = (
            plan.new_super_end_sector
        )
        userdata_start = (
            plan.new_userdata_start_sector
        )
        userdata_end = (
            plan.new_userdata_end_sector
        )
    else:
        super_start = (
            plan.current_super_start_sector
        )
        super_end = (
            plan.current_super_end_sector
        )
        userdata_start = (
            plan.current_userdata_start_sector
        )
        userdata_end = (
            plan.current_userdata_end_sector
        )

    expected_super_first = (
        _kernel_sector_to_lba(
            super_start,
            block_size=snapshot.block_size,
        )
    )

    expected_super_last = (
        _kernel_sector_to_lba(
            super_end,
            block_size=snapshot.block_size,
        )
        - 1
    )

    expected_userdata_first = (
        _kernel_sector_to_lba(
            userdata_start,
            block_size=snapshot.block_size,
        )
    )

    expected_userdata_last = (
        _kernel_sector_to_lba(
            userdata_end,
            block_size=snapshot.block_size,
        )
        - 1
    )

    actual = (
        int(super_part["first_lba"]),
        int(super_part["last_lba"]),
        int(userdata_part["first_lba"]),
        int(userdata_part["last_lba"]),
    )

    expected = (
        expected_super_first,
        expected_super_last,
        expected_userdata_first,
        expected_userdata_last,
    )

    if actual != expected:
        raise RepartitionError(
            "Live GPT geometry does not match "
            f"the {'target' if target else 'source'} "
            f"TreeForge plan: actual={actual}, "
            f"expected={expected}"
        )


def _update_header_crc(
    region: bytearray,
    *,
    header_offset: int,
    entries_crc: int,
) -> None:
    header_size = struct.unpack_from(
        "<I",
        region,
        header_offset + 12,
    )[0]

    struct.pack_into(
        "<I",
        region,
        header_offset + 88,
        entries_crc,
    )

    struct.pack_into(
        "<I",
        region,
        header_offset + 16,
        0,
    )

    header = bytes(
        region[
            header_offset:
            header_offset
            + header_size
        ]
    )

    crc = (
        binascii.crc32(header)
        & 0xFFFFFFFF
    )

    struct.pack_into(
        "<I",
        region,
        header_offset + 16,
        crc,
    )


def _build_target_regions(
    snapshot: GptSnapshot,
    plan: RepartitionPlan,
) -> tuple[
    bytes,
    bytes,
]:
    primary = bytearray(
        snapshot.primary
    )
    backup = bytearray(
        snapshot.backup
    )

    entry_size = int(
        snapshot.primary_header[
            "entry_size"
        ]
    )
    entry_count = int(
        snapshot.primary_header[
            "entry_count"
        ]
    )
    entry_bytes = (
        entry_count
        * entry_size
    )

    primary_entries_offset = (
        int(
            snapshot.primary_header[
                "entries_lba"
            ]
        )
        * snapshot.block_size
    )

    backup_entries_offset = (
        (
            int(
                snapshot.backup_header[
                    "entries_lba"
                ]
            )
            - snapshot.backup_start_lba
        )
        * snapshot.block_size
    )

    target_super_last = (
        _kernel_sector_to_lba(
            plan.new_super_end_sector,
            block_size=snapshot.block_size,
        )
        - 1
    )

    target_userdata_first = (
        _kernel_sector_to_lba(
            plan.new_userdata_start_sector,
            block_size=snapshot.block_size,
        )
    )

    def patch(
        region: bytearray,
        entries_offset: int,
    ) -> int:
        super_offset = (
            entries_offset
            + (25 - 1) * entry_size
        )

        userdata_offset = (
            entries_offset
            + (26 - 1) * entry_size
        )

        struct.pack_into(
            "<Q",
            region,
            super_offset + 40,
            target_super_last,
        )

        struct.pack_into(
            "<Q",
            region,
            userdata_offset + 32,
            target_userdata_first,
        )

        entries = bytes(
            region[
                entries_offset:
                entries_offset
                + entry_bytes
            ]
        )

        return (
            binascii.crc32(entries)
            & 0xFFFFFFFF
        )

    primary_entries_crc = patch(
        primary,
        primary_entries_offset,
    )

    backup_entries_crc = patch(
        backup,
        backup_entries_offset,
    )

    if (
        primary_entries_crc
        != backup_entries_crc
    ):
        raise RepartitionError(
            "Generated GPT arrays have "
            "different CRCs."
        )

    _update_header_crc(
        primary,
        header_offset=snapshot.block_size,
        entries_crc=primary_entries_crc,
    )

    backup_header_offset = (
        (
            snapshot.disk_lbas
            - 1
            - snapshot.backup_start_lba
        )
        * snapshot.block_size
    )

    _update_header_crc(
        backup,
        header_offset=backup_header_offset,
        entries_crc=backup_entries_crc,
    )

    proposed = _snapshot_from_regions(
        primary=bytes(primary),
        backup=bytes(backup),
        block_size=snapshot.block_size,
        disk_lbas=snapshot.disk_lbas,
        backup_start_lba=snapshot.backup_start_lba,
    )

    _validate_plan_geometry(
        proposed,
        plan,
        target=True,
    )

    #
    # Entries 1-24 must stay byte-identical.
    #
    for number in range(
        1,
        25,
    ):
        if (
            _entry(
                snapshot,
                number,
            )["raw"]
            != _entry(
                proposed,
                number,
            )["raw"]
        ):
            raise RepartitionError(
                f"GPT entry {number} changed "
                "unexpectedly."
            )

    return (
        proposed.primary,
        proposed.backup,
    )


class TangorproRepartitionExecutor:
    def __init__(
        self,
        *,
        repository_root: Path,
        fastboot: str,
    ) -> None:
        self.repository_root = (
            repository_root.resolve()
        )

        self.fastboot = fastboot
        self.adb = str(
            treeforge_adb_executable()
        )

        self.output_root = (
            self.repository_root
            / "output"
            / "repartition"
        )

        self.output_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.state_path = (
            self.output_root
            / "repartition-state.json"
        )

        self.boot_image = (
            self.repository_root
            / "aosp"
            / "out"
            / "target"
            / "product"
            / "tangorpro"
            / "boot.img"
        )

    def _fastboot_getvar(
        self,
        key: str,
    ) -> str:
        completed = subprocess.run(
            [
                self.fastboot,
                "getvar",
                key,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        combined = "\n".join(
            value
            for value in (
                completed.stdout,
                completed.stderr,
            )
            if value
        )

        if completed.returncode != 0:
            raise RepartitionError(
                f"fastboot getvar {key} failed: "
                f"{combined.strip()}"
            )

        prefix = f"{key}:"

        for raw in combined.splitlines():
            line = raw.strip()

            if line.startswith(prefix):
                return (
                    line[
                        len(prefix):
                    ]
                    .strip()
                )

            bootloader_prefix = (
                f"(bootloader) {prefix}"
            )

            if line.startswith(
                bootloader_prefix
            ):
                return (
                    line[
                        len(
                            bootloader_prefix
                        ):
                    ]
                    .strip()
                )

        raise RepartitionError(
            f"fastboot did not report {key}"
        )

    def preflight_formatters(
        self,
    ) -> FormatterPreflight:
        if not self.boot_image.is_file():
            raise RepartitionError(
                "Known-good tangorpro AOSP boot.img "
                f"is unavailable: {self.boot_image}"
            )

        #
        # Pixel bootloader fastboot reports these physical
        # partitions as "raw". The Android filesystem
        # contract comes from the tangorpro/gs201 fstab.
        #
        fstab_candidates = [
            (
                self.repository_root
                / "aosp"
                / "device"
                / "google"
                / "gs201"
                / "conf"
                / "fstab.gs201.in"
            ),
            (
                self.repository_root
                / "aosp"
                / "out"
                / "target"
                / "product"
                / "tangorpro"
                / "vendor"
                / "etc"
                / "fstab.gs201"
            ),
        ]

        fstab_path: Path | None = None
        userdata_fs: str | None = None
        metadata_fs: str | None = None

        for candidate in fstab_candidates:
            if not candidate.is_file():
                continue

            candidate_userdata: str | None = None
            candidate_metadata: str | None = None

            for raw in candidate.read_text(
                encoding="utf-8",
                errors="strict",
            ).splitlines():
                line = raw.strip()

                if (
                    not line
                    or line.startswith("#")
                ):
                    continue

                fields = line.split()

                if len(fields) < 3:
                    continue

                source = fields[0]
                mount_point = fields[1]
                fs_type = fields[2].lower()

                if mount_point == "/data":
                    if not source.endswith(
                        "/by-name/userdata"
                    ):
                        raise RepartitionError(
                            "Tangorpro /data fstab entry "
                            "does not reference userdata."
                        )

                    candidate_userdata = fs_type

                elif mount_point == "/metadata":
                    if not source.endswith(
                        "/by-name/metadata"
                    ):
                        raise RepartitionError(
                            "Tangorpro /metadata fstab entry "
                            "does not reference metadata."
                        )

                    candidate_metadata = fs_type

            if (
                candidate_userdata
                and candidate_metadata
            ):
                fstab_path = candidate
                userdata_fs = candidate_userdata
                metadata_fs = candidate_metadata
                break

        if (
            fstab_path is None
            or userdata_fs is None
            or metadata_fs is None
        ):
            raise RepartitionError(
                "Unable to resolve tangorpro userdata/"
                "metadata filesystem types from AOSP fstab."
            )

        #
        # This profile is intentionally exact rather than
        # accepting arbitrary filesystem changes.
        #
        if userdata_fs != "f2fs":
            raise RepartitionError(
                "Tangorpro /data filesystem is "
                f"{userdata_fs!r}; expected 'f2fs'."
            )

        if metadata_fs != "f2fs":
            raise RepartitionError(
                "Tangorpro /metadata filesystem is "
                f"{metadata_fs!r}; expected 'f2fs'."
            )

        make_f2fs = Path(
            AndroidHostTools().make_f2fs
        ).resolve()

        path_dirs = {
            str(
                Path(
                    self.fastboot
                ).resolve().parent
            ),
            str(
                make_f2fs.parent
            ),
        }

        formatter_path = (
            os.pathsep.join(
                sorted(
                    path_dirs
                )
            )
            + os.pathsep
            + os.environ.get(
                "PATH",
                "",
            )
        )

        return FormatterPreflight(
            userdata_fs=userdata_fs,
            metadata_fs=metadata_fs,
            fstab_path=str(
                fstab_path.resolve()
            ),
            path=formatter_path,
            helpers=(
                str(
                    make_f2fs
                ),
            ),
        )

    def _adb_shell(
        self,
        command: str,
        *,
        check: bool = True,
    ) -> str:
        completed = subprocess.run(
            [
                self.adb,
                "shell",
                command,
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if (
            check
            and completed.returncode != 0
        ):
            raise RepartitionError(
                "ADB shell command failed: "
                f"{command}\n"
                f"{completed.stderr.strip()}"
            )

        return completed.stdout.strip()

    def _adb_exec_out(
        self,
        command: str,
    ) -> bytes:
        completed = subprocess.run(
            [
                self.adb,
                "exec-out",
                command,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode != 0:
            raise RepartitionError(
                "ADB raw read failed: "
                + completed.stderr.decode(
                    errors="replace"
                ).strip()
            )

        return completed.stdout

    def _temporary_boot(
        self,
    ) -> None:
        completed = subprocess.run(
            [
                self.fastboot,
                "boot",
                str(
                    self.boot_image
                ),
            ],
            check=False,
        )

        if completed.returncode != 0:
            raise RepartitionError(
                "Unable to temporary-boot "
                "the known-good AOSP boot.img."
            )

        subprocess.run(
            [
                self.adb,
                "wait-for-device",
            ],
            check=True,
        )

        subprocess.run(
            [
                self.adb,
                "root",
            ],
            check=True,
        )

        subprocess.run(
            [
                self.adb,
                "wait-for-device",
            ],
            check=True,
        )

        if (
            self._adb_shell(
                "getprop ro.product.device"
            )
            != "tangorpro"
        ):
            raise RepartitionError(
                "Temporary runtime is not tangorpro."
            )

        if (
            self._adb_shell(
                "cat /sys/class/block/sda/"
                "queue/logical_block_size"
            )
            != "4096"
        ):
            raise RepartitionError(
                "Unexpected /dev/block/sda "
                "logical block size."
            )

    def _read_region(
        self,
        *,
        start_lba: int,
        count: int,
    ) -> bytes:
        return self._adb_exec_out(
            "dd if=/dev/block/sda "
            f"bs={_NATIVE_BLOCK} "
            f"skip={start_lba} "
            f"count={count} "
            "2>/dev/null"
        )

    def _capture_gpt(
        self,
    ) -> GptSnapshot:
        kernel_sectors = int(
            self._adb_shell(
                "cat /sys/class/block/sda/size"
            )
        )

        disk_bytes = (
            kernel_sectors
            * 512
        )

        if (
            disk_bytes
            % _NATIVE_BLOCK
        ):
            raise RepartitionError(
                "Disk size is not native-LBA aligned."
            )

        disk_lbas = (
            disk_bytes
            // _NATIVE_BLOCK
        )

        if (
            disk_lbas
            != _EXPECTED_DISK_LBAS
        ):
            raise RepartitionError(
                "Unexpected tangorpro disk size."
            )

        prefix = self._read_region(
            start_lba=0,
            count=2,
        )

        if len(prefix) != (
            2 * _NATIVE_BLOCK
        ):
            raise RepartitionError(
                "GPT prefix read was truncated."
            )

        ph = _parse_header(
            prefix[
                _NATIVE_BLOCK:
                _NATIVE_BLOCK * 2
            ],
            label="primary",
        )

        primary_count = int(
            ph["first_usable"]
        )

        backup_start = (
            int(
                ph["last_usable"]
            )
            + 1
        )

        backup_count = (
            disk_lbas
            - backup_start
        )

        primary = self._read_region(
            start_lba=0,
            count=primary_count,
        )

        backup = self._read_region(
            start_lba=backup_start,
            count=backup_count,
        )

        return _snapshot_from_regions(
            primary=primary,
            backup=backup,
            block_size=_NATIVE_BLOCK,
            disk_lbas=disk_lbas,
            backup_start_lba=backup_start,
        )

    def _super_prefix_sha256(
        self,
    ) -> str:
        if (
            _STOCK_SUPER_BYTES
            % (1024 * 1024)
        ):
            raise RepartitionError(
                "Stock super size is not MiB aligned."
            )

        count = (
            _STOCK_SUPER_BYTES
            // (1024 * 1024)
        )

        output = self._adb_shell(
            "dd if=/dev/block/by-name/super "
            "bs=1048576 "
            f"count={count} "
            "2>/dev/null | sha256sum"
        )

        digest = (
            output.split()[0]
            if output.split()
            else ""
        )

        if (
            len(digest) != 64
            or any(
                char not in "0123456789abcdefABCDEF"
                for char in digest
            )
        ):
            raise RepartitionError(
                "Unable to fingerprint the stock-size "
                "super prefix."
            )

        return digest.lower()

    def _save_run_artifacts(
        self,
        *,
        direction: str,
        snapshot: GptSnapshot,
        proposed_primary: bytes,
        proposed_backup: bytes,
        plan: RepartitionPlan,
        super_prefix_sha256: str,
    ) -> Path:
        stamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        run_root = (
            self.output_root
            / "backup"
            / f"{stamp}-{direction}"
        )

        run_root.mkdir(
            parents=True,
            exist_ok=False,
        )

        (
            run_root
            / "gpt-primary-before.bin"
        ).write_bytes(
            snapshot.primary
        )

        (
            run_root
            / "gpt-backup-before.bin"
        ).write_bytes(
            snapshot.backup
        )

        (
            run_root
            / "gpt-primary-target.bin"
        ).write_bytes(
            proposed_primary
        )

        (
            run_root
            / "gpt-backup-target.bin"
        ).write_bytes(
            proposed_backup
        )

        (
            run_root
            / "plan.json"
        ).write_text(
            json.dumps(
                plan.to_dict(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        manifest = {
            "direction": direction,
            "profile": plan.profile,
            "super_prefix_bytes": (
                _STOCK_SUPER_BYTES
            ),
            "super_prefix_sha256": (
                super_prefix_sha256
            ),
            "primary_before_sha256": (
                _sha256(
                    snapshot.primary
                )
            ),
            "backup_before_sha256": (
                _sha256(
                    snapshot.backup
                )
            ),
            "primary_target_sha256": (
                _sha256(
                    proposed_primary
                )
            ),
            "backup_target_sha256": (
                _sha256(
                    proposed_backup
                )
            ),
        }

        (
            run_root
            / "manifest.json"
        ).write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return run_root

    def _write_state(
        self,
        payload: dict[str, object],
    ) -> None:
        self.state_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _load_state(
        self,
    ) -> dict[str, object]:
        if not self.state_path.is_file():
            raise RepartitionError(
                "TreeForge repartition state is missing; "
                "automatic undo is refused."
            )

        return json.loads(
            self.state_path.read_text(
                encoding="utf-8"
            )
        )

    def validate_undo_state(
        self,
        *,
        plan: RepartitionPlan,
    ) -> None:
        state = self._load_state()

        expected_current_super = (
            plan.current_super_size_sectors
            * plan.sector_size_bytes
        )

        if (
            state.get(
                "target_super_size_bytes"
            )
            != expected_current_super
        ):
            raise RepartitionError(
                "Saved TreeForge repartition state "
                "does not match the requested undo."
            )

        if not state.get(
            "stock_super_prefix_sha256"
        ):
            raise RepartitionError(
                "Saved TreeForge repartition state "
                "does not contain the super safety "
                "fingerprint."
            )

    def _push(
        self,
        local: Path,
        remote: str,
    ) -> None:
        completed = subprocess.run(
            [
                self.adb,
                "push",
                str(local),
                remote,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if completed.returncode != 0:
            raise RepartitionError(
                f"Unable to stage {local.name}: "
                f"{completed.stderr.strip()}"
            )

    def _write_region(
        self,
        *,
        remote: str,
        start_lba: int,
        count: int,
    ) -> None:
        self._adb_shell(
            "dd "
            f"if={remote} "
            "of=/dev/block/sda "
            f"bs={_NATIVE_BLOCK} "
            f"seek={start_lba} "
            f"count={count} "
            "2>/dev/null"
        )

        self._adb_shell(
            "sync"
        )

    def _write_transaction(
        self,
        *,
        snapshot: GptSnapshot,
        run_root: Path,
        proposed_primary: bytes,
        proposed_backup: bytes,
    ) -> None:
        remote_before_primary = (
            "/data/local/tmp/"
            "treeforge-gpt-primary-before.bin"
        )
        remote_before_backup = (
            "/data/local/tmp/"
            "treeforge-gpt-backup-before.bin"
        )
        remote_target_primary = (
            "/data/local/tmp/"
            "treeforge-gpt-primary-target.bin"
        )
        remote_target_backup = (
            "/data/local/tmp/"
            "treeforge-gpt-backup-target.bin"
        )

        self._push(
            run_root
            / "gpt-primary-before.bin",
            remote_before_primary,
        )
        self._push(
            run_root
            / "gpt-backup-before.bin",
            remote_before_backup,
        )
        self._push(
            run_root
            / "gpt-primary-target.bin",
            remote_target_primary,
        )
        self._push(
            run_root
            / "gpt-backup-target.bin",
            remote_target_backup,
        )

        primary_count = (
            len(
                proposed_primary
            )
            // _NATIVE_BLOCK
        )

        backup_count = (
            len(
                proposed_backup
            )
            // _NATIVE_BLOCK
        )

        self._adb_shell(
            "sync"
        )

        #
        # Stop Android framework activity. We intentionally
        # do NOT ask this running kernel to reread the GPT.
        #
        self._adb_shell(
            "stop"
        )
        self._adb_shell(
            "sync"
        )

        write_started = False

        try:
            #
            # Backup GPT first.
            #
            write_started = True

            self._write_region(
                remote=remote_target_backup,
                start_lba=(
                    snapshot.backup_start_lba
                ),
                count=backup_count,
            )

            if self._read_region(
                start_lba=(
                    snapshot.backup_start_lba
                ),
                count=backup_count,
            ) != proposed_backup:
                raise RepartitionError(
                    "Backup GPT readback mismatch."
                )

            #
            # Primary GPT second.
            #
            self._write_region(
                remote=remote_target_primary,
                start_lba=0,
                count=primary_count,
            )

            if self._read_region(
                start_lba=0,
                count=primary_count,
            ) != proposed_primary:
                raise RepartitionError(
                    "Primary GPT readback mismatch."
                )

        except Exception as error:
            if write_started:
                try:
                    #
                    # Best-effort transactional restoration
                    # while the original partition map is
                    # still active in this kernel.
                    #
                    self._write_region(
                        remote=remote_before_backup,
                        start_lba=(
                            snapshot.backup_start_lba
                        ),
                        count=backup_count,
                    )

                    self._write_region(
                        remote=remote_before_primary,
                        start_lba=0,
                        count=primary_count,
                    )

                    backup_restored = (
                        self._read_region(
                            start_lba=(
                                snapshot.backup_start_lba
                            ),
                            count=backup_count,
                        )
                        == snapshot.backup
                    )

                    primary_restored = (
                        self._read_region(
                            start_lba=0,
                            count=primary_count,
                        )
                        == snapshot.primary
                    )

                    if not (
                        backup_restored
                        and primary_restored
                    ):
                        raise RepartitionError(
                            "Automatic GPT restoration "
                            "did not verify."
                        )

                except Exception as restore_error:
                    raise RepartitionError(
                        "GPT write failed AND automatic "
                        "GPT restoration failed. "
                        f"Recovery artifacts: {run_root}. "
                        f"Write error: {error}. "
                        f"Restore error: {restore_error}"
                    ) from restore_error

                raise RepartitionError(
                    "GPT write failed; the original GPT "
                    "was restored and verified. "
                    f"Original error: {error}"
                ) from error

            raise

        self._adb_shell(
            "rm -f "
            f"{remote_before_primary} "
            f"{remote_before_backup} "
            f"{remote_target_primary} "
            f"{remote_target_backup}",
            check=False,
        )

    def _wait_fastboot(
        self,
    ) -> None:
        for _ in range(60):
            completed = subprocess.run(
                [
                    self.fastboot,
                    "getvar",
                    "product",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            if (
                completed.returncode == 0
                and "tangorpro" in (
                    completed.stdout
                    + completed.stderr
                )
            ):
                return

            time.sleep(1)

        raise RepartitionError(
            "Device did not return to bootloader "
            "fastboot."
        )

    def _verify_fastboot_target(
        self,
        plan: RepartitionPlan,
    ) -> None:
        super_size = int(
            self._fastboot_getvar(
                "partition-size:super"
            ),
            0,
        )

        userdata_size = int(
            self._fastboot_getvar(
                "partition-size:userdata"
            ),
            0,
        )

        expected_super = (
            plan.realized_super_size_bytes
        )

        expected_userdata = (
            plan.new_userdata_size_sectors
            * plan.sector_size_bytes
        )

        if (
            super_size != expected_super
            or userdata_size
            != expected_userdata
        ):
            raise RepartitionError(
                "Bootloader did not report the "
                "expected target partition sizes: "
                f"super={super_size:,}/"
                f"{expected_super:,}, "
                f"userdata={userdata_size:,}/"
                f"{expected_userdata:,}"
            )

    def _format(
        self,
        *,
        partition: str,
        fs_type: str,
        formatter: FormatterPreflight,
    ) -> None:
        env = dict(
            os.environ
        )
        env["PATH"] = formatter.path

        completed = subprocess.run(
            [
                self.fastboot,
                f"format:{fs_type}",
                partition,
            ],
            env=env,
            check=False,
        )

        if completed.returncode != 0:
            raise RepartitionError(
                f"Formatting {partition} "
                f"as {fs_type} failed."
            )

    def execute(
        self,
        *,
        plan: RepartitionPlan,
        formatter: FormatterPreflight,
    ) -> Path:
        direction = plan.direction

        if direction not in {
            "forward",
            "undo",
        }:
            raise RepartitionError(
                f"Unsupported repartition direction: "
                f"{direction}"
            )

        if direction == "undo":
            self.validate_undo_state(
                plan=plan,
            )

        self._temporary_boot()

        snapshot = self._capture_gpt()

        _validate_plan_geometry(
            snapshot,
            plan,
            target=False,
        )

        super_prefix_sha256 = (
            self._super_prefix_sha256()
        )

        if direction == "undo":
            state = self._load_state()

            expected_digest = str(
                state[
                    "stock_super_prefix_sha256"
                ]
            )

            if (
                super_prefix_sha256
                != expected_digest
            ):
                raise RepartitionError(
                    "Undo refused: super has changed "
                    "since TreeForge repartitioned it. "
                    "Shrinking super could truncate "
                    "logical-partition data."
                )

        proposed_primary, proposed_backup = (
            _build_target_regions(
                snapshot,
                plan,
            )
        )

        run_root = (
            self._save_run_artifacts(
                direction=direction,
                snapshot=snapshot,
                proposed_primary=(
                    proposed_primary
                ),
                proposed_backup=(
                    proposed_backup
                ),
                plan=plan,
                super_prefix_sha256=(
                    super_prefix_sha256
                ),
            )
        )

        #
        # Persist enough state for undo BEFORE the first
        # GPT write.
        #
        if direction == "forward":
            self._write_state(
                {
                    "status": "pending-forward",
                    "profile": plan.profile,
                    "target_super_size_bytes": (
                        plan.realized_super_size_bytes
                    ),
                    "stock_super_prefix_bytes": (
                        _STOCK_SUPER_BYTES
                    ),
                    "stock_super_prefix_sha256": (
                        super_prefix_sha256
                    ),
                    "backup_directory": str(
                        run_root
                    ),
                }
            )

        self._write_transaction(
            snapshot=snapshot,
            run_root=run_root,
            proposed_primary=(
                proposed_primary
            ),
            proposed_backup=(
                proposed_backup
            ),
        )

        #
        # Reboot immediately. Do not reread the GPT inside
        # the running Android kernel.
        #
        completed = subprocess.run(
            [
                self.adb,
                "reboot",
                "bootloader",
            ],
            check=False,
        )

        if completed.returncode != 0:
            raise RepartitionError(
                "GPT was written and verified, but "
                "reboot-to-bootloader failed. "
                f"Recovery artifacts: {run_root}"
            )

        self._wait_fastboot()
        self._verify_fastboot_target(
            plan
        )

        if direction == "forward":
            state = self._load_state()
            state["status"] = (
                "geometry-applied"
            )
            self._write_state(
                state
            )

        #
        # Recreate both filesystems only after bootloader
        # fastboot confirms the new GPT geometry.
        #
        self._format(
            partition="userdata",
            fs_type=(
                formatter.userdata_fs
            ),
            formatter=formatter,
        )

        self._format(
            partition="metadata",
            fs_type=(
                formatter.metadata_fs
            ),
            formatter=formatter,
        )

        self._verify_fastboot_target(
            plan
        )

        if direction == "forward":
            state = self._load_state()
            state["status"] = "applied"
            self._write_state(
                state
            )

        else:
            self._write_state(
                {
                    "status": "stock-restored",
                    "profile": plan.profile,
                    "last_undo_backup_directory": (
                        str(run_root)
                    ),
                }
            )

        return run_root
