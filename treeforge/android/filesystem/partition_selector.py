from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from treeforge.android.format.filesystem import (
    FilesystemDetector,
    FilesystemType,
)
from treeforge.android.format.image import (
    ImageFormat,
    ImageFormatDetector,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
    PartitionInventory,
)


class FilesystemPartitionSelectionError(
    RuntimeError,
):
    """Raised when filesystem partition selection fails."""


class FilesystemPartitionSkipReason(StrEnum):
    """Reason one accessible partition was not selected."""

    NON_FILESYSTEM_IMAGE = "non_filesystem_image"
    UNSUPPORTED_IMAGE_FORMAT = "unsupported_image_format"


@dataclass(
    frozen=True,
    slots=True,
)
class SkippedFilesystemPartition:
    """One partition excluded from filesystem metadata collection."""

    partition: InventoryPartition
    reason: FilesystemPartitionSkipReason


@dataclass(
    frozen=True,
    slots=True,
)
class FilesystemPartitionSelection:
    """Immutable result of filesystem partition selection."""

    inventory: PartitionInventory
    skipped: tuple[
        SkippedFilesystemPartition,
        ...,
    ] = ()

    @property
    def selected_names(
        self,
    ) -> tuple[str, ...]:
        """Return selected names in canonical inventory order."""

        return tuple(
            partition.name
            for partition in self.inventory.partitions
        )

    @property
    def skipped_names(
        self,
    ) -> tuple[str, ...]:
        """Return skipped names in canonical inventory order."""

        return tuple(
            skipped.partition.name
            for skipped in self.skipped
        )


class ImageFormatDetectorLike(Protocol):
    """Storage-format detector required by the selector."""

    def detect(
        self,
        source,
    ) -> object:
        """Detect the image storage format."""


class FilesystemDetectorLike(Protocol):
    """Filesystem-signature detector required by the selector."""

    def detect(
        self,
        source,
    ) -> object:
        """Detect the contained filesystem type."""


class FilesystemPartitionSelector:
    """
    Select partitions suitable for filesystem metadata collection.

    Selection rules:

    - only already-normalized raw filesystem images are eligible;
    - raw ext4 images are selected;
    - raw EROFS images are selected;
    - Android sparse images are rejected as incomplete Extraction output;
    - raw images with no recognized filesystem are skipped;
    - unsupported image formats are skipped.

    Exact InventoryPartition identities and source order are preserved.
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

    def select(
        self,
        inventory: PartitionInventory,
    ) -> FilesystemPartitionSelection:
        """Select filesystem-capable inventory partitions."""

        if not isinstance(
            inventory,
            PartitionInventory,
        ):
            raise TypeError(
                "inventory must be a PartitionInventory"
            )

        selected: list[
            InventoryPartition
        ] = []

        skipped: list[
            SkippedFilesystemPartition
        ] = []

        for partition in inventory.partitions:
            try:
                image_format = (
                    self._image_format_detector.detect(
                        partition.artifact.path,
                    )
                )
            except Exception as error:
                raise FilesystemPartitionSelectionError(
                    "Unable to detect image format for "
                    f"partition: {partition.name}"
                ) from error

            normalized_format = (
                self._normalize_image_format(
                    image_format,
                )
            )

            if (
                normalized_format
                is ImageFormat.ANDROID_SPARSE
            ):
                raise FilesystemPartitionSelectionError(
                    "Sparse partition reached filesystem metadata "
                    "selection after Extraction: "
                    f"{partition.name}"
                )

            if normalized_format is not ImageFormat.RAW:
                skipped.append(
                    SkippedFilesystemPartition(
                        partition=partition,
                        reason=(
                            FilesystemPartitionSkipReason
                            .UNSUPPORTED_IMAGE_FORMAT
                        ),
                    )
                )
                continue

            try:
                filesystem_type = (
                    self._filesystem_detector.detect(
                        partition.artifact.path,
                    )
                )
            except Exception as error:
                raise FilesystemPartitionSelectionError(
                    "Unable to detect filesystem type for "
                    f"partition: {partition.name}"
                ) from error

            normalized_filesystem = (
                self._normalize_filesystem_type(
                    filesystem_type,
                )
            )

            if normalized_filesystem in (
                FilesystemType.EXT4,
                FilesystemType.EROFS,
            ):
                selected.append(
                    partition,
                )
                continue

            skipped.append(
                SkippedFilesystemPartition(
                    partition=partition,
                    reason=(
                        FilesystemPartitionSkipReason
                        .NON_FILESYSTEM_IMAGE
                    ),
                )
            )

        return FilesystemPartitionSelection(
            inventory=PartitionInventory(
                partitions=tuple(
                    selected,
                ),
            ),
            skipped=tuple(
                skipped,
            ),
        )

    @staticmethod
    def _normalize_image_format(
        detected: object,
    ) -> ImageFormat:
        """Normalize detector output into ImageFormat."""

        if isinstance(
            detected,
            ImageFormat,
        ):
            return detected

        raw_value = getattr(
            detected,
            "value",
            detected,
        )

        if not isinstance(
            raw_value,
            str,
        ):
            return ImageFormat.UNKNOWN

        try:
            return ImageFormat(
                raw_value,
            )
        except ValueError:
            return ImageFormat.UNKNOWN

    @staticmethod
    def _normalize_filesystem_type(
        detected: object,
    ) -> FilesystemType:
        """Normalize detector output into FilesystemType."""

        if isinstance(
            detected,
            FilesystemType,
        ):
            return detected

        raw_value = getattr(
            detected,
            "value",
            detected,
        )

        if not isinstance(
            raw_value,
            str,
        ):
            return FilesystemType.UNKNOWN

        try:
            return FilesystemType(
                raw_value,
            )
        except ValueError:
            return FilesystemType.UNKNOWN