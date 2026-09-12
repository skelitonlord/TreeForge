from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRuntimeProviderFile:
    """
    One externally supplied implementation file for an exact canonical
    Bootstrap destination path.

    The provider supplies implementation bytes only. Canonical identity,
    requirement ownership, destination path, and population reasons remain
    owned by Bootstrap Planning.
    """

    android_path: PurePosixPath
    source_path: Path
    content_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "android_path must be a PurePosixPath"
            )

        if not self.android_path.is_absolute():
            raise ValueError(
                "runtime provider android_path must be absolute"
            )

        if ".." in self.android_path.parts:
            raise ValueError(
                "runtime provider android_path must not contain parent traversal"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if (
            not isinstance(
                self.content_sha256,
                str,
            )
            or len(self.content_sha256) != 64
            or any(
                value not in "0123456789abcdef"
                for value in self.content_sha256
            )
        ):
            raise ValueError(
                "content_sha256 must be one lowercase SHA-256 hex digest"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRuntimeProvider:
    """
    One verified external implementation provider.

    Providers are implementation sources only. They must never replace
    canonical factory-derived Planning evidence or population identity.
    """

    name: str
    release: str
    canonical_sdk_level: str
    architecture: str

    files: tuple[
        AndroidBootstrapRuntimeProviderFile,
        ...,
    ]

    def __post_init__(self) -> None:
        for field_name in (
            "name",
            "release",
            "canonical_sdk_level",
            "architecture",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if (
            not isinstance(
                self.files,
                tuple,
            )
            or not self.files
        ):
            raise ValueError(
                "runtime provider must contain at least one file"
            )

        if not all(
            isinstance(
                value,
                AndroidBootstrapRuntimeProviderFile,
            )
            for value in self.files
        ):
            raise TypeError(
                "runtime provider files contain an invalid value"
            )

        paths = tuple(
            value.android_path
            for value in self.files
        )

        if len(paths) != len(set(paths)):
            raise ValueError(
                "runtime provider must not contain duplicate Android paths"
            )

    def file_for_android_path(
        self,
        android_path: PurePosixPath,
    ) -> AndroidBootstrapRuntimeProviderFile | None:
        if not isinstance(
            android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "android_path must be a PurePosixPath"
            )

        matches = tuple(
            value
            for value in self.files
            if value.android_path == android_path
        )

        if len(matches) > 1:
            raise RuntimeError(
                "runtime provider contains ambiguous Android path mapping"
            )

        return (
            matches[0]
            if matches
            else None
        )


__all__ = (
    "AndroidBootstrapRuntimeProvider",
    "AndroidBootstrapRuntimeProviderFile",
)
