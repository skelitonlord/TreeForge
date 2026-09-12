from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.parsing.selinux.model import (
    AndroidSelinuxCilAtom,
    AndroidSelinuxCilExpression,
    AndroidSelinuxCilForm,
    AndroidSelinuxCilList,
)


@dataclass(
    frozen=True,
    slots=True,
)
class _Token:
    value: str
    line: int

    quoted: bool = False
    parenthesis: bool = False


class AndroidSelinuxCilParser:
    """
    Structurally decode CIL into generic immutable S-expressions.

    Parsing understands CIL lexical structure only. Android Device Universe
    owns interpretation of individual policy form names and relationships.
    """

    def parse(
        self,
        raw: str,
        *,
        source_path: Path,
    ) -> tuple[
        AndroidSelinuxCilForm,
        ...,
    ]:
        if not isinstance(
            raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        tokens = self._tokenize(
            raw
        )

        index = 0

        forms: list[
            AndroidSelinuxCilForm
        ] = []

        while index < len(tokens):
            expression, index = (
                self._parse_expression(
                    tokens,
                    index,
                )
            )

            if not isinstance(
                expression,
                AndroidSelinuxCilList,
            ):
                raise ValueError(
                    "CIL top-level expression must be a list"
                )

            if not expression.items:
                raise ValueError(
                    "CIL top-level form must not be empty"
                )

            head = expression.items[0]

            if not isinstance(
                head,
                AndroidSelinuxCilAtom,
            ):
                raise ValueError(
                    "CIL form name must be an atom"
                )

            forms.append(
                AndroidSelinuxCilForm(
                    name=head.value,
                    expression=expression,
                    source_line=(
                        expression.source_line
                    ),
                    end_line=(
                        expression.end_line
                    ),
                )
            )

        return tuple(
            forms
        )

    def _parse_expression(
        self,
        tokens: tuple[
            _Token,
            ...,
        ],
        index: int,
    ) -> tuple[
        AndroidSelinuxCilExpression,
        int,
    ]:
        if index >= len(tokens):
            raise ValueError(
                "unexpected end of CIL input"
            )

        token = tokens[index]

        if token.value == ")":
            raise ValueError(
                "unexpected CIL closing parenthesis"
            )

        if token.value != "(":
            return (
                AndroidSelinuxCilAtom(
                    value=token.value,
                    quoted=token.quoted,
                    source_line=token.line,
                ),
                index + 1,
            )

        start_line = token.line

        index += 1

        items: list[
            AndroidSelinuxCilExpression
        ] = []

        while True:
            if index >= len(tokens):
                raise ValueError(
                    "unterminated CIL list"
                )

            if tokens[index].value == ")":
                end_line = (
                    tokens[index].line
                )

                return (
                    AndroidSelinuxCilList(
                        items=tuple(
                            items
                        ),
                        source_line=start_line,
                        end_line=end_line,
                    ),
                    index + 1,
                )

            item, index = (
                self._parse_expression(
                    tokens,
                    index,
                )
            )

            items.append(
                item
            )

    @staticmethod
    def _tokenize(
        raw: str,
    ) -> tuple[
        _Token,
        ...,
    ]:
        tokens: list[
            _Token
        ] = []

        index = 0
        line = 1

        while index < len(raw):
            character = raw[index]

            if character == "\n":
                line += 1
                index += 1
                continue

            if character.isspace():
                index += 1
                continue

            if character == ";":
                while (
                    index < len(raw)
                    and raw[index] != "\n"
                ):
                    index += 1

                continue

            if character in "()":
                tokens.append(
                    _Token(
                        value=character,
                        line=line,
                        parenthesis=True,
                    )
                )

                index += 1
                continue

            if character == '"':
                start_line = line
                index += 1

                value: list[
                    str
                ] = []

                escaped = False

                while index < len(raw):
                    character = raw[index]

                    if character == "\n":
                        line += 1

                    if escaped:
                        value.append(
                            character
                        )
                        escaped = False
                        index += 1
                        continue

                    if character == "\\":
                        escaped = True
                        value.append(
                            character
                        )
                        index += 1
                        continue

                    if character == '"':
                        index += 1
                        break

                    value.append(
                        character
                    )

                    index += 1
                else:
                    raise ValueError(
                        "unterminated CIL quoted string"
                    )

                tokens.append(
                    _Token(
                        value="".join(
                            value
                        ),
                        line=start_line,
                        quoted=True,
                    )
                )

                continue

            start = index
            start_line = line

            while (
                index < len(raw)
                and not raw[index].isspace()
                and raw[index] not in "();"
            ):
                index += 1

            if start == index:
                raise ValueError(
                    "unable to tokenize CIL input"
                )

            tokens.append(
                _Token(
                    value=raw[
                        start:index
                    ],
                    line=start_line,
                )
            )

        return tuple(
            tokens
        )