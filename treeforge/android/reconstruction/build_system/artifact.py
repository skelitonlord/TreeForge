from __future__ import annotations

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactKind,
    AndroidUniverseArtifactRequirement,
)


_KIND_TO_BUILD_ROLE = {
    AndroidUniverseArtifactKind.HAL_SHARED_LIBRARY: (
        AndroidReconstructionBuildRepresentationKind.NATIVE_LIBRARY
    ),
    AndroidUniverseArtifactKind.SHARED_LIBRARY: (
        AndroidReconstructionBuildRepresentationKind.NATIVE_LIBRARY
    ),
    AndroidUniverseArtifactKind.HARDWARE_SERVICE: (
        AndroidReconstructionBuildRepresentationKind.EXECUTABLE
    ),
    AndroidUniverseArtifactKind.EXECUTABLE: (
        AndroidReconstructionBuildRepresentationKind.EXECUTABLE
    ),
    AndroidUniverseArtifactKind.KERNEL_MODULE: (
        AndroidReconstructionBuildRepresentationKind.KERNEL_MODULE
    ),
    AndroidUniverseArtifactKind.APEX: (
        AndroidReconstructionBuildRepresentationKind.APEX
    ),
    AndroidUniverseArtifactKind.APK: (
        AndroidReconstructionBuildRepresentationKind.PACKAGE
    ),
    AndroidUniverseArtifactKind.RUNTIME_RESOURCE_OVERLAY: (
        AndroidReconstructionBuildRepresentationKind.PACKAGE
    ),
    AndroidUniverseArtifactKind.FRAMEWORK_JAR: (
        AndroidReconstructionBuildRepresentationKind.JAVA_LIBRARY
    ),
    AndroidUniverseArtifactKind.JAVA_LIBRARY: (
        AndroidReconstructionBuildRepresentationKind.JAVA_LIBRARY
    ),
}


class AndroidReconstructionArtifactBuildClassifier:
    """
    Classify one preserved canonical filesystem artifact into a
    syntax-neutral build-participation representation.

    Universe remains authoritative for artifact identity, semantic kinds,
    installed partition/path, and preservation disposition.

    This classifier does not infer source-tree placement, module names,
    Make/Soong syntax, dependency wiring, or a copy/prebuilt mechanism.

    Stronger intrinsic build roles are selected only when every artifact kind
    that provides a specialized build role agrees on the same role.

    Otherwise the exact artifact remains a generic PRESERVED_ARTIFACT with
    PARTIAL status. This preserves known build participation without inventing
    a concrete build mechanism.
    """

    @staticmethod
    def classify(
        work_item: AndroidReconstructionWorkItem,
    ) -> AndroidReconstructionBuildRepresentation:
        if not isinstance(
            work_item,
            AndroidReconstructionWorkItem,
        ):
            raise TypeError(
                "work_item must be an AndroidReconstructionWorkItem"
            )

        if (
            work_item.work_kind
            is not AndroidReconstructionWorkKind.PRESERVE
        ):
            raise ValueError(
                "artifact build classification requires PRESERVE work"
            )

        if work_item.requirement_kind != "artifact":
            raise ValueError(
                "artifact build classifier requires artifact work"
            )

        requirement = (
            work_item.obligation.requirement
        )

        if not isinstance(
            requirement,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact build work must preserve an "
                "AndroidUniverseArtifactRequirement"
            )

        if (
            requirement.disposition
            is not AndroidUniverseArtifactDisposition.PRESERVE
        ):
            raise ValueError(
                "artifact build classification requires canonical "
                "Universe PRESERVE disposition"
            )

        if (
            work_item.source_identity
            != requirement.requirement_id
        ):
            raise ValueError(
                "artifact work source_identity must preserve the "
                "canonical Universe requirement identity"
            )

        if (
            work_item.preserved_artifact_id
            != requirement.requirement_id
        ):
            raise ValueError(
                "artifact preserved_artifact_id must preserve the "
                "canonical Universe requirement identity"
            )

        specialized_roles = tuple(
            sorted(
                {
                    role
                    for kind in requirement.kinds
                    if (
                        role := _KIND_TO_BUILD_ROLE.get(
                            kind
                        )
                    )
                    is not None
                },
                key=lambda role: role.value,
            )
        )

        if len(specialized_roles) == 1:
            kind = specialized_roles[0]
            status = (
                AndroidReconstructionBuildRepresentationStatus.RESOLVED
            )
            reason = None

        elif not specialized_roles:
            kind = (
                AndroidReconstructionBuildRepresentationKind
                .PRESERVED_ARTIFACT
            )
            status = (
                AndroidReconstructionBuildRepresentationStatus.PARTIAL
            )
            reason = (
                "Universe requires exact artifact preservation and "
                "provides canonical installed partition/path identity, "
                "but does not establish a more specific build role or "
                "copy/prebuilt mechanism."
            )

        else:
            kind = (
                AndroidReconstructionBuildRepresentationKind
                .PRESERVED_ARTIFACT
            )
            status = (
                AndroidReconstructionBuildRepresentationStatus.PARTIAL
            )
            role_values = ", ".join(
                role.value
                for role in specialized_roles
            )
            reason = (
                "Canonical artifact kinds imply multiple specialized "
                "build roles; Build-System Reconstruction preserves the "
                "artifact without inventing precedence. Roles: "
                f"{role_values}"
            )

        return AndroidReconstructionBuildRepresentation(
            representation_id=(
                "build:artifact:"
                f"{requirement.requirement_id}"
            ),
            kind=kind,
            status=status,
            source_identity=requirement.requirement_id,
            preserved_artifact_id=(
                work_item.preserved_artifact_id
            ),
            installed_partition=(
                requirement.partition_name
            ),
            installed_android_path=(
                requirement.android_path
            ),
            module_identity=None,
            dependency_ids=(),
            reason=reason,
        )
