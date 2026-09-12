from __future__ import annotations

from treeforge.android.parsing.sflb import (
    AndroidParsedSflbEntry,
)

from treeforge.android.universe.sflb.requirement import (
    AndroidUniverseSflbRequirement,
)
from treeforge.android.universe.boot_firmware_lineage import (
    AndroidUniverseBootFirmwareLineageResolver,
)


class AndroidUniverseSflbInterpreter:
    """
    Promote canonical Parsing-stage SFLB observations into Universe.

    No SFLB container or payload bytes are reopened or reparsed here.
    """

    def interpret(
        self,
        parsing: tuple[
            AndroidParsedSflbEntry,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseSflbRequirement,
        ...,
    ]:
        if not isinstance(
            parsing,
            tuple,
        ):
            raise TypeError(
                "parsing must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidParsedSflbEntry,
            )
            for item in parsing
        ):
            raise TypeError(
                "parsing must contain only "
                "AndroidParsedSflbEntry entries"
            )

        return tuple(
            AndroidUniverseSflbRequirement(
                source=item,
                boot_firmware_lineage=(
                    AndroidUniverseBootFirmwareLineageResolver
                    .resolve_sflb_entry(
                        item.artifact
                    )
                ),
            )
            for item in parsing
        )
