from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.kernel_artifact_provider import (
    AndroidDeviceTreeLocalKernelArtifactProvider,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


class AndroidDeviceTreeBootConstructionSource(
    StrEnum,
):
    """
    Explicit source selected for Device Tree boot-family construction.

    FACTORY_CANONICAL is the deterministic default.

    TreeForge Boot Image deployments may be selected explicitly, but they are
    construction inputs only. Their AVB/VBMeta trust result never crosses this
    boundary into Device Tree.
    """

    FACTORY_CANONICAL = "factory_canonical"

    TREEFORGE_BOOT_IMAGE_DEFAULT = (
        "treeforge_boot_image_default"
    )

    TREEFORGE_BOOT_IMAGE_MODIFIED = (
        "treeforge_boot_image_modified"
    )

    TREEFORGE_KERNEL_BASELINE = (
        "treeforge_kernel_baseline"
    )

    TREEFORGE_KERNEL_MODIFIED = (
        "treeforge_kernel_modified"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeBootConstructionImage:
    """
    One exact whole-image input selected for Android prebuilt construction.

    ``source_path`` is a host path whose byte identity has been checked before
    projection.

    ``destination`` is the generated Device Tree path consumed by Android's
    normal build system.

    Selection as a prebuilt construction input does not assert that TreeForge
    reconstructed Google's original source recipe.
    """

    partition_name: str
    requirement_id: str

    source: AndroidDeviceTreeBootConstructionSource

    source_path: Path
    destination: PurePosixPath

    size_bytes: int
    sha256: str

    selected_from_boot_image: bool

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "partition_name",
                self.partition_name,
            ),
            (
                "requirement_id",
                self.requirement_id,
            ),
            (
                "sha256",
                self.sha256,
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
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.source,
            AndroidDeviceTreeBootConstructionSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidDeviceTreeBootConstructionSource"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "destination must be Device Tree relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape the Device Tree workspace"
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
            len(self.sha256) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character
                in self.sha256
            )
        ):
            raise ValueError(
                "sha256 must be a lowercase SHA-256 digest"
            )

        if not isinstance(
            self.selected_from_boot_image,
            bool,
        ):
            raise TypeError(
                "selected_from_boot_image must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeBootConstructionPlan:
    """
    Device Tree-owned boot construction-input plan.

    The plan deliberately distinguishes:

    - selected whole-image construction inputs;
    - boot-family partitions that continue through Android-native construction;
    - Boot Image provenance;
    - excluded VBMeta outputs;
    - source-equivalence state.

    Device Tree never imports Boot Image VBMeta artifacts.
    """

    source: AndroidDeviceTreeBootConstructionSource

    images: tuple[
        AndroidDeviceTreeBootConstructionImage,
        ...,
    ]

    native_construction_partitions: tuple[
        str,
        ...,
    ]

    canonical_fallback_partitions: tuple[
        str,
        ...,
    ]

    boot_image_invoked: bool

    boot_image_manifest_path: Path | None

    excluded_boot_image_vbmeta_count: int = 0

    imported_vbmeta_count: int = 0

    source_equivalence_promotion_count: int = 0

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidDeviceTreeBootConstructionSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidDeviceTreeBootConstructionSource"
            )

        if not isinstance(
            self.images,
            tuple,
        ):
            raise TypeError(
                "images must be a tuple"
            )

        if not all(
            isinstance(
                image,
                AndroidDeviceTreeBootConstructionImage,
            )
            for image
            in self.images
        ):
            raise TypeError(
                "images contains an invalid construction image"
            )

        partition_names = tuple(
            image.partition_name
            for image
            in self.images
        )

        if len(
            partition_names
        ) != len(
            set(
                partition_names
            )
        ):
            raise ValueError(
                "boot construction image partitions must be unique"
            )

        destinations = tuple(
            image.destination.as_posix()
            for image
            in self.images
        )

        if len(
            destinations
        ) != len(
            set(
                destinations
            )
        ):
            raise ValueError(
                "boot construction image destinations must be unique"
            )

        for field_name, values in (
            (
                "native_construction_partitions",
                self.native_construction_partitions,
            ),
            (
                "canonical_fallback_partitions",
                self.canonical_fallback_partitions,
            ),
        ):
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
                    str,
                )
                and value
                for value
                in values
            ):
                raise ValueError(
                    f"{field_name} must contain non-empty strings"
                )

            if values != tuple(
                sorted(
                    set(
                        values
                    )
                )
            ):
                raise ValueError(
                    f"{field_name} must use unique deterministic ordering"
                )

        if not isinstance(
            self.boot_image_invoked,
            bool,
        ):
            raise TypeError(
                "boot_image_invoked must be a bool"
            )

        if (
            self.boot_image_manifest_path
            is not None
            and not isinstance(
                self.boot_image_manifest_path,
                Path,
            )
        ):
            raise TypeError(
                "boot_image_manifest_path must be a Path or None"
            )

        for field_name, value in (
            (
                "excluded_boot_image_vbmeta_count",
                self.excluded_boot_image_vbmeta_count,
            ),
            (
                "imported_vbmeta_count",
                self.imported_vbmeta_count,
            ),
            (
                "source_equivalence_promotion_count",
                self.source_equivalence_promotion_count,
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
                    f"{field_name} must be a non-negative int"
                )

        if self.imported_vbmeta_count != 0:
            raise ValueError(
                "Boot Image VBMeta artifacts must never be imported "
                "into Device Tree"
            )

        if (
            self.source_equivalence_promotion_count
            != 0
        ):
            raise ValueError(
                "construction-input selection must not promote "
                "boot component source equivalence"
            )

        if (
            self.source
            is AndroidDeviceTreeBootConstructionSource
            .FACTORY_CANONICAL
            and self.boot_image_invoked
        ):
            raise ValueError(
                "factory-canonical construction cannot report "
                "a Boot Image invocation"
            )

    def image_for_partition(
        self,
        partition_name: str,
    ) -> AndroidDeviceTreeBootConstructionImage | None:
        for image in self.images:
            if (
                image.partition_name
                == partition_name
            ):
                return image

        return None


class AndroidDeviceTreeBootConstructionProjector:
    """
    Project Android boot construction inputs from canonical Reconstruction and
    an optional explicitly selected TreeForge Boot Image deployment.

    Android 15 r36 establishes whole-image prebuilt ownership for boot.

    init_boot remains Android-native construction. TreeForge preserves its
    canonical Reconstruction evidence, while Android owns the final init_boot
    container and AVB footer. Modified Boot Image inputs that mutate init_boot
    continue to fail closed until TreeForge can carry those mutations
    losslessly into Android-native construction.

    vendor_boot deliberately remains Android-native construction here because
    Android's vendor_kernel_boot build gate requires BUILDING_VENDOR_BOOT_IMAGE
    to remain true.

    A future vendor_boot construction closure may consume exact prebuilt vendor
    ramdisk fragments without changing this selection model.
    """

    WHOLE_IMAGE_PREBUILT_PARTITIONS = (
        "boot",
    )

    NATIVE_CONSTRUCTION_PARTITIONS = (
        "init_boot",
        "pvmfw",
        "vendor_boot",
        "vendor_kernel_boot",
    )

    VBMETA_PARTITIONS = frozenset(
        {
            "vbmeta",
            "vbmeta_system",
            "vbmeta_vendor",
        }
    )

    @staticmethod
    def file_identity(
        source: Path,
    ) -> tuple[int, str]:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a Path"
            )

        if not source.is_file():
            raise FileNotFoundError(
                "boot construction source is unavailable: "
                f"{source}"
            )

        digest = sha256()
        size = 0

        with source.open(
            "rb",
        ) as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                size += len(
                    chunk
                )
                digest.update(
                    chunk
                )

        if size <= 0:
            raise ValueError(
                "boot construction source is empty: "
                f"{source}"
            )

        return (
            size,
            digest.hexdigest(),
        )

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
        source: AndroidDeviceTreeBootConstructionSource,
        boot_image_deployment=None,
        boot_image_invoked: bool = False,
    ) -> AndroidDeviceTreeBootConstructionPlan:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        if not isinstance(
            source,
            AndroidDeviceTreeBootConstructionSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidDeviceTreeBootConstructionSource"
            )

        if not isinstance(
            boot_image_invoked,
            bool,
        ):
            raise TypeError(
                "boot_image_invoked must be a bool"
            )

        boot_compositions = (
            reconstruction
            .boot_image_compositions
        )

        composition_by_partition = {}

        for composition in (
            boot_compositions
        ):
            partition_name = (
                composition
                .requirement
                .partition
                .name
            )

            if partition_name in (
                composition_by_partition
            ):
                raise ValueError(
                    "duplicate canonical boot composition partition: "
                    f"{partition_name}"
                )

            composition_by_partition[
                partition_name
            ] = composition

        deployment_images = ()

        manifest_path = None

        boot_image_sources = (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_DEFAULT,
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_BOOT_IMAGE_MODIFIED,
        )

        kernel_sources = (
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_BASELINE,
            AndroidDeviceTreeBootConstructionSource
            .TREEFORGE_KERNEL_MODIFIED,
        )

        kernel_artifact = None

        if source in boot_image_sources:
            if boot_image_deployment is None:
                raise ValueError(
                    "TreeForge Boot Image construction selection "
                    "requires an explicit validated deployment"
                )

            deployment_images = tuple(
                getattr(
                    boot_image_deployment,
                    "images",
                    (),
                )
            )

            if not deployment_images:
                raise ValueError(
                    "selected TreeForge Boot Image deployment "
                    "contains no images"
                )

            manifest_path = getattr(
                boot_image_deployment,
                "manifest_path",
                None,
            )

            if not isinstance(
                manifest_path,
                Path,
            ):
                raise ValueError(
                    "selected TreeForge Boot Image deployment "
                    "does not expose its manifest path"
                )

        if source in kernel_sources:
            if boot_image_deployment is not None:
                raise ValueError(
                    "TreeForge Kernel construction must not consume "
                    "a Boot Image deployment"
                )

            if boot_image_invoked:
                raise ValueError(
                    "TreeForge Kernel construction must not report "
                    "a Boot Image invocation"
                )

            kernel_source_mode = (
                "baseline"
                if source
                is AndroidDeviceTreeBootConstructionSource
                .TREEFORGE_KERNEL_BASELINE
                else "modified"
            )

            kernel_artifact = (
                AndroidDeviceTreeLocalKernelArtifactProvider
                .resolve(
                    device=identity.device,
                    source_mode=kernel_source_mode,
                )
            )

        deployment_boot_images = {}

        excluded_vbmeta_count = 0

        unsupported_modified_partitions = []

        for deployment_image in (
            deployment_images
        ):
            partition_name = getattr(
                deployment_image,
                "partition_name",
                None,
            )

            source_kind = getattr(
                deployment_image,
                "source_kind",
                None,
            )

            if (
                source_kind
                == "parent_vbmeta"
                or partition_name
                in cls.VBMETA_PARTITIONS
            ):
                excluded_vbmeta_count += 1
                continue

            if source_kind != "boot_image":
                continue

            if (
                not isinstance(
                    partition_name,
                    str,
                )
                or not partition_name
            ):
                raise ValueError(
                    "Boot Image deployment image lost partition identity"
                )

            if partition_name in deployment_boot_images:
                raise ValueError(
                    "Boot Image deployment contains duplicate "
                    "partition identity: "
                    f"{partition_name}"
                )

            deployment_boot_images[
                partition_name
            ] = deployment_image

            if (
                source
                is
                AndroidDeviceTreeBootConstructionSource
                .TREEFORGE_BOOT_IMAGE_MODIFIED
                and partition_name
                not in cls.WHOLE_IMAGE_PREBUILT_PARTITIONS
            ):
                final_sha256 = getattr(
                    deployment_image,
                    "final_sha256",
                    None,
                )

                rollback_sha256 = getattr(
                    deployment_image,
                    "rollback_sha256",
                    None,
                )

                if (
                    final_sha256 is not None
                    and rollback_sha256 is not None
                    and final_sha256
                    != rollback_sha256
                ):
                    unsupported_modified_partitions.append(
                        partition_name
                    )

        if unsupported_modified_partitions:
            raise ValueError(
                "selected modified Boot Image set changes boot-family "
                "partition(s) whose mutations cannot yet be carried "
                "losslessly into Android-native Device Tree construction: "
                f"{tuple(sorted(set(unsupported_modified_partitions)))!r}. "
                "No modified payload was silently discarded."
            )

        projected = []

        canonical_fallback_partitions = []

        for partition_name in (
            cls.WHOLE_IMAGE_PREBUILT_PARTITIONS
        ):
            composition = (
                composition_by_partition.get(
                    partition_name
                )
            )

            if composition is None:
                continue

            selected_path = (
                composition
                .image_artifact
                .path
                .resolve()
            )

            selected_from_boot_image = False

            expected_size = None
            expected_sha256 = None

            if source in kernel_sources:
                if kernel_artifact is None:
                    raise RuntimeError(
                        "TreeForge Kernel artifact resolution "
                        "did not produce an artifact"
                    )

                selected_path = (
                    kernel_artifact
                    .path
                    .resolve()
                )

                expected_size = (
                    kernel_artifact
                    .size_bytes
                )

                expected_sha256 = (
                    kernel_artifact
                    .sha256
                )

            elif (
                source
                is not
                AndroidDeviceTreeBootConstructionSource
                .FACTORY_CANONICAL
            ):
                deployment_image = (
                    deployment_boot_images.get(
                        partition_name
                    )
                )

                if deployment_image is not None:
                    selected_path = (
                        deployment_image
                        .final_path
                        .resolve()
                    )

                    expected_size = (
                        deployment_image
                        .final_size_bytes
                    )

                    expected_sha256 = (
                        deployment_image
                        .final_sha256
                    )

                    selected_from_boot_image = True

                else:
                    canonical_fallback_partitions.append(
                        partition_name
                    )

            actual_size, actual_sha256 = (
                cls.file_identity(
                    selected_path
                )
            )

            if (
                expected_size is not None
                and actual_size
                != expected_size
            ):
                raise ValueError(
                    "selected boot construction input "
                    "changed recorded size: "
                    f"{partition_name}"
                )

            if (
                expected_sha256 is not None
                and actual_sha256
                != expected_sha256
            ):
                raise ValueError(
                    "selected boot construction input "
                    "changed recorded SHA-256: "
                    f"{partition_name}"
                )

            projected.append(
                AndroidDeviceTreeBootConstructionImage(
                    partition_name=(
                        partition_name
                    ),
                    requirement_id=(
                        composition.requirement_id
                    ),
                    source=source,
                    source_path=(
                        selected_path
                    ),
                    destination=(
                        PurePosixPath(
                            identity.device_root.as_posix()
                        )
                        / "boot"
                        / "prebuilt"
                        / f"{partition_name}.img"
                    ),
                    size_bytes=(
                        actual_size
                    ),
                    sha256=(
                        actual_sha256
                    ),
                    selected_from_boot_image=(
                        selected_from_boot_image
                    ),
                )
            )

        native_construction_partitions = tuple(
            sorted(
                partition_name
                for partition_name
                in cls.NATIVE_CONSTRUCTION_PARTITIONS
                if partition_name
                in composition_by_partition
            )
        )

        return AndroidDeviceTreeBootConstructionPlan(
            source=source,
            images=tuple(
                sorted(
                    projected,
                    key=lambda item: (
                        item.partition_name
                    ),
                )
            ),
            native_construction_partitions=(
                native_construction_partitions
            ),
            canonical_fallback_partitions=tuple(
                sorted(
                    set(
                        canonical_fallback_partitions
                    )
                )
            ),
            boot_image_invoked=(
                boot_image_invoked
            ),
            boot_image_manifest_path=(
                manifest_path
            ),
            excluded_boot_image_vbmeta_count=(
                excluded_vbmeta_count
            ),
            imported_vbmeta_count=0,
            source_equivalence_promotion_count=0,
        )
