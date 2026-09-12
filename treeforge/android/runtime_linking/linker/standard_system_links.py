"""
Android linkerconfig AddStandardSystemLinks() semantics.

This module consumes the immutable Section::Resolve() result and produces
the next immutable linker graph checkpoint.

It deliberately stops before namespace reachability, ELF DT_NEEDED
resolution, Reconstruction Ownership, Planning, or materialization.
"""

from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.runtime_linking.linker.expression import (
    variable_library,
)
from treeforge.android.runtime_linking.linker.expression_resolution import (
    AndroidRuntimeLinkerExpressionResolver,
    AndroidRuntimeLinkerVariableEnvironment,
)
from treeforge.android.runtime_linking.linker.resolution import (
    AndroidRuntimeLinkerResolvedNamespace,
    AndroidRuntimeLinkerResolvedNamespaceLink,
    AndroidRuntimeLinkerResolvedSection,
)


_BIONIC_LIBRARIES = (
    "libc.so",
    "libdl.so",
    "libdl_android.so",
    "libm.so",
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerStandardSystemLinkedSection:
    """
    One section immediately after Android AddStandardSystemLinks().

    ``source_section`` preserves the exact Section::Resolve() checkpoint.
    ``linked_section`` preserves all source effective namespace identities
    while augmenting only namespace links.
    """

    source_section: AndroidRuntimeLinkerResolvedSection
    linked_section: AndroidRuntimeLinkerResolvedSection

    system_namespace_name: str
    section_vndk_enabled: bool
    debuggable: bool

    sanitizer_runtime_libraries: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_section,
            AndroidRuntimeLinkerResolvedSection,
        ):
            raise TypeError(
                "source_section has invalid type"
            )

        if not isinstance(
            self.linked_section,
            AndroidRuntimeLinkerResolvedSection,
        ):
            raise TypeError(
                "linked_section has invalid type"
            )

        if (
            not isinstance(
                self.system_namespace_name,
                str,
            )
            or not self.system_namespace_name
        ):
            raise ValueError(
                "system_namespace_name must be non-empty"
            )

        if not isinstance(
            self.section_vndk_enabled,
            bool,
        ):
            raise TypeError(
                "section_vndk_enabled must be a bool"
            )

        if not isinstance(
            self.debuggable,
            bool,
        ):
            raise TypeError(
                "debuggable must be a bool"
            )

        if not isinstance(
            self.sanitizer_runtime_libraries,
            tuple,
        ):
            raise TypeError(
                "sanitizer_runtime_libraries must be a tuple"
            )

        if (
            self.linked_section.section_name
            != self.source_section.section_name
        ):
            raise ValueError(
                "post-standard-link section must preserve section name"
            )

        if (
            self.linked_section.requirement_resolutions
            is not self.source_section.requirement_resolutions
        ):
            raise ValueError(
                "AddStandardSystemLinks must preserve exact "
                "requirement-resolution identity"
            )

        if (
            self.linked_section.status
            is not self.source_section.status
        ):
            raise ValueError(
                "AddStandardSystemLinks must preserve section status"
            )

        if (
            self.linked_section.reasons
            is not self.source_section.reasons
        ):
            raise ValueError(
                "AddStandardSystemLinks must preserve exact reason identity"
            )

        if len(
            self.linked_section.namespaces
        ) != len(
            self.source_section.namespaces
        ):
            raise ValueError(
                "AddStandardSystemLinks must preserve namespace coverage"
            )

        if not all(
            linked.namespace is source.namespace
            for linked, source
            in zip(
                self.linked_section.namespaces,
                self.source_section.namespaces,
                strict=True,
            )
        ):
            raise ValueError(
                "AddStandardSystemLinks must preserve exact "
                "effective namespace identity and order"
            )


