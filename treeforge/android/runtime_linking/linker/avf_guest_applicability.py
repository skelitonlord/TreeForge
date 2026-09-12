from __future__ import annotations

from treeforge.android.universe.avf import (
    AndroidUniverseAvfRequirement,
)

from treeforge.android.runtime_linking.linker.elf_runtime_candidate import (
    AndroidRuntimeLinkerElfRuntimeCandidate,
    AndroidRuntimeLinkerElfRuntimeCandidateStatus,
)

from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerExecutableLoadingContext,
    AndroidUniverseLinkerExecutableLoadingContextStatus,
)


class AndroidRuntimeLinkerAvfGuestTraversalApplicability:
    """
    Determine whether a canonical executable loading context is inapplicable
    as a host Android contextual-DT_NEEDED traversal root because AVF/runtime
    evidence proves that the execution contract belongs to another canonical
    Android runtime.

    Strong generic evidence consists of either:

    1. the exact executable runtime path being declared as an AVF executable
       task; or

    2. an executable from an APEX explicitly selected into an AVF VM requiring
       a DT_NEEDED provider absent from its own runtime but present in a
       distinct canonical Android runtime.

    Linker section/namespace routing remains untouched. This class determines
    traversal applicability only.
    """

    DIRECT_TASK_REASON = (
        "canonical AVF executable task declaration identifies this "
        "runtime path as a guest execution root"
    )

    DISTINCT_RUNTIME_REASON_PREFIX = (
        "AVF-selected APEX executable has required DT_NEEDED provider "
        "only in a distinct canonical Android runtime"
    )

    @staticmethod
    def _candidate_names(
        candidate: AndroidRuntimeLinkerElfRuntimeCandidate,
    ) -> frozenset[
        str
    ]:
        values = set()

        if (
            candidate.physical_basename
            is not None
        ):
            values.add(
                candidate.physical_basename
            )

        if candidate.soname is not None:
            values.add(
                candidate.soname
            )

        values.update(
            path.name
            for path
            in candidate.runtime_alias_paths
        )

        return frozenset(
            values
        )

    @staticmethod
    def _configuration_selects_apex(
        configuration,
        apex_requirement,
    ) -> bool:
        return any(
            selection.resolved
            and selection.candidates[0]
            is apex_requirement
            for selection
            in configuration.apex_selections
        )

    @classmethod
    def classify(
        cls,
        *,
        avf_requirement: (
            AndroidUniverseAvfRequirement
            | None
        ),
        loading_contexts: tuple[
            AndroidUniverseLinkerExecutableLoadingContext,
            ...,
        ],
        candidates: tuple[
            AndroidRuntimeLinkerElfRuntimeCandidate,
            ...,
        ],
    ) -> dict[
        str,
        str,
    ]:
        if avf_requirement is None:
            return {}

        if not isinstance(
            avf_requirement,
            AndroidUniverseAvfRequirement,
        ):
            raise TypeError(
                "avf_requirement must be an "
                "AndroidUniverseAvfRequirement or None"
            )

        if not isinstance(
            loading_contexts,
            tuple,
        ):
            raise TypeError(
                "loading_contexts must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseLinkerExecutableLoadingContext,
            )
            for value
            in loading_contexts
        ):
            raise TypeError(
                "loading_contexts contains an invalid value"
            )

        if not isinstance(
            candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidRuntimeLinkerElfRuntimeCandidate,
            )
            for value
            in candidates
        ):
            raise TypeError(
                "candidates contains an invalid value"
            )

        candidate_by_context_identity = {
            id(
                candidate.linker_elf_context
            ): candidate
            for candidate
            in candidates
        }

        if len(
            candidate_by_context_identity
        ) != len(
            candidates
        ):
            raise ValueError(
                "candidate population must preserve unique "
                "Linker/ELF context identity"
            )

        active_candidates = tuple(
            candidate
            for candidate
            in candidates
            if (
                candidate.status
                is AndroidRuntimeLinkerElfRuntimeCandidateStatus
                .ACTIVE
            )
        )

        candidate_names = {
            id(candidate): (
                cls._candidate_names(
                    candidate
                )
            )
            for candidate
            in active_candidates
        }

        results = {}

        for loading_context in (
            loading_contexts
        ):
            if (
                loading_context.status
                not in {
                    AndroidUniverseLinkerExecutableLoadingContextStatus
                    .RESOLVED,
                    AndroidUniverseLinkerExecutableLoadingContextStatus
                    .DEFAULT_FALLBACK,
                }
            ):
                continue

            elf_context = (
                loading_context
                .routing
                .elf_context
            )

            root_candidate = (
                candidate_by_context_identity
                .get(
                    id(
                        elf_context
                    )
                )
            )

            if (
                root_candidate is None
                or root_candidate.status
                is not (
                    AndroidRuntimeLinkerElfRuntimeCandidateStatus
                    .ACTIVE
                )
            ):
                continue

            selected_apex = (
                elf_context
                .selected_apex_requirement
            )

            if selected_apex is None:
                continue

            configurations = tuple(
                configuration
                for configuration
                in avf_requirement.configurations
                if cls._configuration_selects_apex(
                    configuration,
                    selected_apex,
                )
            )

            if not configurations:
                continue

            #
            # Direct AVF task declaration.
            #
            if (
                root_candidate.runtime_path
                is not None
                and any(
                    configuration.task_type
                    == "executable"
                    and configuration.task_command
                    == (
                        root_candidate
                        .runtime_path
                        .as_posix()
                    )
                    for configuration
                    in configurations
                )
            ):
                results[
                    elf_context.context_id
                ] = (
                    cls.DIRECT_TASK_REASON
                )

                continue

            #
            # Companion executable in an AVF-selected APEX:
            #
            # A required provider exists, but only in another exact canonical
            # Android runtime. Do not pretend that the host namespace should
            # resolve across that runtime boundary.
            #
            distinct_runtime_dependencies = []

            for dependency in (
                root_candidate
                .elf_requirement
                .dependencies
            ):
                providers = tuple(
                    candidate
                    for candidate
                    in active_candidates
                    if (
                        candidate
                        is not root_candidate
                        and candidate.bitness
                        == root_candidate.bitness
                        and dependency.name
                        in candidate_names[
                            id(candidate)
                        ]
                    )
                )

                if not providers:
                    continue

                same_runtime = tuple(
                    provider
                    for provider
                    in providers
                    if (
                        provider
                        .linker_elf_context
                        .shares_runtime(
                            elf_context.runtime_context
                        )
                    )
                )

                if same_runtime:
                    continue

                distinct_runtime_dependencies.append(
                    dependency.name
                )

            if not distinct_runtime_dependencies:
                continue

            names = ", ".join(
                sorted(
                    set(
                        distinct_runtime_dependencies
                    )
                )
            )

            results[
                elf_context.context_id
            ] = (
                cls.DISTINCT_RUNTIME_REASON_PREFIX
                + ": "
                + names
            )

        return results
