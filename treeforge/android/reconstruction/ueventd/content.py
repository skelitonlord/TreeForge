from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)
from treeforge.android.reconstruction.ueventd.model import (
    AndroidReconstructionUeventdSourceRepresentation,
)
from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdRequirement,
    AndroidUniverseUeventdSubsystemRequirement,
)


@dataclass(frozen=True, slots=True)
class _AndroidUeventdRenderedLine:
    line_number: int
    obligation_id: str
    text: str


@dataclass(frozen=True, slots=True)
class AndroidReconstructionUeventdContentSynthesizer:
    """
    Synthesize deterministic UEVENTD source content from canonical
    Reconstruction representations.

    Only admitted Reconstruction work is rendered.

    Exact declaration text is selected mechanically from the canonical
    Universe source context using Parsing-established source-line identities.
    Semantic declaration fields are never reformatted into new source syntax.

    Subsystem declarations retain the exact source header plus all exact,
    ordered option lines belonging to the admitted subsystem declaration.

    Meaningful source lines Parsing could not classify remain unresolved
    source context. They are preserved without inventing semantic obligations.

    No Parsing reach-back, source-tree ownership, destination, filename,
    build-module, reconciliation, or materialization decision is made here.
    """

    @staticmethod
    def _source_line(
        *,
        raw_lines: tuple[str, ...],
        line_number: int,
        source_identity: str,
    ) -> str:
        if not isinstance(
            line_number,
            int,
        ):
            raise TypeError(
                "UEVENTD source line number must be an integer"
            )

        if (
            line_number < 1
            or line_number > len(raw_lines)
        ):
            raise ValueError(
                "UEVENTD canonical source line is outside "
                "the preserved source text: "
                f"source={source_identity!r}, "
                f"line={line_number}, "
                f"lines={len(raw_lines)}"
            )

        return raw_lines[
            line_number - 1
        ]

    @classmethod
    def synthesize(
        cls,
        representation: AndroidReconstructionUeventdSourceRepresentation,
    ) -> AndroidReconstructionSourceContent:
        if not isinstance(
            representation,
            AndroidReconstructionUeventdSourceRepresentation,
        ):
            raise TypeError(
                "representation must be an "
                "AndroidReconstructionUeventdSourceRepresentation"
            )

        raw_lines = tuple(
            representation
            .source_context
            .raw
            .splitlines()
        )

        rendered_lines: list[
            _AndroidUeventdRenderedLine
        ] = []

        contributing_obligation_ids: list[str] = []

        rendered_line_numbers: set[int] = set()

        for item in representation.requirement_work_items:
            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseUeventdRequirement,
            ):
                raise TypeError(
                    "UEVENTD source content requires exact "
                    "AndroidUniverseUeventdRequirement objects"
                )

            declaration = (
                requirement.declaration
            )

            declaration_line = (
                declaration.source_line
            )

            if (
                declaration_line
                in rendered_line_numbers
            ):
                raise ValueError(
                    "multiple admitted UEVENTD requirements "
                    "claim the same canonical source line: "
                    f"{representation.source_identity_key}:"
                    f"{declaration_line}"
                )

            rendered_lines.append(
                _AndroidUeventdRenderedLine(
                    line_number=declaration_line,
                    obligation_id=item.obligation_id,
                    text=cls._source_line(
                        raw_lines=raw_lines,
                        line_number=declaration_line,
                        source_identity=(
                            representation
                            .source_identity
                        ),
                    ),
                )
            )

            rendered_line_numbers.add(
                declaration_line
            )

            if isinstance(
                requirement,
                AndroidUniverseUeventdSubsystemRequirement,
            ):
                for option in declaration.options:
                    option_line = (
                        option.source_line
                    )

                    if (
                        option_line
                        in rendered_line_numbers
                    ):
                        raise ValueError(
                            "UEVENTD subsystem option source line "
                            "collides with another admitted lexical line: "
                            f"{representation.source_identity_key}:"
                            f"{option_line}"
                        )

                    rendered_lines.append(
                        _AndroidUeventdRenderedLine(
                            line_number=option_line,
                            obligation_id=(
                                item.obligation_id
                            ),
                            text=cls._source_line(
                                raw_lines=raw_lines,
                                line_number=option_line,
                                source_identity=(
                                    representation
                                    .source_identity
                                ),
                            ),
                        )
                    )

                    rendered_line_numbers.add(
                        option_line
                    )

            contributing_obligation_ids.append(
                item.obligation_id
            )

        unparsed_lines = (
            representation
            .source_context
            .unparsed_lines
        )

        unresolved_context_ids: list[str] = []

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

        for line in unparsed_lines:
            exact_source_line = (
                cls._source_line(
                    raw_lines=raw_lines,
                    line_number=line.source_line,
                    source_identity=(
                        representation
                        .source_identity
                    ),
                )
            )

            if exact_source_line != line.raw:
                raise ValueError(
                    "UEVENTD unparsed lexical evidence does not "
                    "match preserved canonical source text: "
                    f"{representation.source_identity_key}:"
                    f"{line.source_line}"
                )

            if (
                line.source_line
                in rendered_line_numbers
            ):
                raise ValueError(
                    "UEVENTD unparsed lexical evidence collides "
                    "with an admitted declaration line: "
                    f"{representation.source_identity_key}:"
                    f"{line.source_line}"
                )

            lexical_lines.append(
                (
                    line.source_line,
                    "unparsed",
                    line.raw,
                )
            )

            unresolved_context_ids.append(
                (
                    "ueventd-unparsed:"
                    f"{representation.source_identity_key}:"
                    f"{line.source_line}"
                )
            )

        lexical_lines.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
            )
        )

        if not lexical_lines:
            raise ValueError(
                "UEVENTD source content requires at least "
                "one admitted lexical line"
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
            if unresolved_context_ids
            else AndroidReconstructionSourceContentStatus
            .SYNTHESIZED
        )

        return AndroidReconstructionSourceContent(
            content_id=(
                "source-content:ueventd:"
                f"{representation.representation_id}"
            ),
            representation_id=(
                representation.representation_id
            ),
            media_kind=(
                AndroidReconstructionSourceContentMediaKind.UEVENTD
            ),
            status=status,
            text=text,
            contributing_obligation_ids=tuple(
                contributing_obligation_ids
            ),
            unresolved_context_ids=tuple(
                unresolved_context_ids
            ),
        )

    @classmethod
    def synthesize_all(
        cls,
        representations: tuple[
            AndroidReconstructionUeventdSourceRepresentation,
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
                "UEVENTD source content identities must be unique"
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
                "UEVENTD source content must contain exactly "
                "one content unit per representation"
            )

        return result
