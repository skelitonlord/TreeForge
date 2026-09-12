from __future__ import annotations

from typing import Any

from treeforge.android.persistence.model import (
    SnapshotEnvelope,
    SnapshotNode,
)
from treeforge.android.persistence.registry import (
    SnapshotCodecRegistry,
)


class SnapshotGraphDecoder:
    """
    Restore a canonical object graph while preserving shared identity.

    Each node is decoded at most once. Every later reference receives the
    exact same restored Python object.
    """

    def __init__(
        self,
        *,
        registry: SnapshotCodecRegistry,
    ) -> None:
        if not isinstance(
            registry,
            SnapshotCodecRegistry,
        ):
            raise TypeError(
                "registry must be a SnapshotCodecRegistry"
            )

        self.registry = registry

        self._nodes: dict[
            str,
            SnapshotNode,
        ] = {}

        self._objects: dict[
            str,
            object,
        ] = {}

        self._decoding: set[
            str
        ] = set()

    def decode(
        self,
        envelope: SnapshotEnvelope,
    ) -> object:
        if not isinstance(
            envelope,
            SnapshotEnvelope,
        ):
            raise TypeError(
                "envelope must be a SnapshotEnvelope"
            )

        self._nodes = {
            node.reference: node
            for node in envelope.nodes
        }

        self._objects.clear()
        self._decoding.clear()

        return self.reference(
            envelope.root_reference
        )

    def reference(
        self,
        reference: str,
    ) -> object:
        existing = self._objects.get(
            reference
        )

        if existing is not None:
            return existing

        if reference in self._decoding:
            raise ValueError(
                "cyclic snapshot object graph "
                "is not supported"
            )

        node = self._nodes.get(
            reference
        )

        if node is None:
            raise ValueError(
                "snapshot references unknown node: "
                f"{reference}"
            )

        self._decoding.add(
            reference
        )

        try:
            codec = self.registry.codec_for_tag(
                node.type_tag
            )

            value = codec.decode(
                node.payload,
                self,
            )

            if not isinstance(
                value,
                codec.python_type,
            ):
                raise TypeError(
                    "snapshot codec decode() "
                    "returned the wrong object type"
                )

            self._objects[reference] = value

            return value
        finally:
            self._decoding.discard(
                reference
            )

    def ref(
        self,
        value: Any,
    ) -> object:
        if not isinstance(
            value,
            dict,
        ):
            raise TypeError(
                "checkpoint reference value "
                "must be a dict"
            )

        if set(value) != {
            "$ref",
        }:
            raise ValueError(
                "invalid checkpoint reference value"
            )

        reference = value[
            "$ref"
        ]

        if not isinstance(
            reference,
            str,
        ):
            raise TypeError(
                "checkpoint reference must be a string"
            )

        return self.reference(
            reference
        )
    
    def optional_ref(
        self,
        value: Any,
    ) -> object | None:
        if value is None:
            return None

        return self.ref(
            value
        )

