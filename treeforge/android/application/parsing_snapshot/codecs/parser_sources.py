from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
)
from treeforge.android.filesystem.filesystem import (
    Filesystem,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidFilesystemView,
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
    AndroidParserFilesystemSource,
    AndroidPartitionFilesystem,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)


def _encode_filesystem(
    value: Filesystem,
) -> dict[str, Any]:
    if not isinstance(
        value,
        Filesystem,
    ):
        raise TypeError(
            "value must be a Filesystem"
        )

    return {
        "root": str(
            value.root
        ),
    }


def _decode_filesystem(
    payload: object,
) -> Filesystem:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "Filesystem payload must be a dict"
        )

    root = payload.get(
        "root"
    )

    if not isinstance(
        root,
        str,
    ):
        raise TypeError(
            "Filesystem root must be a string"
        )

    return Filesystem(
        root=Path(
            root
        ),
    )


def _encode_view(
    value: AndroidFilesystemView,
) -> dict[str, Any]:
    return {
        "filesystem": _encode_filesystem(
            value.filesystem
        ),
        "android_prefix": str(
            value.android_prefix
        ),
    }


def _decode_view(
    payload: object,
) -> AndroidFilesystemView:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "AndroidFilesystemView payload "
            "must be a dict"
        )

    return AndroidFilesystemView(
        filesystem=_decode_filesystem(
            payload[
                "filesystem"
            ]
        ),
        android_prefix=PurePosixPath(
            payload[
                "android_prefix"
            ]
        ),
    )


def _optional_ref(
    encoder: SnapshotGraphEncoder,
    value: object | None,
) -> dict[str, str] | None:
    if value is None:
        return None

    return encoder.ref(
        value
    )


def _decode_optional_ref(
    decoder: SnapshotGraphDecoder,
    value: object,
) -> object | None:
    if value is None:
        return None

    return decoder.ref(
        value
    )


class AndroidParserFilesystemSourceCodec:
    type_tag = (
        "android.parser_filesystem_source"
    )

    python_type = (
        AndroidParserFilesystemSource
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "value must be an "
                "AndroidParserFilesystemSource"
            )

        return {
            "source_name": value.source_name,
            "artifact": encoder.ref(
                value.artifact
            ),
            "filesystem": _encode_filesystem(
                value.filesystem
            ),
            "views": [
                _encode_view(
                    view
                )
                for view in value.views
            ],
            "partition": _optional_ref(
                encoder,
                value.partition,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored parser source artifact "
                "must be an ExtractedArtifact"
            )

        partition = _decode_optional_ref(
            decoder,
            payload.get(
                "partition"
            ),
        )

        if (
            partition is not None
            and not isinstance(
                partition,
                InventoryPartition,
            )
        ):
            raise TypeError(
                "restored parser partition must be "
                "an InventoryPartition or None"
            )

        views_payload = payload.get(
            "views"
        )

        if not isinstance(
            views_payload,
            list,
        ):
            raise TypeError(
                "parser filesystem views must be a list"
            )

        return AndroidParserFilesystemSource(
            source_name=payload[
                "source_name"
            ],
            artifact=artifact,
            filesystem=_decode_filesystem(
                payload[
                    "filesystem"
                ]
            ),
            views=tuple(
                _decode_view(
                    view
                )
                for view
                in views_payload
            ),
            partition=partition,
        )


class AndroidPartitionFilesystemCodec:
    type_tag = (
        "android.partition_filesystem_source"
    )

    python_type = (
        AndroidPartitionFilesystem
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidPartitionFilesystem,
        ):
            raise TypeError(
                "value must be an "
                "AndroidPartitionFilesystem"
            )

        return {
            "source_name": value.source_name,
            "artifact": encoder.ref(
                value.artifact
            ),
            "filesystem": _encode_filesystem(
                value.filesystem
            ),
            "views": [
                _encode_view(
                    view
                )
                for view in value.views
            ],
            "partition": encoder.ref(
                value.partition
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        partition = decoder.ref(
            payload[
                "partition"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored parser artifact must be "
                "an ExtractedArtifact"
            )

        if not isinstance(
            partition,
            InventoryPartition,
        ):
            raise TypeError(
                "restored parser partition must be "
                "an InventoryPartition"
            )

        views_payload = payload.get(
            "views"
        )

        if not isinstance(
            views_payload,
            list,
        ):
            raise TypeError(
                "parser filesystem views must be a list"
            )

        return AndroidPartitionFilesystem(
            source_name=payload[
                "source_name"
            ],
            artifact=artifact,
            filesystem=_decode_filesystem(
                payload[
                    "filesystem"
                ]
            ),
            views=tuple(
                _decode_view(
                    view
                )
                for view
                in views_payload
            ),
            partition=partition,
        )


class AndroidModelSourceCodec:
    type_tag = (
        "android.model_source"
    )

    python_type = (
        AndroidModelSource
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidModelSource,
        ):
            raise TypeError(
                "value must be an AndroidModelSource"
            )

        return {
            "kind": value.kind.value,
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "android_path": str(
                value.android_path
            ),
            "host_path": str(
                value.host_path
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        filesystem_source = decoder.ref(
            payload[
                "filesystem_source"
            ]
        )

        if not isinstance(
            filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "restored model source filesystem "
                "must be an "
                "AndroidParserFilesystemSource"
            )

        return AndroidModelSource(
            kind=AndroidModelSourceKind(
                payload[
                    "kind"
                ]
            ),
            filesystem_source=(
                filesystem_source
            ),
            android_path=PurePosixPath(
                payload[
                    "android_path"
                ]
            ),
            host_path=Path(
                payload[
                    "host_path"
                ]
            ),
        )


class AndroidModelSourceInventoryCodec:
    type_tag = (
        "android.model_source_inventory"
    )

    python_type = (
        AndroidModelSourceInventory
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "value must be an "
                "AndroidModelSourceInventory"
            )

        return {
            "filesystems": [
                encoder.ref(
                    filesystem
                )
                for filesystem
                in value.filesystems
            ],
            "sources": [
                encoder.ref(
                    source
                )
                for source
                in value.sources
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        filesystem_refs = payload.get(
            "filesystems",
            [],
        )

        source_refs = payload.get(
            "sources",
            [],
        )

        if not isinstance(
            filesystem_refs,
            list,
        ):
            raise TypeError(
                "filesystems must be a list"
            )

        if not isinstance(
            source_refs,
            list,
        ):
            raise TypeError(
                "sources must be a list"
            )

        filesystems = tuple(
            decoder.ref(
                reference
            )
            for reference
            in filesystem_refs
        )

        sources = tuple(
            decoder.ref(
                reference
            )
            for reference
            in source_refs
        )

        if not all(
            isinstance(
                filesystem,
                AndroidParserFilesystemSource,
            )
            for filesystem
            in filesystems
        ):
            raise TypeError(
                "restored filesystems must contain "
                "AndroidParserFilesystemSource objects"
            )

        if not all(
            isinstance(
                source,
                AndroidModelSource,
            )
            for source
            in sources
        ):
            raise TypeError(
                "restored sources must contain "
                "AndroidModelSource objects"
            )

        return AndroidModelSourceInventory(
            filesystems=filesystems,
            sources=sources,
        )


PARSER_SOURCE_CODECS = (
    AndroidParserFilesystemSourceCodec(),
    AndroidPartitionFilesystemCodec(),
    AndroidModelSourceCodec(),
    AndroidModelSourceInventoryCodec(),
)
