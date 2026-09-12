from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.universe.art_runtime.semantics import (
    AndroidUniverseArtRuntimeVdexDisposition,
    AndroidUniverseArtRuntimeVdexDispositionStatus,
)

from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.parsing.dex.model import (
    AndroidDexClass,
    AndroidDexType,
    ParsedAndroidDex,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkPackageRequirement,
)

from treeforge.android.extraction.model import (
    ExtractionOperation,
)
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
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
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
from treeforge.android.parsing.art_runtime import (
    ParsedAndroidOat,
    ParsedAndroidOatDexFile,
)


class AndroidUniverseRelationshipStatus(
    StrEnum
):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class AndroidUniverseArtifactFulfillmentStatus(
    StrEnum
):
    """
    Canonical artifact-fulfillment conclusion for a relationship whose
    requirement is satisfied by a concrete Universe artifact.

    Fulfillment is deliberately independent of relationship resolution and
    applicability. A relationship may remain unresolved while Universe has
    nevertheless established that no canonical artifact fulfills it.
    """

    FULFILLED = "fulfilled"
    ABSENT = "absent"
    INDETERMINATE = "indeterminate"


class AndroidUniverseSelinuxTypeFulfillmentStatus(
    StrEnum
):
    """
    Canonical fulfillment conclusion for an explicit INIT seclabel type.

    Fulfillment is deliberately independent of structural relationship
    resolution and applicability.

    FULFILLED means the canonical SELinux policy graph contains the requested
    type symbol.

    ABSENT means the explicit INIT seclabel requests a concrete type but the
    complete canonical SELinux type-symbol population contains no such symbol.

    INDETERMINATE is retained for relationship states where canonical evidence
    is not sufficient to establish either presence or absence.
    """

    FULFILLED = "fulfilled"
    ABSENT = "absent"
    INDETERMINATE = "indeterminate"


