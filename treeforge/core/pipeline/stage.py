from abc import ABC, abstractmethod

from treeforge.core.context.context import Context


class PipelineStage(ABC):
    """Base class for all pipeline stages."""

    name = "Unnamed Stage"

    @abstractmethod
    def execute(
        self,
        context: Context,
    ) -> None:
        """Execute the stage."""
        raise NotImplementedError