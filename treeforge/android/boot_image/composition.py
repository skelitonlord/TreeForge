from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.boot_image.models import (
    AndroidBootImageAvbDescriptorInterpretation,
    AndroidBootImageAvbRegionInterpretation,
    AndroidBootImageAvbVbmetaInterpretation,
    AndroidBootImageComponentRole,
    AndroidBootImageBootImageInterpretation,
    AndroidBootImageComponentInterpretation,
    AndroidBootImageDtboContainerInterpretation,
    AndroidBootImageDtboEntryInterpretation,
    AndroidBootImageRamdiskInterpretation,
)
from treeforge.android.boot_image.result import (
    AndroidBootImageInterpretationResult,
)
from treeforge.android.parsing.avb import (
    AndroidParsedAvbHashDescriptor,
)
from treeforge.android.parsing.boot.vendor_ramdisk_table import (
    ParsedVendorRamdiskTable,
    ParsedVendorRamdiskTableEntry,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


def _artifact_descends_from(
    artifact,
    ancestor,
) -> bool:
    """
    Return True only when canonical Extraction parent identity proves that
    ``artifact`` is ``ancestor`` or one of its descendants.
    """

    current = artifact

    seen = set()

    while current is not None:
        identity = id(
            current
        )

        if identity in seen:
            raise ValueError(
                "canonical Extraction artifact ancestry contains a cycle"
            )

        seen.add(
            identity
        )

        if current is ancestor:
            return True

        current = current.parent

    return False


def _artifact_int_fact(
    artifact,
    name: str,
) -> int:
    """
    Return one required canonical integer Extraction fact.

    Physical boot-component offsets remain Extraction-owned. Composition
    consumes those already-canonical facts only to establish byte-range
    relationships between interpreted objects.
    """

    matches = tuple(
        fact.value
        for fact
        in artifact.facts
        if fact.name == name
    )

    if len(
        matches
    ) != 1:
        raise ValueError(
            "canonical Extraction artifact must retain exactly one "
            f"{name!r} fact"
        )

    value = matches[0]

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
            f"canonical Extraction fact {name!r} must be a "
            "non-negative integer"
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageVendorRamdiskEntryComposition:
    """
    Structural association between one canonical vendor-ramdisk-table entry
    and the exact byte range it describes inside the sibling ramdisk
    component.

    The table remains authoritative for fragment metadata. The Extraction
    ramdisk artifact remains authoritative for the physical payload bytes.
    """

    table: ParsedVendorRamdiskTable

    entry: ParsedVendorRamdiskTableEntry

    ramdisk_component: AndroidBootImageComponentInterpretation

    start_offset_bytes: int
    end_offset_bytes: int

    covers_complete_ramdisk_component: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.table,
            ParsedVendorRamdiskTable,
        ):
            raise TypeError(
                "table must be a ParsedVendorRamdiskTable"
            )

        if not isinstance(
            self.entry,
            ParsedVendorRamdiskTableEntry,
        ):
            raise TypeError(
                "entry must be a ParsedVendorRamdiskTableEntry"
            )

        if not any(
            candidate is self.entry
            for candidate
            in self.table.entries
        ):
            raise ValueError(
                "vendor ramdisk entry composition must retain "
                "exact table-entry identity"
            )

        if not isinstance(
            self.ramdisk_component,
            AndroidBootImageComponentInterpretation,
        ):
            raise TypeError(
                "ramdisk_component must be an "
                "AndroidBootImageComponentInterpretation"
            )

        if (
            self.ramdisk_component.role
            is not AndroidBootImageComponentRole.RAMDISK
        ):
            raise ValueError(
                "vendor ramdisk table entries may only compose "
                "against a ramdisk component"
            )

        expected_start = (
            self.entry.ramdisk_offset
        )

        expected_end = (
            self.entry.ramdisk_offset
            + self.entry.ramdisk_size
        )

        if (
            self.start_offset_bytes
            != expected_start
        ):
            raise ValueError(
                "vendor ramdisk entry composition start offset "
                "must equal the canonical table entry offset"
            )

        if (
            self.end_offset_bytes
            != expected_end
        ):
            raise ValueError(
                "vendor ramdisk entry composition end offset "
                "must equal offset + canonical table entry size"
            )

        component_size = (
            self.ramdisk_component
            .artifact
            .size_bytes
        )

        if (
            isinstance(
                component_size,
                bool,
            )
            or not isinstance(
                component_size,
                int,
            )
        ):
            raise ValueError(
                "vendor ramdisk component must retain an exact "
                "physical size for table-range composition"
            )

        if (
            self.start_offset_bytes < 0
            or self.end_offset_bytes
            < self.start_offset_bytes
            or self.end_offset_bytes
            > component_size
        ):
            raise ValueError(
                "vendor ramdisk table entry range exceeds the "
                "canonical ramdisk component"
            )

        expected_complete = (
            self.start_offset_bytes == 0
            and self.end_offset_bytes
            == component_size
        )

        if (
            self.covers_complete_ramdisk_component
            is not expected_complete
        ):
            raise ValueError(
                "covers_complete_ramdisk_component does not match "
                "the canonical byte range"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbPartitionReferenceComposition:
    """
    One exact interpreted AVB descriptor whose canonical partition target
    names one composed boot-family partition.

    This is a structural reference only. It does not infer trust, signing
    ownership, key selection, or realization policy.
    """

    vbmeta: AndroidBootImageAvbVbmetaInterpretation

    descriptor: AndroidBootImageAvbDescriptorInterpretation

    target_partition: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.vbmeta,
            AndroidBootImageAvbVbmetaInterpretation,
        ):
            raise TypeError(
                "vbmeta must be an "
                "AndroidBootImageAvbVbmetaInterpretation"
            )

        if not isinstance(
            self.descriptor,
            AndroidBootImageAvbDescriptorInterpretation,
        ):
            raise TypeError(
                "descriptor must be an "
                "AndroidBootImageAvbDescriptorInterpretation"
            )

        if not any(
            candidate is self.descriptor
            for candidate
            in self.vbmeta.descriptors
        ):
            raise ValueError(
                "AVB partition reference must retain exact "
                "descriptor membership in its VBMeta node"
            )

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
            self.descriptor.target_partition
            != self.target_partition
        ):
            raise ValueError(
                "AVB partition reference target must exactly "
                "match the canonical descriptor target"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageSignedPayloadComposition:
    """
    Exact canonical byte-range relationship between one boot-signature
    component and the boot-image payload covered by its own AVB hash
    descriptor.

    ParsedBootSignature is authoritative for the embedded signature metadata.
    This relationship does not depend on the separately extracted AVB-region
    representation of the same boot image.

    Composition selects no signing key, trust policy, provider, or
    regeneration action.
    """

    signature_component: AndroidBootImageComponentInterpretation

    descriptor: AndroidParsedAvbHashDescriptor

    start_offset_bytes: int
    end_offset_bytes: int

    covered_components: tuple[
        AndroidBootImageComponentInterpretation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            self.signature_component.role
            is not AndroidBootImageComponentRole.BOOT_SIGNATURE
        ):
            raise ValueError(
                "signed-payload composition requires a "
                "boot-signature component"
            )

        boot_signature = (
            self.signature_component.boot_signature
        )

        if boot_signature is None:
            raise ValueError(
                "signed-payload composition requires structured "
                "boot-signature evidence"
            )

        if not isinstance(
            self.descriptor,
            AndroidParsedAvbHashDescriptor,
        ):
            raise TypeError(
                "descriptor must be an "
                "AndroidParsedAvbHashDescriptor"
            )

        if not any(
            candidate is self.descriptor
            for candidate
            in boot_signature.metadata.descriptors
        ):
            raise ValueError(
                "signed-payload descriptor must retain exact "
                "ParsedBootSignature descriptor identity"
            )

        if self.start_offset_bytes != 0:
            raise ValueError(
                "AVB boot-signature hash coverage must begin "
                "at image byte zero"
            )

        if (
            self.end_offset_bytes
            != self.descriptor.image_size
        ):
            raise ValueError(
                "signed-payload end must equal the canonical "
                "AVB hash descriptor image_size"
            )

        signature_offset = _artifact_int_fact(
            self.signature_component.artifact,
            "offset_bytes",
        )

        if (
            signature_offset
            != self.end_offset_bytes
        ):
            raise ValueError(
                "boot-signature component must begin exactly "
                "at the canonical signed-payload boundary"
            )

        if not isinstance(
            self.covered_components,
            tuple,
        ):
            raise TypeError(
                "covered_components must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageComponentInterpretation,
            )
            for value
            in self.covered_components
        ):
            raise TypeError(
                "covered_components contains an invalid component"
            )

        if any(
            value is self.signature_component
            for value
            in self.covered_components
        ):
            raise ValueError(
                "boot-signature component cannot be inside its "
                "own signed payload"
            )

    def covers_component(
        self,
        component: AndroidBootImageComponentInterpretation,
    ) -> bool:
        return any(
            candidate is component
            for candidate
            in self.covered_components
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageBootImageComposition:
    """
    Structural composition of one interpreted Android boot-family image.

    Composition groups already-canonical Boot Image Interpretation objects.
    It does not select output images, source providers, build tools, signing
    material, destinations, or reconstruction policy.
    """

    image: AndroidBootImageBootImageInterpretation

    components: tuple[
        AndroidBootImageComponentInterpretation,
        ...,
    ]

    ramdisk: AndroidBootImageRamdiskInterpretation | None = None

    vendor_ramdisk_entries: tuple[
        AndroidBootImageVendorRamdiskEntryComposition,
        ...,
    ] = ()

    avb_regions: tuple[
        AndroidBootImageAvbRegionInterpretation,
        ...,
    ] = ()

    avb_partition_references: tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ] = ()

    signed_payloads: tuple[
        AndroidBootImageSignedPayloadComposition,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.image,
            AndroidBootImageBootImageInterpretation,
        ):
            raise TypeError(
                "image must be an "
                "AndroidBootImageBootImageInterpretation"
            )

        if not isinstance(
            self.components,
            tuple,
        ):
            raise TypeError(
                "components must be a tuple"
            )

        if not all(
            isinstance(
                component,
                AndroidBootImageComponentInterpretation,
            )
            for component
            in self.components
        ):
            raise TypeError(
                "components contain an invalid Boot Image "
                "component interpretation"
            )

        expected_component_ids = tuple(
            id(
                component
            )
            for component
            in self.image.components
        )

        actual_component_ids = tuple(
            id(
                component
            )
            for component
            in self.components
        )

        if (
            actual_component_ids
            != expected_component_ids
        ):
            raise ValueError(
                "Boot Image composition must preserve every "
                "interpreted boot component in exact order "
                "and object identity"
            )

        if self.ramdisk is not None:
            if not isinstance(
                self.ramdisk,
                AndroidBootImageRamdiskInterpretation,
            ):
                raise TypeError(
                    "ramdisk must be an "
                    "AndroidBootImageRamdiskInterpretation or None"
                )

            if (
                self.ramdisk.boot_image
                is not self.image.image
            ):
                raise ValueError(
                    "Boot Image composition ramdisk must retain "
                    "the exact ParsedBootImage represented by "
                    "this boot-image interpretation"
                )

        relationship_collections = (
            (
                "vendor_ramdisk_entries",
                self.vendor_ramdisk_entries,
                AndroidBootImageVendorRamdiskEntryComposition,
            ),
            (
                "avb_regions",
                self.avb_regions,
                AndroidBootImageAvbRegionInterpretation,
            ),
            (
                "avb_partition_references",
                self.avb_partition_references,
                AndroidBootImageAvbPartitionReferenceComposition,
            ),
        )

        for (
            field_name,
            values,
            expected_type,
        ) in relationship_collections:
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid "
                    f"{expected_type.__name__}"
                )

        partition_artifact = (
            self.image
            .image
            .partition
            .artifact
        )

        for region in self.avb_regions:
            if not _artifact_descends_from(
                region.artifact,
                partition_artifact,
            ):
                raise ValueError(
                    "boot-image AVB region must retain canonical "
                    "Extraction ancestry beneath this exact "
                    "boot partition artifact"
                )

        partition_name = (
            self.image
            .image
            .partition
            .name
        )

        for reference in self.avb_partition_references:
            if (
                reference.target_partition
                != partition_name
            ):
                raise ValueError(
                    "boot-image AVB descriptor reference must "
                    "target this exact canonical partition name"
                )

        table = self.vendor_ramdisk_table

        if table is None:
            if self.vendor_ramdisk_entries:
                raise ValueError(
                    "vendor ramdisk entry compositions require "
                    "a canonical vendor ramdisk table"
                )

        else:
            actual_entries = tuple(
                id(
                    value.entry
                )
                for value
                in self.vendor_ramdisk_entries
            )

            expected_entries = tuple(
                id(
                    value
                )
                for value
                in table.entries
            )

            if (
                actual_entries
                != expected_entries
            ):
                raise ValueError(
                    "vendor ramdisk entry composition must "
                    "conserve every table entry in canonical order "
                    "and exact identity"
                )

            for value in self.vendor_ramdisk_entries:
                if value.table is not table:
                    raise ValueError(
                        "vendor ramdisk entry composition must "
                        "retain this image's exact canonical table"
                    )

        if not isinstance(
            self.signed_payloads,
            tuple,
        ):
            raise TypeError(
                "signed_payloads must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootImageSignedPayloadComposition,
            )
            for value
            in self.signed_payloads
        ):
            raise TypeError(
                "signed_payloads contains an invalid composition"
            )

        for value in self.signed_payloads:
            if not any(
                candidate is value.signature_component
                for candidate
                in self.components
            ):
                raise ValueError(
                    "signed-payload signature component must belong "
                    "to this exact boot-image composition"
                )

            if not all(
                any(
                    candidate is covered
                    for candidate
                    in self.components
                )
                for covered
                in value.covered_components
            ):
                raise ValueError(
                    "signed-payload covered components must belong "
                    "to this exact boot-image composition"
                )

    @property
    def container_kind(
        self,
    ) -> str:
        return self.image.container_kind

    @property
    def component_count(
        self,
    ) -> int:
        return len(
            self.components
        )

    @property
    def dtb_members(
        self,
    ):
        return tuple(
            dtb
            for component
            in self.components
            for dtb
            in component.dtbs
        )

    @property
    def bootconfig(
        self,
    ):
        matches = tuple(
            component.bootconfig
            for component
            in self.components
            if component.bootconfig is not None
        )

        if len(
            matches
        ) > 1:
            raise RuntimeError(
                "one boot-image composition cannot contain "
                "multiple canonical bootconfig interpretations"
            )

        return (
            matches[0]
            if matches
            else None
        )

    @property
    def vendor_ramdisk_table(
        self,
    ):
        matches = tuple(
            component.vendor_ramdisk_table
            for component
            in self.components
            if (
                component.vendor_ramdisk_table
                is not None
            )
        )

        if len(
            matches
        ) > 1:
            raise RuntimeError(
                "one boot-image composition cannot contain "
                "multiple canonical vendor ramdisk tables"
            )

        return (
            matches[0]
            if matches
            else None
        )

    @property
    def kernel(
        self,
    ):
        matches = tuple(
            component.kernel
            for component
            in self.components
            if component.kernel is not None
        )

        if len(
            matches
        ) > 1:
            raise RuntimeError(
                "one boot-image composition cannot contain "
                "multiple canonical parsed kernels"
            )

        return (
            matches[0]
            if matches
            else None
        )

    @property
    def boot_signature(
        self,
    ):
        matches = tuple(
            component.boot_signature
            for component
            in self.components
            if component.boot_signature is not None
        )

        if len(
            matches
        ) > 1:
            raise RuntimeError(
                "one boot-image composition cannot contain "
                "multiple canonical boot signatures"
            )

        return (
            matches[0]
            if matches
            else None
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageCompositionResult:
    """
    Boot Image-owned structural composition of the complete Interpretation
    result.

    All members retain exact Interpretation identities. Composition may group
    relationships but must not recreate canonical Parsing or Interpretation
    objects.
    """

    interpretation: AndroidBootImageInterpretationResult

    boot_images: tuple[
        AndroidBootImageBootImageComposition,
        ...,
    ]

    dtbo_entries: tuple[
        AndroidBootImageDtboEntryInterpretation,
        ...,
    ]

    dtbo_containers: tuple[
        AndroidBootImageDtboContainerInterpretation,
        ...,
    ]

    avb_vbmeta: tuple[
        AndroidBootImageAvbVbmetaInterpretation,
        ...,
    ]

    avb_regions: tuple[
        AndroidBootImageAvbRegionInterpretation,
        ...,
    ]

    avb_partition_references: tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.interpretation,
            AndroidBootImageInterpretationResult,
        ):
            raise TypeError(
                "interpretation must be an "
                "AndroidBootImageInterpretationResult"
            )

        collections = (
            (
                "boot_images",
                self.boot_images,
                AndroidBootImageBootImageComposition,
            ),
            (
                "dtbo_entries",
                self.dtbo_entries,
                AndroidBootImageDtboEntryInterpretation,
            ),
            (
                "dtbo_containers",
                self.dtbo_containers,
                AndroidBootImageDtboContainerInterpretation,
            ),
            (
                "avb_vbmeta",
                self.avb_vbmeta,
                AndroidBootImageAvbVbmetaInterpretation,
            ),
            (
                "avb_regions",
                self.avb_regions,
                AndroidBootImageAvbRegionInterpretation,
            ),
            (
                "avb_partition_references",
                self.avb_partition_references,
                AndroidBootImageAvbPartitionReferenceComposition,
            ),
        )

        for (
            field_name,
            values,
            expected_type,
        ) in collections:
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid "
                    f"{expected_type.__name__}"
                )

        if tuple(
            id(
                value.image
            )
            for value
            in self.boot_images
        ) != tuple(
            id(
                value
            )
            for value
            in self.interpretation.boot_images
        ):
            raise ValueError(
                "Boot Image composition must conserve the complete "
                "boot-image Interpretation population in exact order "
                "and identity"
            )

        identity_checks = (
            (
                "DTBO entries",
                self.dtbo_entries,
                self.interpretation.dtbo_entries,
            ),
            (
                "DTBO containers",
                self.dtbo_containers,
                self.interpretation.dtbo_containers,
            ),
            (
                "VBMeta",
                self.avb_vbmeta,
                self.interpretation.avb_vbmeta,
            ),
            (
                "AVB regions",
                self.avb_regions,
                self.interpretation.avb_regions,
            ),
        )

        for (
            label,
            actual,
            expected,
        ) in identity_checks:
            if tuple(
                id(
                    value
                )
                for value
                in actual
            ) != tuple(
                id(
                    value
                )
                for value
                in expected
            ):
                raise ValueError(
                    "Boot Image composition must conserve "
                    f"{label} in exact Interpretation order "
                    "and identity"
                )

        interpretation_ramdisk_ids = {
            id(
                value
            )
            for value
            in self.interpretation.ramdisks
        }

        composed_ramdisks = tuple(
            value.ramdisk
            for value
            in self.boot_images
            if value.ramdisk is not None
        )

        if {
            id(
                value
            )
            for value
            in composed_ramdisks
        } != interpretation_ramdisk_ids:
            raise ValueError(
                "Boot Image composition must associate every "
                "interpreted ramdisk exactly once"
            )

        if len(
            composed_ramdisks
        ) != len(
            interpretation_ramdisk_ids
        ):
            raise ValueError(
                "Boot Image composition contains duplicate "
                "ramdisk associations"
            )

        global_region_ids = {
            id(
                value
            )
            for value
            in self.avb_regions
        }

        for image in self.boot_images:
            for region in image.avb_regions:
                if (
                    id(
                        region
                    )
                    not in global_region_ids
                ):
                    raise ValueError(
                        "boot-image AVB relationship references "
                        "a region outside the conserved global "
                        "Interpretation population"
                    )

        global_vbmeta_ids = {
            id(
                value
            )
            for value
            in self.avb_vbmeta
        }

        expected_avb_reference_pairs = tuple(
            (
                id(vbmeta),
                id(descriptor),
                descriptor.target_partition,
            )
            for vbmeta
            in self.avb_vbmeta
            for descriptor
            in vbmeta.descriptors
            if descriptor.target_partition
        )

        actual_avb_reference_pairs = tuple(
            (
                id(reference.vbmeta),
                id(reference.descriptor),
                reference.target_partition,
            )
            for reference
            in self.avb_partition_references
        )

        if (
            actual_avb_reference_pairs
            != expected_avb_reference_pairs
        ):
            raise ValueError(
                "global AVB partition-reference topology must "
                "conserve every partition-targeting descriptor "
                "in exact VBMeta/descriptor order and identity"
            )

        for reference in self.avb_partition_references:
            if (
                id(reference.vbmeta)
                not in global_vbmeta_ids
            ):
                raise ValueError(
                    "global AVB partition reference uses a "
                    "VBMeta node outside the conserved "
                    "Interpretation population"
                )

        global_reference_ids = {
            id(
                reference
            )
            for reference
            in self.avb_partition_references
        }

        for image in self.boot_images:
            for reference in (
                image.avb_partition_references
            ):
                if (
                    id(
                        reference.vbmeta
                    )
                    not in global_vbmeta_ids
                ):
                    raise ValueError(
                        "boot-image AVB partition reference uses "
                        "a VBMeta node outside the conserved "
                        "Interpretation population"
                    )

                if (
                    id(reference)
                    not in global_reference_ids
                ):
                    raise ValueError(
                        "boot-image AVB partition reference must "
                        "retain exact membership in the global "
                        "Composition topology"
                    )

    @property
    def parsing(
        self,
    ) -> AndroidParsingResult:
        return self.interpretation.parsing

    @property
    def ramdisks(
        self,
    ):
        return self.interpretation.ramdisks

    @property
    def component_count(
        self,
    ) -> int:
        return sum(
            image.component_count
            for image
            in self.boot_images
        )

    @property
    def dtbo_entry_count(
        self,
    ) -> int:
        return len(
            self.dtbo_entries
        )

    @property
    def dtbo_container_count(
        self,
    ) -> int:
        return len(
            self.dtbo_containers
        )

    @property
    def avb_vbmeta_count(
        self,
    ) -> int:
        return len(
            self.avb_vbmeta
        )

    @property
    def avb_region_count(
        self,
    ) -> int:
        return len(
            self.avb_regions
        )

    @property
    def avb_partition_reference_count(
        self,
    ) -> int:
        return len(
            self.avb_partition_references
        )

    def avb_references_targeting(
        self,
        partition_name: str,
    ) -> tuple[
        AndroidBootImageAvbPartitionReferenceComposition,
        ...,
    ]:
        if (
            not isinstance(
                partition_name,
                str,
            )
            or not partition_name
        ):
            raise ValueError(
                "partition_name must be a non-empty string"
            )

        return tuple(
            reference
            for reference
            in self.avb_partition_references
            if (
                reference.target_partition
                == partition_name
            )
        )

    @property
    def avb_unknown_descriptor_count(
        self,
    ) -> int:
        return (
            self.interpretation
            .avb_unknown_descriptor_count
        )

    @property
    def unclassified_component_count(
        self,
    ) -> int:
        return (
            self.interpretation
            .unclassified_component_count
        )


