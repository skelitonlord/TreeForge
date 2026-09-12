from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidNativeLibraryConfigurationDeclaration:
    """
    One literal meaningful line from an Android native-library
    configuration source.

    Parsing preserves the lexical content and whitespace-tokenized fields.
    It does not interpret whether the declaration represents a public,
    LLNDK, sanitizer, vendor-public, architecture-specific, or other
    runtime-library policy. That semantic interpretation belongs to
    Android Device Universe.
    """

    raw: str
    content: str
    tokens: tuple[
        str,
        ...,
    ]
    source_line: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.content,
            str,
        ):
            raise TypeError(
                "content must be a string"
            )

        if not self.content:
            raise ValueError(
                "content must not be empty"
            )

        if not isinstance(
            self.tokens,
            tuple,
        ):
            raise TypeError(
                "tokens must be a tuple"
            )

        if not self.tokens:
            raise ValueError(
                "tokens must not be empty"
            )

        if not all(
            isinstance(
                token,
                str,
            )
            and token
            for token in self.tokens
        ):
            raise ValueError(
                "tokens must contain only non-empty strings"
            )

        if self.tokens != tuple(
            self.content.split()
        ):
            raise ValueError(
                "tokens must exactly preserve whitespace tokenization "
                "of content"
            )

        if not isinstance(
            self.source_line,
            int,
        ):
            raise TypeError(
                "source_line must be an integer"
            )

        if self.source_line < 1:
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidNativeLibraryConfiguration:
    """
    Literal Parsing-stage representation of one Android native-library
    configuration file.

    ``source`` preserves the canonical AndroidModelSource identity,
    including filesystem/Extraction provenance and Android-visible path.

    ``raw`` preserves the complete decoded source text. ``declarations``
    contains meaningful non-comment lines in original source order.

    Runtime linker-policy interpretation belongs to Android Device Universe.
    """

    source: AndroidModelSource
    raw: str

    declarations: tuple[
        AndroidNativeLibraryConfigurationDeclaration,
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
            .NATIVE_LIBRARY_CONFIGURATION
        ):
            raise ValueError(
                "source must be a native-library configuration source"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not all(
            isinstance(
                declaration,
                AndroidNativeLibraryConfigurationDeclaration,
            )
            for declaration in self.declarations
        ):
            raise TypeError(
                "declarations must contain only "
                "AndroidNativeLibraryConfigurationDeclaration entries"
            )

        source_lines = tuple(
            declaration.source_line
            for declaration in self.declarations
        )

        if source_lines != tuple(
            sorted(
                source_lines
            )
        ):
            raise ValueError(
                "declarations must preserve source order"
            )

        if len(
            source_lines
        ) != len(
            set(
                source_lines
            )
        ):
            raise ValueError(
                "declaration source lines must be unique"
            )

    @property
    def declaration_count(
        self,
    ) -> int:
        return len(
            self.declarations
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerConfigurationSection:
    """
    One literal section header from ld.config.txt.
    """

    name: str
    raw: str
    source_line: int

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
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.source_line,
            int,
        ):
            raise TypeError(
                "source_line must be an integer"
            )

        if self.source_line < 1:
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerConfigurationAssignment:
    """
    One literal key/value assignment from ld.config.txt.

    ``operator`` preserves whether the source used ``=`` or ``+=``.
    No semantic interpretation is performed here.
    """

    key: str
    operator: str
    value: str
    raw: str
    source_line: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.key,
            str,
        ):
            raise TypeError(
                "key must be a string"
            )

        if not self.key:
            raise ValueError(
                "key must not be empty"
            )

        if self.operator not in {
            "=",
            "+=",
        }:
            raise ValueError(
                "operator must be '=' or '+='"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.source_line,
            int,
        ):
            raise TypeError(
                "source_line must be an integer"
            )

        if self.source_line < 1:
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerConfigurationUnparsedLine:
    """
    One meaningful ld.config.txt line not recognized by the lexical parser.
    """

    raw: str
    content: str
    source_line: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.content,
            str,
        ):
            raise TypeError(
                "content must be a string"
            )

        if not self.content:
            raise ValueError(
                "content must not be empty"
            )

        if not isinstance(
            self.source_line,
            int,
        ):
            raise TypeError(
                "source_line must be an integer"
            )

        if self.source_line < 1:
            raise ValueError(
                "source_line must be positive"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidLinkerConfiguration:
    """
    Literal Parsing-stage representation of one ld.config.txt source.

    Parsing preserves source identity, raw text, section headers,
    assignments and otherwise meaningful unparsed lines.

    Linker namespace/search/link semantics belong to Android Device
    Universe.
    """

    source: AndroidModelSource
    raw: str

    sections: tuple[
        AndroidLinkerConfigurationSection,
        ...,
    ] = ()

    assignments: tuple[
        AndroidLinkerConfigurationAssignment,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidLinkerConfigurationUnparsedLine,
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
            .LINKER_CONFIGURATION
        ):
            raise ValueError(
                "source must be a linker configuration source"
            )

        if (
            self.source.android_path.name
            != "ld.config.txt"
        ):
            raise ValueError(
                "source must identify ld.config.txt"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.sections,
            tuple,
        ):
            raise TypeError(
                "sections must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerConfigurationSection,
            )
            for value in self.sections
        ):
            raise TypeError(
                "sections must contain only "
                "AndroidLinkerConfigurationSection entries"
            )

        if not isinstance(
            self.assignments,
            tuple,
        ):
            raise TypeError(
                "assignments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerConfigurationAssignment,
            )
            for value in self.assignments
        ):
            raise TypeError(
                "assignments must contain only "
                "AndroidLinkerConfigurationAssignment entries"
            )

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerConfigurationUnparsedLine,
            )
            for value in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidLinkerConfigurationUnparsedLine entries"
            )

        line_numbers = tuple(
            value.source_line
            for collection in (
                self.sections,
                self.assignments,
                self.unparsed_lines,
            )
            for value in collection
        )

        if len(
            line_numbers
        ) != len(
            set(
                line_numbers
            )
        ):
            raise ValueError(
                "parsed linker configuration line identities "
                "must be unique"
            )

    @property
    def section_count(
        self,
    ) -> int:
        return len(
            self.sections
        )

    @property
    def assignment_count(
        self,
    ) -> int:
        return len(
            self.assignments
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerProtobufUnknownField:
    """
    Exact unsupported protobuf field preserved from linker.config.pb.

    ``raw`` contains the complete encoded field, including its key.
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

        if self.wire_type not in {
            0,
            1,
            2,
            3,
            5,
        }:
            raise ValueError(
                "wire_type must be a supported protobuf wire type"
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
class AndroidLinkerProtobufContribution:
    """
    Literal LinkerConfig.Contribution payload.

    No namespace/search-path semantics are interpreted in Parsing.
    """

    namespace: str
    paths: tuple[
        str,
        ...,
    ] = ()

    unknown_fields: tuple[
        AndroidLinkerProtobufUnknownField,
        ...,
    ] = ()

    raw: bytes = b""

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.namespace,
            str,
        ):
            raise TypeError(
                "namespace must be a string"
            )

        if not isinstance(
            self.paths,
            tuple,
        ):
            raise TypeError(
                "paths must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.paths
        ):
            raise TypeError(
                "paths must contain only strings"
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
                value,
                AndroidLinkerProtobufUnknownField,
            )
            for value in self.unknown_fields
        ):
            raise TypeError(
                "unknown_fields must contain only "
                "AndroidLinkerProtobufUnknownField entries"
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
class ParsedAndroidLinkerProtobufConfiguration:
    """
    Literal Parsing-stage representation of linker.config.pb.

    Field meanings are defined by Android's generic LinkerConfig protobuf
    contract. Parsing decodes the wire format only; linker behavior belongs
    to Android Device Universe.

    Unknown protobuf fields are retained exactly for forward compatibility.
    """

    source: AndroidModelSource
    raw: bytes

    permitted_paths: tuple[
        str,
        ...,
    ] = ()

    visible: bool = False
    visible_present: bool = False

    provide_libs: tuple[
        str,
        ...,
    ] = ()

    require_libs: tuple[
        str,
        ...,
    ] = ()

    contributions: tuple[
        AndroidLinkerProtobufContribution,
        ...,
    ] = ()

    unknown_fields: tuple[
        AndroidLinkerProtobufUnknownField,
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
            .LINKER_CONFIGURATION
        ):
            raise ValueError(
                "source must be a linker configuration source"
            )

        if (
            self.source.android_path.name
            != "linker.config.pb"
        ):
            raise ValueError(
                "source must identify linker.config.pb"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        for name, values in (
            (
                "permitted_paths",
                self.permitted_paths,
            ),
            (
                "provide_libs",
                self.provide_libs,
            ),
            (
                "require_libs",
                self.require_libs,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    str,
                )
                for value in values
            ):
                raise TypeError(
                    f"{name} must contain only strings"
                )

        if not isinstance(
            self.visible,
            bool,
        ):
            raise TypeError(
                "visible must be a bool"
            )

        if not isinstance(
            self.visible_present,
            bool,
        ):
            raise TypeError(
                "visible_present must be a bool"
            )

        if not isinstance(
            self.contributions,
            tuple,
        ):
            raise TypeError(
                "contributions must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerProtobufContribution,
            )
            for value in self.contributions
        ):
            raise TypeError(
                "contributions must contain only "
                "AndroidLinkerProtobufContribution entries"
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
                value,
                AndroidLinkerProtobufUnknownField,
            )
            for value in self.unknown_fields
        ):
            raise TypeError(
                "unknown_fields must contain only "
                "AndroidLinkerProtobufUnknownField entries"
            )
