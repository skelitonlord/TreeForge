from __future__ import annotations

from treeforge.android.parsing.init.model import (
    AndroidInitAction,
)
from treeforge.android.universe.init.action_trigger.model import (
    AndroidUniverseInitActionEventTriggerClause,
    AndroidUniverseInitActionPropertyTriggerClause,
    AndroidUniverseInitActionTrigger,
)


class AndroidUniverseInitActionTriggerInterpreter:
    """
    Interpret one parsed INIT action trigger into ordered semantic clauses.

    The currently established grammar is conjunction-only:
    event clauses and property predicates joined by ``&&``.
    """

    def interpret(
        self,
        action: AndroidInitAction,
    ) -> AndroidUniverseInitActionTrigger:
        if not isinstance(
            action,
            AndroidInitAction,
        ):
            raise TypeError(
                "action must be an AndroidInitAction"
            )

        raw_clauses = tuple(
            part.strip()
            for part in action.trigger.split(
                "&&"
            )
        )

        if not raw_clauses:
            raise ValueError(
                "action trigger must contain at least one clause"
            )

        if any(
            not clause
            for clause in raw_clauses
        ):
            raise ValueError(
                "action trigger contains an empty conjunction clause: "
                f"{action.trigger!r}"
            )

        clauses = tuple(
            self._interpret_clause(
                clause
            )
            for clause in raw_clauses
        )

        return (
            AndroidUniverseInitActionTrigger(
                action=action,
                clauses=clauses,
            )
        )

    def _interpret_clause(
        self,
        clause: str,
    ):
        if clause.startswith(
            "property:"
        ):
            return (
                self._interpret_property_clause(
                    clause
                )
            )

        return (
            AndroidUniverseInitActionEventTriggerClause(
                event=clause
            )
        )

    @staticmethod
    def _interpret_property_clause(
        clause: str,
    ) -> AndroidUniverseInitActionPropertyTriggerClause:
        body = clause[
            len("property:"):
        ]

        if "=" not in body:
            raise ValueError(
                "property trigger clause must contain '=': "
                f"{clause!r}"
            )

        name, value = body.split(
            "=",
            maxsplit=1,
        )

        if not name:
            raise ValueError(
                "property trigger name must not be empty: "
                f"{clause!r}"
            )

        return (
            AndroidUniverseInitActionPropertyTriggerClause(
                name=name,
                value=value,
            )
        )