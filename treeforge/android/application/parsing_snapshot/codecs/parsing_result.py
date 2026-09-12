from __future__ import annotations

from treeforge.android.parsing.elf.model import (
    AndroidElfEmbeddedReferenceKind,
    ParsedAndroidElfEmbeddedReference,
)

import base64
from pathlib import Path, PurePosixPath
from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadataEntry,
)
from treeforge.android.format.compression import (
    CompressionFormat,
)
from treeforge.android.parsing.apex.model import (
    AndroidParsedApex,
    ParsedApexContainer,
)
from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
    AndroidParsedAvbKernelCmdlineDescriptor,
    AndroidParsedAvbPropertyDescriptor,
    AndroidParsedAvbFooter,
    AndroidParsedVbmeta,
)
from treeforge.android.parsing.bmp.model import (
    AndroidParsedBmp,
)
from treeforge.android.parsing.boot.boot import (
    ParsedBootImageMetadata,
)
from treeforge.android.parsing.boot.bootconfig import (
    AndroidBootconfigEntry,
    AndroidBootconfigUnparsedLine,
    ParsedAndroidBootconfig,
)
from treeforge.android.parsing.boot.vendor_boot import (
    ParsedVendorBootImageMetadata,
)
from treeforge.android.parsing.boot.vendor_ramdisk_table import (
    ParsedVendorRamdiskTable,
    ParsedVendorRamdiskTableEntry,
)
from treeforge.android.parsing.bootloader.model import (
    AndroidParsedBootFirmwarePayload,
    AndroidParsedFbpt,
    AndroidParsedFbptEntry,
    AndroidParsedUfpk,
    AndroidParsedUfpkDescriptor,
    AndroidParsedUfsDescriptor,
    AndroidParsedUfsDescriptorKind,
)
from treeforge.android.parsing.dex.model import (
    AndroidDexClass,
    AndroidDexEndianEncoding,
    AndroidDexHeader,
    AndroidDexSource,
    AndroidDexSourceKind,
    AndroidDexString,
    AndroidDexType,
    ParsedAndroidDex,
)

from treeforge.android.parsing.dex.standalone import (
    AndroidStandaloneDexDisposition,
    AndroidStandaloneDexDispositionKind,
    AndroidStandaloneDexParsingResult,
)
from treeforge.android.parsing.dtb.model import (
    AndroidParsedDtboEntry,
    ParsedDtboExternalFixup,
    ParsedDtboExternalFixupLocation,
    ParsedDtboFragmentTarget,
    ParsedDtboLocalFixup,
    ParsedDtboOverlayMetadata,
    ParsedDtboSymbol,
    ParsedFdt,
    ParsedFdtHeader,
    ParsedFdtNode,
    ParsedFdtProperty,
    ParsedFdtReservation,
)
from treeforge.android.parsing.elf.model import (
    AndroidElfClass,
    AndroidElfEndianness,
    AndroidElfParsingResult,
    ParsedAndroidElf,
    ParsedAndroidElfAttribute,
    ParsedAndroidElfAttributeSection,
    ParsedAndroidElfNote,
    ParsedAndroidElfNoteSection,
    ParsedAndroidElfSource,
)
from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.linker import (
    AndroidLinkerConfigurationAssignment,
    AndroidLinkerConfigurationSection,
    AndroidLinkerConfigurationUnparsedLine,
    AndroidLinkerProtobufContribution,
    AndroidLinkerProtobufUnknownField,
    AndroidNativeLibraryConfigurationDeclaration,
    ParsedAndroidLinkerConfiguration,
    ParsedAndroidLinkerProtobufConfiguration,
    ParsedAndroidNativeLibraryConfiguration,
)
from treeforge.android.parsing.art_runtime import (
    AndroidArtImageSectionKind,
    AndroidArtRuntimeParsingResult,
    AndroidOatDexStorageDisposition,
    ParsedAndroidBcpBssInfo,
    ParsedAndroidBcpBssMappingInfo,
    ParsedAndroidIndexBssMapping,
    ParsedAndroidIndexBssMappingEntry,
    ParsedAndroidArtImage,
    ParsedAndroidArtImage111,
    ParsedAndroidArtImageSection,
    ParsedAndroidOat,
    ParsedAndroidOatStructuralHeader,
    ParsedAndroidOatDexFile,
    ParsedAndroidOatKeyValue,
    ParsedAndroidVdex,
    ParsedAndroidVdex027,
    ParsedAndroidVdexSection,
)
from treeforge.android.parsing.art_runtime.model import (
    AndroidDexLayoutSectionKind,
    AndroidDexLayoutType,
    ParsedAndroidDexLayoutSection,
    ParsedAndroidDexLayoutSections,
    ParsedAndroidDexLayoutSubsection,
)
from treeforge.android.parsing.classpath import (
    AndroidClasspathJar,
    AndroidClasspathParsingResult,
    AndroidClasspathProtobufUnknownField,
    ParsedAndroidClasspathConfiguration,
)
from treeforge.android.parsing.aconfig import (
    AndroidAconfigFlagMetadata,
    AndroidAconfigParsedFlag,
    AndroidAconfigParsingResult,
    AndroidAconfigProtobufUnknownField,
    AndroidAconfigTracepoint,
    ParsedAndroidAconfigConfiguration,
)
from treeforge.android.application.parsing_snapshot.codecs.new_parsing_families import (
    AndroidCertificateParsingResultCodec,
    AndroidFontParsingResultCodec,
    AndroidInputParsingResultCodec,
    AndroidJavaArchiveParsingResultCodec,
    AndroidShellScriptParsingResultCodec,
)
from treeforge.android.application.parsing_snapshot.codecs.structured_configuration import (
    STRUCTURED_CONFIGURATION_CODECS,
)
from treeforge.android.parsing.structured_configuration import (
    AndroidStructuredConfigurationParsingResult,
)
from treeforge.android.parsing.certificate import (
    AndroidCertificateParsingResult,
)
from treeforge.android.parsing.font import (
    AndroidFontParsingResult,
)
from treeforge.android.parsing.input import (
    AndroidInputParsingResult,
)
from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveParsingResult,
)
from treeforge.android.parsing.shell_script import (
    AndroidShellScriptParsingResult,
)
from treeforge.android.parsing.apk import (
    AndroidApkCandidateDisposition,
    AndroidApkManifestValue,
    AndroidApkOverlayManifest,
    AndroidApkParsingResult,
    AndroidApkSource,
    ParsedAndroidApk,
)

from treeforge.android.parsing.apk.model import (
    AndroidApkArchiveMember,
)
from treeforge.android.parsing.avf import (
    AndroidAvfVmConfigApex,
    AndroidAvfVmConfigCandidateDisposition,
    AndroidAvfVmConfigExtraApk,
    AndroidAvfVmConfigOs,
    AndroidAvfVmConfigParsingResult,
    AndroidAvfVmConfigSource,
    AndroidAvfVmConfigTask,
    ParsedAndroidAvfVmConfig,
)
from treeforge.android.parsing.kernel_module import (
    AndroidKernelModuleConfigurationKind,
    AndroidKernelModuleConfigurationLine,
    AndroidKernelModuleParsingResult,
    ParsedAndroidKernelModule,
    ParsedAndroidKernelModuleConfiguration,
    ParsedAndroidKernelModuleInfoEntry,
)
from treeforge.android.parsing.kernel.model import (
    ParsedKernelConfig,
    ParsedKernelConfigDeclaration,
    ParsedKernelConfigUnparsedLine,
    ParsedKernelImage,
)
from treeforge.android.extraction.cpio.extractor import (
    CpioExtractionResult,
    CpioNewcEntry,
)
from treeforge.android.parsing.ramdisk import (
    ParsedAndroidRamdisk,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
    ParsedAvbRegion,
    ParsedAvbVbmeta,
    ParsedBootImage,
    ParsedBootSignature,
    ParsedBootloaderChild,
    ParsedBootloaderChildDisposition,
)
from treeforge.android.parsing.sflb.model import (
    AndroidParsedSflbEntry,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)


def _encode_bytes(
    value: bytes,
) -> str:
    if not isinstance(
        value,
        bytes,
    ):
        raise TypeError(
            "value must be bytes"
        )

    return base64.b64encode(
        value
    ).decode(
        "ascii"
    )


def _decode_bytes(
    value: object,
    *,
    field_name: str,
) -> bytes:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string"
        )

    try:
        return base64.b64decode(
            value.encode(
                "ascii"
            ),
            validate=True,
        )
    except Exception as error:
        raise ValueError(
            f"{field_name} is not valid base64"
        ) from error


def _optional_ref(
    encoder: SnapshotGraphEncoder,
    value: object | None,
) -> dict[str, str] | None:
    if value is None:
        return None

    return encoder.ref(
        value
    )


def _decode_optional_ref(
    decoder: SnapshotGraphDecoder,
    value: object,
) -> object | None:
    if value is None:
        return None

    return decoder.ref(
        value
    )


def _strings(
    value: object,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError(
            f"{field_name} must be a list"
        )

    if not all(
        isinstance(
            item,
            str,
        )
        for item in value
    ):
        raise TypeError(
            f"{field_name} must contain only strings"
        )

    return tuple(
        value
    )


# ---------------------------------------------------------------------------
# Native-library configuration
# ---------------------------------------------------------------------------


class AndroidLinkerConfigurationSectionCodec:
    type_tag = "android.parsed.linker_configuration_section"
    python_type = AndroidLinkerConfigurationSection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidLinkerConfigurationSection,
        ):
            raise TypeError(
                "value must be an AndroidLinkerConfigurationSection"
            )

        return {
            "name": value.name,
            "raw": value.raw,
            "source_line": value.source_line,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidLinkerConfigurationSection(
            name=payload["name"],
            raw=payload["raw"],
            source_line=payload["source_line"],
        )


class AndroidLinkerConfigurationAssignmentCodec:
    type_tag = "android.parsed.linker_configuration_assignment"
    python_type = AndroidLinkerConfigurationAssignment

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidLinkerConfigurationAssignment,
        ):
            raise TypeError(
                "value must be an AndroidLinkerConfigurationAssignment"
            )

        return {
            "key": value.key,
            "operator": value.operator,
            "value": value.value,
            "raw": value.raw,
            "source_line": value.source_line,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidLinkerConfigurationAssignment(
            key=payload["key"],
            operator=payload["operator"],
            value=payload["value"],
            raw=payload["raw"],
            source_line=payload["source_line"],
        )


class AndroidLinkerConfigurationUnparsedLineCodec:
    type_tag = "android.parsed.linker_configuration_unparsed_line"
    python_type = AndroidLinkerConfigurationUnparsedLine

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidLinkerConfigurationUnparsedLine,
        ):
            raise TypeError(
                "value must be an AndroidLinkerConfigurationUnparsedLine"
            )

        return {
            "raw": value.raw,
            "content": value.content,
            "source_line": value.source_line,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidLinkerConfigurationUnparsedLine(
            raw=payload["raw"],
            content=payload["content"],
            source_line=payload["source_line"],
        )


class ParsedAndroidLinkerConfigurationCodec:
    type_tag = "android.parsed.linker_configuration"
    python_type = ParsedAndroidLinkerConfiguration

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidLinkerConfiguration,
        ):
            raise TypeError(
                "value must be a ParsedAndroidLinkerConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "raw": value.raw,
            "sections": [
                encoder.ref(
                    item
                )
                for item in value.sections
            ],
            "assignments": [
                encoder.ref(
                    item
                )
                for item in value.assignments
            ],
            "unparsed_lines": [
                encoder.ref(
                    item
                )
                for item in value.unparsed_lines
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored linker configuration source must be "
                "an AndroidModelSource"
            )

        return ParsedAndroidLinkerConfiguration(
            source=source,
            raw=payload["raw"],
            sections=tuple(
                decoder.ref(ref)
                for ref in payload.get(
                    "sections",
                    [],
                )
            ),
            assignments=tuple(
                decoder.ref(ref)
                for ref in payload.get(
                    "assignments",
                    [],
                )
            ),
            unparsed_lines=tuple(
                decoder.ref(ref)
                for ref in payload.get(
                    "unparsed_lines",
                    [],
                )
            ),
        )


class AndroidLinkerProtobufUnknownFieldCodec:
    type_tag = (
        "android.parsed.linker_protobuf_unknown_field"
    )
    python_type = AndroidLinkerProtobufUnknownField

    def encode(
        self,
        value,
        encoder,
    ):
        if not isinstance(
            value,
            AndroidLinkerProtobufUnknownField,
        ):
            raise TypeError(
                "value must be an "
                "AndroidLinkerProtobufUnknownField"
            )

        return {
            "field_number": value.field_number,
            "wire_type": value.wire_type,
            "raw_hex": value.raw.hex(),
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        return AndroidLinkerProtobufUnknownField(
            field_number=int(
                payload["field_number"]
            ),
            wire_type=int(
                payload["wire_type"]
            ),
            raw=bytes.fromhex(
                payload["raw_hex"]
            ),
        )


class AndroidLinkerProtobufContributionCodec:
    type_tag = (
        "android.parsed.linker_protobuf_contribution"
    )
    python_type = AndroidLinkerProtobufContribution

    def encode(
        self,
        value,
        encoder,
    ):
        if not isinstance(
            value,
            AndroidLinkerProtobufContribution,
        ):
            raise TypeError(
                "value must be an "
                "AndroidLinkerProtobufContribution"
            )

        return {
            "namespace": value.namespace,
            "paths": list(
                value.paths
            ),
            "unknown_fields": [
                encoder.ref(
                    item
                )
                for item
                in value.unknown_fields
            ],
            "raw_hex": value.raw.hex(),
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        return AndroidLinkerProtobufContribution(
            namespace=payload[
                "namespace"
            ],
            paths=tuple(
                payload.get(
                    "paths",
                    [],
                )
            ),
            unknown_fields=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "unknown_fields",
                    [],
                )
            ),
            raw=bytes.fromhex(
                payload.get(
                    "raw_hex",
                    "",
                )
            ),
        )


class ParsedAndroidLinkerProtobufConfigurationCodec:
    type_tag = (
        "android.parsed.linker_protobuf_configuration"
    )
    python_type = (
        ParsedAndroidLinkerProtobufConfiguration
    )

    def encode(
        self,
        value,
        encoder,
    ):
        if not isinstance(
            value,
            ParsedAndroidLinkerProtobufConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidLinkerProtobufConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "raw_hex": value.raw.hex(),
            "permitted_paths": list(
                value.permitted_paths
            ),
            "visible": value.visible,
            "visible_present": (
                value.visible_present
            ),
            "provide_libs": list(
                value.provide_libs
            ),
            "require_libs": list(
                value.require_libs
            ),
            "contributions": [
                encoder.ref(
                    item
                )
                for item
                in value.contributions
            ],
            "unknown_fields": [
                encoder.ref(
                    item
                )
                for item
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        source = decoder.ref(
            payload["source"]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "decoded linker protobuf source must "
                "be an AndroidModelSource"
            )

        return ParsedAndroidLinkerProtobufConfiguration(
            source=source,
            raw=bytes.fromhex(
                payload.get(
                    "raw_hex",
                    "",
                )
            ),
            permitted_paths=tuple(
                payload.get(
                    "permitted_paths",
                    [],
                )
            ),
            visible=bool(
                payload.get(
                    "visible",
                    False,
                )
            ),
            visible_present=bool(
                payload.get(
                    "visible_present",
                    False,
                )
            ),
            provide_libs=tuple(
                payload.get(
                    "provide_libs",
                    [],
                )
            ),
            require_libs=tuple(
                payload.get(
                    "require_libs",
                    [],
                )
            ),
            contributions=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "contributions",
                    [],
                )
            ),
            unknown_fields=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "unknown_fields",
                    [],
                )
            ),
        )


class AndroidNativeLibraryConfigurationDeclarationCodec:
    type_tag = (
        "android.parsed.native_library_configuration_declaration"
    )
    python_type = (
        AndroidNativeLibraryConfigurationDeclaration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidNativeLibraryConfigurationDeclaration,
        ):
            raise TypeError(
                "value must be an "
                "AndroidNativeLibraryConfigurationDeclaration"
            )

        return {
            "raw": value.raw,
            "content": value.content,
            "tokens": list(
                value.tokens
            ),
            "source_line": value.source_line,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return (
            AndroidNativeLibraryConfigurationDeclaration(
                raw=payload[
                    "raw"
                ],
                content=payload[
                    "content"
                ],
                tokens=_strings(
                    payload.get(
                        "tokens",
                        [],
                    ),
                    field_name="tokens",
                ),
                source_line=payload[
                    "source_line"
                ],
            )
        )


class ParsedAndroidNativeLibraryConfigurationCodec:
    type_tag = (
        "android.parsed.native_library_configuration"
    )
    python_type = (
        ParsedAndroidNativeLibraryConfiguration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidNativeLibraryConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidNativeLibraryConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "raw": value.raw,
            "declarations": [
                encoder.ref(
                    declaration
                )
                for declaration
                in value.declarations
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload[
                "source"
            ]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored native-library configuration source "
                "must be an AndroidModelSource"
            )

        return ParsedAndroidNativeLibraryConfiguration(
            source=source,
            raw=payload[
                "raw"
            ],
            declarations=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "declarations",
                    [],
                )
            ),
        )


# ---------------------------------------------------------------------------
# ELF
# ---------------------------------------------------------------------------


