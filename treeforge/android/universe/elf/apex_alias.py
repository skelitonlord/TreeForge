from __future__ import annotations

import posixpath
from dataclasses import replace
from pathlib import PurePosixPath

from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.extraction.model import (
    ExtractionOperation,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.elf.alias import (
    AndroidUniverseElfFilesystemAlias,
    AndroidUniverseElfFilesystemAliasReconciler,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.universe.elf.apex_local_alias import (
    AndroidUniverseElfApexLocalAlias,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerElfContext,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)


class AndroidUniverseElfApexFilesystemAliasReconciler:
    """
    Reconcile canonical filesystem symlinks whose Android-visible target lies
    inside one canonical APEX payload.

    This is a Universe semantic-reconciliation pass.

    The source symlink remains authoritative Filesystem Metadata evidence.
    APEX ownership remains authoritative from the already-reconciled
    AndroidUniverseLinkerElfContext. This pass does not select an active APEX,
    synthesize an active mount root, assign linker namespaces, resolve
    DT_NEEDED, or create Reconstruction work.
    """

    @classmethod
    def _terminal_target_path(
        cls,
        *,
        entries,
        alias_entry,
    ) -> str | None:
        """
        Follow canonical symlink metadata inside the alias-owning filesystem
        until resolution leaves that filesystem or reaches a non-symlink path.

        The returned path is an Android/filesystem-native path only. No host
        filesystem lookup is performed.
        """

        target = alias_entry.symlink_target

        if not target:
            return None

        current = (
            AndroidUniverseElfFilesystemAliasReconciler
            ._target_path(
                symlink_path=alias_entry.path,
                target=target,
            )
        )

        seen: set[str] = {
            alias_entry.path,
        }

        while True:
            parts = tuple(
                part
                for part
                in PurePosixPath(current).parts
                if part != "/"
            )

            resolved_parts: list[str] = []
            redirected = False

            for index, part in enumerate(parts):
                resolved_parts.append(part)

                candidate_path = (
                    "/"
                    + "/".join(resolved_parts)
                )

                entry = entries.get(candidate_path)

                if (
                    entry is None
                    or entry.entry_type
                    is not FilesystemEntryType.SYMLINK
                ):
                    continue

                if candidate_path in seen:
                    return None

                seen.add(candidate_path)

                nested_target = entry.symlink_target

                if not nested_target:
                    return None

                target_path = (
                    AndroidUniverseElfFilesystemAliasReconciler
                    ._target_path(
                        symlink_path=candidate_path,
                        target=nested_target,
                    )
                )

                remaining = parts[index + 1:]

                if remaining:
                    target_path = (
                        AndroidUniverseElfFilesystemAliasReconciler
                        ._normalized_path(
                            posixpath.join(
                                target_path,
                                *remaining,
                            )
                        )
                    )

                current = target_path
                redirected = True
                break

            if redirected:
                continue

            return current

    @staticmethod
    def _apex_target_identity(
        path: str,
    ) -> tuple[str, PurePosixPath] | None:
        """
        Interpret the canonical Android APEX mount identity form:

            /apex/<apex-name>/<payload-relative-path>

        This establishes package/payload identity only. It does not conclude
        which version is active or synthesize Runtime Linking deployment.
        """

        value = PurePosixPath(path)

        if not value.is_absolute():
            return None

        parts = value.parts

        if (
            len(parts) < 4
            or parts[0] != "/"
            or parts[1] != "apex"
        ):
            return None

        apex_name = parts[2]

        if not apex_name:
            return None

        payload_path = PurePosixPath(
            "/"
            + "/".join(parts[3:])
        )

        return (
            apex_name,
            payload_path,
        )

    @staticmethod
    def _same_runtime_apex_candidates(
        *,
        apex_name: str,
        runtime_context,
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseApexRequirement,
        ...,
    ]:
        return tuple(
            requirement
            for requirement
            in apex_requirements
            if (
                requirement.apex_name == apex_name
                and (
                    AndroidUniverseRuntimeContextResolver
                    .same_runtime(
                        requirement.runtime_context,
                        runtime_context,
                    )
                )
            )
        )

    @classmethod
    def reconcile(
        cls,
        *,
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
        linker_elf_contexts: tuple[
            AndroidUniverseLinkerElfContext,
            ...,
        ],
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
        source_inventory: AndroidModelSourceInventory,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> tuple[
        tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
        tuple[
            AndroidUniverseLinkerElfContext,
            ...,
        ],
    ]:
        if not isinstance(elf_requirements, tuple):
            raise TypeError(
                "elf_requirements must be a tuple"
            )

        if not all(
            isinstance(value, AndroidUniverseElfRequirement)
            for value in elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement values"
            )

        if not isinstance(linker_elf_contexts, tuple):
            raise TypeError(
                "linker_elf_contexts must be a tuple"
            )

        if not all(
            isinstance(value, AndroidUniverseLinkerElfContext)
            for value in linker_elf_contexts
        ):
            raise TypeError(
                "linker_elf_contexts must contain only "
                "AndroidUniverseLinkerElfContext values"
            )

        if not isinstance(apex_requirements, tuple):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(value, AndroidUniverseApexRequirement)
            for value in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement values"
            )

        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an "
                "AndroidModelSourceInventory"
            )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        context_by_requirement_identity = {
            id(context.elf_requirement): context
            for context
            in linker_elf_contexts
        }

        if len(context_by_requirement_identity) != len(
            linker_elf_contexts
        ):
            raise ValueError(
                "Linker/ELF contexts must preserve unique "
                "ELF requirement identities"
            )

        aliases_by_requirement: dict[
            int,
            list[AndroidUniverseElfFilesystemAlias],
        ] = {}

        apex_local_aliases_by_requirement: dict[
            int,
            list[AndroidUniverseElfApexLocalAlias],
        ] = {}

        #
        # Search canonical symlink witnesses from every parser filesystem.
        # Runtime scoping prevents nested Android runtimes from satisfying
        # aliases belonging to another runtime.
        #
        for alias_filesystem_source in source_inventory.filesystems:
            alias_runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_filesystem_source(
                    alias_filesystem_source
                )
            )

            try:
                inventory_entry = (
                    filesystem_inventory
                    .entry_for_artifact(
                        alias_filesystem_source.artifact
                    )
                )
            except KeyError:
                continue

            entries = (
                inventory_entry
                .result
                .metadata
                .entries
            )

            for alias_entry in sorted(
                (
                    entry
                    for entry
                    in entries.values()
                    if (
                        entry.entry_type
                        is FilesystemEntryType.SYMLINK
                    )
                ),
                key=lambda value: value.path,
            ):
                terminal_target = cls._terminal_target_path(
                    entries=entries,
                    alias_entry=alias_entry,
                )

                if terminal_target is None:
                    continue

                apex_identity = cls._apex_target_identity(
                    terminal_target
                )

                if apex_identity is None:
                    continue

                (
                    apex_name,
                    payload_path,
                ) = apex_identity

                same_runtime_apex = (
                    cls._same_runtime_apex_candidates(
                        apex_name=apex_name,
                        runtime_context=alias_runtime_context,
                        apex_requirements=apex_requirements,
                    )
                )

                #
                # /apex/<name>/... alone does not select among multiple
                # canonical package instances. Active/version selection is
                # Runtime Linking responsibility, so Universe must not guess.
                #
                if len(same_runtime_apex) != 1:
                    continue

                selected_apex = same_runtime_apex[0]

                matching_contexts = tuple(
                    context
                    for context
                    in linker_elf_contexts
                    if (
                        context.selected_apex_requirement
                        is selected_apex
                        and (
                            AndroidUniverseRuntimeContextResolver
                            .same_runtime(
                                context.runtime_context,
                                alias_runtime_context,
                            )
                        )
                        and (
                            context
                            .elf_requirement
                            .source
                            .source
                            .android_path
                            == payload_path
                        )
                    )
                )

                #
                # Preserve ambiguity rather than choosing one physical ELF.
                # No canonical alias edge is emitted unless the target identity
                # is exact.
                #
                if len(matching_contexts) != 1:
                    continue

                context = matching_contexts[0]
                requirement = context.elf_requirement
                parsed_elf = requirement.source
                target_entry = (
                    parsed_elf
                    .source
                    .metadata_entry
                )

                if target_entry is None:
                    continue

                alias_host_path = (
                    AndroidUniverseElfFilesystemAliasReconciler
                    ._materialized_path(
                        filesystem_source=(
                            alias_filesystem_source
                        ),
                        metadata_entry=alias_entry,
                    )
                )

                projected: dict[
                    PurePosixPath,
                    list,
                ] = {}

                for view in alias_filesystem_source.views:
                    try:
                        android_path = (
                            view.android_path_for(
                                alias_host_path
                            )
                        )
                    except ValueError:
                        continue

                    projected.setdefault(
                        android_path,
                        [],
                    ).append(view)

                for (
                    android_path,
                    views,
                ) in projected.items():
                    alias = AndroidUniverseElfFilesystemAlias(
                        source=parsed_elf,
                        alias_entry=alias_entry,
                        target_entry=target_entry,
                        alias_filesystem_source=(
                            alias_filesystem_source
                        ),
                        filesystem_views=tuple(
                            sorted(
                                views,
                                key=lambda value: (
                                    value
                                    .android_prefix
                                    .as_posix(),
                                    value
                                    .filesystem
                                    .root
                                    .as_posix(),
                                ),
                            )
                        ),
                        android_path=android_path,
                    )

                    aliases_by_requirement.setdefault(
                        id(requirement),
                        [],
                    ).append(alias)

        #
        # Reconcile the inverse cross-filesystem direction:
        #
        #   client APEX payload /lib*/foo.so
        #       -> Android-global /system|.../foo.so
        #
        # Exact client-APEX ownership comes only from already-reconciled
        # Linker/ELF contexts. The payload path remains APEX-local here;
        # Runtime Linking later projects it beneath the selected active root.
        #

        apex_by_filesystem_identity: dict[
            int,
            AndroidUniverseApexRequirement,
        ] = {}

        filesystem_by_identity = {}

        for context in linker_elf_contexts:
            selected_apex = (
                context.selected_apex_requirement
            )

            parsed_source = (
                context
                .elf_requirement
                .source
                .source
            )

            filesystem_source = (
                parsed_source.filesystem_source
            )

            if (
                selected_apex is None
                or filesystem_source is None
            ):
                continue

            key = id(filesystem_source)

            existing = (
                apex_by_filesystem_identity
                .get(key)
            )

            if (
                existing is not None
                and existing is not selected_apex
            ):
                raise ValueError(
                    "one canonical APEX payload filesystem "
                    "resolved to more than one exact APEX requirement"
                )

            apex_by_filesystem_identity[
                key
            ] = selected_apex

            filesystem_by_identity[
                key
            ] = filesystem_source

        #
        # Build an exact same-runtime Android-path -> ELF context index from
        # physical canonical paths plus already-established global filesystem
        # aliases. This deliberately does not include APEX-local aliases being
        # created by this pass.
        #
        path_index: dict[
            tuple[
                object,
                str,
            ],
            list[
                AndroidUniverseLinkerElfContext
            ],
        ] = {}

        def runtime_key(runtime_context):
            if runtime_context.is_root:
                return (
                    "root",
                    None,
                )

            return (
                "nested",
                id(runtime_context.partition_container),
            )

        for target_context in linker_elf_contexts:
            target_requirement = (
                target_context.elf_requirement
            )

            parsed_target_source = (
                target_requirement
                .source
                .source
            )

            target_filesystem_source = (
                parsed_target_source
                .filesystem_source
            )

            #
            # This index represents Android-visible targets that may satisfy
            # an APEX payload symlink in the effective post-boot linker
            # filesystem.
            #
            # CPIO-extracted filesystem sources are canonical boot/ramdisk
            # evidence. Their absolute Android paths are valid inside that
            # ramdisk namespace, but they must not compete with mounted
            # post-boot filesystem identities merely because both project,
            # for example, "/system/lib64/libbase.so".
            #
            # Preserve those ELF requirements in Universe; exclude them only
            # from this post-boot APEX-local alias target population.
            #
            if (
                target_filesystem_source is not None
                and (
                    target_filesystem_source
                    .artifact
                    .operation
                    is ExtractionOperation.CPIO_EXTRACTION
                )
            ):
                continue

            target_paths = []

            if (
                parsed_target_source
                .android_path
                is not None
            ):
                target_paths.append(
                    parsed_target_source
                    .android_path
                )

            target_paths.extend(
                alias.android_path
                for alias
                in target_requirement.filesystem_aliases
            )

            for target_path in target_paths:
                path_index.setdefault(
                    (
                        runtime_key(
                            target_context.runtime_context
                        ),
                        target_path.as_posix(),
                    ),
                    [],
                ).append(
                    target_context
                )

        for (
            filesystem_identity,
            client_apex,
        ) in sorted(
            apex_by_filesystem_identity.items(),
            key=lambda item: (
                item[1].apex_name,
                item[0],
            ),
        ):
            alias_filesystem_source = (
                filesystem_by_identity[
                    filesystem_identity
                ]
            )

            alias_runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_filesystem_source(
                    alias_filesystem_source
                )
            )

            if not (
                AndroidUniverseRuntimeContextResolver
                .same_runtime(
                    client_apex.runtime_context,
                    alias_runtime_context,
                )
            ):
                raise ValueError(
                    "canonical APEX payload filesystem and exact "
                    "APEX requirement disagree on runtime identity"
                )

            try:
                inventory_entry = (
                    filesystem_inventory
                    .entry_for_artifact(
                        alias_filesystem_source.artifact
                    )
                )
            except KeyError:
                continue

            entries = (
                inventory_entry
                .result
                .metadata
                .entries
            )

            for alias_entry in sorted(
                (
                    entry
                    for entry
                    in entries.values()
                    if (
                        entry.entry_type
                        is FilesystemEntryType.SYMLINK
                    )
                ),
                key=lambda value: value.path,
            ):
                terminal_target = cls._terminal_target_path(
                    entries=entries,
                    alias_entry=alias_entry,
                )

                if terminal_target is None:
                    continue

                #
                # /apex/<name>/... is handled by the existing opposite-
                # direction reconciliation above.
                #
                if (
                    cls._apex_target_identity(
                        terminal_target
                    )
                    is not None
                ):
                    continue

                matching_contexts = tuple(
                    path_index.get(
                        (
                            runtime_key(
                                alias_runtime_context
                            ),
                            PurePosixPath(
                                terminal_target
                            ).as_posix(),
                        ),
                        (),
                    )
                )

                #
                # Remove accidental duplicate references to the same exact
                # target ELF context while preserving genuine ambiguity.
                #
                unique_matching_contexts = []
                seen_context_ids = set()

                for target_context in matching_contexts:
                    target_source = (
                        target_context
                        .elf_requirement
                        .source
                        .source
                    )

                    if (
                        target_source.filesystem_source
                        is alias_filesystem_source
                    ):
                        continue

                    identity = id(
                        target_context
                        .elf_requirement
                    )

                    if identity in seen_context_ids:
                        continue

                    seen_context_ids.add(
                        identity
                    )

                    unique_matching_contexts.append(
                        target_context
                    )

                if len(
                    unique_matching_contexts
                ) != 1:
                    continue

                target_context = (
                    unique_matching_contexts[0]
                )

                target_requirement = (
                    target_context.elf_requirement
                )

                target_elf = (
                    target_requirement.source
                )

                target_entry = (
                    target_elf
                    .source
                    .metadata_entry
                )

                if target_entry is None:
                    continue

                alias_host_path = (
                    AndroidUniverseElfFilesystemAliasReconciler
                    ._materialized_path(
                        filesystem_source=(
                            alias_filesystem_source
                        ),
                        metadata_entry=alias_entry,
                    )
                )

                projected: dict[
                    PurePosixPath,
                    list,
                ] = {}

                for view in alias_filesystem_source.views:
                    try:
                        payload_path = (
                            view.android_path_for(
                                alias_host_path
                            )
                        )
                    except ValueError:
                        continue

                    projected.setdefault(
                        payload_path,
                        [],
                    ).append(
                        view
                    )

                for (
                    payload_path,
                    views,
                ) in projected.items():
                    alias = (
                        AndroidUniverseElfApexLocalAlias(
                            source=target_elf,
                            client_apex_requirement=(
                                client_apex
                            ),
                            alias_entry=alias_entry,
                            target_entry=target_entry,
                            alias_filesystem_source=(
                                alias_filesystem_source
                            ),
                            filesystem_views=tuple(
                                sorted(
                                    views,
                                    key=lambda value: (
                                        value
                                        .android_prefix
                                        .as_posix(),
                                        value
                                        .filesystem
                                        .root
                                        .as_posix(),
                                    ),
                                )
                            ),
                            payload_path=(
                                payload_path
                            ),
                            target_android_path=(
                                PurePosixPath(
                                    terminal_target
                                )
                            ),
                        )
                    )

                    apex_local_aliases_by_requirement.setdefault(
                        id(target_requirement),
                        [],
                    ).append(
                        alias
                    )

        replacement_by_identity: dict[
            int,
            AndroidUniverseElfRequirement,
        ] = {}

        updated_requirements = []

        for requirement in elf_requirements:
            additions = aliases_by_requirement.get(
                id(requirement),
                [],
            )

            apex_local_additions = (
                apex_local_aliases_by_requirement
                .get(
                    id(requirement),
                    [],
                )
            )

            if (
                not additions
                and not apex_local_additions
            ):
                updated_requirements.append(
                    requirement
                )
                continue

            by_path = {
                alias.android_path: alias
                for alias
                in requirement.filesystem_aliases
            }

            for alias in additions:
                existing = by_path.get(
                    alias.android_path
                )

                if existing is None:
                    by_path[
                        alias.android_path
                    ] = alias
                    continue

                if (
                    existing.alias_entry
                    is alias.alias_entry
                    and existing.target_entry
                    is alias.target_entry
                    and existing.alias_filesystem_source
                    is alias.alias_filesystem_source
                ):
                    continue

                raise ValueError(
                    "distinct canonical ELF aliases project to "
                    "the same Android-visible path during APEX "
                    "cross-filesystem reconciliation: "
                    f"elf={requirement.source.source.identity_key!r}, "
                    f"path={alias.android_path.as_posix()!r}"
                )

            apex_local_by_key = {
                (
                    id(
                        alias.client_apex_requirement
                    ),
                    alias.payload_path,
                ): alias
                for alias
                in requirement.apex_local_aliases
            }

            for alias in apex_local_additions:
                key = (
                    id(
                        alias.client_apex_requirement
                    ),
                    alias.payload_path,
                )

                existing = (
                    apex_local_by_key.get(
                        key
                    )
                )

                if existing is None:
                    apex_local_by_key[
                        key
                    ] = alias
                    continue

                if (
                    existing.alias_entry
                    is alias.alias_entry
                    and existing.target_entry
                    is alias.target_entry
                    and existing.alias_filesystem_source
                    is alias.alias_filesystem_source
                ):
                    continue

                raise ValueError(
                    "distinct canonical APEX-local ELF aliases "
                    "project to the same exact client APEX payload path: "
                    f"elf={requirement.source.source.identity_key!r}, "
                    f"apex={alias.client_apex_requirement.apex_name!r}, "
                    f"path={alias.payload_path.as_posix()!r}"
                )

            updated = replace(
                requirement,
                filesystem_aliases=tuple(
                    sorted(
                        by_path.values(),
                        key=lambda value: (
                            value.android_path.as_posix(),
                            value.alias_entry.path,
                        ),
                    )
                ),
                apex_local_aliases=tuple(
                    sorted(
                        apex_local_by_key.values(),
                        key=lambda value: (
                            value
                            .client_apex_requirement
                            .apex_name,
                            value.payload_path.as_posix(),
                            value
                            .target_android_path
                            .as_posix(),
                        ),
                    )
                ),
            )

            replacement_by_identity[
                id(requirement)
            ] = updated

            updated_requirements.append(updated)

        updated_contexts = tuple(
            (
                replace(
                    context,
                    elf_requirement=(
                        replacement_by_identity[
                            id(context.elf_requirement)
                        ]
                    ),
                )
                if id(context.elf_requirement)
                in replacement_by_identity
                else context
            )
            for context
            in linker_elf_contexts
        )

        return (
            tuple(updated_requirements),
            updated_contexts,
        )
