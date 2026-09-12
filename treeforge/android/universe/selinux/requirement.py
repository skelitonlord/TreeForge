from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidSelinuxSource,
)
from treeforge.android.parsing.selinux import (
    AndroidSelinuxSourceKind,
)
from treeforge.android.universe.selinux.cil import (
    AndroidUniverseSelinuxCilRequirement,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextRequirement,
    AndroidUniverseSelinuxSeappRequirement,
)
from treeforge.android.universe.selinux.mac_permissions import (
    AndroidUniverseSelinuxMacPermissionsRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxSourceRequirement:
    """
    Canonical Universe representation of one parsed SELinux source.

    The exact ParsedAndroidSelinuxSource identity remains attached so all host
    path, Android path, raw-byte, parser and Extraction provenance survives
    promotion into Universe.
    """

    source: ParsedAndroidSelinuxSource

    context_requirements: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ] = ()

    seapp_requirements: tuple[
        AndroidUniverseSelinuxSeappRequirement,
        ...,
    ] = ()

    mac_permissions_requirements: tuple[
        AndroidUniverseSelinuxMacPermissionsRequirement,
        ...,
    ] = ()

    cil_requirements: tuple[
        AndroidUniverseSelinuxCilRequirement,
        ...,
    ] = ()

    @property
    def source_path(
        self,
    ) -> Path:
        return self.source.source_path

    @property
    def android_path(
        self,
    ) -> Path | None:
        return self.source.android_path

    @property
    def kind(
        self,
    ) -> AndroidSelinuxSourceKind:
        return self.source.parsed.kind

    @property
    def parsed(
        self,
    ):
        return self.source.parsed

    @property
    def genfs_labels_version(
        self,
    ) -> str | None:
        """
        Return the parsed genfs labels version observation.

        No source file is reread here. Exact Parsing identity and provenance
        remain attached through ``source``.
        """

        return self.parsed.genfs_labels_version


    @property
    def requirement_id(
        self,
    ) -> str:
        """
        Return the canonical identity for this exact SELinux source.

        ``source_path`` identifies the exact parsed/materialized source.
        ``android_path`` is retained separately as Android-visible identity
        and must not collapse distinct canonical sources that happen to map
        to the same Android pathname.
        """

        return (
            "selinux-source:"
            f"{self.source_path.as_posix()}:"
            f"{self.kind.value}"
        )

    @property
    def uninterpreted_cil_requirements(
        self,
    ) -> tuple[
        AndroidUniverseSelinuxCilRequirement,
        ...,
    ]:
        return tuple(
            requirement
            for requirement
            in self.cil_requirements
            if not requirement.interpreted
        )

    @property
    def is_compiled_policy(
        self,
    ) -> bool:
        return (
            self.kind
            is AndroidSelinuxSourceKind.COMPILED_POLICY
        )

    @property
    def is_opaque(
        self,
    ) -> bool:
        return self.parsed.is_opaque