from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class FilesystemType(
    StrEnum,
):
    """
    Physical filesystem type detected from a source artifact.

    This describes the filesystem format present in a host directory or
    image. It does not perform filesystem traversal, metadata collection,
    or Android semantic interpretation.
    """

    HOST = "host"
    EXT4 = "ext4"
    EROFS = "erofs"
    UNKNOWN = "unknown"


class FilesystemDetector:
    """
    Detect the physical filesystem type of a directory or image.

    Detection uses filesystem signatures rather than filenames or
    extensions.
    """

    EXT4_MAGIC = b"\x53\xef"
    EXT4_MAGIC_OFFSET = (
        1024
        + 56
    )

    EROFS_MAGIC = (
        b"\xe2\xe1\xf5\xe0"
    )
    EROFS_MAGIC_OFFSET = 1024

    @classmethod
    def detect(
        cls,
        source: Path,
    ) -> FilesystemType:
        source = Path(
            source
        )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if source.is_dir():
            return FilesystemType.HOST

        if not source.is_file():
            return (
                FilesystemType.UNKNOWN
            )

        if cls._matches_magic(
            source=source,
            offset=(
                cls.EXT4_MAGIC_OFFSET
            ),
            magic=cls.EXT4_MAGIC,
        ):
            return FilesystemType.EXT4

        if cls._matches_magic(
            source=source,
            offset=(
                cls.EROFS_MAGIC_OFFSET
            ),
            magic=cls.EROFS_MAGIC,
        ):
            return FilesystemType.EROFS

        return FilesystemType.UNKNOWN

    @staticmethod
    def _matches_magic(
        source: Path,
        offset: int,
        magic: bytes,
    ) -> bool:
        """
        Return whether source contains magic at the requested byte offset.

        Images that are too small simply do not match.
        """

        try:
            with source.open(
                "rb"
            ) as image:
                image.seek(
                    offset
                )

                return (
                    image.read(
                        len(
                            magic
                        )
                    )
                    == magic
                )

        except OSError:
            return False