from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class LpdumpParseError(ValueError):
    """
    Raised when textual lpdump output cannot be parsed.
    """


class LpExtentType(StrEnum):
    """
    Logical-partition extent target types printed by lpdump.
    """

    LINEAR = "linear"
    ZERO = "zero"


@dataclass(frozen=True)
class LpMetadataVersion:
    """
    Logical-partition metadata format version.
    """

    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class LpExtent:
    """
    One logical extent belonging to a dynamic partition.

    logical_start_sector and logical_end_sector describe the sector range
    inside the logical partition.

    For linear extents, target_device and target_start_sector identify the
    physical location inside a super block device.

    Zero extents have no physical target.
    """

    logical_start_sector: int
    logical_end_sector: int
    extent_type: LpExtentType
    target_device: str | None = None
    target_start_sector: int | None = None

    @property
    def sector_count(self) -> int:
        """
        Return the number of sectors covered by this extent.
        """

        return (
            self.logical_end_sector
            - self.logical_start_sector
            + 1
        )


@dataclass(frozen=True)
class LpPartition:
    """
    One logical partition described by lpdump.
    """

    name: str
    group: str
    attributes: frozenset[str]
    extents: tuple[LpExtent, ...]

    @property
    def sector_count(self) -> int:
        """
        Return the partition size in sectors.
        """

        return sum(
            extent.sector_count
            for extent in self.extents
        )

    @property
    def slot_suffix(self) -> str | None:
        """
        Return _a or _b when the partition name is slot-suffixed.
        """

        return _detect_slot_suffix(
            self.name
        )

    @property
    def base_name(self) -> str:
        """
        Return the partition name without a recognized slot suffix.
        """

        return _remove_slot_suffix(
            self.name
        )

    @property
    def is_readonly(self) -> bool:
        return "readonly" in self.attributes

    @property
    def is_slot_suffixed(self) -> bool:
        return (
            "slot-suffixed" in self.attributes
            or self.slot_suffix is not None
        )

    @property
    def is_updated(self) -> bool:
        return "updated" in self.attributes

    @property
    def is_disabled(self) -> bool:
        return "disabled" in self.attributes


@dataclass(frozen=True)
class LpBlockDevice:
    """
    Physical block device that stores logical-partition extents.
    """

    name: str
    first_sector: int
    size_bytes: int
    flags: frozenset[str]

    @property
    def slot_suffix(self) -> str | None:
        return _detect_slot_suffix(
            self.name
        )

    @property
    def base_name(self) -> str:
        return _remove_slot_suffix(
            self.name
        )

    @property
    def is_slot_suffixed(self) -> bool:
        return (
            "slot-suffixed" in self.flags
            or self.slot_suffix is not None
        )


@dataclass(frozen=True)
class LpGroup:
    """
    Dynamic-partition allocation group.
    """

    name: str
    maximum_size_bytes: int
    flags: frozenset[str]

    @property
    def slot_suffix(self) -> str | None:
        return _detect_slot_suffix(
            self.name
        )

    @property
    def base_name(self) -> str:
        return _remove_slot_suffix(
            self.name
        )

    @property
    def is_slot_suffixed(self) -> bool:
        return (
            "slot-suffixed" in self.flags
            or self.slot_suffix is not None
        )


@dataclass(frozen=True)
class LpdumpMetadata:
    """
    Normalized representation of one lpdump metadata slot.
    """

    version: LpMetadataVersion
    metadata_size_bytes: int
    metadata_max_size_bytes: int
    metadata_slot_count: int
    header_flags: frozenset[str]
    slot: int | None
    partitions: tuple[LpPartition, ...]
    block_devices: tuple[LpBlockDevice, ...]
    groups: tuple[LpGroup, ...]

    def find_partition(
        self,
        name: str,
    ) -> LpPartition | None:
        """
        Find a logical partition by its exact name.
        """

        for partition in self.partitions:
            if partition.name == name:
                return partition

        return None

    def find_block_device(
        self,
        name: str,
    ) -> LpBlockDevice | None:
        """
        Find a block device by its exact name.
        """

        for block_device in self.block_devices:
            if block_device.name == name:
                return block_device

        return None

    def find_group(
        self,
        name: str,
    ) -> LpGroup | None:
        """
        Find a partition group by its exact name.
        """

        for group in self.groups:
            if group.name == name:
                return group

        return None


