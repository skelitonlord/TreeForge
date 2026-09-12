"""
Runtime Linker provider vocabulary.

This module models the provider inputs consumed by Android
Section::Resolve():

1. concrete libraries provided by namespaces already present in a section;
2. active APEX providers keyed by provided library;
3. section-local LibProvider aliases such as :vndk, :sphal and :vendorall.

It deliberately does not perform Section::Resolve(), namespace reachability,
ELF DT_NEEDED resolution, source ownership, planning, or materialization.
"""

from __future__ import annotations

from treeforge.android.runtime_linking.linker.section_semantics import (
    AndroidRuntimeLinkerSectionSemantics,
)

from treeforge.android.runtime_linking.linker.apex_deployment import (
    AndroidRuntimeLinkerApexDeploymentSemantics,
)

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.runtime_linking.linker.expression import (
    AndroidRuntimeLinkerLibraryExpression,
    literal_library,
    variable_library,
)
from treeforge.android.runtime_linking.linker.effective_configuration import (
    AndroidRuntimeLinkerConstructedNamespace,
    AndroidRuntimeLinkerEffectiveApexConfiguration,
    AndroidRuntimeLinkerEffectiveNamespace,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexProviderDescriptor,
    AndroidUniverseLinkerApexProviderStatus,
)
from treeforge.android.version.model import (
    AndroidSemanticVersionProfile,
)


class AndroidRuntimeLinkerAliasLinkModifierKind(
    StrEnum
):
    """
    Android LibProvider link modifier.
    """

    SHARED_LIBRARIES = "shared_libraries"
    ALLOW_ALL_SHARED_LIBRARIES = "allow_all_shared_libraries"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerAliasLinkModifier:
    """
    Runtime equivalent of linkerconfig SharedLibs / AllowAllSharedLibs.
    """

    kind: AndroidRuntimeLinkerAliasLinkModifierKind

    shared_libraries: tuple[
        AndroidRuntimeLinkerLibraryExpression,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidRuntimeLinkerAliasLinkModifierKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidRuntimeLinkerAliasLinkModifierKind"
            )

        if not isinstance(
            self.shared_libraries,
            tuple,
        ):
            raise TypeError(
                "shared_libraries must be a tuple"
            )

        if not all(
            isinstance(
                library,
                AndroidRuntimeLinkerLibraryExpression,
            )
            for library
            in self.shared_libraries
        ):
            raise TypeError(
                "shared_libraries must contain typed library expressions"
            )

        if (
            self.kind
            is (
                AndroidRuntimeLinkerAliasLinkModifierKind
                .ALLOW_ALL_SHARED_LIBRARIES
            )
            and self.shared_libraries
        ):
            raise ValueError(
                "allow-all modifier must not list shared libraries"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerAliasProvider:
    """
    One Android LibProvider entry.

    ``alias`` includes Android's leading colon.

    ``namespace`` is the namespace that Section::Resolve() will add when the
    alias is consumed and that namespace is not already present.
    """

    alias: str

    namespace: AndroidRuntimeLinkerConstructedNamespace

    link_modifier: AndroidRuntimeLinkerAliasLinkModifier

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.alias,
                str,
            )
            or not self.alias.startswith(
                ":"
            )
            or len(
                self.alias
            ) == 1
        ):
            raise ValueError(
                "alias must be a non-empty colon-prefixed name"
            )

        if not isinstance(
            self.namespace,
            AndroidRuntimeLinkerConstructedNamespace,
        ):
            raise TypeError(
                "namespace must be an "
                "AndroidRuntimeLinkerConstructedNamespace"
            )

        if not isinstance(
            self.link_modifier,
            AndroidRuntimeLinkerAliasLinkModifier,
        ):
            raise TypeError(
                "link_modifier must be an "
                "AndroidRuntimeLinkerAliasLinkModifier"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerConcreteLibraryProvider:
    """
    One concrete provided-library conclusion from a namespace already present
    in the effective section.

    Android Section::Resolve() treats duplicate concrete providers as fatal.
    TreeForge preserves all candidates here so the resolver can represent that
    condition explicitly rather than silently selecting one.
    """

    library_name: str

    namespace: AndroidRuntimeLinkerEffectiveNamespace

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.library_name,
                str,
            )
            or not self.library_name
        ):
            raise ValueError(
                "library_name must be a non-empty string"
            )

        if not isinstance(
            self.namespace,
            AndroidRuntimeLinkerEffectiveNamespace,
        ):
            raise TypeError(
                "namespace must be an "
                "AndroidRuntimeLinkerEffectiveNamespace"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerApexLibraryProvider:
    """
    One active APEX provider for one provideNativeLibs library.
    """

    library_name: str

    apex_provider: AndroidUniverseLinkerApexProviderDescriptor

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.library_name,
                str,
            )
            or not self.library_name
        ):
            raise ValueError(
                "library_name must be a non-empty string"
            )

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
                "APEX library provider requires ACTIVE descriptor"
            )

        if (
            self.library_name
            not in self.apex_provider.provided_libraries
        ):
            raise ValueError(
                "library_name must be provided by the exact APEX descriptor"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerSectionProviderVocabulary:
    """
    Complete provider inputs for one effective linker section immediately
    before Section::Resolve().
    """

    section_name: str

    concrete_library_providers: tuple[
        AndroidRuntimeLinkerConcreteLibraryProvider,
        ...,
    ]

    apex_library_providers: tuple[
        AndroidRuntimeLinkerApexLibraryProvider,
        ...,
    ]

    alias_providers: tuple[
        AndroidRuntimeLinkerAliasProvider,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.section_name,
                str,
            )
            or not self.section_name
        ):
            raise ValueError(
                "section_name must be a non-empty string"
            )

        for field_name, expected_type in (
            (
                "concrete_library_providers",
                AndroidRuntimeLinkerConcreteLibraryProvider,
            ),
            (
                "apex_library_providers",
                AndroidRuntimeLinkerApexLibraryProvider,
            ),
            (
                "alias_providers",
                AndroidRuntimeLinkerAliasProvider,
            ),
        ):
            values = getattr(
                self,
                field_name,
            )

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
                    f"{field_name} contains invalid values"
                )


