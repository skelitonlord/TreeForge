from __future__ import annotations

from treeforge.android.parsing.bootloader import (
    AndroidParsedUfpk,
    AndroidParsedUfpkDescriptor,
)
from treeforge.android.parsing.result import (
    ParsedBootloaderChild,
)

from treeforge.android.universe.bootloader.requirement import (
    AndroidUniverseBootloaderRequirement,
)


class AndroidUniverseBootloaderInterpreter:
    """
    Promote canonical Parsing-stage bootloader children into Universe.

    No FBPK/container data or child payload bytes are reopened or reparsed here.
    """

    def interpret(
        self,
        parsing: tuple[
            ParsedBootloaderChild,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseBootloaderRequirement,
        ...,
    ]:
        if not isinstance(
            parsing,
            tuple,
        ):
            raise TypeError(
                "parsing must be a tuple"
            )

        if not all(
            isinstance(
                item,
                ParsedBootloaderChild,
            )
            for item in parsing
        ):
            raise TypeError(
                "parsing must contain only "
                "ParsedBootloaderChild entries"
            )

        descriptor_counts_by_parent_id: dict[
            int,
            int,
        ] = {}

        for item in parsing:
            if not isinstance(
                item.parsed,
                AndroidParsedUfpkDescriptor,
            ):
                continue

            parent = item.artifact.parent

            if parent is None:
                raise ValueError(
                    "UFPK descriptor artifact must preserve its "
                    "canonical package parent"
                )

            parent_id = id(
                parent
            )

            descriptor_counts_by_parent_id[
                parent_id
            ] = (
                descriptor_counts_by_parent_id.get(
                    parent_id,
                    0,
                )
                + 1
            )

        requirements = []

        for item in parsing:
            validated_descriptor_count = None

            if isinstance(
                item.parsed,
                AndroidParsedUfpk,
            ):
                descriptor_count = (
                    descriptor_counts_by_parent_id.get(
                        id(
                            item.artifact
                        ),
                        0,
                    )
                )

                if (
                    descriptor_count
                    != item.parsed.header_value_0x4c
                ):
                    raise ValueError(
                        "UFPK header value at offset 0x4c does "
                        "not match the independently materialized "
                        "descriptor population: "
                        f"header={item.parsed.header_value_0x4c}, "
                        f"descriptors={descriptor_count}"
                    )

                validated_descriptor_count = (
                    descriptor_count
                )

            requirements.append(
                AndroidUniverseBootloaderRequirement(
                    source=item,
                    validated_descriptor_count=(
                        validated_descriptor_count
                    ),
                )
            )

        return tuple(
            requirements
        )
