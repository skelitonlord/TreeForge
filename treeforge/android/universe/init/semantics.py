from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.universe.init.onrestart import (
    AndroidUniverseInitOnRestartCommand,
)
from treeforge.android.parsing.init.model import (
    AndroidInitServiceOption,
)
from treeforge.android.universe.init.resources import (
    AndroidUniverseInitFileSemantics,
    AndroidUniverseInitInterfaceSemantics,
    AndroidUniverseInitSocketSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitCriticalSemantics:
    """
    Canonical semantic projection of one init ``critical`` declaration.

    Android init permits ``critical`` to carry arguments, so presence alone
    is not sufficient to preserve its semantics.
    """

    arguments: tuple[
        str,
        ...,
    ]

    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
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
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "critical":
            raise ValueError(
                "critical declaration must use keyword "
                "'critical'"
            )

        if (
            self.arguments
            != self.declaration.arguments
        ):
            raise ValueError(
                "critical arguments must preserve the "
                "original declaration arguments"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitIoPrioritySemantics:
    """
    Canonical projection of one init ``ioprio`` declaration.
    """

    class_name: str
    priority: int
    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.class_name,
            str,
        ):
            raise TypeError(
                "class_name must be a string"
            )

        if not self.class_name:
            raise ValueError(
                "class_name must not be empty"
            )

        if not isinstance(
            self.priority,
            int,
        ):
            raise TypeError(
                "priority must be an int"
            )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "ioprio":
            raise ValueError(
                "ioprio declaration must use keyword "
                "'ioprio'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitRlimitSemantics:
    """
    Canonical projection of one init ``rlimit`` declaration.

    Limits remain strings because Android permits symbolic values such as
    ``unlimited`` as well as numeric limits.
    """

    resource: str
    soft_limit: str
    hard_limit: str
    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            ("resource", self.resource),
            ("soft_limit", self.soft_limit),
            ("hard_limit", self.hard_limit),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "rlimit":
            raise ValueError(
                "rlimit declaration must use keyword "
                "'rlimit'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitEnvironmentSemantics:
    """
    Canonical projection of one init ``setenv`` declaration.
    """

    name: str
    value: str
    declaration: AndroidInitServiceOption

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
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "setenv":
            raise ValueError(
                "setenv declaration must use keyword "
                "'setenv'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitRebootOnFailureSemantics:
    """
    Canonical projection of one ``reboot_on_failure`` declaration.

    The reboot target is retained as one literal value. Its comma-delimited
    grammar is intentionally not interpreted by this intrinsic-service
    layer.
    """

    target: str
    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.target,
            str,
        ):
            raise TypeError(
                "target must be a string"
            )

        if not self.target:
            raise ValueError(
                "target must not be empty"
            )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if (
            self.declaration.keyword
            != "reboot_on_failure"
        ):
            raise ValueError(
                "reboot_on_failure declaration must use "
                "keyword 'reboot_on_failure'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitKeycodesSemantics:
    """
    Canonical projection of one init ``keycodes`` declaration.

    Key codes are interpreted as integers while the complete original
    declaration remains attached for literal syntax and provenance.
    """

    keycodes: tuple[
        int,
        ...,
    ]

    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.keycodes,
            tuple,
        ):
            raise TypeError(
                "keycodes must be a tuple"
            )

        if not self.keycodes:
            raise ValueError(
                "keycodes must not be empty"
            )

        if not all(
            isinstance(
                value,
                int,
            )
            for value in self.keycodes
        ):
            raise TypeError(
                "keycodes must contain only integers"
            )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "keycodes":
            raise ValueError(
                "keycodes declaration must use keyword "
                "'keycodes'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitServiceSemantics:
    """
    Canonical semantic projection of intrinsic init-service configuration.

    The complete original service declaration remains attached to the
    Universe requirement. This object adds semantic interpretation without
    replacing or collapsing Parsing evidence.

    Tuple-valued declarations use ``None`` for absence so an explicit empty
    declaration remains distinguishable from no declaration at all.
    """

    classes: tuple[
        str,
        ...,
    ] | None = None

    user: str | None = None

    groups: tuple[
        str,
        ...,
    ] | None = None

    capabilities: tuple[
        str,
        ...,
    ] | None = None

    seclabel: str | None = None

    disabled: bool = False
    oneshot: bool = False
    override: bool = False

    critical: (
        AndroidUniverseInitCriticalSemantics
        | None
    ) = None

    task_profiles: tuple[
        str,
        ...,
    ] | None = None

    ioprio: (
        AndroidUniverseInitIoPrioritySemantics
        | None
    ) = None

    priority: int | None = None

    rlimits: tuple[
        AndroidUniverseInitRlimitSemantics,
        ...,
    ] = ()

    stdio_to_kmsg: bool = False

    environment: tuple[
        AndroidUniverseInitEnvironmentSemantics,
        ...,
    ] = ()

    namespaces: tuple[
        str,
        ...,
    ] | None = None

    updatable: bool = False

    writepid_paths: tuple[
        str,
        ...,
    ] | None = None

    console: bool = False
    gentle_kill: bool = False

    restart_period: int | None = None
    timeout_period: int | None = None

    shutdown: str | None = None

    reboot_on_failure: (
        AndroidUniverseInitRebootOnFailureSemantics
        | None
    ) = None

    sockets: tuple[
        AndroidUniverseInitSocketSemantics,
        ...,
    ] = ()

    files: tuple[
        AndroidUniverseInitFileSemantics,
        ...,
    ] = ()

    interfaces: tuple[
        AndroidUniverseInitInterfaceSemantics,
        ...,
    ] = ()

    onrestart_commands: tuple[
        AndroidUniverseInitOnRestartCommand,
        ...,
    ] = ()

    keycodes: (
        AndroidUniverseInitKeycodesSemantics
        | None
    ) = None

    uninterpreted_options: tuple[
        AndroidInitServiceOption,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for field_name, values in (
            (
                "classes",
                self.classes,
            ),
            (
                "groups",
                self.groups,
            ),
            (
                "capabilities",
                self.capabilities,
            ),
        ):
            if (
                values is not None
                and not isinstance(
                    values,
                    tuple,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a tuple or None"
                )

            if (
                values is not None
                and not all(
                    isinstance(
                        value,
                        str,
                    )
                    for value in values
                )
            ):
                raise TypeError(
                    f"{field_name} must contain only strings"
                )

        for field_name, value in (
            (
                "user",
                self.user,
            ),
            (
                "seclabel",
                self.seclabel,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )

            if value == "":
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        for field_name, value in (
            (
                "disabled",
                self.disabled,
            ),
            (
                "oneshot",
                self.oneshot,
            ),
            (
                "override",
                self.override,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a bool"
                )

        if (
            self.critical is not None
            and not isinstance(
                self.critical,
                AndroidUniverseInitCriticalSemantics,
            )
        ):
            raise TypeError(
                "critical must be an "
                "AndroidUniverseInitCriticalSemantics "
                "or None"
            )

        for field_name, values in (
            (
                "task_profiles",
                self.task_profiles,
            ),
            (
                "namespaces",
                self.namespaces,
            ),
            (
                "writepid_paths",
                self.writepid_paths,
            ),
        ):
            if (
                values is not None
                and not isinstance(
                    values,
                    tuple,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a tuple or None"
                )

            if (
                values is not None
                and not all(
                    isinstance(
                        value,
                        str,
                    )
                    for value in values
                )
            ):
                raise TypeError(
                    f"{field_name} must contain only strings"
                )

        if (
            self.ioprio is not None
            and not isinstance(
                self.ioprio,
                AndroidUniverseInitIoPrioritySemantics,
            )
        ):
            raise TypeError(
                "ioprio must be an "
                "AndroidUniverseInitIoPrioritySemantics "
                "or None"
            )

        if (
            self.priority is not None
            and not isinstance(
                self.priority,
                int,
            )
        ):
            raise TypeError(
                "priority must be an int or None"
            )

        if not isinstance(
            self.rlimits,
            tuple,
        ):
            raise TypeError(
                "rlimits must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseInitRlimitSemantics,
            )
            for value in self.rlimits
        ):
            raise TypeError(
                "rlimits must contain only "
                "AndroidUniverseInitRlimitSemantics"
            )

        if not isinstance(
            self.environment,
            tuple,
        ):
            raise TypeError(
                "environment must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseInitEnvironmentSemantics,
            )
            for value in self.environment
        ):
            raise TypeError(
                "environment must contain only "
                "AndroidUniverseInitEnvironmentSemantics"
            )

        for field_name, value in (
            (
                "stdio_to_kmsg",
                self.stdio_to_kmsg,
            ),
            (
                "updatable",
                self.updatable,
            ),
            (
                "console",
                self.console,
            ),
            (
                "gentle_kill",
                self.gentle_kill,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a bool"
                )

        for field_name, value in (
            (
                "restart_period",
                self.restart_period,
            ),
            (
                "timeout_period",
                self.timeout_period,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int or None"
                )

        if (
            self.shutdown is not None
            and not isinstance(
                self.shutdown,
                str,
            )
        ):
            raise TypeError(
                "shutdown must be a string or None"
            )

        if self.shutdown == "":
            raise ValueError(
                "shutdown must not be empty"
            )

        if (
            self.reboot_on_failure is not None
            and not isinstance(
                self.reboot_on_failure,
                AndroidUniverseInitRebootOnFailureSemantics,
            )
        ):
            raise TypeError(
                "reboot_on_failure must be an "
                "AndroidUniverseInitRebootOnFailureSemantics "
                "or None"
            )

        for field_name, values, expected_type in (
            (
                "sockets",
                self.sockets,
                AndroidUniverseInitSocketSemantics,
            ),
            (
                "files",
                self.files,
                AndroidUniverseInitFileSemantics,
            ),
            (
                "interfaces",
                self.interfaces,
                AndroidUniverseInitInterfaceSemantics,
            ),
        ):
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
                    f"{field_name} contains an invalid "
                    "semantic declaration"
                )

        if not isinstance(
            self.onrestart_commands,
            tuple,
        ):
            raise TypeError(
                "onrestart_commands must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseInitOnRestartCommand,
            )
            for value in self.onrestart_commands
        ):
            raise TypeError(
                "onrestart_commands must contain only "
                "AndroidUniverseInitOnRestartCommand"
            )

        if (
            self.keycodes is not None
            and not isinstance(
                self.keycodes,
                AndroidUniverseInitKeycodesSemantics,
            )
        ):
            raise TypeError(
                "keycodes must be an "
                "AndroidUniverseInitKeycodesSemantics "
                "or None"
            )

        if not isinstance(
            self.uninterpreted_options,
            tuple,
        ):
            raise TypeError(
                "uninterpreted_options must be a tuple"
            )

        if not all(
            isinstance(
                option,
                AndroidInitServiceOption,
            )
            for option
            in self.uninterpreted_options
        ):
            raise TypeError(
                "uninterpreted_options must contain only "
                "AndroidInitServiceOption instances"
            )
