from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
    PartitionInventory,
)
from treeforge.android.partition.layout import (
    LayoutBlockDevice,
    LayoutPartition,
    LayoutPartitionGroup,
    PartitionLayout,
    PartitionLayoutSource,
    PartitionOrigin,
)
from treeforge.android.partition.source import (
    PartitionSource,
)
from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
    ProviderArtifactKind,
    ProviderArtifactKindEvidence,
)
from treeforge.android.providers.content_observation import (
    ProviderContentObservation,
    ProviderContentObservationConfidence,
    ProviderContentSignature,
)
from treeforge.android.providers.provenance import (
    ProviderArtifactProvenance,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)


def _encode_bytes(
    value: bytes | None,
) -> str | None:
    if value is None:
        return None

    return base64.b64encode(
        value
    ).decode(
        "ascii"
    )


def _decode_bytes(
    value: object,
    *,
    field_name: str,
) -> bytes | None:
    if value is None:
        return None

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string or None"
        )

    try:
        return base64.b64decode(
            value.encode(
                "ascii"
            ),
            validate=True,
        )
    except Exception as error:
        raise ValueError(
            f"{field_name} is not valid base64"
        ) from error


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


def _encode_provenance(
    value: ProviderArtifactProvenance,
) -> dict[
    str,
    Any,
]:
    return {
        "parent_source_name": value.parent_source_name,
        "member_path": value.member_path,
        "original_member_path": (
            value.original_member_path
        ),
        "container_depth": value.container_depth,
        "size_bytes": value.size_bytes,
        "compressed_size_bytes": (
            value.compressed_size_bytes
        ),
        "compression_method": (
            value.compression_method
        ),
        "crc32": value.crc32,
        "modified_time": (
            list(
                value.modified_time
            )
            if value.modified_time is not None
            else None
        ),
        "flag_bits": value.flag_bits,
        "create_system": value.create_system,
        "create_version": value.create_version,
        "extract_version": value.extract_version,
        "volume": value.volume,
        "internal_attributes": (
            value.internal_attributes
        ),
        "external_attributes": (
            value.external_attributes
        ),
        "extra": _encode_bytes(
            value.extra
        ),
        "comment": _encode_bytes(
            value.comment
        ),
        "header_offset": value.header_offset,
    }


def _decode_provenance(
    payload: object,
) -> ProviderArtifactProvenance:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "ProviderArtifact provenance payload "
            "must be a dict"
        )

    modified_time = payload.get(
        "modified_time"
    )

    if modified_time is not None:
        if not isinstance(
            modified_time,
            list,
        ):
            raise TypeError(
                "modified_time must be a list or None"
            )

        modified_time = tuple(
            modified_time
        )

    return ProviderArtifactProvenance(
        parent_source_name=payload.get(
            "parent_source_name"
        ),
        member_path=payload.get(
            "member_path"
        ),
        original_member_path=payload.get(
            "original_member_path"
        ),
        container_depth=payload.get(
            "container_depth",
            0,
        ),
        size_bytes=payload.get(
            "size_bytes"
        ),
        compressed_size_bytes=payload.get(
            "compressed_size_bytes"
        ),
        compression_method=payload.get(
            "compression_method"
        ),
        crc32=payload.get(
            "crc32"
        ),
        modified_time=modified_time,
        flag_bits=payload.get(
            "flag_bits"
        ),
        create_system=payload.get(
            "create_system"
        ),
        create_version=payload.get(
            "create_version"
        ),
        extract_version=payload.get(
            "extract_version"
        ),
        volume=payload.get(
            "volume"
        ),
        internal_attributes=payload.get(
            "internal_attributes"
        ),
        external_attributes=payload.get(
            "external_attributes"
        ),
        extra=_decode_bytes(
            payload.get(
                "extra"
            ),
            field_name="extra",
        ),
        comment=_decode_bytes(
            payload.get(
                "comment"
            ),
            field_name="comment",
        ),
        header_offset=payload.get(
            "header_offset"
        ),
    )


def _encode_observation(
    value: ProviderContentObservation,
) -> dict[
    str,
    Any,
]:
    return {
        "signature": value.signature.value,
        "confidence": value.confidence.value,
        "offset": value.offset,
        "matched_bytes": _encode_bytes(
            value.matched_bytes
        ),
    }


