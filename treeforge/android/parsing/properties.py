from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidPropertyDeclaration:
    """
    One lexically parsed Android property declaration.

    The declaration preserves the exact source line and line number so
    downstream stages can derive semantic facts without losing lexical
    provenance.
    """

    key: str
    value: str
    line_number: int
    raw: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.key,
            str,
        ):
            raise TypeError(
                "key must be a string"
            )

        if not self.key:
            raise ValueError(
                "key must not be empty"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not isinstance(
            self.line_number,
            int,
        ):
            raise TypeError(
                "line_number must be an integer"
            )

        if self.line_number < 1:
            raise ValueError(
                "line_number must be positive"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidPropertyUnparsedLine:
    """
    One non-empty, non-comment property-source line that could not be parsed.

    Unsupported or malformed source material remains observable instead of
    disappearing during lexical parsing.
    """

    line_number: int
    raw: str
    reason: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.line_number,
            int,
        ):
            raise TypeError(
                "line_number must be an integer"
            )

        if self.line_number < 1:
            raise ValueError(
                "line_number must be positive"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.reason,
            str,
        ):
            raise TypeError(
                "reason must be a string"
            )

        if not self.reason:
            raise ValueError(
                "reason must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidPropertySource:
    """
    Lossless-enough lexical interpretation of one Android property source.

    Property declaration order and duplicate keys are preserved. Blank lines
    and comments are valid non-semantic syntax and are intentionally omitted.
    Non-empty source lines that cannot be interpreted remain available through
    ``unparsed_lines``.
    """

    declarations: tuple[
        AndroidPropertyDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidPropertyUnparsedLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidPropertyDeclaration,
            )
            for value in self.declarations
        ):
            raise TypeError(
                "declarations must contain only "
                "AndroidPropertyDeclaration instances"
            )

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidPropertyUnparsedLine,
            )
            for value in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidPropertyUnparsedLine instances"
            )

    @property
    def declaration_count(
        self,
    ) -> int:
        return len(
            self.declarations
        )

    @property
    def unparsed_line_count(
        self,
    ) -> int:
        return len(
            self.unparsed_lines
        )

    def values(
        self,
        key: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Return every declaration value for one key in source order.
        """

        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "key must be a string"
            )

        return tuple(
            declaration.value
            for declaration in self.declarations
            if declaration.key == key
        )

    def value(
        self,
        key: str,
    ) -> str | None:
        """
        Return the final declaration value for one key.

        This exposes Android's conventional last-declaration-wins view
        without destroying earlier declarations.
        """

        values = self.values(
            key
        )

        if not values:
            return None

        return values[-1]


def parse_android_properties(
    text: str,
) -> ParsedAndroidPropertySource:
    """
    Lexically parse Android property declarations.

    This function performs no Android semantic interpretation, source
    classification, identity inference, reconstruction policy, or
    filesystem discovery.
    """

    if not isinstance(
        text,
        str,
    ):
        raise TypeError(
            "text must be a string"
        )

    return parse_android_property_lines(
        text.splitlines()
    )


def parse_android_property_lines(
    lines: Iterable[str],
) -> ParsedAndroidPropertySource:
    """
    Lexically parse Android properties from an iterable of source lines.
    """

    declarations: list[
        AndroidPropertyDeclaration
    ] = []

    unparsed_lines: list[
        AndroidPropertyUnparsedLine
    ] = []

    for line_number, raw_line in enumerate(
        lines,
        start=1,
    ):
        if not isinstance(
            raw_line,
            str,
        ):
            raise TypeError(
                "property lines must be strings"
            )

        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        if "=" not in line:
            unparsed_lines.append(
                AndroidPropertyUnparsedLine(
                    line_number=line_number,
                    raw=raw_line,
                    reason="missing_equals",
                )
            )
            continue

        key, value = line.split(
            "=",
            maxsplit=1,
        )

        key = key.strip()
        value = value.strip()

        if not key:
            unparsed_lines.append(
                AndroidPropertyUnparsedLine(
                    line_number=line_number,
                    raw=raw_line,
                    reason="empty_key",
                )
            )
            continue

        declarations.append(
            AndroidPropertyDeclaration(
                key=key,
                value=value,
                line_number=line_number,
                raw=raw_line,
            )
        )

    return ParsedAndroidPropertySource(
        declarations=tuple(
            declarations
        ),
        unparsed_lines=tuple(
            unparsed_lines
        ),
    )


def read_android_properties(
    path: Path,
    *,
    errors: str = "ignore",
) -> ParsedAndroidPropertySource:
    """
    Read and lexically parse one host Android property source.
    """

    if not isinstance(
        path,
        Path,
    ):
        raise TypeError(
            "path must be a Path"
        )

    if not isinstance(
        errors,
        str,
    ):
        raise TypeError(
            "errors must be a string"
        )

    if not errors:
        raise ValueError(
            "errors cannot be empty"
        )

    return parse_android_properties(
        path.read_text(
            encoding="utf-8",
            errors=errors,
        )
    )