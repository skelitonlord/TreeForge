from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
)
from treeforge.android.universe.init.import_requirement import (
    AndroidUniverseInitImportRequirement,
)
from treeforge.android.universe.init.property_expansion import (
    AndroidUniverseInitPropertyExpansion,
    AndroidUniverseInitPropertyExpansionStatus,
    AndroidUniverseInitPropertyExpressionResolver,
    android_init_expression_path_pattern,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)


class AndroidUniverseInitImportResolutionStatus(
    StrEnum
):
    RESOLVED = "resolved"
    RESOLVED_EXTERNAL_TARGET = "resolved_external_target"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitImportResolution:
    """
    Canonical Universe resolution for one literal INIT import declaration.

    ``candidate_sources`` preserves every parsed source compatible with the
    literal property-expression shape. ``matched_sources`` contains only the
    source selected by the concrete expanded path.
    """

    requirement: AndroidUniverseInitImportRequirement

    expansion: AndroidUniverseInitPropertyExpansion

    candidate_sources: tuple[
        ParsedAndroidInitSource,
        ...,
    ]

    matched_sources: tuple[
        ParsedAndroidInitSource,
        ...,
    ]

    external_target_path: PurePosixPath | None

    status: AndroidUniverseInitImportResolutionStatus

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseInitImportRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseInitImportRequirement"
            )

        if not isinstance(
            self.expansion,
            AndroidUniverseInitPropertyExpansion,
        ):
            raise TypeError(
                "expansion must be an "
                "AndroidUniverseInitPropertyExpansion"
            )

        for field_name, values in (
            (
                "candidate_sources",
                self.candidate_sources,
            ),
            (
                "matched_sources",
                self.matched_sources,
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
                    source,
                    ParsedAndroidInitSource,
                )
                for source
                in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "ParsedAndroidInitSource instances"
                )

        candidate_ids = {
            id(source)
            for source
            in self.candidate_sources
        }

        if any(
            id(source)
            not in candidate_ids
            for source
            in self.matched_sources
        ):
            raise ValueError(
                "matched_sources must be drawn from candidate_sources"
            )

        if (
            self.external_target_path is not None
            and not isinstance(
                self.external_target_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "external_target_path must be a "
                "PurePosixPath or None"
            )

        if not isinstance(
            self.status,
            AndroidUniverseInitImportResolutionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseInitImportResolutionStatus"
            )

        if (
            self.expansion.status
            is AndroidUniverseInitPropertyExpansionStatus.CONFLICTING
        ):
            expected = (
                AndroidUniverseInitImportResolutionStatus
                .AMBIGUOUS
            )

        elif (
            self.expansion.status
            is not AndroidUniverseInitPropertyExpansionStatus.RESOLVED
        ):
            expected = (
                AndroidUniverseInitImportResolutionStatus
                .UNRESOLVED
            )

        elif len(
            self.matched_sources
        ) == 1:
            expected = (
                AndroidUniverseInitImportResolutionStatus
                .RESOLVED
            )

        elif (
            self.external_target_path is not None
        ):
            expected = (
                AndroidUniverseInitImportResolutionStatus
                .RESOLVED_EXTERNAL_TARGET
            )

        elif len(
            self.matched_sources
        ) > 1:
            expected = (
                AndroidUniverseInitImportResolutionStatus
                .AMBIGUOUS
            )

        else:
            expected = (
                AndroidUniverseInitImportResolutionStatus
                .UNRESOLVED
            )

        if self.status is not expected:
            raise ValueError(
                "status does not match import resolution"
            )

    @property
    def resolution_id(
        self,
    ) -> str:
        return (
            "init-import-resolution:"
            f"{self.requirement.requirement_id}"
        )


class AndroidUniverseInitImportReconciler:
    """
    Resolve INIT imports against parsed INIT sources and static property facts.
    """

    def reconcile(
        self,
        *,
        requirements: tuple[
            AndroidUniverseInitImportRequirement,
            ...,
        ],
        sources: tuple[
            ParsedAndroidInitSource,
            ...,
        ],
        runtime_properties: tuple[
            AndroidUniverseRuntimePropertyRequirement,
            ...,
        ],
        external_target_paths: frozenset[
            PurePosixPath
        ] = frozenset(),
    ) -> tuple[
        AndroidUniverseInitImportResolution,
        ...,
    ]:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not isinstance(
            external_target_paths,
            frozenset,
        ):
            raise TypeError(
                "external_target_paths must be a frozenset"
            )

        if not all(
            isinstance(
                path,
                PurePosixPath,
            )
            for path in external_target_paths
        ):
            raise TypeError(
                "external_target_paths must contain only "
                "PurePosixPath instances"
            )

        resolver = (
            AndroidUniverseInitPropertyExpressionResolver(
                runtime_properties
            )
        )

        source_paths = tuple(
            (
                source,
                (
                    source.android_path.as_posix()
                    if source.android_path is not None
                    else None
                ),
                (
                    AndroidUniverseRuntimeContextResolver
                    .resolve_optional_filesystem_source(
                        source.filesystem_source
                    )
                ),
            )
            for source in sources
        )

        resolutions = []

        for requirement in requirements:
            requirement_runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    requirement.filesystem_source
                )
            )

            expansion = resolver.expand(
                requirement.path
            )

            pattern = (
                android_init_expression_path_pattern(
                    requirement.path
                )
            )

            candidate_sources = tuple(
                source
                for (
                    source,
                    android_path,
                    source_runtime_context,
                )
                in source_paths
                if (
                    android_path is not None
                    and (
                        AndroidUniverseRuntimeContextResolver
                        .same_runtime(
                            requirement_runtime_context,
                            source_runtime_context,
                        )
                    )
                    and pattern.fullmatch(
                        android_path
                    )
                )
            )

            if (
                expansion.status
                is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
            ):
                expanded_path = (
                    "/"
                    + expansion.expanded_value.lstrip(
                        "/"
                    )
                )

                matched_sources = tuple(
                    source
                    for (
                        source,
                        android_path,
                        source_runtime_context,
                    )
                    in source_paths
                    if (
                        android_path
                        == expanded_path
                        and (
                            AndroidUniverseRuntimeContextResolver
                            .same_runtime(
                                requirement_runtime_context,
                                source_runtime_context,
                            )
                        )
                    )
                )

            else:
                matched_sources = ()

            external_target_path = None

            if (
                requirement_runtime_context.is_root
                and expansion.status
                is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
                and not matched_sources
            ):
                expanded_path = (
                    "/"
                    + expansion.expanded_value.lstrip(
                        "/"
                    )
                )
                candidate_external_target = PurePosixPath(
                    expanded_path
                )

                if (
                    candidate_external_target
                    in external_target_paths
                ):
                    external_target_path = (
                        candidate_external_target
                    )

            if (
                expansion.status
                is AndroidUniverseInitPropertyExpansionStatus.CONFLICTING
            ):
                status = (
                    AndroidUniverseInitImportResolutionStatus
                    .AMBIGUOUS
                )

            elif (
                expansion.status
                is not AndroidUniverseInitPropertyExpansionStatus.RESOLVED
            ):
                status = (
                    AndroidUniverseInitImportResolutionStatus
                    .UNRESOLVED
                )

            elif len(
                matched_sources
            ) == 1:
                status = (
                    AndroidUniverseInitImportResolutionStatus
                    .RESOLVED
                )

            elif external_target_path is not None:
                status = (
                    AndroidUniverseInitImportResolutionStatus
                    .RESOLVED_EXTERNAL_TARGET
                )

            elif len(
                matched_sources
            ) > 1:
                status = (
                    AndroidUniverseInitImportResolutionStatus
                    .AMBIGUOUS
                )

            else:
                status = (
                    AndroidUniverseInitImportResolutionStatus
                    .UNRESOLVED
                )

            resolutions.append(
                AndroidUniverseInitImportResolution(
                    requirement=requirement,
                    expansion=expansion,
                    candidate_sources=tuple(
                        sorted(
                            candidate_sources,
                            key=lambda source: (
                                source.source_path.as_posix()
                            ),
                        )
                    ),
                    matched_sources=tuple(
                        sorted(
                            matched_sources,
                            key=lambda source: (
                                source.source_path.as_posix()
                            ),
                        )
                    ),
                    external_target_path=(
                        external_target_path
                    ),
                    status=status,
                )
            )

        return tuple(
            sorted(
                resolutions,
                key=lambda resolution: (
                    resolution.resolution_id
                ),
            )
        )


