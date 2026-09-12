from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.composition.index import (
    AndroidReconstructionCompositionIndex,
)
from treeforge.android.reconstruction.composition.model import (
    AndroidReconstructionCompositionEndpoint,
    AndroidReconstructionCompositionEndpointKind,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexProviderStatus,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseArtifactFulfillmentStatus,
    AndroidUniverseArtRuntimeClasspathRelationship,
    AndroidUniverseFirstStageKernelModuleLoadingRelationship,
    AndroidUniverseLinkerApexRelationship,
    AndroidUniverseInitClassControlRelationship,
    AndroidUniverseInitEventTriggerRelationship,
    AndroidUniverseInitExecutableArtifactRelationship,
    AndroidUniverseInitExecutableSelinuxRelationship,
    AndroidUniverseInitInterfaceVintfRelationship,
    AndroidUniverseApkVintfStructuralProviderRelationship,
    AndroidUniverseInitOnRestartClassControlRelationship,
    AndroidUniverseInitOnRestartPropertyCommandRelationship,
    AndroidUniverseInitOnRestartServiceControlRelationship,
    AndroidUniverseInitPropertyCommandRelationship,
    AndroidUniverseInitPropertyTriggerRelationship,
    AndroidUniverseInitSeclabelSelinuxRelationship,
    AndroidUniverseInitServiceControlRelationship,
    AndroidUniversePropertySelinuxRelationship,
)

from treeforge.android.universe.relationships.service_substantiation import (
    AndroidUniverseInitServiceTargetClassification,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionCompositionRelationship:
    """
    Projection of one exact canonical Universe relationship into
    Reconstruction composition endpoints.

    Universe remains authoritative for relationship kind, resolution status,
    applicability, matched targets, and semantic interpretation.
    """

    relationship_id: str
    relationship: object
    applicability: AndroidUniverseRequirementApplicability

    source: AndroidReconstructionCompositionEndpoint

    targets: tuple[
        AndroidReconstructionCompositionEndpoint,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.relationship_id,
                str,
            )
            or not self.relationship_id
        ):
            raise ValueError(
                "relationship_id must be a non-empty string"
            )

        canonical_relationship_id = getattr(
            self.relationship,
            "relationship_id",
            None,
        )

        if (
            canonical_relationship_id
            != self.relationship_id
        ):
            raise ValueError(
                "relationship_id must preserve canonical "
                "Universe relationship identity"
            )

        if not isinstance(
            self.applicability,
            AndroidUniverseRequirementApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidUniverseRequirementApplicability"
            )

        if (
            self.applicability.requirement_id
            != self.relationship_id
        ):
            raise ValueError(
                "relationship applicability must match "
                "relationship identity"
            )

        if not isinstance(
            self.source,
            AndroidReconstructionCompositionEndpoint,
        ):
            raise TypeError(
                "source must be an "
                "AndroidReconstructionCompositionEndpoint"
            )

        if not isinstance(
            self.targets,
            tuple,
        ):
            raise TypeError(
                "targets must be a tuple"
            )

        if not all(
            isinstance(
                target,
                AndroidReconstructionCompositionEndpoint,
            )
            for target in self.targets
        ):
            raise TypeError(
                "targets contains an invalid endpoint"
            )

        target_ids = tuple(
            target.endpoint_id
            for target in self.targets
        )

        if len(target_ids) != len(set(target_ids)):
            raise ValueError(
                "composition relationship target identities "
                "must be unique"
            )


