from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.device_tree.product_policy import (
    AndroidDeviceTreeProductPolicySelector,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePlatformBoardConfig:
    """
    Canonical Android platform / SoC BoardConfig identity.

    This model represents platform-level Android build facts that are
    independent of the generated device-tree path and independent of any
    OEM/reference source-tree organization.
    """

    board_platform: str

    system_filesystem_type: str | None = None
    vendor_filesystem_type: str | None = None
    product_filesystem_type: str | None = None
    system_ext_filesystem_type: str | None = None
    odm_filesystem_type: str | None = None
    system_dlkm_filesystem_type: str | None = None
    vendor_dlkm_filesystem_type: str | None = None
    odm_dlkm_filesystem_type: str | None = None

    metadata_partition_present: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.metadata_partition_present,
            bool,
        ):
            raise TypeError(
                "metadata_partition_present must be a bool"
            )

        if not isinstance(
            self.board_platform,
            str,
        ):
            raise TypeError(
                "board_platform must be a string"
            )

        if (
            not self.board_platform
            or self.board_platform.strip()
            != self.board_platform
        ):
            raise ValueError(
                "board_platform must be a non-empty "
                "normalized string"
            )

        for field_name in (
            "system_filesystem_type",
            "vendor_filesystem_type",
            "product_filesystem_type",
            "system_ext_filesystem_type",
            "odm_filesystem_type",
            "system_dlkm_filesystem_type",
            "vendor_dlkm_filesystem_type",
            "odm_dlkm_filesystem_type",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is None:
                continue

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be "
                    "a string or None"
                )

            if (
                not value
                or value.strip().lower()
                != value
            ):
                raise ValueError(
                    f"{field_name} must be "
                    "a normalized lowercase "
                    "filesystem type"
                )