class AndroidUniverseRelationshipKind(
    StrEnum
):
    INIT_EXECUTABLE_ARTIFACT = (
        "init_executable_artifact"
    )
    INIT_EXECUTABLE_SELINUX_FILE_LABEL = (
        "init_executable_selinux_file_label"
    )
    INIT_SECLABEL_SELINUX_TYPE = (
        "init_seclabel_selinux_type"
    )
    INIT_INTERFACE_VINTF_INTERFACE = (
        "init_interface_vintf_interface"
    )
    APK_VINTF_STRUCTURAL_PROVIDER = (
        "apk_vintf_structural_provider"
    )
    PROPERTY_SELINUX_PROPERTY_LABEL = (
        "property_selinux_property_label"
    )

    INIT_SERVICE_CONTROL = (
        "init_service_control"
    )
    INIT_CLASS_CONTROL = (
        "init_class_control"
    )
    INIT_EVENT_TRIGGER = (
        "init_event_trigger"
    )
    INIT_PROPERTY_COMMAND = (
        "init_property_command"
    )
    INIT_PROPERTY_TRIGGER = (
        "init_property_trigger"
    )

    FIRST_STAGE_KERNEL_MODULE_LOADING = (
        "first_stage_kernel_module_loading"
    )
    ART_RUNTIME_CLASSPATH = (
        "art_runtime_classpath"
    )
    LINKER_APEX = (
        "linker_apex"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitClassControlRelationship:
    """
    Connect one canonical INIT class-control command to the effective
    services belonging to its target service class.

    Class names are not service identities. A class relationship is resolved
    whenever at least one effective service belongs to the class. Multiple
    class members are normal INIT semantics and never constitute ambiguity.

    The original action, command, literal target, property-expanded target,
    and every matched service remain preserved.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_action: AndroidUniverseInitActionRequirement
    command_requirement: AndroidUniverseInitActionCommandRequirement

    control_kind: str
    target: str

    matched_services: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ]

    expanded_target: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_CLASS_CONTROL
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an "
                "AndroidUniverseInitActionRequirement"
            )

        if not isinstance(
            self.command_requirement,
            AndroidUniverseInitActionCommandRequirement,
        ):
            raise TypeError(
                "command_requirement must be an "
                "AndroidUniverseInitActionCommandRequirement"
            )

        if (
            self.command_requirement
            not in self.init_action.command_requirements
        ):
            raise ValueError(
                "command_requirement must belong to init_action"
            )

        if self.control_kind not in {
            "class_start",
            "class_stop",
        }:
            raise ValueError(
                "unsupported class control_kind"
            )

        if (
            not isinstance(
                self.target,
                str,
            )
            or not self.target
        ):
            raise ValueError(
                "target must be a non-empty string"
            )

        if not isinstance(
            self.matched_services,
            tuple,
        ):
            raise TypeError(
                "matched_services must be a tuple"
            )

        if not all(
            isinstance(
                service,
                AndroidUniverseInitServiceRequirement,
            )
            for service
            in self.matched_services
        ):
            raise TypeError(
                "matched_services must contain only "
                "AndroidUniverseInitServiceRequirement instances"
            )

        if (
            self.expanded_target is not None
            and (
                not isinstance(
                    self.expanded_target,
                    str,
                )
                or not self.expanded_target
            )
        ):
            raise ValueError(
                "expanded_target must be a non-empty string or None"
            )

        expected_status = (
            AndroidUniverseRelationshipStatus.RESOLVED
            if self.matched_services
            else AndroidUniverseRelationshipStatus.UNRESOLVED
        )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match class-control resolution"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-class-control:"
            f"{self.init_action.requirement_id}:"
            f"{self.command_requirement.command.location.line}:"
            f"{self.control_kind}:"
            f"{self.target}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitServiceControlRelationship:
    """
    Connect one canonical INIT service-control command to the service
    declarations that its target resolves against.

    Exactly one relationship is retained for each control command. This
    preserves unresolved targets rather than silently dropping them and keeps
    ambiguity explicit when a direct service name identifies more than one
    canonical declaration.

    Class control is intentionally different: one class normally contains
    multiple services, so any non-empty class match is resolved rather than
    ambiguous.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_action: AndroidUniverseInitActionRequirement
    command_requirement: AndroidUniverseInitActionCommandRequirement

    control_kind: str
    target: str

    matched_services: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ]

    expanded_target: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_SERVICE_CONTROL
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an "
                "AndroidUniverseInitActionRequirement"
            )

        if not isinstance(
            self.command_requirement,
            AndroidUniverseInitActionCommandRequirement,
        ):
            raise TypeError(
                "command_requirement must be an "
                "AndroidUniverseInitActionCommandRequirement"
            )

        if (
            self.command_requirement
            not in self.init_action.command_requirements
        ):
            raise ValueError(
                "command_requirement must belong to init_action"
            )

        if (
            not isinstance(
                self.control_kind,
                str,
            )
            or not self.control_kind
        ):
            raise ValueError(
                "control_kind must be a non-empty string"
            )

        if self.control_kind not in {
            "start",
            "stop",
            "restart",
            "exec_start",
            "enable",
        }:
            raise ValueError(
                "unsupported control_kind"
            )

        if (
            not isinstance(
                self.target,
                str,
            )
            or not self.target
        ):
            raise ValueError(
                "target must be a non-empty string"
            )

        if not isinstance(
            self.matched_services,
            tuple,
        ):
            raise TypeError(
                "matched_services must be a tuple"
            )

        if (
            self.expanded_target is not None
            and (
                not isinstance(
                    self.expanded_target,
                    str,
                )
                or not self.expanded_target
            )
        ):
            raise ValueError(
                "expanded_target must be a non-empty string or None"
            )

        if not all(
            isinstance(
                service,
                AndroidUniverseInitServiceRequirement,
            )
            for service in self.matched_services
        ):
            raise TypeError(
                "matched_services must contain only "
                "AndroidUniverseInitServiceRequirement instances"
            )

        if not self.matched_services:
            expected_status = (
                AndroidUniverseRelationshipStatus.UNRESOLVED
            )

        elif len(
            self.matched_services
        ) == 1:
            expected_status = (
                AndroidUniverseRelationshipStatus.RESOLVED
            )

        else:
            expected_status = (
                AndroidUniverseRelationshipStatus.AMBIGUOUS
            )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match service-control resolution"
            )

    @property
    def is_class_control(
        self,
    ) -> bool:
        return self.control_kind.startswith(
            "class_"
        )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-service-control:"
            f"{self.init_action.requirement_id}:"
            f"{self.command_requirement.command.location.line}:"
            f"{self.control_kind}:"
            f"{self.target}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitOnRestartClassControlRelationship:
    """
    Connect one service-owned INIT ``onrestart class_restart`` command to the
    effective services belonging to the referenced service class.

    Class membership is a many-member namespace by design. Any non-empty
    matched service set therefore resolves the relationship.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement
    onrestart_command: AndroidUniverseInitOnRestartCommand

    control_kind: str
    target: str

    matched_services: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ]

    expanded_target: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_CLASS_CONTROL
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an "
                "AndroidUniverseInitServiceRequirement"
            )

        if not isinstance(
            self.onrestart_command,
            AndroidUniverseInitOnRestartCommand,
        ):
            raise TypeError(
                "onrestart_command must be an "
                "AndroidUniverseInitOnRestartCommand"
            )

        if (
            self.onrestart_command
            not in self.init_service.semantics.onrestart_commands
        ):
            raise ValueError(
                "onrestart_command must belong to init_service"
            )

        if self.control_kind != "class_restart":
            raise ValueError(
                "unsupported onrestart class control_kind"
            )

        if (
            not isinstance(
                self.target,
                str,
            )
            or not self.target
        ):
            raise ValueError(
                "target must be a non-empty string"
            )

        if not isinstance(
            self.matched_services,
            tuple,
        ):
            raise TypeError(
                "matched_services must be a tuple"
            )

        if not all(
            isinstance(
                service,
                AndroidUniverseInitServiceRequirement,
            )
            for service
            in self.matched_services
        ):
            raise TypeError(
                "matched_services must contain only "
                "AndroidUniverseInitServiceRequirement instances"
            )

        if (
            self.expanded_target is not None
            and (
                not isinstance(
                    self.expanded_target,
                    str,
                )
                or not self.expanded_target
            )
        ):
            raise ValueError(
                "expanded_target must be a non-empty string or None"
            )

        expected_status = (
            AndroidUniverseRelationshipStatus.RESOLVED
            if self.matched_services
            else AndroidUniverseRelationshipStatus.UNRESOLVED
        )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match onrestart "
                "class-control resolution"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-onrestart-class-control:"
            f"{self.init_service.requirement_id}:"
            f"{self.onrestart_command.declaration.location.line}:"
            f"{self.control_kind}:"
            f"{self.target}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitOnRestartServiceControlRelationship:
    """
    Connect one service-owned ``onrestart`` control command to canonical
    INIT service declarations.

    The owning service and original onrestart command remain explicit.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement
    onrestart_command: AndroidUniverseInitOnRestartCommand

    control_kind: str
    target: str

    matched_services: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ]

    expanded_target: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_SERVICE_CONTROL
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an "
                "AndroidUniverseInitServiceRequirement"
            )

        if not isinstance(
            self.onrestart_command,
            AndroidUniverseInitOnRestartCommand,
        ):
            raise TypeError(
                "onrestart_command must be an "
                "AndroidUniverseInitOnRestartCommand"
            )

        if (
            self.onrestart_command
            not in self.init_service.semantics.onrestart_commands
        ):
            raise ValueError(
                "onrestart_command must belong to init_service"
            )

        if self.control_kind != "restart":
            raise ValueError(
                "unsupported onrestart control_kind"
            )

        if (
            not isinstance(
                self.target,
                str,
            )
            or not self.target
        ):
            raise ValueError(
                "target must be a non-empty string"
            )

        if not isinstance(
            self.matched_services,
            tuple,
        ):
            raise TypeError(
                "matched_services must be a tuple"
            )

        if (
            self.expanded_target is not None
            and (
                not isinstance(
                    self.expanded_target,
                    str,
                )
                or not self.expanded_target
            )
        ):
            raise ValueError(
                "expanded_target must be a non-empty string or None"
            )

        if not all(
            isinstance(
                service,
                AndroidUniverseInitServiceRequirement,
            )
            for service in self.matched_services
        ):
            raise TypeError(
                "matched_services must contain only "
                "AndroidUniverseInitServiceRequirement instances"
            )

        if not self.matched_services:
            expected_status = (
                AndroidUniverseRelationshipStatus.UNRESOLVED
            )

        elif len(
            self.matched_services
        ) == 1:
            expected_status = (
                AndroidUniverseRelationshipStatus.RESOLVED
            )

        else:
            expected_status = (
                AndroidUniverseRelationshipStatus.AMBIGUOUS
            )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match onrestart "
                "service-control resolution"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-onrestart-service-control:"
            f"{self.init_service.requirement_id}:"
            f"{self.onrestart_command.declaration.location.line}:"
            f"{self.control_kind}:"
            f"{self.target}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitEventTriggerRelationship:
    """
    Connect one canonical INIT ``trigger <event>`` command to every
    canonical INIT action that listens for the named event.

    Multiple matching actions are normal Android INIT event fan-out.

    ``matched_actions`` records known canonical listeners for the emitted
    event. Listener presence does not determine command validity: Android
    init's ``trigger`` builtin queues the event successfully even when no
    action listens for it.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_action: AndroidUniverseInitActionRequirement
    command_requirement: AndroidUniverseInitActionCommandRequirement

    event: str

    matched_actions: tuple[
        AndroidUniverseInitActionRequirement,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_EVENT_TRIGGER
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an "
                "AndroidUniverseInitActionRequirement"
            )

        if not isinstance(
            self.command_requirement,
            AndroidUniverseInitActionCommandRequirement,
        ):
            raise TypeError(
                "command_requirement must be an "
                "AndroidUniverseInitActionCommandRequirement"
            )

        if (
            self.command_requirement
            not in self.init_action.command_requirements
        ):
            raise ValueError(
                "command_requirement must belong to init_action"
            )

        if (
            not isinstance(
                self.event,
                str,
            )
            or not self.event
        ):
            raise ValueError(
                "event must be a non-empty string"
            )

        if not isinstance(
            self.matched_actions,
            tuple,
        ):
            raise TypeError(
                "matched_actions must be a tuple"
            )

        if not all(
            isinstance(
                action,
                AndroidUniverseInitActionRequirement,
            )
            for action in self.matched_actions
        ):
            raise TypeError(
                "matched_actions must contain only "
                "AndroidUniverseInitActionRequirement instances"
            )

        if (
            self.status
            is not AndroidUniverseRelationshipStatus.RESOLVED
        ):
            raise ValueError(
                "INIT trigger command relationships must be resolved"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-event-trigger:"
            f"{self.init_action.requirement_id}:"
            f"{self.command_requirement.command.location.line}:"
            f"{self.event}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitPropertyCommandRelationship:
    """
    Connect one INIT property command to canonical property evidence.

    ``setprop`` and ``wait_for_prop`` preserve their literal requested
    key/value pair. Matching evidence is collected by property key only;
    deciding the canonical device-level value remains the responsibility
    of the property reconciler.

    Missing property declarations remain explicit unresolved relationships.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_action: AndroidUniverseInitActionRequirement
    command_requirement: AndroidUniverseInitActionCommandRequirement

    command_kind: str
    property_key: str
    property_value: str

    runtime_property: (
        AndroidUniverseRuntimePropertyRequirement
        | None
    )

    property_evidence: tuple

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_PROPERTY_COMMAND
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an "
                "AndroidUniverseInitActionRequirement"
            )

        if not isinstance(
            self.command_requirement,
            AndroidUniverseInitActionCommandRequirement,
        ):
            raise TypeError(
                "command_requirement must be an "
                "AndroidUniverseInitActionCommandRequirement"
            )

        if (
            self.command_requirement
            not in self.init_action.command_requirements
        ):
            raise ValueError(
                "command_requirement must belong to init_action"
            )

        if self.command_kind not in {
            "setprop",
            "wait_for_prop",
        }:
            raise ValueError(
                "unsupported command_kind"
            )

        if (
            not isinstance(
                self.property_key,
                str,
            )
            or not self.property_key
        ):
            raise ValueError(
                "property_key must be a non-empty string"
            )

        if not isinstance(
            self.property_value,
            str,
        ):
            raise TypeError(
                "property_value must be a string"
            )

        if (
            self.runtime_property is not None
            and not isinstance(
                self.runtime_property,
                AndroidUniverseRuntimePropertyRequirement,
            )
        ):
            raise TypeError(
                "runtime_property must be an "
                "AndroidUniverseRuntimePropertyRequirement or None"
            )

        if (
            self.runtime_property is not None
            and (
                self.runtime_property.property_key
                != self.property_key
            )
        ):
            raise ValueError(
                "runtime_property must match property_key"
            )

        if not isinstance(
            self.property_evidence,
            tuple,
        ):
            raise TypeError(
                "property_evidence must be a tuple"
            )

        expected_status = (
            AndroidUniverseRelationshipStatus.RESOLVED
            if self.runtime_property is not None
            else AndroidUniverseRelationshipStatus.UNRESOLVED
        )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match property-command resolution"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-property-command:"
            f"{self.init_action.requirement_id}:"
            f"{self.command_requirement.command.location.line}:"
            f"{self.command_kind}:"
            f"{self.property_key}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitOnRestartPropertyCommandRelationship:
    """
    Connect one service-owned ``onrestart setprop`` command to canonical
    property evidence.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement
    onrestart_command: AndroidUniverseInitOnRestartCommand

    property_key: str
    property_value: str

    runtime_property: (
        AndroidUniverseRuntimePropertyRequirement
        | None
    )

    property_evidence: tuple

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_PROPERTY_COMMAND
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an "
                "AndroidUniverseInitServiceRequirement"
            )

        if not isinstance(
            self.onrestart_command,
            AndroidUniverseInitOnRestartCommand,
        ):
            raise TypeError(
                "onrestart_command must be an "
                "AndroidUniverseInitOnRestartCommand"
            )

        if (
            self.onrestart_command
            not in self.init_service.semantics.onrestart_commands
        ):
            raise ValueError(
                "onrestart_command must belong to init_service"
            )

        if self.onrestart_command.command != "setprop":
            raise ValueError(
                "onrestart property relationship requires setprop"
            )

        if (
            not isinstance(
                self.property_key,
                str,
            )
            or not self.property_key
        ):
            raise ValueError(
                "property_key must be a non-empty string"
            )

        if not isinstance(
            self.property_value,
            str,
        ):
            raise TypeError(
                "property_value must be a string"
            )

        if (
            self.runtime_property is not None
            and not isinstance(
                self.runtime_property,
                AndroidUniverseRuntimePropertyRequirement,
            )
        ):
            raise TypeError(
                "runtime_property must be an "
                "AndroidUniverseRuntimePropertyRequirement or None"
            )

        if (
            self.runtime_property is not None
            and (
                self.runtime_property.property_key
                != self.property_key
            )
        ):
            raise ValueError(
                "runtime_property must match property_key"
            )

        if not isinstance(
            self.property_evidence,
            tuple,
        ):
            raise TypeError(
                "property_evidence must be a tuple"
            )

        expected_status = (
            AndroidUniverseRelationshipStatus.RESOLVED
            if self.runtime_property is not None
            else AndroidUniverseRelationshipStatus.UNRESOLVED
        )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match onrestart "
                "property-command resolution"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-onrestart-property-command:"
            f"{self.init_service.requirement_id}:"
            f"{self.onrestart_command.declaration.location.line}:"
            f"{self.property_key}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitPropertyTriggerRelationship:
    """
    Connect one INIT property-trigger predicate to canonical property
    evidence for the referenced key.

    The literal predicate value is retained, including wildcard and empty
    values. Multiple property declarations are normal evidence fan-in.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_action: AndroidUniverseInitActionRequirement

    property_key: str
    property_value: str

    runtime_property: (
        AndroidUniverseRuntimePropertyRequirement
        | None
    )

    property_evidence: tuple

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_PROPERTY_TRIGGER
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an "
                "AndroidUniverseInitActionRequirement"
            )

        if (
            not isinstance(
                self.property_key,
                str,
            )
            or not self.property_key
        ):
            raise ValueError(
                "property_key must be a non-empty string"
            )

        if not isinstance(
            self.property_value,
            str,
        ):
            raise TypeError(
                "property_value must be a string"
            )

        if (
            self.runtime_property is not None
            and not isinstance(
                self.runtime_property,
                AndroidUniverseRuntimePropertyRequirement,
            )
        ):
            raise TypeError(
                "runtime_property must be an "
                "AndroidUniverseRuntimePropertyRequirement or None"
            )

        if (
            self.runtime_property is not None
            and (
                self.runtime_property.property_key
                != self.property_key
            )
        ):
            raise ValueError(
                "runtime_property must match property_key"
            )

        if not isinstance(
            self.property_evidence,
            tuple,
        ):
            raise TypeError(
                "property_evidence must be a tuple"
            )

        expected_status = (
            AndroidUniverseRelationshipStatus.RESOLVED
            if self.runtime_property is not None
            else AndroidUniverseRelationshipStatus.UNRESOLVED
        )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match property-trigger resolution"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-property-trigger:"
            f"{self.init_action.requirement_id}:"
            f"{self.property_key}:"
            f"{self.property_value}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitExecutableArtifactRelationship:
    """
    Connect one canonical INIT service executable reference to canonical
    Universe filesystem artifact requirements.

    The relationship resolves only against the already-built Universe
    artifact inventory. It never traverses a filesystem, opens an artifact,
    or infers source ownership.

    ``matched_artifacts`` preserves every exact canonical match. No match
    remains UNRESOLVED and multiple matches remain AMBIGUOUS.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement
    executable_path: str

    matched_artifacts: tuple[
        AndroidUniverseArtifactRequirement,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_EXECUTABLE_ARTIFACT
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an "
                "AndroidUniverseInitServiceRequirement"
            )

        if (
            not isinstance(
                self.executable_path,
                str,
            )
            or not self.executable_path
        ):
            raise ValueError(
                "executable_path must be a non-empty string"
            )

        if not isinstance(
            self.matched_artifacts,
            tuple,
        ):
            raise TypeError(
                "matched_artifacts must be a tuple"
            )

        if not all(
            isinstance(
                artifact,
                AndroidUniverseArtifactRequirement,
            )
            for artifact
            in self.matched_artifacts
        ):
            raise TypeError(
                "matched_artifacts must contain only "
                "AndroidUniverseArtifactRequirement instances"
            )

        identities = tuple(
            artifact.identity_key
            for artifact
            in self.matched_artifacts
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "matched_artifacts must preserve unique "
                "canonical artifact identities"
            )

        expected_status = (
            AndroidUniverseRelationshipStatus.UNRESOLVED
            if not self.matched_artifacts
            else (
                AndroidUniverseRelationshipStatus.RESOLVED
                if len(
                    self.matched_artifacts
                ) == 1
                else AndroidUniverseRelationshipStatus.AMBIGUOUS
            )
        )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match executable artifact resolution"
            )

    @property
    def artifact_fulfillment(
        self,
    ) -> AndroidUniverseArtifactFulfillmentStatus:
        """
        Report whether canonical Universe artifact evidence fulfills this
        executable requirement.

        Applicability is intentionally not considered here. ACTIVE versus
        ALTERNATIVE is a separate Universe conclusion. Consumers combine the
        two conclusions when deciding whether an absence is actionable.
        """

        if (
            self.status
            is AndroidUniverseRelationshipStatus.RESOLVED
        ):
            return (
                AndroidUniverseArtifactFulfillmentStatus
                .FULFILLED
            )

        if (
            self.status
            is AndroidUniverseRelationshipStatus.UNRESOLVED
            and not self.matched_artifacts
        ):
            return (
                AndroidUniverseArtifactFulfillmentStatus
                .ABSENT
            )

        return (
            AndroidUniverseArtifactFulfillmentStatus
            .INDETERMINATE
        )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-executable-artifact:"
            f"{self.init_service.requirement_id}:"
            f"{self.executable_path}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitExecutableSelinuxRelationship:
    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement

    context_requirements: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ]

    resolved_type: str | None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_EXECUTABLE_SELINUX_FILE_LABEL
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an "
                "AndroidUniverseInitServiceRequirement"
            )

        if not isinstance(
            self.context_requirements,
            tuple,
        ):
            raise TypeError(
                "context_requirements must be a tuple"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-executable-selinux:"
            f"{self.init_service.requirement_id}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitSeclabelSelinuxRelationship:
    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement

    seclabel: str
    selinux_type: str

    symbol: AndroidUniverseSelinuxSymbol | None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_SECLABEL_SELINUX_TYPE
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an "
                "AndroidUniverseInitServiceRequirement"
            )

        if not isinstance(
            self.seclabel,
            str,
        ) or not self.seclabel:
            raise ValueError(
                "seclabel must be a non-empty string"
            )

        if not isinstance(
            self.selinux_type,
            str,
        ) or not self.selinux_type:
            raise ValueError(
                "selinux_type must be a non-empty string"
            )

    @property
    def type_fulfillment(
        self,
    ) -> AndroidUniverseSelinuxTypeFulfillmentStatus:
        """
        Return canonical fulfillment of the explicit SELinux type request.

        The structural relationship remains UNRESOLVED when no exact symbol
        can be linked.  A missing symbol is nevertheless a closed canonical
        absence conclusion rather than an unknown provider identity.
        """

        if self.symbol is not None:
            return (
                AndroidUniverseSelinuxTypeFulfillmentStatus
                .FULFILLED
            )

        if (
            self.status
            is AndroidUniverseRelationshipStatus.UNRESOLVED
        ):
            return (
                AndroidUniverseSelinuxTypeFulfillmentStatus
                .ABSENT
            )

        return (
            AndroidUniverseSelinuxTypeFulfillmentStatus
            .INDETERMINATE
        )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-seclabel-selinux:"
            f"{self.init_service.requirement_id}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfInterfaceEvidence:
    document: AndroidUniverseVintfDocumentRequirement
    hal: AndroidUniverseVintfHalRequirement
    interface: AndroidUniverseVintfHalInterface | None
    instance: str
    canonical_name: str


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitInterfaceVintfRelationship:
    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    init_service: AndroidUniverseInitServiceRequirement
    init_interface: AndroidUniverseInitInterfaceSemantics

    canonical_name: str

    vintf_evidence: tuple[
        AndroidUniverseVintfInterfaceEvidence,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .INIT_INTERFACE_VINTF_INTERFACE
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if self.status is not AndroidUniverseRelationshipStatus.RESOLVED:
            raise ValueError(
                "exact INIT to VINTF relationships must be resolved"
            )

        if not self.vintf_evidence:
            raise ValueError(
                "vintf_evidence must not be empty"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:init-interface-vintf:"
            f"{self.init_service.requirement_id}:"
            f"{self.init_interface.transport}:"
            f"{self.canonical_name}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniversePropertySelinuxRelationship:
    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    property_key: str

    property_evidence: tuple[
        AndroidUniversePropertyEvidence,
        ...,
    ]

    context_requirements: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ]

    match_kind: AndroidUniversePropertyContextMatchKind

    resolved_type: str | None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .PROPERTY_SELINUX_PROPERTY_LABEL
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.property_key,
            str,
        ) or not self.property_key:
            raise ValueError(
                "property_key must be a non-empty string"
            )

        if not isinstance(
            self.property_evidence,
            tuple,
        ):
            raise TypeError(
                "property_evidence must be a tuple"
            )

        if not isinstance(
            self.context_requirements,
            tuple,
        ):
            raise TypeError(
                "context_requirements must be a tuple"
            )

        if not isinstance(
            self.match_kind,
            AndroidUniversePropertyContextMatchKind,
        ):
            raise TypeError(
                "match_kind must be an "
                "AndroidUniversePropertyContextMatchKind"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:property-selinux:"
            f"{self.property_key}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeClasspathDexEvidence:
    """
    One exact ART OatDexFile observation substantiating a canonical
    effective Classpath entry.

    ``base_location`` is the ART runtime source location after collapsing
    multidex suffix syntax such as ``!classes2.dex`` to its owning JAR/APK
    path. The original ParsedAndroidOatDexFile remains preserved unchanged.
    """

    oat: ParsedAndroidOat
    oat_dex_file: ParsedAndroidOatDexFile
    base_location: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.oat,
            ParsedAndroidOat,
        ):
            raise TypeError(
                "oat must be a ParsedAndroidOat"
            )

        if not isinstance(
            self.oat_dex_file,
            ParsedAndroidOatDexFile,
        ):
            raise TypeError(
                "oat_dex_file must be a ParsedAndroidOatDexFile"
            )

        if (
            not isinstance(
                self.base_location,
                str,
            )
            or not self.base_location
        ):
            raise ValueError(
                "base_location must be a non-empty string"
            )

        expected_base_location = (
            self.oat_dex_file.dex_file_location.split(
                "!",
                1,
            )[0]
        )

        if self.base_location != expected_base_location:
            raise ValueError(
                "base_location must preserve the canonical ART "
                "multidex base location"
            )


class AndroidUniverseArtRuntimeClasspathVdexMatchKind(
    StrEnum
):
    """
    Canonical rule relating one standalone ART VDEX to an effective
    boot Classpath entry.
    """

    BASE_DEX2OAT_BOOT = "base_dex2oat_boot"
    NAMED_BOOT_COMPONENT = "named_boot_component"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeClasspathVdexEvidence:
    """
    One exact NO_OAT_PEER VDEX disposition corroborating an effective
    boot Classpath entry.

    The original parsed VDEX identity remains owned by ART Runtime.
    This model records only the late cross-family relationship.
    """

    disposition: AndroidUniverseArtRuntimeVdexDisposition
    match_kind: AndroidUniverseArtRuntimeClasspathVdexMatchKind

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.disposition,
            AndroidUniverseArtRuntimeVdexDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidUniverseArtRuntimeVdexDisposition"
            )

        if (
            self.disposition.status
            is not AndroidUniverseArtRuntimeVdexDispositionStatus
            .NO_OAT_PEER
        ):
            raise ValueError(
                "ART Runtime/Classpath VDEX evidence must reference "
                "a NO_OAT_PEER VDEX disposition"
            )

        if not isinstance(
            self.match_kind,
            AndroidUniverseArtRuntimeClasspathVdexMatchKind,
        ):
            raise TypeError(
                "match_kind must be an "
                "AndroidUniverseArtRuntimeClasspathVdexMatchKind"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeClasspathRelationship:
    """
    Connect one exact effective Classpath entry to all canonical ART
    OatDexFile observations whose base runtime location equals the entry's
    declared runtime JAR path.

    One relationship is retained per effective Classpath entry. Repeated
    declarations of the same runtime JAR therefore remain distinct canonical
    relationships.

    Multiple matching OatDexFile observations are normal ART runtime evidence
    and never constitute ambiguity.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    entry: AndroidUniverseClasspathEffectiveEntry

    installed_jar_resolution: (
        AndroidUniverseClasspathInstalledJarResolution
    )

    dex_evidence: tuple[
        AndroidUniverseArtRuntimeClasspathDexEvidence,
        ...,
    ]

    vdex_evidence: tuple[
        AndroidUniverseArtRuntimeClasspathVdexEvidence,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind.ART_RUNTIME_CLASSPATH
        ):
            raise ValueError(
                "invalid ART Runtime/Classpath relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.entry,
            AndroidUniverseClasspathEffectiveEntry,
        ):
            raise TypeError(
                "entry must be an AndroidUniverseClasspathEffectiveEntry"
            )

        if not isinstance(
            self.installed_jar_resolution,
            AndroidUniverseClasspathInstalledJarResolution,
        ):
            raise TypeError(
                "installed_jar_resolution must be an "
                "AndroidUniverseClasspathInstalledJarResolution"
            )

        if (
            self.installed_jar_resolution.entry
            is not self.entry
        ):
            raise ValueError(
                "installed JAR resolution must preserve exact effective "
                "Classpath entry identity"
            )

        if not isinstance(
            self.dex_evidence,
            tuple,
        ):
            raise TypeError(
                "dex_evidence must be a tuple"
            )

        if not all(
            isinstance(
                evidence,
                AndroidUniverseArtRuntimeClasspathDexEvidence,
            )
            for evidence in self.dex_evidence
        ):
            raise TypeError(
                "dex_evidence must contain only "
                "AndroidUniverseArtRuntimeClasspathDexEvidence instances"
            )

        if not isinstance(
            self.vdex_evidence,
            tuple,
        ):
            raise TypeError(
                "vdex_evidence must be a tuple"
            )

        if not all(
            isinstance(
                evidence,
                AndroidUniverseArtRuntimeClasspathVdexEvidence,
            )
            for evidence
            in self.vdex_evidence
        ):
            raise TypeError(
                "vdex_evidence must contain only "
                "AndroidUniverseArtRuntimeClasspathVdexEvidence instances"
            )

        vdex_identity_keys = tuple(
            evidence.disposition.vdex.source.identity_key
            for evidence
            in self.vdex_evidence
        )

        if len(
            vdex_identity_keys
        ) != len(
            set(
                vdex_identity_keys
            )
        ):
            raise ValueError(
                "vdex_evidence must preserve unique canonical "
                "VDEX identities per Classpath relationship"
            )

        evidence_ids = tuple(
            (
                id(
                    evidence.oat
                ),
                id(
                    evidence.oat_dex_file
                ),
            )
            for evidence in self.dex_evidence
        )

        if len(
            evidence_ids
        ) != len(
            set(
                evidence_ids
            )
        ):
            raise ValueError(
                "dex_evidence must preserve unique canonical ART identities"
            )

        declared_path = (
            self.entry.requirement.declared_path
        )

        if not declared_path.startswith(
            "/"
        ):
            declared_path = (
                "/"
                + declared_path
            )

        for evidence in self.dex_evidence:
            if evidence.base_location != declared_path:
                raise ValueError(
                    "ART DEX evidence base location must match exact "
                    "Classpath runtime path"
                )

        expected_status = (
            AndroidUniverseRelationshipStatus.RESOLVED
            if (
                self.dex_evidence
                or self.vdex_evidence
            )
            else AndroidUniverseRelationshipStatus.UNRESOLVED
        )

        if self.status is not expected_status:
            raise ValueError(
                "ART Runtime/Classpath relationship status does not "
                "match DEX evidence"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:art-runtime-classpath:"
            f"{self.entry.requirement.requirement_id}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFirstStageKernelModuleLoadingRelationship:
    """
    Connect one exact Boot-owned first-stage module-loading policy to the
    exact Kernel-Module-owned modules.load population carried directly in
    vendor_kernel_boot.

    ``policy`` remains the sole owner of the interpreted parallel-loading
    Boolean. This relationship does not duplicate or reinterpret that value.

    ``load_entries`` preserve the exact canonical modules.load identities and
    source sequence indexes. Parallel execution policy does not rewrite the
    declared list ordering.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    policy: AndroidUniverseFirstStageModuleLoadingPolicy

    load_entries: tuple[
        AndroidUniverseKernelModuleLoadEntry,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .FIRST_STAGE_KERNEL_MODULE_LOADING
        ):
            raise ValueError(
                "invalid first-stage kernel-module loading relationship kind"
            )

        if (
            self.status
            is not AndroidUniverseRelationshipStatus.RESOLVED
        ):
            raise ValueError(
                "first-stage kernel-module loading relationship "
                "must be RESOLVED"
            )

        if not isinstance(
            self.policy,
            AndroidUniverseFirstStageModuleLoadingPolicy,
        ):
            raise TypeError(
                "policy must be an "
                "AndroidUniverseFirstStageModuleLoadingPolicy"
            )

        if not isinstance(
            self.load_entries,
            tuple,
        ):
            raise TypeError(
                "load_entries must be a tuple"
            )

        if not self.load_entries:
            raise ValueError(
                "first-stage module-loading relationship requires "
                "at least one load entry"
            )

        if not all(
            isinstance(
                entry,
                AndroidUniverseKernelModuleLoadEntry,
            )
            for entry in self.load_entries
        ):
            raise TypeError(
                "load_entries must contain only "
                "AndroidUniverseKernelModuleLoadEntry instances"
            )

        load_entry_ids = tuple(
            id(
                entry
            )
            for entry in self.load_entries
        )

        if len(
            load_entry_ids
        ) != len(
            set(
                load_entry_ids
            )
        ):
            raise ValueError(
                "load_entries must preserve unique canonical identities"
            )

        for entry in self.load_entries:
            context = (
                entry.module.source.elf.source
                .filesystem_source.source_name
            )

            if context != "vendor_kernel_boot":
                raise ValueError(
                    "first-stage module-loading relationship may contain "
                    "only vendor_kernel_boot load entries"
                )

        sequence_indexes = tuple(
            entry.sequence_index
            for entry in self.load_entries
        )

        if sequence_indexes != tuple(
            sorted(
                sequence_indexes
            )
        ):
            raise ValueError(
                "load_entries must preserve canonical modules.load "
                "source ordering"
            )

        if len(
            sequence_indexes
        ) != len(
            set(
                sequence_indexes
            )
        ):
            raise ValueError(
                "load_entries must preserve unique modules.load "
                "source ordinals"
            )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:first-stage-kernel-module-loading:"
            f"{self.policy.source.index}:"
            f"{self.policy.source.key}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexRelationship:
    """
    Relate one canonical APEX requirement to the Linker runtime policy whose
    canonical runtime context contains that APEX.

    This relationship establishes runtime-scoped Linker/APEX membership only.
    Native-library provider/requirement resolution remains a later semantic
    reconciliation step.

    The exact APEX requirement and exact matching runtime-policy objects are
    preserved without reparsing or copying manifest declarations.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    apex_requirement: AndroidUniverseApexRequirement

    matched_runtime_policies: tuple[
        AndroidUniverseLinkerRuntimePolicy,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind.LINKER_APEX
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseRelationshipStatus"
            )

        if not isinstance(
            self.apex_requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "apex_requirement must be an "
                "AndroidUniverseApexRequirement"
            )

        if not isinstance(
            self.matched_runtime_policies,
            tuple,
        ):
            raise TypeError(
                "matched_runtime_policies must be a tuple"
            )

        if not all(
            isinstance(
                policy,
                AndroidUniverseLinkerRuntimePolicy,
            )
            for policy in self.matched_runtime_policies
        ):
            raise TypeError(
                "matched_runtime_policies must contain only "
                "AndroidUniverseLinkerRuntimePolicy instances"
            )

        if not self.matched_runtime_policies:
            expected_status = (
                AndroidUniverseRelationshipStatus.UNRESOLVED
            )

        elif len(
            self.matched_runtime_policies
        ) == 1:
            expected_status = (
                AndroidUniverseRelationshipStatus.RESOLVED
            )

        else:
            expected_status = (
                AndroidUniverseRelationshipStatus.AMBIGUOUS
            )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match Linker/APEX runtime-policy "
                "membership resolution"
            )

    @property
    def runtime_policy(
        self,
    ) -> AndroidUniverseLinkerRuntimePolicy | None:
        if len(
            self.matched_runtime_policies
        ) != 1:
            return None

        return self.matched_runtime_policies[
            0
        ]

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:linker-apex:"
            f"{self.apex_requirement.requirement_id}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexContextApplicability:
    """
    Canonical Linker protobuf context applicability for one resolved
    Linker/APEX runtime-membership relationship.

    This layer selects only the applicable partition-context protobuf
    semantics. It does not yet resolve native-library providers.
    """

    membership_relationship: AndroidUniverseLinkerApexRelationship

    applicable_contexts: tuple[
        AndroidUniverseLinkerProtobufConfigurationSemantics,
        ...,
    ]

    status: AndroidUniverseRelationshipStatus

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.membership_relationship,
            AndroidUniverseLinkerApexRelationship,
        ):
            raise TypeError(
                "membership_relationship must be an "
                "AndroidUniverseLinkerApexRelationship"
            )

        if not isinstance(
            self.applicable_contexts,
            tuple,
        ):
            raise TypeError(
                "applicable_contexts must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseLinkerProtobufConfigurationSemantics,
            )
            for value in self.applicable_contexts
        ):
            raise TypeError(
                "applicable_contexts must contain only "
                "AndroidUniverseLinkerProtobufConfigurationSemantics"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an AndroidUniverseRelationshipStatus"
            )

        if (
            self.status
            is AndroidUniverseRelationshipStatus.RESOLVED
            and not self.applicable_contexts
        ):
            raise ValueError(
                "resolved context applicability requires at least one "
                "applicable Linker protobuf context"
            )

        if (
            self.status
            is not AndroidUniverseRelationshipStatus.RESOLVED
            and self.applicable_contexts
        ):
            raise ValueError(
                "non-resolved context applicability must not select "
                "context semantics"
            )

    @property
    def applicability_id(
        self,
    ) -> str:
        return (
            "linker-apex-context:"
            f"{self.membership_relationship.relationship_id}"
        )