class ParsedAndroidElfSourceCodec:
    type_tag = "android.parsed.elf_source"
    python_type = ParsedAndroidElfSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidElfSource,
        ):
            raise TypeError(
                "value must be a ParsedAndroidElfSource"
            )

        return {
            "filesystem_source": _optional_ref(
                encoder,
                value.filesystem_source,
            ),
            "android_path": (
                str(
                    value.android_path
                )
                if value.android_path is not None
                else None
            ),
            "host_path": str(
                value.host_path
            ),
            "metadata_entry": _optional_ref(
                encoder,
                value.metadata_entry,
            ),
            "extraction_artifact": _optional_ref(
                encoder,
                value.extraction_artifact,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        filesystem_source = _decode_optional_ref(
            decoder,
            payload.get(
                "filesystem_source"
            ),
        )

        extraction_artifact = _decode_optional_ref(
            decoder,
            payload.get(
                "extraction_artifact"
            ),
        )

        metadata_entry = _decode_optional_ref(
            decoder,
            payload.get(
                "metadata_entry"
            ),
        )

        if (
            metadata_entry is not None
            and not isinstance(
                metadata_entry,
                FilesystemMetadataEntry,
            )
        ):
            raise TypeError(
                "restored ELF metadata_entry must be a "
                "FilesystemMetadataEntry or None"
            )

        if (
            filesystem_source is not None
            and not isinstance(
                filesystem_source,
                AndroidParserFilesystemSource,
            )
        ):
            raise TypeError(
                "restored ELF filesystem_source must be an "
                "AndroidParserFilesystemSource or None"
            )

        if (
            extraction_artifact is not None
            and not isinstance(
                extraction_artifact,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "restored ELF extraction_artifact must be an "
                "ExtractedArtifact or None"
            )

        android_path = payload.get(
            "android_path"
        )

        return ParsedAndroidElfSource(
            filesystem_source=filesystem_source,
            android_path=(
                PurePosixPath(
                    android_path
                )
                if android_path is not None
                else None
            ),
            host_path=Path(
                payload[
                    "host_path"
                ]
            ),
            metadata_entry=metadata_entry,
            extraction_artifact=extraction_artifact,
        )


class ParsedAndroidElfCodec:
    type_tag = "android.parsed.elf"
    python_type = ParsedAndroidElf

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "value must be a ParsedAndroidElf"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "elf_class": value.elf_class.value,
            "endianness": value.endianness.value,
            "machine": value.machine,
            "elf_type": value.elf_type,
            "soname": value.soname,
            "needed": list(
                value.needed
            ),
            "interpreter": value.interpreter,
            "soong_intermediate_components": list(
                value.soong_intermediate_components
            ),
            "e_flags": value.e_flags,
            "embedded_references": [
                {
                    "kind": reference.kind.value,
                    "section_index": (
                        reference.section_index
                    ),
                    "section_name": (
                        reference.section_name
                    ),
                    "section_byte_offset": (
                        reference.section_byte_offset
                    ),
                    "file_byte_offset": (
                        reference.file_byte_offset
                    ),
                    "value": reference.value,
                }
                for reference
                in value.embedded_references
            ],
            "comments": list(
                value.comments
            ),
            "note_sections": [
                {
                    "section_name": section.section_name,
                    "data": section.data.hex(),
                    "notes": [
                        {
                            "index": note.index,
                            "owner": note.owner,
                            "note_type": note.note_type,
                            "descriptor": note.descriptor,
                        }
                        for note in section.notes
                    ],
                }
                for section in value.note_sections
            ],
            "attribute_sections": [
                {
                    "section_name": section.section_name,
                    "data": section.data.hex(),
                    "attributes": [
                        {
                            "subsection_index": (
                                attribute.subsection_index
                            ),
                            "subsubsection_index": (
                                attribute.subsubsection_index
                            ),
                            "attribute_index": (
                                attribute.attribute_index
                            ),
                            "tag": attribute.tag,
                            "value": attribute.value,
                            "extra": attribute.extra,
                        }
                        for attribute in section.attributes
                    ],
                }
                for section in value.attribute_sections
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload[
                "source"
            ]
        )

        if not isinstance(
            source,
            ParsedAndroidElfSource,
        ):
            raise TypeError(
                "restored ELF source must be a ParsedAndroidElfSource"
            )

        return ParsedAndroidElf(
            source=source,
            elf_class=AndroidElfClass(
                payload[
                    "elf_class"
                ]
            ),
            endianness=AndroidElfEndianness(
                payload[
                    "endianness"
                ]
            ),
            machine=payload[
                "machine"
            ],
            elf_type=payload[
                "elf_type"
            ],
            soname=payload.get(
                "soname"
            ),
            needed=_strings(
                payload.get(
                    "needed",
                    [],
                ),
                field_name="needed",
            ),
            interpreter=payload.get(
                "interpreter"
            ),
            soong_intermediate_components=_strings(
                payload.get(
                    "soong_intermediate_components",
                    [],
                ),
                field_name="soong_intermediate_components",
            ),
            e_flags=int(
                payload.get(
                    "e_flags",
                    0,
                )
            ),
            embedded_references=tuple(
                ParsedAndroidElfEmbeddedReference(
                    kind=(
                        AndroidElfEmbeddedReferenceKind(
                            reference[
                                "kind"
                            ]
                        )
                    ),
                    section_index=int(
                        reference[
                            "section_index"
                        ]
                    ),
                    section_name=reference[
                        "section_name"
                    ],
                    section_byte_offset=int(
                        reference[
                            "section_byte_offset"
                        ]
                    ),
                    file_byte_offset=int(
                        reference[
                            "file_byte_offset"
                        ]
                    ),
                    value=reference[
                        "value"
                    ],
                )
                for reference
                in payload.get(
                    "embedded_references",
                    [],
                )
            ),
            comments=_strings(
                payload.get(
                    "comments",
                    [],
                ),
                field_name="comments",
            ),
            note_sections=tuple(
                ParsedAndroidElfNoteSection(
                    section_name=section[
                        "section_name"
                    ],
                    data=bytes.fromhex(
                        section.get(
                            "data",
                            "",
                        )
                    ),
                    notes=tuple(
                        ParsedAndroidElfNote(
                            index=int(
                                note[
                                    "index"
                                ]
                            ),
                            owner=note.get(
                                "owner",
                                "",
                            ),
                            note_type=note.get(
                                "note_type",
                                "",
                            ),
                            descriptor=note.get(
                                "descriptor",
                                "",
                            ),
                        )
                        for note
                        in section.get(
                            "notes",
                            [],
                        )
                    ),
                )
                for section
                in payload.get(
                    "note_sections",
                    [],
                )
            ),
            attribute_sections=tuple(
                ParsedAndroidElfAttributeSection(
                    section_name=section[
                        "section_name"
                    ],
                    data=bytes.fromhex(
                        section.get(
                            "data",
                            "",
                        )
                    ),
                    attributes=tuple(
                        ParsedAndroidElfAttribute(
                            subsection_index=int(
                                attribute[
                                    "subsection_index"
                                ]
                            ),
                            subsubsection_index=int(
                                attribute[
                                    "subsubsection_index"
                                ]
                            ),
                            attribute_index=int(
                                attribute[
                                    "attribute_index"
                                ]
                            ),
                            tag=attribute[
                                "tag"
                            ],
                            value=attribute.get(
                                "value",
                                "",
                            ),
                            extra=attribute.get(
                                "extra"
                            ),
                        )
                        for attribute
                        in section.get(
                            "attributes",
                            [],
                        )
                    ),
                )
                for section
                in payload.get(
                    "attribute_sections",
                    [],
                )
            ),
        )


class AndroidElfParsingResultCodec:
    type_tag = "android.elf_parsing_result"
    python_type = AndroidElfParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidElfParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidElfParsingResult"
            )

        return {
            "elf_files": [
                encoder.ref(
                    item
                )
                for item in value.elf_files
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidElfParsingResult(
            elf_files=tuple(
                decoder.ref(
                    ref
                )
                for ref in payload.get(
                    "elf_files",
                    [],
                )
            )
        )


# ---------------------------------------------------------------------------
# APEX / BMP / SFLB
# ---------------------------------------------------------------------------


class AndroidParsedApexCodec:
    type_tag = "android.parsed.apex"
    python_type = AndroidParsedApex

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParsedApex,
        ):
            raise TypeError(
                "value must be an AndroidParsedApex"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "apex_name": value.apex_name,
            "version": value.version,
            "provide_native_libs": list(
                value.provide_native_libs
            ),
            "require_native_libs": list(
                value.require_native_libs
            ),
            "jni_libs": list(
                value.jni_libs
            ),
            "require_shared_apex_libs": list(
                value.require_shared_apex_libs
            ),
            "provide_shared_apex_libs": (
                value.provide_shared_apex_libs
            ),
            "provide_shared_apex_libs_present": (
                value.provide_shared_apex_libs_present
            ),
            "supports_rebootless_update": (
                value.supports_rebootless_update
            ),
            "supports_rebootless_update_present": (
                value.supports_rebootless_update_present
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored APEX artifact must be an ExtractedArtifact"
            )

        provide_native_libs = tuple(
            payload.get(
                "provide_native_libs",
                [],
            )
        )

        require_native_libs = tuple(
            payload.get(
                "require_native_libs",
                [],
            )
        )

        jni_libs = tuple(
            payload.get(
                "jni_libs",
                [],
            )
        )

        require_shared_apex_libs = tuple(
            payload.get(
                "require_shared_apex_libs",
                [],
            )
        )

        provide_shared_apex_libs = payload.get(
            "provide_shared_apex_libs",
            False,
        )

        provide_shared_apex_libs_present = payload.get(
            "provide_shared_apex_libs_present",
            False,
        )

        supports_rebootless_update = payload.get(
            "supports_rebootless_update",
            False,
        )

        supports_rebootless_update_present = payload.get(
            "supports_rebootless_update_present",
            False,
        )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            for values in (
                provide_native_libs,
                require_native_libs,
                jni_libs,
                require_shared_apex_libs,
            )
            for value in values
        ):
            raise TypeError(
                "restored APEX native-library fields must contain only "
                "non-empty strings"
            )

        for field_name, value in (
            (
                "provide_shared_apex_libs",
                provide_shared_apex_libs,
            ),
            (
                "provide_shared_apex_libs_present",
                provide_shared_apex_libs_present,
            ),
            (
                "supports_rebootless_update",
                supports_rebootless_update,
            ),
            (
                "supports_rebootless_update_present",
                supports_rebootless_update_present,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"restored APEX {field_name} must be a bool"
                )

        return AndroidParsedApex(
            artifact=artifact,
            apex_name=payload[
                "apex_name"
            ],
            version=payload[
                "version"
            ],
            provide_native_libs=(
                provide_native_libs
            ),
            require_native_libs=(
                require_native_libs
            ),
            jni_libs=jni_libs,
            require_shared_apex_libs=(
                require_shared_apex_libs
            ),
            provide_shared_apex_libs=(
                provide_shared_apex_libs
            ),
            provide_shared_apex_libs_present=(
                provide_shared_apex_libs_present
            ),
            supports_rebootless_update=(
                supports_rebootless_update
            ),
            supports_rebootless_update_present=(
                supports_rebootless_update_present
            ),
        )


class ParsedApexContainerCodec:
    type_tag = "android.parsed.apex_container"
    python_type = ParsedApexContainer

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedApexContainer,
        ):
            raise TypeError(
                "value must be a ParsedApexContainer"
            )

        return {
            "outer_container": encoder.ref(
                value.outer_container
            ),
            "semantic_container": encoder.ref(
                value.semantic_container
            ),
            "payload_artifact": encoder.ref(
                value.payload_artifact
            ),
            "lineage_artifacts": [
                encoder.ref(
                    artifact
                )
                for artifact
                in value.lineage_artifacts
            ],
            "metadata": encoder.ref(
                value.metadata
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        outer_container = decoder.ref(
            payload[
                "outer_container"
            ]
        )

        semantic_container = decoder.ref(
            payload[
                "semantic_container"
            ]
        )

        payload_artifact = decoder.ref(
            payload[
                "payload_artifact"
            ]
        )

        lineage_artifacts = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload[
                "lineage_artifacts"
            ]
        )

        metadata = decoder.ref(
            payload[
                "metadata"
            ]
        )

        return ParsedApexContainer(
            outer_container=outer_container,
            semantic_container=semantic_container,
            payload_artifact=payload_artifact,
            lineage_artifacts=lineage_artifacts,
            metadata=metadata,
        )


class AndroidParsedBmpCodec:
    type_tag = "android.parsed.bmp"
    python_type = AndroidParsedBmp

    _FIELDS = (
        "file_size",
        "pixel_data_offset",
        "dib_header_size",
        "width",
        "height",
        "planes",
        "bits_per_pixel",
        "compression",
        "image_size",
        "horizontal_resolution",
        "vertical_resolution",
        "colors_used",
        "important_colors",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParsedBmp,
        ):
            raise TypeError(
                "value must be an AndroidParsedBmp"
            )

        payload = {
            "artifact": encoder.ref(
                value.artifact
            ),
        }

        for field_name in self._FIELDS:
            payload[
                field_name
            ] = getattr(
                value,
                field_name,
            )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored BMP artifact must be an ExtractedArtifact"
            )

        return AndroidParsedBmp(
            artifact=artifact,
            **{
                field_name: payload[
                    field_name
                ]
                for field_name in self._FIELDS
            },
        )


class AndroidParsedSflbEntryCodec:
    type_tag = "android.parsed.sflb_entry"
    python_type = AndroidParsedSflbEntry

    _INTEGER_FIELDS = (
        "container_index",
        "container_offset_bytes",
        "container_span_bytes",
        "version",
        "entry_count",
        "secondary_count",
        "entry_index",
        "record_offset_bytes",
        "payload_offset_bytes",
        "absolute_payload_offset_bytes",
        "payload_size_bytes",
        "opaque_word",
        "flags",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParsedSflbEntry,
        ):
            raise TypeError(
                "value must be an AndroidParsedSflbEntry"
            )

        payload: dict[str, Any] = {
            "artifact": encoder.ref(
                value.artifact
            ),
            "entry_name": value.entry_name,
            "raw_header_tail": list(
                value.raw_header_tail
            ),
            "raw_payload": _encode_bytes(
                value.raw_payload
            ),
        }

        for field_name in self._INTEGER_FIELDS:
            payload[
                field_name
            ] = getattr(
                value,
                field_name,
            )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored SFLB artifact must be an ExtractedArtifact"
            )

        raw_header_tail = payload[
            "raw_header_tail"
        ]

        if (
            not isinstance(
                raw_header_tail,
                list,
            )
            or len(
                raw_header_tail
            ) != 3
        ):
            raise ValueError(
                "raw_header_tail must contain three values"
            )

        return AndroidParsedSflbEntry(
            artifact=artifact,
            entry_name=payload[
                "entry_name"
            ],
            raw_header_tail=tuple(
                raw_header_tail
            ),
            raw_payload=_decode_bytes(
                payload[
                    "raw_payload"
                ],
                field_name="raw_payload",
            ),
            **{
                field_name: payload[
                    field_name
                ]
                for field_name
                in self._INTEGER_FIELDS
            },
        )


# ---------------------------------------------------------------------------
# FDT / DTBO
# ---------------------------------------------------------------------------


class ParsedFdtPropertyCodec:
    type_tag = "android.parsed.fdt_property"
    python_type = ParsedFdtProperty

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedFdtProperty,
        ):
            raise TypeError(
                "value must be a ParsedFdtProperty"
            )

        return {
            "name": value.name,
            "value": _encode_bytes(
                value.value
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedFdtProperty(
            name=payload[
                "name"
            ],
            value=_decode_bytes(
                payload[
                    "value"
                ],
                field_name="value",
            ),
        )


class ParsedFdtNodeCodec:
    type_tag = "android.parsed.fdt_node"
    python_type = ParsedFdtNode

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedFdtNode,
        ):
            raise TypeError(
                "value must be a ParsedFdtNode"
            )

        return {
            "name": value.name,
            "properties": [
                encoder.ref(
                    item
                )
                for item in value.properties
            ],
            "children": [
                encoder.ref(
                    item
                )
                for item in value.children
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        properties = tuple(
            decoder.ref(
                ref
            )
            for ref in payload.get(
                "properties",
                [],
            )
        )

        children = tuple(
            decoder.ref(
                ref
            )
            for ref in payload.get(
                "children",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                ParsedFdtProperty,
            )
            for value in properties
        ):
            raise TypeError(
                "restored FDT properties contain an invalid value"
            )

        if not all(
            isinstance(
                value,
                ParsedFdtNode,
            )
            for value in children
        ):
            raise TypeError(
                "restored FDT children contain an invalid value"
            )

        return ParsedFdtNode(
            name=payload[
                "name"
            ],
            properties=properties,
            children=children,
        )


def _header_to_dict(
    value: ParsedFdtHeader,
) -> dict[str, int]:
    return {
        field_name: getattr(
            value,
            field_name,
        )
        for field_name in (
            "magic",
            "totalsize",
            "off_dt_struct",
            "off_dt_strings",
            "off_mem_rsvmap",
            "version",
            "last_comp_version",
            "boot_cpuid_phys",
            "size_dt_strings",
            "size_dt_struct",
        )
    }


def _header_from_dict(
    payload: object,
) -> ParsedFdtHeader:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "FDT header payload must be a dict"
        )

    return ParsedFdtHeader(
        **{
            field_name: payload[
                field_name
            ]
            for field_name in (
                "magic",
                "totalsize",
                "off_dt_struct",
                "off_dt_strings",
                "off_mem_rsvmap",
                "version",
                "last_comp_version",
                "boot_cpuid_phys",
                "size_dt_strings",
                "size_dt_struct",
            )
        }
    )


class ParsedFdtCodec:
    type_tag = "android.parsed.fdt"
    python_type = ParsedFdt

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedFdt,
        ):
            raise TypeError(
                "value must be a ParsedFdt"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "header": _header_to_dict(
                value.header
            ),
            "reservations": [
                {
                    "address": item.address,
                    "size": item.size,
                }
                for item in value.reservations
            ],
            "root": encoder.ref(
                value.root
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )
        root = decoder.ref(
            payload[
                "root"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored FDT artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            root,
            ParsedFdtNode,
        ):
            raise TypeError(
                "restored FDT root must be a ParsedFdtNode"
            )

        return ParsedFdt(
            artifact=artifact,
            header=_header_from_dict(
                payload[
                    "header"
                ]
            ),
            reservations=tuple(
                ParsedFdtReservation(
                    address=item[
                        "address"
                    ],
                    size=item[
                        "size"
                    ],
                )
                for item in payload.get(
                    "reservations",
                    [],
                )
            ),
            root=root,
        )


class ParsedDtboOverlayMetadataCodec:
    type_tag = "android.parsed.dtbo_overlay"
    python_type = ParsedDtboOverlayMetadata

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedDtboOverlayMetadata,
        ):
            raise TypeError(
                "value must be a ParsedDtboOverlayMetadata"
            )

        return {
            "fdt": encoder.ref(
                value.fdt
            ),
            "external_fixups": [
                {
                    "source": encoder.ref(
                        item.source
                    ),
                    "symbol": item.symbol,
                    "locations": [
                        {
                            "node_path": location.node_path,
                            "property_name": location.property_name,
                            "byte_offset": location.byte_offset,
                        }
                        for location in item.locations
                    ],
                }
                for item in value.external_fixups
            ],
            "local_fixups": [
                {
                    "source": encoder.ref(
                        item.source
                    ),
                    "node_path": item.node_path,
                    "property_name": item.property_name,
                    "byte_offsets": list(
                        item.byte_offsets
                    ),
                }
                for item in value.local_fixups
            ],
            "symbols": [
                {
                    "source": encoder.ref(
                        item.source
                    ),
                    "symbol": item.symbol,
                    "node_path": item.node_path,
                }
                for item in value.symbols
            ],
            "fragment_targets": [
                {
                    "fragment": encoder.ref(
                        item.fragment
                    ),
                    "fragment_path": item.fragment_path,
                    "target_property": encoder.ref(
                        item.target_property
                    ),
                    "target_phandle": item.target_phandle,
                    "target_path": item.target_path,
                }
                for item in value.fragment_targets
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        fdt = decoder.ref(
            payload[
                "fdt"
            ]
        )

        if not isinstance(
            fdt,
            ParsedFdt,
        ):
            raise TypeError(
                "restored DTBO overlay fdt must be a ParsedFdt"
            )

        external_fixups = []

        for item in payload.get(
            "external_fixups",
            [],
        ):
            source = decoder.ref(
                item[
                    "source"
                ]
            )

            if not isinstance(
                source,
                ParsedFdtProperty,
            ):
                raise TypeError(
                    "restored external-fixup source must be "
                    "a ParsedFdtProperty"
                )

            external_fixups.append(
                ParsedDtboExternalFixup(
                    source=source,
                    symbol=item[
                        "symbol"
                    ],
                    locations=tuple(
                        ParsedDtboExternalFixupLocation(
                            node_path=location[
                                "node_path"
                            ],
                            property_name=location[
                                "property_name"
                            ],
                            byte_offset=location[
                                "byte_offset"
                            ],
                        )
                        for location
                        in item.get(
                            "locations",
                            [],
                        )
                    ),
                )
            )

        local_fixups = []

        for item in payload.get(
            "local_fixups",
            [],
        ):
            source = decoder.ref(
                item[
                    "source"
                ]
            )

            if not isinstance(
                source,
                ParsedFdtProperty,
            ):
                raise TypeError(
                    "restored local-fixup source must be "
                    "a ParsedFdtProperty"
                )

            local_fixups.append(
                ParsedDtboLocalFixup(
                    source=source,
                    node_path=item[
                        "node_path"
                    ],
                    property_name=item[
                        "property_name"
                    ],
                    byte_offsets=tuple(
                        item.get(
                            "byte_offsets",
                            [],
                        )
                    ),
                )
            )

        symbols = []

        for item in payload.get(
            "symbols",
            [],
        ):
            source = decoder.ref(
                item[
                    "source"
                ]
            )

            if not isinstance(
                source,
                ParsedFdtProperty,
            ):
                raise TypeError(
                    "restored symbol source must be "
                    "a ParsedFdtProperty"
                )

            symbols.append(
                ParsedDtboSymbol(
                    source=source,
                    symbol=item[
                        "symbol"
                    ],
                    node_path=item[
                        "node_path"
                    ],
                )
            )

        fragment_targets = []

        for item in payload.get(
            "fragment_targets",
            [],
        ):
            fragment = decoder.ref(
                item[
                    "fragment"
                ]
            )
            target_property = decoder.ref(
                item[
                    "target_property"
                ]
            )

            if not isinstance(
                fragment,
                ParsedFdtNode,
            ):
                raise TypeError(
                    "restored fragment target must reference "
                    "a ParsedFdtNode"
                )

            if not isinstance(
                target_property,
                ParsedFdtProperty,
            ):
                raise TypeError(
                    "restored fragment target property must be "
                    "a ParsedFdtProperty"
                )

            fragment_targets.append(
                ParsedDtboFragmentTarget(
                    fragment=fragment,
                    fragment_path=item[
                        "fragment_path"
                    ],
                    target_property=target_property,
                    target_phandle=item.get(
                        "target_phandle"
                    ),
                    target_path=item.get(
                        "target_path"
                    ),
                )
            )

        return ParsedDtboOverlayMetadata(
            fdt=fdt,
            external_fixups=tuple(
                external_fixups
            ),
            local_fixups=tuple(
                local_fixups
            ),
            symbols=tuple(
                symbols
            ),
            fragment_targets=tuple(
                fragment_targets
            ),
        )


class AndroidParsedDtboEntryCodec:
    type_tag = "android.parsed.dtbo_entry"
    python_type = AndroidParsedDtboEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParsedDtboEntry,
        ):
            raise TypeError(
                "value must be an AndroidParsedDtboEntry"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "fdt": encoder.ref(
                value.fdt
            ),
            "overlay": encoder.ref(
                value.overlay
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )
        fdt = decoder.ref(
            payload[
                "fdt"
            ]
        )
        overlay = decoder.ref(
            payload[
                "overlay"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored DTBO artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            fdt,
            ParsedFdt,
        ):
            raise TypeError(
                "restored DTBO fdt must be a ParsedFdt"
            )

        if not isinstance(
            overlay,
            ParsedDtboOverlayMetadata,
        ):
            raise TypeError(
                "restored DTBO overlay must be "
                "a ParsedDtboOverlayMetadata"
            )

        return AndroidParsedDtboEntry(
            artifact=artifact,
            fdt=fdt,
            overlay=overlay,
        )


# ---------------------------------------------------------------------------
# AVB / VBMeta
# ---------------------------------------------------------------------------


def _avb_descriptor_to_dict(
    value: object,
) -> dict[str, Any]:
    common = {
        "tag": value.tag,
        "num_bytes_following": value.num_bytes_following,
    }

    if isinstance(
        value,
        AndroidParsedAvbPropertyDescriptor,
    ):
        return {
            **common,
            "type": "property",
            "key": value.key,
            "value": value.value,
        }

    if isinstance(
        value,
        AndroidParsedAvbHashtreeDescriptor,
    ):
        return {
            **common,
            "type": "hashtree",
            "dm_verity_version": value.dm_verity_version,
            "image_size": value.image_size,
            "tree_offset": value.tree_offset,
            "tree_size": value.tree_size,
            "data_block_size": value.data_block_size,
            "hash_block_size": value.hash_block_size,
            "fec_num_roots": value.fec_num_roots,
            "fec_offset": value.fec_offset,
            "fec_size": value.fec_size,
            "hash_algorithm": value.hash_algorithm,
            "partition_name": value.partition_name,
            "salt": _encode_bytes(
                value.salt
            ),
            "root_digest": _encode_bytes(
                value.root_digest
            ),
            "flags": value.flags,
        }

    if isinstance(
        value,
        AndroidParsedAvbHashDescriptor,
    ):
        return {
            **common,
            "type": "hash",
            "image_size": value.image_size,
            "hash_algorithm": value.hash_algorithm,
            "partition_name": value.partition_name,
            "salt": _encode_bytes(
                value.salt
            ),
            "digest": _encode_bytes(
                value.digest
            ),
            "flags": value.flags,
        }

    if isinstance(
        value,
        AndroidParsedAvbKernelCmdlineDescriptor,
    ):
        return {
            **common,
            "type": "kernel_cmdline",
            "flags": value.flags,
            "kernel_cmdline": value.kernel_cmdline,
        }

    if isinstance(
        value,
        AndroidParsedAvbChainPartitionDescriptor,
    ):
        return {
            **common,
            "type": "chain_partition",
            "rollback_index_location": (
                value.rollback_index_location
            ),
            "partition_name": value.partition_name,
            "public_key": _encode_bytes(
                value.public_key
            ),
            "flags": value.flags,
        }

    if isinstance(
        value,
        AndroidParsedAvbDescriptor,
    ):
        return {
            **common,
            "type": "unknown",
            "raw_payload": _encode_bytes(
                value.raw_payload
            ),
        }

    raise TypeError(
        "unsupported AVB descriptor type"
    )


def _avb_descriptor_from_dict(
    payload: object,
) -> object:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "AVB descriptor payload must be a dict"
        )

    common = {
        "tag": payload[
            "tag"
        ],
        "num_bytes_following": payload[
            "num_bytes_following"
        ],
    }

    kind = payload[
        "type"
    ]

    if kind == "property":
        return AndroidParsedAvbPropertyDescriptor(
            **common,
            key=payload[
                "key"
            ],
            value=payload[
                "value"
            ],
        )

    if kind == "hashtree":
        return AndroidParsedAvbHashtreeDescriptor(
            **common,
            dm_verity_version=payload[
                "dm_verity_version"
            ],
            image_size=payload[
                "image_size"
            ],
            tree_offset=payload[
                "tree_offset"
            ],
            tree_size=payload[
                "tree_size"
            ],
            data_block_size=payload[
                "data_block_size"
            ],
            hash_block_size=payload[
                "hash_block_size"
            ],
            fec_num_roots=payload[
                "fec_num_roots"
            ],
            fec_offset=payload[
                "fec_offset"
            ],
            fec_size=payload[
                "fec_size"
            ],
            hash_algorithm=payload[
                "hash_algorithm"
            ],
            partition_name=payload[
                "partition_name"
            ],
            salt=_decode_bytes(
                payload[
                    "salt"
                ],
                field_name="salt",
            ),
            root_digest=_decode_bytes(
                payload[
                    "root_digest"
                ],
                field_name="root_digest",
            ),
            flags=payload[
                "flags"
            ],
        )

    if kind == "hash":
        return AndroidParsedAvbHashDescriptor(
            **common,
            image_size=payload[
                "image_size"
            ],
            hash_algorithm=payload[
                "hash_algorithm"
            ],
            partition_name=payload[
                "partition_name"
            ],
            salt=_decode_bytes(
                payload[
                    "salt"
                ],
                field_name="salt",
            ),
            digest=_decode_bytes(
                payload[
                    "digest"
                ],
                field_name="digest",
            ),
            flags=payload[
                "flags"
            ],
        )

    if kind == "kernel_cmdline":
        return AndroidParsedAvbKernelCmdlineDescriptor(
            **common,
            flags=payload[
                "flags"
            ],
            kernel_cmdline=payload[
                "kernel_cmdline"
            ],
        )

    if kind == "chain_partition":
        return AndroidParsedAvbChainPartitionDescriptor(
            **common,
            rollback_index_location=payload[
                "rollback_index_location"
            ],
            partition_name=payload[
                "partition_name"
            ],
            public_key=_decode_bytes(
                payload[
                    "public_key"
                ],
                field_name="public_key",
            ),
            flags=payload[
                "flags"
            ],
        )

    if kind == "unknown":
        return AndroidParsedAvbDescriptor(
            **common,
            raw_payload=_decode_bytes(
                payload[
                    "raw_payload"
                ],
                field_name="raw_payload",
            ),
        )

    raise ValueError(
        f"unknown AVB descriptor type: {kind}"
    )


def _vbmeta_to_dict(
    value: AndroidParsedVbmeta,
) -> dict[str, Any]:
    fields = (
        "required_libavb_version_major",
        "required_libavb_version_minor",
        "authentication_data_block_size",
        "auxiliary_data_block_size",
        "algorithm_type",
        "hash_offset",
        "hash_size",
        "signature_offset",
        "signature_size",
        "public_key_offset",
        "public_key_size",
        "public_key_metadata_offset",
        "public_key_metadata_size",
        "descriptors_offset",
        "descriptors_size",
        "rollback_index",
        "flags",
        "rollback_index_location",
        "release_string",
    )

    return {
        **{
            field_name: getattr(
                value,
                field_name,
            )
            for field_name in fields
        },
        "hash": _encode_bytes(
            value.hash
        ),
        "signature": _encode_bytes(
            value.signature
        ),
        "public_key": _encode_bytes(
            value.public_key
        ),
        "public_key_metadata": _encode_bytes(
            value.public_key_metadata
        ),
        "descriptors": [
            _avb_descriptor_to_dict(
                descriptor
            )
            for descriptor in value.descriptors
        ],
    }


def _vbmeta_from_dict(
    payload: object,
) -> AndroidParsedVbmeta:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "VBMeta payload must be a dict"
        )

    fields = (
        "required_libavb_version_major",
        "required_libavb_version_minor",
        "authentication_data_block_size",
        "auxiliary_data_block_size",
        "algorithm_type",
        "hash_offset",
        "hash_size",
        "signature_offset",
        "signature_size",
        "public_key_offset",
        "public_key_size",
        "public_key_metadata_offset",
        "public_key_metadata_size",
        "descriptors_offset",
        "descriptors_size",
        "rollback_index",
        "flags",
        "rollback_index_location",
        "release_string",
    )

    hash_bytes = _decode_bytes(
        payload[
            "hash"
        ],
        field_name="VBMeta hash",
    )

    signature_bytes = _decode_bytes(
        payload[
            "signature"
        ],
        field_name="VBMeta signature",
    )

    public_key_bytes = _decode_bytes(
        payload[
            "public_key"
        ],
        field_name="VBMeta public_key",
    )

    public_key_metadata_bytes = _decode_bytes(
        payload[
            "public_key_metadata"
        ],
        field_name=(
            "VBMeta public_key_metadata"
        ),
    )

    expected_sizes = (
        (
            "hash",
            hash_bytes,
            payload[
                "hash_size"
            ],
        ),
        (
            "signature",
            signature_bytes,
            payload[
                "signature_size"
            ],
        ),
        (
            "public_key",
            public_key_bytes,
            payload[
                "public_key_size"
            ],
        ),
        (
            "public_key_metadata",
            public_key_metadata_bytes,
            payload[
                "public_key_metadata_size"
            ],
        ),
    )

    for (
        field_name,
        decoded,
        expected_size,
    ) in expected_sizes:
        if not isinstance(
            expected_size,
            int,
        ):
            raise TypeError(
                f"VBMeta {field_name}_size must be an int"
            )

        if len(decoded) != expected_size:
            raise ValueError(
                f"VBMeta {field_name} byte length "
                f"{len(decoded)} does not match "
                f"declared size {expected_size}"
            )

    return AndroidParsedVbmeta(
        **{
            field_name: payload[
                field_name
            ]
            for field_name in fields
        },
        hash=hash_bytes,
        signature=signature_bytes,
        public_key=public_key_bytes,
        public_key_metadata=(
            public_key_metadata_bytes
        ),
        descriptors=tuple(
            _avb_descriptor_from_dict(
                item
            )
            for item in payload.get(
                "descriptors",
                [],
            )
        ),
    )


def _avb_footer_to_dict(
    value: AndroidParsedAvbFooter | None,
) -> dict[str, Any] | None:
    if value is None:
        return None

    if not isinstance(
        value,
        AndroidParsedAvbFooter,
    ):
        raise TypeError(
            "AVB footer must be an AndroidParsedAvbFooter or None"
        )

    return {
        "version_major": value.version_major,
        "version_minor": value.version_minor,
        "original_image_size": (
            value.original_image_size
        ),
        "vbmeta_offset": value.vbmeta_offset,
        "vbmeta_size": value.vbmeta_size,
    }


def _avb_footer_from_dict(
    payload: object,
) -> AndroidParsedAvbFooter | None:
    if payload is None:
        return None

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "AVB footer payload must be a dict or None"
        )

    return AndroidParsedAvbFooter(
        version_major=payload[
            "version_major"
        ],
        version_minor=payload[
            "version_minor"
        ],
        original_image_size=payload[
            "original_image_size"
        ],
        vbmeta_offset=payload[
            "vbmeta_offset"
        ],
        vbmeta_size=payload[
            "vbmeta_size"
        ],
    )


class ParsedAvbVbmetaCodec:
    type_tag = "android.parsed.avb_vbmeta"
    python_type = ParsedAvbVbmeta

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAvbVbmeta,
        ):
            raise TypeError(
                "value must be a ParsedAvbVbmeta"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "container_artifact": encoder.ref(
                value.container_artifact
            ),
            "metadata": _vbmeta_to_dict(
                value.metadata
            ),
            "partition": _optional_ref(
                encoder,
                value.partition,
            ),
            "footer_artifact": _optional_ref(
                encoder,
                value.footer_artifact,
            ),
            "footer": (
                None
                if value.footer is None
                else _avb_footer_to_dict(
                    value.footer
                )
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload["artifact"]
        )

        container_artifact = decoder.ref(
            payload["container_artifact"]
        )

        partition = _decode_optional_ref(
            decoder,
            payload["partition"],
        )

        footer_artifact = _decode_optional_ref(
            decoder,
            payload["footer_artifact"],
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored AVB VBMeta artifact must be "
                "an ExtractedArtifact"
            )

        if not isinstance(
            container_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored AVB VBMeta container artifact must "
                "be an ExtractedArtifact"
            )

        if (
            partition is not None
            and not isinstance(
                partition,
                InventoryPartition,
            )
        ):
            raise TypeError(
                "restored AVB VBMeta partition must be "
                "an InventoryPartition or None"
            )

        if (
            footer_artifact is not None
            and not isinstance(
                footer_artifact,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "restored AVB footer artifact must be "
                "an ExtractedArtifact or None"
            )

        footer_payload = payload["footer"]

        footer = (
            None
            if footer_payload is None
            else _avb_footer_from_dict(
                footer_payload
            )
        )

        return ParsedAvbVbmeta(
            artifact=artifact,
            container_artifact=container_artifact,
            metadata=_vbmeta_from_dict(
                payload["metadata"]
            ),
            partition=partition,
            footer_artifact=footer_artifact,
            footer=footer,
        )


class ParsedAvbRegionCodec:
    type_tag = "android.parsed.avb_region"
    python_type = ParsedAvbRegion

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAvbRegion,
        ):
            raise TypeError(
                "value must be a ParsedAvbRegion"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "disposition": value.disposition,
            "vbmeta": _optional_ref(
                encoder,
                value.vbmeta,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload["artifact"]
        )

        vbmeta = _decode_optional_ref(
            decoder,
            payload["vbmeta"],
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored AVB region artifact must be "
                "an ExtractedArtifact"
            )

        if (
            vbmeta is not None
            and not isinstance(
                vbmeta,
                ParsedAvbVbmeta,
            )
        ):
            raise TypeError(
                "restored AVB region VBMeta must be "
                "a ParsedAvbVbmeta or None"
            )

        return ParsedAvbRegion(
            artifact=artifact,
            disposition=payload[
                "disposition"
            ],
            vbmeta=vbmeta,
        )


# ---------------------------------------------------------------------------
# Bootloader children
# ---------------------------------------------------------------------------


def _fbpt_entry_to_dict(
    value: AndroidParsedFbptEntry,
) -> dict[str, Any]:
    return {
        "index": value.index,
        "size_bytes": value.size_bytes,
        "reserved_prefix": value.reserved_prefix,
        "name": value.name,
        "type_identifier": value.type_identifier,
        "instance_identifier": value.instance_identifier,
        "reserved_tail": _encode_bytes(
            value.reserved_tail
        ),
        "raw_record": _encode_bytes(
            value.raw_record
        ),
    }


def _fbpt_entry_from_dict(
    payload: dict[str, Any],
) -> AndroidParsedFbptEntry:
    return AndroidParsedFbptEntry(
        index=payload[
            "index"
        ],
        size_bytes=payload[
            "size_bytes"
        ],
        reserved_prefix=payload[
            "reserved_prefix"
        ],
        name=payload[
            "name"
        ],
        type_identifier=payload[
            "type_identifier"
        ],
        instance_identifier=payload[
            "instance_identifier"
        ],
        reserved_tail=_decode_bytes(
            payload[
                "reserved_tail"
            ],
            field_name="reserved_tail",
        ),
        raw_record=_decode_bytes(
            payload[
                "raw_record"
            ],
            field_name="raw_record",
        ),
    )


def _bootloader_child_to_dict(
    value: object,
) -> dict[str, Any]:
    if isinstance(
        value,
        AndroidParsedFbpt,
    ):
        return {
            "type": "fbpt",
            "version": value.version,
            "table_index": value.table_index,
            "reserved_header_value": value.reserved_header_value,
            "entry_count": value.entry_count,
            "table_identifier": value.table_identifier,
            "entries": [
                _fbpt_entry_to_dict(
                    entry
                )
                for entry in value.entries
            ],
            "raw_header": _encode_bytes(
                value.raw_header
            ),
        }

    if isinstance(
        value,
        AndroidParsedUfsDescriptor,
    ):
        return {
            "type": "ufs_descriptor",
            "kind": value.kind.value,
            "version": value.version,
            "raw_payload": _encode_bytes(
                value.raw_payload
            ),
        }

    if isinstance(
        value,
        AndroidParsedUfpk,
    ):
        return {
            "type": "ufpk",
            "version": value.version,
            "package_name": value.package_name,
            "header_value_0x4c": value.header_value_0x4c,
            "declared_size": value.declared_size,
            "header_value_0x54": value.header_value_0x54,
            "device_identifier": value.device_identifier,
            "controller_identifier": value.controller_identifier,
            "firmware_identifier": value.firmware_identifier,
            "raw_header": _encode_bytes(
                value.raw_header
            ),
            "raw_payload": _encode_bytes(
                value.raw_payload
            ),
        }

    if isinstance(
        value,
        AndroidParsedUfpkDescriptor,
    ):
        return {
            "type": "ufpk_descriptor",
            "descriptor_kind": value.descriptor_kind,
            "identity": value.identity,
            "field_28": value.field_28,
            "next_offset": value.next_offset,
            "raw_header": _encode_bytes(
                value.raw_header
            ),
        }

    if isinstance(
        value,
        AndroidParsedBootFirmwarePayload,
    ):
        return {
            "type": "boot_firmware_payload",
            "firmware_identity": value.firmware_identity,
            "first_u32_le": value.first_u32_le,
            "arm64_ret_count": value.arm64_ret_count,
            "arm64_nop_count": value.arm64_nop_count,
            "printable_ascii_string_count": (
                value.printable_ascii_string_count
            ),
            "trailing_zero_bytes": value.trailing_zero_bytes,
            "entropy_bits_per_byte": value.entropy_bits_per_byte,
        }

    raise TypeError(
        "unsupported bootloader child Parsing value"
    )


def _bootloader_child_from_dict(
    payload: object,
) -> object:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "bootloader child payload must be a dict"
        )

    kind = payload[
        "type"
    ]

    if kind == "fbpt":
        return AndroidParsedFbpt(
            version=payload[
                "version"
            ],
            table_index=payload[
                "table_index"
            ],
            reserved_header_value=payload[
                "reserved_header_value"
            ],
            entry_count=payload[
                "entry_count"
            ],
            table_identifier=payload[
                "table_identifier"
            ],
            entries=tuple(
                _fbpt_entry_from_dict(
                    entry
                )
                for entry in payload.get(
                    "entries",
                    [],
                )
            ),
            raw_header=_decode_bytes(
                payload[
                    "raw_header"
                ],
                field_name="raw_header",
            ),
        )

    if kind == "ufs_descriptor":
        return AndroidParsedUfsDescriptor(
            kind=AndroidParsedUfsDescriptorKind(
                payload[
                    "kind"
                ]
            ),
            version=payload[
                "version"
            ],
            raw_payload=_decode_bytes(
                payload[
                    "raw_payload"
                ],
                field_name="raw_payload",
            ),
        )

    if kind == "ufpk":
        return AndroidParsedUfpk(
            version=payload[
                "version"
            ],
            package_name=payload[
                "package_name"
            ],
            header_value_0x4c=payload[
                "header_value_0x4c"
            ],
            declared_size=payload[
                "declared_size"
            ],
            header_value_0x54=payload[
                "header_value_0x54"
            ],
            device_identifier=payload[
                "device_identifier"
            ],
            controller_identifier=payload[
                "controller_identifier"
            ],
            firmware_identifier=payload[
                "firmware_identifier"
            ],
            raw_header=_decode_bytes(
                payload[
                    "raw_header"
                ],
                field_name="raw_header",
            ),
            raw_payload=_decode_bytes(
                payload[
                    "raw_payload"
                ],
                field_name="raw_payload",
            ),
        )

    if kind == "ufpk_descriptor":
        return AndroidParsedUfpkDescriptor(
            descriptor_kind=payload[
                "descriptor_kind"
            ],
            identity=payload[
                "identity"
            ],
            field_28=payload[
                "field_28"
            ],
            next_offset=payload[
                "next_offset"
            ],
            raw_header=_decode_bytes(
                payload[
                    "raw_header"
                ],
                field_name="raw_header",
            ),
        )

    if kind == "boot_firmware_payload":
        return AndroidParsedBootFirmwarePayload(
            firmware_identity=payload[
                "firmware_identity"
            ],
            first_u32_le=payload.get(
                "first_u32_le"
            ),
            arm64_ret_count=payload[
                "arm64_ret_count"
            ],
            arm64_nop_count=payload[
                "arm64_nop_count"
            ],
            printable_ascii_string_count=payload[
                "printable_ascii_string_count"
            ],
            trailing_zero_bytes=payload[
                "trailing_zero_bytes"
            ],
            entropy_bits_per_byte=payload[
                "entropy_bits_per_byte"
            ],
        )

    raise ValueError(
        f"unknown bootloader child type: {kind}"
    )


class ParsedBootloaderChildCodec:
    type_tag = "android.parsed.bootloader_child"
    python_type = ParsedBootloaderChild

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedBootloaderChild,
        ):
            raise TypeError(
                "value must be a ParsedBootloaderChild"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "parsed": _bootloader_child_to_dict(
                value.parsed
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored bootloader artifact must be "
                "an ExtractedArtifact"
            )

        return ParsedBootloaderChild(
            artifact=artifact,
            parsed=_bootloader_child_from_dict(
                payload[
                    "parsed"
                ]
            ),
        )


class ParsedBootloaderChildDispositionCodec:
    type_tag = "android.parsed.bootloader_child_disposition"
    python_type = ParsedBootloaderChildDisposition

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedBootloaderChildDisposition,
        ):
            raise TypeError(
                "value must be a "
                "ParsedBootloaderChildDisposition"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "disposition": value.disposition,
            "parsed": _optional_ref(
                encoder,
                value.parsed,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload["artifact"]
        )

        parsed = _decode_optional_ref(
            decoder,
            payload["parsed"],
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored bootloader disposition artifact "
                "must be an ExtractedArtifact"
            )

        if (
            parsed is not None
            and not isinstance(
                parsed,
                ParsedBootloaderChild,
            )
        ):
            raise TypeError(
                "restored bootloader disposition parsed value "
                "must be a ParsedBootloaderChild or None"
            )

        return ParsedBootloaderChildDisposition(
            artifact=artifact,
            disposition=payload[
                "disposition"
            ],
            parsed=parsed,
        )


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------


def _kernel_config_to_dict(
    value: ParsedKernelConfig | None,
) -> dict[str, Any] | None:
    if value is None:
        return None

    return {
        "compression": value.compression.value,
        "marker_start_offset": value.marker_start_offset,
        "payload_start_offset": value.payload_start_offset,
        "marker_end_offset": value.marker_end_offset,
        "declarations": [
            {
                "key": item.key,
                "value": item.value,
                "enabled": item.enabled,
                "line_number": item.line_number,
                "raw": item.raw,
            }
            for item in value.declarations
        ],
        "unparsed_lines": [
            {
                "line_number": item.line_number,
                "raw": item.raw,
                "reason": item.reason,
            }
            for item in value.unparsed_lines
        ],
    }


def _kernel_config_from_dict(
    payload: object,
) -> ParsedKernelConfig | None:
    if payload is None:
        return None

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "kernel config payload must be a dict or None"
        )

    return ParsedKernelConfig(
        compression=CompressionFormat(
            payload[
                "compression"
            ]
        ),
        marker_start_offset=payload[
            "marker_start_offset"
        ],
        payload_start_offset=payload[
            "payload_start_offset"
        ],
        marker_end_offset=payload[
            "marker_end_offset"
        ],
        declarations=tuple(
            ParsedKernelConfigDeclaration(
                key=item[
                    "key"
                ],
                value=item.get(
                    "value"
                ),
                enabled=item.get(
                    "enabled"
                ),
                line_number=item[
                    "line_number"
                ],
                raw=item[
                    "raw"
                ],
            )
            for item in payload.get(
                "declarations",
                [],
            )
        ),
        unparsed_lines=tuple(
            ParsedKernelConfigUnparsedLine(
                line_number=item[
                    "line_number"
                ],
                raw=item[
                    "raw"
                ],
                reason=item[
                    "reason"
                ],
            )
            for item in payload.get(
                "unparsed_lines",
                [],
            )
        ),
    )


class ParsedKernelImageCodec:
    type_tag = "android.parsed.kernel_image"
    python_type = ParsedKernelImage

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedKernelImage,
        ):
            raise TypeError(
                "value must be a ParsedKernelImage"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "linux_banner": value.linux_banner,
            "kernel_release": value.kernel_release,
            "config": _kernel_config_to_dict(
                value.config
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored kernel artifact must be an ExtractedArtifact"
            )

        return ParsedKernelImage(
            artifact=artifact,
            linux_banner=payload.get(
                "linux_banner"
            ),
            kernel_release=payload.get(
                "kernel_release"
            ),
            config=_kernel_config_from_dict(
                payload.get(
                    "config"
                )
            ),
        )


# ---------------------------------------------------------------------------
# Boot-family
# ---------------------------------------------------------------------------


def _boot_metadata_to_dict(
    value: ParsedBootImageMetadata,
) -> dict[str, Any]:
    return {
        "header_version": value.header_version,
        "os_version": value.os_version,
        "android_major": value.android_major,
        "android_minor": value.android_minor,
        "android_patch": value.android_patch,
        "boot_name": value.boot_name,
        "cmdline": value.cmdline,
    }


def _boot_metadata_from_dict(
    payload: object,
) -> ParsedBootImageMetadata:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "boot metadata payload must be a dict"
        )

    return ParsedBootImageMetadata(
        header_version=payload[
            "header_version"
        ],
        os_version=payload[
            "os_version"
        ],
        android_major=payload[
            "android_major"
        ],
        android_minor=payload[
            "android_minor"
        ],
        android_patch=payload[
            "android_patch"
        ],
        boot_name=payload[
            "boot_name"
        ],
        cmdline=payload[
            "cmdline"
        ],
    )


def _vendor_boot_metadata_to_dict(
    value: ParsedVendorBootImageMetadata,
) -> dict[str, Any]:
    return {
        "header_version": value.header_version,
        "boot_name": value.boot_name,
        "cmdline": value.cmdline,
    }


def _vendor_boot_metadata_from_dict(
    payload: object,
) -> ParsedVendorBootImageMetadata:
    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "vendor_boot metadata payload must be a dict"
        )

    return ParsedVendorBootImageMetadata(
        header_version=payload[
            "header_version"
        ],
        boot_name=payload[
            "boot_name"
        ],
        cmdline=payload[
            "cmdline"
        ],
    )


