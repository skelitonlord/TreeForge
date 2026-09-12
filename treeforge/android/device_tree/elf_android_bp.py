from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)
from treeforge.android.reconstruction.build_system.elf import (
    AndroidReconstructionElfBuildSemantics,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeElfAndroidBpModule:
    """
    One TreeForge-owned Android.bp module declaration for an independently
    materialized DIRECT_PARTITION ELF payload.

    module_name is a generated Device Tree identity. It is not an assertion
    about the OEM's original Make/Soong module identity.

    source_path is relative to the generated proprietary package root.
    installed_filename and relative_install_path preserve the exact observed
    runtime destination independently from module identity.
    """

    representation_id: str
    module_name: str
    module_type: str

    source_path: PurePosixPath

    arch: str

    installed_partition: str
    build_partition: str
    installed_android_path: str

    installed_filename: str
    relative_install_path: str | None

    realization: AndroidDeviceTreeBuildRealization

    def __post_init__(self) -> None:
        for field_name, value in (
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "module_name",
                self.module_name,
            ),
            (
                "module_type",
                self.module_type,
            ),
            (
                "arch",
                self.arch,
            ),
            (
                "installed_partition",
                self.installed_partition,
            ),
            (
                "build_partition",
                self.build_partition,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
            ),
            (
                "installed_filename",
                self.installed_filename,
            ),
        ):
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a "
                    "non-empty string"
                )

        if self.module_type not in {
            "cc_prebuilt_library_shared",
            "cc_prebuilt_binary",
        }:
            raise ValueError(
                "unsupported ELF Android.bp module type: "
                f"{self.module_type}"
            )

        if (
            self.module_type
            == "cc_prebuilt_library_shared"
            and not self.installed_filename.endswith(
                ".so"
            )
        ):
            raise ValueError(
                "shared-library prebuilt filename must end in .so: "
                f"{self.installed_filename!r}"
            )

        if self.arch not in {
            "arm",
            "arm64",
            "x86",
            "x86_64",
            "riscv64",
        }:
            raise ValueError(
                "unsupported ELF Android.bp architecture: "
                f"{self.arch}"
            )

        if not isinstance(
            self.source_path,
            PurePosixPath,
        ):
            raise TypeError(
                "source_path must be a PurePosixPath"
            )

        if self.source_path.is_absolute():
            raise ValueError(
                "source_path must be relative to "
                "the proprietary package root"
            )

        if ".." in self.source_path.parts:
            raise ValueError(
                "source_path must not escape "
                "the proprietary package root"
            )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if (
            self.relative_install_path is not None
            and (
                not isinstance(
                    self.relative_install_path,
                    str,
                )
                or not self.relative_install_path
            )
        ):
            raise ValueError(
                "relative_install_path must be a "
                "non-empty string or None"
            )

        if (
            not isinstance(
                self.realization,
                AndroidDeviceTreeBuildRealization,
            )
        ):
            raise TypeError(
                "realization must be an "
                "AndroidDeviceTreeBuildRealization"
            )

        if (
            self.realization.representation_id
            != self.representation_id
        ):
            raise ValueError(
                "Android.bp module changed exact "
                "Device Tree realization identity"
            )

        if (
            self.realization.module_name
            != self.module_name
        ):
            raise ValueError(
                "Android.bp module changed TreeForge "
                "module identity"
            )


class AndroidDeviceTreeElfAndroidBpRenderer:
    """
    Render concrete DIRECT_PARTITION ELF realizations into minimal,
    deterministic Android.bp prebuilt declarations.

    Runtime Linking / Reconstruction physical dependency edges remain
    authoritative upstream and are intentionally not converted into Soong
    shared_libs here. DT_NEEDED resolution does not itself prove the original
    or equivalent source-build linkage declaration.
    """

    _PARTITION_ROOT_COMPONENTS = {
        "system": (),
        "vendor": ("vendor",),
        "product": ("product",),
        "system_ext": ("system_ext",),
        "odm": ("odm",),
    }

    @classmethod
    def project(
        cls,
        *,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
        elf_build_semantics: tuple[
            AndroidReconstructionElfBuildSemantics,
            ...,
        ],
        physical_payload_projections,
        proprietary_root: PurePosixPath,
    ) -> tuple[
        AndroidDeviceTreeElfAndroidBpModule,
        ...,
    ]:
        if not isinstance(
            realizations,
            tuple,
        ):
            raise TypeError(
                "realizations must be a tuple"
            )

        if not isinstance(
            elf_build_semantics,
            tuple,
        ):
            raise TypeError(
                "elf_build_semantics must be a tuple"
            )

        if not all(
            isinstance(
                semantics,
                AndroidReconstructionElfBuildSemantics,
            )
            for semantics
            in elf_build_semantics
        ):
            raise TypeError(
                "elf_build_semantics contains an invalid model"
            )

        if not isinstance(
            physical_payload_projections,
            tuple,
        ):
            raise TypeError(
                "physical_payload_projections must be a tuple"
            )

        if not isinstance(
            proprietary_root,
            PurePosixPath,
        ):
            raise TypeError(
                "proprietary_root must be a PurePosixPath"
            )

        elf_semantics_by_representation_id = {}

        for semantics in elf_build_semantics:
            target_id = (
                semantics.target_build_representation_id
            )

            if target_id is None:
                continue

            if (
                target_id
                in elf_semantics_by_representation_id
            ):
                raise ValueError(
                    "multiple canonical ELF semantics objects "
                    "target one Reconstruction representation: "
                    f"{target_id}"
                )

            elf_semantics_by_representation_id[
                target_id
            ] = semantics

        physical_by_representation_id = {
            projection.representation_id:
            projection
            for projection
            in physical_payload_projections
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

        modules = []

        seen_representation_ids = set()
        seen_module_names = set()

        for realization in realizations:
            representation = (
                realization.build_representation
            )

            if representation.kind not in {
                AndroidReconstructionBuildRepresentationKind
                .NATIVE_LIBRARY,
                AndroidReconstructionBuildRepresentationKind
                .EXECUTABLE,
            }:
                continue

            if (
                realization.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            ):
                continue

            if (
                realization.kind
                is AndroidDeviceTreeBuildRealizationKind
                .COPY_FILE
            ):
                continue

            if (
                realization.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .PREBUILT_MODULE
            ):
                raise ValueError(
                    "resolved module-backed ELF realization "
                    "must use PREBUILT_MODULE"
                )

            if (
                realization.source_path is None
                or realization.module_name is None
            ):
                raise ValueError(
                    "resolved ELF realization requires "
                    "source_path and module_name"
                )

            projection = (
                physical_by_representation_id.get(
                    realization.representation_id
                )
            )

            if projection is None:
                raise ValueError(
                    "resolved ELF realization has no exact "
                    "physical payload projection: "
                    f"{realization.representation_id}"
                )

            if (
                projection.build_representation
                is not representation
            ):
                raise ValueError(
                    "ELF Android.bp projection changed exact "
                    "Reconstruction representation identity"
                )

            source_path = (
                realization.source_path
            )

            try:
                package_source_path = (
                    source_path.relative_to(
                        proprietary_root
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "ELF source path does not reside beneath "
                    "the proprietary package root: "
                    f"{source_path}"
                ) from error

            installed_path = PurePosixPath(
                representation.installed_android_path
            )

            if not installed_path.is_absolute():
                raise ValueError(
                    "ELF installed Android path must be absolute"
                )

            path_parts = tuple(
                installed_path.parts[1:]
            )

            if not path_parts:
                raise ValueError(
                    "ELF installed Android path must identify a file"
                )

            filename = path_parts[-1]

            parent_parts = path_parts[:-1]

            partition = (
                representation.installed_partition
            )

            if partition is None:
                raise ValueError(
                    "ELF realization requires installed partition"
                )

            explicit_build_partition = None

            for candidate in (
                "system_ext",
                "product",
                "vendor",
                "odm",
                "system",
            ):
                if (
                    path_parts
                    and path_parts[0] == candidate
                ):
                    explicit_build_partition = candidate
                    break

            build_partition = (
                explicit_build_partition
                if explicit_build_partition is not None
                else partition
            )

            partition_prefix = (
                cls._PARTITION_ROOT_COMPONENTS.get(
                    build_partition
                )
            )

            if partition_prefix is None:
                raise ValueError(
                    "unsupported Android build partition for ELF "
                    "Android.bp rendering: "
                    f"physical_partition={partition!r}, "
                    f"build_partition={build_partition!r}, "
                    "installed_android_path="
                    f"{representation.installed_android_path!r}, "
                    "representation="
                    f"{realization.representation_id!r}"
                )

            if (
                explicit_build_partition is not None
                and parent_parts
                and parent_parts[0]
                == explicit_build_partition
            ):
                parent_parts = parent_parts[1:]

            elif (
                partition_prefix
                and parent_parts[
                    :len(partition_prefix)
                ]
                == partition_prefix
            ):
                parent_parts = parent_parts[
                    len(partition_prefix):
                ]

            if (
                parent_parts
                and parent_parts[0]
                in {
                    "lib",
                    "lib64",
                    "bin",
                }
            ):
                relative_parts = (
                    parent_parts[1:]
                )
            else:
                relative_parts = parent_parts

            relative_install_path = (
                "/".join(relative_parts)
                if relative_parts
                else None
            )

            semantics = (
                elf_semantics_by_representation_id.get(
                    realization.representation_id
                )
            )

            if semantics is None:
                raise ValueError(
                    "resolved ELF realization has no exact "
                    "Reconstruction ELF build semantics: "
                    f"{realization.representation_id}"
                )

            if (
                semantics.target_build_representation_id
                != realization.representation_id
            ):
                raise ValueError(
                    "ELF Android.bp projection changed exact "
                    "Reconstruction ELF attachment identity"
                )

            requirement = semantics.requirement

            arch = requirement.android_architecture

            if arch is None:
                raise ValueError(
                    "canonical ELF requirement has no supported "
                    "Android architecture interpretation: "
                    f"{requirement.machine!r} for "
                    f"{realization.representation_id}"
                )

            if (
                representation.kind
                is AndroidReconstructionBuildRepresentationKind
                .NATIVE_LIBRARY
            ):
                module_type = (
                    "cc_prebuilt_library_shared"
                )
            else:
                module_type = (
                    "cc_prebuilt_binary"
                )

            module = (
                AndroidDeviceTreeElfAndroidBpModule(
                    representation_id=(
                        realization.representation_id
                    ),
                    module_name=(
                        realization.module_name
                    ),
                    module_type=module_type,
                    source_path=(
                        PurePosixPath(
                            package_source_path.as_posix()
                        )
                    ),
                    arch=arch,
                    installed_partition=partition,
                    build_partition=build_partition,
                    installed_android_path=(
                        representation
                        .installed_android_path
                    ),
                    installed_filename=filename,
                    relative_install_path=(
                        relative_install_path
                    ),
                    realization=realization,
                )
            )

            if (
                module.representation_id
                in seen_representation_ids
            ):
                raise ValueError(
                    "duplicate ELF Android.bp representation"
                )

            if (
                module.module_name
                in seen_module_names
            ):
                raise ValueError(
                    "duplicate ELF Android.bp module name"
                )

            seen_representation_ids.add(
                module.representation_id
            )

            seen_module_names.add(
                module.module_name
            )

            modules.append(module)

        expected_ids = {
            realization.representation_id
            for realization
            in realizations
            if (
                realization.status
                is AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
                and realization.kind
                is AndroidDeviceTreeBuildRealizationKind
                .PREBUILT_MODULE
                and realization
                .build_representation
                .kind
                in {
                    AndroidReconstructionBuildRepresentationKind
                    .NATIVE_LIBRARY,
                    AndroidReconstructionBuildRepresentationKind
                    .EXECUTABLE,
                }
            )
        }

        if seen_representation_ids != expected_ids:
            raise ValueError(
                "ELF Android.bp module projection "
                "coverage mismatch"
            )

        return tuple(
            sorted(
                modules,
                key=lambda module: (
                    module.module_name
                ),
            )
        )

    @classmethod
    def render(
        cls,
        modules: tuple[
            AndroidDeviceTreeElfAndroidBpModule,
            ...,
        ],
    ) -> str:
        if not isinstance(
            modules,
            tuple,
        ):
            raise TypeError(
                "modules must be a tuple"
            )

        lines = [
            "// Generated by TreeForge.",
            "//",
            "// Module names in this file are TreeForge-owned generated",
            "// identities. They do not claim to reproduce the OEM's",
            "// original Make/Soong module names.",
            "",
        ]

        for module in modules:
            lines.extend(
                cls._render_module(
                    module
                )
            )

            lines.append("")

        return "\n".join(lines)

    @classmethod
    def _render_module(
        cls,
        module: AndroidDeviceTreeElfAndroidBpModule,
    ) -> list[str]:
        lines = [
            f"{module.module_type} {{",
            (
                '    name: '
                f'"{module.module_name}",'
            ),
        ]

        if module.build_partition == "vendor":
            lines.append(
                "    vendor: true,"
            )

        elif module.build_partition == "product":
            lines.append(
                "    product_specific: true,"
            )

        elif module.build_partition == "system_ext":
            lines.append(
                "    system_ext_specific: true,"
            )

        elif module.build_partition == "odm":
            lines.append(
                "    device_specific: true,"
            )

        elif module.build_partition != "system":
            raise ValueError(
                "unsupported ELF Android.bp build partition: "
                f"{module.build_partition} "
                f"(physical={module.installed_partition})"
            )

        lines.extend(
            [
                (
                    '    stem: '
                    f'"{module.installed_filename[:-3] if module.module_type == "cc_prebuilt_library_shared" else module.installed_filename}",'
                ),
                "    strip: {",
                "        none: true,",
                "    },",
                "    check_elf_files: false,",
                "    prefer: true,",
            ]
        )

        if (
            module.relative_install_path
            is not None
        ):
            lines.append(
                "    relative_install_path: "
                f'"{module.relative_install_path}",'
            )

        lines.extend(
            [
                "    arch: {",
                f"        {module.arch}: {{",
                (
                    "            srcs: "
                    f'["{module.source_path.as_posix()}"],'
                ),
                "        },",
                "    },",
                "}",
            ]
        )

        return lines