class AndroidUniverseLinkerElfConfigurationScope(
    StrEnum
):
    """
    Canonical Linker configuration scope governing one installed ELF.

    BASE means the ELF participates directly in its Android runtime's base
    Linker configuration. APEX means the ELF belongs to an extracted APEX
    payload whose exact canonical APEX requirement has been reconciled.

    This classification does not select a Linker section or namespace and
    does not resolve DT_NEEDED dependencies.
    """

    BASE = "base"
    APEX = "apex"


class AndroidUniverseLinkerElfRuntimeFilesystemDisposition(
    StrEnum,
):
    """
    Canonical participation of one ELF in the post-boot linker filesystem.

    POST_BOOT_APPLICABLE means the ELF is filesystem-backed and its canonical
    filesystem participates in the mounted Android runtime modeled by
    linkerconfig.

    NO_FILESYSTEM_BACKING preserves extraction-only ELF evidence that has no
    Android filesystem runtime path.

    CPIO_INAPPLICABLE identifies canonical CPIO-extracted ramdisk filesystems.
    Their Android paths belong to that ramdisk namespace and must not be
    projected into the post-boot linkerconfig filesystem.
    """

    POST_BOOT_APPLICABLE = "post_boot_applicable"
    NO_FILESYSTEM_BACKING = "no_filesystem_backing"
    CPIO_INAPPLICABLE = "cpio_inapplicable"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerElfContext:
    """
    Runtime and configuration-scope context for one canonical ELF requirement.

    The exact ELF requirement, runtime context, matching runtime-policy
    candidates, and APEX candidates are preserved by identity.

    APEX ownership is derived from canonical Extraction ancestry using nearest
    exact common-ancestor specificity. No source-name, manifest-name, device,
    partition-name, or destination guessing occurs here.

    Section routing, namespace selection, runtime mount-path synthesis, and
    DT_NEEDED provider resolution remain later Linker/ELF semantic layers.
    """

    elf_requirement: AndroidUniverseElfRequirement

    runtime_context: AndroidUniverseRuntimeContext

    configuration_scope: (
        AndroidUniverseLinkerElfConfigurationScope
    )

    matched_runtime_policies: tuple[
        AndroidUniverseLinkerRuntimePolicy,
        ...,
    ]

    apex_candidates: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ]

    selected_apex_requirement: (
        AndroidUniverseApexRequirement
        | None
    )

    status: AndroidUniverseRelationshipStatus

    def shares_runtime(
        self,
        runtime_context: AndroidUniverseRuntimeContext,
    ) -> bool:
        """
        Whether this canonical Linker/ELF context belongs to the
        supplied canonical Android runtime.
        """

        if not isinstance(
            runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        return (
            AndroidUniverseRuntimeContextResolver
            .same_runtime(
                self.runtime_context,
                runtime_context,
            )
        )

    @property
    def runtime_filesystem_disposition(
        self,
    ) -> AndroidUniverseLinkerElfRuntimeFilesystemDisposition:
        """
        Return the Universe-owned post-boot filesystem disposition.

        Exact Parsing and Extraction identities remain canonical provenance,
        but downstream Runtime Linking does not reinterpret them.
        """

        source = (
            self.elf_requirement
            .source
            .source
        )

        if not source.is_filesystem_backed:
            return (
                AndroidUniverseLinkerElfRuntimeFilesystemDisposition
                .NO_FILESYSTEM_BACKING
            )

        filesystem_source = (
            source.filesystem_source
        )

        if filesystem_source is None:
            raise ValueError(
                "filesystem-backed canonical ELF must preserve "
                "its filesystem source"
            )

        if (
            filesystem_source
            .artifact
            .operation
            is ExtractionOperation.CPIO_EXTRACTION
        ):
            return (
                AndroidUniverseLinkerElfRuntimeFilesystemDisposition
                .CPIO_INAPPLICABLE
            )

        return (
            AndroidUniverseLinkerElfRuntimeFilesystemDisposition
            .POST_BOOT_APPLICABLE
        )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.elf_requirement,
            AndroidUniverseElfRequirement,
        ):
            raise TypeError(
                "elf_requirement must be an "
                "AndroidUniverseElfRequirement"
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
            self.configuration_scope,
            AndroidUniverseLinkerElfConfigurationScope,
        ):
            raise TypeError(
                "configuration_scope must be an "
                "AndroidUniverseLinkerElfConfigurationScope"
            )

        if not isinstance(
            self.matched_runtime_policies,
            tuple,
        ):
            raise TypeError(
                "matched_runtime_policies must be a tuple"
            )

        if not all(
            isinstance(
                policy,
                AndroidUniverseLinkerRuntimePolicy,
            )
            for policy
            in self.matched_runtime_policies
        ):
            raise TypeError(
                "matched_runtime_policies must contain only "
                "AndroidUniverseLinkerRuntimePolicy instances"
            )

        if not isinstance(
            self.apex_candidates,
            tuple,
        ):
            raise TypeError(
                "apex_candidates must be a tuple"
            )

        if not all(
            isinstance(
                apex,
                AndroidUniverseApexRequirement,
            )
            for apex
            in self.apex_candidates
        ):
            raise TypeError(
                "apex_candidates must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        if (
            self.selected_apex_requirement
            is not None
            and not isinstance(
                self.selected_apex_requirement,
                AndroidUniverseApexRequirement,
            )
        ):
            raise TypeError(
                "selected_apex_requirement must be an "
                "AndroidUniverseApexRequirement or None"
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
            self.configuration_scope
            is AndroidUniverseLinkerElfConfigurationScope.BASE
        ):
            if self.apex_candidates:
                raise ValueError(
                    "BASE Linker/ELF context must not carry "
                    "APEX candidates"
                )

            if self.selected_apex_requirement is not None:
                raise ValueError(
                    "BASE Linker/ELF context must not select "
                    "an APEX requirement"
                )

            expected_status = (
                AndroidUniverseRelationshipStatus.RESOLVED
                if len(
                    self.matched_runtime_policies
                ) == 1
                else (
                    AndroidUniverseRelationshipStatus.UNRESOLVED
                    if not self.matched_runtime_policies
                    else AndroidUniverseRelationshipStatus.AMBIGUOUS
                )
            )

        else:
            if (
                self.selected_apex_requirement
                is not None
                and not any(
                    candidate
                    is self.selected_apex_requirement
                    for candidate
                    in self.apex_candidates
                )
            ):
                raise ValueError(
                    "selected_apex_requirement must preserve "
                    "exact APEX candidate identity"
                )

            if (
                len(
                    self.matched_runtime_policies
                ) == 1
                and len(
                    self.apex_candidates
                ) == 1
            ):
                expected_status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                )

                if self.selected_apex_requirement is None:
                    raise ValueError(
                        "resolved APEX Linker/ELF context must "
                        "select its exact APEX requirement"
                    )

            elif (
                len(
                    self.matched_runtime_policies
                ) > 1
                or len(
                    self.apex_candidates
                ) > 1
            ):
                expected_status = (
                    AndroidUniverseRelationshipStatus.AMBIGUOUS
                )

                if self.selected_apex_requirement is not None:
                    raise ValueError(
                        "ambiguous APEX Linker/ELF context must "
                        "not select an APEX requirement"
                    )

            else:
                expected_status = (
                    AndroidUniverseRelationshipStatus.UNRESOLVED
                )

                if self.selected_apex_requirement is not None:
                    raise ValueError(
                        "unresolved APEX Linker/ELF context must "
                        "not select an APEX requirement"
                    )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match Linker/ELF context "
                "resolution"
            )

    @property
    def runtime_policy(
        self,
    ) -> AndroidUniverseLinkerRuntimePolicy | None:
        if len(
            self.matched_runtime_policies
        ) != 1:
            return None

        return self.matched_runtime_policies[
            0
        ]

    @property
    def context_id(
        self,
    ) -> str:
        return (
            "linker-elf-context:"
            f"{self.elf_requirement.requirement_id}"
        )










