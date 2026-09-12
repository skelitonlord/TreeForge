from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AndroidSemanticVersionSelectionSource(
    StrEnum,
):
    """
    Source of the effective Android platform-semantic version.
    """

    CANONICAL = "canonical"
    OVERRIDE = "override"


class AndroidLinkerSemanticCondition(
    StrEnum,
):
    """
    Canonical runtime conditions consumed by release-specific Linker rules.

    Release profiles select which rules depend on these conditions.
    Generic Universe code evaluates them from canonical runtime evidence.
    """

    VENDOR_VNDK_DEFINED = "vendor_vndk_defined"
    VENDOR_VNDK_NOT_DEFINED = "vendor_vndk_not_defined"
    PRODUCT_VNDK_DEFINED = "product_vndk_defined"
    VNDK_IN_SYSTEM_NAMESPACE = "vndk_in_system_namespace"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerSemanticLibraryExpression:
    """
    One Android-release Linker library expression.

    Exactly one of ``library_name`` or ``variable`` must be present.

    ``variable`` represents a genuine Android linkerconfig variable, never a
    TreeForge alias for device/factory-image-derived evidence.
    """

    library_name: str | None = None
    variable: str | None = None
    fallback: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.library_name is None
        ) == (
            self.variable is None
        ):
            raise ValueError(
                "exactly one of library_name or variable must be present"
            )

        if self.library_name is not None:
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

            if self.fallback is not None:
                raise ValueError(
                    "literal library expressions cannot carry fallback"
                )

        if self.variable is not None:
            if (
                not isinstance(
                    self.variable,
                    str,
                )
                or not self.variable
            ):
                raise ValueError(
                    "variable must be a non-empty string"
                )

            if (
                self.fallback is not None
                and not isinstance(
                    self.fallback,
                    str,
                )
            ):
                raise TypeError(
                    "fallback must be a string or None"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerSemanticNamespaceLinkRule:
    """
    One release-specific namespace-link rule.
    """

    target_namespace: str

    shared_libraries: tuple[
        AndroidLinkerSemanticLibraryExpression,
        ...,
    ] = ()

    conditions: tuple[
        AndroidLinkerSemanticCondition,
        ...,
    ] = ()

    section_names: tuple[
        str,
        ...,
    ] = ()

    excluded_section_names: tuple[
        str,
        ...,
    ] = ()

    allow_all_shared_libs: bool = False

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.target_namespace,
                str,
            )
            or not self.target_namespace
        ):
            raise ValueError(
                "target_namespace must be a non-empty string"
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
                value,
                AndroidLinkerSemanticLibraryExpression,
            )
            for value
            in self.shared_libraries
        ):
            raise TypeError(
                "shared_libraries contains invalid expressions"
            )

        if not isinstance(
            self.conditions,
            tuple,
        ):
            raise TypeError(
                "conditions must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerSemanticCondition,
            )
            for value
            in self.conditions
        ):
            raise TypeError(
                "conditions contains invalid values"
            )

        if len(
            self.conditions
        ) != len(
            set(
                self.conditions
            )
        ):
            raise ValueError(
                "conditions must be unique"
            )

        for field_name, values in (
            (
                "section_names",
                self.section_names,
            ),
            (
                "excluded_section_names",
                self.excluded_section_names,
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
                    str,
                )
                and value
                for value
                in values
            ):
                raise ValueError(
                    f"{field_name} must contain only "
                    "non-empty strings"
                )

            if len(
                values
            ) != len(
                set(
                    values
                )
            ):
                raise ValueError(
                    f"{field_name} must be unique"
                )

        if (
            set(
                self.section_names
            )
            & set(
                self.excluded_section_names
            )
        ):
            raise ValueError(
                "section_names and excluded_section_names "
                "must not overlap"
            )

        if not isinstance(
            self.allow_all_shared_libs,
            bool,
        ):
            raise TypeError(
                "allow_all_shared_libs must be a bool"
            )

        if (
            self.allow_all_shared_libs
            and self.shared_libraries
        ):
            raise ValueError(
                "allow-all rules cannot list shared libraries"
            )

        if (
            not self.allow_all_shared_libs
            and not self.shared_libraries
        ):
            raise ValueError(
                "link rule must name libraries or allow all"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerSemanticAdditionalSection:
    """
    One Android-release-specific BASE linkerconfig section.

    This represents only release-selected topology. Generic Runtime Linking
    owns construction of the generated section/namespace objects.

    Search paths here are literal linkerconfig paths. Device-derived and
    runtime-variable paths do not belong in this release profile.
    """

    section_name: str
    namespace_name: str

    namespace_isolated: bool
    namespace_visible: bool

    namespace_search_paths: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "section_name",
                self.section_name,
            ),
            (
                "namespace_name",
                self.namespace_name,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.namespace_isolated,
            bool,
        ):
            raise TypeError(
                "namespace_isolated must be a bool"
            )

        if not isinstance(
            self.namespace_visible,
            bool,
        ):
            raise TypeError(
                "namespace_visible must be a bool"
            )

        if not isinstance(
            self.namespace_search_paths,
            tuple,
        ):
            raise TypeError(
                "namespace_search_paths must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            and value.startswith("/")
            for value
            in self.namespace_search_paths
        ):
            raise ValueError(
                "namespace_search_paths must contain absolute "
                "non-empty path strings"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidLinkerSemanticProfile:
    """
    Android-release-specific Linker implementation semantics.

    Canonical device evidence never belongs here.

    Release profiles own only behavior proven to differ across Android
    platform releases. Generic Runtime Linking owns the machinery that
    evaluates and applies these values.
    """

    system_context_accumulates_configs: bool = False

    base_additional_sections: tuple[
        AndroidLinkerSemanticAdditionalSection,
        ...,
    ] = ()

    base_additional_directory_routes: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ] = ()

    apex_non_vndk_vendor_product_sanitizer_variable: str | None = None

    vendor_default_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    product_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    sphal_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    rs_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    vndk_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    vndk_in_system_allowed_libraries: tuple[
        AndroidLinkerSemanticLibraryExpression,
        ...,
    ] = ()

    vndk_in_system_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    isolated_link_rules: tuple[
        AndroidLinkerSemanticNamespaceLinkRule,
        ...,
    ] = ()

    apex_public_jni_visibility_sections: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.system_context_accumulates_configs,
            bool,
        ):
            raise TypeError(
                "system_context_accumulates_configs must be a bool"
            )

        if not isinstance(
            self.base_additional_sections,
            tuple,
        ):
            raise TypeError(
                "base_additional_sections must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerSemanticAdditionalSection,
            )
            for value in self.base_additional_sections
        ):
            raise TypeError(
                "base_additional_sections must contain only "
                "AndroidLinkerSemanticAdditionalSection instances"
            )

        additional_section_names = tuple(
            value.section_name
            for value
            in self.base_additional_sections
        )

        if len(
            additional_section_names
        ) != len(
            set(
                additional_section_names
            )
        ):
            raise ValueError(
                "base_additional section names must be unique"
            )

        if not isinstance(
            self.base_additional_directory_routes,
            tuple,
        ):
            raise TypeError(
                "base_additional_directory_routes must be a tuple"
            )

        for route in self.base_additional_directory_routes:
            if (
                not isinstance(route, tuple)
                or len(route) != 2
                or not all(
                    isinstance(value, str) and value
                    for value in route
                )
            ):
                raise ValueError(
                    "base_additional_directory_routes must contain "
                    "(path, section_name) string tuples"
                )

            if route[1] not in additional_section_names:
                raise ValueError(
                    "additional directory route must target an "
                    "additional section"
                )

        if (
            self.apex_non_vndk_vendor_product_sanitizer_variable
            is not None
            and (
                not isinstance(
                    self.apex_non_vndk_vendor_product_sanitizer_variable,
                    str,
                )
                or not (
                    self.apex_non_vndk_vendor_product_sanitizer_variable
                    .strip()
                )
            )
        ):
            raise ValueError(
                "apex_non_vndk_vendor_product_sanitizer_variable must "
                "be a non-empty string or None"
            )

        if not isinstance(
            self.vendor_default_link_rules,
            tuple,
        ):
            raise TypeError(
                "vendor_default_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.vendor_default_link_rules
        ):
            raise TypeError(
                "vendor_default_link_rules contains invalid rules"
            )

        if not isinstance(
            self.product_link_rules,
            tuple,
        ):
            raise TypeError(
                "product_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.product_link_rules
        ):
            raise TypeError(
                "product_link_rules contains invalid rules"
            )

        if not isinstance(
            self.sphal_link_rules,
            tuple,
        ):
            raise TypeError(
                "sphal_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.sphal_link_rules
        ):
            raise TypeError(
                "sphal_link_rules contains invalid rules"
            )

        if not isinstance(
            self.rs_link_rules,
            tuple,
        ):
            raise TypeError(
                "rs_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.rs_link_rules
        ):
            raise TypeError(
                "rs_link_rules contains invalid rules"
            )

        if not isinstance(
            self.vndk_link_rules,
            tuple,
        ):
            raise TypeError(
                "vndk_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.vndk_link_rules
        ):
            raise TypeError(
                "vndk_link_rules contains invalid rules"
            )

        if not isinstance(
            self.vndk_in_system_allowed_libraries,
            tuple,
        ):
            raise TypeError(
                "vndk_in_system_allowed_libraries must be a tuple"
            )

        if not all(
            isinstance(
                expression,
                AndroidLinkerSemanticLibraryExpression,
            )
            for expression
            in self.vndk_in_system_allowed_libraries
        ):
            raise TypeError(
                "vndk_in_system_allowed_libraries contains "
                "invalid expressions"
            )

        if not isinstance(
            self.vndk_in_system_link_rules,
            tuple,
        ):
            raise TypeError(
                "vndk_in_system_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.vndk_in_system_link_rules
        ):
            raise TypeError(
                "vndk_in_system_link_rules contains invalid rules"
            )

        if not isinstance(
            self.isolated_link_rules,
            tuple,
        ):
            raise TypeError(
                "isolated_link_rules must be a tuple"
            )

        if not all(
            isinstance(
                rule,
                AndroidLinkerSemanticNamespaceLinkRule,
            )
            for rule
            in self.isolated_link_rules
        ):
            raise TypeError(
                "isolated_link_rules contains invalid rules"
            )

        if not isinstance(
            self.apex_public_jni_visibility_sections,
            tuple,
        ):
            raise TypeError(
                "apex_public_jni_visibility_sections must be a tuple"
            )

        if not all(
            isinstance(
                apex_name,
                str,
            )
            and apex_name
            for apex_name
            in self.apex_public_jni_visibility_sections
        ):
            raise ValueError(
                "apex_public_jni_visibility_sections must contain only "
                "non-empty APEX names"
            )

        if len(
            self.apex_public_jni_visibility_sections
        ) != len(
            set(
                self.apex_public_jni_visibility_sections
            )
        ):
            raise ValueError(
                "apex_public_jni_visibility_sections must be unique"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSemanticVersionProfile:
    """
    Android-release platform semantics consumed by generic TreeForge
    interpreters and reconcilers.

    These are Android implementation semantics, not device knowledge and not
    factory-image evidence.

    Version-sensitive semantic families are added only when TreeForge has
    established a genuine Android release difference.
    """

    android_version: str

    linker: AndroidLinkerSemanticProfile = field(
        default_factory=AndroidLinkerSemanticProfile
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.android_version,
                str,
            )
            or not self.android_version.strip()
        ):
            raise ValueError(
                "android_version must be a non-empty string"
            )

        if not isinstance(
            self.linker,
            AndroidLinkerSemanticProfile,
        ):
            raise TypeError(
                "linker must be an AndroidLinkerSemanticProfile"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSemanticVersionSelection:
    """
    Selected Android platform semantics for one Universe run.

    canonical_version records what canonical factory-image evidence proves.

    requested_override records an explicit caller override without rewriting
    that evidence.

    effective_version is the profile TreeForge actually applies.
    """

    canonical_version: str | None
    requested_override: str | None
    effective_version: str

    source: AndroidSemanticVersionSelectionSource

    profile: AndroidSemanticVersionProfile

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "canonical_version",
                self.canonical_version,
            ),
            (
                "requested_override",
                self.requested_override,
            ),
        ):
            if (
                value is not None
                and (
                    not isinstance(
                        value,
                        str,
                    )
                    or not value.strip()
                )
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty "
                    "string or None"
                )

        if (
            not isinstance(
                self.effective_version,
                str,
            )
            or not self.effective_version.strip()
        ):
            raise ValueError(
                "effective_version must be a non-empty string"
            )

        if not isinstance(
            self.source,
            AndroidSemanticVersionSelectionSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidSemanticVersionSelectionSource"
            )

        if not isinstance(
            self.profile,
            AndroidSemanticVersionProfile,
        ):
            raise TypeError(
                "profile must be an AndroidSemanticVersionProfile"
            )

        if (
            self.profile.android_version
            != self.effective_version
        ):
            raise ValueError(
                "profile version must match effective_version"
            )

        if self.requested_override is not None:
            if (
                self.source
                is not AndroidSemanticVersionSelectionSource.OVERRIDE
                or self.effective_version
                != self.requested_override
            ):
                raise ValueError(
                    "override selection is inconsistent"
                )

        else:
            if (
                self.source
                is not AndroidSemanticVersionSelectionSource.CANONICAL
                or self.canonical_version is None
                or self.effective_version
                != self.canonical_version
            ):
                raise ValueError(
                    "canonical selection is inconsistent"
                )
