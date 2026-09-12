from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from treeforge.android.extraction.cpio.extractor import (
    CpioExtractionResult,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
)
from treeforge.android.extraction.result import (
    AndroidExtractionResult,
)
from treeforge.android.filesystem.backends.manager import (
    FilesystemBackendResult,
    FilesystemSourceType,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
    FilesystemMetadataInventoryEntry,
)
from treeforge.android.filesystem.metadata.builder import (
    MetadataEntryProgressCallback,
)
from treeforge.android.filesystem.metadata.cpio import (
    CpioFilesystemMetadataNormalizer,
)
from treeforge.android.filesystem.partition_selector import (
    FilesystemPartitionSelection,
    FilesystemPartitionSelector,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
    PartitionInventory,
)
from treeforge.core.context.context import Context
from treeforge.core.pipeline.stage import PipelineStage
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


class FilesystemMetadataCollectionStageError(
    RuntimeError
):
    """
    Raised when canonical filesystem metadata cannot be collected.
    """


class FilesystemBackendManagerLike(
    Protocol
):
    """
    Backend-manager contract required by filesystem metadata collection.
    """

    def collect_metadata(
        self,
        artifact: ExtractedArtifact,
        *,
        metadata_source: ExtractedArtifact | None = None,
        partition: InventoryPartition | None = None,
        root: str = "/",
        include_root: bool = True,
        max_depth: int | None = None,
        progress_callback: (
            MetadataEntryProgressCallback
            | None
        ) = None,
    ) -> FilesystemBackendResult:
        ...