def _bootconfig_to_dict(
    value: ParsedAndroidBootconfig | None,
) -> dict[str, Any] | None:
    if value is None:
        return None

    return {
        "entries": [
            {
                "key": item.key,
                "value": item.value,
                "line_number": item.line_number,
                "raw": item.raw,
            }
            for item in value.entries
        ],
        "unparsed_lines": [
            {
                "line_number": item.line_number,
                "raw": item.raw,
                "reason": item.reason,
            }
            for item in value.unparsed_lines
        ],
    }


def _bootconfig_from_dict(
    payload: object,
) -> ParsedAndroidBootconfig | None:
    if payload is None:
        return None

    if not isinstance(
        payload,
        dict,
    ):
        raise TypeError(
            "bootconfig payload must be a dict or None"
        )

    return ParsedAndroidBootconfig(
        entries=tuple(
            AndroidBootconfigEntry(
                key=item[
                    "key"
                ],
                value=item[
                    "value"
                ],
                line_number=item[
                    "line_number"
                ],
                raw=item[
                    "raw"
                ],
            )
            for item in payload.get(
                "entries",
                [],
            )
        ),
        unparsed_lines=tuple(
            AndroidBootconfigUnparsedLine(
                line_number=item[
                    "line_number"
                ],
                raw=item[
                    "raw"
                ],
                reason=item[
                    "reason"
                ],
            )
            for item in payload.get(
                "unparsed_lines",
                [],
            )
        ),
    )


