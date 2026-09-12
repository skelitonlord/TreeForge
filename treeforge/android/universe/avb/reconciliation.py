from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from treeforge.android.parsing.avb import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
)

from treeforge.android.universe.avb.model import (
    AndroidUniverseVbmetaRequirement,
)


class AndroidUniverseAvbChainResolutionStatus(Enum):
    RESOLVED = auto()
    UNRESOLVED = auto()


@dataclass(frozen=True, slots=True)
class AndroidUniverseAvbPartitionAuthentication:
    """
    One literal AVB hash/hashtree authentication relationship.

    The owning Universe VBMeta requirement and exact Parsing descriptor are
    retained as canonical evidence.

    ``partition_name`` preserves the descriptor value literally. AVB sources
    may carry an empty partition-name field; Universe records that unnamed
    target explicitly rather than inventing an Android partition identity.
    """

    owner: AndroidUniverseVbmetaRequirement
    partition_name: str
    descriptor: (
        AndroidParsedAvbHashDescriptor
        | AndroidParsedAvbHashtreeDescriptor
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.owner,
            AndroidUniverseVbmetaRequirement,
        ):
            raise TypeError(
                "owner must be an AndroidUniverseVbmetaRequirement"
            )

        if not isinstance(
            self.partition_name,
            str,
        ):
            raise TypeError(
                "partition_name must be a string"
            )

        if not isinstance(
            self.descriptor,
            (
                AndroidParsedAvbHashDescriptor,
                AndroidParsedAvbHashtreeDescriptor,
            ),
        ):
            raise TypeError(
                "descriptor must be an AVB hash or hashtree descriptor"
            )

        if self.partition_name != self.descriptor.partition_name:
            raise ValueError(
                "partition_name must preserve exact descriptor identity"
            )

    @property
    def has_named_partition(
        self,
    ) -> bool:
        return bool(
            self.partition_name
        )


