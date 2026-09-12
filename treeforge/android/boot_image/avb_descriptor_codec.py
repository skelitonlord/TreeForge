from __future__ import annotations

import struct

from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbAnyDescriptor,
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
    AndroidParsedAvbKernelCmdlineDescriptor,
    AndroidParsedAvbPropertyDescriptor,
)


def _round_to_multiple(
    value: int,
    multiple: int,
) -> int:
    if value < 0:
        raise ValueError(
            "value must not be negative"
        )

    if multiple <= 0:
        raise ValueError(
            "multiple must be positive"
        )

    return (
        (value + multiple - 1)
        // multiple
        * multiple
    )


def _require_num_bytes_following(
    descriptor: AndroidParsedAvbAnyDescriptor,
    actual: int,
) -> None:
    if (
        descriptor.num_bytes_following
        != actual
    ):
        raise ValueError(
            "encoded AVB descriptor size disagrees "
            "with canonical Parsing evidence: "
            f"type={type(descriptor).__name__} "
            f"canonical={descriptor.num_bytes_following} "
            f"encoded={actual}"
        )


def _encode_property(
    descriptor: AndroidParsedAvbPropertyDescriptor,
) -> bytes:
    key = descriptor.key.encode(
        "utf-8"
    )

    value = descriptor.value.encode(
        "utf-8"
    )

    fixed_size = 32

    raw_following = (
        fixed_size
        + len(key)
        + 1
        + len(value)
        + 1
        - 16
    )

    num_bytes_following = (
        _round_to_multiple(
            raw_following,
            8,
        )
    )

    _require_num_bytes_following(
        descriptor,
        num_bytes_following,
    )

    padding = (
        num_bytes_following
        - raw_following
    )

    return (
        struct.pack(
            "!QQQQ",
            descriptor.tag,
            num_bytes_following,
            len(key),
            len(value),
        )
        + key
        + b"\0"
        + value
        + b"\0"
        + b"\0" * padding
    )


def _encode_hashtree(
    descriptor: AndroidParsedAvbHashtreeDescriptor,
) -> bytes:
    partition_name = (
        descriptor.partition_name.encode(
            "utf-8"
        )
    )

    hash_algorithm = (
        descriptor.hash_algorithm.encode(
            "ascii"
        )
    )

    if len(hash_algorithm) > 32:
        raise ValueError(
            "AVB hashtree hash algorithm exceeds "
            "the canonical 32-byte field"
        )

    fixed_size = 180

    raw_following = (
        fixed_size
        + len(partition_name)
        + len(descriptor.salt)
        + len(descriptor.root_digest)
        - 16
    )

    num_bytes_following = (
        _round_to_multiple(
            raw_following,
            8,
        )
    )

    _require_num_bytes_following(
        descriptor,
        num_bytes_following,
    )

    padding = (
        num_bytes_following
        - raw_following
    )

    fixed = struct.pack(
        "!QQLQQQLLLQQ32sLLLL60s",
        descriptor.tag,
        num_bytes_following,
        descriptor.dm_verity_version,
        descriptor.image_size,
        descriptor.tree_offset,
        descriptor.tree_size,
        descriptor.data_block_size,
        descriptor.hash_block_size,
        descriptor.fec_num_roots,
        descriptor.fec_offset,
        descriptor.fec_size,
        hash_algorithm,
        len(partition_name),
        len(descriptor.salt),
        len(descriptor.root_digest),
        descriptor.flags,
        b"\0" * 60,
    )

    return (
        fixed
        + partition_name
        + descriptor.salt
        + descriptor.root_digest
        + b"\0" * padding
    )


def _encode_hash(
    descriptor: AndroidParsedAvbHashDescriptor,
) -> bytes:
    partition_name = (
        descriptor.partition_name.encode(
            "utf-8"
        )
    )

    hash_algorithm = (
        descriptor.hash_algorithm.encode(
            "ascii"
        )
    )

    if len(hash_algorithm) > 32:
        raise ValueError(
            "AVB hash algorithm exceeds the "
            "canonical 32-byte field"
        )

    fixed_size = 132

    raw_following = (
        fixed_size
        + len(partition_name)
        + len(descriptor.salt)
        + len(descriptor.digest)
        - 16
    )

    num_bytes_following = (
        _round_to_multiple(
            raw_following,
            8,
        )
    )

    _require_num_bytes_following(
        descriptor,
        num_bytes_following,
    )

    padding = (
        num_bytes_following
        - raw_following
    )

    fixed = struct.pack(
        "!QQQ32sLLLL60s",
        descriptor.tag,
        num_bytes_following,
        descriptor.image_size,
        hash_algorithm,
        len(partition_name),
        len(descriptor.salt),
        len(descriptor.digest),
        descriptor.flags,
        b"\0" * 60,
    )

    return (
        fixed
        + partition_name
        + descriptor.salt
        + descriptor.digest
        + b"\0" * padding
    )


