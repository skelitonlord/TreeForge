from __future__ import annotations

from treeforge.android.parsing.classpath.model import (
    AndroidClasspathKind,
)

from treeforge.core.knowledge_application import (
    KnowledgeApplicationStage,
)

from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathJarApplicabilityStatus,
)

import io
import os
import shutil
import sys
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path, PurePosixPath

import typer

from treeforge.android.universe.bootloader import (
    AndroidUniverseBootloaderRequirementFamily,
)
from treeforge.android.universe.init.import_resolution import (
    android_init_inapplicable_source_paths,
)
from treeforge.android.universe.properties.conclusion import (
    AndroidUniverseConclusionStatus,
)
from treeforge.android.universe.relationships import (
    AndroidUniverseApkVintfStructuralProviderRelationship,
    AndroidUniverseArtRuntimeClasspathRelationship,
    AndroidUniverseFirstStageKernelModuleLoadingRelationship,
    AndroidUniverseArtifactFulfillmentStatus,
    AndroidUniverseInitExecutableArtifactRelationship,
    AndroidUniverseInitOnRestartPropertyCommandRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
)

def build_device_universe_report(
    *,
    result,
    factory_image: Path | None,
    universe_root: Path,
    generic_only: bool,
) -> str:
    """Build the canonical Android Device Universe report.

    This is the single shared Universe reporting implementation consumed by
    both the Universe and Reconstruction CLIs.  It does not execute Universe
    or Reconstruction Planning; it only renders the already-canonical
    Universe result.
    """


    universe_result = (
        result.universe
    )

    parsing = (
        universe_result.parsing
    )

    evidence = (
        universe_result.property_evidence
    )

    conclusions = (
        universe_result.conclusions
    )

    fstab_requirements = (
        universe_result.fstab_requirements
    )

    fstab_source_contexts = (
        universe_result.fstab_source_contexts
    )

    fstab_source_contexts_with_unparsed_lines = tuple(
        source_context
        for source_context in fstab_source_contexts
        if source_context.unparsed_lines
    )

    fstab_preserved_unparsed_line_count = sum(
        len(source_context.unparsed_lines)
        for source_context in fstab_source_contexts
    )

    init_service_requirements = (
        universe_result.init_service_requirements
    )

    init_semantic_counts = Counter()

    init_uninterpreted_option_counts = Counter()

    for requirement in init_service_requirements:
        semantics = requirement.semantics

        if semantics.classes is not None:
            init_semantic_counts["classes"] += 1

        if semantics.user is not None:
            init_semantic_counts["user"] += 1

        if semantics.groups is not None:
            init_semantic_counts["groups"] += 1

        if semantics.capabilities is not None:
            init_semantic_counts["capabilities"] += 1

        if semantics.seclabel is not None:
            init_semantic_counts["seclabel"] += 1

        if semantics.disabled:
            init_semantic_counts["disabled"] += 1

        if semantics.oneshot:
            init_semantic_counts["oneshot"] += 1

        if semantics.critical is not None:
            init_semantic_counts["critical"] += 1

        for option in semantics.uninterpreted_options:
            init_uninterpreted_option_counts[
                option.keyword
            ] += 1

    fstab_applicability = (
        universe_result.fstab_applicability
    )

    fstab_applicability_conclusions = (
        universe_result.fstab_applicability_conclusions
    )

    fstab_applicability_with_evidence = tuple(
        item
        for item in fstab_applicability
        if item.evidence
    )

    fstab_applicability_resolved = tuple(
        item
        for item in fstab_applicability
        if item.resolved_path is not None
    )

    fstab_applicability_selector_backed = tuple(
        item
        for item in fstab_applicability
        if item.selector_key is not None
    )

    fstab_applicability_without_evidence = tuple(
        item
        for item in fstab_applicability
        if not item.evidence
    )

    fstab_applicability_status_counts = Counter(
        item.status.value
        for item in fstab_applicability_conclusions
    )

    fact_counts = Counter(
        item.fact.fact
        for item in evidence
    )

    partition_counts = Counter(
        item.model_source.partition_name
        for item in evidence
    )

    conclusion_status_counts = Counter(
        item.status.value
        for item in conclusions
    )

    conclusion_by_fact = {
        item.fact: item
        for item in conclusions
    }

    parsed_fstab_declarations = sum(
        source.entry_count
        for source in parsing.filesystem.fstabs
    )

    unknown_fstab_flag_counts = Counter(
        flag
        for requirement in fstab_requirements
        for flag in requirement.unknown_fs_mgr_flags
    )

    fstab_boolean_counts = {
        "logical": sum(
            1
            for item in fstab_requirements
            if item.logical
        ),
        "slotselect": sum(
            1
            for item in fstab_requirements
            if item.slot_select
        ),
        "slotselect_other": sum(
            1
            for item in fstab_requirements
            if item.slot_select_other
        ),
        "first_stage_mount": sum(
            1
            for item in fstab_requirements
            if item.first_stage_mount
        ),
        "latemount": sum(
            1
            for item in fstab_requirements
            if item.late_mount
        ),
        "wait": sum(
            1
            for item in fstab_requirements
            if item.wait
        ),
        "check": sum(
            1
            for item in fstab_requirements
            if item.check
        ),
        "formattable": sum(
            1
            for item in fstab_requirements
            if item.formattable
        ),
        "quota": sum(
            1
            for item in fstab_requirements
            if item.quota
        ),
    }

    avb_requirement_count = sum(
        1
        for item in fstab_requirements
        if item.avb is not None
    )

    avb_hashtree_digest_requirement_count = sum(
        1
        for item in fstab_requirements
        if item.avb_hashtree_digest is not None
    )

    encrypted_requirement_count = sum(
        1
        for item in fstab_requirements
        if (
            item.file_encryption is not None
            or item.metadata_encryption is not None
        )
    )

    zram_requirement_count = sum(
        1
        for item in fstab_requirements
        if item.zram_size is not None
    )

    source_paths = {
        (
            item.model_source.partition_name,
            item.model_source.android_path.as_posix(),
        )
        for item in evidence
    }

    knowledge_resolution = (
        universe_result.knowledge_resolution
    )

    report_buffer = io.StringIO()

    with redirect_stdout(
        report_buffer
    ):
        typer.echo()
        typer.echo(
            "Android Device Universe completed successfully."
        )

        typer.echo()
        if factory_image is not None:
            typer.echo(
                f"Factory image: {factory_image}"
            )
        else:
            typer.echo(
                "Universe input: canonical Parsing snapshot"
            )
        typer.echo(
            f"Device Universe workspace: {universe_root}"
        )

        typer.echo()
        typer.echo(
            "Upstream pipeline:"
        )

        for stage_name in (
            "Discovery",
            "Partition Layout",
            "Extraction",
            "Partition Inventory",
            "Filesystem Metadata",
            "Parsing",
            "Android Device Universe",
        ):
            typer.echo(
                f"  {stage_name}: complete"
            )

        typer.echo()
        typer.echo(
            "Canonical handoff:"
        )
        typer.echo(
            (
                "  Parsing identity preserved: "
                f"{universe_result.parsing is result.parsing_snapshot.parsing}"
            )
        )
        typer.echo(
            (
                "  Knowledge resolution: "
                + (
                    "absent"
                    if knowledge_resolution is None
                    else "preserved"
                )
            )
        )

        typer.echo(
            "  Knowledge application:"
        )
        typer.echo(
            (
                "    Universe: "
                + (
                    "ON"
                    if (
                        result
                        .request
                        .knowledge_application_policy
                        .enabled_for(
                            KnowledgeApplicationStage.UNIVERSE
                        )
                    )
                    else "OFF"
                )
            )
        )

        if knowledge_resolution is not None:
            typer.echo(
                (
                    "  Knowledge roots: "
                    f"{len(knowledge_resolution.root_selections)}"
                )
            )

            for root_selection in (
                knowledge_resolution.root_selections
            ):
                typer.echo(
                    (
                        "    "
                        f"{root_selection.module_id}: "
                        f"{root_selection.source.value}"
                    )
                )

            typer.echo(
                (
                    "  Knowledge modules: "
                    f"{len(knowledge_resolution.module_ids)}"
                )
            )

            for module_id in (
                knowledge_resolution.module_ids
            ):
                typer.echo(
                    f"    {module_id}"
                )

        parsing_boundary = (
            universe_result.parsing_boundary
        )

        typer.echo()
        typer.echo(
            "Parsing -> Universe boundary:"
        )
        typer.echo(
            (
                "  Parsing populations: "
                f"{len(parsing_boundary.dispositions)}"
            )
        )
        typer.echo(
            (
                "  Semantically consumed: "
                f"{len(parsing_boundary.semantically_consumed)}"
            )
        )
        typer.echo(
            (
                "  Deliberately pass-through: "
                f"{len(parsing_boundary.deliberately_pass_through)}"
            )
        )
        typer.echo(
            (
                "  Downstream-owned: "
                f"{len(parsing_boundary.downstream_owned)}"
            )
        )
        typer.echo(
            (
                "  Unresolved: "
                f"{len(parsing_boundary.unresolved)}"
            )
        )

        if parsing_boundary.unresolved:
            typer.echo(
                "  Unresolved populations:"
            )

            for disposition in (
                parsing_boundary.unresolved
            ):
                typer.echo(
                    (
                        "    "
                        f"{disposition.population_name}"
                    )
                )

                if disposition.reason:
                    typer.echo(
                        (
                            "      "
                            f"{disposition.reason}"
                        )
                    )

        if parsing_boundary.deliberately_pass_through:
            typer.echo(
                "  Deliberately pass-through populations:"
            )

            for disposition in (
                parsing_boundary.deliberately_pass_through
            ):
                typer.echo(
                    (
                        "    "
                        f"{disposition.population_name}"
                    )
                )

                if disposition.reason:
                    typer.echo(
                        (
                            "      "
                            f"{disposition.reason}"
                        )
                    )

        if parsing_boundary.downstream_owned:
            typer.echo(
                "  Downstream-owned populations:"
            )

            for disposition in (
                parsing_boundary.downstream_owned
            ):
                typer.echo(
                    (
                        "    "
                        f"{disposition.population_name}"
                    )
                )

                if disposition.reason:
                    typer.echo(
                        (
                            "      "
                            f"{disposition.reason}"
                        )
                    )

        filesystem_entries = (
            universe_result.filesystem_entry_requirements
        )

        filesystem_entry_type_counts = Counter(
            requirement.metadata_entry.entry_type.value
            for requirement
            in filesystem_entries.requirements
        )

        filesystem_entry_disposition_counts = Counter(
            requirement.disposition.value
            for requirement
            in filesystem_entries.requirements
        )

        filesystem_entry_role_counts = Counter(
            requirement.deployment_role.value
            for requirement
            in filesystem_entries.requirements
        )

        artifact_backed_entries = tuple(
            requirement
            for requirement
            in filesystem_entries.requirements
            if requirement.artifact_requirement is not None
        )

        typer.echo()
        typer.echo(
            "Filesystem-entry Universe coverage:"
        )
        typer.echo(
            (
                "  Canonical filesystem entries: "
                f"{len(filesystem_entries.requirements)}"
            )
        )
        typer.echo(
            (
                "  Regular-file Artifact links: "
                f"{len(artifact_backed_entries)}"
            )
        )
        typer.echo(
            (
                "  Artifact linkage matches regular-file inventory: "
                f"{len(artifact_backed_entries) == len(universe_result.artifact_requirements.requirements)}"
            )
        )
        typer.echo(
            (
                "  Unresolved filesystem entries: "
                f"{len(filesystem_entries.unresolved)}"
            )
        )

        typer.echo(
            "  Entries by type:"
        )

        for entry_type, count in sorted(
            filesystem_entry_type_counts.items()
        ):
            typer.echo(
                f"    {entry_type}: {count}"
            )

        typer.echo(
            "  Entries by disposition:"
        )

        for disposition, count in sorted(
            filesystem_entry_disposition_counts.items()
        ):
            typer.echo(
                f"    {disposition}: {count}"
            )

        typer.echo(
            "  Entries by deployment role:"
        )

        for role, count in sorted(
            filesystem_entry_role_counts.items()
        ):
            typer.echo(
                f"    {role}: {count}"
            )

        if filesystem_entries.unresolved:
            typer.echo(
                "  Unresolved filesystem-entry detail:"
            )

            for requirement in (
                filesystem_entries.unresolved
            ):
                typer.echo(
                    (
                        "    "
                        f"{requirement.metadata_entry.entry_type.value}: "
                        f"{requirement.inventory_entry.artifact.path.as_posix()}:"
                        f"{requirement.metadata_entry.path}"
                    )
                )

        model_sources = (
            universe_result.model_source_requirements
        )

        model_source_kind_counts = Counter(
            requirement.source.kind.value
            for requirement
            in model_sources.requirements
        )

        model_source_disposition_counts = Counter(
            requirement.disposition.value
            for requirement
            in model_sources.requirements
        )

        unresolved_model_source_kind_counts = Counter(
            requirement.source.kind.value
            for requirement
            in model_sources.unresolved
        )

        represented_model_source_kinds = {
            requirement.source.kind
            for requirement
            in model_sources.requirements
        }

        typer.echo()
        typer.echo(
            "Model-source Universe coverage:"
        )
        typer.echo(
            (
                "  Canonical model sources: "
                f"{len(model_sources.requirements)}"
            )
        )
        typer.echo(
            (
                "  Source kinds represented: "
                f"{len(represented_model_source_kinds)}"
            )
        )
        typer.echo(
            (
                "  Semantic owner present: "
                f"{sum(
                    1
                    for requirement
                    in model_sources.requirements
                    if requirement.universe_owner is not None
                )}"
            )
        )
        typer.echo(
            (
                "  Unresolved model sources: "
                f"{len(model_sources.unresolved)}"
            )
        )

        typer.echo(
            "  Sources by kind:"
        )

        for kind, count in sorted(
            model_source_kind_counts.items()
        ):
            typer.echo(
                f"    {kind}: {count}"
            )

        typer.echo(
            "  Sources by disposition:"
        )

        for disposition, count in sorted(
            model_source_disposition_counts.items()
        ):
            typer.echo(
                f"    {disposition}: {count}"
            )

        if unresolved_model_source_kind_counts:
            typer.echo(
                "  Unresolved by source kind:"
            )

            for kind, count in sorted(
                unresolved_model_source_kind_counts.items()
            ):
                typer.echo(
                    f"    {kind}: {count}"
                )

        if model_sources.unresolved:
            typer.echo(
                "  Unresolved source detail:"
            )

            for requirement in model_sources.unresolved:
                typer.echo(
                    (
                        "    "
                        f"{requirement.source.kind.value}: "
                        f"{requirement.source.source_name}:"
                        f"{requirement.source.android_path.as_posix()}"
                    )
                )

        filesystem = universe_result.parsing.filesystem

        property_sources = tuple(
            filesystem.property_files
        )
        init_sources = tuple(
            filesystem.init_files
        )
        fstab_sources = tuple(
            filesystem.fstabs
        )
        ueventd_sources = tuple(
            filesystem.ueventd_files
        )
        vintf_sources = tuple(
            filesystem.vintf_documents
        )
        selinux_sources = tuple(
            filesystem.selinux_sources
        )

        property_declarations = sum(
            len(source.declarations)
            for source in property_sources
        )
        property_unparsed = sum(
            len(source.unparsed_lines)
            for source in property_sources
        )

        init_imports = sum(
            len(source.imports)
            for source in init_sources
        )
        init_services = sum(
            len(source.services)
            for source in init_sources
        )
        init_actions = sum(
            len(source.actions)
            for source in init_sources
        )
        init_unparsed = sum(
            len(source.unparsed_lines)
            for source in init_sources
        )

        fstab_declarations = sum(
            len(source.declarations)
            for source in fstab_sources
        )
        fstab_unparsed = sum(
            len(source.unparsed_lines)
            for source in fstab_sources
        )

        ueventd_declarations = sum(
            len(source.declarations)
            for source in ueventd_sources
        )
        ueventd_unparsed = sum(
            len(source.unparsed_lines)
            for source in ueventd_sources
        )

        property_source_identity_match = (
            {
                id(source)
                for source in property_sources
            }
            == {
                id(record.parsed_source)
                for record
                in universe_result.property_source_records
            }
        )

        init_source_identity_match = (
            {
                id(source)
                for source in init_sources
            }
            == {
                id(record.parsed_source)
                for record
                in universe_result.init_source_records
            }
        )

        typer.echo()
        typer.echo(
            "Filesystem Parsing -> Universe source coverage:"
        )

        typer.echo(
            "  Property:"
        )
        typer.echo(
            f"    Parsing sources: {len(property_sources)}"
        )
        typer.echo(
            (
                "    Universe source records: "
                f"{len(universe_result.property_source_records)}"
            )
        )
        typer.echo(
            (
                "    Source identity match: "
                f"{property_source_identity_match}"
            )
        )
        typer.echo(
            f"    Parsed declarations: {property_declarations}"
        )
        typer.echo(
            (
                "    Interpreted evidence observations: "
                f"{len(universe_result.property_evidence)}"
            )
        )
        typer.echo(
            f"    Preserved unparsed lines: {property_unparsed}"
        )

        typer.echo(
            "  INIT:"
        )
        typer.echo(
            f"    Parsing sources: {len(init_sources)}"
        )
        typer.echo(
            (
                "    Universe source records: "
                f"{len(universe_result.init_source_records)}"
            )
        )
        typer.echo(
            (
                "    Source identity match: "
                f"{init_source_identity_match}"
            )
        )
        typer.echo(
            (
                "    Applicability conclusions: "
                f"{len(universe_result.init_source_applicability)}"
            )
        )
        typer.echo(
            f"    Parsed imports: {init_imports}"
        )
        typer.echo(
            f"    Universe imports: {len(universe_result.init_import_requirements)}"
        )
        typer.echo(
            f"    Parsed services: {init_services}"
        )
        typer.echo(
            f"    Universe services: {len(universe_result.init_service_requirements)}"
        )
        typer.echo(
            f"    Parsed actions: {init_actions}"
        )
        typer.echo(
            f"    Universe actions: {len(universe_result.init_action_requirements)}"
        )
        typer.echo(
            f"    Preserved unparsed lines: {init_unparsed}"
        )

        typer.echo(
            "  Fstab:"
        )
        typer.echo(
            f"    Parsing sources: {len(fstab_sources)}"
        )
        typer.echo(
            (
                "    Universe source contexts: "
                f"{len(universe_result.fstab_source_contexts)}"
            )
        )
        typer.echo(
            f"    Parsed declarations: {fstab_declarations}"
        )
        typer.echo(
            (
                "    Universe requirements: "
                f"{len(universe_result.fstab_requirements)}"
            )
        )
        typer.echo(
            f"    Preserved unparsed lines: {fstab_unparsed}"
        )

        typer.echo(
            "  Ueventd:"
        )
        typer.echo(
            f"    Parsing sources: {len(ueventd_sources)}"
        )
        typer.echo(
            (
                "    Universe source contexts: "
                f"{len(universe_result.ueventd_source_contexts)}"
            )
        )
        typer.echo(
            f"    Parsed declarations: {ueventd_declarations}"
        )
        typer.echo(
            (
                "    Universe requirements: "
                f"{len(universe_result.ueventd_requirements)}"
            )
        )
        typer.echo(
            f"    Preserved unparsed lines: {ueventd_unparsed}"
        )

        typer.echo(
            "  VINTF:"
        )
        typer.echo(
            f"    Parsing sources: {len(vintf_sources)}"
        )
        typer.echo(
            (
                "    Universe requirements: "
                f"{len(universe_result.vintf_requirements)}"
            )
        )

        typer.echo(
            "  SELinux:"
        )
        typer.echo(
            f"    Parsing sources: {len(selinux_sources)}"
        )
        typer.echo(
            (
                "    Universe requirements: "
                f"{len(universe_result.selinux_requirements)}"
            )
        )

        typer.echo()
        typer.echo(
            "Current Device Universe coverage:"
        )

        artifact_requirement_inventory = (
            universe_result.artifact_requirements
        )

        artifact_requirements = (
            ()
            if artifact_requirement_inventory is None
            else artifact_requirement_inventory.requirements
        )

        artifact_partition_counts = Counter(
            requirement.partition_name
            for requirement
            in artifact_requirements
        )

        artifact_disposition_counts = Counter(
            requirement.disposition.value
            for requirement
            in artifact_requirements
        )

        artifact_kind_counts = Counter(
            kind.value
            for requirement
            in artifact_requirements
            for kind
            in requirement.kinds
        )

        artifact_classification_origin_counts = Counter(
            requirement.classification_origin.value
            for requirement
            in artifact_requirements
        )

        unclassified_artifact_requirements = tuple(
            requirement
            for requirement
            in artifact_requirements
            if requirement.disposition.value == "unclassified"
        )

        unclassified_deployment_role_counts = Counter(
            requirement.deployment_role.value
            for requirement
            in unclassified_artifact_requirements
        )

        unclassified_partition_counts = Counter(
            requirement.partition_name
            for requirement
            in unclassified_artifact_requirements
        )

        unclassified_kind_counts = Counter(
            kind.value
            for requirement
            in unclassified_artifact_requirements
            for kind
            in requirement.kinds
        )

        unclassified_group_counts = Counter(
            (
                requirement.deployment_role.value,
                requirement.partition_name,
                kind.value,
            )
            for requirement
            in unclassified_artifact_requirements
            for kind
            in requirement.kinds
        )

        unclassified_group_examples = {}

        for requirement in unclassified_artifact_requirements:
            for kind in requirement.kinds:
                group_key = (
                    requirement.deployment_role.value,
                    requirement.partition_name,
                    kind.value,
                )

                examples = unclassified_group_examples.setdefault(
                    group_key,
                    [],
                )

                if len(examples) < 5:
                    examples.append(
                        requirement.android_path
                    )

        typer.echo(
            "Artifact requirements: "
            f"{len(artifact_requirements)}"
        )

        typer.echo(
            "Unclassified artifact requirements: "
            f"{artifact_disposition_counts.get('unclassified', 0)}"
        )

        typer.echo(
            "Artifacts classified from Parsing evidence: "
            f"{artifact_classification_origin_counts.get('parsing_evidence', 0)}"
        )

        typer.echo(
            "Artifacts classified by path fallback: "
            f"{artifact_classification_origin_counts.get('path_classifier', 0)}"
        )

        typer.echo(
            "Artifacts with unresolved classification: "
            f"{artifact_classification_origin_counts.get('unresolved', 0)}"
        )

        if artifact_kind_counts:
            typer.echo(
                "Artifact requirements by kind:"
            )

            for kind, count in sorted(
                artifact_kind_counts.items()
            ):
                typer.echo(
                    f"  {kind}: {count}"
                )

        if artifact_classification_origin_counts:
            typer.echo(
                "Artifact requirements by classification origin:"
            )

            for origin, count in sorted(
                artifact_classification_origin_counts.items()
            ):
                typer.echo(
                    f"  {origin}: {count}"
                )

        if artifact_disposition_counts:
            typer.echo(
                "Artifact requirements by disposition:"
            )

            for disposition, count in sorted(
                artifact_disposition_counts.items()
            ):
                typer.echo(
                    f"  {disposition}: {count}"
                )

        if artifact_partition_counts:
            typer.echo(
                "Artifact requirements by partition:"
            )

            for partition_name, count in sorted(
                artifact_partition_counts.items(),
                key=lambda item: (
                    item[0] is None,
                    "" if item[0] is None else item[0],
                ),
            ):
                typer.echo(
                    f"  {partition_name}: {count}"
                )

        if unclassified_artifact_requirements:
            typer.echo()
            typer.echo(
                "Unclassified artifact disposition analysis:"
            )
            typer.echo(
                "  Total unclassified dispositions: "
                f"{len(unclassified_artifact_requirements)}"
            )

            typer.echo(
                "  By deployment role:"
            )

            for deployment_role, count in sorted(
                unclassified_deployment_role_counts.items()
            ):
                typer.echo(
                    f"    {deployment_role}: {count}"
                )

            typer.echo(
                "  By partition:"
            )

            for partition_name, count in sorted(
                unclassified_partition_counts.items(),
                key=lambda item: (
                    item[0] is None,
                    "" if item[0] is None else item[0],
                ),
            ):
                typer.echo(
                    f"    {partition_name}: {count}"
                )

            typer.echo(
                "  By kind:"
            )

            for kind, count in sorted(
                unclassified_kind_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            ):
                typer.echo(
                    f"    {kind}: {count}"
                )

            typer.echo(
                "  By deployment role / partition / kind:"
            )

            for group_key, count in sorted(
                unclassified_group_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0][0],
                    item[0][1] is None,
                    (
                        ""
                        if item[0][1] is None
                        else item[0][1]
                    ),
                    item[0][2],
                ),
            ):
                (
                    deployment_role,
                    partition_name,
                    kind,
                ) = group_key

                typer.echo(
                    "    "
                    f"{deployment_role} / "
                    f"{partition_name} / "
                    f"{kind}: "
                    f"{count}"
                )

                for example_path in (
                    unclassified_group_examples.get(
                        group_key,
                        ()
                    )
                ):
                    typer.echo(
                        f"      {example_path}"
                    )

        unknown_artifact_requirements = tuple(
            sorted(
                (
                    requirement
                    for requirement
                    in artifact_requirements
                    if (
                        len(requirement.kinds) == 1
                        and requirement.kinds[0].value
                        == "unknown"
                    )
                ),
                key=lambda requirement: (
                    requirement.partition_name is None,
                    (
                        ""
                        if requirement.partition_name is None
                        else requirement.partition_name
                    ),
                    requirement.android_path,
                ),
            )
        )

        if unknown_artifact_requirements:
            unknown_partition_counts = Counter(
                requirement.partition_name
                for requirement
                in unknown_artifact_requirements
            )

            unknown_suffix_counts = Counter()

            unknown_directory_counts = Counter()

            for requirement in (
                unknown_artifact_requirements
            ):
                artifact_path = PurePosixPath(
                    requirement.android_path
                )

                suffix = (
                    artifact_path.suffix.lower()
                    or "<none>"
                )

                unknown_suffix_counts[
                    suffix
                ] += 1

                parent = (
                    artifact_path.parent.as_posix()
                )

                if not parent:
                    parent = "/"

                unknown_directory_counts[
                    (
                        requirement.partition_name,
                        parent,
                    )
                ] += 1

            typer.echo()
            typer.echo(
                "Unknown artifact analysis:"
            )
            typer.echo(
                "  Total unknown artifacts: "
                f"{len(unknown_artifact_requirements)}"
            )

            typer.echo(
                "  By partition:"
            )

            for partition_name, count in sorted(
                unknown_partition_counts.items(),
                key=lambda item: (
                    item[0] is None,
                    "" if item[0] is None else item[0],
                ),
            ):
                typer.echo(
                    f"    {partition_name}: {count}"
                )

            typer.echo(
                "  By suffix:"
            )

            for suffix, count in sorted(
                unknown_suffix_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            ):
                typer.echo(
                    f"    {suffix}: {count}"
                )

            typer.echo(
                "  Top directories:"
            )

            for (
                partition_name,
                directory,
            ), count in sorted(
                unknown_directory_counts.items(),
                key=lambda item: (
                    -item[1],
                    item[0][0] is None,
                    (
                        ""
                        if item[0][0] is None
                        else item[0][0]
                    ),
                    item[0][1],
                ),
            )[:50]:
                typer.echo(
                    "    "
                    f"{partition_name}:"
                    f"{directory}: "
                    f"{count}"
                )

            typer.echo(
                "  Unknown artifacts:"
            )

            for requirement in (
                unknown_artifact_requirements
            ):
                typer.echo(
                    "    "
                    f"{requirement.partition_name}:"
                    f"{requirement.android_path}"
                    f" ({requirement.size} bytes)"
                )
        typer.echo(
            (
                "  Parsed property sources available: "
                f"{len(parsing.filesystem.property_files)}"
            )
        )
        typer.echo(
            (
                "  Property evidence observations: "
                f"{len(evidence)}"
            )
        )

        runtime_property_requirements = (
            universe_result.runtime_property_requirements
        )

        runtime_with_static = sum(
            requirement.has_static_declaration
            for requirement
            in runtime_property_requirements
        )

        runtime_with_runtime_producer = sum(
            requirement.has_runtime_producer
            for requirement
            in runtime_property_requirements
        )

        runtime_with_consumer = sum(
            requirement.has_consumer
            for requirement
            in runtime_property_requirements
        )

        runtime_with_context = sum(
            requirement.has_property_context
            for requirement
            in runtime_property_requirements
        )

        runtime_consumer_only = sum(
            (
                requirement.has_consumer
                and requirement.producer_count == 0
            )
            for requirement
            in runtime_property_requirements
        )

        runtime_total_producers = sum(
            requirement.producer_count
            for requirement
            in runtime_property_requirements
        )

        runtime_total_consumers = sum(
            requirement.consumer_count
            for requirement
            in runtime_property_requirements
        )

        typer.echo()
        typer.echo(
            "Runtime property coverage:"
        )
        typer.echo(
            "  Canonical runtime properties: "
            f"{len(runtime_property_requirements)}"
        )
        typer.echo(
            "  With static declarations: "
            f"{runtime_with_static}"
        )
        typer.echo(
            "  With INIT runtime producers: "
            f"{runtime_with_runtime_producer}"
        )
        typer.echo(
            "  With runtime consumers: "
            f"{runtime_with_consumer}"
        )
        typer.echo(
            "  With SELinux property contexts: "
            f"{runtime_with_context}"
        )
        typer.echo(
            "  Consumer-only properties: "
            f"{runtime_consumer_only}"
        )
        typer.echo(
            "  Producer observations: "
            f"{runtime_total_producers}"
        )
        typer.echo(
            "  Consumer observations: "
            f"{runtime_total_consumers}"
        )
        typer.echo(
            (
                "  Property sources contributing evidence: "
                f"{len(source_paths)}"
            )
        )
        typer.echo(
            (
                "  Distinct interpreted facts: "
                f"{len(fact_counts)}"
            )
        )

        typer.echo()
        typer.echo(
            "Canonical conclusions:"
        )
        typer.echo(
            (
                "  Total conclusions: "
                f"{len(conclusions)}"
            )
        )

        for status in (
            AndroidUniverseConclusionStatus.AGREED,
            AndroidUniverseConclusionStatus.CONFLICTING,
            AndroidUniverseConclusionStatus.UNRESOLVED,
        ):
            typer.echo(
                (
                    f"  {status.value}: "
                    f"{conclusion_status_counts.get(status.value, 0)}"
                )
            )

        typer.echo()
        typer.echo(
            "Key device conclusions:"
        )

        for fact in (
            "device_codename",
            "product_model",
            "product_name",
            "manufacturer",
            "product_brand",
            "android_version",
            "sdk_level",
            "soc_model",
            "screen_density",
        ):
            conclusion = (
                conclusion_by_fact.get(
                    fact
                )
            )

            if conclusion is None:
                typer.echo(
                    f"  {fact}: absent"
                )
                continue

            if conclusion.value is not None:
                typer.echo(
                    (
                        f"  {fact}: "
                        f"{conclusion.value!r} "
                        f"[{conclusion.status.value}]"
                    )
                )
            else:
                typer.echo(
                    (
                        f"  {fact}: "
                        f"[{conclusion.status.value}] "
                        f"values={conclusion.distinct_values}"
                    )
                )

        typer.echo()
        init_cli_service_requirements = (
            universe_result.init_service_requirements
        )

        init_cli_action_requirements = (
            universe_result.init_action_requirements
        )

        init_cli_action_command_count = sum(
            len(
                requirement.commands
            )
            for requirement
            in init_cli_action_requirements
        )

        init_cli_action_command_keywords = {
            command.keyword
            for requirement
            in init_cli_action_requirements
            for command
            in requirement.commands
        }

        init_cli_semantic_action_commands = tuple(
            command_requirement
            for requirement
            in init_cli_action_requirements
            for command_requirement
            in requirement.command_requirements
        )

        init_cli_semantic_action_command_keywords = {
            command_requirement.keyword
            for command_requirement
            in init_cli_semantic_action_commands
        }

        init_cli_uninterpreted_action_command_count = (
            init_cli_action_command_count
            - len(
                init_cli_semantic_action_commands
            )
        )

        init_cli_semantic_action_triggers = tuple(
            requirement.trigger_semantics
            for requirement
            in init_cli_action_requirements
        )

        init_cli_trigger_expressions = {
            trigger.expression
            for trigger
            in init_cli_semantic_action_triggers
        }

        init_cli_event_trigger_clause_count = sum(
            len(
                trigger.event_clauses
            )
            for trigger
            in init_cli_semantic_action_triggers
        )

        init_cli_property_trigger_clause_count = sum(
            len(
                trigger.property_clauses
            )
            for trigger
            in init_cli_semantic_action_triggers
        )

        init_cli_compound_action_count = sum(
            1
            for trigger
            in init_cli_semantic_action_triggers
            if trigger.is_compound
        )

        init_cli_uninterpreted_action_trigger_count = (
            len(
                init_cli_action_requirements
            )
            - len(
                init_cli_semantic_action_triggers
            )
        )

        init_cli_semantic_counts = Counter()

        init_cli_uninterpreted_options = Counter()

        for requirement in init_cli_service_requirements:
            semantics = requirement.semantics

            if semantics.classes is not None:
                init_cli_semantic_counts[
                    "classes"
                ] += 1

            if semantics.user is not None:
                init_cli_semantic_counts[
                    "user"
                ] += 1

            if semantics.groups is not None:
                init_cli_semantic_counts[
                    "groups"
                ] += 1

            if semantics.capabilities is not None:
                init_cli_semantic_counts[
                    "capabilities"
                ] += 1

            if semantics.seclabel is not None:
                init_cli_semantic_counts[
                    "seclabel"
                ] += 1

            if semantics.disabled:
                init_cli_semantic_counts[
                    "disabled"
                ] += 1

            if semantics.oneshot:
                init_cli_semantic_counts[
                    "oneshot"
                ] += 1

            if semantics.override:
                init_cli_semantic_counts[
                    "override"
                ] += 1

            if semantics.critical is not None:
                init_cli_semantic_counts[
                    "critical"
                ] += 1

            if semantics.task_profiles is not None:
                init_cli_semantic_counts[
                    "task_profiles"
                ] += 1

            if semantics.ioprio is not None:
                init_cli_semantic_counts[
                    "ioprio"
                ] += 1

            if semantics.priority is not None:
                init_cli_semantic_counts[
                    "priority"
                ] += 1

            init_cli_semantic_counts[
                "rlimit_declarations"
            ] += len(
                semantics.rlimits
            )

            if semantics.stdio_to_kmsg:
                init_cli_semantic_counts[
                    "stdio_to_kmsg"
                ] += 1

            init_cli_semantic_counts[
                "setenv_declarations"
            ] += len(
                semantics.environment
            )

            if semantics.namespaces is not None:
                init_cli_semantic_counts[
                    "namespace"
                ] += 1

            if semantics.updatable:
                init_cli_semantic_counts[
                    "updatable"
                ] += 1

            if semantics.writepid_paths is not None:
                init_cli_semantic_counts[
                    "writepid"
                ] += 1

            if semantics.console:
                init_cli_semantic_counts[
                    "console"
                ] += 1

            if semantics.gentle_kill:
                init_cli_semantic_counts[
                    "gentle_kill"
                ] += 1

            if semantics.restart_period is not None:
                init_cli_semantic_counts[
                    "restart_period"
                ] += 1

            if semantics.timeout_period is not None:
                init_cli_semantic_counts[
                    "timeout_period"
                ] += 1

            if semantics.shutdown is not None:
                init_cli_semantic_counts[
                    "shutdown"
                ] += 1

            if semantics.reboot_on_failure is not None:
                init_cli_semantic_counts[
                    "reboot_on_failure"
                ] += 1

            init_cli_semantic_counts[
                "socket_declarations"
            ] += len(
                semantics.sockets
            )

            init_cli_semantic_counts[
                "file_declarations"
            ] += len(
                semantics.files
            )

            init_cli_semantic_counts[
                "interface_declarations"
            ] += len(
                semantics.interfaces
            )

            init_cli_semantic_counts[
                "onrestart_commands"
            ] += len(
                semantics.onrestart_commands
            )

            if semantics.keycodes is not None:
                init_cli_semantic_counts[
                    "keycodes"
                ] += 1

            for option in semantics.uninterpreted_options:
                init_cli_uninterpreted_options[
                    option.keyword
                ] += 1

        ueventd_cli_requirements = (
            universe_result.ueventd_requirements
        )

        ueventd_cli_family_counts = Counter(
            type(requirement).__name__
            for requirement
            in ueventd_cli_requirements
        )

        ueventd_cli_subsystem_requirements = tuple(
            requirement
            for requirement
            in ueventd_cli_requirements
            if type(requirement).__name__
            == "AndroidUniverseUeventdSubsystemRequirement"
        )

        ueventd_cli_subsystem_options = tuple(
            option
            for requirement
            in ueventd_cli_subsystem_requirements
            for option
            in requirement.option_semantics
        )

        ueventd_cli_semantic_subsystem_options = tuple(
            option
            for option
            in ueventd_cli_subsystem_options
            if option.interpreted
        )

        ueventd_cli_uninterpreted_subsystem_options = tuple(
            option
            for option
            in ueventd_cli_subsystem_options
            if not option.interpreted
        )

        ueventd_cli_option_keywords = {
            option.keyword
            for option
            in ueventd_cli_subsystem_options
        }

        ueventd_cli_interpreted_option_keywords = {
            option.keyword
            for option
            in ueventd_cli_semantic_subsystem_options
        }

        ueventd_cli_parsed_declarations = sum(
            len(source.declarations)
            for source
            in parsing.filesystem.ueventd_files
        )

        ueventd_cli_unparsed_lines = sum(
            len(source.unparsed_lines)
            for source
            in parsing.filesystem.ueventd_files
        )

        ueventd_cli_source_contexts = (
            universe_result.ueventd_source_contexts
        )

        ueventd_cli_contexts_with_unparsed_lines = sum(
            1
            for source_context
            in ueventd_cli_source_contexts
            if source_context.unparsed_lines
        )

        ueventd_cli_context_unparsed_lines = sum(
            len(source_context.unparsed_lines)
            for source_context
            in ueventd_cli_source_contexts
        )

        typer.echo(
            "INIT Universe coverage:"
        )

        typer.echo(
            (
                "  Universe INIT import requirements: "
                f"{len(universe_result.init_import_requirements)}"
            )
        )

        typer.echo(
            (
                "  Universe INIT service requirements: "
                f"{len(init_cli_service_requirements)}"
            )
        )

        typer.echo(
            (
                "  Universe INIT action requirements: "
                f"{len(init_cli_action_requirements)}"
            )
        )

        typer.echo(
            (
                "  Universe INIT action commands: "
                f"{init_cli_action_command_count}"
            )
        )

        typer.echo(
            (
                "  Distinct INIT action command keywords: "
                f"{len(init_cli_action_command_keywords)}"
            )
        )

        typer.echo(
            (
                "  Semantic INIT action commands: "
                f"{len(init_cli_semantic_action_commands)}"
            )
        )

        typer.echo(
            (
                "  Interpreted action command keywords: "
                f"{len(init_cli_semantic_action_command_keywords)}"
            )
        )

        typer.echo(
            (
                "  Uninterpreted action commands: "
                f"{init_cli_uninterpreted_action_command_count}"
            )
        )

        typer.echo(
            (
                "  Semantic INIT action triggers: "
                f"{len(init_cli_semantic_action_triggers)}"
            )
        )

        typer.echo(
            (
                "  Distinct INIT trigger expressions: "
                f"{len(init_cli_trigger_expressions)}"
            )
        )

        typer.echo(
            (
                "  Event trigger clauses: "
                f"{init_cli_event_trigger_clause_count}"
            )
        )

        typer.echo(
            (
                "  Property trigger clauses: "
                f"{init_cli_property_trigger_clause_count}"
            )
        )

        typer.echo(
            (
                "  Compound INIT actions: "
                f"{init_cli_compound_action_count}"
            )
        )

        typer.echo(
            (
                "  Uninterpreted action triggers: "
                f"{init_cli_uninterpreted_action_trigger_count}"
            )
        )

        typer.echo(
            "  Service semantic coverage:"
        )

        init_cli_semantic_output = (
            ("classes", "classes"),
            ("user", "user"),
            ("groups", "groups"),
            ("capabilities", "capabilities"),
            ("seclabel", "seclabel"),
            ("disabled", "disabled"),
            ("oneshot", "oneshot"),
            ("override", "override"),
            ("critical", "critical"),
            ("task_profiles", "task_profiles"),
            ("ioprio", "ioprio"),
            ("priority", "priority"),
            (
                "rlimit declarations",
                "rlimit_declarations",
            ),
            (
                "stdio_to_kmsg",
                "stdio_to_kmsg",
            ),
            (
                "setenv declarations",
                "setenv_declarations",
            ),
            ("namespace", "namespace"),
            ("updatable", "updatable"),
            ("writepid", "writepid"),
            ("console", "console"),
            ("gentle_kill", "gentle_kill"),
            (
                "restart_period",
                "restart_period",
            ),
            (
                "timeout_period",
                "timeout_period",
            ),
            ("shutdown", "shutdown"),
            (
                "reboot_on_failure",
                "reboot_on_failure",
            ),
            (
                "socket declarations",
                "socket_declarations",
            ),
            (
                "file declarations",
                "file_declarations",
            ),
            (
                "interface declarations",
                "interface_declarations",
            ),
            (
                "onrestart commands",
                "onrestart_commands",
            ),
            ("keycodes", "keycodes"),
        )

        for label, key in init_cli_semantic_output:
            typer.echo(
                (
                    f"    {label}: "
                    f"{init_cli_semantic_counts[key]}"
                )
            )

        typer.echo(
            (
                "  Uninterpreted service options: "
                f"{sum(init_cli_uninterpreted_options.values())}"
            )
        )

        typer.echo(
            (
                "  Distinct uninterpreted option keywords: "
                f"{len(init_cli_uninterpreted_options)}"
            )
        )

        init_cli_onrestart_commands = tuple(
            command
            for requirement
            in init_cli_service_requirements
            for command
            in requirement.semantics.onrestart_commands
        )

        init_cli_onrestart_command_counts = Counter(
            command.command
            for command
            in init_cli_onrestart_commands
        )

        typer.echo(
            "  Onrestart semantic commands:"
        )

        typer.echo(
            (
                "    total: "
                f"{len(init_cli_onrestart_commands)}"
            )
        )

        for keyword, count in sorted(
            init_cli_onrestart_command_counts.items()
        ):
            typer.echo(
                f"    {keyword}: {count}"
            )

        init_import_resolutions = (
            universe_result.init_import_resolutions
        )

        init_import_resolution_status_counts = Counter(
            resolution.status.value
            for resolution
            in init_import_resolutions
        )

        property_selected_imports = tuple(
            resolution
            for resolution
            in init_import_resolutions
            if resolution.expansion.is_property_expression
        )

        structural_unselected_candidates = sum(
            (
                len(
                    resolution.candidate_sources
                )
                - len(
                    resolution.matched_sources
                )
            )
            for resolution
            in property_selected_imports
            if resolution.status.value == "resolved"
        )

        proven_inapplicable_init_sources = (
            android_init_inapplicable_source_paths(
                init_import_resolutions
            )
        )

        typer.echo()
        typer.echo(
            "INIT import resolution:"
        )
        typer.echo(
            (
                "  Import requirements: "
                f"{len(init_import_resolutions)}"
            )
        )
        typer.echo(
            (
                "  Property-selected imports: "
                f"{len(property_selected_imports)}"
            )
        )

        for status, count in sorted(
            init_import_resolution_status_counts.items()
        ):
            typer.echo(
                f"  {status}: {count}"
            )

        typer.echo(
            (
                "  Structural unselected candidates: "
                f"{structural_unselected_candidates}"
            )
        )

        typer.echo(
            (
                "  Proven inapplicable INIT sources: "
                f"{len(proven_inapplicable_init_sources)}"
            )
        )

        typer.echo()
        typer.echo(
            "INIT import resolution detail:"
        )

        for resolution in init_import_resolutions:
            expansion = resolution.expansion

            typer.echo()
            typer.echo(
                f"  {resolution.requirement.path}"
            )
            typer.echo(
                "    status: "
                f"{resolution.status.value}"
            )
            typer.echo(
                "    expansion: "
                f"{expansion.status.value}"
            )

            if expansion.expanded_value is not None:
                typer.echo(
                    "    expanded path: "
                    f"{expansion.expanded_value}"
                )
            else:
                typer.echo(
                    "    expanded path: <unresolved>"
                )

            if expansion.referenced_properties:
                typer.echo(
                    "    referenced properties: "
                    + ", ".join(
                        expansion.referenced_properties
                    )
                )

                resolved_property_map = dict(
                    expansion.resolved_properties
                )

                for property_name in (
                    expansion.referenced_properties
                ):
                    if property_name in resolved_property_map:
                        typer.echo(
                            "      "
                            f"{property_name} = "
                            f"{resolved_property_map[property_name]}"
                        )
                    else:
                        typer.echo(
                            "      "
                            f"{property_name} = <unresolved>"
                        )
            else:
                typer.echo(
                    "    referenced properties: none"
                )

            typer.echo(
                "    candidates: "
                f"{len(resolution.candidate_sources)}"
            )

            for source in resolution.candidate_sources:
                if source.android_path is None:
                    candidate_path = "<no android path>"
                else:
                    candidate_path = (
                        "/"
                        + source.android_path
                        .as_posix()
                        .lstrip("/")
                    )

                typer.echo(
                    f"      candidate: {candidate_path}"
                )

            typer.echo(
                "    matched: "
                f"{len(resolution.matched_sources)}"
            )

            for source in resolution.matched_sources:
                if source.android_path is None:
                    matched_path = "<no android path>"
                else:
                    matched_path = (
                        "/"
                        + source.android_path
                        .as_posix()
                        .lstrip("/")
                    )

                typer.echo(
                    f"      match: {matched_path}"
                )

        init_source_applicability = (
            universe_result.init_source_applicability
        )

        init_source_applicability_status_counts = Counter(
            item.status.value
            for item in init_source_applicability
        )

        init_source_applicability_evidence_counts = Counter(
            evidence.kind.value
            for item in init_source_applicability
            for evidence in item.evidence
        )

        typer.echo()
        typer.echo(
            "INIT source applicability:"
        )

        typer.echo(
            (
                "  Source identities: "
                f"{len(init_source_applicability)}"
            )
        )

        for status in (
            "required",
            "alternative",
            "runtime_selectable",
            "unreferenced",
            "unresolved",
        ):
            typer.echo(
                (
                    f"  {status}: "
                    f"{init_source_applicability_status_counts.get(status, 0)}"
                )
            )

        typer.echo(
            "  Applicability evidence:"
        )

        for evidence_kind, count in sorted(
            init_source_applicability_evidence_counts.items()
        ):
            typer.echo(
                f"    {evidence_kind}: {count}"
            )

        unresolved_init_sources = tuple(
            item
            for item in init_source_applicability
            if item.status.value == "unresolved"
        )

        typer.echo(
            (
                "  Unresolved source identities: "
                f"{len(unresolved_init_sources)}"
            )
        )

        if unresolved_init_sources:
            typer.echo()
            typer.echo(
                "INIT source applicability unresolved detail:"
            )

            for item in unresolved_init_sources:
                typer.echo()
                typer.echo(
                    f"  {item.source_identity}"
                )
                typer.echo(
                    f"    source path: {item.source_path}"
                )

                if item.android_path is None:
                    typer.echo(
                        "    android path: <none>"
                    )
                else:
                    typer.echo(
                        (
                            "    android path: "
                            f"{item.android_path}"
                        )
                    )

                if item.filesystem_source is None:
                    typer.echo(
                        "    filesystem source: <none>"
                    )
                else:
                    typer.echo(
                        (
                            "    filesystem source: "
                            f"{item.filesystem_source}"
                        )
                    )

                typer.echo(
                    (
                        "    requirement IDs: "
                        + ", ".join(item.requirement_ids)
                    )
                )

                typer.echo(
                    (
                        "    evidence: "
                        f"{len(item.evidence)}"
                    )
                )

        init_service_resolutions = (
            universe_result.init_service_resolutions
        )

        init_service_resolution_status_counts = Counter(
            resolution.status.value
            for resolution
            in init_service_resolutions
        )

        init_service_resolution_context_counts = Counter(
            resolution.source_context.value
            for resolution
            in init_service_resolutions
        )

        init_service_override_resolution_count = sum(
            1
            for resolution
            in init_service_resolutions
            if any(
                service.semantics.override
                for service
                in resolution.declarations
            )
        )

        typer.echo()
        typer.echo(
            "INIT service reconciliation:"
        )
        typer.echo(
            (
                "  Context-local service names: "
                f"{len(init_service_resolutions)}"
            )
        )

        for status, count in sorted(
            init_service_resolution_status_counts.items()
        ):
            typer.echo(
                f"  {status}: {count}"
            )

        typer.echo(
            "  By source context:"
        )

        for source_context, count in sorted(
            init_service_resolution_context_counts.items()
        ):
            typer.echo(
                f"    {source_context}: {count}"
            )

        typer.echo(
            (
                "  Names with override evidence: "
                f"{init_service_override_resolution_count}"
            )
        )

        relationships = (
            universe_result.cross_family_relationships
        )

        relationship_kind_counts = Counter(
            relationship.kind.value
            for relationship
            in relationships
        )

        relationship_status_counts = Counter(
            relationship.status.value
            for relationship
            in relationships
        )

        relationship_status_by_kind = {
            kind: Counter(
                relationship.status.value
                for relationship
                in relationships
                if relationship.kind.value == kind
            )
            for kind
            in relationship_kind_counts
        }

        init_onrestart_control_relationships = tuple(
            relationship
            for relationship
            in relationships
            if isinstance(
                relationship,
                AndroidUniverseInitOnRestartServiceControlRelationship,
            )
        )

        init_onrestart_property_relationships = tuple(
            relationship
            for relationship
            in relationships
            if isinstance(
                relationship,
                AndroidUniverseInitOnRestartPropertyCommandRelationship,
            )
        )

        typer.echo()
        typer.echo(
            "Cross-family relationship coverage:"
        )

        typer.echo(
            (
                "  Total relationships: "
                f"{len(relationships)}"
            )
        )

        typer.echo(
            "  Relationship kinds:"
        )

        for kind, count in sorted(
            relationship_kind_counts.items()
        ):
            typer.echo(
                f"    {kind}: {count}"
            )

        typer.echo(
            "  Relationship statuses:"
        )

        for status, count in sorted(
            relationship_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        typer.echo(
            "  Relationship statuses by kind:"
        )

        for kind in sorted(
            relationship_status_by_kind
        ):
            typer.echo(
                f"    {kind}:"
            )

            for status, count in sorted(
                relationship_status_by_kind[
                    kind
                ].items()
            ):
                typer.echo(
                    f"      {status}: {count}"
                )

        relationship_applicability = (
            universe_result
            .cross_family_relationship_applicability
        )

        relationship_applicability_by_id = {
            item.requirement_id: item
            for item
            in relationship_applicability
        }

        relationship_applicability_counts = Counter(
            item.status.value
            for item
            in relationship_applicability
        )

        typer.echo(
            "  Relationship applicability:"
        )

        for status, count in sorted(
            relationship_applicability_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        actionable_relationships = tuple(
            relationship
            for relationship
            in relationships
            if (
                relationship_applicability_by_id[
                    relationship.relationship_id
                ].status.value
                != "alternative"
            )
        )

        actionable_status_counts = Counter(
            relationship.status.value
            for relationship
            in actionable_relationships
        )

        typer.echo(
            "  Actionable relationship statuses:"
        )

        for status, count in sorted(
            actionable_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        actionable_status_by_kind = {}

        for relationship in (
            actionable_relationships
        ):
            actionable_status_by_kind.setdefault(
                relationship.kind.value,
                Counter(),
            )[
                relationship.status.value
            ] += 1

        typer.echo(
            "  Actionable relationship statuses by kind:"
        )

        for kind in sorted(
            actionable_status_by_kind
        ):
            typer.echo(
                f"    {kind}:"
            )

            for status, count in sorted(
                actionable_status_by_kind[
                    kind
                ].items()
            ):
                typer.echo(
                    f"      {status}: {count}"
                )

        apk_vintf_structural_relationships = tuple(
            relationship
            for relationship
            in actionable_relationships
            if isinstance(
                relationship,
                AndroidUniverseApkVintfStructuralProviderRelationship,
            )
        )

        typer.echo(
            (
                "  APK VINTF structural-provider relationships: "
                f"{len(apk_vintf_structural_relationships)}"
            )
        )

        for relationship in sorted(
            apk_vintf_structural_relationships,
            key=lambda item: (
                item.canonical_name,
                item.apk_package.requirement_id,
                item.relationship_id,
            ),
        ):
            applicability = (
                relationship_applicability_by_id[
                    relationship.relationship_id
                ]
            )

            apk_package = (
                relationship.apk_package
            )

            apk_android_path = (
                apk_package
                .source
                .source
                .apk_android_path
                .as_posix()
            )

            typer.echo(
                (
                    "    "
                    f"[{relationship.status.value}] "
                    f"{relationship.canonical_name}"
                )
            )

            typer.echo(
                (
                    "      applicability: "
                    f"{applicability.status.value}"
                )
            )

            typer.echo(
                (
                    "      APK package: "
                    f"{apk_package.package_name}"
                )
            )

            typer.echo(
                (
                    "      APK path: "
                    f"{apk_android_path}"
                )
            )

            typer.echo(
                (
                    "      APK requirement: "
                    f"{apk_package.requirement_id}"
                )
            )

            typer.echo(
                (
                    "      VINTF evidence: "
                    f"{len(relationship.vintf_evidence)}"
                )
            )

            for vintf_evidence_item in sorted(
                relationship.vintf_evidence,
                key=lambda item: (
                    item.document.requirement_id,
                    item.instance,
                    item.canonical_name,
                ),
            ):
                document = (
                    vintf_evidence_item.document
                )

                document_path = (
                    document.android_path.as_posix()
                    if document.android_path is not None
                    else document.source_path.as_posix()
                )

                typer.echo(
                    (
                        "        "
                        f"[{document.semantics.side.value}] "
                        f"{document_path}"
                    )
                )

                typer.echo(
                    (
                        "          document requirement: "
                        f"{document.requirement_id}"
                    )
                )

            typer.echo(
                (
                    "      DEX structural evidence: "
                    f"{len(relationship.provider_evidence)}"
                )
            )

            for provider_evidence_item in sorted(
                relationship.provider_evidence,
                key=lambda item: (
                    item.dex.source.member_index,
                    item.stub_class.definition_index,
                    (
                        item.stub_class
                        .class_type
                        .descriptor
                        .value
                    ),
                ),
            ):
                typer.echo(
                    (
                        "        interface: "
                        f"{provider_evidence_item.interface_type.descriptor.value}"
                    )
                )

                typer.echo(
                    (
                        "        Binder Stub: "
                        f"{provider_evidence_item.stub_class.class_type.descriptor.value}"
                    )
                )

                typer.echo(
                    (
                        "        concrete implementations: "
                        f"{len(provider_evidence_item.implementations)}"
                    )
                )

                for implementation in sorted(
                    provider_evidence_item.implementations,
                    key=lambda item: (
                        item.dex.source.member_index,
                        (
                            item
                            .implementation_class
                            .definition_index
                        ),
                        (
                            item
                            .implementation_class
                            .class_type
                            .descriptor
                            .value
                        ),
                    ),
                ):
                    typer.echo(
                        (
                            "          "
                            f"{implementation.implementation_class.class_type.descriptor.value}"
                        )
                    )

        init_executable_artifact_relationships = tuple(
            relationship
            for relationship
            in actionable_relationships
            if isinstance(
                relationship,
                AndroidUniverseInitExecutableArtifactRelationship,
            )
        )

        init_executable_artifact_nonresolved = tuple(
            relationship
            for relationship
            in init_executable_artifact_relationships
            if relationship.status.value
            != "resolved"
        )

        typer.echo(
            (
                "  Actionable INIT executable-artifact "
                "relationships: "
                f"{len(init_executable_artifact_relationships)}"
            )
        )

        init_executable_artifact_status_counts = Counter(
            relationship.status.value
            for relationship
            in init_executable_artifact_relationships
        )

        for status, count in sorted(
            init_executable_artifact_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        init_executable_artifact_fulfillment_counts = Counter(
            relationship.artifact_fulfillment.value
            for relationship
            in init_executable_artifact_relationships
        )

        absent_active_init_executables = tuple(
            relationship
            for relationship
            in init_executable_artifact_relationships
            if (
                relationship.artifact_fulfillment
                is AndroidUniverseArtifactFulfillmentStatus.ABSENT
            )
        )

        typer.echo(
            "  INIT executable artifact fulfillment:"
        )

        for fulfillment_status in (
            AndroidUniverseArtifactFulfillmentStatus.FULFILLED,
            AndroidUniverseArtifactFulfillmentStatus.ABSENT,
            AndroidUniverseArtifactFulfillmentStatus.INDETERMINATE,
        ):
            count = (
                init_executable_artifact_fulfillment_counts.get(
                    fulfillment_status.value,
                    0,
                )
            )

            if count:
                typer.echo(
                    "    "
                    f"{fulfillment_status.value}: "
                    f"{count}"
                )

        typer.echo(
            (
                "  Absent active INIT executable artifacts: "
                f"{len(absent_active_init_executables)}"
            )
        )

        for relationship in sorted(
            absent_active_init_executables,
            key=lambda item: (
                item.executable_path,
                item.init_service.name,
                item.init_service.requirement_id,
            ),
        ):
            typer.echo(
                (
                    "    "
                    f"{relationship.init_service.name} -> "
                    f"{relationship.executable_path}"
                )
            )

        typer.echo(
            (
                "  Non-resolved actionable INIT "
                "executable-artifact relationships: "
                f"{len(init_executable_artifact_nonresolved)}"
            )
        )

        for relationship in sorted(
            init_executable_artifact_nonresolved,
            key=lambda item: (
                item.status.value,
                item.executable_path,
                item.init_service.name,
                item.init_service.requirement_id,
            ),
        ):
            applicability = (
                relationship_applicability_by_id[
                    relationship.relationship_id
                ]
            )

            service = (
                relationship.init_service
            )

            source_android_path = (
                service.android_path.as_posix()
                if service.android_path is not None
                else "<none>"
            )

            typer.echo(
                (
                    "    "
                    f"[{relationship.status.value}] "
                    f"{service.name}"
                )
            )

            typer.echo(
                (
                    "      executable: "
                    f"{relationship.executable_path}"
                )
            )

            typer.echo(
                (
                    "      INIT source: "
                    f"{source_android_path}"
                )
            )

            typer.echo(
                (
                    "      applicability: "
                    f"{applicability.status.value}"
                )
            )

            typer.echo(
                (
                    "      candidate artifacts: "
                    f"{len(relationship.matched_artifacts)}"
                )
            )

            for artifact in (
                relationship.matched_artifacts
            ):
                artifact_kinds = ", ".join(
                    sorted(
                        kind.value
                        for kind
                        in artifact.kinds
                    )
                )

                typer.echo(
                    (
                        "        "
                        f"{artifact.partition_name}:"
                        f"{artifact.android_path}"
                    )
                )

                typer.echo(
                    (
                        "          kinds: "
                        f"{artifact_kinds}"
                    )
                )

                typer.echo(
                    (
                        "          disposition: "
                        f"{artifact.disposition.value}"
                    )
                )

                typer.echo(
                    (
                        "          classification origin: "
                        f"{artifact.classification_origin.value}"
                    )
                )

                typer.echo(
                    (
                        "          identity: "
                        f"{artifact.identity_key}"
                    )
                )

        service_target_substantiation_by_relationship_id = {
            relationship.relationship_id: conclusion
            for conclusion
            in universe_result.init_service_target_substantiations
            for relationship
            in conclusion.relationships
        }

        semantically_classified_unresolved = []
        semantically_unclassified_unresolved = []
        semantic_closure_counts = Counter()

        for relationship in (
            actionable_relationships
        ):
            if (
                relationship.status.value
                != "unresolved"
            ):
                continue

            kind = relationship.kind.value
            classified = False
            closure_kind = None

            if (
                kind
                == "init_executable_artifact"
            ):
                fulfillment = (
                    relationship
                    .artifact_fulfillment
                    .value
                )

                if fulfillment != "indeterminate":
                    classified = True
                    closure_kind = (
                        "executable_artifact_"
                        f"{fulfillment}"
                    )

            elif (
                kind
                == "init_seclabel_selinux_type"
            ):
                fulfillment = (
                    relationship
                    .type_fulfillment
                    .value
                )

                if fulfillment != "indeterminate":
                    classified = True
                    closure_kind = (
                        "selinux_type_"
                        f"{fulfillment}"
                    )

            elif (
                kind
                == "init_service_control"
            ):
                substantiation = (
                    service_target_substantiation_by_relationship_id
                    .get(
                        relationship.relationship_id
                    )
                )

                if (
                    substantiation is not None
                    and (
                        substantiation
                        .classification
                        .value
                        != "unknown"
                    )
                ):
                    classified = True
                    closure_kind = (
                        "service_target_"
                        f"{substantiation.classification.value}"
                    )

            if classified:
                semantically_classified_unresolved.append(
                    relationship
                )

                semantic_closure_counts[
                    closure_kind
                ] += 1
            else:
                semantically_unclassified_unresolved.append(
                    relationship
                )

        typer.echo(
            (
                "  Actionable structurally unresolved "
                "semantic closure:"
            )
        )

        typer.echo(
            (
                "    classified: "
                f"{len(semantically_classified_unresolved)}"
            )
        )

        typer.echo(
            (
                "    unclassified: "
                f"{len(semantically_unclassified_unresolved)}"
            )
        )

        for closure_kind, count in sorted(
            semantic_closure_counts.items()
        ):
            typer.echo(
                (
                    "    "
                    f"{closure_kind}: {count}"
                )
            )

        for relationship in (
            semantically_unclassified_unresolved
        ):
            typer.echo(
                (
                    "    OPEN: "
                    f"{relationship.kind.value} "
                    f"{relationship.relationship_id}"
                )
            )

        unresolved_event_trigger_relationships = tuple(
            relationship
            for relationship in actionable_relationships
            if (
                relationship.kind.value
                == "init_event_trigger"
                and relationship.status.value
                == "unresolved"
            )
        )

        typer.echo(
            "  Unresolved actionable INIT event triggers:"
        )

        for relationship in (
            unresolved_event_trigger_relationships
        ):
            typer.echo(
                (
                    "    "
                    f"{relationship.event}"
                    f" [{relationship.init_action.source_path.as_posix()}]"
                )
            )

        init_seclabel_relationships = tuple(
            relationship
            for relationship
            in actionable_relationships
            if (
                relationship.kind.value
                == "init_seclabel_selinux_type"
            )
        )

        init_seclabel_fulfillment_counts = Counter(
            relationship.type_fulfillment.value
            for relationship
            in init_seclabel_relationships
        )

        typer.echo(
            "  INIT seclabel SELinux type fulfillment:"
        )

        for status, count in sorted(
            init_seclabel_fulfillment_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        absent_active_init_seclabel_types = tuple(
            relationship
            for relationship
            in init_seclabel_relationships
            if (
                relationship.type_fulfillment.value
                == "absent"
            )
        )

        typer.echo(
            (
                "  Absent active INIT seclabel SELinux types: "
                f"{len(absent_active_init_seclabel_types)}"
            )
        )

        for relationship in (
            absent_active_init_seclabel_types
        ):
            typer.echo(
                (
                    "    "
                    f"{relationship.selinux_type}"
                    f" <- {relationship.seclabel}"
                    f" [{relationship.init_service.source_path.as_posix()}]"
                )
            )

        init_class_control_relationships = tuple(
            relationship
            for relationship
            in relationships
            if (
                relationship.kind.value
                == "init_class_control"
            )
        )

        typer.echo(
            (
                "  INIT class-control relationships: "
                f"{len(init_class_control_relationships)}"
            )
        )

        class_control_status_counts = Counter(
            relationship.status.value
            for relationship
            in init_class_control_relationships
        )

        for status, count in sorted(
            class_control_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        unresolved_class_controls = tuple(
            relationship
            for relationship
            in init_class_control_relationships
            if (
                relationship.status.value
                == "unresolved"
            )
        )

        typer.echo(
            "  Unresolved INIT class-control targets:"
        )

        for relationship in (
            unresolved_class_controls
        ):
            source_owner = getattr(
                relationship,
                "init_action",
                None,
            )

            if source_owner is None:
                source_owner = getattr(
                    relationship,
                    "init_service",
                    None,
                )

            source_path = (
                source_owner.source_path.as_posix()
                if source_owner is not None
                else "<unknown>"
            )

            expanded_target = getattr(
                relationship,
                "expanded_target",
                None,
            )

            if expanded_target is None:
                target_display = (
                    relationship.target
                )
            else:
                target_display = (
                    f"{relationship.target}"
                    f" -> "
                    f"{expanded_target}"
                )

            typer.echo(
                (
                    "    "
                    f"{target_display}"
                    f" [{source_path}]"
                )
            )

        unresolved_service_controls = tuple(
            relationship
            for relationship
            in relationships
            if (
                relationship.kind.value
                == "init_service_control"
                and relationship.status.value
                == "unresolved"
            )
        )

        typer.echo(
            "  Unresolved INIT service-control targets:"
        )

        for relationship in (
            unresolved_service_controls
        ):
            source_owner = getattr(
                relationship,
                "init_action",
                None,
            )

            if source_owner is None:
                source_owner = getattr(
                    relationship,
                    "init_service",
                    None,
                )

            source_path = (
                source_owner.source_path.as_posix()
                if source_owner is not None
                else "<unknown>"
            )

            expanded_target = getattr(
                relationship,
                "expanded_target",
                None,
            )

            if expanded_target is None:
                target_display = (
                    relationship.target
                )
            else:
                target_display = (
                    f"{relationship.target}"
                    f" -> "
                    f"{expanded_target}"
                )

            typer.echo(
                (
                    "    "
                    f"{target_display}"
                    f" [{source_path}]"
                )
            )

        target_substantiations = (
            universe_result.init_service_target_substantiations
        )

        typer.echo(
            "  Unresolved INIT service-target substantiation:"
        )

        typer.echo(
            (
                "    Targets: "
                f"{len(target_substantiations)}"
            )
        )

        target_substantiated_count = sum(
            1
            for item
            in target_substantiations
            if item.substantiated
        )

        typer.echo(
            (
                "    Substantiated by canonical evidence: "
                f"{target_substantiated_count}"
            )
        )

        typer.echo(
            (
                "    Without canonical substantiation evidence: "
                f"{(
                    len(target_substantiations)
                    - target_substantiated_count
                )}"
            )
        )

        for item in target_substantiations:
            target_status = (
                "substantiated"
                if item.substantiated
                else "unsubstantiated"
            )

            typer.echo(
                (
                    "    "
                    f"{item.target}: "
                    f"{target_status}"
                    f" classification={item.classification.value}"
                    f" controls={len(item.relationships)}"
                    f" selinux_contexts="
                    f"{len(item.selinux_context_evidence)}"
                    f" control_peers="
                    f"{len(item.control_peer_evidence)}"
                )
            )

            for context_evidence in (
                item.selinux_context_evidence
            ):
                typer.echo(
                    (
                        "      "
                        f"{context_evidence.kind.value}: "
                        f"{context_evidence.selector} -> "
                        f"{context_evidence.context}"
                    )
                )

            for peer_evidence in (
                item.control_peer_evidence
            ):
                typer.echo(
                    (
                        "      control-peer: "
                        f"{peer_evidence.control_kind} "
                        f"{peer_evidence.target}"
                        " [resolved]"
                    )
                )

        typer.echo(
            (
                "  INIT onrestart service-control relationships: "
                f"{len(init_onrestart_control_relationships)}"
            )
        )

        control_status_counts = Counter(
            relationship.status.value
            for relationship
            in init_onrestart_control_relationships
        )

        for status, count in sorted(
            control_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        typer.echo(
            (
                "  INIT onrestart property-command relationships: "
                f"{len(init_onrestart_property_relationships)}"
            )
        )

        property_status_counts = Counter(
            relationship.status.value
            for relationship
            in init_onrestart_property_relationships
        )

        for status, count in sorted(
            property_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )

        if init_cli_uninterpreted_options:
            typer.echo(
                "  Uninterpreted option vocabulary:"
            )

            for keyword, count in sorted(
                init_cli_uninterpreted_options.items(),
                key=lambda item: (
                    -item[1],
                    item[0],
                ),
            ):
                typer.echo(
                    f"    {keyword}: {count}"
                )

        vintf_cli_requirements = (
            universe_result.vintf_requirements
        )

        vintf_cli_document_type_counts = Counter(
            (
                requirement.semantics.kind.value,
                requirement.semantics.side.value,
            )
            for requirement
            in vintf_cli_requirements
        )

        vintf_cli_hals = tuple(
            hal
            for requirement
            in vintf_cli_requirements
            for hal
            in requirement.semantics.hals
        )

        vintf_cli_hal_format_counts = Counter(
            hal.format.value
            for hal
            in vintf_cli_hals
        )

        vintf_cli_kernels = tuple(
            kernel
            for requirement
            in vintf_cli_requirements
            for kernel
            in requirement.semantics.kernels
        )

        vintf_cli_direct_kernel_configs = tuple(
            config
            for kernel
            in vintf_cli_kernels
            for config
            in kernel.configs
        )

        vintf_cli_kernel_conditions = tuple(
            condition
            for kernel
            in vintf_cli_kernels
            for condition
            in kernel.conditions
        )

        vintf_cli_conditional_kernel_configs = tuple(
            config
            for condition
            in vintf_cli_kernel_conditions
            for config
            in condition.configs
        )

        vintf_cli_interfaces = tuple(
            interface
            for hal
            in vintf_cli_hals
            for interface
            in hal.interfaces
        )

        vintf_cli_exact_instances = tuple(
            instance
            for interface
            in vintf_cli_interfaces
            for instance
            in interface.instances
        )

        vintf_cli_regex_instances = tuple(
            instance
            for interface
            in vintf_cli_interfaces
            for instance
            in interface.regex_instances
        )

        vintf_cli_fqnames = tuple(
            fqname
            for hal
            in vintf_cli_hals
            for fqname
            in hal.fqnames
        )

        vintf_cli_sepolicy_sections = sum(
            len(
                requirement.semantics.sepolicy
            )
            for requirement
            in vintf_cli_requirements
        )

        vintf_cli_system_sdk_sections = sum(
            len(
                requirement.semantics.system_sdk
            )
            for requirement
            in vintf_cli_requirements
        )

        vintf_cli_avb_sections = sum(
            len(
                requirement.semantics.avb
            )
            for requirement
            in vintf_cli_requirements
        )

        vintf_cli_uninterpreted_elements = tuple(
            item
            for requirement
            in vintf_cli_requirements
            for item
            in requirement.semantics.uninterpreted_elements
        )

        vintf_cli_uninterpreted_attributes = tuple(
            item
            for requirement
            in vintf_cli_requirements
            for item
            in requirement.semantics.uninterpreted_attributes
        )

        boot_cli_requirements = (
            universe_result.boot_requirements
        )


        boot_cli_argument_count = sum(
            len(
                requirement.semantics.command_line.arguments
            )
            for requirement
            in boot_cli_requirements
        )

        boot_cli_assignment_count = sum(
            1
            for requirement
            in boot_cli_requirements
            for argument
            in requirement.semantics.command_line.arguments
            if argument.kind.value == "assignment"
        )

        boot_cli_flag_count = sum(
            1
            for requirement
            in boot_cli_requirements
            for argument
            in requirement.semantics.command_line.arguments
            if argument.kind.value == "flag"
        )

        boot_cli_argument_key_counts = Counter(
            argument.key
            for requirement
            in boot_cli_requirements
            for argument
            in requirement.semantics.command_line.arguments
        )

        boot_cli_repeated_argument_keys = {
            key: count
            for key, count
            in boot_cli_argument_key_counts.items()
            if count > 1
        }


        bootconfig_semantics = tuple(
            requirement.semantics.bootconfig
            for requirement
            in boot_cli_requirements
            if (
                requirement.container_format
                == "android_vendor_boot"
                and requirement.semantics.bootconfig
                is not None
            )
        )

        bootconfig_declarations = tuple(
            declaration
            for semantics
            in bootconfig_semantics
            for declaration
            in semantics.declarations
        )

        bootconfig_unparsed_line_count = sum(
            semantics.unparsed_line_count
            for semantics
            in bootconfig_semantics
        )

        bootconfig_key_counts: dict[
            str,
            int,
        ] = {}

        for declaration in bootconfig_declarations:
            bootconfig_key_counts[
                declaration.key
            ] = (
                bootconfig_key_counts.get(
                    declaration.key,
                    0,
                )
                + 1
            )

        bootconfig_repeated_keys = {
            key: count
            for key, count
            in bootconfig_key_counts.items()
            if count > 1
        }


        bootconfig_boot_device_selections = tuple(
            selection
            for semantics
            in bootconfig_semantics
            for selection
            in semantics.boot_device_selections
        )

        bootconfig_module_loading_policies = tuple(
            policy
            for semantics
            in bootconfig_semantics
            for policy
            in semantics.module_loading_policies
        )

        typer.echo(
            "Ueventd Universe coverage:"
        )

        typer.echo(
            (
                "  Parsed ueventd sources: "
                f"{len(parsing.filesystem.ueventd_files)}"
            )
        )

        typer.echo(
            (
                "  Parsed ueventd declarations: "
                f"{ueventd_cli_parsed_declarations}"
            )
        )

        typer.echo(
            (
                "  Universe ueventd requirements: "
                f"{len(ueventd_cli_requirements)}"
            )
        )

        typer.echo(
            (
                "  UEVENTD source contexts: "
                f"{len(ueventd_cli_source_contexts)}"
            )
        )

        typer.echo(
            (
                "  Contexts with unparsed lines: "
                f"{ueventd_cli_contexts_with_unparsed_lines}"
            )
        )

        typer.echo(
            (
                "  Preserved unparsed lines: "
                f"{ueventd_cli_context_unparsed_lines}"
            )
        )

        typer.echo(
            (
                "  Import requirements: "
                f"{ueventd_cli_family_counts.get(
                    "AndroidUniverseUeventdImportRequirement",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Device-rule requirements: "
                f"{ueventd_cli_family_counts.get(
                    "AndroidUniverseUeventdDeviceRuleRequirement",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Sysfs-rule requirements: "
                f"{ueventd_cli_family_counts.get(
                    "AndroidUniverseUeventdSysfsRuleRequirement",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Subsystem requirements: "
                f"{len(ueventd_cli_subsystem_requirements)}"
            )
        )

        typer.echo(
            (
                "  Firmware-directories requirements: "
                f"{ueventd_cli_family_counts.get(
                    "AndroidUniverseUeventdFirmwareDirectoriesRequirement",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Socket-rcvbuf requirements: "
                f"{ueventd_cli_family_counts.get(
                    "AndroidUniverseUeventdSocketRcvbufRequirement",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Subsystem options: "
                f"{len(ueventd_cli_subsystem_options)}"
            )
        )

        typer.echo(
            (
                "  Semantic subsystem options: "
                f"{len(ueventd_cli_semantic_subsystem_options)}"
            )
        )

        typer.echo(
            (
                "  Distinct subsystem option keywords: "
                f"{len(ueventd_cli_option_keywords)}"
            )
        )

        typer.echo(
            (
                "  Interpreted subsystem option keywords: "
                f"{len(ueventd_cli_interpreted_option_keywords)}"
            )
        )

        typer.echo(
            (
                "  Uninterpreted subsystem options: "
                f"{len(ueventd_cli_uninterpreted_subsystem_options)}"
            )
        )

        typer.echo(
            (
                "  Unparsed ueventd lines: "
                f"{ueventd_cli_unparsed_lines}"
            )
        )

        typer.echo(
            "Architecture Universe coverage:"
        )

        architecture = (
            universe_result.architecture
        )

        if architecture is None:
            typer.echo(
                "  Architecture conclusion: unavailable"
            )
        else:
            agreed = tuple(
                conclusion
                for conclusion
                in architecture.conclusions
                if conclusion.status.value
                == "agreed"
            )

            absent = tuple(
                conclusion
                for conclusion
                in architecture.conclusions
                if conclusion.status.value
                == "absent"
            )

            conflicting = tuple(
                conclusion
                for conclusion
                in architecture.conclusions
                if conclusion.status.value
                == "conflicting"
            )

            unresolved = tuple(
                conclusion
                for conclusion
                in architecture.conclusions
                if conclusion.status.value
                == "unresolved"
            )

            typer.echo(
                "  Architecture facts: "
                f"{len(architecture.conclusions)}"
            )

            typer.echo(
                "  Agreed: "
                f"{len(agreed)}"
            )

            typer.echo(
                "  Absent: "
                f"{len(absent)}"
            )

            typer.echo(
                "  Conflicting: "
                f"{len(conflicting)}"
            )

            typer.echo(
                "  Unresolved: "
                f"{len(unresolved)}"
            )

            for conclusion in (
                architecture.conclusions
            ):
                typer.echo(
                    "  "
                    f"{conclusion.fact}: "
                    f"{conclusion.value!r} "
                    f"[{conclusion.status.value}]"
                )

                if not conclusion.observations:
                    typer.echo(
                        "    evidence: none"
                    )
                    continue

                for observation in (
                    conclusion.observations
                ):
                    if (
                        observation.property_evidence
                        is not None
                    ):
                        property_evidence = (
                            observation
                            .property_evidence
                        )

                        source_identity = (
                            property_evidence
                            .model_source
                            .android_path
                            .as_posix()
                        )

                        if (
                            observation.property_derivation
                            is not None
                        ):
                            typer.echo(
                                "    android-derived: "
                                f"{observation.value!r}"
                            )
                            typer.echo(
                                "      from property: "
                                f"{property_evidence.fact.value!r} "
                                f"[{property_evidence.fact.property_key}] "
                                f"[{source_identity}]"
                            )
                            typer.echo(
                                "      rule: "
                                f"{observation.property_derivation}"
                            )
                        else:
                            typer.echo(
                                "    property: "
                                f"{observation.value!r} "
                                f"[{property_evidence.fact.property_key}] "
                                f"[{source_identity}]"
                            )

                    elif (
                        observation.knowledge_module
                        is not None
                    ):
                        module = (
                            observation
                            .knowledge_module
                        )

                        typer.echo(
                            "    knowledge: "
                            f"{observation.value!r} "
                            f"[{module.module_id}] "
                            f"[{module.scope.value}]"
                        )

        typer.echo(
            "SELinux source requirement population:"
        )
        typer.echo(
            "  Universe SELinux requirements: "
            f"{len(universe_result.selinux_requirements)}"
        )

        for requirement in universe_result.selinux_requirements:
            android_path = (
                requirement.android_path.as_posix()
                if requirement.android_path is not None
                else "<none>"
            )

            typer.echo(
                f"  {android_path}"
            )
            typer.echo(
                f"    kind: {requirement.kind.value}"
            )
            typer.echo(
                "    compiled policy: "
                f"{requirement.is_compiled_policy}"
            )
            typer.echo(
                f"    opaque: {requirement.is_opaque}"
            )
            typer.echo(
                "    source path: "
                f"{requirement.source_path.as_posix()}"
            )
            typer.echo(
                "    requirement id: "
                f"{requirement.requirement_id}"
            )

        typer.echo()

        selinux_policy_graph = (
            universe_result.selinux_policy_graph
        )

        typer.echo(
            "MAC_PERMISSIONS Universe coverage:"
        )

        if selinux_policy_graph is None:
            typer.echo(
                "  Policy graph: unavailable"
            )
        else:
            mac_permissions_requirements = (
                selinux_policy_graph
                .mac_permissions_requirements
            )

            mac_permissions_sources = tuple(
                requirement
                for requirement
                in universe_result.selinux_requirements
                if requirement.mac_permissions_requirements
            )

            signer_requirements = tuple(
                requirement
                for requirement
                in mac_permissions_requirements
                if requirement.kind == "signer"
            )

            default_requirements = tuple(
                requirement
                for requirement
                in mac_permissions_requirements
                if requirement.kind == "default"
            )

            package_requirements = tuple(
                package
                for requirement
                in mac_permissions_requirements
                for package
                in requirement.package_requirements
            )

            direct_seinfo_assignments = tuple(
                value
                for requirement
                in mac_permissions_requirements
                for value
                in requirement.seinfo_values
            )

            typer.echo(
                "  Sources: "
                f"{len(mac_permissions_sources)}"
            )
            typer.echo(
                "  Policy rules: "
                f"{len(mac_permissions_requirements)}"
            )
            typer.echo(
                "  Signer rules: "
                f"{len(signer_requirements)}"
            )
            typer.echo(
                "  Default rules: "
                f"{len(default_requirements)}"
            )
            typer.echo(
                "  Package refinements: "
                f"{len(package_requirements)}"
            )
            typer.echo(
                "  Direct seinfo assignments: "
                f"{len(direct_seinfo_assignments)}"
            )

            for source_requirement in (
                mac_permissions_sources
            ):
                source_identity = (
                    source_requirement
                    .android_path
                    .as_posix()
                    if (
                        source_requirement
                        .android_path
                        is not None
                    )
                    else (
                        source_requirement
                        .source_path
                        .as_posix()
                    )
                )

                typer.echo(
                    f"  {source_identity}:"
                )
                typer.echo(
                    "    rules: "
                    f"{len(source_requirement.mac_permissions_requirements)}"
                )

                for requirement in (
                    source_requirement
                    .mac_permissions_requirements
                ):
                    typer.echo(
                        "    "
                        f"{requirement.kind}"
                        f" line={requirement.source_line}"
                    )

                    if requirement.signer_selectors:
                        typer.echo(
                            "      signer selectors: "
                            + ", ".join(
                                requirement
                                .signer_selectors
                            )
                        )

                    if requirement.seinfo_values:
                        typer.echo(
                            "      seinfo: "
                            + ", ".join(
                                requirement
                                .seinfo_values
                            )
                        )

                    if (
                        requirement
                        .package_requirements
                    ):
                        typer.echo(
                            "      packages: "
                            f"{len(requirement.package_requirements)}"
                        )

        typer.echo()

        genfs_labels_version_conclusion = (
            universe_result.selinux_policy_graph
            .genfs_labels_version_conclusion
            if universe_result.selinux_policy_graph is not None
            else None
        )

        typer.echo(
            "Genfs labels version Universe coverage:"
        )

        if genfs_labels_version_conclusion is None:
            typer.echo(
                "  Conclusion: unavailable"
            )
        else:
            typer.echo(
                "  State: "
                f"{genfs_labels_version_conclusion.state.value}"
            )
            typer.echo(
                "  Canonical value: "
                f"{genfs_labels_version_conclusion.value!r}"
            )
            typer.echo(
                "  Observed values: "
                f"{len(genfs_labels_version_conclusion.observed_values)}"
            )
            typer.echo(
                "  Evidence observations: "
                f"{len(genfs_labels_version_conclusion.evidence)}"
            )

            for requirement in (
                genfs_labels_version_conclusion.evidence
            ):
                source_identity = (
                    requirement.android_path.as_posix()
                    if requirement.android_path is not None
                    else requirement.source_path.as_posix()
                )

                typer.echo(
                    "    "
                    f"{requirement.genfs_labels_version} "
                    f"[{source_identity}]"
                )

        typer.echo(
            "Device capability conclusions:"
        )

        device_capabilities = (
            universe_result.device_capabilities
        )

        if not device_capabilities:
            typer.echo(
                "  none"
            )
        else:
            for capability in device_capabilities:
                typer.echo(
                    "  "
                    f"{capability.capability.value}: "
                    f"{capability.status.value}"
                )

                for evidence_item in capability.evidence:
                    typer.echo(
                        "    "
                        f"{evidence_item.hal.name} "
                        f"[{evidence_item.document.requirement_id}]"
                    )

                for scope_item in capability.scope_evidence:
                    typer.echo(
                        "    scope: active device manifest "
                        f"[{scope_item.document.requirement_id}]"
                    )

        typer.echo()

        typer.echo(
            "VINTF applicability coverage:"
        )

        vintf_applicability = (
            universe_result.vintf_applicability
        )

        if vintf_applicability is None:
            typer.echo(
                "  Applicability: unavailable"
            )
        else:
            document_applicability = (
                vintf_applicability
                .document_applicability
            )

            document_active = tuple(
                item
                for item in document_applicability
                if item.status.value == "active"
            )

            document_conditional = tuple(
                item
                for item in document_applicability
                if item.status.value == "conditional"
            )

            document_alternative = tuple(
                item
                for item in document_applicability
                if item.status.value == "alternative"
            )

            document_unresolved = tuple(
                item
                for item in document_applicability
                if item.status.value == "unresolved"
            )

            typer.echo(
                "  Installed documents: "
                f"{len(document_applicability)}"
            )
            typer.echo(
                "  Installed active: "
                f"{len(document_active)}"
            )
            typer.echo(
                "  Installed conditional: "
                f"{len(document_conditional)}"
            )
            typer.echo(
                "  Installed alternative: "
                f"{len(document_alternative)}"
            )
            typer.echo(
                "  Installed unresolved: "
                f"{len(document_unresolved)}"
            )

            selection_conclusions = (
                vintf_applicability
                .selection_conclusions
            )

            selection_active = tuple(
                item
                for item in selection_conclusions
                if (
                    item.applicability.status.value
                    == "active"
                )
            )

            selection_conditional = tuple(
                item
                for item in selection_conclusions
                if (
                    item.applicability.status.value
                    == "conditional"
                )
            )

            selection_alternative = tuple(
                item
                for item in selection_conclusions
                if (
                    item.applicability.status.value
                    == "alternative"
                )
            )

            selection_unresolved = tuple(
                item
                for item in selection_conclusions
                if (
                    item.applicability.status.value
                    == "unresolved"
                )
            )

            typer.echo(
                "  Knowledge fallback selections: "
                f"{len(selection_conclusions)}"
            )
            typer.echo(
                "  Knowledge fallback active: "
                f"{len(selection_active)}"
            )
            typer.echo(
                "  Knowledge fallback conditional: "
                f"{len(selection_conditional)}"
            )
            typer.echo(
                "  Knowledge fallback alternative: "
                f"{len(selection_alternative)}"
            )
            typer.echo(
                "  Knowledge fallback unresolved: "
                f"{len(selection_unresolved)}"
            )

            if document_unresolved:
                typer.echo(
                    "  Unresolved installed documents:"
                )

                for item in document_unresolved:
                    typer.echo(
                        "    "
                        f"{item.requirement_id}"
                    )

            typer.echo(
                "  Knowledge fallback selections:"
            )

            if not selection_conclusions:
                typer.echo(
                    "    none"
                )
            else:
                for conclusion in (
                    selection_conclusions
                ):
                    applicability = (
                        conclusion.applicability
                    )

                    typer.echo(
                        "    "
                        f"{conclusion.role.value}: "
                        f"{conclusion.source_path} "
                        f"[{applicability.status.value}]"
                    )

                    if (
                        applicability.selector_key
                        is not None
                    ):
                        typer.echo(
                            "      selector: "
                            f"{applicability.selector_key}="
                            f"{applicability.selector_value!r}"
                        )

                    if (
                        applicability.alternative_group
                        is not None
                    ):
                        typer.echo(
                            "      alternative group: "
                            f"{applicability.alternative_group}"
                        )

                    for observation in (
                        conclusion
                        .knowledge_observations
                    ):
                        module = (
                            observation
                            .knowledge_module
                        )

                        typer.echo(
                            "      knowledge: "
                            f"[{module.module_id}] "
                            f"[{module.scope.value}]"
                        )

        typer.echo()

        typer.echo(
            "VINTF Universe coverage:"
        )

        typer.echo(
            (
                "  Parsed VINTF documents: "
                f"{len(parsing.filesystem.vintf_documents)}"
            )
        )

        typer.echo(
            (
                "  Universe VINTF requirements: "
                f"{len(vintf_cli_requirements)}"
            )
        )

        typer.echo(
            (
                "  Manifest/device documents: "
                f"{vintf_cli_document_type_counts.get(
                    ("manifest", "device"),
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Manifest/framework documents: "
                f"{vintf_cli_document_type_counts.get(
                    ("manifest", "framework"),
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Compatibility-matrix/device documents: "
                f"{vintf_cli_document_type_counts.get(
                    ("compatibility-matrix", "device"),
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Compatibility-matrix/framework documents: "
                f"{vintf_cli_document_type_counts.get(
                    ("compatibility-matrix", "framework"),
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  HAL requirements: "
                f"{len(vintf_cli_hals)}"
            )
        )

        typer.echo(
            (
                "    AIDL: "
                f"{vintf_cli_hal_format_counts.get(
                    "aidl",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "    HIDL: "
                f"{vintf_cli_hal_format_counts.get(
                    "hidl",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "    native: "
                f"{vintf_cli_hal_format_counts.get(
                    "native",
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Kernel requirements: "
                f"{len(vintf_cli_kernels)}"
            )
        )

        typer.echo(
            (
                "  Direct kernel configs: "
                f"{len(vintf_cli_direct_kernel_configs)}"
            )
        )

        typer.echo(
            (
                "  Kernel conditions: "
                f"{len(vintf_cli_kernel_conditions)}"
            )
        )

        typer.echo(
            (
                "  Conditional kernel configs: "
                f"{len(vintf_cli_conditional_kernel_configs)}"
            )
        )

        typer.echo(
            (
                "  Total kernel configs: "
                f"{(
                    len(vintf_cli_direct_kernel_configs)
                    + len(vintf_cli_conditional_kernel_configs)
                )}"
            )
        )

        typer.echo(
            (
                "  Exact interface instances: "
                f"{len(vintf_cli_exact_instances)}"
            )
        )

        typer.echo(
            (
                "  Regex interface instances: "
                f"{len(vintf_cli_regex_instances)}"
            )
        )

        typer.echo(
            (
                "  FQNames: "
                f"{len(vintf_cli_fqnames)}"
            )
        )

        typer.echo(
            (
                "  SEPolicy sections: "
                f"{vintf_cli_sepolicy_sections}"
            )
        )

        typer.echo(
            (
                "  System-SDK sections: "
                f"{vintf_cli_system_sdk_sections}"
            )
        )

        typer.echo(
            (
                "  AVB sections: "
                f"{vintf_cli_avb_sections}"
            )
        )

        typer.echo(
            (
                "  Uninterpreted VINTF elements: "
                f"{len(vintf_cli_uninterpreted_elements)}"
            )
        )

        typer.echo(
            (
                "  Uninterpreted VINTF attributes: "
                f"{len(vintf_cli_uninterpreted_attributes)}"
            )
        )

        typer.echo(
            "Boot-family Universe coverage:"
        )
        typer.echo(
            (
                "  Parsing boot images: "
                f"{len(parsing.boot_images)}"
            )
        )
        typer.echo(
            (
                "  Universe boot-family requirements: "
                f"{len(boot_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe source identity match: "
                f"{(
                    len(boot_cli_requirements)
                    == len(parsing.boot_images)
                    and all(
                        requirement.source is parsed
                        for requirement, parsed
                        in zip(
                            boot_cli_requirements,
                            parsing.boot_images,
                            strict=True,
                        )
                    )
                )}"
            )
        )

        boot_cli_container_formats = Counter(
            requirement.container_format
            for requirement
            in boot_cli_requirements
        )

        boot_cli_container_kinds = Counter(
            requirement.container_kind
            for requirement
            in boot_cli_requirements
        )

        typer.echo(
            "  Container formats:"
        )

        if boot_cli_container_formats:
            for (
                container_format,
                count,
            ) in sorted(
                boot_cli_container_formats.items()
            ):
                typer.echo(
                    f"    {container_format}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  Container kinds:"
        )

        if boot_cli_container_kinds:
            for (
                container_kind,
                count,
            ) in sorted(
                boot_cli_container_kinds.items()
            ):
                typer.echo(
                    f"    {container_kind}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        for boot_cli_requirement in boot_cli_requirements:
            boot_cli_kind = (
                boot_cli_requirement.container_kind
            )

            typer.echo(
                f"  {boot_cli_kind}:"
            )
            typer.echo(
                (
                    "    container format: "
                    f"{boot_cli_requirement.container_format}"
                )
            )
            typer.echo(
                (
                    "    partition: "
                    f"{boot_cli_requirement.partition.name}"
                )
            )

            boot_cli_semantics = boot_cli_requirement.semantics
            typer.echo(
                f"    header version: {boot_cli_semantics.header_version}"
            )

            if hasattr(boot_cli_semantics, "android_version"):
                boot_cli_android_version = boot_cli_semantics.android_version
                typer.echo(
                    f"    encoded OS version: {boot_cli_android_version.encoded}"
                )
                typer.echo(
                    "    Android version: "
                    f"{boot_cli_android_version.major}."
                    f"{boot_cli_android_version.minor}."
                    f"{boot_cli_android_version.patch}"
                )

            if hasattr(boot_cli_semantics, "boot_name"):
                typer.echo(
                    f"    boot name: {boot_cli_semantics.boot_name!r}"
                )

            boot_cli_arguments = boot_cli_semantics.command_line.arguments
            boot_cli_local_key_counts = Counter(
                argument.key
                for argument in boot_cli_arguments
            )
            boot_cli_local_repeated_keys = {
                key: count
                for key, count in boot_cli_local_key_counts.items()
                if count > 1
            }

            typer.echo(f"    cmdline arguments: {len(boot_cli_arguments)}")
            typer.echo(
                "    assignments: "
                f"{sum(argument.kind.value == "assignment" for argument in boot_cli_arguments)}"
            )
            typer.echo(
                "    flags: "
                f"{sum(argument.kind.value == "flag" for argument in boot_cli_arguments)}"
            )
            typer.echo(
                f"    distinct argument keys: {len(boot_cli_local_key_counts)}"
            )
            typer.echo(
                f"    repeated argument keys: {len(boot_cli_local_repeated_keys)}"
            )

        typer.echo(
            f"  Total boot-family cmdline arguments: {boot_cli_argument_count}"
        )
        typer.echo(
            f"  Total boot-family assignments: {boot_cli_assignment_count}"
        )
        typer.echo(
            f"  Total boot-family flags: {boot_cli_flag_count}"
        )
        typer.echo(
            f"  Distinct boot-family argument keys: {len(boot_cli_argument_key_counts)}"
        )
        typer.echo(
            f"  Repeated boot-family argument keys: {len(boot_cli_repeated_argument_keys)}"
        )

        if boot_cli_repeated_argument_keys:
            typer.echo("  Repeated argument-key vocabulary:")
            for key, count in sorted(boot_cli_repeated_argument_keys.items()):
                typer.echo(f"    {key}: {count}")

        typer.echo()
        typer.echo(
            "Bootconfig Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed vendor_boot bootconfig payloads: "
                f"{len(bootconfig_semantics)}"
            )
        )
        typer.echo(
            (
                "  Universe bootconfig declarations: "
                f"{len(bootconfig_declarations)}"
            )
        )
        typer.echo(
            (
                "  Bootconfig unparsed lines: "
                f"{bootconfig_unparsed_line_count}"
            )
        )
        typer.echo(
            (
                "  Distinct bootconfig keys: "
                f"{len(bootconfig_key_counts)}"
            )
        )
        typer.echo(
            (
                "  Repeated bootconfig keys: "
                f"{len(bootconfig_repeated_keys)}"
            )
        )

        if bootconfig_key_counts:
            typer.echo(
                "  Bootconfig key vocabulary:"
            )

            for key, count in sorted(
                bootconfig_key_counts.items()
            ):
                typer.echo(
                    f"    {key}: {count}"
                )

        typer.echo(
            (
                "  Boot-device semantic selections: "
                f"{len(bootconfig_boot_device_selections)}"
            )
        )

        for selection in (
            bootconfig_boot_device_selections
        ):
            typer.echo(
                (
                    "    "
                    f"line {selection.source.line_number}: "
                    f"{', '.join(selection.devices)}"
                )
            )

        typer.echo(
            (
                "  First-stage module-loading policies: "
                f"{len(bootconfig_module_loading_policies)}"
            )
        )

        for policy in (
            bootconfig_module_loading_policies
        ):
            typer.echo(
                (
                    "    "
                    f"line {policy.source.line_number}: "
                    f"parallel={policy.parallel}"
                )
            )

        for requirement in boot_cli_requirements:
            if (
                requirement.container_format
                != "android_vendor_boot"
            ):
                continue

            bootconfig = (
                requirement.semantics.bootconfig
            )

            typer.echo(
                "  vendor_boot bootconfig:"
            )

            if bootconfig is None:
                typer.echo(
                    "    not present"
                )
                continue

            typer.echo(
                (
                    "    declarations: "
                    f"{len(bootconfig.declarations)}"
                )
            )
            typer.echo(
                (
                    "    unparsed lines: "
                    f"{bootconfig.unparsed_line_count}"
                )
            )

            for declaration in (
                bootconfig.declarations
            ):
                typer.echo(
                    (
                        "    "
                        f"line {declaration.line_number}: "
                        f"{declaration.key}="
                        f"{declaration.value}"
                    )
                )

        apex_cli_requirements = (
            universe_result.apex_requirements
        )

        apex_cli_names = {
            requirement.apex_name
            for requirement
            in apex_cli_requirements
        }

        apex_cli_versions = {
            requirement.version
            for requirement
            in apex_cli_requirements
        }

        apex_cli_native_provide_count = sum(
            len(
                requirement.provide_native_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_native_require_count = sum(
            len(
                requirement.require_native_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_jni_count = sum(
            len(
                requirement.jni_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_require_shared_count = sum(
            len(
                requirement.require_shared_apex_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_with_require_shared = sum(
            bool(
                requirement.require_shared_apex_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_shared_present_count = sum(
            requirement.provide_shared_apex_libs_present
            for requirement
            in apex_cli_requirements
        )

        apex_cli_shared_true_count = sum(
            requirement.provide_shared_apex_libs
            for requirement
            in apex_cli_requirements
        )

        apex_cli_rebootless_present_count = sum(
            requirement.supports_rebootless_update_present
            for requirement
            in apex_cli_requirements
        )

        apex_cli_rebootless_true_count = sum(
            requirement.supports_rebootless_update
            for requirement
            in apex_cli_requirements
        )

        apex_cli_with_native_provides = sum(
            bool(
                requirement.provide_native_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_with_native_requires = sum(
            bool(
                requirement.require_native_libs
            )
            for requirement
            in apex_cli_requirements
        )

        apex_cli_with_jni = sum(
            bool(
                requirement.jni_libs
            )
            for requirement
            in apex_cli_requirements
        )

        typer.echo()
        typer.echo(
            "APEX Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed APEX packages: "
                f"{len(parsing.apex)}"
            )
        )
        typer.echo(
            (
                "  Universe APEX requirements: "
                f"{len(apex_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Distinct APEX names: "
                f"{len(apex_cli_names)}"
            )
        )
        typer.echo(
            (
                "  Distinct APEX versions: "
                f"{len(apex_cli_versions)}"
            )
        )
        typer.echo(
            (
                "  Native library provides: "
                f"{apex_cli_native_provide_count}"
            )
        )
        typer.echo(
            (
                "  Native library requires: "
                f"{apex_cli_native_require_count}"
            )
        )
        typer.echo(
            (
                "  JNI library declarations: "
                f"{apex_cli_jni_count}"
            )
        )
        typer.echo(
            (
                "  APEXes with native provides: "
                f"{apex_cli_with_native_provides}"
            )
        )
        typer.echo(
            (
                "  APEXes with native requires: "
                f"{apex_cli_with_native_requires}"
            )
        )
        typer.echo(
            (
                "  APEXes with JNI libraries: "
                f"{apex_cli_with_jni}"
            )
        )
        typer.echo(
            (
                "  requireSharedApexLibs declarations: "
                f"{apex_cli_require_shared_count}"
            )
        )
        typer.echo(
            (
                "  APEXes requiring shared APEX libs: "
                f"{apex_cli_with_require_shared}"
            )
        )
        typer.echo(
            (
                "  provideSharedApexLibs explicit: "
                f"{apex_cli_shared_present_count}"
            )
        )
        typer.echo(
            (
                "  provideSharedApexLibs true: "
                f"{apex_cli_shared_true_count}"
            )
        )
        typer.echo(
            (
                "  supportsRebootlessUpdate explicit: "
                f"{apex_cli_rebootless_present_count}"
            )
        )
        typer.echo(
            (
                "  supportsRebootlessUpdate true: "
                f"{apex_cli_rebootless_true_count}"
            )
        )
        typer.echo(
            "  Structured manifest semantic promotion: complete"
        )

        if apex_cli_requirements:
            typer.echo(
                "  APEX requirements:"
            )

            for requirement in (
                apex_cli_requirements
            ):
                typer.echo(
                    (
                        "    "
                        f"{requirement.apex_name} "
                        f"version={requirement.version}"
                    )
                )
                typer.echo(
                    (
                        "      artifact: "
                        f"{requirement.artifact.path}"
                    )
                )
                typer.echo(
                    (
                        "      requirement id: "
                        f"{requirement.requirement_id}"
                    )
                )
                typer.echo(
                    (
                        "      requireSharedApexLibs: "
                        f"{len(requirement.require_shared_apex_libs)}"
                    )
                )
                for value in requirement.require_shared_apex_libs:
                    typer.echo(
                        f"        {value}"
                    )

        elf_cli_requirements = (
            universe_result.elf_requirements
        )

        elf_cli_role_counts = Counter(
            requirement.role.value
            for requirement
            in elf_cli_requirements
        )

        elf_cli_bitness_counts = Counter(
            requirement.bitness
            for requirement
            in elf_cli_requirements
        )

        elf_cli_sonames = tuple(
            requirement.soname
            for requirement
            in elf_cli_requirements
            if requirement.soname is not None
        )

        elf_cli_dependency_count = sum(
            len(requirement.dependencies)
            for requirement
            in elf_cli_requirements
        )

        elf_cli_interpreter_count = sum(
            requirement.interpreter_requirement
            is not None
            for requirement
            in elf_cli_requirements
        )

        elf_cli_soong_build_tuple_requirements = tuple(
            tuple_requirement
            for requirement
            in elf_cli_requirements
            for tuple_requirement
            in requirement.soong_build_tuple_requirements
        )

        elf_cli_soong_domain_counts = Counter(
            requirement.domain
            for requirement
            in elf_cli_soong_build_tuple_requirements
        )

        elf_cli_soong_architecture_counts = Counter(
            requirement.architecture
            for requirement
            in elf_cli_soong_build_tuple_requirements
        )

        elf_cli_soong_arch_variant_counts = Counter(
            requirement.arch_variant
            for requirement
            in elf_cli_soong_build_tuple_requirements
        )

        typer.echo()
        kernel_cli_requirements = (
            universe_result.kernel_requirements
        )

        typer.echo()
        bmp_cli_requirements = (
            universe_result.bmp_requirements
        )

        bmp_cli_bpp = Counter(
            requirement.bits_per_pixel
            for requirement
            in bmp_cli_requirements
        )

        bmp_cli_compression = Counter(
            requirement.compression
            for requirement
            in bmp_cli_requirements
        )

        bmp_cli_dimensions = Counter(
            (
                requirement.width,
                requirement.height,
            )
            for requirement
            in bmp_cli_requirements
        )

        bmp_cli_total_file_bytes = sum(
            requirement.file_size
            for requirement
            in bmp_cli_requirements
        )

        typer.echo()
        typer.echo(
            "BMP Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed BMP resources: "
                f"{len(parsing.bmp)}"
            )
        )
        typer.echo(
            (
                "  Universe BMP requirements: "
                f"{len(bmp_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe BMP identity match: "
                f"{all(
                    requirement.source is parsed
                    for requirement, parsed
                    in zip(
                        bmp_cli_requirements,
                        parsing.bmp,
                        strict=True,
                    )
                )}"
            )
        )
        typer.echo(
            (
                "  Extraction artifact identity match: "
                f"{all(
                    requirement.artifact is parsed.artifact
                    for requirement, parsed
                    in zip(
                        bmp_cli_requirements,
                        parsing.bmp,
                        strict=True,
                    )
                )}"
            )
        )
        typer.echo(
            (
                "  Total BMP file bytes: "
                f"{bmp_cli_total_file_bytes}"
            )
        )

        typer.echo(
            "  Bits-per-pixel:"
        )

        if bmp_cli_bpp:
            for bits_per_pixel, count in sorted(
                bmp_cli_bpp.items()
            ):
                typer.echo(
                    f"    {bits_per_pixel}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  Compression values:"
        )

        if bmp_cli_compression:
            for compression, count in sorted(
                bmp_cli_compression.items()
            ):
                typer.echo(
                    f"    {compression}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  Dimensions:"
        )

        if bmp_cli_dimensions:
            for (
                width,
                height,
            ), count in sorted(
                bmp_cli_dimensions.items()
            ):
                typer.echo(
                    f"    {width}x{height}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        sflb_cli_requirements = (
            universe_result.sflb_requirements
        )

        sflb_cli_versions = Counter(
            requirement.version
            for requirement
            in sflb_cli_requirements
        )

        sflb_cli_flags = Counter(
            requirement.flags
            for requirement
            in sflb_cli_requirements
        )

        sflb_cli_total_payload_bytes = sum(
            requirement.payload_size_bytes
            for requirement
            in sflb_cli_requirements
        )

        typer.echo()
        typer.echo(
            "SFLB Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed SFLB entries: "
                f"{len(parsing.sflb)}"
            )
        )
        typer.echo(
            (
                "  Universe SFLB requirements: "
                f"{len(sflb_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe SFLB identity match: "
                f"{all(
                    requirement.source is parsed
                    for requirement, parsed
                    in zip(
                        sflb_cli_requirements,
                        parsing.sflb,
                        strict=True,
                    )
                )}"
            )
        )
        typer.echo(
            (
                "  Extraction artifact identity match: "
                f"{all(
                    requirement.artifact is parsed.artifact
                    for requirement, parsed
                    in zip(
                        sflb_cli_requirements,
                        parsing.sflb,
                        strict=True,
                    )
                )}"
            )
        )
        typer.echo(
            (
                "  Total SFLB payload bytes: "
                f"{sflb_cli_total_payload_bytes}"
            )
        )
        typer.echo(
            "  SFLB versions:"
        )

        if sflb_cli_versions:
            for version, count in sorted(
                sflb_cli_versions.items()
            ):
                typer.echo(
                    f"    {version}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  SFLB flags:"
        )

        if sflb_cli_flags:
            for flags, count in sorted(
                sflb_cli_flags.items()
            ):
                typer.echo(
                    f"    0x{flags:x}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        bootloader_cli_requirements = (
            universe_result.bootloader_requirements
        )

        bootloader_cli_type_counts = Counter(
            requirement.parsed_type
            for requirement
            in bootloader_cli_requirements
        )

        typer.echo()
        typer.echo(
            "Bootloader Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed bootloader children: "
                f"{len(parsing.bootloader)}"
            )
        )
        typer.echo(
            (
                "  Universe bootloader requirements: "
                f"{len(bootloader_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe bootloader identity match: "
                f"{all(
                    requirement.source is parsed
                    for requirement, parsed
                    in zip(
                        bootloader_cli_requirements,
                        parsing.bootloader,
                        strict=True,
                    )
                )}"
            )
        )
        typer.echo(
            (
                "  Extraction artifact identity match: "
                f"{all(
                    requirement.artifact is parsed.artifact
                    for requirement, parsed
                    in zip(
                        bootloader_cli_requirements,
                        parsing.bootloader,
                        strict=True,
                    )
                )}"
            )
        )
        typer.echo(
            "  Parsed child families:"
        )

        if bootloader_cli_type_counts:
            for parsed_type, count in sorted(
                bootloader_cli_type_counts.items()
            ):
                typer.echo(
                    f"    {parsed_type}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        vbmeta_cli_requirements = (
            universe_result.vbmeta_requirements
        )

        avb_cli_regions = (
            universe_result.avb_regions
        )

        def vbmeta_cli_source_label(
            requirement,
        ) -> str:
            partition_name = (
                requirement.partition_name
            )

            if partition_name is not None:
                return (
                    "partition:"
                    f"{partition_name}"
                )

            artifact = (
                requirement.artifact
            )

            semantic_name = (
                artifact.semantic_name
            )

            if semantic_name:
                return (
                    "embedded:"
                    f"{semantic_name} "
                    f"[{artifact.path}]"
                )

            return (
                "embedded:"
                f"{artifact.path}"
            )

        vbmeta_cli_descriptor_count = sum(
            len(requirement.descriptors)
            for requirement
            in vbmeta_cli_requirements
        )

        vbmeta_cli_descriptor_types = Counter(
            type(descriptor).__name__
            for requirement
            in vbmeta_cli_requirements
            for descriptor
            in requirement.descriptors
        )

        vbmeta_cli_partition_backed_count = sum(
            requirement.is_partition_backed
            for requirement
            in vbmeta_cli_requirements
        )

        vbmeta_cli_embedded_count = (
            len(
                vbmeta_cli_requirements
            )
            - vbmeta_cli_partition_backed_count
        )

        avb_cli_region_dispositions = Counter(
            region.disposition
            for region
            in avb_cli_regions
        )

        vbmeta_cli_source_identity_match = (
            len(
                vbmeta_cli_requirements
            )
            == len(
                parsing.vbmeta
            )
            and all(
                requirement.source is parsed
                for requirement, parsed
                in zip(
                    vbmeta_cli_requirements,
                    parsing.vbmeta,
                    strict=True,
                )
            )
        )

        avb_cli_region_identity_match = (
            len(
                avb_cli_regions
            )
            == len(
                parsing.avb_regions
            )
            and all(
                universe_region.source
                is parsed_region
                for (
                    universe_region,
                    parsed_region,
                )
                in zip(
                    avb_cli_regions,
                    parsing.avb_regions,
                    strict=True,
                )
            )
        )

        avb_cli_region_link_identity_match = (
            len(
                avb_cli_regions
            )
            == len(
                parsing.avb_regions
            )
            and all(
                (
                    universe_region
                    .vbmeta_requirement
                    is not None
                    and parsed_region.vbmeta
                    is not None
                    and universe_region
                    .vbmeta_requirement
                    .source
                    is parsed_region.vbmeta
                )
                if (
                    parsed_region.disposition
                    == "parsed"
                )
                else (
                    universe_region
                    .vbmeta_requirement
                    is None
                )
                for (
                    universe_region,
                    parsed_region,
                )
                in zip(
                    avb_cli_regions,
                    parsing.avb_regions,
                    strict=True,
                )
            )
        )

        typer.echo()

        bootloader_family_counts = Counter(
            requirement.family.value
            for requirement
            in bootloader_cli_requirements
        )

        bootloader_interpreted_observations = sum(
            requirement.semantic_coverage.interpreted_observations
            for requirement
            in bootloader_cli_requirements
        )

        bootloader_preserved_opaque_observations = sum(
            requirement
            .semantic_coverage
            .preserved_opaque_observations
            for requirement
            in bootloader_cli_requirements
        )

        bootloader_unresolved_observations = sum(
            requirement.semantic_coverage.unresolved_observations
            for requirement
            in bootloader_cli_requirements
        )

        bootloader_structural_children = sum(
            requirement.structural_child_count
            for requirement
            in bootloader_cli_requirements
        )

        typer.echo(
            "  Bootloader semantic families:"
        )

        for family in (
            AndroidUniverseBootloaderRequirementFamily.FIRMWARE_PAYLOAD,
            AndroidUniverseBootloaderRequirementFamily.PARTITION_TABLE,
            AndroidUniverseBootloaderRequirementFamily.UFS_DESCRIPTOR,
            AndroidUniverseBootloaderRequirementFamily.FIRMWARE_PACKAGE,
            AndroidUniverseBootloaderRequirementFamily
            .FIRMWARE_PACKAGE_DESCRIPTOR,
        ):
            typer.echo(
                (
                    "    "
                    f"{family.value}: "
                    f"{bootloader_family_counts.get(family.value, 0)}"
                )
            )

        typer.echo(
            (
                "  Bootloader structural children: "
                f"{bootloader_structural_children}"
            )
        )


        bootloader_fbpt_trailing_text = Counter(
            value
            for requirement
            in bootloader_cli_requirements
            for value in (
                requirement
                .nonempty_fbpt_trailing_text_observations
            )
        )

        bootloader_validated_ufpk_descriptor_counts = tuple(
            requirement.validated_descriptor_count
            for requirement
            in bootloader_cli_requirements
            if requirement.ufpk_descriptor_count_is_validated
        )

        typer.echo(
            (
                "  FBPT non-empty trailing-text observations: "
                f"{sum(bootloader_fbpt_trailing_text.values())}"
            )
        )

        for value, count in sorted(
            bootloader_fbpt_trailing_text.items()
        ):
            typer.echo(
                f"    {value!r}: {count}"
            )

        typer.echo(
            (
                "  Validated UFPK descriptor-count observations: "
                f"{len(bootloader_validated_ufpk_descriptor_counts)}"
            )
        )

        for count in (
            bootloader_validated_ufpk_descriptor_counts
        ):
            typer.echo(
                f"    descriptor count: {count}"
            )

        typer.echo(
            (
                "  Bootloader interpreted observations: "
                f"{bootloader_interpreted_observations}"
            )
        )

        typer.echo(
            (
                "  Bootloader preserved opaque observations: "
                f"{bootloader_preserved_opaque_observations}"
            )
        )

        typer.echo(
            (
                "  Bootloader unresolved observations: "
                f"{bootloader_unresolved_observations}"
            )
        )

        if bootloader_unresolved_observations:
            typer.echo(
                "  Bootloader semantic completeness: PARTIAL"
            )
        else:
            typer.echo(
                "  Bootloader semantic completeness: COMPLETE"
            )

        typer.echo(
            "VBMeta / AVB Universe coverage:"
        )
        typer.echo(
            (
                "  Parsing VBMeta sources: "
                f"{len(parsing.vbmeta)}"
            )
        )
        typer.echo(
            (
                "    Partition-backed: "
                f"{vbmeta_cli_partition_backed_count}"
            )
        )
        typer.echo(
            (
                "    Embedded: "
                f"{vbmeta_cli_embedded_count}"
            )
        )
        typer.echo(
            (
                "  Universe VBMeta requirements: "
                f"{len(vbmeta_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe VBMeta source identity: "
                + (
                    "PASS"
                    if vbmeta_cli_source_identity_match
                    else "FAIL"
                )
            )
        )
        typer.echo(
            (
                "  Parsing AVB regions: "
                f"{len(parsing.avb_regions)}"
            )
        )
        typer.echo(
            (
                "    Parsed: "
                f"{avb_cli_region_dispositions.get('parsed', 0)}"
            )
        )
        typer.echo(
            (
                "    Fact-derived: "
                f"{avb_cli_region_dispositions.get('fact_derived', 0)}"
            )
        )
        typer.echo(
            (
                "    Preserved: "
                f"{avb_cli_region_dispositions.get('preserved', 0)}"
            )
        )
        typer.echo(
            (
                "  Universe conserved AVB regions: "
                f"{len(avb_cli_regions)}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe AVB-region identity: "
                + (
                    "PASS"
                    if avb_cli_region_identity_match
                    else "FAIL"
                )
            )
        )
        typer.echo(
            (
                "  Parsed-region/VBMeta requirement linkage: "
                + (
                    "PASS"
                    if avb_cli_region_link_identity_match
                    else "FAIL"
                )
            )
        )
        typer.echo(
            (
                "  AVB descriptors: "
                f"{vbmeta_cli_descriptor_count}"
            )
        )

        typer.echo(
            "  Descriptor families:"
        )

        if vbmeta_cli_descriptor_types:
            for (
                descriptor_type,
                count,
            ) in sorted(
                vbmeta_cli_descriptor_types.items()
            ):
                typer.echo(
                    f"    {descriptor_type}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        for requirement in vbmeta_cli_requirements:
            parsed = requirement.source
            metadata = requirement.metadata

            typer.echo(
                "  "
                + vbmeta_cli_source_label(
                    requirement
                )
                + ":"
            )
            typer.echo(
                (
                    "    required libavb: "
                    f"{metadata.required_libavb_version_major}."
                    f"{metadata.required_libavb_version_minor}"
                )
            )
            typer.echo(
                (
                    "    algorithm type: "
                    f"{metadata.algorithm_type}"
                )
            )
            typer.echo(
                (
                    "    rollback index: "
                    f"{metadata.rollback_index}"
                )
            )
            typer.echo(
                (
                    "    rollback index location: "
                    f"{metadata.rollback_index_location}"
                )
            )
            typer.echo(
                (
                    "    flags: "
                    f"{metadata.flags}"
                )
            )
            typer.echo(
                (
                    "    release string: "
                    f"{metadata.release_string!r}"
                )
            )
            typer.echo(
                (
                    "    descriptors: "
                    f"{len(metadata.descriptors)}"
                )
            )

        dtbo_cli_requirements = (
            universe_result.dtbo_requirements
        )

        dtbo_cli_population = (
            universe_result.dtbo_population
        )

        dtbo_cli_node_count = sum(
            requirement.node_count
            for requirement
            in dtbo_cli_requirements
        )

        dtbo_cli_property_count = sum(
            requirement.property_count
            for requirement
            in dtbo_cli_requirements
        )

        dtbo_cli_reservation_count = sum(
            requirement.reservation_count
            for requirement
            in dtbo_cli_requirements
        )

        dtbo_cli_top_level_children = sum(
            requirement.top_level_child_count
            for requirement
            in dtbo_cli_requirements
        )


        dtbo_cli_reference_status = Counter(
            reference.status.name
            for requirement
            in dtbo_cli_requirements
            for reference
            in requirement.semantics.references
        )

        dtbo_cli_reference_count = sum(
            len(requirement.semantics.references)
            for requirement
            in dtbo_cli_requirements
        )

        dtbo_cli_duplicate_phandles = sum(
            len(
                requirement.semantics.duplicate_phandles
            )
            for requirement
            in dtbo_cli_requirements
        )

        dtbo_cli_models = tuple(
            model
            for requirement
            in dtbo_cli_requirements
            for model
            in requirement.semantics.models
        )

        dtbo_cli_compatibles = tuple(
            compatible
            for requirement
            in dtbo_cli_requirements
            for compatible
            in requirement.semantics.compatibles
        )

        dtbo_cli_statuses = Counter(
            status
            for requirement
            in dtbo_cli_requirements
            for status
            in requirement.semantics.statuses
        )

        dtbo_cli_property_value_kinds = Counter(
            observation.value_kind.name
            for requirement
            in dtbo_cli_requirements
            for observation
            in requirement.property_observations
        )

        dtbo_cli_property_semantics = Counter(
            observation.semantic_kind.name
            for requirement
            in dtbo_cli_requirements
            for observation
            in requirement.property_observations
        )

        typer.echo()
        avb_cli_topology = (
            universe_result.avb_topology
        )

        typer.echo()
        typer.echo(
            "AVB topology reconciliation:"
        )
        typer.echo(
            (
                "  VBMeta source nodes: "
                f"{len(avb_cli_topology.requirements)}"
            )
        )
        typer.echo(
            (
                "  Partition authentication relationships: "
                f"{len(avb_cli_topology.authentications)}"
            )
        )
        typer.echo(
            (
                "  Chain-partition relationships: "
                f"{len(avb_cli_topology.chains)}"
            )
        )
        typer.echo(
            (
                "  Resolved chain relationships: "
                f"{avb_cli_topology.resolved_chain_count}"
            )
        )
        typer.echo(
            (
                "  Unresolved chain relationships: "
                f"{avb_cli_topology.unresolved_chain_count}"
            )
        )
        typer.echo(
            (
                "  Root VBMeta requirements: "
                f"{len(avb_cli_topology.root_requirements)}"
            )
        )

        for requirement in (
            avb_cli_topology.root_requirements
        ):
            typer.echo(
                "    "
                + vbmeta_cli_source_label(
                    requirement
                )
            )

        typer.echo(
            (
                "  Orphan VBMeta requirements: "
                f"{len(avb_cli_topology.orphan_requirements)}"
            )
        )

        for requirement in (
            avb_cli_topology.orphan_requirements
        ):
            typer.echo(
                "    "
                + vbmeta_cli_source_label(
                    requirement
                )
            )

        typer.echo(
            (
                "  Cycle requirements: "
                f"{len(avb_cli_topology.cycle_requirements)}"
            )
        )

        for requirement in (
            avb_cli_topology.cycle_requirements
        ):
            typer.echo(
                "    "
                + vbmeta_cli_source_label(
                    requirement
                )
            )

        typer.echo(
            "  Chain topology:"
        )

        if avb_cli_topology.chains:
            for chain in avb_cli_topology.chains:
                owner_name = (
                    vbmeta_cli_source_label(
                        chain.owner
                    )
                )

                target_name = (
                    vbmeta_cli_source_label(
                        chain.target
                    )
                    if chain.target is not None
                    else (
                        "unresolved-partition:"
                        f"{chain.target_partition_name}"
                    )
                )

                typer.echo(
                    (
                        "    "
                        f"{owner_name} -> {target_name} "
                        f"[{chain.status.name}] "
                        "rollback_index_location="
                        f"{chain.descriptor.rollback_index_location}"
                    )
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  Authentication targets:"
        )

        if avb_cli_topology.authentications:
            for authentication in (
                avb_cli_topology.authentications
            ):
                typer.echo(
                    (
                        "    "
                        + vbmeta_cli_source_label(
                            authentication.owner
                        )
                        + " -> partition:"
                        f"{authentication.partition_name} "
                        "["
                        f"{type(authentication.descriptor).__name__}"
                        "]"
                    )
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo()

        typer.echo(
            "DTBO Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed DTBO entries: "
                f"{len(parsing.dtbo)}"
            )
        )
        typer.echo(
            (
                "  Universe DTBO requirements: "
                f"{len(dtbo_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Total FDT nodes: "
                f"{dtbo_cli_node_count}"
            )
        )
        typer.echo(
            (
                "  Total FDT properties: "
                f"{dtbo_cli_property_count}"
            )
        )
        typer.echo(
            (
                "  Total memory reservations: "
                f"{dtbo_cli_reservation_count}"
            )
        )
        typer.echo(
            (
                "  Total top-level children: "
                f"{dtbo_cli_top_level_children}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe DTBO identity match: "
                f"{all(
                    requirement.source is parsed
                    for requirement, parsed
                    in zip(
                        dtbo_cli_requirements,
                        parsing.dtbo,
                        strict=True,
                    )
                )}"
            )
        )


        typer.echo()
        typer.echo(
            "DTBO population reconciliation:"
        )

        typer.echo(
            (
                "  Population entries: "
                f"{len(dtbo_cli_population.entries)}"
            )
        )

        typer.echo(
            (
                "  Requirement identity match: "
                f"{all(
                    entry.requirement is requirement
                    for entry, requirement
                    in zip(
                        dtbo_cli_population.entries,
                        dtbo_cli_requirements,
                        strict=True,
                    )
                )}"
            )
        )

        typer.echo(
            (
                "  Semantic signature groups: "
                f"{len(dtbo_cli_population.signature_groups)}"
            )
        )

        for (
            signature_id,
            entry_indices,
        ) in dtbo_cli_population.signature_groups:
            typer.echo(
                (
                    f"    {signature_id}: "
                    f"{', '.join(
                        str(index)
                        for index in entry_indices
                    )}"
                )
            )

        typer.echo(
            (
                "  Shared compatible values: "
                f"{len(
                    dtbo_cli_population.shared_compatibles
                )}"
            )
        )

        typer.echo(
            (
                "  Varying compatible values: "
                f"{len(
                    dtbo_cli_population.varying_compatibles
                )}"
            )
        )

        typer.echo(
            (
                "  Shared external symbols: "
                f"{len(
                    dtbo_cli_population.shared_external_symbols
                )}"
            )
        )

        typer.echo(
            (
                "  Varying external symbols: "
                f"{len(
                    dtbo_cli_population.varying_external_symbols
                )}"
            )
        )

        typer.echo(
            (
                "  Shared fragment target paths: "
                f"{len(
                    dtbo_cli_population.shared_fragment_target_paths
                )}"
            )
        )

        typer.echo(
            (
                "  Varying fragment target paths: "
                f"{len(
                    dtbo_cli_population.varying_fragment_target_paths
                )}"
            )
        )

        typer.echo(
            (
                "  Shared status values: "
                f"{len(
                    dtbo_cli_population.shared_status_values
                )}"
            )
        )

        typer.echo(
            (
                "  Varying status values: "
                f"{len(
                    dtbo_cli_population.varying_status_values
                )}"
            )
        )

        typer.echo(
            "  Entry signatures:"
        )

        for index, entry in enumerate(
            dtbo_cli_population.entries
        ):
            typer.echo(
                (
                    f"    entry {index}: "
                    f"{entry.signature_id}"
                )
            )

            typer.echo(
                (
                    "      models: "
                    f"{len(entry.models)}"
                )
            )

            for model in entry.models:
                typer.echo(
                    f"        {model!r}"
                )

            typer.echo(
                (
                    "      compatibles: "
                    f"{len(entry.compatibles)}"
                )
            )

            typer.echo(
                (
                    "      external symbols: "
                    f"{len(entry.external_symbols)}"
                )
            )

            typer.echo(
                (
                    "      fragment target paths: "
                    f"{len(entry.fragment_target_paths)}"
                )
            )

            typer.echo(
                (
                    "      status values: "
                    f"{len(entry.status_values)}"
                )
            )

            typer.echo(
                (
                    "      external references: "
                    f"{entry.external_reference_count}"
                )
            )

            typer.echo(
                (
                    "      local references: "
                    f"{entry.local_reference_count}"
                )
            )

            typer.echo(
                (
                    "      external fragment targets: "
                    f"{entry.fragment_external_count}"
                )
            )

            typer.echo(
                (
                    "      path fragment targets: "
                    f"{entry.fragment_path_count}"
                )
            )


        dtbo_cli_deltas = (
            dtbo_cli_population.entry_deltas
        )

        dtbo_cli_cross_signature_deltas = tuple(
            delta
            for delta in dtbo_cli_deltas
            if not delta.same_signature
        )

        dtbo_cli_same_signature_deltas = tuple(
            delta
            for delta in dtbo_cli_deltas
            if delta.same_signature
        )

        dtbo_cli_model_only_deltas = tuple(
            delta
            for delta in dtbo_cli_deltas
            if delta.model_only_difference
        )

        typer.echo()
        typer.echo(
            "DTBO population semantic deltas:"
        )
        typer.echo(
            (
                "  Pairwise comparisons: "
                f"{len(dtbo_cli_deltas)}"
            )
        )
        typer.echo(
            (
                "  Cross-signature comparisons: "
                f"{len(dtbo_cli_cross_signature_deltas)}"
            )
        )
        typer.echo(
            (
                "  Same-signature comparisons: "
                f"{len(dtbo_cli_same_signature_deltas)}"
            )
        )
        typer.echo(
            (
                "  Model-only differences: "
                f"{len(dtbo_cli_model_only_deltas)}"
            )
        )

        typer.echo()
        typer.echo(
            "DTBO canonical variant profiles:"
        )

        dtbo_cli_variants = (
            dtbo_cli_population.variants
        )

        dtbo_cli_variant_profile_counts = Counter(
            variant.variant_profile_id
            for variant
            in dtbo_cli_variants
        )

        typer.echo(
            (
                "  Variant profiles: "
                f"{len(dtbo_cli_variants)}"
            )
        )

        typer.echo(
            (
                "  Unique variant profile IDs: "
                f"{len(dtbo_cli_variant_profile_counts)}"
            )
        )

        typer.echo(
            (
                "  Varying property locations: "
                f"{len(
                    dtbo_cli_population
                    .varying_property_locations
                )}"
            )
        )

        typer.echo(
            (
                "  Varying reference relationships: "
                f"{len(
                    dtbo_cli_population
                    .varying_reference_keys
                )}"
            )
        )

        typer.echo(
            "  Variant family groups:"
        )

        typer.echo(
            (
                "    Family count: "
                f"{len(
                    dtbo_cli_population
                    .variant_family_groups
                )}"
            )
        )

        for (
            family_id,
            entry_indices,
        ) in (
            dtbo_cli_population
            .variant_family_groups
        ):
            typer.echo(
                (
                    f"    {family_id}: "
                    f"entries "
                    f"{', '.join(
                        str(index)
                        for index
                        in entry_indices
                    )}"
                )
            )

        typer.echo(
            "  Variant profile groups:"
        )

        for (
            profile_id,
            count,
        ) in sorted(
            dtbo_cli_variant_profile_counts.items()
        ):
            indices = tuple(
                variant.entry_index
                for variant
                in dtbo_cli_variants
                if (
                    variant.variant_profile_id
                    == profile_id
                )
            )

            typer.echo(
                (
                    f"    {profile_id}: "
                    f"entries "
                    f"{', '.join(
                        str(index)
                        for index
                        in indices
                    )} "
                    f"(count={count})"
                )
            )

        typer.echo(
            "  Varying property locations:"
        )

        for (
            node_path,
            property_name,
        ) in (
            dtbo_cli_population
            .varying_property_locations
        ):
            typer.echo(
                (
                    f"    {node_path}:"
                    f"{property_name}"
                )
            )

        typer.echo(
            "  Variant entries:"
        )

        for variant in dtbo_cli_variants:
            typer.echo(
                (
                    f"    entry "
                    f"{variant.entry_index}: "
                    f"profile="
                    f"{variant.variant_profile_id} "
                    f"family="
                    f"{variant.variant_family_id} "
                    f"signature="
                    f"{variant.signature_id}"
                )
            )

            if variant.models:
                typer.echo(
                    "      models:"
                )

                for model in variant.models:
                    typer.echo(
                        f"        {model!r}"
                    )

            typer.echo(
                (
                    "      variant properties: "
                    f"{len(
                        variant.properties
                    )}"
                )
            )

            for item in (
                variant.properties
            ):
                state = (
                    "absent"
                    if item.value is None
                    else (
                        "empty"
                        if item.value == b""
                        else (
                            f"{len(item.value)} bytes"
                        )
                    )
                )

                typer.echo(
                    (
                        f"        "
                        f"{item.node_path}:"
                        f"{item.property_name} "
                        f"[{state}]"
                    )
                )

            typer.echo(
                (
                    "      variant references: "
                    f"{len(
                        variant.references
                    )}"
                )
            )

            for item in (
                variant.references
            ):
                location = (
                    f"{item.node_path}:"
                    f"{item.property_name}"
                )

                if (
                    item.byte_offset
                    is not None
                ):
                    location += (
                        f"+{item.byte_offset}"
                    )

                target = (
                    item.symbol
                    if item.symbol is not None
                    else (
                        item.target_path
                        if item.target_path is not None
                        else (
                            f"phandle="
                            f"{item.phandle}"
                            if item.phandle
                            is not None
                            else "no-target"
                        )
                    )
                )

                typer.echo(
                    (
                        f"        "
                        f"{item.status} "
                        f"{location} -> "
                        f"{target}"
                    )
                )

        for delta in dtbo_cli_deltas:
            typer.echo(
                (
                    f"  Entries "
                    f"{delta.left_index} -> "
                    f"{delta.right_index}:"
                )
            )
            typer.echo(
                (
                    "    Signature relationship: "
                    f"{'same' if delta.same_signature else 'different'}"
                )
            )
            typer.echo(
                (
                    "    Model-only difference: "
                    f"{delta.model_only_difference}"
                )
            )
            typer.echo(
                (
                    "    Models: "
                    f"{delta.left_models!r} -> "
                    f"{delta.right_models!r}"
                )
            )
            typer.echo(
                (
                    "    Added nodes: "
                    f"{len(delta.added_nodes)}"
                )
            )
            typer.echo(
                (
                    "    Removed nodes: "
                    f"{len(delta.removed_nodes)}"
                )
            )

            added_properties = tuple(
                item
                for item in delta.property_deltas
                if item.kind == "added"
            )
            removed_properties = tuple(
                item
                for item in delta.property_deltas
                if item.kind == "removed"
            )
            changed_properties = tuple(
                item
                for item in delta.property_deltas
                if item.kind == "changed"
            )

            typer.echo(
                (
                    "    Added properties: "
                    f"{len(added_properties)}"
                )
            )
            typer.echo(
                (
                    "    Removed properties: "
                    f"{len(removed_properties)}"
                )
            )
            typer.echo(
                (
                    "    Changed properties: "
                    f"{len(changed_properties)}"
                )
            )
            typer.echo(
                (
                    "    Reference deltas: "
                    f"{len(delta.reference_deltas)}"
                )
            )

            if delta.added_nodes:
                typer.echo(
                    "    Added node paths:"
                )
                for node_path in delta.added_nodes:
                    typer.echo(
                        f"      {node_path}"
                    )

            if delta.removed_nodes:
                typer.echo(
                    "    Removed node paths:"
                )
                for node_path in delta.removed_nodes:
                    typer.echo(
                        f"      {node_path}"
                    )

            if delta.property_deltas:
                typer.echo(
                    "    Property differences:"
                )

                for item in delta.property_deltas:
                    typer.echo(
                        (
                            f"      {item.kind}: "
                            f"{item.node_path}:"
                            f"{item.property_name}"
                        )
                    )

            if delta.reference_deltas:
                typer.echo(
                    "    Reference differences:"
                )

                for item in delta.reference_deltas:
                    location = (
                        f"{item.node_path}:"
                        f"{item.property_name}"
                    )

                    if item.byte_offset is not None:
                        location += (
                            f"+{item.byte_offset}"
                        )

                    detail = (
                        item.symbol
                        if item.symbol is not None
                        else (
                            item.target_path
                            if item.target_path is not None
                            else (
                                f"phandle={item.phandle}"
                                if item.phandle is not None
                                else "no-target"
                            )
                        )
                    )

                    typer.echo(
                        (
                            f"      {item.side}: "
                            f"{item.status} "
                            f"{location} -> "
                            f"{detail}"
                        )
                    )


        typer.echo(
            (
                "  Semantic property observations: "
                f"{sum(
                    len(requirement.property_observations)
                    for requirement
                    in dtbo_cli_requirements
                )}"
            )
        )

        typer.echo(
            (
                "  Reference observations: "
                f"{dtbo_cli_reference_count}"
            )
        )

        typer.echo(
            (
                "  External-symbol references: "
                f"{dtbo_cli_reference_status.get(
                    'EXTERNAL_SYMBOL',
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Resolved local references: "
                f"{dtbo_cli_reference_status.get(
                    'RESOLVED_LOCAL',
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Unresolved local references: "
                f"{dtbo_cli_reference_status.get(
                    'UNRESOLVED_LOCAL',
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  External fragment targets: "
                f"{dtbo_cli_reference_status.get(
                    'FRAGMENT_TARGET_EXTERNAL',
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Path fragment targets: "
                f"{dtbo_cli_reference_status.get(
                    'FRAGMENT_TARGET_PATH',
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "  Duplicate phandles: "
                f"{dtbo_cli_duplicate_phandles}"
            )
        )


        typer.echo(
            (
                "  External fixup locations: "
                f"{sum(
                    requirement.semantics.external_fixup_count
                    for requirement
                    in dtbo_cli_requirements
                )}"
            )
        )

        typer.echo(
            (
                "  Local fixup offsets: "
                f"{sum(
                    requirement.semantics.local_fixup_count
                    for requirement
                    in dtbo_cli_requirements
                )}"
            )
        )

        typer.echo(
            (
                "  Fragment targets: "
                f"{sum(
                    requirement.semantics.fragment_target_count
                    for requirement
                    in dtbo_cli_requirements
                )}"
            )
        )

        typer.echo(
            (
                "  Model observations: "
                f"{len(dtbo_cli_models)}"
            )
        )

        for model in dtbo_cli_models:
            typer.echo(
                f"    {model!r}"
            )

        typer.echo(
            (
                "  Compatible observations: "
                f"{len(dtbo_cli_compatibles)}"
            )
        )

        typer.echo(
            (
                "  Distinct compatible values: "
                f"{len(set(dtbo_cli_compatibles))}"
            )
        )

        typer.echo(
            "  Status values:"
        )

        if dtbo_cli_statuses:
            for status, count in sorted(
                dtbo_cli_statuses.items()
            ):
                typer.echo(
                    f"    {status!r}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  Property value kinds:"
        )

        for kind, count in sorted(
            dtbo_cli_property_value_kinds.items()
        ):
            typer.echo(
                f"    {kind}: {count}"
            )

        typer.echo(
            "  Standard semantic kinds:"
        )

        for kind, count in sorted(
            dtbo_cli_property_semantics.items()
        ):
            typer.echo(
                f"    {kind}: {count}"
            )

        # --------------------------------------------------------------
        # Fresh Parsing-boundary Universe intake coverage
        # --------------------------------------------------------------

        aconfig_cli_requirement = (
            universe_result.aconfig_requirement
        )

        aconfig_cli_configurations = (
            parsing.aconfig.configurations
        )

        aconfig_cli_flags = tuple(
            flag
            for configuration in aconfig_cli_configurations
            for flag in configuration.flags
        )

        aconfig_cli_tracepoints = tuple(
            tracepoint
            for flag in aconfig_cli_flags
            for tracepoint in flag.tracepoints
        )

        aconfig_cli_semantic_configurations = (
            aconfig_cli_requirement.configurations
            if aconfig_cli_requirement is not None
            else ()
        )

        aconfig_cli_semantic_flags = (
            aconfig_cli_requirement.flags
            if aconfig_cli_requirement is not None
            else ()
        )

        aconfig_cli_semantic_tracepoints = tuple(
            tracepoint
            for flag_requirement in aconfig_cli_semantic_flags
            for tracepoint in flag_requirement.semantics.tracepoints
        )

        aconfig_cli_flag_identity_resolved = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if requirement.canonical_identity is not None
        )

        aconfig_cli_flag_identity_unresolved = (
            len(aconfig_cli_semantic_flags)
            - aconfig_cli_flag_identity_resolved
        )

        aconfig_cli_flag_state_known = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                requirement.source.state_present
                and requirement.semantics.state is not None
            )
        )

        aconfig_cli_flag_state_unknown = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                requirement.source.state_present
                and requirement.semantics.state is None
            )
        )

        aconfig_cli_flag_state_absent = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if not requirement.source.state_present
        )

        aconfig_cli_flag_permission_known = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                requirement.source.permission_present
                and requirement.semantics.permission is not None
            )
        )

        aconfig_cli_flag_permission_unknown = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                requirement.source.permission_present
                and requirement.semantics.permission is None
            )
        )

        aconfig_cli_flag_permission_absent = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if not requirement.source.permission_present
        )

        aconfig_cli_flag_purpose_known = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                requirement.source.metadata_present
                and requirement.source.metadata is not None
                and requirement.source.metadata.purpose_present
                and requirement.semantics.purpose is not None
            )
        )

        aconfig_cli_flag_purpose_unknown = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                requirement.source.metadata_present
                and requirement.source.metadata is not None
                and requirement.source.metadata.purpose_present
                and requirement.semantics.purpose is None
            )
        )

        aconfig_cli_flag_purpose_absent = sum(
            1
            for requirement in aconfig_cli_semantic_flags
            if (
                not requirement.source.metadata_present
                or requirement.source.metadata is None
                or not requirement.source.metadata.purpose_present
            )
        )

        aconfig_cli_tracepoint_state_known = sum(
            1
            for semantic in aconfig_cli_semantic_tracepoints
            if (
                semantic.source.state_present
                and semantic.state is not None
            )
        )

        aconfig_cli_tracepoint_state_unknown = sum(
            1
            for semantic in aconfig_cli_semantic_tracepoints
            if (
                semantic.source.state_present
                and semantic.state is None
            )
        )

        aconfig_cli_tracepoint_state_absent = sum(
            1
            for semantic in aconfig_cli_semantic_tracepoints
            if not semantic.source.state_present
        )

        aconfig_cli_tracepoint_permission_known = sum(
            1
            for semantic in aconfig_cli_semantic_tracepoints
            if (
                semantic.source.permission_present
                and semantic.permission is not None
            )
        )

        aconfig_cli_tracepoint_permission_unknown = sum(
            1
            for semantic in aconfig_cli_semantic_tracepoints
            if (
                semantic.source.permission_present
                and semantic.permission is None
            )
        )

        aconfig_cli_tracepoint_permission_absent = sum(
            1
            for semantic in aconfig_cli_semantic_tracepoints
            if not semantic.source.permission_present
        )

        aconfig_cli_fixed_present = sum(
            1
            for flag in aconfig_cli_flags
            if flag.is_fixed_read_only_present
        )

        aconfig_cli_fixed_true = sum(
            1
            for flag in aconfig_cli_flags
            if (
                flag.is_fixed_read_only_present
                and flag.is_fixed_read_only
            )
        )

        aconfig_cli_exported_present = sum(
            1
            for flag in aconfig_cli_flags
            if flag.is_exported_present
        )

        aconfig_cli_exported_true = sum(
            1
            for flag in aconfig_cli_flags
            if (
                flag.is_exported_present
                and flag.is_exported
            )
        )

        aconfig_cli_container_present = sum(
            1
            for flag in aconfig_cli_flags
            if flag.container_present
        )

        aconfig_cli_metadata_present = sum(
            1
            for flag in aconfig_cli_flags
            if flag.metadata_present
        )

        typer.echo()
        typer.echo(
            "Aconfig Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed Aconfig sources: "
                f"{len(aconfig_cli_configurations)}"
            )
        )
        typer.echo(
            (
                "  Parsed Aconfig flags: "
                f"{len(aconfig_cli_flags)}"
            )
        )
        typer.echo(
            (
                "  Parsed Aconfig tracepoints: "
                f"{len(aconfig_cli_tracepoints)}"
            )
        )
        typer.echo(
            (
                "  Universe Aconfig intake present: "
                f"{aconfig_cli_requirement is not None}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe Aconfig identity match: "
                f"{(
                    aconfig_cli_requirement is not None
                    and aconfig_cli_requirement.source
                    is parsing.aconfig
                )}"
            )
        )

        typer.echo(
            "  Semantic coverage:"
        )
        typer.echo(
            (
                "    configurations: "
                f"{len(aconfig_cli_semantic_configurations)}"
            )
        )
        typer.echo(
            (
                "    flags: "
                f"{len(aconfig_cli_semantic_flags)}"
            )
        )
        typer.echo(
            (
                "    tracepoints: "
                f"{len(aconfig_cli_semantic_tracepoints)}"
            )
        )

        typer.echo(
            "  Canonical flag identity:"
        )
        typer.echo(
            (
                "    resolved package/name: "
                f"{aconfig_cli_flag_identity_resolved}"
            )
        )
        typer.echo(
            (
                "    unresolved package/name: "
                f"{aconfig_cli_flag_identity_unresolved}"
            )
        )

        typer.echo(
            "  Flag state semantics:"
        )
        typer.echo(
            f"    known: {aconfig_cli_flag_state_known}"
        )
        typer.echo(
            f"    unknown: {aconfig_cli_flag_state_unknown}"
        )
        typer.echo(
            f"    absent: {aconfig_cli_flag_state_absent}"
        )

        typer.echo(
            "  Flag permission semantics:"
        )
        typer.echo(
            f"    known: {aconfig_cli_flag_permission_known}"
        )
        typer.echo(
            f"    unknown: {aconfig_cli_flag_permission_unknown}"
        )
        typer.echo(
            f"    absent: {aconfig_cli_flag_permission_absent}"
        )

        typer.echo(
            "  Flag purpose semantics:"
        )
        typer.echo(
            f"    known: {aconfig_cli_flag_purpose_known}"
        )
        typer.echo(
            f"    unknown: {aconfig_cli_flag_purpose_unknown}"
        )
        typer.echo(
            f"    absent: {aconfig_cli_flag_purpose_absent}"
        )

        typer.echo(
            "  Tracepoint state semantics:"
        )
        typer.echo(
            f"    known: {aconfig_cli_tracepoint_state_known}"
        )
        typer.echo(
            f"    unknown: {aconfig_cli_tracepoint_state_unknown}"
        )
        typer.echo(
            f"    absent: {aconfig_cli_tracepoint_state_absent}"
        )

        typer.echo(
            "  Tracepoint permission semantics:"
        )
        typer.echo(
            f"    known: {aconfig_cli_tracepoint_permission_known}"
        )
        typer.echo(
            f"    unknown: {aconfig_cli_tracepoint_permission_unknown}"
        )
        typer.echo(
            f"    absent: {aconfig_cli_tracepoint_permission_absent}"
        )

        typer.echo(
            "  Explicit flag metadata:"
        )
        typer.echo(
            (
                "    fixed/read-only field present: "
                f"{aconfig_cli_fixed_present}"
            )
        )
        typer.echo(
            (
                "    fixed/read-only true: "
                f"{aconfig_cli_fixed_true}"
            )
        )
        typer.echo(
            (
                "    exported field present: "
                f"{aconfig_cli_exported_present}"
            )
        )
        typer.echo(
            (
                "    exported true: "
                f"{aconfig_cli_exported_true}"
            )
        )
        typer.echo(
            (
                "    container field present: "
                f"{aconfig_cli_container_present}"
            )
        )
        typer.echo(
            (
                "    metadata message present: "
                f"{aconfig_cli_metadata_present}"
            )
        )
        typer.echo(
            (
                "  Preserved unknown protobuf fields: "
                f"{parsing.aconfig.unknown_field_count}"
            )
        )
        typer.echo(
            "  Cross-family reconciliation: pending"
        )

        apk_cli_requirement = (
            universe_result.apk_requirement
        )

        apk_cli_parsed_packages = (
            parsing.apk.packages
        )

        apk_cli_packages = (
            apk_cli_requirement.packages
            if apk_cli_requirement is not None
            else ()
        )

        apk_cli_overlay_resolutions = (
            apk_cli_requirement.overlay_resolutions
            if apk_cli_requirement is not None
            else ()
        )

        apk_cli_distinct_package_names = {
            package.package_name
            for package
            in apk_cli_packages
        }

        apk_cli_version_code_present = sum(
            1
            for package
            in apk_cli_packages
            if package.source.version_code is not None
        )

        apk_cli_version_name_present = sum(
            1
            for package
            in apk_cli_packages
            if package.source.version_name is not None
        )

        apk_cli_exact_artifact_identity = sum(
            1
            for package
            in apk_cli_packages
            if (
                package.artifact.inventory_entry.artifact
                is package.source.source.filesystem_source.artifact
            )
        )

        apk_cli_overlay_status_counts = Counter(
            resolution.status.value
            for resolution
            in apk_cli_overlay_resolutions
        )

        apk_cli_apex_contained = sum(
            1
            for package
            in apk_cli_packages
            if (
                package.source.source.source_name.startswith(
                    "apex:"
                )
            )
        )

        apk_cli_partition_filesystem = (
            len(apk_cli_packages)
            - apk_cli_apex_contained
        )

        typer.echo()
        typer.echo(
            "APK Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed APK packages: "
                f"{len(apk_cli_parsed_packages)}"
            )
        )
        typer.echo(
            (
                "  Universe APK packages: "
                f"{len(apk_cli_packages)}"
            )
        )
        typer.echo(
            (
                "  Universe APK intake present: "
                f"{apk_cli_requirement is not None}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe APK identity match: "
                f"{(
                    apk_cli_requirement is not None
                    and apk_cli_requirement.source
                    is parsing.apk
                )}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe APK package identity match: "
                f"{(
                    apk_cli_requirement is not None
                    and len(apk_cli_packages)
                    == len(apk_cli_parsed_packages)
                    and all(
                        requirement.source is parsed
                        for parsed, requirement
                        in zip(
                            apk_cli_parsed_packages,
                            apk_cli_packages,
                            strict=True,
                        )
                    )
                )}"
            )
        )

        typer.echo(
            "  Canonical package semantics:"
        )
        typer.echo(
            (
                "    distinct package names: "
                f"{len(apk_cli_distinct_package_names)}"
            )
        )
        typer.echo(
            (
                "    versionCode present: "
                f"{apk_cli_version_code_present}"
            )
        )
        typer.echo(
            (
                "    versionName present: "
                f"{apk_cli_version_name_present}"
            )
        )

        typer.echo(
            "  Exact artifact reconciliation:"
        )
        typer.echo(
            (
                "    packages: "
                f"{len(apk_cli_packages)}"
            )
        )
        typer.echo(
            (
                "    exact filesystem artifact identity: "
                f"{apk_cli_exact_artifact_identity}"
            )
        )
        typer.echo(
            (
                "    failures: "
                f"{(
                    len(apk_cli_packages)
                    - apk_cli_exact_artifact_identity
                )}"
            )
        )

        typer.echo(
            "  APK deployment-source population:"
        )
        typer.echo(
            (
                "    partition filesystem: "
                f"{apk_cli_partition_filesystem}"
            )
        )
        typer.echo(
            (
                "    APEX-contained filesystem: "
                f"{apk_cli_apex_contained}"
            )
        )

        typer.echo(
            "  Runtime resource overlays:"
        )
        typer.echo(
            (
                "    overlays: "
                f"{len(apk_cli_overlay_resolutions)}"
            )
        )
        typer.echo(
            (
                "    resolved: "
                f"{apk_cli_overlay_status_counts.get('resolved', 0)}"
            )
        )
        typer.echo(
            (
                "    absent: "
                f"{apk_cli_overlay_status_counts.get('absent', 0)}"
            )
        )
        typer.echo(
            (
                "    ambiguous: "
                f"{apk_cli_overlay_status_counts.get('ambiguous', 0)}"
            )
        )
        typer.echo(
            (
                "    unresolved: "
                f"{apk_cli_overlay_status_counts.get('unresolved', 0)}"
            )
        )

        if apk_cli_overlay_status_counts.get(
            "absent",
            0,
        ):
            typer.echo(
                "    absent target packages:"
            )

            for resolution in apk_cli_overlay_resolutions:
                if resolution.status.value != "absent":
                    continue

                typer.echo(
                    (
                        "      "
                        + resolution.overlay.package_name
                        + " -> "
                        + (
                            resolution.target_package_name
                            or "<unresolved>"
                        )
                    )
                )

        if apk_cli_overlay_status_counts.get(
            "ambiguous",
            0,
        ):
            typer.echo(
                "    ambiguous target packages:"
            )

            for resolution in apk_cli_overlay_resolutions:
                if resolution.status.value != "ambiguous":
                    continue

                typer.echo(
                    (
                        "      "
                        + resolution.overlay.package_name
                        + " -> "
                        + (
                            resolution.target_package_name
                            or "<unresolved>"
                        )
                        + " ("
                        + str(
                            len(
                                resolution.targets
                            )
                        )
                        + " candidates)"
                    )
                )

        if apk_cli_overlay_status_counts.get(
            "unresolved",
            0,
        ):
            typer.echo(
                "    unresolved target packages:"
            )

            for resolution in apk_cli_overlay_resolutions:
                if resolution.status.value != "unresolved":
                    continue

                typer.echo(
                    (
                        "      "
                        + resolution.overlay.package_name
                        + " -> "
                        + (
                            resolution.target_package_name
                            or "<unresolved>"
                        )
                    )
                )

        typer.echo(
            "  APK semantic reconciliation: complete"
        )

        classpath_cli_requirement = (
            universe_result.classpath_requirement
        )

        classpath_cli_configurations = (
            parsing.classpath.configurations
        )

        classpath_cli_jars = tuple(
            jar
            for configuration
            in classpath_cli_configurations
            for jar
            in configuration.jars
        )

        classpath_cli_applicability = (
            classpath_cli_requirement.jar_applicability
            if classpath_cli_requirement is not None
            else ()
        )

        classpath_cli_active = tuple(
            applicability
            for applicability
            in classpath_cli_applicability
            if (
                applicability.status
                is AndroidUniverseClasspathJarApplicabilityStatus.ACTIVE
            )
        )

        classpath_cli_inapplicable = tuple(
            applicability
            for applicability
            in classpath_cli_applicability
            if (
                applicability.status
                is AndroidUniverseClasspathJarApplicabilityStatus
                .INAPPLICABLE
            )
        )

        classpath_cli_unresolved = tuple(
            applicability
            for applicability
            in classpath_cli_applicability
            if (
                applicability.status
                is AndroidUniverseClasspathJarApplicabilityStatus
                .UNRESOLVED
            )
        )

        classpath_cli_unbounded = tuple(
            applicability
            for applicability
            in classpath_cli_applicability
            if (
                not applicability.requirement
                .min_sdk_version_present
                and not applicability.requirement
                .max_sdk_version_present
            )
        )

        classpath_cli_minimum_bounded = tuple(
            applicability
            for applicability
            in classpath_cli_applicability
            if (
                applicability.requirement
                .min_sdk_version_present
            )
        )

        classpath_cli_maximum_bounded = tuple(
            applicability
            for applicability
            in classpath_cli_applicability
            if (
                applicability.requirement
                .max_sdk_version_present
            )
        )

        classpath_cli_device_sdks = {
            applicability.device_sdk
            for applicability
            in classpath_cli_applicability
        }

        if len(
            classpath_cli_device_sdks
        ) > 1:
            raise ValueError(
                "Classpath applicability contains inconsistent "
                "canonical device SDK values"
            )

        classpath_cli_device_sdk = (
            next(
                iter(
                    classpath_cli_device_sdks
                )
            )
            if classpath_cli_device_sdks
            else None
        )

        classpath_cli_sdk_conclusions = {
            id(
                applicability.sdk_conclusion
            ): applicability.sdk_conclusion
            for applicability
            in classpath_cli_applicability
            if applicability.sdk_conclusion is not None
        }

        if len(
            classpath_cli_sdk_conclusions
        ) > 1:
            raise ValueError(
                "Classpath applicability contains inconsistent "
                "sdk_level conclusion identities"
            )

        classpath_cli_sdk_conclusion = (
            next(
                iter(
                    classpath_cli_sdk_conclusions.values()
                )
            )
            if classpath_cli_sdk_conclusions
            else None
        )

        classpath_cli_effective = (
            classpath_cli_requirement.effective_classpaths
            if classpath_cli_requirement is not None
            else ()
        )

        classpath_cli_effective_unresolved = (
            classpath_cli_requirement
            .effective_unresolved_requirements
            if classpath_cli_requirement is not None
            else ()
        )

        classpath_cli_effective_by_kind = {
            effective.classpath.name: effective
            for effective
            in classpath_cli_effective
        }

        classpath_cli_effective_entry_count = sum(
            len(
                effective.entries
            )
            for effective
            in classpath_cli_effective
        )

        classpath_cli_effective_fragment_paths = {
            entry.runtime_fragment_path
            for effective
            in classpath_cli_effective
            for entry
            in effective.entries
        }

        classpath_cli_installed_jar_resolutions = (
            classpath_cli_requirement.installed_jar_resolutions
            if classpath_cli_requirement is not None
            else ()
        )

        classpath_cli_installed_jar_resolved = tuple(
            resolution
            for resolution
            in classpath_cli_installed_jar_resolutions
            if resolution.status.value == "resolved"
        )

        classpath_cli_installed_jar_absent = tuple(
            resolution
            for resolution
            in classpath_cli_installed_jar_resolutions
            if resolution.status.value == "absent"
        )

        classpath_cli_installed_jar_ambiguous = tuple(
            resolution
            for resolution
            in classpath_cli_installed_jar_resolutions
            if resolution.status.value == "ambiguous"
        )

        classpath_cli_installed_jar_artifacts = {
            resolution.resolved_artifact.identity_key
            for resolution
            in classpath_cli_installed_jar_resolved
            if resolution.resolved_artifact is not None
        }

        typer.echo()
        typer.echo(
            "Classpath Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed Classpath sources: "
                f"{len(classpath_cli_configurations)}"
            )
        )
        typer.echo(
            (
                "  Parsed Classpath JAR entries: "
                f"{len(classpath_cli_jars)}"
            )
        )
        typer.echo(
            (
                "  Universe Classpath intake present: "
                f"{classpath_cli_requirement is not None}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe Classpath identity match: "
                f"{(
                    classpath_cli_requirement is not None
                    and classpath_cli_requirement.source
                    is parsing.classpath
                )}"
            )
        )
        typer.echo(
            "  SDK applicability:"
        )
        typer.echo(
            (
                "    declarations: "
                f"{len(classpath_cli_applicability)}"
            )
        )
        typer.echo(
            (
                "    active: "
                f"{len(classpath_cli_active)}"
            )
        )
        typer.echo(
            (
                "    inapplicable: "
                f"{len(classpath_cli_inapplicable)}"
            )
        )
        typer.echo(
            (
                "    unresolved: "
                f"{len(classpath_cli_unresolved)}"
            )
        )
        typer.echo(
            (
                "    unbounded: "
                f"{len(classpath_cli_unbounded)}"
            )
        )
        typer.echo(
            (
                "    minimum-bounded: "
                f"{len(classpath_cli_minimum_bounded)}"
            )
        )
        typer.echo(
            (
                "    maximum-bounded: "
                f"{len(classpath_cli_maximum_bounded)}"
            )
        )
        typer.echo(
            (
                "    device SDK: "
                f"{classpath_cli_device_sdk}"
            )
        )
        typer.echo(
            (
                "    device SDK conclusion: "
                + (
                    classpath_cli_sdk_conclusion.status.value
                    if classpath_cli_sdk_conclusion is not None
                    else "<absent>"
                )
            )
        )
        typer.echo(
            "  Effective classpath assembly:"
        )
        typer.echo(
            (
                "    classpaths: "
                f"{len(classpath_cli_effective)}"
            )
        )
        typer.echo(
            (
                "    entries: "
                f"{classpath_cli_effective_entry_count}"
            )
        )
        typer.echo(
            (
                "    unresolved declarations: "
                f"{len(classpath_cli_effective_unresolved)}"
            )
        )
        typer.echo(
            (
                "    runtime fragments: "
                f"{len(classpath_cli_effective_fragment_paths)}"
            )
        )

        for classpath_name in (
            "BOOTCLASSPATH",
            "DEX2OATBOOTCLASSPATH",
            "SYSTEMSERVERCLASSPATH",
            "STANDALONE_SYSTEMSERVER_JARS",
        ):
            effective = (
                classpath_cli_effective_by_kind.get(
                    classpath_name
                )
            )

            typer.echo(
                (
                    f"    {classpath_name}: "
                    f"{(
                        len(effective.entries)
                        if effective is not None
                        else 0
                    )}"
                )
            )

        typer.echo(
            "  Declaration semantics: complete"
        )
        typer.echo(
            "  SDK applicability reconciliation: complete"
        )
        typer.echo(
            "  Effective classpath assembly: complete"
        )
        typer.echo(
            "  Installed JAR reconciliation:"
        )
        typer.echo(
            (
                "    entries: "
                f"{len(classpath_cli_installed_jar_resolutions)}"
            )
        )
        typer.echo(
            (
                "    resolved: "
                f"{len(classpath_cli_installed_jar_resolved)}"
            )
        )
        typer.echo(
            (
                "    absent: "
                f"{len(classpath_cli_installed_jar_absent)}"
            )
        )
        typer.echo(
            (
                "    ambiguous: "
                f"{len(classpath_cli_installed_jar_ambiguous)}"
            )
        )
        typer.echo(
            (
                "    distinct resolved artifacts: "
                f"{len(classpath_cli_installed_jar_artifacts)}"
            )
        )

        if classpath_cli_installed_jar_absent:
            typer.echo(
                "    absent declarations:"
            )

            for resolution in (
                classpath_cli_installed_jar_absent
            ):
                typer.echo(
                    (
                        "      "
                        + resolution.entry
                        .requirement
                        .declared_path
                    )
                )

        if classpath_cli_installed_jar_ambiguous:
            typer.echo(
                "    ambiguous declarations:"
            )

            for resolution in (
                classpath_cli_installed_jar_ambiguous
            ):
                typer.echo(
                    (
                        "      "
                        + resolution.entry
                        .requirement
                        .declared_path
                        + ": "
                        + str(
                            len(
                                resolution.matched_artifacts
                            )
                        )
                        + " candidates"
                    )
                )

        typer.echo(
            "  Installed JAR reconciliation: complete"
        )

        art_runtime_cli_requirement = (
            universe_result.art_runtime_requirement
        )

        typer.echo()
        typer.echo(
            "ART Runtime Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed OAT files: "
                f"{len(parsing.art_runtime.oat_files)}"
            )
        )
        typer.echo(
            (
                "  Parsed VDEX files: "
                f"{len(parsing.art_runtime.vdex_files)}"
            )
        )
        typer.echo(
            (
                "  Parsed ART images: "
                f"{len(parsing.art_runtime.art_images)}"
            )
        )
        typer.echo(
            (
                "  Universe ART Runtime intake present: "
                f"{art_runtime_cli_requirement is not None}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe ART Runtime identity match: "
                f"{(
                    art_runtime_cli_requirement is not None
                    and art_runtime_cli_requirement.source
                    is parsing.art_runtime
                )}"
            )
        )
        art_runtime_oat_dex_files = tuple(
            oat_dex_file
            for oat
            in parsing.art_runtime.oat_files
            for oat_dex_file
            in oat.oat_dex_files
        )

        art_runtime_oat_headers = tuple(
            oat.structural_header
            for oat
            in parsing.art_runtime.oat_files
            if oat.structural_header is not None
        )

        art_runtime_oat_dex_offset_fields = (
            (
                "dex_file_offset",
                lambda item: item.dex_file_offset,
            ),
            (
                "class_offsets_offset",
                lambda item: item.class_offsets_offset,
            ),
            (
                "lookup_table_offset",
                lambda item: item.lookup_table_offset,
            ),
            (
                "dex_layout_sections_offset",
                lambda item: item.dex_layout_sections_offset,
            ),
            (
                "method_bss_mapping_offset",
                lambda item: item.method_bss_mapping_offset,
            ),
            (
                "type_bss_mapping_offset",
                lambda item: item.type_bss_mapping_offset,
            ),
            (
                "public_type_bss_mapping_offset",
                lambda item: item.public_type_bss_mapping_offset,
            ),
            (
                "package_type_bss_mapping_offset",
                lambda item: item.package_type_bss_mapping_offset,
            ),
            (
                "string_bss_mapping_offset",
                lambda item: item.string_bss_mapping_offset,
            ),
            (
                "method_type_bss_mapping_offset",
                lambda item: item.method_type_bss_mapping_offset,
            ),
        )

        art_runtime_dex_region_offset_records = tuple(
            (
                oat,
                oat_dex_file,
            )
            for oat
            in parsing.art_runtime.oat_files
            for oat_dex_file
            in oat.oat_dex_files
            if oat_dex_file.dex_file_offset != 0
        )

        typer.echo(
            "  OatDexFile structural-offset audit:"
        )
        typer.echo(
            (
                "    OatDexFile records: "
                f"{len(art_runtime_oat_dex_files)}"
            )
        )

        for (
            field_name,
            getter,
        ) in art_runtime_oat_dex_offset_fields:
            values = tuple(
                getter(
                    item
                )
                for item
                in art_runtime_oat_dex_files
            )

            absent = sum(
                value is None
                for value
                in values
            )

            zero = sum(
                value == 0
                for value
                in values
                if value is not None
            )

            nonzero = sum(
                value != 0
                for value
                in values
                if value is not None
            )

            distinct_nonzero = {
                value
                for value
                in values
                if (
                    value is not None
                    and value != 0
                )
            }

            typer.echo(
                (
                    f"    {field_name}: "
                    f"nonzero={nonzero} "
                    f"zero={zero} "
                    f"absent={absent} "
                    "distinct_nonzero="
                    f"{len(distinct_nonzero)}"
                )
            )

        typer.echo(
            "    Nonzero dex_file_offset detail:"
        )

        if not art_runtime_dex_region_offset_records:
            typer.echo(
                "      <none>"
            )
        else:
            for (
                oat,
                oat_dex_file,
            ) in art_runtime_dex_region_offset_records:
                typer.echo(
                    (
                        "      "
                        f"{oat.elf.source.display_path}"
                    )
                )
                typer.echo(
                    (
                        "        OatDexFile index: "
                        f"{oat_dex_file.index}"
                    )
                )
                typer.echo(
                    (
                        "        location: "
                        f"{oat_dex_file.dex_file_location}"
                    )
                )
                typer.echo(
                    (
                        "        dex_file_offset: "
                        f"{oat_dex_file.dex_file_offset}"
                    )
                )
                typer.echo(
                    (
                        "        dex checksum: "
                        f"{oat_dex_file.dex_file_location_checksum}"
                    )
                )

        bcp_bss_values = tuple(
            header.bcp_bss_info_offset
            for header
            in art_runtime_oat_headers
        )

        typer.echo(
            (
                "    bcp_bss_info_offset: "
                "nonzero="
                f"{sum(value != 0 for value in bcp_bss_values)} "
                "zero="
                f"{sum(value == 0 for value in bcp_bss_values)} "
                "headers="
                f"{len(bcp_bss_values)}"
            )
        )

        art_runtime_peer_resolutions = (
            art_runtime_cli_requirement.oat_vdex_resolutions
            if art_runtime_cli_requirement is not None
            else ()
        )

        art_runtime_peer_resolved = sum(
            1
            for resolution
            in art_runtime_peer_resolutions
            if resolution.status.value
            == "resolved"
        )

        art_runtime_peer_unpaired = sum(
            1
            for resolution
            in art_runtime_peer_resolutions
            if resolution.status.value
            == "unpaired"
        )

        art_runtime_peer_ambiguous = sum(
            1
            for resolution
            in art_runtime_peer_resolutions
            if resolution.status.value
            == "ambiguous"
        )

        art_runtime_vdex_dispositions = (
            art_runtime_cli_requirement.vdex_dispositions
            if art_runtime_cli_requirement is not None
            else ()
        )

        art_runtime_vdex_disposition_counts = Counter(
            disposition.status.value
            for disposition
            in art_runtime_vdex_dispositions
        )

        art_runtime_vdex_identity_match = (
            art_runtime_cli_requirement is not None
            and tuple(
                disposition.vdex
                for disposition
                in art_runtime_vdex_dispositions
            )
            == parsing.art_runtime.vdex_files
        )

        art_runtime_vdex_oat_peer = (
            art_runtime_vdex_disposition_counts.get(
                "oat_peer",
                0,
            )
        )

        art_runtime_vdex_oat_peer_candidate = (
            art_runtime_vdex_disposition_counts.get(
                "oat_peer_candidate",
                0,
            )
        )

        art_runtime_vdex_no_oat_peer = (
            art_runtime_vdex_disposition_counts.get(
                "no_oat_peer",
                0,
            )
        )

        typer.echo(
            (
                "  OAT/VDEX peer resolutions: "
                f"{len(art_runtime_peer_resolutions)}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX peers resolved: "
                f"{art_runtime_peer_resolved}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX OATs unpaired: "
                f"{art_runtime_peer_unpaired}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX peers ambiguous: "
                f"{art_runtime_peer_ambiguous}"
            )
        )
        typer.echo(
            (
                "  VDEX dispositions: "
                f"{len(art_runtime_vdex_dispositions)}"
            )
        )
        typer.echo(
            (
                "    oat_peer: "
                f"{art_runtime_vdex_oat_peer}"
            )
        )
        typer.echo(
            (
                "    oat_peer_candidate: "
                f"{art_runtime_vdex_oat_peer_candidate}"
            )
        )
        typer.echo(
            (
                "    no_oat_peer: "
                f"{art_runtime_vdex_no_oat_peer}"
            )
        )
        typer.echo(
            (
                "  VDEX disposition identity/order match: "
                f"{art_runtime_vdex_identity_match}"
            )
        )
        typer.echo(
            "  OAT/VDEX peer and VDEX disposition reconciliation: complete"
        )

        art_runtime_checksum_resolutions = (
            art_runtime_cli_requirement.dex_checksum_resolutions
            if art_runtime_cli_requirement is not None
            else ()
        )

        art_runtime_checksum_matched = sum(
            1
            for resolution
            in art_runtime_checksum_resolutions
            if resolution.status.value
            == "matched"
        )

        art_runtime_checksum_count_mismatch = sum(
            1
            for resolution
            in art_runtime_checksum_resolutions
            if resolution.status.value
            == "count_mismatch"
        )

        art_runtime_checksum_mismatch = sum(
            1
            for resolution
            in art_runtime_checksum_resolutions
            if resolution.status.value
            == "checksum_mismatch"
        )

        art_runtime_checksum_unsupported = sum(
            1
            for resolution
            in art_runtime_checksum_resolutions
            if resolution.status.value
            == "unsupported"
        )

        art_runtime_checksum_entries = sum(
            len(
                resolution.entries
            )
            for resolution
            in art_runtime_checksum_resolutions
        )

        art_runtime_checksum_entries_matched = sum(
            1
            for resolution
            in art_runtime_checksum_resolutions
            for entry
            in resolution.entries
            if entry.matches
        )

        art_runtime_checksum_entries_mismatched = (
            art_runtime_checksum_entries
            - art_runtime_checksum_entries_matched
        )

        typer.echo(
            (
                "  OAT/VDEX DEX checksum resolutions: "
                f"{len(art_runtime_checksum_resolutions)}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX checksum peers matched: "
                f"{art_runtime_checksum_matched}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX count mismatches: "
                f"{art_runtime_checksum_count_mismatch}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX checksum mismatches: "
                f"{art_runtime_checksum_mismatch}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX checksum unsupported: "
                f"{art_runtime_checksum_unsupported}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX checksum entries: "
                f"{art_runtime_checksum_entries}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX checksum entries matched: "
                f"{art_runtime_checksum_entries_matched}"
            )
        )
        typer.echo(
            (
                "  OAT/VDEX DEX checksum entries mismatched: "
                f"{art_runtime_checksum_entries_mismatched}"
            )
        )
        typer.echo(
            "  OAT/VDEX DEX checksum reconciliation: complete"
        )
        art_runtime_art_image_oat_resolutions = (
            art_runtime_cli_requirement.art_image_oat_resolutions
            if art_runtime_cli_requirement is not None
            else ()
        )

        art_runtime_art_image_oat_resolved = sum(
            1
            for resolution
            in art_runtime_art_image_oat_resolutions
            if resolution.status.value
            == "resolved"
        )

        art_runtime_art_image_oat_unpaired = sum(
            1
            for resolution
            in art_runtime_art_image_oat_resolutions
            if resolution.status.value
            == "unpaired"
        )

        art_runtime_art_image_oat_ambiguous = sum(
            1
            for resolution
            in art_runtime_art_image_oat_resolutions
            if resolution.status.value
            == "ambiguous"
        )

        art_runtime_art_image_oat_checksum_resolutions = (
            art_runtime_cli_requirement
            .art_image_oat_checksum_resolutions
            if art_runtime_cli_requirement is not None
            else ()
        )

        art_runtime_art_image_oat_checksum_matched = sum(
            1
            for resolution
            in art_runtime_art_image_oat_checksum_resolutions
            if resolution.status.value
            == "matched"
        )

        art_runtime_art_image_oat_checksum_mismatch = sum(
            1
            for resolution
            in art_runtime_art_image_oat_checksum_resolutions
            if resolution.status.value
            == "mismatch"
        )

        art_runtime_art_image_oat_checksum_unsupported = sum(
            1
            for resolution
            in art_runtime_art_image_oat_checksum_resolutions
            if resolution.status.value
            == "unsupported"
        )

        typer.echo(
            (
                "  ART image/OAT peer resolutions: "
                f"{len(art_runtime_art_image_oat_resolutions)}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT peers resolved: "
                f"{art_runtime_art_image_oat_resolved}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT images unpaired: "
                f"{art_runtime_art_image_oat_unpaired}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT peers ambiguous: "
                f"{art_runtime_art_image_oat_ambiguous}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT checksum resolutions: "
                f"{len(art_runtime_art_image_oat_checksum_resolutions)}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT checksum matched: "
                f"{art_runtime_art_image_oat_checksum_matched}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT checksum mismatches: "
                f"{art_runtime_art_image_oat_checksum_mismatch}"
            )
        )
        typer.echo(
            (
                "  ART image/OAT checksum unsupported: "
                f"{art_runtime_art_image_oat_checksum_unsupported}"
            )
        )
        typer.echo(
            "  ART image/OAT reconciliation: complete"
        )
        art_runtime_classpath_relationships = tuple(
            relationship
            for relationship
            in universe_result.cross_family_relationships
            if isinstance(
                relationship,
                AndroidUniverseArtRuntimeClasspathRelationship,
            )
        )

        art_runtime_classpath_resolved = tuple(
            relationship
            for relationship
            in art_runtime_classpath_relationships
            if relationship.status.value == "resolved"
        )

        art_runtime_classpath_unresolved = tuple(
            relationship
            for relationship
            in art_runtime_classpath_relationships
            if relationship.status.value == "unresolved"
        )

        art_runtime_classpath_ambiguous = tuple(
            relationship
            for relationship
            in art_runtime_classpath_relationships
            if relationship.status.value == "ambiguous"
        )

        art_runtime_classpath_dex_evidence_count = sum(
            len(
                relationship.dex_evidence
            )
            for relationship
            in art_runtime_classpath_relationships
        )

        art_runtime_classpath_vdex_evidence = tuple(
            evidence
            for relationship
            in art_runtime_classpath_relationships
            for evidence
            in relationship.vdex_evidence
        )

        art_runtime_classpath_vdex_evidence_count = len(
            art_runtime_classpath_vdex_evidence
        )

        art_runtime_classpath_distinct_vdex_ids = {
            id(
                evidence.disposition.vdex
            )
            for evidence
            in art_runtime_classpath_vdex_evidence
        }

        art_runtime_no_oat_peer_vdex_ids = {
            id(
                disposition.vdex
            )
            for disposition
            in art_runtime_vdex_dispositions
            if disposition.status.value
            == "no_oat_peer"
        }

        art_runtime_classpath_unmatched_vdex_ids = (
            art_runtime_no_oat_peer_vdex_ids
            - art_runtime_classpath_distinct_vdex_ids
        )

        art_runtime_classpath_runtime_paths = {
            relationship.entry.requirement.declared_path
            for relationship
            in art_runtime_classpath_relationships
        }

        typer.echo(
            (
                "  ART Runtime/Classpath relationships: "
                f"{len(art_runtime_classpath_relationships)}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath resolved: "
                f"{len(art_runtime_classpath_resolved)}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath unresolved: "
                f"{len(art_runtime_classpath_unresolved)}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath ambiguous: "
                f"{len(art_runtime_classpath_ambiguous)}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath DEX evidence observations: "
                f"{art_runtime_classpath_dex_evidence_count}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath VDEX evidence observations: "
                f"{art_runtime_classpath_vdex_evidence_count}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath distinct VDEX identities: "
                f"{len(art_runtime_classpath_distinct_vdex_ids)}"
            )
        )
        typer.echo(
            (
                "  NO_OAT_PEER VDEX identities: "
                f"{len(art_runtime_no_oat_peer_vdex_ids)}"
            )
        )
        typer.echo(
            (
                "  NO_OAT_PEER VDEX identities without "
                "Classpath corroboration: "
                f"{len(art_runtime_classpath_unmatched_vdex_ids)}"
            )
        )
        typer.echo(
            (
                "  ART Runtime/Classpath distinct runtime paths: "
                f"{len(art_runtime_classpath_runtime_paths)}"
            )
        )
        typer.echo(
            "  ART Runtime/Classpath reconciliation: complete"
        )

        kernel_module_cli_requirement = (
            universe_result.kernel_module_requirement
        )

        kernel_module_cli_kind_counts = Counter(
            configuration.configuration_kind.value
            for configuration
            in parsing.kernel_module_configurations
        )

        kernel_module_cli_modinfo_count = sum(
            len(module.modinfo_entries)
            for module in parsing.kernel_modules.modules
        )

        kernel_module_cli_module_requirements = (
            kernel_module_cli_requirement.module_requirements
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_configuration_requirements = (
            kernel_module_cli_requirement.configuration_requirements
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_semantic_modinfo = tuple(
            semantic
            for requirement in kernel_module_cli_module_requirements
            for semantic in requirement.modinfo
        )

        kernel_module_cli_configuration_lines = tuple(
            line
            for requirement in kernel_module_cli_configuration_requirements
            for line in requirement.lines
        )

        kernel_module_cli_modinfo_kind_counts = Counter(
            semantic.kind.value
            for semantic in kernel_module_cli_semantic_modinfo
        )

        kernel_module_cli_interpreted_configuration_lines = tuple(
            line
            for line in kernel_module_cli_configuration_lines
            if line.interpreted
        )

        kernel_module_cli_uninterpreted_configuration_lines = tuple(
            line
            for line in kernel_module_cli_configuration_lines
            if not line.interpreted
        )

        kernel_module_cli_configuration_semantic_kind_counts = Counter(
            line.configuration_kind.value
            for line in kernel_module_cli_interpreted_configuration_lines
        )

        kernel_module_cli_modules_with_declared_name = sum(
            1
            for requirement in kernel_module_cli_module_requirements
            if requirement.declared_names
        )

        kernel_module_cli_modules_with_multiple_declared_names = sum(
            1
            for requirement in kernel_module_cli_module_requirements
            if len(requirement.declared_names) > 1
        )

        kernel_module_cli_declared_dependency_count = sum(
            len(requirement.declared_dependencies)
            for requirement in kernel_module_cli_module_requirements
        )

        kernel_module_cli_declared_alias_count = sum(
            len(requirement.declared_aliases)
            for requirement in kernel_module_cli_module_requirements
        )

        kernel_module_cli_firmware_requirement_count = sum(
            len(requirement.firmware_requirements)
            for requirement in kernel_module_cli_module_requirements
        )

        kernel_module_cli_modules_with_vermagic = sum(
            1
            for requirement in kernel_module_cli_module_requirements
            if requirement.vermagic_values
        )

        kernel_module_cli_modules_with_multiple_vermagic = sum(
            1
            for requirement in kernel_module_cli_module_requirements
            if len(requirement.vermagic_values) > 1
        )

        kernel_module_cli_logical_identities = (
            kernel_module_cli_requirement.logical_identities
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_cross_context_identities = tuple(
            identity
            for identity in kernel_module_cli_logical_identities
            if identity.is_cross_context
        )

        kernel_module_cli_single_context_identities = tuple(
            identity
            for identity in kernel_module_cli_logical_identities
            if not identity.is_cross_context
        )

        kernel_module_cli_cross_context_instances = sum(
            len(identity.instances)
            for identity in kernel_module_cli_cross_context_identities
        )

        kernel_module_cli_single_context_instances = sum(
            len(identity.instances)
            for identity in kernel_module_cli_single_context_identities
        )

        kernel_module_cli_identity_context_counts = Counter(
            context
            for identity in kernel_module_cli_logical_identities
            for context in identity.deployment_contexts
        )

        kernel_module_cli_identity_width_counts = Counter(
            len(identity.instances)
            for identity in kernel_module_cli_logical_identities
        )

        kernel_module_cli_hard_dependencies = (
            kernel_module_cli_requirement.hard_dependencies
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_modinfo_dependencies = (
            kernel_module_cli_requirement.modinfo_dependencies
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_load_entries = (
            kernel_module_cli_requirement.load_entries
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_aliases = (
            kernel_module_cli_requirement.aliases
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_first_stage_loading_relationships = tuple(
            relationship
            for relationship
            in universe_result.cross_family_relationships
            if isinstance(
                relationship,
                AndroidUniverseFirstStageKernelModuleLoadingRelationship,
            )
        )

        kernel_module_cli_first_stage_loading_entries = tuple(
            entry
            for relationship
            in kernel_module_cli_first_stage_loading_relationships
            for entry in relationship.load_entries
        )

        kernel_module_cli_first_stage_parallel_policies = tuple(
            relationship.policy
            for relationship
            in kernel_module_cli_first_stage_loading_relationships
            if relationship.policy.parallel
        )

        kernel_module_cli_first_stage_relationship_ids = {
            relationship.relationship_id
            for relationship
            in kernel_module_cli_first_stage_loading_relationships
        }

        kernel_module_cli_first_stage_active_relationships = sum(
            1
            for applicability
            in universe_result.cross_family_relationship_applicability
            if (
                applicability.requirement_id
                in kernel_module_cli_first_stage_relationship_ids
                and applicability.status.value == "active"
            )
        )

        kernel_module_cli_blocklist_entries = (
            kernel_module_cli_requirement.blocklist_entries
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_blocklist_resolved_entries = tuple(
            entry
            for entry in kernel_module_cli_blocklist_entries
            if entry.module is not None
        )

        kernel_module_cli_blocklist_unresolved_entries = tuple(
            entry
            for entry in kernel_module_cli_blocklist_entries
            if entry.module is None
        )

        kernel_module_cli_blocklist_context_counts = Counter(
            entry.module.source.elf.source
            .filesystem_source.source_name
            for entry in kernel_module_cli_blocklist_resolved_entries
        )

        kernel_module_cli_blocklist_resolved_ids = {
            id(
                entry.module
            )
            for entry in kernel_module_cli_blocklist_resolved_entries
        }

        kernel_module_cli_blocklist_load_overlap = tuple(
            entry
            for entry in kernel_module_cli_blocklist_resolved_entries
            if id(
                entry.module
            ) in {
                id(
                    load_entry.module
                )
                for load_entry
                in kernel_module_cli_requirement.load_entries
            }
        )

        kernel_module_cli_blocklist_ko_suffix_count = sum(
            1
            for entry in kernel_module_cli_blocklist_entries
            if (
                entry.source.module is not None
                and entry.source.module.endswith(
                    ".ko"
                )
            )
        )

        kernel_module_cli_soft_dependencies = (
            kernel_module_cli_requirement.soft_dependencies
            if kernel_module_cli_requirement is not None
            else ()
        )

        kernel_module_cli_softdep_context_counts = Counter(
            softdep.owner.source.elf.source
            .filesystem_source.source_name
            for softdep in kernel_module_cli_soft_dependencies
        )

        kernel_module_cli_softdep_pre_references = tuple(
            reference
            for softdep in kernel_module_cli_soft_dependencies
            for reference in softdep.pre_dependencies
        )

        kernel_module_cli_softdep_post_references = tuple(
            reference
            for softdep in kernel_module_cli_soft_dependencies
            for reference in softdep.post_dependencies
        )

        kernel_module_cli_softdep_references = (
            kernel_module_cli_softdep_pre_references
            + kernel_module_cli_softdep_post_references
        )

        kernel_module_cli_softdep_resolved_references = tuple(
            reference
            for reference in kernel_module_cli_softdep_references
            if reference.module is not None
        )

        kernel_module_cli_softdep_unresolved_references = tuple(
            reference
            for reference in kernel_module_cli_softdep_references
            if reference.module is None
        )

        kernel_module_cli_softdep_corroborated = tuple(
            softdep
            for softdep in kernel_module_cli_soft_dependencies
            if softdep.modinfo is not None
        )

        kernel_module_cli_softdep_uncorroborated = tuple(
            softdep
            for softdep in kernel_module_cli_soft_dependencies
            if softdep.modinfo is None
        )

        kernel_module_cli_softdep_unresolved_names = tuple(
            sorted(
                {
                    reference.declared_name.replace(
                        "-",
                        "_",
                    )
                    for reference
                    in kernel_module_cli_softdep_unresolved_references
                }
            )
        )

        kernel_module_cli_alias_context_counts = Counter(
            alias.module.source.elf.source
            .filesystem_source.source_name
            for alias in kernel_module_cli_aliases
        )

        kernel_module_cli_alias_corroborated = tuple(
            alias
            for alias in kernel_module_cli_aliases
            if alias.modinfo
        )

        kernel_module_cli_alias_uncorroborated = tuple(
            alias
            for alias in kernel_module_cli_aliases
            if not alias.modinfo
        )

        kernel_module_cli_alias_modinfo_observation_count = sum(
            len(
                alias.modinfo
            )
            for alias in kernel_module_cli_aliases
        )

        kernel_module_cli_alias_multiple_modinfo_corroboration_count = sum(
            1
            for alias in kernel_module_cli_aliases
            if len(
                alias.modinfo
            ) > 1
        )

        kernel_module_cli_alias_pattern_targets = {}

        for alias in kernel_module_cli_aliases:
            context = (
                alias.module.source.elf.source
                .filesystem_source.source_name
            )

            key = (
                context,
                alias.source.alias_pattern,
            )

            kernel_module_cli_alias_pattern_targets.setdefault(
                key,
                [],
            ).append(
                alias.module
            )

        kernel_module_cli_duplicate_alias_patterns = {
            key: tuple(
                modules
            )
            for key, modules
            in kernel_module_cli_alias_pattern_targets.items()
            if len(
                modules
            ) > 1
        }

        kernel_module_cli_same_target_duplicate_alias_patterns = sum(
            1
            for modules
            in kernel_module_cli_duplicate_alias_patterns.values()
            if len(
                {
                    id(
                        module
                    )
                    for module in modules
                }
            )
            == 1
        )

        kernel_module_cli_multi_target_duplicate_alias_patterns = sum(
            1
            for modules
            in kernel_module_cli_duplicate_alias_patterns.values()
            if len(
                {
                    id(
                        module
                    )
                    for module in modules
                }
            )
            > 1
        )

        kernel_module_cli_load_entry_context_counts = Counter(
            entry.module.source.elf.source
            .filesystem_source.source_name
            for entry in kernel_module_cli_load_entries
        )

        kernel_module_cli_modinfo_dependency_context_counts = Counter(
            dependency.owner.source.elf.source
            .filesystem_source.source_name
            for dependency in kernel_module_cli_modinfo_dependencies
        )

        kernel_module_cli_hard_dependency_context_counts = Counter(
            dependency.owner.source.elf.source
            .filesystem_source.source_name
            for dependency in kernel_module_cli_hard_dependencies
        )

        kernel_module_cli_hard_dependency_owner_ids = {
            id(dependency.owner)
            for dependency in kernel_module_cli_hard_dependencies
        }

        kernel_module_cli_dep_configuration_lines = tuple(
            line
            for requirement in kernel_module_cli_configuration_requirements
            if requirement.source.configuration_kind.value == "modules.dep"
            for line in requirement.lines
        )

        kernel_module_cli_dep_owner_count = len(
            kernel_module_cli_dep_configuration_lines
        )

        kernel_module_cli_dep_declared_edge_count = sum(
            len(line.dependencies)
            for line in kernel_module_cli_dep_configuration_lines
        )

        typer.echo()
        typer.echo(
            "Kernel Module Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed kernel modules: "
                f"{len(parsing.kernel_modules.modules)}"
            )
        )
        typer.echo(
            (
                "  Parsed modinfo entries: "
                f"{kernel_module_cli_modinfo_count}"
            )
        )
        typer.echo(
            (
                "  Parsed modules.* configurations: "
                f"{len(parsing.kernel_module_configurations)}"
            )
        )
        typer.echo(
            "  Configuration kinds:"
        )

        if kernel_module_cli_kind_counts:
            for kind, count in sorted(
                kernel_module_cli_kind_counts.items()
            ):
                typer.echo(
                    f"    {kind}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            (
                "  Universe Kernel Module intake present: "
                f"{kernel_module_cli_requirement is not None}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe Kernel Module identity match: "
                f"{(
                    kernel_module_cli_requirement is not None
                    and kernel_module_cli_requirement.modules
                    is parsing.kernel_modules
                    and kernel_module_cli_requirement.configurations
                    is parsing.kernel_module_configurations
                )}"
            )
        )

        typer.echo(
            "  Semantic coverage:"
        )
        typer.echo(
            (
                "    module requirements: "
                f"{len(kernel_module_cli_module_requirements)}"
            )
        )
        typer.echo(
            (
                "    configuration requirements: "
                f"{len(kernel_module_cli_configuration_requirements)}"
            )
        )
        typer.echo(
            (
                "    modinfo observations: "
                f"{len(kernel_module_cli_semantic_modinfo)}"
            )
        )
        typer.echo(
            (
                "    modules.* semantic lines: "
                f"{len(kernel_module_cli_configuration_lines)}"
            )
        )

        typer.echo(
            "  Modinfo semantic kinds:"
        )

        if kernel_module_cli_modinfo_kind_counts:
            for kind, count in sorted(
                kernel_module_cli_modinfo_kind_counts.items()
            ):
                typer.echo(
                    f"    {kind}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            "  Module-local semantic summaries:"
        )
        typer.echo(
            (
                "    modules with declared name: "
                f"{kernel_module_cli_modules_with_declared_name}"
            )
        )
        typer.echo(
            (
                "    modules with multiple declared names: "
                f"{kernel_module_cli_modules_with_multiple_declared_names}"
            )
        )
        typer.echo(
            (
                "    declared dependencies: "
                f"{kernel_module_cli_declared_dependency_count}"
            )
        )
        typer.echo(
            (
                "    declared aliases: "
                f"{kernel_module_cli_declared_alias_count}"
            )
        )
        typer.echo(
            (
                "    firmware requirements: "
                f"{kernel_module_cli_firmware_requirement_count}"
            )
        )
        typer.echo(
            (
                "    modules with vermagic: "
                f"{kernel_module_cli_modules_with_vermagic}"
            )
        )
        typer.echo(
            (
                "    modules with multiple vermagic values: "
                f"{kernel_module_cli_modules_with_multiple_vermagic}"
            )
        )

        typer.echo(
            "  Logical module identity reconciliation:"
        )
        typer.echo(
            (
                "    physical module instances: "
                f"{len(kernel_module_cli_module_requirements)}"
            )
        )
        typer.echo(
            (
                "    logical module identities: "
                f"{len(kernel_module_cli_logical_identities)}"
            )
        )
        typer.echo(
            (
                "    cross-context identities: "
                f"{len(kernel_module_cli_cross_context_identities)}"
            )
        )
        typer.echo(
            (
                "    single-context identities: "
                f"{len(kernel_module_cli_single_context_identities)}"
            )
        )
        typer.echo(
            (
                "    physical instances in cross-context identities: "
                f"{kernel_module_cli_cross_context_instances}"
            )
        )
        typer.echo(
            (
                "    physical instances in single-context identities: "
                f"{kernel_module_cli_single_context_instances}"
            )
        )

        typer.echo(
            "    identity presence by deployment context:"
        )

        if kernel_module_cli_identity_context_counts:
            for context, count in sorted(
                kernel_module_cli_identity_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            "    physical instances per logical identity:"
        )

        if kernel_module_cli_identity_width_counts:
            for width, count in sorted(
                kernel_module_cli_identity_width_counts.items()
            ):
                typer.echo(
                    f"      {width}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            "  Hard dependency reconciliation:"
        )
        typer.echo(
            (
                "    modules.dep owner records: "
                f"{kernel_module_cli_dep_owner_count}"
            )
        )
        typer.echo(
            (
                "    declared hard dependency edges: "
                f"{kernel_module_cli_dep_declared_edge_count}"
            )
        )
        typer.echo(
            (
                "    resolved hard dependency edges: "
                f"{len(kernel_module_cli_hard_dependencies)}"
            )
        )
        typer.echo(
            (
                "    owners participating in hard dependencies: "
                f"{len(kernel_module_cli_hard_dependency_owner_ids)}"
            )
        )

        typer.echo(
            "    resolved edges by deployment context:"
        )

        if kernel_module_cli_hard_dependency_context_counts:
            for context, count in sorted(
                kernel_module_cli_hard_dependency_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            (
                "    unresolved owner paths: "
                f"{max(
                    kernel_module_cli_dep_owner_count
                    - sum(
                        1
                        for line in kernel_module_cli_dep_configuration_lines
                        if any(
                            dependency.source is line
                            for dependency in kernel_module_cli_hard_dependencies
                        )
                        or not line.dependencies
                    ),
                    0,
                )}"
            )
        )

        typer.echo(
            (
                "    unresolved dependency edges: "
                f"{max(
                    kernel_module_cli_dep_declared_edge_count
                    - len(kernel_module_cli_hard_dependencies),
                    0,
                )}"
            )
        )

        typer.echo(
            "  Modinfo dependency reconciliation:"
        )
        typer.echo(
            (
                "    declared dependency names: "
                f"{sum(
                    len(module.declared_dependencies)
                    for module in kernel_module_cli_module_requirements
                )}"
            )
        )
        typer.echo(
            (
                "    corroborated declarations: "
                f"{len(kernel_module_cli_modinfo_dependencies)}"
            )
        )
        typer.echo(
            (
                "    unresolved declarations: "
                f"{max(
                    sum(
                        len(module.declared_dependencies)
                        for module in kernel_module_cli_module_requirements
                    )
                    - len(kernel_module_cli_modinfo_dependencies),
                    0,
                )}"
            )
        )

        typer.echo(
            "    corroborated declarations by deployment context:"
        )

        if kernel_module_cli_modinfo_dependency_context_counts:
            for context, count in sorted(
                kernel_module_cli_modinfo_dependency_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            (
                "    modules.dep hard edges without modinfo declaration: "
                f"{max(
                    len(kernel_module_cli_hard_dependencies)
                    - len(kernel_module_cli_modinfo_dependencies),
                    0,
                )}"
            )
        )

        typer.echo(
            "  Ordered load-sequence reconciliation:"
        )
        typer.echo(
            (
                "    modules.load entries: "
                f"{sum(
                    1
                    for configuration
                    in kernel_module_cli_configuration_requirements
                    for line in configuration.lines
                    if (
                        line.configuration_kind.value
                        == "modules.load"
                    )
                )}"
            )
        )
        typer.echo(
            (
                "    resolved load entries: "
                f"{len(kernel_module_cli_load_entries)}"
            )
        )
        typer.echo(
            (
                "    unresolved load entries: "
                f"{max(
                    sum(
                        1
                        for configuration
                        in kernel_module_cli_configuration_requirements
                        for line in configuration.lines
                        if (
                            line.configuration_kind.value
                            == "modules.load"
                        )
                    )
                    - len(kernel_module_cli_load_entries),
                    0,
                )}"
            )
        )
        typer.echo(
            "    resolved load entries by deployment context:"
        )

        if kernel_module_cli_load_entry_context_counts:
            for context, count in sorted(
                kernel_module_cli_load_entry_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            "  Alias reconciliation:"
        )
        typer.echo(
            (
                "    modules.alias declarations: "
                f"{sum(
                    1
                    for configuration
                    in kernel_module_cli_configuration_requirements
                    for line in configuration.lines
                    if (
                        line.configuration_kind.value
                        == "modules.alias"
                    )
                )}"
            )
        )
        typer.echo(
            (
                "    resolved aliases: "
                f"{len(kernel_module_cli_aliases)}"
            )
        )
        typer.echo(
            (
                "    unresolved aliases: "
                f"{max(
                    sum(
                        1
                        for configuration
                        in kernel_module_cli_configuration_requirements
                        for line in configuration.lines
                        if (
                            line.configuration_kind.value
                            == "modules.alias"
                        )
                    )
                    - len(kernel_module_cli_aliases),
                    0,
                )}"
            )
        )

        typer.echo(
            "    resolved aliases by deployment context:"
        )

        if kernel_module_cli_alias_context_counts:
            for context, count in sorted(
                kernel_module_cli_alias_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            "    exact standard modinfo corroboration:"
        )
        typer.echo(
            (
                "      corroborated: "
                f"{len(kernel_module_cli_alias_corroborated)}"
            )
        )
        typer.echo(
            (
                "      modules.alias-only: "
                f"{len(kernel_module_cli_alias_uncorroborated)}"
            )
        )
        typer.echo(
            (
                "      exact modinfo observations: "
                f"{kernel_module_cli_alias_modinfo_observation_count}"
            )
        )
        typer.echo(
            (
                "      declarations with repeated corroboration: "
                f"{kernel_module_cli_alias_multiple_modinfo_corroboration_count}"
            )
        )

        typer.echo(
            "    duplicate alias patterns:"
        )
        typer.echo(
            (
                "      groups: "
                f"{len(kernel_module_cli_duplicate_alias_patterns)}"
            )
        )
        typer.echo(
            (
                "      same-target: "
                f"{kernel_module_cli_same_target_duplicate_alias_patterns}"
            )
        )
        typer.echo(
            (
                "      multi-target: "
                f"{kernel_module_cli_multi_target_duplicate_alias_patterns}"
            )
        )

        typer.echo(
            "  Soft dependency reconciliation:"
        )
        typer.echo(
            (
                "    modules.softdep declarations: "
                f"{len(kernel_module_cli_soft_dependencies)}"
            )
        )
        typer.echo(
            (
                "    reconciled declarations: "
                f"{len(kernel_module_cli_soft_dependencies)}"
            )
        )

        typer.echo(
            "    declarations by deployment context:"
        )

        if kernel_module_cli_softdep_context_counts:
            for context, count in sorted(
                kernel_module_cli_softdep_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            (
                "    pre references: "
                f"{len(kernel_module_cli_softdep_pre_references)}"
            )
        )
        typer.echo(
            (
                "    post references: "
                f"{len(kernel_module_cli_softdep_post_references)}"
            )
        )
        typer.echo(
            (
                "    physical module references: "
                f"{len(kernel_module_cli_softdep_resolved_references)}"
            )
        )
        typer.echo(
            (
                "    logical-only references: "
                f"{len(kernel_module_cli_softdep_unresolved_references)}"
            )
        )

        typer.echo(
            "    exact standard modinfo corroboration:"
        )
        typer.echo(
            (
                "      corroborated declarations: "
                f"{len(kernel_module_cli_softdep_corroborated)}"
            )
        )
        typer.echo(
            (
                "      modules.softdep-only: "
                f"{len(kernel_module_cli_softdep_uncorroborated)}"
            )
        )

        typer.echo(
            "    logical-only targets:"
        )

        if kernel_module_cli_softdep_unresolved_names:
            for name in kernel_module_cli_softdep_unresolved_names:
                typer.echo(
                    f"      {name}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            "  Blocklist reconciliation:"
        )
        typer.echo(
            (
                "    modules.blocklist declarations: "
                f"{len(kernel_module_cli_blocklist_entries)}"
            )
        )
        typer.echo(
            (
                "    resolved targets: "
                f"{len(kernel_module_cli_blocklist_resolved_entries)}"
            )
        )
        typer.echo(
            (
                "    unresolved logical targets: "
                f"{len(kernel_module_cli_blocklist_unresolved_entries)}"
            )
        )

        if kernel_module_cli_blocklist_unresolved_entries:
            for entry in kernel_module_cli_blocklist_unresolved_entries:
                typer.echo(
                    f"      {entry.source.module}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            "    resolved targets by deployment context:"
        )

        if kernel_module_cli_blocklist_context_counts:
            for context, count in sorted(
                kernel_module_cli_blocklist_context_counts.items()
            ):
                typer.echo(
                    f"      {context}: {count}"
                )
        else:
            typer.echo(
                "      none"
            )

        typer.echo(
            (
                "    declarations with .ko suffix: "
                f"{kernel_module_cli_blocklist_ko_suffix_count}"
            )
        )
        typer.echo(
            (
                "    also explicitly listed in modules.load: "
                f"{len(kernel_module_cli_blocklist_load_overlap)}"
            )
        )

        typer.echo(
            "  First-stage module-loading reconciliation:"
        )
        typer.echo(
            (
                "    relationships: "
                f"{len(kernel_module_cli_first_stage_loading_relationships)}"
            )
        )
        typer.echo(
            (
                "    vendor_kernel_boot load entries: "
                f"{len(kernel_module_cli_first_stage_loading_entries)}"
            )
        )
        typer.echo(
            (
                "    parallel-loading policies: "
                f"{len(kernel_module_cli_first_stage_parallel_policies)}"
            )
        )
        typer.echo(
            (
                "    active relationships: "
                f"{kernel_module_cli_first_stage_active_relationships}"
            )
        )

        if kernel_module_cli_first_stage_loading_relationships:
            for relationship in (
                kernel_module_cli_first_stage_loading_relationships
            ):
                typer.echo(
                    (
                        "    policy: "
                        f"{relationship.policy.source.key}="
                        f"{relationship.policy.source.value} "
                        f"parallel={relationship.policy.parallel}"
                    )
                )

        typer.echo(
            "  modules.* line semantics:"
        )

        if kernel_module_cli_configuration_semantic_kind_counts:
            for kind, count in sorted(
                kernel_module_cli_configuration_semantic_kind_counts.items()
            ):
                typer.echo(
                    f"    {kind}: {count}"
                )
        else:
            typer.echo(
                "    none"
            )

        typer.echo(
            (
                "    interpreted: "
                f"{len(kernel_module_cli_interpreted_configuration_lines)}"
            )
        )
        typer.echo(
            (
                "    uninterpreted: "
                f"{len(kernel_module_cli_uninterpreted_configuration_lines)}"
            )
        )

        typer.echo(
            "  Logical identity reconciliation: complete"
        )
        typer.echo(
            "  Hard dependency reconciliation: complete"
        )
        typer.echo(
            "  Modinfo dependency reconciliation: complete"
        )
        typer.echo(
            "  Ordered load reconciliation: complete"
        )
        typer.echo(
            "  Alias reconciliation: complete"
        )
        typer.echo(
            "  Softdep reconciliation: complete"
        )
        typer.echo(
            "  Blocklist reconciliation: complete"
        )
        typer.echo(
            "  Boot-policy reconciliation: complete"
        )

        linker_cli_requirement = (
            universe_result.linker_requirement
        )

        linker_cli_section_count = sum(
            len(configuration.sections)
            for configuration
            in parsing.linker_configurations
        )

        linker_cli_assignment_count = sum(
            len(configuration.assignments)
            for configuration
            in parsing.linker_configurations
        )

        linker_cli_native_declaration_count = sum(
            len(configuration.declarations)
            for configuration
            in parsing.native_library_configurations
        )

        linker_cli_protobuf_contribution_count = sum(
            len(configuration.contributions)
            for configuration
            in parsing.linker_protobuf_configurations
        )

        typer.echo()
        typer.echo(
            "Linker Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed linker text configurations: "
                f"{len(parsing.linker_configurations)}"
            )
        )
        typer.echo(
            (
                "  Parsed linker sections: "
                f"{linker_cli_section_count}"
            )
        )
        typer.echo(
            (
                "  Parsed linker assignments: "
                f"{linker_cli_assignment_count}"
            )
        )
        typer.echo(
            (
                "  Parsed linker protobuf configurations: "
                f"{len(parsing.linker_protobuf_configurations)}"
            )
        )
        typer.echo(
            (
                "  Parsed linker protobuf contributions: "
                f"{linker_cli_protobuf_contribution_count}"
            )
        )
        typer.echo(
            (
                "  Parsed native-library configurations: "
                f"{len(parsing.native_library_configurations)}"
            )
        )
        typer.echo(
            (
                "  Parsed native-library declarations: "
                f"{linker_cli_native_declaration_count}"
            )
        )
        typer.echo(
            (
                "  Universe Linker intake present: "
                f"{linker_cli_requirement is not None}"
            )
        )
        typer.echo(
            (
                "  Parsing/Universe Linker identity match: "
                f"{(
                    linker_cli_requirement is not None
                    and linker_cli_requirement.configurations
                    is parsing.linker_configurations
                    and linker_cli_requirement.protobuf_configurations
                    is parsing.linker_protobuf_configurations
                    and linker_cli_requirement.native_library_configurations
                    is parsing.native_library_configurations
                )}"
            )
        )
        linker_text_semantics = (
            linker_cli_requirement.text_configuration_semantics
            if linker_cli_requirement is not None
            else ()
        )

        linker_semantic_section_count = sum(
            len(
                configuration.sections
            )
            for configuration
            in linker_text_semantics
        )

        linker_semantic_namespace_count = sum(
            len(
                section.namespaces
            )
            for configuration
            in linker_text_semantics
            for section
            in configuration.sections
        )

        linker_semantic_directory_route_count = sum(
            len(
                section.directory_routes
            )
            for configuration
            in linker_text_semantics
            for section
            in configuration.sections
        )

        linker_semantic_link_count = sum(
            len(
                namespace.links
            )
            for configuration
            in linker_text_semantics
            for section
            in configuration.sections
            for namespace
            in section.namespaces
        )

        linker_semantic_shared_library_count = sum(
            len(
                link.shared_libs
            )
            for configuration
            in linker_text_semantics
            for section
            in configuration.sections
            for namespace
            in section.namespaces
            for link
            in namespace.links
        )

        linker_semantic_assignment_count = sum(
            len(
                configuration.source.assignments
            )
            for configuration
            in linker_text_semantics
        )

        linker_semantic_uninterpreted_count = sum(
            len(
                configuration.uninterpreted_assignments
            )
            for configuration
            in linker_text_semantics
        )

        typer.echo(
            (
                "  Semantic text configurations: "
                f"{len(linker_text_semantics)}"
            )
        )
        typer.echo(
            (
                "  Semantic sections: "
                f"{linker_semantic_section_count}"
            )
        )
        typer.echo(
            (
                "  Semantic namespaces: "
                f"{linker_semantic_namespace_count}"
            )
        )
        typer.echo(
            (
                "  Semantic directory routes: "
                f"{linker_semantic_directory_route_count}"
            )
        )
        typer.echo(
            (
                "  Semantic namespace links: "
                f"{linker_semantic_link_count}"
            )
        )
        typer.echo(
            (
                "  Semantic shared-library link entries: "
                f"{linker_semantic_shared_library_count}"
            )
        )
        typer.echo(
            (
                "  Semantic interpreted assignments: "
                f"{(
                    linker_semantic_assignment_count
                    - linker_semantic_uninterpreted_count
                )}"
            )
        )
        typer.echo(
            (
                "  Semantic uninterpreted assignments: "
                f"{linker_semantic_uninterpreted_count}"
            )
        )
        typer.echo(
            "  Text namespace semantic reconciliation: complete"
        )
        linker_protobuf_semantics = (
            linker_cli_requirement.protobuf_configuration_semantics
            if linker_cli_requirement is not None
            else ()
        )

        linker_protobuf_usage_counts = {
            "apex_local": 0,
            "system_context": 0,
            "vendor_context": 0,
            "product_context": 0,
            "unclassified": 0,
        }

        linker_protobuf_visibility_counts = {
            "default_hidden": 0,
            "explicit_hidden": 0,
            "explicit_visible": 0,
        }

        for configuration in linker_protobuf_semantics:
            linker_protobuf_usage_counts[
                configuration.usage.value
            ] += 1

            linker_protobuf_visibility_counts[
                configuration.visibility_policy.value
            ] += 1

        linker_protobuf_permitted_path_count = sum(
            len(
                configuration.permitted_paths
            )
            for configuration
            in linker_protobuf_semantics
        )

        linker_protobuf_provide_count = sum(
            len(
                configuration.provided_libraries
            )
            for configuration
            in linker_protobuf_semantics
        )

        linker_protobuf_require_count = sum(
            len(
                configuration.required_libraries
            )
            for configuration
            in linker_protobuf_semantics
        )

        linker_protobuf_contribution_count = sum(
            len(
                configuration.contributions
            )
            for configuration
            in linker_protobuf_semantics
        )

        linker_protobuf_unknown_field_count = sum(
            len(
                configuration.unknown_fields
            )
            for configuration
            in linker_protobuf_semantics
        )

        typer.echo(
            (
                "  Semantic protobuf configurations: "
                f"{len(linker_protobuf_semantics)}"
            )
        )
        typer.echo(
            (
                "  Protobuf usage APEX-local: "
                f"{linker_protobuf_usage_counts['apex_local']}"
            )
        )
        typer.echo(
            (
                "  Protobuf usage system context: "
                f"{linker_protobuf_usage_counts['system_context']}"
            )
        )
        typer.echo(
            (
                "  Protobuf usage vendor context: "
                f"{linker_protobuf_usage_counts['vendor_context']}"
            )
        )
        typer.echo(
            (
                "  Protobuf usage product context: "
                f"{linker_protobuf_usage_counts['product_context']}"
            )
        )
        typer.echo(
            (
                "  Protobuf usage unclassified: "
                f"{linker_protobuf_usage_counts['unclassified']}"
            )
        )
        typer.echo(
            (
                "  Protobuf visibility default hidden: "
                f"{linker_protobuf_visibility_counts['default_hidden']}"
            )
        )
        typer.echo(
            (
                "  Protobuf visibility explicit hidden: "
                f"{linker_protobuf_visibility_counts['explicit_hidden']}"
            )
        )
        typer.echo(
            (
                "  Protobuf visibility explicit visible: "
                f"{linker_protobuf_visibility_counts['explicit_visible']}"
            )
        )
        typer.echo(
            (
                "  Protobuf permitted paths: "
                f"{linker_protobuf_permitted_path_count}"
            )
        )
        typer.echo(
            (
                "  Protobuf provided libraries: "
                f"{linker_protobuf_provide_count}"
            )
        )
        typer.echo(
            (
                "  Protobuf required libraries: "
                f"{linker_protobuf_require_count}"
            )
        )
        typer.echo(
            (
                "  Protobuf contributions: "
                f"{linker_protobuf_contribution_count}"
            )
        )
        typer.echo(
            (
                "  Protobuf unknown fields: "
                f"{linker_protobuf_unknown_field_count}"
            )
        )
        typer.echo(
            "  Protobuf local semantic reconciliation: complete"
        )
        linker_native_semantics = (
            linker_cli_requirement.native_library_configuration_semantics
            if linker_cli_requirement is not None
            else ()
        )

        linker_native_policy_counts = Counter()

        linker_native_bitness_counts = {
            "all": 0,
            "32": 0,
            "64": 0,
        }

        linker_native_declaration_count = 0
        linker_native_uninterpreted_count = 0
        linker_native_nopreload_count = 0
        linker_native_qualified_count = 0

        for configuration in linker_native_semantics:
            linker_native_policy_counts[
                configuration.policy_kind.value
            ] += 1

            linker_native_uninterpreted_count += len(
                configuration.uninterpreted_declarations
            )

            for declaration in configuration.declarations:
                linker_native_declaration_count += 1

                linker_native_bitness_counts[
                    declaration.bitness.value
                ] += 1

                if declaration.nopreload:
                    linker_native_nopreload_count += 1

                if declaration.qualifier_tokens:
                    linker_native_qualified_count += 1

        typer.echo(
            (
                "  Semantic native-library configurations: "
                f"{len(linker_native_semantics)}"
            )
        )
        typer.echo(
            (
                "  Native policy system public: "
                f"{linker_native_policy_counts['system_public']}"
            )
        )
        typer.echo(
            (
                "  Native policy extended public: "
                f"{linker_native_policy_counts['extended_public']}"
            )
        )
        typer.echo(
            (
                "  Native policy vendor public: "
                f"{linker_native_policy_counts['vendor_public']}"
            )
        )
        typer.echo(
            (
                "  Native policy LLNDK: "
                f"{linker_native_policy_counts['llndk']}"
            )
        )
        typer.echo(
            (
                "  Native policy sanitizer: "
                f"{linker_native_policy_counts['sanitizer']}"
            )
        )
        typer.echo(
            (
                "  Native policy VNDK core variant: "
                f"{linker_native_policy_counts['vndk_core_variant']}"
            )
        )
        typer.echo(
            (
                "  Native policy VNDK SP: "
                f"{linker_native_policy_counts['vndk_sp']}"
            )
        )
        typer.echo(
            (
                "  Native policy VNDK core: "
                f"{linker_native_policy_counts['vndk_core']}"
            )
        )
        typer.echo(
            (
                "  Native policy VNDK private: "
                f"{linker_native_policy_counts['vndk_private']}"
            )
        )
        typer.echo(
            (
                "  Native policy unclassified: "
                f"{linker_native_policy_counts['unclassified']}"
            )
        )
        typer.echo(
            (
                "  Native semantic declarations: "
                f"{linker_native_declaration_count}"
            )
        )
        typer.echo(
            (
                "  Native uninterpreted declarations: "
                f"{linker_native_uninterpreted_count}"
            )
        )
        typer.echo(
            (
                "  Native bitness all: "
                f"{linker_native_bitness_counts['all']}"
            )
        )
        typer.echo(
            (
                "  Native bitness 32: "
                f"{linker_native_bitness_counts['32']}"
            )
        )
        typer.echo(
            (
                "  Native bitness 64: "
                f"{linker_native_bitness_counts['64']}"
            )
        )
        typer.echo(
            (
                "  Native nopreload declarations: "
                f"{linker_native_nopreload_count}"
            )
        )
        typer.echo(
            (
                "  Native qualified declarations: "
                f"{linker_native_qualified_count}"
            )
        )
        typer.echo(
            "  Native-library local semantic reconciliation: complete"
        )
        linker_runtime_policies = (
            linker_cli_requirement.runtime_policies
            if linker_cli_requirement is not None
            else ()
        )

        linker_root_runtime_policy_count = sum(
            policy.runtime_context.is_root
            for policy in linker_runtime_policies
        )

        linker_nested_runtime_policy_count = sum(
            policy.runtime_context.is_nested
            for policy in linker_runtime_policies
        )

        linker_runtime_policy_text_count = sum(
            len(
                policy.text_configurations
            )
            for policy in linker_runtime_policies
        )

        linker_runtime_policy_protobuf_count = sum(
            len(
                policy.protobuf_configurations
            )
            for policy in linker_runtime_policies
        )

        linker_runtime_policy_native_count = sum(
            len(
                policy.native_library_configurations
            )
            for policy in linker_runtime_policies
        )

        typer.echo(
            (
                "  Unified Linker runtime policies: "
                f"{len(linker_runtime_policies)}"
            )
        )
        typer.echo(
            (
                "  Root runtime policies: "
                f"{linker_root_runtime_policy_count}"
            )
        )
        typer.echo(
            (
                "  Nested runtime policies: "
                f"{linker_nested_runtime_policy_count}"
            )
        )
        typer.echo(
            (
                "  Runtime-policy text configurations: "
                f"{linker_runtime_policy_text_count}"
            )
        )
        typer.echo(
            (
                "  Runtime-policy protobuf configurations: "
                f"{linker_runtime_policy_protobuf_count}"
            )
        )
        typer.echo(
            (
                "  Runtime-policy native-library configurations: "
                f"{linker_runtime_policy_native_count}"
            )
        )
        typer.echo(
            "  Linker runtime-policy grouping: complete"
        )

        #
        # Effective/generated linkerconfig topology and runtime execution
        # semantics are reported by the downstream Runtime Linking stage.
        # Android Device Universe reports only the canonical semantic handoff.
        #

        linker_apex_memberships = tuple(
            relationship
            for relationship
            in universe_result.cross_family_relationships
            if relationship.kind.value == "linker_apex"
        )

        linker_apex_context_applicability = (
            universe_result.linker_apex_context_applicability
        )

        linker_apex_namespace_inputs = (
            universe_result.linker_apex_namespace_inputs
        )

        linker_apex_public_library_conclusions = (
            universe_result.linker_apex_public_library_conclusions
        )

        linker_apex_native_library_conclusions = (
            universe_result.linker_apex_native_library_conclusions
        )

        linker_elf_contexts = (
            universe_result.linker_elf_contexts
        )

        typer.echo(
            "  Linker/APEX canonical semantic handoff:"
        )

        typer.echo(
            (
                "    Membership relationships: "
                f"{len(linker_apex_memberships)}"
            )
        )

        typer.echo(
            (
                "    Context-applicability conclusions: "
                f"{len(linker_apex_context_applicability)}"
            )
        )

        typer.echo(
            (
                "    APEX-local namespace inputs: "
                f"{len(linker_apex_namespace_inputs)}"
            )
        )

        typer.echo(
            (
                "    Public-library conclusions: "
                f"{len(linker_apex_public_library_conclusions)}"
            )
        )

        typer.echo(
            (
                "    requireNativeLibs conclusions: "
                f"{len(linker_apex_native_library_conclusions)}"
            )
        )

        typer.echo(
            (
                "    ELF runtime/configuration contexts: "
                f"{len(linker_elf_contexts)}"
            )
        )

        linker_apex_native_status_counts = Counter(
            conclusion.status.value
            for conclusion
            in linker_apex_native_library_conclusions
        )

        linker_apex_native_provider_counts = Counter(
            conclusion.provider_kind.value
            for conclusion
            in linker_apex_native_library_conclusions
        )

        typer.echo(
            "    requireNativeLibs status:"
        )

        for status_name in (
            "resolved",
            "ambiguous",
            "unresolved",
        ):
            typer.echo(
                (
                    f"      {status_name}: "
                    f"{linker_apex_native_status_counts.get(
                        status_name,
                        0,
                    )}"
                )
            )

        if linker_apex_native_provider_counts:
            typer.echo(
                "    requireNativeLibs provider kinds:"
            )

            for (
                provider_kind,
                provider_count,
            ) in sorted(
                linker_apex_native_provider_counts.items()
            ):
                typer.echo(
                    (
                        f"      {provider_kind}: "
                        f"{provider_count}"
                    )
                )


        unresolved_linker_apex_native = tuple(
            conclusion
            for conclusion
            in linker_apex_native_library_conclusions
            if conclusion.provider_kind.value == "none"
        )

        if unresolved_linker_apex_native:
            typer.echo(
                "    requireNativeLibs unresolved detail:"
            )

            for conclusion in sorted(
                unresolved_linker_apex_native,
                key=lambda value: (
                    value.library_name,
                    value.requirement_index,
                ),
            ):
                apex_requirement = (
                    conclusion
                    .context_applicability
                    .membership_relationship
                    .apex_requirement
                )

                typer.echo(
                    (
                        "      "
                        f"{apex_requirement.apex_name}"
                        f"[{conclusion.requirement_index}]: "
                        f"{conclusion.library_name}"
                    )
                )

                typer.echo(
                    (
                        "        candidates: "
                        "context="
                        f"{len(conclusion.context_provider_candidates)} "
                        "apex="
                        f"{len(conclusion.apex_provider_candidates)} "
                        "llndk="
                        f"{len(conclusion.llndk_provider_candidates)} "
                        "alias="
                        f"{len(conclusion.alias_provider_candidates)}"
                    )
                )


        typer.echo(
            (
                "  Effective linkerconfig topology / active APEX runtime "
                "population / executable routing / loading contexts: "
                "Runtime Linking"
            )
        )

        typer.echo(
            "  Linker/APEX canonical semantic reconciliation: complete"
        )

        typer.echo(
            "Kernel Universe coverage:"
        )
        typer.echo(
            (
                "  Parsing kernels: "
                f"{len(parsing.kernels)}"
            )
        )
        typer.echo(
            (
                "  Universe kernel requirements: "
                f"{len(kernel_cli_requirements)}"
            )
        )

        kernel_cli_identity_match = (
            len(kernel_cli_requirements)
            == len(parsing.kernels)
            and all(
                requirement.source is parsed
                for requirement, parsed
                in zip(
                    kernel_cli_requirements,
                    parsing.kernels,
                    strict=True,
                )
            )
        )

        typer.echo(
            (
                "  Parsing/Universe kernel identity match: "
                f"{kernel_cli_identity_match}"
            )
        )

        if not kernel_cli_requirements:
            typer.echo(
                "  Kernel entries: none"
            )

        for (
            kernel_cli_index,
            kernel_requirement,
        ) in enumerate(
            kernel_cli_requirements
        ):
            typer.echo(
                f"  Kernel [{kernel_cli_index}]:"
            )
            typer.echo(
                (
                    "    Kernel release: "
                    f"{kernel_requirement.kernel_release!r}"
                )
            )
            typer.echo(
                (
                    "    Linux banner present: "
                    f"{kernel_requirement.linux_banner is not None}"
                )
            )
            typer.echo(
                (
                    "    Kernel config requirements: "
                    f"{kernel_requirement.config_count}"
                )
            )
            typer.echo(
                (
                    "    Unparsed kernel config lines: "
                    f"{kernel_requirement.unparsed_config_count}"
                )
            )

        elf_requirements_with_filesystem_aliases = tuple(
            requirement
            for requirement
            in elf_cli_requirements
            if requirement.filesystem_aliases
        )

        elf_filesystem_aliases = tuple(
            alias
            for requirement
            in elf_cli_requirements
            for alias
            in requirement.filesystem_aliases
        )

        elf_filesystem_alias_view_witnesses = sum(
            len(
                alias.filesystem_views
            )
            for alias
            in elf_filesystem_aliases
        )

        typer.echo(
            "ELF Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed ELF objects: "
                f"{len(parsing.elf.elf_files)}"
            )
        )
        typer.echo(
            (
                "  Universe ELF requirements: "
                f"{len(elf_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  ELF requirements with filesystem aliases: "
                f"{len(elf_requirements_with_filesystem_aliases)}"
            )
        )
        typer.echo(
            (
                "  Canonical filesystem alias paths: "
                f"{len(elf_filesystem_aliases)}"
            )
        )
        typer.echo(
            (
                "  Filesystem alias view witnesses: "
                f"{elf_filesystem_alias_view_witnesses}"
            )
        )
        typer.echo(
            (
                "  Executables: "
                f"{elf_cli_role_counts.get('executable', 0)}"
            )
        )
        typer.echo(
            (
                "  Shared objects: "
                f"{elf_cli_role_counts.get('shared_object', 0)}"
            )
        )
        typer.echo(
            (
                "  Other ELF objects: "
                f"{elf_cli_role_counts.get('other', 0)}"
            )
        )
        typer.echo(
            (
                "  32-bit ELF objects: "
                f"{elf_cli_bitness_counts.get(32, 0)}"
            )
        )
        typer.echo(
            (
                "  64-bit ELF objects: "
                f"{elf_cli_bitness_counts.get(64, 0)}"
            )
        )
        typer.echo(
            (
                "  ELF objects with SONAME: "
                f"{len(elf_cli_sonames)}"
            )
        )
        typer.echo(
            (
                "  DT_NEEDED requirements: "
                f"{elf_cli_dependency_count}"
            )
        )
        typer.echo(
            (
                "  Interpreter requirements: "
                f"{elf_cli_interpreter_count}"
            )
        )
        typer.echo(
            (
                "  Soong build-tuple requirements: "
                f"{len(elf_cli_soong_build_tuple_requirements)}"
            )
        )

        elf_soong_literals = tuple(
            literal
            for parsed
            in parsing.elf.elf_files
            for literal
            in parsed.soong_intermediate_components
        )

        elf_soong_dispositions = tuple(
            disposition
            for requirement
            in elf_cli_requirements
            for disposition
            in requirement.soong_build_tuple_dispositions
        )

        elf_soong_build_tuples = sum(
            1
            for disposition
            in elf_soong_dispositions
            if disposition.status.value == "build_tuple"
        )

        elf_soong_non_build_tuples = sum(
            1
            for disposition
            in elf_soong_dispositions
            if disposition.status.value == "non_build_tuple"
        )

        elf_soong_unresolved = sum(
            1
            for disposition
            in elf_soong_dispositions
            if disposition.status.value == "unresolved"
        )

        typer.echo(
            (
                "  Parsing Soong intermediate component literals: "
                f"{len(elf_soong_literals)}"
            )
        )
        typer.echo(
            (
                "  Soong intermediate component dispositions: "
                f"{len(elf_soong_dispositions)}"
            )
        )
        typer.echo(
            (
                "    build_tuple: "
                f"{elf_soong_build_tuples}"
            )
        )
        typer.echo(
            (
                "    non_build_tuple: "
                f"{elf_soong_non_build_tuples}"
            )
        )
        typer.echo(
            (
                "    unresolved: "
                f"{elf_soong_unresolved}"
            )
        )

        if elf_soong_unresolved:
            typer.echo(
                "  Unresolved Soong intermediate component detail:"
            )

            for requirement in elf_cli_requirements:
                for disposition in (
                    requirement.soong_build_tuple_dispositions
                ):
                    if (
                        disposition.status.value
                        != "unresolved"
                    ):
                        continue

                    typer.echo(
                        (
                            "    ELF: "
                            f"{requirement.source.source.identity_key!r}"
                        )
                    )
                    typer.echo(
                        (
                            "      machine: "
                            f"{requirement.machine}"
                        )
                    )
                    typer.echo(
                        (
                            "      literal: "
                            f"{disposition.literal!r}"
                        )
                    )
                    typer.echo(
                        (
                            "      reason: "
                            f"{disposition.reason}"
                        )
                    )
        typer.echo(
            (
                "  Soong component/disposition match: "
                f"{len(elf_soong_literals) == len(elf_soong_dispositions)}"
            )
        )

        elf_filesystem_associations = sum(
            1
            for association
            in universe_result.elf_artifact_associations
            if association.kind.value == "filesystem_artifact"
        )

        elf_extraction_associations = sum(
            1
            for association
            in universe_result.elf_artifact_associations
            if association.kind.value == "extraction_artifact"
        )

        typer.echo(
            (
                "  ELF physical-artifact associations: "
                f"{len(universe_result.elf_artifact_associations)}"
            )
        )
        typer.echo(
            (
                "    filesystem_artifact: "
                f"{elf_filesystem_associations}"
            )
        )
        typer.echo(
            (
                "    extraction_artifact: "
                f"{elf_extraction_associations}"
            )
        )
        typer.echo(
            (
                "  ELF requirement/association match: "
                f"{len(universe_result.elf_artifact_associations) == len(elf_cli_requirements)}"
            )
        )
        typer.echo(
            (
                "  Distinct Soong domains: "
                f"{len(elf_cli_soong_domain_counts)}"
            )
        )

        for domain, count in sorted(
            elf_cli_soong_domain_counts.items(),
            key=lambda item: repr(
                item[0]
            ),
        ):
            display_domain = (
                "/".join(
                    domain
                )
                if domain
                else "<none>"
            )

            typer.echo(
                "    domain "
                f"{display_domain!r}: {count}"
            )

        typer.echo(
            (
                "  Distinct Soong architectures: "
                f"{len(elf_cli_soong_architecture_counts)}"
            )
        )

        for architecture, count in sorted(
            elf_cli_soong_architecture_counts.items()
        ):
            typer.echo(
                "    architecture "
                f"{architecture!r}: {count}"
            )

        typer.echo(
            (
                "  Distinct Soong arch variants: "
                f"{len(elf_cli_soong_arch_variant_counts)}"
            )
        )

        for arch_variant, count in sorted(
            elf_cli_soong_arch_variant_counts.items()
        ):
            typer.echo(
                "    arch variant "
                f"{arch_variant!r}: {count}"
            )

        typer.echo(
            (
                "  Parsing/Universe population match: "
                f"{len(parsing.elf.elf_files) == len(elf_cli_requirements)}"
            )
        )

        typer.echo(
            "Fstab Universe coverage:"
        )
        typer.echo(
            (
                "  Parsed fstab sources: "
                f"{len(parsing.filesystem.fstabs)}"
            )
        )
        typer.echo(
            (
                "  Parsed fstab declarations: "
                f"{parsed_fstab_declarations}"
            )
        )
        typer.echo(
            (
                "  Universe fstab requirements: "
                f"{len(fstab_requirements)}"
            )
        )
        typer.echo(
            (
                "  Fstab source contexts: "
                f"{len(fstab_source_contexts)}"
            )
        )
        typer.echo(
            (
                "  Contexts with unparsed lines: "
                f"{len(fstab_source_contexts_with_unparsed_lines)}"
            )
        )
        typer.echo(
            (
                "  Preserved unparsed lines: "
                f"{fstab_preserved_unparsed_line_count}"
            )
        )
        typer.echo(
            (
                "  Applicability observations: "
                f"{len(fstab_applicability)}"
            )
        )
        typer.echo(
            (
                "  Applicability observations with evidence: "
                f"{len(fstab_applicability_with_evidence)}"
            )
        )
        typer.echo(
            (
                "  Resolved applicability paths: "
                f"{len(fstab_applicability_resolved)}"
            )
        )
        typer.echo(
            (
                "  Selector-backed applicability observations: "
                f"{len(fstab_applicability_selector_backed)}"
            )
        )
        typer.echo(
            (
                "  Applicability observations without evidence: "
                f"{len(fstab_applicability_without_evidence)}"
            )
        )
        typer.echo(
            (
                "  Applicability conclusions: "
                f"{len(fstab_applicability_conclusions)}"
            )
        )

        for status, count in sorted(
            fstab_applicability_status_counts.items()
        ):
            typer.echo(
                f"    {status}: {count}"
            )
        typer.echo(
            (
                "  AVB requirements: "
                f"{avb_requirement_count}"
            )
        )
        typer.echo(
            (
                "  AVB hashtree-digest requirements: "
                f"{avb_hashtree_digest_requirement_count}"
            )
        )
        typer.echo(
            (
                "  Encryption-bearing requirements: "
                f"{encrypted_requirement_count}"
            )
        )
        typer.echo(
            (
                "  Zram requirements: "
                f"{zram_requirement_count}"
            )
        )

        for name, count in sorted(
            fstab_boolean_counts.items()
        ):
            typer.echo(
                f"  {name}: {count}"
            )

        if fstab_applicability_conclusions:
            typer.echo(
                "  Applicability conclusions by requirement:"
            )

            for conclusion in fstab_applicability_conclusions:
                typer.echo(
                    (
                        "    "
                        f"{conclusion.requirement_id}: "
                        f"{conclusion.status.value}"
                    )
                )

        if fstab_applicability_with_evidence:
            typer.echo(
                "  Applicability evidence:"
            )

            for item in fstab_applicability_with_evidence:
                typer.echo(
                    f"    {item.requirement_id}"
                )
                typer.echo(
                    (
                        "      expression: "
                        f"{item.referenced_path_expression!r}"
                    )
                )
                typer.echo(
                    (
                        "      resolved path: "
                        f"{item.resolved_path!r}"
                    )
                )

                if item.selector_key is not None:
                    typer.echo(
                        (
                            "      selector: "
                            f"{item.selector_key}="
                            f"{item.selector_value!r}"
                        )
                    )

                for evidence_item in item.evidence:
                    typer.echo(
                        (
                            "      evidence: "
                            f"{evidence_item.kind.value} "
                            f"{evidence_item.android_path}:"
                            f"{evidence_item.line_number} "
                            f"{evidence_item.raw_value!r}"
                        )
                    )

        typer.echo(
            (
                "  Unknown fs_mgr flag observations: "
                f"{sum(unknown_fstab_flag_counts.values())}"
            )
        )
        typer.echo(
            (
                "  Distinct unknown fs_mgr flags: "
                f"{len(unknown_fstab_flag_counts)}"
            )
        )

        if unknown_fstab_flag_counts:
            typer.echo(
                "  Unknown fs_mgr vocabulary:"
            )

            for flag, count in sorted(
                unknown_fstab_flag_counts.items()
            ):
                typer.echo(
                    f"    {flag}: {count}"
                )

        typer.echo()
        typer.echo(
            "Property fact coverage:"
        )

        if fact_counts:
            for fact, count in sorted(
                fact_counts.items()
            ):
                typer.echo(
                    f"  {fact}: {count}"
                )
        else:
            typer.echo(
                "  none"
            )

        typer.echo()
        typer.echo(
            "Property evidence by partition:"
        )

        if partition_counts:
            for partition, count in sorted(
                partition_counts.items(),
                key=lambda item: (
                    item[0] is None,
                    item[0] or "",
                ),
            ):
                partition_label = (
                    partition
                    if partition is not None
                    else "<unknown>"
                )

                typer.echo(
                    f"  {partition_label}: {count}"
                )
        else:
            typer.echo(
                "  none"
            )

        typer.echo()
        typer.echo(
            "Provenance examples:"
        )

        if not evidence:
            typer.echo(
                "  none"
            )
        else:
            for item in evidence[:10]:
                typer.echo(
                    (
                        f"  {item.fact.fact}={item.fact.value!r}"
                    )
                )
                typer.echo(
                    (
                        "    property: "
                        f"{item.fact.property_key}"
                    )
                )
                typer.echo(
                    (
                        "    partition: "
                        f"{item.model_source.partition_name}"
                    )
                )
                typer.echo(
                    (
                        "    android path: "
                        f"{item.model_source.android_path}"
                    )
                )
                typer.echo(
                    (
                        "    source line: "
                        f"{item.declaration.line_number}"
                    )
                )
                typer.echo(
                    (
                        "    host source: "
                        f"{item.parsed_source.source_path}"
                    )
                )
                typer.echo(
                    (
                        "    filesystem artifact: "
                        f"{item.extraction_artifact.path}"
                    )
                )
                typer.echo(
                    (
                        "    partition artifact: "
                        f"{item.partition.artifact.path}"
                    )
                )


    report_text = report_buffer.getvalue()
    return report_text
