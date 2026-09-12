from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
    AndroidParserFilesystemSource,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceResolution,
    AndroidUniverseInitServiceResolutionStatus,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseCrossFamilyRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
    AndroidUniverseInitSeclabelSelinuxRelationship,
    AndroidUniverseInitServiceControlRelationship,
    AndroidUniverseRelationshipStatus,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextKind,
    AndroidUniverseSelinuxContextRequirement,
)
from treeforge.android.universe.selinux.policy_graph import (
    AndroidUniverseSelinuxPolicyGraph,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)


class AndroidUniverseInitServiceSubstantiationStatus(
    StrEnum
):
    SUBSTANTIATED = "substantiated"
    PARTIALLY_SUBSTANTIATED = (
        "partially_substantiated"
    )
    UNSUBSTANTIATED = "unsubstantiated"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseExecutableEvidence:
    source: AndroidParserFilesystemSource
    android_path: PurePosixPath
    host_path: Path


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitServiceSubstantiation:
    service: AndroidUniverseInitServiceRequirement

    status: (
        AndroidUniverseInitServiceSubstantiationStatus
    )

    executable_path: PurePosixPath

    executable_evidence: tuple[
        AndroidUniverseExecutableEvidence,
        ...,
    ]

    searched_source_names: tuple[
        str,
        ...,
    ]

    explicit_seclabel_present: bool
    explicit_seclabel_resolved: bool | None

    @property
    def executable_present(
        self,
    ) -> bool:
        return bool(
            self.executable_evidence
        )

    @property
    def conclusion_id(
        self,
    ) -> str:
        return (
            "init-service-substantiation:"
            f"{self.service.requirement_id}"
        )


class AndroidUniverseInitServiceTargetClassification(
    StrEnum
):
    """
    Canonical classification of an unresolved INIT service-control target.

    UNDECLARED means the relationship names a concrete literal service target
    but the complete canonical active INIT service population contains no
    declaration for that name.

    UNKNOWN is reserved for targets whose concrete identity cannot be
    established canonically, such as an unresolved property-expanded target.

    AMBIGUOUS means canonical declarations exist for an actionable target, but
    canonical INIT service reconciliation could not reduce them to one
    effective declaration.

    Non-applicable declarations are intentionally not represented here.
    Relationship applicability owns those conclusions and classifies their
    service-control relationships as ALTERNATIVE before target substantiation.

    The classification describes why an actionable unresolved relationship
    lacks one canonical service target. It does not change relationship
    resolution or applicability.
    """

    UNDECLARED = "undeclared"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitServiceTargetSubstantiation:
    """
    Evidence for one unresolved INIT service-control target.

    This conclusion does not resolve the originating relationship. It
    classifies why the unresolved target lacks one canonical active INIT
    service match while preserving any declaration and cross-family evidence
    already established by earlier Universe reconciliation.

    ``selinux_context_evidence`` records exact cross-family identity evidence.

    ``control_peer_evidence`` records resolved service controls occurring in
    the same contiguous INIT control cluster. Peer evidence substantiates that
    the unresolved target intentionally participates in the same control
    context; it does not assert aliasing or service-name equivalence.
    """

    target: str

    classification: AndroidUniverseInitServiceTargetClassification

    relationships: tuple[
        AndroidUniverseInitServiceControlRelationship
        | AndroidUniverseInitOnRestartServiceControlRelationship,
        ...,
    ]

    selinux_context_evidence: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ]

    control_peer_evidence: tuple[
        AndroidUniverseInitServiceControlRelationship
        | AndroidUniverseInitOnRestartServiceControlRelationship,
        ...,
    ]

    @property
    def substantiated(
        self,
    ) -> bool:
        return bool(
            self.selinux_context_evidence
            or self.control_peer_evidence
        )

    @property
    def conclusion_id(
        self,
    ) -> str:
        return (
            "init-service-target-substantiation:"
            f"{self.target}"
        )


