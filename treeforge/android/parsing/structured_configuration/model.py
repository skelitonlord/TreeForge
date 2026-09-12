from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)


@dataclass(frozen=True, slots=True)
class ParsedAndroidAvbPublicKey:
    """
    Literal standalone AVB RSA public-key material.

    This represents the serialized public-key format consumed by libavb /
    avbtool. Parsing records intrinsic key structure only; trust-chain,
    applicability, and signing interpretation remain downstream.
    """

    source: AndroidModelSource
    key_num_bits: int
    n0inv: int
    modulus: bytes
    rr: bytes

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.key_num_bits, int)
            or isinstance(self.key_num_bits, bool)
            or self.key_num_bits <= 0
            or self.key_num_bits % 8 != 0
        ):
            raise ValueError(
                "key_num_bits must be a positive "
                "byte-aligned integer"
            )

        if (
            not isinstance(self.n0inv, int)
            or isinstance(self.n0inv, bool)
            or not 0 <= self.n0inv <= 0xFFFFFFFF
        ):
            raise ValueError(
                "n0inv must be an unsigned 32-bit integer"
            )

        expected_size = (
            self.key_num_bits // 8
        )

        if (
            not isinstance(self.modulus, bytes)
            or len(self.modulus) != expected_size
        ):
            raise ValueError(
                "modulus size must match key_num_bits"
            )

        if (
            not isinstance(self.rr, bytes)
            or len(self.rr) != expected_size
        ):
            raise ValueError(
                "rr size must match key_num_bits"
            )


class AndroidStructuredScalarKind(StrEnum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    NULL = "null"


@dataclass(frozen=True, slots=True)
class AndroidStructuredScalar:
    """
    One literal scalar recovered from structured configuration.

    ``path`` is a deterministic dotted/indexed path into the source
    structure, for example ``Cgroups2.Path``.
    """

    path: str
    kind: AndroidStructuredScalarKind
    value: str | bool | int | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, str)
            or not self.path
        ):
            raise ValueError(
                "path must be a non-empty string"
            )

        if not isinstance(
            self.kind,
            AndroidStructuredScalarKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidStructuredScalarKind"
            )

        if (
            self.kind
            is AndroidStructuredScalarKind.STRING
        ):
            if not isinstance(self.value, str):
                raise TypeError(
                    "STRING value must be str"
                )

        elif (
            self.kind
            is AndroidStructuredScalarKind.BOOLEAN
        ):
            if not isinstance(self.value, bool):
                raise TypeError(
                    "BOOLEAN value must be bool"
                )

        elif (
            self.kind
            is AndroidStructuredScalarKind.INTEGER
        ):
            if (
                not isinstance(self.value, int)
                or isinstance(self.value, bool)
            ):
                raise TypeError(
                    "INTEGER value must be int"
                )

        elif self.value is not None:
            raise TypeError(
                "NULL value must be None"
            )


@dataclass(frozen=True, slots=True)
class ParsedAndroidCgroupConfiguration:
    """
    Literal Android cgroups JSON configuration.

    Parsing flattens scalar JSON leaves while preserving deterministic
    source paths. Cross-field runtime meaning remains downstream.
    """

    source: AndroidModelSource
    scalars: tuple[
        AndroidStructuredScalar,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.scalars, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidStructuredScalar,
                )
                for value in self.scalars
            )
        ):
            raise TypeError(
                "scalars must contain only "
                "AndroidStructuredScalar values"
            )

        paths = tuple(
            value.path
            for value in self.scalars
        )

        if paths != tuple(sorted(paths)):
            raise ValueError(
                "cgroup scalar paths must be "
                "deterministically ordered"
            )

        if len(paths) != len(set(paths)):
            raise ValueError(
                "cgroup scalar paths must be unique"
            )


