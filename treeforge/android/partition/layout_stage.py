from __future__ import annotations

from typing import Protocol

from treeforge.android.partition.layout import (
    PartitionLayout,
)
from treeforge.android.partition.layout_detector import (
    PartitionLayoutDetector,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.pipeline.stage import (
    PipelineStage,
)


class PartitionLayoutStageError(
    RuntimeError,
):
    """
    Raised when partition layout interpretation fails inside the pipeline.
    """


class PartitionLayoutDetectorLike(
    Protocol,
):
    def detect(
        self,
        context: Context,
    ) -> PartitionLayout:
        ...


class DetectPartitionLayoutStage(
    PipelineStage,
):
    """
    Interpret and store the canonical Android partition layout.

    Source Discovery has already completed before this stage executes.

    The stage performs no provider scanning, workspace scanning, filesystem
    inspection, or parallel device-model synchronization.
    """

    name = "Detect Partition Layout"

    def __init__(
        self,
        *,
        detector: (
            PartitionLayoutDetectorLike
            | None
        ) = None,
    ) -> None:
        self._detector = (
            detector
            if detector is not None
            else PartitionLayoutDetector()
        )

    def execute(
        self,
        context: Context,
    ) -> None:
        try:
            layout = (
                self._detector.detect(
                    context
                )
            )
        except Exception as error:
            raise (
                PartitionLayoutStageError(
                    "Unable to detect "
                    "partition layout"
                )
            ) from error

        if not isinstance(
            layout,
            PartitionLayout,
        ):
            raise (
                PartitionLayoutStageError(
                    "Partition layout detector "
                    "returned an invalid result"
                )
            )

        context.partition_layout = layout