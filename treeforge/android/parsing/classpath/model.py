from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


class AndroidClasspathKind(
    IntEnum
):
    """
    Literal classpaths.proto Classpath enum values.

    Unknown future numeric values remain preserved separately by
    ``AndroidClasspathJar.classpath_value`` rather than being rejected.
    """

    UNKNOWN = 0
    BOOTCLASSPATH = 1
    SYSTEMSERVERCLASSPATH = 2
    DEX2OATBOOTCLASSPATH = 3
    STANDALONE_SYSTEMSERVER_JARS = 4


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidClasspathProtobufUnknownField:
    """
    One protobuf wire field not interpreted by the currently supported
    classpaths.proto schema.
    """

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
                "field_number must be an integer"
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
                "wire_type must be an integer"
            )

        if self.wire_type not in {
            0,
            1,
            2,
            3,
            4,
            5,
        }:
            raise ValueError(
                "wire_type is invalid"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        if not self.raw:
            raise ValueError(
                "raw must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidClasspathJar:
    """
    One literal Jar message from classpaths.proto.

    Parsing preserves wire presence independently from scalar default values.
    It does not evaluate SDK applicability or merge classpath fragments.
    """

    path: str = ""
    path_present: bool = False

    classpath_value: int = 0
    classpath_present: bool = False

    min_sdk_version: str = ""
    min_sdk_version_present: bool = False

    max_sdk_version: str = ""
    max_sdk_version_present: bool = False

    unknown_fields: tuple[
        AndroidClasspathProtobufUnknownField,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "path",
            "min_sdk_version",
            "max_sdk_version",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                str,
            ):
                raise TypeError(
                    f"{name} must be a string"
                )

        for name in (
            "path_present",
            "classpath_present",
            "min_sdk_version_present",
            "max_sdk_version_present",
        ):
            if not isinstance(
                getattr(
                    self,
                    name,
                ),
                bool,
            ):
                raise TypeError(
                    f"{name} must be a boolean"
                )

        if not isinstance(
            self.classpath_value,
            int,
        ):
            raise TypeError(
                "classpath_value must be an integer"
            )

        if self.classpath_value < 0:
            raise ValueError(
                "classpath_value must not be negative"
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
                AndroidClasspathProtobufUnknownField,
            )
            for field in self.unknown_fields
        ):
            raise TypeError(
                "unknown_fields must contain only "
                "AndroidClasspathProtobufUnknownField entries"
            )

    @property
    def known_classpath(
        self,
    ) -> AndroidClasspathKind | None:
        """
        Return the schema-known enum member without rejecting future values.
        """

        try:
            return AndroidClasspathKind(
                self.classpath_value
            )
        except ValueError:
            return None


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidClasspathConfiguration:
    """
    Literal Parsing-stage representation of one classpaths.proto fragment.

    ``source`` is the exact canonical AndroidModelSource. ``raw`` preserves
    the complete protobuf bytes. ``jars`` preserves source message order.
    """

    source: AndroidModelSource
    raw: bytes

    jars: tuple[
        AndroidClasspathJar,
        ...,
    ] = ()

    unknown_fields: tuple[
        AndroidClasspathProtobufUnknownField,
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
            .CLASSPATH_CONFIGURATION
        ):
            raise ValueError(
                "source must be a classpath configuration source"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        if not isinstance(
            self.jars,
            tuple,
        ):
            raise TypeError(
                "jars must be a tuple"
            )

        if not all(
            isinstance(
                jar,
                AndroidClasspathJar,
            )
            for jar in self.jars
        ):
            raise TypeError(
                "jars must contain only AndroidClasspathJar entries"
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
                AndroidClasspathProtobufUnknownField,
            )
            for field in self.unknown_fields
        ):
            raise TypeError(
                "unknown_fields must contain only "
                "AndroidClasspathProtobufUnknownField entries"
            )

    @property
    def jar_count(
        self,
    ) -> int:
        return len(
            self.jars
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidClasspathParsingResult:
    """
    Canonical collection of independently parsed classpath fragments.

    Fragment ordering is canonical by AndroidModelSource identity. No merge
    or cross-fragment semantic reconciliation occurs in Parsing.
    """

    configurations: tuple[
        ParsedAndroidClasspathConfiguration,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedAndroidClasspathConfiguration,
            )
            for value in self.configurations
        ):
            raise TypeError(
                "configurations must contain only "
                "ParsedAndroidClasspathConfiguration entries"
            )

        canonical = tuple(
            sorted(
                self.configurations,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if self.configurations != canonical:
            raise ValueError(
                "configurations must be in canonical source order"
            )

        identities = tuple(
            value.source.identity_key
            for value in self.configurations
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "classpath configuration source identities "
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
                "classpath configurations must preserve unique "
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
    def jar_count(
        self,
    ) -> int:
        return sum(
            value.jar_count
            for value in self.configurations
        )

    @property
    def unknown_field_count(
        self,
    ) -> int:
        return sum(
            len(
                value.unknown_fields
            )
            + sum(
                len(
                    jar.unknown_fields
                )
                for jar in value.jars
            )
            for value in self.configurations
        )
