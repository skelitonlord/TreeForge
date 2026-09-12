from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import zipfile
import time

from treeforge.android.host_tools import (
    treeforge_adb_executable,
    treeforge_fastboot_executable,
)


class AndroidInstallError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallOperation:
    line_number: int
    raw: str
    command: str
    domain: str

    partition: str | None = None
    image_name: str | None = None

    apply_vbmeta: bool = False
    slot_other: bool = False
    conditional: bool = False


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallRequirement:
    line_number: int
    raw: str
    key: str
    values: tuple[str, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallImage:
    partition: str
    image_name: str
    path: Path

    size_bytes: int
    sha256: str

    domain: str
    apply_vbmeta: bool
    slot_other: bool


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallBuild:
    product_out: Path
    fastboot_info_path: Path
    android_info_path: Path

    target_device: str

    requirements: tuple[
        AndroidInstallRequirement,
        ...,
    ]

    operations: tuple[
        AndroidInstallOperation,
        ...,
    ]

    images: tuple[
        AndroidInstallImage,
        ...,
    ]

    uses_update_super: bool
    super_empty_path: Path | None

    userdata_fs_type: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallDevice:
    serial: str

    initial_mode: str
    final_mode: str

    product: str | None

    current_slot: str | None
    slot_count: int | None

    unlocked: str | None
    secure: str | None

    snapshot_update_status: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallSelection:
    slot_argument: str
    display_name: str

    final_active_slot: str

    wipe_userdata: bool


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInstallExecutionResult:
    command: tuple[str, ...]
    returncode: int

    final_active_slot: str
    reboot_requested: bool


DENIED_PARTITIONS = frozenset(
    {
        "abl",
        "bl1",
        "bl2",
        "bl31",
        "pbl",
        "tzsw",
        "gsa",
        "ldfw",
        "dpm",
        "dram_train",
    }
)


def _file_identity(
    path: Path,
) -> tuple[int, str]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Install artifact is unavailable: {path}"
        )

    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return (
        path.stat().st_size,
        digest.hexdigest(),
    )


def _candidate_freshness(
    product_out: Path,
) -> float:
    values = []

    fastboot_info = (
        product_out
        / "fastboot-info.txt"
    )

    if fastboot_info.is_file():
        values.append(
            fastboot_info.stat().st_mtime
        )

    for path in (
        product_out.glob("*.img")
    ):
        if path.is_file():
            values.append(
                path.stat().st_mtime
            )

    return max(
        values,
        default=0.0,
    )


def _candidate_product_outputs(
    output: Path,
) -> tuple[Path, ...]:
    candidates: list[Path] = []

    def add(
        path: Path,
    ) -> None:
        resolved = (
            path
            .expanduser()
            .resolve()
        )

        if not (
            resolved
            / "fastboot-info.txt"
        ).is_file():
            return

        if resolved not in candidates:
            candidates.append(
                resolved
            )

    #
    # --input may itself be an Android product output.
    #
    add(
        output
    )

    #
    # Allow a product output to be retained/copied under the
    # TreeForge output root without adding another CLI argument.
    #
    for relative in (
        Path("aosp"),
        Path("build"),
        Path("android-build"),
        Path("device-tree/build"),
        Path("device-tree/aosp-build"),
    ):
        candidate_root = (
            output
            / relative
        )

        if not candidate_root.is_dir():
            continue

        add(
            candidate_root
        )

        for child in (
            candidate_root.iterdir()
        ):
            if child.is_dir():
                add(
                    child
                )

    #
    # Current developer workflow fallback:
    # use the newest completed product output under the local
    # AOSP build destination.
    #
    repository_root = (
        Path.cwd()
        .resolve()
    )

    for out_name in (
        "out-treeforge",
        "out",
    ):
        product_root = (
            repository_root
            / "aosp"
            / out_name
            / "target"
            / "product"
        )

        if not product_root.is_dir():
            continue

        for child in (
            product_root.iterdir()
        ):
            if child.is_dir():
                add(
                    child
                )

    return tuple(
        sorted(
            candidates,
            key=_candidate_freshness,
            reverse=True,
        )
    )


def _safe_relative_image_name(
    value: str,
) -> str:
    candidate = Path(
        value
    )

    if candidate.is_absolute():
        raise AndroidInstallError(
            "fastboot-info.txt contains an absolute "
            f"image path: {value}"
        )

    if ".." in candidate.parts:
        raise AndroidInstallError(
            "fastboot-info.txt image path escapes "
            f"the product output: {value}"
        )

    return candidate.as_posix()


