from __future__ import annotations

from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


def android_universe_init_source_identity(
    *,
    source_path: Path,
    android_path: PurePosixPath | None,
    filesystem_source: AndroidParserFilesystemSource | None,
) -> str:
    """
    Return stable physical-plus-Android identity for one INIT source.

    Parsing owns physical parser-source identity through
    AndroidParserFilesystemSource.source_name.  Android-visible path
    identity remains separate in android_path.

    Host source_path is retained only as the fallback for sources that
    have no canonical Android-visible identity.
    """

    if android_path is None:
        return source_path.as_posix()

    if filesystem_source is None:
        raise ValueError(
            "filesystem_source is required when android_path "
            "provides canonical Android INIT source identity"
        )

    return (
        f"{filesystem_source.source_name}:"
        f"{android_path.as_posix()}"
    )
