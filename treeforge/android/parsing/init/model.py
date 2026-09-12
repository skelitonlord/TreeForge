from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.init.provenance import (
    SourceLocation,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInitImport:
    """
    One parsed Android init import declaration.
    """

    path: str
    location: SourceLocation
    raw: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.path,
            str,
        ):
            raise TypeError(
                "path must be a string"
            )

        if not self.path:
            raise ValueError(
                "path must not be empty"
            )

        if not isinstance(
            self.location,
            SourceLocation,
        ):
            raise TypeError(
                "location must be a SourceLocation"
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
class AndroidInitServiceOption:
    """
    One ordered option declaration inside an init service block.

    Repeated options remain separate declarations.
    """

    keyword: str
    arguments: tuple[
        str,
        ...,
    ]
    location: SourceLocation
    raw: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.keyword,
            str,
        ):
            raise TypeError(
                "keyword must be a string"
            )

        if not self.keyword:
            raise ValueError(
                "keyword must not be empty"
            )

        if not isinstance(
            self.arguments,
            tuple,
        ):
            raise TypeError(
                "arguments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.arguments
        ):
            raise TypeError(
                "arguments must contain only strings"
            )

        if not isinstance(
            self.location,
            SourceLocation,
        ):
            raise TypeError(
                "location must be a SourceLocation"
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
class AndroidInitService:
    """
    One parsed Android init service declaration.
    """

    name: str
    executable: str

    arguments: tuple[
        str,
        ...,
    ]

    options: tuple[
        AndroidInitServiceOption,
        ...,
    ]

    location: SourceLocation
    raw_header: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name must not be empty"
            )

        if not isinstance(
            self.executable,
            str,
        ):
            raise TypeError(
                "executable must be a string"
            )

        if not self.executable:
            raise ValueError(
                "executable must not be empty"
            )

        if not isinstance(
            self.arguments,
            tuple,
        ):
            raise TypeError(
                "arguments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.arguments
        ):
            raise TypeError(
                "arguments must contain only strings"
            )

        if not isinstance(
            self.options,
            tuple,
        ):
            raise TypeError(
                "options must be a tuple"
            )

        if not all(
            isinstance(
                option,
                AndroidInitServiceOption,
            )
            for option in self.options
        ):
            raise TypeError(
                "options must contain only "
                "AndroidInitServiceOption instances"
            )

        if not isinstance(
            self.location,
            SourceLocation,
        ):
            raise TypeError(
                "location must be a SourceLocation"
            )

        if not isinstance(
            self.raw_header,
            str,
        ):
            raise TypeError(
                "raw_header must be a string"
            )

    def options_for(
        self,
        keyword: str,
    ) -> tuple[
        AndroidInitServiceOption,
        ...,
    ]:
        """
        Return every option declaration with one keyword.
        """

        if not isinstance(
            keyword,
            str,
        ):
            raise TypeError(
                "keyword must be a string"
            )

        return tuple(
            option
            for option in self.options
            if option.keyword == keyword
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInitCommand:
    """
    One ordered command inside an Android init action.
    """

    keyword: str

    arguments: tuple[
        str,
        ...,
    ]

    location: SourceLocation
    raw: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.keyword,
            str,
        ):
            raise TypeError(
                "keyword must be a string"
            )

        if not self.keyword:
            raise ValueError(
                "keyword must not be empty"
            )

        if not isinstance(
            self.arguments,
            tuple,
        ):
            raise TypeError(
                "arguments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.arguments
        ):
            raise TypeError(
                "arguments must contain only strings"
            )

        if not isinstance(
            self.location,
            SourceLocation,
        ):
            raise TypeError(
                "location must be a SourceLocation"
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
class AndroidInitAction:
    """
    One parsed Android init action block.
    """

    trigger: str

    commands: tuple[
        AndroidInitCommand,
        ...,
    ]

    location: SourceLocation
    raw_header: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.trigger,
            str,
        ):
            raise TypeError(
                "trigger must be a string"
            )

        if not self.trigger:
            raise ValueError(
                "trigger must not be empty"
            )

        if not isinstance(
            self.commands,
            tuple,
        ):
            raise TypeError(
                "commands must be a tuple"
            )

        if not all(
            isinstance(
                command,
                AndroidInitCommand,
            )
            for command in self.commands
        ):
            raise TypeError(
                "commands must contain only "
                "AndroidInitCommand instances"
            )

        if not isinstance(
            self.location,
            SourceLocation,
        ):
            raise TypeError(
                "location must be a SourceLocation"
            )

        if not isinstance(
            self.raw_header,
            str,
        ):
            raise TypeError(
                "raw_header must be a string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidInitUnparsedLine:
    """
    Preserve one meaningful init source line not represented by the parser.
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
class ParsedAndroidInitFile:
    """
    Immutable syntactic representation of exactly one init ``.rc`` source.

    Imports are declarations only. Import traversal/resolution belongs to a
    later stage and never mutates this source-file representation.
    """

    raw: str

    imports: tuple[
        AndroidInitImport,
        ...,
    ] = ()

    services: tuple[
        AndroidInitService,
        ...,
    ] = ()

    actions: tuple[
        AndroidInitAction,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidInitUnparsedLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        collections = (
            (
                "imports",
                self.imports,
                AndroidInitImport,
            ),
            (
                "services",
                self.services,
                AndroidInitService,
            ),
            (
                "actions",
                self.actions,
                AndroidInitAction,
            ),
            (
                "unparsed_lines",
                self.unparsed_lines,
                AndroidInitUnparsedLine,
            ),
        )

        for (
            field_name,
            values,
            expected_type,
        ) in collections:
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    f"{expected_type.__name__} instances"
                )

    @property
    def statement_count(
        self,
    ) -> int:
        return (
            len(
                self.imports
            )
            + len(
                self.services
            )
            + len(
                self.actions
            )
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return self.statement_count == 0