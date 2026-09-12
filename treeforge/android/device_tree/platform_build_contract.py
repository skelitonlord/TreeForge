from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.device_tree.dynamic_partitions import (
    AndroidDeviceTreeDynamicPartitionConfig,
)
from treeforge.android.partition.layout import (
    PartitionLayout,
)
from treeforge.android.version.device_tree.platform_build_contract import (
    AndroidDeviceTreePlatformBuildContractProfile,
    select_android_device_tree_platform_build_contract,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePlatformBuildContract:
    profile: AndroidDeviceTreePlatformBuildContractProfile
    bootloader_board_name: str
    board_info_path: PurePosixPath
    ab_ota_partitions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.profile,
            AndroidDeviceTreePlatformBuildContractProfile,
        ):
            raise TypeError(
                "profile must be an "
                "AndroidDeviceTreePlatformBuildContractProfile"
            )

        if (
            not isinstance(
                self.bootloader_board_name,
                str,
            )
            or not self.bootloader_board_name
            or self.bootloader_board_name.strip()
            != self.bootloader_board_name
        ):
            raise ValueError(
                "bootloader_board_name must be a normalized "
                "non-empty string"
            )

        if (
            not isinstance(
                self.board_info_path,
                PurePosixPath,
            )
            or self.board_info_path.is_absolute()
            or ".." in self.board_info_path.parts
        ):
            raise ValueError(
                "board_info_path must be a safe Device Tree "
                "relative PurePosixPath"
            )

        if (
            not isinstance(
                self.ab_ota_partitions,
                tuple,
            )
            or not self.ab_ota_partitions
        ):
            raise ValueError(
                "ab_ota_partitions must be a non-empty tuple"
            )


class AndroidDeviceTreePlatformBuildContractProjector:
    @classmethod
    def project(
        cls,
        *,
        android_version: str,
        board_platform: str,
        bootloader_board_name: str,
        device_root: PurePosixPath,
        virtual_ab_enabled: bool,
        layout: PartitionLayout,
        dynamic_partition_config: (
            AndroidDeviceTreeDynamicPartitionConfig | None
        ),
    ) -> AndroidDeviceTreePlatformBuildContract:
        if (
            not isinstance(
                device_root,
                PurePosixPath,
            )
            or device_root.is_absolute()
            or ".." in device_root.parts
        ):
            raise ValueError(
                "device_root must be a safe relative PurePosixPath"
            )

        if not isinstance(
            layout,
            PartitionLayout,
        ):
            raise TypeError(
                "layout must be a PartitionLayout"
            )

        if dynamic_partition_config is None:
            raise ValueError(
                "validated Android platform build contract "
                "requires dynamic-partition topology"
            )

        profile = (
            select_android_device_tree_platform_build_contract(
                android_version,
                board_platform=board_platform,
                virtual_ab_enabled=virtual_ab_enabled,
                super_partition_size_bytes=(
                    dynamic_partition_config
                    .super_partition_size_bytes
                ),
            )
        )

        present_partitions = {
            partition.base_name
            for partition in layout.partitions
        }

        missing = tuple(
            partition
            for partition
            in profile.ab_ota_partition_order
            if partition not in present_partitions
        )

        if missing:
            raise ValueError(
                "validated A/B OTA build contract requires "
                "partitions absent from canonical PartitionLayout: "
                + ", ".join(missing)
            )

        missing_board_info_partitions = tuple(
            partition
            for partition
            in profile.board_info_required_partitions
            if partition not in present_partitions
        )

        if missing_board_info_partitions:
            raise ValueError(
                "validated board-info contract requires "
                "partitions absent from canonical PartitionLayout: "
                + ", ".join(
                    missing_board_info_partitions
                )
            )

        return AndroidDeviceTreePlatformBuildContract(
            profile=profile,
            bootloader_board_name=(
                bootloader_board_name
            ),
            board_info_path=(
                device_root
                / "board-info.txt"
            ),
            ab_ota_partitions=(
                profile.ab_ota_partition_order
            ),
        )


