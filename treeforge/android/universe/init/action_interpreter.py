from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.action_command import (
    AndroidUniverseInitActionCommandInterpreter,
)
from treeforge.android.universe.init.action_trigger import (
    AndroidUniverseInitActionTriggerInterpreter,
)


class AndroidUniverseInitActionInterpreter:
    """
    Promote parsed INIT actions into canonical Universe requirements.

    Parsed action and command identities remain lossless while each action
    command is interpreted into its canonical action-command semantics.
    """

    def __init__(
        self,
        *,
        command_interpreter: (
            AndroidUniverseInitActionCommandInterpreter
            | None
        ) = None,
        trigger_interpreter: (
            AndroidUniverseInitActionTriggerInterpreter
            | None
        ) = None,
    ) -> None:
        self.command_interpreter = (
            command_interpreter
            if command_interpreter is not None
            else AndroidUniverseInitActionCommandInterpreter()
        )

        self.trigger_interpreter = (
            trigger_interpreter
            if trigger_interpreter is not None
            else AndroidUniverseInitActionTriggerInterpreter()
        )

    def interpret(
        self,
        sources: tuple[
            ParsedAndroidInitSource,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitActionRequirement,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                ParsedAndroidInitSource,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedAndroidInitSource instances"
            )

        requirements = []

        for source in sources:
            for action in source.actions:
                trigger_semantics = (
                    self.trigger_interpreter.interpret(
                        action
                    )
                )

                command_requirements = (
                    self.command_interpreter.interpret_all(
                        action.commands
                    )
                )

                requirements.append(
                    AndroidUniverseInitActionRequirement(
                        source_path=source.source_path,
                        android_path=source.android_path,
                        filesystem_source=(
                            source.filesystem_source
                        ),
                        action=action,
                        trigger_semantics=(
                            trigger_semantics
                        ),
                        command_requirements=(
                            command_requirements
                        ),
                    )
                )

        return tuple(
            requirements
        )
