from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from treeforge.android.partition.source import (
    PartitionSource,
)

class PartitionOrigin(StrEnum):
    """
    Physical origin of one normalized Android partition.

    A standalone partition is backed directly by its own image.

    A super partition is a logical partition described by dynamic-partition
    metadata and stored inside a super image.
    """

    STANDALONE = "standalone"
    SUPER = "super"


class PartitionPayloadState(StrEnum):
    """
    Physical payload availability established by canonical layout evidence.

    AVAILABLE means the partition has payload-bearing source evidence that
    Extraction may materialize.

    UNAVAILABLE means the partition is structurally present in canonical
    topology but its source explicitly contains no payload for that partition.

    UNKNOWN means topology is known but payload availability has not yet been
    established.
    """

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class PartitionLayoutSource(StrEnum):
    """
    Overall source composition of a normalized partition layout.

    MIXED supports normal Android factory-image layouts containing both:

    - standalone images such as boot.img and vendor_boot.img;
    - logical partitions stored inside super.img.
    """

    STANDALONE = "standalone"
    SUPER = "super"
    MIXED = "mixed"

class PartitionLayoutValidationError(ValueError):
    """
    Raised when a canonical partition layout is internally invalid.
    """

@dataclass(
    frozen=True,
    slots=True,
)
class LayoutPartition:
    """
    One partition in TreeForge's canonical partition layout.

    PartitionLayout represents partition structure and facts known at the
    layout-interpretation stage.

    It does not require extraction or permanent materialization.

    Attributes:
        name:
            Exact canonical partition name established by layout evidence.

        origin:
            Structural origin of the partition.

            STANDALONE means Discovery identified the partition as its own
            partition artifact.

            SUPER means dynamic-partition metadata identifies the partition
            inside a super layout.

        source:
            Immutable upstream provenance anchor.

            When available, this preserves the exact Discovery
            ProviderArtifact by identity.

        payload_state:
            Physical payload availability established by source evidence.

            AVAILABLE means Extraction may materialize the partition payload.

            UNAVAILABLE means the partition exists in canonical topology but
            the source explicitly carries no partition payload.

            UNKNOWN means topology is established but payload availability is
            not yet known.

        size_bytes:
            Partition size when supported by evidence available to this stage.

            None means Layout has no reliable size evidence.

        readonly:
            Read-only state when explicitly supported by layout evidence.

            True means the source explicitly establishes read-only.

            False means the source explicitly establishes not read-only.

            None means the state is unknown at this stage.

        slot_suffix:
            Recognized Android slot suffix when established by layout
            evidence, normally "_a" or "_b".

            None means no slot suffix has been established.

        group:
            Dynamic-partition group when established by layout metadata.

            None means no group relationship is established.
    """

    name: str
    origin: PartitionOrigin
    source: PartitionSource | None = None
    payload_state: PartitionPayloadState = PartitionPayloadState.UNKNOWN
    size_bytes: int | None = None
    readonly: bool | None = None
    slot_suffix: str | None = None
    group: str | None = None

    def __post_init__(
        self,
    ) -> None:
        """
        Validate one canonical layout partition.
        """

        if not isinstance(
            self.name,
            str,
        ):
            raise PartitionLayoutValidationError(
                "Partition name must be a string"
            )

        if not self.name.strip():
            raise PartitionLayoutValidationError(
                "Partition name cannot be empty"
            )

        if not isinstance(
            self.origin,
            PartitionOrigin,
        ):
            raise PartitionLayoutValidationError(
                f"Invalid partition origin: "
                f"{self.name}"
            )

        if (
            self.source is not None
            and not isinstance(
                self.source,
                PartitionSource,
            )
        ):
            raise PartitionLayoutValidationError(
                "Partition source must be a "
                "PartitionSource or None"
            )

        if not isinstance(
            self.payload_state,
            PartitionPayloadState,
        ):
            raise PartitionLayoutValidationError(
                "Partition payload state must be a "
                "PartitionPayloadState"
            )

        if (
            self.size_bytes is not None
            and (
                not isinstance(
                    self.size_bytes,
                    int,
                )
                or isinstance(
                    self.size_bytes,
                    bool,
                )
            )
        ):
            raise PartitionLayoutValidationError(
                "Partition size must be an "
                "integer or None"
            )

        if (
            self.size_bytes is not None
            and self.size_bytes < 0
        ):
            raise PartitionLayoutValidationError(
                f"Partition size cannot be "
                f"negative: {self.name}"
            )

        if (
            self.readonly is not None
            and not isinstance(
                self.readonly,
                bool,
            )
        ):
            raise PartitionLayoutValidationError(
                "Partition readonly state must be "
                "a boolean or None"
            )

        if (
            self.slot_suffix is not None
            and (
                not isinstance(
                    self.slot_suffix,
                    str,
                )
                or not self.slot_suffix.startswith(
                    "_"
                )
                or len(
                    self.slot_suffix
                ) == 1
            )
        ):
            raise PartitionLayoutValidationError(
                f"Invalid slot suffix for partition "
                f"{self.name}: "
                f"{self.slot_suffix!r}"
            )

        if (
            self.group is not None
            and (
                not isinstance(
                    self.group,
                    str,
                )
                or not self.group.strip()
            )
        ):
            raise PartitionLayoutValidationError(
                f"Partition group cannot be empty: "
                f"{self.name}"
            )

    @property
    def base_name(
        self,
    ) -> str:
        """
        Return the partition name without its established slot suffix.
        """

        if (
            self.slot_suffix is not None
            and self.name.endswith(
                self.slot_suffix
            )
        ):
            return self.name[
                :-len(
                    self.slot_suffix
                )
            ]

        return self.name

    @property
    def is_logical(
        self,
    ) -> bool:
        """
        Return whether this is a logical super partition.
        """

        return (
            self.origin
            is PartitionOrigin.SUPER
        )

