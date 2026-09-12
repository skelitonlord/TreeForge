from __future__ import annotations

from dataclasses import dataclass, replace

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
    AndroidUniverseElfRole,
)
from treeforge.android.runtime_linking.linker.elf_dependency_resolution import (
    AndroidRuntimeLinkerElfDependencyResolutionStatus,
    AndroidRuntimeLinkerElfDependencyTraversal,
)


class AndroidReconstructionElfBuildPopulationProjector:
    """
    Project exact canonical filesystem-backed ELF requirements into physical
    syntax-neutral build participation.

    Exact shared upstream object identity is authoritative:

        ELF:
            (
                id(source.filesystem_source.artifact),
                id(source.metadata_entry),
            )

        Artifact:
            requirement.identity_key

    Existing physical build representations always win. A second physical
    representation is never created for an already represented artifact.

    EXECUTABLE and SHARED_OBJECT are intrinsic ELF build roles established by
    Universe structural ELF semantics. OTHER remains semantic-only until a
    stronger canonical build role exists.

    This projector does not:
    - inspect a source checkout;
    - infer module names;
    - match basenames or SONAMEs;
    - choose Make/Soong syntax;
    - choose source-tree ownership or placement;
    - repeat Runtime Linking resolution.
    """

    @staticmethod
    def project(
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
        artifact_requirements,
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
                elf_requirements,
                tuple,
            )
            or not all(
                isinstance(
                    requirement,
                    AndroidUniverseElfRequirement,
                )
                for requirement in elf_requirements
            )
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement values"
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

        requirements = getattr(
            artifact_requirements,
            "requirements",
            None,
        )

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "artifact_requirements must expose canonical "
                "Artifact requirements as a tuple"
            )

        artifact_by_identity = {
            requirement.identity_key: requirement
            for requirement in requirements
        }

        if len(artifact_by_identity) != len(requirements):
            raise ValueError(
                "canonical Artifact requirements must have unique "
                "exact identities"
            )

        represented_artifact_ids = {
            value
            for representation
            in existing_build_representations
            for value
            in (
                representation.preserved_artifact_id,
                representation.canonical_requirement_id,
            )
            if value is not None
        }

        projected = []

        for requirement in elf_requirements:
            if requirement.role not in (
                AndroidUniverseElfRole.EXECUTABLE,
                AndroidUniverseElfRole.SHARED_OBJECT,
            ):
                continue

            source = requirement.source.source

            if not source.is_filesystem_backed:
                continue

            filesystem_source = source.filesystem_source

            if filesystem_source is None:
                raise ValueError(
                    "filesystem-backed ELF source lost "
                    "filesystem_source identity"
                )

            metadata_entry = source.metadata_entry

            if metadata_entry is None:
                continue

            identity_key = (
                id(filesystem_source.artifact),
                id(metadata_entry),
            )

            artifact = artifact_by_identity.get(
                identity_key
            )

            if artifact is None:
                raise ValueError(
                    "filesystem-backed canonical ELF has no exact "
                    "canonical Artifact requirement: "
                    f"{requirement.requirement_id}"
                )

            if (
                artifact.requirement_id
                in represented_artifact_ids
            ):
                continue

            if (
                requirement.role
                is AndroidUniverseElfRole.SHARED_OBJECT
            ):
                kind = (
                    AndroidReconstructionBuildRepresentationKind
                    .NATIVE_LIBRARY
                )
            else:
                kind = (
                    AndroidReconstructionBuildRepresentationKind
                    .EXECUTABLE
                )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:elf:"
                        f"{requirement.requirement_id}"
                    ),
                    kind=kind,
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    ),
                    source_identity=(
                        requirement.requirement_id
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
                        "Canonical ELF and Artifact evidence establish "
                        "exact installed build participation and ELF role, "
                        "but generic Reconstruction does not establish a "
                        "concrete source module or build mechanism."
                    ),
                )
            )

            represented_artifact_ids.add(
                artifact.requirement_id
            )

        result = tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        if len(result) != len(
            {
                representation.canonical_requirement_id
                for representation in result
            }
        ):
            raise ValueError(
                "ELF build projection created duplicate physical "
                "Artifact participation"
            )

        return result


