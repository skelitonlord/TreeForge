from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.reconstruction_ownership.artifact.evidence_model import (
    AndroidReconstructionArtifactEvidenceInventory,
)


class AndroidReconstructionOwnershipDomain(StrEnum):
    """
    Canonical source-tree ownership domains.

    PROPRIETARY means exact preserved/prebuilt artifact ownership in the
    generated Android source tree. It does not assert licensing status.
    """

    DEVICE = "device"
    VENDOR = "vendor"
    HARDWARE = "hardware"
    KERNEL = "kernel"
    PROPRIETARY = "proprietary"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionOwnershipDecision:
    """One canonical source-tree ownership conclusion."""

    requirement_kind: str
    source_identity: str
    domain: AndroidReconstructionOwnershipDomain

    requirement: object

    reason: str
    evidence: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            (
                "requirement_kind",
                self.requirement_kind,
            ),
            (
                "source_identity",
                self.source_identity,
            ),
            (
                "reason",
                self.reason,
            ),
        ):
            if not isinstance(
                value,
                str,
            ) or not value:
                raise ValueError(
                    f"{field_name} must be a "
                    "non-empty string"
                )

        if not isinstance(
            self.domain,
            AndroidReconstructionOwnershipDomain,
        ):
            raise TypeError(
                "domain must be an "
                "AndroidReconstructionOwnershipDomain"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )


@dataclass(frozen=True, slots=True)
class AndroidReconstructionOwnershipResult:
    """
    Complete first-class Reconstruction Ownership result.

    Ownership is intentionally sparse: only requirement families that
    genuinely need source-tree ownership are required to participate.
    """

    decisions: tuple[
        AndroidReconstructionOwnershipDecision,
        ...,
    ] = ()

    artifact_evidence: (
        AndroidReconstructionArtifactEvidenceInventory
        | None
    ) = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.decisions,
            tuple,
        ):
            raise TypeError(
                "decisions must be a tuple"
            )

        if (
            self.artifact_evidence is not None
            and not isinstance(
                self.artifact_evidence,
                AndroidReconstructionArtifactEvidenceInventory,
            )
        ):
            raise TypeError(
                "artifact_evidence must be an "
                "AndroidReconstructionArtifactEvidenceInventory "
                "or None"
            )

        if not all(
            isinstance(
                decision,
                AndroidReconstructionOwnershipDecision,
            )
            for decision in self.decisions
        ):
            raise TypeError(
                "decisions contains an invalid model"
            )

        keys = tuple(
            (
                decision.requirement_kind,
                decision.source_identity,
            )
            for decision in self.decisions
        )

        if len(keys) != len(set(keys)):
            raise ValueError(
                "Ownership decisions must preserve "
                "unique requirement identities"
            )

        if keys != tuple(sorted(keys)):
            raise ValueError(
                "Ownership decisions must use "
                "deterministic ordering"
            )

    def decision_for(
        self,
        *,
        requirement_kind: str,
        source_identity: str,
    ) -> (
        AndroidReconstructionOwnershipDecision
        | None
    ):
        for decision in self.decisions:
            if (
                decision.requirement_kind
                == requirement_kind
                and decision.source_identity
                == source_identity
            ):
                return decision

        return None

    @property
    def unresolved(self) -> tuple[
        AndroidReconstructionOwnershipDecision,
        ...,
    ]:
        return tuple(
            decision
            for decision in self.decisions
            if (
                decision.domain
                is AndroidReconstructionOwnershipDomain
                .UNRESOLVED
            )
        )
