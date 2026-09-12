from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from struct import unpack_from

from treeforge.android.extraction.firmware_envelope.model import (
    FirmwareEnvelopeStructure,
)


class FirmwareEnvelopeDecodeError(
    ValueError,
):
    pass


class FirmwareEnvelopeDecoder:
    """
    Recognize and decode the structurally verified firmware envelope.

    Recognition is independent of filename, device, platform, Android version,
    or firmware identity. The current physical contract is:

      - 4-byte printable identity at 0x400
      - literal field 0x04 == 1
      - literal field 0x08 == 2
      - payload size at 0x40c
      - preserved literal field at 0x410
      - payload SHA-256 at 0x420..0x43f
      - zero alignment region 0x800..0xfff
      - payload starts at 0x1000
      - payload terminates exactly at physical EOF
      - declared digest equals payload SHA-256

    Unknown field meanings remain intentionally uninterpreted.
    """

    HEADER_OFFSET = 0x400
    PAYLOAD_OFFSET = 0x1000
    DIGEST_OFFSET = 0x420
    DIGEST_SIZE = 32

    def supports(
        self,
        path: Path,
    ) -> bool:
        try:
            self.decode(
                path
            )
        except (
            FirmwareEnvelopeDecodeError,
            FileNotFoundError,
            OSError,
        ):
            return False

        return True

    def decode(
        self,
        path: Path,
    ) -> FirmwareEnvelopeStructure:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            raise FirmwareEnvelopeDecodeError(
                f"firmware envelope is not a file: {path}"
            )

        data = path.read_bytes()

        if len(data) <= self.PAYLOAD_OFFSET:
            raise FirmwareEnvelopeDecodeError(
                f"artifact is too small for firmware envelope: {path}"
            )

        identity_raw = data[
            self.HEADER_OFFSET:
            self.HEADER_OFFSET + 4
        ]

        normalized_identity = (
            identity_raw.rstrip(
                b"\0"
            )
        )

        if not normalized_identity:
            raise FirmwareEnvelopeDecodeError(
                f"firmware identity is empty: {path}"
            )

        if not all(
            0x20 <= byte < 0x7f
            for byte in normalized_identity
        ):
            raise FirmwareEnvelopeDecodeError(
                f"firmware identity is not printable ASCII: {path}"
            )

        try:
            identity = (
                normalized_identity.decode(
                    "ascii"
                )
            )
        except UnicodeDecodeError as error:
            raise FirmwareEnvelopeDecodeError(
                f"firmware identity is not ASCII: {path}"
            ) from error

        (
            field_04,
            field_08,
            payload_size,
            field_10,
        ) = unpack_from(
            "<IIII",
            data,
            self.HEADER_OFFSET + 4,
        )

        #
        # These are observed format-contract constants, not device or
        # firmware-name policy.
        #
        if field_04 != 1:
            raise FirmwareEnvelopeDecodeError(
                "unsupported firmware-envelope field_04 "
                f"value {field_04}: {path}"
            )

        if field_08 != 2:
            raise FirmwareEnvelopeDecodeError(
                "unsupported firmware-envelope field_08 "
                f"value {field_08}: {path}"
            )

        if payload_size <= 0:
            raise FirmwareEnvelopeDecodeError(
                f"firmware payload is empty: {path}"
            )

        payload_end = (
            self.PAYLOAD_OFFSET
            + payload_size
        )

        if payload_end != len(data):
            raise FirmwareEnvelopeDecodeError(
                "firmware payload does not terminate at physical EOF: "
                f"payload_end={payload_end}, file_size={len(data)}, "
                f"path={path}"
            )

        if any(
            data[
                0x800:
                self.PAYLOAD_OFFSET
            ]
        ):
            raise FirmwareEnvelopeDecodeError(
                "firmware-envelope alignment region is not zero-filled: "
                f"{path}"
            )

        declared_digest = data[
            self.DIGEST_OFFSET:
            self.DIGEST_OFFSET
            + self.DIGEST_SIZE
        ]

        if len(
            declared_digest
        ) != self.DIGEST_SIZE:
            raise FirmwareEnvelopeDecodeError(
                f"firmware payload digest is truncated: {path}"
            )

        payload = data[
            self.PAYLOAD_OFFSET:
            payload_end
        ]

        computed_digest = (
            sha256(
                payload
            ).digest()
        )

        if (
            declared_digest
            != computed_digest
        ):
            raise FirmwareEnvelopeDecodeError(
                f"firmware payload SHA-256 mismatch: {path}"
            )

        return FirmwareEnvelopeStructure(
            identity_raw=identity_raw,
            identity=identity,
            field_04=field_04,
            field_08=field_08,
            payload_size=payload_size,
            field_10=field_10,
            header_offset=self.HEADER_OFFSET,
            payload_offset=self.PAYLOAD_OFFSET,
            payload_sha256=(
                computed_digest.hex()
            ),
            physical_size=len(data),
        )
