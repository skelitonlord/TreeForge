from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.parsing.art_runtime import (
    ParsedAndroidArtImage,
    ParsedAndroidOat,
    ParsedAndroidOatDexFile,
    ParsedAndroidVdex,
)


class AndroidUniverseArtRuntimePeerStatus(
    StrEnum
):
    RESOLVED = "resolved"
    UNPAIRED = "unpaired"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimePeerKey:
    """
    Canonical ART-runtime peer identity.

    The key is derived only from Parsing-owned canonical source identity:
    parser source root + Android-visible parent path + runtime artifact stem.
    """

    source_name: str
    parent_path: PurePosixPath
    stem: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_name,
            str,
        ):
            raise TypeError(
                "source_name must be a string"
            )

        if not self.source_name:
            raise ValueError(
                "source_name must not be empty"
            )

        if not isinstance(
            self.parent_path,
            PurePosixPath,
        ):
            raise TypeError(
                "parent_path must be a PurePosixPath"
            )

        if not self.parent_path.is_absolute():
            raise ValueError(
                "parent_path must be absolute"
            )

        if not isinstance(
            self.stem,
            str,
        ):
            raise TypeError(
                "stem must be a string"
            )

        if not self.stem:
            raise ValueError(
                "stem must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeOatVdexResolution:
    """
    Canonical OAT/VDEX peer relationship.

    This resolution establishes source-level peer identity only.
    DEX checksum reconciliation remains a later ART Runtime Universe step.
    """

    key: AndroidUniverseArtRuntimePeerKey
    status: AndroidUniverseArtRuntimePeerStatus
    oat: ParsedAndroidOat | None
    vdex_candidates: tuple[
        ParsedAndroidVdex,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.key,
            AndroidUniverseArtRuntimePeerKey,
        ):
            raise TypeError(
                "key must be an AndroidUniverseArtRuntimePeerKey"
            )

        if not isinstance(
            self.status,
            AndroidUniverseArtRuntimePeerStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseArtRuntimePeerStatus"
            )

        if (
            self.oat is not None
            and not isinstance(
                self.oat,
                ParsedAndroidOat,
            )
        ):
            raise TypeError(
                "oat must be a ParsedAndroidOat or None"
            )

        if not isinstance(
            self.vdex_candidates,
            tuple,
        ):
            raise TypeError(
                "vdex_candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                ParsedAndroidVdex,
            )
            for candidate
            in self.vdex_candidates
        ):
            raise TypeError(
                "vdex_candidates must contain only "
                "ParsedAndroidVdex objects"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimePeerStatus.RESOLVED
            and (
                self.oat is None
                or len(
                    self.vdex_candidates
                ) != 1
            )
        ):
            raise ValueError(
                "resolved OAT/VDEX peer must contain "
                "one OAT and exactly one VDEX"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimePeerStatus.UNPAIRED
            and self.oat is not None
            and self.vdex_candidates
        ):
            raise ValueError(
                "unpaired OAT must not carry VDEX candidates"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimePeerStatus.AMBIGUOUS
            and len(
                self.vdex_candidates
            ) < 2
        ):
            raise ValueError(
                "ambiguous OAT/VDEX peer must carry "
                "multiple VDEX candidates"
            )

    @property
    def vdex(
        self,
    ) -> ParsedAndroidVdex | None:
        if (
            self.status
            is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
        ):
            return None

        return self.vdex_candidates[0]


