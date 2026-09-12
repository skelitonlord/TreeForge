from __future__ import annotations

from dataclasses import replace

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkOverlayResolution,
    AndroidUniverseApkOverlayResolutionStatus,
    AndroidUniverseApkPackageRequirement,
)


class AndroidReconstructionPackageBuildProjector:
    """
    Project canonical installed APK/RRO requirements into syntax-neutral
    Android package build participation.

    Universe already establishes:
    - exact installed APK artifact identity;
    - package identity;
    - installed partition/path;
    - whether the package is an RRO.

    Reconstruction therefore knows that the installed package must be
    represented by the eventual build even when it cannot generically
    establish the concrete source module, prebuilt declaration, copy rule,
    or other build mechanism.

    Preserved artifacts are excluded here because the preserved-artifact
    classifier already owns their physical build representation. Creating a
    second PACKAGE representation would duplicate one canonical artifact.

    This projector does not:
    - inspect an AOSP/source checkout;
    - infer source module names;
    - invoke Knowledge;
    - choose Android.bp/Android.mk syntax;
    - choose source-tree ownership or placement;
    - invent product-package declarations.
    """

    @staticmethod
    def apply_overlay_dependencies(
        *,
        packages: tuple[
            AndroidUniverseApkPackageRequirement,
            ...,
        ],
        overlay_resolutions: tuple[
            AndroidUniverseApkOverlayResolution,
            ...,
        ],
        build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        """
        Attach canonical resolved RRO target-package relationships to the
        syntax-neutral build population.

        Both preserved and requirement-backed package representations are
        supported. Ambiguous, absent, or unresolved overlay targets never
        produce invented build dependencies.
        """

        if (
            not isinstance(
                packages,
                tuple,
            )
            or not all(
                isinstance(
                    package,
                    AndroidUniverseApkPackageRequirement,
                )
                for package in packages
            )
        ):
            raise TypeError(
                "packages must contain only "
                "AndroidUniverseApkPackageRequirement values"
            )

        if (
            not isinstance(
                overlay_resolutions,
                tuple,
            )
            or not all(
                isinstance(
                    resolution,
                    AndroidUniverseApkOverlayResolution,
                )
                for resolution in overlay_resolutions
            )
        ):
            raise TypeError(
                "overlay_resolutions must contain only "
                "AndroidUniverseApkOverlayResolution values"
            )

        if (
            not isinstance(
                build_representations,
                tuple,
            )
            or not all(
                isinstance(
                    representation,
                    AndroidReconstructionBuildRepresentation,
                )
                for representation in build_representations
            )
        ):
            raise TypeError(
                "build_representations must contain only "
                "AndroidReconstructionBuildRepresentation values"
            )

        package_representation_by_artifact_id = {}

        package_artifact_ids = {
            package.artifact.requirement_id
            for package in packages
        }

        for representation in build_representations:
            artifact_id = (
                representation.preserved_artifact_id
                or representation.canonical_requirement_id
            )

            if (
                artifact_id is None
                or artifact_id not in package_artifact_ids
            ):
                continue

            if (
                representation.kind
                is not AndroidReconstructionBuildRepresentationKind
                .PACKAGE
            ):
                raise ValueError(
                    "canonical APK artifact is represented by a "
                    "non-PACKAGE build role: "
                    f"{artifact_id}"
                )

            if (
                artifact_id
                in package_representation_by_artifact_id
            ):
                raise ValueError(
                    "canonical APK artifact maps to multiple "
                    "build representations: "
                    f"{artifact_id}"
                )

            package_representation_by_artifact_id[
                artifact_id
            ] = representation

        expected_artifact_ids = {
            package.artifact.requirement_id
            for package in packages
        }

        if (
            set(
                package_representation_by_artifact_id
            )
            != expected_artifact_ids
        ):
            missing = tuple(
                sorted(
                    expected_artifact_ids
                    - set(
                        package_representation_by_artifact_id
                    )
                )
            )

            raise ValueError(
                "APK build population must represent every canonical "
                "installed package before overlay dependency projection: "
                f"{missing}"
            )

        dependency_ids_by_representation_id = {
            representation.representation_id: set(
                representation.dependency_ids
            )
            for representation in build_representations
        }

        for resolution in overlay_resolutions:
            if (
                resolution.status
                is not AndroidUniverseApkOverlayResolutionStatus
                .RESOLVED
            ):
                continue

            target = resolution.targets[0]

            overlay_representation = (
                package_representation_by_artifact_id[
                    resolution.overlay.artifact.requirement_id
                ]
            )

            target_representation = (
                package_representation_by_artifact_id[
                    target.artifact.requirement_id
                ]
            )

            if (
                overlay_representation.representation_id
                == target_representation.representation_id
            ):
                raise ValueError(
                    "resolved APK overlay must not depend on itself"
                )

            dependency_ids_by_representation_id[
                overlay_representation.representation_id
            ].add(
                target_representation.representation_id
            )

        result = tuple(
            sorted(
                (
                    replace(
                        representation,
                        dependency_ids=tuple(
                            sorted(
                                dependency_ids_by_representation_id[
                                    representation.representation_id
                                ]
                            )
                        ),
                    )
                    for representation
                    in build_representations
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        return result

    @staticmethod
    def project(
        packages: tuple[
            AndroidUniverseApkPackageRequirement,
            ...,
        ],
        *,
        existing_build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ] = (),
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        if (
            not isinstance(
                packages,
                tuple,
            )
            or not all(
                isinstance(
                    package,
                    AndroidUniverseApkPackageRequirement,
                )
                for package in packages
            )
        ):
            raise TypeError(
                "packages must contain only "
                "AndroidUniverseApkPackageRequirement values"
            )

        if (
            not isinstance(
                existing_build_representations,
                tuple,
            )
            or not all(
                isinstance(
                    representation,
                    AndroidReconstructionBuildRepresentation,
                )
                for representation
                in existing_build_representations
            )
        ):
            raise TypeError(
                "existing_build_representations must contain only "
                "AndroidReconstructionBuildRepresentation values"
            )

        represented_artifact_ids = {
            representation.preserved_artifact_id
            for representation
            in existing_build_representations
            if representation.preserved_artifact_id is not None
        }

        projected = []

        for package in packages:
            artifact = package.artifact

            if (
                artifact.requirement_id
                in represented_artifact_ids
            ):
                continue

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:package:"
                        f"{package.requirement_id}"
                    ),
                    kind=(
                        AndroidReconstructionBuildRepresentationKind
                        .PACKAGE
                    ),
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=(
                        package.requirement_id
                    ),
                    canonical_requirement_id=(
                        artifact.requirement_id
                    ),
                    installed_partition=(
                        artifact.partition_name
                    ),
                    installed_android_path=(
                        artifact.android_path
                    ),
                    module_identity=None,
                    dependency_ids=(),
                    reason=(
                        "Canonical Universe APK/package evidence proves "
                        "installed package build participation and exact "
                        "installed artifact identity, but generic "
                        "Reconstruction does not establish the concrete "
                        "source module or build mechanism."
                    ),
                )
            )

        result = tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        representation_ids = tuple(
            representation.representation_id
            for representation in result
        )

        if len(
            representation_ids
        ) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "APK package build representation identities "
                "must be unique"
            )

        requirement_ids = tuple(
            representation.canonical_requirement_id
            for representation in result
        )

        if len(
            requirement_ids
        ) != len(
            set(requirement_ids)
        ):
            raise ValueError(
                "one canonical APK artifact may have at most one "
                "requirement-backed package build representation"
            )

        expected_artifact_ids = {
            package.artifact.requirement_id
            for package in packages
            if (
                package.artifact.requirement_id
                not in represented_artifact_ids
            )
        }

        if set(
            requirement_ids
        ) != expected_artifact_ids:
            raise ValueError(
                "APK package projection must exactly cover every "
                "non-preserved canonical installed APK artifact"
            )

        return result
