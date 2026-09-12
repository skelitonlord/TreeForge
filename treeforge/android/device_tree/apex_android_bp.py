from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import PurePosixPath

from treeforge.android.device_tree.apex_payload_projection import (
    AndroidDeviceTreeApexPayloadProjection,
)
from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeApexAndroidBpModule:
    """
    One exact resolved root-runtime APEX rendered as `prebuilt_apex`.
    """

    representation_id: str
    module_name: str
    apex_name: str
    source_path: PurePosixPath
    filename: str
    installed_partition: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("representation_id", self.representation_id),
            ("module_name", self.module_name),
            ("apex_name", self.apex_name),
            ("filename", self.filename),
            ("installed_partition", self.installed_partition),
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
                "APEX Android.bp source_path must be relative"
            )

        if ".." in self.source_path.parts:
            raise ValueError(
                "APEX Android.bp source_path must not escape "
                "the proprietary module directory"
            )

        if not self.filename.endswith(".apex"):
            raise ValueError(
                "prebuilt_apex filename must end in .apex"
            )

        if self.installed_partition not in {
            "system",
            "system_ext",
            "vendor",
        }:
            raise ValueError(
                "prebuilt_apex renderer does not support "
                "canonical installed partition: "
                f"{self.installed_partition!r}"
            )


class AndroidDeviceTreeApexAndroidBpRenderer:
    """
    Project and render resolved APEX_MODULE realizations into Soong
    `prebuilt_apex` declarations.

    The Soong module name is a deterministic TreeForge-owned identity.

    `apex_name` preserves the canonical activated APEX package identity.

    `filename` is the build-consumable `.apex` filename. For a direct APEX
    this is identical to the canonical installed filename. For a factory
    CAPEX it is the `.apex` filename of the exact canonical `original_apex`
    payload; the outer `.capex` path remains preserved independently by the
    payload projection as installed provenance.
    """

    @classmethod
    def project(
        cls,
        *,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
        apex_payload_projections: tuple[
            AndroidDeviceTreeApexPayloadProjection,
            ...,
        ],
        proprietary_root: PurePosixPath,
    ) -> tuple[
        AndroidDeviceTreeApexAndroidBpModule,
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
            apex_payload_projections,
            tuple,
        ):
            raise TypeError(
                "apex_payload_projections must be a tuple"
            )

        if not isinstance(
            proprietary_root,
            PurePosixPath,
        ):
            raise TypeError(
                "proprietary_root must be a PurePosixPath"
            )

        projection_by_representation_id = {
            projection.representation_id:
            projection
            for projection
            in apex_payload_projections
        }

        if len(
            projection_by_representation_id
        ) != len(
            apex_payload_projections
        ):
            raise ValueError(
                "APEX payload projection identities must be unique"
            )

        resolved_apex_realizations = tuple(
            realization
            for realization
            in realizations
            if (
                realization.kind
                is AndroidDeviceTreeBuildRealizationKind
                .APEX_MODULE
                and realization.status
                is AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            )
        )

        modules = []

        for realization in resolved_apex_realizations:
            projection = (
                projection_by_representation_id.get(
                    realization.representation_id
                )
            )

            if projection is None:
                raise ValueError(
                    "resolved APEX realization has no exact "
                    "root-runtime payload projection: "
                    f"{realization.representation_id}"
                )

            if (
                projection.build_representation
                is not realization.build_representation
            ):
                raise ValueError(
                    "APEX Android.bp projection changed exact "
                    "Reconstruction representation identity: "
                    f"{realization.representation_id}"
                )

            if realization.source_path is None:
                raise ValueError(
                    "resolved APEX realization requires source_path"
                )

            if (
                realization.source_path
                != projection.destination
            ):
                raise ValueError(
                    "resolved APEX source_path must equal exact "
                    "payload projection destination: "
                    f"{realization.representation_id}"
                )

            if realization.module_name is None:
                raise ValueError(
                    "resolved APEX realization requires module_name"
                )

            try:
                relative_source_path = (
                    realization.source_path.relative_to(
                        proprietary_root
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "resolved APEX payload must live beneath the "
                    "proprietary Android.bp root: "
                    f"{realization.source_path}"
                ) from error

            installed_path = PurePosixPath(
                projection.installed_android_path
            )

            if not installed_path.is_absolute():
                raise ValueError(
                    "canonical APEX installed path must be absolute"
                )

            if installed_path.parent.name != "apex":
                raise ValueError(
                    "prebuilt APEX canonical destination must be "
                    "inside an apex directory: "
                    f"{projection.installed_android_path!r}"
                )

            #
            # The canonical installed path may be .capex, but the Soong
            # prebuilt source/output here is the exact build-consumable
            # uncompressed APEX payload selected by Device Tree.
            #
            filename = (
                projection.destination.name
            )

            if not filename.endswith(".apex"):
                raise ValueError(
                    "resolved prebuilt APEX build filename must "
                    "end in .apex: "
                    f"{filename!r}"
                )

            apex_name = projection.requirement.apex_name

            modules.append(
                AndroidDeviceTreeApexAndroidBpModule(
                    representation_id=(
                        realization.representation_id
                    ),
                    module_name=realization.module_name,
                    apex_name=apex_name,
                    source_path=relative_source_path,
                    filename=filename,
                    installed_partition=(
                        projection.installed_partition
                    ),
                )
            )

        result = tuple(
            sorted(
                modules,
                key=lambda module: (
                    module.module_name,
                    module.representation_id,
                ),
            )
        )

        expected_ids = {
            realization.representation_id
            for realization
            in resolved_apex_realizations
        }

        actual_ids = {
            module.representation_id
            for module
            in result
        }

        if actual_ids != expected_ids:
            raise ValueError(
                "APEX Android.bp projection coverage mismatch"
            )

        module_names = tuple(
            module.module_name
            for module
            in result
        )

        if len(module_names) != len(
            set(module_names)
        ):
            raise ValueError(
                "APEX Android.bp module names must be unique"
            )

        return result

    @staticmethod
    def render(
        modules: tuple[
            AndroidDeviceTreeApexAndroidBpModule,
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

        if not modules:
            return (
                "// No resolved TreeForge prebuilt APEX modules.\n"
            )

        lines = [
            "//",
            "// Resolved root-runtime APEX prebuilts.",
            "//",
            "",
        ]

        for module in modules:
            lines.extend(
                [
                    "prebuilt_apex {",
                    (
                        "    name: "
                        f"{json.dumps(module.module_name)},"
                    ),
                    (
                        "    src: "
                        f"{json.dumps(module.source_path.as_posix())},"
                    ),
                    (
                        "    filename: "
                        f"{json.dumps(module.filename)},"
                    ),
                    (
                        "    apex_name: "
                        f"{json.dumps(module.apex_name)},"
                    ),
                ]
            )

            if (
                module.installed_partition
                == "system_ext"
            ):
                lines.append(
                    "    system_ext_specific: true,"
                )

            elif (
                module.installed_partition
                == "vendor"
            ):
                lines.append(
                    "    soc_specific: true,"
                )

            lines.extend(
                [
                    "}",
                    "",
                ]
            )

        return "\n".join(lines)
