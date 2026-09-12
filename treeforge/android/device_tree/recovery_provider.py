from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath
import posixpath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.projection import (
    AndroidDeviceTreeSourceProjection,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeRecoveryConfigInput:
    """
    One already-reconstructed source consumed by a recovery provider module.

    The local copy exists so the recovery Android.bp never needs to escape
    its own source directory with ../ paths.
    """

    kind: str
    source_projection: AndroidDeviceTreeSourceProjection
    destination: PurePosixPath
    installed_name: str

    @property
    def config_id(self) -> str:
        return (
            "recovery-config:"
            f"{self.kind}:"
            f"{self.source_projection.representation_id}"
        )

    def __post_init__(self) -> None:
        if self.kind not in {
            "init",
            "vintf",
        }:
            raise ValueError(
                "recovery config kind must be init or vintf"
            )

        if not isinstance(
            self.source_projection,
            AndroidDeviceTreeSourceProjection,
        ):
            raise TypeError(
                "source_projection must be an "
                "AndroidDeviceTreeSourceProjection"
            )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if (
            self.destination.is_absolute()
            or ".." in self.destination.parts
        ):
            raise ValueError(
                "destination must be safe and Device Tree relative"
            )

        if (
            not isinstance(
                self.installed_name,
                str,
            )
            or not self.installed_name
        ):
            raise ValueError(
                "installed_name must be non-empty"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeRecoveryProvider:
    """
    One exact factory-derived recovery executable exposed to Android as a
    normal recovery cc_prebuilt_binary.

    Selection is relationship-driven:
      recovery INIT service -> executable -> exact vendor_boot ELF.
    """

    provider_id: str
    module_name: str

    source_path: Path
    source_requirement_id: str

    destination: PurePosixPath

    stem: str
    architecture: str
    relative_install_path: str

    shared_libs: tuple[str, ...]

    init_config_ids: tuple[str, ...]
    vintf_config_ids: tuple[str, ...]

    @property
    def size_bytes(self) -> int:
        return self.source_path.stat().st_size

    @property
    def sha256(self) -> str:
        return sha256(
            self.source_path.read_bytes()
        ).hexdigest()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("provider_id", self.provider_id),
            ("module_name", self.module_name),
            (
                "source_requirement_id",
                self.source_requirement_id,
            ),
            ("stem", self.stem),
            ("architecture", self.architecture),
            (
                "relative_install_path",
                self.relative_install_path,
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
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not self.source_path.is_file():
            raise ValueError(
                "recovery provider source must exist: "
                f"{self.source_path}"
            )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if (
            self.destination.is_absolute()
            or ".." in self.destination.parts
        ):
            raise ValueError(
                "recovery provider destination must be safe "
                "and Device Tree relative"
            )

        if (
            not isinstance(
                self.shared_libs,
                tuple,
            )
            or not all(
                isinstance(item, str)
                and item
                and item.strip() == item
                for item in self.shared_libs
            )
            or len(self.shared_libs)
            != len(set(self.shared_libs))
            or self.shared_libs
            != tuple(sorted(self.shared_libs))
        ):
            raise ValueError(
                "shared_libs must be a unique sorted tuple "
                "of normalized Soong module names"
            )

        for field_name, values in (
            (
                "init_config_ids",
                self.init_config_ids,
            ),
            (
                "vintf_config_ids",
                self.vintf_config_ids,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if len(values) != len(
                set(values)
            ):
                raise ValueError(
                    f"{field_name} must be unique"
                )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeRecoveryWipeInput:
    source_path: Path
    destination: PurePosixPath

    @property
    def size_bytes(self) -> int:
        return self.source_path.stat().st_size

    @property
    def sha256(self) -> str:
        return sha256(
            self.source_path.read_bytes()
        ).hexdigest()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not self.source_path.is_file():
            raise ValueError(
                "recovery wipe source must exist"
            )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if (
            self.destination.is_absolute()
            or ".." in self.destination.parts
        ):
            raise ValueError(
                "recovery wipe destination must be safe "
                "and Device Tree relative"
            )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeRecoveryProviderPlan:
    android_bp_path: PurePosixPath

    providers: tuple[
        AndroidDeviceTreeRecoveryProvider,
        ...,
    ]

    config_inputs: tuple[
        AndroidDeviceTreeRecoveryConfigInput,
        ...,
    ]

    recovery_wipe: (
        AndroidDeviceTreeRecoveryWipeInput
        | None
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.android_bp_path,
            PurePosixPath,
        ):
            raise TypeError(
                "android_bp_path must be a PurePosixPath"
            )

        provider_ids = tuple(
            item.provider_id
            for item
            in self.providers
        )

        module_names = tuple(
            item.module_name
            for item
            in self.providers
        )

        config_ids = tuple(
            item.config_id
            for item
            in self.config_inputs
        )

        for field_name, values in (
            ("provider identities", provider_ids),
            ("provider module names", module_names),
            ("config identities", config_ids),
        ):
            if len(values) != len(
                set(values)
            ):
                raise ValueError(
                    f"{field_name} must be unique"
                )

        known_config_ids = set(
            config_ids
        )

        for provider in self.providers:
            unknown = (
                set(
                    provider.init_config_ids
                    + provider.vintf_config_ids
                )
                - known_config_ids
            )

            if unknown:
                raise ValueError(
                    "recovery provider references unknown "
                    f"config inputs: {sorted(unknown)!r}"
                )


class AndroidDeviceTreeRecoveryProviderProjector:
    """
    Project exact device recovery providers from canonical TreeForge evidence.

    No provider name, SoC, product, or Google source path is hardcoded.

    Recovery provider evidence is:

      vendor_boot INIT source
          -> /system/bin/hw executable
          -> exact vendor_boot ELF

    Recovery VINTF documents remain independently owned by TreeForge's
    canonical VINTF build subsystem. This projector owns only exact recovery
    executables and their init_rc attachments.
    """

    _RECOVERY_INIT_DIRECTORY = (
        PurePosixPath(
            "/system/etc/init"
        )
    )

    _RECOVERY_HW_DIRECTORY = (
        PurePosixPath(
            "/system/bin/hw"
        )
    )

    @staticmethod
    def _source_name(
        filesystem_source,
    ) -> str | None:
        if filesystem_source is None:
            return None

        value = getattr(
            filesystem_source,
            "source_name",
            None,
        )

        return (
            value
            if isinstance(
                value,
                str,
            )
            else None
        )

    @staticmethod
    def _projection_for_source(
        *,
        projections: tuple[
            AndroidDeviceTreeSourceProjection,
            ...,
        ],
        family: str,
        source_path: Path,
    ) -> AndroidDeviceTreeSourceProjection:
        matches = tuple(
            projection
            for projection
            in projections
            if (
                projection.family == family
                and projection.source_path
                == source_path
            )
        )

        if len(matches) != 1:
            raise ValueError(
                "recovery provider source must map to exactly "
                "one Device Tree projection: "
                f"family={family!r}, "
                f"source={source_path}, "
                f"matches={len(matches)}"
            )

        return matches[0]

    @classmethod
    def project(
        cls,
        *,
        reconstruction: AndroidReconstructionResult,
        identity: AndroidDeviceTreeIdentity,
        source_projections: tuple[
            AndroidDeviceTreeSourceProjection,
            ...,
        ],
    ) -> AndroidDeviceTreeRecoveryProviderPlan:
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

        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        recovery_root = (
            PurePosixPath(
                identity.device_root.as_posix()
            )
            / "boot"
            / "recovery"
        )

        android_bp_path = (
            recovery_root
            / "Android.bp"
        )

        #
        # Exact recovery.wipe source.
        #
        structured = getattr(
            universe.parsing,
            "structured_configuration",
            None,
        )

        wipe_configs = (
            getattr(
                structured,
                "recovery_wipe_configurations",
                (),
            )
            if structured is not None
            else ()
        )

        vendor_boot_wipes = tuple(
            config
            for config
            in wipe_configs
            if (
                cls._source_name(
                    getattr(
                        config.source,
                        "filesystem_source",
                        None,
                    )
                )
                == "vendor_boot"
            )
        )

        if len(
            vendor_boot_wipes
        ) > 1:
            raise ValueError(
                "multiple vendor_boot recovery.wipe sources "
                "are ambiguous"
            )

        recovery_wipe = (
            AndroidDeviceTreeRecoveryWipeInput(
                source_path=(
                    vendor_boot_wipes[
                        0
                    ].source.host_path
                ),
                destination=(
                    recovery_root
                    / "recovery.wipe"
                ),
            )
            if vendor_boot_wipes
            else None
        )

        #
        # Group recovery INIT declarations by executable.
        #
        service_groups: dict[
            PurePosixPath,
            list[object],
        ] = {}

        for service in (
            universe.init_service_requirements
        ):
            if (
                cls._source_name(
                    service.filesystem_source
                )
                != "vendor_boot"
            ):
                continue

            if (
                service.android_path
                is None
                or service.android_path.parent
                != cls._RECOVERY_INIT_DIRECTORY
            ):
                continue

            executable = PurePosixPath(
                service.executable
            )

            if (
                not executable.is_absolute()
                or executable.parent
                != cls._RECOVERY_HW_DIRECTORY
            ):
                continue

            service_groups.setdefault(
                executable,
                [],
            ).append(
                service
            )

        elf_by_android_path = {}

        for requirement in (
            universe.elf_requirements
        ):
            parsed_source = (
                requirement
                .source
                .source
            )

            if (
                cls._source_name(
                    getattr(
                        parsed_source,
                        "filesystem_source",
                        None,
                    )
                )
                != "vendor_boot"
            ):
                continue

            android_path = (
                parsed_source.android_path
            )

            if android_path is None:
                continue

            if (
                getattr(
                    requirement.role,
                    "value",
                    None,
                )
                != "executable"
            ):
                continue

            if android_path in elf_by_android_path:
                raise ValueError(
                    "multiple exact vendor_boot ELF requirements "
                    "share one Android path: "
                    f"{android_path}"
                )

            elf_by_android_path[
                android_path
            ] = requirement

        config_by_destination: dict[
            str,
            AndroidDeviceTreeRecoveryConfigInput,
        ] = {}

        providers = []

        for executable in sorted(
            service_groups,
            key=lambda value: (
                value.as_posix()
            ),
        ):
            services = tuple(
                sorted(
                    service_groups[
                        executable
                    ],
                    key=lambda item: (
                        item.requirement_id
                    ),
                )
            )

            elf_requirement = (
                elf_by_android_path.get(
                    executable
                )
            )

            if elf_requirement is None:
                raise ValueError(
                    "vendor_boot hardware recovery service "
                    "has no exact matching ELF: "
                    f"{executable}"
                )

            architecture = (
                elf_requirement
                .android_architecture
            )

            if not architecture:
                raise ValueError(
                    "recovery provider ELF has no canonical "
                    "Android architecture: "
                    f"{executable}"
                )

            parsed_source = (
                elf_requirement
                .source
                .source
            )

            source_path = (
                parsed_source
                .host_path
            )

            identity_text = (
                f"{parsed_source.source_name}:"
                f"{executable.as_posix()}"
            )

            digest = sha256(
                identity_text.encode(
                    "utf-8"
                )
            ).hexdigest()[:12]

            module_name = (
                "treeforge_recovery_provider_"
                f"{digest}"
            )

            stem = executable.name

            relative_install_path = (
                executable
                .parent
                .relative_to(
                    PurePosixPath(
                        "/system/bin"
                    )
                )
                .as_posix()
            )

            binary_destination = (
                recovery_root
                / "providers"
                / module_name
                / stem
            )

            shared_libs = tuple(
                sorted(
                    {
                        dependency.name[:-3]
                        for dependency
                        in elf_requirement.dependencies
                        if (
                            dependency.name.endswith(
                                ".so"
                            )
                            and len(
                                dependency.name
                            ) > 3
                        )
                    }
                )
            )

            init_ids = []

            for service in services:
                projection = (
                    cls._projection_for_source(
                        projections=source_projections,
                        family="init",
                        source_path=(
                            service.source_path
                        ),
                    )
                )

                installed_name = (
                    service
                    .android_path
                    .name
                )

                destination = (
                    recovery_root
                    / "config"
                    / "init"
                    / installed_name
                )

                config = (
                    AndroidDeviceTreeRecoveryConfigInput(
                        kind="init",
                        source_projection=(
                            projection
                        ),
                        destination=(
                            destination
                        ),
                        installed_name=(
                            installed_name
                        ),
                    )
                )

                key = (
                    destination.as_posix()
                )

                existing = (
                    config_by_destination
                    .get(
                        key
                    )
                )

                if (
                    existing is not None
                    and (
                        existing
                        .source_projection
                        .content_id
                        != projection.content_id
                    )
                ):
                    raise ValueError(
                        "recovery INIT destination has "
                        "conflicting source identities: "
                        f"{destination}"
                    )

                config_by_destination[
                    key
                ] = config

                init_ids.append(
                    config.config_id
                )

            #
            # VINTF ownership remains with the canonical VINTF build
            # subsystem. Provider modules own only the executable and its
            # init_rc attachment.
            #
            vintf_ids = []

            providers.append(
                AndroidDeviceTreeRecoveryProvider(
                    provider_id=(
                        "recovery-provider:"
                        f"{identity_text}"
                    ),
                    module_name=(
                        module_name
                    ),
                    source_path=(
                        source_path
                    ),
                    source_requirement_id=(
                        elf_requirement
                        .requirement_id
                    ),
                    destination=(
                        binary_destination
                    ),
                    stem=stem,
                    architecture=(
                        architecture
                    ),
                    relative_install_path=(
                        relative_install_path
                    ),
                    shared_libs=shared_libs,
                    init_config_ids=tuple(
                        sorted(
                            set(
                                init_ids
                            )
                        )
                    ),
                    vintf_config_ids=tuple(
                        sorted(
                            set(
                                vintf_ids
                            )
                        )
                    ),
                )
            )

        return (
            AndroidDeviceTreeRecoveryProviderPlan(
                android_bp_path=(
                    android_bp_path
                ),
                providers=tuple(
                    sorted(
                        providers,
                        key=lambda item: (
                            item.module_name
                        ),
                    )
                ),
                config_inputs=tuple(
                    sorted(
                        config_by_destination
                        .values(),
                        key=lambda item: (
                            item.destination
                            .as_posix()
                        ),
                    )
                ),
                recovery_wipe=(
                    recovery_wipe
                ),
            )
        )


class AndroidDeviceTreeRecoveryProviderRenderer:
    @staticmethod
    def _relative(
        *,
        android_bp_path: PurePosixPath,
        source: PurePosixPath,
    ) -> str:
        return posixpath.relpath(
            source.as_posix(),
            android_bp_path
            .parent
            .as_posix(),
        )

    @classmethod
    def render_android_bp(
        cls,
        plan: AndroidDeviceTreeRecoveryProviderPlan,
    ) -> str:
        if not plan.providers:
            return ""

        config_by_id = {
            item.config_id: item
            for item
            in plan.config_inputs
        }

        lines = [
            "// TreeForge exact recovery providers.",
            "//",
            "// Provider selection comes from canonical "
            "vendor_boot INIT -> ELF relationships.",
            "",
        ]

        for provider in plan.providers:
            provider_source = cls._relative(
                android_bp_path=(
                    plan.android_bp_path
                ),
                source=(
                    provider.destination
                ),
            )

            lines.extend(
                [
                    "cc_prebuilt_binary {",
                    (
                        '    name: '
                        f'"{provider.module_name}",'
                    ),
                    (
                        '    stem: '
                        f'"{provider.stem}",'
                    ),
                    "    recovery: true,",
                    (
                        "    relative_install_path: "
                        f'"{provider.relative_install_path}",'
                    ),
                    "    check_elf_files: false,",
                    "    strip: {",
                    "        none: true,",
                    "    },",
                    "    arch: {",
                    (
                        f"        "
                        f"{provider.architecture}: {{"
                    ),
                    (
                        "            srcs: "
                        f'["{provider_source}"],'
                    ),
                    "        },",
                    "    },",
                ]
            )

            if provider.shared_libs:
                lines.append(
                    "    shared_libs: ["
                )

                for library in (
                    provider.shared_libs
                ):
                    lines.append(
                        f'        "{library}",'
                    )

                lines.append(
                    "    ],"
                )

            if provider.init_config_ids:
                lines.append(
                    "    init_rc: ["
                )

                for config_id in (
                    provider.init_config_ids
                ):
                    config = (
                        config_by_id[
                            config_id
                        ]
                    )

                    relative_source = (
                        cls._relative(
                            android_bp_path=(
                                plan.android_bp_path
                            ),
                            source=(
                                config.destination
                            ),
                        )
                    )

                    lines.append(
                        f'        "{relative_source}",'
                    )

                lines.append(
                    "    ],"
                )

            if provider.vintf_config_ids:
                lines.append(
                    "    vintf_fragments: ["
                )

                for config_id in (
                    provider.vintf_config_ids
                ):
                    config = (
                        config_by_id[
                            config_id
                        ]
                    )

                    relative_source = (
                        cls._relative(
                            android_bp_path=(
                                plan.android_bp_path
                            ),
                            source=(
                                config.destination
                            ),
                        )
                    )

                    lines.append(
                        f'        "{relative_source}",'
                    )

                lines.append(
                    "    ],"
                )

            lines.extend(
                [
                    "}",
                    "",
                ]
            )

        return (
            "\n".join(
                lines
            )
            .rstrip()
            + "\n"
        )

    @staticmethod
    def render_product_config(
        plan: AndroidDeviceTreeRecoveryProviderPlan,
    ) -> str:
        if not plan.providers:
            return ""

        lines = [
            "# Exact TreeForge recovery providers.",
            "PRODUCT_PACKAGES += \\",
        ]

        for index, provider in enumerate(
            plan.providers
        ):
            suffix = (
                " \\"
                if index
                < len(plan.providers) - 1
                else ""
            )

            lines.append(
                "    "
                f"{provider.module_name}"
                f"{suffix}"
            )

        return "\n".join(
            lines
        ) + "\n"

    @staticmethod
    def render_board_config(
        plan: AndroidDeviceTreeRecoveryProviderPlan,
    ) -> str:
        if plan.recovery_wipe is None:
            return ""

        return (
            "# Exact factory-derived recovery wipe policy.\n"
            "TARGET_RECOVERY_WIPE := "
            f"{plan.recovery_wipe.destination.as_posix()}\n"
        )