class ParsedBootSignatureCodec:
    type_tag = "android.parsed.boot_signature"
    python_type = ParsedBootSignature

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedBootSignature,
        ):
            raise TypeError(
                "value must be a ParsedBootSignature"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "boot_image_artifact": encoder.ref(
                value.boot_image_artifact
            ),
            "metadata": _vbmeta_to_dict(
                value.metadata
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        artifact = decoder.ref(
            payload[
                "artifact"
            ]
        )

        boot_image_artifact = decoder.ref(
            payload[
                "boot_image_artifact"
            ]
        )

        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored boot-signature artifact must be "
                "an ExtractedArtifact"
            )

        if not isinstance(
            boot_image_artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "restored boot-signature boot-image artifact must "
                "be an ExtractedArtifact"
            )

        return ParsedBootSignature(
            artifact=artifact,
            boot_image_artifact=(
                boot_image_artifact
            ),
            metadata=_vbmeta_from_dict(
                payload[
                    "metadata"
                ]
            ),
        )


class ParsedBootImageCodec:
    type_tag = "android.parsed.boot_image"
    python_type = ParsedBootImage

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedBootImage,
        ):
            raise TypeError(
                "value must be a ParsedBootImage"
            )

        if value.container_format == "android_boot":
            metadata = _boot_metadata_to_dict(
                value.metadata
            )
        elif value.container_format == "android_vendor_boot":
            metadata = _vendor_boot_metadata_to_dict(
                value.metadata
            )
        else:
            raise ValueError(
                "unsupported ParsedBootImage container format"
            )

        return {
            "partition": encoder.ref(
                value.partition
            ),
            "container_format": (
                value.container_format
            ),
            "container_kind": (
                value.container_kind
            ),
            "metadata": metadata,
            "component_artifacts": [
                encoder.ref(
                    artifact
                )
                for artifact
                in value.component_artifacts
            ],
            "bootconfig_artifact": _optional_ref(
                encoder,
                value.bootconfig_artifact,
            ),
            "bootconfig": _bootconfig_to_dict(
                value.bootconfig
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        partition = decoder.ref(
            payload["partition"]
        )

        component_artifacts = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload[
                "component_artifacts"
            ]
        )

        bootconfig_artifact = _decode_optional_ref(
            decoder,
            payload[
                "bootconfig_artifact"
            ],
        )

        if not isinstance(
            partition,
            InventoryPartition,
        ):
            raise TypeError(
                "restored boot image partition must be "
                "an InventoryPartition"
            )

        if not all(
            isinstance(
                artifact,
                ExtractedArtifact,
            )
            for artifact
            in component_artifacts
        ):
            raise TypeError(
                "restored boot image components must contain "
                "only ExtractedArtifact instances"
            )

        if (
            bootconfig_artifact is not None
            and not isinstance(
                bootconfig_artifact,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "restored bootconfig artifact must be "
                "an ExtractedArtifact or None"
            )

        container_format = payload[
            "container_format"
        ]

        if container_format == "android_boot":
            metadata = _boot_metadata_from_dict(
                payload["metadata"]
            )
        elif container_format == "android_vendor_boot":
            metadata = _vendor_boot_metadata_from_dict(
                payload["metadata"]
            )
        else:
            raise ValueError(
                "unsupported restored boot-image "
                f"container format: {container_format}"
            )

        return ParsedBootImage(
            partition=partition,
            container_format=container_format,
            container_kind=payload[
                "container_kind"
            ],
            metadata=metadata,
            component_artifacts=(
                component_artifacts
            ),
            bootconfig_artifact=(
                bootconfig_artifact
            ),
            bootconfig=_bootconfig_from_dict(
                payload["bootconfig"]
            ),
        )


# ---------------------------------------------------------------------------
# DEX Parsing
# ---------------------------------------------------------------------------


class AndroidDexHeaderCodec:
    type_tag = "android.dex.header"
    python_type = AndroidDexHeader

    _INTEGER_FIELDS = (
        "checksum",
        "file_size",
        "header_size",
        "endian_tag",
        "link_size",
        "link_offset",
        "map_offset",
        "string_ids_size",
        "string_ids_offset",
        "type_ids_size",
        "type_ids_offset",
        "proto_ids_size",
        "proto_ids_offset",
        "field_ids_size",
        "field_ids_offset",
        "method_ids_size",
        "method_ids_offset",
        "class_defs_size",
        "class_defs_offset",
        "data_size",
        "data_offset",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidDexHeader,
        ):
            raise TypeError(
                "value must be an AndroidDexHeader"
            )

        payload = {
            field: getattr(
                value,
                field,
            )
            for field
            in self._INTEGER_FIELDS
        }

        payload.update(
            {
                "magic": value.magic.hex(),
                "signature": value.signature.hex(),
                "endian_encoding": (
                    value.endian_encoding.value
                ),
            }
        )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        values = {
            field: payload[field]
            for field
            in self._INTEGER_FIELDS
        }

        return AndroidDexHeader(
            **values,
            magic=bytes.fromhex(
                payload["magic"]
            ),
            signature=bytes.fromhex(
                payload["signature"]
            ),
            endian_encoding=(
                AndroidDexEndianEncoding(
                    payload[
                        "endian_encoding"
                    ]
                )
            ),
        )


class AndroidDexSourceCodec:
    type_tag = "android.dex.source"
    python_type = AndroidDexSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidDexSource,
        ):
            raise TypeError(
                "value must be an AndroidDexSource"
            )

        return {
            "kind": value.kind.value,
            "parent": encoder.ref(
                value.parent
            ),
            "parent_source_name": (
                value.parent_source_name
            ),
            "parent_android_path": (
                value.parent_android_path.as_posix()
            ),
            "member_name": value.member_name,
            "member_index": value.member_index,
            "embedded_offset": value.embedded_offset,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        parent = decoder.ref(
            payload["parent"]
        )

        return AndroidDexSource(
            kind=AndroidDexSourceKind(
                payload["kind"]
            ),
            parent=parent,
            parent_source_name=payload[
                "parent_source_name"
            ],
            parent_android_path=PurePosixPath(
                payload[
                    "parent_android_path"
                ]
            ),
            member_name=payload.get(
                "member_name"
            ),
            member_index=payload.get(
                "member_index"
            ),
            embedded_offset=payload.get(
                "embedded_offset"
            ),
        )


class ParsedAndroidDexCodec:
    type_tag = "android.dex.parsed"
    python_type = ParsedAndroidDex

    @staticmethod
    def _utf16_code_units(
        value: str,
    ) -> tuple[
        int,
        ...,
    ]:
        """
        Reconstruct the exact UTF-16 code-unit sequence represented by the
        canonical Python string.

        surrogatepass preserves unpaired surrogate code units while normal
        supplementary characters expand back to their canonical surrogate
        pair. This is therefore lossless for AndroidDexString.value.
        """

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "DEX string value must be a string"
            )

        encoded = value.encode(
            "utf-16-be",
            errors="surrogatepass",
        )

        if len(
            encoded
        ) % 2 != 0:
            raise ValueError(
                "UTF-16 encoding produced an odd byte count"
            )

        return tuple(
            (
                encoded[index] << 8
            )
            | encoded[
                index + 1
            ]
            for index in range(
                0,
                len(
                    encoded
                ),
                2,
            )
        )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidDex,
        ):
            raise TypeError(
                "value must be a ParsedAndroidDex"
            )

        #
        # DEX strings/types/classes are intrinsic children of one canonical
        # ParsedAndroidDex. They deliberately remain inside this node rather
        # than becoming millions of global SnapshotGraph nodes.
        #
        # Exact identity is reconstructed from canonical table indexes during
        # decode and revalidated by ParsedAndroidDex.__post_init__.
        #

        string_data_offsets = []
        string_values = []

        for string in value.strings:
            reconstructed_units = (
                self._utf16_code_units(
                    string.value
                )
            )

            if (
                reconstructed_units
                != string.utf16_code_units
            ):
                raise ValueError(
                    "DEX snapshot cannot losslessly derive "
                    "UTF-16 code units from canonical string value"
                )

            if (
                len(
                    reconstructed_units
                )
                != string.utf16_size
            ):
                raise ValueError(
                    "DEX snapshot string utf16_size "
                    "does not match canonical value"
                )

            string_data_offsets.append(
                string.data_offset
            )
            string_values.append(
                string.value
            )

        type_descriptor_indices = [
            item.descriptor_index
            for item
            in value.types
        ]

        class_type_indices = []
        class_access_flags = []
        class_superclass_type_indices = []
        class_interfaces_offsets = []
        class_interface_counts = []
        class_interface_type_indices = []
        class_source_file_indices = []
        class_annotations_offsets = []
        class_data_offsets = []
        class_static_values_offsets = []

        for class_item in value.classes:
            class_type_indices.append(
                class_item.class_type_index
            )
            class_access_flags.append(
                class_item.access_flags
            )
            class_superclass_type_indices.append(
                class_item.superclass_type_index
            )
            class_interfaces_offsets.append(
                class_item.interfaces_offset
            )

            class_interface_counts.append(
                len(
                    class_item.interface_type_indices
                )
            )

            class_interface_type_indices.extend(
                class_item.interface_type_indices
            )

            class_source_file_indices.append(
                class_item.source_file_index
            )
            class_annotations_offsets.append(
                class_item.annotations_offset
            )
            class_data_offsets.append(
                class_item.class_data_offset
            )
            class_static_values_offsets.append(
                class_item.static_values_offset
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "payload_size": value.payload_size,
            "header": encoder.ref(
                value.header
            ),

            #
            # String index and UTF-16 size are implicit in source order and
            # canonical string value respectively.
            #
            "string_data_offsets": (
                string_data_offsets
            ),
            "string_values": (
                string_values
            ),

            #
            # Type index is implicit in source order. The descriptor object
            # is reconstructed from descriptor_index.
            #
            "type_descriptor_indices": (
                type_descriptor_indices
            ),

            #
            # Class definition_index is implicit in source order.
            # Interface indexes are flattened to avoid one snapshot container
            # object per DEX class.
            #
            "class_type_indices": (
                class_type_indices
            ),
            "class_access_flags": (
                class_access_flags
            ),
            "class_superclass_type_indices": (
                class_superclass_type_indices
            ),
            "class_interfaces_offsets": (
                class_interfaces_offsets
            ),
            "class_interface_counts": (
                class_interface_counts
            ),
            "class_interface_type_indices": (
                class_interface_type_indices
            ),
            "class_source_file_indices": (
                class_source_file_indices
            ),
            "class_annotations_offsets": (
                class_annotations_offsets
            ),
            "class_data_offsets": (
                class_data_offsets
            ),
            "class_static_values_offsets": (
                class_static_values_offsets
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        header = decoder.ref(
            payload["header"]
        )

        if not isinstance(
            source,
            AndroidDexSource,
        ):
            raise TypeError(
                "restored DEX source must be an "
                "AndroidDexSource"
            )

        if not isinstance(
            header,
            AndroidDexHeader,
        ):
            raise TypeError(
                "restored DEX header must be an "
                "AndroidDexHeader"
            )

        string_data_offsets = payload[
            "string_data_offsets"
        ]
        string_values = payload[
            "string_values"
        ]

        if (
            len(
                string_data_offsets
            )
            != len(
                string_values
            )
        ):
            raise ValueError(
                "restored DEX string payload populations "
                "do not conserve one-to-one identity"
            )

        strings = []

        for (
            index,
            (
                data_offset,
                string_value,
            ),
        ) in enumerate(
            zip(
                string_data_offsets,
                string_values,
                strict=True,
            )
        ):
            code_units = (
                self._utf16_code_units(
                    string_value
                )
            )

            strings.append(
                AndroidDexString(
                    index=index,
                    data_offset=(
                        data_offset
                    ),
                    utf16_size=len(
                        code_units
                    ),
                    utf16_code_units=(
                        code_units
                    ),
                    value=string_value,
                )
            )

        strings = tuple(
            strings
        )

        descriptor_indices = payload[
            "type_descriptor_indices"
        ]

        types = []

        for (
            index,
            descriptor_index,
        ) in enumerate(
            descriptor_indices
        ):
            if (
                isinstance(
                    descriptor_index,
                    bool,
                )
                or not isinstance(
                    descriptor_index,
                    int,
                )
                or descriptor_index < 0
                or descriptor_index
                >= len(
                    strings
                )
            ):
                raise ValueError(
                    "restored DEX type descriptor index "
                    "is out of range"
                )

            types.append(
                AndroidDexType(
                    index=index,
                    descriptor_index=(
                        descriptor_index
                    ),
                    descriptor=strings[
                        descriptor_index
                    ],
                )
            )

        types = tuple(
            types
        )

        class_type_indices = payload[
            "class_type_indices"
        ]
        class_access_flags = payload[
            "class_access_flags"
        ]
        class_superclass_type_indices = payload[
            "class_superclass_type_indices"
        ]
        class_interfaces_offsets = payload[
            "class_interfaces_offsets"
        ]
        class_interface_counts = payload[
            "class_interface_counts"
        ]
        flattened_interface_indices = payload[
            "class_interface_type_indices"
        ]
        class_source_file_indices = payload[
            "class_source_file_indices"
        ]
        class_annotations_offsets = payload[
            "class_annotations_offsets"
        ]
        class_data_offsets = payload[
            "class_data_offsets"
        ]
        class_static_values_offsets = payload[
            "class_static_values_offsets"
        ]

        class_population_sizes = {
            len(
                class_type_indices
            ),
            len(
                class_access_flags
            ),
            len(
                class_superclass_type_indices
            ),
            len(
                class_interfaces_offsets
            ),
            len(
                class_interface_counts
            ),
            len(
                class_source_file_indices
            ),
            len(
                class_annotations_offsets
            ),
            len(
                class_data_offsets
            ),
            len(
                class_static_values_offsets
            ),
        }

        if len(
            class_population_sizes
        ) != 1:
            raise ValueError(
                "restored DEX class payload populations "
                "have inconsistent lengths"
            )

        class_count = len(
            class_type_indices
        )

        classes = []
        interface_cursor = 0

        for definition_index in range(
            class_count
        ):
            class_type_index = (
                class_type_indices[
                    definition_index
                ]
            )

            if (
                isinstance(
                    class_type_index,
                    bool,
                )
                or not isinstance(
                    class_type_index,
                    int,
                )
                or class_type_index < 0
                or class_type_index
                >= len(
                    types
                )
            ):
                raise ValueError(
                    "restored DEX class type index "
                    "is out of range"
                )

            superclass_type_index = (
                class_superclass_type_indices[
                    definition_index
                ]
            )

            if superclass_type_index is None:
                superclass_type = None
            else:
                if (
                    isinstance(
                        superclass_type_index,
                        bool,
                    )
                    or not isinstance(
                        superclass_type_index,
                        int,
                    )
                    or superclass_type_index < 0
                    or superclass_type_index
                    >= len(
                        types
                    )
                ):
                    raise ValueError(
                        "restored DEX superclass type "
                        "index is out of range"
                    )

                superclass_type = types[
                    superclass_type_index
                ]

            interface_count = (
                class_interface_counts[
                    definition_index
                ]
            )

            if (
                isinstance(
                    interface_count,
                    bool,
                )
                or not isinstance(
                    interface_count,
                    int,
                )
                or interface_count < 0
            ):
                raise ValueError(
                    "restored DEX interface count must "
                    "be a non-negative integer"
                )

            interface_end = (
                interface_cursor
                + interface_count
            )

            if (
                interface_end
                > len(
                    flattened_interface_indices
                )
            ):
                raise ValueError(
                    "restored DEX flattened interface "
                    "population is truncated"
                )

            interface_type_indices = tuple(
                flattened_interface_indices[
                    interface_cursor:
                    interface_end
                ]
            )

            interface_types = []

            for type_index in (
                interface_type_indices
            ):
                if (
                    isinstance(
                        type_index,
                        bool,
                    )
                    or not isinstance(
                        type_index,
                        int,
                    )
                    or type_index < 0
                    or type_index
                    >= len(
                        types
                    )
                ):
                    raise ValueError(
                        "restored DEX interface type "
                        "index is out of range"
                    )

                interface_types.append(
                    types[
                        type_index
                    ]
                )

            interface_cursor = (
                interface_end
            )

            source_file_index = (
                class_source_file_indices[
                    definition_index
                ]
            )

            if source_file_index is None:
                source_file = None
            else:
                if (
                    isinstance(
                        source_file_index,
                        bool,
                    )
                    or not isinstance(
                        source_file_index,
                        int,
                    )
                    or source_file_index < 0
                    or source_file_index
                    >= len(
                        strings
                    )
                ):
                    raise ValueError(
                        "restored DEX source-file index "
                        "is out of range"
                    )

                source_file = strings[
                    source_file_index
                ]

            classes.append(
                AndroidDexClass(
                    definition_index=(
                        definition_index
                    ),
                    class_type_index=(
                        class_type_index
                    ),
                    class_type=types[
                        class_type_index
                    ],
                    access_flags=(
                        class_access_flags[
                            definition_index
                        ]
                    ),
                    superclass_type_index=(
                        superclass_type_index
                    ),
                    superclass_type=(
                        superclass_type
                    ),
                    interfaces_offset=(
                        class_interfaces_offsets[
                            definition_index
                        ]
                    ),
                    interface_type_indices=(
                        interface_type_indices
                    ),
                    interface_types=tuple(
                        interface_types
                    ),
                    source_file_index=(
                        source_file_index
                    ),
                    source_file=source_file,
                    annotations_offset=(
                        class_annotations_offsets[
                            definition_index
                        ]
                    ),
                    class_data_offset=(
                        class_data_offsets[
                            definition_index
                        ]
                    ),
                    static_values_offset=(
                        class_static_values_offsets[
                            definition_index
                        ]
                    ),
                )
            )

        if (
            interface_cursor
            != len(
                flattened_interface_indices
            )
        ):
            raise ValueError(
                "restored DEX flattened interface "
                "population has trailing entries"
            )

        return ParsedAndroidDex(
            source=source,
            payload_size=payload[
                "payload_size"
            ],
            header=header,
            strings=strings,
            types=types,
            classes=tuple(
                classes
            ),
        )


class AndroidStandaloneDexDispositionCodec:
    type_tag = "android.dex.standalone_disposition"
    python_type = AndroidStandaloneDexDisposition

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidStandaloneDexDisposition,
        ):
            raise TypeError(
                "value must be an AndroidStandaloneDexDisposition"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "disposition": (
                value.disposition.value
            ),
            "parsed": (
                encoder.ref(
                    value.parsed
                )
                if value.parsed is not None
                else None
            ),
            "reason": value.reason,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        parsed = (
            decoder.ref(
                payload[
                    "parsed"
                ]
            )
            if payload.get(
                "parsed"
            ) is not None
            else None
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored standalone DEX source must be "
                "an AndroidModelSource"
            )

        if (
            parsed is not None
            and not isinstance(
                parsed,
                ParsedAndroidDex,
            )
        ):
            raise TypeError(
                "restored standalone DEX parsed child must be "
                "a ParsedAndroidDex or None"
            )

        #
        # AndroidStandaloneDexDisposition.__post_init__ revalidates:
        #
        #   * DEX source kind,
        #   * disposition semantics,
        #   * exact ParsedAndroidDex parent identity,
        #   * stable parent source/path identity,
        #   * reason presence/absence.
        #
        # Because source and ParsedAndroidDex.source.parent are both graph
        # references, the decoder restores the same canonical source object
        # rather than reconstructing a duplicate.
        #
        return AndroidStandaloneDexDisposition(
            source=source,
            disposition=(
                AndroidStandaloneDexDispositionKind(
                    payload[
                        "disposition"
                    ]
                )
            ),
            parsed=parsed,
            reason=payload.get(
                "reason"
            ),
        )


class AndroidStandaloneDexParsingResultCodec:
    type_tag = "android.dex.standalone_parsing_result"
    python_type = AndroidStandaloneDexParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidStandaloneDexParsingResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidStandaloneDexParsingResult"
            )

        return {
            "dispositions": [
                encoder.ref(
                    disposition
                )
                for disposition
                in value.dispositions
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        dispositions = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "dispositions",
                [],
            )
        )

        if not all(
            isinstance(
                disposition,
                AndroidStandaloneDexDisposition,
            )
            for disposition
            in dispositions
        ):
            raise TypeError(
                "restored standalone DEX dispositions "
                "contain invalid entries"
            )

        #
        # The result model revalidates canonical source order and prohibits
        # duplicate canonical AndroidModelSource objects.
        #
        return AndroidStandaloneDexParsingResult(
            dispositions=dispositions,
        )


# ---------------------------------------------------------------------------
# ART-runtime Parsing
# ---------------------------------------------------------------------------


class ParsedAndroidOatKeyValueCodec:
    type_tag = "android.art_runtime.oat_key_value"
    python_type = ParsedAndroidOatKeyValue

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidOatKeyValue,
        ):
            raise TypeError(
                "value must be a ParsedAndroidOatKeyValue"
            )

        return {
            "index": value.index,
            "key_offset": value.key_offset,
            "value_offset": value.value_offset,
            "key": value.key,
            "value": value.value,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidOatKeyValue(
            index=payload["index"],
            key_offset=payload["key_offset"],
            value_offset=payload["value_offset"],
            key=payload["key"],
            value=payload["value"],
        )


class ParsedAndroidDexLayoutSubsectionCodec:
    type_tag = "android.art_runtime.dex_layout_subsection"
    python_type = ParsedAndroidDexLayoutSubsection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidDexLayoutSubsection,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidDexLayoutSubsection"
            )

        return {
            "index": value.index,
            "kind": value.kind.value,
            "start_offset": value.start_offset,
            "end_offset": value.end_offset,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidDexLayoutSubsection(
            index=payload["index"],
            kind=AndroidDexLayoutType(
                payload["kind"]
            ),
            start_offset=payload["start_offset"],
            end_offset=payload["end_offset"],
        )


class ParsedAndroidDexLayoutSectionCodec:
    type_tag = "android.art_runtime.dex_layout_section"
    python_type = ParsedAndroidDexLayoutSection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidDexLayoutSection,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidDexLayoutSection"
            )

        return {
            "index": value.index,
            "kind": value.kind.value,
            "subsections": [
                encoder.ref(
                    subsection
                )
                for subsection
                in value.subsections
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidDexLayoutSection(
            index=payload["index"],
            kind=AndroidDexLayoutSectionKind(
                payload["kind"]
            ),
            subsections=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload["subsections"]
            ),
        )


class ParsedAndroidDexLayoutSectionsCodec:
    type_tag = "android.art_runtime.dex_layout_sections"
    python_type = ParsedAndroidDexLayoutSections

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidDexLayoutSections,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidDexLayoutSections"
            )

        return {
            "offset": value.offset,
            "size": value.size,
            "sections": [
                encoder.ref(
                    section
                )
                for section
                in value.sections
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidDexLayoutSections(
            offset=payload["offset"],
            size=payload["size"],
            sections=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload["sections"]
            ),
        )


class ParsedAndroidIndexBssMappingEntryCodec:
    type_tag = "android.art_runtime.index_bss_mapping_entry"
    python_type = ParsedAndroidIndexBssMappingEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidIndexBssMappingEntry,
        ):
            raise TypeError(
                "value must be a ParsedAndroidIndexBssMappingEntry"
            )

        return {
            "index": value.index,
            "index_and_mask": value.index_and_mask,
            "bss_offset": value.bss_offset,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidIndexBssMappingEntry(
            index=payload["index"],
            index_and_mask=payload["index_and_mask"],
            bss_offset=payload["bss_offset"],
        )


class ParsedAndroidIndexBssMappingCodec:
    type_tag = "android.art_runtime.index_bss_mapping"
    python_type = ParsedAndroidIndexBssMapping

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidIndexBssMapping,
        ):
            raise TypeError(
                "value must be a ParsedAndroidIndexBssMapping"
            )

        return {
            "offset": value.offset,
            "size": value.size,
            "entry_count": value.entry_count,
            "entries": [
                encoder.ref(
                    entry
                )
                for entry
                in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        entries = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "entries",
                [],
            )
        )

        if not all(
            isinstance(
                entry,
                ParsedAndroidIndexBssMappingEntry,
            )
            for entry
            in entries
        ):
            raise TypeError(
                "restored IndexBssMapping entries have invalid types"
            )

        return ParsedAndroidIndexBssMapping(
            offset=payload["offset"],
            size=payload["size"],
            entry_count=payload["entry_count"],
            entries=entries,
        )


