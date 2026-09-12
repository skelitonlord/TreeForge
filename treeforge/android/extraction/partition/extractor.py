from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.android.extraction.partition.lpunpack import (
    LpunpackResult,
    LpunpackRunner,
)


class LogicalPartitionExtractionError(
    RuntimeError,
):
    """
    Raised when logical partition images cannot be extracted and validated.
    """


class LogicalPartitionExtractor:
    """
    Extract logical partition images into canonical Extraction artifacts.

    This service owns:

    - deterministic output-path construction;
    - stale-output removal;
    - lpunpack coordination;
    - output validation;
    - failed-output cleanup;
    - output hashing and size evidence;
    - explicit logical-partition semantic identity;
    - parent/source lineage;
    - lpunpack execution evidence.

    It does not build PartitionInventory.
    """

    HASH_CHUNK_SIZE = (
        1024 * 1024
    )

    def __init__(
        self,
        *,
        runner: LpunpackRunner | None = None,
    ) -> None:
        self._runner = (
            runner
            if runner is not None
            else LpunpackRunner()
        )

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
        """
        Extract exact logical partitions from one canonical parent artifact.
        """

        normalized_parent = (
            self._validate_parent(
                parent
            )
        )

        normalized_names = (
            self._validate_partition_names(
                partition_names
            )
        )

        normalized_output = (
            self._prepare_output_directory(
                output_directory
            )
        )

        expected_outputs = {
            name: (
                normalized_output
                / f"{name}.img"
            )
            for name in normalized_names
        }

        self._remove_stale_outputs(
            expected_outputs
        )

        try:
            execution = (
                self._runner.run(
                    normalized_parent.path,
                    normalized_names,
                    normalized_output,
                )
            )

            if not isinstance(
                execution,
                LpunpackResult,
            ):
                raise LogicalPartitionExtractionError(
                    "lpunpack runner returned an invalid result"
                )

            self._validate_outputs(
                expected_outputs
            )

            tool = (
                self._build_tool_evidence(
                    execution
                )
            )

            return tuple(
                self._build_artifact(
                    parent=normalized_parent,
                    partition_name=name,
                    path=expected_outputs[
                        name
                    ],
                    tool=tool,
                )
                for name
                in normalized_names
            )

        except Exception as error:
            self._cleanup_outputs(
                expected_outputs
            )

            if isinstance(
                error,
                LogicalPartitionExtractionError,
            ):
                raise

            names = ", ".join(
                normalized_names
            )

            raise LogicalPartitionExtractionError(
                "Unable to extract logical partitions "
                f"{names} from "
                f"{normalized_parent.path}"
            ) from error

    @staticmethod
    def _validate_parent(
        parent: ExtractedArtifact,
    ) -> ExtractedArtifact:
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
            raise LogicalPartitionExtractionError(
                "logical partition parent must be a file: "
                f"{parent.path}"
            )

        if not parent.path.exists():
            raise FileNotFoundError(
                "logical partition source does not exist: "
                f"{parent.path}"
            )

        if not parent.path.is_file():
            raise LogicalPartitionExtractionError(
                "logical partition source must be a regular file: "
                f"{parent.path}"
            )

        return parent

    @staticmethod
    def _validate_partition_names(
        partition_names: tuple[
            str,
            ...,
        ],
    ) -> tuple[
        str,
        ...,
    ]:
        if not isinstance(
            partition_names,
            tuple,
        ):
            raise TypeError(
                "partition_names must be a tuple"
            )

        if not partition_names:
            raise ValueError(
                "partition_names cannot be empty"
            )

        seen: set[str] = set()

        for name in partition_names:
            if not isinstance(
                name,
                str,
            ):
                raise TypeError(
                    "partition names must be strings"
                )

            if not name.strip():
                raise ValueError(
                    "partition names cannot be empty"
                )

            if name in seen:
                raise ValueError(
                    f"Duplicate partition name: {name}"
                )

            if (
                "/" in name
                or "\\" in name
                or name in {
                    ".",
                    "..",
                }
            ):
                raise ValueError(
                    f"Invalid partition name: {name!r}"
                )

            seen.add(
                name
            )

        return partition_names

    @staticmethod
    def _prepare_output_directory(
        output_directory: Path,
    ) -> Path:
        if not isinstance(
            output_directory,
            Path,
        ):
            raise TypeError(
                "output_directory must be a pathlib.Path"
            )

        if (
            output_directory.exists()
            and not output_directory.is_dir()
        ):
            raise NotADirectoryError(
                "Logical partition output path must "
                f"be a directory: {output_directory}"
            )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return output_directory

    @staticmethod
    def _remove_stale_outputs(
        expected_outputs: dict[
            str,
            Path,
        ],
    ) -> None:
        for (
            name,
            image,
        ) in expected_outputs.items():
            if image.is_dir():
                raise LogicalPartitionExtractionError(
                    "Expected logical partition output is "
                    f"a directory for {name}: {image}"
                )

            if image.exists():
                try:
                    image.unlink()
                except OSError as error:
                    raise LogicalPartitionExtractionError(
                        "Unable to remove stale logical "
                        f"partition image for {name}: "
                        f"{image}"
                    ) from error

    @staticmethod
    def _validate_outputs(
        expected_outputs: dict[
            str,
            Path,
        ],
    ) -> None:
        for (
            name,
            image,
        ) in expected_outputs.items():
            if not image.exists():
                raise LogicalPartitionExtractionError(
                    "lpunpack did not produce partition "
                    f"image for {name}: {image}"
                )

            if image.is_dir():
                raise LogicalPartitionExtractionError(
                    "Extracted logical partition image "
                    f"cannot be a directory for {name}: "
                    f"{image}"
                )

            if not image.is_file():
                raise LogicalPartitionExtractionError(
                    "Extracted logical partition image "
                    f"must be a regular file for {name}: "
                    f"{image}"
                )

    @classmethod
    def _build_artifact(
        cls,
        *,
        parent: ExtractedArtifact,
        partition_name: str,
        path: Path,
        tool: ExtractionToolEvidence,
    ) -> ExtractedArtifact:
        return ExtractedArtifact(
            source=parent.source,
            path=path,
            kind=ExtractionArtifactKind.FILE,
            operation=(
                ExtractionOperation
                .LOGICAL_PARTITION_EXTRACTION
            ),
            semantic_name=partition_name,
            parent=parent,
            tool=tool,
            content_sha256=(
                cls._sha256_file(
                    path
                )
            ),
            size_bytes=(
                path.stat().st_size
            ),
        )

    @staticmethod
    def _build_tool_evidence(
        result: LpunpackResult,
    ) -> ExtractionToolEvidence:
        executable = (
            result.command[0]
            if result.command
            else None
        )

        return ExtractionToolEvidence(
            name="lpunpack",
            executable=executable,
            command=result.command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    @classmethod
    def _sha256_file(
        cls,
        path: Path,
    ) -> str:
        digest = sha256()

        with path.open(
            "rb"
        ) as stream:
            while True:
                chunk = stream.read(
                    cls.HASH_CHUNK_SIZE
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return digest.hexdigest()

    @staticmethod
    def _cleanup_outputs(
        expected_outputs: dict[
            str,
            Path,
        ],
    ) -> None:
        for image in (
            expected_outputs.values()
        ):
            try:
                if (
                    image.exists()
                    and image.is_file()
                ):
                    image.unlink()
            except OSError:
                # Preserve the original extraction error.
                pass