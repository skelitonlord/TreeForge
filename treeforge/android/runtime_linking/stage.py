from __future__ import annotations

from treeforge.android.runtime_linking.linker.provider import (
    AndroidRuntimeLinkerSectionProviderVocabulary,
)

from treeforge.android.runtime_linking.linker.avf_guest_applicability import (
    AndroidRuntimeLinkerAvfGuestTraversalApplicability,
)

from treeforge.android.runtime_linking.linker.section_semantics import (
    AndroidRuntimeLinkerSectionSemantics,
)

from treeforge.android.runtime_linking.linker.apex_deployment import (
    AndroidRuntimeLinkerApexDeploymentSemantics,
)

from treeforge.android.runtime_linking.linker.elf_dependency_resolution import (
    AndroidRuntimeLinkerContextualElfDependencyResolver,
    AndroidRuntimeLinkerElfDependencyTraversal,
    AndroidRuntimeLinkerElfDependencyTraversalStatus,
)
from treeforge.android.runtime_linking.linker.elf_runtime_candidate import (
    AndroidRuntimeLinkerElfRuntimeCandidateBuilder,
    AndroidRuntimeLinkerElfRuntimeCandidateStatus,
)
from treeforge.android.runtime_linking.linker.generated_configuration import (
    AndroidUniverseLinkerGeneratedBaseConfigurationBuilder,
    AndroidUniverseLinkerGeneratedConfigurationInputReconciler,
)
from treeforge.android.runtime_linking.linker.effective_configuration import (
    AndroidRuntimeLinkerEffectiveApexConfigurationBuilder,
    AndroidRuntimeLinkerEffectiveConfigurationBuilder,
)
from treeforge.android.runtime_linking.linker.expression_resolution import (
    AndroidRuntimeLinkerVariableEnvironmentBuilder,
)
from treeforge.android.runtime_linking.linker.provider import (
    AndroidRuntimeLinkerProviderVocabularyBuilder,
)
from treeforge.android.runtime_linking.linker.namespace_accessibility import (
    AndroidRuntimeLinkerNamespaceAccessibilityBuilder,
)

from treeforge.android.runtime_linking.linker.standard_system_links import (
    AndroidRuntimeLinkerStandardSystemLinksBuilder,
)

from treeforge.android.runtime_linking.linker.resolution import (
    AndroidRuntimeLinkerSectionResolver,
)
from treeforge.android.runtime_linking.model import (
    AndroidRuntimeLinkerResolvedApexSectionResult,
    AndroidRuntimeLinkerResolvedBaseSectionResult,
    AndroidRuntimeLinking,
)
from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.universe.properties.conclusion import (
    AndroidUniverseConclusionStatus,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerExecutableLoadingContextStatus,
)
from treeforge.android.runtime_linking.relationships.reconciler import (
    AndroidRuntimeLinkingReconciler,
)
from treeforge.android.version.model import (
    AndroidSemanticVersionSelection,
)

from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


