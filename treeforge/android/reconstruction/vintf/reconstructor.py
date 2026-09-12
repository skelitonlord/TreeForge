from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionInput,
    AndroidReconstructionWorkKind,
)
from treeforge.android.reconstruction.vintf.model import (
    AndroidReconstructionVintfDocumentRepresentation,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionVintfReconstructor:
    """
    Reconstruct canonical VINTF document representations.

    Each admitted VINTF Planning obligation is already one complete canonical
    Universe document requirement. Reconstruction therefore preserves that
    document boundary exactly rather than regrouping or decomposing it.

    Universe remains the owner of XML interpretation and applicability.
    No document selection, HAL/interface reconciliation, path inference,
    destination choice, XML rendering, or materialization occurs here.
    """

    @staticmethod
    def reconstruct(
        reconstruction_input: AndroidReconstructionInput,
    ) -> tuple[
        AndroidReconstructionVintfDocumentRepresentation,
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

        expected_obligation_ids = set()

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
                != "vintf"
            ):
                continue

            requirement = (
                item.obligation.requirement
            )

            if not isinstance(
                requirement,
                AndroidUniverseVintfDocumentRequirement,
            ):
                raise TypeError(
                    "VINTF Reconstruction work must preserve an "
                    "AndroidUniverseVintfDocumentRequirement"
                )

            source_identity = (
                requirement.source_identity
            )

            representations.append(
                AndroidReconstructionVintfDocumentRepresentation(
                    source_identity=source_identity,
                    source_path=requirement.source_path,
                    android_path=requirement.android_path,
                    work_item=item,
                    requirement=requirement,
                )
            )

            expected_obligation_ids.add(
                item.obligation_id
            )

        result = tuple(
            sorted(
                representations,
                key=lambda representation: (
                    representation.requirement.requirement_id,
                    representation.obligation_id,
                ),
            )
        )

        representation_ids = tuple(
            representation.representation_id
            for representation in result
        )

        if len(
            representation_ids
        ) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "VINTF document representation identities "
                "must be unique"
            )

        represented_obligation_ids = {
            representation.obligation_id
            for representation in result
        }

        if (
            represented_obligation_ids
            != expected_obligation_ids
        ):
            missing = sorted(
                expected_obligation_ids
                - represented_obligation_ids
            )

            unexpected = sorted(
                represented_obligation_ids
                - expected_obligation_ids
            )

            raise ValueError(
                "VINTF Reconstruction must account for every "
                "admitted VINTF work item exactly once: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        return result
