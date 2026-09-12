"""Source provenance models for Android init artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


class SourceOrigin(StrEnum):
    """Describes how an artifact entered the analysis pipeline."""

    PARSED = "parsed"
    IMPORTED = "imported"
    GENERATED = "generated"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class SourceLocation:
    """
    Identify the source location of a parsed or generated artifact.

    ``file`` preserves the exact parser-facing host path.

    ``android_path`` preserves the canonical absolute Android-visible path.
    """

    file: Path | None = None
    line: int | None = None
    column: int | None = None
    origin: SourceOrigin = SourceOrigin.UNKNOWN
    imported_from: Path | None = None
    android_path: PurePosixPath | None = None

    def __post_init__(
        self,
    ) -> None:
        """Validate all source-location fields."""

        if (
            self.file is not None
            and not isinstance(
                self.file,
                Path,
            )
        ):
            raise TypeError(
                "source file must be a Path or None"
            )

        if (
            self.imported_from is not None
            and not isinstance(
                self.imported_from,
                Path,
            )
        ):
            raise TypeError(
                "imported_from must be a Path or None"
            )

        if not isinstance(
            self.origin,
            SourceOrigin,
        ):
            raise TypeError(
                "origin must be a SourceOrigin"
            )

        if (
            self.line is not None
            and not isinstance(
                self.line,
                int,
            )
        ):
            raise TypeError(
                "source line must be an integer or None"
            )

        if (
            self.column is not None
            and not isinstance(
                self.column,
                int,
            )
        ):
            raise TypeError(
                "source column must be an integer or None"
            )

        if (
            self.line is not None
            and self.line < 1
        ):
            raise ValueError(
                "source line must be greater than or equal to 1"
            )

        if (
            self.column is not None
            and self.column < 1
        ):
            raise ValueError(
                "source column must be greater than or equal to 1"
            )

        if (
            self.column is not None
            and self.line is None
        ):
            raise ValueError(
                "source column requires a source line"
            )

        self._validate_android_path(
            self.android_path
        )

    @staticmethod
    def _validate_android_path(
        android_path: PurePosixPath | None,
    ) -> None:
        """
        Validate an optional canonical Android path.

        Canonical Android paths are absolute Android-visible paths,
        for example ``/system/etc/init/init.rc``.
        """

        if (
            android_path is not None
            and not isinstance(
                android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if android_path is None:
            return

        if not android_path.is_absolute():
            raise ValueError(
                "android_path must be absolute"
            )

        if (
            not android_path.parts
            or str(
                android_path
            ) in {
                "",
                ".",
            }
        ):
            raise ValueError(
                "android_path must identify a file"
            )

        if ".." in android_path.parts:
            raise ValueError(
                "android_path must not contain "
                "parent traversal"
            )

    @property
    def is_known(
        self,
    ) -> bool:
        """Return whether any concrete source information is available."""

        return any(
            value is not None
            for value in (
                self.file,
                self.line,
                self.column,
                self.imported_from,
                self.android_path,
            )
        ) or (
            self.origin
            is not SourceOrigin.UNKNOWN
        )

    @property
    def is_imported(
        self,
    ) -> bool:
        """Return whether the artifact came from an imported source."""

        return (
            self.origin
            is SourceOrigin.IMPORTED
            or self.imported_from is not None
        )

    def format(
        self,
    ) -> str:
        """
        Return a concise human-readable host source location.

        Formatting intentionally uses ``file`` rather than ``android_path``
        because this method reports exact parser provenance.
        """

        if self.file is None:
            if self.line is None:
                return "<unknown>"

            if self.column is None:
                return (
                    f"<unknown>:{self.line}"
                )

            return (
                f"<unknown>:{self.line}:"
                f"{self.column}"
            )

        location = str(
            self.file
        )

        if self.line is not None:
            location = (
                f"{location}:{self.line}"
            )

        if self.column is not None:
            location = (
                f"{location}:{self.column}"
            )

        return location