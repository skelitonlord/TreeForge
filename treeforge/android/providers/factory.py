from __future__ import annotations

from pathlib import Path

from treeforge.android.providers.archive_scanner import (
    ProviderArchiveScanner,
)
from treeforge.android.providers.artifact_enricher import (
    ProviderArtifactSemanticEnricher,
)
from treeforge.android.providers.base import (
    Provider,
    ProviderCapability,
)
from treeforge.android.providers.collection import (
    ProviderCollection,
)
from treeforge.android.providers.generic_android_semantic_rule import (
    GenericAndroidArtifactSemanticRule,
)
from treeforge.android.providers.source_identity import (
    ProviderSourceIdentity,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.progress import (
    ProgressCallback,
)
from treeforge.workspace.source_service import (
    WorkspaceSourceService,
)


class FactoryImageProvider(
    Provider,
):
    """
    Discover every artifact reachable from one factory-image ZIP source.

    FactoryImageProvider owns generic factory-source Discovery only.

    Discovery is exhaustive and structural:

    - every regular root ZIP member is inventoried;
    - every structurally valid nested ZIP is recursively inventoried;
    - nested archives do not depend on filenames or extensions;
    - unknown artifacts remain first-class inventory entries;
    - semantic classification never controls whether an artifact is discovered.

    After structural Discovery, the provider applies only generic Android
    artifact semantics.

    OEM-, platform-, device-, and Android-version-specific knowledge is not
    resolved or applied by this provider. That specialization belongs to the
    post-Discovery application knowledge handoff.

    Extraction, persistent materialization, filesystem handling, parsing,
    partition interpretation, and Android build analysis belong to later
    TreeForge stages.
    """

    provider_id = "factory-image"

    name = "Factory Image"

    description = (
        "Recursively discovers every artifact "
        "reachable from a factory-image ZIP."
    )

    version = "3.0"

    source_type = (
        ProviderSourceType.FACTORY_IMAGE
    )

    capabilities = (
        ProviderCapability.ARTIFACT_DISCOVERY,
    )

    def __init__(
        self,
        *,
        archive_scanner: (
            ProviderArchiveScanner
            | None
        ) = None,
        artifact_enricher: (
            ProviderArtifactSemanticEnricher
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.progress_callback = (
            progress_callback
        )

        self.archive_scanner = (
            archive_scanner
            if archive_scanner is not None
            else ProviderArchiveScanner(
                progress_callback=progress_callback,
                progress_stage="Discover Factory Image",
            )
        )

        if not isinstance(
            self.archive_scanner,
            ProviderArchiveScanner,
        ):
            raise TypeError(
                "archive_scanner must be a "
                "ProviderArchiveScanner"
            )

        if (
            artifact_enricher is not None
            and not isinstance(
                artifact_enricher,
                ProviderArtifactSemanticEnricher,
            )
        ):
            raise TypeError(
                "artifact_enricher must be a "
                "ProviderArtifactSemanticEnricher "
                "or None"
            )

        self.artifact_enricher = (
            artifact_enricher
        )

    def populate(
        self,
        context: Context,
    ) -> None:
        """
        Discover the configured factory package using generic semantics only.

        Provider execution performs:

            source validation
                ->
            exhaustive archive discovery
                ->
            generic Android semantic enrichment
                ->
            canonical provider collection

        No installed device/platform/OEM/version knowledge is resolved here.
        """

        path = self._validate_input(
            context
        )

        source_identity = (
            ProviderSourceIdentity.from_path(
                path,
                provider_id=self.provider_id,
                source_type=self.source_type,
                progress_callback=(
                    self.progress_callback
                ),
                progress_stage=(
                    "Discover Factory Image"
                ),
                progress_subject=(
                    "factory image"
                ),
            )
        )

        discovered_inventory = (
            self.archive_scanner.scan(
                path,
                provider_id=self.provider_id,
                source_type=self.source_type,
                parent_source_name=path.name,
            )
        )

        artifact_inventory = (
            self._semantic_enricher()
            .enrich_inventory(
                discovered_inventory
            )
        )

        provider_result = (
            self.create_result(
                artifact_inventory=(
                    artifact_inventory
                ),
                source_identity=(
                    source_identity
                ),
            )
        )

        context.provider_collection = (
            ProviderCollection(
                results=(
                    provider_result,
                ),
            )
        )

        WorkspaceSourceService(
            context.workspace
        ).save_current(
            source_identity
        )

    def _semantic_enricher(
        self,
    ) -> ProviderArtifactSemanticEnricher:
        """
        Return the generic provider semantic enricher.

        An explicitly injected enricher remains supported for focused provider
        tests and alternate generic provider strategies.

        Installed Android knowledge modules are intentionally not consulted.
        """

        if self.artifact_enricher is not None:
            return self.artifact_enricher

        return ProviderArtifactSemanticEnricher(
            rules=(
                GenericAndroidArtifactSemanticRule(),
            )
        )

    @staticmethod
    def _validate_input(
        context: Context,
    ) -> Path:
        """
        Validate and return the physical factory-source path.

        Archive validity itself belongs to ProviderArchiveScanner.
        """

        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

        if context.input_path is None:
            raise ValueError(
                "No factory image specified."
            )

        path = Path(
            context.input_path
        ).expanduser()

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if path.is_dir():
            raise ValueError(
                "Factory image source must be a file."
            )

        return path