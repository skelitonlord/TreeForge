from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.extraction.cpio.extractor import (
    CpioExtractionResult,
)
from treeforge.android.providers.artifact import (
    ProviderArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidExtractionResult:
    """
    Canonical immutable result of TreeForge source extraction/materialization.

    Every retained output is represented exactly once by physical path.

    Artifacts remain deterministically ordered in the order established by the
    extraction pipeline.

    This result does not reinterpret artifacts into partition, filesystem,
    boot, vendor, build, or reconstruction models.

    Downstream inventories consume this canonical extraction result.
    """

    artifacts: tuple[
        ExtractedArtifact,
        ...,
    ] = ()

    cpio_extractions: tuple[
        CpioExtractionResult,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifacts,
            tuple,
        ):
            raise TypeError(
                "artifacts must be a tuple"
            )

        for artifact in self.artifacts:
            if not isinstance(
                artifact,
                ExtractedArtifact,
            ):
                raise TypeError(
                    "artifacts must contain "
                    "ExtractedArtifact instances"
                )

        paths = tuple(
            artifact.path
            for artifact
            in self.artifacts
        )

        if (
            len(paths)
            != len(
                set(paths)
            )
        ):
            raise ValueError(
                "extraction result must not contain "
                "duplicate artifact paths"
            )

        if not isinstance(
            self.cpio_extractions,
            tuple,
        ):
            raise TypeError(
                "cpio_extractions must be a tuple"
            )

        cpio_artifact_ids: set[
            int
        ] = set()

        for extraction in self.cpio_extractions:
            if not isinstance(
                extraction,
                CpioExtractionResult,
            ):
                raise TypeError(
                    "cpio_extractions must contain "
                    "CpioExtractionResult instances"
                )

            if not any(
                artifact
                is extraction.artifact
                for artifact
                in self.artifacts
            ):
                raise ValueError(
                    "CPIO extraction must reference "
                    "the exact canonical artifact "
                    "contained by this result"
                )

            artifact_id = id(
                extraction.artifact
            )

            if artifact_id in cpio_artifact_ids:
                raise ValueError(
                    "canonical CPIO artifact has "
                    "duplicate extraction results"
                )

            cpio_artifact_ids.add(
                artifact_id
            )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not self.artifacts

    @property
    def paths(
        self,
    ) -> tuple[
        Path,
        ...,
    ]:
        return tuple(
            artifact.path
            for artifact
            in self.artifacts
        )

    def artifact_at(
        self,
        path: Path,
    ) -> ExtractedArtifact | None:
        """
        Return the canonical extraction artifact at an exact physical path.
        """

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        for artifact in self.artifacts:
            if artifact.path == path:
                return artifact

        return None

    def artifacts_for_source(
        self,
        source: ProviderArtifact,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Return artifacts preserving one exact upstream ProviderArtifact identity.
        """

        if not isinstance(
            source,
            ProviderArtifact,
        ):
            raise TypeError(
                "source must be a ProviderArtifact"
            )

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.source is source
        )

    def children_of(
        self,
        parent: ExtractedArtifact,
        *,
        operation: (
            ExtractionOperation
            | None
        ) = None,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Return direct derivation children of one exact canonical artifact.
        """

        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            operation is not None
            and not isinstance(
                operation,
                ExtractionOperation,
            )
        ):
            raise TypeError(
                "operation must be an ExtractionOperation or None"
            )

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if (
                artifact.parent
                is parent
                and (
                    operation is None
                    or artifact.operation
                    is operation
                )
            )
        )

    def child_of(
        self,
        parent: ExtractedArtifact,
        *,
        operation: (
            ExtractionOperation
            | None
        ) = None,
    ) -> ExtractedArtifact | None:
        """
        Return one uniquely identified direct derivation child.
        """

        matching = (
            self.children_of(
                parent,
                operation=operation,
            )
        )

        if not matching:
            return None

        if len(matching) != 1:
            raise ValueError(
                "extraction artifact has ambiguous "
                "direct derivation children: "
                f"{parent.path}"
            )

        return matching[0]

    def artifacts_named(
        self,
        semantic_name: str,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Return artifacts carrying an exact extraction-established semantic name.
        """

        if not isinstance(
            semantic_name,
            str,
        ):
            raise TypeError(
                "semantic_name must be a string"
            )

        if not semantic_name.strip():
            raise ValueError(
                "semantic_name cannot be empty"
            )

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.semantic_name
            == semantic_name
        )

    def artifact_named(
        self,
        semantic_name: str,
        *,
        operation: (
            ExtractionOperation
            | None
        ) = None,
    ) -> ExtractedArtifact | None:
        """
        Return one uniquely identified extraction artifact.

        When operation is supplied, both semantic identity and operation must
        match.

        Ambiguous matches are rejected rather than silently selecting one.
        """

        if (
            operation is not None
            and not isinstance(
                operation,
                ExtractionOperation,
            )
        ):
            raise TypeError(
                "operation must be an ExtractionOperation or None"
            )

        matching = tuple(
            artifact
            for artifact
            in self.artifacts_named(
                semantic_name
            )
            if (
                operation is None
                or artifact.operation
                is operation
            )
        )

        if not matching:
            return None

        if len(matching) != 1:
            raise ValueError(
                "extraction semantic identity is ambiguous: "
                f"{semantic_name}"
            )

        return matching[0]

    def artifacts_for_operation(
        self,
        operation: ExtractionOperation,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Return all artifacts produced/adopted by one exact operation.
        """

        if not isinstance(
            operation,
            ExtractionOperation,
        ):
            raise TypeError(
                "operation must be an ExtractionOperation"
            )

        return tuple(
            artifact
            for artifact
            in self.artifacts
            if artifact.operation
            is operation
        )