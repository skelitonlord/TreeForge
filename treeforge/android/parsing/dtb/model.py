from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedFdtHeader:
    """
    Literal standard FDT header fields, decoded from big-endian integers.
    """

    magic: int
    totalsize: int
    off_dt_struct: int
    off_dt_strings: int
    off_mem_rsvmap: int
    version: int
    last_comp_version: int
    boot_cpuid_phys: int
    size_dt_strings: int
    size_dt_struct: int


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedFdtReservation:
    """
    One literal entry from the FDT memory-reservation block.
    """

    address: int
    size: int


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedFdtProperty:
    """
    One literal FDT property.

    Raw bytes remain canonical. Parsing deliberately does not infer whether a
    value represents strings, cells, phandles, paths, flags, or device policy.
    """

    name: str
    value: bytes

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
                "name cannot be empty"
            )

        if not isinstance(
            self.value,
            bytes,
        ):
            raise TypeError(
                "value must be bytes"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedFdtNode:
    """
    One literal FDT node with deterministic source-order children/properties.
    """

    name: str

    properties: tuple[
        ParsedFdtProperty,
        ...,
    ] = ()

    children: tuple[
        ParsedFdtNode,
        ...,
    ] = ()

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

        if not isinstance(
            self.properties,
            tuple,
        ):
            raise TypeError(
                "properties must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ParsedFdtProperty,
            )
            for item in self.properties
        ):
            raise TypeError(
                "properties must contain ParsedFdtProperty entries"
            )

        if not isinstance(
            self.children,
            tuple,
        ):
            raise TypeError(
                "children must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ParsedFdtNode,
            )
            for item in self.children
        ):
            raise TypeError(
                "children must contain ParsedFdtNode entries"
            )

    @property
    def node_count(
        self,
    ) -> int:
        return (
            1
            + sum(
                child.node_count
                for child in self.children
            )
        )

    @property
    def property_count(
        self,
    ) -> int:
        return (
            len(
                self.properties
            )
            + sum(
                child.property_count
                for child in self.children
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedFdt:
    """
    Complete intrinsic FDT Parsing result for one canonical artifact.

    ``artifact`` is preserved by exact identity from Extraction.
    """

    artifact: ExtractedArtifact
    header: ParsedFdtHeader

    reservations: tuple[
        ParsedFdtReservation,
        ...,
    ]

    root: ParsedFdtNode

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.header,
            ParsedFdtHeader,
        ):
            raise TypeError(
                "header must be a ParsedFdtHeader"
            )

        if not isinstance(
            self.reservations,
            tuple,
        ):
            raise TypeError(
                "reservations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ParsedFdtReservation,
            )
            for item in self.reservations
        ):
            raise TypeError(
                "reservations must contain ParsedFdtReservation entries"
            )

        if not isinstance(
            self.root,
            ParsedFdtNode,
        ):
            raise TypeError(
                "root must be a ParsedFdtNode"
            )

    @property
    def reservation_count(
        self,
    ) -> int:
        return len(
            self.reservations
        )

    @property
    def node_count(
        self,
    ) -> int:
        return self.root.node_count

    @property
    def property_count(
        self,
    ) -> int:
        return self.root.property_count

    @property
    def top_level_child_count(
        self,
    ) -> int:
        return len(
            self.root.children
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedDtboExternalFixupLocation:
    """
    One literal location encoded by a property under ``/__fixups__``.

    ``node_path``, ``property_name``, and ``byte_offset`` are decoded directly
    from the compiled-overlay ``path:property:offset`` string. Parsing records
    the structure only; resolution against a base tree belongs to Universe.
    """

    node_path: str
    property_name: str
    byte_offset: int

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.node_path,
                str,
            )
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be an absolute path"
            )

        if (
            not isinstance(
                self.property_name,
                str,
            )
            or not self.property_name
        ):
            raise ValueError(
                "property_name must be a non-empty string"
            )

        if (
            isinstance(
                self.byte_offset,
                bool,
            )
            or not isinstance(
                self.byte_offset,
                int,
            )
        ):
            raise TypeError(
                "byte_offset must be an integer"
            )

        if self.byte_offset < 0:
            raise ValueError(
                "byte_offset cannot be negative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedDtboExternalFixup:
    """
    One literal external-symbol fixup from ``/__fixups__``.
    """

    source: ParsedFdtProperty
    symbol: str

    locations: tuple[
        ParsedDtboExternalFixupLocation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedFdtProperty,
        ):
            raise TypeError(
                "source must be a ParsedFdtProperty"
            )

        if (
            not isinstance(
                self.symbol,
                str,
            )
            or not self.symbol
        ):
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if self.source.name != self.symbol:
            raise ValueError(
                "external fixup symbol must preserve "
                "its exact source property name"
            )

        if not isinstance(
            self.locations,
            tuple,
        ):
            raise TypeError(
                "locations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ParsedDtboExternalFixupLocation,
            )
            for item in self.locations
        ):
            raise TypeError(
                "locations must contain only "
                "ParsedDtboExternalFixupLocation entries"
            )

        if not self.locations:
            raise ValueError(
                "external fixup must contain at least one location"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedDtboLocalFixup:
    """
    One literal property relocation encoded below ``/__local_fixups__``.

    The local-fixup tree mirrors the corresponding overlay path. Each stored
    integer is the byte offset of a local phandle cell within that property's
    original value.
    """

    source: ParsedFdtProperty
    node_path: str
    property_name: str

    byte_offsets: tuple[
        int,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedFdtProperty,
        ):
            raise TypeError(
                "source must be a ParsedFdtProperty"
            )

        if (
            not isinstance(
                self.node_path,
                str,
            )
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be an absolute path"
            )

        if (
            not isinstance(
                self.property_name,
                str,
            )
            or not self.property_name
        ):
            raise ValueError(
                "property_name must be a non-empty string"
            )

        if self.source.name != self.property_name:
            raise ValueError(
                "local fixup must preserve exact "
                "source property identity"
            )

        if not isinstance(
            self.byte_offsets,
            tuple,
        ):
            raise TypeError(
                "byte_offsets must be a tuple"
            )

        if not self.byte_offsets:
            raise ValueError(
                "local fixup must contain at least one byte offset"
            )

        if not all(
            isinstance(
                item,
                int,
            )
            and not isinstance(
                item,
                bool,
            )
            and item >= 0
            for item in self.byte_offsets
        ):
            raise ValueError(
                "local fixup byte offsets must be "
                "non-negative integers"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedDtboSymbol:
    """
    One literal symbol-to-path declaration from ``/__symbols__``.
    """

    source: ParsedFdtProperty
    symbol: str
    node_path: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedFdtProperty,
        ):
            raise TypeError(
                "source must be a ParsedFdtProperty"
            )

        if (
            not isinstance(
                self.symbol,
                str,
            )
            or not self.symbol
        ):
            raise ValueError(
                "symbol must be a non-empty string"
            )

        if self.source.name != self.symbol:
            raise ValueError(
                "symbol must preserve exact source property name"
            )

        if (
            not isinstance(
                self.node_path,
                str,
            )
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be an absolute path"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedDtboFragmentTarget:
    """
    Literal target declaration for one top-level overlay fragment.

    Exactly one of ``target_phandle`` or ``target_path`` is populated when a
    supported target declaration is present.
    """

    fragment: ParsedFdtNode
    fragment_path: str
    target_property: ParsedFdtProperty
    target_phandle: int | None = None
    target_path: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.fragment,
            ParsedFdtNode,
        ):
            raise TypeError(
                "fragment must be a ParsedFdtNode"
            )

        if (
            not isinstance(
                self.fragment_path,
                str,
            )
            or not self.fragment_path.startswith("/")
        ):
            raise ValueError(
                "fragment_path must be an absolute path"
            )

        if not isinstance(
            self.target_property,
            ParsedFdtProperty,
        ):
            raise TypeError(
                "target_property must be a ParsedFdtProperty"
            )

        populated = sum(
            value is not None
            for value in (
                self.target_phandle,
                self.target_path,
            )
        )

        if populated != 1:
            raise ValueError(
                "exactly one fragment target form must be populated"
            )

        if self.target_phandle is not None:
            if (
                isinstance(
                    self.target_phandle,
                    bool,
                )
                or not isinstance(
                    self.target_phandle,
                    int,
                )
            ):
                raise TypeError(
                    "target_phandle must be an integer or None"
                )

            if self.target_property.name != "target":
                raise ValueError(
                    "target_phandle must originate from target"
                )

        if self.target_path is not None:
            if (
                not isinstance(
                    self.target_path,
                    str,
                )
                or not self.target_path.startswith("/")
            ):
                raise ValueError(
                    "target_path must be an absolute path"
                )

            if self.target_property.name != "target-path":
                raise ValueError(
                    "target_path must originate from target-path"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedDtboOverlayMetadata:
    """
    Literal compiled-device-tree-overlay metadata from one parsed FDT.

    This model records overlay structure only. It does not resolve external
    symbols, apply relocations, identify hardware policy, or infer which board
    variant is active. Those responsibilities belong to Universe.
    """

    fdt: ParsedFdt

    external_fixups: tuple[
        ParsedDtboExternalFixup,
        ...,
    ] = ()

    local_fixups: tuple[
        ParsedDtboLocalFixup,
        ...,
    ] = ()

    symbols: tuple[
        ParsedDtboSymbol,
        ...,
    ] = ()

    fragment_targets: tuple[
        ParsedDtboFragmentTarget,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.fdt,
            ParsedFdt,
        ):
            raise TypeError(
                "fdt must be a ParsedFdt"
            )

        for (
            field_name,
            values,
            expected_type,
        ) in (
            (
                "external_fixups",
                self.external_fixups,
                ParsedDtboExternalFixup,
            ),
            (
                "local_fixups",
                self.local_fixups,
                ParsedDtboLocalFixup,
            ),
            (
                "symbols",
                self.symbols,
                ParsedDtboSymbol,
            ),
            (
                "fragment_targets",
                self.fragment_targets,
                ParsedDtboFragmentTarget,
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
                    item,
                    expected_type,
                )
                for item in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid entry"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedDtboEntry:
    """
    Bind one DTBO-derived canonical Extraction artifact to its parsed FDT.

    DTBO table/container evidence remains owned by Extraction and remains
    available through ``artifact.facts`` and ``artifact.parent``.
    """

    artifact: ExtractedArtifact
    fdt: ParsedFdt
    overlay: ParsedDtboOverlayMetadata

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.fdt,
            ParsedFdt,
        ):
            raise TypeError(
                "fdt must be a ParsedFdt"
            )

        if not isinstance(
            self.overlay,
            ParsedDtboOverlayMetadata,
        ):
            raise TypeError(
                "overlay must be a ParsedDtboOverlayMetadata"
            )

        if self.overlay.fdt is not self.fdt:
            raise ValueError(
                "parsed DTBO overlay metadata must preserve "
                "exact ParsedFdt identity"
            )

        if (
            self.fdt.artifact
            is not self.artifact
        ):
            raise ValueError(
                "parsed DTBO entry must preserve exact "
                "ExtractedArtifact identity"
            )
