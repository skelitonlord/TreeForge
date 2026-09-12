from __future__ import annotations

from treeforge.android.extraction.cpio.extractor import (
    CpioEntryType,
    CpioNewcEntry,
)

from treeforge.android.parsing.kernel_module.model import (
    AndroidKernelModuleConfigurationKind,
    AndroidKernelModuleConfigurationLine,
)

from treeforge.android.parsing.kernel_module.model import (
    ParsedAndroidKernelModule,
)

from dataclasses import dataclass

from treeforge.android.parsing.ramdisk import (
    ParsedAndroidRamdisk,
)
from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidFstab,
    ParsedAndroidInitSource,
    ParsedAndroidUeventd,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.kernel_module.model import (
    ParsedAndroidKernelModuleConfiguration,
)
from treeforge.android.parsing.result import (
    ParsedBootImage,
    ParsedBootSignature,
)
from enum import StrEnum

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
    AndroidParsedAvbKernelCmdlineDescriptor,
    AndroidParsedAvbPropertyDescriptor,
)
from treeforge.android.parsing.dtb.model import (
    AndroidParsedDtboEntry,
)
from treeforge.android.parsing.kernel import (
    ParsedKernelImage,
)
from treeforge.android.parsing.result import (
    ParsedAvbRegion,
    ParsedAvbVbmeta,
    ParsedBootImage,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageIntakeFamily:
    """
    Accounting record for one Boot Image-relevant Parsing population.
    """

    name: str
    population_size: int | None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a str"
            )

        if not self.name:
            raise ValueError(
                "name cannot be empty"
            )

        if (
            self.population_size is not None
            and (
                isinstance(
                    self.population_size,
                    bool,
                )
                or not isinstance(
                    self.population_size,
                    int,
                )
            )
        ):
            raise TypeError(
                "population_size must be an int or None"
            )

        if (
            self.population_size is not None
            and self.population_size < 0
        ):
            raise ValueError(
                "population_size cannot be negative"
            )


from treeforge.android.parsing.boot.bootconfig import (
    ParsedAndroidBootconfig,
)
from treeforge.android.parsing.boot.vendor_ramdisk_table import (
    ParsedVendorRamdiskTable,
)
from treeforge.android.parsing.dtb import (
    ParsedFdt,
)
from treeforge.android.parsing.ramdisk import (
    ParsedAndroidRamdisk,
)


class AndroidBootImageComponentRole(
    StrEnum
):
    """
    Structural role directly encoded by a canonical boot component name.

    These values describe Android boot-container format semantics only.
    They do not assign device policy, build ownership, or realization.
    """

    KERNEL = "kernel"
    RAMDISK = "ramdisk"
    SECOND = "second"
    RECOVERY_DTBO = "recovery_dtbo"
    DTB = "dtb"
    VENDOR_RAMDISK_TABLE = "vendor_ramdisk_table"
    BOOTCONFIG = "bootconfig"
    BOOT_SIGNATURE = "boot_signature"
    OTHER = "other"


