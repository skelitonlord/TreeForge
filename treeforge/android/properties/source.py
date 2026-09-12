from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath


class AndroidPropertySourceKind(
    StrEnum
):
    """
    Generic Android property-source categories.

    These categories describe the lexical source form only. They do not
    interpret property values, assign build ownership, or perform
    reconstruction policy.
    """

    BUILD = "build"
    DEFAULT = "default"
    GENERIC = "generic"


def classify_android_property_source(
    android_path: str,
) -> AndroidPropertySourceKind | None:
    """
    Classify an already-discovered Android property source.

    Classification is intentionally independent of Android version, device,
    partition, SoC, and OEM.

    ``build.prop`` is the conventional partition build-property source.
    ``default.prop`` and ``prop.default`` are default-property sources.
    Other ``*.prop`` files remain valid generic Android property sources
    without being incorrectly promoted into either semantic category.
    """

    if not isinstance(
        android_path,
        str,
    ):
        raise TypeError(
            "android_path must be a string"
        )

    if not android_path:
        return None

    filename = PurePosixPath(
        android_path
    ).name

    if filename == "build.prop":
        return AndroidPropertySourceKind.BUILD

    if filename in {
        "default.prop",
        "prop.default",
    }:
        return AndroidPropertySourceKind.DEFAULT

    if filename.endswith(
        ".prop"
    ):
        return AndroidPropertySourceKind.GENERIC

    return None


def is_android_property_source(
    android_path: str,
) -> bool:
    """
    Return whether an already-discovered path names an Android property
    source.
    """

    return (
        classify_android_property_source(
            android_path
        )
        is not None
    )