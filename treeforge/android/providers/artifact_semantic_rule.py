from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from dataclasses import dataclass

from treeforge.android.providers.artifact import (
    ProviderArtifactClassification,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderArtifactSemanticRule(
    ABC,
):
    """
    Immutable semantic-enrichment rule for discovered provider artifacts.

    Rules operate only after raw Discovery.

    They may interpret artifact identity, filenames, or other later-supplied
    knowledge, but they must never control whether an artifact is discovered.

    A rule miss returns ProviderArtifactClassification.UNKNOWN.

    Rules must not mutate discovery identity, structural kind, kind evidence,
    content observations, source identity, or provenance.
    """

    rule_id: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.rule_id,
            str,
        ):
            raise TypeError(
                "rule_id must be a string"
            )

        if not self.rule_id.strip():
            raise ValueError(
                "rule_id must not be empty"
            )

    @abstractmethod
    def classify(
        self,
        source_name: str,
    ) -> ProviderArtifactClassification:
        """
        Return the semantic classification supplied by this rule.

        UNKNOWN means the rule does not recognize the artifact.
        """

        raise NotImplementedError