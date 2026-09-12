from __future__ import annotations

from treeforge.android.version.device_tree.boot_architecture import (
    AndroidDeviceTreeBootArchitectureProfile,
)


ANDROID_15_R36_BOOT_ARCHITECTURE_REFERENCE_TAG = (
    "android-15.0.0_r36"
)

ANDROID_15_R36_GENERIC_BOOT_PROFILE_ID = (
    "android-15.0.0_r36/"
    "generic-boot-launch-api33-plus-no-recovery-v1"
)


def resolve_android_15_r36_boot_architecture(
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
    Resolve Android 15 generic-boot build semantics.

    The resolver consumes only canonical TreeForge evidence.

    android-15.0.0_r36 and official Android boot documentation are the
    development/reference oracles from which these Android semantics were
    distilled. They are not runtime dependencies.
    """

    if (
        isinstance(
            first_api_level,
            bool,
        )
        or not isinstance(
            first_api_level,
            int,
        )
    ):
        raise TypeError(
            "first_api_level must be an integer"
        )

    partitions = tuple(
        sorted(
            set(
                present_partitions
            )
        )
    )

    #
    # Android 13 introduced the separate init_boot generic-ramdisk
    # architecture for launch devices.
    #
    # Devices launched before API 33 may legitimately retain older boot
    # topology after upgrading to Android 15. TreeForge must model that
    # separately rather than projecting Android-13-launch rules onto them.
    #
    if first_api_level < 33:
        raise ValueError(
            "Android 15 legacy/upgrade boot architecture "
            f"(first API level {first_api_level}) is not yet "
            "modeled; refusing to guess generic-boot semantics"
        )

    #
    # Android 15 corresponds to API 35. A device whose first API is newer
    # than the target platform requires a different compatibility model.
    #
    if first_api_level > 35:
        raise ValueError(
            "Android 15 boot architecture cannot classify a "
            f"device first launched at API {first_api_level}"
        )

    required_partitions = (
        "boot",
        "init_boot",
        "vendor_boot",
    )

    missing = tuple(
        partition
        for partition
        in required_partitions
        if partition
        not in partitions
    )

    if missing:
        raise ValueError(
            "Android 15 API-33+ generic-boot architecture "
            "is missing required observed partitions: "
            + ", ".join(
                missing
            )
        )

    if (
        "vendor_kernel_boot"
        in partitions
        and "vendor_boot"
        not in partitions
    ):
        raise ValueError(
            "vendor_kernel_boot exists without vendor_boot; "
            "TreeForge will not guess this boot topology"
        )

    #
    # Android generic boot may use boot header v3 or v4.
    #
    if boot_header_version not in (
        3,
        4,
    ):
        raise ValueError(
            "Android 15 generic boot requires boot header "
            "version 3 or 4; observed "
            f"{boot_header_version}"
        )

    #
    # init_boot was introduced with header v4.
    #
    if init_boot_header_version != 4:
        raise ValueError(
            "Android 15 API-33+ init_boot requires header "
            "version 4; observed "
            f"{init_boot_header_version}"
        )

    #
    # Dedicated recovery has multiple legitimate Android contracts:
    # - A/B dedicated recovery;
    # - non-A/B dedicated recovery.
    #
    # Partition existence alone does not prove which contract applies.
    # Until TreeForge carries canonical slot topology into this resolver,
    # fail closed rather than selecting the wrong recovery rules.
    #
    if "recovery" in partitions:
        raise ValueError(
            "Android 15 dedicated-recovery generic-boot "
            "architecture requires explicit recovery slot "
            "topology; TreeForge will not infer A/B versus "
            "non-A/B recovery from partition existence alone"
        )

    return (
        AndroidDeviceTreeBootArchitectureProfile(
            profile_id=(
                ANDROID_15_R36_GENERIC_BOOT_PROFILE_ID
            ),
            android_version="15",
            reference_tag=(
                ANDROID_15_R36_BOOT_ARCHITECTURE_REFERENCE_TAG
            ),
            first_api_level=(
                first_api_level
            ),
            present_partitions=(
                partitions
            ),
            boot_header_version=(
                boot_header_version
            ),
            init_boot_header_version=(
                init_boot_header_version
            ),
            uses_recovery_as_boot=False,
            uses_generic_kernel_image=True,
            move_recovery_resources_to_vendor_boot=True,
            exclude_kernel_from_recovery_image=False,
            move_gsi_avb_keys_to_vendor_boot=True,
            requires_generic_ramdisk_product=True,
            build_standalone_vendor_ramdisk_image=False,
            recovery_pixel_format="ABGR_8888",
            recovery_ui_margin_height=165,
            recovery_ui_libs=(
                "//hardware/google/pixel/recovery:"
                "librecovery_ui_pixel",
                "libfstab",
            ),
        )
    )
