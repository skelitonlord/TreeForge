from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidUeventd,
)
from treeforge.android.parsing.ueventd.model import (
    AndroidUeventdUnparsedLine,
)


@dataclass(frozen=True, slots=True)
class AndroidUniverseUeventdSourceContext:
    """
    Exact source-level lexical context for one canonical UEVENTD source.

    UEVENTD semantic requirements remain owned by Android Device Universe.

    This context preserves source text and meaningful unparsed lexical
    evidence that does not become a semantic requirement. It exists so
    downstream Reconstruction can render admitted requirements without
    reaching backward into Parsing or inventing requirements for opaque
    source lines.

    No source-tree ownership, destination, filename, build-module, semantic
    reconciliation, rendering, or materialization decision is made here.
    """

    source_path: Path
    android_path: PurePosixPath | None

    # Preserve the canonical Parsing filesystem-root identity. Android paths
    # alone are not globally unique because the same Android-visible path may
    # legitimately exist in more than one canonical filesystem source.
    source_name: str

    raw: str

    unparsed_lines: tuple[
        AndroidUeventdUnparsedLine,
        ...,
    ] = ()

    @property
    def source_identity(
        self,
    ) -> tuple[
        str,
        str,
    ]:
        return (
            self.source_name,
            (
                self.android_path.as_posix()
                if self.android_path is not None
                else self.source_path.as_posix()
            ),
        )

    @classmethod
    def from_parsed(
        cls,
        source: ParsedAndroidUeventd,
    ) -> "AndroidUniverseUeventdSourceContext":
        if not isinstance(
            source,
            ParsedAndroidUeventd,
        ):
            raise TypeError(
                "source must be a ParsedAndroidUeventd"
            )

        return cls(
            source_path=source.source_path,
            android_path=source.android_path,
            source_name=source.filesystem_source.source_name,
            raw=source.raw,
            unparsed_lines=source.unparsed_lines,
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
            not isinstance(
                self.source_name,
                str,
            )
            or not self.source_name.strip()
        ):
            raise ValueError(
                "source_name must be a non-empty string"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                AndroidUeventdUnparsedLine,
            )
            for line in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidUeventdUnparsedLine objects"
            )

        source_lines = tuple(
            line.source_line
            for line in self.unparsed_lines
        )

        if len(
            source_lines
        ) != len(
            set(source_lines)
        ):
            raise ValueError(
                "UEVENTD unparsed source-line identities "
                "must be unique"
            )

        canonical_unparsed_lines = tuple(
            sorted(
                self.unparsed_lines,
                key=lambda line: (
                    line.source_line,
                    line.raw,
                ),
            )
        )

        if (
            self.unparsed_lines
            != canonical_unparsed_lines
        ):
            raise ValueError(
                "UEVENTD unparsed lines must remain in "
                "canonical source-line order"
            )

        if not all(
            line.source_path
            == self.source_path
            for line in self.unparsed_lines
        ):
            raise ValueError(
                "UEVENTD unparsed lines must preserve the "
                "same canonical source_path"
            )