def _decode_observation(
    payload: object,
) -> ProviderContentObservation:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "ProviderContentObservation payload "
            "must be a dict"
        )

    matched_bytes = _decode_bytes(
        payload.get(
            "matched_bytes"
        ),
        field_name="matched_bytes",
    )

    if matched_bytes is None:
        matched_bytes = b""

    return ProviderContentObservation(
        signature=ProviderContentSignature(
            payload["signature"]
        ),
        confidence=(
            ProviderContentObservationConfidence(
                payload["confidence"]
            )
        ),
        offset=payload["offset"],
        matched_bytes=matched_bytes,
    )


def _encode_fact(
    value: ExtractionFact,
) -> dict[
    str,
    Any,
]:
    return {
        "name": value.name,
        "value": value.value,
    }


def _decode_fact(
    payload: object,
) -> ExtractionFact:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "ExtractionFact payload must be a dict"
        )

    return ExtractionFact(
        name=payload["name"],
        value=payload["value"],
    )


def _encode_tool(
    value: ExtractionToolEvidence | None,
) -> dict[
    str,
    Any,
] | None:
    if value is None:
        return None

    return {
        "name": value.name,
        "executable": value.executable,
        "command": list(
            value.command
        ),
        "returncode": value.returncode,
        "stdout": value.stdout,
        "stderr": value.stderr,
    }


def _decode_tool(
    payload: object,
) -> ExtractionToolEvidence | None:
    if payload is None:
        return None

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "ExtractionToolEvidence payload "
            "must be a dict or None"
        )

    command = payload.get(
        "command",
        [],
    )

    if not isinstance(
        command,
        list,
    ):
        raise TypeError(
            "tool command must be a list"
        )

    return ExtractionToolEvidence(
        name=payload["name"],
        executable=payload.get(
            "executable"
        ),
        command=tuple(
            command
        ),
        returncode=payload.get(
            "returncode"
        ),
        stdout=payload.get(
            "stdout"
        ),
        stderr=payload.get(
            "stderr"
        ),
    )


