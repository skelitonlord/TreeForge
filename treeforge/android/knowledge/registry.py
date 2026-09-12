from __future__ import annotations

from treeforge.android.knowledge.model import (
    AndroidKnowledgeModule,
)


class AndroidKnowledgeRegistry:
    """
    Deterministic registry of installed TreeForge knowledge modules.

    The registry stores modules only.

    Dependency traversal and knowledge-profile construction belong to
    AndroidKnowledgeResolver.
    """

    def __init__(
        self,
        *,
        modules: tuple[
            AndroidKnowledgeModule,
            ...,
        ] = (),
    ) -> None:
        if not isinstance(
            modules,
            tuple,
        ):
            raise TypeError(
                "modules must be a tuple"
            )

        registry: dict[
            str,
            AndroidKnowledgeModule,
        ] = {}

        for module in modules:
            if not isinstance(
                module,
                AndroidKnowledgeModule,
            ):
                raise TypeError(
                    "modules must contain "
                    "AndroidKnowledgeModule "
                    "instances"
                )

            if module.module_id in registry:
                raise ValueError(
                    "duplicate knowledge module ID: "
                    f"{module.module_id}"
                )

            registry[
                module.module_id
            ] = module

        self._modules = registry

    def module(
        self,
        module_id: str,
    ) -> AndroidKnowledgeModule | None:
        self._validate_module_id(
            module_id
        )

        return self._modules.get(
            module_id
        )

    def require(
        self,
        module_id: str,
    ) -> AndroidKnowledgeModule:
        module = self.module(
            module_id
        )

        if module is None:
            raise KeyError(
                "unknown Android knowledge module: "
                f"{module_id}"
            )

        return module

    @property
    def modules(
        self,
    ) -> tuple[
        AndroidKnowledgeModule,
        ...,
    ]:
        return tuple(
            self._modules[
                module_id
            ]
            for module_id in sorted(
                self._modules
            )
        )

    @staticmethod
    def _validate_module_id(
        module_id: str,
    ) -> None:
        if not isinstance(
            module_id,
            str,
        ):
            raise TypeError(
                "module_id must be a string"
            )

        if not module_id.strip():
            raise ValueError(
                "module_id must not be empty"
            )