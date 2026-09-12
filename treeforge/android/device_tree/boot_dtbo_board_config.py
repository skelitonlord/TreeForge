from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.boot_construction import (
    AndroidDeviceTreeBootConstructionPlan,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeBootDtboBoardConfig:
    """
    Concrete generic Android Boot/DTBO BoardConfig projection.

    boot.img may use an exact whole-image prebuilt provider input.
    init_boot remains on Android's native construction path.

    Android's build system remains responsible for final init_boot
    construction and AVB footer/signature generation.

    When boot.img is supplied as a whole-image prebuilt, TARGET_NO_KERNEL is
    emitted with BOARD_PREBUILT_BOOTIMAGE.  This prevents Android's build
    system from fabricating an unowned $(PRODUCT_OUT)/kernel target and lets
    its canonical prebuilt-boot path extract kernel metadata from
    INSTALLED_BOOTIMAGE_TARGET when required.

    vendor_boot intentionally remains on Android-native construction because
    vendor_kernel_boot construction requires BUILDING_VENDOR_BOOT_IMAGE=true.
    """

    boot_header_version: int | None = None
    init_boot_header_version: int | None = None

    boot_partition_size: int | None = None
    init_boot_partition_size: int | None = None
    vendor_boot_partition_size: int | None = None

    prebuilt_boot_source_path: PurePosixPath | None = None

    dtbo_partition_size: int | None = None

    dtbo_source_artifact: Path | None = None
    dtbo_source_path: PurePosixPath | None = None

    def __post_init__(
        self,
    ) -> None:
        for name, value in (
            (
                "boot_header_version",
                self.boot_header_version,
            ),
            (
                "init_boot_header_version",
                self.init_boot_header_version,
            ),
            (
                "boot_partition_size",
                self.boot_partition_size,
            ),
            (
                "init_boot_partition_size",
                self.init_boot_partition_size,
            ),
            (
                "vendor_boot_partition_size",
                self.vendor_boot_partition_size,
            ),
            (
                "dtbo_partition_size",
                self.dtbo_partition_size,
            ),
        ):
            if value is None:
                continue

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an int or None"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        for name, value in (
            (
                "prebuilt_boot_source_path",
                self.prebuilt_boot_source_path,
            ),
        ):
            if value is None:
                continue

            if not isinstance(
                value,
                PurePosixPath,
            ):
                raise TypeError(
                    f"{name} must be a PurePosixPath or None"
                )

            if value.is_absolute():
                raise ValueError(
                    f"{name} must be Device Tree relative"
                )

            if ".." in value.parts:
                raise ValueError(
                    f"{name} must not escape the Device Tree workspace"
                )

        if (
            self.dtbo_source_artifact is None
        ) != (
            self.dtbo_source_path is None
        ):
            raise ValueError(
                "DTBO source artifact and Device Tree "
                "source path must be present together"
            )

        if (
            self.dtbo_source_artifact is not None
            and not isinstance(
                self.dtbo_source_artifact,
                Path,
            )
        ):
            raise TypeError(
                "dtbo_source_artifact must be a Path or None"
            )

        if (
            self.dtbo_source_path is not None
            and not isinstance(
                self.dtbo_source_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "dtbo_source_path must be a "
                "PurePosixPath or None"
            )

        if (
            self.dtbo_source_path is not None
            and self.dtbo_source_path.is_absolute()
        ):
            raise ValueError(
                "dtbo_source_path must be relative to "
                "the Device Tree workspace"
            )


class AndroidDeviceTreeBootDtboBoardConfigRenderer:
    """
    Project and render generic Boot/DTBO Android build integration.

    Whole-image prebuilt construction is selected only for boot.
    init_boot is constructed by Android from its normal generic ramdisk input
    and receives Android-owned AVB signing.

    vendor_boot remains natively built so vendor_kernel_boot can also remain
    on Android's supported construction path.
    """

    @staticmethod
    def _local_path(
        source_path: PurePosixPath,
    ) -> PurePosixPath:
        parts = source_path.parts

        if (
            len(parts) < 4
            or parts[0] != "device"
        ):
            raise ValueError(
                "boot construction source path must reside beneath "
                "a generated device/<vendor>/<device> tree"
            )

        local_path = PurePosixPath(
            *parts[3:]
        )

        if not local_path.parts:
            raise ValueError(
                "boot construction source path must identify "
                "a file beneath the generated device tree"
            )

        return local_path

    @staticmethod
    def project(
        *,
        reconstruction: AndroidReconstructionResult,
        identity: AndroidDeviceTreeIdentity,
        boot_construction_plan: AndroidDeviceTreeBootConstructionPlan,
    ) -> AndroidDeviceTreeBootDtboBoardConfig:
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
            boot_construction_plan,
            AndroidDeviceTreeBootConstructionPlan,
        ):
            raise TypeError(
                "boot_construction_plan must be an "
                "AndroidDeviceTreeBootConstructionPlan"
            )

        boot_compositions = (
            reconstruction
            .boot_image_compositions
        )

        composition_requirement_ids = tuple(
            composition.requirement_id
            for composition
            in boot_compositions
        )

        if len(
            composition_requirement_ids
        ) != len(
            set(
                composition_requirement_ids
            )
        ):
            raise ValueError(
                "Reconstruction boot-image compositions contain "
                "duplicate canonical requirement identities"
            )

        boot_requirements = tuple(
            composition.requirement
            for composition
            in boot_compositions
        )

        partition_layout = (
            reconstruction
            .reconstruction_input
            .partition_layout
        )

        board_config_boot_header_partitions = frozenset(
            {
                "boot",
                "vendor_boot",
            }
        )

        board_config_boot_requirements = tuple(
            requirement
            for requirement
            in boot_requirements
            if (
                requirement.partition.name
                in board_config_boot_header_partitions
            )
        )

        header_versions = {
            requirement.semantics.header_version
            for requirement
            in board_config_boot_requirements
        }

        boot_header_version = (
            next(iter(header_versions))
            if len(header_versions) == 1
            else None
        )

        init_boot_header_versions = {
            requirement.semantics.header_version
            for requirement
            in boot_requirements
            if (
                requirement.partition.name
                == "init_boot"
            )
        }

        if len(init_boot_header_versions) > 1:
            raise ValueError(
                "canonical init_boot requirements disagree on "
                "boot header version"
            )

        init_boot_header_version = (
            next(
                iter(
                    init_boot_header_versions
                )
            )
            if init_boot_header_versions
            else None
        )

        partition_sizes: dict[
            str,
            int | None,
        ] = {}

        for requirement in boot_requirements:
            partition_name = (
                requirement.partition.name
            )

            if (
                not isinstance(
                    partition_name,
                    str,
                )
                or not partition_name
            ):
                raise ValueError(
                    "canonical boot-family requirement has no "
                    "partition identity"
                )

            if partition_name in partition_sizes:
                raise ValueError(
                    "canonical boot-family population contains "
                    "duplicate partition identity: "
                    f"{partition_name}"
                )

            layout_partition = (
                partition_layout.partition(
                    partition_name
                )
                if partition_layout is not None
                else None
            )

            partition_sizes[
                partition_name
            ] = (
                layout_partition.size_bytes
                if layout_partition is not None
                else None
            )

        prebuilt_boot = (
            boot_construction_plan
            .image_for_partition(
                "boot"
            )
        )

        dtbo_source_artifact = None
        dtbo_source_path = None
        dtbo_partition_size = None

        dtbo_container = (
            reconstruction.dtbo_container
        )

        if dtbo_container is not None:
            artifact = dtbo_container.artifact

            if not artifact.path.is_file():
                raise ValueError(
                    "canonical Reconstruction DTBO container "
                    "does not reference an accessible file: "
                    f"{artifact.path}"
                )

            dtbo_source_artifact = (
                artifact.path
            )

            dtbo_source_path = (
                PurePosixPath(
                    identity.device_root.as_posix()
                )
                / "boot"
                / "dtbo.img"
            )

            layout_dtbo_partition = (
                partition_layout.partition(
                    "dtbo"
                )
                if partition_layout is not None
                else None
            )

            dtbo_partition_size = (
                layout_dtbo_partition.size_bytes
                if layout_dtbo_partition is not None
                else None
            )

        return AndroidDeviceTreeBootDtboBoardConfig(
            boot_header_version=(
                boot_header_version
            ),
            init_boot_header_version=(
                init_boot_header_version
            ),
            boot_partition_size=(
                partition_sizes.get(
                    "boot"
                )
            ),
            init_boot_partition_size=(
                partition_sizes.get(
                    "init_boot"
                )
            ),
            vendor_boot_partition_size=(
                partition_sizes.get(
                    "vendor_boot"
                )
            ),
            prebuilt_boot_source_path=(
                prebuilt_boot.destination
                if prebuilt_boot is not None
                else None
            ),
            dtbo_partition_size=(
                dtbo_partition_size
            ),
            dtbo_source_artifact=(
                dtbo_source_artifact
            ),
            dtbo_source_path=(
                dtbo_source_path
            ),
        )

    @classmethod
    def render(
        cls,
        config: AndroidDeviceTreeBootDtboBoardConfig,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreeBootDtboBoardConfig,
        ):
            raise TypeError(
                "config must be an "
                "AndroidDeviceTreeBootDtboBoardConfig"
            )

        lines: list[str] = []

        if config.boot_header_version is not None:
            lines.extend(
                [
                    (
                        "BOARD_BOOT_HEADER_VERSION := "
                        f"{config.boot_header_version}"
                    ),
                    (
                        "BOARD_MKBOOTIMG_ARGS += "
                        "--header_version "
                        f"{config.boot_header_version}"
                    ),
                ]
            )

        if (
            config.init_boot_header_version
            is not None
        ):
            lines.extend(
                [
                    (
                        "BOARD_INIT_BOOT_HEADER_VERSION := "
                        f"{config.init_boot_header_version}"
                    ),
                    (
                        "BOARD_MKBOOTIMG_INIT_ARGS += "
                        "--header_version "
                        f"{config.init_boot_header_version}"
                    ),
                ]
            )

        if config.boot_partition_size is not None:
            lines.append(
                "BOARD_BOOTIMAGE_PARTITION_SIZE := "
                f"{config.boot_partition_size}"
            )

        if (
            config.init_boot_partition_size
            is not None
        ):
            lines.append(
                "BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE := "
                f"{config.init_boot_partition_size}"
            )

        if (
            config.vendor_boot_partition_size
            is not None
        ):
            lines.append(
                "BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE := "
                f"{config.vendor_boot_partition_size}"
            )

        if (
            config.prebuilt_boot_source_path
            is not None
        ):
            lines.extend(
                [
                    "TARGET_NO_KERNEL := true",
                    (
                        "BOARD_PREBUILT_BOOTIMAGE := "
                        f"{config.prebuilt_boot_source_path.as_posix()}"
                    ),
                ]
            )

        if (
            config.dtbo_source_path is not None
        ):
            lines.append(
                "BOARD_PREBUILT_DTBOIMAGE := "
                f"{config.dtbo_source_path.as_posix()}"
            )

        if config.dtbo_partition_size is not None:
            lines.append(
                "BOARD_DTBOIMG_PARTITION_SIZE := "
                f"{config.dtbo_partition_size}"
            )

        if not lines:
            return ""

        return "\n".join(lines) + "\n"
