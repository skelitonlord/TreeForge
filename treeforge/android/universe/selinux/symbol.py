from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.universe.selinux.cil import (
    AndroidUniverseSelinuxCilRequirement,
)


class AndroidUniverseSelinuxSymbolKind(
    StrEnum
):
    TYPE = "type"
    TYPE_ATTRIBUTE = "type_attribute"
    TYPE_ALIAS = "type_alias"
    ROLE = "role"
    ROLE_ATTRIBUTE = "role_attribute"
    USER = "user"
    CLASS = "class"
    COMMON = "common"
    SID = "sid"
    SENSITIVITY = "sensitivity"
    CATEGORY = "category"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxSymbolEvidence:
    """
    One exact CIL declaration contributing to a canonical policy symbol.

    The original Universe requirement remains attached, which in turn retains
    the exact Parsing CIL form and source-line identity.
    """

    requirement: AndroidUniverseSelinuxCilRequirement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxSymbol:
    """
    One canonical named SELinux policy symbol.

    Repeated declarations from framework, vendor, product, system_ext,
    compatibility mappings, or other sources converge here without losing
    any declaration evidence.
    """

    kind: AndroidUniverseSelinuxSymbolKind
    name: str

    evidence: tuple[
        AndroidUniverseSelinuxSymbolEvidence,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidUniverseSelinuxSymbolKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseSelinuxSymbolKind"
            )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name must not be empty"
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
                item,
                AndroidUniverseSelinuxSymbolEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniverseSelinuxSymbolEvidence"
            )

    @property
    def symbol_id(
        self,
    ) -> str:
        return (
            f"selinux-symbol:"
            f"{self.kind.value}:"
            f"{self.name}"
        )