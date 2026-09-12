from __future__ import annotations

from treeforge.android.discovery.result import (
    AndroidDiscoveryResult,
)
from treeforge.android.discovery.snapshot import (
    AndroidDiscoveryArtifactSnapshot,
    AndroidDiscoveryContentObservationSnapshot,
    AndroidDiscoveryIdentityEvidenceSnapshot,
    AndroidDiscoverySnapshot,
)


class AndroidDiscoverySnapshotBuilder:
    """
    Build a stable immutable baseline from canonical Android Discovery state.

    The builder does not perform additional inspection or interpretation.

    Every value comes from models already produced by Discovery.
    """

    def build(
        self,
        discovery: AndroidDiscoveryResult,
    ) -> AndroidDiscoverySnapshot:
        if not isinstance(
            discovery,
            AndroidDiscoveryResult,
        ):
            raise TypeError(
                "discovery must be an "
                "AndroidDiscoveryResult"
            )

        artifacts: list[
            AndroidDiscoveryArtifactSnapshot
        ] = []

        collection = (
            discovery.provider_collection
        )

        if collection is not None:
            for result in collection:
                for artifact in (
                    result.artifact_inventory
                ):
                    provenance = (
                        artifact.provenance
                    )

                    observations = tuple(
                        AndroidDiscoveryContentObservationSnapshot(
                            signature=(
                                observation.signature.value
                            ),
                            confidence=(
                                observation.confidence.value
                            ),
                            offset=(
                                observation.offset
                            ),
                            matched_bytes_hex=(
                                observation.matched_bytes.hex()
                            ),
                        )
                        for observation in (
                            artifact.content_observations
                        )
                    )

                    artifacts.append(
                        AndroidDiscoveryArtifactSnapshot(
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
                                artifact.source_type.value
                            ),
                            kind=(
                                artifact.kind.value
                            ),
                            kind_evidence=(
                                artifact.kind_evidence.value
                            ),
                            classification=(
                                artifact.classification.value
                            ),
                            content_observations=(
                                observations
                            ),
                            container_depth=(
                                provenance.container_depth
                                if provenance is not None
                                else 0
                            ),
                            size_bytes=(
                                provenance.size_bytes
                                if provenance is not None
                                else None
                            ),
                            compressed_size_bytes=(
                                provenance.compressed_size_bytes
                                if provenance is not None
                                else None
                            ),
                            crc32=(
                                provenance.crc32
                                if provenance is not None
                                else None
                            ),
                        )
                    )

        inference = (
            discovery.identity_inference
        )

        identity_evidence = tuple(
            AndroidDiscoveryIdentityEvidenceSnapshot(
                kind=(
                    evidence.kind.value
                ),
                value=(
                    evidence.value
                ),
                source=(
                    evidence.source
                ),
                detail=(
                    evidence.detail
                ),
            )
            for evidence in (
                inference.evidence
            )
        )

        return AndroidDiscoverySnapshot(
            device_id=(
                inference.device_id
            ),
            board_platform=(
                inference.board_platform
            ),
            android_version=(
                inference.android_version
            ),
            identity_evidence=(
                identity_evidence
            ),
            artifacts=tuple(
                artifacts
            ),
        )