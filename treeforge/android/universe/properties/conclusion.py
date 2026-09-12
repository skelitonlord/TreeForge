from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)


class AndroidUniverseConclusionStatus(
    StrEnum
):
    """
    Resolution state of one canonical Universe conclusion.
    """

    UNRESOLVED = "unresolved"
    AGREED = "agreed"
    CONFLICTING = "conflicting"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFactConclusion:
    """
    Canonical Universe conclusion for one semantic fact.

    Every eligible observation is retained. A canonical value exists only
    when all eligible non-empty observations agree unanimously.
    """

    fact: str

    status: AndroidUniverseConclusionStatus

    value: str | None

    evidence: tuple[
        AndroidUniversePropertyEvidence,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.fact,
            str,
        ):
            raise TypeError(
                "fact must be a string"
            )

        if not self.fact.strip():
            raise ValueError(
                "fact must not be empty"
            )

        if not isinstance(
            self.status,
            AndroidUniverseConclusionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseConclusionStatus"
            )

        if (
            self.value is not None
            and not isinstance(
                self.value,
                str,
            )
        ):
            raise TypeError(
                "value must be a string or None"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniversePropertyEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniversePropertyEvidence"
            )

        if self.status is (
            AndroidUniverseConclusionStatus.AGREED
        ):
            if self.value is None:
                raise ValueError(
                    "agreed conclusion must have a value"
                )

        else:
            if self.value is not None:
                raise ValueError(
                    "only agreed conclusions may have "
                    "a canonical value"
                )

    @property
    def distinct_values(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.fact.value
                    for item in self.evidence
                    if item.fact.value
                }
            )
        )