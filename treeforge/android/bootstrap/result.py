from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.boot_image.result import (
    AndroidBootImageIntakeResult,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapIntakeResult:
    """
    Canonical Parsing -> Bootstrap intake boundary.

    Bootstrap retains the exact AndroidParsingResult object. It also retains
    Boot Image's canonical boot-family intake so Bootstrap can request future
    boot-image realization without rediscovering boot-family evidence.

    No recovery policy, installation policy, mutation choice, or device
    transport decision is made at Intake.
    """

    parsing: AndroidParsingResult
    boot_image_intake: AndroidBootImageIntakeResult

    def __post_init__(self) -> None:
        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if not isinstance(
            self.boot_image_intake,
            AndroidBootImageIntakeResult,
        ):
            raise TypeError(
                "boot_image_intake must be an "
                "AndroidBootImageIntakeResult"
            )

        if (
            self.boot_image_intake.parsing
            is not self.parsing
        ):
            raise ValueError(
                "Bootstrap Intake must preserve exact "
                "AndroidParsingResult identity through "
                "Boot Image intake"
            )


__all__ = (
    "AndroidBootstrapIntakeResult",
)
