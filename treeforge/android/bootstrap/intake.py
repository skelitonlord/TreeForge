from __future__ import annotations

from treeforge.android.boot_image.intake import (
    AndroidBootImageIntake,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)

from treeforge.android.bootstrap.result import (
    AndroidBootstrapIntakeResult,
)


class AndroidBootstrapIntake:
    """
    Admit canonical Parsing evidence into Bootstrap.

    Bootstrap does not rediscover boot-family facts. Existing canonical
    Boot Image intake semantics are reused, while the complete exact Parsing
    result remains available for recovery/initramfs derivation.

    Knowledge is not applied here.
    """

    def __init__(
        self,
        *,
        boot_image_intake: AndroidBootImageIntake | None = None,
    ) -> None:
        self.boot_image_intake = (
            boot_image_intake
            if boot_image_intake is not None
            else AndroidBootImageIntake()
        )

        if not isinstance(
            self.boot_image_intake,
            AndroidBootImageIntake,
        ):
            raise TypeError(
                "boot_image_intake must be an "
                "AndroidBootImageIntake"
            )

    def build(
        self,
        parsing: AndroidParsingResult,
    ) -> AndroidBootstrapIntakeResult:
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        boot_image_intake_result = (
            self.boot_image_intake.build(
                parsing
            )
        )

        if (
            boot_image_intake_result.parsing
            is not parsing
        ):
            raise RuntimeError(
                "Boot Image intake lost exact canonical "
                "Parsing identity before Bootstrap"
            )

        result = AndroidBootstrapIntakeResult(
            parsing=parsing,
            boot_image_intake=(
                boot_image_intake_result
            ),
        )

        if result.parsing is not parsing:
            raise RuntimeError(
                "Bootstrap Intake must preserve exact "
                "AndroidParsingResult identity"
            )

        return result


__all__ = (
    "AndroidBootstrapIntake",
)
