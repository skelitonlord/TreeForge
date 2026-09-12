from __future__ import annotations

import posixpath
from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
    normalize_metadata_path,
)
from treeforge.android.parsing.elf import (
    ParsedAndroidElf,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidFilesystemView,
    AndroidParserFilesystemSource,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfFilesystemAlias:
    """
    One canonical Android-visible filesystem alias for an exact parsed ELF.

    This is filesystem/ELF semantic reconciliation only.

    The alias preserves:
    - exact ParsedAndroidElf identity;
    - exact canonical symlink metadata identity;
    - exact canonical physical target metadata identity;
    - exact parser filesystem-view identity;
    - Android-visible alias path.

    ``alias_entry`` may be either:
    - a symlink whose final target is the physical ELF itself; or
    - a symlinked directory prefix through which the physical ELF is
      reachable.

    Directory-prefix aliases do not create synthetic filesystem metadata
    entries. The exact directory symlink remains the canonical witness while
    ``android_path`` identifies the descendant ELF path exposed through it.

    It does not assign a linker namespace, select a runtime provider, resolve
    DT_NEEDED, or create Reconstruction work.
    """

    source: ParsedAndroidElf
    alias_entry: FilesystemMetadataEntry
    target_entry: FilesystemMetadataEntry
    alias_filesystem_source: AndroidParserFilesystemSource
    filesystem_views: tuple[
        AndroidFilesystemView,
        ...,
    ]
    android_path: PurePosixPath

    @property
    def shares_source_filesystem(
        self,
    ) -> bool:
        """
        Whether this alias is projected from the ELF's own canonical
        filesystem source.

        Exact parser filesystem identities remain Universe provenance;
        downstream stages consume only this semantic relationship.
        """

        source_filesystem = (
            self.source
            .source
            .filesystem_source
        )

        if source_filesystem is None:
            raise ValueError(
                "filesystem alias requires a filesystem-backed ELF"
            )

        return (
            self.alias_filesystem_source
            is source_filesystem
        )

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
                "target_entry must preserve the exact parsed ELF "
                "metadata-entry identity"
            )

        filesystem_source = (
            self.source.source.filesystem_source
        )

        if filesystem_source is None:
            raise ValueError(
                "filesystem alias requires a filesystem-backed ELF"
            )

        if not isinstance(
            self.alias_filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "alias_filesystem_source must be an "
                "AndroidParserFilesystemSource"
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
            isinstance(
                view,
                AndroidFilesystemView,
            )
            for view
            in self.filesystem_views
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
                "filesystem_views must preserve exact parser-view identities"
            )

        if len(
            tuple(
                id(
                    view
                )
                for view
                in self.filesystem_views
            )
        ) != len(
            set(
                id(
                    view
                )
                for view
                in self.filesystem_views
            )
        ):
            raise ValueError(
                "filesystem_views must not repeat exact view identities"
            )

        if not isinstance(
            self.android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "android_path must be a PurePosixPath"
            )

        if not self.android_path.is_absolute():
            raise ValueError(
                "android_path must be absolute"
            )


