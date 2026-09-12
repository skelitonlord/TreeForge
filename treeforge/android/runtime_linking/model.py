from __future__ import annotations

from treeforge.android.runtime_linking.linker.provider import (
    AndroidRuntimeLinkerSectionProviderVocabulary,
)

from treeforge.android.version.model import (
    AndroidSemanticVersionSelection,
)
from treeforge.android.runtime_linking.linker.expression_resolution import (
    AndroidRuntimeLinkerVariableEnvironment,
)

from dataclasses import dataclass

from treeforge.android.runtime_linking.linker.generated_configuration import (
    AndroidUniverseLinkerGeneratedBaseConfiguration,
    AndroidUniverseLinkerGeneratedConfigurationInputs,
)
from treeforge.android.runtime_linking.linker.effective_configuration import (
    AndroidRuntimeLinkerEffectiveApexConfiguration,
    AndroidRuntimeLinkerEffectiveBaseConfiguration,
    AndroidRuntimeLinkerEffectiveSection,
)
from treeforge.android.runtime_linking.linker.elf_dependency_resolution import (
    AndroidRuntimeLinkerElfDependencyTraversal,
)

from treeforge.android.runtime_linking.linker.elf_runtime_candidate import (
    AndroidRuntimeLinkerElfRuntimeCandidate,
)

from treeforge.android.runtime_linking.linker.namespace_accessibility import (
    AndroidRuntimeLinkerSectionAccessibility,
)

from treeforge.android.runtime_linking.linker.standard_system_links import (
    AndroidRuntimeLinkerStandardSystemLinkedSection,
)

