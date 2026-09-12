from __future__ import annotations

from dataclasses import dataclass
import re

from treeforge.android.partition.layout import (
    PartitionLayout,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeDynamicPartitionGroup:
    name: str
    size_bytes: int
    partitions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeDynamicPartitionConfig:
    block_device_name: str
    super_partition_size_bytes: int
    groups: tuple[
        AndroidDeviceTreeDynamicPartitionGroup,
        ...,
    ]


class AndroidDeviceTreeDynamicPartitionRenderer:
    """
    Project canonical liblp topology onto Android's generic dynamic-partition
    BoardConfig contract.

    Exact slot-specific partition/group identities remain canonical upstream.
    Only the build representation collapses ``*_a`` / ``*_b`` identities onto
    the unsuffixed logical partition/group names consumed by Android Make.
    """

    @staticmethod
    def _make_variable_token(
        value: str,
    ) -> str:
        token = re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            value,
        ).strip("_").upper()

        if not token:
            raise ValueError(
                "dynamic-partition group cannot map to an empty Make token"
            )

        return token

    @classmethod
    def project(
        cls,
        *,
        layout: PartitionLayout,
    ) -> AndroidDeviceTreeDynamicPartitionConfig | None:
        if not isinstance(
            layout,
            PartitionLayout,
        ):
            raise TypeError(
                "layout must be a PartitionLayout"
            )

        logical = tuple(
            partition
            for partition in layout.partitions
            if partition.is_logical
        )

        if not logical:
            return None

        if len(layout.block_devices) != 1:
            raise ValueError(
                "dynamic Device Tree realization currently requires exactly "
                "one canonical liblp physical block-device record; "
                f"found {len(layout.block_devices)}"
            )

        block_device = layout.block_devices[0]

        groups_by_exact_name = {
            group.name: group
            for group in layout.groups
        }

        referenced_group_order: list[str] = []
        group_partitions: dict[str, list[str]] = {}
        partition_group_owner: dict[str, str] = {}

        for partition in logical:
            if partition.group is None:
                raise ValueError(
                    "logical partition lacks canonical liblp group: "
                    f"{partition.name}"
                )

            exact_group = groups_by_exact_name.get(
                partition.group
            )

            if exact_group is None:
                raise ValueError(
                    "logical partition references unknown canonical group: "
                    f"{partition.name}: {partition.group}"
                )

            group_name = exact_group.base_name
            partition_name = partition.base_name

            previous_group = partition_group_owner.get(
                partition_name
            )

            if (
                previous_group is not None
                and previous_group != group_name
            ):
                raise ValueError(
                    "slot variants of one logical partition map to "
                    "different normalized groups: "
                    f"{partition_name}: {previous_group} vs {group_name}"
                )

            partition_group_owner[partition_name] = group_name

            if group_name not in group_partitions:
                referenced_group_order.append(group_name)
                group_partitions[group_name] = []

            if partition_name not in group_partitions[group_name]:
                group_partitions[group_name].append(partition_name)

        rendered_groups = []

        for group_name in referenced_group_order:
            variants = tuple(
                group
                for group in layout.groups
                if group.base_name == group_name
            )

            maxima = {
                group.maximum_size_bytes
                for group in variants
                if group.maximum_size_bytes is not None
            }

            if len(maxima) != 1:
                raise ValueError(
                    "normalized dynamic-partition group must have exactly one "
                    "canonical maximum across slot variants: "
                    f"{group_name}: {sorted(maxima)!r}"
                )

            maximum = next(iter(maxima))

            if maximum <= 0:
                raise ValueError(
                    "normalized dynamic-partition group maximum must be positive: "
                    f"{group_name}: {maximum}"
                )

            rendered_groups.append(
                AndroidDeviceTreeDynamicPartitionGroup(
                    name=group_name,
                    size_bytes=maximum,
                    partitions=tuple(group_partitions[group_name]),
                )
            )

        return AndroidDeviceTreeDynamicPartitionConfig(
            block_device_name=block_device.partition_name,
            super_partition_size_bytes=block_device.size_bytes,
            groups=tuple(rendered_groups),
        )

    @classmethod
    def render_board_config(
        cls,
        config: AndroidDeviceTreeDynamicPartitionConfig | None,
    ) -> str:
        if config is None:
            return ""

        if not isinstance(
            config,
            AndroidDeviceTreeDynamicPartitionConfig,
        ):
            raise TypeError(
                "config must be an AndroidDeviceTreeDynamicPartitionConfig or None"
            )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Canonical factory-derived Android dynamic-partition topology.",
            "# Exact slot-specific liblp identities remain upstream.",
            "",
            (
                "BOARD_SUPER_PARTITION_SIZE := "
                f"{config.super_partition_size_bytes}"
            ),
            (
                "BOARD_SUPER_PARTITION_GROUPS := "
                + " ".join(group.name for group in config.groups)
            ),
            "",
        ]

        for index, group in enumerate(config.groups):
            token = cls._make_variable_token(group.name)

            lines.append(
                f"BOARD_{token}_SIZE := {group.size_bytes}"
            )

            if group.partitions:
                lines.append(
                    f"BOARD_{token}_PARTITION_LIST := \\\""[:-1]
                )

                last = len(group.partitions) - 1

                for part_index, partition in enumerate(group.partitions):
                    suffix = " \\\""[:-1] if part_index != last else ""
                    lines.append(
                        f"    {partition}{suffix}"
                    )

            if index != len(config.groups) - 1:
                lines.append("")

        lines.append("")
        return "\n".join(lines)
