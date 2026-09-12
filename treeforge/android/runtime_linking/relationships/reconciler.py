"""
Effective Android runtime-linker reconciliation.

This module owns runtime-derived Linker/APEX/ELF behavior downstream of
Android Device Universe. It consumes canonical Universe identities and does
not mutate or recreate them.
"""

from __future__ import annotations

from treeforge.android.runtime_linking.linker.section_semantics import (
    AndroidRuntimeLinkerSectionSemantics,
)

from treeforge.android.runtime_linking.linker.apex_identity import (
    AndroidRuntimeLinkerApexIdentity,
)

from treeforge.android.runtime_linking.linker.apex_deployment import (
    AndroidRuntimeLinkerApexDeploymentSemantics,
)


from treeforge.android.universe.apex.requirement import AndroidUniverseApexRequirement
from treeforge.android.universe.elf.requirement import AndroidUniverseElfRole
from treeforge.android.universe.relationships.model import AndroidUniverseLinkerApexNamespaceInput
from treeforge.android.universe.relationships.model import AndroidUniverseLinkerApexNamespaceStatus
from treeforge.android.universe.relationships.model import AndroidUniverseLinkerApexPublicLibraryStatus
from treeforge.android.universe.relationships.model import AndroidUniverseLinkerElfConfigurationScope
from treeforge.android.universe.relationships.model import AndroidUniverseRelationshipStatus

from pathlib import PurePosixPath

from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexActiveRuntimePath,
    AndroidUniverseLinkerApexProviderDescriptor,
    AndroidUniverseLinkerApexProviderStatus,
    AndroidUniverseLinkerExecutableLoadingContext,
    AndroidUniverseLinkerExecutableLoadingContextStatus,
    AndroidUniverseLinkerExecutableSectionRouting,
    AndroidUniverseLinkerExecutableSectionRoutingStatus,
    AndroidUniverseLinkerSectionApexApplicability,
    AndroidUniverseLinkerSectionApexApplicabilityReason,
    AndroidUniverseLinkerSectionApexApplicabilityStatus,
)


