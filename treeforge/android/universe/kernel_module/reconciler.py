from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath

from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleConfigurationRequirement,
    AndroidUniverseKernelModuleFileRequirement,
    AndroidUniverseKernelModuleAlias,
    AndroidUniverseKernelModuleBlocklistEntry,
    AndroidUniverseKernelModuleHardDependency,
    AndroidUniverseKernelModuleLoadEntry,
    AndroidUniverseKernelModuleLogicalIdentity,
    AndroidUniverseKernelModuleModinfoDependency,
    AndroidUniverseKernelModuleSoftDependency,
    AndroidUniverseKernelModuleSoftDependencyReference,
)
from treeforge.android.universe.kernel_module.semantics import (
    AndroidUniverseKernelModuleInfoKind,
)



def normalize_kernel_module_name(
    value: str,
) -> str:
    """
    Apply Linux kernel-module name normalization.

    Kernel module lookup treats '-' and '_' as interchangeable. Universe
    canonicalizes to '_' while preserving every original filename and
    declared name through the attached Parsing evidence.
    """

    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(
            "kernel-module name must be a non-empty string"
        )

    return value.replace(
        "-",
        "_",
    )


class AndroidUniverseKernelModuleIdentityReconciler:
    """
    Group physical kernel-module requirements into logical identities.

    This reconciler intentionally does not resolve dependencies, aliases,
    load order, softdeps, blocklists, or boot policy.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleLogicalIdentity,
        ...,
    ]:
        if not isinstance(
            modules,
            tuple,
        ) or not all(
            isinstance(
                module,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for module in modules
        ):
            raise TypeError(
                "modules must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        grouped: dict[
            str,
            list[
                AndroidUniverseKernelModuleFileRequirement
            ],
        ] = defaultdict(
            list
        )

        for module in modules:
            names = module.declared_names

            if len(
                names
            ) != 1:
                raise ValueError(
                    "kernel-module identity reconciliation requires "
                    "exactly one declared module name per physical module"
                )

            normalized = normalize_kernel_module_name(
                names[0]
            )

            basename = (
                module.source.elf.source
                .host_path.stem
            )

            normalized_basename = (
                normalize_kernel_module_name(
                    basename
                )
            )

            if normalized_basename != normalized:
                raise ValueError(
                    "kernel-module basename and declared name disagree "
                    "after generic Linux name normalization: "
                    f"{basename!r} != {names[0]!r}"
                )

            grouped[
                normalized
            ].append(
                module
            )

        return tuple(
            AndroidUniverseKernelModuleLogicalIdentity(
                name=name,
                instances=tuple(
                    sorted(
                        instances,
                        key=lambda instance: (
                            instance.source.elf.source
                            .filesystem_source.source_name,
                            instance.source.elf.source
                            .android_path.as_posix(),
                        ),
                    )
                ),
            )
            for name, instances
            in sorted(
                grouped.items()
            )
        )



def _kernel_module_android_path(
    module: AndroidUniverseKernelModuleFileRequirement,
) -> str:
    path = module.source.elf.source.android_path.as_posix()

    if not path.startswith("/"):
        raise ValueError(
            "kernel-module Android path must be absolute"
        )

    return path


def _kernel_module_tree_relative_path(
    value: str,
) -> str:
    """
    Return one kernel-module path relative to its ``lib/modules`` root.

    Parsing preserves the canonical Android-visible filesystem namespace,
    such as ``/system_dlkm/lib/modules/...`` or
    ``/vendor_dlkm/lib/modules/...``.

    Linux/Android module metadata may refer to the same physical module
    through a loader/install namespace, such as
    ``/system/lib/modules/...`` or ``/vendor/lib/modules/...``.

    Those namespace prefixes are not interchangeable canonical paths.
    Reconciliation therefore compares only the path below the semantic
    ``lib/modules`` root while retaining deployment context separately.

    Relative modules.dep paths are also valid and are already module-tree
    relative, so they are preserved directly.
    """

    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(
            "kernel-module path must be a non-empty string"
        )

    path = PurePosixPath(
        value
    )

    if not path.is_absolute():
        relative = path.as_posix()

        if (
            not relative
            or relative == "."
            or relative.startswith("../")
        ):
            raise ValueError(
                "relative kernel-module path must remain inside "
                "the module tree"
            )

        return relative

    parts = path.parts

    anchors = tuple(
        index
        for index in range(
            len(parts) - 1
        )
        if (
            parts[index] == "lib"
            and parts[index + 1] == "modules"
        )
    )

    if len(anchors) != 1:
        raise ValueError(
            "absolute kernel-module path must contain exactly one "
            f"lib/modules root: {value!r}"
        )

    start = (
        anchors[0]
        + 2
    )

    relative_parts = (
        parts[start:]
    )

    if not relative_parts:
        raise ValueError(
            "kernel-module path must identify an entry below "
            f"lib/modules: {value!r}"
        )

    return PurePosixPath(
        *relative_parts
    ).as_posix()


def _kernel_module_context(
    module: AndroidUniverseKernelModuleFileRequirement,
) -> str:
    context = (
        module.source.elf.source
        .filesystem_source.source_name
    )

    if (
        not isinstance(
            context,
            str,
        )
        or not context
    ):
        raise ValueError(
            "kernel-module filesystem source must expose a context name"
        )

    return context


class AndroidUniverseKernelModuleHardDependencyReconciler:
    """
    Resolve modules.dep paths to exact physical module requirements.

    Deployment context plus the path relative to the semantic ``lib/modules``
    root is authoritative.

    Parsing's canonical Android-visible path and modules.dep's loader/install
    path are deliberately preserved as distinct namespace observations. This
    pass does not rewrite either one and does not use logical module-name
    fallback.

    It does not yet reconcile against .modinfo depends= declarations.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
        configurations: tuple[
            AndroidUniverseKernelModuleConfigurationRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleHardDependency,
        ...,
    ]:
        if not isinstance(
            modules,
            tuple,
        ) or not all(
            isinstance(
                module,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for module in modules
        ):
            raise TypeError(
                "modules must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            configurations,
            tuple,
        ) or not all(
            isinstance(
                configuration,
                AndroidUniverseKernelModuleConfigurationRequirement,
            )
            for configuration in configurations
        ):
            raise TypeError(
                "configurations must contain "
                "AndroidUniverseKernelModuleConfigurationRequirement"
            )

        by_context_module_path = {}

        for module in modules:
            canonical_android_path = (
                _kernel_module_android_path(
                    module
                )
            )

            module_relative_path = (
                _kernel_module_tree_relative_path(
                    canonical_android_path
                )
            )

            key = (
                _kernel_module_context(
                    module
                ),
                module_relative_path,
            )

            if key in by_context_module_path:
                raise ValueError(
                    "duplicate physical kernel-module "
                    "context/module-tree identity: "
                    f"{key!r}"
                )

            by_context_module_path[
                key
            ] = module

        edges = []

        for configuration in configurations:
            if (
                configuration.source.configuration_kind.value
                != "modules.dep"
            ):
                continue

            context = (
                configuration.source.source
                .filesystem_source.source_name
            )

            if (
                not isinstance(
                    context,
                    str,
                )
                or not context
            ):
                raise ValueError(
                    "modules.dep configuration must expose "
                    "a deployment context"
                )

            for line in configuration.lines:
                if not line.interpreted:
                    raise ValueError(
                        "modules.dep dependency reconciliation requires "
                        "interpreted source lines"
                    )

                if line.module is None:
                    raise ValueError(
                        "modules.dep semantic line has no owner path"
                    )

                owner_relative_path = (
                    _kernel_module_tree_relative_path(
                        line.module
                    )
                )

                owner_key = (
                    context,
                    owner_relative_path,
                )

                try:
                    owner = by_context_module_path[
                        owner_key
                    ]
                except KeyError as error:
                    raise ValueError(
                        "modules.dep owner does not resolve to an exact "
                        "physical module by deployment context and "
                        "module-tree-relative path: "
                        f"reference={line.module!r} "
                        f"key={owner_key!r}"
                    ) from error

                for dependency_index, dependency_path in enumerate(
                    line.dependencies
                ):
                    dependency_relative_path = (
                        _kernel_module_tree_relative_path(
                            dependency_path
                        )
                    )

                    dependency_key = (
                        context,
                        dependency_relative_path,
                    )

                    try:
                        dependency = by_context_module_path[
                            dependency_key
                        ]
                    except KeyError as error:
                        raise ValueError(
                            "modules.dep dependency does not resolve to an "
                            "exact physical module by deployment context "
                            "and module-tree-relative path: "
                            f"reference={dependency_path!r} "
                            f"key={dependency_key!r}"
                        ) from error

                    edges.append(
                        AndroidUniverseKernelModuleHardDependency(
                            source=line,
                            owner=owner,
                            dependency=dependency,
                            dependency_index=dependency_index,
                        )
                    )

        return tuple(
            edges
        )



class AndroidUniverseKernelModuleModinfoDependencyReconciler:
    """
    Reconcile .modinfo ``depends=`` declarations with physical hard edges.

    Logical Linux module-name normalization is used only to identify the
    same-context physical target named by a modinfo declaration.

    Every resulting relationship must also be corroborated by an existing
    exact modules.dep hard dependency. Additional modules.dep relationships
    are independent evidence and are deliberately not treated as conflicts.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
        hard_dependencies: tuple[
            AndroidUniverseKernelModuleHardDependency,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleModinfoDependency,
        ...,
    ]:
        if not isinstance(
            modules,
            tuple,
        ) or not all(
            isinstance(
                module,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for module in modules
        ):
            raise TypeError(
                "modules must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            hard_dependencies,
            tuple,
        ) or not all(
            isinstance(
                dependency,
                AndroidUniverseKernelModuleHardDependency,
            )
            for dependency in hard_dependencies
        ):
            raise TypeError(
                "hard_dependencies must contain "
                "AndroidUniverseKernelModuleHardDependency"
            )

        by_context_name = defaultdict(
            list
        )

        for module in modules:
            if len(
                module.declared_names
            ) != 1:
                raise ValueError(
                    "modinfo dependency reconciliation requires "
                    "exactly one declared module name per physical instance"
                )

            context = (
                _kernel_module_context(
                    module
                )
            )

            logical_name = (
                normalize_kernel_module_name(
                    module.declared_names[
                        0
                    ]
                )
            )

            by_context_name[
                (
                    context,
                    logical_name,
                )
            ].append(
                module
            )

        hard_by_owner_target = defaultdict(
            list
        )

        for hard_dependency in hard_dependencies:
            hard_by_owner_target[
                (
                    id(
                        hard_dependency.owner
                    ),
                    id(
                        hard_dependency.dependency
                    ),
                )
            ].append(
                hard_dependency
            )

        reconciled = []

        for owner in modules:
            context = (
                _kernel_module_context(
                    owner
                )
            )

            for semantic in owner.modinfo:
                if (
                    semantic.kind
                    is not AndroidUniverseKernelModuleInfoKind.DEPENDS
                ):
                    continue

                if semantic.value is None:
                    raise ValueError(
                        "depends semantic must preserve its parsed value"
                    )

                declarations = tuple(
                    value.strip()
                    for value in semantic.value.split(",")
                    if value.strip()
                )

                for dependency_index, declared_name in enumerate(
                    declarations
                ):
                    logical_name = (
                        normalize_kernel_module_name(
                            declared_name
                        )
                    )

                    candidates = tuple(
                        by_context_name.get(
                            (
                                context,
                                logical_name,
                            ),
                            (),
                        )
                    )

                    if not candidates:
                        raise ValueError(
                            "modinfo dependency does not resolve to a "
                            "same-context physical module: "
                            f"context={context!r} "
                            f"owner={owner.source.android_path.as_posix()!r} "
                            f"declared={declared_name!r}"
                        )

                    if len(
                        candidates
                    ) != 1:
                        raise ValueError(
                            "modinfo dependency resolves ambiguously within "
                            "its deployment context: "
                            f"context={context!r} "
                            f"owner={owner.source.android_path.as_posix()!r} "
                            f"declared={declared_name!r} "
                            f"candidates={len(candidates)}"
                        )

                    dependency = (
                        candidates[
                            0
                        ]
                    )

                    hard_matches = tuple(
                        hard_by_owner_target.get(
                            (
                                id(
                                    owner
                                ),
                                id(
                                    dependency
                                ),
                            ),
                            (),
                        )
                    )

                    if not hard_matches:
                        raise ValueError(
                            "modinfo dependency is not corroborated by "
                            "modules.dep: "
                            f"context={context!r} "
                            f"owner={owner.source.android_path.as_posix()!r} "
                            f"declared={declared_name!r}"
                        )

                    if len(
                        hard_matches
                    ) != 1:
                        raise ValueError(
                            "modinfo dependency has multiple exact "
                            "modules.dep corroborating edges: "
                            f"context={context!r} "
                            f"owner={owner.source.android_path.as_posix()!r} "
                            f"declared={declared_name!r} "
                            f"matches={len(hard_matches)}"
                        )

                    reconciled.append(
                        AndroidUniverseKernelModuleModinfoDependency(
                            source=semantic,
                            dependency_index=dependency_index,
                            declared_name=declared_name,
                            owner=owner,
                            dependency=dependency,
                            hard_dependency=hard_matches[
                                0
                            ],
                        )
                    )

        return tuple(
            reconciled
        )



class AndroidUniverseKernelModuleLoadReconciler:
    """
    Resolve ordered modules.load entries to exact physical module instances.

    Deployment context plus the path relative to the semantic ``lib/modules``
    root is authoritative, matching the physical namespace reconciliation
    used for modules.dep.

    Source order is preserved exactly. This pass does not apply dependency
    ordering, soft dependencies, aliases, blocklists, or boot-time parallel
    loading policy.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
        configurations: tuple[
            AndroidUniverseKernelModuleConfigurationRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleLoadEntry,
        ...,
    ]:
        if not isinstance(
            modules,
            tuple,
        ) or not all(
            isinstance(
                module,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for module in modules
        ):
            raise TypeError(
                "modules must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            configurations,
            tuple,
        ) or not all(
            isinstance(
                configuration,
                AndroidUniverseKernelModuleConfigurationRequirement,
            )
            for configuration in configurations
        ):
            raise TypeError(
                "configurations must contain "
                "AndroidUniverseKernelModuleConfigurationRequirement"
            )

        by_context_module_path = {}

        for module in modules:
            key = (
                _kernel_module_context(
                    module
                ),
                _kernel_module_tree_relative_path(
                    _kernel_module_android_path(
                        module
                    )
                ),
            )

            if key in by_context_module_path:
                raise ValueError(
                    "duplicate physical kernel-module "
                    "context/module-tree identity during "
                    f"modules.load reconciliation: {key!r}"
                )

            by_context_module_path[
                key
            ] = module

        entries = []

        for configuration in configurations:
            if (
                configuration.source.configuration_kind.value
                != "modules.load"
            ):
                continue

            context = (
                configuration.source.source
                .filesystem_source.source_name
            )

            if (
                not isinstance(
                    context,
                    str,
                )
                or not context
            ):
                raise ValueError(
                    "modules.load configuration must expose "
                    "a deployment context"
                )

            seen_module_ids = set()

            for sequence_index, line in enumerate(
                configuration.lines
            ):
                if not line.interpreted:
                    raise ValueError(
                        "modules.load reconciliation requires "
                        "interpreted source lines"
                    )

                if line.module is None:
                    raise ValueError(
                        "modules.load semantic line has no module reference"
                    )

                module_relative_path = (
                    _kernel_module_tree_relative_path(
                        line.module
                    )
                )

                key = (
                    context,
                    module_relative_path,
                )

                try:
                    module = by_context_module_path[
                        key
                    ]
                except KeyError as error:
                    raise ValueError(
                        "modules.load entry does not resolve to an exact "
                        "physical module by deployment context and "
                        "module-tree-relative path: "
                        f"reference={line.module!r} "
                        f"key={key!r}"
                    ) from error

                module_id = id(
                    module
                )

                if module_id in seen_module_ids:
                    raise ValueError(
                        "modules.load contains a duplicate physical "
                        "module within one ordered source: "
                        f"context={context!r} "
                        f"reference={line.module!r}"
                    )

                seen_module_ids.add(
                    module_id
                )

                entries.append(
                    AndroidUniverseKernelModuleLoadEntry(
                        source=line,
                        sequence_index=sequence_index,
                        module=module,
                    )
                )

        return tuple(
            entries
        )



class AndroidUniverseKernelModuleAliasReconciler:
    """
    Resolve modules.alias declarations to exact physical module instances.

    The modules.alias source line is authoritative. Target resolution uses
    same-context Linux logical module-name normalization.

    Exact standard ``alias=`` modinfo observations are attached when
    present, including repeated exact observations. They remain optional
    corroboration. Additional namespaced
    ``*.alias=`` modinfo records remain OTHER semantics and never
    participate here.

    Alias patterns are not unique and are never deduplicated.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
        configurations: tuple[
            AndroidUniverseKernelModuleConfigurationRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleAlias,
        ...,
    ]:
        if not isinstance(
            modules,
            tuple,
        ) or not all(
            isinstance(
                module,
                AndroidUniverseKernelModuleFileRequirement,
            )
            for module in modules
        ):
            raise TypeError(
                "modules must contain "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            configurations,
            tuple,
        ) or not all(
            isinstance(
                configuration,
                AndroidUniverseKernelModuleConfigurationRequirement,
            )
            for configuration in configurations
        ):
            raise TypeError(
                "configurations must contain "
                "AndroidUniverseKernelModuleConfigurationRequirement"
            )

        by_context_name = defaultdict(
            list
        )

        for module in modules:
            if len(
                module.declared_names
            ) != 1:
                raise ValueError(
                    "alias reconciliation requires exactly one "
                    "declared module name per physical instance"
                )

            context = (
                _kernel_module_context(
                    module
                )
            )

            logical_name = (
                normalize_kernel_module_name(
                    module.declared_names[
                        0
                    ]
                )
            )

            by_context_name[
                (
                    context,
                    logical_name,
                )
            ].append(
                module
            )

        aliases = []

        for configuration in configurations:
            if (
                configuration.source.configuration_kind.value
                != "modules.alias"
            ):
                continue

            context = (
                configuration.source.source
                .filesystem_source.source_name
            )

            if (
                not isinstance(
                    context,
                    str,
                )
                or not context
            ):
                raise ValueError(
                    "modules.alias configuration must expose "
                    "a deployment context"
                )

            for line in configuration.lines:
                if not line.interpreted:
                    raise ValueError(
                        "modules.alias reconciliation requires "
                        "interpreted source lines"
                    )

                if (
                    line.alias_pattern is None
                    or not line.alias_pattern
                ):
                    raise ValueError(
                        "modules.alias semantic line has no alias pattern"
                    )

                if (
                    line.module is None
                    or not line.module
                ):
                    raise ValueError(
                        "modules.alias semantic line has no target module"
                    )

                logical_name = (
                    normalize_kernel_module_name(
                        line.module
                    )
                )

                candidates = tuple(
                    by_context_name.get(
                        (
                            context,
                            logical_name,
                        ),
                        (),
                    )
                )

                if not candidates:
                    raise ValueError(
                        "modules.alias target does not resolve to a "
                        "same-context physical module: "
                        f"context={context!r} "
                        f"target={line.module!r} "
                        f"pattern={line.alias_pattern!r}"
                    )

                if len(
                    candidates
                ) != 1:
                    raise ValueError(
                        "modules.alias target resolves ambiguously "
                        "within its deployment context: "
                        f"context={context!r} "
                        f"target={line.module!r} "
                        f"pattern={line.alias_pattern!r} "
                        f"candidates={len(candidates)}"
                    )

                module = (
                    candidates[
                        0
                    ]
                )

                corroborating = tuple(
                    semantic
                    for semantic in module.modinfo
                    if (
                        semantic.kind
                        is AndroidUniverseKernelModuleInfoKind.ALIAS
                        and semantic.value
                        == line.alias_pattern
                    )
                )

                aliases.append(
                    AndroidUniverseKernelModuleAlias(
                        source=line,
                        module=module,
                        modinfo=corroborating,
                    )
                )

        return tuple(
            aliases
        )



class AndroidUniverseKernelModuleSoftDependencyReconciler:
    """
    Resolve modules.softdep declarations without requiring every target to be
    physically installed.

    Owners must resolve uniquely within their deployment context.

    Each pre:/post: target is resolved against the same context using canonical
    Linux module-name normalization. If no same-context physical module target
    exists, the exact declared name remains as a logical-only reference.
    Universe does not infer whether that logical target is built into the
    kernel, externally supplied, or absent when canonical evidence cannot
    distinguish those outcomes.

    Exact standard modinfo ``softdep=`` observations are optional
    declaration-level corroboration.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
        configurations: tuple[
            AndroidUniverseKernelModuleConfigurationRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleSoftDependency,
        ...,
    ]:
        by_context_name = defaultdict(
            list
        )

        for module in modules:
            if len(
                module.declared_names
            ) != 1:
                raise ValueError(
                    "softdep reconciliation requires exactly one declared "
                    "module name per physical instance"
                )

            context = _kernel_module_context(
                module
            )

            by_context_name[
                (
                    context,
                    normalize_kernel_module_name(
                        module.declared_names[0]
                    ),
                )
            ].append(
                module
            )

        results = []

        for configuration in configurations:
            if (
                configuration.source.configuration_kind.value
                != "modules.softdep"
            ):
                continue

            context = (
                configuration.source.source
                .filesystem_source.source_name
            )

            for line in configuration.lines:
                if (
                    not line.interpreted
                    or line.module is None
                    or not line.module
                ):
                    raise ValueError(
                        "modules.softdep reconciliation requires an "
                        "interpreted owner declaration"
                    )

                owner_candidates = tuple(
                    by_context_name.get(
                        (
                            context,
                            normalize_kernel_module_name(
                                line.module
                            ),
                        ),
                        (),
                    )
                )

                if not owner_candidates:
                    raise ValueError(
                        "modules.softdep owner does not resolve to a "
                        "same-context physical module: "
                        f"context={context!r} owner={line.module!r}"
                    )

                if len(
                    owner_candidates
                ) != 1:
                    raise ValueError(
                        "modules.softdep owner resolves ambiguously: "
                        f"context={context!r} owner={line.module!r} "
                        f"candidates={len(owner_candidates)}"
                    )

                owner = owner_candidates[0]

                def resolve_references(
                    names: tuple[
                        str,
                        ...,
                    ],
                ) -> tuple[
                    AndroidUniverseKernelModuleSoftDependencyReference,
                    ...,
                ]:
                    references = []

                    for dependency_index, name in enumerate(
                        names
                    ):
                        candidates = tuple(
                            by_context_name.get(
                                (
                                    context,
                                    normalize_kernel_module_name(
                                        name
                                    ),
                                ),
                                (),
                            )
                        )

                        if len(
                            candidates
                        ) > 1:
                            raise ValueError(
                                "modules.softdep dependency resolves "
                                "ambiguously: "
                                f"context={context!r} "
                                f"owner={line.module!r} "
                                f"dependency={name!r} "
                                f"candidates={len(candidates)}"
                            )

                        references.append(
                            AndroidUniverseKernelModuleSoftDependencyReference(
                                declared_name=name,
                                dependency_index=dependency_index,
                                module=(
                                    candidates[0]
                                    if candidates
                                    else None
                                ),
                            )
                        )

                    return tuple(
                        references
                    )

                pre_dependencies = resolve_references(
                    line.pre_dependencies
                )

                post_dependencies = resolve_references(
                    line.post_dependencies
                )

                expected_parts = []

                if line.pre_dependencies:
                    expected_parts.extend(
                        (
                            "pre:",
                            *line.pre_dependencies,
                        )
                    )

                if line.post_dependencies:
                    expected_parts.extend(
                        (
                            "post:",
                            *line.post_dependencies,
                        )
                    )

                expected_modinfo = " ".join(
                    expected_parts
                )

                corroborating = tuple(
                    semantic
                    for semantic in owner.modinfo
                    if (
                        semantic.kind
                        is AndroidUniverseKernelModuleInfoKind.SOFTDEP
                        and semantic.value
                        == expected_modinfo
                    )
                )

                if len(
                    corroborating
                ) > 1:
                    raise ValueError(
                        "modules.softdep declaration has repeated exact "
                        "standard modinfo corroboration unexpectedly: "
                        f"context={context!r} "
                        f"owner={line.module!r} "
                        f"value={expected_modinfo!r} "
                        f"matches={len(corroborating)}"
                    )

                results.append(
                    AndroidUniverseKernelModuleSoftDependency(
                        source=line,
                        owner=owner,
                        pre_dependencies=pre_dependencies,
                        post_dependencies=post_dependencies,
                        modinfo=(
                            corroborating[0]
                            if corroborating
                            else None
                        ),
                    )
                )

        return tuple(
            results
        )



class AndroidUniverseKernelModuleBlocklistReconciler:
    """
    Reconcile exact modules.blocklist declarations against same-context
    physical module requirements.

    Source spellings may be logical names or ``.ko`` filenames. Resolution
    removes an optional ``.ko`` suffix, applies canonical Linux module-name
    normalization, and remains bounded to the declaration's deployment
    context.

    A declaration with no same-context physical module remains canonical with
    an unresolved physical target. Ambiguous physical resolution remains an
    error. Blocklist membership is independent from explicit modules.load
    presence.
    """

    def reconcile(
        self,
        modules: tuple[
            AndroidUniverseKernelModuleFileRequirement,
            ...,
        ],
        configurations: tuple[
            AndroidUniverseKernelModuleConfigurationRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleBlocklistEntry,
        ...,
    ]:
        by_context_name = defaultdict(
            list
        )

        for module in modules:
            if len(
                module.declared_names
            ) != 1:
                raise ValueError(
                    "blocklist reconciliation requires exactly one "
                    "declared module name per physical instance"
                )

            context = _kernel_module_context(
                module
            )

            by_context_name[
                (
                    context,
                    normalize_kernel_module_name(
                        module.declared_names[0]
                    ),
                )
            ].append(
                module
            )

        entries = []

        for configuration in configurations:
            if (
                configuration.source.configuration_kind.value
                != "modules.blocklist"
            ):
                continue

            context = (
                configuration.source.source
                .filesystem_source.source_name
            )

            for line in configuration.lines:
                if (
                    not line.interpreted
                    or line.module is None
                    or not line.module
                ):
                    raise ValueError(
                        "modules.blocklist reconciliation requires an "
                        "interpreted target declaration"
                    )

                declared = line.module

                logical_name = (
                    declared[:-3]
                    if declared.endswith(
                        ".ko"
                    )
                    else declared
                )

                candidates = tuple(
                    by_context_name.get(
                        (
                            context,
                            normalize_kernel_module_name(
                                logical_name
                            ),
                        ),
                        (),
                    )
                )

                if len(
                    candidates
                ) > 1:
                    raise ValueError(
                        "modules.blocklist target resolves ambiguously: "
                        f"context={context!r} "
                        f"target={declared!r} "
                        f"candidates={len(candidates)}"
                    )

                entries.append(
                    AndroidUniverseKernelModuleBlocklistEntry(
                        source=line,
                        module=(
                            candidates[0]
                            if candidates
                            else None
                        ),
                    )
                )

        return tuple(
            entries
        )