@dataclass(frozen=True, slots=True)
class AndroidReconstructionElfBuildSemantics:
    """
    Syntax-neutral build semantics contributed by one canonical ELF
    requirement.

    This object does not create a second physical build representation for a
    filesystem ELF. When exact Artifact identity exists, it points at the
    already-canonical Artifact build representation.

    Literal ELF evidence remains owned by Parsing and semantic ELF
    interpretation remains owned by Universe. Build-System Reconstruction
    only projects those established facts into build participation context.

    DT_NEEDED names are preserved exactly. They are not resolved to build
    dependencies here because Android linker namespace/search semantics have
    not yet established canonical targets.
    """

    semantics_id: str
    requirement: AndroidUniverseElfRequirement

    target_build_representation_id: str | None = None

    status: AndroidReconstructionBuildRepresentationStatus = (
        AndroidReconstructionBuildRepresentationStatus.PARTIAL
    )

    dependency_names: tuple[str, ...] = ()
    resolved_dependency_ids: tuple[str, ...] = ()

    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.semantics_id,
            str,
        ):
            raise TypeError(
                "semantics_id must be a string"
            )

        if not self.semantics_id:
            raise ValueError(
                "semantics_id must not be empty"
            )

        if not isinstance(
            self.requirement,
            AndroidUniverseElfRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseElfRequirement"
            )

        if (
            self.semantics_id
            != (
                "build:elf:"
                f"{self.requirement.requirement_id}"
            )
        ):
            raise ValueError(
                "semantics_id must preserve canonical ELF "
                "requirement identity"
            )

        if (
            self.target_build_representation_id
            is not None
            and (
                not isinstance(
                    self.target_build_representation_id,
                    str,
                )
                or not self.target_build_representation_id
            )
        ):
            raise ValueError(
                "target_build_representation_id must be a "
                "non-empty string or None"
            )

        if not isinstance(
            self.status,
            AndroidReconstructionBuildRepresentationStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidReconstructionBuildRepresentationStatus"
            )

        if not isinstance(
            self.dependency_names,
            tuple,
        ):
            raise TypeError(
                "dependency_names must be a tuple"
            )

        if not all(
            isinstance(value, str) and value
            for value in self.dependency_names
        ):
            raise ValueError(
                "dependency_names must contain only "
                "non-empty strings"
            )

        expected_dependency_names = tuple(
            dependency.name
            for dependency
            in self.requirement.dependencies
        )

        if (
            self.dependency_names
            != expected_dependency_names
        ):
            raise ValueError(
                "dependency_names must exactly preserve "
                "Universe DT_NEEDED order"
            )

        if not isinstance(
            self.resolved_dependency_ids,
            tuple,
        ):
            raise TypeError(
                "resolved_dependency_ids must be a tuple"
            )

        if not all(
            isinstance(value, str) and value
            for value in self.resolved_dependency_ids
        ):
            raise ValueError(
                "resolved_dependency_ids must contain only "
                "non-empty strings"
            )

        if len(
            self.resolved_dependency_ids
        ) != len(
            set(self.resolved_dependency_ids)
        ):
            raise ValueError(
                "resolved_dependency_ids must be unique"
            )

        if (
            self.resolved_dependency_ids
            != tuple(
                sorted(
                    self.resolved_dependency_ids
                )
            )
        ):
            raise ValueError(
                "resolved_dependency_ids must use "
                "deterministic ordering"
            )

        if (
            self.resolved_dependency_ids
            and not self.dependency_names
        ):
            raise ValueError(
                "resolved ELF dependencies require canonical "
                "DT_NEEDED evidence"
            )

        if (
            self.status
            is AndroidReconstructionBuildRepresentationStatus.UNRESOLVED
            and self.reason is None
        ):
            raise ValueError(
                "UNRESOLVED ELF build semantics requires a reason"
            )