class AndroidUniverseArtRuntimeVdexDispositionStatus(
    StrEnum
):
    """
    Intrinsic canonical relationship of one parsed VDEX to the OAT
    population.

    Classpath/APEX interpretation is intentionally not represented here.
    """

    OAT_PEER = "oat_peer"
    OAT_PEER_CANDIDATE = "oat_peer_candidate"
    NO_OAT_PEER = "no_oat_peer"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeVdexDisposition:
    """
    Exact intrinsic disposition of one canonical parsed VDEX source.

    Every ParsedAndroidVdex must receive exactly one disposition.

    ``OAT_PEER`` means the VDEX participates in exactly one resolved
    canonical OAT/VDEX peer.

    ``OAT_PEER_CANDIDATE`` means the VDEX participates in one or more
    ambiguous OAT/VDEX peer candidate sets.

    ``NO_OAT_PEER`` means no canonical OAT peer references the VDEX.
    This does not imply that the VDEX has no other ART/ClassPath role;
    those relationships remain cross-family semantics.
    """

    key: AndroidUniverseArtRuntimePeerKey
    vdex: ParsedAndroidVdex
    status: AndroidUniverseArtRuntimeVdexDispositionStatus

    peer_resolutions: tuple[
        AndroidUniverseArtRuntimeOatVdexResolution,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.key,
            AndroidUniverseArtRuntimePeerKey,
        ):
            raise TypeError(
                "key must be an AndroidUniverseArtRuntimePeerKey"
            )

        if not isinstance(
            self.vdex,
            ParsedAndroidVdex,
        ):
            raise TypeError(
                "vdex must be a ParsedAndroidVdex"
            )

        if not isinstance(
            self.status,
            AndroidUniverseArtRuntimeVdexDispositionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseArtRuntimeVdexDispositionStatus"
            )

        if not isinstance(
            self.peer_resolutions,
            tuple,
        ):
            raise TypeError(
                "peer_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseArtRuntimeOatVdexResolution,
            )
            for resolution
            in self.peer_resolutions
        ):
            raise TypeError(
                "peer_resolutions contains invalid entries"
            )

        for resolution in self.peer_resolutions:
            if not any(
                candidate is self.vdex
                for candidate
                in resolution.vdex_candidates
            ):
                raise ValueError(
                    "VDEX disposition peer resolution must preserve "
                    "exact VDEX candidate identity"
                )

        if (
            self.status
            is AndroidUniverseArtRuntimeVdexDispositionStatus.OAT_PEER
        ):
            if len(
                self.peer_resolutions
            ) != 1:
                raise ValueError(
                    "OAT_PEER VDEX disposition requires exactly one "
                    "peer resolution"
                )

            if (
                self.peer_resolutions[0].status
                is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
            ):
                raise ValueError(
                    "OAT_PEER VDEX disposition requires a resolved "
                    "OAT/VDEX peer"
                )

        elif (
            self.status
            is AndroidUniverseArtRuntimeVdexDispositionStatus
            .OAT_PEER_CANDIDATE
        ):
            if not self.peer_resolutions:
                raise ValueError(
                    "OAT_PEER_CANDIDATE VDEX disposition requires "
                    "at least one peer resolution"
                )

            if not any(
                resolution.status
                is AndroidUniverseArtRuntimePeerStatus.AMBIGUOUS
                for resolution
                in self.peer_resolutions
            ):
                raise ValueError(
                    "OAT_PEER_CANDIDATE requires ambiguous OAT/VDEX "
                    "peer evidence"
                )

        elif self.peer_resolutions:
            raise ValueError(
                "NO_OAT_PEER VDEX disposition must not carry "
                "peer resolutions"
            )

