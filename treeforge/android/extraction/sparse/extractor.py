from __future__ import annotations

from treeforge.android.toolchain import AndroidHostTools

import os
import shutil
import subprocess
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Protocol, Sequence

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class SparseConversionError(RuntimeError):
    """
    Raised when an Android sparse image cannot be converted.
    """


class SparseConverter:
    """
    Low-level simg2img runner owned by TreeForge Extraction.

    The converter performs only sparse-container conversion.

    Its temporary output exists beside the requested persistent destination and
    is atomically renamed into that destination after successful validation.
    """

    DEFAULT_EXECUTABLE: str | None = None

    def __init__(
        self,
        executable: str | Path = DEFAULT_EXECUTABLE,
    ) -> None:
        if executable is None:
            executable = AndroidHostTools().simg2img

        self._executable = executable

    @property
    def executable(
        self,
    ) -> str | Path:
        return self._executable

    def resolve_executable(
        self,
    ) -> Path:
        executable = Path(
            self._executable
        )

        if executable.parent != Path("."):
            if not executable.exists():
                raise FileNotFoundError(
                    "simg2img executable does not exist: "
                    f"{executable}"
                )

            if not executable.is_file():
                raise FileNotFoundError(
                    "simg2img executable is not a file: "
                    f"{executable}"
                )

            if not os.access(
                executable,
                os.X_OK,
            ):
                raise PermissionError(
                    "simg2img executable is not executable: "
                    f"{executable}"
                )

            return executable.resolve()

        resolved = shutil.which(
            str(
                self._executable
            )
        )

        if resolved is None:
            raise FileNotFoundError(
                "simg2img was not found in PATH"
            )

        return Path(
            resolved
        )

    def convert(
        self,
        source: Path,
        destination: Path,
    ) -> Path:
        source = Path(
            source
        )

        destination = Path(
            destination
        )

        self._validate_source(
            source
        )

        self._validate_destination(
            destination
        )

        executable = (
            self.resolve_executable()
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self._create_temporary_path(
                destination
            )
        )

        try:
            command = (
                self.build_command(
                    executable=executable,
                    source=source,
                    destination=temporary_path,
                )
            )

            self._run(
                command
            )

            self._validate_output(
                temporary_path
            )

            temporary_path.replace(
                destination
            )

        except BaseException:
            temporary_path.unlink(
                missing_ok=True,
            )

            raise

        return destination

    @staticmethod
    def build_command(
        executable: Path,
        source: Path,
        destination: Path,
    ) -> tuple[
        str,
        ...,
    ]:
        return (
            str(
                executable
            ),
            str(
                source
            ),
            str(
                destination
            ),
        )

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> None:
        if not source.exists():
            raise FileNotFoundError(
                f"Sparse image does not exist: {source}"
            )

        if source.is_dir():
            raise IsADirectoryError(
                "Sparse image source is a directory: "
                f"{source}"
            )

        if not source.is_file():
            raise SparseConversionError(
                "Sparse image source is not a regular file: "
                f"{source}"
            )

    @staticmethod
    def _validate_destination(
        destination: Path,
    ) -> None:
        if (
            destination.exists()
            and destination.is_dir()
        ):
            raise IsADirectoryError(
                "Raw image destination is a directory: "
                f"{destination}"
            )

    @staticmethod
    def _create_temporary_path(
        destination: Path,
    ) -> Path:
        (
            file_descriptor,
            temporary_name,
        ) = tempfile.mkstemp(
            prefix=(
                f".{destination.name}."
            ),
            suffix=".tmp",
            dir=destination.parent,
        )

        os.close(
            file_descriptor
        )

        temporary_path = Path(
            temporary_name
        )

        # simg2img creates the output itself.
        temporary_path.unlink()

        return temporary_path

    @staticmethod
    def _run(
        command: Sequence[
            str
        ],
    ) -> None:
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )

        except OSError as error:
            raise SparseConversionError(
                f"Unable to execute simg2img: {error}"
            ) from error

        if result.returncode == 0:
            return

        details = (
            result.stderr.strip()
            or result.stdout.strip()
            or "no diagnostic output"
        )

        raise SparseConversionError(
            "simg2img conversion failed "
            f"with exit code {result.returncode}: "
            f"{details}"
        )

    @staticmethod
    def _validate_output(
        output: Path,
    ) -> None:
        if not output.exists():
            raise SparseConversionError(
                "simg2img completed without creating "
                "an output image"
            )

        if not output.is_file():
            raise SparseConversionError(
                "simg2img output is not a regular file"
            )

        if (
            output.stat().st_size
            == 0
        ):
            raise SparseConversionError(
                "simg2img produced an empty output image"
            )


class SparseConverterLike(
    Protocol,
):
    @property
    def executable(
        self,
    ) -> str | Path:
        ...

    def resolve_executable(
        self,
    ) -> Path:
        ...

    def convert(
        self,
        source: Path,
        destination: Path,
    ) -> Path:
        ...


class SparseImageExtractionError(
    RuntimeError,
):
    """
    Raised when a canonical sparse image cannot be converted to raw.
    """


class SparseImageExtractor:
    """
    Convert one canonical sparse image into a persistent raw artifact.

    The sparse artifact remains in AndroidExtractionResult and becomes the
    immediate parent of the raw artifact.
    """

    HASH_CHUNK_SIZE = (
        1024 * 1024
    )

    def __init__(
        self,
        *,
        converter: (
            SparseConverterLike
            | None
        ) = None,
    ) -> None:
        self._converter = (
            converter
            if converter is not None
            else SparseConverter()
        )

    def extract(
        self,
        parent: ExtractedArtifact,
        destination: Path,
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
            raise SparseImageExtractionError(
                "sparse parent must be a file artifact"
            )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        if (
            destination.exists()
            and destination.is_dir()
        ):
            raise IsADirectoryError(
                "raw image destination is a directory: "
                f"{destination}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if destination.exists():
            destination.unlink()

        try:
            executable = (
                self._converter.resolve_executable()
            )

            converted = (
                self._converter.convert(
                    parent.path,
                    destination,
                )
            )

        except Exception as error:
            raise SparseImageExtractionError(
                "Unable to convert sparse extraction "
                f"artifact: {parent.path}"
            ) from error

        converted = Path(
            converted
        )

        if not converted.exists():
            raise SparseImageExtractionError(
                "Sparse conversion did not create "
                f"its expected output: {converted}"
            )

        if not converted.is_file():
            raise SparseImageExtractionError(
                "Sparse conversion output is not "
                f"a regular file: {converted}"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=converted,
            kind=ExtractionArtifactKind.FILE,
            operation=(
                ExtractionOperation
                .SPARSE_TO_RAW
            ),
            semantic_name=(
                parent.semantic_name
            ),
            parent=parent,
            tool=ExtractionToolEvidence(
                name="simg2img",
                executable=str(
                    executable
                ),
            ),
            content_sha256=(
                self._sha256_file(
                    converted
                )
            ),
            size_bytes=(
                converted.stat().st_size
            ),
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