class ParsedAndroidBcpBssMappingInfoCodec:
    type_tag = "android.art_runtime.bcp_bss_mapping_info"
    python_type = ParsedAndroidBcpBssMappingInfo

    _OFFSET_FIELDS = (
        "method_bss_mapping_offset",
        "type_bss_mapping_offset",
        "public_type_bss_mapping_offset",
        "package_type_bss_mapping_offset",
        "string_bss_mapping_offset",
        "method_type_bss_mapping_offset",
    )

    _MAPPING_FIELDS = (
        "method_bss_mapping",
        "type_bss_mapping",
        "public_type_bss_mapping",
        "package_type_bss_mapping",
        "string_bss_mapping",
        "method_type_bss_mapping",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidBcpBssMappingInfo,
        ):
            raise TypeError(
                "value must be a ParsedAndroidBcpBssMappingInfo"
            )

        payload = {
            "index": value.index,
        }

        for field in self._OFFSET_FIELDS:
            payload[field] = getattr(
                value,
                field,
            )

        for field in self._MAPPING_FIELDS:
            mapping = getattr(
                value,
                field,
            )

            payload[field] = (
                encoder.ref(
                    mapping
                )
                if mapping is not None
                else None
            )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        mappings = {}

        for field in self._MAPPING_FIELDS:
            ref = payload.get(
                field
            )

            value = (
                decoder.ref(
                    ref
                )
                if ref is not None
                else None
            )

            if (
                value is not None
                and not isinstance(
                    value,
                    ParsedAndroidIndexBssMapping,
                )
            ):
                raise TypeError(
                    "restored BCP BSS mapping has invalid type: "
                    f"{field}"
                )

            mappings[field] = value

        return ParsedAndroidBcpBssMappingInfo(
            index=payload["index"],
            method_bss_mapping_offset=payload[
                "method_bss_mapping_offset"
            ],
            type_bss_mapping_offset=payload[
                "type_bss_mapping_offset"
            ],
            public_type_bss_mapping_offset=payload[
                "public_type_bss_mapping_offset"
            ],
            package_type_bss_mapping_offset=payload[
                "package_type_bss_mapping_offset"
            ],
            string_bss_mapping_offset=payload[
                "string_bss_mapping_offset"
            ],
            method_type_bss_mapping_offset=payload.get(
                "method_type_bss_mapping_offset"
            ),
            **mappings,
        )


class ParsedAndroidBcpBssInfoCodec:
    type_tag = "android.art_runtime.bcp_bss_info"
    python_type = ParsedAndroidBcpBssInfo

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidBcpBssInfo,
        ):
            raise TypeError(
                "value must be a ParsedAndroidBcpBssInfo"
            )

        return {
            "offset": value.offset,
            "record_size": value.record_size,
            "dex_file_count": value.dex_file_count,
            "records": [
                encoder.ref(
                    record
                )
                for record
                in value.records
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        records = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "records",
                [],
            )
        )

        if not all(
            isinstance(
                record,
                ParsedAndroidBcpBssMappingInfo,
            )
            for record
            in records
        ):
            raise TypeError(
                "restored BCP BSS records have invalid types"
            )

        return ParsedAndroidBcpBssInfo(
            offset=payload["offset"],
            record_size=payload["record_size"],
            dex_file_count=payload["dex_file_count"],
            records=records,
        )


class ParsedAndroidOatDexFileCodec:
    type_tag = "android.art_runtime.oat_dex_file"
    python_type = ParsedAndroidOatDexFile

    _INTEGER_FIELDS = (
        "index",
        "record_offset",
        "record_size",
        "dex_file_location_size",
        "dex_file_location_checksum",
        "dex_file_offset",
        "class_offsets_offset",
        "lookup_table_offset",
        "dex_layout_sections_offset",
        "method_bss_mapping_offset",
        "type_bss_mapping_offset",
        "public_type_bss_mapping_offset",
        "package_type_bss_mapping_offset",
        "string_bss_mapping_offset",
        "method_type_bss_mapping_offset",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidOatDexFile,
        ):
            raise TypeError(
                "value must be a ParsedAndroidOatDexFile"
            )

        payload = {
            field: getattr(
                value,
                field,
            )
            for field
            in self._INTEGER_FIELDS
        }

        payload.update(
            {
                "dex_file_location_bytes": (
                    _encode_bytes(
                        value.dex_file_location_bytes
                    )
                ),
                "dex_file_location": (
                    value.dex_file_location
                ),
                "dex_file_magic": (
                    _encode_bytes(
                        value.dex_file_magic
                    )
                    if value.dex_file_magic is not None
                    else None
                ),
                "dex_file_sha1": (
                    _encode_bytes(
                        value.dex_file_sha1
                    )
                    if value.dex_file_sha1 is not None
                    else None
                ),
                "dex_storage_disposition": (
                    value.dex_storage_disposition.value
                ),
                "dex_layout_sections": (
                    encoder.ref(
                        value.dex_layout_sections
                    )
                    if value.dex_layout_sections is not None
                    else None
                ),
                "method_bss_mapping": (
                    encoder.ref(
                        value.method_bss_mapping
                    )
                    if value.method_bss_mapping is not None
                    else None
                ),
                "type_bss_mapping": (
                    encoder.ref(
                        value.type_bss_mapping
                    )
                    if value.type_bss_mapping is not None
                    else None
                ),
                "public_type_bss_mapping": (
                    encoder.ref(
                        value.public_type_bss_mapping
                    )
                    if value.public_type_bss_mapping is not None
                    else None
                ),
                "package_type_bss_mapping": (
                    encoder.ref(
                        value.package_type_bss_mapping
                    )
                    if value.package_type_bss_mapping is not None
                    else None
                ),
                "string_bss_mapping": (
                    encoder.ref(
                        value.string_bss_mapping
                    )
                    if value.string_bss_mapping is not None
                    else None
                ),
                "method_type_bss_mapping": (
                    encoder.ref(
                        value.method_type_bss_mapping
                    )
                    if value.method_type_bss_mapping is not None
                    else None
                ),
            }
        )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        values = {
            field: (
                payload.get(field)
                if field == "method_type_bss_mapping_offset"
                else payload[field]
            )
            for field
            in self._INTEGER_FIELDS
        }

        return ParsedAndroidOatDexFile(
            **values,
            dex_file_location_bytes=(
                _decode_bytes(
                    payload[
                        "dex_file_location_bytes"
                    ],
                    field_name=(
                        "dex_file_location_bytes"
                    ),
                )
            ),
            dex_file_location=payload[
                "dex_file_location"
            ],
            dex_file_magic=(
                _decode_bytes(
                    payload[
                        "dex_file_magic"
                    ],
                    field_name="dex_file_magic",
                )
                if payload.get(
                    "dex_file_magic"
                ) is not None
                else None
            ),
            dex_file_sha1=(
                _decode_bytes(
                    payload[
                        "dex_file_sha1"
                    ],
                    field_name="dex_file_sha1",
                )
                if payload.get(
                    "dex_file_sha1"
                ) is not None
                else None
            ),
            dex_storage_disposition=(
                AndroidOatDexStorageDisposition(
                    payload[
                        "dex_storage_disposition"
                    ]
                )
            ),
            dex_layout_sections=(
                decoder.ref(
                    payload[
                        "dex_layout_sections"
                    ]
                )
                if payload.get(
                    "dex_layout_sections"
                ) is not None
                else None
            ),
            method_bss_mapping=(
                decoder.ref(
                    payload[
                        "method_bss_mapping"
                    ]
                )
                if payload.get(
                    "method_bss_mapping"
                ) is not None
                else None
            ),
            type_bss_mapping=(
                decoder.ref(
                    payload[
                        "type_bss_mapping"
                    ]
                )
                if payload.get(
                    "type_bss_mapping"
                ) is not None
                else None
            ),
            public_type_bss_mapping=(
                decoder.ref(
                    payload[
                        "public_type_bss_mapping"
                    ]
                )
                if payload.get(
                    "public_type_bss_mapping"
                ) is not None
                else None
            ),
            package_type_bss_mapping=(
                decoder.ref(
                    payload[
                        "package_type_bss_mapping"
                    ]
                )
                if payload.get(
                    "package_type_bss_mapping"
                ) is not None
                else None
            ),
            string_bss_mapping=(
                decoder.ref(
                    payload[
                        "string_bss_mapping"
                    ]
                )
                if payload.get(
                    "string_bss_mapping"
                ) is not None
                else None
            ),
            method_type_bss_mapping=(
                decoder.ref(
                    payload[
                        "method_type_bss_mapping"
                    ]
                )
                if payload.get(
                    "method_type_bss_mapping"
                ) is not None
                else None
            ),
        )


class ParsedAndroidOatStructuralHeaderCodec:
    type_tag = "android.art_runtime.oat_251_header"
    python_type = ParsedAndroidOatStructuralHeader

    _INTEGER_FIELDS = (
        "checksum",
        "instruction_set",
        "instruction_set_features_bitmap",
        "dex_file_count",
        "oat_dex_files_offset",
        "bcp_bss_info_offset",
        "executable_offset",
        "jni_dlsym_lookup_trampoline_offset",
        "jni_dlsym_lookup_critical_trampoline_offset",
        "quick_generic_jni_trampoline_offset",
        "quick_imt_conflict_trampoline_offset",
        "quick_resolution_trampoline_offset",
        "quick_to_interpreter_bridge_offset",
        "nterp_trampoline_offset",
        "key_value_store_size",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidOatStructuralHeader,
        ):
            raise TypeError(
                "value must be a ParsedAndroidOatStructuralHeader"
            )

        payload = {
            field: getattr(
                value,
                field,
            )
            for field
            in self._INTEGER_FIELDS
        }

        payload["key_values"] = [
            encoder.ref(
                item
            )
            for item
            in value.key_values
        ]

        payload["oat_dex_files"] = [
            encoder.ref(
                item
            )
            for item
            in value.oat_dex_files
        ]

        payload["bcp_bss_info"] = (
            encoder.ref(
                value.bcp_bss_info
            )
            if value.bcp_bss_info is not None
            else None
        )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        key_values = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "key_values",
                [],
            )
        )

        if not all(
            isinstance(
                item,
                ParsedAndroidOatKeyValue,
            )
            for item
            in key_values
        ):
            raise TypeError(
                "restored OAT key/value entries are invalid"
            )

        oat_dex_files = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload[
                "oat_dex_files"
            ]
        )

        if not all(
            isinstance(
                item,
                ParsedAndroidOatDexFile,
            )
            for item
            in oat_dex_files
        ):
            raise TypeError(
                "restored OatDexFile entries are invalid"
            )

        bcp_bss_info = (
            decoder.ref(
                payload[
                    "bcp_bss_info"
                ]
            )
            if payload.get(
                "bcp_bss_info"
            ) is not None
            else None
        )

        if (
            bcp_bss_info is not None
            and not isinstance(
                bcp_bss_info,
                ParsedAndroidBcpBssInfo,
            )
        ):
            raise TypeError(
                "restored BCP BSS info has invalid type"
            )

        values = {
            field: payload[field]
            for field
            in self._INTEGER_FIELDS
        }

        return ParsedAndroidOatStructuralHeader(
            **values,
            key_values=key_values,
            oat_dex_files=oat_dex_files,
            bcp_bss_info=bcp_bss_info,
        )


