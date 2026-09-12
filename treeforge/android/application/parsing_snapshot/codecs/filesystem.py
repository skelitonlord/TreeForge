from __future__ import annotations

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
from treeforge.android.filesystem.backends.manager import (
    FilesystemBackendResult,
    FilesystemSourceType,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
    FilesystemMetadataInventoryEntry,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadata,
    FilesystemMetadataEntry,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)


def _optional_ref(
    encoder: SnapshotGraphEncoder,
    value: object | None,
) -> dict[
    str,
    str,
] | None:
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


class FilesystemMetadataEntryCodec:
    """
    Persist one canonical filesystem metadata entry as a graph object.

    FilesystemMetadataEntry belongs to the canonical Parsing handoff graph.
    Exact entry identity must therefore survive snapshot restoration.
    """

    type_tag = (
        "android.filesystem_metadata_entry"
    )

    python_type = (
        FilesystemMetadataEntry
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "value must be a FilesystemMetadataEntry"
            )

        return {
            "path": value.path,
            "data": value.to_dict(),
        }

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        path = payload.get(
            "path"
        )
        data = payload.get(
            "data"
        )

        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "filesystem metadata entry path "
                "must be a string"
            )

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "filesystem metadata entry data "
                "must be a dict"
            )

        return FilesystemMetadataEntry.from_dict(
            path,
            data,
        )


class FilesystemMetadataCodec:
    """
    Persist canonical filesystem metadata as part of the Parsing graph.

    Entries are graph references so every Parsing consumer observes the
    exact same restored FilesystemMetadataEntry instances.
    """

    type_tag = (
        "android.filesystem_metadata"
    )

    python_type = (
        FilesystemMetadata
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            FilesystemMetadata,
        ):
            raise TypeError(
                "value must be a FilesystemMetadata"
            )

        return {
            "schema_version": value.schema_version,
            "filesystem_type": value.filesystem_type,
            "source": str(
                value.source
            ),
            "entries": [
                {
                    "path": entry_path,
                    "entry": encoder.ref(
                        entry
                    ),
                }
                for entry_path, entry
                in sorted(
                    value.entries.items()
                )
            ],
        }

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        entries_payload = payload.get(
            "entries"
        )

        if not isinstance(
            entries_payload,
            list,
        ):
            raise TypeError(
                "filesystem metadata entries "
                "must be a list"
            )

        entries: dict[
            str,
            FilesystemMetadataEntry,
        ] = {}

        for item in entries_payload:
            if not isinstance(
                item,
                dict,
            ):
                raise TypeError(
                    "filesystem metadata entry reference "
                    "must be a dict"
                )

            entry_path = item.get(
                "path"
            )

            if not isinstance(
                entry_path,
                str,
            ):
                raise TypeError(
                    "filesystem metadata entry path "
                    "must be a string"
                )

            entry = decoder.ref(
                item.get(
                    "entry"
                )
            )

            if not isinstance(
                entry,
                FilesystemMetadataEntry,
            ):
                raise TypeError(
                    "restored filesystem metadata entry "
                    "must be a FilesystemMetadataEntry"
                )

            if entry.path != entry_path:
                raise ValueError(
                    "restored filesystem metadata entry "
                    "path does not match graph key"
                )

            entries[
                entry_path
            ] = entry

        filesystem_type = payload.get(
            "filesystem_type"
        )
        source = payload.get(
            "source"
        )
        schema_version = payload.get(
            "schema_version"
        )

        if not isinstance(
            filesystem_type,
            str,
        ):
            raise TypeError(
                "filesystem metadata filesystem_type "
                "must be a string"
            )

        if not isinstance(
            source,
            str,
        ):
            raise TypeError(
                "filesystem metadata source "
                "must be a string"
            )

        if not isinstance(
            schema_version,
            int,
        ):
            raise TypeError(
                "filesystem metadata schema_version "
                "must be an int"
            )

        from pathlib import Path

        return FilesystemMetadata(
            filesystem_type=filesystem_type,
            source=Path(
                source
            ),
            entries=entries,
            schema_version=schema_version,
        )


class FilesystemBackendResultCodec:
    """
    Persist one canonical filesystem-metadata result.

    FilesystemMetadata is an immutable value object with its own explicit
    serialization contract, while artifact and partition are canonical
    identity-bearing graph objects and therefore remain references.
    """

    type_tag = (
        "android.filesystem_backend_result"
    )

    python_type = (
        FilesystemBackendResult
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            FilesystemBackendResult,
        ):
            raise TypeError(
                "value must be a FilesystemBackendResult"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "source_type": (
                value.source_type.value
            ),
            "metadata": encoder.ref(
                value.metadata
            ),
            "partition": _optional_ref(
                encoder,
                value.partition,
            ),
        }

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
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
                "restored filesystem artifact must "
                "be an ExtractedArtifact"
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
                "restored filesystem partition must "
                "be an InventoryPartition or None"
            )

        metadata = decoder.ref(
            payload[
                "metadata"
            ]
        )

        if not isinstance(
            metadata,
            FilesystemMetadata,
        ):
            raise TypeError(
                "restored filesystem metadata must "
                "be a FilesystemMetadata"
            )

        return FilesystemBackendResult(
            artifact=artifact,
            source_type=FilesystemSourceType(
                payload[
                    "source_type"
                ]
            ),
            metadata=metadata,
            partition=partition,
        )


class FilesystemMetadataInventoryEntryCodec:
    type_tag = (
        "android.filesystem_metadata_inventory_entry"
    )

    python_type = (
        FilesystemMetadataInventoryEntry
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            FilesystemMetadataInventoryEntry,
        ):
            raise TypeError(
                "value must be a "
                "FilesystemMetadataInventoryEntry"
            )

        return {
            "result": encoder.ref(
                value.result
            ),
        }

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        result = decoder.ref(
            payload[
                "result"
            ]
        )

        if not isinstance(
            result,
            FilesystemBackendResult,
        ):
            raise TypeError(
                "restored inventory result must be "
                "a FilesystemBackendResult"
            )

        return FilesystemMetadataInventoryEntry(
            result=result
        )


class FilesystemMetadataInventoryCodec:
    type_tag = (
        "android.filesystem_metadata_inventory"
    )

    python_type = (
        FilesystemMetadataInventory
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[
        str,
        Any,
    ]:
        if not isinstance(
            value,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "value must be a "
                "FilesystemMetadataInventory"
            )

        return {
            "entries": [
                encoder.ref(
                    entry
                )
                for entry
                in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        references = payload.get(
            "entries",
            [],
        )

        if not isinstance(
            references,
            list,
        ):
            raise TypeError(
                "filesystem metadata entries "
                "must be a list"
            )

        entries = tuple(
            decoder.ref(
                reference
            )
            for reference
            in references
        )

        if not all(
            isinstance(
                entry,
                FilesystemMetadataInventoryEntry,
            )
            for entry
            in entries
        ):
            raise TypeError(
                "restored filesystem metadata entries "
                "must contain only "
                "FilesystemMetadataInventoryEntry objects"
            )

        return FilesystemMetadataInventory(
            entries=entries
        )


FILESYSTEM_CODECS = (
    FilesystemMetadataEntryCodec(),
    FilesystemMetadataCodec(),
    FilesystemBackendResultCodec(),
    FilesystemMetadataInventoryEntryCodec(),
    FilesystemMetadataInventoryCodec(),
)
