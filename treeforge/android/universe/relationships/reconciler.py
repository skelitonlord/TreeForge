from __future__ import annotations

from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerApexNamespaceStatus,
)

from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerApexPublicLibraryConclusion,
    AndroidUniverseLinkerApexPublicLibraryStatus,
)

from treeforge.android.universe.artifact.namespace import (
    artifact_android_namespace_paths,
    artifact_projects_to_android_runtime_namespace,
    filesystem_projects_to_android_runtime_namespace,
    metadata_android_namespace_paths,
    normalize_android_namespace_path,
)
from treeforge.android.universe.boot.requirement import (
    AndroidUniverseBootRequirement,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleRequirement,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerApexNamespaceInput,
    AndroidUniverseArtRuntimeClasspathDexEvidence,
    AndroidUniverseArtRuntimeClasspathRelationship,
    AndroidUniverseArtRuntimeClasspathVdexEvidence,
    AndroidUniverseArtRuntimeClasspathVdexMatchKind,
    AndroidUniverseFirstStageKernelModuleLoadingRelationship,
)

from treeforge.android.universe.art_runtime.requirement import (
    AndroidUniverseArtRuntimeRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathInstalledJarResolution,
    AndroidUniverseClasspathRequirement,
)


from collections import defaultdict

from treeforge.android.parsing.classpath import (
    AndroidClasspathKind,
)
from treeforge.android.universe.art_runtime.semantics import (
    AndroidUniverseArtRuntimeVdexDispositionStatus,
)
from pathlib import PurePosixPath

from treeforge.android.extraction.model import (
    ExtractionOperation,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
)

from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.apk.requirement import (
    AndroidUniverseApkPackageRequirement,
    AndroidUniverseApkRequirement,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
    AndroidUniverseElfRole,
)
from treeforge.android.universe.apex.deployment_context import (
    AndroidUniverseApexDeploymentPartition,
)
from treeforge.android.universe.linker.requirement import (
    AndroidUniverseLinkerRequirement,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerNativeLibraryPolicyKind,
    AndroidUniverseLinkerProtobufUsage,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)

from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.init.action_command.semantics import (
    AndroidUniverseInitActionCommandClassRestartSemantics,
    AndroidUniverseInitActionCommandRestartSemantics,
    AndroidUniverseInitActionCommandKeyValueSemantics,
    AndroidUniverseInitActionCommandScalarSemantics,
    AndroidUniverseInitActionCommandTargetSemantics,
)
from treeforge.android.universe.init.model import (
    AndroidUniverseInitServiceRequirement,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportResolution,
    android_init_inapplicable_source_paths,
)
from treeforge.android.universe.init.property_expansion import (
    AndroidUniverseInitPropertyExpansionStatus,
    AndroidUniverseInitPropertyExpressionResolver,
)
from treeforge.android.universe.init.service_reconciliation import (
    AndroidUniverseInitServiceResolution,
    AndroidUniverseInitSourceContext,
    android_init_source_context,
)
from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)
from treeforge.android.universe.runtime_property.context import (
    resolve_android_property_contexts,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseCrossFamilyRelationship,
    AndroidUniverseInitExecutableArtifactRelationship,
    AndroidUniverseInitExecutableSelinuxRelationship,
    AndroidUniverseInitEventTriggerRelationship,
    AndroidUniverseInitPropertyCommandRelationship,
    AndroidUniverseInitPropertyTriggerRelationship,
    AndroidUniverseInitClassControlRelationship,
    AndroidUniverseInitServiceControlRelationship,
    AndroidUniverseInitOnRestartClassControlRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
    AndroidUniverseInitOnRestartPropertyCommandRelationship,
    AndroidUniverseInitInterfaceVintfRelationship,
    AndroidUniverseApkVintfImplementationEvidence,
    AndroidUniverseApkVintfStructuralProviderEvidence,
    AndroidUniverseApkVintfStructuralProviderRelationship,
    AndroidUniverseInitSeclabelSelinuxRelationship,
    AndroidUniversePropertySelinuxRelationship,
    AndroidUniverseRelationshipKind,
    AndroidUniverseRelationshipStatus,
    AndroidUniverseVintfInterfaceEvidence,
    AndroidUniverseLinkerApexRelationship,
    AndroidUniverseLinkerApexContextApplicability,
    AndroidUniverseLinkerApexNativeLibraryAliasProvider,
    AndroidUniverseLinkerApexNativeLibraryApexProvider,
    AndroidUniverseLinkerApexNativeLibraryConclusion,
    AndroidUniverseLinkerApexNativeLibraryProviderKind,
    AndroidUniverseLinkerElfConfigurationScope,
    AndroidUniverseLinkerElfContext,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextKind,
)
from treeforge.android.universe.selinux.policy_graph import (
    AndroidUniverseSelinuxPolicyGraph,
)
from treeforge.android.universe.selinux.symbol import (
    AndroidUniverseSelinuxSymbolKind,
)
from treeforge.android.universe.vintf.document import (
    AndroidUniverseVintfDocumentKind,
    AndroidUniverseVintfDocumentSide,
)
from treeforge.android.universe.vintf.hal import (
    AndroidUniverseVintfHalFormat,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)


