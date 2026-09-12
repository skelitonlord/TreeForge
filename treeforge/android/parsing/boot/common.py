from __future__ import annotations

from pathlib import Path


def validate_image_source(
    image_path: Path,
) -> Path:
    """
    Validate a boot-family image source.
    """

    if not isinstance(
        image_path,
        Path,
    ):
        raise TypeError(
            "image_path must be a Path"
        )

    if not image_path.exists():
        raise FileNotFoundError(
            image_path
        )

    if not image_path.is_file():
        raise IsADirectoryError(
            image_path
        )

    return image_path


def read_image_header(
    image_path: Path,
    *,
    size: int,
    description: str,
) -> bytes:
    """
    Read a fixed-size boot-family image header.
    """

    if (
        isinstance(size, bool)
        or not isinstance(size, int)
    ):
        raise TypeError(
            "size must be an int"
        )

    if size <= 0:
        raise ValueError(
            "size must be greater than zero"
        )

    with image_path.open(
        "rb"
    ) as image:
        header = image.read(
            size
        )

    if len(header) < size:
        raise ValueError(
            f"Incomplete {description} header."
        )

    return header


def validate_image_magic(
    header: bytes,
    *,
    expected: bytes,
    offset: int = 0,
    description: str,
) -> None:
    """
    Validate boot-family image magic without interpreting its format.
    """

    if (
        header[
            offset:
            offset + len(expected)
        ]
        != expected
    ):
        raise ValueError(
            f"Invalid {description}."
        )


def decode_android_os_version(
    value: int,
) -> tuple[
    int,
    int,
    int,
]:
    """
    Decode the Android version tuple from an encoded boot os_version field.
    """

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
    ):
        raise TypeError(
            "value must be an int"
        )

    if value < 0:
        raise ValueError(
            "value cannot be negative"
        )

    major = (
        value >> 25
    ) & 0x7F

    minor = (
        value >> 18
    ) & 0x7F

    patch = (
        value >> 11
    ) & 0x7F

    return (
        major,
        minor,
        patch,
    )
