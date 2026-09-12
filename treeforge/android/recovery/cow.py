from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile

from treeforge.android.recovery.host_provider import (
    AndroidRecoveryHostProvider,
)
from treeforge.android.recovery.virtual_ab import (
    RECOVERY_ANDROID_COW_V3_CREATE_CAPABILITY,
    RecoveryHostImagePlan,
)


RECOVERY_ANDROID_COW_V3_INSPECT_CAPABILITY = (
    "android-cow-v3-inspect"
)

RECOVERY_COW_BLOCK_SIZE = 4096
RECOVERY_COW_ZERO_SOURCE_BYTES = 4096


class RecoveryHostCowRealizationError(
    RuntimeError
):
    """
    Raised when a Recovery host COW cannot be
    safely realized or independently verified.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryHostCowInspection:
    version_major: int
    version_minor: int

    block_size: int

    merge_ops: int
    data_ops: int

    replace_ops: int
    zero_ops: int
    copy_ops: int
    xor_ops: int


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryHostCowPayload:
    partition_name: str
    target_name: str
    target_slot: str

    target_image_path: Path
    target_image_bytes: int
    target_image_sha256: str

    cow_path: Path
    cow_bytes: int
    cow_sha256: str

    compression: str

    create_snapshot_provider_sha256: str
    inspect_cow_provider_sha256: str

    create_snapshot_log: Path
    inspect_cow_log: Path

    inspection: RecoveryHostCowInspection


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


def _resolve_package_image(
    plan: RecoveryHostImagePlan,
    *,
    package_root: Path,
) -> Path:
    package_root = (
        package_root
        .expanduser()
        .resolve()
    )

    relative = PurePosixPath(
        plan.image.path
    )

    if (
        relative.is_absolute()
        or ".." in relative.parts
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery Install Set image path must "
            "remain relative to the package root"
        )

    source = package_root.joinpath(
        *relative.parts
    )

    try:
        source = source.resolve(
            strict=True
        )
    except FileNotFoundError as error:
        raise RecoveryHostCowRealizationError(
            "Recovery target image is unavailable: "
            f"{source}"
        ) from error

    try:
        source.relative_to(
            package_root
        )
    except ValueError as error:
        raise RecoveryHostCowRealizationError(
            "Recovery target image escaped "
            "the package root"
        ) from error

    if not source.is_file():
        raise RecoveryHostCowRealizationError(
            "Recovery target image is not "
            f"a regular file: {source}"
        )

    actual_bytes = source.stat().st_size

    if actual_bytes != plan.image.source_bytes:
        raise RecoveryHostCowRealizationError(
            "Recovery target image size changed "
            "before COW realization: "
            f"expected={plan.image.source_bytes}, "
            f"actual={actual_bytes}"
        )

    actual_sha256 = _file_sha256(
        source
    )

    if actual_sha256 != plan.image.sha256:
        raise RecoveryHostCowRealizationError(
            "Recovery target image identity changed "
            "before COW realization: "
            f"expected={plan.image.sha256}, "
            f"actual={actual_sha256}"
        )

    return source


def _inspection_integer(
    text: str,
    label: str,
) -> int:
    matches = re.findall(
        rf"(?m)^{re.escape(label)}:\s+(\d+)\s*$",
        text,
    )

    if len(matches) != 1:
        raise RecoveryHostCowRealizationError(
            "inspect_cow did not publish exactly "
            f"one {label!r} field"
        )

    return int(
        matches[0]
    )


def _parse_inspect_cow(
    text: str,
) -> RecoveryHostCowInspection:
    versions = re.findall(
        r"(?m)^Version:\s+(\d+)\.(\d+)\s*$",
        text,
    )

    if len(versions) != 1:
        raise RecoveryHostCowRealizationError(
            "inspect_cow did not publish exactly "
            "one COW version"
        )

    version_major = int(
        versions[0][0]
    )
    version_minor = int(
        versions[0][1]
    )

    inspection = RecoveryHostCowInspection(
        version_major=version_major,
        version_minor=version_minor,
        block_size=_inspection_integer(
            text,
            "Block size",
        ),
        merge_ops=_inspection_integer(
            text,
            "Merge ops",
        ),
        data_ops=_inspection_integer(
            text,
            "Data ops",
        ),
        replace_ops=_inspection_integer(
            text,
            "Replace ops",
        ),
        zero_ops=_inspection_integer(
            text,
            "Zero ops",
        ),
        copy_ops=_inspection_integer(
            text,
            "Copy ops",
        ),
        xor_ops=_inspection_integer(
            text,
            "Xor ops",
        ),
    )

    return inspection


def _validate_inspection(
    inspection: RecoveryHostCowInspection,
) -> None:
    if (
        inspection.version_major,
        inspection.version_minor,
    ) != (
        3,
        0,
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery generated an unsupported "
            "COW version: "
            f"{inspection.version_major}."
            f"{inspection.version_minor}"
        )

    if (
        inspection.block_size
        != RECOVERY_COW_BLOCK_SIZE
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery generated an unexpected "
            "COW block size: "
            f"{inspection.block_size}"
        )

    if inspection.merge_ops != 0:
        raise RecoveryHostCowRealizationError(
            "new Recovery COW unexpectedly "
            "contains merge operations"
        )

    if inspection.copy_ops != 0:
        raise RecoveryHostCowRealizationError(
            "Recovery zero-source COW contains "
            "source-dependent COPY operations"
        )

    if inspection.xor_ops != 0:
        raise RecoveryHostCowRealizationError(
            "Recovery zero-source COW contains "
            "source-dependent XOR operations"
        )

    expected_data_ops = (
        inspection.replace_ops
        + inspection.zero_ops
        + inspection.copy_ops
        + inspection.xor_ops
    )

    if (
        inspection.data_ops
        != expected_data_ops
    ):
        raise RecoveryHostCowRealizationError(
            "inspect_cow data-operation accounting "
            "is inconsistent: "
            f"data={inspection.data_ops}, "
            f"accounted={expected_data_ops}"
        )


def realize_recovery_snapshot_cow(
    plan: RecoveryHostImagePlan,
    *,
    package_root: Path,
    output_root: Path,
    create_snapshot_provider: (
        AndroidRecoveryHostProvider
    ),
    inspect_cow_provider: (
        AndroidRecoveryHostProvider
    ),
    compression: str = "lz4",
) -> RecoveryHostCowPayload:
    """
    Realize and independently validate one
    Recovery Virtual A/B COW payload.

    This function is host-only and performs no
    device write, LP mutation, snapshot mapping,
    or slot activation.
    """

    if not isinstance(
        plan,
        RecoveryHostImagePlan,
    ):
        raise TypeError(
            "plan must be a RecoveryHostImagePlan"
        )

    if not plan.snapshot_required:
        raise RecoveryHostCowRealizationError(
            "Recovery COW realization requires "
            "a snapshot-cow image plan"
        )

    if (
        plan.target.target_type
        != "logical"
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery COW realization requires "
            "a logical target"
        )

    if plan.target.slot not in {
        "a",
        "b",
    }:
        raise RecoveryHostCowRealizationError(
            "Recovery COW target slot is unresolved"
        )

    if (
        plan.image.image_format
        != "raw"
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery COW realization currently "
            "requires an expanded RAW image; "
            f"got {plan.image.image_format!r}"
        )

    if (
        plan.image.expanded_bytes
        != plan.image.source_bytes
    ):
        raise RecoveryHostCowRealizationError(
            "RAW Recovery COW target has "
            "inconsistent source/expanded size"
        )

    if (
        plan.image.expanded_bytes
        % RECOVERY_COW_BLOCK_SIZE
        != 0
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery COW target size must be "
            "4096-byte aligned"
        )

    if (
        not isinstance(
            create_snapshot_provider,
            AndroidRecoveryHostProvider,
        )
        or not (
            create_snapshot_provider.supports(
                RECOVERY_ANDROID_COW_V3_CREATE_CAPABILITY
            )
        )
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery create_snapshot provider "
            "does not satisfy "
            f"{RECOVERY_ANDROID_COW_V3_CREATE_CAPABILITY}"
        )

    if (
        not isinstance(
            inspect_cow_provider,
            AndroidRecoveryHostProvider,
        )
        or not (
            inspect_cow_provider.supports(
                RECOVERY_ANDROID_COW_V3_INSPECT_CAPABILITY
            )
        )
    ):
        raise RecoveryHostCowRealizationError(
            "Recovery inspect_cow provider "
            "does not satisfy "
            f"{RECOVERY_ANDROID_COW_V3_INSPECT_CAPABILITY}"
        )

    if (
        not isinstance(compression, str)
        or not compression
    ):
        raise ValueError(
            "compression must be a non-empty string"
        )

    target_image = _resolve_package_image(
        plan,
        package_root=package_root,
    )

    output_root = (
        output_root
        .expanduser()
        .resolve()
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        output_root
        / f"{plan.target.name}.patch"
    )

    create_log = (
        output_root
        / f"{plan.target.name}.create_snapshot.txt"
    )

    inspect_log = (
        output_root
        / f"{plan.target.name}.inspect_cow.txt"
    )

    with tempfile.TemporaryDirectory(
        prefix=(
            f".{plan.target.name}-cow-"
        ),
        dir=output_root,
    ) as temporary:
        temporary_root = Path(
            temporary
        )

        zero_source = (
            temporary_root
            / "zero-source.img"
        )

        zero_source.write_bytes(
            bytes(
                RECOVERY_COW_ZERO_SOURCE_BYTES
            )
        )

        create_completed = subprocess.run(
            [
                str(
                    create_snapshot_provider.executable_for(
                    "android-cow-v3-create"
                )
                ),
                (
                    "--source="
                    f"{zero_source}"
                ),
                (
                    "--target="
                    f"{target_image}"
                ),
                (
                    "--compression="
                    f"{compression}"
                ),
            ],
            cwd=temporary_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        create_log.write_text(
            create_completed.stdout,
            encoding="utf-8",
        )

        if create_completed.returncode != 0:
            raise RecoveryHostCowRealizationError(
                "create_snapshot failed for "
                f"{plan.target.name}: "
                f"status={create_completed.returncode}"
            )

        generated = (
            temporary_root
            / f"{target_image.stem}.patch"
        )

        if not generated.is_file():
            raise RecoveryHostCowRealizationError(
                "create_snapshot did not produce "
                f"the expected COW payload: {generated}"
            )

        if generated.stat().st_size <= 0:
            raise RecoveryHostCowRealizationError(
                "create_snapshot produced "
                "an empty COW payload"
            )

        inspect_completed = subprocess.run(
            [
                str(
                    inspect_cow_provider.executable_for(
                    "android-cow-v3-inspect"
                )
                ),
                str(
                    generated
                ),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        inspect_log.write_text(
            inspect_completed.stdout,
            encoding="utf-8",
        )

        if inspect_completed.returncode != 0:
            raise RecoveryHostCowRealizationError(
                "inspect_cow rejected generated "
                f"COW for {plan.target.name}: "
                f"status={inspect_completed.returncode}"
            )

        inspection = _parse_inspect_cow(
            inspect_completed.stdout
        )

        _validate_inspection(
            inspection
        )

        generated.replace(
            destination
        )

    cow_bytes = destination.stat().st_size
    cow_sha256 = _file_sha256(
        destination
    )

    return RecoveryHostCowPayload(
        partition_name=(
            plan.image.partition_name
        ),
        target_name=plan.target.name,
        target_slot=plan.target.slot,
        target_image_path=target_image,
        target_image_bytes=(
            plan.image.source_bytes
        ),
        target_image_sha256=(
            plan.image.sha256
        ),
        cow_path=destination,
        cow_bytes=cow_bytes,
        cow_sha256=cow_sha256,
        compression=compression,
        create_snapshot_provider_sha256=(
            create_snapshot_provider
            .content_sha256
        ),
        inspect_cow_provider_sha256=(
            inspect_cow_provider
            .content_sha256
        ),
        create_snapshot_log=create_log,
        inspect_cow_log=inspect_log,
        inspection=inspection,
    )


__all__ = (
    "RECOVERY_ANDROID_COW_V3_INSPECT_CAPABILITY",
    "RECOVERY_COW_BLOCK_SIZE",
    "RECOVERY_COW_ZERO_SOURCE_BYTES",
    "RecoveryHostCowInspection",
    "RecoveryHostCowPayload",
    "RecoveryHostCowRealizationError",
    "realize_recovery_snapshot_cow",
)
