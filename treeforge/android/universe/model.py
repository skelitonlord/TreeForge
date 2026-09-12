from __future__ import annotations

from treeforge.android.universe.avb.boot_signature import (
    AndroidUniverseBootSignatureAvbRequirement,
)
from treeforge.android.universe.boot.population import (
    AndroidUniverseBootPopulationReconciliation,
)
from treeforge.android.universe.bootloader.population import (
    AndroidUniverseBootloaderPopulationReconciliation,
)

from treeforge.android.universe.fstab.source_context import (
    AndroidUniverseFstabSourceContext,
)

from dataclasses import dataclass, field

from treeforge.android.knowledge import (
    AndroidKnowledgeResolutionResult,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)

from treeforge.android.universe.parsing_boundary import (
    AndroidUniverseParsingBoundary,
)
from treeforge.android.universe.avb import (
    AndroidUniverseAvbRegion,
    AndroidUniverseAvbTopology,
    AndroidUniverseVbmetaRequirement,
)
from treeforge.android.universe.architecture import (
    AndroidUniverseArchitecture,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.filesystem_entry import (
    AndroidUniverseFilesystemEntryRequirementInventory,
)
from treeforge.android.universe.model_source import (
    AndroidUniverseModelSourceRequirementInventory,
)
from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)
from treeforge.android.universe.properties.source_record import (
    AndroidUniversePropertySourceRecord,
)
from treeforge.android.universe.runtime_property.relevance import (
    AndroidUniverseRuntimePropertyRelevance,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)
from treeforge.android.universe.fstab.model import (
    AndroidUniverseFstabRequirement,
)
from treeforge.android.universe.fstab.applicability import (
    AndroidUniverseFstabApplicabilityObservation,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.properties.conclusion import (
    AndroidUniverseFactConclusion,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceResolution,
)
from treeforge.android.universe.init.import_requirement import (
    AndroidUniverseInitImportRequirement,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportResolution,
)
from treeforge.android.universe.init.source_applicability import (
    AndroidUniverseInitSourceApplicability,
)
from treeforge.android.universe.init.source_record import (
    AndroidUniverseInitSourceRecord,
)
from treeforge.android.universe.ueventd.source_context import (
    AndroidUniverseUeventdSourceContext,
)
from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdRequirement,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)
from treeforge.android.universe.vintf.applicability import (
    AndroidUniverseVintfApplicability,
)
from treeforge.android.universe.boot.requirement import (
    AndroidUniverseBootRequirement,
)
from treeforge.android.universe.aconfig.requirement import (
    AndroidUniverseAconfigRequirement,
)
from treeforge.android.universe.input import (
    AndroidUniverseInputRequirement,
)
from treeforge.android.universe.font import (
    AndroidUniverseFontRequirement,
)
from treeforge.android.universe.certificate import (
    AndroidUniverseCertificateRequirement,
)
from treeforge.android.universe.structured_configuration import (
    AndroidUniverseStructuredConfigurationRequirement,
)
from treeforge.android.universe.dex import (
    AndroidUniverseStandaloneDexPopulationRequirement,
)
from treeforge.android.universe.avf import (
    AndroidUniverseAvfRequirement,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathRequirement,
)
from treeforge.android.universe.shell_script import (
    AndroidUniverseShellScriptReconciliation,
)
from treeforge.android.universe.art_runtime.requirement import (
    AndroidUniverseArtRuntimeRequirement,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleRequirement,
)
from treeforge.android.universe.kernel_module.elf_association import (
    AndroidUniverseKernelModuleElfAssociation,
)
from treeforge.android.universe.linker.requirement import (
    AndroidUniverseLinkerRequirement,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.universe.elf.artifact_association import (
    AndroidUniverseElfArtifactAssociation,
)
from treeforge.android.universe.kernel.requirement import (
    AndroidUniverseKernelRequirement,
)
from treeforge.android.universe.dtbo.requirement import (
    AndroidUniverseDtboRequirement,
)
from treeforge.android.universe.dtbo.population import (
    AndroidUniverseDtboPopulationReconciliation,
)
from treeforge.android.universe.bootloader import (
    AndroidUniverseBootloaderRequirement,
)
from treeforge.android.universe.sflb import (
    AndroidUniverseSflbRequirement,
)
from treeforge.android.universe.bmp import (
    AndroidUniverseBmpRequirement,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)
from treeforge.android.universe.selinux.policy_graph import (
    AndroidUniverseSelinuxPolicyGraph,
)
from treeforge.android.universe.selinux.conclusion import (
    AndroidUniverseSelinuxConclusion,
)
from treeforge.android.universe.relationships import (
    ANDROID_UNIVERSE_CROSS_FAMILY_RELATIONSHIP_TYPES,
    AndroidUniverseCrossFamilyRelationship,
    AndroidUniverseInitServiceSubstantiation,
    AndroidUniverseInitServiceTargetSubstantiation,
    AndroidUniverseLinkerApexContextApplicability,
    AndroidUniverseLinkerApexNativeLibraryConclusion,
    AndroidUniverseLinkerApexRelationship,
    AndroidUniverseLinkerElfContext,
)

from treeforge.android.universe.capability import (
    AndroidUniverseDeviceCapabilityConclusion,
)

from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerApexPublicLibraryConclusion,
    AndroidUniverseLinkerApexNamespaceInput,
)

from treeforge.android.universe.ueventd.reconciliation import (
    AndroidUniverseUeventdReconciliation,
)