def _parse_fastboot_info(
    product_out: Path,
) -> tuple[
    tuple[
        AndroidInstallOperation,
        ...,
    ],
    bool,
]:
    path = (
        product_out
        / "fastboot-info.txt"
    )

    if not path.is_file():
        raise AndroidInstallError(
            f"missing fastboot-info.txt: {path}"
        )

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    operations = []

    domain = (
        "bootloader-fastboot"
    )

    version_seen = False
    uses_update_super = False

    for line_number, raw in enumerate(
        text.splitlines(),
        1,
    ):
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        fields = shlex.split(
            line
        )

        if not fields:
            continue

        command = fields[0]

        if command == "version":
            if fields != [
                "version",
                "1",
            ]:
                raise AndroidInstallError(
                    "unsupported fastboot-info.txt "
                    f"version line: {line}"
                )

            version_seen = True

            operations.append(
                AndroidInstallOperation(
                    line_number=line_number,
                    raw=line,
                    command="version",
                    domain="metadata",
                )
            )

            continue

        if command == "flash":
            args = fields[1:]

            apply_vbmeta = (
                "--apply-vbmeta"
                in args
            )

            slot_other = (
                "--slot-other"
                in args
            )

            positional = tuple(
                value
                for value in args
                if not value.startswith("--")
            )

            if not positional:
                raise AndroidInstallError(
                    "malformed flash operation on "
                    f"line {line_number}: {line}"
                )

            partition = positional[0]

            if partition in DENIED_PARTITIONS:
                raise AndroidInstallError(
                    "AOSP install manifest requests "
                    "a TreeForge-denied firmware/"
                    "bootloader partition: "
                    f"{partition}"
                )

            image_name = (
                positional[1]
                if len(positional) >= 2
                else f"{partition}.img"
            )

            image_name = (
                _safe_relative_image_name(
                    image_name
                )
            )

            operations.append(
                AndroidInstallOperation(
                    line_number=line_number,
                    raw=line,
                    command="flash",
                    domain=domain,
                    partition=partition,
                    image_name=image_name,
                    apply_vbmeta=apply_vbmeta,
                    slot_other=slot_other,
                )
            )

            continue

        if command == "reboot":
            if len(fields) != 2:
                raise AndroidInstallError(
                    "unsupported reboot operation in "
                    f"fastboot-info.txt: {line}"
                )

            target = fields[1]

            if target not in {
                "fastboot",
                "bootloader",
            }:
                raise AndroidInstallError(
                    "unsupported fastboot-info reboot "
                    f"target: {target}"
                )

            operations.append(
                AndroidInstallOperation(
                    line_number=line_number,
                    raw=line,
                    command=f"reboot-{target}",
                    domain="transition",
                )
            )

            domain = (
                "fastbootd"
                if target == "fastboot"
                else "bootloader-fastboot"
            )

            continue

        if command == "update-super":
            if domain != "fastbootd":
                raise AndroidInstallError(
                    "update-super appears outside the "
                    "fastbootd phase"
                )

            uses_update_super = True

            operations.append(
                AndroidInstallOperation(
                    line_number=line_number,
                    raw=line,
                    command="update-super",
                    domain="fastbootd",
                )
            )

            continue

        if command == "if-wipe":
            if (
                len(fields) != 3
                or fields[1] != "erase"
                or fields[2] not in {
                    "userdata",
                    "metadata",
                }
            ):
                raise AndroidInstallError(
                    "unsupported conditional operation: "
                    f"{line}"
                )

            partition = fields[2]

            operations.append(
                AndroidInstallOperation(
                    line_number=line_number,
                    raw=line,
                    command=f"erase-{partition}",
                    domain="conditional",
                    partition=partition,
                    conditional=True,
                )
            )

            continue

        raise AndroidInstallError(
            "unsupported fastboot-info.txt command "
            f"on line {line_number}: {line}"
        )

    if not version_seen:
        raise AndroidInstallError(
            "fastboot-info.txt does not declare version 1"
        )

    flash_operations = tuple(
        operation
        for operation in operations
        if operation.command == "flash"
    )

    if not flash_operations:
        raise AndroidInstallError(
            "fastboot-info.txt contains no flash operations"
        )

    return (
        tuple(
            operations
        ),
        uses_update_super,
    )


def _load_misc_info(
    product_out: Path,
) -> dict[str, str]:
    path = product_out / "misc_info.txt"

    if not path.is_file():
        return {}

    values: dict[str, str] = {}

    for raw in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split(
            "=",
            1,
        )

        values[key.strip()] = value.strip()

    return values



SUPPORTED_ANDROID_INFO_REQUIREMENTS = frozenset(
    {
        "board",
        "product",
        "partition-exists",
        "version-bootloader",
        "version-baseband",
    }
)


def _parse_android_info_requirements(
    path: Path,
) -> tuple[
    AndroidInstallRequirement,
    ...,
]:
    requirements = []

    for line_number, raw in enumerate(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        1,
    ):
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if not line.startswith(
            "require "
        ):
            raise AndroidInstallError(
                "unsupported android-info.txt directive "
                f"on line {line_number}: {line}"
            )

        payload = (
            line[
                len("require "):
            ]
            .strip()
        )

        if "=" not in payload:
            raise AndroidInstallError(
                "malformed android-info.txt requirement "
                f"on line {line_number}: {line}"
            )

        key, value = payload.split(
            "=",
            1,
        )

        key = key.strip()

        values = tuple(
            item.strip()
            for item in value.split("|")
            if item.strip()
        )

        if not key:
            raise AndroidInstallError(
                "android-info.txt requirement has an "
                f"empty key on line {line_number}"
            )

        if not values:
            raise AndroidInstallError(
                "android-info.txt requirement has no "
                f"accepted values on line {line_number}: "
                f"{line}"
            )

        if (
            key
            not in
            SUPPORTED_ANDROID_INFO_REQUIREMENTS
        ):
            raise AndroidInstallError(
                "unsupported android-info.txt requirement "
                f"kind {key!r} on line {line_number}: "
                f"{line}"
            )

        requirements.append(
            AndroidInstallRequirement(
                line_number=line_number,
                raw=line,
                key=key,
                values=values,
            )
        )

    if not requirements:
        raise AndroidInstallError(
            "android-info.txt contains no supported "
            "device admission requirements"
        )

    return tuple(
        requirements
    )


SUPPORTED_ANDROID_INFO_REQUIREMENTS = frozenset(
    {
        "board",
        "product",
        "partition-exists",
        "version-bootloader",
        "version-baseband",
    }
)


def _parse_android_info_requirements(
    path: Path,
) -> tuple[
    AndroidInstallRequirement,
    ...,
]:
    requirements = []

    for line_number, raw in enumerate(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines(),
        1,
    ):
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if not line.startswith(
            "require "
        ):
            raise AndroidInstallError(
                "unsupported android-info.txt directive "
                f"on line {line_number}: {line}"
            )

        payload = (
            line[len("require "):]
            .strip()
        )

        if "=" not in payload:
            raise AndroidInstallError(
                "malformed android-info.txt requirement "
                f"on line {line_number}: {line}"
            )

        key, value = payload.split(
            "=",
            1,
        )

        key = key.strip()

        values = tuple(
            item.strip()
            for item in value.split("|")
            if item.strip()
        )

        if not key or not values:
            raise AndroidInstallError(
                "malformed android-info.txt requirement "
                f"on line {line_number}: {line}"
            )

        if (
            key
            not in
            SUPPORTED_ANDROID_INFO_REQUIREMENTS
        ):
            raise AndroidInstallError(
                "unsupported android-info.txt requirement "
                f"kind {key!r} on line {line_number}: "
                f"{line}"
            )

        requirements.append(
            AndroidInstallRequirement(
                line_number=line_number,
                raw=line,
                key=key,
                values=values,
            )
        )

    if not requirements:
        raise AndroidInstallError(
            "android-info.txt contains no supported "
            "device admission requirements"
        )

    return tuple(
        requirements
    )


def _android_info_target_device(
    requirements: tuple[
        AndroidInstallRequirement,
        ...,
    ],
    *,
    fallback: str,
) -> str:
    product_values = []
    board_values = []

    for requirement in requirements:
        if requirement.key == "product":
            product_values.extend(
                requirement.values
            )

        elif requirement.key == "board":
            board_values.extend(
                requirement.values
            )

    for values in (
        product_values,
        board_values,
    ):
        if fallback in values:
            return fallback

        if values:
            return values[0]

    return fallback


