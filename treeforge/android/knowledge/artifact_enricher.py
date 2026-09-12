from __future__ import annotations

from treeforge.android.knowledge.resolution_result import (
    AndroidKnowledgeResolutionResult,
)
from treeforge.android.providers.artifact_enricher import (
    ProviderArtifactSemanticEnricher,
)
from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)
from treeforge.android.providers.generic_android_semantic_rule import (
    GenericAndroidArtifactSemanticRule,
)


class AndroidKnowledgeArtifactEnricher:
    """
    Re-apply semantic interpretation to an already-discovered artifact
    inventory using a resolved Android knowledge profile.

    This component operates strictly after raw Discovery.

    It does not:

    - rescan the source archive;
    - rediscover artifacts;
    - inspect artifact contents again;
    - change structural kind;
    - change kind evidence;
    - change content observations;
    - change provenance;
    - add or remove artifacts;
    - resolve knowledge dependencies.

    Only semantic classification may change.

    Generic Android semantics remain part of every enrichment pass, followed by
    the semantic rules supplied by the resolved knowledge profile.
    """

    def enrich(
        self,
        *,
        inventory: ProviderArtifactInventory,
        resolution: AndroidKnowledgeResolutionResult,
    ) -> ProviderArtifactInventory:
        if not isinstance(
            inventory,
            ProviderArtifactInventory,
        ):
            raise TypeError(
                "inventory must be a "
                "ProviderArtifactInventory"
            )

        if not isinstance(
            resolution,
            AndroidKnowledgeResolutionResult,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidKnowledgeResolutionResult"
            )

        enricher = ProviderArtifactSemanticEnricher(
            rules=(
                GenericAndroidArtifactSemanticRule(),
                *resolution.profile.discovery_semantic_rules,
            )
        )

        enriched = enricher.enrich_inventory(
            inventory
        )

        self._validate_structural_identity(
            before=inventory,
            after=enriched,
        )

        return enriched

    @staticmethod
    def _validate_structural_identity(
        *,
        before: ProviderArtifactInventory,
        after: ProviderArtifactInventory,
    ) -> None:
        if len(before) != len(after):
            raise ValueError(
                "knowledge enrichment must not "
                "change artifact count"
            )

        before_by_source = {
            artifact.source_name: artifact
            for artifact in before
        }

        after_by_source = {
            artifact.source_name: artifact
            for artifact in after
        }

        if (
            set(before_by_source)
            != set(after_by_source)
        ):
            raise ValueError(
                "knowledge enrichment must not add, "
                "remove, or rename artifacts"
            )

        for source_name in sorted(
            before_by_source
        ):
            original = before_by_source[
                source_name
            ]

            enriched = after_by_source[
                source_name
            ]

            if (
                original.name
                != enriched.name
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"artifact name: {source_name}"
                )

            if (
                original.provider_id
                != enriched.provider_id
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"provider ID: {source_name}"
                )

            if (
                original.source_type
                != enriched.source_type
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"source type: {source_name}"
                )

            if (
                original.kind
                is not enriched.kind
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"structural kind: {source_name}"
                )

            if (
                original.kind_evidence
                is not enriched.kind_evidence
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"kind evidence: {source_name}"
                )

            if (
                original.content_observations
                != enriched.content_observations
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    "content observations: "
                    f"{source_name}"
                )

            if (
                original.provenance
                != enriched.provenance
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"provenance: {source_name}"
                )