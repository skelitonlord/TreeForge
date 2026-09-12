from __future__ import annotations

from dataclasses import replace

from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
)
from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)
from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)
from treeforge.android.providers.generic_android_semantic_rule import (
    GenericAndroidArtifactSemanticRule,
)


class ProviderArtifactSemanticEnricher:
    """
    Apply ordered optional semantic knowledge to discovered artifacts.

    Raw Discovery remains independent of semantic enrichment.

    Enrichment is immutable.

    Discovery identity, structural kind, kind evidence, content observations,
    provider identity, source type, and provenance are preserved exactly.

    Rules are evaluated deterministically in supplied order.

    The first non-UNKNOWN classification wins.

    A complete rule miss leaves the artifact UNKNOWN and never removes it.
    """

    def __init__(
        self,
        *,
        rules: tuple[
            ProviderArtifactSemanticRule,
            ...,
        ] | None = None,
    ) -> None:
        if rules is None:
            rules = (
                GenericAndroidArtifactSemanticRule(),
            )

        if not isinstance(
            rules,
            tuple,
        ):
            raise TypeError(
                "rules must be a tuple"
            )

        for rule in rules:
            if not isinstance(
                rule,
                ProviderArtifactSemanticRule,
            ):
                raise TypeError(
                    "rules must contain only "
                    "ProviderArtifactSemanticRule instances"
                )

        rule_ids = tuple(
            rule.rule_id
            for rule in rules
        )

        if (
            len(rule_ids)
            != len(
                set(
                    rule_ids
                )
            )
        ):
            raise ValueError(
                "rules must not contain "
                "duplicate rule IDs"
            )

        self.rules = rules

    def enrich_inventory(
        self,
        inventory: ProviderArtifactInventory,
    ) -> ProviderArtifactInventory:
        """
        Return a semantically enriched copy of one discovery inventory.
        """

        if not isinstance(
            inventory,
            ProviderArtifactInventory,
        ):
            raise TypeError(
                "inventory must be a "
                "ProviderArtifactInventory"
            )

        return ProviderArtifactInventory(
            artifacts=tuple(
                self.enrich_artifact(
                    artifact
                )
                for artifact in inventory
            )
        )

    def enrich_artifact(
        self,
        artifact: ProviderArtifact,
    ) -> ProviderArtifact:
        """
        Return one artifact with optional semantic classification enrichment.
        """

        if not isinstance(
            artifact,
            ProviderArtifact,
        ):
            raise TypeError(
                "artifact must be a ProviderArtifact"
            )

        classification = (
            self.classify_semantics(
                artifact.name
            )
        )

        if (
            classification
            is artifact.classification
        ):
            return artifact

        return replace(
            artifact,
            classification=classification,
        )

    def classify_semantics(
        self,
        source_name: str,
    ) -> ProviderArtifactClassification:
        """
        Apply semantic rules in deterministic order.

        The first rule that produces a non-UNKNOWN classification wins.

        UNKNOWN is an explicit valid result.
        """

        for rule in self.rules:
            classification = (
                rule.classify(
                    source_name
                )
            )

            if (
                classification
                is ProviderArtifactClassification.UNKNOWN
            ):
                continue

            return classification

        return (
            ProviderArtifactClassification.UNKNOWN
        )