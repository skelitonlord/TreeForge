from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.vintf import (
    VintfXmlElement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfSystemSdkRequirement:
    """
    Semantic VINTF System-SDK declaration.

    Versions preserve their declaration order and literal representation.
    """

    versions: tuple[
        str,
        ...,
    ]

    element: VintfXmlElement