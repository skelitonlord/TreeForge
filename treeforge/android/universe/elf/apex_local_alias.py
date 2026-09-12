from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
)
from treeforge.android.parsing.elf import (
    ParsedAndroidElf,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidFilesystemView,
    AndroidParserFilesystemSource,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfApexLocalAlias:
    """
    One canonical APEX-payload-local filesystem alias for an exact ELF.

    Example semantic shape:

        client APEX payload:
            /lib64/libbase.so -> /system/lib64/libbase.so

        target:
            exact ParsedAndroidElf for /system/lib64/libbase.so

    Universe owns the exact package/filesystem/ELF relationship only.
    ``payload_path`` deliberately remains relative to the canonical APEX
    payload namespace. Runtime Linking owns projection beneath the selected
    active APEX runtime root.

    This model does not:
    - select an active APEX version;
    - synthesize /apex/<name>;
    - assign linker namespaces;
    - resolve DT_NEEDED;
    - create Reconstruction work.
    """

    source: ParsedAndroidElf
    client_apex_requirement: AndroidUniverseApexRequirement

    alias_entry: FilesystemMetadataEntry
    target_entry: FilesystemMetadataEntry

    alias_filesystem_source: AndroidParserFilesystemSource
    filesystem_views: tuple[
        AndroidFilesystemView,
        ...,
    ]

    payload_path: PurePosixPath
    target_android_path: PurePosixPath

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.client_apex_requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "client_apex_requirement must be an "
                "AndroidUniverseApexRequirement"
            )

        if not isinstance(
            self.alias_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "alias_entry must be a FilesystemMetadataEntry"
            )

        if (
            self.alias_entry.entry_type
            is not FilesystemEntryType.SYMLINK
        ):
            raise ValueError(
                "alias_entry must be a canonical symlink entry"
            )

        if not isinstance(
            self.target_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "target_entry must be a FilesystemMetadataEntry"
            )

        if (
            self.target_entry.entry_type
            is not FilesystemEntryType.FILE
        ):
            raise ValueError(
                "target_entry must be a canonical regular-file entry"
            )

        if (
            self.source.source.metadata_entry
            is not self.target_entry
        ):
            raise ValueError(
                "target_entry must preserve exact target ELF "
                "metadata identity"
            )

        if not isinstance(
            self.alias_filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "alias_filesystem_source must be an "
                "AndroidParserFilesystemSource"
            )

        target_filesystem_source = (
            self.source.source.filesystem_source
        )

        if target_filesystem_source is None:
            raise ValueError(
                "APEX-local alias target must be filesystem-backed"
            )

        if (
            target_filesystem_source
            is self.alias_filesystem_source
        ):
            raise ValueError(
                "APEX-local alias must cross filesystem boundaries"
            )

        if not isinstance(
            self.filesystem_views,
            tuple,
        ):
            raise TypeError(
                "filesystem_views must be a tuple"
            )

        if not self.filesystem_views:
            raise ValueError(
                "filesystem_views must not be empty"
            )

        if not all(
            isinstance(view, AndroidFilesystemView)
            for view in self.filesystem_views
        ):
            raise TypeError(
                "filesystem_views must contain only "
                "AndroidFilesystemView values"
            )

        if not all(
            any(
                candidate is view
                for candidate
                in self.alias_filesystem_source.views
            )
            for view
            in self.filesystem_views
        ):
            raise ValueError(
                "filesystem_views must preserve exact "
                "alias-filesystem view identities"
            )

        for name, value in (
            (
                "payload_path",
                self.payload_path,
            ),
            (
                "target_android_path",
                self.target_android_path,
            ),
        ):
            if not isinstance(
                value,
                PurePosixPath,
            ):
                raise TypeError(
                    f"{name} must be a PurePosixPath"
                )

            if not value.is_absolute():
                raise ValueError(
                    f"{name} must be absolute"
                )
