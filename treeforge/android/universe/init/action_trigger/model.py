from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from treeforge.android.parsing.init.model import (
    AndroidInitAction,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionEventTriggerClause:
    """
    One named Android INIT event trigger clause.
    """

    event: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.event,
            str,
        ):
            raise TypeError(
                "event must be a string"
            )

        if not self.event:
            raise ValueError(
                "event must not be empty"
            )

        if self.event.startswith(
            "property:"
        ):
            raise ValueError(
                "event trigger clause must not use "
                "property syntax"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionPropertyTriggerClause:
    """
    One Android INIT property trigger predicate.

    ``value`` is preserved literally, including wildcard ``*`` and
    explicit empty values.
    """

    name: str
    value: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name must not be empty"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )


AndroidUniverseInitActionTriggerClause: TypeAlias = (
    AndroidUniverseInitActionEventTriggerClause
    | AndroidUniverseInitActionPropertyTriggerClause
)


ANDROID_UNIVERSE_INIT_ACTION_TRIGGER_CLAUSE_TYPES = (
    AndroidUniverseInitActionEventTriggerClause,
    AndroidUniverseInitActionPropertyTriggerClause,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionTrigger:
    """
    Canonical semantic interpretation of one INIT action trigger.

    Clauses remain in source order. The original parsed action remains
    attached so literal trigger text, raw header, source location,
    command ownership, and provenance remain lossless.
    """

    action: AndroidInitAction

    clauses: tuple[
        AndroidUniverseInitActionTriggerClause,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.action,
            AndroidInitAction,
        ):
            raise TypeError(
                "action must be an AndroidInitAction"
            )

        if not isinstance(
            self.clauses,
            tuple,
        ):
            raise TypeError(
                "clauses must be a tuple"
            )

        if not self.clauses:
            raise ValueError(
                "clauses must not be empty"
            )

        if not all(
            isinstance(
                clause,
                ANDROID_UNIVERSE_INIT_ACTION_TRIGGER_CLAUSE_TYPES,
            )
            for clause in self.clauses
        ):
            raise TypeError(
                "clauses must contain only supported "
                "INIT action trigger clauses"
            )

    @property
    def expression(
        self,
    ) -> str:
        return self.action.trigger

    @property
    def event_clauses(
        self,
    ) -> tuple[
        AndroidUniverseInitActionEventTriggerClause,
        ...,
    ]:
        return tuple(
            clause
            for clause in self.clauses
            if isinstance(
                clause,
                AndroidUniverseInitActionEventTriggerClause,
            )
        )

    @property
    def property_clauses(
        self,
    ) -> tuple[
        AndroidUniverseInitActionPropertyTriggerClause,
        ...,
    ]:
        return tuple(
            clause
            for clause in self.clauses
            if isinstance(
                clause,
                AndroidUniverseInitActionPropertyTriggerClause,
            )
        )

    @property
    def is_compound(
        self,
    ) -> bool:
        return len(
            self.clauses
        ) > 1