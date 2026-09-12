from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
)

from treeforge.android.parsing.kernel_module import (
    AndroidKernelModuleParsingResult,
    ParsedAndroidKernelModule,
    ParsedAndroidKernelModuleConfiguration,
)
from treeforge.android.universe.kernel_module.semantics import (
    AndroidUniverseKernelModuleConfigurationLineSemantics,
    AndroidUniverseKernelModuleInfoKind,
    AndroidUniverseKernelModuleInfoSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleFileRequirement:
    """
    Canonical semantic requirement for one exact installed kernel module.
    """

    source: ParsedAndroidKernelModule

    modinfo: tuple[
        AndroidUniverseKernelModuleInfoSemantics,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidKernelModule,
        ):
            raise TypeError(
                "source must be a ParsedAndroidKernelModule"
            )

        if not isinstance(
            self.modinfo,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidUniverseKernelModuleInfoSemantics,
            )
            for item in self.modinfo
        ):
            raise TypeError(
                "modinfo must contain "
                "AndroidUniverseKernelModuleInfoSemantics"
            )

        if len(
            self.modinfo
        ) != len(
            self.source.modinfo_entries
        ):
            raise ValueError(
                "Universe modinfo population must match Parsing"
            )

        for parsed, semantic in zip(
            self.source.modinfo_entries,
            self.modinfo,
            strict=True,
        ):
            if semantic.source is not parsed:
                raise ValueError(
                    "modinfo semantics must preserve exact Parsing identity"
                )

    def values(
        self,
        kind: AndroidUniverseKernelModuleInfoKind,
    ) -> tuple[str, ...]:
        if not isinstance(
            kind,
            AndroidUniverseKernelModuleInfoKind,
        ):
            raise TypeError(
                "kind must be an AndroidUniverseKernelModuleInfoKind"
            )

        return tuple(
            semantic.source.value
            for semantic in self.modinfo
            if (
                semantic.kind is kind
                and semantic.source.value is not None
            )
        )

    @property
    def declared_names(
        self,
    ) -> tuple[str, ...]:
        return self.values(
            AndroidUniverseKernelModuleInfoKind.NAME
        )

    @property
    def declared_dependencies(
        self,
    ) -> tuple[str, ...]:
        values: list[str] = []

        for declaration in self.values(
            AndroidUniverseKernelModuleInfoKind.DEPENDS
        ):
            for dependency in declaration.split(","):
                dependency = dependency.strip()

                if dependency:
                    values.append(
                        dependency
                    )

        return tuple(
            values
        )

    @property
    def declared_aliases(
        self,
    ) -> tuple[str, ...]:
        return self.values(
            AndroidUniverseKernelModuleInfoKind.ALIAS
        )

    @property
    def firmware_requirements(
        self,
    ) -> tuple[str, ...]:
        return self.values(
            AndroidUniverseKernelModuleInfoKind.FIRMWARE
        )

    @property
    def vermagic_values(
        self,
    ) -> tuple[str, ...]:
        return self.values(
            AndroidUniverseKernelModuleInfoKind.VERMAGIC
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleConfigurationRequirement:
    """
    Semantic view of one exact modules.* configuration source.
    """

    source: ParsedAndroidKernelModuleConfiguration

    artifact_requirement: AndroidUniverseArtifactRequirement

    lines: tuple[
        AndroidUniverseKernelModuleConfigurationLineSemantics,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidKernelModuleConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidKernelModuleConfiguration"
            )

        if not isinstance(
            self.artifact_requirement,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact_requirement must be an "
                "AndroidUniverseArtifactRequirement"
            )

        model_source = self.source.source

        if (
            self.artifact_requirement.inventory_entry.artifact
            is not model_source.filesystem_source.artifact
        ):
            raise ValueError(
                "kernel-module configuration Artifact must preserve "
                "exact filesystem Artifact identity"
            )

        metadata_path = (
            self.artifact_requirement.inventory_entry
            .filesystem_path_for_materialized_path(
                model_source.host_path
            )
        )

        if (
            self.artifact_requirement.metadata_entry.path
            != metadata_path
        ):
            raise ValueError(
                "kernel-module configuration Artifact must preserve "
                "exact canonical filesystem metadata identity"
            )

        if not isinstance(
            self.lines,
            tuple,
        ) or not all(
            isinstance(
                line,
                AndroidUniverseKernelModuleConfigurationLineSemantics,
            )
            for line in self.lines
        ):
            raise TypeError(
                "lines must contain "
                "AndroidUniverseKernelModuleConfigurationLineSemantics"
            )

        if len(
            self.lines
        ) != len(
            self.source.lines
        ):
            raise ValueError(
                "Universe configuration-line population must match Parsing"
            )

        for parsed, semantic in zip(
            self.source.lines,
            self.lines,
            strict=True,
        ):
            if semantic.source is not parsed:
                raise ValueError(
                    "configuration semantics must preserve exact "
                    "Parsing identity"
                )

            if (
                semantic.configuration_kind
                is not self.source.configuration_kind
            ):
                raise ValueError(
                    "configuration semantic kind must match its source"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleHardDependency:
    """
    One exact modules.dep relationship between physical module instances.

    The source configuration line remains authoritative evidence. Owner and
    dependency are exact physical module requirements in that deployment
    context; no logical-name fallback is used.
    """

    source: AndroidUniverseKernelModuleConfigurationLineSemantics

    owner: AndroidUniverseKernelModuleFileRequirement

    dependency: AndroidUniverseKernelModuleFileRequirement

    dependency_index: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseKernelModuleConfigurationLineSemantics,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseKernelModuleConfigurationLineSemantics"
            )

        if (
            self.source.configuration_kind.value
            != "modules.dep"
            or not self.source.interpreted
        ):
            raise ValueError(
                "hard dependency source must be an interpreted modules.dep line"
            )

        if not isinstance(
            self.owner,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "owner must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            self.dependency,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "dependency must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if (
            not isinstance(
                self.dependency_index,
                int,
            )
            or self.dependency_index < 0
            or self.dependency_index >= len(
                self.source.dependencies
            )
        ):
            raise ValueError(
                "dependency_index must address the source dependency tuple"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleBlocklistEntry:
    """
    One exact modules.blocklist declaration and its physical resolution.

    ``source`` preserves the exact declaration, including whether the target
    was written as a logical module name or with a ``.ko`` suffix.

    ``module`` preserves the exact same-context physical module requirement
    when one exists. ``None`` preserves a legitimate logical blocklist target
    for which this factory image contains no same-context physical module.

    Presence in modules.load is not contradictory and remains an independent
    canonical fact owned by ordered-load reconciliation.
    """

    source: AndroidUniverseKernelModuleConfigurationLineSemantics
    module: AndroidUniverseKernelModuleFileRequirement | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseKernelModuleConfigurationLineSemantics,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseKernelModuleConfigurationLineSemantics"
            )

        if (
            self.source.configuration_kind.value
            != "modules.blocklist"
            or not self.source.interpreted
        ):
            raise ValueError(
                "blocklist source must be an interpreted "
                "modules.blocklist line"
            )

        if (
            self.source.module is None
            or not self.source.module
        ):
            raise ValueError(
                "blocklist source must preserve a target module"
            )

        if (
            self.module is not None
            and not isinstance(
                self.module,
                AndroidUniverseKernelModuleFileRequirement,
            )
        ):
            raise TypeError(
                "module must be an "
                "AndroidUniverseKernelModuleFileRequirement "
                "or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleSoftDependencyReference:
    """
    One ordered pre/post reference from an exact modules.softdep declaration.

    ``declared_name`` preserves the exact module spelling from the source
    line. ``module`` is the exact same-context physical module requirement
    when one exists; None preserves a legitimate logical-only module reference
    without claiming that the target is absent or built into the kernel and
    without invalidating the owning softdep declaration.
    """

    declared_name: str
    dependency_index: int
    module: AndroidUniverseKernelModuleFileRequirement | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.declared_name,
                str,
            )
            or not self.declared_name
        ):
            raise ValueError(
                "declared_name must be a non-empty string"
            )

        if (
            not isinstance(
                self.dependency_index,
                int,
            )
            or self.dependency_index < 0
        ):
            raise ValueError(
                "dependency_index must be a non-negative integer"
            )

        if (
            self.module is not None
            and not isinstance(
                self.module,
                AndroidUniverseKernelModuleFileRequirement,
            )
        ):
            raise TypeError(
                "module must be an "
                "AndroidUniverseKernelModuleFileRequirement or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleSoftDependency:
    """
    One exact modules.softdep declaration.

    The declaration itself remains canonical even when one or more referenced
    modules are absent from the observed physical module population.

    Standard ``softdep=`` modinfo evidence is optional corroboration. When
    present it must exactly match the declaration's pre:/post: semantics.
    """

    source: AndroidUniverseKernelModuleConfigurationLineSemantics
    owner: AndroidUniverseKernelModuleFileRequirement

    pre_dependencies: tuple[
        AndroidUniverseKernelModuleSoftDependencyReference,
        ...,
    ] = ()

    post_dependencies: tuple[
        AndroidUniverseKernelModuleSoftDependencyReference,
        ...,
    ] = ()

    modinfo: AndroidUniverseKernelModuleInfoSemantics | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseKernelModuleConfigurationLineSemantics,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseKernelModuleConfigurationLineSemantics"
            )

        if (
            self.source.configuration_kind.value
            != "modules.softdep"
            or not self.source.interpreted
        ):
            raise ValueError(
                "softdep source must be an interpreted modules.softdep line"
            )

        if (
            self.source.module is None
            or not self.source.module
        ):
            raise ValueError(
                "softdep source must preserve an owner module"
            )

        if not isinstance(
            self.owner,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "owner must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        for name, values in (
            (
                "pre_dependencies",
                self.pre_dependencies,
            ),
            (
                "post_dependencies",
                self.post_dependencies,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ) or not all(
                isinstance(
                    value,
                    AndroidUniverseKernelModuleSoftDependencyReference,
                )
                for value in values
            ):
                raise TypeError(
                    f"{name} must contain "
                    "AndroidUniverseKernelModuleSoftDependencyReference"
                )

            for expected_index, value in enumerate(
                values
            ):
                if (
                    value.dependency_index
                    != expected_index
                ):
                    raise ValueError(
                        f"{name} dependency indexes must preserve "
                        "source ordering"
                    )

        if tuple(
            reference.declared_name
            for reference in self.pre_dependencies
        ) != self.source.pre_dependencies:
            raise ValueError(
                "pre_dependencies must preserve exact source semantics"
            )

        if tuple(
            reference.declared_name
            for reference in self.post_dependencies
        ) != self.source.post_dependencies:
            raise ValueError(
                "post_dependencies must preserve exact source semantics"
            )

        if self.modinfo is not None:
            if not isinstance(
                self.modinfo,
                AndroidUniverseKernelModuleInfoSemantics,
            ):
                raise TypeError(
                    "modinfo must be an "
                    "AndroidUniverseKernelModuleInfoSemantics or None"
                )

            if (
                self.modinfo.kind
                is not AndroidUniverseKernelModuleInfoKind.SOFTDEP
            ):
                raise ValueError(
                    "softdep corroboration must use an exact standard "
                    "modinfo softdep observation"
                )

            expected_parts = []

            if self.source.pre_dependencies:
                expected_parts.extend(
                    (
                        "pre:",
                        *self.source.pre_dependencies,
                    )
                )

            if self.source.post_dependencies:
                expected_parts.extend(
                    (
                        "post:",
                        *self.source.post_dependencies,
                    )
                )

            if self.modinfo.value != " ".join(
                expected_parts
            ):
                raise ValueError(
                    "modinfo softdep corroboration must exactly match "
                    "the source declaration"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleAlias:
    """
    One exact modules.alias declaration resolved to a physical module.

    ``source`` preserves the exact modules.alias semantic line, including
    the alias pattern and declared target spelling.

    ``module`` is the exact same-context physical module instance selected
    by canonical Linux module-name normalization.

    ``modinfo`` preserves zero or more exact standard ``alias=`` modinfo
    observations on that physical module. modules.alias remains
    independently authoritative when corroboration is absent, and repeated
    exact modinfo observations remain distinct evidence.

    Alias patterns are deliberately not unique: multiple declarations may
    repeat the same pattern and may legitimately target different modules.
    """

    source: AndroidUniverseKernelModuleConfigurationLineSemantics

    module: AndroidUniverseKernelModuleFileRequirement

    modinfo: tuple[
        AndroidUniverseKernelModuleInfoSemantics,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseKernelModuleConfigurationLineSemantics,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseKernelModuleConfigurationLineSemantics"
            )

        if (
            self.source.configuration_kind.value
            != "modules.alias"
            or not self.source.interpreted
        ):
            raise ValueError(
                "alias source must be an interpreted modules.alias line"
            )

        if (
            self.source.alias_pattern is None
            or not self.source.alias_pattern
        ):
            raise ValueError(
                "alias source must preserve an alias pattern"
            )

        if (
            self.source.module is None
            or not self.source.module
        ):
            raise ValueError(
                "alias source must preserve a target module"
            )

        if not isinstance(
            self.module,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "module must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            self.modinfo,
            tuple,
        ) or not all(
            isinstance(
                semantic,
                AndroidUniverseKernelModuleInfoSemantics,
            )
            for semantic in self.modinfo
        ):
            raise TypeError(
                "modinfo must contain "
                "AndroidUniverseKernelModuleInfoSemantics"
            )

        for semantic in self.modinfo:
            if (
                semantic.kind
                is not AndroidUniverseKernelModuleInfoKind.ALIAS
            ):
                raise ValueError(
                    "alias corroboration must use exact standard "
                    "modinfo alias observations"
                )

            if (
                semantic.value
                != self.source.alias_pattern
            ):
                raise ValueError(
                    "modinfo alias corroboration must preserve the "
                    "same exact alias pattern"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleLoadEntry:
    """
    One exact ordered modules.load entry resolved to a physical module.

    The configuration-line semantic remains authoritative source evidence.
    ``sequence_index`` preserves the entry's exact ordinal within that
    modules.load source. The target is one exact physical module requirement
    in the same deployment context.

    This relationship expresses declared load-list order only. It does not
    reinterpret modules.dep dependency ordering or boot-time parallel-loading
    policy.
    """

    source: AndroidUniverseKernelModuleConfigurationLineSemantics

    sequence_index: int

    module: AndroidUniverseKernelModuleFileRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseKernelModuleConfigurationLineSemantics,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseKernelModuleConfigurationLineSemantics"
            )

        if (
            self.source.configuration_kind.value
            != "modules.load"
            or not self.source.interpreted
        ):
            raise ValueError(
                "load entry source must be an interpreted modules.load line"
            )

        if (
            self.source.module is None
            or not self.source.module
        ):
            raise ValueError(
                "load entry source must expose a module reference"
            )

        if (
            not isinstance(
                self.sequence_index,
                int,
            )
            or self.sequence_index < 0
        ):
            raise ValueError(
                "sequence_index must be a non-negative integer"
            )

        if not isinstance(
            self.module,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "module must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleModinfoDependency:
    """
    One exact .modinfo ``depends=`` declaration corroborated by modules.dep.

    ``source`` preserves the exact semantic .modinfo record. A single
    depends record may contain multiple comma-separated module names, so
    ``dependency_index`` identifies one non-empty declaration within that
    exact record.

    Owner and dependency remain exact physical module requirements. The
    matching ``hard_dependency`` retains the independent modules.dep
    provenance for the same physical relationship.
    """

    source: AndroidUniverseKernelModuleInfoSemantics

    dependency_index: int

    declared_name: str

    owner: AndroidUniverseKernelModuleFileRequirement

    dependency: AndroidUniverseKernelModuleFileRequirement

    hard_dependency: AndroidUniverseKernelModuleHardDependency

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseKernelModuleInfoSemantics,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseKernelModuleInfoSemantics"
            )

        if (
            self.source.kind
            is not AndroidUniverseKernelModuleInfoKind.DEPENDS
        ):
            raise ValueError(
                "modinfo dependency source must be a depends record"
            )

        if self.source.value is None:
            raise ValueError(
                "modinfo dependency source must preserve a value"
            )

        declarations = tuple(
            value.strip()
            for value in self.source.value.split(",")
            if value.strip()
        )

        if (
            not isinstance(
                self.dependency_index,
                int,
            )
            or self.dependency_index < 0
            or self.dependency_index >= len(
                declarations
            )
        ):
            raise ValueError(
                "dependency_index must address a non-empty "
                "depends declaration"
            )

        if (
            not isinstance(
                self.declared_name,
                str,
            )
            or not self.declared_name
        ):
            raise ValueError(
                "declared_name must be a non-empty string"
            )

        if (
            declarations[
                self.dependency_index
            ]
            != self.declared_name
        ):
            raise ValueError(
                "declared_name must preserve the exact indexed "
                "depends declaration"
            )

        if not isinstance(
            self.owner,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "owner must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            self.dependency,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "dependency must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            self.hard_dependency,
            AndroidUniverseKernelModuleHardDependency,
        ):
            raise TypeError(
                "hard_dependency must be an "
                "AndroidUniverseKernelModuleHardDependency"
            )

        if (
            self.hard_dependency.owner
            is not self.owner
            or self.hard_dependency.dependency
            is not self.dependency
        ):
            raise ValueError(
                "hard_dependency must corroborate the exact "
                "physical owner/dependency relationship"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleLogicalIdentity:
    """
    One canonical logical Linux kernel-module identity.

    Physical module instances are deliberately preserved. A logical identity
    groups only module instances whose exact declared ``name=`` values become
    equal under Linux module-name normalization (``-`` and ``_`` are
    interchangeable for module lookup).
    """

    name: str

    instances: tuple[
        AndroidUniverseKernelModuleFileRequirement,
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
            or "-" in self.name
        ):
            raise ValueError(
                "name must be a non-empty normalized kernel-module name"
            )

        if (
            not isinstance(
                self.instances,
                tuple,
            )
            or not self.instances
            or not all(
                isinstance(
                    instance,
                    AndroidUniverseKernelModuleFileRequirement,
                )
                for instance in self.instances
            )
        ):
            raise TypeError(
                "instances must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        identities = tuple(
            {
                value.replace(
                    "-",
                    "_",
                )
                for value
                in instance.declared_names
            }
            for instance in self.instances
        )

        if any(
            values != {
                self.name
            }
            for values in identities
        ):
            raise ValueError(
                "logical identity instances must all declare the "
                "same normalized module name"
            )

    @property
    def deployment_contexts(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    instance.source.elf.source
                    .filesystem_source.source_name
                    for instance in self.instances
                }
            )
        )

    @property
    def is_cross_context(
        self,
    ) -> bool:
        return len(
            self.deployment_contexts
        ) > 1


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleRequirement:
    """
    Canonical Universe interpretation for kernel modules and modules.* input.

    The original aggregate Parsing objects remain preserved exactly while
    module-local and configuration-local semantics are exposed for later
    dependency/name/load-policy reconciliation.
    """

    modules: AndroidKernelModuleParsingResult

    configurations: tuple[
        ParsedAndroidKernelModuleConfiguration,
        ...,
    ]

    module_requirements: tuple[
        AndroidUniverseKernelModuleFileRequirement,
        ...,
    ] = ()

    configuration_requirements: tuple[
        AndroidUniverseKernelModuleConfigurationRequirement,
        ...,
    ] = ()

    logical_identities: tuple[
        AndroidUniverseKernelModuleLogicalIdentity,
        ...,
    ] = ()

    hard_dependencies: tuple[
        AndroidUniverseKernelModuleHardDependency,
        ...,
    ] = ()

    modinfo_dependencies: tuple[
        AndroidUniverseKernelModuleModinfoDependency,
        ...,
    ] = ()

    load_entries: tuple[
        AndroidUniverseKernelModuleLoadEntry,
        ...,
    ] = ()

    aliases: tuple[
        AndroidUniverseKernelModuleAlias,
        ...,
    ] = ()

    soft_dependencies: tuple[
        AndroidUniverseKernelModuleSoftDependency,
        ...,
    ] = ()

    blocklist_entries: tuple[
        AndroidUniverseKernelModuleBlocklistEntry,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.modules,
            AndroidKernelModuleParsingResult,
        ):
            raise TypeError(
                "modules must be an AndroidKernelModuleParsingResult"
            )

        if not isinstance(
            self.configurations,
            tuple,
        ) or not all(
            isinstance(
                item,
                ParsedAndroidKernelModuleConfiguration,
            )
            for item in self.configurations
        ):
            raise TypeError(
                "configurations must contain only "
                "ParsedAndroidKernelModuleConfiguration instances"
            )

        if not isinstance(
            self.module_requirements,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for item in self.module_requirements
        ):
            raise TypeError(
                "module_requirements must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            self.configuration_requirements,
            tuple,
        ) or not all(
            isinstance(
                item,
                AndroidUniverseKernelModuleConfigurationRequirement,
            )
            for item in self.configuration_requirements
        ):
            raise TypeError(
                "configuration_requirements must contain "
                "AndroidUniverseKernelModuleConfigurationRequirement"
            )

        if not isinstance(
            self.blocklist_entries,
            tuple,
        ) or not all(
            isinstance(
                entry,
                AndroidUniverseKernelModuleBlocklistEntry,
            )
            for entry in self.blocklist_entries
        ):
            raise TypeError(
                "blocklist_entries must contain "
                "AndroidUniverseKernelModuleBlocklistEntry"
            )

        module_ids_for_blocklist = {
            id(
                module
            )
            for module in self.module_requirements
        }

        configuration_line_ids_for_blocklist = {
            id(
                line
            )
            for configuration in self.configuration_requirements
            for line in configuration.lines
        }

        for entry in self.blocklist_entries:
            if (
                entry.module is not None
                and id(
                    entry.module
                ) not in module_ids_for_blocklist
            ):
                raise ValueError(
                    "resolved blocklist target must preserve exact "
                    "module requirement identity"
                )

            if id(
                entry.source
            ) not in configuration_line_ids_for_blocklist:
                raise ValueError(
                    "blocklist source must preserve exact configuration "
                    "semantic identity"
                )

        if not isinstance(
            self.soft_dependencies,
            tuple,
        ) or not all(
            isinstance(
                softdep,
                AndroidUniverseKernelModuleSoftDependency,
            )
            for softdep in self.soft_dependencies
        ):
            raise TypeError(
                "soft_dependencies must contain "
                "AndroidUniverseKernelModuleSoftDependency"
            )

        module_requirement_ids_for_softdeps = {
            id(
                module
            )
            for module in self.module_requirements
        }

        configuration_line_ids_for_softdeps = {
            id(
                line
            )
            for configuration in self.configuration_requirements
            for line in configuration.lines
        }

        for softdep in self.soft_dependencies:
            if id(
                softdep.owner
            ) not in module_requirement_ids_for_softdeps:
                raise ValueError(
                    "softdep owner must preserve exact module "
                    "requirement identity"
                )

            if id(
                softdep.source
            ) not in configuration_line_ids_for_softdeps:
                raise ValueError(
                    "softdep source must preserve exact configuration "
                    "semantic identity"
                )

            for reference in (
                *softdep.pre_dependencies,
                *softdep.post_dependencies,
            ):
                if (
                    reference.module is not None
                    and id(
                        reference.module
                    )
                    not in module_requirement_ids_for_softdeps
                ):
                    raise ValueError(
                        "resolved softdep reference must preserve exact "
                        "module requirement identity"
                    )

            if (
                softdep.modinfo is not None
                and not any(
                    semantic is softdep.modinfo
                    for semantic in softdep.owner.modinfo
                )
            ):
                raise ValueError(
                    "softdep modinfo corroboration must preserve exact "
                    "semantic identity from its owner module"
                )

        if not isinstance(
            self.aliases,
            tuple,
        ) or not all(
            isinstance(
                alias,
                AndroidUniverseKernelModuleAlias,
            )
            for alias in self.aliases
        ):
            raise TypeError(
                "aliases must contain "
                "AndroidUniverseKernelModuleAlias"
            )

        module_ids_for_aliases = {
            id(
                module
            )
            for module in self.module_requirements
        }

        configuration_line_ids = {
            id(
                line
            )
            for configuration in self.configuration_requirements
            for line in configuration.lines
        }

        for alias in self.aliases:
            if id(
                alias.module
            ) not in module_ids_for_aliases:
                raise ValueError(
                    "alias target must preserve an exact "
                    "module requirement identity"
                )

            if id(
                alias.source
            ) not in configuration_line_ids:
                raise ValueError(
                    "alias source must preserve an exact "
                    "configuration semantic identity"
                )

            for corroboration in alias.modinfo:
                if not any(
                    semantic is corroboration
                    for semantic in alias.module.modinfo
                ):
                    raise ValueError(
                        "alias modinfo corroboration must preserve an "
                        "exact semantic identity from the target module"
                    )

            if len(
                {
                    id(
                        corroboration
                    )
                    for corroboration in alias.modinfo
                }
            ) != len(
                alias.modinfo
            ):
                raise ValueError(
                    "alias modinfo corroboration identities must be unique"
                )

        if not isinstance(
            self.load_entries,
            tuple,
        ) or not all(
            isinstance(
                entry,
                AndroidUniverseKernelModuleLoadEntry,
            )
            for entry in self.load_entries
        ):
            raise TypeError(
                "load_entries must contain "
                "AndroidUniverseKernelModuleLoadEntry"
            )

        module_ids_for_load_entries = {
            id(
                module
            )
            for module in self.module_requirements
        }

        load_source_ordinals = set()

        for entry in self.load_entries:
            if id(
                entry.module
            ) not in module_ids_for_load_entries:
                raise ValueError(
                    "load entry must preserve an exact "
                    "module requirement identity"
                )

            source_owner = None

            for configuration in self.configuration_requirements:
                for index, line in enumerate(
                    configuration.lines
                ):
                    if line is entry.source:
                        source_owner = (
                            configuration,
                            index,
                        )
                        break

                if source_owner is not None:
                    break

            if source_owner is None:
                raise ValueError(
                    "load entry source must preserve an exact "
                    "configuration semantic identity"
                )

            configuration, source_index = source_owner

            if (
                configuration.source.configuration_kind.value
                != "modules.load"
            ):
                raise ValueError(
                    "load entry source must belong to modules.load"
                )

            if source_index != entry.sequence_index:
                raise ValueError(
                    "load entry sequence_index must preserve "
                    "the exact modules.load source ordinal"
                )

            identity = (
                id(
                    configuration
                ),
                entry.sequence_index,
            )

            if identity in load_source_ordinals:
                raise ValueError(
                    "duplicate canonical modules.load source ordinal"
                )

            load_source_ordinals.add(
                identity
            )

        if not isinstance(
            self.modinfo_dependencies,
            tuple,
        ) or not all(
            isinstance(
                dependency,
                AndroidUniverseKernelModuleModinfoDependency,
            )
            for dependency in self.modinfo_dependencies
        ):
            raise TypeError(
                "modinfo_dependencies must contain "
                "AndroidUniverseKernelModuleModinfoDependency"
            )

        hard_dependency_ids = {
            id(
                dependency
            )
            for dependency in self.hard_dependencies
        }

        module_ids = {
            id(
                module
            )
            for module in self.module_requirements
        }

        for dependency in self.modinfo_dependencies:
            if id(
                dependency.owner
            ) not in module_ids:
                raise ValueError(
                    "modinfo dependency owner must preserve an exact "
                    "module requirement identity"
                )

            if id(
                dependency.dependency
            ) not in module_ids:
                raise ValueError(
                    "modinfo dependency target must preserve an exact "
                    "module requirement identity"
                )

            if id(
                dependency.hard_dependency
            ) not in hard_dependency_ids:
                raise ValueError(
                    "modinfo dependency must reference an exact "
                    "canonical hard dependency"
                )

        if not isinstance(
            self.hard_dependencies,
            tuple,
        ) or not all(
            isinstance(
                dependency,
                AndroidUniverseKernelModuleHardDependency,
            )
            for dependency in self.hard_dependencies
        ):
            raise TypeError(
                "hard_dependencies must contain "
                "AndroidUniverseKernelModuleHardDependency"
            )

        if not isinstance(
            self.logical_identities,
            tuple,
        ) or not all(
            isinstance(
                identity,
                AndroidUniverseKernelModuleLogicalIdentity,
            )
            for identity in self.logical_identities
        ):
            raise TypeError(
                "logical_identities must contain "
                "AndroidUniverseKernelModuleLogicalIdentity"
            )

        identity_instances = tuple(
            instance
            for identity in self.logical_identities
            for instance in identity.instances
        )

        if len(
            identity_instances
        ) != len(
            self.module_requirements
        ):
            raise ValueError(
                "logical identity population must cover every "
                "physical module requirement exactly once"
            )

        if {
            id(instance)
            for instance in identity_instances
        } != {
            id(instance)
            for instance in self.module_requirements
        }:
            raise ValueError(
                "logical identity instances must be the exact "
                "module requirement population"
            )

        identity_names = tuple(
            identity.name
            for identity in self.logical_identities
        )

        if identity_names != tuple(
            sorted(
                identity_names
            )
        ):
            raise ValueError(
                "logical identities must use deterministic name order"
            )

        if len(
            identity_names
        ) != len(
            set(
                identity_names
            )
        ):
            raise ValueError(
                "logical kernel-module identities must be unique"
            )

        if len(
            self.module_requirements
        ) != len(
            self.modules.modules
        ):
            raise ValueError(
                "Universe kernel-module population must match Parsing"
            )

        for parsed, requirement in zip(
            self.modules.modules,
            self.module_requirements,
            strict=True,
        ):
            if requirement.source is not parsed:
                raise ValueError(
                    "module requirement must preserve exact Parsing identity"
                )

        if len(
            self.configuration_requirements
        ) != len(
            self.configurations
        ):
            raise ValueError(
                "Universe modules.* population must match Parsing"
            )

        for parsed, requirement in zip(
            self.configurations,
            self.configuration_requirements,
            strict=True,
        ):
            if requirement.source is not parsed:
                raise ValueError(
                    "configuration requirement must preserve exact "
                    "Parsing identity"
                )

    @property
    def configuration_lines(
        self,
    ) -> tuple[
        AndroidUniverseKernelModuleConfigurationLineSemantics,
        ...,
    ]:
        return tuple(
            line
            for requirement in self.configuration_requirements
            for line in requirement.lines
        )
