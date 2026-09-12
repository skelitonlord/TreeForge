from __future__ import annotations

from dataclasses import dataclass
import re

from treeforge.android.reconstruction_ownership.source.model import (
    AndroidSourceReachedFile,
    AndroidSourceRelationshipApplicability,
    AndroidSourceRepositoryLineage,
)


_PRODUCT_PACKAGES_ASSIGNMENT_RE = re.compile(
    r"""
    ^\s*
    (?P<variable>
        PRODUCT_PACKAGES
        (?:_[A-Za-z0-9_]+)?
    )
    \s*
    (?P<operator>
        \+=
        |-=
        |:=
        |\?=
        |=
    )
    \s*
    (?P<body>.*)
    $
    """,
    re.VERBOSE | re.DOTALL,
)

_CONDITIONAL_START_RE = re.compile(
    r"^\s*(?:ifeq|ifneq|ifdef|ifndef)\b"
)

_CONDITIONAL_END_RE = re.compile(
    r"^\s*endif\b"
)

_LITERAL_MODULE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.+@-]*$"
)


@dataclass(frozen=True, slots=True)
class AndroidSourceProductModuleConsumption:
    """
    One literal module token declared by a lineage-reachable PRODUCT_PACKAGES
    assignment.

    This is source/product declaration evidence, not a conclusion that the
    module is present in the final target product.

    assignment_operator is preserved because +=, =, :=, ?=, and -= do not
    have interchangeable Make semantics.
    """

    reached_file: AndroidSourceReachedFile

    module_name: str
    variable_name: str
    assignment_operator: str

    evidence_line: int
    applicability: AndroidSourceRelationshipApplicability

    raw_expression: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.reached_file,
            AndroidSourceReachedFile,
        ):
            raise TypeError(
                "reached_file must be an AndroidSourceReachedFile"
            )

        for field_name, value in (
            (
                "module_name",
                self.module_name,
            ),
            (
                "variable_name",
                self.variable_name,
            ),
            (
                "assignment_operator",
                self.assignment_operator,
            ),
            (
                "raw_expression",
                self.raw_expression,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not _LITERAL_MODULE_RE.fullmatch(
            self.module_name
        ):
            raise ValueError(
                "module_name must be an exact literal module token"
            )

        if not (
            self.variable_name == "PRODUCT_PACKAGES"
            or self.variable_name.startswith(
                "PRODUCT_PACKAGES_"
            )
        ):
            raise ValueError(
                "variable_name must be PRODUCT_PACKAGES "
                "or a PRODUCT_PACKAGES_* variable"
            )

        if self.assignment_operator not in (
            "+=",
            "-=",
            ":=",
            "?=",
            "=",
        ):
            raise ValueError(
                "unsupported PRODUCT_PACKAGES assignment operator"
            )

        if (
            not isinstance(
                self.evidence_line,
                int,
            )
            or self.evidence_line <= 0
        ):
            raise ValueError(
                "evidence_line must be a positive integer"
            )

        if not isinstance(
            self.applicability,
            AndroidSourceRelationshipApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidSourceRelationshipApplicability"
            )

        if (
            self.applicability
            is AndroidSourceRelationshipApplicability
            .COMMENTED
        ):
            raise ValueError(
                "product module consumptions cannot be COMMENTED"
            )

    @property
    def is_positive_declaration(
        self,
    ) -> bool:
        return self.assignment_operator != "-="


@dataclass(frozen=True, slots=True)
class AndroidSourceProductUnresolvedExpression:
    """
    Unresolved content from one lineage-reachable PRODUCT_PACKAGES statement.

    Literal module tokens from the same statement may still be represented as
    AndroidSourceProductModuleConsumption values.  This model preserves the
    expression content TreeForge deliberately did not evaluate.
    """

    reached_file: AndroidSourceReachedFile

    variable_name: str
    assignment_operator: str

    evidence_line: int
    applicability: AndroidSourceRelationshipApplicability

    unresolved_fragments: tuple[
        str,
        ...,
    ]

    raw_expression: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.reached_file,
            AndroidSourceReachedFile,
        ):
            raise TypeError(
                "reached_file must be an AndroidSourceReachedFile"
            )

        if (
            not isinstance(
                self.variable_name,
                str,
            )
            or not self.variable_name
        ):
            raise ValueError(
                "variable_name must be a non-empty string"
            )

        if not (
            self.variable_name == "PRODUCT_PACKAGES"
            or self.variable_name.startswith(
                "PRODUCT_PACKAGES_"
            )
        ):
            raise ValueError(
                "variable_name must be PRODUCT_PACKAGES "
                "or a PRODUCT_PACKAGES_* variable"
            )

        if self.assignment_operator not in (
            "+=",
            "-=",
            ":=",
            "?=",
            "=",
        ):
            raise ValueError(
                "unsupported PRODUCT_PACKAGES assignment operator"
            )

        if (
            not isinstance(
                self.evidence_line,
                int,
            )
            or self.evidence_line <= 0
        ):
            raise ValueError(
                "evidence_line must be a positive integer"
            )

        if not isinstance(
            self.applicability,
            AndroidSourceRelationshipApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidSourceRelationshipApplicability"
            )

        if (
            self.applicability
            is AndroidSourceRelationshipApplicability
            .COMMENTED
        ):
            raise ValueError(
                "unresolved product expressions cannot be COMMENTED"
            )

        if (
            not isinstance(
                self.unresolved_fragments,
                tuple,
            )
            or not self.unresolved_fragments
            or not all(
                isinstance(
                    fragment,
                    str,
                )
                and fragment
                for fragment in self.unresolved_fragments
            )
        ):
            raise ValueError(
                "unresolved_fragments must be a non-empty "
                "tuple of non-empty strings"
            )

        if (
            self.unresolved_fragments
            != tuple(
                sorted(
                    set(
                        self.unresolved_fragments
                    )
                )
            )
        ):
            raise ValueError(
                "unresolved_fragments must be unique and "
                "deterministically ordered"
            )

        if (
            not isinstance(
                self.raw_expression,
                str,
            )
            or not self.raw_expression
        ):
            raise ValueError(
                "raw_expression must be a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class AndroidSourceProductModuleConsumptionInventory:
    """
    Literal PRODUCT_PACKAGES evidence from one exact source-lineage result.
    """

    lineage: AndroidSourceRepositoryLineage

    consumptions: tuple[
        AndroidSourceProductModuleConsumption,
        ...,
    ]

    unresolved_expressions: tuple[
        AndroidSourceProductUnresolvedExpression,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.lineage,
            AndroidSourceRepositoryLineage,
        ):
            raise TypeError(
                "lineage must be an AndroidSourceRepositoryLineage"
            )

        if (
            not isinstance(
                self.consumptions,
                tuple,
            )
            or not all(
                isinstance(
                    item,
                    AndroidSourceProductModuleConsumption,
                )
                for item in self.consumptions
            )
        ):
            raise TypeError(
                "consumptions contains an invalid model"
            )

        if (
            not isinstance(
                self.unresolved_expressions,
                tuple,
            )
            or not all(
                isinstance(
                    item,
                    AndroidSourceProductUnresolvedExpression,
                )
                for item in self.unresolved_expressions
            )
        ):
            raise TypeError(
                "unresolved_expressions contains an invalid model"
            )

        reached_ids = {
            id(reached)
            for reached in self.lineage.reached_files
        }

        for item in (
            *self.consumptions,
            *self.unresolved_expressions,
        ):
            if (
                id(
                    item.reached_file
                )
                not in reached_ids
            ):
                raise ValueError(
                    "product evidence must preserve exact "
                    "lineage reached-file identity"
                )

        expected_consumptions = tuple(
            sorted(
                self.consumptions,
                key=lambda item: (
                    item.reached_file.source_path,
                    item.evidence_line,
                    item.variable_name,
                    item.assignment_operator,
                    item.module_name,
                    item.applicability.value,
                    item.raw_expression,
                ),
            )
        )

        if self.consumptions != expected_consumptions:
            raise ValueError(
                "consumptions must use deterministic ordering"
            )

        expected_unresolved = tuple(
            sorted(
                self.unresolved_expressions,
                key=lambda item: (
                    item.reached_file.source_path,
                    item.evidence_line,
                    item.variable_name,
                    item.assignment_operator,
                    item.unresolved_fragments,
                    item.applicability.value,
                    item.raw_expression,
                ),
            )
        )

        if (
            self.unresolved_expressions
            != expected_unresolved
        ):
            raise ValueError(
                "unresolved_expressions must use "
                "deterministic ordering"
            )

    def consumptions_for_module(
        self,
        module_name: str,
    ) -> tuple[
        AndroidSourceProductModuleConsumption,
        ...,
    ]:
        return tuple(
            item
            for item in self.consumptions
            if item.module_name == module_name
        )

    def positive_consumptions_for_module(
        self,
        module_name: str,
    ) -> tuple[
        AndroidSourceProductModuleConsumption,
        ...,
    ]:
        return tuple(
            item
            for item in self.consumptions
            if (
                item.module_name == module_name
                and item.is_positive_declaration
            )
        )


class AndroidSourceProductModuleConsumptionIndexer:
    """
    Index literal PRODUCT_PACKAGES declarations from exact lineage-reachable
    Makefiles.

    The indexer deliberately does not:
    - expand Make variables;
    - execute Make functions;
    - evaluate assignment precedence;
    - resolve += / = / := / ?= / -= into one effective package set;
    - scan files outside lineage.reached_files;
    - infer module names from paths or filenames;
    - choose source providers;
    - decide Reconstruction Ownership.
    """

    @classmethod
    def index(
        cls,
        lineage: AndroidSourceRepositoryLineage,
    ) -> AndroidSourceProductModuleConsumptionInventory:
        if not isinstance(
            lineage,
            AndroidSourceRepositoryLineage,
        ):
            raise TypeError(
                "lineage must be an AndroidSourceRepositoryLineage"
            )

        consumptions = []
        unresolved = []

        for reached_file in lineage.reached_files:
            physical = (
                lineage.inventory.checkout_root
                / reached_file.source_path
            )

            statements = (
                cls._logical_statements(
                    physical.read_text(
                        encoding="utf-8",
                        errors="replace",
                    )
                )
            )

            for (
                evidence_line,
                statement_lines,
                conditional_depth,
            ) in statements:
                expression = "\n".join(
                    statement_lines
                ).strip()

                if not expression:
                    continue

                parsed_expression = (
                    cls._strip_make_comments(
                        statement_lines
                    )
                )

                if not parsed_expression:
                    continue

                match = (
                    _PRODUCT_PACKAGES_ASSIGNMENT_RE
                    .match(
                        parsed_expression
                    )
                )

                if match is None:
                    continue

                variable_name = (
                    match.group(
                        "variable"
                    )
                )

                assignment_operator = (
                    match.group(
                        "operator"
                    )
                )

                body = (
                    match.group(
                        "body"
                    )
                    .replace(
                        "\\\n",
                        " ",
                    )
                    .strip()
                )

                local_applicability = (
                    AndroidSourceRelationshipApplicability
                    .CONDITIONAL
                    if conditional_depth > 0
                    else AndroidSourceRelationshipApplicability
                    .ACTIVE
                )

                applicability = (
                    cls._combine_applicability(
                        incoming=(
                            reached_file.applicability
                        ),
                        statement=(
                            local_applicability
                        ),
                    )
                )

                literal_modules = []
                unresolved_fragments = []

                for token in body.split():
                    candidate = (
                        token
                        .strip()
                        .rstrip(
                            "\\"
                        )
                    )

                    if not candidate:
                        continue

                    if (
                        "$" in candidate
                        or not _LITERAL_MODULE_RE.fullmatch(
                            candidate
                        )
                    ):
                        unresolved_fragments.append(
                            candidate
                        )
                        continue

                    literal_modules.append(
                        candidate
                    )

                for module_name in sorted(
                    set(
                        literal_modules
                    )
                ):
                    consumptions.append(
                        AndroidSourceProductModuleConsumption(
                            reached_file=reached_file,
                            module_name=module_name,
                            variable_name=variable_name,
                            assignment_operator=(
                                assignment_operator
                            ),
                            evidence_line=evidence_line,
                            applicability=applicability,
                            raw_expression=expression,
                        )
                    )

                if unresolved_fragments:
                    unresolved.append(
                        AndroidSourceProductUnresolvedExpression(
                            reached_file=reached_file,
                            variable_name=variable_name,
                            assignment_operator=(
                                assignment_operator
                            ),
                            evidence_line=evidence_line,
                            applicability=applicability,
                            unresolved_fragments=tuple(
                                sorted(
                                    set(
                                        unresolved_fragments
                                    )
                                )
                            ),
                            raw_expression=expression,
                        )
                    )

        consumptions = tuple(
            sorted(
                consumptions,
                key=lambda item: (
                    item.reached_file.source_path,
                    item.evidence_line,
                    item.variable_name,
                    item.assignment_operator,
                    item.module_name,
                    item.applicability.value,
                    item.raw_expression,
                ),
            )
        )

        unresolved = tuple(
            sorted(
                unresolved,
                key=lambda item: (
                    item.reached_file.source_path,
                    item.evidence_line,
                    item.variable_name,
                    item.assignment_operator,
                    item.unresolved_fragments,
                    item.applicability.value,
                    item.raw_expression,
                ),
            )
        )

        return (
            AndroidSourceProductModuleConsumptionInventory(
                lineage=lineage,
                consumptions=consumptions,
                unresolved_expressions=unresolved,
            )
        )

    @staticmethod
    def _logical_statements(
        text: str,
    ) -> tuple[
        tuple[
            int,
            tuple[
                str,
                ...,
            ],
            int,
        ],
        ...,
    ]:
        lines = text.splitlines()

        statements = []
        buffer = []
        start_line = None
        conditional_depth = 0

        for line_number, raw in enumerate(
            lines,
            start=1,
        ):
            stripped = raw.lstrip()

            if (
                not stripped.startswith(
                    "#"
                )
                and _CONDITIONAL_END_RE.match(
                    stripped
                )
            ):
                conditional_depth = max(
                    conditional_depth - 1,
                    0,
                )

            if start_line is None:
                start_line = line_number

            buffer.append(
                raw
            )

            if raw.rstrip().endswith(
                "\\"
            ):
                continue

            statements.append(
                (
                    start_line,
                    tuple(
                        buffer
                    ),
                    conditional_depth,
                )
            )

            if (
                not stripped.startswith(
                    "#"
                )
                and _CONDITIONAL_START_RE.match(
                    stripped
                )
            ):
                conditional_depth += 1

            buffer = []
            start_line = None

        if buffer:
            statements.append(
                (
                    start_line
                    or len(
                        lines
                    )
                    or 1,
                    tuple(
                        buffer
                    ),
                    conditional_depth,
                )
            )

        return tuple(
            statements
        )

    @staticmethod
    def _strip_make_comments(
        statement_lines: tuple[
            str,
            ...,
        ],
    ) -> str:
        cleaned = []

        for raw in statement_lines:
            stripped = raw.lstrip()

            if stripped.startswith(
                "#"
            ):
                continue

            content = raw.split(
                "#",
                1,
            )[0]

            cleaned.append(
                content
            )

        return "\n".join(
            cleaned
        ).strip()

    @staticmethod
    def _combine_applicability(
        *,
        incoming: AndroidSourceRelationshipApplicability,
        statement: AndroidSourceRelationshipApplicability,
    ) -> AndroidSourceRelationshipApplicability:
        if (
            incoming
            is AndroidSourceRelationshipApplicability
            .CONDITIONAL
            or statement
            is AndroidSourceRelationshipApplicability
            .CONDITIONAL
        ):
            return (
                AndroidSourceRelationshipApplicability
                .CONDITIONAL
            )

        return (
            AndroidSourceRelationshipApplicability
            .ACTIVE
        )
