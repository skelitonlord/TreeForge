from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import unicodedata

import typer

from treeforge.core.progress import (
    ProgressEvent,
    ProgressState,
)


_LIVE_PROGRESS_ROWS = 2
_live_progress_active = False


def _write_ephemeral(
    value: str,
) -> None:
    """
    Write transient terminal UI without treating it as semantic CLI output.

    StageTerminalCapture exposes ``write_ephemeral`` on its stdout tee.
    Ordinary stdout streams do not, so direct terminal behavior remains
    unchanged when transcript capture is inactive.
    """

    writer = getattr(
        sys.stdout,
        "write_ephemeral",
        None,
    )

    if writer is None:
        sys.stdout.write(
            value
        )
        return

    writer(
        value
    )


def _terminal_cell_width(
    value: str,
) -> int:
    """
    Return terminal display-cell width without depending on string length.

    Combining/control characters consume no cells. East-Asian wide/fullwidth
    characters consume two. Ordinary TreeForge paths and identifiers consume
    one. Live rendering must reason in terminal cells because one unexpected
    physical wrap invalidates the fixed-height cursor block.
    """

    width = 0

    for character in value:
        if character in ("\n", "\r"):
            continue

        if unicodedata.combining(
            character
        ):
            continue

        category = unicodedata.category(
            character
        )

        if category.startswith("C"):
            continue

        width += (
            2
            if unicodedata.east_asian_width(
                character
            ) in ("W", "F")
            else 1
        )

    return width


def _truncate_terminal_cells(
    value: str,
    width: int,
) -> str:
    """
    Truncate one value to at most ``width`` terminal display cells.
    """

    if width <= 0:
        return ""

    if _terminal_cell_width(
        value
    ) <= width:
        return value

    ellipsis = "..."

    ellipsis_width = (
        _terminal_cell_width(
            ellipsis
        )
    )

    if width <= ellipsis_width:
        return ellipsis[:width]

    target = (
        width
        - ellipsis_width
    )

    result: list[str] = []
    used = 0

    for character in value:
        character_width = (
            _terminal_cell_width(
                character
            )
        )

        if (
            used
            + character_width
            > target
        ):
            break

        result.append(
            character
        )

        used += character_width

    return (
        "".join(result)
        + ellipsis
    )


def fit_progress_line(
    line: str,
) -> str:
    """
    Keep one live progress update on exactly one physical terminal row.

    Producers may supply complete canonical paths, requirement IDs, ELF
    identities, etc. Only the TTY renderer truncates them.
    """

    columns = (
        shutil.get_terminal_size(
            fallback=(80, 24),
        ).columns
    )

    # Reserve one physical cell so terminals with edge-wrap behavior never
    # push the cursor onto a hidden sixth row.
    width = max(
        1,
        columns - 1,
    )

    return _truncate_terminal_cells(
        line,
        width,
    )


def clear_live_progress_block() -> None:
    """
    Remove the current fixed-height TTY activity block without scrolling.
    """

    global _live_progress_active

    if not _live_progress_active:
        return

    _write_ephemeral(
        "\r"
        + "\x1b[1A" * (
            _LIVE_PROGRESS_ROWS - 1
        )
    )

    for index in range(
        _LIVE_PROGRESS_ROWS
    ):
        _write_ephemeral(
            "\r\x1b[2K"
        )

        if index < (
            _LIVE_PROGRESS_ROWS - 1
        ):
            _write_ephemeral(
                "\x1b[1B"
            )

    _write_ephemeral(
        "\x1b[1A" * (
            _LIVE_PROGRESS_ROWS - 1
        )
        + "\r"
    )

    sys.stdout.flush()

    _live_progress_active = False


def progress_bar_line(
    event: ProgressEvent,
) -> tuple[str, bool]:
    """
    Build the stable top row for one semantic progress observation.
    """

    if event.total is None:
        if (
            event.stage == "Discover Factory Image"
            and event.processed is not None
        ):
            current = event.processed
            progress_noun = "discovered"

        elif event.stage == "Expand Physical Artifacts":
            current = (
                event.processed
                if event.processed is not None
                else (
                    0
                    if event.current is None
                    else event.current
                )
            )
            progress_noun = "transformations"

        else:
            current = (
                0
                if event.current is None
                else event.current
            )
            progress_noun = "completed"

        return (
            (
                f"[{event.stage}] "
                f"dynamic  "
                f"{progress_noun}={current}"
            ),
            False,
        )

    total = event.total

    current = (
        0
        if event.current is None
        else event.current
    )

    width = 20

    filled = (
        width
        if total == 0
        else min(
            width,
            int(
                width
                * current
                / total
            ),
        )
    )

    bar = (
        "█" * filled
        + "░" * (
            width - filled
        )
    )

    scope_complete = (
        event.state
        is ProgressState.COMPLETE
        and current == total
    )

    line = (
        f"[{event.stage}] "
        f"{bar} "
        f"{current}/{total}"
    )

    if scope_complete:
        completion_label = (
            event.subject
            if event.subject is not None
            else (
                event.detail
                if event.detail is not None
                else None
            )
        )

        line += " [complete]"

        if completion_label is not None:
            line += (
                " — "
                + completion_label
            )

    return (
        line,
        scope_complete,
    )


def format_byte_size(
    size_bytes: int,
) -> str:
    """
    Render a byte count compactly for terminal progress.
    """

    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
    ):
        raise TypeError(
            "size_bytes must be an int"
        )

    if size_bytes < 0:
        raise ValueError(
            "size_bytes cannot be negative"
        )

    units = (
        "B",
        "KiB",
        "MiB",
        "GiB",
        "TiB",
    )

    value = float(
        size_bytes
    )

    for unit in units:
        if (
            value < 1024.0
            or unit == units[-1]
        ):
            if unit == "B":
                return f"{size_bytes} B"

            return f"{value:.2f} {unit}"

        value /= 1024.0

    raise AssertionError(
        "unreachable byte-size unit"
    )