from treeforge.android.runtime_linking.linker.resolution import (
    AndroidRuntimeLinkerResolvedSection,
)
from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexProviderStatus,
    AndroidUniverseLinkerApexActiveRuntimePath,
    AndroidUniverseLinkerApexProviderDescriptor,
    AndroidUniverseLinkerExecutableLoadingContext,
    AndroidUniverseLinkerExecutableSectionRouting,
    AndroidUniverseLinkerSectionApexApplicability,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerResolvedBaseSectionResult:
    """
    One BASE Section::Resolve() result paired with the exact pre-Resolve
    effective section that produced it.
    """

    effective_section: AndroidRuntimeLinkerEffectiveSection
    resolved_section: AndroidRuntimeLinkerResolvedSection

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.effective_section,
            AndroidRuntimeLinkerEffectiveSection,
        ):
            raise TypeError(
                "effective_section has invalid type"
            )

        if not isinstance(
            self.resolved_section,
            AndroidRuntimeLinkerResolvedSection,
        ):
            raise TypeError(
                "resolved_section has invalid type"
            )

        if (
            self.resolved_section.section_name
            != self.effective_section.generated_section.name
        ):
            raise ValueError(
                "resolved BASE section name must preserve exact effective "
                "section identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerResolvedApexSectionResult:
    """
    One APEX Section::Resolve() result paired with the exact pre-Resolve
    effective APEX configuration that produced it.
    """

    effective_configuration: (
        AndroidRuntimeLinkerEffectiveApexConfiguration
    )

    resolved_section: AndroidRuntimeLinkerResolvedSection

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.effective_configuration,
            AndroidRuntimeLinkerEffectiveApexConfiguration,
        ):
            raise TypeError(
                "effective_configuration has invalid type"
            )

        if not isinstance(
            self.resolved_section,
            AndroidRuntimeLinkerResolvedSection,
        ):
            raise TypeError(
                "resolved_section has invalid type"
            )

        if (
            self.resolved_section.section_name
            != self.effective_configuration.section_name
        ):
            raise ValueError(
                "resolved APEX section name must preserve exact effective "
                "configuration identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinking:
    """
    Canonical result of Android Runtime Linking.

    Android Device Universe remains the authoritative source for canonical
    Linker/APEX/ELF requirements, associations, applicability evidence, and
    semantic inputs.

    Runtime Linking owns the effective runtime behavior derived from those
    exact canonical identities.

    ``semantic_version`` preserves the exact upstream Android semantic-version
    selection applied by this run. Runtime Linking does not own version
    selection; it conserves that exact provenance because release-specific
    linker semantics materially shape the result.

    ``linker_variable_environments`` preserves the exact derived linkerconfig
    variable environment for every generated runtime configuration so later
    Runtime Linking checkpoints do not need to rerun variable derivation.
    """

    universe: AndroidDeviceUniverse
    semantic_version: AndroidSemanticVersionSelection


    linker_generated_configuration_inputs: tuple[
        AndroidUniverseLinkerGeneratedConfigurationInputs,
        ...,
    ]

    linker_variable_environments: tuple[
        AndroidRuntimeLinkerVariableEnvironment,
        ...,
    ]

    linker_generated_base_configurations: tuple[
        AndroidUniverseLinkerGeneratedBaseConfiguration,
        ...,
    ]

    linker_effective_base_configurations: tuple[
        AndroidRuntimeLinkerEffectiveBaseConfiguration,
        ...,
    ]

    linker_effective_apex_configurations: tuple[
        AndroidRuntimeLinkerEffectiveApexConfiguration,
        ...,
    ]

    linker_provider_vocabulary_base_sections: tuple[
        AndroidRuntimeLinkerSectionProviderVocabulary,
        ...,
    ]

    linker_provider_vocabulary_apex_sections: tuple[
        AndroidRuntimeLinkerSectionProviderVocabulary,
        ...,
    ]

    linker_resolved_base_sections: tuple[
        AndroidRuntimeLinkerResolvedBaseSectionResult,
        ...,
    ]

    linker_resolved_apex_sections: tuple[
        AndroidRuntimeLinkerResolvedApexSectionResult,
        ...,
    ]

    linker_standard_system_linked_base_sections: tuple[
        AndroidRuntimeLinkerStandardSystemLinkedSection,
        ...,
    ]

    linker_standard_system_linked_apex_sections: tuple[
        AndroidRuntimeLinkerStandardSystemLinkedSection,
        ...,
    ]

    linker_apex_active_runtime_paths: tuple[
        AndroidUniverseLinkerApexActiveRuntimePath,
        ...,
    ]

    linker_apex_provider_descriptors: tuple[
        AndroidUniverseLinkerApexProviderDescriptor,
        ...,
    ]

    linker_section_apex_applicability: tuple[
        AndroidUniverseLinkerSectionApexApplicability,
        ...,
    ]

    linker_executable_section_routing: tuple[
        AndroidUniverseLinkerExecutableSectionRouting,
        ...,
    ]

    linker_namespace_accessibility_base_sections: tuple[
        AndroidRuntimeLinkerSectionAccessibility,
        ...,
    ]

    linker_namespace_accessibility_apex_sections: tuple[
        AndroidRuntimeLinkerSectionAccessibility,
        ...,
    ]

    linker_executable_loading_contexts: tuple[
        AndroidUniverseLinkerExecutableLoadingContext,
        ...,
    ]

    linker_elf_runtime_candidates: tuple[
        AndroidRuntimeLinkerElfRuntimeCandidate,
        ...,
    ]

    linker_elf_dependency_traversals: tuple[
        AndroidRuntimeLinkerElfDependencyTraversal,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.semantic_version,
            AndroidSemanticVersionSelection,
        ):
            raise TypeError(
                "semantic_version must be an "
                "AndroidSemanticVersionSelection"
            )

        if not isinstance(
            self.universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        active_apex_providers = tuple(
            provider
            for provider
            in self.linker_apex_provider_descriptors
            if (
                provider.status
                is AndroidUniverseLinkerApexProviderStatus.ACTIVE
            )
        )

        if len(
            self.linker_effective_apex_configurations
        ) != len(
            active_apex_providers
        ):
            raise ValueError(
                "effective APEX configuration count must equal "
                "ACTIVE APEX provider count"
            )

        for provider, effective in zip(
            active_apex_providers,
            self.linker_effective_apex_configurations,
            strict=True,
        ):
            if (
                effective.apex_provider
                is not provider
            ):
                raise ValueError(
                    "effective APEX configurations must preserve exact "
                    "ACTIVE provider identity and order"
                )

        for field_name, values, expected_type in (
            (
                "linker_generated_configuration_inputs",
                self.linker_generated_configuration_inputs,
                AndroidUniverseLinkerGeneratedConfigurationInputs,
            ),
            (
                "linker_variable_environments",
                self.linker_variable_environments,
                AndroidRuntimeLinkerVariableEnvironment,
            ),
            (
                "linker_generated_base_configurations",
                self.linker_generated_base_configurations,
                AndroidUniverseLinkerGeneratedBaseConfiguration,
            ),
            (
                "linker_effective_base_configurations",
                self.linker_effective_base_configurations,
                AndroidRuntimeLinkerEffectiveBaseConfiguration,
            ),
            (
                "linker_effective_apex_configurations",
                self.linker_effective_apex_configurations,
                AndroidRuntimeLinkerEffectiveApexConfiguration,
            ),
            (
                "linker_resolved_base_sections",
                self.linker_resolved_base_sections,
                AndroidRuntimeLinkerResolvedBaseSectionResult,
            ),
            (
                "linker_resolved_apex_sections",
                self.linker_resolved_apex_sections,
                AndroidRuntimeLinkerResolvedApexSectionResult,
            ),
            (
                "linker_standard_system_linked_base_sections",
                self.linker_standard_system_linked_base_sections,
                AndroidRuntimeLinkerStandardSystemLinkedSection,
            ),
            (
                "linker_standard_system_linked_apex_sections",
                self.linker_standard_system_linked_apex_sections,
                AndroidRuntimeLinkerStandardSystemLinkedSection,
            ),
            (
                "linker_apex_active_runtime_paths",
                self.linker_apex_active_runtime_paths,
                AndroidUniverseLinkerApexActiveRuntimePath,
            ),
            (
                "linker_apex_provider_descriptors",
                self.linker_apex_provider_descriptors,
                AndroidUniverseLinkerApexProviderDescriptor,
            ),
            (
                "linker_section_apex_applicability",
                self.linker_section_apex_applicability,
                AndroidUniverseLinkerSectionApexApplicability,
            ),
            (
                "linker_executable_section_routing",
                self.linker_executable_section_routing,
                AndroidUniverseLinkerExecutableSectionRouting,
            ),
            (
                "linker_namespace_accessibility_base_sections",
                self.linker_namespace_accessibility_base_sections,
                AndroidRuntimeLinkerSectionAccessibility,
            ),
            (
                "linker_namespace_accessibility_apex_sections",
                self.linker_namespace_accessibility_apex_sections,
                AndroidRuntimeLinkerSectionAccessibility,
            ),
            (
                "linker_executable_loading_contexts",
                self.linker_executable_loading_contexts,
                AndroidUniverseLinkerExecutableLoadingContext,
            ),
            (
                "linker_elf_runtime_candidates",
                self.linker_elf_runtime_candidates,
                AndroidRuntimeLinkerElfRuntimeCandidate,
            ),
            (
                "linker_elf_dependency_traversals",
                self.linker_elf_dependency_traversals,
                AndroidRuntimeLinkerElfDependencyTraversal,
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
                    value,
                    expected_type,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid object"
                )

        if len(
            self.linker_elf_dependency_traversals
        ) != len(
            self.linker_executable_loading_contexts
        ):
            raise ValueError(
                "contextual ELF dependency traversal coverage must equal "
                "Runtime Linking loading-context coverage"
            )

        if not all(
            traversal.loading_context
            is loading_context
            for traversal, loading_context
            in zip(
                self.linker_elf_dependency_traversals,
                self.linker_executable_loading_contexts,
                strict=True,
            )
        ):
            raise ValueError(
                "contextual ELF dependency traversals must preserve exact "
                "loading-context identity and order"
            )

        if len(
            self.linker_elf_runtime_candidates
        ) != len(
            self.universe.linker_elf_contexts
        ):
            raise ValueError(
                "ELF runtime candidate coverage must equal canonical "
                "Universe Linker/ELF context coverage"
            )

        if not all(
            candidate.linker_elf_context
            is context
            for candidate, context
            in zip(
                self.linker_elf_runtime_candidates,
                self.universe.linker_elf_contexts,
                strict=True,
            )
        ):
            raise ValueError(
                "ELF runtime candidates must preserve exact canonical "
                "Linker/ELF context identity and order"
            )

        if len(
            self.linker_variable_environments
        ) != len(
            self.linker_generated_configuration_inputs
        ):
            raise ValueError(
                "Runtime Linking variable-environment coverage must equal "
                "generated configuration-input coverage"
            )

        if not all(
            environment.inputs
            is inputs
            for environment, inputs
            in zip(
                self.linker_variable_environments,
                self.linker_generated_configuration_inputs,
                strict=True,
            )
        ):
            raise ValueError(
                "Runtime Linking variable environments must preserve exact "
                "generated configuration-input identity and order"
            )

        if len(
            self.linker_generated_configuration_inputs
        ) != len(
            self.linker_generated_base_configurations
        ):
            raise ValueError(
                "Runtime Linking must preserve exactly one generated "
                "BASE configuration per generated input set"
            )

        if not all(
            configuration.inputs
            is inputs
            for configuration, inputs
            in zip(
                self.linker_generated_base_configurations,
                self.linker_generated_configuration_inputs,
                strict=True,
            )
        ):
            raise ValueError(
                "generated BASE configurations must preserve exact "
                "generated-input identity and order"
            )

        if len(
            self.linker_effective_base_configurations
        ) != len(
            self.linker_generated_base_configurations
        ):
            raise ValueError(
                "Runtime Linking must preserve exactly one effective "
                "pre-Resolve configuration per generated BASE configuration"
            )

        if not all(
            effective.generated_configuration
            is generated
            for effective, generated
            in zip(
                self.linker_effective_base_configurations,
                self.linker_generated_base_configurations,
                strict=True,
            )
        ):
            raise ValueError(
                "effective configurations must preserve exact generated "
                "BASE configuration identity and order"
            )

        expected_effective_base_sections = tuple(
            section
            for configuration
            in self.linker_effective_base_configurations
            for section
            in configuration.sections
        )

        if len(
            self.linker_resolved_base_sections
        ) != len(
            expected_effective_base_sections
        ):
            raise ValueError(
                "resolved BASE section coverage must equal every effective "
                "pre-Resolve BASE section"
            )

        if not all(
            result.effective_section
            is effective_section
            for result, effective_section
            in zip(
                self.linker_resolved_base_sections,
                expected_effective_base_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "resolved BASE sections must preserve exact effective "
                "section identity and order"
            )

        if len(
            self.linker_resolved_apex_sections
        ) != len(
            self.linker_effective_apex_configurations
        ):
            raise ValueError(
                "resolved APEX section coverage must equal every effective "
                "pre-Resolve APEX configuration"
            )

        if not all(
            result.effective_configuration
            is effective_configuration
            for result, effective_configuration
            in zip(
                self.linker_resolved_apex_sections,
                self.linker_effective_apex_configurations,
                strict=True,
            )
        ):
            raise ValueError(
                "resolved APEX sections must preserve exact effective "
                "configuration identity and order"
            )

        if len(
            self.linker_standard_system_linked_base_sections
        ) != len(
            self.linker_resolved_base_sections
        ):
            raise ValueError(
                "standard-system-linked BASE coverage must equal "
                "resolved BASE section coverage"
            )

        if not all(
            linked.source_section
            is resolved.resolved_section
            for linked, resolved
            in zip(
                self.linker_standard_system_linked_base_sections,
                self.linker_resolved_base_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "standard-system-linked BASE sections must preserve exact "
                "Section::Resolve identity and order"
            )

        if len(
            self.linker_standard_system_linked_apex_sections
        ) != len(
            self.linker_resolved_apex_sections
        ):
            raise ValueError(
                "standard-system-linked APEX coverage must equal "
                "resolved APEX section coverage"
            )

        if not all(
            linked.source_section
            is resolved.resolved_section
            for linked, resolved
            in zip(
                self.linker_standard_system_linked_apex_sections,
                self.linker_resolved_apex_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "standard-system-linked APEX sections must preserve exact "
                "Section::Resolve identity and order"
            )

        if len(
            self.linker_namespace_accessibility_base_sections
        ) != len(
            self.linker_standard_system_linked_base_sections
        ):
            raise ValueError(
                "BASE namespace accessibility coverage must equal "
                "post-standard-link BASE coverage"
            )

        if not all(
            accessibility.source
            is standard
            for accessibility, standard
            in zip(
                self.linker_namespace_accessibility_base_sections,
                self.linker_standard_system_linked_base_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "BASE namespace accessibility must preserve exact "
                "post-standard-link identity and order"
            )

        if len(
            self.linker_namespace_accessibility_apex_sections
        ) != len(
            self.linker_standard_system_linked_apex_sections
        ):
            raise ValueError(
                "APEX namespace accessibility coverage must equal "
                "post-standard-link APEX coverage"
            )

        if not all(
            accessibility.source
            is standard
            for accessibility, standard
            in zip(
                self.linker_namespace_accessibility_apex_sections,
                self.linker_standard_system_linked_apex_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "APEX namespace accessibility must preserve exact "
                "post-standard-link identity and order"
            )

        #
        # Active APEX runtime-path conservation.
        #
        # The reconciler intentionally sorts by runtime_path_id rather than
        # preserving Universe APEX tuple order. The root therefore requires
        # exact canonical APEX coverage plus deterministic result order.
        #
        if len(
            self.linker_apex_active_runtime_paths
        ) != len(
            self.universe.apex_requirements
        ):
            raise ValueError(
                "Runtime Linking active APEX path coverage must equal "
                "canonical Universe APEX coverage"
            )

        canonical_apex_identity = {
            id(
                requirement
            )
            for requirement
            in self.universe.apex_requirements
        }

        active_path_apex_identity = {
            id(
                item.apex_requirement
            )
            for item
            in self.linker_apex_active_runtime_paths
        }

        if (
            active_path_apex_identity
            != canonical_apex_identity
        ):
            raise ValueError(
                "Runtime Linking active APEX paths must preserve exact "
                "Universe APEX requirement identities"
            )

        active_runtime_path_ids = tuple(
            item.runtime_path_id
            for item
            in self.linker_apex_active_runtime_paths
        )

        if (
            active_runtime_path_ids
            != tuple(
                sorted(
                    active_runtime_path_ids
                )
            )
        ):
            raise ValueError(
                "Runtime Linking active APEX paths must preserve "
                "canonical runtime-path-id order"
            )

        #
        # APEX provider-descriptor conservation.
        #
        # Provider descriptors are independently sorted by descriptor_id,
        # which is derived from the same exact APEX requirement identity as
        # runtime_path_id. Preserve complete APEX coverage and the exact
        # active-runtime-path object selected for every descriptor.
        #
        if len(
            self.linker_apex_provider_descriptors
        ) != len(
            self.universe.apex_requirements
        ):
            raise ValueError(
                "Runtime Linking provider descriptor coverage must equal "
                "canonical Universe APEX coverage"
            )

        provider_apex_identity = {
            id(
                provider.apex_requirement
            )
            for provider
            in self.linker_apex_provider_descriptors
        }

        if (
            provider_apex_identity
            != canonical_apex_identity
        ):
            raise ValueError(
                "Runtime Linking provider descriptors must preserve exact "
                "Universe APEX requirement identities"
            )

        provider_descriptor_ids = tuple(
            provider.descriptor_id
            for provider
            in self.linker_apex_provider_descriptors
        )

        if (
            provider_descriptor_ids
            != tuple(
                sorted(
                    provider_descriptor_ids
                )
            )
        ):
            raise ValueError(
                "Runtime Linking provider descriptors must preserve "
                "canonical descriptor-id order"
            )

        if not all(
            provider.apex_requirement
            is active_path.apex_requirement
            and provider.active_runtime_path
            is active_path
            for provider, active_path
            in zip(
                self.linker_apex_provider_descriptors,
                self.linker_apex_active_runtime_paths,
                strict=True,
            )
        ):
            raise ValueError(
                "Runtime Linking provider descriptors must preserve the "
                "exact canonically ordered active APEX runtime-path "
                "population"
            )

        canonical_namespace_input_identity = {
            id(
                namespace_input
            )
            for namespace_input
            in self.universe.linker_apex_namespace_inputs
        }

        if not all(
            id(
                provider.namespace_input
            )
            in canonical_namespace_input_identity
            for provider
            in self.linker_apex_provider_descriptors
        ):
            raise ValueError(
                "Runtime Linking provider descriptors must preserve exact "
                "Universe APEX namespace-input identities"
            )

        #
        # Section/APEX applicability conservation.
        #
        # Reconciliation emits exactly one conclusion for every
        # generated-BASE-section / same-runtime-APEX pair, then sorts the
        # resulting population by conclusion_id.
        #
        expected_section_apex_identity = tuple(
            (
                id(
                    base_configuration
                ),
                id(
                    section
                ),
                id(
                    apex_requirement
                ),
            )
            for base_configuration
            in self.linker_generated_base_configurations
            for section
            in base_configuration.sections
            for apex_requirement
            in self.universe.apex_requirements
            if apex_requirement.shares_runtime(
                base_configuration
                .inputs
                .runtime_policy
                .runtime_context
            )
        )

        actual_section_apex_identity = tuple(
            (
                id(
                    conclusion.base_configuration
                ),
                id(
                    conclusion.section
                ),
                id(
                    conclusion.apex_requirement
                ),
            )
            for conclusion
            in self.linker_section_apex_applicability
        )

        if len(
            actual_section_apex_identity
        ) != len(
            expected_section_apex_identity
        ):
            raise ValueError(
                "Runtime Linking section/APEX applicability coverage must "
                "equal every generated BASE section / same-runtime APEX "
                "combination"
            )

        if (
            set(
                actual_section_apex_identity
            )
            != set(
                expected_section_apex_identity
            )
        ):
            raise ValueError(
                "Runtime Linking section/APEX applicability must preserve "
                "exact generated BASE configuration, section, and APEX "
                "identities"
            )

        applicability_ids = tuple(
            conclusion.conclusion_id
            for conclusion
            in self.linker_section_apex_applicability
        )

        if (
            applicability_ids
            != tuple(
                sorted(
                    applicability_ids
                )
            )
        ):
            raise ValueError(
                "Runtime Linking section/APEX applicability must preserve "
                "canonical conclusion-id order"
            )

        canonical_public_library_identity = {
            id(
                conclusion
            )
            for conclusion
            in (
                self.universe
                .linker_apex_public_library_conclusions
            )
        }

        if not all(
            id(
                conclusion.namespace_input
            )
            in canonical_namespace_input_identity
            for conclusion
            in self.linker_section_apex_applicability
        ):
            raise ValueError(
                "Runtime Linking section/APEX applicability must preserve "
                "exact Universe namespace-input identities"
            )

        if not all(
            id(
                conclusion.public_library_conclusion
            )
            in canonical_public_library_identity
            for conclusion
            in self.linker_section_apex_applicability
        ):
            raise ValueError(
                "Runtime Linking section/APEX applicability must preserve "
                "exact Universe public-library conclusion identities"
            )

        #
        # Executable routing remains a one-result-per-canonical-ELF-context
        # ordered population.
        #
        if len(
            self.linker_executable_section_routing
        ) != len(
            self.universe.linker_elf_contexts
        ):
            raise ValueError(
                "Runtime Linking executable routing must cover every "
                "canonical Universe Linker/ELF context"
            )

        if not all(
            routing.elf_context
            is context
            for routing, context
            in zip(
                self.linker_executable_section_routing,
                self.universe.linker_elf_contexts,
                strict=True,
            )
        ):
            raise ValueError(
                "Runtime Linking executable routing must preserve exact "
                "Universe Linker/ELF context identity and order"
            )

        #
        # Loading-context reconciliation is also one result per routing.
        # Its loading_context_id is derived from the exact routing ELF
        # context, so preserve exact routing identity and order rather than
        # merely requiring membership somewhere in the routing population.
        #
        if len(
            self.linker_executable_loading_contexts
        ) != len(
            self.linker_executable_section_routing
        ):
            raise ValueError(
                "Runtime Linking loading contexts must cover every "
                "executable-routing conclusion"
            )

        if not all(
            loading_context.routing
            is routing
            for loading_context, routing
            in zip(
                self.linker_executable_loading_contexts,
                self.linker_executable_section_routing,
                strict=True,
            )
        ):
            raise ValueError(
                "Runtime Linking loading contexts must preserve exact "
                "executable-routing identity and order"
            )

        #
        # Section::Resolve provider-vocabulary conservation.
        #
        # These populations preserve the complete concrete/APEX/alias
        # candidate vocabulary supplied to Section::Resolve(). Their order
        # is the exact effective BASE-section / APEX-configuration order.
        #
        for field_name, values in (
            (
                "linker_provider_vocabulary_base_sections",
                self.linker_provider_vocabulary_base_sections,
            ),
            (
                "linker_provider_vocabulary_apex_sections",
                self.linker_provider_vocabulary_apex_sections,
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
                    value,
                    AndroidRuntimeLinkerSectionProviderVocabulary,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} contains invalid values"
                )

        expected_base_sections = tuple(
            section
            for configuration
            in self.linker_effective_base_configurations
            for section
            in configuration.sections
        )

        if len(
            self.linker_provider_vocabulary_base_sections
        ) != len(
            expected_base_sections
        ):
            raise ValueError(
                "Runtime Linking BASE provider-vocabulary coverage must "
                "equal effective BASE section coverage"
            )

        for vocabulary, effective_section in zip(
            self.linker_provider_vocabulary_base_sections,
            expected_base_sections,
            strict=True,
        ):
            if (
                vocabulary.section_name
                != effective_section.generated_section.name
            ):
                raise ValueError(
                    "Runtime Linking BASE provider vocabulary must preserve "
                    "exact effective-section order and section identity"
                )

            namespace_identity = {
                id(
                    namespace
                )
                for namespace
                in effective_section.namespaces
            }

            if not all(
                id(
                    provider.namespace
                )
                in namespace_identity
                for provider
                in vocabulary.concrete_library_providers
            ):
                raise ValueError(
                    "Runtime Linking BASE concrete provider vocabulary "
                    "must reference only exact effective-section namespaces"
                )

            inputs = (
                effective_section
                .generated_section
                .configuration
                .inputs
                if hasattr(
                    effective_section.generated_section,
                    "configuration",
                )
                else None
            )

            #
            # The generated section need not expose a parent configuration;
            # exact runtime APEX-provider coverage is checked independently
            # below from the corresponding effective BASE configuration.
            #
            del inputs

        if len(
            self.linker_provider_vocabulary_apex_sections
        ) != len(
            self.linker_effective_apex_configurations
        ):
            raise ValueError(
                "Runtime Linking APEX provider-vocabulary coverage must "
                "equal effective APEX configuration coverage"
            )

        for vocabulary, effective_configuration in zip(
            self.linker_provider_vocabulary_apex_sections,
            self.linker_effective_apex_configurations,
            strict=True,
        ):
            if (
                vocabulary.section_name
                != effective_configuration.section_name
            ):
                raise ValueError(
                    "Runtime Linking APEX provider vocabulary must preserve "
                    "exact effective-configuration order and section identity"
                )

            namespace_identity = {
                id(
                    namespace
                )
                for namespace
                in effective_configuration.namespaces
            }

            if not all(
                id(
                    provider.namespace
                )
                in namespace_identity
                for provider
                in vocabulary.concrete_library_providers
            ):
                raise ValueError(
                    "Runtime Linking APEX concrete provider vocabulary "
                    "must reference only exact effective-configuration "
                    "namespaces"
                )

        #
        # Every provider vocabulary must preserve exactly the ACTIVE APEX
        # library-provider population belonging to its runtime context.
        #
        expected_base_vocabulary_index = 0

        for effective_configuration in (
            self.linker_effective_base_configurations
        ):
            runtime_context = (
                effective_configuration
                .generated_configuration
                .inputs
                .runtime_policy
                .runtime_context
            )

            expected_apex_provider_pairs = tuple(
                (
                    provider,
                    library_name,
                )
                for provider
                in self.linker_apex_provider_descriptors
                if (
                    provider.status
                    is AndroidUniverseLinkerApexProviderStatus.ACTIVE
                    and provider.apex_requirement.shares_runtime(
                        runtime_context
                    )
                )
                for library_name
                in provider.provided_libraries
            )

            for _ in effective_configuration.sections:
                vocabulary = (
                    self
                    .linker_provider_vocabulary_base_sections[
                        expected_base_vocabulary_index
                    ]
                )

                actual_apex_provider_pairs = tuple(
                    (
                        item.apex_provider,
                        item.library_name,
                    )
                    for item
                    in vocabulary.apex_library_providers
                )

                if len(
                    actual_apex_provider_pairs
                ) != len(
                    expected_apex_provider_pairs
                ):
                    raise ValueError(
                        "Runtime Linking BASE provider vocabulary changed "
                        "runtime APEX provider coverage"
                    )

                if not all(
                    actual_provider
                    is expected_provider
                    and actual_library
                    == expected_library
                    for (
                        actual_provider,
                        actual_library,
                    ), (
                        expected_provider,
                        expected_library,
                    )
                    in zip(
                        actual_apex_provider_pairs,
                        expected_apex_provider_pairs,
                        strict=True,
                    )
                ):
                    raise ValueError(
                        "Runtime Linking BASE provider vocabulary changed "
                        "exact runtime APEX provider identity or order"
                    )

                expected_base_vocabulary_index += 1

        if (
            expected_base_vocabulary_index
            != len(
                self.linker_provider_vocabulary_base_sections
            )
        ):
            raise ValueError(
                "Runtime Linking BASE provider-vocabulary traversal did "
                "not consume the complete canonical population"
            )

        for vocabulary, effective_configuration in zip(
            self.linker_provider_vocabulary_apex_sections,
            self.linker_effective_apex_configurations,
            strict=True,
        ):
            runtime_context = (
                effective_configuration
                .runtime_inputs
                .runtime_policy
                .runtime_context
            )

            expected_apex_provider_pairs = tuple(
                (
                    provider,
                    library_name,
                )
                for provider
                in self.linker_apex_provider_descriptors
                if (
                    provider.status
                    is AndroidUniverseLinkerApexProviderStatus.ACTIVE
                    and provider.apex_requirement.shares_runtime(
                        runtime_context
                    )
                )
                for library_name
                in provider.provided_libraries
            )

            actual_apex_provider_pairs = tuple(
                (
                    item.apex_provider,
                    item.library_name,
                )
                for item
                in vocabulary.apex_library_providers
            )

            if len(
                actual_apex_provider_pairs
            ) != len(
                expected_apex_provider_pairs
            ):
                raise ValueError(
                    "Runtime Linking APEX provider vocabulary changed "
                    "runtime APEX provider coverage"
                )

            if not all(
                actual_provider
                is expected_provider
                and actual_library
                == expected_library
                for (
                    actual_provider,
                    actual_library,
                ), (
                    expected_provider,
                    expected_library,
                )
                in zip(
                    actual_apex_provider_pairs,
                    expected_apex_provider_pairs,
                    strict=True,
                )
            ):
                raise ValueError(
                    "Runtime Linking APEX provider vocabulary changed "
                    "exact runtime APEX provider identity or order"
                )

        if len(
            self.linker_provider_vocabulary_base_sections
        ) != len(
            self.linker_resolved_base_sections
        ):
            raise ValueError(
                "Runtime Linking BASE provider vocabulary must preserve "
                "one exact pre-resolution checkpoint per resolved section"
            )

        if not all(
            vocabulary.section_name
            == resolved.resolved_section.section_name
            for vocabulary, resolved
            in zip(
                self.linker_provider_vocabulary_base_sections,
                self.linker_resolved_base_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "Runtime Linking BASE provider vocabulary -> resolution "
                "order changed"
            )

        if len(
            self.linker_provider_vocabulary_apex_sections
        ) != len(
            self.linker_resolved_apex_sections
        ):
            raise ValueError(
                "Runtime Linking APEX provider vocabulary must preserve "
                "one exact pre-resolution checkpoint per resolved section"
            )

        if not all(
            vocabulary.section_name
            == resolved.resolved_section.section_name
            for vocabulary, resolved
            in zip(
                self.linker_provider_vocabulary_apex_sections,
                self.linker_resolved_apex_sections,
                strict=True,
            )
        ):
            raise ValueError(
                "Runtime Linking APEX provider vocabulary -> resolution "
                "order changed"
            )
