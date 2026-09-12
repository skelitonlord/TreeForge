from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from shutil import copyfile

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
    AndroidDeviceTreeInput,
    AndroidDeviceTreeMaterializedApexPayload,
    AndroidDeviceTreeMaterializedArtifact,
    AndroidDeviceTreeMaterializedDerivedSelinuxSource,
    AndroidDeviceTreeMaterializedFile,
    AndroidDeviceTreeMaterializedPhysicalPayload,
    AndroidDeviceTreeResult,
)
from treeforge.android.device_tree.artifact_projection import (
    AndroidDeviceTreeArtifactProjector,
)
from treeforge.android.device_tree.projection import (
    AndroidDeviceTreeDestinationProjector,
)
from treeforge.android.device_tree.physical_payload_projection import (
    AndroidDeviceTreePhysicalPayloadProjector,
)
from treeforge.android.device_tree.apex_payload_projection import (
    AndroidDeviceTreeApexPayloadProjector,
)
from treeforge.android.device_tree.elf_android_bp import (
    AndroidDeviceTreeElfAndroidBpRenderer,
)
from treeforge.android.device_tree.apex_android_bp import (
    AndroidDeviceTreeApexAndroidBpRenderer,
)
from treeforge.android.device_tree.apex_product_participation import (
    AndroidDeviceTreeApexProductParticipationProjector,
)
from treeforge.android.device_tree.product_makefile import (
    AndroidDeviceTreeProductMakefileRenderer,
)
from treeforge.android.device_tree.minimal_runtime import (
    normalize_aosp_init_source,
    select_minimal_runtime_copy_files,
    select_minimal_runtime_elf_packages,    select_minimal_runtime_platform_packages,
)

from treeforge.android.device_tree.apk_android_mk import (
    AndroidDeviceTreeApkAndroidMkRenderer,
)
from treeforge.android.device_tree.product_policy import (
    AndroidDeviceTreeProductPolicySelector,
)
from treeforge.android.device_tree.runtime_property_build import (
    AndroidDeviceTreeRuntimePropertyBuildProjector,
    AndroidDeviceTreeRuntimePropertyBuildRenderer,
)
from treeforge.android.device_tree.product_spine import (
    AndroidDeviceTreeProductSpineRenderer,
)
from treeforge.android.device_tree.fragment_spine import (
    AndroidDeviceTreeFragmentSpineRenderer,
)
from treeforge.android.device_tree.architecture_board_config import (
    AndroidDeviceTreeArchitectureBoardConfigRenderer,
)
from treeforge.android.device_tree.platform_board_config import (
    AndroidDeviceTreePlatformBoardConfigRenderer,
)
from treeforge.android.device_tree.platform_build_contract import (
    AndroidDeviceTreePlatformBuildContractProjector,
    AndroidDeviceTreePlatformBuildContractRenderer,
)
from treeforge.android.device_tree.kernel_board_config import (
    AndroidDeviceTreeKernelBoardConfigRenderer,
)
from treeforge.android.device_tree.vendor_kernel_ramdisk import (
    AndroidDeviceTreeMaterializedVendorKernelRamdiskModule,
    AndroidDeviceTreeVendorKernelRamdiskProjector,
)
from treeforge.android.device_tree.selinux_board_config import (
    AndroidDeviceTreeSelinuxBoardConfigRenderer,
)
from treeforge.android.device_tree.selinux_effective_policy import (
    AndroidDeviceTreeEffectiveSelinuxRenderer,
)
from treeforge.android.device_tree.selinux_realization_promotion import (
    AndroidDeviceTreeDerivedSelinuxRealizationPromoter,
)
from treeforge.android.device_tree.selinux_seapp_policy import (
    AndroidDeviceTreeSeappRenderer,
    AndroidDeviceTreeSeappRealizationPromoter,
)
from treeforge.android.device_tree.selinux_context_policy import (
    AndroidDeviceTreeContextRenderer,
    AndroidDeviceTreeContextRealizationPromoter,
)
from treeforge.android.device_tree.selinux_mac_permissions_policy import (
    AndroidDeviceTreeMacPermissionsRenderer,
    AndroidDeviceTreeMacPermissionsRealizationPromoter,
)
from treeforge.android.device_tree.selinux_runtime_disposition import (
    AndroidDeviceTreeSelinuxRuntimeDispositionFinalizer,
)
from treeforge.android.device_tree.vintf_build import (
    AndroidDeviceTreeVintfBuildRenderer,
)
from treeforge.android.device_tree.vintf_product_participation import (
    AndroidDeviceTreeVintfProductParticipationProjector,
)
from treeforge.android.device_tree.boot_dtbo_board_config import (
    AndroidDeviceTreeBootDtboBoardConfigRenderer,
)
from treeforge.android.device_tree.boot_architecture import (
    AndroidDeviceTreeBootArchitectureProjector,
    AndroidDeviceTreeBootArchitectureRenderer,
)
from treeforge.android.device_tree.ramdisk_recovery_build import (
    AndroidDeviceTreeRamdiskRecoveryBuildProjector,
    AndroidDeviceTreeRamdiskRecoveryBuildRenderer,
)

from treeforge.android.device_tree.vendor_ramdisk_packages import (
    AndroidDeviceTreeVendorRamdiskPackageProjector,
    AndroidDeviceTreeVendorRamdiskPackageRenderer,
)
from treeforge.android.version.device_tree.vendor_ramdisk_packages import (
    select_android_device_tree_vendor_ramdisk_package_providers,
)

from treeforge.android.device_tree.recovery_provider import (
    AndroidDeviceTreeRecoveryProviderProjector,
    AndroidDeviceTreeRecoveryProviderRenderer,
)
from treeforge.android.device_tree.boot_component_evidence import (
    AndroidDeviceTreeBootComponentEvidenceProjector,
)
from treeforge.android.device_tree.boot_construction import (
    AndroidDeviceTreeBootConstructionProjector,
    AndroidDeviceTreeBootConstructionSource,
)
from treeforge.android.device_tree.native_boot_build import (
    AndroidDeviceTreeNativeBootBuildProjector,
    AndroidDeviceTreeNativeBootBuildRenderer,
)
from treeforge.android.device_tree.avb_build_config import (
    AndroidDeviceTreeAvbBuildProjector,
    AndroidDeviceTreeAvbBuildRenderer,
)

from treeforge.android.version.device_tree.avb_signing import (
    select_android_device_tree_avb_signing_profile,
)
from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeApexBuildRealizationProjector,
    AndroidDeviceTreeBoardBuildRealizationProjector,
    AndroidDeviceTreeElfBuildRealizationProjector,
    AndroidDeviceTreeJavaBuildRealizationProjector,
    AndroidDeviceTreeKernelModuleBuildRealizationProjector,
    AndroidDeviceTreePackageBuildRealizationProjector,
    AndroidDeviceTreePolicyBuildRealizationProjector,
    AndroidDeviceTreePreservedBuildRealizationProjector,
    AndroidDeviceTreeSourceBuildRealizationProjector,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)