@dataclass
class _PartitionBuilder:
    """
    Mutable construction state used only while parsing.
    """

    name: str | None = None
    group: str | None = None
    attributes: frozenset[str] = frozenset()
    extents: list[LpExtent] | None = None

    def __post_init__(self) -> None:
        if self.extents is None:
            self.extents = []


@dataclass
class _BlockDeviceBuilder:
    """
    Mutable construction state used only while parsing.
    """

    name: str | None = None
    first_sector: int | None = None
    size_bytes: int | None = None
    flags: frozenset[str] = frozenset()


@dataclass
class _GroupBuilder:
    """
    Mutable construction state used only while parsing.
    """

    name: str | None = None
    maximum_size_bytes: int | None = None
    flags: frozenset[str] = frozenset()


_VERSION_PATTERN = re.compile(
    r"^Metadata version:\s*(\d+)\.(\d+)\s*$"
)

_BYTE_VALUE_PATTERN = re.compile(
    r"^(\d+)\s+bytes$"
)

_EXTENT_PATTERN = re.compile(
    r"^(\d+)\s+\.\.\s+(\d+)\s+"
    r"(linear|zero)"
    r"(?:\s+(\S+)\s+(\d+))?\s*$"
)

_SLOT_PATTERN = re.compile(
    r"^Slot\s+(\d+):\s*$"
)


