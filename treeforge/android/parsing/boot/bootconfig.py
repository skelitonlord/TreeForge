from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction import (
    ExtractedArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootconfigEntry:
    """
    One lexically parsed Android bootconfig declaration.

    Parsing preserves the exact source line and line number. Interpretation of
    bootconfig keys and values belongs to the later AndroidDeviceUniverse
    stage.
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

        if (
            isinstance(
                self.line_number,
                bool,
            )
            or not isinstance(
                self.line_number,
                int,
            )
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
class AndroidBootconfigUnparsedLine:
    """
    One non-empty bootconfig line that could not be parsed.

    Unsupported or malformed material remains observable rather than
    disappearing during lexical parsing.
    """

    line_number: int
    raw: str
    reason: str

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.line_number,
                bool,
            )
            or not isinstance(
                self.line_number,
                int,
            )
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
class ParsedAndroidBootconfig:
    """
    Lexical Parsing result for one extracted Android bootconfig payload.

    Declaration order and duplicate keys are preserved. Blank lines and
    comments are valid non-semantic syntax and are omitted. Non-empty lines
    that cannot be interpreted remain available through ``unparsed_lines``.
    """

    entries: tuple[
        AndroidBootconfigEntry,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidBootconfigUnparsedLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootconfigEntry,
            )
            for value in self.entries
        ):
            raise TypeError(
                "entries must contain only "
                "AndroidBootconfigEntry instances"
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
                AndroidBootconfigUnparsedLine,
            )
            for value in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidBootconfigUnparsedLine instances"
            )


class AndroidBootconfigParser:
    """
    Lexically parse one materialized Android bootconfig payload.

    This parser deliberately performs no device-level interpretation.
    """

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> ParsedAndroidBootconfig:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source_path = artifact.path

        if not source_path.is_file():
            raise ValueError(
                "bootconfig source must be an existing file: "
                f"{source_path}"
            )

        raw_bytes = source_path.read_bytes()

        try:
            text = raw_bytes.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise ValueError(
                "bootconfig source must contain UTF-8 text: "
                f"{source_path}"
            ) from exc

        # The bootconfig payload extracted from vendor_boot may contain
        # trailing NUL padding. That padding is physical container material,
        # not lexical bootconfig syntax.
        text = text.rstrip("\x00")

        entries: list[
            AndroidBootconfigEntry
        ] = []

        unparsed_lines: list[
            AndroidBootconfigUnparsedLine
        ] = []

        for (
            line_number,
            raw,
        ) in enumerate(
            text.splitlines(),
            start=1,
        ):
            stripped = raw.strip()

            if not stripped:
                continue

            if stripped.startswith("#"):
                continue

            if "=" not in stripped:
                unparsed_lines.append(
                    AndroidBootconfigUnparsedLine(
                        line_number=line_number,
                        raw=raw,
                        reason=(
                            "bootconfig declaration "
                            "contains no '=' separator"
                        ),
                    )
                )
                continue

            key, value = stripped.split(
                "=",
                1,
            )

            key = key.strip()
            value = value.strip()

            if not key:
                unparsed_lines.append(
                    AndroidBootconfigUnparsedLine(
                        line_number=line_number,
                        raw=raw,
                        reason=(
                            "bootconfig declaration "
                            "contains an empty key"
                        ),
                    )
                )
                continue

            entries.append(
                AndroidBootconfigEntry(
                    key=key,
                    value=value,
                    line_number=line_number,
                    raw=raw,
                )
            )

        return ParsedAndroidBootconfig(
            entries=tuple(
                entries
            ),
            unparsed_lines=tuple(
                unparsed_lines
            ),
        )