from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


class AndroidUniverseApplicabilityStatus(
    StrEnum
):
    """
    Current applicability state of one Universe requirement or variant.
    """

    ACTIVE = "active"
    CONDITIONAL = "conditional"
    ALTERNATIVE = "alternative"
    UNRESOLVED = "unresolved"


class AndroidUniverseApplicabilityEvidenceKind(
    StrEnum
):
    """
    Kind of upstream evidence establishing requirement applicability.
    """

    PROPERTY = "property"
    INIT_COMMAND = "init_command"
    SOURCE_STRUCTURE = "source_structure"
    SOURCE_EQUIVALENCE = "source_equivalence"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApplicabilityEvidence:
    """
    One exact observation contributing to applicability reasoning.

    raw_value preserves the literal upstream observation. ``source_path`` and
    ``line_number`` preserve its source identity without forcing unrelated
    Parsing model types into this generic relationship contract.
    """

    kind: AndroidUniverseApplicabilityEvidenceKind
    raw_value: str

    source_path: Path | None = None
    android_path: PurePosixPath | None = None
    line_number: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidUniverseApplicabilityEvidenceKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseApplicabilityEvidenceKind"
            )

        if not isinstance(
            self.raw_value,
            str,
        ):
            raise TypeError(
                "raw_value must be a string"
            )

        if not self.raw_value:
            raise ValueError(
                "raw_value must not be empty"
            )

        if (
            self.source_path is not None
            and not isinstance(
                self.source_path,
                Path,
            )
        ):
            raise TypeError(
                "source_path must be a Path or None"
            )

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a "
                "PurePosixPath or None"
            )

        if (
            self.android_path is not None
            and not self.android_path.is_absolute()
        ):
            raise ValueError(
                "android_path must be absolute"
            )

        if (
            self.android_path is not None
            and any(
                part == ".."
                for part in self.android_path.parts
            )
        ):
            raise ValueError(
                "android_path must not contain "
                "parent traversal"
            )

        if (
            self.line_number is not None
            and (
                isinstance(
                    self.line_number,
                    bool,
                )
                or not isinstance(
                    self.line_number,
                    int,
                )
                or self.line_number < 1
            )
        ):
            raise TypeError(
                "line_number must be a positive integer or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRequirementApplicability:
    """
    Applicability conclusion for one Universe requirement.

    ``requirement_id`` is a stable Universe-local identity. The relationship
    layer does not own the requirement object itself.

    No evidence is discarded when applicability cannot yet be resolved.
    """

    requirement_id: str
    status: AndroidUniverseApplicabilityStatus

    evidence: tuple[
        AndroidUniverseApplicabilityEvidence,
        ...,
    ] = ()

    alternative_group: str | None = None
    selector_key: str | None = None
    selector_value: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement_id,
            str,
        ):
            raise TypeError(
                "requirement_id must be a string"
            )

        if not self.requirement_id:
            raise ValueError(
                "requirement_id must not be empty"
            )

        if not isinstance(
            self.status,
            AndroidUniverseApplicabilityStatus,
        ):
            raise TypeError(
                "status must be an AndroidUniverseApplicabilityStatus"
            )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseApplicabilityEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniverseApplicabilityEvidence"
            )

        for field_name, value in (
            (
                "alternative_group",
                self.alternative_group,
            ),
            (
                "selector_key",
                self.selector_key,
            ),
            (
                "selector_value",
                self.selector_value,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )