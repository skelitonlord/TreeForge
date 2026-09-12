from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.init.model import (
    AndroidInitImport,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitImportRequirement:
    """
    One canonical INIT import requirement.

    The exact parsed import declaration remains attached so its literal
    import expression, raw source text, source location, and Parsing identity
    remain lossless.

    This requirement records only that one canonical INIT source declares
    one import. Import-path expansion, target resolution, cross-source
    relationships, ambiguity, and applicability are later Universe concerns.
    """

    source_path: Path
    android_path: PurePosixPath | None
    filesystem_source: AndroidParserFilesystemSource | None
    declaration: AndroidInitImport

    @property
    def path(
        self,
    ) -> str:
        """
        Return the literal import path expression from Parsing.
        """

        return self.declaration.path

    @property
    def requirement_id(
        self,
    ) -> str:
        """
        Return deterministic Universe-local identity for this declaration.

        Source identity and declaration line remain part of the identity so
        repeated or equivalent imports from distinct sources never collapse.
        """

        source_identity = (
            android_universe_init_source_identity(
                source_path=self.source_path,
                android_path=self.android_path,
                filesystem_source=self.filesystem_source,
            )
        )

        return (
            f"init-import:{source_identity}:"
            f"{self.declaration.location.line}"
        )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if (
            self.filesystem_source is not None
            and not isinstance(
                self.filesystem_source,
                AndroidParserFilesystemSource,
            )
        ):
            raise TypeError(
                "filesystem_source must be an "
                "AndroidParserFilesystemSource or None"
            )

        if (
            self.android_path is not None
            and self.filesystem_source is None
        ):
            raise ValueError(
                "filesystem_source is required when "
                "android_path is present"
            )

        if not isinstance(
            self.declaration,
            AndroidInitImport,
        ):
            raise TypeError(
                "declaration must be an AndroidInitImport"
            )