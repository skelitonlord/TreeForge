from treeforge.android.format.filesystem import (
    FilesystemDetector,
    FilesystemType,
)
from treeforge.android.format.image import (
    ImageFormat,
    ImageFormatDetector,
)
from treeforge.android.format.compression import (
    COMPRESSION_PREFIX_SIZE,
    CompressionFormat,
    GZIP_MAGIC,
    LZ4_LEGACY_MAGIC,
    LZ4_MAGIC,
    LZMA_MAGIC,
    LZMA_XZ_MAGIC,
    ZSTD_MAGIC,
    detect_compression,
)


__all__ = [
    "COMPRESSION_PREFIX_SIZE",
    "FilesystemDetector",
    "FilesystemType",
    "GZIP_MAGIC",
    "ImageFormat",
    "ImageFormatDetector",
    "LZ4_LEGACY_MAGIC",
    "LZ4_MAGIC",
    "LZMA_MAGIC",
    "LZMA_XZ_MAGIC",
    "ZSTD_MAGIC",
    "CompressionFormat",
    "detect_compression",
]
