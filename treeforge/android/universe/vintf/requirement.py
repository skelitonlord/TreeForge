from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidVintfSource,
)
from treeforge.android.parsing.vintf import (
    ParsedVintfDocument,
)
from treeforge.android.universe.vintf.document import (
    AndroidUniverseVintfDocumentSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfDocumentRequirement:
    """
    One canonical VINTF document requirement.

    The exact ParsedAndroidVintfSource and ParsedVintfDocument identities
    remain attached so Universe never loses Parsing provenance while adding
    Android semantic interpretation.
    """

    source: ParsedAndroidVintfSource

    semantics: (
        AndroidUniverseVintfDocumentSemantics
    )

    @property
    def source_path(
        self,
    ) -> Path:
        return self.source.source_path

    @property
    def android_path(
        self,
    ) -> PurePosixPath | None:
        return self.source.android_path

    @property
    def parsed(
        self,
    ) -> ParsedVintfDocument:
        return self.source.parsed

    @property
    def source_identity(
        self,
    ) -> tuple[
        str,
        str,
    ]:
        """
        Return the canonical Parsing filesystem-root and path identity.

        Android-visible paths are not globally unique across canonical
        filesystem sources, so Universe preserves the filesystem-root
        component established by Parsing.
        """

        return (
            self.source.filesystem_source.source_name,
            (
                self.android_path.as_posix()
                if self.android_path is not None
                else self.source_path.as_posix()
            ),
        )

    @property
    def requirement_id(
        self,
    ) -> str:
        (
            source_name,
            path_identity,
        ) = self.source_identity

        return (
            "vintf-document:"
            f"{source_name}:"
            f"{path_identity}:"
            f"{self.semantics.kind.value}:"
            f"{self.semantics.side.value}"
        )
