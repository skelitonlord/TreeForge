from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.dtbo.decoder import (
    DtboImageDecoder,
    DtboTableImage,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class DtboEntryExtractionError(
    RuntimeError,
):
    """
    Raised when physical DTBO entry materialization fails.
    """


class DtboEntryExtractor:
    """
    Materialize every physical DT payload from one Android DT table image.
    """

    HASH_CHUNK_SIZE = (
        1024 * 1024
    )

    def __init__(
        self,
        *,
        decoder: DtboImageDecoder | None = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else DtboImageDecoder()
        )

    @property
    def decoder(
        self,
    ) -> DtboImageDecoder:
        return self._decoder

    def extract(
        self,
        parent: ExtractedArtifact,
        destination_root: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        self._validate_parent(
            parent
        )

        structure = (
            self._decoder.decode(
                parent.path
            )
        )

        self._validate_destination(
            destination_root
        )

        destination_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        artifacts: list[
            ExtractedArtifact
        ] = []

        for entry in structure.entries:
            destination = (
                destination_root
                / f"entry_{entry.index:03d}.dtb"
            )

            destination.unlink(
                missing_ok=True
            )

            try:
                with parent.path.open(
                    "rb"
                ) as source:
                    source.seek(
                        entry.dt_offset
                    )

                    remaining = (
                        entry.dt_size
                    )

                    with destination.open(
                        "wb"
                    ) as output:
                        while remaining:
                            chunk = source.read(
                                min(
                                    self.HASH_CHUNK_SIZE,
                                    remaining,
                                )
                            )

                            if not chunk:
                                raise DtboEntryExtractionError(
                                    "DTBO entry ended before its "
                                    "declared size: "
                                    f"index={entry.index}"
                                )

                            output.write(
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
                != entry.dt_size
            ):
                destination.unlink(
                    missing_ok=True
                )

                raise DtboEntryExtractionError(
                    "DTBO entry size mismatch: "
                    f"index={entry.index}, "
                    f"expected={entry.dt_size}, "
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
                        .DTBO_ENTRY_EXTRACTION
                    ),
                    semantic_name=(
                        f"dtbo_entry_{entry.index:03d}"
                    ),
                    parent=parent,
                    facts=self._facts_for_entry(
                        structure,
                        entry.index,
                    ),
                    tool=ExtractionToolEvidence(
                        name="treeforge-dtbo-container",
                    ),
                    content_sha256=(
                        self._sha256_file(
                            destination
                        )
                    ),
                    size_bytes=actual_size,
                )
            )

        return tuple(
            artifacts
        )

    @staticmethod
    def _facts_for_entry(
        structure: DtboTableImage,
        index: int,
    ) -> tuple[
        ExtractionFact,
        ...,
    ]:
        entry = (
            structure.entries[
                index
            ]
        )

        header = (
            structure.header
        )

        return (
            ExtractionFact(
                name="entry_index",
                value=entry.index,
            ),
            ExtractionFact(
                name="offset_bytes",
                value=entry.dt_offset,
            ),
            ExtractionFact(
                name="declared_size_bytes",
                value=entry.dt_size,
            ),
            ExtractionFact(
                name="dtbo_id",
                value=entry.id,
            ),
            ExtractionFact(
                name="dtbo_rev",
                value=entry.rev,
            ),
            ExtractionFact(
                name="dtbo_custom_0",
                value=entry.custom[0],
            ),
            ExtractionFact(
                name="dtbo_custom_1",
                value=entry.custom[1],
            ),
            ExtractionFact(
                name="dtbo_custom_2",
                value=entry.custom[2],
            ),
            ExtractionFact(
                name="dtbo_custom_3",
                value=entry.custom[3],
            ),
            ExtractionFact(
                name="dtbo_table_version",
                value=header.version,
            ),
            ExtractionFact(
                name="dtbo_page_size_bytes",
                value=header.page_size,
            ),
            ExtractionFact(
                name="dtbo_table_total_size_bytes",
                value=header.total_size,
            ),
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
            raise DtboEntryExtractionError(
                "DTBO extraction parent must be a file"
            )

    @staticmethod
    def _validate_destination(
        destination: Path,
    ) -> None:
        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        if (
            destination.exists()
            and not destination.is_dir()
        ):
            raise NotADirectoryError(
                destination
            )

    @classmethod
    def _sha256_file(
        cls,
        path: Path,
    ) -> str:
        digest = sha256()

        with path.open(
            "rb"
        ) as stream:
            while True:
                chunk = stream.read(
                    cls.HASH_CHUNK_SIZE
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return digest.hexdigest()
