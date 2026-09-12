from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.projection import (
    AndroidDeviceTreeSourceProjection,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.universe.fstab.source_context import (
    AndroidUniverseFstabSourceContext,
)
from treeforge.android.version.device_tree.boot_architecture import (
    AndroidDeviceTreeBootArchitectureProfile,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeRamdiskRecoverySourceVariant:
    """
    One exact observed fstab source retained solely for Android build
    composition.

    A source variant:
    - is not an active Reconstruction semantic representation;
    - carries no Reconstruction work item;
    - cannot activate an alternative Universe requirement;
    - preserves the exact extracted factory bytes;
    - is materialized only because the selected Android boot architecture
      needs the observed source available during ramdisk construction.
    """

    source_identity: tuple[str, str]
    source_path: Path
    android_path: PurePosixPath
    destination: PurePosixPath
    payload: bytes
    role: str

    @property
    def variant_id(self) -> str:
        return (
            "fstab-build-source-variant:"
            f"{self.source_identity[0]}::"
            f"{self.source_identity[1]}"
        )

    @property
    def size_bytes(self) -> int:
        return len(self.payload)

    @property
    def sha256(self) -> str:
        return sha256(
            self.payload
        ).hexdigest()

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.source_identity,
                tuple,
            )
            or len(
                self.source_identity
            ) != 2
            or not all(
                isinstance(
                    value,
                    str,
                )
                and value
                for value
                in self.source_identity
            )
        ):
            raise TypeError(
                "source_identity must be a canonical "
                "(source_name, path_identity) tuple"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not isinstance(
            self.android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "android_path must be a PurePosixPath"
            )

        if not self.android_path.is_absolute():
            raise ValueError(
                "android_path must be absolute"
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
            not isinstance(
                self.payload,
                bytes,
            )
            or not self.payload
        ):
            raise ValueError(
                "payload must contain non-empty exact source bytes"
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
class AndroidDeviceTreeRamdiskRecoveryCopy:
    """
    One exact generated-source handoff into an Android ramdisk staging domain.

    The source remains the canonical TreeForge Device Tree projection.
    The destination is Android build syntax, not a reconstructed filesystem
    location inside TreeForge itself.
    """

    source: PurePosixPath
    destination: str
    role: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            PurePosixPath,
        ):
            raise TypeError(
                "source must be a PurePosixPath"
            )

        if self.source.is_absolute():
            raise ValueError(
                "source must be Device Tree relative"
            )

        if ".." in self.source.parts:
            raise ValueError(
                "source must not escape the Device Tree workspace"
            )

        for field_name, value in (
            (
                "destination",
                self.destination,
            ),
            (
                "role",
                self.role,
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


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeRamdiskRecoveryBuildPlan:
    """
    TreeForge-owned Android ramdisk/recovery source-staging contract.

    This deliberately contains no AOSP checkout paths and does not preserve
    a compressed vendor ramdisk container.
    """

    source_variants: tuple[
        AndroidDeviceTreeRamdiskRecoverySourceVariant,
        ...,
    ]

    vendor_ramdisk_copies: tuple[
        AndroidDeviceTreeRamdiskRecoveryCopy,
        ...,
    ]

    recovery_root_copies: tuple[
        AndroidDeviceTreeRamdiskRecoveryCopy,
        ...,
    ]

    recovery_fstab_source: (
        PurePosixPath
        | None
    )

    recovery_default_rotation: str | None = None
    recovery_pixel_format: str | None = None
    recovery_ui_margin_height: int | None = None
    recovery_ui_libs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_variants,
            tuple,
        ):
            raise TypeError(
                "source_variants must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeRamdiskRecoverySourceVariant,
            )
            for item
            in self.source_variants
        ):
            raise TypeError(
                "source_variants contains an invalid model"
            )

        variant_ids = tuple(
            item.variant_id
            for item
            in self.source_variants
        )

        if len(
            variant_ids
        ) != len(
            set(
                variant_ids
            )
        ):
            raise ValueError(
                "ramdisk/recovery source variant identities "
                "must be unique"
            )

        variant_destinations = tuple(
            item.destination.as_posix()
            for item
            in self.source_variants
        )

        if len(
            variant_destinations
        ) != len(
            set(
                variant_destinations
            )
        ):
            raise ValueError(
                "ramdisk/recovery source variant destinations "
                "must be unique"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeRamdiskRecoveryCopy,
            )
            for item
            in (
                self.vendor_ramdisk_copies
                + self.recovery_root_copies
            )
        ):
            raise TypeError(
                "ramdisk/recovery copy populations contain "
                "an invalid model"
            )

        if (
            self.recovery_fstab_source
            is not None
            and not isinstance(
                self.recovery_fstab_source,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "recovery_fstab_source must be "
                "PurePosixPath or None"
            )

        for field_name, value in (
            (
                "recovery_default_rotation",
                self.recovery_default_rotation,
            ),
            (
                "recovery_pixel_format",
                self.recovery_pixel_format,
            ),
        ):
            if (
                value is not None
                and (
                    not isinstance(value, str)
                    or not value.strip()
                    or value.strip() != value
                )
            ):
                raise ValueError(
                    f"{field_name} must be None or a "
                    "non-empty trimmed string"
                )

        if (
            self.recovery_ui_margin_height is not None
            and (
                isinstance(
                    self.recovery_ui_margin_height,
                    bool,
                )
                or not isinstance(
                    self.recovery_ui_margin_height,
                    int,
                )
                or self.recovery_ui_margin_height < 0
            )
        ):
            raise ValueError(
                "recovery_ui_margin_height must be None "
                "or a non-negative integer"
            )

        if not isinstance(
            self.recovery_ui_libs,
            tuple,
        ):
            raise TypeError(
                "recovery_ui_libs must be a tuple"
            )

        if not all(
            isinstance(item, str)
            and item
            and item.strip() == item
            for item in self.recovery_ui_libs
        ):
            raise ValueError(
                "recovery_ui_libs must contain only "
                "non-empty trimmed strings"
            )

        if len(
            self.recovery_ui_libs
        ) != len(
            set(self.recovery_ui_libs)
        ):
            raise ValueError(
                "recovery_ui_libs must be unique"
            )

        destinations = tuple(
            item.destination
            for item
            in (
                self.vendor_ramdisk_copies
                + self.recovery_root_copies
            )
        )

        if len(
            destinations
        ) != len(
            set(
                destinations
            )
        ):
            raise ValueError(
                "ramdisk/recovery staging destinations "
                "must be unique"
            )


class AndroidDeviceTreeRamdiskRecoveryBuildProjector:
    """
    Project canonical Reconstruction source identities into the Android
    staging domains required by the selected boot architecture.

    This projector does not:
    - inspect an AOSP checkout;
    - infer device names or SoC names;
    - copy the factory vendor ramdisk as a container;
    - reinterpret fstab or init semantics;
    - manufacture recovery providers.

    It only maps already-preserved source-domain identities into the
    standard Android ramdisk/recovery build surfaces proven for this
    boot architecture.
    """

    _FIRST_STAGE_PREFIX = (
        "/first_stage_ramdisk/"
    )

    _RECOVERY_FSTAB_PATH = (
        "/system/etc/recovery.fstab"
    )

    _RECOVERY_INIT_PREFIX = (
        "/init.recovery."
    )

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
        boot_architecture_profile: (
            AndroidDeviceTreeBootArchitectureProfile
        ),
    ) -> AndroidDeviceTreeRamdiskRecoveryBuildPlan:
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

        if not isinstance(
            source_projections,
            tuple,
        ):
            raise TypeError(
                "source_projections must be a tuple"
            )

        if not all(
            isinstance(
                projection,
                AndroidDeviceTreeSourceProjection,
            )
            for projection
            in source_projections
        ):
            raise TypeError(
                "source_projections contains an invalid model"
            )

        if not isinstance(
            boot_architecture_profile,
            AndroidDeviceTreeBootArchitectureProfile,
        ):
            raise TypeError(
                "boot_architecture_profile must be an "
                "AndroidDeviceTreeBootArchitectureProfile"
            )

        #
        # This first implementation belongs only to the architecture in
        # which recovery resources are folded into vendor_boot.
        #
        # Other boot architectures will get their own explicit destination
        # policy instead of falling through to this one.
        #
        if not (
            boot_architecture_profile
            .move_recovery_resources_to_vendor_boot
        ):
            return (
                AndroidDeviceTreeRamdiskRecoveryBuildPlan(
                    source_variants=(),
                    vendor_ramdisk_copies=(),
                    recovery_root_copies=(),
                    recovery_fstab_source=None,
                )
            )

        source_variants = []
        vendor_ramdisk_copies = []
        recovery_root_copies = []
        recovery_fstab_candidates = []

        #
        # Recovery display rotation is device-specific factory evidence.
        #
        # Do not promote tangorpro's ROTATION_LEFT into the gs201 or
        # Android-version profile. Resolve the exact reconstructed
        # ro.minui.default_rotation declaration instead.
        #
        recovery_default_rotation = (
            boot_architecture_profile
            .recovery_default_rotation
        )

        rotation_representations = tuple(
            representation
            for representation
            in reconstruction.runtime_property_representations
            if (
                representation.property_key
                == "ro.minui.default_rotation"
            )
        )

        if len(rotation_representations) > 1:
            raise ValueError(
                "multiple reconstructed runtime-property "
                "representations exist for "
                "ro.minui.default_rotation"
            )

        if rotation_representations:
            rotation_requirement = (
                rotation_representations[0]
                .requirement
            )

            declared_rotation_values = tuple(
                sorted(
                    {
                        observation.declaration.value
                        for observation
                        in rotation_requirement
                        .declaration_observations
                        if observation.declaration.value
                    }
                )
            )

            if len(declared_rotation_values) > 1:
                raise ValueError(
                    "factory evidence disagrees on "
                    "ro.minui.default_rotation: "
                    f"{declared_rotation_values!r}"
                )

            if declared_rotation_values:
                factory_rotation = (
                    declared_rotation_values[0]
                )

                if (
                    recovery_default_rotation is not None
                    and recovery_default_rotation
                    != factory_rotation
                ):
                    raise ValueError(
                        "versioned recovery rotation conflicts "
                        "with exact factory evidence: "
                        f"profile={recovery_default_rotation!r}, "
                        f"factory={factory_rotation!r}"
                    )

                recovery_default_rotation = (
                    factory_rotation
                )

        #
        # Runtime applicability and build-source availability are distinct.
        #
        # Reconstruction contains only ACTIVE fstab sources. Planning still
        # preserves every canonical fstab source context, so any observed
        # non-active first-stage source can remain available to Android's
        # vendor-ramdisk builder without being promoted into active semantic
        # work.
        #
        active_fstab_source_identities = {
            representation.source_identity
            for representation
            in reconstruction.fstab_source_representations
        }

        source_contexts = (
            reconstruction
            .reconstruction_input
            .plan
            .fstab_source_contexts
        )

        if not isinstance(
            source_contexts,
            tuple,
        ):
            raise TypeError(
                "plan.fstab_source_contexts must be a tuple"
            )

        if not all(
            isinstance(
                context,
                AndroidUniverseFstabSourceContext,
            )
            for context
            in source_contexts
        ):
            raise TypeError(
                "plan.fstab_source_contexts contains an invalid model"
            )

        variant_contexts = tuple(
            context
            for context
            in source_contexts
            if (
                context.source_identity
                not in active_fstab_source_identities
                and context.android_path is not None
                and context.android_path.as_posix().startswith(
                    cls._FIRST_STAGE_PREFIX
                )
            )
        )

        variant_name_counts: dict[str, int] = {}

        for context in variant_contexts:
            preferred_name = (
                context.android_path.name
                if context.android_path is not None
                else ""
            )

            if not preferred_name:
                raise ValueError(
                    "first-stage fstab source variant has "
                    "no usable filename"
                )

            variant_name_counts[
                preferred_name
            ] = (
                variant_name_counts.get(
                    preferred_name,
                    0,
                )
                + 1
            )

        for context in sorted(
            variant_contexts,
            key=lambda item: (
                item.source_identity,
            ),
        ):
            source_path = (
                context.source_path
            )

            if not source_path.is_file():
                raise ValueError(
                    "canonical first-stage fstab source variant "
                    "is unavailable: "
                    f"{source_path}"
                )

            android_path = (
                context.android_path
            )

            if android_path is None:
                raise ValueError(
                    "first-stage fstab source variant "
                    "lost android_path"
                )

            filename = (
                android_path.name
            )

            if (
                variant_name_counts[
                    filename
                ]
                > 1
            ):
                identity_text = (
                    f"{context.source_identity[0]}::"
                    f"{context.source_identity[1]}"
                )

                digest = sha256(
                    identity_text.encode(
                        "utf-8"
                    )
                ).hexdigest()[:12]

                filename = (
                    f"{filename}-{digest}"
                )

            destination = (
                PurePosixPath(
                    identity.device_root.as_posix()
                )
                / "fstab"
                / "variants"
                / filename
            )

            variant = (
                AndroidDeviceTreeRamdiskRecoverySourceVariant(
                    source_identity=(
                        context.source_identity
                    ),
                    source_path=(
                        source_path
                    ),
                    android_path=(
                        android_path
                    ),
                    destination=(
                        destination
                    ),
                    payload=(
                        source_path.read_bytes()
                    ),
                    role=(
                        "vendor_ramdisk_first_stage_variant"
                    ),
                )
            )

            source_variants.append(
                variant
            )

            vendor_ramdisk_copies.append(
                AndroidDeviceTreeRamdiskRecoveryCopy(
                    source=(
                        variant.destination
                    ),
                    destination=(
                        "$(TARGET_COPY_OUT_VENDOR_RAMDISK)"
                        f"{android_path.as_posix()}"
                    ),
                    role=(
                        "vendor_ramdisk_first_stage_variant"
                    ),
                )
            )

        for projection in source_projections:
            android_path = (
                projection.android_path
            )

            if android_path is None:
                continue

            path = android_path.as_posix()

            #
            # Canonical first-stage content already carries its ramdisk-root
            # path. Preserve that path mechanically under Android's standard
            # vendor_ramdisk staging root.
            #
            if (
                projection.family == "fstab"
                and path.startswith(
                    cls._FIRST_STAGE_PREFIX
                )
            ):
                vendor_ramdisk_copies.append(
                    AndroidDeviceTreeRamdiskRecoveryCopy(
                        source=projection.destination,
                        destination=(
                            "$(TARGET_COPY_OUT_VENDOR_RAMDISK)"
                            f"{path}"
                        ),
                        role="vendor_ramdisk_first_stage",
                    )
                )

                continue

            #
            # Android's recovery builder owns the final recovery.fstab
            # destination. Feed it the canonical TreeForge source via
            # TARGET_RECOVERY_FSTAB rather than independently copying a
            # second output file.
            #
            if (
                projection.family == "fstab"
                and path
                == cls._RECOVERY_FSTAB_PATH
            ):
                recovery_fstab_candidates.append(
                    projection.destination
                )

                continue

            #
            # Device-specific init.recovery.*.rc files are ordinary
            # recovery-root source inputs.
            #
            if (
                projection.family == "init"
                and path.startswith(
                    cls._RECOVERY_INIT_PREFIX
                )
                and path.endswith(".rc")
                and PurePosixPath(
                    path
                ).parent
                == PurePosixPath("/")
            ):
                recovery_root_copies.append(
                    AndroidDeviceTreeRamdiskRecoveryCopy(
                        source=projection.destination,
                        destination=(
                            "$(TARGET_COPY_OUT_RECOVERY)/root"
                            f"{path}"
                        ),
                        role="recovery_init",
                    )
                )

        if len(
            recovery_fstab_candidates
        ) > 1:
            raise ValueError(
                "boot architecture has multiple canonical "
                "recovery.fstab source candidates; refusing "
                "to guess recovery ownership"
            )

        vendor_ramdisk_copies = tuple(
            sorted(
                vendor_ramdisk_copies,
                key=lambda item: (
                    item.destination,
                    item.source.as_posix(),
                ),
            )
        )

        recovery_root_copies = tuple(
            sorted(
                recovery_root_copies,
                key=lambda item: (
                    item.destination,
                    item.source.as_posix(),
                ),
            )
        )

        return (
            AndroidDeviceTreeRamdiskRecoveryBuildPlan(
                source_variants=tuple(
                    sorted(
                        source_variants,
                        key=lambda item: (
                            item.variant_id,
                        ),
                    )
                ),
                vendor_ramdisk_copies=(
                    vendor_ramdisk_copies
                ),
                recovery_root_copies=(
                    recovery_root_copies
                ),
                recovery_fstab_source=(
                    recovery_fstab_candidates[0]
                    if recovery_fstab_candidates
                    else None
                ),
                recovery_default_rotation=(
                    recovery_default_rotation
                ),
                recovery_pixel_format=(
                    boot_architecture_profile
                    .recovery_pixel_format
                ),
                recovery_ui_margin_height=(
                    boot_architecture_profile
                    .recovery_ui_margin_height
                ),
                recovery_ui_libs=(
                    boot_architecture_profile
                    .recovery_ui_libs
                ),
            )
        )