class AndroidDeviceTreePlatformBuildContractRenderer:
    @staticmethod
    def render_board_config(
        contract: AndroidDeviceTreePlatformBuildContract,
    ) -> str:
        if not isinstance(
            contract,
            AndroidDeviceTreePlatformBuildContract,
        ):
            raise TypeError(
                "contract must be an "
                "AndroidDeviceTreePlatformBuildContract"
            )

        profile = contract.profile

        lines = [
            "# TreeForge-owned versioned Android platform build contract.",
            "#",
            f"# Profile: {profile.profile_id}",
            f"# Reference: {profile.reference_tag}",
            "# Runtime AOSP checkout dependency: no",
            "",
            (
                "TARGET_BOOTLOADER_BOARD_NAME := "
                f"{contract.bootloader_board_name}"
            ),
            "",
            (
                "TARGET_BOARD_INFO_FILE := "
                f"{contract.board_info_path.as_posix()}"
            ),
            "",
            (
                "TARGET_USERIMAGES_USE_EXT4 := "
                + (
                    "true"
                    if profile.target_userimages_use_ext4
                    else ""
                )
            ),
            (
                "TARGET_USERIMAGES_USE_F2FS := "
                + (
                    "true"
                    if profile.target_userimages_use_f2fs
                    else ""
                )
            ),
            (
                "BOARD_USERDATAIMAGE_PARTITION_SIZE := "
                f"{profile.userdata_partition_size_bytes}"
            ),
            (
                "BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := "
                f"{profile.userdata_filesystem_type}"
            ),
            (
                "BOARD_FLASH_BLOCK_SIZE := "
                f"{profile.flash_block_size_bytes}"
            ),
            (
                "BOARD_MOUNT_SDCARD_RW := "
                + (
                    "true"
                    if profile.mount_sdcard_rw
                    else ""
                )
            ),
            "",
            (
                "BOARD_SUPER_PARTITION_ERROR_LIMIT := "
                f"{profile.super_partition_error_limit_bytes}"
            ),
            "",
        ]

        if profile.uses_system_other_odex:
            lines.extend(
                [
                    "BOARD_USES_SYSTEM_OTHER_ODEX := true",
                    "",
                ]
            )

        if profile.boot_security_patch_from_platform:
            lines.append(
                "BOOT_SECURITY_PATCH := "
                "$(PLATFORM_SECURITY_PATCH)"
            )

        if profile.vendor_security_patch_from_platform:
            lines.append(
                "VENDOR_SECURITY_PATCH := "
                "$(PLATFORM_SECURITY_PATCH)"
            )

        if (
            profile.boot_security_patch_from_platform
            or profile.vendor_security_patch_from_platform
        ):
            lines.append("")

        for partition in (
            profile.avb_hashtree_partitions
        ):
            variable = (
                "BOARD_AVB_"
                + partition.upper()
                + "_ADD_HASHTREE_FOOTER_ARGS"
            )

            lines.append(
                f"{variable} += --hash_algorithm "
                f"{profile.avb_hashtree_hash_algorithm}"
            )

        lines.extend(
            [
                "",
                "AB_OTA_PARTITIONS := \\",
            ]
        )

        last = len(
            contract.ab_ota_partitions
        ) - 1

        for index, partition in enumerate(
            contract.ab_ota_partitions
        ):
            suffix = (
                " \\"
                if index != last
                else ""
            )

            lines.append(
                f"    {partition}{suffix}"
            )

        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def render_product_config(
        contract: AndroidDeviceTreePlatformBuildContract,
    ) -> str:
        if not isinstance(
            contract,
            AndroidDeviceTreePlatformBuildContract,
        ):
            raise TypeError(
                "contract must be an "
                "AndroidDeviceTreePlatformBuildContract"
            )

        profile = contract.profile

        lines = [
            "# TreeForge-owned versioned Android platform product policy.",
            (
                "PRODUCT_CHARACTERISTICS := "
                f"{profile.product_characteristics}"
            ),
            (
                "PRODUCT_FS_COMPRESSION := "
                f"{profile.product_fs_compression}"
            ),
            (
                "PRODUCT_VIRTUAL_AB_COMPRESSION_METHOD := "
                f"{profile.virtual_ab_compression_method}"
            ),
        ]

        if profile.inherit_developer_gsi_keys:
            lines.extend(
                [
                    "",
                    "$(call inherit-product, "
                    "$(SRC_TARGET_DIR)/product/"
                    "developer_gsi_keys.mk)",
                ]
            )

        if profile.recovery_product_packages:
            lines.extend(
                [
                    "",
                    "PRODUCT_PACKAGES += \\",
                ]
            )

            last = len(
                profile.recovery_product_packages
            ) - 1

            for index, package in enumerate(
                profile.recovery_product_packages
            ):
                suffix = (
                    " \\"
                    if index != last
                    else ""
                )

                lines.append(
                    f"    {package}{suffix}"
                )

        return "\n".join(lines) + "\n"

    @staticmethod
    def render_board_info(
        contract: AndroidDeviceTreePlatformBuildContract,
    ) -> str:
        if not isinstance(
            contract,
            AndroidDeviceTreePlatformBuildContract,
        ):
            raise TypeError(
                "contract must be an "
                "AndroidDeviceTreePlatformBuildContract"
            )

        lines = [
            (
                "require board="
                f"{contract.bootloader_board_name}"
            ),
        ]

        lines.extend(
            "require partition-exists="
            + partition
            for partition
            in contract.profile.board_info_required_partitions
        )

        return "\n".join(lines) + "\n"