class ParsedAndroidOatCodec:
    type_tag = "android.art_runtime.oat"
    python_type = ParsedAndroidOat

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidOat,
        ):
            raise TypeError(
                "value must be a ParsedAndroidOat"
            )

        return {
            "elf": encoder.ref(
                value.elf
            ),
            "oat_offset": value.oat_offset,
            "magic": value.magic.hex(),
            "version": value.version.hex(),
            "layout_supported": value.layout_supported,
            # Historical snapshot key retained for compatibility.
            "header_244_251": (
                encoder.ref(
                    value.structural_header
                )
                if value.structural_header is not None
                else None
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        elf = decoder.ref(
            payload["elf"]
        )

        if not isinstance(
            elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "restored OAT ELF must be a ParsedAndroidElf"
            )

        header_ref = payload.get(
            "header_244_251"
        )

        if header_ref is None:
            header_ref = payload.get(
                "header_251"
            )

        header = (
            decoder.ref(
                header_ref
            )
            if header_ref is not None
            else None
        )

        if (
            header is not None
            and not isinstance(
                header,
                ParsedAndroidOatStructuralHeader,
            )
        ):
            raise TypeError(
                "restored OAT structural header has invalid type"
            )

        return ParsedAndroidOat(
            elf=elf,
            oat_offset=payload["oat_offset"],
            magic=bytes.fromhex(
                payload["magic"]
            ),
            version=bytes.fromhex(
                payload["version"]
            ),
            layout_supported=payload[
                "layout_supported"
            ],
            structural_header=header,
        )


class ParsedAndroidVdexSectionCodec:
    type_tag = "android.art_runtime.vdex_section"
    python_type = ParsedAndroidVdexSection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidVdexSection,
        ):
            raise TypeError(
                "value must be a ParsedAndroidVdexSection"
            )

        return {
            "index": value.index,
            "kind": value.kind,
            "offset": value.offset,
            "size": value.size,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidVdexSection(
            index=payload["index"],
            kind=payload["kind"],
            offset=payload["offset"],
            size=payload["size"],
        )


class ParsedAndroidVdex027Codec:
    type_tag = "android.art_runtime.vdex_027"
    python_type = ParsedAndroidVdex027

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidVdex027,
        ):
            raise TypeError(
                "value must be a ParsedAndroidVdex027"
            )

        return {
            "section_count": value.section_count,
            "sections": [
                encoder.ref(
                    section
                )
                for section
                in value.sections
            ],
            "dex_checksums": list(
                value.dex_checksums
            ),
            "dex_file_count": value.dex_file_count,
            "has_dex_section": value.has_dex_section,
            "dex_files": [
                encoder.ref(
                    dex
                )
                for dex
                in value.dex_files
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        sections = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "sections",
                [],
            )
        )

        if not all(
            isinstance(
                section,
                ParsedAndroidVdexSection,
            )
            for section
            in sections
        ):
            raise TypeError(
                "restored VDEX sections have invalid types"
            )

        dex_files = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "dex_files",
                [],
            )
        )

        if len(
            dex_files
        ) != payload[
            "dex_file_count"
        ] and payload[
            "has_dex_section"
        ]:
            raise ValueError(
                "restored populated VDEX must preserve exactly "
                "dex_file_count DEX payload references"
            )

        return ParsedAndroidVdex027(
            section_count=payload[
                "section_count"
            ],
            sections=sections,
            dex_checksums=tuple(
                payload.get(
                    "dex_checksums",
                    [],
                )
            ),
            dex_file_count=payload[
                "dex_file_count"
            ],
            has_dex_section=payload[
                "has_dex_section"
            ],
            dex_files=dex_files,
        )


class ParsedAndroidVdexCodec:
    type_tag = "android.art_runtime.vdex"
    python_type = ParsedAndroidVdex

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidVdex,
        ):
            raise TypeError(
                "value must be a ParsedAndroidVdex"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "magic": value.magic.hex(),
            "version": value.version.hex(),
            "layout_supported": value.layout_supported,
            "vdex_027": (
                encoder.ref(
                    value.vdex_027
                )
                if value.vdex_027 is not None
                else None
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored VDEX source must be an AndroidModelSource"
            )

        detail_ref = payload.get(
            "vdex_027"
        )

        detail = (
            decoder.ref(
                detail_ref
            )
            if detail_ref is not None
            else None
        )

        if (
            detail is not None
            and not isinstance(
                detail,
                ParsedAndroidVdex027,
            )
        ):
            raise TypeError(
                "restored VDEX 027 detail has invalid type"
            )

        return ParsedAndroidVdex(
            source=source,
            magic=bytes.fromhex(
                payload["magic"]
            ),
            version=bytes.fromhex(
                payload["version"]
            ),
            layout_supported=payload[
                "layout_supported"
            ],
            vdex_027=detail,
        )


class ParsedAndroidArtImageSectionCodec:
    type_tag = "android.art_runtime.image_section"
    python_type = ParsedAndroidArtImageSection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidArtImageSection,
        ):
            raise TypeError(
                "value must be a ParsedAndroidArtImageSection"
            )

        return {
            "index": value.index,
            "kind": value.kind.value,
            "offset": value.offset,
            "size": value.size,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidArtImageSection(
            index=payload["index"],
            kind=AndroidArtImageSectionKind(
                payload["kind"]
            ),
            offset=payload["offset"],
            size=payload["size"],
        )


class ParsedAndroidArtImage111Codec:
    type_tag = "android.art_runtime.image_111"
    python_type = ParsedAndroidArtImage111

    _INTEGER_FIELDS = (
        "image_reservation_size",
        "component_count",
        "image_begin",
        "image_size",
        "image_checksum",
        "oat_checksum",
        "oat_file_begin",
        "oat_data_begin",
        "oat_data_end",
        "oat_file_end",
        "boot_image_begin",
        "boot_image_size",
        "boot_image_component_count",
        "boot_image_checksum",
        "image_roots",
        "pointer_size",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidArtImage111,
        ):
            raise TypeError(
                "value must be a ParsedAndroidArtImage111"
            )

        payload = {
            field: getattr(
                value,
                field,
            )
            for field
            in self._INTEGER_FIELDS
        }

        payload["sections"] = [
            encoder.ref(
                section
            )
            for section
            in value.sections
        ]

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        sections = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "sections",
                [],
            )
        )

        if not all(
            isinstance(
                section,
                ParsedAndroidArtImageSection,
            )
            for section
            in sections
        ):
            raise TypeError(
                "restored ART image sections have invalid types"
            )

        values = {
            field: payload[field]
            for field
            in self._INTEGER_FIELDS
        }

        return ParsedAndroidArtImage111(
            **values,
            sections=sections,
        )


class ParsedAndroidArtImageCodec:
    type_tag = "android.art_runtime.image"
    python_type = ParsedAndroidArtImage

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidArtImage,
        ):
            raise TypeError(
                "value must be a ParsedAndroidArtImage"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "magic": value.magic.hex(),
            "version": value.version.hex(),
            "layout_supported": value.layout_supported,
            "image_111": (
                encoder.ref(
                    value.image_111
                )
                if value.image_111 is not None
                else None
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored ART image source must be an "
                "AndroidModelSource"
            )

        detail_ref = payload.get(
            "image_111"
        )

        detail = (
            decoder.ref(
                detail_ref
            )
            if detail_ref is not None
            else None
        )

        if (
            detail is not None
            and not isinstance(
                detail,
                ParsedAndroidArtImage111,
            )
        ):
            raise TypeError(
                "restored ART image 111 detail has invalid type"
            )

        return ParsedAndroidArtImage(
            source=source,
            magic=bytes.fromhex(
                payload["magic"]
            ),
            version=bytes.fromhex(
                payload["version"]
            ),
            layout_supported=payload[
                "layout_supported"
            ],
            image_111=detail,
        )


class AndroidArtRuntimeParsingResultCodec:
    type_tag = "android.art_runtime.result"
    python_type = AndroidArtRuntimeParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidArtRuntimeParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidArtRuntimeParsingResult"
            )

        return {
            "oat_files": [
                encoder.ref(
                    item
                )
                for item
                in value.oat_files
            ],
            "vdex_files": [
                encoder.ref(
                    item
                )
                for item
                in value.vdex_files
            ],
            "art_images": [
                encoder.ref(
                    item
                )
                for item
                in value.art_images
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        oat_files = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "oat_files",
                [],
            )
        )

        vdex_files = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "vdex_files",
                [],
            )
        )

        art_images = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "art_images",
                [],
            )
        )

        if not all(
            isinstance(
                item,
                ParsedAndroidOat,
            )
            for item
            in oat_files
        ):
            raise TypeError(
                "restored ART-runtime OAT entries are invalid"
            )

        if not all(
            isinstance(
                item,
                ParsedAndroidVdex,
            )
            for item
            in vdex_files
        ):
            raise TypeError(
                "restored ART-runtime VDEX entries are invalid"
            )

        if not all(
            isinstance(
                item,
                ParsedAndroidArtImage,
            )
            for item
            in art_images
        ):
            raise TypeError(
                "restored ART-runtime image entries are invalid"
            )

        return AndroidArtRuntimeParsingResult(
            oat_files=oat_files,
            vdex_files=vdex_files,
            art_images=art_images,
        )


# ---------------------------------------------------------------------------
# Runtime classpath Parsing
# ---------------------------------------------------------------------------


class AndroidClasspathProtobufUnknownFieldCodec:
    type_tag = "android.classpath.protobuf_unknown_field"
    python_type = AndroidClasspathProtobufUnknownField

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidClasspathProtobufUnknownField,
        ):
            raise TypeError(
                "value must be an "
                "AndroidClasspathProtobufUnknownField"
            )

        return {
            "field_number": value.field_number,
            "wire_type": value.wire_type,
            "raw": _encode_bytes(
                value.raw
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidClasspathProtobufUnknownField(
            field_number=payload[
                "field_number"
            ],
            wire_type=payload[
                "wire_type"
            ],
            raw=_decode_bytes(
                payload[
                    "raw"
                ],
                field_name="raw",
            ),
        )


class AndroidClasspathJarCodec:
    type_tag = "android.classpath.jar"
    python_type = AndroidClasspathJar

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidClasspathJar,
        ):
            raise TypeError(
                "value must be an AndroidClasspathJar"
            )

        return {
            "path": value.path,
            "path_present": value.path_present,
            "classpath_value": (
                value.classpath_value
            ),
            "classpath_present": (
                value.classpath_present
            ),
            "min_sdk_version": (
                value.min_sdk_version
            ),
            "min_sdk_version_present": (
                value.min_sdk_version_present
            ),
            "max_sdk_version": (
                value.max_sdk_version
            ),
            "max_sdk_version_present": (
                value.max_sdk_version_present
            ),
            "unknown_fields": [
                encoder.ref(
                    field
                )
                for field
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        unknown_fields = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "unknown_fields",
                [],
            )
        )

        if not all(
            isinstance(
                field,
                AndroidClasspathProtobufUnknownField,
            )
            for field
            in unknown_fields
        ):
            raise TypeError(
                "restored classpath Jar unknown fields "
                "contain invalid entries"
            )

        return AndroidClasspathJar(
            path=payload.get(
                "path",
                "",
            ),
            path_present=payload.get(
                "path_present",
                False,
            ),
            classpath_value=payload.get(
                "classpath_value",
                0,
            ),
            classpath_present=payload.get(
                "classpath_present",
                False,
            ),
            min_sdk_version=payload.get(
                "min_sdk_version",
                "",
            ),
            min_sdk_version_present=payload.get(
                "min_sdk_version_present",
                False,
            ),
            max_sdk_version=payload.get(
                "max_sdk_version",
                "",
            ),
            max_sdk_version_present=payload.get(
                "max_sdk_version_present",
                False,
            ),
            unknown_fields=unknown_fields,
        )


class ParsedAndroidClasspathConfigurationCodec:
    type_tag = "android.classpath.configuration"
    python_type = ParsedAndroidClasspathConfiguration

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidClasspathConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidClasspathConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "raw": _encode_bytes(
                value.raw
            ),
            "jars": [
                encoder.ref(
                    jar
                )
                for jar
                in value.jars
            ],
            "unknown_fields": [
                encoder.ref(
                    field
                )
                for field
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload[
                "source"
            ]
        )

        jars = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "jars",
                [],
            )
        )

        unknown_fields = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "unknown_fields",
                [],
            )
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored classpath source must be an "
                "AndroidModelSource"
            )

        if not all(
            isinstance(
                jar,
                AndroidClasspathJar,
            )
            for jar
            in jars
        ):
            raise TypeError(
                "restored classpath configuration "
                "contains invalid Jar entries"
            )

        if not all(
            isinstance(
                field,
                AndroidClasspathProtobufUnknownField,
            )
            for field
            in unknown_fields
        ):
            raise TypeError(
                "restored classpath configuration "
                "contains invalid unknown fields"
            )

        return ParsedAndroidClasspathConfiguration(
            source=source,
            raw=_decode_bytes(
                payload[
                    "raw"
                ],
                field_name="raw",
            ),
            jars=jars,
            unknown_fields=unknown_fields,
        )


class AndroidClasspathParsingResultCodec:
    type_tag = "android.classpath.result"
    python_type = AndroidClasspathParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidClasspathParsingResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidClasspathParsingResult"
            )

        return {
            "configurations": [
                encoder.ref(
                    configuration
                )
                for configuration
                in value.configurations
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        configurations = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "configurations",
                [],
            )
        )

        if not all(
            isinstance(
                configuration,
                ParsedAndroidClasspathConfiguration,
            )
            for configuration
            in configurations
        ):
            raise TypeError(
                "restored classpath result contains "
                "invalid configurations"
            )

        return AndroidClasspathParsingResult(
            configurations=configurations,
        )


# ---------------------------------------------------------------------------
# Aconfig Parsing
# ---------------------------------------------------------------------------


class AndroidAconfigProtobufUnknownFieldCodec:
    type_tag = "android.aconfig.protobuf_unknown_field"
    python_type = AndroidAconfigProtobufUnknownField

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidAconfigProtobufUnknownField,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAconfigProtobufUnknownField"
            )

        return {
            "field_number": value.field_number,
            "wire_type": value.wire_type,
            "raw": _encode_bytes(
                value.raw
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidAconfigProtobufUnknownField(
            field_number=payload[
                "field_number"
            ],
            wire_type=payload[
                "wire_type"
            ],
            raw=_decode_bytes(
                payload[
                    "raw"
                ],
                field_name="raw",
            ),
        )


class AndroidAconfigFlagMetadataCodec:
    type_tag = "android.aconfig.flag_metadata"
    python_type = AndroidAconfigFlagMetadata

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidAconfigFlagMetadata,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAconfigFlagMetadata"
            )

        return {
            "purpose_value": value.purpose_value,
            "purpose_present": (
                value.purpose_present
            ),
            "unknown_fields": [
                encoder.ref(
                    field
                )
                for field
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        unknown_fields = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "unknown_fields",
                [],
            )
        )

        if not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in unknown_fields
        ):
            raise TypeError(
                "restored aconfig metadata "
                "contains invalid unknown fields"
            )

        return AndroidAconfigFlagMetadata(
            purpose_value=payload.get(
                "purpose_value",
                0,
            ),
            purpose_present=payload.get(
                "purpose_present",
                False,
            ),
            unknown_fields=unknown_fields,
        )


class AndroidAconfigTracepointCodec:
    type_tag = "android.aconfig.tracepoint"
    python_type = AndroidAconfigTracepoint

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidAconfigTracepoint,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAconfigTracepoint"
            )

        return {
            "source": value.source,
            "source_present": (
                value.source_present
            ),
            "state_value": (
                value.state_value
            ),
            "state_present": (
                value.state_present
            ),
            "permission_value": (
                value.permission_value
            ),
            "permission_present": (
                value.permission_present
            ),
            "unknown_fields": [
                encoder.ref(
                    field
                )
                for field
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        unknown_fields = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "unknown_fields",
                [],
            )
        )

        if not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in unknown_fields
        ):
            raise TypeError(
                "restored aconfig tracepoint "
                "contains invalid unknown fields"
            )

        return AndroidAconfigTracepoint(
            source=payload.get(
                "source",
                "",
            ),
            source_present=payload.get(
                "source_present",
                False,
            ),
            state_value=payload.get(
                "state_value",
                0,
            ),
            state_present=payload.get(
                "state_present",
                False,
            ),
            permission_value=payload.get(
                "permission_value",
                0,
            ),
            permission_present=payload.get(
                "permission_present",
                False,
            ),
            unknown_fields=unknown_fields,
        )


class AndroidAconfigParsedFlagCodec:
    type_tag = "android.aconfig.parsed_flag"
    python_type = AndroidAconfigParsedFlag

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidAconfigParsedFlag,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAconfigParsedFlag"
            )

        return {
            "package": value.package,
            "package_present": (
                value.package_present
            ),
            "name": value.name,
            "name_present": (
                value.name_present
            ),
            "namespace": value.namespace,
            "namespace_present": (
                value.namespace_present
            ),
            "description": (
                value.description
            ),
            "description_present": (
                value.description_present
            ),
            "bugs": list(
                value.bugs
            ),
            "state_value": (
                value.state_value
            ),
            "state_present": (
                value.state_present
            ),
            "permission_value": (
                value.permission_value
            ),
            "permission_present": (
                value.permission_present
            ),
            "tracepoints": [
                encoder.ref(
                    tracepoint
                )
                for tracepoint
                in value.tracepoints
            ],
            "is_fixed_read_only": (
                value.is_fixed_read_only
            ),
            "is_fixed_read_only_present": (
                value.is_fixed_read_only_present
            ),
            "is_exported": (
                value.is_exported
            ),
            "is_exported_present": (
                value.is_exported_present
            ),
            "container": (
                value.container
            ),
            "container_present": (
                value.container_present
            ),
            "metadata": (
                encoder.ref(
                    value.metadata
                )
                if value.metadata is not None
                else None
            ),
            "metadata_present": (
                value.metadata_present
            ),
            "unknown_fields": [
                encoder.ref(
                    field
                )
                for field
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        tracepoints = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "tracepoints",
                [],
            )
        )

        if not all(
            isinstance(
                tracepoint,
                AndroidAconfigTracepoint,
            )
            for tracepoint
            in tracepoints
        ):
            raise TypeError(
                "restored aconfig flag "
                "contains invalid tracepoints"
            )

        metadata_ref = payload.get(
            "metadata"
        )

        metadata = (
            decoder.ref(
                metadata_ref
            )
            if metadata_ref is not None
            else None
        )

        if (
            metadata is not None
            and not isinstance(
                metadata,
                AndroidAconfigFlagMetadata,
            )
        ):
            raise TypeError(
                "restored aconfig flag "
                "contains invalid metadata"
            )

        unknown_fields = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "unknown_fields",
                [],
            )
        )

        if not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in unknown_fields
        ):
            raise TypeError(
                "restored aconfig flag "
                "contains invalid unknown fields"
            )

        bugs_payload = payload.get(
            "bugs",
            [],
        )

        bugs = tuple(
            bugs_payload
        )

        if not all(
            isinstance(
                bug,
                str,
            )
            for bug
            in bugs
        ):
            raise TypeError(
                "restored aconfig flag bugs "
                "must be strings"
            )

        return AndroidAconfigParsedFlag(
            package=payload.get(
                "package",
                "",
            ),
            package_present=payload.get(
                "package_present",
                False,
            ),
            name=payload.get(
                "name",
                "",
            ),
            name_present=payload.get(
                "name_present",
                False,
            ),
            namespace=payload.get(
                "namespace",
                "",
            ),
            namespace_present=payload.get(
                "namespace_present",
                False,
            ),
            description=payload.get(
                "description",
                "",
            ),
            description_present=payload.get(
                "description_present",
                False,
            ),
            bugs=bugs,
            state_value=payload.get(
                "state_value",
                0,
            ),
            state_present=payload.get(
                "state_present",
                False,
            ),
            permission_value=payload.get(
                "permission_value",
                0,
            ),
            permission_present=payload.get(
                "permission_present",
                False,
            ),
            tracepoints=tracepoints,
            is_fixed_read_only=payload.get(
                "is_fixed_read_only",
                False,
            ),
            is_fixed_read_only_present=payload.get(
                "is_fixed_read_only_present",
                False,
            ),
            is_exported=payload.get(
                "is_exported",
                False,
            ),
            is_exported_present=payload.get(
                "is_exported_present",
                False,
            ),
            container=payload.get(
                "container",
                "",
            ),
            container_present=payload.get(
                "container_present",
                False,
            ),
            metadata=metadata,
            metadata_present=payload.get(
                "metadata_present",
                False,
            ),
            unknown_fields=unknown_fields,
        )


class ParsedAndroidAconfigConfigurationCodec:
    type_tag = "android.aconfig.configuration"
    python_type = ParsedAndroidAconfigConfiguration

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidAconfigConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidAconfigConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "raw": _encode_bytes(
                value.raw
            ),
            "flags": [
                encoder.ref(
                    flag
                )
                for flag
                in value.flags
            ],
            "unknown_fields": [
                encoder.ref(
                    field
                )
                for field
                in value.unknown_fields
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload[
                "source"
            ]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored aconfig source must be an "
                "AndroidModelSource"
            )

        flags = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "flags",
                [],
            )
        )

        if not all(
            isinstance(
                flag,
                AndroidAconfigParsedFlag,
            )
            for flag
            in flags
        ):
            raise TypeError(
                "restored aconfig configuration "
                "contains invalid flags"
            )

        unknown_fields = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "unknown_fields",
                [],
            )
        )

        if not all(
            isinstance(
                field,
                AndroidAconfigProtobufUnknownField,
            )
            for field
            in unknown_fields
        ):
            raise TypeError(
                "restored aconfig configuration "
                "contains invalid unknown fields"
            )

        return ParsedAndroidAconfigConfiguration(
            source=source,
            raw=_decode_bytes(
                payload[
                    "raw"
                ],
                field_name="raw",
            ),
            flags=flags,
            unknown_fields=unknown_fields,
        )


class AndroidAconfigParsingResultCodec:
    type_tag = "android.aconfig.result"
    python_type = AndroidAconfigParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidAconfigParsingResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAconfigParsingResult"
            )

        return {
            "configurations": [
                encoder.ref(
                    configuration
                )
                for configuration
                in value.configurations
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        configurations = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "configurations",
                [],
            )
        )

        if not all(
            isinstance(
                configuration,
                ParsedAndroidAconfigConfiguration,
            )
            for configuration
            in configurations
        ):
            raise TypeError(
                "restored aconfig result contains "
                "invalid configurations"
            )

        return AndroidAconfigParsingResult(
            configurations=configurations,
        )


