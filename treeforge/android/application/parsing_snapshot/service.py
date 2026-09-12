from __future__ import annotations

from pathlib import Path

from treeforge.android.application.parsing_snapshot.codecs import (
    FILESYSTEM_CODECS,
    FILESYSTEM_OBSERVATION_CODECS,
    IDENTITY_SPINE_CODECS,
    KNOWLEDGE_CODECS,
    PARSER_SOURCE_CODECS,
    PARSING_RESULT_CODECS,
)
from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.application.parsing_snapshot.io import (
    ParsingSnapshotIO,
)
from treeforge.android.application.parsing_snapshot.model import (
    ParsingSnapshotEnvelope,
    ParsingSnapshotNode,
)
from treeforge.android.persistence.model import (
    SnapshotEnvelope,
    SnapshotNode,
)
from treeforge.android.persistence.registry import (
    SnapshotCodecRegistry,
)
from treeforge.android.parsing.snapshot import (
    AndroidParsingSnapshot,
)
from treeforge.workspace.workspace import (
    Workspace,
)


PARSING_SNAPSHOT_FILENAME = (
    "android-parsing-snapshot.json"
)


def build_parsing_snapshot_registry(
) -> SnapshotCodecRegistry:
    """
    Build the complete production registry for the canonical Parsing
    checkpoint boundary.
    """

    registry = (
        SnapshotCodecRegistry()
    )

    for codec in (
        *IDENTITY_SPINE_CODECS,
        *FILESYSTEM_CODECS,
        *PARSER_SOURCE_CODECS,
        *FILESYSTEM_OBSERVATION_CODECS,
        *PARSING_RESULT_CODECS,
        *KNOWLEDGE_CODECS,
    ):
        registry.register(
            codec
        )

    return registry


def parsing_snapshot_path(
    workspace: Workspace,
) -> Path:
    if not isinstance(
        workspace,
        Workspace,
    ):
        raise TypeError(
            "workspace must be a Workspace"
        )

    return (
        workspace.state
        / PARSING_SNAPSHOT_FILENAME
    )


class AndroidParsingSnapshotStore:
    """
    Application-owned persistence for the canonical Parsing snapshot.

    The Parsing model remains persistence-agnostic. This service owns only
    registry assembly, graph encoding/decoding, and workspace JSON transport.
    """

    def __init__(
        self,
        *,
        registry: (
            SnapshotCodecRegistry
            | None
        ) = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else build_parsing_snapshot_registry()
        )

        if not isinstance(
            self.registry,
            SnapshotCodecRegistry,
        ):
            raise TypeError(
                "registry must be a "
                "SnapshotCodecRegistry"
            )

    def save(
        self,
        snapshot: AndroidParsingSnapshot,
        path: Path,
    ) -> None:
        if not isinstance(
            snapshot,
            AndroidParsingSnapshot,
        ):
            raise TypeError(
                "snapshot must be an "
                "AndroidParsingSnapshot"
            )

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        envelope = (
            SnapshotGraphEncoder(
                registry=self.registry
            )
            .encode(
                snapshot
            )
        )

        ParsingSnapshotIO.save(
            ParsingSnapshotEnvelope(
                root_reference=envelope.root_reference,
                nodes=tuple(
                    ParsingSnapshotNode(
                        reference=node.reference,
                        type_tag=node.type_tag,
                        payload=node.payload,
                    )
                    for node in envelope.nodes
                ),
            ),
            path,
        )

    def save_to_workspace(
        self,
        snapshot: AndroidParsingSnapshot,
        workspace: Workspace,
    ) -> Path:
        path = parsing_snapshot_path(
            workspace
        )

        self.save(
            snapshot,
            path,
        )

        return path

    def load(
        self,
        path: Path,
    ) -> AndroidParsingSnapshot:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        persisted = ParsingSnapshotIO.load(
            path
        )

        restored = (
            SnapshotGraphDecoder(
                registry=self.registry
            )
            .decode(
                SnapshotEnvelope(
                    root_reference=(
                        persisted.root_reference
                    ),
                    nodes=tuple(
                        SnapshotNode(
                            reference=node.reference,
                            type_tag=node.type_tag,
                            payload=node.payload,
                        )
                        for node in persisted.nodes
                    ),
                )
            )
        )

        if not isinstance(
            restored,
            AndroidParsingSnapshot,
        ):
            raise TypeError(
                "Parsing snapshot checkpoint root "
                "must restore as AndroidParsingSnapshot"
            )

        return restored

    def load_from_workspace(
        self,
        workspace: Workspace,
    ) -> AndroidParsingSnapshot:
        return self.load(
            parsing_snapshot_path(
                workspace
            )
        )