def _encode_kernel_cmdline(
    descriptor: AndroidParsedAvbKernelCmdlineDescriptor,
) -> bytes:
    cmdline = (
        descriptor.kernel_cmdline.encode(
            "utf-8"
        )
    )

    fixed_size = 24

    raw_following = (
        fixed_size
        + len(cmdline)
        - 16
    )

    num_bytes_following = (
        _round_to_multiple(
            raw_following,
            8,
        )
    )

    _require_num_bytes_following(
        descriptor,
        num_bytes_following,
    )

    padding = (
        num_bytes_following
        - raw_following
    )

    return (
        struct.pack(
            "!QQLL",
            descriptor.tag,
            num_bytes_following,
            descriptor.flags,
            len(cmdline),
        )
        + cmdline
        + b"\0" * padding
    )


def _encode_chain_partition(
    descriptor: AndroidParsedAvbChainPartitionDescriptor,
) -> bytes:
    partition_name = (
        descriptor.partition_name.encode(
            "utf-8"
        )
    )

    fixed_size = 92

    raw_following = (
        fixed_size
        + len(partition_name)
        + len(descriptor.public_key)
        - 16
    )

    num_bytes_following = (
        _round_to_multiple(
            raw_following,
            8,
        )
    )

    _require_num_bytes_following(
        descriptor,
        num_bytes_following,
    )

    padding = (
        num_bytes_following
        - raw_following
    )

    fixed = struct.pack(
        "!QQLLLL60s",
        descriptor.tag,
        num_bytes_following,
        descriptor.rollback_index_location,
        len(partition_name),
        len(descriptor.public_key),
        descriptor.flags,
        b"\0" * 60,
    )

    return (
        fixed
        + partition_name
        + descriptor.public_key
        + b"\0" * padding
    )


def _encode_unknown(
    descriptor: AndroidParsedAvbDescriptor,
) -> bytes:
    if (
        len(descriptor.raw_payload)
        != descriptor.num_bytes_following
    ):
        raise ValueError(
            "unknown AVB descriptor raw payload does not "
            "match canonical num_bytes_following"
        )

    return (
        struct.pack(
            "!QQ",
            descriptor.tag,
            descriptor.num_bytes_following,
        )
        + descriptor.raw_payload
    )


def replace_chain_partition_public_key(
    descriptor: AndroidParsedAvbChainPartitionDescriptor,
    public_key: bytes,
) -> AndroidParsedAvbChainPartitionDescriptor:
    """
    Derive a Realization-time chain descriptor from canonical Parsing
    evidence while changing only the trusted public-key payload.

    The derived num_bytes_following is recomputed from the actual encoded
    key length. The canonical descriptor object itself is never mutated.
    """
    if not isinstance(
        descriptor,
        AndroidParsedAvbChainPartitionDescriptor,
    ):
        raise TypeError(
            "descriptor must be an "
            "AndroidParsedAvbChainPartitionDescriptor"
        )

    if (
        not isinstance(
            public_key,
            bytes,
        )
        or not public_key
    ):
        raise ValueError(
            "public_key must be non-empty bytes"
        )

    partition_name = (
        descriptor.partition_name.encode(
            "utf-8"
        )
    )

    fixed_size = 92

    raw_following = (
        fixed_size
        + len(partition_name)
        + len(public_key)
        - 16
    )

    num_bytes_following = (
        _round_to_multiple(
            raw_following,
            8,
        )
    )

    return AndroidParsedAvbChainPartitionDescriptor(
        tag=descriptor.tag,
        num_bytes_following=num_bytes_following,
        rollback_index_location=(
            descriptor.rollback_index_location
        ),
        partition_name=descriptor.partition_name,
        public_key=public_key,
        flags=descriptor.flags,
    )


def encode_avb_descriptor(
    descriptor: AndroidParsedAvbAnyDescriptor,
) -> bytes:
    if isinstance(
        descriptor,
        AndroidParsedAvbPropertyDescriptor,
    ):
        return _encode_property(
            descriptor
        )

    if isinstance(
        descriptor,
        AndroidParsedAvbHashtreeDescriptor,
    ):
        return _encode_hashtree(
            descriptor
        )

    if isinstance(
        descriptor,
        AndroidParsedAvbHashDescriptor,
    ):
        return _encode_hash(
            descriptor
        )

    if isinstance(
        descriptor,
        AndroidParsedAvbKernelCmdlineDescriptor,
    ):
        return _encode_kernel_cmdline(
            descriptor
        )

    if isinstance(
        descriptor,
        AndroidParsedAvbChainPartitionDescriptor,
    ):
        return _encode_chain_partition(
            descriptor
        )

    if isinstance(
        descriptor,
        AndroidParsedAvbDescriptor,
    ):
        return _encode_unknown(
            descriptor
        )

    raise TypeError(
        "unsupported canonical AVB descriptor type: "
        f"{type(descriptor).__name__}"
    )


def encode_avb_descriptor_sequence(
    descriptors: tuple[
        AndroidParsedAvbAnyDescriptor,
        ...,
    ],
) -> bytes:
    if not isinstance(
        descriptors,
        tuple,
    ):
        raise TypeError(
            "descriptors must be a tuple"
        )

    return b"".join(
        encode_avb_descriptor(
            descriptor
        )
        for descriptor
        in descriptors
    )
