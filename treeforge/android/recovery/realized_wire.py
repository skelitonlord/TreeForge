from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.recovery.install_set import (
    inspect_recovery_image,
)
from treeforge.android.recovery.realization import (
    RecoveryHostInstallRealization,
    RecoveryHostRealizedImage,
)
from treeforge.android.recovery.virtual_ab import (
    RecoveryHostInstallMethod,
)


RECOVERY_REALIZED_INSTALL_SET_WIRE_SCHEMA = (
    "treeforge-recovery-install-set-v2"
)


class RecoveryRealizedWireError(
    RuntimeError
):
    """
    Raised when a realized Recovery install cannot
    be represented safely by the v2 wire contract.
    """


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


def _verified_payload_identity(
    image: RecoveryHostRealizedImage,
) -> tuple[
    Path,
    int,
    str,
]:
    path = (
        image.payload_path
        .expanduser()
        .resolve()
    )

    if not path.is_file():
        raise RecoveryRealizedWireError(
            "realized Recovery payload is "
            f"unavailable: {path}"
        )

    actual_bytes = path.stat().st_size

    if actual_bytes != image.payload_bytes:
        raise RecoveryRealizedWireError(
            "realized Recovery payload size "
            "changed before wire serialization: "
            f"{image.partition_name}: "
            f"expected={image.payload_bytes}, "
            f"actual={actual_bytes}"
        )

    actual_sha256 = _file_sha256(
        path
    )

    if actual_sha256 != image.payload_sha256:
        raise RecoveryRealizedWireError(
            "realized Recovery payload identity "
            "changed before wire serialization: "
            f"{image.partition_name}"
        )

    return (
        path,
        actual_bytes,
        actual_sha256,
    )


def _source_image_metadata(
    image: RecoveryHostRealizedImage,
):
    source = (
        image.source_image_path
        .expanduser()
        .resolve()
    )

    if not source.is_file():
        raise RecoveryRealizedWireError(
            "realized Recovery source image is "
            f"unavailable: {source}"
        )

    inspected = inspect_recovery_image(
        source
    )

    if (
        inspected.source_bytes
        != image.source_image_bytes
        or inspected.sha256
        != image.source_image_sha256
    ):
        raise RecoveryRealizedWireError(
            "realized Recovery source image "
            "identity changed before wire "
            f"serialization: {image.partition_name}"
        )

    return inspected


def _image_wire_lines(
    image: RecoveryHostRealizedImage,
) -> tuple[str, ...]:
    inspected = _source_image_metadata(
        image
    )

    (
        _payload_path,
        payload_bytes,
        payload_sha256,
    ) = _verified_payload_identity(
        image
    )

    if image.method in {
        RecoveryHostInstallMethod.PHYSICAL_DIRECT,
        RecoveryHostInstallMethod.LOGICAL_DIRECT,
    }:
        if image.payload_kind != "image":
            raise RecoveryRealizedWireError(
                "direct Recovery realization must "
                "use an image payload"
            )

        if (
            payload_bytes
            != inspected.source_bytes
            or payload_sha256
            != inspected.sha256
        ):
            raise RecoveryRealizedWireError(
                "direct Recovery payload must "
                "preserve source image identity: "
                f"{image.partition_name}"
            )

        cow_version_major = 0
        cow_version_minor = 0
        cow_block_size = 0
        cow_merge_ops = 0
        cow_data_ops = 0
        cow_replace_ops = 0
        cow_zero_ops = 0
        cow_copy_ops = 0
        cow_xor_ops = 0
        cow_compression = "none"

    elif (
        image.method
        == RecoveryHostInstallMethod.SNAPSHOT_COW
    ):
        if (
            image.payload_kind != "cow"
            or image.cow_payload is None
        ):
            raise RecoveryRealizedWireError(
                "snapshot-cow Recovery realization "
                "must contain a COW payload"
            )

        cow = image.cow_payload
        inspection = cow.inspection

        if (
            cow.cow_path.expanduser().resolve()
            != image.payload_path.expanduser().resolve()
            or cow.cow_bytes != payload_bytes
            or cow.cow_sha256 != payload_sha256
        ):
            raise RecoveryRealizedWireError(
                "Recovery COW payload identity "
                "does not match realized payload: "
                f"{image.partition_name}"
            )

        if (
            inspection.version_major != 3
            or inspection.version_minor != 0
            or inspection.block_size != 4096
            or inspection.merge_ops != 0
            or inspection.copy_ops != 0
            or inspection.xor_ops != 0
        ):
            raise RecoveryRealizedWireError(
                "Recovery COW inspection does not "
                "satisfy the accepted v2 contract: "
                f"{image.partition_name}"
            )

        cow_version_major = (
            inspection.version_major
        )
        cow_version_minor = (
            inspection.version_minor
        )
        cow_block_size = (
            inspection.block_size
        )
        cow_merge_ops = (
            inspection.merge_ops
        )
        cow_data_ops = (
            inspection.data_ops
        )
        cow_replace_ops = (
            inspection.replace_ops
        )
        cow_zero_ops = (
            inspection.zero_ops
        )
        cow_copy_ops = (
            inspection.copy_ops
        )
        cow_xor_ops = (
            inspection.xor_ops
        )
        cow_compression = (
            cow.compression
        )

    else:
        raise RecoveryRealizedWireError(
            "unsupported Recovery realization "
            f"method: {image.method!r}"
        )

    return (
        f"image={image.partition_name}",
        f"method={image.method.value}",
        f"payload_kind={image.payload_kind}",
        f"format={inspected.image_format}",
        f"bytes={inspected.source_bytes}",
        (
            "expanded_bytes="
            f"{inspected.expanded_bytes}"
        ),
        f"sha256={inspected.sha256}",
        f"block_size={inspected.block_size}",
        (
            "total_blocks="
            f"{inspected.total_blocks}"
        ),
        (
            "total_chunks="
            f"{inspected.total_chunks}"
        ),
        (
            "raw_chunks="
            f"{inspected.raw_chunks}"
        ),
        (
            "fill_chunks="
            f"{inspected.fill_chunks}"
        ),
        (
            "dont_care_chunks="
            f"{inspected.dont_care_chunks}"
        ),
        (
            "crc32_chunks="
            f"{inspected.crc32_chunks}"
        ),
        f"payload_bytes={payload_bytes}",
        f"payload_sha256={payload_sha256}",
        (
            "cow_version_major="
            f"{cow_version_major}"
        ),
        (
            "cow_version_minor="
            f"{cow_version_minor}"
        ),
        (
            "cow_block_size="
            f"{cow_block_size}"
        ),
        f"cow_merge_ops={cow_merge_ops}",
        f"cow_data_ops={cow_data_ops}",
        (
            "cow_replace_ops="
            f"{cow_replace_ops}"
        ),
        f"cow_zero_ops={cow_zero_ops}",
        f"cow_copy_ops={cow_copy_ops}",
        f"cow_xor_ops={cow_xor_ops}",
        (
            "cow_compression="
            f"{cow_compression}"
        ),
    )


