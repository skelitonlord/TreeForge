from __future__ import annotations

from treeforge.android.runtime_linking.linker.section_semantics import (
    AndroidRuntimeLinkerSectionSemantics,
)

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath

from treeforge.android.universe.model_source import (
    AndroidUniverseModelSourceRequirementInventory,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.linker.requirement import (
    AndroidUniverseLinkerRequirement,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerProtobufUsage,
    AndroidUniverseLinkerRuntimePolicy,
)
from treeforge.android.universe.properties import (
    AndroidUniverseConclusionStatus,
    AndroidUniverseFactConclusion,
)

from treeforge.android.version.model import (
    AndroidLinkerSemanticCondition,
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticProfile,
    AndroidSemanticVersionProfile,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedConfigurationInputs:
    """
    Canonical runtime inputs consumed by Android linkerconfig generation.

    This object does not itself generate ``ld.config.txt`` sections,
    namespaces, search paths, permitted paths, or namespace links.

    Linker-local policy is preserved by exact ``runtime_policy`` identity.
    Cross-family property conclusions and filesystem source evidence are
    retained rather than flattened away.

    ``None`` for a VNDK conclusion means the corresponding property was not
    observed canonically. A conclusion whose value is the empty string is
    therefore distinguishable from true property absence.
    """

    runtime_policy: AndroidUniverseLinkerRuntimePolicy

    treble_conclusion: (
        AndroidUniverseFactConclusion
        | None
    )

    debuggable_conclusion: (
        AndroidUniverseFactConclusion
        | None
    )

    vendor_vndk_version_conclusion: (
        AndroidUniverseFactConclusion
        | None
    )

    product_vndk_version_conclusion: (
        AndroidUniverseFactConclusion
        | None
    )

    vndk_lite_conclusion: (
        AndroidUniverseFactConclusion
        | None
    )

    product_path_candidates: tuple[
        PurePosixPath,
        ...,
    ]

    system_ext_path_candidates: tuple[
        PurePosixPath,
        ...,
    ]

    vndk_apex_requirements: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.runtime_policy,
            AndroidUniverseLinkerRuntimePolicy,
        ):
            raise TypeError(
                "runtime_policy must be an "
                "AndroidUniverseLinkerRuntimePolicy"
            )

        for field_name, conclusion in (
            (
                "treble_conclusion",
                self.treble_conclusion,
            ),
            (
                "debuggable_conclusion",
                self.debuggable_conclusion,
            ),
            (
                "vendor_vndk_version_conclusion",
                self.vendor_vndk_version_conclusion,
            ),
            (
                "product_vndk_version_conclusion",
                self.product_vndk_version_conclusion,
            ),
            (
                "vndk_lite_conclusion",
                self.vndk_lite_conclusion,
            ),
        ):
            if (
                conclusion is not None
                and not isinstance(
                    conclusion,
                    AndroidUniverseFactConclusion,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an "
                    "AndroidUniverseFactConclusion or None"
                )

        if not isinstance(
            self.vndk_apex_requirements,
            tuple,
        ):
            raise TypeError(
                "vndk_apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in self.vndk_apex_requirements
        ):
            raise TypeError(
                "vndk_apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        if self.vndk_apex_requirements != tuple(
            sorted(
                self.vndk_apex_requirements,
                key=lambda requirement: (
                    requirement.requirement_id
                ),
            )
        ):
            raise ValueError(
                "vndk_apex_requirements must be in canonical order"
            )

        if not all(
            requirement.is_vndk_apex
            for requirement
            in self.vndk_apex_requirements
        ):
            raise ValueError(
                "vndk_apex_requirements must contain only VNDK APEXes"
            )

        if not all(
            requirement.shares_runtime(
                self.runtime_policy.runtime_context
            )
            for requirement
            in self.vndk_apex_requirements
        ):
            raise ValueError(
                "vndk_apex_requirements must belong to the exact "
                "generated-input runtime"
            )

        for (
            field_name,
            values,
        ) in (
            (
                "product_path_candidates",
                self.product_path_candidates,
            ),
            (
                "system_ext_path_candidates",
                self.system_ext_path_candidates,
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
                    PurePosixPath,
                )
                and value.is_absolute()
                for value in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "absolute PurePosixPath values"
                )

            if values != tuple(
                sorted(
                    set(
                        values
                    ),
                    key=lambda value: (
                        value.as_posix()
                    ),
                )
            ):
                raise ValueError(
                    f"{field_name} must be unique and "
                    "canonically ordered"
                )

    @staticmethod
    def _agreed_value(
        conclusion: (
            AndroidUniverseFactConclusion
            | None
        ),
    ) -> str | None:
        if conclusion is None:
            return None

        if (
            conclusion.status
            is not AndroidUniverseConclusionStatus.AGREED
        ):
            return None

        return conclusion.value

    @property
    def treble_enabled(
        self,
    ) -> bool | None:
        value = self._agreed_value(
            self.treble_conclusion
        )

        if value == "true":
            return True

        if value == "false":
            return False

        return None

    @property
    def debuggable(
        self,
    ) -> bool | None:
        """
        Mirror android::base::GetBoolProperty("ro.debuggable", false).

        Property absence and agreed-but-unparseable values use Android's
        false default. A non-AGREED canonical conclusion remains unresolved
        because TreeForge cannot choose which runtime value existed.
        """

        conclusion = self.debuggable_conclusion

        if conclusion is None:
            return False

        if (
            conclusion.status
            is not AndroidUniverseConclusionStatus.AGREED
        ):
            return None

        value = conclusion.value

        if value in {
            "1",
            "y",
            "yes",
            "on",
            "true",
        }:
            return True

        if value in {
            "0",
            "n",
            "no",
            "off",
            "false",
        }:
            return False

        return False

    @property
    def vendor_vndk_version(
        self,
    ) -> str | None:
        return self._agreed_value(
            self.vendor_vndk_version_conclusion
        )

    @property
    def vendor_vndk_version_defined(
        self,
    ) -> bool:
        return (
            self.vendor_vndk_version_conclusion
            is not None
        )

    @property
    def product_vndk_version(
        self,
    ) -> str | None:
        return self._agreed_value(
            self.product_vndk_version_conclusion
        )

    @property
    def product_vndk_version_defined(
        self,
    ) -> bool:
        return (
            self.product_vndk_version_conclusion
            is not None
        )

    @property
    def vndk_lite(
        self,
    ) -> bool | None:
        conclusion = (
            self.vndk_lite_conclusion
        )

        if conclusion is None:
            #
            # Mirrors Android linkerconfig's:
            #
            # GetValue("ro.vndk.lite").value_or("") == "true"
            #
            return False

        value = self._agreed_value(
            conclusion
        )

        if value == "true":
            return True

        if value == "false":
            return False

        return None

    @property
    def vndk_available(
        self,
    ) -> bool:
        """
        Mirror linkerconfig Environment::IsVndkAvailable().

        A VNDK implementation is available when the exact runtime contains
        an active APEX whose canonical module name is in the
        ``com.android.vndk.*`` family.
        """
        return bool(
            self.vndk_apex_requirements
        )

    @property
    def vendor_vndk_loader_version(
        self,
    ) -> str | None:
        """
        Runtime value consumed by LoadVndkLibraryListVariables().

        Canonical property absence mirrors Android's empty-string fallback.
        A non-AGREED conclusion remains unresolved rather than being treated
        as absence.
        """
        conclusion = (
            self.vendor_vndk_version_conclusion
        )

        if conclusion is None:
            return ""

        if (
            conclusion.status
            is not AndroidUniverseConclusionStatus.AGREED
        ):
            return None

        return conclusion.value

    @property
    def vendor_vndk_apex_requirements(
        self,
    ) -> tuple[
        AndroidUniverseApexRequirement,
        ...,
    ] | None:
        version = (
            self.vendor_vndk_loader_version
        )

        if version is None:
            return None

        if version == "":
            return ()

        return tuple(
            requirement
            for requirement
            in self.vndk_apex_requirements
            if requirement.matches_vndk_version(
                version
            )
        )

    @property
    def vendor_vndk_apex_available(
        self,
    ) -> bool | None:
        requirements = (
            self.vendor_vndk_apex_requirements
        )

        if requirements is None:
            return None

        return bool(
            requirements
        )

    @property
    def vndk_in_system_namespace(
        self,
    ) -> bool | None:
        """
        Mirror modules::IsVndkInSystemNamespace() after variable loading.

        ``VNDK_USING_CORE_VARIANT_LIBRARIES`` is defined only when the
        vendor VNDK loader proceeds past both its non-empty-version check
        and its matching VNDK-APEX availability check. Once those checks
        pass, linkerconfig defines the variable even when its value is empty.
        """
        return (
            self.vendor_vndk_apex_available
        )

    @property
    def product_path(
        self,
    ) -> PurePosixPath | None:
        if len(
            self.product_path_candidates
        ) != 1:
            return None

        return self.product_path_candidates[
            0
        ]

    @property
    def system_ext_path(
        self,
    ) -> PurePosixPath | None:
        if len(
            self.system_ext_path_candidates
        ) != 1:
            return None

        return self.system_ext_path_candidates[
            0
        ]

    def _context_library_names(
        self,
        *,
        usage: AndroidUniverseLinkerProtobufUsage,
        provided: bool,
        accumulate: bool,
    ) -> tuple[
        str,
        ...,
    ]:
        configurations = tuple(
            configuration
            for configuration
            in self.runtime_policy.protobuf_configurations
            if configuration.usage is usage
        )

        if (
            not accumulate
            and configurations
        ):
            configurations = (
                configurations[
                    -1
                ],
            )

        return tuple(
            policy.library_name
            for configuration
            in configurations
            for policy
            in (
                configuration.provided_libraries
                if provided
                else configuration.required_libraries
            )
        )

    def system_provided_libraries(
        self,
        *,
        accumulate: bool,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._context_library_names(
            usage=(
                AndroidUniverseLinkerProtobufUsage
                .SYSTEM_CONTEXT
            ),
            provided=True,
            accumulate=accumulate,
        )

    def system_required_libraries(
        self,
        *,
        accumulate: bool,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._context_library_names(
            usage=(
                AndroidUniverseLinkerProtobufUsage
                .SYSTEM_CONTEXT
            ),
            provided=False,
            accumulate=accumulate,
        )

    @property
    def vendor_provided_libraries(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._context_library_names(
            usage=(
                AndroidUniverseLinkerProtobufUsage
                .VENDOR_CONTEXT
            ),
            provided=True,
            accumulate=False,
        )

    @property
    def vendor_required_libraries(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._context_library_names(
            usage=(
                AndroidUniverseLinkerProtobufUsage
                .VENDOR_CONTEXT
            ),
            provided=False,
            accumulate=False,
        )

    @property
    def product_provided_libraries(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._context_library_names(
            usage=(
                AndroidUniverseLinkerProtobufUsage
                .PRODUCT_CONTEXT
            ),
            provided=True,
            accumulate=False,
        )

    @property
    def product_required_libraries(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self._context_library_names(
            usage=(
                AndroidUniverseLinkerProtobufUsage
                .PRODUCT_CONTEXT
            ),
            provided=False,
            accumulate=False,
        )


class AndroidUniverseLinkerGeneratedConfigurationInputReconciler:
    """
    Reconcile canonical inputs required for generated Linker configuration.

    This consumes only already-canonical Universe identities:

    - Linker runtime policies,
    - canonical property conclusions,
    - canonical Universe model-source requirements.

    It does not parse property files, inspect host filesystem paths, infer
    device/version knowledge, generate linker sections, or resolve ELF
    dependencies.
    """

    _PROPERTY_FACTS = (
        "treble_enabled",
        "debuggable",
        "vendor_vndk_version",
        "product_vndk_version",
        "vndk_lite",
    )

    @staticmethod
    def _conclusion_for(
        *,
        fact: str,
        conclusions: tuple[
            AndroidUniverseFactConclusion,
            ...,
        ],
    ) -> (
        AndroidUniverseFactConclusion
        | None
    ):
        matches = tuple(
            conclusion
            for conclusion in conclusions
            if conclusion.fact == fact
        )

        if len(
            matches
        ) > 1:
            raise ValueError(
                "canonical property conclusions contain "
                f"multiple conclusions for {fact!r}"
            )

        if not matches:
            return None

        return matches[
            0
        ]

    def reconcile(
        self,
        *,
        linker_requirement: (
            AndroidUniverseLinkerRequirement
            | None
        ),
        property_conclusions: tuple[
            AndroidUniverseFactConclusion,
            ...,
        ],
        model_source_requirements: (
            AndroidUniverseModelSourceRequirementInventory
        ),
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseLinkerGeneratedConfigurationInputs,
        ...,
    ]:
        if linker_requirement is None:
            return ()

        if not isinstance(
            linker_requirement,
            AndroidUniverseLinkerRequirement,
        ):
            raise TypeError(
                "linker_requirement must be an "
                "AndroidUniverseLinkerRequirement or None"
            )

        if not isinstance(
            property_conclusions,
            tuple,
        ):
            raise TypeError(
                "property_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                conclusion,
                AndroidUniverseFactConclusion,
            )
            for conclusion
            in property_conclusions
        ):
            raise TypeError(
                "property_conclusions must contain only "
                "AndroidUniverseFactConclusion instances"
            )

        if not isinstance(
            model_source_requirements,
            AndroidUniverseModelSourceRequirementInventory,
        ):
            raise TypeError(
                "model_source_requirements must be an "
                "AndroidUniverseModelSourceRequirementInventory"
            )

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

        conclusions = {
            fact: self._conclusion_for(
                fact=fact,
                conclusions=(
                    property_conclusions
                ),
            )
            for fact
            in self._PROPERTY_FACTS
        }

        results = []

        for runtime_policy in (
            linker_requirement.runtime_policies
        ):
            vndk_apex_requirements = tuple(
                sorted(
                    (
                        requirement
                        for requirement
                        in apex_requirements
                        if (
                            requirement.is_vndk_apex
                            and requirement.shares_runtime(
                                runtime_policy.runtime_context
                            )
                        )
                    ),
                    key=lambda requirement: (
                        requirement.requirement_id
                    ),
                )
            )

            results.append(
                AndroidUniverseLinkerGeneratedConfigurationInputs(
                    runtime_policy=runtime_policy,
                    treble_conclusion=(
                        conclusions[
                            "treble_enabled"
                        ]
                    ),
                    debuggable_conclusion=(
                        conclusions[
                            "debuggable"
                        ]
                    ),
                    vendor_vndk_version_conclusion=(
                        conclusions[
                            "vendor_vndk_version"
                        ]
                    ),
                    product_vndk_version_conclusion=(
                        conclusions[
                            "product_vndk_version"
                        ]
                    ),
                    vndk_lite_conclusion=(
                        conclusions[
                            "vndk_lite"
                        ]
                    ),
                    #
                    # PRODUCT and SYSTEM_EXT are linkerconfig environment
                    # roots for the device filesystem, not runtime-local
                    # Linker-policy facts.
                    #
                    # APEX runtime contexts therefore consume the same
                    # canonical partition-root evidence as BASE generation.
                    # Filtering these roots through same_runtime() incorrectly
                    # removes /product and /system_ext evidence when generating
                    # an APEX configuration and causes symbolic ${PRODUCT} /
                    # ${SYSTEM_EXT} placeholders to survive into effective
                    # runtime paths.
                    #
                    # Universe validates the canonical partition role and
                    # Android-visible first path component before exposing
                    # these root candidates, so Runtime Linking does not
                    # reconstruct filesystem semantics from source provenance.
                    #
                    product_path_candidates=(
                        model_source_requirements
                        .partition_root_candidates(
                            "product"
                        )
                    ),
                    system_ext_path_candidates=(
                        model_source_requirements
                        .partition_root_candidates(
                            "system_ext"
                        )
                    ),
                    vndk_apex_requirements=(
                        vndk_apex_requirements
                    ),
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.runtime_policy
                    .runtime_context
                    .kind
                    .value,
                    (
                        ""
                        if (
                            item.runtime_policy
                            .runtime_context
                            .partition_container
                            is None
                        )
                        else str(
                            item.runtime_policy
                            .runtime_context
                            .partition_container
                            .path
                        )
                    ),
                ),
            )
        )


class AndroidUniverseLinkerGeneratedConfigurationStatus(
    str,
    Enum,
):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedDirectoryRoute:
    """
    One ordered executable-directory mapping generated by linkerconfig.

    ``path`` is the resolved Android runtime-visible directory when all
    required generator variables are canonically known.

    Variable-backed routes retain ``variable`` and ``suffix`` even when the
    runtime-specific variable value is unresolved. This preserves Android's
    exact generator semantics without inventing a path.
    """

    index: int
    section_name: str

    path: PurePosixPath | None

    variable: str | None = None
    suffix: PurePosixPath | None = None

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

        if (
            not isinstance(
                self.section_name,
                str,
            )
            or not self.section_name
        ):
            raise ValueError(
                "section_name must be non-empty"
            )

        if (
            self.path is not None
            and (
                not isinstance(
                    self.path,
                    PurePosixPath,
                )
                or not self.path.is_absolute()
            )
        ):
            raise ValueError(
                "path must be an absolute PurePosixPath or None"
            )

        if (
            self.variable is None
        ) != (
            self.suffix is None
        ):
            raise ValueError(
                "variable and suffix must either both be present "
                "or both be absent"
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
                    "variable must be non-empty"
                )

            if not isinstance(
                self.suffix,
                PurePosixPath,
            ):
                raise TypeError(
                    "suffix must be a PurePosixPath"
                )

    @property
    def resolved(
        self,
    ) -> bool:
        return self.path is not None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedNamespacePath:
    """
    One ordered path expression produced by an Android namespace builder.

    ``path`` is the effective linkerconfig path when the required generator
    variable is canonically known, or when Android itself supplies an exact
    fallback value.

    Variable-backed expressions preserve their variable, prefix, suffix, and
    fallback separately so unresolved generator state is never replaced with
    an invented path.

    Unlike generated executable-directory routes, namespace paths may be
    relative when Android's own Var(..., fallback) expression supplies a
    relative fallback such as ``product``.
    """

    path: PurePosixPath | None

    variable: str | None = None
    prefix: str = ""
    suffix: str = ""
    fallback: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.path is not None
            and not isinstance(
                self.path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "path must be a PurePosixPath or None"
            )

        if self.variable is None:
            if (
                self.prefix
                or self.suffix
                or self.fallback is not None
            ):
                raise ValueError(
                    "static namespace paths cannot carry "
                    "variable expression metadata"
                )

        else:
            if (
                not isinstance(
                    self.variable,
                    str,
                )
                or not self.variable
            ):
                raise ValueError(
                    "variable must be non-empty"
                )

            if not isinstance(
                self.prefix,
                str,
            ):
                raise TypeError(
                    "prefix must be a string"
                )

            if not isinstance(
                self.suffix,
                str,
            ):
                raise TypeError(
                    "suffix must be a string"
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

    @property
    def resolved(
        self,
    ) -> bool:
        return self.path is not None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedLibraryExpression:
    """
    One canonical library expression consumed by Android linkerconfig
    namespace semantics before Section::Resolve().

    Exactly one of ``library_name`` or ``variable`` is present.

    ``library_name`` preserves a literal SONAME or provider alias such as
    ``libRS_internal.so`` or ``:vndk``.

    ``variable`` preserves an Android linkerconfig variable whose effective
    value is not yet canonically expanded by TreeForge. ``fallback`` records
    Android's own explicit fallback where one exists.

    This deliberately does not invent a concrete expansion for runtime
    variables such as LLNDK_LIBRARIES_VENDOR or VNDK_CORE_LIBRARIES_VENDOR.
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

        if (
            self.library_name is not None
            and (
                not isinstance(
                    self.library_name,
                    str,
                )
                or not self.library_name
            )
        ):
            raise ValueError(
                "library_name must be a non-empty string or None"
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
                    "variable must be a non-empty string or None"
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

        elif self.fallback is not None:
            raise ValueError(
                "literal library expressions cannot carry fallback"
            )

    @property
    def expression_id(
        self,
    ) -> str:
        if self.library_name is not None:
            return (
                "literal:"
                f"{self.library_name}"
            )

        fallback = (
            ""
            if self.fallback is None
            else self.fallback
        )

        return (
            "variable:"
            f"{self.variable}:"
            f"{fallback}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedNamespaceLinkIntent:
    """
    One explicit namespace-link intent emitted by an Android namespace
    builder before Section::Resolve().

    ``shared_libraries`` preserves ordered literal or symbolic library
    expressions supplied through GetLink(...).AddSharedLib(...).

    ``allow_all_shared_libs`` preserves AllowAllSharedLibs() semantics.

    An empty restricted link is valid. Android intentionally creates some
    links before later provider/standard-link resolution in order to preserve
    namespace link ordering.
    """

    target_namespace: str

    shared_libraries: tuple[
        AndroidUniverseLinkerGeneratedLibraryExpression,
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
                AndroidUniverseLinkerGeneratedLibraryExpression,
            )
            for value
            in self.shared_libraries
        ):
            raise TypeError(
                "shared_libraries must contain only "
                "AndroidUniverseLinkerGeneratedLibraryExpression "
                "instances"
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
                "allow-all link intent cannot also carry a "
                "restricted library list"
            )

    @property
    def intent_id(
        self,
    ) -> str:
        mode = (
            "all"
            if self.allow_all_shared_libs
            else "restricted"
        )

        libraries = ",".join(
            expression.expression_id
            for expression
            in self.shared_libraries
        )

        return (
            f"{self.target_namespace}:"
            f"{mode}:"
            f"{libraries}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedNamespace:
    """
    One namespace constructed before Android BuildSection() expansion.

    This slice preserves namespace identity, generation order, isolation,
    visibility, local search/permitted paths, and the namespace-local semantic
    intents emitted before Android Section::Resolve().

    ``provides`` and ``requires`` retain ordered literal or symbolic library
    expressions. ``link_intents`` retains explicit GetLink()/AddSharedLib()/
    AllowAllSharedLibs() semantics.

    APEX namespace injection, provider resolution, resolved namespace links,
    standard-system-link expansion, and ELF dependency resolution remain
    later semantic slices.
    """

    index: int
    name: str

    is_isolated: bool
    is_visible: bool

    search_paths: tuple[
        AndroidUniverseLinkerGeneratedNamespacePath,
        ...,
    ] = ()

    permitted_paths: tuple[
        AndroidUniverseLinkerGeneratedNamespacePath,
        ...,
    ] = ()

    allowed_libs: tuple[
        AndroidUniverseLinkerGeneratedLibraryExpression,
        ...,
    ] = ()

    provides: tuple[
        AndroidUniverseLinkerGeneratedLibraryExpression,
        ...,
    ] = ()

    requires: tuple[
        AndroidUniverseLinkerGeneratedLibraryExpression,
        ...,
    ] = ()

    link_intents: tuple[
        AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
        ...,
    ] = ()

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

        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "name must be non-empty"
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

        for field_name, values in (
            (
                "search_paths",
                self.search_paths,
            ),
            (
                "permitted_paths",
                self.permitted_paths,
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
                    AndroidUniverseLinkerGeneratedNamespacePath,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "AndroidUniverseLinkerGeneratedNamespacePath "
                    "instances"
                )

        if not isinstance(
            self.allowed_libs,
            tuple,
        ):
            raise TypeError(
                "allowed_libs must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseLinkerGeneratedLibraryExpression,
            )
            for value
            in self.allowed_libs
        ):
            raise TypeError(
                "generated namespace allowed_libs must contain only "
                "AndroidUniverseLinkerGeneratedLibraryExpression "
                "instances"
            )

        for field_name, values in (
            (
                "provides",
                self.provides,
            ),
            (
                "requires",
                self.requires,
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
                    AndroidUniverseLinkerGeneratedLibraryExpression,
                )
                for value
                in values
            ):
                raise TypeError(
                    "generated namespace provides/requires must contain "
                    "only AndroidUniverseLinkerGeneratedLibraryExpression "
                    "instances"
                )

        if not isinstance(
            self.link_intents,
            tuple,
        ):
            raise TypeError(
                "link_intents must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
            )
            for value
            in self.link_intents
        ):
            raise TypeError(
                "link_intents must contain only "
                "AndroidUniverseLinkerGeneratedNamespaceLinkIntent "
                "instances"
            )

        link_targets = tuple(
            value.target_namespace
            for value
            in self.link_intents
        )

        if len(
            link_targets
        ) != len(
            set(
                link_targets
            )
        ):
            raise ValueError(
                "generated namespace link intents must contain at most "
                "one canonical intent per target namespace"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedSection:
    """
    One section identity emitted by Android CreateBaseConfiguration.

    Namespace contents intentionally remain outside this first topology
    slice. They are constructed by the individual Android section builders
    and depend on additional Linker/APEX/VNDK semantics.
    """

    index: int
    name: str

    namespaces: tuple[
        AndroidUniverseLinkerGeneratedNamespace,
        ...,
    ]

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

        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "name must be non-empty"
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
                AndroidUniverseLinkerGeneratedNamespace,
            )
            for namespace
            in self.namespaces
        ):
            raise TypeError(
                "namespaces must contain only "
                "AndroidUniverseLinkerGeneratedNamespace instances"
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
                "namespaces must preserve canonical generation order"
            )

        namespace_names = tuple(
            namespace.name
            for namespace
            in self.namespaces
        )

        if len(
            namespace_names
        ) != len(
            set(
                namespace_names
            )
        ):
            raise ValueError(
                "generated namespace names must be unique within a section"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerGeneratedBaseConfiguration:
    """
    Canonical semantic topology of Android CreateBaseConfiguration.

    Route order is semantic: bionic selects the first matching executable
    directory mapping.

    Section order mirrors linkerconfig generation order.

    Sections contain the exact namespace population constructed before
    Android BuildSection() expansion, including namespace flags and local
    search/permitted paths.

    Namespace-local provides/requires and explicit link intents are preserved
    before resolution. APEX namespace injection, provider resolution, resolved
    namespace links, standard-system-link expansion, and ELF dependency
    resolution remain outside this slice.
    """

    inputs: AndroidUniverseLinkerGeneratedConfigurationInputs

    sections: tuple[
        AndroidUniverseLinkerGeneratedSection,
        ...,
    ]

    directory_routes: tuple[
        AndroidUniverseLinkerGeneratedDirectoryRoute,
        ...,
    ]

    status: AndroidUniverseLinkerGeneratedConfigurationStatus

    unresolved_reasons: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.inputs,
            AndroidUniverseLinkerGeneratedConfigurationInputs,
        ):
            raise TypeError(
                "inputs must be an "
                "AndroidUniverseLinkerGeneratedConfigurationInputs"
            )

        if not isinstance(
            self.sections,
            tuple,
        ):
            raise TypeError(
                "sections must be a tuple"
            )

        if not all(
            isinstance(
                section,
                AndroidUniverseLinkerGeneratedSection,
            )
            for section
            in self.sections
        ):
            raise TypeError(
                "sections must contain only "
                "AndroidUniverseLinkerGeneratedSection instances"
            )

        if tuple(
            section.index
            for section
            in self.sections
        ) != tuple(
            range(
                len(
                    self.sections
                )
            )
        ):
            raise ValueError(
                "sections must preserve canonical generation order"
            )

        section_names = tuple(
            section.name
            for section
            in self.sections
        )

        if len(
            section_names
        ) != len(
            set(
                section_names
            )
        ):
            raise ValueError(
                "generated section names must be unique"
            )

        if not isinstance(
            self.directory_routes,
            tuple,
        ):
            raise TypeError(
                "directory_routes must be a tuple"
            )

        if not all(
            isinstance(
                route,
                AndroidUniverseLinkerGeneratedDirectoryRoute,
            )
            for route
            in self.directory_routes
        ):
            raise TypeError(
                "directory_routes must contain only "
                "AndroidUniverseLinkerGeneratedDirectoryRoute instances"
            )

        if tuple(
            route.index
            for route
            in self.directory_routes
        ) != tuple(
            range(
                len(
                    self.directory_routes
                )
            )
        ):
            raise ValueError(
                "directory_routes must preserve canonical first-match order"
            )

        if not all(
            route.section_name
            in section_names
            for route
            in self.directory_routes
        ):
            raise ValueError(
                "every generated directory route must target "
                "a generated section"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerGeneratedConfigurationStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerGeneratedConfigurationStatus"
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

        unresolved_routes = tuple(
            route
            for route
            in self.directory_routes
            if not route.resolved
        )

        if (
            self.status
            is AndroidUniverseLinkerGeneratedConfigurationStatus.RESOLVED
            and (
                unresolved_routes
                or self.unresolved_reasons
            )
        ):
            raise ValueError(
                "resolved generated configuration cannot contain "
                "unresolved routes or reasons"
            )

        if (
            self.status
            is AndroidUniverseLinkerGeneratedConfigurationStatus.UNRESOLVED
            and not self.unresolved_reasons
        ):
            raise ValueError(
                "unresolved generated configuration must explain why"
            )


class AndroidUniverseLinkerGeneratedBaseConfigurationBuilder:
    """
    Reproduce Android CreateBaseConfiguration topology generically.

    Static route definitions below are Android linkerconfig semantics, not
    device-specific knowledge. Runtime-variable values come exclusively from
    canonical generated-configuration inputs.

    Namespace construction here stops immediately before BuildSection():
    namespace identity/order, isolation/visibility, local search/permitted
    paths, provides/requires, and explicit namespace-link intents are modeled.

    APEX injection, Section::Resolve provider resolution, standard system-link
    expansion, and ELF dependency resolution are not performed here.
    """

    @staticmethod
    def _literal_library(
        value: str,
    ) -> AndroidUniverseLinkerGeneratedLibraryExpression:
        return AndroidUniverseLinkerGeneratedLibraryExpression(
            library_name=value,
        )

    @staticmethod
    def _variable_library(
        variable: str,
        fallback: str | None = None,
    ) -> AndroidUniverseLinkerGeneratedLibraryExpression:
        return AndroidUniverseLinkerGeneratedLibraryExpression(
            variable=variable,
            fallback=fallback,
        )

    @staticmethod
    def _link_intent(
        *,
        target_namespace: str,
        shared_libraries: tuple[
            AndroidUniverseLinkerGeneratedLibraryExpression,
            ...,
        ] = (),
        allow_all_shared_libs: bool = False,
    ) -> AndroidUniverseLinkerGeneratedNamespaceLinkIntent:
        return AndroidUniverseLinkerGeneratedNamespaceLinkIntent(
            target_namespace=target_namespace,
            shared_libraries=shared_libraries,
            allow_all_shared_libs=allow_all_shared_libs,
        )

    @classmethod
    def _profile_library_expression(
        cls,
        expression: AndroidLinkerSemanticLibraryExpression,
    ) -> AndroidUniverseLinkerGeneratedLibraryExpression:
        if expression.library_name is not None:
            return cls._literal_library(
                expression.library_name
            )

        return cls._variable_library(
            expression.variable,
            expression.fallback,
        )

    @staticmethod
    def _profile_condition_matches(
        *,
        condition: AndroidLinkerSemanticCondition,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
    ) -> bool:
        if (
            condition
            is AndroidLinkerSemanticCondition
            .VENDOR_VNDK_DEFINED
        ):
            return (
                inputs.vendor_vndk_version_defined
            )

        if (
            condition
            is AndroidLinkerSemanticCondition
            .VENDOR_VNDK_NOT_DEFINED
        ):
            return (
                not inputs.vendor_vndk_version_defined
            )

        if (
            condition
            is AndroidLinkerSemanticCondition
            .PRODUCT_VNDK_DEFINED
        ):
            return (
                inputs.product_vndk_version_defined
            )

        if (
            condition
            is AndroidLinkerSemanticCondition
            .VNDK_IN_SYSTEM_NAMESPACE
        ):
            return (
                inputs.vndk_in_system_namespace
                is True
            )

        raise AssertionError(
            "unsupported Linker semantic condition: "
            f"{condition!r}"
        )

    @classmethod
    def _profile_link_intents(
        cls,
        *,
        rules,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        section_name: str,
    ) -> tuple[
        AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
        ...,
    ]:
        values = []

        for rule in rules:
            if (
                rule.section_names
                and section_name
                not in rule.section_names
            ):
                continue

            if (
                section_name
                in rule.excluded_section_names
            ):
                continue

            if not all(
                cls._profile_condition_matches(
                    condition=condition,
                    inputs=inputs,
                )
                for condition
                in rule.conditions
            ):
                continue

            values.append(
                cls._link_intent(
                    target_namespace=(
                        rule.target_namespace
                    ),
                    shared_libraries=tuple(
                        cls._profile_library_expression(
                            expression
                        )
                        for expression
                        in rule.shared_libraries
                    ),
                    allow_all_shared_libs=(
                        rule.allow_all_shared_libs
                    ),
                )
            )

        return tuple(
            values
        )

    @staticmethod
    def _static_route(
        *,
        index: int,
        path: str,
        section_name: str,
    ) -> AndroidUniverseLinkerGeneratedDirectoryRoute:
        return AndroidUniverseLinkerGeneratedDirectoryRoute(
            index=index,
            section_name=section_name,
            path=PurePosixPath(
                path
            ),
        )

    @staticmethod
    def _variable_route(
        *,
        index: int,
        root: PurePosixPath | None,
        variable: str,
        suffix: str,
        section_name: str,
    ) -> AndroidUniverseLinkerGeneratedDirectoryRoute:
        relative_suffix = (
            PurePosixPath(
                suffix
            )
        )

        resolved_path = None

        if root is not None:
            resolved_path = (
                root
                / relative_suffix
            )

        return AndroidUniverseLinkerGeneratedDirectoryRoute(
            index=index,
            section_name=section_name,
            path=resolved_path,
            variable=variable,
            suffix=relative_suffix,
        )

    @staticmethod
    def _static_namespace_path(
        value: str,
    ) -> AndroidUniverseLinkerGeneratedNamespacePath:
        return AndroidUniverseLinkerGeneratedNamespacePath(
            path=PurePosixPath(
                value
            ),
        )

    @staticmethod
    def _variable_namespace_path(
        *,
        value: str | None,
        variable: str,
        prefix: str = "",
        suffix: str = "",
        fallback: str | None = None,
    ) -> AndroidUniverseLinkerGeneratedNamespacePath:
        effective_value = (
            value
            if value is not None
            else fallback
        )

        resolved_path = None

        if effective_value is not None:
            resolved_path = PurePosixPath(
                (
                    prefix
                    + effective_value
                    + suffix
                )
            )

        return AndroidUniverseLinkerGeneratedNamespacePath(
            path=resolved_path,
            variable=variable,
            prefix=prefix,
            suffix=suffix,
            fallback=fallback,
        )

    @staticmethod
    def _namespace(
        *,
        index: int,
        name: str,
        isolated: bool,
        visible: bool,
        search_paths: tuple[
            AndroidUniverseLinkerGeneratedNamespacePath,
            ...,
        ] = (),
        permitted_paths: tuple[
            AndroidUniverseLinkerGeneratedNamespacePath,
            ...,
        ] = (),
        allowed_libs: tuple[
            AndroidUniverseLinkerGeneratedLibraryExpression,
            ...,
        ] = (),
        provides: tuple[
            AndroidUniverseLinkerGeneratedLibraryExpression,
            ...,
        ] = (),
        requires: tuple[
            AndroidUniverseLinkerGeneratedLibraryExpression,
            ...,
        ] = (),
        link_intents: tuple[
            AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
            ...,
        ] = (),
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        return AndroidUniverseLinkerGeneratedNamespace(
            index=index,
            name=name,
            is_isolated=isolated,
            is_visible=visible,
            search_paths=search_paths,
            permitted_paths=permitted_paths,
            allowed_libs=allowed_libs,
            provides=provides,
            requires=requires,
            link_intents=link_intents,
        )

    def _system_permitted_paths(
        self,
        *,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        treble: bool,
    ) -> tuple[
        AndroidUniverseLinkerGeneratedNamespacePath,
        ...,
    ]:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        paths = [
            static(
                "/system/${LIB}/drm"
            ),
            static(
                "/system/${LIB}/extractors"
            ),
            static(
                "/system/${LIB}/hw"
            ),
            variable(
                value=(
                    None
                    if inputs.system_ext_path is None
                    else inputs.system_ext_path.as_posix()
                ),
                variable="SYSTEM_EXT",
                suffix="/${LIB}",
            ),
            static(
                "/system/framework"
            ),
            static(
                "/system/app"
            ),
            static(
                "/system/priv-app"
            ),
            variable(
                value=(
                    None
                    if inputs.system_ext_path is None
                    else inputs.system_ext_path.as_posix()
                ),
                variable="SYSTEM_EXT",
                suffix="/framework",
            ),
            variable(
                value=(
                    None
                    if inputs.system_ext_path is None
                    else inputs.system_ext_path.as_posix()
                ),
                variable="SYSTEM_EXT",
                suffix="/app",
            ),
            variable(
                value=(
                    None
                    if inputs.system_ext_path is None
                    else inputs.system_ext_path.as_posix()
                ),
                variable="SYSTEM_EXT",
                suffix="/priv-app",
            ),
            static(
                "/vendor/framework"
            ),
            static(
                "/vendor/app"
            ),
            static(
                "/vendor/priv-app"
            ),
            static(
                "/system/vendor/framework"
            ),
            static(
                "/system/vendor/app"
            ),
            static(
                "/system/vendor/priv-app"
            ),
            static(
                "/odm/framework"
            ),
            static(
                "/odm/app"
            ),
            static(
                "/odm/priv-app"
            ),
            static(
                "/oem/app"
            ),
            variable(
                value=(
                    None
                    if inputs.product_path is None
                    else inputs.product_path.as_posix()
                ),
                variable="PRODUCT",
                suffix="/framework",
            ),
            variable(
                value=(
                    None
                    if inputs.product_path is None
                    else inputs.product_path.as_posix()
                ),
                variable="PRODUCT",
                suffix="/app",
            ),
            variable(
                value=(
                    None
                    if inputs.product_path is None
                    else inputs.product_path.as_posix()
                ),
                variable="PRODUCT",
                suffix="/priv-app",
            ),
            static(
                "/data"
            ),
            static(
                "/mnt/expand"
            ),
            static(
                "/apex/com.android.runtime/${LIB}/bionic"
            ),
            static(
                "/system/${LIB}/bootstrap"
            ),
        ]

        if not treble:
            paths.append(
                variable(
                    value=(
                        None
                        if inputs.product_path is None
                        else inputs.product_path.as_posix()
                    ),
                    variable="PRODUCT",
                    suffix="/${LIB}",
                )
            )

        return tuple(
            paths
        )

    def _system_default_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        treble: bool,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        search_paths = [
            static(
                "/system/${LIB}"
            ),
            variable(
                value=(
                    None
                    if inputs.system_ext_path is None
                    else inputs.system_ext_path.as_posix()
                ),
                variable="SYSTEM_EXT",
                suffix="/${LIB}",
            ),
        ]

        if not treble:
            search_paths.extend(
                (
                    variable(
                        value=(
                            None
                            if inputs.product_path is None
                            else inputs.product_path.as_posix()
                        ),
                        variable="PRODUCT",
                        suffix="/${LIB}",
                    ),
                    static(
                        "/vendor/${LIB}"
                    ),
                    static(
                        "/odm/${LIB}"
                    ),
                )
            )

        return self._namespace(
            index=index,
            name="default",
            isolated=treble,
            visible=True,
            search_paths=tuple(
                search_paths
            ),
            permitted_paths=(
                self._system_permitted_paths(
                    inputs=inputs,
                    treble=treble,
                )
                if treble
                else ()
            ),
            provides=tuple(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.system_provided_libraries(
                    accumulate=(
                        linker_semantics
                        .system_context_accumulates_configs
                    ),
                )
            ),
            requires=tuple(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.system_required_libraries(
                    accumulate=(
                        linker_semantics
                        .system_context_accumulates_configs
                    ),
                )
            ),
        )

    def _system_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        treble: bool,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        search_paths = [
            static(
                "/system/${LIB}"
            ),
            variable(
                value=(
                    None
                    if inputs.system_ext_path is None
                    else inputs.system_ext_path.as_posix()
                ),
                variable="SYSTEM_EXT",
                suffix="/${LIB}",
            ),
        ]

        if not treble:
            search_paths.append(
                variable(
                    value=(
                        None
                        if inputs.product_path is None
                        else inputs.product_path.as_posix()
                    ),
                    variable="PRODUCT",
                    suffix="/${LIB}",
                )
            )

        return self._namespace(
            index=index,
            name="system",
            isolated=False,
            visible=False,
            search_paths=tuple(
                search_paths
            ),
            permitted_paths=self._system_permitted_paths(
                inputs=inputs,
                treble=treble,
            ),
            requires=tuple(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.system_required_libraries(
                    accumulate=(
                        linker_semantics
                        .system_context_accumulates_configs
                    ),
                )
            ),
            provides=tuple(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.system_provided_libraries(
                    accumulate=(
                        linker_semantics
                        .system_context_accumulates_configs
                    ),
                )
            ),
        )

    @staticmethod
    def _system_namespace_name(
        section_name: str,
    ) -> str:
        """
        Mirror Context::GetSystemNamespaceName() for generated BASE sections.

        Android uses the section default namespace as the system namespace in
        system/unrestricted sections and the dedicated ``system`` namespace
        everywhere else.
        """
        return (
            "default"
            if section_name
            in {
                "system",
                "unrestricted",
            }
            else "system"
        )

    @classmethod
    def _with_add_llndk_system_link(
        cls,
        *,
        link_intents: tuple[
            AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
            ...,
        ],
        section_name: str,
        insertion_index: int,
    ) -> tuple[
        AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
        ...,
    ]:
        """
        Preserve AddLlndkLibraries() GetLink(system-namespace) semantics.

        AddLlndkLibraries creates or retrieves the system link before adding
        LLNDK requirements. If another builder operation later adds libraries
        to that same link, Android reuses the existing Link object rather than
        creating a second link. Therefore TreeForge keeps one canonical intent
        per target while preserving the target's first-creation order.
        """
        target_namespace = (
            cls._system_namespace_name(
                section_name
            )
        )

        values = list(
            link_intents
        )

        existing_index = next(
            (
                index
                for index, value
                in enumerate(values)
                if value.target_namespace
                == target_namespace
            ),
            None,
        )

        if existing_index is None:
            intent = cls._link_intent(
                target_namespace=target_namespace,
            )
        else:
            intent = values.pop(
                existing_index
            )

        if (
            insertion_index < 0
            or insertion_index > len(values)
        ):
            raise ValueError(
                "insertion_index is outside canonical link order"
            )

        values.insert(
            insertion_index,
            intent,
        )

        return tuple(
            values
        )

    def _vendor_default_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path

        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.vendor_default_link_rules
            ),
            inputs=inputs,
            section_name="vendor",
        )

        requires = [
            self._variable_library(
                "LLNDK_LIBRARIES_VENDOR",
                "",
            ),
            *(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.vendor_required_libraries
            ),
        ]

        provides = [
            *(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.vendor_provided_libraries
            ),
        ]

        return self._namespace(
            index=index,
            name="default",
            isolated=True,
            visible=True,
            search_paths=tuple(
                static(
                    value
                )
                for value
                in (
                    "/odm/${LIB}",
                    "/vendor/${LIB}",
                    "/vendor/${LIB}/hw",
                    "/vendor/${LIB}/egl",
                )
            ),
            permitted_paths=tuple(
                static(
                    value
                )
                for value
                in (
                    "/odm",
                    "/vendor",
                    "/system/vendor",
                )
            ),
            provides=tuple(
                provides
            ),
            requires=tuple(
                requires
            ),
            link_intents=tuple(
                link_intents
            ),
        )

    def _product_namespace(
        self,
        *,
        index: int,
        name: str,
        section_name: str,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        variable = self._variable_namespace_path

        product_value = (
            None
            if inputs.product_path is None
            else inputs.product_path.as_posix()
        )

        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.product_link_rules
            ),
            inputs=inputs,
            section_name=section_name,
        )

        link_intents = self._with_add_llndk_system_link(
            link_intents=link_intents,
            section_name=section_name,
            insertion_index=0,
        )

        return self._namespace(
            index=index,
            name=name,
            isolated=True,
            visible=True,
            search_paths=(
                variable(
                    value=product_value,
                    variable="PRODUCT",
                    suffix="/${LIB}",
                    fallback="product",
                ),
            ),
            permitted_paths=(
                variable(
                    value=product_value,
                    variable="PRODUCT",
                    fallback="product",
                ),
            ),
            provides=tuple(
                self._literal_library(
                    library_name
                )
                for library_name
                in inputs.product_provided_libraries
            ),
            requires=(
                self._variable_library(
                    "LLNDK_LIBRARIES_PRODUCT",
                    "",
                ),
                *(
                    self._literal_library(
                        library_name
                    )
                    for library_name
                    in inputs.product_required_libraries
                ),
            ),
            link_intents=link_intents,
        )

    def _unrestricted_default_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        return self._namespace(
            index=index,
            name="default",
            isolated=False,
            visible=True,
            search_paths=(
                static(
                    "/system/${LIB}"
                ),
                variable(
                    value=(
                        None
                        if inputs.system_ext_path is None
                        else inputs.system_ext_path.as_posix()
                    ),
                    variable="SYSTEM_EXT",
                    suffix="/${LIB}",
                ),
                static(
                    "/odm/${LIB}"
                ),
                static(
                    "/vendor/${LIB}"
                ),
                variable(
                    value=(
                        None
                        if inputs.product_path is None
                        else inputs.product_path.as_posix()
                    ),
                    variable="PRODUCT",
                    suffix="/${LIB}",
                ),
            ),
        )

    def _postinstall_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        return self._namespace(
            index=index,
            name="default",
            isolated=False,
            visible=False,
            search_paths=(
                static(
                    "/system/${LIB}"
                ),
                variable(
                    value=(
                        None
                        if inputs.system_ext_path is None
                        else inputs.system_ext_path.as_posix()
                    ),
                    variable="SYSTEM_EXT",
                    suffix="/${LIB}",
                ),
                variable(
                    value=(
                        None
                        if inputs.product_path is None
                        else inputs.product_path.as_posix()
                    ),
                    variable="PRODUCT",
                    suffix="/${LIB}",
                ),
            ),
        )

    def _isolated_default_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.isolated_link_rules
            ),
            inputs=inputs,
            section_name="isolated",
        )

        return self._namespace(
            index=index,
            name="default",
            isolated=True,
            visible=False,
            link_intents=link_intents,
        )

    def _sphal_namespace(
        self,
        *,
        index: int,
        section_name: str,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        unrestricted: bool,
        vendor_vndk_defined: bool,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path

        permitted_paths = [
            static(
                "/odm/${LIB}"
            ),
            static(
                "/vendor/${LIB}"
            ),
            static(
                "/vendor/odm/${LIB}"
            ),
            static(
                "/system/vendor/${LIB}"
            ),
        ]

        if not vendor_vndk_defined:
            permitted_paths.append(
                static(
                    "/data"
                )
            )

        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.sphal_link_rules
            ),
            inputs=inputs,
            section_name=section_name,
        )

        link_intents = self._with_add_llndk_system_link(
            link_intents=link_intents,
            section_name=section_name,
            insertion_index=0,
        )

        return self._namespace(
            index=index,
            name="sphal",
            isolated=not unrestricted,
            visible=True,
            search_paths=tuple(
                static(
                    value
                )
                for value
                in (
                    "/odm/${LIB}",
                    "/vendor/${LIB}",
                    "/vendor/${LIB}/egl",
                    "/vendor/${LIB}/hw",
                )
            ),
            permitted_paths=tuple(
                permitted_paths
            ),
            requires=(
                self._variable_library(
                    "LLNDK_LIBRARIES_VENDOR",
                    "",
                ),
            ),
            link_intents=tuple(
                link_intents
            ),
        )

    def _rs_namespace(
        self,
        *,
        index: int,
        section_name: str,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        unrestricted: bool,
        vendor_vndk_defined: bool,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        search_paths = [
            static(
                "/odm/${LIB}/vndk-sp"
            ),
            static(
                "/vendor/${LIB}/vndk-sp"
            ),
        ]

        if vendor_vndk_defined:
            search_paths.append(
                variable(
                    value=inputs.vendor_vndk_version,
                    variable="VENDOR_VNDK_VERSION",
                    prefix="/apex/com.android.vndk.v",
                    suffix="/${LIB}",
                )
            )

        search_paths.extend(
            (
                static(
                    "/odm/${LIB}"
                ),
                static(
                    "/vendor/${LIB}"
                ),
            )
        )

        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.rs_link_rules
            ),
            inputs=inputs,
            section_name=section_name,
        )

        link_intents = self._with_add_llndk_system_link(
            link_intents=link_intents,
            section_name=section_name,
            insertion_index=0,
        )

        return self._namespace(
            index=index,
            name="rs",
            isolated=not unrestricted,
            visible=True,
            search_paths=tuple(
                search_paths
            ),
            permitted_paths=tuple(
                static(
                    value
                )
                for value
                in (
                    "/odm/${LIB}",
                    "/vendor/${LIB}",
                    "/system/vendor/${LIB}",
                    "/data",
                )
            ),
            requires=(
                self._variable_library(
                    "LLNDK_LIBRARIES_VENDOR",
                    "",
                ),
            ),
            link_intents=link_intents,
        )

    def _vndk_namespace(
        self,
        *,
        index: int,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        section_name: str,
        product: bool,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        system_or_unrestricted = (
            section_name
            in {
                "system",
                "unrestricted",
            }
        )

        if product:
            name = (
                "vndk_product"
                if system_or_unrestricted
                else "vndk"
            )

            product_value = (
                None
                if inputs.product_path is None
                else inputs.product_path.as_posix()
            )

            lib_paths = (
                variable(
                    value=product_value,
                    variable="PRODUCT",
                    suffix="/${LIB}",
                ),
            )

            version = (
                inputs.product_vndk_version
            )

            version_variable = (
                "PRODUCT_VNDK_VERSION"
            )

        else:
            name = "vndk"

            lib_paths = (
                static(
                    "/odm/${LIB}"
                ),
                static(
                    "/vendor/${LIB}"
                ),
            )

            version = (
                inputs.vendor_vndk_version
            )

            version_variable = (
                "VENDOR_VNDK_VERSION"
            )

        search_paths = []

        for lib_path in lib_paths:
            if lib_path.path is None:
                search_paths.append(
                    AndroidUniverseLinkerGeneratedNamespacePath(
                        path=None,
                        variable=lib_path.variable,
                        prefix=lib_path.prefix,
                        suffix=(
                            lib_path.suffix
                            + "/vndk-sp"
                        ),
                        fallback=lib_path.fallback,
                    )
                )
            else:
                search_paths.append(
                    AndroidUniverseLinkerGeneratedNamespacePath(
                        path=PurePosixPath(
                            lib_path.path.as_posix()
                            + "/vndk-sp"
                        ),
                        variable=lib_path.variable,
                        prefix=lib_path.prefix,
                        suffix=(
                            lib_path.suffix
                            + "/vndk-sp"
                            if lib_path.variable is not None
                            else ""
                        ),
                        fallback=lib_path.fallback,
                    )
                    if lib_path.variable is not None
                    else static(
                        lib_path.path.as_posix()
                        + "/vndk-sp"
                    )
                )

            if not system_or_unrestricted:
                if lib_path.path is None:
                    search_paths.append(
                        AndroidUniverseLinkerGeneratedNamespacePath(
                            path=None,
                            variable=lib_path.variable,
                            prefix=lib_path.prefix,
                            suffix=(
                                lib_path.suffix
                                + "/vndk"
                            ),
                            fallback=lib_path.fallback,
                        )
                    )
                else:
                    search_paths.append(
                        AndroidUniverseLinkerGeneratedNamespacePath(
                            path=PurePosixPath(
                                lib_path.path.as_posix()
                                + "/vndk"
                            ),
                            variable=lib_path.variable,
                            prefix=lib_path.prefix,
                            suffix=(
                                lib_path.suffix
                                + "/vndk"
                                if lib_path.variable is not None
                                else ""
                            ),
                            fallback=lib_path.fallback,
                        )
                        if lib_path.variable is not None
                        else static(
                            lib_path.path.as_posix()
                            + "/vndk"
                        )
                    )

        search_paths.append(
            variable(
                value=version,
                variable=version_variable,
                prefix="/apex/com.android.vndk.v",
                suffix="/${LIB}",
            )
        )

        if system_or_unrestricted:
            search_paths.extend(
                lib_paths
            )

        permitted_paths = []

        if not product:
            permitted_paths.extend(
                static(
                    value
                )
                for value
                in (
                    "/odm/${LIB}/hw",
                    "/odm/${LIB}/egl",
                    "/vendor/${LIB}/hw",
                    "/vendor/${LIB}/egl",
                    "/system/vendor/${LIB}/hw",
                    "/system/vendor/${LIB}/egl",
                )
            )

            permitted_paths.append(
                variable(
                    value=inputs.vendor_vndk_version,
                    variable="VENDOR_VNDK_VERSION",
                    prefix="/apex/com.android.vndk.v",
                    suffix="/${LIB}/hw",
                )
            )

        requires = [
            self._variable_library(
                (
                    "LLNDK_LIBRARIES_PRODUCT"
                    if product
                    else "LLNDK_LIBRARIES_VENDOR"
                ),
                "",
            ),
        ]

        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.vndk_link_rules
            ),
            inputs=inputs,
            section_name=section_name,
        )

        link_intents = self._with_add_llndk_system_link(
            link_intents=link_intents,
            section_name=section_name,
            insertion_index=(
                1
                if section_name
                in {
                    "vendor",
                    "product",
                }
                else 0
            ),
        )

        return self._namespace(
            index=index,
            name=name,
            isolated=True,
            visible=system_or_unrestricted,
            search_paths=tuple(
                search_paths
            ),
            permitted_paths=tuple(
                permitted_paths
            ),
            requires=tuple(
                requires
            ),
            link_intents=tuple(
                link_intents
            ),
        )

    def _vndk_in_system_namespace(
        self,
        *,
        index: int,
        section_name: str,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        linker_semantics: AndroidLinkerSemanticProfile,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        static = self._static_namespace_path
        variable = self._variable_namespace_path

        allowed_libs = tuple(
            self._profile_library_expression(
                expression
            )
            for expression
            in linker_semantics.vndk_in_system_allowed_libraries
        )

        link_intents = self._profile_link_intents(
            rules=(
                linker_semantics.vndk_in_system_link_rules
            ),
            inputs=inputs,
            section_name=section_name,
        )

        link_intents = self._with_add_llndk_system_link(
            link_intents=link_intents,
            section_name=section_name,
            insertion_index=0,
        )

        requires = (
            self._variable_library(
                (
                    "LLNDK_LIBRARIES_PRODUCT"
                    if AndroidRuntimeLinkerSectionSemantics.is_product(section_name)
                    else "LLNDK_LIBRARIES_VENDOR"
                ),
                "",
            ),
        )

        return self._namespace(
            index=index,
            name="vndk_in_system",
            isolated=True,
            visible=False,
            search_paths=(
                static(
                    "/system/${LIB}"
                ),
                variable(
                    value=(
                        None
                        if inputs.system_ext_path is None
                        else inputs.system_ext_path.as_posix()
                    ),
                    variable="SYSTEM_EXT",
                    suffix="/${LIB}",
                ),
            ),
            allowed_libs=allowed_libs,
            requires=requires,
            link_intents=link_intents,
        )

    def _profile_additional_section_namespace(
        self,
        *,
        index: int,
        section,
    ) -> AndroidUniverseLinkerGeneratedNamespace:
        """
        Construct one release-profile-selected BASE namespace.

        The generic builder knows only the typed descriptor. Release-specific
        section identity and paths remain entirely in the semantic profile.
        """
        static = self._static_namespace_path

        return self._namespace(
            index=index,
            name=section.namespace_name,
            isolated=section.namespace_isolated,
            visible=section.namespace_visible,
            search_paths=tuple(
                static(
                    value
                )
                for value
                in section.namespace_search_paths
            ),
        )

    def _section_namespaces(
        self,
        *,
        section_name: str,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        treble: bool,
        semantic_profile: AndroidSemanticVersionProfile,
    ) -> tuple[
        AndroidUniverseLinkerGeneratedNamespace,
        ...,
    ]:
        namespaces = []

        def append(
            namespace: AndroidUniverseLinkerGeneratedNamespace,
        ) -> None:
            namespaces.append(
                namespace
            )

        def index() -> int:
            return len(
                namespaces
            )

        vendor_vndk_defined = (
            inputs.vendor_vndk_version_defined
        )

        product_vndk_defined = (
            inputs.product_vndk_version_defined
        )

        if AndroidRuntimeLinkerSectionSemantics.is_system(section_name):
            append(
                self._system_default_namespace(
                    index=index(),
                    inputs=inputs,
                    treble=treble,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            if treble:
                append(
                    self._sphal_namespace(
                        index=index(),
                        section_name=section_name,
                        inputs=inputs,
                        unrestricted=False,
                        vendor_vndk_defined=(
                            vendor_vndk_defined
                        ),
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

                append(
                    self._rs_namespace(
                        index=index(),
                        section_name=section_name,
                        inputs=inputs,
                        unrestricted=False,
                        vendor_vndk_defined=(
                            vendor_vndk_defined
                        ),
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

                append(
                    self._product_namespace(
                        index=index(),
                        name="product",
                        section_name=section_name,
                        inputs=inputs,
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

                if inputs.vndk_available:
                    if vendor_vndk_defined:
                        append(
                            self._vndk_namespace(
                                index=index(),
                                inputs=inputs,
                                section_name=(
                                    section_name
                                ),
                                product=False,
                                linker_semantics=(
                                    semantic_profile.linker
                                ),
                            )
                        )

                    if product_vndk_defined:
                        append(
                            self._vndk_namespace(
                                index=index(),
                                inputs=inputs,
                                section_name=(
                                    section_name
                                ),
                                product=True,
                                linker_semantics=(
                                    semantic_profile.linker
                                ),
                            )
                        )

        elif AndroidRuntimeLinkerSectionSemantics.is_vendor(section_name):
            append(
                self._vendor_default_namespace(
                    index=index(),
                    inputs=inputs,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            if vendor_vndk_defined:
                append(
                    self._vndk_namespace(
                        index=index(),
                        inputs=inputs,
                        section_name=section_name,
                        product=False,
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

            append(
                self._system_namespace(
                    index=index(),
                    inputs=inputs,
                    treble=treble,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            append(
                self._rs_namespace(
                    index=index(),
                    section_name=section_name,
                    inputs=inputs,
                    unrestricted=False,
                    vendor_vndk_defined=(
                        vendor_vndk_defined
                    ),
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            if (
                inputs.vndk_in_system_namespace
                is True
            ):
                append(
                    self._vndk_in_system_namespace(
                        index=index(),
                        section_name=section_name,
                        inputs=inputs,
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

        elif AndroidRuntimeLinkerSectionSemantics.is_product(section_name):
            append(
                self._product_namespace(
                    index=index(),
                    name="default",
                    section_name=section_name,
                    inputs=inputs,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            if product_vndk_defined:
                append(
                    self._vndk_namespace(
                        index=index(),
                        inputs=inputs,
                        section_name=section_name,
                        product=True,
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

            append(
                self._system_namespace(
                    index=index(),
                    inputs=inputs,
                    treble=treble,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            if (
                inputs.vndk_in_system_namespace
                is True
            ):
                append(
                    self._vndk_in_system_namespace(
                        index=index(),
                        section_name=section_name,
                        inputs=inputs,
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

        elif AndroidRuntimeLinkerSectionSemantics.is_unrestricted(section_name):
            append(
                self._unrestricted_default_namespace(
                    index=index(),
                    inputs=inputs,
                )
            )

            if treble:
                append(
                    self._sphal_namespace(
                        index=index(),
                        section_name=section_name,
                        inputs=inputs,
                        unrestricted=True,
                        vendor_vndk_defined=(
                            vendor_vndk_defined
                        ),
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

                if vendor_vndk_defined:
                    append(
                        self._vndk_namespace(
                            index=index(),
                            inputs=inputs,
                            section_name=(
                                section_name
                            ),
                            product=False,
                            linker_semantics=(
                                semantic_profile.linker
                            ),
                        )
                    )

                append(
                    self._rs_namespace(
                        index=index(),
                        section_name=section_name,
                        inputs=inputs,
                        unrestricted=True,
                        vendor_vndk_defined=(
                            vendor_vndk_defined
                        ),
                        linker_semantics=(
                            semantic_profile.linker
                        ),
                    )
                )

        elif AndroidRuntimeLinkerSectionSemantics.is_postinstall(section_name):
            append(
                self._postinstall_namespace(
                    index=index(),
                    inputs=inputs,
                )
            )

        elif AndroidRuntimeLinkerSectionSemantics.is_isolated(section_name):
            append(
                self._isolated_default_namespace(
                    index=index(),
                    inputs=inputs,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

            append(
                self._system_namespace(
                    index=index(),
                    inputs=inputs,
                    treble=treble,
                    linker_semantics=(
                        semantic_profile.linker
                    ),
                )
            )

        else:
            profile_sections = tuple(
                section
                for section
                in (
                    semantic_profile
                    .linker
                    .base_additional_sections
                )
                if section.section_name == section_name
            )

            if len(
                profile_sections
            ) != 1:
                raise AssertionError(
                    "unknown generated section: "
                    f"{section_name!r}"
                )

            append(
                self._profile_additional_section_namespace(
                    index=index(),
                    section=profile_sections[
                        0
                    ],
                )
            )

        return tuple(
            namespaces
        )

    def build(
        self,
        *,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
        semantic_profile: AndroidSemanticVersionProfile,
    ) -> AndroidUniverseLinkerGeneratedBaseConfiguration:
        if not isinstance(
            inputs,
            AndroidUniverseLinkerGeneratedConfigurationInputs,
        ):
            raise TypeError(
                "inputs must be an "
                "AndroidUniverseLinkerGeneratedConfigurationInputs"
            )

        if not isinstance(
            semantic_profile,
            AndroidSemanticVersionProfile,
        ):
            raise TypeError(
                "semantic_profile must be an "
                "AndroidSemanticVersionProfile"
            )

        treble = inputs.treble_enabled

        if treble is None:
            return AndroidUniverseLinkerGeneratedBaseConfiguration(
                inputs=inputs,
                sections=(),
                directory_routes=(),
                status=(
                    AndroidUniverseLinkerGeneratedConfigurationStatus
                    .UNRESOLVED
                ),
                unresolved_reasons=(
                    "canonical Treble state is unresolved",
                ),
            )

        if treble:
            section_names = (
                "system",
                "vendor",
                "product",
                "unrestricted",
                *(
                    section.section_name
                    for section
                    in (
                        semantic_profile
                        .linker
                        .base_additional_sections
                    )
                ),
                "postinstall",
                "isolated",
            )
        else:
            section_names = (
                "system",
                "unrestricted",
                *(
                    section.section_name
                    for section
                    in (
                        semantic_profile
                        .linker
                        .base_additional_sections
                    )
                ),
                "postinstall",
                "isolated",
            )

        sections = tuple(
            AndroidUniverseLinkerGeneratedSection(
                index=index,
                name=name,
                namespaces=(
                    self._section_namespaces(
                        section_name=name,
                        inputs=inputs,
                        treble=treble,
                        semantic_profile=(
                            semantic_profile
                        ),
                    )
                ),
            )
            for index, name
            in enumerate(
                section_names
            )
        )

        #
        # Exact CreateBaseConfiguration source order.
        #
        route_specs = (
            ("static", "/system/bin", "system"),
            ("static", "/system/xbin", "system"),
            (
                "system_ext",
                "bin",
                "system",
            ),
            (
                "product",
                "bin",
                "product",
            ),

            ("static", "/odm/bin", "vendor"),
            ("static", "/vendor/bin", "vendor"),
            (
                "static",
                "/data/nativetest/odm",
                "vendor",
            ),
            (
                "static",
                "/data/nativetest64/odm",
                "vendor",
            ),
            (
                "static",
                "/data/benchmarktest/odm",
                "vendor",
            ),
            (
                "static",
                "/data/benchmarktest64/odm",
                "vendor",
            ),
            (
                "static",
                "/data/nativetest/vendor",
                "vendor",
            ),
            (
                "static",
                "/data/nativetest64/vendor",
                "vendor",
            ),
            (
                "static",
                "/data/benchmarktest/vendor",
                "vendor",
            ),
            (
                "static",
                "/data/benchmarktest64/vendor",
                "vendor",
            ),

            (
                "static",
                "/data/nativetest/unrestricted",
                "unrestricted",
            ),
            (
                "static",
                "/data/nativetest64/unrestricted",
                "unrestricted",
            ),

            (
                "static",
                "/data/local/tmp/isolated",
                "isolated",
            ),

            (
                "static",
                "/data/local/tests/product",
                "product",
            ),
            (
                "static",
                "/data/local/tests/system",
                "system",
            ),
            (
                "static",
                "/data/local/tests/unrestricted",
                "unrestricted",
            ),
            (
                "static",
                "/data/local/tests/vendor",
                "vendor",
            ),

            (
                "static",
                "/data/local/tmp",
                "unrestricted",
            ),

            *(
                (
                    "static",
                    path,
                    section_name,
                )
                for path, section_name
                in (
                    semantic_profile
                    .linker
                    .base_additional_directory_routes
                )
            ),

            (
                "static",
                "/postinstall",
                "postinstall",
            ),

            (
                "static",
                "/data",
                "system",
            ),
            (
                "static",
                "/tmp",
                "system",
            ),

            (
                "product",
                "app",
                "system",
            ),
        )

        #
        # AOSP RemoveSection() removes all routes targeting vendor/product
        # when Treble is disabled while retaining the relative order of all
        # surviving routes.
        #
        if not treble:
            route_specs = tuple(
                spec
                for spec
                in route_specs
                if spec[
                    2
                ]
                not in {
                    "vendor",
                    "product",
                }
            )

        routes = []

        for spec in route_specs:
            route_kind = spec[
                0
            ]

            suffix_or_path = spec[
                1
            ]

            section_name = spec[
                2
            ]

            index = len(
                routes
            )

            if route_kind == "static":
                route = self._static_route(
                    index=index,
                    path=suffix_or_path,
                    section_name=section_name,
                )

            elif route_kind == "product":
                route = self._variable_route(
                    index=index,
                    root=inputs.product_path,
                    variable="PRODUCT",
                    suffix=suffix_or_path,
                    section_name=section_name,
                )

            elif route_kind == "system_ext":
                route = self._variable_route(
                    index=index,
                    root=inputs.system_ext_path,
                    variable="SYSTEM_EXT",
                    suffix=suffix_or_path,
                    section_name=section_name,
                )

            else:
                raise AssertionError(
                    "unknown generated route kind: "
                    f"{route_kind!r}"
                )

            routes.append(
                route
            )

        routes = tuple(
            routes
        )

        unresolved_reasons = []

        unresolved_variables = tuple(
            route.variable
            for route
            in routes
            if (
                route.variable is not None
                and not route.resolved
            )
        )

        for variable in tuple(
            dict.fromkeys(
                unresolved_variables
            )
        ):
            unresolved_reasons.append(
                "canonical runtime value for "
                f"{variable} is unresolved"
            )

        unresolved_namespace_variables = tuple(
            path.variable
            for section
            in sections
            for namespace
            in section.namespaces
            for path
            in (
                namespace.search_paths
                + namespace.permitted_paths
            )
            if (
                path.variable is not None
                and not path.resolved
            )
        )

        for variable in tuple(
            dict.fromkeys(
                unresolved_namespace_variables
            )
        ):
            reason = (
                "canonical runtime value for "
                f"{variable} is unresolved"
            )

            if reason not in unresolved_reasons:
                unresolved_reasons.append(
                    reason
                )

        if (
            inputs.vndk_in_system_namespace
            is None
            and any(
                section.name
                in {
                    "vendor",
                    "product",
                }
                for section
                in sections
            )
        ):
            unresolved_reasons.append(
                "canonical VNDK-in-system namespace state is unresolved"
            )

        status = (
            AndroidUniverseLinkerGeneratedConfigurationStatus.RESOLVED
            if not unresolved_reasons
            else (
                AndroidUniverseLinkerGeneratedConfigurationStatus
                .UNRESOLVED
            )
        )

        return AndroidUniverseLinkerGeneratedBaseConfiguration(
            inputs=inputs,
            sections=sections,
            directory_routes=routes,
            status=status,
            unresolved_reasons=tuple(
                unresolved_reasons
            ),
        )

