from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from treeforge.android.discovery import (
    AndroidDiscoveryResult,
    AndroidDiscoveryResultBuilder,
)
from treeforge.android.knowledge import (
    AndroidKnowledgeProviderEnricher,
    AndroidKnowledgeResolutionResult,
    AndroidKnowledgeResolutionService,
    AndroidKnowledgeSelection,
    DEFAULT_ANDROID_KNOWLEDGE_REGISTRY,
)
from treeforge.android.providers import (
    FactoryImageProvider,
)
from treeforge.core.config import (
    load_config,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
    KnowledgeApplicationStage,
)
from treeforge.core.progress import (
    ProgressCallback,
)
from treeforge.workspace.workspace import (
    Workspace,
)


class FactoryImageProviderLike(
    Protocol,
):
    def populate(
        self,
        context: Context,
    ) -> None:
        ...


class AndroidKnowledgeResolutionServiceLike(
    Protocol,
):
    def resolve(
        self,
        *,
        explicit: AndroidKnowledgeSelection,
        inferred,
    ) -> AndroidKnowledgeResolutionResult:
        ...


class AndroidKnowledgeProviderEnricherLike(
    Protocol,
):
    def enrich(
        self,
        *,
        collection,
        resolution: AndroidKnowledgeResolutionResult,
    ):
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class DiscoverFactoryImageRequest:
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


@dataclass(
    frozen=True,
    slots=True,
)
class DiscoverFactoryImageResult:
    """
    Complete result of one factory-image Discovery application run.

    The exact Context used during Discovery is preserved so downstream stages
    consume the canonical enriched provider collection and its original
    provenance rather than reconstructing application state.
    """

    request: DiscoverFactoryImageRequest
    discovery: AndroidDiscoveryResult
    context: Context

    knowledge_resolution: (
        AndroidKnowledgeResolutionResult
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.request,
            DiscoverFactoryImageRequest,
        ):
            raise TypeError(
                "request must be a "
                "DiscoverFactoryImageRequest"
            )

        if not isinstance(
            self.discovery,
            AndroidDiscoveryResult,
        ):
            raise TypeError(
                "discovery must be an "
                "AndroidDiscoveryResult"
            )

        if not isinstance(
            self.context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

        if (
            self.knowledge_resolution is not None
            and not isinstance(
                self.knowledge_resolution,
                AndroidKnowledgeResolutionResult,
            )
        ):
            raise TypeError(
                "knowledge_resolution must be an "
                "AndroidKnowledgeResolutionResult "
                "or None"
            )

        if (
            self.request.generic_only
            and self.knowledge_resolution is not None
        ):
            raise ValueError(
                "generic-only Discovery must not "
                "contain a knowledge resolution"
            )

        if (
            self.discovery.provider_collection
            is not self.context.provider_collection
        ):
            raise ValueError(
                "discovery and context must preserve "
                "the exact provider collection"
            )

class DiscoverFactoryImageService:
    """
    Discover Android facts directly from a factory-image ZIP.

    This service owns the standalone factory-image Discovery boundary.

    It performs exactly one provider scan.

    Default flow:

        FactoryImageProvider
            ↓
        generic AndroidDiscoveryResult
            ↓
        explicit + inferred knowledge selection
            ↓
        knowledge resolution
            ↓
        semantic enrichment of the existing provider collection
            ↓
        final AndroidDiscoveryResult

    Generic-only flow stops after generic Discovery.

    This service stops at Discovery and knowledge enrichment. It does
    not perform Partition Layout, Extraction, Parsing, Universe interpretation,
    Reconstruction, or downstream materialization.
    """

    def __init__(
        self,
        *,
        provider: (
            FactoryImageProviderLike
            | None
        ) = None,
        knowledge_resolution_service: (
            AndroidKnowledgeResolutionServiceLike
            | None
        ) = None,
        knowledge_provider_enricher: (
            AndroidKnowledgeProviderEnricherLike
            | None
        ) = None,
        knowledge_application_policy: (
            KnowledgeApplicationPolicy
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.provider = provider
        self.progress_callback = progress_callback

        self.knowledge_application_policy = (
            knowledge_application_policy
            if knowledge_application_policy is not None
            else KnowledgeApplicationPolicy()
        )

        self.knowledge_resolution_service = (
            knowledge_resolution_service
            if knowledge_resolution_service is not None
            else AndroidKnowledgeResolutionService(
                registry=(
                    DEFAULT_ANDROID_KNOWLEDGE_REGISTRY
                )
            )
        )

        self.knowledge_provider_enricher = (
            knowledge_provider_enricher
            if knowledge_provider_enricher is not None
            else AndroidKnowledgeProviderEnricher()
        )

    def discover(
        self,
        request: DiscoverFactoryImageRequest,
    ) -> DiscoverFactoryImageResult:
        if not isinstance(
            request,
            DiscoverFactoryImageRequest,
        ):
            raise TypeError(
                "request must be a "
                "DiscoverFactoryImageRequest"
            )

        request.workspace.create()

        context = Context(
            workspace=request.workspace,
            config=load_config(),
            input_path=request.factory_image,
            requested_android_version=(
                request.android_version
            ),
            knowledge_application_policy=(
                self.knowledge_application_policy
            ),
        )

        provider = (
            self.provider
            if self.provider is not None
            else FactoryImageProvider(
                progress_callback=(
                    self.progress_callback
                )
            )
        )

        provider.populate(
            context
        )

        generic_discovery = (
            AndroidDiscoveryResultBuilder()
            .build(
                context
            )
        )

        if request.generic_only:
            return DiscoverFactoryImageResult(
                request=request,
                discovery=generic_discovery,
                context=context,
            )

        knowledge_resolution = (
            self.knowledge_resolution_service
            .resolve(
                explicit=(
                    AndroidKnowledgeSelection(
                        device_id=request.device_id,
                        board_platform=(
                            request.board_platform
                        ),
                    )
                ),
                inferred=(
                    generic_discovery
                    .identity_inference
                ),
            )
        )

        context.knowledge_resolution = (
            knowledge_resolution
        )

        provider_collection = (
            context.provider_collection
        )

        if provider_collection is None:
            raise RuntimeError(
                "factory provider did not populate "
                "provider_collection"
            )

        if (
            context.knowledge_application_policy
            .enabled_for(
                KnowledgeApplicationStage.DISCOVERY
            )
        ):
            context.provider_collection = (
                self.knowledge_provider_enricher
                .enrich(
                    collection=provider_collection,
                    resolution=(
                        knowledge_resolution
                    ),
                )
            )

        final_discovery = (
            AndroidDiscoveryResultBuilder()
            .build(
                context
            )
        )

        return DiscoverFactoryImageResult(
            request=request,
            discovery=final_discovery,
            context=context,
            knowledge_resolution=(
                knowledge_resolution
            ),
        )