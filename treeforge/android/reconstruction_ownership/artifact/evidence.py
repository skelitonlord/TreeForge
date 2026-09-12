from __future__ import annotations

from treeforge.android.universe.elf.artifact_association import (
    AndroidUniverseElfArtifactAssociation,
    AndroidUniverseElfArtifactAssociationKind,
)
from treeforge.android.universe.kernel_module.elf_association import (
    AndroidUniverseKernelModuleElfAssociation,
)


from collections import defaultdict

from treeforge.android.reconstruction_ownership.artifact.evidence_model import (
    AndroidReconstructionArtifactEvidence,
    AndroidReconstructionArtifactEvidenceInventory,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.runtime_linking.model import (
    AndroidRuntimeLinking,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkRequirement,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathRequirement,
)
from treeforge.android.universe.shell_script import (
    AndroidUniverseShellScriptReconciliation,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleRequirement,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseInitExecutableArtifactRelationship,
)


class AndroidReconstructionArtifactEvidenceCollector:
    """
    Collect generic semantic lineage around exact canonical filesystem artifacts.

    Exact canonical Universe object identity is authoritative.

    Filesystem-backed ELF evidence is attached through the exact
    AndroidUniverseElfArtifactAssociation produced by Universe.

    Kernel-module evidence is attached through the exact canonical
    kernel-module/ELF association and the ELF's canonical artifact
    association.

    Ownership does not reopen Parsing filesystem, metadata, or ELF source
    identities to reconstruct relationships that Universe already owns.

    No path-name, partition, basename, SONAME, hash, or install-location
    heuristic participates in this bridge.
    """

    @classmethod
    def collect(
        cls,
        *,
        artifacts: AndroidUniverseArtifactRequirementInventory,
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
        elf_artifact_associations: tuple[
            AndroidUniverseElfArtifactAssociation,
            ...,
        ],
        kernel_module_elf_associations: tuple[
            AndroidUniverseKernelModuleElfAssociation,
            ...,
        ],
        kernel_module_requirement: (
            AndroidUniverseKernelModuleRequirement
            | None
        ),
        classpath_requirement: (
            AndroidUniverseClasspathRequirement
            | None
        ),
        shell_script_reconciliation: (
            AndroidUniverseShellScriptReconciliation
            | None
        ),
        apk_requirement: (
            AndroidUniverseApkRequirement
            | None
        ),
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
        runtime_linking: AndroidRuntimeLinking | None,
        cross_family_relationships: tuple[
            object,
            ...,
        ],
    ) -> AndroidReconstructionArtifactEvidenceInventory:
        if not isinstance(
            artifacts,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifacts must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        if not isinstance(
            elf_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            )
            for requirement
            in elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement values"
            )

        if not isinstance(
            elf_artifact_associations,
            tuple,
        ) or not all(
            isinstance(
                association,
                AndroidUniverseElfArtifactAssociation,
            )
            for association
            in elf_artifact_associations
        ):
            raise TypeError(
                "elf_artifact_associations must contain only "
                "AndroidUniverseElfArtifactAssociation values"
            )

        if not isinstance(
            kernel_module_elf_associations,
            tuple,
        ) or not all(
            isinstance(
                association,
                AndroidUniverseKernelModuleElfAssociation,
            )
            for association
            in kernel_module_elf_associations
        ):
            raise TypeError(
                "kernel_module_elf_associations must contain only "
                "AndroidUniverseKernelModuleElfAssociation values"
            )

        if (
            kernel_module_requirement is not None
            and not isinstance(
                kernel_module_requirement,
                AndroidUniverseKernelModuleRequirement,
            )
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement or None"
            )

        if (
            classpath_requirement is not None
            and not isinstance(
                classpath_requirement,
                AndroidUniverseClasspathRequirement,
            )
        ):
            raise TypeError(
                "classpath_requirement must be an "
                "AndroidUniverseClasspathRequirement or None"
            )

        if (
            apk_requirement is not None
            and not isinstance(
                apk_requirement,
                AndroidUniverseApkRequirement,
            )
        ):
            raise TypeError(
                "apk_requirement must be an "
                "AndroidUniverseApkRequirement or None"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement values"
            )

        if (
            runtime_linking is not None
            and not isinstance(
                runtime_linking,
                AndroidRuntimeLinking,
            )
        ):
            raise TypeError(
                "runtime_linking must be an "
                "AndroidRuntimeLinking or None"
            )

        if not isinstance(
            cross_family_relationships,
            tuple,
        ):
            raise TypeError(
                "cross_family_relationships must be a tuple"
            )

        canonical_artifact_object_ids = {
            id(requirement)
            for requirement
            in artifacts.requirements
        }

        canonical_elf_requirement_object_ids = {
            id(requirement)
            for requirement
            in elf_requirements
        }

        if (
            len(
                elf_artifact_associations
            )
            != len(
                elf_requirements
            )
        ):
            raise ValueError(
                "Universe ELF/artifact association coverage must equal "
                "canonical ELF requirement coverage"
            )

        elf_association_by_elf_requirement_id = {}

        elf_associations_by_artifact_object_id = defaultdict(
            list
        )

        for association in (
            elf_artifact_associations
        ):
            elf_requirement_id = id(
                association.elf_requirement
            )

            if (
                elf_requirement_id
                not in canonical_elf_requirement_object_ids
            ):
                raise ValueError(
                    "Universe ELF/artifact association references an "
                    "ELF requirement outside the supplied canonical "
                    "ELF population"
                )

            if (
                elf_requirement_id
                in elf_association_by_elf_requirement_id
            ):
                raise ValueError(
                    "multiple Universe ELF/artifact associations "
                    "reference one canonical ELF requirement"
                )

            elf_association_by_elf_requirement_id[
                elf_requirement_id
            ] = association

            if (
                association.kind
                is AndroidUniverseElfArtifactAssociationKind
                .EXTRACTION_ARTIFACT
            ):
                continue

            artifact = (
                association.artifact_requirement
            )

            if (
                artifact is None
                or id(artifact)
                not in canonical_artifact_object_ids
            ):
                raise ValueError(
                    "filesystem ELF association does not retain an "
                    "exact canonical artifact requirement"
                )

            elf_associations_by_artifact_object_id[
                id(artifact)
            ].append(
                association
            )

        if set(
            elf_association_by_elf_requirement_id
        ) != canonical_elf_requirement_object_ids:
            raise ValueError(
                "Universe ELF/artifact associations must cover every "
                "supplied canonical ELF requirement exactly once"
            )

        unmatched_elf = []

        kernel_associations_by_artifact_object_id = defaultdict(
            list
        )

        unmatched_kernel = []

        expected_kernel_module_requirement_ids = (
            {
                id(requirement)
                for requirement
                in (
                    kernel_module_requirement
                    .module_requirements
                )
            }
            if kernel_module_requirement is not None
            else set()
        )

        if (
            len(
                kernel_module_elf_associations
            )
            != len(
                expected_kernel_module_requirement_ids
            )
        ):
            raise ValueError(
                "Universe kernel-module/ELF association coverage must "
                "equal canonical kernel-module file coverage"
            )

        observed_kernel_module_requirement_ids = set()

        for association in (
            kernel_module_elf_associations
        ):
            module_requirement = (
                association.module_requirement
            )

            module_requirement_id = id(
                module_requirement
            )

            if (
                module_requirement_id
                not in expected_kernel_module_requirement_ids
            ):
                raise ValueError(
                    "Universe kernel-module/ELF association references "
                    "a module outside the canonical module population"
                )

            if (
                module_requirement_id
                in observed_kernel_module_requirement_ids
            ):
                raise ValueError(
                    "multiple Universe kernel-module/ELF associations "
                    "reference one module requirement"
                )

            observed_kernel_module_requirement_ids.add(
                module_requirement_id
            )

            elf_association = (
                elf_association_by_elf_requirement_id.get(
                    id(
                        association.elf_requirement
                    )
                )
            )

            if elf_association is None:
                raise ValueError(
                    "kernel-module/ELF association references an ELF "
                    "without a canonical ELF/artifact association"
                )

            if (
                elf_association.kind
                is AndroidUniverseElfArtifactAssociationKind
                .EXTRACTION_ARTIFACT
            ):
                unmatched_kernel.append(
                    module_requirement
                )
                continue

            artifact = (
                elf_association.artifact_requirement
            )

            if artifact is None:
                raise ValueError(
                    "filesystem ELF association lost its canonical "
                    "artifact requirement"
                )

            kernel_associations_by_artifact_object_id[
                id(artifact)
            ].append(
                association
            )

        if (
            observed_kernel_module_requirement_ids
            != expected_kernel_module_requirement_ids
        ):
            raise ValueError(
                "kernel-module/ELF associations must preserve every "
                "canonical module requirement exactly once"
            )

        init_by_artifact_object_id = defaultdict(
            list
        )

        canonical_artifact_object_ids = {
            id(requirement)
            for requirement
            in artifacts.requirements
        }

        for relationship in cross_family_relationships:
            if not isinstance(
                relationship,
                AndroidUniverseInitExecutableArtifactRelationship,
            ):
                continue

            for matched_artifact in (
                relationship.matched_artifacts
            ):
                if (
                    id(matched_artifact)
                    not in canonical_artifact_object_ids
                ):
                    raise ValueError(
                        "INIT executable relationship contains an "
                        "artifact that is not the exact canonical "
                        "Universe artifact requirement object"
                    )

                init_by_artifact_object_id[
                    id(matched_artifact)
                ].append(
                    relationship
                )

        classpath_by_artifact_object_id = defaultdict(
            list
        )

        if classpath_requirement is not None:
            for resolution in (
                classpath_requirement
                .installed_jar_resolutions
            ):
                for matched_artifact in (
                    resolution.matched_artifacts
                ):
                    if (
                        id(matched_artifact)
                        not in canonical_artifact_object_ids
                    ):
                        raise ValueError(
                            "Classpath installed-JAR resolution contains "
                            "an artifact that is not the exact canonical "
                            "Universe artifact requirement object"
                        )

                    classpath_by_artifact_object_id[
                        id(matched_artifact)
                    ].append(
                        resolution
                    )

        java_archive_by_artifact_object_id = defaultdict(
            list
        )

        if classpath_requirement is not None:
            for association in (
                classpath_requirement
                .java_archive_reconciliation
                .associations
            ):
                artifact = association.artifact

                if (
                    id(artifact)
                    not in canonical_artifact_object_ids
                ):
                    raise ValueError(
                        "Java-archive association contains an artifact "
                        "outside the canonical Universe inventory"
                    )

                java_archive_by_artifact_object_id[
                    id(artifact)
                ].append(
                    association
                )

        shell_script_by_artifact_object_id = defaultdict(
            list
        )

        shell_classpath_by_artifact_object_id = defaultdict(
            list
        )

        if shell_script_reconciliation is not None:
            for association in (
                shell_script_reconciliation.associations
            ):
                artifact = association.artifact

                if (
                    id(artifact)
                    not in canonical_artifact_object_ids
                ):
                    raise ValueError(
                        "shell-script association contains an artifact "
                        "outside the canonical Universe inventory"
                    )

                shell_script_by_artifact_object_id[
                    id(artifact)
                ].append(
                    association
                )

                for resolution in (
                    association.classpath_resolutions
                ):
                    for archive in (
                        resolution.matched_archives
                    ):
                        matched_artifact = (
                            archive.artifact
                        )

                        if (
                            id(matched_artifact)
                            not in canonical_artifact_object_ids
                        ):
                            raise ValueError(
                                "shell CLASSPATH resolution references "
                                "a non-canonical Artifact requirement"
                            )

                        shell_classpath_by_artifact_object_id[
                            id(matched_artifact)
                        ].append(
                            resolution
                        )

        apk_by_artifact_object_id = defaultdict(
            list
        )

        if apk_requirement is not None:
            for package_requirement in (
                apk_requirement.packages
            ):
                artifact = (
                    package_requirement.artifact
                )

                if (
                    id(artifact)
                    not in canonical_artifact_object_ids
                ):
                    raise ValueError(
                        "APK package requirement contains an "
                        "artifact that is not the exact canonical "
                        "Universe artifact requirement object"
                    )

                apk_by_artifact_object_id[
                    id(artifact)
                ].append(
                    package_requirement
                )

        apex_by_container_object_id = {}

        for requirement in apex_requirements:
            container_id = id(
                requirement.artifact
            )

            existing = (
                apex_by_container_object_id.get(
                    container_id
                )
            )

            if (
                existing is not None
                and existing is not requirement
            ):
                raise ValueError(
                    "multiple canonical APEX requirements preserve "
                    "one Extraction container identity"
                )

            apex_by_container_object_id[
                container_id
            ] = requirement

        apex_membership_by_artifact_object_id = defaultdict(
            list
        )

        for artifact in artifacts.requirements:
            filesystem_artifact = (
                artifact.inventory_entry.artifact
            )

            payload = filesystem_artifact.parent

            if payload is None:
                continue

            container = payload.parent

            if container is None:
                continue

            apex_requirement = (
                apex_by_container_object_id.get(
                    id(container)
                )
            )

            if apex_requirement is None:
                continue

            apex_membership_by_artifact_object_id[
                id(artifact)
            ].append(
                apex_requirement
            )

        runtime_candidates_by_elf_requirement_id = defaultdict(
            list
        )
        runtime_root_traversals_by_elf_requirement_id = defaultdict(
            list
        )
        runtime_parent_dependencies_by_elf_requirement_id = defaultdict(
            list
        )
        runtime_provider_dependencies_by_elf_requirement_id = defaultdict(
            list
        )

        if runtime_linking is not None:
            canonical_elf_requirement_ids = {
                id(requirement)
                for requirement
                in elf_requirements
            }

            for candidate in (
                runtime_linking
                .linker_elf_runtime_candidates
            ):
                if (
                    id(candidate.elf_requirement)
                    not in canonical_elf_requirement_ids
                ):
                    raise ValueError(
                        "Runtime Linking candidate does not preserve "
                        "an exact canonical Universe ELF requirement"
                    )

                runtime_candidates_by_elf_requirement_id[
                    id(candidate.elf_requirement)
                ].append(
                    candidate
                )

            for traversal in (
                runtime_linking
                .linker_elf_dependency_traversals
            ):
                root_candidate = traversal.root_candidate

                if root_candidate is not None:
                    if (
                        id(root_candidate.elf_requirement)
                        not in canonical_elf_requirement_ids
                    ):
                        raise ValueError(
                            "Runtime Linking traversal root does not "
                            "preserve an exact canonical Universe "
                            "ELF requirement"
                        )

                    runtime_root_traversals_by_elf_requirement_id[
                        id(root_candidate.elf_requirement)
                    ].append(
                        traversal
                    )

                for resolution in (
                    traversal.dependency_resolutions
                ):
                    parent_requirement = (
                        resolution
                        .parent_candidate
                        .elf_requirement
                    )

                    if (
                        id(parent_requirement)
                        not in canonical_elf_requirement_ids
                    ):
                        raise ValueError(
                            "Runtime Linking dependency parent does not "
                            "preserve an exact canonical Universe "
                            "ELF requirement"
                        )

                    runtime_parent_dependencies_by_elf_requirement_id[
                        id(parent_requirement)
                    ].append(
                        resolution
                    )

                    provider_candidate = (
                        resolution.provider_candidate
                    )

                    if provider_candidate is None:
                        continue

                    provider_requirement = (
                        provider_candidate.elf_requirement
                    )

                    if (
                        id(provider_requirement)
                        not in canonical_elf_requirement_ids
                    ):
                        raise ValueError(
                            "Runtime Linking dependency provider does not "
                            "preserve an exact canonical Universe "
                            "ELF requirement"
                        )

                    runtime_provider_dependencies_by_elf_requirement_id[
                        id(provider_requirement)
                    ].append(
                        resolution
                    )

        evidence = []

        for artifact in artifacts.requirements:
            artifact_object_id = id(
                artifact
            )

            elf_association_evidence = tuple(
                sorted(
                    elf_associations_by_artifact_object_id.get(
                        artifact_object_id,
                        (),
                    ),
                    key=lambda association: (
                        association
                        .elf_requirement
                        .requirement_id
                    ),
                )
            )

            elf_evidence = tuple(
                association.elf_requirement
                for association
                in elf_association_evidence
            )

            kernel_module_elf_association_evidence = tuple(
                sorted(
                    kernel_associations_by_artifact_object_id.get(
                        artifact_object_id,
                        (),
                    ),
                    key=lambda association: (
                        association.association_id
                    ),
                )
            )

            kernel_evidence = tuple(
                association.module_requirement
                for association
                in kernel_module_elf_association_evidence
            )

            init_evidence = tuple(
                sorted(
                    init_by_artifact_object_id.get(
                        id(artifact),
                        (),
                    ),
                    key=lambda relationship: (
                        relationship.relationship_id
                    ),
                )
            )

            classpath_evidence = tuple(
                classpath_by_artifact_object_id.get(
                    id(artifact),
                    (),
                )
            )

            java_archive_evidence = tuple(
                java_archive_by_artifact_object_id.get(
                    id(artifact),
                    (),
                )
            )

            shell_script_evidence = tuple(
                shell_script_by_artifact_object_id.get(
                    id(artifact),
                    (),
                )
            )

            shell_classpath_evidence = tuple(
                shell_classpath_by_artifact_object_id.get(
                    id(artifact),
                    (),
                )
            )

            apk_evidence = tuple(
                sorted(
                    apk_by_artifact_object_id.get(
                        id(artifact),
                        (),
                    ),
                    key=lambda requirement: (
                        requirement.requirement_id
                    ),
                )
            )

            apex_memberships = tuple(
                sorted(
                    apex_membership_by_artifact_object_id.get(
                        id(artifact),
                        (),
                    ),
                    key=lambda requirement: (
                        requirement.requirement_id
                    ),
                )
            )

            runtime_candidates = tuple(
                candidate
                for elf_requirement
                in elf_evidence
                for candidate
                in runtime_candidates_by_elf_requirement_id.get(
                    id(elf_requirement),
                    (),
                )
            )

            runtime_root_traversals = tuple(
                traversal
                for elf_requirement
                in elf_evidence
                for traversal
                in runtime_root_traversals_by_elf_requirement_id.get(
                    id(elf_requirement),
                    (),
                )
            )

            runtime_parent_dependencies = tuple(
                resolution
                for elf_requirement
                in elf_evidence
                for resolution
                in runtime_parent_dependencies_by_elf_requirement_id.get(
                    id(elf_requirement),
                    (),
                )
            )

            runtime_provider_dependencies = tuple(
                resolution
                for elf_requirement
                in elf_evidence
                for resolution
                in runtime_provider_dependencies_by_elf_requirement_id.get(
                    id(elf_requirement),
                    (),
                )
            )

            evidence.append(
                AndroidReconstructionArtifactEvidence(
                    artifact=artifact,
                    elf_requirements=(
                        elf_evidence
                    ),
                    elf_artifact_associations=(
                        elf_association_evidence
                    ),
                    kernel_module_requirements=(
                        kernel_evidence
                    ),
                    kernel_module_elf_associations=(
                        kernel_module_elf_association_evidence
                    ),
                    init_executable_relationships=(
                        init_evidence
                    ),
                    classpath_installed_jar_resolutions=(
                        classpath_evidence
                    ),
                    java_archive_associations=(
                        java_archive_evidence
                    ),
                    shell_script_associations=(
                        shell_script_evidence
                    ),
                    shell_classpath_references=(
                        shell_classpath_evidence
                    ),
                    apk_package_requirements=(
                        apk_evidence
                    ),
                    apex_memberships=(
                        apex_memberships
                    ),
                    runtime_linking_candidates=(
                        runtime_candidates
                    ),
                    runtime_linking_root_traversals=(
                        runtime_root_traversals
                    ),
                    runtime_linking_parent_dependencies=(
                        runtime_parent_dependencies
                    ),
                    runtime_linking_provider_dependencies=(
                        runtime_provider_dependencies
                    ),
                )
            )

        unmatched_elf = tuple(
            sorted(
                unmatched_elf,
                key=lambda requirement: (
                    requirement.requirement_id
                ),
            )
        )

        unmatched_kernel = tuple(
            sorted(
                unmatched_kernel,
                key=lambda requirement: (
                    requirement.source
                    .elf
                    .source
                    .identity_key
                ),
            )
        )

        return (
            AndroidReconstructionArtifactEvidenceInventory(
                artifacts=artifacts,
                evidence=tuple(
                    evidence
                ),
                unmatched_filesystem_elf_requirements=(
                    unmatched_elf
                ),
                unmatched_kernel_module_requirements=(
                    unmatched_kernel
                ),
            )
        )