class AndroidReconstructionCompositionProjector:
    """
    Mechanical projection of canonical Universe relationships onto
    Reconstruction endpoints.

    This class does not perform semantic relationship resolution.
    """

    @staticmethod
    def _representation_endpoint(
        *,
        requirement: object,
        index: AndroidReconstructionCompositionIndex,
        role: str,
    ) -> AndroidReconstructionCompositionEndpoint:
        representation_id = (
            index.representation_by_requirement_identity.get(
                id(requirement)
            )
        )

        requirement_id = getattr(
            requirement,
            "requirement_id",
            None,
        )

        if representation_id is not None:
            return AndroidReconstructionCompositionEndpoint(
                endpoint_id=(
                    f"endpoint:representation:{representation_id}"
                ),
                kind=(
                    AndroidReconstructionCompositionEndpointKind
                    .REPRESENTATION
                ),
                representation_id=representation_id,
            )

        if (
            isinstance(
                requirement_id,
                str,
            )
            and requirement_id
        ):
            preserved_artifact_id = (
                index.preserved_artifact_by_requirement_id.get(
                    requirement_id
                )
            )

            if preserved_artifact_id is not None:
                return AndroidReconstructionCompositionEndpoint(
                    endpoint_id=(
                        "endpoint:preserved-artifact:"
                        f"{preserved_artifact_id}"
                    ),
                    kind=(
                        AndroidReconstructionCompositionEndpointKind
                        .PRESERVED_ARTIFACT
                    ),
                    preserved_artifact_id=(
                        preserved_artifact_id
                    ),
                )

            return AndroidReconstructionCompositionEndpoint(
                endpoint_id=(
                    f"endpoint:canonical:{role}:"
                    f"{requirement_id}"
                ),
                kind=(
                    AndroidReconstructionCompositionEndpointKind
                    .CANONICAL_REQUIREMENT
                ),
                canonical_identity=requirement_id,
            )

        if isinstance(
            requirement,
            AndroidUniverseRuntimePropertyRequirement,
        ):
            property_key = (
                requirement.property_key
            )

            return AndroidReconstructionCompositionEndpoint(
                endpoint_id=(
                    "endpoint:canonical:runtime-property:"
                    f"{property_key}"
                ),
                kind=(
                    AndroidReconstructionCompositionEndpointKind
                    .CANONICAL_REQUIREMENT
                ),
                canonical_identity=property_key,
            )

        raise ValueError(
            "canonical Composition requirement has neither "
            "a Reconstruction representation nor a stable "
            "canonical identity: "
            f"{type(requirement).__name__}"
        )

    @staticmethod
    def _selinux_context_endpoint(
        *,
        context_requirement: object,
        index: AndroidReconstructionCompositionIndex,
    ) -> AndroidReconstructionCompositionEndpoint:
        representation_id = (
            index.selinux_representation_by_context_identity.get(
                id(context_requirement)
            )
        )

        if representation_id is not None:
            return AndroidReconstructionCompositionEndpoint(
                endpoint_id=(
                    f"endpoint:representation:{representation_id}"
                ),
                kind=(
                    AndroidReconstructionCompositionEndpointKind
                    .REPRESENTATION
                ),
                representation_id=representation_id,
            )

        declaration = getattr(
            context_requirement,
            "declaration",
            None,
        )

        context_kind = getattr(
            context_requirement,
            "kind",
            None,
        )

        source_path = getattr(
            declaration,
            "source_path",
            None,
        )

        source_line = getattr(
            declaration,
            "source_line",
            None,
        )

        selector = getattr(
            declaration,
            "selector",
            None,
        )

        context = getattr(
            declaration,
            "context",
            None,
        )

        kind_value = getattr(
            context_kind,
            "value",
            context_kind,
        )

        if (
            not isinstance(kind_value, str)
            or not kind_value
            or source_path is None
            or not isinstance(source_line, int)
            or source_line < 1
            or not isinstance(selector, str)
            or not selector
            or not isinstance(context, str)
            or not context
        ):
            raise ValueError(
                "canonical SELinux context requirement lacks "
                "stable declaration identity"
            )

        canonical_identity = (
            "selinux-context:"
            f"{kind_value}:"
            f"{source_path.as_posix()}:"
            f"{source_line}:"
            f"{selector}:"
            f"{context}"
        )

        return AndroidReconstructionCompositionEndpoint(
            endpoint_id=(
                "endpoint:canonical:"
                f"{canonical_identity}"
            ),
            kind=(
                AndroidReconstructionCompositionEndpointKind
                .CANONICAL_REQUIREMENT
            ),
            canonical_identity=canonical_identity,
        )

    @staticmethod
    def _semantic_endpoint(
        semantic_identity: str,
    ) -> AndroidReconstructionCompositionEndpoint:
        return AndroidReconstructionCompositionEndpoint(
            endpoint_id=(
                f"endpoint:semantic:{semantic_identity}"
            ),
            kind=(
                AndroidReconstructionCompositionEndpointKind
                .SEMANTIC
            ),
            semantic_identity=semantic_identity,
        )

    @staticmethod
    def _unresolved_endpoint(
        relationship_id: str,
        role: str,
    ) -> AndroidReconstructionCompositionEndpoint:
        return AndroidReconstructionCompositionEndpoint(
            endpoint_id=(
                f"endpoint:unresolved:{relationship_id}:{role}"
            ),
            kind=(
                AndroidReconstructionCompositionEndpointKind
                .UNRESOLVED
            ),
            canonical_identity=relationship_id,
        )

    @classmethod
    def _closed_missing_target_endpoint(
        cls,
        *,
        relationship: object,
        applicability: AndroidUniverseRequirementApplicability,
        service_target_substantiation_by_relationship_id: dict[
            str,
            object,
        ],
    ) -> AndroidReconstructionCompositionEndpoint | None:
        """
        Project a missing concrete target when Universe has already supplied
        an exact semantic disposition for that absence.

        Composition remains projection-only:

        * ALTERNATIVE relationships preserve canonical applicability;
        * executable-artifact ABSENT preserves canonical fulfillment;
        * service-target UNDECLARED preserves canonical target classification.

        No alias, provider, artifact, runtime property, or service declaration
        is invented here. Any missing target without one of these exact
        upstream conclusions remains genuinely unresolved.
        """

        relationship_id = getattr(
            relationship,
            "relationship_id",
            None,
        )

        if (
            not isinstance(
                relationship_id,
                str,
            )
            or not relationship_id
        ):
            raise ValueError(
                "canonical relationship lacks a stable relationship_id"
            )

        if (
            applicability.status
            is AndroidUniverseApplicabilityStatus.ALTERNATIVE
        ):
            return cls._semantic_endpoint(
                "relationship-applicability:"
                "alternative:"
                f"{relationship_id}"
            )

        if isinstance(
            relationship,
            AndroidUniverseInitExecutableArtifactRelationship,
        ):
            if (
                relationship.artifact_fulfillment
                is AndroidUniverseArtifactFulfillmentStatus.ABSENT
            ):
                return cls._semantic_endpoint(
                    "init-executable-artifact:"
                    "absent:"
                    f"{relationship_id}"
                )

            return None

        if isinstance(
            relationship,
            (
                AndroidUniverseInitServiceControlRelationship,
                AndroidUniverseInitOnRestartServiceControlRelationship,
            ),
        ):
            substantiation = (
                service_target_substantiation_by_relationship_id.get(
                    relationship_id
                )
            )

            if substantiation is None:
                return None

            if (
                substantiation.classification
                is not (
                    AndroidUniverseInitServiceTargetClassification
                    .UNDECLARED
                )
            ):
                return None

            evidence_status = (
                "substantiated"
                if substantiation.substantiated
                else "unsubstantiated"
            )

            return cls._semantic_endpoint(
                "init-service-target:"
                f"{substantiation.classification.value}:"
                f"{evidence_status}:"
                f"{substantiation.target}"
            )

        return None

    @classmethod
    def project(
        cls,
        result: AndroidReconstructionResult,
    ) -> tuple[
        AndroidReconstructionCompositionRelationship,
        ...,
    ]:
        if not isinstance(
            result,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "result must be an AndroidReconstructionResult"
            )

        index = (
            AndroidReconstructionCompositionIndex.build(
                result
            )
        )

        plan = (
            result.reconstruction_input.plan
        )

        applicability_by_id = {
            applicability.requirement_id: applicability
            for applicability
            in plan.cross_family_relationship_applicability
        }

        if len(
            applicability_by_id
        ) != len(
            plan.cross_family_relationship_applicability
        ):
            raise ValueError(
                "cross-family relationship applicability "
                "identities must be unique"
            )

        universe = (
            result
            .reconstruction_input
            .runtime_linking
            .universe
        )

        service_target_substantiation_by_relationship_id = {}

        for substantiation in (
            universe.init_service_target_substantiations
        ):
            for substantiated_relationship in (
                substantiation.relationships
            ):
                substantiated_relationship_id = (
                    substantiated_relationship.relationship_id
                )

                existing = (
                    service_target_substantiation_by_relationship_id.get(
                        substantiated_relationship_id
                    )
                )

                if (
                    existing is not None
                    and existing is not substantiation
                ):
                    raise ValueError(
                        "canonical INIT service-target substantiation "
                        "maps one relationship to multiple conclusions: "
                        f"{substantiated_relationship_id}"
                    )

                service_target_substantiation_by_relationship_id[
                    substantiated_relationship_id
                ] = substantiation

        projected = []

        for relationship in (
            plan.cross_family_relationships
        ):
            relationship_id = (
                relationship.relationship_id
            )

            applicability = (
                applicability_by_id.get(
                    relationship_id
                )
            )

            if applicability is None:
                raise ValueError(
                    "canonical relationship is missing "
                    "applicability: "
                    f"{relationship_id}"
                )

            source = None
            targets = ()

            if isinstance(
                relationship,
                (
                    AndroidUniverseInitClassControlRelationship,
                    AndroidUniverseInitServiceControlRelationship,
                    AndroidUniverseInitEventTriggerRelationship,
                    AndroidUniverseInitPropertyCommandRelationship,
                    AndroidUniverseInitPropertyTriggerRelationship,
                ),
            ):
                source = cls._representation_endpoint(
                    requirement=relationship.init_action,
                    index=index,
                    role="init-action",
                )

            elif isinstance(
                relationship,
                (
                    AndroidUniverseInitOnRestartClassControlRelationship,
                    AndroidUniverseInitOnRestartServiceControlRelationship,
                    AndroidUniverseInitOnRestartPropertyCommandRelationship,
                    AndroidUniverseInitExecutableArtifactRelationship,
                    AndroidUniverseInitExecutableSelinuxRelationship,
                    AndroidUniverseInitSeclabelSelinuxRelationship,
                    AndroidUniverseInitInterfaceVintfRelationship,
                ),
            ):
                source = cls._representation_endpoint(
                    requirement=relationship.init_service,
                    index=index,
                    role="init-service",
                )

            elif isinstance(
                relationship,
                AndroidUniverseApkVintfStructuralProviderRelationship,
            ):
                source = cls._representation_endpoint(
                    requirement=relationship.apk_package,
                    index=index,
                    role="apk-package",
                )

            elif isinstance(
                relationship,
                AndroidUniverseArtRuntimeClasspathRelationship,
            ):
                source = cls._representation_endpoint(
                    requirement=relationship.entry.requirement,
                    index=index,
                    role="classpath",
                )

            elif isinstance(
                relationship,
                AndroidUniverseFirstStageKernelModuleLoadingRelationship,
            ):
                source = cls._semantic_endpoint(
                    "first-stage-module-loading:"
                    f"{relationship.policy.source.index}:"
                    f"{relationship.policy.source.key}"
                )

            elif isinstance(
                relationship,
                AndroidUniverseLinkerApexRelationship,
            ):
                source = cls._representation_endpoint(
                    requirement=relationship.apex_requirement,
                    index=index,
                    role="apex",
                )

            elif isinstance(
                relationship,
                AndroidUniversePropertySelinuxRelationship,
            ):
                runtime_property_representation = (
                    index.runtime_property_representation_by_key.get(
                        relationship.property_key
                    )
                )

                if runtime_property_representation is not None:
                    source = (
                        AndroidReconstructionCompositionEndpoint(
                            endpoint_id=(
                                "endpoint:representation:"
                                f"{runtime_property_representation}"
                            ),
                            kind=(
                                AndroidReconstructionCompositionEndpointKind
                                .REPRESENTATION
                            ),
                            representation_id=(
                                runtime_property_representation
                            ),
                        )
                    )
                else:
                    source = (
                        AndroidReconstructionCompositionEndpoint(
                            endpoint_id=(
                                "endpoint:canonical:runtime-property:"
                                f"{relationship.property_key}"
                            ),
                            kind=(
                                AndroidReconstructionCompositionEndpointKind
                                .CANONICAL_REQUIREMENT
                            ),
                            canonical_identity=(
                                relationship.property_key
                            ),
                        )
                    )

            else:
                raise TypeError(
                    "unsupported canonical cross-family "
                    "relationship type: "
                    f"{type(relationship).__name__}"
                )

            if isinstance(
                relationship,
                (
                    AndroidUniverseInitClassControlRelationship,
                    AndroidUniverseInitServiceControlRelationship,
                    AndroidUniverseInitOnRestartClassControlRelationship,
                    AndroidUniverseInitOnRestartServiceControlRelationship,
                ),
            ):
                targets = tuple(
                    cls._representation_endpoint(
                        requirement=service,
                        index=index,
                        role="init-service",
                    )
                    for service
                    in relationship.matched_services
                )

                if not targets:
                    closed_target = (
                        cls._closed_missing_target_endpoint(
                            relationship=relationship,
                            applicability=applicability,
                            service_target_substantiation_by_relationship_id=(
                                service_target_substantiation_by_relationship_id
                            ),
                        )
                    )

                    targets = (
                        (
                            closed_target
                            if closed_target is not None
                            else cls._unresolved_endpoint(
                                relationship_id,
                                "service-target",
                            )
                        ),
                    )

            elif isinstance(
                relationship,
                AndroidUniverseInitEventTriggerRelationship,
            ):
                action_targets = tuple(
                    cls._representation_endpoint(
                        requirement=action,
                        index=index,
                        role="init-action",
                    )
                    for action
                    in relationship.matched_actions
                )

                semantic_targets = (
                    cls._semantic_endpoint(
                        "init-event:"
                        f"{relationship.event}"
                    ),
                )

                targets = (
                    action_targets
                    + semantic_targets
                )

            elif isinstance(
                relationship,
                (
                    AndroidUniverseInitPropertyCommandRelationship,
                    AndroidUniverseInitOnRestartPropertyCommandRelationship,
                    AndroidUniverseInitPropertyTriggerRelationship,
                ),
            ):
                if relationship.runtime_property is not None:
                    targets = (
                        cls._representation_endpoint(
                            requirement=(
                                relationship.runtime_property
                            ),
                            index=index,
                            role="runtime-property",
                        ),
                    )
                else:
                    closed_target = (
                        cls._closed_missing_target_endpoint(
                            relationship=relationship,
                            applicability=applicability,
                            service_target_substantiation_by_relationship_id=(
                                service_target_substantiation_by_relationship_id
                            ),
                        )
                    )

                    targets = (
                        (
                            closed_target
                            if closed_target is not None
                            else cls._unresolved_endpoint(
                                relationship_id,
                                "runtime-property",
                            )
                        ),
                    )

            elif isinstance(
                relationship,
                AndroidUniverseInitExecutableArtifactRelationship,
            ):
                targets = tuple(
                    cls._representation_endpoint(
                        requirement=artifact,
                        index=index,
                        role="artifact",
                    )
                    for artifact
                    in relationship.matched_artifacts
                )

                if not targets:
                    closed_target = (
                        cls._closed_missing_target_endpoint(
                            relationship=relationship,
                            applicability=applicability,
                            service_target_substantiation_by_relationship_id=(
                                service_target_substantiation_by_relationship_id
                            ),
                        )
                    )

                    targets = (
                        (
                            closed_target
                            if closed_target is not None
                            else cls._unresolved_endpoint(
                                relationship_id,
                                "executable-artifact",
                            )
                        ),
                    )

            elif isinstance(
                relationship,
                AndroidUniverseInitExecutableSelinuxRelationship,
            ):
                targets = tuple(
                    cls._selinux_context_endpoint(
                        context_requirement=context_requirement,
                        index=index,
                    )
                    for context_requirement
                    in relationship.context_requirements
                )

                if not targets:
                    targets = (
                        cls._unresolved_endpoint(
                            relationship_id,
                            "selinux-context",
                        ),
                    )

            elif isinstance(
                relationship,
                AndroidUniverseInitSeclabelSelinuxRelationship,
            ):
                targets = (
                    cls._semantic_endpoint(
                        "selinux-type:"
                        f"{relationship.selinux_type}"
                    ),
                )

            elif isinstance(
                relationship,
                (
                    AndroidUniverseInitInterfaceVintfRelationship,
                    AndroidUniverseApkVintfStructuralProviderRelationship,
                ),
            ):
                targets = tuple(
                    cls._representation_endpoint(
                        requirement=evidence.document,
                        index=index,
                        role="vintf-document",
                    )
                    for evidence
                    in relationship.vintf_evidence
                )

            elif isinstance(
                relationship,
                AndroidUniverseFirstStageKernelModuleLoadingRelationship,
            ):
                kernel_module_targets = []

                for entry in relationship.load_entries:
                    module_source = (
                        entry.module.source.elf.source
                    )

                    filesystem_source = (
                        module_source.filesystem_source
                    )

                    if filesystem_source is None:
                        raise ValueError(
                            "first-stage kernel module must preserve "
                            "its canonical filesystem source"
                        )

                    context = (
                        filesystem_source.source_name
                    )

                    android_path = (
                        module_source.android_path.as_posix()
                    )

                    if not context:
                        raise ValueError(
                            "first-stage kernel module must preserve "
                            "a non-empty deployment context"
                        )

                    if (
                        not android_path
                        or not android_path.startswith("/")
                    ):
                        raise ValueError(
                            "first-stage kernel module must preserve "
                            "an absolute canonical Android path"
                        )

                    kernel_module_targets.append(
                        cls._semantic_endpoint(
                            "kernel-module:"
                            f"{context}:"
                            f"{android_path}"
                        )
                    )

                targets = tuple(
                    kernel_module_targets
                )

            elif isinstance(
                relationship,
                AndroidUniverseLinkerApexRelationship,
            ):
                runtime_linking = (
                    result
                    .reconstruction_input
                    .runtime_linking
                )

                provider_matches = tuple(
                    descriptor
                    for descriptor
                    in runtime_linking.linker_apex_provider_descriptors
                    if (
                        descriptor.apex_requirement
                        is relationship.apex_requirement
                    )
                )

                if len(provider_matches) != 1:
                    raise ValueError(
                        "Linker/APEX Composition requires exactly one "
                        "Runtime Linking provider descriptor for the exact "
                        "canonical APEX requirement: "
                        f"{relationship.apex_requirement.requirement_id}: "
                        f"matches={len(provider_matches)}"
                    )

                provider = provider_matches[0]

                if (
                    provider.apex_requirement
                    is not relationship.apex_requirement
                ):
                    raise ValueError(
                        "Linker/APEX Composition changed exact canonical "
                        "APEX requirement identity"
                    )

                if (
                    provider.status
                    is AndroidUniverseLinkerApexProviderStatus.ACTIVE
                ):
                    targets = (
                        cls._semantic_endpoint(
                            provider.descriptor_id
                        ),
                    )

                elif (
                    provider.status
                    is (
                        AndroidUniverseLinkerApexProviderStatus
                        .EXCLUDED_SHARED_APEX
                    )
                ):
                    targets = (
                        cls._semantic_endpoint(
                            f"{provider.descriptor_id}:"
                            "excluded-shared-apex"
                        ),
                    )

                elif (
                    provider.status
                    is AndroidUniverseLinkerApexProviderStatus.AMBIGUOUS
                ):
                    targets = (
                        cls._unresolved_endpoint(
                            relationship_id,
                            "linker-apex-provider-ambiguous",
                        ),
                    )

                elif (
                    provider.status
                    is AndroidUniverseLinkerApexProviderStatus.UNRESOLVED
                ):
                    targets = (
                        cls._unresolved_endpoint(
                            relationship_id,
                            "linker-apex-provider-unresolved",
                        ),
                    )

                else:
                    raise ValueError(
                        "unsupported Runtime Linking APEX provider status: "
                        f"{provider.status!r}"
                    )

            elif isinstance(
                relationship,
                AndroidUniverseArtRuntimeClasspathRelationship,
            ):
                art_targets = []

                for evidence in relationship.dex_evidence:
                    (
                        source_name,
                        source_path,
                    ) = (
                        evidence
                        .oat
                        .elf
                        .source
                        .identity_key
                    )

                    art_targets.append(
                        cls._semantic_endpoint(
                            "art-oat-dex:"
                            f"{source_name}:"
                            f"{source_path}:"
                            f"{evidence.oat.oat_offset}:"
                            f"{evidence.oat_dex_file.index}"
                        )
                    )

                targets = tuple(
                    art_targets
                )

                if not targets:
                    targets = (
                        cls._unresolved_endpoint(
                            relationship_id,
                            "art-runtime-classpath",
                        ),
                    )

            elif isinstance(
                relationship,
                AndroidUniversePropertySelinuxRelationship,
            ):
                targets = tuple(
                    cls._selinux_context_endpoint(
                        context_requirement=context_requirement,
                        index=index,
                    )
                    for context_requirement
                    in relationship.context_requirements
                )

                if not targets:
                    targets = (
                        cls._unresolved_endpoint(
                            relationship_id,
                            "selinux-property-context",
                        ),
                    )

            target_by_id = {}

            for target_endpoint in targets:
                existing = target_by_id.get(
                    target_endpoint.endpoint_id
                )

                if (
                    existing is not None
                    and existing != target_endpoint
                ):
                    raise ValueError(
                        "one projected composition endpoint identity "
                        "maps to conflicting endpoint values: "
                        f"{target_endpoint.endpoint_id}"
                    )

                target_by_id[
                    target_endpoint.endpoint_id
                ] = target_endpoint

            canonical_targets = tuple(
                target_by_id[
                    endpoint_id
                ]
                for endpoint_id
                in sorted(
                    target_by_id
                )
            )

            projected.append(
                AndroidReconstructionCompositionRelationship(
                    relationship_id=relationship_id,
                    relationship=relationship,
                    applicability=applicability,
                    source=source,
                    targets=canonical_targets,
                )
            )

        return tuple(
            sorted(
                projected,
                key=lambda edge: (
                    edge.relationship_id
                ),
            )
        )
