from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.semantic_interpreter import (
    AndroidUniverseInitServiceSemanticInterpreter,
)


class AndroidUniverseInitServiceInterpreter:
    """
    Interpret parsed Android init services as Universe requirements.

    The complete Parsing declaration is retained while intrinsic service
    semantics are interpreted additively.
    """

    def __init__(
        self,
        *,
        semantic_interpreter: (
            AndroidUniverseInitServiceSemanticInterpreter
            | None
        ) = None,
    ) -> None:
        self.semantic_interpreter = (
            semantic_interpreter
            if semantic_interpreter is not None
            else AndroidUniverseInitServiceSemanticInterpreter()
        )



    def interpret(
        self,
        sources: tuple[
            ParsedAndroidInitSource,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitServiceRequirement,
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
            for service in source.services:
                requirements.append(
                    AndroidUniverseInitServiceRequirement(
                        source_path=source.source_path,
                        android_path=source.android_path,
                        filesystem_source=(
                            source.filesystem_source
                        ),
                        service=service,
                        semantics=(
                            self.semantic_interpreter.interpret(
                                service
                            )
                        ),
                    )
                )

        return tuple(
            requirements
        )