@dataclass(frozen=True, slots=True)
class AndroidUniverseAvbChainRelationship:
    """
    One AVB chain-partition trust relationship.

    ``owner`` is the VBMeta image containing the chain descriptor.
    ``target`` is the matching Universe VBMeta requirement when the named
    target exists in the parsed VBMeta population.

    Unresolved targets remain first-class evidence rather than being dropped.
    """

    owner: AndroidUniverseVbmetaRequirement
    descriptor: AndroidParsedAvbChainPartitionDescriptor
    target_partition_name: str
    status: AndroidUniverseAvbChainResolutionStatus
    target: AndroidUniverseVbmetaRequirement | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.owner,
            AndroidUniverseVbmetaRequirement,
        ):
            raise TypeError(
                "owner must be an AndroidUniverseVbmetaRequirement"
            )

        if not isinstance(
            self.descriptor,
            AndroidParsedAvbChainPartitionDescriptor,
        ):
            raise TypeError(
                "descriptor must be an "
                "AndroidParsedAvbChainPartitionDescriptor"
            )

        if (
            not isinstance(self.target_partition_name, str)
            or not self.target_partition_name
        ):
            raise ValueError(
                "target_partition_name must be a non-empty string"
            )

        if (
            self.target_partition_name
            != self.descriptor.partition_name
        ):
            raise ValueError(
                "target_partition_name must preserve exact "
                "descriptor partition identity"
            )

        if not isinstance(
            self.status,
            AndroidUniverseAvbChainResolutionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseAvbChainResolutionStatus"
            )

        if (
            self.status
            is AndroidUniverseAvbChainResolutionStatus.RESOLVED
        ):
            if not isinstance(
                self.target,
                AndroidUniverseVbmetaRequirement,
            ):
                raise ValueError(
                    "resolved AVB chain relationship requires target"
                )

        elif self.target is not None:
            raise ValueError(
                "unresolved AVB chain relationship cannot have target"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseAvbTopology:
    """
    Canonical device-level AVB topology derived from the complete parsed
    VBMeta population.

    This object records only relationships proven by AVB descriptors and
    generic graph conclusions. It does not assign device-, vendor-, SoC-, or
    Android-version-specific trust policy.
    """

    requirements: tuple[
        AndroidUniverseVbmetaRequirement,
        ...,
    ]

    authentications: tuple[
        AndroidUniverseAvbPartitionAuthentication,
        ...,
    ]

    chains: tuple[
        AndroidUniverseAvbChainRelationship,
        ...,
    ]

    root_requirements: tuple[
        AndroidUniverseVbmetaRequirement,
        ...,
    ]

    orphan_requirements: tuple[
        AndroidUniverseVbmetaRequirement,
        ...,
    ]

    cycle_requirements: tuple[
        AndroidUniverseVbmetaRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.requirements, tuple):
            raise TypeError("requirements must be a tuple")

        if not all(
            isinstance(item, AndroidUniverseVbmetaRequirement)
            for item in self.requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseVbmetaRequirement instances"
            )

        if not isinstance(self.authentications, tuple):
            raise TypeError("authentications must be a tuple")

        if not all(
            isinstance(
                item,
                AndroidUniverseAvbPartitionAuthentication,
            )
            for item in self.authentications
        ):
            raise TypeError(
                "authentications contains invalid entries"
            )

        if not isinstance(self.chains, tuple):
            raise TypeError("chains must be a tuple")

        if not all(
            isinstance(
                item,
                AndroidUniverseAvbChainRelationship,
            )
            for item in self.chains
        ):
            raise TypeError(
                "chains contains invalid entries"
            )

        requirement_ids = {
            id(requirement)
            for requirement in self.requirements
        }

        for name, values in (
            ("root_requirements", self.root_requirements),
            ("orphan_requirements", self.orphan_requirements),
            ("cycle_requirements", self.cycle_requirements),
        ):
            if not isinstance(values, tuple):
                raise TypeError(f"{name} must be a tuple")

            if not all(
                isinstance(
                    item,
                    AndroidUniverseVbmetaRequirement,
                )
                for item in values
            ):
                raise TypeError(
                    f"{name} contains invalid entries"
                )

            if not all(
                id(item) in requirement_ids
                for item in values
            ):
                raise ValueError(
                    f"{name} must preserve canonical requirement identity"
                )

        for authentication in self.authentications:
            if id(authentication.owner) not in requirement_ids:
                raise ValueError(
                    "AVB authentication owner must preserve "
                    "canonical topology requirement identity"
                )

            if not any(
                descriptor is authentication.descriptor
                for descriptor
                in authentication.owner.descriptors
            ):
                raise ValueError(
                    "AVB authentication must preserve exact "
                    "Parsing descriptor identity"
                )

        for chain in self.chains:
            if id(chain.owner) not in requirement_ids:
                raise ValueError(
                    "AVB chain owner must preserve canonical "
                    "topology requirement identity"
                )

            if not any(
                descriptor is chain.descriptor
                for descriptor
                in chain.owner.descriptors
            ):
                raise ValueError(
                    "AVB chain must preserve exact Parsing "
                    "descriptor identity"
                )

            if (
                chain.target is not None
                and id(chain.target) not in requirement_ids
            ):
                raise ValueError(
                    "resolved AVB chain target must preserve "
                    "canonical topology requirement identity"
                )

            if (
                chain.target is not None
                and chain.target.partition_name
                != chain.target_partition_name
            ):
                raise ValueError(
                    "resolved AVB chain target partition identity "
                    "must match its exact descriptor target"
                )

    @property
    def resolved_chain_count(self) -> int:
        return sum(
            chain.status
            is AndroidUniverseAvbChainResolutionStatus.RESOLVED
            for chain in self.chains
        )

    @property
    def unresolved_chain_count(self) -> int:
        return sum(
            chain.status
            is AndroidUniverseAvbChainResolutionStatus.UNRESOLVED
            for chain in self.chains
        )


class AndroidUniverseAvbTopologyReconciler:
    """
    Reconcile the complete Universe VBMeta population into a generic AVB
    authentication/trust graph.

    No AVB bytes are reopened or reparsed here. Parsing remains authoritative
    for literal descriptors; Universe owns cross-image reconciliation.
    """

    def reconcile(
        self,
        requirements: tuple[
            AndroidUniverseVbmetaRequirement,
            ...,
        ],
    ) -> AndroidUniverseAvbTopology:
        if not isinstance(requirements, tuple):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVbmetaRequirement,
            )
            for item in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseVbmetaRequirement instances"
            )

        by_name: dict[
            str,
            AndroidUniverseVbmetaRequirement,
        ] = {}

        for requirement in requirements:
            name = requirement.partition_name

            if name is None:
                continue

            if name in by_name:
                raise ValueError(
                    "duplicate partition-backed VBMeta identity: "
                    f"{name}"
                )

            by_name[name] = requirement

        authentications = []
        chains = []

        for requirement in requirements:
            for descriptor in requirement.descriptors:
                if isinstance(
                    descriptor,
                    (
                        AndroidParsedAvbHashDescriptor,
                        AndroidParsedAvbHashtreeDescriptor,
                    ),
                ):
                    authentications.append(
                        AndroidUniverseAvbPartitionAuthentication(
                            owner=requirement,
                            partition_name=(
                                descriptor.partition_name
                            ),
                            descriptor=descriptor,
                        )
                    )

                elif isinstance(
                    descriptor,
                    AndroidParsedAvbChainPartitionDescriptor,
                ):
                    target = by_name.get(
                        descriptor.partition_name
                    )

                    chains.append(
                        AndroidUniverseAvbChainRelationship(
                            owner=requirement,
                            descriptor=descriptor,
                            target_partition_name=(
                                descriptor.partition_name
                            ),
                            status=(
                                AndroidUniverseAvbChainResolutionStatus.RESOLVED
                                if target is not None
                                else
                                AndroidUniverseAvbChainResolutionStatus.UNRESOLVED
                            ),
                            target=target,
                        )
                    )

        incoming_ids = {
            id(chain.target)
            for chain in chains
            if chain.target is not None
        }

        root_requirements = tuple(
            requirement
            for requirement in requirements
            if id(requirement) not in incoming_ids
        )

        connected_ids = {
            id(chain.owner)
            for chain in chains
            if chain.target is not None
        } | incoming_ids

        orphan_requirements = tuple(
            requirement
            for requirement in requirements
            if id(requirement) not in connected_ids
        )

        cycle_requirements = (
            self._cycle_requirements(
                requirements=requirements,
                chains=tuple(chains),
            )
        )

        return AndroidUniverseAvbTopology(
            requirements=requirements,
            authentications=tuple(authentications),
            chains=tuple(chains),
            root_requirements=root_requirements,
            orphan_requirements=orphan_requirements,
            cycle_requirements=cycle_requirements,
        )

    def _cycle_requirements(
        self,
        *,
        requirements: tuple[
            AndroidUniverseVbmetaRequirement,
            ...,
        ],
        chains: tuple[
            AndroidUniverseAvbChainRelationship,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseVbmetaRequirement,
        ...,
    ]:
        adjacency: dict[int, set[int]] = {
            id(requirement): set()
            for requirement in requirements
        }

        for chain in chains:
            if chain.target is not None:
                adjacency[
                    id(chain.owner)
                ].add(
                    id(chain.target)
                )

        visiting: set[int] = set()
        visited: set[int] = set()
        cycle_nodes: set[int] = set()

        def visit(
            node: int,
            path: tuple[int, ...],
        ) -> None:
            if node in visiting:
                if node in path:
                    start = path.index(
                        node
                    )
                    cycle_nodes.update(
                        path[start:]
                    )

                cycle_nodes.add(
                    node
                )
                return

            if node in visited:
                return

            visiting.add(
                node
            )

            for target in adjacency[
                node
            ]:
                visit(
                    target,
                    path + (node,),
                )

            visiting.remove(
                node
            )
            visited.add(
                node
            )

        for node in adjacency:
            visit(
                node,
                (),
            )

        return tuple(
            requirement
            for requirement in requirements
            if id(requirement) in cycle_nodes
        )
