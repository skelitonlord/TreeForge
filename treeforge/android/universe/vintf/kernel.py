from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.vintf import (
    VintfXmlElement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfKernelConfigRequirement:
    """
    One typed VINTF kernel configuration requirement.

    ``value_type`` preserves the VINTF type rather than coercing every value
    into a Python scalar. The literal value remains authoritative.
    """

    key: str
    value: str
    value_type: str

    element: VintfXmlElement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfKernelCondition:
    """
    One VINTF kernel compatibility predicate.

    Configs inside a condition are predicates controlling applicability of
    their parent kernel requirement and must not be flattened into the
    unconditional kernel-config set.
    """

    configs: tuple[
        AndroidUniverseVintfKernelConfigRequirement,
        ...,
    ]

    element: VintfXmlElement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfKernelRequirement:
    """
    One complete VINTF kernel compatibility requirement.
    """

    version: str | None
    level: str | None

    configs: tuple[
        AndroidUniverseVintfKernelConfigRequirement,
        ...,
    ] = ()

    conditions: tuple[
        AndroidUniverseVintfKernelCondition,
        ...,
    ] = ()

    element: VintfXmlElement | None = None