@dataclass(frozen=True, slots=True)
class AndroidMke2fsConfigurationEntry:
    section: str
    scope: tuple[str, ...]
    key: str
    value: str
    source_line: int

    def __post_init__(self) -> None:
        for name, value in (
            ("section", self.section),
            ("key", self.key),
            ("value", self.value),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"{name} must be a string"
                )

        if (
            not isinstance(self.scope, tuple)
            or not all(
                isinstance(value, str)
                and value
                for value in self.scope
            )
        ):
            raise TypeError(
                "scope must be tuple[str, ...]"
            )

        if (
            not isinstance(self.source_line, int)
            or isinstance(self.source_line, bool)
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(frozen=True, slots=True)
class ParsedAndroidMke2fsConfiguration:
    """
    Literal mke2fs.conf-style declarations.

    Nested fs-type blocks are retained through ``scope`` rather than
    interpreted into filesystem realization decisions.
    """

    source: AndroidModelSource
    entries: tuple[
        AndroidMke2fsConfigurationEntry,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.entries, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidMke2fsConfigurationEntry,
                )
                for value in self.entries
            )
        ):
            raise TypeError(
                "entries must contain only "
                "AndroidMke2fsConfigurationEntry values"
            )

        source_lines = tuple(
            value.source_line
            for value in self.entries
        )

        if source_lines != tuple(
            sorted(source_lines)
        ):
            raise ValueError(
                "mke2fs entries must preserve source order"
            )


@dataclass(frozen=True, slots=True)
class AndroidRecoveryWipeEntry:
    path: str
    source_line: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.path, str)
            or not self.path
        ):
            raise ValueError(
                "path must be non-empty"
            )

        if (
            not isinstance(self.source_line, int)
            or isinstance(self.source_line, bool)
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(frozen=True, slots=True)
class ParsedAndroidRecoveryWipeConfiguration:
    """
    Ordered literal recovery wipe declarations.

    Parsing records the declared paths and ordering only. Whether a
    partition should actually be wiped is downstream interpretation.
    """

    source: AndroidModelSource
    entries: tuple[
        AndroidRecoveryWipeEntry,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.entries, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidRecoveryWipeEntry,
                )
                for value in self.entries
            )
        ):
            raise TypeError(
                "entries must contain only "
                "AndroidRecoveryWipeEntry values"
            )

        source_lines = tuple(
            value.source_line
            for value in self.entries
        )

        if source_lines != tuple(
            sorted(source_lines)
        ):
            raise ValueError(
                "recovery wipe entries must preserve "
                "source order"
            )


class AndroidBlueprintPropertyKind(StrEnum):
    STRING = "string"
    BOOLEAN = "boolean"
    STRING_LIST = "string_list"


AndroidBlueprintPropertyValue = (
    str
    | bool
    | tuple[str, ...]
)


@dataclass(frozen=True, slots=True)
class AndroidBlueprintProperty:
    """
    One literal Blueprint property.

    Expressions and evaluated build semantics are intentionally excluded.
    """

    name: str
    kind: AndroidBlueprintPropertyKind
    value: AndroidBlueprintPropertyValue
    source_line: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
        ):
            raise ValueError(
                "name must be non-empty"
            )

        if not isinstance(
            self.kind,
            AndroidBlueprintPropertyKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidBlueprintPropertyKind"
            )

        if (
            not isinstance(self.source_line, int)
            or isinstance(self.source_line, bool)
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be positive"
            )

        if (
            self.kind
            is AndroidBlueprintPropertyKind.STRING
        ):
            if not isinstance(self.value, str):
                raise TypeError(
                    "STRING value must be str"
                )

        elif (
            self.kind
            is AndroidBlueprintPropertyKind.BOOLEAN
        ):
            if not isinstance(self.value, bool):
                raise TypeError(
                    "BOOLEAN value must be bool"
                )

        elif (
            not isinstance(self.value, tuple)
            or not all(
                isinstance(value, str)
                for value in self.value
            )
        ):
            raise TypeError(
                "STRING_LIST value must be "
                "tuple[str, ...]"
            )


@dataclass(frozen=True, slots=True)
class AndroidBlueprintModule:
    module_type: str
    name: str | None
    source_line: int
    properties: tuple[
        AndroidBlueprintProperty,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.module_type, str)
            or not self.module_type
        ):
            raise ValueError(
                "module_type must be non-empty"
            )

        if (
            self.name is not None
            and (
                not isinstance(self.name, str)
                or not self.name
            )
        ):
            raise ValueError(
                "name must be non-empty or None"
            )

        if (
            not isinstance(self.source_line, int)
            or isinstance(self.source_line, bool)
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be positive"
            )

        if (
            not isinstance(self.properties, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidBlueprintProperty,
                )
                for value in self.properties
            )
        ):
            raise TypeError(
                "properties must contain only "
                "AndroidBlueprintProperty values"
            )

        expected = tuple(
            sorted(
                self.properties,
                key=lambda value: (
                    value.source_line,
                    value.name,
                ),
            )
        )

        if self.properties != expected:
            raise ValueError(
                "Blueprint properties must use "
                "deterministic source order"
            )


