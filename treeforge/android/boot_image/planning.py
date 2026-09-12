from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.boot_image.composition import (
    AndroidBootImageBootImageComposition,
    AndroidBootImageCompositionResult,
)
from treeforge.android.boot_image.models import (
    AndroidBootImageComponentInterpretation,
    AndroidBootImageComponentRole,
    AndroidBootImageDtboContainerInterpretation,
    AndroidBootImageKernelModuleReference,
    AndroidBootImageKernelModuleResolution,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


class AndroidBootImagePlanningDisposition(
    StrEnum
):
    """
    Baseline realization disposition chosen by Boot Image Planning.

    Planning does not select a concrete provider or execute realization.
    """

    PRESERVE_EXACT = "preserve_exact"


class AndroidBootImagePlanningEvidenceDisposition(
    StrEnum
):
    """
    Explicit Planning accounting for canonical Boot Image evidence that does
    not itself require an independent physical realization output.
    """

    COVERED_BY_EXACT_PARENT = (
        "covered_by_exact_parent"
    )

    RETAINED_EVIDENCE = (
        "retained_evidence"
    )

    RETAINED_UNRESOLVED = (
        "retained_unresolved"
    )

    RETAINED_AMBIGUOUS = (
        "retained_ambiguous"
    )

    CONDITIONAL_INACTIVE = (
        "conditional_inactive"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImagePlanningEvidence:
    """
    Explicit no-silent-drop Planning disposition for one canonical or
    Boot Image-composed evidence object.

    ``evidence`` always retains the exact upstream object identity.
    """

    category: str
    evidence: object
    disposition: AndroidBootImagePlanningEvidenceDisposition
    owner: object | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.category,
                str,
            )
            or not self.category
        ):
            raise ValueError(
                "category must be a non-empty string"
            )

        if not isinstance(
            self.disposition,
            AndroidBootImagePlanningEvidenceDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImagePlanningEvidenceDisposition"
            )


class AndroidBootImageConditionalRequirementKind(
    StrEnum
):
    """
    Structural condition that must be handled if a preserved factory-derived
    composition is mutated downstream.
    """

    AVB_REEVALUATION = "avb_reevaluation"

    BOOTLOADER_TRUST_ANCHOR_UPDATE = (
        "bootloader_trust_anchor_update"
    )

    BOOT_SIGNATURE_REGENERATION = (
        "boot_signature_regeneration"
    )

    VENDOR_RAMDISK_TABLE_REGENERATION = (
        "vendor_ramdisk_table_regeneration"
    )


