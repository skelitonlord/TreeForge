from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.import_requirement import (
    AndroidUniverseInitImportRequirement,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportResolution,
    AndroidUniverseInitImportResolutionStatus,
    android_init_inapplicable_source_paths,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceResolution,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)


AndroidUniverseInitSourceRequirement = (
    AndroidUniverseInitImportRequirement
    | AndroidUniverseInitServiceRequirement
    | AndroidUniverseInitActionRequirement
)


class AndroidUniverseInitSourceApplicabilityStatus(StrEnum):
    """
    Canonical applicability of one observed INIT source.

    REQUIRED means canonical Universe evidence proves that the source
    participates in the selected device configuration.

    ALTERNATIVE means selector-domain evidence proves that the source is an
    unselected alternative.

    RUNTIME_SELECTABLE means the source is a concrete candidate of an INIT
    selector whose value cannot be statically resolved from canonical
    factory evidence. The source must remain available for Android to select
    at runtime, without TreeForge claiming that the candidate is the selected
    source.

    UNREFERENCED means the source is present in the canonical observed INIT
    population but the complete canonical INIT load graph provides no load
    path to it. It is neither automatically loaded, selected/imported,
    selector-reachable, nor otherwise established as participating in the
    selected runtime configuration.

    UNRESOLVED is reserved for a source whose applicability genuinely cannot
    be concluded from the canonical evidence model.
    """

    REQUIRED = "required"
    ALTERNATIVE = "alternative"
    RUNTIME_SELECTABLE = "runtime_selectable"
    UNREFERENCED = "unreferenced"
    UNRESOLVED = "unresolved"


class AndroidUniverseInitSourceApplicabilityEvidenceKind(StrEnum):
    """Canonical evidence establishing INIT source applicability."""

    RESOLVED_IMPORT_TARGET = "resolved_import_target"
    EFFECTIVE_SERVICE_SOURCE = "effective_service_source"
    AUTO_LOADED_INIT_SOURCE = "auto_loaded_init_source"
    UNSELECTED_SELECTOR_ALTERNATIVE = (
        "unselected_selector_alternative"
    )
    UNRESOLVED_SELECTOR_CANDIDATE = (
        "unresolved_selector_candidate"
    )

    OUTSIDE_ROOT_RUNTIME = (
        "outside_root_runtime"
    )

    NO_CANONICAL_LOAD_PATH = (
        "no_canonical_load_path"
    )


@dataclass(frozen=True, slots=True)
class AndroidUniverseInitSourceApplicabilityEvidence:
    kind: AndroidUniverseInitSourceApplicabilityEvidenceKind
    reference_id: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            AndroidUniverseInitSourceApplicabilityEvidenceKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseInitSourceApplicabilityEvidenceKind"
            )

        if not isinstance(self.reference_id, str):
            raise TypeError(
                "reference_id must be a string"
            )

        if not self.reference_id:
            raise ValueError(
                "reference_id must not be empty"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseInitSourceApplicability:
    """
    Canonical Universe conclusion for one INIT source identity.

    Source identity and provenance remain exact. Reconstruction Planning may
    consume this conclusion but must not recreate source applicability from
    import/service semantics.
    """

    source_identity: str
    source_path: Path
    android_path: PurePosixPath | None
    filesystem_source: AndroidParserFilesystemSource | None

    requirement_ids: tuple[str, ...]

    status: AndroidUniverseInitSourceApplicabilityStatus

    evidence: tuple[
        AndroidUniverseInitSourceApplicabilityEvidence,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_identity, str)
            or not self.source_identity
        ):
            raise ValueError(
                "source_identity must be a non-empty string"
            )

        if not isinstance(self.source_path, Path):
            raise TypeError(
                "source_path must be a Path"
            )

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if (
            self.filesystem_source is not None
            and not isinstance(
                self.filesystem_source,
                AndroidParserFilesystemSource,
            )
        ):
            raise TypeError(
                "filesystem_source must be an "
                "AndroidParserFilesystemSource or None"
            )

        if not isinstance(
            self.requirement_ids,
            tuple,
        ):
            raise TypeError(
                "requirement_ids must be a tuple"
            )

        if not all(
            isinstance(item, str) and item
            for item in self.requirement_ids
        ):
            raise ValueError(
                "requirement_ids must contain non-empty strings"
            )

        if self.requirement_ids != tuple(
            sorted(self.requirement_ids)
        ):
            raise ValueError(
                "requirement_ids must be in canonical order"
            )

        if len(self.requirement_ids) != len(
            set(self.requirement_ids)
        ):
            raise ValueError(
                "requirement_ids must not contain duplicates"
            )

        if not isinstance(
            self.status,
            AndroidUniverseInitSourceApplicabilityStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseInitSourceApplicabilityStatus"
            )

        if not isinstance(self.evidence, tuple):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitSourceApplicabilityEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniverseInitSourceApplicabilityEvidence instances"
            )


