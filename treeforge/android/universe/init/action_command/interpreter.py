from __future__ import annotations

from treeforge.android.parsing.init.model import (
    AndroidInitCommand,
)
from treeforge.android.universe.init.action_command.model import (
    AndroidUniverseInitActionCommandRequirement,
)
from treeforge.android.universe.init.action_command.semantics import (
    AndroidUniverseInitActionCommandChmodSemantics,
    AndroidUniverseInitActionCommandClassRestartSemantics,
    AndroidUniverseInitActionCommandChownSemantics,
    AndroidUniverseInitActionCommandExecSemantics,
    AndroidUniverseInitActionCommandFstabSemantics,
    AndroidUniverseInitActionCommandKeyValueSemantics,
    AndroidUniverseInitActionCommandMkdirSemantics,
    AndroidUniverseInitActionCommandMountSemantics,
    AndroidUniverseInitActionCommandNoArgumentSemantics,
    AndroidUniverseInitActionCommandPerformApexConfigSemantics,
    AndroidUniverseInitActionCommandPathSemantics,
    AndroidUniverseInitActionCommandPathsSemantics,
    AndroidUniverseInitActionCommandSetrlimitSemantics,
    AndroidUniverseInitActionCommandRestoreconSemantics,
    AndroidUniverseInitActionCommandRestartSemantics,
    AndroidUniverseInitActionCommandInstallkeySemantics,
    AndroidUniverseInitActionCommandScalarSemantics,
    AndroidUniverseInitActionCommandSourceDestinationSemantics,
    AndroidUniverseInitActionCommandTargetSemantics,
    AndroidUniverseInitActionCommandWaitSemantics,
    AndroidUniverseInitActionCommandWriteSemantics,
)


