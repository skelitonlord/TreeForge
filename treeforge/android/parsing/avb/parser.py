from __future__ import annotations

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbAnyDescriptor,
    AndroidParsedAvbFooter,
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
    AndroidParsedAvbKernelCmdlineDescriptor,
    AndroidParsedAvbPropertyDescriptor,
    AndroidParsedVbmeta,
)


class AndroidVbmetaParser:
    MAGIC = b"AVB0"
    HEADER_SIZE = 256

    FOOTER_MAGIC = b"AVBf"
    FOOTER_SIZE = 64

    TAG_PROPERTY = 0
    TAG_HASHTREE = 1
    TAG_HASH = 2
    TAG_KERNEL_CMDLINE = 3
    TAG_CHAIN_PARTITION = 4

    @staticmethod
    def _u32(data: bytes, offset: int) -> int:
        return int.from_bytes(
            data[offset : offset + 4],
            "big",
        )

    @staticmethod
    def _u64(data: bytes, offset: int) -> int:
        return int.from_bytes(
            data[offset : offset + 8],
            "big",
        )

    @staticmethod
    def _text(data: bytes) -> str:
        return data.decode(
            "utf-8",
            errors="replace",
        )

    def parse_footer(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedAvbFooter | None:
        """
        Parse an AVB footer from the exact canonical partition artifact.

        Images without an AVB footer return None. A present footer is
        validated against the containing image and the embedded AVB0 magic.
        """

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path
        image_size = source.stat().st_size

        if image_size < self.FOOTER_SIZE:
            return None

        with source.open("rb") as image:
            image.seek(
                -self.FOOTER_SIZE,
                2,
            )

            footer = image.read(
                self.FOOTER_SIZE
            )

        if len(footer) != self.FOOTER_SIZE:
            raise ValueError(
                f"Unable to read complete AVB footer: {source}"
            )

        if footer[:4] != self.FOOTER_MAGIC:
            return None

        version_major = self._u32(
            footer,
            4,
        )
        version_minor = self._u32(
            footer,
            8,
        )
        original_image_size = self._u64(
            footer,
            12,
        )
        vbmeta_offset = self._u64(
            footer,
            20,
        )
        vbmeta_size = self._u64(
            footer,
            28,
        )

        if vbmeta_size < self.HEADER_SIZE:
            raise ValueError(
                "AVB footer declares a VBMeta payload smaller "
                f"than the {self.HEADER_SIZE}-byte header: {source}"
            )

        if original_image_size > vbmeta_offset:
            raise ValueError(
                "AVB footer VBMeta offset precedes the original "
                f"image boundary: {source}"
            )

        vbmeta_end = (
            vbmeta_offset
            + vbmeta_size
        )

        footer_start = (
            image_size
            - self.FOOTER_SIZE
        )

        if vbmeta_end > footer_start:
            raise ValueError(
                "AVB footer VBMeta payload overlaps or exceeds "
                f"the footer boundary: {source}"
            )

        with source.open("rb") as image:
            image.seek(
                vbmeta_offset
            )

            magic = image.read(
                len(self.MAGIC)
            )

        if magic != self.MAGIC:
            raise ValueError(
                "AVB footer points to a payload without AVB0 "
                f"magic: {source}"
            )

        return AndroidParsedAvbFooter(
            version_major=version_major,
            version_minor=version_minor,
            original_image_size=(
                original_image_size
            ),
            vbmeta_offset=vbmeta_offset,
            vbmeta_size=vbmeta_size,
        )

    def parse(
        self,
        artifact: ExtractedArtifact,
        *,
        offset: int = 0,
        size: int | None = None,
    ) -> AndroidParsedVbmeta:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path
        image_size = source.stat().st_size

        if (
            not isinstance(offset, int)
            or isinstance(offset, bool)
        ):
            raise TypeError(
                "offset must be an int"
            )

        if offset < 0:
            raise ValueError(
                "offset must not be negative"
            )

        if offset > image_size:
            raise ValueError(
                f"VBMeta offset exceeds image bounds: {source}"
            )

        if size is None:
            read_size = (
                image_size
                - offset
            )

        else:
            if (
                not isinstance(size, int)
                or isinstance(size, bool)
            ):
                raise TypeError(
                    "size must be an int or None"
                )

            if size < 0:
                raise ValueError(
                    "size must not be negative"
                )

            read_size = size

        end = (
            offset
            + read_size
        )

        if end > image_size:
            raise ValueError(
                f"VBMeta region exceeds image bounds: {source}"
            )

        with source.open("rb") as image:
            image.seek(
                offset
            )

            data = image.read(
                read_size
            )

        if len(data) != read_size:
            raise ValueError(
                f"Unable to read complete VBMeta region: {source}"
            )

        if len(data) < self.HEADER_SIZE:
            raise ValueError(
                f"VBMeta image is smaller than "
                f"{self.HEADER_SIZE} bytes: {source}"
            )

        header = data[: self.HEADER_SIZE]

        if header[:4] != self.MAGIC:
            raise ValueError(
                f"Invalid VBMeta magic for {source}"
            )

        authentication_size = self._u64(
            header,
            12,
        )
        auxiliary_size = self._u64(
            header,
            20,
        )

        authentication_start = (
            self.HEADER_SIZE
        )
        authentication_end = (
            authentication_start
            + authentication_size
        )

        auxiliary_start = (
            authentication_end
        )
        auxiliary_end = (
            auxiliary_start
            + auxiliary_size
        )

        if auxiliary_end > len(data):
            raise ValueError(
                f"VBMeta auxiliary block exceeds "
                f"image bounds: {source}"
            )

        hash_offset = self._u64(
            header,
            32,
        )
        hash_size = self._u64(
            header,
            40,
        )

        signature_offset = self._u64(
            header,
            48,
        )
        signature_size = self._u64(
            header,
            56,
        )

        public_key_offset = self._u64(
            header,
            64,
        )
        public_key_size = self._u64(
            header,
            72,
        )

        public_key_metadata_offset = (
            self._u64(
                header,
                80,
            )
        )
        public_key_metadata_size = (
            self._u64(
                header,
                88,
            )
        )

        descriptors_offset = self._u64(
            header,
            96,
        )
        descriptors_size = self._u64(
            header,
            104,
        )

        hash_start = (
            authentication_start
            + hash_offset
        )
        hash_end = (
            hash_start
            + hash_size
        )

        signature_start = (
            authentication_start
            + signature_offset
        )
        signature_end = (
            signature_start
            + signature_size
        )

        public_key_start = (
            auxiliary_start
            + public_key_offset
        )
        public_key_end = (
            public_key_start
            + public_key_size
        )

        public_key_metadata_start = (
            auxiliary_start
            + public_key_metadata_offset
        )
        public_key_metadata_end = (
            public_key_metadata_start
            + public_key_metadata_size
        )

        if (
            hash_end > authentication_end
            or signature_end > authentication_end
        ):
            raise ValueError(
                "VBMeta authentication payload region exceeds "
                f"authentication block: {source}"
            )

        if (
            public_key_end > auxiliary_end
            or public_key_metadata_end > auxiliary_end
        ):
            raise ValueError(
                "VBMeta public-key payload region exceeds "
                f"auxiliary block: {source}"
            )

        descriptor_start = (
            auxiliary_start
            + descriptors_offset
        )
        descriptor_end = (
            descriptor_start
            + descriptors_size
        )

        if descriptor_end > auxiliary_end:
            raise ValueError(
                f"VBMeta descriptor region exceeds "
                f"auxiliary block: {source}"
            )

        descriptors = self._parse_descriptors(
            data[
                descriptor_start:
                descriptor_end
            ]
        )

        release_string = (
            header[128:176]
            .split(b"\0", 1)[0]
            .decode(
                "ascii",
                errors="replace",
            )
        )

        return AndroidParsedVbmeta(
            required_libavb_version_major=(
                self._u32(header, 4)
            ),
            required_libavb_version_minor=(
                self._u32(header, 8)
            ),
            authentication_data_block_size=(
                authentication_size
            ),
            auxiliary_data_block_size=(
                auxiliary_size
            ),
            algorithm_type=self._u32(
                header,
                28,
            ),
            hash_offset=hash_offset,
            hash_size=hash_size,
            signature_offset=signature_offset,
            signature_size=signature_size,
            public_key_offset=public_key_offset,
            public_key_size=public_key_size,
            public_key_metadata_offset=(
                public_key_metadata_offset
            ),
            public_key_metadata_size=(
                public_key_metadata_size
            ),
            hash=data[
                hash_start:
                hash_end
            ],
            signature=data[
                signature_start:
                signature_end
            ],
            public_key=data[
                public_key_start:
                public_key_end
            ],
            public_key_metadata=data[
                public_key_metadata_start:
                public_key_metadata_end
            ],
            descriptors_offset=(
                descriptors_offset
            ),
            descriptors_size=descriptors_size,
            rollback_index=self._u64(
                header,
                112,
            ),
            flags=self._u32(
                header,
                120,
            ),
            rollback_index_location=(
                self._u32(header, 124)
            ),
            release_string=release_string,
            descriptors=descriptors,
        )

    def _parse_descriptors(
        self,
        data: bytes,
    ) -> tuple[
        AndroidParsedAvbAnyDescriptor,
        ...,
    ]:
        descriptors: list[
            AndroidParsedAvbAnyDescriptor
        ] = []

        offset = 0

        while offset < len(data):
            if len(data) - offset < 16:
                raise ValueError(
                    "Truncated AVB descriptor header"
                )

            tag = self._u64(
                data,
                offset,
            )
            num_bytes_following = self._u64(
                data,
                offset + 8,
            )

            total_size = (
                16
                + num_bytes_following
            )

            end = offset + total_size

            if end > len(data):
                raise ValueError(
                    "AVB descriptor exceeds "
                    "descriptor region"
                )

            descriptor = data[offset:end]

            descriptors.append(
                self._parse_descriptor(
                    tag=tag,
                    num_bytes_following=(
                        num_bytes_following
                    ),
                    descriptor=descriptor,
                )
            )

            offset = end

        return tuple(descriptors)

    def _parse_descriptor(
        self,
        *,
        tag: int,
        num_bytes_following: int,
        descriptor: bytes,
    ) -> AndroidParsedAvbAnyDescriptor:
        if tag == self.TAG_PROPERTY:
            return self._parse_property(
                tag,
                num_bytes_following,
                descriptor,
            )

        if tag == self.TAG_HASHTREE:
            return self._parse_hashtree(
                tag,
                num_bytes_following,
                descriptor,
            )

        if tag == self.TAG_HASH:
            return self._parse_hash(
                tag,
                num_bytes_following,
                descriptor,
            )

        if tag == self.TAG_KERNEL_CMDLINE:
            return self._parse_kernel_cmdline(
                tag,
                num_bytes_following,
                descriptor,
            )

        if tag == self.TAG_CHAIN_PARTITION:
            return self._parse_chain_partition(
                tag,
                num_bytes_following,
                descriptor,
            )

        return AndroidParsedAvbDescriptor(
            tag=tag,
            num_bytes_following=(
                num_bytes_following
            ),
            raw_payload=descriptor[16:],
        )

    def _parse_property(
        self,
        tag: int,
        num_bytes_following: int,
        data: bytes,
    ) -> AndroidParsedAvbPropertyDescriptor:
        if len(data) < 32:
            raise ValueError(
                "Truncated AVB property descriptor"
            )

        key_len = self._u64(data, 16)
        value_len = self._u64(data, 24)

        cursor = 32
        key_end = cursor + key_len
        value_start = key_end + 1
        value_end = value_start + value_len

        if value_end > len(data):
            raise ValueError(
                "AVB property descriptor payload "
                "exceeds descriptor bounds"
            )

        return AndroidParsedAvbPropertyDescriptor(
            tag=tag,
            num_bytes_following=(
                num_bytes_following
            ),
            key=self._text(
                data[cursor:key_end]
            ),
            value=self._text(
                data[value_start:value_end]
            ),
        )

    def _parse_hashtree(
        self,
        tag: int,
        num_bytes_following: int,
        data: bytes,
    ) -> AndroidParsedAvbHashtreeDescriptor:
        #
        # AvbHashtreeDescriptor is a packed 180-byte structure:
        #
        #   AvbDescriptor parent_descriptor     16
        #   uint32_t dm_verity_version           4
        #   uint64_t image_size                  8
        #   uint64_t tree_offset                 8
        #   uint64_t tree_size                   8
        #   uint32_t data_block_size             4
        #   uint32_t hash_block_size             4
        #   uint32_t fec_num_roots               4
        #   uint64_t fec_offset                  8
        #   uint64_t fec_size                    8
        #   uint8_t hash_algorithm[32]          32
        #   uint32_t partition_name_len          4
        #   uint32_t salt_len                    4
        #   uint32_t root_digest_len             4
        #   uint32_t flags                       4
        #   uint8_t reserved[60]                60
        #
        # Variable data immediately following the structure is:
        #
        #   partition_name
        #   salt
        #   root_digest
        #
        fixed_size = 180

        if len(data) < fixed_size:
            raise ValueError(
                "Truncated AVB hashtree descriptor"
            )

        partition_name_len = self._u32(
            data,
            104,
        )
        salt_len = self._u32(
            data,
            108,
        )
        root_digest_len = self._u32(
            data,
            112,
        )
        flags = self._u32(
            data,
            116,
        )

        cursor = fixed_size
        partition_end = (
            cursor
            + partition_name_len
        )
        salt_end = partition_end + salt_len
        digest_end = (
            salt_end
            + root_digest_len
        )

        if digest_end > len(data):
            raise ValueError(
                "AVB hashtree variable payload "
                "exceeds descriptor bounds"
            )

        return AndroidParsedAvbHashtreeDescriptor(
            tag=tag,
            num_bytes_following=(
                num_bytes_following
            ),
            dm_verity_version=self._u32(
                data,
                16,
            ),
            image_size=self._u64(
                data,
                20,
            ),
            tree_offset=self._u64(
                data,
                28,
            ),
            tree_size=self._u64(
                data,
                36,
            ),
            data_block_size=self._u32(
                data,
                44,
            ),
            hash_block_size=self._u32(
                data,
                48,
            ),
            fec_num_roots=self._u32(
                data,
                52,
            ),
            fec_offset=self._u64(
                data,
                56,
            ),
            fec_size=self._u64(
                data,
                64,
            ),
            hash_algorithm=(
                data[72:104]
                .split(b"\0", 1)[0]
                .decode(
                    "ascii",
                    errors="replace",
                )
            ),
            partition_name=self._text(
                data[cursor:partition_end]
            ),
            salt=data[
                partition_end:salt_end
            ],
            root_digest=data[
                salt_end:digest_end
            ],
            flags=flags,
        )

    def _parse_hash(
        self,
        tag: int,
        num_bytes_following: int,
        data: bytes,
    ) -> AndroidParsedAvbHashDescriptor:
        fixed_size = 132

        if len(data) < fixed_size:
            raise ValueError(
                "Truncated AVB hash descriptor"
            )

        partition_name_len = self._u32(
            data,
            56,
        )
        salt_len = self._u32(
            data,
            60,
        )
        digest_len = self._u32(
            data,
            64,
        )
        flags = self._u32(
            data,
            68,
        )

        cursor = fixed_size
        partition_end = (
            cursor
            + partition_name_len
        )
        salt_end = partition_end + salt_len
        digest_end = salt_end + digest_len

        if digest_end > len(data):
            raise ValueError(
                "AVB hash variable payload exceeds "
                "descriptor bounds"
            )

        return AndroidParsedAvbHashDescriptor(
            tag=tag,
            num_bytes_following=(
                num_bytes_following
            ),
            image_size=self._u64(
                data,
                16,
            ),
            hash_algorithm=(
                data[24:56]
                .split(b"\0", 1)[0]
                .decode(
                    "ascii",
                    errors="replace",
                )
            ),
            partition_name=self._text(
                data[cursor:partition_end]
            ),
            salt=data[
                partition_end:salt_end
            ],
            digest=data[
                salt_end:digest_end
            ],
            flags=flags,
        )

    def _parse_kernel_cmdline(
        self,
        tag: int,
        num_bytes_following: int,
        data: bytes,
    ) -> AndroidParsedAvbKernelCmdlineDescriptor:
        if len(data) < 24:
            raise ValueError(
                "Truncated AVB kernel cmdline "
                "descriptor"
            )

        flags = self._u32(data, 16)
        cmdline_len = self._u32(
            data,
            20,
        )

        end = 24 + cmdline_len

        if end > len(data):
            raise ValueError(
                "AVB kernel cmdline payload exceeds "
                "descriptor bounds"
            )

        return (
            AndroidParsedAvbKernelCmdlineDescriptor(
                tag=tag,
                num_bytes_following=(
                    num_bytes_following
                ),
                flags=flags,
                kernel_cmdline=self._text(
                    data[24:end]
                ),
            )
        )

    def _parse_chain_partition(
        self,
        tag: int,
        num_bytes_following: int,
        data: bytes,
    ) -> AndroidParsedAvbChainPartitionDescriptor:
        fixed_size = 92

        if len(data) < fixed_size:
            raise ValueError(
                "Truncated AVB chain partition "
                "descriptor"
            )

        rollback_index_location = self._u32(
            data,
            16,
        )
        partition_name_len = self._u32(
            data,
            20,
        )
        public_key_len = self._u32(
            data,
            24,
        )
        flags = self._u32(
            data,
            28,
        )

        cursor = fixed_size
        partition_end = (
            cursor
            + partition_name_len
        )
        public_key_end = (
            partition_end
            + public_key_len
        )

        if public_key_end > len(data):
            raise ValueError(
                "AVB chain partition payload exceeds "
                "descriptor bounds"
            )

        return (
            AndroidParsedAvbChainPartitionDescriptor(
                tag=tag,
                num_bytes_following=(
                    num_bytes_following
                ),
                rollback_index_location=(
                    rollback_index_location
                ),
                partition_name=self._text(
                    data[cursor:partition_end]
                ),
                public_key=data[
                    partition_end:public_key_end
                ],
                flags=flags,
            )
        )
