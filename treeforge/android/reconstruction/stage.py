from __future__ import annotations

from treeforge.android.reconstruction.build_system.artifact import (
    AndroidReconstructionArtifactBuildClassifier,
)
from treeforge.android.reconstruction.build_system.source import (
    AndroidReconstructionSourceBuildProjector,
)
from treeforge.android.reconstruction.build_system.selinux import (
    AndroidReconstructionSelinuxBuildProjector,
)
from treeforge.android.reconstruction.build_system.package import (
    AndroidReconstructionPackageBuildProjector,
)
from treeforge.android.reconstruction.build_system.apex import (
    AndroidReconstructionApexBuildProjector,
)
from treeforge.android.reconstruction.build_system.classpath import (
    AndroidReconstructionClasspathBuildProjector,
)
from treeforge.android.reconstruction.build_system.boot import (
    AndroidReconstructionBootBuildProjector,
)
from treeforge.android.reconstruction.build_system.dtbo import (
    AndroidReconstructionDtboBuildProjector,
)
from treeforge.android.reconstruction.build_system.vbmeta import (
    AndroidReconstructionVbmetaBuildProjector,
)
from treeforge.android.reconstruction.build_system.elf import (
    AndroidReconstructionElfBuildPopulationProjector,
    AndroidReconstructionElfBuildProjector,
)
from treeforge.android.reconstruction.build_system.kernel_module import (
    AndroidReconstructionKernelModuleBuildProjector,
)
from treeforge.android.reconstruction.build_system.dependency import (
    AndroidReconstructionBuildDependencyValidator,
)
from treeforge.android.reconstruction.fstab.content import (
    AndroidReconstructionFstabContentSynthesizer,
)

from dataclasses import dataclass

from treeforge.android.reconstruction.init.reconstructor import (
    AndroidReconstructionInitReconstructor,
)
from treeforge.android.reconstruction.init.content import (
    AndroidReconstructionInitContentSynthesizer,
)
from treeforge.android.reconstruction.runtime_property.content import (
    AndroidReconstructionRuntimePropertyContentSynthesizer,
)
from treeforge.android.reconstruction.runtime_property.reconstructor import (
    AndroidReconstructionRuntimePropertyReconstructor,
)
from treeforge.android.reconstruction.fstab.reconstructor import (
    AndroidReconstructionFstabReconstructor,
)
from treeforge.android.reconstruction.ueventd.content import (
    AndroidReconstructionUeventdContentSynthesizer,
)
from treeforge.android.reconstruction.ueventd.reconstructor import (
    AndroidReconstructionUeventdReconstructor,
)
from treeforge.android.reconstruction.vintf.content import (
    AndroidReconstructionVintfContentSynthesizer,
)
from treeforge.android.reconstruction.vintf.reconstructor import (
    AndroidReconstructionVintfReconstructor,
)
from treeforge.android.reconstruction.selinux.content import (
    AndroidReconstructionSelinuxContentSynthesizer,
)
from treeforge.android.reconstruction.selinux.reconstructor import (
    AndroidReconstructionSelinuxReconstructor,
)

from treeforge.android.reconstruction.composition.relationship import (
    AndroidReconstructionCompositionProjector,
)

