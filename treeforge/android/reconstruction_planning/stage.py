from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlan,
    AndroidReconstructionPlanningCompleteness,
    AndroidReconstructionPlanningDisposition,
    AndroidReconstructionPlanningObligation,
    AndroidReconstructionPlanningOutcome,
    AndroidReconstructionPlanningCoverage,
)
from treeforge.android.reconstruction_planning.artifact.planner import (
    AndroidReconstructionArtifactPlanner,
)
from treeforge.android.reconstruction_planning.runtime_property.planner import (
    AndroidReconstructionRuntimePropertyPlanner,
)
from treeforge.android.reconstruction_planning.fstab.planner import (
    AndroidReconstructionFstabPlanner,
)
from treeforge.android.reconstruction_planning.elf.planner import (
    AndroidReconstructionElfPlanner,
)
from treeforge.android.reconstruction_planning.kernel.planner import (
    AndroidReconstructionKernelPlanner,
)
from treeforge.android.reconstruction_planning.init.action_planner import (
    AndroidReconstructionInitActionPlanner,
)
from treeforge.android.reconstruction_planning.init.import_planner import (
    AndroidReconstructionInitImportPlanner,
)
from treeforge.android.reconstruction_planning.init.service_planner import (
    AndroidReconstructionInitServicePlanner,
)
from treeforge.android.reconstruction_planning.init.source_grouping import (
    AndroidReconstructionInitSourceGrouper,
)
from treeforge.android.reconstruction_planning.ueventd.planner import (
    AndroidReconstructionUeventdPlanner,
)
from treeforge.android.reconstruction_planning.selinux.planner import (
    AndroidReconstructionSelinuxPlanner,
)
from treeforge.android.reconstruction_planning.boot.planner import (
    AndroidReconstructionBootPlanner,
)
from treeforge.android.reconstruction_planning.bootloader.planner import (
    AndroidReconstructionBootloaderPlanner,
)
from treeforge.android.reconstruction_planning.sflb.planner import (
    AndroidReconstructionSflbPlanner,
)
from treeforge.android.reconstruction_planning.vbmeta.planner import (
    AndroidReconstructionVbmetaPlanner,
)
from treeforge.android.reconstruction_planning.bmp.planner import (
    AndroidReconstructionBmpPlanner,
)
from treeforge.android.reconstruction_planning.dtbo.planner import (
    AndroidReconstructionDtboPlanner,
)
from treeforge.android.reconstruction_planning.apex.planner import (
    AndroidReconstructionApexPlanner,
)
from treeforge.android.reconstruction_planning.vintf.planner import (
    AndroidReconstructionVintfPlanner,
)
from treeforge.android.reconstruction_ownership.model import (
    AndroidReconstructionOwnershipResult,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionPlanningStage:
    """Build the canonical reconstruction plan from AndroidDeviceUniverse.

    This stage owns the transition from Universe semantics into reconstruction
    obligations. It does not parse sources, inspect factory images, or perform
    reconstruction itself.
    """

    _REQUIREMENT_FIELDS: tuple[tuple[str, str], ...] = (
        ("artifact", "artifact_requirements"),
        ("runtime_property", "runtime_property_requirements"),
        ("fstab", "fstab_requirements"),
        ("ueventd", "ueventd_requirements"),
        ("vintf", "vintf_requirements"),
        ("selinux", "selinux_requirements"),
        ("boot", "boot_requirements"),
        ("apex", "apex_requirements"),
        ("elf", "elf_requirements"),
        ("kernel", "kernel_requirements"),
        ("vbmeta", "vbmeta_requirements"),
        ("bootloader", "bootloader_requirements"),
        ("sflb", "sflb_requirements"),
        ("bmp", "bmp_requirements"),
        ("dtbo", "dtbo_requirements"),
        ("init_import", "init_import_requirements"),
        ("init_service", "init_service_requirements"),
        ("init_action", "init_action_requirements"),
    )

    def plan(
        self,
        universe: Any,
        *,
        ownership: (
            AndroidReconstructionOwnershipResult
            | None
        ) = None,
    ) -> AndroidReconstructionPlan:
        """Create a deterministic initial plan from one canonical Universe."""

        if (
            ownership is not None
            and not isinstance(
                ownership,
                AndroidReconstructionOwnershipResult,
            )
        ):
            raise TypeError(
                "ownership must be an "
                "AndroidReconstructionOwnershipResult or None"
            )

        obligations = tuple(
            self._collect_obligations(universe)
        )

        runtime_property_relevance = getattr(
            universe,
            "runtime_property_relevance",
            (),
        )

        runtime_property_relevance_by_id = {
            relevance.requirement_id: relevance
            for relevance in runtime_property_relevance
        }

        init_source_applicability = getattr(
            universe,
            "init_source_applicability",
            (),
        )

        init_source_groups = (
            AndroidReconstructionInitSourceGrouper.group(
                obligations,
                source_applicability=(
                    init_source_applicability
                ),
            )
        )

        init_source_dispositions = {
            obligation.obligation_id: group.disposition
            for group in init_source_groups
            for obligation in group.obligations
        }

        outcomes = tuple(
            self._plan_obligation(
                obligation,
                ownership=ownership,
                init_source_dispositions=(
                    init_source_dispositions
                ),
                runtime_property_relevance_by_id=(
                    runtime_property_relevance_by_id
                ),
            )
            for obligation in obligations
        )

        self._validate_init_source_groups(
            init_source_groups
        )

        preserved_count = sum(
            outcome.disposition
            is AndroidReconstructionPlanningDisposition.PRESERVED
            for outcome in outcomes
        )

        not_applicable_count = sum(
            outcome.disposition
            is AndroidReconstructionPlanningDisposition.NOT_APPLICABLE
            for outcome in outcomes
        )

        unresolved_count = sum(
            outcome.disposition
            is AndroidReconstructionPlanningDisposition.UNRESOLVED
            for outcome in outcomes
        )

        planned_count = sum(
            outcome.disposition
            is AndroidReconstructionPlanningDisposition.PLANNED
            for outcome in outcomes
        )

        conflicting_count = sum(
            outcome.disposition
            is AndroidReconstructionPlanningDisposition.CONFLICTING
            for outcome in outcomes
        )

        coverage = AndroidReconstructionPlanningCoverage(
            required=len(obligations),
            planned=planned_count,
            preserved=preserved_count,
            not_applicable=not_applicable_count,
            unresolved=unresolved_count,
            conflicting=conflicting_count,
        )

        completeness = AndroidReconstructionPlanningCompleteness(
            coverage=coverage,
            blocking_unresolved_count=unresolved_count,
            blocking_conflict_count=conflicting_count,
        )

        fstab_source_contexts = (
            universe.fstab_source_contexts
        )

        ueventd_source_contexts = (
            universe.ueventd_source_contexts
        )

        if not isinstance(
            fstab_source_contexts,
            tuple,
        ):
            raise TypeError(
                "canonical Universe fstab_source_contexts "
                "must be a tuple"
            )

        cross_family_relationships = (
            universe.cross_family_relationships
        )

        cross_family_relationship_applicability = (
            universe.cross_family_relationship_applicability
        )

        if not isinstance(
            cross_family_relationships,
            tuple,
        ):
            raise TypeError(
                "canonical Universe cross_family_relationships "
                "must be a tuple"
            )

        if not isinstance(
            cross_family_relationship_applicability,
            tuple,
        ):
            raise TypeError(
                "canonical Universe "
                "cross_family_relationship_applicability "
                "must be a tuple"
            )

        return AndroidReconstructionPlan(
            ownership=ownership,
            obligations=obligations,
            init_source_groups=init_source_groups,
            outcomes=outcomes,
            cross_family_relationships=(
                cross_family_relationships
            ),
            cross_family_relationship_applicability=(
                cross_family_relationship_applicability
            ),
            fstab_source_contexts=(
                fstab_source_contexts
            ),
            ueventd_source_contexts=(
                ueventd_source_contexts
            ),
            completeness=completeness,
        )

    @staticmethod
    def _plan_obligation(
        obligation: AndroidReconstructionPlanningObligation,
        *,
        ownership: (
            AndroidReconstructionOwnershipResult
            | None
        ) = None,
        init_source_dispositions: dict[str, object] | None = None,
        runtime_property_relevance_by_id: dict[str, object] | None = None,
    ) -> AndroidReconstructionPlanningOutcome:
        if obligation.requirement_kind == "init_import":
            source_disposition = (
                init_source_dispositions.get(
                    obligation.obligation_id
                )
                if init_source_dispositions is not None
                else None
            )

            return AndroidReconstructionInitImportPlanner.plan(
                obligation,
                source_disposition=source_disposition,
            )

        if obligation.requirement_kind == "init_action":
            source_disposition = (
                init_source_dispositions.get(
                    obligation.obligation_id
                )
                if init_source_dispositions is not None
                else None
            )

            return AndroidReconstructionInitActionPlanner.plan(
                obligation,
                source_disposition=source_disposition,
            )

        if obligation.requirement_kind == "init_service":
            source_disposition = (
                init_source_dispositions.get(
                    obligation.obligation_id
                )
                if init_source_dispositions is not None
                else None
            )

            return AndroidReconstructionInitServicePlanner.plan(
                obligation,
                source_disposition=source_disposition,
            )

        if obligation.requirement_kind == "runtime_property":
            relevance = (
                runtime_property_relevance_by_id.get(
                    obligation.source_identity
                )
                if runtime_property_relevance_by_id is not None
                else None
            )

            if relevance is None:
                return AndroidReconstructionPlanningOutcome(
                    obligation_id=obligation.obligation_id,
                    disposition=(
                        AndroidReconstructionPlanningDisposition.UNRESOLVED
                    ),
                    obligation=obligation,
                    reason=(
                        "Canonical Universe contains no runtime-property "
                        "relevance conclusion for this requirement."
                    ),
                )

            return AndroidReconstructionRuntimePropertyPlanner.plan(
                obligation,
                relevance=relevance,
            )

        if obligation.requirement_kind == "artifact":
            ownership_decision = (
                ownership.decision_for(
                    requirement_kind="artifact",
                    source_identity=(
                        obligation.source_identity
                    ),
                )
                if ownership is not None
                else None
            )

            return AndroidReconstructionArtifactPlanner.plan(
                obligation,
                ownership=ownership_decision,
            )

        planners = {
            "fstab": AndroidReconstructionFstabPlanner,
            "elf": AndroidReconstructionElfPlanner,
            "kernel": AndroidReconstructionKernelPlanner,
            "ueventd": AndroidReconstructionUeventdPlanner,
            "selinux": AndroidReconstructionSelinuxPlanner,
            "boot": AndroidReconstructionBootPlanner,
            "bootloader": AndroidReconstructionBootloaderPlanner,
            "vbmeta": AndroidReconstructionVbmetaPlanner,
            "sflb": AndroidReconstructionSflbPlanner,
            "bmp": AndroidReconstructionBmpPlanner,
            "dtbo": AndroidReconstructionDtboPlanner,
            "apex": AndroidReconstructionApexPlanner,
            "vintf": AndroidReconstructionVintfPlanner,
        }

        planner = planners.get(
            obligation.requirement_kind
        )

        if planner is not None:
            return planner.plan(
                obligation
            )

        return AndroidReconstructionPlanningOutcome(
            obligation_id=obligation.obligation_id,
            disposition=(
                AndroidReconstructionPlanningDisposition.UNRESOLVED
            ),
            obligation=obligation,
            reason=(
                "No reconstruction family planner has been "
                f"implemented for {obligation.requirement_kind}."
            ),
        )

    @staticmethod
    def _validate_init_source_groups(
        init_source_groups: tuple,
    ) -> None:
        """
        Validate canonical INIT source grouping before final plan assembly.

        Grouping preserves canonical source identity and consumes
        Universe-owned applicability/effective-service conclusions.
        Source-tree ownership, destination, strategy, and source synthesis
        remain Reconstruction concerns established by later capabilities.
        """

        source_identities = tuple(
            group.source_identity
            for group in init_source_groups
        )

        if len(
            source_identities
        ) != len(
            set(source_identities)
        ):
            raise ValueError(
                "duplicate canonical INIT source group identity"
            )

        obligation_ids = tuple(
            obligation.obligation_id
            for group in init_source_groups
            for obligation in group.obligations
        )

        if len(
            obligation_ids
        ) != len(
            set(obligation_ids)
        ):
            raise ValueError(
                "INIT obligation appears in multiple source groups"
            )

    def _collect_obligations(
        self,
        universe: Any,
    ) -> Iterable[AndroidReconstructionPlanningObligation]:
        collected: list[AndroidReconstructionPlanningObligation] = []

        for requirement_kind, field_name in self._REQUIREMENT_FIELDS:
            requirements = getattr(universe, field_name, ())

            for requirement in requirements:
                source_identity = self._source_identity(
                    requirement,
                    requirement_kind,
                )

                obligation_id = (
                    f"{requirement_kind}:{source_identity}"
                )

                universe_context = (
                    self._universe_context(
                        universe=universe,
                        requirement=requirement,
                        requirement_kind=requirement_kind,
                    )
                )

                collected.append(
                    AndroidReconstructionPlanningObligation(
                        obligation_id=obligation_id,
                        requirement=requirement,
                        requirement_kind=requirement_kind,
                        source_identity=source_identity,
                        universe_context=universe_context,
                    )
                )

        collected.sort(
            key=lambda obligation: (
                obligation.requirement_kind,
                obligation.source_identity,
                obligation.obligation_id,
            )
        )

        seen: set[str] = set()

        for obligation in collected:
            if obligation.obligation_id in seen:
                raise ValueError(
                    "duplicate reconstruction planning obligation "
                    f"identity: {obligation.obligation_id}"
                )
            seen.add(obligation.obligation_id)

        return collected

    @staticmethod
    def _universe_context(
        *,
        universe: Any,
        requirement: Any,
        requirement_kind: str,
    ) -> tuple[object, ...]:
        """
        Preserve canonical Universe-owned side context for one requirement.

        Context selection is identity-based. Reconstruction Planning does
        not derive new semantics here; it only carries already-established
        Universe conclusions across the stage boundary.

        Families without canonical side context return an empty tuple.
        """

        if requirement_kind == "ueventd":
            requirement_id = getattr(
                requirement,
                "requirement_id",
                None,
            )

            if (
                not isinstance(
                    requirement_id,
                    str,
                )
                or not requirement_id
            ):
                raise ValueError(
                    "canonical Universe UEVENTD requirement must "
                    "provide requirement_id"
                )

            reconciliation = getattr(
                universe,
                "ueventd_reconciliation",
                None,
            )

            if reconciliation is None:
                raise ValueError(
                    "canonical Universe UEVENTD reconciliation "
                    "is unavailable"
                )

            conclusion = (
                reconciliation.conclusion_for_requirement(
                    requirement_id
                )
            )

            if conclusion is None:
                raise ValueError(
                    "canonical Universe must provide exactly one "
                    "UEVENTD reconciliation conclusion for each "
                    "UEVENTD requirement"
                )

            if conclusion.requirement is not requirement:
                raise ValueError(
                    "UEVENTD reconciliation must retain the exact "
                    "canonical Universe requirement identity"
                )

            return (
                conclusion,
            )

        if requirement_kind == "selinux":
            requirement_id = getattr(
                requirement,
                "requirement_id",
                None,
            )

            if (
                not isinstance(
                    requirement_id,
                    str,
                )
                or not requirement_id
            ):
                raise ValueError(
                    "canonical Universe SELinux requirement must "
                    "provide requirement_id"
                )

            matching_conclusions = tuple(
                conclusion
                for conclusion in getattr(
                    universe,
                    "selinux_applicability",
                    (),
                )
                if (
                    conclusion.requirement_id
                    == requirement_id
                )
            )

            if len(matching_conclusions) != 1:
                raise ValueError(
                    "canonical Universe must provide exactly one "
                    "SELinux applicability conclusion for each "
                    "SELinux requirement"
                )

            return matching_conclusions

        if requirement_kind == "vintf":
            requirement_id = getattr(
                requirement,
                "requirement_id",
                None,
            )

            if (
                not isinstance(
                    requirement_id,
                    str,
                )
                or not requirement_id
            ):
                raise ValueError(
                    "canonical Universe VINTF requirement must "
                    "provide requirement_id"
                )

            vintf_applicability = getattr(
                universe,
                "vintf_applicability",
                None,
            )

            if vintf_applicability is None:
                raise ValueError(
                    "canonical Universe VINTF applicability "
                    "is unavailable"
                )

            matching_conclusions = tuple(
                conclusion
                for conclusion
                in vintf_applicability.document_applicability
                if (
                    conclusion.requirement_id
                    == requirement_id
                )
            )

            if len(matching_conclusions) != 1:
                raise ValueError(
                    "canonical Universe must provide exactly one "
                    "VINTF document applicability conclusion for "
                    "each VINTF requirement"
                )

            return matching_conclusions

        if requirement_kind == "fstab":
            requirement_id = getattr(
                requirement,
                "requirement_id",
                None,
            )

            if (
                not isinstance(
                    requirement_id,
                    str,
                )
                or not requirement_id
            ):
                raise ValueError(
                    "canonical Universe Fstab requirement must "
                    "provide requirement_id"
                )

            matching_conclusions = tuple(
                conclusion
                for conclusion in getattr(
                    universe,
                    "fstab_applicability_conclusions",
                    (),
                )
                if (
                    conclusion.requirement_id
                    == requirement_id
                )
            )

            if len(matching_conclusions) != 1:
                raise ValueError(
                    "canonical Universe must provide exactly one "
                    "Fstab applicability conclusion for each "
                    "Fstab requirement"
                )

            return matching_conclusions

        if requirement_kind == "vbmeta":
            topology = getattr(
                universe,
                "avb_topology",
                None,
            )

            if topology is None:
                return ()

            if not any(
                topology_requirement is requirement
                for topology_requirement
                in topology.requirements
            ):
                raise ValueError(
                    "AVB topology must contain the exact Universe "
                    "VBMeta requirement supplied to Reconstruction"
                )

            authentications = tuple(
                authentication
                for authentication
                in topology.authentications
                if authentication.owner is requirement
            )

            outgoing_chains = tuple(
                chain
                for chain in topology.chains
                if chain.owner is requirement
            )

            incoming_chains = tuple(
                chain
                for chain in topology.chains
                if chain.target is requirement
            )

            return (
                authentications,
                outgoing_chains,
                incoming_chains,
                topology,
            )

        if requirement_kind == "dtbo":
            population = getattr(
                universe,
                "dtbo_population",
                None,
            )

            if population is None:
                return ()

            matching_entries = tuple(
                entry
                for entry in population.entries
                if entry.requirement is requirement
            )

            matching_variants = tuple(
                variant
                for variant in population.variants
                if variant.requirement is requirement
            )

            if len(matching_entries) != 1:
                raise ValueError(
                    "DTBO Universe population must contain exactly one "
                    "entry for each Reconstruction requirement"
                )

            if len(matching_variants) != 1:
                raise ValueError(
                    "DTBO Universe population must contain exactly one "
                    "variant for each Reconstruction requirement"
                )

            return (
                matching_entries[0],
                matching_variants[0],
                population,
            )

        if requirement_kind == "init_import":
            matching_resolutions = tuple(
                resolution
                for resolution
                in getattr(
                    universe,
                    "init_import_resolutions",
                    (),
                )
                if resolution.requirement is requirement
            )

            if len(matching_resolutions) > 1:
                raise ValueError(
                    "canonical Universe INIT Import requirement "
                    "must not have multiple resolutions"
                )

            return matching_resolutions

        if requirement_kind == "init_service":
            matching_resolutions = tuple(
                resolution
                for resolution
                in getattr(
                    universe,
                    "init_service_resolutions",
                    (),
                )
                if any(
                    declaration is requirement
                    for declaration
                    in resolution.declarations
                )
            )

            if len(matching_resolutions) > 1:
                raise ValueError(
                    "canonical Universe INIT Service requirement "
                    "must not belong to multiple resolutions"
                )

            return matching_resolutions

        return ()

    @staticmethod
    def _source_identity(
        requirement: Any,
        requirement_kind: str,
    ) -> str:
        """
        Return canonical identity already exposed by a Universe requirement.

        Planning does not manufacture identity. Prefer explicit canonical
        identity properties owned by the requirement itself.

        Canonical requirement-specific identity belongs to Universe models.
        Planning consumes those public identity surfaces rather than
        rediscovering source structure.
        """

        for attribute_name in (
            "requirement_id",
            "property_key",
            "identity_key",
            "partition_name",
        ):
            identity = getattr(
                requirement,
                attribute_name,
                None,
            )

            if (
                isinstance(identity, str)
                and identity
            ):
                return identity

        # Compatibility for canonical partition-backed requirements that
        # expose only a partition object rather than partition_name.
        partition = getattr(
            requirement,
            "partition",
            None,
        )

        visited_partition_ids: set[int] = set()

        while partition is not None:
            object_id = id(
                partition
            )

            if object_id in visited_partition_ids:
                raise ValueError(
                    "canonical partition association contains a cycle "
                    "while resolving source identity: "
                    f"{requirement_kind}"
                )

            visited_partition_ids.add(
                object_id
            )

            for attribute_name in (
                "partition_name",
                "name",
            ):
                identity = getattr(
                    partition,
                    attribute_name,
                    None,
                )

                if (
                    isinstance(identity, str)
                    and identity
                ):
                    return identity

            partition = getattr(
                partition,
                "partition",
                None,
            )

        raise ValueError(
            "Universe requirement has no canonical source identity: "
            f"{requirement_kind} "
            f"(type={type(requirement).__name__})"
        )
