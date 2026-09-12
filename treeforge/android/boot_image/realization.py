from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from shutil import copy2, which
import subprocess
import sys

from treeforge.android.host_provider_bundle import (
    ANDROID_15_HOST_PROVIDER_RELEASE,
    AndroidHostProviderBundleLoader,
    android_host_provider_bundle_root,
)
from treeforge.android.boot_image.avb_descriptor_codec import (
    encode_avb_descriptor,
    encode_avb_descriptor_sequence,
    replace_chain_partition_public_key,
)
from treeforge.android.boot_image.composition import (
    AndroidBootImageAvbPartitionReferenceComposition,
)
from treeforge.android.boot_image.models import (
    AndroidBootImageAvbDescriptorKind,
    AndroidBootImageAvbSourceKind,
    AndroidBootImageAvbVbmetaInterpretation,
    AndroidBootImageComponentRole,
    AndroidBootImageDtboContainerInterpretation,
)
from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbPropertyDescriptor,
)
from treeforge.android.boot_image.planning import (
    AndroidBootImageBootImagePlan,
    AndroidBootImageComponentPlan,
    AndroidBootImageConditionalRequirement,
    AndroidBootImageConditionalRequirementKind,
    AndroidBootImageConditionalTrigger,
    AndroidBootImagePlanningDisposition,
    AndroidBootImagePlanningResult,
)
from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionArtifactKind,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageMutationRequest:
    """
    Explicit Realization request to replace one exact planned component.

    Mutation is never inferred from structured evidence or provider
    availability. The target retains exact Planning object identity.
    """

    target: AndroidBootImageComponentPlan
    replacement_path: Path

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.target,
            AndroidBootImageComponentPlan,
        ):
            raise TypeError(
                "target must be an AndroidBootImageComponentPlan"
            )

        if not isinstance(
            self.replacement_path,
            Path,
        ):
            raise TypeError(
                "replacement_path must be a pathlib.Path"
            )

        if not self.replacement_path.is_file():
            raise FileNotFoundError(
                "Boot Image mutation replacement does not exist: "
                f"{self.replacement_path}"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageMutationEvaluation:
    """
    Derived consequences of one explicit component mutation request.

    This is trigger evaluation only. It performs no reconstruction and
    selects no provider.
    """

    request: AndroidBootImageMutationRequest
    image_plan: AndroidBootImageBootImagePlan

    original_size_bytes: int
    original_sha256: str

    replacement_size_bytes: int
    replacement_sha256: str

    content_changed: bool

    triggers: tuple[
        AndroidBootImageConditionalTrigger,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.request,
            AndroidBootImageMutationRequest,
        ):
            raise TypeError(
                "request must be an AndroidBootImageMutationRequest"
            )

        if not isinstance(
            self.image_plan,
            AndroidBootImageBootImagePlan,
        ):
            raise TypeError(
                "image_plan must be an AndroidBootImageBootImagePlan"
            )

        if not any(
            candidate is self.request.target
            for candidate
            in self.image_plan.component_plans
        ):
            raise ValueError(
                "mutation request target must belong to the exact "
                "evaluated boot-image plan"
            )

        for name, value in (
            (
                "original_size_bytes",
                self.original_size_bytes,
            ),
            (
                "replacement_size_bytes",
                self.replacement_size_bytes,
            ),
        ):
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
                raise ValueError(
                    f"{name} must be a non-negative int"
                )

        for name, value in (
            (
                "original_sha256",
                self.original_sha256,
            ),
            (
                "replacement_sha256",
                self.replacement_sha256,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or len(
                    value
                ) != 64
            ):
                raise ValueError(
                    f"{name} must be a SHA-256 hex digest"
                )

        expected_changed = (
            self.original_size_bytes
            != self.replacement_size_bytes
            or self.original_sha256
            != self.replacement_sha256
        )

        if (
            self.content_changed
            is not expected_changed
        ):
            raise ValueError(
                "content_changed must exactly reflect replacement "
                "byte identity"
            )

        if not isinstance(
            self.triggers,
            tuple,
        ):
            raise TypeError(
                "triggers must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageConditionalTrigger,
            )
            for value
            in self.triggers
        ):
            raise TypeError(
                "triggers contains an invalid conditional trigger"
            )

        if len(
            {
                value
                for value
                in self.triggers
            }
        ) != len(
            self.triggers
        ):
            raise ValueError(
                "mutation evaluation triggers must be unique"
            )

        if (
            not self.content_changed
            and self.triggers
        ):
            raise ValueError(
                "byte-identical replacement cannot activate "
                "mutation triggers"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageMutationAnalysis:
    """
    Complete mutation-trigger analysis for one exact Planning result.

    Active requirements retain the exact Planning requirement objects.
    """

    planning: AndroidBootImagePlanningResult

    requests: tuple[
        AndroidBootImageMutationRequest,
        ...,
    ]

    evaluations: tuple[
        AndroidBootImageMutationEvaluation,
        ...,
    ]

    active_conditional_requirements: tuple[
        AndroidBootImageConditionalRequirement,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.planning,
            AndroidBootImagePlanningResult,
        ):
            raise TypeError(
                "planning must be an AndroidBootImagePlanningResult"
            )

        if not isinstance(
            self.requests,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageMutationRequest,
            )
            for value
            in self.requests
        ):
            raise TypeError(
                "requests contains an invalid mutation request"
            )

        if not isinstance(
            self.evaluations,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageMutationEvaluation,
            )
            for value
            in self.evaluations
        ):
            raise TypeError(
                "evaluations contains an invalid mutation evaluation"
            )

        if tuple(
            id(
                value.request
            )
            for value
            in self.evaluations
        ) != tuple(
            id(
                value
            )
            for value
            in self.requests
        ):
            raise ValueError(
                "mutation analysis must conserve every request in "
                "exact order and identity"
            )

        all_plans = tuple(
            plan
            for image
            in self.planning.boot_images
            for plan
            in image.component_plans
        )

        for request in self.requests:
            if not any(
                candidate is request.target
                for candidate
                in all_plans
            ):
                raise ValueError(
                    "mutation request target must belong to the "
                    "exact Planning result"
                )

        if len(
            {
                id(
                    request.target
                )
                for request
                in self.requests
            }
        ) != len(
            self.requests
        ):
            raise ValueError(
                "Boot Image mutation analysis permits at most one "
                "replacement request per component plan"
            )

        if not isinstance(
            self.active_conditional_requirements,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageConditionalRequirement,
            )
            for value
            in self.active_conditional_requirements
        ):
            raise TypeError(
                "active_conditional_requirements contains an "
                "invalid Planning requirement"
            )

        planned_requirements = tuple(
            requirement
            for image
            in self.planning.boot_images
            for requirement
            in image.conditional_requirements
        )

        for requirement in (
            self.active_conditional_requirements
        ):
            if not any(
                candidate is requirement
                for candidate
                in planned_requirements
            ):
                raise ValueError(
                    "active conditional requirement must retain "
                    "exact Planning identity"
                )

        if len(
            {
                id(
                    value
                )
                for value
                in self.active_conditional_requirements
            }
        ) != len(
            self.active_conditional_requirements
        ):
            raise ValueError(
                "active conditional requirements must be unique"
            )

    @property
    def request_count(
        self,
    ) -> int:
        return len(
            self.requests
        )

    @property
    def evaluation_count(
        self,
    ) -> int:
        return len(
            self.evaluations
        )

    @property
    def active_requirement_count(
        self,
    ) -> int:
        return len(
            self.active_conditional_requirements
        )


class AndroidBootImageAvbSigningPolicy(
    StrEnum
):
    """
    Requested signing-identity policy for regenerated AVB metadata.

    This is a Realization policy. It is never canonical factory evidence.
    """

    PRESERVE_FACTORY = "preserve_factory"

    EXTERNAL_KEY = "external_key"

    DEVELOPMENT_KEY = "development_key"


class AndroidBootImageAvbResolutionDisposition(
    StrEnum
):
    """
    Current disposition of one active AVB reevaluation requirement.
    """

    PRESERVED = "preserved"

    REGENERATION_READY = "regeneration_ready"

    SIGNING_MATERIAL_REQUIRED = (
        "signing_material_required"
    )

    PARENT_TRUST_UPDATE_REQUIRED = (
        "parent_trust_update_required"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbRegenerationContract:
    """
    Exact canonical AVB contract governing one mutated boot-family image.

    All AVB objects remain the exact Interpretation / Composition objects.
    No signing key or replacement trust identity is invented here.
    """

    requirement: AndroidBootImageConditionalRequirement

    image_plan: AndroidBootImageBootImagePlan

    embedded_vbmeta: AndroidBootImageAvbVbmetaInterpretation

    hash_descriptor: AndroidParsedAvbHashDescriptor

    property_descriptors: tuple[
        AndroidParsedAvbPropertyDescriptor,
        ...,
    ]

    parent_chain_references: tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ]

    partition_size_bytes: int

    def __post_init__(
        self,
    ) -> None:
        if (
            self.requirement.kind
            is not
            AndroidBootImageConditionalRequirementKind
            .AVB_REEVALUATION
        ):
            raise ValueError(
                "AVB regeneration contract requires an "
                "AVB_REEVALUATION requirement"
            )

        if (
            self.requirement.image
            is not self.image_plan.composition
        ):
            raise ValueError(
                "AVB contract must retain exact Planning "
                "Composition identity"
            )

        if (
            self.embedded_vbmeta.source_kind
            is not AndroidBootImageAvbSourceKind.EMBEDDED
        ):
            raise ValueError(
                "AVB regeneration contract requires embedded VBMeta"
            )

        if not any(
            region.vbmeta is self.embedded_vbmeta
            for region
            in self.image_plan.composition.avb_regions
        ):
            raise ValueError(
                "embedded VBMeta must belong to this exact "
                "boot-image Composition"
            )

        if not any(
            descriptor.descriptor is self.hash_descriptor
            and (
                descriptor.kind
                is AndroidBootImageAvbDescriptorKind.HASH
            )
            for descriptor
            in self.embedded_vbmeta.descriptors
        ):
            raise ValueError(
                "AVB contract hash descriptor must retain exact "
                "embedded VBMeta descriptor identity"
            )

        partition_name = (
            self.image_plan
            .composition
            .image
            .image
            .partition
            .name
        )

        if (
            self.hash_descriptor.partition_name
            != partition_name
        ):
            raise ValueError(
                "AVB hash descriptor partition must match "
                "the exact boot-image partition"
            )

        expected_properties = tuple(
            descriptor.descriptor
            for descriptor
            in self.embedded_vbmeta.descriptors
            if isinstance(
                descriptor.descriptor,
                AndroidParsedAvbPropertyDescriptor,
            )
        )

        if tuple(
            id(value)
            for value
            in self.property_descriptors
        ) != tuple(
            id(value)
            for value
            in expected_properties
        ):
            raise ValueError(
                "AVB property descriptor population must retain "
                "exact canonical order and identity"
            )

        for reference in self.parent_chain_references:
            if (
                reference.target_partition
                != partition_name
            ):
                raise ValueError(
                    "parent AVB chain reference targets the "
                    "wrong partition"
                )

            if (
                reference.descriptor.kind
                is not
                AndroidBootImageAvbDescriptorKind
                .CHAIN_PARTITION
            ):
                raise ValueError(
                    "parent AVB reference must be a "
                    "chain-partition descriptor"
                )

            if not isinstance(
                reference.descriptor.descriptor,
                AndroidParsedAvbChainPartitionDescriptor,
            ):
                raise TypeError(
                    "parent chain reference must retain an exact "
                    "AndroidParsedAvbChainPartitionDescriptor"
                )

        if (
            isinstance(
                self.partition_size_bytes,
                bool,
            )
            or not isinstance(
                self.partition_size_bytes,
                int,
            )
            or self.partition_size_bytes <= 0
        ):
            raise ValueError(
                "partition_size_bytes must be a positive int"
            )

        container_size = (
            self.embedded_vbmeta
            .container_artifact
            .size_bytes
        )

        if (
            container_size is not None
            and self.partition_size_bytes
            != container_size
        ):
            raise ValueError(
                "AVB partition size must match the canonical "
                "container artifact size"
            )

        footer = self.embedded_vbmeta.footer

        if footer is None:
            raise ValueError(
                "embedded AVB regeneration requires a canonical footer"
            )

        if (
            footer.original_image_size
            != self.hash_descriptor.image_size
        ):
            raise ValueError(
                "canonical AVB footer original-image size must "
                "equal the hash descriptor image size"
            )

    @property
    def partition_name(
        self,
    ) -> str:
        return self.hash_descriptor.partition_name

    @property
    def hash_algorithm(
        self,
    ) -> str:
        return self.hash_descriptor.hash_algorithm

    @property
    def salt(
        self,
    ) -> bytes:
        return self.hash_descriptor.salt

    @property
    def descriptor_flags(
        self,
    ) -> int:
        return self.hash_descriptor.flags

    @property
    def algorithm_type(
        self,
    ) -> int:
        return self.embedded_vbmeta.algorithm_type

    @property
    def rollback_index(
        self,
    ) -> int:
        return self.embedded_vbmeta.rollback_index

    @property
    def rollback_index_location(
        self,
    ) -> int:
        return (
            self.embedded_vbmeta
            .rollback_index_location
        )

    @property
    def vbmeta_flags(
        self,
    ) -> int:
        return self.embedded_vbmeta.flags

    @property
    def factory_public_key(
        self,
    ) -> bytes:
        return self.embedded_vbmeta.public_key

    @property
    def required_libavb_version_major(
        self,
    ) -> int:
        return (
            self.embedded_vbmeta
            .vbmeta
            .metadata
            .required_libavb_version_major
        )

    @property
    def required_libavb_version_minor(
        self,
    ) -> int:
        return (
            self.embedded_vbmeta
            .vbmeta
            .metadata
            .required_libavb_version_minor
        )

    @property
    def release_string(
        self,
    ) -> str:
        return (
            self.embedded_vbmeta
            .vbmeta
            .metadata
            .release_string
        )

    @property
    def public_key_metadata(
        self,
    ) -> bytes:
        return (
            self.embedded_vbmeta
            .vbmeta
            .metadata
            .public_key_metadata
        )

    @property
    def factory_original_image_size_bytes(
        self,
    ) -> int:
        footer = self.embedded_vbmeta.footer

        assert footer is not None

        return footer.original_image_size


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbResolution:
    """
    Realization-time resolution of one active canonical AVB contract.

    No private signing material is inferred from a factory image.
    """

    contract: AndroidBootImageAvbRegenerationContract

    signing_policy: AndroidBootImageAvbSigningPolicy

    disposition: AndroidBootImageAvbResolutionDisposition

    signing_key_path: Path | None = None

    derived_public_key: bytes | None = None

    parent_trust_update_required: bool | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.contract,
            AndroidBootImageAvbRegenerationContract,
        ):
            raise TypeError(
                "contract must be an "
                "AndroidBootImageAvbRegenerationContract"
            )

        if not isinstance(
            self.signing_policy,
            AndroidBootImageAvbSigningPolicy,
        ):
            raise TypeError(
                "signing_policy must be an "
                "AndroidBootImageAvbSigningPolicy"
            )

        if not isinstance(
            self.disposition,
            AndroidBootImageAvbResolutionDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImageAvbResolutionDisposition"
            )

        if (
            self.signing_key_path is not None
            and not isinstance(
                self.signing_key_path,
                Path,
            )
        ):
            raise TypeError(
                "signing_key_path must be a pathlib.Path or None"
            )

        if (
            self.derived_public_key is not None
            and not isinstance(
                self.derived_public_key,
                bytes,
            )
        ):
            raise TypeError(
                "derived_public_key must be bytes or None"
            )

        if (
            self.parent_trust_update_required
            is not None
            and not isinstance(
                self.parent_trust_update_required,
                bool,
            )
        ):
            raise TypeError(
                "parent_trust_update_required must be bool or None"
            )

        if (
            self.signing_policy
            is AndroidBootImageAvbSigningPolicy
            .PRESERVE_FACTORY
        ):
            if self.signing_key_path is not None:
                raise ValueError(
                    "preserve-factory signing policy cannot "
                    "invent a private key"
                )

            if self.derived_public_key is not None:
                raise ValueError(
                    "preserve-factory signing policy cannot "
                    "invent a replacement public key"
                )

            if (
                self.contract.algorithm_type
                == 0
            ):
                #
                # AVB algorithm NONE has no signing identity. Changed image
                # content still requires regeneration of the hash descriptor,
                # VBMeta block, and footer, but it requires no private key and
                # creates no replacement public-key trust edge.
                #
                if (
                    self.disposition
                    is not
                    AndroidBootImageAvbResolutionDisposition
                    .REGENERATION_READY
                ):
                    raise ValueError(
                        "algorithm-NONE preserve-factory AVB must be "
                        "regeneration-ready"
                    )

                if (
                    self.parent_trust_update_required
                    is not False
                ):
                    raise ValueError(
                        "algorithm-NONE AVB cannot require a signing-identity "
                        "parent trust update"
                    )

            else:
                if (
                    self.disposition
                    is not
                    AndroidBootImageAvbResolutionDisposition
                    .SIGNING_MATERIAL_REQUIRED
                ):
                    raise ValueError(
                        "changed signed AVB content with preserve-factory "
                        "policy must remain signing-material-required"
                    )

                if (
                    self.parent_trust_update_required
                    is not None
                ):
                    raise ValueError(
                        "parent trust cannot be resolved until a "
                        "replacement signing identity exists"
                    )

        elif (
            self.signing_policy
            in {
                AndroidBootImageAvbSigningPolicy
                .EXTERNAL_KEY,
                AndroidBootImageAvbSigningPolicy
                .DEVELOPMENT_KEY,
            }
        ):
            if self.signing_key_path is None:
                raise ValueError(
                    f"{self.signing_policy.value} signing policy "
                    "requires a private key path"
                )

            if not self.signing_key_path.is_file():
                raise FileNotFoundError(
                    "AVB signing key is unavailable: "
                    f"{self.signing_key_path}"
                )

            if (
                not isinstance(
                    self.derived_public_key,
                    bytes,
                )
                or not self.derived_public_key
            ):
                raise ValueError(
                    f"{self.signing_policy.value} signing policy "
                    "requires a derived AVB public key"
                )

            if self.parent_trust_update_required is None:
                raise ValueError(
                    f"{self.signing_policy.value} signing policy "
                    "must resolve parent trust compatibility"
                )

            expected_disposition = (
                AndroidBootImageAvbResolutionDisposition
                .PARENT_TRUST_UPDATE_REQUIRED
                if self.parent_trust_update_required
                else (
                    AndroidBootImageAvbResolutionDisposition
                    .REGENERATION_READY
                )
            )

            if (
                self.disposition
                is not expected_disposition
            ):
                raise ValueError(
                    f"{self.signing_policy.value} AVB disposition "
                    "does not match resolved parent trust "
                    "compatibility"
                )

        else:
            raise ValueError(
                "unsupported AVB signing policy: "
                f"{self.signing_policy}"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbTrustChange:
    """
    One realized change to an AVB signing identity which must be
    propagated through canonical chain-partition references.

    The changed node itself may originate from an initially regenerated
    boot-family AVB image or from a recursively regenerated standalone
    VBMeta image. Parent discovery remains canonical Composition topology.
    """

    target_partition: str

    original_public_key: bytes

    replacement_public_key: bytes

    parent_chain_references: tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ]

    source_resolution: (
        AndroidBootImageAvbResolution
        | None
    ) = None

    source_parent_realization: (
        "AndroidBootImageParentVbmetaRealization"
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.target_partition,
                str,
            )
            or not self.target_partition
        ):
            raise ValueError(
                "target_partition must be a non-empty string"
            )

        if (
            not isinstance(
                self.original_public_key,
                bytes,
            )
            or not self.original_public_key
        ):
            raise ValueError(
                "original_public_key must be non-empty bytes"
            )

        if (
            not isinstance(
                self.replacement_public_key,
                bytes,
            )
            or not self.replacement_public_key
        ):
            raise ValueError(
                "replacement_public_key must be non-empty bytes"
            )

        if (
            self.original_public_key
            == self.replacement_public_key
        ):
            raise ValueError(
                "AVB trust change requires a changed "
                "public signing identity"
            )

        if not isinstance(
            self.parent_chain_references,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageAvbPartitionReferenceComposition,
            )
            for value
            in self.parent_chain_references
        ):
            raise TypeError(
                "parent_chain_references must contain only "
                "canonical AVB partition references"
            )

        if any(
            reference.target_partition
            != self.target_partition
            for reference
            in self.parent_chain_references
        ):
            raise ValueError(
                "every parent chain reference must target the "
                "changed AVB partition"
            )

        source_count = sum(
            (
                self.source_resolution
                is not None,
                self.source_parent_realization
                is not None,
            )
        )

        if source_count != 1:
            raise ValueError(
                "AVB trust change must retain exactly one "
                "realization source"
            )

        if (
            self.source_resolution is not None
            and not isinstance(
                self.source_resolution,
                AndroidBootImageAvbResolution,
            )
        ):
            raise TypeError(
                "source_resolution must be an "
                "AndroidBootImageAvbResolution or None"
            )

        if self.source_resolution is not None:
            resolution = (
                self.source_resolution
            )

            if (
                resolution.parent_trust_update_required
                is not True
            ):
                raise ValueError(
                    "resolution-backed AVB trust change requires "
                    "an active parent-trust update"
                )

            if (
                resolution.derived_public_key
                != self.replacement_public_key
            ):
                raise ValueError(
                    "resolution-backed AVB trust change must "
                    "retain the exact derived public key"
                )

            if (
                resolution.contract.factory_public_key
                != self.original_public_key
            ):
                raise ValueError(
                    "resolution-backed AVB trust change must "
                    "retain the exact canonical factory public key"
                )

            if (
                resolution.contract.partition_name
                != self.target_partition
            ):
                raise ValueError(
                    "resolution-backed AVB trust change partition "
                    "does not match its canonical AVB contract"
                )

            if tuple(
                id(value)
                for value
                in self.parent_chain_references
            ) != tuple(
                id(value)
                for value
                in resolution
                .contract
                .parent_chain_references
            ):
                raise ValueError(
                    "resolution-backed AVB trust change must "
                    "retain exact canonical parent-reference "
                    "order and identity"
                )

    @property
    def origin_resolutions(
        self,
    ) -> tuple[
        AndroidBootImageAvbResolution,
        ...,
    ]:
        if self.source_resolution is not None:
            return (
                self.source_resolution,
            )

        source = (
            self.source_parent_realization
        )

        if source is None:
            raise RuntimeError(
                "AVB trust change lost its realization source"
            )

        ordered = []
        seen = set()

        for trust_change in (
            source
            .rewrite
            .trust_changes
        ):
            for resolution in (
                trust_change
                .origin_resolutions
            ):
                identity = id(
                    resolution
                )

                if identity in seen:
                    continue

                seen.add(
                    identity
                )

                ordered.append(
                    resolution
                )

        return tuple(
            ordered
        )

    @property
    def parent_count(
        self,
    ) -> int:
        return len(
            self.parent_chain_references
        )

    @property
    def is_root_trust_change(
        self,
    ) -> bool:
        return not (
            self.parent_chain_references
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageParentVbmetaRewrite:
    """
    One batched descriptor rewrite for one exact standalone parent
    VBMeta image.

    Every changed child trust edge targeting this parent is rewritten
    together so the parent image is regenerated and signed exactly once.
    Canonical descriptor order and every unaffected descriptor byte are
    preserved.
    """

    trust_changes: tuple[
        AndroidBootImageAvbTrustChange,
        ...,
    ]

    parent_vbmeta: AndroidBootImageAvbVbmetaInterpretation

    chain_references: tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ]

    descriptor_indexes: tuple[
        int,
        ...,
    ]

    original_descriptor_blob: bytes

    rewritten_descriptor_blob: bytes

    original_chain_descriptors: tuple[
        AndroidParsedAvbChainPartitionDescriptor,
        ...,
    ]

    rewritten_chain_descriptors: tuple[
        AndroidParsedAvbChainPartitionDescriptor,
        ...,
    ]

    output_path: Path

    unchanged_descriptor_count: int

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.trust_changes,
                tuple,
            )
            or not self.trust_changes
            or not all(
                isinstance(
                    value,
                    AndroidBootImageAvbTrustChange,
                )
                for value
                in self.trust_changes
            )
        ):
            raise TypeError(
                "trust_changes must be a non-empty tuple of "
                "AndroidBootImageAvbTrustChange"
            )

        if not isinstance(
            self.parent_vbmeta,
            AndroidBootImageAvbVbmetaInterpretation,
        ):
            raise TypeError(
                "parent_vbmeta must be an "
                "AndroidBootImageAvbVbmetaInterpretation"
            )

        if (
            self.parent_vbmeta.source_kind
            is not AndroidBootImageAvbSourceKind.STANDALONE
        ):
            raise ValueError(
                "parent VBMeta rewrite requires a standalone "
                "canonical VBMeta node"
            )

        population_lengths = {
            len(
                self.trust_changes
            ),
            len(
                self.chain_references
            ),
            len(
                self.descriptor_indexes
            ),
            len(
                self.original_chain_descriptors
            ),
            len(
                self.rewritten_chain_descriptors
            ),
        }

        if (
            len(population_lengths) != 1
            or not self.chain_references
        ):
            raise ValueError(
                "parent VBMeta rewrite populations must be "
                "non-empty and have identical lengths"
            )

        canonical_descriptors = (
            self.parent_vbmeta
            .vbmeta
            .metadata
            .descriptors
        )

        seen_indexes = set()
        seen_reference_ids = set()

        for (
            trust_change,
            reference,
            descriptor_index,
            original_chain,
            rewritten_chain,
        ) in zip(
            self.trust_changes,
            self.chain_references,
            self.descriptor_indexes,
            self.original_chain_descriptors,
            self.rewritten_chain_descriptors,
            strict=True,
        ):
            if not isinstance(
                reference,
                AndroidBootImageAvbPartitionReferenceComposition,
            ):
                raise TypeError(
                    "chain_references contains an invalid "
                    "canonical AVB reference"
                )

            if (
                reference.vbmeta
                is not self.parent_vbmeta
            ):
                raise ValueError(
                    "every rewritten chain reference must retain "
                    "the exact parent VBMeta identity"
                )

            if not any(
                candidate is reference
                for candidate
                in trust_change.parent_chain_references
            ):
                raise ValueError(
                    "rewritten chain reference is not an exact "
                    "parent reference of its AVB trust change"
                )

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
                or descriptor_index >= len(
                    canonical_descriptors
                )
            ):
                raise ValueError(
                    "descriptor index is outside the canonical "
                    "parent descriptor population"
                )

            if descriptor_index in seen_indexes:
                raise ValueError(
                    "one canonical parent descriptor cannot be "
                    "rewritten more than once"
                )

            seen_indexes.add(
                descriptor_index
            )

            reference_identity = id(
                reference
            )

            if (
                reference_identity
                in seen_reference_ids
            ):
                raise ValueError(
                    "canonical parent chain reference is duplicated "
                    "inside one rewrite batch"
                )

            seen_reference_ids.add(
                reference_identity
            )

            if not isinstance(
                original_chain,
                AndroidParsedAvbChainPartitionDescriptor,
            ):
                raise TypeError(
                    "original chain descriptor has invalid type"
                )

            if not isinstance(
                rewritten_chain,
                AndroidParsedAvbChainPartitionDescriptor,
            ):
                raise TypeError(
                    "rewritten chain descriptor has invalid type"
                )

            if (
                canonical_descriptors[
                    descriptor_index
                ]
                is not original_chain
            ):
                raise ValueError(
                    "descriptor index must retain exact canonical "
                    "chain-descriptor identity"
                )

            if (
                reference
                .descriptor
                .descriptor
                is not original_chain
            ):
                raise ValueError(
                    "chain reference lost its exact canonical "
                    "descriptor identity"
                )

            if (
                original_chain.partition_name
                != trust_change.target_partition
            ):
                raise ValueError(
                    "canonical chain descriptor target does not "
                    "match its AVB trust change"
                )

            if (
                original_chain.public_key
                != trust_change.original_public_key
            ):
                raise ValueError(
                    "canonical parent chain key does not match "
                    "the trust-change original public key"
                )

            if (
                rewritten_chain.partition_name
                != original_chain.partition_name
            ):
                raise ValueError(
                    "parent rewrite changed chain partition name"
                )

            if (
                rewritten_chain.public_key
                != trust_change.replacement_public_key
            ):
                raise ValueError(
                    "parent rewrite did not install the exact "
                    "replacement public key"
                )

        if not isinstance(
            self.original_descriptor_blob,
            bytes,
        ):
            raise TypeError(
                "original_descriptor_blob must be bytes"
            )

        if not isinstance(
            self.rewritten_descriptor_blob,
            bytes,
        ):
            raise TypeError(
                "rewritten_descriptor_blob must be bytes"
            )

        if (
            self.original_descriptor_blob
            == self.rewritten_descriptor_blob
        ):
            raise ValueError(
                "parent descriptor rewrite must change bytes"
            )

        expected_unchanged = (
            len(
                canonical_descriptors
            )
            - len(
                self.descriptor_indexes
            )
        )

        if (
            self.unchanged_descriptor_count
            != expected_unchanged
        ):
            raise ValueError(
                "parent descriptor unchanged count does not "
                "match the batched rewrite population"
            )

        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be a pathlib.Path"
            )

        if not self.output_path.is_file():
            raise FileNotFoundError(
                "rewritten parent descriptor blob is unavailable: "
                f"{self.output_path}"
            )

        if (
            self.output_path.read_bytes()
            != self.rewritten_descriptor_blob
        ):
            raise ValueError(
                "materialized parent descriptor rewrite changed bytes"
            )

    @property
    def changed_descriptor_count(
        self,
    ) -> int:
        return len(
            self.descriptor_indexes
        )

    @property
    def descriptor_count(
        self,
    ) -> int:
        return len(
            self.parent_vbmeta
            .vbmeta
            .metadata
            .descriptors
        )

    @property
    def descriptor_order_preserved(
        self,
    ) -> bool:
        return True

    @property
    def public_key_changed(
        self,
    ) -> bool:
        return all(
            original.public_key
            != rewritten.public_key
            for original, rewritten
            in zip(
                self.original_chain_descriptors,
                self.rewritten_chain_descriptors,
                strict=True,
            )
        )

    @property
    def child_resolution(
        self,
    ) -> AndroidBootImageAvbResolution | None:
        if len(
            self.trust_changes
        ) != 1:
            return None

        return (
            self.trust_changes[0]
            .source_resolution
        )

    #
    # Compatibility views used by the current single-edge report.
    #
    @property
    def chain_reference(
        self,
    ) -> AndroidBootImageAvbPartitionReferenceComposition:
        return self.chain_references[0]

    @property
    def descriptor_index(
        self,
    ) -> int:
        return self.descriptor_indexes[0]

    @property
    def original_chain_descriptor(
        self,
    ) -> AndroidParsedAvbChainPartitionDescriptor:
        return self.original_chain_descriptors[0]

    @property
    def rewritten_chain_descriptor(
        self,
    ) -> AndroidParsedAvbChainPartitionDescriptor:
        return self.rewritten_chain_descriptors[0]

    @property
    def target_partition(
        self,
    ) -> str:
        if len(
            self.trust_changes
        ) == 1:
            return (
                self.trust_changes[0]
                .target_partition
            )

        return ",".join(
            trust_change.target_partition
            for trust_change
            in self.trust_changes
        )


