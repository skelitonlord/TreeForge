from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.selinux import (
    AndroidSelinuxMacPermissionsElement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxMacPermissionsPackageRequirement:
    """
    One package refinement inside a mac_permissions signer rule.

    Exact Parsing element identity remains attached through ``element``.
    Universe adds only convenience accessors for canonical Android semantics.
    """

    element: AndroidSelinuxMacPermissionsElement

    @property
    def name(
        self,
    ) -> str | None:
        return self.element.attribute(
            "name"
        )

    @property
    def seinfo_values(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            value
            for child in self.element.children
            if child.name == "seinfo"
            for value in (
                child.attribute(
                    "value"
                ),
            )
            if value is not None
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxMacPermissionsRequirement:
    """
    One canonical top-level mac_permissions policy rule.

    The original parsed XML element remains attached exactly. Known Android
    semantics are exposed additively; unknown elements or attributes remain
    available through ``element`` and are never discarded.

    Typical top-level rule kinds are ``signer`` and ``default``.
    """

    element: AndroidSelinuxMacPermissionsElement

    @property
    def kind(
        self,
    ) -> str:
        return self.element.name

    @property
    def signature(
        self,
    ) -> str | None:
        """
        Return a direct signer signature when present.

        This value may be a literal expanded certificate or a symbolic tag.
        Universe does not infer how the source was originally authored.
        """

        return self.element.attribute(
            "signature"
        )

    @property
    def certificate_signatures(
        self,
    ) -> tuple[str, ...]:
        """
        Return direct nested ``cert`` signature selectors, preserving order.
        """

        return tuple(
            value
            for child in self.element.children
            if child.name == "cert"
            for value in (
                child.attribute(
                    "signature"
                ),
            )
            if value is not None
        )

    @property
    def signer_selectors(
        self,
    ) -> tuple[str, ...]:
        """
        Return every signer certificate selector represented by this rule.

        A signer may use either its own ``signature`` attribute, nested
        ``cert`` elements, or both.
        """

        values = []

        if self.signature is not None:
            values.append(
                self.signature
            )

        values.extend(
            self.certificate_signatures
        )

        return tuple(
            values
        )

    @property
    def seinfo_values(
        self,
    ) -> tuple[str, ...]:
        """
        Return direct seinfo values for this signer/default rule.
        """

        return tuple(
            value
            for child in self.element.children
            if child.name == "seinfo"
            for value in (
                child.attribute(
                    "value"
                ),
            )
            if value is not None
        )

    @property
    def package_requirements(
        self,
    ) -> tuple[
        AndroidUniverseSelinuxMacPermissionsPackageRequirement,
        ...,
    ]:
        return tuple(
            AndroidUniverseSelinuxMacPermissionsPackageRequirement(
                element=child
            )
            for child in self.element.children
            if child.name == "package"
        )

    @property
    def source_path(
        self,
    ):
        return self.element.source_path

    @property
    def source_line(
        self,
    ) -> int:
        return self.element.source_line
