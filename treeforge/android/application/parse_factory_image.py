from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
from typing import Protocol

from treeforge.android.application.discover_factory_image import (
    DiscoverFactoryImageRequest,
    DiscoverFactoryImageResult,
    DiscoverFactoryImageService,
)
from treeforge.android.application.source_preparation_pipeline import (
    AndroidSourcePreparationPipeline,
)
from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
)
from treeforge.android.parsing.pipeline import (
    AndroidParsingPipeline,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)
from treeforge.android.parsing.snapshot import (
    AndroidParsingSnapshot,
)
from treeforge.android.partition import (
    PartitionLayout,
    PartitionLayoutDetector,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)
from treeforge.workspace.workspace import (
    Workspace,
)


logger = logging.getLogger(__name__)


class DiscoverFactoryImageServiceLike(
    Protocol,
):
    def discover(
        self,
        request: DiscoverFactoryImageRequest,
    ) -> DiscoverFactoryImageResult:
        ...


class PartitionLayoutDetectorLike(
    Protocol,
):
    def detect(
        self,
        context: Context,
    ) -> PartitionLayout:
        ...


class AndroidSourcePreparationPipelineLike(
    Protocol,
):
    def materialize_sources(
        self,
        context: Context,
    ) -> None:
        ...

    def continue_after_layout(
        self,
        context: Context,
    ) -> None:
        ...

    def run(
        self,
        context: Context,
    ) -> None:
        ...


class AndroidParsingPipelineLike(
    Protocol,
):
    def run(
        self,
        context: Context,
    ) -> AndroidParsingResult:
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class ParseFactoryImageRequest:
    """
    Request the canonical TreeForge pipeline through Android Parsing.
    """

    factory_image: Path
    workspace: Workspace

    device_id: str | None = None
    board_platform: str | None = None
    android_version: str | None = None
    generic_only: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.factory_image,
            Path,
        ):
            raise TypeError(
                "factory_image must be a Path"
            )

        if not isinstance(
            self.workspace,
            Workspace,
        ):
            raise TypeError(
                "workspace must be a Workspace"
            )

        if (
            self.device_id is not None
            and not isinstance(
                self.device_id,
                str,
            )
        ):
            raise TypeError(
                "device_id must be a str or None"
            )

        if (
            self.board_platform is not None
            and not isinstance(
                self.board_platform,
                str,
            )
        ):
            raise TypeError(
                "board_platform must be a str or None"
            )

        if (
            self.android_version is not None
            and not isinstance(
                self.android_version,
                str,
            )
        ):
            raise TypeError(
                "android_version must be a str or None"
            )

        if not isinstance(
            self.generic_only,
            bool,
        ):
            raise TypeError(
                "generic_only must be a bool"
            )

        if (
            self.generic_only
            and (
                self.device_id is not None
                or self.board_platform is not None
                or self.android_version is not None
            )
        ):
            raise ValueError(
                "generic_only cannot be combined with "
                "device_id, board_platform, or android_version"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParseFactoryImageResult:
    """
    Complete production result for a factory image run through Parsing.

    ``parsing`` remains the canonical result owned by the Parsing stage.

    The outer application result preserves the upstream Discovery and
    Partition Layout results so callers can inspect how TreeForge reached
    those parsed observations without duplicating their provenance.
    """

    request: ParseFactoryImageRequest
    discovery: DiscoverFactoryImageResult
    partition_layout: PartitionLayout
    parsing: AndroidParsingResult
    snapshot: AndroidParsingSnapshot

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.request,
            ParseFactoryImageRequest,
        ):
            raise TypeError(
                "request must be a ParseFactoryImageRequest"
            )

        if not isinstance(
            self.discovery,
            DiscoverFactoryImageResult,
        ):
            raise TypeError(
                "discovery must be a "
                "DiscoverFactoryImageResult"
            )

        if not isinstance(
            self.partition_layout,
            PartitionLayout,
        ):
            raise TypeError(
                "partition_layout must be a PartitionLayout"
            )

        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if not isinstance(
            self.snapshot,
            AndroidParsingSnapshot,
        ):
            raise TypeError(
                "snapshot must be an AndroidParsingSnapshot"
            )

        context = (
            self.discovery.context
        )

        if (
            context.partition_layout
            is not self.partition_layout
        ):
            raise ValueError(
                "result must preserve exact PartitionLayout identity"
            )

        if (
            context.android_parsing
            is not self.parsing
        ):
            raise ValueError(
                "result must preserve exact AndroidParsingResult identity"
            )

        if (
            self.snapshot.partition_layout
            is not self.partition_layout
        ):
            raise ValueError(
                "snapshot must preserve exact "
                "PartitionLayout identity"
            )

        if (
            self.snapshot.parsing
            is not self.parsing
        ):
            raise ValueError(
                "snapshot must preserve exact AndroidParsingResult identity"
            )

        if (
            self.snapshot.knowledge_resolution
            is not context.knowledge_resolution
        ):
            raise ValueError(
                "snapshot must preserve exact "
                "AndroidKnowledgeResolutionResult identity"
            )


