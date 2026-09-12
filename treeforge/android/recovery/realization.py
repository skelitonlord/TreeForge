from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.recovery.cow import (
    RecoveryHostCowPayload,
    realize_recovery_snapshot_cow,
)
from treeforge.android.recovery.host_provider import (
    AndroidRecoveryHostProvider,
)
from treeforge.android.recovery.install_set import (
    RecoveryInstallSetImage,
    inspect_recovery_image,
)
from treeforge.android.recovery.virtual_ab import (
    RecoveryHostImagePlan,
    RecoveryHostInstallMethod,
    RecoveryHostInstallPlan,
)


class RecoveryHostInstallRealizationError(
    RuntimeError
):
    """
    Raised when a planned Recovery host install
    cannot be safely realized.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryHostRealizedImage:
    partition_name: str
    target_name: str
    target_slot: str

    method: RecoveryHostInstallMethod

    source_image_path: Path
    source_image_bytes: int
    source_image_sha256: str

    payload_kind: str
    payload_path: Path
    payload_bytes: int
    payload_sha256: str

    cow_payload: RecoveryHostCowPayload | None

    def __post_init__(self) -> None:
        if not self.partition_name:
            raise ValueError(
                "realized Recovery partition "
                "name cannot be empty"
            )

        if not self.target_name:
            raise ValueError(
                "realized Recovery target "
                "name cannot be empty"
            )

        if self.target_slot not in {
            "a",
            "b",
        }:
            raise ValueError(
                "realized Recovery target slot "
                "must be a or b"
            )

        if self.source_image_bytes <= 0:
            raise ValueError(
                "realized Recovery source image "
                "must not be empty"
            )

        if self.payload_bytes <= 0:
            raise ValueError(
                "realized Recovery payload "
                "must not be empty"
            )

        if self.payload_kind not in {
            "image",
            "cow",
        }:
            raise ValueError(
                "unsupported Recovery realized "
                f"payload kind: {self.payload_kind!r}"
            )

        if (
            self.method
            == RecoveryHostInstallMethod.SNAPSHOT_COW
        ):
            if (
                self.payload_kind != "cow"
                or self.cow_payload is None
            ):
                raise ValueError(
                    "snapshot-cow realization "
                    "must contain a COW payload"
                )

        else:
            if (
                self.payload_kind != "image"
                or self.cow_payload is not None
            ):
                raise ValueError(
                    "direct Recovery realization "
                    "must retain the original image"
                )

    @property
    def is_snapshot_cow(
        self,
    ) -> bool:
        return (
            self.method
            == RecoveryHostInstallMethod.SNAPSHOT_COW
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryHostInstallRealization:
    active_slot: str
    target_slot: str

    virtual_ab: bool

    images: tuple[
        RecoveryHostRealizedImage,
        ...,
    ]

    def __post_init__(self) -> None:
        if self.active_slot not in {
            "a",
            "b",
        }:
            raise ValueError(
                "Recovery realization active slot "
                "must be a or b"
            )

        if self.target_slot not in {
            "a",
            "b",
        }:
            raise ValueError(
                "Recovery realization target slot "
                "must be a or b"
            )

        if self.active_slot == self.target_slot:
            raise ValueError(
                "Recovery realization cannot "
                "target the active slot"
            )

        if not self.images:
            raise ValueError(
                "Recovery realization must contain "
                "at least one image"
            )

        targets = tuple(
            image.target_name
            for image in self.images
        )

        if len(targets) != len(set(targets)):
            raise ValueError(
                "Recovery realization contains "
                "duplicate target identities"
            )

    @property
    def snapshot_images(
        self,
    ) -> tuple[
        RecoveryHostRealizedImage,
        ...,
    ]:
        return tuple(
            image
            for image in self.images
            if image.is_snapshot_cow
        )

    @property
    def direct_images(
        self,
    ) -> tuple[
        RecoveryHostRealizedImage,
        ...,
    ]:
        return tuple(
            image
            for image in self.images
            if not image.is_snapshot_cow
        )


def _resolve_verified_package_image(
    plan: RecoveryHostImagePlan,
    *,
    package_root: Path,
) -> tuple[
    Path,
    RecoveryInstallSetImage,
]:
    package_root = (
        package_root
        .expanduser()
        .resolve()
    )

    if not package_root.is_dir():
        raise RecoveryHostInstallRealizationError(
            "Recovery package root is unavailable: "
            f"{package_root}"
        )

    relative = PurePosixPath(
        plan.image.path
    )

    if (
        relative.is_absolute()
        or ".." in relative.parts
    ):
        raise RecoveryHostInstallRealizationError(
            "Recovery Install Set image path must "
            "remain relative to its package root"
        )

    image_path = package_root.joinpath(
        *relative.parts
    )

    try:
        image_path = image_path.resolve(
            strict=True
        )
    except FileNotFoundError as error:
        raise RecoveryHostInstallRealizationError(
            "Recovery Install Set image is "
            f"unavailable: {image_path}"
        ) from error

    try:
        image_path.relative_to(
            package_root
        )
    except ValueError as error:
        raise RecoveryHostInstallRealizationError(
            "Recovery Install Set image escaped "
            "its package root"
        ) from error

    if not image_path.is_file():
        raise RecoveryHostInstallRealizationError(
            "Recovery Install Set image is not "
            f"a regular file: {image_path}"
        )

    inspected = inspect_recovery_image(
        image_path
    )

    checks = (
        (
            "image_format",
            plan.image.image_format,
            inspected.image_format,
        ),
        (
            "source_bytes",
            plan.image.source_bytes,
            inspected.source_bytes,
        ),
        (
            "expanded_bytes",
            plan.image.expanded_bytes,
            inspected.expanded_bytes,
        ),
        (
            "sha256",
            plan.image.sha256,
            inspected.sha256,
        ),
        (
            "block_size",
            plan.image.block_size,
            inspected.block_size,
        ),
        (
            "total_blocks",
            plan.image.total_blocks,
            inspected.total_blocks,
        ),
        (
            "total_chunks",
            plan.image.total_chunks,
            inspected.total_chunks,
        ),
        (
            "raw_chunks",
            plan.image.raw_chunks,
            inspected.raw_chunks,
        ),
        (
            "fill_chunks",
            plan.image.fill_chunks,
            inspected.fill_chunks,
        ),
        (
            "dont_care_chunks",
            plan.image.dont_care_chunks,
            inspected.dont_care_chunks,
        ),
        (
            "crc32_chunks",
            plan.image.crc32_chunks,
            inspected.crc32_chunks,
        ),
    )

    for (
        field_name,
        expected,
        actual,
    ) in checks:
        if actual != expected:
            raise RecoveryHostInstallRealizationError(
                "Recovery Install Set image changed "
                "before host realization: "
                f"{plan.image.partition_name}: "
                f"{field_name}: "
                f"expected={expected!r}, "
                f"actual={actual!r}"
            )

    return (
        image_path,
        inspected,
    )


def realize_recovery_host_install(
    plan: RecoveryHostInstallPlan,
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
) -> RecoveryHostInstallRealization:
    """
    Realize one complete Recovery host install plan.

    Direct targets retain their verified original
    image bytes.

    Virtual A/B logical targets are converted into
    independently verified COW payloads.

    This function performs no device communication,
    partition write, LP mutation, snapshot mapping,
    or slot activation.
    """

    if not isinstance(
        plan,
        RecoveryHostInstallPlan,
    ):
        raise TypeError(
            "plan must be a RecoveryHostInstallPlan"
        )

    package_root = (
        package_root
        .expanduser()
        .resolve()
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

    realized_images: list[
        RecoveryHostRealizedImage
    ] = []

    for image_plan in plan.images:
        source_path, inspected = (
            _resolve_verified_package_image(
                image_plan,
                package_root=package_root,
            )
        )

        if image_plan.snapshot_required:
            cow = realize_recovery_snapshot_cow(
                image_plan,
                package_root=package_root,
                output_root=(
                    output_root
                    / "cow"
                ),
                create_snapshot_provider=(
                    create_snapshot_provider
                ),
                inspect_cow_provider=(
                    inspect_cow_provider
                ),
                compression=compression,
            )

            realized = RecoveryHostRealizedImage(
                partition_name=(
                    image_plan.image.partition_name
                ),
                target_name=(
                    image_plan.target.name
                ),
                target_slot=plan.target_slot,
                method=image_plan.method,
                source_image_path=(
                    source_path
                ),
                source_image_bytes=(
                    inspected.source_bytes
                ),
                source_image_sha256=(
                    inspected.sha256
                ),
                payload_kind="cow",
                payload_path=(
                    cow.cow_path
                ),
                payload_bytes=(
                    cow.cow_bytes
                ),
                payload_sha256=(
                    cow.cow_sha256
                ),
                cow_payload=cow,
            )

        else:
            realized = RecoveryHostRealizedImage(
                partition_name=(
                    image_plan.image.partition_name
                ),
                target_name=(
                    image_plan.target.name
                ),
                target_slot=plan.target_slot,
                method=image_plan.method,
                source_image_path=(
                    source_path
                ),
                source_image_bytes=(
                    inspected.source_bytes
                ),
                source_image_sha256=(
                    inspected.sha256
                ),
                payload_kind="image",
                payload_path=(
                    source_path
                ),
                payload_bytes=(
                    inspected.source_bytes
                ),
                payload_sha256=(
                    inspected.sha256
                ),
                cow_payload=None,
            )

        realized_images.append(
            realized
        )

    return RecoveryHostInstallRealization(
        active_slot=plan.active_slot,
        target_slot=plan.target_slot,
        virtual_ab=plan.virtual_ab,
        images=tuple(
            realized_images
        ),
    )


__all__ = (
    "RecoveryHostInstallRealization",
    "RecoveryHostInstallRealizationError",
    "RecoveryHostRealizedImage",
    "realize_recovery_host_install",
)
