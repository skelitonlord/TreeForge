from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.linker.model import (
    AndroidLinkerConfigurationAssignment,
    AndroidLinkerConfigurationSection,
    ParsedAndroidLinkerConfiguration,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerDirectoryRoute:
    """
    One canonical ``dir.<section>`` route from ld.config.txt.

    The exact Parsing assignment is retained as provenance.
    """

    section_name: str
    path: str
    assignment: AndroidLinkerConfigurationAssignment

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

        if (
            not isinstance(
                self.path,
                str,
            )
            or not self.path
        ):
            raise ValueError(
                "path must be a non-empty string"
            )

        if not isinstance(
            self.assignment,
            AndroidLinkerConfigurationAssignment,
        ):
            raise TypeError(
                "assignment must be an "
                "AndroidLinkerConfigurationAssignment"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerNamespaceLink:
    """
    One canonical linker namespace edge.

    ``shared_libs`` contains the effective ordered allowlist after applying
    the source ``=`` / ``+=`` assignments.

    Every consumed source assignment is preserved exactly in ``assignments``.
    """

    target_namespace: str
    shared_libs: tuple[
        str,
        ...,
    ]
    allow_all_shared_libs: bool
    assignments: tuple[
        AndroidLinkerConfigurationAssignment,
        ...,
    ]

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
            self.shared_libs,
            tuple,
        ):
            raise TypeError(
                "shared_libs must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            for value in self.shared_libs
        ):
            raise ValueError(
                "shared_libs must contain only non-empty strings"
            )

        if not isinstance(
            self.allow_all_shared_libs,
            bool,
        ):
            raise TypeError(
                "allow_all_shared_libs must be a bool"
            )

        if not isinstance(
            self.assignments,
            tuple,
        ):
            raise TypeError(
                "assignments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerConfigurationAssignment,
            )
            for value in self.assignments
        ):
            raise TypeError(
                "assignments must contain only "
                "AndroidLinkerConfigurationAssignment instances"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerNamespace:
    """
    Effective semantics for one linker namespace in one exact section.

    Namespace identity is local to its containing configuration and section.
    Literal path expressions such as ``${LIB}`` remain unexpanded here.
    """

    name: str

    isolated: bool
    visible: bool

    search_paths: tuple[
        str,
        ...,
    ]
    permitted_paths: tuple[
        str,
        ...,
    ]

    asan_search_paths: tuple[
        str,
        ...,
    ]
    asan_permitted_paths: tuple[
        str,
        ...,
    ]

    hwasan_search_paths: tuple[
        str,
        ...,
    ]
    hwasan_permitted_paths: tuple[
        str,
        ...,
    ]

    allowed_libs: tuple[
        str,
        ...,
    ]

    links: tuple[
        AndroidUniverseLinkerNamespaceLink,
        ...,
    ]

    assignments: tuple[
        AndroidLinkerConfigurationAssignment,
        ...,
    ]

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
            self.isolated,
            bool,
        ):
            raise TypeError(
                "isolated must be a bool"
            )

        if not isinstance(
            self.visible,
            bool,
        ):
            raise TypeError(
                "visible must be a bool"
            )

        for field_name in (
            "search_paths",
            "permitted_paths",
            "asan_search_paths",
            "asan_permitted_paths",
            "hwasan_search_paths",
            "hwasan_permitted_paths",
            "allowed_libs",
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
                    str,
                )
                and value
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain only non-empty strings"
                )

        if not isinstance(
            self.links,
            tuple,
        ):
            raise TypeError(
                "links must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseLinkerNamespaceLink,
            )
            for value in self.links
        ):
            raise TypeError(
                "links must contain only "
                "AndroidUniverseLinkerNamespaceLink instances"
            )

        if not isinstance(
            self.assignments,
            tuple,
        ):
            raise TypeError(
                "assignments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerConfigurationAssignment,
            )
            for value in self.assignments
        ):
            raise TypeError(
                "assignments must contain only "
                "AndroidLinkerConfigurationAssignment instances"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerSection:
    """
    Canonical semantics for one exact ld.config.txt section.
    """

    source_section: AndroidLinkerConfigurationSection

    directory_routes: tuple[
        AndroidUniverseLinkerDirectoryRoute,
        ...,
    ]

    namespaces: tuple[
        AndroidUniverseLinkerNamespace,
        ...,
    ]

    assignments: tuple[
        AndroidLinkerConfigurationAssignment,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_section,
            AndroidLinkerConfigurationSection,
        ):
            raise TypeError(
                "source_section must be an "
                "AndroidLinkerConfigurationSection"
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
                value,
                AndroidUniverseLinkerDirectoryRoute,
            )
            for value in self.directory_routes
        ):
            raise TypeError(
                "directory_routes must contain only "
                "AndroidUniverseLinkerDirectoryRoute instances"
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
                value,
                AndroidUniverseLinkerNamespace,
            )
            for value in self.namespaces
        ):
            raise TypeError(
                "namespaces must contain only "
                "AndroidUniverseLinkerNamespace instances"
            )

        namespace_names = tuple(
            value.name
            for value in self.namespaces
        )

        if len(
            namespace_names
        ) != len(
            set(
                namespace_names
            )
        ):
            raise ValueError(
                "namespace identities must be unique within a section"
            )

        if "default" not in namespace_names:
            raise ValueError(
                "every linker section must contain a default namespace"
            )

        if not isinstance(
            self.assignments,
            tuple,
        ):
            raise TypeError(
                "assignments must be a tuple"
            )


