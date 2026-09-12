from __future__ import annotations

from treeforge.android.parsing.init.model import (
    AndroidInitCommand,
    AndroidInitService,
)
from treeforge.android.universe.init.action_command.interpreter import (
    AndroidUniverseInitActionCommandInterpreter,
)
from treeforge.android.universe.init.onrestart import (
    AndroidUniverseInitOnRestartCommand,
)


class AndroidUniverseInitOnRestartInterpreter:
    """
    Project parsed ``onrestart`` declarations into canonical command
    boundaries without interpreting command-specific syntax.
    """

    def interpret(
        self,
        service: AndroidInitService,
    ) -> tuple[
        AndroidUniverseInitOnRestartCommand,
        ...,
    ]:
        if not isinstance(
            service,
            AndroidInitService,
        ):
            raise TypeError(
                "service must be an AndroidInitService"
            )

        commands = []

        for declaration in service.options_for(
            "onrestart"
        ):
            if not declaration.arguments:
                raise ValueError(
                    "expected command for init service "
                    "'onrestart' declaration on service "
                    f"{service.name!r}"
                )

            semantic_command = AndroidInitCommand(
                keyword=declaration.arguments[0],
                arguments=declaration.arguments[1:],
                location=declaration.location,
                raw=declaration.raw,
            )

            semantic_requirement = (
                AndroidUniverseInitActionCommandInterpreter()
                .interpret(
                    semantic_command
                )
            )

            commands.append(
                AndroidUniverseInitOnRestartCommand(
                    command=semantic_command.keyword,
                    arguments=semantic_command.arguments,
                    declaration=declaration,
                    semantics=semantic_requirement.semantics,
                )
            )

        return tuple(
            commands
        )
