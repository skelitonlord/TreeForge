from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.recovery.device_state import (
    RecoveryDeviceFlashTarget,
    RecoveryDeviceState,
)
from treeforge.android.recovery.install_set import (
    RecoveryInstallSetImage,
    RecoveryInstallSetPackage,
)


RECOVERY_ANDROID_COW_V3_CREATE_CAPABILITY = (
    "android-cow-v3-create"
)


class RecoveryHostInstallMethod(
    StrEnum,
):
    PHYSICAL_DIRECT = "physical-direct"
    LOGICAL_DIRECT = "logical-direct"
    SNAPSHOT_COW = "snapshot-cow"


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryHostImagePlan:
    image: RecoveryInstallSetImage
    target: RecoveryDeviceFlashTarget

    method: RecoveryHostInstallMethod

    required_host_capability: str | None

    @property
    def snapshot_required(
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
class RecoveryHostInstallPlan:
    target_slot: str
    active_slot: str

    virtual_ab: bool

    images: tuple[
        RecoveryHostImagePlan,
        ...,
    ]

    @property
    def snapshot_images(
        self,
    ) -> tuple[
        RecoveryHostImagePlan,
        ...,
    ]:
        return tuple(
            image
            for image in self.images
            if image.snapshot_required
        )


def plan_recovery_host_install(
    package: RecoveryInstallSetPackage,
    *,
    device: RecoveryDeviceState,
) -> RecoveryHostInstallPlan:
    if not isinstance(
        package,
        RecoveryInstallSetPackage,
    ):
        raise TypeError(
            "package must be a "
            "RecoveryInstallSetPackage"
        )

    if not isinstance(
        device,
        RecoveryDeviceState,
    ):
        raise TypeError(
            "device must be a RecoveryDeviceState"
        )

    if package.target_slot == device.active_slot:
        raise RuntimeError(
            "Recovery host planning refuses "
            "the active slot"
        )

    planned_images: list[
        RecoveryHostImagePlan
    ] = []

    for image in package.images:
        target = device.target_for(
            canonical_name=(
                image.partition_name
            ),
            slot=package.target_slot,
        )

        if target is None:
            raise RuntimeError(
                "Recovery did not publish a live "
                "target for Install Set image: "
                f"{image.partition_name}_"
                f"{package.target_slot}"
            )

        if target.active:
            raise RuntimeError(
                "Recovery host planning resolved "
                "an active target unexpectedly: "
                f"{target.name}"
            )

        if not target.selectable:
            raise RuntimeError(
                "Recovery host planning resolved "
                "a non-selectable target: "
                f"{target.name}"
            )

        if target.policy != "normal":
            raise RuntimeError(
                "Recovery host planning refuses "
                "target policy "
                f"{target.policy!r}: "
                f"{target.name}"
            )

        if target.target_type == "physical":
            if (
                image.expanded_bytes
                > target.capacity_bytes
            ):
                raise RuntimeError(
                    "Recovery physical target "
                    "capacity is insufficient: "
                    f"{target.name}: "
                    f"image={image.expanded_bytes}, "
                    f"capacity={target.capacity_bytes}"
                )

            method = (
                RecoveryHostInstallMethod
                .PHYSICAL_DIRECT
            )

            capability = None

        elif target.target_type == "logical":
            if (
                device.virtual_ab
            ):
                if (
                    not device.super_found
                    or not device.lp_resolved
                    or not (
                        device
                        .lp_authoritative_valid
                    )
                ):
                    raise RuntimeError(
                        "Recovery Virtual A/B "
                        "planning requires resolved "
                        "authoritative LP metadata"
                    )

                method = (
                    RecoveryHostInstallMethod
                    .SNAPSHOT_COW
                )

                capability = (
                    RECOVERY_ANDROID_COW_V3_CREATE_CAPABILITY
                )

            else:
                if (
                    not target.allocated
                    or image.expanded_bytes
                        > target.capacity_bytes
                ):
                    raise RuntimeError(
                        "Recovery logical target "
                        "requires allocation/resize "
                        "that is not available through "
                        "the direct writer: "
                        f"{target.name}"
                    )

                method = (
                    RecoveryHostInstallMethod
                    .LOGICAL_DIRECT
                )

                capability = None

        else:
            raise RuntimeError(
                "Recovery published an unsupported "
                "target type: "
                f"{target.target_type!r}"
            )

        planned_images.append(
            RecoveryHostImagePlan(
                image=image,
                target=target,
                method=method,
                required_host_capability=(
                    capability
                ),
            )
        )

    return RecoveryHostInstallPlan(
        target_slot=package.target_slot,
        active_slot=device.active_slot,
        virtual_ab=device.virtual_ab,
        images=tuple(
            planned_images
        ),
    )


__all__ = (
    "RECOVERY_ANDROID_COW_V3_CREATE_CAPABILITY",
    "RecoveryHostImagePlan",
    "RecoveryHostInstallMethod",
    "RecoveryHostInstallPlan",
    "plan_recovery_host_install",
)
