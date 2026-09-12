from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


def _require_nonempty_string(
    value: str,
    *,
    name: str,
) -> None:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name} must be a string"
        )

    if not value:
        raise ValueError(
            f"{name} must not be empty"
        )


def _require_string_tuple(
    value: tuple[str, ...],
    *,
    name: str,
    allow_empty: bool = True,
) -> None:
    if not isinstance(
        value,
        tuple,
    ):
        raise TypeError(
            f"{name} must be a tuple"
        )

    if not allow_empty and not value:
        raise ValueError(
            f"{name} must not be empty"
        )

    if not all(
        isinstance(
            item,
            str,
        )
        for item in value
    ):
        raise TypeError(
            f"{name} must contain only strings"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandNoArgumentSemantics:
    """
    One INIT action command whose complete semantic form has no operands.

    The keyword remains explicit so commands sharing this structural
    shape do not lose their distinct behavior.
    """

    keyword: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandPerformApexConfigSemantics:
    """
    One INIT perform_apex_config command.

    Option tokens remain literal so Universe preserves the complete
    command grammar without prematurely interpreting APEX modes.
    """

    options: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        _require_string_tuple(
            self.options,
            name="options",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandTargetSemantics:
    """
    One INIT action command whose semantic operand is one named target.

    The exact keyword remains authoritative. This shape is shared by
    commands such as start, stop, restart, enable, exec_start,
    class_start, and class_stop without conflating their behavior.
    """

    keyword: str
    target: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_nonempty_string(
            self.target,
            name="target",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandScalarSemantics:
    """
    One INIT action command carrying one scalar semantic operand.
    """

    keyword: str
    value: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_nonempty_string(
            self.value,
            name="value",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandPathSemantics:
    """
    One INIT action command operating on one path expression.
    """

    keyword: str
    path: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_nonempty_string(
            self.path,
            name="path",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandWaitSemantics:
    """
    One INIT wait command.

    Android init accepts a required path and an optional timeout. The literal
    timeout is retained exactly while a numeric seconds interpretation is
    added when possible.
    """

    keyword: str
    path: str
    timeout: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_nonempty_string(
            self.path,
            name="path",
        )

        if (
            self.timeout is not None
            and not isinstance(
                self.timeout,
                str,
            )
        ):
            raise TypeError(
                "timeout must be a string or None"
            )

        if self.timeout == "":
            raise ValueError(
                "timeout must not be empty"
            )

    @property
    def timeout_seconds(
        self,
    ) -> float | None:
        if self.timeout is None:
            return None

        try:
            return float(
                self.timeout
            )
        except ValueError:
            return None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandPathsSemantics:
    """
    One INIT action command operating on one or more path expressions.
    """

    keyword: str
    paths: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_string_tuple(
            self.paths,
            name="paths",
            allow_empty=False,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandSetrlimitSemantics:
    """
    One INIT setrlimit command.

    The resource name and both limit expressions are retained exactly as
    declared. Numeric interpretation is deliberately left to later
    reconciliation because INIT expressions may evolve beyond literal
    integers.
    """

    resource: str
    soft_limit: str
    hard_limit: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.resource,
            name="resource",
        )
        _require_nonempty_string(
            self.soft_limit,
            name="soft_limit",
        )
        _require_nonempty_string(
            self.hard_limit,
            name="hard_limit",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandRestoreconSemantics:
    """
    One INIT restorecon command.

    Options and target paths remain distinct so recursive and other
    restorecon behavior is preserved without treating options as paths.
    """

    options: tuple[
        str,
        ...,
    ]
    paths: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        _require_string_tuple(
            self.options,
            name="options",
            allow_empty=True,
        )
        _require_string_tuple(
            self.paths,
            name="paths",
            allow_empty=False,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandInstallkeySemantics:
    """
    One INIT installkey command targeting a key-installation directory.
    """

    directory: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.directory,
            name="directory",
        )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandKeyValueSemantics:
    """
    One INIT action command carrying a key/value semantic pair.
    """

    keyword: str
    key: str
    value: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_nonempty_string(
            self.key,
            name="key",
        )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandSourceDestinationSemantics:
    """
    One INIT action command relating a source and destination path.
    """

    keyword: str
    source: str
    destination: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.keyword,
            name="keyword",
        )
        _require_nonempty_string(
            self.source,
            name="source",
        )
        _require_nonempty_string(
            self.destination,
            name="destination",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandChmodSemantics:
    """
    Canonical semantics of one INIT chmod action command.
    """

    mode: str
    path: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.mode,
            name="mode",
        )
        _require_nonempty_string(
            self.path,
            name="path",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandChownSemantics:
    """
    Canonical semantics of one INIT chown action command.

    Android permits both owner/path and owner/group/path forms.
    """

    owner: str
    group: str | None
    path: str

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.owner,
            name="owner",
        )

        if (
            self.group is not None
            and not isinstance(
                self.group,
                str,
            )
        ):
            raise TypeError(
                "group must be a string or None"
            )

        if self.group == "":
            raise ValueError(
                "group must not be empty"
            )

        _require_nonempty_string(
            self.path,
            name="path",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandMkdirSemantics:
    """
    Canonical semantics of one INIT mkdir action command.

    Optional trailing option declarations remain literal because they
    form their own Android INIT subgrammar and may expand over time.
    """

    path: str
    mode: str | None = None
    owner: str | None = None
    group: str | None = None
    options: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.path,
            name="path",
        )

        for name, value in (
            ("mode", self.mode),
            ("owner", self.owner),
            ("group", self.group),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{name} must be a string or None"
                )

            if value == "":
                raise ValueError(
                    f"{name} must not be empty"
                )

        _require_string_tuple(
            self.options,
            name="options",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandExecSemantics:
    """
    Canonical semantics of exec or exec_background.

    The Android INIT credential prefix and executable argv are separated
    when an explicit ``--`` boundary is present. Direct executable forms
    remain supported and are preserved without inventing credentials.
    """

    keyword: str
    seclabel: str | None
    user: str | None
    groups: tuple[
        str,
        ...,
    ]
    executable: str
    arguments: tuple[
        str,
        ...,
    ]
    explicit_delimiter: bool

    def __post_init__(
        self,
    ) -> None:
        if self.keyword not in {
            "exec",
            "exec_background",
        }:
            raise ValueError(
                "exec semantics keyword must be "
                "'exec' or 'exec_background'"
            )

        for name, value in (
            ("seclabel", self.seclabel),
            ("user", self.user),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{name} must be a string or None"
                )

            if value == "":
                raise ValueError(
                    f"{name} must not be empty"
                )

        _require_string_tuple(
            self.groups,
            name="groups",
        )

        _require_nonempty_string(
            self.executable,
            name="executable",
        )

        _require_string_tuple(
            self.arguments,
            name="arguments",
        )

        if not isinstance(
            self.explicit_delimiter,
            bool,
        ):
            raise TypeError(
                "explicit_delimiter must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandMountSemantics:
    """
    Canonical semantics of one INIT mount action command.

    Android INIT mount declarations identify the filesystem type,
    source, target mount point, and zero or more trailing mount
    options.  The option tokens remain literal so Universe preserves
    the complete command grammar without conflating direct INIT mounts
    with fstab-backed mount_all behavior.
    """

    filesystem_type: str
    source: str
    target: str
    options: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.filesystem_type,
            name="filesystem_type",
        )
        _require_nonempty_string(
            self.source,
            name="source",
        )
        _require_nonempty_string(
            self.target,
            name="target",
        )
        _require_string_tuple(
            self.options,
            name="options",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandFstabSemantics:
    """
    Canonical semantics of mount_all, umount_all, or swapon_all.

    mount_all may legally carry options without an explicit fstab path.
    """

    keyword: str
    fstab_path: str | None
    options: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if self.keyword not in {
            "mount_all",
            "umount_all",
            "swapon_all",
        }:
            raise ValueError(
                "fstab semantics keyword is unsupported"
            )

        if (
            self.fstab_path is not None
            and not isinstance(
                self.fstab_path,
                str,
            )
        ):
            raise TypeError(
                "fstab_path must be a string or None"
            )

        if self.fstab_path == "":
            raise ValueError(
                "fstab_path must not be empty"
            )

        _require_string_tuple(
            self.options,
            name="options",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandWriteSemantics:
    """
    Canonical semantics of one INIT write command.

    Value tokens deliberately remain a tuple. Parsing preserves lexical
    token boundaries, including quoted multi-token forms, and Universe
    must not silently rewrite that source representation.
    """

    path: str
    value_tokens: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.path,
            name="path",
        )

        _require_string_tuple(
            self.value_tokens,
            name="value_tokens",
            allow_empty=False,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandRestartSemantics:
    """
    Canonical semantics of one INIT ``restart`` command.
    """

    target: str
    only_if_running: bool = False

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.target,
            name="target",
        )

        if not isinstance(
            self.only_if_running,
            bool,
        ):
            raise TypeError(
                "only_if_running must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandClassRestartSemantics:
    """
    Canonical semantics of one INIT ``class_restart`` command.
    """

    target: str
    only_enabled: bool = False

    def __post_init__(
        self,
    ) -> None:
        _require_nonempty_string(
            self.target,
            name="target",
        )

        if not isinstance(
            self.only_enabled,
            bool,
        ):
            raise TypeError(
                "only_enabled must be a bool"
            )


AndroidUniverseInitActionCommandSemantics: TypeAlias = (
    AndroidUniverseInitActionCommandRestartSemantics
    | AndroidUniverseInitActionCommandClassRestartSemantics
    | AndroidUniverseInitActionCommandNoArgumentSemantics
    | AndroidUniverseInitActionCommandPerformApexConfigSemantics
    | AndroidUniverseInitActionCommandTargetSemantics
    | AndroidUniverseInitActionCommandScalarSemantics
    | AndroidUniverseInitActionCommandPathSemantics
    | AndroidUniverseInitActionCommandWaitSemantics
    | AndroidUniverseInitActionCommandPathsSemantics
    | AndroidUniverseInitActionCommandSetrlimitSemantics
    | AndroidUniverseInitActionCommandRestoreconSemantics
    | AndroidUniverseInitActionCommandInstallkeySemantics
    | AndroidUniverseInitActionCommandKeyValueSemantics
    | AndroidUniverseInitActionCommandSourceDestinationSemantics
    | AndroidUniverseInitActionCommandChmodSemantics
    | AndroidUniverseInitActionCommandChownSemantics
    | AndroidUniverseInitActionCommandMkdirSemantics
    | AndroidUniverseInitActionCommandExecSemantics
    | AndroidUniverseInitActionCommandFstabSemantics
    | AndroidUniverseInitActionCommandWriteSemantics
)


ANDROID_UNIVERSE_INIT_ACTION_COMMAND_SEMANTIC_TYPES = (
    AndroidUniverseInitActionCommandRestartSemantics,
    AndroidUniverseInitActionCommandClassRestartSemantics,
    AndroidUniverseInitActionCommandNoArgumentSemantics,
    AndroidUniverseInitActionCommandPerformApexConfigSemantics,
    AndroidUniverseInitActionCommandTargetSemantics,
    AndroidUniverseInitActionCommandScalarSemantics,
    AndroidUniverseInitActionCommandPathSemantics,
    AndroidUniverseInitActionCommandWaitSemantics,
    AndroidUniverseInitActionCommandPathsSemantics,
    AndroidUniverseInitActionCommandSetrlimitSemantics,
    AndroidUniverseInitActionCommandRestoreconSemantics,
    AndroidUniverseInitActionCommandInstallkeySemantics,
    AndroidUniverseInitActionCommandKeyValueSemantics,
    AndroidUniverseInitActionCommandSourceDestinationSemantics,
    AndroidUniverseInitActionCommandChmodSemantics,
    AndroidUniverseInitActionCommandChownSemantics,
    AndroidUniverseInitActionCommandMkdirSemantics,
    AndroidUniverseInitActionCommandExecSemantics,
    AndroidUniverseInitActionCommandMountSemantics,
    AndroidUniverseInitActionCommandFstabSemantics,
    AndroidUniverseInitActionCommandWriteSemantics,
)