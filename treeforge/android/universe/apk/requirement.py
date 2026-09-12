from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.apk import (
    AndroidApkParsingResult,
    ParsedAndroidApk,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApkPackageRequirement:
    """
    Canonical Universe identity for one installed APK package.

    The exact ParsedAndroidApk and exact canonical filesystem artifact
    requirement are retained by identity. Universe does not infer source-tree
    ownership, build-module ownership, preservation, or reconstruction
    placement from package identity.
    """

    source: ParsedAndroidApk
    artifact: AndroidUniverseArtifactRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidApk,
        ):
            raise TypeError(
                "source must be a ParsedAndroidApk"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        filesystem_source = (
            self.source.source.filesystem_source
        )

        if (
            self.artifact.inventory_entry.artifact
            is not filesystem_source.artifact
        ):
            raise ValueError(
                "APK artifact must preserve the exact canonical "
                "Parsing filesystem artifact identity"
            )

        metadata_path = (
            self.artifact.inventory_entry
            .filesystem_path_for_materialized_path(
                self.source.source.apk_host_path
            )
        )

        if (
            self.artifact.metadata_entry.path
            != metadata_path
        ):
            raise ValueError(
                "APK artifact must preserve the exact canonical "
                "filesystem metadata identity"
            )

    @property
    def package_name(
        self,
    ) -> str:
        value = self.source.package_name.literal

        if not isinstance(
            value,
            str,
        ) or not value:
            raise ValueError(
                "canonical APK package name must be a "
                "non-empty literal string"
            )

        return value

    @property
    def version_code(
        self,
    ) -> str | int | bool | None:
        if self.source.version_code is None:
            return None

        return self.source.version_code.literal

    @property
    def version_name(
        self,
    ) -> str | int | bool | None:
        if self.source.version_name is None:
            return None

        return self.source.version_name.literal

    @property
    def is_overlay(
        self,
    ) -> bool:
        return self.source.overlay is not None

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "apk-package:"
            f"{self.source.source.source_name}:"
            f"{self.source.source.apk_android_path.as_posix()}"
        )


class AndroidUniverseApkOverlayResolutionStatus(
    StrEnum,
):
    RESOLVED = "resolved"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApkOverlayResolution:
    """
    Resolve one parsed RRO package against canonical APK package identity.

    Package-name matching is semantic reconciliation over already parsed
    manifest identity. It does not imply build/source ownership.
    """

    overlay: AndroidUniverseApkPackageRequirement

    status: AndroidUniverseApkOverlayResolutionStatus

    targets: tuple[
        AndroidUniverseApkPackageRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.overlay,
            AndroidUniverseApkPackageRequirement,
        ):
            raise TypeError(
                "overlay must be an "
                "AndroidUniverseApkPackageRequirement"
            )

        if not self.overlay.is_overlay:
            raise ValueError(
                "overlay resolution must reference an RRO package"
            )

        if not isinstance(
            self.status,
            AndroidUniverseApkOverlayResolutionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseApkOverlayResolutionStatus"
            )

        if not isinstance(
            self.targets,
            tuple,
        ):
            raise TypeError(
                "targets must be a tuple"
            )

        if not all(
            isinstance(
                target,
                AndroidUniverseApkPackageRequirement,
            )
            for target in self.targets
        ):
            raise TypeError(
                "targets must contain only "
                "AndroidUniverseApkPackageRequirement values"
            )

        expected_count = {
            AndroidUniverseApkOverlayResolutionStatus.RESOLVED: 1,
            AndroidUniverseApkOverlayResolutionStatus.ABSENT: 0,
            AndroidUniverseApkOverlayResolutionStatus.UNRESOLVED: 0,
        }

        if self.status in expected_count:
            if len(
                self.targets
            ) != expected_count[
                self.status
            ]:
                raise ValueError(
                    "overlay resolution target population "
                    "does not match status"
                )

        if (
            self.status
            is AndroidUniverseApkOverlayResolutionStatus.AMBIGUOUS
            and len(
                self.targets
            ) < 2
        ):
            raise ValueError(
                "ambiguous overlay resolution requires "
                "multiple targets"
            )

    @property
    def target_package_name(
        self,
    ) -> str | None:
        parsed_overlay = (
            self.overlay.source.overlay
        )

        if (
            parsed_overlay is None
            or parsed_overlay.target_package is None
        ):
            return None

        value = (
            parsed_overlay.target_package.literal
        )

        return (
            value
            if isinstance(
                value,
                str,
            )
            and value
            else None
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApkRequirement:
    """
    Canonical Universe interpretation of APK package identity.

    Every parsed APK must map to one exact canonical artifact requirement.
    Overlay target-package resolution is retained separately so unresolved
    or ambiguous package relationships remain explicit.
    """

    source: AndroidApkParsingResult

    packages: tuple[
        AndroidUniverseApkPackageRequirement,
        ...,
    ] = ()

    overlay_resolutions: tuple[
        AndroidUniverseApkOverlayResolution,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidApkParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidApkParsingResult"
            )

        if not isinstance(
            self.packages,
            tuple,
        ):
            raise TypeError(
                "packages must be a tuple"
            )

        if not all(
            isinstance(
                package,
                AndroidUniverseApkPackageRequirement,
            )
            for package in self.packages
        ):
            raise TypeError(
                "packages must contain only "
                "AndroidUniverseApkPackageRequirement values"
            )

        if len(
            self.packages
        ) != len(
            self.source.packages
        ):
            raise ValueError(
                "Universe APK package population must match Parsing"
            )

        for parsed, requirement in zip(
            self.source.packages,
            self.packages,
            strict=True,
        ):
            if requirement.source is not parsed:
                raise ValueError(
                    "APK requirement must preserve exact "
                    "canonical Parsing package identity"
                )

        if not isinstance(
            self.overlay_resolutions,
            tuple,
        ):
            raise TypeError(
                "overlay_resolutions must be a tuple"
            )

        expected_overlays = tuple(
            package
            for package in self.packages
            if package.is_overlay
        )

        if len(
            self.overlay_resolutions
        ) != len(
            expected_overlays
        ):
            raise ValueError(
                "overlay resolution population must cover "
                "every parsed RRO package"
            )

        for package, resolution in zip(
            expected_overlays,
            self.overlay_resolutions,
            strict=True,
        ):
            if resolution.overlay is not package:
                raise ValueError(
                    "overlay resolution must preserve exact "
                    "APK requirement identity and ordering"
                )

    @property
    def overlay_count(
        self,
    ) -> int:
        return len(
            self.overlay_resolutions
        )
