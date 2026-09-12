from __future__ import annotations

from collections import defaultdict

from treeforge.android.properties.scope import (
    AndroidPropertyScope,
)
from treeforge.android.universe.properties.conclusion import (
    AndroidUniverseConclusionStatus,
    AndroidUniverseFactConclusion,
)
from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)


class AndroidUniversePropertyReconciler:
    """
    Reconcile property evidence into canonical Universe conclusions.

    This owns generic Android property reconciliation semantics.

    It does not perform majority voting, scope precedence, version-specific
    policy, or device-specific overrides.
    """

    _EMPTY_VALUE_FACTS = frozenset(
        {
            "supported_cpu_abis",
            "supported_32_bit_cpu_abis",
            "supported_64_bit_cpu_abis",
        }
    )

    _DEVICE_IDENTITY_FACTS = frozenset(
        {
            "device_codename",
            "manufacturer",
            "product_model",
            "product_name",
            "product_brand",
        }
    )

    _DEVICE_IDENTITY_SCOPES = frozenset(
        {
            AndroidPropertyScope.PRODUCT,
            AndroidPropertyScope.SYSTEM_EXT,
            AndroidPropertyScope.VENDOR,
            AndroidPropertyScope.ODM,
            AndroidPropertyScope.ODM_DLKM,
        }
    )

    _SCOPED_CONSENSUS_FACTS = frozenset(
        {
            "android_version",
            "sdk_level",
            "build_date_utc",
            "build_fingerprint",
            "build_id",
            "build_incremental",
            "build_tags",
            "build_type",
            "debuggable",
        }
    )

    def reconcile(
        self,
        evidence: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseFactConclusion,
        ...,
    ]:
        if not isinstance(
            evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniversePropertyEvidence,
            )
            for item in evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniversePropertyEvidence"
            )

        grouped: dict[
            str,
            list[
                AndroidUniversePropertyEvidence
            ],
        ] = defaultdict(
            list
        )

        for item in evidence:
            grouped[
                item.fact.fact
            ].append(
                item
            )

        return tuple(
            self._reconcile_fact(
                fact=fact,
                observations=tuple(
                    grouped[fact]
                ),
            )
            for fact in sorted(
                grouped
            )
        )

    def _reconcile_fact(
        self,
        *,
        fact: str,
        observations: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
    ) -> AndroidUniverseFactConclusion:
        eligible = self._eligible_evidence(
            fact=fact,
            observations=observations,
        )

        values = tuple(
            sorted(
                {
                    item.fact.value
                    for item in eligible
                    if (
                        item.fact.value
                        or fact in self._EMPTY_VALUE_FACTS
                    )
                }
            )
        )

        if not values:
            return AndroidUniverseFactConclusion(
                fact=fact,
                status=(
                    AndroidUniverseConclusionStatus
                    .UNRESOLVED
                ),
                value=None,
                evidence=eligible,
            )

        if len(values) == 1:
            return AndroidUniverseFactConclusion(
                fact=fact,
                status=(
                    AndroidUniverseConclusionStatus
                    .AGREED
                ),
                value=values[0],
                evidence=eligible,
            )

        return AndroidUniverseFactConclusion(
            fact=fact,
            status=(
                AndroidUniverseConclusionStatus
                .CONFLICTING
            ),
            value=None,
            evidence=eligible,
        )

    def _eligible_evidence(
        self,
        *,
        fact: str,
        observations: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
    ) -> tuple[
        AndroidUniversePropertyEvidence,
        ...,
    ]:
        unscoped = tuple(
            item
            for item in observations
            if item.fact.scope is None
        )

        if unscoped:
            return unscoped

        if fact in self._DEVICE_IDENTITY_FACTS:
            return tuple(
                item
                for item in observations
                if (
                    item.fact.scope
                    in self._DEVICE_IDENTITY_SCOPES
                )
            )

        if fact in self._SCOPED_CONSENSUS_FACTS:
            return tuple(
                item
                for item in observations
                if item.fact.scope is not None
            )

        return ()