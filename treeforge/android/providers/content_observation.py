from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProviderContentSignature(
    StrEnum,
):
    """
    Low-level content signatures observable during provider discovery.

    These values describe byte-level structure only.

    They do not assign Android partition identity or higher-level semantic
    meaning.
    """

    ZIP = "zip"

    FBPK_CONTAINER = (
        "fbpk_container"
    )
    ANDROID_BOOT_FAMILY = (
        "android_boot_family"
    )
    ANDROID_VENDOR_BOOT_FAMILY = (
        "android_vendor_boot_family"
    )
    ANDROID_SPARSE = (
        "android_sparse"
    )
    ANDROID_VERIFIED_BOOT = (
        "android_verified_boot"
    )
    ANDROID_DT_TABLE = (
        "android_dt_table"
    )
    ANDROID_LP_METADATA = (
        "android_lp_metadata"
    )

    EXT4 = "ext4"
    EROFS = "erofs"

    ELF = "elf"
    DOS_EXECUTABLE = (
        "dos_executable"
    )

    DEVICE_TREE_BLOB = (
        "device_tree_blob"
    )

    GZIP = "gzip"
    LZ4 = "lz4"
    LZ4_LEGACY = (
        "lz4_legacy"
    )
    ZSTD = "zstd"
    XZ = "xz"
    LZMA_ALONE = (
        "lzma_alone"
    )

    CPIO_NEWC = (
        "cpio_newc"
    )
    CPIO_CRC = (
        "cpio_crc"
    )

    SHEBANG = "shebang"

    TEXT_LIKE = (
        "text_like"
    )


class ProviderContentObservationConfidence(
    StrEnum,
):
    """
    Strength of one content observation.

    EXACT means fixed bytes matched a known structural signature.

    HEURISTIC means the observation was inferred from content characteristics
    that are useful but not unique enough to be treated as a file-format
    signature.
    """

    EXACT = "exact"

    HEURISTIC = "heuristic"


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderContentObservation:
    """
    Immutable byte-level evidence collected during provider discovery.

    ``offset`` identifies where the evidence was observed in the artifact.

    ``matched_bytes`` preserves the exact bytes responsible for an exact
    signature match.

    Heuristic observations may use an empty matched_bytes value because their
    evidence is derived from a broader sample rather than one unique magic
    value.
    """

    signature: ProviderContentSignature

    confidence: (
        ProviderContentObservationConfidence
    )

    offset: int

    matched_bytes: bytes = b""

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.signature,
            ProviderContentSignature,
        ):
            raise TypeError(
                "signature must be a "
                "ProviderContentSignature"
            )

        if not isinstance(
            self.confidence,
            ProviderContentObservationConfidence,
        ):
            raise TypeError(
                "confidence must be a "
                "ProviderContentObservationConfidence"
            )

        if (
            not isinstance(
                self.offset,
                int,
            )
            or isinstance(
                self.offset,
                bool,
            )
        ):
            raise TypeError(
                "offset must be an integer"
            )

        if self.offset < 0:
            raise ValueError(
                "offset must not be negative"
            )

        if not isinstance(
            self.matched_bytes,
            bytes,
        ):
            raise TypeError(
                "matched_bytes must be bytes"
            )

        if (
            self.confidence
            is ProviderContentObservationConfidence.EXACT
            and not self.matched_bytes
        ):
            raise ValueError(
                "exact observations must preserve "
                "matched bytes"
            )

    @property
    def is_exact(
        self,
    ) -> bool:
        return (
            self.confidence
            is ProviderContentObservationConfidence.EXACT
        )

    @property
    def is_heuristic(
        self,
    ) -> bool:
        return (
            self.confidence
            is ProviderContentObservationConfidence.HEURISTIC
        )