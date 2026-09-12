from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.physical_payload_projection import (
    AndroidDeviceTreePhysicalPayloadProjection,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeKernelBoardConfig:
    """
    Exact Device Tree BoardConfig projection for direct DLKM payloads.

    Kernel module source paths are TreeForge materialized physical payloads.
    No OEM/source module identities are invented.

    modules.load and modules.blocklist remain exact canonical inputs.

    modules.dep, modules.alias, and modules.softdep are intentionally excluded
    because Android's DLKM machinery regenerates depmod metadata.
    """

    system_modules: tuple[PurePosixPath, ...]
    vendor_modules: tuple[PurePosixPath, ...]
    vendor_kernel_ramdisk_modules: tuple[PurePosixPath, ...]
    vendor_kernel_ramdisk_load: tuple[PurePosixPath, ...]

    system_load_file: PurePosixPath | None
    vendor_load_file: PurePosixPath | None

    system_blocklist_file: PurePosixPath | None
    vendor_blocklist_file: PurePosixPath | None

    def __post_init__(self) -> None:
        for field_name, values in (
            ("system_modules", self.system_modules),
            ("vendor_modules", self.vendor_modules),
            (
                "vendor_kernel_ramdisk_modules",
                self.vendor_kernel_ramdisk_modules,
            ),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(value, PurePosixPath)
                for value in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "PurePosixPath values"
                )

            if len(values) != len(set(values)):
                raise ValueError(
                    f"{field_name} must contain unique paths"
                )

            if values != tuple(
                sorted(
                    values,
                    key=lambda value: value.as_posix(),
                )
            ):
                raise ValueError(
                    f"{field_name} must use deterministic ordering"
                )

            for value in values:
                if value.is_absolute():
                    raise ValueError(
                        f"{field_name} paths must be "
                        "source-tree relative"
                    )

                if ".." in value.parts:
                    raise ValueError(
                        f"{field_name} paths must not escape "
                        "the Device Tree workspace"
                    )

                if value.suffix != ".ko":
                    raise ValueError(
                        f"{field_name} must contain only .ko files"
                    )

        if not isinstance(
            self.vendor_kernel_ramdisk_load,
            tuple,
        ):
            raise TypeError(
                "vendor_kernel_ramdisk_load must be a tuple"
            )

        if not all(
            isinstance(value, PurePosixPath)
            for value in self.vendor_kernel_ramdisk_load
        ):
            raise TypeError(
                "vendor_kernel_ramdisk_load must contain only "
                "PurePosixPath values"
            )

        if len(
            self.vendor_kernel_ramdisk_load
        ) != len(
            set(self.vendor_kernel_ramdisk_load)
        ):
            raise ValueError(
                "vendor_kernel_ramdisk_load must contain unique paths"
            )

        for value in self.vendor_kernel_ramdisk_load:
            if value.is_absolute():
                raise ValueError(
                    "vendor_kernel_ramdisk_load paths must be "
                    "source-tree relative"
                )

            if ".." in value.parts:
                raise ValueError(
                    "vendor_kernel_ramdisk_load paths must not escape "
                    "the Device Tree workspace"
                )

            if value.suffix != ".ko":
                raise ValueError(
                    "vendor_kernel_ramdisk_load must contain only .ko files"
                )

        #
        # Do not sort vendor_kernel_ramdisk_load here.
        # Its tuple order is canonical first-stage modules.load order,
        # not a presentation/determinism ordering.
        #

        for field_name, value in (
            ("system_load_file", self.system_load_file),
            ("vendor_load_file", self.vendor_load_file),
            (
                "system_blocklist_file",
                self.system_blocklist_file,
            ),
            (
                "vendor_blocklist_file",
                self.vendor_blocklist_file,
            ),
        ):
            if value is None:
                continue

            if not isinstance(value, PurePosixPath):
                raise TypeError(
                    f"{field_name} must be a "
                    "PurePosixPath or None"
                )

            if value.is_absolute():
                raise ValueError(
                    f"{field_name} must be source-tree relative"
                )

            if ".." in value.parts:
                raise ValueError(
                    f"{field_name} must not escape "
                    "the Device Tree workspace"
                )


class AndroidDeviceTreeKernelBoardConfigRenderer:
    """
    Project resolved direct DLKM Device Tree realizations into BoardConfig.mk.

    Android build/make owns:
    - copying modules into the DLKM image;
    - running depmod;
    - generating modules.dep/modules.alias/modules.softdep;
    - producing modules.load from the supplied load list.

    TreeForge therefore supplies exact prebuilt .ko paths, exact load-list
    content through the canonical modules.load source, and exact blocklist
    source files.

    Vendor module stripping is disabled because TreeForge's physical payload
    is already the exact canonical installed module and must not be mutated.
    """

    _SUPPORTED_DLKM_PARTITIONS = {
        "system_dlkm",
        "vendor_dlkm",
    }

    @classmethod
    def project(
        cls,
        *,
        identity: AndroidDeviceTreeIdentity,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
        physical_payload_projections: tuple[
            AndroidDeviceTreePhysicalPayloadProjection,
            ...,
        ],
        vendor_kernel_ramdisk_plan,
    ) -> AndroidDeviceTreeKernelBoardConfig:
        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an AndroidDeviceTreeIdentity"
            )

        if not isinstance(realizations, tuple):
            raise TypeError(
                "realizations must be a tuple"
            )

        if not isinstance(
            physical_payload_projections,
            tuple,
        ):
            raise TypeError(
                "physical_payload_projections must be a tuple"
            )

        physical_by_representation_id = {
            projection.representation_id:
            projection
            for projection in physical_payload_projections
        }

        if len(
            physical_by_representation_id
        ) != len(
            physical_payload_projections
        ):
            raise ValueError(
                "physical payload projection identities "
                "must be unique"
            )

        from treeforge.android.device_tree.vendor_kernel_ramdisk import (
            AndroidDeviceTreeVendorKernelRamdiskPlan,
        )

        if not isinstance(
            vendor_kernel_ramdisk_plan,
            AndroidDeviceTreeVendorKernelRamdiskPlan,
        ):
            raise TypeError(
                "vendor_kernel_ramdisk_plan must be an "
                "AndroidDeviceTreeVendorKernelRamdiskPlan"
            )

        vendor_kernel_by_representation_id = {
            item.representation_id:
            item
            for item
            in vendor_kernel_ramdisk_plan.module_projections
        }

        modules = {
            "system_dlkm": [],
            "vendor_dlkm": [],
            "vendor_kernel_boot": [],
        }

        load_files = {}
        blocklist_files = {}

        seen_module_representation_ids = set()
        seen_config_representation_ids = set()

        for realization in realizations:
            representation = (
                realization.build_representation
            )

            if (
                representation.kind
                is AndroidReconstructionBuildRepresentationKind
                .KERNEL_MODULE
            ):
                if (
                    realization.status
                    is not AndroidDeviceTreeBuildRealizationStatus
                    .RESOLVED
                ):
                    continue

                if (
                    realization.kind
                    is not AndroidDeviceTreeBuildRealizationKind
                    .KERNEL_MODULE
                ):
                    raise ValueError(
                        "resolved kernel module must retain "
                        "KERNEL_MODULE realization kind"
                    )

                if realization.source_path is None:
                    raise ValueError(
                        "resolved kernel module requires "
                        "an exact source_path"
                    )

                projection = (
                    physical_by_representation_id.get(
                        realization.representation_id
                    )
                )

                if projection is not None:
                    if (
                        projection.build_representation
                        is not representation
                    ):
                        raise ValueError(
                            "kernel BoardConfig projection changed "
                            "exact Reconstruction representation identity"
                        )

                    if (
                        realization.source_path
                        != projection.destination
                    ):
                        raise ValueError(
                            "resolved kernel source_path must equal "
                            "its exact physical payload destination"
                        )

                    partition = (
                        projection.installed_partition
                    )

                    installed_android_path = (
                        projection.installed_android_path
                    )

                else:
                    if (
                        representation.preserved_artifact_id
                        is None
                    ):
                        raise ValueError(
                            "resolved kernel module without physical "
                            "projection must be preserved-backed: "
                            f"{realization.representation_id}"
                        )

                    partition = (
                        representation.installed_partition
                    )

                    installed_android_path = (
                        representation.installed_android_path
                    )

                    if installed_android_path is None:
                        raise ValueError(
                            "preserved-backed resolved kernel module "
                            "requires installed Android path identity"
                        )

                if partition == "vendor_kernel_boot":
                    vendor_kernel_projection = (
                        vendor_kernel_by_representation_id.get(
                            realization.representation_id
                        )
                    )

                    if vendor_kernel_projection is None:
                        raise ValueError(
                            "resolved vendor_kernel_boot module has no "
                            "vendor kernel ramdisk projection: "
                            f"{realization.representation_id}"
                        )

                    if (
                        realization.source_path
                        != vendor_kernel_projection.destination
                    ):
                        raise ValueError(
                            "resolved vendor kernel ramdisk source_path "
                            "must equal its exact projection destination"
                        )

                elif (
                    partition
                    not in cls._SUPPORTED_DLKM_PARTITIONS
                ):
                    raise ValueError(
                        "resolved direct kernel module must belong "
                        "to a supported DLKM or vendor_kernel_boot "
                        "deployment: "
                        f"{partition!r}"
                    )

                installed = PurePosixPath(
                    installed_android_path
                )

                if installed.suffix != ".ko":
                    raise ValueError(
                        "resolved KERNEL_MODULE payload must "
                        "be an installed .ko file"
                    )

                if (
                    realization.representation_id
                    in seen_module_representation_ids
                ):
                    raise ValueError(
                        "duplicate kernel module representation"
                    )

                modules[partition].append(
                    realization.source_path
                )

                seen_module_representation_ids.add(
                    realization.representation_id
                )

                continue

            if not (
                representation.kind
                is AndroidReconstructionBuildRepresentationKind
                .SOURCE_CONFIG
                and representation.source_identity.startswith(
                    "kernel-module-config:"
                )
            ):
                continue

            if (
                realization.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            ):
                continue

            if (
                realization.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SOURCE_CONFIG
            ):
                raise ValueError(
                    "resolved kernel modules.* config must "
                    "retain SOURCE_CONFIG realization kind"
                )

            if realization.source_path is None:
                raise ValueError(
                    "resolved kernel modules.* config requires "
                    "an exact source_path"
                )

            projection = (
                physical_by_representation_id.get(
                    realization.representation_id
                )
            )

            if projection is None:
                raise ValueError(
                    "resolved kernel modules.* config has no "
                    "exact physical payload projection"
                )

            if (
                projection.build_representation
                is not representation
            ):
                raise ValueError(
                    "kernel config BoardConfig projection changed "
                    "exact Reconstruction representation identity"
                )

            if (
                realization.source_path
                != projection.destination
            ):
                raise ValueError(
                    "resolved kernel config source_path must equal "
                    "its physical payload destination"
                )

            partition = projection.installed_partition

            if (
                partition
                not in cls._SUPPORTED_DLKM_PARTITIONS
            ):
                raise ValueError(
                    "resolved direct kernel config must belong "
                    "to a supported DLKM partition"
                )

            name = PurePosixPath(
                projection.installed_android_path
            ).name

            if name == "modules.load":
                target = load_files
            elif name == "modules.blocklist":
                target = blocklist_files
            else:
                raise ValueError(
                    "resolved kernel SOURCE_CONFIG must be "
                    "modules.load or modules.blocklist: "
                    f"{name!r}"
                )

            if partition in target:
                raise ValueError(
                    "multiple resolved kernel config files target "
                    f"{partition}:{name}"
                )

            target[partition] = realization.source_path

            if (
                realization.representation_id
                in seen_config_representation_ids
            ):
                raise ValueError(
                    "duplicate kernel config representation"
                )

            seen_config_representation_ids.add(
                realization.representation_id
            )

        return AndroidDeviceTreeKernelBoardConfig(
            system_modules=tuple(
                sorted(
                    modules["system_dlkm"],
                    key=lambda value: value.as_posix(),
                )
            ),
            vendor_modules=tuple(
                sorted(
                    modules["vendor_dlkm"],
                    key=lambda value: value.as_posix(),
                )
            ),
            vendor_kernel_ramdisk_modules=tuple(
                sorted(
                    modules["vendor_kernel_boot"],
                    key=lambda value: value.as_posix(),
                )
            ),
            vendor_kernel_ramdisk_load=tuple(
                (
                    {
                        PurePosixPath(
                            item.installed_android_path
                        ).name:
                        item.destination
                        for item
                        in vendor_kernel_ramdisk_plan.module_projections
                    }
                )[name]
                for name
                in vendor_kernel_ramdisk_plan.load_module_names
            ),
            system_load_file=load_files.get(
                "system_dlkm"
            ),
            vendor_load_file=load_files.get(
                "vendor_dlkm"
            ),
            system_blocklist_file=(
                blocklist_files.get(
                    "system_dlkm"
                )
            ),
            vendor_blocklist_file=(
                blocklist_files.get(
                    "vendor_dlkm"
                )
            ),
        )

    @staticmethod
    def _render_list(
        variable: str,
        values: tuple[PurePosixPath, ...],
    ) -> list[str]:
        if not values:
            return [
                f"{variable} :=",
                "",
            ]

        lines = [
            f"{variable} := \\",
        ]

        for index, value in enumerate(values):
            suffix = (
                " \\"
                if index < len(values) - 1
                else ""
            )

            lines.append(
                f"    {value.as_posix()}{suffix}"
            )

        lines.append("")

        return lines

    @classmethod
    def render(
        cls,
        config: AndroidDeviceTreeKernelBoardConfig,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreeKernelBoardConfig,
        ):
            raise TypeError(
                "config must be an "
                "AndroidDeviceTreeKernelBoardConfig"
            )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Exact direct DLKM prebuilt integration.",
            "# depmod metadata is regenerated by the Android build system.",
            "",
        ]

        if config.system_modules:
            lines.extend(
                [
                    "BOARD_USES_SYSTEM_DLKMIMAGE := true",
                    "",
                ]
            )

        if config.vendor_modules:
            lines.extend(
                [
                    "BOARD_USES_VENDOR_DLKMIMAGE := true",
                    "",
                    "# Preserve exact reconstructed vendor module bytes.",
                    "BOARD_DO_NOT_STRIP_VENDOR_MODULES := true",
                    "",
                ]
            )

        lines.extend(
            cls._render_list(
                "BOARD_SYSTEM_KERNEL_MODULES",
                config.system_modules,
            )
        )

        lines.extend(
            cls._render_list(
                "BOARD_VENDOR_KERNEL_MODULES",
                config.vendor_modules,
            )
        )

        if config.vendor_kernel_ramdisk_modules:
            lines.extend(
                [
                    "# Preserve exact vendor_kernel_boot module bytes.",
                    (
                        "BOARD_DO_NOT_STRIP_VENDOR_KERNEL_RAMDISK_MODULES "
                        ":= true"
                    ),
                    "",
                ]
            )

        lines.extend(
            cls._render_list(
                "BOARD_VENDOR_KERNEL_RAMDISK_KERNEL_MODULES",
                config.vendor_kernel_ramdisk_modules,
            )
        )

        lines.extend(
            cls._render_list(
                "BOARD_VENDOR_KERNEL_RAMDISK_KERNEL_MODULES_LOAD",
                config.vendor_kernel_ramdisk_load,
            )
        )

        if config.system_load_file is not None:
            lines.extend(
                [
                    (
                        "BOARD_SYSTEM_KERNEL_MODULES_LOAD := "
                        "$(strip $(shell cat "
                        f"{config.system_load_file.as_posix()}))"
                    ),
                    "",
                ]
            )

        if config.vendor_load_file is not None:
            lines.extend(
                [
                    (
                        "BOARD_VENDOR_KERNEL_MODULES_LOAD := "
                        "$(strip $(shell cat "
                        f"{config.vendor_load_file.as_posix()}))"
                    ),
                    "",
                ]
            )

        if config.system_blocklist_file is not None:
            lines.extend(
                [
                    (
                        "BOARD_SYSTEM_KERNEL_MODULES_BLOCKLIST_FILE := "
                        f"{config.system_blocklist_file.as_posix()}"
                    ),
                    "",
                ]
            )

        if config.vendor_blocklist_file is not None:
            lines.extend(
                [
                    (
                        "BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE := "
                        f"{config.vendor_blocklist_file.as_posix()}"
                    ),
                    "",
                ]
            )

        return "\n".join(lines)