class AndroidBootImageParentVbmetaTrustDisposition(
    StrEnum
):
    """
    Trust disposition of one regenerated parent VBMeta image.

    Cryptographic validity and device/root trust are intentionally
    represented separately.
    """

    FACTORY_SIGNING_IDENTITY_PRESERVED = (
        "factory_signing_identity_preserved"
    )

    REPLACEMENT_SIGNING_IDENTITY = (
        "replacement_signing_identity"
    )

    ROOT_TRUST_UNRESOLVED = (
        "root_trust_unresolved"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageParentVbmetaRealization:
    """
    Complete regenerated standalone parent VBMeta image derived from one
    exact parent descriptor rewrite.

    This records cryptographic realization only. A valid signature does
    not itself prove that the device bootloader trusts the signing key.
    """

    rewrite: AndroidBootImageParentVbmetaRewrite

    signing_key_path: Path

    derived_public_key: bytes

    output_path: Path

    size_bytes: int

    content_sha256: str

    verification_complete: bool

    trust_disposition: AndroidBootImageParentVbmetaTrustDisposition

    upstream_chain_references: tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.rewrite,
            AndroidBootImageParentVbmetaRewrite,
        ):
            raise TypeError(
                "rewrite must be an "
                "AndroidBootImageParentVbmetaRewrite"
            )

        if not isinstance(
            self.signing_key_path,
            Path,
        ):
            raise TypeError(
                "signing_key_path must be a pathlib.Path"
            )

        if not self.signing_key_path.is_file():
            raise FileNotFoundError(
                "parent VBMeta signing key is unavailable: "
                f"{self.signing_key_path}"
            )

        if (
            not isinstance(
                self.derived_public_key,
                bytes,
            )
            or not self.derived_public_key
        ):
            raise ValueError(
                "derived_public_key must be non-empty bytes"
            )

        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be a pathlib.Path"
            )

        if (
            isinstance(
                self.size_bytes,
                bool,
            )
            or not isinstance(
                self.size_bytes,
                int,
            )
            or self.size_bytes <= 0
        ):
            raise ValueError(
                "size_bytes must be a positive int"
            )

        if (
            not isinstance(
                self.content_sha256,
                str,
            )
            or len(
                self.content_sha256
            ) != 64
        ):
            raise ValueError(
                "content_sha256 must be a SHA-256 hex digest"
            )

        if not isinstance(
            self.verification_complete,
            bool,
        ):
            raise TypeError(
                "verification_complete must be bool"
            )

        if not isinstance(
            self.trust_disposition,
            AndroidBootImageParentVbmetaTrustDisposition,
        ):
            raise TypeError(
                "trust_disposition must be an "
                "AndroidBootImageParentVbmetaTrustDisposition"
            )

        if not isinstance(
            self.upstream_chain_references,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageAvbPartitionReferenceComposition,
            )
            for value
            in self.upstream_chain_references
        ):
            raise TypeError(
                "upstream_chain_references must contain only "
                "AndroidBootImageAvbPartitionReferenceComposition"
            )

        parent_partition = (
            self.parent_vbmeta.partition
        )

        parent_partition_name = (
            getattr(
                parent_partition,
                "name",
                None,
            )
        )

        if (
            not isinstance(
                parent_partition_name,
                str,
            )
            or not parent_partition_name
        ):
            raise ValueError(
                "parent standalone VBMeta must retain a canonical "
                "partition name"
            )

        if any(
            reference.target_partition
            != parent_partition_name
            for reference
            in self.upstream_chain_references
        ):
            raise ValueError(
                "every upstream AVB reference must target the "
                "realized parent VBMeta partition"
            )

        if (
            self.trust_disposition
            is
            AndroidBootImageParentVbmetaTrustDisposition
            .ROOT_TRUST_UNRESOLVED
            and self.upstream_chain_references
        ):
            raise ValueError(
                "ROOT_TRUST_UNRESOLVED is valid only for a "
                "top-level canonical AVB node with no upstream "
                "AVB chain reference"
            )

        if (
            self.trust_disposition
            is
            AndroidBootImageParentVbmetaTrustDisposition
            .REPLACEMENT_SIGNING_IDENTITY
            and not self.upstream_chain_references
        ):
            raise ValueError(
                "REPLACEMENT_SIGNING_IDENTITY requires an "
                "upstream canonical AVB parent to update"
            )

    @property
    def child_resolution(
        self,
    ) -> AndroidBootImageAvbResolution | None:
        return self.rewrite.child_resolution

    @property
    def origin_resolutions(
        self,
    ) -> tuple[
        AndroidBootImageAvbResolution,
        ...,
    ]:
        ordered = []
        seen = set()

        for trust_change in (
            self.rewrite
            .trust_changes
        ):
            for resolution in (
                trust_change
                .origin_resolutions
            ):
                identity = id(
                    resolution
                )

                if identity in seen:
                    continue

                seen.add(
                    identity
                )

                ordered.append(
                    resolution
                )

        return tuple(
            ordered
        )

    @property
    def parent_vbmeta(
        self,
    ) -> AndroidBootImageAvbVbmetaInterpretation:
        return self.rewrite.parent_vbmeta

    @property
    def upstream_chain_reference_count(
        self,
    ) -> int:
        return len(
            self.upstream_chain_references
        )

    @property
    def is_top_level_avb_node(
        self,
    ) -> bool:
        return (
            self.upstream_chain_reference_count
            == 0
        )

    @property
    def bootloader_trust_anchor_required(
        self,
    ) -> bool:
        return (
            self.verification_complete
            and self.is_top_level_avb_node
            and (
                self.trust_disposition
                is
                AndroidBootImageParentVbmetaTrustDisposition
                .ROOT_TRUST_UNRESOLVED
            )
        )

    @property
    def upstream_trust_update_required(
        self,
    ) -> bool:
        return (
            self.verification_complete
            and not self.is_top_level_avb_node
            and (
                self.trust_disposition
                is
                AndroidBootImageParentVbmetaTrustDisposition
                .REPLACEMENT_SIGNING_IDENTITY
            )
        )

    @property
    def parent_trust_complete(
        self,
    ) -> bool:
        return (
            self.verification_complete
            and (
                self.trust_disposition
                is
                AndroidBootImageParentVbmetaTrustDisposition
                .FACTORY_SIGNING_IDENTITY_PRESERVED
            )
        )


class AndroidBootImageProviderCapability(
    StrEnum
):
    """
    Concrete host capability required by Boot Image Realization.

    Capabilities are consequences of already-proven mutation work.
    Provider availability never creates a mutation requirement.
    """

    BOOT_IMAGE_RECONSTRUCTION = (
        "boot_image_reconstruction"
    )

    BOOT_IMAGE_INSPECTION = (
        "boot_image_inspection"
    )

    AVB_REEVALUATION = (
        "avb_reevaluation"
    )

    BOOT_SIGNATURE_REGENERATION = (
        "boot_signature_regeneration"
    )

    VENDOR_RAMDISK_TABLE_REGENERATION = (
        "vendor_ramdisk_table_regeneration"
    )

    DTBO_RECONSTRUCTION = (
        "dtbo_reconstruction"
    )


class AndroidBootImageProviderSource(
    StrEnum
):
    """
    Origin of one concrete realization provider.
    """

    HOST_PATH = "host_path"

    TREEFORGE_BUNDLE = "treeforge_bundle"



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageProviderCandidate:
    """
    One concrete provider discovered only because a mutation requires one
    of its capabilities.
    """

    name: str
    source: AndroidBootImageProviderSource
    executable: Path

    capabilities: tuple[
        AndroidBootImageProviderCapability,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "provider name must be a non-empty string"
            )

        if not isinstance(
            self.source,
            AndroidBootImageProviderSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidBootImageProviderSource"
            )

        if not isinstance(
            self.executable,
            Path,
        ):
            raise TypeError(
                "executable must be a pathlib.Path"
            )

        if not self.executable.is_file():
            raise FileNotFoundError(
                "Boot Image provider is unavailable: "
                f"{self.executable}"
            )

        if not isinstance(
            self.capabilities,
            tuple,
        ) or not self.capabilities:
            raise ValueError(
                "provider must expose at least one capability"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageProviderCapability,
            )
            for value
            in self.capabilities
        ):
            raise TypeError(
                "provider capabilities contain an invalid value"
            )

        if len(
            set(
                self.capabilities
            )
        ) != len(
            self.capabilities
        ):
            raise ValueError(
                "provider capabilities must be unique"
            )

    def supports(
        self,
        capability: AndroidBootImageProviderCapability,
    ) -> bool:
        return capability in self.capabilities


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageProviderSelection:
    """
    Selection of one provider for one exact mutation-evaluation or Planning
    conditional-requirement owner.
    """

    owner: object
    capability: AndroidBootImageProviderCapability
    provider: AndroidBootImageProviderCandidate

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.capability,
            AndroidBootImageProviderCapability,
        ):
            raise TypeError(
                "capability must be an "
                "AndroidBootImageProviderCapability"
            )

        if not isinstance(
            self.provider,
            AndroidBootImageProviderCandidate,
        ):
            raise TypeError(
                "provider must be an "
                "AndroidBootImageProviderCandidate"
            )

        if not self.provider.supports(
            self.capability
        ):
            raise ValueError(
                "selected provider does not support the "
                "required capability"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageProviderAnalysis:
    """
    Demand-driven provider discovery and selection for one mutation analysis.

    With no required mutation work both populations must remain empty.
    """

    mutation_analysis: AndroidBootImageMutationAnalysis

    candidates: tuple[
        AndroidBootImageProviderCandidate,
        ...,
    ]

    selections: tuple[
        AndroidBootImageProviderSelection,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.mutation_analysis,
            AndroidBootImageMutationAnalysis,
        ):
            raise TypeError(
                "mutation_analysis must be an "
                "AndroidBootImageMutationAnalysis"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageProviderCandidate,
            )
            for value
            in self.candidates
        ):
            raise TypeError(
                "candidates contains an invalid provider"
            )

        if not isinstance(
            self.selections,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageProviderSelection,
            )
            for value
            in self.selections
        ):
            raise TypeError(
                "selections contains an invalid provider selection"
            )

        candidate_ids = {
            id(
                value
            )
            for value
            in self.candidates
        }

        for selection in self.selections:
            if (
                id(
                    selection.provider
                )
                not in candidate_ids
            ):
                raise ValueError(
                    "provider selection must retain exact "
                    "candidate identity"
                )

        valid_owner_ids = {
            id(
                value
            )
            for value
            in (
                *self.mutation_analysis.evaluations,
                *self.mutation_analysis
                .active_conditional_requirements,
            )
        }

        for selection in self.selections:
            if (
                id(
                    selection.owner
                )
                not in valid_owner_ids
            ):
                raise ValueError(
                    "provider selection owner must retain exact "
                    "mutation-evaluation or Planning-requirement identity"
                )

        if (
            not self.mutation_analysis.requests
            and (
                self.candidates
                or self.selections
            )
        ):
            raise ValueError(
                "zero-mutation provider analysis must not "
                "discover or select providers"
            )

    @property
    def candidate_count(
        self,
    ) -> int:
        return len(
            self.candidates
        )

    @property
    def selection_count(
        self,
    ) -> int:
        return len(
            self.selections
        )


