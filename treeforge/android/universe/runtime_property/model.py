from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidPropertyFile,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)
from treeforge.android.parsing.properties import (
    AndroidPropertyDeclaration,
)
from treeforge.android.parsing.shell_script import (
    AndroidShellCommandObservation,
    ParsedAndroidShellScript,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.action_command import (
    AndroidUniverseInitActionCommandRequirement,
)
from treeforge.android.universe.init.action_command.semantics import (
    AndroidUniverseInitActionCommandKeyValueSemantics,
)
from treeforge.android.universe.init.action_trigger.model import (
    AndroidUniverseInitActionPropertyTriggerClause,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.onrestart import (
    AndroidUniverseInitOnRestartCommand,
)
from treeforge.android.universe.runtime_property.context import (
    AndroidUniversePropertyContextMatchKind,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextRequirement,
)


class AndroidUniverseRuntimePropertyCommandKind(
    StrEnum
):
    SETPROP = "setprop"
    WAIT_FOR_PROP = "wait_for_prop"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyBootExportObservation:
    """
    One canonical AOSP boot-property export.

    The source argument is the exact Universe-owned androidboot.* boot
    input, either a kernel command-line argument or vendor_boot bootconfig
    declaration. The target property is the runtime ro.boot.* identity
    exported by Android init from that canonical boot input.
    """

    boot_requirement: object
    argument: object
    property_key: str
    property_value: str

    def __post_init__(self) -> None:
        if not isinstance(self.property_key, str) or not self.property_key:
            raise ValueError(
                "property_key must be a non-empty string"
            )

        if not isinstance(self.property_value, str):
            raise TypeError(
                "property_value must be a string"
            )

        if not self.property_value:
            raise ValueError(
                "property_value must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyDeclarationObservation:
    """
    One exact parsed property declaration contributing to the runtime namespace.

    This deliberately differs from AndroidUniversePropertyEvidence: every
    parsed property declaration is eligible here, not only declarations that
    TreeForge currently maps to a device/build semantic fact.
    """

    parsed_source: ParsedAndroidPropertyFile
    declaration: AndroidPropertyDeclaration
    model_source: AndroidModelSource

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.parsed_source,
            ParsedAndroidPropertyFile,
        ):
            raise TypeError(
                "parsed_source must be a ParsedAndroidPropertyFile"
            )

        if not isinstance(
            self.declaration,
            AndroidPropertyDeclaration,
        ):
            raise TypeError(
                "declaration must be an AndroidPropertyDeclaration"
            )

        if not isinstance(
            self.model_source,
            AndroidModelSource,
        ):
            raise TypeError(
                "model_source must be an AndroidModelSource"
            )

        if (
            self.parsed_source.source_path
            != self.model_source.host_path
        ):
            raise ValueError(
                "parsed_source must match model_source host provenance"
            )

        if self.declaration not in self.parsed_source.declarations:
            raise ValueError(
                "declaration must belong to parsed_source"
            )

    @property
    def property_key(
        self,
    ) -> str:
        return self.declaration.key


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyShellSetpropObservation:
    """
    One canonical lexical ``setprop`` producer in a parsed shell script.

    Parsing owns the exact command syntax. Universe adds only the Android
    runtime-property relationship. This observation does not claim that the
    script executes on every boot or that a dynamic shell expression has
    a statically known value.
    """

    shell_script: ParsedAndroidShellScript
    command: AndroidShellCommandObservation
    property_key: str
    property_value: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.shell_script,
            ParsedAndroidShellScript,
        ):
            raise TypeError(
                "shell_script must be a ParsedAndroidShellScript"
            )

        if not isinstance(
            self.command,
            AndroidShellCommandObservation,
        ):
            raise TypeError(
                "command must be an AndroidShellCommandObservation"
            )

        if not any(
            candidate is self.command
            for candidate
            in self.shell_script.command_observations
        ):
            raise ValueError(
                "command must preserve exact Parsed shell-script identity"
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

        if (
            self.property_value is not None
            and not isinstance(
                self.property_value,
                str,
            )
        ):
            raise TypeError(
                "property_value must be a string or None"
            )

        resolved = self.command.resolved_argv

        if len(
            resolved
        ) not in {
            2,
            3,
        }:
            raise ValueError(
                "shell setprop observation requires exactly a property "
                "key and optional value"
            )

        command_name = (
            resolved[0]
            if resolved[0] is not None
            else self.command.argv[0]
        )

        if (
            command_name.rsplit(
                "/",
                1,
            )[-1]
            != "setprop"
        ):
            raise ValueError(
                "shell runtime-property observation requires setprop"
            )

        if resolved[1] != self.property_key:
            raise ValueError(
                "shell setprop observation property key mismatch"
            )

        expected_value = (
            resolved[2]
            if len(
                resolved
            )
            == 3
            else None
        )

        if expected_value != self.property_value:
            raise ValueError(
                "shell setprop observation property value mismatch"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyActionCommandObservation:
    """
    One INIT action setprop producer or wait_for_prop consumer.
    """

    kind: AndroidUniverseRuntimePropertyCommandKind
    init_action: AndroidUniverseInitActionRequirement
    command_requirement: AndroidUniverseInitActionCommandRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidUniverseRuntimePropertyCommandKind,
        ):
            raise TypeError(
                "kind must be an AndroidUniverseRuntimePropertyCommandKind"
            )

        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an AndroidUniverseInitActionRequirement"
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

        semantics = self.command_requirement.semantics

        if not isinstance(
            semantics,
            AndroidUniverseInitActionCommandKeyValueSemantics,
        ):
            raise TypeError(
                "runtime property command requires key/value semantics"
            )

        if semantics.keyword != self.kind.value:
            raise ValueError(
                "runtime property command kind must match command semantics"
            )

    @property
    def property_key(
        self,
    ) -> str:
        return self.command_requirement.semantics.key

    @property
    def property_value(
        self,
    ) -> str:
        return self.command_requirement.semantics.value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyOnRestartObservation:
    """
    One service-owned onrestart setprop producer.
    """

    init_service: AndroidUniverseInitServiceRequirement
    onrestart_command: AndroidUniverseInitOnRestartCommand

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.init_service,
            AndroidUniverseInitServiceRequirement,
        ):
            raise TypeError(
                "init_service must be an AndroidUniverseInitServiceRequirement"
            )

        if not isinstance(
            self.onrestart_command,
            AndroidUniverseInitOnRestartCommand,
        ):
            raise TypeError(
                "onrestart_command must be an AndroidUniverseInitOnRestartCommand"
            )

        if (
            self.onrestart_command
            not in self.init_service.semantics.onrestart_commands
        ):
            raise ValueError(
                "onrestart_command must belong to init_service"
            )

        semantics = self.onrestart_command.semantics

        if not isinstance(
            semantics,
            AndroidUniverseInitActionCommandKeyValueSemantics,
        ):
            raise TypeError(
                "onrestart runtime property observation requires "
                "key/value semantics"
            )

        if semantics.keyword != "setprop":
            raise ValueError(
                "onrestart runtime property observation requires setprop"
            )

    @property
    def property_key(
        self,
    ) -> str:
        return self.onrestart_command.semantics.key

    @property
    def property_value(
        self,
    ) -> str:
        return self.onrestart_command.semantics.value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyTriggerObservation:
    """
    One INIT property-trigger consumer.
    """

    init_action: AndroidUniverseInitActionRequirement
    clause: AndroidUniverseInitActionPropertyTriggerClause

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.init_action,
            AndroidUniverseInitActionRequirement,
        ):
            raise TypeError(
                "init_action must be an AndroidUniverseInitActionRequirement"
            )

        if not isinstance(
            self.clause,
            AndroidUniverseInitActionPropertyTriggerClause,
        ):
            raise TypeError(
                "clause must be an "
                "AndroidUniverseInitActionPropertyTriggerClause"
            )

        if self.clause not in self.init_action.trigger_semantics.property_clauses:
            raise ValueError(
                "clause must belong to init_action trigger semantics"
            )

    @property
    def property_key(
        self,
    ) -> str:
        return self.clause.name

    @property
    def property_value(
        self,
    ) -> str:
        return self.clause.value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRuntimePropertyRequirement:
    """
    Canonical concrete runtime-property requirement.

    A requirement represents namespace identity, not one global runtime value.
    Runtime values are state-dependent and therefore remain attached to their
    individual producer/consumer observations.
    """

    property_key: str

    declaration_observations: tuple[
        AndroidUniverseRuntimePropertyDeclarationObservation,
        ...,
    ] = ()

    boot_export_observations: tuple[
        AndroidUniverseRuntimePropertyBootExportObservation,
        ...,
    ] = ()

    shell_setprop_observations: tuple[
        AndroidUniverseRuntimePropertyShellSetpropObservation,
        ...,
    ] = ()

    action_command_observations: tuple[
        AndroidUniverseRuntimePropertyActionCommandObservation,
        ...,
    ] = ()

    onrestart_observations: tuple[
        AndroidUniverseRuntimePropertyOnRestartObservation,
        ...,
    ] = ()

    trigger_observations: tuple[
        AndroidUniverseRuntimePropertyTriggerObservation,
        ...,
    ] = ()

    context_requirements: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ] = ()

    context_match_kind: (
        AndroidUniversePropertyContextMatchKind
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.property_key,
            str,
        ) or not self.property_key:
            raise ValueError(
                "property_key must be a non-empty string"
            )

        collections = (
            (
                self.declaration_observations,
                AndroidUniverseRuntimePropertyDeclarationObservation,
                "declaration_observations",
            ),
            (
                self.boot_export_observations,
                AndroidUniverseRuntimePropertyBootExportObservation,
                "boot_export_observations",
            ),
            (
                self.shell_setprop_observations,
                AndroidUniverseRuntimePropertyShellSetpropObservation,
                "shell_setprop_observations",
            ),
            (
                self.action_command_observations,
                AndroidUniverseRuntimePropertyActionCommandObservation,
                "action_command_observations",
            ),
            (
                self.onrestart_observations,
                AndroidUniverseRuntimePropertyOnRestartObservation,
                "onrestart_observations",
            ),
            (
                self.trigger_observations,
                AndroidUniverseRuntimePropertyTriggerObservation,
                "trigger_observations",
            ),
            (
                self.context_requirements,
                AndroidUniverseSelinuxContextRequirement,
                "context_requirements",
            ),
        )

        for values, expected_type, name in collections:
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value in values
            ):
                raise TypeError(
                    f"{name} contains unsupported values"
                )

        observations = (
            *self.declaration_observations,
            *self.boot_export_observations,
            *self.shell_setprop_observations,
            *self.action_command_observations,
            *self.onrestart_observations,
            *self.trigger_observations,
        )

        if any(
            observation.property_key != self.property_key
            for observation in observations
        ):
            raise ValueError(
                "all runtime-property observations must match property_key"
            )

        if (
            self.context_match_kind is None
            and self.context_requirements
        ):
            raise ValueError(
                "context_match_kind is required when contexts are present"
            )

        if (
            self.context_match_kind is not None
            and not self.context_requirements
        ):
            raise ValueError(
                "context_match_kind requires context evidence"
            )

    @property
    def setprop_observations(
        self,
    ) -> tuple[
        AndroidUniverseRuntimePropertyActionCommandObservation,
        ...,
    ]:
        return tuple(
            observation
            for observation
            in self.action_command_observations
            if (
                observation.kind
                is AndroidUniverseRuntimePropertyCommandKind.SETPROP
            )
        )

    @property
    def wait_for_prop_observations(
        self,
    ) -> tuple[
        AndroidUniverseRuntimePropertyActionCommandObservation,
        ...,
    ]:
        return tuple(
            observation
            for observation
            in self.action_command_observations
            if (
                observation.kind
                is AndroidUniverseRuntimePropertyCommandKind.WAIT_FOR_PROP
            )
        )

    @property
    def producer_count(
        self,
    ) -> int:
        return (
            len(self.declaration_observations)
            + len(self.boot_export_observations)
            + len(self.shell_setprop_observations)
            + len(self.setprop_observations)
            + len(self.onrestart_observations)
        )

    @property
    def consumer_count(
        self,
    ) -> int:
        return (
            len(self.wait_for_prop_observations)
            + len(self.trigger_observations)
        )

    @property
    def has_static_declaration(
        self,
    ) -> bool:
        return bool(
            self.declaration_observations
        )

    @property
    def has_runtime_producer(
        self,
    ) -> bool:
        return bool(
            self.boot_export_observations
            or self.shell_setprop_observations
            or self.setprop_observations
            or self.onrestart_observations
        )

    @property
    def has_consumer(
        self,
    ) -> bool:
        return self.consumer_count > 0

    @property
    def has_property_context(
        self,
    ) -> bool:
        return bool(
            self.context_requirements
        )