class AndroidUniverseArtRuntimeDexChecksumStatus(
    StrEnum
):
    MATCHED = "matched"
    COUNT_MISMATCH = "count_mismatch"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    UNSUPPORTED = "unsupported"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeDexChecksumEntry:
    """
    One canonical ordered OAT/VDEX DEX checksum comparison.

    Index identity is preserved exactly from the OatDexFile sequence and
    corresponding VDEX checksum sequence.
    """

    index: int
    oat_dex_file: ParsedAndroidOatDexFile
    vdex_checksum: int
    matches: bool

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if not isinstance(
            self.oat_dex_file,
            ParsedAndroidOatDexFile,
        ):
            raise TypeError(
                "oat_dex_file must be a ParsedAndroidOatDexFile"
            )

        if self.oat_dex_file.index != self.index:
            raise ValueError(
                "checksum entry index must preserve OatDexFile index"
            )

        if (
            isinstance(
                self.vdex_checksum,
                bool,
            )
            or not isinstance(
                self.vdex_checksum,
                int,
            )
            or self.vdex_checksum < 0
        ):
            raise ValueError(
                "vdex_checksum must be a non-negative integer"
            )

        if not isinstance(
            self.matches,
            bool,
        ):
            raise TypeError(
                "matches must be a bool"
            )

        if (
            self.matches
            != (
                self.oat_dex_file.dex_file_location_checksum
                == self.vdex_checksum
            )
        ):
            raise ValueError(
                "matches must reflect exact OAT/VDEX checksum equality"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeDexChecksumResolution:
    """
    Ordered DEX checksum reconciliation for one resolved OAT/VDEX peer.

    Source-level peer identity is established before this result. This model
    records only checksum semantics for that already-resolved peer.
    """

    peer: AndroidUniverseArtRuntimeOatVdexResolution
    status: AndroidUniverseArtRuntimeDexChecksumStatus
    oat_dex_file_count: int
    vdex_checksum_count: int
    entries: tuple[
        AndroidUniverseArtRuntimeDexChecksumEntry,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.peer,
            AndroidUniverseArtRuntimeOatVdexResolution,
        ):
            raise TypeError(
                "peer must be an "
                "AndroidUniverseArtRuntimeOatVdexResolution"
            )

        if (
            self.peer.status
            is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
        ):
            raise ValueError(
                "DEX checksum reconciliation requires a resolved "
                "OAT/VDEX peer"
            )

        if not isinstance(
            self.status,
            AndroidUniverseArtRuntimeDexChecksumStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseArtRuntimeDexChecksumStatus"
            )

        for name, value in (
            (
                "oat_dex_file_count",
                self.oat_dex_file_count,
            ),
            (
                "vdex_checksum_count",
                self.vdex_checksum_count,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                AndroidUniverseArtRuntimeDexChecksumEntry,
            )
            for entry
            in self.entries
        ):
            raise TypeError(
                "entries contains invalid checksum entries"
            )

        expected_indices = tuple(
            range(
                len(
                    self.entries
                )
            )
        )

        actual_indices = tuple(
            entry.index
            for entry
            in self.entries
        )

        if actual_indices != expected_indices:
            raise ValueError(
                "checksum entries must preserve canonical ordered indices"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimeDexChecksumStatus.UNSUPPORTED
        ):
            if self.entries:
                raise ValueError(
                    "unsupported checksum resolution must not carry entries"
                )

            return

        if self.oat_dex_file_count != self.vdex_checksum_count:
            if (
                self.status
                is not (
                    AndroidUniverseArtRuntimeDexChecksumStatus
                    .COUNT_MISMATCH
                )
            ):
                raise ValueError(
                    "unequal DEX populations require count_mismatch status"
                )

            if self.entries:
                raise ValueError(
                    "count mismatch must not imply positional checksum "
                    "correspondence"
                )

            return

        if len(
            self.entries
        ) != self.oat_dex_file_count:
            raise ValueError(
                "equal DEX populations must carry one ordered checksum "
                "entry per DEX"
            )

        has_mismatch = any(
            not entry.matches
            for entry
            in self.entries
        )

        expected_status = (
            AndroidUniverseArtRuntimeDexChecksumStatus.CHECKSUM_MISMATCH
            if has_mismatch
            else AndroidUniverseArtRuntimeDexChecksumStatus.MATCHED
        )

        if self.status is not expected_status:
            raise ValueError(
                "checksum resolution status does not match entry evidence"
            )

@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeArtImageOatResolution:
    """
    Canonical ART image/OAT peer relationship.

    Identity is derived from the shared ART Runtime peer key:
    parser source root + Android-visible parent path + artifact stem.
    """

    key: AndroidUniverseArtRuntimePeerKey
    status: AndroidUniverseArtRuntimePeerStatus
    art_image: ParsedAndroidArtImage
    oat_candidates: tuple[
        ParsedAndroidOat,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.key,
            AndroidUniverseArtRuntimePeerKey,
        ):
            raise TypeError(
                "key must be an AndroidUniverseArtRuntimePeerKey"
            )

        if not isinstance(
            self.status,
            AndroidUniverseArtRuntimePeerStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseArtRuntimePeerStatus"
            )

        if not isinstance(
            self.art_image,
            ParsedAndroidArtImage,
        ):
            raise TypeError(
                "art_image must be a ParsedAndroidArtImage"
            )

        if not isinstance(
            self.oat_candidates,
            tuple,
        ):
            raise TypeError(
                "oat_candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                ParsedAndroidOat,
            )
            for candidate
            in self.oat_candidates
        ):
            raise TypeError(
                "oat_candidates must contain only ParsedAndroidOat objects"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimePeerStatus.RESOLVED
            and len(
                self.oat_candidates
            ) != 1
        ):
            raise ValueError(
                "resolved ART image/OAT peer must contain exactly one OAT"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimePeerStatus.UNPAIRED
            and self.oat_candidates
        ):
            raise ValueError(
                "unpaired ART image must not carry OAT candidates"
            )

        if (
            self.status
            is AndroidUniverseArtRuntimePeerStatus.AMBIGUOUS
            and len(
                self.oat_candidates
            ) < 2
        ):
            raise ValueError(
                "ambiguous ART image/OAT peer must carry multiple "
                "OAT candidates"
            )

    @property
    def oat(
        self,
    ) -> ParsedAndroidOat | None:
        if (
            self.status
            is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
        ):
            return None

        return self.oat_candidates[0]


