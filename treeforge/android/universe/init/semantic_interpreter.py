from __future__ import annotations

from treeforge.android.parsing.init.model import (
    AndroidInitService,
    AndroidInitServiceOption,
)
from treeforge.android.universe.init.onrestart_interpreter import (
    AndroidUniverseInitOnRestartInterpreter,
)
from treeforge.android.universe.init.resource_interpreter import (
    AndroidUniverseInitServiceResourceInterpreter,
)
from treeforge.android.universe.init.semantics import (
    AndroidUniverseInitCriticalSemantics,
    AndroidUniverseInitEnvironmentSemantics,
    AndroidUniverseInitIoPrioritySemantics,
    AndroidUniverseInitKeycodesSemantics,
    AndroidUniverseInitRebootOnFailureSemantics,
    AndroidUniverseInitRlimitSemantics,
    AndroidUniverseInitServiceSemantics,
)


class AndroidUniverseInitServiceSemanticInterpreter:
    """
    Interpret intrinsic Android init service-option semantics.

    Cross-artifact relationships such as sockets, interfaces, files,
    onrestart commands, service control, and trigger applicability are
    intentionally left for later Universe capabilities.
    """

    _INTERPRETED_KEYWORDS = frozenset(
        {
            "class",
            "user",
            "group",
            "capabilities",
            "seclabel",
            "disabled",
            "oneshot",
            "override",
            "critical",
            "task_profiles",
            "ioprio",
            "priority",
            "rlimit",
            "stdio_to_kmsg",
            "setenv",
            "namespace",
            "updatable",
            "writepid",
            "console",
            "gentle_kill",
            "restart_period",
            "timeout_period",
            "shutdown",
            "reboot_on_failure",
            "socket",
            "file",
            "interface",
            "onrestart",
            "keycodes",
        }
    )

    def interpret(
        self,
        service: AndroidInitService,
    ) -> AndroidUniverseInitServiceSemantics:
        if not isinstance(
            service,
            AndroidInitService,
        ):
            raise TypeError(
                "service must be an AndroidInitService"
            )

        classes = self._optional_arguments(
            service,
            "class",
        )

        user = self._optional_scalar(
            service,
            "user",
        )

        groups = self._optional_arguments(
            service,
            "group",
        )

        capabilities = self._optional_arguments(
            service,
            "capabilities",
        )

        seclabel = self._optional_scalar(
            service,
            "seclabel",
        )

        disabled = self._flag(
            service,
            "disabled",
        )

        oneshot = self._flag(
            service,
            "oneshot",
        )

        override = self._flag(
            service,
            "override",
        )

        critical_declaration = (
            self._optional_single(
                service,
                "critical",
            )
        )

        critical = (
            AndroidUniverseInitCriticalSemantics(
                arguments=(
                    critical_declaration.arguments
                ),
                declaration=(
                    critical_declaration
                ),
            )
            if critical_declaration is not None
            else None
        )

        task_profiles = self._optional_arguments(
            service,
            "task_profiles",
        )

        ioprio_declaration = self._optional_single(
            service,
            "ioprio",
        )

        ioprio = None

        if ioprio_declaration is not None:
            if len(
                ioprio_declaration.arguments
            ) != 2:
                raise ValueError(
                    "expected exactly two arguments for "
                    "init service option 'ioprio' on "
                    f"service {service.name!r}; found "
                    f"{len(ioprio_declaration.arguments)}"
                )

            try:
                ioprio_priority = int(
                    ioprio_declaration.arguments[1]
                )
            except ValueError as exc:
                raise ValueError(
                    "expected integer ioprio priority on "
                    f"service {service.name!r}; found "
                    f"{ioprio_declaration.arguments[1]!r}"
                ) from exc

            ioprio = (
                AndroidUniverseInitIoPrioritySemantics(
                    class_name=(
                        ioprio_declaration.arguments[0]
                    ),
                    priority=ioprio_priority,
                    declaration=ioprio_declaration,
                )
            )

        priority = self._optional_integer(
            service,
            "priority",
        )

        rlimits = []

        for declaration in service.options_for(
            "rlimit"
        ):
            if len(
                declaration.arguments
            ) != 3:
                raise ValueError(
                    "expected exactly three arguments for "
                    "init service option 'rlimit' on "
                    f"service {service.name!r}; found "
                    f"{len(declaration.arguments)}"
                )

            rlimits.append(
                AndroidUniverseInitRlimitSemantics(
                    resource=declaration.arguments[0],
                    soft_limit=declaration.arguments[1],
                    hard_limit=declaration.arguments[2],
                    declaration=declaration,
                )
            )

        stdio_to_kmsg = self._flag(
            service,
            "stdio_to_kmsg",
        )

        environment = []

        for declaration in service.options_for(
            "setenv"
        ):
            if len(
                declaration.arguments
            ) != 2:
                raise ValueError(
                    "expected exactly two arguments for "
                    "init service option 'setenv' on "
                    f"service {service.name!r}; found "
                    f"{len(declaration.arguments)}"
                )

            environment.append(
                AndroidUniverseInitEnvironmentSemantics(
                    name=declaration.arguments[0],
                    value=declaration.arguments[1],
                    declaration=declaration,
                )
            )

        namespaces = self._optional_arguments(
            service,
            "namespace",
        )

        updatable = self._flag(
            service,
            "updatable",
        )

        writepid_paths = self._optional_arguments(
            service,
            "writepid",
        )

        console = self._flag(
            service,
            "console",
        )

        gentle_kill = self._flag(
            service,
            "gentle_kill",
        )

        restart_period = self._optional_integer(
            service,
            "restart_period",
        )

        timeout_period = self._optional_integer(
            service,
            "timeout_period",
        )

        shutdown = self._optional_scalar(
            service,
            "shutdown",
        )

        reboot_declaration = self._optional_single(
            service,
            "reboot_on_failure",
        )

        reboot_on_failure = None

        if reboot_declaration is not None:
            if len(
                reboot_declaration.arguments
            ) != 1:
                raise ValueError(
                    "expected exactly one argument for "
                    "init service option "
                    "'reboot_on_failure' on service "
                    f"{service.name!r}; found "
                    f"{len(reboot_declaration.arguments)}"
                )

            reboot_on_failure = (
                AndroidUniverseInitRebootOnFailureSemantics(
                    target=(
                        reboot_declaration.arguments[0]
                    ),
                    declaration=reboot_declaration,
                )
            )

        resource_interpreter = (
            AndroidUniverseInitServiceResourceInterpreter()
        )

        sockets = resource_interpreter.sockets(
            service
        )

        files = resource_interpreter.files(
            service
        )

        interfaces = resource_interpreter.interfaces(
            service
        )

        onrestart_commands = (
            AndroidUniverseInitOnRestartInterpreter()
            .interpret(
                service
            )
        )

        keycodes_declaration = (
            self._optional_single(
                service,
                "keycodes",
            )
        )

        keycodes = None

        if keycodes_declaration is not None:
            if not keycodes_declaration.arguments:
                raise ValueError(
                    "expected at least one key code for "
                    "init service option 'keycodes' on "
                    f"service {service.name!r}"
                )

            parsed_keycodes = []

            for value in keycodes_declaration.arguments:
                try:
                    parsed_keycodes.append(
                        int(
                            value
                        )
                    )
                except ValueError as exc:
                    raise ValueError(
                        "expected integer key code for "
                        "init service option 'keycodes' on "
                        f"service {service.name!r}; found "
                        f"{value!r}"
                    ) from exc

            keycodes = (
                AndroidUniverseInitKeycodesSemantics(
                    keycodes=tuple(
                        parsed_keycodes
                    ),
                    declaration=(
                        keycodes_declaration
                    ),
                )
            )

        uninterpreted_options = tuple(
            option
            for option in service.options
            if (
                option.keyword
                not in self._INTERPRETED_KEYWORDS
            )
        )

        return AndroidUniverseInitServiceSemantics(
            classes=classes,
            user=user,
            groups=groups,
            capabilities=capabilities,
            seclabel=seclabel,
            disabled=disabled,
            oneshot=oneshot,
            override=override,
            critical=critical,
            task_profiles=task_profiles,
            ioprio=ioprio,
            priority=priority,
            rlimits=tuple(
                rlimits
            ),
            stdio_to_kmsg=stdio_to_kmsg,
            environment=tuple(
                environment
            ),
            namespaces=namespaces,
            updatable=updatable,
            writepid_paths=writepid_paths,
            console=console,
            gentle_kill=gentle_kill,
            restart_period=restart_period,
            timeout_period=timeout_period,
            shutdown=shutdown,
            reboot_on_failure=reboot_on_failure,
            sockets=sockets,
            files=files,
            interfaces=interfaces,
            onrestart_commands=onrestart_commands,
            keycodes=keycodes,
            uninterpreted_options=(
                uninterpreted_options
            ),
        )

    @staticmethod
    def _optional_single(
        service: AndroidInitService,
        keyword: str,
    ) -> AndroidInitServiceOption | None:
        declarations = (
            service.options_for(
                keyword
            )
        )

        if len(
            declarations
        ) > 1:
            raise ValueError(
                "expected at most one init service "
                f"{keyword!r} declaration for "
                f"service {service.name!r}; found "
                f"{len(declarations)}"
            )

        if not declarations:
            return None

        return declarations[0]

    @classmethod
    def _optional_arguments(
        cls,
        service: AndroidInitService,
        keyword: str,
    ) -> tuple[
        str,
        ...,
    ] | None:
        declaration = cls._optional_single(
            service,
            keyword,
        )

        if declaration is None:
            return None

        return declaration.arguments

    @classmethod
    def _optional_scalar(
        cls,
        service: AndroidInitService,
        keyword: str,
    ) -> str | None:
        declaration = cls._optional_single(
            service,
            keyword,
        )

        if declaration is None:
            return None

        if len(
            declaration.arguments
        ) != 1:
            raise ValueError(
                "expected exactly one argument for "
                f"init service option {keyword!r} "
                f"on service {service.name!r}; found "
                f"{len(declaration.arguments)}"
            )

        return declaration.arguments[0]

    @classmethod
    def _optional_integer(
        cls,
        service: AndroidInitService,
        keyword: str,
    ) -> int | None:
        value = cls._optional_scalar(
            service,
            keyword,
        )

        if value is None:
            return None

        try:
            return int(
                value
            )
        except ValueError as exc:
            raise ValueError(
                "expected integer argument for init "
                f"service option {keyword!r} on "
                f"service {service.name!r}; found "
                f"{value!r}"
            ) from exc

    @classmethod
    def _flag(
        cls,
        service: AndroidInitService,
        keyword: str,
    ) -> bool:
        declaration = cls._optional_single(
            service,
            keyword,
        )

        if declaration is None:
            return False

        if declaration.arguments:
            raise ValueError(
                "expected no arguments for init "
                f"service flag {keyword!r} on "
                f"service {service.name!r}; found "
                f"{declaration.arguments!r}"
            )

        return True
