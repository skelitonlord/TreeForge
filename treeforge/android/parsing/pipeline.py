from __future__ import annotations

from typing import Protocol

from treeforge.android.extraction import (
    AndroidExtractionResult,
    ExtractionOperation,
)

from treeforge.android.parsing.extraction_ownership import (
    validate_parsing_extraction_ownership,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.parsing.sflb import (
    AndroidParsedSflbEntry,
    AndroidSflbEntryParser,
)
from treeforge.android.parsing.boot.boot import (
    BootImageParser,
    ParsedBootImageMetadata,
)
from treeforge.android.parsing.boot.bootconfig import (
    AndroidBootconfigParser,
    ParsedAndroidBootconfig,
)
from treeforge.android.parsing.boot.vendor_boot import (
    ParsedVendorBootImageMetadata,
    VendorBootImageParser,
)
from treeforge.android.parsing.boot.vendor_ramdisk_table import (
    AndroidVendorRamdiskTableParser,
    ParsedVendorRamdiskTable,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
    ParsedBootImage,
    ParsedBootSignature,
    ParsedBootloaderChild,
    ParsedBootloaderChildDisposition,
    ParsedAvbRegion,
    ParsedAvbVbmeta,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
    PartitionInventory,
)
from treeforge.android.parsing.filesystem.filesystem_sources import (
    AndroidFilesystemSourceBuilder,
)
from treeforge.android.parsing.elf import (
    AndroidElfPopulationParser,
    AndroidElfParsingResult,
)
from treeforge.android.parsing.art_runtime import (
    AndroidArtRuntimeParser,
    AndroidArtRuntimeParsingResult,
)
from treeforge.android.parsing.dex import (
    AndroidStandaloneDexParser,
    AndroidStandaloneDexParsingResult,
)
from treeforge.android.parsing.classpath import (
    AndroidClasspathParsingResult,
    AndroidClasspathProtobufParser,
)
from treeforge.android.parsing.aconfig import (
    AndroidAconfigParsingResult,
    AndroidAconfigProtobufParser,
)
from treeforge.android.parsing.input import (
    AndroidInputConfigurationParser,
    AndroidInputParsingResult,
)
from treeforge.android.parsing.font import (
    AndroidFontParser,
    AndroidFontParsingResult,
)
from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveParser,
    AndroidJavaArchiveParsingResult,
)
from treeforge.android.parsing.shell_script import (
    AndroidShellScriptParser,
    AndroidShellScriptParsingResult,
)
from treeforge.android.parsing.certificate import (
    AndroidCertificateParser,
    AndroidCertificateParsingResult,
)
from treeforge.android.parsing.apk import (
    AndroidApkManifestParser,
    AndroidApkParsingResult,
)

