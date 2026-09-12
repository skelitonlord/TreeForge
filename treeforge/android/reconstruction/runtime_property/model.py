from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionWorkItem,
    AndroidReconstructionWorkKind,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionRuntimePropertyRepresentation:
    """
    Canonical semantic Reconstruction representation of one runtime property.

    Android Device Universe owns the canonical runtime-property requirement,
    including all producer, consumer, declaration, boot-export, trigger, and
    action observations associated with the property key.

    Reconstruction preserves that exact requirement and its admitted Planning
    work item without reinterpreting those observations.

    This representation deliberately does not choose a property file,
    source-tree destination, ownership domain, rendered declaration, INIT
    command, or Device Tree materialization strategy.
    """

    property_key: str

    work_item: AndroidReconstructionWorkItem

    requirement: AndroidUniverseRuntimePropertyRequirement

    @property
    def representation_id(self) -> str:
        return (
            "runtime-property:"
            f"{self.property_key}"
        )

    @property
    def obligation_id(self) -> str:
        return self.work_item.obligation_id

    def __post_init__(self) -> None:
        if not isinstance(
            self.property_key,
            str,
        ):
            raise TypeError(
                "property_key must be a string"
            )

        if not self.property_key:
            raise ValueError(
                "property_key must not be empty"
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
                "runtime-property representation requires "
                "RECONSTRUCT work"
            )

        if (
            self.work_item.requirement_kind
            != "runtime_property"
        ):
            raise ValueError(
                "runtime-property representation requires "
                "runtime_property work"
            )

        if not isinstance(
            self.requirement,
            AndroidUniverseRuntimePropertyRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseRuntimePropertyRequirement"
            )

        if (
            self.requirement
            is not self.work_item.obligation.requirement
        ):
            raise ValueError(
                "runtime-property representation must preserve "
                "the exact canonical Universe requirement identity"
            )

        if (
            self.requirement.property_key
            != self.property_key
        ):
            raise ValueError(
                "property_key must match canonical Universe "
                "runtime-property requirement"
            )

        if (
            self.work_item.source_identity
            != self.property_key
        ):
            raise ValueError(
                "runtime-property Reconstruction source identity "
                "must match property_key"
            )
