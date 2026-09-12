from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.dtb import (
    AndroidParsedDtboEntry,
    ParsedFdt,
)

from treeforge.android.universe.dtbo.semantic import (
    AndroidUniverseFdtPropertyObservation,
)
from treeforge.android.universe.dtbo.reconciliation import (
    AndroidUniverseFdtEntrySemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseDtboRequirement:
    """
    Canonical device-level requirement promoted from one parsed DTBO entry.

    Extraction remains authoritative for DTBO container/table materialization.
    Parsing remains authoritative for intrinsic FDT decoding.

    Universe preserves the exact AndroidParsedDtboEntry as evidence and owns
    generic FDT semantic interpretation and later cross-entry/device-level
    reconciliation.
    """

    source: AndroidParsedDtboEntry

    property_observations: tuple[
        AndroidUniverseFdtPropertyObservation,
        ...,
    ] = ()

    semantics: AndroidUniverseFdtEntrySemantics | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidParsedDtboEntry,
        ):
            raise TypeError(
                "source must be an AndroidParsedDtboEntry"
            )

        if (
            self.source.fdt.artifact
            is not self.source.artifact
        ):
            raise ValueError(
                "DTBO requirement source must preserve exact "
                "Parsing / Extraction artifact identity"
            )

        if not isinstance(
            self.property_observations,
            tuple,
        ):
            raise TypeError(
                "property_observations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFdtPropertyObservation,
            )
            for item in self.property_observations
        ):
            raise TypeError(
                "property_observations must contain only "
                "AndroidUniverseFdtPropertyObservation instances"
            )

        if len(
            self.property_observations
        ) != self.source.fdt.property_count:
            raise ValueError(
                "property_observations must preserve the complete "
                "parsed FDT property population"
            )

        if not isinstance(
            self.semantics,
            AndroidUniverseFdtEntrySemantics,
        ):
            raise TypeError(
                "semantics must be an AndroidUniverseFdtEntrySemantics"
            )

    @property
    def fdt(
        self,
    ) -> ParsedFdt:
        return self.source.fdt

    @property
    def node_count(
        self,
    ) -> int:
        return self.source.fdt.node_count

    @property
    def property_count(
        self,
    ) -> int:
        return self.source.fdt.property_count

    @property
    def reservation_count(
        self,
    ) -> int:
        return self.source.fdt.reservation_count

    @property
    def top_level_child_count(
        self,
    ) -> int:
        return self.source.fdt.top_level_child_count

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "dtbo:"
            f"{self.source.artifact.path.as_posix()}"
        )