from treeforge.android.parsing.avf import (
    AndroidAvfVmConfigParser,
    AndroidAvfVmConfigParsingResult,
)
from treeforge.android.parsing.structured_configuration import (
    AndroidStructuredConfigurationParser,
    AndroidStructuredConfigurationParsingResult,
)
from treeforge.android.parsing.kernel_module import (
    AndroidKernelModuleConfigurationParser,
    AndroidKernelModuleParser,
    AndroidKernelModuleParsingResult,
    ParsedAndroidKernelModuleConfiguration,
)
from treeforge.android.parsing.linker import (
    AndroidLdConfigParser,
    AndroidLinkerConfigProtobufParser,
    AndroidNativeLibraryConfigurationParser,
    ParsedAndroidLinkerConfiguration,
    ParsedAndroidLinkerProtobufConfiguration,
    ParsedAndroidNativeLibraryConfiguration,
)
from treeforge.android.parsing.ramdisk import (
    AndroidRamdiskParser,
)
from treeforge.android.parsing.kernel import (
    AndroidKernelImageParser,
    ParsedKernelImage,
)
from treeforge.android.parsing.apex import (
    AndroidApexManifestParser,
    AndroidParsedApex,
    ParsedApexContainer,
)
from treeforge.android.parsing.bmp import (
    AndroidBmpParser,
    AndroidParsedBmp,
)
from treeforge.android.parsing.avb import (
    AndroidParsedAvbFooter,
    AndroidParsedVbmeta,
    AndroidVbmetaParser,
)
from treeforge.android.parsing.bootloader import (
    AndroidBootFirmwarePayloadParser,
    AndroidUfpkDescriptorParser,
    AndroidBootloaderChildParser,
    AndroidParsedBootFirmwarePayload,
    AndroidParsedFbpt,
    AndroidParsedUfpk,
    AndroidParsedUfpkDescriptor,
    AndroidParsedUfsDescriptor,
)
from treeforge.android.parsing.dtb import (
    AndroidDtboOverlayParser,
    AndroidFdtParser,
    AndroidParsedDtboEntry,
    ParsedDtboOverlayMetadata,
    ParsedFdt,
)
from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
)
from treeforge.android.parsing.filesystem.pipeline import (
    AndroidFilesystemParsingPipeline,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceInventoryBuilder,
    AndroidModelSourceKind,
    AndroidParserFilesystemSource,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


class AndroidFilesystemSourceBuilderLike(
    Protocol,
):
    """
    Contract for preparing parser-facing filesystem sources.
    """

    def build(
        self,
        extraction: AndroidExtractionResult,
        inventory: PartitionInventory,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> tuple[
        AndroidParserFilesystemSource,
        ...,
    ]:
        ...


class AndroidModelSourceInventoryBuilderLike(
    Protocol,
):
    """
    Contract for discovering parser source files from prepared filesystems.
    """

    def build(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> AndroidModelSourceInventory:
        ...


class AndroidFilesystemParsingPipelineLike(
    Protocol,
):
    """
    Contract for parsing filesystem-backed Android sources.
    """

    def extract_inventory(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidFilesystemParsingResult:
        ...


class AndroidElfPopulationParserLike(
    Protocol,
):
    def parse(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
        filesystem_inventory: FilesystemMetadataInventory,
        extraction: AndroidExtractionResult,
    ) -> AndroidElfParsingResult:
        ...


class AndroidArtRuntimeParserLike(
    Protocol,
):
    def parse(
        self,
        *,
        elf: AndroidElfParsingResult,
        source_inventory: AndroidModelSourceInventory,
    ) -> AndroidArtRuntimeParsingResult:
        ...


class AndroidStandaloneDexParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidStandaloneDexParsingResult:
        ...


class AndroidClasspathProtobufParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidClasspathParsingResult:
        ...


class AndroidAconfigProtobufParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidAconfigParsingResult:
        ...


class AndroidInputConfigurationParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidInputParsingResult:
        ...


class AndroidFontParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidFontParsingResult:
        ...


class AndroidJavaArchiveParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidJavaArchiveParsingResult:
        ...


class AndroidShellScriptParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidShellScriptParsingResult:
        ...


class AndroidStructuredConfigurationParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidStructuredConfigurationParsingResult:
        ...


class AndroidCertificateParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidCertificateParsingResult:
        ...


class AndroidApkManifestParserLike(
    Protocol,
):
    def parse(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> AndroidApkParsingResult:
        ...


class AndroidAvfVmConfigParserLike(
    Protocol,
):
    def parse(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> AndroidAvfVmConfigParsingResult:
        ...


class AndroidKernelModuleParserLike(
    Protocol,
):
    def parse(
        self,
        elf: AndroidElfParsingResult,
    ) -> AndroidKernelModuleParsingResult:
        ...


class AndroidKernelModuleConfigurationParserLike(
    Protocol,
):
    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> tuple[
        ParsedAndroidKernelModuleConfiguration,
        ...,
    ]:
        ...


class AndroidLdConfigParserLike(
    Protocol,
):
    def parse_sources(
        self,
        sources: tuple[
            AndroidModelSource,
            ...,
        ],
    ) -> tuple[
        ParsedAndroidLinkerConfiguration,
        ...,
    ]:
        ...


class AndroidLinkerConfigProtobufParserLike(
    Protocol,
):
    def parse_sources(
        self,
        sources: tuple[
            AndroidModelSource,
            ...,
        ],
    ) -> tuple[
        ParsedAndroidLinkerProtobufConfiguration,
        ...,
    ]:
        ...


class AndroidNativeLibraryConfigurationParserLike(
    Protocol,
):
    def parse_sources(
        self,
        sources: tuple[
            AndroidModelSource,
            ...,
        ],
    ) -> tuple[
        ParsedAndroidNativeLibraryConfiguration,
        ...,
    ]:
        ...


class AndroidKernelImageParserLike(
    Protocol,
):
    def parse(
        self,
        artifact,
    ) -> ParsedKernelImage:
        ...


class AndroidApexManifestParserLike(
    Protocol,
):
    def parse(
        self,
        artifact,
    ) -> AndroidParsedApex:
        ...


class AndroidBmpParserLike(
    Protocol,
):
    def parse(
        self,
        artifact,
    ) -> AndroidParsedBmp:
        ...


class AndroidFdtParserLike(
    Protocol,
):
    def parse(
        self,
        artifact,
    ) -> ParsedFdt:
        ...


class AndroidDtboOverlayParserLike(
    Protocol,
):
    def parse(
        self,
        fdt: ParsedFdt,
    ) -> ParsedDtboOverlayMetadata:
        ...


class BootImageParserLike(
    Protocol,
):
    def parse(
        self,
        image_path,
    ) -> ParsedBootImageMetadata:
        ...


class VendorBootImageParserLike(
    Protocol,
):
    def parse(
        self,
        image_path,
    ) -> ParsedVendorBootImageMetadata:
        ...


class AndroidBootconfigParserLike(
    Protocol,
):
    def parse(
        self,
        source_path,
    ) -> ParsedAndroidBootconfig:
        ...


class AndroidParsingPipelineError(
    RuntimeError,
):
    """
    Raised when canonical upstream state cannot complete Android Parsing.
    """


class AndroidParsingPipeline:
    """
    Canonical Android Parsing stage.

    Required upstream state:

        AndroidExtractionResult
            +
        PartitionInventory

    Parsing owns both parser source families:

        filesystem-backed sources
            properties
            fstab
            init RC
            ueventd
            VINTF

        partition-image sources
            boot
            init_boot
            vendor_boot
            vbmeta
            dtbo

        recursively materialized structured sources
            FBPK bootloader children
            embedded ELF artifacts

    This pipeline performs no Discovery, Extraction, Reconstruction,
    cross-source interpretation, or downstream source materialization.

    Parsing answers only:

        "What does each canonical source say?"

    The later AndroidDeviceUniverse stage will interpret what all parsed
    sources collectively say about the device.
    """

    PREFERRED_SLOT_SUFFIX = "_a"

    def __init__(
        self,
        *,
        filesystem_source_builder: (
            AndroidFilesystemSourceBuilderLike
            | None
        ) = None,
        source_inventory_builder: (
            AndroidModelSourceInventoryBuilderLike
            | None
        ) = None,
        filesystem_parser: (
            AndroidFilesystemParsingPipelineLike
            | None
        ) = None,
        elf_parser: (
            AndroidElfPopulationParserLike
            | None
        ) = None,
        art_runtime_parser: (
            AndroidArtRuntimeParserLike
            | None
        ) = None,
        dex_parser: (
            AndroidStandaloneDexParserLike
            | None
        ) = None,
        classpath_parser: (
            AndroidClasspathProtobufParserLike
            | None
        ) = None,
        aconfig_parser: (
            AndroidAconfigProtobufParserLike
            | None
        ) = None,
        input_parser: (
            AndroidInputConfigurationParserLike
            | None
        ) = None,
        font_parser: (
            AndroidFontParserLike
            | None
        ) = None,
        java_archive_parser: (
            AndroidJavaArchiveParserLike
            | None
        ) = None,
        shell_script_parser: (
            AndroidShellScriptParserLike
            | None
        ) = None,
        structured_configuration_parser: (
            AndroidStructuredConfigurationParserLike
            | None
        ) = None,
        certificate_parser: (
            AndroidCertificateParserLike
            | None
        ) = None,
        apk_parser: (
            AndroidApkManifestParserLike
            | None
        ) = None,
        avf_vm_config_parser: (
            AndroidAvfVmConfigParserLike
            | None
        ) = None,
        kernel_module_parser: (
            AndroidKernelModuleParserLike
            | None
        ) = None,
        kernel_module_configuration_parser: (
            AndroidKernelModuleConfigurationParserLike
            | None
        ) = None,
        linker_configuration_parser: (
            AndroidLdConfigParserLike
            | None
        ) = None,
        linker_protobuf_configuration_parser: (
            AndroidLinkerConfigProtobufParserLike
            | None
        ) = None,
        native_library_configuration_parser: (
            AndroidNativeLibraryConfigurationParserLike
            | None
        ) = None,
        kernel_parser: (
            AndroidKernelImageParserLike
            | None
        ) = None,
        apex_parser: (
            AndroidApexManifestParserLike
            | None
        ) = None,
        bmp_parser: (
            AndroidBmpParserLike
            | None
        ) = None,
        dtb_parser: (
            AndroidFdtParserLike
            | None
        ) = None,
        dtbo_overlay_parser: (
            AndroidDtboOverlayParserLike
            | None
        ) = None,
        boot_parser: (
            BootImageParserLike
            | None
        ) = None,
        vendor_boot_parser: (
            VendorBootImageParserLike
            | None
        ) = None,
        bootconfig_parser: (
            AndroidBootconfigParserLike
            | None
        ) = None,
        vbmeta_parser: AndroidVbmetaParser | None = None,
        bootloader_child_parser: (
            AndroidBootloaderChildParser
            | None
        ) = None,
        boot_firmware_payload_parser: (
            AndroidBootFirmwarePayloadParser
            | None
        ) = None,
        ufpk_descriptor_parser: (
            AndroidUfpkDescriptorParser
            | None
        ) = None,
        sflb_parser: (
            AndroidSflbEntryParser
            | None
        ) = None,
        ramdisk_parser: AndroidRamdiskParser | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.filesystem_source_builder = (
            filesystem_source_builder
            if filesystem_source_builder is not None
            else AndroidFilesystemSourceBuilder()
        )

        self.source_inventory_builder = (
            source_inventory_builder
            if source_inventory_builder is not None
            else AndroidModelSourceInventoryBuilder()
        )

        self.filesystem_parser = (
            filesystem_parser
            if filesystem_parser is not None
            else AndroidFilesystemParsingPipeline(
                progress_callback=progress_callback,
            )
        )

        self.elf_parser = (
            elf_parser
            if elf_parser is not None
            else AndroidElfPopulationParser(
                progress_callback=progress_callback,
            )
        )

        self.art_runtime_parser = (
            art_runtime_parser
            if art_runtime_parser is not None
            else AndroidArtRuntimeParser()
        )

        self.dex_parser = (
            dex_parser
            if dex_parser is not None
            else AndroidStandaloneDexParser()
        )

        self.classpath_parser = (
            classpath_parser
            if classpath_parser is not None
            else AndroidClasspathProtobufParser()
        )

        self.aconfig_parser = (
            aconfig_parser
            if aconfig_parser is not None
            else AndroidAconfigProtobufParser()
        )

        self.input_parser = (
            input_parser
            if input_parser is not None
            else AndroidInputConfigurationParser()
        )

        self.font_parser = (
            font_parser
            if font_parser is not None
            else AndroidFontParser()
        )

        self.java_archive_parser = (
            java_archive_parser
            if java_archive_parser is not None
            else AndroidJavaArchiveParser()
        )

        self.shell_script_parser = (
            shell_script_parser
            if shell_script_parser is not None
            else AndroidShellScriptParser()
        )

        self.structured_configuration_parser = (
            structured_configuration_parser
            if structured_configuration_parser
            is not None
            else AndroidStructuredConfigurationParser()
        )

        self.certificate_parser = (
            certificate_parser
            if certificate_parser is not None
            else AndroidCertificateParser()
        )

        self.apk_parser = (
            apk_parser
            if apk_parser is not None
            else AndroidApkManifestParser()
        )

        self.avf_vm_config_parser = (
            avf_vm_config_parser
            if avf_vm_config_parser is not None
            else AndroidAvfVmConfigParser()
        )

        self.kernel_module_parser = (
            kernel_module_parser
            if kernel_module_parser is not None
            else AndroidKernelModuleParser()
        )

        self.kernel_module_configuration_parser = (
            kernel_module_configuration_parser
            if kernel_module_configuration_parser is not None
            else AndroidKernelModuleConfigurationParser()
        )

        self.linker_configuration_parser = (
            linker_configuration_parser
            if linker_configuration_parser is not None
            else AndroidLdConfigParser()
        )

        self.linker_protobuf_configuration_parser = (
            linker_protobuf_configuration_parser
            if linker_protobuf_configuration_parser is not None
            else AndroidLinkerConfigProtobufParser()
        )

        self.native_library_configuration_parser = (
            native_library_configuration_parser
            if native_library_configuration_parser is not None
            else AndroidNativeLibraryConfigurationParser()
        )

        self.apex_parser = (
            apex_parser
            if apex_parser is not None
            else AndroidApexManifestParser()
        )

        self.bmp_parser = (
            bmp_parser
            if bmp_parser is not None
            else AndroidBmpParser()
        )

        self.dtb_parser = (
            dtb_parser
            if dtb_parser is not None
            else AndroidFdtParser()
        )

        self.dtbo_overlay_parser = (
            dtbo_overlay_parser
            if dtbo_overlay_parser is not None
            else AndroidDtboOverlayParser()
        )

        self.kernel_parser = (
            kernel_parser
            if kernel_parser is not None
            else AndroidKernelImageParser()
        )

        self.boot_parser = (
            boot_parser
            if boot_parser is not None
            else BootImageParser()
        )

        self.vendor_boot_parser = (
            vendor_boot_parser
            if vendor_boot_parser is not None
            else VendorBootImageParser()
        )

        self.bootconfig_parser = (
            bootconfig_parser
            if bootconfig_parser is not None
            else AndroidBootconfigParser()
        )

        self.vbmeta_parser = (
            vbmeta_parser
            if vbmeta_parser is not None
            else AndroidVbmetaParser()
        )

        self.bootloader_child_parser = (
            bootloader_child_parser
            if bootloader_child_parser is not None
            else AndroidBootloaderChildParser()
        )


        self.boot_firmware_payload_parser = (
            boot_firmware_payload_parser
            if boot_firmware_payload_parser
            is not None
            else AndroidBootFirmwarePayloadParser()
        )

        self.ufpk_descriptor_parser = (
            ufpk_descriptor_parser
            if ufpk_descriptor_parser is not None
            else AndroidUfpkDescriptorParser()
        )

        self.sflb_parser = (
            sflb_parser
            if sflb_parser is not None
            else AndroidSflbEntryParser()
        )

        self.ramdisk_parser = (
            ramdisk_parser
            if ramdisk_parser is not None
            else AndroidRamdiskParser()
        )

        self.progress_callback = progress_callback

    def execute(
        self,
        context: Context,
    ) -> None:
        """
        Execute Parsing as one first-class pipeline stage.
        """

        self.run(
            context
        )

    def run(
        self,
        context: Context,
    ) -> AndroidParsingResult:
        """
        Parse all supported canonical Android sources.

        The exact immutable result is published atomically to Context and
        returned to the caller.
        """

        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

        validate_parsing_extraction_ownership()

        parsing_knowledge = (
            context.parsing_knowledge
        )

        # Reserved typed module input for intrinsic Parsing
        # knowledge supplied by version/device/platform modules.
        _ = parsing_knowledge

        extraction = (
            context.android_extraction
        )

        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise AndroidParsingPipelineError(
                "canonical Android Extraction state is required "
                "before Parsing"
            )

        inventory = (
            context.partition_inventory
        )

        if not isinstance(
            inventory,
            PartitionInventory,
        ):
            raise AndroidParsingPipelineError(
                "canonical PartitionInventory is required "
                "before Parsing"
            )

        filesystem_inventory = (
            context.filesystem_inventory
        )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise AndroidParsingPipelineError(
                "canonical FilesystemMetadataInventory is required "
                "before Parsing"
            )

        self._report_progress(
            current=0,
            total=28,
            detail="filesystem sources",
            state=ProgressState.RUNNING,
        )

        filesystems = (
            self.filesystem_source_builder.build(
                extraction,
                inventory,
                filesystem_inventory,
            )
        )

        if not isinstance(
            filesystems,
            tuple,
        ):
            raise AndroidParsingPipelineError(
                "filesystem source builder must return a tuple"
            )

        if not all(
            isinstance(
                filesystem,
                AndroidParserFilesystemSource,
            )
            for filesystem in filesystems
        ):
            raise AndroidParsingPipelineError(
                "filesystem source builder returned invalid "
                "parser-facing filesystem sources"
            )

        self._report_progress(
            current=1,
            total=28,
            detail="filesystem sources",
            state=ProgressState.COMPLETE,
            subject="Canonical parser filesystem roots",
            operation=(
                "projected Filesystem Metadata roots into Parsing"
            ),
            item=(
                f"{len(filesystems)} canonical filesystem sources"
            ),
            processed=len(filesystems),
            produced=len(filesystems),
        )

        self._report_progress(
            current=1,
            total=28,
            detail="source inventory",
            state=ProgressState.RUNNING,
        )

        source_inventory = (
            self.source_inventory_builder.build(
                filesystems
            )
        )

        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise AndroidParsingPipelineError(
                "source inventory builder must return an "
                "AndroidModelSourceInventory"
            )

        source_kind_count = len(
            {
                source.kind
                for source
                in source_inventory.sources
            }
        )

        self._report_progress(
            current=2,
            total=28,
            detail="source inventory",
            state=ProgressState.COMPLETE,
            subject="Canonical Android model sources",
            operation=(
                "classified parser-owned source inventory"
            ),
            item=(
                f"{source_inventory.source_count} sources / "
                f"{source_kind_count} populated source kinds"
            ),
            processed=source_inventory.source_count,
            produced=source_inventory.source_count,
        )

        self._report_progress(
            current=2,
            total=28,
            detail="filesystem parsers",
            state=ProgressState.RUNNING,
        )

        filesystem_result = (
            self.filesystem_parser.extract_inventory(
                source_inventory
            )
        )

        if not isinstance(
            filesystem_result,
            AndroidFilesystemParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "filesystem parser must return an "
                "AndroidFilesystemParsingResult"
            )

        self._report_progress(
            current=3,
            total=28,
            detail="filesystem parsers",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=3,
            total=28,
            detail="linker configuration",
            state=ProgressState.RUNNING,
        )

        linker_configuration_sources = (
            source_inventory.sources_for(
                AndroidModelSourceKind
                .LINKER_CONFIGURATION
            )
        )

        linker_configurations = (
            self.linker_configuration_parser
            .parse_sources(
                linker_configuration_sources
            )
        )

        if not isinstance(
            linker_configurations,
            tuple,
        ):
            raise AndroidParsingPipelineError(
                "linker configuration parser must "
                "return a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidLinkerConfiguration,
            )
            for parsed
            in linker_configurations
        ):
            raise AndroidParsingPipelineError(
                "linker configuration parser returned "
                "invalid Parsing results"
            )

        linker_protobuf_configurations = (
            self.linker_protobuf_configuration_parser
            .parse_sources(
                linker_configuration_sources
            )
        )

        if not isinstance(
            linker_protobuf_configurations,
            tuple,
        ):
            raise AndroidParsingPipelineError(
                "linker protobuf configuration parser must "
                "return a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidLinkerProtobufConfiguration,
            )
            for parsed
            in linker_protobuf_configurations
        ):
            raise AndroidParsingPipelineError(
                "linker protobuf configuration parser returned "
                "invalid Parsing results"
            )

        self._report_progress(
            current=4,
            total=28,
            detail="linker configuration",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=4,
            total=28,
            detail="native library configuration",
            state=ProgressState.RUNNING,
        )

        native_library_configuration_sources = (
            source_inventory.sources_for(
                AndroidModelSourceKind
                .NATIVE_LIBRARY_CONFIGURATION
            )
        )

        native_library_configurations = (
            self.native_library_configuration_parser
            .parse_sources(
                native_library_configuration_sources
            )
        )

        if not isinstance(
            native_library_configurations,
            tuple,
        ):
            raise AndroidParsingPipelineError(
                "native-library configuration parser must "
                "return a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidNativeLibraryConfiguration,
            )
            for parsed
            in native_library_configurations
        ):
            raise AndroidParsingPipelineError(
                "native-library configuration parser returned "
                "invalid Parsing results"
            )

        self._report_progress(
            current=5,
            total=28,
            detail="native library configuration",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=5,
            total=28,
            detail="ELF",
            state=ProgressState.RUNNING,
        )

        elf = self.elf_parser.parse(
            filesystems,
            filesystem_inventory,
            extraction,
        )

        if not isinstance(
            elf,
            AndroidElfParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "ELF parser must return an "
                "AndroidElfParsingResult"
            )

        self._report_progress(
            current=6,
            total=28,
            detail="ELF",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=6,
            total=28,
            detail="ART runtime",
            state=ProgressState.RUNNING,
        )

        art_runtime = (
            self.art_runtime_parser.parse(
                elf=elf,
                source_inventory=source_inventory,
            )
        )

        if not isinstance(
            art_runtime,
            AndroidArtRuntimeParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "ART-runtime parser must return an "
                "AndroidArtRuntimeParsingResult"
            )

        self._report_progress(
            current=7,
            total=28,
            detail="ART runtime",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=7,
            total=28,
            detail="standalone DEX",
            state=ProgressState.RUNNING,
            subject="Standalone DEX sources",
            operation=(
                "parsing canonical standalone DEX evidence"
            ),
            item="standalone filesystem DEX candidates",
        )

        dex = self.dex_parser.parse(
            source_inventory
        )

        if not isinstance(
            dex,
            AndroidStandaloneDexParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "standalone DEX parser must return an "
                "AndroidStandaloneDexParsingResult"
            )

        self._report_progress(
            current=8,
            total=28,
            detail="standalone DEX",
            state=ProgressState.COMPLETE,
            subject="Standalone DEX sources",
            operation=(
                "parsed canonical standalone DEX evidence"
            ),
            item="standalone DEX population complete",
        )

        self._report_progress(
            current=8,
            total=28,
            detail="classpath configuration",
            state=ProgressState.RUNNING,
        )

        classpath = self.classpath_parser.parse(
            source_inventory
        )

        self._report_progress(
            current=9,
            total=28,
            detail="classpath configuration",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=9,
            total=28,
            detail="aconfig configuration",
            state=ProgressState.RUNNING,
        )

        aconfig = self.aconfig_parser.parse(
            source_inventory
        )

        if not isinstance(
            aconfig,
            AndroidAconfigParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "aconfig parser must return an "
                "AndroidAconfigParsingResult"
            )

        self._report_progress(
            current=10,
            total=28,
            detail="aconfig configuration",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=10,
            total=28,
            detail="APK package identity",
            state=ProgressState.RUNNING,
        )

        apk = self.apk_parser.parse(
            filesystems
        )

        if not isinstance(
            apk,
            AndroidApkParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "APK parser must return an "
                "AndroidApkParsingResult"
            )

        self._report_progress(
            current=11,
            total=28,
            detail="APK package identity",
            state=ProgressState.COMPLETE,
            subject="Installed APK candidates",
            operation=(
                "classified APK candidates and parsed package identity"
            ),
            item=(
                f"{apk.package_count} packages / "
                f"{len(apk.candidates)} candidate dispositions"
            ),
            processed=len(apk.candidates),
            produced=apk.package_count,
        )

        self._report_progress(
            current=11,
            total=28,
            detail="AVF VM configuration",
            state=ProgressState.RUNNING,
        )

        avf_vm_config = (
            self.avf_vm_config_parser.parse(
                filesystems
            )
        )

        if not isinstance(
            avf_vm_config,
            AndroidAvfVmConfigParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "AVF VM configuration parser must return "
                "an AndroidAvfVmConfigParsingResult"
            )

        self._report_progress(
            current=12,
            total=28,
            detail="AVF VM configuration",
            state=ProgressState.COMPLETE,
            subject="AVF VM configuration candidates",
            operation=(
                "classified APK-member AVF VM configuration candidates"
            ),
            item=(
                f"{avf_vm_config.configuration_count} parsed / "
                f"{len(avf_vm_config.candidates)} candidates"
            ),
            processed=len(
                avf_vm_config.candidates
            ),
            produced=(
                avf_vm_config.configuration_count
            ),
        )

        self._report_progress(
            current=12,
            total=28,
            detail="kernel modules",
            state=ProgressState.RUNNING,
        )

        kernel_modules = (
            self.kernel_module_parser.parse(
                elf
            )
        )

        if not isinstance(
            kernel_modules,
            AndroidKernelModuleParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "kernel-module parser must return an "
                "AndroidKernelModuleParsingResult"
            )

        kernel_module_configurations = (
            self.kernel_module_configuration_parser
            .parse(
                source_inventory
            )
        )

        if not isinstance(
            kernel_module_configurations,
            tuple,
        ):
            raise AndroidParsingPipelineError(
                "kernel-module configuration parser must "
                "return a tuple"
            )

        if not all(
            isinstance(
                parsed,
                ParsedAndroidKernelModuleConfiguration,
            )
            for parsed
            in kernel_module_configurations
        ):
            raise AndroidParsingPipelineError(
                "kernel-module configuration parser returned "
                "invalid Parsing results"
            )

        self._report_progress(
            current=13,
            total=28,
            detail="kernel modules",
            state=ProgressState.COMPLETE,
            subject="Kernel module evidence",
            operation=(
                "parsed ELF kernel modules and modules.* configuration"
            ),
            item=(
                f"{kernel_modules.count} modules / "
                f"{len(kernel_module_configurations)} "
                "configuration sources"
            ),
            processed=(
                kernel_modules.count
                + len(
                    kernel_module_configurations
                )
            ),
            produced=kernel_modules.count,
        )

        self._report_progress(
            current=13,
            total=28,
            detail="kernel",
            state=ProgressState.RUNNING,
        )

        kernels = self._parse_kernels(
            extraction
        )

        self._report_progress(
            current=14,
            total=28,
            detail="kernel",
            state=ProgressState.COMPLETE,
            subject="Canonical kernel images",
            operation=(
                "parsed Extraction-owned kernel payloads"
            ),
            item=f"{len(kernels)} kernel images",
            processed=len(kernels),
            produced=len(kernels),
        )

        self._report_progress(
            current=14,
            total=28,
            detail="APEX manifests",
            state=ProgressState.RUNNING,
        )

        apex = self._parse_apex(
            extraction
        )

        apex_lineage_artifact_count = sum(
            len(
                parsed.lineage_artifacts
            )
            for parsed
            in apex
        )

        self._report_progress(
            current=15,
            total=28,
            detail="APEX manifests",
            state=ProgressState.COMPLETE,
            subject="Canonical APEX lineages",
            operation=(
                "parsed APEX manifests from Extraction-owned lineages"
            ),
            item=(
                f"{len(apex)} logical APEX containers / "
                f"{apex_lineage_artifact_count} lineage artifacts"
            ),
            processed=apex_lineage_artifact_count,
            produced=len(apex),
        )

        self._report_progress(
            current=15,
            total=28,
            detail="boot-family containers",
            state=ProgressState.RUNNING,
        )

        boot_images = self._parse_boot_images(
            extraction,
            inventory,
        )

        boot_component_count = sum(
            len(
                parsed.component_artifacts
            )
            for parsed
            in boot_images
        )

        boot_signatures = (
            self._parse_boot_signatures(
                boot_images
            )
        )

        vendor_ramdisk_tables = (
            self._parse_vendor_ramdisk_tables(
                boot_images
            )
        )

        boot_dtbs = (
            self._parse_boot_dtbs(
                extraction,
                boot_images,
            )
        )

        self._report_progress(
            current=16,
            total=28,
            detail="boot-family containers",
            state=ProgressState.COMPLETE,
            subject="Canonical boot-family images",
            operation=(
                "parsed boot-family containers and component lineage"
            ),
            item=(
                f"{len(boot_images)} boot images / "
                f"{boot_component_count} component artifacts / "
                f"{len(boot_signatures)} boot signatures / "
                f"{len(vendor_ramdisk_tables)} vendor ramdisk tables / "
                f"{len(boot_dtbs)} boot DTB FDT members"
            ),
            processed=boot_component_count,
            produced=len(boot_images),
        )

        self._report_progress(
            current=16,
            total=28,
            detail="DTBO",
            state=ProgressState.RUNNING,
        )

        dtbo = self._parse_dtbo(
            extraction
        )

        self._report_progress(
            current=17,
            total=28,
            detail="DTBO",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=17,
            total=28,
            detail="VBMeta / AVB",
            state=ProgressState.RUNNING,
        )

        (
            vbmeta,
            avb_regions,
        ) = self._parse_vbmeta(
            extraction,
            inventory,
        )

        parsed_avb_region_count = sum(
            region.disposition == "parsed"
            for region
            in avb_regions
        )

        self._report_progress(
            current=18,
            total=28,
            detail="VBMeta / AVB",
            state=ProgressState.COMPLETE,
            subject="Canonical AVB evidence",
            operation=(
                "classified AVB regions and parsed VBMeta metadata"
            ),
            item=(
                f"{len(vbmeta)} VBMeta partitions / "
                f"{len(avb_regions)} AVB regions / "
                f"{parsed_avb_region_count} parsed"
            ),
            processed=len(avb_regions),
            produced=len(vbmeta),
        )

        self._report_progress(
            current=18,
            total=28,
            detail="bootloader children",
            state=ProgressState.RUNNING,
        )

        (
            bootloader,
            bootloader_children,
        ) = (
            self._parse_bootloader_children(
                extraction
            )
        )

        parsed_bootloader_child_count = sum(
            child.disposition == "parsed"
            for child
            in bootloader_children
        )

        self._report_progress(
            current=19,
            total=28,
            detail="bootloader children",
            state=ProgressState.COMPLETE,
            subject="Bootloader child evidence",
            operation=(
                "classified extracted bootloader child artifacts"
            ),
            item=(
                f"{len(bootloader)} parsed children / "
                f"{len(bootloader_children)} dispositions / "
                f"{parsed_bootloader_child_count} parsed dispositions"
            ),
            processed=len(
                bootloader_children
            ),
            produced=len(bootloader),
        )

        self._report_progress(
            current=19,
            total=28,
            detail="SFLB entries",
            state=ProgressState.RUNNING,
        )

        sflb = self._parse_sflb(
            extraction
        )

        self._report_progress(
            current=20,
            total=28,
            detail="SFLB entries",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=20,
            total=28,
            detail="BMP",
            state=ProgressState.RUNNING,
        )

        bmp = self._parse_bmp(
            extraction
        )

        self._report_progress(
            current=21,
            total=28,
            detail="BMP",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=21,
            total=28,
            detail="Android input configuration",
            state=ProgressState.RUNNING,
        )

        input_result = self.input_parser.parse(
            source_inventory
        )

        if not isinstance(
            input_result,
            AndroidInputParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "Android input parser must return an "
                "AndroidInputParsingResult"
            )

        self._report_progress(
            current=22,
            total=28,
            detail="Android input configuration",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=22,
            total=28,
            detail="fonts",
            state=ProgressState.RUNNING,
        )

        font = self.font_parser.parse(
            source_inventory
        )

        if not isinstance(
            font,
            AndroidFontParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "font parser must return an "
                "AndroidFontParsingResult"
            )

        self._report_progress(
            current=23,
            total=28,
            detail="fonts",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=23,
            total=28,
            detail="installed Java archives",
            state=ProgressState.RUNNING,
        )

        java_archive = (
            self.java_archive_parser.parse(
                source_inventory
            )
        )

        if not isinstance(
            java_archive,
            AndroidJavaArchiveParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "Java archive parser must return an "
                "AndroidJavaArchiveParsingResult"
            )

        self._report_progress(
            current=24,
            total=28,
            detail="installed Java archives",
            state=ProgressState.COMPLETE,
        )

        shell_script = (
            self.shell_script_parser.parse(
                source_inventory
            )
        )

        if not isinstance(
            shell_script,
            AndroidShellScriptParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "shell-script parser must return an "
                "AndroidShellScriptParsingResult"
            )

        self._report_progress(
            current=24,
            total=28,
            detail="structured filesystem configuration",
            state=ProgressState.RUNNING,
        )

        structured_configuration = (
            self.structured_configuration_parser.parse(
                source_inventory
            )
        )

        if not isinstance(
            structured_configuration,
            AndroidStructuredConfigurationParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "structured configuration parser must "
                "return an "
                "AndroidStructuredConfigurationParsingResult"
            )

        structured_count = sum(
            (
                len(
                    structured_configuration
                    .avb_public_keys
                ),
                len(
                    structured_configuration
                    .cgroup_configurations
                ),
                len(
                    structured_configuration
                    .mke2fs_configurations
                ),
                len(
                    structured_configuration
                    .recovery_wipe_configurations
                ),
                len(
                    structured_configuration
                    .blueprints
                ),
                len(
                    structured_configuration
                    .sensor_hal_configurations
                ),
                len(
                    structured_configuration
                    .sensor_registry_configurations
                ),
            )
        )

        self._report_progress(
            current=25,
            total=28,
            detail="structured filesystem configuration",
            state=ProgressState.COMPLETE,
            subject="Structured filesystem evidence",
            operation=(
                "decoded intrinsic structured "
                "configuration sources"
            ),
            item=(
                f"{structured_count} parsed sources"
            ),
            processed=structured_count,
            produced=structured_count,
        )

        self._report_progress(
            current=25,
            total=28,
            detail="certificates and OTA trust archives",
            state=ProgressState.RUNNING,
        )

        certificate = (
            self.certificate_parser.parse(
                source_inventory
            )
        )

        if not isinstance(
            certificate,
            AndroidCertificateParsingResult,
        ):
            raise AndroidParsingPipelineError(
                "certificate parser must return an "
                "AndroidCertificateParsingResult"
            )

        self._report_progress(
            current=26,
            total=28,
            detail="certificates and OTA trust archives",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=26,
            total=28,
            detail="ramdisks",
            state=ProgressState.RUNNING,
            subject="Canonical ramdisk evidence",
            operation=(
                "parsing Extraction-owned CPIO ramdisk payloads"
            ),
            item="canonical CPIO extraction population",
        )

        ramdisks = self.ramdisk_parser.parse(
            extraction
        )

        if not isinstance(
            ramdisks,
            tuple,
        ):
            raise AndroidParsingPipelineError(
                "ramdisk parser must return a tuple"
            )

        if len(
            ramdisks
        ) != len(
            extraction.cpio_extractions
        ):
            raise AndroidParsingPipelineError(
                "ramdisk Parsing population does not conserve "
                "canonical CPIO extraction population"
            )

        self._report_progress(
            current=27,
            total=28,
            detail="ramdisks",
            state=ProgressState.COMPLETE,
            subject="Canonical ramdisk evidence",
            operation=(
                "parsed and conserved canonical ramdisk population"
            ),
            item=(
                f"{len(ramdisks)} ramdisks / "
                f"{len(extraction.cpio_extractions)} CPIO extractions"
            ),
            processed=len(
                extraction.cpio_extractions
            ),
            produced=len(ramdisks),
        )

        self._report_progress(
            current=27,
            total=28,
            detail="canonical Parsing result",
            state=ProgressState.RUNNING,
            subject="Canonical Parsing result",
            operation=(
                "assembling immutable Parsing object graph"
            ),
            item="AndroidParsingResult",
        )

        result = AndroidParsingResult(
            filesystem_inventory=filesystem_inventory,
            source_inventory=source_inventory,
            filesystem=filesystem_result,
            elf=elf,
            art_runtime=art_runtime,
            dex=dex,
            classpath=classpath,
            aconfig=aconfig,
            input=input_result,
            font=font,
            java_archive=java_archive,
            shell_script=shell_script,
            certificate=certificate,
            structured_configuration=(
                structured_configuration
            ),
            apk=apk,
            avf_vm_config=avf_vm_config,
            kernel_modules=kernel_modules,
            kernel_module_configurations=(
                kernel_module_configurations
            ),
            linker_configurations=(
                linker_configurations
            ),
            linker_protobuf_configurations=(
                linker_protobuf_configurations
            ),
            native_library_configurations=(
                native_library_configurations
            ),
            apex=apex,
            bmp=bmp,
            sflb=sflb,
            dtbo=dtbo,
            boot_dtbs=boot_dtbs,
            vendor_ramdisk_tables=(
                vendor_ramdisk_tables
            ),
            vbmeta=vbmeta,
            avb_regions=avb_regions,
            bootloader=bootloader,
            bootloader_children=(
                bootloader_children
            ),
            ramdisks=ramdisks,
            kernels=kernels,
            boot_images=boot_images,
            boot_signatures=boot_signatures,
        )

        context.android_parsing = (
            result
        )

        self._report_progress(
            current=28,
            total=28,
            detail="canonical Parsing result",
            state=ProgressState.COMPLETE,
            subject="Canonical Parsing result",
            operation=(
                "assembled immutable canonical Parsing object graph"
            ),
            item="AndroidParsingResult retained in pipeline context",
        )

        return result

    def _report_progress(
        self,
        *,
        current: int,
        total: int,
        detail: str,
        state: ProgressState,
        subject: str | None = None,
        operation: str | None = None,
        item: str | None = None,
        processed: int | None = None,
        produced: int | None = None,
    ) -> None:
        if self.progress_callback is None:
            return

        semantic = {
            "filesystem sources": (
                "Canonical filesystem roots",
                "preparing parser-ready filesystem sources",
                "filesystem source construction",
            ),
            "source inventory": (
                "Parser source inventory",
                "discovering intrinsic parser sources",
                "canonical source classification",
            ),
            "filesystem parsers": (
                "Filesystem model sources",
                "decoding Android filesystem sources",
                "properties / fstab / init / ueventd / VINTF / SELinux",
            ),
            "linker configuration": (
                "Linker configuration",
                "decoding ld.config.txt sources",
                "literal linker configuration declarations",
            ),
            "native library configuration": (
                "Native-library configuration",
                "decoding native-library configuration sources",
                "literal native-library declarations",
            ),
            "ELF": (
                "Canonical ELF population",
                "decoding ELF structure and dynamic metadata",
                "filesystem ELFs + Extraction-materialized embedded ELFs",
            ),
            "ART runtime": (
                "ART runtime artifacts",
                "decoding intrinsic OAT / VDEX / ART image metadata",
                "canonical ELF OAT payloads + ART runtime filesystem sources",
            ),
            "classpath configuration": (
                "Runtime classpath fragments",
                "decoding classpaths.proto configuration",
                "literal ordered JAR declarations",
            ),
            "aconfig configuration": (
                "Aconfig parsed flags",
                "decoding aconfig_flags.pb configuration",
                "literal parsed flags / tracepoints / metadata",
            ),
            "APK package identity": (
                "Installed APK package manifests",
                "decoding Android binary XML package identity",
                "package / version / overlay declarations",
            ),
            "AVF VM configuration": (
                "AVF VM payload configurations",
                "decoding APK-embedded VM payload JSON",
                "literal guest OS / task / APEX declarations",
            ),
            "kernel modules": (
                "Kernel module evidence",
                "decoding module metadata and configuration sources",
                ".ko .modinfo + modules.*",
            ),
            "kernel": (
                "Canonical kernel image",
                "decoding intrinsic kernel image evidence",
                "Linux banner / release / embedded IKCONFIG",
            ),
            "SFLB entries": (
                "Canonical SFLB entry artifacts",
                "recording literal SFLB entry structure",
                "container / record / payload offsets and flags",
            ),
            "BMP": (
                "Canonical BMP resources",
                "decoding literal BMP metadata",
                "BMP file / DIB headers",
            ),
            "VBMeta / AVB": (
                "Canonical VBMeta partition images",
                "decoding AVB header and descriptor structure",
                "vbmeta / vbmeta_system / vbmeta_vendor",
            ),
            "bootloader children": (
                "Canonical FBPK child artifacts",
                "decoding structured bootloader child formats",
                "FBPT / UFSZ / UFSP / UFPK",
            ),
            "DTBO": (
                "Canonical DTBO entry artifacts",
                "decoding intrinsic Flattened Device Tree structure",
                "FDT headers / nodes / properties / reservations",
            ),
            "boot": (
                "boot partition",
                "decoding boot image metadata",
                "boot header and command line",
            ),
            "init_boot": (
                "init_boot partition",
                "decoding init_boot image metadata",
                "init_boot header and command line",
            ),
            "vendor_boot": (
                "vendor_boot partition",
                "decoding vendor_boot image metadata",
                "vendor_boot header / command line / bootconfig",
            ),
        }.get(
            detail,
            (
                detail,
                "parsing canonical source evidence",
                detail,
            ),
        )

        self.progress_callback(
            ProgressEvent(
                stage="Parsing",
                state=state,
                current=current,
                total=total,
                detail=detail,
                subject=(
                    subject
                    if subject is not None
                    else semantic[0]
                ),
                operation=(
                    operation
                    if operation is not None
                    else semantic[1]
                ),
                item=(
                    item
                    if item is not None
                    else semantic[2]
                ),
                processed=(
                    processed
                    if processed is not None
                    else current
                ),
                produced=produced,
            )
        )

    def _report_parser_item(
        self,
        *,
        stage: str,
        current: int,
        total: int,
        subject: str,
        operation: str,
        item: str,
        produced: int,
        state: ProgressState = ProgressState.RUNNING,
    ) -> None:
        """
        Publish truthful item-level Parsing activity.

        The owning parser family supplies its real work-unit total. This
        complements the coarse Parsing-family progress bar without inventing
        synthetic work or moving parser responsibility into CLI rendering.
        """

        if self.progress_callback is None:
            return

        self.progress_callback(
            ProgressEvent(
                stage=stage,
                state=state,
                current=current,
                total=total,
                subject=subject,
                operation=operation,
                item=item,
                processed=current,
                produced=produced,
            )
        )

    def _parse_apex(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        ParsedApexContainer,
        ...,
    ]:
        """
        Parse and conserve every canonical logical APEX lineage.

        Eligibility starts only from terminal canonical ``apex_payload``
        artifacts already established by Extraction.

        Parsing walks exact parent identity upward through
        APEX_CONTAINER_EXTRACTION artifacts until reaching the canonical
        discovered outer container. It never rediscovers APEX files by path,
        suffix, or filesystem scan.
        """

        payloads = tuple(
            sorted(
                (
                    artifact
                    for artifact
                    in extraction.artifacts
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .APEX_CONTAINER_EXTRACTION
                        and artifact.semantic_name
                        == "apex_payload"
                    )
                ),
                key=lambda artifact: (
                    artifact.path.as_posix()
                ),
            )
        )

        parsed_entries: list[
            ParsedApexContainer
        ] = []

        seen_outer_ids: set[int] = set()
        seen_payload_ids: set[int] = set()
        seen_apex_member_ids: set[int] = set()

        total_payloads = len(
            payloads
        )

        for index, payload in enumerate(
            payloads,
            start=1,
        ):
            if id(payload) in seen_payload_ids:
                raise AndroidParsingPipelineError(
                    "canonical APEX payload population contains "
                    "duplicate artifact identity"
                )

            seen_payload_ids.add(
                id(payload)
            )

            semantic_container = (
                payload.parent
            )

            if semantic_container is None:
                raise AndroidParsingPipelineError(
                    "canonical apex_payload artifact has no "
                    "semantic container parent"
                )

            lineage_reversed = [
                payload
            ]

            current = semantic_container

            while (
                current.operation
                is ExtractionOperation
                .APEX_CONTAINER_EXTRACTION
            ):
                lineage_reversed.append(
                    current
                )

                parent = current.parent

                if parent is None:
                    raise AndroidParsingPipelineError(
                        "APEX extraction lineage terminates before "
                        "its canonical outer container"
                    )

                current = parent

            outer_container = current

            if (
                outer_container.operation
                is not ExtractionOperation
                .NESTED_ARTIFACT_DISCOVERY
            ):
                raise AndroidParsingPipelineError(
                    "APEX lineage does not terminate at a canonical "
                    "NESTED_ARTIFACT_DISCOVERY outer container"
                )

            lineage_artifacts = tuple(
                reversed(
                    lineage_reversed
                )
            )

            outer_id = id(
                outer_container
            )

            if outer_id in seen_outer_ids:
                raise AndroidParsingPipelineError(
                    "multiple terminal apex_payload artifacts resolve "
                    "to one canonical outer APEX container"
                )

            seen_outer_ids.add(
                outer_id
            )

            for artifact in lineage_artifacts:
                artifact_id = id(
                    artifact
                )

                if (
                    artifact_id
                    in seen_apex_member_ids
                ):
                    raise AndroidParsingPipelineError(
                        "canonical APEX extraction artifact participates "
                        "in more than one logical APEX lineage"
                    )

                seen_apex_member_ids.add(
                    artifact_id
                )

            self._report_parser_item(
                stage="APEX Parsing",
                current=index - 1,
                total=total_payloads,
                subject=(
                    outer_container.path.name
                    or "APEX container"
                ),
                operation=(
                    "decoding APEX manifest metadata"
                ),
                item=(
                    semantic_container
                    .path
                    .as_posix()
                ),
                produced=index - 1,
            )

            metadata = (
                self.apex_parser.parse(
                    semantic_container
                )
            )

            if not isinstance(
                metadata,
                AndroidParsedApex,
            ):
                raise AndroidParsingPipelineError(
                    "APEX parser must return AndroidParsedApex"
                )

            if (
                metadata.artifact
                is not semantic_container
            ):
                raise AndroidParsingPipelineError(
                    "APEX manifest Parsing must preserve exact "
                    "semantic-container identity"
                )

            parsed = (
                ParsedApexContainer(
                    outer_container=(
                        outer_container
                    ),
                    semantic_container=(
                        semantic_container
                    ),
                    payload_artifact=(
                        payload
                    ),
                    lineage_artifacts=(
                        lineage_artifacts
                    ),
                    metadata=metadata,
                )
            )

            parsed_entries.append(
                parsed
            )

            self._report_parser_item(
                stage="APEX Parsing",
                current=index,
                total=total_payloads,
                subject=(
                    metadata.apex_name
                ),
                operation=(
                    "APEX lineage and manifest parsed"
                ),
                item=(
                    f"{outer_container.path.name} "
                    f"version={metadata.version}"
                ),
                produced=len(
                    parsed_entries
                ),
                state=(
                    ProgressState.COMPLETE
                    if index == total_payloads
                    else ProgressState.RUNNING
                ),
            )

        #
        # Every canonical APEX_CONTAINER_EXTRACTION artifact must belong to
        # exactly one represented logical lineage.
        #
        expected_apex_members = tuple(
            artifact
            for artifact
            in extraction.artifacts
            if (
                artifact.operation
                is ExtractionOperation
                .APEX_CONTAINER_EXTRACTION
            )
        )

        expected_member_ids = {
            id(artifact)
            for artifact
            in expected_apex_members
        }

        if (
            expected_member_ids
            != seen_apex_member_ids
        ):
            missing = (
                expected_member_ids
                - seen_apex_member_ids
            )

            extra = (
                seen_apex_member_ids
                - expected_member_ids
            )

            raise AndroidParsingPipelineError(
                "APEX Extraction-lineage conservation failed: "
                f"missing={len(missing)}, "
                f"extra={len(extra)}"
            )

        if len(
            parsed_entries
        ) != len(
            seen_outer_ids
        ):
            raise AndroidParsingPipelineError(
                "APEX logical population does not preserve "
                "one result per outer canonical container"
            )

        return tuple(
            parsed_entries
        )

    def _parse_sflb(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        AndroidParsedSflbEntry,
        ...,
    ]:
        artifacts = tuple(
            sorted(
                (
                    artifact
                    for artifact in extraction.artifacts
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .SFLB_ENTRY_EXTRACTION
                    )
                ),
                key=lambda artifact: (
                    (
                        artifact.parent.path.as_posix()
                        if artifact.parent is not None
                        else ""
                    ),
                    artifact.semantic_name or "",
                    artifact.path.as_posix(),
                ),
            )
        )

        parsed_entries: list[
            AndroidParsedSflbEntry
        ] = []

        total = len(
            artifacts
        )

        for index, artifact in enumerate(
            artifacts,
            start=1,
        ):
            subject = (
                artifact.semantic_name
                or artifact.path.name
            )

            self._report_parser_item(
                stage="SFLB Entry Parsing",
                current=index - 1,
                total=total,
                subject=subject,
                operation=(
                    "recording canonical SFLB entry structure"
                ),
                item=artifact.path.as_posix(),
                produced=len(
                    parsed_entries
                ),
            )

            parsed = (
                self.sflb_parser
                .parse(
                    artifact
                )
            )

            if not isinstance(
                parsed,
                AndroidParsedSflbEntry,
            ):
                raise AndroidParsingPipelineError(
                    "SFLB parser returned an unsupported result type"
                )

            if parsed.artifact is not artifact:
                raise AndroidParsingPipelineError(
                    "SFLB Parsing must preserve exact canonical "
                    "Extraction artifact identity"
                )

            parsed_entries.append(
                parsed
            )

            self._report_parser_item(
                stage="SFLB Entry Parsing",
                current=index,
                total=total,
                subject=subject,
                operation="SFLB entry parsed",
                item=(
                    f"entry={parsed.entry_index + 1}/"
                    f"{parsed.entry_count} "
                    f"size={parsed.payload_size_bytes} "
                    f"flags=0x{parsed.flags:x}"
                ),
                produced=len(
                    parsed_entries
                ),
                state=(
                    ProgressState.COMPLETE
                    if index == total
                    else ProgressState.RUNNING
                ),
            )

        expected_ids = {
            id(artifact)
            for artifact
            in artifacts
        }

        actual_ids = {
            id(parsed.artifact)
            for parsed
            in parsed_entries
        }

        if expected_ids != actual_ids:
            raise AndroidParsingPipelineError(
                "Parsing SFLB conservation failed"
            )

        if len(actual_ids) != len(
            parsed_entries
        ):
            raise AndroidParsingPipelineError(
                "Parsing SFLB population duplicated a canonical "
                "Extraction artifact"
            )

        return tuple(
            parsed_entries
        )

    def _parse_bmp(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        AndroidParsedBmp,
        ...,
    ]:
        """
        Parse canonical decompressed SFLB resources as literal BMP files.

        Extraction owns SFLB recognition, resource materialization,
        compression detection, decompression, and lineage. Parsing consumes
        only the established canonical decompression artifacts and decodes
        intrinsic BMP structure.
        """

        artifacts = tuple(
            sorted(
                (
                    artifact
                    for artifact
                    in extraction.artifacts
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .SFLB_RESOURCE_DECOMPRESSION
                    )
                ),
                key=lambda artifact: (
                    artifact.path.as_posix()
                ),
            )
        )

        parsed_entries: list[
            AndroidParsedBmp
        ] = []

        total = len(
            artifacts
        )

        for index, artifact in enumerate(
            artifacts,
            start=1,
        ):
            self._report_parser_item(
                stage="BMP Parsing",
                current=index - 1,
                total=total,
                subject=(
                    artifact.semantic_name
                    or artifact.path.name
                ),
                operation=(
                    "decoding BMP file and DIB headers"
                ),
                item=artifact.path.as_posix(),
                produced=len(
                    parsed_entries
                ),
            )

            parsed = self.bmp_parser.parse(
                artifact
            )

            if not isinstance(
                parsed,
                AndroidParsedBmp,
            ):
                raise AndroidParsingPipelineError(
                    "BMP parser must return AndroidParsedBmp"
                )

            if parsed.artifact is not artifact:
                raise AndroidParsingPipelineError(
                    "BMP Parsing must preserve exact canonical "
                    "Extraction artifact identity"
                )

            parsed_entries.append(
                parsed
            )

            self._report_parser_item(
                stage="BMP Parsing",
                current=index,
                total=total,
                subject=(
                    artifact.semantic_name
                    or artifact.path.name
                ),
                operation="BMP metadata parsed",
                item=(
                    f"{parsed.width}x{parsed.height} "
                    f"{parsed.bits_per_pixel}bpp "
                    f"compression={parsed.compression}"
                ),
                produced=len(
                    parsed_entries
                ),
                state=(
                    ProgressState.COMPLETE
                    if index == total
                    else ProgressState.RUNNING
                ),
            )

        expected_ids = {
            id(artifact)
            for artifact
            in artifacts
        }

        actual_ids = {
            id(parsed.artifact)
            for parsed
            in parsed_entries
        }

        if expected_ids != actual_ids:
            raise AndroidParsingPipelineError(
                "Parsing BMP conservation failed"
            )

        if len(actual_ids) != len(
            parsed_entries
        ):
            raise AndroidParsingPipelineError(
                "Parsing BMP population duplicated a canonical "
                "Extraction artifact"
            )

        return tuple(
            parsed_entries
        )

    def _parse_kernels(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        ParsedKernelImage,
        ...,
    ]:
        """
        Parse every canonical decompressed kernel artifact.

        Eligibility is defined exclusively by the canonical Extraction
        operation. A boot component merely named ``kernel`` is not promoted
        into the kernel population unless Extraction actually established a
        KERNEL_DECOMPRESSION artifact.
        """

        artifacts = tuple(
            sorted(
                (
                    artifact
                    for artifact in extraction.artifacts
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .KERNEL_DECOMPRESSION
                    )
                ),
                key=lambda artifact: (
                    (
                        artifact.parent.path.as_posix()
                        if artifact.parent is not None
                        else ""
                    ),
                    artifact.path.as_posix(),
                ),
            )
        )

        parsed_results: list[
            ParsedKernelImage
        ] = []

        for artifact in artifacts:
            parsed = self.kernel_parser.parse(
                artifact
            )

            if not isinstance(
                parsed,
                ParsedKernelImage,
            ):
                raise AndroidParsingPipelineError(
                    "kernel parser must return ParsedKernelImage"
                )

            if parsed.artifact is not artifact:
                raise AndroidParsingPipelineError(
                    "kernel Parsing must preserve exact canonical "
                    "Extraction artifact identity"
                )

            parsed_results.append(
                parsed
            )

        expected_ids = {
            id(artifact)
            for artifact in artifacts
        }

        actual_ids = {
            id(parsed.artifact)
            for parsed in parsed_results
        }

        if expected_ids != actual_ids:
            raise AndroidParsingPipelineError(
                "Parsing kernel conservation failed"
            )

        if len(actual_ids) != len(
            parsed_results
        ):
            raise AndroidParsingPipelineError(
                "Parsing kernel population duplicated a canonical "
                "Extraction artifact"
            )

        return tuple(
            parsed_results
        )

    def _parse_boot_dtbs(
        self,
        extraction: AndroidExtractionResult,
        boot_images: tuple[
            ParsedBootImage,
            ...,
        ],
    ) -> tuple[
        ParsedFdt,
        ...,
    ]:
        """
        Parse every canonical FDT_MEMBER_EXTRACTION child of an exact
        boot-family ``dtb`` component.

        Extraction owns concatenated-member discovery and byte boundaries.
        Parsing consumes only those exact canonical member artifacts.
        """

        artifacts: list[
            object
        ] = []

        for image in boot_images:
            dtb_components = tuple(
                artifact
                for artifact
                in image.component_artifacts
                if artifact.semantic_name == "dtb"
            )

            if len(
                dtb_components
            ) > 1:
                raise AndroidParsingPipelineError(
                    "canonical boot-family image contains multiple "
                    f"dtb components: {image.partition.name}"
                )

            if not dtb_components:
                continue

            component = (
                dtb_components[0]
            )

            members = tuple(
                artifact
                for artifact
                in extraction.children_of(
                    component
                )
                if (
                    artifact.operation
                    is ExtractionOperation
                    .FDT_MEMBER_EXTRACTION
                )
            )

            def member_index(
                artifact,
            ) -> int:
                value = self._canonical_fact(
                    artifact,
                    "member_index",
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
                    or value < 0
                ):
                    raise AndroidParsingPipelineError(
                        "canonical FDT member is missing valid "
                        f"member_index: {artifact.path}"
                    )

                return value

            members = tuple(
                sorted(
                    members,
                    key=lambda artifact: (
                        member_index(
                            artifact
                        ),
                        artifact.path.as_posix(),
                    ),
                )
            )

            member_count_values = {
                self._canonical_fact(
                    artifact,
                    "member_count",
                )
                for artifact
                in members
            }

            if members:
                if (
                    len(
                        member_count_values
                    )
                    != 1
                ):
                    raise AndroidParsingPipelineError(
                        "canonical boot DTB member population has "
                        "inconsistent member_count facts"
                    )

                expected_count = next(
                    iter(
                        member_count_values
                    )
                )

                if (
                    isinstance(
                        expected_count,
                        bool,
                    )
                    or not isinstance(
                        expected_count,
                        int,
                    )
                    or expected_count
                    != len(
                        members
                    )
                ):
                    raise AndroidParsingPipelineError(
                        "canonical boot DTB member population "
                        "failed member-count conservation"
                    )

                expected_indices = tuple(
                    range(
                        len(
                            members
                        )
                    )
                )

                actual_indices = tuple(
                    member_index(
                        artifact
                    )
                    for artifact
                    in members
                )

                if (
                    actual_indices
                    != expected_indices
                ):
                    raise AndroidParsingPipelineError(
                        "canonical boot DTB members do not preserve "
                        "contiguous source order"
                    )

            artifacts.extend(
                members
            )

        parsed_results: list[
            ParsedFdt
        ] = []

        for artifact in artifacts:
            parsed = (
                self.dtb_parser.parse(
                    artifact
                )
            )

            if not isinstance(
                parsed,
                ParsedFdt,
            ):
                raise AndroidParsingPipelineError(
                    "boot DTB parser must return ParsedFdt"
                )

            if (
                parsed.artifact
                is not artifact
            ):
                raise AndroidParsingPipelineError(
                    "boot DTB Parsing must preserve exact canonical "
                    "FDT member artifact identity"
                )

            parsed_results.append(
                parsed
            )

        expected_ids = tuple(
            id(
                artifact
            )
            for artifact
            in artifacts
        )

        actual_ids = tuple(
            id(
                parsed.artifact
            )
            for parsed
            in parsed_results
        )

        if (
            actual_ids
            != expected_ids
        ):
            raise AndroidParsingPipelineError(
                "boot DTB Parsing failed canonical member "
                "order/identity conservation"
            )

        return tuple(
            parsed_results
        )


    def _parse_dtbo(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        AndroidParsedDtboEntry,
        ...,
    ]:
        """
        Parse canonical DTBO entry artifacts produced by Extraction.

        Parsing does not rediscover DTBO containers, decode dtbo.img, or
        reconstruct DT table metadata. Selection is based exclusively on the
        canonical Extraction operation.
        """

        artifacts = tuple(
            artifact
            for artifact in extraction.artifacts
            if (
                artifact.operation
                is ExtractionOperation
                .DTBO_ENTRY_EXTRACTION
            )
        )

        artifacts = tuple(
            sorted(
                artifacts,
                key=lambda artifact: (
                    (
                        artifact.parent.path.as_posix()
                        if artifact.parent is not None
                        else ""
                    ),
                    artifact.semantic_name or "",
                    artifact.path.as_posix(),
                ),
            )
        )

        parsed_entries: list[
            AndroidParsedDtboEntry
        ] = []

        total_artifacts = len(
            artifacts
        )

        for index, artifact in enumerate(
            artifacts,
            start=1,
        ):
            self._report_parser_item(
                stage="DTBO Parsing",
                current=index - 1,
                total=total_artifacts,
                subject=(
                    artifact.semantic_name
                    or "DTBO entry"
                ),
                operation=(
                    "decoding Flattened Device Tree"
                ),
                item=artifact.path.as_posix(),
                produced=index - 1,
            )

            parsed = (
                self.dtb_parser.parse(
                    artifact
                )
            )

            if not isinstance(
                parsed,
                ParsedFdt,
            ):
                raise AndroidParsingPipelineError(
                    "DTB parser must return ParsedFdt"
                )

            if (
                parsed.artifact
                is not artifact
            ):
                raise AndroidParsingPipelineError(
                    "DTBO Parsing must preserve exact canonical "
                    "Extraction artifact identity"
                )

            overlay = (
                self.dtbo_overlay_parser.parse(
                    parsed
                )
            )

            if not isinstance(
                overlay,
                ParsedDtboOverlayMetadata,
            ):
                raise AndroidParsingPipelineError(
                    "DTBO overlay parser must return "
                    "ParsedDtboOverlayMetadata"
                )

            if overlay.fdt is not parsed:
                raise AndroidParsingPipelineError(
                    "DTBO overlay Parsing must preserve exact "
                    "ParsedFdt identity"
                )

            parsed_entry = (
                AndroidParsedDtboEntry(
                    artifact=artifact,
                    fdt=parsed,
                    overlay=overlay,
                )
            )

            parsed_entries.append(
                parsed_entry
            )

            self._report_parser_item(
                stage="DTBO Parsing",
                current=index,
                total=total_artifacts,
                subject=(
                    artifact.semantic_name
                    or "DTBO entry"
                ),
                operation=(
                    "Flattened Device Tree parsed"
                ),
                item=(
                    f"{artifact.path.name} "
                    f"nodes={parsed.node_count:,} "
                    f"properties={parsed.property_count:,}"
                ),
                produced=len(
                    parsed_entries
                ),
                state=(
                    ProgressState.COMPLETE
                    if index == total_artifacts
                    else ProgressState.RUNNING
                ),
            )

        expected_ids = {
            id(artifact)
            for artifact
            in artifacts
        }

        actual_ids = {
            id(parsed.artifact)
            for parsed
            in parsed_entries
        }

        if expected_ids != actual_ids:
            raise AndroidParsingPipelineError(
                "Parsing DTBO conservation failed"
            )

        if len(actual_ids) != len(
            parsed_entries
        ):
            raise AndroidParsingPipelineError(
                "Parsing DTBO population duplicated a canonical "
                "Extraction artifact"
            )

        return tuple(
            parsed_entries
        )

    def _parse_bootloader_children(
        self,
        extraction: AndroidExtractionResult,
    ) -> tuple[
        tuple[
            ParsedBootloaderChild,
            ...,
        ],
        tuple[
            ParsedBootloaderChildDisposition,
            ...,
        ],
    ]:
        """
        Parse and account for every canonical bootloader-child input.

        Eligibility is established exclusively by canonical Extraction
        operation identity.

        Supported intrinsic structures are parsed literally. Unsupported FBPK
        payloads remain exact canonical artifacts with an explicit ``opaque``
        Parsing disposition.

        No candidate admitted into this family may disappear from Parsing
        state.
        """

        artifacts = tuple(
            sorted(
                (
                    artifact
                    for artifact in extraction.artifacts
                    if artifact.operation
                    in {
                        ExtractionOperation
                        .FBPK_ENTRY_EXTRACTION,
                        ExtractionOperation
                        .BOOT_FIRMWARE_PAYLOAD_EXTRACTION,
                        ExtractionOperation
                        .UFPK_DESCRIPTOR_EXTRACTION,
                    }
                ),
                key=lambda artifact: (
                    artifact.path.as_posix()
                ),
            )
        )

        total = len(
            artifacts
        )

        parsed_results: list[
            ParsedBootloaderChild
        ] = []

        dispositions: list[
            ParsedBootloaderChildDisposition
        ] = []

        for index, artifact in enumerate(
            artifacts,
            start=1,
        ):
            semantic_name = (
                artifact.semantic_name
                or artifact.path.name
            )

            parsed_child = None

            if (
                artifact.operation
                is ExtractionOperation
                .UFPK_DESCRIPTOR_EXTRACTION
            ):
                self._report_parser_item(
                    stage="Bootloader Child Parsing",
                    current=index - 1,
                    total=total,
                    subject=semantic_name,
                    operation=(
                        "decoding UFPK descriptor extent"
                    ),
                    item=artifact.path.as_posix(),
                    produced=len(
                        parsed_results
                    ),
                )

                parsed = (
                    self.ufpk_descriptor_parser
                    .parse(
                        artifact
                    )
                )

                if not isinstance(
                    parsed,
                    AndroidParsedUfpkDescriptor,
                ):
                    raise AndroidParsingPipelineError(
                        "UFPK descriptor parser returned "
                        "an unsupported result type"
                    )

                parsed_child = (
                    ParsedBootloaderChild(
                        artifact=artifact,
                        parsed=parsed,
                    )
                )

                detail = (
                    f"kind={parsed.descriptor_kind} "
                    f"identity={parsed.identity} "
                    f"field_28=0x{parsed.field_28:x} "
                    f"next=0x{parsed.next_offset:x}"
                )

                operation = (
                    "UFPK descriptor parsed"
                )

            elif (
                artifact.operation
                is ExtractionOperation
                .BOOT_FIRMWARE_PAYLOAD_EXTRACTION
            ):
                self._report_parser_item(
                    stage="Bootloader Child Parsing",
                    current=index - 1,
                    total=total,
                    subject=semantic_name,
                    operation=(
                        "decoding terminal boot firmware payload"
                    ),
                    item=artifact.path.as_posix(),
                    produced=len(
                        parsed_results
                    ),
                )

                parsed = (
                    self.boot_firmware_payload_parser
                    .parse(
                        artifact
                    )
                )

                if not isinstance(
                    parsed,
                    AndroidParsedBootFirmwarePayload,
                ):
                    raise AndroidParsingPipelineError(
                        "boot firmware payload parser returned "
                        "an unsupported result type"
                    )

                parsed_child = (
                    ParsedBootloaderChild(
                        artifact=artifact,
                        parsed=parsed,
                    )
                )

                detail = (
                    f"identity={parsed.firmware_identity} "
                    f"RET={parsed.arm64_ret_count:,} "
                    f"NOP={parsed.arm64_nop_count:,} "
                    f"entropy={parsed.entropy_bits_per_byte:.4f}"
                )

                operation = (
                    "terminal boot firmware payload parsed"
                )

            elif not (
                self.bootloader_child_parser
                .supports(
                    artifact
                )
            ):
                disposition = (
                    ParsedBootloaderChildDisposition(
                        artifact=artifact,
                        disposition="opaque",
                    )
                )

                dispositions.append(
                    disposition
                )

                self._report_parser_item(
                    stage="Bootloader Child Parsing",
                    current=index,
                    total=total,
                    subject=semantic_name,
                    operation=(
                        "unsupported structured child format; "
                        "preserved with explicit opaque disposition"
                    ),
                    item=artifact.path.as_posix(),
                    produced=len(
                        parsed_results
                    ),
                    state=(
                        ProgressState.COMPLETE
                        if index == total
                        else ProgressState.RUNNING
                    ),
                )

                continue

            else:
                self._report_parser_item(
                    stage="Bootloader Child Parsing",
                    current=index - 1,
                    total=total,
                    subject=semantic_name,
                    operation=(
                        "decoding structured FBPK child payload"
                    ),
                    item=artifact.path.as_posix(),
                    produced=len(
                        parsed_results
                    ),
                )

                parsed = (
                    self.bootloader_child_parser
                    .parse(
                        artifact
                    )
                )

                if not isinstance(
                    parsed,
                    (
                        AndroidParsedFbpt,
                        AndroidParsedUfsDescriptor,
                        AndroidParsedUfpk,
                    ),
                ):
                    raise AndroidParsingPipelineError(
                        "bootloader-child parser returned "
                        "an unsupported result type"
                    )

                parsed_child = (
                    ParsedBootloaderChild(
                        artifact=artifact,
                        parsed=parsed,
                    )
                )

                if isinstance(
                    parsed,
                    AndroidParsedFbpt,
                ):
                    detail = (
                        "FBPT "
                        f"entries={parsed.entry_count}"
                    )

                elif isinstance(
                    parsed,
                    AndroidParsedUfsDescriptor,
                ):
                    detail = (
                        f"{parsed.kind.value} "
                        f"version={parsed.version}"
                    )

                else:
                    detail = (
                        "UFPK "
                        f"version={parsed.version} "
                        f"package={parsed.package_name}"
                    )

                operation = (
                    "structured bootloader child parsed"
                )

            if parsed_child is None:
                raise AndroidParsingPipelineError(
                    "supported bootloader child escaped parsed result "
                    f"construction: {artifact.path}"
                )

            parsed_results.append(
                parsed_child
            )

            dispositions.append(
                ParsedBootloaderChildDisposition(
                    artifact=artifact,
                    disposition="parsed",
                    parsed=parsed_child,
                )
            )

            self._report_parser_item(
                stage="Bootloader Child Parsing",
                current=index,
                total=total,
                subject=semantic_name,
                operation=operation,
                item=detail,
                produced=len(
                    parsed_results
                ),
                state=(
                    ProgressState.COMPLETE
                    if index == total
                    else ProgressState.RUNNING
                ),
            )

        expected_ids = {
            id(artifact)
            for artifact in artifacts
        }

        actual_ids = {
            id(disposition.artifact)
            for disposition in dispositions
        }

        if expected_ids != actual_ids:
            raise AndroidParsingPipelineError(
                "Parsing bootloader child conservation failed"
            )

        if len(
            actual_ids
        ) != len(
            dispositions
        ):
            raise AndroidParsingPipelineError(
                "Parsing bootloader child ledger duplicated a "
                "canonical Extraction artifact"
            )

        parsed_from_ledger = {
            id(disposition.parsed): disposition.parsed
            for disposition in dispositions
            if disposition.parsed is not None
        }

        canonical_parsed = {
            id(parsed): parsed
            for parsed in parsed_results
        }

        if (
            set(parsed_from_ledger)
            != set(canonical_parsed)
        ):
            raise AndroidParsingPipelineError(
                "Parsing bootloader child ledger does not preserve "
                "every parsed result exactly once"
            )

        return (
            tuple(
                parsed_results
            ),
            tuple(
                dispositions
            ),
        )

    @staticmethod
    def _avb_fact(
        artifact,
        name: str,
    ):
        matches = tuple(
            fact.value
            for fact in artifact.facts
            if fact.name == name
        )

        if not matches:
            return None

        if len(matches) != 1:
            raise AndroidParsingPipelineError(
                "canonical AVB artifact contains duplicate "
                f"{name!r} facts: {artifact.path}"
            )

        return matches[0]

    @classmethod
    def _require_avb_fact(
        cls,
        artifact,
        name: str,
    ):
        value = cls._avb_fact(
            artifact,
            name,
        )

        if value is None:
            raise AndroidParsingPipelineError(
                "canonical AVB artifact is missing required "
                f"{name!r} fact: {artifact.path}"
            )

        return value

    @classmethod
    def _footer_from_extraction(
        cls,
        artifact,
    ) -> AndroidParsedAvbFooter:
        """
        Rehydrate literal AVB footer observations from authoritative
        Extraction facts.

        Parsing never reopens the containing image to rediscover footer
        location or VBMeta physical extent.
        """

        if (
            artifact.operation
            is not ExtractionOperation.AVB_REGION_EXTRACTION
        ):
            raise AndroidParsingPipelineError(
                "AVB footer must come from AVB_REGION_EXTRACTION"
            )

        if (
            cls._require_avb_fact(
                artifact,
                "region_kind",
            )
            != "avb_footer"
        ):
            raise AndroidParsingPipelineError(
                "AVB footer artifact has incorrect canonical "
                f"region kind: {artifact.path}"
            )

        footer = AndroidParsedAvbFooter(
            version_major=cls._require_avb_fact(
                artifact,
                "avb_footer_version_major",
            ),
            version_minor=cls._require_avb_fact(
                artifact,
                "avb_footer_version_minor",
            ),
            original_image_size=cls._require_avb_fact(
                artifact,
                "avb_original_image_size_bytes",
            ),
            vbmeta_offset=cls._require_avb_fact(
                artifact,
                "avb_vbmeta_offset_bytes",
            ),
            vbmeta_size=cls._require_avb_fact(
                artifact,
                "avb_vbmeta_size_bytes",
            ),
        )

        if not isinstance(
            footer,
            AndroidParsedAvbFooter,
        ):
            raise AndroidParsingPipelineError(
                "AVB footer fact projection must produce "
                "AndroidParsedAvbFooter"
            )

        return footer

    @staticmethod
    def _partition_for_exact_artifact(
        inventory: PartitionInventory,
        artifact,
    ) -> InventoryPartition | None:
        matches = tuple(
            partition
            for partition in inventory.partitions
            if partition.artifact is artifact
        )

        if len(matches) > 1:
            raise AndroidParsingPipelineError(
                "canonical PartitionInventory contains duplicate "
                "exact artifact identity"
            )

        return (
            matches[0]
            if matches
            else None
        )

    def _parse_vbmeta(
        self,
        extraction: AndroidExtractionResult,
        inventory: PartitionInventory,
    ) -> tuple[
        tuple[
            ParsedAvbVbmeta,
            ...,
        ],
        tuple[
            ParsedAvbRegion,
            ...,
        ],
    ]:
        """
        Parse the complete canonical AVB surface.

        Extraction owns:
        - recognition of footer-backed AVB containers;
        - physical AVB region materialization;
        - offsets, extents, and footer structure facts;
        - exact parent lineage.

        Parsing owns:
        - literal AVB0 header decoding;
        - descriptor decoding;
        - explicit disposition of every AVB_REGION_EXTRACTION artifact.

        Trust-chain interpretation, applicability, signing policy, and
        device-level verified-boot conclusions remain downstream.
        """

        standalone_sources: list[
            tuple[
                InventoryPartition,
                object,
            ]
        ] = []

        #
        # Standalone VBMeta is identified from canonical Extraction structure,
        # not from a fixed partition-name list.
        #
        for partition in inventory.partitions:
            artifact = partition.artifact

            container_format = self._avb_fact(
                artifact,
                "container_format",
            )

            if container_format != "avb_vbmeta":
                continue

            standalone_sources.append(
                (
                    partition,
                    artifact,
                )
            )

        standalone_sources.sort(
            key=lambda item: (
                item[0].name,
                item[1].path.as_posix(),
            )
        )

        regions = tuple(
            sorted(
                (
                    artifact
                    for artifact in extraction.artifacts
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .AVB_REGION_EXTRACTION
                    )
                ),
                key=lambda artifact: (
                    (
                        artifact.parent.path.as_posix()
                        if artifact.parent is not None
                        else ""
                    ),
                    artifact.semantic_name or "",
                    artifact.path.as_posix(),
                ),
            )
        )

        #
        # First validate the complete AVB region population and group exact
        # sibling artifacts by their containing canonical image.
        #
        regions_by_parent: dict[
            int,
            list,
        ] = {}

        supported_region_kinds = {
            "embedded_vbmeta",
            "avb_footer",
            "avb_hashtree",
            "avb_fec",
        }

        for artifact in regions:
            parent = artifact.parent

            if parent is None:
                raise AndroidParsingPipelineError(
                    "AVB region has no canonical containing artifact: "
                    f"{artifact.path}"
                )

            region_kind = self._require_avb_fact(
                artifact,
                "region_kind",
            )

            if region_kind not in supported_region_kinds:
                raise AndroidParsingPipelineError(
                    "Parsing has no disposition for canonical AVB "
                    f"region kind {region_kind!r}: {artifact.path}"
                )

            regions_by_parent.setdefault(
                id(parent),
                [],
            ).append(
                artifact
            )

        parsed_vbmeta: list[
            ParsedAvbVbmeta
        ] = []

        #
        # Standalone AVB0 roots.
        #
        for partition, artifact in standalone_sources:
            metadata = self.vbmeta_parser.parse(
                artifact
            )

            if not isinstance(
                metadata,
                AndroidParsedVbmeta,
            ):
                raise AndroidParsingPipelineError(
                    "VBMeta parser must return AndroidParsedVbmeta"
                )

            parsed_vbmeta.append(
                ParsedAvbVbmeta(
                    artifact=artifact,
                    container_artifact=artifact,
                    partition=partition,
                    metadata=metadata,
                )
            )

        embedded_by_artifact_id: dict[
            int,
            ParsedAvbVbmeta,
        ] = {}

        #
        # Embedded VBMeta is decoded from the exact extracted avb_vbmeta child.
        # Since Extraction already sliced the region, Parsing reads it at
        # offset zero and never rediscovers the containing-image footer.
        #
        for artifact in regions:
            region_kind = self._require_avb_fact(
                artifact,
                "region_kind",
            )

            if region_kind != "embedded_vbmeta":
                continue

            container = artifact.parent

            if container is None:
                raise AndroidParsingPipelineError(
                    "embedded VBMeta has no containing artifact"
                )

            siblings = regions_by_parent[
                id(container)
            ]

            footer_artifacts = tuple(
                sibling
                for sibling in siblings
                if (
                    self._require_avb_fact(
                        sibling,
                        "region_kind",
                    )
                    == "avb_footer"
                )
            )

            if len(footer_artifacts) != 1:
                raise AndroidParsingPipelineError(
                    "embedded VBMeta must have exactly one canonical "
                    "AVB footer sibling: "
                    f"{container.path}"
                )

            footer_artifact = (
                footer_artifacts[0]
            )

            footer = (
                self._footer_from_extraction(
                    footer_artifact
                )
            )

            metadata = self.vbmeta_parser.parse(
                artifact
            )

            if not isinstance(
                metadata,
                AndroidParsedVbmeta,
            ):
                raise AndroidParsingPipelineError(
                    "VBMeta parser must return AndroidParsedVbmeta"
                )

            if (
                artifact.size_bytes is not None
                and footer.vbmeta_size
                != artifact.size_bytes
            ):
                raise AndroidParsingPipelineError(
                    "Extraction AVB footer VBMeta size does not "
                    "match exact avb_vbmeta artifact size: "
                    f"{artifact.path}"
                )

            parsed = ParsedAvbVbmeta(
                artifact=artifact,
                container_artifact=container,
                partition=(
                    self._partition_for_exact_artifact(
                        inventory,
                        container,
                    )
                ),
                metadata=metadata,
                footer_artifact=footer_artifact,
                footer=footer,
            )

            embedded_by_artifact_id[
                id(artifact)
            ] = parsed

            parsed_vbmeta.append(
                parsed
            )

        #
        # Preserve deterministic Parsing order:
        # standalone partition-backed VBMeta first, then embedded sources in
        # exact canonical Extraction-region order.
        #
        standalone_count = len(
            standalone_sources
        )

        embedded_tail = sorted(
            parsed_vbmeta[
                standalone_count:
            ],
            key=lambda parsed: (
                parsed.container_artifact.path.as_posix(),
                parsed.artifact.path.as_posix(),
            ),
        )

        parsed_vbmeta = (
            parsed_vbmeta[
                :standalone_count
            ]
            + embedded_tail
        )

        embedded_by_artifact_id = {
            id(parsed.artifact): parsed
            for parsed in parsed_vbmeta
            if (
                parsed.artifact.operation
                is ExtractionOperation
                .AVB_REGION_EXTRACTION
            )
        }

        dispositions: list[
            ParsedAvbRegion
        ] = []

        for artifact in regions:
            region_kind = self._require_avb_fact(
                artifact,
                "region_kind",
            )

            if region_kind == "embedded_vbmeta":
                parsed = (
                    embedded_by_artifact_id
                    .get(
                        id(artifact)
                    )
                )

                if parsed is None:
                    raise AndroidParsingPipelineError(
                        "canonical embedded VBMeta region was not parsed: "
                        f"{artifact.path}"
                    )

                disposition = ParsedAvbRegion(
                    artifact=artifact,
                    disposition="parsed",
                    vbmeta=parsed,
                )

            elif region_kind == "avb_footer":
                disposition = ParsedAvbRegion(
                    artifact=artifact,
                    disposition="fact_derived",
                )

            elif region_kind in {
                "avb_hashtree",
                "avb_fec",
            }:
                disposition = ParsedAvbRegion(
                    artifact=artifact,
                    disposition="preserved",
                )

            else:
                raise AndroidParsingPipelineError(
                    "canonical AVB region escaped Parsing disposition: "
                    f"{artifact.path}"
                )

            dispositions.append(
                disposition
            )

        #
        # Complete-consumption invariant:
        #
        # every Extraction-owned AVB region
        # ==
        # every Parsing AVB-region disposition.
        #
        expected_ids = {
            id(artifact)
            for artifact in regions
        }

        actual_ids = {
            id(region.artifact)
            for region in dispositions
        }

        if expected_ids != actual_ids:
            raise AndroidParsingPipelineError(
                "Parsing AVB region conservation failed"
            )

        if len(actual_ids) != len(
            dispositions
        ):
            raise AndroidParsingPipelineError(
                "Parsing AVB region ledger duplicated a canonical "
                "Extraction artifact"
            )

        return (
            tuple(
                parsed_vbmeta
            ),
            tuple(
                dispositions
            ),
        )

    @staticmethod
    def _canonical_fact(
        artifact,
        name: str,
    ):
        values = tuple(
            fact.value
            for fact in artifact.facts
            if fact.name == name
        )

        if not values:
            return None

        if len(values) != 1:
            raise AndroidParsingPipelineError(
                "canonical artifact contains duplicate "
                f"{name!r} facts: {artifact.path}"
            )

        return values[0]

    @staticmethod
    def _boot_component_artifacts(
        extraction: AndroidExtractionResult,
        partition: InventoryPartition,
    ) -> tuple[
        object,
        ...,
    ]:
        """
        Preserve exact Extraction-owned components for one canonical
        boot-family container.
        """

        return tuple(
            sorted(
                (
                    artifact
                    for artifact
                    in extraction.children_of(
                        partition.artifact
                    )
                    if (
                        artifact.operation
                        is ExtractionOperation
                        .BOOT_COMPONENT_EXTRACTION
                    )
                ),
                key=lambda artifact: (
                    artifact.semantic_name or "",
                    artifact.path.as_posix(),
                ),
            )
        )

    def _parse_boot_images(
        self,
        extraction: AndroidExtractionResult,
        inventory: PartitionInventory,
    ) -> tuple[
        ParsedBootImage,
        ...,
    ]:
        """
        Parse every canonical boot-family container recognized upstream.

        Parsing dispatches on canonical ``container_format`` and preserves
        ``container_kind`` independently.

        No device-specific partition-name list is used here.
        """

        candidates: list[
            tuple[
                InventoryPartition,
                str,
                str,
            ]
        ] = []

        supported_formats = {
            "android_boot",
            "android_vendor_boot",
        }

        for partition in inventory.partitions:
            artifact = partition.artifact

            container_format = (
                self._canonical_fact(
                    artifact,
                    "container_format",
                )
            )

            if container_format not in supported_formats:
                continue

            container_kind = (
                self._canonical_fact(
                    artifact,
                    "container_kind",
                )
            )

            if not isinstance(
                container_kind,
                str,
            ) or not container_kind:
                raise AndroidParsingPipelineError(
                    "canonical boot-family container is missing "
                    f"container_kind: {artifact.path}"
                )

            candidates.append(
                (
                    partition,
                    container_format,
                    container_kind,
                )
            )

        candidates.sort(
            key=lambda item: (
                item[1],
                item[2],
                item[0].name,
                item[0].artifact.path.as_posix(),
            )
        )

        parsed_results: list[
            ParsedBootImage
        ] = []

        for (
            partition,
            container_format,
            container_kind,
        ) in candidates:
            artifact = partition.artifact

            if (
                container_format
                == "android_boot"
            ):
                metadata = (
                    self.boot_parser.parse(
                        artifact
                    )
                )

                if not isinstance(
                    metadata,
                    ParsedBootImageMetadata,
                ):
                    raise AndroidParsingPipelineError(
                        "ANDROID! parser must return "
                        "ParsedBootImageMetadata"
                    )

            elif (
                container_format
                == "android_vendor_boot"
            ):
                metadata = (
                    self.vendor_boot_parser.parse(
                        artifact
                    )
                )

                if not isinstance(
                    metadata,
                    ParsedVendorBootImageMetadata,
                ):
                    raise AndroidParsingPipelineError(
                        "VNDRBOOT parser must return "
                        "ParsedVendorBootImageMetadata"
                    )

            else:
                raise AndroidParsingPipelineError(
                    "unsupported canonical boot-family format: "
                    f"{container_format}"
                )

            component_artifacts = (
                self._boot_component_artifacts(
                    extraction,
                    partition,
                )
            )

            bootconfig_artifacts = tuple(
                component
                for component
                in component_artifacts
                if (
                    component.semantic_name
                    == "bootconfig"
                )
            )

            if len(
                bootconfig_artifacts
            ) > 1:
                raise AndroidParsingPipelineError(
                    "canonical boot-family container has "
                    "ambiguous bootconfig components: "
                    f"{partition.name}"
                )

            bootconfig_artifact = (
                bootconfig_artifacts[0]
                if bootconfig_artifacts
                else None
            )

            bootconfig = None

            if bootconfig_artifact is not None:
                bootconfig = (
                    self.bootconfig_parser.parse(
                        bootconfig_artifact
                    )
                )

                if not isinstance(
                    bootconfig,
                    ParsedAndroidBootconfig,
                ):
                    raise AndroidParsingPipelineError(
                        "bootconfig parser must return "
                        "ParsedAndroidBootconfig"
                    )

            parsed_results.append(
                ParsedBootImage(
                    partition=partition,
                    container_format=(
                        container_format
                    ),
                    container_kind=(
                        container_kind
                    ),
                    metadata=metadata,
                    component_artifacts=(
                        component_artifacts
                    ),
                    bootconfig_artifact=(
                        bootconfig_artifact
                    ),
                    bootconfig=bootconfig,
                )
            )

        expected_partition_ids = {
            id(partition)
            for (
                partition,
                _container_format,
                _container_kind,
            )
            in candidates
        }

        actual_partition_ids = {
            id(parsed.partition)
            for parsed in parsed_results
        }

        if (
            expected_partition_ids
            != actual_partition_ids
        ):
            raise AndroidParsingPipelineError(
                "Parsing boot-family container conservation failed"
            )

        if len(
            actual_partition_ids
        ) != len(
            parsed_results
        ):
            raise AndroidParsingPipelineError(
                "Parsing boot-family population duplicated a "
                "canonical InventoryPartition"
            )

        return tuple(
            parsed_results
        )

    def _parse_vendor_ramdisk_tables(
        self,
        boot_images: tuple[
            ParsedBootImage,
            ...,
        ],
    ) -> tuple[
        ParsedVendorRamdiskTable,
        ...,
    ]:
        """
        Decode every exact canonical vendor_ramdisk_table boot component.

        Component order follows canonical Parsing boot-image order.
        """

        parsed_results: list[
            ParsedVendorRamdiskTable
        ] = []

        for image in boot_images:
            tables = tuple(
                artifact
                for artifact
                in image.component_artifacts
                if (
                    artifact.semantic_name
                    == "vendor_ramdisk_table"
                )
            )

            if len(
                tables
            ) > 1:
                raise AndroidParsingPipelineError(
                    "canonical boot-family image contains multiple "
                    "vendor_ramdisk_table components: "
                    f"{image.partition.name}"
                )

            if not tables:
                continue

            artifact = tables[0]

            try:
                parsed = (
                    AndroidVendorRamdiskTableParser
                    .parse(
                        artifact,
                        image.partition.artifact,
                    )
                )
            except Exception as error:
                raise AndroidParsingPipelineError(
                    "Unable to parse canonical vendor ramdisk "
                    f"table: {artifact.path}"
                ) from error

            parsed_results.append(
                parsed
            )

        expected_ids = tuple(
            id(
                artifact
            )
            for image
            in boot_images
            for artifact
            in image.component_artifacts
            if (
                artifact.semantic_name
                == "vendor_ramdisk_table"
            )
        )

        actual_ids = tuple(
            id(
                parsed.artifact
            )
            for parsed
            in parsed_results
        )

        if (
            actual_ids
            != expected_ids
        ):
            raise AndroidParsingPipelineError(
                "vendor ramdisk-table Parsing failed canonical "
                "component conservation"
            )

        return tuple(
            parsed_results
        )


    def _parse_boot_signatures(
        self,
        boot_images: tuple[
            ParsedBootImage,
            ...,
        ],
    ) -> tuple[
        ParsedBootSignature,
        ...,
    ]:
        """
        Decode canonical boot_signature components as literal AVB/VBMeta
        evidence without reclassifying them as AVB footer regions.
        """

        parsed_results: list[
            ParsedBootSignature
        ] = []

        for image in boot_images:
            signatures = tuple(
                artifact
                for artifact
                in image.component_artifacts
                if artifact.semantic_name == "boot_signature"
            )

            if len(
                signatures
            ) > 1:
                raise AndroidParsingPipelineError(
                    "canonical boot-family image contains multiple "
                    "boot_signature components: "
                    f"{image.partition.name}"
                )

            if not signatures:
                continue

            artifact = signatures[0]

            metadata = self.vbmeta_parser.parse(
                artifact
            )

            if not isinstance(
                metadata,
                AndroidParsedVbmeta,
            ):
                raise AndroidParsingPipelineError(
                    "boot-signature VBMeta parser must return "
                    "AndroidParsedVbmeta"
                )

            parsed_results.append(
                ParsedBootSignature(
                    artifact=artifact,
                    boot_image_artifact=(
                        image.partition.artifact
                    ),
                    metadata=metadata,
                )
            )

        expected_artifact_ids = tuple(
            id(
                artifact
            )
            for image
            in boot_images
            for artifact
            in image.component_artifacts
            if artifact.semantic_name == "boot_signature"
        )

        actual_artifact_ids = tuple(
            id(
                parsed.artifact
            )
            for parsed
            in parsed_results
        )

        if (
            actual_artifact_ids
            != expected_artifact_ids
        ):
            raise AndroidParsingPipelineError(
                "boot-signature Parsing population failed canonical "
                "component conservation"
            )

        return tuple(
            parsed_results
        )

    @classmethod
    def _select_partition(
        cls,
        inventory: PartitionInventory,
        base_name: str,
    ) -> InventoryPartition | None:
        """
        Select one canonical partition by base name.

        Exact unsuffixed identity is preferred. If only slotted partitions
        exist, one unique partition is accepted, otherwise the canonical
        ``_a`` slot is preferred. Ambiguous identities are rejected rather
        than silently collapsing provenance.
        """

        exact = inventory.partition(
            base_name
        )

        if exact is not None:
            return exact

        variants = inventory.partitions_named(
            base_name
        )

        if not variants:
            return None

        if len(variants) == 1:
            return variants[0]

        preferred = tuple(
            partition
            for partition in variants
            if (
                partition.slot_suffix
                == cls.PREFERRED_SLOT_SUFFIX
            )
        )

        if len(preferred) == 1:
            return preferred[0]

        names = ", ".join(
            partition.name
            for partition in variants
        )

        raise AndroidParsingPipelineError(
            "Unable to select one canonical "
            f"{base_name} partition for Parsing: "
            f"{names}"
        )