class AndroidRuntimeLinkingReconciler:
    """Reconcile effective Android runtime-linker behavior."""

    @staticmethod
    def reconcile_linker_apex_active_runtime_paths(
        *,
        apex_requirements,
    ) -> tuple[
        AndroidUniverseLinkerApexActiveRuntimePath,
        ...,
    ]:
        """
        Resolve canonical active client-visible APEX runtime roots.

        The canonical runtime root is ``/apex/<manifest-name>`` only when one
        exact APEX requirement owns that manifest name in the same canonical
        runtime context.

        Same-name requirements in different Android runtimes do not compete.
        Same-name requirements in one runtime remain ambiguous rather than
        inventing activation/version precedence.
        """

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        results = []

        for requirement in apex_requirements:
            apex_name = (
                requirement.apex_name
            )

            if not apex_name:
                results.append(
                    AndroidUniverseLinkerApexActiveRuntimePath(
                        apex_requirement=requirement,
                        runtime_context=(
                            requirement.runtime_context
                        ),
                        activation_candidates=(),
                        active_root=None,
                        executable_directory=None,
                        status=(
                            AndroidUniverseRelationshipStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "canonical APEX manifest name is absent"
                        ),
                    )
                )
                continue

            candidates = tuple(
                sorted(
                    (
                        candidate
                        for candidate
                        in apex_requirements
                        if (
                            candidate.shares_manifest_name(requirement)
                            and candidate.shares_runtime(
                                requirement.runtime_context
                            )
                        )
                    ),
                    key=lambda candidate: (
                        candidate.requirement_id
                    ),
                )
            )

            if len(
                candidates
            ) == 1:
                active_root = (
                    PurePosixPath(
                        "/apex"
                    )
                    / apex_name
                )

                status = (
                    AndroidUniverseRelationshipStatus
                    .RESOLVED
                )

                executable_directory = (
                    active_root
                    / "bin"
                )

                unresolved_reason = None

            elif len(
                candidates
            ) > 1:
                active_root = None
                executable_directory = None

                status = (
                    AndroidUniverseRelationshipStatus
                    .AMBIGUOUS
                )

                unresolved_reason = None

            else:
                active_root = None
                executable_directory = None

                status = (
                    AndroidUniverseRelationshipStatus
                    .UNRESOLVED
                )

                unresolved_reason = (
                    "canonical APEX activation candidate set is empty"
                )

            results.append(
                AndroidUniverseLinkerApexActiveRuntimePath(
                    apex_requirement=requirement,
                    runtime_context=(
                        requirement.runtime_context
                    ),
                    activation_candidates=candidates,
                    active_root=active_root,
                    executable_directory=(
                        executable_directory
                    ),
                    status=status,
                    unresolved_reason=(
                        unresolved_reason
                    ),
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.runtime_path_id
                ),
            )
        )


    @staticmethod
    def reconcile_linker_executable_section_routing(
        *,
        elf_contexts,
        generated_base_configurations,
        apex_active_runtime_paths,
        unsupported_elf_bitnesses=frozenset(),
    ) -> tuple[
        AndroidUniverseLinkerExecutableSectionRouting,
        ...,
    ]:
        """
        Apply Android's ordered executable-directory routing semantics.

        The first matching resolved BASE directory route wins.

        An unresolved earlier route prevents selection of a later matching
        route because Android first-match semantics could be shadowed by the
        unresolved route.

        APEX executable routing consumes exact canonical active APEX
        runtime-path conclusions and maps payload-relative executable paths
        into their active client-visible runtime paths.
        """

        if not isinstance(
            unsupported_elf_bitnesses,
            frozenset,
        ):
            raise TypeError(
                "unsupported_elf_bitnesses must be a frozenset"
            )

        if not all(
            isinstance(
                bitness,
                int,
            )
            and bitness > 0
            for bitness
            in unsupported_elf_bitnesses
        ):
            raise ValueError(
                "unsupported_elf_bitnesses must contain only "
                "positive integer bitness values"
            )

        if not isinstance(
            elf_contexts,
            tuple,
        ):
            raise TypeError(
                "elf_contexts must be a tuple"
            )

        if not isinstance(
            generated_base_configurations,
            tuple,
        ):
            raise TypeError(
                "generated_base_configurations must be a tuple"
            )

        if not isinstance(
            apex_active_runtime_paths,
            tuple,
        ):
            raise TypeError(
                "apex_active_runtime_paths must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerApexActiveRuntimePath,
            )
            for item
            in apex_active_runtime_paths
        ):
            raise TypeError(
                "apex_active_runtime_paths must contain only "
                "AndroidUniverseLinkerApexActiveRuntimePath instances"
            )

        results = []

        for context in elf_contexts:
            requirement = (
                context.elf_requirement
            )

            if (
                requirement.role
                is not AndroidUniverseElfRole.EXECUTABLE
            ):
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .INAPPLICABLE
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                requirement.role
                is AndroidUniverseElfRole.EXECUTABLE
                and requirement.bitness
                in unsupported_elf_bitnesses
            ):
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .INAPPLICABLE
                        ),
                        apex_runtime_path=None,
                        apex_section_name=None,
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                context.status
                is AndroidUniverseRelationshipStatus.AMBIGUOUS
            ):
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .AMBIGUOUS
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                context.status
                is AndroidUniverseRelationshipStatus.UNRESOLVED
            ):
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "canonical Linker/ELF runtime context is unresolved"
                        ),
                    )
                )
                continue

            if (
                context.configuration_scope
                is AndroidUniverseLinkerElfConfigurationScope.APEX
            ):
                selected_apex = (
                    context.selected_apex_requirement
                )

                if selected_apex is None:
                    raise ValueError(
                        "resolved APEX Linker/ELF context must preserve "
                        "one exact selected APEX requirement"
                    )

                active_path_candidates = tuple(
                    item
                    for item
                    in apex_active_runtime_paths
                    if (
                        item.apex_requirement
                        is selected_apex
                    )
                )

                if not active_path_candidates:
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=None,
                            android_path=None,
                            route_candidates=(),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .UNRESOLVED
                            ),
                            apex_runtime_path=None,
                            apex_section_name=None,
                            unresolved_reason=(
                                "no canonical active APEX runtime-path "
                                "conclusion preserves the selected APEX "
                                "requirement identity"
                            ),
                        )
                    )
                    continue

                if len(
                    active_path_candidates
                ) > 1:
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=None,
                            android_path=None,
                            route_candidates=(),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .AMBIGUOUS
                            ),
                            apex_runtime_path=None,
                            apex_section_name=None,
                            unresolved_reason=None,
                        )
                    )
                    continue

                active_path = (
                    active_path_candidates[
                        0
                    ]
                )

                if (
                    active_path.status
                    is AndroidUniverseRelationshipStatus.AMBIGUOUS
                ):
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=None,
                            android_path=None,
                            route_candidates=(),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .AMBIGUOUS
                            ),
                            apex_runtime_path=active_path,
                            apex_section_name=None,
                            unresolved_reason=None,
                        )
                    )
                    continue

                if (
                    active_path.status
                    is AndroidUniverseRelationshipStatus.UNRESOLVED
                ):
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=None,
                            android_path=None,
                            route_candidates=(),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .UNRESOLVED
                            ),
                            apex_runtime_path=active_path,
                            apex_section_name=None,
                            unresolved_reason=(
                                active_path.unresolved_reason
                                or (
                                    "canonical active APEX runtime path "
                                    "is unresolved"
                                )
                            ),
                        )
                    )
                    continue

                active_root = (
                    active_path.active_root
                )
                executable_directory = (
                    active_path.executable_directory
                )

                if (
                    active_root is None
                    or executable_directory is None
                ):
                    raise ValueError(
                        "resolved active APEX runtime path must expose "
                        "active root and executable directory"
                    )

                payload_path = (
                    requirement.android_path
                )

                if payload_path is None:
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=None,
                            android_path=None,
                            route_candidates=(),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .UNRESOLVED
                            ),
                            apex_runtime_path=active_path,
                            apex_section_name=None,
                            unresolved_reason=(
                                "canonical APEX executable has no "
                                "payload-relative Android path"
                            ),
                        )
                    )
                    continue

                runtime_path = (
                    active_root
                    / payload_path.as_posix().lstrip(
                        "/"
                    )
                )

                if (
                    executable_directory
                    not in runtime_path.parents
                ):
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=None,
                            android_path=runtime_path,
                            route_candidates=(),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .UNRESOLVED
                            ),
                            apex_runtime_path=active_path,
                            apex_section_name=None,
                            unresolved_reason=(
                                "canonical APEX executable does not belong "
                                "to the active APEX executable directory"
                            ),
                        )
                    )
                    continue

                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=runtime_path,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .RESOLVED
                        ),
                        apex_runtime_path=active_path,
                        apex_section_name=(
                            AndroidRuntimeLinkerApexIdentity
                            .section_name(
                                selected_apex
                            )
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                requirement.android_path is None
                and not requirement.is_filesystem_backed
            ):
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .INAPPLICABLE
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            runtime_policy = (
                context.runtime_policy
            )

            if runtime_policy is None:
                raise ValueError(
                    "resolved BASE Linker/ELF context must expose one "
                    "canonical runtime policy"
                )

            base_candidates = tuple(
                base
                for base
                in generated_base_configurations
                if (
                    base.inputs.runtime_policy
                    is runtime_policy
                )
            )

            if not base_candidates:
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "no canonical generated BASE configuration "
                            "matches the executable runtime policy"
                        ),
                    )
                )
                continue

            if len(
                base_candidates
            ) > 1:
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=None,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .AMBIGUOUS
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            base = base_candidates[
                0
            ]

            android_path = (
                requirement.android_path
            )

            if android_path is None:
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=base,
                        android_path=None,
                        route_candidates=(),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "canonical executable has no Android-visible "
                            "filesystem path"
                        ),
                    )
                )
                continue

            unresolved_before_match = []
            resolved_match = None

            for route in base.directory_routes:
                if not route.resolved:
                    unresolved_before_match.append(
                        route
                    )
                    continue

                assert route.path is not None

                if route.path not in android_path.parents:
                    continue

                resolved_match = route
                break

            if resolved_match is not None:
                if unresolved_before_match:
                    results.append(
                        AndroidUniverseLinkerExecutableSectionRouting(
                            elf_context=context,
                            base_configuration=base,
                            android_path=android_path,
                            route_candidates=tuple(
                                (
                                    *unresolved_before_match,
                                    resolved_match,
                                )
                            ),
                            selected_route=None,
                            selected_section=None,
                            status=(
                                AndroidUniverseLinkerExecutableSectionRoutingStatus
                                .UNRESOLVED
                            ),
                            unresolved_reason=(
                                "one or more unresolved earlier directory "
                                "routes may shadow the first known match"
                            ),
                        )
                    )
                    continue

                selected_sections = tuple(
                    section
                    for section
                    in base.sections
                    if (
                        section.name
                        == resolved_match.section_name
                    )
                )

                if len(
                    selected_sections
                ) != 1:
                    raise ValueError(
                        "generated directory route must map to exactly "
                        "one generated BASE section"
                    )

                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=base,
                        android_path=android_path,
                        route_candidates=(
                            resolved_match,
                        ),
                        selected_route=(
                            resolved_match
                        ),
                        selected_section=(
                            selected_sections[
                                0
                            ]
                        ),
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .RESOLVED
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if unresolved_before_match:
                results.append(
                    AndroidUniverseLinkerExecutableSectionRouting(
                        elf_context=context,
                        base_configuration=base,
                        android_path=android_path,
                        route_candidates=tuple(
                            unresolved_before_match
                        ),
                        selected_route=None,
                        selected_section=None,
                        status=(
                            AndroidUniverseLinkerExecutableSectionRoutingStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "unresolved generated directory routes prevent "
                            "proving that no earlier route matches"
                        ),
                    )
                )
                continue

            results.append(
                AndroidUniverseLinkerExecutableSectionRouting(
                    elf_context=context,
                    base_configuration=base,
                    android_path=android_path,
                    route_candidates=(),
                    selected_route=None,
                    selected_section=None,
                    status=(
                        AndroidUniverseLinkerExecutableSectionRoutingStatus
                        .DEFAULT_FALLBACK
                    ),
                    unresolved_reason=None,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.routing_id
                ),
            )
        )


    @staticmethod
    def reconcile_linker_executable_loading_contexts(
        *,
        executable_routing,
        apex_namespace_inputs,
    ) -> tuple[
        AndroidUniverseLinkerExecutableLoadingContext,
        ...,
    ]:
        """
        Select the canonical starting Linker namespace for every canonical
        executable-routing conclusion.

        BASE RESOLVED routing selects the exact generated namespace named
        ``default`` from the exact selected BASE section.

        APEX RESOLVED routing preserves the exact canonical APEX namespace
        input. PRESENT and ABSENT local linker.config.pb states both select
        the semantic APEX ``default`` namespace without generating that
        namespace here.

        DEFAULT_FALLBACK preserves bionic's no-config default namespace
        semantics without inventing generated namespace identity.

        Shared objects remain INAPPLICABLE. DT_NEEDED resolution is later.
        """

        if not isinstance(
            executable_routing,
            tuple,
        ):
            raise TypeError(
                "executable_routing must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerExecutableSectionRouting,
            )
            for item in executable_routing
        ):
            raise TypeError(
                "executable_routing must contain only "
                "AndroidUniverseLinkerExecutableSectionRouting instances"
            )

        if not isinstance(
            apex_namespace_inputs,
            tuple,
        ):
            raise TypeError(
                "apex_namespace_inputs must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerApexNamespaceInput,
            )
            for item in apex_namespace_inputs
        ):
            raise TypeError(
                "apex_namespace_inputs must contain only "
                "AndroidUniverseLinkerApexNamespaceInput instances"
            )

        results = []

        for routing in executable_routing:
            if (
                routing.status
                is AndroidUniverseLinkerExecutableSectionRoutingStatus
                .INAPPLICABLE
            ):
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=None,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .INAPPLICABLE
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                routing.status
                is AndroidUniverseLinkerExecutableSectionRoutingStatus
                .AMBIGUOUS
            ):
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=None,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .AMBIGUOUS
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                routing.status
                is AndroidUniverseLinkerExecutableSectionRoutingStatus
                .UNRESOLVED
            ):
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=None,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            routing.unresolved_reason
                            or (
                                "canonical executable section routing "
                                "is unresolved"
                            )
                        ),
                    )
                )
                continue

            if (
                routing.status
                is AndroidUniverseLinkerExecutableSectionRoutingStatus
                .DEFAULT_FALLBACK
            ):
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=None,
                        namespace_name="default",
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .DEFAULT_FALLBACK
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            scope = (
                routing
                .elf_context
                .configuration_scope
            )

            if (
                scope
                is AndroidUniverseLinkerElfConfigurationScope.BASE
            ):
                section = routing.selected_section

                if section is None:
                    raise ValueError(
                        "resolved BASE routing must preserve exact "
                        "selected section before namespace selection"
                    )

                candidates = tuple(
                    namespace
                    for namespace in section.namespaces
                    if namespace.name == "default"
                )

                if not candidates:
                    results.append(
                        AndroidUniverseLinkerExecutableLoadingContext(
                            routing=routing,
                            base_namespace=None,
                            apex_namespace_input=None,
                            namespace_name=None,
                            status=(
                                AndroidUniverseLinkerExecutableLoadingContextStatus
                                .UNRESOLVED
                            ),
                            unresolved_reason=(
                                "selected generated BASE section has no "
                                "canonical default namespace"
                            ),
                        )
                    )
                    continue

                if len(candidates) > 1:
                    results.append(
                        AndroidUniverseLinkerExecutableLoadingContext(
                            routing=routing,
                            base_namespace=None,
                            apex_namespace_input=None,
                            namespace_name=None,
                            status=(
                                AndroidUniverseLinkerExecutableLoadingContextStatus
                                .AMBIGUOUS
                            ),
                            unresolved_reason=None,
                        )
                    )
                    continue

                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=candidates[0],
                        apex_namespace_input=None,
                        namespace_name="default",
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .RESOLVED
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            selected_apex = (
                routing
                .elf_context
                .selected_apex_requirement
            )

            if selected_apex is None:
                raise ValueError(
                    "resolved APEX routing must preserve exact "
                    "selected APEX requirement before namespace selection"
                )

            candidates = tuple(
                item
                for item in apex_namespace_inputs
                if item.apex_requirement is selected_apex
            )

            if not candidates:
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=None,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "no canonical APEX namespace input preserves "
                            "the selected APEX requirement identity"
                        ),
                    )
                )
                continue

            if len(candidates) > 1:
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=None,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .AMBIGUOUS
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            namespace_input = candidates[0]

            if (
                namespace_input.status
                is AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
            ):
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=namespace_input,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .AMBIGUOUS
                        ),
                        unresolved_reason=None,
                    )
                )
                continue

            if (
                namespace_input.status
                is AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
            ):
                results.append(
                    AndroidUniverseLinkerExecutableLoadingContext(
                        routing=routing,
                        base_namespace=None,
                        apex_namespace_input=namespace_input,
                        namespace_name=None,
                        status=(
                            AndroidUniverseLinkerExecutableLoadingContextStatus
                            .UNRESOLVED
                        ),
                        unresolved_reason=(
                            "canonical APEX-local namespace-policy "
                            "association is unresolved"
                        ),
                    )
                )
                continue

            results.append(
                AndroidUniverseLinkerExecutableLoadingContext(
                    routing=routing,
                    base_namespace=None,
                    apex_namespace_input=namespace_input,
                    namespace_name="default",
                    status=(
                        AndroidUniverseLinkerExecutableLoadingContextStatus
                        .RESOLVED
                    ),
                    unresolved_reason=None,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.loading_context_id
                ),
            )
        )


    @staticmethod
    def reconcile_linker_section_apex_applicability(
        *,
        generated_base_configurations,
        apex_requirements,
        namespace_inputs,
        public_library_conclusions,
    ) -> tuple[
        AndroidUniverseLinkerSectionApexApplicability,
        ...,
    ]:
        """
        Reconcile AOSP Linker section-visible APEX semantics.

        BuildSection-backed sections use two semantic inputs:

        1. the APEX-local linker.config.pb effective ``visible`` value;
        2. the section builder's visible_apexes population.

        System, isolated, and unrestricted add APEXes carrying JNI libraries
        or derived public libraries.

        Vendor and product add APEXes carrying derived public libraries only.

        Postinstall is explicitly excluded because Android constructs that
        Section directly without BuildSection().

        This method determines runtime semantics only. It does not construct
        namespaces, paths, links, providers, expanded sections, or
        Reconstruction outputs.
        """

        for field_name, value in (
            (
                "generated_base_configurations",
                generated_base_configurations,
            ),
            (
                "apex_requirements",
                apex_requirements,
            ),
            (
                "namespace_inputs",
                namespace_inputs,
            ),
            (
                "public_library_conclusions",
                public_library_conclusions,
            ),
        ):
            if not isinstance(
                value,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

        namespace_by_apex_identity = {
            id(
                item.apex_requirement
            ): item
            for item
            in namespace_inputs
        }

        public_by_apex_identity = {
            id(
                item.apex_requirement
            ): item
            for item
            in public_library_conclusions
        }

        if len(
            namespace_by_apex_identity
        ) != len(
            namespace_inputs
        ):
            raise ValueError(
                "namespace_inputs must contain at most one canonical "
                "record per exact APEX requirement"
            )

        if len(
            public_by_apex_identity
        ) != len(
            public_library_conclusions
        ):
            raise ValueError(
                "public_library_conclusions must contain at most one "
                "canonical record per exact APEX requirement"
            )

        conclusions = []

        for base_configuration in (
            generated_base_configurations
        ):
            runtime_context = (
                base_configuration
                .inputs
                .runtime_policy
                .runtime_context
            )

            runtime_apexes = tuple(
                apex
                for apex
                in apex_requirements
                if apex.shares_runtime(
                    runtime_context
                )
            )

            for section in (
                base_configuration.sections
            ):
                for apex in runtime_apexes:
                    namespace_input = (
                        namespace_by_apex_identity
                        .get(
                            id(
                                apex
                            )
                        )
                    )

                    public_conclusion = (
                        public_by_apex_identity
                        .get(
                            id(
                                apex
                            )
                        )
                    )

                    if namespace_input is None:
                        raise ValueError(
                            "section/APEX applicability requires exactly "
                            "one canonical namespace input for every "
                            "canonical APEX requirement"
                        )

                    if public_conclusion is None:
                        raise ValueError(
                            "section/APEX applicability requires exactly "
                            "one canonical public-library conclusion for "
                            "every canonical APEX requirement"
                        )

                    #
                    # Android BuildPostInstallSection() constructs Section
                    # directly and therefore performs no APEX visibility
                    # injection at all.
                    #
                    if AndroidRuntimeLinkerSectionSemantics.is_postinstall(section.name):
                        conclusions.append(
                            AndroidUniverseLinkerSectionApexApplicability(
                                base_configuration=(
                                    base_configuration
                                ),
                                section=section,
                                apex_requirement=apex,
                                namespace_input=(
                                    namespace_input
                                ),
                                public_library_conclusion=(
                                    public_conclusion
                                ),
                                reasons=(),
                                status=(
                                    AndroidUniverseLinkerSectionApexApplicabilityStatus
                                    .INAPPLICABLE
                                ),
                            )
                        )
                        continue

                    rule = (
                        AndroidRuntimeLinkerSectionSemantics
                        .apex_visibility_policy(
                            section.name
                        )
                    )

                    if rule is None:
                        conclusions.append(
                            AndroidUniverseLinkerSectionApexApplicability(
                                base_configuration=(
                                    base_configuration
                                ),
                                section=section,
                                apex_requirement=apex,
                                namespace_input=(
                                    namespace_input
                                ),
                                public_library_conclusion=(
                                    public_conclusion
                                ),
                                reasons=(),
                                status=(
                                    AndroidUniverseLinkerSectionApexApplicabilityStatus
                                    .UNRESOLVED
                                ),
                            )
                        )
                        continue

                    (
                        allows_jni,
                        allows_public,
                    ) = rule

                    reasons = []

                    namespace_ambiguous = False
                    namespace_unresolved = False

                    if (
                        namespace_input.status
                        is AndroidUniverseLinkerApexNamespaceStatus.PRESENT
                    ):
                        selected = (
                            namespace_input
                            .selected_apex_local_configuration
                        )

                        if (
                            selected is not None
                            and selected.effective_visible
                        ):
                            reasons.append(
                                AndroidUniverseLinkerSectionApexApplicabilityReason
                                .APEX_LOCAL_VISIBLE
                            )

                    elif (
                        namespace_input.status
                        is AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
                    ):
                        namespace_ambiguous = True

                    elif (
                        namespace_input.status
                        is AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
                    ):
                        namespace_unresolved = True

                    if (
                        allows_jni
                        and apex.jni_libs
                    ):
                        reasons.append(
                            AndroidUniverseLinkerSectionApexApplicabilityReason
                            .JNI_LIBRARIES
                        )

                    public_ambiguous = False
                    public_unresolved = False

                    if allows_public:
                        if (
                            public_conclusion.status
                            is AndroidUniverseLinkerApexPublicLibraryStatus
                            .AMBIGUOUS
                        ):
                            public_ambiguous = True

                        elif (
                            public_conclusion.status
                            is AndroidUniverseLinkerApexPublicLibraryStatus
                            .UNRESOLVED
                        ):
                            public_unresolved = True

                        elif (
                            public_conclusion.public_libraries
                        ):
                            reasons.append(
                                AndroidUniverseLinkerSectionApexApplicabilityReason
                                .PUBLIC_LIBRARIES
                            )

                    if reasons:
                        status = (
                            AndroidUniverseLinkerSectionApexApplicabilityStatus
                            .ACTIVE
                        )

                    elif (
                        namespace_ambiguous
                        or public_ambiguous
                    ):
                        status = (
                            AndroidUniverseLinkerSectionApexApplicabilityStatus
                            .AMBIGUOUS
                        )

                    elif (
                        namespace_unresolved
                        or public_unresolved
                    ):
                        status = (
                            AndroidUniverseLinkerSectionApexApplicabilityStatus
                            .UNRESOLVED
                        )

                    else:
                        status = (
                            AndroidUniverseLinkerSectionApexApplicabilityStatus
                            .INAPPLICABLE
                        )

                    conclusions.append(
                        AndroidUniverseLinkerSectionApexApplicability(
                            base_configuration=(
                                base_configuration
                            ),
                            section=section,
                            apex_requirement=apex,
                            namespace_input=(
                                namespace_input
                            ),
                            public_library_conclusion=(
                                public_conclusion
                            ),
                            reasons=tuple(
                                reasons
                            ),
                            status=status,
                        )
                    )

        return tuple(
            sorted(
                conclusions,
                key=lambda conclusion: (
                    conclusion.conclusion_id
                ),
            )
        )


    @staticmethod
    def reconcile_linker_apex_provider_descriptors(
        *,
        apex_requirements,
        namespace_inputs,
        active_runtime_paths,
    ) -> tuple[
        AndroidUniverseLinkerApexProviderDescriptor,
        ...,
    ]:
        """
        Assemble the canonical active-APEX provider population consumed by
        later BuildSection()/Section::Resolve() semantics.

        This reproduces only ApexInfo fields required by namespace/provider
        reconciliation. It does not create namespaces or resolve consumers.

        AOSP semantics preserved here:

        - provideSharedApexLibs=true excludes the APEX from the provider set;
        - requireSharedApexLibs non-empty sets ApexInfo.has_shared_lib;
        - absent APEX-local linker.config.pb is valid and contributes no
          additional permitted paths;
        - ambiguous/unresolved activation or local-policy evidence remains
          canonical ambiguity/unresolved state.
        """

        for field_name, values in (
            (
                "apex_requirements",
                apex_requirements,
            ),
            (
                "namespace_inputs",
                namespace_inputs,
            ),
            (
                "active_runtime_paths",
                active_runtime_paths,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        namespace_by_identity = {
            id(
                item.apex_requirement
            ): item
            for item
            in namespace_inputs
        }

        runtime_path_by_identity = {
            id(
                item.apex_requirement
            ): item
            for item
            in active_runtime_paths
        }

        if len(
            namespace_by_identity
        ) != len(
            namespace_inputs
        ):
            raise ValueError(
                "namespace_inputs must contain at most one record "
                "per exact APEX requirement"
            )

        if len(
            runtime_path_by_identity
        ) != len(
            active_runtime_paths
        ):
            raise ValueError(
                "active_runtime_paths must contain at most one record "
                "per exact APEX requirement"
            )

        results = []

        for requirement in apex_requirements:
            namespace_input = (
                namespace_by_identity.get(
                    id(
                        requirement
                    )
                )
            )

            active_runtime_path = (
                runtime_path_by_identity.get(
                    id(
                        requirement
                    )
                )
            )

            if namespace_input is None:
                raise ValueError(
                    "provider reconciliation requires exactly one "
                    "namespace input for every exact APEX requirement"
                )

            if active_runtime_path is None:
                raise ValueError(
                    "provider reconciliation requires exactly one active "
                    "runtime-path conclusion for every exact APEX requirement"
                )

            if requirement.provide_shared_apex_libs:
                status = (
                    AndroidUniverseLinkerApexProviderStatus
                    .EXCLUDED_SHARED_APEX
                )

            elif (
                namespace_input.status
                is AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
                or active_runtime_path.status
                is AndroidUniverseRelationshipStatus.AMBIGUOUS
            ):
                status = (
                    AndroidUniverseLinkerApexProviderStatus.AMBIGUOUS
                )

            elif (
                namespace_input.status
                is AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
                or active_runtime_path.status
                is AndroidUniverseRelationshipStatus.UNRESOLVED
            ):
                status = (
                    AndroidUniverseLinkerApexProviderStatus.UNRESOLVED
                )

            elif (
                namespace_input.status
                in {
                    AndroidUniverseLinkerApexNamespaceStatus.PRESENT,
                    AndroidUniverseLinkerApexNamespaceStatus.ABSENT,
                }
                and active_runtime_path.status
                is AndroidUniverseRelationshipStatus.RESOLVED
            ):
                status = (
                    AndroidUniverseLinkerApexProviderStatus.ACTIVE
                )

            else:
                status = (
                    AndroidUniverseLinkerApexProviderStatus.UNRESOLVED
                )

            if (
                status
                is AndroidUniverseLinkerApexProviderStatus.ACTIVE
            ):
                selected = (
                    namespace_input
                    .selected_apex_local_configuration
                )

                permitted_paths = (
                    ()
                    if selected is None
                    else tuple(
                        item.path
                        for item
                        in selected.permitted_paths
                    )
                )

                namespace_name = (
                    AndroidRuntimeLinkerApexIdentity.namespace_name(requirement)
                )

                active_root = (
                    active_runtime_path.active_root
                )

                in_vendor = (
                    AndroidRuntimeLinkerApexDeploymentSemantics
                    .is_vendor_partition(
                        requirement
                    )
                )

                provided_libraries = (
                    requirement.provide_native_libs
                )

                required_libraries = (
                    requirement.require_native_libs
                )

                has_shared_lib = bool(
                    requirement.require_shared_apex_libs
                )

            else:
                namespace_name = None
                active_root = None
                in_vendor = None
                permitted_paths = ()
                provided_libraries = ()
                required_libraries = ()
                has_shared_lib = None

            results.append(
                AndroidUniverseLinkerApexProviderDescriptor(
                    apex_requirement=requirement,
                    namespace_input=namespace_input,
                    active_runtime_path=(
                        active_runtime_path
                    ),
                    namespace_name=namespace_name,
                    active_root=active_root,
                    in_vendor=in_vendor,
                    permitted_paths=(
                        permitted_paths
                    ),
                    provided_libraries=(
                        provided_libraries
                    ),
                    required_libraries=(
                        required_libraries
                    ),
                    has_shared_lib=(
                        has_shared_lib
                    ),
                    status=status,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.descriptor_id
                ),
            )
        )
