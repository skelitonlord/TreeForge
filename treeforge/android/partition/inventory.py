from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction.model import (
    ExtractedArtifact,
)
class PartitionInventoryValidationError(
    ValueError
):
    """
    Raised when a canonical partition inventory is internally invalid.
    """


@dataclass(
    frozen=True,
    slots=True,
)
class InventoryPartition:
    """
    One directly accessible Android partition.

    The presence of an InventoryPartition guarantees that TreeForge has a
    canonical Extraction artifact representing the accessible partition
    image.

    Attributes:
        name:
            Exact canonical partition name.

        artifact:
            Exact canonical Extraction artifact representing the directly
            accessible partition image.

            This object preserves materialization lineage, operation evidence,
            exact upstream ProviderArtifact identity, hashes, tool evidence,
            and immediate Extraction parent identity.

        slot_suffix:
            Recognized Android slot suffix.

    """

    name: str
    artifact: ExtractedArtifact
    slot_suffix: str | None = None

    def __post_init__(self) -> None:
        """
        Validate one canonical inventory partition.
        """

        if not isinstance(
            self.name,
            str,
        ):
            raise PartitionInventoryValidationError(
                "Inventory partition name must be a string"
            )

        if not self.name.strip():
            raise PartitionInventoryValidationError(
                "Inventory partition name cannot be empty"
            )

        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise PartitionInventoryValidationError(
                "Inventory partition artifact must be an "
                "ExtractedArtifact"
            )

        if (
            self.slot_suffix is not None
            and (
                not self.slot_suffix.startswith(
                    "_"
                )
                or len(
                    self.slot_suffix
                ) == 1
            )
        ):
            raise PartitionInventoryValidationError(
                f"Invalid slot suffix for inventory "
                f"partition {self.name}: "
                f"{self.slot_suffix!r}"
            )

    @property
    def base_name(self) -> str:
        """
        Return the partition name without its recorded slot suffix.
        """

        if (
            self.slot_suffix is not None
            and self.name.endswith(
                self.slot_suffix
            )
        ):
            return self.name[
                :-len(self.slot_suffix)
            ]

        return self.name


@dataclass(
    frozen=True,
    slots=True,
)
class PartitionInventory:
    """
    Canonical immutable inventory of directly accessible partition images.
    """

    partitions: tuple[
        InventoryPartition,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        """
        Validate the complete partition inventory.
        """

        if not isinstance(
            self.partitions,
            tuple,
        ):
            raise PartitionInventoryValidationError(
                "Inventory partitions must be a tuple"
            )

        self._validate_partition_types()
        self._validate_unique_partition_names()

    def _validate_partition_types(
        self,
    ) -> None:
        """
        Ensure every inventory entry is an InventoryPartition.
        """

        for partition in self.partitions:
            if not isinstance(
                partition,
                InventoryPartition,
            ):
                raise PartitionInventoryValidationError(
                    "Inventory entries must be "
                    "InventoryPartition instances"
                )

    def _validate_unique_partition_names(
        self,
    ) -> None:
        """
        Reject duplicate exact partition names.
        """

        seen: set[str] = set()

        for partition in self.partitions:
            if partition.name in seen:
                raise PartitionInventoryValidationError(
                    f"Duplicate inventory partition name: "
                    f"{partition.name}"
                )

            seen.add(
                partition.name
            )

    @property
    def images(
        self,
    ) -> tuple[
        Path,
        ...,
    ]:
        """
        Return accessible images in canonical inventory order.
        """

        return tuple(
            partition.artifact.path
            for partition in self.partitions
        )

    def partition(
        self,
        name: str,
    ) -> InventoryPartition | None:
        """
        Return the inventory partition with the exact supplied name.
        """

        for partition in self.partitions:
            if partition.name == name:
                return partition

        return None

    def partitions_named(
        self,
        base_name: str,
    ) -> tuple[
        InventoryPartition,
        ...,
    ]:
        """
        Return all inventory partitions matching a canonical base name.
        """

        return tuple(
            partition
            for partition in self.partitions
            if partition.base_name
            == base_name
        )

    def contains(
        self,
        name: str,
    ) -> bool:
        """
        Return whether the inventory contains an exact partition name.
        """

        return (
            self.partition(
                name
            )
            is not None
        )