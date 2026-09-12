from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class SnapshotNode:
    """
    One serialized object in a canonical persisted object graph.

    ``reference`` is checkpoint-local object identity.

    ``type_tag`` identifies the explicit codec responsible for restoring
    the object.

    ``payload`` contains JSON-compatible values and graph references.
    """

    reference: str
    type_tag: str
    payload: dict[str, Any]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.reference,
            str,
        ):
            raise TypeError(
                "reference must be a string"
            )

        if not self.reference.strip():
            raise ValueError(
                "reference must not be empty"
            )

        if not isinstance(
            self.type_tag,
            str,
        ):
            raise TypeError(
                "type_tag must be a string"
            )

        if not self.type_tag.strip():
            raise ValueError(
                "type_tag must not be empty"
            )

        if not isinstance(
            self.payload,
            dict,
        ):
            raise TypeError(
                "payload must be a dict"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class SnapshotEnvelope:
    """
    Generic persisted object-graph envelope.

    Snapshot-family format names and schema versions are owned by the
    application persistence service using this graph.
    """

    root_reference: str

    nodes: tuple[
        SnapshotNode,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.root_reference,
            str,
        ):
            raise TypeError(
                "root_reference must be a string"
            )

        if not self.root_reference.strip():
            raise ValueError(
                "root_reference must not be empty"
            )

        if not isinstance(
            self.nodes,
            tuple,
        ):
            raise TypeError(
                "nodes must be a tuple"
            )

        if not all(
            isinstance(
                node,
                SnapshotNode,
            )
            for node in self.nodes
        ):
            raise TypeError(
                "nodes must contain only "
                "SnapshotNode instances"
            )

        references = tuple(
            node.reference
            for node in self.nodes
        )

        if len(
            references
        ) != len(
            set(
                references
            )
        ):
            raise ValueError(
                "snapshot node references must be unique"
            )

        if (
            self.root_reference
            not in set(
                references
            )
        ):
            raise ValueError(
                "root_reference must identify "
                "a serialized node"
            )