def _load_install_build(
    product_out: Path,
) -> AndroidInstallBuild:
    operations, uses_update_super = (
        _parse_fastboot_info(
            product_out
        )
    )

    misc_info = _load_misc_info(
        product_out
    )

    userdata_fs_type = misc_info.get(
        "userdata_fs_type"
    )

    if userdata_fs_type is not None:
        userdata_fs_type = (
            userdata_fs_type
            .strip()
            .lower()
        )

    android_info_path = (
        product_out
        / "android-info.txt"
    )

    if not android_info_path.is_file():
        raise AndroidInstallError(
            "AOSP product output is missing "
            f"android-info.txt: {android_info_path}"
        )

    requirements = (
        _parse_android_info_requirements(
            android_info_path
        )
    )

    images = []

    for operation in operations:
        if operation.command != "flash":
            continue

        assert operation.partition is not None
        assert operation.image_name is not None

        path = (
            product_out
            / operation.image_name
        ).resolve()

        try:
            path.relative_to(
                product_out
            )
        except ValueError as error:
            raise AndroidInstallError(
                "resolved install image escapes "
                "the product output: "
                f"{path}"
            ) from error

        size_bytes, digest = (
            _file_identity(
                path
            )
        )

        images.append(
            AndroidInstallImage(
                partition=(
                    operation.partition
                ),
                image_name=(
                    operation.image_name
                ),
                path=path,
                size_bytes=size_bytes,
                sha256=digest,
                domain=operation.domain,
                apply_vbmeta=(
                    operation.apply_vbmeta
                ),
                slot_other=(
                    operation.slot_other
                ),
            )
        )

    super_empty_path = None

    if uses_update_super:
        super_empty_path = (
            product_out
            / "super_empty.img"
        )

        if not super_empty_path.is_file():
            raise AndroidInstallError(
                "fastboot-info.txt requires update-super "
                "but super_empty.img is missing"
            )

    return AndroidInstallBuild(
        product_out=product_out,
        fastboot_info_path=(
            product_out
            / "fastboot-info.txt"
        ),
        android_info_path=android_info_path,
        target_device=_android_info_target_device(
            requirements,
            fallback=product_out.name,
        ),
        requirements=requirements,
        operations=operations,
        images=tuple(images),
        uses_update_super=uses_update_super,
        super_empty_path=super_empty_path,
        userdata_fs_type=userdata_fs_type,
    )


def _factory_image_archive(
    directory: Path,
) -> Path | None:
    """
    Resolve Google's inner image-*.zip from one factory-image directory.

    A factory directory is authoritative when it contains exactly one
    inner Android image archive. It must never fall through to unrelated
    automatic AOSP-output discovery.
    """

    if not directory.is_dir():
        return None

    candidates = tuple(
        sorted(
            path
            for path
            in directory.glob(
                "image-*.zip"
            )
            if path.is_file()
        )
    )

    if not candidates:
        return None

    if len(candidates) != 1:
        raise AndroidInstallError(
            "factory image directory must contain exactly "
            "one image-*.zip archive; found "
            f"{len(candidates)} in {directory}"
        )

    return candidates[0]


def _factory_cache_root() -> Path:
    #
    # stage.py:
    #   REPO/treeforge/android/install/stage.py
    #
    # parents[3] is the TreeForge repository root.
    #
    repository_root = (
        Path(__file__)
        .resolve()
        .parents[3]
    )

    return (
        repository_root
        / "output"
        / "install"
        / "factory-input"
    )


def _materialize_factory_image_output(
    factory_directory: Path,
    archive: Path,
) -> Path:
    """
    Materialize Google's inner product-image ZIP into a TreeForge-owned
    cache.

    The source factory directory remains untouched.

    The extracted files then enter the exact same Install parsing,
    identity hashing, denylist, slot-applicability, and planning path as
    an AOSP product output.
    """

    archive = (
        archive
        .expanduser()
        .resolve()
    )

    factory_directory = (
        factory_directory
        .expanduser()
        .resolve()
    )

    stat = archive.stat()

    source_identity = (
        f"source={archive}\n"
        f"bytes={stat.st_size}\n"
        f"mtime_ns={stat.st_mtime_ns}\n"
    )

    destination = (
        _factory_cache_root()
        / archive.stem
    )

    marker = (
        destination
        / ".treeforge-factory-source"
    )

    #
    # Reuse a complete cache only when it still corresponds to the exact
    # source archive metadata observed by this process.
    #
    if (
        destination.is_dir()
        and marker.is_file()
        and marker.read_text(
            encoding="utf-8",
            errors="replace",
        )
        == source_identity
        and (
            destination
            / "fastboot-info.txt"
        ).is_file()
        and (
            destination
            / "android-info.txt"
        ).is_file()
    ):
        return destination

    if destination.exists():
        shutil.rmtree(
            destination
        )

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with zipfile.ZipFile(
            archive,
            "r",
        ) as handle:
            members = (
                handle.infolist()
            )

            if not members:
                raise AndroidInstallError(
                    "factory image archive is empty: "
                    f"{archive}"
                )

            #
            # Validate every archive path before allowing extraction.
            #
            for info in members:
                relative = Path(
                    info.filename
                )

                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                ):
                    raise AndroidInstallError(
                        "factory image archive contains an "
                        "unsafe path: "
                        f"{info.filename}"
                    )

            handle.extractall(
                destination
            )

    except (
        zipfile.BadZipFile,
        OSError,
    ) as error:
        if destination.exists():
            shutil.rmtree(
                destination,
                ignore_errors=True,
            )

        raise AndroidInstallError(
            "unable to materialize factory image archive "
            f"{archive}: {error}"
        ) from error

    required = (
        "fastboot-info.txt",
        "android-info.txt",
    )

    missing = tuple(
        name
        for name in required
        if not (
            destination
            / name
        ).is_file()
    )

    if missing:
        shutil.rmtree(
            destination,
            ignore_errors=True,
        )

        raise AndroidInstallError(
            "factory image archive is missing required "
            "Install metadata: "
            + ", ".join(
                missing
            )
        )

    marker.write_text(
        source_identity,
        encoding="utf-8",
    )

    return destination


