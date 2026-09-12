from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdImport:
    """
    One parsed ueventd import declaration.
    """

    path: str
    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdDeviceRule:
    """
    One parsed /dev permission declaration.
    """

    path: str
    mode: str
    user: str
    group: str

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdSysfsRule:
    """
    One parsed /sys attribute permission declaration.
    """

    path: str
    attribute: str
    mode: str
    user: str
    group: str

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdSubsystemOption:
    """
    One ordered option belonging to a subsystem declaration.

    Parsing preserves lexical key/value material without interpreting
    runtime meaning.
    """

    name: str
    value: str

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdSubsystem:
    """
    One parsed subsystem declaration.

    Options retain source order and repetition.
    """

    name: str

    options: tuple[
        AndroidUeventdSubsystemOption,
        ...,
    ]

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdFirmwareDirectories:
    """
    One parsed firmware_directories declaration.

    Parsing preserves the ordered literal directory expressions exactly.
    Runtime firmware-search semantics belong to Android Device Universe.
    """

    directories: tuple[
        str,
        ...,
    ]

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdSocketRcvbufSize:
    """
    One parsed uevent_socket_rcvbuf_size declaration.

    Parsing preserves the literal size expression exactly.
    Runtime interpretation belongs to Android Device Universe.
    """

    size: str

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUeventdUnparsedLine:
    """
    Preserve one meaningful source line that Parsing could not classify.
    """

    raw: str
    source_path: Path
    source_line: int


AndroidUeventdDeclaration = (
    AndroidUeventdImport
    | AndroidUeventdDeviceRule
    | AndroidUeventdSysfsRule
    | AndroidUeventdSubsystem
    | AndroidUeventdFirmwareDirectories
    | AndroidUeventdSocketRcvbufSize
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidUeventdFile:
    """
    Immutable lexical representation of one ueventd source.

    ``declarations`` preserves cross-type source order.

    Unsupported or malformed meaningful input is retained separately as
    unparsed evidence rather than silently discarded.
    """

    source_path: Path
    raw: str

    declarations: tuple[
        AndroidUeventdDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidUeventdUnparsedLine,
        ...,
    ] = ()

    @property
    def imports(
        self,
    ) -> tuple[
        AndroidUeventdImport,
        ...,
    ]:
        return tuple(
            declaration
            for declaration in self.declarations
            if isinstance(
                declaration,
                AndroidUeventdImport,
            )
        )

    @property
    def device_rules(
        self,
    ) -> tuple[
        AndroidUeventdDeviceRule,
        ...,
    ]:
        return tuple(
            declaration
            for declaration in self.declarations
            if isinstance(
                declaration,
                AndroidUeventdDeviceRule,
            )
        )

    @property
    def sysfs_rules(
        self,
    ) -> tuple[
        AndroidUeventdSysfsRule,
        ...,
    ]:
        return tuple(
            declaration
            for declaration in self.declarations
            if isinstance(
                declaration,
                AndroidUeventdSysfsRule,
            )
        )

    @property
    def subsystems(
        self,
    ) -> tuple[
        AndroidUeventdSubsystem,
        ...,
    ]:
        return tuple(
            declaration
            for declaration in self.declarations
            if isinstance(
                declaration,
                AndroidUeventdSubsystem,
            )
        )

    @property
    def firmware_directories(
        self,
    ) -> tuple[
        AndroidUeventdFirmwareDirectories,
        ...,
    ]:
        return tuple(
            declaration
            for declaration in self.declarations
            if isinstance(
                declaration,
                AndroidUeventdFirmwareDirectories,
            )
        )

    @property
    def socket_rcvbuf_sizes(
        self,
    ) -> tuple[
        AndroidUeventdSocketRcvbufSize,
        ...,
    ]:
        return tuple(
            declaration
            for declaration in self.declarations
            if isinstance(
                declaration,
                AndroidUeventdSocketRcvbufSize,
            )
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not (
            self.declarations
            or self.unparsed_lines
        )