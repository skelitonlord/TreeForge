from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeBootArchitectureProfile:
    """
    TreeForge-owned Android boot-architecture build contract.

    This model contains Android build semantics only.

    Device/factory evidence is supplied by Device Tree and interpreted
    through an Android-version-specific resolver. The profile itself must
    never require an AOSP source checkout.
    """

    profile_id: str
    android_version: str
    reference_tag: str

    first_api_level: int

    present_partitions: tuple[
        str,
        ...,
    ]

    boot_header_version: int
    init_boot_header_version: int

    uses_recovery_as_boot: bool
    uses_generic_kernel_image: bool

    move_recovery_resources_to_vendor_boot: bool
    exclude_kernel_from_recovery_image: bool
    move_gsi_avb_keys_to_vendor_boot: bool

    requires_generic_ramdisk_product: bool

    # This is intentionally distinct from vendor_boot construction.
    #
    # A standalone vendor_ramdisk.img is useful to some kernel-development
    # workflows but is not itself required merely because vendor_boot exists.
    build_standalone_vendor_ramdisk_image: bool = False

    # Optional Android recovery-build semantics.
    #
    # Platform-wide values belong in the Android-version/platform resolver.
    # Device-specific values, such as display rotation, must remain unset
    # until Device Tree can resolve them from reconstructed device evidence.
    recovery_default_rotation: str | None = None
    recovery_pixel_format: str | None = None
    recovery_ui_margin_height: int | None = None
    recovery_ui_libs: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "profile_id",
                self.profile_id,
            ),
            (
                "android_version",
                self.android_version,
            ),
            (
                "reference_tag",
                self.reference_tag,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if (
            isinstance(
                self.first_api_level,
                bool,
            )
            or not isinstance(
                self.first_api_level,
                int,
            )
            or self.first_api_level < 1
        ):
            raise ValueError(
                "first_api_level must be a positive integer"
            )

        if not isinstance(
            self.present_partitions,
            tuple,
        ):
            raise TypeError(
                "present_partitions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                str,
            )
            and item
            for item in self.present_partitions
        ):
            raise ValueError(
                "present_partitions must contain "
                "non-empty partition names"
            )

        if (
            tuple(
                sorted(
                    set(
                        self.present_partitions
                    )
                )
            )
            != self.present_partitions
        ):
            raise ValueError(
                "present_partitions must be sorted and unique"
            )

        for field_name, value in (
            (
                "boot_header_version",
                self.boot_header_version,
            ),
            (
                "init_boot_header_version",
                self.init_boot_header_version,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 1
            ):
                raise ValueError(
                    f"{field_name} must be a positive integer"
                )

        for field_name, value in (
            (
                "uses_recovery_as_boot",
                self.uses_recovery_as_boot,
            ),
            (
                "uses_generic_kernel_image",
                self.uses_generic_kernel_image,
            ),
            (
                "move_recovery_resources_to_vendor_boot",
                self.move_recovery_resources_to_vendor_boot,
            ),
            (
                "exclude_kernel_from_recovery_image",
                self.exclude_kernel_from_recovery_image,
            ),
            (
                "move_gsi_avb_keys_to_vendor_boot",
                self.move_gsi_avb_keys_to_vendor_boot,
            ),
            (
                "requires_generic_ramdisk_product",
                self.requires_generic_ramdisk_product,
            ),
            (
                "build_standalone_vendor_ramdisk_image",
                self.build_standalone_vendor_ramdisk_image,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a bool"
                )

        for field_name, value in (
            (
                "recovery_default_rotation",
                self.recovery_default_rotation,
            ),
            (
                "recovery_pixel_format",
                self.recovery_pixel_format,
            ),
        ):
            if (
                value is not None
                and (
                    not isinstance(value, str)
                    or not value.strip()
                    or value.strip() != value
                )
            ):
                raise ValueError(
                    f"{field_name} must be None or a "
                    "non-empty trimmed string"
                )

        if (
            self.recovery_ui_margin_height is not None
            and (
                isinstance(
                    self.recovery_ui_margin_height,
                    bool,
                )
                or not isinstance(
                    self.recovery_ui_margin_height,
                    int,
                )
                or self.recovery_ui_margin_height < 0
            )
        ):
            raise ValueError(
                "recovery_ui_margin_height must be None "
                "or a non-negative integer"
            )

        if not isinstance(
            self.recovery_ui_libs,
            tuple,
        ):
            raise TypeError(
                "recovery_ui_libs must be a tuple"
            )

        if not all(
            isinstance(item, str)
            and item
            and item.strip() == item
            for item in self.recovery_ui_libs
        ):
            raise ValueError(
                "recovery_ui_libs must contain only "
                "non-empty trimmed strings"
            )

        if len(
            self.recovery_ui_libs
        ) != len(
            set(self.recovery_ui_libs)
        ):
            raise ValueError(
                "recovery_ui_libs must be unique"
            )

    @property
    def has_dedicated_recovery(
        self,
    ) -> bool:
        return (
            "recovery"
            in self.present_partitions
        )


def select_android_device_tree_boot_architecture_profile(
    android_version: str,
    *,
    first_api_level: int,
    present_partitions: tuple[
        str,
        ...,
    ],
    boot_header_version: int,
    init_boot_header_version: int,
) -> AndroidDeviceTreeBootArchitectureProfile:
    """
    Resolve one versioned TreeForge Android boot-architecture profile.

    No source checkout is consulted here.
    """

    if not isinstance(
        android_version,
        str,
    ):
        raise TypeError(
            "android_version must be a string"
        )

    normalized_version = (
        android_version.strip()
    )

    if normalized_version == "15":
        from treeforge.android.version.android15.device_tree.boot_architecture import (
            resolve_android_15_r36_boot_architecture,
        )

        return (
            resolve_android_15_r36_boot_architecture(
                first_api_level=(
                    first_api_level
                ),
                present_partitions=(
                    present_partitions
                ),
                boot_header_version=(
                    boot_header_version
                ),
                init_boot_header_version=(
                    init_boot_header_version
                ),
            )
        )

    raise ValueError(
        "TreeForge has no Device Tree boot-architecture "
        f"profile for Android {normalized_version!r}"
    )
