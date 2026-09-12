from __future__ import annotations

from pathlib import PurePosixPath
import re
import shlex

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.shell_script.model import (
    AndroidShellAssignment,
    AndroidShellClasspathEntry,
    AndroidShellCommandObservation,
    AndroidShellExecObservation,
    AndroidShellScriptParsingResult,
    ParsedAndroidShellScript,
)
from treeforge.android.parsing.shell_script.recognizer import (
    shell_interpreter_from_shebang,
)


_VARIABLE = re.compile(
    r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|"
    r"([A-Za-z_][A-Za-z0-9_]*))"
)

_SIMPLE_ASSIGNMENT = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$",
    re.DOTALL,
)


class AndroidShellScriptParsingError(
    ValueError
):
    pass


class AndroidShellScriptParser:
    """
    Parse only statically provable shell observations.

    This is deliberately not a shell interpreter.
    """

    @staticmethod
    def _expand(
        value: str,
        environment: dict[
            str,
            str,
        ],
    ) -> str | None:
        if (
            "$(" in value
            or "`" in value
        ):
            return None

        # Complex ${...} parameter operators are intentionally unsupported.
        for candidate in re.findall(
            r"\$\{([^}]*)\}",
            value,
        ):
            if not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*",
                candidate,
            ):
                return None

        unresolved = False

        def replace(
            match: re.Match[str],
        ) -> str:
            nonlocal unresolved

            name = (
                match.group(1)
                or match.group(2)
            )

            if name not in environment:
                unresolved = True
                return match.group(0)

            return environment[
                name
            ]

        expanded = _VARIABLE.sub(
            replace,
            value,
        )

        return (
            None
            if unresolved
            else expanded
        )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidShellScriptParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.SHELL_SCRIPT
            )
        )

        scripts = tuple(
            self.parse_source(
                source
            )
            for source in sources
        )

        if {
            id(
                source
            )
            for source in sources
        } != {
            id(
                script.source
            )
            for script in scripts
        }:
            raise AndroidShellScriptParsingError(
                "shell-script Parsing failed to conserve the complete "
                "canonical SHELL_SCRIPT source population"
            )

        return AndroidShellScriptParsingResult(
            scripts=tuple(
                sorted(
                    scripts,
                    key=lambda script: (
                        script.source.identity_key
                    ),
                )
            )
        )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidShellScript:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            source.kind
            is not AndroidModelSourceKind.SHELL_SCRIPT
        ):
            raise ValueError(
                "source must be a SHELL_SCRIPT source"
            )

        try:
            raw_bytes = source.host_path.read_bytes()
            raw = raw_bytes.decode(
                "utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ) as error:
            raise AndroidShellScriptParsingError(
                "unable to decode canonical shell script "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        lines = raw.splitlines()

        if not lines:
            raise AndroidShellScriptParsingError(
                "shell script is empty"
            )

        shebang = (
            lines[0]
            if (
                shell_interpreter_from_shebang(
                    lines[0]
                )
                is not None
            )
            else None
        )

        environment: dict[
            str,
            str,
        ] = {}

        assignments = []
        classpath_entries = []
        command_observations = []
        exec_observations = []

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            stripped = line.strip()

            if (
                not stripped
                or stripped.startswith(
                    "#"
                )
            ):
                continue

            try:
                tokens = shlex.split(
                    line,
                    comments=True,
                    posix=True,
                )
            except ValueError:
                continue

            if not tokens:
                continue

            exported = False
            assignment_token = None

            if (
                len(tokens) == 1
                and _SIMPLE_ASSIGNMENT.match(
                    tokens[0]
                )
            ):
                assignment_token = tokens[0]

            elif (
                len(tokens) == 2
                and tokens[0] == "export"
                and _SIMPLE_ASSIGNMENT.match(
                    tokens[1]
                )
            ):
                exported = True
                assignment_token = tokens[1]

            if assignment_token is not None:
                match = _SIMPLE_ASSIGNMENT.match(
                    assignment_token
                )

                assert match is not None

                name = match.group(1)
                raw_value = match.group(2)

                assignment_index = len(
                    assignments
                )

                resolved_value = self._expand(
                    raw_value,
                    environment,
                )

                assignments.append(
                    AndroidShellAssignment(
                        index=assignment_index,
                        line_number=line_number,
                        name=name,
                        raw_value=raw_value,
                        resolved_value=(
                            resolved_value
                        ),
                        exported=exported,
                    )
                )

                if name == "CLASSPATH":
                    for component_index, component in enumerate(
                        raw_value.split(
                            ":"
                        )
                    ):
                        resolved_component = (
                            self._expand(
                                component,
                                environment,
                            )
                        )

                        resolved_path = None

                        if (
                            resolved_component
                            and resolved_component.startswith(
                                "/"
                            )
                        ):
                            candidate = PurePosixPath(
                                resolved_component
                            )

                            if (
                                candidate.is_absolute()
                                and ".."
                                not in candidate.parts
                            ):
                                resolved_path = (
                                    candidate
                                )

                        classpath_entries.append(
                            AndroidShellClasspathEntry(
                                assignment_index=(
                                    assignment_index
                                ),
                                index=(
                                    len(
                                        classpath_entries
                                    )
                                ),
                                raw_component=component,
                                resolved_component=(
                                    resolved_component
                                ),
                                resolved_path=(
                                    resolved_path
                                ),
                            )
                        )

                if resolved_value is None:
                    environment.pop(
                        name,
                        None,
                    )
                else:
                    environment[
                        name
                    ] = resolved_value

                continue

            command_argv = tuple(
                tokens
            )

            command_observations.append(
                AndroidShellCommandObservation(
                    index=len(
                        command_observations
                    ),
                    line_number=line_number,
                    raw=line,
                    argv=command_argv,
                    resolved_argv=tuple(
                        self._expand(
                            token,
                            environment,
                        )
                        for token in command_argv
                    ),
                )
            )

            if tokens[0] != "exec":
                continue

            argv = tuple(
                tokens[1:]
            )

            if not argv:
                continue

            exec_observations.append(
                AndroidShellExecObservation(
                    index=len(
                        exec_observations
                    ),
                    line_number=line_number,
                    raw=line,
                    argv=argv,
                    resolved_argv=tuple(
                        self._expand(
                            token,
                            environment,
                        )
                        for token in argv
                    ),
                )
            )

        return ParsedAndroidShellScript(
            source=source,
            raw=raw,
            shebang=shebang,
            assignments=tuple(
                assignments
            ),
            classpath_entries=tuple(
                classpath_entries
            ),
            command_observations=tuple(
                command_observations
            ),
            exec_observations=tuple(
                exec_observations
            ),
        )
