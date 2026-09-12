from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.universe.selinux.policy_graph import (
    AndroidUniverseSelinuxGenfsLabelsVersionState,
    AndroidUniverseSelinuxPolicyGraph,
)


class AndroidUniverseSelinuxConclusionKind(
    StrEnum
):
    POLICY_RECONCILED = "policy_reconciled"
    GENFS_LABELS_VERSION_AGREED = (
        "genfs_labels_version_agreed"
    )
    GENFS_LABELS_VERSION_CONFLICTING = (
        "genfs_labels_version_conflicting"
    )
    GENFS_LABELS_VERSION_UNRESOLVED = (
        "genfs_labels_version_unresolved"
    )
    CONTEXT_TYPE_UNDECLARED = (
        "context_type_undeclared"
    )
    SEAPP_DOMAIN_UNDECLARED = (
        "seapp_domain_undeclared"
    )
    SEAPP_DATA_TYPE_UNDECLARED = (
        "seapp_data_type_undeclared"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxConclusion:
    kind: AndroidUniverseSelinuxConclusionKind
    subject: str
    detail: str


def conclude_selinux_policy(
    graph: AndroidUniverseSelinuxPolicyGraph,
) -> tuple[
    AndroidUniverseSelinuxConclusion,
    ...,
]:
    type_names = {
        symbol.name
        for symbol in graph.types
    }

    conclusions = [
        AndroidUniverseSelinuxConclusion(
            kind=(
                AndroidUniverseSelinuxConclusionKind
                .POLICY_RECONCILED
            ),
            subject="selinux",
            detail=(
                f"{len(graph.symbols)} canonical symbols; "
                f"{len(graph.access_rules)} access rules; "
                f"{len(graph.type_transitions)} type transitions"
            ),
        )
    ]

    genfs_labels_version = (
        graph.genfs_labels_version_conclusion
    )

    if genfs_labels_version is not None:
        if (
            genfs_labels_version.state
            is AndroidUniverseSelinuxGenfsLabelsVersionState.AGREED
        ):
            conclusions.append(
                AndroidUniverseSelinuxConclusion(
                    kind=(
                        AndroidUniverseSelinuxConclusionKind
                        .GENFS_LABELS_VERSION_AGREED
                    ),
                    subject="genfs_labels_version",
                    detail=(
                        f"{genfs_labels_version.value}; "
                        f"{len(genfs_labels_version.evidence)} "
                        "observation(s)"
                    ),
                )
            )

        elif (
            genfs_labels_version.state
            is AndroidUniverseSelinuxGenfsLabelsVersionState.CONFLICTING
        ):
            conclusions.append(
                AndroidUniverseSelinuxConclusion(
                    kind=(
                        AndroidUniverseSelinuxConclusionKind
                        .GENFS_LABELS_VERSION_CONFLICTING
                    ),
                    subject="genfs_labels_version",
                    detail=(
                        "conflicting observations: "
                        + ", ".join(
                            genfs_labels_version.observed_values
                        )
                    ),
                )
            )

        else:
            conclusions.append(
                AndroidUniverseSelinuxConclusion(
                    kind=(
                        AndroidUniverseSelinuxConclusionKind
                        .GENFS_LABELS_VERSION_UNRESOLVED
                    ),
                    subject="genfs_labels_version",
                    detail=(
                        "no genfs labels version observation "
                        "was present in canonical Parsing output"
                    ),
                )
            )

    referenced_context_types = {
        requirement.selinux_type
        for requirement
        in graph.context_requirements
        if requirement.selinux_type is not None
    }

    for name in sorted(
        referenced_context_types
        - type_names
    ):
        conclusions.append(
            AndroidUniverseSelinuxConclusion(
                kind=(
                    AndroidUniverseSelinuxConclusionKind
                    .CONTEXT_TYPE_UNDECLARED
                ),
                subject=name,
                detail=(
                    "context labeling references a type "
                    "not declared by the observed CIL policy"
                ),
            )
        )

    seapp_domains = {
        requirement.domain
        for requirement
        in graph.seapp_requirements
        if requirement.domain is not None
    }

    for name in sorted(
        seapp_domains
        - type_names
    ):
        conclusions.append(
            AndroidUniverseSelinuxConclusion(
                kind=(
                    AndroidUniverseSelinuxConclusionKind
                    .SEAPP_DOMAIN_UNDECLARED
                ),
                subject=name,
                detail=(
                    "seapp_contexts references a domain "
                    "not declared by the observed CIL policy"
                ),
            )
        )

    seapp_data_types = {
        requirement.data_type
        for requirement
        in graph.seapp_requirements
        if requirement.data_type is not None
    }

    for name in sorted(
        seapp_data_types
        - type_names
    ):
        conclusions.append(
            AndroidUniverseSelinuxConclusion(
                kind=(
                    AndroidUniverseSelinuxConclusionKind
                    .SEAPP_DATA_TYPE_UNDECLARED
                ),
                subject=name,
                detail=(
                    "seapp_contexts references a data type "
                    "not declared by the observed CIL policy"
                ),
            )
        )

    return tuple(
        conclusions
    )