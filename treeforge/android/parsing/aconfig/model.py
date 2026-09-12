from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


class AndroidAconfigFlagState(
    IntEnum,
):
    ENABLED = 1
    DISABLED = 2


class AndroidAconfigFlagPermission(
    IntEnum,
):
    READ_ONLY = 1
    READ_WRITE = 2


class AndroidAconfigFlagPurpose(
    IntEnum,
):
    PURPOSE_UNSPECIFIED = 0
    PURPOSE_FEATURE = 1
    PURPOSE_BUGFIX = 2


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAconfigProtobufUnknownField:
    field_number: int
    wire_type: int
    raw: bytes

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.field_number,
            int,
        ):
            raise TypeError(
                "field_number must be an int"
            )

        if self.field_number < 1:
            raise ValueError(
                "field_number must be positive"
            )

        if not isinstance(
            self.wire_type,
            int,
        ):
            raise TypeError(
                "wire_type must be an int"
            )

        if self.wire_type < 0:
            raise ValueError(
                "wire_type cannot be negative"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAconfigFlagMetadata:
    purpose_value: int = 0
    purpose_present: bool = False

    unknown_fields: tuple[
        AndroidAconfigProtobufUnknownField,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.purpose_value,
            int,
        ):
            raise TypeError(
                "purpose_value must be an int"
            )

        if self.purpose_value < 0:
            raise ValueError(
                "purpose_value cannot be negative"
            )

        if not isinstance(
            self.purpose_present,
            bool,
        ):
            raise TypeError(
                "purpose_present must be a bool"
            )

        if not isinstance(
            self.unknown_fields,
            tuple,
        ):
            raise TypeError(
                "unknown_fields must be a tuple"
            )

        if not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in self.unknown_fields
        ):
            raise TypeError(
                "metadata unknown_fields contain invalid entries"
            )

    @property
    def known_purpose(
        self,
    ) -> AndroidAconfigFlagPurpose | None:
        try:
            return AndroidAconfigFlagPurpose(
                self.purpose_value
            )
        except ValueError:
            return None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAconfigTracepoint:
    source: str = ""
    source_present: bool = False

    state_value: int = 0
    state_present: bool = False

    permission_value: int = 0
    permission_present: bool = False

    unknown_fields: tuple[
        AndroidAconfigProtobufUnknownField,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "source",
                self.source,
            ),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{name} must be a string"
                )

        for name, value in (
            (
                "source_present",
                self.source_present,
            ),
            (
                "state_present",
                self.state_present,
            ),
            (
                "permission_present",
                self.permission_present,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{name} must be a bool"
                )

        for name, value in (
            (
                "state_value",
                self.state_value,
            ),
            (
                "permission_value",
                self.permission_value,
            ),
        ):
            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if not isinstance(
            self.unknown_fields,
            tuple,
        ):
            raise TypeError(
                "unknown_fields must be a tuple"
            )

        if not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in self.unknown_fields
        ):
            raise TypeError(
                "tracepoint unknown_fields contain invalid entries"
            )

    @property
    def known_state(
        self,
    ) -> AndroidAconfigFlagState | None:
        try:
            return AndroidAconfigFlagState(
                self.state_value
            )
        except ValueError:
            return None

    @property
    def known_permission(
        self,
    ) -> AndroidAconfigFlagPermission | None:
        try:
            return AndroidAconfigFlagPermission(
                self.permission_value
            )
        except ValueError:
            return None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAconfigParsedFlag:
    package: str = ""
    package_present: bool = False

    name: str = ""
    name_present: bool = False

    namespace: str = ""
    namespace_present: bool = False

    description: str = ""
    description_present: bool = False

    bugs: tuple[
        str,
        ...,
    ] = ()

    state_value: int = 0
    state_present: bool = False

    permission_value: int = 0
    permission_present: bool = False

    tracepoints: tuple[
        AndroidAconfigTracepoint,
        ...,
    ] = ()

    is_fixed_read_only: bool = False
    is_fixed_read_only_present: bool = False

    is_exported: bool = False
    is_exported_present: bool = False

    container: str = ""
    container_present: bool = False

    metadata: AndroidAconfigFlagMetadata | None = None
    metadata_present: bool = False

    unknown_fields: tuple[
        AndroidAconfigProtobufUnknownField,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("package", self.package),
            ("name", self.name),
            ("namespace", self.namespace),
            ("description", self.description),
            ("container", self.container),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{name} must be a string"
                )

        for name, value in (
            ("package_present", self.package_present),
            ("name_present", self.name_present),
            ("namespace_present", self.namespace_present),
            ("description_present", self.description_present),
            ("state_present", self.state_present),
            ("permission_present", self.permission_present),
            (
                "is_fixed_read_only_present",
                self.is_fixed_read_only_present,
            ),
            (
                "is_exported_present",
                self.is_exported_present,
            ),
            ("container_present", self.container_present),
            ("metadata_present", self.metadata_present),
            (
                "is_fixed_read_only",
                self.is_fixed_read_only,
            ),
            ("is_exported", self.is_exported),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{name} must be a bool"
                )

        for name, value in (
            ("state_value", self.state_value),
            (
                "permission_value",
                self.permission_value,
            ),
        ):
            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if not isinstance(
            self.bugs,
            tuple,
        ) or not all(
            isinstance(
                bug,
                str,
            )
            for bug
            in self.bugs
        ):
            raise TypeError(
                "bugs must be a tuple of strings"
            )

        if not isinstance(
            self.tracepoints,
            tuple,
        ) or not all(
            isinstance(
                tracepoint,
                AndroidAconfigTracepoint,
            )
            for tracepoint
            in self.tracepoints
        ):
            raise TypeError(
                "tracepoints must contain AndroidAconfigTracepoint"
            )

        if (
            self.metadata is not None
            and not isinstance(
                self.metadata,
                AndroidAconfigFlagMetadata,
            )
        ):
            raise TypeError(
                "metadata must be AndroidAconfigFlagMetadata or None"
            )

        if (
            self.metadata_present
            and self.metadata is None
        ):
            raise ValueError(
                "metadata_present requires metadata"
            )

        if (
            not self.metadata_present
            and self.metadata is not None
        ):
            raise ValueError(
                "metadata requires metadata_present"
            )

        if not isinstance(
            self.unknown_fields,
            tuple,
        ) or not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in self.unknown_fields
        ):
            raise TypeError(
                "unknown_fields contain invalid entries"
            )

    @property
    def known_state(
        self,
    ) -> AndroidAconfigFlagState | None:
        try:
            return AndroidAconfigFlagState(
                self.state_value
            )
        except ValueError:
            return None

    @property
    def known_permission(
        self,
    ) -> AndroidAconfigFlagPermission | None:
        try:
            return AndroidAconfigFlagPermission(
                self.permission_value
            )
        except ValueError:
            return None


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidAconfigConfiguration:
    source: AndroidModelSource
    raw: bytes

    flags: tuple[
        AndroidAconfigParsedFlag,
        ...,
    ] = ()

    unknown_fields: tuple[
        AndroidAconfigProtobufUnknownField,
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
            is not AndroidModelSourceKind
            .ACONFIG_CONFIGURATION
        ):
            raise ValueError(
                "source must be an aconfig configuration source"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        if not isinstance(
            self.flags,
            tuple,
        ) or not all(
            isinstance(
                flag,
                AndroidAconfigParsedFlag,
            )
            for flag
            in self.flags
        ):
            raise TypeError(
                "flags must contain AndroidAconfigParsedFlag"
            )

        if not isinstance(
            self.unknown_fields,
            tuple,
        ) or not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in self.unknown_fields
        ):
            raise TypeError(
                "unknown_fields contain invalid entries"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAconfigParsingResult:
    configurations: tuple[
        ParsedAndroidAconfigConfiguration,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.configurations,
            tuple,
        ) or not all(
            isinstance(
                configuration,
                ParsedAndroidAconfigConfiguration,
            )
            for configuration
            in self.configurations
        ):
            raise TypeError(
                "configurations must contain "
                "ParsedAndroidAconfigConfiguration"
            )

        canonical = tuple(
            sorted(
                self.configurations,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if (
            self.configurations
            != canonical
        ):
            raise ValueError(
                "aconfig configurations must use canonical "
                "source order"
            )

        identities = tuple(
            value.source.identity_key
            for value
            in self.configurations
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "aconfig configuration source identities "
                "must be unique"
            )

        source_object_ids = tuple(
            id(
                value.source
            )
            for value
            in self.configurations
        )

        if len(
            source_object_ids
        ) != len(
            set(
                source_object_ids
            )
        ):
            raise ValueError(
                "aconfig configurations must preserve unique "
                "canonical AndroidModelSource object identities"
            )

    @property
    def source_count(
        self,
    ) -> int:
        return len(
            self.configurations
        )

    @property
    def flag_count(
        self,
    ) -> int:
        return sum(
            len(
                configuration.flags
            )
            for configuration
            in self.configurations
        )

    @property
    def tracepoint_count(
        self,
    ) -> int:
        return sum(
            len(
                flag.tracepoints
            )
            for configuration
            in self.configurations
            for flag
            in configuration.flags
        )

    @property
    def unknown_field_count(
        self,
    ) -> int:
        total = 0

        for configuration in self.configurations:
            total += len(
                configuration.unknown_fields
            )

            for flag in configuration.flags:
                total += len(
                    flag.unknown_fields
                )

                for tracepoint in flag.tracepoints:
                    total += len(
                        tracepoint.unknown_fields
                    )

                if flag.metadata is not None:
                    total += len(
                        flag.metadata.unknown_fields
                    )

        return total