class AndroidUniverseLinkerApexPublicLibraryStatus(
    StrEnum
):
    """
    Canonical AOSP public-library augmentation state for one exact APEX.

    RESOLVED means one exact runtime-local public-library policy was
    selected and the APEX provideNativeLibs intersection is known.

    ABSENT means Android semantics establish an empty public-library
    population for this APEX. This includes an optional missing public
    policy file and Treble-separated PRODUCT APEXes.

    AMBIGUOUS means more than one canonical runtime-local policy could
    supply the applicable public-library population.

    UNRESOLVED is reserved for genuinely indeterminate deployment,
    Treble applicability, or uninterpreted applicable policy evidence.
    """

    RESOLVED = "resolved"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexPublicLibraryConclusion:
    """
    Derive AOSP ApexInfo.public_libs for one canonical APEX.

    Runtime association preserves every canonical matching Linker runtime
    policy by exact identity. A singular runtime_policy exists only when
    exactly one runtime policy matches the APEX runtime.

    Android linkerconfig intersects an APEX's provideNativeLibs with the
    runtime-local system public-library policy when the APEX is in SYSTEM,
    SYSTEM_EXT, or non-Treble PRODUCT, and with the runtime-local vendor
    public-library policy when the APEX is in VENDOR or ODM.

    Treble-separated PRODUCT APEXes have no public_libs augmentation.

    This conclusion is runtime semantic evidence only. It does not create
    namespaces, links, ELF providers, Reconstruction obligations, source-tree
    ownership, destinations, or materialized files.
    """

    apex_requirement: AndroidUniverseApexRequirement

    matched_runtime_policies: tuple[
        AndroidUniverseLinkerRuntimePolicy,
        ...,
    ]

    policy_candidates: tuple[
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
        ...,
    ]

    selected_public_policy: (
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics
        | None
    )

    public_libraries: tuple[
        str,
        ...,
    ]

    status: AndroidUniverseLinkerApexPublicLibraryStatus

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
            self.matched_runtime_policies,
            tuple,
        ):
            raise TypeError(
                "matched_runtime_policies must be a tuple"
            )

        if not all(
            isinstance(
                policy,
                AndroidUniverseLinkerRuntimePolicy,
            )
            for policy
            in self.matched_runtime_policies
        ):
            raise TypeError(
                "matched_runtime_policies must contain only "
                "AndroidUniverseLinkerRuntimePolicy instances"
            )

        if len(
            {
                id(
                    policy
                )
                for policy
                in self.matched_runtime_policies
            }
        ) != len(
            self.matched_runtime_policies
        ):
            raise ValueError(
                "matched_runtime_policies must preserve unique "
                "canonical runtime-policy identities"
            )

        if not all(
            AndroidUniverseRuntimeContextResolver.same_runtime(
                policy.runtime_context,
                self.apex_requirement.runtime_context,
            )
            for policy
            in self.matched_runtime_policies
        ):
            raise ValueError(
                "matched_runtime_policies must belong to the exact "
                "APEX runtime"
            )

        if not isinstance(
            self.policy_candidates,
            tuple,
        ):
            raise TypeError(
                "policy_candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
            )
            for candidate
            in self.policy_candidates
        ):
            raise TypeError(
                "policy_candidates must contain only "
                "AndroidUniverseLinkerNativeLibraryConfigurationSemantics "
                "instances"
            )

        if not all(
            AndroidUniverseRuntimeContextResolver.same_runtime(
                candidate.runtime_context,
                self.apex_requirement.runtime_context,
            )
            for candidate
            in self.policy_candidates
        ):
            raise ValueError(
                "public-library policy candidates must belong to the "
                "exact APEX runtime"
            )

        if not all(
            candidate.policy_kind
            in {
                AndroidUniverseLinkerNativeLibraryPolicyKind.SYSTEM_PUBLIC,
                AndroidUniverseLinkerNativeLibraryPolicyKind.VENDOR_PUBLIC,
            }
            for candidate
            in self.policy_candidates
        ):
            raise ValueError(
                "public-library policy candidates must be SYSTEM_PUBLIC "
                "or VENDOR_PUBLIC policies"
            )

        if (
            self.selected_public_policy
            is not None
            and not isinstance(
                self.selected_public_policy,
                AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
            )
        ):
            raise TypeError(
                "selected_public_policy has invalid type"
            )

        if (
            self.selected_public_policy
            is not None
            and not any(
                candidate
                is self.selected_public_policy
                for candidate
                in self.policy_candidates
            )
        ):
            raise ValueError(
                "selected_public_policy must preserve exact candidate "
                "identity"
            )

        if not isinstance(
            self.public_libraries,
            tuple,
        ):
            raise TypeError(
                "public_libraries must be a tuple"
            )

        if not all(
            isinstance(
                library_name,
                str,
            )
            and library_name
            for library_name
            in self.public_libraries
        ):
            raise ValueError(
                "public_libraries must contain only non-empty strings"
            )

        if not all(
            library_name
            in self.apex_requirement.provide_native_libs
            for library_name
            in self.public_libraries
        ):
            raise ValueError(
                "public_libraries must be drawn only from the APEX "
                "provideNativeLibs population"
            )

        expected_order = tuple(
            library_name
            for library_name
            in self.apex_requirement.provide_native_libs
            if library_name
            in set(
                self.public_libraries
            )
        )

        if (
            self.public_libraries
            != expected_order
        ):
            raise ValueError(
                "public_libraries must preserve provideNativeLibs order"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerApexPublicLibraryStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerApexPublicLibraryStatus"
            )

        if (
            self.status
            is AndroidUniverseLinkerApexPublicLibraryStatus.RESOLVED
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                != 1
                or len(
                    self.policy_candidates
                )
                != 1
                or self.selected_public_policy
                is None
            ):
                raise ValueError(
                    "RESOLVED public-library conclusion requires one "
                    "runtime policy and one selected public policy"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexPublicLibraryStatus.ABSENT
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                != 1
                or self.policy_candidates
                or self.selected_public_policy
                is not None
                or self.public_libraries
            ):
                raise ValueError(
                    "ABSENT public-library conclusion requires one "
                    "resolved runtime and an empty public-library policy"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexPublicLibraryStatus.AMBIGUOUS
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                <= 1
                and len(
                    self.policy_candidates
                )
                <= 1
            ):
                raise ValueError(
                    "AMBIGUOUS public-library conclusion requires "
                    "multiple runtime policies or public policies"
                )

            if (
                self.selected_public_policy
                is not None
                or self.public_libraries
            ):
                raise ValueError(
                    "AMBIGUOUS public-library conclusion must not "
                    "select a policy or public libraries"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexPublicLibraryStatus.UNRESOLVED
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                > 1
            ):
                raise ValueError(
                    "multiple matching runtime policies must be "
                    "represented as AMBIGUOUS"
                )

            if (
                self.selected_public_policy
                is not None
                or self.public_libraries
            ):
                raise ValueError(
                    "UNRESOLVED public-library conclusion must not "
                    "claim a selected policy or public libraries"
                )

    @property
    def runtime_policy(
        self,
    ) -> AndroidUniverseLinkerRuntimePolicy | None:
        if len(
            self.matched_runtime_policies
        ) != 1:
            return None

        return self.matched_runtime_policies[
            0
        ]

    @property
    def conclusion_id(
        self,
    ) -> str:
        return (
            "linker-apex-public-libraries:"
            f"{self.apex_requirement.requirement_id}"
        )


