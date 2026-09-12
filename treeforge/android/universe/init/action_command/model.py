from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.init.model import (
    AndroidInitCommand,
)
from treeforge.android.universe.init.action_command.semantics import (
    ANDROID_UNIVERSE_INIT_ACTION_COMMAND_SEMANTIC_TYPES,
    AndroidUniverseInitActionCommandSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionCommandRequirement:
    """
    One interpreted command occurrence owned by an INIT action.

    The original parsed command remains attached exactly so later
    reconstruction retains raw syntax, ordering, location, and identity.
    """

    command: AndroidInitCommand
    semantics: AndroidUniverseInitActionCommandSemantics

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.command,
            AndroidInitCommand,
        ):
            raise TypeError(
                "command must be an AndroidInitCommand"
            )

        if not isinstance(
            self.semantics,
            ANDROID_UNIVERSE_INIT_ACTION_COMMAND_SEMANTIC_TYPES,
        ):
            raise TypeError(
                "semantics must be a supported "
                "Android Universe INIT action-command semantic"
            )

    @property
    def keyword(
        self,
    ) -> str:
        return self.command.keyword

    @property
    def arguments(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.command.arguments