def resolve_install_build(
    input_path: Path,
    *,
    allow_discovery: bool = True,
) -> AndroidInstallBuild:
    input_path = (
        input_path
        .expanduser()
        .resolve()
    )

    #
    # Direct Android product output.
    #
    if (
        input_path.is_dir()
        and (
            input_path
            / "fastboot-info.txt"
        ).is_file()
    ):
        return _load_install_build(
            input_path
        )

    #
    # Direct Google inner image-*.zip.
    #
    if (
        input_path.is_file()
        and input_path.suffix.lower()
        == ".zip"
        and input_path.name.startswith(
            "image-"
        )
    ):
        product_out = (
            _materialize_factory_image_output(
                input_path.parent,
                input_path,
            )
        )

        return _load_install_build(
            product_out
        )

    #
    # Extracted Google factory directory containing image-*.zip.
    #
    factory_archive = (
        _factory_image_archive(
            input_path
        )
    )

    if factory_archive is not None:
        product_out = (
            _materialize_factory_image_output(
                input_path,
                factory_archive,
            )
        )

        return _load_install_build(
            product_out
        )

    #
    # An explicit --input is authoritative.
    #
    # Never silently fall through to an unrelated AOSP build when the
    # user named a source.
    #
    if not allow_discovery:
        raise AndroidInstallError(
            "explicit Install input is not a supported "
            "Android product/factory source: "
            f"{input_path}. Expected a directory containing "
            "fastboot-info.txt, an extracted Google factory "
            "directory containing exactly one image-*.zip, "
            "or the inner image-*.zip directly."
        )

    #
    # Automatic discovery exists only when --input was omitted.
    #
    candidates = (
        _candidate_product_outputs(
            input_path
        )
    )

    if not candidates:
        raise AndroidInstallError(
            "Unable to find an Android product output "
            "containing fastboot-info.txt. "
            f"TreeForge discovery root: {input_path}"
        )

    errors = []

    for candidate in candidates:
        try:
            return _load_install_build(
                candidate
            )

        except (
            AndroidInstallError,
            FileNotFoundError,
        ) as error:
            errors.append(
                f"{candidate}: {error}"
            )

    raise AndroidInstallError(
        "No candidate Android product output passed "
        "Install validation:\n  "
        + "\n  ".join(
            errors
        )
    )




def render_install_fastboot_info(
    *,
    build: AndroidInstallBuild,
    slot_applicability: dict[str, bool | None],
) -> str:
    """
    Produce one source-faithful A/B Install transaction.

    Bootloader-domain slotted images are mirrored to both physical slots.

    Fastbootd/dynamic-partition operations retain the exact source
    primary/secondary semantics. TreeForge must not synthesize a second
    complete logical slot on a Virtual A/B device.

    update-super remains exactly once.

    Conditional userdata/metadata erases are intentionally omitted.

    No terminal Android reboot is encoded.
    """

    lines = [
        "version 1",
        "# Generated by TreeForge Install.",
        "# Source-faithful A/B transaction.",
        "# Physical slotted boot-chain images are mirrored to A + B.",
        "# Dynamic-partition slot semantics remain source-defined.",
        "# Shared super is realized exactly once.",
        "# Userdata and metadata are preserved.",
        "# No final Android reboot.",
    ]

    update_super_count = 0

    def flash_line(
        operation: AndroidInstallOperation,
        *,
        other: bool | None = None,
    ) -> str:
        assert operation.partition is not None
        assert operation.image_name is not None

        use_other = (
            operation.slot_other
            if other is None
            else other
        )

        fields = [
            "flash",
        ]

        if use_other:
            fields.append(
                "--slot-other"
            )

        if operation.apply_vbmeta:
            fields.append(
                "--apply-vbmeta"
            )

        fields.extend(
            (
                operation.partition,
                operation.image_name,
            )
        )

        return " ".join(
            fields
        )

    for operation in build.operations:
        if operation.command == "version":
            continue

        if operation.command == "flash":
            assert operation.partition is not None

            applicable = (
                slot_applicability.get(
                    operation.partition
                )
            )

            if applicable is None:
                raise AndroidInstallError(
                    "cannot establish slot applicability for "
                    f"{operation.partition!r}"
                )

            #
            # Physical/boot-chain domain:
            #
            # TreeForge explicitly provides A/B redundancy here.
            #
            if operation.domain == "bootloader-fastboot":
                if operation.slot_other:
                    #
                    # Preserve an explicitly source-declared secondary
                    # operation rather than inventing another one.
                    #
                    lines.append(
                        flash_line(
                            operation
                        )
                    )
                    continue

                lines.append(
                    flash_line(
                        operation,
                        other=False,
                    )
                )

                if applicable is True:
                    lines.append(
                        flash_line(
                            operation,
                            other=True,
                        )
                    )

                continue

            #
            # Dynamic/fastbootd domain:
            #
            # Preserve the source operation exactly.
            #
            # In particular:
            #
            #   flash system system.img
            #   flash --slot-other system system_other.img
            #
            # remains exactly that. We do NOT fabricate full
            # system/product/vendor/... images for the other slot.
            #
            if operation.domain == "fastbootd":
                lines.append(
                    flash_line(
                        operation
                    )
                )
                continue

            raise AndroidInstallError(
                "flash operation appears in unsupported "
                f"execution domain {operation.domain!r}: "
                f"{operation.raw}"
            )

        if operation.command == "reboot-fastboot":
            lines.append(
                "reboot fastboot"
            )
            continue

        if operation.command == "reboot-bootloader":
            lines.append(
                "reboot bootloader"
            )
            continue

        if operation.command == "update-super":
            update_super_count += 1

            lines.append(
                "update-super"
            )
            continue

        if operation.conditional:
            lines.append(
                "# omitted destructive conditional: "
                + operation.raw
            )
            continue

        raise AndroidInstallError(
            "cannot project source install operation: "
            f"{operation.raw}"
        )

    expected = (
        1
        if build.uses_update_super
        else 0
    )

    if update_super_count != expected:
        raise AndroidInstallError(
            "source-faithful Install expected "
            f"{expected} update-super operation(s), "
            f"found {update_super_count}"
        )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def validate_install_preflight(
    *,
    build: AndroidInstallBuild,
    device: AndroidInstallDevice,
    slot_applicability: dict[str, bool | None],
) -> dict:
    """
    Validate the complete TreeForge projection before any write.

    This validates the topology TreeForge owns. Dynamic allocation/group
    geometry remains source-defined by super_empty.img and fastboot/liblp;
    TreeForge deliberately does not claim that a byte-sum approximation
    proves liblp allocation feasibility.
    """

    if (
        device.slot_count != 2
        or device.current_slot
        not in {
            "a",
            "b",
        }
    ):
        raise AndroidInstallError(
            "Install requires exactly two A/B slots"
        )

    snapshot_status = (
        device.snapshot_update_status
        or "none"
    ).strip().lower()

    if snapshot_status not in {
        "",
        "none",
    }:
        raise AndroidInstallError(
            "Install refuses to modify a device with an "
            "active snapshot/update state: "
            f"{device.snapshot_update_status}"
        )

    update_super_count = sum(
        1
        for operation in build.operations
        if operation.command
        == "update-super"
    )

    expected_update_super = (
        1
        if build.uses_update_super
        else 0
    )

    if (
        update_super_count
        != expected_update_super
    ):
        raise AndroidInstallError(
            "source manifest has an invalid update-super "
            f"count: expected {expected_update_super}, "
            f"found {update_super_count}"
        )

    dynamic_images = tuple(
        image
        for image in build.images
        if image.domain == "fastbootd"
    )

    if (
        build.uses_update_super
        and not dynamic_images
    ):
        raise AndroidInstallError(
            "source manifest requests update-super but "
            "contains no dynamic image operations"
        )

    primary_dynamic_partitions = {
        image.partition
        for image in dynamic_images
        if not image.slot_other
    }

    secondary_dynamic_images = tuple(
        image
        for image in dynamic_images
        if image.slot_other
    )

    for image in build.images:
        applicability = (
            slot_applicability.get(
                image.partition
            )
        )

        if applicability is None:
            raise AndroidInstallError(
                "cannot establish slot applicability for "
                f"{image.partition!r}"
            )

    for image in secondary_dynamic_images:
        if (
            image.partition
            not in primary_dynamic_partitions
        ):
            raise AndroidInstallError(
                "source manifest contains a secondary "
                "dynamic image without a matching primary "
                f"partition: {image.partition} <- "
                f"{image.image_name}"
            )

        if (
            slot_applicability.get(
                image.partition
            )
            is not True
        ):
            raise AndroidInstallError(
                "source manifest requests --slot-other for "
                "a dynamic partition the connected device "
                "does not report as slotted: "
                f"{image.partition}"
            )

    physical_primary_images = tuple(
        image
        for image in build.images
        if (
            image.domain
            == "bootloader-fastboot"
            and not image.slot_other
        )
    )

    mirrored_physical_images = tuple(
        image
        for image in physical_primary_images
        if (
            slot_applicability.get(
                image.partition
            )
            is True
        )
    )

    return {
        "snapshot_state_safe": True,
        "update_super_count":
            update_super_count,
        "dynamic_topology":
            "source-defined",
        "dynamic_image_count":
            len(dynamic_images),
        "dynamic_primary_image_count":
            len(
                tuple(
                    image
                    for image in dynamic_images
                    if not image.slot_other
                )
            ),
        "dynamic_secondary_image_count":
            len(
                secondary_dynamic_images
            ),
        "synthetic_secondary_dynamic_images":
            0,
        "physical_primary_image_count":
            len(
                physical_primary_images
            ),
        "mirrored_physical_image_count":
            len(
                mirrored_physical_images
            ),
        "conditional_wipes_preserved":
            False,
        "automatic_android_reboot":
            False,
    }


