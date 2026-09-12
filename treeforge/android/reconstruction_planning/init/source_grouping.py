from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlanningObligation,
)
from treeforge.android.universe.init.source_applicability import (
    AndroidUniverseInitSourceApplicability,
    AndroidUniverseInitSourceApplicabilityStatus,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)


_INIT_REQUIREMENT_KINDS = frozenset(
    {
        "init_import",
        "init_service",
        "init_action",
    }
)


class AndroidReconstructionInitSourceDisposition(str, Enum):
    """Reconstruction disposition of one canonical INIT source."""

    REQUIRED = "required"
    ALTERNATIVE = "alternative"
    RUNTIME_SELECTABLE = "runtime_selectable"
    UNREFERENCED = "unreferenced"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidReconstructionInitSourceGroup:
    """
    Canonical Reconstruction Planning view of one INIT source.

    The source identity remains owned by Android Device Universe.
    Reconstruction only groups exact Universe requirements that share
    that already-established source identity.

    This model deliberately does not infer source-tree ownership,
    destination, reconstruction strategy, or rendered content.
    """

    source_identity: str

    disposition: AndroidReconstructionInitSourceDisposition

    obligations: tuple[
        AndroidReconstructionPlanningObligation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_identity,
            str,
        ):
            raise TypeError(
                "source_identity must be a string"
            )

        if not self.source_identity:
            raise ValueError(
                "source_identity must not be empty"
            )

        if not isinstance(
            self.disposition,
            AndroidReconstructionInitSourceDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidReconstructionInitSourceDisposition"
            )

        if not isinstance(
            self.obligations,
            tuple,
        ):
            raise TypeError(
                "obligations must be a tuple"
            )

        if not self.obligations:
            raise ValueError(
                "INIT source group must contain at least "
                "one obligation"
            )

        if not all(
            isinstance(
                obligation,
                AndroidReconstructionPlanningObligation,
            )
            for obligation in self.obligations
        ):
            raise TypeError(
                "obligations must contain only "
                "AndroidReconstructionPlanningObligation "
                "instances"
            )

        if not all(
            obligation.requirement_kind
            in _INIT_REQUIREMENT_KINDS
            for obligation in self.obligations
        ):
            raise ValueError(
                "INIT source group may contain only "
                "init_import, init_service, or init_action "
                "obligations"
            )

        obligation_ids = tuple(
            obligation.obligation_id
            for obligation in self.obligations
        )

        if len(
            obligation_ids
        ) != len(
            set(obligation_ids)
        ):
            raise ValueError(
                "INIT source group must not contain duplicate "
                "obligation identities"
            )

        for obligation in self.obligations:
            requirement = obligation.requirement

            actual_source_identity = (
                android_universe_init_source_identity(
                    source_path=requirement.source_path,
                    android_path=requirement.android_path,
                    filesystem_source=(
                        requirement.filesystem_source
                    ),
                )
            )

            if (
                actual_source_identity
                != self.source_identity
            ):
                raise ValueError(
                    "INIT source group obligations must share "
                    "one canonical Universe source identity"
                )

    @property
    def universe_requirement_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                obligation.source_identity
                for obligation in self.obligations
            )
        )


class AndroidReconstructionInitSourceGrouper:
    """
    Group INIT planning obligations by canonical Universe source identity.

    No source identity is invented here. The grouper delegates identity
    calculation to the exact Universe helper used by INIT requirements.
    """

    @staticmethod
    def group(
        obligations: tuple[
            AndroidReconstructionPlanningObligation,
            ...,
        ],
        *,
        source_applicability: tuple[
            AndroidUniverseInitSourceApplicability,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionInitSourceGroup,
        ...,
    ]:
        if not isinstance(
            obligations,
            tuple,
        ):
            raise TypeError(
                "obligations must be a tuple"
            )

        if not isinstance(
            source_applicability,
            tuple,
        ):
            raise TypeError(
                "source_applicability must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitSourceApplicability,
            )
            for item in source_applicability
        ):
            raise TypeError(
                "source_applicability must contain only "
                "AndroidUniverseInitSourceApplicability instances"
            )

        applicability_by_identity = {
            item.source_identity: item
            for item in source_applicability
        }

        if len(
            applicability_by_identity
        ) != len(
            source_applicability
        ):
            raise ValueError(
                "source_applicability must contain one conclusion "
                "per canonical Universe source identity"
            )

        grouped: dict[
            str,
            list[
                AndroidReconstructionPlanningObligation
            ],
        ] = {}

        for obligation in obligations:
            if not isinstance(
                obligation,
                AndroidReconstructionPlanningObligation,
            ):
                raise TypeError(
                    "obligations must contain only "
                    "AndroidReconstructionPlanningObligation "
                    "instances"
                )

            if (
                obligation.requirement_kind
                not in _INIT_REQUIREMENT_KINDS
            ):
                continue

            requirement = obligation.requirement

            source_identity = (
                android_universe_init_source_identity(
                    source_path=requirement.source_path,
                    android_path=requirement.android_path,
                    filesystem_source=(
                        requirement.filesystem_source
                    ),
                )
            )

            grouped.setdefault(
                source_identity,
                [],
            ).append(
                obligation
            )

        return tuple(
            AndroidReconstructionInitSourceGroup(
                source_identity=source_identity,
                disposition=(
                    AndroidReconstructionInitSourceGrouper
                    ._source_disposition(
                        source_identity=source_identity,
                        source_applicability=(
                            applicability_by_identity
                        ),
                    )
                ),
                obligations=tuple(
                    sorted(
                        source_obligations,
                        key=lambda obligation: (
                            obligation.requirement_kind,
                            obligation.source_identity,
                            obligation.obligation_id,
                        ),
                    )
                ),
            )
            for source_identity, source_obligations
            in sorted(
                grouped.items(),
                key=lambda item: item[0],
            )
        )

    @staticmethod
    def _source_disposition(
        *,
        source_identity: str,
        source_applicability: dict[
            str,
            AndroidUniverseInitSourceApplicability,
        ],
    ) -> AndroidReconstructionInitSourceDisposition:
        conclusion = source_applicability.get(
            source_identity
        )

        if conclusion is None:
            return AndroidReconstructionInitSourceDisposition.UNRESOLVED

        if (
            conclusion.status
            is AndroidUniverseInitSourceApplicabilityStatus.REQUIRED
        ):
            return AndroidReconstructionInitSourceDisposition.REQUIRED

        if (
            conclusion.status
            is AndroidUniverseInitSourceApplicabilityStatus.ALTERNATIVE
        ):
            return AndroidReconstructionInitSourceDisposition.ALTERNATIVE

        if (
            conclusion.status
            is AndroidUniverseInitSourceApplicabilityStatus.RUNTIME_SELECTABLE
        ):
            return (
                AndroidReconstructionInitSourceDisposition
                .RUNTIME_SELECTABLE
            )

        if (
            conclusion.status
            is AndroidUniverseInitSourceApplicabilityStatus.UNREFERENCED
        ):
            return (
                AndroidReconstructionInitSourceDisposition
                .UNREFERENCED
            )

        if (
            conclusion.status
            is AndroidUniverseInitSourceApplicabilityStatus.UNRESOLVED
        ):
            return AndroidReconstructionInitSourceDisposition.UNRESOLVED

        raise ValueError(
            "unsupported canonical Universe INIT source "
            "applicability status: "
            f"{conclusion.status!r}"
        )
