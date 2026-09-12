from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
import xml.etree.ElementTree as ET

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeDerivedVintfSource:
    derived_source_id: str
    source_requirement_id: str
    source_representation_id: str
    source_content_id: str

    destination: PurePosixPath
    text: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("derived_source_id", self.derived_source_id),
            (
                "source_requirement_id",
                self.source_requirement_id,
            ),
            (
                "source_representation_id",
                self.source_representation_id,
            ),
            (
                "source_content_id",
                self.source_content_id,
            ),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "destination must be source-tree relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape the source tree"
            )

        if not isinstance(self.text, str) or not self.text:
            raise ValueError(
                "text must be a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVintfFragmentModule:
    representation_id: str
    module_name: str
    source_path: PurePosixPath
    install_partition: str

    def __post_init__(self) -> None:
        if not self.representation_id:
            raise ValueError(
                "representation_id must not be empty"
            )

        if not self.module_name:
            raise ValueError(
                "module_name must not be empty"
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
                "source_path must be source-tree relative"
            )

        if ".." in self.source_path.parts:
            raise ValueError(
                "source_path must not escape the source tree"
            )

        if self.install_partition not in {
            "vendor",
            "system_ext",
            "vendor_boot",
        }:
            raise ValueError(
                "unsupported VINTF fragment install partition: "
                f"{self.install_partition}"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVintfBuildConfig:
    device_manifest_file: PurePosixPath | None = None
    device_matrix_file: PurePosixPath | None = None
    product_matrix_file: PurePosixPath | None = None

    device_framework_matrix_files: tuple[
        PurePosixPath,
        ...,
    ] = ()

    derived_sources: tuple[
        AndroidDeviceTreeDerivedVintfSource,
        ...,
    ] = ()

    system_ext_manifest_files: tuple[
        PurePosixPath,
        ...,
    ] = ()

    fragment_modules: tuple[
        AndroidDeviceTreeVintfFragmentModule,
        ...,
    ] = ()


class AndroidDeviceTreeVintfBuildRenderer:
    """
    Render only VINTF documents whose concrete Android build ownership is
    proven by canonical factory provenance.

    Physical source origin is derived from Parsing's retained
    AndroidParserFilesystemSource identity. No extraction-path parsing,
    device-name matching, AOSP checkout, or Knowledge fallback is used.

    Supported concrete roles:
    - vendor base device manifest -> DEVICE_MANIFEST_FILE
    - vendor device matrix -> DEVICE_MATRIX_FILE
    - vendor manifest fragment -> vintf_fragment module
    - product framework matrix -> DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE
    - assembled device framework compatibility matrix -> derived source-equivalent DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE
    - system_ext framework manifest fragment -> vintf_fragment module
    - vendor_boot manifest fragment -> vintf_fragment module; final recovery/vendor-ramdisk placement follows boot architecture

    Platform/system, alternate system images, and container/APEX-owned VINTF
    observations remain canonical evidence and are intentionally not rendered
    here.
    """

    @staticmethod
    def _source_name(
        source_representation,
    ) -> str:
        filesystem_source = (
            source_representation
            .requirement
            .source
            .filesystem_source
        )

        source_name = getattr(
            filesystem_source,
            "source_name",
            None,
        )

        if (
            not isinstance(source_name, str)
            or not source_name
        ):
            raise ValueError(
                "VINTF source must retain canonical "
                "filesystem source identity"
            )

        return source_name

    @staticmethod
    def _path_suffix(
        path: PurePosixPath,
    ) -> tuple[str, ...]:
        return tuple(path.parts)

    @staticmethod
    def _local_tag(
        tag: str,
    ) -> str:
        if "}" in tag:
            return tag.rsplit(
                "}",
                1,
            )[1]

        return tag

    @classmethod
    def _derive_device_framework_matrix(
        cls,
        *,
        source_representation,
        source_content,
        identity: AndroidDeviceTreeIdentity,
    ) -> (
        AndroidDeviceTreeDerivedVintfSource
        | None
    ):
        """
        Reverse only the source-authored portion of an assembled
        framework_compatibility_matrix.device.xml.

        AOSP's device framework-matrix build adds SEPolicy and AVB
        metadata while assembling the final matrix. Those generated
        sections are final-build output and must not be replayed as
        DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE source input.

        Every other top-level compatibility requirement remains
        source-declarable evidence and is preserved in the derived
        source-equivalent matrix.
        """

        raw = source_content.text

        if not isinstance(raw, str) or not raw:
            raise ValueError(
                "device framework matrix requires "
                "exact canonical XML text"
            )

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError(
                "device framework matrix contains invalid XML"
            ) from exc

        if (
            cls._local_tag(root.tag)
            != "compatibility-matrix"
        ):
            raise ValueError(
                "device framework matrix root must be "
                "compatibility-matrix"
            )

        if root.attrib.get("type") != "framework":
            raise ValueError(
                "device framework matrix must be "
                "framework-side"
            )

        #
        # framework_compatibility_matrix.device.xml is the
        # common/device extension matrix, not one numbered FCM.
        #
        # A levelled observed document is not safely invertible by
        # this source-equivalent projection.
        #
        if "level" in root.attrib:
            raise ValueError(
                "assembled device framework matrix "
                "unexpectedly contains a level attribute"
            )

        unexpected_root_attributes = (
            set(root.attrib)
            - {
                "version",
                "type",
            }
        )

        if unexpected_root_attributes:
            raise ValueError(
                "assembled device framework matrix contains "
                "unsupported root attributes: "
                f"{sorted(unexpected_root_attributes)!r}"
            )

        #
        # assemble_vintf injects these into the final
        # framework_compatibility_matrix.device.xml.
        #
        # They are build output, not source requirements.
        #
        generated_tags = {
            "sepolicy",
            "avb",
        }

        retained_children = tuple(
            deepcopy(child)
            for child in root
            if (
                cls._local_tag(child.tag)
                not in generated_tags
            )
        )

        #
        # If nothing source-authored remains, the original build did
        # not require a DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE
        # contribution at all.
        #
        if not retained_children:
            return None

        derived_root = ET.Element(
            root.tag,
            dict(root.attrib),
        )

        for child in retained_children:
            derived_root.append(child)

        ET.indent(
            derived_root,
            space="    ",
        )

        rendered = ET.tostring(
            derived_root,
            encoding="unicode",
            short_empty_elements=True,
        )

        if not rendered.endswith("\n"):
            rendered += "\n"

        #
        # Fail closed on the exact invariant this projection owns.
        #
        check_root = ET.fromstring(rendered)

        if any(
            cls._local_tag(child.tag)
            in generated_tags
            for child in check_root
        ):
            raise ValueError(
                "derived device framework matrix retained "
                "assemble_vintf-generated metadata"
            )

        digest = sha256(
            source_representation
            .representation_id
            .encode("utf-8")
        ).hexdigest()[:12]

        destination = (
            PurePosixPath(
                identity.device_root.as_posix()
            )
            / "vintf"
            / "derived"
            / (
                "framework_compatibility_matrix-"
                f"{digest}.xml"
            )
        )

        return AndroidDeviceTreeDerivedVintfSource(
            derived_source_id=(
                "vintf-derived-framework-matrix:"
                f"{source_representation.representation_id}"
            ),
            source_requirement_id=(
                source_representation
                .requirement
                .requirement_id
            ),
            source_representation_id=(
                source_representation
                .representation_id
            ),
            source_content_id=(
                source_content.content_id
            ),
            destination=destination,
            text=rendered,
        )

    @classmethod
    def project(
        cls,
        *,
        reconstruction: AndroidReconstructionResult,
        identity: AndroidDeviceTreeIdentity,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> AndroidDeviceTreeVintfBuildConfig:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an AndroidReconstructionResult"
            )

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

        representation_by_id = {
            item.representation_id: item
            for item
            in reconstruction.vintf_document_representations
        }

        source_by_content_id = {}
        content_by_id = {}

        for content in reconstruction.vintf_source_contents:
            source = representation_by_id.get(
                content.representation_id
            )

            if source is None:
                raise ValueError(
                    "VINTF content has no exact source representation: "
                    f"{content.content_id}"
                )

            source_by_content_id[
                content.content_id
            ] = source

            content_by_id[
                content.content_id
            ] = content

        device_manifest_file = None
        device_matrix_file = None
        product_matrix_file = None

        device_framework_matrix_files = []
        derived_sources = []
        system_ext_manifest_files = []
        fragment_modules = []

        seen_module_names = set()

        for realization in realizations:
            if (
                realization.kind
                is not
                AndroidDeviceTreeBuildRealizationKind
                .VINTF_DOCUMENT
            ):
                continue

            if (
                realization.status
                is not
                AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            ):
                continue

            representation = (
                realization.build_representation
            )

            if (
                representation.kind
                is not
                AndroidReconstructionBuildRepresentationKind
                .VINTF_DOCUMENT
            ):
                raise ValueError(
                    "resolved VINTF realization changed "
                    "Reconstruction build role"
                )

            if representation.source_content_id is None:
                raise ValueError(
                    "resolved VINTF realization requires "
                    "source_content_id"
                )

            source = source_by_content_id.get(
                representation.source_content_id
            )

            if source is None:
                raise ValueError(
                    "resolved VINTF realization has no "
                    "canonical VINTF source"
                )

            if realization.source_path is None:
                raise ValueError(
                    "resolved VINTF realization requires "
                    "source_path"
                )

            android_path = source.android_path

            if android_path is None:
                raise ValueError(
                    "resolved VINTF realization requires "
                    "canonical Android path"
                )

            source_name = cls._source_name(source)

            parts = tuple(android_path.parts)

            is_base_manifest = (
                len(parts) >= 3
                and parts[-3:] == (
                    "etc",
                    "vintf",
                    "manifest.xml",
                )
            )

            is_base_matrix = (
                len(parts) >= 3
                and parts[-3:] == (
                    "etc",
                    "vintf",
                    "compatibility_matrix.xml",
                )
            )

            document_kind = getattr(
                source.document_kind,
                "value",
                None,
            )

            document_side = getattr(
                source.document_side,
                "value",
                None,
            )

            is_device_framework_matrix = (
                document_kind == "compatibility-matrix"
                and document_side == "framework"
                and len(parts) >= 3
                and parts[-3:] == (
                    "etc",
                    "vintf",
                    "compatibility_matrix.device.xml",
                )
            )

            is_system_ext_framework_base_manifest = (
                source_name == "system_ext"
                and document_kind == "manifest"
                and document_side == "framework"
                and is_base_manifest
            )

            is_manifest_fragment = (
                len(parts) >= 4
                and parts[-3:-1] == (
                    "vintf",
                    "manifest",
                )
                and parts[-1].endswith(".xml")
            )

            if (
                source_name == "vendor"
                and is_base_manifest
            ):
                if device_manifest_file is not None:
                    raise ValueError(
                        "multiple resolved vendor base manifests"
                    )

                device_manifest_file = (
                    realization.source_path
                )
                continue

            if is_device_framework_matrix:
                source_content = content_by_id.get(
                    representation.source_content_id
                )

                if source_content is None:
                    raise ValueError(
                        "resolved device framework matrix "
                        "has no canonical source content"
                    )

                derived_source = (
                    cls._derive_device_framework_matrix(
                        source_representation=source,
                        source_content=source_content,
                        identity=identity,
                    )
                )

                if derived_source is not None:
                    if (
                        derived_source.destination
                        in device_framework_matrix_files
                    ):
                        raise ValueError(
                            "duplicate derived device framework "
                            "matrix destination"
                        )

                    device_framework_matrix_files.append(
                        derived_source.destination
                    )

                    derived_sources.append(
                        derived_source
                    )

                continue

            if (
                source_name == "vendor"
                and is_base_matrix
            ):
                if device_matrix_file is not None:
                    raise ValueError(
                        "multiple resolved vendor device matrices"
                    )

                device_matrix_file = (
                    realization.source_path
                )
                continue

            if (
                source_name == "product"
                and is_base_matrix
            ):
                if product_matrix_file is not None:
                    raise ValueError(
                        "multiple resolved product matrices"
                    )

                product_matrix_file = (
                    realization.source_path
                )
                continue

            if (
                is_system_ext_framework_base_manifest
            ):
                raise ValueError(
                    "system_ext framework base manifest is an "
                    "assembled platform/framework output and "
                    "must remain canonical evidence rather than "
                    "a concrete Device Tree VINTF input"
                )

            if (
                source_name
                in {
                    "vendor",
                    "system_ext",
                    "vendor_boot",
                }
                and is_manifest_fragment
            ):
                if realization.module_name is None:
                    raise ValueError(
                        "resolved VINTF fragment requires "
                        "concrete module_name"
                    )

                if (
                    realization.module_name
                    in seen_module_names
                ):
                    raise ValueError(
                        "duplicate VINTF fragment module name: "
                        f"{realization.module_name}"
                    )

                seen_module_names.add(
                    realization.module_name
                )

                fragment_modules.append(
                    AndroidDeviceTreeVintfFragmentModule(
                        representation_id=(
                            realization.representation_id
                        ),
                        module_name=(
                            realization.module_name
                        ),
                        source_path=(
                            realization.source_path
                        ),
                        install_partition=source_name,
                    )
                )
                continue

            raise ValueError(
                "resolved VINTF realization has no supported "
                "concrete renderer disposition: "
                f"source={source_name!r}, "
                f"path={android_path.as_posix()!r}"
            )

        return AndroidDeviceTreeVintfBuildConfig(
            device_manifest_file=device_manifest_file,
            device_matrix_file=device_matrix_file,
            product_matrix_file=product_matrix_file,
            device_framework_matrix_files=tuple(
                sorted(
                    device_framework_matrix_files,
                    key=lambda value: value.as_posix(),
                )
            ),
            derived_sources=tuple(
                sorted(
                    derived_sources,
                    key=lambda value: (
                        value.destination.as_posix(),
                        value.derived_source_id,
                    ),
                )
            ),
            system_ext_manifest_files=tuple(
                sorted(
                    system_ext_manifest_files,
                    key=lambda value: value.as_posix(),
                )
            ),
            fragment_modules=tuple(
                sorted(
                    fragment_modules,
                    key=lambda value: (
                        value.module_name,
                        value.representation_id,
                    ),
                )
            ),
        )

    @staticmethod
    def render_board_config(
        config: AndroidDeviceTreeVintfBuildConfig,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreeVintfBuildConfig,
        ):
            raise TypeError(
                "config must be an AndroidDeviceTreeVintfBuildConfig"
            )

        lines = [
            "# Canonical factory-derived VINTF integration.",
        ]

        if config.device_manifest_file is not None:
            lines.append(
                "DEVICE_MANIFEST_FILE := "
                + config.device_manifest_file.as_posix()
            )

        if config.device_matrix_file is not None:
            lines.append(
                "DEVICE_MATRIX_FILE := "
                + config.device_matrix_file.as_posix()
            )

        if config.product_matrix_file is not None:
            lines.append(
                "DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE := "
                + config.product_matrix_file.as_posix()
            )

        if config.device_framework_matrix_files:
            lines.append(
                "DEVICE_FRAMEWORK_COMPATIBILITY_MATRIX_FILE += "
                + " ".join(
                    path.as_posix()
                    for path
                    in config.device_framework_matrix_files
                )
            )

        if config.system_ext_manifest_files:
            lines.append(
                "SYSTEM_EXT_MANIFEST_FILES += \\"
            )

            for index, path in enumerate(
                config.system_ext_manifest_files
            ):
                suffix = (
                    " \\"
                    if index
                    < len(
                        config.system_ext_manifest_files
                    ) - 1
                    else ""
                )

                lines.append(
                    "    "
                    + path.as_posix()
                    + suffix
                )

        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def render_android_bp(
        config: AndroidDeviceTreeVintfBuildConfig,
        *,
        vintf_root: PurePosixPath,
        vendor_boot_as_recovery: bool = False,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreeVintfBuildConfig,
        ):
            raise TypeError(
                "config must be an AndroidDeviceTreeVintfBuildConfig"
            )

        if not isinstance(
            vendor_boot_as_recovery,
            bool,
        ):
            raise TypeError(
                "vendor_boot_as_recovery must be a bool"
            )

        lines = [
            "// Generated by TreeForge.",
            "// Canonical factory-derived VINTF fragments.",
            "",
        ]

        for module in config.fragment_modules:
            try:
                relative_source = (
                    module.source_path.relative_to(
                        vintf_root
                    )
                )
            except ValueError as exc:
                raise ValueError(
                    "VINTF fragment source must live under "
                    "the canonical generated VINTF root: "
                    f"{module.source_path.as_posix()}"
                ) from exc

            lines.extend(
                [
                    "vintf_fragment {",
                    f'    name: "{module.module_name}",',
                    f'    src: "{relative_source.as_posix()}",',
                ]
            )

            if module.install_partition == "vendor":
                lines.append(
                    "    vendor: true,"
                )
            elif (
                module.install_partition
                == "vendor_boot"
            ):
                if vendor_boot_as_recovery:
                    lines.append(
                        "    recovery: true,"
                    )
                else:
                    lines.append(
                        "    vendor_ramdisk: true,"
                    )
            elif (
                module.install_partition
                == "system_ext"
            ):
                lines.append(
                    "    system_ext_specific: true,"
                )
            else:
                raise ValueError(
                    "unsupported VINTF fragment partition"
                )

            lines.extend(
                [
                    "}",
                    "",
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def product_packages(
        config: AndroidDeviceTreeVintfBuildConfig,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                module.module_name
                for module
                in config.fragment_modules
            )
        )
