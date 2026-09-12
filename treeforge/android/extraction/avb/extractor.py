from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.avb.metadata import (
    AvbFooterStructure,
    AvbHashtreePhysicalStructure,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class AvbRegionExtractionError(
    RuntimeError,
):
    pass


class AvbRegionExtractor:
    """
    Materialize exact physical regions described by an AVB footer.
    """

    HASH_CHUNK_SIZE = (
        1024 * 1024
    )

    def extract(
        self,
        parent: ExtractedArtifact,
        structure: AvbFooterStructure,
        destination_root: Path,
        *,
        hashtree_structures: tuple[
            AvbHashtreePhysicalStructure,
            ...,
        ] = (),
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
            raise AvbRegionExtractionError(
                "AVB extraction parent must be a file"
            )

        if not isinstance(
            structure,
            AvbFooterStructure,
        ):
            raise TypeError(
                "structure must be an AvbFooterStructure"
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

        for layout in hashtree_structures:
            suffix = (
                ""
                if len(hashtree_structures) == 1
                else f"_{layout.descriptor_index}"
            )

            artifacts.append(
                self._extract_region(
                    parent=parent,
                    destination=(
                        destination_root
                        / f"avb_hashtree{suffix}"
                    ),
                    semantic_name=(
                        f"avb_hashtree{suffix}"
                    ),
                    offset=layout.tree_offset,
                    size=layout.tree_size,
                    extra_facts=(
                        ExtractionFact(
                            name="region_kind",
                            value="avb_hashtree",
                        ),
                        ExtractionFact(
                            name="descriptor_index",
                            value=layout.descriptor_index,
                        ),
                        ExtractionFact(
                            name="avb_image_size_bytes",
                            value=layout.image_size,
                        ),
                        ExtractionFact(
                            name="data_block_size_bytes",
                            value=layout.data_block_size,
                        ),
                        ExtractionFact(
                            name="hash_block_size_bytes",
                            value=layout.hash_block_size,
                        ),
                    ),
                )
            )

            if layout.fec_size:
                artifacts.append(
                    self._extract_region(
                        parent=parent,
                        destination=(
                            destination_root
                            / f"avb_fec{suffix}"
                        ),
                        semantic_name=(
                            f"avb_fec{suffix}"
                        ),
                        offset=layout.fec_offset,
                        size=layout.fec_size,
                        extra_facts=(
                            ExtractionFact(
                                name="region_kind",
                                value="avb_fec",
                            ),
                            ExtractionFact(
                                name="descriptor_index",
                                value=layout.descriptor_index,
                            ),
                            ExtractionFact(
                                name="avb_image_size_bytes",
                                value=layout.image_size,
                            ),
                            ExtractionFact(
                                name="fec_num_roots",
                                value=layout.fec_num_roots,
                            ),
                        ),
                    )
                )

        artifacts.extend(
            (
                self._extract_region(
                    parent=parent,
                    destination=(
                        destination_root
                        / "avb_vbmeta"
                    ),
                    semantic_name="avb_vbmeta",
                    offset=structure.vbmeta_offset,
                    size=structure.vbmeta_size,
                    extra_facts=(
                        ExtractionFact(
                            name="region_kind",
                            value="embedded_vbmeta",
                        ),
                        ExtractionFact(
                            name="avb_footer_version_major",
                            value=structure.version_major,
                        ),
                        ExtractionFact(
                            name="avb_footer_version_minor",
                            value=structure.version_minor,
                        ),
                    ),
                ),
                self._extract_region(
                    parent=parent,
                    destination=(
                        destination_root
                        / "avb_footer"
                    ),
                    semantic_name="avb_footer",
                    offset=structure.footer_offset,
                    size=structure.footer_size,
                    extra_facts=(
                        ExtractionFact(
                            name="region_kind",
                            value="avb_footer",
                        ),
                        ExtractionFact(
                            name="avb_footer_version_major",
                            value=structure.version_major,
                        ),
                        ExtractionFact(
                            name="avb_footer_version_minor",
                            value=structure.version_minor,
                        ),
                        ExtractionFact(
                            name="avb_original_image_size_bytes",
                            value=structure.original_image_size,
                        ),
                        ExtractionFact(
                            name="avb_vbmeta_offset_bytes",
                            value=structure.vbmeta_offset,
                        ),
                        ExtractionFact(
                            name="avb_vbmeta_size_bytes",
                            value=structure.vbmeta_size,
                        ),
                    ),
                ),
            )
        )

        return tuple(
            artifacts
        )

    def _extract_region(
        self,
        *,
        parent: ExtractedArtifact,
        destination: Path,
        semantic_name: str,
        offset: int,
        size: int,
        extra_facts: tuple[
            ExtractionFact,
            ...,
        ],
    ) -> ExtractedArtifact:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.unlink(
            missing_ok=True
        )

        digest = sha256()

        try:
            with parent.path.open(
                "rb"
            ) as source:
                source.seek(
                    offset
                )

                remaining = size

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
                            raise AvbRegionExtractionError(
                                "AVB region ended before declared size: "
                                f"{parent.path} {semantic_name}"
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

        if actual_size != size:
            destination.unlink(
                missing_ok=True
            )

            raise AvbRegionExtractionError(
                "AVB region size mismatch for "
                f"{semantic_name}: expected {size}, got {actual_size}"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=(
                ExtractionArtifactKind.FILE
            ),
            operation=(
                ExtractionOperation
                .AVB_REGION_EXTRACTION
            ),
            semantic_name=semantic_name,
            parent=parent,
            facts=(
                ExtractionFact(
                    name="offset_bytes",
                    value=offset,
                ),
                ExtractionFact(
                    name="declared_size_bytes",
                    value=size,
                ),
                *extra_facts,
            ),
            tool=ExtractionToolEvidence(
                name="treeforge-avb-region",
            ),
            content_sha256=(
                digest.hexdigest()
            ),
            size_bytes=actual_size,
        )
