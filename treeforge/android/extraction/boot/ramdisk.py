from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Protocol

from treeforge.android.extraction.compression.processor import (
    CompressionProcessor,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.format.compression import (
    CompressionFormat,
)


class CompressionProcessorLike(
    Protocol,
):
    def process(
        self,
        data: bytes,
    ) -> tuple[
        CompressionFormat,
        bytes,
    ]:
        ...


class RamdiskDecompressionError(
    RuntimeError,
):
    pass


class RamdiskDecompressor:
    """
    Materialize one canonical ramdisk payload as an uncompressed CPIO
    artifact.

    Ramdisk owns semantic eligibility and output identity. Generic compression
    detection and physical decompression are delegated to CompressionProcessor.
    """

    def __init__(
        self,
        *,
        processor: CompressionProcessorLike | None = None,
    ) -> None:
        self._processor = (
            processor
            if processor is not None
            else CompressionProcessor()
        )

    def decompress(
        self,
        parent: ExtractedArtifact,
        destination: Path,
    ) -> ExtractedArtifact:
        self._validate_parent(
            parent
        )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        if (
            destination.exists()
            and destination.is_dir()
        ):
            raise IsADirectoryError(
                destination
            )

        compressed_data = (
            parent.path.read_bytes()
        )

        try:
            (
                compression,
                decompressed_data,
            ) = self._processor.process(
                compressed_data
            )
        except Exception as error:
            raise RamdiskDecompressionError(
                "Unable to decompress ramdisk artifact: "
                f"{parent.path}"
            ) from error

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.unlink(
            missing_ok=True
        )

        try:
            destination.write_bytes(
                decompressed_data
            )
        except BaseException:
            destination.unlink(
                missing_ok=True
            )
            raise

        actual_size = (
            destination.stat().st_size
        )

        if actual_size != len(
            decompressed_data
        ):
            destination.unlink(
                missing_ok=True
            )

            raise RamdiskDecompressionError(
                "Decompressed ramdisk size mismatch: "
                f"expected {len(decompressed_data)}, "
                f"got {actual_size}"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=ExtractionArtifactKind.FILE,
            operation=(
                ExtractionOperation
                .RAMDISK_DECOMPRESSION
            ),
            semantic_name="ramdisk_cpio",
            parent=parent,
            facts=(
                ExtractionFact(
                    name="compression",
                    value=compression.value,
                ),
                ExtractionFact(
                    name="compressed_size_bytes",
                    value=len(
                        compressed_data
                    ),
                ),
                ExtractionFact(
                    name="decompressed_size_bytes",
                    value=actual_size,
                ),
            ),
            tool=ExtractionToolEvidence(
                name="treeforge-compression-processor",
            ),
            content_sha256=(
                sha256(
                    decompressed_data
                ).hexdigest()
            ),
            size_bytes=actual_size,
        )

    @staticmethod
    def _validate_parent(
        parent: ExtractedArtifact,
    ) -> None:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise RamdiskDecompressionError(
                "ramdisk parent must be a file"
            )

        if (
            parent.operation
            is not ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
        ):
            raise RamdiskDecompressionError(
                "ramdisk decompression requires "
                "a boot-component artifact"
            )

        if parent.semantic_name != "ramdisk":
            raise RamdiskDecompressionError(
                "ramdisk decompression requires "
                "semantic_name='ramdisk'"
            )