class AndroidUniverseLinkerApexNamespaceStatus(
    StrEnum
):
    """
    Canonical availability/resolution state for one APEX-local
    linker.config.pb association.

    PRESENT means one exact canonical local policy is selected.

    ABSENT means canonical evidence establishes that this APEX has no
    APEX-local linker.config.pb. Absence is normal and must not be treated
    as unresolved Linker semantics.

    AMBIGUOUS means multiple canonical local-policy candidates remain.

    UNRESOLVED is reserved for a genuinely indeterminate association.
    """

    PRESENT = "present"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexNamespaceInput:
    """
    Canonical APEX-local Linker namespace input for one exact APEX.

    Runtime association preserves every matching canonical Linker runtime
    policy by exact identity. A singular runtime_policy exists only when
    exactly one runtime policy matches.

    APEX-local protobuf association is provenance-based. APEX names, parser
    source names, host paths, partition names, device facts, and version
    knowledge are not identity inputs.

    This is input semantics for later Linker section reconciliation only.
    It does not create namespaces or links and does not resolve ELF
    dependencies.
    """

    apex_requirement: AndroidUniverseApexRequirement

    matched_runtime_policies: tuple[
        AndroidUniverseLinkerRuntimePolicy,
        ...,
    ]

    apex_local_candidates: tuple[
        AndroidUniverseLinkerProtobufConfigurationSemantics,
        ...,
    ]

    selected_apex_local_configuration: (
        AndroidUniverseLinkerProtobufConfigurationSemantics
        | None
    )

    status: AndroidUniverseLinkerApexNamespaceStatus

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
            self.matched_runtime_policies,
            tuple,
        ):
            raise TypeError(
                "matched_runtime_policies must be a tuple"
            )

        if not all(
            isinstance(
                policy,
                AndroidUniverseLinkerRuntimePolicy,
            )
            for policy
            in self.matched_runtime_policies
        ):
            raise TypeError(
                "matched_runtime_policies must contain only "
                "AndroidUniverseLinkerRuntimePolicy instances"
            )

        if len(
            {
                id(
                    policy
                )
                for policy
                in self.matched_runtime_policies
            }
        ) != len(
            self.matched_runtime_policies
        ):
            raise ValueError(
                "matched_runtime_policies must preserve unique "
                "canonical runtime-policy identities"
            )

        if not all(
            AndroidUniverseRuntimeContextResolver.same_runtime(
                policy.runtime_context,
                self.apex_requirement.runtime_context,
            )
            for policy
            in self.matched_runtime_policies
        ):
            raise ValueError(
                "matched_runtime_policies must belong to the exact "
                "APEX runtime"
            )

        if not isinstance(
            self.apex_local_candidates,
            tuple,
        ):
            raise TypeError(
                "apex_local_candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                AndroidUniverseLinkerProtobufConfigurationSemantics,
            )
            for candidate
            in self.apex_local_candidates
        ):
            raise TypeError(
                "apex_local_candidates must contain only "
                "AndroidUniverseLinkerProtobufConfigurationSemantics "
                "instances"
            )

        if not all(
            candidate.applies_apex_local_policy
            for candidate
            in self.apex_local_candidates
        ):
            raise ValueError(
                "apex_local_candidates must contain only APEX-local "
                "protobuf semantics"
            )

        if not all(
            AndroidUniverseRuntimeContextResolver.same_runtime(
                candidate.runtime_context,
                self.apex_requirement.runtime_context,
            )
            for candidate
            in self.apex_local_candidates
        ):
            raise ValueError(
                "APEX-local candidates must belong to the exact "
                "APEX runtime"
            )

        if (
            self.selected_apex_local_configuration
            is not None
            and not isinstance(
                self.selected_apex_local_configuration,
                AndroidUniverseLinkerProtobufConfigurationSemantics,
            )
        ):
            raise TypeError(
                "selected_apex_local_configuration has invalid type"
            )

        if (
            self.selected_apex_local_configuration
            is not None
            and not any(
                candidate
                is self.selected_apex_local_configuration
                for candidate
                in self.apex_local_candidates
            )
        ):
            raise ValueError(
                "selected APEX-local configuration must preserve exact "
                "candidate identity"
            )

        if not isinstance(
            self.status,
            AndroidUniverseLinkerApexNamespaceStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseLinkerApexNamespaceStatus"
            )

        if (
            self.status
            is AndroidUniverseLinkerApexNamespaceStatus.PRESENT
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                != 1
                or len(
                    self.apex_local_candidates
                )
                != 1
                or self.selected_apex_local_configuration
                is None
            ):
                raise ValueError(
                    "PRESENT APEX namespace input requires one runtime "
                    "policy and one selected APEX-local configuration"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexNamespaceStatus.ABSENT
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                != 1
                or self.apex_local_candidates
                or self.selected_apex_local_configuration
                is not None
            ):
                raise ValueError(
                    "ABSENT APEX namespace input requires one resolved "
                    "runtime and no APEX-local policy"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
        ):
            if (
                len(
                    self.matched_runtime_policies
                )
                <= 1
                and len(
                    self.apex_local_candidates
                )
                <= 1
            ):
                raise ValueError(
                    "AMBIGUOUS APEX namespace input requires multiple "
                    "runtime policies or local-policy candidates"
                )

            if (
                self.selected_apex_local_configuration
                is not None
            ):
                raise ValueError(
                    "AMBIGUOUS APEX namespace input must not select "
                    "a local policy"
                )

        elif (
            self.status
            is AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
        ):
            if self.matched_runtime_policies:
                raise ValueError(
                    "UNRESOLVED APEX namespace runtime association must "
                    "not claim a resolved runtime policy"
                )

            if (
                self.selected_apex_local_configuration
                is not None
            ):
                raise ValueError(
                    "UNRESOLVED APEX namespace input must not select "
                    "a local policy"
                )

    @property
    def runtime_policy(
        self,
    ) -> AndroidUniverseLinkerRuntimePolicy | None:
        if len(
            self.matched_runtime_policies
        ) != 1:
            return None

        return self.matched_runtime_policies[
            0
        ]

    @property
    def input_id(
        self,
    ) -> str:
        return (
            "linker-apex-namespace-input:"
            f"{self.apex_requirement.requirement_id}"
        )












