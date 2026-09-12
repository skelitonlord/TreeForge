from __future__ import annotations

from pathlib import Path
from typing import Protocol

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
)


class NestedArtifactCandidateConsumer(
    Protocol,
):
    """
    Contract for recursive Extraction consumers that can identify interesting
    physical files inside an already-materialized directory artifact.

    Candidate discovery is intentionally narrower than full Extraction
    support. It answers only whether a physical filesystem path is worth
    promoting into canonical Extraction state.
    """

    name: str

    def supports_discovered_path(
        self,
        path: Path,
    ) -> bool:
        ...


class NestedArtifactDiscoverer:
    """
    Discover recursively materializable child files inside canonical
    DIRECTORY artifacts.

    Ordinary filesystem contents remain ordinary filesystem contents.

    A path becomes a canonical ExtractedArtifact only when at least one
    registered recursive Extraction consumer explicitly declares interest in
    that physical file.

    This keeps the Extraction graph focused on materialization boundaries
    rather than indexing every file in every extracted filesystem.
    """

    def discover(
        self,
        parent: ExtractedArtifact,
        *,
        consumers: tuple[
            NestedArtifactCandidateConsumer,
            ...,
        ],
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.DIRECTORY
        ):
            return ()

        if not isinstance(
            consumers,
            tuple,
        ):
            raise TypeError(
                "consumers must be a tuple"
            )

        discovered: list[
            ExtractedArtifact
        ] = []

        for path in sorted(
            parent.path.rglob("*"),
            key=lambda item: (
                item.as_posix()
            ),
        ):
            if not path.is_file():
                continue

            interested = False

            for consumer in consumers:
                supports_discovered_path = getattr(
                    consumer,
                    "supports_discovered_path",
                    None,
                )

                if supports_discovered_path is None:
                    continue

                try:
                    if supports_discovered_path(
                        path
                    ):
                        interested = True
                        break

                except (
                    FileNotFoundError,
                    OSError,
                    ValueError,
                ):
                    continue

            if not interested:
                continue

            relative_path = (
                path.relative_to(
                    parent.path
                )
            )

            discovered.append(
                ExtractedArtifact(
                    source=parent.source,
                    path=path,
                    kind=ExtractionArtifactKind.FILE,
                    operation=(
                        ExtractionOperation
                        .NESTED_ARTIFACT_DISCOVERY
                    ),
                    semantic_name=(
                        parent.semantic_name
                    ),
                    parent=parent,
                    facts=(
                        ExtractionFact(
                            name="relative_path",
                            value=(
                                relative_path
                                .as_posix()
                            ),
                        ),
                    ),
                )
            )

        return tuple(
            discovered
        )