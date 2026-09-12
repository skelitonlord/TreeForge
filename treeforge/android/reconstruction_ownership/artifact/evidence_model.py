from __future__ import annotations

from treeforge.android.universe.elf.artifact_association import (
    AndroidUniverseElfArtifactAssociation,
    AndroidUniverseElfArtifactAssociationKind,
)
from treeforge.android.universe.kernel_module.elf_association import (
    AndroidUniverseKernelModuleElfAssociation,
)


from dataclasses import dataclass

from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.runtime_linking.linker.elf_dependency_resolution import (
    AndroidRuntimeLinkerElfDependencyResolution,
    AndroidRuntimeLinkerElfDependencyTraversal,
)
from treeforge.android.runtime_linking.linker.elf_runtime_candidate import (
    AndroidRuntimeLinkerElfRuntimeCandidate,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkPackageRequirement,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathInstalledJarResolution,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseJavaArchiveAssociation,
)
from treeforge.android.universe.shell_script import (
    AndroidUniverseShellClasspathResolution,
    AndroidUniverseShellScriptAssociation,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleFileRequirement,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseInitExecutableArtifactRelationship,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidReconstructionArtifactEvidence:
    """
    Generic lineage evidence accumulated around one exact canonical artifact.

    This model deliberately contains evidence only.

    It does not:
    - decide source-tree ownership;
    - decide source availability;
    - classify an artifact as proprietary;
    - require exact payload preservation;
    - create Reconstruction Planning work.
    """

    artifact: AndroidUniverseArtifactRequirement

    elf_requirements: tuple[
        AndroidUniverseElfRequirement,
        ...,
    ] = ()

    elf_artifact_associations: tuple[
        AndroidUniverseElfArtifactAssociation,
        ...,
    ] = ()

    kernel_module_requirements: tuple[
        AndroidUniverseKernelModuleFileRequirement,
        ...,
    ] = ()

    kernel_module_elf_associations: tuple[
        AndroidUniverseKernelModuleElfAssociation,
        ...,
    ] = ()

    init_executable_relationships: tuple[
        AndroidUniverseInitExecutableArtifactRelationship,
        ...,
    ] = ()

    classpath_installed_jar_resolutions: tuple[
        AndroidUniverseClasspathInstalledJarResolution,
        ...,
    ] = ()

    java_archive_associations: tuple[
        AndroidUniverseJavaArchiveAssociation,
        ...,
    ] = ()

    shell_script_associations: tuple[
        AndroidUniverseShellScriptAssociation,
        ...,
    ] = ()

    shell_classpath_references: tuple[
        AndroidUniverseShellClasspathResolution,
        ...,
    ] = ()

    apk_package_requirements: tuple[
        AndroidUniverseApkPackageRequirement,
        ...,
    ] = ()

    apex_memberships: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ] = ()

    runtime_linking_candidates: tuple[
        AndroidRuntimeLinkerElfRuntimeCandidate,
        ...,
    ] = ()

    runtime_linking_root_traversals: tuple[
        AndroidRuntimeLinkerElfDependencyTraversal,
        ...,
    ] = ()

    runtime_linking_parent_dependencies: tuple[
        AndroidRuntimeLinkerElfDependencyResolution,
        ...,
    ] = ()

    runtime_linking_provider_dependencies: tuple[
        AndroidRuntimeLinkerElfDependencyResolution,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        if not isinstance(
            self.elf_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            )
            for requirement
            in self.elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement values"
            )

        if not isinstance(
            self.kernel_module_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for requirement
            in self.kernel_module_requirements
        ):
            raise TypeError(
                "kernel_module_requirements must contain only "
                "AndroidUniverseKernelModuleFileRequirement values"
            )

        if not isinstance(
            self.elf_artifact_associations,
            tuple,
        ) or not all(
            isinstance(
                association,
                AndroidUniverseElfArtifactAssociation,
            )
            for association
            in self.elf_artifact_associations
        ):
            raise TypeError(
                "elf_artifact_associations must contain only "
                "AndroidUniverseElfArtifactAssociation values"
            )

        elf_requirement_object_ids_for_association = {
            id(requirement)
            for requirement
            in self.elf_requirements
        }

        association_elf_requirement_ids = {
            id(
                association.elf_requirement
            )
            for association
            in self.elf_artifact_associations
        }

        if (
            association_elf_requirement_ids
            != elf_requirement_object_ids_for_association
            or len(
                self.elf_artifact_associations
            )
            != len(
                self.elf_requirements
            )
        ):
            raise ValueError(
                "artifact ELF evidence must preserve exactly one "
                "canonical Universe ELF/artifact association per ELF"
            )

        for association in (
            self.elf_artifact_associations
        ):
            if (
                association.kind
                is not AndroidUniverseElfArtifactAssociationKind
                .FILESYSTEM_ARTIFACT
            ):
                raise ValueError(
                    "filesystem artifact evidence must not contain "
                    "an extraction-backed ELF association"
                )

            if (
                association.artifact_requirement
                is not self.artifact
            ):
                raise ValueError(
                    "ELF/artifact association must preserve the exact "
                    "canonical artifact requirement object"
                )

        if not isinstance(
            self.kernel_module_elf_associations,
            tuple,
        ) or not all(
            isinstance(
                association,
                AndroidUniverseKernelModuleElfAssociation,
            )
            for association
            in self.kernel_module_elf_associations
        ):
            raise TypeError(
                "kernel_module_elf_associations must contain only "
                "AndroidUniverseKernelModuleElfAssociation values"
            )

        module_requirement_object_ids = {
            id(requirement)
            for requirement
            in self.kernel_module_requirements
        }

        association_module_requirement_ids = {
            id(
                association.module_requirement
            )
            for association
            in self.kernel_module_elf_associations
        }

        if (
            association_module_requirement_ids
            != module_requirement_object_ids
            or len(
                self.kernel_module_elf_associations
            )
            != len(
                self.kernel_module_requirements
            )
        ):
            raise ValueError(
                "kernel-module evidence must preserve exactly one "
                "canonical module/ELF association per module"
            )

        for association in (
            self.kernel_module_elf_associations
        ):
            if (
                id(
                    association.elf_requirement
                )
                not in (
                    elf_requirement_object_ids_for_association
                )
            ):
                raise ValueError(
                    "kernel-module/ELF association must reference an "
                    "exact ELF requirement attached to this artifact"
                )

        if not isinstance(
            self.init_executable_relationships,
            tuple,
        ) or not all(
            isinstance(
                relationship,
                AndroidUniverseInitExecutableArtifactRelationship,
            )
            for relationship
            in self.init_executable_relationships
        ):
            raise TypeError(
                "init_executable_relationships must contain only "
                "AndroidUniverseInitExecutableArtifactRelationship values"
            )

        for relationship in self.init_executable_relationships:
            if not any(
                matched is self.artifact
                for matched
                in relationship.matched_artifacts
            ):
                raise ValueError(
                    "INIT executable evidence must retain the exact "
                    "canonical artifact requirement object"
                )

        if not isinstance(
            self.classpath_installed_jar_resolutions,
            tuple,
        ) or not all(
            isinstance(
                resolution,
                AndroidUniverseClasspathInstalledJarResolution,
            )
            for resolution
            in self.classpath_installed_jar_resolutions
        ):
            raise TypeError(
                "classpath_installed_jar_resolutions must contain only "
                "AndroidUniverseClasspathInstalledJarResolution values"
            )

        for resolution in (
            self.classpath_installed_jar_resolutions
        ):
            if not any(
                matched is self.artifact
                for matched
                in resolution.matched_artifacts
            ):
                raise ValueError(
                    "Classpath evidence must retain the exact canonical "
                    "artifact requirement object"
                )

        if (
            not isinstance(
                self.java_archive_associations,
                tuple,
            )
            or not all(
                isinstance(
                    association,
                    AndroidUniverseJavaArchiveAssociation,
                )
                for association
                in self.java_archive_associations
            )
        ):
            raise TypeError(
                "java_archive_associations contains invalid values"
            )

        for association in self.java_archive_associations:
            if association.artifact is not self.artifact:
                raise ValueError(
                    "Java-archive evidence must preserve the exact "
                    "canonical artifact requirement object"
                )

        if (
            not isinstance(
                self.shell_script_associations,
                tuple,
            )
            or not all(
                isinstance(
                    association,
                    AndroidUniverseShellScriptAssociation,
                )
                for association
                in self.shell_script_associations
            )
        ):
            raise TypeError(
                "shell_script_associations contains invalid values"
            )

        for association in self.shell_script_associations:
            if association.artifact is not self.artifact:
                raise ValueError(
                    "shell-script evidence must preserve the exact "
                    "canonical artifact requirement object"
                )

        if (
            not isinstance(
                self.shell_classpath_references,
                tuple,
            )
            or not all(
                isinstance(
                    resolution,
                    AndroidUniverseShellClasspathResolution,
                )
                for resolution
                in self.shell_classpath_references
            )
        ):
            raise TypeError(
                "shell_classpath_references contains invalid values"
            )

        for resolution in self.shell_classpath_references:
            if not any(
                association.artifact
                is self.artifact
                for association
                in resolution.matched_archives
            ):
                raise ValueError(
                    "shell CLASSPATH evidence must preserve an exact "
                    "Java-archive association for this artifact"
                )

        if not isinstance(
            self.apk_package_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseApkPackageRequirement,
            )
            for requirement
            in self.apk_package_requirements
        ):
            raise TypeError(
                "apk_package_requirements must contain only "
                "AndroidUniverseApkPackageRequirement values"
            )

        for requirement in self.apk_package_requirements:
            if requirement.artifact is not self.artifact:
                raise ValueError(
                    "APK package evidence must retain the exact "
                    "canonical artifact requirement object"
                )

        if not isinstance(
            self.apex_memberships,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in self.apex_memberships
        ):
            raise TypeError(
                "apex_memberships must contain only "
                "AndroidUniverseApexRequirement values"
            )

        filesystem_artifact = (
            self.artifact.inventory_entry.artifact
        )

        payload = filesystem_artifact.parent
        container = (
            payload.parent
            if payload is not None
            else None
        )

        for requirement in self.apex_memberships:
            if container is not requirement.artifact:
                raise ValueError(
                    "APEX membership evidence must preserve exact "
                    "canonical Extraction ancestry"
                )

        if not isinstance(
            self.runtime_linking_candidates,
            tuple,
        ) or not all(
            isinstance(
                candidate,
                AndroidRuntimeLinkerElfRuntimeCandidate,
            )
            for candidate
            in self.runtime_linking_candidates
        ):
            raise TypeError(
                "runtime_linking_candidates must contain only "
                "AndroidRuntimeLinkerElfRuntimeCandidate values"
            )

        elf_requirement_object_ids = {
            id(requirement)
            for requirement
            in self.elf_requirements
        }

        for candidate in self.runtime_linking_candidates:
            if (
                id(candidate.elf_requirement)
                not in elf_requirement_object_ids
            ):
                raise ValueError(
                    "Runtime Linking candidate evidence must preserve "
                    "an exact canonical ELF requirement attached to "
                    "this artifact"
                )

        if not isinstance(
            self.runtime_linking_root_traversals,
            tuple,
        ) or not all(
            isinstance(
                traversal,
                AndroidRuntimeLinkerElfDependencyTraversal,
            )
            for traversal
            in self.runtime_linking_root_traversals
        ):
            raise TypeError(
                "runtime_linking_root_traversals must contain only "
                "AndroidRuntimeLinkerElfDependencyTraversal values"
            )

        for traversal in self.runtime_linking_root_traversals:
            root_candidate = traversal.root_candidate

            if (
                root_candidate is None
                or id(root_candidate.elf_requirement)
                not in elf_requirement_object_ids
            ):
                raise ValueError(
                    "Runtime Linking root traversal evidence must "
                    "preserve an exact canonical ELF requirement "
                    "attached to this artifact"
                )

        for field_name, resolutions in (
            (
                "runtime_linking_parent_dependencies",
                self.runtime_linking_parent_dependencies,
            ),
            (
                "runtime_linking_provider_dependencies",
                self.runtime_linking_provider_dependencies,
            ),
        ):
            if not isinstance(
                resolutions,
                tuple,
            ) or not all(
                isinstance(
                    resolution,
                    AndroidRuntimeLinkerElfDependencyResolution,
                )
                for resolution
                in resolutions
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "AndroidRuntimeLinkerElfDependencyResolution values"
                )

        for resolution in (
            self.runtime_linking_parent_dependencies
        ):
            if (
                id(
                    resolution
                    .parent_candidate
                    .elf_requirement
                )
                not in elf_requirement_object_ids
            ):
                raise ValueError(
                    "Runtime Linking parent dependency evidence must "
                    "preserve an exact canonical ELF requirement "
                    "attached to this artifact"
                )

        for resolution in (
            self.runtime_linking_provider_dependencies
        ):
            provider = resolution.provider_candidate

            if (
                provider is None
                or id(provider.elf_requirement)
                not in elf_requirement_object_ids
            ):
                raise ValueError(
                    "Runtime Linking provider dependency evidence must "
                    "preserve an exact canonical ELF requirement "
                    "attached to this artifact"
                )

        #
        # Kernel-module -> ELF continuity is validated through the exact
        # canonical Universe association population above. Ownership does not
        # reopen ParsedAndroidKernelModule / ParsedAndroidElf identities.
        #

    @property
    def has_elf_evidence(
        self,
    ) -> bool:
        return bool(
            self.elf_requirements
        )

    @property
    def has_kernel_module_evidence(
        self,
    ) -> bool:
        return bool(
            self.kernel_module_requirements
        )

    @property
    def has_init_executable_evidence(
        self,
    ) -> bool:
        return bool(
            self.init_executable_relationships
        )

    @property
    def has_classpath_evidence(
        self,
    ) -> bool:
        return bool(
            self.classpath_installed_jar_resolutions
        )

    @property
    def has_java_archive_evidence(
        self,
    ) -> bool:
        return bool(
            self.java_archive_associations
        )

    @property
    def has_shell_script_evidence(
        self,
    ) -> bool:
        return bool(
            self.shell_script_associations
        )

    @property
    def has_shell_classpath_reference_evidence(
        self,
    ) -> bool:
        return bool(
            self.shell_classpath_references
        )

    @property
    def has_apk_evidence(
        self,
    ) -> bool:
        return bool(
            self.apk_package_requirements
        )

    @property
    def has_apex_membership_evidence(
        self,
    ) -> bool:
        return bool(
            self.apex_memberships
        )

    @property
    def has_runtime_linking_candidate_evidence(
        self,
    ) -> bool:
        return bool(
            self.runtime_linking_candidates
        )

    @property
    def has_runtime_linking_root_evidence(
        self,
    ) -> bool:
        return bool(
            self.runtime_linking_root_traversals
        )

    @property
    def has_runtime_linking_consumer_evidence(
        self,
    ) -> bool:
        return bool(
            self.runtime_linking_parent_dependencies
        )

    @property
    def has_runtime_linking_provider_evidence(
        self,
    ) -> bool:
        return bool(
            self.runtime_linking_provider_dependencies
        )

    @property
    def has_runtime_linking_evidence(
        self,
    ) -> bool:
        return (
            self.has_runtime_linking_candidate_evidence
            or self.has_runtime_linking_root_evidence
            or self.has_runtime_linking_consumer_evidence
            or self.has_runtime_linking_provider_evidence
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidReconstructionArtifactEvidenceInventory:
    """
    Complete deterministic evidence population for canonical artifacts.

    Every AndroidUniverseArtifactRequirement appears exactly once, including
    artifacts for which no additional generic lineage has yet been discovered.
    """

    artifacts: AndroidUniverseArtifactRequirementInventory

    evidence: tuple[
        AndroidReconstructionArtifactEvidence,
        ...,
    ]

    unmatched_filesystem_elf_requirements: tuple[
        AndroidUniverseElfRequirement,
        ...,
    ] = ()

    unmatched_kernel_module_requirements: tuple[
        AndroidUniverseKernelModuleFileRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifacts,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifacts must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidReconstructionArtifactEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidReconstructionArtifactEvidence values"
            )

        expected_ids = tuple(
            id(requirement)
            for requirement
            in self.artifacts.requirements
        )

        observed_ids = tuple(
            id(item.artifact)
            for item
            in self.evidence
        )

        if set(observed_ids) != set(expected_ids):
            raise ValueError(
                "artifact evidence must cover every canonical "
                "artifact requirement exactly once"
            )

        if len(observed_ids) != len(
            set(observed_ids)
        ):
            raise ValueError(
                "artifact evidence contains duplicate canonical artifacts"
            )

        expected_order = tuple(
            requirement.key
            for requirement
            in self.artifacts.requirements
        )

        observed_order = tuple(
            item.artifact.key
            for item
            in self.evidence
        )

        if observed_order != expected_order:
            raise ValueError(
                "artifact evidence must preserve canonical artifact ordering"
            )

        if not isinstance(
            self.unmatched_filesystem_elf_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            )
            for requirement
            in self.unmatched_filesystem_elf_requirements
        ):
            raise TypeError(
                "unmatched_filesystem_elf_requirements has invalid values"
            )

        if not isinstance(
            self.unmatched_kernel_module_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for requirement
            in self.unmatched_kernel_module_requirements
        ):
            raise TypeError(
                "unmatched_kernel_module_requirements has invalid values"
            )

    @property
    def artifacts_with_elf_evidence(
        self,
    ) -> tuple[
        AndroidReconstructionArtifactEvidence,
        ...,
    ]:
        return tuple(
            item
            for item
            in self.evidence
            if item.has_elf_evidence
        )

    @property
    def artifacts_with_kernel_module_evidence(
        self,
    ) -> tuple[
        AndroidReconstructionArtifactEvidence,
        ...,
    ]:
        return tuple(
            item
            for item
            in self.evidence
            if item.has_kernel_module_evidence
        )

    @property
    def artifacts_with_classpath_evidence(
        self,
    ) -> tuple[
        AndroidReconstructionArtifactEvidence,
        ...,
    ]:
        return tuple(
            item
            for item
            in self.evidence
            if item.has_classpath_evidence
        )

    @property
    def artifacts_with_apk_evidence(
        self,
    ) -> tuple[
        AndroidReconstructionArtifactEvidence,
        ...,
    ]:
        return tuple(
            item
            for item
            in self.evidence
            if item.has_apk_evidence
        )

    @property
    def artifacts_with_apex_membership_evidence(
        self,
    ) -> tuple[
        AndroidReconstructionArtifactEvidence,
        ...,
    ]:
        return tuple(
            item
            for item
            in self.evidence
            if item.has_apex_membership_evidence
        )

