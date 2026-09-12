from __future__ import annotations

from treeforge.android.knowledge.model import (
    AndroidKnowledgeCapability,
    AndroidKnowledgeModule,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationStage,
)


def applied_universe_knowledge_modules(
    context: Context,
) -> tuple[
    AndroidKnowledgeModule,
    ...,
]:
    """
    Return resolved Knowledge modules that Universe is explicitly allowed
    to apply.

    Knowledge resolution and Knowledge application are intentionally
    independent:

        resolved != applied

    A resolved profile may remain attached to Context and snapshots while
    Universe Knowledge application is disabled.

    Universe application is OFF unless the caller explicitly enables
    KnowledgeApplicationStage.UNIVERSE.
    """

    if not isinstance(
        context,
        Context,
    ):
        raise TypeError(
            "context must be a Context"
        )

    if not (
        context
        .knowledge_application_policy
        .enabled_for(
            KnowledgeApplicationStage.UNIVERSE
        )
    ):
        return ()

    resolution = (
        context.knowledge_resolution
    )

    if resolution is None:
        return ()

    return (
        resolution
        .profile
        .modules_supporting(
            AndroidKnowledgeCapability.UNIVERSE
        )
    )


def applied_universe_architecture_knowledge_modules(
    context: Context,
) -> tuple[
    AndroidKnowledgeModule,
    ...,
]:
    return tuple(
        module
        for module
        in applied_universe_knowledge_modules(
            context
        )
        if (
            module.universe is not None
            and module.universe.architecture
            is not None
        )
    )


def applied_universe_vintf_knowledge_modules(
    context: Context,
) -> tuple[
    AndroidKnowledgeModule,
    ...,
]:
    return tuple(
        module
        for module
        in applied_universe_knowledge_modules(
            context
        )
        if (
            module.universe is not None
            and module.universe.vintf_selections
        )
    )