@dataclass(frozen=True, slots=True)
class ParsedAndroidBlueprint:
    """
    Literal Android.bp evidence from a factory-image filesystem.

    This parser never executes Soong and never decides ownership,
    provider selection, target applicability, or reconstruction.
    """

    source: AndroidModelSource
    modules: tuple[
        AndroidBlueprintModule,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.modules, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidBlueprintModule,
                )
                for value in self.modules
            )
        ):
            raise TypeError(
                "modules must contain only "
                "AndroidBlueprintModule values"
            )

        source_lines = tuple(
            value.source_line
            for value in self.modules
        )

        if source_lines != tuple(
            sorted(source_lines)
        ):
            raise ValueError(
                "Blueprint modules must preserve source order"
            )



@dataclass(frozen=True, slots=True)
class AndroidSensorHalEntry:
    """
    One literal Sensors Multi-HAL provider declaration.

    Parsing records declaration text and source order only. Provider
    applicability, ownership, and runtime selection remain downstream.
    """

    module: str
    source_line: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.module, str)
            or not self.module.strip()
        ):
            raise ValueError(
                "module must be a non-empty string"
            )

        if self.module != self.module.strip():
            raise ValueError(
                "module must be normalized"
            )

        if (
            not isinstance(self.source_line, int)
            or isinstance(self.source_line, bool)
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(frozen=True, slots=True)
class ParsedAndroidSensorHalConfiguration:
    """
    Literal sensors/hals.conf declarations.

    No attempt is made here to decide what capabilities a declared HAL
    provides.
    """

    source: AndroidModelSource
    entries: tuple[
        AndroidSensorHalEntry,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.entries, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidSensorHalEntry,
                )
                for value in self.entries
            )
        ):
            raise TypeError(
                "entries must contain only "
                "AndroidSensorHalEntry values"
            )

        source_lines = tuple(
            value.source_line
            for value in self.entries
        )

        if source_lines != tuple(
            sorted(source_lines)
        ):
            raise ValueError(
                "sensor HAL entries must preserve source order"
            )


class AndroidSensorRegistryRecordKind(StrEnum):
    NODE = "node"
    PROPERTY = "property"
    LITERAL = "literal"


@dataclass(frozen=True, slots=True)
class AndroidSensorRegistryRecord:
    """
    One meaningful literal line from a sensor registry source.

    Known node and key/value grammar is decoded without discarding the raw
    declaration. Unknown non-comment syntax is retained as LITERAL evidence.
    """

    kind: AndroidSensorRegistryRecordKind
    raw: str
    source_line: int

    node_operator: str | None = None
    node_path: str | None = None

    scope_path: str | None = None
    key: str | None = None
    value: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            AndroidSensorRegistryRecordKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidSensorRegistryRecordKind"
            )

        if (
            not isinstance(self.raw, str)
            or not self.raw
        ):
            raise ValueError(
                "raw must be non-empty"
            )

        if (
            not isinstance(self.source_line, int)
            or isinstance(self.source_line, bool)
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be positive"
            )

        if (
            self.scope_path is not None
            and (
                not isinstance(self.scope_path, str)
                or not self.scope_path
            )
        ):
            raise ValueError(
                "scope_path must be non-empty or None"
            )

        if self.kind is AndroidSensorRegistryRecordKind.NODE:
            if (
                not isinstance(self.node_operator, str)
                or not self.node_operator
            ):
                raise ValueError(
                    "NODE record requires node_operator"
                )

            if (
                not isinstance(self.node_path, str)
                or not self.node_path
            ):
                raise ValueError(
                    "NODE record requires node_path"
                )

            if (
                self.key is not None
                or self.value is not None
            ):
                raise ValueError(
                    "NODE record must not contain a property"
                )

        elif (
            self.kind
            is AndroidSensorRegistryRecordKind.PROPERTY
        ):
            if (
                not isinstance(self.key, str)
                or not self.key
            ):
                raise ValueError(
                    "PROPERTY record requires key"
                )

            if not isinstance(self.value, str):
                raise TypeError(
                    "PROPERTY record value must be str"
                )

            if (
                self.node_operator is not None
                or self.node_path is not None
            ):
                raise ValueError(
                    "PROPERTY record must not contain node fields"
                )

        else:
            if any(
                value is not None
                for value in (
                    self.node_operator,
                    self.node_path,
                    self.scope_path,
                    self.key,
                    self.value,
                )
            ):
                raise ValueError(
                    "LITERAL record must contain only raw evidence"
                )


