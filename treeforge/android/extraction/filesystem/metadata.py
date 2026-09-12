from __future__ import annotations

from dataclasses import dataclass



@dataclass(
    frozen=True,
    slots=True,
)
class Ext4FilesystemStructure:
    """
    Literal physical structure declared by the primary ext4 superblock.

    This model preserves filesystem-container evidence only. File traversal,
    Android policy, mount semantics, ownership, SELinux, and other filesystem
    semantics remain downstream responsibilities.
    """

    image_size: int

    superblock_offset: int
    superblock_size: int

    inode_count: int

    block_size: int
    block_count: int
    free_block_count: int
    free_inode_count: int

    first_data_block: int
    blocks_per_group: int
    inodes_per_group: int

    creator_os: int
    revision_level: int
    state: int
    errors_behavior: int

    inode_size: int
    descriptor_size: int

    feature_compat: int
    feature_incompat: int
    feature_ro_compat: int

    uuid: str
    volume_name: str

    def __post_init__(
        self,
    ) -> None:
        integer_fields = (
            ("image_size", self.image_size),
            (
                "superblock_offset",
                self.superblock_offset,
            ),
            (
                "superblock_size",
                self.superblock_size,
            ),
            ("inode_count", self.inode_count),
            ("block_size", self.block_size),
            ("block_count", self.block_count),
            (
                "free_block_count",
                self.free_block_count,
            ),
            (
                "free_inode_count",
                self.free_inode_count,
            ),
            (
                "first_data_block",
                self.first_data_block,
            ),
            (
                "blocks_per_group",
                self.blocks_per_group,
            ),
            (
                "inodes_per_group",
                self.inodes_per_group,
            ),
            ("creator_os", self.creator_os),
            (
                "revision_level",
                self.revision_level,
            ),
            ("state", self.state),
            (
                "errors_behavior",
                self.errors_behavior,
            ),
            ("inode_size", self.inode_size),
            (
                "descriptor_size",
                self.descriptor_size,
            ),
            (
                "feature_compat",
                self.feature_compat,
            ),
            (
                "feature_incompat",
                self.feature_incompat,
            ),
            (
                "feature_ro_compat",
                self.feature_ro_compat,
            ),
        )

        for name, value in integer_fields:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if self.superblock_offset != 1024:
            raise ValueError(
                "primary ext4 superblock offset must be 1024"
            )

        if self.superblock_size != 1024:
            raise ValueError(
                "ext4 superblock size must be 1024"
            )

        if self.block_size <= 0:
            raise ValueError(
                "block_size must be greater than zero"
            )

        if self.block_count <= 0:
            raise ValueError(
                "block_count must be greater than zero"
            )

        if self.filesystem_size_bytes > self.image_size:
            raise ValueError(
                "ext4 filesystem extent exceeds containing image"
            )

        if not isinstance(
            self.uuid,
            str,
        ):
            raise TypeError(
                "uuid must be a string"
            )

        if not isinstance(
            self.volume_name,
            str,
        ):
            raise TypeError(
                "volume_name must be a string"
            )

    @property
    def filesystem_size_bytes(
        self,
    ) -> int:
        return (
            self.block_size
            * self.block_count
        )
