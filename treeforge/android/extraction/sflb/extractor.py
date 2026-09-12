from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.extraction.sflb.model import (
    EmbeddedSflbStructure,
)


class SflbContainerExtractionError(
    RuntimeError,
):
    """
    Raised when an SFLB resource cannot be materialized exactly.
    """


class SflbContainerExtractor:
    """
    Materialize structurally decoded SFLB resources as canonical children.
    """

    COPY_CHUNK_SIZE = (
        1024 * 1024
    )

    def extract(
        self,
        parent: ExtractedArtifact,
        structure: EmbeddedSflbStructure,
        destination_root: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
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
            raise SflbContainerExtractionError(
                "SFLB parent must be a file"
            )

        if not isinstance(
            structure,
            EmbeddedSflbStructure,
        ):
            raise TypeError(
                "structure must be an EmbeddedSflbStructure"
            )

        if structure.source != parent.path:
            raise SflbContainerExtractionError(
                "SFLB structure source does not match parent artifact"
            )

        if not isinstance(
            destination_root,
            Path,
        ):
            raise TypeError(
                "destination_root must be a pathlib.Path"
            )

        artifacts: list[
            ExtractedArtifact
        ] = []

        for container in structure.containers:
            container_root = (
                destination_root
                / f"{container.index:03d}"
            )

            container_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            for entry in container.entries:
                safe_name = self._safe_name(
                    entry.name
                )

                destination = (
                    container_root
                    / (
                        f"{entry.index:03d}-"
                        f"{safe_name}"
                    )
                )

                destination.unlink(
                    missing_ok=True
                )

                absolute_payload_offset = (
                    container.offset_bytes
                    + entry.payload_offset
                )

                digest = sha256()

                remaining = (
                    entry.payload_size
                )

                try:
                    with parent.path.open(
                        "rb"
                    ) as source:
                        source.seek(
                            absolute_payload_offset
                        )

                        with destination.open(
                            "wb"
                        ) as output:
                            while remaining:
                                chunk = source.read(
                                    min(
                                        self.COPY_CHUNK_SIZE,
                                        remaining,
                                    )
                                )

                                if not chunk:
                                    raise SflbContainerExtractionError(
                                        "SFLB payload ended before "
                                        "declared size"
                                    )

                                output.write(
                                    chunk
                                )

                                digest.update(
                                    chunk
                                )

                                remaining -= len(
                                    chunk
                                )

                except BaseException:
                    destination.unlink(
                        missing_ok=True
                    )
                    raise

                actual_size = (
                    destination.stat().st_size
                )

                if actual_size != entry.payload_size:
                    destination.unlink(
                        missing_ok=True
                    )

                    raise SflbContainerExtractionError(
                        "SFLB payload size mismatch"
                    )

                artifacts.append(
                    ExtractedArtifact(
                        source=parent.source,
                        path=destination,
                        kind=(
                            ExtractionArtifactKind.FILE
                        ),
                        operation=(
                            ExtractionOperation
                            .SFLB_ENTRY_EXTRACTION
                        ),
                        semantic_name=(
                            entry.name
                        ),
                        parent=parent,
                        facts=(
                            ExtractionFact(
                                name="sflb_container_index",
                                value=container.index,
                            ),
                            ExtractionFact(
                                name="sflb_container_offset_bytes",
                                value=container.offset_bytes,
                            ),
                            ExtractionFact(
                                name="sflb_container_span_bytes",
                                value=container.span_bytes,
                            ),
                            ExtractionFact(
                                name="sflb_version",
                                value=container.version,
                            ),
                            ExtractionFact(
                                name="sflb_entry_count",
                                value=container.entry_count,
                            ),
                            ExtractionFact(
                                name="sflb_secondary_count",
                                value=container.secondary_count,
                            ),
                            ExtractionFact(
                                name="entry_index",
                                value=entry.index,
                            ),
                            ExtractionFact(
                                name="record_offset_bytes",
                                value=entry.record_offset,
                            ),
                            ExtractionFact(
                                name="payload_offset_bytes",
                                value=entry.payload_offset,
                            ),
                            ExtractionFact(
                                name="absolute_payload_offset_bytes",
                                value=absolute_payload_offset,
                            ),
                            ExtractionFact(
                                name="payload_size_bytes",
                                value=entry.payload_size,
                            ),
                            ExtractionFact(
                                name="opaque_word",
                                value=entry.opaque_word,
                            ),
                            ExtractionFact(
                                name="flags",
                                value=entry.flags,
                            ),
                            *tuple(
                                ExtractionFact(
                                    name=f"raw_header_tail_u32_{index}",
                                    value=value,
                                )
                                for index, value
                                in enumerate(
                                    container.raw_header_tail
                                )
                            ),
                        ),
                        tool=(
                            ExtractionToolEvidence(
                                name=(
                                    "treeforge-sflb-container"
                                ),
                            )
                        ),
                        content_sha256=(
                            digest.hexdigest()
                        ),
                        size_bytes=actual_size,
                    )
                )

        return tuple(
            artifacts
        )

    @staticmethod
    def _safe_name(
        value: str,
    ) -> str:
        safe = re.sub(
            r"[^A-Za-z0-9._-]+",
            "_",
            value,
        ).strip(
            "._-"
        )

        return (
            safe
            or "resource"
        )
