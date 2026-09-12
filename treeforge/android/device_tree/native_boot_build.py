from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


from treeforge.android.format.compression import (
    CompressionFormat,
    detect_compression,
)

@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeNativeBootBytesInput:
    """
    Exact bytes TreeForge places for an Android-native image builder.

    TreeForge does not build the image represented by these bytes.
    """

    destination: PurePosixPath
    payload: bytes
    role: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "destination must be source-tree relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape the source tree"
            )

        if not isinstance(
            self.payload,
            bytes,
        ):
            raise TypeError(
                "payload must be bytes"
            )

        if not self.payload:
            raise ValueError(
                "payload must not be empty"
            )

        if (
            not isinstance(
                self.role,
                str,
            )
            or not self.role
        ):
            raise ValueError(
                "role must be a non-empty string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeNativeBootFileInput:
    """
    Exact existing canonical file copied into a generated Device Tree.

    The Android build consumes the resulting path through its standard build
    mechanisms.
    """

    source_path: Path
    destination: PurePosixPath
    role: str

    def __post_init__(
        self,
    ) -> None:
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
                "destination must be source-tree relative"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape the source tree"
            )

        if (
            not isinstance(
                self.role,
                str,
            )
            or not self.role
        ):
            raise ValueError(
                "role must be a non-empty string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeVendorRamdiskFragment:
    """
    One canonical vendor_boot v4 vendor-ramdisk fragment.

    TreeForge only slices the exact Extraction-established ramdisk section
    according to the already-parsed canonical vendor-ramdisk table.

    Android's own vendor_boot builder regenerates the table and container.
    """

    name: str

    destination: PurePosixPath
    payload: bytes

    ramdisk_type: int
    ramdisk_name: str
    board_id: tuple[int, ...]

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
                "name must be a non-empty string"
            )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if not isinstance(
            self.payload,
            bytes,
        ):
            raise TypeError(
                "payload must be bytes"
            )

        if not self.payload:
            raise ValueError(
                "vendor ramdisk fragment must not be empty"
            )

        if (
            isinstance(
                self.ramdisk_type,
                bool,
            )
            or not isinstance(
                self.ramdisk_type,
                int,
            )
            or self.ramdisk_type < 0
        ):
            raise ValueError(
                "ramdisk_type must be a non-negative int"
            )

        if not isinstance(
            self.ramdisk_name,
            str,
        ):
            raise TypeError(
                "ramdisk_name must be a string"
            )

        if (
            not isinstance(
                self.board_id,
                tuple,
            )
            or len(self.board_id) != 16
        ):
            raise ValueError(
                "board_id must contain exactly 16 words"
            )

        if not all(
            isinstance(
                value,
                int,
            )
            and not isinstance(
                value,
                bool,
            )
            and 0 <= value <= 0xFFFFFFFF
            for value in self.board_id
        ):
            raise ValueError(
                "board_id entries must be uint32 values"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeNativeBootBuildPlan:
    """
    Minimal TreeForge -> Android-native boot construction handoff.

    Android owns:
    - vendor_boot mkbootimg execution;
    - vendor_ramdisk_table generation;
    - vendor_kernel_boot mkbootimg execution;
    - kernel module ramdisk packaging;
    - AVB footer generation.

    TreeForge only places canonical source inputs and emits standard Android
    build variables.
    """

    device_root: PurePosixPath

    vendor_boot_requirement_id: str
    vendor_kernel_boot_requirement_id: str
    pvmfw_requirement_id: str

    vendor_ramdisk_fragments: tuple[
        AndroidDeviceTreeVendorRamdiskFragment,
        ...,
    ]

    file_inputs: tuple[
        AndroidDeviceTreeNativeBootFileInput,
        ...,
    ]

    # Canonical vendor_boot bootconfig semantics.
    #
    # The exact reconstructed bootconfig file remains in file_inputs for
    # provenance/materialization. These parameters are the Android build
    # handoff, avoiding BOARD_BOOTCONFIG_FILE path rebasing in Soong fsgen.
    bootconfig_parameters: tuple[str, ...]

    # Canonical vendor_boot command-line arguments that Android must place
    # into the rebuilt vendor_boot header. The source's standalone
    # ``bootconfig`` flag is intentionally omitted because Android appends it
    # automatically whenever BOARD_BOOTCONFIG is non-empty.
    kernel_cmdline_parameters: tuple[str, ...]

    # Android's standard ramdisk compressor must preserve the canonical
    # vendor_kernel_boot compression contract.
    ramdisk_use_lz4: bool

    pvmfw_source_path: Path
    pvmfw_destination: PurePosixPath

    pvmfw_partition_size: int
    vendor_kernel_boot_partition_size: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.device_root,
            PurePosixPath,
        ):
            raise TypeError(
                "device_root must be a PurePosixPath"
            )

        for field_name, value in (
            (
                "vendor_boot_requirement_id",
                self.vendor_boot_requirement_id,
            ),
            (
                "vendor_kernel_boot_requirement_id",
                self.vendor_kernel_boot_requirement_id,
            ),
            (
                "pvmfw_requirement_id",
                self.pvmfw_requirement_id,
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
                    f"{field_name} must be non-empty"
                )

        if not isinstance(
            self.vendor_ramdisk_fragments,
            tuple,
        ):
            raise TypeError(
                "vendor_ramdisk_fragments must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeVendorRamdiskFragment,
            )
            for item in self.vendor_ramdisk_fragments
        ):
            raise TypeError(
                "vendor_ramdisk_fragments contains an invalid model"
            )

        if not isinstance(
            self.file_inputs,
            tuple,
        ):
            raise TypeError(
                "file_inputs must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeNativeBootFileInput,
            )
            for item in self.file_inputs
        ):
            raise TypeError(
                "file_inputs contains an invalid model"
            )

        if not isinstance(
            self.pvmfw_source_path,
            Path,
        ):
            raise TypeError(
                "pvmfw_source_path must be a Path"
            )

        if not isinstance(
            self.pvmfw_destination,
            PurePosixPath,
        ):
            raise TypeError(
                "pvmfw_destination must be a PurePosixPath"
            )

        if (
            isinstance(
                self.pvmfw_partition_size,
                bool,
            )
            or not isinstance(
                self.pvmfw_partition_size,
                int,
            )
            or self.pvmfw_partition_size <= 0
        ):
            raise ValueError(
                "pvmfw_partition_size must be a positive int"
            )

        if not isinstance(
            self.kernel_cmdline_parameters,
            tuple,
        ):
            raise TypeError(
                "kernel_cmdline_parameters must be a tuple"
            )

        if not all(
            isinstance(parameter, str)
            and parameter
            and "\n" not in parameter
            and "\r" not in parameter
            for parameter
            in self.kernel_cmdline_parameters
        ):
            raise ValueError(
                "kernel_cmdline_parameters must contain only "
                "non-empty single-line strings"
            )

        if not isinstance(
            self.ramdisk_use_lz4,
            bool,
        ):
            raise TypeError(
                "ramdisk_use_lz4 must be a bool"
            )

        if (
            isinstance(
                self.vendor_kernel_boot_partition_size,
                bool,
            )
            or not isinstance(
                self.vendor_kernel_boot_partition_size,
                int,
            )
            or self.vendor_kernel_boot_partition_size <= 0
        ):
            raise ValueError(
                "vendor_kernel_boot_partition_size "
                "must be a positive int"
            )

        destinations = tuple(
            fragment.destination.as_posix()
            for fragment
            in self.vendor_ramdisk_fragments
        ) + tuple(
            item.destination.as_posix()
            for item
            in self.file_inputs
        ) + (
            self.pvmfw_destination.as_posix(),
        )

        if len(
            destinations
        ) != len(
            set(
                destinations
            )
        ):
            raise ValueError(
                "native boot input destinations must be unique"
            )

    @property
    def board_config_path(
        self,
    ) -> PurePosixPath:
        return (
            self.device_root
            / "boot"
            / "native"
            / "BoardConfig.mk"
        )

    @property
    def android_board_path(
        self,
    ) -> PurePosixPath:
        return (
            self.device_root
            / "AndroidBoard.mk"
        )

    @property
    def resolved_partitions(
        self,
    ) -> tuple[str, ...]:
        return (
            "pvmfw",
            "vendor_boot",
            "vendor_kernel_boot",
        )

    @property
    def materialized_input_count(
        self,
    ) -> int:
        return (
            len(
                self.vendor_ramdisk_fragments
            )
            + len(
                self.file_inputs
            )
            + 1
        )

    def resolves_partition(
        self,
        partition_name: str,
    ) -> bool:
        return (
            partition_name
            in self.resolved_partitions
        )

    def source_path_for_partition(
        self,
        partition_name: str,
    ) -> PurePosixPath | None:
        if partition_name in {
            "vendor_boot",
            "vendor_kernel_boot",
        }:
            return self.board_config_path

        if partition_name == "pvmfw":
            return self.android_board_path

        return None

    def file_input_for_role(
        self,
        role: str,
    ) -> AndroidDeviceTreeNativeBootFileInput | None:
        matches = tuple(
            item
            for item in self.file_inputs
            if item.role == role
        )

        if len(matches) > 1:
            raise ValueError(
                "native boot plan contains duplicate role: "
                f"{role}"
            )

        return (
            matches[0]
            if matches
            else None
        )


