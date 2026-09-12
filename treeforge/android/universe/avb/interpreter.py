from __future__ import annotations

from treeforge.android.parsing.result import (
    ParsedAvbRegion,
    ParsedAvbVbmeta,
)
from treeforge.android.universe.avb.model import (
    AndroidUniverseAvbRegion,
    AndroidUniverseVbmetaRequirement,
)


class AndroidUniverseVbmetaInterpreter:
    """
    Promote the complete literal Parsing-stage VBMeta population into Universe.

    This interpreter performs no AVB byte decoding and no trust-chain
    reconciliation.
    """

    def interpret(
        self,
        parsed: tuple[ParsedAvbVbmeta, ...],
    ) -> tuple[AndroidUniverseVbmetaRequirement, ...]:
        if not isinstance(parsed, tuple):
            raise TypeError(
                "parsed must be a tuple"
            )

        if not all(
            isinstance(item, ParsedAvbVbmeta)
            for item in parsed
        ):
            raise TypeError(
                "parsed must contain only ParsedAvbVbmeta entries"
            )

        return tuple(
            AndroidUniverseVbmetaRequirement(
                source=item,
            )
            for item in parsed
        )


class AndroidUniverseAvbRegionConservator:
    """
    Preserve the complete Parsing AVB-region disposition population.

    Parsing already owns AVB-region classification. Universe records that
    boundary disposition exactly and connects parsed VBMeta regions to the
    exact corresponding Universe VBMeta requirement.

    No AVB bytes, Extraction facts, or region kinds are reinterpreted here.
    """

    def conserve(
        self,
        parsed_regions: tuple[ParsedAvbRegion, ...],
        vbmeta_requirements: tuple[
            AndroidUniverseVbmetaRequirement,
            ...,
        ],
    ) -> tuple[AndroidUniverseAvbRegion, ...]:
        if not isinstance(
            parsed_regions,
            tuple,
        ):
            raise TypeError(
                "parsed_regions must be a tuple"
            )

        if not all(
            isinstance(region, ParsedAvbRegion)
            for region in parsed_regions
        ):
            raise TypeError(
                "parsed_regions must contain only ParsedAvbRegion entries"
            )

        if not isinstance(
            vbmeta_requirements,
            tuple,
        ):
            raise TypeError(
                "vbmeta_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseVbmetaRequirement,
            )
            for requirement in vbmeta_requirements
        ):
            raise TypeError(
                "vbmeta_requirements must contain only "
                "AndroidUniverseVbmetaRequirement entries"
            )

        requirement_by_source_identity = {
            id(requirement.source): requirement
            for requirement in vbmeta_requirements
        }

        if (
            len(requirement_by_source_identity)
            != len(vbmeta_requirements)
        ):
            raise ValueError(
                "Universe VBMeta requirements contain duplicate "
                "Parsing source identity"
            )

        conserved: list[
            AndroidUniverseAvbRegion
        ] = []

        for region in parsed_regions:
            requirement = None

            if region.disposition == "parsed":
                if region.vbmeta is None:
                    raise ValueError(
                        "Parsing produced a parsed AVB region without "
                        "its canonical ParsedAvbVbmeta"
                    )

                requirement = (
                    requirement_by_source_identity.get(
                        id(region.vbmeta)
                    )
                )

                if requirement is None:
                    raise ValueError(
                        "parsed AVB region references a "
                        "ParsedAvbVbmeta absent from the complete "
                        "Universe VBMeta population"
                    )

            conserved.append(
                AndroidUniverseAvbRegion(
                    source=region,
                    vbmeta_requirement=requirement,
                )
            )

        return tuple(conserved)