class ParseFactoryImageService:
    """
    Run a real Android factory image through TreeForge's Parsing boundary.

    Production flow:

        Factory ZIP
            ↓
        Discovery
            ↓
        Knowledge enrichment
            ↓
        Partition Layout
            ↓
        Source Preparation
            ↓
        Android Parsing
            ↓
        AndroidParsingResult
            ↓
        STOP

    This service stops at canonical Parsing and does not perform
    Universe interpretation, Reconstruction, or downstream materialization.
    """

    def __init__(
        self,
        *,
        host_tools: (
            AndroidHostTools
            | None
        ) = None,
        discovery_service: (
            DiscoverFactoryImageServiceLike
            | None
        ) = None,
        layout_detector: (
            PartitionLayoutDetectorLike
            | None
        ) = None,
        source_preparation_pipeline: (
            AndroidSourcePreparationPipelineLike
            | None
        ) = None,
        parsing_pipeline: (
            AndroidParsingPipelineLike
            | None
        ) = None,
        snapshot_store: (
            AndroidParsingSnapshotStore
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.progress_callback = progress_callback

        self.host_tools = (
            host_tools
            if host_tools is not None
            else AndroidHostTools()
        )

        self.discovery_service = (
            discovery_service
            if discovery_service is not None
            else DiscoverFactoryImageService(
                progress_callback=progress_callback,
            )
        )

        self.layout_detector = (
            layout_detector
            if layout_detector is not None
            else PartitionLayoutDetector()
        )

        self.source_preparation_pipeline = (
            source_preparation_pipeline
            if source_preparation_pipeline is not None
            else AndroidSourcePreparationPipeline(
                host_tools=self.host_tools,
                progress_callback=progress_callback,
            )
        )

        self.parsing_pipeline = (
            parsing_pipeline
            if parsing_pipeline is not None
            else AndroidParsingPipeline(
                progress_callback=progress_callback,
            )
        )

        self.snapshot_store = (
            snapshot_store
            if snapshot_store is not None
            else AndroidParsingSnapshotStore()
        )

    def parse(
        self,
        request: ParseFactoryImageRequest,
    ) -> ParseFactoryImageResult:
        """
        Run one factory image through the canonical Parsing boundary.
        """

        if not isinstance(
            request,
            ParseFactoryImageRequest,
        ):
            raise TypeError(
                "request must be a ParseFactoryImageRequest"
            )

        logger.info(
            "Discovery: starting"
        )

        discovery = (
            self.discovery_service.discover(
                DiscoverFactoryImageRequest(
                    factory_image=(
                        request.factory_image
                    ),
                    workspace=(
                        request.workspace
                    ),
                    device_id=(
                        request.device_id
                    ),
                    board_platform=(
                        request.board_platform
                    ),
                    android_version=(
                        request.android_version
                    ),
                    generic_only=(
                        request.generic_only
                    ),
                )
            )
        )

        logger.info(
            "Discovery: complete"
        )

        context = (
            discovery.context
        )

        provider_collection = (
            context.provider_collection
        )

        if provider_collection is None:
            raise RuntimeError(
                "Discovery did not provide a "
                "provider collection"
            )

        logger.info(
            (
                "Discovery downstream handoff: "
                "%s input, %s forwarded, "
                "0 removed"
            ),
            len(provider_collection.artifacts),
            len(provider_collection.artifacts),
        )

        logger.info(
            "Source Materialization: starting"
        )

        self.source_preparation_pipeline.materialize_sources(
            context
        )

        logger.info(
            "Source Materialization: complete"
        )

        logger.info(
            "Partition Layout: starting"
        )

        partition_layout = (
            self.layout_detector.detect(
                context
            )
        )

        if not isinstance(
            partition_layout,
            PartitionLayout,
        ):
            raise TypeError(
                "layout detector must return a PartitionLayout"
            )

        context.partition_layout = (
            partition_layout
        )

        logger.info(
            "Partition Layout: complete"
        )

        logger.info(
            "Source Preparation: continuing after Layout"
        )

        self.source_preparation_pipeline.continue_after_layout(
            context
        )

        logger.info(
            "Source Preparation: complete"
        )
        logger.info(
            "Parsing: starting"
        )

        parsing = (
            self.parsing_pipeline.run(
                context
            )
        )

        logger.info(
            "Parsing: complete"
        )

        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "Parsing pipeline must return an "
                "AndroidParsingResult"
            )

        snapshot = AndroidParsingSnapshot(
            partition_layout=partition_layout,
            parsing=parsing,
            knowledge_resolution=(
                context.knowledge_resolution
            ),
        )

        if self.progress_callback is not None:
            self.progress_callback(
                ProgressEvent(
                    stage="Parsing Snapshot",
                    state=ProgressState.RUNNING,
                    current=0,
                    total=1,
                    detail="snapshot persistence",
                    subject="Parsing checkpoint",
                    operation=(
                        "serializing canonical Parsing object graph"
                    ),
                    item="schema 1",
                    processed=0,
                )
            )

        snapshot_path = (
            self.snapshot_store
            .save_to_workspace(
                snapshot,
                request.workspace,
            )
        )

        if self.progress_callback is not None:
            self.progress_callback(
                ProgressEvent(
                    stage="Parsing Snapshot",
                    state=ProgressState.COMPLETE,
                    current=1,
                    total=1,
                    detail="snapshot persistence",
                    subject="Parsing checkpoint",
                    operation=(
                        "canonical Parsing object graph saved"
                    ),
                    item=snapshot_path.as_posix(),
                    processed=1,
                    produced=1,
                )
            )

        logger.info(
            "Parsing snapshot: saved to %s",
            snapshot_path,
        )

        return ParseFactoryImageResult(
            request=request,
            discovery=discovery,
            partition_layout=partition_layout,
            parsing=parsing,
            snapshot=snapshot,
        )
