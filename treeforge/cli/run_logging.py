from __future__ import annotations

import re
import sys
import traceback

from datetime import datetime
from pathlib import Path
from typing import TextIO


_ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)


class _TerminalTee:
    """
    Mirror one text stream to the real terminal and a plain-text transcript.

    Terminal behavior is preserved through the primary stream. ANSI control
    sequences are removed only from the persisted transcript.
    """

    def __init__(
        self,
        primary: TextIO,
        transcript: TextIO,
    ) -> None:
        self._primary = primary
        self._transcript = transcript

    def write(
        self,
        value: str,
    ) -> int:
        written = self._primary.write(
            value
        )

        self._transcript.write(
            _ANSI_ESCAPE_RE.sub(
                "",
                value,
            )
        )

        return written

    def write_ephemeral(
        self,
        value: str,
    ) -> int:
        """
        Write transient terminal UI without persisting it to the transcript.

        Live progress bars, cursor movement, and similar redrawable output
        belong only to the interactive terminal. Semantic completion lines
        and ordinary CLI output continue through write() and are retained.
        """

        return self._primary.write(
            value
        )

    def flush(
        self,
    ) -> None:
        self._primary.flush()
        self._transcript.flush()

    def isatty(
        self,
    ) -> bool:
        return self._primary.isatty()

    @property
    def encoding(
        self,
    ):
        return getattr(
            self._primary,
            "encoding",
            "utf-8",
        )

    @property
    def errors(
        self,
    ):
        return getattr(
            self._primary,
            "errors",
            None,
        )

    def fileno(
        self,
    ) -> int:
        return self._primary.fileno()


class StageTerminalCapture:
    """
    Persist the user-visible terminal stream for one TreeForge stage run.

    stdout and stderr continue to flow to their original terminal streams
    while a plain-text copy is written to ``logs/terminal.log``.

    ``logs/verbose.log`` is a distinct stable surface reserved for TreeForge's
    richer structured diagnostic logging.
    """

    TERMINAL_LOG_NAME = "terminal.log"
    VERBOSE_LOG_NAME = "verbose.log"

    def __init__(
        self,
        stage_root: Path,
    ) -> None:
        if not isinstance(
            stage_root,
            Path,
        ):
            raise TypeError(
                "stage_root must be a pathlib.Path"
            )

        self.stage_root = stage_root
        self.logs_root = (
            stage_root
            / "logs"
        )

        self.terminal_log_path = (
            self.logs_root
            / self.TERMINAL_LOG_NAME
        )

        self.verbose_log_path = (
            self.logs_root
            / self.VERBOSE_LOG_NAME
        )

        self._stream: TextIO | None = None
        self._original_stdout: TextIO | None = None
        self._original_stderr: TextIO | None = None
        self._started = False

    def start(
        self,
    ) -> None:
        if self._started:
            return

        self.logs_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._stream = (
            self.terminal_log_path.open(
                "w",
                encoding="utf-8",
                buffering=1,
            )
        )

        self.verbose_log_path.write_text(
            (
                "TreeForge verbose diagnostic log\n"
                f"Started: {datetime.now().astimezone().isoformat()}\n"
                "Command: "
                + " ".join(
                    sys.argv
                )
                + "\n"
                "Working directory: "
                + str(
                    Path.cwd()
                )
                + "\n"
                + "-" * 72
                + "\n"
            ),
            encoding="utf-8",
        )

        self._stream.write(
            "TreeForge terminal transcript\n"
        )
        self._stream.write(
            (
                "Started: "
                f"{datetime.now().astimezone().isoformat()}\n"
            )
        )
        self._stream.write(
            (
                "Command: "
                + " ".join(
                    sys.argv
                )
                + "\n"
            )
        )
        self._stream.write(
            (
                "Working directory: "
                f"{Path.cwd()}\n"
            )
        )
        self._stream.write(
            "-" * 72
            + "\n"
        )
        self._stream.flush()

        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

        sys.stdout = _TerminalTee(
            self._original_stdout,
            self._stream,
        )
        sys.stderr = _TerminalTee(
            self._original_stderr,
            self._stream,
        )

        self._started = True

    def log_exception(
        self,
        error: BaseException,
        *,
        context: str | None = None,
    ) -> None:
        """
        Persist one complete diagnostic exception record.

        The terminal remains concise. The verbose log preserves the concrete
        exception type, message, traceback, and chained causes/contexts.
        """

        if not isinstance(
            error,
            BaseException,
        ):
            raise TypeError(
                "error must be a BaseException"
            )

        if (
            context is not None
            and not isinstance(
                context,
                str,
            )
        ):
            raise TypeError(
                "context must be a string or None"
            )

        self.logs_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        traceback_text = "".join(
            traceback.TracebackException
            .from_exception(
                error,
                capture_locals=False,
            )
            .format(
                chain=True
            )
        )

        with self.verbose_log_path.open(
            "a",
            encoding="utf-8",
        ) as stream:
            stream.write(
                "\n=== EXCEPTION ===\n"
            )
            stream.write(
                "Timestamp: "
                f"{datetime.now().astimezone().isoformat()}\n"
            )

            if context is not None:
                stream.write(
                    f"Context: {context}\n"
                )

            stream.write(
                "Type: "
                f"{type(error).__module__}."
                f"{type(error).__qualname__}\n"
            )
            stream.write(
                f"Message: {error}\n"
            )
            stream.write(
                "\n"
            )
            stream.write(
                traceback_text
            )

            if (
                traceback_text
                and not traceback_text.endswith(
                    "\n"
                )
            ):
                stream.write(
                    "\n"
                )

            stream.flush()


    def close(
        self,
    ) -> None:
        if not self._started:
            return

        assert self._stream is not None
        assert self._original_stdout is not None
        assert self._original_stderr is not None

        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

        self._stream.write(
            "-" * 72
            + "\n"
        )
        self._stream.write(
            (
                "Finished: "
                f"{datetime.now().astimezone().isoformat()}\n"
            )
        )

        self._stream.flush()
        self._stream.close()

        with self.verbose_log_path.open(
            "a",
            encoding="utf-8",
        ) as verbose_stream:
            verbose_stream.write(
                "-" * 72
                + "\n"
            )
            verbose_stream.write(
                "Finished: "
                f"{datetime.now().astimezone().isoformat()}\n"
            )

        self._started = False