class AndroidBootImageComposer:
    """
    Compose the canonical Boot Image Interpretation into structural image
    groupings.

    No realization or provider decisions are made here.
    """

    def build(
        self,
        interpretation: AndroidBootImageInterpretationResult,
    ) -> AndroidBootImageCompositionResult:
        if not isinstance(
            interpretation,
            AndroidBootImageInterpretationResult,
        ):
            raise TypeError(
                "interpretation must be an "
                "AndroidBootImageInterpretationResult"
            )

        ramdisk_by_boot_image_id = {}

        for ramdisk in interpretation.ramdisks:
            identity = id(
                ramdisk.boot_image
            )

            if (
                identity
                in ramdisk_by_boot_image_id
            ):
                raise ValueError(
                    "multiple Boot Image ramdisk interpretations "
                    "resolve to the same ParsedBootImage"
                )

            ramdisk_by_boot_image_id[
                identity
            ] = ramdisk

        avb_partition_references = tuple(
            AndroidBootImageAvbPartitionReferenceComposition(
                vbmeta=vbmeta,
                descriptor=descriptor,
                target_partition=descriptor.target_partition,
            )
            for vbmeta
            in interpretation.avb_vbmeta
            for descriptor
            in vbmeta.descriptors
            if descriptor.target_partition
        )

        def compose_boot_image(
            image,
        ) -> AndroidBootImageBootImageComposition:
            ramdisk = (
                ramdisk_by_boot_image_id.get(
                    id(
                        image.image
                    )
                )
            )

            partition_artifact = (
                image.image
                .partition
                .artifact
            )

            partition_name = (
                image.image
                .partition
                .name
            )

            image_avb_regions = tuple(
                region
                for region
                in interpretation.avb_regions
                if _artifact_descends_from(
                    region.artifact,
                    partition_artifact,
                )
            )

            image_avb_references = tuple(
                reference
                for reference
                in avb_partition_references
                if (
                    reference.target_partition
                    == partition_name
                )
            )

            table_components = tuple(
                component
                for component
                in image.components
                if (
                    component.vendor_ramdisk_table
                    is not None
                )
            )

            ramdisk_components = tuple(
                component
                for component
                in image.components
                if (
                    component.role
                    is AndroidBootImageComponentRole.RAMDISK
                )
            )

            vendor_ramdisk_entries = ()

            signed_payloads = []

            signature_components = tuple(
                component
                for component
                in image.components
                if (
                    component.role
                    is AndroidBootImageComponentRole
                    .BOOT_SIGNATURE
                    and component.boot_signature is not None
                )
            )

            for signature_component in signature_components:
                boot_signature = (
                    signature_component.boot_signature
                )

                assert boot_signature is not None

                hash_descriptors = tuple(
                    descriptor
                    for descriptor
                    in boot_signature.metadata.descriptors
                    if isinstance(
                        descriptor,
                        AndroidParsedAvbHashDescriptor,
                    )
                )

                if len(
                    hash_descriptors
                ) != 1:
                    raise ValueError(
                        "structured boot-signature component must "
                        "contain exactly one AVB hash descriptor"
                    )

                parsed_hash = (
                    hash_descriptors[0]
                )

                if (
                    parsed_hash.partition_name
                    != image.image.partition.name
                ):
                    raise ValueError(
                        "boot-signature hash descriptor partition "
                        "must match the exact canonical boot-image "
                        "partition"
                    )

                covered_components = []

                for candidate in image.components:
                    if candidate is signature_component:
                        continue

                    component_offset = _artifact_int_fact(
                        candidate.artifact,
                        "offset_bytes",
                    )

                    component_size = (
                        candidate.artifact.size_bytes
                    )

                    if (
                        isinstance(
                            component_size,
                            bool,
                        )
                        or not isinstance(
                            component_size,
                            int,
                        )
                        or component_size < 0
                    ):
                        raise ValueError(
                            "boot component must retain an exact "
                            "physical size for signed-range composition"
                        )

                    component_end = (
                        component_offset
                        + component_size
                    )

                    if (
                        component_offset
                        < parsed_hash.image_size
                        and component_end > 0
                    ):
                        if (
                            component_end
                            > parsed_hash.image_size
                        ):
                            raise ValueError(
                                "boot component crosses the canonical "
                                "signed-payload boundary"
                            )

                        covered_components.append(
                            candidate
                        )

                signed_payloads.append(
                    AndroidBootImageSignedPayloadComposition(
                        signature_component=signature_component,
                        descriptor=parsed_hash,
                        start_offset_bytes=0,
                        end_offset_bytes=(
                            parsed_hash.image_size
                        ),
                        covered_components=tuple(
                            covered_components
                        ),
                    )
                )

            if table_components:
                if len(
                    table_components
                ) != 1:
                    raise ValueError(
                        "one boot image cannot contain multiple "
                        "canonical vendor ramdisk tables"
                    )

                table = (
                    table_components[0]
                    .vendor_ramdisk_table
                )

                assert table is not None

                if table.entries:
                    if len(
                        ramdisk_components
                    ) != 1:
                        raise ValueError(
                            "non-empty vendor ramdisk table requires "
                            "exactly one sibling ramdisk component"
                        )

                    ramdisk_component = (
                        ramdisk_components[0]
                    )

                    component_size = (
                        ramdisk_component
                        .artifact
                        .size_bytes
                    )

                    if (
                        isinstance(
                            component_size,
                            bool,
                        )
                        or not isinstance(
                            component_size,
                            int,
                        )
                    ):
                        raise ValueError(
                            "vendor ramdisk component is missing "
                            "an exact physical size"
                        )

                    vendor_ramdisk_entries = tuple(
                        AndroidBootImageVendorRamdiskEntryComposition(
                            table=table,
                            entry=entry,
                            ramdisk_component=(
                                ramdisk_component
                            ),
                            start_offset_bytes=(
                                entry.ramdisk_offset
                            ),
                            end_offset_bytes=(
                                entry.ramdisk_offset
                                + entry.ramdisk_size
                            ),
                            covers_complete_ramdisk_component=(
                                entry.ramdisk_offset == 0
                                and (
                                    entry.ramdisk_size
                                    == component_size
                                )
                            ),
                        )
                        for entry
                        in table.entries
                    )

            return AndroidBootImageBootImageComposition(
                image=image,
                components=image.components,
                ramdisk=ramdisk,
                vendor_ramdisk_entries=(
                    vendor_ramdisk_entries
                ),
                avb_regions=(
                    image_avb_regions
                ),
                avb_partition_references=(
                    image_avb_references
                ),
                signed_payloads=tuple(
                    signed_payloads
                ),
            )

        boot_images = tuple(
            compose_boot_image(
                image
            )
            for image
            in interpretation.boot_images
        )

        result = AndroidBootImageCompositionResult(
            interpretation=interpretation,
            boot_images=boot_images,
            dtbo_entries=(
                interpretation.dtbo_entries
            ),
            dtbo_containers=(
                interpretation.dtbo_containers
            ),
            avb_vbmeta=(
                interpretation.avb_vbmeta
            ),
            avb_regions=(
                interpretation.avb_regions
            ),
            avb_partition_references=(
                avb_partition_references
            ),
        )

        if (
            result.interpretation
            is not interpretation
        ):
            raise RuntimeError(
                "Boot Image composition must preserve exact "
                "Interpretation result identity"
            )

        if (
            result.parsing
            is not interpretation.parsing
        ):
            raise RuntimeError(
                "Boot Image composition must preserve exact "
                "AndroidParsingResult identity"
            )

        return result
