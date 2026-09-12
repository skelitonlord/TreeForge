from __future__ import annotations

from pathlib import Path

from treeforge.android.init.provenance import (
    SourceLocation,
    SourceOrigin,
)
from treeforge.android.parsing.init.lexer import (
    AndroidInitLexer,
)
from treeforge.android.parsing.init.model import (
    AndroidInitAction,
    AndroidInitCommand,
    AndroidInitImport,
    AndroidInitService,
    AndroidInitServiceOption,
    AndroidInitUnparsedLine,
    ParsedAndroidInitFile,
)


class InitRcParser:
    """
    Parse exactly one Android init ``.rc`` source.

    Import declarations are preserved but never followed recursively.
    """

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

    def parse(
        self,
        path: Path,
    ) -> ParsedAndroidInitFile:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not path.is_file():
            raise IsADirectoryError(
                path
            )

        source_path = path.resolve()

        raw = source_path.read_text(
            encoding="utf-8",
            errors="strict",
        )

        lines = raw.splitlines()

        imports: list[
            AndroidInitImport
        ] = []

        services: list[
            AndroidInitService
        ] = []

        actions: list[
            AndroidInitAction
        ] = []

        unparsed_lines: list[
            AndroidInitUnparsedLine
        ] = []

        index = 0

        while index < len(
            lines
        ):
            raw_line = lines[
                index
            ]

            normalized = (
                raw_line.strip()
            )

            line_number = (
                index
                + 1
            )

            if (
                not normalized
                or normalized.startswith(
                    "#"
                )
            ):
                index += 1
                continue

            if normalized.startswith(
                "import "
            ):
                (
                    parsed_import,
                    next_index,
                ) = self._parse_import(
                    path=source_path,
                    lines=lines,
                    index=index,
                )

                if parsed_import is None:
                    unparsed_lines.append(
                        AndroidInitUnparsedLine(
                            line_number=(
                                line_number
                            ),
                            raw=raw_line,
                            reason=(
                                "malformed_import"
                            ),
                        )
                    )
                else:
                    imports.append(
                        parsed_import
                    )

                index = next_index
                continue

            if normalized.startswith(
                "service "
            ):
                (
                    service,
                    next_index,
                    rejected,
                ) = self._parse_service(
                    path=source_path,
                    lines=lines,
                    index=index,
                )

                if service is not None:
                    services.append(
                        service
                    )

                unparsed_lines.extend(
                    rejected
                )

                index = next_index
                continue

            if normalized.startswith(
                "on "
            ):
                (
                    action,
                    next_index,
                    rejected,
                ) = self._parse_action(
                    path=source_path,
                    lines=lines,
                    index=index,
                )

                if action is not None:
                    actions.append(
                        action
                    )

                unparsed_lines.extend(
                    rejected
                )

                index = next_index
                continue

            unparsed_lines.append(
                AndroidInitUnparsedLine(
                    line_number=line_number,
                    raw=raw_line,
                    reason=(
                        "orphan_indented_line"
                        if self._is_indented(
                            raw_line
                        )
                        else "unsupported_top_level_statement"
                    ),
                )
            )

            index += 1

        return ParsedAndroidInitFile(
            raw=raw,
            imports=tuple(
                imports
            ),
            services=tuple(
                services
            ),
            actions=tuple(
                actions
            ),
            unparsed_lines=tuple(
                unparsed_lines
            ),
        )

    def _parse_import(
        self,
        *,
        path: Path,
        lines: list[str],
        index: int,
    ) -> tuple[
        AndroidInitImport | None,
        int,
    ]:
        statement = (
            self._lexer.statement(
                lines=lines,
                index=index,
            )
        )

        parts = statement.tokens

        if (
            len(parts) != 2
            or parts[0] != "import"
            or not parts[1]
        ):
            return (
                None,
                statement.next_index,
            )

        return (
            AndroidInitImport(
                path=parts[1],
                location=(
                    self._location(
                        path=path,
                        line_number=(
                            statement.line_number
                        ),
                    )
                ),
                raw=statement.raw,
            ),
            statement.next_index,
        )

    def _parse_service(
        self,
        *,
        path: Path,
        lines: list[str],
        index: int,
    ) -> tuple[
        AndroidInitService | None,
        int,
        list[
            AndroidInitUnparsedLine
        ],
    ]:
        header_statement = (
            self._lexer.statement(
                lines=lines,
                index=index,
            )
        )

        header = (
            header_statement.tokens
        )

        rejected: list[
            AndroidInitUnparsedLine
        ] = []

        if (
            len(header) < 3
            or header[0] != "service"
        ):
            rejected.append(
                AndroidInitUnparsedLine(
                    line_number=(
                        header_statement.line_number
                    ),
                    raw=header_statement.raw,
                    reason=(
                        "malformed_service_header"
                    ),
                )
            )

            return (
                None,
                header_statement.next_index,
                rejected,
            )

        options: list[
            AndroidInitServiceOption
        ] = []

        next_index = (
            header_statement.next_index
        )

        while next_index < len(
            lines
        ):
            raw_option = lines[
                next_index
            ]

            normalized = (
                raw_option.strip()
            )

            if (
                not normalized
                or normalized.startswith(
                    "#"
                )
            ):
                next_index += 1
                continue

            if self._is_top_level_declaration(
                normalized
            ):
                break

            if not self._is_indented(
                raw_option
            ):
                break

            statement = (
                self._lexer.statement(
                    lines=lines,
                    index=next_index,
                )
            )

            parts = statement.tokens

            if not parts:
                next_index = (
                    statement.next_index
                )
                continue

            options.append(
                AndroidInitServiceOption(
                    keyword=parts[0],
                    arguments=tuple(
                        parts[1:]
                    ),
                    location=(
                        self._location(
                            path=path,
                            line_number=(
                                statement.line_number
                            ),
                        )
                    ),
                    raw=statement.raw,
                )
            )

            next_index = (
                statement.next_index
            )

        return (
            AndroidInitService(
                name=header[1],
                executable=header[2],
                arguments=tuple(
                    header[3:]
                ),
                options=tuple(
                    options
                ),
                location=(
                    self._location(
                        path=path,
                        line_number=(
                            header_statement.line_number
                        ),
                    )
                ),
                raw_header=(
                    header_statement.raw
                ),
            ),
            next_index,
            rejected,
        )

    def _parse_action(
        self,
        *,
        path: Path,
        lines: list[str],
        index: int,
    ) -> tuple[
        AndroidInitAction | None,
        int,
        list[
            AndroidInitUnparsedLine
        ],
    ]:
        header_statement = (
            self._lexer.statement(
                lines=lines,
                index=index,
            )
        )

        header = (
            header_statement.tokens
        )

        rejected: list[
            AndroidInitUnparsedLine
        ] = []

        if (
            len(header) < 2
            or header[0] != "on"
        ):
            rejected.append(
                AndroidInitUnparsedLine(
                    line_number=(
                        header_statement.line_number
                    ),
                    raw=header_statement.raw,
                    reason=(
                        "malformed_action_header"
                    ),
                )
            )

            return (
                None,
                header_statement.next_index,
                rejected,
            )

        trigger = " ".join(
            header[1:]
        )

        commands: list[
            AndroidInitCommand
        ] = []

        next_index = (
            header_statement.next_index
        )

        while next_index < len(
            lines
        ):
            raw_command = lines[
                next_index
            ]

            normalized = (
                raw_command.strip()
            )

            if (
                not normalized
                or normalized.startswith(
                    "#"
                )
            ):
                next_index += 1
                continue

            if self._is_top_level_declaration(
                normalized
            ):
                break

            if not self._is_indented(
                raw_command
            ):
                break

            statement = (
                self._lexer.statement(
                    lines=lines,
                    index=next_index,
                )
            )

            parts = statement.tokens

            if not parts:
                next_index = (
                    statement.next_index
                )
                continue

            commands.append(
                AndroidInitCommand(
                    keyword=parts[0],
                    arguments=tuple(
                        parts[1:]
                    ),
                    location=(
                        self._location(
                            path=path,
                            line_number=(
                                statement.line_number
                            ),
                        )
                    ),
                    raw=statement.raw,
                )
            )

            next_index = (
                statement.next_index
            )

        return (
            AndroidInitAction(
                trigger=trigger,
                commands=tuple(
                    commands
                ),
                location=(
                    self._location(
                        path=path,
                        line_number=(
                            header_statement.line_number
                        ),
                    )
                ),
                raw_header=(
                    header_statement.raw
                ),
            ),
            next_index,
            rejected,
        )

    @staticmethod
    def _is_top_level_declaration(
        normalized: str,
    ) -> bool:
        return (
            normalized == "on"
            or normalized.startswith(
                "on "
            )
            or normalized == "service"
            or normalized.startswith(
                "service "
            )
            or normalized == "import"
            or normalized.startswith(
                "import "
            )
        )

    @staticmethod
    def _location(
        *,
        path: Path,
        line_number: int,
    ) -> SourceLocation:
        return SourceLocation(
            file=path,
            line=line_number,
            origin=SourceOrigin.PARSED,
        )

    @staticmethod
    def _is_indented(
        line: str,
    ) -> bool:
        return bool(
            line
        ) and line[
            :1
        ].isspace()


def read_android_init_rc(
    path: Path,
) -> ParsedAndroidInitFile:
    """
    Read and parse exactly one Android init ``.rc`` source.
    """

    return InitRcParser().parse(
        path
    )