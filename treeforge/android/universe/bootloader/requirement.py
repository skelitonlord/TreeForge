from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.bootloader import (
    AndroidParsedBootFirmwarePayload,
    AndroidParsedBootloaderChild,
    AndroidParsedFbpt,
    AndroidParsedUfpk,
    AndroidParsedUfpkDescriptor,
    AndroidParsedUfsDescriptor,
)
from treeforge.android.parsing.result import (
    ParsedBootloaderChild,
)


class AndroidUniverseBootloaderRequirementFamily(
    StrEnum
):
    """
    Canonical semantic family for one bootloader requirement.

    Families are derived only from Parsing-stage structural identity.
    They do not assign vendor/device policy or execution meaning.
    """

    FIRMWARE_PAYLOAD = "firmware_payload"
    PARTITION_TABLE = "partition_table"
    UFS_DESCRIPTOR = "ufs_descriptor"
    FIRMWARE_PACKAGE = "firmware_package"
    FIRMWARE_PACKAGE_DESCRIPTOR = (
        "firmware_package_descriptor"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootloaderSemanticCoverage:
    """
    Universe-owned semantic coverage for one canonical bootloader requirement.

    ``interpreted_observations`` counts fields whose structural or semantic
    meaning has been established from canonical evidence.

    ``preserved_opaque_observations`` counts exact evidence intentionally
    retained without semantic decoding. Opaque preservation is not itself a
    semantic-completeness failure.

    ``unresolved_observations`` counts named structural observations whose
    meaning remains genuinely unresolved. Their values remain preserved rather
    than guessed.
    """

    interpreted_observations: int
    preserved_opaque_observations: int
    unresolved_observations: int

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "interpreted_observations",
                self.interpreted_observations,
            ),
            (
                "preserved_opaque_observations",
                self.preserved_opaque_observations,
            ),
            (
                "unresolved_observations",
                self.unresolved_observations,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootloaderRequirement:
    """
    Canonical device-level requirement promoted from one parsed bootloader child.

    Extraction remains authoritative for FBPK/container child materialization.
    Parsing remains authoritative for literal child-format decoding.

    Universe preserves the exact ParsedBootloaderChild as canonical evidence
    and owns later device-level interpretation and reconciliation.
    """

    source: ParsedBootloaderChild

    validated_descriptor_count: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedBootloaderChild,
        ):
            raise TypeError(
                "source must be a ParsedBootloaderChild"
            )

        if not isinstance(
            self.source.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "source.artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.source.parsed,
            (
                AndroidParsedBootFirmwarePayload,
                AndroidParsedFbpt,
                AndroidParsedUfsDescriptor,
                AndroidParsedUfpk,
                AndroidParsedUfpkDescriptor,
            ),
        ):
            raise TypeError(
                "source.parsed must be a supported "
                "bootloader Parsing result"
            )


        if self.validated_descriptor_count is not None:
            if (
                isinstance(
                    self.validated_descriptor_count,
                    bool,
                )
                or not isinstance(
                    self.validated_descriptor_count,
                    int,
                )
                or self.validated_descriptor_count < 0
            ):
                raise ValueError(
                    "validated_descriptor_count must be a "
                    "non-negative integer or None"
                )

            if not isinstance(
                self.source.parsed,
                AndroidParsedUfpk,
            ):
                raise ValueError(
                    "validated_descriptor_count is only valid "
                    "for an AndroidParsedUfpk requirement"
                )

            if (
                self.validated_descriptor_count
                != self.source.parsed.header_value_0x4c
            ):
                raise ValueError(
                    "validated_descriptor_count must match the "
                    "literal UFPK header value at offset 0x4c"
                )

    @property
    def family(
        self,
    ) -> AndroidUniverseBootloaderRequirementFamily:
        parsed = self.source.parsed

        if isinstance(
            parsed,
            AndroidParsedBootFirmwarePayload,
        ):
            return (
                AndroidUniverseBootloaderRequirementFamily
                .FIRMWARE_PAYLOAD
            )

        if isinstance(
            parsed,
            AndroidParsedFbpt,
        ):
            return (
                AndroidUniverseBootloaderRequirementFamily
                .PARTITION_TABLE
            )

        if isinstance(
            parsed,
            AndroidParsedUfsDescriptor,
        ):
            return (
                AndroidUniverseBootloaderRequirementFamily
                .UFS_DESCRIPTOR
            )

        if isinstance(
            parsed,
            AndroidParsedUfpk,
        ):
            return (
                AndroidUniverseBootloaderRequirementFamily
                .FIRMWARE_PACKAGE
            )

        if isinstance(
            parsed,
            AndroidParsedUfpkDescriptor,
        ):
            return (
                AndroidUniverseBootloaderRequirementFamily
                .FIRMWARE_PACKAGE_DESCRIPTOR
            )

        raise TypeError(
            "unsupported bootloader Parsing result"
        )

    @property
    def fbpt_trailing_text_observations(
        self,
    ) -> tuple[
        str | None,
        ...,
    ]:
        """
        Interpret the fixed FBPT trailing field as optional NUL-terminated
        ASCII when its bytes prove that representation.

        The field's higher-level purpose is deliberately not guessed.
        ``None`` means the field is structurally empty.
        """

        parsed = self.source.parsed

        if not isinstance(
            parsed,
            AndroidParsedFbpt,
        ):
            return ()

        observations: list[
            str | None
        ] = []

        for entry in parsed.entries:
            raw = entry.reserved_tail

            if not raw:
                observations.append(
                    None
                )
                continue

            value_bytes = raw.split(
                b"\0",
                1,
            )[0]

            if not value_bytes:
                observations.append(
                    None
                )
                continue

            if not all(
                0x20 <= byte < 0x7F
                for byte in value_bytes
            ):
                raise ValueError(
                    "FBPT trailing field contains non-ASCII "
                    "non-zero data"
                )

            observations.append(
                value_bytes.decode(
                    "ascii"
                )
            )

        return tuple(
            observations
        )

    @property
    def nonempty_fbpt_trailing_text_observations(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            value
            for value in (
                self.fbpt_trailing_text_observations
            )
            if value is not None
        )

    @property
    def ufpk_descriptor_count_is_validated(
        self,
    ) -> bool:
        return (
            isinstance(
                self.source.parsed,
                AndroidParsedUfpk,
            )
            and self.validated_descriptor_count
            is not None
        )

    @property
    def semantic_coverage(
        self,
    ) -> AndroidUniverseBootloaderSemanticCoverage:
        """
        Report structural semantic coverage without inventing unknown meaning.
        """

        parsed = self.source.parsed

        if isinstance(
            parsed,
            AndroidParsedFbpt,
        ):
            #
            # Header semantics:
            #   version
            #   table_index
            #   entry_count
            #   table_identifier
            #
            # Preserved opaque header evidence:
            #   reserved_header_value
            #
            # Per-entry semantics:
            #   index
            #   size_bytes
            #   name
            #   type_identifier
            #   instance_identifier
            #   optional trailing ASCII text
            #
            # Preserved opaque per-entry evidence:
            #   reserved_prefix
            #
            # Parsing has structurally identified this reserved field and
            # preserves the exact record bytes. Universe intentionally makes
            # no vendor-specific claim about its meaning.
            #
            trailing_text_observations = (
                self.fbpt_trailing_text_observations
            )

            if (
                len(
                    trailing_text_observations
                )
                != len(
                    parsed.entries
                )
            ):
                raise ValueError(
                    "FBPT trailing-text population must match "
                    "the entry population"
                )

            return AndroidUniverseBootloaderSemanticCoverage(
                interpreted_observations=(
                    4
                    + (
                        len(
                            parsed.entries
                        )
                        * 6
                    )
                ),
                preserved_opaque_observations=(
                    1
                    + len(
                        parsed.entries
                    )
                ),
                unresolved_observations=0,
            )

        if isinstance(
            parsed,
            AndroidParsedUfsDescriptor,
        ):
            #
            # kind and version are structurally established.
            # The remainder of the exact payload is retained but not
            # semantically decoded.
            #
            return AndroidUniverseBootloaderSemanticCoverage(
                interpreted_observations=2,
                preserved_opaque_observations=1,
                unresolved_observations=0,
            )

        if isinstance(
            parsed,
            AndroidParsedUfpk,
        ):
            #
            # Structurally established:
            #   version
            #   package_name
            #   declared_size
            #   device_identifier
            #   controller_identifier
            #   firmware_identifier
            #
            # Population-reconciled when canonical descriptor evidence exists:
            #   header_value_0x4c -> descriptor count
            #
            # Preserved opaque evidence:
            #   header_value_0x54
            #   remaining raw header/payload state
            #
            # header_value_0x4c is interpreted only when canonical descriptor
            # population reconciliation validates it as the descriptor count.
            #
            descriptor_count_interpreted = (
                1
                if self.ufpk_descriptor_count_is_validated
                else 0
            )

            return AndroidUniverseBootloaderSemanticCoverage(
                interpreted_observations=(
                    6
                    + descriptor_count_interpreted
                ),
                preserved_opaque_observations=2,
                unresolved_observations=(
                    0
                    if descriptor_count_interpreted
                    else 1
                ),
            )

        if isinstance(
            parsed,
            AndroidParsedUfpkDescriptor,
        ):
            #
            # Structurally established:
            #   descriptor_kind
            #   identity
            #   next_offset
            #
            # Preserved opaque evidence:
            #   field_28
            #
            # The scalar and raw descriptor header are retained exactly, but
            # Universe does not assign unsupported vendor-specific semantics.
            #
            return AndroidUniverseBootloaderSemanticCoverage(
                interpreted_observations=3,
                preserved_opaque_observations=1,
                unresolved_observations=0,
            )

        if isinstance(
            parsed,
            AndroidParsedBootFirmwarePayload,
        ):
            #
            # All exposed fields are literal observations of the terminal
            # payload. They are interpreted as observations only; Universe
            # does not infer firmware execution role or platform policy.
            #
            return AndroidUniverseBootloaderSemanticCoverage(
                interpreted_observations=6,
                preserved_opaque_observations=0,
                unresolved_observations=0,
            )

        raise TypeError(
            "unsupported bootloader Parsing result"
        )

    @property
    def structural_child_count(
        self,
    ) -> int:
        """
        Number of structurally contained semantic children exposed by Parsing.
        """

        parsed = self.source.parsed

        if isinstance(
            parsed,
            AndroidParsedFbpt,
        ):
            return len(
                parsed.entries
            )

        return 0

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        return self.source.artifact

    @property
    def parsed(
        self,
    ) -> AndroidParsedBootloaderChild:
        return self.source.parsed

    @property
    def parsed_type(
        self,
    ) -> str:
        return type(
            self.source.parsed
        ).__name__

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "bootloader:"
            f"{self.source.artifact.path.as_posix()}:"
            f"{self.parsed_type}"
        )
