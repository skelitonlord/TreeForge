from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Protocol

from treeforge.android.toolchain import AndroidHostTools


class LpunpackError(RuntimeError):
    """
    Base error raised by the lpunpack integration layer.
    """


class LpunpackExecutableNotFoundError(
    LpunpackError
):
    """
    Raised when the configured lpunpack executable cannot be started.
    """


class LpunpackExecutionError(
    LpunpackError
):
    """
    Raised when lpunpack exits unsuccessfully.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class LpunpackResult:
    """
    Immutable result of one successful lpunpack invocation.
    """

    command: tuple[
        str,
        ...,
    ]
    returncode: int
    stdout: str
    stderr: str


class ProcessExecutorLike(
    Protocol
):
    """
    Process execution contract required by LpunpackRunner.
    """

    def run(
        self,
        command: tuple[
            str,
            ...,
        ],
    ) -> subprocess.CompletedProcess[
        str
    ]:
        """
        Execute one command and return its completed-process result.
        """


class SubprocessExecutor:
    """
    Production process executor backed by subprocess.run.
    """

    def run(
        self,
        command: tuple[
            str,
            ...,
        ],
    ) -> subprocess.CompletedProcess[
        str
    ]:
        """
        Execute a command without invoking a shell.
        """

        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )


class LpunpackRunner:
    """
    Validate and invoke the Android lpunpack host tool.

    The runner owns:

    - command construction;
    - source-image validation;
    - partition-name validation;
    - output-directory preparation;
    - process execution;
    - process failure reporting.

    It does not validate the partition images produced by lpunpack. That
    responsibility belongs to LogicalPartitionExtractor.
    """

    def __init__(
        self,
        *,
        executable: str | None = None,
        executor: ProcessExecutorLike | None = None,
    ) -> None:
        if executable is None:
            executable = AndroidHostTools().lpunpack

        if not isinstance(
            executable,
            str,
        ):
            raise TypeError(
                "executable must be a string"
            )

        if not executable.strip():
            raise ValueError(
                "executable cannot be empty"
            )

        self._executable = executable
        self._executor = (
            executor
            if executor is not None
            else SubprocessExecutor()
        )

    def run(
        self,
        source_image: Path,
        partition_names: tuple[
            str,
            ...,
        ],
        output_directory: Path,
    ) -> LpunpackResult:
        """
        Extract selected logical partitions from one super image.

        Command shape:

            lpunpack
                -p system_a
                -p vendor_a
                super.img
                output_directory
        """

        normalized_source = (
            self._validate_source_image(
                source_image
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

        command = self._build_command(
            source_image=normalized_source,
            partition_names=normalized_names,
            output_directory=normalized_output,
        )

        try:
            completed = self._executor.run(
                command
            )
        except FileNotFoundError as error:
            raise LpunpackExecutableNotFoundError(
                f"lpunpack executable was not found: "
                f"{self._executable}"
            ) from error
        except OSError as error:
            raise LpunpackExecutionError(
                f"Unable to start lpunpack: {error}"
            ) from error

        if not isinstance(
            completed,
            subprocess.CompletedProcess,
        ):
            raise LpunpackExecutionError(
                "Process executor returned an invalid result"
            )

        if completed.returncode != 0:
            raise LpunpackExecutionError(
                self._format_failure(
                    command=command,
                    returncode=completed.returncode,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
            )

        return LpunpackResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )

    def _build_command(
        self,
        *,
        source_image: Path,
        partition_names: tuple[
            str,
            ...,
        ],
        output_directory: Path,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Build one deterministic lpunpack command.
        """

        command: list[str] = [
            self._executable,
        ]

        for name in partition_names:
            command.extend(
                (
                    "-p",
                    name,
                )
            )

        command.extend(
            (
                str(
                    source_image
                ),
                str(
                    output_directory
                ),
            )
        )

        return tuple(
            command
        )

    @staticmethod
    def _validate_source_image(
        source_image: Path,
    ) -> Path:
        """
        Validate the source super image.
        """

        if not isinstance(
            source_image,
            Path,
        ):
            raise TypeError(
                "source_image must be a pathlib.Path"
            )

        if not source_image.exists():
            raise FileNotFoundError(
                f"Source image does not exist: "
                f"{source_image}"
            )

        if source_image.is_dir():
            raise IsADirectoryError(
                f"Source image cannot be a directory: "
                f"{source_image}"
            )

        if not source_image.is_file():
            raise LpunpackError(
                f"Source image must be a regular file: "
                f"{source_image}"
            )

        return source_image

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
        """
        Validate exact logical partition names.
        """

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

            seen.add(
                name
            )

        return partition_names

    @staticmethod
    def _prepare_output_directory(
        output_directory: Path,
    ) -> Path:
        """
        Validate and create the extraction output directory.
        """

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
                f"lpunpack output path must be a "
                f"directory: {output_directory}"
            )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return output_directory

    @staticmethod
    def _format_failure(
        *,
        command: tuple[
            str,
            ...,
        ],
        returncode: int,
        stdout: str | None,
        stderr: str | None,
    ) -> str:
        """
        Build a useful process-failure message.
        """

        details = (
            (stderr or "").strip()
            or (stdout or "").strip()
            or "no process output"
        )

        return (
            f"lpunpack failed with exit code "
            f"{returncode}: {details}; "
            f"command={command!r}"
        )