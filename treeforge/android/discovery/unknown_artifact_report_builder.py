from __future__ import annotations

from treeforge.android.discovery.result import (
    AndroidDiscoveryResult,
)
from treeforge.android.discovery.unknown_artifact import (
    AndroidUnknownArtifact,
)
from treeforge.android.discovery.unknown_artifact_report import (
    AndroidUnknownArtifactReport,
)


class AndroidUnknownArtifactReportBuilder:
    """
    Build a canonical unknown-artifact report from Android Discovery results.

    ProviderCollection remains the authoritative owner of provider inventories.

    This builder reads those inventories and reports unknown semantic artifacts
    without modifying Discovery state.
    """

    def build(
        self,
        discovery: AndroidDiscoveryResult,
    ) -> AndroidUnknownArtifactReport:
        if not isinstance(
            discovery,
            AndroidDiscoveryResult,
        ):
            raise TypeError(
                "discovery must be an "
                "AndroidDiscoveryResult"
            )

        collection = (
            discovery.provider_collection
        )

        if collection is None:
            return AndroidUnknownArtifactReport()

        total = 0
        known = 0

        unknowns: list[
            AndroidUnknownArtifact
        ] = []

        for result in collection:
            inventory = (
                result.artifact_inventory
            )

            total += (
                inventory.artifact_count
            )

            known += (
                inventory.known_count
            )

            for artifact in (
                inventory.unknown_artifacts
            ):
                unknowns.append(
                    AndroidUnknownArtifact(
                        source_name=(
                            artifact.source_name
                        ),
                        name=(
                            artifact.name
                        ),
                        provider_id=(
                            artifact.provider_id
                        ),
                        source_type=(
                            artifact.source_type
                        ),
                        kind=(
                            artifact.kind
                        ),
                        kind_evidence=(
                            artifact.kind_evidence
                        ),
                        classification=(
                            artifact.classification
                        ),
                        content_observations=(
                            artifact.content_observations
                        ),
                        provenance=(
                            artifact.provenance
                        ),
                    )
                )

        return AndroidUnknownArtifactReport(
            total_artifact_count=total,
            known_artifact_count=known,
            unknown_artifact_count=(
                len(
                    unknowns
                )
            ),
            artifacts=tuple(
                unknowns
            ),
        )