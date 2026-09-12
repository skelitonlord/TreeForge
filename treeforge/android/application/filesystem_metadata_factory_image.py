from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.application.discover_factory_image import (
    DiscoverFactoryImageRequest,
    DiscoverFactoryImageResult,
    DiscoverFactoryImageService,
)
from treeforge.android.extraction import (
    AndroidExtractionResult,
)
from treeforge.android.application.source_preparation_pipeline import (
    AndroidSourcePreparationPipeline,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.partition import (
    PartitionLayout,
    PartitionLayoutDetector,
)
from treeforge.android.partition.inventory import (
    PartitionInventory,
)
from treeforge.android.toolchain import (
    AndroidHostTools,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
)
from treeforge.core.progress import (
    ProgressCallback,
)
from treeforge.workspace.workspace import (
    Workspace,
)


@dataclass(
    frozen=True,
    slots=True,
)
class FilesystemMetadataFactoryImageRequest:
    """
    Request the canonical TreeForge pipeline through Filesystem Metadata.
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

        for name, value in (
            ("device_id", self.device_id),
            ("board_platform", self.board_platform),
            ("android_version", self.android_version),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{name} must be a str or None"
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
class FilesystemMetadataFactoryImageResult:
    """
    Complete canonical result through the Filesystem Metadata boundary.
    """

    request: FilesystemMetadataFactoryImageRequest
    discovery: DiscoverFactoryImageResult
    partition_layout: PartitionLayout
    extraction: AndroidExtractionResult
    partition_inventory: PartitionInventory
    filesystem_inventory: FilesystemMetadataInventory

    def __post_init__(
        self,
    ) -> None:
        context = self.discovery.context

        if (
            context.partition_layout
            is not self.partition_layout
        ):
            raise ValueError(
                "result must preserve exact PartitionLayout identity"
            )

        if (
            context.android_extraction
            is not self.extraction
        ):
            raise ValueError(
                "result must preserve exact AndroidExtractionResult identity"
            )

        if (
            context.partition_inventory
            is not self.partition_inventory
        ):
            raise ValueError(
                "result must preserve exact PartitionInventory identity"
            )

        if (
            context.filesystem_inventory
            is not self.filesystem_inventory
        ):
            raise ValueError(
                "result must preserve exact "
                "FilesystemMetadataInventory identity"
            )


class FilesystemMetadataFactoryImageService:
    """
    Run a real Android factory image through Filesystem Metadata and stop.

    Production flow:

        Factory ZIP
            ↓
        Discovery
            ↓
        Extraction source materialization
            ↓
        Partition Layout
            ↓
        post-layout Extraction
            └── PartitionInventory projection
            ↓
        Filesystem Metadata
            ↓
        FilesystemMetadataInventory
            ↓
        STOP
    """

    def __init__(
        self,
        *,
        host_tools: AndroidHostTools | None = None,
        knowledge_application_policy: (
            KnowledgeApplicationPolicy
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.host_tools = (
            host_tools
            if host_tools is not None
            else AndroidHostTools()
        )

        self.knowledge_application_policy = (
            knowledge_application_policy
            if knowledge_application_policy is not None
            else KnowledgeApplicationPolicy()
        )

        self.progress_callback = (
            progress_callback
        )

    def run(
        self,
        request: FilesystemMetadataFactoryImageRequest,
    ) -> FilesystemMetadataFactoryImageResult:
        if not isinstance(
            request,
            FilesystemMetadataFactoryImageRequest,
        ):
            raise TypeError(
                "request must be a "
                "FilesystemMetadataFactoryImageRequest"
            )

        discovery = (
            DiscoverFactoryImageService(
                progress_callback=self.progress_callback,
                knowledge_application_policy=(
                    self.knowledge_application_policy
                ),
            )
            .discover(
                DiscoverFactoryImageRequest(
                    factory_image=request.factory_image,
                    workspace=request.workspace,
                    device_id=request.device_id,
                    board_platform=request.board_platform,
                    android_version=request.android_version,
                    generic_only=request.generic_only,
                )
            )
        )

        context = (
            discovery.context
        )

        provider_collection = (
            context.provider_collection
        )

        if provider_collection is None:
            raise RuntimeError(
                "Discovery did not provide a provider collection"
            )

        source_preparation_pipeline = (
            AndroidSourcePreparationPipeline(
                host_tools=self.host_tools,
                progress_callback=self.progress_callback,
            )
        )

        source_preparation_pipeline.materialize_sources(
            context
        )

        partition_layout = (
            PartitionLayoutDetector()
            .detect(
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

        source_preparation_pipeline.continue_after_layout(
            context
        )

        extraction = (
            context.android_extraction
        )

        partition_inventory = (
            context.partition_inventory
        )

        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise RuntimeError(
                "Extraction did not publish "
                "AndroidExtractionResult"
            )

        if not isinstance(
            partition_inventory,
            PartitionInventory,
        ):
            raise RuntimeError(
                "Extraction did not publish PartitionInventory"
            )

        filesystem_inventory = (
            context.filesystem_inventory
        )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise RuntimeError(
                "Filesystem Metadata did not publish "
                "FilesystemMetadataInventory"
            )

        return FilesystemMetadataFactoryImageResult(
            request=request,
            discovery=discovery,
            partition_layout=partition_layout,
            extraction=extraction,
            partition_inventory=partition_inventory,
            filesystem_inventory=filesystem_inventory,
        )
