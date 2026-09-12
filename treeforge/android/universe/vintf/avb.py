from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.vintf import (
    VintfXmlElement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfAvbRequirement:
    """
    Semantic VINTF AVB compatibility declaration.
    """

    vbmeta_version: str | None

    element: VintfXmlElement