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
class AndroidDeviceTreeApkAndroidMkModule:
    """
    One exact canonical APK rendered as an Android Make prebuilt module.

    ``module_name`` is TreeForge-owned build identity. It is deliberately
    distinct from the observed APK directory/filename identity.

    ``module_path`` and ``module_stem`` preserve the exact canonical
    app/priv-app installation directory and filename.
    """

    representation_id: str
    module_name: str
    source_path: PurePosixPath
    module_path: str
    module_stem: str
    privileged: bool
    compressed: bool

    def __post_init__(self) -> None:
        for field_name, value in (
            ("representation_id", self.representation_id),
            ("module_name", self.module_name),
            ("module_path", self.module_path),
            ("module_stem", self.module_stem),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(self.source_path, PurePosixPath):
            raise TypeError(
                "source_path must be a PurePosixPath"
            )

        if self.source_path.is_absolute():
            raise ValueError(
                "APK Android.mk source_path must be relative"
            )

        if ".." in self.source_path.parts:
            raise ValueError(
                "APK Android.mk source_path must not escape "
                "LOCAL_PATH"
            )

        if self.compressed:
            if not self.module_stem.lower().endswith(".apk.gz"):
                raise ValueError(
                    "compressed APK Android.mk module_stem "
                    "must end with .apk.gz"
                )
        elif not self.module_stem.lower().endswith(".apk"):
            raise ValueError(
                "APK Android.mk module_stem must be an .apk"
            )


class AndroidDeviceTreeApkAndroidMkRenderer:
    """
    Render resolved top-level app/priv-app APK PREBUILT_MODULE realizations.

    Android Make BUILD_PREBUILT permits TreeForge to keep a collision-safe
    generated module identity while independently preserving:

    - exact APK source payload;
    - exact logical partition;
    - exact app/priv-app directory;
    - exact installed APK filename;
    - canonical privileged placement.

    Top-level app/priv-app APKs, canonical RRO APKs, and supported
    top-level compressed .apk.gz factory payloads are rendered here as exact
    opaque prebuilts.  Irregular nested APK layouts retain their existing
    Device Tree realization.
    """

    _TARGET_OUT_BY_PARTITION = {
        "system": "$(TARGET_OUT)",
        "vendor": "$(TARGET_OUT_VENDOR)",
        "product": "$(TARGET_OUT_PRODUCT)",
        "system_ext": "$(TARGET_OUT_SYSTEM_EXT)",
        "odm": "$(TARGET_OUT_ODM)",
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
    ) -> tuple[
        AndroidDeviceTreeApkAndroidMkModule,
        ...,
    ]:
        if not isinstance(identity, AndroidDeviceTreeIdentity):
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
            for projection
            in physical_payload_projections
        }

        if len(physical_by_representation_id) != len(
            physical_payload_projections
        ):
            raise ValueError(
                "physical payload projection identities "
                "must be unique"
            )

        vendor_device_root = (
            identity.proprietary_root.parent
        )

        modules = []

        for realization in realizations:
            representation = realization.build_representation

            if (
                representation.kind
                is not AndroidReconstructionBuildRepresentationKind
                .PACKAGE
            ):
                continue

            if (
                realization.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .PREBUILT_MODULE
            ):
                continue

            if (
                realization.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            ):
                raise ValueError(
                    "APK PREBUILT_MODULE realization must be resolved"
                )

            if realization.module_name is None:
                raise ValueError(
                    "APK PREBUILT_MODULE requires module_name"
                )

            if realization.source_path is None:
                raise ValueError(
                    "APK PREBUILT_MODULE requires source_path"
                )

            projection = (
                physical_by_representation_id.get(
                    realization.representation_id
                )
            )

            if projection is None:
                raise ValueError(
                    "APK PREBUILT_MODULE has no exact physical "
                    "payload projection: "
                    f"{realization.representation_id}"
                )

            if projection.build_representation is not representation:
                raise ValueError(
                    "APK Android.mk projection changed exact "
                    "Reconstruction representation identity"
                )

            if realization.source_path != projection.destination:
                raise ValueError(
                    "APK PREBUILT_MODULE source_path must equal "
                    "its exact physical payload destination"
                )

            installed_partition = (
                projection.installed_partition
            )

            installed_path = PurePosixPath(
                projection.installed_android_path
            )

            if not installed_path.is_absolute():
                raise ValueError(
                    "APK installed Android path must be absolute"
                )

            parts = list(
                installed_path.parts[1:]
            )

            if (
                parts
                and parts[0] == installed_partition
            ):
                parts = parts[1:]

            logical_partition = installed_partition

            if logical_partition not in cls._TARGET_OUT_BY_PARTITION:
                if (
                    parts
                    and parts[0] in cls._TARGET_OUT_BY_PARTITION
                ):
                    logical_partition = parts.pop(0)
                else:
                    raise ValueError(
                        "APK Android.mk renderer cannot derive "
                        "logical partition: "
                        f"{realization.representation_id}"
                    )

            if len(parts) < 2:
                raise ValueError(
                    "APK PREBUILT_MODULE must identify an "
                    "installed APK payload path: "
                    f"{realization.representation_id}"
                )

            install_class = parts[0]
            filename = parts[-1]
            relative_parent_parts = parts[1:-1]

            if not install_class:
                raise ValueError(
                    "APK PREBUILT_MODULE must retain an exact "
                    "install-class path component"
                )

            if (
                install_class in {"app", "priv-app"}
                and not relative_parent_parts
            ):
                raise ValueError(
                    "APK PREBUILT_MODULE must retain an install "
                    "directory below app/priv-app"
                )

            is_compressed_apk = (
                filename.lower().endswith(".apk.gz")
            )

            is_plain_apk = (
                filename.lower().endswith(".apk")
                and not is_compressed_apk
            )

            if not (
                is_plain_apk
                or is_compressed_apk
            ):
                raise ValueError(
                    "APK PREBUILT_MODULE must target .apk "
                    "or .apk.gz"
                )

            is_top_level_app = (
                install_class in {"app", "priv-app"}
                and len(relative_parent_parts) == 1
            )

            is_rro_apk = (
                install_class == "overlay"
                and is_plain_apk
            )

            if (
                is_compressed_apk
                and not is_top_level_app
            ):
                raise ValueError(
                    "compressed APK PREBUILT_MODULE is only "
                    "supported for top-level app/priv-app payloads"
                )

            try:
                local_source_path = (
                    realization.source_path.relative_to(
                        vendor_device_root
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "APK PREBUILT_MODULE source must reside under "
                    "the generated vendor device root: "
                    f"{realization.source_path}"
                ) from error

            target_root = (
                cls._TARGET_OUT_BY_PARTITION[
                    logical_partition
                ]
            )

            module_path = "/".join(
                (
                    target_root,
                    install_class,
                    *relative_parent_parts,
                )
            )

            modules.append(
                AndroidDeviceTreeApkAndroidMkModule(
                    representation_id=(
                        realization.representation_id
                    ),
                    module_name=realization.module_name,
                    source_path=local_source_path,
                    module_path=module_path,
                    module_stem=filename,
                    privileged=(
                        is_top_level_app
                        and install_class == "priv-app"
                    ),
                    compressed=is_compressed_apk,
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

        module_names = tuple(
            module.module_name
            for module in result
        )

        if len(module_names) != len(set(module_names)):
            raise ValueError(
                "APK Android.mk module names must be unique"
            )

        representation_ids = tuple(
            module.representation_id
            for module in result
        )

        if len(representation_ids) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "APK Android.mk representation identities "
                "must be unique"
            )

        return result

    @staticmethod
    def render(
        modules: tuple[
            AndroidDeviceTreeApkAndroidMkModule,
            ...,
        ],
    ) -> str:
        if not isinstance(modules, tuple):
            raise TypeError(
                "modules must be a tuple"
            )

        lines = [
            "LOCAL_PATH := $(call my-dir)",
            "",
        ]

        for index, module in enumerate(modules):
            path_parts = PurePosixPath(
                module.module_path
            ).parts

            is_top_level_app = (
                len(path_parts) >= 2
                and path_parts[-2] in {"app", "priv-app"}
            )

            is_rro_apk = (
                len(path_parts) >= 2
                and path_parts[1] == "overlay"
                and module.module_stem.lower().endswith(".apk")
            )

            is_apk_prebuilt = (
                is_top_level_app
                or is_rro_apk
            )

            lines.extend(
                [
                    "include $(CLEAR_VARS)",
                    f"LOCAL_MODULE := {module.module_name}",
                    (
                        "LOCAL_SRC_FILES := "
                        f"{module.source_path.as_posix()}"
                    ),
                    (
                        "LOCAL_MODULE_CLASS := "
                        f"{'APPS' if is_apk_prebuilt else 'ETC'}"
                    ),
                    (
                        "LOCAL_MODULE_PATH := "
                        f"{module.module_path}"
                    ),
                    (
                        "LOCAL_MODULE_STEM := "
                        f"{module.module_stem}"
                    ),
                ]
            )

            if is_apk_prebuilt:
                #
                # This module is an exact opaque factory APK prebuilt.
                #
                # TreeForge owns a collision-safe build identity while the
                # canonical APK payload, install directory, and installed
                # filename remain unchanged.  The target AOSP build must not
                # dexpreopt that payload as though TreeForge had reconstructed
                # the OEM's source-module/class-loader contract.
                #
                # Likewise, TreeForge has not established source-build
                # LOCAL_USES_LIBRARIES / LOCAL_OPTIONAL_USES_LIBRARIES
                # declarations for these opaque factory prebuilts.  Disable
                # the build-time coherence check together with dexpreopt
                # rather than recording an invented class-loader context.
                #
                lines.extend(
                    [
                        "LOCAL_DEX_PREOPT := false",
                        "LOCAL_ENFORCE_USES_LIBRARIES := false",
                    ]
                )

                if module.compressed:
                    lines.extend(
                        [
                            "LOCAL_COMPRESSED_MODULE := true",
                            (
                                "LOCAL_INSTALLED_MODULE_STEM := "
                                f"{module.module_stem}"
                            ),
                            (
                                "LOCAL_REPLACE_PREBUILT_APK_INSTALLED := "
                                "$(LOCAL_PATH)/"
                                f"{module.source_path.as_posix()}"
                            ),
                            "LOCAL_CERTIFICATE := PRESIGNED",
                        ]
                    )
                else:
                    lines.extend(
                        [
                            "LOCAL_MODULE_SUFFIX := .apk",
                            "LOCAL_CERTIFICATE := PRESIGNED",
                        ]
                    )

            if module.privileged:
                lines.append(
                    "LOCAL_PRIVILEGED_MODULE := true"
                )

            lines.append(
                "include $(BUILD_PREBUILT)"
            )

            if index != len(modules) - 1:
                lines.append("")

        return "\n".join(lines).rstrip() + "\n"
