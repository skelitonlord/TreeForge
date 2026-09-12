from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class FirmwareEnvelopeStructure:
    """
    Literal physical structure of one verified boot-firmware envelope.

    Field semantics that have not yet been established remain deliberately
    unnamed. The structure records only values and relationships proven from
    the physical artifact.
    """

    identity_raw: bytes
    identity: str

    field_04: int
    field_08: int
    payload_size: int
    field_10: int

    header_offset: int
    payload_offset: int
    payload_sha256: str
    physical_size: int

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.identity_raw,
                bytes,
            )
            or len(self.identity_raw) != 4
        ):
            raise ValueError(
                "identity_raw must contain exactly four bytes"
            )

        if (
            not isinstance(
                self.identity,
                str,
            )
            or not self.identity
        ):
            raise ValueError(
                "identity must be a non-empty string"
            )

        for name in (
            "field_04",
            "field_08",
            "payload_size",
            "field_10",
            "header_offset",
            "payload_offset",
            "physical_size",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if (
            not isinstance(
                self.payload_sha256,
                str,
            )
            or len(self.payload_sha256) != 64
        ):
            raise ValueError(
                "payload_sha256 must be a SHA-256 hexadecimal digest"
            )

        if (
            self.payload_offset
            + self.payload_size
            != self.physical_size
        ):
            raise ValueError(
                "payload range must terminate exactly at physical EOF"
            )
