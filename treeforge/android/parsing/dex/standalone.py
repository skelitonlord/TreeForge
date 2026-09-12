from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.dex.model import (
    AndroidDexSource,
    AndroidDexSourceKind,
    ParsedAndroidDex,
)
from treeforge.android.parsing.dex.parser import (
    AndroidDexParser,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


class AndroidStandaloneDexDispositionKind(
    StrEnum
):
    PARSED = "parsed"
    UNSUPPORTED_COMPACT_DEX = "unsupported_compact_dex"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidStandaloneDexDisposition:
    """
    Exact Parsing disposition for one canonical filesystem DEX-family source.

    Every AndroidModelSourceKind.DEX source is retained exactly once here.
    Standard DEX is decoded structurally. CompactDex remains explicit,
    preserved canonical evidence until a generic CompactDex parser exists.
    """

    source: AndroidModelSource
    disposition: AndroidStandaloneDexDispositionKind
    parsed: ParsedAndroidDex | None = None
    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.source.kind
            is not AndroidModelSourceKind.DEX
        ):
            raise ValueError(
                "standalone DEX disposition source must use DEX kind"
            )

        if not isinstance(
            self.disposition,
            AndroidStandaloneDexDispositionKind,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidStandaloneDexDispositionKind"
            )

        if (
            self.disposition
            is AndroidStandaloneDexDispositionKind.PARSED
        ):
            if not isinstance(
                self.parsed,
                ParsedAndroidDex,
            ):
                raise ValueError(
                    "parsed standalone DEX disposition requires "
                    "ParsedAndroidDex"
                )

            if self.parsed.source.kind is not (
                AndroidDexSourceKind.STANDALONE
            ):
                raise ValueError(
                    "parsed standalone DEX must use STANDALONE provenance"
                )

            if self.parsed.source.parent is not self.source:
                raise ValueError(
                    "parsed standalone DEX must preserve exact canonical "
                    "AndroidModelSource parent identity"
                )

            if (
                self.parsed.source.parent_source_name
                != self.source.source_name
                or self.parsed.source.parent_android_path
                != self.source.android_path
            ):
                raise ValueError(
                    "parsed standalone DEX stable parent identity mismatch"
                )

            if self.reason is not None:
                raise ValueError(
                    "parsed standalone DEX must not carry a reason"
                )

        else:
            if self.parsed is not None:
                raise ValueError(
                    "unsupported CompactDex disposition must not "
                    "carry ParsedAndroidDex"
                )

            if (
                not isinstance(
                    self.reason,
                    str,
                )
                or not self.reason
            ):
                raise ValueError(
                    "unsupported CompactDex disposition requires "
                    "a non-empty reason"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidStandaloneDexParsingResult:
    """
    Complete deterministic population of canonical standalone DEX-family
    filesystem sources.
    """

    dispositions: tuple[
        AndroidStandaloneDexDisposition,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.dispositions,
            tuple,
        ):
            raise TypeError(
                "dispositions must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidStandaloneDexDisposition,
            )
            for value in self.dispositions
        ):
            raise TypeError(
                "dispositions must contain only "
                "AndroidStandaloneDexDisposition values"
            )

        canonical = tuple(
            sorted(
                self.dispositions,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if canonical != self.dispositions:
            raise ValueError(
                "standalone DEX dispositions must use canonical source order"
            )

        source_ids = tuple(
            id(
                value.source
            )
            for value
            in self.dispositions
        )

        if len(
            source_ids
        ) != len(
            set(
                source_ids
            )
        ):
            raise ValueError(
                "standalone DEX dispositions must not duplicate "
                "canonical AndroidModelSource objects"
            )

    @property
    def sources(
        self,
    ) -> tuple[
        AndroidModelSource,
        ...,
    ]:
        return tuple(
            value.source
            for value
            in self.dispositions
        )

    @property
    def dex_files(
        self,
    ) -> tuple[
        ParsedAndroidDex,
        ...,
    ]:
        return tuple(
            value.parsed
            for value
            in self.dispositions
            if value.parsed is not None
        )

    @property
    def source_count(
        self,
    ) -> int:
        return len(
            self.dispositions
        )

    @property
    def parsed_count(
        self,
    ) -> int:
        return len(
            self.dex_files
        )

    @property
    def compact_dex_count(
        self,
    ) -> int:
        return sum(
            1
            for value
            in self.dispositions
            if (
                value.disposition
                is AndroidStandaloneDexDispositionKind
                .UNSUPPORTED_COMPACT_DEX
            )
        )

    @property
    def unresolved_count(
        self,
    ) -> int:
        #
        # CompactDex is explicitly dispositioned, not silently unresolved.
        #
        return 0


class AndroidStandaloneDexParser:
    """
    Parse canonical filesystem-backed DEX-family sources.

    Standard DEX is decoded using the generic byte-oriented DEX parser.
    CompactDex is retained with an explicit unsupported disposition rather
    than silently omitted or treated as malformed standard DEX.
    """

    def __init__(
        self,
        *,
        dex_parser: AndroidDexParser | None = None,
    ) -> None:
        self.dex_parser = (
            dex_parser
            if dex_parser is not None
            else AndroidDexParser()
        )

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidStandaloneDexParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source
            in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.DEX
            )
        )

        dispositions = []

        for source in sources:
            suffix = (
                source.android_path
                .suffix
                .lower()
            )

            if suffix == ".cdex":
                dispositions.append(
                    AndroidStandaloneDexDisposition(
                        source=source,
                        disposition=(
                            AndroidStandaloneDexDispositionKind
                            .UNSUPPORTED_COMPACT_DEX
                        ),
                        reason=(
                            "CompactDex source is preserved as canonical "
                            "Parsing evidence; generic CompactDex structural "
                            "decoding is not implemented"
                        ),
                    )
                )
                continue

            if suffix != ".dex":
                raise ValueError(
                    "canonical DEX source has unsupported suffix: "
                    f"{suffix!r}"
                )

            payload = (
                source.host_path
                .read_bytes()
            )

            parsed = self.dex_parser.parse(
                payload=payload,
                source=AndroidDexSource(
                    kind=(
                        AndroidDexSourceKind.STANDALONE
                    ),
                    parent=source,
                    parent_source_name=(
                        source.source_name
                    ),
                    parent_android_path=(
                        source.android_path
                    ),
                ),
            )

            dispositions.append(
                AndroidStandaloneDexDisposition(
                    source=source,
                    disposition=(
                        AndroidStandaloneDexDispositionKind.PARSED
                    ),
                    parsed=parsed,
                )
            )

        result = AndroidStandaloneDexParsingResult(
            dispositions=tuple(
                sorted(
                    dispositions,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            )
        )

        expected_source_ids = {
            id(
                source
            )
            for source
            in sources
        }

        observed_source_ids = {
            id(
                source
            )
            for source
            in result.sources
        }

        if (
            expected_source_ids
            != observed_source_ids
        ):
            raise ValueError(
                "standalone DEX Parsing failed to conserve every "
                "canonical DEX source exactly once"
            )

        if (
            len(
                result.dispositions
            )
            != len(
                sources
            )
        ):
            raise ValueError(
                "standalone DEX Parsing must retain one disposition "
                "per canonical DEX source"
            )

        return result
