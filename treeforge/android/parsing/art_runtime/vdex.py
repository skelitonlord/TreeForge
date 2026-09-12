from __future__ import annotations

import struct

from treeforge.android.parsing.art_runtime.model import (
    ParsedAndroidVdex,
    ParsedAndroidVdex027,
    ParsedAndroidVdexSection,
)
from treeforge.android.parsing.dex.model import (
    AndroidDexSource,
    AndroidDexSourceKind,
)
from treeforge.android.parsing.dex.parser import (
    AndroidDexParser,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)


class AndroidVdexParsingError(
    ValueError,
):
    pass


class AndroidVdexParser:
    MAGIC = b"vdex"
    VERSION_027 = b"027\x00"
    FILE_HEADER_SIZE = 12
    SECTION_HEADER_SIZE = 12
    VERSION_027_SECTION_COUNT = 4

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidVdex:
        content = source.host_path.read_bytes()

        if len(
            content
        ) < 8:
            raise AndroidVdexParsingError(
                "truncated VDEX identity header"
            )

        magic = content[:4]
        version = content[
            4:8
        ]

        if magic != self.MAGIC:
            raise AndroidVdexParsingError(
                "invalid VDEX magic"
            )

        if version != self.VERSION_027:
            return ParsedAndroidVdex(
                source=source,
                magic=magic,
                version=version,
                layout_supported=False,
            )

        return ParsedAndroidVdex(
            source=source,
            magic=magic,
            version=version,
            layout_supported=True,
            vdex_027=self._parse_027(
                content,
                source=source,
            ),
        )

    def _parse_027(
        self,
        content: bytes,
        *,
        source: AndroidModelSource,
    ) -> ParsedAndroidVdex027:
        if len(
            content
        ) < self.FILE_HEADER_SIZE:
            raise AndroidVdexParsingError(
                "truncated VDEX 027 file header"
            )

        section_count = struct.unpack_from(
            "<I",
            content,
            8,
        )[0]

        if (
            section_count
            != self.VERSION_027_SECTION_COUNT
        ):
            raise AndroidVdexParsingError(
                "unexpected VDEX 027 section count: "
                f"{section_count}"
            )

        headers_end = (
            self.FILE_HEADER_SIZE
            + section_count
            * self.SECTION_HEADER_SIZE
        )

        if headers_end > len(
            content
        ):
            raise AndroidVdexParsingError(
                "truncated VDEX 027 section table"
            )

        sections = []

        for index in range(
            section_count
        ):
            base = (
                self.FILE_HEADER_SIZE
                + index
                * self.SECTION_HEADER_SIZE
            )

            kind, offset, size = (
                struct.unpack_from(
                    "<III",
                    content,
                    base,
                )
            )

            if (
                offset
                + size
                > len(
                    content
                )
            ):
                raise AndroidVdexParsingError(
                    "VDEX section exceeds source size: "
                    f"index={index} "
                    f"offset={offset} "
                    f"size={size}"
                )

            sections.append(
                ParsedAndroidVdexSection(
                    index=index,
                    kind=kind,
                    offset=offset,
                    size=size,
                )
            )

        checksum_section = sections[0]

        if checksum_section.kind != 0:
            raise AndroidVdexParsingError(
                "VDEX 027 checksum section is not first"
            )

        if (
            checksum_section.size
            % 4
        ) != 0:
            raise AndroidVdexParsingError(
                "VDEX checksum section size is not uint32 aligned"
            )

        dex_file_count = (
            checksum_section.size
            // 4
        )

        dex_checksums = tuple(
            struct.unpack_from(
                "<I",
                content,
                (
                    checksum_section.offset
                    + index * 4
                ),
            )[0]
            for index
            in range(
                dex_file_count
            )
        )

        dex_section = sections[1]

        if dex_section.kind != 1:
            raise AndroidVdexParsingError(
                "VDEX 027 DEX section is not second"
            )

        dex_files = []

        if dex_section.size != 0:
            if source.android_path is None:
                raise AndroidVdexParsingError(
                    "VDEX source lacks canonical Android path"
                )

            cursor = dex_section.offset
            section_end = (
                dex_section.offset
                + dex_section.size
            )

            for dex_index in range(
                dex_file_count
            ):
                if (
                    cursor
                    + AndroidDexParser.STANDARD_HEADER_SIZE
                    > section_end
                ):
                    raise AndroidVdexParsingError(
                        "VDEX DEX section is truncated before DEX "
                        f"index={dex_index}"
                    )

                magic = content[
                    cursor:
                    cursor + 8
                ]

                if not magic.startswith(
                    b"dex\n"
                ):
                    raise AndroidVdexParsingError(
                        "VDEX physical DEX section contains an "
                        "unsupported/non-standard DEX payload: "
                        f"index={dex_index} "
                        f"offset={cursor} "
                        f"magic={magic!r}"
                    )

                dex_file_size = struct.unpack_from(
                    "<I",
                    content,
                    cursor + 32,
                )[0]

                if (
                    dex_file_size
                    < AndroidDexParser.STANDARD_HEADER_SIZE
                ):
                    raise AndroidVdexParsingError(
                        "VDEX-contained DEX declares invalid file size: "
                        f"index={dex_index} "
                        f"size={dex_file_size}"
                    )

                dex_end = (
                    cursor
                    + dex_file_size
                )

                if dex_end > section_end:
                    raise AndroidVdexParsingError(
                        "VDEX-contained DEX exceeds physical DEX section: "
                        f"index={dex_index} "
                        f"offset={cursor} "
                        f"size={dex_file_size} "
                        f"section_end={section_end}"
                    )

                parsed_dex = AndroidDexParser().parse(
                    payload=content[
                        cursor:
                        dex_end
                    ],
                    source=AndroidDexSource(
                        kind=AndroidDexSourceKind.VDEX_CONTAINED,
                        parent=source,
                        parent_source_name=(
                            source.source_name
                        ),
                        parent_android_path=(
                            source.android_path
                        ),
                        embedded_offset=cursor,
                    ),
                )

                dex_files.append(
                    parsed_dex
                )

                cursor = (
                    dex_end
                    + 3
                ) & ~3

                if cursor > section_end:
                    raise AndroidVdexParsingError(
                        "VDEX DEX alignment exceeds physical section: "
                        f"index={dex_index}"
                    )

            if cursor != section_end:
                raise AndroidVdexParsingError(
                    "VDEX physical DEX section was not exactly consumed: "
                    f"consumed_end={cursor} "
                    f"section_end={section_end} "
                    f"dex_count={len(dex_files)}"
                )

        return ParsedAndroidVdex027(
            section_count=section_count,
            sections=tuple(
                sections
            ),
            dex_checksums=dex_checksums,
            dex_file_count=dex_file_count,
            has_dex_section=(
                dex_section.size
                != 0
            ),
            dex_files=tuple(
                dex_files
            ),
        )
