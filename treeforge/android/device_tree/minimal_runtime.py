from __future__ import annotations

from collections import deque
from pathlib import PurePosixPath

from treeforge.android.device_tree.product_makefile import (
    AndroidDeviceTreeProductCopyFile,
)


#
# Current bring-up policy:
#
# Build the smallest useful AOSP device image from canonical TreeForge
# evidence.  Full factory userspace reproduction is deliberately not the goal
# of this policy.
#
# Framework-side factory payloads remain preserved in TreeForge's generated
# source tree/evidence but do not participate in the minimal AOSP product.
#
# Device-side runtime remains eligible when it is:
# - vendor/odm configuration copied from canonical requirements;
# - reconstructed vendor/odm init/fstab/ueventd source;
# - an ELF executable referenced by canonical INIT service declarations;
# - an ELF dependency of one of those service executables;
# - a small class of dynamically loaded hardware/EGL plugins which cannot be
#   recovered from DT_NEEDED closure alone.
#
_MINIMAL_DEVICE_PARTITIONS = frozenset(
    {
        "vendor",
        "odm",
    }
)

#
# Runtime ELF selection is evidence-driven rather than device-partition
# driven. A canonical INIT service may execute code from system,
# system_ext, product, vendor, or odm.
#
_MINIMAL_RUNTIME_ELF_PARTITIONS = frozenset(
    {
        "system",
        "system_ext",
        "product",
        "vendor",
        "odm",
    }
)

#
# Factory-backed direct-copy promotion is intentionally narrower than the
# complete runtime ELF namespace. System remains source-built AOSP.
# Device/runtime helpers in system_ext/product/vendor/odm may be preserved
# when canonical INIT directly executes them and no ELF realization owns the
# path.
#
_MINIMAL_RUNTIME_COPY_PROMOTION_PARTITIONS = frozenset(
    {
        "system_ext",
        "product",
        "vendor",
        "odm",
    }
)

#
# Android-version source-provider contracts whose installed runtime payload
# cannot be recovered from a TreeForge ELF realization alone.
#
# These are selected only when the corresponding canonical INIT runtime path
# is actually required by the reconstructed device. They are therefore
# versioned platform facts, not unconditional product baggage.
#
# Android 15 gs201 selects otapreopt_script; that module requires
# otapreopt_slot and installs the /system/bin/otapreopt_slot runtime invoked
# by otapreopt.rc.
#
_ANDROID_15_INIT_RUNTIME_SOURCE_PROVIDERS = (
    (
        "/system/bin/otapreopt_slot",
        "otapreopt_script",
    ),
)

#
# Generated source participation is distinct from ordinary factory-payload
# copy participation.
#
# INIT and ueventd remain device-side vendor/odm configuration in the
# minimum product. FSTAB additionally admits product-owned canonical source:
# this is reconstructed Android build/runtime configuration, not promotion
# of arbitrary factory product payloads.
#
_MINIMAL_GENERATED_SOURCE_PARTITIONS = {
    "init": _MINIMAL_DEVICE_PARTITIONS,
    "fstab": (
        _MINIMAL_DEVICE_PARTITIONS
        | frozenset(
            {
                "product",
            }
        )
    ),
    "ueventd": _MINIMAL_DEVICE_PARTITIONS,
}

_MINIMAL_GENERATED_SOURCE_FAMILIES = frozenset(
    _MINIMAL_GENERATED_SOURCE_PARTITIONS
)

_DYNAMIC_RUNTIME_PREFIXES = (
    "/vendor/lib/hw/",
    "/vendor/lib64/hw/",
    "/vendor/lib/egl/",
    "/vendor/lib64/egl/",
    "/odm/lib/hw/",
    "/odm/lib64/hw/",
    "/odm/lib/egl/",
    "/odm/lib64/egl/",
)

_DYNAMIC_RUNTIME_BASENAME_PREFIXES = (
    "sensors.",
)


def _path_parts(
    path: PurePosixPath,
) -> tuple[str, ...]:
    parts = path.parts

    if path.is_absolute():
        parts = parts[1:]

    return tuple(parts)


