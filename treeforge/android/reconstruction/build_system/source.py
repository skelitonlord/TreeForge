from __future__ import annotations

from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentation,
    AndroidReconstructionBuildRepresentationKind,
    AndroidReconstructionBuildRepresentationStatus,
)
from treeforge.android.reconstruction.source_content import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
)


_MEDIA_KIND_TO_BUILD_KIND = {
    AndroidReconstructionSourceContentMediaKind.INIT_RC: (
        AndroidReconstructionBuildRepresentationKind.SOURCE_CONFIG
    ),
    AndroidReconstructionSourceContentMediaKind.FSTAB: (
        AndroidReconstructionBuildRepresentationKind.SOURCE_CONFIG
    ),
    AndroidReconstructionSourceContentMediaKind.UEVENTD: (
        AndroidReconstructionBuildRepresentationKind.SOURCE_CONFIG
    ),
    AndroidReconstructionSourceContentMediaKind.VINTF_XML: (
        AndroidReconstructionBuildRepresentationKind.VINTF_DOCUMENT
    ),
}


class AndroidReconstructionSourceBuildProjector:
    """
    Project reconstructed source-content units into syntax-neutral Android
    build participation.

    Reconstruction remains responsible only for establishing that one
    canonical reconstructed source-content unit participates in the eventual
    build and, where intrinsically known, what broad build role it has.

    This projector deliberately does not choose:
    - source-tree ownership;
    - source-tree destination paths;
    - filenames;
    - Android.bp versus Android.mk;
    - concrete Soong/Make module syntax;
    - product/BoardConfig variables;
    - filesystem materialization.

    Runtime-property content is intentionally not accepted here yet because
    Reconstruction already distinguishes source-declarable from
    NOT_SOURCE_DECLARABLE property content and that policy needs a dedicated
    projection rather than treating every property as a source file.
    """

    @staticmethod
    def project(
        contents: tuple[
            AndroidReconstructionSourceContent,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionBuildRepresentation,
        ...,
    ]:
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
                "contents contains an invalid source-content model"
            )

        projected = []

        for content in contents:
            kind = _MEDIA_KIND_TO_BUILD_KIND.get(
                content.media_kind
            )

            if kind is None:
                raise ValueError(
                    "source-content media kind has no build "
                    "participation mapping: "
                    f"{content.media_kind.value}"
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
                "source-backed build representation identities "
                "must be unique"
            )

        source_content_ids = tuple(
            representation.source_content_id
            for representation in result
        )

        if len(
            source_content_ids
        ) != len(
            set(source_content_ids)
        ):
            raise ValueError(
                "source content may map to only one source-backed "
                "build representation"
            )

        expected_content_ids = {
            content.content_id
            for content in contents
        }

        if set(source_content_ids) != expected_content_ids:
            raise ValueError(
                "source-backed build representations must cover "
                "the input source-content population exactly"
            )

        return result
