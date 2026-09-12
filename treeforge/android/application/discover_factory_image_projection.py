from __future__ import annotations

from typing import Any

from treeforge.android.application.discover_factory_image import (
    DiscoverFactoryImageResult,
)


class DiscoverFactoryImageProjection:
    """
    Project a completed factory-image Discovery result into deterministic,
    JSON-compatible data.

    This is an inspection/export representation, not a Discovery snapshot.
    It exposes only information retained by the canonical result models.
    """

    def project(
        self,
        result: DiscoverFactoryImageResult,
    ) -> dict[str, Any]:
        if not isinstance(
            result,
            DiscoverFactoryImageResult,
        ):
            raise TypeError(
                "result must be a DiscoverFactoryImageResult"
            )

        discovery = result.discovery
        collection = discovery.provider_collection

        if collection is None:
            raise ValueError(
                "Discovery result does not contain "
                "a provider collection"
            )

        factory_result = collection.result_for(
            "factory-image"
        )

        if factory_result is None:
            raise ValueError(
                "Discovery result does not contain "
                "the factory-image provider result"
            )

        inventory = factory_result.artifact_inventory
        inference = discovery.identity_inference

        return {
            "schema": "treeforge.discovery",
            "schema_version": 1,
            "mode": (
                "generic-only"
                if result.request.generic_only
                else "knowledge-enriched"
            ),
            "source": {
                "factory_image": str(
                    result.request.factory_image
                ),
            },
            "identity": {
                "device": inference.device_id,
                "android_version": (
                    inference.android_version
                ),
                "evidence": [
                    {
                        "kind": evidence.kind.value,
                        "value": evidence.value,
                        "source": evidence.source,
                        "detail": evidence.detail,
                    }
                    for evidence in inference.evidence
                ],
            },
            "explicit_selection": {
                "device": result.request.device_id,
                "android_version": (
                    result.request.android_version
                ),
            },
            "knowledge": self._project_knowledge(
                result
            ),
            "artifacts": {
                "total": len(inventory),
                "known": inventory.known_count,
                "unknown": inventory.unknown_count,
                "items": [
                    self._project_artifact(
                        artifact
                    )
                    for artifact in inventory
                ],
            },
        }

    @staticmethod
    def _project_knowledge(
        result: DiscoverFactoryImageResult,
    ) -> dict[str, Any] | None:
        resolution = result.knowledge_resolution

        if resolution is None:
            return None

        return {
            "root_selections": [
                {
                    "module_id": root.module_id,
                    "source": root.source.value,
                }
                for root in resolution.root_selections
            ],
            "resolved_modules": list(
                resolution.module_ids
            ),
        }

    @staticmethod
    def _project_artifact(
        artifact,
    ) -> dict[str, Any]:
        provenance = artifact.provenance

        return {
            "name": artifact.name,
            "source_name": artifact.source_name,
            "provider_id": artifact.provider_id,
            "source_type": artifact.source_type.value,
            "kind": artifact.kind.value,
            "kind_evidence": (
                artifact.kind_evidence.value
            ),
            "classification": (
                artifact.classification.value
            ),
            "content_observations": [
                {
                    "signature": (
                        observation.signature.value
                    ),
                    "confidence": (
                        observation.confidence.value
                    ),
                    "offset": observation.offset,
                    "matched_bytes": (
                        observation.matched_bytes.hex()
                        if observation.matched_bytes
                        else None
                    ),
                }
                for observation in (
                    artifact.content_observations
                )
            ],
            "provenance": (
                {
                    "container_depth": (
                        provenance.container_depth
                    ),
                    "size_bytes": (
                        provenance.size_bytes
                    ),
                    "compressed_size_bytes": (
                        provenance.compressed_size_bytes
                    ),
                    "crc32": provenance.crc32,
                }
                if provenance is not None
                else None
            ),
        }