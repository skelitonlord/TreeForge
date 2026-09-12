from __future__ import annotations

from pathlib import Path
from uuid import UUID

from treeforge.android.extraction.filesystem.metadata import (
    Ext4FilesystemStructure,
)


class Ext4FilesystemStructureError(
    RuntimeError,
):
    pass


class Ext4FilesystemStructureDecoder:
    """
    Decode literal physical structure from the primary ext4 superblock.
    """

    SUPERBLOCK_OFFSET = 1024
    SUPERBLOCK_SIZE = 1024

    MAGIC_OFFSET = 0x38
    MAGIC = 0xEF53

    @staticmethod
    def _u16(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 2
            ],
            "little",
        )

    @staticmethod
    def _u32(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 4
            ],
            "little",
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

        if (
            not source.exists()
            or not source.is_file()
        ):
            return False

        if (
            source.stat().st_size
            < (
                self.SUPERBLOCK_OFFSET
                + self.SUPERBLOCK_SIZE
            )
        ):
            return False

        try:
            with source.open(
                "rb"
            ) as image:
                image.seek(
                    self.SUPERBLOCK_OFFSET
                    + self.MAGIC_OFFSET
                )

                raw = image.read(2)

        except OSError:
            return False

        return (
            len(raw) == 2
            and int.from_bytes(
                raw,
                "little",
            ) == self.MAGIC
        )

    def decode(
        self,
        source: Path,
    ) -> Ext4FilesystemStructure:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if not source.is_file():
            raise Ext4FilesystemStructureError(
                "ext4 source must be a regular file"
            )

        image_size = (
            source.stat().st_size
        )

        with source.open(
            "rb"
        ) as image:
            image.seek(
                self.SUPERBLOCK_OFFSET
            )

            superblock = image.read(
                self.SUPERBLOCK_SIZE
            )

        if (
            len(superblock)
            != self.SUPERBLOCK_SIZE
        ):
            raise Ext4FilesystemStructureError(
                "unable to read complete ext4 superblock"
            )

        magic = self._u16(
            superblock,
            self.MAGIC_OFFSET,
        )

        if magic != self.MAGIC:
            raise Ext4FilesystemStructureError(
                "ext4 superblock magic is missing"
            )

        log_block_size = self._u32(
            superblock,
            0x18,
        )

        block_size = (
            1
            << (
                10
                + log_block_size
            )
        )

        blocks_count_lo = self._u32(
            superblock,
            0x04,
        )

        blocks_count_hi = self._u32(
            superblock,
            0x150,
        )

        free_blocks_lo = self._u32(
            superblock,
            0x0C,
        )

        free_blocks_hi = self._u32(
            superblock,
            0x158,
        )

        block_count = (
            blocks_count_lo
            | (
                blocks_count_hi
                << 32
            )
        )

        free_block_count = (
            free_blocks_lo
            | (
                free_blocks_hi
                << 32
            )
        )

        uuid_raw = (
            superblock[
                0x68:0x78
            ]
        )

        volume_name_raw = (
            superblock[
                0x78:0x88
            ]
        )

        volume_name = (
            volume_name_raw
            .split(
                b"\0",
                1,
            )[0]
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        return Ext4FilesystemStructure(
            image_size=image_size,
            superblock_offset=(
                self.SUPERBLOCK_OFFSET
            ),
            superblock_size=(
                self.SUPERBLOCK_SIZE
            ),
            inode_count=self._u32(
                superblock,
                0x00,
            ),
            block_size=block_size,
            block_count=block_count,
            free_block_count=(
                free_block_count
            ),
            free_inode_count=self._u32(
                superblock,
                0x10,
            ),
            first_data_block=self._u32(
                superblock,
                0x14,
            ),
            blocks_per_group=self._u32(
                superblock,
                0x20,
            ),
            inodes_per_group=self._u32(
                superblock,
                0x28,
            ),
            creator_os=self._u32(
                superblock,
                0x48,
            ),
            revision_level=self._u32(
                superblock,
                0x4C,
            ),
            state=self._u16(
                superblock,
                0x3A,
            ),
            errors_behavior=self._u16(
                superblock,
                0x3C,
            ),
            inode_size=self._u16(
                superblock,
                0x58,
            ),
            descriptor_size=self._u16(
                superblock,
                0xFE,
            ),
            feature_compat=self._u32(
                superblock,
                0x5C,
            ),
            feature_incompat=self._u32(
                superblock,
                0x60,
            ),
            feature_ro_compat=self._u32(
                superblock,
                0x64,
            ),
            uuid=str(
                UUID(
                    bytes=uuid_raw
                )
            ),
            volume_name=volume_name,
        )