_ANDROID_INIT_AUTOLOAD_PREFIXES = (
    PurePosixPath("/system/etc/init"),
    PurePosixPath("/system_ext/etc/init"),
    PurePosixPath("/product/etc/init"),
    PurePosixPath("/vendor/etc/init"),
    PurePosixPath("/odm/etc/init"),
)


def _is_android_init_auto_loaded_source(
    android_path: PurePosixPath | None,
) -> bool:
    if android_path is None:
        return False

    return any(
        android_path.parent == prefix
        for prefix in _ANDROID_INIT_AUTOLOAD_PREFIXES
    )


class AndroidUniverseInitSourceApplicabilityReconciler:
    """
    Reconcile canonical INIT source applicability from Universe-owned evidence.

    This capability intentionally reproduces only conclusions already
    established generically by canonical import and service reconciliation.
    It does not infer source-tree ownership, reconstruction destination,
    generated representation, or device-specific behavior.
    """

    @staticmethod
    def reconcile(
        *,
        sources: tuple[
            ParsedAndroidInitSource,
            ...,
        ],
        import_requirements: tuple[

            AndroidUniverseInitImportRequirement,
            ...,
        ],
        service_requirements: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        action_requirements: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        import_resolutions: tuple[
            AndroidUniverseInitImportResolution,
            ...,
        ],
        service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitSourceApplicability,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                ParsedAndroidInitSource,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedAndroidInitSource instances"
            )

        requirements = (
            tuple(import_requirements)
            + tuple(service_requirements)
            + tuple(action_requirements)
        )

        grouped: dict[
            str,
            list[AndroidUniverseInitSourceRequirement],
        ] = {}

        source_by_identity = {}

        for source in sources:
            source_identity = (
                android_universe_init_source_identity(
                    source_path=source.source_path,
                    android_path=source.android_path,
                    filesystem_source=(
                        source.filesystem_source
                    ),
                )
            )

            if (
                source_identity
                in source_by_identity
            ):
                raise ValueError(
                    "canonical INIT sources must have unique "
                    "Universe source identities"
                )

            source_by_identity[
                source_identity
            ] = source

            grouped[
                source_identity
            ] = []

        for requirement in requirements:
            source_identity = (
                android_universe_init_source_identity(
                    source_path=requirement.source_path,
                    android_path=requirement.android_path,
                    filesystem_source=(
                        requirement.filesystem_source
                    ),
                )
            )

            if (
                source_identity
                not in source_by_identity
            ):
                raise ValueError(
                    "INIT semantic requirement refers to a source "
                    "outside the canonical Parsing INIT population"
                )

            grouped[
                source_identity
            ].append(
                requirement
            )

        inapplicable_paths = (
            android_init_inapplicable_source_paths(
                import_resolutions
            )
        )

        import_evidence_by_path: dict[
            Path,
            list[
                AndroidUniverseInitSourceApplicabilityEvidence
            ],
        ] = {}

        for resolution in import_resolutions:
            if resolution.status not in (
                AndroidUniverseInitImportResolutionStatus.RESOLVED,
                AndroidUniverseInitImportResolutionStatus.RESOLVED_EXTERNAL_TARGET,
            ):
                continue

            if (
                resolution.status
                is AndroidUniverseInitImportResolutionStatus.RESOLVED
            ):
                for source in resolution.matched_sources:
                    import_evidence_by_path.setdefault(
                        source.source_path,
                        [],
                    ).append(
                        AndroidUniverseInitSourceApplicabilityEvidence(
                            kind=(
                                AndroidUniverseInitSourceApplicabilityEvidenceKind
                                .RESOLVED_IMPORT_TARGET
                            ),
                            reference_id=resolution.resolution_id,
                        )
                    )

            else:
                import_evidence_by_path.setdefault(
                    resolution.requirement.source_path,
                    [],
                ).append(
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .RESOLVED_IMPORT_TARGET
                        ),
                        reference_id=resolution.resolution_id,
                    )
                )

        runtime_selectable_evidence_by_path: dict[
            Path,
            list[
                AndroidUniverseInitSourceApplicabilityEvidence
            ],
        ] = {}

        for resolution in import_resolutions:
            if (
                resolution.status
                is not AndroidUniverseInitImportResolutionStatus.UNRESOLVED
            ):
                continue

            for source in resolution.candidate_sources:
                runtime_selectable_evidence_by_path.setdefault(
                    source.source_path,
                    [],
                ).append(
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .UNRESOLVED_SELECTOR_CANDIDATE
                        ),
                        reference_id=resolution.resolution_id,
                    )
                )

        service_evidence_by_path: dict[
            Path,
            list[
                AndroidUniverseInitSourceApplicabilityEvidence
            ],
        ] = {}

        for resolution in service_resolutions:
            for service in resolution.effective_services:
                service_evidence_by_path.setdefault(
                    service.source_path,
                    [],
                ).append(
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .EFFECTIVE_SERVICE_SOURCE
                        ),
                        reference_id=service.requirement_id,
                    )
                )

        results = []

        for source_identity, source_requirements in sorted(
            grouped.items(),
            key=lambda item: item[0],
        ):
            canonical_requirements = tuple(
                sorted(
                    source_requirements,
                    key=lambda item: item.requirement_id,
                )
            )

            source = source_by_identity.get(
                source_identity
            )

            if source is None:
                raise ValueError(
                    "INIT applicability group has no canonical "
                    "Parsing source"
                )

            source_path = source.source_path

            runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    source.filesystem_source
                )
            )

            positive_evidence = (
                tuple(
                    import_evidence_by_path.get(
                        source_path,
                        (),
                    )
                )
                + tuple(
                    service_evidence_by_path.get(
                        source_path,
                        (),
                    )
                )
            )

            if (
                runtime_context.is_root
                and source_path in inapplicable_paths
                and positive_evidence
            ):
                raise ValueError(
                    "canonical Universe INIT evidence classifies "
                    "the same source as both required and alternative: "
                    f"{source_identity}"
                )

            runtime_selectable_evidence = tuple(
                runtime_selectable_evidence_by_path.get(
                    source_path,
                    (),
                )
            )

            if not runtime_context.is_root:
                #
                # The source belongs to a distinct Android runtime discovered
                # beneath another materialized filesystem. Preserve its exact
                # Parsing/Universe identity, but do not admit it into the
                # selected ROOT INIT load graph.
                #
                status = (
                    AndroidUniverseInitSourceApplicabilityStatus
                    .UNREFERENCED
                )

                evidence = (
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .OUTSIDE_ROOT_RUNTIME
                        ),
                        reference_id=source_identity,
                    ),
                )

            elif positive_evidence:
                status = (
                    AndroidUniverseInitSourceApplicabilityStatus
                    .REQUIRED
                )

                evidence = tuple(
                    sorted(
                        positive_evidence,
                        key=lambda item: (
                            item.kind.value,
                            item.reference_id,
                        ),
                    )
                )

            elif runtime_selectable_evidence:
                status = (
                    AndroidUniverseInitSourceApplicabilityStatus
                    .RUNTIME_SELECTABLE
                )

                evidence = tuple(
                    sorted(
                        runtime_selectable_evidence,
                        key=lambda item: (
                            item.kind.value,
                            item.reference_id,
                        ),
                    )
                )

            elif source_path in inapplicable_paths:
                status = (
                    AndroidUniverseInitSourceApplicabilityStatus
                    .ALTERNATIVE
                )

                evidence = (
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .UNSELECTED_SELECTOR_ALTERNATIVE
                        ),
                        reference_id=source_identity,
                    ),
                )

            elif _is_android_init_auto_loaded_source(
                source.android_path
            ):
                status = (
                    AndroidUniverseInitSourceApplicabilityStatus
                    .REQUIRED
                )

                evidence = (
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .AUTO_LOADED_INIT_SOURCE
                        ),
                        reference_id=source_identity,
                    ),
                )

            else:
                #
                # Every canonical source has now passed through every
                # modeled INIT load-path class:
                #
                #   * resolved imports,
                #   * unresolved selector candidates,
                #   * selector alternatives,
                #   * effective source evidence, and
                #   * Android's canonical auto-loaded init directories.
                #
                # A remaining source is therefore not merely "unknown".
                # The complete canonical observed source graph contains no
                # load path to it.
                #
                status = (
                    AndroidUniverseInitSourceApplicabilityStatus
                    .UNREFERENCED
                )

                evidence = (
                    AndroidUniverseInitSourceApplicabilityEvidence(
                        kind=(
                            AndroidUniverseInitSourceApplicabilityEvidenceKind
                            .NO_CANONICAL_LOAD_PATH
                        ),
                        reference_id=source_identity,
                    ),
                )

            results.append(
                AndroidUniverseInitSourceApplicability(
                    source_identity=source_identity,
                    source_path=source_path,
                    android_path=(
                        source.android_path
                    ),
                    filesystem_source=(
                        source.filesystem_source
                    ),
                    requirement_ids=tuple(
                        requirement.requirement_id
                        for requirement
                        in canonical_requirements
                    ),
                    status=status,
                    evidence=evidence,
                )
            )

        return tuple(results)
