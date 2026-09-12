from __future__ import annotations

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.input.model import (
    AndroidInputLexicalLine,
    AndroidInputLexicalLineKind,
    AndroidInputParsingResult,
    ParsedAndroidInputConfiguration,
)


class AndroidInputParsingError(ValueError):
    """
    Raised when a positively identified Android input source cannot be
    represented faithfully as text.
    """


class AndroidInputConfigurationParser:
    """
    Literally parse Android .kl, .kcm, and .idc sources.

    Parsing records source identity, raw text, source-line identity, lexical
    tokens, brace structure, and literal IDC-style key/value assignments.

    Android key codes, device matching, keyboard behavior, axes, calibration,
    and cross-source interpretation remain owned by Android Device Universe.
    """

    _KINDS = frozenset(
        {
            AndroidModelSourceKind.INPUT_KEY_LAYOUT,
            AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP,
            AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION,
        }
    )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidInputConfiguration:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if source.kind not in self._KINDS:
            raise ValueError(
                "source must be an Android input configuration source"
            )

        try:
            raw = source.host_path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ) as error:
            raise AndroidInputParsingError(
                "unable to read Android input configuration "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        lines = tuple(
            self._parse_line(
                source=source,
                source_line=index,
                raw_line=raw_line,
            )
            for index, raw_line in enumerate(
                raw.splitlines(),
                start=1,
            )
        )

        return ParsedAndroidInputConfiguration(
            source=source,
            raw=raw,
            lines=lines,
        )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidInputParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source
            in inventory.sources
            if source.kind in self._KINDS
        )

        configurations = tuple(
            self.parse_source(
                source
            )
            for source
            in sources
        )

        expected_source_ids = {
            id(source)
            for source
            in sources
        }

        actual_source_ids = {
            id(configuration.source)
            for configuration
            in configurations
        }

        if (
            expected_source_ids
            != actual_source_ids
        ):
            raise AndroidInputParsingError(
                "Android input Parsing failed to conserve the "
                "complete canonical input source population"
            )

        if len(
            actual_source_ids
        ) != len(
            configurations
        ):
            raise AndroidInputParsingError(
                "Android input Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return AndroidInputParsingResult(
            configurations=tuple(
                sorted(
                    configurations,
                    key=lambda configuration: (
                        configuration.source.identity_key
                    ),
                )
            )
        )

    @staticmethod
    def _parse_line(
        *,
        source: AndroidModelSource,
        source_line: int,
        raw_line: str,
    ) -> AndroidInputLexicalLine:
        content = raw_line.strip()

        if not content:
            return AndroidInputLexicalLine(
                source_line=source_line,
                raw=raw_line,
                content="",
                kind=AndroidInputLexicalLineKind.BLANK,
            )

        if content.startswith("#"):
            return AndroidInputLexicalLine(
                source_line=source_line,
                raw=raw_line,
                content=content,
                kind=AndroidInputLexicalLineKind.COMMENT,
                tokens=tuple(
                    content.split()
                ),
            )

        if (
            source.kind
            is AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION
            and "=" in content
        ):
            key, separator, value = content.partition(
                "="
            )

            if separator and key.strip():
                return AndroidInputLexicalLine(
                    source_line=source_line,
                    raw=raw_line,
                    content=content,
                    kind=(
                        AndroidInputLexicalLineKind
                        .ASSIGNMENT
                    ),
                    tokens=tuple(
                        content.split()
                    ),
                    key=key.strip(),
                    value=value.strip(),
                )

        if content == "}":
            kind = (
                AndroidInputLexicalLineKind
                .BLOCK_CLOSE
            )
        elif content.endswith("{"):
            kind = (
                AndroidInputLexicalLineKind
                .BLOCK_OPEN
            )
        else:
            kind = (
                AndroidInputLexicalLineKind
                .DECLARATION
            )

        return AndroidInputLexicalLine(
            source_line=source_line,
            raw=raw_line,
            content=content,
            kind=kind,
            tokens=tuple(
                content.split()
            ),
        )