def _normalize_android_runtime_path(
    path: PurePosixPath,
) -> PurePosixPath:
    """
    Normalize compatibility spellings into one Android runtime path.

    Modern Android mounts product, system_ext, and vendor at the root while
    /system/{product,system_ext,vendor} may still appear in canonical source
    and factory-derived evidence.
    """
    if not isinstance(path, PurePosixPath):
        raise TypeError(
            "runtime path must be a PurePosixPath"
        )

    parts = _path_parts(path)

    if (
        len(parts) >= 2
        and parts[0] == "system"
        and parts[1]
        in {
            "product",
            "system_ext",
            "vendor",
        }
    ):
        return PurePosixPath(
            "/",
            *parts[1:],
        )

    return PurePosixPath(
        "/",
        *parts,
    )


def _logical_android_path(
    *,
    partition: str,
    installed_android_path: str,
) -> PurePosixPath:
    """
    Convert TreeForge's canonical partition-relative or Android-root-relative
    installed path into one normalized Android runtime namespace path.

    Examples:
        vendor + /bin/foo      -> /vendor/bin/foo
        vendor + /vendor/bin/foo -> /vendor/bin/foo
        product + /app/Foo     -> /product/app/Foo
    """
    path = PurePosixPath(
        installed_android_path
    )

    parts = _path_parts(path)

    if (
        parts
        and parts[0] == partition
    ):
        logical = PurePosixPath(
            "/",
            *parts,
        )

    else:
        logical = PurePosixPath(
            "/",
            partition,
            *parts,
        )

    return _normalize_android_runtime_path(
        logical
    )


def _projection_install_identity(
    projection,
) -> tuple[
    str,
    PurePosixPath,
] | None:
    """
    Derive minimum-runtime installation identity for generated source.

    Participation is family-specific and independent from the narrower
    ordinary factory-payload copy policy.
    """
    family = getattr(
        projection,
        "family",
        None,
    )

    allowed_partitions = (
        _MINIMAL_GENERATED_SOURCE_PARTITIONS.get(
            family
        )
    )

    if allowed_partitions is None:
        return None

    android_path = projection.android_path

    if android_path is None:
        return None

    normalized = (
        _normalize_android_runtime_path(
            android_path
        )
    )

    parts = _path_parts(
        normalized
    )

    if not parts:
        return None

    partition = parts[0]

    if partition not in allowed_partitions:
        return None

    relative = PurePosixPath(
        *parts[1:]
    )

    if not relative.parts:
        return None

    return (
        partition,
        relative,
    )



def _target_copy_root(
    partition: str,
) -> str:
    roots = {
        "vendor": "$(TARGET_COPY_OUT_VENDOR)",
        "odm": "$(TARGET_COPY_OUT_ODM)",
        "system_ext": "$(TARGET_COPY_OUT_SYSTEM_EXT)",
        "product": "$(TARGET_COPY_OUT_PRODUCT)",
    }

    root = roots.get(
        partition
    )

    if root is not None:
        return root

    raise ValueError(
        "minimum runtime copy requested for unsupported partition: "
        f"{partition!r}"
    )




