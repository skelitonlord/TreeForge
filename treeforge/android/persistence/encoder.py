from __future__ import annotations

from treeforge.android.persistence.model import (
    SnapshotEnvelope,
    SnapshotNode,
)
from treeforge.android.persistence.registry import (
    SnapshotCodecRegistry,
)


class SnapshotGraphEncoder:
    """
    Encode a canonical object graph while preserving shared identity.

    Objects receive checkpoint-local references by first deterministic
    encounter. The same Python object identity always maps to the same
    checkpoint reference.
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

        self._references: dict[
            int,
            str,
        ] = {}

        self._nodes: dict[
            str,
            SnapshotNode,
        ] = {}

        self._encoding: set[
            int
        ] = set()

    def encode(
        self,
        root: object,
    ) -> SnapshotEnvelope:
        self._references.clear()
        self._nodes.clear()
        self._encoding.clear()

        root_reference = self.reference(
            root
        )

        nodes = tuple(
            self._nodes[reference]
            for reference in sorted(
                self._nodes,
                key=self._reference_index,
            )
        )

        return SnapshotEnvelope(
            root_reference=root_reference,
            nodes=nodes,
        )

    def reference(
        self,
        value: object,
    ) -> str:
        identity = id(
            value
        )

        existing = self._references.get(
            identity
        )

        if existing is not None:
            return existing

        reference = (
            f"n{len(self._references) + 1:08d}"
        )

        # Reserve object identity before recursively encoding its payload.
        #
        # A later reference to the same object can therefore resolve to this
        # checkpoint-local reference even while the object's node payload is
        # still being constructed. This permits canonical cyclic graphs
        # without flattening or duplicating identity.
        self._references[identity] = reference
        self._encoding.add(identity)

        try:
            codec = self.registry.codec_for_value(
                value
            )

            payload = codec.encode(
                value,
                self,
            )

            if not isinstance(
                payload,
                dict,
            ):
                raise TypeError(
                    "snapshot codec encode() "
                    "must return a dict"
                )

            self._nodes[reference] = SnapshotNode(
                reference=reference,
                type_tag=codec.type_tag,
                payload=payload,
            )
        except Exception:
            self._references.pop(
                identity,
                None,
            )
            self._nodes.pop(
                reference,
                None,
            )
            raise
        finally:
            self._encoding.discard(
                identity
            )

        return reference

    @staticmethod
    def ref_value(
        reference: str,
    ) -> dict[
        str,
        str,
    ]:
        return {
            "$ref": reference,
        }

    def ref(
        self,
        value: object,
    ) -> dict[
        str,
        str,
    ]:
        return self.ref_value(
            self.reference(
                value
            )
        )

    def optional_ref(
        self,
        value: object | None,
    ) -> dict[str, str] | None:
        if value is None:
            return None

        return self.ref(
            value
        )

    @staticmethod
    def _reference_index(
        reference: str,
    ) -> int:
        if (
            len(reference) < 2
            or reference[0] != "n"
        ):
            raise ValueError(
                "invalid snapshot reference"
            )

        return int(
            reference[1:]
        )
