from __future__ import annotations

from dataclasses import (
    dataclass,
    fields,
)
from enum import StrEnum

from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


class AndroidUniverseParsingPopulationDispositionKind(
    StrEnum,
):
    """
    Explicit disposition of one top-level AndroidParsingResult population at
    the Parsing -> Android Device Universe boundary.
    """

    SEMANTICALLY_CONSUMED = "semantically_consumed"

    DELIBERATELY_PASS_THROUGH = (
        "deliberately_pass_through"
    )

    DOWNSTREAM_OWNED = "downstream_owned"

    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseParsingPopulationDisposition:
    """
    Explicit boundary accounting for one canonical Parsing population.

    ``parsing_value`` must be the exact object owned by the supplied
    AndroidParsingResult. This invariant intentionally applies equally to a
    live Parsing result and to a graph restored from a Parsing snapshot.

    ``universe_values`` identifies the canonical Universe representations
    produced from or associated with this Parsing population. Family-specific
    models remain responsible for stronger semantic and identity invariants.
    """

    population_name: str

    disposition: (
        AndroidUniverseParsingPopulationDispositionKind
    )

    parsing_value: object

    universe_values: tuple[
        object,
        ...,
    ] = ()

    reason: str = ""

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.population_name,
                str,
            )
            or not self.population_name
        ):
            raise ValueError(
                "population_name must be a non-empty string"
            )

        if not isinstance(
            self.disposition,
            AndroidUniverseParsingPopulationDispositionKind,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidUniverseParsingPopulationDispositionKind"
            )

        if not isinstance(
            self.universe_values,
            tuple,
        ):
            raise TypeError(
                "universe_values must be a tuple"
            )

        if (
            not isinstance(
                self.reason,
                str,
            )
            or not self.reason
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseParsingBoundary:
    """
    Complete canonical accounting of AndroidParsingResult at the Universe
    boundary.

    The boundary is intentionally derived from the AndroidParsingResult
    dataclass field population rather than a hand-maintained master list.
    Adding a new Parsing result field therefore makes an incomplete Universe
    boundary fail immediately instead of allowing the population to disappear
    silently.

    This contract is source-path agnostic: live Parsing and Parsing snapshot
    restoration must satisfy exactly the same invariants.
    """

    parsing: AndroidParsingResult

    dispositions: tuple[
        AndroidUniverseParsingPopulationDisposition,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if not isinstance(
            self.dispositions,
            tuple,
        ):
            raise TypeError(
                "dispositions must be a tuple"
            )

        if not all(
            isinstance(
                disposition,
                AndroidUniverseParsingPopulationDisposition,
            )
            for disposition
            in self.dispositions
        ):
            raise TypeError(
                "dispositions must contain only "
                "AndroidUniverseParsingPopulationDisposition values"
            )

        expected_names = tuple(
            field.name
            for field
            in fields(
                AndroidParsingResult
            )
        )

        actual_names = tuple(
            disposition.population_name
            for disposition
            in self.dispositions
        )

        if len(
            actual_names
        ) != len(
            set(
                actual_names
            )
        ):
            raise ValueError(
                "Parsing boundary contains duplicate population names"
            )

        if set(
            actual_names
        ) != set(
            expected_names
        ):
            missing = tuple(
                name
                for name in expected_names
                if name not in actual_names
            )

            unexpected = tuple(
                name
                for name in actual_names
                if name not in expected_names
            )

            raise ValueError(
                "Parsing boundary must account for every "
                "AndroidParsingResult population exactly once: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        if actual_names != expected_names:
            raise ValueError(
                "Parsing boundary dispositions must preserve "
                "AndroidParsingResult field order"
            )

        for disposition in self.dispositions:
            expected_value = getattr(
                self.parsing,
                disposition.population_name,
            )

            if (
                disposition.parsing_value
                is not expected_value
            ):
                raise ValueError(
                    "Parsing boundary must preserve exact canonical "
                    "Parsing population identity: "
                    f"{disposition.population_name}"
                )

    def disposition_for(
        self,
        population_name: str,
    ) -> AndroidUniverseParsingPopulationDisposition:
        if not isinstance(
            population_name,
            str,
        ):
            raise TypeError(
                "population_name must be a string"
            )

        for disposition in self.dispositions:
            if (
                disposition.population_name
                == population_name
            ):
                return disposition

        raise KeyError(
            population_name
        )

    @property
    def semantically_consumed(
        self,
    ) -> tuple[
        AndroidUniverseParsingPopulationDisposition,
        ...,
    ]:
        return tuple(
            disposition
            for disposition
            in self.dispositions
            if disposition.disposition
            is AndroidUniverseParsingPopulationDispositionKind
            .SEMANTICALLY_CONSUMED
        )

    @property
    def deliberately_pass_through(
        self,
    ) -> tuple[
        AndroidUniverseParsingPopulationDisposition,
        ...,
    ]:
        return tuple(
            disposition
            for disposition
            in self.dispositions
            if disposition.disposition
            is AndroidUniverseParsingPopulationDispositionKind
            .DELIBERATELY_PASS_THROUGH
        )

    @property
    def unresolved(
        self,
    ) -> tuple[
        AndroidUniverseParsingPopulationDisposition,
        ...,
    ]:
        return tuple(
            disposition
            for disposition
            in self.dispositions
            if disposition.disposition
            is AndroidUniverseParsingPopulationDispositionKind
            .UNRESOLVED
        )

    @property
    def downstream_owned(
        self,
    ) -> tuple[
        AndroidUniverseParsingPopulationDisposition,
        ...,
    ]:
        return tuple(
            disposition
            for disposition
            in self.dispositions
            if disposition.disposition
            is AndroidUniverseParsingPopulationDispositionKind
            .DOWNSTREAM_OWNED
        )
