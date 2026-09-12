from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.providers.artifact import (
    ProviderArtifactKind,
)


class ProviderArtifactClassifier:
    """
    Provide non-authoritative structural filename hints.

    This component does not assign Android semantic meaning.

    Filename hints never control whether an artifact is discovered.

    Stronger structural evidence from artifact contents may override the hint.
    For example, ProviderArchiveScanner can prove that an extensionless member
    is actually a ZIP archive.
    """

    _TEXT_SUFFIXES = (
        ".txt",
        ".xml",
        ".json",
        ".conf",
        ".cfg",
    )

    _SCRIPT_SUFFIXES = (
        ".sh",
        ".bat",
    )

    _BINARY_SUFFIXES = (
        ".bin",
        ".fw",
    )

    def classify_kind(
        self,
        source_name: str,
    ) -> ProviderArtifactKind:
        """
        Return a generic filename-derived structural hint.

        The result is not authoritative content detection.
        """

        lower_name = self._normalized_name(
            source_name
        )

        if lower_name.endswith(
            ".img"
        ):
            return (
                ProviderArtifactKind.IMAGE
            )

        if lower_name.endswith(
            ".zip"
        ):
            return (
                ProviderArtifactKind.ARCHIVE
            )

        if lower_name.endswith(
            self._TEXT_SUFFIXES
        ):
            return (
                ProviderArtifactKind.TEXT
            )

        if lower_name.endswith(
            self._SCRIPT_SUFFIXES
        ):
            return (
                ProviderArtifactKind.SCRIPT
            )

        if lower_name.endswith(
            self._BINARY_SUFFIXES
        ):
            return (
                ProviderArtifactKind.BINARY
            )

        return (
            ProviderArtifactKind.UNKNOWN
        )

    @staticmethod
    def _normalized_name(
        source_name: str,
    ) -> str:
        if not isinstance(
            source_name,
            str,
        ):
            raise TypeError(
                "source_name must be a string"
            )

        if not source_name.strip():
            raise ValueError(
                "source_name must not be empty"
            )

        return (
            PurePosixPath(
                source_name
            )
            .name
            .lower()
        )