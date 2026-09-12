from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.reconstruction.selinux.model import (
    AndroidReconstructionSelinuxSourceRepresentation,
)
from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionSelinuxContentSynthesizer:
    """
    Preserve exact canonical SELinux source bytes.

    Parsing guarantees that every SELinux source retains its exact raw bytes.
    Universe preserves the exact ParsedAndroidSelinuxSource identity and
    Reconstruction preserves the exact Universe requirement identity.

    Textual SELinux sources are therefore PRESERVED_EXACT directly from their
    canonical raw bytes. Compiled policy and otherwise opaque sources remain
    OPAQUE and carry those same exact bytes.

    No textual source is regenerated from semantic declarations or CIL forms.
    Compiled policy is never reverse-generated.

    No Parsing reach-back, policy reconciliation, ownership, destination,
    filename, build-module, or materialization decision occurs here.
    """

    @staticmethod
    def synthesize(
        representation: AndroidReconstructionSelinuxSourceRepresentation,
    ) -> AndroidReconstructionSourceContent:
        if not isinstance(
            representation,
            AndroidReconstructionSelinuxSourceRepresentation,
        ):
            raise TypeError(
                "representation must be an "
                "AndroidReconstructionSelinuxSourceRepresentation"
            )

        requirement = representation.requirement
        raw_bytes = requirement.parsed.raw_bytes

        if not isinstance(
            raw_bytes,
            bytes,
        ):
            raise TypeError(
                "canonical SELinux raw source must be bytes"
            )

        status = (
            AndroidReconstructionSourceContentStatus.OPAQUE
            if requirement.is_opaque
            else (
                AndroidReconstructionSourceContentStatus
                .PRESERVED_EXACT
            )
        )

        return AndroidReconstructionSourceContent(
            content_id=(
                "source-content:selinux:"
                f"{representation.representation_id}"
            ),
            representation_id=(
                representation.representation_id
            ),
            media_kind=(
                AndroidReconstructionSourceContentMediaKind.SELINUX
            ),
            status=status,
            raw_bytes=raw_bytes,
            contributing_obligation_ids=(
                representation.obligation_id,
            ),
        )

    @classmethod
    def synthesize_all(
        cls,
        representations: tuple[
            AndroidReconstructionSelinuxSourceRepresentation,
            ...,
        ],
    ) -> tuple[
        AndroidReconstructionSourceContent,
        ...,
    ]:
        if not isinstance(
            representations,
            tuple,
        ):
            raise TypeError(
                "representations must be a tuple"
            )

        result = tuple(
            sorted(
                (
                    cls.synthesize(representation)
                    for representation
                    in representations
                ),
                key=lambda content: (
                    content.representation_id,
                    content.content_id,
                ),
            )
        )

        content_ids = tuple(
            content.content_id
            for content in result
        )

        if len(content_ids) != len(set(content_ids)):
            raise ValueError(
                "SELinux source content identities must be unique"
            )

        representation_ids = tuple(
            content.representation_id
            for content in result
        )

        if len(
            representation_ids
        ) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "SELinux source content must contain exactly "
                "one content unit per source representation"
            )

        return result
