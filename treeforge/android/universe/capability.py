from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.vintf.applicability import (
    AndroidUniverseVintfApplicability,
)
from treeforge.android.universe.vintf.document import (
    AndroidUniverseVintfDocumentKind,
    AndroidUniverseVintfDocumentSide,
)
from treeforge.android.universe.vintf.hal import (
    AndroidUniverseVintfHalRequirement,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)


class AndroidUniverseDeviceCapability(
    StrEnum,
):
    """
    Generic device capabilities proven by canonical Universe evidence.

    These are semantic device conclusions. They are deliberately independent
    of Android build-system/product makefile policy.
    """

    CELLULAR = "cellular"


class AndroidUniverseDeviceCapabilityStatus(
    StrEnum,
):
    """
    Canonical state of one device capability.

    ABSENT requires explicit negative canonical evidence. Mere lack of
    positive evidence remains UNKNOWN.
    """

    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseDeviceCapabilityEvidence:
    """
    One exact VINTF observation proving a device capability.

    Both the canonical VINTF document requirement and the exact interpreted
    HAL requirement remain attached by identity.
    """

    document: AndroidUniverseVintfDocumentRequirement
    hal: AndroidUniverseVintfHalRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.document,
            AndroidUniverseVintfDocumentRequirement,
        ):
            raise TypeError(
                "document must be an "
                "AndroidUniverseVintfDocumentRequirement"
            )

        if not isinstance(
            self.hal,
            AndroidUniverseVintfHalRequirement,
        ):
            raise TypeError(
                "hal must be an AndroidUniverseVintfHalRequirement"
            )

        if not any(
            candidate is self.hal
            for candidate in self.document.semantics.hals
        ):
            raise ValueError(
                "hal must preserve exact identity from document semantics"
            )

    @property
    def evidence_id(
        self,
    ) -> str:
        return (
            f"{self.document.requirement_id}:"
            f"hal:{self.hal.name}:"
            f"{self.hal.format.value}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseDeviceCapabilityScopeEvidence:
    """
    Canonical evidence that one installed VINTF document participates in the
    authoritative device-side capability declaration surface.

    The document must be an ACTIVE DEVICE MANIFEST.  This evidence does not
    itself assert presence or absence of any specific HAL.  Instead, the
    complete active device-manifest surface establishes the canonical scope
    within which implementation HAL presence or absence may be interpreted.
    """

    document: AndroidUniverseVintfDocumentRequirement
    applicability: AndroidUniverseRequirementApplicability

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.document,
            AndroidUniverseVintfDocumentRequirement,
        ):
            raise TypeError(
                "document must be an "
                "AndroidUniverseVintfDocumentRequirement"
            )

        if not isinstance(
            self.applicability,
            AndroidUniverseRequirementApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidUniverseRequirementApplicability"
            )

        if (
            self.applicability.requirement_id
            != self.document.requirement_id
        ):
            raise ValueError(
                "capability scope applicability must preserve exact "
                "VINTF document requirement identity"
            )

        semantics = self.document.semantics

        if (
            semantics.kind
            is not AndroidUniverseVintfDocumentKind.MANIFEST
            or semantics.side
            is not AndroidUniverseVintfDocumentSide.DEVICE
        ):
            raise ValueError(
                "capability scope evidence must reference a DEVICE MANIFEST"
            )

        if (
            self.applicability.status
            is not AndroidUniverseApplicabilityStatus.ACTIVE
        ):
            raise ValueError(
                "capability scope evidence must reference an ACTIVE "
                "VINTF document"
            )

    @property
    def evidence_id(
        self,
    ) -> str:
        return (
            f"{self.document.requirement_id}:"
            "active-device-manifest"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseDeviceCapabilityConclusion:
    """
    Canonical conclusion for one generic device capability.
    """

    capability: AndroidUniverseDeviceCapability
    status: AndroidUniverseDeviceCapabilityStatus

    evidence: tuple[
        AndroidUniverseDeviceCapabilityEvidence,
        ...,
    ] = ()

    scope_evidence: tuple[
        AndroidUniverseDeviceCapabilityScopeEvidence,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.capability,
            AndroidUniverseDeviceCapability,
        ):
            raise TypeError(
                "capability must be an "
                "AndroidUniverseDeviceCapability"
            )

        if not isinstance(
            self.status,
            AndroidUniverseDeviceCapabilityStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseDeviceCapabilityStatus"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDeviceCapabilityEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniverseDeviceCapabilityEvidence instances"
            )

        evidence_ids = tuple(
            item.evidence_id
            for item in self.evidence
        )

        if evidence_ids != tuple(
            sorted(
                evidence_ids
            )
        ):
            raise ValueError(
                "device capability evidence must use canonical order"
            )

        if len(
            evidence_ids
        ) != len(
            set(
                evidence_ids
            )
        ):
            raise ValueError(
                "device capability evidence must be unique"
            )

        if not isinstance(
            self.scope_evidence,
            tuple,
        ):
            raise TypeError(
                "scope_evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDeviceCapabilityScopeEvidence,
            )
            for item in self.scope_evidence
        ):
            raise TypeError(
                "scope_evidence must contain only "
                "AndroidUniverseDeviceCapabilityScopeEvidence instances"
            )

        scope_evidence_ids = tuple(
            item.evidence_id
            for item in self.scope_evidence
        )

        if scope_evidence_ids != tuple(
            sorted(
                scope_evidence_ids
            )
        ):
            raise ValueError(
                "device capability scope evidence must use canonical order"
            )

        if len(
            scope_evidence_ids
        ) != len(
            set(
                scope_evidence_ids
            )
        ):
            raise ValueError(
                "device capability scope evidence must be unique"
            )

        if (
            self.status
            is AndroidUniverseDeviceCapabilityStatus.PRESENT
        ):
            if not self.evidence:
                raise ValueError(
                    "present device capability requires positive evidence"
                )

            if not self.scope_evidence:
                raise ValueError(
                    "present device capability requires canonical scope "
                    "evidence"
                )

        if (
            self.status
            is AndroidUniverseDeviceCapabilityStatus.ABSENT
        ):
            if self.evidence:
                raise ValueError(
                    "absent device capability must not carry positive "
                    "evidence"
                )

            if not self.scope_evidence:
                raise ValueError(
                    "absent device capability requires canonical scope "
                    "evidence"
                )

        if (
            self.status
            is AndroidUniverseDeviceCapabilityStatus.UNKNOWN
        ):
            if self.evidence:
                raise ValueError(
                    "unknown device capability must not carry positive "
                    "evidence"
                )

            if self.scope_evidence:
                raise ValueError(
                    "unknown device capability must not carry canonical "
                    "scope evidence"
                )


