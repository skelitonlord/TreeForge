from __future__ import annotations

from collections import defaultdict

from treeforge.android.parsing.apk import (
    AndroidApkParsingResult,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkOverlayResolution,
    AndroidUniverseApkOverlayResolutionStatus,
    AndroidUniverseApkPackageRequirement,
    AndroidUniverseApkRequirement,
)


class AndroidUniverseApkInterpreter:
    """
    Promote canonical APK Parsing into installed-package Universe semantics.

    Exact physical reconciliation follows the same canonical mechanism used
    by Artifact Parsing evidence: parser materialized host paths are converted
    through FilesystemMetadataInventoryEntry to their exact metadata entries.

    No source-tree ownership or reconstruction disposition is inferred here.
    """

    def interpret(
        self,
        parsing: AndroidApkParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseApkRequirement:
        if not isinstance(
            parsing,
            AndroidApkParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidApkParsingResult"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        artifacts_by_identity = {
            requirement.identity_key: requirement
            for requirement
            in artifact_requirements.requirements
        }

        package_requirements = []

        for parsed in parsing.packages:
            filesystem_source = (
                parsed.source.filesystem_source
            )

            try:
                inventory_entry = (
                    artifact_requirements
                    .source_inventory
                    .entry_for_artifact(
                        filesystem_source.artifact
                    )
                )
            except KeyError as error:
                raise ValueError(
                    "APK Parsing filesystem source does not map "
                    "to canonical Filesystem Metadata identity: "
                    f"{parsed.source.source_name}:"
                    f"{parsed.source.apk_android_path.as_posix()}"
                ) from error

            try:
                metadata_path = (
                    inventory_entry
                    .filesystem_path_for_materialized_path(
                        parsed.source.apk_host_path
                    )
                )
            except ValueError as error:
                raise ValueError(
                    "APK host path does not belong to its "
                    "canonical filesystem artifact: "
                    f"{parsed.source.source_name}:"
                    f"{parsed.source.apk_android_path.as_posix()}"
                ) from error

            metadata_entry = (
                inventory_entry
                .result
                .metadata
                .get(
                    metadata_path
                )
            )

            if metadata_entry is None:
                raise ValueError(
                    "APK Parsing source does not map to a "
                    "canonical filesystem metadata entry: "
                    f"{parsed.source.source_name}:"
                    f"{parsed.source.apk_android_path.as_posix()} "
                    f"-> {metadata_path}"
                )

            identity = (
                id(
                    filesystem_source.artifact
                ),
                id(
                    metadata_entry
                ),
            )

            artifact = (
                artifacts_by_identity.get(
                    identity
                )
            )

            if artifact is None:
                raise ValueError(
                    "APK Parsing source has no exact canonical "
                    "artifact requirement: "
                    f"{parsed.source.source_name}:"
                    f"{parsed.source.apk_android_path.as_posix()}"
                )

            package_requirements.append(
                AndroidUniverseApkPackageRequirement(
                    source=parsed,
                    artifact=artifact,
                )
            )

        packages = tuple(
            package_requirements
        )

        packages_by_name = defaultdict(
            list
        )

        for package in packages:
            packages_by_name[
                package.package_name
            ].append(
                package
            )

        overlay_resolutions = tuple(
            self._resolve_overlay(
                overlay=package,
                packages_by_name=packages_by_name,
            )
            for package in packages
            if package.is_overlay
        )

        return AndroidUniverseApkRequirement(
            source=parsing,
            packages=packages,
            overlay_resolutions=(
                overlay_resolutions
            ),
        )

    @staticmethod
    def _resolve_overlay(
        *,
        overlay: AndroidUniverseApkPackageRequirement,
        packages_by_name,
    ) -> AndroidUniverseApkOverlayResolution:
        parsed_overlay = (
            overlay.source.overlay
        )

        if (
            parsed_overlay is None
            or parsed_overlay.target_package is None
        ):
            return AndroidUniverseApkOverlayResolution(
                overlay=overlay,
                status=(
                    AndroidUniverseApkOverlayResolutionStatus
                    .UNRESOLVED
                ),
            )

        target_name = (
            parsed_overlay.target_package.literal
        )

        if (
            not isinstance(
                target_name,
                str,
            )
            or not target_name
        ):
            return AndroidUniverseApkOverlayResolution(
                overlay=overlay,
                status=(
                    AndroidUniverseApkOverlayResolutionStatus
                    .UNRESOLVED
                ),
            )

        matches = tuple(
            packages_by_name.get(
                target_name,
                ()
            )
        )

        if not matches:
            status = (
                AndroidUniverseApkOverlayResolutionStatus
                .ABSENT
            )

        elif len(
            matches
        ) == 1:
            status = (
                AndroidUniverseApkOverlayResolutionStatus
                .RESOLVED
            )

        else:
            status = (
                AndroidUniverseApkOverlayResolutionStatus
                .AMBIGUOUS
            )

        return AndroidUniverseApkOverlayResolution(
            overlay=overlay,
            status=status,
            targets=matches,
        )
