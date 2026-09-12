from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class UfpkDescriptor:
    """
    Literal physical descriptor-chain entry inside a UFPK container.

    Fields whose semantic purpose has not been independently established
    remain intentionally named by their physical offset.
    """

    index: int
    offset: int
    kind: int
    identity_raw: bytes
    identity: str
    field_28: int
    next_offset: int
    physical_end: int
    physical_size: int

    def __post_init__(
        self,
    ) -> None:
        for name in (
            "index",
            "offset",
            "kind",
            "field_28",
            "next_offset",
            "physical_end",
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
                self.identity_raw,
                bytes,
            )
            or not self.identity_raw
        ):
            raise ValueError(
                "identity_raw must be non-empty bytes"
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

        if self.physical_end < self.offset:
            raise ValueError(
                "physical_end cannot precede offset"
            )

        if (
            self.physical_end
            - self.offset
            != self.physical_size
        ):
            raise ValueError(
                "physical_size must equal physical_end - offset"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class UfpkStructure:
    """
    Literal physical structure of one validated UFPK descriptor chain.
    """

    physical_size: int
    aligned_physical_end: int
    descriptors: tuple[
        UfpkDescriptor,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.physical_size,
                bool,
            )
            or not isinstance(
                self.physical_size,
                int,
            )
            or self.physical_size <= 0
        ):
            raise ValueError(
                "physical_size must be a positive integer"
            )

        if (
            isinstance(
                self.aligned_physical_end,
                bool,
            )
            or not isinstance(
                self.aligned_physical_end,
                int,
            )
            or self.aligned_physical_end < self.physical_size
        ):
            raise ValueError(
                "aligned_physical_end is invalid"
            )

        if (
            not isinstance(
                self.descriptors,
                tuple,
            )
            or not self.descriptors
        ):
            raise ValueError(
                "descriptors must be a non-empty tuple"
            )