class LpdumpParser:
    """
    Parse the human-readable output emitted by Android's lpdump tool.

    The parser accepts one metadata slot at a time. The duplicated
    'Super partition layout' section is ignored because the partition table
    already contains the same extent information in a partition-centric form.
    """

    def parse(
        self,
        text: str,
    ) -> LpdumpMetadata:
        """
        Parse lpdump output into normalized immutable records.

        Args:
            text:
                Standard output captured from lpdump.

        Raises:
            TypeError:
                If text is not a string.

            LpdumpParseError:
                If required fields are missing or malformed.
        """

        normalized = self._validate_text(
            text
        )

        lines = normalized.splitlines()

        version: LpMetadataVersion | None = None
        metadata_size_bytes: int | None = None
        metadata_max_size_bytes: int | None = None
        metadata_slot_count: int | None = None
        header_flags = frozenset[str]()
        slot: int | None = None

        partitions: list[LpPartition] = []
        block_devices: list[LpBlockDevice] = []
        groups: list[LpGroup] = []

        section: str | None = None
        partition_builder: _PartitionBuilder | None = None
        block_device_builder: _BlockDeviceBuilder | None = None
        group_builder: _GroupBuilder | None = None

        for raw_line in lines:
            stripped = raw_line.strip()

            if not stripped:
                continue

            slot_match = _SLOT_PATTERN.match(
                stripped
            )

            if slot_match is not None:
                parsed_slot = int(
                    slot_match.group(1)
                )

                if (
                    slot is not None
                    and slot != parsed_slot
                ):
                    raise LpdumpParseError(
                        "Multiple metadata slots were found; "
                        "parse one slot at a time"
                    )

                slot = parsed_slot
                continue

            version_match = _VERSION_PATTERN.match(
                stripped
            )

            if version_match is not None:
                version = LpMetadataVersion(
                    major=int(
                        version_match.group(1)
                    ),
                    minor=int(
                        version_match.group(2)
                    ),
                )
                continue

            if stripped.startswith(
                "Metadata size:"
            ):
                metadata_size_bytes = self._parse_byte_field(
                    stripped,
                    "Metadata size:",
                )
                continue

            if stripped.startswith(
                "Metadata max size:"
            ):
                metadata_max_size_bytes = self._parse_byte_field(
                    stripped,
                    "Metadata max size:",
                )
                continue

            if stripped.startswith(
                "Metadata slot count:"
            ):
                metadata_slot_count = self._parse_integer_field(
                    stripped,
                    "Metadata slot count:",
                )
                continue

            if stripped.startswith(
                "Header flags:"
            ):
                header_flags = self._parse_flags(
                    stripped.removeprefix(
                        "Header flags:"
                    )
                )
                continue

            if stripped == "Partition table:":
                self._finish_partition(
                    partition_builder,
                    partitions,
                )
                partition_builder = None
                section = "partitions"
                continue

            if stripped == "Super partition layout:":
                self._finish_partition(
                    partition_builder,
                    partitions,
                )
                partition_builder = None
                section = "layout"
                continue

            if stripped == "Block device table:":
                self._finish_partition(
                    partition_builder,
                    partitions,
                )
                partition_builder = None

                self._finish_block_device(
                    block_device_builder,
                    block_devices,
                )
                block_device_builder = None

                section = "block_devices"
                continue

            if stripped == "Group table:":
                self._finish_block_device(
                    block_device_builder,
                    block_devices,
                )
                block_device_builder = None

                self._finish_group(
                    group_builder,
                    groups,
                )
                group_builder = None

                section = "groups"
                continue

            if self._is_separator(
                stripped
            ):
                if section == "partitions":
                    self._finish_partition(
                        partition_builder,
                        partitions,
                    )
                    partition_builder = None

                elif section == "block_devices":
                    self._finish_block_device(
                        block_device_builder,
                        block_devices,
                    )
                    block_device_builder = None

                elif section == "groups":
                    self._finish_group(
                        group_builder,
                        groups,
                    )
                    group_builder = None

                continue

            if section == "partitions":
                partition_builder = self._parse_partition_line(
                    stripped,
                    partition_builder,
                )
                continue

            if section == "block_devices":
                block_device_builder = self._parse_block_device_line(
                    stripped,
                    block_device_builder,
                )
                continue

            if section == "groups":
                group_builder = self._parse_group_line(
                    stripped,
                    group_builder,
                )
                continue

            # The super layout and platform-specific snapshot sections are
            # intentionally ignored.

        self._finish_partition(
            partition_builder,
            partitions,
        )

        self._finish_block_device(
            block_device_builder,
            block_devices,
        )

        self._finish_group(
            group_builder,
            groups,
        )

        if version is None:
            raise LpdumpParseError(
                "Missing metadata version"
            )

        if metadata_size_bytes is None:
            raise LpdumpParseError(
                "Missing metadata size"
            )

        if metadata_max_size_bytes is None:
            raise LpdumpParseError(
                "Missing metadata max size"
            )

        if metadata_slot_count is None:
            raise LpdumpParseError(
                "Missing metadata slot count"
            )

        return LpdumpMetadata(
            version=version,
            metadata_size_bytes=metadata_size_bytes,
            metadata_max_size_bytes=metadata_max_size_bytes,
            metadata_slot_count=metadata_slot_count,
            header_flags=header_flags,
            slot=slot,
            partitions=tuple(
                partitions
            ),
            block_devices=tuple(
                block_devices
            ),
            groups=tuple(
                groups
            ),
        )

    @staticmethod
    def _validate_text(
        text: str,
    ) -> str:
        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "text must be a string"
            )

        if not text.strip():
            raise LpdumpParseError(
                "lpdump output is empty"
            )

        return text

    @staticmethod
    def _is_separator(
        line: str,
    ) -> bool:
        return (
            len(line) >= 3
            and set(line) == {"-"}
        )

    @staticmethod
    def _parse_byte_field(
        line: str,
        prefix: str,
    ) -> int:
        value = line.removeprefix(
            prefix
        ).strip()

        match = _BYTE_VALUE_PATTERN.match(
            value
        )

        if match is None:
            raise LpdumpParseError(
                f"Invalid byte value for {prefix.rstrip(':')}: "
                f"{value}"
            )

        return int(
            match.group(1)
        )

    @staticmethod
    def _parse_integer_field(
        line: str,
        prefix: str,
    ) -> int:
        value = line.removeprefix(
            prefix
        ).strip()

        try:
            parsed = int(
                value
            )
        except ValueError as error:
            raise LpdumpParseError(
                f"Invalid integer value for {prefix.rstrip(':')}: "
                f"{value}"
            ) from error

        if parsed < 0:
            raise LpdumpParseError(
                f"Negative value for {prefix.rstrip(':')}: "
                f"{parsed}"
            )

        return parsed

    @staticmethod
    def _parse_flags(
        value: str,
    ) -> frozenset[str]:
        normalized = value.strip()

        if not normalized or normalized == "none":
            return frozenset()

        return frozenset(
            flag.strip()
            for flag in normalized.split(",")
            if flag.strip()
        )

    def _parse_partition_line(
        self,
        line: str,
        builder: _PartitionBuilder | None,
    ) -> _PartitionBuilder:
        if line.startswith(
            "Name:"
        ):
            if builder is not None and builder.name is not None:
                raise LpdumpParseError(
                    "Partition record started before the previous "
                    "record was completed"
                )

            return _PartitionBuilder(
                name=self._parse_required_string(
                    line,
                    "Name:",
                )
            )

        if builder is None:
            raise LpdumpParseError(
                f"Partition field appeared before partition name: "
                f"{line}"
            )

        if line.startswith(
            "Group:"
        ):
            builder.group = self._parse_required_string(
                line,
                "Group:",
            )
            return builder

        if line.startswith(
            "Attributes:"
        ):
            builder.attributes = self._parse_flags(
                line.removeprefix(
                    "Attributes:"
                )
            )
            return builder

        if line == "Extents:":
            return builder

        extent_match = _EXTENT_PATTERN.match(
            line
        )

        if extent_match is not None:
            extent_type = LpExtentType(
                extent_match.group(3)
            )

            target_device = extent_match.group(4)
            target_start_sector = (
                int(extent_match.group(5))
                if extent_match.group(5) is not None
                else None
            )

            if extent_type is LpExtentType.LINEAR:
                if (
                    target_device is None
                    or target_start_sector is None
                ):
                    raise LpdumpParseError(
                        f"Linear extent is missing its target: "
                        f"{line}"
                    )

            if extent_type is LpExtentType.ZERO:
                if (
                    target_device is not None
                    or target_start_sector is not None
                ):
                    raise LpdumpParseError(
                        f"Zero extent cannot have a target: "
                        f"{line}"
                    )

            assert builder.extents is not None

            builder.extents.append(
                LpExtent(
                    logical_start_sector=int(
                        extent_match.group(1)
                    ),
                    logical_end_sector=int(
                        extent_match.group(2)
                    ),
                    extent_type=extent_type,
                    target_device=target_device,
                    target_start_sector=target_start_sector,
                )
            )

            return builder

        raise LpdumpParseError(
            f"Unrecognized partition line: {line}"
        )

    def _parse_block_device_line(
        self,
        line: str,
        builder: _BlockDeviceBuilder | None,
    ) -> _BlockDeviceBuilder:
        if line.startswith(
            "Partition name:"
        ):
            if builder is not None and builder.name is not None:
                raise LpdumpParseError(
                    "Block-device record started before the previous "
                    "record was completed"
                )

            return _BlockDeviceBuilder(
                name=self._parse_required_string(
                    line,
                    "Partition name:",
                )
            )

        if builder is None:
            raise LpdumpParseError(
                f"Block-device field appeared before device name: "
                f"{line}"
            )

        if line.startswith(
            "First sector:"
        ):
            builder.first_sector = self._parse_integer_field(
                line,
                "First sector:",
            )
            return builder

        if line.startswith(
            "Size:"
        ):
            builder.size_bytes = self._parse_byte_field(
                line,
                "Size:",
            )
            return builder

        if line.startswith(
            "Flags:"
        ):
            builder.flags = self._parse_flags(
                line.removeprefix(
                    "Flags:"
                )
            )
            return builder

        raise LpdumpParseError(
            f"Unrecognized block-device line: {line}"
        )

    def _parse_group_line(
        self,
        line: str,
        builder: _GroupBuilder | None,
    ) -> _GroupBuilder:
        if line.startswith(
            "Name:"
        ):
            if builder is not None and builder.name is not None:
                raise LpdumpParseError(
                    "Group record started before the previous "
                    "record was completed"
                )

            return _GroupBuilder(
                name=self._parse_required_string(
                    line,
                    "Name:",
                )
            )

        if builder is None:
            raise LpdumpParseError(
                f"Group field appeared before group name: "
                f"{line}"
            )

        if line.startswith(
            "Maximum size:"
        ):
            builder.maximum_size_bytes = self._parse_byte_field(
                line,
                "Maximum size:",
            )
            return builder

        if line.startswith(
            "Flags:"
        ):
            builder.flags = self._parse_flags(
                line.removeprefix(
                    "Flags:"
                )
            )
            return builder

        raise LpdumpParseError(
            f"Unrecognized group line: {line}"
        )

    @staticmethod
    def _parse_required_string(
        line: str,
        prefix: str,
    ) -> str:
        value = line.removeprefix(
            prefix
        ).strip()

        if not value:
            raise LpdumpParseError(
                f"{prefix.rstrip(':')} cannot be empty"
            )

        return value

    @staticmethod
    def _finish_partition(
        builder: _PartitionBuilder | None,
        partitions: list[LpPartition],
    ) -> None:
        if builder is None:
            return

        if builder.name is None:
            raise LpdumpParseError(
                "Partition is missing its name"
            )

        if builder.group is None:
            raise LpdumpParseError(
                f"Partition {builder.name} is missing its group"
            )

        assert builder.extents is not None

        partitions.append(
            LpPartition(
                name=builder.name,
                group=builder.group,
                attributes=builder.attributes,
                extents=tuple(
                    builder.extents
                ),
            )
        )

    @staticmethod
    def _finish_block_device(
        builder: _BlockDeviceBuilder | None,
        block_devices: list[LpBlockDevice],
    ) -> None:
        if builder is None:
            return

        if builder.name is None:
            raise LpdumpParseError(
                "Block device is missing its name"
            )

        if builder.first_sector is None:
            raise LpdumpParseError(
                f"Block device {builder.name} is missing "
                f"its first sector"
            )

        if builder.size_bytes is None:
            raise LpdumpParseError(
                f"Block device {builder.name} is missing its size"
            )

        block_devices.append(
            LpBlockDevice(
                name=builder.name,
                first_sector=builder.first_sector,
                size_bytes=builder.size_bytes,
                flags=builder.flags,
            )
        )

    @staticmethod
    def _finish_group(
        builder: _GroupBuilder | None,
        groups: list[LpGroup],
    ) -> None:
        if builder is None:
            return

        if builder.name is None:
            raise LpdumpParseError(
                "Group is missing its name"
            )

        if builder.maximum_size_bytes is None:
            raise LpdumpParseError(
                f"Group {builder.name} is missing its maximum size"
            )

        groups.append(
            LpGroup(
                name=builder.name,
                maximum_size_bytes=builder.maximum_size_bytes,
                flags=builder.flags,
            )
        )


def _detect_slot_suffix(
    name: str,
) -> str | None:
    """
    Detect conventional Android A/B slot suffixes.
    """

    if name.endswith(
        "_a"
    ):
        return "_a"

    if name.endswith(
        "_b"
    ):
        return "_b"

    return None


def _remove_slot_suffix(
    name: str,
) -> str:
    """
    Remove a conventional Android A/B slot suffix.
    """

    suffix = _detect_slot_suffix(
        name
    )

    if suffix is None:
        return name

    return name[
        :-len(suffix)
    ]