class AndroidBootImageInterpretationDisposition(
    StrEnum
):
    """
    Explicit disposition for one admitted canonical boot component.
    """

    INTERPRETED = "interpreted"
    PRESERVED_UNCLASSIFIED = "preserved_unclassified"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageComponentInterpretation:
    """
    Boot Image interpretation of one exact canonical boot component.

    The original ExtractedArtifact remains authoritative for physical
    placement, size, offsets, hashes, and Extraction lineage.
    """

    artifact: ExtractedArtifact
    semantic_name: str
    role: AndroidBootImageComponentRole
    disposition: AndroidBootImageInterpretationDisposition
    kernel: ParsedKernelImage | None = None
    boot_signature: ParsedBootSignature | None = None
    ramdisk: ParsedAndroidRamdisk | None = None
    bootconfig: ParsedAndroidBootconfig | None = None
    dtbs: tuple[
        ParsedFdt,
        ...,
    ] = ()
    vendor_ramdisk_table: (
        ParsedVendorRamdiskTable
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            not isinstance(
                self.semantic_name,
                str,
            )
            or not self.semantic_name
        ):
            raise ValueError(
                "semantic_name must be a non-empty string"
            )

        if (
            self.artifact.semantic_name
            != self.semantic_name
        ):
            raise ValueError(
                "Boot Image component semantic name must exactly "
                "match the canonical Extraction artifact"
            )

        if not isinstance(
            self.role,
            AndroidBootImageComponentRole,
        ):
            raise TypeError(
                "role must be an AndroidBootImageComponentRole"
            )

        if not isinstance(
            self.disposition,
            AndroidBootImageInterpretationDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImageInterpretationDisposition"
            )

        if (
            self.role
            is AndroidBootImageComponentRole.OTHER
        ):
            if (
                self.disposition
                is not
                AndroidBootImageInterpretationDisposition
                .PRESERVED_UNCLASSIFIED
            ):
                raise ValueError(
                    "unclassified boot components must be "
                    "explicitly preserved"
                )
        elif (
            self.disposition
            is not
            AndroidBootImageInterpretationDisposition
            .INTERPRETED
        ):
            raise ValueError(
                "recognized boot components must be interpreted"
            )

        if self.kernel is not None:
            if not isinstance(
                self.kernel,
                ParsedKernelImage,
            ):
                raise TypeError(
                    "kernel must be a ParsedKernelImage or None"
                )

            if (
                self.role
                is not AndroidBootImageComponentRole.KERNEL
            ):
                raise ValueError(
                    "only a kernel component may retain "
                    "a ParsedKernelImage"
                )

            if (
                self.kernel.artifact.parent
                is not self.artifact
            ):
                raise ValueError(
                    "Boot Image kernel interpretation must retain "
                    "the exact canonical kernel component as the "
                    "parent of its parsed decompressed kernel artifact"
                )

        if self.boot_signature is not None:
            if not isinstance(
                self.boot_signature,
                ParsedBootSignature,
            ):
                raise TypeError(
                    "boot_signature must be a "
                    "ParsedBootSignature or None"
                )

            if (
                self.role
                is not
                AndroidBootImageComponentRole.BOOT_SIGNATURE
            ):
                raise ValueError(
                    "only a boot_signature component may retain "
                    "a ParsedBootSignature"
                )

            if (
                self.boot_signature.artifact
                is not self.artifact
            ):
                raise ValueError(
                    "Boot Image boot-signature interpretation must "
                    "retain exact canonical component artifact identity"
                )

        if (
            self.role
            is AndroidBootImageComponentRole.BOOT_SIGNATURE
            and self.boot_signature is None
        ):
            raise ValueError(
                "recognized boot_signature component must retain "
                "its exact canonical ParsedBootSignature"
            )

        if self.ramdisk is not None:
            if not isinstance(
                self.ramdisk,
                ParsedAndroidRamdisk,
            ):
                raise TypeError(
                    "ramdisk must be a ParsedAndroidRamdisk or None"
                )

            if (
                self.role
                is not AndroidBootImageComponentRole.RAMDISK
            ):
                raise ValueError(
                    "only a ramdisk component may retain "
                    "a ParsedAndroidRamdisk"
                )

            if (
                self.ramdisk.ramdisk_component
                is not self.artifact
            ):
                raise ValueError(
                    "Boot Image ramdisk component association must "
                    "retain exact canonical component identity"
                )

        if self.bootconfig is not None:
            if not isinstance(
                self.bootconfig,
                ParsedAndroidBootconfig,
            ):
                raise TypeError(
                    "bootconfig must be a "
                    "ParsedAndroidBootconfig or None"
                )

            if (
                self.role
                is not AndroidBootImageComponentRole.BOOTCONFIG
            ):
                raise ValueError(
                    "only a bootconfig component may retain "
                    "a ParsedAndroidBootconfig"
                )

        if not isinstance(
            self.dtbs,
            tuple,
        ):
            raise TypeError(
                "dtbs must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedFdt,
            )
            for value
            in self.dtbs
        ):
            raise TypeError(
                "dtbs must contain only ParsedFdt values"
            )

        if (
            self.dtbs
            and self.role
            is not AndroidBootImageComponentRole.DTB
        ):
            raise ValueError(
                "only a dtb component may retain ParsedFdt members"
            )

        dtb_artifact_ids = tuple(
            id(
                value.artifact
            )
            for value
            in self.dtbs
        )

        if len(
            dtb_artifact_ids
        ) != len(
            set(
                dtb_artifact_ids
            )
        ):
            raise ValueError(
                "Boot Image DTB component association contains "
                "duplicate canonical ParsedFdt artifact identity"
            )

        for value in self.dtbs:
            if (
                value.artifact.parent
                is not self.artifact
            ):
                raise ValueError(
                    "Boot Image DTB component association must "
                    "retain exact FDT-member parent identity"
                )

        if self.vendor_ramdisk_table is not None:
            if not isinstance(
                self.vendor_ramdisk_table,
                ParsedVendorRamdiskTable,
            ):
                raise TypeError(
                    "vendor_ramdisk_table must be a "
                    "ParsedVendorRamdiskTable or None"
                )

            if (
                self.role
                is not
                AndroidBootImageComponentRole
                .VENDOR_RAMDISK_TABLE
            ):
                raise ValueError(
                    "only a vendor_ramdisk_table component may "
                    "retain a ParsedVendorRamdiskTable"
                )

            if (
                self.vendor_ramdisk_table.artifact
                is not self.artifact
            ):
                raise ValueError(
                    "Boot Image vendor ramdisk-table association "
                    "must retain exact canonical component identity"
                )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageBootImageInterpretation:
    """
    Structural Boot Image interpretation of one canonical boot-family image.

    No build provider, output image, signing key, or composition decision is
    selected here.
    """

    image: ParsedBootImage

    components: tuple[
        AndroidBootImageComponentInterpretation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.image,
            ParsedBootImage,
        ):
            raise TypeError(
                "image must be a ParsedBootImage"
            )

        if not isinstance(
            self.components,
            tuple,
        ):
            raise TypeError(
                "components must be a tuple"
            )

        if not all(
            isinstance(
                component,
                AndroidBootImageComponentInterpretation,
            )
            for component
            in self.components
        ):
            raise TypeError(
                "components contain an invalid interpretation"
            )

        expected = tuple(
            id(
                artifact
            )
            for artifact
            in self.image.component_artifacts
        )

        actual = tuple(
            id(
                component.artifact
            )
            for component
            in self.components
        )

        if actual != expected:
            raise ValueError(
                "Boot Image interpretation must preserve every boot "
                "component in exact canonical order and identity"
            )

    @property
    def container_kind(
        self,
    ) -> str:
        return self.image.container_kind

    @property
    def container_format(
        self,
    ) -> str:
        return self.image.container_format

    @property
    def header_version(
        self,
    ) -> int:
        return self.image.metadata.header_version

    @property
    def cmdline(
        self,
    ) -> str:
        return self.image.metadata.cmdline

    @property
    def boot_name(
        self,
    ) -> str:
        return self.image.metadata.boot_name

    @property
    def has_kernel(
        self,
    ) -> bool:
        return self._has_role(
            AndroidBootImageComponentRole.KERNEL
        )

    @property
    def has_ramdisk(
        self,
    ) -> bool:
        return self._has_role(
            AndroidBootImageComponentRole.RAMDISK
        )

    @property
    def has_dtb(
        self,
    ) -> bool:
        return self._has_role(
            AndroidBootImageComponentRole.DTB
        )

    @property
    def has_vendor_ramdisk_table(
        self,
    ) -> bool:
        return self._has_role(
            AndroidBootImageComponentRole
            .VENDOR_RAMDISK_TABLE
        )

    @property
    def has_bootconfig(
        self,
    ) -> bool:
        return self._has_role(
            AndroidBootImageComponentRole.BOOTCONFIG
        )

    @property
    def unclassified_component_count(
        self,
    ) -> int:
        return sum(
            1
            for component
            in self.components
            if (
                component.disposition
                is AndroidBootImageInterpretationDisposition
                .PRESERVED_UNCLASSIFIED
            )
        )

    def _has_role(
        self,
        role: AndroidBootImageComponentRole,
    ) -> bool:
        return any(
            component.role is role
            for component
            in self.components
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDtboEntryInterpretation:
    """
    Structural interpretation of one exact canonical DTBO table entry.

    Extraction remains authoritative for physical DTBO table/container
    structure. Parsing remains authoritative for the FDT and overlay metadata.
    Boot Image merely reconciles those already-canonical observations.
    """

    entry: AndroidParsedDtboEntry

    container: ExtractedArtifact

    entry_index: int
    offset_bytes: int
    declared_size_bytes: int

    dtbo_id: int
    dtbo_rev: int

    custom: tuple[
        int,
        int,
        int,
        int,
    ]

    page_size_bytes: int
    table_total_size_bytes: int
    table_version: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.entry,
            AndroidParsedDtboEntry,
        ):
            raise TypeError(
                "entry must be an AndroidParsedDtboEntry"
            )

        if not isinstance(
            self.container,
            ExtractedArtifact,
        ):
            raise TypeError(
                "container must be an ExtractedArtifact"
            )

        if self.entry.artifact.parent is not self.container:
            raise ValueError(
                "DTBO interpretation must retain the exact "
                "canonical DTBO container parent"
            )

        for field_name in (
            "entry_index",
            "offset_bytes",
            "declared_size_bytes",
            "dtbo_id",
            "dtbo_rev",
            "page_size_bytes",
            "table_total_size_bytes",
            "table_version",
        ):
            value = getattr(
                self,
                field_name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

        if (
            not isinstance(
                self.custom,
                tuple,
            )
            or len(
                self.custom
            ) != 4
            or not all(
                isinstance(
                    value,
                    int,
                )
                and not isinstance(
                    value,
                    bool,
                )
                and value >= 0
                for value
                in self.custom
            )
        ):
            raise ValueError(
                "custom must contain exactly four "
                "non-negative integers"
            )

        if (
            self.entry.artifact.size_bytes
            is not None
            and self.entry.artifact.size_bytes
            != self.declared_size_bytes
        ):
            raise ValueError(
                "DTBO declared size must match the exact "
                "canonical extracted payload size"
            )

    @property
    def fdt(
        self,
    ):
        return self.entry.fdt

    @property
    def overlay(
        self,
    ):
        return self.entry.overlay


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDtboContainerInterpretation:
    """
    One canonical DTBO container and its complete interpreted entry population.
    """

    container: ExtractedArtifact

    entries: tuple[
        AndroidBootImageDtboEntryInterpretation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.container,
            ExtractedArtifact,
        ):
            raise TypeError(
                "container must be an ExtractedArtifact"
            )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                AndroidBootImageDtboEntryInterpretation,
            )
            for entry
            in self.entries
        ):
            raise TypeError(
                "entries contain an invalid DTBO interpretation"
            )

        if not all(
            entry.container
            is self.container
            for entry
            in self.entries
        ):
            raise ValueError(
                "all DTBO entries must retain exact "
                "container identity"
            )

        indices = tuple(
            entry.entry_index
            for entry
            in self.entries
        )

        if len(
            indices
        ) != len(
            set(
                indices
            )
        ):
            raise ValueError(
                "DTBO container contains duplicate entry indices"
            )

        if indices != tuple(
            sorted(
                indices
            )
        ):
            raise ValueError(
                "DTBO entries must remain in table index order"
            )

    @property
    def entry_count(
        self,
    ) -> int:
        return len(
            self.entries
        )


