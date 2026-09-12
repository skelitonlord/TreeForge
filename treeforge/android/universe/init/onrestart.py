from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.init.model import (
    AndroidInitServiceOption,
)
from treeforge.android.universe.init.action_command.semantics import (
    ANDROID_UNIVERSE_INIT_ACTION_COMMAND_SEMANTIC_TYPES,
    AndroidUniverseInitActionCommandSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitOnRestartCommand:
    """
    One command executed when an init service restarts.

    This model establishes the command boundary without interpreting the
    command-specific grammar. Command semantics are intentionally left for
    the shared INIT command interpretation layer.
    """

    command: str
    arguments: tuple[
        str,
        ...,
    ]
    declaration: AndroidInitServiceOption
    semantics: AndroidUniverseInitActionCommandSemantics

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.command,
            str,
        ):
            raise TypeError(
                "command must be a string"
            )

        if not self.command:
            raise ValueError(
                "command must not be empty"
            )

        if not isinstance(
            self.arguments,
            tuple,
        ):
            raise TypeError(
                "arguments must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.arguments
        ):
            raise TypeError(
                "arguments must contain only strings"
            )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if not isinstance(
            self.semantics,
            ANDROID_UNIVERSE_INIT_ACTION_COMMAND_SEMANTIC_TYPES,
        ):
            raise TypeError(
                "semantics must be a supported "
                "Android Universe INIT command semantic"
            )

        if (
            self.declaration.keyword
            != "onrestart"
        ):
            raise ValueError(
                "onrestart declaration must use keyword "
                "'onrestart'"
            )
