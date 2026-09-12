from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdDeviceRuleRequirement,
    AndroidUniverseUeventdFirmwareDirectoriesRequirement,
    AndroidUniverseUeventdImportRequirement,
    AndroidUniverseUeventdRequirement,
    AndroidUniverseUeventdSocketRcvbufRequirement,
    AndroidUniverseUeventdSubsystemRequirement,
    AndroidUniverseUeventdSysfsRuleRequirement,
)


class AndroidUniverseUeventdImportResolutionStatus(StrEnum):
    """Canonical resolution state of one UEVENTD import."""

    RESOLVED = "resolved"
    ABSENT = "absent"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


class AndroidUniverseUeventdSubjectStatus(StrEnum):
    """Cross-source state of one UEVENTD semantic subject."""

    UNIQUE = "unique"
    EQUIVALENT = "equivalent"
    CONFLICTING = "conflicting"


class AndroidUniverseUeventdRequirementStatus(StrEnum):
    """Canonical effective state of one UEVENTD requirement."""

    ACTIVE = "active"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(frozen=True, slots=True)
class AndroidUniverseUeventdImportResolution:
    requirement: AndroidUniverseUeventdImportRequirement
    status: AndroidUniverseUeventdImportResolutionStatus
    target_path: PurePosixPath
    matched_source_identities: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseUeventdImportRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseUeventdImportRequirement"
            )

        if not isinstance(
            self.status,
            AndroidUniverseUeventdImportResolutionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseUeventdImportResolutionStatus"
            )

        if not isinstance(
            self.target_path,
            PurePosixPath,
        ):
            raise TypeError(
                "target_path must be a PurePosixPath"
            )

        if not isinstance(
            self.matched_source_identities,
            tuple,
        ):
            raise TypeError(
                "matched_source_identities must be a tuple"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseUeventdSourceReachability:
    source_identity: str
    root: bool
    reachable: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.source_identity,
                str,
            )
            or not self.source_identity
        ):
            raise ValueError(
                "source_identity must be a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseUeventdSubjectConclusion:
    subject_key: tuple[object, ...]
    status: AndroidUniverseUeventdSubjectStatus
    requirements: tuple[
        AndroidUniverseUeventdRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.subject_key,
            tuple,
        ):
            raise TypeError(
                "subject_key must be a tuple"
            )

        if not isinstance(
            self.status,
            AndroidUniverseUeventdSubjectStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseUeventdSubjectStatus"
            )

        if (
            not isinstance(
                self.requirements,
                tuple,
            )
            or not self.requirements
        ):
            raise ValueError(
                "requirements must be a non-empty tuple"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseUeventdRequirementConclusion:
    requirement: AndroidUniverseUeventdRequirement
    status: AndroidUniverseUeventdRequirementStatus
    reason: str

    @property
    def requirement_id(self) -> str:
        return self.requirement.requirement_id


@dataclass(frozen=True, slots=True)
class AndroidUniverseUeventdReconciliation:
    """
    Canonical cross-source UEVENTD reconciliation.

    This result uses only canonical TreeForge evidence:

    - source Android identities;
    - explicit UEVENTD imports;
    - declaration semantic subjects; and
    - declaration payload equality.

    It does not assume Android override precedence and does not use
    device-specific Knowledge.
    """

    import_resolutions: tuple[
        AndroidUniverseUeventdImportResolution,
        ...,
    ]

    source_reachability: tuple[
        AndroidUniverseUeventdSourceReachability,
        ...,
    ]

    subject_conclusions: tuple[
        AndroidUniverseUeventdSubjectConclusion,
        ...,
    ]

    requirement_conclusions: tuple[
        AndroidUniverseUeventdRequirementConclusion,
        ...,
    ]

    def __post_init__(self) -> None:
        requirement_ids = tuple(
            conclusion.requirement_id
            for conclusion
            in self.requirement_conclusions
        )

        if len(
            requirement_ids
        ) != len(
            set(
                requirement_ids
            )
        ):
            raise ValueError(
                "UEVENTD requirement conclusions must contain "
                "each requirement exactly once"
            )

    def conclusion_for_requirement(
        self,
        requirement_id: str,
    ) -> AndroidUniverseUeventdRequirementConclusion | None:
        return next(
            (
                conclusion
                for conclusion
                in self.requirement_conclusions
                if (
                    conclusion.requirement_id
                    == requirement_id
                )
            ),
            None,
        )


class AndroidUniverseUeventdReconciler:
    """
    Reconcile canonical UEVENTD requirements using TreeForge evidence only.

    Import targets are resolved by canonical Android source identity.
    Reachability follows resolved imports from structurally discovered roots.

    Repeated semantic subjects among proven-reachable sources are equivalent
    when their source-independent declaration payloads are identical. Differing
    reachable payloads are preserved as conflicts rather than resolved using an
    assumed runtime precedence rule.

    Declarations from sources not proven reachable remain explicit unresolved
    requirements and do not participate in effective subject conflict
    classification.
    """

    @classmethod
    def reconcile(
        cls,
        requirements: tuple[
            AndroidUniverseUeventdRequirement,
            ...,
        ],
    ) -> AndroidUniverseUeventdReconciliation:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        source_requirements: dict[
            str,
            list[AndroidUniverseUeventdRequirement],
        ] = defaultdict(list)

        for requirement in requirements:
            source_requirements[
                cls._source_identity(
                    requirement
                )
            ].append(
                requirement
            )

        available_sources = frozenset(
            source_requirements
        )

        import_resolutions = tuple(
            sorted(
                (
                    cls._resolve_import(
                        requirement,
                        available_sources,
                    )
                    for requirement
                    in requirements
                    if isinstance(
                        requirement,
                        AndroidUniverseUeventdImportRequirement,
                    )
                ),
                key=lambda item: (
                    item.requirement.requirement_id
                ),
            )
        )

        resolved_edges: dict[
            str,
            set[str],
        ] = defaultdict(set)

        resolved_targets: set[str] = set()

        for resolution in import_resolutions:
            if (
                resolution.status
                is not AndroidUniverseUeventdImportResolutionStatus
                .RESOLVED
            ):
                continue

            source_identity = cls._source_identity(
                resolution.requirement
            )

            target_identity = (
                resolution.matched_source_identities[0]
            )

            resolved_edges[
                source_identity
            ].add(
                target_identity
            )

            resolved_targets.add(
                target_identity
            )

        roots = tuple(
            sorted(
                available_sources
                - resolved_targets
            )
        )

        reachable: set[str] = set(
            roots
        )

        queue = deque(
            roots
        )

        while queue:
            source_identity = queue.popleft()

            for target_identity in sorted(
                resolved_edges.get(
                    source_identity,
                    (),
                )
            ):
                if target_identity in reachable:
                    continue

                reachable.add(
                    target_identity
                )

                queue.append(
                    target_identity
                )

        source_reachability = tuple(
            AndroidUniverseUeventdSourceReachability(
                source_identity=source_identity,
                root=(
                    source_identity
                    in roots
                ),
                reachable=(
                    source_identity
                    in reachable
                ),
            )
            for source_identity
            in sorted(
                available_sources
            )
        )

        subject_groups: dict[
            tuple[object, ...],
            list[AndroidUniverseUeventdRequirement],
        ] = defaultdict(list)

        #
        # Effective UEVENTD semantic subjects are reconciled only across
        # sources proven reachable by the canonical import graph.
        #
        # Requirements from unreachable sources are retained below as
        # UNRESOLVED requirements, but they must not make a reachable
        # declaration appear conflicting merely because an unreachable
        # source contains a different declaration for the same subject.
        #
        for requirement in requirements:
            source_identity = cls._source_identity(
                requirement
            )

            if source_identity not in reachable:
                continue

            subject_groups[
                cls._subject_key(
                    requirement
                )
            ].append(
                requirement
            )

        subject_conclusions: list[
            AndroidUniverseUeventdSubjectConclusion
        ] = []

        subject_status_by_requirement_id: dict[
            str,
            AndroidUniverseUeventdSubjectStatus,
        ] = {}

        for subject_key, members in sorted(
            subject_groups.items(),
            key=lambda item: repr(
                item[0]
            ),
        ):
            payloads = {
                cls._payload_key(
                    member
                )
                for member
                in members
            }

            if len(members) == 1:
                status = (
                    AndroidUniverseUeventdSubjectStatus
                    .UNIQUE
                )
            elif len(payloads) == 1:
                status = (
                    AndroidUniverseUeventdSubjectStatus
                    .EQUIVALENT
                )
            else:
                status = (
                    AndroidUniverseUeventdSubjectStatus
                    .CONFLICTING
                )

            canonical_members = tuple(
                sorted(
                    members,
                    key=lambda member: (
                        member.requirement_id
                    ),
                )
            )

            subject_conclusions.append(
                AndroidUniverseUeventdSubjectConclusion(
                    subject_key=subject_key,
                    status=status,
                    requirements=canonical_members,
                )
            )

            for member in canonical_members:
                subject_status_by_requirement_id[
                    member.requirement_id
                ] = status

        import_resolution_by_id = {
            resolution.requirement.requirement_id:
            resolution
            for resolution
            in import_resolutions
        }

        requirement_conclusions: list[
            AndroidUniverseUeventdRequirementConclusion
        ] = []

        for requirement in sorted(
            requirements,
            key=lambda item: (
                item.requirement_id
            ),
        ):
            requirement_id = (
                requirement.requirement_id
            )

            source_identity = (
                cls._source_identity(
                    requirement
                )
            )

            if source_identity not in reachable:
                requirement_conclusions.append(
                    AndroidUniverseUeventdRequirementConclusion(
                        requirement=requirement,
                        status=(
                            AndroidUniverseUeventdRequirementStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            "Canonical UEVENTD source is not proven "
                            "reachable from the observed source graph."
                        ),
                    )
                )
                continue

            if isinstance(
                requirement,
                AndroidUniverseUeventdImportRequirement,
            ):
                resolution = (
                    import_resolution_by_id[
                        requirement_id
                    ]
                )

                if (
                    resolution.status
                    is AndroidUniverseUeventdImportResolutionStatus
                    .RESOLVED
                ):
                    status = (
                        AndroidUniverseUeventdRequirementStatus
                        .ACTIVE
                    )
                    reason = (
                        "UEVENTD import resolves to exactly one "
                        "canonical observed source."
                    )
                elif (
                    resolution.status
                    is AndroidUniverseUeventdImportResolutionStatus
                    .ABSENT
                ):
                    status = (
                        AndroidUniverseUeventdRequirementStatus
                        .NOT_APPLICABLE
                    )
                    reason = (
                        "UEVENTD import target is absent from the "
                        "complete canonical observed source population."
                    )
                elif (
                    resolution.status
                    is AndroidUniverseUeventdImportResolutionStatus
                    .AMBIGUOUS
                ):
                    status = (
                        AndroidUniverseUeventdRequirementStatus
                        .CONFLICTING
                    )
                    reason = (
                        "UEVENTD import matches multiple canonical "
                        "observed sources."
                    )
                else:
                    status = (
                        AndroidUniverseUeventdRequirementStatus
                        .UNRESOLVED
                    )
                    reason = (
                        "UEVENTD import resolution remains genuinely "
                        "indeterminate."
                    )

                requirement_conclusions.append(
                    AndroidUniverseUeventdRequirementConclusion(
                        requirement=requirement,
                        status=status,
                        reason=reason,
                    )
                )
                continue

            subject_status = (
                subject_status_by_requirement_id.get(
                    requirement_id
                )
            )

            if subject_status is None:
                raise ValueError(
                    "reachable UEVENTD declaration has no canonical "
                    "semantic-subject conclusion: "
                    f"{requirement_id}"
                )

            if (
                subject_status
                is AndroidUniverseUeventdSubjectStatus
                .CONFLICTING
            ):
                status = (
                    AndroidUniverseUeventdRequirementStatus
                    .CONFLICTING
                )
                reason = (
                    "Reachable UEVENTD declarations for the same "
                    "semantic subject have differing payloads."
                )
            elif (
                subject_status
                is AndroidUniverseUeventdSubjectStatus
                .EQUIVALENT
            ):
                status = (
                    AndroidUniverseUeventdRequirementStatus
                    .ACTIVE
                )
                reason = (
                    "Reachable UEVENTD declaration is semantically "
                    "equivalent to another canonical declaration."
                )
            else:
                status = (
                    AndroidUniverseUeventdRequirementStatus
                    .ACTIVE
                )
                reason = (
                    "Reachable UEVENTD declaration has a unique "
                    "canonical semantic subject."
                )

            requirement_conclusions.append(
                AndroidUniverseUeventdRequirementConclusion(
                    requirement=requirement,
                    status=status,
                    reason=reason,
                )
            )

        return AndroidUniverseUeventdReconciliation(
            import_resolutions=import_resolutions,
            source_reachability=source_reachability,
            subject_conclusions=tuple(
                subject_conclusions
            ),
            requirement_conclusions=tuple(
                requirement_conclusions
            ),
        )

    @classmethod
    def _resolve_import(
        cls,
        requirement: AndroidUniverseUeventdImportRequirement,
        available_sources: frozenset[str],
    ) -> AndroidUniverseUeventdImportResolution:
        target_path = PurePosixPath(
            "/"
            + requirement.declaration.path.lstrip(
                "/"
            )
        )

        canonical_target = (
            target_path.as_posix()
        )

        matched = tuple(
            sorted(
                source_identity
                for source_identity
                in available_sources
                if (
                    cls._normalize_source_identity(
                        source_identity
                    )
                    == canonical_target
                )
            )
        )

        if len(matched) == 1:
            status = (
                AndroidUniverseUeventdImportResolutionStatus
                .RESOLVED
            )
        elif len(matched) > 1:
            status = (
                AndroidUniverseUeventdImportResolutionStatus
                .AMBIGUOUS
            )
        elif canonical_target not in available_sources:
            status = (
                AndroidUniverseUeventdImportResolutionStatus
                .ABSENT
            )
        else:
            status = (
                AndroidUniverseUeventdImportResolutionStatus
                .UNRESOLVED
            )

        return AndroidUniverseUeventdImportResolution(
            requirement=requirement,
            status=status,
            target_path=target_path,
            matched_source_identities=matched,
        )

    @staticmethod
    def _source_identity(
        requirement: AndroidUniverseUeventdRequirement,
    ) -> str:
        path_identity = (
            requirement.android_path.as_posix()
            if requirement.android_path is not None
            else requirement.source_path.as_posix()
        )

        return (
            f"{requirement.source_name}::{path_identity}"
        )

    @staticmethod
    def _normalize_source_identity(
        source_identity: str,
    ) -> str:
        #
        # Canonical source identity is:
        #
        #     <filesystem-source-name>::<android-path>
        #
        # Import resolution intentionally compares only the Android-visible
        # target path, while retaining the filesystem-root component in the
        # actual source identity. Multiple matching roots therefore remain
        # explicit candidates instead of collapsing into one source.
        #
        if "::" in source_identity:
            (
                _source_name,
                source_identity,
            ) = source_identity.split(
                "::",
                1,
            )

        if not source_identity.startswith(
            "/"
        ):
            return source_identity

        return PurePosixPath(
            source_identity
        ).as_posix()

    @staticmethod
    def _subject_key(
        requirement: AndroidUniverseUeventdRequirement,
    ) -> tuple[object, ...]:
        declaration = requirement.declaration

        if isinstance(
            requirement,
            AndroidUniverseUeventdImportRequirement,
        ):
            return (
                "import",
                declaration.path,
            )

        if isinstance(
            requirement,
            AndroidUniverseUeventdDeviceRuleRequirement,
        ):
            return (
                "device",
                declaration.path,
            )

        if isinstance(
            requirement,
            AndroidUniverseUeventdSysfsRuleRequirement,
        ):
            return (
                "sysfs",
                declaration.path,
                declaration.attribute,
            )

        if isinstance(
            requirement,
            AndroidUniverseUeventdSubsystemRequirement,
        ):
            return (
                "subsystem",
                declaration.name,
            )

        if isinstance(
            requirement,
            AndroidUniverseUeventdFirmwareDirectoriesRequirement,
        ):
            return (
                "firmware_directories",
            )

        if isinstance(
            requirement,
            AndroidUniverseUeventdSocketRcvbufRequirement,
        ):
            return (
                "socket_rcvbuf",
            )

        raise TypeError(
            "unsupported canonical UEVENTD requirement type"
        )

    @classmethod
    def _payload_key(
        cls,
        requirement: AndroidUniverseUeventdRequirement,
    ) -> tuple[tuple[str, object], ...]:
        declaration = requirement.declaration

        if not is_dataclass(
            declaration
        ):
            raise TypeError(
                "UEVENTD declaration must be a dataclass"
            )

        payload: list[
            tuple[str, object]
        ] = []

        for field in fields(
            declaration
        ):
            if field.name in {
                "source_path",
                "source_line",
            }:
                continue

            payload.append(
                (
                    field.name,
                    cls._freeze(
                        getattr(
                            declaration,
                            field.name,
                        )
                    ),
                )
            )

        return tuple(
            payload
        )

    @classmethod
    def _freeze(
        cls,
        value: Any,
    ) -> object:
        if isinstance(
            value,
            dict,
        ):
            return tuple(
                sorted(
                    (
                        cls._freeze(key),
                        cls._freeze(item),
                    )
                    for key, item
                    in value.items()
                )
            )

        if isinstance(
            value,
            (
                list,
                tuple,
                set,
                frozenset,
            ),
        ):
            return tuple(
                cls._freeze(
                    item
                )
                for item
                in value
            )

        if is_dataclass(
            value
        ):
            #
            # Payload equality is intentionally source-independent.
            #
            # UEVENTD declarations can contain nested Parsing dataclasses,
            # notably AndroidUeventdSubsystemOption. Those nested objects
            # retain their own source_path/source_line provenance. If that
            # provenance participates in the frozen payload, two lexically
            # and semantically identical declarations recovered from
            # different canonical sources compare unequal.
            #
            # Preserve container/sequence order while recursively excluding
            # only Parsing provenance fields. Semantic fields remain part of
            # the payload key.
            #
            return tuple(
                (
                    field.name,
                    cls._freeze(
                        getattr(
                            value,
                            field.name,
                        )
                    ),
                )
                for field
                in fields(
                    value
                )
                if field.name
                not in {
                    "source_path",
                    "source_line",
                }
            )

        return value
