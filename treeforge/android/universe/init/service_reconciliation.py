from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportResolution,
    android_init_inapplicable_source_paths,
)
from treeforge.android.universe.runtime_context.model import (
    AndroidUniverseRuntimeContext,
    AndroidUniverseRuntimeContextKind,
)
from treeforge.android.universe.runtime_context.resolver import (
    AndroidUniverseRuntimeContextResolver,
)


class AndroidUniverseInitSourceContext(
    StrEnum
):
    """
    Runtime/source domain containing one canonical INIT declaration.

    These are Android architectural source domains rather than device-specific
    service classifications.
    """

    FILESYSTEM = "filesystem"
    INIT_BOOT = "init_boot"
    VENDOR_BOOT = "vendor_boot"


class AndroidUniverseInitServiceResolutionStatus(
    StrEnum
):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    INAPPLICABLE = "inapplicable"


def android_init_source_context(
    path: Path,
) -> AndroidUniverseInitSourceContext:
    """
    Determine canonical INIT source context from Extraction provenance.

    Boot-family ramdisks remain distinct from ordinary filesystem sources.
    The extraction workspace path is provenance produced by TreeForge itself,
    not an OEM/device naming rule.
    """

    if not isinstance(
        path,
        Path,
    ):
        raise TypeError(
            "path must be a Path"
        )

    parts = path.parts

    for index, part in enumerate(
        parts
    ):
        if part != "ramdisk":
            continue

        if index + 1 >= len(parts):
            break

        owner = parts[
            index + 1
        ]

        if owner == "init_boot":
            return (
                AndroidUniverseInitSourceContext
                .INIT_BOOT
            )

        if owner == "vendor_boot":
            return (
                AndroidUniverseInitSourceContext
                .VENDOR_BOOT
            )

    return (
        AndroidUniverseInitSourceContext
        .FILESYSTEM
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitServiceResolution:
    """
    Canonical effective-service conclusion for one name in one source context.

    Every original declaration is retained. ``effective_services`` contains
    only declarations that remain candidates after intrinsic INIT override
    semantics are applied.
    """

    name: str
    source_context: AndroidUniverseInitSourceContext
    runtime_context: AndroidUniverseRuntimeContext

    declarations: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ]

    effective_services: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ]

    status: AndroidUniverseInitServiceResolutionStatus

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ) or not self.name:
            raise ValueError(
                "name must be a non-empty string"
            )

        if not isinstance(
            self.source_context,
            AndroidUniverseInitSourceContext,
        ):
            raise TypeError(
                "source_context must be an "
                "AndroidUniverseInitSourceContext"
            )

        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        for field_name, values in (
            (
                "declarations",
                self.declarations,
            ),
            (
                "effective_services",
                self.effective_services,
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
                    AndroidUniverseInitServiceRequirement,
                )
                for value in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "AndroidUniverseInitServiceRequirement "
                    "instances"
                )

        if not self.declarations:
            raise ValueError(
                "declarations must not be empty"
            )

        if any(
            service.name != self.name
            for service
            in self.declarations
        ):
            raise ValueError(
                "all declarations must match name"
            )

        if any(
            (
                android_init_source_context(
                    service.source_path
                )
                is not self.source_context
            )
            for service
            in self.declarations
        ):
            raise ValueError(
                "all declarations must match source_context"
            )

        for service in self.declarations:
            if service.filesystem_source is None:
                declaration_runtime_context = (
                    AndroidUniverseRuntimeContext(
                        kind=(
                            AndroidUniverseRuntimeContextKind
                            .ROOT
                        ),
                    )
                )
            else:
                declaration_runtime_context = (
                    AndroidUniverseRuntimeContextResolver
                    .resolve_filesystem_source(
                        service.filesystem_source
                    )
                )

            if not (
                AndroidUniverseRuntimeContextResolver
                .same_runtime(
                    declaration_runtime_context,
                    self.runtime_context,
                )
            ):
                raise ValueError(
                    "all declarations must match runtime_context"
                )

        declaration_ids = {
            id(service)
            for service
            in self.declarations
        }

        if any(
            id(service)
            not in declaration_ids
            for service
            in self.effective_services
        ):
            raise ValueError(
                "effective_services must be drawn from declarations"
            )

        if not self.effective_services:
            expected_status = (
                AndroidUniverseInitServiceResolutionStatus
                .INAPPLICABLE
            )

        elif len(
            self.effective_services
        ) == 1:
            expected_status = (
                AndroidUniverseInitServiceResolutionStatus
                .RESOLVED
            )

        else:
            expected_status = (
                AndroidUniverseInitServiceResolutionStatus
                .AMBIGUOUS
            )

        if self.status is not expected_status:
            raise ValueError(
                "status does not match effective service cardinality"
            )

    @property
    def resolution_id(
        self,
    ) -> str:
        if self.runtime_context.is_root:
            runtime_identity = "root"
        else:
            partition_container = (
                self.runtime_context
                .partition_container
            )

            if partition_container is None:
                raise ValueError(
                    "nested runtime context must preserve "
                    "partition_container"
                )

            if not partition_container.content_sha256:
                raise ValueError(
                    "nested runtime partition container must "
                    "preserve canonical content_sha256"
                )

            runtime_identity = (
                "nested:"
                f"{partition_container.content_sha256}"
            )

        return (
            "init-service-resolution:"
            f"{runtime_identity}:"
            f"{self.source_context.value}:"
            f"{self.name}"
        )


