from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.parsing.ueventd import (
    AndroidUeventdSubsystemOption,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdPathSemantics:
    """
    Semantic interpretation of one literal ueventd path expression.

    The original expression remains available unchanged. Universe records
    only generic structural characteristics here; device-specific path
    classification belongs to later reconciliation or downstream consumers.
    """

    expression: str
    has_wildcards: bool


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdPermissionSemantics:
    """
    Canonical permission meaning for one ueventd permission declaration.

    ``literal_mode`` preserves Parsing text while ``mode`` provides its
    normalized numeric value.
    """

    literal_mode: str
    mode: int
    user: str
    group: str


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdSubsystemOptionSemantics:
    """
    Semantic interpretation of one subsystem option.

    The exact parsed option remains attached. Unknown future keywords remain
    explicitly represented with ``interpreted=False`` rather than being
    discarded.
    """

    option: AndroidUeventdSubsystemOption
    interpreted: bool

    devname_strategy: str | None = None
    dirname: PurePosixPath | None = None

    @property
    def keyword(
        self,
    ) -> str:
        return self.option.name

    @property
    def value(
        self,
    ) -> str:
        return self.option.value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseUeventdSocketBufferSemantics:
    """
    Semantic interpretation of uevent_socket_rcvbuf_size.
    """

    literal_size: str
    size_bytes: int