from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidReconstructionBuildRepresentationKind(
    StrEnum,
):
    """
    Canonical build-participation role reconstructed from Android evidence.

    These values describe what the Android build must account for. They do
    not prescribe Make/Soong syntax, a source-tree repository, filename, or
    physical Device Tree placement.
    """

    PRESERVED_ARTIFACT = "preserved_artifact"

    PREBUILT_MODULE = "prebuilt_module"
    COPY_FILE = "copy_file"
    SOURCE_CONFIG = "source_config"

    PACKAGE = "package"

    JAVA_LIBRARY = "java_library"

    NATIVE_LIBRARY = "native_library"
    EXECUTABLE = "executable"

    KERNEL_MODULE = "kernel_module"

    APEX = "apex"

    SELINUX_POLICY = "selinux_policy"
    SELINUX_RUNTIME_OUTPUT = "selinux_runtime_output"
    VINTF_DOCUMENT = "vintf_document"

    BOOT_ARTIFACT = "boot_artifact"
    DTBO_ARTIFACT = "dtbo_artifact"
    VBMETA_ARTIFACT = "vbmeta_artifact"


class AndroidReconstructionBuildRepresentationStatus(
    StrEnum,
):
    """
    Disposition of one canonical build representation.

    RESOLVED means the build-participation semantics represented by this
    object are established by canonical upstream evidence.

    PARTIAL means some build semantics are established while specific
    downstream build facts remain unresolved.

    UNRESOLVED means Reconstruction cannot yet establish a safe build
    representation without inventing policy or unsupported source structure.
    """

    RESOLVED = "resolved"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionBuildRepresentation:
    """
    One canonical syntax-neutral Android build-system representation.

    Build-System Reconstruction consumes existing Reconstruction output and
    records how one reconstructed source/content unit, exact preserved
    artifact, or exact existing source build module participates in an
    eventual Android build.

    It may preserve canonical installed partition/path facts because those
    describe the observed Android result.

    It deliberately does not choose:

    - device/vendor/hardware/kernel/proprietary source-tree repositories;
    - source-tree destination paths;
    - Android.bp versus Android.mk;
    - concrete Soong or Make module syntax;
    - BoardConfig/product variable syntax;
    - filesystem materialization.

    Exactly one upstream payload identity is required:
    ``source_content_id`` for reconstructed source content,
    ``preserved_artifact_id`` for preserved canonical artifacts,
    ``source_module_id`` for an exact existing source build module, or
    ``canonical_requirement_id`` when canonical upstream evidence proves
    build participation but Reconstruction cannot yet establish the concrete
    source/content/preservation mechanism.
    """

    representation_id: str
    kind: AndroidReconstructionBuildRepresentationKind
    status: AndroidReconstructionBuildRepresentationStatus

    source_identity: str

    source_content_id: str | None = None
    preserved_artifact_id: str | None = None
    source_module_id: str | None = None
    canonical_requirement_id: str | None = None

    installed_partition: str | None = None
    installed_android_path: str | None = None

    module_identity: str | None = None

    dependency_ids: tuple[str, ...] = ()

    reason: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("representation_id", self.representation_id),
            ("source_identity", self.source_identity),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.kind,
            AndroidReconstructionBuildRepresentationKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidReconstructionBuildRepresentationKind"
            )

        if not isinstance(
            self.status,
            AndroidReconstructionBuildRepresentationStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidReconstructionBuildRepresentationStatus"
            )

        payload_count = sum(
            value is not None
            for value in (
                self.source_content_id,
                self.preserved_artifact_id,
                self.source_module_id,
                self.canonical_requirement_id,
            )
        )

        if payload_count != 1:
            raise ValueError(
                "build representation requires exactly one "
                "source_content_id, preserved_artifact_id, "
                "source_module_id, or canonical_requirement_id"
            )

        for field_name, value in (
            ("source_content_id", self.source_content_id),
            (
                "preserved_artifact_id",
                self.preserved_artifact_id,
            ),
            (
                "canonical_requirement_id",
                self.canonical_requirement_id,
            ),
            (
                "source_module_id",
                self.source_module_id,
            ),
            (
                "installed_partition",
                self.installed_partition,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
            ),
            ("module_identity", self.module_identity),
            ("reason", self.reason),
        ):
            if (
                value is not None
                and (
                    not isinstance(value, str)
                    or not value
                )
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty "
                    "string or None"
                )

        if (
            self.installed_android_path is not None
            and not self.installed_android_path.startswith("/")
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if not isinstance(
            self.dependency_ids,
            tuple,
        ):
            raise TypeError(
                "dependency_ids must be a tuple"
            )

        if not all(
            isinstance(value, str) and value
            for value in self.dependency_ids
        ):
            raise ValueError(
                "dependency_ids must contain only "
                "non-empty strings"
            )

        if len(
            self.dependency_ids
        ) != len(
            set(self.dependency_ids)
        ):
            raise ValueError(
                "dependency_ids must be unique"
            )

        if self.dependency_ids != tuple(
            sorted(
                self.dependency_ids
            )
        ):
            raise ValueError(
                "dependency_ids must use deterministic ordering"
            )

        if (
            self.status
            is AndroidReconstructionBuildRepresentationStatus.UNRESOLVED
            and self.reason is None
        ):
            raise ValueError(
                "UNRESOLVED build representation requires a reason"
            )
