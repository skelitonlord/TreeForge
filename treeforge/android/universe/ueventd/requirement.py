from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.ueventd import (
    AndroidUeventdDeclaration,
    AndroidUeventdDeviceRule,
    AndroidUeventdFirmwareDirectories,
    AndroidUeventdImport,
    AndroidUeventdSocketRcvbufSize,
    AndroidUeventdSubsystem,
    AndroidUeventdSysfsRule,
)
from treeforge.android.universe.ueventd.semantics import (
    AndroidUniverseUeventdPathSemantics,
    AndroidUniverseUeventdPermissionSemantics,
    AndroidUniverseUeventdSocketBufferSemantics,
    AndroidUniverseUeventdSubsystemOptionSemantics,
)


def _source_identity(
    source_name: str,
    source_path: Path,
    android_path: PurePosixPath | None,
) -> str:
    path_identity = (
        android_path.as_posix()
        if android_path is not None
        else source_path.as_posix()
    )

    return (
        f"{source_name}::{path_identity}"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdImportRequirement:
    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidUeventdImport

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "ueventd-import:"
            f"{_source_identity(self.source_name, self.source_path, self.android_path)}:"
            f"{self.declaration.source_line}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdDeviceRuleRequirement:
    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidUeventdDeviceRule

    path_semantics: AndroidUniverseUeventdPathSemantics
    permission_semantics: AndroidUniverseUeventdPermissionSemantics

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "ueventd-device:"
            f"{_source_identity(self.source_name, self.source_path, self.android_path)}:"
            f"{self.declaration.source_line}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdSysfsRuleRequirement:
    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidUeventdSysfsRule

    path_semantics: AndroidUniverseUeventdPathSemantics
    permission_semantics: AndroidUniverseUeventdPermissionSemantics

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "ueventd-sysfs:"
            f"{_source_identity(self.source_name, self.source_path, self.android_path)}:"
            f"{self.declaration.source_line}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdSubsystemRequirement:
    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidUeventdSubsystem

    option_semantics: tuple[
        AndroidUniverseUeventdSubsystemOptionSemantics,
        ...,
    ]

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "ueventd-subsystem:"
            f"{_source_identity(self.source_name, self.source_path, self.android_path)}:"
            f"{self.declaration.source_line}"
        )

    @property
    def uninterpreted_options(
        self,
    ) -> tuple[
        AndroidUniverseUeventdSubsystemOptionSemantics,
        ...,
    ]:
        return tuple(
            option
            for option in self.option_semantics
            if not option.interpreted
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdFirmwareDirectoriesRequirement:
    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidUeventdFirmwareDirectories

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "ueventd-firmware-directories:"
            f"{_source_identity(self.source_name, self.source_path, self.android_path)}:"
            f"{self.declaration.source_line}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdSocketRcvbufRequirement:
    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidUeventdSocketRcvbufSize

    semantics: AndroidUniverseUeventdSocketBufferSemantics

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "ueventd-socket-rcvbuf:"
            f"{_source_identity(self.source_name, self.source_path, self.android_path)}:"
            f"{self.declaration.source_line}"
        )


AndroidUniverseUeventdRequirement = (
    AndroidUniverseUeventdImportRequirement
    | AndroidUniverseUeventdDeviceRuleRequirement
    | AndroidUniverseUeventdSysfsRuleRequirement
    | AndroidUniverseUeventdSubsystemRequirement
    | AndroidUniverseUeventdFirmwareDirectoriesRequirement
    | AndroidUniverseUeventdSocketRcvbufRequirement
)


def declaration_for_requirement(
    requirement: AndroidUniverseUeventdRequirement,
) -> AndroidUeventdDeclaration:
    return requirement.declaration