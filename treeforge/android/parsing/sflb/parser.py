from __future__ import annotations

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.parsing.sflb.model import (
    AndroidParsedSflbEntry,
)


class AndroidSflbEntryParsingError(
    ValueError,
):
    pass


class AndroidSflbEntryParser:
    """
    Canonicalize literal SFLB-entry observations from one Extraction artifact.

    This parser deliberately does not rediscover SFLB containers. Extraction
    already established the exact container/record/payload boundary and
    retained that structural evidence on the canonical artifact.

    Parsing validates that evidence against the materialized payload and
    exposes it as immutable semantic input for later stages.
    """

    _REQUIRED_FACTS = (
        "sflb_container_index",
        "sflb_container_offset_bytes",
        "sflb_container_span_bytes",
        "sflb_version",
        "sflb_entry_count",
        "sflb_secondary_count",
        "entry_index",
        "record_offset_bytes",
        "payload_offset_bytes",
        "absolute_payload_offset_bytes",
        "payload_size_bytes",
        "opaque_word",
        "flags",
        "raw_header_tail_u32_0",
        "raw_header_tail_u32_1",
        "raw_header_tail_u32_2",
    )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedSflbEntry:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            artifact.operation
            is not ExtractionOperation
            .SFLB_ENTRY_EXTRACTION
        ):
            raise AndroidSflbEntryParsingError(
                "SFLB Parsing requires an "
                "SFLB_ENTRY_EXTRACTION artifact"
            )

        if artifact.parent is None:
            raise AndroidSflbEntryParsingError(
                "SFLB entry artifact must retain its "
                "canonical container parent"
            )

        if (
            not isinstance(
                artifact.semantic_name,
                str,
            )
            or not artifact.semantic_name
        ):
            raise AndroidSflbEntryParsingError(
                "SFLB entry artifact must carry a semantic name"
            )

        facts = {
            fact.name: fact.value
            for fact in artifact.facts
        }

        missing = tuple(
            name
            for name in self._REQUIRED_FACTS
            if name not in facts
        )

        if missing:
            raise AndroidSflbEntryParsingError(
                "SFLB entry is missing canonical structural facts: "
                + ", ".join(
                    missing
                )
            )

        for name in self._REQUIRED_FACTS:
            value = facts[
                name
            ]

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
                raise AndroidSflbEntryParsingError(
                    f"SFLB structural fact {name!r} "
                    "must be a non-negative integer"
                )

        raw_payload = (
            artifact.path.read_bytes()
        )

        payload_size = facts[
            "payload_size_bytes"
        ]

        if len(
            raw_payload
        ) != payload_size:
            raise AndroidSflbEntryParsingError(
                "SFLB materialized payload size does not match "
                "canonical entry structure"
            )

        if (
            artifact.size_bytes is not None
            and artifact.size_bytes
            != len(
                raw_payload
            )
        ):
            raise AndroidSflbEntryParsingError(
                "SFLB Extraction artifact size evidence does not "
                "match the materialized payload"
            )

        return AndroidParsedSflbEntry(
            artifact=artifact,
            entry_name=(
                artifact.semantic_name
            ),
            container_index=facts[
                "sflb_container_index"
            ],
            container_offset_bytes=facts[
                "sflb_container_offset_bytes"
            ],
            container_span_bytes=facts[
                "sflb_container_span_bytes"
            ],
            version=facts[
                "sflb_version"
            ],
            entry_count=facts[
                "sflb_entry_count"
            ],
            secondary_count=facts[
                "sflb_secondary_count"
            ],
            entry_index=facts[
                "entry_index"
            ],
            record_offset_bytes=facts[
                "record_offset_bytes"
            ],
            payload_offset_bytes=facts[
                "payload_offset_bytes"
            ],
            absolute_payload_offset_bytes=facts[
                "absolute_payload_offset_bytes"
            ],
            payload_size_bytes=payload_size,
            opaque_word=facts[
                "opaque_word"
            ],
            flags=facts[
                "flags"
            ],
            raw_header_tail=(
                facts[
                    "raw_header_tail_u32_0"
                ],
                facts[
                    "raw_header_tail_u32_1"
                ],
                facts[
                    "raw_header_tail_u32_2"
                ],
            ),
            raw_payload=raw_payload,
        )
