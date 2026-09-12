from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.parsing.sflb import (
    AndroidParsedSflbEntry,
)
from treeforge.android.parsing.boot.boot import (
    ParsedBootImageMetadata,
)
from treeforge.android.parsing.boot.bootconfig import (
    ParsedAndroidBootconfig,
)
from treeforge.android.parsing.boot.vendor_boot import (
    ParsedVendorBootImageMetadata,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)
from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
)
from treeforge.android.parsing.elf import (
    AndroidElfParsingResult,
)
from treeforge.android.parsing.art_runtime import (
    AndroidArtRuntimeParsingResult,
)
from treeforge.android.parsing.dex import (
    AndroidStandaloneDexParsingResult,
)
from treeforge.android.parsing.classpath import (
    AndroidClasspathParsingResult,
)
from treeforge.android.parsing.apk import (
    AndroidApkParsingResult,
)

from treeforge.android.parsing.avf import (
    AndroidAvfVmConfigParsingResult,
)
from treeforge.android.parsing.aconfig import (
    AndroidAconfigParsingResult,
)
from treeforge.android.parsing.input import (
    AndroidInputParsingResult,
)
from treeforge.android.parsing.font import (
    AndroidFontParsingResult,
)
from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveParsingResult,
)
from treeforge.android.parsing.shell_script import (
    AndroidShellScriptParsingResult,
)
from treeforge.android.parsing.certificate import (
    AndroidCertificateParsingResult,
)
from treeforge.android.parsing.structured_configuration import (
    AndroidStructuredConfigurationParsingResult,
)
from treeforge.android.parsing.kernel_module import (
    AndroidKernelModuleParsingResult,
    ParsedAndroidKernelModuleConfiguration,
)
from treeforge.android.parsing.linker import (
    ParsedAndroidLinkerConfiguration,
    ParsedAndroidLinkerProtobufConfiguration,
    ParsedAndroidNativeLibraryConfiguration,
)
from treeforge.android.parsing.kernel import (
    ParsedKernelImage,
)
from treeforge.android.parsing.ramdisk import (
    ParsedAndroidRamdisk,
)
from treeforge.android.parsing.apex import (
    ParsedApexContainer,
)
from treeforge.android.parsing.bmp import (
    AndroidParsedBmp,
)
from treeforge.android.parsing.dtb import (
    AndroidParsedDtboEntry,
    ParsedFdt,
)
from treeforge.android.parsing.boot.vendor_ramdisk_table import (
    ParsedVendorRamdiskTable,
)
from treeforge.android.parsing.avb import (
    AndroidParsedAvbFooter,
    AndroidParsedVbmeta,
)
from treeforge.android.parsing.bootloader import (
    AndroidParsedBootloaderChild,
    AndroidParsedBootFirmwarePayload,
    AndroidParsedFbpt,
    AndroidParsedUfpkDescriptor,
    AndroidParsedUfpk,
    AndroidParsedUfsDescriptor,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


def _validate_boot_component_artifacts(
    *,
    partition: InventoryPartition,
    component_artifacts: tuple[
        ExtractedArtifact,
        ...,
    ],
) -> None:
    """
    Validate exact boot-family component provenance retained from Extraction.

    Extraction remains authoritative for physical container structure,
    component offsets/sizes, and materialization. Parsing preserves those
    already-established artifact identities without re-decoding the image.
    """

    if not isinstance(
        component_artifacts,
        tuple,
    ):
        raise TypeError(
            "component_artifacts must be a tuple"
        )

    semantic_names: list[str] = []

    for artifact in component_artifacts:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "component_artifacts must contain only "
                "ExtractedArtifact instances"
            )

        if (
            artifact.operation
            is not ExtractionOperation
            .BOOT_COMPONENT_EXTRACTION
        ):
            raise ValueError(
                "boot component artifact must be produced by "
                "BOOT_COMPONENT_EXTRACTION"
            )

        if (
            artifact.parent
            is not partition.artifact
        ):
            raise ValueError(
                "boot component artifact must be a direct child "
                "of the exact canonical boot-family partition artifact"
            )

        semantic_name = (
            artifact.semantic_name
        )

        if semantic_name is None:
            raise ValueError(
                "boot component artifact must preserve "
                "its canonical semantic identity"
            )

        semantic_names.append(
            semantic_name
        )

    if len(
        semantic_names
    ) != len(
        set(
            semantic_names
        )
    ):
        raise ValueError(
            "boot component artifacts must not contain "
            "duplicate semantic identities"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedBootSignature:
    """
    One canonical AVB/VBMeta boot-signature component.

    This is intentionally distinct from ParsedAvbVbmeta:

    - standalone ParsedAvbVbmeta is partition-backed;
    - embedded ParsedAvbVbmeta is AVB_REGION_EXTRACTION-backed;
    - ParsedBootSignature is an exact BOOT_COMPONENT_EXTRACTION child.

    Parsing owns only literal AVB/VBMeta decoding here. Trust, signing
    policy, applicability, and reconstruction decisions remain downstream.
    """

    artifact: ExtractedArtifact
    boot_image_artifact: ExtractedArtifact
    metadata: AndroidParsedVbmeta

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "boot-signature artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.boot_image_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "boot_image_artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.metadata,
            AndroidParsedVbmeta,
        ):
            raise TypeError(
                "boot-signature metadata must be AndroidParsedVbmeta"
            )

        if (
            self.artifact.operation
            is not ExtractionOperation.BOOT_COMPONENT_EXTRACTION
        ):
            raise ValueError(
                "boot-signature artifact must be a canonical "
                "BOOT_COMPONENT_EXTRACTION artifact"
            )

        if self.artifact.semantic_name != "boot_signature":
            raise ValueError(
                "boot-signature artifact must preserve canonical "
                "semantic_name='boot_signature'"
            )

        if self.artifact.parent is not self.boot_image_artifact:
            raise ValueError(
                "boot-signature artifact must retain exact canonical "
                "boot-image parent identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedBootImage:
    """
    Literal Parsing result for one canonical Android boot-family container.

    ``container_format`` identifies the physical header family established by
    Extraction:

    - android_boot
    - android_vendor_boot

    ``container_kind`` preserves the exact semantic container identity
    established upstream, for example:

    - boot
    - init_boot
    - recovery
    - pvmfw
    - vendor_boot
    - vendor_kernel_boot

    Parsing interprets semantic header fields and optional bootconfig content.
    Extraction remains authoritative for physical layout and component
    materialization.
    """

    partition: InventoryPartition
    container_format: str
    container_kind: str

    metadata: (
        ParsedBootImageMetadata
        | ParsedVendorBootImageMetadata
    )

    component_artifacts: tuple[
        ExtractedArtifact,
        ...,
    ] = ()

    bootconfig_artifact: (
        ExtractedArtifact
        | None
    ) = None

    bootconfig: (
        ParsedAndroidBootconfig
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.partition,
            InventoryPartition,
        ):
            raise TypeError(
                "partition must be an InventoryPartition"
            )

        if not isinstance(
            self.container_format,
            str,
        ):
            raise TypeError(
                "container_format must be a string"
            )

        if self.container_format not in {
            "android_boot",
            "android_vendor_boot",
        }:
            raise ValueError(
                "unsupported canonical boot container format: "
                f"{self.container_format}"
            )

        if not isinstance(
            self.container_kind,
            str,
        ):
            raise TypeError(
                "container_kind must be a string"
            )

        if not self.container_kind:
            raise ValueError(
                "container_kind cannot be empty"
            )

        if self.container_format == "android_boot":
            if not isinstance(
                self.metadata,
                ParsedBootImageMetadata,
            ):
                raise TypeError(
                    "android_boot metadata must be "
                    "ParsedBootImageMetadata"
                )

        else:
            if not isinstance(
                self.metadata,
                ParsedVendorBootImageMetadata,
            ):
                raise TypeError(
                    "android_vendor_boot metadata must be "
                    "ParsedVendorBootImageMetadata"
                )

        _validate_boot_component_artifacts(
            partition=self.partition,
            component_artifacts=(
                self.component_artifacts
            ),
        )

        for artifact in self.component_artifacts:
            container_kind_facts = tuple(
                fact.value
                for fact in artifact.facts
                if fact.name == "container_kind"
            )

            if len(container_kind_facts) != 1:
                raise ValueError(
                    "boot component must preserve exactly one "
                    "canonical container_kind fact"
                )

            if (
                container_kind_facts[0]
                != self.container_kind
            ):
                raise ValueError(
                    "boot component container identity does not "
                    "match ParsedBootImage"
                )

        if (
            self.bootconfig_artifact is None
        ) != (
            self.bootconfig is None
        ):
            raise ValueError(
                "bootconfig_artifact and bootconfig must either "
                "both be present or both be absent"
            )

        if (
            self.bootconfig_artifact is not None
            and not isinstance(
                self.bootconfig_artifact,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "bootconfig_artifact must be an "
                "ExtractedArtifact or None"
            )

        if (
            self.bootconfig is not None
            and not isinstance(
                self.bootconfig,
                ParsedAndroidBootconfig,
            )
        ):
            raise TypeError(
                "bootconfig must be a "
                "ParsedAndroidBootconfig or None"
            )

        bootconfig_components = tuple(
            artifact
            for artifact in self.component_artifacts
            if artifact.semantic_name == "bootconfig"
        )

        if len(bootconfig_components) > 1:
            raise ValueError(
                "boot container contains ambiguous "
                "bootconfig components"
            )

        expected_bootconfig = (
            bootconfig_components[0]
            if bootconfig_components
            else None
        )

        if (
            self.bootconfig_artifact
            is not expected_bootconfig
        ):
            raise ValueError(
                "bootconfig_artifact must preserve the exact "
                "bootconfig member of component_artifacts"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAvbVbmeta:
    """
    One literal AVB VBMeta source consumed by Parsing.

    The source is artifact-centric rather than partition-centric because AVB
    VBMeta may belong to a directly accessible partition image or to a nested
    canonical image such as an APEX payload.

    Parsing preserves exact Extraction identity and literal AVB observations.
    Trust topology, applicability, signing policy, and device-level verified
    boot conclusions remain downstream responsibilities.
    """

    artifact: ExtractedArtifact
    container_artifact: ExtractedArtifact
    metadata: AndroidParsedVbmeta

    partition: InventoryPartition | None = None

    footer_artifact: ExtractedArtifact | None = None
    footer: AndroidParsedAvbFooter | None = None

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

        if not isinstance(
            self.container_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "container_artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.metadata,
            AndroidParsedVbmeta,
        ):
            raise TypeError(
                "metadata must be an AndroidParsedVbmeta"
            )

        if (
            self.partition is not None
            and not isinstance(
                self.partition,
                InventoryPartition,
            )
        ):
            raise TypeError(
                "partition must be an InventoryPartition or None"
            )

        if (
            self.footer_artifact is not None
            and not isinstance(
                self.footer_artifact,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "footer_artifact must be an "
                "ExtractedArtifact or None"
            )

        if (
            self.footer is not None
            and not isinstance(
                self.footer,
                AndroidParsedAvbFooter,
            )
        ):
            raise TypeError(
                "footer must be an AndroidParsedAvbFooter or None"
            )

        if (
            self.footer_artifact is None
        ) != (
            self.footer is None
        ):
            raise ValueError(
                "footer_artifact and footer must either both "
                "be present or both be absent"
            )

        if self.artifact is self.container_artifact:
            if self.partition is None:
                raise ValueError(
                    "standalone VBMeta source must retain its "
                    "exact InventoryPartition"
                )

            if (
                self.partition.artifact
                is not self.artifact
            ):
                raise ValueError(
                    "standalone VBMeta partition must retain "
                    "the exact VBMeta Extraction artifact"
                )

            if self.footer is not None:
                raise ValueError(
                    "standalone VBMeta source cannot carry an "
                    "embedded AVB footer association"
                )

            return

        if (
            self.artifact.parent
            is not self.container_artifact
        ):
            raise ValueError(
                "embedded VBMeta artifact must retain its exact "
                "containing Extraction artifact"
            )

        if (
            self.artifact.operation
            is not ExtractionOperation.AVB_REGION_EXTRACTION
        ):
            raise ValueError(
                "embedded VBMeta artifact must be an "
                "AVB_REGION_EXTRACTION artifact"
            )

        if self.footer_artifact is None:
            raise ValueError(
                "embedded VBMeta source must retain its exact "
                "canonical AVB footer artifact"
            )

        if (
            self.footer_artifact.parent
            is not self.container_artifact
        ):
            raise ValueError(
                "embedded VBMeta footer must share the exact "
                "containing Extraction artifact"
            )

        if (
            self.footer_artifact.operation
            is not ExtractionOperation.AVB_REGION_EXTRACTION
        ):
            raise ValueError(
                "embedded VBMeta footer must be an "
                "AVB_REGION_EXTRACTION artifact"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAvbRegion:
    """
    Explicit Parsing disposition for one Extraction-owned AVB region.

    No AVB_REGION_EXTRACTION artifact may disappear merely because its raw
    payload has no additional Parsing-owned structure.

    Dispositions:

    parsed
        The region contains VBMeta and has a ParsedAvbVbmeta result.

    fact_derived
        Literal structure is already represented by authoritative Extraction
        facts and Parsing records that disposition without rediscovering it.

    preserved
        The raw physical region is canonical evidence whose semantics are
        represented by another parsed source (for example a VBMeta hashtree
        descriptor). Parsing preserves the exact artifact without decoding
        the raw Merkle-tree or FEC payload itself.
    """

    artifact: ExtractedArtifact
    disposition: str
    vbmeta: ParsedAvbVbmeta | None = None

    _VALID_DISPOSITIONS = frozenset(
        {
            "parsed",
            "fact_derived",
            "preserved",
        }
    )

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
            self.artifact.operation
            is not ExtractionOperation.AVB_REGION_EXTRACTION
        ):
            raise ValueError(
                "AVB region disposition must retain an exact "
                "AVB_REGION_EXTRACTION artifact"
            )

        if not isinstance(
            self.disposition,
            str,
        ):
            raise TypeError(
                "disposition must be a string"
            )

        if (
            self.disposition
            not in self._VALID_DISPOSITIONS
        ):
            raise ValueError(
                "unsupported AVB Parsing disposition: "
                f"{self.disposition}"
            )

        if (
            self.vbmeta is not None
            and not isinstance(
                self.vbmeta,
                ParsedAvbVbmeta,
            )
        ):
            raise TypeError(
                "vbmeta must be a ParsedAvbVbmeta or None"
            )

        if self.disposition == "parsed":
            if self.vbmeta is None:
                raise ValueError(
                    "parsed AVB region must retain its "
                    "ParsedAvbVbmeta result"
                )

            if (
                self.vbmeta.artifact
                is not self.artifact
            ):
                raise ValueError(
                    "parsed AVB region must retain exact "
                    "ParsedAvbVbmeta artifact identity"
                )

        elif self.vbmeta is not None:
            raise ValueError(
                "only parsed AVB regions may carry a VBMeta result"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedBootloaderChild:
    """
    Associate one literal parsed bootloader-child structure with the exact
    canonical Extraction artifact that supplied it.

    Extraction owns FBPK container decoding and child materialization.
    Parsing owns only literal decoding of the child payload format.

    Device-level interpretation belongs to Android Device Universe.
    """

    artifact: ExtractedArtifact
    parsed: AndroidParsedBootloaderChild

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

        if not isinstance(
            self.parsed,
            (
                AndroidParsedBootFirmwarePayload,
                AndroidParsedFbpt,
                AndroidParsedUfsDescriptor,
                AndroidParsedUfpk,
                AndroidParsedUfpkDescriptor,
            ),
        ):
            raise TypeError(
                "parsed must be a supported bootloader-child "
                "Parsing result"
            )



@dataclass(
    frozen=True,
    slots=True,
)
class ParsedBootloaderChildDisposition:
    """
    Explicit Parsing disposition for one canonical bootloader-child input.

    Every Extraction-owned artifact admitted into Bootloader Child Parsing
    receives exactly one disposition.

    parsed
        The artifact has a literal ParsedBootloaderChild result.

    opaque
        The artifact is canonical and retained exactly, but Parsing has no
        proven structured decoder for its intrinsic payload format.
    """

    artifact: ExtractedArtifact
    disposition: str
    parsed: ParsedBootloaderChild | None = None

    _VALID_DISPOSITIONS = frozenset(
        {
            "parsed",
            "opaque",
        }
    )

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
            self.artifact.operation
            not in {
                ExtractionOperation
                .FBPK_ENTRY_EXTRACTION,
                ExtractionOperation
                .BOOT_FIRMWARE_PAYLOAD_EXTRACTION,
                ExtractionOperation
                .UFPK_DESCRIPTOR_EXTRACTION,
            }
        ):
            raise ValueError(
                "bootloader child disposition must retain a "
                "canonical bootloader Parsing input artifact"
            )

        if not isinstance(
            self.disposition,
            str,
        ):
            raise TypeError(
                "disposition must be a string"
            )

        if (
            self.disposition
            not in self._VALID_DISPOSITIONS
        ):
            raise ValueError(
                "unsupported bootloader Parsing disposition: "
                f"{self.disposition}"
            )

        if (
            self.parsed is not None
            and not isinstance(
                self.parsed,
                ParsedBootloaderChild,
            )
        ):
            raise TypeError(
                "parsed must be a ParsedBootloaderChild or None"
            )

        if self.disposition == "parsed":
            if self.parsed is None:
                raise ValueError(
                    "parsed bootloader disposition must retain "
                    "its ParsedBootloaderChild"
                )

            if (
                self.parsed.artifact
                is not self.artifact
            ):
                raise ValueError(
                    "parsed bootloader disposition must retain "
                    "exact canonical artifact identity"
                )

        elif self.parsed is not None:
            raise ValueError(
                "opaque bootloader disposition cannot carry "
                "a parsed result"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsingResult:
    """
    Canonical immutable result of the Android Parsing stage.

    Parsing records what each prepared source says while retaining the source
    inventory and exact canonical boot-partition identities that produced
    those observations.

    Cross-source interpretation belongs to the later AndroidDeviceUniverse
    stage.
    """

    filesystem_inventory: FilesystemMetadataInventory
    source_inventory: AndroidModelSourceInventory
    filesystem: AndroidFilesystemParsingResult
    elf: AndroidElfParsingResult

    art_runtime: AndroidArtRuntimeParsingResult = (
        AndroidArtRuntimeParsingResult()
    )

    dex: AndroidStandaloneDexParsingResult = (
        AndroidStandaloneDexParsingResult()
    )

    classpath: AndroidClasspathParsingResult = (
        AndroidClasspathParsingResult()
    )

    aconfig: AndroidAconfigParsingResult = (
        AndroidAconfigParsingResult()
    )

    input: AndroidInputParsingResult = (
        AndroidInputParsingResult()
    )

    font: AndroidFontParsingResult = (
        AndroidFontParsingResult()
    )

    java_archive: AndroidJavaArchiveParsingResult = (
        AndroidJavaArchiveParsingResult()
    )

    shell_script: AndroidShellScriptParsingResult = (
        AndroidShellScriptParsingResult()
    )

    certificate: AndroidCertificateParsingResult = (
        AndroidCertificateParsingResult()
    )

    structured_configuration: (
        AndroidStructuredConfigurationParsingResult
    ) = AndroidStructuredConfigurationParsingResult()

    apk: AndroidApkParsingResult = (
        AndroidApkParsingResult()
    )

    avf_vm_config: AndroidAvfVmConfigParsingResult = (
        AndroidAvfVmConfigParsingResult()
    )

    kernel_modules: AndroidKernelModuleParsingResult = (
        AndroidKernelModuleParsingResult()
    )

    kernel_module_configurations: tuple[
        ParsedAndroidKernelModuleConfiguration,
        ...,
    ] = ()

    linker_configurations: tuple[
        ParsedAndroidLinkerConfiguration,
        ...,
    ] = ()

    linker_protobuf_configurations: tuple[
        ParsedAndroidLinkerProtobufConfiguration,
        ...,
    ] = ()

    native_library_configurations: tuple[
        ParsedAndroidNativeLibraryConfiguration,
        ...,
    ] = ()

    apex: tuple[
        ParsedApexContainer,
        ...,
    ] = ()

    bmp: tuple[
        AndroidParsedBmp,
        ...,
    ] = ()

    sflb: tuple[
        AndroidParsedSflbEntry,
        ...,
    ] = ()

    dtbo: tuple[
        AndroidParsedDtboEntry,
        ...,
    ] = ()

    boot_dtbs: tuple[
        ParsedFdt,
        ...,
    ] = ()

    vendor_ramdisk_tables: tuple[
        ParsedVendorRamdiskTable,
        ...,
    ] = ()

    vbmeta: tuple[
        ParsedAvbVbmeta,
        ...,
    ] = ()

    avb_regions: tuple[
        ParsedAvbRegion,
        ...,
    ] = ()

    bootloader: tuple[
        ParsedBootloaderChild,
        ...,
    ] = ()

    bootloader_children: tuple[
        ParsedBootloaderChildDisposition,
        ...,
    ] = ()

    ramdisks: tuple[
        ParsedAndroidRamdisk,
        ...,
    ] = ()

    kernels: tuple[
        ParsedKernelImage,
        ...,
    ] = ()

    boot_images: tuple[
        ParsedBootImage,
        ...,
    ] = ()

    boot_signatures: tuple[
        ParsedBootSignature,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if not isinstance(
            self.source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an "
                "AndroidModelSourceInventory"
            )

        if not isinstance(
            self.filesystem,
            AndroidFilesystemParsingResult,
        ):
            raise TypeError(
                "filesystem must be an "
                "AndroidFilesystemParsingResult"
            )

        if not isinstance(
            self.elf,
            AndroidElfParsingResult,
        ):
            raise TypeError(
                "elf must be an AndroidElfParsingResult"
            )

        if not isinstance(
            self.art_runtime,
            AndroidArtRuntimeParsingResult,
        ):
            raise TypeError(
                "art_runtime must be an "
                "AndroidArtRuntimeParsingResult"
            )

        if not isinstance(
            self.dex,
            AndroidStandaloneDexParsingResult,
        ):
            raise TypeError(
                "dex must be an AndroidStandaloneDexParsingResult"
            )

        if not isinstance(
            self.classpath,
            AndroidClasspathParsingResult,
        ):
            raise TypeError(
                "classpath must be an "
                "AndroidClasspathParsingResult"
            )

        if not isinstance(
            self.aconfig,
            AndroidAconfigParsingResult,
        ):
            raise TypeError(
                "aconfig must be an "
                "AndroidAconfigParsingResult"
            )

        if not isinstance(
            self.input,
            AndroidInputParsingResult,
        ):
            raise TypeError(
                "input must be an "
                "AndroidInputParsingResult"
            )

        if not isinstance(
            self.font,
            AndroidFontParsingResult,
        ):
            raise TypeError(
                "font must be an "
                "AndroidFontParsingResult"
            )

        if not isinstance(
            self.java_archive,
            AndroidJavaArchiveParsingResult,
        ):
            raise TypeError(
                "java_archive must be an "
                "AndroidJavaArchiveParsingResult"
            )

        if not isinstance(
            self.shell_script,
            AndroidShellScriptParsingResult,
        ):
            raise TypeError(
                "shell_script must be an "
                "AndroidShellScriptParsingResult"
            )

        if not isinstance(
            self.certificate,
            AndroidCertificateParsingResult,
        ):
            raise TypeError(
                "certificate must be an "
                "AndroidCertificateParsingResult"
            )

        if not isinstance(
            self.structured_configuration,
            AndroidStructuredConfigurationParsingResult,
        ):
            raise TypeError(
                "structured_configuration must be an "
                "AndroidStructuredConfigurationParsingResult"
            )

        if not isinstance(
            self.apk,
            AndroidApkParsingResult,
        ):
            raise TypeError(
                "apk must be an AndroidApkParsingResult"
            )

        if not isinstance(
            self.avf_vm_config,
            AndroidAvfVmConfigParsingResult,
        ):
            raise TypeError(
                "avf_vm_config must be an "
                "AndroidAvfVmConfigParsingResult"
            )

        canonical_filesystems = {
            value.source_name: value
            for value
            in self.source_inventory.filesystems
        }

        for parsed in self.apk.packages:
            canonical_filesystem = (
                canonical_filesystems.get(
                    parsed.source.source_name
                )
            )

            if canonical_filesystem is None:
                raise ValueError(
                    "APK package must reference a filesystem "
                    "from the canonical "
                    "AndroidModelSourceInventory"
                )

            if (
                parsed.source.filesystem_source
                is not canonical_filesystem
            ):
                raise ValueError(
                    "APK package must reuse the exact canonical "
                    "parser filesystem source"
                )

        for candidate in self.apk.candidates:
            canonical_filesystem = (
                canonical_filesystems.get(
                    candidate.source.source_name
                )
            )

            if canonical_filesystem is None:
                raise ValueError(
                    "APK candidate must reference a filesystem "
                    "from the canonical "
                    "AndroidModelSourceInventory"
                )

            if (
                candidate.source.filesystem_source
                is not canonical_filesystem
            ):
                raise ValueError(
                    "APK candidate must reuse the exact canonical "
                    "parser filesystem source"
                )

        for candidate in (
            self.avf_vm_config.candidates
        ):
            canonical_filesystem = (
                canonical_filesystems.get(
                    candidate.source.source_name
                )
            )

            if canonical_filesystem is None:
                raise ValueError(
                    "AVF candidate must reference a filesystem "
                    "from the canonical "
                    "AndroidModelSourceInventory"
                )

            if (
                candidate.source.filesystem_source
                is not canonical_filesystem
            ):
                raise ValueError(
                    "AVF candidate must reuse the exact canonical "
                    "parser filesystem source"
                )

        for parsed in (
            self.avf_vm_config.configurations
        ):
            canonical_filesystem = (
                canonical_filesystems.get(
                    parsed.source.source_name
                )
            )

            if canonical_filesystem is None:
                raise ValueError(
                    "AVF VM configuration must reference "
                    "a filesystem from the canonical "
                    "AndroidModelSourceInventory"
                )

            if (
                parsed.source.filesystem_source
                is not canonical_filesystem
            ):
                raise ValueError(
                    "AVF VM configuration must reuse the "
                    "exact canonical parser filesystem source"
                )

        elf_identities = {
            parsed.source.identity_key: parsed
            for parsed
            in self.elf.elf_files
        }

        for oat in self.art_runtime.oat_files:
            canonical_elf = elf_identities.get(
                oat.elf.source.identity_key
            )

            if canonical_elf is None:
                raise ValueError(
                    "ART-runtime OAT observation must reference "
                    "an ELF from the canonical "
                    "AndroidElfParsingResult"
                )

            if oat.elf is not canonical_elf:
                raise ValueError(
                    "ART-runtime OAT observation must reuse the "
                    "exact canonical ParsedAndroidElf object"
                )

        source_identities = {
            source.identity_key: source
            for source
            in self.source_inventory.sources
        }

        source_owner_groups = (
            (
                "filesystem.init",
                frozenset({
                    AndroidModelSourceKind.INIT,
                }),
                tuple(
                    value.source
                    for value
                    in self.filesystem.init_files
                ),
            ),
            (
                "filesystem.fstab",
                frozenset({
                    AndroidModelSourceKind.FSTAB,
                }),
                tuple(
                    value.source
                    for value
                    in self.filesystem.fstabs
                ),
            ),
            (
                "filesystem.ueventd",
                frozenset({
                    AndroidModelSourceKind.UEVENTD,
                }),
                tuple(
                    value.source
                    for value
                    in self.filesystem.ueventd_files
                ),
            ),
            (
                "filesystem.vintf",
                frozenset({
                    AndroidModelSourceKind.VINTF,
                }),
                tuple(
                    value.source
                    for value
                    in self.filesystem.vintf_documents
                ),
            ),
            (
                "filesystem.property",
                frozenset({
                    AndroidModelSourceKind.PROPERTY,
                }),
                tuple(
                    value.source
                    for value
                    in self.filesystem.property_files
                ),
            ),
            (
                "filesystem.selinux",
                frozenset({
                    AndroidModelSourceKind.SELINUX,
                }),
                tuple(
                    value.source
                    for value
                    in self.filesystem.selinux_sources
                ),
            ),
            (
                "linker",
                frozenset({
                    AndroidModelSourceKind
                    .LINKER_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in (
                        *self.linker_configurations,
                        *self.linker_protobuf_configurations,
                    )
                ),
            ),
            (
                "native_library",
                frozenset({
                    AndroidModelSourceKind
                    .NATIVE_LIBRARY_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in self.native_library_configurations
                ),
            ),
            (
                "kernel_module_configuration",
                frozenset({
                    AndroidModelSourceKind
                    .KERNEL_MODULE_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in self.kernel_module_configurations
                ),
            ),
            (
                "art_runtime",
                frozenset({
                    AndroidModelSourceKind.ART_RUNTIME,
                }),
                tuple(
                    value.source
                    for value
                    in (
                        *self.art_runtime.vdex_files,
                        *self.art_runtime.art_images,
                    )
                ),
            ),
            (
                "dex",
                frozenset({
                    AndroidModelSourceKind.DEX,
                }),
                tuple(
                    self.dex.sources
                ),
            ),
            (
                "classpath",
                frozenset({
                    AndroidModelSourceKind
                    .CLASSPATH_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in self.classpath.configurations
                ),
            ),
            (
                "aconfig",
                frozenset({
                    AndroidModelSourceKind
                    .ACONFIG_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in self.aconfig.configurations
                ),
            ),
            (
                "input",
                frozenset({
                    AndroidModelSourceKind.INPUT_KEY_LAYOUT,
                    AndroidModelSourceKind
                    .INPUT_KEY_CHARACTER_MAP,
                    AndroidModelSourceKind
                    .INPUT_DEVICE_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in self.input.configurations
                ),
            ),
            (
                "font",
                frozenset({
                    AndroidModelSourceKind.FONT,
                }),
                tuple(
                    value.source
                    for value
                    in self.font.fonts
                ),
            ),
            (
                "java_archive",
                frozenset({
                    AndroidModelSourceKind.JAVA_ARCHIVE,
                }),
                tuple(
                    value.source
                    for value
                    in self.java_archive.archives
                ),
            ),
            (
                "shell_script",
                frozenset({
                    AndroidModelSourceKind.SHELL_SCRIPT,
                }),
                tuple(
                    value.source
                    for value
                    in self.shell_script.scripts
                ),
            ),
            (
                "certificate",
                frozenset({
                    AndroidModelSourceKind.CERTIFICATE,
                }),
                tuple(
                    value.source
                    for value
                    in self.certificate.sources
                ),
            ),
            (
                "structured_configuration",
                frozenset({
                    AndroidModelSourceKind.AVB_PUBLIC_KEY,
                    AndroidModelSourceKind.CGROUP_CONFIGURATION,
                    AndroidModelSourceKind.MKE2FS_CONFIGURATION,
                    AndroidModelSourceKind
                    .RECOVERY_WIPE_CONFIGURATION,
                    AndroidModelSourceKind.BLUEPRINT,
                    AndroidModelSourceKind
                    .SENSOR_HAL_CONFIGURATION,
                    AndroidModelSourceKind
                    .SENSOR_REGISTRY_CONFIGURATION,
                }),
                tuple(
                    value.source
                    for value
                    in (
                        *self.structured_configuration
                        .avb_public_keys,
                        *self.structured_configuration
                        .cgroup_configurations,
                        *self.structured_configuration
                        .mke2fs_configurations,
                        *self.structured_configuration
                        .recovery_wipe_configurations,
                        *self.structured_configuration
                        .blueprints,
                        *self.structured_configuration
                        .sensor_hal_configurations,
                        *self.structured_configuration
                        .sensor_registry_configurations,
                    )
                ),
            ),
            (
                "ota_certificate_archive",
                frozenset({
                    AndroidModelSourceKind
                    .OTA_CERTIFICATE_ARCHIVE,
                }),
                tuple(
                    value.source
                    for value
                    in self.certificate.ota_archives
                ),
            ),
        )

        declared_owned_kinds = set()

        observed_sources = []

        for (
            owner_name,
            allowed_kinds,
            owned_sources,
        ) in source_owner_groups:
            declared_owned_kinds.update(
                allowed_kinds
            )

            for source in owned_sources:
                if source is None:
                    raise ValueError(
                        "inventory-backed Parsing source owner "
                        f"{owner_name!r} contains a missing "
                        "canonical AndroidModelSource"
                    )

                if source.kind not in allowed_kinds:
                    raise ValueError(
                        "Parsing source owner "
                        f"{owner_name!r} claimed unexpected "
                        f"source kind {source.kind.value!r}"
                    )

                observed_sources.append(
                    source
                )

        enum_source_kinds = set(
            AndroidModelSourceKind
        )

        if (
            declared_owned_kinds
            != enum_source_kinds
        ):
            missing_kinds = tuple(
                sorted(
                    (
                        kind.value
                        for kind
                        in (
                            enum_source_kinds
                            - declared_owned_kinds
                        )
                    )
                )
            )

            extra_kinds = tuple(
                sorted(
                    (
                        kind.value
                        for kind
                        in (
                            declared_owned_kinds
                            - enum_source_kinds
                        )
                    )
                )
            )

            raise ValueError(
                "global Parsing Source Inventory ownership "
                "registry does not exactly cover "
                "AndroidModelSourceKind; "
                f"missing={missing_kinds!r}, "
                f"extra={extra_kinds!r}"
            )

        expected_global_source_ids = tuple(
            id(source)
            for source
            in self.source_inventory.sources
        )

        observed_global_source_ids = tuple(
            id(source)
            for source
            in observed_sources
        )

        if len(
            observed_global_source_ids
        ) != len(
            set(
                observed_global_source_ids
            )
        ):
            raise ValueError(
                "global Parsing Source Inventory ownership "
                "contains a canonical AndroidModelSource "
                "claimed by more than one owner"
            )

        if (
            set(
                expected_global_source_ids
            )
            != set(
                observed_global_source_ids
            )
        ):
            raise ValueError(
                "global Parsing Source Inventory ownership "
                "must conserve every canonical "
                "AndroidModelSource exactly once"
            )

        if len(
            expected_global_source_ids
        ) != len(
            observed_global_source_ids
        ):
            raise ValueError(
                "global Parsing Source Inventory ownership "
                "must preserve one source-level observation "
                "per canonical AndroidModelSource"
            )

        for source in observed_sources:
            canonical_source = source_identities.get(
                source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "global Parsing Source Inventory owner "
                    "references a source outside the canonical "
                    "AndroidModelSourceInventory"
                )

            if source is not canonical_source:
                raise ValueError(
                    "global Parsing Source Inventory owner "
                    "must reuse the exact canonical "
                    "AndroidModelSource object"
                )

        structured_groups = (
            (
                AndroidModelSourceKind.AVB_PUBLIC_KEY,
                self.structured_configuration.avb_public_keys,
            ),
            (
                AndroidModelSourceKind.CGROUP_CONFIGURATION,
                self.structured_configuration
                .cgroup_configurations,
            ),
            (
                AndroidModelSourceKind.MKE2FS_CONFIGURATION,
                self.structured_configuration
                .mke2fs_configurations,
            ),
            (
                AndroidModelSourceKind
                .RECOVERY_WIPE_CONFIGURATION,
                self.structured_configuration
                .recovery_wipe_configurations,
            ),
            (
                AndroidModelSourceKind.BLUEPRINT,
                self.structured_configuration.blueprints,
            ),
            (
                AndroidModelSourceKind
                .SENSOR_HAL_CONFIGURATION,
                self.structured_configuration
                .sensor_hal_configurations,
            ),
            (
                AndroidModelSourceKind
                .SENSOR_REGISTRY_CONFIGURATION,
                self.structured_configuration
                .sensor_registry_configurations,
            ),
        )

        for kind, parsed_values in structured_groups:
            expected_sources = {
                id(source): source
                for source
                in self.source_inventory.sources
                if source.kind is kind
            }

            parsed_sources = {
                id(parsed.source): parsed.source
                for parsed in parsed_values
            }

            if (
                set(expected_sources)
                != set(parsed_sources)
            ):
                raise ValueError(
                    "structured configuration Parsing "
                    f"must conserve every canonical "
                    f"{kind.value!r} source exactly once"
                )

            for parsed in parsed_values:
                canonical_source = source_identities.get(
                    parsed.source.identity_key
                )

                if canonical_source is None:
                    raise ValueError(
                        "structured configuration must "
                        "reference a source from the canonical "
                        "AndroidModelSourceInventory"
                    )

                if parsed.source is not canonical_source:
                    raise ValueError(
                        "structured configuration must reuse "
                        "the exact canonical "
                        "AndroidModelSource object"
                    )

        expected_certificate_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.CERTIFICATE
            )
        }

        parsed_certificate_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.certificate.sources
        }

        if (
            set(
                expected_certificate_sources
            )
            != set(
                parsed_certificate_sources
            )
        ):
            raise ValueError(
                "certificate Parsing must conserve every canonical "
                "CERTIFICATE source exactly once"
            )

        expected_ota_certificate_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .OTA_CERTIFICATE_ARCHIVE
            )
        }

        parsed_ota_certificate_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.certificate.ota_archives
        }

        if (
            set(
                expected_ota_certificate_sources
            )
            != set(
                parsed_ota_certificate_sources
            )
        ):
            raise ValueError(
                "certificate Parsing must conserve every canonical "
                "OTA_CERTIFICATE_ARCHIVE source exactly once"
            )

        for parsed in (
            *self.certificate.sources,
            *self.certificate.ota_archives,
        ):
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "certificate observation must reference a source "
                    "from the canonical AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "certificate observation must reuse the exact "
                    "canonical AndroidModelSource object"
                )

        expected_java_archive_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.JAVA_ARCHIVE
            )
        }

        parsed_java_archive_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.java_archive.archives
        }

        if (
            set(
                expected_java_archive_sources
            )
            != set(
                parsed_java_archive_sources
            )
        ):
            raise ValueError(
                "Java archive Parsing must conserve every canonical "
                "JAVA_ARCHIVE source exactly once"
            )

        for parsed in self.java_archive.archives:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "Java archive must reference a source from the "
                    "canonical AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "Java archive must reuse the exact canonical "
                    "AndroidModelSource object"
                )

        expected_shell_script_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.SHELL_SCRIPT
            )
        }

        parsed_shell_script_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.shell_script.scripts
        }

        if (
            set(
                expected_shell_script_sources
            )
            != set(
                parsed_shell_script_sources
            )
        ):
            raise ValueError(
                "shell-script Parsing must conserve every canonical "
                "SHELL_SCRIPT source exactly once"
            )

        for parsed in self.shell_script.scripts:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "shell script must reference a source from the "
                    "canonical AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "shell script must reuse the exact canonical "
                    "AndroidModelSource object"
                )

        expected_font_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.FONT
            )
        }

        parsed_font_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.font.fonts
        }

        if (
            set(
                expected_font_sources
            )
            != set(
                parsed_font_sources
            )
        ):
            raise ValueError(
                "font Parsing must conserve every canonical "
                "FONT source exactly once"
            )

        for parsed in self.font.fonts:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "font must reference a source from the "
                    "canonical AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "font must reuse the exact canonical "
                    "AndroidModelSource object"
                )

        expected_input_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if source.kind in {
                AndroidModelSourceKind.INPUT_KEY_LAYOUT,
                AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP,
                AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION,
            }
        }

        parsed_input_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.input.configurations
        }

        if (
            set(
                expected_input_sources
            )
            != set(
                parsed_input_sources
            )
        ):
            raise ValueError(
                "input Parsing must conserve every canonical "
                "Android input source exactly once"
            )

        for parsed in self.input.configurations:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "input configuration must reference a source "
                    "from the canonical AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "input configuration must reuse the exact "
                    "canonical AndroidModelSource object"
                )

        expected_linker_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .LINKER_CONFIGURATION
            )
        }

        parsed_text_linker_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.linker_configurations
        }

        parsed_protobuf_linker_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.linker_protobuf_configurations
        }

        if (
            set(
                parsed_text_linker_sources
            )
            & set(
                parsed_protobuf_linker_sources
            )
        ):
            raise ValueError(
                "LINKER_CONFIGURATION source populations must "
                "not overlap between text and protobuf parsers"
            )

        parsed_linker_source_ids = (
            set(
                parsed_text_linker_sources
            )
            | set(
                parsed_protobuf_linker_sources
            )
        )

        if (
            set(
                expected_linker_sources
            )
            != parsed_linker_source_ids
        ):
            raise ValueError(
                "linker Parsing must conserve every canonical "
                "LINKER_CONFIGURATION source exactly once"
            )

        for parsed in (
            *self.linker_configurations,
            *self.linker_protobuf_configurations,
        ):
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "linker configuration must reference a source "
                    "from the canonical AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "linker configuration must reuse the exact "
                    "canonical AndroidModelSource object"
                )

        expected_native_library_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .NATIVE_LIBRARY_CONFIGURATION
            )
        }

        parsed_native_library_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.native_library_configurations
        }

        if (
            set(
                expected_native_library_sources
            )
            != set(
                parsed_native_library_sources
            )
        ):
            raise ValueError(
                "native_library_configurations must conserve every "
                "canonical NATIVE_LIBRARY_CONFIGURATION source "
                "exactly once"
            )

        for parsed in self.native_library_configurations:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "native-library configuration must reference "
                    "a source from the canonical "
                    "AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "native-library configuration must reuse the "
                    "exact canonical AndroidModelSource object"
                )

        for module in self.kernel_modules.modules:
            canonical_elf = elf_identities.get(
                module.elf.source.identity_key
            )

            if canonical_elf is None:
                raise ValueError(
                    "kernel module must reference an ELF from "
                    "the canonical AndroidElfParsingResult"
                )

            if module.elf is not canonical_elf:
                raise ValueError(
                    "kernel module must reuse the exact canonical "
                    "ParsedAndroidElf object"
                )

        expected_kernel_module_sources = {
            id(source): source
            for source
            in self.source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .KERNEL_MODULE_CONFIGURATION
            )
        }

        parsed_kernel_module_sources = {
            id(parsed.source): parsed.source
            for parsed
            in self.kernel_module_configurations
        }

        if (
            set(
                expected_kernel_module_sources
            )
            != set(
                parsed_kernel_module_sources
            )
        ):
            raise ValueError(
                "kernel_module_configurations must conserve every "
                "canonical KERNEL_MODULE_CONFIGURATION source exactly once"
            )

        for parsed in self.kernel_module_configurations:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "kernel-module configuration must reference "
                    "a source from the canonical "
                    "AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "kernel-module configuration must reuse the "
                    "exact canonical AndroidModelSource object"
                )

        for parsed in self.classpath.configurations:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "classpath configuration must reference "
                    "a source from the canonical "
                    "AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "classpath configuration must reuse the "
                    "exact canonical AndroidModelSource object"
                )

        for parsed in self.aconfig.configurations:
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "aconfig configuration must reference "
                    "a source from the canonical "
                    "AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "aconfig configuration must reuse the "
                    "exact canonical AndroidModelSource object"
                )

        for parsed in (
            *self.art_runtime.vdex_files,
            *self.art_runtime.art_images,
        ):
            canonical_source = source_identities.get(
                parsed.source.identity_key
            )

            if canonical_source is None:
                raise ValueError(
                    "ART-runtime filesystem observation must "
                    "reference a source from the canonical "
                    "AndroidModelSourceInventory"
                )

            if parsed.source is not canonical_source:
                raise ValueError(
                    "ART-runtime filesystem observation must "
                    "reuse the exact canonical "
                    "AndroidModelSource object"
                )

        if not isinstance(
            self.apex,
            tuple,
        ):
            raise TypeError(
                "apex must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedApexContainer,
            )
            for parsed
            in self.apex
        ):
            raise TypeError(
                "apex must contain only ParsedApexContainer entries"
            )

        apex_outer_ids = tuple(
            id(
                parsed.outer_container
            )
            for parsed
            in self.apex
        )

        if len(
            apex_outer_ids
        ) != len(
            set(
                apex_outer_ids
            )
        ):
            raise ValueError(
                "APEX Parsing result contains duplicate "
                "canonical outer-container identities"
            )

        apex_payload_ids = tuple(
            id(
                parsed.payload_artifact
            )
            for parsed
            in self.apex
        )

        if len(
            apex_payload_ids
        ) != len(
            set(
                apex_payload_ids
            )
        ):
            raise ValueError(
                "APEX Parsing result contains duplicate "
                "terminal payload identities"
            )

        if not isinstance(
            self.kernel_modules,
            AndroidKernelModuleParsingResult,
        ):
            raise TypeError(
                "kernel_modules must be an "
                "AndroidKernelModuleParsingResult"
            )

        if not isinstance(
            self.kernel_module_configurations,
            tuple,
        ):
            raise TypeError(
                "kernel_module_configurations must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidKernelModuleConfiguration,
            )
            for parsed
            in self.kernel_module_configurations
        ):
            raise TypeError(
                "kernel_module_configurations must contain only "
                "ParsedAndroidKernelModuleConfiguration entries"
            )

        elf_identities = {
            parsed.source.identity_key
            for parsed
            in self.elf.elf_files
        }

        for module in self.kernel_modules.modules:
            if (
                module.elf.source.identity_key
                not in elf_identities
            ):
                raise ValueError(
                    "kernel module must reference an ELF from the "
                    "canonical AndroidElfParsingResult"
                )

        if not isinstance(
            self.linker_configurations,
            tuple,
        ):
            raise TypeError(
                "linker_configurations must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidLinkerConfiguration,
            )
            for parsed
            in self.linker_configurations
        ):
            raise TypeError(
                "linker_configurations must contain only "
                "ParsedAndroidLinkerConfiguration entries"
            )

        linker_configuration_keys = tuple(
            (
                parsed.source.source_name,
                parsed.source.android_path.as_posix(),
            )
            for parsed
            in self.linker_configurations
        )

        if linker_configuration_keys != tuple(
            sorted(
                linker_configuration_keys
            )
        ):
            raise ValueError(
                "linker_configurations must use canonical "
                "source-name/Android-path order"
            )

        if len(
            linker_configuration_keys
        ) != len(
            set(
                linker_configuration_keys
            )
        ):
            raise ValueError(
                "linker_configurations must preserve unique "
                "canonical source identities"
            )

        if not isinstance(
            self.linker_protobuf_configurations,
            tuple,
        ):
            raise TypeError(
                "linker_protobuf_configurations must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidLinkerProtobufConfiguration,
            )
            for parsed
            in self.linker_protobuf_configurations
        ):
            raise TypeError(
                "linker_protobuf_configurations must contain only "
                "ParsedAndroidLinkerProtobufConfiguration entries"
            )

        linker_protobuf_configuration_keys = tuple(
            (
                parsed.source.source_name,
                parsed.source.android_path.as_posix(),
            )
            for parsed
            in self.linker_protobuf_configurations
        )

        if linker_protobuf_configuration_keys != tuple(
            sorted(
                linker_protobuf_configuration_keys
            )
        ):
            raise ValueError(
                "linker_protobuf_configurations must use canonical "
                "source-name/Android-path order"
            )

        if len(
            linker_protobuf_configuration_keys
        ) != len(
            set(
                linker_protobuf_configuration_keys
            )
        ):
            raise ValueError(
                "linker_protobuf_configurations must preserve unique "
                "canonical source identities"
            )

        if not isinstance(
            self.native_library_configurations,
            tuple,
        ):
            raise TypeError(
                "native_library_configurations must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidNativeLibraryConfiguration,
            )
            for parsed
            in self.native_library_configurations
        ):
            raise TypeError(
                "native_library_configurations must contain only "
                "ParsedAndroidNativeLibraryConfiguration entries"
            )

        native_library_configuration_keys = tuple(
            (
                parsed.source.source_name,
                parsed.source.android_path.as_posix(),
            )
            for parsed
            in self.native_library_configurations
        )

        if native_library_configuration_keys != tuple(
            sorted(
                native_library_configuration_keys
            )
        ):
            raise ValueError(
                "native_library_configurations must use canonical "
                "source-name/Android-path order"
            )

        if len(
            native_library_configuration_keys
        ) != len(
            set(
                native_library_configuration_keys
            )
        ):
            raise ValueError(
                "native_library_configurations must preserve unique "
                "canonical source identities"
            )

        if not isinstance(
            self.sflb,
            tuple,
        ):
            raise TypeError(
                "sflb must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                AndroidParsedSflbEntry,
            )
            for parsed in self.sflb
        ):
            raise TypeError(
                "sflb must contain only "
                "AndroidParsedSflbEntry entries"
            )

        if not isinstance(
            self.bmp,
            tuple,
        ):
            raise TypeError(
                "bmp must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                AndroidParsedBmp,
            )
            for parsed in self.bmp
        ):
            raise TypeError(
                "bmp must contain only AndroidParsedBmp entries"
            )

        if not isinstance(
            self.boot_dtbs,
            tuple,
        ):
            raise TypeError(
                "boot_dtbs must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedFdt,
            )
            for parsed
            in self.boot_dtbs
        ):
            raise TypeError(
                "boot_dtbs must contain only ParsedFdt entries"
            )

        boot_dtb_artifact_ids = tuple(
            id(
                parsed.artifact
            )
            for parsed
            in self.boot_dtbs
        )

        if len(
            boot_dtb_artifact_ids
        ) != len(
            set(
                boot_dtb_artifact_ids
            )
        ):
            raise ValueError(
                "boot_dtbs contains duplicate canonical "
                "Extraction artifact identity"
            )

        canonical_boot_dtb_component_ids = {
            id(
                artifact
            )
            for image
            in self.boot_images
            for artifact
            in image.component_artifacts
            if artifact.semantic_name == "dtb"
        }

        for parsed in self.boot_dtbs:
            artifact = parsed.artifact

            if (
                artifact.operation
                is not ExtractionOperation
                .FDT_MEMBER_EXTRACTION
            ):
                raise ValueError(
                    "boot_dtbs must originate from "
                    "FDT_MEMBER_EXTRACTION"
                )

            if (
                artifact.parent is None
                or id(
                    artifact.parent
                )
                not in canonical_boot_dtb_component_ids
            ):
                raise ValueError(
                    "boot DTB FDT member must retain an exact "
                    "canonical boot-image dtb component parent"
                )

        if not isinstance(
            self.vendor_ramdisk_tables,
            tuple,
        ):
            raise TypeError(
                "vendor_ramdisk_tables must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedVendorRamdiskTable,
            )
            for parsed
            in self.vendor_ramdisk_tables
        ):
            raise TypeError(
                "vendor_ramdisk_tables must contain only "
                "ParsedVendorRamdiskTable entries"
            )

        expected_vendor_table_artifacts = tuple(
            artifact
            for image
            in self.boot_images
            for artifact
            in image.component_artifacts
            if (
                artifact.semantic_name
                == "vendor_ramdisk_table"
            )
        )

        actual_vendor_table_artifacts = tuple(
            parsed.artifact
            for parsed
            in self.vendor_ramdisk_tables
        )

        if tuple(
            id(
                artifact
            )
            for artifact
            in actual_vendor_table_artifacts
        ) != tuple(
            id(
                artifact
            )
            for artifact
            in expected_vendor_table_artifacts
        ):
            raise ValueError(
                "vendor_ramdisk_tables must conserve every "
                "canonical vendor_ramdisk_table component in "
                "exact boot-image order and artifact identity"
            )

        if len(
            {
                id(
                    artifact
                )
                for artifact
                in actual_vendor_table_artifacts
            }
        ) != len(
            actual_vendor_table_artifacts
        ):
            raise ValueError(
                "vendor_ramdisk_tables contains duplicate "
                "canonical component identity"
            )

        if not isinstance(
            self.dtbo,
            tuple,
        ):
            raise TypeError(
                "dtbo must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                AndroidParsedDtboEntry,
            )
            for parsed in self.dtbo
        ):
            raise TypeError(
                "dtbo must contain only AndroidParsedDtboEntry entries"
            )

        sflb_artifact_ids = tuple(
            id(parsed.artifact)
            for parsed
            in self.sflb
        )

        if len(
            sflb_artifact_ids
        ) != len(
            set(
                sflb_artifact_ids
            )
        ):
            raise ValueError(
                "sflb must preserve unique canonical "
                "Extraction artifact identities"
            )

        bmp_artifact_ids = tuple(
            id(parsed.artifact)
            for parsed
            in self.bmp
        )

        if len(
            bmp_artifact_ids
        ) != len(
            set(
                bmp_artifact_ids
            )
        ):
            raise ValueError(
                "bmp must preserve unique canonical "
                "Extraction artifact identities"
            )

        dtbo_artifact_ids = tuple(
            id(parsed.artifact)
            for parsed
            in self.dtbo
        )

        if len(
            dtbo_artifact_ids
        ) != len(
            set(
                dtbo_artifact_ids
            )
        ):
            raise ValueError(
                "dtbo must preserve unique canonical "
                "Extraction artifact identities"
            )

        if not isinstance(
            self.vbmeta,
            tuple,
        ):
            raise TypeError(
                "vbmeta must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAvbVbmeta,
            )
            for parsed in self.vbmeta
        ):
            raise TypeError(
                "vbmeta must contain only ParsedAvbVbmeta entries"
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
                ParsedAvbRegion,
            )
            for region in self.avb_regions
        ):
            raise TypeError(
                "avb_regions must contain only ParsedAvbRegion entries"
            )

        region_artifact_ids: set[int] = set()

        for region in self.avb_regions:
            identity = id(
                region.artifact
            )

            if identity in region_artifact_ids:
                raise ValueError(
                    "avb_regions contains duplicate canonical "
                    "Extraction artifact identity"
                )

            region_artifact_ids.add(
                identity
            )

        parsed_region_vbmeta = {
            id(region.vbmeta): region.vbmeta
            for region in self.avb_regions
            if region.vbmeta is not None
        }

        embedded_vbmeta = {
            id(parsed): parsed
            for parsed in self.vbmeta
            if (
                parsed.artifact.operation
                is ExtractionOperation.AVB_REGION_EXTRACTION
            )
        }

        if (
            set(parsed_region_vbmeta)
            != set(embedded_vbmeta)
        ):
            raise ValueError(
                "AVB region ledger must preserve every embedded "
                "Parsing VBMeta result exactly once"
            )

        if not isinstance(
            self.boot_signatures,
            tuple,
        ):
            raise TypeError(
                "boot_signatures must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedBootSignature,
            )
            for parsed
            in self.boot_signatures
        ):
            raise TypeError(
                "boot_signatures must contain only "
                "ParsedBootSignature entries"
            )

        boot_signature_artifact_ids = tuple(
            id(
                parsed.artifact
            )
            for parsed
            in self.boot_signatures
        )

        if len(
            boot_signature_artifact_ids
        ) != len(
            set(
                boot_signature_artifact_ids
            )
        ):
            raise ValueError(
                "boot_signatures contains duplicate canonical "
                "Extraction artifact identity"
            )

        expected_boot_signature_artifacts = tuple(
            artifact
            for image
            in self.boot_images
            for artifact
            in image.component_artifacts
            if artifact.semantic_name == "boot_signature"
        )

        expected_boot_signature_ids = tuple(
            id(
                artifact
            )
            for artifact
            in expected_boot_signature_artifacts
        )

        if (
            boot_signature_artifact_ids
            != expected_boot_signature_ids
        ):
            raise ValueError(
                "boot_signatures must conserve every canonical "
                "boot_signature component in exact boot-image order "
                "and artifact identity"
            )

        boot_image_artifact_ids = {
            id(
                image.partition.artifact
            )
            for image
            in self.boot_images
        }

        for parsed in self.boot_signatures:
            if (
                id(
                    parsed.boot_image_artifact
                )
                not in boot_image_artifact_ids
            ):
                raise ValueError(
                    "boot-signature boot-image parent is not present "
                    "in canonical Parsing boot_images"
                )

        if not isinstance(
            self.bootloader,
            tuple,
        ):
            raise TypeError(
                "bootloader must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedBootloaderChild,
            )
            for parsed in self.bootloader
        ):
            raise TypeError(
                "bootloader must contain only "
                "ParsedBootloaderChild entries"
            )

        if not isinstance(
            self.bootloader_children,
            tuple,
        ):
            raise TypeError(
                "bootloader_children must be a tuple"
            )

        if not all(
            isinstance(
                disposition,
                ParsedBootloaderChildDisposition,
            )
            for disposition in self.bootloader_children
        ):
            raise TypeError(
                "bootloader_children must contain only "
                "ParsedBootloaderChildDisposition entries"
            )

        bootloader_artifact_ids: set[int] = set()

        for disposition in self.bootloader_children:
            identity = id(
                disposition.artifact
            )

            if identity in bootloader_artifact_ids:
                raise ValueError(
                    "bootloader_children contains duplicate "
                    "canonical Extraction artifact identity"
                )

            bootloader_artifact_ids.add(
                identity
            )

        ledger_parsed = {
            id(disposition.parsed): disposition.parsed
            for disposition in self.bootloader_children
            if disposition.parsed is not None
        }

        canonical_parsed = {
            id(parsed): parsed
            for parsed in self.bootloader
        }

        if (
            set(ledger_parsed)
            != set(canonical_parsed)
        ):
            raise ValueError(
                "bootloader child disposition ledger must preserve "
                "every parsed bootloader child exactly once"
            )

        if not isinstance(
            self.ramdisks,
            tuple,
        ):
            raise TypeError(
                "ramdisks must be a tuple"
            )

        if not all(
            isinstance(
                ramdisk,
                ParsedAndroidRamdisk,
            )
            for ramdisk
            in self.ramdisks
        ):
            raise TypeError(
                "ramdisks must contain only "
                "ParsedAndroidRamdisk instances"
            )

        ramdisk_root_ids = tuple(
            id(
                ramdisk.ramdisk_root
            )
            for ramdisk
            in self.ramdisks
        )

        if len(
            ramdisk_root_ids
        ) != len(
            set(
                ramdisk_root_ids
            )
        ):
            raise ValueError(
                "Parsing ramdisk population must not contain "
                "duplicate canonical CPIO root identities"
            )

        if not isinstance(
            self.kernels,
            tuple,
        ):
            raise TypeError(
                "kernels must be a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedKernelImage,
            )
            for parsed in self.kernels
        ):
            raise TypeError(
                "kernels must contain only "
                "ParsedKernelImage entries"
            )

        kernel_artifact_ids = tuple(
            id(parsed.artifact)
            for parsed in self.kernels
        )

        if len(
            kernel_artifact_ids
        ) != len(
            set(
                kernel_artifact_ids
            )
        ):
            raise ValueError(
                "kernels must preserve unique canonical "
                "Extraction artifact identities"
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
                parsed,
                ParsedBootImage,
            )
            for parsed in self.boot_images
        ):
            raise TypeError(
                "boot_images must contain only "
                "ParsedBootImage entries"
            )

        boot_partition_ids = tuple(
            id(parsed.partition)
            for parsed in self.boot_images
        )

        if len(
            boot_partition_ids
        ) != len(
            set(
                boot_partition_ids
            )
        ):
            raise ValueError(
                "boot_images must preserve each canonical "
                "InventoryPartition exactly once"
            )

        boot_artifact_ids = tuple(
            id(
                parsed.partition.artifact
            )
            for parsed in self.boot_images
        )

        if len(
            boot_artifact_ids
        ) != len(
            set(
                boot_artifact_ids
            )
        ):
            raise ValueError(
                "boot_images must preserve unique canonical "
                "Extraction artifact identities"
            )
