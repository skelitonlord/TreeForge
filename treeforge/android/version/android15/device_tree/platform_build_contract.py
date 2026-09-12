from __future__ import annotations

from treeforge.android.version.device_tree.platform_build_contract import (
    AndroidDeviceTreePlatformBuildContractProfile,
)


ANDROID_15_R36_PLATFORM_BUILD_REFERENCE_TAG = (
    "android-15.0.0_r36"
)

ANDROID_15_R36_GS201_PLATFORM_BUILD_PROFILE_ID = (
    "android-15.0.0_r36/gs201-platform-build-v2"
)

_GS201_SUPER_BUILD_HEADROOM_BYTES = (
    500 * 1024 * 1024
)

_GS201_AVB_HASHTREE_PARTITIONS = (
    "system",
    "system_other",
    "system_dlkm",
    "system_ext",
    "product",
    "vendor",
    "vendor_dlkm",
)

_GS201_RECOVERY_PRODUCT_PACKAGES = (
    "fastbootd",
    "update_engine_sideload",
)

_GS201_BOARD_INFO_REQUIRED_PARTITIONS = (
    "vendor_kernel_boot",
)

_GS201_AB_OTA_PARTITION_ORDER = (
    "system",
    "system_dlkm",
    "system_ext",
    "product",
    "vbmeta_system",
    "boot",
    "init_boot",
    "vendor_boot",
    "dtbo",
    "vendor_kernel_boot",
    "vbmeta",
    "pvmfw",
    "vbmeta_vendor",
    "vendor",
    "vendor_dlkm",
)


def resolve_android_15_r36_platform_build_contract(
    *,
    board_platform: str,
    virtual_ab_enabled: bool,
    super_partition_size_bytes: int,
) -> AndroidDeviceTreePlatformBuildContractProfile:
    """
    Android 15 r36 gs201 build-policy contract.

    The values here are version/platform build semantics distilled from the
    canonical Google Android 15 r36 build and validated against the
    hardware-proven AOSP tangorpro product.  They are not device-tree source
    dependencies and are not tangorpro identity hardcodes.
    """

    if board_platform != "gs201":
        raise ValueError(
            "Android 15 r36 platform build contract does not "
            "yet support board_platform "
            f"{board_platform!r}"
        )

    if not isinstance(
        virtual_ab_enabled,
        bool,
    ):
        raise TypeError(
            "virtual_ab_enabled must be a bool"
        )

    if not virtual_ab_enabled:
        raise ValueError(
            "Android 15 r36 gs201 platform build contract "
            "currently requires canonical Virtual A/B evidence"
        )

    if (
        isinstance(
            super_partition_size_bytes,
            bool,
        )
        or not isinstance(
            super_partition_size_bytes,
            int,
        )
        or super_partition_size_bytes
        <= _GS201_SUPER_BUILD_HEADROOM_BYTES
    ):
        raise ValueError(
            "super partition is too small for the validated "
            "Android 15 r36 gs201 build-headroom policy"
        )

    return AndroidDeviceTreePlatformBuildContractProfile(
        profile_id=(
            ANDROID_15_R36_GS201_PLATFORM_BUILD_PROFILE_ID
        ),
        android_version="15",
        reference_tag=(
            ANDROID_15_R36_PLATFORM_BUILD_REFERENCE_TAG
        ),
        board_platform="gs201",
        target_userimages_use_ext4=True,
        target_userimages_use_f2fs=True,
        userdata_partition_size_bytes=11796480000,
        userdata_filesystem_type="f2fs",
        product_fs_compression=1,
        flash_block_size_bytes=4096,
        mount_sdcard_rw=True,
        product_characteristics="nosdcard",
        virtual_ab_compression_method="lz4",
        super_partition_error_limit_bytes=(
            super_partition_size_bytes
            - _GS201_SUPER_BUILD_HEADROOM_BYTES
        ),
        ab_ota_partition_order=(
            _GS201_AB_OTA_PARTITION_ORDER
        ),
        uses_system_other_odex=True,
        boot_security_patch_from_platform=True,
        vendor_security_patch_from_platform=True,
        avb_hashtree_hash_algorithm="sha256",
        avb_hashtree_partitions=(
            _GS201_AVB_HASHTREE_PARTITIONS
        ),
        inherit_developer_gsi_keys=True,
        recovery_product_packages=(
            _GS201_RECOVERY_PRODUCT_PACKAGES
        ),
        board_info_required_partitions=(
            _GS201_BOARD_INFO_REQUIRED_PARTITIONS
        ),
    )
