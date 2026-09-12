from __future__ import annotations

from treeforge.android.parsing.apex.model import (
    ParsedApexContainer,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)
from treeforge.android.universe.apex.deployment_context import (
    AndroidUniverseApexDeploymentContextResolver,
)


class AndroidUniverseApexInterpreter:
    """
    Promote the complete canonical Parsing APEX population into Universe.

    Parsing owns container decoding, lineage construction, payload identity,
    and manifest decoding. Universe preserves those exact identities and adds
    runtime/deployment context only.

    No APEX bytes are reopened or reparsed here.
    """

    def interpret(
        self,
        sources: tuple[
            ParsedApexContainer,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseApexRequirement,
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
                ParsedApexContainer,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedApexContainer instances"
            )

        requirements = tuple(
            AndroidUniverseApexRequirement(
                source=source,
                runtime_context=(
                    AndroidUniverseRuntimeContextResolver
                    .resolve_artifact(
                        source.outer_container
                    )
                ),
                deployment_context=(
                    AndroidUniverseApexDeploymentContextResolver
                    .resolve_artifact(
                        source.outer_container
                    )
                ),
            )
            for source in sources
        )

        if len(
            requirements
        ) != len(
            sources
        ):
            raise ValueError(
                "Universe APEX interpretation must conserve "
                "the complete Parsing APEX population"
            )

        if not all(
            requirement.source is source
            for requirement, source
            in zip(
                requirements,
                sources,
                strict=True,
            )
        ):
            raise ValueError(
                "Universe APEX interpretation must preserve "
                "exact ParsedApexContainer identity and order"
            )

        return requirements
