from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.universe.selinux.cil import (
    AndroidUniverseSelinuxCilRequirement,
)
from treeforge.android.universe.selinux.mac_permissions import (
    AndroidUniverseSelinuxMacPermissionsRequirement,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextRequirement,
    AndroidUniverseSelinuxSeappRequirement,
)
from treeforge.android.universe.selinux.symbol import (
    AndroidUniverseSelinuxSymbol,
)


class AndroidUniverseSelinuxAccessRuleKind(
    StrEnum
):
    ALLOW = "allow"
    AUDITALLOW = "auditallow"
    DONTAUDIT = "dontaudit"
    NEVERALLOW = "neverallow"


class AndroidUniverseSelinuxGenfsLabelsVersionState(
    StrEnum
):
    AGREED = "agreed"
    CONFLICTING = "conflicting"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxGenfsLabelsVersionConclusion:
    """
    Canonical Universe conclusion for the SELinux genfs labels version.

    Every observed source requirement remains attached as evidence. Repeated
    identical observations converge on one agreed value; differing observations
    remain an explicit conflict. Absence of an observation is unresolved and
    never invents a default.
    """

    state: AndroidUniverseSelinuxGenfsLabelsVersionState

    value: str | None = None

    observed_values: tuple[
        str,
        ...,
    ] = ()

    evidence: tuple[
        "AndroidUniverseSelinuxSourceRequirement",
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        from treeforge.android.universe.selinux.requirement import (
            AndroidUniverseSelinuxSourceRequirement,
        )

        if not isinstance(
            self.state,
            AndroidUniverseSelinuxGenfsLabelsVersionState,
        ):
            raise TypeError(
                "state must be an "
                "AndroidUniverseSelinuxGenfsLabelsVersionState"
            )

        if (
            self.value is not None
            and not isinstance(
                self.value,
                str,
            )
        ):
            raise TypeError(
                "value must be a str or None"
            )

        if not isinstance(
            self.observed_values,
            tuple,
        ):
            raise TypeError(
                "observed_values must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.observed_values
        ):
            raise TypeError(
                "observed_values must contain only strings"
            )

        if (
            self.observed_values
            != tuple(
                sorted(
                    set(
                        self.observed_values
                    )
                )
            )
        ):
            raise ValueError(
                "observed_values must contain unique values "
                "in canonical order"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseSelinuxSourceRequirement,
            )
            for requirement in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniverseSelinuxSourceRequirement instances"
            )

        if (
            self.state
            is AndroidUniverseSelinuxGenfsLabelsVersionState.AGREED
        ):
            if (
                len(
                    self.observed_values
                )
                != 1
                or self.value
                != self.observed_values[0]
                or not self.evidence
            ):
                raise ValueError(
                    "agreed genfs labels version requires exactly "
                    "one observed value, matching value, and evidence"
                )

        elif (
            self.state
            is AndroidUniverseSelinuxGenfsLabelsVersionState.CONFLICTING
        ):
            if (
                len(
                    self.observed_values
                )
                < 2
                or self.value is not None
                or not self.evidence
            ):
                raise ValueError(
                    "conflicting genfs labels version requires at least "
                    "two observed values, no canonical value, and evidence"
                )

        elif (
            self.state
            is AndroidUniverseSelinuxGenfsLabelsVersionState.UNRESOLVED
        ):
            if (
                self.value is not None
                or self.observed_values
                or self.evidence
            ):
                raise ValueError(
                    "unresolved genfs labels version must not invent "
                    "a value or evidence"
                )