class AndroidUniverseInitServiceTargetSubstantiationReconciler:
    """
    Substantiate unresolved service-control targets using exact canonical
    cross-family evidence without inventing aliases or changing relationship
    resolution.
    """

    def reconcile(
        self,
        *,
        relationships: tuple[
            AndroidUniverseCrossFamilyRelationship,
            ...,
        ],
        relationship_applicability: tuple[
            AndroidUniverseRequirementApplicability,
            ...,
        ],
        init_service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ],
        selinux_policy_graph: AndroidUniverseSelinuxPolicyGraph,
    ) -> tuple[
        AndroidUniverseInitServiceTargetSubstantiation,
        ...,
    ]:
        if not isinstance(
            relationship_applicability,
            tuple,
        ):
            raise TypeError(
                "relationship_applicability must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            for item
            in relationship_applicability
        ):
            raise TypeError(
                "relationship_applicability must contain only "
                "AndroidUniverseRequirementApplicability instances"
            )

        if not isinstance(
            init_service_resolutions,
            tuple,
        ):
            raise TypeError(
                "init_service_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitServiceResolution,
            )
            for item
            in init_service_resolutions
        ):
            raise TypeError(
                "init_service_resolutions must contain only "
                "AndroidUniverseInitServiceResolution instances"
            )

        applicability_by_relationship_id = {
            item.requirement_id: item
            for item
            in relationship_applicability
        }

        relationship_ids = {
            relationship.relationship_id
            for relationship
            in relationships
        }

        if (
            set(
                applicability_by_relationship_id
            )
            != relationship_ids
        ):
            raise ValueError(
                "relationship_applicability must cover exactly "
                "the supplied relationships"
            )

        def is_actionable(
            relationship,
        ) -> bool:
            return (
                applicability_by_relationship_id[
                    relationship.relationship_id
                ].status
                is not AndroidUniverseApplicabilityStatus.ALTERNATIVE
            )

        unresolved_by_target = {}

        ordinary_relationships = {}
        onrestart_relationships = {}

        for relationship in relationships:
            if not is_actionable(
                relationship
            ):
                continue

            if isinstance(
                relationship,
                AndroidUniverseInitServiceControlRelationship,
            ):
                ordinary_relationships[
                    id(
                        relationship.command_requirement
                    )
                ] = relationship

            elif isinstance(
                relationship,
                AndroidUniverseInitOnRestartServiceControlRelationship,
            ):
                onrestart_relationships[
                    id(
                        relationship.onrestart_command
                    )
                ] = relationship

            else:
                continue

            if (
                relationship.status
                is not AndroidUniverseRelationshipStatus.UNRESOLVED
            ):
                continue

            unresolved_by_target.setdefault(
                relationship.target,
                [],
            ).append(
                relationship
            )

        control_peers_by_relationship_id = {}

        ordinary_actions = {}

        for relationship in relationships:
            if not is_actionable(
                relationship
            ):
                continue

            if not isinstance(
                relationship,
                AndroidUniverseInitServiceControlRelationship,
            ):
                continue

            ordinary_actions[
                id(
                    relationship.init_action
                )
            ] = relationship.init_action

        for action in ordinary_actions.values():
            cluster = []

            def flush_cluster():
                if not cluster:
                    return

                resolved_peers = tuple(
                    item
                    for item in cluster
                    if (
                        item.status
                        is AndroidUniverseRelationshipStatus.RESOLVED
                    )
                )

                if resolved_peers:
                    for item in cluster:
                        if (
                            item.status
                            is AndroidUniverseRelationshipStatus.UNRESOLVED
                        ):
                            control_peers_by_relationship_id.setdefault(
                                item.relationship_id,
                                [],
                            ).extend(
                                resolved_peers
                            )

                cluster.clear()

            for command_requirement in (
                action.command_requirements
            ):
                relationship = (
                    ordinary_relationships.get(
                        id(
                            command_requirement
                        )
                    )
                )

                if relationship is None:
                    flush_cluster()
                    continue

                cluster.append(
                    relationship
                )

            flush_cluster()

        onrestart_services = {}

        for relationship in relationships:
            if not is_actionable(
                relationship
            ):
                continue

            if not isinstance(
                relationship,
                AndroidUniverseInitOnRestartServiceControlRelationship,
            ):
                continue

            onrestart_services[
                id(
                    relationship.init_service
                )
            ] = relationship.init_service

        for service in onrestart_services.values():
            cluster = []

            def flush_onrestart_cluster():
                if not cluster:
                    return

                resolved_peers = tuple(
                    item
                    for item in cluster
                    if (
                        item.status
                        is AndroidUniverseRelationshipStatus.RESOLVED
                    )
                )

                if resolved_peers:
                    for item in cluster:
                        if (
                            item.status
                            is AndroidUniverseRelationshipStatus.UNRESOLVED
                        ):
                            control_peers_by_relationship_id.setdefault(
                                item.relationship_id,
                                [],
                            ).extend(
                                resolved_peers
                            )

                cluster.clear()

            for command in (
                service.semantics.onrestart_commands
            ):
                relationship = (
                    onrestart_relationships.get(
                        id(
                            command
                        )
                    )
                )

                if relationship is None:
                    flush_onrestart_cluster()
                    continue

                cluster.append(
                    relationship
                )

            flush_onrestart_cluster()

        service_context_kinds = {
            AndroidUniverseSelinuxContextKind.SERVICE,
            AndroidUniverseSelinuxContextKind.HWSERVICE,
            AndroidUniverseSelinuxContextKind.VNDSERVICE,
        }

        contexts_by_selector = {}

        for requirement in (
            selinux_policy_graph.context_requirements
        ):
            if (
                requirement.kind
                not in service_context_kinds
            ):
                continue

            contexts_by_selector.setdefault(
                requirement.selector,
                [],
            ).append(
                requirement
            )

        service_resolutions_by_name = {}

        for resolution in init_service_resolutions:
            service_resolutions_by_name.setdefault(
                resolution.name,
                [],
            ).append(
                resolution
            )

        conclusions = []

        for target, target_relationships in (
            unresolved_by_target.items()
        ):
            target_resolutions = tuple(
                service_resolutions_by_name.get(
                    target,
                    (),
                )
            )

            if not target_resolutions:
                dynamic_target = any(
                    "${" in relationship.target
                    for relationship
                    in target_relationships
                )

                target_classification = (
                    AndroidUniverseInitServiceTargetClassification
                    .UNKNOWN
                    if dynamic_target
                    else (
                        AndroidUniverseInitServiceTargetClassification
                        .UNDECLARED
                    )
                )
            else:
                target_classification = (
                    AndroidUniverseInitServiceTargetClassification
                    .AMBIGUOUS
                )

            evidence = tuple(
                sorted(
                    contexts_by_selector.get(
                        target,
                        (),
                    ),
                    key=lambda requirement: (
                        requirement.kind.value,
                        requirement.selector,
                        requirement.context,
                    ),
                )
            )

            control_peer_evidence = {
                peer.relationship_id: peer
                for relationship
                in target_relationships
                for peer
                in control_peers_by_relationship_id.get(
                    relationship.relationship_id,
                    (),
                )
                if (
                    peer.target
                    != target
                )
            }

            control_peer_evidence = tuple(
                sorted(
                    control_peer_evidence.values(),
                    key=lambda relationship: (
                        relationship.relationship_id
                    ),
                )
            )

            conclusions.append(
                AndroidUniverseInitServiceTargetSubstantiation(
                    target=target,
                    classification=target_classification,
                    relationships=tuple(
                        sorted(
                            target_relationships,
                            key=lambda relationship: (
                                relationship.relationship_id
                            ),
                        )
                    ),
                    selinux_context_evidence=evidence,
                    control_peer_evidence=(
                        control_peer_evidence
                    ),
                )
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.conclusion_id
                ),
            )
        )