class AndroidUniverseInitActionCommandInterpreter:
    """
    Interpret the complete canonical INIT action-command vocabulary.

    This interpreter is intentionally specific to commands owned by
    AndroidUniverseInitActionRequirement. Service ``onrestart`` commands
    remain a separate Universe semantic family.
    """

    SUPPORTED_KEYWORDS = frozenset(
        {
            "bootchart",
            "chmod",
            "chown",
            "class_restart",
            "class_start",
            "class_stop",
            "copy",
            "domainname",
            "enable",
            "enter_default_mount_ns",
            "exec",
            "exec_background",
            "exec_start",
            "export",
            "hostname",
            "ifup",
            "import",
            "init_user0",
            "installkey",
            "load_exports",
            "load_persist_props",
            "loglevel",
            "mark_post_data",
            "mkdir",
            "mount",
            "mount_all",
            "perform_apex_config",
            "restart",
            "restorecon",
            "restorecon_recursive",
            "remount_userdata",
            "rm",
            "rmdir",
            "setprop",
            "setrlimit",
            "start",
            "stop",
            "swapon_all",
            "symlink",
            "sysclktz",
            "trigger",
            "umount",
            "umount_all",
            "verity_update_state",
            "wait",
            "wait_for_prop",
            "write",
        }
    )

    _NO_ARGUMENT_KEYWORDS = frozenset(
        {
            "enter_default_mount_ns",
            "init_user0",
            "load_persist_props",
            "mark_post_data",
            "remount_userdata",
            "verity_update_state",
        }
    )

    _TARGET_KEYWORDS = frozenset(
        {
            "class_start",
            "class_stop",
            "enable",
            "exec_start",
            "start",
            "stop",
        }
    )

    _SCALAR_KEYWORDS = frozenset(
        {
            "bootchart",
            "domainname",
            "hostname",
            "ifup",
            "loglevel",
            "sysclktz",
            "trigger",
        }
    )

    _PATH_KEYWORDS = frozenset(
        {
            "import",
            "load_exports",
            "rm",
            "rmdir",
        }
    )

    _KEY_VALUE_KEYWORDS = frozenset(
        {
            "export",
            "setprop",
            "wait_for_prop",
        }
    )

    _SOURCE_DESTINATION_KEYWORDS = frozenset(
        {
            "copy",
            "symlink",
        }
    )

    def interpret(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandRequirement:
        if not isinstance(
            command,
            AndroidInitCommand,
        ):
            raise TypeError(
                "command must be an AndroidInitCommand"
            )

        keyword = command.keyword
        arguments = command.arguments

        if keyword not in self.SUPPORTED_KEYWORDS:
            raise ValueError(
                "unsupported INIT action command keyword: "
                f"{keyword!r}"
            )

        if keyword in self._NO_ARGUMENT_KEYWORDS:
            semantics = self._interpret_no_argument(
                command
            )

        elif keyword == "perform_apex_config":
            semantics = self._interpret_perform_apex_config(
                command
            )

        elif keyword == "class_restart":
            semantics = self._interpret_class_restart(
                command
            )

        elif keyword == "restart":
            semantics = self._interpret_restart(
                command
            )

        elif keyword in self._TARGET_KEYWORDS:
            semantics = self._interpret_target(
                command
            )

        elif keyword in self._SCALAR_KEYWORDS:
            semantics = self._interpret_scalar(
                command
            )

        elif keyword == "wait":
            semantics = self._interpret_wait(
                command
            )

        elif keyword in self._PATH_KEYWORDS:
            semantics = self._interpret_path(
                command
            )

        elif keyword == "restorecon":
            semantics = self._interpret_restorecon(
                command
            )

        elif keyword == "restorecon_recursive":
            semantics = self._interpret_paths(
                command
            )

        elif keyword == "setrlimit":
            semantics = self._interpret_setrlimit(
                command
            )

        elif keyword == "installkey":
            semantics = self._interpret_installkey(
                command
            )

        elif keyword in self._KEY_VALUE_KEYWORDS:
            semantics = self._interpret_key_value(
                command
            )

        elif keyword in self._SOURCE_DESTINATION_KEYWORDS:
            semantics = (
                self._interpret_source_destination(
                    command
                )
            )

        elif keyword == "chmod":
            self._require_argument_count(
                command,
                exact=2,
            )

            semantics = (
                AndroidUniverseInitActionCommandChmodSemantics(
                    mode=arguments[0],
                    path=arguments[1],
                )
            )

        elif keyword == "chown":
            if len(arguments) == 2:
                semantics = (
                    AndroidUniverseInitActionCommandChownSemantics(
                        owner=arguments[0],
                        group=None,
                        path=arguments[1],
                    )
                )

            elif len(arguments) == 3:
                semantics = (
                    AndroidUniverseInitActionCommandChownSemantics(
                        owner=arguments[0],
                        group=arguments[1],
                        path=arguments[2],
                    )
                )

            else:
                self._raise_shape_error(
                    command,
                    "expected owner/path or "
                    "owner/group/path",
                )

        elif keyword == "mkdir":
            semantics = self._interpret_mkdir(
                command
            )

        elif keyword in {
            "exec",
            "exec_background",
        }:
            semantics = self._interpret_exec(
                command
            )

        elif keyword == "mount":
            if len(arguments) < 3:
                self._raise_shape_error(
                    command,
                    "expected filesystem type, source, target, "
                    "and optional mount options",
                )

            semantics = (
                AndroidUniverseInitActionCommandMountSemantics(
                    filesystem_type=arguments[0],
                    source=arguments[1],
                    target=arguments[2],
                    options=tuple(
                        arguments[3:]
                    ),
                )
            )

        elif keyword == "umount":
            self._require_argument_count(
                command,
                exact=1,
            )

            semantics = (
                AndroidUniverseInitActionCommandPathSemantics(
                    keyword=keyword,
                    path=arguments[0],
                )
            )

        elif keyword == "mount_all":
            semantics = self._interpret_mount_all(
                command
            )

        elif keyword in {
            "swapon_all",
            "umount_all",
        }:
            self._require_argument_count(
                command,
                exact=1,
            )

            semantics = (
                AndroidUniverseInitActionCommandFstabSemantics(
                    keyword=keyword,
                    fstab_path=arguments[0],
                    options=(),
                )
            )

        elif keyword == "write":
            if len(arguments) < 2:
                self._raise_shape_error(
                    command,
                    "expected path plus at least one value token",
                )

            semantics = (
                AndroidUniverseInitActionCommandWriteSemantics(
                    path=arguments[0],
                    value_tokens=tuple(
                        arguments[1:]
                    ),
                )
            )

        else:
            raise AssertionError(
                "supported keyword was not dispatched: "
                f"{keyword!r}"
            )

        return (
            AndroidUniverseInitActionCommandRequirement(
                command=command,
                semantics=semantics,
            )
        )

    def interpret_all(
        self,
        commands: tuple[
            AndroidInitCommand,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitActionCommandRequirement,
        ...,
    ]:
        if not isinstance(
            commands,
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
            for command in commands
        ):
            raise TypeError(
                "commands must contain only "
                "AndroidInitCommand instances"
            )

        return tuple(
            self.interpret(
                command
            )
            for command in commands
        )

    def _interpret_no_argument(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandNoArgumentSemantics:
        self._require_argument_count(
            command,
            exact=0,
        )

        return (
            AndroidUniverseInitActionCommandNoArgumentSemantics(
                keyword=command.keyword,
            )
        )

    def _interpret_perform_apex_config(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandPerformApexConfigSemantics:
        for argument in command.arguments:
            if not argument.startswith("--"):
                self._raise_shape_error(
                    command,
                    "expected only perform_apex_config options",
                )

        return (
            AndroidUniverseInitActionCommandPerformApexConfigSemantics(
                options=command.arguments,
            )
        )

    def _interpret_restart(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandRestartSemantics:
        arguments = command.arguments

        if len(arguments) == 1:
            return (
                AndroidUniverseInitActionCommandRestartSemantics(
                    target=arguments[0],
                    only_if_running=False,
                )
            )

        if (
            len(arguments) == 2
            and arguments[0]
            == "--only-if-running"
        ):
            return (
                AndroidUniverseInitActionCommandRestartSemantics(
                    target=arguments[1],
                    only_if_running=True,
                )
            )

        self._raise_shape_error(
            command,
            "expected service name with optional "
            "'--only-if-running'",
        )

    def _interpret_class_restart(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandClassRestartSemantics:
        arguments = command.arguments

        if len(arguments) == 1:
            return (
                AndroidUniverseInitActionCommandClassRestartSemantics(
                    target=arguments[0],
                    only_enabled=False,
                )
            )

        if (
            len(arguments) == 2
            and arguments[0] == "--only-enabled"
        ):
            return (
                AndroidUniverseInitActionCommandClassRestartSemantics(
                    target=arguments[1],
                    only_enabled=True,
                )
            )

        self._raise_shape_error(
            command,
            "expected class name with optional '--only-enabled'",
        )

    def _interpret_target(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandTargetSemantics:
        self._require_argument_count(
            command,
            exact=1,
        )

        return (
            AndroidUniverseInitActionCommandTargetSemantics(
                keyword=command.keyword,
                target=command.arguments[0],
            )
        )

    def _interpret_scalar(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandScalarSemantics:
        self._require_argument_count(
            command,
            exact=1,
        )

        return (
            AndroidUniverseInitActionCommandScalarSemantics(
                keyword=command.keyword,
                value=command.arguments[0],
            )
        )

    def _interpret_path(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandPathSemantics:
        self._require_argument_count(
            command,
            exact=1,
        )

        return (
            AndroidUniverseInitActionCommandPathSemantics(
                keyword=command.keyword,
                path=command.arguments[0],
            )
        )

    def _interpret_wait(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandWaitSemantics:
        arguments = command.arguments

        if len(arguments) not in {
            1,
            2,
        }:
            self._raise_shape_error(
                command,
                "expected path with optional timeout",
            )

        timeout = (
            arguments[1]
            if len(arguments) == 2
            else None
        )

        return (
            AndroidUniverseInitActionCommandWaitSemantics(
                keyword=command.keyword,
                path=arguments[0],
                timeout=timeout,
            )
        )

    def _interpret_paths(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandPathsSemantics:
        if not command.arguments:
            self._raise_shape_error(
                command,
                "expected at least one path",
            )

        return (
            AndroidUniverseInitActionCommandPathsSemantics(
                keyword=command.keyword,
                paths=command.arguments,
            )
        )

    def _interpret_setrlimit(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandSetrlimitSemantics:
        self._require_argument_count(
            command,
            exact=3,
        )

        return (
            AndroidUniverseInitActionCommandSetrlimitSemantics(
                resource=command.arguments[0],
                soft_limit=command.arguments[1],
                hard_limit=command.arguments[2],
            )
        )

    def _interpret_restorecon(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandRestoreconSemantics:
        if not command.arguments:
            self._raise_shape_error(
                command,
                "expected restorecon path",
            )

        options = []
        paths = []

        for argument in command.arguments:
            if (
                not paths
                and argument.startswith("--")
            ):
                options.append(
                    argument
                )
            else:
                paths.append(
                    argument
                )

        if not paths:
            self._raise_shape_error(
                command,
                "expected at least one restorecon path",
            )

        return (
            AndroidUniverseInitActionCommandRestoreconSemantics(
                options=tuple(
                    options
                ),
                paths=tuple(
                    paths
                ),
            )
        )

    def _interpret_installkey(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandInstallkeySemantics:
        self._require_argument_count(
            command,
            exact=1,
        )

        return (
            AndroidUniverseInitActionCommandInstallkeySemantics(
                directory=command.arguments[0],
            )
        )


    def _interpret_key_value(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandKeyValueSemantics:
        self._require_argument_count(
            command,
            exact=2,
        )

        return (
            AndroidUniverseInitActionCommandKeyValueSemantics(
                keyword=command.keyword,
                key=command.arguments[0],
                value=command.arguments[1],
            )
        )

    def _interpret_source_destination(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandSourceDestinationSemantics:
        self._require_argument_count(
            command,
            exact=2,
        )

        return (
            AndroidUniverseInitActionCommandSourceDestinationSemantics(
                keyword=command.keyword,
                source=command.arguments[0],
                destination=command.arguments[1],
            )
        )

    def _interpret_mkdir(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandMkdirSemantics:
        arguments = command.arguments

        if not arguments:
            self._raise_shape_error(
                command,
                "expected directory path",
            )

        path = arguments[0]

        positional = []
        options = []

        for value in arguments[1:]:
            if (
                "=" in value
                or options
            ):
                options.append(
                    value
                )
            else:
                positional.append(
                    value
                )

        if len(positional) > 3:
            self._raise_shape_error(
                command,
                "expected at most mode/owner/group "
                "before mkdir options",
            )

        mode = (
            positional[0]
            if len(positional) >= 1
            else None
        )

        owner = (
            positional[1]
            if len(positional) >= 2
            else None
        )

        group = (
            positional[2]
            if len(positional) >= 3
            else None
        )

        return (
            AndroidUniverseInitActionCommandMkdirSemantics(
                path=path,
                mode=mode,
                owner=owner,
                group=group,
                options=tuple(
                    options
                ),
            )
        )

    def _interpret_exec(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandExecSemantics:
        arguments = command.arguments

        if not arguments:
            self._raise_shape_error(
                command,
                "expected executable declaration",
            )

        if "--" not in arguments:
            return (
                AndroidUniverseInitActionCommandExecSemantics(
                    keyword=command.keyword,
                    seclabel=None,
                    user=None,
                    groups=(),
                    executable=arguments[0],
                    arguments=tuple(
                        arguments[1:]
                    ),
                    explicit_delimiter=False,
                )
            )

        delimiter_index = arguments.index(
            "--"
        )

        prefix = arguments[
            :delimiter_index
        ]

        payload = arguments[
            delimiter_index + 1:
        ]

        if not payload:
            self._raise_shape_error(
                command,
                "expected executable after '--'",
            )

        seclabel = (
            prefix[0]
            if len(prefix) >= 1
            else None
        )

        user = (
            prefix[1]
            if len(prefix) >= 2
            else None
        )

        groups = tuple(
            prefix[2:]
        )

        return (
            AndroidUniverseInitActionCommandExecSemantics(
                keyword=command.keyword,
                seclabel=seclabel,
                user=user,
                groups=groups,
                executable=payload[0],
                arguments=tuple(
                    payload[1:]
                ),
                explicit_delimiter=True,
            )
        )

    def _interpret_mount_all(
        self,
        command: AndroidInitCommand,
    ) -> AndroidUniverseInitActionCommandFstabSemantics:
        arguments = command.arguments

        if not arguments:
            self._raise_shape_error(
                command,
                "expected fstab path and/or mount_all options",
            )

        first = arguments[0]

        if first.startswith(
            "--"
        ):
            return (
                AndroidUniverseInitActionCommandFstabSemantics(
                    keyword="mount_all",
                    fstab_path=None,
                    options=arguments,
                )
            )

        return (
            AndroidUniverseInitActionCommandFstabSemantics(
                keyword="mount_all",
                fstab_path=first,
                options=tuple(
                    arguments[1:]
                ),
            )
        )

    @staticmethod
    def _require_argument_count(
        command: AndroidInitCommand,
        *,
        exact: int,
    ) -> None:
        if len(
            command.arguments
        ) != exact:
            AndroidUniverseInitActionCommandInterpreter._raise_shape_error(
                command,
                f"expected exactly {exact} arguments",
            )

    @staticmethod
    def _raise_shape_error(
        command: AndroidInitCommand,
        expectation: str,
    ) -> None:
        raise ValueError(
            "invalid INIT action command shape for "
            f"{command.keyword!r} at "
            f"{command.location.file}:"
            f"{command.location.line}: "
            f"{expectation}; found "
            f"{command.arguments!r}"
        )