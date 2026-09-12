from __future__ import annotations

import logging

from treeforge.core.context.context import Context
from treeforge.core.pipeline.stage import PipelineStage

logger = logging.getLogger(__name__)


class CreateWorkspaceStage(PipelineStage):
    """Create the directory structure for a workspace."""

    name = "Create Workspace"

    def execute(
        self,
        context: Context,
    ) -> None:

        logger.info("Creating workspace")

        context.workspace.create()