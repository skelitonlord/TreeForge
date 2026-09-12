from __future__ import annotations

from dataclasses import dataclass
import posixpath

from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
    normalize_metadata_path,
)
from treeforge.android.parsing.dex import (
    AndroidDexSourceKind,
    AndroidStandaloneDexDisposition,
    AndroidStandaloneDexDispositionKind,
    AndroidStandaloneDexParsingResult,
    ParsedAndroidDex,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseStandaloneDexRequirement:
    """
    One canonical filesystem-backed standalone DEX-family source.

    This requirement owns only Parsing's standalone DEX population.

    APK-member, Java-archive-member, and VDEX-contained DEX payloads remain
    owned by their existing canonical container populations and are not
    duplicated here.

    ``source_metadata_entry`` preserves the logical installed filesystem node.
    ``payload_metadata_entry`` preserves the final regular file whose bytes
    Parsing consumed. ``symlink_chain`` retains any canonical alias lineage
    between those nodes.

    No package, classpath, ART-runtime, or reconstruction relationship is
    inferred merely from names, paths, DEX signatures, or payload similarity.
    """

    source: AndroidStandaloneDexDisposition

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
            AndroidStandaloneDexDisposition,
        ):
            raise TypeError(
                "source must be an AndroidStandaloneDexDisposition"
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
            for entry
            in self.symlink_chain
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

        if (
            self.payload_metadata_entry.entry_type
            is not FilesystemEntryType.FILE
        ):
            raise ValueError(
                "standalone DEX payload must resolve to a regular file"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        model_source = (
            self.source.source
        )

        if (
            self.artifact.inventory_entry.artifact
            is not model_source.filesystem_source.artifact
        ):
            raise ValueError(
                "standalone DEX requirement must preserve exact "
                "Parsing filesystem artifact identity"
            )

        metadata = (
            self.artifact.inventory_entry
            .result
            .metadata
        )

        if (
            metadata.get(
                self.source_metadata_entry.path
            )
            is not self.source_metadata_entry
        ):
            raise ValueError(
                "standalone DEX logical source metadata must preserve "
                "exact canonical filesystem identity"
            )

        if (
            metadata.get(
                self.payload_metadata_entry.path
            )
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "standalone DEX payload metadata must preserve "
                "exact canonical filesystem identity"
            )

        if (
            self.artifact.metadata_entry
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "standalone DEX Artifact must own the exact "
                "regular-file payload metadata entry"
            )

        if self.symlink_chain:
            if (
                self.symlink_chain[0]
                is not self.source_metadata_entry
            ):
                raise ValueError(
                    "standalone DEX symlink chain must begin with "
                    "the exact logical source metadata entry"
                )

            if not all(
                entry.entry_type
                is FilesystemEntryType.SYMLINK
                for entry
                in self.symlink_chain
            ):
                raise ValueError(
                    "standalone DEX symlink chain may contain only "
                    "canonical symlink entries"
                )

        elif (
            self.source_metadata_entry
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "non-symlink standalone DEX source must itself "
                "be the payload metadata entry"
            )

        if (
            self.source.disposition
            is AndroidStandaloneDexDispositionKind.PARSED
        ):
            parsed = (
                self.source.parsed
            )

            if not isinstance(
                parsed,
                ParsedAndroidDex,
            ):
                raise ValueError(
                    "parsed standalone DEX requirement must retain "
                    "ParsedAndroidDex"
                )

            if (
                parsed.source.kind
                is not AndroidDexSourceKind.STANDALONE
            ):
                raise ValueError(
                    "parsed standalone DEX must preserve "
                    "STANDALONE DEX provenance"
                )

            if (
                parsed.source.parent
                is not model_source
            ):
                raise ValueError(
                    "parsed standalone DEX must preserve exact "
                    "AndroidModelSource parent identity"
                )

        elif (
            self.source.disposition
            is AndroidStandaloneDexDispositionKind
            .UNSUPPORTED_COMPACT_DEX
        ):
            if (
                self.source.parsed
                is not None
            ):
                raise ValueError(
                    "unsupported CompactDex must not carry a "
                    "ParsedAndroidDex"
                )

        else:
            raise ValueError(
                "unsupported standalone DEX Parsing disposition: "
                f"{self.source.disposition!r}"
            )

    @property
    def parsed_dex(
        self,
    ) -> ParsedAndroidDex | None:
        return self.source.parsed

    @property
    def is_compact_dex(
        self,
    ) -> bool:
        return (
            self.source.disposition
            is AndroidStandaloneDexDispositionKind
            .UNSUPPORTED_COMPACT_DEX
        )

    @property
    def is_alias(
        self,
    ) -> bool:
        return bool(
            self.symlink_chain
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseStandaloneDexPopulationRequirement:
    """
    Complete Universe ownership of Parsing's standalone DEX-family population.

    The requirement may legitimately be empty on a device with no standalone
    filesystem DEX sources.

    Empty population does not mean DEX is absent from the device: DEX payloads
    owned by APK, Java archive, or ART/VDEX populations remain represented by
    those canonical owners.
    """

    source: AndroidStandaloneDexParsingResult

    requirements: tuple[
        AndroidUniverseStandaloneDexRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidStandaloneDexParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidStandaloneDexParsingResult"
            )

        if not isinstance(
            self.requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseStandaloneDexRequirement,
            )
            for requirement
            in self.requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseStandaloneDexRequirement values"
            )

        if (
            len(
                self.requirements
            )
            != len(
                self.source.dispositions
            )
        ):
            raise ValueError(
                "standalone DEX Universe requirement must conserve "
                "the complete Parsing disposition population"
            )

        if not all(
            requirement.source
            is disposition
            for requirement, disposition
            in zip(
                self.requirements,
                self.source.dispositions,
                strict=True,
            )
        ):
            raise ValueError(
                "standalone DEX Universe requirement must preserve "
                "exact Parsing disposition identity and order"
            )

        source_ids = tuple(
            id(
                requirement.source.source
            )
            for requirement
            in self.requirements
        )

        if (
            len(
                source_ids
            )
            != len(
                set(
                    source_ids
                )
            )
        ):
            raise ValueError(
                "standalone DEX Universe requirements must not "
                "duplicate canonical AndroidModelSource objects"
            )

    @property
    def source_count(
        self,
    ) -> int:
        return len(
            self.requirements
        )

    @property
    def parsed_count(
        self,
    ) -> int:
        return sum(
            1
            for requirement
            in self.requirements
            if (
                requirement.source.disposition
                is AndroidStandaloneDexDispositionKind.PARSED
            )
        )

    @property
    def compact_dex_count(
        self,
    ) -> int:
        return sum(
            1
            for requirement
            in self.requirements
            if requirement.is_compact_dex
        )


def _resolve_payload_metadata(
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
    current = (
        source_metadata_entry
    )

    chain = []
    seen_paths = set()

    while (
        current.entry_type
        is FilesystemEntryType.SYMLINK
    ):
        if (
            current.path
            in seen_paths
        ):
            raise ValueError(
                "standalone DEX symlink loop detected at "
                f"{current.path}"
            )

        seen_paths.add(
            current.path
        )

        chain.append(
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
                "standalone DEX symlink is missing target: "
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
                "standalone DEX symlink target is absent from "
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
            "standalone DEX source resolves to non-file entry: "
            f"{source_metadata_entry.path} -> "
            f"{current.path} "
            f"type={current.entry_type.value}"
        )

    return (
        tuple(
            chain
        ),
        current,
    )


def _filesystem_binding(
    disposition: AndroidStandaloneDexDisposition,
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
    model_source = (
        disposition.source
    )

    filesystem_source = (
        model_source.filesystem_source
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
            "standalone DEX source does not preserve canonical "
            "filesystem artifact identity: "
            f"{model_source.source_name}:"
            f"{model_source.android_path.as_posix()}"
        ) from error

    if (
        inventory_entry.artifact
        is not filesystem_source.artifact
    ):
        raise ValueError(
            "standalone DEX filesystem lookup must preserve "
            "exact Extraction artifact identity"
        )

    metadata_path = (
        inventory_entry
        .filesystem_path_for_materialized_path(
            model_source.host_path
        )
    )

    source_metadata_entry = (
        inventory_entry
        .result
        .metadata
        .get(
            metadata_path
        )
    )

    if source_metadata_entry is None:
        raise ValueError(
            "standalone DEX source has no canonical filesystem "
            "metadata entry: "
            f"{model_source.source_name}:"
            f"{model_source.android_path.as_posix()}"
        )

    (
        symlink_chain,
        payload_metadata_entry,
    ) = _resolve_payload_metadata(
        source_metadata_entry,
        inventory_entry=inventory_entry,
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

    if (
        len(
            matches
        )
        != 1
    ):
        raise ValueError(
            "standalone DEX payload must reconcile to exactly "
            "one canonical Artifact requirement: "
            f"{model_source.source_name}:"
            f"{model_source.android_path.as_posix()} "
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


class AndroidUniverseStandaloneDexInterpreter:
    def interpret(
        self,
        parsing: AndroidStandaloneDexParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseStandaloneDexPopulationRequirement:
        if not isinstance(
            parsing,
            AndroidStandaloneDexParsingResult,
        ):
            raise TypeError(
                "parsing must be an "
                "AndroidStandaloneDexParsingResult"
            )

        requirements = []

        for disposition in (
            parsing.dispositions
        ):
            (
                source_metadata_entry,
                symlink_chain,
                payload_metadata_entry,
                artifact,
            ) = _filesystem_binding(
                disposition,
                artifact_requirements=(
                    artifact_requirements
                ),
            )

            requirements.append(
                AndroidUniverseStandaloneDexRequirement(
                    source=disposition,
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

        return (
            AndroidUniverseStandaloneDexPopulationRequirement(
                source=parsing,
                requirements=tuple(
                    requirements
                ),
            )
        )
