from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


class AndroidInputLexicalLineKind(StrEnum):
    """
    Literal lexical shape of one Android input configuration line.

    These values intentionally do not assign Android runtime meaning.
    """

    BLANK = "blank"
    COMMENT = "comment"
    DECLARATION = "declaration"
    ASSIGNMENT = "assignment"
    BLOCK_OPEN = "block_open"
    BLOCK_CLOSE = "block_close"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInputLexicalLine:
    """
    One exact source line from a .kl, .kcm, or .idc source.

    Parsing preserves literal text and lightweight lexical structure only.
    Device/key semantics remain owned by Android Device Universe.
    """

    source_line: int
    raw: str
    content: str

    kind: AndroidInputLexicalLineKind

    tokens: tuple[str, ...] = ()

    key: str | None = None
    value: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.source_line, bool)
            or not isinstance(self.source_line, int)
            or self.source_line < 1
        ):
            raise ValueError(
                "source_line must be a positive integer"
            )

        if not isinstance(self.raw, str):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(self.content, str):
            raise TypeError(
                "content must be a string"
            )

        if not isinstance(
            self.kind,
            AndroidInputLexicalLineKind,
        ):
            raise TypeError(
                "kind must be an AndroidInputLexicalLineKind"
            )

        if not isinstance(self.tokens, tuple):
            raise TypeError(
                "tokens must be a tuple"
            )

        if not all(
            isinstance(token, str)
            for token in self.tokens
        ):
            raise TypeError(
                "tokens must contain only strings"
            )

        if self.key is None:
            if self.value is not None:
                raise ValueError(
                    "value requires key"
                )
        else:
            if (
                not isinstance(self.key, str)
                or not self.key
            ):
                raise ValueError(
                    "key must be a non-empty string or None"
                )

            if not isinstance(self.value, str):
                raise TypeError(
                    "value must be a string when key is present"
                )

            if (
                self.kind
                is not AndroidInputLexicalLineKind.ASSIGNMENT
            ):
                raise ValueError(
                    "key/value are valid only for ASSIGNMENT lines"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidInputConfiguration:
    """
    One canonically identified Android input configuration source.

    The exact AndroidModelSource identity and raw textual source are retained.
    Parsing records lexical structure only and performs no cross-source or
    device-level interpretation.
    """

    source: AndroidModelSource
    raw: str

    lines: tuple[
        AndroidInputLexicalLine,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if self.source.kind not in {
            AndroidModelSourceKind.INPUT_KEY_LAYOUT,
            AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP,
            AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION,
        }:
            raise ValueError(
                "source must be an Android input configuration source"
            )

        if not isinstance(self.raw, str):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(self.lines, tuple):
            raise TypeError(
                "lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                AndroidInputLexicalLine,
            )
            for line in self.lines
        ):
            raise TypeError(
                "lines must contain only AndroidInputLexicalLine values"
            )

        expected_lines = tuple(
            range(
                1,
                len(self.lines) + 1,
            )
        )

        actual_lines = tuple(
            line.source_line
            for line in self.lines
        )

        if actual_lines != expected_lines:
            raise ValueError(
                "input lexical lines must preserve contiguous "
                "source-line ordering"
            )

    @property
    def declaration_count(self) -> int:
        return sum(
            1
            for line in self.lines
            if line.kind
            in {
                AndroidInputLexicalLineKind.DECLARATION,
                AndroidInputLexicalLineKind.ASSIGNMENT,
                AndroidInputLexicalLineKind.BLOCK_OPEN,
                AndroidInputLexicalLineKind.BLOCK_CLOSE,
            }
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInputParsingResult:
    """
    Canonical deterministic Android input configuration population.

    Distinct canonical source observations remain distinct. Cross-source
    reconciliation and device meaning belong to Android Device Universe.
    """

    configurations: tuple[
        ParsedAndroidInputConfiguration,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        if not all(
            isinstance(
                configuration,
                ParsedAndroidInputConfiguration,
            )
            for configuration in self.configurations
        ):
            raise TypeError(
                "configurations must contain only "
                "ParsedAndroidInputConfiguration values"
            )

        canonical = tuple(
            sorted(
                self.configurations,
                key=lambda configuration: (
                    configuration.source.identity_key
                ),
            )
        )

        if canonical != self.configurations:
            raise ValueError(
                "input configurations must use canonical source order"
            )

        identities = tuple(
            configuration.source.identity_key
            for configuration in self.configurations
        )

        if len(identities) != len(set(identities)):
            raise ValueError(
                "input configuration source identities must be unique"
            )

        source_object_ids = tuple(
            id(
                configuration.source
            )
            for configuration
            in self.configurations
        )

        if len(
            source_object_ids
        ) != len(
            set(
                source_object_ids
            )
        ):
            raise ValueError(
                "input configurations must preserve unique "
                "canonical AndroidModelSource object identities"
            )

    @property
    def source_count(self) -> int:
        return len(
            self.configurations
        )

    @property
    def key_layout_count(self) -> int:
        return sum(
            1
            for configuration in self.configurations
            if configuration.source.kind
            is AndroidModelSourceKind.INPUT_KEY_LAYOUT
        )

    @property
    def key_character_map_count(self) -> int:
        return sum(
            1
            for configuration in self.configurations
            if configuration.source.kind
            is AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP
        )

    @property
    def device_configuration_count(self) -> int:
        return sum(
            1
            for configuration in self.configurations
            if configuration.source.kind
            is AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION
        )

    @property
    def declaration_count(self) -> int:
        return sum(
            configuration.declaration_count
            for configuration in self.configurations
        )
