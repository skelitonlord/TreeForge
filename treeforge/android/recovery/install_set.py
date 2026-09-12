from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from hashlib import sha256
import json
from pathlib import Path
import shutil
import struct


RECOVERY_INSTALL_SET_HOST_SCHEMA = (
    "treeforge-recovery-install-set-host-v1"
)

RECOVERY_INSTALL_SET_WIRE_SCHEMA = (
    "treeforge-recovery-install-set-v1"
)

ANDROID_SPARSE_MAGIC = 0xED26FF3A
ANDROID_SPARSE_MAJOR_VERSION = 1

ANDROID_SPARSE_FILE_HEADER_SIZE = 28
ANDROID_SPARSE_CHUNK_HEADER_SIZE = 12

ANDROID_SPARSE_CHUNK_RAW = 0xCAC1
ANDROID_SPARSE_CHUNK_FILL = 0xCAC2
ANDROID_SPARSE_CHUNK_DONT_CARE = 0xCAC3
ANDROID_SPARSE_CHUNK_CRC32 = 0xCAC4


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryInstallSetImage:
    partition_name: str
    path: str

    image_format: str

    source_bytes: int
    expanded_bytes: int

    sha256: str

    block_size: int
    total_blocks: int
    total_chunks: int

    raw_chunks: int
    fill_chunks: int
    dont_care_chunks: int
    crc32_chunks: int


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryInstallSetPackage:
    schema: str
    image_set: str
    target_slot: str

    recovery_manifest: str

    images: tuple[
        RecoveryInstallSetImage,
        ...,
    ]


def _file_sha256(
    path: Path,
) -> str:
    digest = sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _validate_partition_name(
    value: str,
) -> str:
    if not value:
        raise ValueError(
            "Recovery install-set partition "
            "name cannot be empty"
        )

    if any(
        not (
            "a" <= character <= "z"
            or "0" <= character <= "9"
            or character == "_"
        )
        for character in value
    ):
        raise ValueError(
            "Recovery install-set partition "
            "name must contain only lowercase "
            "letters, digits, and underscores: "
            f"{value!r}"
        )

    return value


