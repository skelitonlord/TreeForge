from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class ProgressState(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    COMPLETE = "complete"


@dataclass(
    frozen=True,
    slots=True,
)
class ProgressEvent:
    """
    Framework-neutral progress observation emitted by TreeForge work.

    Core/application code reports semantic progress only. Terminal rendering,
    logging, GUI presentation, and persistence remain caller responsibilities.
    """

    stage: str
    state: ProgressState
    current: int | None = None
    total: int | None = None
    detail: str | None = None
    subject: str | None = None
    operation: str | None = None
    item: str | None = None
    processed: int | None = None
    input_size_bytes: int | None = None
    output_size_bytes: int | None = None
    produced: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage, str):
            raise TypeError("stage must be a string")

        if not self.stage:
            raise ValueError("stage cannot be empty")

        if not isinstance(self.state, ProgressState):
            raise TypeError("state must be a ProgressState")

        for name, value in (
            ("current", self.current),
            ("total", self.total),
        ):
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError(
                        f"{name} must be an int or None"
                    )

                if value < 0:
                    raise ValueError(
                        f"{name} cannot be negative"
                    )

        if (
            self.current is not None
            and self.total is not None
            and self.current > self.total
        ):
            raise ValueError(
                "current cannot exceed total"
            )

        for name, value in (
            ("detail", self.detail),
            ("subject", self.subject),
            ("operation", self.operation),
            ("item", self.item),
        ):
            if (
                value is not None
                and not isinstance(value, str)
            ):
                raise TypeError(
                    f"{name} must be a string or None"
                )

        for name, value in (
            ("processed", self.processed),
            ("input_size_bytes", self.input_size_bytes),
            ("output_size_bytes", self.output_size_bytes),
            ("produced", self.produced),
        ):
            if value is not None:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                ):
                    raise TypeError(
                        f"{name} must be an int or None"
                    )

                if value < 0:
                    raise ValueError(
                        f"{name} cannot be negative"
                    )


ProgressCallback = Callable[[ProgressEvent], None]
