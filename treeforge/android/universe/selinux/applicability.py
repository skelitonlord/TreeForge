from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityEvidence,
    AndroidUniverseApplicabilityEvidenceKind,
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)


class AndroidUniverseSelinuxApplicabilityReconciler:
    """
    Reconcile applicability for canonical SELinux source requirements.

    SELinux source applicability is established only from canonical Universe
    evidence. A source with an Android filesystem path is structurally present
    in the observed device policy surface and is therefore active.

    Requirements without Android source-structure evidence remain unresolved;
    this layer does not infer applicability from SELinux source kind alone.
    """

    def reconcile(
        self,
        *,
        requirements: tuple[
            AndroidUniverseSelinuxSourceRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ]:
        conclusions = []

        for requirement in requirements:
            android_path = requirement.android_path

            if android_path is None:
                conclusions.append(
                    AndroidUniverseRequirementApplicability(
                        requirement_id=(
                            requirement.requirement_id
                        ),
                        status=(
                            AndroidUniverseApplicabilityStatus
                            .UNRESOLVED
                        ),
                        evidence=(),
                    )
                )
                continue

            normalized = (
                "/"
                + android_path.as_posix().lstrip("/")
            )

            evidence = (
                AndroidUniverseApplicabilityEvidence(
                    kind=(
                        AndroidUniverseApplicabilityEvidenceKind
                        .SOURCE_STRUCTURE
                    ),
                    raw_value=normalized,
                    source_path=requirement.source_path,
                    android_path=PurePosixPath(
                        normalized
                    ),
                ),
            )

            conclusions.append(
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        requirement.requirement_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .ACTIVE
                    ),
                    evidence=evidence,
                )
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )
