from __future__ import annotations

from pathlib import Path

from treeforge.android.extraction.avb.metadata import (
    AvbFooterStructure,
    AvbHashtreePhysicalStructure,
    AvbVbmetaStructure,
)


class AvbFooterStructureError(
    RuntimeError,
):
    """
    Raised when a present AVB footer describes invalid physical structure.
    """


class AvbFooterStructureDecoder:
    """
    Decode only the physical AVB footer/container layout.

    Extraction owns recognition of the trailing AVB footer and the exact
    embedded VBMeta byte region referenced by it.

    This decoder deliberately does NOT decode the VBMeta header, descriptors,
    keys, hashes, algorithms, rollback indexes, properties, or trust graph.
    Those remain Parsing/downstream responsibilities.
    """

    FOOTER_MAGIC = b"AVBf"
    FOOTER_SIZE = 64

    VBMETA_MAGIC = b"AVB0"
    VBMETA_HEADER_SIZE = 256

    @staticmethod
    def _u32(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset : offset + 4
            ],
            "big",
        )

    @staticmethod
    def _u64(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset : offset + 8
            ],
            "big",
        )

    def has_footer(
        self,
        source: Path,
    ) -> bool:
        """
        Cheap structural probe for a trailing AVB footer.
        """

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if (
            not source.exists()
            or not source.is_file()
        ):
            return False

        image_size = (
            source.stat().st_size
        )

        if image_size < self.FOOTER_SIZE:
            return False

        with source.open(
            "rb"
        ) as image:
            image.seek(
                -self.FOOTER_SIZE,
                2,
            )

            return (
                image.read(
                    len(
                        self.FOOTER_MAGIC
                    )
                )
                == self.FOOTER_MAGIC
            )

    def decode(
        self,
        source: Path,
    ) -> AvbFooterStructure | None:
        """
        Decode one authoritative trailing AVB footer.

        Images without AVBf at the final 64 bytes return None. Once AVBf is
        present, malformed structure is an error rather than silently ignored.
        """

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if not source.is_file():
            raise AvbFooterStructureError(
                "AVB source must be a regular file: "
                f"{source}"
            )

        image_size = (
            source.stat().st_size
        )

        if image_size < self.FOOTER_SIZE:
            return None

        footer_offset = (
            image_size
            - self.FOOTER_SIZE
        )

        with source.open(
            "rb"
        ) as image:
            image.seek(
                footer_offset
            )

            footer = image.read(
                self.FOOTER_SIZE
            )

        if len(footer) != self.FOOTER_SIZE:
            raise AvbFooterStructureError(
                "Unable to read complete AVB footer: "
                f"{source}"
            )

        if (
            footer[:4]
            != self.FOOTER_MAGIC
        ):
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

        if (
            vbmeta_size
            < self.VBMETA_HEADER_SIZE
        ):
            raise AvbFooterStructureError(
                "AVB footer declares a VBMeta region smaller than "
                f"{self.VBMETA_HEADER_SIZE} bytes: {source}"
            )

        if (
            original_image_size
            > vbmeta_offset
        ):
            raise AvbFooterStructureError(
                "AVB footer VBMeta offset precedes original image "
                f"boundary: {source}"
            )

        vbmeta_end = (
            vbmeta_offset
            + vbmeta_size
        )

        if (
            vbmeta_end
            > footer_offset
        ):
            raise AvbFooterStructureError(
                "AVB footer VBMeta region overlaps or exceeds "
                f"the footer boundary: {source}"
            )

        with source.open(
            "rb"
        ) as image:
            image.seek(
                vbmeta_offset
            )

            magic = image.read(
                len(
                    self.VBMETA_MAGIC
                )
            )

        if magic != self.VBMETA_MAGIC:
            raise AvbFooterStructureError(
                "AVB footer points to a region without AVB0 "
                f"magic: {source}"
            )

        return AvbFooterStructure(
            image_size=image_size,
            footer_offset=footer_offset,
            footer_size=self.FOOTER_SIZE,
            version_major=version_major,
            version_minor=version_minor,
            original_image_size=(
                original_image_size
            ),
            vbmeta_offset=vbmeta_offset,
            vbmeta_size=vbmeta_size,
        )



    def decode_hashtree_physical_structures(
        self,
        source: Path,
        structure: AvbFooterStructure,
    ) -> tuple[
        AvbHashtreePhysicalStructure,
        ...,
    ]:
        """
        Decode only physical ranges from tag-1 AVB descriptors.

        Descriptor payload semantics remain downstream-owned.
        """

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not isinstance(
            structure,
            AvbFooterStructure,
        ):
            raise TypeError(
                "structure must be an AvbFooterStructure"
            )

        with source.open(
            "rb"
        ) as image:
            image.seek(
                structure.vbmeta_offset
            )

            vbmeta = image.read(
                structure.vbmeta_size
            )

        if (
            len(vbmeta)
            != structure.vbmeta_size
        ):
            raise AvbFooterStructureError(
                "Unable to read complete embedded VBMeta"
            )

        if vbmeta[:4] != self.VBMETA_MAGIC:
            raise AvbFooterStructureError(
                "Embedded VBMeta lacks AVB0 magic"
            )

        authentication_size = self._u64(
            vbmeta,
            12,
        )

        auxiliary_size = self._u64(
            vbmeta,
            20,
        )

        descriptors_offset = self._u64(
            vbmeta,
            96,
        )

        descriptors_size = self._u64(
            vbmeta,
            104,
        )

        auxiliary_start = (
            self.VBMETA_HEADER_SIZE
            + authentication_size
        )

        auxiliary_end = (
            auxiliary_start
            + auxiliary_size
        )

        if auxiliary_end > len(vbmeta):
            raise AvbFooterStructureError(
                "Embedded VBMeta auxiliary block exceeds "
                "declared VBMeta region"
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
            raise AvbFooterStructureError(
                "Embedded VBMeta descriptor region exceeds "
                "auxiliary block"
            )

        layouts: list[
            AvbHashtreePhysicalStructure
        ] = []

        cursor = descriptor_start
        descriptor_index = 0

        while cursor < descriptor_end:
            if cursor + 16 > descriptor_end:
                raise AvbFooterStructureError(
                    "Truncated AVB descriptor envelope"
                )

            tag = self._u64(
                vbmeta,
                cursor,
            )

            bytes_following = self._u64(
                vbmeta,
                cursor + 8,
            )

            next_cursor = (
                cursor
                + 16
                + bytes_following
            )

            if next_cursor > descriptor_end:
                raise AvbFooterStructureError(
                    "AVB descriptor exceeds descriptor region"
                )

            #
            # Tag 1 is AvbHashtreeDescriptor.
            #
            # Extraction reads only the fixed physical-layout
            # prefix needed to identify image/tree/FEC ranges.
            #
            if tag == 1:
                if bytes_following < 56:
                    raise AvbFooterStructureError(
                        "AVB hashtree descriptor is too small "
                        "for physical layout fields"
                    )

                base = cursor + 16

                layout = (
                    AvbHashtreePhysicalStructure(
                        descriptor_index=(
                            descriptor_index
                        ),
                        image_size=self._u64(
                            vbmeta,
                            base + 4,
                        ),
                        tree_offset=self._u64(
                            vbmeta,
                            base + 12,
                        ),
                        tree_size=self._u64(
                            vbmeta,
                            base + 20,
                        ),
                        data_block_size=self._u32(
                            vbmeta,
                            base + 28,
                        ),
                        hash_block_size=self._u32(
                            vbmeta,
                            base + 32,
                        ),
                        fec_num_roots=self._u32(
                            vbmeta,
                            base + 36,
                        ),
                        fec_offset=self._u64(
                            vbmeta,
                            base + 40,
                        ),
                        fec_size=self._u64(
                            vbmeta,
                            base + 48,
                        ),
                    )
                )

                if layout.image_size > layout.tree_offset:
                    raise AvbFooterStructureError(
                        "AVB hashtree starts before declared "
                        "original image extent"
                    )

                if (
                    layout.tree_end
                    > structure.vbmeta_offset
                ):
                    raise AvbFooterStructureError(
                        "AVB hashtree overlaps embedded VBMeta"
                    )

                if layout.fec_size:
                    if (
                        layout.fec_offset
                        < layout.tree_end
                    ):
                        raise AvbFooterStructureError(
                            "AVB FEC overlaps hashtree"
                        )

                    if (
                        layout.fec_end
                        > structure.vbmeta_offset
                    ):
                        raise AvbFooterStructureError(
                            "AVB FEC overlaps embedded VBMeta"
                        )

                layouts.append(
                    layout
                )

            cursor = next_cursor
            descriptor_index += 1

        if cursor != descriptor_end:
            raise AvbFooterStructureError(
                "AVB descriptor traversal ended "
                "at unexpected boundary"
            )

        return tuple(
            layouts
        )



class AvbVbmetaStructureDecoder:
    """
    Decode literal physical structure of a standalone AVB0 image.

    Descriptor contents, key semantics, signing/trust, and verified-boot
    policy remain downstream responsibilities.
    """

    MAGIC = b"AVB0"
    HEADER_SIZE = 256

    @staticmethod
    def _u32(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 4
            ],
            "big",
        )

    @staticmethod
    def _u64(
        data: bytes,
        offset: int,
    ) -> int:
        return int.from_bytes(
            data[
                offset:
                offset + 8
            ],
            "big",
        )

    @staticmethod
    def _cstring(
        data: bytes,
    ) -> str:
        return (
            data.split(
                b"\0",
                1,
            )[0]
            .decode(
                "utf-8",
                errors="replace",
            )
        )

    def supports(
        self,
        source: Path,
    ) -> bool:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if (
            not source.exists()
            or not source.is_file()
        ):
            return False

        if (
            source.stat().st_size
            < self.HEADER_SIZE
        ):
            return False

        with source.open(
            "rb"
        ) as image:
            return (
                image.read(4)
                == self.MAGIC
            )

    def decode(
        self,
        source: Path,
    ) -> AvbVbmetaStructure:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if not source.is_file():
            raise AvbFooterStructureError(
                "standalone AVB0 source must be "
                f"a regular file: {source}"
            )

        image_size = (
            source.stat().st_size
        )

        if image_size < self.HEADER_SIZE:
            raise AvbFooterStructureError(
                "standalone AVB0 image is smaller "
                "than its fixed header"
            )

        with source.open(
            "rb"
        ) as image:
            header = image.read(
                self.HEADER_SIZE
            )

        if header[:4] != self.MAGIC:
            raise AvbFooterStructureError(
                "standalone AVB0 magic is missing"
            )

        structure = AvbVbmetaStructure(
            image_size=image_size,
            header_size=self.HEADER_SIZE,
            required_version_major=self._u32(
                header,
                4,
            ),
            required_version_minor=self._u32(
                header,
                8,
            ),
            authentication_block_size=self._u64(
                header,
                12,
            ),
            auxiliary_block_size=self._u64(
                header,
                20,
            ),
            algorithm_type=self._u32(
                header,
                28,
            ),
            hash_offset=self._u64(
                header,
                32,
            ),
            hash_size=self._u64(
                header,
                40,
            ),
            signature_offset=self._u64(
                header,
                48,
            ),
            signature_size=self._u64(
                header,
                56,
            ),
            public_key_offset=self._u64(
                header,
                64,
            ),
            public_key_size=self._u64(
                header,
                72,
            ),
            public_key_metadata_offset=self._u64(
                header,
                80,
            ),
            public_key_metadata_size=self._u64(
                header,
                88,
            ),
            descriptors_offset=self._u64(
                header,
                96,
            ),
            descriptors_size=self._u64(
                header,
                104,
            ),
            rollback_index=self._u64(
                header,
                112,
            ),
            flags=self._u32(
                header,
                120,
            ),
            rollback_index_location=self._u32(
                header,
                124,
            ),
            release_string=self._cstring(
                header[
                    128:176
                ]
            ),
        )

        return structure
