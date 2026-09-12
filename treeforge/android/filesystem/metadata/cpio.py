from __future__ import annotations

import stat

from treeforge.android.extraction.cpio.extractor import (
    CpioEntryType,
    CpioExtractionResult,
)
from treeforge.android.filesystem.metadata.builder import (
    MetadataEntryProgressCallback,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadata,
    FilesystemMetadataEntry,
    normalize_metadata_path,
)


class CpioFilesystemMetadataNormalizer:
    """
    Normalize authoritative CPIO newc records into Filesystem Metadata.

    Extraction remains the owner of the original CpioNewcEntry records.
    This layer derives the generic FilesystemMetadata representation without
    rediscovering metadata from the materialized host directory.
    """

    def build(
        self,
        extraction: CpioExtractionResult,
        *,
        progress_callback: (
            MetadataEntryProgressCallback
            | None
        ) = None,
    ) -> FilesystemMetadata:
        if not isinstance(
            extraction,
            CpioExtractionResult,
        ):
            raise TypeError(
                "extraction must be a CpioExtractionResult"
            )

        artifact = extraction.artifact

        if artifact.parent is None:
            raise ValueError(
                "CPIO extraction artifact has no canonical archive parent"
            )

        entries: dict[
            str,
            FilesystemMetadataEntry,
        ] = {}

        processed = 0

        for source_entry in extraction.entries:
            path = normalize_metadata_path(
                source_entry.path
            )

            entry_type = FilesystemEntryType(
                source_entry.entry_type.value
            )

            device_major: int | None = None
            device_minor: int | None = None

            if source_entry.entry_type in {
                CpioEntryType.CHARACTER_DEVICE,
                CpioEntryType.BLOCK_DEVICE,
            }:
                device_major = (
                    source_entry.rdevmajor
                )
                device_minor = (
                    source_entry.rdevminor
                )

            entry = FilesystemMetadataEntry(
                path=path,
                entry_type=entry_type,
                mode=stat.S_IMODE(
                    source_entry.mode
                ),
                uid=source_entry.uid,
                gid=source_entry.gid,
                size=source_entry.filesize,
                inode=source_entry.ino,
                link_count=source_entry.nlink,
                symlink_target=(
                    source_entry.symlink_target
                ),
                device_major=device_major,
                device_minor=device_minor,
                xattrs={},
            )

            #
            # CPIO archives may legally repeat a path. Extraction applies
            # entries in archive order, so the last record determines the
            # final materialized filesystem state. Mirror that behavior here
            # while preserving every original record in CpioExtractionResult.
            #
            entries[
                path
            ] = entry

            processed += 1

            if progress_callback is not None:
                progress_callback(
                    path,
                    processed,
                )

        return FilesystemMetadata(
            filesystem_type="cpio_newc",
            source=artifact.parent.path,
            entries=entries,
        )
