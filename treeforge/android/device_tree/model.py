from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeIdentity:
    """Canonical source-tree identity owned by Device Tree."""

    vendor: str

    # Canonical hardware/runtime device identity reconstructed from
    # factory evidence, for example "tangorpro".
    device: str

    # TreeForge-owned Android build target identity.  This must be
    # namespace-distinct from an upstream/reference tree that may target
    # the same physical device, for example "treeforge_tangorpro".
    build_device: str

    # Android product identity, for example "treeforge_tangorpro".
    product: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("vendor", self.vendor),
            ("device", self.device),
            ("build_device", self.build_device),
            ("product", self.product),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            normalized = value.strip()

            if not normalized:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

            if normalized != value:
                raise ValueError(
                    f"{field_name} must not contain "
                    "leading or trailing whitespace"
                )

            if "/" in value or "\\" in value:
                raise ValueError(
                    f"{field_name} must be one source-tree "
                    "path component"
                )

    @property
    def device_root(self) -> Path:
        """
        TreeForge-owned Android build source root.

        The final path component is the build-device identity rather than
        the canonical physical-device codename.  Android's board-config
        discovery keys directly on TARGET_DEVICE and requires that exactly
        one matching BoardConfig.mk exist across the checkout.
        """
        return (
            Path("device")
            / self.vendor
            / self.build_device
        )

    @property
    def proprietary_root(self) -> Path:
        """
        Exact/preserved implementation payloads owned by this generated
        Device Tree.

        TreeForge emits one self-contained Android source tree beneath
        device/<vendor>/<device>.  A second vendor/<vendor>/<device> source
        tree is intentionally not created.
        """
        return (
            self.device_root
            / "proprietary"
        )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeInput:
    """Canonical Reconstruction -> Device Tree handoff."""

    reconstruction: AndroidReconstructionResult
    identity: AndroidDeviceTreeIdentity

    boot_construction_plan: object | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            self.identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        if self.boot_construction_plan is not None:
            from treeforge.android.device_tree.boot_construction import (
                AndroidDeviceTreeBootConstructionPlan,
            )

            if not isinstance(
                self.boot_construction_plan,
                AndroidDeviceTreeBootConstructionPlan,
            ):
                raise TypeError(
                    "boot_construction_plan contains an invalid model"
                )

    @property
    def source_contents(self) -> tuple[object, ...]:
        reconstruction = self.reconstruction

        return (
            reconstruction.init_source_contents
            + reconstruction.fstab_source_contents
            + reconstruction.runtime_property_source_contents
            + reconstruction.ueventd_source_contents
            + reconstruction.vintf_source_contents
            + reconstruction.selinux_source_contents
        )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMaterializedFile:
    """One file physically written by Device Tree."""

    relative_path: Path
    content_id: str
    representation_id: str
    family: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.relative_path,
            Path,
        ):
            raise TypeError(
                "relative_path must be a Path"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in self.relative_path.parts:
            raise ValueError(
                "relative_path must not escape "
                "the Device Tree workspace"
            )

        for field_name, value in (
            ("content_id", self.content_id),
            (
                "representation_id",
                self.representation_id,
            ),
            ("family", self.family),
        ):
            if not isinstance(
                value,
                str,
            ) or not value:
                raise ValueError(
                    f"{field_name} must be a "
                    "non-empty string"
                )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMaterializedDerivedSelinuxSource:
    """One Device Tree-derived SELinux source physically written."""

    relative_path: Path

    derived_source_id: str
    source_requirement_id: str
    source_representation_id: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.relative_path,
            Path,
        ):
            raise TypeError(
                "relative_path must be a Path"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in self.relative_path.parts:
            raise ValueError(
                "relative_path must not escape "
                "the Device Tree workspace"
            )

        for field_name, value in (
            ("derived_source_id", self.derived_source_id),
            (
                "source_requirement_id",
                self.source_requirement_id,
            ),
            (
                "source_representation_id",
                self.source_representation_id,
            ),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMaterializedArtifact:
    """One exact preserved artifact physically copied by Device Tree."""

    relative_path: Path

    artifact_id: str
    representation_id: str

    installed_partition: str
    installed_android_path: str

    source_path: Path

    def __post_init__(self) -> None:
        if not isinstance(
            self.relative_path,
            Path,
        ):
            raise TypeError(
                "relative_path must be a Path"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in self.relative_path.parts:
            raise ValueError(
                "relative_path must not escape "
                "the Device Tree workspace"
            )

        for field_name, value in (
            (
                "artifact_id",
                self.artifact_id,
            ),
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "installed_partition",
                self.installed_partition,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
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
                    f"{field_name} must be a "
                    "non-empty string"
                )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMaterializedPhysicalPayload:
    """
    One exact requirement-backed DIRECT_PARTITION Artifact physically
    copied by Device Tree.
    """

    relative_path: Path

    requirement_id: str
    representation_id: str

    installed_partition: str
    installed_android_path: str

    source_path: Path

    def __post_init__(self) -> None:
        if not isinstance(
            self.relative_path,
            Path,
        ):
            raise TypeError(
                "relative_path must be a Path"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in self.relative_path.parts:
            raise ValueError(
                "relative_path must not escape "
                "the Device Tree workspace"
            )

        for field_name, value in (
            (
                "requirement_id",
                self.requirement_id,
            ),
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "installed_partition",
                self.installed_partition,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
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
                    f"{field_name} must be a "
                    "non-empty string"
                )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMaterializedApexPayload:
    """
    One exact root-runtime canonical APEX container physically copied
    by Device Tree.
    """

    relative_path: Path

    requirement_id: str
    representation_id: str

    installed_partition: str
    installed_android_path: str

    source_path: Path

    def __post_init__(self) -> None:
        if not isinstance(
            self.relative_path,
            Path,
        ):
            raise TypeError(
                "relative_path must be a Path"
            )

        if self.relative_path.is_absolute():
            raise ValueError(
                "relative_path must be relative"
            )

        if ".." in self.relative_path.parts:
            raise ValueError(
                "relative_path must not escape "
                "the Device Tree workspace"
            )

        for field_name, value in (
            ("requirement_id", self.requirement_id),
            ("representation_id", self.representation_id),
            ("installed_partition", self.installed_partition),
            ("installed_android_path", self.installed_android_path),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not self.installed_android_path.startswith("/"):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeResult:
    """Canonical Device Tree stage result."""

    device_tree_input: AndroidDeviceTreeInput

    projections: tuple[object, ...] = ()

    artifact_projections: tuple[
        object,
        ...,
    ] = ()

    physical_payload_projections: tuple[
        object,
        ...,
    ] = ()

    vendor_kernel_ramdisk_plan: object | None = None

    native_boot_build_plan: object | None = None
    avb_build_plan: object | None = None

    apex_payload_projections: tuple[
        object,
        ...,
    ] = ()




    product_copy_files: tuple[
        object,
        ...,
    ] = ()

    product_policy: object | None = None

    kernel_board_config: object | None = None

    vintf_build_config: object | None = None

    build_realizations: tuple[
        "AndroidDeviceTreeBuildRealization",
        ...,
    ] = ()

    derived_selinux_sources: tuple[
        "AndroidDeviceTreeDerivedSelinuxSource",
        ...,
    ] = ()

    materialized_derived_selinux_sources: tuple[
        AndroidDeviceTreeMaterializedDerivedSelinuxSource,
        ...,
    ] = ()

    materialized_files: tuple[
        AndroidDeviceTreeMaterializedFile,
        ...,
    ] = ()

    materialized_artifacts: tuple[
        AndroidDeviceTreeMaterializedArtifact,
        ...,
    ] = ()

    materialized_physical_payloads: tuple[
        AndroidDeviceTreeMaterializedPhysicalPayload,
        ...,
    ] = ()

    materialized_vendor_kernel_ramdisk_modules: tuple[
        object,
        ...,
    ] = ()

    materialized_apex_payloads: tuple[
        AndroidDeviceTreeMaterializedApexPayload,
        ...,
    ] = ()

    materialized_native_boot_inputs: tuple[
        Path,
        ...,
    ] = ()

    materialized_avb_inputs: tuple[
        Path,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.device_tree_input,
            AndroidDeviceTreeInput,
        ):
            raise TypeError(
                "device_tree_input must be an "
                "AndroidDeviceTreeInput"
            )

        if not isinstance(
            self.projections,
            tuple,
        ):
            raise TypeError(
                "projections must be a tuple"
            )

        if not isinstance(
            self.artifact_projections,
            tuple,
        ):
            raise TypeError(
                "artifact_projections must be a tuple"
            )

        if not isinstance(
            self.physical_payload_projections,
            tuple,
        ):
            raise TypeError(
                "physical_payload_projections must be a tuple"
            )

        if self.vendor_kernel_ramdisk_plan is not None:
            from treeforge.android.device_tree.vendor_kernel_ramdisk import (
                AndroidDeviceTreeVendorKernelRamdiskPlan,
            )

            if not isinstance(
                self.vendor_kernel_ramdisk_plan,
                AndroidDeviceTreeVendorKernelRamdiskPlan,
            ):
                raise TypeError(
                    "vendor_kernel_ramdisk_plan contains an invalid model"
                )

        from treeforge.android.device_tree.native_boot_build import (
            AndroidDeviceTreeNativeBootBuildPlan,
        )
        from treeforge.android.device_tree.avb_build_config import (
            AndroidDeviceTreeAvbBuildPlan,
        )

        if not isinstance(
            self.native_boot_build_plan,
            AndroidDeviceTreeNativeBootBuildPlan,
        ):
            raise TypeError(
                "native_boot_build_plan contains an invalid model"
            )

        if not isinstance(
            self.avb_build_plan,
            AndroidDeviceTreeAvbBuildPlan,
        ):
            raise TypeError(
                "avb_build_plan contains an invalid model"
            )

        if not isinstance(
            self.apex_payload_projections,
            tuple,
        ):
            raise TypeError(
                "apex_payload_projections must be a tuple"
            )










        if not isinstance(
            self.product_copy_files,
            tuple,
        ):
            raise TypeError(
                "product_copy_files must be a tuple"
            )

        from treeforge.android.device_tree.product_makefile import (
            AndroidDeviceTreeProductCopyFile,
        )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeProductCopyFile,
            )
            for item
            in self.product_copy_files
        ):
            raise TypeError(
                "product_copy_files contains an invalid model"
            )

        if self.product_policy is not None:
            from treeforge.android.device_tree.product_policy import (
                AndroidDeviceTreeProductPolicy,
            )

            if not isinstance(
                self.product_policy,
                AndroidDeviceTreeProductPolicy,
            ):
                raise TypeError(
                    "product_policy contains an invalid model"
                )

        if self.product_policy is None:
            raise ValueError(
                "Device Tree result requires a resolved "
                "product_policy"
            )

        if self.kernel_board_config is not None:
            from treeforge.android.device_tree.kernel_board_config import (
                AndroidDeviceTreeKernelBoardConfig,
            )

            if not isinstance(
                self.kernel_board_config,
                AndroidDeviceTreeKernelBoardConfig,
            ):
                raise TypeError(
                    "kernel_board_config contains an invalid model"
                )

        if self.vintf_build_config is not None:
            from treeforge.android.device_tree.vintf_build import (
                AndroidDeviceTreeVintfBuildConfig,
            )

            if not isinstance(
                self.vintf_build_config,
                AndroidDeviceTreeVintfBuildConfig,
            ):
                raise TypeError(
                    "vintf_build_config contains an invalid model"
                )

        if not isinstance(
            self.build_realizations,
            tuple,
        ):
            raise TypeError(
                "build_realizations must be a tuple"
            )

        from treeforge.android.device_tree.build_realization import (
            AndroidDeviceTreeBuildRealization,
        )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeBuildRealization,
            )
            for item
            in self.build_realizations
        ):
            raise TypeError(
                "build_realizations contains an invalid model"
            )

        realization_ids = tuple(
            item.realization_id
            for item
            in self.build_realizations
        )

        if len(
            realization_ids
        ) != len(
            set(
                realization_ids
            )
        ):
            raise ValueError(
                "Device Tree build realization identities "
                "must be globally unique"
            )

        realized_representation_ids = tuple(
            item.representation_id
            for item
            in self.build_realizations
        )

        if len(
            realized_representation_ids
        ) != len(
            set(
                realized_representation_ids
            )
        ):
            raise ValueError(
                "Device Tree build realizations must not "
                "duplicate Reconstruction representation coverage"
            )

        #
        # PRODUCT_COPY_FILES is now a policy-selected Device Tree output.
        #
        # It is intentionally not required to equal the complete set of
        # resolved COPY_FILE realizations:
        #
        # - minimum-runtime policy may omit preserved factory payloads;
        # - generated source projections such as reconstructed init/fstab/
        #   ueventd files may add install entries which are not COPY_FILE
        #   build realizations at all.
        #
        # The authoritative contract here is therefore the selected
        # product_copy_files collection itself.  Validate its internal
        # identity and destination integrity rather than comparing it with
        # the pre-policy Reconstruction universe.
        #
        product_copy_file_representation_ids = tuple(
            item.representation_id
            for item
            in self.product_copy_files
        )

        if len(
            product_copy_file_representation_ids
        ) != len(
            set(
                product_copy_file_representation_ids
            )
        ):
            raise ValueError(
                "Device Tree PRODUCT_COPY_FILES selection "
                "must contain each selected representation exactly once"
            )

        product_copy_file_destinations = tuple(
            item.destination
            for item
            in self.product_copy_files
        )

        if len(
            product_copy_file_destinations
        ) != len(
            set(
                product_copy_file_destinations
            )
        ):
            raise ValueError(
                "Device Tree PRODUCT_COPY_FILES selection "
                "must contain each install destination exactly once"
            )

        if not isinstance(
            self.derived_selinux_sources,
            tuple,
        ):
            raise TypeError(
                "derived_selinux_sources must be a tuple"
            )

        from treeforge.android.device_tree.selinux_derived_source import (
            AndroidDeviceTreeDerivedSelinuxSource,
        )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeDerivedSelinuxSource,
            )
            for item in self.derived_selinux_sources
        ):
            raise TypeError(
                "derived_selinux_sources contains an invalid model"
            )

        derived_source_ids = tuple(
            item.derived_source_id
            for item in self.derived_selinux_sources
        )

        if len(
            derived_source_ids
        ) != len(
            set(derived_source_ids)
        ):
            raise ValueError(
                "derived SELinux source identities must be unique"
            )

        derived_source_paths = tuple(
            item.destination.as_posix()
            for item in self.derived_selinux_sources
        )

        if len(
            derived_source_paths
        ) != len(
            set(derived_source_paths)
        ):
            raise ValueError(
                "derived SELinux source destinations must be unique"
            )

        if not isinstance(
            self.materialized_derived_selinux_sources,
            tuple,
        ):
            raise TypeError(
                "materialized_derived_selinux_sources must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeMaterializedDerivedSelinuxSource,
            )
            for item
            in self.materialized_derived_selinux_sources
        ):
            raise TypeError(
                "materialized_derived_selinux_sources contains "
                "an invalid model"
            )

        materialized_derived_ids = tuple(
            item.derived_source_id
            for item
            in self.materialized_derived_selinux_sources
        )

        if len(
            materialized_derived_ids
        ) != len(
            set(materialized_derived_ids)
        ):
            raise ValueError(
                "materialized derived SELinux source identities "
                "must be unique"
            )

        if set(
            materialized_derived_ids
        ) != set(
            derived_source_ids
        ):
            missing = sorted(
                set(derived_source_ids)
                - set(materialized_derived_ids)
            )
            unexpected = sorted(
                set(materialized_derived_ids)
                - set(derived_source_ids)
            )

            raise ValueError(
                "materialized derived SELinux sources must cover "
                "the derived source population exactly: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        derived_by_id = {
            item.derived_source_id: item
            for item in self.derived_selinux_sources
        }

        for item in self.materialized_derived_selinux_sources:
            source = derived_by_id[item.derived_source_id]

            if (
                item.relative_path.as_posix()
                != source.destination.as_posix()
            ):
                raise ValueError(
                    "materialized derived SELinux source path "
                    "does not match its canonical Device Tree "
                    "destination"
                )

            if (
                item.source_requirement_id
                != source.source_requirement_id
                or item.source_representation_id
                != source.source_representation_id
            ):
                raise ValueError(
                    "materialized derived SELinux source changed "
                    "its canonical provenance identity"
                )

        if not isinstance(
            self.materialized_files,
            tuple,
        ):
            raise TypeError(
                "materialized_files must be a tuple"
            )

        if not isinstance(
            self.materialized_artifacts,
            tuple,
        ):
            raise TypeError(
                "materialized_artifacts must be a tuple"
            )

        if not isinstance(
            self.materialized_physical_payloads,
            tuple,
        ):
            raise TypeError(
                "materialized_physical_payloads must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeMaterializedFile,
            )
            for item in self.materialized_files
        ):
            raise TypeError(
                "materialized_files contains "
                "an invalid model"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeMaterializedArtifact,
            )
            for item in self.materialized_artifacts
        ):
            raise TypeError(
                "materialized_artifacts contains "
                "an invalid model"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeMaterializedPhysicalPayload,
            )
            for item in self.materialized_physical_payloads
        ):
            raise TypeError(
                "materialized_physical_payloads contains "
                "an invalid model"
            )

        if not isinstance(
            self.materialized_vendor_kernel_ramdisk_modules,
            tuple,
        ):
            raise TypeError(
                "materialized_vendor_kernel_ramdisk_modules "
                "must be a tuple"
            )

        from treeforge.android.device_tree.vendor_kernel_ramdisk import (
            AndroidDeviceTreeMaterializedVendorKernelRamdiskModule,
        )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeMaterializedVendorKernelRamdiskModule,
            )
            for item
            in self.materialized_vendor_kernel_ramdisk_modules
        ):
            raise TypeError(
                "materialized_vendor_kernel_ramdisk_modules "
                "contains an invalid model"
            )

        if not isinstance(
            self.materialized_apex_payloads,
            tuple,
        ):
            raise TypeError(
                "materialized_apex_payloads must be a tuple"
            )

        for field_name, values in (
            (
                "materialized_native_boot_inputs",
                self.materialized_native_boot_inputs,
            ),
            (
                "materialized_avb_inputs",
                self.materialized_avb_inputs,
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
                    item,
                    Path,
                )
                and not item.is_absolute()
                and ".." not in item.parts
                for item in values
            ):
                raise ValueError(
                    f"{field_name} must contain only safe "
                    "relative Paths"
                )

            if len(values) != len(
                set(values)
            ):
                raise ValueError(
                    f"{field_name} must contain unique paths"
                )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeMaterializedApexPayload,
            )
            for item in self.materialized_apex_payloads
        ):
            raise TypeError(
                "materialized_apex_payloads contains "
                "an invalid model"
            )

        paths = tuple(
            item.relative_path.as_posix()
            for item in self.materialized_files
        )

        artifact_paths = tuple(
            item.relative_path.as_posix()
            for item in self.materialized_artifacts
        )

        physical_payload_paths = tuple(
            item.relative_path.as_posix()
            for item
            in self.materialized_physical_payloads
        )

        vendor_kernel_ramdisk_paths = tuple(
            item.relative_path.as_posix()
            for item
            in self.materialized_vendor_kernel_ramdisk_modules
        )

        apex_payload_paths = tuple(
            item.relative_path.as_posix()
            for item
            in self.materialized_apex_payloads
        )

        derived_selinux_paths = tuple(
            item.relative_path.as_posix()
            for item
            in self.materialized_derived_selinux_sources
        )

        native_boot_paths = tuple(
            item.as_posix()
            for item
            in self.materialized_native_boot_inputs
        )

        avb_input_paths = tuple(
            item.as_posix()
            for item
            in self.materialized_avb_inputs
        )

        all_paths = (
            paths
            + artifact_paths
            + physical_payload_paths
            + vendor_kernel_ramdisk_paths
            + apex_payload_paths
            + derived_selinux_paths
            + native_boot_paths
            + avb_input_paths
        )

        if len(all_paths) != len(
            set(all_paths)
        ):
            raise ValueError(
                "materialized Device Tree paths "
                "must be globally unique"
            )

    @property
    def reconstruction(
        self,
    ) -> AndroidReconstructionResult:
        return self.device_tree_input.reconstruction

    @property
    def identity(
        self,
    ) -> AndroidDeviceTreeIdentity:
        return self.device_tree_input.identity

    @property
    def boot_construction_plan(
        self,
    ):
        return (
            self.device_tree_input
            .boot_construction_plan
        )

    @property
    def materialized_boot_construction_image_count(
        self,
    ) -> int:
        plan = self.boot_construction_plan

        if plan is None:
            return 0

        return len(
            plan.images
        )

    @property
    def source_content_count(self) -> int:
        return len(
            self.device_tree_input.source_contents
        )

    @property
    def build_representation_count(self) -> int:
        return len(
            self.reconstruction
            .artifact_build_representations
        )

    @property
    def composition_relationship_count(self) -> int:
        return len(
            self.reconstruction
            .composition_relationships
        )

    @property
    def build_realization_count(self) -> int:
        return len(
            self.build_realizations
        )

    @property
    def projected_file_count(self) -> int:
        return len(self.projections)

    @property
    def materialized_file_count(self) -> int:
        return len(self.materialized_files)

    @property
    def projected_artifact_count(self) -> int:
        return len(
            self.artifact_projections
        )

    @property
    def materialized_artifact_count(self) -> int:
        return len(
            self.materialized_artifacts
        )

    @property
    def projected_physical_payload_count(
        self,
    ) -> int:
        return len(
            self.physical_payload_projections
        )

    @property
    def materialized_physical_payload_count(
        self,
    ) -> int:
        return len(
            self.materialized_physical_payloads
        )

    @property
    def projected_vendor_kernel_ramdisk_module_count(
        self,
    ) -> int:
        if self.vendor_kernel_ramdisk_plan is None:
            return 0

        return len(
            self.vendor_kernel_ramdisk_plan.module_projections
        )

    @property
    def materialized_vendor_kernel_ramdisk_module_count(
        self,
    ) -> int:
        return len(
            self.materialized_vendor_kernel_ramdisk_modules
        )

    @property
    def projected_apex_payload_count(
        self,
    ) -> int:
        return len(
            self.apex_payload_projections
        )

    @property
    def materialized_apex_payload_count(
        self,
    ) -> int:
        return len(
            self.materialized_apex_payloads
        )

    @property
    def projected_product_copy_file_count(
        self,
    ) -> int:
        return len(
            self.product_copy_files
        )

    @property
    def projected_kernel_module_count(self) -> int:
        if self.kernel_board_config is None:
            return 0

        return (
            len(
                self.kernel_board_config.system_modules
            )
            + len(
                self.kernel_board_config.vendor_modules
            )
        )

    @property
    def total_materialized_count(self) -> int:
        return (
            self.materialized_file_count
            + self.materialized_artifact_count
            + self.materialized_physical_payload_count
            + self.materialized_vendor_kernel_ramdisk_module_count
            + self.materialized_apex_payload_count
            + self.materialized_boot_construction_image_count
            + len(
                self.materialized_native_boot_inputs
            )
            + len(
                self.materialized_avb_inputs
            )
        )
