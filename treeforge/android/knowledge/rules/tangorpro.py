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
class TangorproArtifactSemanticRule(
    ProviderArtifactSemanticRule,
):
    """
    Artifact semantics currently validated specifically for tangorpro.

    These rules may later be promoted to a broader platform/OEM module if
    evidence proves that their scope is wider.
    """

    rule_id: str = (
        "tangorpro-artifact-semantics"
    )

    def classify(
        self,
        source_name: str,
    ) -> ProviderArtifactClassification:
        lower_name = self._normalized_name(
            source_name
        )

        if lower_name.endswith(
            ".ec.bin"
        ):
            return (
                ProviderArtifactClassification
                .EMBEDDED_CONTROLLER_FIRMWARE
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