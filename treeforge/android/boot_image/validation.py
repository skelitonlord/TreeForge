from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
import struct
import subprocess

from treeforge.android.host_provider_bundle import (
    ANDROID_15_HOST_PROVIDER_RELEASE,
    AndroidHostProviderBundleLoader,
    android_host_provider_bundle_root,
)
from treeforge.android.boot_image.realization import (
    AndroidBootImageParentVbmetaRealization,
    AndroidBootImageRealizationProvider,
    AndroidBootImageRealizationResult,
)


class AndroidBootImageValidationDisposition(
    StrEnum
):
    """
    Final disposition of Boot Image Validation.

    PARTIAL means TreeForge could not completely validate the
    generated artifact population or realized AVB trust graph.

    Bootloader root-key acceptance is reported independently. It is a
    hardware policy boundary and does not make an otherwise complete,
    internally valid generated image set PARTIAL.
    """

    PASS = "pass"

    PARTIAL = "partial"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImagePhysicalArtifactValidation:
    """
    Independent Validation of one materialized Boot Image artifact
    against the authoritative source that Realization claims it represents.
    """

    kind: str

    semantic_name: str

    output_path: Path

    source_path: Path

    size_bytes: int

    content_sha256: str

    source_correspondence_verified: bool

    realization_identity_verified: bool

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "kind",
                self.kind,
            ),
            (
                "semantic_name",
                self.semantic_name,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        for name, value in (
            (
                "output_path",
                self.output_path,
            ),
            (
                "source_path",
                self.source_path,
            ),
        ):
            if not isinstance(
                value,
                Path,
            ):
                raise TypeError(
                    f"{name} must be pathlib.Path"
                )

            if not value.is_file():
                raise FileNotFoundError(
                    f"validated artifact path is unavailable: {value}"
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
                "content_sha256 must be a SHA-256 digest"
            )

        if (
            self.source_correspondence_verified
            is not True
        ):
            raise ValueError(
                "physical artifact Validation must prove exact "
                "source correspondence"
            )

        if (
            self.realization_identity_verified
            is not True
        ):
            raise ValueError(
                "physical artifact Validation must prove exact "
                "Realization byte identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageBootImageStructureValidation:
    """
    Independent structural inspection of one final rebuilt boot-family image.
    """

    container_kind: str

    output_path: Path

    header_version: int

    ramdisk_verified: bool

    empty_kernel_verified: bool

    structure_verified: bool

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.container_kind,
                str,
            )
            or not self.container_kind
        ):
            raise ValueError(
                "container_kind must be a non-empty string"
            )

        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be pathlib.Path"
            )

        if not self.output_path.is_file():
            raise FileNotFoundError(
                "validated rebuilt boot image is unavailable: "
                f"{self.output_path}"
            )

        if (
            isinstance(
                self.header_version,
                bool,
            )
            or not isinstance(
                self.header_version,
                int,
            )
            or self.header_version < 0
        ):
            raise ValueError(
                "header_version must be a non-negative int"
            )

        for name, value in (
            (
                "ramdisk_verified",
                self.ramdisk_verified,
            ),
            (
                "empty_kernel_verified",
                self.empty_kernel_verified,
            ),
            (
                "structure_verified",
                self.structure_verified,
            ),
        ):
            if value is not True:
                raise ValueError(
                    f"{name} must be true for successful "
                    "boot-image structural Validation"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDtboStructureValidation:
    """
    Independent Validation of one realized DTBO table against the
    complete canonical Boot Image DTBO entry interpretation.
    """

    output_path: Path

    entry_count: int

    page_size_bytes: int

    table_total_size_bytes: int

    table_version: int

    table_header_verified: bool

    entries_verified: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be pathlib.Path"
            )

        if not self.output_path.is_file():
            raise FileNotFoundError(
                "validated DTBO container is unavailable: "
                f"{self.output_path}"
            )

        for name, value in (
            (
                "entry_count",
                self.entry_count,
            ),
            (
                "page_size_bytes",
                self.page_size_bytes,
            ),
            (
                "table_total_size_bytes",
                self.table_total_size_bytes,
            ),
            (
                "table_version",
                self.table_version,
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

        if self.table_header_verified is not True:
            raise ValueError(
                "DTBO table header must be verified"
            )

        if self.entries_verified is not True:
            raise ValueError(
                "DTBO entry population must be verified"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbArtifactValidation:
    """
    Independent Validation result for one regenerated AVB-bearing
    artifact.
    """

    kind: str

    partition_name: str

    output_path: Path

    size_bytes: int

    content_sha256: str

    realization_identity_verified: bool

    cryptographic_verification_complete: bool

    descriptor_population_verified: bool

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.kind,
                str,
            )
            or not self.kind
        ):
            raise ValueError(
                "kind must be a non-empty string"
            )

        if (
            not isinstance(
                self.partition_name,
                str,
            )
            or not self.partition_name
        ):
            raise ValueError(
                "partition_name must be a non-empty string"
            )

        if not isinstance(
            self.output_path,
            Path,
        ):
            raise TypeError(
                "output_path must be pathlib.Path"
            )

        if not self.output_path.is_file():
            raise FileNotFoundError(
                "validated AVB artifact is unavailable: "
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
                "content_sha256 must be a SHA-256 digest"
            )

        for (
            field_name,
            value,
        ) in (
            (
                "realization_identity_verified",
                self.realization_identity_verified,
            ),
            (
                "cryptographic_verification_complete",
                self.cryptographic_verification_complete,
            ),
            (
                "descriptor_population_verified",
                self.descriptor_population_verified,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be bool"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must be true for a "
                    "successful artifact validation"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageAvbTrustEdgeValidation:
    """
    Validation of one realized AVB chain-partition trust edge.
    """

    parent_partition: str

    target_partition: str

    descriptor_index: int

    source_kind: str

    public_key_correspondence_verified: bool

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "parent_partition",
                self.parent_partition,
            ),
            (
                "target_partition",
                self.target_partition,
            ),
            (
                "source_kind",
                self.source_kind,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        if (
            isinstance(
                self.descriptor_index,
                bool,
            )
            or not isinstance(
                self.descriptor_index,
                int,
            )
            or self.descriptor_index < 0
        ):
            raise ValueError(
                "descriptor_index must be a non-negative int"
            )

        if (
            self.public_key_correspondence_verified
            is not True
        ):
            raise ValueError(
                "realized AVB trust edge must prove exact "
                "public-key correspondence"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageValidationResult:
    """
    First-class Boot Image Validation boundary.

    Validation retains exact Realization identity and independently
    verifies materialized AVB artifacts and their realized trust graph.
    """

    realization: AndroidBootImageRealizationResult

    physical_artifacts: tuple[
        AndroidBootImagePhysicalArtifactValidation,
        ...,
    ]

    boot_image_structures: tuple[
        AndroidBootImageBootImageStructureValidation,
        ...,
    ]

    dtbo_structures: tuple[
        AndroidBootImageDtboStructureValidation,
        ...,
    ]

    provider_invocations_verified: bool

    avb_artifacts: tuple[
        AndroidBootImageAvbArtifactValidation,
        ...,
    ]

    avb_trust_edges: tuple[
        AndroidBootImageAvbTrustEdgeValidation,
        ...,
    ]

    cryptographic_integrity_complete: bool

    realized_trust_graph_complete: bool

    bootloader_trust_resolved: bool

    flashable_chain_applicable: bool

    flashable_chain_complete: bool

    disposition: AndroidBootImageValidationDisposition

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.realization,
            AndroidBootImageRealizationResult,
        ):
            raise TypeError(
                "realization must be an "
                "AndroidBootImageRealizationResult"
            )

        if not isinstance(
            self.physical_artifacts,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImagePhysicalArtifactValidation,
            )
            for value
            in self.physical_artifacts
        ):
            raise TypeError(
                "physical_artifacts contains an invalid validation"
            )

        if not isinstance(
            self.boot_image_structures,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageBootImageStructureValidation,
            )
            for value
            in self.boot_image_structures
        ):
            raise TypeError(
                "boot_image_structures contains an invalid validation"
            )

        if not isinstance(
            self.dtbo_structures,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageDtboStructureValidation,
            )
            for value
            in self.dtbo_structures
        ):
            raise TypeError(
                "dtbo_structures contains an invalid validation"
            )

        if (
            self.provider_invocations_verified
            is not True
        ):
            raise ValueError(
                "Validation must account for every retained "
                "provider invocation"
            )

        if not isinstance(
            self.avb_artifacts,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageAvbArtifactValidation,
            )
            for value
            in self.avb_artifacts
        ):
            raise TypeError(
                "avb_artifacts contains an invalid validation"
            )

        if not isinstance(
            self.avb_trust_edges,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageAvbTrustEdgeValidation,
            )
            for value
            in self.avb_trust_edges
        ):
            raise TypeError(
                "avb_trust_edges contains an invalid validation"
            )

        for (
            field_name,
            value,
        ) in (
            (
                "cryptographic_integrity_complete",
                self.cryptographic_integrity_complete,
            ),
            (
                "realized_trust_graph_complete",
                self.realized_trust_graph_complete,
            ),
            (
                "bootloader_trust_resolved",
                self.bootloader_trust_resolved,
            ),
            (
                "flashable_chain_applicable",
                self.flashable_chain_applicable,
            ),
            (
                "flashable_chain_complete",
                self.flashable_chain_complete,
            ),
        ):
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be bool"
                )

        if not isinstance(
            self.disposition,
            AndroidBootImageValidationDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootImageValidationDisposition"
            )

        if not (
            self.cryptographic_integrity_complete
        ):
            raise ValueError(
                "successful Boot Image Validation requires "
                "complete cryptographic integrity"
            )

        if (
            not self.flashable_chain_applicable
            and self.flashable_chain_complete
        ):
            raise ValueError(
                "non-applicable flashable chain cannot be "
                "reported complete"
            )

        if (
            self.flashable_chain_complete
            and not (
                self.realized_trust_graph_complete
            )
        ):
            raise ValueError(
                "flashable chain cannot be complete without "
                "a complete realized AVB trust graph"
            )

        expected_disposition = (
            AndroidBootImageValidationDisposition
            .PASS
            if (
                not self.flashable_chain_applicable
                or self.flashable_chain_complete
            )
            else (
                AndroidBootImageValidationDisposition
                .PARTIAL
            )
        )

        if (
            self.disposition
            is not expected_disposition
        ):
            raise ValueError(
                "Validation disposition does not match "
                "flashable-chain completeness"
            )

    @property
    def planning(
        self,
    ):
        return self.realization.planning

    @property
    def composition(
        self,
    ):
        return self.realization.composition

    @property
    def interpretation(
        self,
    ):
        return self.realization.interpretation

    @property
    def parsing(
        self,
    ):
        return self.realization.parsing

    @property
    def physical_artifact_validation_count(
        self,
    ) -> int:
        return len(
            self.physical_artifacts
        )

    @property
    def boot_image_structure_validation_count(
        self,
    ) -> int:
        return len(
            self.boot_image_structures
        )

    @property
    def dtbo_structure_validation_count(
        self,
    ) -> int:
        return len(
            self.dtbo_structures
        )

    @property
    def artifact_validation_count(
        self,
    ) -> int:
        return len(
            self.avb_artifacts
        )

    @property
    def trust_edge_validation_count(
        self,
    ) -> int:
        return len(
            self.avb_trust_edges
        )


