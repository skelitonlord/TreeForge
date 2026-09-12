from __future__ import annotations

from treeforge.android.extraction.result import (
    AndroidExtractionResult,
)
from treeforge.android.parsing.ramdisk.model import (
    ParsedAndroidRamdisk,
)


class AndroidRamdiskParser:
    """
    Project complete canonical CPIO ramdisk evidence into Parsing.

    No CPIO decoding is repeated here. Parsing consumes the exact immutable
    Extraction results and preserves their canonical object graph.
    """

    def parse(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        ParsedAndroidRamdisk,
        ...,
    ]:
        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise TypeError(
                "extraction must be an AndroidExtractionResult"
            )

        parsed = []

        for cpio in extraction.cpio_extractions:
            ramdisk_root = cpio.artifact
            ramdisk_cpio = ramdisk_root.parent

            if ramdisk_cpio is None:
                raise ValueError(
                    "canonical CPIO extraction has no "
                    "ramdisk_cpio parent"
                )

            ramdisk_component = ramdisk_cpio.parent

            if ramdisk_component is None:
                raise ValueError(
                    "canonical ramdisk_cpio has no "
                    "ramdisk component parent"
                )

            boot_image_artifact = (
                ramdisk_component.parent
            )

            if boot_image_artifact is None:
                raise ValueError(
                    "canonical ramdisk component has no "
                    "boot-image parent"
                )

            parsed.append(
                ParsedAndroidRamdisk(
                    cpio=cpio,
                    boot_image_artifact=(
                        boot_image_artifact
                    ),
                    ramdisk_component=(
                        ramdisk_component
                    ),
                    ramdisk_cpio=ramdisk_cpio,
                    ramdisk_root=ramdisk_root,
                )
            )

        result = tuple(
            parsed
        )

        if len(
            result
        ) != len(
            extraction.cpio_extractions
        ):
            raise RuntimeError(
                "Parsing must conserve every canonical "
                "CPIO extraction exactly once"
            )

        for parsed_ramdisk, cpio in zip(
            result,
            extraction.cpio_extractions,
            strict=True,
        ):
            if parsed_ramdisk.cpio is not cpio:
                raise RuntimeError(
                    "Parsing ramdisk projection must retain "
                    "exact CpioExtractionResult identity"
                )

        return result
