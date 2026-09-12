from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidReconstructionSourceContentStatus(StrEnum):
    """
    Canonical source-content synthesis disposition.

    SYNTHESIZED means all active source semantics owned by the
    representation were rendered and no known unresolved member remains.

    PARTIAL_UNRESOLVED means active source content was rendered while exact
    canonical source members remain explicitly unresolved upstream.

    The remaining values support later Reconstruction families without
    pretending semantic representations are always source-declarable.
    """

    SYNTHESIZED = "synthesized"
    PARTIAL_UNRESOLVED = "partial_unresolved"
    PRESERVED_EXACT = "preserved_exact"
    NOT_SOURCE_DECLARABLE = "not_source_declarable"
    OPAQUE = "opaque"


class AndroidReconstructionSourceContentMediaKind(StrEnum):
    """Intrinsic source-content grammar represented by one content unit."""

    INIT_RC = "init_rc"
    FSTAB = "fstab"
    UEVENTD = "ueventd"
    VINTF_XML = "vintf_xml"
    SELINUX = "selinux"
    PROPERTY = "property"


@dataclass(frozen=True, slots=True)
class AndroidReconstructionSourceContent:
    """
    One canonical source-content result produced by Reconstruction.

    This model owns renderable content only. It does not choose a Device Tree
    destination, ownership domain, filename, build module, or filesystem
    materialization strategy.

    ``contributing_obligation_ids`` identifies admitted Reconstruction work
    rendered into the content.

    ``excluded_obligation_ids`` identifies canonical members of the same
    source that Planning intentionally did not admit for Reconstruction.

    ``unresolved_obligation_ids`` preserves canonical members whose status
    remains explicitly known-unresolved.
    """

    content_id: str
    representation_id: str

    media_kind: AndroidReconstructionSourceContentMediaKind
    status: AndroidReconstructionSourceContentStatus

    text: str | None = None
    raw_bytes: bytes | None = None

    contributing_obligation_ids: tuple[str, ...] = ()
    excluded_obligation_ids: tuple[str, ...] = ()
    unresolved_obligation_ids: tuple[str, ...] = ()
    unresolved_context_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("content_id", self.content_id),
            ("representation_id", self.representation_id),
        ):
            if not isinstance(value, str):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.media_kind,
            AndroidReconstructionSourceContentMediaKind,
        ):
            raise TypeError(
                "media_kind must be an "
                "AndroidReconstructionSourceContentMediaKind"
            )

        if not isinstance(
            self.status,
            AndroidReconstructionSourceContentStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidReconstructionSourceContentStatus"
            )

        if (
            self.text is not None
            and not isinstance(self.text, str)
        ):
            raise TypeError(
                "text must be a string or None"
            )

        if (
            self.raw_bytes is not None
            and not isinstance(self.raw_bytes, bytes)
        ):
            raise TypeError(
                "raw_bytes must be bytes or None"
            )

        for field_name, values in (
            (
                "contributing_obligation_ids",
                self.contributing_obligation_ids,
            ),
            (
                "excluded_obligation_ids",
                self.excluded_obligation_ids,
            ),
            (
                "unresolved_obligation_ids",
                self.unresolved_obligation_ids,
            ),
            (
                "unresolved_context_ids",
                self.unresolved_context_ids,
            ),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(value, str) and value
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain only "
                    "non-empty strings"
                )

            if len(values) != len(set(values)):
                raise ValueError(
                    f"{field_name} must not contain duplicates"
                )

        contributing = set(
            self.contributing_obligation_ids
        )
        excluded = set(
            self.excluded_obligation_ids
        )
        unresolved = set(
            self.unresolved_obligation_ids
        )

        if contributing & excluded:
            raise ValueError(
                "contributing and excluded obligation identities "
                "must be disjoint"
            )

        if contributing & unresolved:
            raise ValueError(
                "contributing and unresolved obligation identities "
                "must be disjoint"
            )

        if excluded & unresolved:
            raise ValueError(
                "excluded and unresolved obligation identities "
                "must be disjoint"
            )

        if self.status in (
            AndroidReconstructionSourceContentStatus.SYNTHESIZED,
            AndroidReconstructionSourceContentStatus.PARTIAL_UNRESOLVED,
        ):
            if (
                not isinstance(self.text, str)
                or not self.text
            ):
                raise ValueError(
                    "rendered source content requires non-empty text"
                )

        if (
            self.status
            is AndroidReconstructionSourceContentStatus.PARTIAL_UNRESOLVED
            and not (
                self.unresolved_obligation_ids
                or self.unresolved_context_ids
            )
        ):
            raise ValueError(
                "PARTIAL_UNRESOLVED content requires unresolved "
                "obligation identities or unresolved source context"
            )

        if (
            self.status
            is AndroidReconstructionSourceContentStatus.SYNTHESIZED
            and (
                self.unresolved_obligation_ids
                or self.unresolved_context_ids
            )
        ):
            raise ValueError(
                "SYNTHESIZED content may not carry unresolved "
                "obligation identities or unresolved source context"
            )