class AndroidReconstructionElfBuildProjector:
    """
    Project canonical ELF requirements into Build-System semantics.

    Filesystem-backed ELF objects attach only through exact shared
    filesystem Artifact identity. No path or basename matching is allowed.

    Extraction-backed ELF objects remain standalone semantic observations
    because no canonical filesystem Artifact representation exists for them.

    DT_NEEDED resolution is consumed only from canonical Runtime Linking
    traversals. Build-System Reconstruction never repeats linker namespace,
    runtime-path, architecture, alias, or provider resolution.
    """

    @staticmethod
    def apply_resolved_dependencies(
        *,
        elf_semantics: tuple[
            AndroidReconstructionElfBuildSemantics,
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
        Project already-resolved Runtime Linking ELF providers onto physical
        Build-System representation dependencies.

        ``AndroidReconstructionElfBuildSemantics.resolved_dependency_ids``
        preserves canonical provider ELF requirement identities. This pass
        translates only providers that themselves have an exact physical
        Build-System representation.

        It never repeats linker resolution and never guesses a provider.
        """

        if not isinstance(
            elf_semantics,
            tuple,
        ):
            raise TypeError(
                "elf_semantics must be a tuple"
            )

        if not all(
            isinstance(
                semantics,
                AndroidReconstructionElfBuildSemantics,
            )
            for semantics in elf_semantics
        ):
            raise TypeError(
                "elf_semantics contains an invalid model"
            )

        if not isinstance(
            build_representations,
            tuple,
        ):
            raise TypeError(
                "build_representations must be a tuple"
            )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionBuildRepresentation,
            )
            for representation in build_representations
        ):
            raise TypeError(
                "build_representations contains an invalid model"
            )

        representation_by_id = {
            representation.representation_id: representation
            for representation in build_representations
        }

        if len(
            representation_by_id
        ) != len(
            build_representations
        ):
            raise ValueError(
                "Build-System representation identities must be unique"
            )

        representation_id_by_elf_requirement_id = {}

        for semantics in elf_semantics:
            target_id = (
                semantics.target_build_representation_id
            )

            if target_id is None:
                continue

            if target_id not in representation_by_id:
                raise ValueError(
                    "ELF semantics targets a missing Build-System "
                    "representation: "
                    f"{target_id}"
                )

            requirement_id = (
                semantics.requirement.requirement_id
            )

            existing = (
                representation_id_by_elf_requirement_id.get(
                    requirement_id
                )
            )

            if (
                existing is not None
                and existing != target_id
            ):
                raise ValueError(
                    "one canonical ELF requirement maps to multiple "
                    "physical Build-System representations"
                )

            representation_id_by_elf_requirement_id[
                requirement_id
            ] = target_id

        dependencies_by_representation_id: dict[
            str,
            set[str],
        ] = {}

        for semantics in elf_semantics:
            parent_representation_id = (
                semantics.target_build_representation_id
            )

            if parent_representation_id is None:
                continue

            for provider_requirement_id in (
                semantics.resolved_dependency_ids
            ):
                provider_representation_id = (
                    representation_id_by_elf_requirement_id.get(
                        provider_requirement_id
                    )
                )

                #
                # A resolved runtime provider may intentionally have no
                # physical build representation yet, for example an ELF role
                # that remains semantic-only. Preserve the Runtime Linking
                # conclusion in elf_semantics, but do not manufacture a build
                # dependency target.
                #
                if provider_representation_id is None:
                    continue

                if (
                    provider_representation_id
                    == parent_representation_id
                ):
                    #
                    # Self-resolution is meaningful runtime evidence but does
                    # not need a Build-System self-dependency edge.
                    #
                    continue

                dependencies_by_representation_id.setdefault(
                    parent_representation_id,
                    set(),
                ).add(
                    provider_representation_id
                )

        projected = []

        for representation in build_representations:
            additions = (
                dependencies_by_representation_id.get(
                    representation.representation_id,
                    set(),
                )
            )

            if not additions:
                projected.append(
                    representation
                )
                continue

            dependency_ids = tuple(
                sorted(
                    {
                        *representation.dependency_ids,
                        *additions,
                    }
                )
            )

            projected.append(
                replace(
                    representation,
                    dependency_ids=dependency_ids,
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

        result_ids = {
            representation.representation_id
            for representation in result
        }

        for representation in result:
            missing = (
                set(representation.dependency_ids)
                - result_ids
            )

            if missing:
                raise ValueError(
                    "Build-System dependency references missing "
                    "representation identities: "
                    f"{sorted(missing)!r}"
                )

        return result

    @staticmethod
    def project(
        reconstruction_input: AndroidReconstructionInput,
        artifact_build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ],
        *,
        runtime_linking_traversals: tuple[
            AndroidRuntimeLinkerElfDependencyTraversal,
            ...,
        ] = (),
    ) -> tuple[
        AndroidReconstructionElfBuildSemantics,
        ...,
    ]:
        if not isinstance(
            reconstruction_input,
            AndroidReconstructionInput,
        ):
            raise TypeError(
                "reconstruction_input must be an "
                "AndroidReconstructionInput"
            )

        if not isinstance(
            artifact_build_representations,
            tuple,
        ):
            raise TypeError(
                "artifact_build_representations must be a tuple"
            )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionBuildRepresentation,
            )
            for representation
            in artifact_build_representations
        ):
            raise TypeError(
                "artifact_build_representations contains "
                "an invalid model"
            )

        if not isinstance(
            runtime_linking_traversals,
            tuple,
        ):
            raise TypeError(
                "runtime_linking_traversals must be a tuple"
            )

        if not all(
            isinstance(
                traversal,
                AndroidRuntimeLinkerElfDependencyTraversal,
            )
            for traversal
            in runtime_linking_traversals
        ):
            raise TypeError(
                "runtime_linking_traversals contains an "
                "invalid Runtime Linking traversal"
            )

        build_representation_by_preserved_id = {
            representation.preserved_artifact_id: representation
            for representation
            in artifact_build_representations
        }

        artifact_build_by_identity = {}

        for item in reconstruction_input.work_items:
            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.PRESERVE
                or item.requirement_kind != "artifact"
            ):
                continue

            requirement = item.obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise TypeError(
                    "artifact Reconstruction work must preserve "
                    "AndroidUniverseArtifactRequirement"
                )

            representation = (
                build_representation_by_preserved_id.get(
                    item.preserved_artifact_id
                )
            )

            if representation is None:
                raise ValueError(
                    "preserved Artifact work has no canonical "
                    "Build-System representation: "
                    f"{item.obligation_id}"
                )

            identity_key = requirement.identity_key

            existing = artifact_build_by_identity.get(
                identity_key
            )

            if (
                existing is not None
                and existing.representation_id
                != representation.representation_id
            ):
                raise ValueError(
                    "exact Artifact identity maps to multiple "
                    "Build-System representations"
                )

            artifact_build_by_identity[
                identity_key
            ] = representation

        #
        # Requirement-backed physical build representations also preserve
        # exact canonical Artifact identity. This includes ELF population
        # created immediately before this semantic projection.
        #
        canonical_artifact_requirements = (
            reconstruction_input
            .runtime_linking
            .universe
            .artifact_requirements
            .requirements
        )

        artifact_requirement_by_id = {
            requirement.requirement_id: requirement
            for requirement
            in canonical_artifact_requirements
        }

        if len(
            artifact_requirement_by_id
        ) != len(
            canonical_artifact_requirements
        ):
            raise ValueError(
                "canonical Artifact requirement identities "
                "must be unique"
            )

        for representation in artifact_build_representations:
            artifact_id = (
                representation.canonical_requirement_id
            )

            if artifact_id is None:
                continue

            artifact_requirement = (
                artifact_requirement_by_id.get(
                    artifact_id
                )
            )

            if artifact_requirement is None:
                continue

            identity_key = (
                artifact_requirement.identity_key
            )

            existing = (
                artifact_build_by_identity.get(
                    identity_key
                )
            )

            if (
                existing is not None
                and existing.representation_id
                != representation.representation_id
            ):
                raise ValueError(
                    "exact Artifact identity maps to multiple "
                    "Build-System representations"
                )

            artifact_build_by_identity[
                identity_key
            ] = representation

        resolved_provider_ids_by_parent_source: dict[
            int,
            set[str],
        ] = {}

        observed_dependencies_by_parent_source: dict[
            int,
            set[int],
        ] = {}

        all_resolved_by_parent_source: dict[
            int,
            bool,
        ] = {}

        for traversal in runtime_linking_traversals:
            for resolution in traversal.dependency_resolutions:
                parent_source = (
                    resolution.parent_candidate
                    .elf_requirement
                    .source
                )

                if (
                    resolution.dependency.source
                    is not parent_source
                ):
                    raise ValueError(
                        "Runtime Linking dependency must preserve "
                        "exact parent ELF source identity"
                    )

                parent_key = id(
                    parent_source
                )

                observed_dependencies_by_parent_source.setdefault(
                    parent_key,
                    set(),
                ).add(
                    id(resolution.dependency)
                )

                all_resolved_by_parent_source[
                    parent_key
                ] = (
                    all_resolved_by_parent_source.get(
                        parent_key,
                        True,
                    )
                    and (
                        resolution.status
                        is (
                            AndroidRuntimeLinkerElfDependencyResolutionStatus
                            .RESOLVED
                        )
                    )
                )

                if (
                    resolution.status
                    is not (
                        AndroidRuntimeLinkerElfDependencyResolutionStatus
                        .RESOLVED
                    )
                ):
                    continue

                provider_candidate = (
                    resolution.provider_candidate
                )

                if provider_candidate is None:
                    raise ValueError(
                        "resolved Runtime Linking dependency must "
                        "preserve its exact provider candidate"
                    )

                provider_requirement = (
                    provider_candidate
                    .elf_requirement
                )

                resolved_provider_ids_by_parent_source.setdefault(
                    parent_key,
                    set(),
                ).add(
                    provider_requirement.requirement_id
                )

        projected = []

        for item in reconstruction_input.work_items:
            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.PRESERVE
                or item.requirement_kind != "elf"
            ):
                continue

            requirement = item.obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            ):
                raise TypeError(
                    "ELF Reconstruction work must preserve "
                    "AndroidUniverseElfRequirement"
                )

            if (
                item.source_identity
                != requirement.requirement_id
            ):
                raise ValueError(
                    "ELF work source_identity must preserve "
                    "canonical Universe requirement identity"
                )

            if (
                item.preserved_artifact_id
                != requirement.requirement_id
            ):
                raise ValueError(
                    "ELF preserved_artifact_id must preserve "
                    "canonical Universe requirement identity"
                )

            source = requirement.source.source
            target_representation = None

            if source.is_filesystem_backed:
                filesystem_source = source.filesystem_source

                if filesystem_source is None:
                    raise ValueError(
                        "filesystem-backed ELF source must retain "
                        "filesystem_source"
                    )

                if source.metadata_entry is not None:
                    identity_key = (
                        id(filesystem_source.artifact),
                        id(source.metadata_entry),
                    )

                    target_representation = (
                        artifact_build_by_identity.get(
                            identity_key
                        )
                    )

            dependency_names = tuple(
                dependency.name
                for dependency
                in requirement.dependencies
            )

            parent_source_key = id(
                requirement.source
            )

            resolved_dependency_ids = tuple(
                sorted(
                    resolved_provider_ids_by_parent_source.get(
                        parent_source_key,
                        set(),
                    )
                )
            )

            expected_dependency_identity = {
                id(dependency)
                for dependency
                in requirement.dependencies
            }

            observed_dependency_identity = (
                observed_dependencies_by_parent_source.get(
                    parent_source_key,
                    set(),
                )
            )

            runtime_dependency_complete = (
                bool(
                    expected_dependency_identity
                )
                and (
                    observed_dependency_identity
                    == expected_dependency_identity
                )
                and all_resolved_by_parent_source.get(
                    parent_source_key,
                    False,
                )
            )

            if target_representation is None:
                status = (
                    AndroidReconstructionBuildRepresentationStatus
                    .PARTIAL
                )

                if source.is_extraction_backed:
                    reason = (
                        "ELF semantics are preserved from an "
                        "extraction-backed source, but no canonical "
                        "filesystem Artifact build representation exists."
                    )
                elif source.metadata_entry is None:
                    reason = (
                        "Filesystem-backed ELF semantics cannot attach "
                        "to an Artifact build representation because the "
                        "source has no canonical regular-file metadata entry."
                    )
                else:
                    reason = (
                        "ELF semantics have exact filesystem identity, "
                        "but the corresponding Artifact does not participate "
                        "as a preserved Build-System representation."
                    )

            elif dependency_names:
                if runtime_dependency_complete:
                    status = (
                        AndroidReconstructionBuildRepresentationStatus
                        .RESOLVED
                    )
                    reason = None
                else:
                    status = (
                        AndroidReconstructionBuildRepresentationStatus
                        .PARTIAL
                    )

                    if not observed_dependency_identity:
                        reason = (
                            "ELF semantics attach to the exact Artifact "
                            "build representation, but this canonical ELF "
                            "does not participate in a resolved Runtime "
                            "Linking dependency traversal."
                        )
                    elif (
                        observed_dependency_identity
                        != expected_dependency_identity
                    ):
                        reason = (
                            "Runtime Linking reaches this canonical ELF, "
                            "but does not provide contextual observations "
                            "for every canonical DT_NEEDED requirement."
                        )
                    else:
                        reason = (
                            "Runtime Linking observes every canonical "
                            "DT_NEEDED requirement for this ELF, but at "
                            "least one contextual dependency occurrence "
                            "remains ambiguous or unresolved."
                        )

            else:
                status = (
                    AndroidReconstructionBuildRepresentationStatus
                    .RESOLVED
                )
                reason = None

            projected.append(
                AndroidReconstructionElfBuildSemantics(
                    semantics_id=(
                        "build:elf:"
                        f"{requirement.requirement_id}"
                    ),
                    requirement=requirement,
                    target_build_representation_id=(
                        target_representation.representation_id
                        if target_representation is not None
                        else None
                    ),
                    status=status,
                    dependency_names=dependency_names,
                    resolved_dependency_ids=(
                        resolved_dependency_ids
                    ),
                    reason=reason,
                )
            )

        return tuple(
            sorted(
                projected,
                key=lambda semantics: (
                    semantics.semantics_id
                ),
            )
        )