@dataclass(frozen=True, slots=True)
class LayoutBlockDevice:
    # Canonical physical block-device evidence for dynamic partitions.
    #
    # The liblp-structure path may populate exact raw alignment/flag fields.
    # The lpdump path populates only the normalized fields it actually exposes.
    # Missing source facts remain None; they are never guessed.

    partition_name: str
    size_bytes: int

    first_logical_sector: int | None = None
    alignment_bytes: int | None = None
    alignment_offset_bytes: int | None = None

    flags: frozenset[str] = frozenset()
    raw_flags: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(self.partition_name, str)
            or not self.partition_name.strip()
        ):
            raise PartitionLayoutValidationError(
                "block-device partition_name must be non-empty"
            )

        if (
            not isinstance(self.size_bytes, int)
            or isinstance(self.size_bytes, bool)
            or self.size_bytes <= 0
        ):
            raise PartitionLayoutValidationError(
                "block-device size_bytes must be a positive integer"
            )

        for name, value in (
            ("first_logical_sector", self.first_logical_sector),
            ("alignment_bytes", self.alignment_bytes),
            ("alignment_offset_bytes", self.alignment_offset_bytes),
            ("raw_flags", self.raw_flags),
        ):
            if (
                value is not None
                and (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or value < 0
                )
            ):
                raise PartitionLayoutValidationError(
                    f"block-device {name} must be "
                    "a non-negative integer or None"
                )

        if not isinstance(self.flags, frozenset):
            raise PartitionLayoutValidationError(
                "block-device flags must be a frozenset"
            )

        if not all(
            isinstance(item, str) and item
            for item in self.flags
        ):
            raise PartitionLayoutValidationError(
                "block-device flags must contain only non-empty strings"
            )



