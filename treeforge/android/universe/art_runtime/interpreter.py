from __future__ import annotations

from treeforge.android.parsing.art_runtime import (
    AndroidArtRuntimeParsingResult,
)
from treeforge.android.universe.art_runtime.reconciler import (
    AndroidUniverseArtRuntimeReconciler,
)
from treeforge.android.universe.art_runtime.requirement import (
    AndroidUniverseArtRuntimeRequirement,
)


class AndroidUniverseArtRuntimeInterpreter:
    """Promote canonical ART Runtime Parsing into Android Device Universe."""

    def __init__(
        self,
        *,
        reconciler: AndroidUniverseArtRuntimeReconciler | None = None,
    ) -> None:
        self.reconciler = (
            reconciler
            if reconciler is not None
            else AndroidUniverseArtRuntimeReconciler()
        )

    def interpret(
        self,
        parsing: AndroidArtRuntimeParsingResult,
    ) -> AndroidUniverseArtRuntimeRequirement:
        if not isinstance(
            parsing,
            AndroidArtRuntimeParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidArtRuntimeParsingResult"
            )

        (
            oat_vdex_resolutions,
            vdex_dispositions,
            dex_checksum_resolutions,
            art_image_oat_resolutions,
            art_image_oat_checksum_resolutions,
        ) = self.reconciler.reconcile(
            parsing
        )

        return AndroidUniverseArtRuntimeRequirement(
            source=parsing,
            oat_vdex_resolutions=(
                oat_vdex_resolutions
            ),
            vdex_dispositions=(
                vdex_dispositions
            ),
            dex_checksum_resolutions=(
                dex_checksum_resolutions
            ),
            art_image_oat_resolutions=(
                art_image_oat_resolutions
            ),
            art_image_oat_checksum_resolutions=(
                art_image_oat_checksum_resolutions
            ),
        )
