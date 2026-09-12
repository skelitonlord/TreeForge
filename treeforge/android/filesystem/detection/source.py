from __future__ import annotations

from pathlib import Path
from typing import Protocol

from treeforge.android.filesystem.backends.manager import (
    FilesystemSourceType,
)
from treeforge.android.format.filesystem import (
    FilesystemDetector,
    FilesystemType,
)
from treeforge.android.format.image import (
    ImageFormat,
    ImageFormatDetector,
)

class ImageFormatDetectorLike(
    Protocol,
):
    def detect(
        self,
        source: Path,
    ) -> object:
        ...


class FilesystemDetectorLike(
    Protocol,
):
    def detect(
        self,
        source: Path,
    ) -> object:
        ...


class FilesystemSourceDetector:
    """
    Detect the storage format and contained filesystem of one source.

    Android sparse images are classified before filesystem-signature
    inspection because their contained raw filesystem is not directly
    visible until conversion.
    """

    def __init__(
        self,
        *,
        image_format_detector: (
            ImageFormatDetectorLike
            | None
        ) = None,
        filesystem_detector: (
            FilesystemDetectorLike
            | None
        ) = None,
    ) -> None:
        self._image_format_detector = (
            image_format_detector
            if image_format_detector is not None
            else ImageFormatDetector()
        )

        self._filesystem_detector = (
            filesystem_detector
            if filesystem_detector is not None
            else FilesystemDetector()
        )

    def detect(
        self,
        source: Path,
    ) -> FilesystemSourceType:
        """
        Detect one source as host, sparse ext4, raw ext4, EROFS, or unknown.
        """

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        image_format = (
            self._normalize_image_format(
                self._image_format_detector.detect(
                    source
                )
            )
        )

        if image_format is ImageFormat.HOST:
            return (
                FilesystemSourceType
                .HOST_DIRECTORY
            )

        if (
            image_format
            is ImageFormat.ANDROID_SPARSE
        ):
            return (
                FilesystemSourceType
                .SPARSE_EXT4
            )

        if image_format is not ImageFormat.RAW:
            return FilesystemSourceType.UNKNOWN

        filesystem_type = (
            self._normalize_filesystem_type(
                self._filesystem_detector.detect(
                    source
                )
            )
        )

        if filesystem_type is FilesystemType.EXT4:
            return FilesystemSourceType.RAW_EXT4

        if filesystem_type is FilesystemType.EROFS:
            return FilesystemSourceType.EROFS

        return FilesystemSourceType.UNKNOWN

    @staticmethod
    def _normalize_image_format(
        detected: object,
    ) -> ImageFormat:
        if isinstance(
            detected,
            ImageFormat,
        ):
            return detected

        value = getattr(
            detected,
            "value",
            detected,
        )

        if not isinstance(
            value,
            str,
        ):
            return ImageFormat.UNKNOWN

        try:
            return ImageFormat(
                value
            )
        except ValueError:
            return ImageFormat.UNKNOWN

    @staticmethod
    def _normalize_filesystem_type(
        detected: object,
    ) -> FilesystemType:
        if isinstance(
            detected,
            FilesystemType,
        ):
            return detected

        value = getattr(
            detected,
            "value",
            detected,
        )

        if not isinstance(
            value,
            str,
        ):
            return FilesystemType.UNKNOWN

        try:
            return FilesystemType(
                value
            )
        except ValueError:
            return FilesystemType.UNKNOWN