class AndroidInstallDeviceController:
    FASTBOOT_DISCOVERY_ATTEMPTS = 60
    FASTBOOT_DISCOVERY_INTERVAL_SECONDS = 1.0

    def __init__(
        self,
    ) -> None:
        self.fastboot = (
            treeforge_fastboot_executable()
        )

        self.adb = (
            treeforge_adb_executable()
        )

        version_result = subprocess.run(
            (
                str(self.fastboot),
                "--version",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        self.fastboot_version = (
            version_result.stdout
            + version_result.stderr
        ).strip()

        if version_result.returncode != 0:
            raise AndroidInstallError(
                "unable to query TreeForge-owned fastboot version"
            )

    @staticmethod
    def _capture(
        command: tuple[str, ...],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    @staticmethod
    def _combined(
        completed: subprocess.CompletedProcess[str],
    ) -> str:
        return (
            completed.stdout
            + "\n"
            + completed.stderr
        )

    def _fastboot_serials(
        self,
    ) -> tuple[str, ...]:
        completed = self._capture(
            (
                str(self.fastboot),
                "devices",
            )
        )

        if completed.returncode != 0:
            return ()

        serials = []

        for line in (
            completed.stdout
            .splitlines()
        ):
            fields = line.strip().split()

            if fields:
                serials.append(
                    fields[0]
                )

        return tuple(
            serials
        )

    def _adb_serials(
        self,
    ) -> tuple[str, ...]:
        if self.adb is None:
            return ()

        completed = self._capture(
            (
                str(self.adb),
                "devices",
            )
        )

        if completed.returncode != 0:
            return ()

        serials = []

        for line in (
            completed.stdout
            .splitlines()[1:]
        ):
            fields = line.strip().split()

            if (
                len(fields) >= 2
                and fields[1] == "device"
            ):
                serials.append(
                    fields[0]
                )

        return tuple(
            serials
        )

    def _getvar(
        self,
        *,
        serial: str,
        name: str,
    ) -> str | None:
        completed = self._capture(
            (
                str(self.fastboot),
                "-s",
                serial,
                "getvar",
                name,
            )
        )

        text = self._combined(
            completed
        )

        pattern = re.compile(
            rf"(?m)^(?:\(bootloader\)\s*)?"
            rf"{re.escape(name)}:\s*(.*?)\s*$"
        )

        match = pattern.search(
            text
        )

        if match is not None:
            value = (
                match.group(1)
                .strip()
            )

            return (
                value
                if value
                else None
            )

        return None

    def _classify_fastboot(
        self,
        *,
        serial: str,
    ) -> str:
        value = self._getvar(
            serial=serial,
            name="is-userspace",
        )

        if (
            value is not None
            and value.strip().lower()
            in {
                "yes",
                "true",
                "1",
            }
        ):
            return "fastbootd"

        return "bootloader-fastboot"

    def _wait_for_fastboot(
        self,
        *,
        expected_serial: str,
    ) -> str:
        for _ in range(
            self.FASTBOOT_DISCOVERY_ATTEMPTS
        ):
            serials = (
                self._fastboot_serials()
            )

            if not serials:
                time.sleep(
                    self.FASTBOOT_DISCOVERY_INTERVAL_SECONDS
                )
                continue

            if len(serials) != 1:
                raise AndroidInstallError(
                    "Install requires exactly one fastboot "
                    "device after transition; "
                    f"found {len(serials)}"
                )

            serial = serials[0]

            if serial != expected_serial:
                raise AndroidInstallError(
                    "device serial changed across transport "
                    "transition: "
                    f"{expected_serial!r} -> {serial!r}"
                )

            return serial

        raise AndroidInstallError(
            "device did not become available in fastboot "
            "after mode transition"
        )

    def _reboot_fastboot_to_bootloader(
        self,
        *,
        serial: str,
    ) -> str:
        completed = self._capture(
            (
                str(self.fastboot),
                "-s",
                serial,
                "reboot",
                "bootloader",
            )
        )

        if completed.returncode != 0:
            raise AndroidInstallError(
                "failed to reboot fastbootd to bootloader:\n"
                + self._combined(
                    completed
                )
            )

        return self._wait_for_fastboot(
            expected_serial=serial,
        )

    def ensure_bootloader(
        self,
        *,
        serial: str,
    ) -> str:
        serial = self._wait_for_fastboot(
            expected_serial=serial,
        )

        mode = self._classify_fastboot(
            serial=serial,
        )

        if mode == "fastbootd":
            serial = (
                self._reboot_fastboot_to_bootloader(
                    serial=serial,
                )
            )

        final_mode = (
            self._classify_fastboot(
                serial=serial,
            )
        )

        if final_mode != "bootloader-fastboot":
            raise AndroidInstallError(
                "device did not enter bootloader fastboot"
            )

        return serial

    def enter_bootloader(
        self,
    ) -> AndroidInstallDevice:
        fastboot_serials = (
            self._fastboot_serials()
        )

        if len(fastboot_serials) > 1:
            raise AndroidInstallError(
                "Install requires exactly one fastboot "
                f"device; found {len(fastboot_serials)}"
            )

        if fastboot_serials:
            serial = (
                fastboot_serials[0]
            )

            initial_mode = (
                self._classify_fastboot(
                    serial=serial,
                )
            )

            if initial_mode == "fastbootd":
                serial = (
                    self._reboot_fastboot_to_bootloader(
                        serial=serial,
                    )
                )

        else:
            if self.adb is None:
                raise AndroidInstallError(
                    "no fastboot device is connected "
                    "and adb is unavailable"
                )

            adb_serials = (
                self._adb_serials()
            )

            if len(adb_serials) != 1:
                raise AndroidInstallError(
                    "Install requires exactly one ADB "
                    "device when no fastboot device exists; "
                    f"found {len(adb_serials)}"
                )

            serial = adb_serials[0]
            initial_mode = "adb"

            completed = self._capture(
                (
                    str(self.adb),
                    "-s",
                    serial,
                    "reboot",
                    "bootloader",
                )
            )

            if completed.returncode != 0:
                raise AndroidInstallError(
                    "failed to reboot ADB device into "
                    "bootloader fastboot:\n"
                    + self._combined(
                        completed
                    )
                )

            serial = self._wait_for_fastboot(
                expected_serial=serial,
            )

        serial = self.ensure_bootloader(
            serial=serial,
        )

        product = self._getvar(
            serial=serial,
            name="product",
        )

        current_slot = self._getvar(
            serial=serial,
            name="current-slot",
        )

        slot_count_raw = self._getvar(
            serial=serial,
            name="slot-count",
        )

        slot_count = None

        if slot_count_raw is not None:
            try:
                slot_count = int(
                    slot_count_raw,
                    10,
                )

            except ValueError as error:
                raise AndroidInstallError(
                    "fastboot returned invalid slot-count: "
                    f"{slot_count_raw!r}"
                ) from error

        unlocked = self._getvar(
            serial=serial,
            name="unlocked",
        )

        secure = self._getvar(
            serial=serial,
            name="secure",
        )

        snapshot_update_status = (
            self._getvar(
                serial=serial,
                name="snapshot-update-status",
            )
        )

        if (
            unlocked is not None
            and unlocked.strip().lower()
            in {
                "no",
                "false",
                "0",
            }
        ):
            raise AndroidInstallError(
                "device reports an explicitly locked "
                "bootloader; Install will not flash"
            )

        return AndroidInstallDevice(
            serial=serial,
            initial_mode=initial_mode,
            final_mode="bootloader-fastboot",
            product=product,
            current_slot=current_slot,
            slot_count=slot_count,
            unlocked=unlocked,
            secure=secure,
            snapshot_update_status=(
                snapshot_update_status
            ),
        )

    def partition_exists(
        self,
        *,
        serial: str,
        partition: str,
    ) -> bool:
        #
        # Unslotted physical/shared partition.
        #
        if (
            self._getvar(
                serial=serial,
                name=(
                    f"partition-size:{partition}"
                ),
            )
            is not None
        ):
            return True

        #
        # Slotted physical or logical partition.
        #
        # A zero-sized logical partition is still a real declared
        # partition, so variable presence matters here rather than
        # requiring a non-zero numeric size.
        #
        for suffix in (
            "a",
            "b",
        ):
            if (
                self._getvar(
                    serial=serial,
                    name=(
                        "partition-size:"
                        f"{partition}_{suffix}"
                    ),
                )
                is not None
            ):
                return True

        return False

    def validate_android_info(
        self,
        *,
        build: AndroidInstallBuild,
        device: AndroidInstallDevice,
    ) -> tuple[str, ...]:
        passed = []

        for requirement in (
            build.requirements
        ):
            key = requirement.key
            accepted = (
                requirement.values
            )

            if key in {
                "board",
                "product",
            }:
                observed = (
                    device.product
                )

                if (
                    observed is None
                    or observed not in accepted
                ):
                    raise AndroidInstallError(
                        "android-info.txt requirement "
                        f"failed: {requirement.raw}; "
                        "connected fastboot product="
                        f"{observed!r}"
                    )

                passed.append(
                    requirement.raw
                )
                continue

            if key == "partition-exists":
                existing = tuple(
                    partition
                    for partition in accepted
                    if self.partition_exists(
                        serial=device.serial,
                        partition=partition,
                    )
                )

                #
                # Android requirement alternatives separated by '|'
                # are treated as acceptable alternatives.
                #
                if not existing:
                    raise AndroidInstallError(
                        "android-info.txt requirement "
                        f"failed: {requirement.raw}; "
                        "none of the required partition "
                        "alternatives exist"
                    )

                passed.append(
                    requirement.raw
                )
                continue

            if key in {
                "version-bootloader",
                "version-baseband",
            }:
                observed = (
                    self._getvar(
                        serial=device.serial,
                        name=key,
                    )
                )

                if (
                    observed is None
                    or observed not in accepted
                ):
                    raise AndroidInstallError(
                        "android-info.txt requirement "
                        f"failed: {requirement.raw}; "
                        f"device reports {key}="
                        f"{observed!r}"
                    )

                passed.append(
                    requirement.raw
                )
                continue

            #
            # _parse_android_info_requirements() should make this
            # unreachable. Keep the execution gate closed if the model
            # and validator ever diverge.
            #
            raise AndroidInstallError(
                "android-info.txt requirement reached "
                "validation without an implementation: "
                f"{requirement.raw}"
            )

        return tuple(
            passed
        )

    def has_slot(
        self,
        *,
        serial: str,
        partition: str,
    ) -> bool | None:
        value = self._getvar(
            serial=serial,
            name=f"has-slot:{partition}",
        )

        if value is None:
            return None

        normalized = (
            value
            .strip()
            .lower()
        )

        if normalized in {
            "yes",
            "true",
            "1",
        }:
            return True

        if normalized in {
            "no",
            "false",
            "0",
        }:
            return False

        return None

    def partition_size_bytes(
        self,
        *,
        serial: str,
        partition: str,
    ) -> int:
        value = self._getvar(
            serial=serial,
            name=(
                f"partition-size:{partition}"
            ),
        )

        if value is None:
            raise AndroidInstallError(
                "fastboot did not report partition size "
                f"for {partition!r}"
            )

        try:
            result = int(
                value,
                0,
            )

        except ValueError as error:
            raise AndroidInstallError(
                "fastboot returned invalid partition size "
                f"for {partition!r}: {value!r}"
            ) from error

        if result <= 0:
            raise AndroidInstallError(
                "fastboot returned a non-positive "
                f"partition size for {partition!r}: "
                f"{result}"
            )

        return result

    def _run_visible(
        self,
        command: list[str],
        *,
        environment: dict[str, str] | None = None,
        description: str,
    ) -> None:
        print()
        print(f"--- {description} ---")

        completed = subprocess.run(
            tuple(command),
            env=environment,
            check=False,
        )

        if completed.returncode != 0:
            raise AndroidInstallError(
                f"{description} failed with "
                f"exit status {completed.returncode}"
            )

    def _link_runtime_artifact(
        self,
        *,
        runtime_root: Path,
        relative_name: str,
        source: Path,
    ) -> None:
        target = (
            runtime_root
            / relative_name
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if target.exists():
            if (
                target.resolve()
                != source.resolve()
            ):
                raise AndroidInstallError(
                    "runtime product output contains "
                    "conflicting artifact identity for "
                    f"{relative_name}"
                )

            return

        target.symlink_to(
            source.resolve()
        )

    def reboot_android(
        self,
        *,
        serial: str,
    ) -> None:
        serial = self._wait_for_fastboot(
            expected_serial=serial,
        )

        self._run_visible(
            [
                str(self.fastboot),
                "-s",
                serial,
                "reboot",
            ],
            description=(
                "Rebooting to Android"
            ),
        )

    def _execute_install(
        self,
        *,
        build: AndroidInstallBuild,
        device: AndroidInstallDevice,
        fastboot_info_text: str,
        wipe_userdata: bool,
    ) -> AndroidInstallExecutionResult:
        if (
            device.slot_count != 2
            or device.current_slot
            not in {
                "a",
                "b",
            }
        ):
            raise AndroidInstallError(
                "canonical Install requires exactly "
                "two A/B slots"
            )

        primary_slot = (
            device.current_slot
        )

        serial = self.ensure_bootloader(
            serial=device.serial,
        )

        with tempfile.TemporaryDirectory(
            prefix="treeforge-install-"
        ) as temporary:
            runtime_root = Path(
                temporary
            )

            self._link_runtime_artifact(
                runtime_root=runtime_root,
                relative_name="android-info.txt",
                source=build.android_info_path,
            )

            if (
                build.super_empty_path
                is not None
            ):
                self._link_runtime_artifact(
                    runtime_root=runtime_root,
                    relative_name="super_empty.img",
                    source=build.super_empty_path,
                )

            for image in build.images:
                self._link_runtime_artifact(
                    runtime_root=runtime_root,
                    relative_name=image.image_name,
                    source=image.path,
                )

            (
                runtime_root
                / "fastboot-info.txt"
            ).write_text(
                fastboot_info_text,
                encoding="utf-8",
            )

            environment = (
                os.environ.copy()
            )

            environment[
                "ANDROID_PRODUCT_OUT"
            ] = str(
                runtime_root
            )

            command = [
                str(self.fastboot),
                "-s",
                serial,
            ]

            if wipe_userdata:
                command.append(
                    "-w"
                )

            command.extend(
                [
                    "--slot",
                    primary_slot,
                    "--skip-reboot",
                    "flashall",
                ]
            )

            self._run_visible(
                command,
                environment=environment,
                description=(
                    "TreeForge source-faithful A/B install"
                ),
            )

        #
        # --skip-reboot suppresses the terminal Android reboot.
        # The manifest's required bootloader <-> fastbootd transitions
        # remain part of the task graph.
        #
        serial = self._wait_for_fastboot(
            expected_serial=serial,
        )

        final_mode = (
            self._classify_fastboot(
                serial=serial,
            )
        )

        if final_mode not in {
            "bootloader-fastboot",
            "fastbootd",
        }:
            raise AndroidInstallError(
                "install completed but device is no longer "
                "observable in a fastboot domain"
            )

        print()
        print(
            "Source-faithful A/B task graph completed "
            "successfully."
        )
        print(
            f"Device left in: {final_mode}"
        )
        print(
            "Automatic Android reboot: NO"
        )
        print(
            "Post-install set-active: NO"
        )

        return AndroidInstallExecutionResult(
            command=tuple(command),
            returncode=0,
            final_active_slot=primary_slot,
            reboot_requested=False,
        )

    def execute(
        self,
        *,
        build: AndroidInstallBuild,
        device: AndroidInstallDevice,
        selection: AndroidInstallSelection,
        fastboot_info_text: str,
    ) -> AndroidInstallExecutionResult:
        if (
            selection.final_active_slot
            != device.current_slot
        ):
            raise AndroidInstallError(
                "canonical Install preserves the "
                "pre-install active slot"
            )

        return self._execute_install(
            build=build,
            device=device,
            fastboot_info_text=(
                fastboot_info_text
            ),
            wipe_userdata=(
                selection.wipe_userdata
            ),
        )



def _write_json(
    path: Path,
    payload: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _image_json(
    image: AndroidInstallImage,
) -> dict:
    return {
        "partition":
            image.partition,
        "image_name":
            image.image_name,
        "path":
            str(image.path),
        "size_bytes":
            image.size_bytes,
        "sha256":
            image.sha256,
        "domain":
            image.domain,
        "apply_vbmeta":
            image.apply_vbmeta,
        "slot_other":
            image.slot_other,
    }


def build_plan_payload(
    *,
    build: AndroidInstallBuild,
    device: AndroidInstallDevice,
    selection: AndroidInstallSelection,
    slot_applicability: dict[str, bool | None],
    preflight: dict,
) -> dict:
    other_slot = (
        "b"
        if device.current_slot == "a"
        else "a"
    )

    return {
        "schema_version": 1,
        "execution_policy": {
            "mode":
                "source-faithful-ab",
            "physical_slotted_images":
                "mirror-a-and-b",
            "dynamic_partition_layout":
                "source-defined",
            "dynamic_primary_slot":
                device.current_slot,
            "dynamic_secondary_slot":
                other_slot,
            "shared_super_realizations":
                (
                    1
                    if build.uses_update_super
                    else 0
                ),
            "preserve_userdata":
                not selection.wipe_userdata,
            "preserve_metadata":
                not selection.wipe_userdata,
            "automatic_post_install_set_active":
                False,
            "automatic_android_reboot":
                False,
            "independent_other_dynamic_slot_bootability":
                "not-claimed",
        },
        "preflight":
            preflight,
        "build": {
            "product_out":
                str(build.product_out),
            "fastboot_info":
                str(build.fastboot_info_path),
            "android_info":
                str(build.android_info_path),
            "target_device":
                build.target_device,
            "uses_update_super":
                build.uses_update_super,
            "userdata_fs_type":
                build.userdata_fs_type,
            "super_empty":
                (
                    str(
                        build.super_empty_path
                    )
                    if build.super_empty_path
                    is not None
                    else None
                ),
            "images": [
                _image_json(
                    image
                )
                for image in build.images
            ],
        },
        "device": {
            "serial":
                device.serial,
            "initial_mode":
                device.initial_mode,
            "final_mode":
                device.final_mode,
            "product":
                device.product,
            "current_slot":
                device.current_slot,
            "slot_count":
                device.slot_count,
            "unlocked":
                device.unlocked,
            "secure":
                device.secure,
            "snapshot_update_status":
                device.snapshot_update_status,
        },
        "selection": {
            "slot_argument":
                selection.slot_argument,
            "display_name":
                selection.display_name,
            "final_active_slot":
                selection.final_active_slot,
            "wipe_userdata":
                selection.wipe_userdata,
        },
        "slot_applicability":
            slot_applicability,
        "operations": [
            {
                "line_number":
                    operation.line_number,
                "raw":
                    operation.raw,
                "command":
                    operation.command,
                "domain":
                    operation.domain,
                "partition":
                    operation.partition,
                "image_name":
                    operation.image_name,
                "apply_vbmeta":
                    operation.apply_vbmeta,
                "slot_other":
                    operation.slot_other,
                "conditional":
                    operation.conditional,
            }
            for operation
            in build.operations
        ],
    }



def render_preflight_report(
    *,
    build: AndroidInstallBuild,
    device: AndroidInstallDevice,
    selection: AndroidInstallSelection,
    slot_applicability: dict[str, bool | None],
    preflight: dict,
) -> str:
    other_slot = (
        "b"
        if device.current_slot == "a"
        else "a"
    )

    lines = [
        "TreeForge Install Device Preflight",
        "",
        f"Product output: {build.product_out}",
        f"Target device: {build.target_device}",
        f"Fastboot manifest: {build.fastboot_info_path}",
        "",
        f"Device serial: {device.serial}",
        f"Initial mode: {device.initial_mode}",
        f"Deployment mode: {device.final_mode}",
        f"Device product: {device.product}",
        f"Current slot: {device.current_slot}",
        f"Other slot: {other_slot}",
        f"Slot count: {device.slot_count}",
        f"Unlocked: {device.unlocked}",
        f"Secure: {device.secure}",
        (
            "Snapshot update status: "
            f"{device.snapshot_update_status}"
        ),
        "",
        f"Install selection: {selection.display_name}",
        (
            "Fastboot primary slot: "
            f"{selection.slot_argument}"
        ),
        "",
        "Physical bootloader-fastboot operations:",
    ]

    for image in build.images:
        if (
            image.domain
            != "bootloader-fastboot"
        ):
            continue

        applicability = (
            slot_applicability.get(
                image.partition
            )
        )

        if (
            not image.slot_other
            and applicability is True
        ):
            destination = (
                f"{image.partition}_a + "
                f"{image.partition}_b"
            )
        elif image.slot_other:
            destination = (
                f"{image.partition}_{other_slot}"
                if applicability is True
                else image.partition
            )
        else:
            destination = (
                image.partition
            )

        lines.append(
            "  "
            f"{destination} <- "
            f"{image.image_name} "
            f"({image.size_bytes} bytes)"
        )

    lines.extend(
        [
            "",
            "Dynamic-partition operations:",
            "  Semantics: SOURCE-DEFINED",
        ]
    )

    if build.uses_update_super:
        lines.append(
            "  update-super <- super_empty.img"
        )

    for image in build.images:
        if image.domain != "fastbootd":
            continue

        applicability = (
            slot_applicability.get(
                image.partition
            )
        )

        if image.slot_other:
            destination = (
                f"{image.partition}_{other_slot}"
                if applicability is True
                else image.partition
            )

            role = (
                "source secondary"
            )

        else:
            destination = (
                f"{image.partition}_{device.current_slot}"
                if applicability is True
                else image.partition
            )

            role = (
                "source primary"
            )

        lines.append(
            "  "
            f"{destination} <- "
            f"{image.image_name} "
            f"[{role}] "
            f"({image.size_bytes} bytes)"
        )

    lines.extend(
        [
            "",
            "Projection validation:",
            "  Snapshot state safe: YES",
            (
                "  update-super operations: "
                f"{preflight['update_super_count']}"
            ),
            (
                "  Dynamic images: "
                f"{preflight['dynamic_image_count']}"
            ),
            (
                "  Dynamic primary images: "
                f"{preflight['dynamic_primary_image_count']}"
            ),
            (
                "  Dynamic secondary images: "
                f"{preflight['dynamic_secondary_image_count']}"
            ),
            "  Synthetic secondary dynamic images: 0",
            (
                "  Mirrored physical images: "
                f"{preflight['mirrored_physical_image_count']}"
            ),
            "",
            "Safety boundary:",
            "  Device is in bootloader fastboot: YES",
            "  Product identity checked: YES",
            "  Snapshot state checked: YES",
            "  Manifest denylist checked: YES",
            "  Image identities captured: YES",
            "  Dynamic graph preserved from source: YES",
            "  Synthetic full second logical slot: NO",
            "  Conditional userdata erase: OMITTED",
            "  Conditional metadata erase: OMITTED",
            "  No flash has occurred yet: YES",
            "  Explicit confirmation still required: YES",
            "  Automatic Android reboot: NO",
            "",
        ]
    )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )

