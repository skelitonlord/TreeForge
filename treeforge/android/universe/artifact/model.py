from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
    FilesystemMetadataInventoryEntry,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
)


class AndroidUniverseArtifactKind(
    StrEnum,
):
    """
    Canonical semantic family of one Android filesystem artifact.

    Kinds describe what an artifact is. Reconstruction disposition is
    represented independently by AndroidUniverseArtifactDisposition.

    UNKNOWN is intentional and preserves artifacts for which Universe does
    not yet have sufficient semantic classification knowledge.
    """

    UNKNOWN = "unknown"

    # Android semantic configuration sources.
    INIT_RC = "init_rc"
    FSTAB = "fstab"
    UEVENTD_RC = "ueventd_rc"
    PROPERTY_FILE = "property_file"

    VINTF_MANIFEST = "vintf_manifest"
    VINTF_MATRIX = "vintf_matrix"
    VINTF_XML = "vintf_xml"

    SELINUX_POLICY = "selinux_policy"
    SELINUX_CONTEXTS = "selinux_contexts"

    PERMISSION_XML = "permission_xml"
    MEDIA_CONFIGURATION = "media_configuration"

    # Native/runtime executable artifacts.
    HAL_SHARED_LIBRARY = "hal_shared_library"
    SHARED_LIBRARY = "shared_library"
    HARDWARE_SERVICE = "hardware_service"
    EXECUTABLE = "executable"

    # Kernel artifacts.
    KERNEL_MODULE = "kernel_module"
    KERNEL_MODULE_METADATA = "kernel_module_metadata"

    # Device/runtime payloads.
    FIRMWARE = "firmware"

    APEX = "apex"
    APK = "apk"
    RUNTIME_RESOURCE_OVERLAY = "runtime_resource_overlay"
    FRAMEWORK_JAR = "framework_jar"
    JAVA_LIBRARY = "java_library"

    # APEX filesystem-internal metadata/support payloads.
    APEX_MANIFEST_METADATA = "apex_manifest_metadata"
    APEX_SUPPORT_METADATA = "apex_support_metadata"
    CTS_SHIM_ALLOWED_HASHES = "cts_shim_allowed_hashes"

    # ART runtime/compiler output.
    ART_RUNTIME_ARTIFACT = "art_runtime_artifact"

    # Filesystem integrity metadata.
    FSVERITY_METADATA = "fsverity_metadata"

    # Android input configuration.
    ANDROID_KEY_LAYOUT = "android_key_layout"
    ANDROID_KEY_CHARACTER_MAP = "android_key_character_map"
    ANDROID_INPUT_DEVICE_CONFIGURATION = (
        "android_input_device_configuration"
    )

    # Specialized runtime/device artifacts.
    CHRE_NANOAPP_METADATA = "chre_nanoapp_metadata"
    EBPF_OBJECT = "ebpf_object"
    MODEM_PROFILE = "modem_profile"
    OPENCL_ICD_CONFIGURATION = "opencl_icd_configuration"

    # Installed data/resource payloads.
    FONT = "font"
    FONT_CONFIGURATION = "font_configuration"

    MEDIA_ASSET = "media_asset"
    WALLPAPER_ASSET = "wallpaper_asset"

    HYPHENATION_DICTIONARY = "hyphenation_dictionary"
    HYPHENATION_LICENSE = "hyphenation_license"

    MACHINE_LEARNING_MODEL = "machine_learning_model"
    SPEECH_MODEL_DATA = "speech_model_data"

    RUNTIME_BITCODE = "runtime_bitcode"
    ARCHIVE = "archive"

    # Security and integrity material.
    TRUST_CERTIFICATE = "trust_certificate"
    OTA_CERTIFICATE_ARCHIVE = "ota_certificate_archive"
    FSVERITY_SIGNATURE = "fsverity_signature"
    SECCOMP_POLICY = "seccomp_policy"
    AVB_PUBLIC_KEY = "avb_public_key"

    # Android platform/runtime configuration.
    COMPATIBILITY_CONFIGURATION = (
        "compatibility_configuration"
    )
    DEFAULT_PERMISSION_CONFIGURATION = (
        "default_permission_configuration"
    )
    RUNTIME_CLASSPATH_CONFIGURATION = (
        "runtime_classpath_configuration"
    )
    LINKER_CONFIGURATION = "linker_configuration"
    NATIVE_LIBRARY_CONFIGURATION = (
        "native_library_configuration"
    )
    FILESYSTEM_CONFIGURATION = (
        "filesystem_configuration"
    )
    ACCOUNT_DATABASE = "account_database"
    BUILD_FEATURE_METADATA = "build_feature_metadata"
    NOTICE_METADATA = "notice_metadata"
    TIMEZONE_DATA = "timezone_data"
    ICU_RUNTIME_DATA = "icu_runtime_data"
    ANDROID_BUILD_DEFINITION = "android_build_definition"
    PREFERRED_APP_CONFIGURATION = (
        "preferred_app_configuration"
    )

    # Device/platform configuration and calibration.
    UWB_CONFIGURATION = "uwb_configuration"
    UWB_CALIBRATION = "uwb_calibration"

    AUDIO_CONFIGURATION = "audio_configuration"
    AUDIO_DSP_DATA = "audio_dsp_data"
    BLUETOOTH_CONFIGURATION = "bluetooth_configuration"

    MODEM_CONFIGURATION = "modem_configuration"
    WIFI_CONFIGURATION = "wifi_configuration"

    SENSOR_CONFIGURATION = "sensor_configuration"
    SENSOR_CALIBRATION = "sensor_calibration"

    DISPLAY_CONFIGURATION = "display_configuration"
    DISPLAY_CALIBRATION = "display_calibration"

    POWER_CONFIGURATION = "power_configuration"
    THERMAL_CONFIGURATION = "thermal_configuration"

    PARAMETER_FRAMEWORK_CONFIGURATION = (
        "parameter_framework_configuration"
    )
    KERNEL_CONFIGURATION = "kernel_configuration"

    CHRE_RUNTIME_DATA = "chre_runtime_data"
    ESIM_SUPPORT_DATA = "esim_support_data"

    TRACING_CONFIGURATION = "tracing_configuration"
    PROTOLOG_CONFIGURATION = "protolog_configuration"

    DEVICE_CALIBRATION_DATA = "device_calibration_data"
    CAMERA_CONFIGURATION = "camera_configuration"

    VIRTUALIZATION_CONFIGURATION = "virtualization_configuration"
    VIRTUALIZATION_RUNTIME_ARTIFACT = (
        "virtualization_runtime_artifact"
    )

    BOOTLOADER_PAYLOAD = "bootloader_payload"

    # Additional audited platform/runtime families.
    GNSS_CONFIGURATION = "gnss_configuration"
    NFC_CONFIGURATION = "nfc_configuration"
    FILESYSTEM_TOOL_CONFIGURATION = (
        "filesystem_tool_configuration"
    )
    SHELL_CONFIGURATION = "shell_configuration"

    INPUT_METHOD_DATA = "input_method_data"
    FACE_DETECTION_MODEL_DATA = (
        "face_detection_model_data"
    )

    CERTIFICATE_CHAIN = "certificate_chain"

    KERNEL_MODULE_CONFIGURATION = (
        "kernel_module_configuration"
    )

    CHARGER_CONFIGURATION = "charger_configuration"
    TOUCH_CONFIGURATION = "touch_configuration"
    RECOVERY_CONFIGURATION = "recovery_configuration"

    # Known runtime/support metadata with no reconstruction semantics.
    SYSTEM_RUNTIME_METADATA = "system_runtime_metadata"

class AndroidUniverseArtifactClassificationOrigin(
    StrEnum,
):
    """
    Origin of the semantic classification assigned to one artifact.

    PARSING_EVIDENCE means Universe classified the artifact from canonical
    parser-family/source identity retained by Parsing.

    APEX_EVIDENCE means Universe classified the artifact by reconciling its
    exact canonical Extraction filesystem lineage with an exact canonical
    AndroidUniverseApexRequirement.

    PATH_CLASSIFIER means Universe classified the artifact from its canonical
    filesystem path using the artifact classifier.

    UNRESOLVED means no available canonical evidence provided a semantic
    classification.
    """

    PARSING_EVIDENCE = "parsing_evidence"
    APEX_EVIDENCE = "apex_evidence"
    PATH_CLASSIFIER = "path_classifier"
    UNRESOLVED = "unresolved"


class AndroidUniverseArtifactDeploymentRole(
    StrEnum,
):
    """
    Canonical deployment relationship of one filesystem artifact.

    This describes how the artifact relates to the Android runtime filesystem,
    independently of its semantic artifact kind and Reconstruction
    disposition.

    DIRECT_PARTITION means the file belongs to the canonical filesystem
    directly extracted from the selected partition image and is eligible for
    independent source-tree installation.

    ALTERNATIVE_PARTITION means the file belongs to a direct partition
    filesystem that represents a non-selected slot/variant of a canonical
    partition base name.

    NESTED_FILESYSTEM means the file belongs to a filesystem derived beneath
    another container/filesystem rather than directly from the selected
    partition image.

    BOOT_FILESYSTEM means the file belongs to boot/ramdisk/CPIO-derived
    filesystem state and must not be independently installed as a normal
    partition proprietary artifact.
    """

    DIRECT_PARTITION = "direct_partition"
    ALTERNATIVE_PARTITION = "alternative_partition"
    NESTED_FILESYSTEM = "nested_filesystem"
    BOOT_FILESYSTEM = "boot_filesystem"


class AndroidUniverseArtifactDisposition(
    StrEnum,
):
    """
    Universe reconstruction disposition for one concrete filesystem artifact.

    UNCLASSIFIED is intentional: the artifact exists canonically and Universe
    has taken ownership of deciding what reconstruction obligation it creates,
    but no family-specific semantic interpreter has classified it yet.
    """

    UNCLASSIFIED = "unclassified"
    SEMANTIC_SOURCE = "semantic_source"
    PRESERVE = "preserve"
    INVENTORY_ONLY = "inventory_only"
    IGNORE = "ignore"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtifactRequirement:
    """
    Canonical Universe requirement for one exact Android filesystem file.

    The requirement preserves both the containing canonical filesystem
    inventory entry and the exact FilesystemMetadataEntry by identity.

    Partition identity, Extraction lineage, Android path, ownership metadata,
    size, xattrs, and other literal filesystem facts therefore remain delegated
    to their canonical upstream objects rather than being copied into Universe.
    """

    inventory_entry: FilesystemMetadataInventoryEntry
    metadata_entry: FilesystemMetadataEntry
    deployment_role: AndroidUniverseArtifactDeploymentRole

    kinds: tuple[
        AndroidUniverseArtifactKind,
        ...,
    ] = (
        AndroidUniverseArtifactKind.UNKNOWN,
    )

    disposition: AndroidUniverseArtifactDisposition = (
        AndroidUniverseArtifactDisposition.UNCLASSIFIED
    )

    classification_origin: (
        AndroidUniverseArtifactClassificationOrigin
    ) = (
        AndroidUniverseArtifactClassificationOrigin.UNRESOLVED
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.inventory_entry,
            FilesystemMetadataInventoryEntry,
        ):
            raise TypeError(
                "inventory_entry must be a "
                "FilesystemMetadataInventoryEntry"
            )

        if not isinstance(
            self.metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "metadata_entry must be a "
                "FilesystemMetadataEntry"
            )

        if not isinstance(
            self.deployment_role,
            AndroidUniverseArtifactDeploymentRole,
        ):
            raise TypeError(
                "deployment_role must be an "
                "AndroidUniverseArtifactDeploymentRole"
            )

        if (
            self.metadata_entry.entry_type
            is not FilesystemEntryType.FILE
        ):
            raise ValueError(
                "artifact requirements must reference "
                "regular filesystem files"
            )

        if not isinstance(
            self.kinds,
            tuple,
        ):
            raise TypeError(
                "kinds must be a tuple"
            )

        if not self.kinds:
            raise ValueError(
                "kinds must contain at least one "
                "AndroidUniverseArtifactKind"
            )

        if any(
            not isinstance(
                kind,
                AndroidUniverseArtifactKind,
            )
            for kind in self.kinds
        ):
            raise TypeError(
                "kinds must contain only "
                "AndroidUniverseArtifactKind values"
            )

        if len(set(self.kinds)) != len(self.kinds):
            raise ValueError(
                "kinds must not contain duplicates"
            )

        if self.kinds != tuple(
            sorted(
                self.kinds,
                key=lambda kind: kind.value,
            )
        ):
            raise ValueError(
                "kinds must use deterministic ordering"
            )

        if (
            AndroidUniverseArtifactKind.UNKNOWN
            in self.kinds
            and len(self.kinds) != 1
        ):
            raise ValueError(
                "unknown artifact kind cannot coexist "
                "with classified semantic kinds"
            )

        if not isinstance(
            self.disposition,
            AndroidUniverseArtifactDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidUniverseArtifactDisposition"
            )

        if not isinstance(
            self.classification_origin,
            AndroidUniverseArtifactClassificationOrigin,
        ):
            raise TypeError(
                "classification_origin must be an "
                "AndroidUniverseArtifactClassificationOrigin"
            )

        if (
            self.kinds
            == (
                AndroidUniverseArtifactKind.UNKNOWN,
            )
            and self.classification_origin
            is not AndroidUniverseArtifactClassificationOrigin.UNRESOLVED
        ):
            raise ValueError(
                "unknown artifact kind must have unresolved "
                "classification origin"
            )

        if (
            self.kinds
            != (
                AndroidUniverseArtifactKind.UNKNOWN,
            )
            and self.classification_origin
            is AndroidUniverseArtifactClassificationOrigin.UNRESOLVED
        ):
            raise ValueError(
                "classified artifact kind must preserve "
                "its classification origin"
            )

        canonical_entry = (
            self.inventory_entry
            .result
            .metadata
            .entries
            .get(
                self.metadata_entry.path
            )
        )

        if (
            canonical_entry
            is not self.metadata_entry
        ):
            raise ValueError(
                "metadata_entry must be preserved by exact identity "
                "from inventory_entry"
            )

    @property
    def partition_name(
        self,
    ) -> str | None:
        """
        Return the canonical partition name.
        """

        return (
            self.inventory_entry
            .partition_name
        )

    @property
    def android_path(
        self,
    ) -> str:
        """
        Return the canonical Android filesystem path.
        """

        return (
            self.metadata_entry
            .path
        )

    @property
    def size(
        self,
    ) -> int:
        """
        Return the canonical file size.
        """

        return (
            self.metadata_entry
            .size
        )

    @property
    def identity_key(
        self,
    ) -> tuple[
        int,
        int,
    ]:
        """
        Return exact canonical upstream object identity.

        Universe does not manufacture filesystem identity. The containing
        Extraction artifact and exact FilesystemMetadataEntry remain owned by
        their canonical upstream stages.
        """

        return (
            id(
                self.inventory_entry.artifact
            ),
            id(
                self.metadata_entry
            ),
        )

    @property
    def key(
        self,
    ) -> tuple[
        str,
        str,
    ]:
        """
        Return the deterministic artifact ordering key.

        The canonical Extraction artifact path distinguishes independent
        physical filesystems that may share partition ownership and
        filesystem-native paths.
        """

        return (
            self.inventory_entry
            .artifact
            .path
            .as_posix(),
            self.metadata_entry.path,
        )

    @property
    def requirement_id(
        self,
    ) -> str:
        """
        Return a stable human-readable Universe requirement identifier.
        """

        return (
            "artifact:"
            f"{self.inventory_entry.artifact.path.as_posix()}:"
            f"{self.metadata_entry.path}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtifactRequirementInventory:
    """
    Immutable complete Universe inventory of canonical regular-file artifacts.

    The exact FilesystemMetadataInventory is retained by identity. Every
    regular file in that source inventory must appear exactly once.
    """

    source_inventory: FilesystemMetadataInventory

    requirements: tuple[
        AndroidUniverseArtifactRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "source_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if not isinstance(
            self.requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        source_inventory_entries = {
            id(entry): entry
            for entry
            in self.source_inventory.entries
        }

        seen: set[
            tuple[
                int,
                int,
            ]
        ] = set()

        previous_key: (
            tuple[
                str,
                str,
            ]
            | None
        ) = None

        for requirement in self.requirements:
            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise TypeError(
                    "requirements must contain only "
                    "AndroidUniverseArtifactRequirement objects"
                )

            if (
                id(requirement.inventory_entry)
                not in source_inventory_entries
            ):
                raise ValueError(
                    "artifact requirement must preserve an exact "
                    "filesystem inventory entry from source_inventory"
                )

            identity_key = (
                requirement.identity_key
            )

            if identity_key in seen:
                raise ValueError(
                    "duplicate artifact requirement: "
                    f"{requirement.key}"
                )

            key = requirement.key

            if (
                previous_key is not None
                and key < previous_key
            ):
                raise ValueError(
                    "artifact requirements must use "
                    "deterministic key ordering"
                )

            seen.add(
                identity_key
            )

            previous_key = key

        expected = {
            (
                id(
                    inventory_entry.artifact
                ),
                id(
                    metadata_entry
                ),
            )
            for inventory_entry
            in self.source_inventory.entries
            for metadata_entry
            in (
                inventory_entry
                .result
                .metadata
                .entries
                .values()
            )
            if (
                metadata_entry.entry_type
                is FilesystemEntryType.FILE
            )
        }

        if seen != expected:
            missing = (
                expected
                - seen
            )

            extra = (
                seen
                - expected
            )

            raise ValueError(
                "artifact requirement inventory must cover every "
                "canonical regular file exactly once; "
                f"missing={len(missing)}, extra={len(extra)}"
            )

    def __len__(
        self,
    ) -> int:
        return len(
            self.requirements
        )

    def __iter__(
        self,
    ):
        return iter(
            self.requirements
        )

    @property
    def unclassified(
        self,
    ) -> tuple[
        AndroidUniverseArtifactRequirement,
        ...,
    ]:
        return tuple(
            requirement
            for requirement
            in self.requirements
            if (
                requirement.disposition
                is AndroidUniverseArtifactDisposition.UNCLASSIFIED
            )
        )

    def for_partition(
        self,
        partition_name: str,
    ) -> tuple[
        AndroidUniverseArtifactRequirement,
        ...,
    ]:
        if not isinstance(
            partition_name,
            str,
        ):
            raise TypeError(
                "partition_name must be a string"
            )

        if not partition_name:
            raise ValueError(
                "partition_name cannot be empty"
            )

        return tuple(
            requirement
            for requirement
            in self.requirements
            if (
                requirement.partition_name
                == partition_name
            )
        )