class AndroidBootImageAvbSourceKind(
    StrEnum
):
    """
    Physical placement of one canonical VBMeta source.
    """

    STANDALONE = "standalone"
    EMBEDDED = "embedded"


class AndroidBootImageAvbDescriptorKind(
    StrEnum
):
    """
    Literal semantic class of one AVB descriptor.
    """

    PROPERTY = "property"
    HASHTREE = "hashtree"
    HASH = "hash"
    KERNEL_CMDLINE = "kernel_cmdline"
    CHAIN_PARTITION = "chain_partition"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbDescriptorInterpretation:
    """
    Structural interpretation of one literal parsed AVB descriptor.

    No trust decision or signing policy is assigned here.
    """

    descriptor: object
    kind: AndroidBootImageAvbDescriptorKind
    disposition: AndroidBootImageInterpretationDisposition
    target_partition: str | None = None

    def __post_init__(
        self,
    ) -> None:
        supported = (
            AndroidParsedAvbPropertyDescriptor,
            AndroidParsedAvbHashtreeDescriptor,
            AndroidParsedAvbHashDescriptor,
            AndroidParsedAvbKernelCmdlineDescriptor,
            AndroidParsedAvbChainPartitionDescriptor,
            AndroidParsedAvbDescriptor,
        )

        if not isinstance(
            self.descriptor,
            supported,
        ):
            raise TypeError(
                "descriptor must be a parsed AVB descriptor"
            )

        if not isinstance(
            self.kind,
            AndroidBootImageAvbDescriptorKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidBootImageAvbDescriptorKind"
            )

        if not isinstance(
            self.disposition,
            AndroidBootImageInterpretationDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImageInterpretationDisposition"
            )

        if (
            self.kind
            is AndroidBootImageAvbDescriptorKind.UNKNOWN
        ):
            if (
                self.disposition
                is not
                AndroidBootImageInterpretationDisposition
                .PRESERVED_UNCLASSIFIED
            ):
                raise ValueError(
                    "unknown AVB descriptors must be "
                    "explicitly preserved"
                )
        elif (
            self.disposition
            is not
            AndroidBootImageInterpretationDisposition
            .INTERPRETED
        ):
            raise ValueError(
                "known AVB descriptors must be interpreted"
            )

        hash_kinds = {
            AndroidBootImageAvbDescriptorKind.HASHTREE,
            AndroidBootImageAvbDescriptorKind.HASH,
        }

        if self.kind in hash_kinds:
            if not isinstance(
                self.target_partition,
                str,
            ):
                raise TypeError(
                    "hash/hashtree AVB descriptors must retain "
                    "their canonical partition_name string"
                )

        elif (
            self.kind
            is AndroidBootImageAvbDescriptorKind.CHAIN_PARTITION
        ):
            if (
                not isinstance(
                    self.target_partition,
                    str,
                )
                or not self.target_partition
            ):
                raise ValueError(
                    "chain-partition AVB descriptors must retain "
                    "a non-empty target partition"
                )

        elif self.target_partition is not None:
            raise ValueError(
                "non-partition AVB descriptors cannot carry "
                "a target partition"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbVbmetaInterpretation:
    """
    Boot Image interpretation of one exact canonical VBMeta source.
    """

    vbmeta: ParsedAvbVbmeta
    source_kind: AndroidBootImageAvbSourceKind

    descriptors: tuple[
        AndroidBootImageAvbDescriptorInterpretation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.vbmeta,
            ParsedAvbVbmeta,
        ):
            raise TypeError(
                "vbmeta must be a ParsedAvbVbmeta"
            )

        if not isinstance(
            self.source_kind,
            AndroidBootImageAvbSourceKind,
        ):
            raise TypeError(
                "source_kind must be an "
                "AndroidBootImageAvbSourceKind"
            )

        expected_kind = (
            AndroidBootImageAvbSourceKind.STANDALONE
            if (
                self.vbmeta.artifact
                is self.vbmeta.container_artifact
            )
            else AndroidBootImageAvbSourceKind.EMBEDDED
        )

        if self.source_kind is not expected_kind:
            raise ValueError(
                "VBMeta source kind must match canonical "
                "artifact/container identity"
            )

        if not isinstance(
            self.descriptors,
            tuple,
        ):
            raise TypeError(
                "descriptors must be a tuple"
            )

        if not all(
            isinstance(
                descriptor,
                AndroidBootImageAvbDescriptorInterpretation,
            )
            for descriptor
            in self.descriptors
        ):
            raise TypeError(
                "descriptors contain an invalid AVB "
                "interpretation"
            )

        expected = tuple(
            id(
                descriptor
            )
            for descriptor
            in self.vbmeta.metadata.descriptors
        )

        actual = tuple(
            id(
                descriptor.descriptor
            )
            for descriptor
            in self.descriptors
        )

        if actual != expected:
            raise ValueError(
                "AVB interpretation must preserve every "
                "descriptor in exact canonical order and identity"
            )

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        return self.vbmeta.artifact

    @property
    def container_artifact(
        self,
    ) -> ExtractedArtifact:
        return self.vbmeta.container_artifact

    @property
    def partition(
        self,
    ):
        return self.vbmeta.partition

    @property
    def footer(
        self,
    ):
        return self.vbmeta.footer

    @property
    def algorithm_type(
        self,
    ) -> int:
        return self.vbmeta.metadata.algorithm_type

    @property
    def rollback_index(
        self,
    ) -> int:
        return self.vbmeta.metadata.rollback_index

    @property
    def rollback_index_location(
        self,
    ) -> int:
        return self.vbmeta.metadata.rollback_index_location

    @property
    def flags(
        self,
    ) -> int:
        return self.vbmeta.metadata.flags

    @property
    def public_key(
        self,
    ) -> bytes:
        return self.vbmeta.metadata.public_key

    @property
    def unknown_descriptor_count(
        self,
    ) -> int:
        return sum(
            1
            for descriptor
            in self.descriptors
            if (
                descriptor.kind
                is AndroidBootImageAvbDescriptorKind.UNKNOWN
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbRegionInterpretation:
    """
    Explicit Boot Image accounting for one canonical AVB region.

    Parsing's region disposition remains authoritative. Boot Image only binds
    parsed VBMeta regions to their corresponding interpreted VBMeta node.
    """

    region: ParsedAvbRegion

    vbmeta: (
        AndroidBootImageAvbVbmetaInterpretation
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.region,
            ParsedAvbRegion,
        ):
            raise TypeError(
                "region must be a ParsedAvbRegion"
            )

        if (
            self.vbmeta is not None
            and not isinstance(
                self.vbmeta,
                AndroidBootImageAvbVbmetaInterpretation,
            )
        ):
            raise TypeError(
                "vbmeta must be an interpreted VBMeta node or None"
            )

        if self.region.disposition == "parsed":
            if self.vbmeta is None:
                raise ValueError(
                    "parsed AVB region must retain its "
                    "interpreted VBMeta node"
                )

            if (
                self.region.vbmeta
                is not self.vbmeta.vbmeta
            ):
                raise ValueError(
                    "parsed AVB region must preserve exact "
                    "ParsedAvbVbmeta identity"
                )

        elif self.vbmeta is not None:
            raise ValueError(
                "only parsed AVB regions may reference "
                "an interpreted VBMeta node"
            )

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        return self.region.artifact

    @property
    def disposition(
        self,
    ) -> str:
        return self.region.disposition



class AndroidBootImageKernelModuleResolution(
    StrEnum
):
    """
    Resolution state of one literal modules.* module reference.
    """

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageKernelModuleReference:
    """
    One literal module reference reconciled only against the exact module
    population physically associated with this ramdisk.

    Boot Image does not infer load policy here.
    """

    raw_reference: str

    resolution: AndroidBootImageKernelModuleResolution

    module: ParsedAndroidKernelModule | None = None

    candidates: tuple[
        ParsedAndroidKernelModule,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.raw_reference,
                str,
            )
            or not self.raw_reference
        ):
            raise ValueError(
                "raw_reference must be a non-empty string"
            )

        if not isinstance(
            self.resolution,
            AndroidBootImageKernelModuleResolution,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidBootImageKernelModuleResolution"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                ParsedAndroidKernelModule,
            )
            for candidate
            in self.candidates
        ):
            raise TypeError(
                "candidates must contain only "
                "ParsedAndroidKernelModule instances"
            )

        if (
            self.resolution
            is AndroidBootImageKernelModuleResolution.RESOLVED
        ):
            if not isinstance(
                self.module,
                ParsedAndroidKernelModule,
            ):
                raise ValueError(
                    "resolved module reference must retain "
                    "the exact resolved module"
                )

            if self.candidates != (
                self.module,
            ):
                raise ValueError(
                    "resolved module reference must retain "
                    "exactly one candidate"
                )

        elif (
            self.resolution
            is AndroidBootImageKernelModuleResolution.UNRESOLVED
        ):
            if self.module is not None:
                raise ValueError(
                    "unresolved module reference cannot retain "
                    "a resolved module"
                )

            if self.candidates:
                raise ValueError(
                    "unresolved module reference cannot retain "
                    "candidate modules"
                )

        else:
            if self.module is not None:
                raise ValueError(
                    "ambiguous module reference cannot choose "
                    "a resolved module"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous module reference must retain "
                    "at least two candidates"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageKernelModuleLoadEntry:
    """
    One exact modules.load line.

    Reference order is the literal token order from Parsing.
    """

    configuration: ParsedAndroidKernelModuleConfiguration
    line: AndroidKernelModuleConfigurationLine

    references: tuple[
        AndroidBootImageKernelModuleReference,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.configuration.configuration_kind
            is not AndroidKernelModuleConfigurationKind.LOAD
        ):
            raise ValueError(
                "load entry requires modules.load configuration"
            )

        if not any(
            value is self.line
            for value
            in self.configuration.lines
        ):
            raise ValueError(
                "load entry must retain exact canonical line identity"
            )

        if not self.references:
            raise ValueError(
                "load entry must retain at least one module reference"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageKernelModuleDependencyEntry:
    """
    One exact modules.dep line.
    """

    configuration: ParsedAndroidKernelModuleConfiguration
    line: AndroidKernelModuleConfigurationLine

    module: AndroidBootImageKernelModuleReference

    dependencies: tuple[
        AndroidBootImageKernelModuleReference,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.configuration.configuration_kind
            is not AndroidKernelModuleConfigurationKind.DEP
        ):
            raise ValueError(
                "dependency entry requires modules.dep configuration"
            )

        if not any(
            value is self.line
            for value
            in self.configuration.lines
        ):
            raise ValueError(
                "dependency entry must retain exact canonical line identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageKernelModuleAliasEntry:
    """
    One exact modules.alias line.
    """

    configuration: ParsedAndroidKernelModuleConfiguration
    line: AndroidKernelModuleConfigurationLine

    alias: str
    module: AndroidBootImageKernelModuleReference

    def __post_init__(
        self,
    ) -> None:
        if (
            self.configuration.configuration_kind
            is not AndroidKernelModuleConfigurationKind.ALIAS
        ):
            raise ValueError(
                "alias entry requires modules.alias configuration"
            )

        if not any(
            value is self.line
            for value
            in self.configuration.lines
        ):
            raise ValueError(
                "alias entry must retain exact canonical line identity"
            )

        if not self.alias:
            raise ValueError(
                "alias must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageKernelModuleSoftDependencyEntry:
    """
    One exact modules.softdep line.

    ``pre`` and ``post`` preserve source ordering independently.
    """

    configuration: ParsedAndroidKernelModuleConfiguration
    line: AndroidKernelModuleConfigurationLine

    module: AndroidBootImageKernelModuleReference

    pre: tuple[
        AndroidBootImageKernelModuleReference,
        ...,
    ] = ()

    post: tuple[
        AndroidBootImageKernelModuleReference,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            self.configuration.configuration_kind
            is not AndroidKernelModuleConfigurationKind.SOFTDEP
        ):
            raise ValueError(
                "soft dependency entry requires "
                "modules.softdep configuration"
            )

        if not any(
            value is self.line
            for value
            in self.configuration.lines
        ):
            raise ValueError(
                "soft dependency entry must retain exact "
                "canonical line identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageKernelModuleUninterpretedLine:
    """
    Explicit disposition for a modules.* relationship line whose lexical
    structure cannot be interpreted without guessing.
    """

    configuration: ParsedAndroidKernelModuleConfiguration
    line: AndroidKernelModuleConfigurationLine
    reason: str

    def __post_init__(
        self,
    ) -> None:
        if not any(
            value is self.line
            for value
            in self.configuration.lines
        ):
            raise ValueError(
                "uninterpreted line must retain exact canonical line identity"
            )

        if (
            not isinstance(
                self.reason,
                str,
            )
            or not self.reason
        ):
            raise ValueError(
                "reason must be a non-empty string"
            )


class AndroidBootImageCpioEntryKind(
    StrEnum
):
    """
    Boot Image-visible structural meaning of one exact CPIO entry.

    This classification does not imply reconstruction, inclusion, execution,
    or boot policy.
    """

    DIRECTORY = "directory"
    SYMLINK = "symlink"

    CHARACTER_DEVICE = "character_device"
    BLOCK_DEVICE = "block_device"
    FIFO = "fifo"
    SOCKET = "socket"

    INIT_BINARY = "init_binary"
    INIT_CONFIGURATION = "init_configuration"
    FSTAB_CONFIGURATION = "fstab_configuration"
    UEVENTD_CONFIGURATION = "ueventd_configuration"

    KERNEL_MODULE = "kernel_module"
    KERNEL_MODULE_CONFIGURATION = "kernel_module_configuration"

    EXECUTABLE = "executable"
    SHARED_LIBRARY = "shared_library"

    OTHER_FILE = "other_file"
    UNKNOWN = "unknown"


class AndroidBootImageCpioEntryDisposition(
    StrEnum
):
    """
    Explicit disposition of every exact canonical CPIO entry.
    """

    INTERPRETED = "interpreted"
    CANONICAL_PARSING_ASSOCIATION = (
        "canonical_parsing_association"
    )
    PRESERVED_RESOURCE = "preserved_resource"
    PRESERVED_UNCLASSIFIED = "preserved_unclassified"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageCpioEntryInterpretation:
    """
    Lossless Boot Image interpretation of one exact canonical CPIO entry.

    ``entry`` is never copied or rebuilt: it is the exact CpioNewcEntry
    retained by the canonical Parsing result.
    """

    entry: CpioNewcEntry
    index: int

    kind: AndroidBootImageCpioEntryKind

    disposition: AndroidBootImageCpioEntryDisposition

    associated_source: AndroidModelSource | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.entry,
            CpioNewcEntry,
        ):
            raise TypeError(
                "entry must be a CpioNewcEntry"
            )

        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if not isinstance(
            self.kind,
            AndroidBootImageCpioEntryKind,
        ):
            raise TypeError(
                "kind must be an AndroidBootImageCpioEntryKind"
            )

        if not isinstance(
            self.disposition,
            AndroidBootImageCpioEntryDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImageCpioEntryDisposition"
            )

        if (
            self.associated_source is not None
            and not isinstance(
                self.associated_source,
                AndroidModelSource,
            )
        ):
            raise TypeError(
                "associated_source must be an "
                "AndroidModelSource or None"
            )

        if (
            self.disposition
            in {
                AndroidBootImageCpioEntryDisposition
                .CANONICAL_PARSING_ASSOCIATION,
                AndroidBootImageCpioEntryDisposition
                .PRESERVED_RESOURCE,
            }
            and self.associated_source is None
        ):
            raise ValueError(
                "Parsing-associated CPIO dispositions must "
                "retain an exact canonical AndroidModelSource"
            )

        if (
            self.disposition
            is AndroidBootImageCpioEntryDisposition
            .PRESERVED_UNCLASSIFIED
            and self.associated_source is not None
        ):
            raise ValueError(
                "preserved-unclassified CPIO entries cannot "
                "claim a canonical Parsing source association"
            )

        expected_physical_kinds = {
            CpioEntryType.DIRECTORY:
                AndroidBootImageCpioEntryKind.DIRECTORY,
            CpioEntryType.SYMLINK:
                AndroidBootImageCpioEntryKind.SYMLINK,
            CpioEntryType.CHARACTER_DEVICE:
                AndroidBootImageCpioEntryKind.CHARACTER_DEVICE,
            CpioEntryType.BLOCK_DEVICE:
                AndroidBootImageCpioEntryKind.BLOCK_DEVICE,
            CpioEntryType.FIFO:
                AndroidBootImageCpioEntryKind.FIFO,
            CpioEntryType.SOCKET:
                AndroidBootImageCpioEntryKind.SOCKET,
        }

        expected = expected_physical_kinds.get(
            self.entry.entry_type
        )

        if (
            expected is not None
            and self.kind is not expected
        ):
            raise ValueError(
                "non-file CPIO entry kind must preserve "
                "its exact physical entry type"
            )

        if (
            self.kind
            is AndroidBootImageCpioEntryKind.UNKNOWN
            and self.disposition
            is not AndroidBootImageCpioEntryDisposition
            .PRESERVED_UNCLASSIFIED
        ):
            raise ValueError(
                "unknown CPIO entries must be preserved unclassified"
            )

        if (
            self.kind
            is AndroidBootImageCpioEntryKind.OTHER_FILE
            and self.disposition
            not in {
                AndroidBootImageCpioEntryDisposition
                .CANONICAL_PARSING_ASSOCIATION,
                AndroidBootImageCpioEntryDisposition
                .PRESERVED_RESOURCE,
                AndroidBootImageCpioEntryDisposition
                .PRESERVED_UNCLASSIFIED,
            }
        ):
            raise ValueError(
                "other files must either retain an exact "
                "canonical Parsing association or remain "
                "explicitly preserved unclassified"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageRamdiskInterpretation:
    """
    Structural Boot Image interpretation of one exact canonical ramdisk.

    Associations are derived exclusively through canonical Parsing object
    identity. No container-name role mapping, reconstruction policy, module
    dependency interpretation, or image-composition decision is performed
    here.
    """

    ramdisk: ParsedAndroidRamdisk

    filesystem_source: AndroidParserFilesystemSource

    boot_image: ParsedBootImage

    canonical_sources: tuple[
        AndroidModelSource,
        ...,
    ] = ()

    init_files: tuple[
        ParsedAndroidInitSource,
        ...,
    ] = ()

    fstabs: tuple[
        ParsedAndroidFstab,
        ...,
    ] = ()

    ueventd_files: tuple[
        ParsedAndroidUeventd,
        ...,
    ] = ()

    kernel_modules: tuple[
        ParsedAndroidKernelModule,
        ...,
    ] = ()

    kernel_module_configurations: tuple[
        ParsedAndroidKernelModuleConfiguration,
        ...,
    ] = ()

    kernel_module_load_entries: tuple[
        AndroidBootImageKernelModuleLoadEntry,
        ...,
    ] = ()

    kernel_module_dependency_entries: tuple[
        AndroidBootImageKernelModuleDependencyEntry,
        ...,
    ] = ()

    kernel_module_alias_entries: tuple[
        AndroidBootImageKernelModuleAliasEntry,
        ...,
    ] = ()

    kernel_module_soft_dependency_entries: tuple[
        AndroidBootImageKernelModuleSoftDependencyEntry,
        ...,
    ] = ()

    kernel_module_uninterpreted_lines: tuple[
        AndroidBootImageKernelModuleUninterpretedLine,
        ...,
    ] = ()

    cpio_entries: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.ramdisk,
            ParsedAndroidRamdisk,
        ):
            raise TypeError(
                "ramdisk must be a ParsedAndroidRamdisk"
            )

        if not isinstance(
            self.filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "filesystem_source must be an "
                "AndroidParserFilesystemSource"
            )

        if (
            self.filesystem_source.artifact
            is not self.ramdisk.ramdisk_root
        ):
            raise ValueError(
                "ramdisk interpretation filesystem source must "
                "retain exact ramdisk-root artifact identity"
            )

        if not isinstance(
            self.boot_image,
            ParsedBootImage,
        ):
            raise TypeError(
                "boot_image must be a ParsedBootImage"
            )

        if (
            self.boot_image.partition.artifact
            is not self.ramdisk.boot_image_artifact
        ):
            raise ValueError(
                "ramdisk interpretation boot image must retain "
                "exact boot-family artifact identity"
            )

        collections = (
            (
                "canonical_sources",
                self.canonical_sources,
                AndroidModelSource,
            ),
            (
                "init_files",
                self.init_files,
                ParsedAndroidInitSource,
            ),
            (
                "fstabs",
                self.fstabs,
                ParsedAndroidFstab,
            ),
            (
                "ueventd_files",
                self.ueventd_files,
                ParsedAndroidUeventd,
            ),
            (
                "kernel_modules",
                self.kernel_modules,
                ParsedAndroidKernelModule,
            ),
            (
                "kernel_module_configurations",
                self.kernel_module_configurations,
                ParsedAndroidKernelModuleConfiguration,
            ),
            (
                "kernel_module_load_entries",
                self.kernel_module_load_entries,
                AndroidBootImageKernelModuleLoadEntry,
            ),
            (
                "kernel_module_dependency_entries",
                self.kernel_module_dependency_entries,
                AndroidBootImageKernelModuleDependencyEntry,
            ),
            (
                "kernel_module_alias_entries",
                self.kernel_module_alias_entries,
                AndroidBootImageKernelModuleAliasEntry,
            ),
            (
                "kernel_module_soft_dependency_entries",
                self.kernel_module_soft_dependency_entries,
                AndroidBootImageKernelModuleSoftDependencyEntry,
            ),
            (
                "kernel_module_uninterpreted_lines",
                self.kernel_module_uninterpreted_lines,
                AndroidBootImageKernelModuleUninterpretedLine,
            ),
            (
                "cpio_entries",
                self.cpio_entries,
                AndroidBootImageCpioEntryInterpretation,
            ),
        )

        for (
            field_name,
            values,
            expected_type,
        ) in collections:
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    f"{expected_type.__name__} instances"
                )

        canonical_source_ids = tuple(
            id(source)
            for source
            in self.canonical_sources
        )

        if len(
            canonical_source_ids
        ) != len(
            set(
                canonical_source_ids
            )
        ):
            raise ValueError(
                "canonical Parsing sources must retain "
                "unique exact object identities"
            )

        for source in self.canonical_sources:
            if (
                source.filesystem_source
                is not self.filesystem_source
            ):
                raise ValueError(
                    "canonical Parsing source must retain "
                    "exact ramdisk filesystem-source identity"
                )

        for value in self.init_files:
            if (
                value.filesystem_source
                is not self.filesystem_source
            ):
                raise ValueError(
                    "INIT source must retain exact ramdisk "
                    "filesystem-source identity"
                )

        for value in self.fstabs:
            if (
                value.filesystem_source
                is not self.filesystem_source
            ):
                raise ValueError(
                    "fstab source must retain exact ramdisk "
                    "filesystem-source identity"
                )

        for value in self.ueventd_files:
            if (
                value.filesystem_source
                is not self.filesystem_source
            ):
                raise ValueError(
                    "ueventd source must retain exact ramdisk "
                    "filesystem-source identity"
                )

        for value in self.kernel_modules:
            if (
                value.elf.source.filesystem_source
                is not self.filesystem_source
            ):
                raise ValueError(
                    "kernel-module payload must retain exact ramdisk "
                    "filesystem-source identity"
                )

        for value in self.kernel_module_configurations:
            if (
                value.source.filesystem_source
                is not self.filesystem_source
            ):
                raise ValueError(
                    "kernel-module configuration must retain "
                    "exact ramdisk filesystem-source identity"
                )

        if len(
            self.cpio_entries
        ) != len(
            self.ramdisk.entries
        ):
            raise ValueError(
                "CPIO interpretation population must exactly match "
                "the canonical ramdisk entry population"
            )

        for (
            expected_index,
            (
                canonical_entry,
                interpreted_entry,
            ),
        ) in enumerate(
            zip(
                self.ramdisk.entries,
                self.cpio_entries,
                strict=True,
            )
        ):
            if (
                interpreted_entry.index
                != expected_index
            ):
                raise ValueError(
                    "CPIO interpretation index must preserve "
                    "exact archive order"
                )

            if (
                interpreted_entry.entry
                is not canonical_entry
            ):
                raise ValueError(
                    "CPIO interpretation must retain exact "
                    "canonical CpioNewcEntry identity"
                )

        configuration_ids = {
            id(
                configuration
            )
            for configuration
            in self.kernel_module_configurations
        }

        module_ids = {
            id(
                module
            )
            for module
            in self.kernel_modules
        }

        relationships = (
            *self.kernel_module_load_entries,
            *self.kernel_module_dependency_entries,
            *self.kernel_module_alias_entries,
            *self.kernel_module_soft_dependency_entries,
            *self.kernel_module_uninterpreted_lines,
        )

        for relationship in relationships:
            if (
                id(
                    relationship.configuration
                )
                not in configuration_ids
            ):
                raise ValueError(
                    "kernel-module relationship must retain a configuration "
                    "from this exact ramdisk"
                )

        references = []

        for entry in self.kernel_module_load_entries:
            references.extend(
                entry.references
            )

        for entry in self.kernel_module_dependency_entries:
            references.append(
                entry.module
            )
            references.extend(
                entry.dependencies
            )

        for entry in self.kernel_module_alias_entries:
            references.append(
                entry.module
            )

        for entry in self.kernel_module_soft_dependency_entries:
            references.append(
                entry.module
            )
            references.extend(
                entry.pre
            )
            references.extend(
                entry.post
            )

        for reference in references:
            for candidate in reference.candidates:
                if id(
                    candidate
                ) not in module_ids:
                    raise ValueError(
                        "kernel-module relationship candidate must belong "
                        "to this exact ramdisk module population"
                    )

            if (
                reference.module is not None
                and id(
                    reference.module
                ) not in module_ids
            ):
                raise ValueError(
                    "resolved kernel-module relationship must belong "
                    "to this exact ramdisk module population"
                )

    @property
    def contains_init(
        self,
    ) -> bool:
        return bool(
            self.init_files
        )

    @property
    def contains_fstab(
        self,
    ) -> bool:
        return bool(
            self.fstabs
        )

    @property
    def contains_ueventd(
        self,
    ) -> bool:
        return bool(
            self.ueventd_files
        )

    @property
    def contains_kernel_modules(
        self,
    ) -> bool:
        return bool(
            self.kernel_modules
        )

    @property
    def contains_kernel_module_configuration(
        self,
    ) -> bool:
        return bool(
            self.kernel_module_configurations
        )

    @property
    def has_bootconfig(
        self,
    ) -> bool:
        return (
            self.boot_image.bootconfig
            is not None
        )

    @property
    def cpio_entry_count(
        self,
    ) -> int:
        return self.ramdisk.entry_count

    @property
    def boot_family_name(
        self,
    ) -> str | None:
        return self.ramdisk.boot_image_name
