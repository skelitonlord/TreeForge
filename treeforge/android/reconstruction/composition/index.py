from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
    AndroidReconstructionWorkKind,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionCompositionIndex:
    """
    Deterministic lookup index from exact canonical Universe objects and
    identities to existing Reconstruction representations/artifacts.

    This index performs no semantic resolution. It only indexes identities
    already admitted and reconstructed/preserved by earlier Reconstruction
    work.
    """

    representation_by_requirement_identity: dict[
        int,
        str,
    ]

    representation_by_requirement_id: dict[
        str,
        str,
    ]

    runtime_property_representation_by_key: dict[
        str,
        str,
    ]

    preserved_artifact_by_requirement_id: dict[
        str,
        str,
    ]

    selinux_representation_by_context_identity: dict[
        int,
        str,
    ]

    vintf_representation_by_document_identity: dict[
        int,
        str,
    ]

    @classmethod
    def build(
        cls,
        result: AndroidReconstructionResult,
    ) -> "AndroidReconstructionCompositionIndex":
        if not isinstance(
            result,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "result must be an AndroidReconstructionResult"
            )

        representation_by_requirement_identity: dict[
            int,
            str,
        ] = {}

        representation_by_requirement_id: dict[
            str,
            str,
        ] = {}

        runtime_property_representation_by_key: dict[
            str,
            str,
        ] = {}

        preserved_artifact_by_requirement_id: dict[
            str,
            str,
        ] = {}

        selinux_representation_by_context_identity: dict[
            int,
            str,
        ] = {}

        vintf_representation_by_document_identity: dict[
            int,
            str,
        ] = {}

        def index_requirement(
            requirement: object,
            representation_id: str,
        ) -> None:
            object_identity = id(
                requirement
            )

            existing = (
                representation_by_requirement_identity
                .get(
                    object_identity
                )
            )

            if (
                existing is not None
                and existing != representation_id
            ):
                raise ValueError(
                    "one canonical Universe requirement maps to "
                    "multiple Reconstruction representations"
                )

            representation_by_requirement_identity[
                object_identity
            ] = representation_id

            requirement_id = getattr(
                requirement,
                "requirement_id",
                None,
            )

            if (
                isinstance(
                    requirement_id,
                    str,
                )
                and requirement_id
            ):
                existing = (
                    representation_by_requirement_id
                    .get(
                        requirement_id
                    )
                )

                if (
                    existing is not None
                    and existing != representation_id
                ):
                    raise ValueError(
                        "one canonical requirement identity maps "
                        "to multiple Reconstruction representations: "
                        f"{requirement_id}"
                    )

                representation_by_requirement_id[
                    requirement_id
                ] = representation_id

        for representation in (
            result.init_source_representations
        ):
            for requirement in (
                representation.import_requirements
                + representation.service_requirements
                + representation.action_requirements
            ):
                index_requirement(
                    requirement,
                    representation.representation_id,
                )

        for representation in (
            result.runtime_property_representations
        ):
            index_requirement(
                representation.requirement,
                representation.representation_id,
            )

            property_key = (
                representation.property_key
            )

            existing = (
                runtime_property_representation_by_key
                .get(
                    property_key
                )
            )

            if (
                existing is not None
                and existing
                != representation.representation_id
            ):
                raise ValueError(
                    "one canonical runtime-property key maps "
                    "to multiple Reconstruction representations: "
                    f"{property_key}"
                )

            runtime_property_representation_by_key[
                property_key
            ] = representation.representation_id

        for representation in (
            result.fstab_source_representations
        ):
            for requirement in (
                representation.requirements
            ):
                index_requirement(
                    requirement,
                    representation.representation_id,
                )

        for representation in (
            result.ueventd_source_representations
        ):
            for requirement in (
                representation.requirements
            ):
                index_requirement(
                    requirement,
                    representation.representation_id,
                )

        for representation in (
            result.vintf_document_representations
        ):
            requirement = (
                representation.requirement
            )

            index_requirement(
                requirement,
                representation.representation_id,
            )

            document_identity = id(
                requirement
            )

            existing = (
                vintf_representation_by_document_identity
                .get(
                    document_identity
                )
            )

            if (
                existing is not None
                and existing
                != representation.representation_id
            ):
                raise ValueError(
                    "one canonical VINTF document maps to multiple "
                    "Reconstruction representations"
                )

            vintf_representation_by_document_identity[
                document_identity
            ] = representation.representation_id

        for representation in (
            result.selinux_source_representations
        ):
            requirement = (
                representation.requirement
            )

            index_requirement(
                requirement,
                representation.representation_id,
            )

            for context_requirement in (
                requirement.context_requirements
            ):
                context_identity = id(
                    context_requirement
                )

                existing = (
                    selinux_representation_by_context_identity
                    .get(
                        context_identity
                    )
                )

                if (
                    existing is not None
                    and existing
                    != representation.representation_id
                ):
                    raise ValueError(
                        "one canonical SELinux context requirement "
                        "maps to multiple SELinux source representations"
                    )

                selinux_representation_by_context_identity[
                    context_identity
                ] = representation.representation_id

        for item in (
            result.reconstruction_input.work_items
        ):
            if (
                item.work_kind
                is not AndroidReconstructionWorkKind.PRESERVE
            ):
                continue

            requirement_id = getattr(
                item.obligation.requirement,
                "requirement_id",
                None,
            )

            if (
                not isinstance(
                    requirement_id,
                    str,
                )
                or not requirement_id
            ):
                continue

            preserved_artifact_id = (
                item.preserved_artifact_id
            )

            if preserved_artifact_id is None:
                raise ValueError(
                    "PRESERVE work is missing preserved artifact identity"
                )

            existing = (
                preserved_artifact_by_requirement_id
                .get(
                    requirement_id
                )
            )

            if (
                existing is not None
                and existing != preserved_artifact_id
            ):
                raise ValueError(
                    "one canonical preserved requirement maps to "
                    "multiple preserved artifact identities: "
                    f"{requirement_id}"
                )

            preserved_artifact_by_requirement_id[
                requirement_id
            ] = preserved_artifact_id

        return cls(
            runtime_property_representation_by_key=(
                runtime_property_representation_by_key
            ),
            representation_by_requirement_identity=(
                representation_by_requirement_identity
            ),
            representation_by_requirement_id=(
                representation_by_requirement_id
            ),
            preserved_artifact_by_requirement_id=(
                preserved_artifact_by_requirement_id
            ),
            selinux_representation_by_context_identity=(
                selinux_representation_by_context_identity
            ),
            vintf_representation_by_document_identity=(
                vintf_representation_by_document_identity
            ),
        )
