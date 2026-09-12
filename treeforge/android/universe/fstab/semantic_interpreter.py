from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.universe.fstab.semantics import (
    AndroidUniverseFstabDeviceExpression,
    AndroidUniverseFstabDeviceKind,
    AndroidUniverseMountOption,
)


class AndroidUniverseFstabSemanticInterpreter:
    """
    Interpret intrinsic fstab device-expression and mount-option semantics.

    Classification is generic and lossless. Unknown/future forms remain
    represented through OTHER while retaining their exact raw value.
    """

    def interpret_device(
        self,
        value: str,
    ) -> AndroidUniverseFstabDeviceExpression:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not value:
            raise ValueError(
                "value must not be empty"
            )

        if value == "/dev/block/zram0":
            return AndroidUniverseFstabDeviceExpression(
                raw_value=value,
                kind=AndroidUniverseFstabDeviceKind.ZRAM,
                block_device_path=PurePosixPath(
                    value
                ),
            )

        if (
            value.startswith(
                "/dev/block/"
            )
        ):
            partition_name = None

            marker = "/by-name/"

            if marker in value:
                candidate = value.rsplit(
                    marker,
                    1,
                )[1]

                if candidate:
                    partition_name = candidate

            return AndroidUniverseFstabDeviceExpression(
                raw_value=value,
                kind=AndroidUniverseFstabDeviceKind.BLOCK_DEVICE,
                partition_name=partition_name,
                block_device_path=PurePosixPath(
                    value
                ),
            )

        if (
            value.startswith(
                "/devices/"
            )
            or "*" in value
            or "?" in value
        ):
            return AndroidUniverseFstabDeviceExpression(
                raw_value=value,
                kind=(
                    AndroidUniverseFstabDeviceKind
                    .DEVICE_PATTERN
                ),
            )

        if "/" not in value:
            return AndroidUniverseFstabDeviceExpression(
                raw_value=value,
                kind=(
                    AndroidUniverseFstabDeviceKind
                    .LOGICAL_PARTITION
                ),
                partition_name=value,
            )

        return AndroidUniverseFstabDeviceExpression(
            raw_value=value,
            kind=AndroidUniverseFstabDeviceKind.OTHER,
        )

    def interpret_mount_options(
        self,
        values: tuple[
            str,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseMountOption,
        ...,
    ]:
        if not isinstance(
            values,
            tuple,
        ):
            raise TypeError(
                "values must be a tuple"
            )

        options = []

        for raw_value in values:
            if not isinstance(
                raw_value,
                str,
            ):
                raise TypeError(
                    "values must contain only strings"
                )

            name, separator, value = (
                raw_value.partition("=")
            )

            options.append(
                AndroidUniverseMountOption(
                    raw_value=raw_value,
                    name=name,
                    value=(
                        value
                        if separator
                        else None
                    ),
                )
            )

        return tuple(
            options
        )