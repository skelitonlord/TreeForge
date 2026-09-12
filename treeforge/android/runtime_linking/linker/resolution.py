"""
Android linkerconfig Section::Resolve() semantics.

This module consumes one already-constructed effective section and reproduces
the runtime namespace/provider resolution algorithm:

    existing namespace providers
        -> active APEX providers
        -> section-local LibProviders
        -> dynamic namespace injection
        -> process appended namespaces
        -> final default-first/name ordering

It deliberately stops before AddStandardSystemLinks(), namespace
reachability, ELF DT_NEEDED resolution, Reconstruction Ownership, Planning,
or materialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.runtime_linking.linker.effective_configuration import (
    AndroidRuntimeLinkerConstructedNamespace,
    AndroidRuntimeLinkerEffectiveNamespace,
)
from treeforge.android.runtime_linking.linker.expression import (
    AndroidRuntimeLinkerLibraryExpression,
    literal_library,
)
from treeforge.android.runtime_linking.linker.expression_resolution import (
    AndroidRuntimeLinkerExpressionResolver,
    AndroidRuntimeLinkerVariableEnvironment,
)
from treeforge.android.runtime_linking.linker.provider import (
    AndroidRuntimeLinkerAliasLinkModifierKind,
    AndroidRuntimeLinkerAliasProvider,
    AndroidRuntimeLinkerApexLibraryProvider,
    AndroidRuntimeLinkerConcreteLibraryProvider,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexProviderDescriptor,
)


class AndroidRuntimeLinkerResolutionStatus(
    StrEnum
):
    RESOLVED = "resolved"
    TOLERATED_MISSING = "tolerated_missing"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class AndroidRuntimeLinkerResolvedProviderKind(
    StrEnum
):
    CONCRETE_NAMESPACE = "concrete_namespace"
    APEX = "apex"
    ALIAS = "alias"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerResolvedNamespaceLink:
    """
    Final accumulated link from one namespace to one target namespace.

    Android Namespace::GetLink() reuses an existing link for a target, so
    provider resolution augments an existing target link rather than creating
    duplicate target-link objects.
    """

    source_namespace: str
    target_namespace: str

    shared_libraries: tuple[
        str,
        ...,
    ] = ()

    allow_all_shared_libs: bool = False

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "source_namespace",
            "target_namespace",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.shared_libraries,
            tuple,
        ):
            raise TypeError(
                "shared_libraries must be a tuple"
            )

        if not all(
            isinstance(
                library,
                str,
            )
            and library
            for library
            in self.shared_libraries
        ):
            raise ValueError(
                "shared_libraries must contain non-empty strings"
            )

        if not isinstance(
            self.allow_all_shared_libs,
            bool,
        ):
            raise TypeError(
                "allow_all_shared_libs must be a bool"
            )

        if (
            self.allow_all_shared_libs
            and self.shared_libraries
        ):
            raise ValueError(
                "allow-all link cannot also carry restricted libraries"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerRequirementResolution:
    """
    Resolution of one concrete library/provider-alias requirement.
    """

    source_namespace: AndroidRuntimeLinkerEffectiveNamespace

    library_name: str

    provider_kind: (
        AndroidRuntimeLinkerResolvedProviderKind
        | None
    )

    target_namespace: str | None

    apex_provider: (
        AndroidUniverseLinkerApexProviderDescriptor
        | None
    ) = None

    alias_provider: (
        AndroidRuntimeLinkerAliasProvider
        | None
    ) = None

    status: AndroidRuntimeLinkerResolutionStatus = (
        AndroidRuntimeLinkerResolutionStatus.RESOLVED
    )

    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_namespace,
            AndroidRuntimeLinkerEffectiveNamespace,
        ):
            raise TypeError(
                "source_namespace has invalid type"
            )

        if (
            not isinstance(
                self.library_name,
                str,
            )
            or not self.library_name
        ):
            raise ValueError(
                "library_name must be a non-empty string"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerResolutionStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if (
            self.status
            is AndroidRuntimeLinkerResolutionStatus.RESOLVED
            and (
                self.provider_kind is None
                or self.target_namespace is None
            )
        ):
            raise ValueError(
                "resolved requirement requires provider and target namespace"
            )

        if (
            self.status
            is AndroidRuntimeLinkerResolutionStatus.TOLERATED_MISSING
            and (
                self.provider_kind is not None
                or self.target_namespace is not None
                or self.apex_provider is not None
                or self.alias_provider is not None
            )
        ):
            raise ValueError(
                "tolerated missing requirement must not claim a provider"
            )

        if (
            self.status
            is not AndroidRuntimeLinkerResolutionStatus.RESOLVED
            and not self.reason
        ):
            raise ValueError(
                "non-resolved requirement must explain why"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerResolvedNamespace:
    """
    One namespace after Section::Resolve().
    """

    namespace: AndroidRuntimeLinkerEffectiveNamespace

    links: tuple[
        AndroidRuntimeLinkerResolvedNamespaceLink,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.namespace,
            AndroidRuntimeLinkerEffectiveNamespace,
        ):
            raise TypeError(
                "namespace has invalid type"
            )

        if not isinstance(
            self.links,
            tuple,
        ):
            raise TypeError(
                "links must be a tuple"
            )

        targets = tuple(
            link.target_namespace
            for link
            in self.links
        )

        if len(
            targets
        ) != len(
            set(
                targets
            )
        ):
            raise ValueError(
                "resolved namespace must contain one link per target"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerResolvedSection:
    """
    Result immediately after Section::Resolve() and before
    AddStandardSystemLinks().
    """

    section_name: str

    namespaces: tuple[
        AndroidRuntimeLinkerResolvedNamespace,
        ...,
    ]

    requirement_resolutions: tuple[
        AndroidRuntimeLinkerRequirementResolution,
        ...,
    ]

    status: AndroidRuntimeLinkerResolutionStatus

    reasons: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.section_name,
                str,
            )
            or not self.section_name
        ):
            raise ValueError(
                "section_name must be a non-empty string"
            )

        if not isinstance(
            self.namespaces,
            tuple,
        ):
            raise TypeError(
                "namespaces must be a tuple"
            )

        names = tuple(
            item.namespace.name
            for item
            in self.namespaces
        )

        if len(
            names
        ) != len(
            set(
                names
            )
        ):
            raise ValueError(
                "resolved namespace names must remain unique"
            )

        if names and names[
            0
        ] != "default":
            raise ValueError(
                "resolved section must sort default namespace first"
            )

        if names[
            1:
        ] != tuple(
            sorted(
                names[
                    1:
                ]
            )
        ):
            raise ValueError(
                "resolved namespaces after default must be lexical"
            )

        if not isinstance(
            self.requirement_resolutions,
            tuple,
        ):
            raise TypeError(
                "requirement_resolutions must be a tuple"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerResolutionStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if (
            self.status
            is AndroidRuntimeLinkerResolutionStatus.RESOLVED
            and self.reasons
        ):
            raise ValueError(
                "resolved section cannot carry failure reasons"
            )

        if (
            self.status
            is not AndroidRuntimeLinkerResolutionStatus.RESOLVED
            and not self.reasons
        ):
            raise ValueError(
                "non-resolved section must carry reasons"
            )


@dataclass
class _WorkingLink:
    target_namespace: str
    shared_libraries: list[str]
    allow_all_shared_libs: bool


@dataclass
class _WorkingNamespace:
    namespace: AndroidRuntimeLinkerEffectiveNamespace
    links: list[_WorkingLink]


class AndroidRuntimeLinkerSectionResolver:
    """
    Shared Android Section::Resolve() implementation.

    Callers supply the section-local alias-provider population. BASE vendor
    sections and APEX sections therefore share one resolver while retaining
    their distinct LibProviders contexts.
    """

    @staticmethod
    def _expressions(
        namespace: AndroidRuntimeLinkerEffectiveNamespace,
    ) -> tuple[
        AndroidRuntimeLinkerLibraryExpression,
        ...,
    ]:
        if namespace.generated_namespace is not None:
            return namespace.generated_namespace.requires

        if namespace.constructed_namespace is not None:
            return (
                namespace
                .constructed_namespace
                .required_libraries
            )

        if namespace.apex_provider is not None:
            return tuple(
                literal_library(
                    library_name
                )
                for library_name
                in namespace.apex_provider.required_libraries
            )

        raise AssertionError(
            "effective namespace has no primary origin"
        )

    @staticmethod
    def _link_intents(
        namespace: AndroidRuntimeLinkerEffectiveNamespace,
    ):
        if namespace.generated_namespace is not None:
            return namespace.generated_namespace.link_intents

        if namespace.constructed_namespace is not None:
            return namespace.constructed_namespace.link_intents

        # BuildApexNamespace() starts without links; requirements create them
        # during Section::Resolve().
        return ()

    @staticmethod
    def _provided_library_names(
        namespace: AndroidRuntimeLinkerEffectiveNamespace,
    ) -> tuple[
        str,
        ...,
    ]:
        if namespace.generated_namespace is not None:
            return tuple(
                expression.library_name
                for expression
                in namespace.generated_namespace.provides
                if expression.library_name is not None
            )

        if namespace.constructed_namespace is not None:
            return tuple(
                expression.library_name
                for expression
                in (
                    namespace
                    .constructed_namespace
                    .provided_libraries
                )
                if expression.library_name is not None
            )

        if namespace.apex_provider is not None:
            return namespace.apex_provider.provided_libraries

        raise AssertionError(
            "effective namespace has no primary origin"
        )

    @staticmethod
    def _get_link(
        *,
        working: _WorkingNamespace,
        target_namespace: str,
    ) -> _WorkingLink:
        for link in working.links:
            if link.target_namespace == target_namespace:
                return link

        link = _WorkingLink(
            target_namespace=target_namespace,
            shared_libraries=[],
            allow_all_shared_libs=False,
        )

        working.links.append(
            link
        )

        return link

    @classmethod
    def _initial_links(
        cls,
        *,
        namespace: AndroidRuntimeLinkerEffectiveNamespace,
        environment: AndroidRuntimeLinkerVariableEnvironment,
        unresolved_reasons: list[str],
    ) -> list[
        _WorkingLink
    ]:
        links = []

        working = _WorkingNamespace(
            namespace=namespace,
            links=links,
        )

        for intent in cls._link_intents(
            namespace
        ):
            link = cls._get_link(
                working=working,
                target_namespace=(
                    intent.target_namespace
                ),
            )

            if intent.allow_all_shared_libs:
                link.allow_all_shared_libs = True
                link.shared_libraries.clear()
                continue

            if link.allow_all_shared_libs:
                continue

            for expression in (
                intent.shared_libraries
            ):
                resolved = (
                    AndroidRuntimeLinkerExpressionResolver
                    .resolve(
                        expression=expression,
                        environment=environment,
                    )
                )

                if (
                    resolved.unresolved_variable
                    is not None
                ):
                    reason = (
                        f"namespace {namespace.name!r} link to "
                        f"{intent.target_namespace!r} requires undefined "
                        f"variable {resolved.unresolved_variable!r}"
                    )

                    if reason not in unresolved_reasons:
                        unresolved_reasons.append(
                            reason
                        )

                    continue

                for library_name in resolved.libraries:
                    if (
                        library_name
                        not in link.shared_libraries
                    ):
                        link.shared_libraries.append(
                            library_name
                        )

        return links

    @staticmethod
    def _index_concrete(
        providers: tuple[
            AndroidRuntimeLinkerConcreteLibraryProvider,
            ...,
        ],
    ) -> dict[
        str,
        tuple[
            AndroidRuntimeLinkerConcreteLibraryProvider,
            ...,
        ],
    ]:
        values = {}

        for provider in providers:
            values.setdefault(
                provider.library_name,
                [],
            ).append(
                provider
            )

        return {
            name: tuple(
                candidates
            )
            for name, candidates
            in values.items()
        }

    @staticmethod
    def _index_apex(
        providers: tuple[
            AndroidRuntimeLinkerApexLibraryProvider,
            ...,
        ],
    ) -> dict[
        str,
        tuple[
            AndroidRuntimeLinkerApexLibraryProvider,
            ...,
        ],
    ]:
        values = {}

        for provider in providers:
            values.setdefault(
                provider.library_name,
                [],
            ).append(
                provider
            )

        return {
            name: tuple(
                candidates
            )
            for name, candidates
            in values.items()
        }

    @staticmethod
    def _index_alias(
        providers: tuple[
            AndroidRuntimeLinkerAliasProvider,
            ...,
        ],
    ) -> dict[
        str,
        tuple[
            AndroidRuntimeLinkerAliasProvider,
            ...,
        ],
    ]:
        values = {}

        for provider in providers:
            values.setdefault(
                provider.alias,
                [],
            ).append(
                provider
            )

        return {
            name: tuple(
                candidates
            )
            for name, candidates
            in values.items()
        }

    @staticmethod
    def _should_fail_on_missing_deps(
        *,
        namespace_name: str,
        strict_mode: bool,
        target_apex: str | None,
    ) -> bool:
        """
        Reproduce modules/section.cc ShouldFailOnMissingDeps().

        Normal linkerconfig generation is non-strict. When --strict is used
        with --apex, only the default and target-APEX namespaces are strict.
        """

        if not strict_mode:
            return False

        if target_apex:
            return (
                namespace_name == "default"
                or namespace_name == target_apex
            )

        return True

    @classmethod
    def resolve(
        cls,
        *,
        section_name: str,
        namespaces: tuple[
            AndroidRuntimeLinkerEffectiveNamespace,
            ...,
        ],
        concrete_providers: tuple[
            AndroidRuntimeLinkerConcreteLibraryProvider,
            ...,
        ],
        apex_providers: tuple[
            AndroidRuntimeLinkerApexLibraryProvider,
            ...,
        ],
        alias_providers: tuple[
            AndroidRuntimeLinkerAliasProvider,
            ...,
        ],
        environment: AndroidRuntimeLinkerVariableEnvironment,
        strict_mode: bool = False,
        target_apex: str | None = None,
    ) -> AndroidRuntimeLinkerResolvedSection:
        """
        Reproduce Section::Resolve() provider ordering and dynamic expansion.

        Namespace iteration is index-based so namespaces appended while
        resolving requirements are themselves subsequently processed.
        """

        if not namespaces:
            raise ValueError(
                "Section::Resolve() requires at least one namespace"
            )

        if not isinstance(
            strict_mode,
            bool,
        ):
            raise TypeError(
                "strict_mode must be a bool"
            )

        if (
            target_apex is not None
            and (
                not isinstance(
                    target_apex,
                    str,
                )
                or not target_apex
            )
        ):
            raise ValueError(
                "target_apex must be a non-empty string or None"
            )

        unresolved_reasons = []
        ambiguous_reasons = []

        working = [
            _WorkingNamespace(
                namespace=namespace,
                links=cls._initial_links(
                    namespace=namespace,
                    environment=environment,
                    unresolved_reasons=(
                        unresolved_reasons
                    ),
                ),
            )
            for namespace
            in namespaces
        ]

        namespace_by_name = {
            item.namespace.name: item
            for item
            in working
        }

        if len(
            namespace_by_name
        ) != len(
            working
        ):
            raise ValueError(
                "pre-Resolve namespace names must be unique"
            )

        concrete_by_library = cls._index_concrete(
            concrete_providers
        )

        # Android treats duplicate initial concrete providers as fatal.
        duplicate_concrete = tuple(
            (
                library_name,
                candidates,
            )
            for library_name, candidates
            in concrete_by_library.items()
            if len(
                candidates
            ) > 1
        )

        if duplicate_concrete:
            names = ", ".join(
                sorted(
                    library_name
                    for library_name, _
                    in duplicate_concrete
                )
            )

            raise ValueError(
                "duplicate concrete namespace providers for: "
                f"{names}"
            )

        apex_by_library = cls._index_apex(
            apex_providers
        )

        alias_by_name = cls._index_alias(
            alias_providers
        )

        requirement_resolutions = []

        def add_namespace(
            namespace: AndroidRuntimeLinkerEffectiveNamespace,
        ) -> _WorkingNamespace:
            existing = namespace_by_name.get(
                namespace.name
            )

            if existing is not None:
                return existing

            item = _WorkingNamespace(
                namespace=namespace,
                links=cls._initial_links(
                    namespace=namespace,
                    environment=environment,
                    unresolved_reasons=(
                        unresolved_reasons
                    ),
                ),
            )

            working.append(
                item
            )

            namespace_by_name[
                namespace.name
            ] = item

            # Android add_namespace() adds newly introduced namespace
            # provides only when no provider already exists.
            for library_name in (
                cls._provided_library_names(
                    namespace
                )
            ):
                if library_name in concrete_by_library:
                    continue

                concrete_by_library[
                    library_name
                ] = (
                    AndroidRuntimeLinkerConcreteLibraryProvider(
                        library_name=library_name,
                        namespace=namespace,
                    ),
                )

            return item

        index = 0

        while index < len(
            working
        ):
            current = working[
                index
            ]

            index += 1

            for expression in cls._expressions(
                current.namespace
            ):
                resolved_expression = (
                    AndroidRuntimeLinkerExpressionResolver
                    .resolve(
                        expression=expression,
                        environment=environment,
                    )
                )

                if (
                    resolved_expression.unresolved_variable
                    is not None
                ):
                    reason = (
                        f"namespace {current.namespace.name!r} requires "
                        f"undefined variable "
                        f"{resolved_expression.unresolved_variable!r}"
                    )

                    if reason not in unresolved_reasons:
                        unresolved_reasons.append(
                            reason
                        )

                    continue

                for library_name in (
                    resolved_expression.libraries
                ):
                    concrete_candidates = (
                        concrete_by_library.get(
                            library_name,
                            (),
                        )
                    )

                    if concrete_candidates:
                        provider = (
                            concrete_candidates[
                                0
                            ]
                        )

                        target = (
                            provider.namespace.name
                        )

                        link = cls._get_link(
                            working=current,
                            target_namespace=target,
                        )

                        if not link.allow_all_shared_libs:
                            if (
                                library_name
                                not in link.shared_libraries
                            ):
                                link.shared_libraries.append(
                                    library_name
                                )

                        requirement_resolutions.append(
                            AndroidRuntimeLinkerRequirementResolution(
                                source_namespace=(
                                    current.namespace
                                ),
                                library_name=library_name,
                                provider_kind=(
                                    AndroidRuntimeLinkerResolvedProviderKind
                                    .CONCRETE_NAMESPACE
                                ),
                                target_namespace=target,
                            )
                        )

                        continue

                    apex_candidates = (
                        apex_by_library.get(
                            library_name,
                            (),
                        )
                    )

                    if len(
                        apex_candidates
                    ) > 1:
                        reason = (
                            f"library {library_name!r} has multiple active "
                            "APEX providers"
                        )

                        if reason not in ambiguous_reasons:
                            ambiguous_reasons.append(
                                reason
                            )

                        requirement_resolutions.append(
                            AndroidRuntimeLinkerRequirementResolution(
                                source_namespace=(
                                    current.namespace
                                ),
                                library_name=library_name,
                                provider_kind=None,
                                target_namespace=None,
                                status=(
                                    AndroidRuntimeLinkerResolutionStatus
                                    .AMBIGUOUS
                                ),
                                reason=reason,
                            )
                        )

                        continue

                    if len(
                        apex_candidates
                    ) == 1:
                        provider = (
                            apex_candidates[
                                0
                            ]
                            .apex_provider
                        )

                        if provider.namespace_name is None:
                            reason = (
                                f"APEX provider for {library_name!r} "
                                "has no namespace name"
                            )

                            if reason not in unresolved_reasons:
                                unresolved_reasons.append(
                                    reason
                                )

                            requirement_resolutions.append(
                                AndroidRuntimeLinkerRequirementResolution(
                                    source_namespace=(
                                        current.namespace
                                    ),
                                    library_name=library_name,
                                    provider_kind=None,
                                    target_namespace=None,
                                    status=(
                                        AndroidRuntimeLinkerResolutionStatus
                                        .UNRESOLVED
                                    ),
                                    reason=reason,
                                )
                            )

                            continue

                        target = (
                            provider.namespace_name
                        )

                        link = cls._get_link(
                            working=current,
                            target_namespace=target,
                        )

                        if not link.allow_all_shared_libs:
                            if (
                                library_name
                                not in link.shared_libraries
                            ):
                                link.shared_libraries.append(
                                    library_name
                                )

                        add_namespace(
                            AndroidRuntimeLinkerEffectiveNamespace(
                                index=len(
                                    working
                                ),
                                apex_provider=provider,
                                apex_provider_visible=False,
                            )
                        )

                        requirement_resolutions.append(
                            AndroidRuntimeLinkerRequirementResolution(
                                source_namespace=(
                                    current.namespace
                                ),
                                library_name=library_name,
                                provider_kind=(
                                    AndroidRuntimeLinkerResolvedProviderKind
                                    .APEX
                                ),
                                target_namespace=target,
                                apex_provider=provider,
                            )
                        )

                        continue

                    alias_candidates = (
                        alias_by_name.get(
                            library_name,
                            (),
                        )
                    )

                    if alias_candidates:
                        # Android LibProviders maps one alias to a vector and
                        # applies every provider in that vector.
                        for alias_provider in (
                            alias_candidates
                        ):
                            target = (
                                alias_provider.namespace.name
                            )

                            link = cls._get_link(
                                working=current,
                                target_namespace=target,
                            )

                            modifier = (
                                alias_provider
                                .link_modifier
                            )

                            if (
                                modifier.kind
                                is (
                                    AndroidRuntimeLinkerAliasLinkModifierKind
                                    .ALLOW_ALL_SHARED_LIBRARIES
                                )
                            ):
                                link.allow_all_shared_libs = True
                                link.shared_libraries.clear()

                            elif not link.allow_all_shared_libs:
                                for modifier_expression in (
                                    modifier.shared_libraries
                                ):
                                    resolved_modifier = (
                                        AndroidRuntimeLinkerExpressionResolver
                                        .resolve(
                                            expression=(
                                                modifier_expression
                                            ),
                                            environment=environment,
                                        )
                                    )

                                    if (
                                        resolved_modifier
                                        .unresolved_variable
                                        is not None
                                    ):
                                        reason = (
                                            f"alias {library_name!r} "
                                            "requires undefined variable "
                                            f"{resolved_modifier.unresolved_variable!r}"
                                        )

                                        if (
                                            reason
                                            not in unresolved_reasons
                                        ):
                                            unresolved_reasons.append(
                                                reason
                                            )

                                        continue

                                    for shared_library in (
                                        resolved_modifier.libraries
                                    ):
                                        if (
                                            shared_library
                                            not in link.shared_libraries
                                        ):
                                            link.shared_libraries.append(
                                                shared_library
                                            )

                            added_namespace = (
                                AndroidRuntimeLinkerEffectiveNamespace(
                                    index=len(
                                        working
                                    ),
                                    constructed_namespace=(
                                        alias_provider.namespace
                                    ),
                                )
                            )

                            add_namespace(
                                added_namespace
                            )

                            requirement_resolutions.append(
                                AndroidRuntimeLinkerRequirementResolution(
                                    source_namespace=(
                                        current.namespace
                                    ),
                                    library_name=library_name,
                                    provider_kind=(
                                        AndroidRuntimeLinkerResolvedProviderKind
                                        .ALIAS
                                    ),
                                    target_namespace=target,
                                    alias_provider=(
                                        alias_provider
                                    ),
                                )
                            )

                        continue

                    reason = (
                        f"no concrete, APEX, or alias provider for "
                        f"{library_name!r} required by namespace "
                        f"{current.namespace.name!r}"
                    )

                    should_fail = (
                        cls._should_fail_on_missing_deps(
                            namespace_name=(
                                current.namespace.name
                            ),
                            strict_mode=strict_mode,
                            target_apex=target_apex,
                        )
                    )

                    if should_fail:
                        if reason not in unresolved_reasons:
                            unresolved_reasons.append(
                                reason
                            )

                        missing_status = (
                            AndroidRuntimeLinkerResolutionStatus
                            .UNRESOLVED
                        )

                    else:
                        missing_status = (
                            AndroidRuntimeLinkerResolutionStatus
                            .TOLERATED_MISSING
                        )

                    requirement_resolutions.append(
                        AndroidRuntimeLinkerRequirementResolution(
                            source_namespace=(
                                current.namespace
                            ),
                            library_name=library_name,
                            provider_kind=None,
                            target_namespace=None,
                            status=missing_status,
                            reason=reason,
                        )
                    )

        # Android sorts only after dynamic expansion completes:
        # default first, everything else lexical by namespace name.
        ordered = tuple(
            sorted(
                working,
                key=lambda item: (
                    0
                    if item.namespace.name
                    == "default"
                    else 1,
                    item.namespace.name,
                ),
            )
        )

        resolved_namespaces = tuple(
            AndroidRuntimeLinkerResolvedNamespace(
                namespace=item.namespace,
                links=tuple(
                    AndroidRuntimeLinkerResolvedNamespaceLink(
                        source_namespace=(
                            item.namespace.name
                        ),
                        target_namespace=(
                            link.target_namespace
                        ),
                        shared_libraries=tuple(
                            link.shared_libraries
                        ),
                        allow_all_shared_libs=(
                            link.allow_all_shared_libs
                        ),
                    )
                    for link
                    in item.links
                ),
            )
            for item
            in ordered
        )

        final_namespace_names = {
            namespace.namespace.name
            for namespace
            in resolved_namespaces
        }

        dangling_links = tuple(
            (
                namespace.namespace.name,
                link.target_namespace,
            )
            for namespace
            in resolved_namespaces
            for link
            in namespace.links
            if (
                link.target_namespace
                not in final_namespace_names
            )
        )

        if dangling_links:
            raise ValueError(
                "Section::Resolve produced namespace links with "
                "missing final targets: "
                f"section={section_name!r}, "
                f"links={dangling_links!r}"
            )

        if unresolved_reasons:
            status = (
                AndroidRuntimeLinkerResolutionStatus
                .UNRESOLVED
            )

            reasons = tuple(
                unresolved_reasons
                + ambiguous_reasons
            )

        elif ambiguous_reasons:
            status = (
                AndroidRuntimeLinkerResolutionStatus
                .AMBIGUOUS
            )

            reasons = tuple(
                ambiguous_reasons
            )

        else:
            status = (
                AndroidRuntimeLinkerResolutionStatus
                .RESOLVED
            )

            reasons = ()

        return AndroidRuntimeLinkerResolvedSection(
            section_name=section_name,
            namespaces=resolved_namespaces,
            requirement_resolutions=tuple(
                requirement_resolutions
            ),
            status=status,
            reasons=reasons,
        )
