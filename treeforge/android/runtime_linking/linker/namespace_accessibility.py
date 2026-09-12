"""
Direct Android linker namespace accessibility.

This models the exact one-hop namespace-link relation consumed by bionic
library lookup after Section::Resolve() and AddStandardSystemLinks().

It deliberately does not compute a transitive namespace closure.

For one library lookup, bionic searches the starting namespace and then its
direct linked namespaces in canonical link order. A direct link participates
only when it allows all shared libraries or admits the requested SONAME.

When a library is loaded through a linked namespace, that load does not
recursively search the target namespace's links. If the loaded library has
DT_NEEDED dependencies, those later tasks begin from the namespace in which
the parent library was loaded.
"""

from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.runtime_linking.linker.resolution import (
    AndroidRuntimeLinkerResolvedNamespace,
    AndroidRuntimeLinkerResolvedNamespaceLink,
    AndroidRuntimeLinkerResolvedSection,
)
from treeforge.android.runtime_linking.linker.standard_system_links import (
    AndroidRuntimeLinkerStandardSystemLinkedSection,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerNamespaceAccessibilityLink:
    """
    One exact ordered direct namespace-accessibility edge.
    """

    index: int

    source_namespace: AndroidRuntimeLinkerResolvedNamespace
    target_namespace: AndroidRuntimeLinkerResolvedNamespace | None

    source_link: AndroidRuntimeLinkerResolvedNamespaceLink

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.index,
            int,
        ):
            raise TypeError(
                "index must be an int"
            )

        if self.index < 0:
            raise ValueError(
                "index must be non-negative"
            )

        if not isinstance(
            self.source_namespace,
            AndroidRuntimeLinkerResolvedNamespace,
        ):
            raise TypeError(
                "source_namespace has invalid type"
            )

        if (
            self.target_namespace is not None
            and not isinstance(
                self.target_namespace,
                AndroidRuntimeLinkerResolvedNamespace,
            )
        ):
            raise TypeError(
                "target_namespace has invalid type"
            )

        if not isinstance(
            self.source_link,
            AndroidRuntimeLinkerResolvedNamespaceLink,
        ):
            raise TypeError(
                "source_link has invalid type"
            )

        if (
            self.source_link.source_namespace
            != self.source_namespace.namespace.name
        ):
            raise ValueError(
                "source link namespace identity does not match "
                "source namespace"
            )

        if (
            self.target_namespace is not None
            and self.source_link.target_namespace
            != self.target_namespace.namespace.name
        ):
            raise ValueError(
                "source link target identity does not match "
                "target namespace"
            )

    @property
    def source_namespace_name(
        self,
    ) -> str:
        return (
            self.source_namespace
            .namespace
            .name
        )

    @property
    def target_namespace_name(
        self,
    ) -> str:
        return (
            self.source_link
            .target_namespace
        )

    @property
    def allow_all_shared_libs(
        self,
    ) -> bool:
        return (
            self.source_link
            .allow_all_shared_libs
        )

    @property
    def shared_libraries(
        self,
    ) -> tuple[str, ...]:
        return (
            self.source_link
            .shared_libraries
        )

    def admits(
        self,
        soname: str,
    ) -> bool:
        """
        Mirror android_namespace_link_t::is_accessible().
        """

        if (
            not isinstance(
                soname,
                str,
            )
            or not soname
        ):
            raise ValueError(
                "soname must be a non-empty string"
            )

        return (
            self.allow_all_shared_libs
            or soname
            in self.shared_libraries
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerNamespaceAccessibility:
    """
    Direct ordered accessibility for one final namespace.
    """

    namespace: AndroidRuntimeLinkerResolvedNamespace

    links: tuple[
        AndroidRuntimeLinkerNamespaceAccessibilityLink,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.namespace,
            AndroidRuntimeLinkerResolvedNamespace,
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

        if not all(
            isinstance(
                link,
                AndroidRuntimeLinkerNamespaceAccessibilityLink,
            )
            for link
            in self.links
        ):
            raise TypeError(
                "links contain invalid values"
            )

        if tuple(
            link.index
            for link
            in self.links
        ) != tuple(
            range(
                len(
                    self.links
                )
            )
        ):
            raise ValueError(
                "links must preserve canonical zero-based link order"
            )

        if not all(
            link.source_namespace
            is self.namespace
            for link
            in self.links
        ):
            raise ValueError(
                "all accessibility links must preserve exact "
                "source namespace identity"
            )

        if tuple(
            link.source_link
            for link
            in self.links
        ) != self.namespace.links:
            raise ValueError(
                "accessibility links must preserve exact final "
                "namespace-link identity and order"
            )

    def links_admitting(
        self,
        soname: str,
    ) -> tuple[
        AndroidRuntimeLinkerNamespaceAccessibilityLink,
        ...,
    ]:
        """
        Return direct linked namespaces admitting SONAME, in bionic order.
        """

        return tuple(
            link
            for link
            in self.links
            if link.admits(
                soname
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerSectionAccessibility:
    """
    Direct namespace accessibility for one post-standard-link section.
    """

    source: AndroidRuntimeLinkerStandardSystemLinkedSection

    section: AndroidRuntimeLinkerResolvedSection

    namespaces: tuple[
        AndroidRuntimeLinkerNamespaceAccessibility,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidRuntimeLinkerStandardSystemLinkedSection,
        ):
            raise TypeError(
                "source has invalid type"
            )

        if (
            self.section
            is not self.source.linked_section
        ):
            raise ValueError(
                "section must preserve exact post-standard-link "
                "section identity"
            )

        if not isinstance(
            self.namespaces,
            tuple,
        ):
            raise TypeError(
                "namespaces must be a tuple"
            )

        if len(
            self.namespaces
        ) != len(
            self.section.namespaces
        ):
            raise ValueError(
                "namespace accessibility coverage must equal "
                "final section namespace coverage"
            )

        if not all(
            accessibility.namespace
            is namespace
            for accessibility, namespace
            in zip(
                self.namespaces,
                self.section.namespaces,
                strict=True,
            )
        ):
            raise ValueError(
                "namespace accessibility must preserve exact "
                "final namespace identity and order"
            )

    def namespace(
        self,
        name: str,
    ) -> (
        AndroidRuntimeLinkerNamespaceAccessibility
        | None
    ):
        candidates = tuple(
            namespace
            for namespace
            in self.namespaces
            if (
                namespace
                .namespace
                .namespace
                .name
                == name
            )
        )

        if not candidates:
            return None

        if len(
            candidates
        ) != 1:
            raise ValueError(
                "final linker section contains duplicate "
                f"namespace name: {name!r}"
            )

        return candidates[0]


class AndroidRuntimeLinkerNamespaceAccessibilityBuilder:
    """
    Build direct bionic namespace accessibility from one final section.
    """

    @staticmethod
    def build(
        source: AndroidRuntimeLinkerStandardSystemLinkedSection,
    ) -> AndroidRuntimeLinkerSectionAccessibility:
        if not isinstance(
            source,
            AndroidRuntimeLinkerStandardSystemLinkedSection,
        ):
            raise TypeError(
                "source has invalid type"
            )

        section = (
            source.linked_section
        )

        namespace_by_name = {}

        for namespace in section.namespaces:
            name = (
                namespace
                .namespace
                .name
            )

            if name in namespace_by_name:
                raise ValueError(
                    "final linker section contains duplicate "
                    f"namespace name: {name!r}"
                )

            namespace_by_name[
                name
            ] = namespace

        results = []

        for namespace in section.namespaces:
            links = []

            for index, source_link in enumerate(
                namespace.links
            ):
                target = (
                    namespace_by_name
                    .get(
                        source_link
                        .target_namespace
                    )
                )

                links.append(
                    AndroidRuntimeLinkerNamespaceAccessibilityLink(
                        index=index,
                        source_namespace=namespace,
                        target_namespace=target,
                        source_link=source_link,
                    )
                )

            results.append(
                AndroidRuntimeLinkerNamespaceAccessibility(
                    namespace=namespace,
                    links=tuple(
                        links
                    ),
                )
            )

        return (
            AndroidRuntimeLinkerSectionAccessibility(
                source=source,
                section=section,
                namespaces=tuple(
                    results
                ),
            )
        )
