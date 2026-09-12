from __future__ import annotations

from treeforge.android.discovery.report import (
    AndroidDiscoveryComparisonReport,
    AndroidDiscoveryReport,
)
from treeforge.android.discovery.snapshot import (
    AndroidDiscoverySnapshot,
)
from treeforge.android.discovery.snapshot_diff import (
    AndroidDiscoverySnapshotDiff,
)


class AndroidDiscoveryReportBuilder:
    """
    Build the canonical Discovery report from an immutable snapshot.

    An optional already-computed snapshot diff may be attached.

    No additional Discovery, inspection, comparison, or interpretation occurs
    here.
    """

    def build(
        self,
        *,
        snapshot: AndroidDiscoverySnapshot,
        diff: AndroidDiscoverySnapshotDiff | None = None,
    ) -> AndroidDiscoveryReport:
        if not isinstance(
            snapshot,
            AndroidDiscoverySnapshot,
        ):
            raise TypeError(
                "snapshot must be an "
                "AndroidDiscoverySnapshot"
            )

        if (
            diff is not None
            and not isinstance(
                diff,
                AndroidDiscoverySnapshotDiff,
            )
        ):
            raise TypeError(
                "diff must be an "
                "AndroidDiscoverySnapshotDiff or None"
            )

        unknown_artifacts = (
            snapshot.unknown_artifacts
        )

        structurally_known_unknown_count = sum(
            artifact.kind != "unknown"
            for artifact in unknown_artifacts
        )

        structurally_unknown_unknown_count = sum(
            artifact.kind == "unknown"
            for artifact in unknown_artifacts
        )

        comparison = (
            self._build_comparison(
                diff
            )
            if diff is not None
            else None
        )

        return AndroidDiscoveryReport(
            device_id=(
                snapshot.device_id
            ),
            android_version=(
                snapshot.android_version
            ),
            identity_evidence=(
                snapshot.identity_evidence
            ),
            total_artifact_count=(
                snapshot.artifact_count
            ),
            known_artifact_count=(
                snapshot.known_artifact_count
            ),
            unknown_artifact_count=(
                snapshot.unknown_artifact_count
            ),
            content_observed_artifact_count=(
                len(
                    snapshot.artifacts_with_content_observations
                )
            ),
            structurally_known_unknown_count=(
                structurally_known_unknown_count
            ),
            structurally_unknown_unknown_count=(
                structurally_unknown_unknown_count
            ),
            unknown_artifacts=(
                unknown_artifacts
            ),
            comparison=(
                comparison
            ),
        )

    @staticmethod
    def _build_comparison(
        diff: AndroidDiscoverySnapshotDiff,
    ) -> AndroidDiscoveryComparisonReport:
        return AndroidDiscoveryComparisonReport(
            device_before=(
                diff.device_before
            ),
            device_after=(
                diff.device_after
            ),
            android_version_before=(
                diff.android_version_before
            ),
            android_version_after=(
                diff.android_version_after
            ),
            added=(
                diff.added
            ),
            removed=(
                diff.removed
            ),
            changed=(
                diff.changed
            ),
            unchanged_count=(
                diff.unchanged_count
            ),
            newly_unknown=(
                diff.newly_unknown
            ),
            newly_understood=(
                diff.newly_understood
            ),
        )