class AndroidUniverseDeviceCapabilityReconciler:
    """
    Derive generic device capabilities from canonical Universe evidence.

    Cellular capability is derived only from the authoritative ACTIVE
    DEVICE MANIFEST surface.

    Presence is proven when that surface declares at least one core Android
    cellular radio implementation HAL.

    Absence is proven only when at least one ACTIVE DEVICE MANIFEST establishes
    the canonical device declaration scope and the complete active scope
    contains none of the core cellular radio implementation HALs.

    Framework compatibility matrices, product compatibility matrices,
    vendor extension HALs, package presence, RIL libraries, build flags, and
    other support artifacts are intentionally not sufficient by themselves.

    If no ACTIVE DEVICE MANIFEST scope is available, lack of positive evidence
    remains UNKNOWN.
    """

    _CELLULAR_IMPLEMENTATION_HAL_NAMES = frozenset(
        {
            "android.hardware.radio",
            "android.hardware.radio.data",
            "android.hardware.radio.messaging",
            "android.hardware.radio.modem",
            "android.hardware.radio.network",
            "android.hardware.radio.sim",
            "android.hardware.radio.voice",
        }
    )

    def reconcile(
        self,
        *,
        requirements: tuple[
            AndroidUniverseVintfDocumentRequirement,
            ...,
        ],
        applicability: AndroidUniverseVintfApplicability,
    ) -> tuple[
        AndroidUniverseDeviceCapabilityConclusion,
        ...,
    ]:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfDocumentRequirement,
            )
            for item in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseVintfDocumentRequirement instances"
            )

        if not isinstance(
            applicability,
            AndroidUniverseVintfApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidUniverseVintfApplicability"
            )

        applicability_by_requirement_id = {
            item.requirement_id: item
            for item in applicability.document_applicability
        }

        requirement_ids = {
            item.requirement_id
            for item in requirements
        }

        if set(
            applicability_by_requirement_id
        ) != requirement_ids:
            raise ValueError(
                "VINTF applicability must cover exactly the supplied "
                "VINTF requirements"
            )

        cellular_evidence = []
        cellular_scope_evidence = []

        for requirement in requirements:
            semantics = requirement.semantics

            if (
                semantics.kind
                is not AndroidUniverseVintfDocumentKind.MANIFEST
                or semantics.side
                is not AndroidUniverseVintfDocumentSide.DEVICE
            ):
                continue

            document_applicability = (
                applicability_by_requirement_id[
                    requirement.requirement_id
                ]
            )

            if (
                document_applicability.status
                is not AndroidUniverseApplicabilityStatus.ACTIVE
            ):
                continue

            cellular_scope_evidence.append(
                AndroidUniverseDeviceCapabilityScopeEvidence(
                    document=requirement,
                    applicability=document_applicability,
                )
            )

            for hal in semantics.hals:
                if (
                    hal.name
                    not in self._CELLULAR_IMPLEMENTATION_HAL_NAMES
                ):
                    continue

                cellular_evidence.append(
                    AndroidUniverseDeviceCapabilityEvidence(
                        document=requirement,
                        hal=hal,
                    )
                )

        canonical_cellular_evidence = tuple(
            sorted(
                cellular_evidence,
                key=lambda item: (
                    item.evidence_id
                ),
            )
        )

        canonical_cellular_scope_evidence = tuple(
            sorted(
                cellular_scope_evidence,
                key=lambda item: (
                    item.evidence_id
                ),
            )
        )

        if canonical_cellular_evidence:
            cellular_status = (
                AndroidUniverseDeviceCapabilityStatus.PRESENT
            )
        elif canonical_cellular_scope_evidence:
            cellular_status = (
                AndroidUniverseDeviceCapabilityStatus.ABSENT
            )
        else:
            cellular_status = (
                AndroidUniverseDeviceCapabilityStatus.UNKNOWN
            )

        return (
            AndroidUniverseDeviceCapabilityConclusion(
                capability=(
                    AndroidUniverseDeviceCapability.CELLULAR
                ),
                status=cellular_status,
                evidence=canonical_cellular_evidence,
                scope_evidence=(
                    canonical_cellular_scope_evidence
                ),
            ),
        )
