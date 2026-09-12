from __future__ import annotations

from treeforge.android.parsing.bmp import (
    AndroidParsedBmp,
)
from treeforge.android.universe.bmp.requirement import (
    AndroidUniverseBmpRequirement,
)
from treeforge.android.universe.boot_firmware_lineage import (
    AndroidUniverseBootFirmwareLineageResolver,
)


class AndroidUniverseBmpInterpreter:
    """
    Promote canonical Parsing BMP evidence into Universe requirements.

    This interpreter performs no filename-, device-, Android-version-, or
    resource-role inference. It preserves the complete Parsing population and
    exact source identities.
    """

    def interpret(
        self,
        parsed: tuple[
            AndroidParsedBmp,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseBmpRequirement,
        ...,
    ]:
        if not isinstance(
            parsed,
            tuple,
        ):
            raise TypeError(
                "parsed must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidParsedBmp,
            )
            for item in parsed
        ):
            raise TypeError(
                "parsed must contain only AndroidParsedBmp entries"
            )

        return tuple(
            AndroidUniverseBmpRequirement(
                source=item,
                boot_firmware_lineage=(
                    AndroidUniverseBootFirmwareLineageResolver
                    .resolve_sflb_bmp(
                        item.artifact
                    )
                ),
            )
            for item in parsed
        )
