from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.dex.model import (
    AndroidDexSourceKind,
    ParsedAndroidDex,
)
from treeforge.android.parsing.elf.model import (
    ParsedAndroidElf,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


class AndroidArtRuntimeFormat(
    StrEnum
):
    OAT = "oat"
    VDEX = "vdex"
    ART_IMAGE = "art_image"


class AndroidOatDexStorageDisposition(
    StrEnum
):
    """
    Structural offset disposition encoded by OatDexFile::dex_file_offset.

    A nonzero value identifies an offset into ART's DEX backing region.
    Parsing preserves that literal fact without assigning the backing region
    to a particular OAT/VDEX source. Physical-source reconciliation remains
    later semantic work.
    """

    EXTERNAL_DEX = "external_dex"
    DEX_REGION_OFFSET = "dex_region_offset"


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidOatKeyValue:
    index: int
    key_offset: int
    value_offset: int
    key: str
    value: str

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("index", self.index),
            ("key_offset", self.key_offset),
            ("value_offset", self.value_offset),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not self.key:
            raise ValueError(
                "OAT key must not be empty"
            )


class AndroidDexLayoutSectionKind(
    StrEnum
):
    CODE = "code"
    STRINGS = "strings"


class AndroidDexLayoutType(
    StrEnum
):
    HOT = "hot"
    SOMETIMES_USED = "sometimes_used"
    STARTUP_ONLY = "startup_only"
    USED_ONCE = "used_once"
    UNUSED = "unused"


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidDexLayoutSubsection:
    """
    One exact DexLayoutSection::Subsection.

    The encoded values are DEX-relative byte bounds [start_offset, end_offset).
    Parsing preserves them structurally and does not resolve them against a
    particular external DEX container.
    """

    index: int
    kind: AndroidDexLayoutType
    start_offset: int
    end_offset: int

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "DEX layout subsection index must be a "
                "non-negative integer"
            )

        if not isinstance(
            self.kind,
            AndroidDexLayoutType,
        ):
            raise TypeError(
                "DEX layout subsection kind must be an "
                "AndroidDexLayoutType"
            )

        for name, value in (
            (
                "start_offset",
                self.start_offset,
            ),
            (
                "end_offset",
                self.end_offset,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if self.end_offset < self.start_offset:
            raise ValueError(
                "DEX layout subsection end_offset must not precede "
                "start_offset"
            )

    @property
    def size(
        self,
    ) -> int:
        return (
            self.end_offset
            - self.start_offset
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidDexLayoutSection:
    """
    One exact DexLayoutSection in canonical serialized layout order.
    """

    index: int
    kind: AndroidDexLayoutSectionKind
    subsections: tuple[
        ParsedAndroidDexLayoutSubsection,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "DEX layout section index must be a non-negative integer"
            )

        if not isinstance(
            self.kind,
            AndroidDexLayoutSectionKind,
        ):
            raise TypeError(
                "DEX layout section kind must be an "
                "AndroidDexLayoutSectionKind"
            )

        expected_kinds = tuple(
            AndroidDexLayoutType
        )

        actual_kinds = tuple(
            subsection.kind
            for subsection
            in self.subsections
        )

        if (
            len(
                self.subsections
            )
            != len(
                expected_kinds
            )
            or actual_kinds
            != expected_kinds
        ):
            raise ValueError(
                "DEX layout subsections must preserve the complete "
                "canonical layout-type order"
            )

        expected_indices = tuple(
            range(
                len(
                    expected_kinds
                )
            )
        )

        actual_indices = tuple(
            subsection.index
            for subsection
            in self.subsections
        )

        if actual_indices != expected_indices:
            raise ValueError(
                "DEX layout subsection indices must preserve "
                "canonical serialized order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidDexLayoutSections:
    """
    Complete exact DexLayoutSections object referenced by one OatDexFile.

    `offset` is preserved relative to the beginning of the OAT data, exactly
    matching the serialized OatDexFile pointer.
    """

    offset: int
    size: int
    sections: tuple[
        ParsedAndroidDexLayoutSection,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "offset",
                self.offset,
            ),
            (
                "size",
                self.size,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if self.offset == 0:
            raise ValueError(
                "decoded DexLayoutSections must have a nonzero offset"
            )

        if self.size == 0:
            raise ValueError(
                "decoded DexLayoutSections must have a positive size"
            )

        expected_kinds = tuple(
            AndroidDexLayoutSectionKind
        )

        actual_kinds = tuple(
            section.kind
            for section
            in self.sections
        )

        if (
            len(
                self.sections
            )
            != len(
                expected_kinds
            )
            or actual_kinds
            != expected_kinds
        ):
            raise ValueError(
                "DexLayoutSections must preserve the complete canonical "
                "section order"
            )

        expected_indices = tuple(
            range(
                len(
                    expected_kinds
                )
            )
        )

        actual_indices = tuple(
            section.index
            for section
            in self.sections
        )

        if actual_indices != expected_indices:
            raise ValueError(
                "DEX layout section indices must preserve canonical "
                "serialized order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidIndexBssMappingEntry:
    """
    One exact ART IndexBssMappingEntry.

    ``index_and_mask`` is preserved exactly as serialized. Decoding the
    packed index/mask semantics requires the corresponding DEX index-space
    size and therefore remains separate from this purely structural object.
    """

    index: int
    index_and_mask: int
    bss_offset: int

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("index", self.index),
            ("index_and_mask", self.index_and_mask),
            ("bss_offset", self.bss_offset),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidIndexBssMapping:
    """
    Exact self-delimiting ART IndexBssMapping.

    ART serializes this as a LengthPrefixedArray<IndexBssMappingEntry>:
    one uint32 entry count followed by that many two-uint32 entries.
    The mapping offset is OAT-relative.
    """

    offset: int
    size: int
    entry_count: int
    entries: tuple[
        ParsedAndroidIndexBssMappingEntry,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("offset", self.offset),
            ("size", self.size),
            ("entry_count", self.entry_count),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if self.offset == 0:
            raise ValueError(
                "decoded IndexBssMapping must have a nonzero offset"
            )

        if self.entry_count == 0:
            raise ValueError(
                "decoded IndexBssMapping must contain at least one entry"
            )

        if len(
            self.entries
        ) != self.entry_count:
            raise ValueError(
                "IndexBssMapping entry count does not match entries"
            )

        if self.size != (
            4
            + self.entry_count * 8
        ):
            raise ValueError(
                "IndexBssMapping size does not match serialized structure"
            )

        expected_indices = tuple(
            range(
                self.entry_count
            )
        )

        actual_indices = tuple(
            entry.index
            for entry
            in self.entries
        )

        if actual_indices != expected_indices:
            raise ValueError(
                "IndexBssMapping entries must preserve serialized order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidBcpBssMappingInfo:
    """
    One exact boot-class-path BSS mapping-offset record.

    The record itself contains only OAT-relative offsets. Each nonzero
    offset is followed separately and represented by its exact decoded
    IndexBssMapping.
    """

    index: int

    method_bss_mapping_offset: int
    type_bss_mapping_offset: int
    public_type_bss_mapping_offset: int
    package_type_bss_mapping_offset: int
    string_bss_mapping_offset: int
    method_type_bss_mapping_offset: int | None

    method_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    type_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    public_type_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    package_type_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    string_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    method_type_bss_mapping: ParsedAndroidIndexBssMapping | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "BCP BSS mapping index must be non-negative"
            )

        pairs = (
            (
                self.method_bss_mapping_offset,
                self.method_bss_mapping,
            ),
            (
                self.type_bss_mapping_offset,
                self.type_bss_mapping,
            ),
            (
                self.public_type_bss_mapping_offset,
                self.public_type_bss_mapping,
            ),
            (
                self.package_type_bss_mapping_offset,
                self.package_type_bss_mapping,
            ),
            (
                self.string_bss_mapping_offset,
                self.string_bss_mapping,
            ),
        )

        for offset, mapping in pairs:
            if (
                isinstance(
                    offset,
                    bool,
                )
                or not isinstance(
                    offset,
                    int,
                )
                or offset < 0
            ):
                raise ValueError(
                    "BCP BSS mapping offsets must be non-negative"
                )

            if (
                offset == 0
            ) != (
                mapping is None
            ):
                raise ValueError(
                    "BCP decoded BSS mapping presence must exactly "
                    "match its serialized offset"
                )

            if (
                mapping is not None
                and mapping.offset != offset
            ):
                raise ValueError(
                    "BCP decoded BSS mapping offset mismatch"
                )

        if self.method_type_bss_mapping_offset is None:
            if self.method_type_bss_mapping is not None:
                raise ValueError(
                    "method-type BSS mapping must be absent when the "
                    "serialized OAT layout has no method-type field"
                )
        else:
            offset = self.method_type_bss_mapping_offset

            if (
                isinstance(
                    offset,
                    bool,
                )
                or not isinstance(
                    offset,
                    int,
                )
                or offset < 0
            ):
                raise ValueError(
                    "method-type BSS mapping offset must be non-negative"
                )

            if (
                offset == 0
            ) != (
                self.method_type_bss_mapping is None
            ):
                raise ValueError(
                    "BCP method-type BSS mapping presence must exactly "
                    "match its serialized offset"
                )

            if (
                self.method_type_bss_mapping is not None
                and self.method_type_bss_mapping.offset != offset
            ):
                raise ValueError(
                    "BCP method-type BSS mapping offset mismatch"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidBcpBssInfo:
    """
    Complete self-described boot-class-path BSS metadata referenced by the
    OAT header.
    """

    offset: int
    record_size: int
    dex_file_count: int
    records: tuple[
        ParsedAndroidBcpBssMappingInfo,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("offset", self.offset),
            ("record_size", self.record_size),
            ("dex_file_count", self.dex_file_count),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if self.offset == 0:
            raise ValueError(
                "decoded BCP BSS info must have a nonzero offset"
            )

        if self.record_size not in {
            20,
            24,
        }:
            raise ValueError(
                "BCP BSS record size must be 20 or 24 bytes"
            )

        if self.dex_file_count == 0:
            raise ValueError(
                "nonzero BCP BSS info must contain at least one record"
            )

        if len(
            self.records
        ) != self.dex_file_count:
            raise ValueError(
                "BCP BSS record count does not match dex_file_count"
            )

        actual_indices = tuple(
            record.index
            for record
            in self.records
        )

        if actual_indices != tuple(
            range(
                self.dex_file_count
            )
        ):
            raise ValueError(
                "BCP BSS records must preserve serialized order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidOatDexFile:
    """
    One exact serialized OatDexFile record.

    Offsets are preserved exactly as encoded. Parsing structurally decodes
    DexLayoutSections when present, but does not resolve their DEX-relative
    ranges against external DEX containers. Class tables, lookup tables, BSS
    mappings, external DEX containers, and runtime canonical locations remain
    separate later work.
    """

    index: int

    #
    # Offset of this record relative to the beginning of the OAT header.
    #
    record_offset: int
    record_size: int

    dex_file_location_size: int
    dex_file_location_bytes: bytes
    dex_file_location: str

    dex_file_magic: bytes | None
    dex_file_location_checksum: int
    dex_file_sha1: bytes | None

    dex_file_offset: int
    dex_storage_disposition: AndroidOatDexStorageDisposition
    class_offsets_offset: int
    lookup_table_offset: int
    dex_layout_sections_offset: int
    dex_layout_sections: ParsedAndroidDexLayoutSections | None

    method_bss_mapping_offset: int
    type_bss_mapping_offset: int
    public_type_bss_mapping_offset: int
    package_type_bss_mapping_offset: int
    string_bss_mapping_offset: int
    method_type_bss_mapping_offset: int | None

    method_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    type_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    public_type_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    package_type_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    string_bss_mapping: ParsedAndroidIndexBssMapping | None = None
    method_type_bss_mapping: ParsedAndroidIndexBssMapping | None = None

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "index",
                self.index,
            ),
            (
                "record_offset",
                self.record_offset,
            ),
            (
                "record_size",
                self.record_size,
            ),
            (
                "dex_file_location_size",
                self.dex_file_location_size,
            ),
            (
                "dex_file_location_checksum",
                self.dex_file_location_checksum,
            ),
            (
                "dex_file_offset",
                self.dex_file_offset,
            ),
            (
                "class_offsets_offset",
                self.class_offsets_offset,
            ),
            (
                "lookup_table_offset",
                self.lookup_table_offset,
            ),
            (
                "dex_layout_sections_offset",
                self.dex_layout_sections_offset,
            ),
            (
                "method_bss_mapping_offset",
                self.method_bss_mapping_offset,
            ),
            (
                "type_bss_mapping_offset",
                self.type_bss_mapping_offset,
            ),
            (
                "public_type_bss_mapping_offset",
                self.public_type_bss_mapping_offset,
            ),
            (
                "package_type_bss_mapping_offset",
                self.package_type_bss_mapping_offset,
            ),
            (
                "string_bss_mapping_offset",
                self.string_bss_mapping_offset,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.dex_storage_disposition,
            AndroidOatDexStorageDisposition,
        ):
            raise TypeError(
                "dex_storage_disposition must be an "
                "AndroidOatDexStorageDisposition"
            )

        expected_storage_disposition = (
            AndroidOatDexStorageDisposition.DEX_REGION_OFFSET
            if self.dex_file_offset != 0
            else AndroidOatDexStorageDisposition.EXTERNAL_DEX
        )

        if (
            self.dex_storage_disposition
            is not expected_storage_disposition
        ):
            raise ValueError(
                "dex_storage_disposition must exactly match "
                "dex_file_offset structural semantics"
            )

        if (
            self.dex_layout_sections_offset == 0
        ) != (
            self.dex_layout_sections is None
        ):
            raise ValueError(
                "dex_layout_sections must exist exactly when "
                "dex_layout_sections_offset is nonzero"
            )

        if (
            self.dex_layout_sections is not None
            and (
                self.dex_layout_sections.offset
                != self.dex_layout_sections_offset
            )
        ):
            raise ValueError(
                "decoded DexLayoutSections offset must exactly match "
                "the serialized OatDexFile pointer"
            )

        if self.record_size == 0:
            raise ValueError(
                "record_size must be positive"
            )

        if self.dex_file_location_size == 0:
            raise ValueError(
                "OatDexFile location must not be empty"
            )

        if (
            len(
                self.dex_file_location_bytes
            )
            != self.dex_file_location_size
        ):
            raise ValueError(
                "OatDexFile location byte length does not match "
                "dex_file_location_size"
            )

        if (
            self.dex_file_location_bytes.decode(
                "utf-8"
            )
            != self.dex_file_location
        ):
            raise ValueError(
                "OatDexFile decoded location does not match exact bytes"
            )

        if (
            self.dex_file_magic is not None
            and len(
                self.dex_file_magic
            ) != 8
        ):
            raise ValueError(
                "OatDexFile DEX magic must be exactly eight bytes "
                "when present"
            )

        if (
            self.dex_file_sha1 is not None
            and len(
                self.dex_file_sha1
            ) != 20
        ):
            raise ValueError(
                "OatDexFile SHA-1 must be exactly twenty bytes "
                "when present"
            )

        if (
            (self.dex_file_magic is None)
            != (self.dex_file_sha1 is None)
        ):
            raise ValueError(
                "OatDexFile DEX magic and SHA-1 must either both "
                "be present or both be absent"
            )


        if (
            self.method_type_bss_mapping_offset is not None
            and (
                isinstance(
                    self.method_type_bss_mapping_offset,
                    bool,
                )
                or not isinstance(
                    self.method_type_bss_mapping_offset,
                    int,
                )
                or self.method_type_bss_mapping_offset < 0
            )
        ):
            raise ValueError(
                "method_type_bss_mapping_offset must be a "
                "non-negative integer or None"
            )

        bss_pairs = (
            (
                self.method_bss_mapping_offset,
                self.method_bss_mapping,
            ),
            (
                self.type_bss_mapping_offset,
                self.type_bss_mapping,
            ),
            (
                self.public_type_bss_mapping_offset,
                self.public_type_bss_mapping,
            ),
            (
                self.package_type_bss_mapping_offset,
                self.package_type_bss_mapping,
            ),
            (
                self.string_bss_mapping_offset,
                self.string_bss_mapping,
            ),
        )

        for offset, mapping in bss_pairs:
            if (
                offset == 0
            ) != (
                mapping is None
            ):
                raise ValueError(
                    "decoded OatDexFile BSS mapping presence must "
                    "exactly match its serialized offset"
                )

            if (
                mapping is not None
                and mapping.offset != offset
            ):
                raise ValueError(
                    "decoded OatDexFile BSS mapping offset mismatch"
                )

        if self.method_type_bss_mapping_offset is None:
            if self.method_type_bss_mapping is not None:
                raise ValueError(
                    "method-type BSS mapping must be absent for an OAT "
                    "layout without the serialized field"
                )
        elif (
            self.method_type_bss_mapping_offset == 0
        ) != (
            self.method_type_bss_mapping is None
        ):
            raise ValueError(
                "decoded OatDexFile method-type BSS mapping presence "
                "must exactly match its serialized offset"
            )
        elif (
            self.method_type_bss_mapping is not None
            and self.method_type_bss_mapping.offset
            != self.method_type_bss_mapping_offset
        ):
            raise ValueError(
                "decoded OatDexFile method-type BSS mapping offset mismatch"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidOatStructuralHeader:
    checksum: int
    instruction_set: int
    instruction_set_features_bitmap: int
    dex_file_count: int
    oat_dex_files_offset: int
    bcp_bss_info_offset: int
    executable_offset: int
    jni_dlsym_lookup_trampoline_offset: int
    jni_dlsym_lookup_critical_trampoline_offset: int
    quick_generic_jni_trampoline_offset: int
    quick_imt_conflict_trampoline_offset: int
    quick_resolution_trampoline_offset: int
    quick_to_interpreter_bridge_offset: int
    nterp_trampoline_offset: int
    key_value_store_size: int
    key_values: tuple[
        ParsedAndroidOatKeyValue,
        ...,
    ] = ()

    oat_dex_files: tuple[
        ParsedAndroidOatDexFile,
        ...,
    ] = ()

    bcp_bss_info: ParsedAndroidBcpBssInfo | None = None

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "checksum",
                self.checksum,
            ),
            (
                "instruction_set",
                self.instruction_set,
            ),
            (
                "instruction_set_features_bitmap",
                self.instruction_set_features_bitmap,
            ),
            (
                "dex_file_count",
                self.dex_file_count,
            ),
            (
                "oat_dex_files_offset",
                self.oat_dex_files_offset,
            ),
            (
                "bcp_bss_info_offset",
                self.bcp_bss_info_offset,
            ),
            (
                "executable_offset",
                self.executable_offset,
            ),
            (
                "key_value_store_size",
                self.key_value_store_size,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if len(
            self.oat_dex_files
        ) != self.dex_file_count:
            raise ValueError(
                "OatDexFile record count must exactly match "
                "dex_file_count"
            )

        expected_indices = tuple(
            range(
                self.dex_file_count
            )
        )

        actual_indices = tuple(
            item.index
            for item
            in self.oat_dex_files
        )

        if actual_indices != expected_indices:
            raise ValueError(
                "OatDexFile records must preserve canonical record order"
            )

        if (
            self.bcp_bss_info_offset == 0
            and self.bcp_bss_info is not None
        ):
            raise ValueError(
                "decoded BCP BSS info requires a nonzero header offset"
            )

        if (
            self.bcp_bss_info is not None
            and self.bcp_bss_info.offset
            != self.bcp_bss_info_offset
        ):
            raise ValueError(
                "decoded BCP BSS info offset must match header pointer"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidOat:
    elf: ParsedAndroidElf
    oat_offset: int
    magic: bytes
    version: bytes
    layout_supported: bool
    structural_header: ParsedAndroidOatStructuralHeader | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            not self.elf.source.is_filesystem_backed
            or self.elf.source.android_path is None
        ):
            raise ValueError(
                "OAT source must reuse a filesystem-backed canonical ELF"
            )

        if (
            self.elf.source.android_path.suffix.lower()
            not in {
                ".odex",
                ".oat",
            }
        ):
            raise ValueError(
                "OAT source must be a .odex or .oat ELF"
            )

        if self.oat_offset < 0:
            raise ValueError(
                "oat_offset must be non-negative"
            )

        if self.magic != b"oat\n":
            raise ValueError(
                "invalid OAT magic"
            )

        if len(
            self.version
        ) != 4:
            raise ValueError(
                "OAT version must be exactly four bytes"
            )

        if (
            self.layout_supported
            != (
                self.structural_header
                is not None
            )
        ):
            raise ValueError(
                "supported OAT layout must carry its decoded header"
            )

        if (
            self.structural_header is not None
            and self.version
            not in {
                b"236\x00",
                b"244\x00",
                b"251\x00",
            }
        ):
            raise ValueError(
                "supported OAT structural header must preserve "
                "version 236, 244, or 251"
            )

    @property
    def header(
        self,
    ) -> ParsedAndroidOatStructuralHeader | None:
        """
        Return the decoded structural OAT header independent of the exact
        supported version that supplied it.
        """

        return self.structural_header

    @property
    def oat_dex_files(
        self,
    ) -> tuple[
        ParsedAndroidOatDexFile,
        ...,
    ]:
        """
        Return decoded OatDexFile records independent of the supported
        serialized OAT version that supplied them.
        """

        if self.structural_header is None:
            return ()

        return self.structural_header.oat_dex_files

    @property
    def source_name(
        self,
    ) -> str:
        return self.elf.source.source_name


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidVdexSection:
    index: int
    kind: int
    offset: int
    size: int

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("index", self.index),
            ("kind", self.kind),
            ("offset", self.offset),
            ("size", self.size),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidVdex027:
    section_count: int
    sections: tuple[
        ParsedAndroidVdexSection,
        ...,
    ]
    dex_checksums: tuple[int, ...]
    dex_file_count: int
    has_dex_section: bool
    dex_files: tuple[
        ParsedAndroidDex,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if len(
            self.dex_checksums
        ) != self.dex_file_count:
            raise ValueError(
                "VDEX checksum count must exactly match dex_file_count"
            )

        if self.has_dex_section:
            if len(
                self.dex_files
            ) != self.dex_file_count:
                raise ValueError(
                    "populated VDEX DEX section must decode exactly "
                    "dex_file_count DEX payloads"
                )
        elif self.dex_files:
            raise ValueError(
                "VDEX without a physical DEX section must not carry "
                "decoded DEX payloads"
            )

        identities = tuple(
            dex.source.identity_key
            for dex
            in self.dex_files
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "VDEX-contained DEX identities must be unique"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidVdex:
    source: AndroidModelSource
    magic: bytes
    version: bytes
    layout_supported: bool
    vdex_027: ParsedAndroidVdex027 | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.source.kind
            is not AndroidModelSourceKind.ART_RUNTIME
        ):
            raise ValueError(
                "VDEX source must use ART_RUNTIME model-source kind"
            )

        if (
            self.source.android_path.suffix.lower()
            != ".vdex"
        ):
            raise ValueError(
                "VDEX source must have .vdex suffix"
            )

        if self.magic != b"vdex":
            raise ValueError(
                "invalid VDEX magic"
            )

        if len(
            self.version
        ) != 4:
            raise ValueError(
                "VDEX version must be exactly four bytes"
            )

        if (
            self.layout_supported
            != (
                self.vdex_027
                is not None
            )
        ):
            raise ValueError(
                "supported VDEX layout must carry its decoded structure"
            )

        if self.vdex_027 is not None:
            for dex in self.vdex_027.dex_files:
                dex_source = dex.source

                if (
                    dex_source.kind
                    is not AndroidDexSourceKind.VDEX_CONTAINED
                ):
                    raise ValueError(
                        "VDEX physical DEX children must use "
                        "VDEX_CONTAINED provenance"
                    )

                if dex_source.parent is not self.source:
                    raise ValueError(
                        "VDEX-contained DEX must retain the exact "
                        "canonical VDEX AndroidModelSource parent"
                    )

                if (
                    dex_source.parent_source_name
                    != self.source.source_name
                ):
                    raise ValueError(
                        "VDEX-contained DEX parent source name must "
                        "match canonical VDEX source"
                    )

                if (
                    dex_source.parent_android_path
                    != self.source.android_path
                ):
                    raise ValueError(
                        "VDEX-contained DEX parent Android path must "
                        "match canonical VDEX source"
                    )


class AndroidArtImageSectionKind(
    StrEnum
):
    OBJECTS = "objects"
    ART_FIELDS = "art_fields"
    ART_METHODS = "art_methods"
    IM_TABLES = "im_tables"
    IMT_CONFLICT_TABLES = "imt_conflict_tables"
    RUNTIME_METHODS = "runtime_methods"
    JNI_STUB_METHODS = "jni_stub_methods"
    INTERNED_STRINGS = "interned_strings"
    CLASS_TABLE = "class_table"
    STRING_REFERENCE_OFFSETS = "string_reference_offsets"
    DEX_CACHE_ARRAYS = "dex_cache_arrays"
    METADATA = "metadata"
    IMAGE_BITMAP = "image_bitmap"


ART_IMAGE_111_SECTION_KINDS = tuple(
    AndroidArtImageSectionKind
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidArtImageSection:
    index: int
    kind: AndroidArtImageSectionKind
    offset: int
    size: int

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            ("index", self.index),
            ("offset", self.offset),
            ("size", self.size),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidArtImage111:
    image_reservation_size: int
    component_count: int
    image_begin: int
    image_size: int
    image_checksum: int
    oat_checksum: int
    oat_file_begin: int
    oat_data_begin: int
    oat_data_end: int
    oat_file_end: int
    boot_image_begin: int
    boot_image_size: int
    boot_image_component_count: int
    boot_image_checksum: int
    image_roots: int
    pointer_size: int
    sections: tuple[
        ParsedAndroidArtImageSection,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidArtImage:
    source: AndroidModelSource
    magic: bytes
    version: bytes
    layout_supported: bool
    image_111: ParsedAndroidArtImage111 | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.source.kind
            is not AndroidModelSourceKind.ART_RUNTIME
        ):
            raise ValueError(
                "ART image source must use ART_RUNTIME model-source kind"
            )

        if (
            self.source.android_path.suffix.lower()
            != ".art"
        ):
            raise ValueError(
                "ART image source must have .art suffix"
            )

        if self.magic != b"art\n":
            raise ValueError(
                "invalid ART image magic"
            )

        if len(
            self.version
        ) != 4:
            raise ValueError(
                "ART image version must be exactly four bytes"
            )

        if (
            self.layout_supported
            != (
                self.image_111
                is not None
            )
        ):
            raise ValueError(
                "supported ART image layout must carry its decoded structure"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidArtRuntimeParsingResult:
    oat_files: tuple[
        ParsedAndroidOat,
        ...,
    ] = ()
    vdex_files: tuple[
        ParsedAndroidVdex,
        ...,
    ] = ()
    art_images: tuple[
        ParsedAndroidArtImage,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        oat_identities = tuple(
            item.elf.source.identity_key
            for item
            in self.oat_files
        )

        if oat_identities != tuple(
            sorted(
                oat_identities
            )
        ):
            raise ValueError(
                "OAT observations must use deterministic ELF identity order"
            )

        if len(
            set(
                oat_identities
            )
        ) != len(
            oat_identities
        ):
            raise ValueError(
                "duplicate OAT ELF identities"
            )

        oat_elf_object_ids = tuple(
            id(
                item.elf
            )
            for item
            in self.oat_files
        )

        if len(
            oat_elf_object_ids
        ) != len(
            set(
                oat_elf_object_ids
            )
        ):
            raise ValueError(
                "OAT observations must preserve unique canonical "
                "ParsedAndroidElf object identities"
            )

        for collection, label in (
            (
                self.vdex_files,
                "VDEX",
            ),
            (
                self.art_images,
                "ART image",
            ),
        ):
            identities = tuple(
                item.source.identity_key
                for item
                in collection
            )

            if identities != tuple(
                sorted(
                    identities
                )
            ):
                raise ValueError(
                    f"{label} observations must use deterministic source order"
                )

            if len(
                set(
                    identities
                )
            ) != len(
                identities
            ):
                raise ValueError(
                    f"duplicate {label} source identities"
                )

            source_object_ids = tuple(
                id(
                    item.source
                )
                for item
                in collection
            )

            if len(
                source_object_ids
            ) != len(
                set(
                    source_object_ids
                )
            ):
                raise ValueError(
                    f"{label} observations must preserve unique "
                    "canonical AndroidModelSource object identities"
                )

    @property
    def oat_count(
        self,
    ) -> int:
        return len(
            self.oat_files
        )

    @property
    def vdex_count(
        self,
    ) -> int:
        return len(
            self.vdex_files
        )

    @property
    def art_image_count(
        self,
    ) -> int:
        return len(
            self.art_images
        )

    @property
    def count(
        self,
    ) -> int:
        return (
            self.oat_count
            + self.vdex_count
            + self.art_image_count
        )
