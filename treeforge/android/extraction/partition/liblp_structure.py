from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from struct import unpack_from


LP_METADATA_GEOMETRY_MAGIC = 0x616C4467
LP_METADATA_HEADER_MAGIC = 0x414C5030

LP_METADATA_GEOMETRY_SIZE = 4096
LP_PARTITION_RESERVED_BYTES = 4096

LP_PARTITION_ENTRY_SIZE = 52
LP_EXTENT_ENTRY_SIZE = 24
LP_GROUP_ENTRY_SIZE = 48
LP_BLOCK_DEVICE_ENTRY_SIZE = 64


class LiblpStructureDecodeError(ValueError):
    """
    Raised when literal Android liblp metadata cannot be decoded safely.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class LiblpPartitionRecord:
    name: str
    attributes: int
    first_extent_index: int
    num_extents: int
    group_index: int


@dataclass(
    frozen=True,
    slots=True,
)
class LiblpExtentRecord:
    num_sectors: int
    target_type: int
    target_data: int
    target_source: int


@dataclass(
    frozen=True,
    slots=True,
)
class LiblpGroupRecord:
    name: str
    flags: int
    maximum_size_bytes: int


@dataclass(
    frozen=True,
    slots=True,
)
class LiblpBlockDeviceRecord:
    first_logical_sector: int
    alignment_bytes: int
    alignment_offset_bytes: int
    size_bytes: int
    partition_name: str
    flags: int

    @property
    def first_logical_byte(self) -> int:
        return self.first_logical_sector * 512


@dataclass(
    frozen=True,
    slots=True,
)
class LiblpStructure:
    image_size_bytes: int

    geometry_offset_bytes: int
    geometry_struct_size_bytes: int
    geometry_checksum: str
    geometry_checksum_valid: bool
    metadata_max_size_bytes: int
    metadata_slot_count: int
    logical_block_size_bytes: int

    metadata_header_offset_bytes: int
    metadata_major_version: int
    metadata_minor_version: int
    metadata_header_size_bytes: int
    metadata_tables_size_bytes: int
    metadata_header_checksum: str
    metadata_header_checksum_valid: bool
    metadata_tables_checksum: str
    metadata_tables_checksum_valid: bool

    partition_table_offset_bytes: int
    partition_entry_size_bytes: int
    partitions: tuple[
        LiblpPartitionRecord,
        ...,
    ]

    extent_table_offset_bytes: int
    extent_entry_size_bytes: int
    extents: tuple[
        LiblpExtentRecord,
        ...,
    ]

    group_table_offset_bytes: int
    group_entry_size_bytes: int
    groups: tuple[
        LiblpGroupRecord,
        ...,
    ]

    block_device_table_offset_bytes: int
    block_device_entry_size_bytes: int
    block_devices: tuple[
        LiblpBlockDeviceRecord,
        ...,
    ]

    serialized_end_bytes: int

    @property
    def metadata_only_serialization(self) -> bool:
        return self.geometry_offset_bytes == 0

    @property
    def exactly_serialized_image(self) -> bool:
        return (
            self.metadata_only_serialization
            and self.serialized_end_bytes
            == self.image_size_bytes
        )


@dataclass(
    frozen=True,
    slots=True,
)
class _TableDescriptor:
    offset: int
    num_entries: int
    entry_size: int

    @property
    def size_bytes(self) -> int:
        return (
            self.num_entries
            * self.entry_size
        )


class LiblpStructureDecoder:
    """
    Decode literal on-disk Android liblp geometry and metadata.

    This decoder owns physical structure only. It does not infer Android
    partition-layout semantics, slot policy, mount behavior, reconstruction
    obligations, or payload ownership.

    Both forms used by Android are recognized:

    - metadata-only serialization:
        geometry at byte 0;
        metadata immediately after the 4096-byte geometry area;

    - full raw super container:
        reserved area at byte 0;
        primary geometry at byte 4096;
        backup geometry follows;
        primary metadata begins at byte 12288.

    Only metadata physically present in the supplied artifact is described.
    """

    _GEOMETRY_MAGIC = (
        LP_METADATA_GEOMETRY_MAGIC
    )

    _HEADER_MAGIC = (
        LP_METADATA_HEADER_MAGIC
    )

    def supports(
        self,
        source: Path,
    ) -> bool:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.is_file():
            return False

        try:
            self.decode(
                source
            )
        except (
            OSError,
            LiblpStructureDecodeError,
        ):
            return False

        return True

    def decode(
        self,
        source: Path,
    ) -> LiblpStructure:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                f"liblp source does not exist: "
                f"{source}"
            )

        if not source.is_file():
            raise LiblpStructureDecodeError(
                "liblp source must be a regular file: "
                f"{source}"
            )

        data = source.read_bytes()

        geometry_offset = (
            self._find_geometry_offset(
                data
            )
        )

        (
            geometry_struct_size,
            geometry_checksum,
            geometry_checksum_valid,
            metadata_max_size,
            metadata_slot_count,
            logical_block_size,
        ) = self._decode_geometry(
            data,
            geometry_offset,
        )

        metadata_offset = (
            self._metadata_offset(
                geometry_offset
            )
        )

        (
            major_version,
            minor_version,
            header_size,
            tables_size,
            header_checksum,
            header_checksum_valid,
            tables_checksum,
            tables_checksum_valid,
            partition_descriptor,
            extent_descriptor,
            group_descriptor,
            block_device_descriptor,
        ) = self._decode_header(
            data,
            metadata_offset,
        )

        tables_start = (
            metadata_offset
            + header_size
        )

        serialized_end = (
            tables_start
            + tables_size
        )

        if serialized_end > len(data):
            raise LiblpStructureDecodeError(
                "liblp metadata tables extend beyond "
                "the supplied artifact"
            )

        partitions = (
            self._decode_partitions(
                data=data,
                tables_start=tables_start,
                descriptor=partition_descriptor,
            )
        )

        extents = (
            self._decode_extents(
                data=data,
                tables_start=tables_start,
                descriptor=extent_descriptor,
            )
        )

        groups = (
            self._decode_groups(
                data=data,
                tables_start=tables_start,
                descriptor=group_descriptor,
            )
        )

        block_devices = (
            self._decode_block_devices(
                data=data,
                tables_start=tables_start,
                descriptor=block_device_descriptor,
            )
        )

        self._validate_references(
            partitions=partitions,
            extents=extents,
            groups=groups,
            block_devices=block_devices,
        )

        return LiblpStructure(
            image_size_bytes=len(data),
            geometry_offset_bytes=(
                geometry_offset
            ),
            geometry_struct_size_bytes=(
                geometry_struct_size
            ),
            geometry_checksum=(
                geometry_checksum
            ),
            geometry_checksum_valid=(
                geometry_checksum_valid
            ),
            metadata_max_size_bytes=(
                metadata_max_size
            ),
            metadata_slot_count=(
                metadata_slot_count
            ),
            logical_block_size_bytes=(
                logical_block_size
            ),
            metadata_header_offset_bytes=(
                metadata_offset
            ),
            metadata_major_version=(
                major_version
            ),
            metadata_minor_version=(
                minor_version
            ),
            metadata_header_size_bytes=(
                header_size
            ),
            metadata_tables_size_bytes=(
                tables_size
            ),
            metadata_header_checksum=(
                header_checksum
            ),
            metadata_header_checksum_valid=(
                header_checksum_valid
            ),
            metadata_tables_checksum=(
                tables_checksum
            ),
            metadata_tables_checksum_valid=(
                tables_checksum_valid
            ),
            partition_table_offset_bytes=(
                tables_start
                + partition_descriptor.offset
            ),
            partition_entry_size_bytes=(
                partition_descriptor.entry_size
            ),
            partitions=partitions,
            extent_table_offset_bytes=(
                tables_start
                + extent_descriptor.offset
            ),
            extent_entry_size_bytes=(
                extent_descriptor.entry_size
            ),
            extents=extents,
            group_table_offset_bytes=(
                tables_start
                + group_descriptor.offset
            ),
            group_entry_size_bytes=(
                group_descriptor.entry_size
            ),
            groups=groups,
            block_device_table_offset_bytes=(
                tables_start
                + block_device_descriptor.offset
            ),
            block_device_entry_size_bytes=(
                block_device_descriptor.entry_size
            ),
            block_devices=block_devices,
            serialized_end_bytes=(
                serialized_end
            ),
        )

    @classmethod
    def _find_geometry_offset(
        cls,
        data: bytes,
    ) -> int:
        for offset in (
            0,
            LP_PARTITION_RESERVED_BYTES,
        ):
            if (
                offset + 4
                > len(data)
            ):
                continue

            magic = unpack_from(
                "<I",
                data,
                offset,
            )[0]

            if (
                magic
                == cls._GEOMETRY_MAGIC
            ):
                return offset

        raise LiblpStructureDecodeError(
            "liblp geometry magic was not found"
        )

    @staticmethod
    def _metadata_offset(
        geometry_offset: int,
    ) -> int:
        if geometry_offset == 0:
            return (
                LP_METADATA_GEOMETRY_SIZE
            )

        if (
            geometry_offset
            == LP_PARTITION_RESERVED_BYTES
        ):
            return (
                LP_PARTITION_RESERVED_BYTES
                + (
                    LP_METADATA_GEOMETRY_SIZE
                    * 2
                )
            )

        raise LiblpStructureDecodeError(
            "unsupported liblp geometry offset: "
            f"{geometry_offset}"
        )

    @classmethod
    def _decode_geometry(
        cls,
        data: bytes,
        offset: int,
    ) -> tuple[
        int,
        str,
        bool,
        int,
        int,
        int,
    ]:
        minimum_size = 52

        if (
            offset + minimum_size
            > len(data)
        ):
            raise LiblpStructureDecodeError(
                "truncated liblp geometry"
            )

        magic = unpack_from(
            "<I",
            data,
            offset,
        )[0]

        if magic != cls._GEOMETRY_MAGIC:
            raise LiblpStructureDecodeError(
                "invalid liblp geometry magic"
            )

        struct_size = unpack_from(
            "<I",
            data,
            offset + 4,
        )[0]

        if (
            struct_size < minimum_size
            or offset + struct_size
            > len(data)
        ):
            raise LiblpStructureDecodeError(
                "invalid liblp geometry "
                f"struct size: {struct_size}"
            )

        stored_checksum = data[
            offset + 8:
            offset + 40
        ]

        checksum_input = bytearray(
            data[
                offset:
                offset + struct_size
            ]
        )

        checksum_input[
            8:40
        ] = b"\0" * 32

        computed_checksum = sha256(
            checksum_input
        ).digest()

        metadata_max_size = (
            unpack_from(
                "<I",
                data,
                offset + 40,
            )[0]
        )

        metadata_slot_count = (
            unpack_from(
                "<I",
                data,
                offset + 44,
            )[0]
        )

        logical_block_size = (
            unpack_from(
                "<I",
                data,
                offset + 48,
            )[0]
        )

        return (
            struct_size,
            stored_checksum.hex(),
            (
                stored_checksum
                == computed_checksum
            ),
            metadata_max_size,
            metadata_slot_count,
            logical_block_size,
        )

    @classmethod
    def _decode_header(
        cls,
        data: bytes,
        offset: int,
    ):
        minimum_size = 128

        if (
            offset + minimum_size
            > len(data)
        ):
            raise LiblpStructureDecodeError(
                "truncated liblp metadata header"
            )

        magic = unpack_from(
            "<I",
            data,
            offset,
        )[0]

        if magic != cls._HEADER_MAGIC:
            raise LiblpStructureDecodeError(
                "invalid liblp metadata header magic "
                f"at byte {offset}"
            )

        major_version = unpack_from(
            "<H",
            data,
            offset + 4,
        )[0]

        minor_version = unpack_from(
            "<H",
            data,
            offset + 6,
        )[0]

        header_size = unpack_from(
            "<I",
            data,
            offset + 8,
        )[0]

        if (
            header_size < minimum_size
            or offset + header_size
            > len(data)
        ):
            raise LiblpStructureDecodeError(
                "invalid liblp metadata header size: "
                f"{header_size}"
            )

        stored_header_checksum = data[
            offset + 12:
            offset + 44
        ]

        tables_size = unpack_from(
            "<I",
            data,
            offset + 44,
        )[0]

        stored_tables_checksum = data[
            offset + 48:
            offset + 80
        ]

        header_input = bytearray(
            data[
                offset:
                offset + header_size
            ]
        )

        header_input[
            12:44
        ] = b"\0" * 32

        computed_header_checksum = sha256(
            header_input
        ).digest()

        tables_start = (
            offset
            + header_size
        )

        tables_end = (
            tables_start
            + tables_size
        )

        if tables_end > len(data):
            raise LiblpStructureDecodeError(
                "liblp tables extend beyond "
                "the supplied artifact"
            )

        computed_tables_checksum = sha256(
            data[
                tables_start:
                tables_end
            ]
        ).digest()

        descriptors = tuple(
            cls._decode_descriptor(
                data,
                offset + 80 + index * 12,
            )
            for index in range(4)
        )

        for descriptor in descriptors:
            if (
                descriptor.offset
                + descriptor.size_bytes
                > tables_size
            ):
                raise LiblpStructureDecodeError(
                    "liblp table descriptor exceeds "
                    "declared tables size"
                )

        return (
            major_version,
            minor_version,
            header_size,
            tables_size,
            stored_header_checksum.hex(),
            (
                stored_header_checksum
                == computed_header_checksum
            ),
            stored_tables_checksum.hex(),
            (
                stored_tables_checksum
                == computed_tables_checksum
            ),
            descriptors[0],
            descriptors[1],
            descriptors[2],
            descriptors[3],
        )

    @staticmethod
    def _decode_descriptor(
        data: bytes,
        offset: int,
    ) -> _TableDescriptor:
        return _TableDescriptor(
            offset=unpack_from(
                "<I",
                data,
                offset,
            )[0],
            num_entries=unpack_from(
                "<I",
                data,
                offset + 4,
            )[0],
            entry_size=unpack_from(
                "<I",
                data,
                offset + 8,
            )[0],
        )

    @classmethod
    def _decode_partitions(
        cls,
        *,
        data: bytes,
        tables_start: int,
        descriptor: _TableDescriptor,
    ) -> tuple[
        LiblpPartitionRecord,
        ...,
    ]:
        cls._require_entry_size(
            "partition",
            descriptor,
            LP_PARTITION_ENTRY_SIZE,
        )

        records = []

        for index in range(
            descriptor.num_entries
        ):
            offset = (
                tables_start
                + descriptor.offset
                + index
                * descriptor.entry_size
            )

            records.append(
                LiblpPartitionRecord(
                    name=cls._decode_name(
                        data[
                            offset:
                            offset + 36
                        ]
                    ),
                    attributes=unpack_from(
                        "<I",
                        data,
                        offset + 36,
                    )[0],
                    first_extent_index=(
                        unpack_from(
                            "<I",
                            data,
                            offset + 40,
                        )[0]
                    ),
                    num_extents=unpack_from(
                        "<I",
                        data,
                        offset + 44,
                    )[0],
                    group_index=unpack_from(
                        "<I",
                        data,
                        offset + 48,
                    )[0],
                )
            )

        return tuple(
            records
        )

    @classmethod
    def _decode_extents(
        cls,
        *,
        data: bytes,
        tables_start: int,
        descriptor: _TableDescriptor,
    ) -> tuple[
        LiblpExtentRecord,
        ...,
    ]:
        cls._require_entry_size(
            "extent",
            descriptor,
            LP_EXTENT_ENTRY_SIZE,
        )

        records = []

        for index in range(
            descriptor.num_entries
        ):
            offset = (
                tables_start
                + descriptor.offset
                + index
                * descriptor.entry_size
            )

            records.append(
                LiblpExtentRecord(
                    num_sectors=unpack_from(
                        "<Q",
                        data,
                        offset,
                    )[0],
                    target_type=unpack_from(
                        "<I",
                        data,
                        offset + 8,
                    )[0],
                    target_data=unpack_from(
                        "<Q",
                        data,
                        offset + 12,
                    )[0],
                    target_source=unpack_from(
                        "<I",
                        data,
                        offset + 20,
                    )[0],
                )
            )

        return tuple(
            records
        )

    @classmethod
    def _decode_groups(
        cls,
        *,
        data: bytes,
        tables_start: int,
        descriptor: _TableDescriptor,
    ) -> tuple[
        LiblpGroupRecord,
        ...,
    ]:
        cls._require_entry_size(
            "group",
            descriptor,
            LP_GROUP_ENTRY_SIZE,
        )

        records = []

        for index in range(
            descriptor.num_entries
        ):
            offset = (
                tables_start
                + descriptor.offset
                + index
                * descriptor.entry_size
            )

            records.append(
                LiblpGroupRecord(
                    name=cls._decode_name(
                        data[
                            offset:
                            offset + 36
                        ]
                    ),
                    flags=unpack_from(
                        "<I",
                        data,
                        offset + 36,
                    )[0],
                    maximum_size_bytes=(
                        unpack_from(
                            "<Q",
                            data,
                            offset + 40,
                        )[0]
                    ),
                )
            )

        return tuple(
            records
        )

    @classmethod
    def _decode_block_devices(
        cls,
        *,
        data: bytes,
        tables_start: int,
        descriptor: _TableDescriptor,
    ) -> tuple[
        LiblpBlockDeviceRecord,
        ...,
    ]:
        cls._require_entry_size(
            "block device",
            descriptor,
            LP_BLOCK_DEVICE_ENTRY_SIZE,
        )

        records = []

        for index in range(
            descriptor.num_entries
        ):
            offset = (
                tables_start
                + descriptor.offset
                + index
                * descriptor.entry_size
            )

            records.append(
                LiblpBlockDeviceRecord(
                    first_logical_sector=(
                        unpack_from(
                            "<Q",
                            data,
                            offset,
                        )[0]
                    ),
                    alignment_bytes=(
                        unpack_from(
                            "<I",
                            data,
                            offset + 8,
                        )[0]
                    ),
                    alignment_offset_bytes=(
                        unpack_from(
                            "<I",
                            data,
                            offset + 12,
                        )[0]
                    ),
                    size_bytes=unpack_from(
                        "<Q",
                        data,
                        offset + 16,
                    )[0],
                    partition_name=(
                        cls._decode_name(
                            data[
                                offset + 24:
                                offset + 60
                            ]
                        )
                    ),
                    flags=unpack_from(
                        "<I",
                        data,
                        offset + 60,
                    )[0],
                )
            )

        return tuple(
            records
        )

    @staticmethod
    def _require_entry_size(
        name: str,
        descriptor: _TableDescriptor,
        minimum_size: int,
    ) -> None:
        if (
            descriptor.num_entries
            and descriptor.entry_size
            < minimum_size
        ):
            raise LiblpStructureDecodeError(
                f"liblp {name} entry size "
                f"{descriptor.entry_size} is smaller "
                f"than required {minimum_size}"
            )

    @staticmethod
    def _decode_name(
        raw: bytes,
    ) -> str:
        name_bytes = raw.split(
            b"\0",
            1,
        )[0]

        try:
            return name_bytes.decode(
                "ascii"
            )
        except UnicodeDecodeError as error:
            raise LiblpStructureDecodeError(
                "liblp record name is not ASCII"
            ) from error

    @staticmethod
    def _validate_references(
        *,
        partitions: tuple[
            LiblpPartitionRecord,
            ...,
        ],
        extents: tuple[
            LiblpExtentRecord,
            ...,
        ],
        groups: tuple[
            LiblpGroupRecord,
            ...,
        ],
        block_devices: tuple[
            LiblpBlockDeviceRecord,
            ...,
        ],
    ) -> None:
        for partition in partitions:
            extent_end = (
                partition.first_extent_index
                + partition.num_extents
            )

            if extent_end > len(extents):
                raise LiblpStructureDecodeError(
                    "liblp partition extent range "
                    "exceeds extent table: "
                    f"{partition.name}"
                )

            if (
                partition.group_index
                >= len(groups)
            ):
                raise LiblpStructureDecodeError(
                    "liblp partition references "
                    "missing group: "
                    f"{partition.name}"
                )

        for extent in extents:
            if (
                extent.target_type == 0
                and extent.target_source
                >= len(block_devices)
            ):
                raise LiblpStructureDecodeError(
                    "liblp linear extent references "
                    "missing block device"
                )