class AndroidUniverseInitServiceReconciler:
    """
    Reconcile raw INIT service declarations into context-local namespaces.

    A unique ``override`` declaration supersedes non-override declarations
    having the same name in the same source context. Multiple override
    declarations remain ambiguous because source/import ordering must not be
    invented when Universe lacks evidence.

    Definitions from different boot/runtime contexts never compete here.
    """

    def reconcile(
        self,
        services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        *,
        import_resolutions: tuple[
            AndroidUniverseInitImportResolution,
            ...,
        ] = (),
    ) -> tuple[
        AndroidUniverseInitServiceResolution,
        ...,
    ]:
        if not isinstance(
            services,
            tuple,
        ):
            raise TypeError(
                "services must be a tuple"
            )

        if not all(
            isinstance(
                service,
                AndroidUniverseInitServiceRequirement,
            )
            for service in services
        ):
            raise TypeError(
                "services must contain only "
                "AndroidUniverseInitServiceRequirement instances"
            )

        if not isinstance(
            import_resolutions,
            tuple,
        ):
            raise TypeError(
                "import_resolutions must be a tuple"
            )

        inapplicable_source_paths = (
            android_init_inapplicable_source_paths(
                import_resolutions
            )
        )

        grouped = defaultdict(
            list
        )

        runtime_context_by_group = {}

        for service in services:
            if service.filesystem_source is None:
                runtime_context = (
                    AndroidUniverseRuntimeContext(
                        kind=(
                            AndroidUniverseRuntimeContextKind
                            .ROOT
                        ),
                    )
                )
            else:
                runtime_context = (
                    AndroidUniverseRuntimeContextResolver
                    .resolve_filesystem_source(
                        service.filesystem_source
                    )
                )

            if runtime_context.is_root:
                runtime_key = (
                    "root",
                    None,
                )
            else:
                partition_container = (
                    runtime_context
                    .partition_container
                )

                if partition_container is None:
                    raise ValueError(
                        "nested runtime context must preserve "
                        "partition_container"
                    )

                runtime_key = (
                    "nested_partition_set",
                    id(partition_container),
                )

            source_context = (
                android_init_source_context(
                    service.source_path
                )
            )

            group_key = (
                runtime_key,
                source_context,
                service.name,
            )

            grouped[
                group_key
            ].append(
                service
            )

            existing_runtime_context = (
                runtime_context_by_group.get(
                    group_key
                )
            )

            if existing_runtime_context is None:
                runtime_context_by_group[
                    group_key
                ] = runtime_context

            elif not (
                AndroidUniverseRuntimeContextResolver
                .same_runtime(
                    existing_runtime_context,
                    runtime_context,
                )
            ):
                raise ValueError(
                    "INIT service group merged distinct "
                    "runtime contexts"
                )

        conclusions = []

        for (
            group_key,
            declarations,
        ) in grouped.items():
            (
                _runtime_key,
                source_context,
                name,
            ) = group_key

            runtime_context = (
                runtime_context_by_group[
                    group_key
                ]
            )
            declarations = tuple(
                sorted(
                    declarations,
                    key=lambda service: (
                        service.requirement_id
                    ),
                )
            )

            applicable_declarations = tuple(
                service
                for service
                in declarations
                if (
                    service.source_path
                    not in inapplicable_source_paths
                )
            )

            overrides = tuple(
                service
                for service
                in applicable_declarations
                if service.semantics.override
            )

            if overrides:
                effective_services = (
                    overrides
                )
            else:
                effective_services = (
                    applicable_declarations
                )

            if not effective_services:
                status = (
                    AndroidUniverseInitServiceResolutionStatus
                    .INAPPLICABLE
                )

            elif len(
                effective_services
            ) == 1:
                status = (
                    AndroidUniverseInitServiceResolutionStatus
                    .RESOLVED
                )

            else:
                status = (
                    AndroidUniverseInitServiceResolutionStatus
                    .AMBIGUOUS
                )

            conclusions.append(
                AndroidUniverseInitServiceResolution(
                    name=name,
                    source_context=source_context,
                    runtime_context=runtime_context,
                    declarations=declarations,
                    effective_services=(
                        effective_services
                    ),
                    status=status,
                )
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.resolution_id,
                ),
            )
        )
