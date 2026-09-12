from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionSelinuxSourceRepresentation:
    """
    Canonical semantic Reconstruction representation of one SELinux source.

    Android Device Universe already owns SELinux source interpretation,
    cross-source policy reconciliation, policy conclusions, and source
    applicability.

    Each admitted Planning obligation is already one complete canonical
    AndroidUniverseSelinuxSourceRequirement. Reconstruction therefore
    preserves that source boundary exactly.

    The exact Universe requirement retains:
    - exact parsed/materialized source identity,
    - Android-visible path identity,
    - source kind,
    - context declarations,
    - seapp declarations,
    - CIL requirements and semantic classifications,
    - uninterpreted CIL coverage,
    - opaque/compiled-policy state,
    - raw-byte/parser/Extraction provenance.

    Reconstruction does not re-run policy reconciliation, split a source
    into independently owned policy rules, choose a source-tree destination,
    assign ownership, render policy syntax, or materialize Device Tree files.
    """

    source_identity: str

    source_path: Path
    android_path: PurePosixPath | None

    work_item: AndroidReconstructionWorkItem

    requirement: AndroidUniverseSelinuxSourceRequirement

    @property
    def representation_id(self) -> str:
        return (
            "selinux-representation:"
            f"{self.requirement.requirement_id}"
        )

    @property
    def obligation_id(self) -> str:
        return self.work_item.obligation_id

    @property
    def source_kind(self):
        return self.requirement.kind

    @property
    def context_requirements(self):
        return self.requirement.context_requirements

    @property
    def seapp_requirements(self):
        return self.requirement.seapp_requirements

    @property
    def mac_permissions_requirements(self):
        return self.requirement.mac_permissions_requirements

    @property
    def cil_requirements(self):
        return self.requirement.cil_requirements

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_identity,
            str,
        ):
            raise TypeError(
                "source_identity must be a string"
            )

        if not self.source_identity:
            raise ValueError(
                "source_identity must not be empty"
            )

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
            self.work_item,
            AndroidReconstructionWorkItem,
        ):
            raise TypeError(
                "work_item must be an "
                "AndroidReconstructionWorkItem"
            )

        if (
            self.work_item.work_kind
            is not AndroidReconstructionWorkKind.RECONSTRUCT
        ):
            raise ValueError(
                "SELinux representation requires RECONSTRUCT work"
            )

        if (
            self.work_item.requirement_kind
            != "selinux"
        ):
            raise ValueError(
                "SELinux representation requires selinux work"
            )

        if not isinstance(
            self.requirement,
            AndroidUniverseSelinuxSourceRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseSelinuxSourceRequirement"
            )

        if (
            self.requirement
            is not self.work_item.obligation.requirement
        ):
            raise ValueError(
                "SELinux representation must preserve the exact "
                "canonical Universe requirement identity"
            )

        if (
            self.work_item.source_identity
            != self.requirement.requirement_id
        ):
            raise ValueError(
                "SELinux work item source identity must preserve "
                "the canonical Universe requirement identity"
            )

        if (
            self.source_identity
            != self.requirement.requirement_id
        ):
            raise ValueError(
                "source_identity must preserve the canonical "
                "Universe SELinux source requirement identity"
            )

        if (
            self.source_path
            != self.requirement.source_path
        ):
            raise ValueError(
                "source_path must preserve the canonical "
                "Universe SELinux source path"
            )

        if (
            self.android_path
            != self.requirement.android_path
        ):
            raise ValueError(
                "android_path must preserve the canonical "
                "Universe SELinux Android path"
            )
