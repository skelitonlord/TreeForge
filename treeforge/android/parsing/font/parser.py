from __future__ import annotations

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.font.model import (
    AndroidFontContainerKind,
    AndroidFontNameRecord,
    AndroidFontParsingResult,
    AndroidFontTable,
    ParsedAndroidFont,
    ParsedAndroidFontFace,
)


class AndroidFontParsingError(ValueError):
    """
    Raised when an installed font source cannot be structurally represented.
    """


def _u16(
    data: bytes,
    offset: int,
) -> int:
    end = offset + 2

    if offset < 0 or end > len(data):
        raise AndroidFontParsingError(
            "truncated font uint16"
        )

    return int.from_bytes(
        data[offset:end],
        "big",
    )


def _u32(
    data: bytes,
    offset: int,
) -> int:
    end = offset + 4

    if offset < 0 or end > len(data):
        raise AndroidFontParsingError(
            "truncated font uint32"
        )

    return int.from_bytes(
        data[offset:end],
        "big",
    )


class AndroidFontParser:
    """
    Parse intrinsic SFNT/OpenType/TrueType/TTC structure.

    No external font library is required. Parsing records only container
    structure and literal name-table evidence. Font fallback, language
    selection, rendering behavior, source ownership, and build ownership
    remain outside Parsing.
    """

    _SFNT_SIGNATURES = frozenset(
        {
            b"\x00\x01\x00\x00",
            b"OTTO",
            b"true",
            b"typ1",
        }
    )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidFontParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source
            in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.FONT
            )
        )

        fonts = tuple(
            self.parse_source(
                source
            )
            for source
            in sources
        )

        expected_source_ids = {
            id(source)
            for source
            in sources
        }

        actual_source_ids = {
            id(font.source)
            for font
            in fonts
        }

        if (
            expected_source_ids
            != actual_source_ids
        ):
            raise AndroidFontParsingError(
                "font Parsing failed to conserve the complete "
                "canonical FONT source population"
            )

        if len(
            actual_source_ids
        ) != len(
            fonts
        ):
            raise AndroidFontParsingError(
                "font Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return AndroidFontParsingResult(
            fonts=tuple(
                sorted(
                    fonts,
                    key=lambda font: (
                        font.source.identity_key
                    ),
                )
            )
        )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidFont:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            source.kind
            is not AndroidModelSourceKind.FONT
        ):
            raise ValueError(
                "source must be a FONT source"
            )

        try:
            data = source.host_path.read_bytes()
        except OSError as error:
            raise AndroidFontParsingError(
                "unable to read font source "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        if len(data) < 4:
            raise AndroidFontParsingError(
                "font source is too small: "
                f"{source.source_name}:"
                f"{source.android_path}"
            )

        try:
            if data[:4] == b"ttcf":
                return self._parse_collection(
                    source=source,
                    data=data,
                )

            return self._parse_standalone(
                source=source,
                data=data,
            )

        except AndroidFontParsingError as error:
            raise AndroidFontParsingError(
                "failed to parse font "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

    def _parse_standalone(
        self,
        *,
        source: AndroidModelSource,
        data: bytes,
    ) -> ParsedAndroidFont:
        face = self._parse_face(
            data=data,
            face_index=0,
            offset=0,
        )

        return ParsedAndroidFont(
            source=source,
            file_size=len(data),
            container_kind=(
                AndroidFontContainerKind.SFNT
            ),
            collection_version=None,
            faces=(
                face,
            ),
        )

    def _parse_collection(
        self,
        *,
        source: AndroidModelSource,
        data: bytes,
    ) -> ParsedAndroidFont:
        if len(data) < 12:
            raise AndroidFontParsingError(
                "truncated TTC header"
            )

        collection_version = _u32(
            data,
            4,
        )

        face_count = _u32(
            data,
            8,
        )

        if face_count < 1:
            raise AndroidFontParsingError(
                "TTC contains zero faces"
            )

        if face_count > 4096:
            raise AndroidFontParsingError(
                "TTC face count exceeds supported structural limit"
            )

        offsets_end = (
            12
            + (
                face_count
                * 4
            )
        )

        if offsets_end > len(data):
            raise AndroidFontParsingError(
                "truncated TTC face-offset table"
            )

        face_offsets = tuple(
            _u32(
                data,
                12 + index * 4,
            )
            for index in range(
                face_count
            )
        )

        faces = tuple(
            self._parse_face(
                data=data,
                face_index=index,
                offset=offset,
            )
            for index, offset
            in enumerate(
                face_offsets
            )
        )

        return ParsedAndroidFont(
            source=source,
            file_size=len(data),
            container_kind=(
                AndroidFontContainerKind
                .TRUE_TYPE_COLLECTION
            ),
            collection_version=(
                collection_version
            ),
            faces=faces,
        )

    def _parse_face(
        self,
        *,
        data: bytes,
        face_index: int,
        offset: int,
    ) -> ParsedAndroidFontFace:
        header_end = offset + 12

        if (
            offset < 0
            or header_end > len(data)
        ):
            raise AndroidFontParsingError(
                "truncated SFNT face header"
            )

        sfnt_version = data[
            offset:
            offset + 4
        ]

        if (
            sfnt_version
            not in self._SFNT_SIGNATURES
        ):
            raise AndroidFontParsingError(
                "unsupported SFNT signature "
                f"{sfnt_version!r}"
            )

        table_count = _u16(
            data,
            offset + 4,
        )

        directory_end = (
            offset
            + 12
            + table_count * 16
        )

        if directory_end > len(data):
            raise AndroidFontParsingError(
                "truncated SFNT table directory"
            )

        tables = []

        for index in range(
            table_count
        ):
            record_offset = (
                offset
                + 12
                + index * 16
            )

            raw_tag = data[
                record_offset:
                record_offset + 4
            ]

            tag = raw_tag.decode(
                "latin-1"
            )

            checksum = _u32(
                data,
                record_offset + 4,
            )

            table_offset = _u32(
                data,
                record_offset + 8,
            )

            table_length = _u32(
                data,
                record_offset + 12,
            )

            table_end = (
                table_offset
                + table_length
            )

            if table_end > len(data):
                raise AndroidFontParsingError(
                    "SFNT table exceeds font payload: "
                    f"{tag!r}"
                )

            tables.append(
                AndroidFontTable(
                    tag=tag,
                    checksum=checksum,
                    offset=table_offset,
                    length=table_length,
                )
            )

        tables_tuple = tuple(
            tables
        )

        name_table = next(
            (
                table
                for table in tables_tuple
                if table.tag == "name"
            ),
            None,
        )

        names = (
            ()
            if name_table is None
            else self._parse_name_table(
                data=data,
                table=name_table,
            )
        )

        return ParsedAndroidFontFace(
            face_index=face_index,
            offset=offset,
            sfnt_version=sfnt_version,
            tables=tables_tuple,
            names=names,
        )

    def _parse_name_table(
        self,
        *,
        data: bytes,
        table: AndroidFontTable,
    ) -> tuple[
        AndroidFontNameRecord,
        ...,
    ]:
        table_start = table.offset
        table_end = (
            table.offset
            + table.length
        )

        if (
            table.length < 6
            or table_end > len(data)
        ):
            raise AndroidFontParsingError(
                "truncated SFNT name table"
            )

        record_count = _u16(
            data,
            table_start + 2,
        )

        string_offset = _u16(
            data,
            table_start + 4,
        )

        records_end = (
            table_start
            + 6
            + record_count * 12
        )

        string_base = (
            table_start
            + string_offset
        )

        if (
            records_end > table_end
            or string_base > table_end
        ):
            raise AndroidFontParsingError(
                "invalid SFNT name-table layout"
            )

        records = []

        for index in range(
            record_count
        ):
            record_offset = (
                table_start
                + 6
                + index * 12
            )

            platform_id = _u16(
                data,
                record_offset,
            )
            encoding_id = _u16(
                data,
                record_offset + 2,
            )
            language_id = _u16(
                data,
                record_offset + 4,
            )
            name_id = _u16(
                data,
                record_offset + 6,
            )
            value_length = _u16(
                data,
                record_offset + 8,
            )
            value_offset = _u16(
                data,
                record_offset + 10,
            )

            value_start = (
                string_base
                + value_offset
            )
            value_end = (
                value_start
                + value_length
            )

            if (
                value_start < string_base
                or value_end > table_end
            ):
                raise AndroidFontParsingError(
                    "SFNT name record exceeds string storage"
                )

            raw_value = data[
                value_start:
                value_end
            ]

            decoded_value = (
                self._decode_name(
                    platform_id=platform_id,
                    raw_value=raw_value,
                )
            )

            records.append(
                AndroidFontNameRecord(
                    record_index=index,
                    platform_id=platform_id,
                    encoding_id=encoding_id,
                    language_id=language_id,
                    name_id=name_id,
                    raw_value=raw_value,
                    decoded_value=decoded_value,
                )
            )

        return tuple(
            records
        )

    @staticmethod
    def _decode_name(
        *,
        platform_id: int,
        raw_value: bytes,
    ) -> str | None:
        if platform_id in {
            0,
            3,
        }:
            encoding = "utf-16-be"
        elif platform_id == 1:
            encoding = "mac_roman"
        elif platform_id == 2:
            encoding = "latin-1"
        else:
            return None

        try:
            return raw_value.decode(
                encoding
            )
        except UnicodeDecodeError:
            return None
