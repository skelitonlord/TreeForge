"""
Runtime-Linker relationship/result semantics.

These objects consume exact canonical Android Device Universe identities but
represent effective runtime behavior owned exclusively by Runtime Linking.
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

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
)

from treeforge.android.universe.boot.semantics import (
    AndroidUniverseFirstStageModuleLoadingPolicy,
)

from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleLoadEntry,
)

from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.action_command import (
    AndroidUniverseInitActionCommandRequirement,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.onrestart import (
    AndroidUniverseInitOnRestartCommand,
)
from treeforge.android.universe.init.resources import (
    AndroidUniverseInitInterfaceSemantics,
)
from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)
from treeforge.android.universe.runtime_property.context import (
    AndroidUniversePropertyContextMatchKind,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextRequirement,
)
from treeforge.android.universe.selinux.symbol import (
    AndroidUniverseSelinuxSymbol,
)
from treeforge.android.universe.vintf.hal import (
    AndroidUniverseVintfHalInterface,
    AndroidUniverseVintfHalRequirement,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathEffectiveEntry,
    AndroidUniverseClasspathInstalledJarResolution,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)

from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContext,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
    AndroidUniverseLinkerNativeLibraryDeclaration,
    AndroidUniverseLinkerNativeLibraryPolicyKind,
    AndroidUniverseLinkerNamespace,
    AndroidUniverseLinkerProtobufConfigurationSemantics,
    AndroidUniverseLinkerProtobufLibraryPolicy,
    AndroidUniverseLinkerRuntimePolicy,
    AndroidUniverseLinkerSection,
    AndroidUniverseLinkerTextConfigurationSemantics,
)



from treeforge.android.runtime_linking.linker.generated_configuration import (
    AndroidUniverseLinkerGeneratedBaseConfiguration,
    AndroidUniverseLinkerGeneratedDirectoryRoute,
    AndroidUniverseLinkerGeneratedSection,
    AndroidUniverseLinkerGeneratedNamespace,
)

from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerApexNamespaceInput,
    AndroidUniverseLinkerApexNamespaceStatus,
    AndroidUniverseLinkerApexPublicLibraryConclusion,
    AndroidUniverseLinkerElfConfigurationScope,
    AndroidUniverseLinkerElfContext,
    AndroidUniverseRelationshipStatus,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexActiveRuntimePath:
    """
    Canonical active runtime mount-path semantics for one APEX requirement.

    Android exposes the active APEX to runtime consumers through the
    unversioned ``/apex/<manifest-name>`` mount. The versioned apexd mount is
    activation machinery and is not the canonical client-visible executable
    root modeled here.

    Activation identity remains runtime-local. Requirements with the same
    manifest name compete only when they belong to the same canonical Android
    runtime context.

    This is runtime semantic reconciliation only. It does not create APEX
    namespaces, generate linker configuration, choose source-tree ownership
    or destinations, or create Reconstruction obligations.
    """

    apex_requirement: AndroidUniverseApexRequirement

    runtime_context: AndroidUniverseRuntimeContext

    activation_candidates: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ]

    active_root: PurePosixPath | None

    executable_directory: PurePosixPath | None

    status: AndroidUniverseRelationshipStatus

    unresolved_reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.apex_requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "apex_requirement must be an "
                "AndroidUniverseApexRequirement"
            )

        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        if self.runtime_context is not (
            self.apex_requirement.runtime_context
        ):
            raise ValueError(
                "runtime_context must preserve exact APEX requirement "
                "runtime-context identity"
            )

        if not isinstance(
            self.activation_candidates,
            tuple,
        ):
            raise TypeError(
                "activation_candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                AndroidUniverseApexRequirement,
            )
            for candidate
            in self.activation_candidates
        ):
            raise TypeError(
                "activation_candidates must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        candidate_ids = tuple(
            candidate.requirement_id
            for candidate
            in self.activation_candidates
        )

        if candidate_ids != tuple(
            sorted(
                candidate_ids
            )
        ):
            raise ValueError(
                "activation_candidates must preserve canonical "
                "requirement-id order"
            )

        if self.activation_candidates:
            if not any(
                candidate is self.apex_requirement
                for candidate
                in self.activation_candidates
            ):
                raise ValueError(
                    "activation_candidates must preserve the exact "
                    "APEX requirement identity"
                )

            if not all(
                candidate.shares_manifest_name(self.apex_requirement)
                for candidate
                in self.activation_candidates
            ):
                raise ValueError(
                    "activation_candidates must share the canonical "
                    "APEX manifest name"
                )

            if not all(
                candidate.shares_runtime(
                    self.runtime_context
                )
                for candidate
                in self.activation_candidates
            ):
                raise ValueError(
                    "activation_candidates must belong to the same "
                    "canonical runtime context"
                )

        if (
            self.active_root is not None
            and not isinstance(
                self.active_root,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "active_root must be a PurePosixPath or None"
            )

        if (
            self.executable_directory is not None
            and not isinstance(
                self.executable_directory,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "executable_directory must be a PurePosixPath or None"
            )

        if self.active_root is not None:
            if not self.active_root.is_absolute():
                raise ValueError(
                    "active_root must be absolute"
                )

        if self.executable_directory is not None:
            if not self.executable_directory.is_absolute():
                raise ValueError(
                    "executable_directory must be absolute"
                )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if (
            self.status
            is AndroidUniverseRelationshipStatus.RESOLVED
        ):
            if len(
                self.activation_candidates
            ) != 1:
                raise ValueError(
                    "resolved active APEX runtime path requires exactly "
                    "one activation candidate"
                )

            if (
                self.activation_candidates[
                    0
                ]
                is not self.apex_requirement
            ):
                raise ValueError(
                    "resolved active APEX runtime path must select the "
                    "exact APEX requirement"
                )

            expected_root = PurePosixPath(
                "/apex"
            ) / self.apex_requirement.apex_name

            if self.active_root != expected_root:
                raise ValueError(
                    "resolved active_root must follow canonical "
                    "/apex/<manifest-name> semantics"
                )

            if (
                self.executable_directory
                != expected_root / "bin"
            ):
                raise ValueError(
                    "resolved executable_directory must be the canonical "
                    "active APEX bin directory"
                )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "resolved active APEX runtime path must not carry "
                    "unresolved_reason"
                )

        elif (
            self.status
            is AndroidUniverseRelationshipStatus.AMBIGUOUS
        ):
            if len(
                self.activation_candidates
            ) <= 1:
                raise ValueError(
                    "ambiguous active APEX runtime path requires multiple "
                    "same-runtime activation candidates"
                )

            if (
                self.active_root is not None
                or self.executable_directory is not None
            ):
                raise ValueError(
                    "ambiguous active APEX runtime path must not select "
                    "runtime paths"
                )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "ambiguous active APEX runtime path must not carry "
                    "unresolved_reason"
                )

        else:
            if (
                self.active_root is not None
                or self.executable_directory is not None
            ):
                raise ValueError(
                    "unresolved active APEX runtime path must not select "
                    "runtime paths"
                )

            if self.unresolved_reason is None:
                raise ValueError(
                    "unresolved active APEX runtime path requires a reason"
                )

    @property
    def runtime_path_id(
        self,
    ) -> str:
        return (
            "linker-apex-active-runtime-path:"
            f"{self.apex_requirement.requirement_id}"
        )


class AndroidUniverseLinkerExecutableSectionRoutingStatus(
    StrEnum
):
    """
    Canonical executable-to-Linker-section routing state.

    RESOLVED means Android's ordered directory routing selects one exact
    generated BASE section.

    DEFAULT_FALLBACK means the ELF is a canonical runtime executable but no
    generated directory mapping matches its Android path, so bionic falls
    back to its default no-config namespace semantics.

    INAPPLICABLE is used for ELFs that do not participate in Android
    executable-directory routing.

    AMBIGUOUS preserves ambiguous canonical Linker/ELF runtime context.

    UNRESOLVED preserves insufficient runtime-path or ordered-route evidence
    without guessing.
    """

    RESOLVED = "resolved"
    DEFAULT_FALLBACK = "default_fallback"
    INAPPLICABLE = "inapplicable"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerExecutableSectionRouting:
    """
    Route one canonical ELF through Android linkerconfig executable-directory
    semantics.

    BASE executable routing consumes the exact Parsing-stage Android-visible
    path and the exact ordered generated directory routes.

    APEX executable routing consumes one exact canonical active APEX
    runtime-path conclusion. It does not independently synthesize
    ``/apex/<name>`` paths.

    BASE selected_section remains a generated BASE-section identity.
    APEX routing instead preserves its exact active-runtime-path conclusion
    plus the canonical APEX section name.

    Shared objects and other non-launchable ELFs are inapplicable.

    This is runtime semantic reconciliation only. It does not construct
    namespaces, links, expanded sections, source destinations, or
    Reconstruction outputs.
    """

    elf_context: AndroidUniverseLinkerElfContext

    base_configuration: (
        AndroidUniverseLinkerGeneratedBaseConfiguration
        | None
    )

    android_path: PurePosixPath | None

    route_candidates: tuple[
        AndroidUniverseLinkerGeneratedDirectoryRoute,
        ...,
    ]

    selected_route: (
        AndroidUniverseLinkerGeneratedDirectoryRoute
        | None
    )

    selected_section: (
        AndroidUniverseLinkerGeneratedSection
        | None
    )

    status: AndroidUniverseLinkerExecutableSectionRoutingStatus

    apex_runtime_path: (
        AndroidUniverseLinkerApexActiveRuntimePath
        | None
    ) = None

    apex_section_name: str | None = None

    unresolved_reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.elf_context,
            AndroidUniverseLinkerElfContext,
        ):
            raise TypeError(
                "elf_context must be an AndroidUniverseLinkerElfContext"
            )

        if (
            self.base_configuration is not None
            and not isinstance(
                self.base_configuration,
                AndroidUniverseLinkerGeneratedBaseConfiguration,
            )
        ):
            raise TypeError(
                "base_configuration must be an "
                "AndroidUniverseLinkerGeneratedBaseConfiguration or None"
            )

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if (
            self.android_path is not None
            and not self.android_path.is_absolute()
        ):
            raise ValueError(
                "android_path must be absolute"
            )

        if not isinstance(
            self.route_candidates,
            tuple,
        ):
            raise TypeError(
                "route_candidates must be a tuple"
            )

        if not all(
            isinstance(
                route,
                AndroidUniverseLinkerGeneratedDirectoryRoute,
            )
            for route
            in self.route_candidates
        ):
            raise TypeError(
                "route_candidates must contain only "
                "AndroidUniverseLinkerGeneratedDirectoryRoute instances"
            )

        candidate_indexes = tuple(
            route.index
            for route
            in self.route_candidates
        )

        if candidate_indexes != tuple(
            sorted(
                candidate_indexes
            )
        ):
            raise ValueError(
                "route_candidates must preserve canonical first-match order"
            )

        if (
            self.selected_route is not None
            and not isinstance(
                self.selected_route,
                AndroidUniverseLinkerGeneratedDirectoryRoute,
            )
        ):
            raise TypeError(
                "selected_route must be an "
                "AndroidUniverseLinkerGeneratedDirectoryRoute or None"
            )

        if (
            self.selected_section is not None
            and not isinstance(
                self.selected_section,
                AndroidUniverseLinkerGeneratedSection,
            )
        ):
            raise TypeError(
                "selected_section must be an "
                "AndroidUniverseLinkerGeneratedSection or None"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerExecutableSectionRoutingStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerExecutableSectionRoutingStatus"
            )


        if (
            self.apex_runtime_path is not None
            and not isinstance(
                self.apex_runtime_path,
                AndroidUniverseLinkerApexActiveRuntimePath,
            )
        ):
            raise TypeError(
                "apex_runtime_path must be an "
                "AndroidUniverseLinkerApexActiveRuntimePath or None"
            )

        if (
            self.apex_section_name is not None
            and not isinstance(
                self.apex_section_name,
                str,
            )
        ):
            raise TypeError(
                "apex_section_name must be a string or None"
            )

        if (
            self.apex_section_name is not None
            and not self.apex_section_name
        ):
            raise ValueError(
                "apex_section_name must not be empty"
            )

        if self.apex_runtime_path is not None:
            if (
                self.elf_context.configuration_scope
                is not AndroidUniverseLinkerElfConfigurationScope.APEX
            ):
                raise ValueError(
                    "only APEX routing may carry apex_runtime_path"
                )

            selected_apex = (
                self.elf_context.selected_apex_requirement
            )

            if selected_apex is None:
                raise ValueError(
                    "APEX routing with apex_runtime_path requires an exact "
                    "selected APEX requirement"
                )

            if (
                self.apex_runtime_path.apex_requirement
                is not selected_apex
            ):
                raise ValueError(
                    "apex_runtime_path must preserve exact selected APEX "
                    "requirement identity"
                )

        if (
            self.apex_section_name is not None
            and self.apex_runtime_path is None
        ):
            raise ValueError(
                "apex_section_name requires apex_runtime_path"
            )

        if (
            self.unresolved_reason is not None
            and (
                not isinstance(
                    self.unresolved_reason,
                    str,
                )
                or not self.unresolved_reason.strip()
            )
        ):
            raise ValueError(
                "unresolved_reason must be a non-empty string or None"
            )

        if self.base_configuration is not None:
            if not all(
                any(
                    route is canonical
                    for canonical
                    in self.base_configuration.directory_routes
                )
                for route
                in self.route_candidates
            ):
                raise ValueError(
                    "route_candidates must preserve exact generated "
                    "directory-route identity"
                )

            if (
                self.selected_route is not None
                and not any(
                    self.selected_route is canonical
                    for canonical
                    in self.base_configuration.directory_routes
                )
            ):
                raise ValueError(
                    "selected_route must preserve exact generated "
                    "directory-route identity"
                )

            if (
                self.selected_section is not None
                and not any(
                    self.selected_section is canonical
                    for canonical
                    in self.base_configuration.sections
                )
            ):
                raise ValueError(
                    "selected_section must preserve exact generated "
                    "section identity"
                )

        if (
            self.status
            is AndroidUniverseLinkerExecutableSectionRoutingStatus.RESOLVED
            and self.elf_context.configuration_scope
            is AndroidUniverseLinkerElfConfigurationScope.BASE
        ):
            if (
                self.base_configuration is None
                or self.android_path is None
                or self.selected_route is None
                or self.selected_section is None
            ):
                raise ValueError(
                    "resolved BASE executable routing requires exact "
                    "configuration, Android path, route, and section"
                )

            if self.selected_route not in self.route_candidates:
                raise ValueError(
                    "selected_route must be present in route_candidates"
                )

            if (
                self.selected_route.section_name
                != self.selected_section.name
            ):
                raise ValueError(
                    "selected route and section identities must agree"
                )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "resolved BASE routing must not carry unresolved_reason"
                )

        if (
            self.status
            is not AndroidUniverseLinkerExecutableSectionRoutingStatus.RESOLVED
        ):
            if (
                self.selected_route is not None
                or self.selected_section is not None
            ):
                raise ValueError(
                    "non-resolved routing must not select route or section"
                )

        if (
            self.status
            is (
                AndroidUniverseLinkerExecutableSectionRoutingStatus
                .DEFAULT_FALLBACK
            )
        ):
            if (
                self.base_configuration is None
                or self.android_path is None
            ):
                raise ValueError(
                    "default-fallback routing requires exact BASE "
                    "configuration and Android path"
                )

            if self.route_candidates:
                raise ValueError(
                    "default-fallback routing must not carry route candidates"
                )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "default-fallback routing must not carry "
                    "unresolved_reason"
                )

        if (
            self.status
            is AndroidUniverseLinkerExecutableSectionRoutingStatus.INAPPLICABLE
        ):
            if self.unresolved_reason is not None:
                raise ValueError(
                    "inapplicable routing must not carry unresolved_reason"
                )

        if (
            self.status
            is AndroidUniverseLinkerExecutableSectionRoutingStatus.UNRESOLVED
            and self.unresolved_reason is None
        ):
            raise ValueError(
                "unresolved routing requires unresolved_reason"
            )

        if (
            self.status
            is AndroidUniverseLinkerExecutableSectionRoutingStatus.RESOLVED
            and self.elf_context.configuration_scope
            is AndroidUniverseLinkerElfConfigurationScope.APEX
        ):
            if self.base_configuration is not None:
                raise ValueError(
                    "resolved APEX routing must not select a BASE "
                    "configuration"
                )

            if self.route_candidates:
                raise ValueError(
                    "resolved APEX routing must not carry BASE route "
                    "candidates"
                )

            if self.selected_route is not None:
                raise ValueError(
                    "resolved APEX routing must not select a BASE route"
                )

            if self.selected_section is not None:
                raise ValueError(
                    "resolved APEX routing must not select a generated "
                    "BASE section"
                )

            if self.apex_runtime_path is None:
                raise ValueError(
                    "resolved APEX routing requires canonical active "
                    "APEX runtime-path semantics"
                )

            if (
                self.apex_runtime_path.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
            ):
                raise ValueError(
                    "resolved APEX routing requires a resolved active "
                    "APEX runtime path"
                )

            expected_section_name = (
                AndroidRuntimeLinkerApexIdentity.section_name(self.apex_runtime_path.apex_requirement)
            )

            if self.apex_section_name != expected_section_name:
                raise ValueError(
                    "resolved APEX routing section name must equal the "
                    "canonical APEX manifest name"
                )

            if self.android_path is None:
                raise ValueError(
                    "resolved APEX routing requires canonical runtime "
                    "executable path"
                )

            executable_directory = (
                self.apex_runtime_path
                .executable_directory
            )

            if executable_directory is None:
                raise ValueError(
                    "resolved APEX routing requires canonical executable "
                    "directory"
                )

            if executable_directory not in self.android_path.parents:
                raise ValueError(
                    "resolved APEX executable path must belong to the "
                    "canonical active APEX executable directory"
                )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "resolved APEX routing must not carry "
                    "unresolved_reason"
                )

        if (
            self.elf_context.configuration_scope
            is AndroidUniverseLinkerElfConfigurationScope.BASE
            and (
                self.apex_runtime_path is not None
                or self.apex_section_name is not None
            )
        ):
            raise ValueError(
                "BASE executable routing must not carry APEX routing "
                "targets"
            )

    @property
    def routing_id(
        self,
    ) -> str:
        return (
            "linker-executable-routing:"
            f"{self.elf_context.context_id}"
        )


class AndroidUniverseLinkerExecutableLoadingContextStatus(
    StrEnum
):
    """
    Canonical starting Linker namespace state for one ELF routing conclusion.

    RESOLVED means one exact starting namespace identity is established.

    DEFAULT_FALLBACK preserves bionic's no-config default namespace behavior
    when executable section routing itself selected DEFAULT_FALLBACK.

    INAPPLICABLE preserves ELFs that are not load-entry executables.

    AMBIGUOUS and UNRESOLVED preserve upstream ambiguity or insufficient
    canonical namespace evidence without guessing.
    """

    RESOLVED = "resolved"
    DEFAULT_FALLBACK = "default_fallback"
    INAPPLICABLE = "inapplicable"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerExecutableLoadingContext:
    """
    Canonical starting Linker loading context for one exact ELF routing result.

    BASE routing preserves the exact generated ``default`` namespace object
    from the already-selected generated section.

    APEX routing preserves the exact APEX namespace-input conclusion and the
    semantic ``default`` namespace identity. It does not construct the final
    APEX namespace, inject namespaces into BASE sections, or create links.

    DEFAULT_FALLBACK represents bionic's default no-config namespace without
    pretending that it belongs to a generated BASE section.

    Shared objects remain INAPPLICABLE here. They may later be reachable from
    many loading contexts and are never permanently assigned to one namespace.

    This is Universe runtime semantic reconciliation only. It does not resolve
    DT_NEEDED providers or create Reconstruction obligations.
    """

    routing: AndroidUniverseLinkerExecutableSectionRouting

    base_namespace: (
        AndroidUniverseLinkerGeneratedNamespace
        | None
    )

    apex_namespace_input: (
        AndroidUniverseLinkerApexNamespaceInput
        | None
    )

    namespace_name: str | None

    status: (
        AndroidUniverseLinkerExecutableLoadingContextStatus
    )

    unresolved_reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.routing,
            AndroidUniverseLinkerExecutableSectionRouting,
        ):
            raise TypeError(
                "routing must be an "
                "AndroidUniverseLinkerExecutableSectionRouting"
            )

        if (
            self.base_namespace is not None
            and not isinstance(
                self.base_namespace,
                AndroidUniverseLinkerGeneratedNamespace,
            )
        ):
            raise TypeError(
                "base_namespace must be an "
                "AndroidUniverseLinkerGeneratedNamespace or None"
            )

        if (
            self.apex_namespace_input is not None
            and not isinstance(
                self.apex_namespace_input,
                AndroidUniverseLinkerApexNamespaceInput,
            )
        ):
            raise TypeError(
                "apex_namespace_input must be an "
                "AndroidUniverseLinkerApexNamespaceInput or None"
            )

        if (
            self.namespace_name is not None
            and (
                not isinstance(
                    self.namespace_name,
                    str,
                )
                or not self.namespace_name
            )
        ):
            raise ValueError(
                "namespace_name must be a non-empty string or None"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerExecutableLoadingContextStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerExecutableLoadingContextStatus"
            )

        if (
            self.unresolved_reason is not None
            and (
                not isinstance(
                    self.unresolved_reason,
                    str,
                )
                or not self.unresolved_reason.strip()
            )
        ):
            raise ValueError(
                "unresolved_reason must be a non-empty string or None"
            )

        scope = (
            self.routing
            .elf_context
            .configuration_scope
        )

        if (
            self.base_namespace is not None
            and scope
            is not AndroidUniverseLinkerElfConfigurationScope.BASE
        ):
            raise ValueError(
                "only BASE loading contexts may preserve "
                "base_namespace"
            )

        if (
            self.apex_namespace_input is not None
            and scope
            is not AndroidUniverseLinkerElfConfigurationScope.APEX
        ):
            raise ValueError(
                "only APEX loading contexts may preserve "
                "apex_namespace_input"
            )

        if (
            self.apex_namespace_input is not None
        ):
            selected_apex = (
                self.routing
                .elf_context
                .selected_apex_requirement
            )

            if selected_apex is None:
                raise ValueError(
                    "APEX namespace input requires one exact selected "
                    "APEX requirement"
                )

            if (
                self.apex_namespace_input.apex_requirement
                is not selected_apex
            ):
                raise ValueError(
                    "apex_namespace_input must preserve exact selected "
                    "APEX requirement identity"
                )

        if (
            self.status
            is AndroidUniverseLinkerExecutableLoadingContextStatus.RESOLVED
        ):
            if (
                self.routing.status
                is not (
                    AndroidUniverseLinkerExecutableSectionRoutingStatus
                    .RESOLVED
                )
            ):
                raise ValueError(
                    "resolved loading context requires resolved "
                    "executable routing"
                )

            if self.namespace_name != "default":
                raise ValueError(
                    "resolved executable loading context must select "
                    "the canonical default namespace"
                )

            if (
                scope
                is AndroidUniverseLinkerElfConfigurationScope.BASE
            ):
                if self.base_namespace is None:
                    raise ValueError(
                        "resolved BASE loading context requires exact "
                        "generated default namespace"
                    )

                if self.apex_namespace_input is not None:
                    raise ValueError(
                        "resolved BASE loading context must not carry "
                        "APEX namespace input"
                    )

                selected_section = (
                    self.routing.selected_section
                )

                if selected_section is None:
                    raise ValueError(
                        "resolved BASE loading context requires exact "
                        "selected section"
                    )

                if not any(
                    namespace
                    is self.base_namespace
                    for namespace
                    in selected_section.namespaces
                ):
                    raise ValueError(
                        "base_namespace must preserve exact namespace "
                        "identity from selected section"
                    )

                if self.base_namespace.name != "default":
                    raise ValueError(
                        "resolved BASE loading context must select "
                        "namespace named default"
                    )

            else:
                if self.base_namespace is not None:
                    raise ValueError(
                        "resolved APEX loading context must not carry "
                        "generated BASE namespace"
                    )

                if self.apex_namespace_input is None:
                    raise ValueError(
                        "resolved APEX loading context requires exact "
                        "APEX namespace input"
                    )

                if self.apex_namespace_input.status not in {
                    AndroidUniverseLinkerApexNamespaceStatus.PRESENT,
                    AndroidUniverseLinkerApexNamespaceStatus.ABSENT,
                }:
                    raise ValueError(
                        "resolved APEX loading context requires PRESENT "
                        "or ABSENT canonical local-policy state"
                    )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "resolved loading context must not carry "
                    "unresolved_reason"
                )

        elif (
            self.status
            is (
                AndroidUniverseLinkerExecutableLoadingContextStatus
                .DEFAULT_FALLBACK
            )
        ):
            if (
                self.routing.status
                is not (
                    AndroidUniverseLinkerExecutableSectionRoutingStatus
                    .DEFAULT_FALLBACK
                )
            ):
                raise ValueError(
                    "default-fallback loading context requires "
                    "default-fallback executable routing"
                )

            if (
                self.base_namespace is not None
                or self.apex_namespace_input is not None
            ):
                raise ValueError(
                    "default-fallback loading context must not claim "
                    "generated namespace identity"
                )

            if self.namespace_name != "default":
                raise ValueError(
                    "default-fallback loading context must preserve "
                    "default namespace semantics"
                )

            if self.unresolved_reason is not None:
                raise ValueError(
                    "default-fallback loading context must not carry "
                    "unresolved_reason"
                )

        elif (
            self.status
            is (
                AndroidUniverseLinkerExecutableLoadingContextStatus
                .INAPPLICABLE
            )
        ):
            if (
                self.routing.status
                is not (
                    AndroidUniverseLinkerExecutableSectionRoutingStatus
                    .INAPPLICABLE
                )
            ):
                raise ValueError(
                    "inapplicable loading context requires "
                    "inapplicable executable routing"
                )

            if (
                self.base_namespace is not None
                or self.apex_namespace_input is not None
                or self.namespace_name is not None
                or self.unresolved_reason is not None
            ):
                raise ValueError(
                    "inapplicable loading context must not select "
                    "namespace semantics"
                )

        elif (
            self.status
            is (
                AndroidUniverseLinkerExecutableLoadingContextStatus
                .AMBIGUOUS
            )
        ):
            if (
                self.base_namespace is not None
                or self.namespace_name is not None
                or self.unresolved_reason is not None
            ):
                raise ValueError(
                    "ambiguous loading context must not select a "
                    "concrete namespace"
                )

            if (
                self.apex_namespace_input is not None
                and self.apex_namespace_input.status
                is not AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
            ):
                raise ValueError(
                    "preserved ambiguous APEX namespace input must "
                    "itself be ambiguous"
                )

        else:
            if (
                self.base_namespace is not None
                or self.namespace_name is not None
            ):
                raise ValueError(
                    "unresolved loading context must not select "
                    "a concrete namespace"
                )

            if self.unresolved_reason is None:
                raise ValueError(
                    "unresolved loading context requires a reason"
                )

            if (
                self.apex_namespace_input is not None
                and self.apex_namespace_input.status
                is not AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
            ):
                raise ValueError(
                    "preserved unresolved APEX namespace input must "
                    "itself be unresolved"
                )

    @property
    def loading_context_id(
        self,
    ) -> str:
        return (
            "linker-executable-loading-context:"
            f"{self.routing.elf_context.context_id}"
        )


class AndroidUniverseLinkerSectionApexApplicabilityStatus(
    StrEnum
):
    """
    Canonical semantic applicability of one APEX to one generated Linker
    section.

    ACTIVE means Android linkerconfig semantics prove that the APEX belongs
    to the section's visible APEX namespace population.

    INAPPLICABLE means the relevant Android rule is fully known and does not
    select the APEX.

    AMBIGUOUS and UNRESOLVED preserve uncertainty rather than guessing.
    """

    ACTIVE = "active"
    INAPPLICABLE = "inapplicable"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class AndroidUniverseLinkerSectionApexApplicabilityReason(
    StrEnum
):
    """
    Positive semantic reason why an APEX is visible in a Linker section.

    These correspond to Android linkerconfig semantic inputs, not
    Reconstruction instructions.
    """

    APEX_LOCAL_VISIBLE = "apex_local_visible"
    JNI_LIBRARIES = "jni_libraries"
    PUBLIC_LIBRARIES = "public_libraries"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerSectionApexApplicability:
    """
    Determine whether one canonical APEX participates visibly in one
    canonical generated Linker section.

    This models the semantic predicate consumed by Android BuildSection().
    It deliberately does not create an APEX namespace, synthesize /apex
    paths, construct links, resolve provides/requires, order expanded
    namespaces, or produce Reconstruction work.

    ``postinstall`` is special: Android constructs that Section directly and
    does not call BuildSection(), therefore APEX visibility injection does not
    apply to it.
    """

    base_configuration: AndroidUniverseLinkerGeneratedBaseConfiguration
    section: AndroidUniverseLinkerGeneratedSection

    apex_requirement: AndroidUniverseApexRequirement

    namespace_input: AndroidUniverseLinkerApexNamespaceInput

    public_library_conclusion: (
        AndroidUniverseLinkerApexPublicLibraryConclusion
    )

    reasons: tuple[
        AndroidUniverseLinkerSectionApexApplicabilityReason,
        ...,
    ]

    status: AndroidUniverseLinkerSectionApexApplicabilityStatus

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.base_configuration,
            AndroidUniverseLinkerGeneratedBaseConfiguration,
        ):
            raise TypeError(
                "base_configuration must be an "
                "AndroidUniverseLinkerGeneratedBaseConfiguration"
            )

        if not isinstance(
            self.section,
            AndroidUniverseLinkerGeneratedSection,
        ):
            raise TypeError(
                "section must be an "
                "AndroidUniverseLinkerGeneratedSection"
            )

        if not any(
            candidate is self.section
            for candidate
            in self.base_configuration.sections
        ):
            raise ValueError(
                "section must preserve exact generated BASE section identity"
            )

        if not isinstance(
            self.apex_requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "apex_requirement must be an AndroidUniverseApexRequirement"
            )

        if not (
            self.apex_requirement
            .shares_runtime(
                self.base_configuration
                .inputs
                .runtime_policy
                .runtime_context
            )
        ):
            raise ValueError(
                "section/APEX applicability must remain inside one exact "
                "canonical runtime"
            )

        if not isinstance(
            self.namespace_input,
            AndroidUniverseLinkerApexNamespaceInput,
        ):
            raise TypeError(
                "namespace_input must be an "
                "AndroidUniverseLinkerApexNamespaceInput"
            )

        if (
            self.namespace_input.apex_requirement
            is not self.apex_requirement
        ):
            raise ValueError(
                "namespace_input must preserve exact APEX identity"
            )

        if not isinstance(
            self.public_library_conclusion,
            AndroidUniverseLinkerApexPublicLibraryConclusion,
        ):
            raise TypeError(
                "public_library_conclusion must be an "
                "AndroidUniverseLinkerApexPublicLibraryConclusion"
            )

        if (
            self.public_library_conclusion.apex_requirement
            is not self.apex_requirement
        ):
            raise ValueError(
                "public_library_conclusion must preserve exact APEX identity"
            )

        if not isinstance(
            self.reasons,
            tuple,
        ):
            raise TypeError(
                "reasons must be a tuple"
            )

        if not all(
            isinstance(
                reason,
                AndroidUniverseLinkerSectionApexApplicabilityReason,
            )
            for reason
            in self.reasons
        ):
            raise TypeError(
                "reasons must contain only "
                "AndroidUniverseLinkerSectionApexApplicabilityReason values"
            )

        if len(
            self.reasons
        ) != len(
            set(
                self.reasons
            )
        ):
            raise ValueError(
                "section/APEX applicability reasons must be unique"
            )

        canonical_reason_order = (
            AndroidUniverseLinkerSectionApexApplicabilityReason
            .APEX_LOCAL_VISIBLE,
            AndroidUniverseLinkerSectionApexApplicabilityReason
            .JNI_LIBRARIES,
            AndroidUniverseLinkerSectionApexApplicabilityReason
            .PUBLIC_LIBRARIES,
        )

        expected_reasons = tuple(
            reason
            for reason
            in canonical_reason_order
            if reason
            in self.reasons
        )

        if self.reasons != expected_reasons:
            raise ValueError(
                "section/APEX applicability reasons must preserve "
                "canonical semantic order"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerSectionApexApplicabilityStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerSectionApexApplicabilityStatus"
            )

        if (
            AndroidRuntimeLinkerSectionSemantics.is_postinstall(self.section.name)
            and self.status
            is not (
                AndroidUniverseLinkerSectionApexApplicabilityStatus
                .INAPPLICABLE
            )
        ):
            raise ValueError(
                "postinstall bypasses BuildSection and cannot receive "
                "APEX visibility injection"
            )

        if (
            self.status
            is AndroidUniverseLinkerSectionApexApplicabilityStatus.ACTIVE
        ):
            if not self.reasons:
                raise ValueError(
                    "ACTIVE section/APEX applicability requires at least "
                    "one positive semantic reason"
                )

        elif self.reasons:
            raise ValueError(
                "only ACTIVE section/APEX applicability may carry "
                "positive reasons"
            )

        if (
            AndroidUniverseLinkerSectionApexApplicabilityReason
            .APEX_LOCAL_VISIBLE
            in self.reasons
        ):
            selected = (
                self.namespace_input
                .selected_apex_local_configuration
            )

            if (
                selected is None
                or not selected.effective_visible
            ):
                raise ValueError(
                    "APEX_LOCAL_VISIBLE requires an exact selected "
                    "APEX-local policy with effective_visible=True"
                )

        if (
            AndroidUniverseLinkerSectionApexApplicabilityReason
            .JNI_LIBRARIES
            in self.reasons
        ):
            if (
                not (
                    AndroidRuntimeLinkerSectionSemantics
                    .allows_jni_apex_visibility(
                        self.section.name
                    )
                )
                or not self.apex_requirement.jni_libs
            ):
                raise ValueError(
                    "JNI_LIBRARIES is valid only for system, isolated, "
                    "or unrestricted sections with canonical JNI libs"
                )

        if (
            AndroidUniverseLinkerSectionApexApplicabilityReason
            .PUBLIC_LIBRARIES
            in self.reasons
        ):
            if (
                not (
                    AndroidRuntimeLinkerSectionSemantics
                    .allows_public_library_apex_visibility(
                        self.section.name
                    )
                )
                or not self.public_library_conclusion.public_libraries
            ):
                raise ValueError(
                    "PUBLIC_LIBRARIES requires canonical public libraries "
                    "and a BuildSection-backed section"
                )

    @property
    def conclusion_id(
        self,
    ) -> str:
        return (
            "linker-section-apex:"
            f"{self.section.name}:"
            f"{self.apex_requirement.requirement_id}"
        )


class AndroidUniverseLinkerApexProviderStatus(
    StrEnum
):
    """
    Canonical eligibility/resolution state for one APEX in Android
    linkerconfig's active APEX provider population.

    ACTIVE means enough canonical evidence exists to reproduce the ApexInfo
    fields consumed by BuildApexNamespace()/InitializeWithApex().

    EXCLUDED_SHARED_APEX corresponds to apex-info-list.xml
    provideSharedApexLibs=true. Android linkerconfig explicitly excludes such
    APEXes from the active provider population.

    AMBIGUOUS preserves multiple canonical activation or APEX-local policy
    candidates.

    UNRESOLVED preserves genuinely indeterminate activation or namespace
    input semantics.
    """

    ACTIVE = "active"
    EXCLUDED_SHARED_APEX = "excluded_shared_apex"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexProviderDescriptor:
    """
    Canonical ApexInfo-equivalent provider semantics required by later
    BuildSection()/Section::Resolve() reconciliation.

    This joins only already-established Universe semantics:

    - exact AndroidUniverseApexRequirement identity,
    - exact APEX-local linker.config.pb namespace input,
    - exact active runtime-path conclusion.

    It does not create a namespace, resolve native-library consumers, choose
    Reconstruction ownership/destinations, or materialize files.
    """

    apex_requirement: AndroidUniverseApexRequirement

    namespace_input: AndroidUniverseLinkerApexNamespaceInput

    active_runtime_path: AndroidUniverseLinkerApexActiveRuntimePath

    namespace_name: str | None

    active_root: PurePosixPath | None

    in_vendor: bool | None

    permitted_paths: tuple[
        str,
        ...,
    ]

    provided_libraries: tuple[
        str,
        ...,
    ]

    required_libraries: tuple[
        str,
        ...,
    ]

    has_shared_lib: bool | None

    status: AndroidUniverseLinkerApexProviderStatus

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.apex_requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "apex_requirement must be an "
                "AndroidUniverseApexRequirement"
            )

        if not isinstance(
            self.namespace_input,
            AndroidUniverseLinkerApexNamespaceInput,
        ):
            raise TypeError(
                "namespace_input must be an "
                "AndroidUniverseLinkerApexNamespaceInput"
            )

        if (
            self.namespace_input.apex_requirement
            is not self.apex_requirement
        ):
            raise ValueError(
                "namespace_input must preserve exact APEX identity"
            )

        if not isinstance(
            self.active_runtime_path,
            AndroidUniverseLinkerApexActiveRuntimePath,
        ):
            raise TypeError(
                "active_runtime_path must be an "
                "AndroidUniverseLinkerApexActiveRuntimePath"
            )

        if (
            self.active_runtime_path.apex_requirement
            is not self.apex_requirement
        ):
            raise ValueError(
                "active_runtime_path must preserve exact APEX identity"
            )

        if (
            self.namespace_name is not None
            and (
                not isinstance(
                    self.namespace_name,
                    str,
                )
                or not self.namespace_name
            )
        ):
            raise ValueError(
                "namespace_name must be a non-empty string or None"
            )

        if (
            self.active_root is not None
            and (
                not isinstance(
                    self.active_root,
                    PurePosixPath,
                )
                or not self.active_root.is_absolute()
            )
        ):
            raise ValueError(
                "active_root must be an absolute PurePosixPath or None"
            )

        if (
            self.in_vendor is not None
            and not isinstance(
                self.in_vendor,
                bool,
            )
        ):
            raise TypeError(
                "in_vendor must be a bool or None"
            )

        for field_name, values in (
            (
                "permitted_paths",
                self.permitted_paths,
            ),
            (
                "provided_libraries",
                self.provided_libraries,
            ),
            (
                "required_libraries",
                self.required_libraries,
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

        if (
            self.has_shared_lib is not None
            and not isinstance(
                self.has_shared_lib,
                bool,
            )
        ):
            raise TypeError(
                "has_shared_lib must be a bool or None"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerApexProviderStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerApexProviderStatus"
            )

        populated = (
            self.namespace_name is not None
            or self.active_root is not None
            or self.in_vendor is not None
            or bool(
                self.permitted_paths
            )
            or bool(
                self.provided_libraries
            )
            or bool(
                self.required_libraries
            )
            or self.has_shared_lib is not None
        )

        if (
            self.status
            is AndroidUniverseLinkerApexProviderStatus
            .EXCLUDED_SHARED_APEX
        ):
            if not self.apex_requirement.provide_shared_apex_libs:
                raise ValueError(
                    "EXCLUDED_SHARED_APEX requires canonical "
                    "provideSharedApexLibs=true"
                )

            if populated:
                raise ValueError(
                    "excluded shared APEX provider descriptors must not "
                    "claim effective provider fields"
                )

            return

        if (
            self.status
            is AndroidUniverseLinkerApexProviderStatus.ACTIVE
        ):
            if self.apex_requirement.provide_shared_apex_libs:
                raise ValueError(
                    "ACTIVE provider cannot be a provideSharedApexLibs APEX"
                )

            if (
                self.namespace_input.status
                not in {
                    AndroidUniverseLinkerApexNamespaceStatus.PRESENT,
                    AndroidUniverseLinkerApexNamespaceStatus.ABSENT,
                }
            ):
                raise ValueError(
                    "ACTIVE provider requires PRESENT or ABSENT "
                    "APEX-local namespace input"
                )

            if (
                self.active_runtime_path.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
            ):
                raise ValueError(
                    "ACTIVE provider requires resolved active runtime path"
                )

            expected_namespace_name = (
                AndroidRuntimeLinkerApexIdentity.namespace_name(self.apex_requirement)
            )

            if (
                self.namespace_name
                != expected_namespace_name
            ):
                raise ValueError(
                    "namespace_name must preserve Android ApexInfo "
                    "dot-to-underscore namespace identity"
                )

            if (
                self.active_root
                != self.active_runtime_path.active_root
            ):
                raise ValueError(
                    "active_root must preserve exact active runtime-path "
                    "conclusion"
                )

            expected_in_vendor = (
                AndroidRuntimeLinkerApexDeploymentSemantics
                .is_vendor_partition(
                    self.apex_requirement
                )
            )

            if self.in_vendor is not expected_in_vendor:
                raise ValueError(
                    "in_vendor must match canonical deployment semantics"
                )

            selected = (
                self.namespace_input
                .selected_apex_local_configuration
            )

            expected_permitted_paths = (
                ()
                if selected is None
                else tuple(
                    item.path
                    for item
                    in selected.permitted_paths
                )
            )

            if (
                self.permitted_paths
                != expected_permitted_paths
            ):
                raise ValueError(
                    "permitted_paths must preserve selected APEX-local "
                    "linker.config.pb order"
                )

            if (
                self.provided_libraries
                != self.apex_requirement.provide_native_libs
            ):
                raise ValueError(
                    "provided_libraries must preserve provideNativeLibs"
                )

            if (
                self.required_libraries
                != self.apex_requirement.require_native_libs
            ):
                raise ValueError(
                    "required_libraries must preserve requireNativeLibs"
                )

            if (
                self.has_shared_lib
                is not bool(
                    self.apex_requirement.require_shared_apex_libs
                )
            ):
                raise ValueError(
                    "has_shared_lib must match non-empty "
                    "requireSharedApexLibs semantics"
                )

            return

        if populated:
            raise ValueError(
                "non-active provider descriptors must not claim "
                "effective provider fields"
            )

        if (
            self.status
            is AndroidUniverseLinkerApexProviderStatus.AMBIGUOUS
        ):
            if (
                self.namespace_input.status
                is not AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
                and self.active_runtime_path.status
                is not AndroidUniverseRelationshipStatus.AMBIGUOUS
            ):
                raise ValueError(
                    "AMBIGUOUS provider requires ambiguous namespace "
                    "or activation evidence"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexProviderStatus.UNRESOLVED
        ):
            if (
                self.namespace_input.status
                is not AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
                and self.active_runtime_path.status
                is not AndroidUniverseRelationshipStatus.UNRESOLVED
            ):
                raise ValueError(
                    "UNRESOLVED provider requires unresolved namespace "
                    "or activation evidence"
                )

    @property
    def descriptor_id(
        self,
    ) -> str:
        return (
            "linker-apex-provider:"
            f"{self.apex_requirement.requirement_id}"
        )
