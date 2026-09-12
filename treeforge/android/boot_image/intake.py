from __future__ import annotations

from treeforge.android.boot_image.models import (
    AndroidBootImageIntakeFamily,
)
from treeforge.android.boot_image.result import (
    AndroidBootImageIntakeResult,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


class AndroidBootImageIntake:
    """
    Admit canonical Parsing evidence into the Boot Image branch.

    No Boot Image-specific interpretation is performed here.
    """

    _COUNTED_FAMILIES = (
        "boot_images",
        "boot_signatures",
        "boot_dtbs",
        "vendor_ramdisk_tables",
        "ramdisks",
        "kernels",
        "dtbo",
        "vbmeta",
        "avb_regions",
        "bootloader",
        "bootloader_children",
        "sflb",
        "bmp",
    )

    _AGGREGATE_FAMILIES = (
        "filesystem",
        "filesystem_inventory",
        "source_inventory",
    )

    def build(
        self,
        parsing: AndroidParsingResult,
    ) -> AndroidBootImageIntakeResult:
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        families: list[
            AndroidBootImageIntakeFamily
        ] = []

        for name in self._COUNTED_FAMILIES:
            population = getattr(
                parsing,
                name,
            )

            if not isinstance(
                population,
                tuple,
            ):
                raise TypeError(
                    f"Parsing family {name!r} must be a tuple"
                )

            families.append(
                AndroidBootImageIntakeFamily(
                    name=name,
                    population_size=len(
                        population
                    ),
                )
            )

        for name in self._AGGREGATE_FAMILIES:
            population = getattr(
                parsing,
                name,
            )

            if population is None:
                raise ValueError(
                    f"Parsing aggregate {name!r} "
                    "cannot be absent at Boot Image intake"
                )

            families.append(
                AndroidBootImageIntakeFamily(
                    name=name,
                    population_size=None,
                )
            )

        result = AndroidBootImageIntakeResult(
            parsing=parsing,
            families=tuple(
                families
            ),
        )

        if result.parsing is not parsing:
            raise RuntimeError(
                "Boot Image intake must preserve exact "
                "AndroidParsingResult identity"
            )

        return result
