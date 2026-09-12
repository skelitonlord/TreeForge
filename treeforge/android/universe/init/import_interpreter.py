from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
)
from treeforge.android.universe.init.import_requirement import (
    AndroidUniverseInitImportRequirement,
)


class AndroidUniverseInitImportInterpreter:
    """
    Promote parsed INIT import declarations into canonical Universe
    requirements.

    Parsing identity remains attached exactly. This interpreter does not
    resolve imports, expand properties, traverse imported sources, or infer
    runtime relationships.
    """

    def interpret(
        self,
        sources: tuple[
            ParsedAndroidInitSource,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitImportRequirement,
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
            for declaration in source.imports:
                requirements.append(
                    AndroidUniverseInitImportRequirement(
                        source_path=source.source_path,
                        android_path=source.android_path,
                        filesystem_source=(
                            source.filesystem_source
                        ),
                        declaration=declaration,
                    )
                )

        return tuple(
            requirements
        )