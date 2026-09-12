from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.boot_image.models import (
    AndroidBootImageAvbRegionInterpretation,
    AndroidBootImageAvbVbmetaInterpretation,
    AndroidBootImageBootImageInterpretation,
    AndroidBootImageDtboContainerInterpretation,
    AndroidBootImageDtboEntryInterpretation,
    AndroidBootImageIntakeFamily,
    AndroidBootImageRamdiskInterpretation,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageIntakeResult:
    """
    Canonical Parsing -> Boot Image intake boundary.
    """

    parsing: AndroidParsingResult

    families: tuple[
        AndroidBootImageIntakeFamily,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if not isinstance(
            self.families,
            tuple,
        ):
            raise TypeError(
                "families must be a tuple"
            )

        if not all(
            isinstance(
                family,
                AndroidBootImageIntakeFamily,
            )
            for family
            in self.families
        ):
            raise TypeError(
                "families contain an invalid intake family"
            )

        names = tuple(
            family.name
            for family
            in self.families
        )

        if len(
            names
        ) != len(
            set(
                names
            )
        ):
            raise ValueError(
                "Boot Image intake family names must be unique"
            )

    @property
    def boot_images(self):
        return self.parsing.boot_images

    @property
    def boot_signatures(
        self,
    ):
        return self.parsing.boot_signatures

    @property
    def boot_dtbs(
        self,
    ):
        return self.parsing.boot_dtbs

    @property
    def vendor_ramdisk_tables(
        self,
    ):
        return self.parsing.vendor_ramdisk_tables

    @property
    def ramdisks(
        self,
    ):
        return self.parsing.ramdisks

    @property
    def kernels(self):
        return self.parsing.kernels

    @property
    def dtbo(self):
        return self.parsing.dtbo

    @property
    def vbmeta(self):
        return self.parsing.vbmeta

    @property
    def avb_regions(self):
        return self.parsing.avb_regions

    @property
    def bootloader(self):
        return self.parsing.bootloader

    @property
    def bootloader_children(self):
        return self.parsing.bootloader_children

    @property
    def sflb(self):
        return self.parsing.sflb

    @property
    def bmp(self):
        return self.parsing.bmp

    @property
    def filesystem(self):
        return self.parsing.filesystem

    @property
    def filesystem_inventory(self):
        return self.parsing.filesystem_inventory

    @property
    def source_inventory(self):
        return self.parsing.source_inventory


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageInterpretationResult:
    """
    Boot Image-owned structural interpretation of canonical Parsing evidence.
    """

    intake: AndroidBootImageIntakeResult

    boot_images: tuple[
        AndroidBootImageBootImageInterpretation,
        ...,
    ]

    ramdisks: tuple[
        AndroidBootImageRamdiskInterpretation,
        ...,
    ]

    dtbo_entries: tuple[
        AndroidBootImageDtboEntryInterpretation,
        ...,
    ]

    dtbo_containers: tuple[
        AndroidBootImageDtboContainerInterpretation,
        ...,
    ]

    avb_vbmeta: tuple[
        AndroidBootImageAvbVbmetaInterpretation,
        ...,
    ]

    avb_regions: tuple[
        AndroidBootImageAvbRegionInterpretation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.ramdisks,
            tuple,
        ):
            raise TypeError(
                "ramdisks must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageRamdiskInterpretation,
            )
            for value
            in self.ramdisks
        ):
            raise TypeError(
                "ramdisks must contain only "
                "AndroidBootImageRamdiskInterpretation instances"
            )

        expected_ramdisk_ids = tuple(
            id(
                value
            )
            for value
            in self.intake.ramdisks
        )

        actual_ramdisk_ids = tuple(
            id(
                value.ramdisk
            )
            for value
            in self.ramdisks
        )

        if (
            actual_ramdisk_ids
            != expected_ramdisk_ids
        ):
            raise ValueError(
                "Boot Image ramdisk interpretation population "
                "must conserve exact Parsing ramdisk order "
                "and identity"
            )

        root_ids = tuple(
            id(
                value.ramdisk.ramdisk_root
            )
            for value
            in self.ramdisks
        )

        if len(
            root_ids
        ) != len(
            set(
                root_ids
            )
        ):
            raise ValueError(
                "Boot Image ramdisk interpretation must not "
                "duplicate canonical ramdisk-root identities"
            )

        total_cpio_entries = sum(
            value.cpio_entry_count
            for value
            in self.ramdisks
        )

        total_cpio_interpretations = sum(
            len(
                value.cpio_entries
            )
            for value
            in self.ramdisks
        )

        if (
            total_cpio_interpretations
            != total_cpio_entries
        ):
            raise ValueError(
                "Boot Image ramdisk CPIO interpretation must "
                "conserve every canonical CPIO entry exactly once"
            )

        cpio_disposition_counts = {}

        for ramdisk in self.ramdisks:
            for interpretation in ramdisk.cpio_entries:
                disposition = (
                    interpretation
                    .disposition
                    .value
                )

                cpio_disposition_counts[
                    disposition
                ] = (
                    cpio_disposition_counts.get(
                        disposition,
                        0,
                    )
                    + 1
                )

        accounted_cpio_entries = sum(
            cpio_disposition_counts.values()
        )

        if (
            accounted_cpio_entries
            != total_cpio_entries
        ):
            raise ValueError(
                "Boot Image ramdisk CPIO disposition accounting "
                "must equal the complete canonical CPIO population"
            )

        if not isinstance(
            self.intake,
            AndroidBootImageIntakeResult,
        ):
            raise TypeError(
                "intake must be an AndroidBootImageIntakeResult"
            )

        if not isinstance(
            self.boot_images,
            tuple,
        ):
            raise TypeError(
                "boot_images must be a tuple"
            )

        if not all(
            isinstance(
                image,
                AndroidBootImageBootImageInterpretation,
            )
            for image
            in self.boot_images
        ):
            raise TypeError(
                "boot_images contain an invalid interpretation"
            )

        if not isinstance(
            self.dtbo_entries,
            tuple,
        ):
            raise TypeError(
                "dtbo_entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                AndroidBootImageDtboEntryInterpretation,
            )
            for entry
            in self.dtbo_entries
        ):
            raise TypeError(
                "dtbo_entries contain an invalid interpretation"
            )

        if not isinstance(
            self.dtbo_containers,
            tuple,
        ):
            raise TypeError(
                "dtbo_containers must be a tuple"
            )

        if not all(
            isinstance(
                container,
                AndroidBootImageDtboContainerInterpretation,
            )
            for container
            in self.dtbo_containers
        ):
            raise TypeError(
                "dtbo_containers contain an invalid interpretation"
            )

        expected_dtbo = tuple(
            id(
                entry
            )
            for entry
            in self.intake.dtbo
        )

        actual_dtbo = tuple(
            id(
                interpretation.entry
            )
            for interpretation
            in self.dtbo_entries
        )

        if actual_dtbo != expected_dtbo:
            raise ValueError(
                "Boot Image interpretation must preserve the complete "
                "DTBO population in canonical order and identity"
            )

        flattened_dtbo = tuple(
            entry
            for container
            in self.dtbo_containers
            for entry
            in container.entries
        )

        if tuple(
            id(
                entry
            )
            for entry
            in flattened_dtbo
        ) != tuple(
            id(
                entry
            )
            for entry
            in self.dtbo_entries
        ):
            raise ValueError(
                "DTBO container grouping must conserve every "
                "interpreted entry exactly once"
            )

        if not isinstance(
            self.avb_vbmeta,
            tuple,
        ):
            raise TypeError(
                "avb_vbmeta must be a tuple"
            )

        if not all(
            isinstance(
                node,
                AndroidBootImageAvbVbmetaInterpretation,
            )
            for node
            in self.avb_vbmeta
        ):
            raise TypeError(
                "avb_vbmeta contains an invalid interpretation"
            )

        if not isinstance(
            self.avb_regions,
            tuple,
        ):
            raise TypeError(
                "avb_regions must be a tuple"
            )

        if not all(
            isinstance(
                region,
                AndroidBootImageAvbRegionInterpretation,
            )
            for region
            in self.avb_regions
        ):
            raise TypeError(
                "avb_regions contains an invalid interpretation"
            )

        expected_vbmeta = tuple(
            id(
                vbmeta
            )
            for vbmeta
            in self.intake.vbmeta
        )

        actual_vbmeta = tuple(
            id(
                node.vbmeta
            )
            for node
            in self.avb_vbmeta
        )

        if actual_vbmeta != expected_vbmeta:
            raise ValueError(
                "Boot Image interpretation must preserve the "
                "complete VBMeta population in canonical order "
                "and identity"
            )

        expected_regions = tuple(
            id(
                region
            )
            for region
            in self.intake.avb_regions
        )

        actual_regions = tuple(
            id(
                interpretation.region
            )
            for interpretation
            in self.avb_regions
        )

        if actual_regions != expected_regions:
            raise ValueError(
                "Boot Image interpretation must preserve the "
                "complete AVB-region population in canonical "
                "order and identity"
            )

        expected = tuple(
            id(
                image
            )
            for image
            in self.intake.boot_images
        )

        actual = tuple(
            id(
                interpretation.image
            )
            for interpretation
            in self.boot_images
        )

        if actual != expected:
            raise ValueError(
                "Boot Image interpretation must preserve the complete "
                "boot-image population in canonical order and identity"
            )

    @property
    def parsing(
        self,
    ) -> AndroidParsingResult:
        return self.intake.parsing

    @property
    def avb_vbmeta_count(
        self,
    ) -> int:
        return len(
            self.avb_vbmeta
        )

    @property
    def avb_region_count(
        self,
    ) -> int:
        return len(
            self.avb_regions
        )

    @property
    def avb_unknown_descriptor_count(
        self,
    ) -> int:
        return sum(
            node.unknown_descriptor_count
            for node
            in self.avb_vbmeta
        )

    @property
    def dtbo_entry_count(
        self,
    ) -> int:
        return len(
            self.dtbo_entries
        )

    @property
    def dtbo_container_count(
        self,
    ) -> int:
        return len(
            self.dtbo_containers
        )

    @property
    def component_count(
        self,
    ) -> int:
        return sum(
            len(
                image.components
            )
            for image
            in self.boot_images
        )

    @property
    def unclassified_component_count(
        self,
    ) -> int:
        return sum(
            image.unclassified_component_count
            for image
            in self.boot_images
        )
