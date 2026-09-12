from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Protocol

from treeforge.android.extraction.partition.extractor import (
    LogicalPartitionExtractor,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
)
from treeforge.android.extraction.result import (
    AndroidExtractionResult,
)
from treeforge.android.partition.layout import (
    LayoutPartition,
    PartitionLayout,
    PartitionOrigin,
    PartitionPayloadState,
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


class PartitionImageExtractionError(
    RuntimeError,
):
    """
    Raised when post-layout partition images cannot be made accessible.
    """


class LogicalPartitionExtractorLike(
    Protocol,
):
    def extract(
        self,
        parent: ExtractedArtifact,
        partition_names: tuple[
            str,
            ...,
        ],
        output_directory: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        ...


class PartitionImageExtractionStage(
    PipelineStage,
):
    """
    Establish canonical accessible partition-image artifacts after Layout.

    Source-artifact materialization must already have established canonical
    accessible source artifacts in Extraction state.

    Standalone partitions consume those canonical artifacts directly.

    Logical partitions are extracted from the canonical materialized parent
    source identified by exact ProviderArtifact provenance.

    Existing extraction state is preserved and extended rather than replaced.

    This stage does not build PartitionInventory and does not inspect
    filesystems.
    """

    name = "Extract Partition Images"

    OUTPUT_DIRECTORY_NAME = (
        "partitions"
    )

    def __init__(
        self,
        *,
        logical_extractor: (
            LogicalPartitionExtractorLike
            | None
        ) = None,
        progress_callback: (
            ProgressCallback
            | None
        ) = None,
    ) -> None:
        self._logical_extractor = (
            logical_extractor
            if logical_extractor
            is not None
            else LogicalPartitionExtractor()
        )

        self._progress_callback = (
            progress_callback
        )

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

        layout = (
            context.partition_layout
        )

        if layout is None:
            raise PartitionImageExtractionError(
                "Partition layout has not been established"
            )

        if not isinstance(
            layout,
            PartitionLayout,
        ):
            raise PartitionImageExtractionError(
                "context partition layout is invalid"
            )

        existing = (
            context.android_extraction
            if context.android_extraction
            is not None
            else AndroidExtractionResult()
        )

        if not isinstance(
            existing,
            AndroidExtractionResult,
        ):
            raise PartitionImageExtractionError(
                "context extraction result is invalid"
            )

        artifacts: list[
            ExtractedArtifact
        ] = list(
            existing.artifacts
        )

        by_path: dict[
            Path,
            ExtractedArtifact,
        ] = {
            artifact.path: artifact
            for artifact
            in artifacts
        }

        unresolved_logical: list[
            LayoutPartition
        ] = []

        partitions = (
            layout.partitions
        )

        total = len(
            partitions
        )

        completed = 0

        for partition in (
            partitions
        ):
            if (
                partition.origin
                is PartitionOrigin.STANDALONE
            ):
                source_artifact = (
                    self._require_partition_source(
                        partition
                    )
                )

                self._report_progress(
                    state=ProgressState.RUNNING,
                    current=completed,
                    total=total,
                    detail=partition.name,
                    operation=(
                        "locating materialized partition image"
                    ),
                    item=source_artifact.source_name,
                )

                materialized_source = self._require_materialized_source(
                    partition=partition,
                    extraction=existing,
                )

                completed += 1

                self._report_progress(
                    state=ProgressState.COMPLETE,
                    current=completed,
                    total=total,
                    detail=partition.name,
                    operation=(
                        "using standalone partition image"
                    ),
                    item=materialized_source.path.as_posix(),
                    output_size_bytes=materialized_source.size_bytes,
                )

                continue

            if (
                partition.origin
                is PartitionOrigin.SUPER
            ):
                if (
                    partition.payload_state
                    is PartitionPayloadState.UNAVAILABLE
                ):
                    completed += 1

                    self._report_progress(
                        state=ProgressState.COMPLETE,
                        current=completed,
                        total=total,
                        detail=partition.name,
                        operation=(
                            "logical partition topology only; "
                            "payload unavailable"
                        ),
                        item=(
                            partition.source.artifact.source_name
                            if partition.source is not None
                            else None
                        ),
                    )

                    continue

                unresolved_logical.append(
                    partition
                )

                continue

            raise PartitionImageExtractionError(
                "unsupported partition origin: "
                f"{partition.name}: "
                f"{partition.origin}"
            )

        groups = (
            self._group_logical_partitions(
                tuple(
                    unresolved_logical
                ),
            )
        )

        output_directory = (
            context.workspace.root
            / "images"
            / self.OUTPUT_DIRECTORY_NAME
        )

        for (
            source_artifact,
            partitions,
        ) in groups.items():
            parent = (
                self._require_materialized_source_artifact(
                    source_artifact=source_artifact,
                    partitions=partitions,
                    extraction=existing,
                )
            )

            partition_names = tuple(
                partition.name
                for partition
                in partitions
            )

            if partition_names:
                self._report_progress(
                    state=ProgressState.RUNNING,
                    current=completed,
                    total=total,
                    detail=partition_names[0],
                    operation=(
                        "unpacking logical partition"
                    ),
                    item=parent.path.as_posix(),
                )

            extracted = (
                self._logical_extractor.extract(
                    parent,
                    partition_names,
                    output_directory,
                )
            )

            if not isinstance(
                extracted,
                tuple,
            ):
                raise PartitionImageExtractionError(
                    "logical extractor must return a tuple"
                )

            if (
                len(extracted)
                != len(partition_names)
            ):
                raise PartitionImageExtractionError(
                    "logical extractor did not return "
                    "one artifact per requested partition"
                )

            returned_names = tuple(
                artifact.semantic_name
                for artifact
                in extracted
            )

            if (
                returned_names
                != partition_names
            ):
                raise PartitionImageExtractionError(
                    "logical extractor did not preserve "
                    "requested partition ordering and identity"
                )

            for index, artifact in enumerate(
                extracted
            ):
                self._append_unique_artifact(
                    artifact,
                    artifacts=artifacts,
                    by_path=by_path,
                )

                completed += 1

                detail = (
                    artifact.semantic_name
                    or artifact.path.name
                )

                self._report_progress(
                    state=ProgressState.COMPLETE,
                    current=completed,
                    total=total,
                    detail=detail,
                    operation=(
                        "logical partition image ready"
                    ),
                    item=artifact.path.as_posix(),
                    output_size_bytes=artifact.size_bytes,
                )

                if index + 1 < len(extracted):
                    next_artifact = (
                        extracted[
                            index + 1
                        ]
                    )

                    self._report_progress(
                        state=ProgressState.RUNNING,
                        current=completed,
                        total=total,
                        detail=(
                            next_artifact.semantic_name
                            or next_artifact.path.name
                        ),
                        operation=(
                            "unpacking logical partition"
                        ),
                        item=parent.path.as_posix(),
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
        detail: str,
        operation: str = "resolving partition image",
        item: str | None = None,
        input_size_bytes: int | None = None,
        output_size_bytes: int | None = None,
        produced: int | None = None,
    ) -> None:
        if self._progress_callback is None:
            return

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
                    else detail
                ),
                processed=current,
                input_size_bytes=input_size_bytes,
                output_size_bytes=output_size_bytes,
                produced=produced,
            )
        )

    @staticmethod
    def _require_partition_source(
        partition: LayoutPartition,
    ):
        source = (
            partition.source
        )

        if source is None:
            raise PartitionImageExtractionError(
                "partition has no canonical source provenance: "
                f"{partition.name}"
            )

        return source.artifact

    @classmethod
    def _require_materialized_source(
        cls,
        *,
        partition: LayoutPartition,
        extraction: AndroidExtractionResult,
    ) -> ExtractedArtifact:
        source_artifact = (
            cls._require_partition_source(
                partition
            )
        )

        candidates = (
            extraction.artifacts_for_source(
                source_artifact
            )
        )

        candidates = tuple(
            artifact
            for artifact
            in candidates
            if (
                artifact.semantic_name
                == partition.name
                and artifact.operation
                in (
                    ExtractionOperation
                    .SOURCE_ADOPTION,
                    ExtractionOperation
                    .ARCHIVE_MEMBER_EXTRACTION,
                )
            )
        )

        if not candidates:
            raise PartitionImageExtractionError(
                "standalone partition has not been "
                "materialized by source extraction: "
                f"{partition.name}"
            )

        if len(candidates) != 1:
            raise PartitionImageExtractionError(
                "standalone partition has ambiguous "
                "source materialization state: "
                f"{partition.name}"
            )

        artifact = (
            candidates[0]
        )

        cls._validate_source_identity(
            partition,
            artifact,
        )

        cls._validate_image(
            artifact.path,
            partition_name=partition.name,
        )

        return artifact

    @classmethod
    def _require_materialized_source_artifact(
        cls,
        *,
        source_artifact,
        partitions: tuple[
            LayoutPartition,
            ...,
        ],
        extraction: AndroidExtractionResult,
    ) -> ExtractedArtifact:
        candidates = (
            extraction.artifacts_for_source(
                source_artifact
            )
        )

        candidates = tuple(
            artifact
            for artifact
            in candidates
            if artifact.operation
            in (
                ExtractionOperation
                .SOURCE_ADOPTION,
                ExtractionOperation
                .ARCHIVE_MEMBER_EXTRACTION,
            )
        )

        if not candidates:
            raise PartitionImageExtractionError(
                "logical partition source has not been "
                "materialized by source extraction: "
                f"{partitions[0].name}"
            )

        if len(candidates) != 1:
            raise PartitionImageExtractionError(
                "logical partition source has ambiguous "
                "materialization state: "
                f"{partitions[0].name}"
            )

        parent = (
            candidates[0]
        )

        for partition in partitions:
            cls._validate_source_identity(
                partition,
                parent,
            )

        cls._validate_image(
            parent.path,
            partition_name=(
                partitions[0].name
            ),
        )

        return parent

    @classmethod
    def _group_logical_partitions(
        cls,
        partitions: tuple[
            LayoutPartition,
            ...,
        ],
    ) -> OrderedDict[
        object,
        tuple[
            LayoutPartition,
            ...,
        ],
    ]:
        grouped: OrderedDict[
            object,
            list[
                LayoutPartition
            ],
        ] = OrderedDict()

        for partition in partitions:
            if (
                partition.origin
                is not PartitionOrigin.SUPER
            ):
                raise PartitionImageExtractionError(
                    "partition is not a logical "
                    "super partition: "
                    f"{partition.name}"
                )

            source_artifact = (
                cls._require_partition_source(
                    partition
                )
            )

            grouped.setdefault(
                source_artifact,
                [],
            ).append(
                partition
            )

        return OrderedDict(
            (
                source_artifact,
                tuple(
                    source_partitions
                ),
            )
            for (
                source_artifact,
                source_partitions,
            ) in grouped.items()
        )

    @staticmethod
    def _validate_image(
        image: Path,
        *,
        partition_name: str,
    ) -> Path:
        if not isinstance(
            image,
            Path,
        ):
            raise TypeError(
                "partition image must be a pathlib.Path: "
                f"{partition_name}"
            )

        if not image.exists():
            raise PartitionImageExtractionError(
                "partition image does not exist for "
                f"{partition_name}: {image}"
            )

        if image.is_dir():
            raise PartitionImageExtractionError(
                "partition image cannot be a directory for "
                f"{partition_name}: {image}"
            )

        if not image.is_file():
            raise PartitionImageExtractionError(
                "partition image must be a regular file for "
                f"{partition_name}: {image}"
            )

        return image

    @staticmethod
    def _validate_source_identity(
        partition: LayoutPartition,
        artifact: ExtractedArtifact,
    ) -> None:
        expected = (
            partition.source.artifact
            if partition.source is not None
            else None
        )

        if artifact.source is not expected:
            raise PartitionImageExtractionError(
                "extraction artifact must preserve exact "
                "partition ProviderArtifact identity for "
                f"{partition.name}"
            )

    @staticmethod
    def _append_unique_artifact(
        artifact: ExtractedArtifact,
        *,
        artifacts: list[
            ExtractedArtifact
        ],
        by_path: dict[
            Path,
            ExtractedArtifact,
        ],
    ) -> None:
        existing = (
            by_path.get(
                artifact.path
            )
        )

        if existing is not None:
            if existing is artifact:
                return

            raise PartitionImageExtractionError(
                "multiple canonical extraction artifacts "
                "cannot own the same physical path: "
                f"{artifact.path}"
            )

        artifacts.append(
            artifact
        )

        by_path[
            artifact.path
        ] = artifact