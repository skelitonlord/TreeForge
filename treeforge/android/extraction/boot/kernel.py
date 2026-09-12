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


class KernelCompressionProcessorLike(
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


class KernelDecompressionError(
    RuntimeError,
):
    pass


class KernelDecompressor:
    """
    Materialize one boot-extracted kernel payload as its uncompressed image.

    Kernel semantic eligibility remains separate from generic compression
    mechanics.
    """

    def __init__(
        self,
        *,
        processor: KernelCompressionProcessorLike | None = None,
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
            raise KernelDecompressionError(
                "Unable to decompress kernel artifact: "
                f"{parent.path}"
            ) from error

        if compression is CompressionFormat.NONE:
            #
            # A boot component named kernel may already be an uncompressed
            # Linux Image. Do not create a false decompression derivation.
            #
            raise KernelDecompressionError(
                "kernel artifact is not compressed: "
                f"{parent.path}"
            )

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

            raise KernelDecompressionError(
                "Decompressed kernel size mismatch: "
                f"expected {len(decompressed_data)}, "
                f"got {actual_size}"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=ExtractionArtifactKind.FILE,
            operation=(
                ExtractionOperation
                .KERNEL_DECOMPRESSION
            ),
            semantic_name="kernel_image",
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
            raise KernelDecompressionError(
                "kernel parent must be a file"
            )

        if (
            parent.operation
            is not ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
        ):
            raise KernelDecompressionError(
                "kernel decompression requires "
                "a boot-component artifact"
            )

        if parent.semantic_name != "kernel":
            raise KernelDecompressionError(
                "kernel decompression requires "
                "semantic_name='kernel'"
            )
