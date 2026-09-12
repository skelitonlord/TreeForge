from __future__ import annotations

from treeforge.android.universe.avb.boot_signature import (
    AndroidUniverseBootSignatureAvbInterpreter,
)
from treeforge.android.universe.boot.population import (
    AndroidUniverseBootPopulationReconciler,
)

from treeforge.android.universe.bootloader.population import (
    AndroidUniverseBootloaderPopulationReconciler,
)

from treeforge.android.universe.knowledge_application import (
    applied_universe_architecture_knowledge_modules,
    applied_universe_vintf_knowledge_modules,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)

from treeforge.android.universe.fstab.source_context import (
    AndroidUniverseFstabSourceContext,
)

from treeforge.android.universe.architecture import (
    AndroidUniverseArchitectureReconciler,
)
from treeforge.android.universe.relationships.applicability import (
    reconcile_android_relationship_applicability,
)

from treeforge.android.universe.ueventd.source_context import (
    AndroidUniverseUeventdSourceContext,
)
from treeforge.android.universe.ueventd.reconciliation import (
    AndroidUniverseUeventdReconciler,
)
from treeforge.android.universe.capability import (
    AndroidUniverseDeviceCapabilityReconciler,
)

from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementBuilder,
)
from treeforge.android.universe.properties.interpreter import (
    AndroidUniversePropertyInterpreter,
)
from treeforge.android.universe.properties.source_record import (
    AndroidUniversePropertySourceRecord,
)
from treeforge.android.universe.fstab.interpreter import (
    AndroidUniverseFstabInterpreter,
)
from treeforge.android.universe.fstab.applicability import (
    AndroidUniverseFstabApplicabilityInterpreter,
    AndroidUniverseFstabApplicabilityReconciler,
)
from treeforge.android.universe.properties.reconciliation import (
    AndroidUniversePropertyReconciler,
)
from treeforge.android.universe.runtime_property.relevance import (
    AndroidUniverseRuntimePropertyRelevanceReconciler,
)
from treeforge.android.universe.runtime_property import (
    AndroidUniverseRuntimePropertyBuilder,
)
from treeforge.android.universe.init.action_interpreter import (
    AndroidUniverseInitActionInterpreter,
)
from treeforge.android.universe.init.interpreter import (
    AndroidUniverseInitServiceInterpreter,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceReconciler,
)
from treeforge.android.universe.init.import_interpreter import (
    AndroidUniverseInitImportInterpreter,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportReconciler,
    android_init_inapplicable_source_paths,
)
from treeforge.android.universe.init.source_applicability import (
    AndroidUniverseInitSourceApplicabilityReconciler,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)