class AndroidUniverseArtRuntimeArtImageOatChecksumStatus(
    StrEnum
):
    MATCHED = "matched"
    MISMATCH = "mismatch"
    UNSUPPORTED = "unsupported"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArtRuntimeArtImageOatChecksumResolution:
    """
    ART image/OAT checksum reconciliation for one resolved peer.

    For supported layouts, ART image image_111.oat_checksum is compared
    exactly against the paired decoded OAT header checksum.
    """

    peer: AndroidUniverseArtRuntimeArtImageOatResolution
    status: AndroidUniverseArtRuntimeArtImageOatChecksumStatus
    art_image_oat_checksum: int | None
    oat_header_checksum: int | None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.peer,
            AndroidUniverseArtRuntimeArtImageOatResolution,
        ):
            raise TypeError(
                "peer must be an "
                "AndroidUniverseArtRuntimeArtImageOatResolution"
            )

        if (
            self.peer.status
            is not AndroidUniverseArtRuntimePeerStatus.RESOLVED
        ):
            raise ValueError(
                "ART image/OAT checksum reconciliation requires "
                "a resolved peer"
            )

        if not isinstance(
            self.status,
            AndroidUniverseArtRuntimeArtImageOatChecksumStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseArtRuntimeArtImageOatChecksumStatus"
            )

        for name, value in (
            (
                "art_image_oat_checksum",
                self.art_image_oat_checksum,
            ),
            (
                "oat_header_checksum",
                self.oat_header_checksum,
            ),
        ):
            if (
                value is not None
                and (
                    isinstance(
                        value,
                        bool,
                    )
                    or not isinstance(
                        value,
                        int,
                    )
                    or value < 0
                )
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer or None"
                )

        if (
            self.status
            is AndroidUniverseArtRuntimeArtImageOatChecksumStatus.UNSUPPORTED
        ):
            if (
                self.art_image_oat_checksum is not None
                or self.oat_header_checksum is not None
            ):
                raise ValueError(
                    "unsupported ART image/OAT checksum resolution must "
                    "not claim decoded checksum evidence"
                )

            return

        if (
            self.art_image_oat_checksum is None
            or self.oat_header_checksum is None
        ):
            raise ValueError(
                "supported ART image/OAT checksum resolution must carry "
                "both checksum values"
            )

        expected_status = (
            AndroidUniverseArtRuntimeArtImageOatChecksumStatus.MATCHED
            if (
                self.art_image_oat_checksum
                == self.oat_header_checksum
            )
            else (
                AndroidUniverseArtRuntimeArtImageOatChecksumStatus
                .MISMATCH
            )
        )

        if self.status is not expected_status:
            raise ValueError(
                "ART image/OAT checksum status does not match evidence"
            )

