from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.art_runtime import (
    AndroidArtRuntimeParsingResult,
)
from treeforge.android.universe.art_runtime.semantics import (
    AndroidUniverseArtRuntimeArtImageOatChecksumResolution,
    AndroidUniverseArtRuntimeArtImageOatResolution,
    AndroidUniverseArtRuntimeDexChecksumResolution,
    AndroidUniverseArtRuntimeOatVdexResolution,
    AndroidUniverseArtRuntimePeerStatus,
    AndroidUniverseArtRuntimeVdexDisposition,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeRequirement:
    """
    Canonical ART Runtime Universe requirement.

    Parsing identity is preserved exactly while Universe adds semantic
    reconciliation relationships between runtime artifacts.
    """

    source: AndroidArtRuntimeParsingResult

    oat_vdex_resolutions: tuple[
        AndroidUniverseArtRuntimeOatVdexResolution,
        ...,
    ] = ()

    vdex_dispositions: tuple[
        AndroidUniverseArtRuntimeVdexDisposition,
        ...,
    ] = ()

    dex_checksum_resolutions: tuple[
        AndroidUniverseArtRuntimeDexChecksumResolution,
        ...,
    ] = ()

    art_image_oat_resolutions: tuple[
        AndroidUniverseArtRuntimeArtImageOatResolution,
        ...,
    ] = ()

    art_image_oat_checksum_resolutions: tuple[
        AndroidUniverseArtRuntimeArtImageOatChecksumResolution,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidArtRuntimeParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidArtRuntimeParsingResult"
            )

        if not isinstance(
            self.oat_vdex_resolutions,
            tuple,
        ):
            raise TypeError(
                "oat_vdex_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseArtRuntimeOatVdexResolution,
            )
            for resolution
            in self.oat_vdex_resolutions
        ):
            raise TypeError(
                "oat_vdex_resolutions contains invalid entries"
            )

        if len(
            self.oat_vdex_resolutions
        ) != len(
            self.source.oat_files
        ):
            raise ValueError(
                "every parsed OAT must have exactly one "
                "Universe OAT/VDEX resolution"
            )

        if not isinstance(
            self.vdex_dispositions,
            tuple,
        ):
            raise TypeError(
                "vdex_dispositions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseArtRuntimeVdexDisposition,
            )
            for item
            in self.vdex_dispositions
        ):
            raise TypeError(
                "vdex_dispositions contains invalid entries"
            )

        if len(
            self.vdex_dispositions
        ) != len(
            self.source.vdex_files
        ):
            raise ValueError(
                "every parsed VDEX must have exactly one "
                "Universe VDEX disposition"
            )

        if tuple(
            item.vdex
            for item
            in self.vdex_dispositions
        ) != self.source.vdex_files:
            raise ValueError(
                "VDEX dispositions must preserve exact parsed "
                "VDEX identity and canonical order"
            )

        vdex_identity_keys = tuple(
            item.vdex.source.identity_key
            for item
            in self.vdex_dispositions
        )

        if len(
            vdex_identity_keys
        ) != len(
            set(
                vdex_identity_keys
            )
        ):
            raise ValueError(
                "VDEX dispositions must preserve unique canonical "
                "VDEX source identities"
            )

        if not isinstance(
            self.dex_checksum_resolutions,
            tuple,
        ):
            raise TypeError(
                "dex_checksum_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseArtRuntimeDexChecksumResolution,
            )
            for resolution
            in self.dex_checksum_resolutions
        ):
            raise TypeError(
                "dex_checksum_resolutions contains invalid entries"
            )

        resolved_peers = tuple(
            resolution
            for resolution
            in self.oat_vdex_resolutions
            if (
                resolution.status
                is AndroidUniverseArtRuntimePeerStatus.RESOLVED
            )
        )

        if len(
            self.dex_checksum_resolutions
        ) != len(
            resolved_peers
        ):
            raise ValueError(
                "every resolved OAT/VDEX peer must have exactly one "
                "DEX checksum resolution"
            )

        if tuple(
            item.peer
            for item
            in self.dex_checksum_resolutions
        ) != resolved_peers:
            raise ValueError(
                "DEX checksum resolutions must preserve resolved peer "
                "identity and canonical order"
            )

        if not isinstance(
            self.art_image_oat_resolutions,
            tuple,
        ):
            raise TypeError(
                "art_image_oat_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseArtRuntimeArtImageOatResolution,
            )
            for resolution
            in self.art_image_oat_resolutions
        ):
            raise TypeError(
                "art_image_oat_resolutions contains invalid entries"
            )

        if len(
            self.art_image_oat_resolutions
        ) != len(
            self.source.art_images
        ):
            raise ValueError(
                "every parsed ART image must have exactly one "
                "Universe ART image/OAT resolution"
            )

        if tuple(
            item.art_image
            for item
            in self.art_image_oat_resolutions
        ) != self.source.art_images:
            raise ValueError(
                "ART image/OAT resolutions must preserve canonical "
                "ART image identity and order"
            )

        if not isinstance(
            self.art_image_oat_checksum_resolutions,
            tuple,
        ):
            raise TypeError(
                "art_image_oat_checksum_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseArtRuntimeArtImageOatChecksumResolution,
            )
            for resolution
            in self.art_image_oat_checksum_resolutions
        ):
            raise TypeError(
                "art_image_oat_checksum_resolutions contains "
                "invalid entries"
            )

        resolved_art_image_oat_peers = tuple(
            resolution
            for resolution
            in self.art_image_oat_resolutions
            if (
                resolution.status
                is AndroidUniverseArtRuntimePeerStatus.RESOLVED
            )
        )

        if len(
            self.art_image_oat_checksum_resolutions
        ) != len(
            resolved_art_image_oat_peers
        ):
            raise ValueError(
                "every resolved ART image/OAT peer must have exactly "
                "one checksum resolution"
            )

        if tuple(
            item.peer
            for item
            in self.art_image_oat_checksum_resolutions
        ) != resolved_art_image_oat_peers:
            raise ValueError(
                "ART image/OAT checksum resolutions must preserve "
                "resolved peer identity and canonical order"
            )
