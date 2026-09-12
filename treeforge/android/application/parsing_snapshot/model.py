from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PARSING_SNAPSHOT_FORMAT = (
    "treeforge.android.parsing_snapshot"
)

PARSING_SNAPSHOT_SCHEMA_VERSION = 1


@dataclass(
    frozen=True,
    slots=True,
)
class ParsingSnapshotNode:
    """
    One serialized object in a Parsing checkpoint object graph.

    ``reference`` is the checkpoint-local canonical identity of the object.

    ``type_tag`` identifies the explicit codec responsible for restoring it.

    ``payload`` contains only JSON-compatible values and checkpoint
    references. Shared canonical objects appear once in the node table and
    are referenced everywhere else by the same ``reference``.
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
class ParsingSnapshotEnvelope:
    """
    Versioned persisted representation of one Parsing checkpoint graph.

    This is an application persistence model. It is intentionally separate
    from AndroidParsingSnapshot, which remains the canonical in-memory
    Parsing boundary.
    """

    root_reference: str

    nodes: tuple[
        ParsingSnapshotNode,
        ...,
    ]

    format_name: str = (
        PARSING_SNAPSHOT_FORMAT
    )

    schema_version: int = (
        PARSING_SNAPSHOT_SCHEMA_VERSION
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            self.format_name
            != PARSING_SNAPSHOT_FORMAT
        ):
            raise ValueError(
                "unsupported Parsing snapshot format"
            )

        if (
            self.schema_version
            != PARSING_SNAPSHOT_SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported Parsing snapshot schema version"
            )

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
                ParsingSnapshotNode,
            )
            for node in self.nodes
        ):
            raise TypeError(
                "nodes must contain only "
                "ParsingSnapshotNode instances"
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
                "Parsing snapshot node references "
                "must be unique"
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
