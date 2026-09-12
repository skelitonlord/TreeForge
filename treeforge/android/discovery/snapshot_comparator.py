from __future__ import annotations

from treeforge.android.discovery.snapshot import (
    AndroidDiscoveryArtifactSnapshot,
    AndroidDiscoverySnapshot,
)
from treeforge.android.discovery.snapshot_diff import (
    AndroidDiscoveryArtifactChange,
    AndroidDiscoverySnapshotDiff,
)


class AndroidDiscoverySnapshotComparator:
    """
    Compare two canonical Android Discovery snapshots.

    Matching uses exact source_name identity in v1.

    Comparison is limited to fields already stored in the Discovery snapshot.
    """

    _COMPARABLE_FIELDS = (
        "name",
        "provider_id",
        "source_type",
        "kind",
        "kind_evidence",
        "classification",
        "content_observations",
        "container_depth",
        "size_bytes",
        "compressed_size_bytes",
        "crc32",
    )

    def compare(
        self,
        *,
        before: AndroidDiscoverySnapshot,
        after: AndroidDiscoverySnapshot,
    ) -> AndroidDiscoverySnapshotDiff:
        if not isinstance(
            before,
            AndroidDiscoverySnapshot,
        ):
            raise TypeError(
                "before must be an "
                "AndroidDiscoverySnapshot"
            )

        if not isinstance(
            after,
            AndroidDiscoverySnapshot,
        ):
            raise TypeError(
                "after must be an "
                "AndroidDiscoverySnapshot"
            )

        before_by_source = {
            artifact.source_name: artifact
            for artifact in before.artifacts
        }

        after_by_source = {
            artifact.source_name: artifact
            for artifact in after.artifacts
        }

        before_sources = set(
            before_by_source
        )

        after_sources = set(
            after_by_source
        )

        added = tuple(
            after_by_source[
                source_name
            ]
            for source_name in sorted(
                after_sources
                - before_sources
            )
        )

        removed = tuple(
            before_by_source[
                source_name
            ]
            for source_name in sorted(
                before_sources
                - after_sources
            )
        )

        changed: list[
            AndroidDiscoveryArtifactChange
        ] = []

        unchanged: list[
            AndroidDiscoveryArtifactSnapshot
        ] = []

        shared_sources = tuple(
            sorted(
                before_sources
                & after_sources
            )
        )

        for source_name in shared_sources:
            before_artifact = (
                before_by_source[
                    source_name
                ]
            )

            after_artifact = (
                after_by_source[
                    source_name
                ]
            )

            changed_fields = (
                self._changed_fields(
                    before=before_artifact,
                    after=after_artifact,
                )
            )

            if changed_fields:
                changed.append(
                    AndroidDiscoveryArtifactChange(
                        before=before_artifact,
                        after=after_artifact,
                        changed_fields=(
                            changed_fields
                        ),
                    )
                )
            else:
                unchanged.append(
                    after_artifact
                )

        return AndroidDiscoverySnapshotDiff(
            added=added,
            removed=removed,
            changed=tuple(
                changed
            ),
            unchanged=tuple(
                unchanged
            ),
            device_before=(
                before.device_id
            ),
            device_after=(
                after.device_id
            ),
            android_version_before=(
                before.android_version
            ),
            android_version_after=(
                after.android_version
            ),
        )

    def _changed_fields(
        self,
        *,
        before: AndroidDiscoveryArtifactSnapshot,
        after: AndroidDiscoveryArtifactSnapshot,
    ) -> tuple[
        str,
        ...,
    ]:
        changed = tuple(
            field_name
            for field_name in (
                self._COMPARABLE_FIELDS
            )
            if (
                getattr(
                    before,
                    field_name,
                )
                != getattr(
                    after,
                    field_name,
                )
            )
        )

        return changed