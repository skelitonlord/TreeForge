from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class DebugfsExtractionError(
    RuntimeError,
):
    """
    Raised when read-only debugfs materialization cannot complete.
    """


class DebugfsExtractionRunner:
    """
    Minimal read-only debugfs runner owned by Extraction.

    This runner provides only the capabilities required to physically
    materialize an ext-family filesystem image:

    - resolve the debugfs executable;
    - construct a read-only debugfs command;
    - safely quote debugfs command arguments;
    - recursively dump a directory to a host destination.

    Filesystem inspection, stat parsing, path existence checks, metadata
    traversal, xattr collection, and higher-level filesystem interpretation
    remain outside Extraction.
    """

    DEFAULT_EXECUTABLE = "debugfs"

    def __init__(
        self,
        executable: str | Path = DEFAULT_EXECUTABLE,
    ) -> None:
        self._executable = executable

    @property
    def executable(
        self,
    ) -> str | Path:
        """
        Return the configured debugfs executable.
        """

        return self._executable

    def resolve_executable(
        self,
    ) -> Path:
        """
        Resolve the configured debugfs executable.
        """

        executable = Path(
            self._executable
        )

        if executable.parent != Path("."):
            if not executable.exists():
                raise FileNotFoundError(
                    "debugfs executable does not exist: "
                    f"{executable}"
                )

            if not executable.is_file():
                raise FileNotFoundError(
                    "debugfs executable is not a file: "
                    f"{executable}"
                )

            if not os.access(
                executable,
                os.X_OK,
            ):
                raise PermissionError(
                    "debugfs executable is not executable: "
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
                "debugfs was not found in PATH"
            )

        return Path(
            resolved
        )

    def rdump(
        self,
        image: Path,
        source: str,
        destination: Path,
    ) -> str:
        """
        Recursively materialize one directory from an ext-family image.

        debugfs remains read-only with respect to the source image.
        """

        normalized_image = Path(
            image
        )

        self._validate_image(
            normalized_image
        )

        normalized_source = (
            self._normalize_filesystem_path(
                source
            )
        )

        normalized_destination = Path(
            destination
        )

        if (
            normalized_destination.exists()
            and not normalized_destination.is_dir()
        ):
            raise NotADirectoryError(
                "debugfs extraction destination is not a directory: "
                f"{normalized_destination}"
            )

        normalized_destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        request = (
            "rdump "
            f"{self.quote_argument(normalized_source)} "
            f"{self.quote_argument(str(normalized_destination))}"
        )

        return self.run(
            normalized_image,
            request,
        )

    def run(
        self,
        image: Path,
        request: str,
    ) -> str:
        """
        Execute one read-only debugfs request.
        """

        normalized_image = Path(
            image
        )

        self._validate_image(
            normalized_image
        )

        normalized_request = (
            self._normalize_request(
                request
            )
        )

        executable = (
            self.resolve_executable()
        )

        command = self.build_command(
            executable=executable,
            image=normalized_image,
            request=normalized_request,
        )

        result = self._run_process(
            command
        )

        return result.stdout

    @staticmethod
    def build_command(
        executable: Path,
        image: Path,
        request: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Build a read-only debugfs command.
        """

        return (
            str(
                executable
            ),
            "-R",
            request,
            str(
                image
            ),
        )

    @staticmethod
    def quote_argument(
        value: str,
    ) -> str:
        """
        Quote one argument for debugfs's internal command language.
        """

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        escaped = (
            value
            .replace(
                "\\",
                "\\\\",
            )
            .replace(
                '"',
                '\\"',
            )
        )

        return (
            f'"{escaped}"'
        )

    @staticmethod
    def _validate_image(
        image: Path,
    ) -> None:
        if not image.exists():
            raise FileNotFoundError(
                "Filesystem image does not exist: "
                f"{image}"
            )

        if image.is_dir():
            raise IsADirectoryError(
                "Filesystem image is a directory: "
                f"{image}"
            )

        if not image.is_file():
            raise DebugfsExtractionError(
                "Filesystem image is not a regular file: "
                f"{image}"
            )

    @staticmethod
    def _normalize_request(
        request: str,
    ) -> str:
        if not isinstance(
            request,
            str,
        ):
            raise TypeError(
                "debugfs request must be a string"
            )

        normalized = (
            request.strip()
        )

        if not normalized:
            raise ValueError(
                "debugfs request cannot be empty"
            )

        return normalized

    @staticmethod
    def _normalize_filesystem_path(
        path: str,
    ) -> str:
        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "debugfs filesystem path must be a string"
            )

        normalized = (
            path.strip()
        )

        if not normalized:
            raise ValueError(
                "debugfs filesystem path cannot be empty"
            )

        if "\x00" in normalized:
            raise ValueError(
                "debugfs filesystem path cannot contain null bytes"
            )

        if (
            "\n" in normalized
            or "\r" in normalized
        ):
            raise ValueError(
                "debugfs filesystem path cannot contain newlines"
            )

        return normalized

    @staticmethod
    def _run_process(
        command: Sequence[
            str
        ],
    ) -> subprocess.CompletedProcess[
        str
    ]:
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )

        except OSError as error:
            raise DebugfsExtractionError(
                f"Unable to execute debugfs: {error}"
            ) from error

        if result.returncode == 0:
            return result

        details = (
            result.stderr.strip()
            or result.stdout.strip()
            or "no diagnostic output"
        )

        raise DebugfsExtractionError(
            "debugfs command failed "
            f"with exit code {result.returncode}: "
            f"{details}"
        )