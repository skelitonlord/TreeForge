from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdRequirement,
)
from treeforge.android.universe.ueventd.source_context import (
    AndroidUniverseUeventdSourceContext,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionUeventdSourceRepresentation:
    """
    Canonical semantic Reconstruction representation of one UEVENTD source.

    Android Device Universe already owns declaration interpretation, import
    resolution, source reachability, semantic-subject reconciliation, and
    effective applicability.

    Reconstruction groups only the exact ACTIVE requirements admitted by
    Planning that share one canonical source identity.

    Mixed UEVENTD declaration kinds remain attached to their exact canonical
    Universe requirements and retain their original source-line ordering.

    This representation does not choose a new filename, source-tree
    destination, ownership domain, rendered text, override policy, or
    Device Tree materialization strategy.
    """

    source_identity: tuple[
        str,
        str,
    ]

    source_path: Path
    android_path: PurePosixPath | None

    source_context: AndroidUniverseUeventdSourceContext

    requirement_work_items: tuple[
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
            "ueventd-source:"
            f"{self.source_identity_key}"
        )

    @property
    def contributing_obligation_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            item.obligation_id
            for item in self.requirement_work_items
        )

    @property
    def requirements(
        self,
    ) -> tuple[
        AndroidUniverseUeventdRequirement,
        ...,
    ]:
        return tuple(
            item.obligation.requirement
            for item in self.requirement_work_items
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
            AndroidUniverseUeventdSourceContext,
        ):
            raise TypeError(
                "source_context must be an "
                "AndroidUniverseUeventdSourceContext"
            )

        if (
            self.source_context.source_identity
            != self.source_identity
        ):
            raise ValueError(
                "UEVENTD source_context must preserve the "
                "same canonical source identity"
            )

        if (
            self.source_context.source_path
            != self.source_path
        ):
            raise ValueError(
                "UEVENTD source_context must preserve the "
                "same source_path"
            )

        if (
            self.source_context.android_path
            != self.android_path
        ):
            raise ValueError(
                "UEVENTD source_context must preserve the "
                "same android_path"
            )

        if not isinstance(
            self.requirement_work_items,
            tuple,
        ):
            raise TypeError(
                "requirement_work_items must be a tuple"
            )

        if not self.requirement_work_items:
            raise ValueError(
                "UEVENTD source representation requires at least "
                "one Reconstruction work item"
            )

        previous_source_line = None

        for item in self.requirement_work_items:
            if not isinstance(
                item,
                AndroidReconstructionWorkItem,
            ):
                raise TypeError(
                    "requirement_work_items must contain only "
                    "AndroidReconstructionWorkItem instances"
                )

            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.RECONSTRUCT
            ):
                raise ValueError(
                    "UEVENTD source representation may contain "
                    "only RECONSTRUCT work"
                )

            if (
                item.requirement_kind
                != "ueventd"
            ):
                raise ValueError(
                    "UEVENTD source representation may contain "
                    "only ueventd work"
                )

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseUeventdRequirement,
            ):
                raise TypeError(
                    "UEVENTD Reconstruction work must preserve "
                    "an AndroidUniverseUeventdRequirement"
                )

            if (
                item.source_identity
                != requirement.requirement_id
            ):
                raise ValueError(
                    "UEVENTD work item source identity must "
                    "preserve the canonical requirement identity"
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
                    "all UEVENTD requirements in one representation "
                    "must share one canonical source identity"
                )

            if (
                requirement.source_path
                != self.source_path
            ):
                raise ValueError(
                    "all UEVENTD requirements in one representation "
                    "must preserve the same source_path"
                )

            if (
                requirement.android_path
                != self.android_path
            ):
                raise ValueError(
                    "all UEVENTD requirements in one representation "
                    "must preserve the same android_path"
                )

            source_line = (
                requirement.declaration.source_line
            )

            if (
                previous_source_line is not None
                and source_line < previous_source_line
            ):
                raise ValueError(
                    "UEVENTD source requirements must remain in "
                    "canonical source-line order"
                )

            previous_source_line = source_line

        obligation_ids = (
            self.contributing_obligation_ids
        )

        if len(
            obligation_ids
        ) != len(
            set(obligation_ids)
        ):
            raise ValueError(
                "UEVENTD source representation contains duplicate "
                "Reconstruction work identities"
            )
