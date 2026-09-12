from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.extraction.ufpk.model import (
    UfpkStructure,
)


class UfpkExtractionError(
    ValueError,
):
    pass


class UfpkExtractor:
    """
    Materialize the exact physical region owned by every validated UFPK
    descriptor-chain entry.
    """

    def extract(
        self,
        parent: ExtractedArtifact,
        structure: UfpkStructure,
        output_root: Path,
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

        if not isinstance(
            structure,
            UfpkStructure,
        ):
            raise TypeError(
                "structure must be a UfpkStructure"
            )

        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        data = parent.path.read_bytes()

        if len(data) != structure.physical_size:
            raise UfpkExtractionError(
                "UFPK physical size changed before materialization"
            )

        artifacts = []

        for descriptor in (
            structure.descriptors
        ):
            blob = data[
                descriptor.offset:
                descriptor.physical_end
            ]

            if (
                len(blob)
                != descriptor.physical_size
            ):
                raise UfpkExtractionError(
                    "UFPK descriptor physical extent changed "
                    "during materialization"
                )

            digest = sha256(
                blob
            ).hexdigest()

            destination = (
                output_root
                / (
                    f"{descriptor.index:03d}-"
                    f"{descriptor.identity}.bin"
                )
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
                    blob
                )
            except BaseException:
                destination.unlink(
                    missing_ok=True
                )
                raise

            if (
                destination.stat().st_size
                != descriptor.physical_size
            ):
                destination.unlink(
                    missing_ok=True
                )

                raise UfpkExtractionError(
                    "materialized UFPK descriptor size mismatch"
                )

            artifact = ExtractedArtifact(
                source=parent.source,
                path=destination,
                kind=ExtractionArtifactKind.FILE,
                operation=(
                    ExtractionOperation
                    .UFPK_DESCRIPTOR_EXTRACTION
                ),
                semantic_name=descriptor.identity,
                parent=parent,
                tool=ExtractionToolEvidence(
                    name="treeforge-ufpk"
                ),
                facts=(
                    ExtractionFact(
                        name="descriptor_index",
                        value=descriptor.index,
                    ),
                    ExtractionFact(
                        name="descriptor_kind",
                        value=descriptor.kind,
                    ),
                    ExtractionFact(
                        name="descriptor_offset",
                        value=descriptor.offset,
                    ),
                    ExtractionFact(
                        name="field_28",
                        value=descriptor.field_28,
                    ),
                    ExtractionFact(
                        name="next_offset",
                        value=descriptor.next_offset,
                    ),
                    ExtractionFact(
                        name="physical_end",
                        value=descriptor.physical_end,
                    ),
                    ExtractionFact(
                        name="physical_size_bytes",
                        value=descriptor.physical_size,
                    ),
                ),
                content_sha256=digest,
                size_bytes=descriptor.physical_size,
            )

            artifacts.append(
                artifact
            )

        return tuple(
            artifacts
        )
