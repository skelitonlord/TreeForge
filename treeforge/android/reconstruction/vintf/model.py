from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionVintfDocumentRepresentation:
    """
    Canonical semantic Reconstruction representation of one VINTF document.

    Android Device Universe already owns VINTF XML interpretation and
    document applicability. Planning admits only the exact canonical ACTIVE
    document requirements that require downstream Reconstruction.

    The exact Universe document requirement remains attached, preserving:
    source and Android path identity, faithful parsed XML identity, document
    kind and side, HAL/kernel/SEPolicy/System-SDK/AVB semantics, and explicit
    uninterpreted XML coverage debt.

    Reconstruction does not split the document into independent HAL/interface
    outputs, re-run applicability or selection, choose a source-tree
    destination, assign ownership, render XML, or materialize Device Tree
    files.
    """

    source_identity: tuple[
        str,
        str,
    ]

    source_path: Path
    android_path: PurePosixPath | None

    work_item: AndroidReconstructionWorkItem

    requirement: AndroidUniverseVintfDocumentRequirement

    @property
    def representation_id(self) -> str:
        return (
            "vintf-document:"
            f"{self.requirement.requirement_id}"
        )

    @property
    def obligation_id(self) -> str:
        return self.work_item.obligation_id

    @property
    def document_kind(self):
        return self.requirement.semantics.kind

    @property
    def document_side(self):
        return self.requirement.semantics.side

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.source_identity,
                tuple,
            )
            or len(
                self.source_identity
            ) != 2
            or not all(
                isinstance(
                    value,
                    str,
                )
                and value
                for value
                in self.source_identity
            )
        ):
            raise TypeError(
                "source_identity must preserve the canonical "
                "Universe VINTF (source_name, path_identity) tuple"
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
                "VINTF representation requires RECONSTRUCT work"
            )

        if (
            self.work_item.requirement_kind
            != "vintf"
        ):
            raise ValueError(
                "VINTF representation requires vintf work"
            )

        if not isinstance(
            self.requirement,
            AndroidUniverseVintfDocumentRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseVintfDocumentRequirement"
            )

        if (
            self.requirement
            is not self.work_item.obligation.requirement
        ):
            raise ValueError(
                "VINTF representation must preserve the exact "
                "canonical Universe requirement identity"
            )

        if (
            self.work_item.source_identity
            != self.requirement.requirement_id
        ):
            raise ValueError(
                "VINTF work item source identity must preserve "
                "the canonical requirement identity"
            )

        expected_source_identity = (
            self.requirement.source_identity
        )

        if (
            self.source_identity
            != expected_source_identity
        ):
            raise ValueError(
                "source_identity must preserve the canonical "
                "Universe VINTF source identity"
            )

        if (
            self.source_path
            != self.requirement.source_path
        ):
            raise ValueError(
                "source_path must preserve the canonical "
                "Universe VINTF source path"
            )

        if (
            self.android_path
            != self.requirement.android_path
        ):
            raise ValueError(
                "android_path must preserve the canonical "
                "Universe VINTF Android path"
            )
