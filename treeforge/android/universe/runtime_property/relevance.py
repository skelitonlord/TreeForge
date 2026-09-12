from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)

if TYPE_CHECKING:
    from treeforge.android.universe.init.service_reconciliation import (
        AndroidUniverseInitServiceResolution,
    )
    from treeforge.android.universe.init.source_applicability import (
        AndroidUniverseInitSourceApplicability,
    )


class AndroidUniverseRuntimePropertyRelevanceStatus(
    StrEnum
):
    """
    Canonical reconstruction relevance of one runtime-property requirement.
    """

    RECONSTRUCTION_REQUIRED = "reconstruction_required"
    COVERED_BY_OTHER_FAMILY = "covered_by_other_family"
    RUNTIME_INPUT = "runtime_input"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyRelevance:
    """
    Universe-owned reconstruction relevance for one concrete property.

    The exact canonical runtime-property requirement is retained so downstream
    stages consume the Universe conclusion without reinterpreting its evidence.

    ``covered_by_family`` identifies another canonical Universe family that
    owns the reconstruction concern when the runtime-property requirement
    contributes only cross-family evidence.
    """

    requirement: AndroidUniverseRuntimePropertyRequirement
    status: AndroidUniverseRuntimePropertyRelevanceStatus
    covered_by_family: str | None = None
    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseRuntimePropertyRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseRuntimePropertyRequirement"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRuntimePropertyRelevanceStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRuntimePropertyRelevanceStatus"
            )

        if (
            self.covered_by_family is not None
            and (
                not isinstance(
                    self.covered_by_family,
                    str,
                )
                or not self.covered_by_family
            )
        ):
            raise TypeError(
                "covered_by_family must be a non-empty string or None"
            )

        if (
            self.status
            is AndroidUniverseRuntimePropertyRelevanceStatus
            .COVERED_BY_OTHER_FAMILY
        ):
            if self.covered_by_family is None:
                raise ValueError(
                    "COVERED_BY_OTHER_FAMILY requires "
                    "covered_by_family"
                )

        elif self.covered_by_family is not None:
            raise ValueError(
                "covered_by_family is valid only for "
                "COVERED_BY_OTHER_FAMILY"
            )

        if (
            self.reason is not None
            and (
                not isinstance(
                    self.reason,
                    str,
                )
                or not self.reason
            )
        ):
            raise TypeError(
                "reason must be a non-empty string or None"
            )

    @property
    def requirement_id(
        self,
    ) -> str:
        return self.requirement.property_key


