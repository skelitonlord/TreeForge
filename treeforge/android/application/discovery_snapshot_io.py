from __future__ import annotations

import json
from pathlib import Path

from treeforge.android.discovery import (
    AndroidDiscoveryArtifactSnapshot,
    AndroidDiscoveryContentObservationSnapshot,
    AndroidDiscoveryIdentityEvidenceSnapshot,
    AndroidDiscoverySnapshot,
)


class AndroidDiscoverySnapshotIO:
    """
    Serialize and restore canonical Android Discovery snapshots.

    Snapshot files are stable comparison baselines, not full inspection dumps.
    """

    SCHEMA = "treeforge.discovery.snapshot"
    SCHEMA_VERSION = 1

    def write(
        self,
        *,
        snapshot: AndroidDiscoverySnapshot,
        destination: Path,
    ) -> None:
        if not isinstance(
            snapshot,
            AndroidDiscoverySnapshot,
        ):
            raise TypeError(
                "snapshot must be an AndroidDiscoverySnapshot"
            )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a Path"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.write_text(
            json.dumps(
                self.to_dict(
                    snapshot
                ),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def read(
        self,
        source: Path,
    ) -> AndroidDiscoverySnapshot:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a Path"
            )

        payload = json.loads(
            source.read_text(
                encoding="utf-8",
            )
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "snapshot payload must be a JSON object"
            )

        if (
            payload.get("schema")
            != self.SCHEMA
        ):
            raise ValueError(
                "unsupported Discovery snapshot schema"
            )

        if (
            payload.get("schema_version")
            != self.SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported Discovery snapshot schema version"
            )

        identity = payload.get(
            "identity",
            {},
        )

        if not isinstance(
            identity,
            dict,
        ):
            raise ValueError(
                "identity must be a JSON object"
            )

        evidence_payload = identity.get(
            "evidence",
            [],
        )

        artifacts_payload = payload.get(
            "artifacts",
            [],
        )

        if not isinstance(
            evidence_payload,
            list,
        ):
            raise ValueError(
                "identity evidence must be a JSON array"
            )

        if not isinstance(
            artifacts_payload,
            list,
        ):
            raise ValueError(
                "artifacts must be a JSON array"
            )

        identity_evidence = tuple(
            AndroidDiscoveryIdentityEvidenceSnapshot(
                kind=item["kind"],
                value=item["value"],
                source=item["source"],
                detail=item["detail"],
            )
            for item in evidence_payload
        )

        artifacts = tuple(
            self._artifact_from_dict(
                item
            )
            for item in artifacts_payload
        )

        return AndroidDiscoverySnapshot(
            device_id=identity.get(
                "device"
            ),
            board_platform=identity.get(
                "board_platform"
            ),
            android_version=identity.get(
                "android_version"
            ),
            identity_evidence=(
                identity_evidence
            ),
            artifacts=artifacts,
        )

    def to_dict(
        self,
        snapshot: AndroidDiscoverySnapshot,
    ) -> dict[str, object]:
        if not isinstance(
            snapshot,
            AndroidDiscoverySnapshot,
        ):
            raise TypeError(
                "snapshot must be an AndroidDiscoverySnapshot"
            )

        return {
            "schema": self.SCHEMA,
            "schema_version": self.SCHEMA_VERSION,
            "identity": {
                "device": snapshot.device_id,
                "board_platform": (
                    snapshot.board_platform
                ),
                "android_version": (
                    snapshot.android_version
                ),
                "evidence": [
                    {
                        "kind": evidence.kind,
                        "value": evidence.value,
                        "source": evidence.source,
                        "detail": evidence.detail,
                    }
                    for evidence
                    in snapshot.identity_evidence
                ],
            },
            "artifacts": [
                {
                    "source_name": (
                        artifact.source_name
                    ),
                    "name": artifact.name,
                    "provider_id": (
                        artifact.provider_id
                    ),
                    "source_type": (
                        artifact.source_type
                    ),
                    "kind": artifact.kind,
                    "kind_evidence": (
                        artifact.kind_evidence
                    ),
                    "classification": (
                        artifact.classification
                    ),
                    "content_observations": [
                        {
                            "signature": (
                                observation.signature
                            ),
                            "confidence": (
                                observation.confidence
                            ),
                            "offset": (
                                observation.offset
                            ),
                            "matched_bytes_hex": (
                                observation.matched_bytes_hex
                            ),
                        }
                        for observation in (
                            artifact
                            .content_observations
                        )
                    ],
                    "container_depth": (
                        artifact.container_depth
                    ),
                    "size_bytes": (
                        artifact.size_bytes
                    ),
                    "compressed_size_bytes": (
                        artifact.compressed_size_bytes
                    ),
                    "crc32": artifact.crc32,
                }
                for artifact
                in snapshot.artifacts
            ],
        }

    @staticmethod
    def _artifact_from_dict(
        item: object,
    ) -> AndroidDiscoveryArtifactSnapshot:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "artifact snapshot entry must be "
                "a JSON object"
            )

        observations_payload = item.get(
            "content_observations",
            [],
        )

        if not isinstance(
            observations_payload,
            list,
        ):
            raise ValueError(
                "content_observations must be "
                "a JSON array"
            )

        observations = tuple(
            AndroidDiscoveryContentObservationSnapshot(
                signature=observation[
                    "signature"
                ],
                confidence=observation[
                    "confidence"
                ],
                offset=observation[
                    "offset"
                ],
                matched_bytes_hex=observation.get(
                    "matched_bytes_hex",
                    "",
                ),
            )
            for observation
            in observations_payload
        )

        return AndroidDiscoveryArtifactSnapshot(
            source_name=item[
                "source_name"
            ],
            name=item[
                "name"
            ],
            provider_id=item[
                "provider_id"
            ],
            source_type=item[
                "source_type"
            ],
            kind=item[
                "kind"
            ],
            kind_evidence=item[
                "kind_evidence"
            ],
            classification=item[
                "classification"
            ],
            content_observations=(
                observations
            ),
            container_depth=item.get(
                "container_depth",
                0,
            ),
            size_bytes=item.get(
                "size_bytes"
            ),
            compressed_size_bytes=item.get(
                "compressed_size_bytes"
            ),
            crc32=item.get(
                "crc32"
            ),
        )