class AndroidUniverseCrossFamilyReconciler:
    @staticmethod
    def reconcile_art_runtime_classpath(
        *,
        classpath_requirement,
        art_runtime_requirement,
    ) -> tuple[
        AndroidUniverseArtRuntimeClasspathRelationship,
        ...,
    ]:
        """
        Relate every canonical effective Classpath entry to all ART
        OatDexFile observations whose canonical base runtime location equals
        that entry's literal runtime JAR path.

        Classpath applicability, effective ordering, and installed-artifact
        resolution remain owned entirely by the Classpath family.

        ART parsing and OAT structure remain owned entirely by ART Runtime.

        This method performs only the late semantic cross-family join.
        """

        if classpath_requirement is None:
            return ()

        if art_runtime_requirement is None:
            return ()

        if not isinstance(
            classpath_requirement,
            AndroidUniverseClasspathRequirement,
        ):
            raise TypeError(
                "classpath_requirement must be an "
                "AndroidUniverseClasspathRequirement or None"
            )

        if not isinstance(
            art_runtime_requirement,
            AndroidUniverseArtRuntimeRequirement,
        ):
            raise TypeError(
                "art_runtime_requirement must be an "
                "AndroidUniverseArtRuntimeRequirement or None"
            )

        installed_by_entry_id = {
            id(
                resolution.entry
            ): resolution
            for resolution
            in classpath_requirement.installed_jar_resolutions
        }

        art_by_base_location = defaultdict(
            list
        )

        for oat in (
            art_runtime_requirement.source.oat_files
        ):
            for oat_dex_file in (
                oat.oat_dex_files
            ):
                base_location = (
                    oat_dex_file.dex_file_location.split(
                        "!",
                        1,
                    )[0]
                )

                art_by_base_location[
                    base_location
                ].append(
                    AndroidUniverseArtRuntimeClasspathDexEvidence(
                        oat=oat,
                        oat_dex_file=oat_dex_file,
                        base_location=base_location,
                    )
                )

        standalone_vdex_by_name = {}
        base_boot_vdex = None

        for disposition in (
            art_runtime_requirement.vdex_dispositions
        ):
            if (
                disposition.status
                is not AndroidUniverseArtRuntimeVdexDispositionStatus
                .NO_OAT_PEER
            ):
                continue

            vdex_path = (
                disposition.vdex.source.android_path
            )
            vdex_stem = vdex_path.stem

            if vdex_stem == "boot":
                if base_boot_vdex is not None:
                    raise ValueError(
                        "multiple standalone base boot.vdex sources "
                        "cannot be reconciled canonically"
                    )

                base_boot_vdex = disposition
                continue

            if not vdex_stem.startswith(
                "boot-"
            ):
                continue

            logical_name = vdex_stem[
                len("boot-"):
            ]

            if logical_name in standalone_vdex_by_name:
                raise ValueError(
                    "multiple standalone boot VDEX sources share "
                    f"logical name: {logical_name}"
                )

            standalone_vdex_by_name[
                logical_name
            ] = disposition

        relationships = []

        for effective in (
            classpath_requirement.effective_classpaths
        ):
            for entry in effective.entries:
                installed_resolution = (
                    installed_by_entry_id.get(
                        id(
                            entry
                        )
                    )
                )

                if installed_resolution is None:
                    raise ValueError(
                        "every effective Classpath entry must preserve "
                        "its installed-JAR resolution before ART Runtime "
                        "cross-family reconciliation"
                    )

                declared_path = (
                    entry.requirement.declared_path
                )

                if not declared_path.startswith(
                    "/"
                ):
                    declared_path = (
                        "/"
                        + declared_path
                    )

                evidence = tuple(
                    art_by_base_location.get(
                        declared_path,
                        (),
                    )
                )

                vdex_evidence = []

                declared_name = declared_path.rsplit(
                    "/",
                    1,
                )[-1]

                declared_stem = (
                    declared_name[:-4]
                    if declared_name.endswith(
                        ".jar"
                    )
                    else declared_name
                )

                named_vdex = (
                    standalone_vdex_by_name.get(
                        declared_stem
                    )
                )

                if (
                    effective.classpath
                    in {
                        AndroidClasspathKind.BOOTCLASSPATH,
                        AndroidClasspathKind.DEX2OATBOOTCLASSPATH,
                    }
                    and named_vdex is not None
                ):
                    vdex_evidence.append(
                        AndroidUniverseArtRuntimeClasspathVdexEvidence(
                            disposition=named_vdex,
                            match_kind=(
                                AndroidUniverseArtRuntimeClasspathVdexMatchKind
                                .NAMED_BOOT_COMPONENT
                            ),
                        )
                    )

                if (
                    effective.classpath
                    is AndroidClasspathKind.DEX2OATBOOTCLASSPATH
                    and entry.classpath_index == 0
                    and base_boot_vdex is not None
                ):
                    vdex_evidence.append(
                        AndroidUniverseArtRuntimeClasspathVdexEvidence(
                            disposition=base_boot_vdex,
                            match_kind=(
                                AndroidUniverseArtRuntimeClasspathVdexMatchKind
                                .BASE_DEX2OAT_BOOT
                            ),
                        )
                    )

                canonical_vdex_evidence = tuple(
                    vdex_evidence
                )

                relationships.append(
                    AndroidUniverseArtRuntimeClasspathRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .ART_RUNTIME_CLASSPATH
                        ),
                        status=(
                            AndroidUniverseRelationshipStatus.RESOLVED
                            if (
                                evidence
                                or canonical_vdex_evidence
                            )
                            else AndroidUniverseRelationshipStatus.UNRESOLVED
                        ),
                        entry=entry,
                        installed_jar_resolution=(
                            installed_resolution
                        ),
                        dex_evidence=evidence,
                        vdex_evidence=canonical_vdex_evidence,
                    )
                )

        return tuple(
            sorted(
                relationships,
                key=lambda relationship: (
                    relationship.relationship_id
                ),
            )
        )

    @staticmethod
    def reconcile_first_stage_kernel_module_loading(
        *,
        boot_requirements,
        kernel_module_requirement,
    ) -> tuple[
        AndroidUniverseFirstStageKernelModuleLoadingRelationship,
        ...,
    ]:
        """
        Relate Boot-owned first-stage loading policy to the exact
        vendor_kernel_boot modules.load population.

        This is intentionally a late cross-family reconciliation because
        canonical Kernel Module semantics are constructed after the original
        INIT/SELinux/VINTF relationship pass.

        No Parsing input is reread or reinterpreted here.
        """

        if kernel_module_requirement is None:
            return ()

        if not isinstance(
            kernel_module_requirement,
            AndroidUniverseKernelModuleRequirement,
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement or None"
            )

        policies = []

        for requirement in boot_requirements:
            if not isinstance(
                requirement,
                AndroidUniverseBootRequirement,
            ):
                raise TypeError(
                    "boot_requirements must contain only "
                    "AndroidUniverseBootRequirement instances"
                )

            if (
                requirement.container_format
                != "android_vendor_boot"
            ):
                continue

            bootconfig = (
                requirement.semantics.bootconfig
            )

            if bootconfig is None:
                continue

            policies.extend(
                bootconfig.module_loading_policies
            )

        if not policies:
            return ()

        load_entries = tuple(
            sorted(
                (
                    entry
                    for entry
                    in kernel_module_requirement.load_entries
                    if (
                        entry.module.source.elf.source
                        .filesystem_source.source_name
                        == "vendor_kernel_boot"
                    )
                ),
                key=lambda entry: (
                    entry.sequence_index
                ),
            )
        )

        if not load_entries:
            return ()

        return tuple(
            AndroidUniverseFirstStageKernelModuleLoadingRelationship(
                kind=(
                    AndroidUniverseRelationshipKind
                    .FIRST_STAGE_KERNEL_MODULE_LOADING
                ),
                status=(
                    AndroidUniverseRelationshipStatus.RESOLVED
                ),
                policy=policy,
                load_entries=load_entries,
            )
            for policy in policies
        )


    @staticmethod
    def reconcile_linker_elf_contexts(
        *,
        linker_requirement,
        elf_requirements,
        apex_requirements,
    ) -> tuple[
        AndroidUniverseLinkerElfContext,
        ...,
    ]:
        """
        Establish runtime and configuration-scope context for every canonical
        ELF requirement.

        Runtime membership comes from canonical Extraction ancestry. ELF
        objects whose filesystem lineage passes through APEX container
        extraction are reconciled to canonical APEX requirements by nearest
        exact common-ancestor specificity.

        This slice deliberately does not select Linker sections/namespaces,
        synthesize APEX runtime mount paths, or resolve DT_NEEDED entries.
        """

        if linker_requirement is None:
            return ()

        if not isinstance(
            elf_requirements,
            tuple,
        ):
            raise TypeError(
                "elf_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            )
            for requirement
            in elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement instances"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        def artifact_lineage(
            artifact,
        ) -> tuple:
            values = []

            current = artifact

            while current is not None:
                values.append(
                    current
                )
                current = current.parent

            return tuple(
                values
            )

        apex_lineages = tuple(
            (
                requirement,
                artifact_lineage(
                    requirement.artifact
                ),
            )
            for requirement
            in apex_requirements
        )

        contexts = []

        for elf_requirement in elf_requirements:
            parsed_elf = (
                elf_requirement.source
            )

            filesystem_source = (
                parsed_elf.source.filesystem_source
            )

            extraction_artifact = (
                parsed_elf.source.extraction_artifact
            )

            if filesystem_source is not None:
                runtime_context = (
                    AndroidUniverseRuntimeContextResolver
                    .resolve_filesystem_source(
                        filesystem_source
                    )
                )

                elf_origin = (
                    filesystem_source.artifact
                )

            elif extraction_artifact is not None:
                runtime_context = (
                    AndroidUniverseRuntimeContextResolver
                    .resolve_artifact(
                        extraction_artifact
                    )
                )

                elf_origin = extraction_artifact

            else:
                raise ValueError(
                    "canonical ELF source has no runtime-resolvable "
                    "origin"
                )

            matched_runtime_policies = tuple(
                policy
                for policy
                in linker_requirement.runtime_policies
                if (
                    AndroidUniverseRuntimeContextResolver
                    .same_runtime(
                        policy.runtime_context,
                        runtime_context,
                    )
                )
            )

            elf_lineage = artifact_lineage(
                elf_origin
            )

            #
            # APEX configuration scope is established only when the ELF's
            # owning filesystem extraction is itself the payload produced
            # directly by an APEX container extraction.
            #
            # Do not search arbitrary ancestors for APEX container
            # extraction: a nested Android runtime may itself have been
            # discovered through an outer APEX payload while the ELF belongs
            # to that runtime's ordinary partition filesystem.
            #
            # This remains purely structural Extraction provenance and does
            # not depend on source names, package names, partition names, or
            # device-specific knowledge.
            #
            filesystem_artifact = (
                filesystem_source.artifact
                if filesystem_source is not None
                else None
            )

            filesystem_parent = (
                filesystem_artifact.parent
                if filesystem_artifact is not None
                else None
            )

            is_apex_backed = (
                filesystem_parent is not None
                and filesystem_parent.operation.value
                == "apex_container_extraction"
            )

            apex_candidates = ()
            selected_apex_requirement = None

            if is_apex_backed:
                scored = []

                for (
                    apex_requirement,
                    apex_lineage,
                ) in apex_lineages:
                    if not (
                        AndroidUniverseRuntimeContextResolver
                        .same_runtime(
                            apex_requirement.runtime_context,
                            runtime_context,
                        )
                    ):
                        continue

                    common = tuple(
                        (
                            elf_index,
                            apex_index,
                        )
                        for elf_index, elf_artifact
                        in enumerate(
                            elf_lineage
                        )
                        for apex_index, apex_artifact
                        in enumerate(
                            apex_lineage
                        )
                        if elf_artifact is apex_artifact
                    )

                    if not common:
                        continue

                    nearest = min(
                        common,
                        key=lambda item: (
                            item[0],
                            item[1],
                        ),
                    )

                    scored.append(
                        (
                            nearest[
                                0
                            ],
                            nearest[
                                1
                            ],
                            apex_requirement,
                        )
                    )

                if scored:
                    best_key = min(
                        (
                            elf_index,
                            apex_index,
                        )
                        for (
                            elf_index,
                            apex_index,
                            _,
                        )
                        in scored
                    )

                    apex_candidates = tuple(
                        requirement
                        for (
                            elf_index,
                            apex_index,
                            requirement,
                        )
                        in scored
                        if (
                            elf_index,
                            apex_index,
                        )
                        == best_key
                    )

                if (
                    len(
                        apex_candidates
                    )
                    == 1
                ):
                    selected_apex_requirement = (
                        apex_candidates[
                            0
                        ]
                    )

                configuration_scope = (
                    AndroidUniverseLinkerElfConfigurationScope
                    .APEX
                )

            else:
                configuration_scope = (
                    AndroidUniverseLinkerElfConfigurationScope
                    .BASE
                )

            if (
                len(
                    matched_runtime_policies
                ) > 1
                or (
                    configuration_scope
                    is AndroidUniverseLinkerElfConfigurationScope.APEX
                    and len(
                        apex_candidates
                    ) > 1
                )
            ):
                status = (
                    AndroidUniverseRelationshipStatus.AMBIGUOUS
                )

            elif (
                len(
                    matched_runtime_policies
                ) == 1
                and (
                    configuration_scope
                    is AndroidUniverseLinkerElfConfigurationScope.BASE
                    or len(
                        apex_candidates
                    ) == 1
                )
            ):
                status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                )

            else:
                status = (
                    AndroidUniverseRelationshipStatus.UNRESOLVED
                )

            contexts.append(
                AndroidUniverseLinkerElfContext(
                    elf_requirement=(
                        elf_requirement
                    ),
                    runtime_context=(
                        runtime_context
                    ),
                    configuration_scope=(
                        configuration_scope
                    ),
                    matched_runtime_policies=(
                        matched_runtime_policies
                    ),
                    apex_candidates=(
                        apex_candidates
                    ),
                    selected_apex_requirement=(
                        selected_apex_requirement
                    ),
                    status=status,
                )
            )

        return tuple(
            sorted(
                contexts,
                key=lambda item: (
                    item.context_id
                ),
            )
        )


    @staticmethod
    def reconcile_linker_apex_public_libraries(
        *,
        linker_requirement,
        apex_requirements,
        treble_enabled,
    ) -> tuple[
        AndroidUniverseLinkerApexPublicLibraryConclusion,
        ...,
    ]:
        """
        Reproduce AOSP ApexInfo.public_libs augmentation from canonical
        TreeForge evidence.

        SYSTEM and SYSTEM_EXT consume SYSTEM_PUBLIC.

        PRODUCT consumes SYSTEM_PUBLIC only when Treble is explicitly false.
        When Treble is true, PRODUCT is separated from system and receives no
        public-library augmentation.

        VENDOR and ODM consume VENDOR_PUBLIC.

        Policy selection is constrained to the exact canonical runtime.
        EXTENDED_PUBLIC is deliberately excluded because AOSP
        ScanActiveApexes does not use public.libraries-*.txt extensions for
        ApexInfo.public_libs.

        No namespace generation or Reconstruction behavior occurs here.
        """

        if linker_requirement is None:
            if not isinstance(
                apex_requirements,
                tuple,
            ):
                raise TypeError(
                    "apex_requirements must be a tuple"
                )

            if not all(
                isinstance(
                    apex,
                    AndroidUniverseApexRequirement,
                )
                for apex
                in apex_requirements
            ):
                raise TypeError(
                    "apex_requirements must contain only "
                    "AndroidUniverseApexRequirement instances"
                )

            return tuple(
                sorted(
                    (
                        AndroidUniverseLinkerApexPublicLibraryConclusion(
                            apex_requirement=apex,
                            matched_runtime_policies=(),
                            policy_candidates=(),
                            selected_public_policy=None,
                            public_libraries=(),
                            status=(
                                AndroidUniverseLinkerApexPublicLibraryStatus
                                .UNRESOLVED
                            ),
                        )
                        for apex
                        in apex_requirements
                    ),
                    key=lambda conclusion: (
                        conclusion.conclusion_id
                    ),
                )
            )

        if not isinstance(
            linker_requirement,
            AndroidUniverseLinkerRequirement,
        ):
            raise TypeError(
                "linker_requirement must be an "
                "AndroidUniverseLinkerRequirement or None"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                apex,
                AndroidUniverseApexRequirement,
            )
            for apex
            in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        if (
            treble_enabled is not None
            and not isinstance(
                treble_enabled,
                bool,
            )
        ):
            raise TypeError(
                "treble_enabled must be a bool or None"
            )

        conclusions = []

        for apex in apex_requirements:
            matching_runtime_policies = tuple(
                policy
                for policy
                in linker_requirement.runtime_policies
                if (
                    AndroidUniverseRuntimeContextResolver
                    .same_runtime(
                        policy.runtime_context,
                        apex.runtime_context,
                    )
                )
            )

            if not matching_runtime_policies:
                conclusions.append(
                    AndroidUniverseLinkerApexPublicLibraryConclusion(
                        apex_requirement=apex,
                        matched_runtime_policies=(),
                        policy_candidates=(),
                        selected_public_policy=None,
                        public_libraries=(),
                        status=(
                            AndroidUniverseLinkerApexPublicLibraryStatus
                            .UNRESOLVED
                        ),
                    )
                )
                continue

            if len(
                matching_runtime_policies
            ) > 1:
                conclusions.append(
                    AndroidUniverseLinkerApexPublicLibraryConclusion(
                        apex_requirement=apex,
                        matched_runtime_policies=(
                            matching_runtime_policies
                        ),
                        policy_candidates=(),
                        selected_public_policy=None,
                        public_libraries=(),
                        status=(
                            AndroidUniverseLinkerApexPublicLibraryStatus
                            .AMBIGUOUS
                        ),
                    )
                )
                continue

            runtime_policy = (
                matching_runtime_policies[
                    0
                ]
            )

            deployment = (
                apex.deployment_context.partition
            )

            policy_kind = None
            known_empty = False
            indeterminate = False

            if deployment in {
                AndroidUniverseApexDeploymentPartition.SYSTEM,
                AndroidUniverseApexDeploymentPartition.SYSTEM_EXT,
            }:
                policy_kind = (
                    AndroidUniverseLinkerNativeLibraryPolicyKind
                    .SYSTEM_PUBLIC
                )

            elif deployment in {
                AndroidUniverseApexDeploymentPartition.VENDOR,
                AndroidUniverseApexDeploymentPartition.ODM,
            }:
                policy_kind = (
                    AndroidUniverseLinkerNativeLibraryPolicyKind
                    .VENDOR_PUBLIC
                )

            elif (
                deployment
                is AndroidUniverseApexDeploymentPartition.PRODUCT
            ):
                if treble_enabled is False:
                    policy_kind = (
                        AndroidUniverseLinkerNativeLibraryPolicyKind
                        .SYSTEM_PUBLIC
                    )

                elif treble_enabled is True:
                    #
                    # AOSP ApexInfo::InSystem() is false for PRODUCT on a
                    # Treble device, while InProduct() is true. ScanActiveApexes
                    # therefore performs no public_libs augmentation.
                    #
                    known_empty = True

                else:
                    indeterminate = True

            else:
                indeterminate = True

            if known_empty:
                conclusions.append(
                    AndroidUniverseLinkerApexPublicLibraryConclusion(
                        apex_requirement=apex,
                        matched_runtime_policies=(runtime_policy,),
                        policy_candidates=(),
                        selected_public_policy=None,
                        public_libraries=(),
                        status=(
                            AndroidUniverseLinkerApexPublicLibraryStatus
                            .ABSENT
                        ),
                    )
                )
                continue

            if indeterminate:
                conclusions.append(
                    AndroidUniverseLinkerApexPublicLibraryConclusion(
                        apex_requirement=apex,
                        matched_runtime_policies=(runtime_policy,),
                        policy_candidates=(),
                        selected_public_policy=None,
                        public_libraries=(),
                        status=(
                            AndroidUniverseLinkerApexPublicLibraryStatus
                            .UNRESOLVED
                        ),
                    )
                )
                continue

            candidates = tuple(
                configuration
                for configuration
                in runtime_policy.native_library_configurations
                if (
                    configuration.policy_kind
                    is policy_kind
                )
            )

            candidates = tuple(
                sorted(
                    candidates,
                    key=lambda configuration: (
                        configuration.source.source.identity_key
                    ),
                )
            )

            if len(
                candidates
            ) == 0:
                #
                # ReadPublicLibrariesOpt() treats a missing canonical public
                # library file as a valid empty public-library set.
                #
                status = (
                    AndroidUniverseLinkerApexPublicLibraryStatus.ABSENT
                )

                selected = None
                public_libraries = ()

            elif len(
                candidates
            ) > 1:
                status = (
                    AndroidUniverseLinkerApexPublicLibraryStatus.AMBIGUOUS
                )

                selected = None
                public_libraries = ()

            else:
                candidate = (
                    candidates[
                        0
                    ]
                )

                if candidate.uninterpreted_declarations:
                    #
                    # Do not silently derive a partial public population from a
                    # policy whose declarations are not completely understood.
                    #
                    status = (
                        AndroidUniverseLinkerApexPublicLibraryStatus
                        .UNRESOLVED
                    )

                    selected = None
                    public_libraries = ()

                else:
                    policy_names = {
                        declaration.library_name
                        for declaration
                        in candidate.declarations
                    }

                    public_libraries = tuple(
                        library_name
                        for library_name
                        in apex.provide_native_libs
                        if library_name
                        in policy_names
                    )

                    status = (
                        AndroidUniverseLinkerApexPublicLibraryStatus
                        .RESOLVED
                    )

                    selected = candidate

            conclusions.append(
                AndroidUniverseLinkerApexPublicLibraryConclusion(
                    apex_requirement=apex,
                    matched_runtime_policies=(runtime_policy,),
                    policy_candidates=candidates,
                    selected_public_policy=selected,
                    public_libraries=public_libraries,
                    status=status,
                )
            )

        return tuple(
            sorted(
                conclusions,
                key=lambda conclusion: (
                    conclusion.conclusion_id
                ),
            )
        )

    @staticmethod
    def reconcile_linker_apex_namespace_inputs(
        *,
        linker_requirement,
        apex_requirements,
    ) -> tuple[
        AndroidUniverseLinkerApexNamespaceInput,
        ...,
    ]:
        """
        Associate each canonical APEX requirement with its exact APEX-local
        linker.config.pb policy, when present.

        A protobuf semantic is eligible only when its parser filesystem is
        structurally APEX-backed: the filesystem Extraction artifact's direct
        parent must be the canonical ``apex_payload`` artifact produced by
        APEX_CONTAINER_EXTRACTION.

        Eligible protobuf sources are associated to canonical APEX
        requirements by nearest exact common-ancestor specificity across their
        Extraction lineages, constrained to the same canonical runtime.

        No APEX names, parser source names, Android paths, host paths,
        partition names, device facts, or version-specific knowledge are used.

        This remains input semantics for later BuildSection processing only.
        It does not generate namespaces or links and does not resolve ELF
        dependencies.
        """

        if linker_requirement is None:
            if not isinstance(
                apex_requirements,
                tuple,
            ):
                raise TypeError(
                    "apex_requirements must be a tuple"
                )

            if not all(
                isinstance(
                    requirement,
                    AndroidUniverseApexRequirement,
                )
                for requirement
                in apex_requirements
            ):
                raise TypeError(
                    "apex_requirements must contain only "
                    "AndroidUniverseApexRequirement instances"
                )

            return tuple(
                sorted(
                    (
                        AndroidUniverseLinkerApexNamespaceInput(
                            apex_requirement=requirement,
                            matched_runtime_policies=(),
                            apex_local_candidates=(),
                            selected_apex_local_configuration=None,
                            status=(
                                AndroidUniverseLinkerApexNamespaceStatus
                                .UNRESOLVED
                            ),
                        )
                        for requirement
                        in apex_requirements
                    ),
                    key=lambda value: (
                        value.input_id
                    ),
                )
            )

        if not isinstance(
            linker_requirement,
            AndroidUniverseLinkerRequirement,
        ):
            raise TypeError(
                "linker_requirement must be an "
                "AndroidUniverseLinkerRequirement or None"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement
            in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        def artifact_lineage(
            artifact,
        ) -> tuple:
            values = []

            current = artifact

            while current is not None:
                values.append(
                    current
                )
                current = current.parent

            return tuple(
                values
            )

        apex_lineages = tuple(
            (
                requirement,
                artifact_lineage(
                    requirement.artifact
                ),
            )
            for requirement
            in apex_requirements
        )

        #
        # First resolve every APEX-local protobuf semantic to the canonical
        # APEX requirement(s) owning its nearest exact Extraction ancestry.
        #
        protobuf_matches = []

        for runtime_policy in (
            linker_requirement.runtime_policies
        ):
            for semantics in (
                runtime_policy.protobuf_configurations
            ):
                if not semantics.applies_apex_local_policy:
                    continue

                filesystem_source = (
                    semantics.source.source.filesystem_source
                )

                if filesystem_source is None:
                    continue

                filesystem_artifact = (
                    filesystem_source.artifact
                )

                payload = (
                    filesystem_artifact.parent
                )

                #
                # This is the same structural APEX boundary already enforced
                # by Parsing's specialized APEX filesystem-source builder.
                #
                if (
                    payload is None
                    or payload.operation.value
                    != "apex_container_extraction"
                    or payload.semantic_name
                    != "apex_payload"
                ):
                    continue

                protobuf_lineage = artifact_lineage(
                    filesystem_artifact
                )

                scored = []

                for (
                    apex_requirement,
                    apex_lineage,
                ) in apex_lineages:
                    if not (
                        AndroidUniverseRuntimeContextResolver
                        .same_runtime(
                            semantics.runtime_context,
                            apex_requirement.runtime_context,
                        )
                    ):
                        continue

                    common = tuple(
                        (
                            protobuf_index,
                            apex_index,
                        )
                        for (
                            protobuf_index,
                            protobuf_artifact,
                        )
                        in enumerate(
                            protobuf_lineage
                        )
                        for (
                            apex_index,
                            apex_artifact,
                        )
                        in enumerate(
                            apex_lineage
                        )
                        if (
                            protobuf_artifact
                            is apex_artifact
                        )
                    )

                    if not common:
                        continue

                    nearest = min(
                        common,
                        key=lambda item: (
                            item[
                                0
                            ],
                            item[
                                1
                            ],
                        ),
                    )

                    scored.append(
                        (
                            nearest[
                                0
                            ],
                            nearest[
                                1
                            ],
                            apex_requirement,
                        )
                    )

                if not scored:
                    protobuf_matches.append(
                        (
                            semantics,
                            (),
                        )
                    )
                    continue

                best_key = min(
                    (
                        protobuf_index,
                        apex_index,
                    )
                    for (
                        protobuf_index,
                        apex_index,
                        _,
                    )
                    in scored
                )

                best_apex_requirements = tuple(
                    sorted(
                        (
                            apex_requirement
                            for (
                                protobuf_index,
                                apex_index,
                                apex_requirement,
                            )
                            in scored
                            if (
                                protobuf_index,
                                apex_index,
                            )
                            == best_key
                        ),
                        key=lambda requirement: (
                            requirement.requirement_id
                        ),
                    )
                )

                protobuf_matches.append(
                    (
                        semantics,
                        best_apex_requirements,
                    )
                )

        results = []

        for apex_requirement in (
            apex_requirements
        ):
            matching_policies = tuple(
                policy
                for policy
                in linker_requirement.runtime_policies
                if (
                    AndroidUniverseRuntimeContextResolver
                    .same_runtime(
                        policy.runtime_context,
                        apex_requirement.runtime_context,
                    )
                )
            )

            #
            # Runtime ambiguity is preserved as part of this exact APEX
            # input. Local protobuf candidates are still collected below so
            # no provenance evidence is discarded.
            #

            resolved_candidates = []
            ambiguous_candidates = []

            for (
                semantics,
                matched_apex_requirements,
            ) in protobuf_matches:
                if not any(
                    candidate
                    is apex_requirement
                    for candidate
                    in matched_apex_requirements
                ):
                    continue

                if len(
                    matched_apex_requirements
                ) == 1:
                    resolved_candidates.append(
                        semantics
                    )
                else:
                    ambiguous_candidates.append(
                        semantics
                    )

            canonical_resolved = tuple(
                sorted(
                    resolved_candidates,
                    key=lambda semantics: (
                        semantics.source.source.identity_key
                    ),
                )
            )

            canonical_ambiguous = tuple(
                sorted(
                    ambiguous_candidates,
                    key=lambda semantics: (
                        semantics.source.source.identity_key
                    ),
                )
            )

            canonical_candidates = tuple(
                sorted(
                    (
                        *canonical_resolved,
                        *canonical_ambiguous,
                    ),
                    key=lambda semantics: (
                        semantics.source.source.identity_key
                    ),
                )
            )

            if not matching_policies:
                status = (
                    AndroidUniverseLinkerApexNamespaceStatus.UNRESOLVED
                )

                selected = None

            elif len(
                matching_policies
            ) > 1:
                status = (
                    AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
                )

                selected = None

            elif canonical_ambiguous:
                status = (
                    AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
                )

                selected = None

            elif len(
                canonical_resolved
            ) == 1:
                status = (
                    AndroidUniverseLinkerApexNamespaceStatus.PRESENT
                )

                selected = (
                    canonical_resolved[
                        0
                    ]
                )

            elif len(
                canonical_resolved
            ) > 1:
                status = (
                    AndroidUniverseLinkerApexNamespaceStatus.AMBIGUOUS
                )

                selected = None

            else:
                #
                # Absence of an APEX-local linker.config.pb is currently
                # represented by the relationship-status vocabulary as
                # UNRESOLVED/no-local-policy. BuildSection semantics will need
                # to treat that as normal optional absence rather than a
                # reconstruction failure.
                #
                status = (
                    AndroidUniverseLinkerApexNamespaceStatus.ABSENT
                )

                selected = None

            results.append(
                AndroidUniverseLinkerApexNamespaceInput(
                    apex_requirement=(
                        apex_requirement
                    ),
                    matched_runtime_policies=(
                        matching_policies
                    ),
                    apex_local_candidates=(
                        canonical_candidates
                    ),
                    selected_apex_local_configuration=(
                        selected
                    ),
                    status=status,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda value: (
                    value.input_id
                ),
            )
        )

    @staticmethod
    def reconcile_linker_apex(
        *,
        linker_requirement,
        apex_requirements,
    ) -> tuple[
        AndroidUniverseLinkerApexRelationship,
        ...,
    ]:
        """
        Relate each canonical APEX requirement to Linker runtime policy using
        canonical runtime-context identity only.

        This establishes runtime membership and deliberately does not resolve
        native-library providers, consumers, JNI declarations, or ELF
        dependencies.
        """

        if linker_requirement is None:
            return ()

        if not isinstance(
            linker_requirement,
            AndroidUniverseLinkerRequirement,
        ):
            raise TypeError(
                "linker_requirement must be an "
                "AndroidUniverseLinkerRequirement or None"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        relationships = []

        for apex_requirement in apex_requirements:
            matched_runtime_policies = tuple(
                policy
                for policy
                in linker_requirement.runtime_policies
                if (
                    AndroidUniverseRuntimeContextResolver
                    .same_runtime(
                        policy.runtime_context,
                        apex_requirement.runtime_context,
                    )
                )
            )

            if not matched_runtime_policies:
                status = (
                    AndroidUniverseRelationshipStatus.UNRESOLVED
                )

            elif len(
                matched_runtime_policies
            ) == 1:
                status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                )

            else:
                status = (
                    AndroidUniverseRelationshipStatus.AMBIGUOUS
                )

            relationships.append(
                AndroidUniverseLinkerApexRelationship(
                    kind=(
                        AndroidUniverseRelationshipKind
                        .LINKER_APEX
                    ),
                    status=status,
                    apex_requirement=(
                        apex_requirement
                    ),
                    matched_runtime_policies=(
                        matched_runtime_policies
                    ),
                )
            )

        return tuple(
            sorted(
                relationships,
                key=lambda relationship: (
                    relationship.relationship_id
                ),
            )
        )

    @staticmethod
    def reconcile_linker_apex_context_applicability(
        *,
        relationships,
        treble_enabled: bool | None,
    ) -> tuple[
        AndroidUniverseLinkerApexContextApplicability,
        ...,
    ]:
        """
        Select partition-context linker.config.pb semantics applicable to
        each Linker/APEX runtime-membership relationship.

        PRODUCT depends on the canonical Treble conclusion. No native-library
        provider matching occurs here.
        """

        if not isinstance(
            relationships,
            tuple,
        ):
            raise TypeError(
                "relationships must be a tuple"
            )

        if not all(
            isinstance(
                relationship,
                AndroidUniverseLinkerApexRelationship,
            )
            for relationship in relationships
        ):
            raise TypeError(
                "relationships must contain only "
                "AndroidUniverseLinkerApexRelationship instances"
            )

        if (
            treble_enabled is not None
            and not isinstance(
                treble_enabled,
                bool,
            )
        ):
            raise TypeError(
                "treble_enabled must be a bool or None"
            )

        results = []

        for relationship in relationships:
            policy = relationship.runtime_policy
            apex = relationship.apex_requirement

            if policy is None:
                results.append(
                    AndroidUniverseLinkerApexContextApplicability(
                        membership_relationship=relationship,
                        applicable_contexts=(),
                        status=(
                            AndroidUniverseRelationshipStatus.UNRESOLVED
                        ),
                    )
                )
                continue

            partition = (
                apex.deployment_context.partition
            )

            expected_usage = None

            if partition in {
                AndroidUniverseApexDeploymentPartition.SYSTEM,
                AndroidUniverseApexDeploymentPartition.SYSTEM_EXT,
            }:
                expected_usage = (
                    AndroidUniverseLinkerProtobufUsage.SYSTEM_CONTEXT
                )

            elif partition in {
                AndroidUniverseApexDeploymentPartition.VENDOR,
                AndroidUniverseApexDeploymentPartition.ODM,
            }:
                expected_usage = (
                    AndroidUniverseLinkerProtobufUsage.VENDOR_CONTEXT
                )

            elif (
                partition
                is AndroidUniverseApexDeploymentPartition.PRODUCT
            ):
                if treble_enabled is None:
                    results.append(
                        AndroidUniverseLinkerApexContextApplicability(
                            membership_relationship=relationship,
                            applicable_contexts=(),
                            status=(
                                AndroidUniverseRelationshipStatus.UNRESOLVED
                            ),
                        )
                    )
                    continue

                expected_usage = (
                    AndroidUniverseLinkerProtobufUsage.PRODUCT_CONTEXT
                    if treble_enabled
                    else AndroidUniverseLinkerProtobufUsage.SYSTEM_CONTEXT
                )

            else:
                results.append(
                    AndroidUniverseLinkerApexContextApplicability(
                        membership_relationship=relationship,
                        applicable_contexts=(),
                        status=(
                            AndroidUniverseRelationshipStatus.UNRESOLVED
                        ),
                    )
                )
                continue

            applicable = tuple(
                semantics
                for semantics
                in policy.protobuf_configurations
                if semantics.usage is expected_usage
            )

            if applicable:
                status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                )
                selected = applicable
            else:
                status = (
                    AndroidUniverseRelationshipStatus.UNRESOLVED
                )
                selected = ()

            results.append(
                AndroidUniverseLinkerApexContextApplicability(
                    membership_relationship=relationship,
                    applicable_contexts=selected,
                    status=status,
                )
            )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.applicability_id
                ),
            )
        )


    @staticmethod
    def reconcile_linker_apex_native_libraries(
        *,
        context_applicability,
        apex_requirements,
    ) -> tuple[
        AndroidUniverseLinkerApexNativeLibraryConclusion,
        ...,
    ]:
        """
        Reconcile exact APEX requireNativeLibs occurrences against the
        already-established runtime-local provider vocabulary.

        Provider precedence in this slice is:

        1. applicable Linker protobuf context provider
        2. same-runtime APEX manifest provider

        Alias semantics and ELF artifact resolution are intentionally
        deferred. No Reconstruction decisions occur here.
        """

        if not isinstance(
            context_applicability,
            tuple,
        ):
            raise TypeError(
                "context_applicability must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerApexContextApplicability,
            )
            for item in context_applicability
        ):
            raise TypeError(
                "context_applicability must contain only "
                "AndroidUniverseLinkerApexContextApplicability instances"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseApexRequirement,
            )
            for requirement in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        apex_providers_by_consumer = {}

        for consumer in apex_requirements:
            providers = defaultdict(
                list
            )

            for provider_apex in apex_requirements:
                if not (
                    AndroidUniverseRuntimeContextResolver
                    .same_runtime(
                        consumer.runtime_context,
                        provider_apex.runtime_context,
                    )
                ):
                    continue

                for (
                    provider_index,
                    library_name,
                ) in enumerate(
                    provider_apex.provide_native_libs
                ):
                    providers[
                        library_name
                    ].append(
                        AndroidUniverseLinkerApexNativeLibraryApexProvider(
                            apex_requirement=(
                                provider_apex
                            ),
                            provider_index=(
                                provider_index
                            ),
                            library_name=(
                                library_name
                            ),
                        )
                    )

            apex_providers_by_consumer[
                id(
                    consumer
                )
            ] = providers

        conclusions = []

        for applicability in context_applicability:
            apex = (
                applicability
                .membership_relationship
                .apex_requirement
            )

            for (
                requirement_index,
                library_name,
            ) in enumerate(
                apex.require_native_libs
            ):
                context_candidates = tuple(
                    provider
                    for semantics
                    in applicability.applicable_contexts
                    for provider
                    in semantics.provided_libraries
                    if (
                        provider.library_name
                        == library_name
                    )
                )

                apex_candidates = tuple(
                    apex_providers_by_consumer[
                        id(
                            apex
                        )
                    ].get(
                        library_name,
                        (),
                    )
                )

                llndk_candidates = tuple(
                    declaration
                    for configuration
                    in (
                        applicability
                        .membership_relationship
                        .runtime_policy
                        .native_library_configurations
                    )
                    if (
                        apex.deployment_context.partition.value
                        in {
                            "vendor",
                            "odm",
                        }
                        and configuration.policy_kind
                        is AndroidUniverseLinkerNativeLibraryPolicyKind.LLNDK
                    )
                    for declaration
                    in configuration.declarations
                    if (
                        declaration.library_name
                        == library_name
                    )
                ) if (
                    applicability
                    .membership_relationship
                    .runtime_policy
                    is not None
                ) else ()

                alias_candidates = tuple(
                    AndroidUniverseLinkerApexNativeLibraryAliasProvider(
                        alias_name=library_name,
                        text_configuration=configuration,
                        section=section,
                        target_namespace=namespace,
                    )
                    for configuration
                    in (
                        applicability
                        .membership_relationship
                        .runtime_policy
                        .text_configurations
                    )
                    for section
                    in configuration.sections
                    for namespace
                    in section.namespaces
                    if (
                        library_name == ":sphal"
                        and apex.deployment_context.partition.value
                        not in {
                            "vendor",
                            "odm",
                        }
                        and namespace.name == "sphal"
                    )
                ) if (
                    applicability
                    .membership_relationship
                    .runtime_policy
                    is not None
                ) else ()

                selected_context_provider = None
                selected_apex_provider = None
                selected_llndk_provider = None
                selected_alias_provider = None

                if (
                    applicability.status
                    is not AndroidUniverseRelationshipStatus.RESOLVED
                ):
                    status = (
                        AndroidUniverseRelationshipStatus.UNRESOLVED
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .NONE
                    )

                elif len(
                    context_candidates
                ) == 1:
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .CONTEXT
                    )
                    selected_context_provider = (
                        context_candidates[
                            0
                        ]
                    )

                elif len(
                    context_candidates
                ) > 1:
                    status = (
                        AndroidUniverseRelationshipStatus.AMBIGUOUS
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .NONE
                    )

                elif len(
                    apex_candidates
                ) == 1:
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .APEX
                    )
                    selected_apex_provider = (
                        apex_candidates[
                            0
                        ]
                    )

                elif len(
                    apex_candidates
                ) > 1:
                    status = (
                        AndroidUniverseRelationshipStatus.AMBIGUOUS
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .NONE
                    )

                elif len(
                    llndk_candidates
                ) == 1:
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .LLNDK
                    )
                    selected_llndk_provider = (
                        llndk_candidates[
                            0
                        ]
                    )

                elif len(
                    llndk_candidates
                ) > 1:
                    status = (
                        AndroidUniverseRelationshipStatus.AMBIGUOUS
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .NONE
                    )

                elif len(
                    alias_candidates
                ) == 1:
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .ALIAS
                    )
                    selected_alias_provider = (
                        alias_candidates[
                            0
                        ]
                    )

                elif len(
                    alias_candidates
                ) > 1:
                    status = (
                        AndroidUniverseRelationshipStatus.AMBIGUOUS
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .NONE
                    )

                else:
                    status = (
                        AndroidUniverseRelationshipStatus.UNRESOLVED
                    )
                    provider_kind = (
                        AndroidUniverseLinkerApexNativeLibraryProviderKind
                        .NONE
                    )

                conclusions.append(
                    AndroidUniverseLinkerApexNativeLibraryConclusion(
                        context_applicability=(
                            applicability
                        ),
                        requirement_index=(
                            requirement_index
                        ),
                        library_name=(
                            library_name
                        ),
                        context_provider_candidates=(
                            context_candidates
                        ),
                        apex_provider_candidates=(
                            apex_candidates
                        ),
                        llndk_provider_candidates=(
                            llndk_candidates
                        ),
                        alias_provider_candidates=(
                            alias_candidates
                        ),
                        provider_kind=(
                            provider_kind
                        ),
                        selected_context_provider=(
                            selected_context_provider
                        ),
                        selected_apex_provider=(
                            selected_apex_provider
                        ),
                        selected_llndk_provider=(
                            selected_llndk_provider
                        ),
                        selected_alias_provider=(
                            selected_alias_provider
                        ),
                        status=status,
                    )
                )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.conclusion_id
                ),
            )
        )

    def reconcile(
        self,
        *,
        init_services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        init_import_resolutions: tuple[
            AndroidUniverseInitImportResolution,
            ...,
        ],
        init_service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ],
        init_actions: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        property_evidence: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
        runtime_property_requirements: tuple[
            AndroidUniverseRuntimePropertyRequirement,
            ...,
        ],
        vintf_requirements: tuple[
            AndroidUniverseVintfDocumentRequirement,
            ...,
        ],
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
        selinux_graph: AndroidUniverseSelinuxPolicyGraph,
    ) -> tuple[
        AndroidUniverseCrossFamilyRelationship,
        ...,
    ]:
        relationships = []

        runtime_properties_by_key = {
            requirement.property_key: requirement
            for requirement
            in runtime_property_requirements
        }

        property_expression_resolver = (
            AndroidUniverseInitPropertyExpressionResolver(
                runtime_property_requirements
            )
        )

        relationships.extend(
            self._init_service_control_relationships(
                init_services=init_services,
                init_service_resolutions=(
                    init_service_resolutions
                ),
                init_actions=init_actions,
                property_expression_resolver=(
                    property_expression_resolver
                ),
            )
        )

        relationships.extend(
            self._init_onrestart_service_control_relationships(
                init_services=init_services,
                init_service_resolutions=(
                    init_service_resolutions
                ),
                property_expression_resolver=(
                    property_expression_resolver
                ),
            )
        )

        relationships.extend(
            self._init_event_trigger_relationships(
                init_actions=init_actions,
            )
        )

        relationships.extend(
            self._init_property_command_relationships(
                init_actions=init_actions,
                runtime_properties_by_key=(
                    runtime_properties_by_key
                ),
                property_evidence=property_evidence,
            )
        )

        relationships.extend(
            self._init_onrestart_property_command_relationships(
                init_services=init_services,
                runtime_properties_by_key=(
                    runtime_properties_by_key
                ),
                property_evidence=property_evidence,
            )
        )

        relationships.extend(
            self._init_property_trigger_relationships(
                init_actions=init_actions,
                runtime_properties_by_key=(
                    runtime_properties_by_key
                ),
                property_evidence=property_evidence,
            )
        )

        relationships.extend(
            self._init_executable_artifact_relationships(
                init_services=init_services,
                artifact_requirements=(
                    artifact_requirements
                ),
                apex_requirements=(
                    apex_requirements
                ),
            )
        )

        relationships.extend(
            self._init_executable_relationships(
                init_services=init_services,
                selinux_graph=selinux_graph,
            )
        )

        relationships.extend(
            self._init_seclabel_relationships(
                init_services=init_services,
                selinux_graph=selinux_graph,
            )
        )

        relationships.extend(
            self._init_vintf_relationships(
                init_services=init_services,
                vintf_requirements=vintf_requirements,
            )
        )

        relationships.extend(
            self._property_relationships(
                property_evidence=property_evidence,
                selinux_graph=selinux_graph,
            )
        )

        return tuple(
            sorted(
                relationships,
                key=lambda item: (
                    item.kind.value,
                    item.relationship_id,
                ),
            )
        )

    @staticmethod
    def _runtime_context_key(
        runtime_context,
    ):
        """
        Return a process-local exact grouping key for one canonical runtime.

        Persistent identity remains owned by AndroidUniverseRuntimeContext;
        this key is used only to prevent dictionary indexes from merging
        distinct runtime namespaces during one reconciliation run.
        """

        if runtime_context.is_root:
            return (
                "root",
                None,
            )

        partition_container = (
            runtime_context.partition_container
        )

        if partition_container is None:
            raise ValueError(
                "nested runtime context must preserve "
                "partition_container"
            )

        return (
            "nested_partition_set",
            id(
                partition_container
            ),
        )


    @staticmethod
    def _effective_service_indexes(
        *,
        init_service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ],
    ):
        services_by_context_name = {}
        services_by_name_members = defaultdict(list)
        class_members = {}

        for resolution in init_service_resolutions:
            runtime_key = (
                AndroidUniverseCrossFamilyReconciler
                ._runtime_context_key(
                    resolution.runtime_context
                )
            )

            services_by_context_name[
                (
                    runtime_key,
                    resolution.source_context,
                    resolution.name,
                )
            ] = resolution.effective_services

            services_by_name_members[
                (
                    runtime_key,
                    resolution.name,
                )
            ].extend(
                resolution.effective_services
            )

            for service in resolution.effective_services:
                effective_classes = (
                    service.semantics.classes
                    if (
                        service.semantics.classes
                        is not None
                    )
                    else ("default",)
                )

                for class_name in (
                    effective_classes
                ):
                    key = (
                        runtime_key,
                        resolution.source_context,
                        class_name,
                    )

                    class_members.setdefault(
                        key,
                        [],
                    ).append(
                        service
                    )

        services_by_name = {
            key: tuple(
                sorted(
                    services,
                    key=lambda service: (
                        service.requirement_id
                    ),
                )
            )
            for key, services
            in services_by_name_members.items()
        }

        services_by_context_class = {
            key: tuple(
                sorted(
                    services,
                    key=lambda service: (
                        service.requirement_id
                    ),
                )
            )
            for key, services
            in class_members.items()
        }

        return (
            services_by_context_name,
            services_by_name,
            services_by_context_class,
        )


    @staticmethod
    def _init_service_control_relationships(
        *,
        init_services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        init_service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ],
        init_actions: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        property_expression_resolver: (
            AndroidUniverseInitPropertyExpressionResolver
        ),
    ) -> tuple[
        AndroidUniverseInitServiceControlRelationship
        | AndroidUniverseInitClassControlRelationship,
        ...,
    ]:
        del init_services

        control_keywords = {
            "class_start",
            "class_stop",
            "start",
            "stop",
            "restart",
            "exec_start",
            "enable",
        }

        (
            services_by_context_name,
            services_by_name,
            services_by_context_class,
        ) = (
            AndroidUniverseCrossFamilyReconciler
            ._effective_service_indexes(
                init_service_resolutions=(
                    init_service_resolutions
                ),
            )
        )

        relationships = []

        for action in init_actions:
            source_context = (
                android_init_source_context(
                    action.source_path
                )
            )

            runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    action.filesystem_source
                )
            )

            runtime_key = (
                AndroidUniverseCrossFamilyReconciler
                ._runtime_context_key(
                    runtime_context
                )
            )

            for command_requirement in (
                action.command_requirements
            ):
                semantics = (
                    command_requirement.semantics
                )

                if not isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandTargetSemantics,
                ):
                    continue

                control_kind = (
                    semantics.keyword
                )

                if (
                    control_kind
                    not in control_keywords
                ):
                    continue

                target = semantics.target

                expansion = (
                    property_expression_resolver.expand(
                        target
                    )
                )

                if (
                    expansion.status
                    is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
                ):
                    lookup_target = (
                        expansion.expanded_value
                    )
                else:
                    lookup_target = None

                expanded_target = (
                    expansion.expanded_value
                    if (
                        expansion.is_property_expression
                        and expansion.status
                        is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
                    )
                    else None
                )

                if lookup_target is None:
                    matched_services = ()

                elif control_kind.startswith(
                    "class_"
                ):
                    matched_services = (
                        services_by_context_class.get(
                            (
                                runtime_key,
                                source_context,
                                lookup_target,
                            ),
                            (),
                        )
                    )

                else:
                    matched_services = (
                        services_by_context_name.get(
                            (
                                runtime_key,
                                source_context,
                                lookup_target,
                            ),
                            (),
                        )
                    )

                    if not matched_services:
                        matched_services = (
                            services_by_name.get(
                                (
                                    runtime_key,
                                    lookup_target,
                                ),
                                (),
                            )
                        )

                if control_kind.startswith(
                    "class_"
                ):
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                        if matched_services
                        else AndroidUniverseRelationshipStatus.UNRESOLVED
                    )

                elif not matched_services:
                    status = (
                        AndroidUniverseRelationshipStatus.UNRESOLVED
                    )

                elif len(
                    matched_services
                ) == 1:
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                    )

                else:
                    status = (
                        AndroidUniverseRelationshipStatus.AMBIGUOUS
                    )

                relationship_type = (
                    AndroidUniverseInitClassControlRelationship
                    if control_kind.startswith(
                        "class_"
                    )
                    else AndroidUniverseInitServiceControlRelationship
                )

                relationship_kind = (
                    AndroidUniverseRelationshipKind
                    .INIT_CLASS_CONTROL
                    if control_kind.startswith(
                        "class_"
                    )
                    else AndroidUniverseRelationshipKind
                    .INIT_SERVICE_CONTROL
                )

                relationships.append(
                    relationship_type(
                        kind=relationship_kind,
                        status=status,
                        init_action=action,
                        command_requirement=(
                            command_requirement
                        ),
                        control_kind=control_kind,
                        target=target,
                        matched_services=(
                            matched_services
                        ),
                        expanded_target=(
                            expanded_target
                        ),
                    )
                )

        return tuple(
            relationships
        )


    @staticmethod
    def _init_onrestart_service_control_relationships(
        *,
        init_services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        init_service_resolutions: tuple[
            AndroidUniverseInitServiceResolution,
            ...,
        ],
        property_expression_resolver: (
            AndroidUniverseInitPropertyExpressionResolver
        ),
    ) -> tuple[
        AndroidUniverseInitOnRestartServiceControlRelationship
        | AndroidUniverseInitOnRestartClassControlRelationship,
        ...,
    ]:
        (
            services_by_context_name,
            services_by_name,
            services_by_context_class,
        ) = (
            AndroidUniverseCrossFamilyReconciler
            ._effective_service_indexes(
                init_service_resolutions=(
                    init_service_resolutions
                ),
            )
        )

        relationships = []

        for owner in init_services:
            source_context = (
                android_init_source_context(
                    owner.source_path
                )
            )

            runtime_context = (
                AndroidUniverseRuntimeContextResolver
                .resolve_optional_filesystem_source(
                    owner.filesystem_source
                )
            )

            runtime_key = (
                AndroidUniverseCrossFamilyReconciler
                ._runtime_context_key(
                    runtime_context
                )
            )

            for command in (
                owner.semantics.onrestart_commands
            ):
                semantics = command.semantics

                if isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandClassRestartSemantics,
                ):
                    control_kind = (
                        "class_restart"
                    )
                    target = semantics.target

                elif isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandRestartSemantics,
                ):
                    control_kind = "restart"
                    target = semantics.target

                else:
                    continue

                expansion = (
                    property_expression_resolver.expand(
                        target
                    )
                )

                if (
                    expansion.status
                    is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
                ):
                    lookup_target = (
                        expansion.expanded_value
                    )
                else:
                    lookup_target = None

                expanded_target = (
                    expansion.expanded_value
                    if (
                        expansion.is_property_expression
                        and expansion.status
                        is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
                    )
                    else None
                )

                if lookup_target is None:
                    matched_services = ()

                elif control_kind.startswith(
                    "class_"
                ):
                    matched_services = (
                        services_by_context_class.get(
                            (
                                runtime_key,
                                source_context,
                                lookup_target,
                            ),
                            (),
                        )
                    )

                else:
                    matched_services = (
                        services_by_context_name.get(
                            (
                                runtime_key,
                                source_context,
                                lookup_target,
                            ),
                            (),
                        )
                    )

                    if not matched_services:
                        matched_services = (
                            services_by_name.get(
                                (
                                    runtime_key,
                                    lookup_target,
                                ),
                                (),
                            )
                        )

                if control_kind.startswith(
                    "class_"
                ):
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                        if matched_services
                        else AndroidUniverseRelationshipStatus.UNRESOLVED
                    )

                elif not matched_services:
                    status = (
                        AndroidUniverseRelationshipStatus.UNRESOLVED
                    )

                elif len(
                    matched_services
                ) == 1:
                    status = (
                        AndroidUniverseRelationshipStatus.RESOLVED
                    )

                else:
                    status = (
                        AndroidUniverseRelationshipStatus.AMBIGUOUS
                    )

                relationship_type = (
                    AndroidUniverseInitOnRestartClassControlRelationship
                    if control_kind == "class_restart"
                    else AndroidUniverseInitOnRestartServiceControlRelationship
                )

                relationship_kind = (
                    AndroidUniverseRelationshipKind
                    .INIT_CLASS_CONTROL
                    if control_kind == "class_restart"
                    else AndroidUniverseRelationshipKind
                    .INIT_SERVICE_CONTROL
                )

                relationships.append(
                    relationship_type(
                        kind=relationship_kind,
                        status=status,
                        init_service=owner,
                        onrestart_command=command,
                        control_kind=control_kind,
                        target=target,
                        matched_services=(
                            matched_services
                        ),
                        expanded_target=(
                            expanded_target
                        ),
                    )
                )

        return tuple(
            relationships
        )


    @staticmethod
    def _init_event_trigger_relationships(
        *,
        init_actions: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitEventTriggerRelationship,
        ...,
    ]:
        actions_by_event = defaultdict(
            list
        )

        for action in init_actions:
            for clause in (
                action.trigger_semantics.event_clauses
            ):
                actions_by_event[
                    clause.event
                ].append(
                    action
                )

        relationships = []

        for action in init_actions:
            for command_requirement in (
                action.command_requirements
            ):
                semantics = (
                    command_requirement.semantics
                )

                if not isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandScalarSemantics,
                ):
                    continue

                if semantics.keyword != "trigger":
                    continue

                event = semantics.value

                matched_actions = tuple(
                    actions_by_event.get(
                        event,
                        (),
                    )
                )

                relationships.append(
                    AndroidUniverseInitEventTriggerRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .INIT_EVENT_TRIGGER
                        ),
                        status=(
                            AndroidUniverseRelationshipStatus
                            .RESOLVED
                        ),
                        init_action=action,
                        command_requirement=(
                            command_requirement
                        ),
                        event=event,
                        matched_actions=(
                            matched_actions
                        ),
                    )
                )

        return tuple(
            relationships
        )

    @staticmethod
    def _property_evidence_by_key(
        property_evidence,
    ):
        evidence_by_key = defaultdict(
            list
        )

        for item in property_evidence:
            evidence_by_key[
                item.declaration.key
            ].append(
                item
            )

        return evidence_by_key

    @classmethod
    def _init_property_command_relationships(
        cls,
        *,
        init_actions: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        runtime_properties_by_key,
        property_evidence,
    ) -> tuple[
        AndroidUniverseInitPropertyCommandRelationship,
        ...,
    ]:
        evidence_by_key = (
            cls._property_evidence_by_key(
                property_evidence
            )
        )

        relationships = []

        for action in init_actions:
            for command_requirement in (
                action.command_requirements
            ):
                semantics = (
                    command_requirement.semantics
                )

                if not isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandKeyValueSemantics,
                ):
                    continue

                if semantics.keyword not in {
                    "setprop",
                    "wait_for_prop",
                }:
                    continue

                runtime_property = (
                    runtime_properties_by_key.get(
                        semantics.key
                    )
                )

                evidence = tuple(
                    evidence_by_key.get(
                        semantics.key,
                        (),
                    )
                )

                status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                    if runtime_property is not None
                    else AndroidUniverseRelationshipStatus.UNRESOLVED
                )

                relationships.append(
                    AndroidUniverseInitPropertyCommandRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .INIT_PROPERTY_COMMAND
                        ),
                        status=status,
                        init_action=action,
                        command_requirement=(
                            command_requirement
                        ),
                        command_kind=(
                            semantics.keyword
                        ),
                        property_key=(
                            semantics.key
                        ),
                        property_value=(
                            semantics.value
                        ),
                        runtime_property=runtime_property,
                        property_evidence=evidence,
                    )
                )

        return tuple(
            relationships
        )

    @classmethod
    def _init_onrestart_property_command_relationships(
        cls,
        *,
        init_services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        runtime_properties_by_key,
        property_evidence,
    ) -> tuple[
        AndroidUniverseInitOnRestartPropertyCommandRelationship,
        ...,
    ]:
        evidence_by_key = (
            cls._property_evidence_by_key(
                property_evidence
            )
        )

        relationships = []

        for owner in init_services:
            for command in (
                owner.semantics.onrestart_commands
            ):
                semantics = command.semantics

                if not isinstance(
                    semantics,
                    AndroidUniverseInitActionCommandKeyValueSemantics,
                ):
                    continue

                if semantics.keyword != "setprop":
                    continue

                runtime_property = (
                    runtime_properties_by_key.get(
                        semantics.key
                    )
                )

                evidence = tuple(
                    evidence_by_key.get(
                        semantics.key,
                        (),
                    )
                )

                status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                    if runtime_property is not None
                    else AndroidUniverseRelationshipStatus.UNRESOLVED
                )

                relationships.append(
                    AndroidUniverseInitOnRestartPropertyCommandRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .INIT_PROPERTY_COMMAND
                        ),
                        status=status,
                        init_service=owner,
                        onrestart_command=command,
                        property_key=semantics.key,
                        property_value=semantics.value,
                        runtime_property=runtime_property,
                        property_evidence=evidence,
                    )
                )

        return tuple(
            relationships
        )


    @classmethod
    def _init_property_trigger_relationships(
        cls,
        *,
        init_actions: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        runtime_properties_by_key,
        property_evidence,
    ) -> tuple[
        AndroidUniverseInitPropertyTriggerRelationship,
        ...,
    ]:
        evidence_by_key = (
            cls._property_evidence_by_key(
                property_evidence
            )
        )

        relationships = []

        for action in init_actions:
            for clause in (
                action.trigger_semantics.property_clauses
            ):
                runtime_property = (
                    runtime_properties_by_key.get(
                        clause.name
                    )
                )

                evidence = tuple(
                    evidence_by_key.get(
                        clause.name,
                        (),
                    )
                )

                status = (
                    AndroidUniverseRelationshipStatus.RESOLVED
                    if runtime_property is not None
                    else AndroidUniverseRelationshipStatus.UNRESOLVED
                )

                relationships.append(
                    AndroidUniverseInitPropertyTriggerRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .INIT_PROPERTY_TRIGGER
                        ),
                        status=status,
                        init_action=action,
                        property_key=clause.name,
                        property_value=clause.value,
                        runtime_property=runtime_property,
                        property_evidence=evidence,
                    )
                )

        return tuple(
            relationships
        )

    @staticmethod
    def _status(
        types: set[
            str,
        ],
    ) -> tuple[
        AndroidUniverseRelationshipStatus,
        str | None,
    ]:
        if not types:
            return (
                AndroidUniverseRelationshipStatus.UNRESOLVED,
                None,
            )

        if len(types) == 1:
            return (
                AndroidUniverseRelationshipStatus.RESOLVED,
                next(iter(types)),
            )

        return (
            AndroidUniverseRelationshipStatus.AMBIGUOUS,
            None,
        )

    @classmethod
    def _init_executable_artifact_relationships(
        cls,
        *,
        init_services: tuple[
            AndroidUniverseInitServiceRequirement,
            ...,
        ],
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseInitExecutableArtifactRelationship,
        ...,
    ]:
        """
        Resolve INIT executable references against canonical Universe
        artifact requirements.

        Only canonical Android runtime namespace roots contribute ordinary
        executable candidates. Nested guest filesystems remain valid Universe
        artifact evidence but do not implicitly occupy their containing
        Android system's runtime namespace.

        Filesystem Metadata symlink declarations are consumed as canonical
        namespace-alias evidence. Candidate artifacts are then constrained to
        the same canonical INIT runtime/source context as the service
        declaration. Service context comes from ``android_init_source_context``;
        artifact context comes independently from canonical Extraction
        boot-family lineage.

        Ordinary filesystem, init_boot, and vendor_boot namespaces therefore
        never compete without interpreting an Extraction artifact path as an
        INIT declaration path.

        No filesystem traversal or host-path lookup occurs here.
        """

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseApexRequirement,
            )
            for item in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        apex_names_by_container_id = {
            id(
                requirement.artifact
            ): requirement.apex_name
            for requirement
            in apex_requirements
        }

        artifacts_by_android_path = defaultdict(
            list
        )

        for requirement in (
            artifact_requirements.requirements
        ):
            if not artifact_projects_to_android_runtime_namespace(
                requirement=requirement,
                apex_names_by_container_id=(
                    apex_names_by_container_id
                ),
            ):
                continue

            for android_path in (
                artifact_android_namespace_paths(
                    requirement=requirement,
                    apex_names_by_container_id=(
                        apex_names_by_container_id
                    ),
                )
            ):
                artifacts_by_android_path[
                    android_path
                ].append(
                    requirement
                )

        namespace_aliases_by_context = (
            cls._filesystem_namespace_aliases(
                artifact_requirements=(
                    artifact_requirements
                ),
                apex_names_by_container_id=(
                    apex_names_by_container_id
                ),
            )
        )

        relationships = []

        for service in init_services:
            executable = PurePosixPath(
                service.executable
            )

            if not executable.is_absolute():
                executable = (
                    PurePosixPath("/")
                    / executable
                )

            service_source_context = (
                android_init_source_context(
                    service.source_path
                )
            )

            resolved_paths = (
                cls._resolve_namespace_aliases(
                    path=executable,
                    aliases=(
                        namespace_aliases_by_context.get(
                            service_source_context,
                            {},
                        )
                    ),
                )
            )

            matches_by_identity = {}

            for resolved_path in resolved_paths:
                for item in (
                    artifacts_by_android_path.get(
                        resolved_path,
                        (),
                    )
                ):
                    artifact_source_context = (
                        cls._artifact_init_source_context(
                            item.inventory_entry.artifact
                        )
                    )

                    if (
                        artifact_source_context
                        is not service_source_context
                    ):
                        continue

                    matches_by_identity[
                        item.identity_key
                    ] = item

            matched_artifacts = tuple(
                sorted(
                    matches_by_identity.values(),
                    key=lambda item: (
                        item.partition_name or "",
                        item.android_path,
                        item.identity_key,
                    ),
                )
            )

            if not matched_artifacts:
                status = (
                    AndroidUniverseRelationshipStatus
                    .UNRESOLVED
                )

            elif len(
                matched_artifacts
            ) == 1:
                status = (
                    AndroidUniverseRelationshipStatus
                    .RESOLVED
                )

            else:
                status = (
                    AndroidUniverseRelationshipStatus
                    .AMBIGUOUS
                )

            relationships.append(
                AndroidUniverseInitExecutableArtifactRelationship(
                    kind=(
                        AndroidUniverseRelationshipKind
                        .INIT_EXECUTABLE_ARTIFACT
                    ),
                    status=status,
                    init_service=service,
                    executable_path=(
                        executable.as_posix()
                    ),
                    matched_artifacts=(
                        matched_artifacts
                    ),
                )
            )

        return tuple(
            relationships
        )

    @staticmethod
    def _artifact_init_source_context(
        filesystem_artifact,
    ) -> AndroidUniverseInitSourceContext:
        """
        Determine the INIT runtime/source domain represented by one canonical
        filesystem Extraction artifact.

        This is the artifact-side counterpart to
        ``android_init_source_context``. It derives boot-family identity from
        canonical Extraction lineage rather than from workspace path shape.

        The lineage contract is the same one consumed by the parser
        filesystem-source builder:

            CPIO extraction
                -> ramdisk CPIO
                -> ramdisk component
                -> boot-family artifact

        Only init_boot and vendor_boot are distinct INIT source contexts.
        Ordinary partition filesystems, APEX payload filesystems, and any
        other filesystem source remain in the normal FILESYSTEM context.
        """

        if (
            filesystem_artifact.operation
            is not ExtractionOperation.CPIO_EXTRACTION
        ):
            return (
                AndroidUniverseInitSourceContext
                .FILESYSTEM
            )

        ramdisk_cpio = (
            filesystem_artifact.parent
        )

        if ramdisk_cpio is None:
            return (
                AndroidUniverseInitSourceContext
                .FILESYSTEM
            )

        ramdisk_component = (
            ramdisk_cpio.parent
        )

        if ramdisk_component is None:
            return (
                AndroidUniverseInitSourceContext
                .FILESYSTEM
            )

        boot_family = (
            ramdisk_component.parent
        )

        if boot_family is None:
            return (
                AndroidUniverseInitSourceContext
                .FILESYSTEM
            )

        boot_family_name = (
            boot_family.semantic_name
        )

        if boot_family_name == "init_boot":
            return (
                AndroidUniverseInitSourceContext
                .INIT_BOOT
            )

        if boot_family_name == "vendor_boot":
            return (
                AndroidUniverseInitSourceContext
                .VENDOR_BOOT
            )

        return (
            AndroidUniverseInitSourceContext
            .FILESYSTEM
        )

    @classmethod
    def _filesystem_namespace_aliases(
        cls,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        apex_names_by_container_id: dict[
            int,
            str,
        ],
    ) -> dict[
        AndroidUniverseInitSourceContext,
        dict[
            PurePosixPath,
            tuple[
                PurePosixPath,
                ...,
            ],
        ],
    ]:
        """
        Build context-local Android namespace aliases from canonical
        Filesystem Metadata symlink declarations.

        Identical Android-visible paths may have different meanings in the
        ordinary filesystem, init_boot, and vendor_boot runtime domains.
        Alias evidence therefore remains scoped to the canonical source
        context that owns the symlink.

        Symlinks are not promoted into regular-file artifact requirements.
        """

        alias_targets_by_context = defaultdict(
            lambda: defaultdict(set)
        )

        for inventory_entry in (
            artifact_requirements
            .source_inventory
            .entries
        ):
            if not filesystem_projects_to_android_runtime_namespace(
                inventory_entry=inventory_entry,
                apex_names_by_container_id=(
                    apex_names_by_container_id
                ),
            ):
                continue

            source_context = (
                cls._artifact_init_source_context(
                    inventory_entry.artifact
                )
            )

            for metadata_entry in (
                inventory_entry
                .result
                .metadata
                .entries
                .values()
            ):
                if (
                    metadata_entry.entry_type
                    is not FilesystemEntryType.SYMLINK
                ):
                    continue

                target = (
                    metadata_entry.symlink_target
                )

                if not target:
                    continue

                alias_paths = (
                    metadata_android_namespace_paths(
                        inventory_entry=inventory_entry,
                        metadata_path=(
                            metadata_entry.path
                        ),
                        apex_names_by_container_id=(
                            apex_names_by_container_id
                        ),
                    )
                )

                for alias_path in alias_paths:
                    target_path = PurePosixPath(
                        target
                    )

                    if not target_path.is_absolute():
                        target_path = (
                            alias_path.parent
                            / target_path
                        )

                    target_path = (
                        normalize_android_namespace_path(
                            target_path
                        )
                    )

                    alias_targets_by_context[
                        source_context
                    ][
                        alias_path
                    ].add(
                        target_path
                    )

        return {
            source_context: {
                alias: tuple(
                    sorted(
                        targets,
                        key=lambda item: (
                            item.as_posix()
                        ),
                    )
                )
                for alias, targets
                in alias_targets.items()
            }
            for source_context, alias_targets
            in alias_targets_by_context.items()
        }

    @classmethod
    def _resolve_namespace_aliases(
        cls,
        *,
        path: PurePosixPath,
        aliases: dict[
            PurePosixPath,
            tuple[
                PurePosixPath,
                ...,
            ],
        ],
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        """
        Resolve exact and directory-prefix Android namespace aliases.

        Multiple conflicting canonical aliases remain multiple candidate paths.
        Cycles terminate conservatively without inventing a resolution.
        """

        pending = [
            normalize_android_namespace_path(
                path
            )
        ]

        resolved = set()
        visited = set()

        while pending:
            current = pending.pop()

            if current in visited:
                continue

            visited.add(
                current
            )

            matching_aliases = tuple(
                alias
                for alias
                in aliases
                if (
                    current == alias
                    or alias in current.parents
                )
            )

            if not matching_aliases:
                resolved.add(
                    current
                )
                continue

            longest_length = max(
                len(
                    alias.parts
                )
                for alias
                in matching_aliases
            )

            longest_aliases = tuple(
                alias
                for alias
                in matching_aliases
                if len(
                    alias.parts
                ) == longest_length
            )

            expanded = False

            for alias in longest_aliases:
                relative = (
                    PurePosixPath(".")
                    if current == alias
                    else current.relative_to(
                        alias
                    )
                )

                for target in aliases[
                    alias
                ]:
                    candidate = target

                    if (
                        relative
                        != PurePosixPath(".")
                    ):
                        candidate = (
                            candidate
                            / relative
                        )

                    candidate = (
                        normalize_android_namespace_path(
                            candidate
                        )
                    )

                    if candidate not in visited:
                        pending.append(
                            candidate
                        )
                        expanded = True

            if not expanded:
                resolved.add(
                    current
                )

        return tuple(
            sorted(
                resolved,
                key=lambda item: (
                    item.as_posix()
                ),
            )
        )

    def _init_executable_relationships(
        self,
        *,
        init_services,
        selinux_graph,
    ):
        by_selector = defaultdict(
            list
        )

        for requirement in (
            selinux_graph.context_requirements
        ):
            if (
                requirement.kind
                is AndroidUniverseSelinuxContextKind.FILE
            ):
                by_selector[
                    requirement.selector
                ].append(
                    requirement
                )

        results = []

        for service in init_services:
            evidence = tuple(
                by_selector.get(
                    service.executable,
                    (),
                )
            )

            if not evidence:
                continue

            types = {
                item.selinux_type
                for item in evidence
                if item.selinux_type is not None
            }

            status, resolved_type = (
                self._status(
                    types
                )
            )

            results.append(
                AndroidUniverseInitExecutableSelinuxRelationship(
                    kind=(
                        AndroidUniverseRelationshipKind
                        .INIT_EXECUTABLE_SELINUX_FILE_LABEL
                    ),
                    status=status,
                    init_service=service,
                    context_requirements=evidence,
                    resolved_type=resolved_type,
                )
            )

        return tuple(
            results
        )

    def _init_seclabel_relationships(
        self,
        *,
        init_services,
        selinux_graph,
    ):
        type_symbols = {
            symbol.name: symbol
            for symbol in selinux_graph.symbols
            if (
                symbol.kind
                is AndroidUniverseSelinuxSymbolKind.TYPE
            )
        }

        results = []

        for service in init_services:
            seclabel = (
                service.semantics.seclabel
            )

            if seclabel is None:
                continue

            parts = seclabel.split(
                ":"
            )

            if len(parts) < 3:
                continue

            selinux_type = parts[2]

            symbol = type_symbols.get(
                selinux_type
            )

            status = (
                AndroidUniverseRelationshipStatus.RESOLVED
                if symbol is not None
                else AndroidUniverseRelationshipStatus.UNRESOLVED
            )

            results.append(
                AndroidUniverseInitSeclabelSelinuxRelationship(
                    kind=(
                        AndroidUniverseRelationshipKind
                        .INIT_SECLABEL_SELINUX_TYPE
                    ),
                    status=status,
                    init_service=service,
                    seclabel=seclabel,
                    selinux_type=selinux_type,
                    symbol=symbol,
                )
            )

        return tuple(
            results
        )

    @staticmethod
    def _apk_vintf_structural_evidence(
        *,
        package: AndroidUniverseApkPackageRequirement,
        canonical_name: str,
    ) -> tuple[
        AndroidUniverseApkVintfStructuralProviderEvidence,
        ...,
    ]:
        """
        Return exact DEX structural evidence that one canonical APK contains
        a Binder implementation for one canonical VINTF AIDL service.

        Matching is structural:
          VINTF canonical AIDL identity
              -> exact DEX interface descriptor
              -> exact generated $Stub class implementing that interface
              -> one or more concrete direct subclasses of that Stub.

        No filename, package-name, free-form string, or payload-similarity
        heuristic participates.
        """

        if not isinstance(
            package,
            AndroidUniverseApkPackageRequirement,
        ):
            raise TypeError(
                "package must be an "
                "AndroidUniverseApkPackageRequirement"
            )

        if (
            not isinstance(
                canonical_name,
                str,
            )
            or not canonical_name
            or "/" not in canonical_name
        ):
            raise ValueError(
                "canonical_name must be a canonical "
                "VINTF AIDL service identity"
            )

        service_identity = (
            canonical_name.split(
                "/",
                1,
            )[0]
        )

        interface_descriptor = (
            "L"
            + service_identity.replace(
                ".",
                "/",
            )
            + ";"
        )

        stub_descriptor = (
            interface_descriptor[
                :-1
            ]
            + "$Stub;"
        )

        results = []

        for dex in package.source.dex_files:
            interface_types = tuple(
                type_item
                for type_item
                in dex.types
                if (
                    type_item
                    .descriptor
                    .value
                    == interface_descriptor
                )
            )

            if not interface_types:
                continue

            if len(
                interface_types
            ) != 1:
                raise ValueError(
                    "canonical DEX contains multiple type_ids for "
                    "one exact AIDL interface descriptor: "
                    f"{package.requirement_id}:"
                    f"{interface_descriptor}"
                )

            interface_type = (
                interface_types[0]
            )

            stub_classes = tuple(
                class_item
                for class_item
                in dex.classes
                if (
                    class_item
                    .class_type
                    .descriptor
                    .value
                    == stub_descriptor
                    and any(
                        implemented_type
                        is interface_type
                        for implemented_type
                        in class_item.interface_types
                    )
                )
            )

            for stub_class in stub_classes:
                implementations = []

                for implementation_dex in (
                    package.source.dex_files
                ):
                    for implementation_class in (
                        implementation_dex.classes
                    ):
                        superclass = (
                            implementation_class
                            .superclass_type
                        )

                        if superclass is None:
                            continue

                        if (
                            superclass
                            .descriptor
                            .value
                            != stub_descriptor
                        ):
                            continue

                        if (
                            implementation_class.access_flags
                            & (
                                0x0200  # ACC_INTERFACE
                                | 0x0400  # ACC_ABSTRACT
                            )
                        ):
                            continue

                        implementations.append(
                            AndroidUniverseApkVintfImplementationEvidence(
                                dex=implementation_dex,
                                implementation_class=(
                                    implementation_class
                                ),
                            )
                        )

                if not implementations:
                    continue

                results.append(
                    AndroidUniverseApkVintfStructuralProviderEvidence(
                        dex=dex,
                        interface_type=interface_type,
                        stub_class=stub_class,
                        implementations=tuple(
                            sorted(
                                implementations,
                                key=lambda item: (
                                    item.dex.source.member_index,
                                    (
                                        item
                                        .implementation_class
                                        .definition_index
                                    ),
                                    (
                                        item
                                        .implementation_class
                                        .class_type
                                        .descriptor
                                        .value
                                    ),
                                ),
                            )
                        ),
                    )
                )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.dex.source.member_index,
                    item.stub_class.definition_index,
                    (
                        item.stub_class
                        .class_type
                        .descriptor
                        .value
                    ),
                ),
            )
        )

    def reconcile_apk_vintf(
        self,
        *,
        apk_requirement: AndroidUniverseApkRequirement,
        vintf_requirements: tuple[
            AndroidUniverseVintfDocumentRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseApkVintfStructuralProviderRelationship,
        ...,
    ]:
        """
        Reconcile canonical APK DEX structure against canonical AIDL VINTF
        manifest interfaces across both canonical manifest sides.

        One relationship is emitted for each APK candidate containing exact
        structural Binder-provider evidence.

        If exactly one APK package contains qualifying structural evidence for
        the canonical VINTF interface, the relationship is RESOLVED.

        If multiple APK packages independently contain qualifying evidence,
        every candidate relationship is retained as AMBIGUOUS.
        """

        if not isinstance(
            apk_requirement,
            AndroidUniverseApkRequirement,
        ):
            raise TypeError(
                "apk_requirement must be an "
                "AndroidUniverseApkRequirement"
            )

        if not isinstance(
            vintf_requirements,
            tuple,
        ):
            raise TypeError(
                "vintf_requirements must be a tuple"
            )

        by_identity = defaultdict(
            list
        )

        for document in vintf_requirements:
            semantics = document.semantics

            if (
                semantics.kind
                is not AndroidUniverseVintfDocumentKind.MANIFEST
            ):
                continue

            for hal in semantics.hals:
                if (
                    hal.format
                    is not AndroidUniverseVintfHalFormat.AIDL
                ):
                    continue

                for interface in hal.interfaces:
                    if interface.name is None:
                        continue

                    for instance in interface.instances:
                        canonical_name = (
                            f"{hal.name}."
                            f"{interface.name}/"
                            f"{instance}"
                        )

                        by_identity[
                            canonical_name
                        ].append(
                            AndroidUniverseVintfInterfaceEvidence(
                                document=document,
                                hal=hal,
                                interface=interface,
                                instance=instance,
                                canonical_name=canonical_name,
                            )
                        )

                for fqname in hal.fqnames:
                    canonical_name = (
                        fqname
                        if fqname.startswith(
                            hal.name + "."
                        )
                        else (
                            f"{hal.name}."
                            f"{fqname}"
                        )
                    )

                    if "/" not in canonical_name:
                        continue

                    instance = (
                        canonical_name.split(
                            "/",
                            1,
                        )[1]
                    )

                    by_identity[
                        canonical_name
                    ].append(
                        AndroidUniverseVintfInterfaceEvidence(
                            document=document,
                            hal=hal,
                            interface=None,
                            instance=instance,
                            canonical_name=canonical_name,
                        )
                    )

        results = []

        for canonical_name in sorted(
            by_identity
        ):
            candidates = []

            for package in sorted(
                apk_requirement.packages,
                key=lambda item: (
                    item.requirement_id
                ),
            ):
                provider_evidence = (
                    self._apk_vintf_structural_evidence(
                        package=package,
                        canonical_name=canonical_name,
                    )
                )

                if not provider_evidence:
                    continue

                candidates.append(
                    (
                        package,
                        provider_evidence,
                    )
                )

            if not candidates:
                continue

            status = (
                AndroidUniverseRelationshipStatus.RESOLVED
                if len(
                    candidates
                ) == 1
                else AndroidUniverseRelationshipStatus.AMBIGUOUS
            )

            vintf_evidence = tuple(
                sorted(
                    by_identity[
                        canonical_name
                    ],
                    key=lambda item: (
                        item.document.requirement_id,
                        item.instance,
                    ),
                )
            )

            for (
                package,
                provider_evidence,
            ) in candidates:
                results.append(
                    AndroidUniverseApkVintfStructuralProviderRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .APK_VINTF_STRUCTURAL_PROVIDER
                        ),
                        status=status,
                        apk_package=package,
                        canonical_name=canonical_name,
                        provider_evidence=(
                            provider_evidence
                        ),
                        vintf_evidence=(
                            vintf_evidence
                        ),
                    )
                )

        return tuple(
            sorted(
                results,
                key=lambda item: (
                    item.relationship_id
                ),
            )
        )

    def _init_vintf_relationships(
        self,
        *,
        init_services,
        vintf_requirements,
    ):
        by_identity = defaultdict(
            list
        )

        for document in vintf_requirements:
            semantics = document.semantics

            if (
                semantics.kind
                is not AndroidUniverseVintfDocumentKind.MANIFEST
                or semantics.side
                is not AndroidUniverseVintfDocumentSide.DEVICE
            ):
                continue

            for hal in semantics.hals:
                if (
                    hal.format
                    is not AndroidUniverseVintfHalFormat.AIDL
                ):
                    continue

                for interface in hal.interfaces:
                    if interface.name is None:
                        continue

                    for instance in interface.instances:
                        canonical_name = (
                            f"{hal.name}."
                            f"{interface.name}/"
                            f"{instance}"
                        )

                        by_identity[
                            canonical_name
                        ].append(
                            AndroidUniverseVintfInterfaceEvidence(
                                document=document,
                                hal=hal,
                                interface=interface,
                                instance=instance,
                                canonical_name=canonical_name,
                            )
                        )

                for fqname in hal.fqnames:
                    canonical_name = (
                        fqname
                        if fqname.startswith(
                            hal.name + "."
                        )
                        else (
                            f"{hal.name}."
                            f"{fqname}"
                        )
                    )

                    instance = (
                        canonical_name.split(
                            "/",
                            1,
                        )[1]
                        if "/" in canonical_name
                        else ""
                    )

                    by_identity[
                        canonical_name
                    ].append(
                        AndroidUniverseVintfInterfaceEvidence(
                            document=document,
                            hal=hal,
                            interface=None,
                            instance=instance,
                            canonical_name=canonical_name,
                        )
                    )

        results = []

        for service in init_services:
            for interface in service.semantics.interfaces:
                if interface.transport != "aidl":
                    continue

                evidence = tuple(
                    by_identity.get(
                        interface.name,
                        (),
                    )
                )

                if not evidence:
                    continue

                results.append(
                    AndroidUniverseInitInterfaceVintfRelationship(
                        kind=(
                            AndroidUniverseRelationshipKind
                            .INIT_INTERFACE_VINTF_INTERFACE
                        ),
                        status=(
                            AndroidUniverseRelationshipStatus
                            .RESOLVED
                        ),
                        init_service=service,
                        init_interface=interface,
                        canonical_name=interface.name,
                        vintf_evidence=evidence,
                    )
                )

        return tuple(
            results
        )

    def _property_relationships(
        self,
        *,
        property_evidence,
        selinux_graph,
    ):
        evidence_by_key = defaultdict(
            list
        )

        for item in property_evidence:
            evidence_by_key[
                item.declaration.key
            ].append(
                item
            )

        contexts = tuple(
            requirement
            for requirement
            in selinux_graph.context_requirements
            if (
                requirement.kind
                is AndroidUniverseSelinuxContextKind.PROPERTY
            )
        )

        results = []

        for key in sorted(
            evidence_by_key
        ):
            context_evidence, match_kind = (
                resolve_android_property_contexts(
                    property_key=key,
                    requirements=contexts,
                )
            )

            if not context_evidence:
                continue

            types = {
                item.selinux_type
                for item
                in context_evidence
                if item.selinux_type is not None
            }

            status, resolved_type = (
                self._status(
                    types
                )
            )

            results.append(
                AndroidUniversePropertySelinuxRelationship(
                    kind=(
                        AndroidUniverseRelationshipKind
                        .PROPERTY_SELINUX_PROPERTY_LABEL
                    ),
                    status=status,
                    property_key=key,
                    property_evidence=tuple(
                        evidence_by_key[
                            key
                        ]
                    ),
                    context_requirements=context_evidence,
                    match_kind=match_kind,
                    resolved_type=resolved_type,
                )
            )

        return tuple(
            results
        )
