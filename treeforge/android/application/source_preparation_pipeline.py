from __future__ import annotations

from typing import Protocol

from treeforge.android.extraction.pipeline import (
    AndroidExtractionPipeline,
)
from treeforge.android.filesystem.backends.manager import (
    FilesystemBackendManager,
)
from treeforge.android.filesystem.detection.source import (
    FilesystemSourceDetector,
)
from treeforge.android.filesystem.metadata_stage import (
    CollectFilesystemMetadataStage,
)
from treeforge.android.partition.inventory_resolver import (
    PartitionInventoryResolver,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.pipeline.pipeline import (
    Pipeline,
)
from treeforge.core.pipeline.stage import (
    PipelineStage,
)
from treeforge.core.progress import ProgressCallback


class SourcePreparationPipelineLike(
    Protocol,
):
    """
    Pipeline contract required by AndroidSourcePreparationPipeline.
    """

    def add_stage(
        self,
        stage: PipelineStage,
    ) -> None:
        ...

    def run(
        self,
        context: Context,
    ) -> None:
        ...


class AndroidSourcePreparationPipeline:
    """
    Prepare canonical Android sources through the filesystem-metadata boundary.

    Two legitimate entry modes are supported.

    Factory-image orchestration:

        Discovery
            ↓
        Extraction source materialization
            ↓
        Partition Layout
            ↓
        post-layout Extraction
            ├── physical expansion
            └── PartitionInventory projection
            ↓
        filesystem metadata

    Existing-layout orchestration:

        established PartitionLayout
            ↓
        complete Extraction
            └── PartitionInventory projection
            ↓
        filesystem metadata

    Extraction remains the sole owner of physical materialization and
    transformation.

    Partition Layout remains a separate interpretation stage.
    """

    def __init__(
        self,
        *,
        host_tools: (
            AndroidHostTools
            | None
        ) = None,
        pipeline: (
            SourcePreparationPipelineLike
            | None
        ) = None,
        source_materialization_stage: (
            PipelineStage
            | None
        ) = None,
        partition_extraction_stage: (
            PipelineStage
            | None
        ) = None,
        recursive_extraction_stage: (
            PipelineStage
            | None
        ) = None,
        partition_inventory_resolver: (
            PartitionInventoryResolver
            | None
        ) = None,
        filesystem_metadata_stage: (
            PipelineStage
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.host_tools = (
            host_tools
            if host_tools is not None
            else AndroidHostTools()
        )

        #
        # Retained for the existing constructor contract.
        #
        # The factory-image path now has a real Partition Layout boundary
        # between source materialization and later Extraction, so one
        # uninterrupted generic Pipeline cannot represent that ordering.
        #
        self.pipeline = (
            pipeline
            if pipeline is not None
            else Pipeline()
        )

        self.extraction_pipeline = (
            AndroidExtractionPipeline(
                host_tools=self.host_tools,
                progress_callback=progress_callback,
                source_materialization_stage=(
                    source_materialization_stage
                ),
                partition_extraction_stage=(
                    partition_extraction_stage
                ),
                recursive_extraction_stage=(
                    recursive_extraction_stage
                ),
                partition_inventory_resolver=(
                    partition_inventory_resolver
                ),
            )
        )

        self.source_materialization_stage = (
            self.extraction_pipeline
            .source_materialization_stage
        )

        self.partition_extraction_stage = (
            self.extraction_pipeline
            .partition_extraction_stage
        )

        self.recursive_extraction_stage = (
            self.extraction_pipeline
            .recursive_extraction_stage
        )

        self.filesystem_metadata_stage = (
            filesystem_metadata_stage
            if filesystem_metadata_stage
            is not None
            else CollectFilesystemMetadataStage(
                manager=(
                    FilesystemBackendManager(
                        detector=FilesystemSourceDetector(),
                    )
                ),
                progress_callback=progress_callback,
            )
        )

    def materialize_sources(
        self,
        context: Context,
    ) -> None:
        """
        Establish Extraction-owned source accessibility before Layout.
        """

        self._validate_context(
            context
        )

        self.extraction_pipeline.materialize_sources(
            context
        )

    def continue_after_layout(
        self,
        context: Context,
    ) -> None:
        """
        Complete canonical preparation after Partition Layout.

        Post-layout Extraction completes physical expansion and its canonical
        PartitionInventory projection before filesystem metadata collection.
        """

        self._validate_context(
            context
        )

        self.extraction_pipeline.continue_after_layout(
            context
        )

        self.filesystem_metadata_stage.execute(
            context
        )

    def run(
        self,
        context: Context,
    ) -> None:
        """
        Run preparation for a context whose Partition Layout already exists.
        """

        self._validate_context(
            context
        )

        self.extraction_pipeline.run(
            context
        )

        self.filesystem_metadata_stage.execute(
            context
        )

    @staticmethod
    def _validate_context(
        context: Context,
    ) -> None:
        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

