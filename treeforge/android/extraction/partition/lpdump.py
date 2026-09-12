from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from treeforge.android.toolchain import AndroidHostTools


class LpdumpError(RuntimeError):
    """
    Base error raised when lpdump cannot inspect a super image.
    """


class LpdumpNotFoundError(LpdumpError):
    """
    Raised when the configured lpdump executable cannot be found.
    """


class LpdumpExecutionError(LpdumpError):
    """
    Raised when lpdump exits unsuccessfully.
    """


@dataclass(frozen=True)
class LpdumpResult:
    """
    Captured result from an lpdump command.

    Attributes:
        source:
            Super image inspected by lpdump.

        command:
            Exact command arguments supplied to the subprocess runner.

        stdout:
            Standard output emitted by lpdump.

        stderr:
            Standard error emitted by lpdump.

        returncode:
            Process exit status.
    """

    source: Path
    command: tuple[str, ...]
    stdout: str
    stderr: str
    returncode: int


CompletedProcess = subprocess.CompletedProcess[str]

CommandRunner = Callable[
    [Sequence[str]],
    CompletedProcess,
]

ExecutableResolver = Callable[
    [str],
    str | None,
]


class LpdumpRunner:
    """
    Execute Android's lpdump tool against a super image.

    This class is responsible only for:

    - validating the source image;
    - resolving the lpdump executable;
    - constructing the command;
    - executing the process;
    - returning captured output;
    - translating low-level process failures into TreeForge errors.

    Parsing lpdump output belongs in a separate component.
    """

    def __init__(
        self,
        *,
        executable: str | None = None,
        command_runner: CommandRunner | None = None,
        executable_resolver: ExecutableResolver | None = None,
    ) -> None:
        if executable is None:
            executable = AndroidHostTools().lpdump

        self._executable = self._validate_executable_name(
            executable
        )

        self._command_runner = (
            command_runner
            if command_runner is not None
            else self._run_command
        )

        self._executable_resolver = (
            executable_resolver
            if executable_resolver is not None
            else which
        )

    @property
    def executable(self) -> str:
        """
        Return the configured lpdump executable name or path.
        """

        return self._executable

    def inspect(
        self,
        source: Path,
    ) -> LpdumpResult:
        """
        Run lpdump against a super image.

        Args:
            source:
                Path to a raw super partition image.

        Returns:
            Captured lpdump process output.

        Raises:
            TypeError:
                If source is not a pathlib.Path.

            FileNotFoundError:
                If source does not exist.

            ValueError:
                If source is not a regular file.

            LpdumpNotFoundError:
                If the executable cannot be located.

            LpdumpExecutionError:
                If the command cannot be started or exits unsuccessfully.
        """

        normalized_source = self._validate_source(
            source
        )

        executable = self._resolve_executable()

        command = (
            executable,
            str(normalized_source),
        )

        try:
            completed = self._command_runner(
                command
            )
        except OSError as error:
            raise LpdumpExecutionError(
                f"Unable to execute lpdump for "
                f"{normalized_source}"
            ) from error
        except Exception as error:
            raise LpdumpExecutionError(
                f"Unexpected lpdump execution failure for "
                f"{normalized_source}"
            ) from error

        result = LpdumpResult(
            source=normalized_source,
            command=tuple(command),
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )

        if result.returncode != 0:
            message = result.stderr.strip()

            if not message:
                message = result.stdout.strip()

            if not message:
                message = (
                    f"lpdump exited with status "
                    f"{result.returncode}"
                )

            raise LpdumpExecutionError(
                f"Unable to inspect super image "
                f"{normalized_source}: {message}"
            )

        return result

    def _resolve_executable(self) -> str:
        """
        Resolve the configured executable.

        Explicit paths are accepted directly after existence validation.
        Plain executable names are resolved through PATH.
        """

        executable_path = Path(
            self._executable
        )

        if executable_path.parent != Path("."):
            if not executable_path.exists():
                raise LpdumpNotFoundError(
                    f"lpdump executable does not exist: "
                    f"{executable_path}"
                )

            if not executable_path.is_file():
                raise LpdumpNotFoundError(
                    f"lpdump executable is not a file: "
                    f"{executable_path}"
                )

            return str(executable_path)

        resolved = self._executable_resolver(
            self._executable
        )

        if resolved is None:
            raise LpdumpNotFoundError(
                f"Unable to locate lpdump executable: "
                f"{self._executable}"
            )

        return resolved

    @staticmethod
    def _validate_executable_name(
        executable: str,
    ) -> str:
        """
        Validate and normalize the configured executable.
        """

        if not isinstance(
            executable,
            str,
        ):
            raise TypeError(
                "executable must be a string"
            )

        normalized = executable.strip()

        if not normalized:
            raise ValueError(
                "executable cannot be empty"
            )

        if any(
            character in normalized
            for character in ("\x00", "\n", "\r")
        ):
            raise ValueError(
                "executable contains unsafe characters"
            )

        return normalized

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> Path:
        """
        Validate the supplied super image.
        """

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if not source.is_file():
            raise ValueError(
                f"Super image source must be a file: "
                f"{source}"
            )

        return source

    @staticmethod
    def _run_command(
        command: Sequence[str],
    ) -> CompletedProcess:
        """
        Execute lpdump without invoking a shell.
        """

        return subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
        )