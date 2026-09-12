from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AndroidSelinuxSourceKind(
    StrEnum,
):
    FILE_CONTEXTS = "file_contexts"
    PROPERTY_CONTEXTS = "property_contexts"
    SERVICE_CONTEXTS = "service_contexts"
    HWSERVICE_CONTEXTS = "hwservice_contexts"
    VNDSERVICE_CONTEXTS = "vndservice_contexts"
    SEAPP_CONTEXTS = "seapp_contexts"
    KEYSTORE2_KEY_CONTEXTS = "keystore2_key_contexts"

    MAC_PERMISSIONS = "mac_permissions"

    CIL = "cil"

    POLICY_VERSION = "policy_version"
    POLICY_HASH = "policy_hash"

    GENFS_LABELS_VERSION = "genfs_labels_version"

    COMPILED_POLICY = "compiled_policy"

    OTHER_TEXT = "other_text"
    OPAQUE = "opaque"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxContextDeclaration:
    """
    One lexical SELinux context declaration.

    Parsing deliberately does not interpret selector matching, context
    semantics, property matching mode, value type, or file-type qualifiers.

    ``trailing_fields`` preserves every lexical field after the context.
    ``selector_fields`` preserves optional material between selector and
    context, such as a file_contexts file-type qualifier.
    """

    selector: str
    context: str

    selector_fields: tuple[
        str,
        ...,
    ] = ()

    trailing_fields: tuple[
        str,
        ...,
    ] = ()

    raw: str = ""

    source_path: Path = Path(".")
    source_line: int = 0


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxSeappField:
    name: str
    value: str


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxSeappDeclaration:
    """
    One ordered seapp_contexts declaration.

    Field ordering is preserved exactly. Parsing does not assign Android
    runtime meaning to individual keys.
    """

    fields: tuple[
        AndroidSelinuxSeappField,
        ...,
    ]

    raw: str
    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxMacPermissionsAttribute:
    """
    One ordered attribute on a mac_permissions XML element.
    """

    name: str
    value: str


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxMacPermissionsElement:
    """
    One structured mac_permissions XML element.

    Exact source bytes remain attached to ParsedAndroidSelinuxFile.
    Parsing preserves XML hierarchy and literal values without assigning
    cross-source Android policy semantics.
    """

    name: str

    attributes: tuple[
        AndroidSelinuxMacPermissionsAttribute,
        ...,
    ] = ()

    children: tuple[
        "AndroidSelinuxMacPermissionsElement",
        ...,
    ] = ()

    text: str = ""

    source_path: Path = Path(".")
    source_line: int = 0

    def attribute(
        self,
        name: str,
    ) -> str | None:
        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        values = tuple(
            attribute.value
            for attribute in self.attributes
            if attribute.name == name
        )

        if not values:
            return None

        if len(values) != 1:
            raise ValueError(
                "XML element contains duplicate attribute "
                f"{name!r}"
            )

        return values[0]

    def descendants(
        self,
    ) -> tuple[
        "AndroidSelinuxMacPermissionsElement",
        ...,
    ]:
        values = [self]

        for child in self.children:
            values.extend(
                child.descendants()
            )

        return tuple(values)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxTextLine:
    """
    One meaningful textual source line that does not belong to a richer
    intrinsic SELinux grammar handled by Parsing.
    """

    value: str
    raw: str

    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxUnparsedLine:
    raw: str
    source_path: Path
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxCilAtom:
    value: str
    quoted: bool
    source_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxCilList:
    items: tuple[
        "AndroidSelinuxCilExpression",
        ...,
    ]

    source_line: int
    end_line: int


type AndroidSelinuxCilExpression = (
    AndroidSelinuxCilAtom
    | AndroidSelinuxCilList
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSelinuxCilForm:
    """
    One complete top-level CIL S-expression.

    The generic tree is intentionally lexical. Universe owns semantic
    interpretation of forms such as allow, neverallow, typeattributeset,
    genfscon, typetransition, and all other policy constructs.
    """

    name: str
    expression: AndroidSelinuxCilList

    source_line: int
    end_line: int


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidSelinuxFile:
    """
    Complete immutable Parsing result for one SELinux source.

    The exact source bytes are always retained.

    Textual files additionally retain decoded text and intrinsic lexical
    structures. Unsupported material is never silently discarded.
    """

    source_path: Path
    kind: AndroidSelinuxSourceKind

    raw_bytes: bytes

    raw: str | None = None

    context_declarations: tuple[
        AndroidSelinuxContextDeclaration,
        ...,
    ] = ()

    seapp_declarations: tuple[
        AndroidSelinuxSeappDeclaration,
        ...,
    ] = ()

    mac_permissions_root: (
        AndroidSelinuxMacPermissionsElement
        | None
    ) = None

    cil_forms: tuple[
        AndroidSelinuxCilForm,
        ...,
    ] = ()

    text_lines: tuple[
        AndroidSelinuxTextLine,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidSelinuxUnparsedLine,
        ...,
    ] = ()

    @property
    def genfs_labels_version(
        self,
    ) -> str | None:
        """
        Return the intrinsic genfs labels version scalar.

        Parsing owns only literal decoding and validation of the source.
        Cross-source reconciliation and applicability belong to Universe.
        """

        if (
            self.kind
            is not AndroidSelinuxSourceKind.GENFS_LABELS_VERSION
        ):
            return None

        if self.raw is None:
            raise ValueError(
                "genfs labels version source must contain text"
            )

        value = self.raw.strip()

        if not value:
            raise ValueError(
                "genfs labels version source must not be empty"
            )

        if not value.isdigit():
            raise ValueError(
                "genfs labels version source must contain only digits"
            )

        if len(self.text_lines) != 1:
            raise ValueError(
                "genfs labels version source must contain "
                "exactly one meaningful line"
            )

        if self.text_lines[0].value != value:
            raise ValueError(
                "genfs labels version text observation "
                "does not match decoded scalar"
            )

        return value


    @property
    def declaration_count(
        self,
    ) -> int:
        mac_permissions_count = (
            len(
                self.mac_permissions_root
                .descendants()
            )
            if self.mac_permissions_root
            is not None
            else 0
        )

        return (
            len(self.context_declarations)
            + len(self.seapp_declarations)
            + mac_permissions_count
            + len(self.cil_forms)
            + len(self.text_lines)
        )

    @property
    def is_opaque(
        self,
    ) -> bool:
        return (
            self.kind
            in {
                AndroidSelinuxSourceKind.COMPILED_POLICY,
                AndroidSelinuxSourceKind.OPAQUE,
            }
        )