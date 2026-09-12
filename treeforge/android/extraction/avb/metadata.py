from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AvbFooterStructure:
    """
    Literal physical layout established by an AVB footer.

    This model owns only byte-container structure. It intentionally contains
    no VBMeta descriptor, authentication, key, rollback, or trust semantics.
    """

    image_size: int

    footer_offset: int
    footer_size: int

    version_major: int
    version_minor: int

    original_image_size: int

    vbmeta_offset: int
    vbmeta_size: int

    def __post_init__(
        self,
    ) -> None:
        fields = (
            ("image_size", self.image_size),
            ("footer_offset", self.footer_offset),
            ("footer_size", self.footer_size),
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

        if self.footer_size <= 0:
            raise ValueError(
                "footer_size must be greater than zero"
            )

        if self.vbmeta_size <= 0:
            raise ValueError(
                "vbmeta_size must be greater than zero"
            )

        if (
            self.footer_offset
            + self.footer_size
            != self.image_size
        ):
            raise ValueError(
                "AVB footer must terminate at the containing image boundary"
            )

        if (
            self.original_image_size
            > self.vbmeta_offset
        ):
            raise ValueError(
                "AVB VBMeta offset precedes original image boundary"
            )

        if (
            self.vbmeta_offset
            + self.vbmeta_size
            > self.footer_offset
        ):
            raise ValueError(
                "AVB VBMeta region overlaps the AVB footer"
            )

    @property
    def vbmeta_end(
        self,
    ) -> int:
        return (
            self.vbmeta_offset
            + self.vbmeta_size
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AvbVbmetaStructure:
    """
    Literal physical layout of one standalone AVB0 VBMeta image.

    This model preserves only serialized container/header structure.
    Descriptor, key, signing, rollback-policy, and trust semantics remain
    downstream responsibilities.
    """

    image_size: int

    header_size: int

    required_version_major: int
    required_version_minor: int

    authentication_block_size: int
    auxiliary_block_size: int

    algorithm_type: int

    hash_offset: int
    hash_size: int

    signature_offset: int
    signature_size: int

    public_key_offset: int
    public_key_size: int

    public_key_metadata_offset: int
    public_key_metadata_size: int

    descriptors_offset: int
    descriptors_size: int

    rollback_index: int
    flags: int
    rollback_index_location: int

    release_string: str

    def __post_init__(
        self,
    ) -> None:
        integer_fields = (
            ("image_size", self.image_size),
            ("header_size", self.header_size),
            (
                "required_version_major",
                self.required_version_major,
            ),
            (
                "required_version_minor",
                self.required_version_minor,
            ),
            (
                "authentication_block_size",
                self.authentication_block_size,
            ),
            (
                "auxiliary_block_size",
                self.auxiliary_block_size,
            ),
            ("algorithm_type", self.algorithm_type),
            ("hash_offset", self.hash_offset),
            ("hash_size", self.hash_size),
            ("signature_offset", self.signature_offset),
            ("signature_size", self.signature_size),
            (
                "public_key_offset",
                self.public_key_offset,
            ),
            (
                "public_key_size",
                self.public_key_size,
            ),
            (
                "public_key_metadata_offset",
                self.public_key_metadata_offset,
            ),
            (
                "public_key_metadata_size",
                self.public_key_metadata_size,
            ),
            (
                "descriptors_offset",
                self.descriptors_offset,
            ),
            (
                "descriptors_size",
                self.descriptors_size,
            ),
            ("rollback_index", self.rollback_index),
            ("flags", self.flags),
            (
                "rollback_index_location",
                self.rollback_index_location,
            ),
        )

        for name, value in integer_fields:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if self.image_size <= 0:
            raise ValueError(
                "image_size must be greater than zero"
            )

        if self.header_size != 256:
            raise ValueError(
                "standalone AVB0 header_size must be 256"
            )

        if not isinstance(
            self.release_string,
            str,
        ):
            raise TypeError(
                "release_string must be a string"
            )

        if self.vbmeta_size > self.image_size:
            raise ValueError(
                "declared standalone VBMeta structure "
                "extends beyond image"
            )

        if (
            self.hash_offset
            + self.hash_size
            > self.authentication_block_size
        ):
            raise ValueError(
                "AVB hash range extends beyond "
                "authentication block"
            )

        if (
            self.signature_offset
            + self.signature_size
            > self.authentication_block_size
        ):
            raise ValueError(
                "AVB signature range extends beyond "
                "authentication block"
            )

        for (
            name,
            offset,
            size,
        ) in (
            (
                "public_key",
                self.public_key_offset,
                self.public_key_size,
            ),
            (
                "public_key_metadata",
                self.public_key_metadata_offset,
                self.public_key_metadata_size,
            ),
            (
                "descriptors",
                self.descriptors_offset,
                self.descriptors_size,
            ),
        ):
            if (
                offset + size
                > self.auxiliary_block_size
            ):
                raise ValueError(
                    f"AVB {name} range extends beyond "
                    "auxiliary block"
                )

    @property
    def authentication_block_offset(
        self,
    ) -> int:
        return self.header_size

    @property
    def authentication_block_end(
        self,
    ) -> int:
        return (
            self.authentication_block_offset
            + self.authentication_block_size
        )

    @property
    def auxiliary_block_offset(
        self,
    ) -> int:
        return self.authentication_block_end

    @property
    def auxiliary_block_end(
        self,
    ) -> int:
        return (
            self.auxiliary_block_offset
            + self.auxiliary_block_size
        )

    @property
    def vbmeta_size(
        self,
    ) -> int:
        return self.auxiliary_block_end



@dataclass(
    frozen=True,
    slots=True,
)
class AvbHashtreePhysicalStructure:
    """
    Literal physical data ranges declared by one AVB hashtree descriptor.

    Extraction preserves only byte layout. Hash algorithm, digest, salt,
    partition identity, verification policy, and trust semantics remain
    downstream responsibilities.
    """

    descriptor_index: int

    image_size: int

    tree_offset: int
    tree_size: int

    data_block_size: int
    hash_block_size: int

    fec_num_roots: int
    fec_offset: int
    fec_size: int

    def __post_init__(
        self,
    ) -> None:
        fields = (
            (
                "descriptor_index",
                self.descriptor_index,
            ),
            ("image_size", self.image_size),
            ("tree_offset", self.tree_offset),
            ("tree_size", self.tree_size),
            (
                "data_block_size",
                self.data_block_size,
            ),
            (
                "hash_block_size",
                self.hash_block_size,
            ),
            (
                "fec_num_roots",
                self.fec_num_roots,
            ),
            ("fec_offset", self.fec_offset),
            ("fec_size", self.fec_size),
        )

        for name, value in fields:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if self.tree_size <= 0:
            raise ValueError(
                "tree_size must be greater than zero"
            )

        if self.data_block_size <= 0:
            raise ValueError(
                "data_block_size must be greater than zero"
            )

        if self.hash_block_size <= 0:
            raise ValueError(
                "hash_block_size must be greater than zero"
            )

    @property
    def tree_end(
        self,
    ) -> int:
        return (
            self.tree_offset
            + self.tree_size
        )

    @property
    def fec_end(
        self,
    ) -> int:
        return (
            self.fec_offset
            + self.fec_size
        )
