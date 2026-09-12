from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.result import (
    ParsedBootloaderChildDisposition,
)
from treeforge.android.universe.bootloader.requirement import (
    AndroidUniverseBootloaderRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootloaderChildDisposition:
    """
    Universe accounting for one exact Parsing bootloader-child disposition.

    Parsed children retain their exact semantic requirement. Opaque children
    intentionally retain no fabricated requirement.
    """

    source: ParsedBootloaderChildDisposition
    requirement: AndroidUniverseBootloaderRequirement | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedBootloaderChildDisposition,
        ):
            raise TypeError(
                "source must be a ParsedBootloaderChildDisposition"
            )

        if self.source.disposition == "parsed":
            if self.requirement is None:
                raise ValueError(
                    "parsed bootloader child must retain its "
                    "Universe requirement"
                )

            if (
                self.requirement.source
                is not self.source.parsed
            ):
                raise ValueError(
                    "parsed bootloader disposition must preserve "
                    "exact ParsedBootloaderChild identity"
                )

            if (
                self.requirement.artifact
                is not self.source.artifact
            ):
                raise ValueError(
                    "parsed bootloader disposition must preserve "
                    "exact Extraction artifact identity"
                )

        elif self.source.disposition == "opaque":
            if self.requirement is not None:
                raise ValueError(
                    "opaque bootloader child must not gain an "
                    "invented semantic requirement"
                )

        else:
            raise ValueError(
                "unsupported bootloader child disposition"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootloaderPopulationReconciliation:
    source: tuple[
        ParsedBootloaderChildDisposition,
        ...,
    ]

    entries: tuple[
        AndroidUniverseBootloaderChildDisposition,
        ...,
    ]

    def __post_init__(self) -> None:
        if len(
            self.entries
        ) != len(
            self.source
        ):
            raise ValueError(
                "bootloader population reconciliation must conserve "
                "every Parsing disposition"
            )

        if not all(
            entry.source is source
            for entry, source
            in zip(
                self.entries,
                self.source,
                strict=True,
            )
        ):
            raise ValueError(
                "bootloader population reconciliation must preserve "
                "exact Parsing disposition identity and order"
            )


class AndroidUniverseBootloaderPopulationReconciler:
    def reconcile(
        self,
        parsing: tuple[
            ParsedBootloaderChildDisposition,
            ...,
        ],
        requirements: tuple[
            AndroidUniverseBootloaderRequirement,
            ...,
        ],
    ) -> AndroidUniverseBootloaderPopulationReconciliation:
        requirement_by_source_id = {
            id(requirement.source): requirement
            for requirement
            in requirements
        }

        entries = []

        for disposition in parsing:
            requirement = None

            if disposition.disposition == "parsed":
                requirement = (
                    requirement_by_source_id.get(
                        id(
                            disposition.parsed
                        )
                    )
                )

                if requirement is None:
                    raise ValueError(
                        "parsed bootloader disposition has no exact "
                        "canonical Universe requirement"
                    )

            entries.append(
                AndroidUniverseBootloaderChildDisposition(
                    source=disposition,
                    requirement=requirement,
                )
            )

        consumed_requirement_ids = {
            id(entry.requirement)
            for entry
            in entries
            if entry.requirement is not None
        }

        expected_requirement_ids = {
            id(requirement)
            for requirement
            in requirements
        }

        if (
            consumed_requirement_ids
            != expected_requirement_ids
        ):
            raise ValueError(
                "bootloader disposition reconciliation must cover "
                "every structured Universe requirement exactly once"
            )

        return AndroidUniverseBootloaderPopulationReconciliation(
            source=parsing,
            entries=tuple(
                entries
            ),
        )