from treeforge.android.device_tree.dynamic_partitions import (
    AndroidDeviceTreeDynamicPartitionRenderer,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeStage:
    """
    Canonical Reconstruction -> physical Device Tree boundary.

    Device Tree owns:
    - generated source-tree destinations;
    - deterministic collision handling;
    - Android build-file realization;
    - directory/file materialization.

    Canonical Device Tree generation consumes TreeForge's frozen
    Reconstruction handoff and does not inspect an Android source checkout.

    An Android/AOSP workspace may be used later as a deployment and build
    destination. It is not canonical input to Device Tree generation.

    Optional Android-version/provider facts, when proven necessary, belong in
    explicitly gated TreeForge Knowledge rather than live checkout scanning.

    It does not redo upstream semantic resolution.
    """

    progress_callback: ProgressCallback | None = None

    def _report_progress(
        self,
        *,
        state: ProgressState,
        current: int,
        total: int,
        subject: str,
        operation: str,
        item: str,
    ) -> None:
        if self.progress_callback is None:
            return

        self.progress_callback(
            ProgressEvent(
                stage="Device Tree",
                state=state,
                current=current,
                total=total,
                detail=operation,
                subject=subject,
                operation=operation,
                item=item,
                processed=current,
            )
        )

    def prepare(
        self,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
        boot_construction_plan,
    ) -> AndroidDeviceTreeInput:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        source_contents = (
            reconstruction.init_source_contents
            + reconstruction.fstab_source_contents
            + reconstruction.runtime_property_source_contents
            + reconstruction.ueventd_source_contents
            + reconstruction.vintf_source_contents
            + reconstruction.selinux_source_contents
        )

        content_ids = tuple(
            content.content_id
            for content in source_contents
        )

        if len(content_ids) != len(
            set(content_ids)
        ):
            raise ValueError(
                "Reconstruction source-content identities "
                "must be globally unique before Device Tree"
            )

        return AndroidDeviceTreeInput(
            reconstruction=reconstruction,
            identity=identity,
            boot_construction_plan=(
                boot_construction_plan
            ),
        )

    def build(
        self,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
        output_root: Path,
        boot_construction_source: (
            AndroidDeviceTreeBootConstructionSource
        ) = (
            AndroidDeviceTreeBootConstructionSource
            .FACTORY_CANONICAL
        ),
        boot_image_deployment=None,
        boot_image_invoked: bool = False,
        avb_signing_provider: str = "treeforge",
    ) -> AndroidDeviceTreeResult:
        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a Path"
            )

        self._report_progress(
            state=ProgressState.STARTING,
            current=0,
            total=1,
            subject="Device Tree reconstruction",
            operation="preparing Device Tree projections",
            item="canonical Reconstruction input",
        )

        boot_construction_plan = (
            AndroidDeviceTreeBootConstructionProjector
            .project(
                reconstruction,
                identity=identity,
                source=(
                    boot_construction_source
                ),
                boot_image_deployment=(
                    boot_image_deployment
                ),
                boot_image_invoked=(
                    boot_image_invoked
                ),
            )
        )

        device_tree_input = self.prepare(
            reconstruction,
            identity=identity,
            boot_construction_plan=(
                boot_construction_plan
            ),
        )

        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        partition_layout = (
            reconstruction
            .reconstruction_input
            .partition_layout
        )

        dynamic_partition_config = (
            AndroidDeviceTreeDynamicPartitionRenderer
            .project(
                layout=partition_layout,
            )
            if partition_layout is not None
            else None
        )

        dynamic_partition_board_config_content = (
            AndroidDeviceTreeDynamicPartitionRenderer
            .render_board_config(
                dynamic_partition_config
            )
        )

        product_policy = (
            AndroidDeviceTreeProductPolicySelector
            .select(
                universe=universe,
            )
        )

        avb_signing_profile = (
            select_android_device_tree_avb_signing_profile(
                product_policy.android_version,
                avb_signing_provider,
                device_root=identity.device_root,
                device_name=identity.device,
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=1,
            total=19,
            subject="Destination projection",
            operation="projecting generated source destinations",
            item="Reconstruction source contents",
        )

        projections = (
            AndroidDeviceTreeDestinationProjector
            .project(
                reconstruction,
                identity=identity,
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=2,
            total=19,
            subject="Artifact projection",
            operation="projecting preserved artifacts",
            item="preserved Reconstruction artifacts",
        )

        artifact_projections = (
            AndroidDeviceTreeArtifactProjector
            .project(
                reconstruction,
                identity=identity,
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=3,
            total=19,
            subject="Physical payload projection",
            operation="projecting physical and APEX payloads",
            item="canonical Artifact and root-runtime APEX requirements",
        )

        physical_payload_projections = (
            AndroidDeviceTreePhysicalPayloadProjector
            .project(
                reconstruction,
                identity=identity,
            )
        )

        apex_payload_projections = (
            AndroidDeviceTreeApexPayloadProjector
            .project(
                reconstruction,
                identity=identity,
            )
        )

        vendor_kernel_ramdisk_plan = (
            AndroidDeviceTreeVendorKernelRamdiskProjector
            .project(
                reconstruction,
                identity=identity,
            )
        )

        boot_component_evidence = (
            AndroidDeviceTreeBootComponentEvidenceProjector
            .project(
                reconstruction
            )
        )

        native_boot_build_plan = (
            AndroidDeviceTreeNativeBootBuildProjector
            .project(
                reconstruction,
                identity=identity,
                vendor_kernel_ramdisk_plan=(
                    vendor_kernel_ramdisk_plan
                ),
            )
        )

        avb_build_plan = (
            AndroidDeviceTreeAvbBuildProjector
            .project(
                reconstruction,
                identity=identity,
                native_boot_plan=(
                    native_boot_build_plan
                ),
                signing_profile=(
                    avb_signing_profile
                ),
            )
        )

        # Canonical Device Tree generation does not inspect the
        # deployment checkout. AOSP-provider reconciliation is permitted
        # only after generation, against the staged deployment build view;
        # it must never mutate canonical projections, realizations, payloads,
        # or output/device-tree content.

        self._report_progress(
            state=ProgressState.RUNNING,
            current=4,
            total=19,
            subject="Build realization",
            operation="realizing generated source participation",
            item="generated source representations",
        )

        source_build_realizations = (
            AndroidDeviceTreeSourceBuildRealizationProjector
            .project(
                reconstruction,
                source_projections=projections,
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=5,
            total=19,
            subject="Build realization",
            operation="realizing preserved participation",
            item="preserved representations",
        )

        preserved_build_realizations = (
            AndroidDeviceTreePreservedBuildRealizationProjector
            .project(
                reconstruction,
                artifact_projections=artifact_projections,
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=6,
            total=19,
            subject="Build realization",
            operation="realizing package participation",
            item="APK/RRO representations",
        )

        package_build_realizations = (
            AndroidDeviceTreePackageBuildRealizationProjector
            .project(
                reconstruction,
                existing_realizations=(
                    *source_build_realizations,
                    *preserved_build_realizations,
                ),
                physical_payload_projections=(
                    physical_payload_projections
                ),
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=7,
            total=19,
            subject="Build realization",
            operation="realizing ELF participation",
            item="native-library and executable representations",
        )

        elf_build_realizations = (
            AndroidDeviceTreeElfBuildRealizationProjector
            .project(
                reconstruction,
                existing_realizations=(
                    *source_build_realizations,
                    *preserved_build_realizations,
                    *package_build_realizations,
                ),
                physical_payload_projections=(
                    physical_payload_projections
                ),
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=8,
            total=19,
            subject="Build realization",
            operation="realizing Java participation",
            item="Java library representations",
        )

        java_build_realizations = (
            AndroidDeviceTreeJavaBuildRealizationProjector
            .project(
                reconstruction,
                existing_realizations=(
                    *source_build_realizations,
                    *preserved_build_realizations,
                    *package_build_realizations,
                    *elf_build_realizations,
                ),
                physical_payload_projections=(
                    physical_payload_projections
                ),
            )
        )

        java_representation_ids = {
            realization.representation_id
            for realization
            in java_build_realizations
        }

        retained_preserved_build_realizations = tuple(
            realization
            for realization
            in preserved_build_realizations
            if (
                realization.representation_id
                not in java_representation_ids
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=9,
            total=19,
            subject="Build realization",
            operation="realizing APEX participation",
            item="APEX representations",
        )

        apex_build_realizations = (
            AndroidDeviceTreeApexBuildRealizationProjector
            .project(
                reconstruction,
                existing_realizations=(
                    *source_build_realizations,
                    *retained_preserved_build_realizations,
                    *package_build_realizations,
                    *elf_build_realizations,
                    *java_build_realizations,
                ),
                apex_payload_projections=(
                    apex_payload_projections
                ),
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=10,
            total=19,
            subject="Build realization",
            operation="realizing kernel-module participation",
            item="kernel module representations",
        )

        kernel_build_realizations = (
            AndroidDeviceTreeKernelModuleBuildRealizationProjector
            .project(
                reconstruction,
                existing_realizations=(
                    *source_build_realizations,
                    *retained_preserved_build_realizations,
                    *package_build_realizations,
                    *elf_build_realizations,
                    *java_build_realizations,
                    *apex_build_realizations,
                ),
                physical_payload_projections=(
                    physical_payload_projections
                ),
                vendor_kernel_ramdisk_projections=(
                    vendor_kernel_ramdisk_plan
                    .module_projections
                ),
            )
        )

        kernel_representation_ids = {
            realization.representation_id
            for realization
            in kernel_build_realizations
        }

        retained_preserved_build_realizations = tuple(
            realization
            for realization
            in retained_preserved_build_realizations
            if (
                realization.representation_id
                not in kernel_representation_ids
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=11,
            total=19,
            subject="Build realization",
            operation="realizing Android policy participation",
            item="VINTF and SELinux representations",
        )

        policy_build_realizations = (
            AndroidDeviceTreePolicyBuildRealizationProjector
            .project(
                reconstruction,
                existing_realizations=(
                    *source_build_realizations,
                    *retained_preserved_build_realizations,
                    *package_build_realizations,
                    *elf_build_realizations,
                    *java_build_realizations,
                    *apex_build_realizations,
                    *kernel_build_realizations,
                ),
            )
        )

        policy_representation_ids = {
            realization.representation_id
            for realization
            in policy_build_realizations
        }

        retained_source_build_realizations = tuple(
            realization
            for realization
            in source_build_realizations
            if (
                realization.representation_id
                not in policy_representation_ids
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=12,
            total=19,
            subject="Build realization",
            operation="realizing board configuration",
            item="board-level representations",
        )

        board_build_realizations = (
            AndroidDeviceTreeBoardBuildRealizationProjector
            .project(
                reconstruction,
                identity=identity,
                boot_component_evidence=(
                    boot_component_evidence
                ),
                boot_construction_plan=(
                    boot_construction_plan
                ),
                native_boot_build_plan=(
                    native_boot_build_plan
                ),
                avb_build_plan=(
                    avb_build_plan
                ),
                existing_realizations=(
                    *retained_source_build_realizations,
                    *policy_build_realizations,
                    *retained_preserved_build_realizations,
                    *package_build_realizations,
                    *elf_build_realizations,
                    *java_build_realizations,
                    *apex_build_realizations,
                    *kernel_build_realizations,
                ),
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=13,
            total=19,
            subject="Build realization",
            operation="merging and validating realization coverage",
            item="complete Reconstruction representation graph",
        )

        build_realizations = tuple(
            sorted(
                (
                    *retained_source_build_realizations,
                    *policy_build_realizations,
                    *retained_preserved_build_realizations,
                    *package_build_realizations,
                    *elf_build_realizations,
                    *java_build_realizations,
                    *apex_build_realizations,
                    *kernel_build_realizations,
                    *board_build_realizations,
                ),
                key=lambda realization: (
                    realization.realization_id
                ),
            )
        )

        realization_ids = tuple(
            realization.realization_id
            for realization
            in build_realizations
        )

        if len(
            realization_ids
        ) != len(
            set(realization_ids)
        ):
            raise ValueError(
                "Device Tree family realization merge created "
                "duplicate realization identities"
            )

        realized_representation_ids = tuple(
            realization.representation_id
            for realization
            in build_realizations
        )

        if len(
            realized_representation_ids
        ) != len(
            set(realized_representation_ids)
        ):
            raise ValueError(
                "Device Tree family realization merge created "
                "duplicate Reconstruction representation coverage"
            )

        expected_incremental_representation_ids = {
            representation.representation_id
            for representation
            in reconstruction.artifact_build_representations
        }

        if (
            set(realized_representation_ids)
            != expected_incremental_representation_ids
        ):
            missing = sorted(
                expected_incremental_representation_ids
                - set(realized_representation_ids)
            )

            unexpected = sorted(
                set(realized_representation_ids)
                - expected_incremental_representation_ids
            )

            raise ValueError(
                "Device Tree incremental realization coverage mismatch: "
                f"missing={len(missing)}, "
                f"unexpected={len(unexpected)}"
            )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=14,
            total=19,
            subject="Build rendering",
            operation="projecting ELF and APEX Android.bp modules",
            item="resolved module-backed ELF and APEX realizations",
        )

        # Canonical Device Tree generation does not infer ELF provider
        # ownership from the deployment checkout. Reconstruction remains
        # authoritative for exact factory ELF identity. Exact AOSP provider
        # reconciliation is permitted only later against the staged deployment
        # build view and must not mutate output/device-tree.
        elf_render_realizations = build_realizations

        elf_android_bp_modules = (
            AndroidDeviceTreeElfAndroidBpRenderer.project(
                realizations=elf_render_realizations,
                elf_build_semantics=(
                    reconstruction.elf_build_semantics
                ),
                physical_payload_projections=(
                    physical_payload_projections
                ),
                proprietary_root=PurePosixPath(
                    identity.proprietary_root.as_posix()
                ),
            )
        )

        minimal_runtime_elf_product_packages = (
            select_minimal_runtime_elf_packages(
                universe=universe,
                modules=elf_android_bp_modules,
            )
        )

        minimal_runtime_platform_product_packages = (
            select_minimal_runtime_platform_packages(
                universe=universe,
                android_version=(
                    product_policy.android_version
                ),
            )
        )

        elf_android_bp_content = (
            AndroidDeviceTreeElfAndroidBpRenderer.render(
                elf_android_bp_modules
            )
        )

        apex_render_realizations = build_realizations

        apex_android_bp_modules = (
            AndroidDeviceTreeApexAndroidBpRenderer.project(
                realizations=apex_render_realizations,
                apex_payload_projections=(
                    apex_payload_projections
                ),
                proprietary_root=PurePosixPath(
                    identity.proprietary_root.as_posix()
                ),
            )
        )

        apex_android_bp_content = (
            AndroidDeviceTreeApexAndroidBpRenderer.render(
                apex_android_bp_modules
            )
        )

        proprietary_android_bp_content = (
            elf_android_bp_content.rstrip()
            + "\n\n"
            + apex_android_bp_content.lstrip()
        )

        #
        # Canonical APEX payload/module realization remains complete.
        # Minimum-AOSP product participation is a separate Device Tree
        # decision and must not automatically install framework-side factory
        # APEXes. Exact platform-provider overlap remains a later staged-
        # deployment concern.
        #
        apex_product_participation = (
            AndroidDeviceTreeApexProductParticipationProjector.project(
                modules=apex_android_bp_modules,
            )
        )

        apex_product_packages = (
            apex_product_participation.product_packages
        )

        apk_android_mk_modules = (
            AndroidDeviceTreeApkAndroidMkRenderer.project(
                identity=identity,
                realizations=build_realizations,
                physical_payload_projections=(
                    physical_payload_projections
                ),
            )
        )

        apk_android_mk_content = (
            AndroidDeviceTreeApkAndroidMkRenderer.render(
                apk_android_mk_modules
            )
        )

        #
        # Minimum-AOSP bring-up deliberately does not install factory APKs.
        # Their exact payloads/modules remain preserved in the generated
        # Device Tree so a later product policy can opt them back in.
        #
        apk_product_packages = ()

        self._report_progress(
            state=ProgressState.RUNNING,
            current=15,
            total=19,
            subject="Build rendering",
            operation="projecting product makefile integration",
            item="resolved COPY_FILE and APEX module participation",
        )

        product_copy_files = (
            AndroidDeviceTreeProductMakefileRenderer.project(
                identity=identity,
                realizations=build_realizations,
                artifact_projections=(
                    artifact_projections
                ),
                physical_payload_projections=(
                    physical_payload_projections
                ),
            )
        )

        product_copy_files = (
            select_minimal_runtime_copy_files(
                copy_files=product_copy_files,
                projections=projections,
                universe=universe,
                modules=elf_android_bp_modules,
                identity=identity,
                output_root=output_root,
            )
        )

        vintf_build_config = (
            AndroidDeviceTreeVintfBuildRenderer.project(
                reconstruction=reconstruction,
                identity=identity,
                realizations=build_realizations,
            )
        )

        # Canonical VINTF realization is retained in full and remains
        # checkout-independent. Product participation is a separate Device
        # Tree policy decision and never mutates the canonical VINTF source
        # or module population. Exact AOSP provider reconciliation remains a
        # later staged-deployment concern.

        vintf_product_participation = (
            AndroidDeviceTreeVintfProductParticipationProjector.project(
                reconstruction=reconstruction,
                config=vintf_build_config,
                apk_modules=apk_android_mk_modules,
                apk_product_packages=apk_product_packages,
            )
        )

        vintf_product_packages = (
            vintf_product_participation.product_packages
        )

        runtime_property_build_plan = (
            AndroidDeviceTreeRuntimePropertyBuildProjector
            .project(
                reconstruction=reconstruction,
            )
        )

        runtime_property_board_config_content = (
            AndroidDeviceTreeRuntimePropertyBuildRenderer
            .render_board_config(
                runtime_property_build_plan
            )
        )

        runtime_property_product_content = (
            AndroidDeviceTreeRuntimePropertyBuildRenderer
            .render_product_config(
                runtime_property_build_plan
            )
        )

        product_makefile_content = (
            AndroidDeviceTreeProductMakefileRenderer.render(
                product_copy_files,
                product_packages=tuple(
                    sorted(
                        set(
                            apex_product_packages
                            + minimal_runtime_elf_product_packages
                            + minimal_runtime_platform_product_packages
                            + vintf_product_packages
                        )
                    )
                ),
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=16,
            total=19,
            subject="Build rendering",
            operation=(
                "projecting architecture, platform, and "
                "kernel BoardConfig integration"
            ),
            item=(
                "canonical architecture/platform facts and "
                "resolved direct kernel module/config realizations"
            ),
        )

        architecture_board_config = (
            AndroidDeviceTreeArchitectureBoardConfigRenderer.project(
                universe=universe,
            )
        )

        architecture_board_config_content = (
            AndroidDeviceTreeArchitectureBoardConfigRenderer.render(
                architecture_board_config
            )
        )

        platform_board_config = (
            AndroidDeviceTreePlatformBoardConfigRenderer.project(
                universe=universe,
            )
        )

        platform_board_config_content = (
            AndroidDeviceTreePlatformBoardConfigRenderer.render(
                platform_board_config
            )
        )

        if partition_layout is None:
            raise ValueError(
                "platform build contract requires "
                "canonical PartitionLayout"
            )

        platform_build_contract = (
            AndroidDeviceTreePlatformBuildContractProjector
            .project(
                android_version=(
                    product_policy.android_version
                ),
                board_platform=(
                    platform_board_config
                    .board_platform
                ),
                bootloader_board_name=(
                    identity.device
                ),
                device_root=(
                    identity.device_root
                ),
                virtual_ab_enabled=(
                    product_policy.virtual_ab_enabled
                ),
                layout=partition_layout,
                dynamic_partition_config=(
                    dynamic_partition_config
                ),
            )
        )

        platform_build_contract_board_content = (
            AndroidDeviceTreePlatformBuildContractRenderer
            .render_board_config(
                platform_build_contract
            )
        )

        platform_build_contract_product_content = (
            AndroidDeviceTreePlatformBuildContractRenderer
            .render_product_config(
                platform_build_contract
            )
        )

        platform_board_config_content = (
            "\n\n".join(
                item.rstrip()
                for item
                in (
                    platform_board_config_content,
                    platform_build_contract_board_content,
                )
                if item.strip()
            )
            + "\n"
        )

        kernel_board_config = (
            AndroidDeviceTreeKernelBoardConfigRenderer.project(
                identity=identity,
                realizations=build_realizations,
                physical_payload_projections=(
                    physical_payload_projections
                ),
                vendor_kernel_ramdisk_plan=(
                    vendor_kernel_ramdisk_plan
                ),
            )
        )

        kernel_board_config_content = (
            AndroidDeviceTreeKernelBoardConfigRenderer.render(
                kernel_board_config
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=17,
            total=19,
            subject="Build rendering",
            operation="synthesizing SELinux source policy",
            item=(
                "canonical factory-derived SELinux semantics, exact text, "
                "and effective partition recovery candidates"
            ),
        )

        partition_selinux_syntheses = tuple(
            (
                partition,
                AndroidDeviceTreeEffectiveSelinuxRenderer.project(
                    reconstruction,
                    identity=identity,
                    partition=partition,
                ),
            )
            for partition in (
                "vendor",
                "system_ext",
                "product",
            )
        )

        for (
            partition,
            synthesis,
        ) in partition_selinux_syntheses:
            if not synthesis.sources:
                raise ValueError(
                    "canonical effective SELinux policy "
                    "did not produce source-equivalent "
                    f"output: {partition}"
                )

            if not synthesis.complete:
                raise ValueError(
                    "canonical effective SELinux policy "
                    "contains unsupported source recovery "
                    f"semantics: {partition}; "
                    "unsupported forms="
                    f"{synthesis.unsupported_form_names}"
                )

        seapp_synthesis = (
            AndroidDeviceTreeSeappRenderer.project(
                reconstruction,
                identity=identity,
            )
        )

        context_synthesis = (
            AndroidDeviceTreeContextRenderer.project(
                reconstruction,
                identity=identity,
                realizations=build_realizations,
            )
        )

        mac_permissions_synthesis = (
            AndroidDeviceTreeMacPermissionsRenderer.project(
                reconstruction,
                identity=identity,
            )
        )

        effective_selinux_sources = tuple(
            source
            for _, synthesis
            in partition_selinux_syntheses
            for source in synthesis.sources
        )

        derived_selinux_sources = (
            effective_selinux_sources
            + seapp_synthesis.sources
            + context_synthesis.sources
            + mac_permissions_synthesis.sources
        )

        for (
            _,
            synthesis,
        ) in partition_selinux_syntheses:
            build_realizations = (
                AndroidDeviceTreeDerivedSelinuxRealizationPromoter.project(
                    reconstruction,
                    synthesis=synthesis,
                    realizations=build_realizations,
                )
            )

        build_realizations = (
            AndroidDeviceTreeSeappRealizationPromoter.project(
                reconstruction,
                synthesis=seapp_synthesis,
                realizations=build_realizations,
            )
        )

        build_realizations = (
            AndroidDeviceTreeContextRealizationPromoter.project(
                reconstruction,
                synthesis=context_synthesis,
                realizations=build_realizations,
            )
        )

        build_realizations = (
            AndroidDeviceTreeMacPermissionsRealizationPromoter.project(
                reconstruction,
                synthesis=mac_permissions_synthesis,
                realizations=build_realizations,
            )
        )

        selinux_runtime_disposition = (
            AndroidDeviceTreeSelinuxRuntimeDispositionFinalizer.project(
                reconstruction,
                realizations=build_realizations,
            )
        )

        build_realizations = (
            selinux_runtime_disposition.realizations
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=18,
            total=19,
            subject="Build rendering",
            operation="projecting SELinux and VINTF build integration",
            item="resolved Android policy realizations",
        )

        selinux_board_config = (
            AndroidDeviceTreeSelinuxBoardConfigRenderer.project(
                reconstruction=reconstruction,
                identity=identity,
                realizations=build_realizations,
                derived_sources=derived_selinux_sources,
            )
        )

        selinux_board_config_content = (
            AndroidDeviceTreeSelinuxBoardConfigRenderer.render(
                selinux_board_config
            )
        )

        vintf_board_config_content = (
            AndroidDeviceTreeVintfBuildRenderer.render_board_config(
                vintf_build_config
            )
        )

        self._report_progress(
            state=ProgressState.RUNNING,
            current=19,
            total=19,
            subject="Build rendering",
            operation="projecting boot and DTBO BoardConfig integration",
            item="canonical boot and DTBO requirements",
        )

        boot_dtbo_board_config = (
            AndroidDeviceTreeBootDtboBoardConfigRenderer.project(
                reconstruction=reconstruction,
                identity=identity,
                boot_construction_plan=(
                    boot_construction_plan
                ),
            )
        )

        boot_dtbo_base_board_config_content = (
            AndroidDeviceTreeBootDtboBoardConfigRenderer.render(
                boot_dtbo_board_config
            )
        )

        boot_architecture_profile = (
            AndroidDeviceTreeBootArchitectureProjector.project(
                reconstruction,
                android_version=(
                    product_policy.android_version
                ),
                boot_header_version=(
                    boot_dtbo_board_config
                    .boot_header_version
                ),
                init_boot_header_version=(
                    boot_dtbo_board_config
                    .init_boot_header_version
                ),
            )
        )

        boot_architecture_board_config_content = (
            AndroidDeviceTreeBootArchitectureRenderer
            .render_board_config(
                boot_architecture_profile
            )
        )

        boot_dtbo_board_config_content = (
            "\n\n".join(
                item.rstrip()
                for item
                in (
                    boot_dtbo_base_board_config_content,
                    boot_architecture_board_config_content,
                )
                if item.strip()
            )
            + "\n"
        )

        #
        # Ramdisk/recovery staging depends on the already-resolved Android
        # boot architecture. Keep this beside the boot-architecture/native
        # boot rendering boundary instead of the earlier generic product
        # realization pass.
        #
        ramdisk_recovery_build_plan = (
            AndroidDeviceTreeRamdiskRecoveryBuildProjector
            .project(
                reconstruction=reconstruction,
                identity=identity,
                source_projections=projections,
                boot_architecture_profile=(
                    boot_architecture_profile
                ),
            )
        )

        vendor_ramdisk_package_providers = (
            select_android_device_tree_vendor_ramdisk_package_providers(
                product_policy.android_version
            )
        )

        vendor_ramdisk_package_plan = (
            AndroidDeviceTreeVendorRamdiskPackageProjector
            .project(
                universe=universe,
                providers=(
                    vendor_ramdisk_package_providers
                ),
            )
        )

        vendor_ramdisk_package_product_content = (
            AndroidDeviceTreeVendorRamdiskPackageRenderer
            .render_product_config(
                vendor_ramdisk_package_plan
            )
        )

        recovery_provider_plan = (
            AndroidDeviceTreeRecoveryProviderProjector
            .project(
                reconstruction=reconstruction,
                identity=identity,
                source_projections=projections,
            )
        )

        recovery_provider_android_bp_content = (
            AndroidDeviceTreeRecoveryProviderRenderer
            .render_android_bp(
                recovery_provider_plan
            )
        )

        recovery_provider_product_content = (
            AndroidDeviceTreeRecoveryProviderRenderer
            .render_product_config(
                recovery_provider_plan
            )
        )

        recovery_provider_board_config_content = (
            AndroidDeviceTreeRecoveryProviderRenderer
            .render_board_config(
                recovery_provider_plan
            )
        )

        ramdisk_recovery_product_content = (
            AndroidDeviceTreeRamdiskRecoveryBuildRenderer
            .render_product_config(
                ramdisk_recovery_build_plan
            )
        )

        ramdisk_recovery_board_config_content = (
            AndroidDeviceTreeRamdiskRecoveryBuildRenderer
            .render_board_config(
                ramdisk_recovery_build_plan
            )
        )

        if recovery_provider_board_config_content.strip():
            ramdisk_recovery_board_config_content = (
                ramdisk_recovery_board_config_content.rstrip()
                + "\n\n"
                + recovery_provider_board_config_content.lstrip()
            )

        if ramdisk_recovery_product_content.strip():
            product_makefile_content = (
                product_makefile_content.rstrip()
                + "\n\n"
                + ramdisk_recovery_product_content.lstrip()
            )

        if vendor_ramdisk_package_product_content.strip():
            product_makefile_content = (
                product_makefile_content.rstrip()
                + "\n\n"
                + vendor_ramdisk_package_product_content.lstrip()
            )

        if recovery_provider_product_content.strip():
            product_makefile_content = (
                product_makefile_content.rstrip()
                + "\n\n"
                + recovery_provider_product_content.lstrip()
            )

        native_boot_board_config_content = (
            AndroidDeviceTreeNativeBootBuildRenderer
            .render_board_config(
                native_boot_build_plan
            )
        )

        native_boot_product_content = (
            AndroidDeviceTreeNativeBootBuildRenderer
            .render_product_config(
                native_boot_build_plan
            )
        )

        boot_architecture_product_content = (
            AndroidDeviceTreeBootArchitectureRenderer
            .render_product_config(
                boot_architecture_profile
            )
        )

        native_boot_product_content = (
            "\n\n".join(
                item.rstrip()
                for item
                in (
                    native_boot_product_content,
                    boot_architecture_product_content,
                )
                if item.strip()
            )
            + "\n"
        )

        avb_board_config_content = (
            AndroidDeviceTreeAvbBuildRenderer
            .render_board_config(
                avb_build_plan
            )
        )

        android_board_content = (
            AndroidDeviceTreeAvbBuildRenderer
            .render_android_board(
                avb_build_plan,
                native_boot_build_plan,
            )
        )

        #
        # TreeForge-owned BoardConfig capability fragments.
        #
        # These are organizational boundaries only.  Each fragment preserves
        # the exact already-derived content produced by its owning renderer.
        # No new semantics are inferred by this composition layer.
        #
        board_config_fragments = tuple(
            (
                relative_path,
                content.rstrip() + "\n",
            )
            for relative_path, content
            in (
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "architecture"
                    / "BoardConfig.mk",
                    architecture_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "platform"
                    / "BoardConfig.mk",
                    platform_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "properties"
                    / "BoardConfig.mk",
                    runtime_property_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "dynamic"
                    / "BoardConfig.mk",
                    dynamic_partition_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "kernel"
                    / "BoardConfig.mk",
                    kernel_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "sepolicy"
                    / "BoardConfig.mk",
                    selinux_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "vintf"
                    / "BoardConfig.mk",
                    vintf_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "boot"
                    / "BoardConfig.mk",
                    boot_dtbo_board_config_content,
                ),
                (
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "boot"
                    / "recovery"
                    / "BoardConfig.mk",
                    ramdisk_recovery_board_config_content,
                ),
                (
                    native_boot_build_plan
                    .board_config_path,
                    native_boot_board_config_content,
                ),
                (
                    avb_build_plan
                    .board_config_path,
                    avb_board_config_content,
                ),
            )
            if content.strip()
        )

        board_config_content = (
            AndroidDeviceTreeFragmentSpineRenderer
            .render_board_config(
                identity=identity,
                fragments=tuple(
                    path
                    for path, _
                    in board_config_fragments
                ),
            )
        )

        vintf_android_bp_content = (
            AndroidDeviceTreeVintfBuildRenderer.render_android_bp(
                vintf_build_config,
                vintf_root=(
                    PurePosixPath(
                        identity.device_root.as_posix()
                    )
                    / "vintf"
                ),
                vendor_boot_as_recovery=(
                    boot_architecture_profile
                    .move_recovery_resources_to_vendor_boot
                ),
            )
        )

        materialized = []

        materialization_total = (
            1
            + len(projections)
            + len(
                ramdisk_recovery_build_plan
                .source_variants
            )
            + len(
                recovery_provider_plan
                .providers
            )
            + len(
                recovery_provider_plan
                .config_inputs
            )
            + (
                1
                if (
                    recovery_provider_plan
                    .recovery_wipe
                    is not None
                )
                else 0
            )
            + (
                1
                if recovery_provider_android_bp_content.strip()
                else 0
            )
            + len(artifact_projections)
            + len(physical_payload_projections)
            + len(
                vendor_kernel_ramdisk_plan
                .module_projections
            )
            + len(apex_payload_projections)
            + len(derived_selinux_sources)
            + len(
                vintf_build_config.derived_sources
            )
            + len(
                boot_construction_plan.images
            )
            + (
                native_boot_build_plan
                .materialized_input_count
            )
            + len(
                avb_build_plan
                .static_source_inputs
            )
            + 1
            + 8
            + len(board_config_fragments)
            + (
                1
                if (
                    boot_dtbo_board_config
                    .dtbo_source_artifact
                    is not None
                )
                else 0
            )
        )
        materialization_current = 0

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Materialization",
            operation="materializing Device Tree files",
            item=(
                "generated sources, preserved artifacts, physical payloads, "
                "APEX payloads, BoardConfig, vendor integration, and "
                "product registration files"
            ),
        )

        #
        # Device Tree-derived VINTF source equivalents.
        #
        # Canonical Reconstruction XML remains materialized separately and
        # unchanged. These files exist only to reverse final assembled VINTF
        # output into legitimate Android source-build participation.
        #
        for derived_source in (
            vintf_build_config.derived_sources
        ):
            destination = (
                output_root
                / Path(
                    derived_source
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_text(
                derived_source.text,
                encoding="utf-8",
            )

            if (
                destination.read_text(
                    encoding="utf-8"
                )
                != derived_source.text
            ):
                raise ValueError(
                    "derived VINTF source materialization "
                    "changed rendered content: "
                    f"{derived_source.derived_source_id}"
                )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        derived_source
                        .destination
                        .as_posix()
                    ),
                    content_id=(
                        "device-tree:"
                        f"{derived_source.derived_source_id}"
                    ),
                    representation_id=(
                        derived_source.derived_source_id
                    ),
                    family="vintf_derived_source",
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="VINTF source",
                operation=(
                    "materializing derived framework "
                    "compatibility source"
                ),
                item=(
                    derived_source
                    .destination
                    .as_posix()
                ),
            )

        if (
            boot_dtbo_board_config
            .dtbo_source_artifact
            is not None
        ):
            dtbo_source = (
                boot_dtbo_board_config
                .dtbo_source_artifact
            )

            dtbo_relative_destination = (
                boot_dtbo_board_config
                .dtbo_source_path
            )

            if dtbo_relative_destination is None:
                raise ValueError(
                    "DTBO source artifact requires its "
                    "Device Tree destination"
                )

            dtbo_destination = (
                output_root
                / Path(
                    dtbo_relative_destination
                    .as_posix()
                )
            )

            dtbo_destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                dtbo_source,
                dtbo_destination,
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="DTBO image",
                operation=(
                    "materializing exact canonical "
                    "DTBO container"
                ),
                item=(
                    dtbo_relative_destination
                    .as_posix()
                ),
            )

        #
        # Exact selected boot construction inputs.
        #
        # These are build inputs only. Their presence does not imply source
        # equivalence, and no Boot Image VBMeta artifact is admitted here.
        #
        for construction_image in (
            boot_construction_plan.images
        ):
            source = (
                construction_image
                .source_path
            )

            actual_size, actual_sha256 = (
                AndroidDeviceTreeBootConstructionProjector
                .file_identity(
                    source
                )
            )

            if (
                actual_size
                != construction_image.size_bytes
                or actual_sha256
                != construction_image.sha256
            ):
                raise ValueError(
                    "boot construction input changed after "
                    "projection: "
                    f"{construction_image.partition_name}"
                )

            destination = (
                output_root
                / Path(
                    construction_image
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            copied_size, copied_sha256 = (
                AndroidDeviceTreeBootConstructionProjector
                .file_identity(
                    destination
                )
            )

            if (
                copied_size
                != construction_image.size_bytes
                or copied_sha256
                != construction_image.sha256
            ):
                raise ValueError(
                    "materialized boot construction image "
                    "lost exact byte identity: "
                    f"{construction_image.partition_name}"
                )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Boot construction image",
                operation=(
                    "materializing exact selected "
                    "whole-image construction input"
                ),
                item=(
                    construction_image
                    .destination
                    .as_posix()
                ),
            )

        materialized_native_boot_inputs = []

        for fragment in (
            native_boot_build_plan
            .vendor_ramdisk_fragments
        ):
            destination = (
                output_root
                / Path(
                    fragment
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_bytes(
                fragment.payload
            )

            if (
                destination.read_bytes()
                != fragment.payload
            ):
                raise ValueError(
                    "vendor ramdisk fragment materialization "
                    "lost exact bytes: "
                    f"{fragment.name}"
                )

            materialized_native_boot_inputs.append(
                Path(
                    fragment
                    .destination
                    .as_posix()
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Native boot input",
                operation=(
                    "materializing canonical vendor "
                    "ramdisk fragment"
                ),
                item=(
                    fragment
                    .destination
                    .as_posix()
                ),
            )

        for native_input in (
            native_boot_build_plan
            .file_inputs
        ):
            source = (
                native_input
                .source_path
            )

            if not source.is_file():
                raise ValueError(
                    "canonical native boot input is unavailable: "
                    f"{source}"
                )

            destination = (
                output_root
                / Path(
                    native_input
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            if (
                destination.read_bytes()
                != source.read_bytes()
            ):
                raise ValueError(
                    "native boot input copy lost exact bytes: "
                    f"{native_input.role}"
                )

            materialized_native_boot_inputs.append(
                Path(
                    native_input
                    .destination
                    .as_posix()
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Native boot input",
                operation=(
                    "materializing exact canonical "
                    f"{native_input.role}"
                ),
                item=(
                    native_input
                    .destination
                    .as_posix()
                ),
            )

        pvmfw_source = (
            native_boot_build_plan
            .pvmfw_source_path
        )

        pvmfw_destination = (
            output_root
            / Path(
                native_boot_build_plan
                .pvmfw_destination
                .as_posix()
            )
        )

        pvmfw_destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        copyfile(
            pvmfw_source,
            pvmfw_destination,
        )

        if (
            pvmfw_destination.read_bytes()
            != pvmfw_source.read_bytes()
        ):
            raise ValueError(
                "pvmfw exact prebuilt handoff lost byte identity"
            )

        materialized_native_boot_inputs.append(
            Path(
                native_boot_build_plan
                .pvmfw_destination
                .as_posix()
            )
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Native boot input",
            operation=(
                "materializing exact canonical pvmfw image"
            ),
            item=(
                native_boot_build_plan
                .pvmfw_destination
                .as_posix()
            ),
        )

        materialized_avb_inputs = []

        for provider in (
            avb_build_plan
            .static_source_inputs
        ):
            source = provider.source_path

            if not source.is_file():
                raise ValueError(
                    "canonical AVB descriptor source "
                    "is unavailable: "
                    f"{source}"
                )

            destination = (
                output_root
                / Path(
                    provider
                    .source_destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            if (
                destination.read_bytes()
                != source.read_bytes()
            ):
                raise ValueError(
                    "AVB descriptor source copy lost exact bytes: "
                    f"{provider.partition_name}"
                )

            materialized_avb_inputs.append(
                Path(
                    provider
                    .source_destination
                    .as_posix()
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="AVB source input",
                operation=(
                    "materializing exact canonical "
                    "descriptor source"
                ),
                item=(
                    provider
                    .source_destination
                    .as_posix()
                ),
            )

        materialized_derived_selinux_sources = []

        for source in derived_selinux_sources:
            destination = (
                output_root
                / Path(
                    source.destination.as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_text(
                source.text,
                encoding="utf-8",
            )

            materialized_derived_selinux_sources.append(
                AndroidDeviceTreeMaterializedDerivedSelinuxSource(
                    relative_path=Path(
                        source.destination.as_posix()
                    ),
                    derived_source_id=(
                        source.derived_source_id
                    ),
                    source_requirement_id=(
                        source.source_requirement_id
                    ),
                    source_representation_id=(
                        source.source_representation_id
                    ),
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Derived SELinux source",
                operation=(
                    "materializing canonical-semantic "
                    "SELinux source"
                ),
                item=source.destination.as_posix(),
            )

        #
        # Exact TreeForge recovery provider build surface.
        #
        recovery_bp = (
            recovery_provider_plan
            .android_bp_path
        )

        if recovery_provider_android_bp_content.strip():
            destination = (
                output_root
                / Path(
                    recovery_bp
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_text(
                recovery_provider_android_bp_content,
                encoding="utf-8",
            )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        recovery_bp.as_posix()
                    ),
                    content_id=(
                        "device-tree:recovery-provider:"
                        "android-bp"
                    ),
                    representation_id=(
                        "device-tree:recovery-provider:"
                        "android-bp"
                    ),
                    family="recovery_provider",
                )
            )

            materialization_current += 1

        wipe = (
            recovery_provider_plan
            .recovery_wipe
        )

        if wipe is not None:
            destination = (
                output_root
                / Path(
                    wipe
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                wipe.source_path,
                destination,
            )

            if (
                destination.read_bytes()
                != wipe.source_path.read_bytes()
            ):
                raise ValueError(
                    "recovery.wipe materialization "
                    "lost exact bytes"
                )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        wipe.destination
                        .as_posix()
                    ),
                    content_id=(
                        "device-tree:recovery-wipe"
                    ),
                    representation_id=(
                        "device-tree:recovery-wipe"
                    ),
                    family="recovery_wipe",
                )
            )

            materialization_current += 1

        for config in (
            recovery_provider_plan
            .config_inputs
        ):
            destination = (
                output_root
                / Path(
                    config
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            content = (
                config
                .source_projection
                .content
            )

            if content.text is not None:
                value = content.text

                if config.kind == "init":
                    value = (
                        normalize_aosp_init_source(
                            value
                        )
                    )

                destination.write_text(
                    value,
                    encoding="utf-8",
                )

            elif content.raw_bytes is not None:
                destination.write_bytes(
                    content.raw_bytes
                )

            else:
                raise ValueError(
                    "recovery provider config has "
                    "no materializable payload"
                )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        config
                        .destination
                        .as_posix()
                    ),
                    content_id=(
                        "device-tree:"
                        f"{config.config_id}"
                    ),
                    representation_id=(
                        config.config_id
                    ),
                    family=(
                        "recovery_"
                        f"{config.kind}"
                    ),
                )
            )

            materialization_current += 1

        for provider in (
            recovery_provider_plan
            .providers
        ):
            destination = (
                output_root
                / Path(
                    provider
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                provider.source_path,
                destination,
            )

            if (
                destination.read_bytes()
                != provider.source_path.read_bytes()
            ):
                raise ValueError(
                    "recovery provider materialization "
                    "lost exact bytes: "
                    f"{provider.provider_id}"
                )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        provider
                        .destination
                        .as_posix()
                    ),
                    content_id=(
                        "device-tree:"
                        f"{provider.provider_id}"
                    ),
                    representation_id=(
                        provider.provider_id
                    ),
                    family="recovery_provider",
                )
            )

            materialization_current += 1

        #
        # Exact non-active first-stage fstab build-source variants.
        #
        # These are observed Android build inputs, not active Reconstruction
        # semantics. They remain outside the canonical source-projection
        # population and are materialized only through the ramdisk/recovery
        # build contract.
        #
        for variant in (
            ramdisk_recovery_build_plan
            .source_variants
        ):
            destination = (
                output_root
                / Path(
                    variant
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            destination.write_bytes(
                variant.payload
            )

            if (
                destination.read_bytes()
                != variant.payload
            ):
                raise ValueError(
                    "ramdisk/recovery source variant "
                    "materialization lost exact bytes: "
                    f"{variant.variant_id}"
                )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        variant
                        .destination
                        .as_posix()
                    ),
                    content_id=(
                        "build-source:"
                        f"{variant.variant_id}"
                    ),
                    representation_id=(
                        variant.variant_id
                    ),
                    family="fstab_variant",
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Ramdisk build-source variant",
                operation=(
                    "materializing exact non-active "
                    "first-stage fstab source"
                ),
                item=(
                    variant
                    .destination
                    .as_posix()
                ),
            )

        for projection in projections:
            destination = (
                output_root
                / Path(
                    projection
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            content = projection.content

            if content.text is not None:
                materialized_text = (
                    content.text
                )

                #
                # Reconstruction remains canonical/source-faithful.
                # Device Tree owns source-build compatibility adaptation.
                #
                if projection.family == "init":
                    materialized_text = (
                        normalize_aosp_init_source(
                            materialized_text
                        )
                    )

                destination.write_text(
                    materialized_text,
                    encoding="utf-8",
                )

            elif content.raw_bytes is not None:
                destination.write_bytes(
                    content.raw_bytes
                )

            else:
                raise ValueError(
                    "Device Tree projection has no materializable "
                    "Reconstruction payload"
                )

            materialized.append(
                AndroidDeviceTreeMaterializedFile(
                    relative_path=Path(
                        projection
                        .destination
                        .as_posix()
                    ),
                    content_id=(
                        projection.content_id
                    ),
                    representation_id=(
                        projection
                        .representation_id
                    ),
                    family=projection.family,
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Generated source files",
                operation="materializing generated source",
                item=projection.destination.as_posix(),
            )

        materialized_artifacts = []

        for projection in artifact_projections:
            source = (
                projection.source_path
            )

            if not source.exists():
                raise ValueError(
                    "canonical preserved Artifact payload "
                    "is not materialized: "
                    f"{source}"
                )

            if not source.is_file():
                raise ValueError(
                    "canonical preserved Artifact payload "
                    "is not a regular host file: "
                    f"{source}"
                )

            expected_size = (
                projection
                .requirement
                .size
            )

            actual_size = (
                source.stat().st_size
            )

            if actual_size != expected_size:
                raise ValueError(
                    "canonical preserved Artifact payload "
                    "size differs from authoritative metadata: "
                    f"artifact={projection.artifact_id}, "
                    f"expected={expected_size}, "
                    f"actual={actual_size}"
                )

            destination = (
                output_root
                / Path(
                    projection
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            copied_size = (
                destination.stat().st_size
            )

            if copied_size != expected_size:
                raise ValueError(
                    "Device Tree preserved Artifact copy "
                    "does not match canonical size: "
                    f"artifact={projection.artifact_id}"
                )

            materialized_artifacts.append(
                AndroidDeviceTreeMaterializedArtifact(
                    relative_path=Path(
                        projection
                        .destination
                        .as_posix()
                    ),
                    artifact_id=(
                        projection.artifact_id
                    ),
                    representation_id=(
                        projection
                        .representation_id
                    ),
                    installed_partition=(
                        projection
                        .installed_partition
                    ),
                    installed_android_path=(
                        projection
                        .installed_android_path
                    ),
                    source_path=source,
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Preserved artifacts",
                operation="materializing preserved artifact",
                item=projection.destination.as_posix(),
            )

        materialized_physical_payloads = []

        for projection in physical_payload_projections:
            source = projection.source_path

            if not source.exists():
                raise ValueError(
                    "canonical requirement-backed Artifact payload "
                    "is not materialized: "
                    f"{source}"
                )

            if not source.is_file():
                raise ValueError(
                    "canonical requirement-backed Artifact payload "
                    "is not a regular host file: "
                    f"{source}"
                )

            expected_size = (
                projection.requirement.size
            )

            actual_size = (
                source.stat().st_size
            )

            if actual_size != expected_size:
                raise ValueError(
                    "canonical requirement-backed Artifact payload "
                    "size differs from authoritative metadata: "
                    f"requirement={projection.requirement_id}, "
                    f"expected={expected_size}, "
                    f"actual={actual_size}"
                )

            destination = (
                output_root
                / Path(
                    projection
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            copied_size = (
                destination.stat().st_size
            )

            if copied_size != expected_size:
                raise ValueError(
                    "Device Tree requirement-backed Artifact copy "
                    "does not match canonical size: "
                    f"requirement={projection.requirement_id}"
                )

            materialized_physical_payloads.append(
                AndroidDeviceTreeMaterializedPhysicalPayload(
                    relative_path=Path(
                        projection
                        .destination
                        .as_posix()
                    ),
                    requirement_id=(
                        projection.requirement_id
                    ),
                    representation_id=(
                        projection.representation_id
                    ),
                    installed_partition=(
                        projection.installed_partition
                    ),
                    installed_android_path=(
                        projection.installed_android_path
                    ),
                    source_path=source,
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Physical payloads",
                operation="materializing canonical physical payload",
                item=projection.destination.as_posix(),
            )

        materialized_vendor_kernel_ramdisk_modules = []

        for projection in (
            vendor_kernel_ramdisk_plan.module_projections
        ):
            source = projection.source_path

            if not source.exists():
                raise ValueError(
                    "canonical vendor_kernel_boot module payload "
                    "is not materialized: "
                    f"{source}"
                )

            if not source.is_file():
                raise ValueError(
                    "canonical vendor_kernel_boot module payload "
                    "is not a regular host file: "
                    f"{source}"
                )

            expected_size = projection.requirement.size
            actual_size = source.stat().st_size

            if actual_size != expected_size:
                raise ValueError(
                    "canonical vendor_kernel_boot module size differs "
                    "from authoritative metadata: "
                    f"artifact={projection.artifact_id}, "
                    f"expected={expected_size}, "
                    f"actual={actual_size}"
                )

            destination = (
                output_root
                / Path(
                    projection.destination.as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            copied_size = destination.stat().st_size

            if copied_size != expected_size:
                raise ValueError(
                    "Device Tree vendor kernel ramdisk module copy "
                    "does not preserve canonical size: "
                    f"artifact={projection.artifact_id}"
                )

            materialized_vendor_kernel_ramdisk_modules.append(
                AndroidDeviceTreeMaterializedVendorKernelRamdiskModule(
                    relative_path=Path(
                        projection.destination.as_posix()
                    ),
                    artifact_id=projection.artifact_id,
                    representation_id=(
                        projection.representation_id
                    ),
                    source_path=source,
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Vendor kernel ramdisk",
                operation=(
                    "materializing canonical first-stage "
                    "kernel module"
                ),
                item=projection.destination.as_posix(),
            )

        materialized_apex_payloads = []

        for projection in apex_payload_projections:
            source = projection.source_path

            if not source.exists():
                raise ValueError(
                    "canonical root-runtime APEX payload "
                    "is not materialized: "
                    f"{source}"
                )

            if not source.is_file():
                raise ValueError(
                    "canonical root-runtime APEX payload "
                    "is not a regular host file: "
                    f"{source}"
                )

            expected_size = (
                projection
                .requirement
                .artifact
                .size_bytes
            )

            actual_size = (
                source.stat().st_size
            )

            if (
                expected_size is not None
                and actual_size != expected_size
            ):
                raise ValueError(
                    "canonical root-runtime APEX payload "
                    "size differs from authoritative "
                    "Extraction metadata: "
                    f"requirement={projection.requirement_id}, "
                    f"expected={expected_size}, "
                    f"actual={actual_size}"
                )

            destination = (
                output_root
                / Path(
                    projection
                    .destination
                    .as_posix()
                )
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            copyfile(
                source,
                destination,
            )

            copied_size = (
                destination.stat().st_size
            )

            if copied_size != actual_size:
                raise ValueError(
                    "Device Tree APEX payload copy "
                    "does not preserve exact source size: "
                    f"requirement={projection.requirement_id}, "
                    f"source={actual_size}, "
                    f"copied={copied_size}"
                )

            materialized_apex_payloads.append(
                AndroidDeviceTreeMaterializedApexPayload(
                    relative_path=Path(
                        projection
                        .destination
                        .as_posix()
                    ),
                    requirement_id=(
                        projection.requirement_id
                    ),
                    representation_id=(
                        projection.representation_id
                    ),
                    installed_partition=(
                        projection.installed_partition
                    ),
                    installed_android_path=(
                        projection.installed_android_path
                    ),
                    source_path=source,
                )
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="APEX payloads",
                operation=(
                    "materializing canonical "
                    "root-runtime APEX payload"
                ),
                item=projection.destination.as_posix(),
            )

        elf_android_bp_relative_path = (
            identity.proprietary_root
            / "Android.bp"
        )

        elf_android_bp_path = (
            output_root
            / elf_android_bp_relative_path
        )

        elf_android_bp_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        elf_android_bp_path.write_text(
            proprietary_android_bp_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing ELF/APEX Android.bp",
            item=elf_android_bp_relative_path.as_posix(),
        )

        vintf_android_bp_relative_path = (
            PurePosixPath(
                identity.device_root.as_posix()
            )
            / "vintf"
            / "Android.bp"
        )

        vintf_android_bp_path = (
            output_root
            / Path(
                vintf_android_bp_relative_path.as_posix()
            )
        )

        vintf_android_bp_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        vintf_android_bp_path.write_text(
            vintf_android_bp_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing VINTF Android.bp",
            item=vintf_android_bp_relative_path.as_posix(),
        )

        apk_android_mk_relative_path = (
            identity.proprietary_root.parent
            / "Android.mk"
        )

        apk_android_mk_path = (
            output_root
            / Path(
                apk_android_mk_relative_path.as_posix()
            )
        )

        apk_android_mk_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        apk_android_mk_path.write_text(
            apk_android_mk_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing APK Android.mk",
            item=apk_android_mk_relative_path.as_posix(),
        )

        vendor_device_root = (
            identity.proprietary_root.parent
        )

        vendor_makefile_relative_path = (
            vendor_device_root
            / (
                f"{vendor_device_root.name}"
                "-vendor.mk"
            )
        )

        vendor_makefile_path = (
            output_root
            / vendor_makefile_relative_path
        )

        vendor_makefile_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        vendor_makefile_path.write_text(
            product_makefile_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing vendor product integration",
            item=vendor_makefile_relative_path.as_posix(),
        )

        #
        # Materialize TreeForge-owned BoardConfig capability fragments.
        #
        for (
            fragment_relative_path,
            fragment_content,
        ) in board_config_fragments:
            fragment_path = (
                output_root
                / Path(
                    fragment_relative_path.as_posix()
                )
            )

            fragment_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            fragment_path.write_text(
                fragment_content,
                encoding="utf-8",
            )

            materialization_current += 1

            self._report_progress(
                state=ProgressState.RUNNING,
                current=materialization_current,
                total=materialization_total,
                subject="Build files",
                operation=(
                    "materializing TreeForge "
                    "BoardConfig capability fragment"
                ),
                item=fragment_relative_path.as_posix(),
            )

        android_board_relative_path = (
            avb_build_plan.android_board_path
        )

        android_board_path = (
            output_root
            / Path(
                android_board_relative_path
                .as_posix()
            )
        )

        android_board_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        android_board_path.write_text(
            android_board_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation=(
                "materializing minimal Android-native "
                "construction glue"
            ),
            item=(
                android_board_relative_path
                .as_posix()
            ),
        )

        kernel_board_config_relative_path = (
            identity.device_root
            / "BoardConfig.mk"
        )

        kernel_board_config_path = (
            output_root
            / kernel_board_config_relative_path
        )

        kernel_board_config_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        kernel_board_config_path.write_text(
            board_config_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing BoardConfig.mk",
            item=kernel_board_config_relative_path.as_posix(),
        )

        board_info_relative_path = (
            platform_build_contract
            .board_info_path
        )

        board_info_path = (
            output_root
            / board_info_relative_path
        )

        board_info_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        board_info_path.write_text(
            AndroidDeviceTreePlatformBuildContractRenderer
            .render_board_info(
                platform_build_contract
            ),
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing board-info.txt",
            item=board_info_relative_path.as_posix(),
        )

        #
        # Canonical Android product spine.
        #
        # Device Tree owns concrete Android build syntax and maps canonical
        # Universe semantics to Android-version-specific product policy.
        #
        device_makefile_relative_path = (
            identity.device_root
            / "device.mk"
        )

        device_makefile_path = (
            output_root
            / device_makefile_relative_path
        )

        device_makefile_content = (
            AndroidDeviceTreeProductSpineRenderer
            .render_device_makefile(
                identity=identity,
            )
        )

        device_makefile_content = (
            "\n\n".join(
                content.rstrip()
                for content
                in (
                    device_makefile_content,
                    platform_build_contract_product_content,
                    native_boot_product_content,
                    runtime_property_product_content,
                )
                if content.strip()
            )
            + "\n"
        )

        device_makefile_path.write_text(
            device_makefile_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing device.mk",
            item=device_makefile_relative_path.as_posix(),
        )

        product_makefile_relative_path = (
            identity.device_root
            / f"{identity.product}.mk"
        )

        product_makefile_path = (
            output_root
            / product_makefile_relative_path
        )

        product_makefile_content = (
            AndroidDeviceTreeProductSpineRenderer
            .render_product_makefile(
                identity=identity,
                policy=product_policy,
                use_dynamic_partitions=(
                    dynamic_partition_config
                    is not None
                ),
            )
        )

        product_makefile_path.write_text(
            product_makefile_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.RUNNING,
            current=materialization_current,
            total=materialization_total,
            subject="Build files",
            operation="materializing product makefile",
            item=product_makefile_relative_path.as_posix(),
        )

        android_products_relative_path = (
            identity.device_root
            / "AndroidProducts.mk"
        )

        android_products_path = (
            output_root
            / android_products_relative_path
        )

        android_products_content = (
            AndroidDeviceTreeProductSpineRenderer
            .render_android_products(
                identity=identity,
            )
        )

        android_products_path.write_text(
            android_products_content,
            encoding="utf-8",
        )

        materialization_current += 1

        self._report_progress(
            state=ProgressState.COMPLETE,
            current=materialization_current,
            total=materialization_total,
            subject="Device Tree materialization",
            operation="Device Tree materialization complete",
            item=android_products_relative_path.as_posix(),
        )

        return AndroidDeviceTreeResult(
            device_tree_input=device_tree_input,
            projections=projections,
            artifact_projections=(
                artifact_projections
            ),
            physical_payload_projections=(
                physical_payload_projections
            ),
            vendor_kernel_ramdisk_plan=(
                vendor_kernel_ramdisk_plan
            ),
            native_boot_build_plan=(
                native_boot_build_plan
            ),
            avb_build_plan=(
                avb_build_plan
            ),
            apex_payload_projections=(
                apex_payload_projections
            ),
            product_copy_files=(
                product_copy_files
            ),
            product_policy=(
                product_policy
            ),
            kernel_board_config=(
                kernel_board_config
            ),
            vintf_build_config=(
                vintf_build_config
            ),
            build_realizations=(
                build_realizations
            ),
            derived_selinux_sources=(
                derived_selinux_sources
            ),
            materialized_derived_selinux_sources=tuple(
                materialized_derived_selinux_sources
            ),
            materialized_files=tuple(
                materialized
            ),
            materialized_artifacts=tuple(
                materialized_artifacts
            ),
            materialized_physical_payloads=tuple(
                materialized_physical_payloads
            ),
            materialized_vendor_kernel_ramdisk_modules=tuple(
                materialized_vendor_kernel_ramdisk_modules
            ),
            materialized_apex_payloads=tuple(
                materialized_apex_payloads
            ),
            materialized_native_boot_inputs=tuple(
                materialized_native_boot_inputs
            ),
            materialized_avb_inputs=tuple(
                materialized_avb_inputs
            ),
        )
