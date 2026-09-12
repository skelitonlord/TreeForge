from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import time

from treeforge.android.boot_image.deployment_planning import (
    AndroidBootImageBaseDeployment,
    AndroidBootImageDeploymentImage,
    AndroidBootImageDeploymentPlan,
    AndroidBootImageReusableDeployment,
)
from treeforge.android.host_tools import (
    treeforge_adb_executable,
    treeforge_fastboot_executable,
)


class AndroidBootImageDeviceMode(str, Enum):
    ANDROID_ADB = "android_adb"
    RECOVERY_ADB = "recovery_adb"
    FASTBOOT_BOOTLOADER = "fastboot_bootloader"
    FASTBOOTD = "fastbootd"


class AndroidBootImageSlotSelection(str, Enum):
    SLOT_A = "a"
    SLOT_B = "b"


class AndroidBootImageDeploymentPayload(str, Enum):
    """
    Exact byte population intentionally selected for hardware deployment.
    """

    MODIFIED = "modified"
    ORIGINAL = "original"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageFastbootDevice:
    serial: str
    initial_mode: AndroidBootImageDeviceMode
    final_mode: AndroidBootImageDeviceMode
    current_slot: str | None
    slot_count: int | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.serial, str)
            or not self.serial
        ):
            raise ValueError(
                "serial must be a non-empty string"
            )

        if not isinstance(
            self.initial_mode,
            AndroidBootImageDeviceMode,
        ):
            raise TypeError(
                "initial_mode must be an AndroidBootImageDeviceMode"
            )

        if (
            self.final_mode
            is not
            AndroidBootImageDeviceMode.FASTBOOT_BOOTLOADER
        ):
            raise ValueError(
                "Device Deployment must finish preparation in "
                "bootloader fastboot mode"
            )

        if (
            self.current_slot is not None
            and self.current_slot not in {
                "a",
                "b",
            }
        ):
            raise ValueError(
                "current_slot must be a, b, or None"
            )

        if (
            self.slot_count is not None
            and (
                isinstance(self.slot_count, bool)
                or not isinstance(
                    self.slot_count,
                    int,
                )
                or self.slot_count <= 0
            )
        ):
            raise ValueError(
                "slot_count must be a positive int or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDeviceInspection:
    deployment: (
        AndroidBootImageDeploymentPlan
        | AndroidBootImageReusableDeployment
        | AndroidBootImageBaseDeployment
    )

    adb_path: Path | None
    fastboot_path: Path

    device: AndroidBootImageFastbootDevice

    slot_applicability: tuple[
        tuple[
            AndroidBootImageDeploymentImage,
            bool,
        ],
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.deployment,
            (
                AndroidBootImageDeploymentPlan,
                AndroidBootImageReusableDeployment,
                AndroidBootImageBaseDeployment,
            ),
        ):
            raise TypeError(
                "deployment must be an AndroidBootImageDeploymentPlan"
            )

        if (
            self.adb_path is not None
            and not isinstance(
                self.adb_path,
                Path,
            )
        ):
            raise TypeError(
                "adb_path must be a pathlib.Path or None"
            )

        if not isinstance(
            self.fastboot_path,
            Path,
        ):
            raise TypeError(
                "fastboot_path must be a pathlib.Path"
            )

        if not self.fastboot_path.is_file():
            raise FileNotFoundError(
                "fastboot executable is unavailable: "
                f"{self.fastboot_path}"
            )

        if not isinstance(
            self.device,
            AndroidBootImageFastbootDevice,
        ):
            raise TypeError(
                "device must be an AndroidBootImageFastbootDevice"
            )

        if tuple(
            id(image)
            for image, _
            in self.slot_applicability
        ) != tuple(
            id(image)
            for image
            in self.deployment.images
        ):
            raise ValueError(
                "Device inspection must conserve every Deployment "
                "Planning image in exact order and identity"
            )

        if not all(
            isinstance(slot_applicable, bool)
            for _, slot_applicable
            in self.slot_applicability
        ):
            raise TypeError(
                "slot applicability must contain bool values"
            )

    @property
    def has_slotted_targets(self) -> bool:
        return any(
            slot_applicable
            for _, slot_applicable
            in self.slot_applicability
        )

    @property
    def active_slot(self) -> str | None:
        return self.device.current_slot

    @property
    def inactive_slot(self) -> str | None:
        if (
            self.device.current_slot is None
            or self.device.slot_count != 2
        ):
            return None

        return (
            "b"
            if self.device.current_slot == "a"
            else "a"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDeviceDeploymentTarget:
    image: AndroidBootImageDeploymentImage

    partition_name: str
    slot_applicable: bool
    target_slot: str | None
    fastboot_partition: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.image,
            AndroidBootImageDeploymentImage,
        ):
            raise TypeError(
                "image must be an AndroidBootImageDeploymentImage"
            )

        if (
            not isinstance(
                self.partition_name,
                str,
            )
            or not self.partition_name
        ):
            raise ValueError(
                "partition_name must be non-empty"
            )

        if not isinstance(
            self.slot_applicable,
            bool,
        ):
            raise TypeError(
                "slot_applicable must be bool"
            )

        if self.slot_applicable:
            if self.target_slot not in {
                "a",
                "b",
            }:
                raise ValueError(
                    "slotted target requires slot a or b"
                )

            if self.fastboot_partition != (
                f"{self.partition_name}_"
                f"{self.target_slot}"
            ):
                raise ValueError(
                    "slotted fastboot partition does not match "
                    "partition + selected slot"
                )

        else:
            if self.target_slot is not None:
                raise ValueError(
                    "non-slotted partition cannot retain a slot"
                )

            if (
                self.fastboot_partition
                != self.partition_name
            ):
                raise ValueError(
                    "non-slotted fastboot partition must equal "
                    "canonical partition name"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDeviceDeploymentPlan:
    inspection: AndroidBootImageDeviceInspection

    payload: AndroidBootImageDeploymentPayload

    slot_selection: (
        AndroidBootImageSlotSelection
        | None
    )

    targets: tuple[
        AndroidBootImageDeviceDeploymentTarget,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.inspection,
            AndroidBootImageDeviceInspection,
        ):
            raise TypeError(
                "inspection must be an AndroidBootImageDeviceInspection"
            )

        if not isinstance(
            self.payload,
            AndroidBootImageDeploymentPayload,
        ):
            raise TypeError(
                "payload must be an AndroidBootImageDeploymentPayload"
            )

        if self.inspection.has_slotted_targets:
            if not isinstance(
                self.slot_selection,
                AndroidBootImageSlotSelection,
            ):
                raise ValueError(
                    "slotted deployment requires explicit "
                    "active/inactive selection"
                )

        elif self.slot_selection is not None:
            raise ValueError(
                "non-slotted deployment cannot retain "
                "a slot selection"
            )

        if tuple(
            id(target.image)
            for target
            in self.targets
        ) != tuple(
            id(image)
            for image
            in self.inspection.deployment.images
        ):
            raise ValueError(
                "Device Deployment must conserve every Deployment "
                "Planning image in exact order and identity"
            )

    @property
    def deployment(
        self,
    ) -> (
        AndroidBootImageDeploymentPlan
        | AndroidBootImageReusableDeployment
        | AndroidBootImageBaseDeployment
    ):
        return self.inspection.deployment

    @property
    def device(self) -> AndroidBootImageFastbootDevice:
        return self.inspection.device

    @property
    def fastboot_path(self) -> Path:
        return self.inspection.fastboot_path


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageFlashInvocation:
    target: AndroidBootImageDeviceDeploymentTarget

    payload: AndroidBootImageDeploymentPayload

    command: tuple[str, ...]
    returncode: int

    stdout: bytes
    stderr: bytes

    def __post_init__(self) -> None:
        if not isinstance(
            self.target,
            AndroidBootImageDeviceDeploymentTarget,
        ):
            raise TypeError(
                "target must be an "
                "AndroidBootImageDeviceDeploymentTarget"
            )

        if not isinstance(
            self.payload,
            AndroidBootImageDeploymentPayload,
        ):
            raise TypeError(
                "payload must be an AndroidBootImageDeploymentPayload"
            )

        if (
            not isinstance(self.command, tuple)
            or not self.command
        ):
            raise ValueError(
                "command must be a non-empty tuple"
            )

        if self.returncode != 0:
            raise ValueError(
                "successful flash invocation requires returncode 0"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDeviceDeploymentResult:
    plan: AndroidBootImageDeviceDeploymentPlan

    invocations: tuple[
        AndroidBootImageFlashInvocation,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.plan,
            AndroidBootImageDeviceDeploymentPlan,
        ):
            raise TypeError(
                "plan must be an AndroidBootImageDeviceDeploymentPlan"
            )

        if tuple(
            id(invocation.target)
            for invocation
            in self.invocations
        ) != tuple(
            id(target)
            for target
            in self.plan.targets
        ):
            raise ValueError(
                "Device Deployment must execute every target "
                "exactly once in plan order"
            )

        if any(
            invocation.payload
            is not self.plan.payload
            for invocation
            in self.invocations
        ):
            raise ValueError(
                "flash invocation payload does not match "
                "Device Deployment plan"
            )


class AndroidBootImageDeviceDeployer:
    """
    Hardware-facing Boot Image deployment owner.

    Device state:
      - detects ADB, bootloader fastboot, or fastbootd;
      - transitions ADB/fastbootd to bootloader fastboot as required;
      - re-discovers the same device;
      - re-queries authoritative slot state after transition.

    Deployment policy:
      - modified vs original image population is explicit;
      - active vs inactive slot is explicit;
      - selected bytes are reverified immediately before flashing;
      - the complementary original image remains available when modified
        bytes are selected;
      - no automatic set-active;
      - reboot occurs only after explicit caller confirmation.
    """

    FASTBOOT_DISCOVERY_ATTEMPTS = 30
    FASTBOOT_DISCOVERY_INTERVAL_SECONDS = 1.0

    @staticmethod
    def _file_identity(
        path: Path,
    ) -> tuple[int, str]:
        if not path.is_file():
            raise FileNotFoundError(
                "Boot Image Device Deployment artifact "
                f"is unavailable: {path}"
            )

        digest = sha256()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(chunk)

        return (
            path.stat().st_size,
            digest.hexdigest(),
        )

    @staticmethod
    def _run(
        command: tuple[str, ...],
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    @staticmethod
    def _executable(
        name: str,
        *,
        required: bool,
    ) -> Path | None:
        try:
            if name == "adb":
                return (
                    treeforge_adb_executable()
                )

            if name == "fastboot":
                return (
                    treeforge_fastboot_executable()
                )

            raise RuntimeError(
                "Boot Image Device Deployment requested "
                f"an unsupported host executable: {name}"
            )

        except (
            RuntimeError,
            KeyError,
            ValueError,
            FileNotFoundError,
        ) as error:
            if required:
                raise RuntimeError(
                    "Boot Image Device Deployment requires "
                    "the TreeForge-owned "
                    f"{name} host provider"
                ) from error

            return None

    @classmethod
    def _fastboot_serials(
        cls,
        fastboot: Path,
    ) -> tuple[str, ...]:
        completed = cls._run(
            (
                str(fastboot),
                "devices",
            )
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "fastboot devices failed: "
                + (
                    completed.stderr
                    + b"\n"
                    + completed.stdout
                ).decode(
                    "utf-8",
                    errors="replace",
                )
            )

        serials = []

        for raw_line in (
            completed.stdout
            .decode(
                "utf-8",
                errors="replace",
            )
            .splitlines()
        ):
            fields = raw_line.strip().split()

            if fields:
                serials.append(fields[0])

        return tuple(serials)

    @classmethod
    def _adb_serials(
        cls,
        adb: Path,
    ) -> tuple[str, ...]:
        completed = cls._run(
            (
                str(adb),
                "devices",
            )
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "adb devices failed: "
                + (
                    completed.stderr
                    + b"\n"
                    + completed.stdout
                ).decode(
                    "utf-8",
                    errors="replace",
                )
            )

        serials = []

        lines = (
            completed.stdout
            .decode(
                "utf-8",
                errors="replace",
            )
            .splitlines()
        )

        for raw_line in lines[1:]:
            fields = raw_line.strip().split()

            if (
                len(fields) >= 2
                and fields[1] == "device"
            ):
                serials.append(fields[0])

        return tuple(serials)

    @classmethod
    def _getvar(
        cls,
        *,
        fastboot: Path,
        serial: str,
        name: str,
    ) -> str | None:
        completed = cls._run(
            (
                str(fastboot),
                "-s",
                serial,
                "getvar",
                name,
            )
        )

        text = (
            completed.stderr
            + b"\n"
            + completed.stdout
        ).decode(
            "utf-8",
            errors="replace",
        )

        if completed.returncode != 0:
            return None

        prefix = f"{name}:"

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if line.startswith(prefix):
                value = (
                    line[
                        len(prefix):
                    ]
                    .strip()
                )

                return value or None

        return None

    @classmethod
    def _adb_getprop(
        cls,
        *,
        adb: Path,
        serial: str,
        name: str,
    ) -> str | None:
        completed = cls._run(
            (
                str(adb),
                "-s",
                serial,
                "shell",
                "getprop",
                name,
            )
        )

        if completed.returncode != 0:
            return None

        value = (
            completed.stdout
            .decode(
                "utf-8",
                errors="replace",
            )
            .strip()
        )

        return value or None

    @classmethod
    def _classify_adb_mode(
        cls,
        *,
        adb: Path,
        serial: str,
    ) -> AndroidBootImageDeviceMode:
        bootmode = (
            cls._adb_getprop(
                adb=adb,
                serial=serial,
                name="ro.bootmode",
            )
            or cls._adb_getprop(
                adb=adb,
                serial=serial,
                name="ro.boot.mode",
            )
            or ""
        ).lower()

        if "recovery" in bootmode:
            return (
                AndroidBootImageDeviceMode
                .RECOVERY_ADB
            )

        return (
            AndroidBootImageDeviceMode
            .ANDROID_ADB
        )

    @classmethod
    def _classify_fastboot_mode(
        cls,
        *,
        fastboot: Path,
        serial: str,
    ) -> AndroidBootImageDeviceMode:
        value = cls._getvar(
            fastboot=fastboot,
            serial=serial,
            name="is-userspace",
        )

        if (
            value is not None
            and value.strip().lower()
            in {
                "yes",
                "true",
                "1",
            }
        ):
            return (
                AndroidBootImageDeviceMode
                .FASTBOOTD
            )

        return (
            AndroidBootImageDeviceMode
            .FASTBOOT_BOOTLOADER
        )

    @classmethod
    def _wait_for_fastboot(
        cls,
        *,
        fastboot: Path,
        expected_serial: str,
    ) -> str:
        for _ in range(
            cls.FASTBOOT_DISCOVERY_ATTEMPTS
        ):
            serials = cls._fastboot_serials(
                fastboot
            )

            if not serials:
                time.sleep(
                    cls.FASTBOOT_DISCOVERY_INTERVAL_SECONDS
                )
                continue

            if len(serials) != 1:
                raise RuntimeError(
                    "Device Deployment requires exactly one "
                    "fastboot device after transition; "
                    f"found {len(serials)}"
                )

            serial = serials[0]

            if serial != expected_serial:
                raise RuntimeError(
                    "device serial changed across transport "
                    "transition; exact hardware identity cannot "
                    "be proven: "
                    f"{expected_serial!r} -> {serial!r}"
                )

            return serial

        raise RuntimeError(
            "device did not become available in fastboot "
            "after mode transition"
        )

    @classmethod
    def has_connected_device(
        cls,
    ) -> bool:
        """
        Perform a read-only transport probe.

        This does not reboot the device, change modes, query slots, or
        perform any hardware mutation.
        """

        fastboot = cls._executable(
            "fastboot",
            required=False,
        )

        if fastboot is not None:
            serials = cls._fastboot_serials(
                fastboot
            )

            if len(serials) > 1:
                raise RuntimeError(
                    "Boot Image Device Deployment found multiple "
                    "fastboot devices; exactly one device is required"
                )

            if serials:
                return True

        adb = cls._executable(
            "adb",
            required=False,
        )

        if adb is not None:
            serials = cls._adb_serials(
                adb
            )

            if len(serials) > 1:
                raise RuntimeError(
                    "Boot Image Device Deployment found multiple "
                    "ADB devices; exactly one device is required"
                )

            if serials:
                return True

        return False


    @classmethod
    def _prepare_bootloader_fastboot(
        cls,
    ) -> tuple[
        Path | None,
        Path,
        AndroidBootImageFastbootDevice,
    ]:
        fastboot = cls._executable(
            "fastboot",
            required=True,
        )

        assert fastboot is not None

        adb = cls._executable(
            "adb",
            required=False,
        )

        fastboot_serials = (
            cls._fastboot_serials(
                fastboot
            )
        )

        if len(fastboot_serials) > 1:
            raise RuntimeError(
                "Device Deployment requires exactly one "
                "fastboot device; "
                f"found {len(fastboot_serials)}"
            )

        if fastboot_serials:
            serial = fastboot_serials[0]

            initial_mode = (
                cls._classify_fastboot_mode(
                    fastboot=fastboot,
                    serial=serial,
                )
            )

            if (
                initial_mode
                is
                AndroidBootImageDeviceMode.FASTBOOTD
            ):
                completed = cls._run(
                    (
                        str(fastboot),
                        "-s",
                        serial,
                        "reboot",
                        "bootloader",
                    )
                )

                if completed.returncode != 0:
                    raise RuntimeError(
                        "failed to transition fastbootd "
                        "to bootloader fastboot: "
                        + (
                            completed.stderr
                            + b"\n"
                            + completed.stdout
                        ).decode(
                            "utf-8",
                            errors="replace",
                        )
                    )

                serial = cls._wait_for_fastboot(
                    fastboot=fastboot,
                    expected_serial=serial,
                )

                final_mode = (
                    cls._classify_fastboot_mode(
                        fastboot=fastboot,
                        serial=serial,
                    )
                )

                if (
                    final_mode
                    is not
                    AndroidBootImageDeviceMode
                    .FASTBOOT_BOOTLOADER
                ):
                    raise RuntimeError(
                        "device remained in userspace fastboot "
                        "after bootloader transition"
                    )

            else:
                final_mode = initial_mode

        else:
            if adb is None:
                raise RuntimeError(
                    "no fastboot device is connected and "
                    "adb is unavailable"
                )

            adb_serials = cls._adb_serials(
                adb
            )

            if len(adb_serials) != 1:
                raise RuntimeError(
                    "Device Deployment requires exactly one "
                    "ADB device when no fastboot device exists; "
                    f"found {len(adb_serials)}"
                )

            serial = adb_serials[0]

            initial_mode = (
                cls._classify_adb_mode(
                    adb=adb,
                    serial=serial,
                )
            )

            completed = cls._run(
                (
                    str(adb),
                    "-s",
                    serial,
                    "reboot",
                    "bootloader",
                )
            )

            if completed.returncode != 0:
                raise RuntimeError(
                    "failed to reboot ADB device into bootloader: "
                    + (
                        completed.stderr
                        + b"\n"
                        + completed.stdout
                    ).decode(
                        "utf-8",
                        errors="replace",
                    )
                )

            serial = cls._wait_for_fastboot(
                fastboot=fastboot,
                expected_serial=serial,
            )

            final_mode = (
                cls._classify_fastboot_mode(
                    fastboot=fastboot,
                    serial=serial,
                )
            )

            if (
                final_mode
                is not
                AndroidBootImageDeviceMode
                .FASTBOOT_BOOTLOADER
            ):
                raise RuntimeError(
                    "ADB reboot did not produce "
                    "bootloader fastboot"
                )

        #
        # Authoritative slot state is read only after the final
        # transport transition.
        #
        current_slot = cls._getvar(
            fastboot=fastboot,
            serial=serial,
            name="current-slot",
        )

        if (
            current_slot is not None
            and current_slot not in {
                "a",
                "b",
            }
        ):
            raise RuntimeError(
                "unsupported fastboot current-slot value: "
                f"{current_slot!r}"
            )

        slot_count_raw = cls._getvar(
            fastboot=fastboot,
            serial=serial,
            name="slot-count",
        )

        slot_count = None

        if slot_count_raw is not None:
            try:
                slot_count = int(
                    slot_count_raw,
                    10,
                )
            except ValueError as error:
                raise RuntimeError(
                    "fastboot returned non-integer slot-count: "
                    f"{slot_count_raw!r}"
                ) from error

        return (
            adb,
            fastboot,
            AndroidBootImageFastbootDevice(
                serial=serial,
                initial_mode=initial_mode,
                final_mode=final_mode,
                current_slot=current_slot,
                slot_count=slot_count,
            ),
        )

    @classmethod
    def inspect(
        cls,
        deployment: (
        AndroidBootImageDeploymentPlan
        | AndroidBootImageReusableDeployment
        | AndroidBootImageBaseDeployment
    ),
    ) -> AndroidBootImageDeviceInspection:
        if not isinstance(
            deployment,
            (
                AndroidBootImageDeploymentPlan,
                AndroidBootImageReusableDeployment,
                AndroidBootImageBaseDeployment,
            ),
        ):
            raise TypeError(
                "deployment must be an AndroidBootImageDeploymentPlan"
            )

        if not deployment.images:
            raise RuntimeError(
                "Boot Image Device Deployment has no images "
                "available for deployment"
            )

        adb, fastboot, device = (
            cls._prepare_bootloader_fastboot()
        )

        slot_applicability = []

        for image in deployment.images:
            value = cls._getvar(
                fastboot=fastboot,
                serial=device.serial,
                name=(
                    "has-slot:"
                    f"{image.partition_name}"
                ),
            )

            if value is None:
                raise RuntimeError(
                    "fastboot did not report slot applicability "
                    "for partition "
                    f"{image.partition_name!r}"
                )

            normalized = value.strip().lower()

            if normalized in {
                "yes",
                "true",
                "1",
            }:
                slot_applicable = True

            elif normalized in {
                "no",
                "false",
                "0",
            }:
                slot_applicable = False

            else:
                raise RuntimeError(
                    "unsupported has-slot response for "
                    f"{image.partition_name}: {value!r}"
                )

            slot_applicability.append(
                (
                    image,
                    slot_applicable,
                )
            )

        inspection = (
            AndroidBootImageDeviceInspection(
                deployment=deployment,
                adb_path=adb,
                fastboot_path=fastboot,
                device=device,
                slot_applicability=tuple(
                    slot_applicability
                ),
            )
        )

        if inspection.has_slotted_targets:
            if inspection.active_slot is None:
                raise RuntimeError(
                    "slotted deployment requires "
                    "current-slot evidence"
                )

            if device.slot_count != 2:
                raise RuntimeError(
                    "active/inactive deployment currently "
                    "requires exactly two slots; "
                    f"reported slot-count={device.slot_count!r}"
                )

            if inspection.inactive_slot is None:
                raise RuntimeError(
                    "inactive slot could not be derived"
                )

        return inspection

    @classmethod
    def plan(
        cls,
        inspection: AndroidBootImageDeviceInspection,
        *,
        payload: AndroidBootImageDeploymentPayload,
        slot_selection: (
            AndroidBootImageSlotSelection
            | None
        ),
    ) -> AndroidBootImageDeviceDeploymentPlan:
        if not isinstance(
            inspection,
            AndroidBootImageDeviceInspection,
        ):
            raise TypeError(
                "inspection must be an "
                "AndroidBootImageDeviceInspection"
            )

        if not isinstance(
            payload,
            AndroidBootImageDeploymentPayload,
        ):
            raise TypeError(
                "payload must be an "
                "AndroidBootImageDeploymentPayload"
            )

        if inspection.has_slotted_targets:
            if not isinstance(
                slot_selection,
                AndroidBootImageSlotSelection,
            ):
                raise ValueError(
                    "slotted deployment requires explicit "
                    "slot selection"
                )

            selected_slot = (
                slot_selection.value
            )

            if selected_slot not in {
                "a",
                "b",
            }:
                raise RuntimeError(
                    "selected slot is unavailable"
                )

        else:
            if slot_selection is not None:
                raise ValueError(
                    "non-slotted deployment cannot retain "
                    "slot selection"
                )

            selected_slot = None

        targets = []

        for (
            image,
            slot_applicable,
        ) in inspection.slot_applicability:
            if slot_applicable:
                assert selected_slot is not None

                target_slot = selected_slot

                fastboot_partition = (
                    f"{image.partition_name}_"
                    f"{target_slot}"
                )

            else:
                target_slot = None
                fastboot_partition = (
                    image.partition_name
                )

            targets.append(
                AndroidBootImageDeviceDeploymentTarget(
                    image=image,
                    partition_name=(
                        image.partition_name
                    ),
                    slot_applicable=(
                        slot_applicable
                    ),
                    target_slot=target_slot,
                    fastboot_partition=(
                        fastboot_partition
                    ),
                )
            )

        return AndroidBootImageDeviceDeploymentPlan(
            inspection=inspection,
            payload=payload,
            slot_selection=slot_selection,
            targets=tuple(targets),
        )

    @classmethod
    def flash(
        cls,
        plan: AndroidBootImageDeviceDeploymentPlan,
    ) -> AndroidBootImageDeviceDeploymentResult:
        if not isinstance(
            plan,
            AndroidBootImageDeviceDeploymentPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidBootImageDeviceDeploymentPlan"
            )

        #
        # Re-read slot state immediately before any write.
        #
        fresh_current_slot = cls._getvar(
            fastboot=plan.fastboot_path,
            serial=plan.device.serial,
            name="current-slot",
        )

        if (
            fresh_current_slot
            != plan.device.current_slot
        ):
            raise RuntimeError(
                "device current slot changed after inspection: "
                f"{plan.device.current_slot!r} -> "
                f"{fresh_current_slot!r}"
            )

        invocations = []

        for target in plan.targets:
            image = target.image

            if (
                plan.payload
                is
                AndroidBootImageDeploymentPayload.MODIFIED
            ):
                source_path = (
                    image.final_path
                )
                expected_size = (
                    image.final_size_bytes
                )
                expected_digest = (
                    image.final_sha256
                )

                #
                # Original bytes must still be available and valid
                # before a modified hardware write is allowed.
                #
                (
                    original_size,
                    original_digest,
                ) = cls._file_identity(
                    image.rollback_path
                )

                if (
                    original_size
                    != image.rollback_size_bytes
                    or original_digest
                    != image.rollback_sha256
                ):
                    raise RuntimeError(
                        "original image failed pre-flash "
                        "identity verification: "
                        f"{image.partition_name}"
                    )

            else:
                source_path = (
                    image.rollback_path
                )
                expected_size = (
                    image.rollback_size_bytes
                )
                expected_digest = (
                    image.rollback_sha256
                )

            actual_size, actual_digest = (
                cls._file_identity(
                    source_path
                )
            )

            if (
                actual_size != expected_size
                or actual_digest != expected_digest
            ):
                raise RuntimeError(
                    "selected deployment image changed "
                    "after Deployment Planning: "
                    f"{image.partition_name}"
                )

            command = (
                str(plan.fastboot_path),
                "-s",
                plan.device.serial,
                "flash",
                target.fastboot_partition,
                str(source_path),
            )

            completed = cls._run(command)

            if completed.returncode != 0:
                raise RuntimeError(
                    "fastboot flash failed for "
                    f"{target.fastboot_partition}: "
                    + (
                        completed.stderr
                        + b"\n"
                        + completed.stdout
                    ).decode(
                        "utf-8",
                        errors="replace",
                    )
                )

            invocations.append(
                AndroidBootImageFlashInvocation(
                    target=target,
                    payload=plan.payload,
                    command=command,
                    returncode=(
                        completed.returncode
                    ),
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
            )

        return AndroidBootImageDeviceDeploymentResult(
            plan=plan,
            invocations=tuple(invocations),
        )

    @classmethod
    def reboot(
        cls,
        plan: AndroidBootImageDeviceDeploymentPlan,
    ) -> None:
        """
        Reboot the exact fastboot device associated with a completed
        deployment plan.

        This operation is never automatic. The CLI must obtain explicit
        user confirmation after all planned writes have succeeded.
        """
        if not isinstance(
            plan,
            AndroidBootImageDeviceDeploymentPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidBootImageDeviceDeploymentPlan"
            )

        command = (
            str(
                plan.fastboot_path
            ),
            "-s",
            plan.device.serial,
            "reboot",
        )

        completed = cls._run(
            command
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "fastboot reboot failed: "
                + (
                    completed.stderr
                    + b"\n"
                    + completed.stdout
                ).decode(
                    "utf-8",
                    errors="replace",
                )
            )


    @classmethod
    def restore_original(
        cls,
        plan: AndroidBootImageDeviceDeploymentPlan,
    ) -> AndroidBootImageDeviceDeploymentResult:
        """
        Explicit same-target restoration of the exact canonical originals.

        This is available after a modified deployment but is never invoked
        automatically.
        """

        original_plan = (
            AndroidBootImageDeviceDeploymentPlan(
                inspection=plan.inspection,
                payload=(
                    AndroidBootImageDeploymentPayload
                    .ORIGINAL
                ),
                slot_selection=(
                    plan.slot_selection
                ),
                targets=plan.targets,
            )
        )

        return cls.flash(
            original_plan
        )


__all__ = (
    "AndroidBootImageDeviceMode",
    "AndroidBootImageSlotSelection",
    "AndroidBootImageDeploymentPayload",
    "AndroidBootImageFastbootDevice",
    "AndroidBootImageDeviceInspection",
    "AndroidBootImageDeviceDeploymentTarget",
    "AndroidBootImageDeviceDeploymentPlan",
    "AndroidBootImageFlashInvocation",
    "AndroidBootImageDeviceDeploymentResult",
    "AndroidBootImageDeviceDeployer",
)