def android_init_inapplicable_source_paths(
    resolutions: tuple[
        AndroidUniverseInitImportResolution,
        ...,
    ],
) -> frozenset[Path]:
    """
    Return INIT sources whose selector-domain inapplicability is proven.

    A source is not inapplicable merely because one resolved property import
    did not select it. Parsed INIT sources may participate in more than one
    import expression, and another selector may still select the same source.

    Inapplicability is therefore established only when all of the following
    are true:

    * the source is a structural candidate of at least one property-expression
      import;
    * every property-expression import for which it is a candidate has a
      concrete RESOLVED expansion and import resolution;
    * none of those selector resolutions selects the source; and
    * no other resolved import selects the source.

    Unresolved or conflicting selector evidence keeps the source preserved as
    potentially applicable. This makes selector-domain applicability a
    conservative conclusion derived from canonical import-resolution evidence
    without changing the import-resolution contract itself.
    """

    if not isinstance(
        resolutions,
        tuple,
    ):
        raise TypeError(
            "resolutions must be a tuple"
        )

    if not all(
        isinstance(
            resolution,
            AndroidUniverseInitImportResolution,
        )
        for resolution in resolutions
    ):
        raise TypeError(
            "resolutions must contain only "
            "AndroidUniverseInitImportResolution instances"
        )

    selected_source_paths = {
        source.source_path
        for resolution in resolutions
        if (
            resolution.status
            is AndroidUniverseInitImportResolutionStatus.RESOLVED
        )
        for source in resolution.matched_sources
    }

    selector_resolutions_by_source_path = {}

    for resolution in resolutions:
        if not (
            resolution.expansion.is_property_expression
        ):
            continue

        for source in resolution.candidate_sources:
            selector_resolutions_by_source_path.setdefault(
                source.source_path,
                [],
            ).append(
                resolution
            )

    inapplicable_source_paths = set()

    for (
        source_path,
        selector_resolutions,
    ) in selector_resolutions_by_source_path.items():
        if source_path in selected_source_paths:
            continue

        if not selector_resolutions:
            continue

        if not all(
            (
                resolution.expansion.status
                is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
            )
            and (
                resolution.status
                is AndroidUniverseInitImportResolutionStatus.RESOLVED
            )
            for resolution
            in selector_resolutions
        ):
            continue

        if any(
            source_path
            in {
                source.source_path
                for source
                in resolution.matched_sources
            }
            for resolution
            in selector_resolutions
        ):
            continue

        inapplicable_source_paths.add(
            source_path
        )

    return frozenset(
        inapplicable_source_paths
    )
