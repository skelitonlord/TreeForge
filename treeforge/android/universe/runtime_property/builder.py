from __future__ import annotations

from collections import defaultdict

from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.shell_script import (
    AndroidShellScriptParsingResult,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.action_command.semantics import (
    AndroidUniverseInitActionCommandKeyValueSemantics,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.runtime_property.context import (
    AndroidUniversePropertyContextMatchKind,
    android_property_context_mode,
    resolve_android_property_contexts,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyActionCommandObservation,
    AndroidUniverseRuntimePropertyBootExportObservation,
    AndroidUniverseRuntimePropertyCommandKind,
    AndroidUniverseRuntimePropertyDeclarationObservation,
    AndroidUniverseRuntimePropertyOnRestartObservation,
    AndroidUniverseRuntimePropertyRequirement,
    AndroidUniverseRuntimePropertyShellSetpropObservation,
    AndroidUniverseRuntimePropertyTriggerObservation,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextKind,
)
from treeforge.android.universe.selinux.policy_graph import (
    AndroidUniverseSelinuxPolicyGraph,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)


class AndroidUniverseRuntimePropertyBuilder:
    """
    Build the canonical concrete ROOT runtime-property namespace.

    The namespace combines root-runtime property declarations with ROOT INIT
    producers/consumers, ROOT shell producers, boot exports, and ROOT SELinux
    property_contexts evidence.

    Canonical observations belonging to nested Android runtimes remain
    preserved by their owning Parsing and Universe families; they do not
    establish reconstruction obligations in the selected ROOT namespace.
    """

    def build(
        self,
        *,
        parsing: AndroidFilesystemParsingResult,
        source_inventory: AndroidModelSourceInventory,
        init_services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        init_actions: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        boot_requirements: tuple[
            object,
            ...,
        ],
        selinux_graph: AndroidUniverseSelinuxPolicyGraph,
        shell_scripts: AndroidShellScriptParsingResult | None = None,
    ) -> tuple[
        AndroidUniverseRuntimePropertyRequirement,
        ...,
    ]:
        if not isinstance(
            parsing,
            AndroidFilesystemParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidFilesystemParsingResult"
            )

        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an AndroidModelSourceInventory"
            )

        if not isinstance(
            init_services,
            tuple,
        ):
            raise TypeError(
                "init_services must be a tuple"
            )

        if not isinstance(
            init_actions,
            tuple,
        ):
            raise TypeError(
                "init_actions must be a tuple"
            )

        if not isinstance(
            boot_requirements,
            tuple,
        ):
            raise TypeError(
                "boot_requirements must be a tuple"
            )

        if not isinstance(
            selinux_graph,
            AndroidUniverseSelinuxPolicyGraph,
        ):
            raise TypeError(
                "selinux_graph must be an AndroidUniverseSelinuxPolicyGraph"
            )

        if (
            shell_scripts is not None
            and not isinstance(
                shell_scripts,
                AndroidShellScriptParsingResult,
            )
        ):
            raise TypeError(
                "shell_scripts must be an "
                "AndroidShellScriptParsingResult or None"
            )

        declarations = defaultdict(list)
        boot_exports = defaultdict(list)
        shell_setprops = defaultdict(list)
        action_commands = defaultdict(list)
        onrestart_commands = defaultdict(list)
        triggers = defaultdict(list)

        property_sources = {
            source.host_path: source
            for source
            in source_inventory.sources_for(
                AndroidModelSourceKind.PROPERTY
            )
        }

        selinux_sources = {
            source.host_path: source
            for source
            in source_inventory.sources_for(
                AndroidModelSourceKind.SELINUX
            )
        }

        property_keys = set()

        for parsed_source in parsing.property_files:
            model_source = property_sources.get(
                parsed_source.source_path
            )

            if model_source is None:
                raise ValueError(
                    "Parsed property source has no canonical "
                    "AndroidModelSource: "
                    f"{parsed_source.source_path}"
                )

            if not (
                AndroidUniverseRuntimeContextResolver
                .resolve_model_source(
                    model_source
                )
                .is_root
            ):
                continue

            for declaration in parsed_source.declarations:
                property_keys.add(
                    declaration.key
                )

                declarations[
                    declaration.key
                ].append(
                    AndroidUniverseRuntimePropertyDeclarationObservation(
                        parsed_source=parsed_source,
                        declaration=declaration,
                        model_source=model_source,
                    )
                )

        for boot_requirement in boot_requirements:
            semantics = getattr(
                boot_requirement,
                "semantics",
                None,
            )

            command_line = getattr(
                semantics,
                "command_line",
                None,
            )

            if command_line is None:
                continue

            for argument in command_line.arguments:
                if not argument.key.startswith("androidboot."):
                    continue

                if argument.kind.value != "assignment":
                    continue

                if argument.value is None:
                    continue

                property_key = (
                    "ro.boot."
                    + argument.key[len("androidboot."):]
                )

                property_keys.add(property_key)

                boot_exports[property_key].append(
                    AndroidUniverseRuntimePropertyBootExportObservation(
                        boot_requirement=boot_requirement,
                        argument=argument,
                        property_key=property_key,
                        property_value=argument.value,
                    )
                )

            bootconfig = getattr(
                semantics,
                "bootconfig",
                None,
            )

            if bootconfig is not None:
                for declaration in (
                    bootconfig.declarations
                ):
                    if not declaration.key.startswith(
                        "androidboot."
                    ):
                        continue

                    property_value = (
                        declaration.scalar_value
                    )

                    if not property_value:
                        continue

                    property_key = (
                        "ro.boot."
                        + declaration.key[
                            len(
                                "androidboot."
                            ):
                        ]
                    )

                    property_keys.add(
                        property_key
                    )

                    boot_exports[
                        property_key
                    ].append(
                        AndroidUniverseRuntimePropertyBootExportObservation(
                            boot_requirement=boot_requirement,
                            argument=declaration,
                            property_key=property_key,
                            property_value=property_value,
                        )
                    )

        for action in init_actions:
            if not (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    action.filesystem_source
                )
                .is_root
            ):
                continue

            for command_requirement in (
                action.command_requirements
            ):
                semantics = (
                    command_requirement.semantics
                )

                if not isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandKeyValueSemantics,
                ):
                    continue

                if semantics.keyword not in {
                    "setprop",
                    "wait_for_prop",
                }:
                    continue

                property_keys.add(
                    semantics.key
                )

                action_commands[
                    semantics.key
                ].append(
                    AndroidUniverseRuntimePropertyActionCommandObservation(
                        kind=(
                            AndroidUniverseRuntimePropertyCommandKind(
                                semantics.keyword
                            )
                        ),
                        init_action=action,
                        command_requirement=command_requirement,
                    )
                )

            for clause in (
                action.trigger_semantics.property_clauses
            ):
                property_keys.add(
                    clause.name
                )

                triggers[
                    clause.name
                ].append(
                    AndroidUniverseRuntimePropertyTriggerObservation(
                        init_action=action,
                        clause=clause,
                    )
                )

        for service in init_services:
            if not (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    service.filesystem_source
                )
                .is_root
            ):
                continue

            for command in (
                service.semantics.onrestart_commands
            ):
                semantics = command.semantics

                if not isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandKeyValueSemantics,
                ):
                    continue

                if semantics.keyword != "setprop":
                    continue

                property_keys.add(
                    semantics.key
                )

                onrestart_commands[
                    semantics.key
                ].append(
                    AndroidUniverseRuntimePropertyOnRestartObservation(
                        init_service=service,
                        onrestart_command=command,
                    )
                )

        property_contexts_list = []

        for requirement in (
            selinux_graph.context_requirements
        ):
            if (
                requirement.kind
                is not AndroidUniverseSelinuxContextKind.PROPERTY
            ):
                continue

            model_source = (
                selinux_sources.get(
                    requirement.declaration.source_path
                )
            )

            if model_source is None:
                raise ValueError(
                    "SELinux property_context requirement has no "
                    "canonical AndroidModelSource: "
                    f"{requirement.declaration.source_path}"
                )

            if not (
                AndroidUniverseRuntimeContextResolver
                .resolve_model_source(
                    model_source
                )
                .is_root
            ):
                continue

            property_contexts_list.append(
                requirement
            )

        property_contexts = tuple(
            property_contexts_list
        )

        if shell_scripts is not None:
            for script in shell_scripts.scripts:
                if not (
                    AndroidUniverseRuntimeContextResolver
                    .resolve_model_source(
                        script.source
                    )
                    .is_root
                ):
                    continue

                for command in script.command_observations:
                    resolved = command.resolved_argv

                    if len(
                        resolved
                    ) not in {
                        2,
                        3,
                    }:
                        continue

                    command_name = (
                        resolved[0]
                        if resolved[0] is not None
                        else command.argv[0]
                    )

                    if (
                        command_name.rsplit(
                            "/",
                            1,
                        )[-1]
                        != "setprop"
                    ):
                        continue

                    property_key = resolved[1]

                    if (
                        property_key is None
                        or not property_key
                    ):
                        continue

                    property_value = (
                        resolved[2]
                        if len(
                            resolved
                        )
                        == 3
                        else None
                    )

                    property_keys.add(
                        property_key
                    )

                    shell_setprops[
                        property_key
                    ].append(
                        AndroidUniverseRuntimePropertyShellSetpropObservation(
                            shell_script=script,
                            command=command,
                            property_key=property_key,
                            property_value=property_value,
                        )
                    )

        # Exact property_contexts selectors describe one concrete key and can
        # independently establish that runtime-property identity. Prefix
        # selectors are namespaces and attach only to concrete keys discovered
        # elsewhere.
        for requirement in property_contexts:
            if (
                android_property_context_mode(
                    requirement
                )
                is AndroidUniversePropertyContextMatchKind.EXACT
            ):
                property_keys.add(
                    requirement.selector
                )

        requirements = []

        for property_key in sorted(
            property_keys
        ):
            context_requirements, match_kind = (
                resolve_android_property_contexts(
                    property_key=property_key,
                    requirements=property_contexts,
                )
            )

            declaration_observations = tuple(
                sorted(
                    declarations.get(
                        property_key,
                        (),
                    ),
                    key=lambda item: (
                        item.model_source.source_name,
                        item.model_source.android_path.as_posix(),
                        item.declaration.line_number,
                        item.declaration.value,
                    ),
                )
            )

            boot_export_observations = tuple(
                sorted(
                    boot_exports.get(
                        property_key,
                        (),
                    ),
                    key=lambda item: (
                        item.boot_requirement.requirement_id,
                        item.argument.index,
                        item.argument.raw,
                        item.property_value,
                    ),
                )
            )

            shell_setprop_observations = tuple(
                sorted(
                    shell_setprops.get(
                        property_key,
                        (),
                    ),
                    key=lambda item: (
                        item.shell_script.source.identity_key,
                        item.command.line_number,
                        item.command.index,
                    ),
                )
            )

            action_command_observations = tuple(
                sorted(
                    action_commands.get(
                        property_key,
                        (),
                    ),
                    key=lambda item: (
                        item.init_action.requirement_id,
                        item.command_requirement.command.location.line,
                        item.kind.value,
                        item.property_value,
                    ),
                )
            )

            onrestart_observations = tuple(
                sorted(
                    onrestart_commands.get(
                        property_key,
                        (),
                    ),
                    key=lambda item: (
                        item.init_service.requirement_id,
                        item.onrestart_command.declaration.location.line,
                        item.property_value,
                    ),
                )
            )

            trigger_observations = tuple(
                sorted(
                    triggers.get(
                        property_key,
                        (),
                    ),
                    key=lambda item: (
                        item.init_action.requirement_id,
                        item.property_value,
                    ),
                )
            )

            requirements.append(
                AndroidUniverseRuntimePropertyRequirement(
                    property_key=property_key,
                    declaration_observations=(
                        declaration_observations
                    ),
                    boot_export_observations=(
                        boot_export_observations
                    ),
                    shell_setprop_observations=(
                        shell_setprop_observations
                    ),
                    action_command_observations=(
                        action_command_observations
                    ),
                    onrestart_observations=(
                        onrestart_observations
                    ),
                    trigger_observations=(
                        trigger_observations
                    ),
                    context_requirements=(
                        context_requirements
                    ),
                    context_match_kind=match_kind,
                )
            )

        return tuple(
            requirements
        )