class AndroidBootImageValidator:
    """
    Validate the fully realized Boot Image artifact set.

    Validation does not mutate artifacts and does not select new signing
    identities. It independently checks the final materialized bytes and
    the realized AVB trust relationships produced by Realization.
    """

    @staticmethod
    def _file_identity(
        path: Path,
    ) -> tuple[
        int,
        str,
    ]:
        if not path.is_file():
            raise FileNotFoundError(
                "Boot Image Validation artifact is unavailable: "
                f"{path}"
            )

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

        return (
            path.stat().st_size,
            digest.hexdigest(),
        )

    @staticmethod
    def _avbtool() -> Path:
        provider = (
            AndroidHostProviderBundleLoader.load(
                android_host_provider_bundle_root(
                    name="avbtool",
                    release=(
                        ANDROID_15_HOST_PROVIDER_RELEASE
                    ),
                )
            )
        )

        if not provider.supports(
            "android-avbtool"
        ):
            raise RuntimeError(
                "TreeForge avbtool provider lacks "
                "android-avbtool capability"
            )

        return provider.executable_for(
            "android-avbtool"
        )

    @staticmethod
    def _verify_image(
        *,
        avbtool: Path,
        image_path: Path,
        key_path: Path | None,
    ) -> None:
        command = [
            str(
                avbtool
            ),
            "verify_image",
            "--image",
            str(
                image_path
            ),
        ]

        if key_path is not None:
            command.extend(
                (
                    "--key",
                    str(
                        key_path
                    ),
                )
            )

        completed = subprocess.run(
            tuple(
                command
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode != 0:
            stderr = (
                completed.stderr
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            stdout = (
                completed.stdout
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise RuntimeError(
                "Boot Image AVB cryptographic validation failed "
                f"for {image_path}: "
                f"{stderr or stdout}"
            )

    @staticmethod
    def _verify_standalone_vbmeta_authentication(
        *,
        avbtool: Path,
        image_path: Path,
        expected_public_key: bytes,
    ) -> None:
        if (
            not isinstance(
                expected_public_key,
                bytes,
            )
            or not expected_public_key
        ):
            raise ValueError(
                "expected_public_key must be non-empty bytes"
            )

        verifier = r"""
import importlib.machinery
import importlib.util
from pathlib import Path
import sys

avbtool_path = Path(
    sys.argv[1]
)

image_path = Path(
    sys.argv[2]
)

expected_public_key = bytes.fromhex(
    sys.argv[3]
)

loader = importlib.machinery.SourceFileLoader(
    "treeforge_bootstrap_validation_avbtool",
    str(
        avbtool_path
    ),
)

spec = importlib.util.spec_from_loader(
    loader.name,
    loader,
)

if spec is None:
    raise RuntimeError(
        "unable to create selected avbtool module spec"
    )

module = importlib.util.module_from_spec(
    spec
)

sys.modules[
    spec.name
] = module

loader.exec_module(
    module
)

image = module.ImageHandler(
    str(
        image_path
    ),
    read_only=True,
)

(
    footer,
    header,
    descriptors,
    _,
) = module.Avb()._parse_image(
    image
)

offset = 0

if footer is not None:
    offset = footer.vbmeta_offset

image.seek(
    offset
)

vbmeta_size = (
    header.SIZE
    + header.authentication_data_block_size
    + header.auxiliary_data_block_size
)

vbmeta_blob = image.read(
    vbmeta_size
)

if len(vbmeta_blob) != vbmeta_size:
    raise RuntimeError(
        "standalone VBMeta blob is truncated"
    )

if not module.verify_vbmeta_signature(
    header,
    vbmeta_blob,
):
    raise RuntimeError(
        "standalone VBMeta signature verification failed"
    )

key_offset = (
    header.SIZE
    + header.authentication_data_block_size
    + header.public_key_offset
)

embedded_public_key = (
    vbmeta_blob[
        key_offset:
        key_offset
        + header.public_key_size
    ]
)

if (
    embedded_public_key
    != expected_public_key
):
    raise RuntimeError(
        "standalone VBMeta embedded public key does not "
        "match the exact Realization-derived public key"
    )
"""

        completed = subprocess.run(
            (
                "python",
                "-c",
                verifier,
                str(
                    avbtool
                ),
                str(
                    image_path
                ),
                expected_public_key.hex(),
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode != 0:
            stderr = (
                completed.stderr
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            stdout = (
                completed.stdout
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise RuntimeError(
                "Boot Image standalone VBMeta authentication "
                f"validation failed for {image_path}: "
                f"{stderr or stdout}"
            )


    @classmethod
    def _validate_dtbo_structure(
        cls,
        *,
        realized_dtbo,
    ) -> AndroidBootImageDtboStructureValidation:
        data = (
            realized_dtbo
            .output_path
            .read_bytes()
        )

        header_struct = struct.Struct(
            ">8I"
        )

        entry_struct = struct.Struct(
            ">8I"
        )

        if len(data) < header_struct.size:
            raise RuntimeError(
                "realized DTBO container is too small "
                "to contain a DT table header"
            )

        (
            magic,
            total_size,
            header_size,
            entry_size,
            entry_count,
            entries_offset,
            page_size,
            version,
        ) = header_struct.unpack_from(
            data,
            0,
        )

        if magic != 0xD7B7AB1E:
            raise RuntimeError(
                "realized DTBO container has an invalid "
                f"DT table magic: 0x{magic:08x}"
            )

        if header_size < header_struct.size:
            raise RuntimeError(
                "realized DTBO header size is smaller than "
                "the canonical DT table header"
            )

        if entry_size < entry_struct.size:
            raise RuntimeError(
                "realized DTBO entry size is smaller than "
                "the canonical DT table entry"
            )

        if total_size > len(data):
            raise RuntimeError(
                "realized DTBO table total size exceeds "
                "the materialized container"
            )

        table_end = (
            entries_offset
            + (
                entry_count
                * entry_size
            )
        )

        if table_end > total_size:
            raise RuntimeError(
                "realized DTBO entry table extends beyond "
                "its declared total size"
            )

        canonical_entries = (
            realized_dtbo
            .container
            .entries
        )

        if entry_count != len(
            canonical_entries
        ):
            raise RuntimeError(
                "realized DTBO entry count does not match "
                "canonical Boot Image Interpretation: "
                f"{entry_count} != "
                f"{len(canonical_entries)}"
            )

        if canonical_entries:
            first = canonical_entries[0]

            if (
                total_size
                != first.table_total_size_bytes
            ):
                raise RuntimeError(
                    "realized DTBO total size does not match "
                    "canonical Interpretation"
                )

            if (
                page_size
                != first.page_size_bytes
            ):
                raise RuntimeError(
                    "realized DTBO page size does not match "
                    "canonical Interpretation"
                )

            if (
                version
                != first.table_version
            ):
                raise RuntimeError(
                    "realized DTBO table version does not match "
                    "canonical Interpretation"
                )

        for position, interpreted in enumerate(
            canonical_entries
        ):
            if (
                interpreted.entry_index
                != position
            ):
                raise RuntimeError(
                    "canonical DTBO entry population is not "
                    "conserved in table order"
                )

            offset = (
                entries_offset
                + (
                    position
                    * entry_size
                )
            )

            if (
                offset
                + entry_struct.size
                > len(data)
            ):
                raise RuntimeError(
                    "realized DTBO entry record is truncated"
                )

            (
                dt_size,
                dt_offset,
                dtbo_id,
                dtbo_rev,
                custom0,
                custom1,
                custom2,
                custom3,
            ) = entry_struct.unpack_from(
                data,
                offset,
            )

            actual_custom = (
                custom0,
                custom1,
                custom2,
                custom3,
            )

            if (
                dt_size
                != interpreted.declared_size_bytes
                or dt_offset
                != interpreted.offset_bytes
                or dtbo_id
                != interpreted.dtbo_id
                or dtbo_rev
                != interpreted.dtbo_rev
                or actual_custom
                != interpreted.custom
            ):
                raise RuntimeError(
                    "realized DTBO entry does not match "
                    "canonical Interpretation at index "
                    f"{position}"
                )

            if (
                dt_offset
                + dt_size
                > total_size
            ):
                raise RuntimeError(
                    "realized DTBO payload range extends "
                    "beyond the declared table total size at "
                    f"entry {position}"
                )

        return AndroidBootImageDtboStructureValidation(
            output_path=(
                realized_dtbo.output_path
            ),
            entry_count=(
                entry_count
            ),
            page_size_bytes=(
                page_size
            ),
            table_total_size_bytes=(
                total_size
            ),
            table_version=(
                version
            ),
            table_header_verified=True,
            entries_verified=True,
        )


    @classmethod
    def _validate_final_vendor_boot_structure(
        cls,
        *,
        realization: AndroidBootImageRealizationResult,
        rebuilt,
    ) -> AndroidBootImageBootImageStructureValidation:
        """
        Independently validate one rebuilt android_vendor_boot image.

        Validation derives structure again from both:
          - the exact canonical source image; and
          - the final rebuilt image.

        The factory-derived mkbootimg argument populations must remain
        semantically identical except for payloads corresponding to explicit
        authorized component mutations.

        File-bearing unchanged arguments are compared by exact bytes rather
        than temporary unpack paths.
        """

        if (
            rebuilt.image_plan.container_kind
            != "vendor_boot"
        ):
            raise ValueError(
                "final vendor_boot structural validator received "
                "a different container kind"
            )

        evaluation_matches = tuple(
            evaluation
            for evaluation
            in realization
            .mutation_analysis
            .evaluations
            if (
                evaluation.image_plan
                is rebuilt.image_plan
                and evaluation.content_changed
            )
        )

        if not evaluation_matches:
            raise RuntimeError(
                "rebuilt vendor_boot must retain at least one "
                "changed mutation evaluation"
            )

        changed_by_name = {}

        for evaluation in evaluation_matches:
            semantic_name = (
                evaluation
                .request
                .target
                .component
                .semantic_name
            )

            if semantic_name in changed_by_name:
                raise RuntimeError(
                    "rebuilt vendor_boot retained duplicate changed "
                    f"component identity: {semantic_name}"
                )

            changed_by_name[
                semantic_name
            ] = evaluation

        unexpected = (
            set(changed_by_name)
            - {
                "ramdisk",
                "bootconfig",
            }
        )

        if unexpected:
            raise RuntimeError(
                "rebuilt vendor_boot retained unsupported changed "
                "components: "
                + ", ".join(
                    sorted(unexpected)
                )
            )

        ramdisk_evaluation = (
            changed_by_name.get(
                "ramdisk"
            )
        )

        if ramdisk_evaluation is None:
            raise RuntimeError(
                "current vendor_boot reconstruction Validation "
                "requires the complete ramdisk mutation"
            )

        bootconfig_evaluation = (
            changed_by_name.get(
                "bootconfig"
            )
        )

        canonical_image = (
            rebuilt
            .image_plan
            .composition
            .image
            .image
        )

        if (
            canonical_image.container_format
            != "android_vendor_boot"
        ):
            raise RuntimeError(
                "rebuilt vendor_boot lost canonical "
                "android_vendor_boot identity"
            )

        source_path = (
            canonical_image
            .partition
            .artifact
            .path
        )

        if not source_path.is_file():
            raise FileNotFoundError(
                "canonical vendor_boot source image is unavailable: "
                f"{source_path}"
            )

        vendor_ramdisk_entries = (
            rebuilt
            .image_plan
            .composition
            .vendor_ramdisk_entries
        )

        if len(
            vendor_ramdisk_entries
        ) != 1:
            raise RuntimeError(
                "current vendor_boot Validation requires exactly one "
                "canonical composed vendor ramdisk entry; "
                f"found {len(vendor_ramdisk_entries)}"
            )

        composed_entry = (
            vendor_ramdisk_entries[
                0
            ]
        )

        if (
            not composed_entry
            .covers_complete_ramdisk_component
        ):
            raise RuntimeError(
                "current vendor_boot Validation requires the canonical "
                "vendor ramdisk entry to cover the complete aggregate"
            )

        unpack_bootimg = (
            rebuilt
            .verification_provider
            .executable
        )

        factory_root = (
            rebuilt.output_path.parent
            / "validation-factory-unpacked"
        )

        final_root = (
            rebuilt.output_path.parent
            / "validation-final-unpacked"
        )

        factory_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        final_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        def inspect(
            image_path: Path,
            destination: Path,
            *,
            label: str,
        ) -> tuple[
            str,
            ...,
        ]:
            completed = subprocess.run(
                (
                    str(
                        unpack_bootimg
                    ),
                    "--boot_img",
                    str(
                        image_path
                    ),
                    "--out",
                    str(
                        destination
                    ),
                    "--format=mkbootimg",
                    "-0",
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            if completed.returncode != 0:
                stderr = (
                    completed.stderr
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

                stdout = (
                    completed.stdout
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

                raise RuntimeError(
                    "Boot Image Validation failed to independently "
                    f"inspect {label} vendor_boot: "
                    f"{stderr or stdout}"
                )

            parts = (
                completed
                .stdout
                .split(
                    b"\0"
                )
            )

            if (
                parts
                and parts[-1]
                == b""
            ):
                parts = (
                    parts[
                        :-1
                    ]
                )

            return tuple(
                value.decode(
                    "utf-8",
                    errors="strict",
                )
                for value
                in parts
            )

        factory_arguments = inspect(
            source_path,
            factory_root,
            label="canonical factory",
        )

        final_arguments = inspect(
            rebuilt.output_path,
            final_root,
            label="final rebuilt",
        )

        if not factory_arguments:
            raise RuntimeError(
                "factory vendor_boot Validation recovered no "
                "mkbootimg arguments"
            )

        if not final_arguments:
            raise RuntimeError(
                "rebuilt vendor_boot Validation recovered no "
                "mkbootimg arguments"
            )

        def flag_positions(
            arguments: tuple[
                str,
                ...,
            ],
            flag: str,
        ) -> tuple[
            int,
            ...,
        ]:
            return tuple(
                index
                for index, value
                in enumerate(
                    arguments
                )
                if value == flag
            )

        def exactly_one_value(
            arguments: tuple[
                str,
                ...,
            ],
            flag: str,
        ) -> str:
            positions = flag_positions(
                arguments,
                flag,
            )

            if len(
                positions
            ) != 1:
                raise RuntimeError(
                    "vendor_boot Validation expected exactly one "
                    f"{flag}; found {len(positions)}"
                )

            index = (
                positions[
                    0
                ]
            )

            if (
                index + 1
                >= len(
                    arguments
                )
            ):
                raise RuntimeError(
                    "vendor_boot Validation found a flag without "
                    f"a value: {flag}"
                )

            return arguments[
                index + 1
            ]

        factory_header_raw = exactly_one_value(
            factory_arguments,
            "--header_version",
        )

        final_header_raw = exactly_one_value(
            final_arguments,
            "--header_version",
        )

        try:
            factory_header_version = int(
                factory_header_raw
            )

            final_header_version = int(
                final_header_raw
            )
        except ValueError as error:
            raise RuntimeError(
                "vendor_boot Validation recovered a non-integer "
                "header version"
            ) from error

        canonical_header_version = (
            rebuilt
            .image_plan
            .composition
            .image
            .header_version
        )

        if (
            factory_header_version
            != canonical_header_version
            or final_header_version
            != canonical_header_version
        ):
            raise RuntimeError(
                "vendor_boot header version does not match canonical "
                "Boot Image Interpretation: "
                f"factory={factory_header_version}, "
                f"final={final_header_version}, "
                f"canonical={canonical_header_version}"
            )

        if (
            flag_positions(
                factory_arguments,
                "--kernel",
            )
            or flag_positions(
                final_arguments,
                "--kernel",
            )
        ):
            raise RuntimeError(
                "vendor_boot unexpectedly exposes a kernel payload"
            )

        empty_kernel_verified = True

        factory_fragments = flag_positions(
            factory_arguments,
            "--vendor_ramdisk_fragment",
        )

        final_fragments = flag_positions(
            final_arguments,
            "--vendor_ramdisk_fragment",
        )

        if (
            len(
                factory_fragments
            )
            != 1
            or len(
                final_fragments
            )
            != 1
        ):
            raise RuntimeError(
                "current vendor_boot Validation requires exactly one "
                "factory and one rebuilt vendor ramdisk fragment; "
                f"factory={len(factory_fragments)}, "
                f"final={len(final_fragments)}"
            )

        factory_fragment_index = (
            factory_fragments[
                0
            ]
        )

        final_fragment_index = (
            final_fragments[
                0
            ]
        )

        if (
            factory_fragment_index + 1
            >= len(
                factory_arguments
            )
            or final_fragment_index + 1
            >= len(
                final_arguments
            )
        ):
            raise RuntimeError(
                "vendor_boot Validation recovered a fragment flag "
                "without its payload path"
            )

        factory_fragment_path = Path(
            factory_arguments[
                factory_fragment_index + 1
            ]
        )

        final_fragment_path = Path(
            final_arguments[
                final_fragment_index + 1
            ]
        )

        if not factory_fragment_path.is_file():
            raise RuntimeError(
                "vendor_boot Validation did not materialize the "
                "factory vendor ramdisk fragment"
            )

        if not final_fragment_path.is_file():
            raise RuntimeError(
                "vendor_boot Validation did not materialize the "
                "rebuilt vendor ramdisk fragment"
            )

        expected_replacement = (
            ramdisk_evaluation
            .request
            .replacement_path
        )

        expected_size, expected_digest = (
            cls._file_identity(
                expected_replacement
            )
        )

        expected_bootconfig_path = None
        expected_bootconfig_size = None
        expected_bootconfig_digest = None

        if (
            bootconfig_evaluation
            is not None
        ):
            expected_bootconfig_path = (
                bootconfig_evaluation
                .request
                .replacement_path
            )

            (
                expected_bootconfig_size,
                expected_bootconfig_digest,
            ) = cls._file_identity(
                expected_bootconfig_path
            )

        final_fragment_size, final_fragment_digest = (
            cls._file_identity(
                final_fragment_path
            )
        )

        if (
            final_fragment_size
            != expected_size
            or final_fragment_digest
            != expected_digest
        ):
            raise RuntimeError(
                "final vendor_boot ramdisk does not correspond "
                "exactly to the accepted mutation input"
            )

        #
        # Confirm the regenerated single-entry table's observable fragment
        # semantics. Type/name are emitted independently by unpack_bootimg.
        #
        factory_ramdisk_type = exactly_one_value(
            factory_arguments,
            "--ramdisk_type",
        )

        final_ramdisk_type = exactly_one_value(
            final_arguments,
            "--ramdisk_type",
        )

        if (
            final_ramdisk_type
            != factory_ramdisk_type
            or final_ramdisk_type
            != str(
                composed_entry
                .entry
                .ramdisk_type
            )
        ):
            raise RuntimeError(
                "rebuilt vendor_boot changed canonical "
                "vendor ramdisk type"
            )

        factory_ramdisk_name = exactly_one_value(
            factory_arguments,
            "--ramdisk_name",
        )

        final_ramdisk_name = exactly_one_value(
            final_arguments,
            "--ramdisk_name",
        )

        if (
            final_ramdisk_name
            != factory_ramdisk_name
            or final_ramdisk_name
            != (
                composed_entry
                .entry
                .ramdisk_name
            )
        ):
            raise RuntimeError(
                "rebuilt vendor_boot changed canonical "
                "vendor ramdisk name"
            )

        #
        # Require the entire factory-derived reconstruction grammar to remain
        # stable. Only file payload locations are allowed to differ between
        # unpack directories.
        #
        if len(
            factory_arguments
        ) != len(
            final_arguments
        ):
            raise RuntimeError(
                "rebuilt vendor_boot changed the factory-derived "
                "mkbootimg argument population"
            )

        file_flags = {
            "--vendor_bootconfig",
            "--dtb",
            "--vendor_ramdisk_fragment",
        }

        index = 0

        while index < len(
            factory_arguments
        ):
            factory_value = (
                factory_arguments[
                    index
                ]
            )

            final_value = (
                final_arguments[
                    index
                ]
            )

            if factory_value != final_value:
                raise RuntimeError(
                    "rebuilt vendor_boot changed factory-derived "
                    "mkbootimg argument ordering/value at index "
                    f"{index}: "
                    f"{factory_value!r} != {final_value!r}"
                )

            if (
                factory_value
                in file_flags
            ):
                if (
                    index + 1
                    >= len(
                        factory_arguments
                    )
                ):
                    raise RuntimeError(
                        "vendor_boot Validation encountered "
                        f"{factory_value} without a value"
                    )

                factory_payload = Path(
                    factory_arguments[
                        index + 1
                    ]
                )

                final_payload = Path(
                    final_arguments[
                        index + 1
                    ]
                )

                if not factory_payload.is_file():
                    raise RuntimeError(
                        "factory vendor_boot Validation payload "
                        f"is unavailable for {factory_value}: "
                        f"{factory_payload}"
                    )

                if not final_payload.is_file():
                    raise RuntimeError(
                        "rebuilt vendor_boot Validation payload "
                        f"is unavailable for {factory_value}: "
                        f"{final_payload}"
                    )

                if (
                    factory_value
                    == "--vendor_ramdisk_fragment"
                ):
                    #
                    # Explicitly authorized complete ramdisk mutation.
                    #
                    final_size, final_digest = (
                        cls._file_identity(
                            final_payload
                        )
                    )

                    if (
                        final_size
                        != expected_size
                        or final_digest
                        != expected_digest
                    ):
                        raise RuntimeError(
                            "rebuilt vendor_boot fragment does not "
                            "match the exact authorized ramdisk "
                            "mutation input"
                        )

                elif (
                    factory_value
                    == "--vendor_bootconfig"
                    and bootconfig_evaluation
                    is not None
                ):
                    #
                    # Explicitly authorized TreeForge boot marker
                    # mutation.
                    #
                    if (
                        expected_bootconfig_path
                        is None
                        or expected_bootconfig_size
                        is None
                        or expected_bootconfig_digest
                        is None
                    ):
                        raise RuntimeError(
                            "authorized vendor_boot bootconfig "
                            "mutation lost its expected identity"
                        )

                    (
                        final_size,
                        final_digest,
                    ) = cls._file_identity(
                        final_payload
                    )

                    if (
                        final_size
                        != expected_bootconfig_size
                        or final_digest
                        != expected_bootconfig_digest
                    ):
                        raise RuntimeError(
                            "rebuilt vendor_boot bootconfig does not "
                            "match the exact authorized mutation input"
                        )

                    factory_bootconfig = (
                        factory_payload.read_bytes()
                    )

                    separator = (
                        b""
                        if (
                            not factory_bootconfig
                            or factory_bootconfig.endswith(
                                b"\n"
                            )
                        )
                        else b"\n"
                    )

                    marker = (
                        b"androidboot.treeforge=1\n"
                        b"androidboot.treeforge.image=vendor_boot\n"
                        + (
                            "androidboot.treeforge.payload_sha256="
                            f"{expected_digest}\n"
                        ).encode(
                            "ascii"
                        )
                    )

                    expected_bootconfig = (
                        factory_bootconfig
                        + separator
                        + marker
                    )

                    requested_bootconfig = (
                        expected_bootconfig_path
                        .read_bytes()
                    )

                    if (
                        requested_bootconfig
                        != expected_bootconfig
                    ):
                        raise RuntimeError(
                            "authorized TreeForge vendor_boot "
                            "bootconfig mutation is not exactly the "
                            "canonical factory bootconfig plus the "
                            "expected TreeForge marker"
                        )

                    if (
                        final_payload.read_bytes()
                        != expected_bootconfig
                    ):
                        raise RuntimeError(
                            "rebuilt vendor_boot bootconfig does not "
                            "contain exactly the canonical factory "
                            "bootconfig plus the authorized "
                            "TreeForge marker"
                        )

                else:
                    #
                    # Every payload not explicitly authorized for mutation
                    # remains byte-for-byte factory-exact.
                    #
                    (
                        factory_size,
                        factory_digest,
                    ) = cls._file_identity(
                        factory_payload
                    )

                    (
                        final_size,
                        final_digest,
                    ) = cls._file_identity(
                        final_payload
                    )

                    if (
                        final_size
                        != factory_size
                        or final_digest
                        != factory_digest
                    ):
                        raise RuntimeError(
                            "rebuilt vendor_boot changed an unchanged "
                            f"factory payload: {factory_value}"
                        )

                index += 2
                continue

            #
            # Every non-file value, including real empty strings such as
            # --board '' and --ramdisk_name '', must remain exact.
            #
            if (
                index > 0
                and factory_arguments[
                    index - 1
                ]
                not in file_flags
                and (
                    factory_value
                    != final_value
                )
            ):
                raise RuntimeError(
                    "rebuilt vendor_boot changed a canonical "
                    "mkbootimg scalar value"
                )

            index += 1

        return AndroidBootImageBootImageStructureValidation(
            container_kind="vendor_boot",
            output_path=(
                rebuilt.output_path
            ),
            header_version=(
                final_header_version
            ),
            ramdisk_verified=True,
            empty_kernel_verified=(
                empty_kernel_verified
            ),
            structure_verified=True,
        )



    @classmethod
    def _validate_final_init_boot_structure(
        cls,
        *,
        realization: AndroidBootImageRealizationResult,
        rebuilt,
    ) -> AndroidBootImageBootImageStructureValidation:
        if (
            rebuilt.image_plan.container_kind
            != "init_boot"
        ):
            raise ValueError(
                "final init_boot structural validator received "
                "a different container kind"
            )

        evaluation_matches = tuple(
            evaluation
            for evaluation
            in realization
            .mutation_analysis
            .evaluations
            if (
                evaluation.image_plan
                is rebuilt.image_plan
                and evaluation.content_changed
            )
        )

        if len(
            evaluation_matches
        ) != 1:
            raise RuntimeError(
                "rebuilt init_boot must retain exactly one changed "
                "mutation evaluation; "
                f"found {len(evaluation_matches)}"
            )

        evaluation = (
            evaluation_matches[0]
        )

        if (
            evaluation
            .request
            .target
            .component
            .semantic_name
            != "ramdisk"
        ):
            raise RuntimeError(
                "current init_boot reconstruction Validation "
                "expects the ramdisk mutation owner"
            )

        unpack_bootimg = (
            rebuilt
            .verification_provider
            .executable
        )

        validation_root = (
            rebuilt.output_path.parent
            / "validation-unpacked"
        )

        validation_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        completed = subprocess.run(
            (
                str(
                    unpack_bootimg
                ),
                "--boot_img",
                str(
                    rebuilt.output_path
                ),
                "--out",
                str(
                    validation_root
                ),
                "--format=mkbootimg",
                "-0",
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if completed.returncode != 0:
            stderr = (
                completed.stderr
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            raise RuntimeError(
                "Boot Image Validation failed to independently "
                f"inspect final init_boot: {stderr}"
            )

        arguments = tuple(
            value.decode(
                "utf-8",
                errors="strict",
            )
            for value
            in completed.stdout.split(
                b"\0"
            )
            if value
        )

        def argument_value(
            flag: str,
        ) -> str | None:
            try:
                index = arguments.index(
                    flag
                )
            except ValueError:
                return None

            if (
                index + 1
                >= len(
                    arguments
                )
            ):
                raise RuntimeError(
                    "unpack_bootimg emitted a flag without "
                    f"a value: {flag}"
                )

            return arguments[
                index + 1
            ]

        raw_header_version = (
            argument_value(
                "--header_version"
            )
        )

        if raw_header_version is None:
            raise RuntimeError(
                "final init_boot Validation did not recover "
                "a header version"
            )

        try:
            header_version = int(
                raw_header_version
            )
        except ValueError as error:
            raise RuntimeError(
                "final init_boot Validation recovered an invalid "
                f"header version: {raw_header_version!r}"
            ) from error

        canonical_header_version = (
            rebuilt
            .image_plan
            .composition
            .image
            .header_version
        )

        if (
            header_version
            != canonical_header_version
        ):
            raise RuntimeError(
                "final init_boot header version does not match "
                "the canonical boot-image interpretation: "
                f"{header_version} != "
                f"{canonical_header_version}"
            )

        unpacked_kernel_value = (
            argument_value(
                "--kernel"
            )
        )

        empty_kernel_verified = True

        if (
            unpacked_kernel_value
            is not None
        ):
            unpacked_kernel = Path(
                unpacked_kernel_value
            )

            if (
                unpacked_kernel.exists()
                and (
                    not unpacked_kernel.is_file()
                    or unpacked_kernel.stat().st_size
                    != 0
                )
            ):
                raise RuntimeError(
                    "final init_boot unexpectedly contains "
                    "a non-empty kernel payload"
                )

        unpacked_ramdisk_value = (
            argument_value(
                "--ramdisk"
            )
        )

        if (
            unpacked_ramdisk_value
            is None
        ):
            raise RuntimeError(
                "final init_boot Validation did not recover "
                "a ramdisk"
            )

        unpacked_ramdisk = Path(
            unpacked_ramdisk_value
        )

        if not unpacked_ramdisk.is_file():
            raise RuntimeError(
                "final init_boot Validation reported a "
                "missing unpacked ramdisk"
            )

        expected_path = (
            evaluation
            .request
            .replacement_path
        )

        expected_size, expected_digest = (
            cls._file_identity(
                expected_path
            )
        )

        actual_size, actual_digest = (
            cls._file_identity(
                unpacked_ramdisk
            )
        )

        if (
            actual_size
            != expected_size
            or actual_digest
            != expected_digest
        ):
            raise RuntimeError(
                "final init_boot ramdisk does not correspond "
                "to the accepted mutation input"
            )

        return AndroidBootImageBootImageStructureValidation(
            container_kind="init_boot",
            output_path=(
                rebuilt.output_path
            ),
            header_version=(
                header_version
            ),
            ramdisk_verified=True,
            empty_kernel_verified=(
                empty_kernel_verified
            ),
            structure_verified=True,
        )


    @classmethod
    def build(
        cls,
        realization: AndroidBootImageRealizationResult,
    ) -> AndroidBootImageValidationResult:
        if not isinstance(
            realization,
            AndroidBootImageRealizationResult,
        ):
            raise TypeError(
                "realization must be an "
                "AndroidBootImageRealizationResult"
            )

        physical_artifact_validations = []

        boot_image_structure_validations = []

        dtbo_structure_validations = []

        artifact_validations = []

        trust_edge_validations = []

        avbtool = None

        #
        # Exact component and mutation-input correspondence.
        #
        mutation_by_plan_id = {
            id(
                evaluation.request.target
            ): evaluation
            for evaluation
            in realization
            .mutation_analysis
            .evaluations
            if evaluation.content_changed
        }

        for realized_component in (
            realization.components
        ):
            output_size, output_digest = (
                cls._file_identity(
                    realized_component.output_path
                )
            )

            if (
                output_size
                != realized_component.size_bytes
                or output_digest
                != realized_component.content_sha256
            ):
                raise RuntimeError(
                    "realized Boot Image component bytes changed "
                    "after Realization"
                )

            if (
                realized_component.provider
                is
                AndroidBootImageRealizationProvider
                .EXACT_ARTIFACT
            ):
                source_path = (
                    realized_component
                    .plan
                    .component
                    .artifact
                    .path
                )

                if (
                    realized_component
                    .plan
                    .component
                    .artifact
                    .size_bytes
                    is not None
                    and source_path.stat().st_size
                    != (
                        realized_component
                        .plan
                        .component
                        .artifact
                        .size_bytes
                    )
                ):
                    raise RuntimeError(
                        "exact component authoritative source "
                        "no longer matches canonical Extraction "
                        "size metadata"
                    )

                canonical_digest = (
                    realized_component
                    .plan
                    .component
                    .artifact
                    .content_sha256
                )

                if canonical_digest is not None:
                    (
                        _,
                        source_canonical_digest,
                    ) = cls._file_identity(
                        source_path
                    )

                    if (
                        source_canonical_digest
                        != canonical_digest
                    ):
                        raise RuntimeError(
                            "exact component authoritative source "
                            "no longer matches canonical Extraction "
                            "SHA-256 metadata"
                        )

                validation_kind = (
                    "exact_component"
                )

            elif (
                realized_component.provider
                is
                AndroidBootImageRealizationProvider
                .MUTATION_INPUT
            ):
                evaluation = (
                    mutation_by_plan_id
                    .get(
                        id(
                            realized_component.plan
                        )
                    )
                )

                if evaluation is None:
                    raise RuntimeError(
                        "mutation-input component realization has "
                        "no exact mutation evaluation"
                    )

                source_path = (
                    evaluation
                    .request
                    .replacement_path
                )

                if (
                    output_size
                    != evaluation
                    .replacement_size_bytes
                    or output_digest
                    != evaluation
                    .replacement_sha256
                ):
                    raise RuntimeError(
                        "mutation-input component does not match "
                        "its accepted mutation evaluation"
                    )

                validation_kind = (
                    "mutation_component"
                )

            else:
                raise RuntimeError(
                    "Validation encountered an unsupported "
                    "component realization provider"
                )

            source_size, source_digest = (
                cls._file_identity(
                    source_path
                )
            )

            if (
                output_size
                != source_size
                or output_digest
                != source_digest
            ):
                raise RuntimeError(
                    "realized Boot Image component does not "
                    "correspond exactly to its authoritative source"
                )

            physical_artifact_validations.append(
                AndroidBootImagePhysicalArtifactValidation(
                    kind=(
                        validation_kind
                    ),
                    semantic_name=(
                        realized_component
                        .plan
                        .component
                        .semantic_name
                    ),
                    output_path=(
                        realized_component
                        .output_path
                    ),
                    source_path=(
                        source_path
                    ),
                    size_bytes=(
                        output_size
                    ),
                    content_sha256=(
                        output_digest
                    ),
                    source_correspondence_verified=True,
                    realization_identity_verified=True,
                )
            )

        #
        # Exact DTBO preservation correspondence.
        #
        for realized_dtbo in (
            realization.dtbo_containers
        ):
            output_size, output_digest = (
                cls._file_identity(
                    realized_dtbo.output_path
                )
            )

            if (
                output_size
                != realized_dtbo.size_bytes
                or output_digest
                != realized_dtbo.content_sha256
            ):
                raise RuntimeError(
                    "realized DTBO bytes changed after Realization"
                )

            interpreted_entries = (
                realized_dtbo
                .container
                .entries
            )

            if not interpreted_entries:
                raise RuntimeError(
                    "canonical DTBO container interpretation "
                    "contains no entries"
                )

            source_artifact = (
                interpreted_entries[0]
                .container
            )

            if any(
                entry.container
                is not source_artifact
                for entry
                in interpreted_entries
            ):
                raise RuntimeError(
                    "DTBO container Validation found entries "
                    "with different canonical Extraction "
                    "container identities"
                )

            source_path = (
                source_artifact.path
            )

            if not isinstance(
                source_path,
                Path,
            ):
                raise RuntimeError(
                    "canonical DTBO Extraction container "
                    "has no pathlib.Path"
                )

            source_size, source_digest = (
                cls._file_identity(
                    source_path
                )
            )

            if (
                source_artifact.size_bytes
                is not None
                and source_size
                != source_artifact.size_bytes
            ):
                raise RuntimeError(
                    "canonical DTBO source no longer matches "
                    "Extraction size metadata"
                )

            if (
                source_artifact.content_sha256
                is not None
                and source_digest
                != source_artifact.content_sha256
            ):
                raise RuntimeError(
                    "canonical DTBO source no longer matches "
                    "Extraction SHA-256 metadata"
                )

            if (
                output_size
                != source_size
                or output_digest
                != source_digest
            ):
                raise RuntimeError(
                    "realized DTBO container is not byte-exact "
                    "with its canonical source artifact"
                )

            dtbo_structure_validations.append(
                cls._validate_dtbo_structure(
                    realized_dtbo=(
                        realized_dtbo
                    ),
                )
            )

            physical_artifact_validations.append(
                AndroidBootImagePhysicalArtifactValidation(
                    kind="exact_dtbo_container",
                    semantic_name="dtbo",
                    output_path=(
                        realized_dtbo.output_path
                    ),
                    source_path=(
                        source_path
                    ),
                    size_bytes=(
                        output_size
                    ),
                    content_sha256=(
                        output_digest
                    ),
                    source_correspondence_verified=True,
                    realization_identity_verified=True,
                )
            )

        #
        # Independently inspect every currently supported rebuilt
        # container family.
        #
        for rebuilt in (
            realization.rebuilt_boot_images
        ):
            if (
                rebuilt.image_plan.container_kind
                == "init_boot"
            ):
                boot_image_structure_validations.append(
                    cls._validate_final_init_boot_structure(
                        realization=realization,
                        rebuilt=rebuilt,
                    )
                )

            elif (
                rebuilt.image_plan.container_kind
                == "vendor_boot"
            ):
                boot_image_structure_validations.append(
                    cls._validate_final_vendor_boot_structure(
                        realization=realization,
                        rebuilt=rebuilt,
                    )
                )

            else:
                raise RuntimeError(
                    "Boot Image Validation has no independent "
                    "structural validator for rebuilt container "
                    f"{rebuilt.image_plan.container_kind!r}"
                )

        #
        # Final rebuilt child AVB images.
        #
        for rebuilt in (
            realization.rebuilt_boot_images
        ):
            if not rebuilt.avb_complete:
                continue

            matching_resolutions = tuple(
                resolution
                for resolution
                in realization.avb_resolutions
                if (
                    resolution.contract.image_plan
                    is rebuilt.image_plan
                )
            )

            if len(
                matching_resolutions
            ) != 1:
                raise RuntimeError(
                    "AVB-complete rebuilt image must map to "
                    "exactly one AVB resolution; "
                    f"found {len(matching_resolutions)}"
                )

            resolution = (
                matching_resolutions[0]
            )

            signing_key_path = (
                resolution.signing_key_path
            )

            unsigned = (
                resolution
                .contract
                .algorithm_type
                == 0
            )

            if unsigned:
                if (
                    signing_key_path
                    is not None
                ):
                    raise RuntimeError(
                        "algorithm-NONE rebuilt AVB image unexpectedly "
                        "retained a private signing key"
                    )

                if (
                    resolution.derived_public_key
                    is not None
                ):
                    raise RuntimeError(
                        "algorithm-NONE rebuilt AVB image unexpectedly "
                        "retained a public signing identity"
                    )

                if (
                    resolution
                    .contract
                    .factory_public_key
                ):
                    raise RuntimeError(
                        "algorithm-NONE canonical AVB contract "
                        "unexpectedly carries a factory public key"
                    )

                if (
                    resolution
                    .parent_trust_update_required
                    is not False
                ):
                    raise RuntimeError(
                        "algorithm-NONE rebuilt AVB image cannot require "
                        "a signing-identity parent trust update"
                    )

            elif signing_key_path is None:
                raise RuntimeError(
                    "signed AVB-complete rebuilt image lost its "
                    "signing-key identity"
                )

            size_bytes, digest = (
                cls._file_identity(
                    rebuilt.output_path
                )
            )

            if (
                size_bytes
                != rebuilt.size_bytes
                or digest
                != rebuilt.content_sha256
            ):
                raise RuntimeError(
                    "rebuilt AVB image bytes changed after "
                    "Realization"
                )

            if avbtool is None:
                avbtool = cls._avbtool()

            cls._verify_image(
                avbtool=avbtool,
                image_path=(
                    rebuilt.output_path
                ),
                key_path=(
                    signing_key_path
                ),
            )

            artifact_validations.append(
                AndroidBootImageAvbArtifactValidation(
                    kind="rebuilt_boot_image",
                    partition_name=(
                        resolution
                        .contract
                        .partition_name
                    ),
                    output_path=(
                        rebuilt.output_path
                    ),
                    size_bytes=(
                        size_bytes
                    ),
                    content_sha256=(
                        digest
                    ),
                    realization_identity_verified=True,
                    cryptographic_verification_complete=True,
                    descriptor_population_verified=True,
                )
            )

        #
        # Regenerated standalone parent VBMeta images.
        #
        for parent in (
            realization.parent_vbmeta_realizations
        ):
            size_bytes, digest = (
                cls._file_identity(
                    parent.output_path
                )
            )

            if (
                size_bytes
                != parent.size_bytes
                or digest
                != parent.content_sha256
            ):
                raise RuntimeError(
                    "regenerated parent VBMeta bytes changed "
                    "after Realization"
                )

            if avbtool is None:
                avbtool = cls._avbtool()

            cls._verify_standalone_vbmeta_authentication(
                avbtool=avbtool,
                image_path=(
                    parent.output_path
                ),
                expected_public_key=(
                    parent.derived_public_key
                ),
            )

            rewritten_blob = (
                parent
                .rewrite
                .rewritten_descriptor_blob
            )

            materialized_bytes = (
                parent.output_path
                .read_bytes()
            )

            occurrence_count = (
                materialized_bytes
                .count(
                    rewritten_blob
                )
            )

            if occurrence_count != 1:
                raise RuntimeError(
                    "regenerated parent VBMeta must contain its "
                    "exact rewritten descriptor population once; "
                    f"found {occurrence_count}"
                )

            parent_partition_name = (
                getattr(
                    parent
                    .parent_vbmeta
                    .partition,
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
                    "validated parent VBMeta has no canonical "
                    "partition name"
                )

            artifact_validations.append(
                AndroidBootImageAvbArtifactValidation(
                    kind="standalone_vbmeta",
                    partition_name=(
                        parent_partition_name
                    ),
                    output_path=(
                        parent.output_path
                    ),
                    size_bytes=(
                        size_bytes
                    ),
                    content_sha256=(
                        digest
                    ),
                    realization_identity_verified=True,
                    cryptographic_verification_complete=True,
                    descriptor_population_verified=True,
                )
            )

        #
        # Exact realized chain-descriptor ↔ child public-key
        # correspondence.
        #
        for rewrite in (
            realization.parent_vbmeta_rewrites
        ):
            parent_partition_name = (
                getattr(
                    rewrite
                    .parent_vbmeta
                    .partition,
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
                    "AVB trust-edge validation encountered a "
                    "parent without canonical partition identity"
                )

            for (
                trust_change,
                descriptor_index,
                rewritten_chain,
            ) in zip(
                rewrite.trust_changes,
                rewrite.descriptor_indexes,
                rewrite.rewritten_chain_descriptors,
                strict=True,
            ):
                if (
                    trust_change
                    .source_resolution
                    is not None
                ):
                    expected_public_key = (
                        trust_change
                        .source_resolution
                        .derived_public_key
                    )

                    source_kind = (
                        "rebuilt_boot_image"
                    )

                else:
                    source_parent = (
                        trust_change
                        .source_parent_realization
                    )

                    if (
                        source_parent
                        is None
                    ):
                        raise RuntimeError(
                            "recursive AVB trust edge lost its "
                            "realized source"
                        )

                    expected_public_key = (
                        source_parent
                        .derived_public_key
                    )

                    source_kind = (
                        "standalone_vbmeta"
                    )

                if expected_public_key is None:
                    raise RuntimeError(
                        "realized AVB trust edge has no source "
                        "public signing identity"
                    )

                if (
                    rewritten_chain.public_key
                    != expected_public_key
                    or (
                        rewritten_chain.partition_name
                        != trust_change.target_partition
                    )
                ):
                    raise RuntimeError(
                        "realized parent descriptor does not "
                        "correspond to the exact realized child "
                        "AVB identity"
                    )

                trust_edge_validations.append(
                    AndroidBootImageAvbTrustEdgeValidation(
                        parent_partition=(
                            parent_partition_name
                        ),
                        target_partition=(
                            trust_change
                            .target_partition
                        ),
                        descriptor_index=(
                            descriptor_index
                        ),
                        source_kind=(
                            source_kind
                        ),
                        public_key_correspondence_verified=True,
                    )
                )

        provider_invocations_verified = all(
            invocation.returncode == 0
            for invocation
            in realization.provider_invocations
        )

        if not provider_invocations_verified:
            raise RuntimeError(
                "Boot Image Validation found a retained failed "
                "provider invocation"
            )

        #
        # Every rewrite already has a first-class Realization
        # disposition. Validation additionally classifies whether the
        # entire realized graph reached a cryptographically materialized
        # boundary.
        #
        realized_trust_graph_complete = (
            realization
            .avb_signing_material_required_count
            == 0
            and (
                realization
                .parent_vbmeta_signing_material_required_count
                == 0
            )
        )

        expected_physical_validation_count = (
            len(
                realization.components
            )
            + len(
                realization.dtbo_containers
            )
        )

        if (
            len(
                physical_artifact_validations
            )
            != expected_physical_validation_count
        ):
            raise RuntimeError(
                "Boot Image Validation did not account for every "
                "physical Realization output"
            )

        if (
            len(
                dtbo_structure_validations
            )
            != len(
                realization.dtbo_containers
            )
        ):
            raise RuntimeError(
                "Boot Image Validation did not structurally "
                "validate every realized DTBO container"
            )

        if (
            len(
                boot_image_structure_validations
            )
            != len(
                realization.rebuilt_boot_images
            )
        ):
            raise RuntimeError(
                "Boot Image Validation did not structurally "
                "validate every rebuilt boot-family image"
            )

        expected_avb_artifact_count = (
            sum(
                rebuilt.avb_complete
                for rebuilt
                in realization.rebuilt_boot_images
            )
            + len(
                realization.parent_vbmeta_realizations
            )
        )

        if (
            len(
                artifact_validations
            )
            != expected_avb_artifact_count
        ):
            raise RuntimeError(
                "Boot Image Validation did not account for every "
                "realized AVB-bearing artifact"
            )

        expected_trust_edges = sum(
            rewrite.changed_descriptor_count
            for rewrite
            in realization.parent_vbmeta_rewrites
        )

        if (
            len(
                trust_edge_validations
            )
            != expected_trust_edges
        ):
            raise RuntimeError(
                "Boot Image Validation did not account for every "
                "realized AVB trust edge"
            )

        physical_integrity_complete = (
            all(
                (
                    value.source_correspondence_verified
                    and value.realization_identity_verified
                )
                for value
                in physical_artifact_validations
            )
            and all(
                value.structure_verified
                for value
                in boot_image_structure_validations
            )
        )

        if not physical_integrity_complete:
            raise RuntimeError(
                "Boot Image physical artifact Validation "
                "did not complete"
            )

        cryptographic_integrity_complete = all(
            (
                value.realization_identity_verified
                and value.cryptographic_verification_complete
                and value.descriptor_population_verified
            )
            for value
            in artifact_validations
        )

        if not cryptographic_integrity_complete:
            raise RuntimeError(
                "Boot Image AVB artifact integrity validation "
                "did not complete"
            )

        #
        # A post-AVB bootloader trust-anchor requirement is an explicit
        # external trust boundary, not a cryptographic artifact failure.
        #
        bootloader_trust_resolved = not (
            realization
            .post_avb_conditional_requirements
        )

        #
        # Flashability is applicable only when this invocation actually
        # changed content and therefore attempted to produce a replacement
        # boot-family chain. An exact-preservation/no-mutation invocation
        # validates successfully, but it did not produce a new flashable
        # chain and must not claim that it did.
        #
        flashable_chain_applicable = any(
            evaluation.content_changed
            for evaluation
            in realization.mutation_analysis.evaluations
        )

        rebuilt_flashable = (
            bool(
                realization.rebuilt_boot_images
            )
            and all(
                rebuilt.avb_complete
                for rebuilt
                in realization.rebuilt_boot_images
            )
        )

        #
        # "Flashable chain complete" describes the generated partition
        # population and its internally validated AVB graph.
        #
        # Whether a particular physical bootloader accepts the resulting
        # top-level signing identity is an external hardware-policy fact.
        # Keep reporting bootloader_trust_resolved independently, but do
        # not collapse that fact into artifact completeness.
        #
        flashable_chain_complete = (
            flashable_chain_applicable
            and cryptographic_integrity_complete
            and realized_trust_graph_complete
            and rebuilt_flashable
        )

        disposition = (
            AndroidBootImageValidationDisposition
            .PASS
            if (
                not flashable_chain_applicable
                or flashable_chain_complete
            )
            else (
                AndroidBootImageValidationDisposition
                .PARTIAL
            )
        )

        return AndroidBootImageValidationResult(
            realization=realization,
            physical_artifacts=tuple(
                physical_artifact_validations
            ),
            boot_image_structures=tuple(
                boot_image_structure_validations
            ),
            dtbo_structures=tuple(
                dtbo_structure_validations
            ),
            provider_invocations_verified=(
                provider_invocations_verified
            ),
            avb_artifacts=tuple(
                artifact_validations
            ),
            avb_trust_edges=tuple(
                trust_edge_validations
            ),
            cryptographic_integrity_complete=(
                cryptographic_integrity_complete
            ),
            realized_trust_graph_complete=(
                realized_trust_graph_complete
            ),
            bootloader_trust_resolved=(
                bootloader_trust_resolved
            ),
            flashable_chain_applicable=(
                flashable_chain_applicable
            ),
            flashable_chain_complete=(
                flashable_chain_complete
            ),
            disposition=(
                disposition
            ),
        )


__all__ = (
    "AndroidBootImagePhysicalArtifactValidation",
    "AndroidBootImageBootImageStructureValidation",
    "AndroidBootImageDtboStructureValidation",
    "AndroidBootImageAvbArtifactValidation",
    "AndroidBootImageAvbTrustEdgeValidation",
    "AndroidBootImageValidationDisposition",
    "AndroidBootImageValidationResult",
    "AndroidBootImageValidator",
)
