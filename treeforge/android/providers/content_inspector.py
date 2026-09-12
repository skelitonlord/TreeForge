from __future__ import annotations

from treeforge.android.providers.content_observation import (
    ProviderContentObservation,
    ProviderContentObservationConfidence,
    ProviderContentSignature,
)


class ProviderContentInspector:
    """
    Inspect a small artifact prefix for low-level structural evidence.

    This is a Discovery component.

    It performs no:

    - semantic Android classification;
    - persistent materialization;
    - sparse conversion;
    - filesystem extraction;
    - boot parsing;
    - decompression;
    - CPIO extraction;
    - ELF parsing.

    Observations describe only what artifact bytes directly support.
    """

    INSPECTION_SIZE = 8192

    _SIGNATURES: tuple[
        tuple[
            ProviderContentSignature,
            int,
            bytes,
        ],
        ...,
    ] = (
        (
            ProviderContentSignature
            .FBPK_CONTAINER,
            0,
            b"FBPK",
        ),
        (
            ProviderContentSignature
            .ANDROID_BOOT_FAMILY,
            0,
            b"ANDROID!",
        ),
        (
            ProviderContentSignature
            .ANDROID_VENDOR_BOOT_FAMILY,
            0,
            b"VNDRBOOT",
        ),
        (
            ProviderContentSignature
            .ANDROID_VERIFIED_BOOT,
            0,
            b"AVB0",
        ),
        (
            ProviderContentSignature
            .ANDROID_LP_METADATA,
            0,
            b"\x67\x44\x6c\x61",
        ),
        (
            ProviderContentSignature
            .ANDROID_LP_METADATA,
            4096,
            b"\x67\x44\x6c\x61",
        ),
        (
            ProviderContentSignature
            .ANDROID_DT_TABLE,
            0,
            b"\xd7\xb7\xab\x1e",
        ),
        (
            ProviderContentSignature
            .ANDROID_SPARSE,
            0,
            b"\x3a\xff\x26\xed",
        ),
        (
            ProviderContentSignature.ELF,
            0,
            b"\x7fELF",
        ),
        (
            ProviderContentSignature
            .DOS_EXECUTABLE,
            0,
            b"MZ",
        ),
        (
            ProviderContentSignature
            .DEVICE_TREE_BLOB,
            0,
            b"\xd0\x0d\xfe\xed",
        ),
        (
            ProviderContentSignature.GZIP,
            0,
            b"\x1f\x8b",
        ),
        (
            ProviderContentSignature.LZ4,
            0,
            b"\x04\x22\x4d\x18",
        ),
        (
            ProviderContentSignature
            .LZ4_LEGACY,
            0,
            b"\x02\x21\x4c\x18",
        ),
        (
            ProviderContentSignature.ZSTD,
            0,
            b"\x28\xb5\x2f\xfd",
        ),
        (
            ProviderContentSignature.XZ,
            0,
            b"\xfd7zXZ\x00",
        ),
        (
            ProviderContentSignature
            .LZMA_ALONE,
            0,
            b"\x5d\x00\x00\x80\x00",
        ),
        (
            ProviderContentSignature
            .CPIO_NEWC,
            0,
            b"070701",
        ),
        (
            ProviderContentSignature
            .CPIO_CRC,
            0,
            b"070702",
        ),
        (
            ProviderContentSignature
            .SHEBANG,
            0,
            b"#!",
        ),
        (
            ProviderContentSignature.EROFS,
            1024,
            b"\xe2\xe1\xf5\xe0",
        ),
        (
            ProviderContentSignature.EXT4,
            1024 + 56,
            b"\x53\xef",
        ),
    )

    _ZIP_SIGNATURES = (
        b"PK\x03\x04",
        b"PK\x05\x06",
        b"PK\x07\x08",
    )

    def inspect(
        self,
        data: bytes,
    ) -> tuple[
        ProviderContentObservation,
        ...,
    ]:
        """
        Inspect one artifact prefix and return canonical observations.
        """

        if not isinstance(
            data,
            bytes,
        ):
            raise TypeError(
                "data must be bytes"
            )

        observations: list[
            ProviderContentObservation
        ] = []

        self._observe_zip(
            data,
            observations,
        )

        for (
            signature,
            offset,
            magic,
        ) in self._SIGNATURES:
            if not self._matches(
                data,
                offset=offset,
                magic=magic,
            ):
                continue

            observations.append(
                ProviderContentObservation(
                    signature=signature,
                    confidence=(
                        ProviderContentObservationConfidence
                        .EXACT
                    ),
                    offset=offset,
                    matched_bytes=magic,
                )
            )

        if self._looks_like_text(
            data
        ):
            observations.append(
                ProviderContentObservation(
                    signature=(
                        ProviderContentSignature
                        .TEXT_LIKE
                    ),
                    confidence=(
                        ProviderContentObservationConfidence
                        .HEURISTIC
                    ),
                    offset=0,
                    matched_bytes=b"",
                )
            )

        return tuple(
            sorted(
                observations,
                key=lambda observation: (
                    observation.offset,
                    observation.signature.value,
                    observation.confidence.value,
                    observation.matched_bytes,
                ),
            )
        )

    @classmethod
    def _observe_zip(
        cls,
        data: bytes,
        observations: list[
            ProviderContentObservation
        ],
    ) -> None:
        for magic in cls._ZIP_SIGNATURES:
            if not data.startswith(
                magic
            ):
                continue

            observations.append(
                ProviderContentObservation(
                    signature=(
                        ProviderContentSignature.ZIP
                    ),
                    confidence=(
                        ProviderContentObservationConfidence
                        .EXACT
                    ),
                    offset=0,
                    matched_bytes=magic,
                )
            )

            return

    @staticmethod
    def _matches(
        data: bytes,
        *,
        offset: int,
        magic: bytes,
    ) -> bool:
        end = (
            offset
            + len(
                magic
            )
        )

        if end > len(
            data
        ):
            return False

        return (
            data[
                offset:end
            ]
            == magic
        )

    @staticmethod
    def _looks_like_text(
        data: bytes,
    ) -> bool:
        """
        Return whether the sampled bytes appear predominantly textual.

        This is deliberately heuristic and therefore never represented as an
        exact signature.
        """

        if not data:
            return False

        if b"\x00" in data:
            return False

        sample = data[
            :4096
        ]

        try:
            text = sample.decode(
                "utf-8",
            )
        except UnicodeDecodeError:
            return False

        if not text:
            return False

        printable = 0

        for character in text:
            if (
                character.isprintable()
                or character
                in "\r\n\t"
            ):
                printable += 1

        ratio = (
            printable
            / len(
                text
            )
        )

        return ratio >= 0.90