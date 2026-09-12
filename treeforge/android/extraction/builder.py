from __future__ import annotations

from pathlib import Path

from treeforge.android.extraction.cpio.extractor import (
    CpioExtractionResult,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.extraction.result import (
    AndroidExtractionResult,
)


class AndroidExtractionBuilder:
    """
    Mutable execution-only accumulator for canonical Extraction state.

    AndroidExtractionResult remains the immutable public boundary.

    This builder centralizes:
    - physical-path uniqueness;
    - exact parent identity validation;
    - CPIO result identity;
    - child/operation queries;
    - final immutable result construction.
    """

    def __init__(
        self,
        result: AndroidExtractionResult,
    ) -> None:
        if not isinstance(
            result,
            AndroidExtractionResult,
        ):
            raise TypeError(
                "result must be an AndroidExtractionResult"
            )

        self._artifacts = list(
            result.artifacts
        )

        self._by_path: dict[
            Path,
            ExtractedArtifact,
        ] = {
            artifact.path: artifact
            for artifact
            in self._artifacts
        }

        self._cpio_extractions = list(
            result.cpio_extractions
        )

        self._cpio_artifact_ids = {
            id(
                item.artifact
            )
            for item
            in self._cpio_extractions
        }

    @property
    def artifacts(
        self,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        return tuple(
            self._artifacts
        )

    def contains(
        self,
        artifact: ExtractedArtifact,
    ) -> bool:
        return any(
            candidate is artifact
            for candidate
            in self._artifacts
        )

    def artifact_at(
        self,
        path: Path,
    ) -> ExtractedArtifact | None:
        return self._by_path.get(
            path
        )

    def children_of(
        self,
        parent: ExtractedArtifact,
        *,
        operation: ExtractionOperation | None = None,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        return tuple(
            artifact
            for artifact
            in self._artifacts
            if (
                artifact.parent is parent
                and (
                    operation is None
                    or artifact.operation is operation
                )
            )
        )

    def has_child(
        self,
        parent: ExtractedArtifact,
        *,
        operation: ExtractionOperation,
    ) -> bool:
        return bool(
            self.children_of(
                parent,
                operation=operation,
            )
        )

    def replace_artifact(
        self,
        original: ExtractedArtifact,
        replacement: ExtractedArtifact,
    ) -> ExtractedArtifact:
        """
        Replace one canonical artifact with an enriched immutable equivalent.

        Replacement is intentionally narrow. Physical/provenance identity
        must remain unchanged; only additive canonical evidence such as
        Extraction facts may differ.

        Replacement is permitted only before canonical children or CPIO
        extraction state depend on the original object, because those
        relationships preserve exact object identity.
        """

        if not isinstance(
            original,
            ExtractedArtifact,
        ):
            raise TypeError(
                "original must be an ExtractedArtifact"
            )

        if not isinstance(
            replacement,
            ExtractedArtifact,
        ):
            raise TypeError(
                "replacement must be an ExtractedArtifact"
            )

        if not self.contains(
            original
        ):
            raise ValueError(
                "original artifact is not canonical"
            )

        if replacement is original:
            return original

        for (
            field_name,
            original_value,
            replacement_value,
        ) in (
            (
                "source",
                original.source,
                replacement.source,
            ),
            (
                "path",
                original.path,
                replacement.path,
            ),
            (
                "kind",
                original.kind,
                replacement.kind,
            ),
            (
                "operation",
                original.operation,
                replacement.operation,
            ),
            (
                "semantic_name",
                original.semantic_name,
                replacement.semantic_name,
            ),
            (
                "parent",
                original.parent,
                replacement.parent,
            ),
            (
                "tool",
                original.tool,
                replacement.tool,
            ),
            (
                "content_sha256",
                original.content_sha256,
                replacement.content_sha256,
            ),
            (
                "size_bytes",
                original.size_bytes,
                replacement.size_bytes,
            ),
        ):
            if original_value is not replacement_value:
                if original_value != replacement_value:
                    raise ValueError(
                        "canonical artifact replacement must preserve "
                        f"{field_name}"
                    )

        if self.children_of(
            original
        ):
            raise ValueError(
                "canonical artifact cannot be replaced after "
                "children depend on its exact identity"
            )

        if any(
            extraction.artifact is original
            for extraction
            in self._cpio_extractions
        ):
            raise ValueError(
                "canonical artifact cannot be replaced after "
                "CPIO state depends on its exact identity"
            )

        existing = self._by_path.get(
            original.path
        )

        if existing is not original:
            raise ValueError(
                "canonical path index does not reference "
                "the original artifact"
            )

        index = next(
            (
                index
                for index, artifact
                in enumerate(
                    self._artifacts
                )
                if artifact is original
            ),
            None,
        )

        if index is None:
            raise ValueError(
                "canonical artifact index is inconsistent"
            )

        self._artifacts[
            index
        ] = replacement

        self._by_path[
            replacement.path
        ] = replacement

        return replacement

    def add(
        self,
        artifact: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            artifact.parent is not None
            and not self.contains(
                artifact.parent
            )
        ):
            raise ValueError(
                "derived artifact parent must be the exact "
                "canonical artifact already owned by Extraction"
            )

        existing = (
            self._by_path.get(
                artifact.path
            )
        )

        if existing is artifact:
            return False

        if existing is not None:
            raise ValueError(
                "multiple canonical extraction artifacts "
                "cannot own the same physical path: "
                f"{artifact.path}"
            )

        self._artifacts.append(
            artifact
        )

        self._by_path[
            artifact.path
        ] = artifact

        return True

    def add_many(
        self,
        artifacts: tuple[
            ExtractedArtifact,
            ...,
        ],
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        if not isinstance(
            artifacts,
            tuple,
        ):
            raise TypeError(
                "artifacts must be a tuple"
            )

        added = []

        for artifact in artifacts:
            if self.add(
                artifact
            ):
                added.append(
                    artifact
                )

        return tuple(
            added
        )

    def add_cpio_extraction(
        self,
        extraction: CpioExtractionResult,
    ) -> None:
        if not isinstance(
            extraction,
            CpioExtractionResult,
        ):
            raise TypeError(
                "extraction must be a CpioExtractionResult"
            )

        if not self.contains(
            extraction.artifact
        ):
            raise ValueError(
                "CPIO extraction artifact must already be canonical"
            )

        artifact_id = id(
            extraction.artifact
        )

        if artifact_id in self._cpio_artifact_ids:
            return

        self._cpio_artifact_ids.add(
            artifact_id
        )

        self._cpio_extractions.append(
            extraction
        )

    def build(
        self,
    ) -> AndroidExtractionResult:
        return AndroidExtractionResult(
            artifacts=tuple(
                self._artifacts
            ),
            cpio_extractions=tuple(
                self._cpio_extractions
            ),
        )
