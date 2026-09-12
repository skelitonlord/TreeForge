from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    AndroidExtractionResult,
)
from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.partition.inventory import (
    PartitionInventory,
)
from treeforge.android.parsing.filesystem.filesystem_sources import (
    AndroidFilesystemSourceBuilder,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
    AndroidModelSourceInventoryBuilder,
    AndroidParserFilesystemSource,
)


class AndroidParsingPreparationError(
    RuntimeError,
):
    """
    Raised when canonical upstream state cannot be prepared for Parsing.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsingPreparation:
    """
    Canonical immutable parser-input preparation.

    This boundary contains no parsed observations.

    It records:
    - the exact Filesystem Metadata inventory consumed;
    - one parser-facing filesystem source for every canonical filesystem root;
    - the complete canonical Android model-source inventory discovered from
      those filesystem sources.
    """

    filesystem_inventory: (
        FilesystemMetadataInventory
    )

    filesystems: tuple[
        AndroidParserFilesystemSource,
        ...,
    ]

    source_inventory: (
        AndroidModelSourceInventory
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        if not isinstance(
            self.filesystems,
            tuple,
        ):
            raise TypeError(
                "filesystems must be a tuple"
            )

        if not all(
            isinstance(
                filesystem,
                AndroidParserFilesystemSource,
            )
            for filesystem in self.filesystems
        ):
            raise TypeError(
                "filesystems must contain only "
                "AndroidParserFilesystemSource instances"
            )

        if not isinstance(
            self.source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an "
                "AndroidModelSourceInventory"
            )

        if (
            len(
                self.filesystems
            )
            != len(
                self.filesystem_inventory
            )
        ):
            raise ValueError(
                "Parsing Preparation must preserve one parser "
                "filesystem source per Filesystem Metadata root"
            )

        metadata_artifacts = {
            id(
                entry.artifact
            ): entry.artifact
            for entry
            in self.filesystem_inventory
        }

        parser_artifacts: dict[
            int,
            object,
        ] = {}

        for filesystem in self.filesystems:
            identity = id(
                filesystem.artifact
            )

            if identity in parser_artifacts:
                raise ValueError(
                    "Parsing Preparation contains duplicate "
                    "parser filesystem artifact identity"
                )

            parser_artifacts[
                identity
            ] = filesystem.artifact

        if (
            set(
                metadata_artifacts
            )
            != set(
                parser_artifacts
            )
        ):
            raise ValueError(
                "Parsing Preparation filesystem identities do "
                "not exactly match Filesystem Metadata"
            )

        if (
            len(
                self.source_inventory.filesystems
            )
            != len(
                self.filesystems
            )
        ):
            raise ValueError(
                "source inventory filesystem count does not "
                "match Parsing Preparation"
            )

        for (
            prepared,
            inventoried,
        ) in zip(
            self.filesystems,
            self.source_inventory.filesystems,
            strict=True,
        ):
            if inventoried is not prepared:
                raise ValueError(
                    "source inventory must retain the exact "
                    "Parsing Preparation filesystem objects"
                )


class AndroidParsingPreparationBuilder:
    """
    Build canonical parser inputs from completed upstream Android state.

    This builder performs source preparation only. It does not parse any
    Android source format.
    """

    def __init__(
        self,
        *,
        filesystem_source_builder=(
            None
        ),
        source_inventory_builder=(
            None
        ),
    ) -> None:
        self.filesystem_source_builder = (
            filesystem_source_builder
            if filesystem_source_builder is not None
            else AndroidFilesystemSourceBuilder()
        )

        self.source_inventory_builder = (
            source_inventory_builder
            if source_inventory_builder is not None
            else AndroidModelSourceInventoryBuilder()
        )

    def build(
        self,
        *,
        extraction: AndroidExtractionResult,
        partition_inventory: PartitionInventory,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> AndroidParsingPreparation:
        if not isinstance(
            extraction,
            AndroidExtractionResult,
        ):
            raise TypeError(
                "extraction must be an AndroidExtractionResult"
            )

        if not isinstance(
            partition_inventory,
            PartitionInventory,
        ):
            raise TypeError(
                "partition_inventory must be a PartitionInventory"
            )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        filesystems = (
            self.filesystem_source_builder
            .build(
                extraction,
                partition_inventory,
                filesystem_inventory,
            )
        )

        if not isinstance(
            filesystems,
            tuple,
        ):
            raise AndroidParsingPreparationError(
                "filesystem source builder must return a tuple"
            )

        if not all(
            isinstance(
                filesystem,
                AndroidParserFilesystemSource,
            )
            for filesystem in filesystems
        ):
            raise AndroidParsingPreparationError(
                "filesystem source builder returned invalid "
                "parser filesystem sources"
            )

        source_inventory = (
            self.source_inventory_builder
            .build(
                filesystems
            )
        )

        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise AndroidParsingPreparationError(
                "source inventory builder must return an "
                "AndroidModelSourceInventory"
            )

        return AndroidParsingPreparation(
            filesystem_inventory=(
                filesystem_inventory
            ),
            filesystems=filesystems,
            source_inventory=(
                source_inventory
            ),
        )
