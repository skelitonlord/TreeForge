from __future__ import annotations

from treeforge.android.persistence.codec import (
    SnapshotCodec,
)


class SnapshotCodecRegistry:
    """
    Registry of explicit canonical object-graph codecs.

    No generic dataclass fallback is provided. Every canonical family that
    crosses a persisted boundary must opt into an explicit codec so identity
    and provenance semantics cannot be silently flattened.
    """

    def __init__(
        self,
    ) -> None:
        self._by_type: dict[
            type,
            SnapshotCodec,
        ] = {}

        self._by_tag: dict[
            str,
            SnapshotCodec,
        ] = {}

    def register(
        self,
        codec: SnapshotCodec,
    ) -> None:
        python_type = codec.python_type
        type_tag = codec.type_tag

        if not isinstance(
            python_type,
            type,
        ):
            raise TypeError(
                "codec.python_type must be a type"
            )

        if not isinstance(
            type_tag,
            str,
        ):
            raise TypeError(
                "codec.type_tag must be a string"
            )

        if not type_tag.strip():
            raise ValueError(
                "codec.type_tag must not be empty"
            )

        existing_type = self._by_type.get(
            python_type
        )

        if (
            existing_type is not None
            and existing_type is not codec
        ):
            raise ValueError(
                "duplicate snapshot codec for "
                f"{python_type.__qualname__}"
            )

        existing_tag = self._by_tag.get(
            type_tag
        )

        if (
            existing_tag is not None
            and existing_tag is not codec
        ):
            raise ValueError(
                "duplicate snapshot codec type tag: "
                f"{type_tag}"
            )

        self._by_type[python_type] = codec
        self._by_tag[type_tag] = codec

    def codec_for_value(
        self,
        value: object,
    ) -> SnapshotCodec:
        codec = self._by_type.get(
            type(
                value
            )
        )

        if codec is None:
            raise TypeError(
                "no snapshot codec registered for "
                f"{type(value).__module__}."
                f"{type(value).__qualname__}"
            )

        return codec

    def codec_for_tag(
        self,
        type_tag: str,
    ) -> SnapshotCodec:
        codec = self._by_tag.get(
            type_tag
        )

        if codec is None:
            raise ValueError(
                "unknown snapshot codec type tag: "
                f"{type_tag}"
            )

        return codec
