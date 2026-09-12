from __future__ import annotations

from pathlib import Path

from treeforge.core.binary import (
    align_up,
    read_uint32_le,
    read_uint64_le,
)
from treeforge.android.extraction.boot.metadata import (
    BootComponentLayout,
    VendorBootImageStructure,
    VendorRamdiskTableEntry,
)


class VendorBootImageStructureDecodeError(
    RuntimeError,
):
    """
    Raised when a VNDRBOOT image cannot be structurally decoded.
    """


class VendorBootImageStructureDecoder:
    """
    Decode the physical structure of Android vendor_boot images.

    Supported header versions:

    - v3
    - v4

    The declared header version inside the image selects the exact
    structural interpretation. No Android-version policy, filename
    inference, parser-layer metadata, or fallback guessing is used.

    This decoder owns only physical facts required by Extraction:

    - header version;
    - header size;
    - page size;
    - aggregate vendor ramdisk range;
    - DTB range;
    - v4 vendor ramdisk table range;
    - v4 bootconfig range.

    Semantic interpretation of vendor ramdisk table entries and
    bootconfig contents remains deferred.
    """

    VENDOR_BOOT_MAGIC = (
        b"VNDRBOOT"
    )

    MAGIC_SIZE = 8

    HEADER_VERSION_OFFSET = 8
    PAGE_SIZE_OFFSET = 12

    KERNEL_ADDR_OFFSET = 16
    RAMDISK_ADDR_OFFSET = 20

    VENDOR_RAMDISK_SIZE_OFFSET = 24

    CMDLINE_OFFSET = 28
    CMDLINE_SIZE = 2048

    TAGS_ADDR_OFFSET = 2076

    NAME_OFFSET = 2080
    NAME_SIZE = 16

    HEADER_SIZE_OFFSET = 2096
    DTB_SIZE_OFFSET = 2100
    DTB_ADDR_OFFSET = 2104

    #
    # vendor_boot v3 ends before the following fields.
    #
    V3_STRUCT_SIZE = 2112

    #
    # vendor_boot v4 extension.
    #
    V4_RAMDISK_TABLE_SIZE_OFFSET = 2112
    V4_RAMDISK_TABLE_ENTRY_NUM_OFFSET = 2116
    V4_RAMDISK_TABLE_ENTRY_SIZE_OFFSET = 2120
    V4_BOOTCONFIG_SIZE_OFFSET = 2124

    V4_STRUCT_SIZE = 2128

    V4_RAMDISK_ENTRY_MIN_SIZE = 108

    V4_ENTRY_RAMDISK_SIZE_OFFSET = 0
    V4_ENTRY_RAMDISK_OFFSET_OFFSET = 4
    V4_ENTRY_RAMDISK_TYPE_OFFSET = 8

    V4_ENTRY_NAME_OFFSET = 12
    V4_ENTRY_NAME_SIZE = 32

    V4_ENTRY_BOARD_ID_OFFSET = 44
    V4_ENTRY_BOARD_ID_WORDS = 16

    HEADER_READ_SIZE = 4096

    SUPPORTED_HEADER_VERSIONS = (
        3,
        4,
    )

    def decode(
        self,
        image_path: Path,
    ) -> VendorBootImageStructure:
        """
        Decode one VNDRBOOT image into immutable Extraction structure.
        """

        image_path = (
            self._validate_image_path(
                image_path
            )
        )

        image_size = (
            image_path.stat().st_size
        )

        with image_path.open(
            "rb",
        ) as handle:
            header = handle.read(
                self.HEADER_READ_SIZE
            )

        self._validate_magic(
            header
        )

        header_version = (
            read_uint32_le(
                header,
                self.HEADER_VERSION_OFFSET,
            )
        )

        if (
            header_version
            not in self.SUPPORTED_HEADER_VERSIONS
        ):
            raise VendorBootImageStructureDecodeError(
                "Unsupported vendor_boot header version: "
                f"{header_version}"
            )

        if header_version == 3:
            return self._decode_v3(
                header,
                image_size=image_size,
            )

        return self._decode_v4(
            header,
            image_path=image_path,
            image_size=image_size,
        )

    def _decode_v3(
        self,
        header: bytes,
        *,
        image_size: int,
    ) -> VendorBootImageStructure:
        """
        Decode vendor_boot header version 3.
        """

        common = (
            self._decode_common(
                header,
                image_size=image_size,
                header_version=3,
            )
        )

        return VendorBootImageStructure(
            header_version=3,
            header_size=(
                common["header_size"]
            ),
            page_size=(
                common["page_size"]
            ),
            kernel_addr=common["kernel_addr"],
            ramdisk_addr=common["ramdisk_addr"],
            tags_addr=common["tags_addr"],
            dtb_addr=common["dtb_addr"],
            cmdline=common["cmdline"],
            name=common["name"],
            vendor_ramdisk=(
                common["vendor_ramdisk"]
            ),
            dtb=(
                common["dtb"]
            ),
            vendor_ramdisk_table=(
                BootComponentLayout(
                    offset=0,
                    size=0,
                )
            ),
            bootconfig=(
                BootComponentLayout(
                    offset=0,
                    size=0,
                )
            ),
            vendor_ramdisk_table_entry_num=0,
            vendor_ramdisk_table_entry_size=0,
            vendor_ramdisk_table_entries=(),
            image_size=image_size,
        )

    def _decode_v4(
        self,
        header: bytes,
        *,
        image_path: Path,
        image_size: int,
    ) -> VendorBootImageStructure:
        """
        Decode vendor_boot header version 4.
        """

        common = (
            self._decode_common(
                header,
                image_size=image_size,
                header_version=4,
            )
        )

        page_size = (
            common["page_size"]
        )

        dtb = (
            common["dtb"]
        )

        vendor_ramdisk_table_size = (
            read_uint32_le(
                header,
                self.V4_RAMDISK_TABLE_SIZE_OFFSET,
            )
        )

        vendor_ramdisk_table_entry_num = (
            read_uint32_le(
                header,
                self.V4_RAMDISK_TABLE_ENTRY_NUM_OFFSET,
            )
        )

        vendor_ramdisk_table_entry_size = (
            read_uint32_le(
                header,
                self.V4_RAMDISK_TABLE_ENTRY_SIZE_OFFSET,
            )
        )

        bootconfig_size = (
            read_uint32_le(
                header,
                self.V4_BOOTCONFIG_SIZE_OFFSET,
            )
        )

        #
        # The table begins at the next page after the DTB region.
        #
        vendor_ramdisk_table_offset = (
            align_up(
                dtb.end,
                page_size,
            )
        )

        vendor_ramdisk_table = (
            BootComponentLayout(
                offset=(
                    vendor_ramdisk_table_offset
                ),
                size=(
                    vendor_ramdisk_table_size
                ),
            )
        )

        #
        # bootconfig follows the table at the next page boundary.
        #
        bootconfig_offset = (
            align_up(
                vendor_ramdisk_table.end,
                page_size,
            )
        )

        bootconfig = (
            BootComponentLayout(
                offset=bootconfig_offset,
                size=bootconfig_size,
            )
        )

        if (
            vendor_ramdisk_table_entry_num
            and vendor_ramdisk_table_entry_size
            < self.V4_RAMDISK_ENTRY_MIN_SIZE
        ):
            raise VendorBootImageStructureDecodeError(
                "vendor_boot v4 ramdisk table entry size is smaller "
                f"than {self.V4_RAMDISK_ENTRY_MIN_SIZE}: "
                f"{vendor_ramdisk_table_entry_size}"
            )

        expected_table_size = (
            vendor_ramdisk_table_entry_num
            * vendor_ramdisk_table_entry_size
        )

        if (
            expected_table_size
            > vendor_ramdisk_table_size
        ):
            raise VendorBootImageStructureDecodeError(
                "vendor_boot v4 ramdisk table entries exceed "
                "the declared table size"
            )

        table_entries: list[
            VendorRamdiskTableEntry
        ] = []

        if vendor_ramdisk_table_entry_num:
            with image_path.open(
                "rb"
            ) as image:
                image.seek(
                    vendor_ramdisk_table_offset
                )

                table_data = image.read(
                    vendor_ramdisk_table_size
                )

            if (
                len(table_data)
                != vendor_ramdisk_table_size
            ):
                raise VendorBootImageStructureDecodeError(
                    "unable to read complete vendor ramdisk table"
                )

            for index in range(
                vendor_ramdisk_table_entry_num
            ):
                start = (
                    index
                    * vendor_ramdisk_table_entry_size
                )

                entry = table_data[
                    start:
                    (
                        start
                        + vendor_ramdisk_table_entry_size
                    )
                ]

                ramdisk_size = read_uint32_le(
                    entry,
                    self.V4_ENTRY_RAMDISK_SIZE_OFFSET,
                )

                ramdisk_offset = read_uint32_le(
                    entry,
                    self.V4_ENTRY_RAMDISK_OFFSET_OFFSET,
                )

                ramdisk_type = read_uint32_le(
                    entry,
                    self.V4_ENTRY_RAMDISK_TYPE_OFFSET,
                )

                ramdisk_name = self._decode_c_string(
                    entry[
                        self.V4_ENTRY_NAME_OFFSET:
                        (
                            self.V4_ENTRY_NAME_OFFSET
                            + self.V4_ENTRY_NAME_SIZE
                        )
                    ]
                )

                board_id = tuple(
                    read_uint32_le(
                        entry,
                        (
                            self.V4_ENTRY_BOARD_ID_OFFSET
                            + word_index * 4
                        ),
                    )
                    for word_index
                    in range(
                        self.V4_ENTRY_BOARD_ID_WORDS
                    )
                )

                if (
                    ramdisk_offset
                    + ramdisk_size
                    > common[
                        "vendor_ramdisk"
                    ].size
                ):
                    raise VendorBootImageStructureDecodeError(
                        "vendor ramdisk table entry extends beyond "
                        "the aggregate vendor ramdisk section: "
                        f"index={index}"
                    )

                table_entries.append(
                    VendorRamdiskTableEntry(
                        index=index,
                        ramdisk_size=ramdisk_size,
                        ramdisk_offset=ramdisk_offset,
                        ramdisk_type=ramdisk_type,
                        ramdisk_name=ramdisk_name,
                        board_id=board_id,
                    )
                )

        return VendorBootImageStructure(
            header_version=4,
            header_size=(
                common["header_size"]
            ),
            page_size=page_size,
            kernel_addr=common["kernel_addr"],
            ramdisk_addr=common["ramdisk_addr"],
            tags_addr=common["tags_addr"],
            dtb_addr=common["dtb_addr"],
            cmdline=common["cmdline"],
            name=common["name"],
            vendor_ramdisk=(
                common["vendor_ramdisk"]
            ),
            dtb=dtb,
            vendor_ramdisk_table=(
                vendor_ramdisk_table
            ),
            bootconfig=bootconfig,
            vendor_ramdisk_table_entry_num=(
                vendor_ramdisk_table_entry_num
            ),
            vendor_ramdisk_table_entry_size=(
                vendor_ramdisk_table_entry_size
            ),
            vendor_ramdisk_table_entries=(
                tuple(
                    table_entries
                )
            ),
            image_size=image_size,
        )

    def _decode_common(
        self,
        header: bytes,
        *,
        image_size: int,
        header_version: int,
    ) -> dict[
        str,
        int | BootComponentLayout,
    ]:
        """
        Decode the physical fields shared by vendor_boot v3 and v4.
        """

        page_size = (
            read_uint32_le(
                header,
                self.PAGE_SIZE_OFFSET,
            )
        )

        if page_size <= 0:
            raise VendorBootImageStructureDecodeError(
                "vendor_boot declares an invalid "
                f"page size: {page_size}"
            )

        header_size = (
            read_uint32_le(
                header,
                self.HEADER_SIZE_OFFSET,
            )
        )

        minimum_header_size = (
            self.V4_STRUCT_SIZE
            if header_version == 4
            else self.V3_STRUCT_SIZE
        )

        if (
            header_size
            < minimum_header_size
        ):
            raise VendorBootImageStructureDecodeError(
                f"vendor_boot v{header_version} "
                "declares an invalid header size: "
                f"{header_size}"
            )

        kernel_addr = read_uint32_le(
            header,
            self.KERNEL_ADDR_OFFSET,
        )

        ramdisk_addr = read_uint32_le(
            header,
            self.RAMDISK_ADDR_OFFSET,
        )

        vendor_ramdisk_size = (
            read_uint32_le(
                header,
                self.VENDOR_RAMDISK_SIZE_OFFSET,
            )
        )

        cmdline = self._decode_c_string(
            header[
                self.CMDLINE_OFFSET:
                (
                    self.CMDLINE_OFFSET
                    + self.CMDLINE_SIZE
                )
            ]
        )

        tags_addr = read_uint32_le(
            header,
            self.TAGS_ADDR_OFFSET,
        )

        name = self._decode_c_string(
            header[
                self.NAME_OFFSET:
                (
                    self.NAME_OFFSET
                    + self.NAME_SIZE
                )
            ]
        )

        dtb_size = (
            read_uint32_le(
                header,
                self.DTB_SIZE_OFFSET,
            )
        )

        dtb_addr = read_uint64_le(
            header,
            self.DTB_ADDR_OFFSET,
        )

        #
        # The physical vendor ramdisk begins after the header region,
        # aligned to the image-declared vendor_boot page size.
        #
        vendor_ramdisk_offset = (
            align_up(
                header_size,
                page_size,
            )
        )

        vendor_ramdisk = (
            BootComponentLayout(
                offset=vendor_ramdisk_offset,
                size=vendor_ramdisk_size,
            )
        )

        #
        # The DTB region follows the vendor ramdisk at the next page
        # boundary. Retain its physical offset even when dtb_size == 0
        # because v4 places the ramdisk table relative to the end of
        # this region.
        #
        dtb_offset = (
            align_up(
                vendor_ramdisk.end,
                page_size,
            )
        )

        dtb = (
            BootComponentLayout(
                offset=dtb_offset,
                size=dtb_size,
            )
        )

        if (
            vendor_ramdisk.end
            > image_size
        ):
            raise VendorBootImageStructureDecodeError(
                "vendor_boot ramdisk extends beyond image: "
                f"offset={vendor_ramdisk.offset}, "
                f"size={vendor_ramdisk.size}, "
                f"end={vendor_ramdisk.end}, "
                f"image_size={image_size}"
            )

        if (
            dtb.present
            and dtb.end
            > image_size
        ):
            raise VendorBootImageStructureDecodeError(
                "vendor_boot DTB extends beyond image: "
                f"offset={dtb.offset}, "
                f"size={dtb.size}, "
                f"end={dtb.end}, "
                f"image_size={image_size}"
            )

        return {
            "page_size": page_size,
            "header_size": header_size,
            "kernel_addr": kernel_addr,
            "ramdisk_addr": ramdisk_addr,
            "tags_addr": tags_addr,
            "dtb_addr": dtb_addr,
            "cmdline": cmdline,
            "name": name,
            "vendor_ramdisk": (
                vendor_ramdisk
            ),
            "dtb": dtb,
        }

    @staticmethod
    def _decode_c_string(
        value: bytes,
    ) -> str:
        raw = value.split(
            b"\x00",
            1,
        )[0]

        return raw.decode(
            "utf-8",
            errors="surrogateescape",
        )

    def _validate_magic(
        self,
        header: bytes,
    ) -> None:
        if (
            len(header)
            < self.MAGIC_SIZE
        ):
            raise VendorBootImageStructureDecodeError(
                "vendor_boot image is too small "
                "to contain VNDRBOOT magic"
            )

        if (
            header[
                0:
                self.MAGIC_SIZE
            ]
            != self.VENDOR_BOOT_MAGIC
        ):
            raise VendorBootImageStructureDecodeError(
                "Invalid vendor_boot magic"
            )

    @staticmethod
    def _validate_image_path(
        image_path: Path,
    ) -> Path:
        if not isinstance(
            image_path,
            Path,
        ):
            raise TypeError(
                "image_path must be a pathlib.Path"
            )

        normalized = (
            image_path
            .expanduser()
            .resolve()
        )

        if not normalized.exists():
            raise FileNotFoundError(
                normalized
            )

        if not normalized.is_file():
            raise VendorBootImageStructureDecodeError(
                "vendor_boot image must be a "
                f"regular file: {normalized}"
            )

        if (
            normalized.stat().st_size
            <= 0
        ):
            raise VendorBootImageStructureDecodeError(
                "vendor_boot image cannot be empty: "
                f"{normalized}"
            )

        return normalized