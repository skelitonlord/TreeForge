from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from treeforge.android.extraction.fbpk.model import (
    FbpkContainerStructure,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class FbpkContainerExtractionError(
    RuntimeError,
):
    """
    Raised when an FBPK payload cannot be materialized exactly.
    """


class FbpkContainerExtractor:
    """
    Materialize physical FBPK payload ranges as canonical Extraction children.
    """

    COPY_CHUNK_SIZE = (
        1024 * 1024
    )

    def extract(
        self,
        parent: ExtractedArtifact,
        structure: FbpkContainerStructure,
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
            raise FbpkContainerExtractionError(
                "FBPK parent must be a file"
            )

        if not isinstance(
            structure,
            FbpkContainerStructure,
        ):
            raise TypeError(
                "structure must be an FbpkContainerStructure"
            )

        if not isinstance(
            destination_root,
            Path,
        ):
            raise TypeError(
                "destination_root must be a pathlib.Path"
            )

        destination_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        artifacts: list[
            ExtractedArtifact
        ] = []

        for entry in (
            structure.payload_entries
        ):
            safe_name = (
                self._safe_name(
                    entry.name
                )
            )

            destination = (
                destination_root
                / (
                    f"{entry.index:03d}-"
                    f"{safe_name}.bin"
                )
            )

            destination.unlink(
                missing_ok=True
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
                        entry.payload_offset
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
                                raise (
                                    FbpkContainerExtractionError(
                                        "FBPK payload ended before "
                                        "declared size: "
                                        f"entry={entry.index}, "
                                        f"name={entry.name!r}"
                                    )
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

            if (
                actual_size
                != entry.payload_size
            ):
                destination.unlink(
                    missing_ok=True
                )

                raise FbpkContainerExtractionError(
                    "FBPK payload size mismatch: "
                    f"entry={entry.index}, "
                    f"expected={entry.payload_size}, "
                    f"actual={actual_size}"
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
                        .FBPK_ENTRY_EXTRACTION
                    ),
                    semantic_name=(
                        entry.name
                    ),
                    parent=parent,
                    facts=(
                        ExtractionFact(
                            name="fbpk_version",
                            value=structure.version,
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
                            name="record_type",
                            value=entry.record_type,
                        ),
                        ExtractionFact(
                            name="payload_offset_bytes",
                            value=entry.payload_offset,
                        ),
                        ExtractionFact(
                            name="payload_size_bytes",
                            value=entry.payload_size,
                        ),
                        *(
                            (
                                ExtractionFact(
                                    name="flags",
                                    value=entry.flags,
                                ),
                            )
                            if entry.flags is not None
                            else ()
                        ),
                        *tuple(
                            ExtractionFact(
                                name=(
                                    f"raw_tail_u32_{index}"
                                ),
                                value=value,
                            )
                            for index, value
                            in enumerate(
                                entry.raw_tail
                            )
                        ),
                    ),
                    tool=(
                        ExtractionToolEvidence(
                            name=(
                                "treeforge-fbpk-container"
                            ),
                        )
                    ),
                    content_sha256=(
                        digest.hexdigest()
                    ),
                    size_bytes=(
                        actual_size
                    ),
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
            or "entry"
        )
