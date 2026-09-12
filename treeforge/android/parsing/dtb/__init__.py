"""
Generic Flattened Device Tree Parsing.

Extraction owns physical container materialization. This package decodes only
the intrinsic structure of already-accessible FDT/DTB artifacts.
"""

from treeforge.android.parsing.dtb.model import (
    AndroidParsedDtboEntry,
    ParsedDtboExternalFixup,
    ParsedDtboExternalFixupLocation,
    ParsedDtboFragmentTarget,
    ParsedDtboLocalFixup,
    ParsedDtboOverlayMetadata,
    ParsedDtboSymbol,
    ParsedFdt,
    ParsedFdtHeader,
    ParsedFdtNode,
    ParsedFdtProperty,
    ParsedFdtReservation,
)
from treeforge.android.parsing.dtb.overlay import (
    AndroidDtboOverlayParser,
    DtboOverlayParsingError,
)
from treeforge.android.parsing.dtb.parser import (
    AndroidFdtParser,
    FdtParsingError,
)

__all__ = (
    "AndroidDtboOverlayParser",
    "AndroidFdtParser",
    "AndroidParsedDtboEntry",
    "DtboOverlayParsingError",
    "FdtParsingError",
    "ParsedDtboExternalFixup",
    "ParsedDtboExternalFixupLocation",
    "ParsedDtboFragmentTarget",
    "ParsedDtboLocalFixup",
    "ParsedDtboOverlayMetadata",
    "ParsedDtboSymbol",
    "ParsedFdt",
    "ParsedFdtHeader",
    "ParsedFdtNode",
    "ParsedFdtProperty",
    "ParsedFdtReservation",
)