class AndroidRuntimeLinkerProviderVocabularyBuilder:
    """
    Construct provider inputs without performing provider resolution.
    """

    @staticmethod
    def _namespace_provided_libraries(
        namespace: AndroidRuntimeLinkerEffectiveNamespace,
    ) -> tuple[
        str,
        ...,
    ]:
        if namespace.generated_namespace is not None:
            values = []

            for expression in (
                namespace
                .generated_namespace
                .provides
            ):
                # Section::Resolve() can index only concrete provided library
                # names here. Symbolic linkerconfig variables remain symbolic
                # until their owning variable-expansion semantics are available.
                library_name = (
                    expression.library_name
                )

                if library_name is not None:
                    values.append(
                        library_name
                    )

            return tuple(
                values
            )

        if namespace.constructed_namespace is not None:
            return tuple(
                expression.library_name
                for expression
                in (
                    namespace
                    .constructed_namespace
                    .provided_libraries
                )
                if expression.library_name is not None
            )

        if namespace.apex_provider is not None:
            return (
                namespace
                .apex_provider
                .provided_libraries
            )

        raise AssertionError(
            "effective namespace has no primary origin"
        )

    @classmethod
    def concrete_providers(
        cls,
        *,
        namespaces: tuple[
            AndroidRuntimeLinkerEffectiveNamespace,
            ...,
        ],
    ) -> tuple[
        AndroidRuntimeLinkerConcreteLibraryProvider,
        ...,
    ]:
        values = []

        for namespace in namespaces:
            for library_name in (
                cls._namespace_provided_libraries(
                    namespace
                )
            ):
                values.append(
                    AndroidRuntimeLinkerConcreteLibraryProvider(
                        library_name=library_name,
                        namespace=namespace,
                    )
                )

        return tuple(
            values
        )

    @staticmethod
    def apex_providers(
        *,
        apex_provider_descriptors: tuple[
            AndroidUniverseLinkerApexProviderDescriptor,
            ...,
        ],
    ) -> tuple[
        AndroidRuntimeLinkerApexLibraryProvider,
        ...,
    ]:
        values = []

        for provider in apex_provider_descriptors:
            if (
                provider.status
                is not AndroidUniverseLinkerApexProviderStatus.ACTIVE
            ):
                continue

            for library_name in (
                provider.provided_libraries
            ):
                values.append(
                    AndroidRuntimeLinkerApexLibraryProvider(
                        library_name=library_name,
                        apex_provider=provider,
                    )
                )

        return tuple(
            values
        )

    @staticmethod
    def _shared(
        *variables: str,
    ) -> AndroidRuntimeLinkerAliasLinkModifier:
        return AndroidRuntimeLinkerAliasLinkModifier(
            kind=(
                AndroidRuntimeLinkerAliasLinkModifierKind
                .SHARED_LIBRARIES
            ),
            shared_libraries=tuple(
                variable_library(
                    variable
                )
                for variable
                in variables
            ),
        )

    @staticmethod
    def _allow_all(
    ) -> AndroidRuntimeLinkerAliasLinkModifier:
        return AndroidRuntimeLinkerAliasLinkModifier(
            kind=(
                AndroidRuntimeLinkerAliasLinkModifierKind
                .ALLOW_ALL_SHARED_LIBRARIES
            ),
        )

    @staticmethod
    def _vendor_namespace(
        *,
        inputs,
        name: str,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        return AndroidRuntimeLinkerConstructedNamespace(
            name=name,
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
    def _vendor_subdir_namespace(
        *,
        name: str,
        subdir: str,
        vendor_vndk_defined: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        requirements = [
            variable_library(
                "LLNDK_LIBRARIES_VENDOR",
                "",
            ),
            literal_library(
                ":vendorall"
            ),
        ]

        if vendor_vndk_defined:
            requirements.append(
                literal_library(
                    ":vndk"
                )
            )

        return AndroidRuntimeLinkerConstructedNamespace(
            name=name,
            is_isolated=True,
            is_visible=True,
            search_paths=(
                f"/vendor/${{LIB}}/{subdir}",
            ),
            permitted_paths=(
                f"/vendor/${{LIB}}/{subdir}",
                f"/system/vendor/${{LIB}}/{subdir}",
            ),
            required_libraries=tuple(
                requirements
            ),
        )

    @staticmethod
    def _system_namespace(
        *,
        inputs,
        treble: bool,
        system_context_accumulates_configs: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        search_paths = [
            "/system/${LIB}",
        ]

        if inputs.system_ext_path is None:
            search_paths.append(
                "${SYSTEM_EXT}/${LIB}"
            )
        else:
            search_paths.append(
                f"{inputs.system_ext_path.as_posix()}/${{LIB}}"
            )

        if not treble:
            if inputs.product_path is None:
                search_paths.append(
                    "${PRODUCT}/${LIB}"
                )
            else:
                search_paths.append(
                    f"{inputs.product_path.as_posix()}/${{LIB}}"
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
                    accumulate=system_context_accumulates_configs,
                )
            ),
            required_libraries=tuple(
                literal_library(
                    library_name
                )
                for library_name
                in inputs.system_required_libraries(
                    accumulate=system_context_accumulates_configs,
                )
            ),
        )

    @staticmethod
    def _sphal_namespace(
        *,
        inputs,
        vendor_vndk_defined: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        permitted = [
            "/odm/${LIB}",
            "/vendor/${LIB}",
            "/vendor/odm/${LIB}",
            "/system/vendor/${LIB}",
        ]

        if not vendor_vndk_defined:
            permitted.append(
                "/data"
            )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="sphal",
            is_isolated=True,
            is_visible=True,
            search_paths=(
                "/odm/${LIB}",
                "/vendor/${LIB}",
                "/vendor/${LIB}/egl",
                "/vendor/${LIB}/hw",
            ),
            permitted_paths=tuple(
                permitted
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
            root = (
                "${PRODUCT}"
                if inputs.product_path is None
                else inputs.product_path.as_posix()
            )

            version = (
                inputs.product_vndk_version
            )

            return AndroidRuntimeLinkerConstructedNamespace(
                name="vndk",
                is_isolated=True,
                is_visible=False,
                search_paths=(
                    f"{root}/${{LIB}}/vndk-sp",
                    f"{root}/${{LIB}}/vndk",
                    (
                        "/apex/com.android.vndk.v"
                        f"{version}"
                        "/${LIB}"
                    ),
                ),
                required_libraries=(
                    variable_library(
                        "LLNDK_LIBRARIES_PRODUCT",
                        "",
                    ),
                ),
            )

        version = (
            inputs.vendor_vndk_version
        )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="vndk",
            is_isolated=True,
            is_visible=False,
            search_paths=(
                "/odm/${LIB}/vndk-sp",
                "/odm/${LIB}/vndk",
                "/vendor/${LIB}/vndk-sp",
                "/vendor/${LIB}/vndk",
                (
                    "/apex/com.android.vndk.v"
                    f"{version}"
                    "/${LIB}"
                ),
            ),
            required_libraries=(
                variable_library(
                    "LLNDK_LIBRARIES_VENDOR",
                    "",
                ),
            ),
        )

    @staticmethod
    def _vndk_in_system_namespace(
        *,
        inputs,
        product: bool,
    ) -> AndroidRuntimeLinkerConstructedNamespace:
        system_ext = (
            "${SYSTEM_EXT}"
            if inputs.system_ext_path is None
            else inputs.system_ext_path.as_posix()
        )

        return AndroidRuntimeLinkerConstructedNamespace(
            name="vndk_in_system",
            is_isolated=True,
            is_visible=False,
            search_paths=(
                "/system/${LIB}",
                f"{system_ext}/${{LIB}}",
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
    def _vndk_alias(
        cls,
        *,
        inputs,
        product: bool,
    ) -> tuple[
        AndroidRuntimeLinkerAliasProvider,
        ...,
    ]:
        suffix = (
            "PRODUCT"
            if product
            else "VENDOR"
        )

        values = [
            AndroidRuntimeLinkerAliasProvider(
                alias=":vndk",
                namespace=cls._vndk_namespace(
                    inputs=inputs,
                    product=product,
                ),
                link_modifier=cls._shared(
                    f"VNDK_SAMEPROCESS_LIBRARIES_{suffix}",
                    f"VNDK_CORE_LIBRARIES_{suffix}",
                ),
            )
        ]

        if (
            inputs.vndk_in_system_namespace
            is True
        ):
            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":vndk",
                    namespace=(
                        cls._vndk_in_system_namespace(
                            inputs=inputs,
                            product=product,
                        )
                    ),
                    link_modifier=cls._shared(
                        "VNDK_USING_CORE_VARIANT_LIBRARIES"
                    ),
                )
            )

        return tuple(
            values
        )

    @classmethod
    def base_alias_providers(
        cls,
        *,
        section_name: str,
        inputs,
    ) -> tuple[
        AndroidRuntimeLinkerAliasProvider,
        ...,
    ]:
        """
        Android BASE sections pass LibProviders only for vendor.
        """

        if not AndroidRuntimeLinkerSectionSemantics.is_vendor(section_name):
            return ()

        values = []

        if inputs.vendor_vndk_version_defined:
            values.extend(
                cls._vndk_alias(
                    inputs=inputs,
                    product=False,
                )
            )

        values.append(
            AndroidRuntimeLinkerAliasProvider(
                alias=":mediacas",
                namespace=(
                    cls._vendor_subdir_namespace(
                        name="mediacas",
                        subdir="mediacas",
                        vendor_vndk_defined=(
                            inputs.vendor_vndk_version_defined
                        ),
                    )
                ),
                link_modifier=cls._allow_all(),
            )
        )

        values.append(
            AndroidRuntimeLinkerAliasProvider(
                alias=":vendorall",
                namespace=cls._vendor_namespace(
                    inputs=inputs,
                    name="default",
                ),
                link_modifier=cls._allow_all(),
            )
        )

        return tuple(
            values
        )

    @classmethod
    def apex_alias_providers(
        cls,
        *,
        configuration: (
            AndroidRuntimeLinkerEffectiveApexConfiguration
        ),
        non_vndk_sanitizer_variable: str | None,
        system_context_accumulates_configs: bool,
    ) -> tuple[
        AndroidRuntimeLinkerAliasProvider,
        ...,
    ]:
        """
        Android BuildApexDefaultSection() LibProviders.
        """

        provider = (
            configuration.apex_provider
        )

        inputs = (
            configuration.runtime_inputs
        )

        treble = (
            inputs.treble_enabled
        )

        if treble is None:
            raise ValueError(
                "effective APEX configuration requires resolved Treble state"
            )

        in_vendor = (
            AndroidRuntimeLinkerApexDeploymentSemantics
            .is_vendor_partition(
                provider.apex_requirement
            )
        )

        in_product = (
            AndroidRuntimeLinkerApexDeploymentSemantics
            .is_product_linker_domain(
                provider.apex_requirement,
                treble=treble,
            )
        )

        values = []

        if in_vendor:
            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":sphal",
                    namespace=cls._vendor_namespace(
                        inputs=inputs,
                        name="vendor",
                    ),
                    link_modifier=cls._shared(),
                )
            )
        else:
            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":sphal",
                    namespace=cls._sphal_namespace(
                        inputs=inputs,
                        vendor_vndk_defined=(
                            inputs.vendor_vndk_version_defined
                        ),
                    ),
                    link_modifier=cls._shared(),
                )
            )

        in_vendor_with_vndk = (
            not in_product
            and inputs.vendor_vndk_version_defined
        )

        in_product_with_vndk = (
            in_product
            and inputs.product_vndk_version_defined
        )

        if (
            in_vendor_with_vndk
            or in_product_with_vndk
        ):
            product = (
                in_product
            )

            suffix = (
                "PRODUCT"
                if product
                else "VENDOR"
            )

            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":sanitizer",
                    namespace=cls._system_namespace(
                        inputs=inputs,
                        treble=treble,
                        system_context_accumulates_configs=(
                            system_context_accumulates_configs
                        ),
                    ),
                    link_modifier=cls._shared(
                        f"SANITIZER_DEFAULT_{suffix}"
                    ),
                )
            )

            values.extend(
                cls._vndk_alias(
                    inputs=inputs,
                    product=product,
                )
            )

            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":vndksp",
                    namespace=cls._vndk_namespace(
                        inputs=inputs,
                        product=product,
                    ),
                    link_modifier=cls._shared(
                        f"VNDK_SAMEPROCESS_LIBRARIES_{suffix}"
                    ),
                )
            )

        elif (
            (
                in_product
                or in_vendor
            )
            and non_vndk_sanitizer_variable is not None
        ):
            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":sanitizer",
                    namespace=cls._system_namespace(
                        inputs=inputs,
                        treble=treble,
                        system_context_accumulates_configs=(
                            system_context_accumulates_configs
                        ),
                    ),
                    link_modifier=cls._shared(
                        non_vndk_sanitizer_variable
                    ),
                )
            )

        if in_vendor:
            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":mediacas",
                    namespace=(
                        cls._vendor_subdir_namespace(
                            name="mediacas",
                            subdir="mediacas",
                            vendor_vndk_defined=(
                                inputs.vendor_vndk_version_defined
                            ),
                        )
                    ),
                    link_modifier=cls._allow_all(),
                )
            )

            values.append(
                AndroidRuntimeLinkerAliasProvider(
                    alias=":vendorall",
                    namespace=cls._vendor_namespace(
                        inputs=inputs,
                        name="vendor",
                    ),
                    link_modifier=cls._allow_all(),
                )
            )

        return tuple(
            values
        )