# ---------------------------------------------------------------------------
# APK package-identity Parsing
# ---------------------------------------------------------------------------


class AndroidApkSourceCodec:
    type_tag = "android.apk_source"
    python_type = AndroidApkSource

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidApkSource,
        ):
            raise TypeError(
                "value must be an AndroidApkSource"
            )

        return {
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "apk_android_path": (
                value.apk_android_path.as_posix()
            ),
            "apk_host_path": str(
                value.apk_host_path
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        filesystem_source = decoder.ref(
            payload[
                "filesystem_source"
            ]
        )

        if not isinstance(
            filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "restored APK filesystem source must be an "
                "AndroidParserFilesystemSource"
            )

        apk_android_path = payload[
            "apk_android_path"
        ]

        if not isinstance(
            apk_android_path,
            str,
        ):
            raise TypeError(
                "restored APK android path must be a string"
            )

        apk_host_path = payload[
            "apk_host_path"
        ]

        if not isinstance(
            apk_host_path,
            str,
        ):
            raise TypeError(
                "restored APK host path must be a string"
            )

        return AndroidApkSource(
            filesystem_source=filesystem_source,
            apk_android_path=PurePosixPath(
                apk_android_path
            ),
            apk_host_path=Path(
                apk_host_path
            ),
        )


class AndroidApkArchiveMemberCodec:
    type_tag = "android.apk_archive_member"
    python_type = AndroidApkArchiveMember

    _INTEGER_FIELDS = (
        "index",
        "compression_method",
        "crc32",
        "compressed_size",
        "uncompressed_size",
        "external_attributes",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidApkArchiveMember,
        ):
            raise TypeError(
                "value must be an AndroidApkArchiveMember"
            )

        payload = {
            field: getattr(
                value,
                field,
            )
            for field
            in self._INTEGER_FIELDS
        }

        payload.update(
            {
                "filename": value.filename,
                "is_directory": value.is_directory,
            }
        )

        return payload

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        values = {
            field: payload[field]
            for field
            in self._INTEGER_FIELDS
        }

        return AndroidApkArchiveMember(
            **values,
            filename=payload["filename"],
            is_directory=payload["is_directory"],
        )


class AndroidApkManifestValueCodec:
    type_tag = "android.apk_manifest_value"
    python_type = AndroidApkManifestValue

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidApkManifestValue,
        ):
            raise TypeError(
                "value must be an AndroidApkManifestValue"
            )

        return {
            "literal": value.literal,
            "data_type": value.data_type,
            "data": value.data,
            "raw_string": value.raw_string,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidApkManifestValue(
            literal=payload.get(
                "literal"
            ),
            data_type=payload.get(
                "data_type"
            ),
            data=payload.get(
                "data"
            ),
            raw_string=payload.get(
                "raw_string"
            ),
        )


class AndroidApkOverlayManifestCodec:
    type_tag = "android.apk_overlay_manifest"
    python_type = AndroidApkOverlayManifest

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidApkOverlayManifest,
        ):
            raise TypeError(
                "value must be an AndroidApkOverlayManifest"
            )

        return {
            "target_package": _optional_ref(
                encoder,
                value.target_package,
            ),
            "priority": _optional_ref(
                encoder,
                value.priority,
            ),
            "is_static": _optional_ref(
                encoder,
                value.is_static,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        target_package = _decode_optional_ref(
            decoder,
            payload.get(
                "target_package"
            ),
        )

        priority = _decode_optional_ref(
            decoder,
            payload.get(
                "priority"
            ),
        )

        is_static = _decode_optional_ref(
            decoder,
            payload.get(
                "is_static"
            ),
        )

        for name, value in (
            (
                "target_package",
                target_package,
            ),
            (
                "priority",
                priority,
            ),
            (
                "is_static",
                is_static,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    AndroidApkManifestValue,
                )
            ):
                raise TypeError(
                    "restored APK overlay "
                    f"{name} has invalid type"
                )

        return AndroidApkOverlayManifest(
            target_package=target_package,
            priority=priority,
            is_static=is_static,
        )


class ParsedAndroidApkCodec:
    type_tag = "android.parsed_apk"
    python_type = ParsedAndroidApk

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidApk,
        ):
            raise TypeError(
                "value must be a ParsedAndroidApk"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "members": [
                encoder.ref(
                    member
                )
                for member
                in value.members
            ],
            "dex_files": [
                encoder.ref(
                    dex_file
                )
                for dex_file
                in value.dex_files
            ],
            "package_name": encoder.ref(
                value.package_name
            ),
            "version_code": _optional_ref(
                encoder,
                value.version_code,
            ),
            "version_name": _optional_ref(
                encoder,
                value.version_name,
            ),
            "overlay": _optional_ref(
                encoder,
                value.overlay,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        members = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload.get(
                "members",
                [],
            )
        )

        dex_files = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload.get(
                "dex_files",
                [],
            )
        )

        package_name = decoder.ref(
            payload["package_name"]
        )

        version_code = _decode_optional_ref(
            decoder,
            payload.get(
                "version_code"
            ),
        )

        version_name = _decode_optional_ref(
            decoder,
            payload.get(
                "version_name"
            ),
        )

        overlay = _decode_optional_ref(
            decoder,
            payload.get(
                "overlay"
            ),
        )

        if not isinstance(
            source,
            AndroidApkSource,
        ):
            raise TypeError(
                "restored APK source has invalid type"
            )

        if not all(
            isinstance(
                member,
                AndroidApkArchiveMember,
            )
            for member
            in members
        ):
            raise TypeError(
                "restored APK members contain invalid entries"
            )

        if not all(
            isinstance(
                dex_file,
                ParsedAndroidDex,
            )
            for dex_file
            in dex_files
        ):
            raise TypeError(
                "restored APK DEX population contains invalid entries"
            )

        if not isinstance(
            package_name,
            AndroidApkManifestValue,
        ):
            raise TypeError(
                "restored APK package name has invalid type"
            )

        for name, value in (
            (
                "version_code",
                version_code,
            ),
            (
                "version_name",
                version_name,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    AndroidApkManifestValue,
                )
            ):
                raise TypeError(
                    "restored APK "
                    f"{name} has invalid type"
                )

        if (
            overlay is not None
            and not isinstance(
                overlay,
                AndroidApkOverlayManifest,
            )
        ):
            raise TypeError(
                "restored APK overlay has invalid type"
            )

        #
        # ParsedAndroidApk.__post_init__ validates the complete restored
        # object graph:
        #
        #   * exact central-directory member ordering,
        #   * APK_MEMBER provenance,
        #   * exact AndroidApkSource parent object identity,
        #   * member index/name correspondence,
        #   * unique DEX identities.
        #
        # Do not rebuild or reconcile any of those relationships here.
        #
        return ParsedAndroidApk(
            source=source,
            members=members,
            dex_files=dex_files,
            package_name=package_name,
            version_code=version_code,
            version_name=version_name,
            overlay=overlay,
        )


class AndroidApkCandidateDispositionCodec:
    type_tag = "android.apk_candidate_disposition"
    python_type = AndroidApkCandidateDisposition

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidApkCandidateDisposition,
        ):
            raise TypeError(
                "value must be an "
                "AndroidApkCandidateDisposition"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "disposition": value.disposition,
            "parsed": _optional_ref(
                encoder,
                value.parsed,
            ),
            "reason": value.reason,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        parsed = _decode_optional_ref(
            decoder,
            payload["parsed"],
        )

        if not isinstance(
            source,
            AndroidApkSource,
        ):
            raise TypeError(
                "restored APK candidate source must be "
                "an AndroidApkSource"
            )

        if (
            parsed is not None
            and not isinstance(
                parsed,
                ParsedAndroidApk,
            )
        ):
            raise TypeError(
                "restored APK candidate parsed value must be "
                "a ParsedAndroidApk or None"
            )

        return AndroidApkCandidateDisposition(
            source=source,
            disposition=payload[
                "disposition"
            ],
            parsed=parsed,
            reason=payload[
                "reason"
            ],
        )


class AndroidApkParsingResultCodec:
    type_tag = "android.apk_parsing_result"
    python_type = AndroidApkParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidApkParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidApkParsingResult"
            )

        return {
            "packages": [
                encoder.ref(
                    package
                )
                for package
                in value.packages
            ],
            "candidates": [
                encoder.ref(
                    candidate
                )
                for candidate
                in value.candidates
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        packages = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload[
                "packages"
            ]
        )

        if not all(
            isinstance(
                package,
                ParsedAndroidApk,
            )
            for package
            in packages
        ):
            raise TypeError(
                "restored APK Parsing result contains "
                "invalid package entries"
            )

        candidates = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload[
                "candidates"
            ]
        )

        if not all(
            isinstance(
                candidate,
                AndroidApkCandidateDisposition,
            )
            for candidate
            in candidates
        ):
            raise TypeError(
                "restored APK Parsing result contains "
                "invalid candidate entries"
            )

        return AndroidApkParsingResult(
            packages=packages,
            candidates=candidates,
        )


# ---------------------------------------------------------------------------
# AVF VM configuration Parsing
# ---------------------------------------------------------------------------


class AndroidAvfVmConfigSourceCodec:
    type_tag = "android.avf.vm_config_source"
    python_type = AndroidAvfVmConfigSource

    def encode(
        self,
        value,
        encoder,
    ):
        if not isinstance(
            value,
            AndroidAvfVmConfigSource,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAvfVmConfigSource"
            )

        return {
            "filesystem_source": encoder.ref(
                value.filesystem_source
            ),
            "apk_android_path": (
                value.apk_android_path.as_posix()
            ),
            "apk_host_path": (
                value.apk_host_path.as_posix()
            ),
            "member_path": value.member_path,
            "member_index": value.member_index,
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        filesystem_source = decoder.ref(
            payload["filesystem_source"]
        )

        if not isinstance(
            filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "restored AVF filesystem source "
                "must be an AndroidParserFilesystemSource"
            )

        return AndroidAvfVmConfigSource(
            filesystem_source=filesystem_source,
            apk_android_path=PurePosixPath(
                payload["apk_android_path"]
            ),
            apk_host_path=Path(
                payload["apk_host_path"]
            ),
            member_path=payload["member_path"],
            member_index=payload["member_index"],
        )


class AndroidAvfVmConfigOsCodec:
    type_tag = "android.avf.vm_config_os"
    python_type = AndroidAvfVmConfigOs

    def encode(
        self,
        value,
        encoder,
    ):
        return {
            "name": value.name,
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        return AndroidAvfVmConfigOs(
            name=payload["name"],
        )


class AndroidAvfVmConfigTaskCodec:
    type_tag = "android.avf.vm_config_task"
    python_type = AndroidAvfVmConfigTask

    def encode(
        self,
        value,
        encoder,
    ):
        return {
            "task_type": value.task_type,
            "command": value.command,
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        return AndroidAvfVmConfigTask(
            task_type=payload["task_type"],
            command=payload["command"],
        )


class AndroidAvfVmConfigApexCodec:
    type_tag = "android.avf.vm_config_apex"
    python_type = AndroidAvfVmConfigApex

    def encode(
        self,
        value,
        encoder,
    ):
        return {
            "name": value.name,
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        return AndroidAvfVmConfigApex(
            name=payload["name"],
        )


class AndroidAvfVmConfigExtraApkCodec:
    type_tag = "android.avf.vm_config_extra_apk"
    python_type = AndroidAvfVmConfigExtraApk

    def encode(
        self,
        value,
        encoder,
    ):
        return {
            "path": value.path,
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        return AndroidAvfVmConfigExtraApk(
            path=payload["path"],
        )


class ParsedAndroidAvfVmConfigCodec:
    type_tag = "android.avf.vm_config"
    python_type = ParsedAndroidAvfVmConfig

    def encode(
        self,
        value,
        encoder,
    ):
        return {
            "source": encoder.ref(
                value.source
            ),
            "raw": _encode_bytes(
                value.raw
            ),
            "version": value.version,
            "os": encoder.ref(
                value.os
            ),
            "task": encoder.ref(
                value.task
            ),
            "prefer_staged": (
                value.prefer_staged
            ),
            "apexes": [
                encoder.ref(
                    item
                )
                for item
                in value.apexes
            ],
            "extra_apks": [
                encoder.ref(
                    item
                )
                for item
                in value.extra_apks
            ],
            "export_tombstones": (
                value.export_tombstones
            ),
            "enable_authfs": (
                value.enable_authfs
            ),
            "hugepages": (
                value.hugepages
            ),
            "unknown_fields": list(
                value.unknown_fields
            ),
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        source = decoder.ref(
            payload["source"]
        )
        os_value = decoder.ref(
            payload["os"]
        )
        task = decoder.ref(
            payload["task"]
        )

        apexes = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "apexes",
                [],
            )
        )

        extra_apks = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "extra_apks",
                [],
            )
        )

        if not isinstance(
            source,
            AndroidAvfVmConfigSource,
        ):
            raise TypeError(
                "restored AVF source has invalid type"
            )

        if not isinstance(
            os_value,
            AndroidAvfVmConfigOs,
        ):
            raise TypeError(
                "restored AVF OS has invalid type"
            )

        if not isinstance(
            task,
            AndroidAvfVmConfigTask,
        ):
            raise TypeError(
                "restored AVF task has invalid type"
            )

        return ParsedAndroidAvfVmConfig(
            source=source,
            raw=_decode_bytes(
                payload["raw"],
                field_name="AVF raw",
            ),
            version=payload.get(
                "version"
            ),
            os=os_value,
            task=task,
            prefer_staged=payload.get(
                "prefer_staged"
            ),
            apexes=apexes,
            extra_apks=extra_apks,
            export_tombstones=payload.get(
                "export_tombstones"
            ),
            enable_authfs=payload.get(
                "enable_authfs"
            ),
            hugepages=payload.get(
                "hugepages"
            ),
            unknown_fields=tuple(
                payload.get(
                    "unknown_fields",
                    [],
                )
            ),
        )


class AndroidAvfVmConfigCandidateDispositionCodec:
    type_tag = "android.avf.vm_config_candidate_disposition"
    python_type = AndroidAvfVmConfigCandidateDisposition

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidAvfVmConfigCandidateDisposition,
        ):
            raise TypeError(
                "value must be an "
                "AndroidAvfVmConfigCandidateDisposition"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "raw": _encode_bytes(
                value.raw
            ),
            "disposition": value.disposition,
            "parsed": _optional_ref(
                encoder,
                value.parsed,
            ),
            "reason": value.reason,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload["source"]
        )

        parsed = _decode_optional_ref(
            decoder,
            payload["parsed"],
        )

        if not isinstance(
            source,
            AndroidAvfVmConfigSource,
        ):
            raise TypeError(
                "restored AVF candidate source must be "
                "an AndroidAvfVmConfigSource"
            )

        if (
            parsed is not None
            and not isinstance(
                parsed,
                ParsedAndroidAvfVmConfig,
            )
        ):
            raise TypeError(
                "restored AVF candidate parsed value must be "
                "a ParsedAndroidAvfVmConfig or None"
            )

        return AndroidAvfVmConfigCandidateDisposition(
            source=source,
            raw=_decode_bytes(
                payload["raw"],
                field_name=(
                    "AVF candidate raw"
                ),
            ),
            disposition=payload[
                "disposition"
            ],
            parsed=parsed,
            reason=payload[
                "reason"
            ],
        )


class AndroidAvfVmConfigParsingResultCodec:
    type_tag = "android.avf.vm_config_result"
    python_type = AndroidAvfVmConfigParsingResult

    def encode(
        self,
        value,
        encoder,
    ):
        return {
            "configurations": [
                encoder.ref(
                    item
                )
                for item
                in value.configurations
            ],
            "candidates": [
                encoder.ref(
                    item
                )
                for item
                in value.candidates
            ],
        }

    def decode(
        self,
        payload,
        decoder,
    ):
        configurations = tuple(
            decoder.ref(ref)
            for ref
            in payload[
                "configurations"
            ]
        )

        if not all(
            isinstance(
                item,
                ParsedAndroidAvfVmConfig,
            )
            for item
            in configurations
        ):
            raise TypeError(
                "restored AVF result contains "
                "invalid configurations"
            )

        candidates = tuple(
            decoder.ref(
                reference
            )
            for reference
            in payload[
                "candidates"
            ]
        )

        if not all(
            isinstance(
                item,
                AndroidAvfVmConfigCandidateDisposition,
            )
            for item
            in candidates
        ):
            raise TypeError(
                "restored AVF result contains "
                "invalid candidate dispositions"
            )

        return AndroidAvfVmConfigParsingResult(
            configurations=configurations,
            candidates=candidates,
        )


# ---------------------------------------------------------------------------
# Kernel-module Parsing
# ---------------------------------------------------------------------------


class ParsedAndroidKernelModuleInfoEntryCodec:
    type_tag = "android.kernel_module.modinfo_entry"
    python_type = ParsedAndroidKernelModuleInfoEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidKernelModuleInfoEntry,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidKernelModuleInfoEntry"
            )

        return {
            "index": value.index,
            "byte_offset": value.byte_offset,
            "raw": value.raw,
            "key": value.key,
            "value": value.value,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidKernelModuleInfoEntry(
            index=payload[
                "index"
            ],
            byte_offset=payload[
                "byte_offset"
            ],
            raw=payload[
                "raw"
            ],
            key=payload.get(
                "key"
            ),
            value=payload.get(
                "value"
            ),
        )


class ParsedAndroidKernelModuleCodec:
    type_tag = "android.kernel_module.module"
    python_type = ParsedAndroidKernelModule

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidKernelModule,
        ):
            raise TypeError(
                "value must be a ParsedAndroidKernelModule"
            )

        return {
            "elf": encoder.ref(
                value.elf
            ),
            "modinfo_section_offset": (
                value.modinfo_section_offset
            ),
            "modinfo_section_size": (
                value.modinfo_section_size
            ),
            "modinfo_entries": [
                encoder.ref(
                    entry
                )
                for entry
                in value.modinfo_entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        elf = decoder.ref(
            payload[
                "elf"
            ]
        )

        if not isinstance(
            elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "restored kernel-module ELF must be "
                "a ParsedAndroidElf"
            )

        entries = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "modinfo_entries",
                [],
            )
        )

        if not all(
            isinstance(
                entry,
                ParsedAndroidKernelModuleInfoEntry,
            )
            for entry
            in entries
        ):
            raise TypeError(
                "restored modinfo entries must contain only "
                "ParsedAndroidKernelModuleInfoEntry objects"
            )

        return ParsedAndroidKernelModule(
            elf=elf,
            modinfo_section_offset=payload.get(
                "modinfo_section_offset"
            ),
            modinfo_section_size=payload[
                "modinfo_section_size"
            ],
            modinfo_entries=entries,
        )


class AndroidKernelModuleParsingResultCodec:
    type_tag = "android.kernel_module.result"
    python_type = AndroidKernelModuleParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidKernelModuleParsingResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidKernelModuleParsingResult"
            )

        return {
            "modules": [
                encoder.ref(
                    module
                )
                for module
                in value.modules
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        modules = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "modules",
                [],
            )
        )

        if not all(
            isinstance(
                module,
                ParsedAndroidKernelModule,
            )
            for module
            in modules
        ):
            raise TypeError(
                "restored kernel-module result contains "
                "invalid module entries"
            )

        return AndroidKernelModuleParsingResult(
            modules=modules,
        )


class AndroidKernelModuleConfigurationLineCodec:
    type_tag = "android.kernel_module.configuration_line"
    python_type = AndroidKernelModuleConfigurationLine

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidKernelModuleConfigurationLine,
        ):
            raise TypeError(
                "value must be an "
                "AndroidKernelModuleConfigurationLine"
            )

        return {
            "raw": value.raw,
            "content": value.content,
            "tokens": list(
                value.tokens
            ),
            "source_line": value.source_line,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        tokens = payload[
            "tokens"
        ]

        if not isinstance(
            tokens,
            list,
        ):
            raise TypeError(
                "restored kernel-module configuration "
                "tokens must be a list"
            )

        return AndroidKernelModuleConfigurationLine(
            raw=payload[
                "raw"
            ],
            content=payload[
                "content"
            ],
            tokens=tuple(
                tokens
            ),
            source_line=payload[
                "source_line"
            ],
        )


class ParsedAndroidKernelModuleConfigurationCodec:
    type_tag = "android.kernel_module.configuration"
    python_type = ParsedAndroidKernelModuleConfiguration

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidKernelModuleConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidKernelModuleConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "configuration_kind": (
                value.configuration_kind.value
            ),
            "raw": value.raw,
            "lines": [
                encoder.ref(
                    line
                )
                for line
                in value.lines
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        source = decoder.ref(
            payload[
                "source"
            ]
        )

        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "restored kernel-module configuration source "
                "must be an AndroidModelSource"
            )

        lines = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "lines",
                [],
            )
        )

        if not all(
            isinstance(
                line,
                AndroidKernelModuleConfigurationLine,
            )
            for line
            in lines
        ):
            raise TypeError(
                "restored kernel-module configuration contains "
                "invalid line entries"
            )

        return ParsedAndroidKernelModuleConfiguration(
            source=source,
            configuration_kind=(
                AndroidKernelModuleConfigurationKind(
                    payload[
                        "configuration_kind"
                    ]
                )
            ),
            raw=payload[
                "raw"
            ],
            lines=lines,
        )



