from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.runtime_property.model import (
    AndroidReconstructionRuntimePropertyRepresentation,
)
from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionRuntimePropertyContentSynthesizer:
    """
    Classify runtime-property Reconstruction representations for Source Content.

    A canonical runtime-property Reconstruction representation proves that a
    property key requires reconstruction, but it does not establish a literal
    source declaration, value, producer, property file, ownership domain, or
    destination.

    Therefore runtime-property Source Content must not invent ``key=value``
    text or any source-tree placement. Each admitted representation is retained
    as an explicit NOT_SOURCE_DECLARABLE Source Content unit until a later
    Reconstruction capability establishes a legitimate source-producing
    mechanism.
    """

    @staticmethod
    def synthesize(
        representation: AndroidReconstructionRuntimePropertyRepresentation,
    ) -> AndroidReconstructionSourceContent:
        if not isinstance(
            representation,
            AndroidReconstructionRuntimePropertyRepresentation,
        ):
            raise TypeError(
                "representation must be an "
                "AndroidReconstructionRuntimePropertyRepresentation"
            )

        return AndroidReconstructionSourceContent(
            content_id=(
                "source-content:runtime-property:"
                f"{representation.representation_id}"
            ),
            representation_id=representation.representation_id,
            media_kind=(
                AndroidReconstructionSourceContentMediaKind.PROPERTY
            ),
            status=(
                AndroidReconstructionSourceContentStatus
                .NOT_SOURCE_DECLARABLE
            ),
            contributing_obligation_ids=(
                representation.obligation_id,
            ),
        )

    @classmethod
    def synthesize_all(
        cls,
        representations: tuple[
            AndroidReconstructionRuntimePropertyRepresentation,
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
                    cls.synthesize(representation)
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

        if len(content_ids) != len(set(content_ids)):
            raise ValueError(
                "runtime-property source content identities "
                "must be unique"
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
                "runtime-property Source Content must contain "
                "exactly one unit per representation"
            )

        return result