def _canonical_init_runtime_roots(
    *,
    universe,
) -> tuple[
    tuple[
        PurePosixPath,
        tuple[object, ...],
        tuple[str, ...],
    ],
    ...,
]:
    """
    Return every concrete canonical INIT executable root relevant to the
    reconstructed runtime.

    Sources:
    - effective/substantiated INIT service executables;
    - concrete exec / exec_background action commands.

    Proven-inapplicable property-selected INIT source alternatives are
    excluded using Universe-owned applicability evidence.

    Factory payload evidence is retained with each root when available so
    non-ELF device helpers can be promoted without guessing source-module
    identity.
    """
    from treeforge.android.universe.init.action_command.semantics import (
        AndroidUniverseInitActionCommandExecSemantics,
    )
    from treeforge.android.universe.init.import_resolution import (
        android_init_inapplicable_source_paths,
    )
    from treeforge.android.universe.relationships.service_substantiation import (
        AndroidUniverseInitServiceSubstantiationReconciler,
    )

    records = {}

    def add_root(
        *,
        executable,
        evidence,
        identity_text: str,
    ) -> None:
        executable_text = (
            executable.as_posix()
            if isinstance(executable, PurePosixPath)
            else str(executable)
        )

        if (
            not executable_text
            or "${" in executable_text
        ):
            return

        raw_path = PurePosixPath(
            executable_text
        )

        if not raw_path.is_absolute():
            return

        normalized = (
            _normalize_android_runtime_path(
                raw_path
            )
        )

        record = records.setdefault(
            normalized,
            {
                "evidence": {},
                "identities": set(),
            },
        )

        record["identities"].add(
            identity_text
        )

        for item in evidence:
            host_path = getattr(
                item,
                "host_path",
                None,
            )

            if (
                host_path is None
                or not host_path.is_file()
            ):
                continue

            evidence_path = getattr(
                item,
                "android_path",
                None,
            )

            if evidence_path is None:
                continue

            evidence_path = (
                _normalize_android_runtime_path(
                    evidence_path
                )
            )

            if evidence_path != normalized:
                continue

            record["evidence"][
                host_path.as_posix()
            ] = item

    #
    # Existing canonical service substantiations remain first-class roots.
    #
    for substantiation in (
        universe.init_service_substantiations
    ):
        add_root(
            executable=(
                substantiation.executable_path
            ),
            evidence=(
                substantiation.executable_evidence
            ),
            identity_text=(
                "service:"
                f"{substantiation.service.requirement_id}"
            ),
        )

    #
    # Action commands are already semantically interpreted by Universe.
    # Consume that model rather than reparsing RC source.
    #
    inapplicable_source_paths = (
        android_init_inapplicable_source_paths(
            universe.init_import_resolutions
        )
    )

    evidence_resolver = (
        AndroidUniverseInitServiceSubstantiationReconciler()
    )

    source_inventory = (
        universe.parsing.source_inventory
    )

    for action in (
        universe.init_action_requirements
    ):
        if (
            action.source_path
            in inapplicable_source_paths
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
                AndroidUniverseInitActionCommandExecSemantics,
            ):
                continue

            executable_text = (
                semantics.executable
            )

            if (
                not executable_text
                or "${" in executable_text
            ):
                continue

            executable = PurePosixPath(
                executable_text
            )

            if not executable.is_absolute():
                continue

            normalized = (
                _normalize_android_runtime_path(
                    executable
                )
            )

            evidence = (
                evidence_resolver._resolve_executable(
                    executable=normalized,
                    source_inventory=source_inventory,
                )
            )

            line = (
                command_requirement
                .command
                .location
                .line
            )

            add_root(
                executable=normalized,
                evidence=evidence,
                identity_text=(
                    "action:"
                    f"{action.requirement_id}:"
                    f"{line}:"
                    f"{semantics.keyword}"
                ),
            )

    return tuple(
        (
            runtime_path,
            tuple(
                record["evidence"][key]
                for key in sorted(
                    record["evidence"]
                )
            ),
            tuple(
                sorted(
                    record["identities"]
                )
            ),
        )
        for runtime_path, record
        in sorted(
            records.items(),
            key=lambda item: (
                item[0].as_posix()
            ),
        )
    )


def select_minimal_runtime_platform_packages(
    *,
    universe,
    android_version: str,
) -> tuple[
    str,
    ...,
]:
    """
    Select source-built Android platform modules required by canonical INIT
    runtime paths when no TreeForge build realization can express ownership.

    This is deliberately evidence-gated: a provider is selected only when the
    corresponding runtime path is present in canonical INIT semantics.
    """
    if (
        not isinstance(
            android_version,
            str,
        )
        or not android_version
    ):
        raise ValueError(
            "android_version must be a non-empty string"
        )

    if (
        android_version != "15"
        and not android_version.startswith(
            "15."
        )
    ):
        raise ValueError(
            "minimum INIT runtime source-provider selection currently "
            "supports Android 15 only"
        )

    runtime_paths = {
        runtime_path.as_posix()
        for (
            runtime_path,
            _,
            _,
        )
        in _canonical_init_runtime_roots(
            universe=universe,
        )
    }

    providers = (
        _ANDROID_15_INIT_RUNTIME_SOURCE_PROVIDERS
    )

    return tuple(
        sorted(
            {
                module_name
                for (
                    runtime_path,
                    module_name,
                )
                in providers
                if runtime_path
                in runtime_paths
            }
        )
    )



