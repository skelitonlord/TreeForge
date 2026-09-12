from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInitLogicalStatement:
    """
    One logical Android INIT statement assembled from physical source lines.

    ``raw`` preserves every consumed physical line exactly as supplied by the
    parser input.

    ``text`` contains the logical statement after continuation joining and
    comment removal, but before token interpretation.

    ``tokens`` contains the lexical INIT arguments with quoting and escaping
    interpreted while preserving whitespace embedded inside quoted or escaped
    values.
    """

    line_number: int
    raw: str
    text: str

    tokens: tuple[
        str,
        ...,
    ]

    next_index: int


class AndroidInitLexer:
    """
    Lexical decoder for Android INIT ``.rc`` syntax.

    This class owns syntax only. It deliberately does not interpret INIT
    commands, service options, triggers, properties, resources, or Android
    runtime behavior.
    """

    def statement(
        self,
        *,
        lines: list[str],
        index: int,
    ) -> AndroidInitLogicalStatement:
        if not isinstance(
            lines,
            list,
        ):
            raise TypeError(
                "lines must be a list"
            )

        if (
            isinstance(
                index,
                bool,
            )
            or not isinstance(
                index,
                int,
            )
        ):
            raise TypeError(
                "index must be an integer"
            )

        if (
            index < 0
            or index >= len(
                lines
            )
        ):
            raise IndexError(
                "index is outside lines"
            )

        physical_lines: list[
            str
        ] = []

        semantic_parts: list[
            str
        ] = []

        next_index = index

        quote: str | None = None

        while next_index < len(
            lines
        ):
            raw_line = lines[
                next_index
            ]

            physical_lines.append(
                raw_line
            )

            semantic, quote = (
                self._physical_semantic_text(
                    raw_line,
                    quote=quote,
                )
            )

            continued = (
                self._has_unescaped_continuation(
                    semantic
                )
            )

            if continued:
                semantic = (
                    semantic[:-1]
                    .rstrip()
                )

            semantic_parts.append(
                semantic
            )

            next_index += 1

            if (
                quote is None
                and not continued
            ):
                break

        text = " ".join(
            part.strip()
            for part in semantic_parts
            if part.strip()
        )

        return AndroidInitLogicalStatement(
            line_number=index + 1,
            raw="\n".join(
                physical_lines
            ),
            text=text,
            tokens=self.tokenize(
                text
            ),
            next_index=next_index,
        )

    def tokenize(
        self,
        text: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Tokenize one logical INIT statement.

        Quote delimiters are syntactic and are not retained in interpreted
        token values. Backslash escaping preserves the escaped character as
        literal token content.
        """

        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "text must be a string"
            )

        tokens: list[
            str
        ] = []

        current: list[
            str
        ] = []

        quote: str | None = None
        escaped = False
        token_started = False

        for character in text:
            if escaped:
                current.append(
                    character
                )
                token_started = True
                escaped = False
                continue

            if character == "\\":
                escaped = True
                token_started = True
                continue

            if quote is not None:
                if character == quote:
                    quote = None
                else:
                    current.append(
                        character
                    )

                token_started = True
                continue

            if character in {
                '"',
                "'",
            }:
                quote = character
                token_started = True
                continue

            if character.isspace():
                if token_started:
                    tokens.append(
                        "".join(
                            current
                        )
                    )
                    current.clear()
                    token_started = False

                continue

            current.append(
                character
            )
            token_started = True

        if escaped:
            current.append(
                "\\"
            )
            token_started = True

        if quote is not None:
            raise ValueError(
                "unterminated INIT quoted string"
            )

        if token_started:
            tokens.append(
                "".join(
                    current
                )
            )

        return tuple(
            tokens
        )

    @staticmethod
    def _physical_semantic_text(
        raw: str,
        *,
        quote: str | None,
    ) -> tuple[
        str,
        str | None,
    ]:
        """
        Remove an INIT comment while respecting quoting and escaping.

        Quote state is returned so quoted values may span physical lines.
        """

        output: list[
            str
        ] = []

        escaped = False

        for character in raw:
            if escaped:
                output.append(
                    "\\"
                )
                output.append(
                    character
                )
                escaped = False
                continue

            if character == "\\":
                escaped = True
                continue

            if quote is not None:
                output.append(
                    character
                )

                if character == quote:
                    quote = None

                continue

            if character in {
                '"',
                "'",
            }:
                quote = character
                output.append(
                    character
                )
                continue

            if character == "#":
                break

            output.append(
                character
            )

        if escaped:
            output.append(
                "\\"
            )

        return (
            "".join(
                output
            ).rstrip(),
            quote,
        )

    @staticmethod
    def _has_unescaped_continuation(
        text: str,
    ) -> bool:
        """
        Return whether a logical line ends in an unescaped backslash.
        """

        count = 0

        for character in reversed(
            text
        ):
            if character != "\\":
                break

            count += 1

        return (
            count % 2
            == 1
        )