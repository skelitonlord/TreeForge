from __future__ import annotations

from enum import StrEnum


class CompressionFormat(
    StrEnum,
):
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    LZ4_LEGACY = "lz4_legacy"
    ZSTD = "zstd"
    LZMA = "lzma"


GZIP_MAGIC = bytes.fromhex(
    "1f8b"
)

LZ4_MAGIC = bytes.fromhex(
    "04224d18"
)

LZ4_LEGACY_MAGIC = bytes.fromhex(
    "02214c18"
)

ZSTD_MAGIC = bytes.fromhex(
    "28b52ffd"
)

LZMA_MAGIC = (
    b"\x5d\x00\x00\x80\x00"
)

LZMA_XZ_MAGIC = (
    b"\xfd7zXZ"
)

COMPRESSION_PREFIX_SIZE = max(
    len(GZIP_MAGIC),
    len(LZ4_MAGIC),
    len(LZ4_LEGACY_MAGIC),
    len(ZSTD_MAGIC),
    len(LZMA_MAGIC),
    len(LZMA_XZ_MAGIC),
)


def detect_compression(
    data: bytes,
) -> CompressionFormat:
    """
    Identify a supported compression format from leading payload bytes.

    This is generic structural format detection. It assigns no Android
    semantic meaning to the payload.
    """

    if not isinstance(
        data,
        bytes,
    ):
        raise TypeError(
            "data must be bytes"
        )

    if not data:
        return CompressionFormat.NONE

    if data.startswith(
        GZIP_MAGIC
    ):
        return CompressionFormat.GZIP

    if data.startswith(
        LZ4_MAGIC
    ):
        return CompressionFormat.LZ4

    if data.startswith(
        LZ4_LEGACY_MAGIC
    ):
        return CompressionFormat.LZ4_LEGACY

    if data.startswith(
        ZSTD_MAGIC
    ):
        return CompressionFormat.ZSTD

    if (
        data.startswith(
            LZMA_MAGIC
        )
        or data.startswith(
            LZMA_XZ_MAGIC
        )
    ):
        return CompressionFormat.LZMA

    return CompressionFormat.NONE