# ---------------------------------------------------------------------------
# Ramdisk / CPIO Parsing
# ---------------------------------------------------------------------------


class CpioNewcEntryCodec:
    type_tag = "android.cpio.newc_entry"
    python_type = CpioNewcEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            CpioNewcEntry,
        ):
            raise TypeError(
                "value must be a CpioNewcEntry"
            )

        return {
            "path": value.path,
            "ino": value.ino,
            "mode": value.mode,
            "uid": value.uid,
            "gid": value.gid,
            "nlink": value.nlink,
            "mtime": value.mtime,
            "filesize": value.filesize,
            "devmajor": value.devmajor,
            "devminor": value.devminor,
            "rdevmajor": value.rdevmajor,
            "rdevminor": value.rdevminor,
            "namesize": value.namesize,
            "check": value.check,
            "data": base64.b64encode(
                value.data
            ).decode(
                "ascii"
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> CpioNewcEntry:
        return CpioNewcEntry(
            path=payload["path"],
            ino=payload["ino"],
            mode=payload["mode"],
            uid=payload["uid"],
            gid=payload["gid"],
            nlink=payload["nlink"],
            mtime=payload["mtime"],
            filesize=payload["filesize"],
            devmajor=payload["devmajor"],
            devminor=payload["devminor"],
            rdevmajor=payload["rdevmajor"],
            rdevminor=payload["rdevminor"],
            namesize=payload["namesize"],
            check=payload["check"],
            data=base64.b64decode(
                payload["data"].encode(
                    "ascii"
                )
            ),
        )


class CpioExtractionResultCodec:
    type_tag = "android.cpio.extraction_result"
    python_type = CpioExtractionResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            CpioExtractionResult,
        ):
            raise TypeError(
                "value must be a CpioExtractionResult"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "entries": [
                encoder.ref(
                    entry
                )
                for entry
                in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> CpioExtractionResult:
        return CpioExtractionResult(
            artifact=decoder.ref(
                payload[
                    "artifact"
                ]
            ),
            entries=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "entries"
                ]
            ),
        )


class ParsedAndroidRamdiskCodec:
    type_tag = "android.ramdisk.parsed"
    python_type = ParsedAndroidRamdisk

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidRamdisk,
        ):
            raise TypeError(
                "value must be a ParsedAndroidRamdisk"
            )

        return {
            "cpio": encoder.ref(
                value.cpio
            ),
            "boot_image_artifact": encoder.ref(
                value.boot_image_artifact
            ),
            "ramdisk_component": encoder.ref(
                value.ramdisk_component
            ),
            "ramdisk_cpio": encoder.ref(
                value.ramdisk_cpio
            ),
            "ramdisk_root": encoder.ref(
                value.ramdisk_root
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> ParsedAndroidRamdisk:
        return ParsedAndroidRamdisk(
            cpio=decoder.ref(
                payload[
                    "cpio"
                ]
            ),
            boot_image_artifact=decoder.ref(
                payload[
                    "boot_image_artifact"
                ]
            ),
            ramdisk_component=decoder.ref(
                payload[
                    "ramdisk_component"
                ]
            ),
            ramdisk_cpio=decoder.ref(
                payload[
                    "ramdisk_cpio"
                ]
            ),
            ramdisk_root=decoder.ref(
                payload[
                    "ramdisk_root"
                ]
            ),
        )


class ParsedVendorRamdiskTableEntryCodec:
    type_tag = (
        "android.parsed.vendor_ramdisk_table_entry"
    )
    python_type = ParsedVendorRamdiskTableEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedVendorRamdiskTableEntry,
        ):
            raise TypeError(
                "value must be a "
                "ParsedVendorRamdiskTableEntry"
            )

        return {
            "index": value.index,
            "ramdisk_size": (
                value.ramdisk_size
            ),
            "ramdisk_offset": (
                value.ramdisk_offset
            ),
            "ramdisk_type": (
                value.ramdisk_type
            ),
            "ramdisk_name": (
                value.ramdisk_name
            ),
            "board_id": list(
                value.board_id
            ),
            "raw": (
                base64.b64encode(
                    value.raw
                ).decode(
                    "ascii"
                )
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedVendorRamdiskTableEntry(
            index=int(
                payload[
                    "index"
                ]
            ),
            ramdisk_size=int(
                payload[
                    "ramdisk_size"
                ]
            ),
            ramdisk_offset=int(
                payload[
                    "ramdisk_offset"
                ]
            ),
            ramdisk_type=int(
                payload[
                    "ramdisk_type"
                ]
            ),
            ramdisk_name=str(
                payload[
                    "ramdisk_name"
                ]
            ),
            board_id=tuple(
                int(
                    value
                )
                for value
                in payload[
                    "board_id"
                ]
            ),
            raw=base64.b64decode(
                payload[
                    "raw"
                ]
            ),
        )


class ParsedVendorRamdiskTableCodec:
    type_tag = (
        "android.parsed.vendor_ramdisk_table"
    )
    python_type = ParsedVendorRamdiskTable

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedVendorRamdiskTable,
        ):
            raise TypeError(
                "value must be a ParsedVendorRamdiskTable"
            )

        return {
            "artifact": encoder.ref(
                value.artifact
            ),
            "boot_image_artifact": encoder.ref(
                value.boot_image_artifact
            ),
            "entry_size": (
                value.entry_size
            ),
            "entries": [
                encoder.ref(
                    entry
                )
                for entry
                in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedVendorRamdiskTable(
            artifact=decoder.ref(
                payload[
                    "artifact"
                ]
            ),
            boot_image_artifact=decoder.ref(
                payload[
                    "boot_image_artifact"
                ]
            ),
            entry_size=int(
                payload[
                    "entry_size"
                ]
            ),
            entries=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "entries"
                ]
            ),
        )


# ---------------------------------------------------------------------------
# AndroidParsingResult aggregate
# ---------------------------------------------------------------------------


class AndroidParsingResultCodec:
    type_tag = "android.parsing_result"
    python_type = AndroidParsingResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParsingResult,
        ):
            raise TypeError(
                "value must be an AndroidParsingResult"
            )

        return {
            "filesystem_inventory": encoder.ref(
                value.filesystem_inventory
            ),
            "source_inventory": encoder.ref(
                value.source_inventory
            ),
            "filesystem": encoder.ref(
                value.filesystem
            ),
            "elf": encoder.ref(
                value.elf
            ),
            "art_runtime": encoder.ref(
                value.art_runtime
            ),
            "dex": encoder.ref(
                value.dex
            ),
            "classpath": encoder.ref(
                value.classpath
            ),
            "aconfig": encoder.ref(
                value.aconfig
            ),
            "input": encoder.ref(
                value.input
            ),
            "font": encoder.ref(
                value.font
            ),
            "java_archive": encoder.ref(
                value.java_archive
            ),
            "shell_script": encoder.ref(
                value.shell_script
            ),
            "certificate": encoder.ref(
                value.certificate
            ),
            "structured_configuration": encoder.ref(
                value.structured_configuration
            ),
            "apk": encoder.ref(
                value.apk
            ),
            "avf_vm_config": encoder.ref(
                value.avf_vm_config
            ),
            "kernel_modules": encoder.ref(
                value.kernel_modules
            ),
            "kernel_module_configurations": [
                encoder.ref(
                    item
                )
                for item
                in value.kernel_module_configurations
            ],
            "linker_configurations": [
                encoder.ref(
                    item
                )
                for item
                in value.linker_configurations
            ],
            "linker_protobuf_configurations": [
                encoder.ref(
                    item
                )
                for item
                in value.linker_protobuf_configurations
            ],
            "native_library_configurations": [
                encoder.ref(
                    item
                )
                for item
                in value.native_library_configurations
            ],
            "apex": [
                encoder.ref(
                    item
                )
                for item in value.apex
            ],
            "bmp": [
                encoder.ref(
                    item
                )
                for item in value.bmp
            ],
            "sflb": [
                encoder.ref(
                    item
                )
                for item in value.sflb
            ],
            "dtbo": [
                encoder.ref(
                    item
                )
                for item in value.dtbo
            ],
            "boot_dtbs": [
                encoder.ref(
                    item
                )
                for item
                in value.boot_dtbs
            ],
            "vendor_ramdisk_tables": [
                encoder.ref(
                    item
                )
                for item
                in value.vendor_ramdisk_tables
            ],
            "vbmeta": [
                encoder.ref(
                    item
                )
                for item
                in value.vbmeta
            ],
            "avb_regions": [
                encoder.ref(
                    item
                )
                for item
                in value.avb_regions
            ],
            "bootloader": [
                encoder.ref(
                    item
                )
                for item
                in value.bootloader
            ],
            "bootloader_children": [
                encoder.ref(
                    item
                )
                for item
                in value.bootloader_children
            ],
            "ramdisks": [
                encoder.ref(
                    ramdisk
                )
                for ramdisk
                in value.ramdisks
            ],
            "kernels": [
                encoder.ref(
                    item
                )
                for item
                in value.kernels
            ],
            "boot_images": [
                encoder.ref(
                    item
                )
                for item
                in value.boot_images
            ],
            "boot_signatures": [
                encoder.ref(
                    item
                )
                for item
                in value.boot_signatures
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        filesystem_inventory = decoder.ref(
            payload[
                "filesystem_inventory"
            ]
        )
        source_inventory = decoder.ref(
            payload[
                "source_inventory"
            ]
        )
        filesystem = decoder.ref(
            payload[
                "filesystem"
            ]
        )
        elf = decoder.ref(
            payload[
                "elf"
            ]
        )

        art_runtime = decoder.ref(
            payload[
                "art_runtime"
            ]
        )

        dex_ref = payload.get(
            "dex"
        )

        dex = (
            decoder.ref(
                dex_ref
            )
            if dex_ref is not None
            else AndroidStandaloneDexParsingResult()
        )

        classpath = decoder.ref(
            payload[
                "classpath"
            ]
        )

        aconfig = decoder.ref(
            payload[
                "aconfig"
            ]
        )

        input_result = decoder.ref(
            payload[
                "input"
            ]
        )

        font = decoder.ref(
            payload[
                "font"
            ]
        )

        java_archive = decoder.ref(
            payload[
                "java_archive"
            ]
        )

        shell_script_ref = payload.get(
            "shell_script"
        )

        shell_script = (
            decoder.ref(
                shell_script_ref
            )
            if shell_script_ref is not None
            else AndroidShellScriptParsingResult()
        )

        certificate = decoder.ref(
            payload[
                "certificate"
            ]
        )

        structured_configuration_ref = (
            payload.get(
                "structured_configuration"
            )
        )

        if structured_configuration_ref is None:
            structured_configuration = (
                AndroidStructuredConfigurationParsingResult()
            )
        else:
            structured_configuration = decoder.ref(
                structured_configuration_ref
            )

            if not isinstance(
                structured_configuration,
                AndroidStructuredConfigurationParsingResult,
            ):
                raise TypeError(
                    "restored structured_configuration "
                    "must be an "
                    "AndroidStructuredConfigurationParsingResult"
                )

        apk = decoder.ref(
            payload[
                "apk"
            ]
        )

        avf_vm_config = decoder.ref(
            payload[
                "avf_vm_config"
            ]
        )

        kernel_modules = decoder.ref(
            payload[
                "kernel_modules"
            ]
        )

        kernel_module_configurations = tuple(
            decoder.ref(
                ref
            )
            for ref
            in payload.get(
                "kernel_module_configurations",
                [],
            )
        )

        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "restored source_inventory must be an "
                "AndroidModelSourceInventory"
            )

        if not isinstance(
            filesystem,
            AndroidFilesystemParsingResult,
        ):
            raise TypeError(
                "restored filesystem must be an "
                "AndroidFilesystemParsingResult"
            )

        if not isinstance(
            elf,
            AndroidElfParsingResult,
        ):
            raise TypeError(
                "restored elf must be an AndroidElfParsingResult"
            )

        if not isinstance(
            art_runtime,
            AndroidArtRuntimeParsingResult,
        ):
            raise TypeError(
                "restored art_runtime must be an "
                "AndroidArtRuntimeParsingResult"
            )

        if not isinstance(
            dex,
            AndroidStandaloneDexParsingResult,
        ):
            raise TypeError(
                "restored dex must be an "
                "AndroidStandaloneDexParsingResult"
            )

        if not isinstance(
            classpath,
            AndroidClasspathParsingResult,
        ):
            raise TypeError(
                "restored classpath must be an "
                "AndroidClasspathParsingResult"
            )

        if not isinstance(
            aconfig,
            AndroidAconfigParsingResult,
        ):
            raise TypeError(
                "restored aconfig must be an "
                "AndroidAconfigParsingResult"
            )

        if not isinstance(
            input_result,
            AndroidInputParsingResult,
        ):
            raise TypeError(
                "restored input must be an "
                "AndroidInputParsingResult"
            )

        if not isinstance(
            font,
            AndroidFontParsingResult,
        ):
            raise TypeError(
                "restored font must be an "
                "AndroidFontParsingResult"
            )

        if not isinstance(
            java_archive,
            AndroidJavaArchiveParsingResult,
        ):
            raise TypeError(
                "restored java_archive must be an "
                "AndroidJavaArchiveParsingResult"
            )

        if not isinstance(
            shell_script,
            AndroidShellScriptParsingResult,
        ):
            raise TypeError(
                "restored shell_script must be an "
                "AndroidShellScriptParsingResult"
            )

        if not isinstance(
            certificate,
            AndroidCertificateParsingResult,
        ):
            raise TypeError(
                "restored certificate must be an "
                "AndroidCertificateParsingResult"
            )

        if not isinstance(
            apk,
            AndroidApkParsingResult,
        ):
            raise TypeError(
                "restored apk must be an "
                "AndroidApkParsingResult"
            )

        if not isinstance(
            avf_vm_config,
            AndroidAvfVmConfigParsingResult,
        ):
            raise TypeError(
                "restored avf_vm_config must be an "
                "AndroidAvfVmConfigParsingResult"
            )

        if not isinstance(
            kernel_modules,
            AndroidKernelModuleParsingResult,
        ):
            raise TypeError(
                "restored kernel_modules must be an "
                "AndroidKernelModuleParsingResult"
            )

        if not all(
            isinstance(
                item,
                ParsedAndroidKernelModuleConfiguration,
            )
            for item
            in kernel_module_configurations
        ):
            raise TypeError(
                "restored kernel_module_configurations contain "
                "invalid entries"
            )

        return AndroidParsingResult(
            filesystem_inventory=filesystem_inventory,
            source_inventory=source_inventory,
            filesystem=filesystem,
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
            linker_configurations=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "linker_configurations"
                ]
            ),
            linker_protobuf_configurations=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "linker_protobuf_configurations"
                ]
            ),
            native_library_configurations=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "native_library_configurations"
                ]
            ),
            apex=tuple(
                decoder.ref(
                    ref
                )
                for ref in payload[
                    "apex"
                ]
            ),
            bmp=tuple(
                decoder.ref(
                    ref
                )
                for ref in payload[
                    "bmp"
                ]
            ),
            sflb=tuple(
                decoder.ref(
                    ref
                )
                for ref in payload[
                    "sflb"
                ]
            ),
            dtbo=tuple(
                decoder.ref(
                    ref
                )
                for ref in payload[
                    "dtbo"
                ]
            ),
            boot_dtbs=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "boot_dtbs",
                    [],
                )
            ),
            vendor_ramdisk_tables=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "vendor_ramdisk_tables",
                    [],
                )
            ),
            vbmeta=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "vbmeta"
                ]
            ),
            avb_regions=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "avb_regions"
                ]
            ),
            bootloader=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "bootloader"
                ]
            ),
            bootloader_children=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "bootloader_children"
                ]
            ),
            ramdisks=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "ramdisks"
                ]
            ),
            kernels=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "kernels"
                ]
            ),
            boot_images=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload[
                    "boot_images"
                ]
            ),
            boot_signatures=tuple(
                decoder.ref(
                    ref
                )
                for ref
                in payload.get(
                    "boot_signatures",
                    [],
                )
            ),
        )


PARSING_RESULT_CODECS = (
    *STRUCTURED_CONFIGURATION_CODECS,
    CpioNewcEntryCodec(),
    CpioExtractionResultCodec(),
    ParsedAndroidRamdiskCodec(),
    AndroidLinkerConfigurationSectionCodec(),
    AndroidLinkerConfigurationAssignmentCodec(),
    AndroidLinkerConfigurationUnparsedLineCodec(),
    ParsedAndroidLinkerConfigurationCodec(),
    AndroidLinkerProtobufUnknownFieldCodec(),
    AndroidLinkerProtobufContributionCodec(),
    ParsedAndroidLinkerProtobufConfigurationCodec(),
    AndroidNativeLibraryConfigurationDeclarationCodec(),
    ParsedAndroidNativeLibraryConfigurationCodec(),
    ParsedAndroidElfSourceCodec(),
    ParsedAndroidElfCodec(),
    AndroidElfParsingResultCodec(),
    AndroidDexHeaderCodec(),
    AndroidDexSourceCodec(),
    ParsedAndroidDexCodec(),
    AndroidStandaloneDexDispositionCodec(),
    AndroidStandaloneDexParsingResultCodec(),
    ParsedAndroidOatKeyValueCodec(),
    ParsedAndroidDexLayoutSubsectionCodec(),
    ParsedAndroidDexLayoutSectionCodec(),
    ParsedAndroidDexLayoutSectionsCodec(),
    ParsedAndroidIndexBssMappingEntryCodec(),
    ParsedAndroidIndexBssMappingCodec(),
    ParsedAndroidBcpBssMappingInfoCodec(),
    ParsedAndroidBcpBssInfoCodec(),
    ParsedAndroidOatDexFileCodec(),
    ParsedAndroidOatStructuralHeaderCodec(),
    ParsedAndroidOatCodec(),
    ParsedAndroidVdexSectionCodec(),
    ParsedAndroidVdex027Codec(),
    ParsedAndroidVdexCodec(),
    ParsedAndroidArtImageSectionCodec(),
    ParsedAndroidArtImage111Codec(),
    ParsedAndroidArtImageCodec(),
    AndroidArtRuntimeParsingResultCodec(),
    AndroidClasspathProtobufUnknownFieldCodec(),
    AndroidClasspathJarCodec(),
    ParsedAndroidClasspathConfigurationCodec(),
    AndroidClasspathParsingResultCodec(),
    AndroidAconfigProtobufUnknownFieldCodec(),
    AndroidAconfigFlagMetadataCodec(),
    AndroidAconfigTracepointCodec(),
    AndroidAconfigParsedFlagCodec(),
    ParsedAndroidAconfigConfigurationCodec(),
    AndroidAconfigParsingResultCodec(),
    AndroidInputParsingResultCodec(),
    AndroidFontParsingResultCodec(),
    AndroidJavaArchiveParsingResultCodec(),
    AndroidShellScriptParsingResultCodec(),
    AndroidCertificateParsingResultCodec(),
    AndroidApkSourceCodec(),
    AndroidApkArchiveMemberCodec(),
    AndroidApkManifestValueCodec(),
    AndroidApkOverlayManifestCodec(),
    ParsedAndroidApkCodec(),
    AndroidApkCandidateDispositionCodec(),
    AndroidApkParsingResultCodec(),
    AndroidAvfVmConfigSourceCodec(),
    AndroidAvfVmConfigOsCodec(),
    AndroidAvfVmConfigTaskCodec(),
    AndroidAvfVmConfigApexCodec(),
    AndroidAvfVmConfigExtraApkCodec(),
    ParsedAndroidAvfVmConfigCodec(),
    AndroidAvfVmConfigCandidateDispositionCodec(),
    AndroidAvfVmConfigParsingResultCodec(),
    ParsedAndroidKernelModuleInfoEntryCodec(),
    ParsedAndroidKernelModuleCodec(),
    AndroidKernelModuleParsingResultCodec(),
    AndroidKernelModuleConfigurationLineCodec(),
    ParsedAndroidKernelModuleConfigurationCodec(),
    AndroidParsedApexCodec(),
    ParsedApexContainerCodec(),
    AndroidParsedBmpCodec(),
    AndroidParsedSflbEntryCodec(),
    ParsedFdtPropertyCodec(),
    ParsedFdtNodeCodec(),
    ParsedFdtCodec(),
    ParsedVendorRamdiskTableEntryCodec(),
    ParsedVendorRamdiskTableCodec(),
    ParsedDtboOverlayMetadataCodec(),
    AndroidParsedDtboEntryCodec(),
    ParsedAvbVbmetaCodec(),
    ParsedAvbRegionCodec(),
    ParsedBootloaderChildCodec(),
    ParsedBootloaderChildDispositionCodec(),
    ParsedKernelImageCodec(),
    ParsedBootSignatureCodec(),
    ParsedBootImageCodec(),
    AndroidParsingResultCodec(),
)
