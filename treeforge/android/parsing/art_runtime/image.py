from __future__ import annotations

import struct

from treeforge.android.parsing.art_runtime.model import (
    ART_IMAGE_111_SECTION_KINDS,
    ParsedAndroidArtImage,
    ParsedAndroidArtImage111,
    ParsedAndroidArtImageSection,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)


class AndroidArtImageParsingError(
    ValueError,
):
    pass


class AndroidArtImageParser:
    MAGIC = b"art\n"
    VERSION_111 = b"111\x00"

    #
    # Version 111:
    #   magic/version                       0x00..0x07
    #   16 uint32 scalar fields            0x08..0x47
    #   13 ImageSection {offset,size}       0x48..0xaf
    #
    PREFIX_SIZE = 0x48
    SECTION_COUNT = 13
    SECTION_SIZE = 8
    MINIMUM_HEADER_SIZE = (
        PREFIX_SIZE
        + SECTION_COUNT
        * SECTION_SIZE
    )

    def parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidArtImage:
        content = source.host_path.read_bytes()

        if len(
            content
        ) < 8:
            raise AndroidArtImageParsingError(
                "truncated ART image identity header"
            )

        magic = content[:4]
        version = content[
            4:8
        ]

        if magic != self.MAGIC:
            raise AndroidArtImageParsingError(
                "invalid ART image magic"
            )

        if version != self.VERSION_111:
            return ParsedAndroidArtImage(
                source=source,
                magic=magic,
                version=version,
                layout_supported=False,
            )

        return ParsedAndroidArtImage(
            source=source,
            magic=magic,
            version=version,
            layout_supported=True,
            image_111=self._parse_111(
                content
            ),
        )

    def _parse_111(
        self,
        content: bytes,
    ) -> ParsedAndroidArtImage111:
        if len(
            content
        ) < self.MINIMUM_HEADER_SIZE:
            raise AndroidArtImageParsingError(
                "truncated ART image 111 structural header"
            )

        values = struct.unpack_from(
            "<16I",
            content,
            8,
        )

        (
            image_reservation_size,
            component_count,
            image_begin,
            image_size,
            image_checksum,
            oat_checksum,
            oat_file_begin,
            oat_data_begin,
            oat_data_end,
            oat_file_end,
            boot_image_begin,
            boot_image_size,
            boot_image_component_count,
            boot_image_checksum,
            image_roots,
            pointer_size,
        ) = values

        sections = []

        for index, kind in enumerate(
            ART_IMAGE_111_SECTION_KINDS
        ):
            base = (
                self.PREFIX_SIZE
                + index
                * self.SECTION_SIZE
            )

            offset, size = (
                struct.unpack_from(
                    "<II",
                    content,
                    base,
                )
            )

            sections.append(
                ParsedAndroidArtImageSection(
                    index=index,
                    kind=kind,
                    offset=offset,
                    size=size,
                )
            )

        return ParsedAndroidArtImage111(
            image_reservation_size=(
                image_reservation_size
            ),
            component_count=component_count,
            image_begin=image_begin,
            image_size=image_size,
            image_checksum=image_checksum,
            oat_checksum=oat_checksum,
            oat_file_begin=oat_file_begin,
            oat_data_begin=oat_data_begin,
            oat_data_end=oat_data_end,
            oat_file_end=oat_file_end,
            boot_image_begin=boot_image_begin,
            boot_image_size=boot_image_size,
            boot_image_component_count=(
                boot_image_component_count
            ),
            boot_image_checksum=(
                boot_image_checksum
            ),
            image_roots=image_roots,
            pointer_size=pointer_size,
            sections=tuple(
                sections
            ),
        )
