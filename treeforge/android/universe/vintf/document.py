from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.vintf import (
    VintfXmlAttribute,
    VintfXmlElement,
)
from treeforge.android.universe.vintf.avb import (
    AndroidUniverseVintfAvbRequirement,
)
from treeforge.android.universe.vintf.hal import (
    AndroidUniverseVintfHalRequirement,
)
from treeforge.android.universe.vintf.kernel import (
    AndroidUniverseVintfKernelRequirement,
)
from treeforge.android.universe.vintf.sepolicy import (
    AndroidUniverseVintfSepolicyRequirement,
)
from treeforge.android.universe.vintf.system_sdk import (
    AndroidUniverseVintfSystemSdkRequirement,
)


class AndroidUniverseVintfDocumentKind(
    StrEnum
):
    MANIFEST = "manifest"
    COMPATIBILITY_MATRIX = (
        "compatibility-matrix"
    )


class AndroidUniverseVintfDocumentSide(
    StrEnum
):
    DEVICE = "device"
    FRAMEWORK = "framework"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfUninterpretedElement:
    """
    Preserve a VINTF XML element whose semantic family is not yet known.

    Future Android versions must become visible as explicit Universe
    coverage debt rather than disappearing during interpretation.
    """

    element: VintfXmlElement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfUninterpretedAttribute:
    """
    Preserve an attribute outside the currently interpreted VINTF grammar.
    """

    element: VintfXmlElement
    attribute: VintfXmlAttribute


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfDocumentSemantics:
    """
    Complete interpreted semantic surface of one VINTF document.
    """

    kind: AndroidUniverseVintfDocumentKind
    side: AndroidUniverseVintfDocumentSide

    meta_version: str

    level: str | None = None
    target_level: str | None = None

    hals: tuple[
        AndroidUniverseVintfHalRequirement,
        ...,
    ] = ()

    kernels: tuple[
        AndroidUniverseVintfKernelRequirement,
        ...,
    ] = ()

    sepolicy: tuple[
        AndroidUniverseVintfSepolicyRequirement,
        ...,
    ] = ()

    system_sdk: tuple[
        AndroidUniverseVintfSystemSdkRequirement,
        ...,
    ] = ()

    avb: tuple[
        AndroidUniverseVintfAvbRequirement,
        ...,
    ] = ()

    uninterpreted_elements: tuple[
        AndroidUniverseVintfUninterpretedElement,
        ...,
    ] = ()

    uninterpreted_attributes: tuple[
        AndroidUniverseVintfUninterpretedAttribute,
        ...,
    ] = ()