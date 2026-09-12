from __future__ import annotations

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.device_tree.selinux_effective_policy import (
    AndroidDeviceTreeEffectiveSelinuxSynthesis,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)


class AndroidDeviceTreeDerivedSelinuxRealizationPromoter:
    """
    Promote one completed Device Tree-derived SELinux source synthesis back
    onto the exact Reconstruction build representation that supplied it.

    Reconstruction remains unchanged. Its SELINUX_RUNTIME_OUTPUT role records
    the canonical observed factory artifact. Device Tree may select a stronger
    downstream build mechanism when it has successfully reconstructed
    source-equivalent Android policy inputs.

    This preserves the invariant that every Reconstruction representation has
    exactly one Device Tree realization. Derived source files are evidence for
    that realization; they are not additional canonical obligations.
    """

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        synthesis: AndroidDeviceTreeEffectiveSelinuxSynthesis,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> tuple[
        AndroidDeviceTreeBuildRealization,
        ...,
    ]:
        from treeforge.android.reconstruction.model import (
            AndroidReconstructionResult,
        )

        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            synthesis,
            AndroidDeviceTreeEffectiveSelinuxSynthesis,
        ):
            raise TypeError(
                "synthesis must be an "
                "AndroidDeviceTreeEffectiveSelinuxSynthesis"
            )

        if not isinstance(
            realizations,
            tuple,
        ):
            raise TypeError(
                "realizations must be a tuple"
            )

        if not all(
            isinstance(
                realization,
                AndroidDeviceTreeBuildRealization,
            )
            for realization in realizations
        ):
            raise TypeError(
                "realizations must contain only "
                "AndroidDeviceTreeBuildRealization values"
            )

        # No applicable effective policy synthesis is a valid generic outcome.
        if not synthesis.sources:
            return realizations

        # Incomplete synthesis remains canonical evidence only. Never promote
        # a runtime artifact merely because Device Tree emitted a partial file.
        if not synthesis.complete:
            return realizations

        source_representation_ids = {
            source.source_representation_id
            for source in synthesis.sources
        }

        source_requirement_ids = {
            source.source_requirement_id
            for source in synthesis.sources
        }

        if len(source_representation_ids) != 1:
            raise ValueError(
                "completed derived SELinux synthesis must identify "
                "exactly one source representation"
            )

        if len(source_requirement_ids) != 1:
            raise ValueError(
                "completed derived SELinux synthesis must identify "
                "exactly one canonical source requirement"
            )

        source_representation_id = next(
            iter(source_representation_ids)
        )

        source_requirement_id = next(
            iter(source_requirement_ids)
        )

        matching_source_representations = tuple(
            source
            for source
            in reconstruction.selinux_source_representations
            if (
                source.representation_id
                == source_representation_id
            )
        )

        if len(matching_source_representations) != 1:
            raise ValueError(
                "completed derived SELinux synthesis does not resolve "
                "to exactly one Reconstruction SELinux source "
                "representation: "
                f"{source_representation_id}"
            )

        source_representation = (
            matching_source_representations[0]
        )

        if (
            source_representation.requirement.requirement_id
            != source_requirement_id
        ):
            raise ValueError(
                "derived SELinux synthesis requirement identity does "
                "not match its Reconstruction source representation"
            )

        matching_contents = tuple(
            content
            for content
            in reconstruction.selinux_source_contents
            if (
                content.representation_id
                == source_representation_id
            )
        )

        if len(matching_contents) != 1:
            raise ValueError(
                "completed derived SELinux synthesis must map to "
                "exactly one Reconstruction SELinux source content"
            )

        source_content_id = (
            matching_contents[0].content_id
        )

        matching_realizations = tuple(
            realization
            for realization
            in realizations
            if (
                realization
                .build_representation
                .source_content_id
                == source_content_id
            )
        )

        if len(matching_realizations) != 1:
            raise ValueError(
                "completed derived SELinux synthesis must map to "
                "exactly one Device Tree build realization"
            )

        existing = matching_realizations[0]
        representation = existing.build_representation

        if (
            representation.kind
            is not AndroidReconstructionBuildRepresentationKind
            .SELINUX_RUNTIME_OUTPUT
        ):
            raise ValueError(
                "derived SELinux source synthesis may promote only "
                "a Reconstruction SELINUX_RUNTIME_OUTPUT representation"
            )

        if (
            existing.kind
            is not AndroidDeviceTreeBuildRealizationKind
            .SELINUX_RUNTIME_OUTPUT
            or existing.status
            is not AndroidDeviceTreeBuildRealizationStatus
            .PARTIAL
        ):
            raise ValueError(
                "derived SELinux source synthesis expected one PARTIAL "
                "SELINUX_RUNTIME_OUTPUT Device Tree realization"
            )

        # A completed source synthesis must contain at least one Android
        # policy-language .te payload for this source representation.
        #
        # A canonical effective partition representation may realize into
        # multiple source-policy files when Android ownership requires a
        # public/private split. Preserve the one-realization-per-
        # Reconstruction identity while allowing that representation to be
        # backed by multiple derived source files.
        policy_sources = tuple(
            sorted(
                (
                    source
                    for source in synthesis.sources
                    if (
                        source.source_representation_id
                        == source_representation_id
                        and source.destination.suffix == ".te"
                    )
                ),
                key=lambda source: (
                    source.destination.as_posix()
                ),
            )
        )

        if not policy_sources:
            raise ValueError(
                "completed derived SELinux synthesis must contain "
                "at least one primary .te policy source"
            )

        if len(policy_sources) == 1:
            realization_source_path = (
                policy_sources[0].destination
            )
        else:
            source_paths = tuple(
                source.destination
                for source in policy_sources
            )

            first_path = source_paths[0]

            common_ancestor = None

            for candidate in (
                first_path.parent,
                *first_path.parents,
            ):
                if all(
                    source_path.is_relative_to(candidate)
                    for source_path in source_paths
                ):
                    common_ancestor = candidate
                    break

            if common_ancestor is None:
                raise ValueError(
                    "derived SELinux policy sources for one "
                    "Reconstruction representation do not share "
                    "a common source root"
                )

            realization_source_path = common_ancestor

        promoted = (
            AndroidDeviceTreeBuildRealization(
                realization_id=existing.realization_id,
                kind=(
                    AndroidDeviceTreeBuildRealizationKind
                    .SELINUX_POLICY
                ),
                status=(
                    AndroidDeviceTreeBuildRealizationStatus
                    .RESOLVED
                ),
                build_representation=representation,
                source_path=realization_source_path,
                module_name=None,
                dependency_realization_ids=(
                    existing.dependency_realization_ids
                ),
                reason=None,
            )
        )

        # Replace the matching realization in-place. Device Tree
        # promotion must preserve the existing realization ordering as
        # well as the exact one-realization-per-Reconstruction identity
        # universe.
        result = tuple(
            promoted
            if realization.realization_id
            == existing.realization_id
            else realization
            for realization in realizations
        )

        # Preserve the exact one-realization-per-Reconstruction identity
        # universe after promotion.
        before_ids = tuple(
            sorted(
                realization.representation_id
                for realization in realizations
            )
        )

        after_ids = tuple(
            sorted(
                realization.representation_id
                for realization in result
            )
        )

        if before_ids != after_ids:
            raise ValueError(
                "derived SELinux realization promotion changed "
                "Reconstruction representation coverage"
            )

        if len(result) != len(realizations):
            raise ValueError(
                "derived SELinux realization promotion changed "
                "Device Tree realization count"
            )

        return result
