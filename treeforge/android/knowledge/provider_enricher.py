from __future__ import annotations

from dataclasses import replace

from treeforge.android.knowledge.artifact_enricher import (
    AndroidKnowledgeArtifactEnricher,
)
from treeforge.android.knowledge.resolution_result import (
    AndroidKnowledgeResolutionResult,
)
from treeforge.android.providers.collection import (
    ProviderCollection,
)


class AndroidKnowledgeProviderEnricher:
    """
    Apply resolved Android knowledge to an existing provider collection.

    Provider discovery has already completed before this component runs.

    This component:

    - does not rescan provider sources;
    - does not add or remove provider results;
    - does not change provider identity;
    - does not change provider capabilities;
    - does not change provider warnings;
    - does not change source identity or provenance;
    - replaces only artifact inventories whose semantics are enriched.

    ProviderResult and ProviderCollection remain immutable. New canonical
    instances are returned instead of mutating existing provider state.
    """

    def __init__(
        self,
        *,
        artifact_enricher: (
            AndroidKnowledgeArtifactEnricher
            | None
        ) = None,
    ) -> None:
        self.artifact_enricher = (
            artifact_enricher
            if artifact_enricher is not None
            else AndroidKnowledgeArtifactEnricher()
        )

    def enrich(
        self,
        *,
        collection: ProviderCollection,
        resolution: AndroidKnowledgeResolutionResult,
    ) -> ProviderCollection:
        if not isinstance(
            collection,
            ProviderCollection,
        ):
            raise TypeError(
                "collection must be a "
                "ProviderCollection"
            )

        if not isinstance(
            resolution,
            AndroidKnowledgeResolutionResult,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidKnowledgeResolutionResult"
            )

        enriched_results = tuple(
            replace(
                result,
                artifact_inventory=(
                    self.artifact_enricher.enrich(
                        inventory=(
                            result.artifact_inventory
                        ),
                        resolution=resolution,
                    )
                ),
            )
            for result in collection
        )

        enriched_collection = (
            ProviderCollection(
                results=enriched_results,
            )
        )

        self._validate_collection_identity(
            before=collection,
            after=enriched_collection,
        )

        return enriched_collection

    @staticmethod
    def _validate_collection_identity(
        *,
        before: ProviderCollection,
        after: ProviderCollection,
    ) -> None:
        if len(before) != len(after):
            raise ValueError(
                "knowledge enrichment must not "
                "change provider count"
            )

        before_by_id = {
            result.provider_id: result
            for result in before
        }

        after_by_id = {
            result.provider_id: result
            for result in after
        }

        if (
            set(before_by_id)
            != set(after_by_id)
        ):
            raise ValueError(
                "knowledge enrichment must not add, "
                "remove, or rename providers"
            )

        for provider_id in sorted(
            before_by_id
        ):
            original = before_by_id[
                provider_id
            ]

            enriched = after_by_id[
                provider_id
            ]

            if (
                original.provider_name
                != enriched.provider_name
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"provider name: {provider_id}"
                )

            if (
                original.provider_version
                != enriched.provider_version
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"provider version: {provider_id}"
                )

            if (
                original.source_type
                is not enriched.source_type
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"source type: {provider_id}"
                )

            if (
                original.source_identity
                != enriched.source_identity
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"source identity: {provider_id}"
                )

            if (
                original.capabilities
                != enriched.capabilities
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"capabilities: {provider_id}"
                )

            if (
                original.warnings
                != enriched.warnings
            ):
                raise ValueError(
                    "knowledge enrichment changed "
                    f"warnings: {provider_id}"
                )