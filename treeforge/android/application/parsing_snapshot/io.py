from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from treeforge.android.application.parsing_snapshot.model import (
    PARSING_SNAPSHOT_FORMAT,
    PARSING_SNAPSHOT_SCHEMA_VERSION,
    ParsingSnapshotEnvelope,
    ParsingSnapshotNode,
)


class ParsingSnapshotIO:
    """
    JSON transport for versioned Parsing snapshot envelopes.

    Object encoding and restoration are intentionally delegated to the graph
    encoder/decoder and explicit codecs.
    """

    @staticmethod
    def save(
        envelope: ParsingSnapshotEnvelope,
        path: Path,
    ) -> None:
        if not isinstance(
            envelope,
            ParsingSnapshotEnvelope,
        ):
            raise TypeError(
                "envelope must be a "
                "ParsingSnapshotEnvelope"
            )

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "format": (
                envelope.format_name
            ),
            "schema_version": (
                envelope.schema_version
            ),
            "root_reference": (
                envelope.root_reference
            ),
            "nodes": [
                {
                    "reference": (
                        node.reference
                    ),
                    "type": (
                        node.type_tag
                    ),
                    "payload": (
                        node.payload
                    ),
                }
                for node in envelope.nodes
            ],
        }

        path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    @staticmethod
    def load(
        path: Path,
    ) -> ParsingSnapshotEnvelope:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        raw = json.loads(
            path.read_text()
        )

        if not isinstance(
            raw,
            dict,
        ):
            raise ValueError(
                "Parsing snapshot root must be an object"
            )

        if (
            raw.get("format")
            != PARSING_SNAPSHOT_FORMAT
        ):
            raise ValueError(
                "unsupported Parsing snapshot format"
            )

        if (
            raw.get("schema_version")
            != PARSING_SNAPSHOT_SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported Parsing snapshot schema version"
            )

        root_reference = raw.get(
            "root_reference"
        )

        if not isinstance(
            root_reference,
            str,
        ):
            raise ValueError(
                "Parsing snapshot root_reference "
                "must be a string"
            )

        raw_nodes = raw.get(
            "nodes"
        )

        if not isinstance(
            raw_nodes,
            list,
        ):
            raise ValueError(
                "Parsing snapshot nodes must be a list"
            )

        nodes: list[
            ParsingSnapshotNode
        ] = []

        for raw_node in raw_nodes:
            if not isinstance(
                raw_node,
                dict,
            ):
                raise ValueError(
                    "Parsing snapshot node "
                    "must be an object"
                )

            reference = raw_node.get(
                "reference"
            )
            type_tag = raw_node.get(
                "type"
            )
            payload = raw_node.get(
                "payload"
            )

            if not isinstance(
                reference,
                str,
            ):
                raise ValueError(
                    "Parsing snapshot node reference "
                    "must be a string"
                )

            if not isinstance(
                type_tag,
                str,
            ):
                raise ValueError(
                    "Parsing snapshot node type "
                    "must be a string"
                )

            if not isinstance(
                payload,
                dict,
            ):
                raise ValueError(
                    "Parsing snapshot node payload "
                    "must be an object"
                )

            nodes.append(
                ParsingSnapshotNode(
                    reference=reference,
                    type_tag=type_tag,
                    payload=payload,
                )
            )

        return ParsingSnapshotEnvelope(
            root_reference=root_reference,
            nodes=tuple(
                nodes
            ),
        )
