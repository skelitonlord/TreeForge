from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Sequence

from treeforge.android.filesystem.debugfs.stat import (
    DebugfsStatParseError,
    DebugfsStatParser,
)


class DebugfsError(RuntimeError):
    """
    Raised when a debugfs command cannot be completed.
    """


class DebugfsRunner:
    """
    Execute read-only debugfs commands against ext-family filesystem images.

    The runner supports low-level command execution as well as common
    read-only image operations:

    - stat a path;
    - test whether a path exists;
    - list a directory;
    - extract one file;
    - recursively extract one directory;
    - read one file as bytes;
    - read one file as text.

    Parsing richer debugfs output remains delegated to dedicated parsers.
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
        """Return the configured debugfs executable."""

        return self._executable

    def resolve_executable(
        self,
    ) -> Path:
        """
        Resolve the configured debugfs executable.

        A plain executable name is searched for in PATH. Values containing a
        directory component are treated as explicit paths.
        """

        executable = Path(
            self._executable,
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
                self._executable,
            ),
        )

        if resolved is None:
            raise FileNotFoundError(
                "debugfs was not found in PATH"
            )

        return Path(
            resolved,
        )

    def run(
        self,
        image: Path,
        request: str,
    ) -> str:
        """
        Execute one read-only debugfs request.

        Args:
            image:
                Raw ext-family filesystem image.

            request:
                Command passed to debugfs through its ``-R`` option.

        Returns:
            Standard output produced by debugfs.
        """

        normalized_image = Path(
            image,
        )

        self._validate_image(
            normalized_image,
        )

        normalized_request = (
            self._normalize_request(
                request,
            )
        )

        executable = self.resolve_executable()

        command = self.build_command(
            executable=executable,
            image=normalized_image,
            request=normalized_request,
        )

        result = self._run_process(
            command,
        )

        return result.stdout

    def stat(
        self,
        image: Path,
        path: str,
    ) -> str:
        """
        Run the debugfs ``stat`` command for a filesystem path.
        """

        normalized_path = (
            self._normalize_filesystem_path(
                path,
            )
        )

        return self.run(
            image,
            (
                "stat "
                f"{self.quote_argument(normalized_path)}"
            ),
        )

    def exists(
        self,
        image: Path,
        path: str,
    ) -> bool:
        """
        Return whether a path exists inside an ext-family image.

        Existence is confirmed by parsing the complete ``stat`` response.
        Missing or malformed path responses return ``False``. Image,
        executable, and argument validation errors continue to propagate.
        """

        normalized_path = (
            self._normalize_filesystem_path(
                path,
            )
        )

        try:
            output = self.stat(
                image,
                normalized_path,
            )
        except DebugfsError:
            return False

        try:
            DebugfsStatParser.parse(
                output,
            )
        except DebugfsStatParseError:
            return False

        return True

    def list_directory(
        self,
        image: Path,
        path: str = "/",
    ) -> str:
        """
        Run a detailed debugfs directory listing.
        """

        normalized_path = (
            self._normalize_filesystem_path(
                path,
            )
        )

        return self.run(
            image,
            (
                "ls -l "
                f"{self.quote_argument(normalized_path)}"
            ),
        )

    def dump(
        self,
        image: Path,
        source: str,
        destination: Path,
    ) -> Path:
        """
        Extract one file from an image to a host destination.

        The filesystem image remains read-only. Existing destination content
        is replaced by debugfs.
        """

        normalized_source = (
            self._normalize_filesystem_path(
                source,
            )
        )

        normalized_destination = Path(
            destination,
        )

        if (
            normalized_destination.exists()
            and normalized_destination.is_dir()
        ):
            raise IsADirectoryError(
                "debugfs file destination is a directory: "
                f"{normalized_destination}"
            )

        normalized_destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.run(
            image,
            (
                "dump "
                f"{self.quote_argument(normalized_source)} "
                f"{self.quote_argument(str(normalized_destination))}"
            ),
        )

        if not normalized_destination.exists():
            raise DebugfsError(
                "debugfs dump did not create its destination: "
                f"{normalized_destination}"
            )

        if not normalized_destination.is_file():
            raise DebugfsError(
                "debugfs dump destination is not a regular file: "
                f"{normalized_destination}"
            )

        return normalized_destination

    def read_bytes(
        self,
        image: Path,
        path: str,
    ) -> bytes:
        """
        Read one file from an image as bytes.

        A temporary disk-backed destination is used so complete file contents
        are never accumulated through debugfs standard output.
        """

        normalized_path = (
            self._normalize_filesystem_path(
                path,
            )
        )

        with TemporaryDirectory(
            prefix="treeforge-debugfs-read-",
        ) as temporary_directory:
            destination = (
                Path(
                    temporary_directory,
                )
                / "content"
            )

            dumped = self.dump(
                image,
                normalized_path,
                destination,
            )

            return dumped.read_bytes()

    def read_text(
        self,
        image: Path,
        path: str,
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
    ) -> str:
        """
        Read and decode one text file from an image.
        """

        if not isinstance(
            encoding,
            str,
        ):
            raise TypeError(
                "encoding must be a string"
            )

        if not encoding:
            raise ValueError(
                "encoding cannot be empty"
            )

        if not isinstance(
            errors,
            str,
        ):
            raise TypeError(
                "errors must be a string"
            )

        if not errors:
            raise ValueError(
                "errors cannot be empty"
            )

        return self.read_bytes(
            image,
            path,
        ).decode(
            encoding=encoding,
            errors=errors,
        )

    def rdump(
        self,
        image: Path,
        source: str,
        destination: Path,
    ) -> str:
        """
        Recursively extract a directory from an image.

        ``debugfs`` remains in its default read-only filesystem mode. The
        command writes only to the host destination.
        """

        normalized_source = (
            self._normalize_filesystem_path(
                source,
            )
        )

        normalized_destination = Path(
            destination,
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

        return self.run(
            image,
            (
                "rdump "
                f"{self.quote_argument(normalized_source)} "
                f"{self.quote_argument(str(normalized_destination))}"
            ),
        )

    @staticmethod
    def build_command(
        executable: Path,
        image: Path,
        request: str,
    ) -> tuple[str, ...]:
        """
        Build a read-only debugfs command.
        """

        return (
            str(
                executable,
            ),
            "-R",
            request,
            str(
                image,
            ),
        )

    @staticmethod
    def quote_argument(
        value: str,
    ) -> str:
        """
        Quote one argument for the debugfs request parser.

        This quoting applies to debugfs's internal command language. The
        subprocess itself executes without ``shell=True``.
        """

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

        return f'"{escaped}"'

    @staticmethod
    def _validate_image(
        image: Path,
    ) -> None:
        """Validate an ext-family filesystem image."""

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
            raise DebugfsError(
                "Filesystem image is not a regular file: "
                f"{image}"
            )

    @staticmethod
    def _normalize_request(
        request: str,
    ) -> str:
        """Validate and normalize one debugfs request."""

        if not isinstance(
            request,
            str,
        ):
            raise TypeError(
                "debugfs request must be a string"
            )

        normalized = request.strip()

        if not normalized:
            raise ValueError(
                "debugfs request cannot be empty"
            )

        return normalized

    @staticmethod
    def _normalize_filesystem_path(
        path: str,
    ) -> str:
        """Validate and normalize one path inside an image."""

        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "debugfs filesystem path must be a string"
            )

        normalized = path.strip()

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
        command: Sequence[str],
    ) -> subprocess.CompletedProcess[str]:
        """Execute one debugfs subprocess."""

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            raise DebugfsError(
                f"Unable to execute debugfs: {error}"
            ) from error

        if result.returncode == 0:
            return result

        details = (
            result.stderr.strip()
            or result.stdout.strip()
            or "no diagnostic output"
        )

        raise DebugfsError(
            "debugfs command failed "
            f"with exit code {result.returncode}: "
            f"{details}"
        )