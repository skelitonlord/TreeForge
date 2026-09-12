from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidShellAssignment:
    """
    One simple shell assignment observed lexically.

    ``resolved_value`` is populated only when TreeForge can substitute every
    referenced variable from preceding statically resolved assignments.
    """

    index: int
    line_number: int
    name: str
    raw_value: str
    resolved_value: str | None
    exported: bool = False

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
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
            or self.line_number < 1
        ):
            raise ValueError(
                "line_number must be a positive integer"
            )

        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "name must be a non-empty string"
            )

        if not isinstance(
            self.raw_value,
            str,
        ):
            raise TypeError(
                "raw_value must be a string"
            )

        if (
            self.resolved_value is not None
            and not isinstance(
                self.resolved_value,
                str,
            )
        ):
            raise TypeError(
                "resolved_value must be a string or None"
            )

        if not isinstance(
            self.exported,
            bool,
        ):
            raise TypeError(
                "exported must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidShellClasspathEntry:
    """
    One colon-delimited CLASSPATH component from a shell assignment.

    ``resolved_path`` is present only when the component is statically proven
    to be one absolute Android path.
    """

    assignment_index: int
    index: int
    raw_component: str
    resolved_component: str | None
    resolved_path: PurePosixPath | None

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "assignment_index",
                self.assignment_index,
            ),
            (
                "index",
                self.index,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.raw_component,
            str,
        ):
            raise TypeError(
                "raw_component must be a string"
            )

        if (
            self.resolved_component is not None
            and not isinstance(
                self.resolved_component,
                str,
            )
        ):
            raise TypeError(
                "resolved_component must be a string or None"
            )

        if (
            self.resolved_path is not None
            and not isinstance(
                self.resolved_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "resolved_path must be a PurePosixPath or None"
            )

        if (
            self.resolved_path is not None
            and not self.resolved_path.is_absolute()
        ):
            raise ValueError(
                "resolved_path must be absolute"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidShellCommandObservation:
    """
    One lexically tokenized non-assignment shell command line.

    This observation preserves only syntax that Parsing can establish
    statically. It does not prove execution, control-flow reachability,
    PATH resolution, command semantics, or shell side effects.

    ``argv`` preserves shell words exactly after lexical tokenization,
    including explicitly quoted empty arguments. ``resolved_argv`` contains
    per-token variable expansion only where the existing preceding-assignment
    environment can resolve the token completely.
    """

    index: int
    line_number: int
    raw: str

    argv: tuple[
        str,
        ...,
    ]

    resolved_argv: tuple[
        str | None,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if (
            not isinstance(
                self.line_number,
                int,
            )
            or self.line_number <= 0
        ):
            raise ValueError(
                "line_number must be a positive integer"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if (
            not isinstance(
                self.argv,
                tuple,
            )
            or not self.argv
            or not all(
                isinstance(
                    token,
                    str,
                )
                for token in self.argv
            )
        ):
            raise ValueError(
                "argv must contain one or more strings"
            )

        if (
            not isinstance(
                self.resolved_argv,
                tuple,
            )
            or len(
                self.resolved_argv
            )
            != len(
                self.argv
            )
            or not all(
                value is None
                or isinstance(
                    value,
                    str,
                )
                for value in self.resolved_argv
            )
        ):
            raise ValueError(
                "resolved_argv must preserve argv cardinality and "
                "contain only strings or None"
            )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidShellExecObservation:
    """
    One lexically explicit shell ``exec`` command.

    Parsing does not perform PATH lookup or assign runtime semantics.
    """

    index: int
    line_number: int
    raw: str
    argv: tuple[
        str,
        ...,
    ]
    resolved_argv: tuple[
        str | None,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
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
            or self.line_number < 1
        ):
            raise ValueError(
                "line_number must be a positive integer"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if (
            not isinstance(
                self.argv,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    str,
                )
                for value in self.argv
            )
        ):
            raise TypeError(
                "argv must contain only strings"
            )

        if (
            not isinstance(
                self.resolved_argv,
                tuple,
            )
            or not all(
                value is None
                or isinstance(
                    value,
                    str,
                )
                for value
                in self.resolved_argv
            )
        ):
            raise TypeError(
                "resolved_argv must contain strings or None"
            )

        if len(
            self.argv
        ) != len(
            self.resolved_argv
        ):
            raise ValueError(
                "resolved_argv must preserve argv cardinality"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidShellScript:
    """
    Intrinsic shell-script observations from one canonical filesystem source.

    Parsing intentionally does not execute shell, evaluate command
    substitutions, perform PATH lookup, or assign Java/runtime meaning.
    """

    source: AndroidModelSource
    raw: str
    shebang: str | None

    assignments: tuple[
        AndroidShellAssignment,
        ...,
    ] = ()

    classpath_entries: tuple[
        AndroidShellClasspathEntry,
        ...,
    ] = ()

    command_observations: tuple[
        AndroidShellCommandObservation,
        ...,
    ] = ()

    exec_observations: tuple[
        AndroidShellExecObservation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            self.source.kind
            is not AndroidModelSourceKind.SHELL_SCRIPT
        ):
            raise ValueError(
                "source must be a SHELL_SCRIPT source"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if (
            self.shebang is not None
            and (
                not isinstance(
                    self.shebang,
                    str,
                )
                or not self.shebang.startswith(
                    "#!"
                )
            )
        ):
            raise ValueError(
                "shebang must preserve a shell shebang or be None"
            )

        for name, values, expected in (
            (
                "assignments",
                self.assignments,
                AndroidShellAssignment,
            ),
            (
                "classpath_entries",
                self.classpath_entries,
                AndroidShellClasspathEntry,
            ),
            (
                "command_observations",
                self.command_observations,
                AndroidShellCommandObservation,
            ),
            (
                "exec_observations",
                self.exec_observations,
                AndroidShellExecObservation,
            ),
        ):
            if (
                not isinstance(
                    values,
                    tuple,
                )
                or not all(
                    isinstance(
                        value,
                        expected,
                    )
                    for value in values
                )
            ):
                raise TypeError(
                    f"{name} contains invalid values"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidShellScriptParsingResult:
    """
    Canonical deterministic shell-script Parsing population.
    """

    scripts: tuple[
        ParsedAndroidShellScript,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.scripts,
                tuple,
            )
            or not all(
                isinstance(
                    script,
                    ParsedAndroidShellScript,
                )
                for script in self.scripts
            )
        ):
            raise TypeError(
                "scripts must contain only ParsedAndroidShellScript values"
            )

        expected = tuple(
            sorted(
                self.scripts,
                key=lambda script: (
                    script.source.identity_key
                ),
            )
        )

        if expected != self.scripts:
            raise ValueError(
                "scripts must use canonical source order"
            )

        identities = tuple(
            script.source.identity_key
            for script in self.scripts
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "shell-script source identities must be unique"
            )

    @property
    def source_count(
        self,
    ) -> int:
        return len(
            self.scripts
        )

    @property
    def classpath_entry_count(
        self,
    ) -> int:
        return sum(
            len(
                script.classpath_entries
            )
            for script in self.scripts
        )

    @property
    def command_count(
        self,
    ) -> int:
        return sum(
            len(
                script.command_observations
            )
            for script in self.scripts
        )

    @property
    def exec_count(
        self,
    ) -> int:
        return sum(
            len(
                script.exec_observations
            )
            for script in self.scripts
        )
