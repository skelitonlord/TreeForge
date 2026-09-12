from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.init.model import (
    AndroidReconstructionInitSourceRepresentation,
)
from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.import_requirement import (
    AndroidUniverseInitImportRequirement,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)


@dataclass(frozen=True, slots=True)
class _AndroidInitRenderedStatement:
    line: int
    obligation_id: str
    requirement_id: str
    text: str


@dataclass(frozen=True, slots=True)
class AndroidReconstructionInitContentSynthesizer:
    """
    Synthesize canonical INIT source content from admitted Reconstruction work.

    The synthesizer consumes only one existing INIT Reconstruction
    representation. It never reparses source files, reads the filesystem,
    re-runs Universe reconciliation, or revives Planning NOT_APPLICABLE work.

    Exact parsed declaration syntax remains the rendering source. Statements
    are restored to canonical original source order using their preserved
    source locations.
    """

    @staticmethod
    def _render_import(
        *,
        obligation_id: str,
        requirement: AndroidUniverseInitImportRequirement,
    ) -> _AndroidInitRenderedStatement:
        declaration = requirement.declaration

        return _AndroidInitRenderedStatement(
            line=declaration.location.line,
            obligation_id=obligation_id,
            requirement_id=requirement.requirement_id,
            text=declaration.raw,
        )

    @staticmethod
    def _render_service(
        *,
        obligation_id: str,
        requirement: AndroidUniverseInitServiceRequirement,
    ) -> _AndroidInitRenderedStatement:
        service = requirement.service

        lines = [
            service.raw_header,
            *(
                option.raw
                for option in service.options
            ),
        ]

        return _AndroidInitRenderedStatement(
            line=service.location.line,
            obligation_id=obligation_id,
            requirement_id=requirement.requirement_id,
            text="\n".join(lines),
        )

    @staticmethod
    def _render_action(
        *,
        obligation_id: str,
        requirement: AndroidUniverseInitActionRequirement,
    ) -> _AndroidInitRenderedStatement:
        action = requirement.action

        lines = [
            action.raw_header,
            *(
                command.raw
                for command in action.commands
            ),
        ]

        return _AndroidInitRenderedStatement(
            line=action.location.line,
            obligation_id=obligation_id,
            requirement_id=requirement.requirement_id,
            text="\n".join(lines),
        )

    @classmethod
    def synthesize(
        cls,
        representation: AndroidReconstructionInitSourceRepresentation,
    ) -> AndroidReconstructionSourceContent:
        if not isinstance(
            representation,
            AndroidReconstructionInitSourceRepresentation,
        ):
            raise TypeError(
                "representation must be an "
                "AndroidReconstructionInitSourceRepresentation"
            )

        statements: list[
            _AndroidInitRenderedStatement
        ] = []

        for item in representation.import_work_items:
            requirement = item.obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseInitImportRequirement,
            ):
                raise TypeError(
                    "INIT import work must preserve an "
                    "AndroidUniverseInitImportRequirement"
                )

            statements.append(
                cls._render_import(
                    obligation_id=item.obligation_id,
                    requirement=requirement,
                )
            )

        for item in representation.service_work_items:
            requirement = item.obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseInitServiceRequirement,
            ):
                raise TypeError(
                    "INIT service work must preserve an "
                    "AndroidUniverseInitServiceRequirement"
                )

            statements.append(
                cls._render_service(
                    obligation_id=item.obligation_id,
                    requirement=requirement,
                )
            )

        for item in representation.action_work_items:
            requirement = item.obligation.requirement

            if not isinstance(
                requirement,
                AndroidUniverseInitActionRequirement,
            ):
                raise TypeError(
                    "INIT action work must preserve an "
                    "AndroidUniverseInitActionRequirement"
                )

            statements.append(
                cls._render_action(
                    obligation_id=item.obligation_id,
                    requirement=requirement,
                )
            )

        if not statements:
            raise ValueError(
                "INIT source content requires admitted "
                "Reconstruction statements"
            )

        ordered = tuple(
            sorted(
                statements,
                key=lambda statement: (
                    statement.line,
                    statement.requirement_id,
                    statement.obligation_id,
                ),
            )
        )

        if len(
            {
                statement.obligation_id
                for statement in ordered
            }
        ) != len(ordered):
            raise ValueError(
                "INIT source content contains duplicate "
                "obligation identities"
            )

        for statement in ordered:
            if (
                not isinstance(statement.text, str)
                or not statement.text
            ):
                raise ValueError(
                    "INIT admitted statement lacks preserved "
                    "renderable syntax"
                )

            if statement.line < 1:
                raise ValueError(
                    "INIT admitted statement lacks a positive "
                    "source line"
                )

        contributing_ids = tuple(
            statement.obligation_id
            for statement in ordered
        )

        unresolved_ids = tuple(
            sorted(
                outcome.obligation_id
                for outcome
                in representation.known_unresolved_outcomes
            )
        )

        group_ids = set(
            representation.source_group_obligation_ids
        )

        accounted_ids = (
            set(contributing_ids)
            | set(unresolved_ids)
        )

        if not accounted_ids.issubset(group_ids):
            raise ValueError(
                "INIT source content accounting escaped its "
                "canonical Planning source group"
            )

        excluded_ids = tuple(
            sorted(
                group_ids
                - accounted_ids
            )
        )

        status = (
            AndroidReconstructionSourceContentStatus
            .PARTIAL_UNRESOLVED
            if unresolved_ids
            else (
                AndroidReconstructionSourceContentStatus
                .SYNTHESIZED
            )
        )

        text = "\n\n".join(
            statement.text
            for statement in ordered
        )

        if not text.endswith("\n"):
            text += "\n"

        return AndroidReconstructionSourceContent(
            content_id=(
                "source-content:init-rc:"
                f"{representation.representation_id}"
            ),
            representation_id=(
                representation.representation_id
            ),
            media_kind=(
                AndroidReconstructionSourceContentMediaKind
                .INIT_RC
            ),
            status=status,
            text=text,
            contributing_obligation_ids=(
                contributing_ids
            ),
            excluded_obligation_ids=(
                excluded_ids
            ),
            unresolved_obligation_ids=(
                unresolved_ids
            ),
        )

    @classmethod
    def synthesize_all(
        cls,
        representations: tuple[
            AndroidReconstructionInitSourceRepresentation,
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

        if len(content_ids) != len(set(content_ids)):
            raise ValueError(
                "INIT source content identities must be unique"
            )

        return result