class ProviderArtifactCodec:
    type_tag = (
        "android.provider_artifact"
    )

    python_type = (
        ProviderArtifact
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
            ProviderArtifact,
        ):
            raise TypeError(
                "value must be a ProviderArtifact"
            )

        return {
            "source_name": value.source_name,
            "name": value.name,
            "kind": value.kind.value,
            "classification": (
                value.classification.value
            ),
            "provider_id": value.provider_id,
            "source_type": value.source_type.value,
            "provenance": _encode_provenance(
                value.provenance
            ),
            "kind_evidence": (
                value.kind_evidence.value
            ),
            "content_observations": [
                _encode_observation(
                    observation
                )
                for observation
                in value.content_observations
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
        observations = payload.get(
            "content_observations",
            [],
        )

        if not isinstance(
            observations,
            list,
        ):
            raise TypeError(
                "content_observations must be a list"
            )

        return ProviderArtifact(
            source_name=payload[
                "source_name"
            ],
            name=payload[
                "name"
            ],
            kind=ProviderArtifactKind(
                payload[
                    "kind"
                ]
            ),
            classification=(
                ProviderArtifactClassification(
                    payload[
                        "classification"
                    ]
                )
            ),
            provider_id=payload[
                "provider_id"
            ],
            source_type=ProviderSourceType(
                payload[
                    "source_type"
                ]
            ),
            provenance=_decode_provenance(
                payload[
                    "provenance"
                ]
            ),
            kind_evidence=(
                ProviderArtifactKindEvidence(
                    payload[
                        "kind_evidence"
                    ]
                )
            ),
            content_observations=tuple(
                _decode_observation(
                    observation
                )
                for observation
                in observations
            ),
        )


class ExtractedArtifactCodec:
    type_tag = (
        "android.extracted_artifact"
    )

    python_type = (
        ExtractedArtifact
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
            ExtractedArtifact,
        ):
            raise TypeError(
                "value must be an ExtractedArtifact"
            )

        return {
            "source": _optional_ref(
                encoder,
                value.source,
            ),
            "path": str(
                value.path
            ),
            "kind": value.kind.value,
            "operation": value.operation.value,
            "semantic_name": value.semantic_name,
            "parent": _optional_ref(
                encoder,
                value.parent,
            ),
            "tool": _encode_tool(
                value.tool
            ),
            "facts": [
                _encode_fact(
                    fact
                )
                for fact in value.facts
            ],
            "content_sha256": (
                value.content_sha256
            ),
            "size_bytes": value.size_bytes,
        }

    def decode(
        self,
        payload: dict[
            str,
            Any,
        ],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        facts = payload.get(
            "facts",
            [],
        )

        if not isinstance(
            facts,
            list,
        ):
            raise TypeError(
                "facts must be a list"
            )

        source = _decode_optional_ref(
            decoder,
            payload.get(
                "source"
            ),
        )

        parent = _decode_optional_ref(
            decoder,
            payload.get(
                "parent"
            ),
        )

        if (
            source is not None
            and not isinstance(
                source,
                ProviderArtifact,
            )
        ):
            raise TypeError(
                "restored source must be "
                "a ProviderArtifact or None"
            )

        if (
            parent is not None
            and not isinstance(
                parent,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "restored parent must be "
                "an ExtractedArtifact or None"
            )

        return ExtractedArtifact(
            source=source,
            path=Path(
                payload[
                    "path"
                ]
            ),
            kind=ExtractionArtifactKind(
                payload[
                    "kind"
                ]
            ),
            operation=ExtractionOperation(
                payload[
                    "operation"
                ]
            ),
            semantic_name=payload.get(
                "semantic_name"
            ),
            parent=parent,
            tool=_decode_tool(
                payload.get(
                    "tool"
                )
            ),
            facts=tuple(
                _decode_fact(
                    fact
                )
                for fact in facts
            ),
            content_sha256=payload.get(
                "content_sha256"
            ),
            size_bytes=payload.get(
                "size_bytes"
            ),
        )


class InventoryPartitionCodec:
    type_tag = (
        "android.inventory_partition"
    )

    python_type = (
        InventoryPartition
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
            InventoryPartition,
        ):
            raise TypeError(
                "value must be an InventoryPartition"
            )

        return {
            "name": value.name,
            "artifact": encoder.ref(
                value.artifact
            ),
            "slot_suffix": value.slot_suffix,
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
                "restored inventory artifact must "
                "be an ExtractedArtifact"
            )

        return InventoryPartition(
            name=payload[
                "name"
            ],
            artifact=artifact,
            slot_suffix=payload.get(
                "slot_suffix"
            ),
        )


class PartitionInventoryCodec:
    type_tag = (
        "android.partition_inventory"
    )

    python_type = (
        PartitionInventory
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
            PartitionInventory,
        ):
            raise TypeError(
                "value must be a PartitionInventory"
            )

        return {
            "partitions": [
                encoder.ref(
                    partition
                )
                for partition
                in value.partitions
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
            "partitions",
            [],
        )

        if not isinstance(
            references,
            list,
        ):
            raise TypeError(
                "partitions must be a list"
            )

        partitions = tuple(
            decoder.ref(
                reference
            )
            for reference
            in references
        )

        if not all(
            isinstance(
                partition,
                InventoryPartition,
            )
            for partition
            in partitions
        ):
            raise TypeError(
                "restored partitions must contain "
                "only InventoryPartition instances"
            )

        return PartitionInventory(
            partitions=partitions
        )



class PartitionSourceCodec:
    type_tag = "android.partition_source"
    python_type = PartitionSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            PartitionSource,
        ):
            raise TypeError(
                "value must be a PartitionSource"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
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
            ProviderArtifact,
        ):
            raise TypeError(
                "restored partition source artifact "
                "must be a ProviderArtifact"
            )

        return PartitionSource(
            artifact=artifact,
        )


class LayoutPartitionCodec:
    type_tag = "android.layout_partition"
    python_type = LayoutPartition

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            LayoutPartition,
        ):
            raise TypeError(
                "value must be a LayoutPartition"
            )

        return {
            "name": value.name,
            "origin": value.origin.value,
            "source": (
                None
                if value.source is None
                else encoder.ref(
                    value.source
                )
            ),
            "size_bytes": value.size_bytes,
            "readonly": value.readonly,
            "slot_suffix": value.slot_suffix,
            "group": value.group,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source_ref = payload.get(
            "source"
        )

        source = (
            None
            if source_ref is None
            else decoder.ref(
                source_ref
            )
        )

        if (
            source is not None
            and not isinstance(
                source,
                PartitionSource,
            )
        ):
            raise TypeError(
                "restored layout partition source "
                "must be a PartitionSource or None"
            )

        return LayoutPartition(
            name=payload[
                "name"
            ],
            origin=PartitionOrigin(
                payload[
                    "origin"
                ]
            ),
            source=source,
            size_bytes=payload.get(
                "size_bytes"
            ),
            readonly=payload.get(
                "readonly"
            ),
            slot_suffix=payload.get(
                "slot_suffix"
            ),
            group=payload.get(
                "group"
            ),
        )


class LayoutPartitionGroupCodec:
    type_tag = "android.layout_partition_group"
    python_type = LayoutPartitionGroup

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            LayoutPartitionGroup,
        ):
            raise TypeError(
                "value must be a LayoutPartitionGroup"
            )

        return {
            "name": value.name,
            "maximum_size_bytes": (
                value.maximum_size_bytes
            ),
            "slot_suffix": value.slot_suffix,
            "flags": sorted(
                value.flags
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        flags = payload.get(
            "flags",
            [],
        )

        if not isinstance(
            flags,
            list,
        ):
            raise TypeError(
                "restored layout group flags "
                "must be a list"
            )

        if not all(
            isinstance(
                flag,
                str,
            )
            for flag in flags
        ):
            raise TypeError(
                "restored layout group flags "
                "must contain only strings"
            )

        return LayoutPartitionGroup(
            name=payload[
                "name"
            ],
            maximum_size_bytes=payload.get(
                "maximum_size_bytes"
            ),
            slot_suffix=payload.get(
                "slot_suffix"
            ),
            flags=frozenset(
                flags
            ),
        )


class LayoutBlockDeviceCodec:
    type_tag = "android.layout_block_device"
    python_type = LayoutBlockDevice

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            LayoutBlockDevice,
        ):
            raise TypeError(
                "value must be a LayoutBlockDevice"
            )

        return {
            "partition_name": (
                value.partition_name
            ),
            "size_bytes": (
                value.size_bytes
            ),
            "first_logical_sector": (
                value.first_logical_sector
            ),
            "alignment_bytes": (
                value.alignment_bytes
            ),
            "alignment_offset_bytes": (
                value.alignment_offset_bytes
            ),
            "flags": sorted(
                value.flags
            ),
            "raw_flags": (
                value.raw_flags
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        flags = payload.get(
            "flags",
            [],
        )

        if not isinstance(
            flags,
            list,
        ):
            raise TypeError(
                "restored block-device flags "
                "must be a list"
            )

        if not all(
            isinstance(
                flag,
                str,
            )
            for flag in flags
        ):
            raise TypeError(
                "restored block-device flags "
                "must contain only strings"
            )

        return LayoutBlockDevice(
            partition_name=payload[
                "partition_name"
            ],
            size_bytes=payload[
                "size_bytes"
            ],
            first_logical_sector=(
                payload.get(
                    "first_logical_sector"
                )
            ),
            alignment_bytes=(
                payload.get(
                    "alignment_bytes"
                )
            ),
            alignment_offset_bytes=(
                payload.get(
                    "alignment_offset_bytes"
                )
            ),
            flags=frozenset(
                flags
            ),
            raw_flags=payload.get(
                "raw_flags"
            ),
        )

class PartitionLayoutCodec:
    type_tag = "android.partition_layout"
    python_type = PartitionLayout

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            PartitionLayout,
        ):
            raise TypeError(
                "value must be a PartitionLayout"
            )

        return {
            "source": (
                value.source.value
            ),
            "partitions": [
                encoder.ref(
                    partition
                )
                for partition
                in value.partitions
            ],
            "groups": [
                encoder.ref(
                    group
                )
                for group
                in value.groups
            ],
            "block_devices": [
                encoder.ref(
                    block_device
                )
                for block_device
                in value.block_devices
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        partitions = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload.get(
                "partitions",
                [],
            )
        )

        groups = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload.get(
                "groups",
                [],
            )
        )

        block_devices = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload.get(
                "block_devices",
                [],
            )
        )

        if not all(
            isinstance(
                partition,
                LayoutPartition,
            )
            for partition
            in partitions
        ):
            raise TypeError(
                "restored PartitionLayout partitions "
                "must contain only LayoutPartition instances"
            )

        if not all(
            isinstance(
                group,
                LayoutPartitionGroup,
            )
            for group
            in groups
        ):
            raise TypeError(
                "restored PartitionLayout groups "
                "must contain only "
                "LayoutPartitionGroup instances"
            )

        if not all(
            isinstance(
                block_device,
                LayoutBlockDevice,
            )
            for block_device
            in block_devices
        ):
            raise TypeError(
                "restored PartitionLayout block_devices "
                "must contain only "
                "LayoutBlockDevice instances"
            )

        return PartitionLayout(
            source=PartitionLayoutSource(
                payload[
                    "source"
                ]
            ),
            partitions=partitions,
            groups=groups,
            block_devices=block_devices,
        )



IDENTITY_SPINE_CODECS = (
    ProviderArtifactCodec(),
    ExtractedArtifactCodec(),
    PartitionSourceCodec(),
    LayoutPartitionCodec(),
    LayoutPartitionGroupCodec(),
    LayoutBlockDeviceCodec(),
    PartitionLayoutCodec(),
    InventoryPartitionCodec(),
    PartitionInventoryCodec(),
)