class AndroidUniverseElfFilesystemAliasReconciler:
    """
    Reconcile canonical filesystem symlinks that resolve to one parsed ELF.

    Resolution is performed entirely from authoritative Filesystem Metadata.
    The materialized host filesystem is not queried and symlinks are not
    followed through pathlib/os APIs.
    """

    @staticmethod
    def _normalized_path(
        value: str,
    ) -> str:
        normalized = normalize_metadata_path(
            value
        )

        if not normalized.startswith(
            "/"
        ):
            normalized = (
                "/"
                + normalized
            )

        return normalized

    @classmethod
    def _target_path(
        cls,
        *,
        symlink_path: str,
        target: str,
    ) -> str:
        if target.startswith(
            "/"
        ):
            value = posixpath.normpath(
                target
            )

        else:
            value = posixpath.normpath(
                posixpath.join(
                    posixpath.dirname(
                        symlink_path
                    ),
                    target,
                )
            )

        return cls._normalized_path(
            value
        )

    @classmethod
    def _resolve_metadata_path(
        cls,
        *,
        entries: dict[
            str,
            FilesystemMetadataEntry,
        ],
        path: str,
    ) -> FilesystemMetadataEntry | None:
        """
        Resolve one filesystem-native path using canonical metadata only.

        Symlinks in intermediate path components are resolved as well as a
        symlink occupying the final path component.
        """

        current = cls._normalized_path(
            path
        )

        seen_symlinks: set[str] = set()

        while True:
            parts = tuple(
                part
                for part
                in PurePosixPath(
                    current
                ).parts
                if part != "/"
            )

            resolved_parts: list[str] = []
            redirected = False

            for index, part in enumerate(
                parts
            ):
                resolved_parts.append(
                    part
                )

                candidate_path = (
                    "/"
                    + "/".join(
                        resolved_parts
                    )
                )

                entry = entries.get(
                    candidate_path
                )

                if (
                    entry is None
                    or entry.entry_type
                    is not FilesystemEntryType.SYMLINK
                ):
                    continue

                if candidate_path in seen_symlinks:
                    return None

                seen_symlinks.add(
                    candidate_path
                )

                target = (
                    entry.symlink_target
                )

                if not target:
                    return None

                target_path = cls._target_path(
                    symlink_path=candidate_path,
                    target=target,
                )

                remaining = parts[
                    index + 1:
                ]

                if remaining:
                    target_path = cls._normalized_path(
                        posixpath.join(
                            target_path,
                            *remaining,
                        )
                    )

                current = target_path
                redirected = True
                break

            if redirected:
                continue

            return entries.get(
                current
            )

    @classmethod
    def _materialized_path_for_native_path(
        cls,
        *,
        filesystem_source,
        native_path: str,
    ):
        """
        Project one metadata-native path into canonical materialized storage.

        The supplied path does not need its own metadata entry. This is needed
        for a physical ELF exposed beneath a symlinked directory prefix, where
        the exact symlink metadata entry is the evidence but the descendant
        alias path is implicit in normal filesystem path traversal.

        This performs namespace projection only and never reads the host
        filesystem.
        """

        normalized = cls._normalized_path(
            native_path
        )

        parts = tuple(
            part
            for part
            in normalized.split(
                "/"
            )
            if part
        )

        return (
            filesystem_source
            .artifact
            .path
            .joinpath(
                *parts
            )
        )

    @staticmethod
    def _materialized_path(
        *,
        filesystem_source,
        metadata_entry: FilesystemMetadataEntry,
    ):
        """
        Project filesystem-native metadata identity into the canonical
        extracted filesystem namespace without reading the host filesystem.
        """

        return (
            AndroidUniverseElfFilesystemAliasReconciler
            ._materialized_path_for_native_path(
                filesystem_source=filesystem_source,
                native_path=metadata_entry.path,
            )
        )

    @classmethod
    def reconcile(
        cls,
        *,
        elf: ParsedAndroidElf,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> tuple[
        AndroidUniverseElfFilesystemAlias,
        ...,
    ]:
        if not isinstance(
            elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "elf must be a ParsedAndroidElf"
            )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        source = elf.source

        if not source.is_filesystem_backed:
            return ()

        filesystem_source = (
            source.filesystem_source
        )

        target_entry = (
            source.metadata_entry
        )

        assert filesystem_source is not None

        if target_entry is None:
            return ()

        try:
            inventory_entry = (
                filesystem_inventory
                .entry_for_artifact(
                    filesystem_source.artifact
                )
            )

        except KeyError:
            return ()

        entries = (
            inventory_entry
            .result
            .metadata
            .entries
        )

        if (
            entries.get(
                target_entry.path
            )
            is not target_entry
        ):
            raise ValueError(
                "parsed ELF metadata entry must preserve exact "
                "filesystem-inventory identity"
            )

        projections: dict[
            tuple[
                int,
                PurePosixPath,
            ],
            tuple[
                FilesystemMetadataEntry,
                list[
                    AndroidFilesystemView
                ],
            ],
        ] = {}

        for alias_entry in sorted(
            (
                entry
                for entry
                in entries.values()
                if (
                    entry.entry_type
                    is FilesystemEntryType.SYMLINK
                )
            ),
            key=lambda entry: (
                entry.path
            ),
        ):
            resolved = cls._resolve_metadata_path(
                entries=entries,
                path=alias_entry.path,
            )

            if resolved is None:
                continue

            if resolved is target_entry:
                alias_native_path = (
                    alias_entry.path
                )

            elif (
                resolved.entry_type
                is FilesystemEntryType.DIRECTORY
            ):
                resolved_directory = (
                    PurePosixPath(
                        cls._normalized_path(
                            resolved.path
                        )
                    )
                )

                target_path = (
                    PurePosixPath(
                        cls._normalized_path(
                            target_entry.path
                        )
                    )
                )

                try:
                    descendant = (
                        target_path.relative_to(
                            resolved_directory
                        )
                    )

                except ValueError:
                    continue

                if not descendant.parts:
                    continue

                alias_native_path = (
                    cls._normalized_path(
                        posixpath.join(
                            alias_entry.path,
                            descendant.as_posix(),
                        )
                    )
                )

                #
                # Permanent invariant:
                # the synthesized path through the exact symlink witness must
                # resolve back to this exact canonical ELF metadata entry.
                #
                if (
                    cls._resolve_metadata_path(
                        entries=entries,
                        path=alias_native_path,
                    )
                    is not target_entry
                ):
                    raise ValueError(
                        "directory-symlink ELF alias does not resolve "
                        "to its exact canonical target: "
                        f"elf={elf.source.identity_key!r}, "
                        f"alias={alias_native_path!r}, "
                        f"symlink={alias_entry.path!r}"
                    )

            else:
                continue

            alias_host_path = (
                cls._materialized_path_for_native_path(
                    filesystem_source=filesystem_source,
                    native_path=alias_native_path,
                )
            )

            for view in filesystem_source.views:
                try:
                    android_path = (
                        view.android_path_for(
                            alias_host_path
                        )
                    )

                except ValueError:
                    continue

                key = (
                    id(
                        alias_entry
                    ),
                    android_path,
                )

                projection = projections.get(
                    key
                )

                if projection is None:
                    projections[
                        key
                    ] = (
                        alias_entry,
                        [
                            view
                        ],
                    )
                    continue

                (
                    existing_alias_entry,
                    existing_views,
                ) = projection

                if existing_alias_entry is not alias_entry:
                    raise ValueError(
                        "ELF alias projection lost exact metadata identity"
                    )

                if not any(
                    candidate is view
                    for candidate
                    in existing_views
                ):
                    existing_views.append(
                        view
                    )

        values = tuple(
            sorted(
                (
                    AndroidUniverseElfFilesystemAlias(
                        source=elf,
                        alias_entry=alias_entry,
                        target_entry=target_entry,
                        alias_filesystem_source=filesystem_source,
                        filesystem_views=tuple(
                            sorted(
                                views,
                                key=lambda view: (
                                    view.android_prefix.as_posix(),
                                    view.filesystem.root.as_posix(),
                                ),
                            )
                        ),
                        android_path=android_path,
                    )
                    for (
                        _,
                        android_path,
                    ), (
                        alias_entry,
                        views,
                    )
                    in projections.items()
                ),
                key=lambda value: (
                    value.android_path.as_posix(),
                    value.alias_entry.path,
                ),
            )
        )

        by_android_path: dict[
            PurePosixPath,
            AndroidUniverseElfFilesystemAlias,
        ] = {}

        for value in values:
            existing = by_android_path.get(
                value.android_path
            )

            if existing is None:
                by_android_path[
                    value.android_path
                ] = value
                continue

            if (
                existing.alias_entry
                is value.alias_entry
            ):
                raise ValueError(
                    "identical ELF alias projection was not grouped"
                )

            raise ValueError(
                "distinct canonical filesystem aliases project to "
                "the same Android-visible path: "
                f"elf={elf.source.identity_key!r}, "
                f"android_path={value.android_path.as_posix()!r}, "
                f"aliases={(existing.alias_entry.path, value.alias_entry.path)!r}"
            )

        return values
