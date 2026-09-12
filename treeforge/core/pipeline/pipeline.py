from __future__ import annotations

import logging

from treeforge.core.context.context import Context
from treeforge.core.pipeline.stage import PipelineStage
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)

logger = logging.getLogger(__name__)


class Pipeline:
    """Executes a sequence of pipeline stages."""

    def __init__(
        self,
        *,
        progress_callback: ProgressCallback | None = None,
        progress_stage: str | None = None,
    ) -> None:
        """Create an empty pipeline."""

        self._stages: list[PipelineStage] = []
        self._progress_callback = progress_callback
        self._progress_stage = progress_stage

    def add_stage(
        self,
        stage: PipelineStage,
    ) -> None:
        """Add a stage to the pipeline."""

        self._stages.append(
            stage
        )

    def run(
        self,
        context: Context,
    ) -> None:
        """Run all pipeline stages."""

        total = len(
            self._stages
        )

        for index, stage in enumerate(
            self._stages,
            start=1,
        ):
            logger.info(
                "Running stage %s",
                stage.name,
            )

            if (
                self._progress_callback is not None
                and self._progress_stage is not None
            ):
                self._progress_callback(
                    ProgressEvent(
                        stage=self._progress_stage,
                        state=ProgressState.RUNNING,
                        current=index - 1,
                        total=total,
                        detail=stage.name,
                    )
                )

            stage.execute(
                context
            )

            if (
                self._progress_callback is not None
                and self._progress_stage is not None
            ):
                self._progress_callback(
                    ProgressEvent(
                        stage=self._progress_stage,
                        state=ProgressState.COMPLETE,
                        current=index,
                        total=total,
                        detail=stage.name,
                    )
                )

        logger.info(
            "Pipeline complete"
        )