@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceUniverse:
    """
    Canonical immutable result of Android Device Universe interpretation.

    Universe owns the complete semantic interpretation of canonical Android
    Parsing observations into device-level facts and requirements.

    The exact Parsing and Knowledge inputs are retained so every future
    Universe conclusion can preserve its complete upstream evidence chain.

    Downstream stages must consume Universe rather than independently
    reinterpret Parsing observations.
    """

    parsing: AndroidParsingResult

    parsing_boundary: AndroidUniverseParsingBoundary

    knowledge_resolution: (
        AndroidKnowledgeResolutionResult
        | None
    ) = None

    artifact_requirements: (
        AndroidUniverseArtifactRequirementInventory
        | None
    ) = None

    filesystem_entry_requirements: (
        AndroidUniverseFilesystemEntryRequirementInventory
    ) = field(
        kw_only=True,
    )

    model_source_requirements: (
        AndroidUniverseModelSourceRequirementInventory
    ) = field(
        kw_only=True,
    )

    property_source_records: tuple[
        AndroidUniversePropertySourceRecord,
        ...,
    ] = ()

    property_evidence: tuple[
        AndroidUniversePropertyEvidence,
        ...,
    ] = ()

    architecture: (
        AndroidUniverseArchitecture
        | None
    ) = None

    runtime_property_requirements: tuple[
        AndroidUniverseRuntimePropertyRequirement,
        ...,
    ] = ()

    runtime_property_relevance: tuple[
        AndroidUniverseRuntimePropertyRelevance,
        ...,
    ] = ()

    conclusions: tuple[
        AndroidUniverseFactConclusion,
        ...,
    ] = ()

    fstab_requirements: tuple[
        AndroidUniverseFstabRequirement,
        ...,
    ] = ()

    fstab_source_contexts: tuple[
        AndroidUniverseFstabSourceContext,
        ...,
    ] = ()

    ueventd_requirements: tuple[
        AndroidUniverseUeventdRequirement,
        ...,
    ] = ()

    ueventd_source_contexts: tuple[
        AndroidUniverseUeventdSourceContext,
        ...,
    ] = ()

    ueventd_reconciliation: AndroidUniverseUeventdReconciliation = field(
        kw_only=True,
    )

    vintf_requirements: tuple[
        AndroidUniverseVintfDocumentRequirement,
        ...,
    ] = ()

    vintf_applicability: (
        AndroidUniverseVintfApplicability
        | None
    ) = None

    device_capabilities: tuple[
        AndroidUniverseDeviceCapabilityConclusion,
        ...,
    ] = ()

    selinux_requirements: tuple[
        AndroidUniverseSelinuxSourceRequirement,
        ...,
    ] = ()

    selinux_policy_graph: (
        AndroidUniverseSelinuxPolicyGraph
        | None
    ) = None

    selinux_conclusions: tuple[
        AndroidUniverseSelinuxConclusion,
        ...,
    ] = ()

    selinux_applicability: tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ] = ()

    cross_family_relationships: tuple[
        AndroidUniverseCrossFamilyRelationship,
        ...,
    ] = ()


    cross_family_relationship_applicability: tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ] = ()

    linker_apex_context_applicability: tuple[
        AndroidUniverseLinkerApexContextApplicability,
        ...,
    ] = ()

    linker_apex_namespace_inputs: tuple[
        AndroidUniverseLinkerApexNamespaceInput,
        ...,
    ] = ()

    linker_apex_public_library_conclusions: tuple[
        AndroidUniverseLinkerApexPublicLibraryConclusion,
        ...,
    ] = ()

    linker_apex_native_library_conclusions: tuple[
        AndroidUniverseLinkerApexNativeLibraryConclusion,
        ...,
    ] = ()

    linker_elf_contexts: tuple[
        AndroidUniverseLinkerElfContext,
        ...,
    ] = ()

    init_service_substantiations: tuple[
        AndroidUniverseInitServiceSubstantiation,
        ...,
    ] = ()

    init_service_target_substantiations: tuple[
        AndroidUniverseInitServiceTargetSubstantiation,
        ...,
    ] = ()

    boot_requirements: tuple[
        AndroidUniverseBootRequirement,
        ...,
    ] = ()

    boot_population: (
        AndroidUniverseBootPopulationReconciliation
        | None
    ) = None

    boot_signature_avb_requirements: tuple[
        AndroidUniverseBootSignatureAvbRequirement,
        ...,
    ] = ()

    apex_requirements: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ] = ()

    elf_requirements: tuple[
        AndroidUniverseElfRequirement,
        ...,
    ] = ()

    elf_artifact_associations: tuple[
        AndroidUniverseElfArtifactAssociation,
        ...,
    ] = ()

    kernel_module_elf_associations: tuple[
        AndroidUniverseKernelModuleElfAssociation,
        ...,
    ] = ()

    kernel_requirements: tuple[
        AndroidUniverseKernelRequirement,
        ...,
    ] = ()

    vbmeta_requirements: tuple[
        AndroidUniverseVbmetaRequirement,
        ...,
    ] = ()

    avb_regions: tuple[
        AndroidUniverseAvbRegion,
        ...,
    ] = ()

    avb_topology: (
        AndroidUniverseAvbTopology
        | None
    ) = None

    bootloader_requirements: tuple[
        AndroidUniverseBootloaderRequirement,
        ...,
    ] = ()

    bootloader_population: (
        AndroidUniverseBootloaderPopulationReconciliation
        | None
    ) = None

    sflb_requirements: tuple[
        AndroidUniverseSflbRequirement,
        ...,
    ] = ()

    bmp_requirements: tuple[
        AndroidUniverseBmpRequirement,
        ...,
    ] = ()

    dtbo_requirements: tuple[
        AndroidUniverseDtboRequirement,
        ...,
    ] = ()

    dtbo_population: (
        AndroidUniverseDtboPopulationReconciliation
        | None
    ) = None

    init_import_requirements: tuple[
        AndroidUniverseInitImportRequirement,
        ...,
    ] = ()

    init_import_resolutions: tuple[
        AndroidUniverseInitImportResolution,
        ...,
    ] = ()

    init_service_requirements: tuple[
        AndroidUniverseInitServiceRequirement,
        ...,
    ] = ()

    init_service_resolutions: tuple[
        AndroidUniverseInitServiceResolution,
        ...,
    ] = ()

    init_action_requirements: tuple[
        AndroidUniverseInitActionRequirement,
        ...,
    ] = ()

    init_source_records: tuple[
        AndroidUniverseInitSourceRecord,
        ...,
    ] = ()

    init_source_applicability: tuple[
        AndroidUniverseInitSourceApplicability,
        ...,
    ] = ()

    fstab_applicability: tuple[
        AndroidUniverseFstabApplicabilityObservation,
        ...,
    ] = ()

    fstab_applicability_conclusions: tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ] = ()

    aconfig_requirement: (
        AndroidUniverseAconfigRequirement
        | None
    ) = None

    input_requirement: (
        AndroidUniverseInputRequirement
        | None
    ) = None

    font_requirement: (
        AndroidUniverseFontRequirement
        | None
    ) = None

    certificate_requirement: (
        AndroidUniverseCertificateRequirement
        | None
    ) = None

    structured_configuration_requirement: (
        AndroidUniverseStructuredConfigurationRequirement
        | None
    ) = None

    dex_requirement: (
        AndroidUniverseStandaloneDexPopulationRequirement
        | None
    ) = None

    avf_requirement: (
        AndroidUniverseAvfRequirement
        | None
    ) = None

    apk_requirement: (
        AndroidUniverseApkRequirement
        | None
    ) = None

    classpath_requirement: (
        AndroidUniverseClasspathRequirement
        | None
    ) = None

    shell_script_reconciliation: (
        AndroidUniverseShellScriptReconciliation
        | None
    ) = None

    art_runtime_requirement: (
        AndroidUniverseArtRuntimeRequirement
        | None
    ) = None

    kernel_module_requirement: (
        AndroidUniverseKernelModuleRequirement
        | None
    ) = None

    linker_requirement: (
        AndroidUniverseLinkerRequirement
        | None
    ) = None

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
            self.parsing_boundary,
            AndroidUniverseParsingBoundary,
        ):
            raise TypeError(
                "parsing_boundary must be an "
                "AndroidUniverseParsingBoundary"
            )

        if (
            self.parsing_boundary.parsing
            is not self.parsing
        ):
            raise ValueError(
                "parsing_boundary must preserve exact canonical "
                "AndroidParsingResult identity"
            )

        if (
            self.aconfig_requirement is not None
            and not isinstance(
                self.aconfig_requirement,
                AndroidUniverseAconfigRequirement,
            )
        ):
            raise TypeError(
                "aconfig_requirement must be an "
                "AndroidUniverseAconfigRequirement or None"
            )

        if (
            self.input_requirement is not None
            and not isinstance(
                self.input_requirement,
                AndroidUniverseInputRequirement,
            )
        ):
            raise TypeError(
                "input_requirement must be an "
                "AndroidUniverseInputRequirement or None"
            )

        if (
            self.font_requirement is not None
            and not isinstance(
                self.font_requirement,
                AndroidUniverseFontRequirement,
            )
        ):
            raise TypeError(
                "font_requirement must be an "
                "AndroidUniverseFontRequirement or None"
            )

        if (
            self.certificate_requirement is not None
            and not isinstance(
                self.certificate_requirement,
                AndroidUniverseCertificateRequirement,
            )
        ):
            raise TypeError(
                "certificate_requirement must be an "
                "AndroidUniverseCertificateRequirement or None"
            )

        if (
            self.structured_configuration_requirement
            is not None
            and not isinstance(
                self.structured_configuration_requirement,
                AndroidUniverseStructuredConfigurationRequirement,
            )
        ):
            raise TypeError(
                "structured_configuration_requirement must be an "
                "AndroidUniverseStructuredConfigurationRequirement "
                "or None"
            )

        if (
            self.dex_requirement is not None
            and not isinstance(
                self.dex_requirement,
                AndroidUniverseStandaloneDexPopulationRequirement,
            )
        ):
            raise TypeError(
                "dex_requirement must be an "
                "AndroidUniverseStandaloneDexPopulationRequirement "
                "or None"
            )

        if (
            self.avf_requirement is not None
            and not isinstance(
                self.avf_requirement,
                AndroidUniverseAvfRequirement,
            )
        ):
            raise TypeError(
                "avf_requirement must be an "
                "AndroidUniverseAvfRequirement or None"
            )

        if (
            self.apk_requirement is not None
            and not isinstance(
                self.apk_requirement,
                AndroidUniverseApkRequirement,
            )
        ):
            raise TypeError(
                "apk_requirement must be an "
                "AndroidUniverseApkRequirement or None"
            )

        if (
            self.classpath_requirement is not None
            and not isinstance(
                self.classpath_requirement,
                AndroidUniverseClasspathRequirement,
            )
        ):
            raise TypeError(
                "classpath_requirement must be an "
                "AndroidUniverseClasspathRequirement or None"
            )

        if (
            self.shell_script_reconciliation is not None
            and not isinstance(
                self.shell_script_reconciliation,
                AndroidUniverseShellScriptReconciliation,
            )
        ):
            raise TypeError(
                "shell_script_reconciliation must be an "
                "AndroidUniverseShellScriptReconciliation or None"
            )

        if (
            self.art_runtime_requirement is not None
            and not isinstance(
                self.art_runtime_requirement,
                AndroidUniverseArtRuntimeRequirement,
            )
        ):
            raise TypeError(
                "art_runtime_requirement must be an "
                "AndroidUniverseArtRuntimeRequirement or None"
            )

        if (
            self.kernel_module_requirement is not None
            and not isinstance(
                self.kernel_module_requirement,
                AndroidUniverseKernelModuleRequirement,
            )
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement or None"
            )

        if (
            self.linker_requirement is not None
            and not isinstance(
                self.linker_requirement,
                AndroidUniverseLinkerRequirement,
            )
        ):
            raise TypeError(
                "linker_requirement must be an "
                "AndroidUniverseLinkerRequirement or None"
            )

        if (
            self.aconfig_requirement is not None
            and self.aconfig_requirement.source
            is not self.parsing.aconfig
        ):
            raise ValueError(
                "aconfig_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.input_requirement is not None
            and self.input_requirement.source
            is not self.parsing.input
        ):
            raise ValueError(
                "input_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.font_requirement is not None
            and self.font_requirement.source
            is not self.parsing.font
        ):
            raise ValueError(
                "font_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.certificate_requirement is not None
            and self.certificate_requirement.source
            is not self.parsing.certificate
        ):
            raise ValueError(
                "certificate_requirement source must preserve "
                "exact canonical Parsing identity"
            )

        if (
            self.structured_configuration_requirement
            is not None
            and (
                self.structured_configuration_requirement.source
                is not self.parsing.structured_configuration
            )
        ):
            raise ValueError(
                "structured_configuration_requirement source must "
                "preserve exact canonical Parsing identity"
            )

        if (
            self.dex_requirement is not None
            and self.dex_requirement.source
            is not self.parsing.dex
        ):
            raise ValueError(
                "dex_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.avf_requirement is not None
            and self.avf_requirement.source
            is not self.parsing.avf_vm_config
        ):
            raise ValueError(
                "avf_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.apk_requirement is not None
            and self.apk_requirement.source
            is not self.parsing.apk
        ):
            raise ValueError(
                "apk_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.classpath_requirement is not None
            and self.classpath_requirement.source
            is not self.parsing.classpath
        ):
            raise ValueError(
                "classpath_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if (
            self.classpath_requirement is not None
            and (
                self.classpath_requirement
                .java_archive_reconciliation
                .source
                is not self.parsing.java_archive
            )
        ):
            raise ValueError(
                "Classpath Java-archive reconciliation must preserve "
                "exact canonical Parsing java_archive identity"
            )

        if (
            self.shell_script_reconciliation is not None
            and (
                self.shell_script_reconciliation.source
                is not self.parsing.shell_script
            )
        ):
            raise ValueError(
                "shell-script reconciliation must preserve exact "
                "canonical Parsing shell_script identity"
            )

        if (
            self.art_runtime_requirement is not None
            and self.art_runtime_requirement.source
            is not self.parsing.art_runtime
        ):
            raise ValueError(
                "art_runtime_requirement source must preserve exact "
                "canonical Parsing identity"
            )

        if self.kernel_module_requirement is not None:
            if (
                self.kernel_module_requirement.modules
                is not self.parsing.kernel_modules
            ):
                raise ValueError(
                    "kernel_module_requirement modules must preserve "
                    "exact canonical Parsing identity"
                )

            if (
                self.kernel_module_requirement.configurations
                is not self.parsing.kernel_module_configurations
            ):
                raise ValueError(
                    "kernel_module_requirement configurations must "
                    "preserve exact canonical Parsing identity"
                )

        if self.linker_requirement is not None:
            if (
                self.linker_requirement.configurations
                is not self.parsing.linker_configurations
            ):
                raise ValueError(
                    "linker_requirement configurations must preserve "
                    "exact canonical Parsing identity"
                )

            if (
                self.linker_requirement.protobuf_configurations
                is not self.parsing.linker_protobuf_configurations
            ):
                raise ValueError(
                    "linker_requirement protobuf configurations must "
                    "preserve exact canonical Parsing identity"
                )

            if (
                self.linker_requirement.native_library_configurations
                is not self.parsing.native_library_configurations
            ):
                raise ValueError(
                    "linker_requirement native-library configurations "
                    "must preserve exact canonical Parsing identity"
                )

        if (
            self.knowledge_resolution is not None
            and not isinstance(
                self.knowledge_resolution,
                AndroidKnowledgeResolutionResult,
            )
        ):
            raise TypeError(
                "knowledge_resolution must be an "
                "AndroidKnowledgeResolutionResult or None"
            )

        if (
            self.artifact_requirements is not None
            and not isinstance(
                self.artifact_requirements,
                AndroidUniverseArtifactRequirementInventory,
            )
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory "
                "or None"
            )

        if (
            self.artifact_requirements is not None
            and (
                self.artifact_requirements.source_inventory
                is not self.parsing.filesystem_inventory
            )
        ):
            raise ValueError(
                "artifact requirements must preserve exact "
                "Parsing filesystem inventory identity"
            )

        if not isinstance(
            self.filesystem_entry_requirements,
            AndroidUniverseFilesystemEntryRequirementInventory,
        ):
            raise TypeError(
                "filesystem_entry_requirements must be an "
                "AndroidUniverseFilesystemEntryRequirementInventory"
            )

        if (
            self.filesystem_entry_requirements.source_inventory
            is not self.parsing.filesystem_inventory
        ):
            raise ValueError(
                "filesystem_entry_requirements must preserve exact "
                "Parsing filesystem inventory identity"
            )

        if (
            self.artifact_requirements is not None
        ):
            artifact_by_identity = {
                requirement.identity_key: requirement
                for requirement
                in self.artifact_requirements.requirements
            }

            for requirement in (
                self.filesystem_entry_requirements.requirements
            ):
                if requirement.artifact_requirement is None:
                    continue

                expected = artifact_by_identity.get(
                    requirement.identity_key
                )

                if (
                    expected is None
                    or requirement.artifact_requirement
                    is not expected
                ):
                    raise ValueError(
                        "filesystem-entry regular-file linkage must "
                        "preserve exact canonical Artifact requirement "
                        "identity"
                    )

        if not isinstance(
            self.model_source_requirements,
            AndroidUniverseModelSourceRequirementInventory,
        ):
            raise TypeError(
                "model_source_requirements must be an "
                "AndroidUniverseModelSourceRequirementInventory"
            )

        if (
            self.model_source_requirements.source_inventory
            is not self.parsing.source_inventory
        ):
            raise ValueError(
                "model_source_requirements must preserve exact "
                "Parsing source_inventory identity"
            )

        if (
            self.architecture is not None
            and not isinstance(
                self.architecture,
                AndroidUniverseArchitecture,
            )
        ):
            raise TypeError(
                "architecture must be an "
                "AndroidUniverseArchitecture or None"
            )

        if not isinstance(
            self.property_source_records,
            tuple,
        ):
            raise TypeError(
                "property_source_records must be a tuple"
            )

        if not all(
            isinstance(
                record,
                AndroidUniversePropertySourceRecord,
            )
            for record in self.property_source_records
        ):
            raise TypeError(
                "property_source_records must contain only "
                "AndroidUniversePropertySourceRecord instances"
            )

        expected_property_sources = tuple(
            self.parsing.filesystem.property_files
        )

        actual_property_sources = tuple(
            record.parsed_source
            for record
            in self.property_source_records
        )

        expected_property_ids = {
            id(source)
            for source
            in expected_property_sources
        }

        actual_property_ids = {
            id(source)
            for source
            in actual_property_sources
        }

        if (
            expected_property_ids
            != actual_property_ids
        ):
            raise ValueError(
                "property_source_records must conserve every exact "
                "ParsedAndroidPropertyFile identity"
            )

        if (
            len(actual_property_ids)
            != len(actual_property_sources)
        ):
            raise ValueError(
                "property_source_records must not duplicate "
                "Parsing property sources"
            )

        canonical_property_source_records = tuple(
            sorted(
                self.property_source_records,
                key=lambda record: (
                    record.identity_key
                ),
            )
        )

        if (
            self.property_source_records
            != canonical_property_source_records
        ):
            raise ValueError(
                "property_source_records must be in canonical order"
            )

        if not isinstance(
            self.property_evidence,
            tuple,
        ):
            raise TypeError(
                "property_evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniversePropertyEvidence,
            )
            for item in self.property_evidence
        ):
            raise TypeError(
                "property_evidence must contain only "
                "AndroidUniversePropertyEvidence instances"
            )

        canonical_evidence = tuple(
            sorted(
                self.property_evidence,
                key=lambda item: (
                    item.model_source.source_name,
                    item.model_source.android_path.as_posix(),
                    item.declaration.line_number,
                    item.fact.fact,
                    item.fact.property_key,
                    item.fact.value,
                ),
            )
        )

        if self.property_evidence != canonical_evidence:
            raise ValueError(
                "property_evidence must be in canonical order"
            )

        if not isinstance(
            self.runtime_property_requirements,
            tuple,
        ):
            raise TypeError(
                "runtime_property_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRuntimePropertyRequirement,
            )
            for item
            in self.runtime_property_requirements
        ):
            raise TypeError(
                "runtime_property_requirements must contain only "
                "AndroidUniverseRuntimePropertyRequirement instances"
            )

        canonical_runtime_property_requirements = tuple(
            sorted(
                self.runtime_property_requirements,
                key=lambda item: (
                    item.property_key
                ),
            )
        )

        if (
            self.runtime_property_requirements
            != canonical_runtime_property_requirements
        ):
            raise ValueError(
                "runtime_property_requirements must be in canonical "
                "property-key order"
            )

        runtime_property_keys = tuple(
            item.property_key
            for item
            in self.runtime_property_requirements
        )

        if len(
            runtime_property_keys
        ) != len(
            set(
                runtime_property_keys
            )
        ):
            raise ValueError(
                "runtime_property_requirements must contain one "
                "requirement per property key"
            )

        if not isinstance(
            self.runtime_property_relevance,
            tuple,
        ):
            raise TypeError(
                "runtime_property_relevance must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRuntimePropertyRelevance,
            )
            for item in self.runtime_property_relevance
        ):
            raise TypeError(
                "runtime_property_relevance must contain only "
                "AndroidUniverseRuntimePropertyRelevance instances"
            )

        canonical_runtime_property_relevance = tuple(
            sorted(
                self.runtime_property_relevance,
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )

        if (
            self.runtime_property_relevance
            != canonical_runtime_property_relevance
        ):
            raise ValueError(
                "runtime_property_relevance must be in canonical "
                "property-key order"
            )

        runtime_property_relevance_ids = tuple(
            item.requirement_id
            for item in self.runtime_property_relevance
        )

        if len(
            runtime_property_relevance_ids
        ) != len(
            set(
                runtime_property_relevance_ids
            )
        ):
            raise ValueError(
                "runtime_property_relevance must contain one "
                "conclusion per runtime-property requirement"
            )

        if set(
            runtime_property_relevance_ids
        ) != set(
            runtime_property_keys
        ):
            raise ValueError(
                "runtime_property_relevance must cover every "
                "runtime-property requirement exactly once"
            )

        relevance_by_id = {
            item.requirement_id: item
            for item in self.runtime_property_relevance
        }

        requirement_by_key = {
            item.property_key: item
            for item in self.runtime_property_requirements
        }

        if any(
            relevance_by_id[property_key].requirement
            is not requirement
            for property_key, requirement
            in requirement_by_key.items()
        ):
            raise ValueError(
                "runtime_property_relevance must retain exact canonical "
                "runtime-property requirement identity"
            )

        if not isinstance(
            self.conclusions,
            tuple,
        ):
            raise TypeError(
                "conclusions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFactConclusion,
            )
            for item in self.conclusions
        ):
            raise TypeError(
                "conclusions must contain only "
                "AndroidUniverseFactConclusion instances"
            )

        conclusion_facts = tuple(
            item.fact
            for item in self.conclusions
        )

        if conclusion_facts != tuple(
            sorted(
                conclusion_facts
            )
        ):
            raise ValueError(
                "conclusions must be in canonical fact order"
            )

        if len(
            conclusion_facts
        ) != len(
            set(
                conclusion_facts
            )
        ):
            raise ValueError(
                "conclusions must contain one entry per fact"
            )

        if not isinstance(
            self.fstab_requirements,
            tuple,
        ):
            raise TypeError(
                "fstab_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFstabRequirement,
            )
            for item in self.fstab_requirements
        ):
            raise TypeError(
                "fstab_requirements must contain only "
                "AndroidUniverseFstabRequirement instances"
            )

        if not isinstance(
            self.ueventd_requirements,
            tuple,
        ):
            raise TypeError(
                "ueventd_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseUeventdRequirement.__args__,
            )
            for item in self.ueventd_requirements
        ):
            raise TypeError(
                "ueventd_requirements must contain only "
                "AndroidUniverseUeventdRequirement instances"
            )

        if not isinstance(
            self.ueventd_source_contexts,
            tuple,
        ):
            raise TypeError(
                "ueventd_source_contexts must be a tuple"
            )

        if not all(
            isinstance(
                context,
                AndroidUniverseUeventdSourceContext,
            )
            for context in self.ueventd_source_contexts
        ):
            raise TypeError(
                "ueventd_source_contexts must contain only "
                "AndroidUniverseUeventdSourceContext instances"
            )

        ueventd_source_context_ids = tuple(
            context.source_identity
            for context in self.ueventd_source_contexts
        )

        if len(
            ueventd_source_context_ids
        ) != len(
            set(
                ueventd_source_context_ids
            )
        ):
            raise ValueError(
                "ueventd_source_contexts must preserve unique "
                "canonical source identities"
            )

        canonical_ueventd_source_contexts = tuple(
            sorted(
                self.ueventd_source_contexts,
                key=lambda context: (
                    context.source_identity
                ),
            )
        )

        if (
            self.ueventd_source_contexts
            != canonical_ueventd_source_contexts
        ):
            raise ValueError(
                "ueventd_source_contexts must be in canonical order"
            )

        canonical_ueventd_requirements = tuple(
            sorted(
                self.ueventd_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else item.source_path.as_posix()
                    ),
                    item.declaration.source_line,
                    item.requirement_id,
                ),
            )
        )

        if (
            self.ueventd_requirements
            != canonical_ueventd_requirements
        ):
            raise ValueError(
                "ueventd_requirements must be in canonical order"
            )

        ueventd_requirement_ids = tuple(
            item.requirement_id
            for item in self.ueventd_requirements
        )

        if len(
            ueventd_requirement_ids
        ) != len(
            set(
                ueventd_requirement_ids
            )
        ):
            raise ValueError(
                "ueventd_requirements must contain unique "
                "requirement identities"
            )

        if (
            self.vintf_applicability is not None
            and not isinstance(
                self.vintf_applicability,
                AndroidUniverseVintfApplicability,
            )
        ):
            raise TypeError(
                "vintf_applicability must be an "
                "AndroidUniverseVintfApplicability or None"
            )

        if not isinstance(
            self.device_capabilities,
            tuple,
        ):
            raise TypeError(
                "device_capabilities must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDeviceCapabilityConclusion,
            )
            for item in self.device_capabilities
        ):
            raise TypeError(
                "device_capabilities must contain only "
                "AndroidUniverseDeviceCapabilityConclusion instances"
            )

        capability_names = tuple(
            item.capability.value
            for item in self.device_capabilities
        )

        if capability_names != tuple(
            sorted(
                capability_names
            )
        ):
            raise ValueError(
                "device_capabilities must use canonical capability order"
            )

        if len(
            capability_names
        ) != len(
            set(
                capability_names
            )
        ):
            raise ValueError(
                "device_capabilities must contain one conclusion "
                "per capability"
            )

        if not isinstance(
            self.vintf_requirements,
            tuple,
        ):
            raise TypeError(
                "vintf_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfDocumentRequirement,
            )
            for item in self.vintf_requirements
        ):
            raise TypeError(
                "vintf_requirements must contain only "
                "AndroidUniverseVintfDocumentRequirement instances"
            )

        canonical_vintf_requirements = tuple(
            sorted(
                self.vintf_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else item.source_path.as_posix()
                    ),
                    item.semantics.kind.value,
                    item.semantics.side.value,
                    item.requirement_id,
                ),
            )
        )

        if (
            self.vintf_requirements
            != canonical_vintf_requirements
        ):
            raise ValueError(
                "vintf_requirements must be in canonical order"
            )

        vintf_requirement_ids = tuple(
            item.requirement_id
            for item in self.vintf_requirements
        )

        if len(
            vintf_requirement_ids
        ) != len(
            set(
                vintf_requirement_ids
            )
        ):
            raise ValueError(
                "vintf_requirements must contain unique "
                "requirement identities"
            )

        if not isinstance(
            self.selinux_requirements,
            tuple,
        ):
            raise TypeError(
                "selinux_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseSelinuxSourceRequirement,
            )
            for item in self.selinux_requirements
        ):
            raise TypeError(
                "selinux_requirements must contain only "
                "AndroidUniverseSelinuxSourceRequirement instances"
            )

        canonical_selinux_requirements = tuple(
            sorted(
                self.selinux_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else item.source_path.as_posix()
                    ),
                    item.kind.value,
                    item.requirement_id,
                ),
            )
        )

        if (
            self.selinux_requirements
            != canonical_selinux_requirements
        ):
            raise ValueError(
                "selinux_requirements must be in canonical order"
            )

        selinux_requirement_ids = tuple(
            item.requirement_id
            for item in self.selinux_requirements
        )

        if len(
            selinux_requirement_ids
        ) != len(
            set(
                selinux_requirement_ids
            )
        ):
            raise ValueError(
                "selinux_requirements must contain unique "
                "requirement identities"
            )

        if (
            self.selinux_policy_graph is not None
            and not isinstance(
                self.selinux_policy_graph,
                AndroidUniverseSelinuxPolicyGraph,
            )
        ):
            raise TypeError(
                "selinux_policy_graph must be an "
                "AndroidUniverseSelinuxPolicyGraph or None"
            )

        if not isinstance(
            self.selinux_conclusions,
            tuple,
        ):
            raise TypeError(
                "selinux_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseSelinuxConclusion,
            )
            for item in self.selinux_conclusions
        ):
            raise TypeError(
                "selinux_conclusions must contain only "
                "AndroidUniverseSelinuxConclusion instances"
            )

        if not isinstance(
            self.selinux_applicability,
            tuple,
        ):
            raise TypeError(
                "selinux_applicability must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            for item in self.selinux_applicability
        ):
            raise TypeError(
                "selinux_applicability must contain only "
                "AndroidUniverseRequirementApplicability instances"
            )

        canonical_selinux_applicability = tuple(
            sorted(
                self.selinux_applicability,
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )

        if (
            self.selinux_applicability
            != canonical_selinux_applicability
        ):
            raise ValueError(
                "selinux_applicability must be in canonical "
                "requirement order"
            )

        selinux_applicability_ids = tuple(
            item.requirement_id
            for item in self.selinux_applicability
        )

        if len(
            selinux_applicability_ids
        ) != len(
            set(
                selinux_applicability_ids
            )
        ):
            raise ValueError(
                "selinux_applicability must contain one entry "
                "per requirement"
            )

        if set(
            selinux_applicability_ids
        ) != set(
            selinux_requirement_ids
        ):
            raise ValueError(
                "selinux_applicability must cover every SELinux "
                "requirement exactly once"
            )

        if not isinstance(
            self.cross_family_relationships,
            tuple,
        ):
            raise TypeError(
                "cross_family_relationships must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ANDROID_UNIVERSE_CROSS_FAMILY_RELATIONSHIP_TYPES,
            )
            for item in self.cross_family_relationships
        ):
            raise TypeError(
                "cross_family_relationships must contain only "
                "supported Android Universe cross-family "
                "relationship instances"
            )

        canonical_cross_family_relationships = tuple(
            sorted(
                self.cross_family_relationships,
                key=lambda item: (
                    item.kind.value,
                    item.relationship_id,
                ),
            )
        )

        if (
            self.cross_family_relationships
            != canonical_cross_family_relationships
        ):
            raise ValueError(
                "cross_family_relationships must be in canonical order"
            )

        cross_family_relationship_ids = tuple(
            item.relationship_id
            for item
            in self.cross_family_relationships
        )

        if len(
            cross_family_relationship_ids
        ) != len(
            set(
                cross_family_relationship_ids
            )
        ):
            raise ValueError(
                "cross_family_relationships must contain unique "
                "relationship identities"
            )

        if not isinstance(
            self.cross_family_relationship_applicability,
            tuple,
        ):
            raise TypeError(
                "cross_family_relationship_applicability "
                "must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            for item
            in self.cross_family_relationship_applicability
        ):
            raise TypeError(
                "cross_family_relationship_applicability "
                "must contain only "
                "AndroidUniverseRequirementApplicability instances"
            )

        canonical_cross_family_relationship_applicability = tuple(
            sorted(
                self.cross_family_relationship_applicability,
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )

        if (
            self.cross_family_relationship_applicability
            != canonical_cross_family_relationship_applicability
        ):
            raise ValueError(
                "cross_family_relationship_applicability "
                "must be in canonical order"
            )

        relationship_ids = {
            relationship.relationship_id
            for relationship
            in self.cross_family_relationships
        }

        applicability_ids = tuple(
            item.requirement_id
            for item
            in self.cross_family_relationship_applicability
        )

        if len(
            applicability_ids
        ) != len(
            set(
                applicability_ids
            )
        ):
            raise ValueError(
                "cross_family_relationship_applicability "
                "must contain unique requirement identities"
            )

        if (
            set(
                applicability_ids
            )
            != relationship_ids
        ):
            raise ValueError(
                "cross_family_relationship_applicability "
                "must cover every cross-family relationship exactly once"
            )

        if not isinstance(
            self.linker_apex_context_applicability,
            tuple,
        ):
            raise TypeError(
                "linker_apex_context_applicability must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerApexContextApplicability,
            )
            for item
            in self.linker_apex_context_applicability
        ):
            raise TypeError(
                "linker_apex_context_applicability must contain only "
                "AndroidUniverseLinkerApexContextApplicability instances"
            )

        canonical_linker_apex_context_applicability = tuple(
            sorted(
                self.linker_apex_context_applicability,
                key=lambda item: (
                    item.applicability_id
                ),
            )
        )

        if (
            self.linker_apex_context_applicability
            != canonical_linker_apex_context_applicability
        ):
            raise ValueError(
                "linker_apex_context_applicability must be in "
                "canonical order"
            )

        linker_apex_applicability_ids = tuple(
            item.applicability_id
            for item
            in self.linker_apex_context_applicability
        )

        if len(
            linker_apex_applicability_ids
        ) != len(
            set(
                linker_apex_applicability_ids
            )
        ):
            raise ValueError(
                "linker_apex_context_applicability must contain "
                "unique conclusion identities"
            )

        linker_apex_relationships = tuple(
            relationship
            for relationship
            in self.cross_family_relationships
            if isinstance(
                relationship,
                AndroidUniverseLinkerApexRelationship,
            )
        )

        if len(
            self.linker_apex_context_applicability
        ) != len(
            linker_apex_relationships
        ):
            raise ValueError(
                "linker_apex_context_applicability must cover every "
                "Linker/APEX relationship exactly once"
            )

        if not all(
            any(
                applicability.membership_relationship
                is relationship
                for relationship
                in linker_apex_relationships
            )
            for applicability
            in self.linker_apex_context_applicability
        ):
            raise ValueError(
                "linker_apex_context_applicability must preserve exact "
                "canonical Linker/APEX relationship identity"
            )

        if not isinstance(
            self.linker_apex_namespace_inputs,
            tuple,
        ):
            raise TypeError(
                "linker_apex_namespace_inputs must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerApexNamespaceInput,
            )
            for item
            in self.linker_apex_namespace_inputs
        ):
            raise TypeError(
                "linker_apex_namespace_inputs must contain only "
                "AndroidUniverseLinkerApexNamespaceInput instances"
            )

        canonical_linker_apex_namespace_inputs = tuple(
            sorted(
                self.linker_apex_namespace_inputs,
                key=lambda item: (
                    item.input_id
                ),
            )
        )

        if (
            self.linker_apex_namespace_inputs
            != canonical_linker_apex_namespace_inputs
        ):
            raise ValueError(
                "linker_apex_namespace_inputs must be in canonical order"
            )

        linker_apex_namespace_input_ids = tuple(
            item.input_id
            for item
            in self.linker_apex_namespace_inputs
        )

        if len(
            linker_apex_namespace_input_ids
        ) != len(
            set(
                linker_apex_namespace_input_ids
            )
        ):
            raise ValueError(
                "linker_apex_namespace_inputs must contain unique "
                "input identities"
            )

        if len(
            self.linker_apex_namespace_inputs
        ) != len(
            self.apex_requirements
        ):
            raise ValueError(
                "linker_apex_namespace_inputs must cover every "
                "canonical APEX requirement exactly once"
            )

        if not all(
            any(
                item.apex_requirement
                is apex_requirement
                for apex_requirement
                in self.apex_requirements
            )
            for item
            in self.linker_apex_namespace_inputs
        ):
            raise ValueError(
                "linker_apex_namespace_inputs must preserve exact "
                "canonical APEX requirement identity"
            )

        if self.linker_requirement is None:
            if any(
                item.matched_runtime_policies
                for item
                in self.linker_apex_namespace_inputs
            ):
                raise ValueError(
                    "APEX namespace inputs must not claim Linker runtime "
                    "policies when no Linker requirement exists"
                )
        elif not all(
            all(
                any(
                    matched_policy
                    is canonical_policy
                    for canonical_policy
                    in self.linker_requirement.runtime_policies
                )
                for matched_policy
                in item.matched_runtime_policies
            )
            for item
            in self.linker_apex_namespace_inputs
        ):
            raise ValueError(
                "linker_apex_namespace_inputs must preserve exact "
                "canonical Linker runtime-policy identities"
            )

        if not isinstance(
            self.linker_apex_public_library_conclusions,
            tuple,
        ):
            raise TypeError(
                "linker_apex_public_library_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                conclusion,
                AndroidUniverseLinkerApexPublicLibraryConclusion,
            )
            for conclusion
            in self.linker_apex_public_library_conclusions
        ):
            raise TypeError(
                "linker_apex_public_library_conclusions must contain only "
                "AndroidUniverseLinkerApexPublicLibraryConclusion instances"
            )

        canonical_linker_apex_public_library_conclusions = tuple(
            sorted(
                self.linker_apex_public_library_conclusions,
                key=lambda conclusion: (
                    conclusion.conclusion_id
                ),
            )
        )

        if (
            self.linker_apex_public_library_conclusions
            != canonical_linker_apex_public_library_conclusions
        ):
            raise ValueError(
                "linker_apex_public_library_conclusions must be in "
                "canonical order"
            )

        linker_apex_public_library_conclusion_ids = tuple(
            conclusion.conclusion_id
            for conclusion
            in self.linker_apex_public_library_conclusions
        )

        if len(
            linker_apex_public_library_conclusion_ids
        ) != len(
            set(
                linker_apex_public_library_conclusion_ids
            )
        ):
            raise ValueError(
                "linker_apex_public_library_conclusions must contain "
                "unique conclusion identities"
            )

        if len(
            self.linker_apex_public_library_conclusions
        ) != len(
            self.apex_requirements
        ):
            raise ValueError(
                "linker_apex_public_library_conclusions must cover every "
                "canonical APEX requirement exactly once"
            )

        if not all(
            any(
                conclusion.apex_requirement
                is apex_requirement
                for apex_requirement
                in self.apex_requirements
            )
            for conclusion
            in self.linker_apex_public_library_conclusions
        ):
            raise ValueError(
                "linker_apex_public_library_conclusions must preserve "
                "exact canonical APEX requirement identity"
            )

        if self.linker_requirement is None:
            if any(
                conclusion.matched_runtime_policies
                for conclusion
                in self.linker_apex_public_library_conclusions
            ):
                raise ValueError(
                    "APEX public-library conclusions must not claim "
                    "Linker runtime policies when no Linker requirement exists"
                )
        elif not all(
            all(
                any(
                    matched_policy
                    is canonical_policy
                    for canonical_policy
                    in self.linker_requirement.runtime_policies
                )
                for matched_policy
                in conclusion.matched_runtime_policies
            )
            for conclusion
            in self.linker_apex_public_library_conclusions
        ):
            raise ValueError(
                "linker_apex_public_library_conclusions must preserve "
                "exact canonical Linker runtime-policy identities"
            )

        if not isinstance(
            self.linker_apex_native_library_conclusions,
            tuple,
        ):
            raise TypeError(
                "linker_apex_native_library_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerApexNativeLibraryConclusion,
            )
            for item
            in self.linker_apex_native_library_conclusions
        ):
            raise TypeError(
                "linker_apex_native_library_conclusions must contain only "
                "AndroidUniverseLinkerApexNativeLibraryConclusion instances"
            )

        canonical_linker_apex_native_library_conclusions = tuple(
            sorted(
                self.linker_apex_native_library_conclusions,
                key=lambda item: (
                    item.conclusion_id
                ),
            )
        )

        if (
            self.linker_apex_native_library_conclusions
            != canonical_linker_apex_native_library_conclusions
        ):
            raise ValueError(
                "linker_apex_native_library_conclusions must be in "
                "canonical order"
            )

        linker_apex_native_library_conclusion_ids = tuple(
            item.conclusion_id
            for item
            in self.linker_apex_native_library_conclusions
        )

        if len(
            linker_apex_native_library_conclusion_ids
        ) != len(
            set(
                linker_apex_native_library_conclusion_ids
            )
        ):
            raise ValueError(
                "linker_apex_native_library_conclusions must contain "
                "unique conclusion identities"
            )

        expected_linker_apex_native_library_occurrences = {
            (
                id(
                    applicability
                ),
                requirement_index,
                library_name,
            )
            for applicability
            in self.linker_apex_context_applicability
            for requirement_index, library_name
            in enumerate(
                applicability
                .membership_relationship
                .apex_requirement
                .require_native_libs
            )
        }

        actual_linker_apex_native_library_occurrences = {
            (
                id(
                    conclusion.context_applicability
                ),
                conclusion.requirement_index,
                conclusion.library_name,
            )
            for conclusion
            in self.linker_apex_native_library_conclusions
        }

        if (
            actual_linker_apex_native_library_occurrences
            != expected_linker_apex_native_library_occurrences
        ):
            raise ValueError(
                "linker_apex_native_library_conclusions must cover "
                "every exact requireNativeLibs occurrence exactly once"
            )

        if not all(
            any(
                conclusion.context_applicability
                is applicability
                for applicability
                in self.linker_apex_context_applicability
            )
            for conclusion
            in self.linker_apex_native_library_conclusions
        ):
            raise ValueError(
                "linker_apex_native_library_conclusions must preserve "
                "exact context-applicability identity"
            )

        if not isinstance(
            self.linker_elf_contexts,
            tuple,
        ):
            raise TypeError(
                "linker_elf_contexts must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerElfContext,
            )
            for item
            in self.linker_elf_contexts
        ):
            raise TypeError(
                "linker_elf_contexts must contain only "
                "AndroidUniverseLinkerElfContext instances"
            )

        canonical_linker_elf_contexts = tuple(
            sorted(
                self.linker_elf_contexts,
                key=lambda item: (
                    item.context_id
                ),
            )
        )

        if (
            self.linker_elf_contexts
            != canonical_linker_elf_contexts
        ):
            raise ValueError(
                "linker_elf_contexts must be in canonical order"
            )

        linker_elf_context_ids = tuple(
            item.context_id
            for item
            in self.linker_elf_contexts
        )

        if len(
            linker_elf_context_ids
        ) != len(
            set(
                linker_elf_context_ids
            )
        ):
            raise ValueError(
                "linker_elf_contexts must contain unique "
                "context identities"
            )

        if len(
            self.linker_elf_contexts
        ) != len(
            self.elf_requirements
        ):
            raise ValueError(
                "linker_elf_contexts must cover every canonical "
                "ELF requirement exactly once"
            )

        if not all(
            any(
                context.elf_requirement
                is requirement
                for requirement
                in self.elf_requirements
            )
            for context
            in self.linker_elf_contexts
        ):
            raise ValueError(
                "linker_elf_contexts must preserve exact canonical "
                "ELF requirement identity"
            )

        if not isinstance(
            self.init_service_substantiations,
            tuple,
        ):
            raise TypeError(
                "init_service_substantiations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitServiceSubstantiation,
            )
            for item in self.init_service_substantiations
        ):
            raise TypeError(
                "init_service_substantiations must contain only "
                "AndroidUniverseInitServiceSubstantiation instances"
            )

        canonical_init_service_substantiations = tuple(
            sorted(
                self.init_service_substantiations,
                key=lambda item: (
                    item.conclusion_id
                ),
            )
        )

        if (
            self.init_service_substantiations
            != canonical_init_service_substantiations
        ):
            raise ValueError(
                "init_service_substantiations must be in canonical order"
            )

        substantiation_ids = tuple(
            item.conclusion_id
            for item
            in self.init_service_substantiations
        )

        if len(
            substantiation_ids
        ) != len(
            set(
                substantiation_ids
            )
        ):
            raise ValueError(
                "init_service_substantiations must contain unique "
                "conclusion identities"
            )

        if not isinstance(
            self.init_service_target_substantiations,
            tuple,
        ):
            raise TypeError(
                "init_service_target_substantiations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitServiceTargetSubstantiation,
            )
            for item
            in self.init_service_target_substantiations
        ):
            raise TypeError(
                "init_service_target_substantiations must contain only "
                "AndroidUniverseInitServiceTargetSubstantiation"
            )

        canonical_init_service_target_substantiations = tuple(
            sorted(
                self.init_service_target_substantiations,
                key=lambda item: (
                    item.conclusion_id
                ),
            )
        )

        if (
            self.init_service_target_substantiations
            != canonical_init_service_target_substantiations
        ):
            raise ValueError(
                "init_service_target_substantiations must be in "
                "canonical order"
            )

        target_substantiation_ids = tuple(
            item.conclusion_id
            for item
            in self.init_service_target_substantiations
        )

        if (
            len(target_substantiation_ids)
            != len(set(target_substantiation_ids))
        ):
            raise ValueError(
                "init_service_target_substantiations must contain "
                "unique conclusion identities"
            )


        if not isinstance(
            self.boot_requirements,
            tuple,
        ):
            raise TypeError(
                "boot_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseBootRequirement,
            )
            for item in self.boot_requirements
        ):
            raise TypeError(
                "boot_requirements must contain only "
                "AndroidUniverseBootRequirement instances"
            )

        if len(
            self.boot_requirements
        ) != len(
            self.parsing.boot_images
        ):
            raise ValueError(
                "boot_requirements must preserve the complete "
                "Parsing boot_images population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.boot_requirements,
                self.parsing.boot_images,
                strict=True,
            )
        ):
            raise ValueError(
                "boot_requirements must preserve exact Parsing "
                "boot-image identity and order"
            )

        boot_requirement_ids = tuple(
            item.requirement_id
            for item in self.boot_requirements
        )

        if len(
            boot_requirement_ids
        ) != len(
            set(
                boot_requirement_ids
            )
        ):
            raise ValueError(
                "boot_requirements must contain unique "
                "requirement identities"
            )

        boot_source_ids = tuple(
            id(
                requirement.source
            )
            for requirement
            in self.boot_requirements
        )

        if len(
            boot_source_ids
        ) != len(
            set(
                boot_source_ids
            )
        ):
            raise ValueError(
                "boot_requirements must preserve unique "
                "ParsedBootImage source identities"
            )

        if not isinstance(
            self.boot_population,
            AndroidUniverseBootPopulationReconciliation,
        ):
            raise TypeError(
                "boot_population must be an "
                "AndroidUniverseBootPopulationReconciliation"
            )

        if (
            self.boot_population.boot_dtbs
            is not self.parsing.boot_dtbs
        ):
            raise ValueError(
                "boot_population must preserve exact canonical "
                "Parsing boot_dtbs tuple identity"
            )

        if (
            self.boot_population.vendor_ramdisk_tables
            is not self.parsing.vendor_ramdisk_tables
        ):
            raise ValueError(
                "boot_population must preserve exact canonical "
                "Parsing vendor_ramdisk_tables tuple identity"
            )

        if (
            self.boot_population.ramdisks
            is not self.parsing.ramdisks
        ):
            raise ValueError(
                "boot_population must preserve exact canonical "
                "Parsing ramdisks tuple identity"
            )

        if (
            self.boot_population.boot_signatures
            is not self.parsing.boot_signatures
        ):
            raise ValueError(
                "boot_population must preserve exact canonical "
                "Parsing boot_signatures tuple identity"
            )

        if not isinstance(
            self.boot_signature_avb_requirements,
            tuple,
        ):
            raise TypeError(
                "boot_signature_avb_requirements must be a tuple"
            )

        if len(
            self.boot_signature_avb_requirements
        ) != len(
            self.parsing.boot_signatures
        ):
            raise ValueError(
                "boot_signature_avb_requirements must conserve "
                "the complete Parsing boot-signature population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.boot_signature_avb_requirements,
                self.parsing.boot_signatures,
                strict=True,
            )
        ):
            raise ValueError(
                "boot_signature_avb_requirements must preserve "
                "exact Parsing boot-signature identity and order"
            )

        if not all(
            association.avb_requirement
            is requirement
            for association, requirement
            in zip(
                self.boot_population.boot_signature_associations,
                self.boot_signature_avb_requirements,
                strict=True,
            )
        ):
            raise ValueError(
                "boot_population must preserve exact boot-signature "
                "AVB requirement identity and order"
            )

        if not isinstance(
            self.init_import_requirements,
            tuple,
        ):
            raise TypeError(
                "init_import_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitImportRequirement,
            )
            for item in self.init_import_requirements
        ):
            raise TypeError(
                "init_import_requirements must contain only "
                "AndroidUniverseInitImportRequirement instances"
            )

        if not isinstance(
            self.init_source_records,
            tuple,
        ):
            raise TypeError(
                "init_source_records must be a tuple"
            )

        if not all(
            isinstance(
                record,
                AndroidUniverseInitSourceRecord,
            )
            for record in self.init_source_records
        ):
            raise TypeError(
                "init_source_records must contain only "
                "AndroidUniverseInitSourceRecord instances"
            )

        expected_init_sources = tuple(
            self.parsing.filesystem.init_files
        )

        actual_init_sources = tuple(
            record.parsed_source
            for record
            in self.init_source_records
        )

        expected_init_ids = {
            id(source)
            for source
            in expected_init_sources
        }

        actual_init_ids = {
            id(source)
            for source
            in actual_init_sources
        }

        if (
            expected_init_ids
            != actual_init_ids
        ):
            raise ValueError(
                "init_source_records must conserve every exact "
                "ParsedAndroidInitSource identity"
            )

        if (
            len(actual_init_ids)
            != len(actual_init_sources)
        ):
            raise ValueError(
                "init_source_records must not duplicate "
                "Parsing INIT sources"
            )

        canonical_init_source_records = tuple(
            sorted(
                self.init_source_records,
                key=lambda record: (
                    record.identity_key
                ),
            )
        )

        if (
            self.init_source_records
            != canonical_init_source_records
        ):
            raise ValueError(
                "init_source_records must be in canonical order"
            )

        canonical_init_import_requirements = tuple(
            sorted(
                self.init_import_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else item.source_path.as_posix()
                    ),
                    item.declaration.location.line,
                    item.path,
                    item.declaration.raw,
                ),
            )
        )

        if (
            self.init_import_requirements
            != canonical_init_import_requirements
        ):
            raise ValueError(
                "init_import_requirements must be in canonical order"
            )

        init_import_requirement_ids = tuple(
            item.requirement_id
            for item in self.init_import_requirements
        )

        if len(
            init_import_requirement_ids
        ) != len(
            set(
                init_import_requirement_ids
            )
        ):
            raise ValueError(
                "init_import_requirements must contain unique "
                "requirement identities"
            )

        if not isinstance(
            self.init_import_resolutions,
            tuple,
        ):
            raise TypeError(
                "init_import_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitImportResolution,
            )
            for item
            in self.init_import_resolutions
        ):
            raise TypeError(
                "init_import_resolutions must contain only "
                "AndroidUniverseInitImportResolution instances"
            )

        canonical_init_import_resolutions = tuple(
            sorted(
                self.init_import_resolutions,
                key=lambda item: (
                    item.resolution_id
                ),
            )
        )

        if (
            self.init_import_resolutions
            != canonical_init_import_resolutions
        ):
            raise ValueError(
                "init_import_resolutions must be in canonical order"
            )

        import_resolution_ids = tuple(
            item.resolution_id
            for item
            in self.init_import_resolutions
        )

        if len(
            import_resolution_ids
        ) != len(
            set(
                import_resolution_ids
            )
        ):
            raise ValueError(
                "init_import_resolutions must contain unique "
                "resolution identities"
            )

        if not isinstance(
            self.init_service_requirements,
            tuple,
        ):
            raise TypeError(
                "init_service_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitServiceRequirement,
            )
            for item in self.init_service_requirements
        ):
            raise TypeError(
                "init_service_requirements must contain only "
                "AndroidUniverseInitServiceRequirement instances"
            )

        canonical_init_service_requirements = tuple(
            sorted(
                self.init_service_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else item.source_path.as_posix()
                    ),
                    item.service.location.line,
                    item.name,
                    item.executable,
                    item.arguments,
                ),
            )
        )

        if (
            self.init_service_requirements
            != canonical_init_service_requirements
        ):
            raise ValueError(
                "init_service_requirements must be in canonical order"
            )

        init_requirement_ids = tuple(
            item.requirement_id
            for item in self.init_service_requirements
        )

        if len(
            init_requirement_ids
        ) != len(
            set(
                init_requirement_ids
            )
        ):
            raise ValueError(
                "init_service_requirements must contain unique "
                "requirement identities"
            )

        if not isinstance(
            self.init_service_resolutions,
            tuple,
        ):
            raise TypeError(
                "init_service_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitServiceResolution,
            )
            for item
            in self.init_service_resolutions
        ):
            raise TypeError(
                "init_service_resolutions must contain only "
                "AndroidUniverseInitServiceResolution instances"
            )

        canonical_init_service_resolutions = tuple(
            sorted(
                self.init_service_resolutions,
                key=lambda item: (
                    item.resolution_id,
                ),
            )
        )

        if (
            self.init_service_resolutions
            != canonical_init_service_resolutions
        ):
            raise ValueError(
                "init_service_resolutions must be in canonical order"
            )

        resolution_ids = tuple(
            item.resolution_id
            for item
            in self.init_service_resolutions
        )

        if len(
            resolution_ids
        ) != len(
            set(
                resolution_ids
            )
        ):
            raise ValueError(
                "init_service_resolutions must contain unique "
                "resolution identities"
            )

        if not isinstance(
            self.init_action_requirements,
            tuple,
        ):
            raise TypeError(
                "init_action_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitActionRequirement,
            )
            for item in self.init_action_requirements
        ):
            raise TypeError(
                "init_action_requirements must contain only "
                "AndroidUniverseInitActionRequirement instances"
            )

        canonical_init_action_requirements = tuple(
            sorted(
                self.init_action_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else item.source_path.as_posix()
                    ),
                    item.action.location.line,
                    item.trigger,
                ),
            )
        )

        if (
            self.init_action_requirements
            != canonical_init_action_requirements
        ):
            raise ValueError(
                "init_action_requirements must be in canonical order"
            )

        init_action_requirement_ids = tuple(
            item.requirement_id
            for item in self.init_action_requirements
        )

        if len(
            init_action_requirement_ids
        ) != len(
            set(
                init_action_requirement_ids
            )
        ):
            raise ValueError(
                "init_action_requirements must contain unique "
                "requirement identities"
            )

        if not isinstance(
            self.elf_requirements,
            tuple,
        ):
            raise TypeError(
                "elf_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseElfRequirement,
            )
            for item in self.elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement instances"
            )

        canonical_elf_requirements = tuple(
            sorted(
                self.elf_requirements,
                key=lambda item: (
                    item.source.source.identity_key,
                    item.requirement_id,
                ),
            )
        )

        if (
            self.elf_requirements
            != canonical_elf_requirements
        ):
            raise ValueError(
                "elf_requirements must be in canonical order"
            )

        elf_requirement_ids = tuple(
            item.requirement_id
            for item in self.elf_requirements
        )

        if len(
            elf_requirement_ids
        ) != len(
            set(
                elf_requirement_ids
            )
        ):
            raise ValueError(
                "elf_requirements must contain unique "
                "requirement identities"
            )

        if len(
            self.elf_requirements
        ) != len(
            self.parsing.elf.elf_files
        ):
            raise ValueError(
                "elf_requirements must preserve the complete "
                "Parsing ELF population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.elf_requirements,
                self.parsing.elf.elf_files,
                strict=True,
            )
        ):
            raise ValueError(
                "elf_requirements must preserve exact Parsing "
                "ELF source identity and order"
            )

        if not isinstance(
            self.elf_artifact_associations,
            tuple,
        ):
            raise TypeError(
                "elf_artifact_associations must be a tuple"
            )

        if not all(
            isinstance(
                association,
                AndroidUniverseElfArtifactAssociation,
            )
            for association
            in self.elf_artifact_associations
        ):
            raise TypeError(
                "elf_artifact_associations must contain only "
                "AndroidUniverseElfArtifactAssociation values"
            )

        if (
            len(
                self.elf_artifact_associations
            )
            != len(
                self.elf_requirements
            )
        ):
            raise ValueError(
                "elf_artifact_associations must cover every "
                "canonical ELF requirement exactly once"
            )

        if not all(
            association.elf_requirement
            is requirement
            for association, requirement
            in zip(
                self.elf_artifact_associations,
                self.elf_requirements,
                strict=True,
            )
        ):
            raise ValueError(
                "elf_artifact_associations must preserve exact "
                "ELF requirement identity and order"
            )

        if not isinstance(
            self.kernel_module_elf_associations,
            tuple,
        ):
            raise TypeError(
                "kernel_module_elf_associations must be a tuple"
            )

        if not all(
            isinstance(
                association,
                AndroidUniverseKernelModuleElfAssociation,
            )
            for association
            in self.kernel_module_elf_associations
        ):
            raise TypeError(
                "kernel_module_elf_associations must contain only "
                "AndroidUniverseKernelModuleElfAssociation values"
            )

        expected_kernel_module_requirements = (
            self.kernel_module_requirement.module_requirements
            if self.kernel_module_requirement is not None
            else ()
        )

        if len(
            self.kernel_module_elf_associations
        ) != len(
            expected_kernel_module_requirements
        ):
            raise ValueError(
                "kernel_module_elf_associations must cover every "
                "canonical kernel-module file requirement exactly once"
            )

        if not all(
            association.module_requirement
            is module_requirement
            for association, module_requirement
            in zip(
                self.kernel_module_elf_associations,
                expected_kernel_module_requirements,
                strict=True,
            )
        ):
            raise ValueError(
                "kernel_module_elf_associations must preserve exact "
                "kernel-module requirement identity and order"
            )

        canonical_elf_requirement_object_ids = {
            id(requirement)
            for requirement
            in self.elf_requirements
        }

        if not all(
            id(
                association.elf_requirement
            )
            in canonical_elf_requirement_object_ids
            for association
            in self.kernel_module_elf_associations
        ):
            raise ValueError(
                "kernel_module_elf_associations must reference exact "
                "canonical Universe ELF requirements"
            )

        if not isinstance(
            self.kernel_requirements,
            tuple,
        ):
            raise TypeError(
                "kernel_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseKernelRequirement,
            )
            for item in self.kernel_requirements
        ):
            raise TypeError(
                "kernel_requirements must contain only "
                "AndroidUniverseKernelRequirement instances"
            )

        if len(
            self.kernel_requirements
        ) != len(
            self.parsing.kernels
        ):
            raise ValueError(
                "kernel_requirements must preserve the complete "
                "Parsing kernel population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.kernel_requirements,
                self.parsing.kernels,
                strict=True,
            )
        ):
            raise ValueError(
                "kernel_requirements must preserve exact "
                "Parsing kernel source identity and order"
            )

        if not all(
            requirement.config_count
            == parsed.config_count
            for requirement, parsed
            in zip(
                self.kernel_requirements,
                self.parsing.kernels,
                strict=True,
            )
        ):
            raise ValueError(
                "kernel config requirements must preserve "
                "complete Parsing config populations"
            )

        if not all(
            requirement.unparsed_config_count
            == parsed.unparsed_config_count
            for requirement, parsed
            in zip(
                self.kernel_requirements,
                self.parsing.kernels,
                strict=True,
            )
        ):
            raise ValueError(
                "kernel unparsed evidence must preserve "
                "complete Parsing unparsed-line populations"
            )

        if not isinstance(
            self.vbmeta_requirements,
            tuple,
        ):
            raise TypeError(
                "vbmeta_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVbmetaRequirement,
            )
            for item in self.vbmeta_requirements
        ):
            raise TypeError(
                "vbmeta_requirements must contain only "
                "AndroidUniverseVbmetaRequirement instances"
            )

        if len(
            self.vbmeta_requirements
        ) != len(
            self.parsing.vbmeta
        ):
            raise ValueError(
                "vbmeta_requirements must preserve the complete "
                "Parsing VBMeta population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.vbmeta_requirements,
                self.parsing.vbmeta,
                strict=True,
            )
        ):
            raise ValueError(
                "vbmeta_requirements must preserve exact Parsing "
                "VBMeta source identity and order"
            )

        if not all(
            requirement.metadata is parsed.metadata
            for requirement, parsed
            in zip(
                self.vbmeta_requirements,
                self.parsing.vbmeta,
                strict=True,
            )
        ):
            raise ValueError(
                "vbmeta_requirements must preserve exact Parsing "
                "AVB metadata identity"
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
                AndroidUniverseAvbRegion,
            )
            for region in self.avb_regions
        ):
            raise TypeError(
                "avb_regions must contain only "
                "AndroidUniverseAvbRegion instances"
            )

        if len(
            self.avb_regions
        ) != len(
            self.parsing.avb_regions
        ):
            raise ValueError(
                "avb_regions must conserve the complete "
                "Parsing AVB-region population"
            )

        if not all(
            universe_region.source is parsed_region
            for universe_region, parsed_region
            in zip(
                self.avb_regions,
                self.parsing.avb_regions,
                strict=True,
            )
        ):
            raise ValueError(
                "avb_regions must preserve exact Parsing "
                "AVB-region identity and order"
            )

        vbmeta_requirement_by_source_id = {
            id(requirement.source): requirement
            for requirement
            in self.vbmeta_requirements
        }

        if (
            len(vbmeta_requirement_by_source_id)
            != len(self.vbmeta_requirements)
        ):
            raise ValueError(
                "vbmeta_requirements must contain unique "
                "Parsing VBMeta source identities"
            )

        for universe_region in self.avb_regions:
            parsed_region = (
                universe_region.source
            )

            if (
                parsed_region.disposition
                == "parsed"
            ):
                parsed_vbmeta = (
                    parsed_region.vbmeta
                )

                if parsed_vbmeta is None:
                    raise ValueError(
                        "parsed AVB region must retain its "
                        "ParsedAvbVbmeta identity"
                    )

                expected_requirement = (
                    vbmeta_requirement_by_source_id.get(
                        id(parsed_vbmeta)
                    )
                )

                if expected_requirement is None:
                    raise ValueError(
                        "parsed AVB region references VBMeta "
                        "outside the canonical Universe "
                        "VBMeta population"
                    )

                if (
                    universe_region.vbmeta_requirement
                    is not expected_requirement
                ):
                    raise ValueError(
                        "parsed AVB region must preserve the exact "
                        "corresponding Universe VBMeta requirement"
                    )

            elif (
                universe_region.vbmeta_requirement
                is not None
            ):
                raise ValueError(
                    "non-parsed AVB regions must not gain "
                    "a Universe VBMeta requirement"
                )

        if not isinstance(
            self.avb_topology,
            AndroidUniverseAvbTopology,
        ):
            raise TypeError(
                "avb_topology must be an AndroidUniverseAvbTopology"
            )

        if (
            len(self.avb_topology.requirements)
            != len(self.vbmeta_requirements)
        ):
            raise ValueError(
                "avb_topology must preserve the complete "
                "Universe VBMeta requirement population"
            )

        if not all(
            topology_requirement is requirement
            for topology_requirement, requirement
            in zip(
                self.avb_topology.requirements,
                self.vbmeta_requirements,
                strict=True,
            )
        ):
            raise ValueError(
                "avb_topology must preserve exact Universe VBMeta "
                "requirement identity and order"
            )

        if not isinstance(
            self.bootloader_requirements,
            tuple,
        ):
            raise TypeError(
                "bootloader_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseBootloaderRequirement,
            )
            for item in self.bootloader_requirements
        ):
            raise TypeError(
                "bootloader_requirements must contain only "
                "AndroidUniverseBootloaderRequirement instances"
            )

        if len(
            self.bootloader_requirements
        ) != len(
            self.parsing.bootloader
        ):
            raise ValueError(
                "bootloader_requirements must preserve the complete "
                "Parsing bootloader population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.bootloader_requirements,
                self.parsing.bootloader,
                strict=True,
            )
        ):
            raise ValueError(
                "bootloader_requirements must preserve exact Parsing "
                "bootloader source identity and order"
            )

        if not all(
            requirement.artifact is parsed.artifact
            for requirement, parsed
            in zip(
                self.bootloader_requirements,
                self.parsing.bootloader,
                strict=True,
            )
        ):
            raise ValueError(
                "bootloader_requirements must preserve exact "
                "Extraction artifact identity"
            )

        if not all(
            requirement.parsed is parsed.parsed
            for requirement, parsed
            in zip(
                self.bootloader_requirements,
                self.parsing.bootloader,
                strict=True,
            )
        ):
            raise ValueError(
                "bootloader_requirements must preserve exact "
                "Parsing child payload identity"
            )

        if not isinstance(
            self.bootloader_population,
            AndroidUniverseBootloaderPopulationReconciliation,
        ):
            raise TypeError(
                "bootloader_population must be an "
                "AndroidUniverseBootloaderPopulationReconciliation"
            )

        if (
            self.bootloader_population.source
            is not self.parsing.bootloader_children
        ):
            raise ValueError(
                "bootloader_population must preserve exact canonical "
                "Parsing bootloader_children tuple identity"
            )

        canonical_requirement_ids = {
            id(requirement)
            for requirement
            in self.bootloader_requirements
        }

        reconciled_requirement_ids = {
            id(entry.requirement)
            for entry
            in self.bootloader_population.entries
            if entry.requirement is not None
        }

        if (
            reconciled_requirement_ids
            != canonical_requirement_ids
        ):
            raise ValueError(
                "bootloader_population must reconcile the complete "
                "Universe bootloader requirement population"
            )

        if not isinstance(
            self.sflb_requirements,
            tuple,
        ):
            raise TypeError(
                "sflb_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseSflbRequirement,
            )
            for item in self.sflb_requirements
        ):
            raise TypeError(
                "sflb_requirements must contain only "
                "AndroidUniverseSflbRequirement instances"
            )

        if len(
            self.sflb_requirements
        ) != len(
            self.parsing.sflb
        ):
            raise ValueError(
                "sflb_requirements must preserve the complete "
                "Parsing SFLB population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.sflb_requirements,
                self.parsing.sflb,
                strict=True,
            )
        ):
            raise ValueError(
                "sflb_requirements must preserve exact Parsing "
                "SFLB source identity and order"
            )

        if not all(
            requirement.artifact is parsed.artifact
            for requirement, parsed
            in zip(
                self.sflb_requirements,
                self.parsing.sflb,
                strict=True,
            )
        ):
            raise ValueError(
                "sflb_requirements must preserve exact "
                "Extraction artifact identity"
            )

        if not isinstance(
            self.bmp_requirements,
            tuple,
        ):
            raise TypeError(
                "bmp_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseBmpRequirement,
            )
            for item in self.bmp_requirements
        ):
            raise TypeError(
                "bmp_requirements must contain only "
                "AndroidUniverseBmpRequirement instances"
            )

        if len(
            self.bmp_requirements
        ) != len(
            self.parsing.bmp
        ):
            raise ValueError(
                "bmp_requirements must preserve the complete "
                "Parsing BMP population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.bmp_requirements,
                self.parsing.bmp,
                strict=True,
            )
        ):
            raise ValueError(
                "bmp_requirements must preserve exact Parsing "
                "BMP source identity and order"
            )

        if not all(
            requirement.artifact is parsed.artifact
            for requirement, parsed
            in zip(
                self.bmp_requirements,
                self.parsing.bmp,
                strict=True,
            )
        ):
            raise ValueError(
                "bmp_requirements must preserve exact "
                "Extraction artifact identity"
            )

        if not isinstance(
            self.dtbo_requirements,
            tuple,
        ):
            raise TypeError(
                "dtbo_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboRequirement,
            )
            for item in self.dtbo_requirements
        ):
            raise TypeError(
                "dtbo_requirements must contain only "
                "AndroidUniverseDtboRequirement instances"
            )

        if len(
            self.dtbo_requirements
        ) != len(
            self.parsing.dtbo
        ):
            raise ValueError(
                "dtbo_requirements must preserve the complete "
                "Parsing DTBO population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.dtbo_requirements,
                self.parsing.dtbo,
                strict=True,
            )
        ):
            raise ValueError(
                "dtbo_requirements must preserve exact Parsing "
                "DTBO source identity and order"
            )


        if not isinstance(
            self.dtbo_population,
            AndroidUniverseDtboPopulationReconciliation,
        ):
            raise TypeError(
                "dtbo_population must be an "
                "AndroidUniverseDtboPopulationReconciliation"
            )

        if len(
            self.dtbo_population.entries
        ) != len(
            self.dtbo_requirements
        ):
            raise ValueError(
                "dtbo_population must preserve the complete "
                "Universe DTBO requirement population"
            )

        if not all(
            entry.requirement is requirement
            for entry, requirement
            in zip(
                self.dtbo_population.entries,
                self.dtbo_requirements,
                strict=True,
            )
        ):
            raise ValueError(
                "dtbo_population must preserve exact "
                "DTBO requirement identity and order"
            )

        if not isinstance(
            self.fstab_applicability,
            tuple,
        ):
            raise TypeError(
                "fstab_applicability must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFstabApplicabilityObservation,
            )
            for item in self.fstab_applicability
        ):
            raise TypeError(
                "fstab_applicability must contain only "
                "AndroidUniverseFstabApplicabilityObservation instances"
            )

        canonical_fstab_applicability = tuple(
            sorted(
                self.fstab_applicability,
                key=lambda item: (
                    item.requirement_id,
                    item.resolved_path or "",
                    item.selector_key or "",
                    item.selector_value or "",
                ),
            )
        )

        if (
            self.fstab_applicability
            != canonical_fstab_applicability
        ):
            raise ValueError(
                "fstab_applicability must be in canonical order"
            )

        if not isinstance(
            self.fstab_applicability_conclusions,
            tuple,
        ):
            raise TypeError(
                "fstab_applicability_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRequirementApplicability,
            )
            for item in self.fstab_applicability_conclusions
        ):
            raise TypeError(
                "fstab_applicability_conclusions must contain only "
                "AndroidUniverseRequirementApplicability instances"
            )

        applicability_conclusion_ids = tuple(
            item.requirement_id
            for item in self.fstab_applicability_conclusions
        )

        if applicability_conclusion_ids != tuple(
            sorted(
                applicability_conclusion_ids
            )
        ):
            raise ValueError(
                "fstab_applicability_conclusions must be in "
                "canonical requirement order"
            )

        if len(
            applicability_conclusion_ids
        ) != len(
            set(
                applicability_conclusion_ids
            )
        ):
            raise ValueError(
                "fstab_applicability_conclusions must contain "
                "one entry per requirement"
            )

        requirement_ids = {
            item.requirement_id
            for item in self.fstab_requirements
        }

        if set(
            applicability_conclusion_ids
        ) != requirement_ids:
            raise ValueError(
                "fstab_applicability_conclusions must cover "
                "every fstab requirement exactly once"
            )

        canonical_fstab_requirements = tuple(
            sorted(
                self.fstab_requirements,
                key=lambda item: (
                    (
                        item.android_path.as_posix()
                        if item.android_path is not None
                        else ""
                    ),
                    item.declaration.line_number,
                    item.mount_point,
                    item.device,
                    item.filesystem_type,
                ),
            )
        )

        if (
            self.fstab_requirements
            != canonical_fstab_requirements
        ):
            raise ValueError(
                "fstab_requirements must be in canonical order"
            )

