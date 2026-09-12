from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)
from treeforge.android.reconstruction.vintf.model import (
    AndroidReconstructionVintfDocumentRepresentation,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionVintfContentSynthesizer:
    """
    Preserve exact VINTF XML content from the canonical Reconstruction
    document representation.

    Android Device Universe retains the exact ParsedAndroidVintfSource and
    ParsedVintfDocument identities. ParsedVintfDocument.raw is therefore the
    canonical original XML text for this admitted document.

    Source Content does not serialize the immutable XML model or regenerate
    XML from semantic VINTF fields. Doing so could normalize formatting,
    whitespace, comments, namespace spelling, or other lexical details.

    Uninterpreted VINTF elements and attributes remain semantic coverage debt
    owned by Universe, but do not make the source content partial because the
    exact original XML containing them is preserved unchanged.

    No Parsing reach-back, applicability reconciliation, ownership,
    destination, filename, build-module, or materialization decision occurs
    here.
    """

    @staticmethod
    def synthesize(
        representation: AndroidReconstructionVintfDocumentRepresentation,
    ) -> AndroidReconstructionSourceContent:
        if not isinstance(
            representation,
            AndroidReconstructionVintfDocumentRepresentation,
        ):
            raise TypeError(
                "representation must be an "
                "AndroidReconstructionVintfDocumentRepresentation"
            )

        raw = (
            representation
            .requirement
            .parsed
            .raw
        )

        if not isinstance(
            raw,
            str,
        ):
            raise TypeError(
                "canonical VINTF raw source must be a string"
            )

        if not raw:
            raise ValueError(
                "canonical VINTF raw source must not be empty"
            )

        return AndroidReconstructionSourceContent(
            content_id=(
                "source-content:vintf:"
                f"{representation.representation_id}"
            ),
            representation_id=(
                representation.representation_id
            ),
            media_kind=(
                AndroidReconstructionSourceContentMediaKind.VINTF_XML
            ),
            status=(
                AndroidReconstructionSourceContentStatus
                .PRESERVED_EXACT
            ),
            text=raw,
            contributing_obligation_ids=(
                representation.obligation_id,
            ),
        )

    @classmethod
    def synthesize_all(
        cls,
        representations: tuple[
            AndroidReconstructionVintfDocumentRepresentation,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionSourceContent,
        ...,
    ]:
        if not isinstance(
            representations,
            tuple,
        ):
            raise TypeError(
                "representations must be a tuple"
            )

        result = tuple(
            sorted(
                (
                    cls.synthesize(
                        representation
                    )
                    for representation
                    in representations
                ),
                key=lambda content: (
                    content.representation_id,
                    content.content_id,
                ),
            )
        )

        content_ids = tuple(
            content.content_id
            for content in result
        )

        if len(
            content_ids
        ) != len(
            set(content_ids)
        ):
            raise ValueError(
                "VINTF source content identities must be unique"
            )

        representation_ids = tuple(
            content.representation_id
            for content in result
        )

        if len(
            representation_ids
        ) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "VINTF source content must contain exactly "
                "one content unit per document representation"
            )

        return result
