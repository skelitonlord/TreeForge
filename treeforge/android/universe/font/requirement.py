from __future__ import annotations

from dataclasses import dataclass
import posixpath

from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
    normalize_metadata_path,
)

from treeforge.android.parsing.font import (
    AndroidFontParsingResult,
    ParsedAndroidFont,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInstalledFontRequirement:
    """
    One canonical installed Android font source.

    ``source_metadata_entry`` represents the exact filesystem node named by
    the Parsing source. It may itself be a regular file or a symlink.

    ``symlink_chain`` preserves every exact canonical symlink metadata entry
    encountered while resolving that logical source.

    ``payload_metadata_entry`` is the final exact regular-file metadata entry
    whose bytes were structurally parsed by Parsing.

    ``artifact`` is the Artifact requirement for that regular-file payload.

    This distinction is required for Reconstruction: an installed alias must
    remain distinguishable from an independent copied font payload.
    """

    source: ParsedAndroidFont

    source_metadata_entry: FilesystemMetadataEntry

    symlink_chain: tuple[
        FilesystemMetadataEntry,
        ...,
    ]

    payload_metadata_entry: FilesystemMetadataEntry

    artifact: AndroidUniverseArtifactRequirement

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidFont,
        ):
            raise TypeError(
                "source must be a ParsedAndroidFont"
            )

        if not isinstance(
            self.source_metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "source_metadata_entry must be a "
                "FilesystemMetadataEntry"
            )

        if not isinstance(
            self.symlink_chain,
            tuple,
        ):
            raise TypeError(
                "symlink_chain must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                FilesystemMetadataEntry,
            )
            for entry in self.symlink_chain
        ):
            raise TypeError(
                "symlink_chain must contain only "
                "FilesystemMetadataEntry values"
            )

        if not isinstance(
            self.payload_metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "payload_metadata_entry must be a "
                "FilesystemMetadataEntry"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        filesystem_source = (
            self.source.source.filesystem_source
        )

        inventory_entry = (
            self.artifact.inventory_entry
        )

        if (
            inventory_entry.artifact
            is not filesystem_source.artifact
        ):
            raise ValueError(
                "installed Font requirement must preserve exact "
                "Parsing filesystem artifact identity"
            )

        canonical_source = (
            inventory_entry
            .result
            .metadata
            .get(
                self.source_metadata_entry.path
            )
        )

        if (
            canonical_source
            is not self.source_metadata_entry
        ):
            raise ValueError(
                "installed Font source metadata must preserve "
                "exact canonical filesystem identity"
            )

        canonical_payload = (
            inventory_entry
            .result
            .metadata
            .get(
                self.payload_metadata_entry.path
            )
        )

        if (
            canonical_payload
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "installed Font payload metadata must preserve "
                "exact canonical filesystem identity"
            )

        if (
            self.payload_metadata_entry.entry_type
            is not FilesystemEntryType.FILE
        ):
            raise ValueError(
                "installed Font payload metadata must resolve "
                "to a regular file"
            )

        if (
            self.artifact.metadata_entry
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "installed Font Artifact requirement must own "
                "the exact resolved regular-file payload"
            )

        if self.symlink_chain:
            if (
                self.symlink_chain[0]
                is not self.source_metadata_entry
            ):
                raise ValueError(
                    "Font symlink chain must begin with the "
                    "exact installed source metadata entry"
                )

            if not all(
                entry.entry_type
                is FilesystemEntryType.SYMLINK
                for entry in self.symlink_chain
            ):
                raise ValueError(
                    "Font symlink chain may contain only "
                    "canonical symlink metadata entries"
                )

        elif (
            self.source_metadata_entry
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "non-symlink Font source must itself be the "
                "resolved payload metadata entry"
            )

    @property
    def is_alias(self) -> bool:
        return bool(
            self.symlink_chain
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFontRequirement:
    """
    Canonical Universe handoff for installed fonts.

    Later ownership/planning/reconstruction stages can preserve, source,
    generate, or otherwise realize each exact installed font without
    rediscovering filesystem files or reparsing font containers.
    """

    source: AndroidFontParsingResult

    fonts: tuple[
        AndroidUniverseInstalledFontRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidFontParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidFontParsingResult"
            )

        if not isinstance(self.fonts, tuple):
            raise TypeError(
                "fonts must be a tuple"
            )

        if len(
            self.fonts
        ) != len(
            self.source.fonts
        ):
            raise ValueError(
                "Font requirement must conserve the complete "
                "Parsing font population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.fonts,
                self.source.fonts,
                strict=True,
            )
        ):
            raise ValueError(
                "Font requirement must preserve exact Parsing "
                "font identity and order"
            )




def _resolve_font_payload_metadata(
    source_metadata_entry: FilesystemMetadataEntry,
    *,
    inventory_entry,
) -> tuple[
    tuple[
        FilesystemMetadataEntry,
        ...,
    ],
    FilesystemMetadataEntry,
]:
    """
    Resolve one canonical filesystem font node to its regular-file payload.

    Resolution uses only canonical filesystem metadata retained by Parsing.
    It does not consult host ``Path.resolve()``, Android logical mount
    namespaces, filenames outside the declared symlink relationship, or any
    external state.
    """

    current = (
        source_metadata_entry
    )

    symlink_chain = []
    seen_paths = set()

    while (
        current.entry_type
        is FilesystemEntryType.SYMLINK
    ):
        if current.path in seen_paths:
            raise ValueError(
                "Font symlink loop detected at "
                f"{current.path}"
            )

        seen_paths.add(
            current.path
        )

        symlink_chain.append(
            current
        )

        target = (
            current.symlink_target
        )

        if (
            not isinstance(
                target,
                str,
            )
            or not target
        ):
            raise ValueError(
                "Font symlink is missing a canonical target: "
                f"{current.path}"
            )

        if target.startswith("/"):
            target_path = (
                normalize_metadata_path(
                    target
                )
            )
        else:
            target_path = (
                normalize_metadata_path(
                    posixpath.join(
                        posixpath.dirname(
                            current.path
                        ),
                        target,
                    )
                )
            )

        target_entry = (
            inventory_entry
            .result
            .metadata
            .get(
                target_path
            )
        )

        if target_entry is None:
            raise ValueError(
                "Font symlink target is not represented by "
                "canonical filesystem metadata: "
                f"{current.path} -> {target_path}"
            )

        current = (
            target_entry
        )

    if (
        current.entry_type
        is not FilesystemEntryType.FILE
    ):
        raise ValueError(
            "Font source resolves to a non-file filesystem "
            "entry: "
            f"{source_metadata_entry.path} -> "
            f"{current.path} "
            f"type={current.entry_type.value}"
        )

    return (
        tuple(
            symlink_chain
        ),
        current,
    )


def _artifact_for_font(
    source: ParsedAndroidFont,
    *,
    artifact_requirements: (
        AndroidUniverseArtifactRequirementInventory
    ),
) -> tuple[
    FilesystemMetadataEntry,
    tuple[
        FilesystemMetadataEntry,
        ...,
    ],
    FilesystemMetadataEntry,
    AndroidUniverseArtifactRequirement,
]:
    """
    Reconcile one parsed installed Font source.

    The logical source node and the physical payload are intentionally
    distinct. A regular source resolves to itself. A symlink source retains
    its complete canonical alias chain and resolves to the Artifact
    requirement owned by the final regular-file target.
    """

    filesystem_source = (
        source.source.filesystem_source
    )

    try:
        inventory_entry = (
            artifact_requirements
            .source_inventory
            .entry_for_artifact(
                filesystem_source.artifact
            )
        )
    except KeyError as error:
        raise ValueError(
            "Font Parsing filesystem source does not preserve a "
            "canonical Filesystem Metadata artifact identity: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()}"
        ) from error

    try:
        source_metadata_path = (
            inventory_entry
            .filesystem_path_for_materialized_path(
                source.source.host_path
            )
        )
    except ValueError as error:
        raise ValueError(
            "Font Parsing host path does not belong to its "
            "exact canonical filesystem artifact: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()}"
        ) from error

    source_metadata_entry = (
        inventory_entry
        .result
        .metadata
        .get(
            source_metadata_path
        )
    )

    if source_metadata_entry is None:
        raise ValueError(
            "Font Parsing source does not map to canonical "
            "filesystem metadata: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()} "
            f"-> {source_metadata_path}"
        )

    (
        symlink_chain,
        payload_metadata_entry,
    ) = _resolve_font_payload_metadata(
        source_metadata_entry,
        inventory_entry=(
            inventory_entry
        ),
    )

    matches = tuple(
        requirement
        for requirement
        in artifact_requirements.requirements
        if (
            requirement.inventory_entry
            is inventory_entry
            and requirement.metadata_entry
            is payload_metadata_entry
        )
    )

    if len(matches) != 1:
        raise ValueError(
            "Resolved Font payload must reconcile to exactly "
            "one canonical Artifact requirement: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()} "
            f"source={source_metadata_entry.path} "
            f"payload={payload_metadata_entry.path} "
            f"matches={len(matches)}"
        )

    return (
        source_metadata_entry,
        symlink_chain,
        payload_metadata_entry,
        matches[0],
    )

class AndroidUniverseFontInterpreter:
    def interpret(
        self,
        parsing: AndroidFontParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseFontRequirement:
        if not isinstance(
            parsing,
            AndroidFontParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidFontParsingResult"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        fonts = []

        for source in parsing.fonts:
            (
                source_metadata_entry,
                symlink_chain,
                payload_metadata_entry,
                artifact,
            ) = _artifact_for_font(
                source,
                artifact_requirements=(
                    artifact_requirements
                ),
            )

            fonts.append(
                AndroidUniverseInstalledFontRequirement(
                    source=source,
                    source_metadata_entry=(
                        source_metadata_entry
                    ),
                    symlink_chain=(
                        symlink_chain
                    ),
                    payload_metadata_entry=(
                        payload_metadata_entry
                    ),
                    artifact=artifact,
                )
            )

        fonts = tuple(
            fonts
        )

        return AndroidUniverseFontRequirement(
            source=parsing,
            fonts=fonts,
        )