def recovery_realized_wire_text(
    realization: RecoveryHostInstallRealization,
) -> str:
    """
    Serialize a realized Recovery install as the
    v2 device wire contract.

    `bytes`, `expanded_bytes`, `sha256`, and sparse
    metadata describe the original/final partition
    image.

    `payload_bytes` and `payload_sha256` describe
    the bytes actually streamed to Recovery.

    For direct images these identities are equal.

    For snapshot-cow images they intentionally
    differ.

    No target partition name is serialized.
    Recovery must derive the concrete target from
    canonical image name, target slot, and current
    live topology.
    """

    if not isinstance(
        realization,
        RecoveryHostInstallRealization,
    ):
        raise TypeError(
            "realization must be a "
            "RecoveryHostInstallRealization"
        )

    if realization.target_slot not in {
        "a",
        "b",
    }:
        raise RecoveryRealizedWireError(
            "Recovery v2 target slot must be a or b"
        )

    if realization.active_slot == realization.target_slot:
        raise RecoveryRealizedWireError(
            "Recovery v2 manifest refuses "
            "the active slot"
        )

    if not realization.images:
        raise RecoveryRealizedWireError(
            "Recovery v2 manifest requires "
            "at least one image"
        )

    canonical_names = tuple(
        image.partition_name
        for image in realization.images
    )

    if (
        len(canonical_names)
        != len(set(canonical_names))
    ):
        raise RecoveryRealizedWireError(
            "Recovery v2 manifest contains "
            "duplicate canonical images"
        )

    lines = [
        RECOVERY_REALIZED_INSTALL_SET_WIRE_SCHEMA,
        (
            "target_slot="
            f"{realization.target_slot}"
        ),
        (
            "image_count="
            f"{len(realization.images)}"
        ),
    ]

    for image in realization.images:
        if (
            image.target_slot
            != realization.target_slot
        ):
            raise RecoveryRealizedWireError(
                "realized image target slot does "
                "not match set target slot: "
                f"{image.partition_name}"
            )

        lines.extend(
            _image_wire_lines(
                image
            )
        )

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def write_recovery_realized_wire_manifest(
    realization: RecoveryHostInstallRealization,
    *,
    path: Path,
) -> Path:
    path = (
        path
        .expanduser()
        .resolve()
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        recovery_realized_wire_text(
            realization
        ),
        encoding="utf-8",
    )

    return path


__all__ = (
    "RECOVERY_REALIZED_INSTALL_SET_WIRE_SCHEMA",
    "RecoveryRealizedWireError",
    "recovery_realized_wire_text",
    "write_recovery_realized_wire_manifest",
)
