"""
Generic embedded-ELF physical Extraction support.

The decoder identifies complete physically backed ELF byte ranges using only
intrinsic ELF structure. Container eligibility policy remains outside this
package.
"""

from treeforge.android.extraction.elf.decoder import (
    EmbeddedElfDecodeError,
    EmbeddedElfDecoder,
)
from treeforge.android.extraction.elf.extractor import (
    EmbeddedElfExtractionError,
    EmbeddedElfExtractor,
)
from treeforge.android.extraction.elf.model import (
    EmbeddedElfRange,
    EmbeddedElfStructure,
)

__all__ = [
    "EmbeddedElfDecodeError",
    "EmbeddedElfDecoder",
    "EmbeddedElfExtractionError",
    "EmbeddedElfExtractor",
    "EmbeddedElfRange",
    "EmbeddedElfStructure",
]