class AndroidUniverseLinkerApexNativeLibraryProviderKind(
    StrEnum
):
    """
    Canonical provider category selected by Linker/APEX native-library
    semantic reconciliation.

    This describes runtime semantics only. It does not identify a physical
    ELF artifact or imply Reconstruction work.
    """

    CONTEXT = "context"
    APEX = "apex"
    LLNDK = "llndk"
    ALIAS = "alias"
    NONE = "none"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexNativeLibraryApexProvider:
    """
    Exact provideNativeLibs occurrence from one canonical APEX requirement.
    """

    apex_requirement: AndroidUniverseApexRequirement
    provider_index: int
    library_name: str

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

        if (
            not isinstance(
                self.provider_index,
                int,
            )
            or self.provider_index < 0
        ):
            raise ValueError(
                "provider_index must be a non-negative integer"
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

        if (
            self.provider_index
            >= len(
                self.apex_requirement.provide_native_libs
            )
            or self.apex_requirement.provide_native_libs[
                self.provider_index
            ]
            != self.library_name
        ):
            raise ValueError(
                "APEX provider must preserve exact provideNativeLibs "
                "index and value"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexNativeLibraryAliasProvider:
    """
    Exact Linker namespace target selected for one special provider alias.

    Namespace identity is preserved together with its exact containing
    text configuration and section. This is runtime-semantic evidence only.
    """

    alias_name: str

    text_configuration: (
        AndroidUniverseLinkerTextConfigurationSemantics
    )

    section: AndroidUniverseLinkerSection

    target_namespace: AndroidUniverseLinkerNamespace

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.alias_name,
                str,
            )
            or not self.alias_name
        ):
            raise ValueError(
                "alias_name must be a non-empty string"
            )

        if not isinstance(
            self.text_configuration,
            AndroidUniverseLinkerTextConfigurationSemantics,
        ):
            raise TypeError(
                "text_configuration must be an "
                "AndroidUniverseLinkerTextConfigurationSemantics"
            )

        if not isinstance(
            self.section,
            AndroidUniverseLinkerSection,
        ):
            raise TypeError(
                "section must be an AndroidUniverseLinkerSection"
            )

        if not isinstance(
            self.target_namespace,
            AndroidUniverseLinkerNamespace,
        ):
            raise TypeError(
                "target_namespace must be an AndroidUniverseLinkerNamespace"
            )

        if not any(
            candidate
            is self.section
            for candidate
            in self.text_configuration.sections
        ):
            raise ValueError(
                "section must preserve exact containing configuration "
                "identity"
            )

        if not any(
            candidate
            is self.target_namespace
            for candidate
            in self.section.namespaces
        ):
            raise ValueError(
                "target_namespace must preserve exact containing section "
                "identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerApexNativeLibraryConclusion:
    """
    Runtime-semantic conclusion for one exact APEX requireNativeLibs
    occurrence.

    Provider precedence represented here is limited to already-established
    applicable Linker context providers followed by same-runtime APEX
    manifest providers.

    Alias semantics and ELF artifact resolution remain later semantic layers.
    Reconstruction ownership, destination selection, and materialization are
    explicitly out of scope.
    """

    context_applicability: (
        AndroidUniverseLinkerApexContextApplicability
    )

    requirement_index: int
    library_name: str

    context_provider_candidates: tuple[
        AndroidUniverseLinkerProtobufLibraryPolicy,
        ...,
    ]

    apex_provider_candidates: tuple[
        AndroidUniverseLinkerApexNativeLibraryApexProvider,
        ...,
    ]

    llndk_provider_candidates: tuple[
        AndroidUniverseLinkerNativeLibraryDeclaration,
        ...,
    ]

    alias_provider_candidates: tuple[
        AndroidUniverseLinkerApexNativeLibraryAliasProvider,
        ...,
    ]

    provider_kind: (
        AndroidUniverseLinkerApexNativeLibraryProviderKind
    )

    selected_context_provider: (
        AndroidUniverseLinkerProtobufLibraryPolicy
        | None
    )

    selected_apex_provider: (
        AndroidUniverseLinkerApexNativeLibraryApexProvider
        | None
    )

    selected_llndk_provider: (
        AndroidUniverseLinkerNativeLibraryDeclaration
        | None
    )

    selected_alias_provider: (
        AndroidUniverseLinkerApexNativeLibraryAliasProvider
        | None
    )

    status: AndroidUniverseRelationshipStatus

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.context_applicability,
            AndroidUniverseLinkerApexContextApplicability,
        ):
            raise TypeError(
                "context_applicability must be an "
                "AndroidUniverseLinkerApexContextApplicability"
            )

        if (
            not isinstance(
                self.requirement_index,
                int,
            )
            or self.requirement_index < 0
        ):
            raise ValueError(
                "requirement_index must be a non-negative integer"
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

        apex = (
            self.context_applicability
            .membership_relationship
            .apex_requirement
        )

        if (
            self.requirement_index
            >= len(
                apex.require_native_libs
            )
            or apex.require_native_libs[
                self.requirement_index
            ]
            != self.library_name
        ):
            raise ValueError(
                "native-library conclusion must preserve exact "
                "requireNativeLibs index and value"
            )

        if not isinstance(
            self.context_provider_candidates,
            tuple,
        ):
            raise TypeError(
                "context_provider_candidates must be a tuple"
            )

        if not all(
            isinstance(
                provider,
                AndroidUniverseLinkerProtobufLibraryPolicy,
            )
            for provider
            in self.context_provider_candidates
        ):
            raise TypeError(
                "context_provider_candidates contains an invalid "
                "provider object"
            )

        if not isinstance(
            self.apex_provider_candidates,
            tuple,
        ):
            raise TypeError(
                "apex_provider_candidates must be a tuple"
            )

        if not all(
            isinstance(
                provider,
                AndroidUniverseLinkerApexNativeLibraryApexProvider,
            )
            for provider
            in self.apex_provider_candidates
        ):
            raise TypeError(
                "apex_provider_candidates contains an invalid "
                "provider object"
            )

        if not isinstance(
            self.llndk_provider_candidates,
            tuple,
        ):
            raise TypeError(
                "llndk_provider_candidates must be a tuple"
            )

        if not all(
            isinstance(
                provider,
                AndroidUniverseLinkerNativeLibraryDeclaration,
            )
            for provider
            in self.llndk_provider_candidates
        ):
            raise TypeError(
                "llndk_provider_candidates contains an invalid "
                "provider object"
            )

        if not isinstance(
            self.alias_provider_candidates,
            tuple,
        ):
            raise TypeError(
                "alias_provider_candidates must be a tuple"
            )

        if not all(
            isinstance(
                provider,
                AndroidUniverseLinkerApexNativeLibraryAliasProvider,
            )
            for provider
            in self.alias_provider_candidates
        ):
            raise TypeError(
                "alias_provider_candidates contains an invalid "
                "provider object"
            )

        if not isinstance(
            self.provider_kind,
            AndroidUniverseLinkerApexNativeLibraryProviderKind,
        ):
            raise TypeError(
                "provider_kind must be an "
                "AndroidUniverseLinkerApexNativeLibraryProviderKind"
            )

        if not isinstance(
            self.status,
            AndroidUniverseRelationshipStatus,
        ):
            raise TypeError(
                "status must be an AndroidUniverseRelationshipStatus"
            )

        if (
            self.selected_context_provider is not None
            and not isinstance(
                self.selected_context_provider,
                AndroidUniverseLinkerProtobufLibraryPolicy,
            )
        ):
            raise TypeError(
                "selected_context_provider has invalid type"
            )

        if (
            self.selected_apex_provider is not None
            and not isinstance(
                self.selected_apex_provider,
                AndroidUniverseLinkerApexNativeLibraryApexProvider,
            )
        ):
            raise TypeError(
                "selected_apex_provider has invalid type"
            )

        if (
            self.selected_llndk_provider is not None
            and not isinstance(
                self.selected_llndk_provider,
                AndroidUniverseLinkerNativeLibraryDeclaration,
            )
        ):
            raise TypeError(
                "selected_llndk_provider has invalid type"
            )

        if (
            self.selected_alias_provider is not None
            and not isinstance(
                self.selected_alias_provider,
                AndroidUniverseLinkerApexNativeLibraryAliasProvider,
            )
        ):
            raise TypeError(
                "selected_alias_provider has invalid type"
            )

        if (
            self.provider_kind
            is AndroidUniverseLinkerApexNativeLibraryProviderKind.CONTEXT
        ):
            if (
                self.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
                or self.selected_context_provider is None
                or self.selected_apex_provider is not None
                or self.selected_llndk_provider is not None
                or self.selected_alias_provider is not None
            ):
                raise ValueError(
                    "CONTEXT provider conclusion is inconsistent"
                )

            if not any(
                candidate
                is self.selected_context_provider
                for candidate
                in self.context_provider_candidates
            ):
                raise ValueError(
                    "selected context provider must preserve candidate "
                    "identity"
                )

        elif (
            self.provider_kind
            is AndroidUniverseLinkerApexNativeLibraryProviderKind.APEX
        ):
            if (
                self.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
                or self.selected_context_provider is not None
                or self.selected_apex_provider is None
                or self.selected_llndk_provider is not None
                or self.selected_alias_provider is not None
            ):
                raise ValueError(
                    "APEX provider conclusion is inconsistent"
                )

            if not any(
                candidate
                is self.selected_apex_provider
                for candidate
                in self.apex_provider_candidates
            ):
                raise ValueError(
                    "selected APEX provider must preserve candidate "
                    "identity"
                )

        elif (
            self.provider_kind
            is AndroidUniverseLinkerApexNativeLibraryProviderKind.LLNDK
        ):
            if (
                self.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
                or self.selected_context_provider is not None
                or self.selected_apex_provider is not None
                or self.selected_llndk_provider is None
                or self.selected_alias_provider is not None
            ):
                raise ValueError(
                    "LLNDK provider conclusion is inconsistent"
                )

            if not any(
                candidate
                is self.selected_llndk_provider
                for candidate
                in self.llndk_provider_candidates
            ):
                raise ValueError(
                    "selected LLNDK provider must preserve candidate "
                    "identity"
                )

        elif (
            self.provider_kind
            is AndroidUniverseLinkerApexNativeLibraryProviderKind.ALIAS
        ):
            if (
                self.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
                or self.selected_context_provider is not None
                or self.selected_apex_provider is not None
                or self.selected_llndk_provider is not None
                or self.selected_alias_provider is None
            ):
                raise ValueError(
                    "ALIAS provider conclusion is inconsistent"
                )

            if not any(
                candidate
                is self.selected_alias_provider
                for candidate
                in self.alias_provider_candidates
            ):
                raise ValueError(
                    "selected alias provider must preserve candidate "
                    "identity"
                )

        else:
            if (
                self.selected_context_provider is not None
                or self.selected_apex_provider is not None
                or self.selected_llndk_provider is not None
                or self.selected_alias_provider is not None
            ):
                raise ValueError(
                    "NONE provider conclusion must not select a provider"
                )

            if (
                self.status
                is AndroidUniverseRelationshipStatus.RESOLVED
            ):
                raise ValueError(
                    "NONE provider conclusion cannot be resolved"
                )

    @property
    def conclusion_id(
        self,
    ) -> str:
        return (
            "linker-apex-native-library:"
            f"{self.context_applicability.applicability_id}:"
            f"{self.requirement_index}:"
            f"{self.library_name}"
        )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApkVintfImplementationEvidence:
    """
    One exact concrete DEX class whose direct superclass is the generated
    Binder Stub class retained by structural provider evidence.

    This is a literal class-graph observation. It does not assert that the
    class is instantiated or registered at runtime.
    """

    dex: ParsedAndroidDex
    implementation_class: AndroidDexClass

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.dex,
            ParsedAndroidDex,
        ):
            raise TypeError(
                "dex must be a ParsedAndroidDex"
            )

        if not isinstance(
            self.implementation_class,
            AndroidDexClass,
        ):
            raise TypeError(
                "implementation_class must be an AndroidDexClass"
            )

        if not any(
            candidate is self.implementation_class
            for candidate
            in self.dex.classes
        ):
            raise ValueError(
                "implementation_class must preserve exact "
                "canonical DEX class identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApkVintfStructuralProviderEvidence:
    """
    Exact structural evidence that one APK contains a Binder implementation
    for one VINTF AIDL interface.

    The evidence consists of:
      * the exact canonical DEX,
      * the exact AIDL interface type,
      * the exact generated Binder $Stub class implementing that interface,
      * one or more exact concrete classes directly extending that Stub.

    Universe assigns no runtime-registration conclusion from this evidence.
    """

    dex: ParsedAndroidDex
    interface_type: AndroidDexType
    stub_class: AndroidDexClass

    implementations: tuple[
        AndroidUniverseApkVintfImplementationEvidence,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.dex,
            ParsedAndroidDex,
        ):
            raise TypeError(
                "dex must be a ParsedAndroidDex"
            )

        if not isinstance(
            self.interface_type,
            AndroidDexType,
        ):
            raise TypeError(
                "interface_type must be an AndroidDexType"
            )

        if not isinstance(
            self.stub_class,
            AndroidDexClass,
        ):
            raise TypeError(
                "stub_class must be an AndroidDexClass"
            )

        if not any(
            candidate is self.interface_type
            for candidate
            in self.dex.types
        ):
            raise ValueError(
                "interface_type must preserve exact "
                "canonical DEX type identity"
            )

        if not any(
            candidate is self.stub_class
            for candidate
            in self.dex.classes
        ):
            raise ValueError(
                "stub_class must preserve exact "
                "canonical DEX class identity"
            )

        if not any(
            candidate is self.interface_type
            for candidate
            in self.stub_class.interface_types
        ):
            raise ValueError(
                "generated Binder Stub class must implement "
                "the exact canonical interface type"
            )

        expected_stub_descriptor = (
            self.interface_type.descriptor.value[
                :-1
            ]
            + "$Stub;"
        )

        if (
            self.stub_class
            .class_type
            .descriptor
            .value
            != expected_stub_descriptor
        ):
            raise ValueError(
                "Binder Stub class descriptor must be derived "
                "exactly from the canonical interface descriptor"
            )

        if not isinstance(
            self.implementations,
            tuple,
        ):
            raise TypeError(
                "implementations must be a tuple"
            )

        if not self.implementations:
            raise ValueError(
                "structural provider evidence requires at least "
                "one concrete Binder Stub subclass"
            )

        for implementation in self.implementations:
            if not isinstance(
                implementation,
                AndroidUniverseApkVintfImplementationEvidence,
            ):
                raise TypeError(
                    "implementations must contain only "
                    "AndroidUniverseApkVintfImplementationEvidence"
                )

            implementation_class = (
                implementation
                .implementation_class
            )

            if (
                implementation_class.access_flags
                & (
                    0x0200  # ACC_INTERFACE
                    | 0x0400  # ACC_ABSTRACT
                )
            ):
                raise ValueError(
                    "structural provider implementation must be "
                    "a concrete DEX class"
                )

            superclass = (
                implementation_class
                .superclass_type
            )

            if superclass is None:
                raise ValueError(
                    "structural provider implementation must "
                    "have the Binder Stub as its superclass"
                )

            if (
                superclass.descriptor.value
                != expected_stub_descriptor
            ):
                raise ValueError(
                    "structural provider implementation must "
                    "directly extend the canonical Binder Stub"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApkVintfStructuralProviderRelationship:
    """
    Relate one canonical APK package to one exact VINTF AIDL interface when
    the APK's canonical DEX graph structurally contains the generated Binder
    Stub and at least one concrete direct Stub subclass.

    RESOLVED means this APK is the sole canonical APK package with structural
    provider evidence for the VINTF interface.

    AMBIGUOUS means multiple canonical APK packages independently contain
    qualifying structural provider evidence. The relationship is retained
    but must not be treated as exclusive provider ownership.

    This relationship does not claim that Android runtime service registration
    has been observed.
    """

    kind: AndroidUniverseRelationshipKind
    status: AndroidUniverseRelationshipStatus

    apk_package: AndroidUniverseApkPackageRequirement

    canonical_name: str

    provider_evidence: tuple[
        AndroidUniverseApkVintfStructuralProviderEvidence,
        ...,
    ]

    vintf_evidence: tuple[
        AndroidUniverseVintfInterfaceEvidence,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.kind
            is not AndroidUniverseRelationshipKind
            .APK_VINTF_STRUCTURAL_PROVIDER
        ):
            raise ValueError(
                "invalid relationship kind"
            )

        if self.status not in {
            AndroidUniverseRelationshipStatus.RESOLVED,
            AndroidUniverseRelationshipStatus.AMBIGUOUS,
        }:
            raise ValueError(
                "APK/VINTF structural provider relationship must "
                "be resolved or ambiguous"
            )

        if not isinstance(
            self.apk_package,
            AndroidUniverseApkPackageRequirement,
        ):
            raise TypeError(
                "apk_package must be an "
                "AndroidUniverseApkPackageRequirement"
            )

        if (
            not isinstance(
                self.canonical_name,
                str,
            )
            or not self.canonical_name
            or "/" not in self.canonical_name
        ):
            raise ValueError(
                "canonical_name must be a non-empty canonical "
                "AIDL VINTF service identity"
            )

        if not isinstance(
            self.provider_evidence,
            tuple,
        ):
            raise TypeError(
                "provider_evidence must be a tuple"
            )

        if not self.provider_evidence:
            raise ValueError(
                "provider_evidence must not be empty"
            )

        if not isinstance(
            self.vintf_evidence,
            tuple,
        ):
            raise TypeError(
                "vintf_evidence must be a tuple"
            )

        if not self.vintf_evidence:
            raise ValueError(
                "vintf_evidence must not be empty"
            )

        canonical_dex_ids = {
            id(
                dex
            )
            for dex
            in self.apk_package.source.dex_files
        }

        service_identity = (
            self.canonical_name.split(
                "/",
                1,
            )[0]
        )

        expected_descriptor = (
            "L"
            + service_identity.replace(
                ".",
                "/",
            )
            + ";"
        )

        for evidence in self.provider_evidence:
            if not isinstance(
                evidence,
                AndroidUniverseApkVintfStructuralProviderEvidence,
            ):
                raise TypeError(
                    "provider_evidence must contain only "
                    "AndroidUniverseApkVintfStructuralProviderEvidence"
                )

            if id(
                evidence.dex
            ) not in canonical_dex_ids:
                raise ValueError(
                    "provider evidence DEX must belong to the exact "
                    "canonical APK package"
                )

            if (
                evidence
                .interface_type
                .descriptor
                .value
                != expected_descriptor
            ):
                raise ValueError(
                    "provider evidence interface descriptor must "
                    "match canonical VINTF AIDL identity"
                )

            for implementation in evidence.implementations:
                if id(
                    implementation.dex
                ) not in canonical_dex_ids:
                    raise ValueError(
                        "implementation evidence DEX must belong "
                        "to the exact canonical APK package"
                    )

        for evidence in self.vintf_evidence:
            if not isinstance(
                evidence,
                AndroidUniverseVintfInterfaceEvidence,
            ):
                raise TypeError(
                    "vintf_evidence must contain only "
                    "AndroidUniverseVintfInterfaceEvidence"
                )

            if (
                evidence.canonical_name
                != self.canonical_name
            ):
                raise ValueError(
                    "VINTF evidence canonical identity must match "
                    "relationship canonical_name"
                )

    @property
    def relationship_id(
        self,
    ) -> str:
        return (
            "relationship:apk-vintf-structural-provider:"
            f"{self.apk_package.requirement_id}:"
            f"{self.canonical_name}"
        )


AndroidUniverseCrossFamilyRelationship = (
    AndroidUniverseInitClassControlRelationship
    | AndroidUniverseInitServiceControlRelationship
    | AndroidUniverseInitOnRestartClassControlRelationship
    | AndroidUniverseInitOnRestartServiceControlRelationship
    | AndroidUniverseInitOnRestartPropertyCommandRelationship
    | AndroidUniverseInitEventTriggerRelationship
    | AndroidUniverseInitPropertyCommandRelationship
    | AndroidUniverseInitPropertyTriggerRelationship
    | AndroidUniverseInitExecutableArtifactRelationship
    | AndroidUniverseInitExecutableSelinuxRelationship
    | AndroidUniverseInitSeclabelSelinuxRelationship
    | AndroidUniverseInitInterfaceVintfRelationship
    | AndroidUniverseApkVintfStructuralProviderRelationship
    | AndroidUniversePropertySelinuxRelationship
    | AndroidUniverseFirstStageKernelModuleLoadingRelationship
    | AndroidUniverseArtRuntimeClasspathRelationship
    | AndroidUniverseLinkerApexRelationship
)


ANDROID_UNIVERSE_CROSS_FAMILY_RELATIONSHIP_TYPES = (
    AndroidUniverseInitClassControlRelationship,
    AndroidUniverseInitServiceControlRelationship,
    AndroidUniverseInitOnRestartClassControlRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
    AndroidUniverseInitOnRestartPropertyCommandRelationship,
    AndroidUniverseInitEventTriggerRelationship,
    AndroidUniverseInitPropertyCommandRelationship,
    AndroidUniverseInitPropertyTriggerRelationship,
    AndroidUniverseInitExecutableArtifactRelationship,
    AndroidUniverseInitExecutableSelinuxRelationship,
    AndroidUniverseInitSeclabelSelinuxRelationship,
    AndroidUniverseInitInterfaceVintfRelationship,
    AndroidUniverseApkVintfStructuralProviderRelationship,
    AndroidUniversePropertySelinuxRelationship,
    AndroidUniverseFirstStageKernelModuleLoadingRelationship,
    AndroidUniverseArtRuntimeClasspathRelationship,
    AndroidUniverseLinkerApexRelationship,
)
