from __future__ import annotations

from treeforge.android.runtime_linking.linker.apex_identity import (
    AndroidRuntimeLinkerApexIdentity,
)

from treeforge.android.runtime_linking.linker.apex_deployment import (
    AndroidRuntimeLinkerApexDeploymentSemantics,
)

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.runtime_linking.linker.expression import (
    AndroidRuntimeLinkerLibraryExpression,
    AndroidRuntimeLinkerNamespaceLinkIntent,
    literal_library,
    namespace_link_intent,
    variable_library,
)
from treeforge.android.runtime_linking.linker.generated_configuration import (
    AndroidUniverseLinkerGeneratedBaseConfiguration,
    AndroidUniverseLinkerGeneratedNamespace,
    AndroidUniverseLinkerGeneratedSection,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexProviderDescriptor,
    AndroidUniverseLinkerApexProviderStatus,
    AndroidUniverseLinkerSectionApexApplicability,
    AndroidUniverseLinkerSectionApexApplicabilityReason,
    AndroidUniverseLinkerSectionApexApplicabilityStatus,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.version.model import (
    AndroidSemanticVersionProfile,
)


class AndroidRuntimeLinkerEffectiveConfigurationStatus(
    StrEnum
):
    """
    Resolution state of one pre-Section::Resolve() effective configuration.

    RESOLVED means BuildSection namespace population is completely known.

    AMBIGUOUS and UNRESOLVED preserve uncertainty in canonical APEX
    participation/provider inputs rather than guessing namespace population.

    This status is Runtime Linking semantic state. It is not a
    Reconstruction Planning obligation/status.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerConstructedNamespace:
    """
    One linker namespace constructed directly by Runtime Linking rather than
    inherited from a generated BASE section.

    Library requirements/provisions and namespace links use the same typed
    expression vocabulary as generated linker configuration. Literal SONAMEs,
    provider aliases, and symbolic linker variables therefore remain
    semantically distinct before Section::Resolve().
    """

    name: str
    is_isolated: bool
    is_visible: bool

    search_paths: tuple[
        str,
        ...,
    ] = ()

    permitted_paths: tuple[
        str,
        ...,
    ] = ()

    provided_libraries: tuple[
        AndroidRuntimeLinkerLibraryExpression,
        ...,
    ] = ()

    required_libraries: tuple[
        AndroidRuntimeLinkerLibraryExpression,
        ...,
    ] = ()

    link_intents: tuple[
        AndroidRuntimeLinkerNamespaceLinkIntent,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "name must be a non-empty string"
            )

        if not isinstance(
            self.is_isolated,
            bool,
        ):
            raise TypeError(
                "is_isolated must be a bool"
            )

        if not isinstance(
            self.is_visible,
            bool,
        ):
            raise TypeError(
                "is_visible must be a bool"
            )

        for field_name in (
            "search_paths",
            "permitted_paths",
            "provided_libraries",
            "required_libraries",
            "link_intents",
        ):
            if not isinstance(
                getattr(
                    self,
                    field_name,
                ),
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

        for field_name in (
            "search_paths",
            "permitted_paths",
        ):
            values = getattr(
                self,
                field_name,
            )

            if not all(
                isinstance(
                    value,
                    str,
                )
                and value
                for value
                in values
            ):
                raise ValueError(
                    f"{field_name} must contain only non-empty strings"
                )

        for field_name in (
            "provided_libraries",
            "required_libraries",
        ):
            if not all(
                isinstance(
                    expression,
                    AndroidRuntimeLinkerLibraryExpression,
                )
                for expression
                in getattr(
                    self,
                    field_name,
                )
            ):
                raise TypeError(
                    f"{field_name} must contain typed library expressions"
                )

        if not all(
            isinstance(
                intent,
                AndroidRuntimeLinkerNamespaceLinkIntent,
            )
            for intent
            in self.link_intents
        ):
            raise TypeError(
                "link_intents must contain typed namespace-link intents"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerEffectiveNamespace:
    """
    One namespace after Android BuildSection() visible-APEX population and
    immediately before Section::Resolve().

    Exactly one primary namespace origin is preserved:

    - ``generated_namespace`` for a namespace already created by the section
      builder; or
    - ``apex_provider`` for an APEX namespace appended by BuildSection().

    When a visible APEX has the same namespace name as an already-generated
    namespace, Android does not replace or reinitialize that namespace.
    BuildSection() only calls SetVisible(true). That exact semantic is
    represented by ``visibility_override_apex_provider``.

    No provider resolution, namespace-link synthesis, alias expansion,
    namespace sorting, ELF resolution, source ownership, reconstruction
    planning, or materialization occurs here.
    """

    index: int

    generated_namespace: (
        AndroidUniverseLinkerGeneratedNamespace
        | None
    ) = None

    constructed_namespace: (
        AndroidRuntimeLinkerConstructedNamespace
        | None
    ) = None

    apex_provider: (
        AndroidUniverseLinkerApexProviderDescriptor
        | None
    ) = None

    apex_provider_visible: bool = True

    visibility_override_apex_provider: (
        AndroidUniverseLinkerApexProviderDescriptor
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        primary_origins = (
            self.generated_namespace is not None,
            self.constructed_namespace is not None,
            self.apex_provider is not None,
        )

        if sum(
            primary_origins
        ) != 1:
            raise ValueError(
                "effective namespace must preserve exactly one primary "
                "generated, constructed, or APEX-provider origin"
            )

        if (
            self.generated_namespace is not None
            and not isinstance(
                self.generated_namespace,
                AndroidUniverseLinkerGeneratedNamespace,
            )
        ):
            raise TypeError(
                "generated_namespace has invalid type"
            )

        if (
            self.constructed_namespace is not None
            and not isinstance(
                self.constructed_namespace,
                AndroidRuntimeLinkerConstructedNamespace,
            )
        ):
            raise TypeError(
                "constructed_namespace has invalid type"
            )

        if not isinstance(
            self.apex_provider_visible,
            bool,
        ):
            raise TypeError(
                "apex_provider_visible must be a bool"
            )

        if (
            self.apex_provider is None
            and self.apex_provider_visible is not True
        ):
            raise ValueError(
                "apex_provider_visible may differ from true only for "
                "an APEX-provider namespace"
            )

        if (
            self.apex_provider is not None
            and not isinstance(
                self.apex_provider,
                AndroidUniverseLinkerApexProviderDescriptor,
            )
        ):
            raise TypeError(
                "apex_provider has invalid type"
            )

        if (
            self.visibility_override_apex_provider
            is not None
            and not isinstance(
                self.visibility_override_apex_provider,
                AndroidUniverseLinkerApexProviderDescriptor,
            )
        ):
            raise TypeError(
                "visibility_override_apex_provider has invalid type"
            )

        if self.apex_provider is not None:
            if (
                self.apex_provider.status
                is not AndroidUniverseLinkerApexProviderStatus.ACTIVE
            ):
                raise ValueError(
                    "injected APEX namespace requires ACTIVE provider"
                )

            if (
                self.visibility_override_apex_provider
                is not None
            ):
                raise ValueError(
                    "injected APEX namespace cannot also be a generated "
                    "namespace visibility override"
                )

        if (
            self.visibility_override_apex_provider
            is not None
        ):
            if self.generated_namespace is None:
                raise ValueError(
                    "visibility override applies only to an existing "
                    "generated namespace"
                )

            if (
                self.visibility_override_apex_provider.status
                is not AndroidUniverseLinkerApexProviderStatus.ACTIVE
            ):
                raise ValueError(
                    "visibility override requires ACTIVE APEX provider"
                )

            if (
                self.visibility_override_apex_provider.namespace_name
                != self.generated_namespace.name
            ):
                raise ValueError(
                    "visibility override APEX namespace name must match "
                    "the exact generated namespace name"
                )

    @property
    def name(
        self,
    ) -> str:
        if self.generated_namespace is not None:
            return self.generated_namespace.name

        if self.constructed_namespace is not None:
            return self.constructed_namespace.name

        assert self.apex_provider is not None
        assert self.apex_provider.namespace_name is not None

        return self.apex_provider.namespace_name

    @property
    def is_isolated(
        self,
    ) -> bool:
        if self.generated_namespace is not None:
            return self.generated_namespace.is_isolated

        if self.constructed_namespace is not None:
            return self.constructed_namespace.is_isolated

        # BaseContext::BuildApexNamespace(...):
        # Namespace(apex_info.namespace_name, true, visible)
        return True

    @property
    def is_visible(
        self,
    ) -> bool:
        if self.apex_provider is not None:
            return self.apex_provider_visible

        if self.constructed_namespace is not None:
            return self.constructed_namespace.is_visible

        assert self.generated_namespace is not None

        return (
            self.generated_namespace.is_visible
            or self.visibility_override_apex_provider is not None
        )

    @property
    def injected_apex(
        self,
    ) -> bool:
        return self.apex_provider is not None

    @property
    def apex_search_paths(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Exact InitializeWithApex() search-path population.

        Generated namespaces preserve their existing typed path objects and
        therefore expose no APEX-derived paths through this property.
        """

        if self.apex_provider is None:
            return ()

        root = self.apex_provider.active_root

        if root is None:
            raise ValueError(
                "ACTIVE APEX provider must have active_root"
            )

        base = root.as_posix()

        paths = [
            f"{base}/${{LIB}}",
        ]

        if self.apex_provider.in_vendor:
            paths.append(
                f"{base}/${{LIB}}/hw"
            )

        return tuple(
            paths
        )

    @property
    def apex_permitted_paths(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Exact Android 15 InitializeWithApex() permitted-path order.
        """

        if self.apex_provider is None:
            return ()

        root = self.apex_provider.active_root

        if root is None:
            raise ValueError(
                "ACTIVE APEX provider must have active_root"
            )

        paths = [
            f"{root.as_posix()}/${{LIB}}",
            "/system/${LIB}",
            "/system_ext/${LIB}",
            *self.apex_provider.permitted_paths,
        ]

        if self.apex_provider.has_shared_lib:
            paths.append(
                "/apex"
            )

        return tuple(
            paths
        )

    @property
    def apex_provided_libraries(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        if self.apex_provider is None:
            return ()

        return self.apex_provider.provided_libraries

    @property
    def apex_required_libraries(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        if self.apex_provider is None:
            return ()

        return self.apex_provider.required_libraries


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerEffectiveSection:
    """
    One generated BASE section after BuildSection() visible-APEX injection and
    before Section::Resolve().

    Namespace order here intentionally preserves BuildSection construction
    order. Android sorts namespaces only at the end of Section::Resolve();
    this model must therefore not sort them.
    """

    base_configuration: (
        AndroidUniverseLinkerGeneratedBaseConfiguration
    )

    generated_section: AndroidUniverseLinkerGeneratedSection

    namespaces: tuple[
        AndroidRuntimeLinkerEffectiveNamespace,
        ...,
    ]

    status: AndroidRuntimeLinkerEffectiveConfigurationStatus

    unresolved_reasons: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.base_configuration,
            AndroidUniverseLinkerGeneratedBaseConfiguration,
        ):
            raise TypeError(
                "base_configuration has invalid type"
            )

        if not isinstance(
            self.generated_section,
            AndroidUniverseLinkerGeneratedSection,
        ):
            raise TypeError(
                "generated_section has invalid type"
            )

        if not any(
            section is self.generated_section
            for section
            in self.base_configuration.sections
        ):
            raise ValueError(
                "generated_section must preserve exact BASE section identity"
            )

        if not isinstance(
            self.namespaces,
            tuple,
        ):
            raise TypeError(
                "namespaces must be a tuple"
            )

        if not all(
            isinstance(
                namespace,
                AndroidRuntimeLinkerEffectiveNamespace,
            )
            for namespace
            in self.namespaces
        ):
            raise TypeError(
                "namespaces contains invalid object"
            )

        if tuple(
            namespace.index
            for namespace
            in self.namespaces
        ) != tuple(
            range(
                len(
                    self.namespaces
                )
            )
        ):
            raise ValueError(
                "effective namespaces must preserve construction order"
            )

        generated_count = len(
            self.generated_section.namespaces
        )

        if len(
            self.namespaces
        ) < generated_count:
            raise ValueError(
                "effective section cannot lose generated BASE namespaces"
            )

        for index, generated in enumerate(
            self.generated_section.namespaces
        ):
            effective = self.namespaces[
                index
            ]

            if (
                effective.generated_namespace
                is not generated
            ):
                raise ValueError(
                    "effective section must preserve every generated BASE "
                    "namespace by exact identity and original order"
                )

        names = tuple(
            namespace.name
            for namespace
            in self.namespaces
        )

        if len(
            names
        ) != len(
            set(
                names
            )
        ):
            raise ValueError(
                "effective namespace names must remain unique"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerEffectiveConfigurationStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if not isinstance(
            self.unresolved_reasons,
            tuple,
        ):
            raise TypeError(
                "unresolved_reasons must be a tuple"
            )

        if not all(
            isinstance(
                reason,
                str,
            )
            and reason
            for reason
            in self.unresolved_reasons
        ):
            raise ValueError(
                "unresolved_reasons must contain non-empty strings"
            )

        if (
            self.status
            is AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
            and self.unresolved_reasons
        ):
            raise ValueError(
                "resolved effective section cannot carry unresolved reasons"
            )

        if (
            self.status
            is not AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
            and not self.unresolved_reasons
        ):
            raise ValueError(
                "non-resolved effective section must explain why"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerEffectiveBaseConfiguration:
    """
    Runtime Linking checkpoint immediately before Section::Resolve().

    It preserves the exact generated BASE configuration and section identities
    while constructing only BuildSection's visible-APEX namespace population.
    """

    generated_configuration: (
        AndroidUniverseLinkerGeneratedBaseConfiguration
    )

    sections: tuple[
        AndroidRuntimeLinkerEffectiveSection,
        ...,
    ]

    status: AndroidRuntimeLinkerEffectiveConfigurationStatus

    unresolved_reasons: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.generated_configuration,
            AndroidUniverseLinkerGeneratedBaseConfiguration,
        ):
            raise TypeError(
                "generated_configuration has invalid type"
            )

        if not isinstance(
            self.sections,
            tuple,
        ):
            raise TypeError(
                "sections must be a tuple"
            )

        if len(
            self.sections
        ) != len(
            self.generated_configuration.sections
        ):
            raise ValueError(
                "effective configuration must preserve every generated "
                "section exactly once"
            )

        if not all(
            effective.generated_section is generated
            for effective, generated
            in zip(
                self.sections,
                self.generated_configuration.sections,
                strict=True,
            )
        ):
            raise ValueError(
                "effective configuration must preserve exact generated "
                "section identity and order"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerEffectiveConfigurationStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if not isinstance(
            self.unresolved_reasons,
            tuple,
        ):
            raise TypeError(
                "unresolved_reasons must be a tuple"
            )

        if (
            self.status
            is AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
            and self.unresolved_reasons
        ):
            raise ValueError(
                "resolved effective configuration cannot carry "
                "unresolved reasons"
            )

        if (
            self.status
            is not AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
            and not self.unresolved_reasons
        ):
            raise ValueError(
                "non-resolved effective configuration must explain why"
            )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerEffectiveApexConfiguration:
    """
    One Android APEX linker configuration immediately before
    Section::Resolve().

    The target APEX provider preserves exact canonical APEX identity.
    Namespace order is BuildApexDefaultSection()/BuildSection construction
    order and must not yet be sorted.
    """

    apex_provider: AndroidUniverseLinkerApexProviderDescriptor

    runtime_inputs: object

    section_name: str

    namespaces: tuple[
        AndroidRuntimeLinkerEffectiveNamespace,
        ...,
    ]

    status: AndroidRuntimeLinkerEffectiveConfigurationStatus

    unresolved_reasons: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.apex_provider,
            AndroidUniverseLinkerApexProviderDescriptor,
        ):
            raise TypeError(
                "apex_provider has invalid type"
            )

        if (
            self.apex_provider.status
            is not AndroidUniverseLinkerApexProviderStatus.ACTIVE
        ):
            raise ValueError(
                "effective APEX configuration requires ACTIVE provider"
            )

        expected_name = (
            AndroidRuntimeLinkerApexIdentity.section_name(self.apex_provider.apex_requirement)
        )

        if self.section_name != expected_name:
            raise ValueError(
                "APEX section name must equal canonical APEX manifest name"
            )

        if not isinstance(
            self.namespaces,
            tuple,
        ):
            raise TypeError(
                "namespaces must be a tuple"
            )

        if not self.namespaces:
            raise ValueError(
                "effective APEX configuration requires namespaces"
            )

        if tuple(
            namespace.index
            for namespace
            in self.namespaces
        ) != tuple(
            range(
                len(
                    self.namespaces
                )
            )
        ):
            raise ValueError(
                "APEX namespaces must preserve construction order"
            )

        if self.namespaces[
            0
        ].name != "default":
            raise ValueError(
                "APEX section must begin with default namespace"
            )

        if len(
            {
                namespace.name
                for namespace
                in self.namespaces
            }
        ) != len(
            self.namespaces
        ):
            raise ValueError(
                "APEX effective namespace names must remain unique"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerEffectiveConfigurationStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if (
            self.status
            is AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
            and self.unresolved_reasons
        ):
            raise ValueError(
                "resolved APEX configuration cannot carry unresolved reasons"
            )

        if (
            self.status
            is not AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
            and not self.unresolved_reasons
        ):
            raise ValueError(
                "non-resolved APEX configuration must explain why"
            )


class AndroidRuntimeLinkerEffectiveApexConfigurationBuilder:
    """
    Reproduce Android BuildApexDefaultSection() + BuildSection() namespace
    population only.

    This intentionally stops before Section::Resolve().
    """

    @staticmethod
    def _runtime_inputs_for(
        *,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
        generated_base_configurations: tuple[
            AndroidUniverseLinkerGeneratedBaseConfiguration,
            ...,
        ],
    ):
        matches = tuple(
            configuration.inputs
            for configuration
            in generated_base_configurations
            if (
                provider.apex_requirement.shares_runtime(
                    configuration
                    .inputs
                    .runtime_policy
                    .runtime_context
                )
            )
        )

        if len(
            matches
        ) != 1:
            return None

        return matches[
            0
        ]

    @staticmethod
    def _in_product(
        *,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
        treble: bool,
    ) -> bool:
        return (
            AndroidRuntimeLinkerApexDeploymentSemantics
            .is_product_linker_domain(
                provider.apex_requirement,
                treble=treble,
            )
        )

    @staticmethod
    def _in_vendor(
        *,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
    ) -> bool:
        return (
            AndroidRuntimeLinkerApexDeploymentSemantics
            .is_vendor_partition(
                provider.apex_requirement
            )
        )

    @staticmethod
    def _in_system(
        *,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
        treble: bool,
    ) -> bool:
        return (
            AndroidRuntimeLinkerApexDeploymentSemantics
            .is_system_linker_domain(
                provider.apex_requirement,
                treble=treble,
            )
        )

    @classmethod
    def _include_sanitizer_requirement(
        cls,
        *,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
        inputs,
        treble: bool,
        semantic_profile: AndroidSemanticVersionProfile,
    ) -> bool:
        if cls._in_system(
            provider=provider,
            treble=treble,
        ):
            return False

        in_vendor = cls._in_vendor(
            provider=provider,
        )

        in_product = cls._in_product(
            provider=provider,
            treble=treble,
        )

        if (
            in_vendor
            and inputs.vendor_vndk_version_defined
        ):
            return True

        if (
            in_product
            and inputs.product_vndk_version_defined
        ):
            return True

        return (
            (
                in_vendor
                or in_product
            )
            and (
                semantic_profile
                .linker
                .apex_non_vndk_vendor_product_sanitizer_variable
                is not None
            )
        )

    @staticmethod
    def _apex_initialized_namespace(
        *,
        name: str,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
        visible: bool,
        include_sanitizer_requirement: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        if provider.active_root is None:
            raise ValueError(
                "ACTIVE APEX provider requires active_root"
            )

        root = provider.active_root.as_posix()

        search_paths = [
            f"{root}/${{LIB}}",
        ]

        if provider.in_vendor:
            search_paths.append(
                f"{root}/${{LIB}}/hw"
            )

        permitted_paths = [
            f"{root}/${{LIB}}",
            "/system/${LIB}",
            "/system_ext/${LIB}",
            *provider.permitted_paths,
        ]

        if provider.has_shared_lib:
            permitted_paths.append(
                "/apex"
            )

        required = [
            literal_library(
                library_name
            )
            for library_name
            in provider.required_libraries
        ]

        if include_sanitizer_requirement:
            required.append(
                literal_library(
                    ":sanitizer"
                )
            )

        return AndroidRuntimeLinkerConstructedNamespace(
            name=name,
            is_isolated=True,
            is_visible=visible,
            search_paths=tuple(
                search_paths
            ),
            permitted_paths=tuple(
                permitted_paths
            ),
            provided_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in provider.provided_libraries
            ),
            required_libraries=tuple(
                required
            ),
        )

    @staticmethod
    def _empty_default_namespace(
        *,
        provider: AndroidUniverseLinkerApexProviderDescriptor,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        if provider.namespace_name is None:
            raise ValueError(
                "ACTIVE APEX provider requires namespace_name"
            )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="default",
            is_isolated=True,
            is_visible=False,
            required_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in provider.required_libraries
            ),
            link_intents=(
                namespace_link_intent(
                    target_namespace=(
                        provider.namespace_name
                    ),
                    allow_all_shared_libs=True,
                ),
            ),
        )

    @staticmethod
    def _system_namespace(
        *,
        inputs,
        treble: bool,
        semantic_profile: AndroidSemanticVersionProfile,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        search_paths = [
            "/system/${LIB}",
        ]

        system_ext = inputs.system_ext_path

        search_paths.append(
            (
                "${SYSTEM_EXT}/${LIB}"
                if system_ext is None
                else (
                    f"{system_ext.as_posix()}/${{LIB}}"
                )
            )
        )

        if not treble:
            product = inputs.product_path

            search_paths.append(
                (
                    "${PRODUCT}/${LIB}"
                    if product is None
                    else (
                        f"{product.as_posix()}/${{LIB}}"
                    )
                )
            )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="system",
            is_isolated=True,
            is_visible=True,
            search_paths=tuple(
                search_paths
            ),
            provided_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in inputs.system_provided_libraries(
                    accumulate=(
                        semantic_profile
                        .linker
                        .system_context_accumulates_configs
                    ),
                )
            ),
            required_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in inputs.system_required_libraries(
                    accumulate=(
                        semantic_profile
                        .linker
                        .system_context_accumulates_configs
                    ),
                )
            ),
        )

    @staticmethod
    def _vendor_namespace(
        *,
        inputs,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        return AndroidRuntimeLinkerConstructedNamespace(
            name="vendor",
            is_isolated=True,
            is_visible=True,
            search_paths=(
                "/odm/${LIB}",
                "/vendor/${LIB}",
                "/vendor/${LIB}/hw",
                "/vendor/${LIB}/egl",
            ),
            permitted_paths=(
                "/odm",
                "/vendor",
                "/system/vendor",
            ),
            provided_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in inputs.vendor_provided_libraries
            ),
            required_libraries=(
                variable_library(
                    "LLNDK_LIBRARIES_VENDOR",
                    "",
                ),
                *(
                    literal_library(
                        library_name
                    )
                    for library_name
                    in inputs.vendor_required_libraries
                ),
            ),
        )

    @staticmethod
    def _product_namespace(
        *,
        inputs,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        product = inputs.product_path

        product_root = (
            "${PRODUCT}"
            if product is None
            else product.as_posix()
        )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="product",
            is_isolated=True,
            is_visible=True,
            search_paths=(
                f"{product_root}/${{LIB}}",
            ),
            permitted_paths=(
                product_root,
            ),
            provided_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in inputs.product_provided_libraries
            ),
            required_libraries=(
                variable_library(
                    "LLNDK_LIBRARIES_PRODUCT",
                    "",
                ),
                *(
                    literal_library(
                        library_name
                    )
                    for library_name
                    in inputs.product_required_libraries
                ),
            ),
        )

    @staticmethod
    def _rs_namespace(
        *,
        inputs,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        search_paths = [
            "/odm/${LIB}/vndk-sp",
            "/vendor/${LIB}/vndk-sp",
        ]

        if inputs.vendor_vndk_version_defined:
            search_paths.append(
                (
                    "/apex/com.android.vndk.v"
                    f"{inputs.vendor_vndk_version}"
                    "/${LIB}"
                )
            )

        search_paths.extend(
            (
                "/odm/${LIB}",
                "/vendor/${LIB}",
            )
        )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="rs",
            is_isolated=True,
            is_visible=True,
            search_paths=tuple(
                search_paths
            ),
            permitted_paths=(
                "/odm/${LIB}",
                "/vendor/${LIB}",
                "/system/vendor/${LIB}",
                "/data",
            ),
            required_libraries=(
                variable_library(
                    "LLNDK_LIBRARIES_VENDOR",
                    "",
                ),
            ),
        )

    @staticmethod
    def _vndk_namespace(
        *,
        inputs,
        product: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        if product:
            version = inputs.product_vndk_version
            root = (
                "${PRODUCT}"
                if inputs.product_path is None
                else inputs.product_path.as_posix()
            )

            search_paths = (
                f"{root}/${{LIB}}/vndk-sp",
                f"{root}/${{LIB}}/vndk",
                (
                    "/apex/com.android.vndk.v"
                    f"{version}"
                    "/${LIB}"
                ),
            )

            required = (
                variable_library(
                    "LLNDK_LIBRARIES_PRODUCT",
                    "",
                ),
            )

        else:
            version = inputs.vendor_vndk_version

            search_paths = (
                "/odm/${LIB}/vndk-sp",
                "/odm/${LIB}/vndk",
                "/vendor/${LIB}/vndk-sp",
                "/vendor/${LIB}/vndk",
                (
                    "/apex/com.android.vndk.v"
                    f"{version}"
                    "/${LIB}"
                ),
            )

            required = (
                variable_library(
                    "LLNDK_LIBRARIES_VENDOR",
                    "",
                ),
            )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="vndk",
            is_isolated=True,
            is_visible=False,
            search_paths=search_paths,
            required_libraries=required,
        )

    @staticmethod
    def _vndk_in_system_namespace(
        *,
        inputs,
        product: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        return AndroidRuntimeLinkerConstructedNamespace(
            name="vndk_in_system",
            is_isolated=True,
            is_visible=False,
            search_paths=(
                "/system/${LIB}",
                (
                    "${SYSTEM_EXT}/${LIB}"
                    if inputs.system_ext_path is None
                    else (
                        f"{inputs.system_ext_path.as_posix()}/${{LIB}}"
                    )
                ),
            ),
            required_libraries=(
                variable_library(
                    (
                        "LLNDK_LIBRARIES_PRODUCT"
                        if product
                        else "LLNDK_LIBRARIES_VENDOR"
                    ),
                    "",
                ),
            ),
        )

    @classmethod
    def build(
        cls,
        *,
        generated_base_configurations: tuple[
            AndroidUniverseLinkerGeneratedBaseConfiguration,
            ...,
        ],
        apex_provider_descriptors: tuple[
            AndroidUniverseLinkerApexProviderDescriptor,
            ...,
        ],
        semantic_profile: AndroidSemanticVersionProfile,
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
        section_apex_applicability: tuple[
            AndroidUniverseLinkerSectionApexApplicability,
            ...,
        ],
    ) -> tuple[
        AndroidRuntimeLinkerEffectiveApexConfiguration,
        ...,
    ]:
        active_providers = tuple(
            provider
            for provider
            in apex_provider_descriptors
            if (
                provider.status
                is AndroidUniverseLinkerApexProviderStatus.ACTIVE
            )
        )

        provider_by_requirement = {
            id(
                provider.apex_requirement
            ): provider
            for provider
            in active_providers
        }

        results = []

        for target_provider in active_providers:
            target_requirement = (
                target_provider.apex_requirement
            )

            inputs = cls._runtime_inputs_for(
                provider=target_provider,
                generated_base_configurations=(
                    generated_base_configurations
                ),
            )

            if inputs is None:
                raise ValueError(
                    "ACTIVE APEX provider has no exact generated "
                    "runtime configuration inputs"
                )

            treble = inputs.treble_enabled

            if treble is None:
                raise ValueError(
                    "ACTIVE APEX provider runtime has unresolved "
                    "Treble semantics"
                )

            target_visible = (
                target_provider
                .namespace_input
                .selected_apex_local_configuration
                is not None
                and target_provider
                .namespace_input
                .selected_apex_local_configuration
                .effective_visible
                is True
            )

            special_visibility = (
                target_requirement.apex_name
                in (
                    semantic_profile
                    .linker
                    .apex_public_jni_visibility_sections
                )
            )

            visible_requirement_ids = set()

            if special_visibility:
                for candidate in apex_requirements:
                    if (
                        candidate.jni_libs
                        or any(
                            conclusion.apex_requirement
                            is candidate
                            and (
                                AndroidUniverseLinkerSectionApexApplicabilityReason
                                .PUBLIC_LIBRARIES
                                in conclusion.reasons
                            )
                            for conclusion
                            in section_apex_applicability
                        )
                    ):
                        visible_requirement_ids.add(
                            id(
                                candidate
                            )
                        )

                        if candidate is target_requirement:
                            target_visible = True

            namespaces = []

            def append_constructed(
                namespace: AndroidRuntimeLinkerConstructedNamespace,
            ) -> None:
                namespaces.append(
                    AndroidRuntimeLinkerEffectiveNamespace(
                        index=len(
                            namespaces
                        ),
                        constructed_namespace=namespace,
                    )
                )

            if target_visible:
                append_constructed(
                    cls._empty_default_namespace(
                        provider=target_provider
                    )
                )
            else:
                append_constructed(
                    cls._apex_initialized_namespace(
                        name="default",
                        provider=target_provider,
                        visible=False,
                        include_sanitizer_requirement=(
                            cls._include_sanitizer_requirement(
                                provider=target_provider,
                                inputs=inputs,
                                treble=treble,
                                semantic_profile=semantic_profile,
                            )
                        ),
                    )
                )

            append_constructed(
                cls._system_namespace(
                    inputs=inputs,
                    treble=treble,
                    semantic_profile=semantic_profile,
                )
            )

            in_vendor = cls._in_vendor(
                provider=target_provider
            )

            in_product = cls._in_product(
                provider=target_provider,
                treble=treble,
            )

            if treble and in_vendor:
                append_constructed(
                    cls._rs_namespace(
                        inputs=inputs
                    )
                )

                vendor = cls._vendor_namespace(
                    inputs=inputs
                )

                if vendor.provided_libraries:
                    append_constructed(
                        vendor
                    )

                if inputs.vendor_vndk_version_defined:
                    append_constructed(
                        cls._vndk_namespace(
                            inputs=inputs,
                            product=False,
                        )
                    )

                    if (
                        inputs.vndk_in_system_namespace
                        is True
                    ):
                        append_constructed(
                            cls._vndk_in_system_namespace(
                                inputs=inputs,
                                product=False,
                            )
                        )

            elif treble and in_product:
                product = cls._product_namespace(
                    inputs=inputs
                )

                if product.provided_libraries:
                    append_constructed(
                        product
                    )

                if inputs.product_vndk_version_defined:
                    append_constructed(
                        cls._vndk_namespace(
                            inputs=inputs,
                            product=True,
                        )
                    )

                    if (
                        inputs.vndk_in_system_namespace
                        is True
                    ):
                        append_constructed(
                            cls._vndk_in_system_namespace(
                                inputs=inputs,
                                product=True,
                            )
                        )

            name_to_index = {
                namespace.name: namespace.index
                for namespace
                in namespaces
            }

            # BuildSection() visible-APEX injection.
            for candidate_requirement in apex_requirements:
                candidate_provider = provider_by_requirement.get(
                    id(
                        candidate_requirement
                    )
                )

                if candidate_provider is None:
                    continue

                selected_policy = (
                    candidate_provider
                    .namespace_input
                    .selected_apex_local_configuration
                )

                candidate_visible = (
                    selected_policy is not None
                    and selected_policy.effective_visible
                    is True
                )

                explicitly_visible = (
                    id(
                        candidate_requirement
                    )
                    in visible_requirement_ids
                )

                if not (
                    candidate_visible
                    or explicitly_visible
                ):
                    continue

                namespace_name = (
                    candidate_provider.namespace_name
                )

                if namespace_name is None:
                    continue

                existing_index = (
                    name_to_index.get(
                        namespace_name
                    )
                )

                if existing_index is not None:
                    existing = namespaces[
                        existing_index
                    ]

                    if existing.apex_provider is None:
                        namespaces[
                            existing_index
                        ] = (
                            AndroidRuntimeLinkerEffectiveNamespace(
                                index=existing.index,
                                generated_namespace=(
                                    existing.generated_namespace
                                ),
                                constructed_namespace=(
                                    existing.constructed_namespace
                                ),
                                visibility_override_apex_provider=(
                                    candidate_provider
                                ),
                            )
                        )

                    continue

                namespaces.append(
                    AndroidRuntimeLinkerEffectiveNamespace(
                        index=len(
                            namespaces
                        ),
                        apex_provider=candidate_provider,
                    )
                )

                name_to_index[
                    namespace_name
                ] = len(
                    namespaces
                ) - 1

            results.append(
                AndroidRuntimeLinkerEffectiveApexConfiguration(
                    apex_provider=target_provider,
                    runtime_inputs=inputs,
                    section_name=(
                        AndroidRuntimeLinkerApexIdentity
                        .section_name(
                            target_requirement
                        )
                    ),
                    namespaces=tuple(
                        namespaces
                    ),
                    status=(
                        AndroidRuntimeLinkerEffectiveConfigurationStatus
                        .RESOLVED
                    ),
                )
            )

        return tuple(
            results
        )


class AndroidRuntimeLinkerEffectiveConfigurationBuilder:
    """
    Reproduce only Android BuildSection() namespace-population semantics.

    This builder stops before:

    - Section::Resolve();
    - provider matching;
    - provider-triggered non-visible APEX namespace injection;
    - alias expansion;
    - link generation;
    - final namespace sorting;
    - AddStandardSystemLinks();
    - ELF DT_NEEDED resolution;
    - Reconstruction Ownership / Planning / Reconstruction.
    """

    @staticmethod
    def build(
        *,
        generated_base_configurations: tuple[
            AndroidUniverseLinkerGeneratedBaseConfiguration,
            ...,
        ],
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
        apex_provider_descriptors: tuple[
            AndroidUniverseLinkerApexProviderDescriptor,
            ...,
        ],
        section_apex_applicability: tuple[
            AndroidUniverseLinkerSectionApexApplicability,
            ...,
        ],
    ) -> tuple[
        AndroidRuntimeLinkerEffectiveBaseConfiguration,
        ...,
    ]:
        for field_name, values in (
            (
                "generated_base_configurations",
                generated_base_configurations,
            ),
            (
                "apex_requirements",
                apex_requirements,
            ),
            (
                "apex_provider_descriptors",
                apex_provider_descriptors,
            ),
            (
                "section_apex_applicability",
                section_apex_applicability,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

        provider_by_apex_identity = {
            id(
                descriptor.apex_requirement
            ): descriptor
            for descriptor
            in apex_provider_descriptors
        }

        if len(
            provider_by_apex_identity
        ) != len(
            apex_provider_descriptors
        ):
            raise ValueError(
                "APEX provider descriptors must contain at most one "
                "descriptor per exact APEX requirement"
            )

        if {
            id(
                requirement
            )
            for requirement
            in apex_requirements
        } != set(
            provider_by_apex_identity
        ):
            raise ValueError(
                "effective configuration requires exactly one provider "
                "descriptor for every exact canonical APEX requirement"
            )

        applicability_by_identity = {}

        for conclusion in section_apex_applicability:
            key = (
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

            if key in applicability_by_identity:
                raise ValueError(
                    "duplicate exact section/APEX applicability conclusion"
                )

            applicability_by_identity[
                key
            ] = conclusion

        effective_configurations = []

        for base_configuration in generated_base_configurations:
            effective_sections = []

            for generated_section in base_configuration.sections:
                effective_namespaces = [
                    AndroidRuntimeLinkerEffectiveNamespace(
                        index=index,
                        generated_namespace=namespace,
                    )
                    for index, namespace
                    in enumerate(
                        generated_section.namespaces
                    )
                ]

                name_to_index = {
                    namespace.name: namespace.index
                    for namespace
                    in effective_namespaces
                }

                ambiguous_reasons = []
                unresolved_reasons = []

                # AOSP BuildSection() iterates ctx.GetApexModules(). TreeForge
                # preserves canonical runtime APEX order through the exact
                # Universe APEX requirement sequence supplied by the stage.
                for apex_requirement in apex_requirements:
                    key = (
                        id(
                            base_configuration
                        ),
                        id(
                            generated_section
                        ),
                        id(
                            apex_requirement
                        ),
                    )

                    applicability = (
                        applicability_by_identity.get(
                            key
                        )
                    )

                    # A generated configuration with no applicability surface
                    # for this section/APEX pair cannot safely invent one.
                    if applicability is None:
                        unresolved_reasons.append(
                            "missing section/APEX applicability: "
                            f"{generated_section.name}:"
                            f"{apex_requirement.requirement_id}"
                        )
                        continue

                    if (
                        applicability.status
                        is AndroidUniverseLinkerSectionApexApplicabilityStatus
                        .INAPPLICABLE
                    ):
                        continue

                    if (
                        applicability.status
                        is AndroidUniverseLinkerSectionApexApplicabilityStatus
                        .AMBIGUOUS
                    ):
                        ambiguous_reasons.append(
                            "ambiguous section/APEX applicability: "
                            f"{applicability.conclusion_id}"
                        )
                        continue

                    if (
                        applicability.status
                        is AndroidUniverseLinkerSectionApexApplicabilityStatus
                        .UNRESOLVED
                    ):
                        unresolved_reasons.append(
                            "unresolved section/APEX applicability: "
                            f"{applicability.conclusion_id}"
                        )
                        continue

                    descriptor = provider_by_apex_identity[
                        id(
                            apex_requirement
                        )
                    ]

                    if (
                        descriptor.status
                        is AndroidUniverseLinkerApexProviderStatus
                        .EXCLUDED_SHARED_APEX
                    ):
                        # provideSharedApexLibs=true APEXes are not present in
                        # linkerconfig's active APEX module population.
                        continue

                    if (
                        descriptor.status
                        is AndroidUniverseLinkerApexProviderStatus.AMBIGUOUS
                    ):
                        ambiguous_reasons.append(
                            "ambiguous active APEX provider: "
                            f"{descriptor.descriptor_id}"
                        )
                        continue

                    if (
                        descriptor.status
                        is AndroidUniverseLinkerApexProviderStatus.UNRESOLVED
                    ):
                        unresolved_reasons.append(
                            "unresolved active APEX provider: "
                            f"{descriptor.descriptor_id}"
                        )
                        continue

                    if (
                        descriptor.status
                        is not AndroidUniverseLinkerApexProviderStatus.ACTIVE
                    ):
                        raise ValueError(
                            "unexpected APEX provider status"
                        )

                    namespace_name = descriptor.namespace_name

                    if namespace_name is None:
                        raise ValueError(
                            "ACTIVE APEX provider must have namespace_name"
                        )

                    existing_index = name_to_index.get(
                        namespace_name
                    )

                    if existing_index is not None:
                        existing = effective_namespaces[
                            existing_index
                        ]

                        if existing.apex_provider is not None:
                            # BuildSection sees the namespace already present
                            # and only forces visibility. It never creates a
                            # duplicate namespace.
                            continue

                        effective_namespaces[
                            existing_index
                        ] = (
                            AndroidRuntimeLinkerEffectiveNamespace(
                                index=existing.index,
                                generated_namespace=(
                                    existing.generated_namespace
                                ),
                                visibility_override_apex_provider=(
                                    descriptor
                                ),
                            )
                        )

                        continue

                    index = len(
                        effective_namespaces
                    )

                    effective_namespaces.append(
                        AndroidRuntimeLinkerEffectiveNamespace(
                            index=index,
                            apex_provider=descriptor,
                        )
                    )

                    name_to_index[
                        namespace_name
                    ] = index

                section_reasons = tuple(
                    [
                        *ambiguous_reasons,
                        *unresolved_reasons,
                    ]
                )

                if unresolved_reasons:
                    section_status = (
                        AndroidRuntimeLinkerEffectiveConfigurationStatus
                        .UNRESOLVED
                    )
                elif ambiguous_reasons:
                    section_status = (
                        AndroidRuntimeLinkerEffectiveConfigurationStatus
                        .AMBIGUOUS
                    )
                else:
                    section_status = (
                        AndroidRuntimeLinkerEffectiveConfigurationStatus
                        .RESOLVED
                    )

                effective_sections.append(
                    AndroidRuntimeLinkerEffectiveSection(
                        base_configuration=base_configuration,
                        generated_section=generated_section,
                        namespaces=tuple(
                            effective_namespaces
                        ),
                        status=section_status,
                        unresolved_reasons=section_reasons,
                    )
                )

            configuration_reasons = tuple(
                reason
                for section
                in effective_sections
                for reason
                in section.unresolved_reasons
            )

            if any(
                section.status
                is AndroidRuntimeLinkerEffectiveConfigurationStatus.UNRESOLVED
                for section
                in effective_sections
            ):
                configuration_status = (
                    AndroidRuntimeLinkerEffectiveConfigurationStatus
                    .UNRESOLVED
                )

            elif any(
                section.status
                is AndroidRuntimeLinkerEffectiveConfigurationStatus.AMBIGUOUS
                for section
                in effective_sections
            ):
                configuration_status = (
                    AndroidRuntimeLinkerEffectiveConfigurationStatus
                    .AMBIGUOUS
                )

            else:
                configuration_status = (
                    AndroidRuntimeLinkerEffectiveConfigurationStatus.RESOLVED
                )

            effective_configurations.append(
                AndroidRuntimeLinkerEffectiveBaseConfiguration(
                    generated_configuration=base_configuration,
                    sections=tuple(
                        effective_sections
                    ),
                    status=configuration_status,
                    unresolved_reasons=configuration_reasons,
                )
            )

        return tuple(
            effective_configurations
        )
