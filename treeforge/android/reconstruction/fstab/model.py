from __future__ import annotations

from treeforge.android.universe.fstab.source_context import (
    AndroidUniverseFstabSourceContext,
)

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.fstab.model import (
    AndroidUniverseFstabRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionFstabSourceRepresentation:
    """
    Canonical semantic Reconstruction representation of one fstab source.

    Android Device Universe already owns lexical interpretation, intrinsic
    fstab semantics, and applicability. Reconstruction groups only the exact
    admitted ACTIVE requirements that share one canonical source identity.

    Every work item retains its exact Universe requirement, including the
    parsed declaration, device expression, mount options, fs_mgr flags,
    interpreted semantics, unknown vocabulary, and provenance.

    This representation does not choose a new filename, source-tree
    destination, ownership domain, rendered text, or Device Tree
    materialization strategy.
    """

    source_identity: tuple[
        str,
        str,
    ]

    source_path: Path
    android_path: PurePosixPath | None

    source_context: AndroidUniverseFstabSourceContext

    entry_work_items: tuple[
        AndroidReconstructionWorkItem,
        ...,
    ]

    @property
    def source_identity_key(
        self,
    ) -> str:
        (
            source_name,
            path_identity,
        ) = self.source_identity

        return (
            f"{source_name}::"
            f"{path_identity}"
        )

    @property
    def representation_id(self) -> str:
        return (
            "fstab-source:"
            f"{self.source_identity_key}"
        )

    @property
    def contributing_obligation_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            item.obligation_id
            for item in self.entry_work_items
        )

    @property
    def requirements(
        self,
    ) -> tuple[
        AndroidUniverseFstabRequirement,
        ...,
    ]:
        return tuple(
            item.obligation.requirement
            for item in self.entry_work_items
        )

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
                "source_identity must be the canonical "
                "(source_name, path_identity) tuple"
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
            self.source_context,
            AndroidUniverseFstabSourceContext,
        ):
            raise TypeError(
                "source_context must be an "
                "AndroidUniverseFstabSourceContext"
            )

        if (
            self.source_context.source_identity
            != self.source_identity
        ):
            raise ValueError(
                "source_context must preserve the exact canonical "
                "fstab source identity"
            )

        if (
            self.source_context.source_path
            != self.source_path
            or self.source_context.android_path
            != self.android_path
        ):
            raise ValueError(
                "source_context path identities must match the "
                "fstab Reconstruction representation"
            )

        if not isinstance(
            self.entry_work_items,
            tuple,
        ):
            raise TypeError(
                "entry_work_items must be a tuple"
            )

        if not self.entry_work_items:
            raise ValueError(
                "fstab source representation requires at least "
                "one Reconstruction work item"
            )

        for item in self.entry_work_items:
            if not isinstance(
                item,
                AndroidReconstructionWorkItem,
            ):
                raise TypeError(
                    "entry_work_items must contain only "
                    "AndroidReconstructionWorkItem instances"
                )

            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.RECONSTRUCT
            ):
                raise ValueError(
                    "fstab source representation may contain "
                    "only RECONSTRUCT work"
                )

            if (
                item.requirement_kind
                != "fstab"
            ):
                raise ValueError(
                    "fstab source representation may contain "
                    "only fstab work"
                )

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseFstabRequirement,
            ):
                raise TypeError(
                    "fstab Reconstruction work must preserve an "
                    "AndroidUniverseFstabRequirement"
                )

            if (
                item.source_identity
                != requirement.requirement_id
            ):
                raise ValueError(
                    "fstab work item source identity must preserve "
                    "the canonical requirement identity"
                )

            requirement_path_identity = (
                requirement.android_path.as_posix()
                if requirement.android_path is not None
                else requirement.source_path.as_posix()
            )

            requirement_source_identity = (
                requirement.source_name,
                requirement_path_identity,
            )

            if (
                requirement_source_identity
                != self.source_identity
            ):
                raise ValueError(
                    "all fstab entries in one representation "
                    "must share one canonical source identity"
                )

            if (
                requirement.source_path
                != self.source_path
            ):
                raise ValueError(
                    "all fstab entries in one representation "
                    "must preserve the same source_path"
                )

            if (
                requirement.android_path
                != self.android_path
            ):
                raise ValueError(
                    "all fstab entries in one representation "
                    "must preserve the same android_path"
                )

        obligation_ids = (
            self.contributing_obligation_ids
        )

        if len(
            obligation_ids
        ) != len(
            set(obligation_ids)
        ):
            raise ValueError(
                "fstab source representation contains duplicate "
                "Reconstruction work identities"
            )
