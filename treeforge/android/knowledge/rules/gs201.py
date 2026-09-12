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
class Gs201ArtifactSemanticRule(
    ProviderArtifactSemanticRule,
):
    """
    Artifact semantic knowledge currently validated for the gs201 platform.

    This knowledge must not be treated as generic Android behavior.
    """

    rule_id: str = (
        "gs201-artifact-semantics"
    )

    _BOOTLOADER_NAMES = frozenset(
        {
            "abl.img",
            "bl1.img",
            "bl2.img",
            "bl31.img",
            "pbl.img",
        }
    )

    _FIRMWARE_NAMES = frozenset(
        {
            "gsa.img",
            "ldfw.img",
            "tzsw.img",
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
            lower_name
            in self._BOOTLOADER_NAMES
        ):
            return (
                ProviderArtifactClassification
                .BOOTLOADER
            )

        if (
            lower_name
            in self._FIRMWARE_NAMES
        ):
            return (
                ProviderArtifactClassification
                .FIRMWARE
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