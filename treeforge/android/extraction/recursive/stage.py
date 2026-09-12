from __future__ import annotations

from collections import deque
from pathlib import Path

from treeforge.android.extraction.builder import (
    AndroidExtractionBuilder,
)
from treeforge.android.extraction.recursive.materializer import (
    ExtractionArtifactMaterializer,
    ExtractionMaterializationOutcome,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
)
from treeforge.android.extraction.recursive.nested import (
    NestedArtifactDiscoverer,
)
from treeforge.android.extraction.result import (
    AndroidExtractionResult,
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


class RecursiveExtractionStageError(
    RuntimeError,
):
    pass


class RecursiveExtractionStage(
    PipelineStage,
):
    """
    Expand canonical physical Extraction artifacts to a fixed point.

    Each materializer receives every newly available canonical artifact at
    most once. Newly produced children are immediately scheduled for every
    materializer, allowing arbitrary supported nesting without re-entering
    an earlier pipeline stage.
    """

    name = "Expand Physical Artifacts"

    def __init__(
        self,
        *,
        materializers: tuple[
            ExtractionArtifactMaterializer,
            ...,
        ],
        progress_callback: (
            ProgressCallback
            | None
        ) = None,
    ) -> None:
        if not isinstance(
            materializers,
            tuple,
        ):
            raise TypeError(
                "materializers must be a tuple"
            )

        names = tuple(
            materializer.name
            for materializer
            in materializers
        )

        if len(
            names
        ) != len(
            set(
                names
            )
        ):
            raise ValueError(
                "materializer names must be unique"
            )

        self.materializers = (
            materializers
        )

        self._progress_callback = (
            progress_callback
        )

        self.nested_artifact_discoverer = (
            NestedArtifactDiscoverer()
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

        existing = (
            context.android_extraction
        )

        if existing is None:
            raise RecursiveExtractionStageError(
                "Canonical extraction state has not been established"
            )

        if not isinstance(
            existing,
            AndroidExtractionResult,
        ):
            raise RecursiveExtractionStageError(
                "context extraction result is invalid"
            )

        builder = (
            AndroidExtractionBuilder(
                existing
            )
        )

        queue = deque(
            existing.artifacts
        )

        processed: set[
            tuple[
                int,
                str,
            ]
        ] = set()

        output_root = (
            context.workspace.root
            / "extracted"
        )

        completed_materializations = 0

        while queue:
            parent = queue.popleft()

            for materializer in (
                self.materializers
            ):
                identity = (
                    id(
                        parent
                    ),
                    materializer.name,
                )

                if identity in processed:
                    continue

                processed.add(
                    identity
                )

                #
                # Exact canonical child identity makes the stage safely
                # re-entrant over an already-expanded Extraction result.
                #
                if builder.has_child(
                    parent,
                    operation=(
                        materializer.operation
                    ),
                ):
                    continue

                try:
                    supported = (
                        materializer.supports(
                            parent
                        )
                    )

                except Exception as error:
                    raise RecursiveExtractionStageError(
                        "Unable to determine recursive extraction "
                        f"eligibility for {parent.path} using "
                        f"{materializer.name}"
                    ) from error

                if not supported:
                    continue

                self._report_progress(
                    current=completed_materializations,
                    subject=(
                        parent.semantic_name
                        or parent.path.name
                    ),
                    operation=self._operation_label(
                        materializer.name
                    ),
                    item=parent.path.as_posix(),
                    detail=(
                        f"queued_before={len(queue)}"
                    ),
                    input_size_bytes=parent.size_bytes,
                )

                try:
                    outcome = (
                        materializer.materialize(
                            parent,
                            output_root,
                        )
                    )

                except Exception as error:
                    raise RecursiveExtractionStageError(
                        "Recursive extraction materializer failed: "
                        f"{materializer.name}: {parent.path}"
                    ) from error

                if not isinstance(
                    outcome,
                    ExtractionMaterializationOutcome,
                ):
                    raise RecursiveExtractionStageError(
                        "materializer returned an invalid outcome: "
                        f"{materializer.name}"
                    )

                effective_parent = parent

                if (
                    outcome.replacement_parent
                    is not None
                ):
                    try:
                        effective_parent = (
                            builder.replace_artifact(
                                parent,
                                outcome.replacement_parent,
                            )
                        )
                    except Exception as error:
                        raise RecursiveExtractionStageError(
                            "Unable to install canonical artifact "
                            "replacement produced by "
                            f"{materializer.name}: {parent.path}"
                        ) from error

                    parent = effective_parent

                for artifact in (
                    outcome.artifacts
                ):
                    if (
                        artifact.parent
                        is not effective_parent
                    ):
                        raise RecursiveExtractionStageError(
                            "recursive extraction must preserve "
                            "exact effective parent identity"
                        )

                    if (
                        artifact.operation
                        is not materializer.operation
                    ):
                        raise RecursiveExtractionStageError(
                            "materializer produced the wrong "
                            "ExtractionOperation: "
                            f"{materializer.name}"
                        )

                added = (
                    builder.add_many(
                        outcome.artifacts
                    )
                )

                for extraction in (
                    outcome.cpio_extractions
                ):
                    builder.add_cpio_extraction(
                        extraction
                    )

                queue.extend(
                    added
                )

                for artifact in added:
                    if (
                        artifact.kind
                        is not ExtractionArtifactKind.DIRECTORY
                    ):
                        continue

                    discovered = (
                        self.nested_artifact_discoverer.discover(
                            artifact,
                            consumers=(
                                self.materializers
                            ),
                        )
                    )

                    discovered_added = (
                        builder.add_many(
                            discovered
                        )
                    )

                    queue.extend(
                        discovered_added
                    )

                completed_materializations += 1

                produced_total = len(
                    added
                )

                output_size_bytes = (
                    sum(
                        artifact.size_bytes
                        for artifact in added
                        if artifact.size_bytes is not None
                    )
                    if any(
                        artifact.size_bytes is not None
                        for artifact in added
                    )
                    else None
                )

                self._report_progress(
                    current=completed_materializations,
                    subject=(
                        parent.semantic_name
                        or parent.path.name
                    ),
                    operation=self._operation_label(
                        materializer.name
                    ),
                    item=parent.path.as_posix(),
                    detail=(
                        f"produced_total={produced_total}, "
                        f"queued_after={len(queue)}"
                    ),
                    input_size_bytes=parent.size_bytes,
                    output_size_bytes=output_size_bytes,
                    produced=produced_total,
                )

        result = (
            builder.build()
        )

        context.android_extraction = (
            result
        )

        self._report_completion(
            completed_materializations=(
                completed_materializations
            ),
            artifact_count=len(
                result.artifacts
            ),
        )

    def _report_completion(
        self,
        *,
        completed_materializations: int,
        artifact_count: int,
    ) -> None:
        """
        Report the fixed point reached by recursive Extraction.

        Recursive expansion has no truthful total while it is running because
        each transformation may expose additional canonical artifacts. The
        final artifact count becomes authoritative only after the work queue
        is exhausted.
        """

        if self._progress_callback is None:
            return

        self._progress_callback(
            ProgressEvent(
                stage=self.name,
                state=ProgressState.COMPLETE,
                current=artifact_count,
                total=artifact_count,
                detail=(
                    "recursive extraction fixed point reached"
                ),
                subject="canonical extraction artifacts",
                operation=(
                    "recursive artifact expansion complete"
                ),
                processed=artifact_count,
                produced=artifact_count,
            )
        )

    @staticmethod
    def _operation_label(
        materializer_name: str,
    ) -> str:
        """
        Return concise human-readable progress wording for one physical
        Extraction materializer.

        Internal materializer names remain stable implementation identities.
        This mapping affects presentation only.
        """

        labels = {
            "sparse": "normalizing sparse image",
            "boot": "reading boot-family structure",
            "dtbo": "reading DTBO structure and entries",
            "standalone_avb_vbmeta": (
                "reading standalone AVB structure"
            ),
            "ext4_structure": (
                "reading EXT4 physical structure"
            ),
            "avb": (
                "extracting AVB verification regions"
            ),
            "kernel": "decompressing kernel payload",
            "ramdisk": "decompressing ramdisk",
            "cpio": "extracting CPIO archive",
            "apex": "extracting APEX container",
            "fbpk": "extracting FBPK payload entries",
            "ufpk": "extracting UFPK descriptor regions",
            "boot_firmware_envelope": (
                "extracting verified firmware payload"
            ),
            "sflb": "extracting SFLB resource entries",
            "sflb_compression": (
                "decompressing SFLB resource"
            ),
            "embedded_elf": (
                "extracting embedded ELF objects"
            ),
            "logical_partition_container": (
                "unpacking logical partitions"
            ),
            "filesystem": (
                "extracting filesystem contents"
            ),
        }

        return labels.get(
            materializer_name,
            materializer_name.replace(
                "_",
                " ",
            ),
        )

    def _report_progress(
        self,
        *,
        current: int,
        subject: str,
        operation: str,
        item: str,
        detail: str,
        input_size_bytes: int | None = None,
        output_size_bytes: int | None = None,
        produced: int | None = None,
    ) -> None:
        if self._progress_callback is None:
            return

        self._progress_callback(
            ProgressEvent(
                stage=self.name,
                state=ProgressState.RUNNING,
                current=current,
                total=None,
                detail=detail,
                subject=subject,
                operation=operation,
                item=item,
                processed=current,
                input_size_bytes=input_size_bytes,
                output_size_bytes=output_size_bytes,
                produced=produced,
            )
        )