def select_minimal_runtime_copy_files(
    *,
    copy_files: tuple[
        AndroidDeviceTreeProductCopyFile,
        ...,
    ],
    projections: tuple[
        object,
        ...,
    ],
    universe,
    modules: tuple[
        object,
        ...,
    ],
    identity,
    output_root,
) -> tuple[
    AndroidDeviceTreeProductCopyFile,
    ...,
]:
    """
    Select the minimum filesystem-copy surface for current AOSP bring-up.

    Existing canonical vendor/odm COPY_FILE realizations remain eligible.

    Factory system payloads remain excluded from product participation.
    Concrete INIT-executed device helpers in system_ext/product/vendor/odm
    may be promoted from exact factory evidence when no ELF realization owns
    the runtime path.

    Both service executables and exec/exec_background action executables are
    treated as canonical INIT runtime roots.
    """
    if not isinstance(
        copy_files,
        tuple,
    ):
        raise TypeError(
            "copy_files must be a tuple"
        )

    if not isinstance(
        projections,
        tuple,
    ):
        raise TypeError(
            "projections must be a tuple"
        )

    if not isinstance(
        modules,
        tuple,
    ):
        raise TypeError(
            "modules must be a tuple"
        )

    by_destination = {}

    #
    # Keep normal device-side direct copies.
    #
    for item in copy_files:
        if (
            item.installed_partition
            not in _MINIMAL_DEVICE_PARTITIONS
        ):
            continue

        by_destination[
            item.destination
        ] = item

    #
    # Build exact runtime-path ownership for every reconstructed ELF module.
    #
    elf_runtime_paths = set()

    for module in modules:
        if (
            module.build_partition
            not in _MINIMAL_RUNTIME_ELF_PARTITIONS
        ):
            continue

        elf_runtime_paths.add(
            _logical_android_path(
                partition=module.build_partition,
                installed_android_path=(
                    module.installed_android_path
                ),
            )
        )

    from hashlib import sha256
    from shutil import copyfile as _copyfile

    #
    # Promote concrete non-ELF INIT runtime roots from exact factory evidence.
    #
    for (
        normalized,
        executable_evidence,
        root_identities,
    ) in _canonical_init_runtime_roots(
        universe=universe,
    ):
        parts = _path_parts(
            normalized
        )

        if (
            not parts
            or parts[0]
            not in _MINIMAL_RUNTIME_COPY_PROMOTION_PARTITIONS
        ):
            continue

        #
        # An ELF realization owns this path. Keep it under ELF/provider
        # reconciliation rather than creating duplicate copy ownership.
        #
        if normalized in elf_runtime_paths:
            continue

        partition = parts[0]

        relative = PurePosixPath(
            *parts[1:]
        )

        if not relative.parts:
            continue

        evidence_by_host_path = {}

        for evidence in (
            executable_evidence
        ):
            evidence_path = (
                _normalize_android_runtime_path(
                    evidence.android_path
                )
            )

            if evidence_path != normalized:
                continue

            host_path = (
                evidence.host_path
            )

            if not host_path.is_file():
                continue

            evidence_by_host_path[
                host_path.as_posix()
            ] = evidence

        if not evidence_by_host_path:
            #
            # Source-built platform/provider ownership may still satisfy it.
            #
            continue

        if len(evidence_by_host_path) != 1:
            raise ValueError(
                "minimum runtime INIT root has ambiguous "
                "factory payload evidence: "
                f"{normalized} -> "
                f"{sorted(evidence_by_host_path)}"
            )

        evidence = next(
            iter(
                evidence_by_host_path.values()
            )
        )

        source_path = PurePosixPath(
            (
                identity.proprietary_root
                / partition
                / relative
            ).as_posix()
        )

        destination = (
            f"{_target_copy_root(partition)}/"
            f"{relative.as_posix()}"
        )

        if destination in by_destination:
            continue

        materialized = (
            output_root
            / source_path.as_posix()
        )

        materialized.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        _copyfile(
            evidence.host_path,
            materialized,
        )

        identity_digest = (
            sha256(
                "\n".join(
                    root_identities
                ).encode(
                    "utf-8"
                )
            )
            .hexdigest()[:24]
        )

        by_destination[
            destination
        ] = AndroidDeviceTreeProductCopyFile(
            representation_id=(
                "minimal-runtime:init-root:"
                f"{identity_digest}"
            ),
            source_path=source_path,
            installed_partition=partition,
            installed_android_path=(
                normalized.as_posix()
            ),
            destination=destination,
        )

    #
    # Generated source is the source-build representation AOSP consumes for
    # reconstructed configuration families.
    #
    for projection in projections:
        if (
            projection.family
            not in _MINIMAL_GENERATED_SOURCE_FAMILIES
        ):
            continue

        projection_identity = (
            _projection_install_identity(
                projection
            )
        )

        if projection_identity is None:
            continue

        partition, relative = (
            projection_identity
        )

        destination = (
            f"{_target_copy_root(partition)}/"
            f"{relative.as_posix()}"
        )

        installed_android_path = (
            PurePosixPath(
                "/",
                partition,
                *relative.parts,
            )
            .as_posix()
        )

        by_destination[
            destination
        ] = (
            AndroidDeviceTreeProductCopyFile(
                representation_id=(
                    projection.representation_id
                ),
                source_path=(
                    projection.destination
                ),
                installed_partition=(
                    partition
                ),
                installed_android_path=(
                    installed_android_path
                ),
                destination=destination,
            )
        )

    result = tuple(
        sorted(
            by_destination.values(),
            key=lambda item: (
                item.destination,
                item.source_path.as_posix(),
                item.representation_id,
            ),
        )
    )

    if not result:
        raise ValueError(
            "minimum runtime policy produced no filesystem copy files"
        )

    return result




