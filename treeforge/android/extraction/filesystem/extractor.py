from __future__ import annotations

from pathlib import Path
from shutil import rmtree

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.extraction.filesystem.debugfs import (
    DebugfsExtractionRunner,
)
from treeforge.android.format.filesystem import (
    FilesystemDetector,
    FilesystemType,
)

class FilesystemExtractionError(
    RuntimeError,
):
    """
    Raised when a filesystem image cannot be materialized into a host directory.
    """


class FilesystemExtractor:
    """
    Materialize supported filesystem images into persistent host directories.

    Physical filesystem extraction belongs to TreeForge Extraction.

    The produced DIRECTORY artifact preserves:

    - exact Discovery provenance;
    - exact immediate parent artifact;
    - established semantic identity;
    - FILESYSTEM_EXTRACTION derivation;
    - tool/backend evidence.

    Filesystem parsing and Android model interpretation are intentionally
    outside this class.
    """

    def __init__(
        self,
        *,
        debugfs_runner: DebugfsExtractionRunner | None = None,
    ) -> None:
        self._debugfs_runner = (
            debugfs_runner
            if debugfs_runner is not None
            else DebugfsExtractionRunner()
        )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        """
        Return whether the canonical artifact contains a filesystem TreeForge
        can currently extract.
        """

        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        try:
            detected = FilesystemDetector.detect(
                parent.path
            )
        except (
            FileNotFoundError,
            OSError,
            ValueError,
        ):
            return False

        return (
            detected
            is FilesystemType.EXT4
        )

    def extract(
        self,
        parent: ExtractedArtifact,
        destination: Path,
    ) -> ExtractedArtifact:
        """
        Extract one supported filesystem image into a persistent directory.
        """

        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise FilesystemExtractionError(
                "filesystem extraction parent must be a file"
            )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        if not parent.path.exists():
            raise FileNotFoundError(
                f"filesystem image does not exist: {parent.path}"
            )

        if not parent.path.is_file():
            raise FilesystemExtractionError(
                "filesystem extraction source must be "
                f"a regular file: {parent.path}"
            )

        detected = FilesystemDetector.detect(
            parent.path
        )

        if (
            detected
            is not FilesystemType.EXT4
        ):
            raise FilesystemExtractionError(
                "filesystem extraction is not implemented "
                f"for {detected}: {parent.path}"
            )

        self._prepare_destination(
            destination
        )

        executable = (
            self._debugfs_runner.resolve_executable()
        )

        request = (
            "rdump "
            f"{self._debugfs_runner.quote_argument('/')} "
            f"{self._debugfs_runner.quote_argument(str(destination))}"
        )

        command = (
            self._debugfs_runner.build_command(
                executable=executable,
                image=parent.path,
                request=request,
            )
        )

        try:
            stdout = (
                self._debugfs_runner.rdump(
                    parent.path,
                    "/",
                    destination,
                )
            )
        except Exception as error:
            self._cleanup_failed_destination(
                destination
            )

            raise FilesystemExtractionError(
                "Unable to extract filesystem image: "
                f"{parent.path}"
            ) from error

        if not destination.exists():
            raise FilesystemExtractionError(
                "filesystem extraction did not create "
                f"its destination: {destination}"
            )

        if not destination.is_dir():
            raise FilesystemExtractionError(
                "filesystem extraction destination is "
                f"not a directory: {destination}"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=ExtractionArtifactKind.DIRECTORY,
            operation=(
                ExtractionOperation
                .FILESYSTEM_EXTRACTION
            ),
            semantic_name=(
                parent.semantic_name
            ),
            parent=parent,
            tool=ExtractionToolEvidence(
                name="debugfs",
                executable=str(
                    executable
                ),
                command=command,
                returncode=0,
                stdout=stdout,
            ),
        )

    @staticmethod
    def _prepare_destination(
        destination: Path,
    ) -> None:
        if destination.exists():
            if not destination.is_dir():
                raise NotADirectoryError(
                    "filesystem extraction destination "
                    f"must be a directory: {destination}"
                )

            rmtree(
                destination
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _cleanup_failed_destination(
        destination: Path,
    ) -> None:
        try:
            if destination.is_dir():
                rmtree(
                    destination
                )
        except OSError:
            # Preserve the original extraction failure.
            pass