class AndroidUniverseRuntimePropertyRelevanceReconciler:
    """
    Reconcile runtime-property reconstruction relevance from canonical evidence.

    Concrete static declarations and observed runtime producers establish
    runtime-property reconstruction work.

    Android INIT service-state properties are covered by INIT when canonical
    effective-service reconciliation establishes the exact corresponding
    service. The relationship is architectural Android INIT behavior rather
    than device- or filename-specific policy.

    Consumer-only properties whose every exact INIT source is canonically
    ALTERNATIVE or UNREFERENCED are not applicable to the selected runtime.

    A requirement represented only by SELinux property_contexts is retained as
    runtime-property evidence, while ownership of reconstructing that source
    rule remains with the SELinux family.

    Remaining consumer-only properties are canonical runtime inputs when
    Universe has exhausted its modeled static/runtime producer families but
    retains an applicable or potentially applicable consumer.  The property
    identity therefore matters to reconstructed runtime logic, while no
    independent property source representation has been established for
    Reconstruction to emit.

    UNRESOLVED is reserved for cases where Universe cannot determine even this
    reconstruction boundary.
    """

    _INIT_SERVICE_PROPERTY_PREFIX = "init.svc."

    @staticmethod
    def _source_identity(
        init_action,
    ) -> str:
        from treeforge.android.universe.init.source_identity import (
            android_universe_init_source_identity,
        )

        return android_universe_init_source_identity(
            source_path=init_action.source_path,
            android_path=init_action.android_path,
            filesystem_source=(
                init_action.filesystem_source
            ),
        )

    @classmethod
    def reconcile(
        cls,
        *,
        requirements: tuple[
            AndroidUniverseRuntimePropertyRequirement,
            ...,
        ],
        init_service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ] = (),
        init_source_applicability: tuple[
            AndroidUniverseInitSourceApplicability,
            ...,
        ] = (),
    ) -> tuple[
        AndroidUniverseRuntimePropertyRelevance,
        ...,
    ]:
        from treeforge.android.universe.init.service_reconciliation import (
            AndroidUniverseInitServiceResolution,
        )
        from treeforge.android.universe.init.source_applicability import (
            AndroidUniverseInitSourceApplicability,
            AndroidUniverseInitSourceApplicabilityStatus,
        )

        inapplicable_consumer_source_statuses = frozenset({
            AndroidUniverseInitSourceApplicabilityStatus.ALTERNATIVE,
            AndroidUniverseInitSourceApplicabilityStatus.UNREFERENCED,
        })

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseRuntimePropertyRequirement,
            )
            for requirement in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseRuntimePropertyRequirement instances"
            )

        if not isinstance(
            init_service_resolutions,
            tuple,
        ):
            raise TypeError(
                "init_service_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseInitServiceResolution,
            )
            for resolution in init_service_resolutions
        ):
            raise TypeError(
                "init_service_resolutions must contain only "
                "AndroidUniverseInitServiceResolution instances"
            )

        if not isinstance(
            init_source_applicability,
            tuple,
        ):
            raise TypeError(
                "init_source_applicability must be a tuple"
            )

        if not all(
            isinstance(
                applicability,
                AndroidUniverseInitSourceApplicability,
            )
            for applicability in init_source_applicability
        ):
            raise TypeError(
                "init_source_applicability must contain only "
                "AndroidUniverseInitSourceApplicability instances"
            )

        applicability_by_source_identity = {
            applicability.source_identity: applicability
            for applicability in init_source_applicability
        }

        if (
            len(
                applicability_by_source_identity
            )
            != len(
                init_source_applicability
            )
        ):
            raise ValueError(
                "canonical INIT source applicability identities "
                "must be unique"
            )

        effective_service_names = frozenset(
            resolution.name
            for resolution in init_service_resolutions
            if (
                resolution.runtime_context.is_root
                and resolution.effective_services
            )
        )

        conclusions = []

        for requirement in requirements:
            #
            # Direct producer evidence is authoritative.
            #
            if (
                requirement.has_static_declaration
                or requirement.has_runtime_producer
            ):
                conclusion = (
                    AndroidUniverseRuntimePropertyRelevance(
                        requirement=requirement,
                        status=(
                            AndroidUniverseRuntimePropertyRelevanceStatus
                            .RECONSTRUCTION_REQUIRED
                        ),
                        reason=(
                            "Canonical Universe evidence contains a static "
                            "property declaration or observed runtime producer."
                        ),
                    )
                )

                conclusions.append(
                    conclusion
                )
                continue

            #
            # Android init publishes init.svc.<service> state for ordinary
            # services. Do not accept the namespace spelling by itself:
            # require an exact effective canonical service resolution.
            #
            property_key = requirement.property_key

            if property_key.startswith(
                cls._INIT_SERVICE_PROPERTY_PREFIX
            ):
                service_name = property_key[
                    len(
                        cls._INIT_SERVICE_PROPERTY_PREFIX
                    ):
                ]

                if (
                    service_name
                    and service_name
                    in effective_service_names
                ):
                    conclusion = (
                        AndroidUniverseRuntimePropertyRelevance(
                            requirement=requirement,
                            status=(
                                AndroidUniverseRuntimePropertyRelevanceStatus
                                .COVERED_BY_OTHER_FAMILY
                            ),
                            covered_by_family="init",
                            reason=(
                                "Canonical INIT service reconciliation "
                                "establishes an effective service named "
                                f"{service_name!r}; Android init owns the "
                                "generated init.svc.<service> lifecycle "
                                "property."
                            ),
                        )
                    )

                    conclusions.append(
                        conclusion
                    )
                    continue

            #
            # Determine applicability of the exact INIT consumer population.
            #
            consumer_actions = (
                tuple(
                    observation.init_action
                    for observation
                    in requirement.wait_for_prop_observations
                )
                + tuple(
                    observation.init_action
                    for observation
                    in requirement.trigger_observations
                )
            )

            consumer_source_statuses = []
            complete_consumer_applicability = bool(
                consumer_actions
            )

            for init_action in consumer_actions:
                source_identity = (
                    cls._source_identity(
                        init_action
                    )
                )

                applicability = (
                    applicability_by_source_identity.get(
                        source_identity
                    )
                )

                if applicability is None:
                    complete_consumer_applicability = False
                    break

                consumer_source_statuses.append(
                    applicability.status
                )

            if (
                complete_consumer_applicability
                and consumer_source_statuses
                and all(
                    status
                    in inapplicable_consumer_source_statuses
                    for status
                    in consumer_source_statuses
                )
            ):
                conclusion = (
                    AndroidUniverseRuntimePropertyRelevance(
                        requirement=requirement,
                        status=(
                            AndroidUniverseRuntimePropertyRelevanceStatus
                            .NOT_APPLICABLE
                        ),
                        reason=(
                            "Every canonical INIT consumer of this "
                            "producer-less runtime property belongs to an "
                            "INIT source classified ALTERNATIVE or "
                            "UNREFERENCED for the selected runtime."
                        ),
                    )
                )

            elif (
                requirement.has_property_context
                and not requirement.has_consumer
            ):
                conclusion = (
                    AndroidUniverseRuntimePropertyRelevance(
                        requirement=requirement,
                        status=(
                            AndroidUniverseRuntimePropertyRelevanceStatus
                            .COVERED_BY_OTHER_FAMILY
                        ),
                        covered_by_family="selinux",
                        reason=(
                            "This concrete property identity is established "
                            "only by SELinux property_contexts evidence; "
                            "reconstruction of that source rule belongs to "
                            "the SELinux family."
                        ),
                    )
                )

            elif requirement.has_consumer:
                conclusion = (
                    AndroidUniverseRuntimePropertyRelevance(
                        requirement=requirement,
                        status=(
                            AndroidUniverseRuntimePropertyRelevanceStatus
                            .RUNTIME_INPUT
                        ),
                        reason=(
                            "Canonical Universe preserves an applicable or "
                            "potentially applicable runtime-property consumer "
                            "after exhausting canonical static declarations "
                            "and modeled runtime producer evidence. The "
                            "property is therefore a runtime input to the "
                            "reconstructed consumer logic; no independent "
                            "property source representation is established "
                            "for Reconstruction to emit."
                        ),
                    )
                )

            else:
                conclusion = (
                    AndroidUniverseRuntimePropertyRelevance(
                        requirement=requirement,
                        status=(
                            AndroidUniverseRuntimePropertyRelevanceStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            "Canonical Universe cannot establish a static "
                            "declaration, modeled runtime producer, consumer "
                            "role, or other canonical reconstruction owner "
                            "for this runtime-property identity."
                        ),
                    )
                )

            conclusions.append(
                conclusion
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )
