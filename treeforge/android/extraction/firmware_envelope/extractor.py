from __future__ import annotations

from pathlib import Path

from treeforge.android.extraction.firmware_envelope.model import (
    FirmwareEnvelopeStructure,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class FirmwareEnvelopeExtractionError(
    ValueError,
):
    pass


class FirmwareEnvelopeExtractor:
    """
    Materialize the exact verified payload of one firmware envelope.
    """

    def extract(
        self,
        parent: ExtractedArtifact,
        structure: FirmwareEnvelopeStructure,
        destination: Path,
    ) -> ExtractedArtifact:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if not isinstance(
            structure,
            FirmwareEnvelopeStructure,
        ):
            raise TypeError(
                "structure must be a FirmwareEnvelopeStructure"
            )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        data = parent.path.read_bytes()

        payload_end = (
            structure.payload_offset
            + structure.payload_size
        )

        payload = data[
            structure.payload_offset:
            payload_end
        ]

        if len(payload) != structure.payload_size:
            raise FirmwareEnvelopeExtractionError(
                "firmware payload size changed during materialization"
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
                payload
            )
        except BaseException:
            destination.unlink(
                missing_ok=True
            )
            raise

        actual_size = (
            destination.stat().st_size
        )

        if actual_size != structure.payload_size:
            destination.unlink(
                missing_ok=True
            )

            raise FirmwareEnvelopeExtractionError(
                "materialized firmware payload size mismatch"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=ExtractionArtifactKind.FILE,
            operation=(
                ExtractionOperation
                .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
            ),
            semantic_name=structure.identity,
            parent=parent,
            tool=ExtractionToolEvidence(
                name="treeforge-firmware-envelope"
            ),
            facts=(
                ExtractionFact(
                    name="firmware_identity",
                    value=structure.identity,
                ),
                ExtractionFact(
                    name="header_offset",
                    value=structure.header_offset,
                ),
                ExtractionFact(
                    name="field_04",
                    value=structure.field_04,
                ),
                ExtractionFact(
                    name="field_08",
                    value=structure.field_08,
                ),
                ExtractionFact(
                    name="field_10",
                    value=structure.field_10,
                ),
                ExtractionFact(
                    name="payload_offset",
                    value=structure.payload_offset,
                ),
                ExtractionFact(
                    name="payload_size_bytes",
                    value=structure.payload_size,
                ),
                ExtractionFact(
                    name="payload_sha256",
                    value=structure.payload_sha256,
                ),
            ),
            content_sha256=structure.payload_sha256,
            size_bytes=actual_size,
        )