from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContext,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerTextConfigurationSemantics:
    """
    Semantic Universe interpretation of one exact Parsed ld.config.txt.

    Parsing source identity is retained exactly. Unknown or unsupported
    assignments are preserved rather than discarded.
    """

    source: ParsedAndroidLinkerConfiguration

    runtime_context: AndroidUniverseRuntimeContext

    sections: tuple[
        AndroidUniverseLinkerSection,
        ...,
    ]

    uninterpreted_assignments: tuple[
        AndroidLinkerConfigurationAssignment,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidLinkerConfiguration,
        ):
            raise TypeError(
                "source must be a ParsedAndroidLinkerConfiguration"
            )

        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
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
                value,
                AndroidUniverseLinkerSection,
            )
            for value in self.sections
        ):
            raise TypeError(
                "sections must contain only "
                "AndroidUniverseLinkerSection instances"
            )

        if not isinstance(
            self.uninterpreted_assignments,
            tuple,
        ):
            raise TypeError(
                "uninterpreted_assignments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidLinkerConfigurationAssignment,
            )
            for value in self.uninterpreted_assignments
        ):
            raise TypeError(
                "uninterpreted_assignments must contain only "
                "AndroidLinkerConfigurationAssignment instances"
            )

        interpreted_ids = {
            id(
                assignment
            )
            for section in self.sections
            for assignment in section.assignments
        }

        uninterpreted_ids = {
            id(
                assignment
            )
            for assignment in self.uninterpreted_assignments
        }

        if interpreted_ids & uninterpreted_ids:
            raise ValueError(
                "a linker assignment cannot be both interpreted "
                "and uninterpreted"
            )

        if (
            len(
                interpreted_ids
            )
            + len(
                uninterpreted_ids
            )
            != len(
                self.source.assignments
            )
        ):
            raise ValueError(
                "Linker semantic interpretation must account for every "
                "Parsing assignment exactly once"
            )


from enum import Enum

from treeforge.android.parsing.linker.model import (
    AndroidLinkerProtobufContribution,
    AndroidLinkerProtobufUnknownField,
    ParsedAndroidLinkerProtobufConfiguration,
)


class AndroidUniverseLinkerProtobufUsage(
    str,
    Enum,
):
    """
    Generic Android consumption role for one linker.config.pb source.

    This classifies only the canonical Android location/context in which the
    protobuf participates. It does not resolve competing source observations.
    """

    APEX_LOCAL = "apex_local"
    SYSTEM_CONTEXT = "system_context"
    VENDOR_CONTEXT = "vendor_context"
    PRODUCT_CONTEXT = "product_context"
    UNCLASSIFIED = "unclassified"


class AndroidUniverseLinkerVisibilityPolicy(
    str,
    Enum,
):
    """
    Presence-aware linker namespace visibility policy.

    AOSP treats an absent protobuf visibility field as false, but the
    distinction between absent and explicitly false remains canonical evidence.
    """

    DEFAULT_HIDDEN = "default_hidden"
    EXPLICIT_HIDDEN = "explicit_hidden"
    EXPLICIT_VISIBLE = "explicit_visible"