class AndroidBootImageConditionalTrigger(
    StrEnum
):
    """
    Mutation condition that activates a planning requirement.
    """

    IMAGE_CONTENT_CHANGED = (
        "image_content_changed"
    )

    TOP_LEVEL_AVB_SIGNING_IDENTITY_CHANGED = (
        "top_level_avb_signing_identity_changed"
    )

    SIGNED_BOOT_PAYLOAD_CHANGED = (
        "signed_boot_payload_changed"
    )

    VENDOR_RAMDISK_LAYOUT_CHANGED = (
        "vendor_ramdisk_layout_changed"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageComponentPlan:
    """
    Baseline plan for one exact composed boot component.

    Exact factory-derived preservation is always available because the
    canonical Extraction artifact remains present. Structured Parsing
    evidence is recorded separately and must not be confused with a proven
    writer/rebuilder capability.
    """

    component: AndroidBootImageComponentInterpretation

    disposition: AndroidBootImagePlanningDisposition

    structured_evidence_available: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.component,
            AndroidBootImageComponentInterpretation,
        ):
            raise TypeError(
                "component must be an "
                "AndroidBootImageComponentInterpretation"
            )

        if not isinstance(
            self.disposition,
            AndroidBootImagePlanningDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImagePlanningDisposition"
            )

        if (
            self.disposition
            is not
            AndroidBootImagePlanningDisposition
            .PRESERVE_EXACT
        ):
            raise ValueError(
                "initial Boot Image Planning only permits "
                "exact-preservation baseline component plans"
            )

        if not isinstance(
            self.structured_evidence_available,
            bool,
        ):
            raise TypeError(
                "structured_evidence_available must be bool"
            )

        expected_structured = (
            (
                self.component.role
                is AndroidBootImageComponentRole.KERNEL
                and self.component.kernel is not None
            )
            or (
                self.component.role
                is AndroidBootImageComponentRole.RAMDISK
                and self.component.ramdisk is not None
            )
            or (
                self.component.role
                is AndroidBootImageComponentRole.DTB
                and bool(
                    self.component.dtbs
                )
            )
            or (
                self.component.role
                is AndroidBootImageComponentRole.BOOTCONFIG
                and self.component.bootconfig is not None
            )
            or (
                self.component.role
                is
                AndroidBootImageComponentRole
                .VENDOR_RAMDISK_TABLE
                and (
                    self.component.vendor_ramdisk_table
                    is not None
                )
            )
            or (
                self.component.role
                is AndroidBootImageComponentRole.BOOT_SIGNATURE
                and self.component.boot_signature is not None
            )
        )

        if (
            self.structured_evidence_available
            is not expected_structured
        ):
            raise ValueError(
                "structured_evidence_available must exactly "
                "reflect canonical structured associations"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageConditionalRequirement:
    """
    Conditional downstream requirement activated only if exact preserved
    content is changed.

    No concrete tool, key, provider, or output is selected here.
    """

    kind: AndroidBootImageConditionalRequirementKind

    trigger: AndroidBootImageConditionalTrigger

    image: AndroidBootImageBootImageComposition

    component: (
        AndroidBootImageComponentInterpretation
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidBootImageConditionalRequirementKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidBootImageConditionalRequirementKind"
            )

        if not isinstance(
            self.trigger,
            AndroidBootImageConditionalTrigger,
        ):
            raise TypeError(
                "trigger must be an "
                "AndroidBootImageConditionalTrigger"
            )

        if not isinstance(
            self.image,
            AndroidBootImageBootImageComposition,
        ):
            raise TypeError(
                "image must be an "
                "AndroidBootImageBootImageComposition"
            )

        if (
            self.component is not None
            and not isinstance(
                self.component,
                AndroidBootImageComponentInterpretation,
            )
        ):
            raise TypeError(
                "component must be an "
                "AndroidBootImageComponentInterpretation or None"
            )

        if self.component is not None:
            if not any(
                candidate is self.component
                for candidate
                in self.image.components
            ):
                raise ValueError(
                    "conditional planning requirement component "
                    "must belong to the exact composed image"
                )

        if (
            self.kind
            is
            AndroidBootImageConditionalRequirementKind
            .AVB_REEVALUATION
        ):
            if (
                self.trigger
                is not
                AndroidBootImageConditionalTrigger
                .IMAGE_CONTENT_CHANGED
            ):
                raise ValueError(
                    "AVB reevaluation requires the "
                    "image-content-changed trigger"
                )

            if self.component is not None:
                raise ValueError(
                    "AVB reevaluation is image-scoped"
                )

            if not (
                self.image.avb_regions
                or self.image.avb_partition_references
            ):
                raise ValueError(
                    "AVB reevaluation requires canonical AVB "
                    "evidence for the composed image"
                )

        elif (
            self.kind
            is
            AndroidBootImageConditionalRequirementKind
            .BOOTLOADER_TRUST_ANCHOR_UPDATE
        ):
            if (
                self.trigger
                is not
                AndroidBootImageConditionalTrigger
                .TOP_LEVEL_AVB_SIGNING_IDENTITY_CHANGED
            ):
                raise ValueError(
                    "bootloader trust-anchor update requires the "
                    "top-level-AVB-signing-identity-changed trigger"
                )

            if self.component is not None:
                raise ValueError(
                    "bootloader trust-anchor update is image-scoped"
                )

            if not (
                self.image.avb_regions
                or self.image.avb_partition_references
            ):
                raise ValueError(
                    "bootloader trust-anchor update requires "
                    "canonical AVB evidence"
                )

        elif (
            self.kind
            is
            AndroidBootImageConditionalRequirementKind
            .BOOT_SIGNATURE_REGENERATION
        ):
            if (
                self.trigger
                is not
                AndroidBootImageConditionalTrigger
                .SIGNED_BOOT_PAYLOAD_CHANGED
            ):
                raise ValueError(
                    "boot-signature regeneration requires the "
                    "signed-payload-changed trigger"
                )

            if (
                self.component is None
                or self.component.role
                is not
                AndroidBootImageComponentRole.BOOT_SIGNATURE
                or self.component.boot_signature is None
            ):
                raise ValueError(
                    "boot-signature regeneration must retain the "
                    "exact canonical boot-signature component"
                )

        elif (
            self.kind
            is
            AndroidBootImageConditionalRequirementKind
            .VENDOR_RAMDISK_TABLE_REGENERATION
        ):
            if (
                self.trigger
                is not
                AndroidBootImageConditionalTrigger
                .VENDOR_RAMDISK_LAYOUT_CHANGED
            ):
                raise ValueError(
                    "vendor-ramdisk-table regeneration requires "
                    "the ramdisk-layout-changed trigger"
                )

            if (
                self.component is None
                or self.component.role
                is not
                AndroidBootImageComponentRole
                .VENDOR_RAMDISK_TABLE
                or (
                    self.component.vendor_ramdisk_table
                    is None
                )
            ):
                raise ValueError(
                    "vendor-ramdisk-table regeneration must "
                    "retain the exact canonical table component"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageBootImagePlan:
    """
    Target-neutral Planning result for one composed boot-family image.

    The baseline is exact preservation. Conditional requirements make clear
    what must be reconsidered if downstream Realization changes that baseline.
    """

    composition: AndroidBootImageBootImageComposition

    component_plans: tuple[
        AndroidBootImageComponentPlan,
        ...,
    ]

    conditional_requirements: tuple[
        AndroidBootImageConditionalRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.composition,
            AndroidBootImageBootImageComposition,
        ):
            raise TypeError(
                "composition must be an "
                "AndroidBootImageBootImageComposition"
            )

        if not isinstance(
            self.component_plans,
            tuple,
        ):
            raise TypeError(
                "component_plans must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageComponentPlan,
            )
            for value
            in self.component_plans
        ):
            raise TypeError(
                "component_plans contains an invalid plan"
            )

        expected = tuple(
            id(
                value
            )
            for value
            in self.composition.components
        )

        actual = tuple(
            id(
                value.component
            )
            for value
            in self.component_plans
        )

        if actual != expected:
            raise ValueError(
                "Boot Image Planning must conserve every composed "
                "component in exact order and identity"
            )

        if not isinstance(
            self.conditional_requirements,
            tuple,
        ):
            raise TypeError(
                "conditional_requirements must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageConditionalRequirement,
            )
            for value
            in self.conditional_requirements
        ):
            raise TypeError(
                "conditional_requirements contains an invalid "
                "requirement"
            )

        for value in self.conditional_requirements:
            if value.image is not self.composition:
                raise ValueError(
                    "conditional requirement must retain exact "
                    "boot-image Composition identity"
                )

    @property
    def container_kind(
        self,
    ) -> str:
        return self.composition.container_kind

    @property
    def exact_preservation_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self.component_plans
            if (
                value.disposition
                is
                AndroidBootImagePlanningDisposition
                .PRESERVE_EXACT
            )
        )

    @property
    def structured_evidence_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self.component_plans
            if value.structured_evidence_available
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImagePlanningResult:
    """
    First-class Boot Image Planning boundary.

    Planning preserves exact Composition identity and records only
    evidence-backed baseline and conditional realization requirements.
    """

    composition: AndroidBootImageCompositionResult

    boot_images: tuple[
        AndroidBootImageBootImagePlan,
        ...,
    ]

    dtbo_containers: tuple[
        AndroidBootImageDtboContainerInterpretation,
        ...,
    ]

    evidence: tuple[
        AndroidBootImagePlanningEvidence,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.composition,
            AndroidBootImageCompositionResult,
        ):
            raise TypeError(
                "composition must be an "
                "AndroidBootImageCompositionResult"
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
                value,
                AndroidBootImageBootImagePlan,
            )
            for value
            in self.boot_images
        ):
            raise TypeError(
                "boot_images contains an invalid plan"
            )

        expected_images = tuple(
            id(
                value
            )
            for value
            in self.composition.boot_images
        )

        actual_images = tuple(
            id(
                value.composition
            )
            for value
            in self.boot_images
        )

        if actual_images != expected_images:
            raise ValueError(
                "Boot Image Planning must conserve every boot-image "
                "Composition in exact order and identity"
            )

        if not isinstance(
            self.dtbo_containers,
            tuple,
        ):
            raise TypeError(
                "dtbo_containers must be a tuple"
            )

        if tuple(
            id(
                value
            )
            for value
            in self.dtbo_containers
        ) != tuple(
            id(
                value
            )
            for value
            in self.composition.dtbo_containers
        ):
            raise ValueError(
                "Boot Image Planning must conserve global DTBO "
                "containers in exact Composition order and identity"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImagePlanningEvidence,
            )
            for value
            in self.evidence
        ):
            raise TypeError(
                "evidence contains an invalid Planning evidence record"
            )

    @property
    def interpretation(
        self,
    ):
        return self.composition.interpretation

    @property
    def parsing(
        self,
    ) -> AndroidParsingResult:
        return self.composition.parsing

    @property
    def component_plan_count(
        self,
    ) -> int:
        return sum(
            len(
                image.component_plans
            )
            for image
            in self.boot_images
        )

    @property
    def exact_preservation_count(
        self,
    ) -> int:
        return sum(
            image.exact_preservation_count
            for image
            in self.boot_images
        )

    @property
    def conditional_requirement_count(
        self,
    ) -> int:
        return sum(
            len(
                image.conditional_requirements
            )
            for image
            in self.boot_images
        )

    @property
    def evidence_count(
        self,
    ) -> int:
        return len(
            self.evidence
        )

    @property
    def retained_unresolved_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self.evidence
            if (
                value.disposition
                is AndroidBootImagePlanningEvidenceDisposition
                .RETAINED_UNRESOLVED
            )
        )

    @property
    def retained_ambiguous_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self.evidence
            if (
                value.disposition
                is AndroidBootImagePlanningEvidenceDisposition
                .RETAINED_AMBIGUOUS
            )
        )


