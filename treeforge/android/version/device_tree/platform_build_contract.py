from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePlatformBuildContractProfile:
    """
    Versioned Android platform build-policy contract.

    Factory/Universe evidence selects this profile.  The profile contains
    Android build semantics distilled from the canonical version/platform
    oracle and never consults an AOSP checkout at runtime.
    """

    profile_id: str
    android_version: str
    reference_tag: str
    board_platform: str

    target_userimages_use_ext4: bool
    target_userimages_use_f2fs: bool

    userdata_partition_size_bytes: int
    userdata_filesystem_type: str

    product_fs_compression: int
    flash_block_size_bytes: int
    mount_sdcard_rw: bool

    product_characteristics: str

    virtual_ab_compression_method: str

    super_partition_error_limit_bytes: int

    ab_ota_partition_order: tuple[str, ...]

    uses_system_other_odex: bool

    boot_security_patch_from_platform: bool
    vendor_security_patch_from_platform: bool

    avb_hashtree_hash_algorithm: str
    avb_hashtree_partitions: tuple[str, ...]

    inherit_developer_gsi_keys: bool
    recovery_product_packages: tuple[str, ...]

    board_info_required_partitions: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "profile_id",
            "android_version",
            "reference_tag",
            "board_platform",
            "userdata_filesystem_type",
            "product_characteristics",
            "virtual_ab_compression_method",
            "avb_hashtree_hash_algorithm",
        ):
            value = getattr(self, field_name)

            if (
                not isinstance(value, str)
                or not value
                or value.strip() != value
            ):
                raise ValueError(
                    f"{field_name} must be a normalized non-empty string"
                )

        for field_name in (
            "target_userimages_use_ext4",
            "target_userimages_use_f2fs",
            "mount_sdcard_rw",
            "uses_system_other_odex",
            "boot_security_patch_from_platform",
            "vendor_security_patch_from_platform",
            "inherit_developer_gsi_keys",
        ):
            if not isinstance(
                getattr(self, field_name),
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a bool"
                )

        for field_name in (
            "userdata_partition_size_bytes",
            "product_fs_compression",
            "flash_block_size_bytes",
            "super_partition_error_limit_bytes",
        ):
            value = getattr(self, field_name)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(
                    f"{field_name} must be a positive integer"
                )

        for field_name in (
            "avb_hashtree_partitions",
            "recovery_product_packages",
            "board_info_required_partitions",
        ):
            values = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(
                    values,
                    tuple,
                )
                or not values
                or not all(
                    isinstance(item, str)
                    and item
                    and item.strip() == item
                    for item in values
                )
                or len(values)
                != len(set(values))
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty "
                    "unique tuple of normalized strings"
                )

        if (
            not isinstance(
                self.ab_ota_partition_order,
                tuple,
            )
            or not self.ab_ota_partition_order
            or not all(
                isinstance(item, str) and item
                for item in self.ab_ota_partition_order
            )
            or len(self.ab_ota_partition_order)
            != len(set(self.ab_ota_partition_order))
        ):
            raise ValueError(
                "ab_ota_partition_order must be a non-empty "
                "unique tuple of partition names"
            )


def select_android_device_tree_platform_build_contract(
    android_version: str,
    *,
    board_platform: str,
    virtual_ab_enabled: bool,
    super_partition_size_bytes: int,
) -> AndroidDeviceTreePlatformBuildContractProfile:
    if not isinstance(android_version, str):
        raise TypeError(
            "android_version must be a string"
        )

    normalized_version = android_version.strip()

    if normalized_version == "15":
        from treeforge.android.version.android15.device_tree.platform_build_contract import (
            resolve_android_15_r36_platform_build_contract,
        )

        return resolve_android_15_r36_platform_build_contract(
            board_platform=board_platform,
            virtual_ab_enabled=virtual_ab_enabled,
            super_partition_size_bytes=(
                super_partition_size_bytes
            ),
        )

    raise ValueError(
        "TreeForge has no platform build contract for "
        f"Android {normalized_version!r}"
    )
