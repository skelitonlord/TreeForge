from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from treeforge.android.providers.provenance import (
    ProviderArtifactProvenance,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.android.providers.content_observation import (
    ProviderContentObservation,
)


class ProviderArtifactKind(
    StrEnum,
):
    """
    Broad structural kind assigned to one discovered provider artifact.

    Kind does not imply Android semantic meaning.

    ProviderArtifact.kind_evidence records how this structural interpretation
    was obtained.
    """

    IMAGE = "image"
    ARCHIVE = "archive"
    TEXT = "text"
    SCRIPT = "script"
    BINARY = "binary"
    UNKNOWN = "unknown"


class ProviderArtifactKindEvidence(
    StrEnum,
):
    """
    Evidence supporting an artifact's structural kind.

    CONTENT means TreeForge directly verified the structure from artifact
    contents during discovery.

    FILENAME means the kind is a non-authoritative filename or extension hint.

    UNKNOWN means no structural interpretation could yet be established.
    """

    CONTENT = "content"
    FILENAME = "filename"
    UNKNOWN = "unknown"


class ProviderArtifactClassification(
    StrEnum,
):
    """
    Optional semantic interpretation understood by TreeForge.

    Semantic classification is enrichment layered on top of discovery.

    UNKNOWN is an explicit first-class state and never prevents an artifact
    from being discovered or preserved.
    """

    UNKNOWN = "unknown"

    FACTORY_IMAGE_ARCHIVE = (
        "factory_image_archive"
    )
    IMAGE_ARCHIVE = (
        "image_archive"
    )
    ANDROID_INFO = (
        "android_info"
    )
    FASTBOOT_INFO = (
        "fastboot_info"
    )
    FLASH_SCRIPT = (
        "flash_script"
    )

    BOOT = "boot"
    INIT_BOOT = "init_boot"
    VENDOR_BOOT = "vendor_boot"
    VENDOR_KERNEL_BOOT = (
        "vendor_kernel_boot"
    )
    RECOVERY = "recovery"

    SYSTEM = "system"
    SYSTEM_EXT = "system_ext"
    SYSTEM_OTHER = "system_other"
    PRODUCT = "product"
    VENDOR = "vendor"
    ODM = "odm"
    USERDATA = "userdata"

    VENDOR_DLKM = "vendor_dlkm"
    SYSTEM_DLKM = "system_dlkm"
    ODM_DLKM = "odm_dlkm"

    SUPER = "super"
    SUPER_EMPTY = "super_empty"

    VBMETA = "vbmeta"
    VBMETA_SYSTEM = "vbmeta_system"
    VBMETA_VENDOR = "vbmeta_vendor"

    DTBO = "dtbo"

    PVMFW = "pvmfw"

    BOOTLOADER = "bootloader"
    FIRMWARE = "firmware"

    EMBEDDED_CONTROLLER_FIRMWARE = (
        "embedded_controller_firmware"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderArtifact:
    """
    One exact artifact discovered from a provider source.

    Discovery identity and discovery provenance are authoritative.

    ``kind`` describes the current broad structural interpretation.

    ``kind_evidence`` records whether that interpretation was observed from
    contents, inferred from the filename, or remains unknown.

    ``classification`` is semantic enrichment and may remain UNKNOWN
    indefinitely without causing the artifact to disappear from TreeForge.

    Physical accessibility and materialization are intentionally not owned
    by Discovery. Those concerns belong to Extraction.
    """

    source_name: str
    name: str

    kind: ProviderArtifactKind

    classification: (
        ProviderArtifactClassification
    )

    provider_id: str
    source_type: ProviderSourceType

    provenance: (
        ProviderArtifactProvenance
    ) = ProviderArtifactProvenance()

    kind_evidence: (
        ProviderArtifactKindEvidence
    ) = ProviderArtifactKindEvidence.UNKNOWN

    content_observations: tuple[
        ProviderContentObservation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        self._validate_string(
            self.source_name,
            field_name="source_name",
        )

        self._validate_string(
            self.name,
            field_name="name",
        )

        if not isinstance(
            self.kind,
            ProviderArtifactKind,
        ):
            raise TypeError(
                "kind must be a ProviderArtifactKind"
            )

        if not isinstance(
            self.kind_evidence,
            ProviderArtifactKindEvidence,
        ):
            raise TypeError(
                "kind_evidence must be a "
                "ProviderArtifactKindEvidence"
            )

        if not isinstance(
            self.content_observations,
            tuple,
        ):
            raise TypeError(
                "content_observations must be a tuple"
            )

        for observation in (
            self.content_observations
        ):
            if not isinstance(
                observation,
                ProviderContentObservation,
            ):
                raise TypeError(
                    "content_observations must contain "
                    "ProviderContentObservation instances"
                )

        signatures = tuple(
            (
                observation.signature,
                observation.offset,
                observation.matched_bytes,
            )
            for observation
            in self.content_observations
        )

        if (
            len(signatures)
            != len(
                set(
                    signatures
                )
            )
        ):
            raise ValueError(
                "content_observations must not "
                "contain duplicates"
            )

        canonical_observations = tuple(
            sorted(
                self.content_observations,
                key=lambda observation: (
                    observation.offset,
                    observation.signature.value,
                    observation.confidence.value,
                    observation.matched_bytes,
                ),
            )
        )

        object.__setattr__(
            self,
            "content_observations",
            canonical_observations,
        )

        if (
            self.kind
            is ProviderArtifactKind.UNKNOWN
            and self.kind_evidence
            is not ProviderArtifactKindEvidence.UNKNOWN
        ):
            raise ValueError(
                "UNKNOWN artifact kind must use "
                "UNKNOWN kind evidence"
            )

        if (
            self.kind
            is not ProviderArtifactKind.UNKNOWN
            and self.kind_evidence
            is ProviderArtifactKindEvidence.UNKNOWN
        ):
            raise ValueError(
                "known artifact kind requires "
                "kind evidence"
            )

        if not isinstance(
            self.classification,
            ProviderArtifactClassification,
        ):
            raise TypeError(
                "classification must be a "
                "ProviderArtifactClassification"
            )

        self._validate_string(
            self.provider_id,
            field_name="provider_id",
        )

        if not isinstance(
            self.source_type,
            ProviderSourceType,
        ):
            raise TypeError(
                "source_type must be a ProviderSourceType"
            )

        if not isinstance(
            self.provenance,
            ProviderArtifactProvenance,
        ):
            raise TypeError(
                "provenance must be a "
                "ProviderArtifactProvenance"
            )

    @staticmethod
    def _validate_string(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )

    @property
    def has_content_observations(
        self,
    ) -> bool:
        return bool(
            self.content_observations
        )

    @property
    def is_known(
        self,
    ) -> bool:
        return (
            self.classification
            is not ProviderArtifactClassification.UNKNOWN
        )

    @property
    def is_unknown(
        self,
    ) -> bool:
        return not self.is_known

    @property
    def has_content_verified_kind(
        self,
    ) -> bool:
        return (
            self.kind_evidence
            is ProviderArtifactKindEvidence.CONTENT
        )

    @property
    def has_filename_inferred_kind(
        self,
    ) -> bool:
        return (
            self.kind_evidence
            is ProviderArtifactKindEvidence.FILENAME
        )

    @property
    def is_image(
        self,
    ) -> bool:
        return (
            self.kind
            is ProviderArtifactKind.IMAGE
        )

    @property
    def parent_source_name(
        self,
    ) -> str | None:
        return (
            self.provenance
            .parent_source_name
        )

    @property
    def member_path(
        self,
    ) -> str | None:
        return (
            self.provenance
            .member_path
        )

    @property
    def container_depth(
        self,
    ) -> int:
        return (
            self.provenance
            .container_depth
        )

    @property
    def size_bytes(
        self,
    ) -> int | None:
        return (
            self.provenance
            .size_bytes
        )

    @property
    def compressed_size_bytes(
        self,
    ) -> int | None:
        return (
            self.provenance
            .compressed_size_bytes
        )

    @property
    def compression_method(
        self,
    ) -> int | None:
        return (
            self.provenance
            .compression_method
        )

    @property
    def crc32(
        self,
    ) -> int | None:
        return (
            self.provenance
            .crc32
        )