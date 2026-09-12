from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.fstab.model import (
    AndroidReconstructionFstabSourceRepresentation,
)
from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)
from treeforge.android.universe.fstab.model import (
    AndroidUniverseFstabRequirement,
)


@dataclass(frozen=True, slots=True)
class _AndroidFstabRenderedLine:
    line_number: int
    obligation_id: str
    text: str


@dataclass(frozen=True, slots=True)
class AndroidReconstructionFstabContentSynthesizer:
    """
    Synthesize deterministic fstab source content from canonical
    Reconstruction representations.

    Only admitted Reconstruction work is rendered. Exact lexical fstab lines
    come from the Parsing declaration retained by the canonical Universe
    requirement.

    Source-context unparsed lines are preserved in source order when present,
    but remain explicitly unresolved lexical context rather than being
    interpreted as semantic fstab requirements.

    No source-tree ownership, destination, filename, build-module, or
    materialization decisions are made here.
    """

    @staticmethod
    def synthesize(
        representation: AndroidReconstructionFstabSourceRepresentation,
    ) -> AndroidReconstructionSourceContent:
        if not isinstance(
            representation,
            AndroidReconstructionFstabSourceRepresentation,
        ):
            raise TypeError(
                "representation must be an "
                "AndroidReconstructionFstabSourceRepresentation"
            )

        rendered_lines: list[
            _AndroidFstabRenderedLine
        ] = []

        contributing_obligation_ids = []

        for item in representation.entry_work_items:
            requirement = item.obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseFstabRequirement,
            ):
                raise TypeError(
                    "fstab source content requires exact "
                    "AndroidUniverseFstabRequirement objects"
                )

            declaration = requirement.declaration

            rendered_lines.append(
                _AndroidFstabRenderedLine(
                    line_number=declaration.line_number,
                    obligation_id=item.obligation_id,
                    text=declaration.raw,
                )
            )

            contributing_obligation_ids.append(
                item.obligation_id
            )

        unparsed_lines = (
            representation
            .source_context
            .unparsed_lines
        )

        lexical_lines: list[
            tuple[int, str, str]
        ] = [
            (
                line.line_number,
                "declaration",
                line.text,
            )
            for line in rendered_lines
        ]

        lexical_lines.extend(
            (
                line.line_number,
                "unparsed",
                line.raw,
            )
            for line in unparsed_lines
        )

        lexical_lines.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
            )
        )

        text = (
            "\n".join(
                line_text
                for _, _, line_text
                in lexical_lines
            )
            + "\n"
        )

        status = (
            AndroidReconstructionSourceContentStatus
            .PARTIAL_UNRESOLVED
            if unparsed_lines
            else AndroidReconstructionSourceContentStatus
            .SYNTHESIZED
        )

        unresolved_ids = tuple(
            (
                "fstab-unparsed:"
                f"{representation.source_identity_key}:"
                f"{line.line_number}"
            )
            for line in unparsed_lines
        )

        return AndroidReconstructionSourceContent(
            content_id=(
                "source-content:fstab:"
                f"{representation.representation_id}"
            ),
            representation_id=(
                representation.representation_id
            ),
            media_kind=(
                AndroidReconstructionSourceContentMediaKind.FSTAB
            ),
            status=status,
            text=text,
            contributing_obligation_ids=tuple(
                contributing_obligation_ids
            ),
            unresolved_context_ids=unresolved_ids,
        )

    @classmethod
    def synthesize_all(
        cls,
        representations: tuple[
            AndroidReconstructionFstabSourceRepresentation,
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
                    for representation in representations
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

        if len(content_ids) != len(
            set(content_ids)
        ):
            raise ValueError(
                "fstab source content identities must be unique"
            )

        representation_ids = tuple(
            content.representation_id
            for content in result
        )

        if len(representation_ids) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "fstab source content must contain exactly one "
                "content unit per representation"
            )

        return result