@dataclass(frozen=True, slots=True)
class ParsedAndroidSensorRegistryConfiguration:
    """
    Literal sensor registry evidence.

    Records remain in source order. Parsing recognizes only intrinsic syntax;
    sensor identity, transport, transforms, and provider semantics remain
    downstream concerns.
    """

    source: AndroidModelSource
    records: tuple[
        AndroidSensorRegistryRecord,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            not isinstance(self.records, tuple)
            or not all(
                isinstance(
                    value,
                    AndroidSensorRegistryRecord,
                )
                for value in self.records
            )
        ):
            raise TypeError(
                "records must contain only "
                "AndroidSensorRegistryRecord values"
            )

        source_lines = tuple(
            value.source_line
            for value in self.records
        )

        if source_lines != tuple(
            sorted(source_lines)
        ):
            raise ValueError(
                "sensor registry records must preserve source order"
            )

        if len(source_lines) != len(set(source_lines)):
            raise ValueError(
                "sensor registry records must preserve "
                "one record per source line"
            )


@dataclass(frozen=True, slots=True)
class AndroidStructuredConfigurationParsingResult:
    avb_public_keys: tuple[
        ParsedAndroidAvbPublicKey,
        ...,
    ] = ()

    cgroup_configurations: tuple[
        ParsedAndroidCgroupConfiguration,
        ...,
    ] = ()

    mke2fs_configurations: tuple[
        ParsedAndroidMke2fsConfiguration,
        ...,
    ] = ()

    recovery_wipe_configurations: tuple[
        ParsedAndroidRecoveryWipeConfiguration,
        ...,
    ] = ()

    blueprints: tuple[
        ParsedAndroidBlueprint,
        ...,
    ] = ()

    sensor_hal_configurations: tuple[
        ParsedAndroidSensorHalConfiguration,
        ...,
    ] = ()

    sensor_registry_configurations: tuple[
        ParsedAndroidSensorRegistryConfiguration,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        groups = (
            (
                self.avb_public_keys,
                ParsedAndroidAvbPublicKey,
                "avb_public_keys",
            ),
            (
                self.cgroup_configurations,
                ParsedAndroidCgroupConfiguration,
                "cgroup_configurations",
            ),
            (
                self.mke2fs_configurations,
                ParsedAndroidMke2fsConfiguration,
                "mke2fs_configurations",
            ),
            (
                self.recovery_wipe_configurations,
                ParsedAndroidRecoveryWipeConfiguration,
                "recovery_wipe_configurations",
            ),
            (
                self.blueprints,
                ParsedAndroidBlueprint,
                "blueprints",
            ),
            (
                self.sensor_hal_configurations,
                ParsedAndroidSensorHalConfiguration,
                "sensor_hal_configurations",
            ),
            (
                self.sensor_registry_configurations,
                ParsedAndroidSensorRegistryConfiguration,
                "sensor_registry_configurations",
            ),
        )

        for values, expected_type, name in groups:
            if (
                not isinstance(values, tuple)
                or not all(
                    isinstance(
                        value,
                        expected_type,
                    )
                    for value in values
                )
            ):
                raise TypeError(
                    f"{name} contains invalid values"
                )

            keys = tuple(
                (
                    value.source.source_name,
                    value.source.android_path.as_posix(),
                )
                for value in values
            )

            if keys != tuple(sorted(keys)):
                raise ValueError(
                    f"{name} must use canonical source order"
                )

            if len(keys) != len(set(keys)):
                raise ValueError(
                    f"{name} must preserve unique sources"
                )