from treeforge.android.reconstruction.model import (
    AndroidReconstructionCoverage,
    AndroidReconstructionInput,
    AndroidReconstructionOutcome,
    AndroidReconstructionOutcomeStatus,
    AndroidReconstructionResult,
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction_planning.model import (
    AndroidReconstructionPlan,
    AndroidReconstructionPlanningDisposition,
)
from treeforge.android.runtime_linking.model import (
    AndroidRuntimeLinking,
)
from treeforge.android.partition.layout import (
    PartitionLayout,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionStage:
    """
    Canonical Planning -> Reconstruction boundary.

    The current foundation owns admission only. Family-specific semantic
    reconstruction will be added behind this boundary later.

    This stage does not:
    - inspect factory-image sources;
    - reinterpret Android Device Universe;
    - redo Reconstruction Planning;
    - infer source-tree ownership;
    - choose destinations or filenames;
    - render source files;
    - materialize Device Tree output.
    """

    def prepare(
        self,
        plan: AndroidReconstructionPlan,
        *,
        runtime_linking: AndroidRuntimeLinking,
        partition_layout: PartitionLayout | None = None,
    ) -> AndroidReconstructionInput:
        """
        Validate and deterministically admit one canonical Planning result.

        Known unresolved Planning outcomes are accepted canonical unknowns.
        Conflicts and unresolved outcomes not explicitly classified as known
        are rejected because Reconstruction must not silently guess through
        an upstream planning gap.
        """

        if not isinstance(
            plan,
            AndroidReconstructionPlan,
        ):
            raise TypeError(
                "plan must be an AndroidReconstructionPlan"
            )

        if not isinstance(
            runtime_linking,
            AndroidRuntimeLinking,
        ):
            raise TypeError(
                "runtime_linking must be an AndroidRuntimeLinking"
            )

        if (
            partition_layout is not None
            and not isinstance(
                partition_layout,
                PartitionLayout,
            )
        ):
            raise TypeError(
                "partition_layout must be a PartitionLayout or None"
            )

        universe = runtime_linking.universe

        if (
            len(
                plan.cross_family_relationships
            )
            != len(
                universe.cross_family_relationships
            )
            or not all(
                planned is canonical
                for planned, canonical
                in zip(
                    plan.cross_family_relationships,
                    universe.cross_family_relationships,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Reconstruction Planning must preserve exact canonical "
                "Universe cross-family relationship identity and order"
            )

        if (
            len(
                plan.cross_family_relationship_applicability
            )
            != len(
                universe.cross_family_relationship_applicability
            )
            or not all(
                planned is canonical
                for planned, canonical
                in zip(
                    plan.cross_family_relationship_applicability,
                    universe.cross_family_relationship_applicability,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Reconstruction Planning must preserve exact canonical "
                "Universe relationship-applicability identity and order"
            )

        canonical_runtime_elf_requirements = {
            id(requirement)
            for requirement
            in runtime_linking.universe.elf_requirements
        }

        for obligation in plan.obligations:
            if obligation.requirement_kind != "elf":
                continue

            if (
                id(obligation.requirement)
                not in canonical_runtime_elf_requirements
            ):
                raise ValueError(
                    "Reconstruction Planning ELF obligation does "
                    "not preserve exact Runtime Linking Universe "
                    "ELF requirement identity: "
                    f"{obligation.obligation_id}"
                )

        obligation_by_id = {
            obligation.obligation_id: obligation
            for obligation in plan.obligations
        }

        if len(obligation_by_id) != len(plan.obligations):
            raise ValueError(
                "Planning obligations must have unique identities"
            )

        outcome_by_id = {
            outcome.obligation_id: outcome
            for outcome in plan.outcomes
        }

        if len(outcome_by_id) != len(plan.outcomes):
            raise ValueError(
                "Planning outcomes must have unique obligation identities"
            )

        if set(outcome_by_id) != set(obligation_by_id):
            missing = sorted(
                set(obligation_by_id)
                - set(outcome_by_id)
            )
            unexpected = sorted(
                set(outcome_by_id)
                - set(obligation_by_id)
            )

            raise ValueError(
                "Planning must provide exactly one outcome for every "
                "obligation before Reconstruction: "
                f"missing={missing!r}, unexpected={unexpected!r}"
            )

        work_items: list[
            AndroidReconstructionWorkItem
        ] = []

        not_applicable_outcomes = []
        known_unresolved_outcomes = []

        for obligation in plan.obligations:
            outcome = outcome_by_id[
                obligation.obligation_id
            ]

            if outcome.obligation is None:
                raise ValueError(
                    "Planning outcome must preserve its canonical "
                    f"obligation: {outcome.obligation_id}"
                )

            if (
                outcome.obligation.obligation_id
                != obligation.obligation_id
            ):
                raise ValueError(
                    "Planning outcome obligation identity mismatch: "
                    f"{outcome.obligation_id}"
                )

            disposition = outcome.disposition

            if (
                disposition
                is AndroidReconstructionPlanningDisposition.PLANNED
            ):
                work_items.append(
                    AndroidReconstructionWorkItem(
                        obligation_id=obligation.obligation_id,
                        requirement_kind=obligation.requirement_kind,
                        source_identity=obligation.source_identity,
                        work_kind=(
                            AndroidReconstructionWorkKind.RECONSTRUCT
                        ),
                        obligation=obligation,
                        planning_outcome=outcome,
                    )
                )
                continue

            if (
                disposition
                is AndroidReconstructionPlanningDisposition.PRESERVED
            ):
                work_items.append(
                    AndroidReconstructionWorkItem(
                        obligation_id=obligation.obligation_id,
                        requirement_kind=obligation.requirement_kind,
                        source_identity=obligation.source_identity,
                        work_kind=(
                            AndroidReconstructionWorkKind.PRESERVE
                        ),
                        obligation=obligation,
                        planning_outcome=outcome,
                        preserved_artifact_id=(
                            outcome.preserved_artifact_id
                        ),
                    )
                )
                continue

            if (
                disposition
                is AndroidReconstructionPlanningDisposition.NOT_APPLICABLE
            ):
                not_applicable_outcomes.append(
                    outcome
                )
                continue

            if (
                disposition
                is AndroidReconstructionPlanningDisposition.UNRESOLVED
            ):
                if not outcome.known_unresolved:
                    raise ValueError(
                        "Reconstruction cannot admit an unclassified "
                        "Planning unresolved outcome: "
                        f"{outcome.obligation_id}: {outcome.reason}"
                    )

                known_unresolved_outcomes.append(
                    outcome
                )
                continue

            if (
                disposition
                is AndroidReconstructionPlanningDisposition.CONFLICTING
            ):
                raise ValueError(
                    "Reconstruction cannot admit a conflicting "
                    "Planning outcome: "
                    f"{outcome.obligation_id}: {outcome.reason}"
                )

            raise ValueError(
                "unsupported Reconstruction Planning disposition: "
                f"{disposition!r}"
            )

        work_items_tuple = tuple(
            sorted(
                work_items,
                key=lambda item: (
                    item.requirement_kind,
                    item.source_identity,
                    item.obligation_id,
                    item.work_kind.value,
                ),
            )
        )

        not_applicable_tuple = tuple(
            sorted(
                not_applicable_outcomes,
                key=lambda outcome: outcome.obligation_id,
            )
        )

        known_unresolved_tuple = tuple(
            sorted(
                known_unresolved_outcomes,
                key=lambda outcome: outcome.obligation_id,
            )
        )

        reconstruction_work_count = sum(
            item.work_kind
            is AndroidReconstructionWorkKind.RECONSTRUCT
            for item in work_items_tuple
        )

        preservation_work_count = sum(
            item.work_kind
            is AndroidReconstructionWorkKind.PRESERVE
            for item in work_items_tuple
        )

        coverage = AndroidReconstructionCoverage(
            required=len(plan.obligations),
            reconstruction_work=reconstruction_work_count,
            preservation_work=preservation_work_count,
            not_applicable=len(not_applicable_tuple),
            known_unresolved=len(known_unresolved_tuple),
        )

        return AndroidReconstructionInput(
            plan=plan,
            runtime_linking=runtime_linking,
            work_items=work_items_tuple,
            not_applicable_outcomes=not_applicable_tuple,
            known_unresolved_outcomes=known_unresolved_tuple,
            coverage=coverage,
            partition_layout=partition_layout,
        )

    def reconstruct(
        self,
        reconstruction_input: AndroidReconstructionInput,
    ) -> AndroidReconstructionResult:
        """
        Execute the Reconstruction families currently implemented.

        INIT Reconstruction consumes the canonical source grouping already
        established by Planning.

        PRESERVE work resolves directly to its exact canonical artifact
        identity.

        Other RECONSTRUCT work remains pending until its owning family
        reconstructor exists. No outcome is fabricated for unimplemented
        Reconstruction work.
        """

        if not isinstance(
            reconstruction_input,
            AndroidReconstructionInput,
        ):
            raise TypeError(
                "reconstruction_input must be an "
                "AndroidReconstructionInput"
            )

        init_source_representations = (
            AndroidReconstructionInitReconstructor
            .reconstruct(
                reconstruction_input
            )
        )

        init_source_contents = (
            AndroidReconstructionInitContentSynthesizer
            .synthesize_all(
                init_source_representations
            )
        )


        runtime_property_representations = (
            AndroidReconstructionRuntimePropertyReconstructor
            .reconstruct(
                reconstruction_input
            )
        )

        runtime_property_source_contents = (
            AndroidReconstructionRuntimePropertyContentSynthesizer
            .synthesize_all(
                runtime_property_representations
            )
        )


        fstab_source_representations = (
            AndroidReconstructionFstabReconstructor
            .reconstruct(
                reconstruction_input
            )
        )

        fstab_source_contents = (
            AndroidReconstructionFstabContentSynthesizer
            .synthesize_all(
                fstab_source_representations
            )
        )


        ueventd_source_representations = (
            AndroidReconstructionUeventdReconstructor
            .reconstruct(
                reconstruction_input
            )
        )

        ueventd_source_contents = (
            AndroidReconstructionUeventdContentSynthesizer
            .synthesize_all(
                ueventd_source_representations
            )
        )


        vintf_document_representations = (
            AndroidReconstructionVintfReconstructor
            .reconstruct(
                reconstruction_input
            )
        )

        vintf_source_contents = (
            AndroidReconstructionVintfContentSynthesizer
            .synthesize_all(
                vintf_document_representations
            )
        )


        selinux_source_representations = (
            AndroidReconstructionSelinuxReconstructor
            .reconstruct(
                reconstruction_input
            )
        )

        selinux_source_contents = (
            AndroidReconstructionSelinuxContentSynthesizer
            .synthesize_all(
                selinux_source_representations
            )
        )

        representation_by_obligation_id: dict[
            str,
            str,
        ] = {}

        for representation in (
            init_source_representations
        ):
            for obligation_id in (
                representation.contributing_obligation_ids
            ):
                if (
                    obligation_id
                    in representation_by_obligation_id
                ):
                    raise ValueError(
                        "Reconstruction obligation maps to "
                        "multiple INIT source representations: "
                        f"{obligation_id}"
                    )

                representation_by_obligation_id[
                    obligation_id
                ] = (
                    representation.representation_id
                )

        for representation in (
            runtime_property_representations
        ):
            obligation_id = (
                representation.obligation_id
            )

            if (
                obligation_id
                in representation_by_obligation_id
            ):
                raise ValueError(
                    "Reconstruction obligation maps to "
                    "multiple representations: "
                    f"{obligation_id}"
                )

            representation_by_obligation_id[
                obligation_id
            ] = (
                representation.representation_id
            )

        for representation in (
            fstab_source_representations
        ):
            for obligation_id in (
                representation.contributing_obligation_ids
            ):
                if (
                    obligation_id
                    in representation_by_obligation_id
                ):
                    raise ValueError(
                        "Reconstruction obligation maps to "
                        "multiple representations: "
                        f"{obligation_id}"
                    )

                representation_by_obligation_id[
                    obligation_id
                ] = (
                    representation.representation_id
                )

        for representation in (
            ueventd_source_representations
        ):
            for obligation_id in (
                representation.contributing_obligation_ids
            ):
                if (
                    obligation_id
                    in representation_by_obligation_id
                ):
                    raise ValueError(
                        "Reconstruction obligation maps to "
                        "multiple representations: "
                        f"{obligation_id}"
                    )

                representation_by_obligation_id[
                    obligation_id
                ] = (
                    representation.representation_id
                )

        for representation in (
            vintf_document_representations
        ):
            obligation_id = (
                representation.obligation_id
            )

            if (
                obligation_id
                in representation_by_obligation_id
            ):
                raise ValueError(
                    "Reconstruction obligation maps to "
                    "multiple representations: "
                    f"{obligation_id}"
                )

            representation_by_obligation_id[
                obligation_id
            ] = (
                representation.representation_id
            )

        for representation in (
            selinux_source_representations
        ):
            obligation_id = (
                representation.obligation_id
            )

            if (
                obligation_id
                in representation_by_obligation_id
            ):
                raise ValueError(
                    "Reconstruction obligation maps to "
                    "multiple representations: "
                    f"{obligation_id}"
                )

            representation_by_obligation_id[
                obligation_id
            ] = (
                representation.representation_id
            )

        preserved_artifact_build_representations = tuple(
            AndroidReconstructionArtifactBuildClassifier.classify(
                item
            )
            for item
            in reconstruction_input.work_items
            if (
                item.work_kind
                is AndroidReconstructionWorkKind.PRESERVE
                and item.requirement_kind == "artifact"
            )
        )

        source_build_representations = (
            AndroidReconstructionSourceBuildProjector.project(
                (
                    *init_source_contents,
                    *fstab_source_contents,
                    *ueventd_source_contents,
                    *vintf_source_contents,
                )
            )
        )

        selinux_build_representations = (
            AndroidReconstructionSelinuxBuildProjector.project(
                selinux_source_representations,
                selinux_source_contents,
            )
        )

        apk_requirement = getattr(
            reconstruction_input.runtime_linking.universe,
            "apk_requirement",
            None,
        )

        package_build_representations = ()

        if apk_requirement is not None:
            packages = getattr(
                apk_requirement,
                "packages",
                None,
            )

            if not isinstance(
                packages,
                tuple,
            ):
                raise TypeError(
                    "canonical Universe APK requirement packages "
                    "must be a tuple"
                )

            package_build_representations = (
                AndroidReconstructionPackageBuildProjector.project(
                    packages,
                    existing_build_representations=(
                        preserved_artifact_build_representations
                    ),
                )
            )

        artifact_build_representations = tuple(
            sorted(
                (
                    *preserved_artifact_build_representations,
                    *source_build_representations,
                    *selinux_build_representations,
                    *package_build_representations,
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        if apk_requirement is not None:
            overlay_resolutions = getattr(
                apk_requirement,
                "overlay_resolutions",
                None,
            )

            if not isinstance(
                overlay_resolutions,
                tuple,
            ):
                raise TypeError(
                    "canonical Universe APK overlay resolutions "
                    "must be a tuple"
                )

            artifact_build_representations = (
                AndroidReconstructionPackageBuildProjector
                .apply_overlay_dependencies(
                    packages=packages,
                    overlay_resolutions=(
                        overlay_resolutions
                    ),
                    build_representations=(
                        artifact_build_representations
                    ),
                )
            )

        apex_build_representations = (
            AndroidReconstructionApexBuildProjector.project(
                reconstruction_input
                .runtime_linking
                .universe
                .apex_requirements,
                existing_build_representations=(
                    artifact_build_representations
                ),
            )
        )

        artifact_build_representations = tuple(
            sorted(
                (
                    *artifact_build_representations,
                    *apex_build_representations,
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        boot_requirements = (
            reconstruction_input
            .runtime_linking
            .universe
            .boot_requirements
        )

        boot_image_compositions = (
            AndroidReconstructionBootBuildProjector
            .project_compositions(
                boot_requirements
            )
        )

        boot_build_representations = (
            AndroidReconstructionBootBuildProjector.project(
                boot_requirements,
                existing_build_representations=(
                    artifact_build_representations
                ),
            )
        )

        artifact_build_representations = tuple(
            sorted(
                (
                    *artifact_build_representations,
                    *boot_build_representations,
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        dtbo_requirements = (
            reconstruction_input
            .runtime_linking
            .universe
            .dtbo_requirements
        )

        dtbo_container = (
            AndroidReconstructionDtboBuildProjector
            .project_container(
                dtbo_requirements
            )
        )

        dtbo_build_representations = (
            AndroidReconstructionDtboBuildProjector.project(
                dtbo_requirements,
                existing_build_representations=(
                    artifact_build_representations
                ),
            )
        )

        artifact_build_representations = tuple(
            sorted(
                (
                    *artifact_build_representations,
                    *dtbo_build_representations,
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        vbmeta_build_representations = (
            AndroidReconstructionVbmetaBuildProjector.project(
                reconstruction_input
                .runtime_linking
                .universe
                .vbmeta_requirements,
                existing_build_representations=(
                    artifact_build_representations
                ),
            )
        )

        artifact_build_representations = tuple(
            sorted(
                (
                    *artifact_build_representations,
                    *vbmeta_build_representations,
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        classpath_requirement = (
            reconstruction_input
            .runtime_linking
            .universe
            .classpath_requirement
        )

        if classpath_requirement is not None:
            classpath_build_representations = (
                AndroidReconstructionClasspathBuildProjector.project(
                    classpath_requirement,
                    existing_build_representations=(
                        artifact_build_representations
                    ),
                )
            )

            artifact_build_representations = tuple(
                sorted(
                    (
                        *artifact_build_representations,
                        *classpath_build_representations,
                    ),
                    key=lambda representation: (
                        representation.representation_id
                    ),
                )
            )

        kernel_module_requirement = (
            reconstruction_input
            .runtime_linking
            .universe
            .kernel_module_requirement
        )

        if kernel_module_requirement is not None:
            kernel_module_build_representations = (
                AndroidReconstructionKernelModuleBuildProjector.project(
                    kernel_module_requirement,
                    reconstruction_input
                    .runtime_linking
                    .universe
                    .artifact_requirements,
                    existing_build_representations=(
                        artifact_build_representations
                    ),
                )
            )

            artifact_build_representations = tuple(
                sorted(
                    (
                        *artifact_build_representations,
                        *kernel_module_build_representations,
                    ),
                    key=lambda representation: (
                        representation.representation_id
                    ),
                )
            )

            kernel_module_config_build_representations = (
                AndroidReconstructionKernelModuleBuildProjector
                .project_configurations(
                    kernel_module_requirement,
                    reconstruction_input
                    .runtime_linking
                    .universe
                    .artifact_requirements,
                    existing_build_representations=(
                        artifact_build_representations
                    ),
                )
            )

            artifact_build_representations = tuple(
                sorted(
                    (
                        *artifact_build_representations,
                        *kernel_module_config_build_representations,
                    ),
                    key=lambda representation: (
                        representation.representation_id
                    ),
                )
            )

        elf_build_representations = (
            AndroidReconstructionElfBuildPopulationProjector.project(
                reconstruction_input
                .runtime_linking
                .universe
                .elf_requirements,
                reconstruction_input
                .runtime_linking
                .universe
                .artifact_requirements,
                existing_build_representations=(
                    artifact_build_representations
                ),
            )
        )

        artifact_build_representations = tuple(
            sorted(
                (
                    *artifact_build_representations,
                    *elf_build_representations,
                ),
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        elf_build_semantics = (
            AndroidReconstructionElfBuildProjector.project(
                reconstruction_input,
                artifact_build_representations,
                runtime_linking_traversals=(
                    reconstruction_input
                    .runtime_linking
                    .linker_elf_dependency_traversals
                ),
            )
        )

        artifact_build_representations = (
            AndroidReconstructionElfBuildProjector
            .apply_resolved_dependencies(
                elf_semantics=elf_build_semantics,
                build_representations=(
                    artifact_build_representations
                ),
            )
        )

        if kernel_module_requirement is not None:
            artifact_build_representations = (
                AndroidReconstructionKernelModuleBuildProjector
                .apply_hard_dependencies(
                    kernel_module_requirement,
                    reconstruction_input
                    .runtime_linking
                    .universe
                    .artifact_requirements,
                    build_representations=(
                        artifact_build_representations
                    ),
                )
            )

        AndroidReconstructionBuildDependencyValidator.validate(
            artifact_build_representations
        )

        outcomes: list[
            AndroidReconstructionOutcome
        ] = []

        for item in (
            reconstruction_input.work_items
        ):
            if (
                item.work_kind
                is AndroidReconstructionWorkKind.PRESERVE
            ):
                outcomes.append(
                    AndroidReconstructionOutcome(
                        obligation_id=(
                            item.obligation_id
                        ),
                        status=(
                            AndroidReconstructionOutcomeStatus
                            .PRESERVED
                        ),
                        preserved_artifact_id=(
                            item.preserved_artifact_id
                        ),
                    )
                )

                continue

            representation_id = (
                representation_by_obligation_id.get(
                    item.obligation_id
                )
            )

            if representation_id is None:
                continue

            outcomes.append(
                AndroidReconstructionOutcome(
                    obligation_id=(
                        item.obligation_id
                    ),
                    status=(
                        AndroidReconstructionOutcomeStatus
                        .RECONSTRUCTED
                    ),
                    representation_ids=(
                        representation_id,
                    ),
                )
            )

        result = AndroidReconstructionResult(
            reconstruction_input=(
                reconstruction_input
            ),
            init_source_representations=(
                init_source_representations
            ),
            init_source_contents=(
                init_source_contents
            ),
            runtime_property_representations=(
                runtime_property_representations
            ),
            runtime_property_source_contents=(
                runtime_property_source_contents
            ),
            fstab_source_representations=(
                fstab_source_representations
            ),
            fstab_source_contents=(
                fstab_source_contents
            ),
            ueventd_source_representations=(
                ueventd_source_representations
            ),
            ueventd_source_contents=(
                ueventd_source_contents
            ),
            vintf_document_representations=(
                vintf_document_representations
            ),
            vintf_source_contents=(
                vintf_source_contents
            ),
            selinux_source_representations=(
                selinux_source_representations
            ),
            selinux_source_contents=(
                selinux_source_contents
            ),
            boot_image_compositions=(
                boot_image_compositions
            ),
            dtbo_container=(
                dtbo_container
            ),
            artifact_build_representations=(
                artifact_build_representations
            ),
            elf_build_semantics=(
                elf_build_semantics
            ),
            outcomes=tuple(
                sorted(
                    outcomes,
                    key=lambda outcome: (
                        outcome.obligation_id
                    ),
                )
            ),
        )

        composition_relationships = (
            AndroidReconstructionCompositionProjector.project(
                result
            )
        )

        result = AndroidReconstructionResult(
            reconstruction_input=(
                result.reconstruction_input
            ),
            init_source_representations=(
                result.init_source_representations
            ),
            init_source_contents=(
                result.init_source_contents
            ),
            runtime_property_representations=(
                result.runtime_property_representations
            ),
            runtime_property_source_contents=(
                result.runtime_property_source_contents
            ),
            fstab_source_representations=(
                result.fstab_source_representations
            ),
            fstab_source_contents=(
                result.fstab_source_contents
            ),
            ueventd_source_representations=(
                result.ueventd_source_representations
            ),
            ueventd_source_contents=(
                result.ueventd_source_contents
            ),
            vintf_document_representations=(
                result.vintf_document_representations
            ),
            vintf_source_contents=(
                result.vintf_source_contents
            ),
            selinux_source_representations=(
                result.selinux_source_representations
            ),
            selinux_source_contents=(
                result.selinux_source_contents
            ),
            boot_image_compositions=(
                result.boot_image_compositions
            ),
            dtbo_container=(
                result.dtbo_container
            ),
            artifact_build_representations=(
                result.artifact_build_representations
            ),
            elf_build_semantics=(
                result.elf_build_semantics
            ),
            composition_relationships=(
                composition_relationships
            ),
            outcomes=(
                result.outcomes
            ),
        )

        expected_init_ids = set(
            representation_by_obligation_id
        )

        reconstructed_init_ids = {
            outcome.obligation_id
            for outcome in result.outcomes
            if (
                outcome.status
                is AndroidReconstructionOutcomeStatus.RECONSTRUCTED
            )
        }

        if (
            reconstructed_init_ids
            != expected_init_ids
        ):
            raise ValueError(
                "INIT Reconstruction outcomes must correspond "
                "exactly to represented INIT Reconstruction work"
            )

        return result