class AndroidBootImageRealizationProvider(
    StrEnum
):
    """
    Concrete provider used for one Boot Image Realization outcome.

    External Android construction providers are intentionally not selected
    until a plan requires mutation/reconstruction.
    """

    EXACT_ARTIFACT = "exact_artifact"
    MUTATION_INPUT = "mutation_input"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageComponentRealization:
    """
    Physical realization of one exact Boot Image component plan.

    The initial realization path preserves the canonical Extraction payload
    byte-for-byte. No image reconstruction or mutation is performed.
    """

    plan: AndroidBootImageComponentPlan
    provider: AndroidBootImageRealizationProvider
    output_path: Path
    size_bytes: int
    content_sha256: str
    mutated: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.plan,
            AndroidBootImageComponentPlan,
        ):
            raise TypeError(
                "plan must be an AndroidBootImageComponentPlan"
            )

        if (
            self.plan.disposition
            is not
            AndroidBootImagePlanningDisposition
            .PRESERVE_EXACT
        ):
            raise ValueError(
                "initial Boot Image Realization requires "
                "PRESERVE_EXACT component plans"
            )

        if self.provider not in (
            AndroidBootImageRealizationProvider.EXACT_ARTIFACT,
            AndroidBootImageRealizationProvider.MUTATION_INPUT,
        ):
            raise ValueError(
                "unsupported Boot Image component realization provider"
            )

        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be a pathlib.Path"
            )

        if not self.output_path.is_file():
            raise FileNotFoundError(
                "realized component does not exist: "
                f"{self.output_path}"
            )

        if (
            isinstance(
                self.size_bytes,
                bool,
            )
            or not isinstance(
                self.size_bytes,
                int,
            )
            or self.size_bytes < 0
        ):
            raise ValueError(
                "size_bytes must be a non-negative int"
            )

        if (
            not isinstance(
                self.content_sha256,
                str,
            )
            or len(
                self.content_sha256
            ) != 64
        ):
            raise ValueError(
                "content_sha256 must be a SHA-256 hex digest"
            )

        if (
            self.provider
            is AndroidBootImageRealizationProvider.EXACT_ARTIFACT
            and self.mutated
        ):
            raise ValueError(
                "exact-artifact realization cannot be mutated"
            )

        if (
            self.provider
            is AndroidBootImageRealizationProvider.MUTATION_INPUT
            and not self.mutated
        ):
            raise ValueError(
                "mutation-input realization must represent changed bytes"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDtboRealization:
    """
    Exact realization of one globally composed DTBO container.
    """

    container: AndroidBootImageDtboContainerInterpretation
    provider: AndroidBootImageRealizationProvider
    output_path: Path
    size_bytes: int
    content_sha256: str
    mutated: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.container,
            AndroidBootImageDtboContainerInterpretation,
        ):
            raise TypeError(
                "container must be an "
                "AndroidBootImageDtboContainerInterpretation"
            )

        if (
            self.provider
            is not
            AndroidBootImageRealizationProvider
            .EXACT_ARTIFACT
        ):
            raise ValueError(
                "initial DTBO realization only permits "
                "the exact-artifact provider"
            )

        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be a pathlib.Path"
            )

        if not self.output_path.is_file():
            raise FileNotFoundError(
                "realized DTBO container does not exist: "
                f"{self.output_path}"
            )

        if (
            isinstance(
                self.size_bytes,
                bool,
            )
            or not isinstance(
                self.size_bytes,
                int,
            )
            or self.size_bytes < 0
        ):
            raise ValueError(
                "size_bytes must be a non-negative int"
            )

        if (
            not isinstance(
                self.content_sha256,
                str,
            )
            or len(
                self.content_sha256
            ) != 64
        ):
            raise ValueError(
                "content_sha256 must be a SHA-256 hex digest"
            )

        if self.mutated:
            raise ValueError(
                "exact DTBO realization cannot be mutated"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageProviderInvocation:
    """
    One concrete external provider execution.

    Provider selection and provider invocation remain distinct so selected
    AVB work may remain pending while a pre-AVB image is reconstructed.
    """

    provider: AndroidBootImageProviderCandidate
    capability: AndroidBootImageProviderCapability
    command: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes

    def __post_init__(self) -> None:
        if not isinstance(
            self.provider,
            AndroidBootImageProviderCandidate,
        ):
            raise TypeError(
                "provider must be an AndroidBootImageProviderCandidate"
            )

        if not isinstance(
            self.capability,
            AndroidBootImageProviderCapability,
        ):
            raise TypeError(
                "capability must be an AndroidBootImageProviderCapability"
            )

        if not self.provider.supports(self.capability):
            raise ValueError(
                "invoked provider does not support the recorded capability"
            )

        if (
            not isinstance(self.command, tuple)
            or not self.command
            or not all(isinstance(value, str) for value in self.command)
        ):
            raise TypeError(
                "command must be a non-empty tuple of strings"
            )

        if (
            isinstance(self.returncode, bool)
            or not isinstance(self.returncode, int)
        ):
            raise TypeError("returncode must be an int")

        if not isinstance(self.stdout, bytes):
            raise TypeError("stdout must be bytes")

        if not isinstance(self.stderr, bytes):
            raise TypeError("stderr must be bytes")


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageBootImageRealization:
    """
    Reconstructed pre-AVB boot-family image.

    AVB completion is intentionally separate from mkbootimg construction.
    """

    image_plan: AndroidBootImageBootImagePlan
    provider: AndroidBootImageProviderCandidate
    verification_provider: AndroidBootImageProviderCandidate
    output_path: Path
    size_bytes: int
    content_sha256: str
    avb_complete: bool
    parent_trust_complete: bool

    def __post_init__(self) -> None:
        if not isinstance(
            self.image_plan,
            AndroidBootImageBootImagePlan,
        ):
            raise TypeError(
                "image_plan must be an AndroidBootImageBootImagePlan"
            )

        if not self.provider.supports(
            AndroidBootImageProviderCapability.BOOT_IMAGE_RECONSTRUCTION
        ):
            raise ValueError(
                "boot image provider lacks reconstruction capability"
            )

        if not self.verification_provider.supports(
            AndroidBootImageProviderCapability.BOOT_IMAGE_INSPECTION
        ):
            raise ValueError(
                "verification provider lacks boot-image inspection capability"
            )

        if not isinstance(self.output_path, Path):
            raise TypeError("output_path must be a pathlib.Path")

        if not self.output_path.is_file():
            raise FileNotFoundError(
                f"reconstructed boot image is unavailable: {self.output_path}"
            )

        if (
            isinstance(self.size_bytes, bool)
            or not isinstance(self.size_bytes, int)
            or self.size_bytes <= 0
        ):
            raise ValueError(
                "size_bytes must be a positive int"
            )

        if (
            not isinstance(self.content_sha256, str)
            or len(self.content_sha256) != 64
        ):
            raise ValueError(
                "content_sha256 must be a SHA-256 hex digest"
            )

        if not isinstance(self.avb_complete, bool):
            raise TypeError("avb_complete must be bool")

        if not isinstance(
            self.parent_trust_complete,
            bool,
        ):
            raise TypeError(
                "parent_trust_complete must be bool"
            )

    @property
    def flashable_chain_complete(
        self,
    ) -> bool:
        return (
            self.avb_complete
            and self.parent_trust_complete
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageRealizationResult:
    """
    First-class Boot Image Realization boundary.

    Exact Planning identity is retained. The initial realization population
    consists only of byte-exact preservation outcomes.
    """

    planning: AndroidBootImagePlanningResult

    mutation_analysis: AndroidBootImageMutationAnalysis

    provider_analysis: AndroidBootImageProviderAnalysis

    avb_resolutions: tuple[
        AndroidBootImageAvbResolution,
        ...,
    ]

    parent_vbmeta_rewrites: tuple[
        AndroidBootImageParentVbmetaRewrite,
        ...,
    ]

    parent_vbmeta_realizations: tuple[
        AndroidBootImageParentVbmetaRealization,
        ...,
    ]

    parent_vbmeta_signing_material_required: tuple[
        AndroidBootImageParentVbmetaRewrite,
        ...,
    ]

    post_avb_conditional_requirements: tuple[
        AndroidBootImageConditionalRequirement,
        ...,
    ]

    provider_invocations: tuple[
        AndroidBootImageProviderInvocation,
        ...,
    ]

    rebuilt_boot_images: tuple[
        AndroidBootImageBootImageRealization,
        ...,
    ]

    components: tuple[
        AndroidBootImageComponentRealization,
        ...,
    ]

    dtbo_containers: tuple[
        AndroidBootImageDtboRealization,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.planning,
            AndroidBootImagePlanningResult,
        ):
            raise TypeError(
                "planning must be an AndroidBootImagePlanningResult"
            )

        if not isinstance(
            self.mutation_analysis,
            AndroidBootImageMutationAnalysis,
        ):
            raise TypeError(
                "mutation_analysis must be an "
                "AndroidBootImageMutationAnalysis"
            )

        if (
            self.mutation_analysis.planning
            is not self.planning
        ):
            raise ValueError(
                "mutation analysis must retain exact "
                "Planning result identity"
            )

        if not isinstance(
            self.provider_analysis,
            AndroidBootImageProviderAnalysis,
        ):
            raise TypeError(
                "provider_analysis must be an "
                "AndroidBootImageProviderAnalysis"
            )

        if (
            self.provider_analysis.mutation_analysis
            is not self.mutation_analysis
        ):
            raise ValueError(
                "provider analysis must retain exact "
                "mutation-analysis identity"
            )

        if not isinstance(
            self.avb_resolutions,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageAvbResolution,
            )
            for value
            in self.avb_resolutions
        ):
            raise TypeError(
                "avb_resolutions contains an invalid AVB resolution"
            )

        active_avb_requirements = tuple(
            requirement
            for requirement
            in (
                self.mutation_analysis
                .active_conditional_requirements
            )
            if (
                requirement.kind
                is
                AndroidBootImageConditionalRequirementKind
                .AVB_REEVALUATION
            )
        )

        if tuple(
            id(
                value.contract.requirement
            )
            for value
            in self.avb_resolutions
        ) != tuple(
            id(
                value
            )
            for value
            in active_avb_requirements
        ):
            raise ValueError(
                "AVB resolutions must conserve every active "
                "AVB_REEVALUATION requirement in exact order "
                "and identity"
            )

        if not isinstance(
            self.parent_vbmeta_rewrites,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageParentVbmetaRewrite,
            )
            for value
            in self.parent_vbmeta_rewrites
        ):
            raise TypeError(
                "parent_vbmeta_rewrites contains an invalid rewrite"
            )

        #
        # Initial trust propagation must consume every canonical parent
        # edge of every resolved child identity change exactly once.
        #
        expected_initial_edges = []

        for resolution in (
            self.avb_resolutions
        ):
            if (
                resolution.parent_trust_update_required
                is not True
                or resolution.derived_public_key is None
            ):
                continue

            for reference in (
                resolution
                .contract
                .parent_chain_references
            ):
                expected_initial_edges.append(
                    (
                        id(
                            resolution
                        ),
                        id(
                            reference
                        ),
                    )
                )

        actual_initial_edges = []

        for rewrite in (
            self.parent_vbmeta_rewrites
        ):
            for (
                trust_change,
                reference,
            ) in zip(
                rewrite.trust_changes,
                rewrite.chain_references,
                strict=True,
            ):
                if (
                    trust_change
                    .source_resolution
                    is None
                ):
                    continue

                actual_initial_edges.append(
                    (
                        id(
                            trust_change
                            .source_resolution
                        ),
                        id(
                            reference
                        ),
                    )
                )

        if (
            len(actual_initial_edges)
            != len(expected_initial_edges)
            or set(
                actual_initial_edges
            )
            != set(
                expected_initial_edges
            )
        ):
            raise ValueError(
                "parent VBMeta rewrites must conserve every "
                "initial canonical parent-trust edge exactly once"
            )

        #
        # A standalone parent whose replacement signing identity requires
        # another upstream update must likewise have every canonical
        # upstream edge consumed exactly once by a later rewrite.
        #
        expected_recursive_edges = []

        for realization in (
            self.parent_vbmeta_realizations
        ):
            if not (
                realization
                .upstream_trust_update_required
            ):
                continue

            for reference in (
                realization
                .upstream_chain_references
            ):
                expected_recursive_edges.append(
                    (
                        id(
                            realization
                        ),
                        id(
                            reference
                        ),
                    )
                )

        actual_recursive_edges = []

        for rewrite in (
            self.parent_vbmeta_rewrites
        ):
            for (
                trust_change,
                reference,
            ) in zip(
                rewrite.trust_changes,
                rewrite.chain_references,
                strict=True,
            ):
                if (
                    trust_change
                    .source_parent_realization
                    is None
                ):
                    continue

                actual_recursive_edges.append(
                    (
                        id(
                            trust_change
                            .source_parent_realization
                        ),
                        id(
                            reference
                        ),
                    )
                )

        if (
            len(actual_recursive_edges)
            != len(expected_recursive_edges)
            or set(
                actual_recursive_edges
            )
            != set(
                expected_recursive_edges
            )
        ):
            raise ValueError(
                "recursive parent VBMeta rewrites must conserve "
                "every required upstream canonical trust edge "
                "exactly once"
            )

        #
        # One standalone parent must be rewritten at most once. All child
        # trust changes affecting it are required to be batched.
        #
        parent_rewrite_ids = tuple(
            id(
                rewrite.parent_vbmeta
            )
            for rewrite
            in self.parent_vbmeta_rewrites
        )

        if len(
            parent_rewrite_ids
        ) != len(
            set(
                parent_rewrite_ids
            )
        ):
            raise ValueError(
                "one standalone parent VBMeta may have only one "
                "batched rewrite in a propagation graph"
            )

        if not isinstance(
            self.parent_vbmeta_realizations,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageParentVbmetaRealization,
            )
            for value
            in self.parent_vbmeta_realizations
        ):
            raise TypeError(
                "parent_vbmeta_realizations contains "
                "an invalid realization"
            )

        rewrite_ids = {
            id(
                value
            )
            for value
            in self.parent_vbmeta_rewrites
        }

        for realization in (
            self.parent_vbmeta_realizations
        ):
            if (
                id(
                    realization.rewrite
                )
                not in rewrite_ids
            ):
                raise ValueError(
                    "parent VBMeta realization must retain "
                    "exact rewrite identity"
                )

        if len(
            {
                id(
                    value.rewrite
                )
                for value
                in self.parent_vbmeta_realizations
            }
        ) != len(
            self.parent_vbmeta_realizations
        ):
            raise ValueError(
                "each parent VBMeta rewrite may be realized "
                "at most once"
            )

        if not isinstance(
            self.parent_vbmeta_signing_material_required,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageParentVbmetaRewrite,
            )
            for value
            in self.parent_vbmeta_signing_material_required
        ):
            raise TypeError(
                "parent_vbmeta_signing_material_required "
                "contains an invalid rewrite"
            )

        rewrite_ids = {
            id(
                value
            )
            for value
            in self.parent_vbmeta_rewrites
        }

        unresolved_rewrite_ids = tuple(
            id(
                value
            )
            for value
            in self.parent_vbmeta_signing_material_required
        )

        if any(
            identity not in rewrite_ids
            for identity
            in unresolved_rewrite_ids
        ):
            raise ValueError(
                "parent signing-material requirement must retain "
                "exact parent-rewrite identity"
            )

        if len(
            unresolved_rewrite_ids
        ) != len(
            set(
                unresolved_rewrite_ids
            )
        ):
            raise ValueError(
                "parent signing-material requirement population "
                "contains duplicate rewrite identity"
            )

        realized_rewrite_ids = {
            id(
                realization.rewrite
            )
            for realization
            in self.parent_vbmeta_realizations
        }

        overlap = (
            realized_rewrite_ids
            & set(
                unresolved_rewrite_ids
            )
        )

        if overlap:
            raise ValueError(
                "one parent VBMeta rewrite cannot be both "
                "realized and signing-material-required"
            )

        disposed_rewrite_ids = (
            realized_rewrite_ids
            | set(
                unresolved_rewrite_ids
            )
        )

        if disposed_rewrite_ids != rewrite_ids:
            raise ValueError(
                "every parent VBMeta rewrite must be explicitly "
                "disposed as realized or signing-material-required"
            )

        if not isinstance(
            self.post_avb_conditional_requirements,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageConditionalRequirement,
            )
            for value
            in self.post_avb_conditional_requirements
        ):
            raise TypeError(
                "post_avb_conditional_requirements contains "
                "an invalid Planning requirement"
            )

        planned_requirements = tuple(
            requirement
            for image_plan
            in self.planning.boot_images
            for requirement
            in image_plan.conditional_requirements
        )

        for requirement in (
            self.post_avb_conditional_requirements
        ):
            if not any(
                candidate is requirement
                for candidate
                in planned_requirements
            ):
                raise ValueError(
                    "post-AVB conditional requirement must retain "
                    "exact Planning requirement identity"
                )

            if (
                requirement.kind
                is not
                AndroidBootImageConditionalRequirementKind
                .BOOTLOADER_TRUST_ANCHOR_UPDATE
            ):
                raise ValueError(
                    "only bootloader trust-anchor requirements "
                    "may be activated by post-AVB analysis"
                )

            if (
                requirement.trigger
                is not
                AndroidBootImageConditionalTrigger
                .TOP_LEVEL_AVB_SIGNING_IDENTITY_CHANGED
            ):
                raise ValueError(
                    "post-AVB bootloader trust requirement has "
                    "the wrong trigger"
                )

        expected_post_avb_requirements = []

        for parent_realization in (
            self.parent_vbmeta_realizations
        ):
            if not (
                parent_realization
                .bootloader_trust_anchor_required
            ):
                continue

            for origin_resolution in (
                parent_realization
                .origin_resolutions
            ):
                child_image = (
                    origin_resolution
                    .contract
                    .requirement
                    .image
                )

                matches = tuple(
                    requirement
                    for requirement
                    in planned_requirements
                    if (
                        requirement.image
                        is child_image
                        and (
                            requirement.kind
                            is
                            AndroidBootImageConditionalRequirementKind
                            .BOOTLOADER_TRUST_ANCHOR_UPDATE
                        )
                        and (
                            requirement.trigger
                            is
                            AndroidBootImageConditionalTrigger
                            .TOP_LEVEL_AVB_SIGNING_IDENTITY_CHANGED
                        )
                    )
                )

                if len(matches) != 1:
                    raise ValueError(
                        "top-level AVB signing-identity change must "
                        "map each origin image to exactly one planned "
                        "bootloader trust-anchor requirement; "
                        f"found {len(matches)}"
                    )

                requirement = (
                    matches[0]
                )

                if any(
                    candidate is requirement
                    for candidate
                    in expected_post_avb_requirements
                ):
                    continue

                expected_post_avb_requirements.append(
                    requirement
                )

        if tuple(
            id(value)
            for value
            in self.post_avb_conditional_requirements
        ) != tuple(
            id(value)
            for value
            in expected_post_avb_requirements
        ):
            raise ValueError(
                "post-AVB conditional requirements must exactly "
                "conserve every realized top-level signing-identity "
                "change in parent-realization order"
            )

        if not isinstance(
            self.provider_invocations,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageProviderInvocation,
            )
            for value
            in self.provider_invocations
        ):
            raise TypeError(
                "provider_invocations contains an invalid invocation"
            )

        candidate_ids = {
            id(value)
            for value
            in self.provider_analysis.candidates
        }

        for invocation in self.provider_invocations:
            if id(invocation.provider) not in candidate_ids:
                raise ValueError(
                    "provider invocation must retain exact provider "
                    "candidate identity"
                )

        if not isinstance(
            self.rebuilt_boot_images,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageBootImageRealization,
            )
            for value
            in self.rebuilt_boot_images
        ):
            raise TypeError(
                "rebuilt_boot_images contains an invalid realization"
            )

        planned_image_ids = {
            id(value)
            for value
            in self.planning.boot_images
        }

        for rebuilt in self.rebuilt_boot_images:
            if id(rebuilt.image_plan) not in planned_image_ids:
                raise ValueError(
                    "rebuilt boot image must retain exact image-plan identity"
                )

        if len(
            {id(value.image_plan) for value in self.rebuilt_boot_images}
        ) != len(self.rebuilt_boot_images):
            raise ValueError(
                "each boot-image plan may be reconstructed at most once"
            )

        if not isinstance(
            self.components,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageComponentRealization,
            )
            for value
            in self.components
        ):
            raise TypeError(
                "components contains an invalid realization"
            )

        if not isinstance(
            self.dtbo_containers,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageDtboRealization,
            )
            for value
            in self.dtbo_containers
        ):
            raise TypeError(
                "dtbo_containers contains an invalid realization"
            )

        expected_component_plans = tuple(
            plan
            for image
            in self.planning.boot_images
            for plan
            in image.component_plans
        )

        if tuple(
            id(
                value.plan
            )
            for value
            in self.components
        ) != tuple(
            id(
                value
            )
            for value
            in expected_component_plans
        ):
            raise ValueError(
                "Boot Image Realization must conserve every "
                "component plan in exact order and identity"
            )

        if tuple(
            id(
                value.container
            )
            for value
            in self.dtbo_containers
        ) != tuple(
            id(
                value
            )
            for value
            in self.planning.dtbo_containers
        ):
            raise ValueError(
                "Boot Image Realization must conserve every "
                "DTBO plan in exact order and identity"
            )

    @property
    def composition(
        self,
    ):
        return self.planning.composition

    @property
    def interpretation(
        self,
    ):
        return self.planning.interpretation

    @property
    def parsing(
        self,
    ) -> AndroidParsingResult:
        return self.planning.parsing

    @property
    def evidence(
        self,
    ):
        """
        Exact Planning evidence population retained across the Realization
        boundary without duplication or reinterpretation.
        """

        return self.planning.evidence

    @property
    def evidence_count(
        self,
    ) -> int:
        return len(
            self.evidence
        )

    @property
    def exact_preservation_count(
        self,
    ) -> int:
        return sum(
            not value.mutated
            for value
            in (
                *self.components,
                *self.dtbo_containers,
            )
        )

    @property
    def mutated_count(
        self,
    ) -> int:
        return sum(
            value.mutated
            for value
            in (
                *self.components,
                *self.dtbo_containers,
            )
        )

    @property
    def mutation_request_count(
        self,
    ) -> int:
        return self.mutation_analysis.request_count

    @property
    def mutation_evaluation_count(
        self,
    ) -> int:
        return self.mutation_analysis.evaluation_count

    @property
    def provider_candidates(
        self,
    ) -> tuple[
        AndroidBootImageProviderCandidate,
        ...,
    ]:
        return self.provider_analysis.candidates

    @property
    def provider_selections(
        self,
    ) -> tuple[
        AndroidBootImageProviderSelection,
        ...,
    ]:
        return self.provider_analysis.selections

    @property
    def provider_candidate_count(
        self,
    ) -> int:
        return self.provider_analysis.candidate_count

    @property
    def provider_selection_count(
        self,
    ) -> int:
        return self.provider_analysis.selection_count

    @property
    def avb_resolution_count(
        self,
    ) -> int:
        return len(
            self.avb_resolutions
        )

    @property
    def avb_signing_material_required_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self.avb_resolutions
            if (
                value.disposition
                is
                AndroidBootImageAvbResolutionDisposition
                .SIGNING_MATERIAL_REQUIRED
            )
        )

    @property
    def parent_vbmeta_rewrite_count(
        self,
    ) -> int:
        return len(
            self.parent_vbmeta_rewrites
        )

    @property
    def parent_vbmeta_realization_count(
        self,
    ) -> int:
        return len(
            self.parent_vbmeta_realizations
        )

    @property
    def parent_vbmeta_signing_material_required_count(
        self,
    ) -> int:
        return len(
            self.parent_vbmeta_signing_material_required
        )

    @property
    def provider_invocation_count(
        self,
    ) -> int:
        return len(self.provider_invocations)

    @property
    def rebuilt_boot_image_count(
        self,
    ) -> int:
        return len(self.rebuilt_boot_images)

    @property
    def active_conditional_requirements(
        self,
    ) -> tuple[
        AndroidBootImageConditionalRequirement,
        ...,
    ]:
        return (
            self.mutation_analysis
            .active_conditional_requirements
            + self.post_avb_conditional_requirements
        )

    @property
    def active_conditional_requirement_count(
        self,
    ) -> int:
        return len(
            self.active_conditional_requirements
        )


