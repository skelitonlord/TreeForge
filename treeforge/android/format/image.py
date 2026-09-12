from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class ImageFormat(
    StrEnum,
):
    """
    Physical storage format of an Android source artifact.

    This describes how artifact bytes are physically represented, not the
    filesystem or higher-level content contained within them.
    """

    HOST = "host"
    RAW = "raw"
    ANDROID_SPARSE = "android_sparse"
    UNKNOWN = "unknown"


class ImageFormatDetector:
    """
    Detect the physical storage format of an Android source artifact.

    Android sparse detection is based only on the sparse-container magic and
    does not inspect or interpret the contained filesystem.
    """

    ANDROID_SPARSE_MAGIC = (
        0xED26FF3A
    )

    ANDROID_SPARSE_MAGIC_BYTES = (
        ANDROID_SPARSE_MAGIC.to_bytes(
            length=4,
            byteorder="little",
        )
    )

    @classmethod
    def detect(
        cls,
        source: Path,
    ) -> ImageFormat:
        """
        Detect whether a source is a host directory, raw file, Android sparse
        image, or an unsupported source kind.
        """

        source = Path(
            source
        )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if source.is_dir():
            return ImageFormat.HOST

        if not source.is_file():
            return ImageFormat.UNKNOWN

        if cls.is_android_sparse(
            source
        ):
            return (
                ImageFormat
                .ANDROID_SPARSE
            )

        return ImageFormat.RAW

    @classmethod
    def is_android_sparse(
        cls,
        source: Path,
    ) -> bool:
        """
        Return whether a file begins with Android sparse-image magic.
        """

        source = Path(
            source
        )

        if not source.is_file():
            return False

        try:
            with source.open(
                "rb"
            ) as image:
                magic = image.read(
                    len(
                        cls
                        .ANDROID_SPARSE_MAGIC_BYTES
                    )
                )

        except OSError:
            return False

        return (
            magic
            == cls.ANDROID_SPARSE_MAGIC_BYTES
        )