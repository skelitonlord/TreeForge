from __future__ import annotations

from collections import defaultdict

from treeforge.android.parsing.art_runtime import (
    AndroidArtRuntimeParsingResult,
    ParsedAndroidArtImage,
    ParsedAndroidOat,
    ParsedAndroidVdex,
)
from treeforge.android.universe.art_runtime.semantics import (
    AndroidUniverseArtRuntimeArtImageOatChecksumResolution,
    AndroidUniverseArtRuntimeArtImageOatChecksumStatus,
    AndroidUniverseArtRuntimeArtImageOatResolution,
    AndroidUniverseArtRuntimeDexChecksumEntry,
    AndroidUniverseArtRuntimeDexChecksumResolution,
    AndroidUniverseArtRuntimeDexChecksumStatus,
    AndroidUniverseArtRuntimeOatVdexResolution,
    AndroidUniverseArtRuntimePeerKey,
    AndroidUniverseArtRuntimePeerStatus,
    AndroidUniverseArtRuntimeVdexDisposition,
    AndroidUniverseArtRuntimeVdexDispositionStatus,
)


class AndroidUniverseArtRuntimeReconciler:
    """
    Reconcile canonical ART-runtime peer and checksum relationships.

    This pass establishes OAT/VDEX peer identity and then reconciles ordered
    DEX checksums only for source-resolved peers. It does not canonicalize
    DEX locations or resolve Classpath/APEX relationships.
    """

    @staticmethod
    def _oat_key(
        oat: ParsedAndroidOat,
    ) -> AndroidUniverseArtRuntimePeerKey:
        path = oat.elf.source.android_path

        return AndroidUniverseArtRuntimePeerKey(
            source_name=(
                oat.elf.source.source_name
            ),
            parent_path=path.parent,
            stem=path.stem,
        )

    @staticmethod
    def _vdex_key(
        vdex: ParsedAndroidVdex,
    ) -> AndroidUniverseArtRuntimePeerKey:
        path = vdex.source.android_path

        return AndroidUniverseArtRuntimePeerKey(
            source_name=vdex.source.source_name,
            parent_path=path.parent,
            stem=path.stem,
        )

    @staticmethod
    def _art_image_key(
        art_image: ParsedAndroidArtImage,
    ) -> AndroidUniverseArtRuntimePeerKey:
        path = art_image.source.android_path

        return AndroidUniverseArtRuntimePeerKey(
            source_name=art_image.source.source_name,
            parent_path=path.parent,
            stem=path.stem,
        )

    @staticmethod
    def reconcile_art_image_oat_checksum(
        peer: AndroidUniverseArtRuntimeArtImageOatResolution,
    ) -> (
        AndroidUniverseArtRuntimeArtImageOatChecksumResolution
    ):
        if not isinstance(
            peer,
            AndroidUniverseArtRuntimeArtImageOatResolution,
        ):
            raise TypeError(
                "peer must be an "
                "AndroidUniverseArtRuntimeArtImageOatResolution"
            )

        if (
            peer.status
            is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
        ):
            raise ValueError(
                "ART image/OAT checksum reconciliation requires "
                "a resolved peer"
            )

        oat = peer.oat

        if oat is None:
            raise ValueError(
                "resolved ART image/OAT peer must carry one OAT"
            )

        if (
            peer.art_image.image_111 is None
            or oat.header is None
        ):
            return (
                AndroidUniverseArtRuntimeArtImageOatChecksumResolution(
                    peer=peer,
                    status=(
                        AndroidUniverseArtRuntimeArtImageOatChecksumStatus
                        .UNSUPPORTED
                    ),
                    art_image_oat_checksum=None,
                    oat_header_checksum=None,
                )
            )

        art_image_oat_checksum = (
            peer.art_image.image_111.oat_checksum
        )

        oat_header_checksum = (
            oat.header.checksum
        )

        status = (
            AndroidUniverseArtRuntimeArtImageOatChecksumStatus.MATCHED
            if (
                art_image_oat_checksum
                == oat_header_checksum
            )
            else (
                AndroidUniverseArtRuntimeArtImageOatChecksumStatus
                .MISMATCH
            )
        )

        return (
            AndroidUniverseArtRuntimeArtImageOatChecksumResolution(
                peer=peer,
                status=status,
                art_image_oat_checksum=art_image_oat_checksum,
                oat_header_checksum=oat_header_checksum,
            )
        )

    @staticmethod
    def reconcile_dex_checksums(
        peer: AndroidUniverseArtRuntimeOatVdexResolution,
    ) -> AndroidUniverseArtRuntimeDexChecksumResolution:
        if not isinstance(
            peer,
            AndroidUniverseArtRuntimeOatVdexResolution,
        ):
            raise TypeError(
                "peer must be an "
                "AndroidUniverseArtRuntimeOatVdexResolution"
            )

        if (
            peer.status
            is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
        ):
            raise ValueError(
                "DEX checksum reconciliation requires a resolved peer"
            )

        oat = peer.oat
        vdex = peer.vdex

        if (
            oat is None
            or vdex is None
        ):
            raise ValueError(
                "resolved peer must carry one OAT and one VDEX"
            )

        if (
            oat.header is None
            or vdex.vdex_027 is None
        ):
            return AndroidUniverseArtRuntimeDexChecksumResolution(
                peer=peer,
                status=(
                    AndroidUniverseArtRuntimeDexChecksumStatus.UNSUPPORTED
                ),
                oat_dex_file_count=(
                    len(
                        oat.header.oat_dex_files
                    )
                    if oat.header is not None
                    else 0
                ),
                vdex_checksum_count=(
                    len(
                        vdex.vdex_027.dex_checksums
                    )
                    if vdex.vdex_027 is not None
                    else 0
                ),
            )

        oat_dex_files = (
            oat.header.oat_dex_files
        )

        vdex_checksums = (
            vdex.vdex_027.dex_checksums
        )

        if len(
            oat_dex_files
        ) != len(
            vdex_checksums
        ):
            return AndroidUniverseArtRuntimeDexChecksumResolution(
                peer=peer,
                status=(
                    AndroidUniverseArtRuntimeDexChecksumStatus
                    .COUNT_MISMATCH
                ),
                oat_dex_file_count=len(
                    oat_dex_files
                ),
                vdex_checksum_count=len(
                    vdex_checksums
                ),
            )

        entries = tuple(
            AndroidUniverseArtRuntimeDexChecksumEntry(
                index=index,
                oat_dex_file=oat_dex_file,
                vdex_checksum=vdex_checksum,
                matches=(
                    oat_dex_file.dex_file_location_checksum
                    == vdex_checksum
                ),
            )
            for (
                index,
                (
                    oat_dex_file,
                    vdex_checksum,
                ),
            )
            in enumerate(
                zip(
                    oat_dex_files,
                    vdex_checksums,
                    strict=True,
                )
            )
        )

        status = (
            AndroidUniverseArtRuntimeDexChecksumStatus.MATCHED
            if all(
                entry.matches
                for entry
                in entries
            )
            else (
                AndroidUniverseArtRuntimeDexChecksumStatus
                .CHECKSUM_MISMATCH
            )
        )

        return AndroidUniverseArtRuntimeDexChecksumResolution(
            peer=peer,
            status=status,
            oat_dex_file_count=len(
                oat_dex_files
            ),
            vdex_checksum_count=len(
                vdex_checksums
            ),
            entries=entries,
        )

    def reconcile(
        self,
        parsing: AndroidArtRuntimeParsingResult,
    ) -> tuple[
        tuple[
            AndroidUniverseArtRuntimeOatVdexResolution,
            ...,
        ],
        tuple[
            AndroidUniverseArtRuntimeVdexDisposition,
            ...,
        ],
        tuple[
            AndroidUniverseArtRuntimeDexChecksumResolution,
            ...,
        ],
        tuple[
            AndroidUniverseArtRuntimeArtImageOatResolution,
            ...,
        ],
        tuple[
            AndroidUniverseArtRuntimeArtImageOatChecksumResolution,
            ...,
        ],
    ]:
        if not isinstance(
            parsing,
            AndroidArtRuntimeParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidArtRuntimeParsingResult"
            )

        vdex_by_key: dict[
            AndroidUniverseArtRuntimePeerKey,
            list[
                ParsedAndroidVdex
            ],
        ] = defaultdict(
            list
        )

        for vdex in parsing.vdex_files:
            vdex_by_key[
                self._vdex_key(
                    vdex
                )
            ].append(
                vdex
            )

        resolutions = []
        consumed_vdex_ids: set[
            tuple
        ] = set()

        for oat in parsing.oat_files:
            key = self._oat_key(
                oat
            )

            candidates = tuple(
                sorted(
                    vdex_by_key.get(
                        key,
                        (),
                    ),
                    key=lambda candidate: (
                        candidate.source.identity_key
                    ),
                )
            )

            if len(
                candidates
            ) == 1:
                status = (
                    AndroidUniverseArtRuntimePeerStatus.RESOLVED
                )

                consumed_vdex_ids.add(
                    candidates[0].source.identity_key
                )

            elif not candidates:
                status = (
                    AndroidUniverseArtRuntimePeerStatus.UNPAIRED
                )

            else:
                status = (
                    AndroidUniverseArtRuntimePeerStatus.AMBIGUOUS
                )

                for candidate in candidates:
                    consumed_vdex_ids.add(
                        candidate.source.identity_key
                    )

            resolutions.append(
                AndroidUniverseArtRuntimeOatVdexResolution(
                    key=key,
                    status=status,
                    oat=oat,
                    vdex_candidates=candidates,
                )
            )

        sorted_resolutions = tuple(
            sorted(
                resolutions,
                key=lambda resolution: (
                    resolution.key.source_name,
                    resolution.key.parent_path.as_posix(),
                    resolution.key.stem,
                ),
            )
        )

        vdex_peer_resolutions = defaultdict(
            list
        )

        for resolution in sorted_resolutions:
            for candidate in resolution.vdex_candidates:
                vdex_peer_resolutions[
                    candidate.source.identity_key
                ].append(
                    resolution
                )

        vdex_dispositions = []

        for vdex in parsing.vdex_files:
            peer_resolutions = tuple(
                vdex_peer_resolutions.get(
                    vdex.source.identity_key,
                    (),
                )
            )

            resolved_peers = tuple(
                resolution
                for resolution
                in peer_resolutions
                if (
                    resolution.status
                    is AndroidUniverseArtRuntimePeerStatus.RESOLVED
                )
            )

            ambiguous_peers = tuple(
                resolution
                for resolution
                in peer_resolutions
                if (
                    resolution.status
                    is AndroidUniverseArtRuntimePeerStatus.AMBIGUOUS
                )
            )

            if len(
                resolved_peers
            ) == 1:
                status = (
                    AndroidUniverseArtRuntimeVdexDispositionStatus
                    .OAT_PEER
                )
                canonical_peers = resolved_peers

            elif ambiguous_peers:
                status = (
                    AndroidUniverseArtRuntimeVdexDispositionStatus
                    .OAT_PEER_CANDIDATE
                )
                canonical_peers = peer_resolutions

            elif not peer_resolutions:
                status = (
                    AndroidUniverseArtRuntimeVdexDispositionStatus
                    .NO_OAT_PEER
                )
                canonical_peers = ()

            else:
                raise ValueError(
                    "VDEX peer evidence has no canonical disposition"
                )

            vdex_dispositions.append(
                AndroidUniverseArtRuntimeVdexDisposition(
                    key=self._vdex_key(
                        vdex
                    ),
                    vdex=vdex,
                    status=status,
                    peer_resolutions=canonical_peers,
                )
            )

        canonical_vdex_dispositions = tuple(
            vdex_dispositions
        )

        dex_checksum_resolutions = tuple(
            self.reconcile_dex_checksums(
                resolution
            )
            for resolution
            in sorted_resolutions
            if (
                resolution.status
                is AndroidUniverseArtRuntimePeerStatus.RESOLVED
            )
        )

        oat_by_key: dict[
            AndroidUniverseArtRuntimePeerKey,
            list[
                ParsedAndroidOat
            ],
        ] = defaultdict(
            list
        )

        for oat in parsing.oat_files:
            oat_by_key[
                self._oat_key(
                    oat
                )
            ].append(
                oat
            )

        art_image_oat_resolutions = []

        for art_image in parsing.art_images:
            key = self._art_image_key(
                art_image
            )

            candidates = tuple(
                sorted(
                    oat_by_key.get(
                        key,
                        (),
                    ),
                    key=lambda candidate: (
                        candidate.elf.source.identity_key
                    ),
                )
            )

            if len(
                candidates
            ) == 1:
                status = (
                    AndroidUniverseArtRuntimePeerStatus.RESOLVED
                )

            elif not candidates:
                status = (
                    AndroidUniverseArtRuntimePeerStatus.UNPAIRED
                )

            else:
                status = (
                    AndroidUniverseArtRuntimePeerStatus.AMBIGUOUS
                )

            art_image_oat_resolutions.append(
                AndroidUniverseArtRuntimeArtImageOatResolution(
                    key=key,
                    status=status,
                    art_image=art_image,
                    oat_candidates=candidates,
                )
            )

        canonical_art_image_oat_resolutions = tuple(
            art_image_oat_resolutions
        )

        art_image_oat_checksum_resolutions = tuple(
            self.reconcile_art_image_oat_checksum(
                resolution
            )
            for resolution
            in canonical_art_image_oat_resolutions
            if (
                resolution.status
                is AndroidUniverseArtRuntimePeerStatus.RESOLVED
            )
        )

        return (
            sorted_resolutions,
            canonical_vdex_dispositions,
            dex_checksum_resolutions,
            canonical_art_image_oat_resolutions,
            art_image_oat_checksum_resolutions,
        )