class AndroidBootImageRealizer:
    """
    Execute target-neutral Boot Image Planning outcomes.

    Current scope:
    - exact physical artifact preservation;
    - explicit component mutation-request validation;
    - mutation trigger evaluation;
    - exact Planning conditional-requirement activation;
    - no mutation provider execution yet;
    - no mkbootimg invocation;
    - no AVB regeneration;
    - no DTBO regeneration;
    - no signing.

    Provider selection is intentionally deferred until a mutation analysis
    proves that reconstruction work is required.
    """

    @staticmethod
    def _digest_file(
        path: Path,
    ) -> str:
        digest = sha256()

        with path.open(
            "rb"
        ) as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return digest.hexdigest()

    @classmethod
    def _file_identity(
        cls,
        path: Path,
    ) -> tuple[
        int,
        str,
    ]:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            raise FileNotFoundError(
                f"Boot Image mutation source is unavailable: {path}"
            )

        return (
            path.stat().st_size,
            cls._digest_file(
                path
            ),
        )

    @staticmethod
    def _image_for_component_plan(
        planning: AndroidBootImagePlanningResult,
        target: AndroidBootImageComponentPlan,
    ) -> AndroidBootImageBootImagePlan:
        matches = tuple(
            image
            for image
            in planning.boot_images
            if any(
                candidate is target
                for candidate
                in image.component_plans
            )
        )

        if len(
            matches
        ) != 1:
            raise ValueError(
                "mutation target must resolve to exactly one "
                "boot-image plan"
            )

        return matches[0]

    @classmethod
    def analyze_mutations(
        cls,
        planning: AndroidBootImagePlanningResult,
        mutation_requests: tuple[
            AndroidBootImageMutationRequest,
            ...,
        ] = (),
    ) -> AndroidBootImageMutationAnalysis:
        if not isinstance(
            planning,
            AndroidBootImagePlanningResult,
        ):
            raise TypeError(
                "planning must be an AndroidBootImagePlanningResult"
            )

        if not isinstance(
            mutation_requests,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageMutationRequest,
            )
            for value
            in mutation_requests
        ):
            raise TypeError(
                "mutation_requests must contain only "
                "AndroidBootImageMutationRequest values"
            )

        if len(
            {
                id(
                    request.target
                )
                for request
                in mutation_requests
            }
        ) != len(
            mutation_requests
        ):
            raise ValueError(
                "only one mutation request may target each "
                "component plan"
            )

        evaluations = []

        triggers_by_image: dict[
            int,
            set[
                AndroidBootImageConditionalTrigger
            ],
        ] = {}

        for request in mutation_requests:
            image_plan = cls._image_for_component_plan(
                planning,
                request.target,
            )

            artifact = (
                request.target
                .component
                .artifact
            )

            original_size, original_digest = (
                cls._file_identity(
                    artifact.path
                )
            )

            if (
                artifact.size_bytes is not None
                and original_size
                != artifact.size_bytes
            ):
                raise RuntimeError(
                    "mutation analysis found canonical Extraction "
                    "size mismatch"
                )

            if (
                artifact.content_sha256 is not None
                and original_digest
                != artifact.content_sha256
            ):
                raise RuntimeError(
                    "mutation analysis found canonical Extraction "
                    "SHA-256 mismatch"
                )

            (
                replacement_size,
                replacement_digest,
            ) = cls._file_identity(
                request.replacement_path
            )

            content_changed = (
                original_size
                != replacement_size
                or original_digest
                != replacement_digest
            )

            triggers = []

            if content_changed:
                triggers.append(
                    AndroidBootImageConditionalTrigger
                    .IMAGE_CONTENT_CHANGED
                )

                component = (
                    request.target.component
                )

                if any(
                    signed_payload.covers_component(
                        component
                    )
                    for signed_payload
                    in (
                        image_plan
                        .composition
                        .signed_payloads
                    )
                ):
                    triggers.append(
                        AndroidBootImageConditionalTrigger
                        .SIGNED_BOOT_PAYLOAD_CHANGED
                    )

                if (
                    component.role
                    is AndroidBootImageComponentRole.RAMDISK
                    and bool(
                        image_plan
                        .composition
                        .vendor_ramdisk_entries
                    )
                    and replacement_size
                    != original_size
                ):
                    triggers.append(
                        AndroidBootImageConditionalTrigger
                        .VENDOR_RAMDISK_LAYOUT_CHANGED
                    )

            evaluation = (
                AndroidBootImageMutationEvaluation(
                    request=request,
                    image_plan=image_plan,
                    original_size_bytes=(
                        original_size
                    ),
                    original_sha256=(
                        original_digest
                    ),
                    replacement_size_bytes=(
                        replacement_size
                    ),
                    replacement_sha256=(
                        replacement_digest
                    ),
                    content_changed=(
                        content_changed
                    ),
                    triggers=tuple(
                        triggers
                    ),
                )
            )

            evaluations.append(
                evaluation
            )

            image_triggers = (
                triggers_by_image
                .setdefault(
                    id(
                        image_plan
                    ),
                    set(),
                )
            )

            image_triggers.update(
                evaluation.triggers
            )

        active_requirements = []

        for image_plan in planning.boot_images:
            active_triggers = (
                triggers_by_image.get(
                    id(
                        image_plan
                    ),
                    set(),
                )
            )

            for requirement in (
                image_plan
                .conditional_requirements
            ):
                if (
                    requirement.trigger
                    in active_triggers
                ):
                    active_requirements.append(
                        requirement
                    )

        return AndroidBootImageMutationAnalysis(
            planning=planning,
            requests=mutation_requests,
            evaluations=tuple(
                evaluations
            ),
            active_conditional_requirements=tuple(
                active_requirements
            ),
        )

    @classmethod
    def resolve_avb_requirements(
        cls,
        mutation_analysis: AndroidBootImageMutationAnalysis,
        *,
        provider_analysis: AndroidBootImageProviderAnalysis,
        signing_key_path: Path | None = None,
        signing_keys_by_partition: dict[
            str,
            Path,
        ] | None = None,
        output_root: Path,
    ) -> tuple[
        tuple[
            AndroidBootImageAvbResolution,
            ...,
        ],
        tuple[
            AndroidBootImageProviderInvocation,
            ...,
        ],
    ]:
        if not isinstance(
            mutation_analysis,
            AndroidBootImageMutationAnalysis,
        ):
            raise TypeError(
                "mutation_analysis must be an "
                "AndroidBootImageMutationAnalysis"
            )

        if not isinstance(
            provider_analysis,
            AndroidBootImageProviderAnalysis,
        ):
            raise TypeError(
                "provider_analysis must be an "
                "AndroidBootImageProviderAnalysis"
            )

        if (
            provider_analysis.mutation_analysis
            is not mutation_analysis
        ):
            raise ValueError(
                "AVB resolution must retain exact "
                "provider-analysis mutation identity"
            )

        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if signing_key_path is not None:
            if not isinstance(
                signing_key_path,
                Path,
            ):
                raise TypeError(
                    "signing_key_path must be a pathlib.Path or None"
                )

            if not signing_key_path.is_file():
                raise FileNotFoundError(
                    "AVB signing key is unavailable: "
                    f"{signing_key_path}"
                )

            signing_key_path = (
                signing_key_path
                .expanduser()
                .resolve()
            )

        resolutions = []
        provider_invocations = []

        for requirement in (
            mutation_analysis
            .active_conditional_requirements
        ):
            if (
                requirement.kind
                is not
                AndroidBootImageConditionalRequirementKind
                .AVB_REEVALUATION
            ):
                continue

            image_matches = tuple(
                image_plan
                for image_plan
                in mutation_analysis.planning.boot_images
                if (
                    image_plan.composition
                    is requirement.image
                )
            )

            if len(
                image_matches
            ) != 1:
                raise RuntimeError(
                    "active AVB requirement must resolve exactly "
                    "one boot-image plan by exact Composition identity; "
                    f"found {len(image_matches)}"
                )

            image_plan = image_matches[0]

            embedded_vbmeta_nodes = []

            for region in (
                image_plan
                .composition
                .avb_regions
            ):
                vbmeta = region.vbmeta

                if (
                    vbmeta is None
                    or (
                        vbmeta.source_kind
                        is not
                        AndroidBootImageAvbSourceKind
                        .EMBEDDED
                    )
                ):
                    continue

                if not any(
                    candidate is vbmeta
                    for candidate
                    in embedded_vbmeta_nodes
                ):
                    embedded_vbmeta_nodes.append(
                        vbmeta
                    )

            if len(
                embedded_vbmeta_nodes
            ) != 1:
                raise RuntimeError(
                    "active boot-image AVB reevaluation requires "
                    "exactly one embedded VBMeta node; "
                    f"found {len(embedded_vbmeta_nodes)} "
                    f"for {image_plan.container_kind}"
                )

            embedded_vbmeta = (
                embedded_vbmeta_nodes[0]
            )

            partition_name = (
                image_plan
                .composition
                .image
                .image
                .partition
                .name
            )

            hash_descriptors = tuple(
                descriptor.descriptor
                for descriptor
                in embedded_vbmeta.descriptors
                if (
                    descriptor.kind
                    is AndroidBootImageAvbDescriptorKind.HASH
                    and isinstance(
                        descriptor.descriptor,
                        AndroidParsedAvbHashDescriptor,
                    )
                    and (
                        descriptor.descriptor.partition_name
                        == partition_name
                    )
                )
            )

            if len(
                hash_descriptors
            ) != 1:
                raise RuntimeError(
                    "active boot-image AVB reevaluation requires "
                    "exactly one embedded hash descriptor for "
                    f"{partition_name}; "
                    f"found {len(hash_descriptors)}"
                )

            property_descriptors = tuple(
                descriptor.descriptor
                for descriptor
                in embedded_vbmeta.descriptors
                if isinstance(
                    descriptor.descriptor,
                    AndroidParsedAvbPropertyDescriptor,
                )
            )

            parent_chain_references = tuple(
                reference
                for reference
                in (
                    image_plan
                    .composition
                    .avb_partition_references
                )
                if (
                    reference.descriptor.kind
                    is
                    AndroidBootImageAvbDescriptorKind
                    .CHAIN_PARTITION
                    and isinstance(
                        reference.descriptor.descriptor,
                        AndroidParsedAvbChainPartitionDescriptor,
                    )
                )
            )

            partition_size = (
                embedded_vbmeta
                .container_artifact
                .size_bytes
            )

            if (
                isinstance(
                    partition_size,
                    bool,
                )
                or not isinstance(
                    partition_size,
                    int,
                )
                or partition_size <= 0
            ):
                raise RuntimeError(
                    "active AVB reevaluation requires an exact "
                    "canonical partition image size"
                )

            contract = (
                AndroidBootImageAvbRegenerationContract(
                    requirement=requirement,
                    image_plan=image_plan,
                    embedded_vbmeta=embedded_vbmeta,
                    hash_descriptor=(
                        hash_descriptors[0]
                    ),
                    property_descriptors=(
                        property_descriptors
                    ),
                    parent_chain_references=(
                        parent_chain_references
                    ),
                    partition_size_bytes=(
                        partition_size
                    ),
                )
            )

            #
            # An explicit global signing_key_path remains a compatibility
            # override. Otherwise select the exact TreeForge-managed key
            # for this canonical partition.
            #
            resolved_signing_key_path = (
                signing_key_path
            )

            resolved_signing_policy = (
                AndroidBootImageAvbSigningPolicy
                .EXTERNAL_KEY
                if resolved_signing_key_path is not None
                else None
            )

            if (
                resolved_signing_key_path is None
                and signing_keys_by_partition is not None
            ):
                resolved_signing_key_path = (
                    signing_keys_by_partition
                    .get(
                        partition_name
                    )
                )

                if resolved_signing_key_path is not None:
                    resolved_signing_policy = (
                        AndroidBootImageAvbSigningPolicy
                        .DEVELOPMENT_KEY
                    )

            #
            # AVB algorithm type 0 is NONE. It has no private/public signing
            # identity. The canonical hash descriptor/VBMeta/footer still
            # have to be regenerated after content changes, but no signing
            # material or parent signing-identity propagation is required.
            #
            if (
                contract.algorithm_type
                == 0
            ):
                if (
                    resolved_signing_key_path
                    is not None
                ):
                    raise RuntimeError(
                        "canonical AVB algorithm NONE must not consume "
                        "private signing material for "
                        f"{partition_name}"
                    )

                if contract.factory_public_key:
                    raise RuntimeError(
                        "canonical AVB algorithm NONE unexpectedly carries "
                        "a public signing key for "
                        f"{partition_name}"
                    )

                resolutions.append(
                    AndroidBootImageAvbResolution(
                        contract=contract,
                        signing_policy=(
                            AndroidBootImageAvbSigningPolicy
                            .PRESERVE_FACTORY
                        ),
                        disposition=(
                            AndroidBootImageAvbResolutionDisposition
                            .REGENERATION_READY
                        ),
                        signing_key_path=None,
                        derived_public_key=None,
                        parent_trust_update_required=False,
                    )
                )

                continue

            #
            # Signed factory images prove the public signing identity, never
            # possession of the matching private key.
            #
            if resolved_signing_key_path is None:
                resolutions.append(
                    AndroidBootImageAvbResolution(
                        contract=contract,
                        signing_policy=(
                            AndroidBootImageAvbSigningPolicy
                            .PRESERVE_FACTORY
                        ),
                        disposition=(
                            AndroidBootImageAvbResolutionDisposition
                            .SIGNING_MATERIAL_REQUIRED
                        ),
                        signing_key_path=None,
                        derived_public_key=None,
                        parent_trust_update_required=None,
                    )
                )

                continue

            if resolved_signing_policy is None:
                raise RuntimeError(
                    "resolved AVB signing material has no "
                    "signing policy"
                )

            avbtool = cls._selected_provider(
                provider_analysis,
                owner=requirement,
                capability=(
                    AndroidBootImageProviderCapability
                    .AVB_REEVALUATION
                ),
            )

            key_root = (
                output_root
                / "avb"
                / "keys"
                / partition_name
            )

            key_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            derived_public_key_path = (
                key_root
                / "derived-public-key.avbpubkey"
            )

            extract_command = (
                str(avbtool.executable),
                "extract_public_key",
                "--key",
                str(resolved_signing_key_path),
                "--output",
                str(derived_public_key_path),
            )

            invocation = cls._run_provider(
                provider=avbtool,
                capability=(
                    AndroidBootImageProviderCapability
                    .AVB_REEVALUATION
                ),
                command=extract_command,
            )

            provider_invocations.append(
                invocation
            )

            if not derived_public_key_path.is_file():
                raise RuntimeError(
                    "avbtool extract_public_key completed without "
                    "producing an AVB public-key blob"
                )

            derived_public_key = (
                derived_public_key_path
                .read_bytes()
            )

            if not derived_public_key:
                raise RuntimeError(
                    "avbtool derived an empty AVB public-key blob"
                )

            #
            # The embedded child key and each parent chain descriptor
            # should describe the same canonical factory trust identity.
            # Refuse to continue if the factory evidence contradicts itself.
            #
            canonical_parent_keys = tuple(
                reference
                .descriptor
                .descriptor
                .public_key
                for reference
                in contract.parent_chain_references
            )

            if any(
                key != contract.factory_public_key
                for key
                in canonical_parent_keys
            ):
                raise RuntimeError(
                    "canonical AVB parent-chain public key does not "
                    "match the embedded factory signing identity"
                )

            parent_trust_update_required = any(
                derived_public_key != key
                for key
                in canonical_parent_keys
            )

            #
            # If no parent chain exists, there is no parent trust edge
            # to rewrite even when the signing identity differs.
            #
            if not canonical_parent_keys:
                parent_trust_update_required = False

            disposition = (
                AndroidBootImageAvbResolutionDisposition
                .PARENT_TRUST_UPDATE_REQUIRED
                if parent_trust_update_required
                else (
                    AndroidBootImageAvbResolutionDisposition
                    .REGENERATION_READY
                )
            )

            resolutions.append(
                AndroidBootImageAvbResolution(
                    contract=contract,
                    signing_policy=(
                        resolved_signing_policy
                    ),
                    disposition=disposition,
                    signing_key_path=resolved_signing_key_path,
                    derived_public_key=derived_public_key,
                    parent_trust_update_required=(
                        parent_trust_update_required
                    ),
                )
            )

        return (
            tuple(
                resolutions
            ),
            tuple(
                provider_invocations
            ),
        )

    @classmethod
    def _rewrite_parent_vbmeta_descriptors(
        cls,
        *,
        entries: tuple[
            tuple[
                AndroidBootImageAvbTrustChange,
                AndroidBootImageAvbPartitionReferenceComposition,
            ],
            ...,
        ],
        parent_vbmeta: AndroidBootImageAvbVbmetaInterpretation,
        output_root: Path,
    ) -> AndroidBootImageParentVbmetaRewrite:
        if (
            not isinstance(
                entries,
                tuple,
            )
            or not entries
        ):
            raise ValueError(
                "parent VBMeta rewrite requires a non-empty "
                "trust-change/reference batch"
            )

        if (
            parent_vbmeta.source_kind
            is not AndroidBootImageAvbSourceKind.STANDALONE
        ):
            raise RuntimeError(
                "parent trust rewrite requires a standalone "
                "canonical VBMeta image"
            )

        canonical_descriptors = (
            parent_vbmeta
            .vbmeta
            .metadata
            .descriptors
        )

        original_encoded = tuple(
            encode_avb_descriptor(
                descriptor
            )
            for descriptor
            in canonical_descriptors
        )

        rewritten_descriptors = list(
            canonical_descriptors
        )

        trust_changes = []
        chain_references = []
        descriptor_indexes = []
        original_chains = []
        rewritten_chains = []

        seen_indexes = set()

        for (
            trust_change,
            reference,
        ) in entries:
            if (
                reference.vbmeta
                is not parent_vbmeta
            ):
                raise ValueError(
                    "batched parent reference does not belong "
                    "to the selected parent VBMeta"
                )

            original_chain = (
                reference
                .descriptor
                .descriptor
            )

            if not isinstance(
                original_chain,
                AndroidParsedAvbChainPartitionDescriptor,
            ):
                raise TypeError(
                    "parent chain reference lost canonical "
                    "chain-descriptor identity"
                )

            matches = tuple(
                index
                for index, descriptor
                in enumerate(
                    canonical_descriptors
                )
                if descriptor is original_chain
            )

            if len(matches) != 1:
                raise RuntimeError(
                    "exact canonical parent chain descriptor must "
                    "occur once in the parent sequence; "
                    f"found {len(matches)}"
                )

            descriptor_index = (
                matches[0]
            )

            if descriptor_index in seen_indexes:
                raise RuntimeError(
                    "multiple AVB trust changes attempted to "
                    "rewrite the same canonical parent descriptor"
                )

            seen_indexes.add(
                descriptor_index
            )

            if (
                original_chain.public_key
                != trust_change.original_public_key
            ):
                raise RuntimeError(
                    "canonical parent descriptor public key does "
                    "not match the changed child factory identity"
                )

            rewritten_chain = (
                replace_chain_partition_public_key(
                    original_chain,
                    trust_change.replacement_public_key,
                )
            )

            rewritten_descriptors[
                descriptor_index
            ] = rewritten_chain

            trust_changes.append(
                trust_change
            )

            chain_references.append(
                reference
            )

            descriptor_indexes.append(
                descriptor_index
            )

            original_chains.append(
                original_chain
            )

            rewritten_chains.append(
                rewritten_chain
            )

        rewritten_encoded = tuple(
            encode_avb_descriptor(
                descriptor
            )
            for descriptor
            in rewritten_descriptors
        )

        changed_indexes = set(
            descriptor_indexes
        )

        unchanged_count = sum(
            1
            for index, (
                original_bytes,
                rewritten_bytes,
            )
            in enumerate(
                zip(
                    original_encoded,
                    rewritten_encoded,
                    strict=True,
                )
            )
            if (
                index not in changed_indexes
                and original_bytes == rewritten_bytes
            )
        )

        if (
            unchanged_count
            != (
                len(
                    canonical_descriptors
                )
                - len(
                    changed_indexes
                )
            )
        ):
            raise RuntimeError(
                "parent VBMeta batched rewrite changed an "
                "unrelated canonical descriptor"
            )

        for descriptor_index in (
            changed_indexes
        ):
            if (
                original_encoded[
                    descriptor_index
                ]
                == rewritten_encoded[
                    descriptor_index
                ]
            ):
                raise RuntimeError(
                    "requested parent chain rewrite did not "
                    "change descriptor bytes"
                )

        original_blob = b"".join(
            original_encoded
        )

        rewritten_blob = b"".join(
            rewritten_encoded
        )

        parent_partition_name = getattr(
            parent_vbmeta.partition,
            "name",
            None,
        )

        if (
            not isinstance(
                parent_partition_name,
                str,
            )
            or not parent_partition_name
        ):
            raise RuntimeError(
                "standalone parent VBMeta has no canonical "
                "partition name"
            )

        parent_root = (
            output_root
            / "vbmeta"
            / "parents"
            / parent_partition_name
        )

        parent_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            parent_root
            / "descriptors.bin"
        )

        output_path.write_bytes(
            rewritten_blob
        )

        return AndroidBootImageParentVbmetaRewrite(
            trust_changes=tuple(
                trust_changes
            ),
            parent_vbmeta=parent_vbmeta,
            chain_references=tuple(
                chain_references
            ),
            descriptor_indexes=tuple(
                descriptor_indexes
            ),
            original_descriptor_blob=(
                original_blob
            ),
            rewritten_descriptor_blob=(
                rewritten_blob
            ),
            original_chain_descriptors=tuple(
                original_chains
            ),
            rewritten_chain_descriptors=tuple(
                rewritten_chains
            ),
            output_path=output_path,
            unchanged_descriptor_count=(
                unchanged_count
            ),
        )

    @staticmethod
    def _recursive_avb_provider(
        provider_analysis: AndroidBootImageProviderAnalysis,
    ) -> AndroidBootImageProviderCandidate:
        providers = []

        seen = set()

        for selection in (
            provider_analysis
            .selections
        ):
            if (
                selection.capability
                is not
                AndroidBootImageProviderCapability
                .AVB_REEVALUATION
            ):
                continue

            identity = id(
                selection.provider
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            providers.append(
                selection.provider
            )

        if len(providers) != 1:
            raise RuntimeError(
                "recursive AVB propagation requires exactly one "
                "selected AVB provider; "
                f"found {len(providers)}"
            )

        return providers[0]


    @classmethod
    def _realize_parent_vbmeta(
        cls,
        *,
        rewrite: AndroidBootImageParentVbmetaRewrite,
        signing_key_path: Path,
        upstream_chain_references: tuple[
            AndroidBootImageAvbPartitionReferenceComposition,
            ...,
        ],
        provider_analysis: AndroidBootImageProviderAnalysis,
        output_root: Path,
    ) -> tuple[
        AndroidBootImageParentVbmetaRealization,
        tuple[
            AndroidBootImageProviderInvocation,
            ...,
        ],
    ]:
        if not isinstance(
            signing_key_path,
            Path,
        ):
            raise TypeError(
                "signing_key_path must be a pathlib.Path"
            )

        if not signing_key_path.is_file():
            raise FileNotFoundError(
                "parent VBMeta signing key is unavailable: "
                f"{signing_key_path}"
            )

        if not isinstance(
            upstream_chain_references,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageAvbPartitionReferenceComposition,
            )
            for value
            in upstream_chain_references
        ):
            raise TypeError(
                "upstream_chain_references contains an invalid "
                "canonical AVB reference"
            )

        parent_vbmeta = (
            rewrite.parent_vbmeta
        )

        if (
            parent_vbmeta.source_kind
            is not AndroidBootImageAvbSourceKind.STANDALONE
        ):
            raise RuntimeError(
                "initial parent VBMeta realization requires "
                "standalone VBMeta"
            )

        metadata = (
            parent_vbmeta
            .vbmeta
            .metadata
        )

        if (
            metadata.required_libavb_version_major
            != 1
        ):
            raise RuntimeError(
                "unsupported parent canonical libavb major "
                f"version: "
                f"{metadata.required_libavb_version_major}"
            )

        if metadata.public_key_metadata:
            raise RuntimeError(
                "parent VBMeta public-key metadata "
                "regeneration is not yet implemented"
            )

        avbtool = (
            cls._recursive_avb_provider(
                provider_analysis
            )
        )

        parent_partition_name = getattr(
            parent_vbmeta.partition,
            "name",
            None,
        )

        if (
            not isinstance(
                parent_partition_name,
                str,
            )
            or not parent_partition_name
        ):
            raise RuntimeError(
                "standalone parent VBMeta has no canonical "
                "partition name"
            )

        parent_root = (
            output_root
            / "vbmeta"
            / "parents"
            / parent_partition_name
        )

        parent_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        derived_public_key_path = (
            parent_root
            / "parent-derived-public-key.avbpubkey"
        )

        extract_invocation = cls._run_provider(
            provider=avbtool,
            capability=(
                AndroidBootImageProviderCapability
                .AVB_REEVALUATION
            ),
            command=(
                str(
                    avbtool.executable
                ),
                "extract_public_key",
                "--key",
                str(
                    signing_key_path
                ),
                "--output",
                str(
                    derived_public_key_path
                ),
            ),
        )

        if not derived_public_key_path.is_file():
            raise RuntimeError(
                "avbtool extract_public_key completed "
                "without producing parent public key"
            )

        derived_public_key = (
            derived_public_key_path
            .read_bytes()
        )

        if not derived_public_key:
            raise RuntimeError(
                "derived parent AVB public key is empty"
            )

        #
        # Initial implementation deliberately requires a descriptor-width
        # preserving rewrite. This lets the canonical standalone parent
        # VBMeta serve as a descriptor carrier after replacing exactly the
        # already-audited descriptor byte range.
        #
        if (
            len(
                rewrite.original_descriptor_blob
            )
            != len(
                rewrite.rewritten_descriptor_blob
            )
        ):
            raise RuntimeError(
                "initial parent VBMeta realization requires "
                "descriptor-width preservation"
            )

        canonical_artifact = (
            parent_vbmeta
            .container_artifact
        )

        source_path = getattr(
            canonical_artifact,
            "path",
            None,
        )

        if not isinstance(
            source_path,
            Path,
        ):
            raise RuntimeError(
                "canonical parent VBMeta artifact has no "
                "materializable filesystem path"
            )

        if not source_path.is_file():
            raise FileNotFoundError(
                "canonical parent VBMeta artifact is unavailable: "
                f"{source_path}"
            )

        carrier_path = (
            parent_root
            / "vbmeta.descriptor-carrier.img"
        )

        carrier_bytes = bytearray(
            source_path.read_bytes()
        )

        original_blob = (
            rewrite.original_descriptor_blob
        )

        rewritten_blob = (
            rewrite.rewritten_descriptor_blob
        )

        matches = []
        offset = 0

        while True:
            found = carrier_bytes.find(
                original_blob,
                offset,
            )

            if found < 0:
                break

            matches.append(
                found
            )

            offset = (
                found
                + 1
            )

        if len(
            matches
        ) != 1:
            raise RuntimeError(
                "canonical parent descriptor sequence must "
                "occur exactly once in standalone VBMeta bytes; "
                f"found {len(matches)}"
            )

        descriptor_offset = matches[0]

        carrier_bytes[
            descriptor_offset:
            descriptor_offset
            + len(
                original_blob
            )
        ] = rewritten_blob

        carrier_path.write_bytes(
            bytes(
                carrier_bytes
            )
        )

        if (
            carrier_path.read_bytes()[
                descriptor_offset:
                descriptor_offset
                + len(
                    rewritten_blob
                )
            ]
            != rewritten_blob
        ):
            raise RuntimeError(
                "parent VBMeta descriptor carrier "
                "did not retain rewritten descriptor bytes"
            )

        version_invocation = cls._run_provider(
            provider=avbtool,
            capability=(
                AndroidBootImageProviderCapability
                .AVB_REEVALUATION
            ),
            command=(
                str(
                    avbtool.executable
                ),
                "version",
            ),
        )

        provider_release_string = (
            version_invocation.stdout
            .decode(
                "utf-8",
                errors="strict",
            )
            .strip()
        )

        if (
            provider_release_string
            != metadata.release_string
        ):
            raise RuntimeError(
                "selected avbtool cannot reproduce "
                "the canonical parent VBMeta release string: "
                f"provider={provider_release_string!r}, "
                f"canonical={metadata.release_string!r}"
            )

        output_path = (
            parent_root
            / "vbmeta.img"
        )

        #
        # Do not use --include_descriptors_from_image here.
        #
        # avbtool intentionally deduplicates descriptors carrying a
        # partition_name and then emits them in sorted-key order. That
        # behavior is useful for normal Android build composition but it
        # violates Boot Image's stronger canonical-order invariant.
        #
        # Instead, load the selected avbtool provider directly, parse the
        # descriptor carrier in its existing order, and ask avbtool's own
        # VBMeta generator to sign that exact ordered descriptor list.
        #
        generator = r"""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

avbtool_path = Path(sys.argv[1])
carrier_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])
key_path = Path(sys.argv[4])

algorithm_name = sys.argv[5]
rollback_index = int(sys.argv[6])
flags = int(sys.argv[7])
rollback_index_location = int(sys.argv[8])
release_string = sys.argv[9]

loader = importlib.machinery.SourceFileLoader(
    "_treeforge_avbtool_provider",
    str(avbtool_path),
)

spec = importlib.util.spec_from_loader(
    loader.name,
    loader,
)

if spec is None:
    raise SystemExit(
        "unable to create selected avbtool provider module spec"
    )

module = importlib.util.module_from_spec(spec)

sys.modules[
    spec.name
] = module

loader.exec_module(
    module
)

avb = module.Avb()

carrier = module.ImageHandler(
    str(carrier_path),
    read_only=True,
)

(
    _footer,
    carrier_header,
    carrier_descriptors,
    _vbmeta_offset,
) = avb._parse_image(
    carrier
)

expected_blob = b"".join(
    descriptor.encode()
    for descriptor
    in carrier_descriptors
)

carrier_bytes = carrier_path.read_bytes()

aux_offset = (
    module.AvbVBMetaHeader.SIZE
    + carrier_header.authentication_data_block_size
)

descriptor_start = (
    aux_offset
    + carrier_header.descriptors_offset
)

descriptor_end = (
    descriptor_start
    + carrier_header.descriptors_size
)

carrier_descriptor_blob = carrier_bytes[
    descriptor_start:
    descriptor_end
]

if expected_blob != carrier_descriptor_blob:
    raise SystemExit(
        "avbtool parser did not preserve the descriptor "
        "carrier byte sequence"
    )

vbmeta_blob = avb._generate_vbmeta_blob(
    algorithm_name,
    str(key_path),
    None,
    list(
        carrier_descriptors
    ),
    None,
    None,
    rollback_index,
    flags,
    rollback_index_location,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    release_string,
    None,
    carrier_header.required_libavb_version_minor,
)

output_path.write_bytes(
    vbmeta_blob
)

print(
    "parent VBMeta generated from exact ordered descriptors"
)
"""

        generator_command = (
            sys.executable,
            "-c",
            generator,
            str(
                avbtool.executable
            ),
            str(
                carrier_path
            ),
            str(
                output_path
            ),
            str(
                signing_key_path
            ),
            cls._avb_algorithm_name(
                parent_vbmeta.algorithm_type
            ),
            str(
                parent_vbmeta.rollback_index
            ),
            str(
                parent_vbmeta.flags
            ),
            str(
                parent_vbmeta.rollback_index_location
            ),
            metadata.release_string,
        )

        completed = subprocess.run(
            generator_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        signing_invocation = (
            AndroidBootImageProviderInvocation(
                provider=avbtool,
                capability=(
                    AndroidBootImageProviderCapability
                    .AVB_REEVALUATION
                ),
                command=generator_command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )

        if completed.returncode != 0:
            stderr = completed.stderr.decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "parent VBMeta exact-order generation failed: "
                f"{stderr}"
            )

        if not output_path.is_file():
            raise RuntimeError(
                "exact-order parent VBMeta generation completed "
                "without producing vbmeta.img"
            )

        canonical_parent_size = (
            parent_vbmeta
            .container_artifact
            .size_bytes
        )

        if (
            not isinstance(
                canonical_parent_size,
                int,
            )
            or canonical_parent_size <= 0
        ):
            raise RuntimeError(
                "canonical standalone parent VBMeta has no "
                "valid container size"
            )

        generated_size = (
            output_path.stat().st_size
        )

        if generated_size > canonical_parent_size:
            raise RuntimeError(
                "regenerated parent VBMeta exceeds canonical "
                "standalone image size: "
                f"generated={generated_size}, "
                f"canonical={canonical_parent_size}"
            )

        if generated_size < canonical_parent_size:
            with output_path.open("ab") as stream:
                stream.write(
                    b"\x00"
                    * (
                        canonical_parent_size
                        - generated_size
                    )
                )

        if (
            output_path.stat().st_size
            != canonical_parent_size
        ):
            raise RuntimeError(
                "parent VBMeta canonical image sizing failed"
            )

        #
        # avbtool verify_image intentionally walks hash, hashtree, and
        # chained descriptors and therefore requires the complete sibling
        # partition image population. Parent-VBMeta realization has a
        # narrower responsibility: authenticate this regenerated VBMeta
        # object and prove that its exact derived descriptor population
        # was signed.
        #
        # Use avbtool's own parsing/signature primitives in a subprocess
        # so the cryptographic semantics still come from the selected
        # AOSP provider without recursively consuming child images here.
        #
        verifier = r"""
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

avbtool_path = Path(sys.argv[1])
image_path = Path(sys.argv[2])
key_path = Path(sys.argv[3])
expected_descriptors_path = Path(sys.argv[4])

loader = importlib.machinery.SourceFileLoader(
    "_treeforge_avbtool_provider",
    str(avbtool_path),
)

spec = importlib.util.spec_from_loader(
    loader.name,
    loader,
)

if spec is None:
    raise SystemExit(
        "unable to create selected avbtool provider module spec"
    )

module = importlib.util.module_from_spec(spec)

sys.modules[
    spec.name
] = module

loader.exec_module(
    module
)

image_bytes = image_path.read_bytes()

if len(image_bytes) < module.AvbVBMetaHeader.SIZE:
    raise SystemExit(
        "regenerated parent VBMeta is smaller than its header"
    )

header = module.AvbVBMetaHeader(
    image_bytes[
        :module.AvbVBMetaHeader.SIZE
    ]
)

vbmeta_size = (
    module.AvbVBMetaHeader.SIZE
    + header.authentication_data_block_size
    + header.auxiliary_data_block_size
)

if len(image_bytes) < vbmeta_size:
    raise SystemExit(
        "regenerated parent VBMeta is truncated"
    )

vbmeta_blob = image_bytes[:vbmeta_size]

if not module.verify_vbmeta_signature(
    header,
    vbmeta_blob,
):
    raise SystemExit(
        "regenerated parent VBMeta signature verification failed"
    )

expected_public_key = bytes(
    module.RSAPublicKey(
        str(key_path)
    ).encode()
)

aux_offset = (
    module.AvbVBMetaHeader.SIZE
    + header.authentication_data_block_size
)

public_key_start = (
    aux_offset
    + header.public_key_offset
)

public_key_end = (
    public_key_start
    + header.public_key_size
)

embedded_public_key = bytes(
    image_bytes[
        public_key_start:
        public_key_end
    ]
)

if embedded_public_key != expected_public_key:
    raise SystemExit(
        "regenerated parent VBMeta embedded public key does not "
        "match the explicit parent signing key"
    )

descriptor_start = (
    aux_offset
    + header.descriptors_offset
)

descriptor_end = (
    descriptor_start
    + header.descriptors_size
)

actual_descriptors = bytes(
    image_bytes[
        descriptor_start:
        descriptor_end
    ]
)

expected_descriptors = (
    expected_descriptors_path
    .read_bytes()
)

if actual_descriptors != expected_descriptors:
    raise SystemExit(
        "regenerated parent VBMeta descriptor population does not "
        "exactly match TreeForge's rewritten descriptor blob"
    )

print(
    "parent VBMeta signature/key/descriptors verified"
)
"""

        verifier_command = (
            sys.executable,
            "-c",
            verifier,
            str(
                avbtool.executable
            ),
            str(
                output_path
            ),
            str(
                signing_key_path
            ),
            str(
                rewrite.output_path
            ),
        )

        completed = subprocess.run(
            verifier_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        verification_invocation = (
            AndroidBootImageProviderInvocation(
                provider=avbtool,
                capability=(
                    AndroidBootImageProviderCapability
                    .AVB_REEVALUATION
                ),
                command=verifier_command,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )

        if completed.returncode != 0:
            stderr = completed.stderr.decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "parent VBMeta authentication verification failed: "
                f"{stderr}"
            )

        size_bytes, digest = (
            cls._file_identity(
                output_path
            )
        )

        factory_identity_preserved = (
            derived_public_key
            == parent_vbmeta.public_key
        )

        if factory_identity_preserved:
            trust_disposition = (
                AndroidBootImageParentVbmetaTrustDisposition
                .FACTORY_SIGNING_IDENTITY_PRESERVED
            )

        elif upstream_chain_references:
            trust_disposition = (
                AndroidBootImageParentVbmetaTrustDisposition
                .REPLACEMENT_SIGNING_IDENTITY
            )

        else:
            trust_disposition = (
                AndroidBootImageParentVbmetaTrustDisposition
                .ROOT_TRUST_UNRESOLVED
            )

        realization = (
            AndroidBootImageParentVbmetaRealization(
                rewrite=rewrite,
                signing_key_path=(
                    signing_key_path
                ),
                derived_public_key=(
                    derived_public_key
                ),
                output_path=(
                    output_path
                ),
                size_bytes=(
                    size_bytes
                ),
                content_sha256=(
                    digest
                ),
                verification_complete=True,
                trust_disposition=(
                    trust_disposition
                ),
                upstream_chain_references=(
                    upstream_chain_references
                ),
            )
        )

        return (
            realization,
            (
                extract_invocation,
                version_invocation,
                signing_invocation,
                verification_invocation,
            ),
        )

    @staticmethod
    def _avb_algorithm_name(
        algorithm_type: int,
    ) -> str:
        names = {
            0: "NONE",
            1: "SHA256_RSA2048",
            2: "SHA256_RSA4096",
            3: "SHA256_RSA8192",
            4: "SHA512_RSA2048",
            5: "SHA512_RSA4096",
            6: "SHA512_RSA8192",
        }

        try:
            return names[
                algorithm_type
            ]
        except KeyError as exc:
            raise RuntimeError(
                "unsupported canonical AVB algorithm type: "
                f"{algorithm_type}"
            ) from exc

    @classmethod
    def _finalize_boot_image_avb(
        cls,
        *,
        rebuilt: AndroidBootImageBootImageRealization,
        resolution: AndroidBootImageAvbResolution,
        provider_analysis: AndroidBootImageProviderAnalysis,
        output_root: Path,
    ) -> tuple[
        AndroidBootImageBootImageRealization,
        tuple[
            AndroidBootImageProviderInvocation,
            ...,
        ],
    ]:
        contract = resolution.contract

        if (
            rebuilt.image_plan
            is not contract.image_plan
        ):
            raise ValueError(
                "AVB finalization must retain exact "
                "boot-image plan identity"
            )

        unsigned = (
            contract.algorithm_type
            == 0
        )

        if unsigned:
            if (
                resolution.signing_policy
                is not
                AndroidBootImageAvbSigningPolicy
                .PRESERVE_FACTORY
            ):
                raise ValueError(
                    "algorithm-NONE AVB finalization must preserve the "
                    "canonical unsigned signing policy"
                )

            if (
                resolution.disposition
                is not
                AndroidBootImageAvbResolutionDisposition
                .REGENERATION_READY
            ):
                raise ValueError(
                    "algorithm-NONE AVB finalization requires a "
                    "regeneration-ready resolution"
                )

            if (
                resolution.signing_key_path
                is not None
                or resolution.derived_public_key
                is not None
            ):
                raise ValueError(
                    "algorithm-NONE AVB finalization must not carry "
                    "signing material"
                )

        else:
            if (
                resolution.signing_policy
                not in {
                    AndroidBootImageAvbSigningPolicy
                    .EXTERNAL_KEY,
                    AndroidBootImageAvbSigningPolicy
                    .DEVELOPMENT_KEY,
                }
            ):
                raise ValueError(
                    "signed AVB finalization requires resolved "
                    "private signing material"
                )

            if (
                resolution.disposition
                not in {
                    AndroidBootImageAvbResolutionDisposition
                    .REGENERATION_READY,
                    AndroidBootImageAvbResolutionDisposition
                    .PARENT_TRUST_UPDATE_REQUIRED,
                }
            ):
                raise ValueError(
                    "signed AVB finalization requires a realizable "
                    "AVB resolution"
                )

        signing_key = (
            resolution.signing_key_path
        )

        if (
            not unsigned
            and signing_key is None
        ):
            raise RuntimeError(
                "signed AVB finalization has no signing key"
            )

        if rebuilt.avb_complete:
            raise RuntimeError(
                "boot image is already AVB-complete"
            )

        if (
            contract.required_libavb_version_major
            != 1
        ):
            raise RuntimeError(
                "unsupported canonical libavb major version: "
                f"{contract.required_libavb_version_major}"
            )

        if contract.public_key_metadata:
            raise RuntimeError(
                "AVB public-key metadata regeneration "
                "is not yet implemented"
            )

        if (
            contract.descriptor_flags
            not in (0, 1)
        ):
            raise RuntimeError(
                "unsupported canonical AVB hash-descriptor flags: "
                f"{contract.descriptor_flags}"
            )

        avbtool = cls._selected_provider(
            provider_analysis,
            owner=contract.requirement,
            capability=(
                AndroidBootImageProviderCapability
                .AVB_REEVALUATION
            ),
        )

        image_root = (
            output_root
            / "images"
            / rebuilt.image_plan.container_kind
        )

        image_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        final_path = (
            image_root
            / (
                f"{rebuilt.image_plan.container_kind}"
                ".img"
            )
        )

        copy2(
            rebuilt.output_path,
            final_path,
        )

        version_invocation = cls._run_provider(
            provider=avbtool,
            capability=(
                AndroidBootImageProviderCapability
                .AVB_REEVALUATION
            ),
            command=(
                str(avbtool.executable),
                "version",
            ),
        )

        provider_release_string = (
            version_invocation.stdout
            .decode(
                "utf-8",
                errors="strict",
            )
            .strip()
        )

        if (
            provider_release_string
            != contract.release_string
        ):
            raise RuntimeError(
                "selected avbtool cannot reproduce the canonical "
                "VBMeta release string: "
                f"provider={provider_release_string!r}, "
                f"canonical={contract.release_string!r}"
            )

        command = [
            str(avbtool.executable),
            "add_hash_footer",
            "--image",
            str(final_path),
            "--partition_size",
            str(
                contract.partition_size_bytes
            ),
            "--partition_name",
            contract.partition_name,
            "--hash_algorithm",
            contract.hash_algorithm,
            "--salt",
            contract.salt.hex(),
            "--algorithm",
            cls._avb_algorithm_name(
                contract.algorithm_type
            ),
            "--rollback_index",
            str(
                contract.rollback_index
            ),
            "--rollback_index_location",
            str(
                contract.rollback_index_location
            ),
            "--flags",
            str(
                contract.vbmeta_flags
            ),
        ]

        if not unsigned:
            assert signing_key is not None

            algorithm_index = (
                command.index(
                    "--algorithm"
                )
            )

            command[
                algorithm_index + 2:
                algorithm_index + 2
            ] = [
                "--key",
                str(
                    signing_key
                ),
            ]

        for prop in (
            contract.property_descriptors
        ):
            command.extend(
                (
                    "--prop",
                    f"{prop.key}:{prop.value}",
                )
            )

        if contract.descriptor_flags == 1:
            command.append(
                "--do_not_use_ab"
            )

        signing_invocation = cls._run_provider(
            provider=avbtool,
            capability=(
                AndroidBootImageProviderCapability
                .AVB_REEVALUATION
            ),
            command=tuple(
                command
            ),
        )

        if not final_path.is_file():
            raise RuntimeError(
                "avbtool add_hash_footer completed "
                "without producing the final image"
            )

        final_size = (
            final_path.stat().st_size
        )

        if (
            final_size
            != contract.partition_size_bytes
        ):
            raise RuntimeError(
                "AVB-finalized image does not match "
                "canonical partition size: "
                f"{final_size} != "
                f"{contract.partition_size_bytes}"
            )

        verify_command_values = [
            str(
                avbtool.executable
            ),
            "verify_image",
            "--image",
            str(
                final_path
            ),
        ]

        if not unsigned:
            assert signing_key is not None

            verify_command_values.extend(
                (
                    "--key",
                    str(
                        signing_key
                    ),
                )
            )

        verify_command = tuple(
            verify_command_values
        )

        verification_invocation = (
            cls._run_provider(
                provider=avbtool,
                capability=(
                    AndroidBootImageProviderCapability
                    .AVB_REEVALUATION
                ),
                command=verify_command,
            )
        )

        size_bytes, digest = (
            cls._file_identity(
                final_path
            )
        )

        finalized = (
            AndroidBootImageBootImageRealization(
                image_plan=rebuilt.image_plan,
                provider=rebuilt.provider,
                verification_provider=(
                    rebuilt.verification_provider
                ),
                output_path=final_path,
                size_bytes=size_bytes,
                content_sha256=digest,
                avb_complete=True,
                parent_trust_complete=(
                    not bool(
                        resolution
                        .parent_trust_update_required
                    )
                ),
            )
        )

        return (
            finalized,
            (
                version_invocation,
                signing_invocation,
                verification_invocation,
            ),
        )

    @staticmethod
    def _run_provider(
        *,
        provider: AndroidBootImageProviderCandidate,
        capability: AndroidBootImageProviderCapability,
        command: tuple[str, ...],
    ) -> AndroidBootImageProviderInvocation:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        invocation = AndroidBootImageProviderInvocation(
            provider=provider,
            capability=capability,
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

        if completed.returncode != 0:
            stderr = completed.stderr.decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "Boot Image provider execution failed: "
                f"{provider.name}: {stderr}"
            )

        return invocation

    @staticmethod
    def _selected_provider(
        provider_analysis: AndroidBootImageProviderAnalysis,
        *,
        owner: object,
        capability: AndroidBootImageProviderCapability,
    ) -> AndroidBootImageProviderCandidate:
        matches = tuple(
            selection
            for selection
            in provider_analysis.selections
            if (
                selection.owner is owner
                and selection.capability is capability
            )
        )

        if len(matches) != 1:
            raise RuntimeError(
                "Boot Image execution requires exactly one provider "
                f"selection for {capability.value}; found {len(matches)}"
            )

        return matches[0].provider

    @classmethod
    def select_providers(
        cls,
        mutation_analysis: AndroidBootImageMutationAnalysis,
    ) -> AndroidBootImageProviderAnalysis:
        if not isinstance(
            mutation_analysis,
            AndroidBootImageMutationAnalysis,
        ):
            raise TypeError(
                "mutation_analysis must be an "
                "AndroidBootImageMutationAnalysis"
            )

        required: list[
            tuple[
                object,
                AndroidBootImageProviderCapability,
            ]
        ] = []

        for evaluation in (
            mutation_analysis.evaluations
        ):
            if not evaluation.content_changed:
                continue

            required.append(
                (
                    evaluation,
                    AndroidBootImageProviderCapability
                    .BOOT_IMAGE_RECONSTRUCTION,
                )
            )

            required.append(
                (
                    evaluation,
                    AndroidBootImageProviderCapability
                    .BOOT_IMAGE_INSPECTION,
                )
            )

        for requirement in (
            mutation_analysis
            .active_conditional_requirements
        ):
            if (
                requirement.kind
                is
                AndroidBootImageConditionalRequirementKind
                .AVB_REEVALUATION
            ):
                capability = (
                    AndroidBootImageProviderCapability
                    .AVB_REEVALUATION
                )

            elif (
                requirement.kind
                is
                AndroidBootImageConditionalRequirementKind
                .BOOT_SIGNATURE_REGENERATION
            ):
                capability = (
                    AndroidBootImageProviderCapability
                    .BOOT_SIGNATURE_REGENERATION
                )

            elif (
                requirement.kind
                is
                AndroidBootImageConditionalRequirementKind
                .VENDOR_RAMDISK_TABLE_REGENERATION
            ):
                capability = (
                    AndroidBootImageProviderCapability
                    .VENDOR_RAMDISK_TABLE_REGENERATION
                )

            else:
                raise RuntimeError(
                    "Boot Image provider selection encountered "
                    "an unsupported conditional requirement kind: "
                    f"{requirement.kind.value}"
                )

            required.append(
                (
                    requirement,
                    capability,
                )
            )

        #
        # Critical lazy-discovery invariant:
        #
        # Do not resolve PATH tools or touch bundled provider files at
        # all when there is no required mutation work.
        #
        if not required:
            return AndroidBootImageProviderAnalysis(
                mutation_analysis=mutation_analysis,
                candidates=(),
                selections=(),
            )

        required_capabilities = {
            capability
            for _, capability
            in required
        }

        candidates = []

        mkbootimg_capabilities = {
            AndroidBootImageProviderCapability
            .BOOT_IMAGE_RECONSTRUCTION,
            AndroidBootImageProviderCapability
            .VENDOR_RAMDISK_TABLE_REGENERATION,
        }

        image_tools_provider = None

        if (
            required_capabilities
            & (
                mkbootimg_capabilities
                | {
                    AndroidBootImageProviderCapability
                    .BOOT_IMAGE_INSPECTION
                }
            )
        ):
            image_tools_provider = (
                AndroidHostProviderBundleLoader.load(
                    android_host_provider_bundle_root(
                        name="android-image-tools",
                        release=(
                            ANDROID_15_HOST_PROVIDER_RELEASE
                        ),
                    )
                )
            )

        if (
            required_capabilities
            & mkbootimg_capabilities
        ):
            if image_tools_provider is None:
                raise RuntimeError(
                    "Boot Image Android image-tools provider "
                    "was not resolved"
                )

            executable = (
                image_tools_provider.executable_for(
                    "android-mkbootimg"
                )
            )

            candidates.append(
                AndroidBootImageProviderCandidate(
                    name="mkbootimg",
                    source=(
                        AndroidBootImageProviderSource
                        .TREEFORGE_BUNDLE
                    ),
                    executable=executable,
                    capabilities=(
                        AndroidBootImageProviderCapability
                        .BOOT_IMAGE_RECONSTRUCTION,
                        AndroidBootImageProviderCapability
                        .VENDOR_RAMDISK_TABLE_REGENERATION,
                    ),
                )
            )

        if (
            AndroidBootImageProviderCapability
            .BOOT_IMAGE_INSPECTION
            in required_capabilities
        ):
            if image_tools_provider is None:
                raise RuntimeError(
                    "Boot Image Android image-tools provider "
                    "was not resolved"
                )

            executable = (
                image_tools_provider.executable_for(
                    "android-unpack-bootimg"
                )
            )

            candidates.append(
                AndroidBootImageProviderCandidate(
                    name="unpack_bootimg",
                    source=(
                        AndroidBootImageProviderSource
                        .TREEFORGE_BUNDLE
                    ),
                    executable=executable,
                    capabilities=(
                        AndroidBootImageProviderCapability
                        .BOOT_IMAGE_INSPECTION,
                    ),
                )
            )

        avb_capabilities = {
            AndroidBootImageProviderCapability
            .AVB_REEVALUATION,
            AndroidBootImageProviderCapability
            .BOOT_SIGNATURE_REGENERATION,
        }

        if (
            required_capabilities
            & avb_capabilities
        ):
            avbtool_provider = (
                AndroidHostProviderBundleLoader.load(
                    android_host_provider_bundle_root(
                        name="avbtool",
                        release=(
                            ANDROID_15_HOST_PROVIDER_RELEASE
                        ),
                    )
                )
            )

            if not avbtool_provider.supports(
                "android-avbtool"
            ):
                raise RuntimeError(
                    "TreeForge avbtool provider lacks "
                    "android-avbtool capability"
                )

            candidates.append(
                AndroidBootImageProviderCandidate(
                    name="avbtool",
                    source=(
                        AndroidBootImageProviderSource
                        .TREEFORGE_BUNDLE
                    ),
                    executable=(
                        avbtool_provider.executable_for("android-avbtool")
                    ),
                    capabilities=(
                        AndroidBootImageProviderCapability
                        .AVB_REEVALUATION,
                        AndroidBootImageProviderCapability
                        .BOOT_SIGNATURE_REGENERATION,
                    ),
                )
            )

        if (
            AndroidBootImageProviderCapability
            .DTBO_RECONSTRUCTION
            in required_capabilities
        ):
            mkdtimg_provider = (
                AndroidHostProviderBundleLoader.load(
                    android_host_provider_bundle_root(
                        name="mkdtimg",
                        release=(
                            ANDROID_15_HOST_PROVIDER_RELEASE
                        ),
                    )
                )
            )

            if not mkdtimg_provider.supports(
                "android-mkdtimg"
            ):
                raise RuntimeError(
                    "TreeForge mkdtimg provider lacks "
                    "android-mkdtimg capability"
                )

            candidates.append(
                AndroidBootImageProviderCandidate(
                    name="mkdtimg",
                    source=(
                        AndroidBootImageProviderSource
                        .TREEFORGE_BUNDLE
                    ),
                    executable=(
                        mkdtimg_provider.executable_for("android-mkdtimg")
                    ),
                    capabilities=(
                        AndroidBootImageProviderCapability
                        .DTBO_RECONSTRUCTION,
                    ),
                )
            )

        selections = []

        for owner, capability in required:
            matches = tuple(
                candidate
                for candidate
                in candidates
                if candidate.supports(
                    capability
                )
            )

            if len(
                matches
            ) != 1:
                raise RuntimeError(
                    "Boot Image provider selection requires exactly "
                    "one capable provider for "
                    f"{capability.value}; found {len(matches)}"
                )

            selections.append(
                AndroidBootImageProviderSelection(
                    owner=owner,
                    capability=capability,
                    provider=matches[0],
                )
            )

        return AndroidBootImageProviderAnalysis(
            mutation_analysis=mutation_analysis,
            candidates=tuple(
                candidates
            ),
            selections=tuple(
                selections
            ),
        )

    @classmethod
    def _reconstruct_vendor_boot(
        cls,
        *,
        evaluations: tuple[
            AndroidBootImageMutationEvaluation,
            ...,
        ],
        provider_analysis: AndroidBootImageProviderAnalysis,
        output_root: Path,
    ) -> tuple[
        AndroidBootImageBootImageRealization,
        tuple[
            AndroidBootImageProviderInvocation,
            ...,
        ],
    ]:
        """
        Reconstruct one android_vendor_boot container from canonical factory
        structure while replacing exactly one complete vendor-ramdisk
        aggregate.

        TreeForge does not synthesize vendor_boot header/table semantics here.
        ``unpack_bootimg --format=mkbootimg -0`` derives the complete
        reconstruction argument vector from the canonical source image.
        TreeForge preserves that vector exactly, including empty string
        values, and replaces only the exact vendor ramdisk fragment path.

        The initial implementation intentionally supports only the structural
        case proven by canonical evidence:

          - one changed RAMDISK component;
          - one canonical vendor ramdisk-table entry;
          - that entry covers the complete ramdisk component;
          - unpack_bootimg emits one vendor ramdisk fragment.

        Multi-fragment aggregate mutation remains explicitly unsupported until
        Planning can express fragment-level mutation identity.
        """

        if not evaluations:
            raise ValueError(
                "vendor_boot reconstruction requires at least one "
                "changed mutation evaluation"
            )

        image_plan = evaluations[0].image_plan

        if any(
            evaluation.image_plan is not image_plan
            for evaluation
            in evaluations
        ):
            raise ValueError(
                "vendor_boot reconstruction evaluations must all "
                "belong to the same exact image plan"
            )

        canonical_image = (
            image_plan
            .composition
            .image
            .image
        )

        if (
            canonical_image.container_format
            != "android_vendor_boot"
        ):
            raise ValueError(
                "_reconstruct_vendor_boot requires an "
                "android_vendor_boot image plan"
            )

        changed_by_name = {}

        for evaluation in evaluations:
            if not evaluation.content_changed:
                raise ValueError(
                    "vendor_boot reconstruction received a "
                    "byte-identical mutation evaluation"
                )

            semantic_name = (
                evaluation
                .request
                .target
                .component
                .semantic_name
            )

            if semantic_name in changed_by_name:
                raise ValueError(
                    "vendor_boot reconstruction received duplicate "
                    f"changed component identity: {semantic_name}"
                )

            changed_by_name[semantic_name] = evaluation

        unexpected = (
            set(changed_by_name)
            - {
                "ramdisk",
                "bootconfig",
            }
        )

        if unexpected:
            raise ValueError(
                "vendor_boot reconstruction received unsupported "
                "changed components: "
                + ", ".join(sorted(unexpected))
            )

        ramdisk_evaluation = changed_by_name.get(
            "ramdisk"
        )

        if ramdisk_evaluation is None:
            raise ValueError(
                "vendor_boot reconstruction requires the complete "
                "ramdisk mutation"
            )

        bootconfig_evaluation = changed_by_name.get(
            "bootconfig"
        )

        component = (
            ramdisk_evaluation
            .request
            .target
            .component
        )

        if (
            component.role
            is not AndroidBootImageComponentRole.RAMDISK
        ):
            raise ValueError(
                "vendor_boot ramdisk mutation lost RAMDISK role"
            )

        replacement_path = (
            ramdisk_evaluation
            .request
            .replacement_path
        )

        if not replacement_path.is_file():
            raise FileNotFoundError(
                "vendor_boot replacement ramdisk is unavailable: "
                f"{replacement_path}"
            )

        bootconfig_replacement_path = None

        if bootconfig_evaluation is not None:
            bootconfig_component = (
                bootconfig_evaluation
                .request
                .target
                .component
            )

            if (
                bootconfig_component.role
                is not AndroidBootImageComponentRole.BOOTCONFIG
            ):
                raise ValueError(
                    "vendor_boot bootconfig mutation lost BOOTCONFIG role"
                )

            bootconfig_replacement_path = (
                bootconfig_evaluation
                .request
                .replacement_path
            )

            if not bootconfig_replacement_path.is_file():
                raise FileNotFoundError(
                    "vendor_boot replacement bootconfig is unavailable: "
                    f"{bootconfig_replacement_path}"
                )

        original_image = (
            canonical_image
            .partition
            .artifact
        )

        if not original_image.path.is_file():
            raise FileNotFoundError(
                "canonical vendor_boot image is unavailable: "
                f"{original_image.path}"
            )

        if (
            component.artifact.parent
            is not original_image
        ):
            raise RuntimeError(
                "vendor_boot ramdisk mutation target lost exact canonical "
                "image-parent identity"
            )

        if (
            bootconfig_evaluation is not None
            and (
                bootconfig_evaluation
                .request
                .target
                .component
                .artifact
                .parent
                is not original_image
            )
        ):
            raise RuntimeError(
                "vendor_boot bootconfig mutation target lost exact "
                "canonical image-parent identity"
            )

        #
        # Composition already owns the exact table-entry -> aggregate ramdisk
        # structural relationships. Do not reach back into Parsing and rebuild
        # that association during Realization.
        #
        vendor_ramdisk_entries = (
            image_plan
            .composition
            .vendor_ramdisk_entries
        )

        if len(
            vendor_ramdisk_entries
        ) != 1:
            raise RuntimeError(
                "complete vendor_boot ramdisk replacement currently "
                "requires exactly one composed vendor ramdisk fragment; "
                f"found {len(vendor_ramdisk_entries)}"
            )

        vendor_ramdisk_entry = (
            vendor_ramdisk_entries[
                0
            ]
        )

        table_entry = (
            vendor_ramdisk_entry
            .entry
        )

        original_ramdisk_size = (
            component
            .artifact
            .path
            .stat()
            .st_size
        )

        if (
            not vendor_ramdisk_entry
            .covers_complete_ramdisk_component
            or table_entry.ramdisk_offset
            != 0
            or table_entry.ramdisk_size
            != original_ramdisk_size
        ):
            raise RuntimeError(
                "canonical vendor ramdisk entry does not cover "
                "the complete selected ramdisk component"
            )

        mkbootimg = cls._selected_provider(
            provider_analysis,
            owner=ramdisk_evaluation,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_RECONSTRUCTION
            ),
        )

        unpack_bootimg = cls._selected_provider(
            provider_analysis,
            owner=ramdisk_evaluation,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_INSPECTION
            ),
        )

        image_root = (
            output_root
            / "images"
            / image_plan.container_kind
        )

        image_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        reconstruction_root = (
            output_root
            / "reconstruction"
            / image_plan.container_kind
        )

        reconstruction_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        #
        # First derive the exact mkbootimg argument vector from the canonical
        # factory image. Empty NUL-delimited values are significant and must
        # remain present.
        #
        derive_command = (
            str(
                unpack_bootimg.executable
            ),
            "--boot_img",
            str(
                original_image.path
            ),
            "--out",
            str(
                reconstruction_root
            ),
            "--format=mkbootimg",
            "-0",
        )

        derive_invocation = cls._run_provider(
            provider=unpack_bootimg,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_INSPECTION
            ),
            command=derive_command,
        )

        raw_parts = (
            derive_invocation
            .stdout
            .split(
                b"\0"
            )
        )

        if (
            raw_parts
            and raw_parts[-1] == b""
        ):
            raw_parts = (
                raw_parts[
                    :-1
                ]
            )

        arguments = [
            value.decode(
                "utf-8",
                errors="strict",
            )
            for value
            in raw_parts
        ]

        if not arguments:
            raise RuntimeError(
                "unpack_bootimg produced no vendor_boot "
                "mkbootimg arguments"
            )

        header_version_indices = tuple(
            index
            for index, value
            in enumerate(
                arguments
            )
            if (
                value
                == "--header_version"
            )
        )

        if len(
            header_version_indices
        ) != 1:
            raise RuntimeError(
                "canonical vendor_boot reconstruction requires exactly "
                "one --header_version argument"
            )

        header_index = (
            header_version_indices[
                0
            ]
        )

        if (
            header_index + 1
            >= len(
                arguments
            )
            or arguments[
                header_index + 1
            ]
            != "4"
        ):
            raise RuntimeError(
                "initial vendor_boot reconstruction currently requires "
                "canonical header version 4"
            )

        fragment_indices = tuple(
            index
            for index, value
            in enumerate(
                arguments
            )
            if (
                value
                == "--vendor_ramdisk_fragment"
            )
        )

        if len(
            fragment_indices
        ) != 1:
            raise RuntimeError(
                "complete vendor_boot ramdisk replacement currently "
                "requires exactly one factory-derived "
                "--vendor_ramdisk_fragment argument; "
                f"found {len(fragment_indices)}"
            )

        fragment_index = (
            fragment_indices[
                0
            ]
        )

        if (
            fragment_index + 1
            >= len(
                arguments
            )
        ):
            raise RuntimeError(
                "factory-derived --vendor_ramdisk_fragment "
                "has no value"
            )

        #
        # Preserve every factory-derived argument verbatim except the exact
        # vendor ramdisk payload path.
        #
        arguments[
            fragment_index + 1
        ] = str(
            replacement_path
        )

        if (
            bootconfig_replacement_path
            is not None
        ):
            bootconfig_indices = tuple(
                index
                for index, value
                in enumerate(arguments)
                if value == "--vendor_bootconfig"
            )

            if len(bootconfig_indices) != 1:
                raise RuntimeError(
                    "authorized vendor_boot bootconfig mutation "
                    "requires exactly one factory-derived "
                    "--vendor_bootconfig argument; "
                    f"found {len(bootconfig_indices)}"
                )

            bootconfig_index = bootconfig_indices[0]

            if (
                bootconfig_index + 1
                >= len(arguments)
            ):
                raise RuntimeError(
                    "factory-derived --vendor_bootconfig "
                    "has no value"
                )

            arguments[
                bootconfig_index + 1
            ] = str(
                bootconfig_replacement_path
            )

        output_path = (
            image_root
            / (
                f"{image_plan.container_kind}"
                ".pre-avb.img"
            )
        )

        output_path.unlink(
            missing_ok=True
        )

        build_command = (
            str(
                mkbootimg.executable
            ),
            *arguments,
            "--vendor_boot",
            str(
                output_path
            ),
        )

        build_invocation = cls._run_provider(
            provider=mkbootimg,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_RECONSTRUCTION
            ),
            command=build_command,
        )

        if not output_path.is_file():
            raise RuntimeError(
                "mkbootimg completed without producing "
                "vendor_boot output"
            )

        #
        # Inspect the newly reconstructed container through the independent
        # provider. Do not trust successful mkbootimg exit alone.
        #
        verification_root = (
            output_root
            / "verification"
            / image_plan.container_kind
        )

        verification_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        verify_command = (
            str(
                unpack_bootimg.executable
            ),
            "--boot_img",
            str(
                output_path
            ),
            "--out",
            str(
                verification_root
            ),
            "--format=mkbootimg",
            "-0",
        )

        verify_invocation = cls._run_provider(
            provider=unpack_bootimg,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_INSPECTION
            ),
            command=verify_command,
        )

        verify_parts = (
            verify_invocation
            .stdout
            .split(
                b"\0"
            )
        )

        if (
            verify_parts
            and verify_parts[-1] == b""
        ):
            verify_parts = (
                verify_parts[
                    :-1
                ]
            )

        verify_arguments = tuple(
            value.decode(
                "utf-8",
                errors="strict",
            )
            for value
            in verify_parts
        )

        verify_fragment_indices = tuple(
            index
            for index, value
            in enumerate(
                verify_arguments
            )
            if (
                value
                == "--vendor_ramdisk_fragment"
            )
        )

        if len(
            verify_fragment_indices
        ) != 1:
            raise RuntimeError(
                "rebuilt vendor_boot did not decode to exactly "
                "one vendor ramdisk fragment"
            )

        verify_fragment_index = (
            verify_fragment_indices[
                0
            ]
        )

        if (
            verify_fragment_index + 1
            >= len(
                verify_arguments
            )
        ):
            raise RuntimeError(
                "rebuilt vendor_boot fragment has no extracted path"
            )

        rebuilt_fragment_path = Path(
            verify_arguments[
                verify_fragment_index + 1
            ]
        )

        if not rebuilt_fragment_path.is_file():
            raise RuntimeError(
                "unpack_bootimg did not materialize rebuilt "
                "vendor ramdisk fragment: "
                f"{rebuilt_fragment_path}"
            )

        (
            replacement_size,
            replacement_sha256,
        ) = cls._file_identity(
            replacement_path
        )

        (
            rebuilt_fragment_size,
            rebuilt_fragment_sha256,
        ) = cls._file_identity(
            rebuilt_fragment_path
        )

        if (
            rebuilt_fragment_size
            != replacement_size
            or rebuilt_fragment_sha256
            != replacement_sha256
        ):
            raise RuntimeError(
                "rebuilt vendor_boot did not preserve the exact "
                "replacement ramdisk bytes"
            )

        if (
            bootconfig_replacement_path
            is not None
        ):
            verify_bootconfig_indices = tuple(
                index
                for index, value
                in enumerate(verify_arguments)
                if value == "--vendor_bootconfig"
            )

            if len(verify_bootconfig_indices) != 1:
                raise RuntimeError(
                    "rebuilt vendor_boot did not decode to exactly "
                    "one bootconfig payload"
                )

            verify_bootconfig_index = (
                verify_bootconfig_indices[0]
            )

            if (
                verify_bootconfig_index + 1
                >= len(verify_arguments)
            ):
                raise RuntimeError(
                    "rebuilt vendor_boot bootconfig has no extracted path"
                )

            rebuilt_bootconfig_path = Path(
                verify_arguments[
                    verify_bootconfig_index + 1
                ]
            )

            if not rebuilt_bootconfig_path.is_file():
                raise RuntimeError(
                    "unpack_bootimg did not materialize rebuilt "
                    "vendor bootconfig: "
                    f"{rebuilt_bootconfig_path}"
                )

            (
                expected_bootconfig_size,
                expected_bootconfig_sha256,
            ) = cls._file_identity(
                bootconfig_replacement_path
            )

            (
                rebuilt_bootconfig_size,
                rebuilt_bootconfig_sha256,
            ) = cls._file_identity(
                rebuilt_bootconfig_path
            )

            if (
                rebuilt_bootconfig_size
                != expected_bootconfig_size
                or rebuilt_bootconfig_sha256
                != expected_bootconfig_sha256
            ):
                raise RuntimeError(
                    "rebuilt vendor_boot did not preserve the exact "
                    "authorized replacement bootconfig bytes"
                )

        (
            output_size,
            output_sha256,
        ) = cls._file_identity(
            output_path
        )

        realization = (
            AndroidBootImageBootImageRealization(
                image_plan=image_plan,
                provider=mkbootimg,
                verification_provider=(
                    unpack_bootimg
                ),
                output_path=output_path,
                size_bytes=output_size,
                content_sha256=(
                    output_sha256
                ),
                avb_complete=False,
                parent_trust_complete=False,
            )
        )

        return (
            realization,
            (
                derive_invocation,
                build_invocation,
                verify_invocation,
            ),
        )


    @classmethod
    def _reconstruct_init_boot(
        cls,
        *,
        evaluation: AndroidBootImageMutationEvaluation,
        provider_analysis: AndroidBootImageProviderAnalysis,
        replacement_path: Path,
        output_root: Path,
    ) -> tuple[
        AndroidBootImageBootImageRealization,
        tuple[
            AndroidBootImageProviderInvocation,
            ...,
        ],
    ]:
        image_plan = evaluation.image_plan

        if image_plan.container_kind != "init_boot":
            raise ValueError(
                "_reconstruct_init_boot requires an init_boot image plan"
            )

        component = evaluation.request.target.component

        if component.role is not AndroidBootImageComponentRole.RAMDISK:
            raise ValueError(
                "initial init_boot reconstruction supports only "
                "ramdisk replacement"
            )

        if image_plan.composition.image.header_version != 4:
            raise ValueError(
                "initial init_boot reconstruction requires "
                "canonical header version 4"
            )

        if image_plan.composition.image.has_kernel:
            raise ValueError(
                "init_boot reconstruction unexpectedly contains a kernel"
            )

        if image_plan.composition.image.cmdline:
            raise ValueError(
                "initial init_boot reconstruction currently requires "
                "an empty canonical cmdline"
            )

        mkbootimg = cls._selected_provider(
            provider_analysis,
            owner=evaluation,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_RECONSTRUCTION
            ),
        )

        unpack_bootimg = cls._selected_provider(
            provider_analysis,
            owner=evaluation,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_INSPECTION
            ),
        )

        image_root = (
            output_root
            / "images"
            / image_plan.container_kind
        )

        image_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            image_root
            / "init_boot.pre-avb.img"
        )

        build_command = (
            str(mkbootimg.executable),
            "--ramdisk",
            str(replacement_path),
            "--header_version",
            "4",
            "--output",
            str(output_path),
        )

        build_invocation = cls._run_provider(
            provider=mkbootimg,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_RECONSTRUCTION
            ),
            command=build_command,
        )

        if not output_path.is_file():
            raise RuntimeError(
                "mkbootimg completed without producing init_boot output"
            )

        verification_root = (
            output_root
            / "verification"
            / image_plan.container_kind
        )

        verification_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        verify_command = (
            str(unpack_bootimg.executable),
            "--boot_img",
            str(output_path),
            "--out",
            str(verification_root),
            "--format=mkbootimg",
            "-0",
        )

        verify_invocation = cls._run_provider(
            provider=unpack_bootimg,
            capability=(
                AndroidBootImageProviderCapability
                .BOOT_IMAGE_INSPECTION
            ),
            command=verify_command,
        )

        arguments = tuple(
            value.decode(
                "utf-8",
                errors="strict",
            )
            for value
            in verify_invocation.stdout.split(b"\0")
            if value
        )

        def argument_value(flag: str) -> str | None:
            try:
                index = arguments.index(flag)
            except ValueError:
                return None

            if index + 1 >= len(arguments):
                raise RuntimeError(
                    f"unpack_bootimg emitted flag without value: {flag}"
                )

            return arguments[index + 1]

        header_version = argument_value(
            "--header_version"
        )

        if header_version != "4":
            raise RuntimeError(
                "rebuilt init_boot verification did not recover "
                "header version 4"
            )

        unpacked_kernel_value = argument_value(
            "--kernel"
        )

        if unpacked_kernel_value is not None:
            unpacked_kernel = Path(
                unpacked_kernel_value
            )

            if (
                unpacked_kernel.exists()
                and (
                    not unpacked_kernel.is_file()
                    or unpacked_kernel.stat().st_size != 0
                )
            ):
                raise RuntimeError(
                    "rebuilt init_boot unexpectedly contains "
                    "a non-empty kernel payload"
                )

        unpacked_ramdisk_value = argument_value(
            "--ramdisk"
        )

        if unpacked_ramdisk_value is None:
            raise RuntimeError(
                "rebuilt init_boot verification did not recover a ramdisk"
            )

        unpacked_ramdisk = Path(
            unpacked_ramdisk_value
        )

        if not unpacked_ramdisk.is_file():
            raise RuntimeError(
                "unpack_bootimg reported a missing ramdisk: "
                f"{unpacked_ramdisk}"
            )

        replacement_size, replacement_digest = (
            cls._file_identity(
                replacement_path
            )
        )

        unpacked_size, unpacked_digest = (
            cls._file_identity(
                unpacked_ramdisk
            )
        )

        if (
            unpacked_size != replacement_size
            or unpacked_digest != replacement_digest
        ):
            raise RuntimeError(
                "rebuilt init_boot ramdisk verification failed"
            )

        size_bytes, digest = cls._file_identity(
            output_path
        )

        rebuilt = AndroidBootImageBootImageRealization(
            image_plan=image_plan,
            provider=mkbootimg,
            verification_provider=unpack_bootimg,
            output_path=output_path,
            size_bytes=size_bytes,
            content_sha256=digest,
            avb_complete=False,
            parent_trust_complete=False,
        )

        return (
            rebuilt,
            (
                build_invocation,
                verify_invocation,
            ),
        )

    @classmethod
    def _materialize_exact(
        cls,
        *,
        artifact: ExtractedArtifact,
        destination: Path,
    ) -> tuple[
        int,
        str,
    ]:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            artifact.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise ValueError(
                "Boot Image exact realization currently requires "
                "regular-file artifacts"
            )

        source = artifact.path

        if not source.is_file():
            raise FileNotFoundError(
                "canonical Extraction artifact is unavailable: "
                f"{source}"
            )

        source_size = source.stat().st_size
        source_digest = cls._digest_file(
            source
        )

        if (
            artifact.size_bytes is not None
            and source_size
            != artifact.size_bytes
        ):
            raise RuntimeError(
                "canonical Extraction size evidence mismatch: "
                f"{source}"
            )

        if (
            artifact.content_sha256 is not None
            and source_digest
            != artifact.content_sha256
        ):
            raise RuntimeError(
                "canonical Extraction SHA-256 evidence mismatch: "
                f"{source}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        copy2(
            source,
            destination,
        )

        destination_size = (
            destination.stat().st_size
        )

        destination_digest = (
            cls._digest_file(
                destination
            )
        )

        if (
            destination_size
            != source_size
        ):
            raise RuntimeError(
                "Boot Image exact realization changed artifact size"
            )

        if (
            destination_digest
            != source_digest
        ):
            raise RuntimeError(
                "Boot Image exact realization changed artifact bytes"
            )

        return (
            destination_size,
            destination_digest,
        )

    def build(
        self,
        planning: AndroidBootImagePlanningResult,
        *,
        output_root: Path,
        mutation_requests: tuple[
            AndroidBootImageMutationRequest,
            ...,
        ] = (),
        avb_signing_key: Path | None = None,
        avb_signing_keys: tuple[
            tuple[
                str,
                Path,
            ],
            ...,
        ] = (),
        parent_vbmeta_signing_key: Path | None = None,
        vbmeta_signing_keys: tuple[
            tuple[
                str,
                Path,
            ],
            ...,
        ] = (),
    ) -> AndroidBootImageRealizationResult:
        if not isinstance(
            planning,
            AndroidBootImagePlanningResult,
        ):
            raise TypeError(
                "planning must be an AndroidBootImagePlanningResult"
            )

        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if parent_vbmeta_signing_key is not None:
            if not isinstance(
                parent_vbmeta_signing_key,
                Path,
            ):
                raise TypeError(
                    "parent_vbmeta_signing_key must be a "
                    "pathlib.Path or None"
                )

            parent_vbmeta_signing_key = (
                parent_vbmeta_signing_key
                .expanduser()
                .resolve()
            )

            if not parent_vbmeta_signing_key.is_file():
                raise FileNotFoundError(
                    "parent VBMeta signing key is unavailable: "
                    f"{parent_vbmeta_signing_key}"
                )

        if not isinstance(
            avb_signing_keys,
            tuple,
        ):
            raise TypeError(
                "avb_signing_keys must be a tuple"
            )

        avb_signing_key_by_partition = {}

        for value in avb_signing_keys:
            if (
                not isinstance(
                    value,
                    tuple,
                )
                or len(value) != 2
            ):
                raise TypeError(
                    "each avb_signing_keys entry must be "
                    "(partition_name, Path)"
                )

            partition_name, key_path = value

            if (
                not isinstance(
                    partition_name,
                    str,
                )
                or not partition_name
            ):
                raise ValueError(
                    "AVB signing-key partition name must be "
                    "a non-empty string"
                )

            if not isinstance(
                key_path,
                Path,
            ):
                raise TypeError(
                    "AVB signing-key path must be pathlib.Path"
                )

            key_path = (
                key_path
                .expanduser()
                .resolve()
            )

            if not key_path.is_file():
                raise FileNotFoundError(
                    "AVB signing key is unavailable: "
                    f"{key_path}"
                )

            if (
                partition_name
                in avb_signing_key_by_partition
            ):
                raise ValueError(
                    "duplicate AVB signing-key partition: "
                    f"{partition_name}"
                )

            avb_signing_key_by_partition[
                partition_name
            ] = key_path

        if not isinstance(
            vbmeta_signing_keys,
            tuple,
        ):
            raise TypeError(
                "vbmeta_signing_keys must be a tuple"
            )

        vbmeta_signing_key_by_partition = {}

        for value in vbmeta_signing_keys:
            if (
                not isinstance(
                    value,
                    tuple,
                )
                or len(value) != 2
            ):
                raise TypeError(
                    "each vbmeta_signing_keys entry must be "
                    "(partition_name, Path)"
                )

            partition_name, key_path = value

            if (
                not isinstance(
                    partition_name,
                    str,
                )
                or not partition_name
            ):
                raise ValueError(
                    "VBMeta signing-key partition name must be "
                    "a non-empty string"
                )

            if not isinstance(
                key_path,
                Path,
            ):
                raise TypeError(
                    "VBMeta signing-key path must be pathlib.Path"
                )

            key_path = (
                key_path
                .expanduser()
                .resolve()
            )

            if not key_path.is_file():
                raise FileNotFoundError(
                    "VBMeta signing key is unavailable: "
                    f"{key_path}"
                )

            if (
                partition_name
                in vbmeta_signing_key_by_partition
            ):
                raise ValueError(
                    "duplicate VBMeta signing-key partition: "
                    f"{partition_name}"
                )

            vbmeta_signing_key_by_partition[
                partition_name
            ] = key_path

        mutation_analysis = (
            self.analyze_mutations(
                planning,
                mutation_requests,
            )
        )

        provider_analysis = (
            self.select_providers(
                mutation_analysis,
            )
        )

        (
            avb_resolutions,
            avb_resolution_invocations,
        ) = self.resolve_avb_requirements(
            mutation_analysis,
            provider_analysis=provider_analysis,
            signing_key_path=avb_signing_key,
            signing_keys_by_partition=(
                avb_signing_key_by_partition
            ),
            output_root=output_root,
        )

        initial_trust_changes = []

        for resolution in (
            avb_resolutions
        ):
            if (
                resolution.parent_trust_update_required
                is not True
                or resolution.derived_public_key is None
            ):
                continue

            initial_trust_changes.append(
                AndroidBootImageAvbTrustChange(
                    target_partition=(
                        resolution
                        .contract
                        .partition_name
                    ),
                    original_public_key=(
                        resolution
                        .contract
                        .factory_public_key
                    ),
                    replacement_public_key=(
                        resolution
                        .derived_public_key
                    ),
                    parent_chain_references=(
                        resolution
                        .contract
                        .parent_chain_references
                    ),
                    source_resolution=(
                        resolution
                    ),
                )
            )

        parent_vbmeta_rewrites = []

        parent_vbmeta_realizations = []

        parent_vbmeta_signing_material_required = []

        parent_vbmeta_invocations = []

        pending_trust_changes = list(
            initial_trust_changes
        )

        processed_parent_vbmeta_ids = set()

        while pending_trust_changes:
            grouped_entries = {}

            parent_order = []

            for trust_change in (
                pending_trust_changes
            ):
                for reference in (
                    trust_change
                    .parent_chain_references
                ):
                    parent_vbmeta = (
                        reference.vbmeta
                    )

                    parent_identity = id(
                        parent_vbmeta
                    )

                    if (
                        parent_identity
                        not in grouped_entries
                    ):
                        grouped_entries[
                            parent_identity
                        ] = [
                            parent_vbmeta,
                            [],
                        ]

                        parent_order.append(
                            parent_identity
                        )

                    grouped_entries[
                        parent_identity
                    ][1].append(
                        (
                            trust_change,
                            reference,
                        )
                    )

            pending_trust_changes = []

            for parent_identity in (
                parent_order
            ):
                if (
                    parent_identity
                    in processed_parent_vbmeta_ids
                ):
                    raise RuntimeError(
                        "recursive AVB propagation revisited an "
                        "already-processed standalone parent; "
                        "canonical topology contains a cycle or "
                        "duplicate propagation path"
                    )

                processed_parent_vbmeta_ids.add(
                    parent_identity
                )

                (
                    parent_vbmeta,
                    entries,
                ) = grouped_entries[
                    parent_identity
                ]

                if any(
                    reference.vbmeta
                    is not parent_vbmeta
                    for _, reference
                    in entries
                ):
                    raise RuntimeError(
                        "recursive AVB parent grouping lost exact "
                        "VBMeta identity"
                    )

                rewrite = (
                    self._rewrite_parent_vbmeta_descriptors(
                        entries=tuple(
                            entries
                        ),
                        parent_vbmeta=(
                            parent_vbmeta
                        ),
                        output_root=(
                            output_root
                        ),
                    )
                )

                parent_vbmeta_rewrites.append(
                    rewrite
                )

                parent_partition_name = (
                    getattr(
                        parent_vbmeta.partition,
                        "name",
                        None,
                    )
                )

                if (
                    not isinstance(
                        parent_partition_name,
                        str,
                    )
                    or not parent_partition_name
                ):
                    raise RuntimeError(
                        "standalone parent VBMeta has no "
                        "canonical partition name"
                    )

                parent_signing_key = (
                    vbmeta_signing_key_by_partition
                    .get(
                        parent_partition_name
                    )
                )

                if (
                    parent_signing_key is None
                ):
                    parent_signing_key = (
                        parent_vbmeta_signing_key
                    )

                if (
                    parent_signing_key is None
                ):
                    #
                    # Keep the exact canonical rewrite as a first-class
                    # unresolved signing-material obligation. Never borrow
                    # another partition's private signing identity.
                    #
                    parent_vbmeta_signing_material_required.append(
                        rewrite
                    )

                    continue

                upstream_chain_references = (
                    planning
                    .composition
                    .avb_references_targeting(
                        parent_partition_name
                    )
                )

                if any(
                    reference.vbmeta
                    is parent_vbmeta
                    for reference
                    in upstream_chain_references
                ):
                    raise RuntimeError(
                        "canonical AVB topology contains a "
                        "self-referential standalone VBMeta chain"
                    )

                (
                    parent_realization,
                    parent_invocations,
                ) = self._realize_parent_vbmeta(
                    rewrite=rewrite,
                    signing_key_path=(
                        parent_signing_key
                    ),
                    upstream_chain_references=(
                        upstream_chain_references
                    ),
                    provider_analysis=(
                        provider_analysis
                    ),
                    output_root=(
                        output_root
                    ),
                )

                parent_vbmeta_realizations.append(
                    parent_realization
                )

                parent_vbmeta_invocations.extend(
                    parent_invocations
                )

                if (
                    parent_realization
                    .upstream_trust_update_required
                ):
                    pending_trust_changes.append(
                        AndroidBootImageAvbTrustChange(
                            target_partition=(
                                parent_partition_name
                            ),
                            original_public_key=(
                                parent_vbmeta
                                .public_key
                            ),
                            replacement_public_key=(
                                parent_realization
                                .derived_public_key
                            ),
                            parent_chain_references=(
                                upstream_chain_references
                            ),
                            source_parent_realization=(
                                parent_realization
                            ),
                        )
                    )

        post_avb_conditional_requirements = []

        planned_conditional_requirements = tuple(
            requirement
            for image_plan
            in planning.boot_images
            for requirement
            in image_plan.conditional_requirements
        )

        for parent_realization in (
            parent_vbmeta_realizations
        ):
            if not (
                parent_realization
                .bootloader_trust_anchor_required
            ):
                continue

            for origin_resolution in (
                parent_realization
                .origin_resolutions
            ):
                child_image = (
                    origin_resolution
                    .contract
                    .requirement
                    .image
                )

                matches = tuple(
                    requirement
                    for requirement
                    in planned_conditional_requirements
                    if (
                        requirement.image
                        is child_image
                        and (
                            requirement.kind
                            is
                            AndroidBootImageConditionalRequirementKind
                            .BOOTLOADER_TRUST_ANCHOR_UPDATE
                        )
                        and (
                            requirement.trigger
                            is
                            AndroidBootImageConditionalTrigger
                            .TOP_LEVEL_AVB_SIGNING_IDENTITY_CHANGED
                        )
                    )
                )

                if len(matches) != 1:
                    raise RuntimeError(
                        "top-level AVB signing-identity change requires "
                        "exactly one planned bootloader trust-anchor "
                        "requirement for each origin image; "
                        f"found {len(matches)}"
                    )

                requirement = (
                    matches[0]
                )

                if any(
                    candidate is requirement
                    for candidate
                    in post_avb_conditional_requirements
                ):
                    continue

                post_avb_conditional_requirements.append(
                    requirement
                )

        component_realizations = []

        for image_index, image in enumerate(
            planning.boot_images
        ):
            for component_index, plan in enumerate(
                image.component_plans
            ):
                artifact = (
                    plan.component.artifact
                )

                destination = (
                    output_root
                    / "components"
                    / (
                        f"{image_index:02d}-"
                        f"{image.container_kind}"
                    )
                    / (
                        f"{component_index:02d}-"
                        f"{plan.component.semantic_name}"
                    )
                )

                matching_evaluations = tuple(
                    evaluation
                    for evaluation
                    in mutation_analysis.evaluations
                    if evaluation.request.target is plan
                )

                if len(matching_evaluations) > 1:
                    raise RuntimeError(
                        "component plan has multiple mutation evaluations"
                    )

                if (
                    matching_evaluations
                    and matching_evaluations[0].content_changed
                ):
                    evaluation = matching_evaluations[0]

                    destination.parent.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    copy2(
                        evaluation.request.replacement_path,
                        destination,
                    )

                    size_bytes, digest = self._file_identity(
                        destination
                    )

                    if (
                        size_bytes
                        != evaluation.replacement_size_bytes
                        or digest
                        != evaluation.replacement_sha256
                    ):
                        raise RuntimeError(
                            "Boot Image mutation-input materialization "
                            "changed replacement bytes"
                        )

                    provider = (
                        AndroidBootImageRealizationProvider
                        .MUTATION_INPUT
                    )

                    mutated = True

                else:
                    size_bytes, digest = (
                        self._materialize_exact(
                            artifact=artifact,
                            destination=destination,
                        )
                    )

                    provider = (
                        AndroidBootImageRealizationProvider
                        .EXACT_ARTIFACT
                    )

                    mutated = False

                component_realizations.append(
                    AndroidBootImageComponentRealization(
                        plan=plan,
                        provider=provider,
                        output_path=destination,
                        size_bytes=size_bytes,
                        content_sha256=digest,
                        mutated=mutated,
                    )
                )

        provider_invocations = list(
            avb_resolution_invocations
        )

        provider_invocations.extend(
            parent_vbmeta_invocations
        )

        rewrite_by_reference_id = {}

        for rewrite in (
            parent_vbmeta_rewrites
        ):
            for reference in (
                rewrite.chain_references
            ):
                identity = id(
                    reference
                )

                if (
                    identity
                    in rewrite_by_reference_id
                ):
                    raise RuntimeError(
                        "canonical AVB reference was consumed by "
                        "multiple parent rewrite batches"
                    )

                rewrite_by_reference_id[
                    identity
                ] = rewrite

        realization_by_rewrite_id = {
            id(
                realization.rewrite
            ): realization
            for realization
            in parent_vbmeta_realizations
        }

        def parent_reference_chain_complete(
            reference,
            active_reference_ids=None,
        ):
            if active_reference_ids is None:
                active_reference_ids = set()

            reference_identity = id(
                reference
            )

            if (
                reference_identity
                in active_reference_ids
            ):
                raise RuntimeError(
                    "cycle detected while evaluating AVB parent "
                    "trust completion"
                )

            rewrite = (
                rewrite_by_reference_id
                .get(
                    reference_identity
                )
            )

            if rewrite is None:
                return False

            realization = (
                realization_by_rewrite_id
                .get(
                    id(
                        rewrite
                    )
                )
            )

            if realization is None:
                return False

            if (
                realization
                .parent_trust_complete
            ):
                return True

            if (
                realization
                .bootloader_trust_anchor_required
            ):
                return False

            if not (
                realization
                .upstream_trust_update_required
            ):
                return False

            next_active = set(
                active_reference_ids
            )

            next_active.add(
                reference_identity
            )

            return all(
                parent_reference_chain_complete(
                    upstream_reference,
                    next_active,
                )
                for upstream_reference
                in realization
                .upstream_chain_references
            )

        def resolution_parent_trust_complete(
            resolution,
        ):
            references = (
                resolution
                .contract
                .parent_chain_references
            )

            if not references:
                return True

            return all(
                parent_reference_chain_complete(
                    reference
                )
                for reference
                in references
            )

        rebuilt_boot_images = []
        rebuilt_image_plan_ids = set()

        for evaluation in mutation_analysis.evaluations:
            if not evaluation.content_changed:
                continue

            image_plan = evaluation.image_plan

            image_plan_identity = id(
                image_plan
            )

            if (
                image_plan_identity
                in rebuilt_image_plan_ids
            ):
                continue

            rebuilt_image_plan_ids.add(
                image_plan_identity
            )

            changed_in_image = tuple(
                candidate
                for candidate
                in mutation_analysis.evaluations
                if (
                    candidate.image_plan is image_plan
                    and candidate.content_changed
                )
            )

            if image_plan.container_kind == "init_boot":
                if len(changed_in_image) != 1:
                    raise RuntimeError(
                        "initial init_boot reconstruction supports "
                        "exactly one changed component"
                    )

                rebuilt, invocations = (
                    self._reconstruct_init_boot(
                        evaluation=evaluation,
                        provider_analysis=provider_analysis,
                        replacement_path=(
                            evaluation.request.replacement_path
                        ),
                        output_root=output_root,
                    )
                )

                provider_invocations.extend(
                    invocations
                )

                matching_avb_resolutions = tuple(
                    resolution
                    for resolution
                    in avb_resolutions
                    if (
                        resolution.contract.image_plan
                        is image_plan
                    )
                )

                if len(
                    matching_avb_resolutions
                ) != 1:
                    raise RuntimeError(
                        "rebuilt init_boot requires exactly one "
                        "AVB resolution by exact image-plan identity; "
                        f"found {len(matching_avb_resolutions)}"
                    )

                avb_resolution = (
                    matching_avb_resolutions[0]
                )

                if (
                    avb_resolution.signing_key_path
                    is not None
                ):
                    (
                        rebuilt,
                        avb_invocations,
                    ) = self._finalize_boot_image_avb(
                        rebuilt=rebuilt,
                        resolution=avb_resolution,
                        provider_analysis=provider_analysis,
                        output_root=output_root,
                    )

                    provider_invocations.extend(
                        avb_invocations
                    )

                    if (
                        avb_resolution
                        .parent_trust_update_required
                        is True
                    ):
                        parent_trust_complete = (
                            resolution_parent_trust_complete(
                                avb_resolution
                            )
                        )

                        rebuilt = (
                            AndroidBootImageBootImageRealization(
                                image_plan=(
                                    rebuilt.image_plan
                                ),
                                provider=(
                                    rebuilt.provider
                                ),
                                verification_provider=(
                                    rebuilt
                                    .verification_provider
                                ),
                                output_path=(
                                    rebuilt.output_path
                                ),
                                size_bytes=(
                                    rebuilt.size_bytes
                                ),
                                content_sha256=(
                                    rebuilt.content_sha256
                                ),
                                avb_complete=(
                                    rebuilt.avb_complete
                                ),
                                parent_trust_complete=(
                                    parent_trust_complete
                                ),
                            )
                        )

                rebuilt_boot_images.append(
                    rebuilt
                )

                continue

            if (
                image_plan
                .composition
                .image
                .image
                .container_format
                == "android_vendor_boot"
            ):
                rebuilt, invocations = (
                    self._reconstruct_vendor_boot(
                        evaluations=(
                            changed_in_image
                        ),
                        provider_analysis=(
                            provider_analysis
                        ),
                        output_root=(
                            output_root
                        ),
                    )
                )

                provider_invocations.extend(
                    invocations
                )

                matching_avb_resolutions = tuple(
                    resolution
                    for resolution
                    in avb_resolutions
                    if (
                        resolution
                        .contract
                        .image_plan
                        is image_plan
                    )
                )

                if len(
                    matching_avb_resolutions
                ) != 1:
                    raise RuntimeError(
                        "rebuilt vendor_boot requires exactly one "
                        "AVB resolution by exact image-plan identity; "
                        f"found {len(matching_avb_resolutions)}"
                    )

                avb_resolution = (
                    matching_avb_resolutions[
                        0
                    ]
                )

                if (
                    avb_resolution
                    .disposition
                    in {
                        AndroidBootImageAvbResolutionDisposition
                        .REGENERATION_READY,
                        AndroidBootImageAvbResolutionDisposition
                        .PARENT_TRUST_UPDATE_REQUIRED,
                    }
                ):
                    (
                        rebuilt,
                        avb_invocations,
                    ) = (
                        self
                        ._finalize_boot_image_avb(
                            rebuilt=rebuilt,
                            resolution=(
                                avb_resolution
                            ),
                            provider_analysis=(
                                provider_analysis
                            ),
                            output_root=(
                                output_root
                            ),
                        )
                    )

                    provider_invocations.extend(
                        avb_invocations
                    )

                rebuilt_boot_images.append(
                    rebuilt
                )

                continue

            raise RuntimeError(
                "Boot Image mutation provider execution is not yet "
                "implemented for boot-family image: "
                f"{image_plan.container_kind}"
            )

        dtbo_realizations = []

        for index, container in enumerate(
            planning.dtbo_containers
        ):
            artifact = container.container

            destination = (
                output_root
                / "dtbo"
                / (
                    f"{index:02d}-"
                    f"{artifact.path.name}"
                )
            )

            size_bytes, digest = (
                self._materialize_exact(
                    artifact=artifact,
                    destination=destination,
                )
            )

            dtbo_realizations.append(
                AndroidBootImageDtboRealization(
                    container=container,
                    provider=(
                        AndroidBootImageRealizationProvider
                        .EXACT_ARTIFACT
                    ),
                    output_path=destination,
                    size_bytes=size_bytes,
                    content_sha256=digest,
                    mutated=False,
                )
            )

        result = AndroidBootImageRealizationResult(
            planning=planning,
            mutation_analysis=mutation_analysis,
            provider_analysis=provider_analysis,
            avb_resolutions=avb_resolutions,
            parent_vbmeta_rewrites=tuple(
                parent_vbmeta_rewrites
            ),
            parent_vbmeta_realizations=tuple(
                parent_vbmeta_realizations
            ),
            parent_vbmeta_signing_material_required=tuple(
                parent_vbmeta_signing_material_required
            ),
            post_avb_conditional_requirements=tuple(
                post_avb_conditional_requirements
            ),
            provider_invocations=tuple(
                provider_invocations
            ),
            rebuilt_boot_images=tuple(
                rebuilt_boot_images
            ),
            components=tuple(
                component_realizations
            ),
            dtbo_containers=tuple(
                dtbo_realizations
            ),
        )

        if result.planning is not planning:
            raise RuntimeError(
                "Boot Image Realization must preserve exact "
                "Planning result identity"
            )

        if result.parsing is not planning.parsing:
            raise RuntimeError(
                "Boot Image Realization must preserve exact "
                "AndroidParsingResult identity"
            )

        if (
            len(
                result.components
            )
            != planning.component_plan_count
        ):
            raise RuntimeError(
                "Boot Image Realization component conservation failed"
            )

        if (
            len(
                result.dtbo_containers
            )
            != len(
                planning.dtbo_containers
            )
        ):
            raise RuntimeError(
                "Boot Image Realization DTBO conservation failed"
            )

        if result.mutation_request_count == 0:
            if result.mutated_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization "
                    "must not mutate artifacts"
                )

            if (
                result.active_conditional_requirement_count
                != 0
            ):
                raise RuntimeError(
                    "zero-mutation Boot Image Realization cannot "
                    "activate conditional requirements"
                )

            if (
                result.post_avb_conditional_requirements
            ):
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not activate "
                    "post-AVB requirements"
                )

            if result.provider_candidate_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "discover external providers"
                )

            if result.provider_selection_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "select external providers"
                )

            if result.provider_invocation_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "invoke external providers"
                )

            if result.avb_resolution_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "derive active AVB regeneration contracts"
                )

            if result.parent_vbmeta_rewrite_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "derive parent VBMeta rewrites"
                )

            if (
                result.parent_vbmeta_realization_count
                != 0
            ):
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "realize parent VBMeta images"
                )

            if (
                result
                .parent_vbmeta_signing_material_required_count
                != 0
            ):
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "derive parent VBMeta signing-material "
                    "requirements"
                )

            if result.rebuilt_boot_image_count != 0:
                raise RuntimeError(
                    "zero-mutation Boot Image Realization must not "
                    "reconstruct boot images"
                )

        if (
            tuple(
                id(
                    value
                )
                for value
                in result.evidence
            )
            != tuple(
                id(
                    value
                )
                for value
                in planning.evidence
            )
        ):
            raise RuntimeError(
                "Boot Image Realization must conserve every Planning "
                "evidence record in exact order and identity"
            )

        return result
