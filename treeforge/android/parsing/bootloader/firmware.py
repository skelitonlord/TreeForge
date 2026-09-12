from __future__ import annotations

from collections import Counter
import math
import re
from struct import unpack_from

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
)
from treeforge.android.parsing.bootloader.model import (
    AndroidParsedBootFirmwarePayload,
)


class AndroidBootFirmwarePayloadParsingError(
    ValueError,
):
    pass


class AndroidBootFirmwarePayloadParser:
    """
    Parse literal observations from canonical terminal boot-firmware payloads.

    Eligibility is established by the canonical Extraction operation.
    Firmware identities, filenames, device names, platform names, and Android
    versions do not control parser selection.

    This parser intentionally avoids disassembly and semantic firmware-role
    interpretation. It records byte-level evidence only.
    """

    ARM64_RET = bytes.fromhex(
        "c0035fd6"
    )

    ARM64_NOP = bytes.fromhex(
        "1f2003d5"
    )

    PRINTABLE_ASCII = re.compile(
        rb"[\x20-\x7e]{8,}"
    )

    def supports(
        self,
        artifact: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        return (
            artifact.kind
            is ExtractionArtifactKind.FILE
            and artifact.operation
            is ExtractionOperation
            .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
            and artifact.path.is_file()
        )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedBootFirmwarePayload:
        if not self.supports(
            artifact
        ):
            raise AndroidBootFirmwarePayloadParsingError(
                "artifact is not a canonical boot firmware payload: "
                f"{artifact.path}"
            )

        identity = (
            artifact.semantic_name
        )

        if not identity:
            raise AndroidBootFirmwarePayloadParsingError(
                "canonical boot firmware payload lacks semantic identity: "
                f"{artifact.path}"
            )

        data = artifact.path.read_bytes()

        first_u32_le = (
            unpack_from(
                "<I",
                data,
                0,
            )[0]
            if len(data) >= 4
            else None
        )

        ret_count = (
            self._count_occurrences(
                data,
                self.ARM64_RET,
            )
        )

        nop_count = (
            self._count_occurrences(
                data,
                self.ARM64_NOP,
            )
        )

        printable_count = sum(
            1
            for _ in self.PRINTABLE_ASCII.finditer(
                data
            )
        )

        trailing_zero_bytes = (
            len(data)
            - len(
                data.rstrip(
                    b"\0"
                )
            )
        )

        entropy = (
            self._entropy(
                data
            )
        )

        return AndroidParsedBootFirmwarePayload(
            firmware_identity=identity,
            first_u32_le=first_u32_le,
            arm64_ret_count=ret_count,
            arm64_nop_count=nop_count,
            printable_ascii_string_count=(
                printable_count
            ),
            trailing_zero_bytes=(
                trailing_zero_bytes
            ),
            entropy_bits_per_byte=(
                entropy
            ),
        )

    @staticmethod
    def _count_occurrences(
        data: bytes,
        needle: bytes,
    ) -> int:
        count = 0
        start = 0

        while True:
            offset = data.find(
                needle,
                start,
            )

            if offset < 0:
                return count

            count += 1
            start = offset + 1

    @staticmethod
    def _entropy(
        data: bytes,
    ) -> float:
        if not data:
            return 0.0

        counts = Counter(
            data
        )

        total = len(
            data
        )

        return float(
            -sum(
                (
                    count
                    / total
                )
                * math.log2(
                    count
                    / total
                )
                for count
                in counts.values()
            )
        )