class AndroidUniverseInitServiceSubstantiationReconciler:
    def reconcile(
        self,
        *,
        services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        relationships: tuple[
            AndroidUniverseCrossFamilyRelationship,
            ...,
        ],
        source_inventory: AndroidModelSourceInventory,
    ) -> tuple[
        AndroidUniverseInitServiceSubstantiation,
        ...,
    ]:
        seclabel_by_service_id = {
            relationship.init_service.requirement_id:
            relationship
            for relationship in relationships
            if isinstance(
                relationship,
                AndroidUniverseInitSeclabelSelinuxRelationship,
            )
        }

        searched_source_names = tuple(
            source.source_name
            for source
            in source_inventory.filesystems
        )

        conclusions = []

        for service in services:
            executable = PurePosixPath(
                service.executable
            )

            executable_evidence = (
                self._resolve_executable(
                    executable=executable,
                    source_inventory=source_inventory,
                )
            )

            seclabel = (
                service.semantics.seclabel
            )

            explicit_seclabel_present = (
                seclabel is not None
            )

            explicit_seclabel_resolved = None

            if explicit_seclabel_present:
                relationship = (
                    seclabel_by_service_id.get(
                        service.requirement_id
                    )
                )

                explicit_seclabel_resolved = (
                    relationship is not None
                    and relationship.status
                    is AndroidUniverseRelationshipStatus.RESOLVED
                )

            dynamic_executable = (
                "${" in service.executable
            )

            if (
                executable_evidence
                and (
                    not explicit_seclabel_present
                    or explicit_seclabel_resolved
                )
            ):
                status = (
                    AndroidUniverseInitServiceSubstantiationStatus
                    .SUBSTANTIATED
                )

            elif (
                not dynamic_executable
                and not executable_evidence
                and explicit_seclabel_present
                and explicit_seclabel_resolved is False
            ):
                status = (
                    AndroidUniverseInitServiceSubstantiationStatus
                    .UNSUBSTANTIATED
                )

            else:
                status = (
                    AndroidUniverseInitServiceSubstantiationStatus
                    .PARTIALLY_SUBSTANTIATED
                )

            conclusions.append(
                AndroidUniverseInitServiceSubstantiation(
                    service=service,
                    status=status,
                    executable_path=executable,
                    executable_evidence=(
                        executable_evidence
                    ),
                    searched_source_names=(
                        searched_source_names
                    ),
                    explicit_seclabel_present=(
                        explicit_seclabel_present
                    ),
                    explicit_seclabel_resolved=(
                        explicit_seclabel_resolved
                    ),
                )
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.conclusion_id
                ),
            )
        )

    def _resolve_executable(
        self,
        *,
        executable: PurePosixPath,
        source_inventory: AndroidModelSourceInventory,
    ) -> tuple[
        AndroidUniverseExecutableEvidence,
        ...,
    ]:
        executable = self._normalize_executable_path(
            executable
        )

        evidence = []
        seen_host_paths = set()

        for source in source_inventory.filesystems:
            candidates = (
                self._candidate_paths(
                    source=source,
                    android_path=executable,
                )
            )

            for filesystem, relative in candidates:
                try:
                    if not filesystem.is_file(
                        relative
                    ):
                        continue

                    host_path = filesystem.resolve(
                        relative
                    )

                except (
                    OSError,
                    RuntimeError,
                    ValueError,
                ):
                    continue

                if host_path in seen_host_paths:
                    continue

                seen_host_paths.add(
                    host_path
                )

                evidence.append(
                    AndroidUniverseExecutableEvidence(
                        source=source,
                        android_path=executable,
                        host_path=host_path,
                    )
                )

        return tuple(
            sorted(
                evidence,
                key=lambda item: (
                    item.source.source_name,
                    item.host_path.as_posix(),
                ),
            )
        )

    @staticmethod
    def _normalize_executable_path(
        executable: PurePosixPath,
    ) -> PurePosixPath:
        """
        Normalize one INIT executable spelling for Android namespace lookup.

        INIT declarations normally use absolute Android paths, but vendor
        configuration may also use Android-root-relative spellings such as
        ``vendor/bin/foo``.  Normalization is resolution-only: the original
        parsed service executable remains unchanged.
        """

        if executable.is_absolute():
            return executable

        return PurePosixPath(
            "/"
        ) / executable

    @staticmethod
    def _candidate_paths(
        *,
        source,
        android_path,
    ):
        candidates = []
        seen = set()

        def add(
            filesystem,
            relative,
        ):
            identity = (
                filesystem.root,
                relative,
            )

            if identity in seen:
                return

            seen.add(
                identity
            )

            candidates.append(
                (
                    filesystem,
                    relative,
                )
            )

        partition_name = (
            source.partition_name
        )

        partition_prefixes = []

        if (
            partition_name is not None
            and partition_name != "system"
        ):
            partition_prefixes.append(
                PurePosixPath(
                    f"/{partition_name}"
                )
            )

            system_alias_partitions = {
                "product",
                "system_ext",
            }

            if (
                partition_name
                in system_alias_partitions
            ):
                partition_prefixes.append(
                    PurePosixPath(
                        f"/system/{partition_name}"
                    )
                )

        for prefix in partition_prefixes:
            if (
                android_path == prefix
                or prefix in android_path.parents
            ):
                relative = (
                    android_path.relative_to(
                        prefix
                    ).as_posix()
                )

                add(
                    source.filesystem,
                    relative,
                )

        for view in source.views:
            prefix = view.android_prefix

            if (
                prefix == PurePosixPath("/")
            ):
                if (
                    source.partition is None
                    or partition_name == "system"
                ):
                    add(
                        view.filesystem,
                        android_path.as_posix(),
                    )

                continue

            if (
                android_path == prefix
                or prefix in android_path.parents
            ):
                relative = (
                    android_path.relative_to(
                        prefix
                    ).as_posix()
                )

                add(
                    view.filesystem,
                    relative,
                )

        return tuple(
            candidates
        )
