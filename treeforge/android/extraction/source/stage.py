from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.extraction.result import (
    AndroidExtractionResult,
)
from treeforge.android.extraction.source.materializer import (
    SourceArtifactMaterializer,
)
from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
    ProviderArtifactKind,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.pipeline.stage import (
    PipelineStage,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


class SourceArtifactMaterializationStageError(
    RuntimeError,
):
    """
    Raised when canonical post-Discovery source artifacts cannot
    be made physically accessible before partition extraction.
    """


class SourceArtifactMaterializerLike(
    Protocol,
):
    def materialize(
        self,
        artifact: ProviderArtifact,
        *,
        source_path: Path,
        destination: Path,
    ) -> ExtractedArtifact:
        ...


class SourceArtifactMaterializationStage(
    PipelineStage,
):
    """
    Materialize canonical post-Discovery image artifacts.

    Discovery owns source identity, classification, and provenance.

    This Extraction stage consumes the canonical ProviderCollection directly
    and establishes physical accessibility for discovered image artifacts
    before Partition Layout interpretation.

    It:

    - consumes exact ProviderArtifact identities from Discovery;
    - materializes discovered image artifacts when required;
    - preserves exact ProviderArtifact identity and provenance;
    - stores canonical ExtractedArtifact state;
    - never depends on PartitionLayout;
    - never mutates ProviderArtifact;
    - never performs partition interpretation;
    - never builds PartitionInventory;
    - never inspects filesystems.

    Later stages may consume this canonical Extraction state without moving
    physical materialization responsibility out of Extraction.
    """

    name = "Materialize Source Artifacts"

    OUTPUT_DIRECTORY_NAME = "sources"

    def __init__(
        self,
        *,
        materializer: (
            SourceArtifactMaterializerLike
            | None
        ) = None,
        progress_callback: (
            ProgressCallback
            | None
        ) = None,
    ) -> None:
        self._materializer = (
            materializer
            if materializer is not None
            else SourceArtifactMaterializer()
        )
        self._progress_callback = progress_callback

    def execute(
        self,
        context: Context,
    ) -> None:
        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

        collection = context.provider_collection

        if collection is None:
            raise SourceArtifactMaterializationStageError(
                "Provider collection has not been established"
            )

        existing = (
            context.android_extraction
            if context.android_extraction is not None
            else AndroidExtractionResult()
        )

        if not isinstance(
            existing,
            AndroidExtractionResult,
        ):
            raise SourceArtifactMaterializationStageError(
                "context extraction result is invalid"
            )

        artifacts = list(
            existing.artifacts
        )

        by_source_identity: dict[
            int,
            ExtractedArtifact,
        ] = {}

        by_path: dict[
            Path,
            ExtractedArtifact,
        ] = {}

        for extracted in artifacts:
            by_path[extracted.path] = extracted

            if extracted.source is not None:
                by_source_identity[
                    id(extracted.source)
                ] = extracted

        discovered = []

        for result in collection:
            for artifact in result.artifact_inventory:
                if (
                    artifact.kind
                    is not ProviderArtifactKind.IMAGE
                ):
                    continue

                discovered.append(
                    artifact
                )

        discovered.sort(
            key=lambda artifact: (
                artifact.classification.value,
                artifact.source_name,
                artifact.name,
            )
        )

        materialization_root = (
            context.workspace.root
            / "images"
            / self.OUTPUT_DIRECTORY_NAME
        )

        total = len(
            discovered
        )

        for current, provider_artifact in enumerate(
            discovered,
            start=1,
        ):
            self._report_progress(
                state=ProgressState.RUNNING,
                current=current - 1,
                total=total,
                artifact=provider_artifact,
                operation="preparing discovered image source",
                item=provider_artifact.name,
            )

            canonical = (
                self._materialize_source(
                    context=context,
                    provider_artifact=provider_artifact,
                    materialization_root=materialization_root,
                    artifacts=artifacts,
                    by_source_identity=by_source_identity,
                    by_path=by_path,
                )
            )

            self._report_progress(
                state=ProgressState.COMPLETE,
                current=current,
                total=total,
                artifact=provider_artifact,
                operation=self._operation_label(
                    canonical.operation
                ),
                output_size_bytes=canonical.size_bytes,
                item=provider_artifact.name,
            )

        context.android_extraction = (
            AndroidExtractionResult(
                artifacts=tuple(
                    artifacts
                ),
                cpio_extractions=(
                    existing.cpio_extractions
                ),
            )
        )

    def _report_progress(
        self,
        *,
        state: ProgressState,
        current: int,
        total: int,
        artifact: ProviderArtifact,
        operation: str = "preparing discovered image source",
        output_size_bytes: int | None = None,
        item: str | None = None,
    ) -> None:
        if self._progress_callback is None:
            return

        detail = (
            artifact.classification.value
            if (
                artifact.classification
                is not ProviderArtifactClassification.UNKNOWN
            )
            else artifact.name
        )

        self._progress_callback(
            ProgressEvent(
                stage=self.name,
                state=state,
                current=current,
                total=total,
                detail=detail,
                subject=detail,
                operation=operation,
                item=(
                    item
                    if item is not None
                    else artifact.source_name
                ),
                processed=current,
                output_size_bytes=output_size_bytes,
            )
        )

    @staticmethod
    def _operation_label(
        operation: ExtractionOperation,
    ) -> str:
        """
        Return concise live wording for a completed source operation.
        """

        labels = {
            ExtractionOperation.SOURCE_ADOPTION:
                "adopted existing image source",
            ExtractionOperation.SOURCE_MATERIALIZATION:
                "materialized image source",
            ExtractionOperation.ARCHIVE_MEMBER_EXTRACTION:
                "extracted image from factory archive",
        }

        return labels.get(
            operation,
            operation.value.replace(
                "_",
                " ",
            ),
        )

    def _materialize_source(
        self,
        *,
        context: Context,
        provider_artifact: ProviderArtifact,
        materialization_root: Path,
        artifacts: list[
            ExtractedArtifact
        ],
        by_source_identity: dict[
            int,
            ExtractedArtifact,
        ],
        by_path: dict[
            Path,
            ExtractedArtifact,
        ],
    ) -> ExtractedArtifact:
        canonical = (
            by_source_identity.get(
                id(provider_artifact)
            )
        )

        if canonical is not None:
            return canonical

        source_path = (
            self._provider_source_path(
                context,
                provider_artifact,
            )
        )

        destination = (
            materialization_root
            / self._destination_name(
                provider_artifact
            )
        )

        canonical = (
            self._materializer.materialize(
                provider_artifact,
                source_path=source_path,
                destination=destination,
            )
        )

        if canonical.source is not provider_artifact:
            raise SourceArtifactMaterializationStageError(
                "source materializer did not preserve exact "
                "ProviderArtifact identity for "
                f"{provider_artifact.source_name}"
            )

        if canonical.path in by_path:
            raise SourceArtifactMaterializationStageError(
                "multiple canonical extraction artifacts "
                "cannot own the same physical path: "
                f"{canonical.path}"
            )

        semantic_name = (
            self._semantic_name(
                provider_artifact
            )
        )

        if semantic_name is not None:
            canonical = replace(
                canonical,
                semantic_name=semantic_name,
            )

        artifacts.append(
            canonical
        )

        by_source_identity[
            id(provider_artifact)
        ] = canonical

        by_path[
            canonical.path
        ] = canonical

        return canonical

    @staticmethod
    def _semantic_name(
        artifact: ProviderArtifact,
    ) -> str | None:
        classification = artifact.classification

        if (
            classification
            is not ProviderArtifactClassification.UNKNOWN
        ):
            return classification.value

        #
        # Semantic classification and canonical source identity are separate
        # concerns.
        #
        # Discovery may structurally establish that an artifact is an image
        # while intentionally leaving its Android semantic role UNKNOWN.
        # Such an artifact still has an exact factory-supplied image identity
        # that Extraction must preserve for downstream filesystem lineage.
        #
        # Using the basename stem does not promote the image into a known
        # partition/classification family; UNKNOWN remains authoritative.
        #
        if (
            artifact.kind
            is ProviderArtifactKind.IMAGE
        ):
            name = Path(
                artifact.name
            )

            if (
                name.suffix.lower()
                == ".img"
                and name.stem
            ):
                return name.stem

        return None

    @classmethod
    def _destination_name(
        cls,
        artifact: ProviderArtifact,
    ) -> str:
        digest = (
            sha256(
                artifact.source_name.encode(
                    "utf-8"
                )
            )
            .hexdigest()[:16]
        )

        basename = Path(
            artifact.name
        ).name

        if not basename:
            basename = "artifact"

        return (
            f"{digest}-{basename}"
        )

    @staticmethod
    def _provider_source_path(
        context: Context,
        artifact: ProviderArtifact,
    ) -> Path:
        collection = context.provider_collection

        if collection is None:
            raise SourceArtifactMaterializationStageError(
                "Provider collection has not been established"
            )

        result = collection.result_for(
            artifact.provider_id
        )

        if result is None:
            raise SourceArtifactMaterializationStageError(
                "provider collection does not contain "
                "the artifact provider: "
                f"{artifact.provider_id}"
            )

        source_identity = result.source_identity

        if source_identity is None:
            raise SourceArtifactMaterializationStageError(
                "provider result does not preserve "
                "physical source identity for "
                f"{artifact.provider_id}"
            )

        source_path = source_identity.path

        if not isinstance(
            source_path,
            Path,
        ):
            raise SourceArtifactMaterializationStageError(
                "provider source identity does not "
                "contain a pathlib.Path"
            )

        if not source_path.exists():
            raise SourceArtifactMaterializationStageError(
                "provider source no longer exists: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise SourceArtifactMaterializationStageError(
                "provider source is not a regular file: "
                f"{source_path}"
            )

        return source_path

