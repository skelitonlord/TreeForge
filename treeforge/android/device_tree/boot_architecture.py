from __future__ import annotations

from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.version.device_tree.boot_architecture import (
    AndroidDeviceTreeBootArchitectureProfile,
    select_android_device_tree_boot_architecture_profile,
)


class AndroidDeviceTreeBootArchitectureProjector:
    """
    Resolve Android boot architecture from canonical TreeForge evidence.

    This projector does not inspect an Android/AOSP source checkout.
    """

    _TRACKED_PARTITIONS = (
        "boot",
        "dtbo",
        "init_boot",
        "pvmfw",
        "recovery",
        "vendor_boot",
        "vendor_kernel_boot",
    )

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        android_version: str,
        boot_header_version: int,
        init_boot_header_version: int,
    ) -> AndroidDeviceTreeBootArchitectureProfile:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an AndroidReconstructionResult"
            )

        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        first_api_level = (
            cls._agreed_int_fact(
                universe,
                "first_api_level",
            )
        )

        partition_layout = (
            reconstruction
            .reconstruction_input
            .partition_layout
        )

        if partition_layout is None:
            raise ValueError(
                "Device Tree boot architecture requires "
                "canonical PartitionLayout evidence"
            )

        present_partitions = tuple(
            partition
            for partition
            in cls._TRACKED_PARTITIONS
            if cls._partition_present(
                partition_layout,
                partition,
            )
        )

        return (
            select_android_device_tree_boot_architecture_profile(
                android_version,
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

    @staticmethod
    def _partition_present(
        partition_layout,
        partition_name: str,
    ) -> bool:
        """
        Test canonical and explicit slot-suffixed identities.

        This does not invent slot topology. It only answers whether a
        partition family is materially represented in canonical layout
        evidence.
        """

        return any(
            partition_layout.partition(
                candidate
            )
            is not None
            for candidate
            in (
                partition_name,
                f"{partition_name}_a",
                f"{partition_name}_b",
            )
        )

    @staticmethod
    def _agreed_fact(
        universe,
        fact_name: str,
    ):
        """
        Read one agreed canonical Universe fact.

        Prefer the architecture conclusion surface when populated, matching
        Device Tree's existing canonical product-policy consumption.
        """

        architecture = getattr(
            universe,
            "architecture",
            None,
        )

        if architecture is not None:
            conclusion = (
                architecture.conclusion(
                    fact_name
                )
            )

            if conclusion is not None:
                if (
                    conclusion.status.value
                    != "agreed"
                ):
                    raise ValueError(
                        "Device Tree boot architecture requires "
                        f"agreed {fact_name!r} evidence"
                    )

                return conclusion.value

        matches = tuple(
            conclusion
            for conclusion
            in universe.conclusions
            if (
                conclusion.fact
                == fact_name
                and conclusion.status.value
                == "agreed"
            )
        )

        if len(matches) != 1:
            raise ValueError(
                "Device Tree boot architecture requires exactly "
                f"one agreed {fact_name!r} conclusion; "
                f"found {len(matches)}"
            )

        return matches[0].value

    @classmethod
    def _agreed_int_fact(
        cls,
        universe,
        fact_name: str,
    ) -> int:
        value = cls._agreed_fact(
            universe,
            fact_name,
        )

        if (
            isinstance(
                value,
                int,
            )
            and not isinstance(
                value,
                bool,
            )
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            normalized = value.strip()

            if normalized.isdecimal():
                return int(
                    normalized
                )

        raise ValueError(
            "Device Tree boot architecture requires "
            f"{fact_name!r} to resolve to an integer; "
            f"observed {value!r}"
        )


class AndroidDeviceTreeBootArchitectureRenderer:
    """
    Render the resolved TreeForge boot architecture onto Android build syntax.
    """

    @staticmethod
    def render_board_config(
        profile: AndroidDeviceTreeBootArchitectureProfile,
    ) -> str:
        if not isinstance(
            profile,
            AndroidDeviceTreeBootArchitectureProfile,
        ):
            raise TypeError(
                "profile must be an "
                "AndroidDeviceTreeBootArchitectureProfile"
            )

        def assignment(
            name: str,
            value: bool,
        ) -> str:
            return (
                f"{name} := true"
                if value
                else f"{name} :="
            )

        lines = [
            "# TreeForge-owned Android boot architecture contract.",
            "#",
            f"# Profile: {profile.profile_id}",
            f"# Reference: {profile.reference_tag}",
            (
                "# First API level: "
                f"{profile.first_api_level}"
            ),
            "# Runtime AOSP checkout dependency: no",
            "",
            assignment(
                "BOARD_USES_RECOVERY_AS_BOOT",
                profile.uses_recovery_as_boot,
            ),
            assignment(
                "BOARD_USES_GENERIC_KERNEL_IMAGE",
                profile.uses_generic_kernel_image,
            ),
            assignment(
                "BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT",
                profile.move_recovery_resources_to_vendor_boot,
            ),
            assignment(
                "BOARD_EXCLUDE_KERNEL_FROM_RECOVERY_IMAGE",
                profile.exclude_kernel_from_recovery_image,
            ),
            assignment(
                "BOARD_MOVE_GSI_AVB_KEYS_TO_VENDOR_BOOT",
                profile.move_gsi_avb_keys_to_vendor_boot,
            ),
            assignment(
                "TARGET_NO_RECOVERY",
                not profile.has_dedicated_recovery,
            ),
            "",
            (
                "# Standalone vendor_ramdisk.img is intentionally "
                "not selected by this boot contract."
            ),
            (
                "# vendor_boot construction remains independently "
                "owned by the native boot build plan."
            ),
        ]

        return (
            "\n".join(
                lines
            )
            + "\n"
        )

    @staticmethod
    def render_product_config(
        profile: AndroidDeviceTreeBootArchitectureProfile,
    ) -> str:
        if not isinstance(
            profile,
            AndroidDeviceTreeBootArchitectureProfile,
        ):
            raise TypeError(
                "profile must be an "
                "AndroidDeviceTreeBootArchitectureProfile"
            )

        lines = [
            "# TreeForge-owned boot product contract.",
            (
                "PRODUCT_SHIPPING_API_LEVEL := "
                f"{profile.first_api_level}"
            ),
        ]

        if profile.requires_generic_ramdisk_product:
            lines.extend(
                [
                    "$(call inherit-product, "
                    "$(SRC_TARGET_DIR)/product/generic_ramdisk.mk)",
                ]
            )

        return "\n".join(lines) + "\n"
