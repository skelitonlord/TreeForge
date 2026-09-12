from __future__ import annotations

import struct

from treeforge.android.parsing.art_runtime.model import (
    AndroidDexLayoutSectionKind,
    AndroidDexLayoutType,
    AndroidOatDexStorageDisposition,
    ParsedAndroidBcpBssInfo,
    ParsedAndroidBcpBssMappingInfo,
    ParsedAndroidIndexBssMapping,
    ParsedAndroidIndexBssMappingEntry,
    ParsedAndroidDexLayoutSection,
    ParsedAndroidDexLayoutSections,
    ParsedAndroidDexLayoutSubsection,
    ParsedAndroidOat,
    ParsedAndroidOatStructuralHeader,
    ParsedAndroidOatDexFile,
    ParsedAndroidOatKeyValue,
)
from treeforge.android.parsing.elf.model import (
    AndroidElfParsingResult,
    ParsedAndroidElf,
)


class AndroidOatParsingError(
    ValueError,
):
    pass


class AndroidOatParser:
    MAGIC = b"oat\n"
    VERSION_236 = b"236\x00"
    VERSION_244 = b"244\x00"
    VERSION_251 = b"251\x00"

    SUPPORTED_STRUCTURAL_VERSIONS = frozenset(
        {
            VERSION_236,
            VERSION_244,
            VERSION_251,
        }
    )

    OAT_STRUCTURAL_FIXED_SIZE = 0x44

    #
    # DexLayoutSections:
    #
    #   SectionType:
    #       code
    #       strings
    #
    #   Each DexLayoutSection contains one Subsection for each LayoutType:
    #       hot
    #       sometimes-used
    #       startup-only
    #       used-once
    #       unused
    #
    #   Each Subsection is exactly:
    #       uint32 start_offset
    #       uint32 end_offset
    #
    DEX_LAYOUT_SECTION_KINDS = (
        AndroidDexLayoutSectionKind.CODE,
        AndroidDexLayoutSectionKind.STRINGS,
    )

    DEX_LAYOUT_TYPES = (
        AndroidDexLayoutType.HOT,
        AndroidDexLayoutType.SOMETIMES_USED,
        AndroidDexLayoutType.STARTUP_ONLY,
        AndroidDexLayoutType.USED_ONCE,
        AndroidDexLayoutType.UNUSED,
    )

    DEX_LAYOUT_SUBSECTION_SIZE = 8
    DEX_LAYOUT_SECTIONS_SIZE = (
        len(
            DEX_LAYOUT_SECTION_KINDS
        )
        * len(
            DEX_LAYOUT_TYPES
        )
        * DEX_LAYOUT_SUBSECTION_SIZE
    )

    def parse(
        self,
        elf: AndroidElfParsingResult,
    ) -> tuple[
        ParsedAndroidOat,
        ...,
    ]:
        candidates = tuple(
            item
            for item
            in elf.elf_files
            if (
                item.source.is_filesystem_backed
                and item.source.android_path is not None
                and (
                    item.source.android_path.suffix.lower()
                    in {
                        ".odex",
                        ".oat",
                    }
                )
            )
        )

        parsed = tuple(
            self.parse_elf(
                item
            )
            for item
            in candidates
        )

        expected_elf_ids = {
            id(item)
            for item
            in candidates
        }

        actual_elf_ids = {
            id(value.elf)
            for value
            in parsed
        }

        if (
            expected_elf_ids
            != actual_elf_ids
        ):
            raise AndroidOatParsingError(
                "OAT Parsing failed to conserve the complete "
                "canonical .oat/.odex ELF population"
            )

        if len(
            actual_elf_ids
        ) != len(
            parsed
        ):
            raise AndroidOatParsingError(
                "OAT Parsing duplicated a canonical "
                "ParsedAndroidElf"
            )

        return tuple(
            sorted(
                parsed,
                key=lambda value: (
                    value.elf.source.identity_key
                ),
            )
        )

    def parse_elf(
        self,
        elf: ParsedAndroidElf,
    ) -> ParsedAndroidOat:
        content = elf.source.host_path.read_bytes()

        offset = content.find(
            self.MAGIC
        )

        if offset < 0:
            raise AndroidOatParsingError(
                "OAT magic not found in canonical ELF source: "
                f"{elf.source.display_path}"
            )

        if len(
            content
        ) < offset + 8:
            raise AndroidOatParsingError(
                "truncated OAT identity header"
            )

        magic = content[
            offset:offset + 4
        ]

        version = content[
            offset + 4:offset + 8
        ]

        if version not in self.SUPPORTED_STRUCTURAL_VERSIONS:
            return ParsedAndroidOat(
                elf=elf,
                oat_offset=offset,
                magic=magic,
                version=version,
                layout_supported=False,
            )

        header = self._parse_structural_header(
            content,
            offset,
            version=version,
        )

        return ParsedAndroidOat(
            elf=elf,
            oat_offset=offset,
            magic=magic,
            version=version,
            layout_supported=True,
            structural_header=header,
        )

    def _parse_structural_header(
        self,
        content: bytes,
        offset: int,
        *,
        version: bytes,
    ) -> ParsedAndroidOatStructuralHeader:
        end = (
            offset
            + self.OAT_STRUCTURAL_FIXED_SIZE
        )

        if len(
            content
        ) < end:
            raise AndroidOatParsingError(
                "truncated OAT "
                f"{version.rstrip(bytes((0,))).decode('ascii')} "
                "fixed header"
            )

        fields = struct.unpack_from(
            "<15I",
            content,
            offset + 8,
        )

        (
            checksum,
            instruction_set,
            instruction_set_features_bitmap,
            dex_file_count,
            oat_dex_files_offset,
            bcp_bss_info_offset,
            executable_offset,
            jni_dlsym_lookup_trampoline_offset,
            jni_dlsym_lookup_critical_trampoline_offset,
            quick_generic_jni_trampoline_offset,
            quick_imt_conflict_trampoline_offset,
            quick_resolution_trampoline_offset,
            quick_to_interpreter_bridge_offset,
            nterp_trampoline_offset,
            key_value_store_size,
        ) = fields

        store_start = end
        store_end = (
            store_start
            + key_value_store_size
        )

        if store_end > len(
            content
        ):
            raise AndroidOatParsingError(
                "supported OAT key/value store exceeds source size"
            )

        key_values = self._parse_key_values(
            content[
                store_start:store_end
            ]
        )

        oat_dex_files = (
            self._parse_oat_dex_files(
                content=content,
                oat_offset=offset,
                header_size=(
                    store_end
                    - offset
                ),
                dex_file_count=dex_file_count,
                oat_dex_files_offset=(
                    oat_dex_files_offset
                ),
                has_dex_identity_fields=(
                    version != self.VERSION_236
                ),
                has_method_type_bss_mapping=(
                    version != self.VERSION_236
                ),
            )
        )

        #
        # bcp_bss_info_offset is retained exactly as serialized.
        #
        # Do not follow this pointer here until the target structure and
        # offset-base semantics are proven generically for the selected OAT
        # layout. Treat a nonzero value as deferred structural evidence,
        # rather than guessing from observed file layout.
        #
        bcp_bss_info = None

        return ParsedAndroidOatStructuralHeader(
            checksum=checksum,
            instruction_set=instruction_set,
            instruction_set_features_bitmap=(
                instruction_set_features_bitmap
            ),
            dex_file_count=dex_file_count,
            oat_dex_files_offset=oat_dex_files_offset,
            bcp_bss_info_offset=bcp_bss_info_offset,
            executable_offset=executable_offset,
            jni_dlsym_lookup_trampoline_offset=(
                jni_dlsym_lookup_trampoline_offset
            ),
            jni_dlsym_lookup_critical_trampoline_offset=(
                jni_dlsym_lookup_critical_trampoline_offset
            ),
            quick_generic_jni_trampoline_offset=(
                quick_generic_jni_trampoline_offset
            ),
            quick_imt_conflict_trampoline_offset=(
                quick_imt_conflict_trampoline_offset
            ),
            quick_resolution_trampoline_offset=(
                quick_resolution_trampoline_offset
            ),
            quick_to_interpreter_bridge_offset=(
                quick_to_interpreter_bridge_offset
            ),
            nterp_trampoline_offset=(
                nterp_trampoline_offset
            ),
            key_value_store_size=(
                key_value_store_size
            ),
            key_values=key_values,
            oat_dex_files=oat_dex_files,
            bcp_bss_info=bcp_bss_info,
        )

    @classmethod
    def _parse_dex_layout_sections(
        cls,
        *,
        content: bytes,
        oat_offset: int,
        dex_layout_sections_offset: int,
        oat_dex_file_index: int,
    ) -> ParsedAndroidDexLayoutSections | None:
        """
        Follow and decode one OAT-relative DexLayoutSections pointer.

        ART treats dex_layout_sections_offset as relative to OatFile::Begin().
        TreeForge's `oat_offset` is the beginning of that OAT payload inside
        the containing ELF, so the host-file target is:

            oat_offset + dex_layout_sections_offset
        """

        if dex_layout_sections_offset == 0:
            return None

        target = (
            oat_offset
            + dex_layout_sections_offset
        )

        end = (
            target
            + cls.DEX_LAYOUT_SECTIONS_SIZE
        )

        if (
            target < oat_offset
            or target > len(
                content
            )
            or end > len(
                content
            )
        ):
            raise AndroidOatParsingError(
                "OatDexFile DexLayoutSections exceeds source size: "
                f"index={oat_dex_file_index} "
                f"offset={dex_layout_sections_offset} "
                f"size={cls.DEX_LAYOUT_SECTIONS_SIZE}"
            )

        cursor = target
        sections = []

        for (
            section_index,
            section_kind,
        ) in enumerate(
            cls.DEX_LAYOUT_SECTION_KINDS
        ):
            subsections = []

            for (
                subsection_index,
                layout_kind,
            ) in enumerate(
                cls.DEX_LAYOUT_TYPES
            ):
                (
                    start_offset,
                    end_offset,
                ) = struct.unpack_from(
                    "<II",
                    content,
                    cursor,
                )

                cursor += (
                    cls.DEX_LAYOUT_SUBSECTION_SIZE
                )

                if end_offset < start_offset:
                    raise AndroidOatParsingError(
                        "OatDexFile DexLayoutSections contains an "
                        "inverted DEX-relative range: "
                        f"index={oat_dex_file_index} "
                        f"section={section_kind.value} "
                        f"layout={layout_kind.value} "
                        f"start={start_offset} "
                        f"end={end_offset}"
                    )

                subsections.append(
                    ParsedAndroidDexLayoutSubsection(
                        index=subsection_index,
                        kind=layout_kind,
                        start_offset=start_offset,
                        end_offset=end_offset,
                    )
                )

            sections.append(
                ParsedAndroidDexLayoutSection(
                    index=section_index,
                    kind=section_kind,
                    subsections=tuple(
                        subsections
                    ),
                )
            )

        if cursor != end:
            raise AndroidOatParsingError(
                "DexLayoutSections decoder did not consume its "
                "complete fixed structure"
            )

        return ParsedAndroidDexLayoutSections(
            offset=dex_layout_sections_offset,
            size=cls.DEX_LAYOUT_SECTIONS_SIZE,
            sections=tuple(
                sections
            ),
        )

    @classmethod
    def _parse_index_bss_mapping(
        cls,
        *,
        content: bytes,
        oat_offset: int,
        mapping_offset: int,
        label: str,
    ) -> ParsedAndroidIndexBssMapping | None:
        """
        Follow one OAT-relative ART IndexBssMapping pointer.

        IndexBssMapping is a LengthPrefixedArray of fixed-size
        IndexBssMappingEntry records, so its complete byte extent is
        derivable from the serialized mapping itself without DEX identity
        resolution.
        """

        if mapping_offset == 0:
            return None

        if mapping_offset % 4 != 0:
            raise AndroidOatParsingError(
                f"{label} IndexBssMapping offset is not uint32 aligned: "
                f"{mapping_offset}"
            )

        target = (
            oat_offset
            + mapping_offset
        )

        if (
            target < oat_offset
            or target + 4 > len(
                content
            )
        ):
            raise AndroidOatParsingError(
                f"{label} IndexBssMapping length prefix exceeds source"
            )

        entry_count = struct.unpack_from(
            "<I",
            content,
            target,
        )[0]

        if entry_count == 0:
            raise AndroidOatParsingError(
                f"{label} IndexBssMapping has zero entries"
            )

        size = (
            4
            + entry_count * 8
        )

        end = (
            target
            + size
        )

        if end > len(
            content
        ):
            raise AndroidOatParsingError(
                f"{label} IndexBssMapping exceeds source: "
                f"offset={mapping_offset} "
                f"entries={entry_count} "
                f"size={size}"
            )

        entries = tuple(
            ParsedAndroidIndexBssMappingEntry(
                index=index,
                index_and_mask=struct.unpack_from(
                    "<I",
                    content,
                    target + 4 + index * 8,
                )[0],
                bss_offset=struct.unpack_from(
                    "<I",
                    content,
                    target + 8 + index * 8,
                )[0],
            )
            for index
            in range(
                entry_count
            )
        )

        return ParsedAndroidIndexBssMapping(
            offset=mapping_offset,
            size=size,
            entry_count=entry_count,
            entries=entries,
        )

    @classmethod
    def _parse_bcp_bss_info(
        cls,
        *,
        content: bytes,
        oat_offset: int,
        bcp_bss_info_offset: int,
        has_method_type_bss_mapping: bool,
    ) -> ParsedAndroidBcpBssInfo | None:
        """
        Decode the OAT header's boot-class-path BSS metadata.

        A nonzero bcp_bss_info_offset points to:
          uint32 dex_file_count
          dex_file_count fixed BSS-mapping-offset records

        The record width follows the self-described OAT layout already
        selected by the caller.
        """

        if bcp_bss_info_offset == 0:
            return None

        target = (
            oat_offset
            + bcp_bss_info_offset
        )

        if (
            bcp_bss_info_offset % 4 != 0
            or target < oat_offset
            or target + 4 > len(
                content
            )
        ):
            raise AndroidOatParsingError(
                "BCP BSS info pointer is invalid or truncated"
            )

        dex_file_count = struct.unpack_from(
            "<I",
            content,
            target,
        )[0]

        if dex_file_count == 0:
            raise AndroidOatParsingError(
                "nonzero BCP BSS info contains zero DEX records"
            )

        record_size = (
            24
            if has_method_type_bss_mapping
            else 20
        )

        records_start = (
            target
            + 4
        )

        records_end = (
            records_start
            + dex_file_count * record_size
        )

        if records_end > len(
            content
        ):
            raise AndroidOatParsingError(
                "BCP BSS info records exceed source: "
                f"count={dex_file_count} "
                f"record_size={record_size}"
            )

        records = []

        for index in range(
            dex_file_count
        ):
            record_offset = (
                records_start
                + index * record_size
            )

            offsets = struct.unpack_from(
                (
                    "<6I"
                    if has_method_type_bss_mapping
                    else "<5I"
                ),
                content,
                record_offset,
            )

            method_offset = offsets[0]
            type_offset = offsets[1]
            public_type_offset = offsets[2]
            package_type_offset = offsets[3]
            string_offset = offsets[4]

            method_type_offset = (
                offsets[5]
                if has_method_type_bss_mapping
                else None
            )

            records.append(
                ParsedAndroidBcpBssMappingInfo(
                    index=index,
                    method_bss_mapping_offset=method_offset,
                    type_bss_mapping_offset=type_offset,
                    public_type_bss_mapping_offset=public_type_offset,
                    package_type_bss_mapping_offset=package_type_offset,
                    string_bss_mapping_offset=string_offset,
                    method_type_bss_mapping_offset=method_type_offset,
                    method_bss_mapping=(
                        cls._parse_index_bss_mapping(
                            content=content,
                            oat_offset=oat_offset,
                            mapping_offset=method_offset,
                            label=(
                                f"BCP[{index}] method"
                            ),
                        )
                    ),
                    type_bss_mapping=(
                        cls._parse_index_bss_mapping(
                            content=content,
                            oat_offset=oat_offset,
                            mapping_offset=type_offset,
                            label=(
                                f"BCP[{index}] type"
                            ),
                        )
                    ),
                    public_type_bss_mapping=(
                        cls._parse_index_bss_mapping(
                            content=content,
                            oat_offset=oat_offset,
                            mapping_offset=public_type_offset,
                            label=(
                                f"BCP[{index}] public-type"
                            ),
                        )
                    ),
                    package_type_bss_mapping=(
                        cls._parse_index_bss_mapping(
                            content=content,
                            oat_offset=oat_offset,
                            mapping_offset=package_type_offset,
                            label=(
                                f"BCP[{index}] package-type"
                            ),
                        )
                    ),
                    string_bss_mapping=(
                        cls._parse_index_bss_mapping(
                            content=content,
                            oat_offset=oat_offset,
                            mapping_offset=string_offset,
                            label=(
                                f"BCP[{index}] string"
                            ),
                        )
                    ),
                    method_type_bss_mapping=(
                        cls._parse_index_bss_mapping(
                            content=content,
                            oat_offset=oat_offset,
                            mapping_offset=method_type_offset,
                            label=(
                                f"BCP[{index}] method-type"
                            ),
                        )
                        if method_type_offset is not None
                        else None
                    ),
                )
            )

        return ParsedAndroidBcpBssInfo(
            offset=bcp_bss_info_offset,
            record_size=record_size,
            dex_file_count=dex_file_count,
            records=tuple(
                records
            ),
        )

    @classmethod
    def _parse_oat_dex_files(
        cls,
        *,
        content: bytes,
        oat_offset: int,
        header_size: int,
        dex_file_count: int,
        oat_dex_files_offset: int,
        has_dex_identity_fields: bool,
        has_method_type_bss_mapping: bool,
    ) -> tuple[
        ParsedAndroidOatDexFile,
        ...,
    ]:
        """
        Decode exact supported OAT OatDexFile records.

        `oat_dex_files_offset` is relative to the OAT beginning. Encoded
        offsets remain exact structural evidence. DexLayoutSections pointers
        are additionally followed and decoded here because their target is a
        fixed binary structure; semantic DEX-container reconciliation remains
        outside Parsing.
        """

        if oat_dex_files_offset < header_size:
            raise AndroidOatParsingError(
                "supported OAT oat_dex_files_offset precedes end of header"
            )

        cursor = (
            oat_offset
            + oat_dex_files_offset
        )

        if (
            cursor < oat_offset
            or cursor > len(
                content
            )
        ):
            raise AndroidOatParsingError(
                "supported OAT oat_dex_files_offset exceeds source size"
            )

        records = []

        def require(
            size: int,
            *,
            label: str,
            index: int,
        ) -> None:
            if (
                size < 0
                or cursor + size
                > len(
                    content
                )
            ):
                raise AndroidOatParsingError(
                    "truncated OatDexFile "
                    f"record index={index} after {label}"
                )

        def read_u32(
            *,
            label: str,
            index: int,
        ) -> int:
            nonlocal cursor

            require(
                4,
                label=label,
                index=index,
            )

            value = struct.unpack_from(
                "<I",
                content,
                cursor,
            )[0]

            cursor += 4

            return value

        def read_bytes(
            size: int,
            *,
            label: str,
            index: int,
        ) -> bytes:
            nonlocal cursor

            require(
                size,
                label=label,
                index=index,
            )

            value = content[
                cursor:
                cursor + size
            ]

            cursor += size

            return value

        for index in range(
            dex_file_count
        ):
            record_start = cursor

            location_size = read_u32(
                label="location size",
                index=index,
            )

            if location_size == 0:
                raise AndroidOatParsingError(
                    "OatDexFile location must not be empty: "
                    f"index={index}"
                )

            location_bytes = read_bytes(
                location_size,
                label="location",
                index=index,
            )

            try:
                location = (
                    location_bytes.decode(
                        "utf-8"
                    )
                )
            except UnicodeDecodeError as error:
                raise AndroidOatParsingError(
                    "OatDexFile location is not valid UTF-8: "
                    f"index={index}"
                ) from error

            #
            # OAT 236 factory artifacts predate the serialized DEX magic/SHA-1
            # identity fields. OAT 244/251 carry both fields.
            #
            dex_magic = (
                read_bytes(
                    8,
                    label="DEX magic",
                    index=index,
                )
                if has_dex_identity_fields
                else None
            )

            dex_checksum = read_u32(
                label="DEX checksum",
                index=index,
            )

            dex_sha1 = (
                read_bytes(
                    20,
                    label="DEX SHA-1",
                    index=index,
                )
                if has_dex_identity_fields
                else None
            )

            dex_file_offset = read_u32(
                label="DEX file offset",
                index=index,
            )

            class_offsets_offset = read_u32(
                label="class offsets offset",
                index=index,
            )

            lookup_table_offset = read_u32(
                label="lookup table offset",
                index=index,
            )

            dex_layout_sections_offset = (
                read_u32(
                    label=(
                        "DEX layout sections offset"
                    ),
                    index=index,
                )
            )

            #
            # ART consumes five IndexBssMapping offsets in OAT 236.
            # OAT 244/251 append method-type mapping as the sixth offset.
            # Their target structures remain later semantic/structural work.
            #
            method_bss_mapping_offset = (
                read_u32(
                    label=(
                        "method BSS mapping offset"
                    ),
                    index=index,
                )
            )

            type_bss_mapping_offset = (
                read_u32(
                    label=(
                        "type BSS mapping offset"
                    ),
                    index=index,
                )
            )

            public_type_bss_mapping_offset = (
                read_u32(
                    label=(
                        "public type BSS mapping offset"
                    ),
                    index=index,
                )
            )

            package_type_bss_mapping_offset = (
                read_u32(
                    label=(
                        "package type BSS mapping offset"
                    ),
                    index=index,
                )
            )

            string_bss_mapping_offset = (
                read_u32(
                    label=(
                        "string BSS mapping offset"
                    ),
                    index=index,
                )
            )

            method_type_bss_mapping_offset = (
                read_u32(
                    label=(
                        "method type BSS mapping offset"
                    ),
                    index=index,
                )
                if has_method_type_bss_mapping
                else None
            )

            dex_layout_sections = (
                cls._parse_dex_layout_sections(
                    content=content,
                    oat_offset=oat_offset,
                    dex_layout_sections_offset=(
                        dex_layout_sections_offset
                    ),
                    oat_dex_file_index=index,
                )
            )

            method_bss_mapping = (
                cls._parse_index_bss_mapping(
                    content=content,
                    oat_offset=oat_offset,
                    mapping_offset=method_bss_mapping_offset,
                    label=f"OatDexFile[{index}] method",
                )
            )

            type_bss_mapping = (
                cls._parse_index_bss_mapping(
                    content=content,
                    oat_offset=oat_offset,
                    mapping_offset=type_bss_mapping_offset,
                    label=f"OatDexFile[{index}] type",
                )
            )

            public_type_bss_mapping = (
                cls._parse_index_bss_mapping(
                    content=content,
                    oat_offset=oat_offset,
                    mapping_offset=public_type_bss_mapping_offset,
                    label=f"OatDexFile[{index}] public-type",
                )
            )

            package_type_bss_mapping = (
                cls._parse_index_bss_mapping(
                    content=content,
                    oat_offset=oat_offset,
                    mapping_offset=package_type_bss_mapping_offset,
                    label=f"OatDexFile[{index}] package-type",
                )
            )

            string_bss_mapping = (
                cls._parse_index_bss_mapping(
                    content=content,
                    oat_offset=oat_offset,
                    mapping_offset=string_bss_mapping_offset,
                    label=f"OatDexFile[{index}] string",
                )
            )

            method_type_bss_mapping = (
                cls._parse_index_bss_mapping(
                    content=content,
                    oat_offset=oat_offset,
                    mapping_offset=method_type_bss_mapping_offset,
                    label=f"OatDexFile[{index}] method-type",
                )
                if method_type_bss_mapping_offset is not None
                else None
            )

            records.append(
                ParsedAndroidOatDexFile(
                    index=index,
                    record_offset=(
                        record_start
                        - oat_offset
                    ),
                    record_size=(
                        cursor
                        - record_start
                    ),
                    dex_file_location_size=(
                        location_size
                    ),
                    dex_file_location_bytes=(
                        location_bytes
                    ),
                    dex_file_location=location,
                    dex_file_magic=dex_magic,
                    dex_file_location_checksum=(
                        dex_checksum
                    ),
                    dex_file_sha1=dex_sha1,
                    dex_file_offset=(
                        dex_file_offset
                    ),
                    dex_storage_disposition=(
                        AndroidOatDexStorageDisposition.DEX_REGION_OFFSET
                        if dex_file_offset != 0
                        else AndroidOatDexStorageDisposition.EXTERNAL_DEX
                    ),
                    class_offsets_offset=(
                        class_offsets_offset
                    ),
                    lookup_table_offset=(
                        lookup_table_offset
                    ),
                    dex_layout_sections_offset=(
                        dex_layout_sections_offset
                    ),
                    dex_layout_sections=(
                        dex_layout_sections
                    ),
                    method_bss_mapping_offset=(
                        method_bss_mapping_offset
                    ),
                    type_bss_mapping_offset=(
                        type_bss_mapping_offset
                    ),
                    public_type_bss_mapping_offset=(
                        public_type_bss_mapping_offset
                    ),
                    package_type_bss_mapping_offset=(
                        package_type_bss_mapping_offset
                    ),
                    string_bss_mapping_offset=(
                        string_bss_mapping_offset
                    ),
                    method_type_bss_mapping_offset=(
                        method_type_bss_mapping_offset
                    ),
                    method_bss_mapping=(
                        method_bss_mapping
                    ),
                    type_bss_mapping=(
                        type_bss_mapping
                    ),
                    public_type_bss_mapping=(
                        public_type_bss_mapping
                    ),
                    package_type_bss_mapping=(
                        package_type_bss_mapping
                    ),
                    string_bss_mapping=(
                        string_bss_mapping
                    ),
                    method_type_bss_mapping=(
                        method_type_bss_mapping
                    ),
                )
            )

        return tuple(
            records
        )

    @staticmethod
    def _parse_key_values(
        store: bytes,
    ) -> tuple[
        ParsedAndroidOatKeyValue,
        ...,
    ]:
        values = []
        cursor = 0
        index = 0

        while cursor < len(
            store
        ):
            key_end = store.find(
                b"\x00",
                cursor,
            )

            if key_end < 0:
                raise AndroidOatParsingError(
                    "unterminated OAT key"
                )

            key_offset = cursor
            key_bytes = store[
                cursor:key_end
            ]

            value_start = (
                key_end
                + 1
            )

            value_end = store.find(
                b"\x00",
                value_start,
            )

            if value_end < 0:
                raise AndroidOatParsingError(
                    "unterminated OAT value"
                )

            value_bytes = store[
                value_start:value_end
            ]

            try:
                key = key_bytes.decode(
                    "utf-8"
                )

                value = value_bytes.decode(
                    "utf-8"
                )
            except UnicodeDecodeError as error:
                raise AndroidOatParsingError(
                    "OAT key/value store is not valid UTF-8"
                ) from error

            values.append(
                ParsedAndroidOatKeyValue(
                    index=index,
                    key_offset=key_offset,
                    value_offset=value_start,
                    key=key,
                    value=value,
                )
            )

            cursor = (
                value_end
                + 1
            )

            index += 1

        return tuple(
            values
        )
