from __future__ import annotations

import struct


def read_uint32_le(
    data: bytes,
    offset: int,
) -> int:
    """
    Read one little-endian unsigned 32-bit integer from a byte sequence.
    """

    _validate_data(
        data
    )

    _validate_offset(
        offset
    )

    end = (
        offset
        + 4
    )

    if end > len(
        data
    ):
        raise ValueError(
            "uint32 field extends beyond available data: "
            f"offset={offset}, "
            f"available={len(data)}"
        )

    return struct.unpack_from(
        "<I",
        data,
        offset,
    )[0]


def read_uint64_le(
    data: bytes,
    offset: int,
) -> int:
    """
    Read one little-endian unsigned 64-bit integer from a byte sequence.
    """

    _validate_data(
        data
    )

    _validate_offset(
        offset
    )

    end = (
        offset
        + 8
    )

    if end > len(
        data
    ):
        raise ValueError(
            "uint64 field extends beyond available data: "
            f"offset={offset}, "
            f"available={len(data)}"
        )

    return struct.unpack_from(
        "<Q",
        data,
        offset,
    )[0]


def read_c_string(
    data: bytes,
    offset: int,
    size: int,
    *,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> str:
    """
    Read one fixed-width null-terminated string from a byte sequence.
    """

    _validate_data(
        data
    )

    _validate_offset(
        offset
    )

    if (
        isinstance(
            size,
            bool,
        )
        or not isinstance(
            size,
            int,
        )
    ):
        raise TypeError(
            "size must be an integer"
        )

    if size < 0:
        raise ValueError(
            "size must be non-negative"
        )

    if not isinstance(
        encoding,
        str,
    ):
        raise TypeError(
            "encoding must be a string"
        )

    if not encoding:
        raise ValueError(
            "encoding must not be empty"
        )

    if not isinstance(
        errors,
        str,
    ):
        raise TypeError(
            "errors must be a string"
        )

    if not errors:
        raise ValueError(
            "errors must not be empty"
        )

    end = (
        offset
        + size
    )

    if end > len(
        data
    ):
        raise ValueError(
            "string field extends beyond available data: "
            f"offset={offset}, "
            f"size={size}, "
            f"available={len(data)}"
        )

    raw = data[
        offset:end
    ]

    value = raw.split(
        b"\x00",
        1,
    )[0]

    return value.decode(
        encoding,
        errors=errors,
    )


def align_up(
    value: int,
    alignment: int,
) -> int:
    """
    Align one non-negative integer upward to a positive byte boundary.
    """

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise TypeError(
            "value must be an integer"
        )

    if (
        isinstance(
            alignment,
            bool,
        )
        or not isinstance(
            alignment,
            int,
        )
    ):
        raise TypeError(
            "alignment must be an integer"
        )

    if value < 0:
        raise ValueError(
            "value must be non-negative"
        )

    if alignment <= 0:
        raise ValueError(
            "alignment must be greater than zero"
        )

    return (
        (
            value
            + alignment
            - 1
        )
        // alignment
    ) * alignment


def _validate_data(
    data: bytes,
) -> None:
    if not isinstance(
        data,
        bytes,
    ):
        raise TypeError(
            "data must be bytes"
        )


def _validate_offset(
    offset: int,
) -> None:
    if (
        isinstance(
            offset,
            bool,
        )
        or not isinstance(
            offset,
            int,
        )
    ):
        raise TypeError(
            "offset must be an integer"
        )

    if offset < 0:
        raise ValueError(
            "offset must be non-negative"
        )