class FilesystemPartitionSelectorLike(
    Protocol,
):
    def select(
        self,
        inventory: PartitionInventory,
    ) -> FilesystemPartitionSelection:
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class _FilesystemMetadataWorkItem:
    """
    One canonical physical filesystem whose metadata must be normalized.
    """

    artifact: ExtractedArtifact
    partition: InventoryPartition | None = None
    metadata_source: ExtractedArtifact | None = None
    cpio_extraction: CpioExtractionResult | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            self.artifact.kind
            is not ExtractionArtifactKind.DIRECTORY
        ):
            raise ValueError(
                "canonical filesystem artifact must be a directory"
            )

        if (
            self.partition is not None
            and not isinstance(
                self.partition,
                InventoryPartition,
            )
        ):
            raise TypeError(
                "partition must be an InventoryPartition or None"
            )

        if (
            self.metadata_source is not None
            and not isinstance(
                self.metadata_source,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "metadata_source must be an ExtractedArtifact or None"
            )

        if (
            self.cpio_extraction is not None
            and not isinstance(
                self.cpio_extraction,
                CpioExtractionResult,
            )
        ):
            raise TypeError(
                "cpio_extraction must be a CpioExtractionResult or None"
            )

        if (
            self.cpio_extraction is not None
            and self.cpio_extraction.artifact
            is not self.artifact
        ):
            raise ValueError(
                "CPIO work item must preserve exact artifact identity"
            )

        if (
            self.metadata_source is not None
            and self.cpio_extraction is not None
        ):
            raise ValueError(
                "work item cannot contain both image metadata source "
                "and CPIO metadata evidence"
            )


class CollectFilesystemMetadataStage(
    PipelineStage
):
    """
    Normalize metadata for canonical materialized Android filesystems.

    Filesystem identity comes from exact Extraction directory artifacts.

    Intrinsic metadata comes from authoritative upstream evidence:
    - filesystem-image parents for FILESYSTEM_EXTRACTION directories;
    - CpioNewcEntry records for CPIO_EXTRACTION directories.

    Host-directory stat information is never promoted as Android filesystem
    metadata.
    """

    name = "Collect Filesystem Metadata"

    def __init__(
        self,
        *,
        manager: FilesystemBackendManagerLike,
        selector: (
            FilesystemPartitionSelectorLike
            | None
        ) = None,
        root: str = "/",
        include_root: bool = True,
        max_depth: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self._manager = manager

        self._selector = (
            selector
            if selector is not None
            else FilesystemPartitionSelector()
        )

        self._cpio_normalizer = (
            CpioFilesystemMetadataNormalizer()
        )

        self._root = root
        self._include_root = include_root
        self._max_depth = max_depth
        self._progress_callback = progress_callback

    def execute(
        self,
        context: Context,
    ) -> None:
        extraction = (
            context.android_extraction
        )

        if extraction is None:
            raise FilesystemMetadataCollectionStageError(
                "Android Extraction has not completed"
            )

        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise FilesystemMetadataCollectionStageError(
                "context.android_extraction must be an "
                "AndroidExtractionResult"
            )

        inventory = (
            context.partition_inventory
        )

        if inventory is None:
            raise FilesystemMetadataCollectionStageError(
                "Partition inventory has not been resolved"
            )

        self._validate_inventory(
            inventory
        )

        selection = self._selector.select(
            inventory
        )

        if not isinstance(
            selection,
            FilesystemPartitionSelection,
        ):
            raise FilesystemMetadataCollectionStageError(
                "filesystem partition selector must return "
                "a FilesystemPartitionSelection"
            )

        self._validate_selection_coverage(
            inventory=inventory,
            selection=selection,
        )

        work_items = self._build_work_items(
            extraction=extraction,
            inventory=inventory,
            selection=selection,
        )

        self._validate_work_item_coverage(
            extraction=extraction,
            work_items=work_items,
        )

        total = len(
            work_items
        )

        self._report_progress(
            ProgressEvent(
                stage="Filesystem Metadata",
                state=ProgressState.STARTING,
                current=0,
                total=total,
                subject="canonical filesystems",
                operation=(
                    "normalizing filesystem metadata"
                ),
                item=(
                    self._work_item_label(
                        work_items[0]
                    )
                    if work_items
                    else None
                ),
                processed=0,
            )
        )

        collected: list[
            FilesystemMetadataInventoryEntry
        ] = []

        total_metadata_entries = 0

        for index, item in enumerate(
            work_items,
            start=1,
        ):
            label = (
                self._work_item_label(
                    item
                )
            )

            self._report_progress(
                ProgressEvent(
                    stage="Filesystem Metadata",
                    state=ProgressState.RUNNING,
                    current=index - 1,
                    total=total,
                    detail=label,
                    subject=label,
                    operation=(
                        "normalizing filesystem metadata"
                    ),
                    item=item.artifact.path.as_posix(),
                    processed=0,
                )
            )

            try:
                result = (
                    self._collect_work_item(
                        item=item,
                        current=index - 1,
                        total=total,
                    )
                )
            except Exception as error:
                raise FilesystemMetadataCollectionStageError(
                    "Unable to collect filesystem metadata for "
                    f"{label}: {item.artifact.path}"
                ) from error

            if not isinstance(
                result,
                FilesystemBackendResult,
            ):
                raise FilesystemMetadataCollectionStageError(
                    "Filesystem metadata collection returned "
                    f"an invalid result for {label}"
                )

            if result.artifact is not item.artifact:
                raise FilesystemMetadataCollectionStageError(
                    "Filesystem metadata result does not preserve "
                    f"exact Extraction artifact identity for {label}"
                )

            if result.partition is not item.partition:
                raise FilesystemMetadataCollectionStageError(
                    "Filesystem metadata result does not preserve "
                    f"partition context for {label}"
                )

            entry_count = len(
                result.metadata.entries
            )

            total_metadata_entries += (
                entry_count
            )

            collected.append(
                FilesystemMetadataInventoryEntry(
                    result=result,
                )
            )

            self._report_progress(
                ProgressEvent(
                    stage="Filesystem Metadata",
                    state=ProgressState.RUNNING,
                    current=index,
                    total=total,
                    detail=label,
                    subject=label,
                    operation=(
                        "normalizing filesystem metadata"
                    ),
                    item=item.artifact.path.as_posix(),
                    processed=entry_count,
                )
            )

        context.filesystem_inventory = (
            FilesystemMetadataInventory(
                entries=tuple(
                    collected
                )
            )
        )

        self._report_progress(
            ProgressEvent(
                stage="Filesystem Metadata",
                state=ProgressState.COMPLETE,
                current=total,
                total=total,
                subject="Canonical filesystem inventory",
                operation=(
                    "completed canonical filesystem metadata collection"
                ),
                item=(
                    f"{total} filesystem roots / "
                    f"{total_metadata_entries} metadata entries"
                ),
                processed=total_metadata_entries,
                produced=total,
            )
        )

    def _build_work_items(
        self,
        *,
        extraction: AndroidExtractionResult,
        inventory: PartitionInventory,
        selection: FilesystemPartitionSelection,
    ) -> tuple[
        _FilesystemMetadataWorkItem,
        ...,
    ]:
        work_items: list[
            _FilesystemMetadataWorkItem
        ] = []

        seen_artifacts: set[
            int
        ] = set()

        #
        # Partition filesystems.
        #
        # The partition image remains authoritative metadata evidence.
        # The FILESYSTEM_EXTRACTION child is the canonical filesystem
        # identity shared with Parsing.
        #
        for partition in (
            selection.inventory.partitions
        ):
            filesystem_artifact = (
                extraction.child_of(
                    partition.artifact,
                    operation=(
                        ExtractionOperation
                        .FILESYSTEM_EXTRACTION
                    ),
                )
            )

            if filesystem_artifact is None:
                raise FilesystemMetadataCollectionStageError(
                    "Filesystem-capable partition has no canonical "
                    "FILESYSTEM_EXTRACTION child: "
                    f"{partition.name}"
                )

            self._validate_filesystem_artifact(
                filesystem_artifact
            )

            work_items.append(
                _FilesystemMetadataWorkItem(
                    artifact=filesystem_artifact,
                    partition=partition,
                    metadata_source=partition.artifact,
                )
            )

            seen_artifacts.add(
                id(
                    filesystem_artifact
                )
            )

        #
        # Ramdisk / CPIO filesystems.
        #
        # CpioExtractionResult contains the authoritative intrinsic metadata.
        #
        for cpio_extraction in (
            extraction.cpio_extractions
        ):
            artifact = (
                cpio_extraction.artifact
            )

            if id(
                artifact
            ) in seen_artifacts:
                continue

            self._validate_filesystem_artifact(
                artifact
            )

            work_items.append(
                _FilesystemMetadataWorkItem(
                    artifact=artifact,
                    partition=(
                        self._owning_partition(
                            artifact,
                            inventory,
                        )
                    ),
                    cpio_extraction=(
                        cpio_extraction
                    ),
                )
            )

            seen_artifacts.add(
                id(
                    artifact
                )
            )

        #
        # Every other canonical filesystem extraction.
        #
        # This naturally includes APEX payload filesystems without knowing
        # anything about APEX semantics. Extraction operation + lineage are
        # sufficient.
        #
        for artifact in (
            extraction.artifacts
        ):
            if id(
                artifact
            ) in seen_artifacts:
                continue

            if (
                artifact.kind
                is not ExtractionArtifactKind.DIRECTORY
            ):
                continue

            if (
                artifact.operation
                is not ExtractionOperation
                .FILESYSTEM_EXTRACTION
            ):
                continue

            parent = (
                artifact.parent
            )

            if parent is None:
                raise FilesystemMetadataCollectionStageError(
                    "FILESYSTEM_EXTRACTION artifact has no "
                    "canonical metadata-source parent: "
                    f"{artifact.path}"
                )

            self._validate_filesystem_artifact(
                artifact
            )

            work_items.append(
                _FilesystemMetadataWorkItem(
                    artifact=artifact,
                    partition=(
                        self._owning_partition(
                            artifact,
                            inventory,
                        )
                    ),
                    metadata_source=parent,
                )
            )

            seen_artifacts.add(
                id(
                    artifact
                )
            )

        return tuple(
            work_items
        )

    def _collect_work_item(
        self,
        *,
        item: _FilesystemMetadataWorkItem,
        current: int,
        total: int,
    ) -> FilesystemBackendResult:
        label = (
            self._work_item_label(
                item
            )
        )

        progress_callback = (
            self._entry_progress_callback(
                subject=label,
                current=current,
                total=total,
            )
        )

        if item.cpio_extraction is not None:
            metadata = (
                self._cpio_normalizer.build(
                    item.cpio_extraction,
                    progress_callback=(
                        progress_callback
                    ),
                )
            )

            return FilesystemBackendResult(
                artifact=item.artifact,
                source_type=(
                    FilesystemSourceType
                    .HOST_DIRECTORY
                ),
                metadata=metadata,
                partition=item.partition,
            )

        if item.metadata_source is None:
            raise FilesystemMetadataCollectionStageError(
                "Image-backed filesystem work item has no "
                "authoritative metadata source"
            )

        return self._manager.collect_metadata(
            item.artifact,
            metadata_source=(
                item.metadata_source
            ),
            partition=item.partition,
            root=self._root,
            include_root=self._include_root,
            max_depth=self._max_depth,
            progress_callback=(
                progress_callback
            ),
        )

    def _entry_progress_callback(
        self,
        *,
        subject: str,
        current: int,
        total: int,
    ) -> MetadataEntryProgressCallback:
        def report(
            path: str,
            processed: int,
        ) -> None:
            self._report_progress(
                ProgressEvent(
                    stage="Filesystem Metadata",
                    state=ProgressState.RUNNING,
                    current=current,
                    total=total,
                    subject=subject,
                    operation=(
                        "normalizing filesystem metadata"
                    ),
                    item=path,
                    processed=processed,
                )
            )

        return report

    @staticmethod
    def _validate_selection_coverage(
        *,
        inventory: PartitionInventory,
        selection: FilesystemPartitionSelection,
    ) -> None:
        """
        Require every canonical InventoryPartition to receive exactly one
        filesystem-selection disposition.

        A partition is either selected for Filesystem Metadata or explicitly
        skipped with a canonical reason. No InventoryPartition may disappear
        between Extraction and Filesystem Metadata.
        """

        input_by_identity = {
            id(partition): partition
            for partition in inventory.partitions
        }

        selected = tuple(
            selection.inventory.partitions
        )

        skipped = tuple(
            item.partition
            for item in selection.skipped
        )

        classified = (
            selected
            + skipped
        )

        classified_by_identity = {
            id(partition): partition
            for partition in classified
        }

        if len(classified_by_identity) != len(classified):
            raise FilesystemMetadataCollectionStageError(
                "filesystem partition selection classified one "
                "InventoryPartition more than once"
            )

        input_identities = set(
            input_by_identity
        )

        classified_identities = set(
            classified_by_identity
        )

        if classified_identities != input_identities:
            missing = tuple(
                input_by_identity[identity].name
                for identity
                in sorted(
                    input_identities
                    - classified_identities
                )
            )

            unexpected = tuple(
                classified_by_identity[identity].name
                for identity
                in sorted(
                    classified_identities
                    - input_identities
                )
            )

            raise FilesystemMetadataCollectionStageError(
                "filesystem partition selection does not completely "
                "account for canonical PartitionInventory: "
                f"missing={missing}, unexpected={unexpected}"
            )

    @staticmethod
    def _validate_work_item_coverage(
        *,
        extraction: AndroidExtractionResult,
        work_items: tuple[
            _FilesystemMetadataWorkItem,
            ...,
        ],
    ) -> None:
        """
        Require exact coverage of every Extraction-owned filesystem root.

        Filesystem Metadata owns:
        - every canonical FILESYSTEM_EXTRACTION directory artifact;
        - every canonical CPIO extraction root.

        Other Extraction artifacts intentionally remain outside this stage.
        """

        expected: dict[
            int,
            ExtractedArtifact,
        ] = {}

        for artifact in extraction.artifacts:
            if (
                artifact.kind
                is ExtractionArtifactKind.DIRECTORY
                and artifact.operation
                is ExtractionOperation.FILESYSTEM_EXTRACTION
            ):
                expected[
                    id(artifact)
                ] = artifact

        for cpio_extraction in extraction.cpio_extractions:
            artifact = (
                cpio_extraction.artifact
            )

            existing = expected.get(
                id(artifact)
            )

            if (
                existing is not None
                and existing is not artifact
            ):
                raise FilesystemMetadataCollectionStageError(
                    "filesystem coverage identity collision detected"
                )

            expected[
                id(artifact)
            ] = artifact

        actual: dict[
            int,
            ExtractedArtifact,
        ] = {}

        for item in work_items:
            artifact = (
                item.artifact
            )

            artifact_id = id(
                artifact
            )

            if artifact_id in actual:
                raise FilesystemMetadataCollectionStageError(
                    "filesystem metadata work item duplicated exact "
                    "Extraction artifact identity: "
                    f"{artifact.path}"
                )

            actual[
                artifact_id
            ] = artifact

        expected_ids = set(
            expected
        )

        actual_ids = set(
            actual
        )

        if expected_ids == actual_ids:
            return

        missing = tuple(
            expected[identity].path.as_posix()
            for identity
            in sorted(
                expected_ids
                - actual_ids
            )
        )

        unexpected = tuple(
            actual[identity].path.as_posix()
            for identity
            in sorted(
                actual_ids
                - expected_ids
            )
        )

        raise FilesystemMetadataCollectionStageError(
            "Filesystem Metadata work-item coverage does not exactly "
            "match Extraction-owned filesystem roots: "
            f"missing={missing}, unexpected={unexpected}"
        )

    @staticmethod
    def _validate_filesystem_artifact(
        artifact: ExtractedArtifact,
    ) -> None:
        if (
            artifact.kind
            is not ExtractionArtifactKind.DIRECTORY
        ):
            raise FilesystemMetadataCollectionStageError(
                "canonical filesystem artifact must be a directory: "
                f"{artifact.path}"
            )

    @staticmethod
    def _owning_partition(
        artifact: ExtractedArtifact,
        inventory: PartitionInventory,
    ) -> InventoryPartition | None:
        """
        Return the InventoryPartition present in exact Extraction lineage.

        Partition ownership is provenance context only. It does not define
        physical filesystem identity.
        """

        ancestor: ExtractedArtifact | None = (
            artifact
        )

        while ancestor is not None:
            for partition in inventory.partitions:
                if (
                    ancestor
                    is partition.artifact
                ):
                    return partition

            ancestor = (
                ancestor.parent
            )

        return None

    @staticmethod
    def _work_item_label(
        item: _FilesystemMetadataWorkItem,
    ) -> str:
        if item.partition is not None:
            partition_name = (
                item.partition.name
            )

            if (
                item.artifact.operation
                is ExtractionOperation
                .FILESYSTEM_EXTRACTION
                and item.artifact.parent
                is item.partition.artifact
            ):
                return partition_name

            return (
                f"{partition_name}:"
                f"{item.artifact.semantic_name or item.artifact.path.name}"
            )

        return (
            item.artifact.semantic_name
            or item.artifact.path.name
            or item.artifact.path.as_posix()
        )

    def _report_progress(
        self,
        event: ProgressEvent,
    ) -> None:
        if self._progress_callback is not None:
            self._progress_callback(
                event
            )

    @staticmethod
    def _validate_inventory(
        inventory: PartitionInventory,
    ) -> None:
        if not isinstance(
            inventory,
            PartitionInventory,
        ):
            raise FilesystemMetadataCollectionStageError(
                "context.partition_inventory must be "
                "a PartitionInventory"
            )
