from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionBuildDependencyValidation:
    """
    Global integrity summary for the finished syntax-neutral build graph.

    Family projectors remain authoritative for deciding which canonical
    relationships are real physical build dependencies. This model records
    only graph-wide structural validation after those projections are
    complete.
    """

    representation_count: int
    representations_with_dependencies: int
    dependency_edge_count: int


class AndroidReconstructionBuildDependencyValidator:
    """
    Validate the completed Build-System dependency graph.

    This validator does not infer, add, remove, or reinterpret dependencies.
    It only verifies structural invariants over dependency_ids already
    projected by their owning build families.
    """

    @staticmethod
    def validate(
        build_representations: tuple[
            AndroidReconstructionBuildRepresentation,
            ...,
        ],
    ) -> AndroidReconstructionBuildDependencyValidation:
        if not isinstance(
            build_representations,
            tuple,
        ):
            raise TypeError(
                "build_representations must be a tuple"
            )

        if not all(
            isinstance(
                representation,
                AndroidReconstructionBuildRepresentation,
            )
            for representation
            in build_representations
        ):
            raise TypeError(
                "build_representations must contain only "
                "AndroidReconstructionBuildRepresentation values"
            )

        representation_by_id = {
            representation.representation_id: representation
            for representation
            in build_representations
        }

        if len(
            representation_by_id
        ) != len(
            build_representations
        ):
            raise ValueError(
                "Build-System representation identities must be unique"
            )

        representation_ids = set(
            representation_by_id
        )

        dependency_edge_count = 0
        representations_with_dependencies = 0

        for representation in build_representations:
            dependency_ids = representation.dependency_ids

            #
            # These are already enforced by the representation model itself,
            # but retain them here as explicit finished-graph invariants.
            #
            if len(
                dependency_ids
            ) != len(
                set(dependency_ids)
            ):
                raise ValueError(
                    "Build-System dependency identities must be unique "
                    "within each representation: "
                    f"{representation.representation_id}"
                )

            if dependency_ids != tuple(
                sorted(
                    dependency_ids
                )
            ):
                raise ValueError(
                    "Build-System dependencies must use deterministic "
                    "ordering: "
                    f"{representation.representation_id}"
                )

            if (
                representation.representation_id
                in dependency_ids
            ):
                raise ValueError(
                    "Build-System representation must not depend on "
                    "itself: "
                    f"{representation.representation_id}"
                )

            missing_dependency_ids = (
                set(
                    dependency_ids
                )
                - representation_ids
            )

            if missing_dependency_ids:
                raise ValueError(
                    "Build-System dependency references missing "
                    "representation identities: "
                    f"owner={representation.representation_id!r}, "
                    f"missing={sorted(missing_dependency_ids)!r}"
                )

            if dependency_ids:
                representations_with_dependencies += 1

            dependency_edge_count += len(
                dependency_ids
            )

        return AndroidReconstructionBuildDependencyValidation(
            representation_count=len(
                build_representations
            ),
            representations_with_dependencies=(
                representations_with_dependencies
            ),
            dependency_edge_count=(
                dependency_edge_count
            ),
        )
