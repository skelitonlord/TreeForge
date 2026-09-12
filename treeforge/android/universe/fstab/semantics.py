from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath


class AndroidUniverseFstabDeviceKind(
    str,
    Enum,
):
    LOGICAL_PARTITION = "logical_partition"
    BLOCK_DEVICE = "block_device"
    ZRAM = "zram"
    DEVICE_PATTERN = "device_pattern"
    OTHER = "other"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFstabDeviceExpression:
    """
    Semantic interpretation of one fstab source/device expression.

    raw_value is always retained. Classification adds meaning without
    replacing the original Parsing observation.
    """

    raw_value: str
    kind: AndroidUniverseFstabDeviceKind

    partition_name: str | None = None
    block_device_path: PurePosixPath | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.raw_value,
            str,
        ):
            raise TypeError(
                "raw_value must be a string"
            )

        if not self.raw_value:
            raise ValueError(
                "raw_value must not be empty"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseFstabDeviceKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseFstabDeviceKind"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseMountOption:
    """
    Structured interpretation of one lexical mount option.

    Bare options have value=None. Parameterized options preserve the
    substring after the first '=' exactly.
    """

    raw_value: str
    name: str
    value: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.raw_value,
            str,
        ):
            raise TypeError(
                "raw_value must be a string"
            )

        if not self.raw_value:
            raise ValueError(
                "raw_value must not be empty"
            )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name must not be empty"
            )