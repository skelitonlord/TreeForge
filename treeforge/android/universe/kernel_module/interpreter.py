from __future__ import annotations

from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementInventory,
)

from treeforge.android.parsing.kernel_module import (
    AndroidKernelModuleConfigurationKind,
    AndroidKernelModuleConfigurationLine,
    AndroidKernelModuleParsingResult,
    ParsedAndroidKernelModule,
    ParsedAndroidKernelModuleConfiguration,
    ParsedAndroidKernelModuleInfoEntry,
)
from treeforge.android.universe.kernel_module.reconciler import (
    AndroidUniverseKernelModuleAliasReconciler,
    AndroidUniverseKernelModuleBlocklistReconciler,
    AndroidUniverseKernelModuleHardDependencyReconciler,
    AndroidUniverseKernelModuleIdentityReconciler,
    AndroidUniverseKernelModuleLoadReconciler,
    AndroidUniverseKernelModuleSoftDependencyReconciler,
    AndroidUniverseKernelModuleModinfoDependencyReconciler,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleConfigurationRequirement,
    AndroidUniverseKernelModuleFileRequirement,
    AndroidUniverseKernelModuleRequirement,
)
from treeforge.android.universe.kernel_module.semantics import (
    AndroidUniverseKernelModuleConfigurationLineSemantics,
    AndroidUniverseKernelModuleInfoKind,
    AndroidUniverseKernelModuleInfoSemantics,
)


_STANDARD_MODINFO_KINDS = {
    kind.value: kind
    for kind in AndroidUniverseKernelModuleInfoKind
    if kind not in {
        AndroidUniverseKernelModuleInfoKind.OTHER,
        AndroidUniverseKernelModuleInfoKind.UNKEYED,
    }
}


