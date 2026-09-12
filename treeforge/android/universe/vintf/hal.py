from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.vintf import (
    VintfXmlElement,
)


class AndroidUniverseVintfHalFormat(
    StrEnum
):
    AIDL = "aidl"
    HIDL = "hidl"
    NATIVE = "native"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfHalTransport:
    """
    One semantic VINTF HAL transport declaration.

    ``element`` preserves exact Parsing identity.
    """

    kind: str
    arch: str | None

    element: VintfXmlElement


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfHalInterface:
    """
    One HAL interface declaration.

    ``name`` is optional because real VINTF compatibility data may contain
    interface declarations consisting only of regex-instance constraints.

    Exact and regex instances remain distinct because their matching
    semantics differ.
    """

    name: str | None

    instances: tuple[
        str,
        ...,
    ] = ()

    regex_instances: tuple[
        str,
        ...,
    ] = ()

    element: VintfXmlElement | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfHalRequirement:
    """
    Complete semantic interpretation of one VINTF HAL declaration.

    Repeated versions, interfaces, fqnames, transports, and all audited
    declaration attributes remain lossless.
    """

    name: str
    format: AndroidUniverseVintfHalFormat

    versions: tuple[
        str,
        ...,
    ] = ()

    interfaces: tuple[
        AndroidUniverseVintfHalInterface,
        ...,
    ] = ()

    fqnames: tuple[
        str,
        ...,
    ] = ()

    transports: tuple[
        AndroidUniverseVintfHalTransport,
        ...,
    ] = ()

    optional: bool | None = None

    min_level: str | None = None
    max_level: str | None = None

    updatable_via_apex: bool | None = None

    element: VintfXmlElement | None = None