@dataclass(
    frozen=True,
    slots=True,
)
class LayoutPartitionGroup:
    """
    One dynamic-partition group in the canonical partition layout.

    Attributes:
        name:
            Exact group name represented by the source metadata.

        maximum_size_bytes:
            Maximum size assigned to the group.

            None means the source did not provide a reliable maximum.

        slot_suffix:
            Recognized Android slot suffix, normally "_a" or "_b".

        flags:
            Immutable source metadata flags associated with the group.
    """

    name: str
    maximum_size_bytes: int | None = None
    slot_suffix: str | None = None
    flags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        """
        Validate one canonical partition group.
        """

        if not isinstance(
            self.name,
            str,
        ):
            raise PartitionLayoutValidationError(
                "Partition group name must be a string"
            )

        if not self.name.strip():
            raise PartitionLayoutValidationError(
                "Partition group name cannot be empty"
            )

        if (
            self.maximum_size_bytes is not None
            and self.maximum_size_bytes < 0
        ):
            raise PartitionLayoutValidationError(
                f"Partition group maximum size cannot be negative: "
                f"{self.name}"
            )

        if (
            self.slot_suffix is not None
            and (
                not self.slot_suffix.startswith("_")
                or len(self.slot_suffix) == 1
            )
        ):
            raise PartitionLayoutValidationError(
                f"Invalid slot suffix for partition group "
                f"{self.name}: {self.slot_suffix!r}"
            )

        if not isinstance(
            self.flags,
            frozenset,
        ):
            raise PartitionLayoutValidationError(
                f"Partition group flags must be a frozenset: "
                f"{self.name}"
            )

    @property
    def base_name(self) -> str:
        """
        Return the group name without its recorded slot suffix.
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
class PartitionLayout:
    """
    Canonical immutable Android partition layout.
    """

    source: PartitionLayoutSource
    partitions: tuple[
        LayoutPartition,
        ...,
    ] = ()
    groups: tuple[
        LayoutPartitionGroup,
        ...,
    ] = ()

    block_devices: tuple[
        LayoutBlockDevice,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        """
        Validate the complete canonical partition layout.
        """

        if not isinstance(
            self.partitions,
            tuple,
        ):
            raise PartitionLayoutValidationError(
                "Layout partitions must be a tuple"
            )

        if not isinstance(
            self.groups,
            tuple,
        ):
            raise PartitionLayoutValidationError(
                "Layout groups must be a tuple"
            )

        if (
            not isinstance(
                self.block_devices,
                tuple,
            )
            or not all(
                isinstance(
                    item,
                    LayoutBlockDevice,
                )
                for item in self.block_devices
            )
        ):
            raise PartitionLayoutValidationError(
                "Layout block_devices must contain only LayoutBlockDevice values"
            )

        self._validate_unique_partition_names()
        self._validate_unique_group_names()
        self._validate_unique_block_device_names()
        self._validate_partition_group_references()

    def _validate_unique_block_device_names(
        self,
    ) -> None:
        """
        Reject duplicate exact physical block-device names.
        """

        names = tuple(
            item.partition_name
            for item in self.block_devices
        )

        if len(names) != len(set(names)):
            raise PartitionLayoutValidationError(
                "Duplicate dynamic-partition block-device name"
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
                raise PartitionLayoutValidationError(
                    f"Duplicate partition name: "
                    f"{partition.name}"
                )

            seen.add(
                partition.name
            )

    def _validate_unique_group_names(
        self,
    ) -> None:
        """
        Reject duplicate exact group names.
        """

        seen: set[str] = set()

        for group in self.groups:
            if group.name in seen:
                raise PartitionLayoutValidationError(
                    f"Duplicate partition group name: "
                    f"{group.name}"
                )

            seen.add(
                group.name
            )

    def _validate_partition_group_references(
        self,
    ) -> None:
        """
        Ensure every referenced partition group exists.
        """

        group_names = {
            group.name
            for group in self.groups
        }

        for partition in self.partitions:
            if (
                partition.group is not None
                and partition.group not in group_names
            ):
                raise PartitionLayoutValidationError(
                    f"Partition {partition.name} references "
                    f"unknown group: {partition.group}"
                )

    def block_device(
        self,
        partition_name: str,
    ) -> LayoutBlockDevice | None:
        """
        Return the exact physical block-device record by partition name.
        """

        for block_device in self.block_devices:
            if block_device.partition_name == partition_name:
                return block_device

        return None

    def partition(
        self,
        name: str,
    ) -> LayoutPartition | None:
        """
        Return the partition with the exact supplied name.
        """

        for partition in self.partitions:
            if partition.name == name:
                return partition

        return None

    def partitions_named(
        self,
        base_name: str,
    ) -> tuple[
        LayoutPartition,
        ...,
    ]:
        """
        Return all partitions matching a canonical base name.

        This supports layouts containing slot variants such as system_a and
        system_b without forcing callers to understand suffix removal.
        """

        return tuple(
            partition
            for partition in self.partitions
            if partition.base_name
            == base_name
        )

    def group(
        self,
        name: str,
    ) -> LayoutPartitionGroup | None:
        """
        Return the group with the exact supplied name.

        None is returned when the layout does not contain that group.
        """

        for group in self.groups:
            if group.name == name:
                return group

        return None

    def groups_named(
        self,
        base_name: str,
    ) -> tuple[
        LayoutPartitionGroup,
        ...,
    ]:
        """
        Return all groups matching a canonical base name.
        """

        return tuple(
            group
            for group in self.groups
            if group.base_name
            == base_name
        )

    def contains(
        self,
        name: str,
    ) -> bool:
        """
        Return whether the layout contains an exact partition name.
        """

        return (
            self.partition(name)
            is not None
        )