def activity_lines(
    event: ProgressEvent,
) -> tuple[str, str, str, str]:
    """
    Render structured semantic activity supplied by the producer.
    """

    subject = (
        event.subject
        if event.subject is not None
        else "-"
    )

    operation = (
        event.operation
        if event.operation is not None
        else (
            event.detail
            if event.detail is not None
            else event.state.value
        )
    )

    item = (
        event.item
        if event.item is not None
        else (
            event.detail
            if (
                event.detail is not None
                and event.operation is None
            )
            else "-"
        )
    )

    processed = (
        "-"
        if event.processed is None
        else f"{event.processed:,}"
    )

    if (
        event.stage == "Discover Factory Image"
        and event.operation == "hashing provider source"
        and event.current is not None
        and event.total is not None
    ):
        activity = (
            f"{format_byte_size(event.current)}"
            " / "
            f"{format_byte_size(event.total)}"
        )
    elif (
        event.stage == "Discover Factory Image"
        and event.processed is not None
    ):
        activity = (
            f"{event.processed:,} artifacts discovered"
        )
    elif (
        event.stage == "Materialize Source Artifacts"
        and event.current is not None
        and event.total is not None
    ):
        activity = (
            f"{event.current:,}/{event.total:,} sources"
        )
    elif event.stage == "Expand Physical Artifacts":
        parts = []

        if event.processed is not None:
            parts.append(
                f"{event.processed:,} transformations"
            )

        if event.detail is not None:
            match = re.search(
                r"queued_(?:before|after)=(\\d+)",
                event.detail,
            )

            if match is not None:
                parts.append(
                    f"{int(match.group(1)):,} queued"
                )

        if event.produced is not None:
            parts.append(
                f"{event.produced:,} produced"
            )

        activity = (
            " · ".join(parts)
            if parts
            else "-"
        )

    elif (
        event.input_size_bytes is not None
        and event.output_size_bytes is not None
    ):
        activity = (
            f"{format_byte_size(event.input_size_bytes)}"
            " -> "
            f"{format_byte_size(event.output_size_bytes)}"
        )
    elif event.output_size_bytes is not None:
        activity = (
            format_byte_size(
                event.output_size_bytes
            )
        )
    elif event.input_size_bytes is not None:
        activity = (
            format_byte_size(
                event.input_size_bytes
            )
        )
    elif event.produced is not None:
        activity = (
            f"{event.produced:,} produced"
        )
    else:
        activity = processed

    if event.stage == "Filesystem Metadata":
        subject_label = "Filesystem"
        processed_suffix = (
            ""
            if event.processed is None
            else " entries"
        )
    else:
        subject_label = "Subject"
        processed_suffix = ""

    return (
        f"  {subject_label}:  {subject}",
        f"  Operation:  {operation}",
        f"  Current:    {item}",
        (
            f"  Progress:   "
            f"{activity}"
            f"{processed_suffix}"
        ),
    )


def render_progress(
    event: ProgressEvent,
) -> None:
    """
    Render one framework-neutral TreeForge progress event.
    """

    global _live_progress_active

    progress_line, scope_complete = (
        progress_bar_line(
            event
        )
    )

    if not sys.stdout.isatty():
        parts = [
            progress_line,
        ]

        if event.subject is not None:
            parts.append(
                event.subject
            )

        if (
            event.operation is not None
            and event.operation != event.subject
        ):
            parts.append(
                event.operation
            )

        typer.echo(
            "  ".join(
                parts
            )
        )
        return

    if scope_complete:
        clear_live_progress_block()

        typer.echo(
            fit_progress_line(
                progress_line
            )
        )
        return

    detail_parts = []

    if event.subject is not None:
        detail_parts.append(
            event.subject
        )

    if (
        event.operation is not None
        and event.operation != event.subject
    ):
        detail_parts.append(
            event.operation
        )

    if (
        not detail_parts
        and event.detail is not None
    ):
        detail_parts.append(
            event.detail
        )

    if not detail_parts:
        detail_parts.append(
            event.state.value
        )

    rows = (
        progress_line,
        (
            "  "
            + " — ".join(
                detail_parts
            )
        ),
    )

    if _live_progress_active:
        clear_live_progress_block()

    _write_ephemeral(
        "\n".join(
            fit_progress_line(
                row
            )
            for row in rows
        )
    )

    sys.stdout.flush()

    _live_progress_active = True


def configure_live_progress_logging() -> None:
    """
    Keep INFO logging from corrupting live TTY progress.
    """

    if not sys.stdout.isatty():
        return

    logging.getLogger(
        "treeforge"
    ).setLevel(
        logging.WARNING
    )


def prompt_show_report() -> bool:
    """
    Ask whether to print a completed TreeForge report.
    """

    if not sys.stdout.isatty():
        return False

    try:
        terminal_path = os.ttyname(
            sys.stdout.fileno()
        )
    except (
        OSError,
        ValueError,
    ):
        return False

    try:
        with open(
            terminal_path,
            "r",
            encoding="utf-8",
            buffering=1,
        ) as terminal_input:
            while True:
                sys.stdout.write(
                    "Show report now? [y/N]: "
                )
                sys.stdout.flush()

                response = (
                    terminal_input.readline()
                    .strip()
                    .lower()
                )

                if response in (
                    "",
                    "n",
                    "no",
                ):
                    return False

                if response in (
                    "y",
                    "yes",
                ):
                    return True

                sys.stdout.write(
                    "Please answer y or n.\n"
                )
                sys.stdout.flush()

    except OSError:
        return False
