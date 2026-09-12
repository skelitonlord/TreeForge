from __future__ import annotations

from pathlib import Path

from treeforge.android.runtime_linking.model import (
    AndroidRuntimeLinking,
)
from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)


def write_runtime_linking_report(
    *,
    runtime_linking_result: AndroidRuntimeLinking,
    universe_result: AndroidDeviceUniverse,
    runtime_linking_report_path: Path,
) -> None:
    """
    Write the canonical Runtime Linking report.

    This is the single report surface used whether Runtime Linking is
    invoked directly or as an upstream stage of Reconstruction.
    """

    if not isinstance(
        runtime_linking_result,
        AndroidRuntimeLinking,
    ):
        raise TypeError(
            "runtime_linking_result must be an AndroidRuntimeLinking"
        )

    if not isinstance(
        universe_result,
        AndroidDeviceUniverse,
    ):
        raise TypeError(
            "universe_result must be an AndroidDeviceUniverse"
        )

    if (
        runtime_linking_result.universe
        is not universe_result
    ):
        raise ValueError(
            "Runtime Linking report requires exact Universe identity"
        )

    if not isinstance(
        runtime_linking_report_path,
        Path,
    ):
        raise TypeError(
            "runtime_linking_report_path must be a Path"
        )

    runtime_linking_report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resolved_base_sections = tuple(
        item.resolved_section
        for item
        in runtime_linking_result.linker_resolved_base_sections
    )

    resolved_apex_sections = tuple(
        item.resolved_section
        for item
        in runtime_linking_result.linker_resolved_apex_sections
    )

    all_resolved_sections = (
        resolved_base_sections
        + resolved_apex_sections
    )

    all_requirement_resolutions = tuple(
        requirement
        for section
        in all_resolved_sections
        for requirement
        in section.requirement_resolutions
    )

    resolved_namespace_count = sum(
        len(
            section.namespaces
        )
        for section
        in all_resolved_sections
    )

    resolved_namespace_link_count = sum(
        len(
            namespace.links
        )
        for section
        in all_resolved_sections
        for namespace
        in section.namespaces
    )

    def section_status_count(
        sections,
        status: str,
    ) -> int:
        return sum(
            section.status.value == status
            for section
            in sections
        )

    def requirement_status_count(
        status: str,
    ) -> int:
        return sum(
            requirement.status.value == status
            for requirement
            in all_requirement_resolutions
        )

    def provider_kind_count(
        kind: str,
    ) -> int:
        return sum(
            (
                requirement.provider_kind is not None
                and requirement.provider_kind.value == kind
            )
            for requirement
            in all_requirement_resolutions
        )

    def standard_system_link_stats(
        sections,
    ) -> dict[str, int]:
        stats = {
            "sections": len(sections),
            "changed_sections": 0,
            "unchanged_sections": 0,
            "links_created": 0,
            "links_augmented": 0,
            "bionic_library_additions": 0,
            "sanitizer_library_additions": 0,
            "libfdtrack_additions": 0,
        }

        bionic_libraries = {
            "libc.so",
            "libdl.so",
            "libdl_android.so",
            "libm.so",
        }

        for result in sections:
            source_section = (
                result.source_section
            )

            linked_section = (
                result.linked_section
            )

            section_changed = False

            source_namespaces = {
                namespace.namespace.name: namespace
                for namespace
                in source_section.namespaces
            }

            linked_namespaces = {
                namespace.namespace.name: namespace
                for namespace
                in linked_section.namespaces
            }

            if (
                source_namespaces.keys()
                != linked_namespaces.keys()
            ):
                raise RuntimeError(
                    "AddStandardSystemLinks report requires "
                    "identical source/final namespace coverage"
                )

            sanitizer_libraries = set(
                result.sanitizer_runtime_libraries
            )

            for namespace_name in (
                source_namespaces
            ):
                source_namespace = (
                    source_namespaces[
                        namespace_name
                    ]
                )

                linked_namespace = (
                    linked_namespaces[
                        namespace_name
                    ]
                )

                source_links = {
                    link.target_namespace: link
                    for link
                    in source_namespace.links
                }

                linked_links = {
                    link.target_namespace: link
                    for link
                    in linked_namespace.links
                }

                for target_name, linked_link in (
                    linked_links.items()
                ):
                    source_link = (
                        source_links.get(
                            target_name
                        )
                    )

                    if source_link is None:
                        stats[
                            "links_created"
                        ] += 1
                        section_changed = True

                        added_libraries = set(
                            linked_link.shared_libraries
                        )

                    else:
                        if (
                            linked_link
                            == source_link
                        ):
                            continue

                        stats[
                            "links_augmented"
                        ] += 1
                        section_changed = True

                        added_libraries = (
                            set(
                                linked_link.shared_libraries
                            )
                            - set(
                                source_link.shared_libraries
                            )
                        )

                    stats[
                        "bionic_library_additions"
                    ] += len(
                        added_libraries
                        & bionic_libraries
                    )

                    stats[
                        "sanitizer_library_additions"
                    ] += len(
                        added_libraries
                        & sanitizer_libraries
                    )

                    if (
                        "libfdtrack.so"
                        in added_libraries
                    ):
                        stats[
                            "libfdtrack_additions"
                        ] += 1

            if section_changed:
                stats[
                    "changed_sections"
                ] += 1
            else:
                stats[
                    "unchanged_sections"
                ] += 1

        return stats


    standard_base_stats = (
        standard_system_link_stats(
            runtime_linking_result
            .linker_standard_system_linked_base_sections
        )
    )

    standard_apex_stats = (
        standard_system_link_stats(
            runtime_linking_result
            .linker_standard_system_linked_apex_sections
        )
    )

    standard_all_stats = {
        key: (
            standard_base_stats[
                key
            ]
            + standard_apex_stats[
                key
            ]
        )
        for key
        in standard_base_stats
    }

    namespace_accessibility_sections = (
        runtime_linking_result
        .linker_namespace_accessibility_base_sections
        + runtime_linking_result
        .linker_namespace_accessibility_apex_sections
    )

    namespace_accessibility_namespaces = tuple(
        namespace
        for section
        in namespace_accessibility_sections
        for namespace
        in section.namespaces
    )

    namespace_accessibility_links = tuple(
        link
        for namespace
        in namespace_accessibility_namespaces
        for link
        in namespace.links
    )

    namespace_accessibility_allow_all_links = sum(
        1
        for link
        in namespace_accessibility_links
        if link.allow_all_shared_libs
    )

    namespace_accessibility_restricted_links = (
        len(
            namespace_accessibility_links
        )
        - namespace_accessibility_allow_all_links
    )

    namespace_accessibility_explicit_soname_grants = sum(
        len(
            link.shared_libraries
        )
        for link
        in namespace_accessibility_links
        if not link.allow_all_shared_libs
    )

    elf_runtime_candidates = (
        runtime_linking_result.linker_elf_runtime_candidates
    )

    elf_runtime_candidate_active = sum(
        1
        for candidate
        in elf_runtime_candidates
        if candidate.status.value == "active"
    )

    elf_runtime_candidate_inapplicable = sum(
        1
        for candidate
        in elf_runtime_candidates
        if candidate.status.value == "inapplicable"
    )

    elf_runtime_candidate_ambiguous = sum(
        1
        for candidate
        in elf_runtime_candidates
        if candidate.status.value == "ambiguous"
    )

    elf_runtime_candidate_unresolved = sum(
        1
        for candidate
        in elf_runtime_candidates
        if candidate.status.value == "unresolved"
    )

    elf_runtime_candidate_base_active = sum(
        1
        for candidate
        in elf_runtime_candidates
        if (
            candidate.status.value == "active"
            and candidate.active_apex_runtime_path is None
        )
    )

    elf_runtime_candidate_apex_active = sum(
        1
        for candidate
        in elf_runtime_candidates
        if (
            candidate.status.value == "active"
            and candidate.active_apex_runtime_path is not None
        )
    )

    elf_runtime_candidate_alias_paths = sum(
        len(
            candidate.runtime_alias_paths
        )
        for candidate
        in elf_runtime_candidates
    )

    elf_runtime_candidate_soname = sum(
        1
        for candidate
        in elf_runtime_candidates
        if candidate.soname is not None
    )

    #
    # Preserve the complete inapplicable-candidate reason population in the
    # human-readable report. Runtime Linking already carries these reasons on
    # the canonical result objects; reporting must not collapse them to only
    # an aggregate count.
    #
    elf_runtime_candidate_inapplicable_reason_counts = {}
    elf_runtime_candidate_inapplicable_reason_examples = {}

    for candidate in (
        elf_runtime_candidates
    ):
        if (
            candidate.status.value
            != "inapplicable"
        ):
            continue

        reason = (
            candidate.reason
            or "<missing inapplicable candidate reason>"
        )

        elf_runtime_candidate_inapplicable_reason_counts[
            reason
        ] = (
            elf_runtime_candidate_inapplicable_reason_counts
            .get(
                reason,
                0,
            )
            + 1
        )

        identity = (
            str(
                candidate.runtime_path
            )
            if candidate.runtime_path
            is not None
            else (
                str(
                    candidate.physical_android_path
                )
                if (
                    candidate.physical_android_path
                    is not None
                )
                else (
                    candidate
                    .linker_elf_context
                    .context_id
                )
            )
        )

        configuration_scope = getattr(
            (
                candidate
                .linker_elf_context
                .configuration_scope
            ),
            "value",
            str(
                candidate
                .linker_elf_context
                .configuration_scope
            ),
        )

        runtime_kind = getattr(
            (
                candidate
                .linker_elf_context
                .runtime_context
                .kind
            ),
            "value",
            str(
                candidate
                .linker_elf_context
                .runtime_context
                .kind
            ),
        )

        elf_runtime_candidate_inapplicable_reason_examples.setdefault(
            reason,
            [],
        ).append(
            (
                f"{identity} "
                f"[scope={configuration_scope} "
                f"runtime={runtime_kind}]"
            )
        )

    elf_runtime_candidate_inapplicable_reason_lines = []

    for reason in sorted(
        elf_runtime_candidate_inapplicable_reason_counts,
        key=lambda value: (
            -elf_runtime_candidate_inapplicable_reason_counts[
                value
            ],
            value,
        ),
    ):
        count = (
            elf_runtime_candidate_inapplicable_reason_counts[
                reason
            ]
        )

        elf_runtime_candidate_inapplicable_reason_lines.append(
            f"    {count}: {reason}"
        )

        for example in (
            elf_runtime_candidate_inapplicable_reason_examples[
                reason
            ][:5]
        ):
            elf_runtime_candidate_inapplicable_reason_lines.append(
                f"      example: {example}"
            )

    elf_dependency_traversals = (
        runtime_linking_result
        .linker_elf_dependency_traversals
    )

    elf_dependency_traversal_resolved = sum(
        traversal.status.value == "resolved"
        for traversal
        in elf_dependency_traversals
    )

    elf_dependency_traversal_inapplicable = sum(
        traversal.status.value == "inapplicable"
        for traversal
        in elf_dependency_traversals
    )

    elf_dependency_traversal_ambiguous = sum(
        traversal.status.value == "ambiguous"
        for traversal
        in elf_dependency_traversals
    )

    elf_dependency_traversal_unresolved = sum(
        traversal.status.value == "unresolved"
        for traversal
        in elf_dependency_traversals
    )

    #
    # Every non-resolved traversal already has a mandatory reason in the
    # Runtime Linking model. Surface every distinct INAPPLICABLE reason and
    # representative identities instead of hiding 3,000+ conclusions behind
    # one number.
    #
    elf_dependency_traversal_inapplicable_reason_counts = {}
    elf_dependency_traversal_inapplicable_reason_examples = {}

    for traversal in (
        elf_dependency_traversals
    ):
        if (
            traversal.status.value
            != "inapplicable"
        ):
            continue

        reason = (
            traversal.reason
            or "<missing inapplicable traversal reason>"
        )

        elf_dependency_traversal_inapplicable_reason_counts[
            reason
        ] = (
            elf_dependency_traversal_inapplicable_reason_counts
            .get(
                reason,
                0,
            )
            + 1
        )

        root_candidate = (
            traversal.root_candidate
        )

        if root_candidate is not None:
            identity = (
                str(
                    root_candidate.runtime_path
                )
                if root_candidate.runtime_path
                is not None
                else (
                    str(
                        root_candidate
                        .physical_android_path
                    )
                    if (
                        root_candidate
                        .physical_android_path
                        is not None
                    )
                    else (
                        traversal
                        .loading_context
                        .loading_context_id
                    )
                )
            )
        else:
            identity = (
                traversal
                .loading_context
                .loading_context_id
            )

        elf_context = (
            traversal
            .loading_context
            .routing
            .elf_context
        )

        configuration_scope = getattr(
            elf_context.configuration_scope,
            "value",
            str(
                elf_context.configuration_scope
            ),
        )

        runtime_kind = getattr(
            elf_context.runtime_context.kind,
            "value",
            str(
                elf_context.runtime_context.kind
            ),
        )

        root_status = (
            root_candidate.status.value
            if root_candidate is not None
            else "none"
        )

        elf_dependency_traversal_inapplicable_reason_examples.setdefault(
            reason,
            [],
        ).append(
            (
                f"{identity} "
                f"[scope={configuration_scope} "
                f"runtime={runtime_kind} "
                f"root_candidate={root_status}]"
            )
        )

    elf_dependency_traversal_inapplicable_reason_lines = []

    for reason in sorted(
        elf_dependency_traversal_inapplicable_reason_counts,
        key=lambda value: (
            -elf_dependency_traversal_inapplicable_reason_counts[
                value
            ],
            value,
        ),
    ):
        count = (
            elf_dependency_traversal_inapplicable_reason_counts[
                reason
            ]
        )

        elf_dependency_traversal_inapplicable_reason_lines.append(
            f"    {count}: {reason}"
        )

        for example in (
            elf_dependency_traversal_inapplicable_reason_examples[
                reason
            ][:5]
        ):
            elf_dependency_traversal_inapplicable_reason_lines.append(
                f"      example: {example}"
            )

    elf_dependency_visited_states = sum(
        traversal.visited_elf_namespace_states
        for traversal
        in elf_dependency_traversals
    )

    elf_dependency_resolutions = tuple(
        resolution
        for traversal
        in elf_dependency_traversals
        for resolution
        in traversal.dependency_resolutions
    )

    elf_dependency_resolution_resolved = sum(
        resolution.status.value == "resolved"
        for resolution
        in elf_dependency_resolutions
    )

    elf_dependency_resolution_ambiguous = sum(
        resolution.status.value == "ambiguous"
        for resolution
        in elf_dependency_resolutions
    )

    elf_dependency_resolution_unresolved = sum(
        resolution.status.value == "unresolved"
        for resolution
        in elf_dependency_resolutions
    )

    elf_dependency_physical_matches = sum(
        (
            resolution.provider_path_kind is not None
            and resolution.provider_path_kind.value
            == "physical"
        )
        for resolution
        in elf_dependency_resolutions
    )

    elf_dependency_alias_matches = sum(
        (
            resolution.provider_path_kind is not None
            and resolution.provider_path_kind.value
            == "filesystem_alias"
        )
        for resolution
        in elf_dependency_resolutions
    )

    elf_dependency_ambiguous_examples = tuple(
        resolution
        for resolution
        in elf_dependency_resolutions
        if resolution.status.value == "ambiguous"
    )[:20]

    elf_dependency_unresolved_examples = tuple(
        resolution
        for resolution
        in elf_dependency_resolutions
        if resolution.status.value == "unresolved"
    )[:40]

    elf_dependency_provider_namespaces = {
        resolution.provider_namespace_name
        for resolution
        in elf_dependency_resolutions
        if resolution.provider_namespace_name
        is not None
    }

    elf_dependency_roots_with_resolutions = sum(
        bool(
            traversal.dependency_resolutions
        )
        for traversal
        in elf_dependency_traversals
    )

    runtime_linking_report_lines = [
        "TreeForge Android Runtime Linking Report",
        "=======================================",
        "",
        "Pipeline boundary:",
        (
            "  Parsing -> Android Device Universe -> "
            "Runtime Linking"
        ),
        "",
        "Canonical input identity:",
        "  Android Device Universe: preserved",
        (
            "  Exact Universe identity: "
            f"{runtime_linking_result.universe is universe_result}"
        ),
        "",
        "Runtime Linking coverage:",
        (
            "  Generated configuration inputs: "
            f"{len(runtime_linking_result.linker_generated_configuration_inputs)}"
        ),
        (
            "  Generated BASE configurations: "
            f"{len(runtime_linking_result.linker_generated_base_configurations)}"
        ),
        (
            "  Effective pre-Resolve BASE configurations: "
            f"{len(runtime_linking_result.linker_effective_base_configurations)}"
        ),
        (
            "  Effective pre-Resolve APEX configurations: "
            f"{len(runtime_linking_result.linker_effective_apex_configurations)}"
        ),
        "",
        "Section::Resolve coverage:",
        (
            "  BASE sections: "
            f"{len(resolved_base_sections)}"
        ),
        (
            "    resolved: "
            f"{section_status_count(resolved_base_sections, 'resolved')}"
        ),
        (
            "    ambiguous: "
            f"{section_status_count(resolved_base_sections, 'ambiguous')}"
        ),
        (
            "    unresolved: "
            f"{section_status_count(resolved_base_sections, 'unresolved')}"
        ),
        (
            "  APEX sections: "
            f"{len(resolved_apex_sections)}"
        ),
        (
            "    resolved: "
            f"{section_status_count(resolved_apex_sections, 'resolved')}"
        ),
        (
            "    ambiguous: "
            f"{section_status_count(resolved_apex_sections, 'ambiguous')}"
        ),
        (
            "    unresolved: "
            f"{section_status_count(resolved_apex_sections, 'unresolved')}"
        ),
        (
            "  Requirement resolutions: "
            f"{len(all_requirement_resolutions)}"
        ),
        (
            "    resolved: "
            f"{requirement_status_count('resolved')}"
        ),
        (
            "    tolerated missing: "
            f"{requirement_status_count('tolerated_missing')}"
        ),
        (
            "    ambiguous: "
            f"{requirement_status_count('ambiguous')}"
        ),
        (
            "    unresolved: "
            f"{requirement_status_count('unresolved')}"
        ),
        (
            "  Resolved provider kinds:"
        ),
        (
            "    concrete namespace: "
            f"{provider_kind_count('concrete_namespace')}"
        ),
        (
            "    APEX: "
            f"{provider_kind_count('apex')}"
        ),
        (
            "    alias: "
            f"{provider_kind_count('alias')}"
        ),
        (
            "  Final namespaces after dynamic injection: "
            f"{resolved_namespace_count}"
        ),
        (
            "  Final namespace links: "
            f"{resolved_namespace_link_count}"
        ),
        "",
        "AddStandardSystemLinks coverage:",
        (
            "  BASE sections: "
            f"{standard_base_stats['sections']}"
        ),
        (
            "  APEX sections: "
            f"{standard_apex_stats['sections']}"
        ),
        (
            "  Changed sections: "
            f"{standard_all_stats['changed_sections']}"
        ),
        (
            "  Unchanged sections: "
            f"{standard_all_stats['unchanged_sections']}"
        ),
        (
            "  System links created: "
            f"{standard_all_stats['links_created']}"
        ),
        (
            "  Existing system links augmented: "
            f"{standard_all_stats['links_augmented']}"
        ),
        (
            "  Bionic library additions: "
            f"{standard_all_stats['bionic_library_additions']}"
        ),
        (
            "  Sanitizer runtime library additions: "
            f"{standard_all_stats['sanitizer_library_additions']}"
        ),
        (
            "  libfdtrack.so additions: "
            f"{standard_all_stats['libfdtrack_additions']}"
        ),
        "",
        "Namespace accessibility coverage:",
        (
            "  BASE sections: "
            f"{len(runtime_linking_result.linker_namespace_accessibility_base_sections)}"
        ),
        (
            "  APEX sections: "
            f"{len(runtime_linking_result.linker_namespace_accessibility_apex_sections)}"
        ),
        (
            "  Namespaces: "
            f"{len(namespace_accessibility_namespaces)}"
        ),
        (
            "  Direct namespace links: "
            f"{len(namespace_accessibility_links)}"
        ),
        (
            "  Restricted links: "
            f"{namespace_accessibility_restricted_links}"
        ),
        (
            "  Allow-all links: "
            f"{namespace_accessibility_allow_all_links}"
        ),
        (
            "  Explicit SONAME grants: "
            f"{namespace_accessibility_explicit_soname_grants}"
        ),
        "",
        "ELF runtime candidate coverage:",
        (
            "  Candidate conclusions: "
            f"{len(elf_runtime_candidates)}"
        ),
        (
            "  Active: "
            f"{elf_runtime_candidate_active}"
        ),
        (
            "    BASE: "
            f"{elf_runtime_candidate_base_active}"
        ),
        (
            "    APEX: "
            f"{elf_runtime_candidate_apex_active}"
        ),
        (
            "  Inapplicable: "
            f"{elf_runtime_candidate_inapplicable}"
        ),
        (
            "  Ambiguous: "
            f"{elf_runtime_candidate_ambiguous}"
        ),
        (
            "  Unresolved: "
            f"{elf_runtime_candidate_unresolved}"
        ),
        (
            "  Runtime filesystem alias paths: "
            f"{elf_runtime_candidate_alias_paths}"
        ),
        (
            "  Candidates carrying DT_SONAME: "
            f"{elf_runtime_candidate_soname}"
        ),
        "  Inapplicable candidate reason coverage:",
        (
            "    reason-bearing conclusions: "
            f"{sum(elf_runtime_candidate_inapplicable_reason_counts.values())}"
            f"/{elf_runtime_candidate_inapplicable}"
        ),
        *(
            elf_runtime_candidate_inapplicable_reason_lines
        ),
        "",
        "Contextual ELF DT_NEEDED coverage:",
        (
            "  Loading-context traversals: "
            f"{len(elf_dependency_traversals)}"
        ),
        (
            "    resolved: "
            f"{elf_dependency_traversal_resolved}"
        ),
        (
            "    inapplicable: "
            f"{elf_dependency_traversal_inapplicable}"
        ),
        (
            "    ambiguous: "
            f"{elf_dependency_traversal_ambiguous}"
        ),
        (
            "    unresolved: "
            f"{elf_dependency_traversal_unresolved}"
        ),
        "  Inapplicable traversal reason coverage:",
        (
            "    reason-bearing conclusions: "
            f"{sum(elf_dependency_traversal_inapplicable_reason_counts.values())}"
            f"/{elf_dependency_traversal_inapplicable}"
        ),
        *(
            elf_dependency_traversal_inapplicable_reason_lines
        ),
        (
            "  Roots with contextual dependency resolutions: "
            f"{elf_dependency_roots_with_resolutions}"
        ),
        (
            "  Visited ELF/namespace states: "
            f"{elf_dependency_visited_states}"
        ),
        (
            "  DT_NEEDED resolutions: "
            f"{len(elf_dependency_resolutions)}"
        ),
        (
            "    resolved: "
            f"{elf_dependency_resolution_resolved}"
        ),
        (
            "    ambiguous: "
            f"{elf_dependency_resolution_ambiguous}"
        ),
        (
            "    unresolved: "
            f"{elf_dependency_resolution_unresolved}"
        ),
        "  Resolved provider path kinds:",
        (
            "    physical: "
            f"{elf_dependency_physical_matches}"
        ),
        (
            "    filesystem alias: "
            f"{elf_dependency_alias_matches}"
        ),
        (
            "  Distinct resolved provider namespaces: "
            f"{len(elf_dependency_provider_namespaces)}"
        ),
        "",
        "Contextual ELF DT_NEEDED ambiguity examples:",
        *(
            (
                "  "
                f"{resolution.parent_candidate.runtime_path} "
                f"[{resolution.starting_namespace_name}] -> "
                f"{resolution.dependency.name}: "
                f"{resolution.reason}"
            )
            for resolution
            in elf_dependency_ambiguous_examples
        ),
        "",
        "Contextual ELF DT_NEEDED unresolved examples:",
        *(
            (
                "  "
                f"{resolution.parent_candidate.runtime_path} "
                f"[{resolution.starting_namespace_name}] -> "
                f"{resolution.dependency.name}: "
                f"{resolution.reason}"
            )
            for resolution
            in elf_dependency_unresolved_examples
        ),
        "",
        "Section::Resolve unresolved detail:",
        *(
            (
                "  "
                f"{section.section_name}: "
                f"{section.status.value}"
            )
            for section
            in all_resolved_sections
            if section.status.value != "resolved"
        ),
        *(
            (
                "    "
                f"{requirement.source_namespace.name}: "
                f"{requirement.library_name}: "
                f"{requirement.status.value}: "
                f"{requirement.reason}"
            )
            for section
            in all_resolved_sections
            for requirement
            in section.requirement_resolutions
            if requirement.status.value
            in {
                "ambiguous",
                "unresolved",
            }
        ),
        *(
            (
                "    section reason: "
                f"{reason}"
            )
            for section
            in all_resolved_sections
            for reason
            in section.reasons
            if (
                reason.startswith("namespace ")
                and "undefined variable" in reason
            )
        ),
        "",
        (
            "  Active APEX runtime paths: "
            f"{len(runtime_linking_result.linker_apex_active_runtime_paths)}"
        ),
        (
            "  APEX provider descriptors: "
            f"{len(runtime_linking_result.linker_apex_provider_descriptors)}"
        ),
        (
            "  Section/APEX applicability conclusions: "
            f"{len(runtime_linking_result.linker_section_apex_applicability)}"
        ),
        (
            "  Executable section routing conclusions: "
            f"{len(runtime_linking_result.linker_executable_section_routing)}"
        ),
        (
            "  Executable loading contexts: "
            f"{len(runtime_linking_result.linker_executable_loading_contexts)}"
        ),
        "",
        "Ownership:",
        (
            "  Generated linkerconfig implementation: Runtime Linking"
        ),
        (
            "  Runtime-derived execution/result: Runtime Linking"
        ),
        (
            "  Inapplicable candidate/traversal dispositions and reasons: "
            "preserved on Runtime Linking result objects"
        ),
        (
            "  Canonical Linker/APEX/ELF semantic inputs: "
            "Android Device Universe"
        ),
        "",
    ]

    runtime_linking_report_path.write_text(
        "\n".join(
            runtime_linking_report_lines
        ),
        encoding="utf-8",
    )
