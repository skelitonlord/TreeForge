"""
Contextual Android ELF DT_NEEDED resolution.

This module consumes already-derived Runtime Linking state:

- canonical ELF dependency requirements;
- runtime ELF candidates;
- executable starting loading contexts;
- post-AddStandardSystemLinks namespace accessibility;
- effective namespace search-path policy.

It deliberately performs no filesystem reads and no Reconstruction work.

For one DT_NEEDED lookup the semantic order is:

    starting namespace
        ->
    starting namespace search paths, in order
        ->
    direct linked namespaces admitting the requested name,
        in exact link order
        ->
    each target namespace's own search paths, in order

The lookup is intentionally one-hop. It never recursively traverses namespace
links for the same dependency lookup.

When a dependency resolves in namespace B, that provider ELF's own DT_NEEDED
requirements begin from B. This reproduces the important bionic distinction
between namespace-link accessibility and dependency-chain propagation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.runtime_linking.linker.elf_runtime_candidate import (
    AndroidRuntimeLinkerElfRuntimeCandidate,
    AndroidRuntimeLinkerElfRuntimeCandidateStatus,
)
from treeforge.android.runtime_linking.linker.expression_resolution import (
    AndroidRuntimeLinkerVariableEnvironment,
)
from treeforge.android.runtime_linking.linker.namespace_accessibility import (
    AndroidRuntimeLinkerNamespaceAccessibility,
    AndroidRuntimeLinkerSectionAccessibility,
)
from treeforge.android.runtime_linking.linker.namespace_lookup import (
    AndroidRuntimeLinkerNamespaceLookupPolicy,
    AndroidRuntimeLinkerNamespaceLookupPolicyBuilder,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfDependencyRequirement,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContext,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerExecutableLoadingContext,
)


class AndroidRuntimeLinkerElfDependencyResolutionStatus(
    StrEnum,
):
    """
    Contextual resolution state for one canonical DT_NEEDED requirement.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class AndroidRuntimeLinkerElfDependencyProviderPathKind(
    StrEnum,
):
    """
    Which canonical runtime path identity satisfied a lookup.
    """

    PHYSICAL = "physical"
    FILESYSTEM_ALIAS = "filesystem_alias"


