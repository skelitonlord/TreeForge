from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction.runtime_property.model import (
    AndroidReconstructionRuntimePropertyRepresentation,
)
from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionRuntimePropertyReconstructor:
    """
    Reconstruct canonical runtime-property semantic representations.

    One admitted runtime-property obligation becomes one representation for
    its canonical Universe property key.

    This stage does not infer property files, destinations, ownership,
    producers, values, or rendering. Those concerns may only be established
    later when supported by canonical Reconstruction semantics.
    """

    @staticmethod
    def reconstruct(
        reconstruction_input: AndroidReconstructionInput,
    ) -> tuple[
        AndroidReconstructionRuntimePropertyRepresentation,
        ...,
    ]:
        if not isinstance(
            reconstruction_input,
            AndroidReconstructionInput,
        ):
            raise TypeError(
                "reconstruction_input must be an "
                "AndroidReconstructionInput"
            )

        representations = []

        for item in (
            reconstruction_input.work_items
        ):
            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.RECONSTRUCT
            ):
                continue

            if (
                item.requirement_kind
                != "runtime_property"
            ):
                continue

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseRuntimePropertyRequirement,
            ):
                raise TypeError(
                    "runtime_property Reconstruction work "
                    "must preserve an "
                    "AndroidUniverseRuntimePropertyRequirement"
                )

            representations.append(
                AndroidReconstructionRuntimePropertyRepresentation(
                    property_key=(
                        requirement.property_key
                    ),
                    work_item=item,
                    requirement=requirement,
                )
            )

        result = tuple(
            sorted(
                representations,
                key=lambda representation: (
                    representation.property_key,
                    representation.obligation_id,
                ),
            )
        )

        property_keys = tuple(
            representation.property_key
            for representation in result
        )

        if len(
            property_keys
        ) != len(
            set(property_keys)
        ):
            raise ValueError(
                "runtime-property Reconstruction must contain "
                "one representation per canonical property key"
            )

        obligation_ids = tuple(
            representation.obligation_id
            for representation in result
        )

        if len(
            obligation_ids
        ) != len(
            set(obligation_ids)
        ):
            raise ValueError(
                "runtime-property Reconstruction work identities "
                "must be unique"
            )

        expected_obligation_ids = {
            item.obligation_id
            for item in reconstruction_input.work_items
            if (
                item.work_kind
                is AndroidReconstructionWorkKind.RECONSTRUCT
                and item.requirement_kind
                == "runtime_property"
            )
        }

        if (
            set(obligation_ids)
            != expected_obligation_ids
        ):
            raise ValueError(
                "runtime-property Reconstruction must account "
                "for every admitted runtime_property work item "
                "exactly once"
            )

        return result
