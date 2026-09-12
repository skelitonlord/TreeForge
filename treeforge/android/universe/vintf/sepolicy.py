from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.vintf import (
    VintfXmlElement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfSepolicyRequirement:
    """
    Complete semantic VINTF SEPolicy declaration.

    Manifest-style ``version`` values and compatibility-matrix-style
    ``sepolicy-version`` values remain separate and ordered.
    """

    versions: tuple[
        str,
        ...,
    ]

    sepolicy_versions: tuple[
        str,
        ...,
    ]

    kernel_sepolicy_version: (
        str
        | None
    )

    element: VintfXmlElement