class AndroidRuntimeLinkerStandardSystemLinksBuilder:
    """
    Reproduce contents::AddStandardSystemLinks().
    """

    @staticmethod
    def _append_unique(
        target: list[str],
        values: tuple[
            str,
            ...,
        ],
    ) -> None:
        for value in values:
            if value not in target:
                target.append(
                    value
                )

    @classmethod
    def apply(
        cls,
        *,
        section: AndroidRuntimeLinkerResolvedSection,
        environment: AndroidRuntimeLinkerVariableEnvironment,
        system_namespace_name: str,
        section_vndk_enabled: bool,
        debuggable: bool,
    ) -> AndroidRuntimeLinkerStandardSystemLinkedSection:
        if not isinstance(
            section,
            AndroidRuntimeLinkerResolvedSection,
        ):
            raise TypeError(
                "section has invalid type"
            )

        if (
            not isinstance(
                system_namespace_name,
                str,
            )
            or not system_namespace_name
        ):
            raise ValueError(
                "system_namespace_name must be non-empty"
            )

        if not isinstance(
            section_vndk_enabled,
            bool,
        ):
            raise TypeError(
                "section_vndk_enabled must be a bool"
            )

        if not isinstance(
            debuggable,
            bool,
        ):
            raise TypeError(
                "debuggable must be a bool"
            )

        sanitizer_expression = (
            AndroidRuntimeLinkerExpressionResolver
            .resolve(
                expression=variable_library(
                    "SANITIZER_RUNTIME_LIBRARIES",
                    "",
                ),
                environment=environment,
            )
        )

        if (
            sanitizer_expression.unresolved_variable
            is not None
        ):
            raise ValueError(
                "SANITIZER_RUNTIME_LIBRARIES must be defined by "
                "LoadLibraryListVariables semantics"
            )

        sanitizer_libraries = tuple(
            sanitizer_expression.libraries
        )

        linked_namespaces = []

        for resolved_namespace in section.namespaces:
            namespace_name = (
                resolved_namespace
                .namespace
                .name
            )

            if namespace_name == system_namespace_name:
                linked_namespaces.append(
                    resolved_namespace
                )
                continue

            links = list(
                resolved_namespace.links
            )

            system_link_index = next(
                (
                    index
                    for index, link
                    in enumerate(
                        links
                    )
                    if (
                        link.target_namespace
                        == system_namespace_name
                    )
                ),
                None,
            )

            if system_link_index is None:
                shared_libraries = []

                cls._append_unique(
                    shared_libraries,
                    _BIONIC_LIBRARIES,
                )

                if not (
                    section_vndk_enabled
                    and namespace_name == "default"
                ):
                    cls._append_unique(
                        shared_libraries,
                        sanitizer_libraries,
                    )

                if debuggable:
                    cls._append_unique(
                        shared_libraries,
                        (
                            "libfdtrack.so",
                        ),
                    )

                links.append(
                    AndroidRuntimeLinkerResolvedNamespaceLink(
                        source_namespace=namespace_name,
                        target_namespace=system_namespace_name,
                        shared_libraries=tuple(
                            shared_libraries
                        ),
                    )
                )

            else:
                existing = links[
                    system_link_index
                ]

                #
                # TreeForge's resolved-link model intentionally represents an
                # allow-all link without an additional restricted library set.
                # Android AddSharedLib() cannot make such a link more permissive,
                # so preserving allow-all retains the exact effective semantics.
                #
                if not existing.allow_all_shared_libs:
                    shared_libraries = list(
                        existing.shared_libraries
                    )

                    cls._append_unique(
                        shared_libraries,
                        _BIONIC_LIBRARIES,
                    )

                    if not (
                        section_vndk_enabled
                        and namespace_name == "default"
                    ):
                        cls._append_unique(
                            shared_libraries,
                            sanitizer_libraries,
                        )

                    if debuggable:
                        cls._append_unique(
                            shared_libraries,
                            (
                                "libfdtrack.so",
                            ),
                        )

                    links[
                        system_link_index
                    ] = (
                        AndroidRuntimeLinkerResolvedNamespaceLink(
                            source_namespace=(
                                existing.source_namespace
                            ),
                            target_namespace=(
                                existing.target_namespace
                            ),
                            shared_libraries=tuple(
                                shared_libraries
                            ),
                            allow_all_shared_libs=False,
                        )
                    )

            linked_namespaces.append(
                AndroidRuntimeLinkerResolvedNamespace(
                    namespace=(
                        resolved_namespace.namespace
                    ),
                    links=tuple(
                        links
                    ),
                )
            )

        linked_section = (
            AndroidRuntimeLinkerResolvedSection(
                section_name=section.section_name,
                namespaces=tuple(
                    linked_namespaces
                ),
                requirement_resolutions=(
                    section.requirement_resolutions
                ),
                status=section.status,
                reasons=section.reasons,
            )
        )

        return (
            AndroidRuntimeLinkerStandardSystemLinkedSection(
                source_section=section,
                linked_section=linked_section,
                system_namespace_name=(
                    system_namespace_name
                ),
                section_vndk_enabled=(
                    section_vndk_enabled
                ),
                debuggable=debuggable,
                sanitizer_runtime_libraries=(
                    sanitizer_libraries
                ),
            )
        )