class AndroidDeviceTreeRamdiskRecoveryBuildRenderer:
    """
    Render the TreeForge ramdisk/recovery plan into standard Android syntax.
    """

    @staticmethod
    def render_product_config(
        plan: AndroidDeviceTreeRamdiskRecoveryBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeRamdiskRecoveryBuildPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeRamdiskRecoveryBuildPlan"
            )

        copies = (
            plan.vendor_ramdisk_copies
            + plan.recovery_root_copies
        )

        if not copies:
            return ""

        lines = [
            "# TreeForge-owned ramdisk/recovery source staging.",
            "#",
            "# Sources are reconstructed factory semantics.",
            "# Android owns the final recovery/vendor-ramdisk containers.",
            "",
            "PRODUCT_COPY_FILES += \\",
        ]

        for index, copy in enumerate(
            copies
        ):
            suffix = (
                " \\"
                if index
                < len(copies) - 1
                else ""
            )

            lines.append(
                "    "
                f"{copy.source.as_posix()}:"
                f"{copy.destination}"
                f"{suffix}"
            )

        return "\n".join(
            lines
        ) + "\n"

    @staticmethod
    def render_board_config(
        plan: AndroidDeviceTreeRamdiskRecoveryBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeRamdiskRecoveryBuildPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeRamdiskRecoveryBuildPlan"
            )

        lines = [
            "# TreeForge-owned recovery build contract.",
            "#",
            "# Factory/device semantics and versioned Android build facts",
            "# remain explicit inputs; Android owns final ramdisk assembly.",
        ]

        if plan.recovery_fstab_source is not None:
            lines.extend(
                [
                    "",
                    "# Android's recovery builder installs this canonical",
                    "# source as system/etc/recovery.fstab.",
                    "TARGET_RECOVERY_FSTAB := "
                    f"{plan.recovery_fstab_source.as_posix()}",
                ]
            )

        if plan.recovery_default_rotation is not None:
            lines.extend(
                [
                    "",
                    "TARGET_RECOVERY_DEFAULT_ROTATION := "
                    f"{plan.recovery_default_rotation}",
                ]
            )

        if plan.recovery_pixel_format is not None:
            lines.extend(
                [
                    "",
                    "TARGET_RECOVERY_PIXEL_FORMAT := "
                    f"{plan.recovery_pixel_format}",
                ]
            )

        if plan.recovery_ui_margin_height is not None:
            lines.extend(
                [
                    "",
                    "TARGET_RECOVERY_UI_MARGIN_HEIGHT := "
                    f"{plan.recovery_ui_margin_height}",
                ]
            )

        if plan.recovery_ui_libs:
            lines.extend(
                [
                    "",
                    "TARGET_RECOVERY_UI_LIB := \\",
                ]
            )

            for index, module in enumerate(
                plan.recovery_ui_libs
            ):
                suffix = (
                    " \\"
                    if index
                    < len(plan.recovery_ui_libs) - 1
                    else ""
                )

                lines.append(
                    f"    {module}{suffix}"
                )

        if len(lines) == 4:
            return ""

        return "\n".join(lines) + "\n"
