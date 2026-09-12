from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.fstab import (
    AndroidFstabUnparsedLine,
)
from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidFstab,
)


@dataclass(frozen=True, slots=True)
class AndroidUniverseFstabSourceContext:
    """
    Canonical source-level context for one parsed Android fstab source.

    Universe requirements represent successfully interpreted declarations.
    This companion context preserves meaningful lexical material that Parsing
    intentionally could not interpret, without inventing semantic
    requirements for it.

    The exact Parsing ``AndroidFstabUnparsedLine`` objects are retained.
    Downstream stages may preserve this context but must not reinterpret it
    as a canonical fstab requirement.

    This object does not choose source-tree ownership, destination, filename,
    rendering policy, or materialization behavior.
    """

    source_path: Path
    android_path: PurePosixPath | None
    source_name: str

    unparsed_lines: tuple[
        AndroidFstabUnparsedLine,
        ...,
    ] = ()

    @property
    def source_identity(self) -> tuple[
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

    def __post_init__(self) -> None:
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

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidFstabUnparsedLine,
            )
            for item in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidFstabUnparsedLine instances"
            )

        line_numbers = tuple(
            item.line_number
            for item in self.unparsed_lines
        )

        if len(line_numbers) != len(
            set(line_numbers)
        ):
            raise ValueError(
                "fstab source context contains duplicate "
                "unparsed source-line identities"
            )

        if tuple(sorted(line_numbers)) != line_numbers:
            raise ValueError(
                "fstab source context unparsed lines must be "
                "in canonical source order"
            )

    @classmethod
    def from_parsed(
        cls,
        source: ParsedAndroidFstab,
    ) -> "AndroidUniverseFstabSourceContext":
        if not isinstance(
            source,
            ParsedAndroidFstab,
        ):
            raise TypeError(
                "source must be a ParsedAndroidFstab"
            )

        return cls(
            source_path=source.source_path,
            android_path=source.android_path,
            source_name=(
                source.filesystem_source.source_name
            ),
            unparsed_lines=source.unparsed_lines,
        )