from treeforge.android.universe.init.source_record import (
    AndroidUniverseInitSourceRecord,
)
from treeforge.android.universe.ueventd.interpreter import (
    AndroidUniverseUeventdInterpreter,
)
from treeforge.android.universe.vintf.applicability import (
    AndroidUniverseVintfApplicabilityReconciler,
)
from treeforge.android.universe.vintf.interpreter import (
    AndroidUniverseVintfInterpreter,
)
from treeforge.android.universe.boot.interpreter import (
    AndroidUniverseBootInterpreter,
)
from treeforge.android.universe.aconfig.interpreter import (
    AndroidUniverseAconfigInterpreter,
)
from treeforge.android.universe.input import (
    AndroidUniverseInputInterpreter,
)
from treeforge.android.universe.font import (
    AndroidUniverseFontInterpreter,
)
from treeforge.android.universe.certificate import (
    AndroidUniverseCertificateInterpreter,
)
from treeforge.android.universe.structured_configuration import (
    AndroidUniverseStructuredConfigurationInterpreter,
)
from treeforge.android.universe.dex import (
    AndroidUniverseStandaloneDexInterpreter,
)
from treeforge.android.universe.avf import (
    AndroidUniverseAvfInterpreter,
)
from treeforge.android.universe.apk.interpreter import (
    AndroidUniverseApkInterpreter,
)
from treeforge.android.universe.classpath.interpreter import (
    AndroidUniverseClasspathInterpreter,
)
from treeforge.android.universe.shell_script import (
    AndroidUniverseShellScriptReconciler,
)
from treeforge.android.universe.art_runtime.interpreter import (
    AndroidUniverseArtRuntimeInterpreter,
)
from treeforge.android.universe.kernel_module.interpreter import (
    AndroidUniverseKernelModuleInterpreter,
)
from treeforge.android.universe.linker.interpreter import (
    AndroidUniverseLinkerInterpreter,
)
from treeforge.android.universe.apex.interpreter import (
    AndroidUniverseApexInterpreter,
)
from treeforge.android.universe.elf.interpreter import (
    AndroidUniverseElfInterpreter,
)
from treeforge.android.universe.elf.artifact_association import (
    AndroidUniverseElfArtifactAssociationBuilder,
)
from treeforge.android.universe.kernel_module.elf_association import (
    AndroidUniverseKernelModuleElfAssociationBuilder,
)
from treeforge.android.universe.elf.apex_alias import (
    AndroidUniverseElfApexFilesystemAliasReconciler,
)
from treeforge.android.universe.kernel.interpreter import (
    AndroidUniverseKernelInterpreter,
)
from treeforge.android.universe.dtbo.interpreter import (
    AndroidUniverseDtboInterpreter,
)
from treeforge.android.universe.dtbo.population import (
    AndroidUniverseDtboPopulationReconciler,
)
from treeforge.android.universe.bootloader import (
    AndroidUniverseBootloaderInterpreter,
)
from treeforge.android.universe.sflb import (
    AndroidUniverseSflbInterpreter,
)
from treeforge.android.universe.bmp import (
    AndroidUniverseBmpInterpreter,
)
from treeforge.android.universe.avb import (
    AndroidUniverseAvbRegionConservator,
    AndroidUniverseAvbTopologyReconciler,
    AndroidUniverseVbmetaInterpreter,
)
from treeforge.android.universe.selinux.interpreter import (
    AndroidUniverseSelinuxInterpreter,
)
from treeforge.android.universe.selinux.reconciliation import (
    AndroidUniverseSelinuxReconciler,
)
from treeforge.android.universe.selinux.applicability import (
    AndroidUniverseSelinuxApplicabilityReconciler,
)
from treeforge.android.universe.selinux.conclusion import (
    conclude_selinux_policy,
)
from treeforge.android.universe.relationships import (
    AndroidUniverseCrossFamilyReconciler,
    AndroidUniverseInitServiceSubstantiationReconciler,
    AndroidUniverseInitServiceTargetSubstantiationReconciler,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.android.universe.parsing_boundary import (
    AndroidUniverseParsingBoundary,
    AndroidUniverseParsingPopulationDisposition,
    AndroidUniverseParsingPopulationDispositionKind,
)
from treeforge.android.universe.filesystem_entry import (
    AndroidUniverseFilesystemEntryRequirementBuilder,
)
from treeforge.android.universe.model_source import (
    AndroidUniverseModelSourceRequirementBuilder,
)
from treeforge.core.pipeline.stage import (
    PipelineStage,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)
from treeforge.android.version.selector import (
    AndroidSemanticVersionSelector,
)


class AndroidDeviceUniverseStage(
    PipelineStage
):
    """
    Own canonical Android device-level interpretation after Parsing.

    This stage is the exclusive semantic boundary between literal Parsing
    observations and all downstream reconstruction, analysis, build, and
    generation behavior.
    """

    name = "Android Device Universe"

    def __init__(
        self,
        *,
        artifact_requirement_builder: (
            AndroidUniverseArtifactRequirementBuilder
            | None
        ) = None,
        property_interpreter: (
            AndroidUniversePropertyInterpreter
            | None
        ) = None,
        property_reconciler: (
            AndroidUniversePropertyReconciler
            | None
        ) = None,
        runtime_property_builder: (
            AndroidUniverseRuntimePropertyBuilder
            | None
        ) = None,
        fstab_interpreter: (
            AndroidUniverseFstabInterpreter
            | None
        ) = None,
        ueventd_interpreter: (
            AndroidUniverseUeventdInterpreter
            | None
        ) = None,
        vintf_interpreter: (
            AndroidUniverseVintfInterpreter
            | None
        ) = None,
        selinux_interpreter: (
            AndroidUniverseSelinuxInterpreter
            | None
        ) = None,
        selinux_reconciler: (
            AndroidUniverseSelinuxReconciler
            | None
        ) = None,
        cross_family_reconciler: (
            AndroidUniverseCrossFamilyReconciler
            | None
        ) = None,
        init_service_substantiation_reconciler: (
            AndroidUniverseInitServiceSubstantiationReconciler
            | None
        ) = None,
        init_service_target_substantiation_reconciler: (
            AndroidUniverseInitServiceTargetSubstantiationReconciler
            | None
        ) = None,
        boot_interpreter: (
            AndroidUniverseBootInterpreter
            | None
        ) = None,
        aconfig_interpreter: (
            AndroidUniverseAconfigInterpreter
            | None
        ) = None,
        apk_interpreter: (
            AndroidUniverseApkInterpreter
            | None
        ) = None,
        classpath_interpreter: (
            AndroidUniverseClasspathInterpreter
            | None
        ) = None,
        art_runtime_interpreter: (
            AndroidUniverseArtRuntimeInterpreter
            | None
        ) = None,
        kernel_module_interpreter: (
            AndroidUniverseKernelModuleInterpreter
            | None
        ) = None,
        linker_interpreter: (
            AndroidUniverseLinkerInterpreter
            | None
        ) = None,
        apex_interpreter: (
            AndroidUniverseApexInterpreter
            | None
        ) = None,
        elf_interpreter: (
            AndroidUniverseElfInterpreter
            | None
        ) = None,
        kernel_interpreter: (
            AndroidUniverseKernelInterpreter
            | None
        ) = None,
        dtbo_interpreter: (
            AndroidUniverseDtboInterpreter
            | None
        ) = None,
        dtbo_population_reconciler: (
            AndroidUniverseDtboPopulationReconciler
            | None
        ) = None,
        vbmeta_interpreter: (
            AndroidUniverseVbmetaInterpreter
            | None
        ) = None,
        avb_region_conservator: (
            AndroidUniverseAvbRegionConservator
            | None
        ) = None,
        avb_topology_reconciler: (
            AndroidUniverseAvbTopologyReconciler
            | None
        ) = None,
        bootloader_interpreter: (
            AndroidUniverseBootloaderInterpreter
            | None
        ) = None,
        sflb_interpreter: (
            AndroidUniverseSflbInterpreter
            | None
        ) = None,
        bmp_interpreter: (
            AndroidUniverseBmpInterpreter
            | None
        ) = None,
        init_import_interpreter: (
            AndroidUniverseInitImportInterpreter
            | None
        ) = None,
        init_service_interpreter: (
            AndroidUniverseInitServiceInterpreter
            | None
        ) = None,
        init_service_reconciler: (
            AndroidUniverseInitServiceReconciler
            | None
        ) = None,
        init_action_interpreter: (
            AndroidUniverseInitActionInterpreter
            | None
        ) = None,
        fstab_applicability_interpreter: (
            AndroidUniverseFstabApplicabilityInterpreter
            | None
        ) = None,
        fstab_applicability_reconciler: (
            AndroidUniverseFstabApplicabilityReconciler
            | None
        ) = None,
        progress_callback: (
            ProgressCallback
            | None
        ) = None,
    ) -> None:
        self.artifact_requirement_builder = (
            artifact_requirement_builder
            if artifact_requirement_builder is not None
            else AndroidUniverseArtifactRequirementBuilder()
        )

        self.property_interpreter = (
            property_interpreter
            if property_interpreter is not None
            else AndroidUniversePropertyInterpreter()
        )

        self.property_reconciler = (
            property_reconciler
            if property_reconciler is not None
            else AndroidUniversePropertyReconciler()
        )

        self.runtime_property_builder = (
            runtime_property_builder
            if runtime_property_builder is not None
            else AndroidUniverseRuntimePropertyBuilder()
        )

        self.fstab_interpreter = (
            fstab_interpreter
            if fstab_interpreter is not None
            else AndroidUniverseFstabInterpreter()
        )

        self.ueventd_interpreter = (
            ueventd_interpreter
            if ueventd_interpreter is not None
            else AndroidUniverseUeventdInterpreter()
        )

        self.vintf_interpreter = (
            vintf_interpreter
            if vintf_interpreter is not None
            else AndroidUniverseVintfInterpreter()
        )

        self.selinux_interpreter = (
            selinux_interpreter
            if selinux_interpreter is not None
            else AndroidUniverseSelinuxInterpreter()
        )

        self.selinux_reconciler = (
            selinux_reconciler
            if selinux_reconciler is not None
            else AndroidUniverseSelinuxReconciler()
        )

        self.selinux_applicability_reconciler = (
            AndroidUniverseSelinuxApplicabilityReconciler()
        )

        self.cross_family_reconciler = (
            cross_family_reconciler
            if cross_family_reconciler is not None
            else AndroidUniverseCrossFamilyReconciler()
        )

        self.init_service_substantiation_reconciler = (
            init_service_substantiation_reconciler
            if init_service_substantiation_reconciler is not None
            else AndroidUniverseInitServiceSubstantiationReconciler()
        )

        self.init_service_target_substantiation_reconciler = (
            init_service_target_substantiation_reconciler
            if (
                init_service_target_substantiation_reconciler
                is not None
            )
            else (
                AndroidUniverseInitServiceTargetSubstantiationReconciler()
            )
        )

        self.boot_interpreter = (
            boot_interpreter
            if boot_interpreter is not None
            else AndroidUniverseBootInterpreter()
        )

        self.aconfig_interpreter = (
            aconfig_interpreter
            if aconfig_interpreter is not None
            else AndroidUniverseAconfigInterpreter()
        )

        self.apk_interpreter = (
            apk_interpreter
            if apk_interpreter is not None
            else AndroidUniverseApkInterpreter()
        )

        self.classpath_interpreter = (
            classpath_interpreter
            if classpath_interpreter is not None
            else AndroidUniverseClasspathInterpreter()
        )

        self.art_runtime_interpreter = (
            art_runtime_interpreter
            if art_runtime_interpreter is not None
            else AndroidUniverseArtRuntimeInterpreter()
        )

        self.kernel_module_interpreter = (
            kernel_module_interpreter
            if kernel_module_interpreter is not None
            else AndroidUniverseKernelModuleInterpreter()
        )

        self.linker_interpreter = (
            linker_interpreter
            if linker_interpreter is not None
            else AndroidUniverseLinkerInterpreter()
        )

        self.apex_interpreter = (
            apex_interpreter
            if apex_interpreter is not None
            else AndroidUniverseApexInterpreter()
        )

        self.elf_interpreter = (
            elf_interpreter
            if elf_interpreter is not None
            else AndroidUniverseElfInterpreter()
        )

        self.kernel_interpreter = (
            kernel_interpreter
            if kernel_interpreter is not None
            else AndroidUniverseKernelInterpreter()
        )

        self.dtbo_interpreter = (
            dtbo_interpreter
            if dtbo_interpreter is not None
            else AndroidUniverseDtboInterpreter()
        )


        self.dtbo_population_reconciler = (
            dtbo_population_reconciler
            if dtbo_population_reconciler is not None
            else AndroidUniverseDtboPopulationReconciler()
        )

        self.vbmeta_interpreter = (
            vbmeta_interpreter
            if vbmeta_interpreter is not None
            else AndroidUniverseVbmetaInterpreter()
        )

        self.avb_region_conservator = (
            avb_region_conservator
            if avb_region_conservator is not None
            else AndroidUniverseAvbRegionConservator()
        )

        self.avb_topology_reconciler = (
            avb_topology_reconciler
            if avb_topology_reconciler is not None
            else AndroidUniverseAvbTopologyReconciler()
        )

        self.bootloader_interpreter = (
            bootloader_interpreter
            if bootloader_interpreter is not None
            else AndroidUniverseBootloaderInterpreter()
        )

        self.sflb_interpreter = (
            sflb_interpreter
            if sflb_interpreter is not None
            else AndroidUniverseSflbInterpreter()
        )

        self.bmp_interpreter = (
            bmp_interpreter
            if bmp_interpreter is not None
            else AndroidUniverseBmpInterpreter()
        )

        self.init_import_interpreter = (
            init_import_interpreter
            if init_import_interpreter is not None
            else AndroidUniverseInitImportInterpreter()
        )

        self.init_service_interpreter = (
            init_service_interpreter
            if init_service_interpreter is not None
            else AndroidUniverseInitServiceInterpreter()
        )

        self.init_service_reconciler = (
            init_service_reconciler
            if init_service_reconciler is not None
            else AndroidUniverseInitServiceReconciler()
        )

        self.init_action_interpreter = (
            init_action_interpreter
            if init_action_interpreter is not None
            else AndroidUniverseInitActionInterpreter()
        )

        self.fstab_applicability_interpreter = (
            fstab_applicability_interpreter
            if fstab_applicability_interpreter is not None
            else AndroidUniverseFstabApplicabilityInterpreter()
        )

        self.fstab_applicability_reconciler = (
            fstab_applicability_reconciler
            if fstab_applicability_reconciler is not None
            else AndroidUniverseFstabApplicabilityReconciler()
        )

        self.progress_callback = (
            progress_callback
        )

    def preflight(
        self,
        context: Context,
    ):
        """
        Exercise Universe runtime contracts without failing at the first
        independent semantic operation.

        Semantic work remains delegated to this stage's exact production
        collaborators. The diagnostic runner owns only dependency-aware
        orchestration and reporting.
        """

        from treeforge.android.universe.preflight import (
            AndroidDeviceUniversePreflightRunner,
        )

        return (
            AndroidDeviceUniversePreflightRunner(
                self
            )
            .run(
                context
            )
        )

    def execute(
        self,
        context: Context,
    ) -> None:
        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

        if context.android_parsing is None:
            raise RuntimeError(
                "Android Parsing must complete before "
                "Android Device Universe"
            )


        #
        # APEX semantic identity is required as contextual evidence by the
        # artifact requirement builder. Interpret it once here and retain this
        # exact canonical tuple for final Universe assembly.
        #
        apex_requirements = (
            self.apex_interpreter.interpret(
                context.android_parsing.apex
            )
        )

        self._report_progress(
            current=1,
            total=37,
            operation="ELF",
            state=ProgressState.RUNNING,
        )

        elf_requirements = (
            self.elf_interpreter.interpret(
                context.android_parsing.elf,
                filesystem_inventory=(
                    context.android_parsing
                    .filesystem_inventory
                ),
            )
        )

        elf_requirements = tuple(
            sorted(
                elf_requirements,
                key=lambda item: (
                    item.source.source.identity_key,
                    item.requirement_id,
                ),
            )
        )

        self._report_progress(
            current=1,
            total=37,
            operation="ELF",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=2,
            total=37,
            operation="kernel",
            state=ProgressState.RUNNING,
        )

        kernel_requirements = (
            self.kernel_interpreter.interpret(
                context.android_parsing.kernels
            )
        )

        self._report_progress(
            current=2,
            total=37,
            operation="kernel",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=3,
            total=37,
            operation="DTBO",
            state=ProgressState.RUNNING,
        )

        dtbo_requirements = (
            self.dtbo_interpreter.interpret(
                context.android_parsing.dtbo
            )
        )

        self._report_progress(
            current=3,
            total=37,
            operation="DTBO",
            state=ProgressState.COMPLETE,
        )


        self._report_progress(
            current=4,
            total=37,
            operation="DTBO population reconciliation",
            state=ProgressState.RUNNING,
        )

        dtbo_population = (
            self.dtbo_population_reconciler.reconcile(
                dtbo_requirements
            )
        )

        self._report_progress(
            current=4,
            total=37,
            operation="DTBO population reconciliation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=5,
            total=37,
            operation="VBMeta / AVB",
            state=ProgressState.RUNNING,
        )

        vbmeta_requirements = (
            self.vbmeta_interpreter.interpret(
                context.android_parsing.vbmeta
            )
        )

        avb_regions = (
            self.avb_region_conservator.conserve(
                context.android_parsing.avb_regions,
                vbmeta_requirements,
            )
        )

        self._report_progress(
            current=5,
            total=37,
            operation="VBMeta / AVB",
            state=ProgressState.COMPLETE,
        )


        self._report_progress(
            current=6,
            total=37,
            operation="AVB topology reconciliation",
            state=ProgressState.RUNNING,
        )

        avb_topology = (
            self.avb_topology_reconciler.reconcile(
                vbmeta_requirements
            )
        )

        self._report_progress(
            current=6,
            total=37,
            operation="AVB topology reconciliation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=7,
            total=37,
            operation="Bootloader",
            state=ProgressState.RUNNING,
        )

        bootloader_requirements = (
            self.bootloader_interpreter.interpret(
                context.android_parsing.bootloader
            )
        )

        bootloader_population = (
            AndroidUniverseBootloaderPopulationReconciler()
            .reconcile(
                context.android_parsing.bootloader_children,
                bootloader_requirements,
            )
        )

        self._report_progress(
            current=7,
            total=37,
            operation="Bootloader",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=8,
            total=37,
            operation="SFLB",
            state=ProgressState.RUNNING,
        )

        sflb_requirements = (
            self.sflb_interpreter.interpret(
                context.android_parsing.sflb
            )
        )

        self._report_progress(
            current=8,
            total=37,
            operation="SFLB",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=9,
            total=37,
            operation="BMP",
            state=ProgressState.RUNNING,
        )

        bmp_requirements = (
            self.bmp_interpreter.interpret(
                context.android_parsing.bmp
            )
        )

        self._report_progress(
            current=9,
            total=37,
            operation="BMP",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=10,
            total=37,
            operation="artifact requirements",
            state=ProgressState.RUNNING,
        )

        artifact_requirements = (
            self.artifact_requirement_builder.build(
                context.android_parsing.filesystem_inventory,
                parsing_source_inventory=(
                    context.android_parsing.source_inventory
                ),
                apk_parsing=(
                    context.android_parsing.apk
                ),
                elf_parsing=(
                    context.android_parsing.elf
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        filesystem_entry_requirements = (
            AndroidUniverseFilesystemEntryRequirementBuilder()
            .build(
                context.android_parsing.filesystem_inventory,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        model_source_requirements = (
            AndroidUniverseModelSourceRequirementBuilder()
            .build(
                context.android_parsing.source_inventory
            )
        )

        self._report_progress(
            current=10,
            total=37,
            operation="artifact requirements",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=11,
            total=37,
            operation="properties",
            state=ProgressState.RUNNING,
        )

        property_source_records = tuple(
            sorted(
                (
                    AndroidUniversePropertySourceRecord(
                        parsed_source=source,
                        model_source=source.source,
                    )
                    for source
                    in context.android_parsing.filesystem.property_files
                ),
                key=lambda record: (
                    record.identity_key
                ),
            )
        )

        property_evidence = (
            self.property_interpreter.interpret(
                parsing=(
                    context.android_parsing.filesystem
                ),
                source_inventory=(
                    context.android_parsing.source_inventory
                ),
            )
        )

        property_evidence = tuple(
            sorted(
                property_evidence,
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

        self._report_progress(
            current=11,
            total=37,
            operation="properties",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=12,
            total=37,
            operation="property reconciliation",
            state=ProgressState.RUNNING,
        )

        conclusions = (
            self.property_reconciler.reconcile(
                property_evidence
            )
        )

        context.android_semantic_version = (
            AndroidSemanticVersionSelector()
            .select(
                conclusions=conclusions,
                requested_override=(
                    context.requested_android_version
                ),
            )
        )

        self._report_progress(
            current=12,
            total=37,
            operation="property reconciliation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=13,
            total=37,
            operation="fstab",
            state=ProgressState.RUNNING,
        )

        fstab_requirements = (
            self.fstab_interpreter.interpret(
                context.android_parsing.filesystem.fstabs
            )
        )

        fstab_source_contexts = tuple(
            sorted(
                (
                    AndroidUniverseFstabSourceContext
                    .from_parsed(source)
                    for source
                    in context.android_parsing.filesystem.fstabs
                ),
                key=lambda source_context: (
                    source_context.source_identity
                ),
            )
        )

        fstab_source_context_ids = tuple(
            source_context.source_identity
            for source_context
            in fstab_source_contexts
        )

        if len(
            fstab_source_context_ids
        ) != len(
            set(fstab_source_context_ids)
        ):
            raise ValueError(
                "canonical fstab source contexts must have "
                "unique source identities"
            )

        fstab_requirements = tuple(
            sorted(
                fstab_requirements,
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

        self._report_progress(
            current=13,
            total=37,
            operation="fstab",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=14,
            total=37,
            operation="ueventd",
            state=ProgressState.RUNNING,
        )

        ueventd_requirements = (
            self.ueventd_interpreter.interpret(
                context.android_parsing.filesystem.ueventd_files
            )
        )

        ueventd_source_contexts = tuple(
            sorted(
                (
                    AndroidUniverseUeventdSourceContext.from_parsed(
                        source
                    )
                    for source
                    in context.android_parsing.filesystem.ueventd_files
                ),
                key=lambda source_context: (
                    source_context.source_identity
                ),
            )
        )

        ueventd_source_context_ids = tuple(
            source_context.source_identity
            for source_context in ueventd_source_contexts
        )

        if len(
            ueventd_source_context_ids
        ) != len(
            set(
                ueventd_source_context_ids
            )
        ):
            raise ValueError(
                "canonical UEVENTD source contexts must have "
                "unique source identities"
            )

        ueventd_reconciliation = (
            AndroidUniverseUeventdReconciler.reconcile(
                tuple(
                    ueventd_requirements
                )
            )
        )

        ueventd_requirements = tuple(
            sorted(
                ueventd_requirements,
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

        self._report_progress(
            current=14,
            total=37,
            operation="ueventd",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=15,
            total=37,
            operation="boot",
            state=ProgressState.RUNNING,
        )

        boot_requirements = (
            self.boot_interpreter.interpret(
                context.android_parsing.boot_images
            )
        )


        boot_signature_avb_requirements = (
            AndroidUniverseBootSignatureAvbInterpreter()
            .interpret(
                context.android_parsing.boot_signatures
            )
        )

        boot_population = (
            AndroidUniverseBootPopulationReconciler()
            .reconcile(
                boot_requirements=(
                    boot_requirements
                ),
                boot_dtbs=(
                    context.android_parsing.boot_dtbs
                ),
                vendor_ramdisk_tables=(
                    context.android_parsing.vendor_ramdisk_tables
                ),
                ramdisks=(
                    context.android_parsing.ramdisks
                ),
                boot_signatures=(
                    context.android_parsing.boot_signatures
                ),
                boot_signature_avb_requirements=(
                    boot_signature_avb_requirements
                ),
            )
        )

        self._report_progress(
            current=15,
            total=37,
            operation="boot",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=16,
            total=37,
            operation="APEX",
            state=ProgressState.RUNNING,
        )

        #
        # apex_requirements was interpreted before artifact classification
        # because artifact semantics may depend on exact APEX ownership.
        # Reuse that exact canonical tuple here.
        #

        self._report_progress(
            current=16,
            total=37,
            operation="APEX",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=17,
            total=37,
            operation="VINTF",
            state=ProgressState.RUNNING,
        )

        vintf_requirements = (
            self.vintf_interpreter.interpret(
                context.android_parsing.filesystem.vintf_documents
            )
        )

        vintf_requirements = tuple(
            sorted(
                vintf_requirements,
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

        self._report_progress(
            current=17,
            total=37,
            operation="VINTF",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=18,
            total=37,
            operation="SELinux",
            state=ProgressState.RUNNING,
        )

        selinux_requirements = (
            self.selinux_interpreter.interpret(
                context.android_parsing.filesystem.selinux_sources
            )
        )

        selinux_requirements = tuple(
            sorted(
                selinux_requirements,
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

        self._report_progress(
            current=18,
            total=37,
            operation="SELinux",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=19,
            total=37,
            operation="SELinux reconciliation",
            state=ProgressState.RUNNING,
        )

        selinux_policy_graph = (
            self.selinux_reconciler.reconcile(
                selinux_requirements
            )
        )

        self._report_progress(
            current=19,
            total=37,
            operation="SELinux reconciliation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=20,
            total=37,
            operation="SELinux conclusions",
            state=ProgressState.RUNNING,
        )

        selinux_conclusions = (
            conclude_selinux_policy(
                selinux_policy_graph
            )
        )

        selinux_applicability = (
            self.selinux_applicability_reconciler.reconcile(
                requirements=selinux_requirements,
            )
        )

        self._report_progress(
            current=20,
            total=37,
            operation="SELinux conclusions",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=21,
            total=37,
            operation="init imports",
            state=ProgressState.RUNNING,
        )

        init_source_records = tuple(
            sorted(
                (
                    AndroidUniverseInitSourceRecord(
                        parsed_source=source,
                        model_source=source.source,
                    )
                    for source
                    in context.android_parsing.filesystem.init_files
                ),
                key=lambda record: (
                    record.identity_key
                ),
            )
        )

        init_import_requirements = (
            self.init_import_interpreter.interpret(
                context.android_parsing.filesystem.init_files
            )
        )

        init_import_requirements = tuple(
            sorted(
                init_import_requirements,
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

        self._report_progress(
            current=21,
            total=37,
            operation="init imports",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=22,
            total=37,
            operation="init services",
            state=ProgressState.RUNNING,
        )

        init_service_requirements = (
            self.init_service_interpreter.interpret(
                context.android_parsing.filesystem.init_files
            )
        )

        init_service_requirements = tuple(
            sorted(
                init_service_requirements,
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

        self._report_progress(
            current=22,
            total=37,
            operation="init services",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=23,
            total=37,
            operation="init actions",
            state=ProgressState.RUNNING,
        )

        init_action_requirements = (
            self.init_action_interpreter.interpret(
                context.android_parsing.filesystem.init_files
            )
        )

        init_action_requirements = tuple(
            sorted(
                init_action_requirements,
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

        self._report_progress(
            current=23,
            total=37,
            operation="init actions",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=24,
            total=37,
            operation="init reconciliation",
            state=ProgressState.RUNNING,
        )

        property_resolution_requirements = (
            self.runtime_property_builder.build(
                parsing=(
                    context.android_parsing.filesystem
                ),
                source_inventory=(
                    context.android_parsing.source_inventory
                ),
                init_services=(
                    init_service_requirements
                ),
                init_actions=(
                    init_action_requirements
                ),
                boot_requirements=(
                    boot_requirements
                ),
                selinux_graph=(
                    selinux_policy_graph
                ),
                shell_scripts=(
                    context.android_parsing.shell_script
                ),
            )
        )

        init_import_resolutions = (
            AndroidUniverseInitImportReconciler().reconcile(
                requirements=(
                    init_import_requirements
                ),
                sources=(
                    context.android_parsing.filesystem.init_files
                ),
                runtime_properties=(
                    property_resolution_requirements
                ),
                external_target_paths=frozenset(
                    requirement.android_path
                    for requirement
                    in ueventd_requirements
                    if (
                        requirement.android_path is not None
                        and (
                            AndroidUniverseRuntimeContextResolver
                            .resolve_optional_filesystem_source(
                                getattr(
                                    requirement,
                                    "filesystem_source",
                                    None,
                                )
                            )
                            .is_root
                        )
                    )
                ),
            )
        )

        init_service_resolutions = (
            self.init_service_reconciler.reconcile(
                init_service_requirements,
                import_resolutions=(
                    init_import_resolutions
                ),
            )
        )

        init_source_applicability = (
            AndroidUniverseInitSourceApplicabilityReconciler
            .reconcile(
                sources=(
                    context.android_parsing.filesystem.init_files
                ),

                import_requirements=(
                    init_import_requirements
                ),
                service_requirements=(
                    init_service_requirements
                ),
                action_requirements=(
                    init_action_requirements
                ),
                import_resolutions=(
                    init_import_resolutions
                ),
                service_resolutions=(
                    init_service_resolutions
                ),
            )
        )

        inapplicable_init_source_paths = (
            android_init_inapplicable_source_paths(
                init_import_resolutions
            )
        )

        runtime_property_requirements = (
            property_resolution_requirements
        )

        runtime_property_relevance = (
            AndroidUniverseRuntimePropertyRelevanceReconciler.reconcile(
                requirements=(
                    runtime_property_requirements
                ),
                init_service_resolutions=(
                    init_service_resolutions
                ),
                init_source_applicability=(
                    init_source_applicability
                ),
            )
        )

        self._report_progress(
            current=24,
            total=37,
            operation="init reconciliation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=25,
            total=37,
            operation="cross-family relationships",
            state=ProgressState.RUNNING,
        )

        vintf_applicability = (
            AndroidUniverseVintfApplicabilityReconciler()
            .reconcile(
                requirements=vintf_requirements,
                knowledge_modules=(
                    applied_universe_vintf_knowledge_modules(
                        context
                    )
                ),
            )
        )

        cross_family_relationships = (
            self.cross_family_reconciler.reconcile(
                init_services=(
                    init_service_requirements
                ),
                init_import_resolutions=(
                    init_import_resolutions
                ),
                init_service_resolutions=(
                    init_service_resolutions
                ),
                init_actions=(
                    init_action_requirements
                ),
                property_evidence=(
                    property_evidence
                ),
                runtime_property_requirements=(
                    runtime_property_requirements
                ),
                vintf_requirements=(
                    vintf_requirements
                ),
                artifact_requirements=(
                    artifact_requirements
                ),
                apex_requirements=(
                    apex_requirements
                ),
                selinux_graph=(
                    selinux_policy_graph
                ),
            )
        )

        cross_family_relationship_applicability = (
            reconcile_android_relationship_applicability(
                relationships=(
                    cross_family_relationships
                ),
                init_import_resolutions=(
                    init_import_resolutions
                ),
                init_service_resolutions=(
                    init_service_resolutions
                ),
                init_source_applicability=(
                    init_source_applicability
                ),
            )
        )

        self._report_progress(
            current=25,
            total=37,
            operation="cross-family relationships",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=26,
            total=37,
            operation="init service substantiation",
            state=ProgressState.RUNNING,
        )

        init_service_substantiations = (
            self.init_service_substantiation_reconciler.reconcile(
                services=(
                    init_service_requirements
                ),
                relationships=(
                    cross_family_relationships
                ),
                source_inventory=(
                    context.android_parsing.source_inventory
                ),
            )
        )

        self._report_progress(
            current=26,
            total=37,
            operation="init service substantiation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=27,
            total=37,
            operation="init service target substantiation",
            state=ProgressState.RUNNING,
        )

        init_service_target_substantiations = (
            self.init_service_target_substantiation_reconciler.reconcile(
                relationships=(
                    cross_family_relationships
                ),
                relationship_applicability=(
                    cross_family_relationship_applicability
                ),
                init_service_resolutions=(
                    init_service_resolutions
                ),
                selinux_policy_graph=(
                    selinux_policy_graph
                ),
            )
        )

        self._report_progress(
            current=27,
            total=37,
            operation="init service target substantiation",
            state=ProgressState.COMPLETE,
        )

        avf_requirement = (
            AndroidUniverseAvfInterpreter()
            .interpret(
                context.android_parsing.avf_vm_config,
                artifact_requirements=(
                    artifact_requirements
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        self._report_progress(
            current=28,
            total=37,
            operation="fstab applicability",
            state=ProgressState.RUNNING,
        )

        fstab_applicability = (
            self.fstab_applicability_interpreter.interpret(
                parsing=(
                    context.android_parsing.filesystem
                ),
                requirements=fstab_requirements,
                init_action_requirements=(
                    init_action_requirements
                ),
            )
        )

        fstab_applicability = tuple(
            sorted(
                fstab_applicability,
                key=lambda item: (
                    item.requirement_id,
                    item.resolved_path or "",
                    item.selector_key or "",
                    item.selector_value or "",
                ),
            )
        )

        self._report_progress(
            current=28,
            total=37,
            operation="fstab applicability",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=29,
            total=37,
            operation="fstab applicability reconciliation",
            state=ProgressState.RUNNING,
        )

        fstab_applicability_conclusions = (
            self.fstab_applicability_reconciler.reconcile(
                requirements=fstab_requirements,
                observations=fstab_applicability,
                avf_requirement=avf_requirement,
            )
        )

        self._report_progress(
            current=29,
            total=37,
            operation="fstab applicability reconciliation",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=30,
            total=37,
            operation="architecture",
            state=ProgressState.RUNNING,
        )

        architecture = (
            AndroidUniverseArchitectureReconciler()
            .reconcile(
                property_evidence=property_evidence,
                elf_requirements=elf_requirements,
                knowledge_modules=(
                    applied_universe_architecture_knowledge_modules(
                        context
                    )
                ),
            )
        )

        self._report_progress(
            current=30,
            total=37,
            operation="architecture",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=31,
            total=37,
            operation="Aconfig",
            state=ProgressState.RUNNING,
        )

        aconfig_requirement = (
            self.aconfig_interpreter.interpret(
                context.android_parsing.aconfig
            )
        )

        input_requirement = (
            AndroidUniverseInputInterpreter()
            .interpret(
                context.android_parsing.input,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        font_requirement = (
            AndroidUniverseFontInterpreter()
            .interpret(
                context.android_parsing.font,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        certificate_requirement = (
            AndroidUniverseCertificateInterpreter()
            .interpret(
                context.android_parsing.certificate,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        structured_configuration_requirement = (
            AndroidUniverseStructuredConfigurationInterpreter()
            .interpret(
                context.android_parsing.structured_configuration,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        dex_requirement = (
            AndroidUniverseStandaloneDexInterpreter()
            .interpret(
                context.android_parsing.dex,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        self._report_progress(
            current=31,
            total=37,
            operation="Aconfig",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=32,
            total=37,
            operation="APK",
            state=ProgressState.RUNNING,
        )

        apk_requirement = (
            self.apk_interpreter.interpret(
                context.android_parsing.apk,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        self._report_progress(
            current=32,
            total=37,
            operation="APK",
            state=ProgressState.COMPLETE,
        )

        apk_vintf_relationships = (
            self.cross_family_reconciler
            .reconcile_apk_vintf(
                apk_requirement=(
                    apk_requirement
                ),
                vintf_requirements=(
                    vintf_requirements
                ),
            )
        )

        if apk_vintf_relationships:
            cross_family_relationships = tuple(
                sorted(
                    (
                        *cross_family_relationships,
                        *apk_vintf_relationships,
                    ),
                    key=lambda item: (
                        item.kind.value,
                        item.relationship_id,
                    ),
                )
            )

            apk_vintf_relationship_applicability = (
                reconcile_android_relationship_applicability(
                    relationships=(
                        apk_vintf_relationships
                    ),
                    init_import_resolutions=(
                        init_import_resolutions
                    ),
                    init_service_resolutions=(
                        init_service_resolutions
                    ),
                    init_source_applicability=(
                        init_source_applicability
                    ),
                )
            )

            cross_family_relationship_applicability = tuple(
                sorted(
                    (
                        *cross_family_relationship_applicability,
                        *apk_vintf_relationship_applicability,
                    ),
                    key=lambda item: (
                        item.requirement_id
                    ),
                )
            )

        self._report_progress(
            current=33,
            total=37,
            operation="Classpath",
            state=ProgressState.RUNNING,
        )

        classpath_requirement = (
            self.classpath_interpreter.interpret(
                context.android_parsing.classpath,
                java_archives=(
                    context.android_parsing.java_archive
                ),
                property_conclusions=conclusions,
                apex_requirements=apex_requirements,
                artifact_requirements=artifact_requirements,
            )
        )

        self._report_progress(
            current=33,
            total=37,
            operation="Classpath",
            state=ProgressState.COMPLETE,
        )

        shell_script_reconciliation = (
            AndroidUniverseShellScriptReconciler()
            .reconcile(
                context.android_parsing.shell_script,
                artifact_requirements=(
                    artifact_requirements
                ),
                java_archive_reconciliation=(
                    None
                    if classpath_requirement is None
                    else (
                        classpath_requirement
                        .java_archive_reconciliation
                    )
                ),
            )
        )

        self._report_progress(
            current=34,
            total=37,
            operation="ART Runtime",
            state=ProgressState.RUNNING,
        )

        art_runtime_requirement = (
            self.art_runtime_interpreter.interpret(
                context.android_parsing.art_runtime
            )
        )

        self._report_progress(
            current=34,
            total=37,
            operation="ART Runtime",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=35,
            total=37,
            operation="Kernel Modules",
            state=ProgressState.RUNNING,
        )

        kernel_module_requirement = (
            self.kernel_module_interpreter.interpret(
                context.android_parsing.kernel_modules,
                context.android_parsing.kernel_module_configurations,
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        self._report_progress(
            current=35,
            total=37,
            operation="Kernel Modules",
            state=ProgressState.COMPLETE,
        )

        self._report_progress(
            current=36,
            total=37,
            operation="Linker",
            state=ProgressState.RUNNING,
        )

        linker_requirement = (
            self.linker_interpreter.interpret(
                context.android_parsing.linker_configurations,
                context.android_parsing.linker_protobuf_configurations,
                context.android_parsing.native_library_configurations,
            )
        )

        linker_apex_relationships = (
            self.cross_family_reconciler
            .reconcile_linker_apex(
                linker_requirement=(
                    linker_requirement
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        if linker_apex_relationships:
            cross_family_relationships = tuple(
                sorted(
                    (
                        *cross_family_relationships,
                        *linker_apex_relationships,
                    ),
                    key=lambda item: (
                        item.kind.value,
                        item.relationship_id,
                    ),
                )
            )

            cross_family_relationship_applicability = tuple(
                sorted(
                    (
                        *cross_family_relationship_applicability,
                        *(
                            AndroidUniverseRequirementApplicability(
                                requirement_id=(
                                    relationship.relationship_id
                                ),
                                status=(
                                    AndroidUniverseApplicabilityStatus.ACTIVE
                                ),
                            )
                            for relationship
                            in linker_apex_relationships
                        ),
                    ),
                    key=lambda item: (
                        item.requirement_id
                    ),
                )
            )

        linker_apex_namespace_inputs = (
            self.cross_family_reconciler
            .reconcile_linker_apex_namespace_inputs(
                linker_requirement=(
                    linker_requirement
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        treble_fact_conclusions = tuple(
            conclusion
            for conclusion
            in conclusions
            if conclusion.fact == "treble_enabled"
        )

        if len(
            treble_fact_conclusions
        ) > 1:
            raise RuntimeError(
                "canonical property reconciliation produced multiple "
                "treble_enabled conclusions"
            )

        treble_enabled = None

        if treble_fact_conclusions:
            treble_value = (
                treble_fact_conclusions[
                    0
                ].value
            )

            if treble_value == "true":
                treble_enabled = True

            elif treble_value == "false":
                treble_enabled = False

        linker_apex_context_applicability = (
            self.cross_family_reconciler
            .reconcile_linker_apex_context_applicability(
                relationships=(
                    linker_apex_relationships
                ),
                treble_enabled=(
                    treble_enabled
                ),
            )
        )

        linker_apex_public_library_conclusions = (
            self.cross_family_reconciler
            .reconcile_linker_apex_public_libraries(
                linker_requirement=(
                    linker_requirement
                ),
                apex_requirements=(
                    apex_requirements
                ),
                treble_enabled=(
                    treble_enabled
                ),
            )
        )

        linker_apex_native_library_conclusions = (
            self.cross_family_reconciler
            .reconcile_linker_apex_native_libraries(
                context_applicability=(
                    linker_apex_context_applicability
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        linker_elf_contexts = (
            self.cross_family_reconciler
            .reconcile_linker_elf_contexts(
                linker_requirement=(
                    linker_requirement
                ),
                elf_requirements=(
                    elf_requirements
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        (
            elf_requirements,
            linker_elf_contexts,
        ) = (
            AndroidUniverseElfApexFilesystemAliasReconciler
            .reconcile(
                elf_requirements=(
                    elf_requirements
                ),
                linker_elf_contexts=(
                    linker_elf_contexts
                ),
                apex_requirements=(
                    apex_requirements
                ),
                source_inventory=(
                    context
                    .android_parsing
                    .source_inventory
                ),
                filesystem_inventory=(
                    context
                    .android_parsing
                    .filesystem_inventory
                ),
            )
        )

        elf_artifact_associations = (
            AndroidUniverseElfArtifactAssociationBuilder()
            .build(
                elf_requirements=(
                    elf_requirements
                ),
                artifact_requirements=(
                    artifact_requirements
                ),
            )
        )

        kernel_module_elf_associations = (
            AndroidUniverseKernelModuleElfAssociationBuilder()
            .build(
                kernel_module_requirement=(
                    kernel_module_requirement
                ),
                elf_requirements=(
                    elf_requirements
                ),
            )
        )

        self._report_progress(
            current=36,
            total=37,
            operation="Linker",
            state=ProgressState.COMPLETE,
        )

        art_runtime_classpath_relationships = (
            self.cross_family_reconciler
            .reconcile_art_runtime_classpath(
                classpath_requirement=(
                    classpath_requirement
                ),
                art_runtime_requirement=(
                    art_runtime_requirement
                ),
            )
        )

        if art_runtime_classpath_relationships:
            cross_family_relationships = tuple(
                sorted(
                    (
                        *cross_family_relationships,
                        *art_runtime_classpath_relationships,
                    ),
                    key=lambda item: (
                        item.kind.value,
                        item.relationship_id,
                    ),
                )
            )

            cross_family_relationship_applicability = tuple(
                sorted(
                    (
                        *cross_family_relationship_applicability,
                        *(
                            AndroidUniverseRequirementApplicability(
                                requirement_id=(
                                    relationship.relationship_id
                                ),
                                status=(
                                    AndroidUniverseApplicabilityStatus.ACTIVE
                                ),
                            )
                            for relationship
                            in art_runtime_classpath_relationships
                        ),
                    ),
                    key=lambda item: (
                        item.requirement_id
                    ),
                )
            )

        first_stage_kernel_module_relationships = (
            self.cross_family_reconciler
            .reconcile_first_stage_kernel_module_loading(
                boot_requirements=boot_requirements,
                kernel_module_requirement=(
                    kernel_module_requirement
                ),
            )
        )

        if first_stage_kernel_module_relationships:
            cross_family_relationships = tuple(
                sorted(
                    (
                        *cross_family_relationships,
                        *first_stage_kernel_module_relationships,
                    ),
                    key=lambda item: (
                        item.kind.value,
                        item.relationship_id,
                    ),
                )
            )

            cross_family_relationship_applicability = tuple(
                sorted(
                    (
                        *cross_family_relationship_applicability,
                        *(
                            AndroidUniverseRequirementApplicability(
                                requirement_id=relationship.relationship_id,
                                status=(
                                    AndroidUniverseApplicabilityStatus.ACTIVE
                                ),
                            )
                            for relationship
                            in first_stage_kernel_module_relationships
                        ),
                    ),
                    key=lambda item: (
                        item.requirement_id
                    ),
                )
            )

        self._report_progress(
            current=37,
            total=37,
            operation="canonical Universe assembly",
            state=ProgressState.RUNNING,
        )

        parsing = context.android_parsing

        parsing_boundary = AndroidUniverseParsingBoundary(
            parsing=parsing,
            dispositions=(
                AndroidUniverseParsingPopulationDisposition(
                    population_name="filesystem_inventory",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.filesystem_inventory,
                    universe_values=(
                        artifact_requirements,
                        filesystem_entry_requirements,
                    ),
                    reason=(
                        "Universe conserves every canonical filesystem "
                        "metadata entry in a complete filesystem-entry ledger, "
                        "promotes every regular file into the Artifact family, "
                        "and retains non-regular entries for structural, alias, "
                        "special-node, or explicit unresolved semantics."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="source_inventory",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.source_inventory,
                    universe_values=(
                        artifact_requirements,
                        model_source_requirements,
                    ),
                    reason=(
                        "Universe conserves every canonical Android model "
                        "source in a complete source-level ownership ledger; "
                        "source kinds with a current semantic owner are "
                        "explicitly identified and source kinds whose required "
                        "Universe semantics are not yet implemented remain "
                        "explicitly unresolved."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="filesystem",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.filesystem,
                    universe_values=(
                        *property_source_records,
                        *property_evidence,
                        *fstab_source_contexts,
                        *fstab_requirements,
                        *ueventd_source_contexts,
                        *ueventd_requirements,
                        *vintf_requirements,
                        *selinux_requirements,
                        *init_source_records,
                        *init_import_requirements,
                        *init_service_requirements,
                        *init_action_requirements,
                    ),
                    reason=(
                        "Universe conserves every filesystem Parsing source "
                        "and semantically interprets properties, fstab, "
                        "ueventd, VINTF, SELinux, and INIT; complete source "
                        "records/contexts retain declaration-empty and "
                        "unparsed source material without reinterpreting it."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="elf",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.elf,
                    universe_values=(
                        *elf_requirements,
                        *elf_artifact_associations,
                    ),
                    reason=(
                        "Universe promotes every parsed ELF object into its "
                        "canonical ELF requirement population and records one "
                        "exact physical-artifact association per ELF, preserving "
                        "filesystem Artifact identity or embedded Extraction "
                        "artifact identity as appropriate."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="art_runtime",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.art_runtime,
                    universe_values=(
                        (art_runtime_requirement,)
                        if art_runtime_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets and reconciles ART runtime "
                        "Parsing evidence."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="dex",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.dex,
                    universe_values=(
                        dex_requirement,
                    ),
                    reason=(
                        "Universe conserves the complete canonical standalone "
                        "DEX-family Parsing population, including parsed "
                        "standard DEX and explicitly unsupported CompactDex "
                        "dispositions, and reconciles each filesystem-backed "
                        "source to its exact Artifact payload. APK-member, "
                        "Java-archive-member, and VDEX-contained DEX remain "
                        "owned by their canonical container populations; no "
                        "cross-family association is inferred from filenames, "
                        "paths, signatures, or payload similarity."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="classpath",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.classpath,
                    universe_values=(
                        (classpath_requirement,)
                        if classpath_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe evaluates classpath applicability, "
                        "effective assembly, and installed-JAR resolution."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="aconfig",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.aconfig,
                    universe_values=(
                        (aconfig_requirement,)
                        if aconfig_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets the canonical Aconfig Parsing "
                        "population."
                    ),
                ),

                # -----------------------------------------------------------
                # Known Universe semantic gaps.
                # These remain explicit UNRESOLVED entries until their
                # family audits/consumers are implemented. Do not recast
                # them as pass-through merely to make the ledger look clean.
                # -----------------------------------------------------------

                AndroidUniverseParsingPopulationDisposition(
                    population_name="input",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.input,
                    universe_values=(
                        input_requirement,
                    ),
                    reason=(
                        "Universe conserves every canonical KL/KCM/IDC "
                        "source, reconciles each to its exact Artifact "
                        "requirement, interprets device-selector and input "
                        "configuration semantics, preserves unknown syntax, "
                        "and exposes explicit keyboard-layout candidate "
                        "relationships for downstream reconstruction."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="font",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.font,
                    universe_values=(
                        font_requirement,
                    ),
                    reason=(
                        "Universe conserves every canonical installed font, "
                        "reconciles it to its exact Artifact requirement, and "
                        "preserves intrinsic SFNT/TTC face, table, and name "
                        "semantics for downstream ownership and "
                        "reconstruction without inventing unparsed Android "
                        "font-family or fallback relationships."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="java_archive",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.java_archive,
                    universe_values=(
                        (
                            classpath_requirement
                            .java_archive_reconciliation,
                        )
                        if classpath_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe reconciles every canonical parsed Java "
                        "archive with its exact installed Artifact requirement "
                        "and existing effective-Classpath resolution without "
                        "inferring classpath membership."
                    ),
                ),
                                AndroidUniverseParsingPopulationDisposition(
                    population_name="shell_script",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.shell_script,
                    universe_values=(
                        shell_script_reconciliation,
                    ),
                    reason=(
                        "Universe reconciles every intrinsic shell-script "
                        "Parsing source to its exact filesystem Artifact, "
                        "resolves statically provable CLASSPATH paths against "
                        "canonical installed Java archives, and identifies "
                        "literal app_process exec wrappers without executing "
                        "shell or inferring dynamic values."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="certificate",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.certificate,
                    universe_values=(
                        certificate_requirement,
                    ),
                    reason=(
                        "Universe conserves every canonical direct "
                        "certificate and OTA certificate archive source, "
                        "reconciles installed sources to exact filesystem "
                        "payload Artifacts, assigns evidence-backed Android "
                        "certificate use roles, groups exact DER identities, "
                        "and exposes structural issuer candidates without "
                        "claiming cryptographic signature validation or "
                        "update authorization."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="structured_configuration",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.structured_configuration,
                    universe_values=(
                        structured_configuration_requirement,
                    ),
                    reason=(
                        "Universe decomposes the canonical structured "
                        "configuration population into independently typed "
                        "AVB public-key, process-resource-control, filesystem "
                        "construction, recovery wipe-policy, Blueprint "
                        "build-definition, sensor-HAL composition, and sensor "
                        "registry requirements. Exact Parsing source and "
                        "Artifact identities are retained; unproven AVB trust "
                        "usage, runtime cgroup behavior, build consumption, "
                        "and sensor provider/transport relationships are not "
                        "invented."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="apk",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.apk,
                    universe_values=(
                        (apk_requirement,)
                        if apk_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets canonical APK package Parsing "
                        "evidence and reconciles it with installed artifacts."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="avf_vm_config",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.avf_vm_config,
                    universe_values=(
                        avf_requirement,
                    ),
                    reason=(
                        "Universe conserves every canonical AVF candidate "
                        "disposition and parsed VM configuration, reconciles "
                        "each parsed configuration to its exact containing APK "
                        "Artifact, preserves declared guest-runtime and task "
                        "semantics, resolves explicit APEX names and extra-APK "
                        "paths only to canonical candidate requirements, and "
                        "reconciles same-container configurations into exact "
                        "core-runtime variant families. No kernel, ramdisk, "
                        "runtime implementation, provider, or activation "
                        "relationship is inferred from names alone."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="kernel_modules",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.kernel_modules,
                    universe_values=(
                        (kernel_module_requirement,)
                        if kernel_module_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets kernel-module identities, "
                        "modinfo, dependencies, aliases, and deployment "
                        "relationships."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="kernel_module_configurations",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.kernel_module_configurations,
                    universe_values=(
                        (kernel_module_requirement,)
                        if kernel_module_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets canonical modules.* "
                        "configuration evidence with the kernel-module "
                        "population."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="linker_configurations",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.linker_configurations,
                    universe_values=(
                        (linker_requirement,)
                        if linker_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets lexical linker configuration "
                        "as canonical runtime-policy semantic input."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="linker_protobuf_configurations",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.linker_protobuf_configurations,
                    universe_values=(
                        (linker_requirement,)
                        if linker_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets linkerconfig protobuf evidence "
                        "into canonical linker-policy semantic input."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="native_library_configurations",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.native_library_configurations,
                    universe_values=(
                        (linker_requirement,)
                        if linker_requirement is not None
                        else ()
                    ),
                    reason=(
                        "Universe interprets native-library configuration "
                        "declarations into canonical runtime policy."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="apex",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.apex,
                    universe_values=apex_requirements,
                    reason=(
                        "Universe interprets every parsed APEX container and "
                        "its deployment/runtime semantic requirements."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="bmp",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.bmp,
                    universe_values=bmp_requirements,
                    reason=(
                        "Universe promotes parsed BMP observations into "
                        "canonical BMP requirements."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="sflb",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.sflb,
                    universe_values=sflb_requirements,
                    reason=(
                        "Universe promotes parsed SFLB observations into "
                        "canonical SFLB requirements."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="dtbo",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.dtbo,
                    universe_values=(
                        *dtbo_requirements,
                        dtbo_population,
                    ),
                    reason=(
                        "Universe interprets the complete DTBO population "
                        "and reconciles overlay structure and population "
                        "semantics."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="boot_dtbs",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.boot_dtbs,
                    universe_values=(
                        boot_population,
                    ),
                    reason=(
                        "Universe reconciles every canonical boot-family DTB "
                        "to its exact Boot requirement and exact dtb component "
                        "without rediscovering container lineage."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="vendor_ramdisk_tables",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.vendor_ramdisk_tables,
                    universe_values=(
                        boot_population,
                    ),
                    reason=(
                        "Universe reconciles every canonical vendor ramdisk "
                        "table to its exact Boot requirement while preserving "
                        "table, entry, component, and boot-image identity."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="vbmeta",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.vbmeta,
                    universe_values=(
                        *vbmeta_requirements,
                        avb_topology,
                    ),
                    reason=(
                        "Universe interprets complete VBMeta evidence and "
                        "reconciles canonical AVB trust topology."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="avb_regions",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.avb_regions,
                    universe_values=(
                        *avb_regions,
                        avb_topology,
                    ),
                    reason=(
                        "Universe conserves every Parsing AVB region and "
                        "reconciles it with VBMeta topology."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="bootloader",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.bootloader,
                    universe_values=bootloader_requirements,
                    reason=(
                        "Universe interprets every structured parsed "
                        "bootloader-child payload while preserving exact "
                        "artifact identity."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="bootloader_children",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.bootloader_children,
                    universe_values=(
                        bootloader_population,
                    ),
                    reason=(
                        "Universe accounts for every canonical bootloader-child "
                        "disposition: parsed children retain their exact "
                        "Bootloader requirement and opaque children remain "
                        "explicitly preserved without invented semantics."
                    ),
                ),
                                AndroidUniverseParsingPopulationDisposition(
                    population_name="ramdisks",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.ramdisks,
                    universe_values=(
                        boot_population,
                    ),
                    reason=(
                        "Universe reconciles every canonical ramdisk lineage "
                        "to its exact Boot requirement while preserving the "
                        "complete Parsing CPIO projection and component "
                        "identity."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="kernels",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.kernels,
                    universe_values=kernel_requirements,
                    reason=(
                        "Universe interprets complete kernel and embedded "
                        "kernel-config Parsing evidence."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="boot_images",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.boot_images,
                    universe_values=boot_requirements,
                    reason=(
                        "Universe interprets every canonical boot-family "
                        "Parsing result including bootconfig semantics."
                    ),
                ),
                AndroidUniverseParsingPopulationDisposition(
                    population_name="boot_signatures",
                    disposition=(
                        AndroidUniverseParsingPopulationDispositionKind
                        .SEMANTICALLY_CONSUMED
                    ),
                    parsing_value=parsing.boot_signatures,
                    universe_values=(
                        boot_population,
                    ),
                    reason=(
                        "Universe preserves exact boot-signature containment "
                        "through Boot and derives source-local AVB descriptor "
                        "semantics without inventing a partition-backed "
                        "VBMeta identity."
                    ),
                ),
            ),
        )

        context.android_device_universe = (
            AndroidDeviceUniverse(
                parsing=context.android_parsing,
                parsing_boundary=parsing_boundary,
                knowledge_resolution=(
                    context.knowledge_resolution
                ),
                artifact_requirements=artifact_requirements,
                filesystem_entry_requirements=(
                    filesystem_entry_requirements
                ),
                model_source_requirements=(
                    model_source_requirements
                ),
                property_source_records=(
                    property_source_records
                ),
                property_evidence=property_evidence,
                architecture=architecture,
                runtime_property_requirements=(
                    runtime_property_requirements
                ),
                runtime_property_relevance=(
                    runtime_property_relevance
                ),
                conclusions=conclusions,
                fstab_requirements=fstab_requirements,
                fstab_source_contexts=(
                    fstab_source_contexts
                ),
                ueventd_requirements=(
                    ueventd_requirements
                ),
                ueventd_source_contexts=(
                    ueventd_source_contexts
                ),
                ueventd_reconciliation=(
                    ueventd_reconciliation
                ),
                vintf_requirements=(
                    vintf_requirements
                ),
                vintf_applicability=(
                    vintf_applicability
                ),
                device_capabilities=(
                    AndroidUniverseDeviceCapabilityReconciler()
                    .reconcile(
                        requirements=vintf_requirements,
                        applicability=vintf_applicability,
                    )
                ),
                selinux_requirements=(
                    selinux_requirements
                ),
                selinux_policy_graph=(
                    selinux_policy_graph
                ),
                selinux_conclusions=(
                    selinux_conclusions
                ),
                selinux_applicability=(
                    selinux_applicability
                ),
                cross_family_relationships=(
                    cross_family_relationships
                ),
                cross_family_relationship_applicability=(
                    cross_family_relationship_applicability
                ),
                linker_apex_context_applicability=(
                    linker_apex_context_applicability
                ),
                linker_apex_namespace_inputs=(
                    linker_apex_namespace_inputs
                ),
                linker_apex_public_library_conclusions=(
                    linker_apex_public_library_conclusions
                ),
                linker_apex_native_library_conclusions=(
                    linker_apex_native_library_conclusions
                ),
                linker_elf_contexts=(
                    linker_elf_contexts
                ),
                init_service_substantiations=(
                    init_service_substantiations
                ),
                init_service_target_substantiations=(
                    init_service_target_substantiations
                ),
                boot_requirements=(
                    boot_requirements
                ),
                boot_population=(
                    boot_population
                ),
                boot_signature_avb_requirements=(
                    boot_signature_avb_requirements
                ),
                apex_requirements=(
                    apex_requirements
                ),
                elf_requirements=(
                    elf_requirements
                ),
                elf_artifact_associations=(
                    elf_artifact_associations
                ),
                kernel_module_elf_associations=(
                    kernel_module_elf_associations
                ),
                kernel_requirements=(
                    kernel_requirements
                ),
                aconfig_requirement=aconfig_requirement,
                input_requirement=input_requirement,
                font_requirement=font_requirement,
                certificate_requirement=(
                    certificate_requirement
                ),
                structured_configuration_requirement=(
                    structured_configuration_requirement
                ),
                dex_requirement=dex_requirement,
                avf_requirement=avf_requirement,
                apk_requirement=apk_requirement,
                classpath_requirement=classpath_requirement,
                shell_script_reconciliation=(
                    shell_script_reconciliation
                ),
                art_runtime_requirement=art_runtime_requirement,
                kernel_module_requirement=(
                    kernel_module_requirement
                ),
                linker_requirement=linker_requirement,
                dtbo_requirements=(
                    dtbo_requirements
                ),
                dtbo_population=(
                    dtbo_population
                ),
                vbmeta_requirements=(
                    vbmeta_requirements
                ),
                avb_regions=(
                    avb_regions
                ),
                avb_topology=(
                    avb_topology
                ),
                bootloader_requirements=(
                    bootloader_requirements
                ),
                bootloader_population=(
                    bootloader_population
                ),
                sflb_requirements=(
                    sflb_requirements
                ),
                bmp_requirements=(
                    bmp_requirements
                ),
                init_import_requirements=(
                    init_import_requirements
                ),
                init_import_resolutions=(
                    init_import_resolutions
                ),
                init_service_requirements=(
                    init_service_requirements
                ),
                init_service_resolutions=(
                    init_service_resolutions
                ),
                init_action_requirements=(
                    init_action_requirements
                ),
                init_source_records=(
                    init_source_records
                ),
                init_source_applicability=(
                    init_source_applicability
                ),
                fstab_applicability=fstab_applicability,
                fstab_applicability_conclusions=(
                    fstab_applicability_conclusions
                ),
            )
        )

        self._report_progress(
            current=37,
            total=37,
            operation="canonical Universe assembly",
            state=ProgressState.COMPLETE,
        )

    def _report_progress(
        self,
        *,
        current: int,
        total: int,
        operation: str,
        state: ProgressState,
    ) -> None:
        """
        Publish one semantic Android Device Universe progress observation.

        Universe owns the interpretation/reconciliation meaning. The shared
        CLI renderer owns terminal-width fitting and presentation.
        """

        if self.progress_callback is None:
            return

        semantics = {
            "Aconfig": (
                "Canonical Aconfig Parsing result",
                "promoting Aconfig observations",
                "parsed Aconfig flags / tracepoints -> canonical Universe intake",
            ),
            "APK": (
                "Canonical APK package Parsing result",
                "promoting installed package identity",
                (
                    "APK manifests + exact filesystem artifacts "
                    "-> canonical packages / RRO target relationships"
                ),
            ),
            "Classpath": (
                "Canonical Classpath Parsing result",
                "promoting classpath observations",
                "parsed classpath configurations -> canonical Universe intake",
            ),
            "ART Runtime": (
                "Canonical ART Runtime Parsing result",
                "promoting ART runtime observations",
                "parsed OAT / VDEX / ART images -> canonical Universe intake",
            ),
            "Kernel Modules": (
                "Canonical kernel-module Parsing result",
                "promoting kernel-module observations",
                "kernel modules / modules.* -> canonical Universe intake",
            ),
            "Linker": (
                "Canonical linker-policy Parsing inputs",
                "promoting linker-policy observations",
                "linker configs / protobuf / native-library lists -> canonical Universe intake",
            ),
            "ELF": (
                "Parsed ELF objects",
                "interpreting ELF requirements",
                "ELF metadata / dependencies / interpreters -> canonical requirements",
            ),
            "kernel": (
                "Parsed kernel image",
                "interpreting kernel requirements",
                "kernel release / IKCONFIG -> canonical kernel requirements",
            ),
            "DTBO": (
                "Parsed DTBO entries",
                "interpreting DTBO requirements",
                "parsed FDT entries -> canonical DTBO requirements",
            ),
            "DTBO population reconciliation": (
                "Canonical DTBO requirements",
                "reconciling DTBO population",
                (
                    "overlay entries / models / compatibles / targets "
                    "-> shared and variant DTBO evidence"
                ),
            ),
            "VBMeta / AVB": (
                "Canonical Parsing VBMeta sources and AVB regions",
                "interpreting and conserving AVB evidence",
                (
                    "VBMeta sources / AVB-region dispositions "
                    "-> canonical AVB requirements and conserved regions"
                ),
            ),
            "AVB topology reconciliation": (
                "Canonical VBMeta requirements",
                "reconciling AVB topology",
                (
                    "chain-partition / hash / hashtree descriptors "
                    "-> canonical AVB trust and authentication topology"
                ),
            ),
            "Bootloader": (
                "Parsed bootloader child structures",
                "interpreting bootloader requirements",
                "FBPK children / firmware / FBPT / UFS / UFPK -> canonical requirements",
            ),
            "SFLB": (
                "Parsed SFLB entry structures",
                "interpreting SFLB requirements",
                "entry structure / offsets / flags / payload evidence -> canonical requirements",
            ),
            "BMP": (
                "Parsed BMP resource metadata",
                "interpreting BMP requirements",
                "BMP file / DIB structure -> canonical resource evidence",
            ),
            "artifact requirements": (
                "Factory artifact requirement set",
                "classifying canonical artifact requirements",
                "filesystem inventory + parser sources -> artifact requirements",
            ),
            "properties": (
                "Parsed Android properties",
                "interpreting property evidence",
                "property declarations -> canonical device facts",
            ),
            "property reconciliation": (
                "Device property evidence",
                "reconciling cross-source property facts",
                "evidence -> agreed / conflicting / unresolved conclusions",
            ),
            "fstab": (
                "Parsed fstab declarations",
                "interpreting filesystem requirements",
                "mount topology / fs_mgr / encryption / AVB semantics",
            ),
            "ueventd": (
                "Parsed ueventd declarations",
                "interpreting device-node requirements",
                "device / sysfs / firmware / subsystem requirements",
            ),
            "boot": (
                "Parsed boot-family state",
                "interpreting boot requirements",
                "boot / init_boot / vendor_boot -> boot requirements",
            ),
            "APEX": (
                "Parsed APEX packages",
                "interpreting canonical APEX manifest metadata",
                "APEX observations -> package requirements",
            ),
            "VINTF": (
                "Installed VINTF documents",
                "interpreting VINTF requirements",
                "manifests / matrices / HALs / kernel requirements / configs",
            ),
            "SELinux": (
                "Parsed SELinux sources",
                "interpreting SELinux requirements",
                "policy sources / contexts -> policy requirements",
            ),
            "SELinux reconciliation": (
                "SELinux policy requirements",
                "reconciling SELinux policy graph",
                "cross-source policy evidence -> canonical policy graph",
            ),
            "SELinux conclusions": (
                "Canonical SELinux policy graph",
                "deriving SELinux conclusions",
                "policy graph -> device-level SELinux conclusions",
            ),
            "architecture": (
                "Architecture evidence",
                "reconciling architecture facts",
                "factory architecture evidence -> architecture conclusions",
            ),
            "init imports": (
                "Parsed init imports",
                "resolving init import requirements",
                "import declarations -> canonical import relationships",
            ),
            "init services": (
                "Parsed init services",
                "interpreting init service requirements",
                "service declarations -> canonical service requirements",
            ),
            "init actions": (
                "Parsed init actions",
                "interpreting init action requirements",
                "triggers / commands -> canonical action requirements",
            ),
            "init relationships": (
                "Init semantic requirements",
                "reconciling init relationships",
                "services / actions / properties -> init relationships",
            ),
            "init reconciliation": (
                "Init semantic requirements",
                "reconciling init requirements",
                "imports / services / runtime properties -> canonical resolutions",
            ),
            "cross-family relationships": (
                "Cross-family requirement evidence",
                "reconciling cross-family relationships",
                (
                    "init / properties / VINTF / SELinux / lifecycle "
                    "-> canonical relationships"
                ),
            ),
            "init service substantiation": (
                "Init service requirements",
                "substantiating init service dependencies",
                (
                    "services / relationships / source inventory "
                    "-> substantiation evidence"
                ),
            ),
            "init service target substantiation": (
                "Init service target relationships",
                "substantiating init service targets",
                "relationships / applicability -> target substantiation evidence",
            ),
            "fstab applicability": (
                "Installed fstab requirements",
                "evaluating fstab applicability",
                "selectors / source evidence -> applicability observations",
            ),
            "fstab applicability reconciliation": (
                "Fstab applicability evidence",
                "reconciling fstab applicability",
                "observations -> active / conditional / alternative conclusions",
            ),
            "canonical Universe assembly": (
                "Canonical Android device state",
                "assembling AndroidDeviceUniverse",
                "all reconciled requirement families -> immutable Universe",
            ),
        }

        subject, semantic_operation, item = (
            semantics.get(
                operation,
                (
                    f"{operation} evidence",
                    f"processing {operation}",
                    f"{operation} -> canonical Universe state",
                ),
            )
        )

        self.progress_callback(
            ProgressEvent(
                stage=self.name,
                state=state,
                current=current,
                total=total,
                detail=operation,
                subject=subject,
                operation=semantic_operation,
                item=item,
                processed=current,
            )
        )
