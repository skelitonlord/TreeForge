from __future__ import annotations

from typing import (
    Any,
    Protocol,
    TYPE_CHECKING,
)


if TYPE_CHECKING:
    from treeforge.android.persistence.decoder import (
        SnapshotGraphDecoder,
    )
    from treeforge.android.persistence.encoder import (
        SnapshotGraphEncoder,
    )


class SnapshotCodec(
    Protocol,
):
    """
    Explicit serialization contract for one canonical object family.

    Persistence behavior stays outside canonical domain models.
    """

    type_tag: str
    python_type: type

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[
        str,
        Any,
    ]:
        ...

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        ...
