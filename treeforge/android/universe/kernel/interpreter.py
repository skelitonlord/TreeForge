from __future__ import annotations

from treeforge.android.parsing.kernel import (
    ParsedKernelImage,
)

from treeforge.android.universe.kernel.requirement import (
    AndroidUniverseKernelConfigRequirement,
    AndroidUniverseKernelRequirement,
    AndroidUniverseKernelUnparsedConfigEvidence,
)


class AndroidUniverseKernelInterpreter:
    """
    Promote canonical Parsing-stage kernel observations into Universe.

    This interpreter never reopens or reparses the kernel image.
    """

    def interpret(
        self,
        parsing: tuple[
            ParsedKernelImage,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelRequirement,
        ...,
    ]:
        if not isinstance(
            parsing,
            tuple,
        ):
            raise TypeError(
                "parsing must be a tuple"
            )

        if not all(
            isinstance(
                source,
                ParsedKernelImage,
            )
            for source in parsing
        ):
            raise TypeError(
                "parsing must contain only "
                "ParsedKernelImage entries"
            )

        requirements: list[
            AndroidUniverseKernelRequirement
        ] = []

        for source in parsing:
            if source.config is None:
                config_requirements = ()
                unparsed_config_evidence = ()
            else:
                config_requirements = tuple(
                    AndroidUniverseKernelConfigRequirement(
                        source=source,
                        declaration=declaration,
                    )
                    for declaration
                    in source.config.declarations
                )

                unparsed_config_evidence = tuple(
                    AndroidUniverseKernelUnparsedConfigEvidence(
                        source=source,
                        line=line,
                    )
                    for line
                    in source.config.unparsed_lines
                )

            requirements.append(
                AndroidUniverseKernelRequirement(
                    source=source,
                    config_requirements=(
                        config_requirements
                    ),
                    unparsed_config_evidence=(
                        unparsed_config_evidence
                    ),
                )
            )

        return tuple(
            requirements
        )