def inspect_recovery_image(
    path: Path,
) -> RecoveryInstallSetImage:
    path = (
        path
        .expanduser()
        .resolve()
    )

    if not path.is_file():
        raise FileNotFoundError(
            f"Recovery image does not exist: {path}"
        )

    source_bytes = (
        path.stat().st_size
    )

    if source_bytes <= 0:
        raise ValueError(
            f"Recovery image is empty: {path}"
        )

    digest = _file_sha256(
        path
    )

    with path.open("rb") as stream:
        initial = stream.read(
            ANDROID_SPARSE_FILE_HEADER_SIZE
        )

        if len(initial) < 4:
            return RecoveryInstallSetImage(
                partition_name="",
                path=str(path),
                image_format="raw",
                source_bytes=source_bytes,
                expanded_bytes=source_bytes,
                sha256=digest,
                block_size=0,
                total_blocks=0,
                total_chunks=0,
                raw_chunks=0,
                fill_chunks=0,
                dont_care_chunks=0,
                crc32_chunks=0,
            )

        magic = struct.unpack_from(
            "<I",
            initial,
            0,
        )[0]

        if magic != ANDROID_SPARSE_MAGIC:
            return RecoveryInstallSetImage(
                partition_name="",
                path=str(path),
                image_format="raw",
                source_bytes=source_bytes,
                expanded_bytes=source_bytes,
                sha256=digest,
                block_size=0,
                total_blocks=0,
                total_chunks=0,
                raw_chunks=0,
                fill_chunks=0,
                dont_care_chunks=0,
                crc32_chunks=0,
            )

        if (
            len(initial)
            != ANDROID_SPARSE_FILE_HEADER_SIZE
        ):
            raise ValueError(
                "truncated Android sparse header: "
                f"{path}"
            )

        (
            _magic,
            major_version,
            _minor_version,
            file_header_size,
            chunk_header_size,
            block_size,
            total_blocks,
            total_chunks,
            _image_checksum,
        ) = struct.unpack(
            "<IHHHHIIII",
            initial,
        )

        if (
            major_version
            != ANDROID_SPARSE_MAJOR_VERSION
        ):
            raise ValueError(
                "unsupported Android sparse "
                f"major version {major_version}: "
                f"{path}"
            )

        if (
            file_header_size
            < ANDROID_SPARSE_FILE_HEADER_SIZE
        ):
            raise ValueError(
                "invalid Android sparse file "
                f"header size: {path}"
            )

        if (
            chunk_header_size
            < ANDROID_SPARSE_CHUNK_HEADER_SIZE
        ):
            raise ValueError(
                "invalid Android sparse chunk "
                f"header size: {path}"
            )

        if (
            block_size <= 0
            or block_size % 4 != 0
        ):
            raise ValueError(
                "invalid Android sparse block "
                f"size: {path}"
            )

        if (
            total_blocks <= 0
            or total_chunks <= 0
        ):
            raise ValueError(
                "invalid Android sparse block/"
                f"chunk counts: {path}"
            )

        stream.seek(
            file_header_size
        )

        raw_chunks = 0
        fill_chunks = 0
        dont_care_chunks = 0
        crc32_chunks = 0

        output_blocks = 0

        for _index in range(
            total_chunks
        ):
            header = stream.read(
                chunk_header_size
            )

            if len(header) != chunk_header_size:
                raise ValueError(
                    "truncated Android sparse "
                    f"chunk header: {path}"
                )

            (
                chunk_type,
                _reserved,
                chunk_blocks,
                total_size,
            ) = struct.unpack_from(
                "<HHII",
                header,
                0,
            )

            if (
                total_size
                < chunk_header_size
            ):
                raise ValueError(
                    "invalid Android sparse "
                    f"chunk size: {path}"
                )

            payload_size = (
                total_size
                - chunk_header_size
            )

            if (
                chunk_type
                == ANDROID_SPARSE_CHUNK_RAW
            ):
                expected = (
                    chunk_blocks
                    * block_size
                )

                if (
                    payload_size
                    != expected
                ):
                    raise ValueError(
                        "invalid Android sparse "
                        f"RAW chunk: {path}"
                    )

                raw_chunks += 1
                output_blocks += (
                    chunk_blocks
                )

            elif (
                chunk_type
                == ANDROID_SPARSE_CHUNK_FILL
            ):
                if payload_size != 4:
                    raise ValueError(
                        "invalid Android sparse "
                        f"FILL chunk: {path}"
                    )

                fill_chunks += 1
                output_blocks += (
                    chunk_blocks
                )

            elif (
                chunk_type
                == ANDROID_SPARSE_CHUNK_DONT_CARE
            ):
                if payload_size != 0:
                    raise ValueError(
                        "invalid Android sparse "
                        f"DONT_CARE chunk: {path}"
                    )

                dont_care_chunks += 1
                output_blocks += (
                    chunk_blocks
                )

            elif (
                chunk_type
                == ANDROID_SPARSE_CHUNK_CRC32
            ):
                if (
                    payload_size != 4
                    or chunk_blocks != 0
                ):
                    raise ValueError(
                        "invalid Android sparse "
                        f"CRC32 chunk: {path}"
                    )

                crc32_chunks += 1

            else:
                raise ValueError(
                    "unsupported Android sparse "
                    f"chunk type 0x{chunk_type:04x}: "
                    f"{path}"
                )

            stream.seek(
                payload_size,
                1,
            )

        if (
            output_blocks
            != total_blocks
        ):
            raise ValueError(
                "Android sparse output block "
                f"count mismatch: {path}"
            )

        if (
            stream.tell()
            != source_bytes
        ):
            raise ValueError(
                "Android sparse image has "
                f"trailing bytes: {path}"
            )

    return RecoveryInstallSetImage(
        partition_name="",
        path=str(path),
        image_format="android-sparse",
        source_bytes=source_bytes,
        expanded_bytes=(
            total_blocks
            * block_size
        ),
        sha256=digest,
        block_size=block_size,
        total_blocks=total_blocks,
        total_chunks=total_chunks,
        raw_chunks=raw_chunks,
        fill_chunks=fill_chunks,
        dont_care_chunks=dont_care_chunks,
        crc32_chunks=crc32_chunks,
    )


