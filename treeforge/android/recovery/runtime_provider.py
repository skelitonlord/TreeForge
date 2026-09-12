from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryRuntimeProviderFile:
    """
    One verified implementation file supplied by a bundled
    Recovery runtime provider.

    The provider supplies implementation bytes only. Device topology,
    target-slot identity, Virtual A/B requirements, and other canonical
    Recovery facts remain owned by Recovery's live/canonical evidence.
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
                "runtime provider android_path must not contain "
                "parent traversal"
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
                "content_sha256 must be one lowercase SHA-256 "
                "hex digest"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryRuntimeProvider:
    """
    One verified bundled Recovery device-runtime provider.

    This is an implementation-provider model only.

    It must not supply or replace canonical Recovery facts such as
    active slot, target slot, logical-partition topology, Virtual A/B
    enablement, partition sizes, or installation policy.
    """

    name: str
    release: str
    canonical_sdk_level: str
    architecture: str

    files: tuple[
        RecoveryRuntimeProviderFile,
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
                RecoveryRuntimeProviderFile,
            )
            for value in self.files
        ):
            raise TypeError(
                "runtime provider files contain an invalid value"
            )

        android_paths = tuple(
            value.android_path
            for value in self.files
        )

        if (
            len(android_paths)
            != len(set(android_paths))
        ):
            raise ValueError(
                "runtime provider must not contain duplicate "
                "Android paths"
            )

    def file_for_android_path(
        self,
        android_path: PurePosixPath,
    ) -> RecoveryRuntimeProviderFile | None:
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
                "runtime provider contains ambiguous Android path "
                "mapping"
            )

        return (
            matches[0]
            if matches
            else None
        )


__all__ = (
    "RecoveryRuntimeProvider",
    "RecoveryRuntimeProviderFile",
)