class AndroidDeviceTreeNativeBootBuildProjector:
    """
    Project exact canonical files onto Android's existing boot builders.

    No AOSP checkout is inspected here.
    """

    @staticmethod
    def _composition_by_partition(
        reconstruction: AndroidReconstructionResult,
    ):
        result = {}

        for composition in (
            reconstruction.boot_image_compositions
        ):
            partition_name = (
                composition
                .requirement
                .partition
                .name
            )

            if partition_name in result:
                raise ValueError(
                    "duplicate boot composition partition: "
                    f"{partition_name}"
                )

            result[
                partition_name
            ] = composition

        return result

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
        vendor_kernel_ramdisk_plan,
    ) -> AndroidDeviceTreeNativeBootBuildPlan:
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
                "identity must be an AndroidDeviceTreeIdentity"
            )

        from treeforge.android.device_tree.vendor_kernel_ramdisk import (
            AndroidDeviceTreeVendorKernelRamdiskPlan,
        )

        if not isinstance(
            vendor_kernel_ramdisk_plan,
            AndroidDeviceTreeVendorKernelRamdiskPlan,
        ):
            raise TypeError(
                "vendor_kernel_ramdisk_plan must be an "
                "AndroidDeviceTreeVendorKernelRamdiskPlan"
            )

        if not (
            vendor_kernel_ramdisk_plan
            .module_projections
        ):
            raise ValueError(
                "native vendor_kernel_boot construction requires "
                "the canonical vendor-kernel-ramdisk module population"
            )

        compositions = (
            cls._composition_by_partition(
                reconstruction
            )
        )

        required = {
            "vendor_boot",
            "vendor_kernel_boot",
            "pvmfw",
        }

        missing = (
            required
            - set(
                compositions
            )
        )

        if missing:
            raise ValueError(
                "native boot construction is missing canonical "
                "composition(s): "
                f"{sorted(missing)!r}"
            )

        vendor_boot = (
            compositions[
                "vendor_boot"
            ]
        )

        vendor_kernel_boot = (
            compositions[
                "vendor_kernel_boot"
            ]
        )

        pvmfw = (
            compositions[
                "pvmfw"
            ]
        )

        vendor_ramdisk = (
            vendor_boot
            .requirement
            .component_artifact(
                "ramdisk"
            )
        )

        bootconfig = (
            vendor_boot
            .requirement
            .component_artifact(
                "bootconfig"
            )
        )

        vendor_kernel_ramdisk = (
            vendor_kernel_boot
            .requirement
            .component_artifact(
                "ramdisk"
            )
        )

        vendor_kernel_dtb = (
            vendor_kernel_boot
            .requirement
            .component_artifact(
                "dtb"
            )
        )

        for name, artifact in (
            (
                "vendor_boot ramdisk",
                vendor_ramdisk,
            ),
            (
                "vendor_boot bootconfig",
                bootconfig,
            ),
            (
                "vendor_kernel_boot ramdisk",
                vendor_kernel_ramdisk,
            ),
            (
                "vendor_kernel_boot dtb",
                vendor_kernel_dtb,
            ),
        ):
            if artifact is None:
                raise ValueError(
                    f"canonical {name} component is unavailable"
                )

            if not artifact.path.is_file():
                raise ValueError(
                    f"canonical {name} payload is not materialized: "
                    f"{artifact.path}"
                )

        bootconfig_parameters = tuple(
            parameter
            for parameter in (
                line.strip()
                for line in (
                    bootconfig
                    .path
                    .read_text(
                        encoding="utf-8"
                    )
                    .splitlines()
                )
            )
            if (
                parameter
                and not parameter.startswith("#")
            )
        )

        if not bootconfig_parameters:
            raise ValueError(
                "canonical vendor_boot bootconfig contains no "
                "semantic parameters"
            )

        whitespace_parameters = tuple(
            parameter
            for parameter in bootconfig_parameters
            if any(
                character.isspace()
                for character in parameter
            )
        )

        if whitespace_parameters:
            raise ValueError(
                "canonical vendor_boot bootconfig contains "
                "whitespace-bearing parameters that Android "
                "BOARD_BOOTCONFIG cannot preserve exactly; "
                "BOARD_BOOTCONFIG_FILE is intentionally not used "
                "because Android 15 Soong fsgen rebases that path: "
                f"{whitespace_parameters!r}"
            )

        make_unsafe_parameters = tuple(
            parameter
            for parameter in bootconfig_parameters
            if any(
                character in parameter
                for character in (
                    "$",
                    "#",
                    "\\",
                )
            )
        )

        if make_unsafe_parameters:
            raise ValueError(
                "canonical vendor_boot bootconfig contains "
                "Make-unsafe parameters that cannot be emitted "
                "losslessly through BOARD_BOOTCONFIG: "
                f"{make_unsafe_parameters!r}"
            )

        command_line = (
            vendor_boot
            .requirement
            .semantics
            .command_line
        )

        bootconfig_flag_indexes = tuple(
            argument.index
            for argument
            in command_line.arguments
            if (
                argument.key == "bootconfig"
                and argument.value is None
            )
        )

        if len(bootconfig_flag_indexes) != 1:
            raise ValueError(
                "Android-native vendor_boot cmdline projection requires "
                "exactly one canonical standalone bootconfig flag because "
                "Android appends exactly one flag when BOARD_BOOTCONFIG is "
                "non-empty; "
                f"found {len(bootconfig_flag_indexes)}"
            )

        bootconfig_flag_index = (
            bootconfig_flag_indexes[0]
        )

        kernel_cmdline_parameters = tuple(
            argument.raw
            for argument
            in command_line.arguments
            if argument.index != bootconfig_flag_index
        )

        ramdisk_compression = detect_compression(
            vendor_kernel_ramdisk
            .path
            .read_bytes()
        )

        if (
            ramdisk_compression
            is CompressionFormat.LZ4_LEGACY
        ):
            ramdisk_use_lz4 = True

        elif (
            ramdisk_compression
            is CompressionFormat.GZIP
        ):
            ramdisk_use_lz4 = False

        else:
            raise ValueError(
                "canonical vendor_kernel_boot ramdisk compression cannot "
                "be represented exactly by Android's standard "
                "BOARD_RAMDISK_USE_LZ4 switch: "
                f"{ramdisk_compression.value}"
            )

        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        boot_population = (
            universe.boot_population
        )

        if boot_population is None:
            raise ValueError(
                "native vendor_boot projection requires "
                "canonical boot_population"
            )

        table_associations = tuple(
            association
            for association
            in (
                boot_population
                .vendor_ramdisk_table_associations
            )
            if (
                association.boot_requirement
                is vendor_boot.requirement
            )
        )

        if len(
            table_associations
        ) != 1:
            raise ValueError(
                "vendor_boot must have exactly one canonical "
                "vendor-ramdisk-table association"
            )

        table = (
            table_associations[0]
            .source
        )

        ramdisk_bytes = (
            vendor_ramdisk
            .path
            .read_bytes()
        )

        fragments = []
        cursor = 0

        primary_vendor_ramdisk_entry_count = 0

        for entry in (
            table.entries
        ):
            if entry.ramdisk_offset != cursor:
                raise ValueError(
                    "canonical vendor ramdisk fragments are not "
                    "contiguous in table order: "
                    f"entry={entry.index}, "
                    f"expected_offset={cursor}, "
                    f"actual_offset={entry.ramdisk_offset}"
                )

            end = (
                entry.ramdisk_offset
                + entry.ramdisk_size
            )

            if end > len(
                ramdisk_bytes
            ):
                raise ValueError(
                    "canonical vendor ramdisk table exceeds "
                    "the exact ramdisk component"
                )

            payload = ramdisk_bytes[
                entry.ramdisk_offset:end
            ]

            if len(payload) != entry.ramdisk_size:
                raise ValueError(
                    "vendor ramdisk fragment byte conservation failed"
                )

            is_android_primary_vendor_ramdisk = (
                entry.ramdisk_type == 1
                and not entry.ramdisk_name
                and not any(
                    entry.board_id
                )
            )

            if is_android_primary_vendor_ramdisk:
                primary_vendor_ramdisk_entry_count += 1

                if (
                    primary_vendor_ramdisk_entry_count
                    > 1
                ):
                    raise ValueError(
                        "vendor_boot contains multiple canonical "
                        "Android primary vendor ramdisk entries"
                    )

                #
                # The exact factory bytes remain proven canonical evidence,
                # but they are not an Android build input here. Android
                # reconstructs this primary ramdisk from TARGET_VENDOR_RAMDISK_OUT
                # plus the recovery staging owned by the selected boot
                # architecture.
                #
                cursor = end
                continue

            fragment_name = (
                "treeforge_vendor_ramdisk_"
                f"{entry.index:02d}"
            )

            fragments.append(
                AndroidDeviceTreeVendorRamdiskFragment(
                    name=fragment_name,
                    destination=(
                        PurePosixPath(
                            identity
                            .device_root
                            .as_posix()
                        )
                        / "boot"
                        / "native"
                        / "vendor_ramdisk"
                        / (
                            f"{entry.index:02d}-"
                            f"{fragment_name}.img"
                        )
                    ),
                    payload=payload,
                    ramdisk_type=(
                        entry.ramdisk_type
                    ),
                    ramdisk_name=(
                        entry.ramdisk_name
                    ),
                    board_id=(
                        entry.board_id
                    ),
                )
            )

            cursor = end

        if cursor != len(
            ramdisk_bytes
        ):
            raise ValueError(
                "canonical vendor ramdisk table does not "
                "conserve the complete ramdisk component: "
                f"covered={cursor}, "
                f"component={len(ramdisk_bytes)}"
            )

        file_inputs = (
            AndroidDeviceTreeNativeBootFileInput(
                source_path=(
                    bootconfig.path
                ),
                destination=(
                    PurePosixPath(
                        identity
                        .device_root
                        .as_posix()
                    )
                    / "boot"
                    / "native"
                    / "vendor_boot"
                    / "bootconfig"
                ),
                role="vendor_boot_bootconfig",
            ),
            AndroidDeviceTreeNativeBootFileInput(
                source_path=(
                    vendor_kernel_dtb.path
                ),
                destination=(
                    PurePosixPath(
                        identity
                        .device_root
                        .as_posix()
                    )
                    / "boot"
                    / "native"
                    / "dtb"
                    / "00-vendor_kernel_boot.dtb"
                ),
                role="vendor_kernel_boot_dtb",
            ),
        )

        pvmfw_source = (
            pvmfw
            .image_artifact
            .path
            .resolve()
        )

        if not pvmfw_source.is_file():
            raise ValueError(
                "canonical pvmfw image is not materially available: "
                f"{pvmfw_source}"
            )

        partition_layout = (
            reconstruction
            .reconstruction_input
            .partition_layout
        )

        if partition_layout is None:
            raise ValueError(
                "native vendor_kernel_boot construction requires "
                "Partition Layout"
            )

        pvmfw_layout = (
            partition_layout.partition(
                "pvmfw"
            )
        )

        if (
            pvmfw_layout is None
            or pvmfw_layout.size_bytes
            is None
        ):
            raise ValueError(
                "pvmfw partition capacity is unavailable"
            )

        vendor_kernel_layout = (
            partition_layout.partition(
                "vendor_kernel_boot"
            )
        )

        if (
            vendor_kernel_layout is None
            or vendor_kernel_layout.size_bytes
            is None
        ):
            raise ValueError(
                "vendor_kernel_boot partition capacity is unavailable"
            )

        return AndroidDeviceTreeNativeBootBuildPlan(
            device_root=PurePosixPath(
                identity.device_root.as_posix()
            ),
            vendor_boot_requirement_id=(
                vendor_boot.requirement_id
            ),
            vendor_kernel_boot_requirement_id=(
                vendor_kernel_boot
                .requirement_id
            ),
            pvmfw_requirement_id=(
                pvmfw.requirement_id
            ),
            vendor_ramdisk_fragments=tuple(
                fragments
            ),
            file_inputs=file_inputs,
            bootconfig_parameters=bootconfig_parameters,
            kernel_cmdline_parameters=(
                kernel_cmdline_parameters
            ),
            ramdisk_use_lz4=ramdisk_use_lz4,
            pvmfw_source_path=(
                pvmfw_source
            ),
            pvmfw_destination=(
                PurePosixPath(
                    identity.device_root.as_posix()
                )
                / "boot"
                / "native"
                / "pvmfw"
                / "pvmfw.img"
            ),
            pvmfw_partition_size=(
                pvmfw_layout.size_bytes
            ),
            vendor_kernel_boot_partition_size=(
                vendor_kernel_layout
                .size_bytes
            ),
        )


