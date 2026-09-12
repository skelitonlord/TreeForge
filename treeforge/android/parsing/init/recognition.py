from __future__ import annotations

from pathlib import Path

from treeforge.android.parsing.init.lexer import (
    AndroidInitLexer,
)


class AndroidInitSourceRecognizer:
    """
    Recognize Android INIT RC sources from intrinsic syntax.

    Recognition is intentionally conservative. A candidate is recognized
    only when it contains at least one top-level Android INIT statement.

    This recognizer does not parse semantic content and does not determine
    whether every statement in the file is supported by TreeForge.
    """

    _TOP_LEVEL_KEYWORDS = frozenset(
        {
            "import",
            "on",
            "service",
        }
    )

    def __init__(
        self,
        *,
        lexer: AndroidInitLexer | None = None,
    ) -> None:
        self._lexer = (
            lexer
            if lexer is not None
            else AndroidInitLexer()
        )

    def recognizes(
        self,
        path: Path,
    ) -> bool:
        """
        Return whether one file contains recognizable Android INIT syntax.
        """

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        if not path.is_file():
            return False

        try:
            raw = path.read_text(
                encoding="utf-8",
                errors="strict",
            )
        except OSError:
            return False

        lines = raw.splitlines()

        index = 0

        while index < len(
            lines
        ):
            raw_line = lines[
                index
            ]

            if (
                not raw_line.strip()
                or raw_line.lstrip().startswith(
                    "#"
                )
            ):
                index += 1
                continue

            if raw_line[:1].isspace():
                index += 1
                continue

            try:
                statement = self._lexer.statement(
                    lines=lines,
                    index=index,
                )
            except ValueError:
                return False

            index = statement.next_index

            if (
                statement.tokens
                and statement.tokens[0]
                in self._TOP_LEVEL_KEYWORDS
            ):
                return True

        return False


def is_android_init_source(
    path: Path,
) -> bool:
    """
    Return whether one file is recognizable as Android INIT RC syntax.
    """

    return AndroidInitSourceRecognizer().recognizes(
        path
    )