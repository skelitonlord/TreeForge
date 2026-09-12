from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.providers.artifact import (
    ProviderArtifactClassification,
)
from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GoogleFactoryArtifactSemanticRule(
    ProviderArtifactSemanticRule,
):
    """
    Google factory-package semantic conventions.

    This rule is OEM knowledge, not generic Android knowledge.
    """

    rule_id: str = (
        "google-factory-artifact-semantics"
    )

    _FLASH_SCRIPT_NAMES = frozenset(
        {
            "flash-all.sh",
            "flash-base.sh",
            "flash-all.bat",
        }
    )

    def classify(
        self,
        source_name: str,
    ) -> ProviderArtifactClassification:
        lower_name = self._normalized_name(
            source_name
        )

        if (
            lower_name.startswith(
                "bootloader-"
            )
            and lower_name.endswith(
                ".img"
            )
        ):
            return (
                ProviderArtifactClassification
                .BOOTLOADER
            )

        if (
            lower_name.startswith(
                "image-"
            )
            and lower_name.endswith(
                ".zip"
            )
        ):
            return (
                ProviderArtifactClassification
                .IMAGE_ARCHIVE
            )

        if (
            lower_name
            in self._FLASH_SCRIPT_NAMES
        ):
            return (
                ProviderArtifactClassification
                .FLASH_SCRIPT
            )

        return (
            ProviderArtifactClassification.UNKNOWN
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