class AndroidRuntimeLinkerElfDependencyTraversalStatus(
    StrEnum,
):
    """
    Contextual dependency-traversal state for one loading-context conclusion.
    """

    RESOLVED = "resolved"
    INAPPLICABLE = "inapplicable"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerElfDependencyResolution:
    """
    Contextual resolution of one exact canonical DT_NEEDED requirement.

    ``parent_candidate`` is the exact runtime ELF whose dependency is being
    resolved.

    ``starting_namespace_name`` is the namespace in which the parent was
    loaded. A resolved provider's child dependencies therefore start from
    ``provider_namespace_name``.

    ``searched_namespace_names`` preserves the actual one-hop Bionic lookup
    order attempted for this dependency.
    """

    dependency: AndroidUniverseElfDependencyRequirement

    parent_candidate: AndroidRuntimeLinkerElfRuntimeCandidate

    starting_namespace_name: str

    searched_namespace_names: tuple[
        str,
        ...,
    ]

    provider_candidate: (
        AndroidRuntimeLinkerElfRuntimeCandidate
        | None
    )

    provider_namespace_name: str | None

    provider_runtime_path: PurePosixPath | None

    provider_path_kind: (
        AndroidRuntimeLinkerElfDependencyProviderPathKind
        | None
    )

    status: AndroidRuntimeLinkerElfDependencyResolutionStatus

    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.dependency,
            AndroidUniverseElfDependencyRequirement,
        ):
            raise TypeError(
                "dependency must be an "
                "AndroidUniverseElfDependencyRequirement"
            )

        if not isinstance(
            self.parent_candidate,
            AndroidRuntimeLinkerElfRuntimeCandidate,
        ):
            raise TypeError(
                "parent_candidate must be an "
                "AndroidRuntimeLinkerElfRuntimeCandidate"
            )

        if (
            not self.parent_candidate.elf_requirement.owns_dependency(self.dependency)
        ):
            raise ValueError(
                "dependency must preserve exact canonical parent ELF "
                "identity"
            )

        if (
            not isinstance(
                self.starting_namespace_name,
                str,
            )
            or not self.starting_namespace_name
        ):
            raise ValueError(
                "starting_namespace_name must be non-empty"
            )

        if not isinstance(
            self.searched_namespace_names,
            tuple,
        ):
            raise TypeError(
                "searched_namespace_names must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            for value
            in self.searched_namespace_names
        ):
            raise ValueError(
                "searched_namespace_names must contain non-empty strings"
            )

        if not self.searched_namespace_names:
            raise ValueError(
                "dependency resolution must preserve at least one "
                "searched namespace"
            )

        if (
            self.searched_namespace_names[
                0
            ]
            != self.starting_namespace_name
        ):
            raise ValueError(
                "current namespace must be searched first"
            )

        if (
            self.provider_candidate
            is not None
            and not isinstance(
                self.provider_candidate,
                AndroidRuntimeLinkerElfRuntimeCandidate,
            )
        ):
            raise TypeError(
                "provider_candidate has invalid type"
            )

        if (
            self.provider_namespace_name
            is not None
            and (
                not isinstance(
                    self.provider_namespace_name,
                    str,
                )
                or not self.provider_namespace_name
            )
        ):
            raise ValueError(
                "provider_namespace_name must be non-empty or None"
            )

        if (
            self.provider_runtime_path
            is not None
            and (
                not isinstance(
                    self.provider_runtime_path,
                    PurePosixPath,
                )
                or not self.provider_runtime_path.is_absolute()
            )
        ):
            raise ValueError(
                "provider_runtime_path must be an absolute "
                "PurePosixPath or None"
            )

        if (
            self.provider_path_kind
            is not None
            and not isinstance(
                self.provider_path_kind,
                AndroidRuntimeLinkerElfDependencyProviderPathKind,
            )
        ):
            raise TypeError(
                "provider_path_kind has invalid type"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerElfDependencyResolutionStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if (
            self.status
            is AndroidRuntimeLinkerElfDependencyResolutionStatus.RESOLVED
        ):
            if (
                self.provider_candidate is None
                or self.provider_namespace_name is None
                or self.provider_runtime_path is None
                or self.provider_path_kind is None
            ):
                raise ValueError(
                    "resolved dependency requires complete provider identity"
                )

            if (
                self.provider_candidate.status
                is not AndroidRuntimeLinkerElfRuntimeCandidateStatus.ACTIVE
            ):
                raise ValueError(
                    "resolved dependency provider must be ACTIVE"
                )

            if (
                self.provider_candidate.bitness
                != self.parent_candidate.bitness
            ):
                raise ValueError(
                    "resolved dependency must preserve parent ELF bitness"
                )

            if self.reason is not None:
                raise ValueError(
                    "resolved dependency must not carry a reason"
                )

        else:
            if (
                self.provider_candidate is not None
                or self.provider_namespace_name is not None
                or self.provider_runtime_path is not None
                or self.provider_path_kind is not None
            ):
                raise ValueError(
                    "non-resolved dependency must not select a provider"
                )

            if (
                not isinstance(
                    self.reason,
                    str,
                )
                or not self.reason
            ):
                raise ValueError(
                    "non-resolved dependency requires a reason"
                )

    @property
    def resolution_id(
        self,
    ) -> str:
        return (
            "runtime-linker-elf-needed:"
            f"{self.parent_candidate.candidate_id}:"
            f"{self.starting_namespace_name}:"
            f"{self.dependency.name}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerElfDependencyTraversal:
    """
    Complete contextual DT_NEEDED traversal rooted at one exact loading context.

    Shared-object loading contexts remain INAPPLICABLE at the root layer. They
    become contextual only when reached from a resolved parent dependency.
    """

    loading_context: AndroidUniverseLinkerExecutableLoadingContext

    root_candidate: (
        AndroidRuntimeLinkerElfRuntimeCandidate
        | None
    )

    section_accessibility: (
        AndroidRuntimeLinkerSectionAccessibility
        | None
    )

    starting_namespace_name: str | None

    dependency_resolutions: tuple[
        AndroidRuntimeLinkerElfDependencyResolution,
        ...,
    ]

    visited_elf_namespace_states: int

    status: AndroidRuntimeLinkerElfDependencyTraversalStatus

    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.loading_context,
            AndroidUniverseLinkerExecutableLoadingContext,
        ):
            raise TypeError(
                "loading_context has invalid type"
            )

        if (
            self.root_candidate is not None
            and not isinstance(
                self.root_candidate,
                AndroidRuntimeLinkerElfRuntimeCandidate,
            )
        ):
            raise TypeError(
                "root_candidate has invalid type"
            )

        if (
            self.section_accessibility is not None
            and not isinstance(
                self.section_accessibility,
                AndroidRuntimeLinkerSectionAccessibility,
            )
        ):
            raise TypeError(
                "section_accessibility has invalid type"
            )

        if (
            self.starting_namespace_name
            is not None
            and (
                not isinstance(
                    self.starting_namespace_name,
                    str,
                )
                or not self.starting_namespace_name
            )
        ):
            raise ValueError(
                "starting_namespace_name must be non-empty or None"
            )

        if not isinstance(
            self.dependency_resolutions,
            tuple,
        ):
            raise TypeError(
                "dependency_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidRuntimeLinkerElfDependencyResolution,
            )
            for item
            in self.dependency_resolutions
        ):
            raise TypeError(
                "dependency_resolutions contains invalid values"
            )

        if (
            not isinstance(
                self.visited_elf_namespace_states,
                int,
            )
            or self.visited_elf_namespace_states < 0
        ):
            raise ValueError(
                "visited_elf_namespace_states must be non-negative"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerElfDependencyTraversalStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if (
            self.status
            is AndroidRuntimeLinkerElfDependencyTraversalStatus.RESOLVED
        ):
            if (
                self.root_candidate is None
                or self.section_accessibility is None
                or self.starting_namespace_name is None
            ):
                raise ValueError(
                    "resolved traversal requires root runtime context"
                )

            if self.reason is not None:
                raise ValueError(
                    "resolved traversal must not carry a reason"
                )

        elif (
            not isinstance(
                self.reason,
                str,
            )
            or not self.reason
        ):
            raise ValueError(
                "non-resolved traversal requires a reason"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class _CandidatePathMatch:
    candidate: AndroidRuntimeLinkerElfRuntimeCandidate
    path: PurePosixPath
    path_kind: AndroidRuntimeLinkerElfDependencyProviderPathKind

    @property
    def diagnostic_identity(
        self,
    ) -> str:
        source_identity = self.candidate.elf_requirement.identity_key

        return (
            f"{self.path_kind.value}:"
            f"{source_identity!r}:"
            f"runtime={self.path.as_posix()}"
        )


class AndroidRuntimeLinkerContextualElfDependencyResolver:
    """
    Resolve complete contextual ELF dependency chains for one linker section.
    """

    @staticmethod
    def _candidate_paths(
        candidate: AndroidRuntimeLinkerElfRuntimeCandidate,
    ) -> tuple[
        tuple[
            PurePosixPath,
            AndroidRuntimeLinkerElfDependencyProviderPathKind,
        ],
        ...,
    ]:
        if (
            candidate.status
            is not AndroidRuntimeLinkerElfRuntimeCandidateStatus.ACTIVE
        ):
            return ()

        if candidate.runtime_path is None:
            raise ValueError(
                "ACTIVE runtime candidate must preserve runtime_path"
            )

        values = [
            (
                candidate.runtime_path,
                AndroidRuntimeLinkerElfDependencyProviderPathKind.PHYSICAL,
            ),
        ]

        values.extend(
            (
                alias,
                (
                    AndroidRuntimeLinkerElfDependencyProviderPathKind
                    .FILESYSTEM_ALIAS
                ),
            )
            for alias
            in candidate.runtime_alias_paths
        )

        return tuple(
            values
        )

    @classmethod
    def _index_candidates(
        cls,
        *,
        candidates: tuple[
            AndroidRuntimeLinkerElfRuntimeCandidate,
            ...,
        ],
        bitness: int,
        runtime_context: AndroidUniverseRuntimeContext,
    ) -> dict[
        PurePosixPath,
        tuple[
            _CandidatePathMatch,
            ...,
        ],
    ]:
        working: dict[
            PurePosixPath,
            list[
                _CandidatePathMatch
            ],
        ] = {}

        for candidate in candidates:
            if (
                candidate.status
                is not AndroidRuntimeLinkerElfRuntimeCandidateStatus.ACTIVE
            ):
                continue

            if candidate.bitness != bitness:
                continue

            if not (
                candidate.linker_elf_context.shares_runtime(runtime_context)
            ):
                continue

            for path, path_kind in cls._candidate_paths(
                candidate
            ):
                working.setdefault(
                    path,
                    [],
                ).append(
                    _CandidatePathMatch(
                        candidate=candidate,
                        path=path,
                        path_kind=path_kind,
                    )
                )

        return {
            path: tuple(
                values
            )
            for path, values
            in working.items()
        }

    @staticmethod
    def _namespace_policy(
        *,
        accessibility: AndroidRuntimeLinkerNamespaceAccessibility,
        bitness: int,
        environment: AndroidRuntimeLinkerVariableEnvironment,
    ) -> AndroidRuntimeLinkerNamespaceLookupPolicy:
        return (
            AndroidRuntimeLinkerNamespaceLookupPolicyBuilder
            .build(
                namespace=(
                    accessibility
                    .namespace
                    .namespace
                ),
                bitness=bitness,
                environment=environment,
            )
        )

    @classmethod
    def _search_namespace(
        cls,
        *,
        accessibility: AndroidRuntimeLinkerNamespaceAccessibility,
        dependency_name: str,
        bitness: int,
        environment: AndroidRuntimeLinkerVariableEnvironment,
        candidate_index: dict[
            PurePosixPath,
            tuple[
                _CandidatePathMatch,
                ...,
            ],
        ],
    ) -> tuple[
        _CandidatePathMatch,
        ...,
    ]:
        policy = cls._namespace_policy(
            accessibility=accessibility,
            bitness=bitness,
            environment=environment,
        )

        if not policy.admits_library(
            dependency_name
        ):
            return ()

        for directory in policy.search_paths:
            requested_path = (
                directory
                / dependency_name
            )

            matches = (
                candidate_index.get(
                    requested_path,
                    (),
                )
            )

            if matches:
                #
                # Filesystem search order selects the first search directory
                # containing the requested filename. Multiple canonical ELFs
                # at that exact runtime path represent model ambiguity rather
                # than permission to continue to a later directory.
                #
                return matches

        return ()

    @classmethod
    def _resolve_one(
        cls,
        *,
        parent_candidate: AndroidRuntimeLinkerElfRuntimeCandidate,
        dependency: AndroidUniverseElfDependencyRequirement,
        starting_namespace: AndroidRuntimeLinkerNamespaceAccessibility,
        section_accessibility: AndroidRuntimeLinkerSectionAccessibility,
        environment: AndroidRuntimeLinkerVariableEnvironment,
        candidate_index: dict[
            PurePosixPath,
            tuple[
                _CandidatePathMatch,
                ...,
            ],
        ],
    ) -> AndroidRuntimeLinkerElfDependencyResolution:
        dependency_name = (
            dependency.name
        )

        searched_namespace_names = [
            (
                starting_namespace
                .namespace
                .namespace
                .name
            )
        ]

        matches = cls._search_namespace(
            accessibility=starting_namespace,
            dependency_name=dependency_name,
            bitness=parent_candidate.bitness,
            environment=environment,
            candidate_index=candidate_index,
        )

        if matches:
            if len(matches) == 1:
                match = matches[0]

                return (
                    AndroidRuntimeLinkerElfDependencyResolution(
                        dependency=dependency,
                        parent_candidate=parent_candidate,
                        starting_namespace_name=(
                            searched_namespace_names[
                                0
                            ]
                        ),
                        searched_namespace_names=tuple(
                            searched_namespace_names
                        ),
                        provider_candidate=(
                            match.candidate
                        ),
                        provider_namespace_name=(
                            searched_namespace_names[
                                0
                            ]
                        ),
                        provider_runtime_path=(
                            match.path
                        ),
                        provider_path_kind=(
                            match.path_kind
                        ),
                        status=(
                            AndroidRuntimeLinkerElfDependencyResolutionStatus
                            .RESOLVED
                        ),
                    )
                )

            return (
                AndroidRuntimeLinkerElfDependencyResolution(
                    dependency=dependency,
                    parent_candidate=parent_candidate,
                    starting_namespace_name=(
                        searched_namespace_names[
                            0
                        ]
                    ),
                    searched_namespace_names=tuple(
                        searched_namespace_names
                    ),
                    provider_candidate=None,
                    provider_namespace_name=None,
                    provider_runtime_path=None,
                    provider_path_kind=None,
                    status=(
                        AndroidRuntimeLinkerElfDependencyResolutionStatus
                        .AMBIGUOUS
                    ),
                    reason=(
                        "multiple canonical active ELF candidates occupy "
                        "the first matching runtime path in the starting "
                        "namespace: "
                        + " | ".join(
                            match.diagnostic_identity
                            for match
                            in matches
                        )
                    ),
                )
            )

        for link in starting_namespace.links_admitting(
            dependency_name
        ):
            target_name = (
                link.target_namespace_name
            )

            searched_namespace_names.append(
                target_name
            )

            target = (
                section_accessibility
                .namespace(
                    target_name
                )
            )

            if target is None:
                #
                # Android linkerconfig may emit a named link target without
                # materializing that namespace in the same section. Preserve
                # the edge identity and lookup order, but do not invent target
                # search-path policy that the generated section does not
                # contain.
                #
                continue

            matches = cls._search_namespace(
                accessibility=target,
                dependency_name=dependency_name,
                bitness=parent_candidate.bitness,
                environment=environment,
                candidate_index=candidate_index,
            )

            if not matches:
                continue

            if len(matches) == 1:
                match = matches[0]

                return (
                    AndroidRuntimeLinkerElfDependencyResolution(
                        dependency=dependency,
                        parent_candidate=parent_candidate,
                        starting_namespace_name=(
                            searched_namespace_names[
                                0
                            ]
                        ),
                        searched_namespace_names=tuple(
                            searched_namespace_names
                        ),
                        provider_candidate=(
                            match.candidate
                        ),
                        provider_namespace_name=(
                            target_name
                        ),
                        provider_runtime_path=(
                            match.path
                        ),
                        provider_path_kind=(
                            match.path_kind
                        ),
                        status=(
                            AndroidRuntimeLinkerElfDependencyResolutionStatus
                            .RESOLVED
                        ),
                    )
                )

            return (
                AndroidRuntimeLinkerElfDependencyResolution(
                    dependency=dependency,
                    parent_candidate=parent_candidate,
                    starting_namespace_name=(
                        searched_namespace_names[
                            0
                        ]
                    ),
                    searched_namespace_names=tuple(
                        searched_namespace_names
                    ),
                    provider_candidate=None,
                    provider_namespace_name=None,
                    provider_runtime_path=None,
                    provider_path_kind=None,
                    status=(
                        AndroidRuntimeLinkerElfDependencyResolutionStatus
                        .AMBIGUOUS
                    ),
                    reason=(
                        "multiple canonical active ELF candidates occupy "
                        "the first matching runtime path in an accessible "
                        f"namespace {target_name!r}: "
                        + " | ".join(
                            match.diagnostic_identity
                            for match
                            in matches
                        )
                    ),
                )
            )

        return (
            AndroidRuntimeLinkerElfDependencyResolution(
                dependency=dependency,
                parent_candidate=parent_candidate,
                starting_namespace_name=(
                    searched_namespace_names[
                        0
                    ]
                ),
                searched_namespace_names=tuple(
                    searched_namespace_names
                ),
                provider_candidate=None,
                provider_namespace_name=None,
                provider_runtime_path=None,
                provider_path_kind=None,
                status=(
                    AndroidRuntimeLinkerElfDependencyResolutionStatus
                    .UNRESOLVED
                ),
                reason=(
                    "requested DT_NEEDED filename is absent from the "
                    "starting namespace and every directly linked namespace "
                    "that admits it"
                ),
            )
        )

    @classmethod
    def resolve(
        cls,
        *,
        loading_context: AndroidUniverseLinkerExecutableLoadingContext,
        root_candidate: AndroidRuntimeLinkerElfRuntimeCandidate,
        section_accessibility: AndroidRuntimeLinkerSectionAccessibility,
        environment: AndroidRuntimeLinkerVariableEnvironment,
        candidates: tuple[
            AndroidRuntimeLinkerElfRuntimeCandidate,
            ...,
        ],
    ) -> AndroidRuntimeLinkerElfDependencyTraversal:
        """
        Resolve one complete dependency traversal from one executable root.

        A visited state is identified by:

            exact canonical ELF requirement identity
            +
            provider namespace name

        This prevents dependency cycles from causing recursive expansion while
        still allowing the same ELF to be resolved independently in distinct
        namespaces.
        """

        if not isinstance(
            loading_context,
            AndroidUniverseLinkerExecutableLoadingContext,
        ):
            raise TypeError(
                "loading_context has invalid type"
            )

        if not isinstance(
            root_candidate,
            AndroidRuntimeLinkerElfRuntimeCandidate,
        ):
            raise TypeError(
                "root_candidate has invalid type"
            )

        if (
            root_candidate.status
            is not AndroidRuntimeLinkerElfRuntimeCandidateStatus.ACTIVE
        ):
            raise ValueError(
                "contextual dependency traversal requires ACTIVE root ELF"
            )

        if not isinstance(
            section_accessibility,
            AndroidRuntimeLinkerSectionAccessibility,
        ):
            raise TypeError(
                "section_accessibility has invalid type"
            )

        if not isinstance(
            environment,
            AndroidRuntimeLinkerVariableEnvironment,
        ):
            raise TypeError(
                "environment has invalid type"
            )

        if not isinstance(
            candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        namespace_name = (
            loading_context.namespace_name
        )

        if namespace_name is None:
            raise ValueError(
                "resolved loading context must preserve namespace_name"
            )

        starting_namespace = (
            section_accessibility
            .namespace(
                namespace_name
            )
        )

        if starting_namespace is None:
            raise ValueError(
                "starting loading namespace is absent from selected "
                f"section: {namespace_name!r}"
            )

        candidate_index = cls._index_candidates(
            candidates=candidates,
            bitness=root_candidate.bitness,
            runtime_context=(
                root_candidate
                .linker_elf_context
                .runtime_context
            ),
        )

        queue = [
            (
                root_candidate,
                namespace_name,
            ),
        ]

        visited: set[
            tuple[
                int,
                str,
            ]
        ] = set()

        resolutions = []

        while queue:
            (
                parent_candidate,
                parent_namespace_name,
            ) = queue.pop(
                0
            )

            state = (
                id(
                    parent_candidate
                    .elf_requirement
                ),
                parent_namespace_name,
            )

            if state in visited:
                continue

            visited.add(
                state
            )

            parent_namespace = (
                section_accessibility
                .namespace(
                    parent_namespace_name
                )
            )

            if parent_namespace is None:
                raise ValueError(
                    "dependency-chain provider namespace is absent "
                    "from selected section: "
                    f"{parent_namespace_name!r}"
                )

            for dependency in (
                parent_candidate
                .elf_requirement
                .dependencies
            ):
                resolution = cls._resolve_one(
                    parent_candidate=parent_candidate,
                    dependency=dependency,
                    starting_namespace=parent_namespace,
                    section_accessibility=section_accessibility,
                    environment=environment,
                    candidate_index=candidate_index,
                )

                resolutions.append(
                    resolution
                )

                if (
                    resolution.status
                    is not AndroidRuntimeLinkerElfDependencyResolutionStatus
                    .RESOLVED
                ):
                    continue

                provider = (
                    resolution.provider_candidate
                )

                provider_namespace = (
                    resolution.provider_namespace_name
                )

                assert provider is not None
                assert provider_namespace is not None

                queue.append(
                    (
                        provider,
                        provider_namespace,
                    )
                )

        result = tuple(
            resolutions
        )

        if any(
            resolution.status
            is AndroidRuntimeLinkerElfDependencyResolutionStatus.AMBIGUOUS
            for resolution
            in result
        ):
            traversal_status = (
                AndroidRuntimeLinkerElfDependencyTraversalStatus
                .AMBIGUOUS
            )

            reason = (
                "one or more contextual DT_NEEDED requirements are ambiguous"
            )

        elif any(
            resolution.status
            is AndroidRuntimeLinkerElfDependencyResolutionStatus.UNRESOLVED
            for resolution
            in result
        ):
            traversal_status = (
                AndroidRuntimeLinkerElfDependencyTraversalStatus
                .UNRESOLVED
            )

            reason = (
                "one or more contextual DT_NEEDED requirements are unresolved"
            )

        else:
            traversal_status = (
                AndroidRuntimeLinkerElfDependencyTraversalStatus
                .RESOLVED
            )

            reason = None

        return (
            AndroidRuntimeLinkerElfDependencyTraversal(
                loading_context=loading_context,
                root_candidate=root_candidate,
                section_accessibility=section_accessibility,
                starting_namespace_name=namespace_name,
                dependency_resolutions=result,
                visited_elf_namespace_states=len(
                    visited
                ),
                status=traversal_status,
                reason=reason,
            )
        )