class AndroidBootImagePlanner:
    """
    Convert accepted Boot Image Composition into a target-neutral realization
    plan.

    This initial planner chooses only the universally safe baseline:
    preserve exact canonical physical components. It additionally records
    evidence-backed requirements that become active if downstream realization
    mutates those components or images.
    """

    @staticmethod
    def _structured_evidence_available(
        component: AndroidBootImageComponentInterpretation,
    ) -> bool:
        return (
            (
                component.role
                is AndroidBootImageComponentRole.KERNEL
                and component.kernel is not None
            )
            or (
                component.role
                is AndroidBootImageComponentRole.RAMDISK
                and component.ramdisk is not None
            )
            or (
                component.role
                is AndroidBootImageComponentRole.DTB
                and bool(
                    component.dtbs
                )
            )
            or (
                component.role
                is AndroidBootImageComponentRole.BOOTCONFIG
                and component.bootconfig is not None
            )
            or (
                component.role
                is
                AndroidBootImageComponentRole
                .VENDOR_RAMDISK_TABLE
                and (
                    component.vendor_ramdisk_table
                    is not None
                )
            )
            or (
                component.role
                is AndroidBootImageComponentRole.BOOT_SIGNATURE
                and component.boot_signature is not None
            )
        )

    @staticmethod
    def _module_references(
        ramdisk,
    ) -> tuple[
        AndroidBootImageKernelModuleReference,
        ...,
    ]:
        values = []

        for entry in ramdisk.kernel_module_load_entries:
            values.extend(
                entry.references
            )

        for entry in ramdisk.kernel_module_dependency_entries:
            values.append(
                entry.module
            )
            values.extend(
                entry.dependencies
            )

        for entry in ramdisk.kernel_module_alias_entries:
            values.append(
                entry.module
            )

        for entry in ramdisk.kernel_module_soft_dependency_entries:
            values.append(
                entry.module
            )
            values.extend(
                entry.pre
            )
            values.extend(
                entry.post
            )

        return tuple(
            values
        )

    @classmethod
    def _build_evidence(
        cls,
        composition: AndroidBootImageCompositionResult,
        boot_images: tuple[
            AndroidBootImageBootImagePlan,
            ...,
        ],
    ) -> tuple[
        AndroidBootImagePlanningEvidence,
        ...,
    ]:
        evidence = []

        # DTBO entries are physically contained by their exact preserved
        # container. Preserve the relationships explicitly without creating
        # redundant physical realization outputs.
        for container in composition.dtbo_containers:
            for entry in container.entries:
                evidence.append(
                    AndroidBootImagePlanningEvidence(
                        category="dtbo_entry",
                        evidence=entry,
                        disposition=(
                            AndroidBootImagePlanningEvidenceDisposition
                            .COVERED_BY_EXACT_PARENT
                        ),
                        owner=container,
                    )
                )

        # Global VBMeta/descriptor semantics remain first-class evidence.
        for vbmeta in composition.avb_vbmeta:
            evidence.append(
                AndroidBootImagePlanningEvidence(
                    category="avb_vbmeta",
                    evidence=vbmeta,
                    disposition=(
                        AndroidBootImagePlanningEvidenceDisposition
                        .RETAINED_EVIDENCE
                    ),
                )
            )

            for descriptor in vbmeta.descriptors:
                evidence.append(
                    AndroidBootImagePlanningEvidence(
                        category="avb_descriptor",
                        evidence=descriptor,
                        disposition=(
                            AndroidBootImagePlanningEvidenceDisposition
                            .RETAINED_EVIDENCE
                        ),
                        owner=vbmeta,
                    )
                )

        # Physical AVB regions remain explicit. Where their bytes live inside
        # another exact artifact they are not separately materialized.
        for region in composition.avb_regions:
            evidence.append(
                AndroidBootImagePlanningEvidence(
                    category="avb_region",
                    evidence=region,
                    disposition=(
                        AndroidBootImagePlanningEvidenceDisposition
                        .COVERED_BY_EXACT_PARENT
                    ),
                    owner=region.artifact.parent,
                )
            )

        for image_plan in boot_images:
            image = image_plan.composition

            for entry in image.vendor_ramdisk_entries:
                evidence.append(
                    AndroidBootImagePlanningEvidence(
                        category="vendor_ramdisk_entry_range",
                        evidence=entry,
                        disposition=(
                            AndroidBootImagePlanningEvidenceDisposition
                            .COVERED_BY_EXACT_PARENT
                        ),
                        owner=entry.ramdisk_component,
                    )
                )

            for reference in image.avb_partition_references:
                evidence.append(
                    AndroidBootImagePlanningEvidence(
                        category="avb_partition_reference",
                        evidence=reference,
                        disposition=(
                            AndroidBootImagePlanningEvidenceDisposition
                            .RETAINED_EVIDENCE
                        ),
                        owner=image,
                    )
                )

            for signed_payload in image.signed_payloads:
                evidence.append(
                    AndroidBootImagePlanningEvidence(
                        category="signed_payload",
                        evidence=signed_payload,
                        disposition=(
                            AndroidBootImagePlanningEvidenceDisposition
                            .RETAINED_EVIDENCE
                        ),
                        owner=image,
                    )
                )

            ramdisk = image.ramdisk

            if ramdisk is not None:
                for entry in ramdisk.cpio_entries:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="ramdisk_cpio_entry",
                            evidence=entry,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .COVERED_BY_EXACT_PARENT
                            ),
                            owner=ramdisk,
                        )
                    )

                for source in ramdisk.canonical_sources:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="ramdisk_canonical_source",
                            evidence=source,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .RETAINED_EVIDENCE
                            ),
                            owner=ramdisk,
                        )
                    )

                for value in ramdisk.init_files:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="ramdisk_init",
                            evidence=value,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .RETAINED_EVIDENCE
                            ),
                            owner=ramdisk,
                        )
                    )

                for value in ramdisk.fstabs:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="ramdisk_fstab",
                            evidence=value,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .RETAINED_EVIDENCE
                            ),
                            owner=ramdisk,
                        )
                    )

                for value in ramdisk.ueventd_files:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="ramdisk_ueventd",
                            evidence=value,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .RETAINED_EVIDENCE
                            ),
                            owner=ramdisk,
                        )
                    )

                for value in ramdisk.kernel_modules:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="kernel_module",
                            evidence=value,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .COVERED_BY_EXACT_PARENT
                            ),
                            owner=ramdisk,
                        )
                    )

                for value in ramdisk.kernel_module_configurations:
                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="kernel_module_configuration",
                            evidence=value,
                            disposition=(
                                AndroidBootImagePlanningEvidenceDisposition
                                .COVERED_BY_EXACT_PARENT
                            ),
                            owner=ramdisk,
                        )
                    )

                relationship_groups = (
                    (
                        "kernel_module_load_entry",
                        ramdisk.kernel_module_load_entries,
                    ),
                    (
                        "kernel_module_dependency_entry",
                        ramdisk.kernel_module_dependency_entries,
                    ),
                    (
                        "kernel_module_alias_entry",
                        ramdisk.kernel_module_alias_entries,
                    ),
                    (
                        "kernel_module_softdep_entry",
                        ramdisk.kernel_module_soft_dependency_entries,
                    ),
                    (
                        "kernel_module_uninterpreted_line",
                        ramdisk.kernel_module_uninterpreted_lines,
                    ),
                )

                for category, values in relationship_groups:
                    for value in values:
                        evidence.append(
                            AndroidBootImagePlanningEvidence(
                                category=category,
                                evidence=value,
                                disposition=(
                                    AndroidBootImagePlanningEvidenceDisposition
                                    .RETAINED_EVIDENCE
                                ),
                                owner=ramdisk,
                            )
                        )

                for reference in cls._module_references(
                    ramdisk
                ):
                    if (
                        reference.resolution
                        is AndroidBootImageKernelModuleResolution
                        .UNRESOLVED
                    ):
                        disposition = (
                            AndroidBootImagePlanningEvidenceDisposition
                            .RETAINED_UNRESOLVED
                        )
                    elif (
                        reference.resolution
                        is AndroidBootImageKernelModuleResolution
                        .AMBIGUOUS
                    ):
                        disposition = (
                            AndroidBootImagePlanningEvidenceDisposition
                            .RETAINED_AMBIGUOUS
                        )
                    else:
                        disposition = (
                            AndroidBootImagePlanningEvidenceDisposition
                            .RETAINED_EVIDENCE
                        )

                    evidence.append(
                        AndroidBootImagePlanningEvidence(
                            category="kernel_module_reference",
                            evidence=reference,
                            disposition=disposition,
                            owner=ramdisk,
                        )
                    )

            for requirement in image_plan.conditional_requirements:
                evidence.append(
                    AndroidBootImagePlanningEvidence(
                        category="conditional_requirement",
                        evidence=requirement,
                        disposition=(
                            AndroidBootImagePlanningEvidenceDisposition
                            .CONDITIONAL_INACTIVE
                        ),
                        owner=image_plan,
                    )
                )

        return tuple(
            evidence
        )

    def _plan_image(
        self,
        image: AndroidBootImageBootImageComposition,
    ) -> AndroidBootImageBootImagePlan:
        component_plans = tuple(
            AndroidBootImageComponentPlan(
                component=component,
                disposition=(
                    AndroidBootImagePlanningDisposition
                    .PRESERVE_EXACT
                ),
                structured_evidence_available=(
                    self._structured_evidence_available(
                        component
                    )
                ),
            )
            for component
            in image.components
        )

        conditional = []

        if (
            image.avb_regions
            or image.avb_partition_references
        ):
            conditional.append(
                AndroidBootImageConditionalRequirement(
                    kind=(
                        AndroidBootImageConditionalRequirementKind
                        .AVB_REEVALUATION
                    ),
                    trigger=(
                        AndroidBootImageConditionalTrigger
                        .IMAGE_CONTENT_CHANGED
                    ),
                    image=image,
                )
            )

            conditional.append(
                AndroidBootImageConditionalRequirement(
                    kind=(
                        AndroidBootImageConditionalRequirementKind
                        .BOOTLOADER_TRUST_ANCHOR_UPDATE
                    ),
                    trigger=(
                        AndroidBootImageConditionalTrigger
                        .TOP_LEVEL_AVB_SIGNING_IDENTITY_CHANGED
                    ),
                    image=image,
                )
            )

        for component in image.components:
            if (
                component.role
                is AndroidBootImageComponentRole.BOOT_SIGNATURE
                and component.boot_signature is not None
            ):
                conditional.append(
                    AndroidBootImageConditionalRequirement(
                        kind=(
                            AndroidBootImageConditionalRequirementKind
                            .BOOT_SIGNATURE_REGENERATION
                        ),
                        trigger=(
                            AndroidBootImageConditionalTrigger
                            .SIGNED_BOOT_PAYLOAD_CHANGED
                        ),
                        image=image,
                        component=component,
                    )
                )

            if (
                component.role
                is
                AndroidBootImageComponentRole
                .VENDOR_RAMDISK_TABLE
                and (
                    component.vendor_ramdisk_table
                    is not None
                )
            ):
                conditional.append(
                    AndroidBootImageConditionalRequirement(
                        kind=(
                            AndroidBootImageConditionalRequirementKind
                            .VENDOR_RAMDISK_TABLE_REGENERATION
                        ),
                        trigger=(
                            AndroidBootImageConditionalTrigger
                            .VENDOR_RAMDISK_LAYOUT_CHANGED
                        ),
                        image=image,
                        component=component,
                    )
                )

        return AndroidBootImageBootImagePlan(
            composition=image,
            component_plans=component_plans,
            conditional_requirements=tuple(
                conditional
            ),
        )

    def build(
        self,
        composition: AndroidBootImageCompositionResult,
    ) -> AndroidBootImagePlanningResult:
        if not isinstance(
            composition,
            AndroidBootImageCompositionResult,
        ):
            raise TypeError(
                "composition must be an "
                "AndroidBootImageCompositionResult"
            )

        boot_images = tuple(
            self._plan_image(
                image
            )
            for image
            in composition.boot_images
        )

        evidence = self._build_evidence(
            composition,
            boot_images,
        )

        result = AndroidBootImagePlanningResult(
            composition=composition,
            boot_images=boot_images,
            dtbo_containers=(
                composition.dtbo_containers
            ),
            evidence=evidence,
        )

        if result.composition is not composition:
            raise RuntimeError(
                "Boot Image Planning must preserve exact "
                "Composition result identity"
            )

        if result.parsing is not composition.parsing:
            raise RuntimeError(
                "Boot Image Planning must preserve exact "
                "AndroidParsingResult identity"
            )

        return result
