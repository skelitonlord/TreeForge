from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.elf.model import (
    EmbeddedElfStructure,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class EmbeddedElfExtractionError(
    RuntimeError,
):
    """
    Raised when a structurally validated embedded ELF cannot be materialized
    exactly.
    """


class EmbeddedElfExtractor:
    """
    Materialize structurally validated embedded ELF ranges as canonical
    Extraction children.
    """

    COPY_CHUNK_SIZE = (
        1024 * 1024
    )

    def extract(
        self,
        parent: ExtractedArtifact,
        structure: EmbeddedElfStructure,
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
            raise EmbeddedElfExtractionError(
                "embedded ELF parent must be a file"
            )

        if not isinstance(
            structure,
            EmbeddedElfStructure,
        ):
            raise TypeError(
                "structure must be an EmbeddedElfStructure"
            )

        if structure.source != parent.path:
            raise ValueError(
                "embedded ELF structure source must match parent artifact"
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

        for elf_range in structure.ranges:
            destination = (
                destination_root
                / f"elf_{elf_range.index:03d}.elf"
            )

            destination.unlink(
                missing_ok=True
            )

            digest = sha256()

            remaining = (
                elf_range.size_bytes
            )

            try:
                with parent.path.open(
                    "rb"
                ) as source:
                    source.seek(
                        elf_range.offset_bytes
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
                                raise EmbeddedElfExtractionError(
                                    "embedded ELF ended before "
                                    "its structural extent: "
                                    f"index={elf_range.index}"
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

            if actual_size != elf_range.size_bytes:
                destination.unlink(
                    missing_ok=True
                )

                raise EmbeddedElfExtractionError(
                    "embedded ELF size mismatch: "
                    f"index={elf_range.index}, "
                    f"expected={elf_range.size_bytes}, "
                    f"actual={actual_size}"
                )

            with destination.open(
                "rb"
            ) as stream:
                magic = stream.read(
                    4
                )

            if magic != b"\x7fELF":
                destination.unlink(
                    missing_ok=True
                )

                raise EmbeddedElfExtractionError(
                    "materialized embedded ELF lost ELF magic: "
                    f"index={elf_range.index}"
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
                        .EMBEDDED_ELF_EXTRACTION
                    ),
                    semantic_name=(
                        f"embedded_elf_{elf_range.index:03d}"
                    ),
                    parent=parent,
                    facts=(
                        ExtractionFact(
                            name="embedded_index",
                            value=elf_range.index,
                        ),
                        ExtractionFact(
                            name="offset_bytes",
                            value=elf_range.offset_bytes,
                        ),
                        ExtractionFact(
                            name="size_bytes",
                            value=elf_range.size_bytes,
                        ),
                        ExtractionFact(
                            name="elf_class",
                            value=elf_range.elf_class,
                        ),
                        ExtractionFact(
                            name="elf_encoding",
                            value=elf_range.encoding,
                        ),
                        ExtractionFact(
                            name="elf_type",
                            value=elf_range.elf_type,
                        ),
                        ExtractionFact(
                            name="elf_machine",
                            value=elf_range.machine,
                        ),
                        ExtractionFact(
                            name="elf_version",
                            value=elf_range.elf_version,
                        ),
                        ExtractionFact(
                            name="entry_point",
                            value=elf_range.entry_point,
                        ),
                        ExtractionFact(
                            name="program_header_count",
                            value=(
                                elf_range
                                .program_header_count
                            ),
                        ),
                        ExtractionFact(
                            name="section_header_count",
                            value=(
                                elf_range
                                .section_header_count
                            ),
                        ),
                    ),
                    tool=(
                        ExtractionToolEvidence(
                            name=(
                                "treeforge-embedded-elf"
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
