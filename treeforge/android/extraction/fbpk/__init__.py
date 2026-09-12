"""
FBPK container extraction support.

FBPK decoding is structural only. Entry names and raw record fields are
preserved exactly as container evidence and are not assigned platform- or
device-specific semantics here.
"""

from treeforge.android.extraction.fbpk.model import (
    FbpkContainerStructure,
    FbpkEntry,
)
from treeforge.android.extraction.fbpk.decoder import (
    FbpkContainerDecoder,
    FbpkContainerDecodeError,
)
from treeforge.android.extraction.fbpk.extractor import (
    FbpkContainerExtractor,
    FbpkContainerExtractionError,
)

__all__ = (
    "FbpkContainerStructure",
    "FbpkEntry",
    "FbpkContainerDecoder",
    "FbpkContainerDecodeError",
    "FbpkContainerExtractor",
    "FbpkContainerExtractionError",
)