def _wire_manifest_text(
    *,
    target_slot: str,
    images: tuple[
        RecoveryInstallSetImage,
        ...,
    ],
) -> str:
    lines = [
        RECOVERY_INSTALL_SET_WIRE_SCHEMA,
        f"target_slot={target_slot}",
        f"image_count={len(images)}",
    ]

    for image in images:
        lines.extend(
            (
                f"image={image.partition_name}",
                f"format={image.image_format}",
                f"bytes={image.source_bytes}",
                (
                    "expanded_bytes="
                    f"{image.expanded_bytes}"
                ),
                f"sha256={image.sha256}",
                f"block_size={image.block_size}",
                (
                    "total_blocks="
                    f"{image.total_blocks}"
                ),
                (
                    "total_chunks="
                    f"{image.total_chunks}"
                ),
                (
                    "raw_chunks="
                    f"{image.raw_chunks}"
                ),
                (
                    "fill_chunks="
                    f"{image.fill_chunks}"
                ),
                (
                    "dont_care_chunks="
                    f"{image.dont_care_chunks}"
                ),
                (
                    "crc32_chunks="
                    f"{image.crc32_chunks}"
                ),
            )
        )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def build_recovery_install_set(
    deployment,
    *,
    output_root: Path,
    target_slot: str,
    image_set: str,
) -> Path:
    target_slot = (
        target_slot
        .strip()
        .lower()
    )

    if target_slot not in {
        "a",
        "b",
    }:
        raise ValueError(
            "Recovery Install Set target slot "
            "must be a or b"
        )

    output_root = (
        output_root
        .expanduser()
        .resolve()
    )

    if output_root.exists():
        shutil.rmtree(
            output_root
        )

    images_root = (
        output_root
        / "images"
    )

    images_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    packaged_images = []

    seen_names = set()

    for source_image in deployment.images:
        partition_name = (
            _validate_partition_name(
                source_image.partition_name
            )
        )

        if partition_name in seen_names:
            raise ValueError(
                "duplicate Recovery Install Set "
                f"partition: {partition_name}"
            )

        seen_names.add(
            partition_name
        )

        source_path = (
            Path(
                source_image.final_path
            )
            .expanduser()
            .resolve()
        )

        inspected = (
            inspect_recovery_image(
                source_path
            )
        )

        expected_size = getattr(
            source_image,
            "final_size_bytes",
            None,
        )

        if (
            expected_size is not None
            and inspected.source_bytes
                != expected_size
        ):
            raise RuntimeError(
                "Boot Image deployment size "
                "changed before Recovery packaging: "
                f"{partition_name}"
            )

        expected_sha256 = getattr(
            source_image,
            "final_sha256",
            None,
        )

        if (
            expected_sha256 is not None
            and inspected.sha256
                != expected_sha256
        ):
            raise RuntimeError(
                "Boot Image deployment identity "
                "changed before Recovery packaging: "
                f"{partition_name}"
            )

        destination = (
            images_root
            / f"{partition_name}.img"
        )

        shutil.copy2(
            source_path,
            destination,
        )

        packaged_images.append(
            RecoveryInstallSetImage(
                partition_name=partition_name,
                path=str(
                    destination.relative_to(
                        output_root
                    )
                ),
                image_format=(
                    inspected.image_format
                ),
                source_bytes=(
                    inspected.source_bytes
                ),
                expanded_bytes=(
                    inspected.expanded_bytes
                ),
                sha256=(
                    inspected.sha256
                ),
                block_size=(
                    inspected.block_size
                ),
                total_blocks=(
                    inspected.total_blocks
                ),
                total_chunks=(
                    inspected.total_chunks
                ),
                raw_chunks=(
                    inspected.raw_chunks
                ),
                fill_chunks=(
                    inspected.fill_chunks
                ),
                dont_care_chunks=(
                    inspected.dont_care_chunks
                ),
                crc32_chunks=(
                    inspected.crc32_chunks
                ),
            )
        )

    if not packaged_images:
        raise ValueError(
            "Recovery Install Set cannot be "
            "created without images"
        )

    images = tuple(
        packaged_images
    )

    recovery_manifest_path = (
        output_root
        / "recovery-install-set.manifest"
    )

    recovery_manifest_path.write_text(
        _wire_manifest_text(
            target_slot=target_slot,
            images=images,
        ),
        encoding="utf-8",
    )

    package = RecoveryInstallSetPackage(
        schema=(
            RECOVERY_INSTALL_SET_HOST_SCHEMA
        ),
        image_set=image_set,
        target_slot=target_slot,
        recovery_manifest=(
            recovery_manifest_path.name
        ),
        images=images,
    )

    package_path = (
        output_root
        / "install-set.json"
    )

    package_path.write_text(
        json.dumps(
            asdict(
                package
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return package_path


def load_and_verify_recovery_install_set(
    package_path: Path,
) -> RecoveryInstallSetPackage:
    package_path = (
        package_path
        .expanduser()
        .resolve()
    )

    if not package_path.is_file():
        raise FileNotFoundError(
            "Recovery Install Set not found: "
            f"{package_path}"
        )

    raw = json.loads(
        package_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        raw.get("schema")
        != RECOVERY_INSTALL_SET_HOST_SCHEMA
    ):
        raise ValueError(
            "unsupported Recovery Install Set "
            "host schema"
        )

    target_slot = raw.get(
        "target_slot"
    )

    if target_slot not in {
        "a",
        "b",
    }:
        raise ValueError(
            "Recovery Install Set has invalid "
            "target slot"
        )

    image_records = raw.get(
        "images"
    )

    if (
        not isinstance(
            image_records,
            list,
        )
        or not image_records
    ):
        raise ValueError(
            "Recovery Install Set has no images"
        )

    root = package_path.parent

    verified_images = []

    seen_names = set()

    for record in image_records:
        partition_name = (
            _validate_partition_name(
                str(
                    record[
                        "partition_name"
                    ]
                )
            )
        )

        if partition_name in seen_names:
            raise ValueError(
                "duplicate Recovery Install Set "
                f"partition: {partition_name}"
            )

        seen_names.add(
            partition_name
        )

        image_path = (
            root
            / str(
                record[
                    "path"
                ]
            )
        ).resolve()

        try:
            image_path.relative_to(
                root
            )

        except ValueError as exc:
            raise ValueError(
                "Recovery Install Set image "
                "escapes package root: "
                f"{image_path}"
            ) from exc

        inspected = (
            inspect_recovery_image(
                image_path
            )
        )

        checks = {
            "image_format":
                inspected.image_format,
            "source_bytes":
                inspected.source_bytes,
            "expanded_bytes":
                inspected.expanded_bytes,
            "sha256":
                inspected.sha256,
            "block_size":
                inspected.block_size,
            "total_blocks":
                inspected.total_blocks,
            "total_chunks":
                inspected.total_chunks,
            "raw_chunks":
                inspected.raw_chunks,
            "fill_chunks":
                inspected.fill_chunks,
            "dont_care_chunks":
                inspected.dont_care_chunks,
            "crc32_chunks":
                inspected.crc32_chunks,
        }

        for key, actual in checks.items():
            if record.get(key) != actual:
                raise RuntimeError(
                    "Recovery Install Set image "
                    "identity/metadata mismatch: "
                    f"{partition_name}: {key}"
                )

        verified_images.append(
            RecoveryInstallSetImage(
                partition_name=(
                    partition_name
                ),
                path=str(
                    image_path.relative_to(
                        root
                    )
                ),
                image_format=(
                    inspected.image_format
                ),
                source_bytes=(
                    inspected.source_bytes
                ),
                expanded_bytes=(
                    inspected.expanded_bytes
                ),
                sha256=(
                    inspected.sha256
                ),
                block_size=(
                    inspected.block_size
                ),
                total_blocks=(
                    inspected.total_blocks
                ),
                total_chunks=(
                    inspected.total_chunks
                ),
                raw_chunks=(
                    inspected.raw_chunks
                ),
                fill_chunks=(
                    inspected.fill_chunks
                ),
                dont_care_chunks=(
                    inspected.dont_care_chunks
                ),
                crc32_chunks=(
                    inspected.crc32_chunks
                ),
            )
        )

    images = tuple(
        verified_images
    )

    manifest_name = str(
        raw.get(
            "recovery_manifest",
            "",
        )
    )

    manifest_path = (
        root
        / manifest_name
    ).resolve()

    try:
        manifest_path.relative_to(
            root
        )

    except ValueError as exc:
        raise ValueError(
            "Recovery wire manifest escapes "
            "package root"
        ) from exc

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Recovery wire manifest not found: "
            f"{manifest_path}"
        )

    expected_manifest = (
        _wire_manifest_text(
            target_slot=target_slot,
            images=images,
        )
    )

    if (
        manifest_path.read_text(
            encoding="utf-8"
        )
        != expected_manifest
    ):
        raise RuntimeError(
            "Recovery wire manifest does not "
            "match verified package images"
        )

    return RecoveryInstallSetPackage(
        schema=(
            RECOVERY_INSTALL_SET_HOST_SCHEMA
        ),
        image_set=str(
            raw.get(
                "image_set",
                "unknown",
            )
        ),
        target_slot=target_slot,
        recovery_manifest=(
            manifest_name
        ),
        images=images,
    )