class AndroidUniverseKernelModuleInterpreter:
    """
    Interpret canonical module-local and modules.* semantics.

    Cross-source module identity reconciliation, dependency graph resolution,
    load-order reconciliation, and boot-policy reconciliation remain separate
    Android Device Universe work.
    """

    def interpret(
        self,
        modules: AndroidKernelModuleParsingResult,
        configurations: tuple[
            ParsedAndroidKernelModuleConfiguration,
            ...,
        ],
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseKernelModuleRequirement:
        if not isinstance(
            modules,
            AndroidKernelModuleParsingResult,
        ):
            raise TypeError(
                "modules must be an AndroidKernelModuleParsingResult"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        if not isinstance(
            configurations,
            tuple,
        ) or not all(
            isinstance(
                item,
                ParsedAndroidKernelModuleConfiguration,
            )
            for item in configurations
        ):
            raise TypeError(
                "configurations must contain "
                "ParsedAndroidKernelModuleConfiguration"
            )

        module_requirements = tuple(
            self._interpret_module(
                module
            )
            for module in modules.modules
        )

        configuration_requirements = tuple(
            self._interpret_configuration(
                configuration,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
            for configuration in configurations
        )

        logical_identities = (
            AndroidUniverseKernelModuleIdentityReconciler()
            .reconcile(
                module_requirements
            )
        )

        hard_dependencies = (
            AndroidUniverseKernelModuleHardDependencyReconciler()
            .reconcile(
                module_requirements,
                configuration_requirements,
            )
        )

        modinfo_dependencies = (
            AndroidUniverseKernelModuleModinfoDependencyReconciler()
            .reconcile(
                module_requirements,
                hard_dependencies,
            )
        )

        load_entries = (
            AndroidUniverseKernelModuleLoadReconciler()
            .reconcile(
                module_requirements,
                configuration_requirements,
            )
        )

        aliases = (
            AndroidUniverseKernelModuleAliasReconciler()
            .reconcile(
                module_requirements,
                configuration_requirements,
            )
        )

        soft_dependencies = (
            AndroidUniverseKernelModuleSoftDependencyReconciler()
            .reconcile(
                module_requirements,
                configuration_requirements,
            )
        )

        blocklist_entries = (
            AndroidUniverseKernelModuleBlocklistReconciler()
            .reconcile(
                module_requirements,
                configuration_requirements,
            )
        )

        return AndroidUniverseKernelModuleRequirement(
            modules=modules,
            configurations=configurations,
            module_requirements=module_requirements,
            configuration_requirements=configuration_requirements,
            logical_identities=logical_identities,
            hard_dependencies=hard_dependencies,
            modinfo_dependencies=modinfo_dependencies,
            load_entries=load_entries,
            aliases=aliases,
            soft_dependencies=soft_dependencies,
            blocklist_entries=blocklist_entries,
        )

    def _interpret_module(
        self,
        module: ParsedAndroidKernelModule,
    ) -> AndroidUniverseKernelModuleFileRequirement:
        return AndroidUniverseKernelModuleFileRequirement(
            source=module,
            modinfo=tuple(
                self._interpret_modinfo(
                    entry
                )
                for entry in module.modinfo_entries
            ),
        )

    @staticmethod
    def _interpret_modinfo(
        entry: ParsedAndroidKernelModuleInfoEntry,
    ) -> AndroidUniverseKernelModuleInfoSemantics:
        if entry.key is None:
            kind = AndroidUniverseKernelModuleInfoKind.UNKEYED
        else:
            kind = _STANDARD_MODINFO_KINDS.get(
                entry.key,
                AndroidUniverseKernelModuleInfoKind.OTHER,
            )

        return AndroidUniverseKernelModuleInfoSemantics(
            source=entry,
            kind=kind,
        )

    def _interpret_configuration(
        self,
        configuration: ParsedAndroidKernelModuleConfiguration,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseKernelModuleConfigurationRequirement:
        model_source = configuration.source

        try:
            inventory_entry = (
                artifact_requirements
                .source_inventory
                .entry_for_artifact(
                    model_source.filesystem_source.artifact
                )
            )
        except KeyError as error:
            raise ValueError(
                "kernel-module configuration source has no exact "
                "canonical Filesystem Metadata inventory entry: "
                f"source={model_source.identity_key!r}"
            ) from error

        metadata_path = (
            inventory_entry
            .filesystem_path_for_materialized_path(
                model_source.host_path
            )
        )

        metadata_entry = (
            inventory_entry
            .result
            .metadata
            .get(
                metadata_path
            )
        )

        if metadata_entry is None:
            raise ValueError(
                "kernel-module configuration source has no exact "
                "canonical Filesystem Metadata entry: "
                f"source={model_source.identity_key!r}, "
                f"metadata_path={metadata_path!r}"
            )

        matches = tuple(
            requirement
            for requirement
            in artifact_requirements.requirements
            if (
                requirement.inventory_entry
                is inventory_entry
                and requirement.metadata_entry
                is metadata_entry
            )
        )

        if len(matches) != 1:
            raise ValueError(
                "kernel-module configuration source must reconcile "
                "to exactly one canonical Artifact requirement: "
                f"source={model_source.identity_key!r}, "
                f"matches={len(matches)}"
            )

        return AndroidUniverseKernelModuleConfigurationRequirement(
            source=configuration,
            artifact_requirement=matches[0],
            lines=tuple(
                self._interpret_configuration_line(
                    configuration.configuration_kind,
                    line,
                )
                for line in configuration.lines
            ),
        )

    def _interpret_configuration_line(
        self,
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        if kind is AndroidKernelModuleConfigurationKind.DEP:
            return self._interpret_dep(
                kind,
                line,
            )

        if kind is AndroidKernelModuleConfigurationKind.LOAD:
            return self._interpret_load(
                kind,
                line,
            )

        if kind is AndroidKernelModuleConfigurationKind.ALIAS:
            return self._interpret_alias(
                kind,
                line,
            )

        if kind is AndroidKernelModuleConfigurationKind.SOFTDEP:
            return self._interpret_softdep(
                kind,
                line,
            )

        if kind is AndroidKernelModuleConfigurationKind.BLOCKLIST:
            return self._interpret_blocklist(
                kind,
                line,
            )

        return self._uninterpreted(
            kind,
            line,
        )

    @staticmethod
    def _interpret_dep(
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        module, separator, remainder = line.content.partition(
            ":"
        )

        module = module.strip()

        if not separator or not module:
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        dependencies = tuple(
            value
            for value in remainder.split()
            if value
        )

        return AndroidUniverseKernelModuleConfigurationLineSemantics(
            source=line,
            configuration_kind=kind,
            interpreted=True,
            module=module,
            dependencies=dependencies,
        )

    @staticmethod
    def _interpret_load(
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        if len(
            line.tokens
        ) != 1:
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        return AndroidUniverseKernelModuleConfigurationLineSemantics(
            source=line,
            configuration_kind=kind,
            interpreted=True,
            module=line.tokens[0],
        )

    @staticmethod
    def _interpret_alias(
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        tokens = line.tokens

        if (
            len(tokens) < 3
            or tokens[0] != "alias"
        ):
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        #
        # Treat the final token as the module target and preserve every token
        # between "alias" and that target as the pattern. This deliberately
        # handles observed aliases containing spaces.
        #
        pattern = " ".join(
            tokens[1:-1]
        )

        if not pattern:
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        return AndroidUniverseKernelModuleConfigurationLineSemantics(
            source=line,
            configuration_kind=kind,
            interpreted=True,
            module=tokens[-1],
            alias_pattern=pattern,
        )

    @staticmethod
    def _interpret_blocklist(
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        tokens = line.tokens

        if (
            len(tokens) != 2
            or tokens[0] != "blocklist"
        ):
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        return AndroidUniverseKernelModuleConfigurationLineSemantics(
            source=line,
            configuration_kind=kind,
            interpreted=True,
            module=tokens[1],
        )

    @staticmethod
    def _interpret_softdep(
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        tokens = line.tokens

        if (
            len(tokens) < 2
            or tokens[0] != "softdep"
        ):
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        module = tokens[1]
        before: list[str] = []
        after: list[str] = []

        target: list[str] | None = None

        for token in tokens[2:]:
            if token == "pre:":
                target = before
                continue

            if token == "post:":
                target = after
                continue

            if target is None:
                return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                    kind,
                    line,
                )

            target.append(
                token
            )

        if not before and not after:
            return AndroidUniverseKernelModuleInterpreter._uninterpreted(
                kind,
                line,
            )

        return AndroidUniverseKernelModuleConfigurationLineSemantics(
            source=line,
            configuration_kind=kind,
            interpreted=True,
            module=module,
            pre_dependencies=tuple(
                before
            ),
            post_dependencies=tuple(
                after
            ),
        )

    @staticmethod
    def _uninterpreted(
        kind: AndroidKernelModuleConfigurationKind,
        line: AndroidKernelModuleConfigurationLine,
    ) -> AndroidUniverseKernelModuleConfigurationLineSemantics:
        return AndroidUniverseKernelModuleConfigurationLineSemantics(
            source=line,
            configuration_kind=kind,
            interpreted=False,
        )
