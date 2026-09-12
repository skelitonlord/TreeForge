from __future__ import annotations

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.reconstruction.selinux.model import (
    AndroidReconstructionSelinuxSourceRepresentation,
)
from treeforge.android.reconstruction.source_content import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)


class AndroidReconstructionSelinuxBuildProjector:
    """
    Project canonical SELinux Reconstruction content into syntax-neutral
    Android build roles.

    Intrinsic SELinux grammar does not by itself establish that a
    factory-observed file is a policy source-tree input.

    Android-visible installed SELinux files are runtime/build outputs.
    Compiled or otherwise opaque SELinux content is likewise treated as
    runtime/output content.

    Only non-installed, non-opaque SELinux content remains a candidate
    SELINUX_POLICY source input.

    Device Tree remains responsible for choosing the concrete realization.
    """

    @classmethod
    def project(
        cls,
        representations: tuple[
            AndroidReconstructionSelinuxSourceRepresentation,
            ...,
        ],
        contents: tuple[
            AndroidReconstructionSourceContent,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
        if not isinstance(representations, tuple):
            raise TypeError("representations must be a tuple")

        if not all(
            isinstance(
                representation,
                AndroidReconstructionSelinuxSourceRepresentation,
            )
            for representation in representations
        ):
            raise TypeError(
                "representations must contain only "
                "AndroidReconstructionSelinuxSourceRepresentation values"
            )

        if not isinstance(contents, tuple):
            raise TypeError("contents must be a tuple")

        if not all(
            isinstance(
                content,
                AndroidReconstructionSourceContent,
            )
            for content in contents
        ):
            raise TypeError(
                "contents must contain only "
                "AndroidReconstructionSourceContent values"
            )

        if not all(
            content.media_kind
            is AndroidReconstructionSourceContentMediaKind.SELINUX
            for content in contents
        ):
            raise ValueError(
                "SELinux build projection accepts only SELINUX content"
            )

        representation_by_id = {
            representation.representation_id: representation
            for representation in representations
        }

        if len(representation_by_id) != len(representations):
            raise ValueError(
                "SELinux Reconstruction representation identities "
                "must be unique"
            )

        content_by_representation_id = {
            content.representation_id: content
            for content in contents
        }

        if len(content_by_representation_id) != len(contents):
            raise ValueError(
                "SELinux Reconstruction content must contain exactly "
                "one unit per representation"
            )

        if (
            set(content_by_representation_id)
            != set(representation_by_id)
        ):
            missing = sorted(
                set(representation_by_id)
                - set(content_by_representation_id)
            )
            unexpected = sorted(
                set(content_by_representation_id)
                - set(representation_by_id)
            )

            raise ValueError(
                "SELinux build projection must preserve exact "
                "representation/content coverage: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        projected = []

        for representation in representations:
            content = content_by_representation_id[
                representation.representation_id
            ]

            if (
                representation.android_path is not None
                or representation.requirement.is_compiled_policy
                or representation.requirement.is_opaque
                or content.status
                is AndroidReconstructionSourceContentStatus.OPAQUE
            ):
                kind = (
                    AndroidReconstructionBuildRepresentationKind
                    .SELINUX_RUNTIME_OUTPUT
                )
            else:
                kind = (
                    AndroidReconstructionBuildRepresentationKind
                    .SELINUX_POLICY
                )

            projected.append(
                AndroidReconstructionBuildRepresentation(
                    representation_id=(
                        "build-representation:source:"
                        f"{content.content_id}"
                    ),
                    kind=kind,
                    status=(
                        AndroidReconstructionBuildRepresentationStatus
                        .RESOLVED
                    ),
                    source_identity=content.content_id,
                    source_content_id=content.content_id,
                    preserved_artifact_id=None,
                    installed_partition=None,
                    installed_android_path=None,
                    module_identity=None,
                    dependency_ids=(),
                    reason=None,
                )
            )

        result = tuple(
            sorted(
                projected,
                key=lambda representation: (
                    representation.representation_id
                ),
            )
        )

        source_content_ids = tuple(
            representation.source_content_id
            for representation in result
        )

        if len(source_content_ids) != len(set(source_content_ids)):
            raise ValueError(
                "SELinux source content may map to only one "
                "build representation"
            )

        if set(source_content_ids) != {
            content.content_id
            for content in contents
        }:
            raise ValueError(
                "SELinux build representations must cover the "
                "input source-content population exactly"
            )

        return result
