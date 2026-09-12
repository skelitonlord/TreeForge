from __future__ import annotations

import gzip
import lzma
import struct

import lz4.block
import lz4.frame
import zstandard

from treeforge.android.format.compression import (
    CompressionFormat,
    LZ4_LEGACY_MAGIC,
    detect_compression,
)


LZ4_LEGACY_BLOCK_SIZE = (
    8 * 1024 * 1024
)


class CompressionProcessor:
    """
    Generic physical decompression mechanism used by semantic Extraction
    materializers.

    This class does not decide which artifacts should be decompressed.
    Eligibility remains owned by the semantic materializer consuming it.
    """

    def decompress(
        self,
        data: bytes,
        compression: CompressionFormat,
    ) -> bytes:
        if not isinstance(
            data,
            bytes,
        ):
            raise TypeError(
                "data must be bytes"
            )

        if not isinstance(
            compression,
            CompressionFormat,
        ):
            raise TypeError(
                "compression must be a CompressionFormat"
            )

        if compression is CompressionFormat.GZIP:
            return gzip.decompress(
                data
            )

        if compression is CompressionFormat.LZ4:
            return lz4.frame.decompress(
                data
            )

        if compression is CompressionFormat.LZ4_LEGACY:
            return self._decompress_legacy_lz4(
                data
            )

        if compression is CompressionFormat.ZSTD:
            return (
                zstandard
                .ZstdDecompressor()
                .decompress(
                    data
                )
            )

        if compression is CompressionFormat.LZMA:
            try:
                return lzma.decompress(
                    data,
                    format=lzma.FORMAT_ALONE,
                )
            except lzma.LZMAError:
                return lzma.decompress(
                    data,
                    format=lzma.FORMAT_XZ,
                )

        if compression is CompressionFormat.NONE:
            return data

        raise NotImplementedError(
            "Unsupported compression format: "
            f"{compression}"
        )

    def process(
        self,
        data: bytes,
    ) -> tuple[
        CompressionFormat,
        bytes,
    ]:
        compression = (
            detect_compression(
                data
            )
        )

        return (
            compression,
            self.decompress(
                data,
                compression,
            ),
        )

    @staticmethod
    def _decompress_legacy_lz4(
        data: bytes,
    ) -> bytes:
        """
        Decompress a Linux-kernel legacy LZ4 stream.

        Legacy streams contain the four-byte magic followed by one or more
        little-endian compressed-size fields and raw LZ4 blocks.
        """

        if not data.startswith(
            LZ4_LEGACY_MAGIC
        ):
            raise ValueError(
                "Invalid legacy LZ4 magic."
            )

        offset = len(
            LZ4_LEGACY_MAGIC
        )

        output = bytearray()

        while offset < len(
            data
        ):
            if offset + 4 > len(data):
                raise ValueError(
                    "Incomplete legacy LZ4 block header."
                )

            compressed_size = (
                struct.unpack_from(
                    "<I",
                    data,
                    offset,
                )[0]
            )

            offset += 4

            if compressed_size == 0:
                break

            block_end = (
                offset
                + compressed_size
            )

            if block_end > len(data):
                raise ValueError(
                    "Incomplete legacy LZ4 block."
                )

            try:
                decompressed_block = (
                    lz4.block.decompress(
                        data[offset:block_end],
                        uncompressed_size=(
                            LZ4_LEGACY_BLOCK_SIZE
                        ),
                    )
                )
            except lz4.block.LZ4BlockError as error:
                raise ValueError(
                    "Invalid legacy LZ4 block."
                ) from error

            output.extend(
                decompressed_block
            )

            offset = block_end

        return bytes(
            output
        )
