from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeDerivedSelinuxSource:
    """
    One SELinux source-language file synthesized by Device Tree from
    canonical effective SELinux semantics.

    This is deliberately not Reconstruction source content.

    Reconstruction preserves the exact upstream source/runtime artifact
    identity. Device Tree may derive a new source-tree representation when
    canonical semantics are sufficient to express equivalent Android build
    input.

    ``source_requirement_id`` identifies the canonical SELinux requirement
    whose semantics justify this derived source.

    ``source_representation_id`` preserves the exact Reconstruction
    representation from which Device Tree derived the build realization.

    ``contributing_cil_requirement_ids`` records the exact canonical CIL
    semantic requirements admitted into this generated source file.
    """

    derived_source_id: str
    destination: PurePosixPath
    text: str

    source_requirement_id: str
    source_representation_id: str

    contributing_cil_requirement_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("derived_source_id", self.derived_source_id),
            ("source_requirement_id", self.source_requirement_id),
            (
                "source_representation_id",
                self.source_representation_id,
            ),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "destination must be relative to the "
                "Device Tree workspace"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape the "
                "Device Tree workspace"
            )

        if not isinstance(self.text, str) or not self.text:
            raise ValueError(
                "text must be a non-empty string"
            )

        if not self.text.endswith("\n"):
            raise ValueError(
                "derived SELinux source text must end with a newline"
            )

        if not isinstance(
            self.contributing_cil_requirement_ids,
            tuple,
        ):
            raise TypeError(
                "contributing_cil_requirement_ids must be a tuple"
            )

        if not all(
            isinstance(value, str) and value
            for value
            in self.contributing_cil_requirement_ids
        ):
            raise ValueError(
                "contributing_cil_requirement_ids must contain "
                "only non-empty strings"
            )

        if len(
            self.contributing_cil_requirement_ids
        ) != len(
            set(self.contributing_cil_requirement_ids)
        ):
            raise ValueError(
                "contributing_cil_requirement_ids must be unique"
            )

        if (
            self.contributing_cil_requirement_ids
            != tuple(
                sorted(
                    self.contributing_cil_requirement_ids
                )
            )
        ):
            raise ValueError(
                "contributing_cil_requirement_ids must use "
                "deterministic ordering"
            )