class AndroidUniverseLinkerProtobufLibraryPolicyKind(
    str,
    Enum,
):
    PROVIDE = "provide"
    REQUIRE = "require"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerProtobufPermittedPath:
    source: ParsedAndroidLinkerProtobufConfiguration
    index: int
    path: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidLinkerProtobufConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidLinkerProtobufConfiguration"
            )

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
                self.path,
                str,
            )
            or not self.path
        ):
            raise ValueError(
                "path must be a non-empty string"
            )

        if (
            self.index
            >= len(
                self.source.permitted_paths
            )
            or self.source.permitted_paths[
                self.index
            ]
            != self.path
        ):
            raise ValueError(
                "permitted path must preserve exact Parsing "
                "index and value"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerProtobufLibraryPolicy:
    source: ParsedAndroidLinkerProtobufConfiguration
    kind: AndroidUniverseLinkerProtobufLibraryPolicyKind
    index: int
    library_name: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidLinkerProtobufConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidLinkerProtobufConfiguration"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseLinkerProtobufLibraryPolicyKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseLinkerProtobufLibraryPolicyKind"
            )

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
                self.library_name,
                str,
            )
            or not self.library_name
        ):
            raise ValueError(
                "library_name must be a non-empty string"
            )

        values = (
            self.source.provide_libs
            if (
                self.kind
                is AndroidUniverseLinkerProtobufLibraryPolicyKind
                .PROVIDE
            )
            else self.source.require_libs
        )

        if (
            self.index
            >= len(
                values
            )
            or values[
                self.index
            ]
            != self.library_name
        ):
            raise ValueError(
                "library policy must preserve exact Parsing "
                "index and value"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerProtobufContributionSemantics:
    source: ParsedAndroidLinkerProtobufConfiguration
    index: int
    contribution: AndroidLinkerProtobufContribution

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidLinkerProtobufConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidLinkerProtobufConfiguration"
            )

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

        if not isinstance(
            self.contribution,
            AndroidLinkerProtobufContribution,
        ):
            raise TypeError(
                "contribution must be an "
                "AndroidLinkerProtobufContribution"
            )

        if (
            self.index
            >= len(
                self.source.contributions
            )
            or self.source.contributions[
                self.index
            ]
            is not self.contribution
        ):
            raise ValueError(
                "contribution must preserve exact Parsing identity "
                "and index"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerProtobufConfigurationSemantics:
    """
    Source-local semantic interpretation of one linker.config.pb.

    This intentionally does not resolve provide/require relationships between
    namespaces and does not join APEX manifests, native-library policy, or ELF.
    """

    source: ParsedAndroidLinkerProtobufConfiguration

    runtime_context: AndroidUniverseRuntimeContext

    usage: AndroidUniverseLinkerProtobufUsage

    visibility_policy: AndroidUniverseLinkerVisibilityPolicy
    effective_visible: bool

    permitted_paths: tuple[
        AndroidUniverseLinkerProtobufPermittedPath,
        ...,
    ]

    provided_libraries: tuple[
        AndroidUniverseLinkerProtobufLibraryPolicy,
        ...,
    ]

    required_libraries: tuple[
        AndroidUniverseLinkerProtobufLibraryPolicy,
        ...,
    ]

    contributions: tuple[
        AndroidUniverseLinkerProtobufContributionSemantics,
        ...,
    ]

    unknown_fields: tuple[
        AndroidLinkerProtobufUnknownField,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidLinkerProtobufConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidLinkerProtobufConfiguration"
            )

        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        if not isinstance(
            self.usage,
            AndroidUniverseLinkerProtobufUsage,
        ):
            raise TypeError(
                "usage must be an AndroidUniverseLinkerProtobufUsage"
            )

        if not isinstance(
            self.visibility_policy,
            AndroidUniverseLinkerVisibilityPolicy,
        ):
            raise TypeError(
                "visibility_policy must be an "
                "AndroidUniverseLinkerVisibilityPolicy"
            )

        if not isinstance(
            self.effective_visible,
            bool,
        ):
            raise TypeError(
                "effective_visible must be a bool"
            )

        expected_visibility_policy = (
            AndroidUniverseLinkerVisibilityPolicy.EXPLICIT_VISIBLE
            if (
                self.source.visible_present
                and self.source.visible
            )
            else (
                AndroidUniverseLinkerVisibilityPolicy.EXPLICIT_HIDDEN
                if self.source.visible_present
                else AndroidUniverseLinkerVisibilityPolicy.DEFAULT_HIDDEN
            )
        )

        if (
            self.visibility_policy
            is not expected_visibility_policy
        ):
            raise ValueError(
                "visibility policy must preserve protobuf "
                "presence/value semantics"
            )

        if (
            self.effective_visible
            is not self.source.visible
        ):
            raise ValueError(
                "effective_visible must match AOSP protobuf "
                "default/value behavior"
            )

        if tuple(
            item.path
            for item in self.permitted_paths
        ) != self.source.permitted_paths:
            raise ValueError(
                "permitted paths must preserve exact Parsing order"
            )

        if tuple(
            item.library_name
            for item in self.provided_libraries
        ) != self.source.provide_libs:
            raise ValueError(
                "provided libraries must preserve exact Parsing order"
            )

        if tuple(
            item.library_name
            for item in self.required_libraries
        ) != self.source.require_libs:
            raise ValueError(
                "required libraries must preserve exact Parsing order"
            )

        if tuple(
            item.contribution
            for item in self.contributions
        ) != self.source.contributions:
            raise ValueError(
                "contributions must preserve exact Parsing order"
            )

        if self.unknown_fields != self.source.unknown_fields:
            raise ValueError(
                "unknown fields must preserve exact Parsing evidence"
            )

    @property
    def applies_apex_local_policy(
        self,
    ) -> bool:
        return (
            self.usage
            is AndroidUniverseLinkerProtobufUsage.APEX_LOCAL
        )

    @property
    def applies_context_library_policy(
        self,
    ) -> bool:
        return self.usage in {
            AndroidUniverseLinkerProtobufUsage.SYSTEM_CONTEXT,
            AndroidUniverseLinkerProtobufUsage.VENDOR_CONTEXT,
            AndroidUniverseLinkerProtobufUsage.PRODUCT_CONTEXT,
        }


from treeforge.android.parsing.linker.model import (
    AndroidNativeLibraryConfigurationDeclaration,
    ParsedAndroidNativeLibraryConfiguration,
)


class AndroidUniverseLinkerNativeLibraryPolicyKind(
    str,
    Enum,
):
    """
    Source-local Android native-library policy role.
    """

    SYSTEM_PUBLIC = "system_public"
    EXTENDED_PUBLIC = "extended_public"
    VENDOR_PUBLIC = "vendor_public"
    LLNDK = "llndk"
    SANITIZER = "sanitizer"

    VNDK_CORE_VARIANT = "vndk_core_variant"
    VNDK_SP = "vndk_sp"
    VNDK_CORE = "vndk_core"
    VNDK_PRIVATE = "vndk_private"

    UNCLASSIFIED = "unclassified"


class AndroidUniverseLinkerNativeLibraryBitness(
    str,
    Enum,
):
    """
    Bitness selector used by public-library declarations.
    """

    ALL = "all"
    ONLY_32 = "32"
    ONLY_64 = "64"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerNativeLibraryDeclaration:
    """
    Semantic interpretation of one native-library configuration line.

    ``source_declaration`` retains the exact Parsing-stage evidence.
    """

    source: ParsedAndroidNativeLibraryConfiguration
    source_declaration: AndroidNativeLibraryConfigurationDeclaration

    library_name: str
    bitness: AndroidUniverseLinkerNativeLibraryBitness
    nopreload: bool

    qualifier_tokens: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidNativeLibraryConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidNativeLibraryConfiguration"
            )

        if not isinstance(
            self.source_declaration,
            AndroidNativeLibraryConfigurationDeclaration,
        ):
            raise TypeError(
                "source_declaration must be an "
                "AndroidNativeLibraryConfigurationDeclaration"
            )

        if not any(
            declaration
            is self.source_declaration
            for declaration
            in self.source.declarations
        ):
            raise ValueError(
                "source_declaration must preserve exact Parsing identity"
            )

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
            self.bitness,
            AndroidUniverseLinkerNativeLibraryBitness,
        ):
            raise TypeError(
                "bitness must be an "
                "AndroidUniverseLinkerNativeLibraryBitness"
            )

        if not isinstance(
            self.nopreload,
            bool,
        ):
            raise TypeError(
                "nopreload must be a bool"
            )

        if not isinstance(
            self.qualifier_tokens,
            tuple,
        ):
            raise TypeError(
                "qualifier_tokens must be a tuple"
            )

        if (
            self.source_declaration.tokens[0]
            != self.library_name
        ):
            raise ValueError(
                "library_name must preserve the first Parsing token"
            )

        if (
            self.source_declaration.tokens[1:]
            != self.qualifier_tokens
        ):
            raise ValueError(
                "qualifier_tokens must preserve exact Parsing tokens"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerNativeLibraryConfigurationSemantics:
    """
    Source-local semantics for one native-library policy file.

    This does not select effective partition populations, join APEX metadata,
    build namespace links, or resolve libraries to ELF artifacts.
    """

    source: ParsedAndroidNativeLibraryConfiguration

    runtime_context: AndroidUniverseRuntimeContext

    policy_kind: AndroidUniverseLinkerNativeLibraryPolicyKind

    declarations: tuple[
        AndroidUniverseLinkerNativeLibraryDeclaration,
        ...,
    ]

    uninterpreted_declarations: tuple[
        AndroidNativeLibraryConfigurationDeclaration,
        ...,
    ]

    @property
    def version_token(
        self,
    ) -> str | None:
        """
        Return the optional version token carried by Android's versioned
        native-library policy filename.

        Examples:
          vndksp.libraries.34.txt -> "34"
          llndk.libraries.34.txt  -> "34"
          sanitizer.libraries.txt -> None

        Parsing preserves the exact path. Universe owns this source-local
        semantic interpretation so downstream Runtime Linking does not reopen
        Parsing path evidence.
        """

        name = (
            self.source
            .source
            .android_path
            .name
        )

        parts = name.split(
            "."
        )

        if (
            len(
                parts
            ) >= 4
            and parts[
                -1
            ] == "txt"
            and parts[
                -2
            ]
        ):
            return parts[
                -2
            ]

        return None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidNativeLibraryConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidNativeLibraryConfiguration"
            )

        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        if not isinstance(
            self.policy_kind,
            AndroidUniverseLinkerNativeLibraryPolicyKind,
        ):
            raise TypeError(
                "policy_kind must be an "
                "AndroidUniverseLinkerNativeLibraryPolicyKind"
            )

        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not isinstance(
            self.uninterpreted_declarations,
            tuple,
        ):
            raise TypeError(
                "uninterpreted_declarations must be a tuple"
            )

        interpreted = tuple(
            declaration.source_declaration
            for declaration
            in self.declarations
        )

        accounted = (
            interpreted
            + self.uninterpreted_declarations
        )

        if len(
            accounted
        ) != len(
            self.source.declarations
        ):
            raise ValueError(
                "every native-library declaration must be accounted for "
                "exactly once"
            )

        if len(
            {
                id(
                    declaration
                )
                for declaration
                in accounted
            }
        ) != len(
            accounted
        ):
            raise ValueError(
                "native-library declaration identities must not be "
                "accounted more than once"
            )

        if {
            id(
                declaration
            )
            for declaration
            in accounted
        } != {
            id(
                declaration
            )
            for declaration
            in self.source.declarations
        }:
            raise ValueError(
                "native-library semantics must preserve exact Parsing "
                "declaration population"
            )

    @property
    def is_public_policy(
        self,
    ) -> bool:
        return self.policy_kind in {
            AndroidUniverseLinkerNativeLibraryPolicyKind.SYSTEM_PUBLIC,
            AndroidUniverseLinkerNativeLibraryPolicyKind.EXTENDED_PUBLIC,
            AndroidUniverseLinkerNativeLibraryPolicyKind.VENDOR_PUBLIC,
        }

@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerRuntimePolicy:
    """
    Unified Linker policy inputs for one canonical Android runtime context.

    This groups already-interpreted Linker-local semantics only. It does not
    resolve cross-source providers, join APEX manifests, or resolve ELF
    dependencies.
    """

    runtime_context: AndroidUniverseRuntimeContext

    text_configurations: tuple[
        AndroidUniverseLinkerTextConfigurationSemantics,
        ...,
    ]

    protobuf_configurations: tuple[
        AndroidUniverseLinkerProtobufConfigurationSemantics,
        ...,
    ]

    native_library_configurations: tuple[
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        for field_name, values, expected_type in (
            (
                "text_configurations",
                self.text_configurations,
                AndroidUniverseLinkerTextConfigurationSemantics,
            ),
            (
                "protobuf_configurations",
                self.protobuf_configurations,
                AndroidUniverseLinkerProtobufConfigurationSemantics,
            ),
            (
                "native_library_configurations",
                self.native_library_configurations,
                AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
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
                for value in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid semantic object"
                )

            for value in values:
                if (
                    value.runtime_context
                    != self.runtime_context
                ):
                    raise ValueError(
                        f"{field_name} contains semantics from a "
                        "different runtime context"
                    )

    @property
    def semantic_configuration_count(
        self,
    ) -> int:
        return (
            len(
                self.text_configurations
            )
            + len(
                self.protobuf_configurations
            )
            + len(
                self.native_library_configurations
            )
        )

