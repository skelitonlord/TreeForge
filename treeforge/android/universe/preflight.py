from __future__ import annotations


from treeforge.android.universe.knowledge_application import (
    applied_universe_architecture_knowledge_modules,
    applied_universe_vintf_knowledge_modules,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from treeforge.android.universe.architecture import (
    AndroidUniverseArchitectureReconciler,
)
from treeforge.android.universe.fstab.applicability import (
    AndroidUniverseFstabApplicabilityReconciler,
)
from treeforge.android.universe.init.import_resolution import (
    AndroidUniverseInitImportReconciler,
)
from treeforge.android.universe.capability import (
    AndroidUniverseDeviceCapabilityReconciler,
)

from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.universe.relationships.applicability import (
    reconcile_android_relationship_applicability,
)
from treeforge.android.universe.selinux.conclusion import (
    conclude_selinux_policy,
)
from treeforge.android.universe.vintf.applicability import (
    AndroidUniverseVintfApplicabilityReconciler,
)
from treeforge.core.context.context import (
    Context,
)


class AndroidUniversePreflightStatus(
    StrEnum,
):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniversePreflightOperation:
    step: int
    name: str
    status: AndroidUniversePreflightStatus
    error_type: str | None = None
    message: str | None = None
    dependencies: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniversePreflightReport:
    operations: tuple[
        AndroidUniversePreflightOperation,
        ...,
    ]
    universe: AndroidDeviceUniverse | None = None

    @property
    def passed(
        self,
    ) -> tuple[
        AndroidUniversePreflightOperation,
        ...,
    ]:
        return tuple(
            item
            for item in self.operations
            if (
                item.status
                is AndroidUniversePreflightStatus.PASS
            )
        )

    @property
    def failed(
        self,
    ) -> tuple[
        AndroidUniversePreflightOperation,
        ...,
    ]:
        return tuple(
            item
            for item in self.operations
            if (
                item.status
                is AndroidUniversePreflightStatus.FAIL
            )
        )

    @property
    def skipped(
        self,
    ) -> tuple[
        AndroidUniversePreflightOperation,
        ...,
    ]:
        return tuple(
            item
            for item in self.operations
            if (
                item.status
                is AndroidUniversePreflightStatus.SKIP
            )
        )

    @property
    def is_successful(
        self,
    ) -> bool:
        return not self.failed


class AndroidDeviceUniversePreflightRunner:
    """
    Exercise the production Universe semantic components without
    failing on the first independent runtime invariant.

    This runner owns diagnostic orchestration only. Every semantic
    interpretation/reconciliation operation is delegated to the exact
    production collaborator already owned by AndroidDeviceUniverseStage.

    Failed prerequisites cause dependent operations to be skipped.
    Independent families continue so one preflight exposes as many
    runtime contract failures as possible.
    """

    def __init__(
        self,
        stage,
    ) -> None:
        self.stage = stage
        self._results: dict[
            str,
            object,
        ] = {}
        self._operations: list[
            AndroidUniversePreflightOperation
        ] = []

    def run(
        self,
        context: Context,
    ) -> AndroidUniversePreflightReport:
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
                "Android Device Universe preflight"
            )

        self._results = {}
        self._operations = []

        parsing = context.android_parsing

        # APEX is logically step 16 but must run early because
        # artifact requirements consume its exact semantic identity.
        self._run(
            step=16,
            name="APEX",
            action=lambda: (
                self.stage.apex_interpreter.interpret(
                    parsing.apex
                )
            ),
        )

        self._run(
            step=1,
            name="ELF",
            action=lambda: tuple(
                sorted(
                    self.stage.elf_interpreter.interpret(
                        parsing.elf,
                        filesystem_inventory=(
                            parsing.filesystem_inventory
                        ),
                    ),
                    key=lambda item: (
                        item.source.source.identity_key,
                        item.requirement_id,
                    ),
                )
            ),
        )

        self._run(
            step=2,
            name="kernel",
            action=lambda: (
                self.stage.kernel_interpreter.interpret(
                    parsing.kernels
                )
            ),
        )

        self._run(
            step=3,
            name="DTBO",
            action=lambda: (
                self.stage.dtbo_interpreter.interpret(
                    parsing.dtbo
                )
            ),
        )

        self._run(
            step=4,
            name="DTBO population reconciliation",
            dependencies=("DTBO",),
            action=lambda: (
                self.stage.dtbo_population_reconciler.reconcile(
                    self._results["DTBO"]
                )
            ),
        )

        def interpret_avb_population():
            vbmeta_requirements = (
                self.stage.vbmeta_interpreter.interpret(
                    parsing.vbmeta
                )
            )

            avb_regions = (
                self.stage.avb_region_conservator.conserve(
                    parsing.avb_regions,
                    vbmeta_requirements,
                )
            )

            return (
                vbmeta_requirements,
                avb_regions,
            )

        self._run(
            step=5,
            name="VBMeta / AVB",
            action=interpret_avb_population,
        )

        self._run(
            step=6,
            name="AVB topology reconciliation",
            dependencies=("VBMeta / AVB",),
            action=lambda: (
                self.stage.avb_topology_reconciler.reconcile(
                    self._results[
                        "VBMeta / AVB"
                    ][0]
                )
            ),
        )

        self._run(
            step=7,
            name="Bootloader",
            action=lambda: (
                self.stage.bootloader_interpreter.interpret(
                    parsing.bootloader
                )
            ),
        )

        self._run(
            step=8,
            name="SFLB",
            action=lambda: (
                self.stage.sflb_interpreter.interpret(
                    parsing.sflb
                )
            ),
        )

        self._run(
            step=9,
            name="BMP",
            action=lambda: (
                self.stage.bmp_interpreter.interpret(
                    parsing.bmp
                )
            ),
        )

        self._run(
            step=10,
            name="artifact requirements",
            dependencies=("APEX",),
            action=lambda: (
                self.stage.artifact_requirement_builder.build(
                    parsing.filesystem_inventory,
                    parsing_source_inventory=(
                        parsing.source_inventory
                    ),
                    apex_requirements=(
                        self._results["APEX"]
                    ),
                )
            ),
        )

        self._run(
            step=11,
            name="properties",
            action=lambda: tuple(
                sorted(
                    self.stage.property_interpreter.interpret(
                        parsing=parsing.filesystem,
                        source_inventory=(
                            parsing.source_inventory
                        ),
                    ),
                    key=lambda item: (
                        item.model_source.source_name,
                        item.model_source.android_path.as_posix(),
                        item.declaration.line_number,
                        item.fact.fact,
                        item.fact.property_key,
                        item.fact.value,
                    ),
                )
            ),
        )

        self._run(
            step=12,
            name="property reconciliation",
            dependencies=("properties",),
            action=lambda: (
                self.stage.property_reconciler.reconcile(
                    self._results["properties"]
                )
            ),
        )

        self._run(
            step=13,
            name="fstab",
            action=lambda: tuple(
                sorted(
                    self.stage.fstab_interpreter.interpret(
                        parsing.filesystem.fstabs
                    ),
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
            ),
        )

        self._run(
            step=14,
            name="ueventd",
            action=lambda: tuple(
                sorted(
                    self.stage.ueventd_interpreter.interpret(
                        parsing.filesystem.ueventd_files
                    ),
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
            ),
        )

        self._run(
            step=15,
            name="boot",
            action=lambda: (
                self.stage.boot_interpreter.interpret(
                    parsing.boot_images
                )
            ),
        )

        self._run(
            step=17,
            name="VINTF",
            action=lambda: tuple(
                sorted(
                    self.stage.vintf_interpreter.interpret(
                        parsing.filesystem.vintf_documents
                    ),
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
            ),
        )

        self._run(
            step=18,
            name="SELinux",
            action=lambda: tuple(
                sorted(
                    self.stage.selinux_interpreter.interpret(
                        parsing.filesystem.selinux_sources
                    ),
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
            ),
        )

        self._run(
            step=19,
            name="SELinux reconciliation",
            dependencies=("SELinux",),
            action=lambda: (
                self.stage.selinux_reconciler.reconcile(
                    self._results["SELinux"]
                )
            ),
        )

        self._run(
            step=20,
            name="SELinux conclusions",
            dependencies=("SELinux reconciliation",),
            action=lambda: (
                conclude_selinux_policy(
                    self._results[
                        "SELinux reconciliation"
                    ]
                )
            ),
        )

        self._run(
            step=21,
            name="init imports",
            action=lambda: tuple(
                sorted(
                    self.stage.init_import_interpreter.interpret(
                        parsing.filesystem.init_files
                    ),
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
            ),
        )

        self._run(
            step=22,
            name="init services",
            action=lambda: tuple(
                sorted(
                    self.stage.init_service_interpreter.interpret(
                        parsing.filesystem.init_files
                    ),
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
            ),
        )

        self._run(
            step=23,
            name="init actions",
            action=lambda: tuple(
                sorted(
                    self.stage.init_action_interpreter.interpret(
                        parsing.filesystem.init_files
                    ),
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
            ),
        )

        self._run(
            step=24,
            name="init reconciliation",
            dependencies=(
                "init imports",
                "init services",
                "init actions",
                "SELinux reconciliation",
            ),
            action=lambda: self._build_init_reconciliation(
                context
            ),
        )

        self._run(
            step=25,
            name="cross-family relationships",
            dependencies=(
                "properties",
                "VINTF",
                "SELinux reconciliation",
                "init services",
                "init actions",
                "init reconciliation",
                "artifact requirements",
                "APEX",
            ),
            action=lambda: self._build_cross_family(
                context
            ),
        )

        self._run(
            step=26,
            name="init service substantiation",
            dependencies=(
                "init services",
                "cross-family relationships",
            ),
            action=lambda: (
                self.stage
                .init_service_substantiation_reconciler
                .reconcile(
                    services=(
                        self._results["init services"]
                    ),
                    relationships=(
                        self._results[
                            "cross-family relationships"
                        ]["relationships"]
                    ),
                    source_inventory=(
                        parsing.source_inventory
                    ),
                )
            ),
        )

        self._run(
            step=27,
            name="init service target substantiation",
            dependencies=(
                "init reconciliation",
                "cross-family relationships",
                "SELinux reconciliation",
            ),
            action=lambda: (
                self.stage
                .init_service_target_substantiation_reconciler
                .reconcile(
                    relationships=(
                        self._results[
                            "cross-family relationships"
                        ]["relationships"]
                    ),
                    relationship_applicability=(
                        self._results[
                            "cross-family relationships"
                        ]["applicability"]
                    ),
                    init_service_resolutions=(
                        self._results[
                            "init reconciliation"
                        ]["service_resolutions"]
                    ),
                    selinux_policy_graph=(
                        self._results[
                            "SELinux reconciliation"
                        ]
                    ),
                )
            ),
        )

        self._run(
            step=28,
            name="fstab applicability",
            dependencies=(
                "fstab",
                "init actions",
            ),
            action=lambda: tuple(
                sorted(
                    self.stage
                    .fstab_applicability_interpreter
                    .interpret(
                        parsing=parsing.filesystem,
                        requirements=(
                            self._results["fstab"]
                        ),
                        init_action_requirements=(
                            self._results["init actions"]
                        ),
                    ),
                    key=lambda item: (
                        item.requirement_id,
                        item.resolved_path or "",
                        item.selector_key or "",
                        item.selector_value or "",
                    ),
                )
            ),
        )

        self._run(
            step=29,
            name="fstab applicability reconciliation",
            dependencies=(
                "fstab",
                "fstab applicability",
            ),
            action=lambda: (
                self.stage
                .fstab_applicability_reconciler
                .reconcile(
                    requirements=(
                        self._results["fstab"]
                    ),
                    observations=(
                        self._results[
                            "fstab applicability"
                        ]
                    ),
                )
            ),
        )

        self._run(
            step=30,
            name="architecture",
            dependencies=("properties",),
            action=lambda: (
                AndroidUniverseArchitectureReconciler()
                .reconcile(
                    property_evidence=(
                        self._results["properties"]
                    ),
                    knowledge_modules=(
                        self._architecture_knowledge_modules(
                            context
                        )
                    ),
                )
            ),
        )

        self._run(
            step=31,
            name="Aconfig",
            action=lambda: (
                self.stage.aconfig_interpreter.interpret(
                    parsing.aconfig
                )
            ),
        )

        self._run(
            step=32,
            name="APK",
            dependencies=(
                "artifact requirements",
            ),
            action=lambda: (
                self.stage.apk_interpreter.interpret(
                    parsing.apk,
                    artifact_requirements=(
                        self._results[
                            "artifact requirements"
                        ]
                    ),
                )
            ),
        )

        self._run(
            step=33,
            name="APK VINTF structural relationships",
            dependencies=(
                "APK",
                "VINTF",
                "init reconciliation",
            ),
            action=(
                self._build_apk_vintf_structural_relationships
            ),
        )

        self._run(
            step=34,
            name="Classpath",
            dependencies=(
                "property reconciliation",
                "APEX",
                "artifact requirements",
            ),
            action=lambda: (
                self.stage.classpath_interpreter.interpret(
                    parsing.classpath,
                    property_conclusions=(
                        self._results[
                            "property reconciliation"
                        ]
                    ),
                    apex_requirements=(
                        self._results[
                            "APEX"
                        ]
                    ),
                    artifact_requirements=(
                        self._results[
                            "artifact requirements"
                        ]
                    ),
                )
            ),
        )

        self._run(
            step=35,
            name="ART Runtime",
            action=lambda: (
                self.stage.art_runtime_interpreter.interpret(
                    parsing.art_runtime
                )
            ),
        )

        self._run(
            step=36,
            name="Kernel Modules",
            action=lambda: (
                self.stage.kernel_module_interpreter.interpret(
                    parsing.kernel_modules,
                    parsing.kernel_module_configurations,
                )
            ),
        )

        self._run(
            step=37,
            name="Linker",
            action=lambda: (
                self.stage.linker_interpreter.interpret(
                    parsing.linker_configurations,
                    parsing.linker_protobuf_configurations,
                    parsing.native_library_configurations,
                )
            ),
        )

        self._run(
            step=38,
            name="canonical Universe assembly",
            dependencies=(
                "ELF",
                "kernel",
                "DTBO",
                "DTBO population reconciliation",
                "VBMeta / AVB",
                "AVB topology reconciliation",
                "Bootloader",
                "SFLB",
                "BMP",
                "artifact requirements",
                "properties",
                "property reconciliation",
                "fstab",
                "ueventd",
                "boot",
                "APEX",
                "VINTF",
                "SELinux",
                "SELinux reconciliation",
                "SELinux conclusions",
                "init imports",
                "init services",
                "init actions",
                "init reconciliation",
                "cross-family relationships",
                "init service substantiation",
                "init service target substantiation",
                "fstab applicability",
                "fstab applicability reconciliation",
                "architecture",
                "Aconfig",
                "APK",
                "APK VINTF structural relationships",
                "Classpath",
                "ART Runtime",
                "Kernel Modules",
                "Linker",
            ),
            action=lambda: self._assemble_universe(
                context
            ),
        )

        universe = self._results.get(
            "canonical Universe assembly"
        )

        if (
            universe is not None
            and not isinstance(
                universe,
                AndroidDeviceUniverse,
            )
        ):
            raise TypeError(
                "canonical Universe assembly result must be "
                "an AndroidDeviceUniverse"
            )

        if universe is not None:
            context.android_device_universe = universe

        return AndroidUniversePreflightReport(
            operations=tuple(
                sorted(
                    self._operations,
                    key=lambda item: (
                        item.step,
                        item.name,
                    ),
                )
            ),
            universe=universe,
        )

    def _run(
        self,
        *,
        step: int,
        name: str,
        action: Callable[[], object],
        dependencies: tuple[str, ...] = (),
    ) -> None:
        missing = tuple(
            dependency
            for dependency in dependencies
            if dependency not in self._results
        )

        if missing:
            self._operations.append(
                AndroidUniversePreflightOperation(
                    step=step,
                    name=name,
                    status=(
                        AndroidUniversePreflightStatus.SKIP
                    ),
                    message=(
                        "dependency failed or was skipped: "
                        + ", ".join(missing)
                    ),
                    dependencies=dependencies,
                )
            )
            return

        try:
            result = action()
        except Exception as error:
            self._operations.append(
                AndroidUniversePreflightOperation(
                    step=step,
                    name=name,
                    status=(
                        AndroidUniversePreflightStatus.FAIL
                    ),
                    error_type=type(error).__name__,
                    message=str(error),
                    dependencies=dependencies,
                )
            )
            return

        self._results[name] = result

        self._operations.append(
            AndroidUniversePreflightOperation(
                step=step,
                name=name,
                status=AndroidUniversePreflightStatus.PASS,
                dependencies=dependencies,
            )
        )

    def _build_init_reconciliation(
        self,
        context: Context,
    ) -> dict[str, object]:
        parsing = context.android_parsing

        runtime_properties = (
            self.stage.runtime_property_builder.build(
                parsing=parsing.filesystem,
                source_inventory=parsing.source_inventory,
                init_services=(
                    self._results["init services"]
                ),
                init_actions=(
                    self._results["init actions"]
                ),
                boot_requirements=(
                    self._results["boot"]
                ),
                selinux_graph=(
                    self._results[
                        "SELinux reconciliation"
                    ]
                ),
            )
        )

        import_resolutions = (
            AndroidUniverseInitImportReconciler()
            .reconcile(
                requirements=(
                    self._results["init imports"]
                ),
                sources=(
                    parsing.filesystem.init_files
                ),
                runtime_properties=runtime_properties,
            )
        )

        service_resolutions = (
            self.stage
            .init_service_reconciler
            .reconcile(
                self._results["init services"],
                import_resolutions=import_resolutions,
            )
        )

        return {
            "runtime_properties": runtime_properties,
            "import_resolutions": import_resolutions,
            "service_resolutions": service_resolutions,
        }

    def _build_cross_family(
        self,
        context: Context,
    ) -> dict[str, object]:
        init_state = (
            self._results["init reconciliation"]
        )

        vintf_applicability = (
            AndroidUniverseVintfApplicabilityReconciler()
            .reconcile(
                requirements=(
                    self._results["VINTF"]
                ),
                knowledge_modules=(
                    self._vintf_knowledge_modules(
                        context
                    )
                ),
            )
        )

        relationships = (
            self.stage.cross_family_reconciler.reconcile(
                init_services=(
                    self._results["init services"]
                ),
                init_import_resolutions=(
                    init_state["import_resolutions"]
                ),
                init_service_resolutions=(
                    init_state["service_resolutions"]
                ),
                init_actions=(
                    self._results["init actions"]
                ),
                property_evidence=(
                    self._results["properties"]
                ),
                runtime_property_requirements=(
                    init_state["runtime_properties"]
                ),
                vintf_requirements=(
                    self._results["VINTF"]
                ),
                artifact_requirements=(
                    self._results[
                        "artifact requirements"
                    ]
                ),
                apex_requirements=(
                    self._results["APEX"]
                ),
                selinux_graph=(
                    self._results[
                        "SELinux reconciliation"
                    ]
                ),
            )
        )

        applicability = (
            reconcile_android_relationship_applicability(
                relationships=relationships,
                init_import_resolutions=(
                    init_state["import_resolutions"]
                ),
                init_service_resolutions=(
                    init_state["service_resolutions"]
                ),
            )
        )

        return {
            "vintf_applicability": (
                vintf_applicability
            ),
            "relationships": relationships,
            "applicability": applicability,
        }

    def _build_apk_vintf_structural_relationships(
        self,
    ) -> dict[str, object]:
        """
        Exercise the production generic APK/VINTF structural-provider
        reconciliation after the APK Universe family exists.

        Preflight owns orchestration only. Structural matching remains owned
        by AndroidUniverseCrossFamilyReconciler.
        """

        init_state = (
            self._results["init reconciliation"]
        )

        relationships = (
            self.stage.cross_family_reconciler
            .reconcile_apk_vintf(
                apk_requirement=(
                    self._results["APK"]
                ),
                vintf_requirements=(
                    self._results["VINTF"]
                ),
            )
        )

        applicability = (
            reconcile_android_relationship_applicability(
                relationships=relationships,
                init_import_resolutions=(
                    init_state[
                        "import_resolutions"
                    ]
                ),
                init_service_resolutions=(
                    init_state[
                        "service_resolutions"
                    ]
                ),
            )
        )

        return {
            "relationships": relationships,
            "applicability": applicability,
        }

    def _assemble_universe(
        self,
        context: Context,
    ) -> AndroidDeviceUniverse:
        init_state = (
            self._results["init reconciliation"]
        )
        cross_family = (
            self._results[
                "cross-family relationships"
            ]
        )

        apk_vintf = (
            self._results[
                "APK VINTF structural relationships"
            ]
        )

        relationships = tuple(
            sorted(
                (
                    *cross_family[
                        "relationships"
                    ],
                    *apk_vintf[
                        "relationships"
                    ],
                ),
                key=lambda item: (
                    item.kind.value,
                    item.relationship_id,
                ),
            )
        )

        relationship_applicability = tuple(
            sorted(
                (
                    *cross_family[
                        "applicability"
                    ],
                    *apk_vintf[
                        "applicability"
                    ],
                ),
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )

        first_stage_kernel_module_relationships = (
            self.stage.cross_family_reconciler
            .reconcile_first_stage_kernel_module_loading(
                boot_requirements=(
                    self._results["boot"]
                ),
                kernel_module_requirement=(
                    self._results["Kernel Modules"]
                ),
            )
        )

        if first_stage_kernel_module_relationships:
            relationships = tuple(
                sorted(
                    (
                        *relationships,
                        *first_stage_kernel_module_relationships,
                    ),
                    key=lambda item: (
                        item.kind.value,
                        item.relationship_id,
                    ),
                )
            )

            relationship_applicability = tuple(
                sorted(
                    (
                        *relationship_applicability,
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

        relationships_by_id = {}
        for relationship in relationships:
            relationships_by_id.setdefault(
                relationship.relationship_id,
                [],
            ).append(
                relationship
            )

        duplicate_relationships = {
            relationship_id: items
            for relationship_id, items
            in relationships_by_id.items()
            if len(items) > 1
        }

        if duplicate_relationships:
            details = []
            for relationship_id in sorted(
                duplicate_relationships
            ):
                items = duplicate_relationships[
                    relationship_id
                ]
                details.append(
                    f"{relationship_id} => "
                    + ", ".join(
                        type(item).__name__
                        for item in items
                    )
                )

            raise ValueError(
                "duplicate cross-family relationship "
                "identities before universe assembly: "
                + " | ".join(details)
            )

        return AndroidDeviceUniverse(
            parsing=context.android_parsing,
            knowledge_resolution=(
                context.knowledge_resolution
            ),
            artifact_requirements=(
                self._results["artifact requirements"]
            ),
            property_evidence=(
                self._results["properties"]
            ),
            architecture=(
                self._results["architecture"]
            ),
            runtime_property_requirements=(
                init_state["runtime_properties"]
            ),
            conclusions=(
                self._results[
                    "property reconciliation"
                ]
            ),
            fstab_requirements=(
                self._results["fstab"]
            ),
            ueventd_requirements=(
                self._results["ueventd"]
            ),
            vintf_requirements=(
                self._results["VINTF"]
            ),
            vintf_applicability=(
                cross_family[
                    "vintf_applicability"
                ]
            ),
            device_capabilities=(
                AndroidUniverseDeviceCapabilityReconciler()
                .reconcile(
                    requirements=(
                        self._results["VINTF"]
                    ),
                    applicability=(
                        cross_family[
                            "vintf_applicability"
                        ]
                    ),
                )
            ),
            selinux_requirements=(
                self._results["SELinux"]
            ),
            selinux_policy_graph=(
                self._results[
                    "SELinux reconciliation"
                ]
            ),
            selinux_conclusions=(
                self._results[
                    "SELinux conclusions"
                ]
            ),
            cross_family_relationships=(
                relationships
            ),
            cross_family_relationship_applicability=(
                relationship_applicability
            ),
            init_service_substantiations=(
                self._results[
                    "init service substantiation"
                ]
            ),
            init_service_target_substantiations=(
                self._results[
                    "init service target substantiation"
                ]
            ),
            boot_requirements=(
                self._results["boot"]
            ),
            apex_requirements=(
                self._results["APEX"]
            ),
            elf_requirements=(
                self._results["ELF"]
            ),
            kernel_requirements=(
                self._results["kernel"]
            ),
            aconfig_requirement=(
                self._results["Aconfig"]
            ),
            apk_requirement=(
                self._results["APK"]
            ),
            classpath_requirement=(
                self._results["Classpath"]
            ),
            art_runtime_requirement=(
                self._results["ART Runtime"]
            ),
            kernel_module_requirement=(
                self._results["Kernel Modules"]
            ),
            linker_requirement=(
                self._results["Linker"]
            ),
            dtbo_requirements=(
                self._results["DTBO"]
            ),
            dtbo_population=(
                self._results[
                    "DTBO population reconciliation"
                ]
            ),
            vbmeta_requirements=(
                self._results[
                    "VBMeta / AVB"
                ][0]
            ),
            avb_regions=(
                self._results[
                    "VBMeta / AVB"
                ][1]
            ),
            avb_topology=(
                self._results[
                    "AVB topology reconciliation"
                ]
            ),
            bootloader_requirements=(
                self._results["Bootloader"]
            ),
            sflb_requirements=(
                self._results["SFLB"]
            ),
            bmp_requirements=(
                self._results["BMP"]
            ),
            init_import_requirements=(
                self._results["init imports"]
            ),
            init_import_resolutions=(
                init_state["import_resolutions"]
            ),
            init_service_requirements=(
                self._results["init services"]
            ),
            init_service_resolutions=(
                init_state["service_resolutions"]
            ),
            init_action_requirements=(
                self._results["init actions"]
            ),
            fstab_applicability=(
                self._results[
                    "fstab applicability"
                ]
            ),
            fstab_applicability_conclusions=(
                self._results[
                    "fstab applicability reconciliation"
                ]
            ),
        )

    @staticmethod
    def _vintf_knowledge_modules(
        context: Context,
    ) -> tuple:
        return (
            applied_universe_vintf_knowledge_modules(
                context
            )
        )

    @staticmethod
    def _architecture_knowledge_modules(
        context: Context,
    ) -> tuple:
        return (
            applied_universe_architecture_knowledge_modules(
                context
            )
        )