class AndroidRuntimeLinkingStage:
    """
    Evaluate Android runtime-linker behavior from canonical Device Universe
    facts.

    The stage consumes exact Universe identities and the exact upstream
    Android semantic-version selection. It does not reparse, reselect a
    platform version, infer device knowledge, or create Reconstruction work.
    """

    def __init__(
        self,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.progress_callback = progress_callback

    def run(
        self,
        universe: AndroidDeviceUniverse,
        *,
        semantic_version: AndroidSemanticVersionSelection,
    ) -> AndroidRuntimeLinking:
        if not isinstance(
            universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        if not isinstance(
            semantic_version,
            AndroidSemanticVersionSelection,
        ):
            raise TypeError(
                "semantic_version must be an "
                "AndroidSemanticVersionSelection"
            )

        self._report_progress(
            current=1,
            total=15,
            operation="generated configuration inputs",
            state=ProgressState.RUNNING,
        )

        linker_generated_configuration_inputs = (
            AndroidUniverseLinkerGeneratedConfigurationInputReconciler()
            .reconcile(
                linker_requirement=(
                    universe.linker_requirement
                ),
                property_conclusions=(
                    universe.conclusions
                ),
                model_source_requirements=(
                    universe.model_source_requirements
                ),
                apex_requirements=(
                    universe.apex_requirements
                ),
            )
        )

        self._report_progress(
            current=1,
            total=15,
            operation="generated configuration inputs",
            state=ProgressState.COMPLETE,
        )

        #
        # Materialize one exact linkerconfig variable environment per
        # generated runtime input set. This is a canonical Runtime Linking
        # derivation and is reused by Section::Resolve(),
        # AddStandardSystemLinks(), namespace lookup, and contextual
        # DT_NEEDED resolution.
        #
        linker_variable_environments = tuple(
            AndroidRuntimeLinkerVariableEnvironmentBuilder
            .build(
                inputs=inputs,
            )
            for inputs
            in linker_generated_configuration_inputs
        )

        variable_environment_by_input_identity = {
            id(
                environment.inputs
            ): environment
            for environment
            in linker_variable_environments
        }

        if len(
            variable_environment_by_input_identity
        ) != len(
            linker_variable_environments
        ):
            raise ValueError(
                "Runtime Linking variable environments must contain "
                "exactly one record per generated input identity"
            )

        def runtime_variable_environment(
            *,
            inputs,
        ):
            environment = (
                variable_environment_by_input_identity
                .get(
                    id(
                        inputs
                    )
                )
            )

            if environment is None:
                raise ValueError(
                    "Runtime Linking requires one preserved variable "
                    "environment for the exact generated input identity"
                )

            if environment.inputs is not inputs:
                raise ValueError(
                    "Runtime Linking variable-environment lookup changed "
                    "generated input identity"
                )

            return environment

        self._report_progress(
            current=2,
            total=15,
            operation="generated BASE topology",
            state=ProgressState.RUNNING,
        )

        generated_base_builder = (
            AndroidUniverseLinkerGeneratedBaseConfigurationBuilder()
        )

        linker_generated_base_configurations = tuple(
            generated_base_builder.build(
                inputs=inputs,
                semantic_profile=(
                    semantic_version.profile
                ),
            )
            for inputs
            in linker_generated_configuration_inputs
        )

        self._report_progress(
            current=2,
            total=15,
            operation="generated BASE topology",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=3,
            total=15,
            operation="active APEX runtime population",
            state=ProgressState.RUNNING,
        )

        linker_apex_active_runtime_paths = (
            AndroidRuntimeLinkingReconciler
            .reconcile_linker_apex_active_runtime_paths(
                apex_requirements=(
                    universe.apex_requirements
                ),
            )
        )

        self._report_progress(
            current=3,
            total=15,
            operation="active APEX runtime population",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=4,
            total=15,
            operation="APEX provider population",
            state=ProgressState.RUNNING,
        )

        linker_apex_provider_descriptors = (
            AndroidRuntimeLinkingReconciler
            .reconcile_linker_apex_provider_descriptors(
                apex_requirements=(
                    universe.apex_requirements
                ),
                namespace_inputs=(
                    universe.linker_apex_namespace_inputs
                ),
                active_runtime_paths=(
                    linker_apex_active_runtime_paths
                ),
            )
        )

        self._report_progress(
            current=4,
            total=15,
            operation="APEX provider population",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=5,
            total=15,
            operation="section/APEX participation",
            state=ProgressState.RUNNING,
        )

        linker_section_apex_applicability = (
            AndroidRuntimeLinkingReconciler
            .reconcile_linker_section_apex_applicability(
                generated_base_configurations=(
                    linker_generated_base_configurations
                ),
                apex_requirements=(
                    universe.apex_requirements
                ),
                namespace_inputs=(
                    universe.linker_apex_namespace_inputs
                ),
                public_library_conclusions=(
                    universe
                    .linker_apex_public_library_conclusions
                ),
            )
        )

        self._report_progress(
            current=5,
            total=15,
            operation="section/APEX participation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=6,
            total=15,
            operation="effective namespace population",
            state=ProgressState.RUNNING,
        )

        linker_effective_base_configurations = (
            AndroidRuntimeLinkerEffectiveConfigurationBuilder.build(
                generated_base_configurations=(
                    linker_generated_base_configurations
                ),
                apex_requirements=(
                    universe.apex_requirements
                ),
                apex_provider_descriptors=(
                    linker_apex_provider_descriptors
                ),
                section_apex_applicability=(
                    linker_section_apex_applicability
                ),
            )
        )

        self._report_progress(
            current=6,
            total=15,
            operation="effective namespace population",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=7,
            total=15,
            operation="APEX effective section population",
            state=ProgressState.RUNNING,
        )

        linker_effective_apex_configurations = (
            AndroidRuntimeLinkerEffectiveApexConfigurationBuilder.build(
                generated_base_configurations=(
                    linker_generated_base_configurations
                ),
                apex_provider_descriptors=(
                    linker_apex_provider_descriptors
                ),
                semantic_profile=(
                    semantic_version.profile
                ),
                apex_requirements=(
                    universe.apex_requirements
                ),
                section_apex_applicability=(
                    linker_section_apex_applicability
                ),
            )
        )

        self._report_progress(
            current=7,
            total=15,
            operation="APEX effective section population",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=8,
            total=15,
            operation="Section::Resolve",
            state=ProgressState.RUNNING,
        )

        provider_builder = (
            AndroidRuntimeLinkerProviderVocabularyBuilder
        )

        def runtime_apex_library_providers(
            *,
            inputs,
        ):
            runtime_provider_descriptors = tuple(
                provider
                for provider
                in linker_apex_provider_descriptors
                if (
                    provider
                    .apex_requirement
                    .shares_runtime(
                        inputs.runtime_policy.runtime_context
                    )
                )
            )

            return provider_builder.apex_providers(
                apex_provider_descriptors=(
                    runtime_provider_descriptors
                ),
            )

        provider_vocabulary_base_sections = []
        resolved_base_sections = []

        for effective_configuration in (
            linker_effective_base_configurations
        ):
            inputs = (
                effective_configuration
                .generated_configuration
                .inputs
            )

            environment = (
                runtime_variable_environment(
                    inputs=inputs,
                )
            )

            apex_library_providers = (
                runtime_apex_library_providers(
                    inputs=inputs,
                )
            )

            for effective_section in (
                effective_configuration.sections
            ):
                section_name = (
                    effective_section
                    .generated_section
                    .name
                )

                provider_vocabulary = (
                    AndroidRuntimeLinkerSectionProviderVocabulary(
                        section_name=section_name,
                        concrete_library_providers=(
                            provider_builder
                            .concrete_providers(
                                namespaces=(
                                    effective_section
                                    .namespaces
                                ),
                            )
                        ),
                        apex_library_providers=(
                            apex_library_providers
                        ),
                        alias_providers=(
                            provider_builder
                            .base_alias_providers(
                                section_name=section_name,
                                inputs=inputs,
                            )
                        ),
                    )
                )

                provider_vocabulary_base_sections.append(
                    provider_vocabulary
                )

                resolved_section = (
                    AndroidRuntimeLinkerSectionResolver
                    .resolve(
                        section_name=(
                            provider_vocabulary
                            .section_name
                        ),
                        namespaces=(
                            effective_section.namespaces
                        ),
                        concrete_providers=(
                            provider_vocabulary
                            .concrete_library_providers
                        ),
                        apex_providers=(
                            provider_vocabulary
                            .apex_library_providers
                        ),
                        alias_providers=(
                            provider_vocabulary
                            .alias_providers
                        ),
                        environment=environment,
                    )
                )

                resolved_base_sections.append(
                    AndroidRuntimeLinkerResolvedBaseSectionResult(
                        effective_section=(
                            effective_section
                        ),
                        resolved_section=(
                            resolved_section
                        ),
                    )
                )

        linker_provider_vocabulary_base_sections = tuple(
            provider_vocabulary_base_sections
        )

        linker_resolved_base_sections = tuple(
            resolved_base_sections
        )

        provider_vocabulary_apex_sections = []
        resolved_apex_sections = []

        for effective_configuration in (
            linker_effective_apex_configurations
        ):
            inputs = (
                effective_configuration
                .runtime_inputs
            )

            environment = (
                runtime_variable_environment(
                    inputs=inputs,
                )
            )

            provider_vocabulary = (
                AndroidRuntimeLinkerSectionProviderVocabulary(
                    section_name=(
                        effective_configuration
                        .section_name
                    ),
                    concrete_library_providers=(
                        provider_builder
                        .concrete_providers(
                            namespaces=(
                                effective_configuration
                                .namespaces
                            ),
                        )
                    ),
                    apex_library_providers=(
                        runtime_apex_library_providers(
                            inputs=inputs,
                        )
                    ),
                    alias_providers=(
                        provider_builder
                        .apex_alias_providers(
                            configuration=(
                                effective_configuration
                            ),
                            non_vndk_sanitizer_variable=(
                                semantic_version
                                .profile
                                .linker
                                .apex_non_vndk_vendor_product_sanitizer_variable
                            ),
                            system_context_accumulates_configs=(
                                semantic_version
                                .profile
                                .linker
                                .system_context_accumulates_configs
                            ),
                        )
                    ),
                )
            )

            provider_vocabulary_apex_sections.append(
                provider_vocabulary
            )

            resolved_section = (
                AndroidRuntimeLinkerSectionResolver
                .resolve(
                    section_name=(
                        provider_vocabulary
                        .section_name
                    ),
                    namespaces=(
                        effective_configuration
                        .namespaces
                    ),
                    concrete_providers=(
                        provider_vocabulary
                        .concrete_library_providers
                    ),
                    apex_providers=(
                        provider_vocabulary
                        .apex_library_providers
                    ),
                    alias_providers=(
                        provider_vocabulary
                        .alias_providers
                    ),
                    environment=environment,
                )
            )

            resolved_apex_sections.append(
                AndroidRuntimeLinkerResolvedApexSectionResult(
                    effective_configuration=(
                        effective_configuration
                    ),
                    resolved_section=(
                        resolved_section
                    ),
                )
            )

        linker_provider_vocabulary_apex_sections = tuple(
            provider_vocabulary_apex_sections
        )

        linker_resolved_apex_sections = tuple(
            resolved_apex_sections
        )

        self._report_progress(
            current=8,
            total=15,
            operation="Section::Resolve",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=9,
            total=15,
            operation="AddStandardSystemLinks",
            state=ProgressState.RUNNING,
        )

        standard_base_sections = []

        resolved_base_iterator = iter(
            linker_resolved_base_sections
        )

        for effective_configuration in (
            linker_effective_base_configurations
        ):
            inputs = (
                effective_configuration
                .generated_configuration
                .inputs
            )

            debuggable = inputs.debuggable

            if debuggable is None:
                raise ValueError(
                    "AddStandardSystemLinks requires resolved "
                    "ro.debuggable semantics"
                )

            environment = (
                runtime_variable_environment(
                    inputs=inputs,
                )
            )

            for effective_section in (
                effective_configuration.sections
            ):
                resolved_result = next(
                    resolved_base_iterator
                )

                if (
                    resolved_result.effective_section
                    is not effective_section
                ):
                    raise ValueError(
                        "resolved BASE section order changed before "
                        "AddStandardSystemLinks"
                    )

                section_name = (
                    effective_section
                    .generated_section
                    .name
                )

                system_namespace_name = AndroidRuntimeLinkerSectionSemantics.standard_system_namespace_name(section_name)

                section_vndk_enabled = AndroidRuntimeLinkerSectionSemantics.vndk_enabled(section_name, vendor_vndk_defined=inputs.vendor_vndk_version_defined, product_vndk_defined=inputs.product_vndk_version_defined)

                standard_base_sections.append(
                    AndroidRuntimeLinkerStandardSystemLinksBuilder
                    .apply(
                        section=(
                            resolved_result
                            .resolved_section
                        ),
                        environment=environment,
                        system_namespace_name=(
                            system_namespace_name
                        ),
                        section_vndk_enabled=(
                            section_vndk_enabled
                        ),
                        debuggable=debuggable,
                    )
                )

        try:
            next(
                resolved_base_iterator
            )
        except StopIteration:
            pass
        else:
            raise ValueError(
                "unconsumed resolved BASE sections remain after "
                "AddStandardSystemLinks"
            )

        linker_standard_system_linked_base_sections = (
            tuple(
                standard_base_sections
            )
        )

        standard_apex_sections = []

        for (
            effective_configuration,
            resolved_result,
        ) in zip(
            linker_effective_apex_configurations,
            linker_resolved_apex_sections,
            strict=True,
        ):
            inputs = (
                effective_configuration
                .runtime_inputs
            )

            debuggable = inputs.debuggable

            if debuggable is None:
                raise ValueError(
                    "AddStandardSystemLinks requires resolved "
                    "ro.debuggable semantics"
                )

            environment = (
                runtime_variable_environment(
                    inputs=inputs,
                )
            )

            apex_requirement = (
                effective_configuration
                .apex_provider
                .apex_requirement
            )

            if (
                AndroidRuntimeLinkerApexDeploymentSemantics
                .is_vendor_partition(
                    apex_requirement
                )
            ):
                section_vndk_enabled = (
                    inputs.vendor_vndk_version_defined
                )

            elif (
                AndroidRuntimeLinkerApexDeploymentSemantics
                .is_product_partition(
                    apex_requirement
                )
            ):
                section_vndk_enabled = (
                    inputs.product_vndk_version_defined
                )

            else:
                section_vndk_enabled = False

            standard_apex_sections.append(
                AndroidRuntimeLinkerStandardSystemLinksBuilder
                .apply(
                    section=(
                        resolved_result
                        .resolved_section
                    ),
                    environment=environment,
                    system_namespace_name="system",
                    section_vndk_enabled=(
                        section_vndk_enabled
                    ),
                    debuggable=debuggable,
                )
            )

        linker_standard_system_linked_apex_sections = (
            tuple(
                standard_apex_sections
            )
        )

        self._report_progress(
            current=9,
            total=15,
            operation="AddStandardSystemLinks",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=10,
            total=15,
            operation="namespace accessibility",
            state=ProgressState.RUNNING,
        )

        linker_namespace_accessibility_base_sections = tuple(
            AndroidRuntimeLinkerNamespaceAccessibilityBuilder
            .build(
                section
            )
            for section
            in linker_standard_system_linked_base_sections
        )

        linker_namespace_accessibility_apex_sections = tuple(
            AndroidRuntimeLinkerNamespaceAccessibilityBuilder
            .build(
                section
            )
            for section
            in linker_standard_system_linked_apex_sections
        )

        self._report_progress(
            current=10,
            total=15,
            operation="namespace accessibility",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=11,
            total=15,
            operation="executable section routing",
            state=ProgressState.RUNNING,
        )

        unsupported_elf_bitnesses = frozenset(
            bitness
            for fact, bitness
            in (
                (
                    "supported_32_bit_cpu_abis",
                    32,
                ),
                (
                    "supported_64_bit_cpu_abis",
                    64,
                ),
            )
            for conclusion
            in universe.conclusions
            if (
                conclusion.fact == fact
                and conclusion.status
                is AndroidUniverseConclusionStatus.AGREED
                and conclusion.value == ""
            )
        )

        linker_executable_section_routing = (
            AndroidRuntimeLinkingReconciler
            .reconcile_linker_executable_section_routing(
                elf_contexts=(
                    universe.linker_elf_contexts
                ),
                generated_base_configurations=(
                    linker_generated_base_configurations
                ),
                apex_active_runtime_paths=(
                    linker_apex_active_runtime_paths
                ),
                unsupported_elf_bitnesses=(
                    unsupported_elf_bitnesses
                ),
            )
        )

        self._report_progress(
            current=11,
            total=15,
            operation="executable section routing",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=12,
            total=15,
            operation="starting loading contexts",
            state=ProgressState.RUNNING,
        )

        linker_executable_loading_contexts = (
            AndroidRuntimeLinkingReconciler
            .reconcile_linker_executable_loading_contexts(
                executable_routing=(
                    linker_executable_section_routing
                ),
                apex_namespace_inputs=(
                    universe.linker_apex_namespace_inputs
                ),
            )
        )

        self._report_progress(
            current=12,
            total=15,
            operation="starting loading contexts",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=13,
            total=15,
            operation="ELF runtime candidate population",
            state=ProgressState.RUNNING,
        )

        linker_elf_runtime_candidates = (
            AndroidRuntimeLinkerElfRuntimeCandidateBuilder
            .build(
                elf_contexts=(
                    universe.linker_elf_contexts
                ),
                apex_active_runtime_paths=(
                    linker_apex_active_runtime_paths
                ),
            )
        )

        self._report_progress(
            current=13,
            total=15,
            operation="ELF runtime candidate population",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=14,
            total=15,
            operation="contextual ELF DT_NEEDED resolution",
            state=ProgressState.RUNNING,
        )

        candidate_by_elf_context_identity = {
            id(
                candidate.linker_elf_context
            ): candidate
            for candidate
            in linker_elf_runtime_candidates
        }

        if len(
            candidate_by_elf_context_identity
        ) != len(
            linker_elf_runtime_candidates
        ):
            raise ValueError(
                "ELF runtime candidates must preserve unique exact "
                "Linker/ELF context identity"
            )

        guest_traversal_inapplicable_reasons = (
            AndroidRuntimeLinkerAvfGuestTraversalApplicability
            .classify(
                avf_requirement=(
                    universe.avf_requirement
                ),
                loading_contexts=(
                    linker_executable_loading_contexts
                ),
                candidates=(
                    linker_elf_runtime_candidates
                ),
            )
        )

        #
        # Preserve exact BASE effective-section -> post-standard accessibility
        # and variable-environment ownership.
        #
        base_runtime_contexts = []

        base_accessibility_iterator = iter(
            linker_namespace_accessibility_base_sections
        )

        base_standard_link_iterator = iter(
            linker_standard_system_linked_base_sections
        )

        for effective_configuration in (
            linker_effective_base_configurations
        ):
            inputs = (
                effective_configuration
                .generated_configuration
                .inputs
            )

            environment = (
                runtime_variable_environment(
                    inputs=inputs,
                )
            )

            for effective_section in (
                effective_configuration.sections
            ):
                accessibility = next(
                    base_accessibility_iterator
                )

                standard_linked_section = next(
                    base_standard_link_iterator
                )

                if (
                    accessibility.source
                    is not standard_linked_section
                ):
                    raise ValueError(
                        "BASE accessibility must preserve the exact "
                        "standard-linked section identity before "
                        "contextual ELF resolution"
                    )

                if (
                    accessibility.section
                    is not standard_linked_section.linked_section
                ):
                    raise ValueError(
                        "BASE accessibility must preserve the exact "
                        "post-standard resolved-section identity before "
                        "contextual ELF resolution"
                    )

                if (
                    accessibility
                    .source
                    .source_section
                    .section_name
                    != effective_section.generated_section.name
                ):
                    raise ValueError(
                        "BASE accessibility order changed before "
                        "contextual ELF resolution"
                    )

                base_runtime_contexts.append(
                    (
                        effective_section.generated_section,
                        accessibility,
                        environment,
                    )
                )

        try:
            next(
                base_accessibility_iterator
            )
        except StopIteration:
            pass
        else:
            raise ValueError(
                "unconsumed BASE accessibility sections remain before "
                "contextual ELF resolution"
            )

        try:
            next(
                base_standard_link_iterator
            )
        except StopIteration:
            pass
        else:
            raise ValueError(
                "unconsumed BASE standard-linked sections remain before "
                "contextual ELF resolution"
            )

        #
        # Preserve exact APEX provider/configuration -> accessibility and
        # variable-environment ownership.
        #
        apex_runtime_contexts = []

        for (
            effective_configuration,
            standard_linked_section,
            accessibility,
        ) in zip(
            linker_effective_apex_configurations,
            linker_standard_system_linked_apex_sections,
            linker_namespace_accessibility_apex_sections,
            strict=True,
        ):
            if (
                accessibility.source
                is not standard_linked_section
            ):
                raise ValueError(
                    "APEX accessibility must preserve the exact "
                    "standard-linked section identity before "
                    "contextual ELF resolution"
                )

            if (
                accessibility.section
                is not standard_linked_section.linked_section
            ):
                raise ValueError(
                    "APEX accessibility must preserve the exact "
                    "post-standard resolved-section identity before "
                    "contextual ELF resolution"
                )

            if (
                standard_linked_section
                .source_section
                .section_name
                != effective_configuration.section_name
            ):
                raise ValueError(
                    "APEX standard-linked section order changed before "
                    "contextual ELF resolution"
                )

            environment = (
                runtime_variable_environment(
                    inputs=(
                        effective_configuration
                        .runtime_inputs
                    ),
                )
            )

            apex_runtime_contexts.append(
                (
                    effective_configuration
                    .apex_provider
                    .apex_requirement,
                    accessibility,
                    environment,
                )
            )

        dependency_traversals = []

        for loading_context in (
            linker_executable_loading_contexts
        ):
            status = (
                loading_context.status
            )

            elf_context = (
                loading_context
                .routing
                .elf_context
            )

            root_candidate = (
                candidate_by_elf_context_identity
                .get(
                    id(
                        elf_context
                    )
                )
            )

            if root_candidate is None:
                raise ValueError(
                    "loading context has no exact ELF runtime-candidate "
                    "conclusion"
                )

            guest_inapplicable_reason = (
                guest_traversal_inapplicable_reasons
                .get(
                    elf_context.context_id
                )
            )

            if (
                guest_inapplicable_reason
                is not None
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=(
                            loading_context
                        ),
                        root_candidate=(
                            root_candidate
                        ),
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .INAPPLICABLE
                        ),
                        reason=(
                            guest_inapplicable_reason
                        ),
                    )
                )
                continue

            if (
                status
                is AndroidUniverseLinkerExecutableLoadingContextStatus
                .INAPPLICABLE
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=None,
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .INAPPLICABLE
                        ),
                        reason=(
                            "ELF is not a load-entry executable; shared-object "
                            "dependencies are resolved only when reached from "
                            "a contextual parent load"
                        ),
                    )
                )
                continue

            if (
                status
                is AndroidUniverseLinkerExecutableLoadingContextStatus
                .AMBIGUOUS
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=None,
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .AMBIGUOUS
                        ),
                        reason=(
                            loading_context.unresolved_reason
                            or "starting executable loading context is "
                            "ambiguous"
                        ),
                    )
                )
                continue

            if (
                status
                is AndroidUniverseLinkerExecutableLoadingContextStatus
                .UNRESOLVED
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=None,
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            loading_context.unresolved_reason
                            or "starting executable loading context is "
                            "unresolved"
                        ),
                    )
                )
                continue

            #
            # A loading context can be structurally resolvable even when the
            # exact root ELF does not participate in the post-boot Runtime
            # Linking filesystem. Preserve that candidate conclusion rather
            # than passing a non-ACTIVE root into contextual resolution.
            #
            # Loading-context INAPPLICABLE / AMBIGUOUS / UNRESOLVED states
            # above remain authoritative at the loading-context layer.
            #
            if (
                root_candidate.status
                is AndroidRuntimeLinkerElfRuntimeCandidateStatus
                .INAPPLICABLE
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=root_candidate,
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .INAPPLICABLE
                        ),
                        reason=(
                            root_candidate.reason
                            or "root ELF is inapplicable to the effective "
                            "Runtime Linking filesystem"
                        ),
                    )
                )
                continue

            if (
                root_candidate.status
                is AndroidRuntimeLinkerElfRuntimeCandidateStatus
                .AMBIGUOUS
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=root_candidate,
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .AMBIGUOUS
                        ),
                        reason=(
                            root_candidate.reason
                            or "root ELF runtime candidate is ambiguous"
                        ),
                    )
                )
                continue

            if (
                root_candidate.status
                is AndroidRuntimeLinkerElfRuntimeCandidateStatus
                .UNRESOLVED
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=root_candidate,
                        section_accessibility=None,
                        starting_namespace_name=None,
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            root_candidate.reason
                            or "root ELF runtime candidate is unresolved"
                        ),
                    )
                )
                continue

            if (
                root_candidate.status
                is not AndroidRuntimeLinkerElfRuntimeCandidateStatus
                .ACTIVE
            ):
                raise ValueError(
                    "unknown ELF runtime-candidate status before contextual "
                    f"dependency traversal: {root_candidate.status!r}"
                )

            if (
                status
                is AndroidUniverseLinkerExecutableLoadingContextStatus
                .DEFAULT_FALLBACK
            ):
                dependency_traversals.append(
                    AndroidRuntimeLinkerElfDependencyTraversal(
                        loading_context=loading_context,
                        root_candidate=root_candidate,
                        section_accessibility=None,
                        starting_namespace_name=(
                            loading_context.namespace_name
                        ),
                        dependency_resolutions=(),
                        visited_elf_namespace_states=0,
                        status=(
                            AndroidRuntimeLinkerElfDependencyTraversalStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            "bionic default no-linkerconfig loading context "
                            "is established, but its filesystem search policy "
                            "is not yet modeled by Runtime Linking"
                        ),
                    )
                )
                continue

            if (
                status
                is not AndroidUniverseLinkerExecutableLoadingContextStatus
                .RESOLVED
            ):
                raise ValueError(
                    "unknown executable loading-context status: "
                    f"{status!r}"
                )

            routing = (
                loading_context.routing
            )

            section_accessibility = None
            environment = None

            if routing.selected_section is not None:
                matches = tuple(
                    (
                        accessibility,
                        candidate_environment,
                    )
                    for (
                        generated_section,
                        accessibility,
                        candidate_environment,
                    )
                    in base_runtime_contexts
                    if generated_section
                    is routing.selected_section
                )

                if len(
                    matches
                ) != 1:
                    raise ValueError(
                        "resolved BASE executable must map to exactly one "
                        "post-standard accessibility section: "
                        f"matches={len(matches)}"
                    )

                (
                    section_accessibility,
                    environment,
                ) = matches[
                    0
                ]

            else:
                selected_apex = (
                    elf_context
                    .selected_apex_requirement
                )

                if selected_apex is None:
                    raise ValueError(
                        "resolved non-BASE executable loading context must "
                        "preserve one exact selected APEX requirement"
                    )

                matches = tuple(
                    (
                        accessibility,
                        candidate_environment,
                    )
                    for (
                        apex_requirement,
                        accessibility,
                        candidate_environment,
                    )
                    in apex_runtime_contexts
                    if apex_requirement
                    is selected_apex
                )

                if len(
                    matches
                ) != 1:
                    raise ValueError(
                        "resolved APEX executable must map to exactly one "
                        "post-standard accessibility section: "
                        f"matches={len(matches)}"
                    )

                (
                    section_accessibility,
                    environment,
                ) = matches[
                    0
                ]

            assert section_accessibility is not None
            assert environment is not None

            dependency_traversals.append(
                AndroidRuntimeLinkerContextualElfDependencyResolver
                .resolve(
                    loading_context=loading_context,
                    root_candidate=root_candidate,
                    section_accessibility=(
                        section_accessibility
                    ),
                    environment=environment,
                    candidates=(
                        linker_elf_runtime_candidates
                    ),
                )
            )

        linker_elf_dependency_traversals = tuple(
            dependency_traversals
        )

        if len(
            linker_elf_dependency_traversals
        ) != len(
            linker_executable_loading_contexts
        ):
            raise ValueError(
                "contextual ELF dependency traversal population must "
                "preserve one result per loading-context conclusion"
            )

        if not all(
            traversal.loading_context
            is loading_context
            for traversal, loading_context
            in zip(
                linker_elf_dependency_traversals,
                linker_executable_loading_contexts,
                strict=True,
            )
        ):
            raise ValueError(
                "contextual ELF dependency traversal population changed "
                "loading-context identity or order"
            )

        self._report_progress(
            current=14,
            total=15,
            operation="contextual ELF DT_NEEDED resolution",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=15,
            total=15,
            operation="Runtime Linking assembly",
            state=ProgressState.RUNNING,
        )

        result = AndroidRuntimeLinking(
            universe=universe,
            semantic_version=semantic_version,
            linker_generated_configuration_inputs=(
                linker_generated_configuration_inputs
            ),
            linker_variable_environments=(
                linker_variable_environments
            ),
            linker_generated_base_configurations=(
                linker_generated_base_configurations
            ),
            linker_effective_base_configurations=(
                linker_effective_base_configurations
            ),
            linker_effective_apex_configurations=(
                linker_effective_apex_configurations
            ),
            linker_provider_vocabulary_base_sections=(
                linker_provider_vocabulary_base_sections
            ),
            linker_provider_vocabulary_apex_sections=(
                linker_provider_vocabulary_apex_sections
            ),
            linker_resolved_base_sections=(
                linker_resolved_base_sections
            ),
            linker_resolved_apex_sections=(
                linker_resolved_apex_sections
            ),
            linker_standard_system_linked_base_sections=(
                linker_standard_system_linked_base_sections
            ),
            linker_standard_system_linked_apex_sections=(
                linker_standard_system_linked_apex_sections
            ),
            linker_apex_active_runtime_paths=(
                linker_apex_active_runtime_paths
            ),
            linker_apex_provider_descriptors=(
                linker_apex_provider_descriptors
            ),
            linker_section_apex_applicability=(
                linker_section_apex_applicability
            ),
            linker_executable_section_routing=(
                linker_executable_section_routing
            ),
            linker_namespace_accessibility_base_sections=(
                linker_namespace_accessibility_base_sections
            ),
            linker_namespace_accessibility_apex_sections=(
                linker_namespace_accessibility_apex_sections
            ),
            linker_executable_loading_contexts=(
                linker_executable_loading_contexts
            ),
            linker_elf_runtime_candidates=(
                linker_elf_runtime_candidates
            ),
            linker_elf_dependency_traversals=(
                linker_elf_dependency_traversals
            ),
        )

        self._report_progress(
            current=15,
            total=15,
            operation="Runtime Linking assembly",
            state=ProgressState.COMPLETE,
        )

        return result

    def _report_progress(
        self,
        *,
        current: int,
        total: int,
        operation: str,
        state: ProgressState,
    ) -> None:
        """
        Publish one semantic Runtime Linking progress observation.

        Runtime Linking owns effective linkerconfig/runtime interpretation.
        Presentation remains the responsibility of the shared caller
        progress renderer.
        """

        if self.progress_callback is None:
            return

        semantics = {
            "contextual ELF DT_NEEDED resolution": (
                "Executable loading contexts and post-standard namespaces",
                "resolving contextual ELF dependency providers",
                (
                    "starting namespaces / ordered search paths / direct "
                    "SONAME-qualified namespace links / canonical ELF "
                    "runtime paths -> contextual DT_NEEDED providers"
                ),
            ),
            "ELF runtime candidate population": (
                "Canonical Universe ELF contexts and active APEX roots",
                "projecting canonical ELF identities into runtime paths",
                (
                    "physical ELF paths / filesystem aliases / "
                    "Linker-ELF contexts -> runtime lookup candidates"
                ),
            ),
            "generated configuration inputs": (
                "Canonical Universe Linker/runtime facts",
                "deriving effective linkerconfig inputs",
                (
                    "runtime policies / properties / APEX requirements "
                    "-> generated linkerconfig input sets"
                ),
            ),
            "generated BASE topology": (
                "Generated linkerconfig input sets",
                "building effective BASE topology",
                (
                    "semantic-version linker profile / runtime inputs "
                    "-> sections / namespaces / directory routes"
                ),
            ),
            "active APEX runtime population": (
                "Canonical Universe APEX requirements",
                "selecting active runtime APEX paths",
                (
                    "runtime-local APEX versions / deployment "
                    "-> active client-visible APEX roots"
                ),
            ),
            "APEX provider population": (
                "Active APEX paths and canonical namespace inputs",
                "assembling active APEX providers",
                (
                    "APEX manifests / local Linker policy / active roots "
                    "-> runtime provider population"
                ),
            ),
            "section/APEX participation": (
                "Generated BASE sections and canonical APEX facts",
                "reconciling section/APEX participation",
                (
                    "BASE topology / JNI / public libraries / visibility "
                    "-> section-visible APEX population"
                ),
            ),
            "effective namespace population": (
                "Generated BASE sections and selected active APEX providers",
                "constructing pre-Resolve effective namespace population",
                (
                    "BASE namespaces / section APEX participation / active "
                    "providers -> BuildSection namespace population"
                ),
            ),
            "APEX effective section population": (
                "Active APEX providers / release linker semantics",
                "constructing pre-Resolve APEX linker sections",
                (
                    "APEX deployment / visibility / VNDK state -> "
                    "BuildApexDefaultSection namespace population"
                ),
            ),
            "Section::Resolve": (
                "Effective BASE and APEX linker sections",
                "resolving namespace providers and links",
                (
                    "typed requirements / concrete providers / active APEX "
                    "providers / section aliases -> resolved namespace graph"
                ),
            ),
            "AddStandardSystemLinks": (
                "Section::Resolve namespace graphs",
                "adding standard system namespace links",
                (
                    "system namespace identity / Bionic libraries / sanitizer "
                    "runtime libraries / ro.debuggable -> post-standard-link "
                    "namespace graph"
                ),
            ),
            "namespace accessibility": (
                "Post-AddStandardSystemLinks namespace graphs",
                "indexing direct SONAME-qualified namespace accessibility",
                (
                    "ordered namespace links / shared SONAME filters / "
                    "allow-all semantics -> direct bionic lookup relation"
                ),
            ),
            "executable section routing": (
                "Canonical ELF contexts and Runtime Linking topology",
                "routing executables to Linker sections",
                (
                    "ELF runtime paths / directory routes / active APEX roots "
                    "-> executable section selection"
                ),
            ),
            "starting loading contexts": (
                "Executable routing conclusions",
                "selecting starting loading contexts",
                (
                    "selected sections / APEX namespace inputs "
                    "-> starting namespace identity"
                ),
            ),
            "Runtime Linking assembly": (
                "Derived Runtime Linking semantic results",
                "assembling Runtime Linking result",
                (
                    "generated topology / APEX population / routing "
                    "-> canonical Runtime Linking result"
                ),
            ),
        }

        (
            subject,
            operation_detail,
            detail,
        ) = semantics.get(
            operation,
            (
                "Runtime Linking semantic inputs",
                operation,
                operation,
            ),
        )

        self.progress_callback(
            ProgressEvent(
                stage="Android Runtime Linking",
                state=state,
                current=current,
                total=total,
                subject=subject,
                operation=operation_detail,
                detail=detail,
            )
        )