class AndroidDeviceTreePlatformBoardConfigRenderer:
    """
    Project canonical Universe platform conclusions into Android
    BoardConfig syntax.

    Platform identity comes exclusively from canonical evidence.
    This renderer must not infer platform identity from:

    - device names;
    - vendor names;
    - source-tree paths;
    - reference device trees;
    - hardcoded SoC knowledge.

    Reference source trees may later be reconciled against this canonical
    platform identity by dedicated Device Tree source-consumption logic.
    """

    @classmethod
    def project(
        cls,
        *,
        universe: AndroidDeviceUniverse,
    ) -> AndroidDeviceTreePlatformBoardConfig:
        if not isinstance(
            universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        board_platform = (
            AndroidDeviceTreeProductPolicySelector
            ._agreed_fact(
                universe,
                "board_platform",
            )
        )

        if not isinstance(
            board_platform,
            str,
        ):
            raise TypeError(
                "canonical board_platform must be a string"
            )

        artifact_requirements = getattr(
            universe,
            "artifact_requirements",
            None,
        )

        source_inventory = getattr(
            artifact_requirements,
            "source_inventory",
            None,
        )

        if not isinstance(
            source_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "canonical Universe artifact requirements "
                "must preserve FilesystemMetadataInventory "
                "source_inventory"
            )

        filesystem_fields = (
            (
                "system",
                "system_filesystem_type",
            ),
            (
                "vendor",
                "vendor_filesystem_type",
            ),
            (
                "product",
                "product_filesystem_type",
            ),
            (
                "system_ext",
                "system_ext_filesystem_type",
            ),
            (
                "odm",
                "odm_filesystem_type",
            ),
            (
                "system_dlkm",
                "system_dlkm_filesystem_type",
            ),
            (
                "vendor_dlkm",
                "vendor_dlkm_filesystem_type",
            ),
            (
                "odm_dlkm",
                "odm_dlkm_filesystem_type",
            ),
        )

        filesystem_values: dict[
            str,
            str | None,
        ] = {
            field_name: None
            for (
                _,
                field_name,
            )
            in filesystem_fields
        }

        for (
            partition_name,
            field_name,
        ) in filesystem_fields:
            if not source_inventory.contains(
                partition_name
            ):
                continue

            result = source_inventory.result(
                partition_name
            )

            metadata = getattr(
                result,
                "metadata",
                None,
            )

            filesystem_type = getattr(
                metadata,
                "filesystem_type",
                None,
            )

            if not isinstance(
                filesystem_type,
                str,
            ):
                raise TypeError(
                    "canonical filesystem metadata "
                    f"for {partition_name} has no "
                    "string filesystem_type"
                )

            filesystem_type = (
                filesystem_type
                .strip()
                .lower()
            )

            if not filesystem_type:
                raise ValueError(
                    "canonical filesystem metadata "
                    f"for {partition_name} has an "
                    "empty filesystem_type"
                )

            filesystem_values[
                field_name
            ] = filesystem_type

        #
        # /metadata is a root mountpoint requirement, not a
        # filesystem-image construction requirement.  Derive its AOSP
        # topology declaration from canonical Universe fstab semantics.
        #
        fstab_requirements = getattr(
            universe,
            "fstab_requirements",
            None,
        )

        if not isinstance(
            fstab_requirements,
            tuple,
        ):
            raise TypeError(
                "canonical Universe must preserve tuple "
                "fstab_requirements"
            )

        metadata_partition_present = any(
            requirement.mount_point == "/metadata"
            for requirement in fstab_requirements
        )

        #
        # Canonical /metadata root-mount topology.
        #
        # Metadata is not necessarily represented by the filesystem-image
        # inventory.  Its required root mountpoint is instead derived from
        # canonical Universe fstab semantics.
        #
        fstab_requirements = getattr(
            universe,
            "fstab_requirements",
            (),
        )

        if fstab_requirements is None:
            fstab_requirements = ()

        try:
            fstab_requirements = tuple(
                fstab_requirements
            )
        except TypeError as exc:
            raise TypeError(
                "canonical Universe fstab_requirements "
                "must be iterable"
            ) from exc

        metadata_partition_present = any(
            getattr(
                requirement,
                "mount_point",
                None,
            ) == "/metadata"
            for requirement in fstab_requirements
        )

        return AndroidDeviceTreePlatformBoardConfig(
            board_platform=board_platform,
            metadata_partition_present=metadata_partition_present,
            **filesystem_values,
        )

    @staticmethod
    def render(
        config: AndroidDeviceTreePlatformBoardConfig,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreePlatformBoardConfig,
        ):
            raise TypeError(
                "config must be an "
                "AndroidDeviceTreePlatformBoardConfig"
            )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Canonical Android board platform / SoC identity.",
            "",
            (
                "TARGET_BOARD_PLATFORM := "
                f"{config.board_platform}"
            ),
        ]

        #
        # AOSP must be told explicitly when these partitions are built as
        # independent images.  The filesystem-type evidence already proves
        # that TreeForge is constructing each image; derive the topology
        # declaration from that same canonical evidence rather than from
        # device-specific policy.
        #
        image_topology_variables = (
            (
                "BOARD_USES_VENDORIMAGE",
                config.vendor_filesystem_type,
            ),
            (
                "BOARD_USES_PRODUCTIMAGE",
                config.product_filesystem_type,
            ),
            (
                "BOARD_USES_SYSTEM_EXTIMAGE",
                config.system_ext_filesystem_type,
            ),
        )

        for variable, filesystem_type in image_topology_variables:
            if filesystem_type is not None:
                lines.append(
                    f"{variable} := true"
                )

        if any(
            filesystem_type is not None
            for _, filesystem_type
            in image_topology_variables
        ):
            lines.append("")

        if config.metadata_partition_present:
            lines.append(
                "BOARD_USES_METADATA_PARTITION := true"
            )
            lines.append("")

        filesystem_variables = (
            (
                "BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE",
                config.system_filesystem_type,
            ),
            (
                "BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE",
                config.vendor_filesystem_type,
            ),
            (
                "BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE",
                config.product_filesystem_type,
            ),
            (
                "BOARD_SYSTEM_EXTIMAGE_FILE_SYSTEM_TYPE",
                config.system_ext_filesystem_type,
            ),
            (
                "BOARD_ODMIMAGE_FILE_SYSTEM_TYPE",
                config.odm_filesystem_type,
            ),
            (
                "BOARD_SYSTEM_DLKMIMAGE_FILE_SYSTEM_TYPE",
                config.system_dlkm_filesystem_type,
            ),
            (
                "BOARD_VENDOR_DLKMIMAGE_FILE_SYSTEM_TYPE",
                config.vendor_dlkm_filesystem_type,
            ),
            (
                "BOARD_ODM_DLKMIMAGE_FILE_SYSTEM_TYPE",
                config.odm_dlkm_filesystem_type,
            ),
        )

        #
        # Android's image configuration contract requires the copy-out
        # root for each independently constructed partition image to
        # resolve to that partition's canonical lowercase name.
        #
        # These are generic Android build-mechanism facts.  They are
        # emitted only when canonical filesystem evidence says TreeForge
        # is constructing the corresponding image.
        #
        copy_out_variables = (
            (
                "TARGET_COPY_OUT_VENDOR",
                "vendor",
                config.vendor_filesystem_type,
            ),
            (
                "TARGET_COPY_OUT_PRODUCT",
                "product",
                config.product_filesystem_type,
            ),
            (
                "TARGET_COPY_OUT_SYSTEM_EXT",
                "system_ext",
                config.system_ext_filesystem_type,
            ),
            (
                "TARGET_COPY_OUT_ODM",
                "odm",
                config.odm_filesystem_type,
            ),
            (
                "TARGET_COPY_OUT_SYSTEM_DLKM",
                "system_dlkm",
                config.system_dlkm_filesystem_type,
            ),
            (
                "TARGET_COPY_OUT_VENDOR_DLKM",
                "vendor_dlkm",
                config.vendor_dlkm_filesystem_type,
            ),
            (
                "TARGET_COPY_OUT_ODM_DLKM",
                "odm_dlkm",
                config.odm_dlkm_filesystem_type,
            ),
        )

        filesystem_lines = tuple(
            f"{variable} := {filesystem_type}"
            for (
                variable,
                filesystem_type,
            )
            in filesystem_variables
            if filesystem_type is not None
        )

        copy_out_lines = tuple(
            f"{variable} := {partition_name}"
            for (
                variable,
                partition_name,
                filesystem_type,
            )
            in copy_out_variables
            if filesystem_type is not None
        )

        if filesystem_lines:
            lines.extend(
                (
                    "",
                    (
                        "# Canonical factory-derived "
                        "filesystem image construction."
                    ),
                    *filesystem_lines,
                )
            )

        if copy_out_lines:
            lines.extend(
                (
                    "",
                    (
                        "# Android image output roots for "
                        "canonically constructed partitions."
                    ),
                    *copy_out_lines,
                )
            )

        lines.append(
            ""
        )

        return "\n".join(
            lines
        )