def select_minimal_runtime_elf_packages(
    *,
    universe,
    modules: tuple[
        object,
        ...,
    ],
) -> tuple[
    str,
    ...,
]:
    """
    Select TreeForge-generated ELF modules required for minimal device runtime.

    Roots:
    - every concrete canonical INIT service executable;
    - every concrete canonical INIT exec/exec_background executable;
    - dynamically loaded hardware/EGL plugin modules.

    Closure:
    - recursively consume exact Device Tree dependency_realization_ids.

    Arbitrary factory tools/tests remain excluded merely for existing.
    """
    if not isinstance(
        modules,
        tuple,
    ):
        raise TypeError(
            "modules must be a tuple"
        )

    by_runtime_path = {}
    by_realization_id = {}

    for module in modules:
        if (
            module.build_partition
            not in _MINIMAL_RUNTIME_ELF_PARTITIONS
        ):
            continue

        runtime_path = (
            _logical_android_path(
                partition=module.build_partition,
                installed_android_path=(
                    module.installed_android_path
                ),
            )
        )

        existing = (
            by_runtime_path.get(
                runtime_path
            )
        )

        if (
            existing is not None
            and existing.module_name
            != module.module_name
        ):
            raise ValueError(
                "multiple TreeForge ELF modules claim one runtime path: "
                f"{runtime_path}"
            )

        by_runtime_path[
            runtime_path
        ] = module

        realization_id = (
            module
            .realization
            .realization_id
        )

        if (
            realization_id
            in by_realization_id
        ):
            raise ValueError(
                "duplicate ELF realization identity in minimum "
                f"runtime selection: {realization_id}"
            )

        by_realization_id[
            realization_id
        ] = module

    root_realization_ids = set()

    #
    # Canonical INIT service + action executable roots.
    #
    for (
        normalized,
        _,
        _,
    ) in _canonical_init_runtime_roots(
        universe=universe,
    ):
        parts = _path_parts(
            normalized
        )

        if (
            not parts
            or parts[0]
            not in _MINIMAL_RUNTIME_ELF_PARTITIONS
        ):
            continue

        module = (
            by_runtime_path.get(
                normalized
            )
        )

        if module is None:
            #
            # Source-built AOSP modules or direct-copy payloads can satisfy
            # runtime roots outside the reconstructed ELF surface.
            #
            continue

        root_realization_ids.add(
            module.realization.realization_id
        )

    #
    # HAL/graphics dlopen providers cannot be recovered solely from DT_NEEDED.
    #
    for runtime_path, module in (
        by_runtime_path.items()
    ):
        text = runtime_path.as_posix()
        basename = runtime_path.name

        dynamic_root = any(
            text.startswith(prefix)
            for prefix
            in _DYNAMIC_RUNTIME_PREFIXES
        )

        if not dynamic_root:
            dynamic_root = any(
                basename.startswith(prefix)
                for prefix
                in _DYNAMIC_RUNTIME_BASENAME_PREFIXES
            )

        if dynamic_root:
            root_realization_ids.add(
                module.realization.realization_id
            )

    if not root_realization_ids:
        raise ValueError(
            "minimum runtime policy found no canonical ELF roots"
        )

    queue = deque(
        sorted(
            root_realization_ids
        )
    )

    retained_realization_ids = set()

    while queue:
        realization_id = (
            queue.popleft()
        )

        if (
            realization_id
            in retained_realization_ids
        ):
            continue

        module = (
            by_realization_id.get(
                realization_id
            )
        )

        if module is None:
            continue

        retained_realization_ids.add(
            realization_id
        )

        for dependency_id in (
            module
            .realization
            .dependency_realization_ids
        ):
            dependency = (
                by_realization_id.get(
                    dependency_id
                )
            )

            if dependency is None:
                continue

            if (
                dependency.build_partition
                not in _MINIMAL_RUNTIME_ELF_PARTITIONS
            ):
                continue

            if (
                dependency_id
                not in retained_realization_ids
            ):
                queue.append(
                    dependency_id
                )

    packages = tuple(
        sorted(
            {
                by_realization_id[
                    realization_id
                ].module_name
                for realization_id
                in retained_realization_ids
            }
        )
    )

    if not packages:
        raise ValueError(
            "minimum runtime ELF dependency closure is empty"
        )

    return packages


