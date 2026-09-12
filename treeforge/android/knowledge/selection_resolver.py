from __future__ import annotations

from treeforge.android.discovery.identity import (
    AndroidIdentityInferenceResult,
)
from treeforge.android.knowledge.registry import (
    AndroidKnowledgeRegistry,
)
from treeforge.android.knowledge.selection import (
    AndroidKnowledgeRootSelection,
    AndroidKnowledgeSelection,
    AndroidKnowledgeSelectionSource,
)


class AndroidKnowledgeSelectionResolver:
    """
    Resolve optional device/platform Knowledge identities.

    Device and platform identities do not imply that a matching Knowledge
    module must be installed. Knowledge specializes canonical identity when
    available; absence of a specialization leaves that identity intact.
    """

    def __init__(
        self,
        *,
        registry: AndroidKnowledgeRegistry,
    ) -> None:
        if not isinstance(
            registry,
            AndroidKnowledgeRegistry,
        ):
            raise TypeError(
                "registry must be an AndroidKnowledgeRegistry"
            )

        self.registry = registry

    def resolve(
        self,
        *,
        explicit: AndroidKnowledgeSelection,
        inferred: AndroidIdentityInferenceResult,
    ) -> tuple[
        AndroidKnowledgeRootSelection,
        ...,
    ]:
        if not isinstance(
            explicit,
            AndroidKnowledgeSelection,
        ):
            raise TypeError(
                "explicit must be an "
                "AndroidKnowledgeSelection"
            )

        if not isinstance(
            inferred,
            AndroidIdentityInferenceResult,
        ):
            raise TypeError(
                "inferred must be an "
                "AndroidIdentityInferenceResult"
            )

        roots: list[
            AndroidKnowledgeRootSelection
        ] = []

        device_root = self._device_root(
            explicit=explicit,
            inferred=inferred,
        )

        if device_root is not None:
            roots.append(
                device_root
            )

        platform_root = self._platform_root(
            explicit=explicit,
            inferred=inferred,
        )

        if platform_root is not None:
            roots.append(
                platform_root
            )

        return tuple(
            roots
        )

    def _device_root(
        self,
        *,
        explicit: AndroidKnowledgeSelection,
        inferred: AndroidIdentityInferenceResult,
    ) -> AndroidKnowledgeRootSelection | None:
        if explicit.device_id is not None:
            module_id = (
                f"device:{explicit.device_id}"
            )
            source = (
                AndroidKnowledgeSelectionSource
                .EXPLICIT
            )

        elif inferred.device_id is not None:
            module_id = (
                f"device:{inferred.device_id}"
            )
            source = (
                AndroidKnowledgeSelectionSource
                .INFERRED
            )

        else:
            return None

        if self.registry.module(
            module_id
        ) is None:
            return None

        return AndroidKnowledgeRootSelection(
            module_id=module_id,
            source=source,
        )

    def _platform_root(
        self,
        *,
        explicit: AndroidKnowledgeSelection,
        inferred: AndroidIdentityInferenceResult,
    ) -> AndroidKnowledgeRootSelection | None:
        if explicit.board_platform is not None:
            board_platform = (
                explicit.board_platform
            )
            source = (
                AndroidKnowledgeSelectionSource
                .EXPLICIT
            )

        elif inferred.board_platform is not None:
            board_platform = (
                inferred.board_platform
            )
            source = (
                AndroidKnowledgeSelectionSource
                .INFERRED
            )

        else:
            return None

        module_id = (
            f"platform:{board_platform}"
        )

        if self.registry.module(
            module_id
        ) is None:
            return None

        return AndroidKnowledgeRootSelection(
            module_id=module_id,
            source=source,
        )
