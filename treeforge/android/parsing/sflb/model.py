from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction.model import (
    ExtractedArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedSflbEntry:
    """
    Literal structural observations for one canonical SFLB entry artifact.

    Extraction owns discovery of the embedded SFLB container, structural
    boundary validation, payload materialization, decompression decisions,
    hashing, and lineage.

    Parsing records the established literal entry/container observations while
    retaining the exact canonical Extraction artifact that supplied the
    materialized payload. Device- or boot-policy interpretation belongs to
    Android Device Universe.
    """

    artifact: ExtractedArtifact

    entry_name: str

    container_index: int
    container_offset_bytes: int
    container_span_bytes: int

    version: int
    entry_count: int
    secondary_count: int

    entry_index: int
    record_offset_bytes: int

    payload_offset_bytes: int
    absolute_payload_offset_bytes: int
    payload_size_bytes: int

    opaque_word: int
    flags: int

    raw_header_tail: tuple[
        int,
        int,
        int,
    ]

    raw_payload: bytes

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            not isinstance(
                self.entry_name,
                str,
            )
            or not self.entry_name
        ):
            raise ValueError(
                "entry_name must be a non-empty string"
            )

        for name in (
            "container_index",
            "container_offset_bytes",
            "container_span_bytes",
            "version",
            "entry_count",
            "secondary_count",
            "entry_index",
            "record_offset_bytes",
            "payload_offset_bytes",
            "absolute_payload_offset_bytes",
            "payload_size_bytes",
            "opaque_word",
            "flags",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if self.container_span_bytes <= 0:
            raise ValueError(
                "container_span_bytes must be greater than zero"
            )

        if self.entry_count <= 0:
            raise ValueError(
                "entry_count must be greater than zero"
            )

        if self.payload_size_bytes <= 0:
            raise ValueError(
                "payload_size_bytes must be greater than zero"
            )

        if (
            not isinstance(
                self.raw_header_tail,
                tuple,
            )
            or len(
                self.raw_header_tail
            ) != 3
        ):
            raise ValueError(
                "raw_header_tail must contain exactly three integers"
            )

        if not all(
            isinstance(
                value,
                int,
            )
            and not isinstance(
                value,
                bool,
            )
            and value >= 0
            for value in self.raw_header_tail
        ):
            raise ValueError(
                "raw_header_tail must contain non-negative integers"
            )

        if not isinstance(
            self.raw_payload,
            bytes,
        ):
            raise TypeError(
                "raw_payload must be bytes"
            )

        if len(
            self.raw_payload
        ) != self.payload_size_bytes:
            raise ValueError(
                "raw_payload size must match payload_size_bytes"
            )
