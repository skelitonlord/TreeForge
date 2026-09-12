from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class AndroidParsedAvbDescriptor:
    tag: int
    num_bytes_following: int
    raw_payload: bytes


@dataclass(frozen=True, slots=True)
class AndroidParsedAvbPropertyDescriptor:
    tag: int
    num_bytes_following: int
    key: str
    value: str


@dataclass(frozen=True, slots=True)
class AndroidParsedAvbHashtreeDescriptor:
    tag: int
    num_bytes_following: int
    dm_verity_version: int
    image_size: int
    tree_offset: int
    tree_size: int
    data_block_size: int
    hash_block_size: int
    fec_num_roots: int
    fec_offset: int
    fec_size: int
    hash_algorithm: str
    partition_name: str
    salt: bytes
    root_digest: bytes
    flags: int


@dataclass(frozen=True, slots=True)
class AndroidParsedAvbHashDescriptor:
    tag: int
    num_bytes_following: int
    image_size: int
    hash_algorithm: str
    partition_name: str
    salt: bytes
    digest: bytes
    flags: int


@dataclass(frozen=True, slots=True)
class AndroidParsedAvbKernelCmdlineDescriptor:
    tag: int
    num_bytes_following: int
    flags: int
    kernel_cmdline: str


@dataclass(frozen=True, slots=True)
class AndroidParsedAvbChainPartitionDescriptor:
    tag: int
    num_bytes_following: int
    rollback_index_location: int
    partition_name: str
    public_key: bytes
    flags: int


AndroidParsedAvbKnownDescriptor = (
    AndroidParsedAvbPropertyDescriptor
    | AndroidParsedAvbHashtreeDescriptor
    | AndroidParsedAvbHashDescriptor
    | AndroidParsedAvbKernelCmdlineDescriptor
    | AndroidParsedAvbChainPartitionDescriptor
)

AndroidParsedAvbAnyDescriptor = (
    AndroidParsedAvbKnownDescriptor
    | AndroidParsedAvbDescriptor
)


@dataclass(frozen=True, slots=True)
class AndroidParsedAvbFooter:
    """
    Literal AVB footer metadata describing one embedded VBMeta payload.

    The footer describes where the VBMeta block lives inside its containing
    partition image. Trust-chain interpretation remains downstream.
    """

    version_major: int
    version_minor: int
    original_image_size: int
    vbmeta_offset: int
    vbmeta_size: int

    def __post_init__(
        self,
    ) -> None:
        fields = (
            ("version_major", self.version_major),
            ("version_minor", self.version_minor),
            (
                "original_image_size",
                self.original_image_size,
            ),
            ("vbmeta_offset", self.vbmeta_offset),
            ("vbmeta_size", self.vbmeta_size),
        )

        for name, value in fields:
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} must not be negative"
                )


@dataclass(frozen=True, slots=True)
class AndroidParsedVbmeta:
    required_libavb_version_major: int
    required_libavb_version_minor: int

    authentication_data_block_size: int
    auxiliary_data_block_size: int

    algorithm_type: int

    hash_offset: int
    hash_size: int

    signature_offset: int
    signature_size: int

    public_key_offset: int
    public_key_size: int

    public_key_metadata_offset: int
    public_key_metadata_size: int

    hash: bytes
    signature: bytes
    public_key: bytes
    public_key_metadata: bytes

    descriptors_offset: int
    descriptors_size: int

    rollback_index: int
    flags: int
    rollback_index_location: int

    release_string: str

    descriptors: tuple[
        AndroidParsedAvbAnyDescriptor,
        ...,
    ]
