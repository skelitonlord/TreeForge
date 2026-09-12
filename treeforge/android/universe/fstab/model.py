from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.fstab import (
    AndroidFstabDeclaration,
)
from treeforge.android.universe.fstab.semantics import (
    AndroidUniverseFstabDeviceExpression,
    AndroidUniverseMountOption,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFstabRequirement:
    """
    One semantic device requirement derived from an Android fstab declaration.

    The complete lexical declaration and its source identities are retained
    so Universe interpretation never destroys Parsing evidence.

    No attempt is made here to decide whether requirements from different
    fstab sources are simultaneous, alternative, variant-specific, or
    conflicting. That is a separate Universe reconciliation concern.
    """

    source_path: Path
    android_path: PurePosixPath | None
    source_name: str
    declaration: AndroidFstabDeclaration

    device: str
    mount_point: str
    filesystem_type: str

    mount_options: tuple[
        str,
        ...,
    ]

    fs_mgr_flags: tuple[
        str,
        ...,
    ]

    device_expression: (
        AndroidUniverseFstabDeviceExpression
    )

    interpreted_mount_options: tuple[
        AndroidUniverseMountOption,
        ...,
    ]

    logical: bool = False
    slot_select: bool = False
    slot_select_other: bool = False
    first_stage_mount: bool = False
    late_mount: bool = False
    wait: bool = False
    check: bool = False
    formattable: bool = False
    quota: bool = False

    avb: str | None = None
    avb_keys: str | None = None
    avb_hashtree_digest: str | None = None

    file_encryption: str | None = None
    metadata_encryption: str | None = None
    key_directory: str | None = None

    checkpoint: str | None = None

    vold_managed: str | None = None

    zram_size: str | None = None
    zram_backing_device_size: str | None = None

    filesystem_compression: bool = False
    metadata_checksum: bool = False

    readahead_size_kb: str | None = None
    reserved_size: str | None = None
    sysfs_path: str | None = None

    unknown_fs_mgr_flags: tuple[
        str,
        ...,
    ] = ()

    @property
    def requirement_id(
        self,
    ) -> str:
        """
        Return deterministic Universe-local identity for this observation.

        Source identity and declaration line are included deliberately:
        distinct alternatives must never collapse merely because they share
        a mount point or partition.
        """

        android_path = (
            self.android_path.as_posix()
            if self.android_path is not None
            else self.source_path.as_posix()
        )

        return (
            f"fstab:{self.source_name}:{android_path}:"
            f"{self.declaration.line_number}"
        )

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

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if not isinstance(
            self.declaration,
            AndroidFstabDeclaration,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidFstabDeclaration"
            )

        for field_name, value in (
            ("device", self.device),
            ("mount_point", self.mount_point),
            ("filesystem_type", self.filesystem_type),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.device_expression,
            AndroidUniverseFstabDeviceExpression,
        ):
            raise TypeError(
                "device_expression must be an "
                "AndroidUniverseFstabDeviceExpression"
            )

        if not isinstance(
            self.interpreted_mount_options,
            tuple,
        ):
            raise TypeError(
                "interpreted_mount_options must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseMountOption,
            )
            for item in self.interpreted_mount_options
        ):
            raise TypeError(
                "interpreted_mount_options must contain only "
                "AndroidUniverseMountOption instances"
            )

        if (
            tuple(
                item.raw_value
                for item in self.interpreted_mount_options
            )
            != self.mount_options
        ):
            raise ValueError(
                "interpreted_mount_options must preserve "
                "mount_options exactly"
            )

        for field_name, value in (
            (
                "mount_options",
                self.mount_options,
            ),
            (
                "fs_mgr_flags",
                self.fs_mgr_flags,
            ),
            (
                "unknown_fs_mgr_flags",
                self.unknown_fs_mgr_flags,
            ),
        ):
            if not isinstance(
                value,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    item,
                    str,
                )
                for item in value
            ):
                raise TypeError(
                    f"{field_name} must contain only strings"
                )