class AndroidUniverseSelinuxExtendedAccessRuleKind(
    StrEnum
):
    ALLOWX = "allowx"
    DONTAUDITX = "dontauditx"
    NEVERALLOWX = "neverallowx"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxTypeAttributeMembership:
    attribute: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxTypeAttributeExpansion:
    """
    One CIL expandtypeattribute requirement.

    CIL supplies the affected attributes as an expression list rather than
    one scalar symbol. ``attributes`` preserves the directly enumerable
    symbols while the exact original expression remains attached through
    ``requirement``.

    ``expand`` is the normalized boolean when the literal is ``true`` or
    ``false``. ``expand_literal`` always preserves the original value.
    """

    attributes: tuple[
        str,
        ...,
    ]

    expand_literal: str
    expand: bool | None

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxTypeAliasRelationship:
    alias: str
    actual: str | None

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxRoleTypeRelationship:
    role: str
    type_name: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxUserRoleRelationship:
    user: str
    role: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxClassCommonRelationship:
    class_name: str
    common_name: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxAccessRule:
    kind: AndroidUniverseSelinuxAccessRuleKind

    source: str
    target: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxExtendedAccessRule:
    kind: AndroidUniverseSelinuxExtendedAccessRuleKind

    source: str
    target: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxTypeTransition:
    source: str
    target: str
    object_class: str
    result_type: str

    name: str | None

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxGenfsContext:
    filesystem: str
    path: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxFsUse:
    behavior: str
    filesystem: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxHandleUnknown:
    """
    Effective CIL handleunknown policy.

    The literal is retained because future policy versions could expose a
    value TreeForge does not yet normalize.
    """

    value: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxSidContext:
    sid: str

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxPolicyGraph:
    """
    Canonical reconciled SELinux policy graph.

    Named declarations are canonicalized into symbols. Every relationship
    retains the exact Universe CIL requirement that established it.

    Complex CIL expressions are deliberately retained through their original
    requirement instead of being flattened or guessed.
    """

    genfs_labels_version_conclusion: (
        AndroidUniverseSelinuxGenfsLabelsVersionConclusion
        | None
    ) = None

    symbols: tuple[
        AndroidUniverseSelinuxSymbol,
        ...,
    ] = ()

    type_attribute_memberships: tuple[
        AndroidUniverseSelinuxTypeAttributeMembership,
        ...,
    ] = ()

    type_attribute_expansions: tuple[
        AndroidUniverseSelinuxTypeAttributeExpansion,
        ...,
    ] = ()

    type_aliases: tuple[
        AndroidUniverseSelinuxTypeAliasRelationship,
        ...,
    ] = ()

    role_types: tuple[
        AndroidUniverseSelinuxRoleTypeRelationship,
        ...,
    ] = ()

    user_roles: tuple[
        AndroidUniverseSelinuxUserRoleRelationship,
        ...,
    ] = ()

    class_commons: tuple[
        AndroidUniverseSelinuxClassCommonRelationship,
        ...,
    ] = ()

    access_rules: tuple[
        AndroidUniverseSelinuxAccessRule,
        ...,
    ] = ()

    extended_access_rules: tuple[
        AndroidUniverseSelinuxExtendedAccessRule,
        ...,
    ] = ()

    type_transitions: tuple[
        AndroidUniverseSelinuxTypeTransition,
        ...,
    ] = ()

    genfs_contexts: tuple[
        AndroidUniverseSelinuxGenfsContext,
        ...,
    ] = ()

    fs_uses: tuple[
        AndroidUniverseSelinuxFsUse,
        ...,
    ] = ()

    sid_contexts: tuple[
        AndroidUniverseSelinuxSidContext,
        ...,
    ] = ()

    handle_unknown: tuple[
        AndroidUniverseSelinuxHandleUnknown,
        ...,
    ] = ()

    context_requirements: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ] = ()

    seapp_requirements: tuple[
        AndroidUniverseSelinuxSeappRequirement,
        ...,
    ] = ()

    mac_permissions_requirements: tuple[
        AndroidUniverseSelinuxMacPermissionsRequirement,
        ...,
    ] = ()

    policy_capabilities: tuple[
        AndroidUniverseSelinuxCilRequirement,
        ...,
    ] = ()

    mls_requirements: tuple[
        AndroidUniverseSelinuxCilRequirement,
        ...,
    ] = ()

    ordering_requirements: tuple[
        AndroidUniverseSelinuxCilRequirement,
        ...,
    ] = ()

    other_requirements: tuple[
        AndroidUniverseSelinuxCilRequirement,
        ...,
    ] = ()

    @property
    def types(
        self,
    ) -> tuple[
        AndroidUniverseSelinuxSymbol,
        ...,
    ]:
        from treeforge.android.universe.selinux.symbol import (
            AndroidUniverseSelinuxSymbolKind,
        )

        return tuple(
            symbol
            for symbol in self.symbols
            if (
                symbol.kind
                is AndroidUniverseSelinuxSymbolKind.TYPE
            )
        )

    @property
    def type_attributes(
        self,
    ) -> tuple[
        AndroidUniverseSelinuxSymbol,
        ...,
    ]:
        from treeforge.android.universe.selinux.symbol import (
            AndroidUniverseSelinuxSymbolKind,
        )

        return tuple(
            symbol
            for symbol in self.symbols
            if (
                symbol.kind
                is AndroidUniverseSelinuxSymbolKind.TYPE_ATTRIBUTE
            )
        )