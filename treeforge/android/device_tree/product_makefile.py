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
from treeforge.android.device_tree.artifact_projection import (
    AndroidDeviceTreeArtifactProjection,
)
from treeforge.android.device_tree.physical_payload_projection import (
    AndroidDeviceTreePhysicalPayloadProjection,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeProductCopyFile:
    """
    One exact Device Tree COPY_FILE realization rendered as
    PRODUCT_COPY_FILES syntax.
    """

    representation_id: str
    source_path: PurePosixPath
    installed_partition: str
    installed_android_path: str
    destination: str

    def __post_init__(self) -> None:
        for field_name, value in (
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "installed_partition",
                self.installed_partition,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
            ),
            (
                "destination",
                self.destination,
            ),
        ):
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
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
                "source_path must be relative to the "
                "Device Tree workspace"
            )

        if ".." in self.source_path.parts:
            raise ValueError(
                "source_path must not escape the "
                "Device Tree workspace"
            )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

    @property
    def make_entry(self) -> str:
        return (
            f"{self.source_path.as_posix()}:"
            f"{self.destination}"
        )


class AndroidDeviceTreeProductMakefileRenderer:
    """
    Render resolved Device Tree COPY_FILE realizations into a
    deterministic vendor product makefile.

    Device Tree does not infer module identity here. PRODUCT_PACKAGE
    realizations remain outside this renderer until a concrete module
    identity is independently established.
    """

    _TARGET_COPY_OUT_BY_PARTITION = {
        "system": "$(TARGET_COPY_OUT_SYSTEM)",
        "vendor": "$(TARGET_COPY_OUT_VENDOR)",
        "product": "$(TARGET_COPY_OUT_PRODUCT)",
        "system_ext": "$(TARGET_COPY_OUT_SYSTEM_EXT)",
        "odm": "$(TARGET_COPY_OUT_ODM)",
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
        artifact_projections: tuple[
            AndroidDeviceTreeArtifactProjection,
            ...,
        ],
        physical_payload_projections: tuple[
            AndroidDeviceTreePhysicalPayloadProjection,
            ...,
        ],
    ) -> tuple[
        AndroidDeviceTreeProductCopyFile,
        ...,
    ]:
        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        if not isinstance(
            realizations,
            tuple,
        ):
            raise TypeError(
                "realizations must be a tuple"
            )

        if not isinstance(
            artifact_projections,
            tuple,
        ):
            raise TypeError(
                "artifact_projections must be a tuple"
            )

        if not all(
            isinstance(
                projection,
                AndroidDeviceTreeArtifactProjection,
            )
            for projection
            in artifact_projections
        ):
            raise TypeError(
                "artifact_projections must contain only "
                "AndroidDeviceTreeArtifactProjection values"
            )

        if not isinstance(
            physical_payload_projections,
            tuple,
        ):
            raise TypeError(
                "physical_payload_projections must be a tuple"
            )

        if not all(
            isinstance(
                projection,
                AndroidDeviceTreePhysicalPayloadProjection,
            )
            for projection
            in physical_payload_projections
        ):
            raise TypeError(
                "physical_payload_projections must contain only "
                "AndroidDeviceTreePhysicalPayloadProjection values"
            )

        artifact_by_representation_id = {
            projection.representation_id:
            projection
            for projection
            in artifact_projections
        }

        if len(
            artifact_by_representation_id
        ) != len(
            artifact_projections
        ):
            raise ValueError(
                "preserved Artifact projection identities "
                "must be unique"
            )

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

        overlapping_projection_ids = (
            set(artifact_by_representation_id)
            & set(physical_by_representation_id)
        )

        if overlapping_projection_ids:
            raise ValueError(
                "one Reconstruction representation cannot have "
                "both preserved-Artifact and requirement-backed "
                "physical payload projections"
            )

        copy_realizations = tuple(
            realization
            for realization
            in realizations
            if (
                realization.kind
                is AndroidDeviceTreeBuildRealizationKind
                .COPY_FILE
                and realization.status
                is AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            )
        )

        projected = []

        seen_representation_ids = set()
        seen_destinations = set()

        for realization in copy_realizations:
            representation_id = (
                realization.representation_id
            )

            representation = (
                realization.build_representation
            )

            if (
                representation.preserved_artifact_id
                is not None
            ):
                projection = (
                    artifact_by_representation_id.get(
                        representation_id
                    )
                )

                projection_description = (
                    "preserved Artifact"
                )

            else:
                projection = (
                    physical_by_representation_id.get(
                        representation_id
                    )
                )

                projection_description = (
                    "requirement-backed physical payload"
                )

            if projection is None:
                raise ValueError(
                    "resolved COPY_FILE realization has no "
                    f"exact {projection_description} projection: "
                    f"{representation_id}"
                )

            if (
                projection.build_representation
                is not realization.build_representation
            ):
                raise ValueError(
                    "COPY_FILE product projection changed "
                    "exact Reconstruction representation identity: "
                    f"{representation_id}"
                )

            if realization.source_path is None:
                raise ValueError(
                    "resolved COPY_FILE realization requires "
                    "an exact Device Tree source_path: "
                    f"{representation_id}"
                )

            if (
                realization.source_path
                != projection.destination
            ):
                raise ValueError(
                    "COPY_FILE realization source_path must equal "
                    "its exact physical payload destination: "
                    f"{representation_id}"
                )

            installed_partition = (
                projection.installed_partition
            )

            installed_path = PurePosixPath(
                projection.installed_android_path
            )

            if not installed_path.is_absolute():
                raise ValueError(
                    "COPY_FILE installed Android path must be "
                    "absolute: "
                    f"{representation_id}"
                )

            parts = list(
                installed_path.parts[1:]
            )

            if not parts:
                raise ValueError(
                    "COPY_FILE installed Android path must "
                    "identify a file: "
                    f"{representation_id}"
                )

            #
            # The canonical installed partition is the physical
            # filesystem container. The Android path may repeat that
            # physical prefix:
            #
            #   system:/system/lib/foo.so
            #   system_other:/system_other/product/app/Foo/Foo.odex
            #
            # Remove that exact physical prefix first. This does not
            # reinterpret partition ownership; it only converts the
            # absolute canonical Android path into a path relative to
            # the physical filesystem root.
            #
            if (
                parts
                and parts[0]
                == installed_partition
            ):
                parts = parts[1:]

            if not parts:
                raise ValueError(
                    "COPY_FILE installed Android path must "
                    "identify a partition-relative file: "
                    f"{representation_id}"
                )

            #
            # Normal Android partitions map directly to their product
            # output roots.
            #
            # Some physical filesystem containers do not themselves
            # represent an Android product-output namespace. In that
            # case, the canonical Android path must expose the logical
            # namespace as its next component. Consume that component
            # mechanically rather than hardcoding a physical-partition
            # alias.
            #
            logical_partition = installed_partition

            target_root = (
                cls._TARGET_COPY_OUT_BY_PARTITION.get(
                    logical_partition
                )
            )

            if target_root is None:
                logical_partition = parts[0]

                target_root = (
                    cls._TARGET_COPY_OUT_BY_PARTITION.get(
                        logical_partition
                    )
                )

                if target_root is None:
                    raise ValueError(
                        "COPY_FILE product renderer cannot derive "
                        "a supported logical Android install "
                        "namespace from canonical evidence: "
                        f"physical_partition="
                        f"{installed_partition!r}, "
                        f"installed_path="
                        f"{projection.installed_android_path!r}, "
                        f"representation="
                        f"{representation_id}"
                    )

                parts = parts[1:]

                if not parts:
                    raise ValueError(
                        "COPY_FILE logical Android namespace "
                        "must contain a file path: "
                        f"{representation_id}"
                    )

            relative_install_path = (
                PurePosixPath(*parts)
            )

            destination = (
                f"{target_root}/"
                f"{relative_install_path.as_posix()}"
            )

            if (
                representation_id
                in seen_representation_ids
            ):
                raise ValueError(
                    "duplicate COPY_FILE representation identity: "
                    f"{representation_id}"
                )

            if destination in seen_destinations:
                raise ValueError(
                    "multiple COPY_FILE realizations target the "
                    "same Android install destination: "
                    f"{destination}"
                )

            projected.append(
                AndroidDeviceTreeProductCopyFile(
                    representation_id=(
                        representation_id
                    ),
                    source_path=(
                        realization.source_path
                    ),
                    installed_partition=(
                        installed_partition
                    ),
                    installed_android_path=(
                        projection.installed_android_path
                    ),
                    destination=destination,
                )
            )

            seen_representation_ids.add(
                representation_id
            )

            seen_destinations.add(
                destination
            )

        expected_ids = {
            realization.representation_id
            for realization
            in copy_realizations
        }

        if seen_representation_ids != expected_ids:
            raise ValueError(
                "COPY_FILE product projection coverage mismatch"
            )

        return tuple(
            sorted(
                projected,
                key=lambda item: (
                    item.destination,
                    item.source_path.as_posix(),
                    item.representation_id,
                ),
            )
        )

    @staticmethod
    def render(
        copy_files: tuple[
            AndroidDeviceTreeProductCopyFile,
            ...,
        ],
        *,
        product_packages: tuple[str, ...] = (),
    ) -> str:
        if not isinstance(
            copy_files,
            tuple,
        ):
            raise TypeError(
                "copy_files must be a tuple"
            )

        if not isinstance(
            product_packages,
            tuple,
        ):
            raise TypeError(
                "product_packages must be a tuple"
            )

        if not all(
            isinstance(module_name, str)
            and module_name
            for module_name
            in product_packages
        ):
            raise ValueError(
                "product_packages must contain only "
                "non-empty strings"
            )

        if len(
            product_packages
        ) != len(
            set(product_packages)
        ):
            raise ValueError(
                "product_packages must be unique"
            )

        if product_packages != tuple(
            sorted(product_packages)
        ):
            raise ValueError(
                "product_packages must use deterministic ordering"
            )

        if (
            not copy_files
            and not product_packages
        ):
            return (
                "# Generated by TreeForge.\n"
                "# No vendor product entries are currently resolved.\n"
            )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Exact resolved Device Tree product integration.",
            "",
        ]

        if copy_files:
            lines.append(
                "PRODUCT_COPY_FILES += \\"
            )

            for index, copy_file in enumerate(
                copy_files
            ):
                suffix = (
                    " \\"
                    if index
                    < len(copy_files) - 1
                    else ""
                )

                lines.append(
                    (
                        "    "
                        f"{copy_file.make_entry}"
                        f"{suffix}"
                    )
                )

            lines.append("")

        if product_packages:
            lines.append(
                "PRODUCT_PACKAGES += \\"
            )

            for index, module_name in enumerate(
                product_packages
            ):
                suffix = (
                    " \\"
                    if index
                    < len(product_packages) - 1
                    else ""
                )

                lines.append(
                    (
                        "    "
                        f"{module_name}"
                        f"{suffix}"
                    )
                )

            lines.append("")

        return "\n".join(lines)