def normalize_aosp_init_source(
    text: str,
) -> str:
    """
    Make Android init's implicit root service identity explicit.

    Reconstruction preserves the admitted INIT source syntax exactly.
    Device Tree, however, emits source that must pass AOSP source-build
    validation.

    For every service block:
    - preserve an existing ``user`` option exactly;
    - when no ``user`` option exists, append ``user root``;
    - never select services by name, device, partition, or count.

    Android init's runtime default is root when no service ``user`` option
    is specified, so this changes source spelling without changing runtime
    identity.
    """
    if not isinstance(text, str):
        raise TypeError(
            "INIT source text must be a string"
        )

    had_trailing_newline = text.endswith("\n")
    source_lines = text.splitlines()

    output: list[str] = []

    in_service = False
    service_has_user = False

    def finish_service() -> None:
        nonlocal in_service
        nonlocal service_has_user

        if (
            in_service
            and not service_has_user
        ):
            output.append(
                "    user root"
            )

        in_service = False
        service_has_user = False

    for line in source_lines:
        stripped = line.strip()

        is_service = (
            stripped.startswith(
                "service "
            )
        )

        is_top_level_boundary = (
            is_service
            or stripped.startswith(
                "on "
            )
            or stripped.startswith(
                "import "
            )
        )

        if (
            in_service
            and is_top_level_boundary
        ):
            finish_service()

        if is_service:
            in_service = True
            service_has_user = False

        elif in_service:
            tokens = stripped.split()

            if (
                tokens
                and tokens[0] == "user"
            ):
                service_has_user = True

        output.append(line)

    finish_service()

    normalized = "\n".join(
        output
    )

    if had_trailing_newline:
        normalized += "\n"

    return normalized