class AndroidDeviceTreeNativeBootBuildRenderer:
    """
    Render standard Android configuration for the native boot builders.
    """

    @staticmethod
    def _render_kernel_cmdline_parameter(
        parameter: str,
    ) -> str:
        if (
            not isinstance(parameter, str)
            or not parameter
            or "\n" in parameter
            or "\r" in parameter
        ):
            raise ValueError(
                "kernel cmdline parameter must be a "
                "non-empty single-line string"
            )

        parameter = parameter.replace(
            "$",
            "$$",
        )

        rendered: list[str] = []
        preceding_backslashes = 0

        for character in parameter:
            if (
                character in {'"', '#'}
                and preceding_backslashes % 2 == 0
            ):
                rendered.append("\\")

            rendered.append(character)

            if character == "\\":
                preceding_backslashes += 1
            else:
                preceding_backslashes = 0

        return "".join(rendered)

    @staticmethod
    def render_board_config(
        plan: AndroidDeviceTreeNativeBootBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeNativeBootBuildPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeNativeBootBuildPlan"
            )

        bootconfig = (
            plan.file_input_for_role(
                "vendor_boot_bootconfig"
            )
        )

        dtb = (
            plan.file_input_for_role(
                "vendor_kernel_boot_dtb"
            )
        )

        if bootconfig is None:
            raise ValueError(
                "native boot plan lost vendor_boot bootconfig"
            )

        if dtb is None:
            raise ValueError(
                "native boot plan lost vendor_kernel_boot DTB"
            )

        dtb_dir = (
            dtb.destination.parent
        )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Canonical inputs for Android's normal vendor_boot and",
            "# vendor_kernel_boot builders.",
            "# TreeForge does not invoke mkbootimg here.",
            "",
            (
                "BOARD_PVMFWIMAGE_PARTITION_SIZE := "
                f"0x{plan.pvmfw_partition_size:08x}"
            ),
            (
                "BOARD_VENDOR_KERNEL_BOOTIMAGE_PARTITION_SIZE := "
                f"{plan.vendor_kernel_boot_partition_size}"
            ),
            "",
        ]

        if plan.vendor_ramdisk_fragments:
            lines.append(
                "BOARD_VENDOR_RAMDISK_FRAGMENTS := \\"
            )

            for index, fragment in enumerate(
                plan.vendor_ramdisk_fragments
            ):
                suffix = (
                    " \\"
                    if (
                        index
                        < len(
                            plan.vendor_ramdisk_fragments
                        )
                        - 1
                    )
                    else ""
                )

                lines.append(
                    f"    {fragment.name}{suffix}"
                )

            lines.append("")

        for fragment in (
            plan.vendor_ramdisk_fragments
        ):
            prefix = (
                "BOARD_VENDOR_RAMDISK_FRAGMENT."
                f"{fragment.name}"
            )

            lines.extend(
                [
                    (
                        f"{prefix}.PREBUILT := "
                        f"{fragment.destination.as_posix()}"
                    ),
                ]
            )

            args = [
                "--ramdisk_type",
                str(
                    fragment.ramdisk_type
                ),
            ]

            if fragment.ramdisk_name:
                args.extend(
                    [
                        "--ramdisk_name",
                        fragment.ramdisk_name,
                    ]
                )

            for index, value in enumerate(
                fragment.board_id
            ):
                if value:
                    args.extend(
                        [
                            f"--board_id{index}",
                            f"0x{value:08x}",
                        ]
                    )

            lines.extend(
                [
                    (
                        f"{prefix}.MKBOOTIMG_ARGS := "
                        + " ".join(args)
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                (
                    "BOARD_RAMDISK_USE_LZ4 := "
                    + (
                        "true"
                        if plan.ramdisk_use_lz4
                        else "false"
                    )
                ),
                "",
            ]
        )

        lines.extend(
            (
                "BOARD_KERNEL_CMDLINE += "
                + AndroidDeviceTreeNativeBootBuildRenderer
                ._render_kernel_cmdline_parameter(
                    parameter
                )
            )
            for parameter
            in plan.kernel_cmdline_parameters
        )

        if plan.kernel_cmdline_parameters:
            lines.append("")

        lines.extend(
            f"BOARD_BOOTCONFIG += {parameter}"
            for parameter in plan.bootconfig_parameters
        )

        lines.append("")

        lines.extend(
            [
                "BOARD_INCLUDE_DTB_IN_BOOTIMG := true",
                (
                    "BOARD_PREBUILT_DTBIMAGE_DIR := "
                    f"{dtb_dir.as_posix()}"
                ),
                "",
            ]
        )

        return (
            "\n".join(lines)
            .rstrip()
            + "\n"
        )

    @staticmethod
    def render_product_config(
        plan: AndroidDeviceTreeNativeBootBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeNativeBootBuildPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeNativeBootBuildPlan"
            )

        return (
            "# TreeForge boot-image construction ownership.\n"
            "# Android owns the actual image builders.\n"
            "PRODUCT_BUILD_VENDOR_BOOT_IMAGE := true\n"
            "PRODUCT_BUILD_VENDOR_KERNEL_BOOT_IMAGE := true\n"
            "\n"
            "# Android owns pvmfw image construction for this product.\n"
            "PRODUCT_BUILD_PVMFW_IMAGE := true\n"
            "\n"
            "PRODUCT_BUILD_VBMETA_IMAGE := true\n"
        )
