from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from treeforge.android.providers.source_identity import (
    ProviderSourceFilesystemProvenance,
    ProviderSourceIdentity,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)


@dataclass(
    frozen=True,
    slots=True,
)
class WorkspaceSourceState:
    """
    Persistent workspace state for one complete provider source identity.

    Workspace source state uses the current TreeForge schema only.
    Obsolete workspace state should be regenerated from the canonical source.
    """

    SCHEMA_VERSION = 2

    source_identity: ProviderSourceIdentity

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_identity,
            ProviderSourceIdentity,
        ):
            raise TypeError(
                "source_identity must be a "
                "ProviderSourceIdentity"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize complete source identity and provenance.
        """

        source = (
            self.source_identity
        )

        filesystem = (
            source.filesystem_provenance
        )

        return {
            "schema_version": (
                self.SCHEMA_VERSION
            ),
            "source": {
                "provider_id": (
                    source.provider_id
                ),
                "source_type": (
                    source.source_type.value
                ),
                "supplied_path": str(
                    source.supplied_path
                ),
                "path": str(
                    source.path
                ),
                "size": source.size,
                "sha256": source.sha256,
                "filesystem_provenance": {
                    "modified_time_ns": (
                        filesystem.modified_time_ns
                    ),
                    "change_time_ns": (
                        filesystem.change_time_ns
                    ),
                    "mode": filesystem.mode,
                    "uid": filesystem.uid,
                    "gid": filesystem.gid,
                    "inode": filesystem.inode,
                    "device": filesystem.device,
                    "link_count": (
                        filesystem.link_count
                    ),
                    "device_type": (
                        filesystem.device_type
                    ),
                    "block_size": (
                        filesystem.block_size
                    ),
                    "blocks": (
                        filesystem.blocks
                    ),
                    "birth_time_ns": (
                        filesystem.birth_time_ns
                    ),
                },
            },
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> WorkspaceSourceState:
        """
        Deserialize current workspace source state.
        """

        if not isinstance(
            data,
            dict,
        ):
            raise TypeError(
                "data must be a dictionary"
            )

        schema_version = data.get(
            "schema_version"
        )

        if (
            schema_version
            != cls.SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported workspace source "
                "state schema version"
            )

        source = data.get(
            "source"
        )

        if not isinstance(
            source,
            dict,
        ):
            raise ValueError(
                "source must be a dictionary"
            )

        try:
            provider_id = source[
                "provider_id"
            ]
            source_type = source[
                "source_type"
            ]
            supplied_path = source[
                "supplied_path"
            ]
            path = source[
                "path"
            ]
            size = source[
                "size"
            ]
            digest = source[
                "sha256"
            ]
            filesystem = source[
                "filesystem_provenance"
            ]

        except KeyError as exc:
            raise ValueError(
                "workspace source state is "
                "missing a required source field"
            ) from exc

        if not isinstance(
            provider_id,
            str,
        ):
            raise TypeError(
                "provider_id must be a string"
            )

        if not isinstance(
            source_type,
            str,
        ):
            raise TypeError(
                "source_type must be a string"
            )

        if not isinstance(
            supplied_path,
            str,
        ):
            raise TypeError(
                "supplied_path must be a string"
            )

        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "path must be a string"
            )

        if not isinstance(
            size,
            int,
        ):
            raise TypeError(
                "size must be an integer"
            )

        if not isinstance(
            digest,
            str,
        ):
            raise TypeError(
                "sha256 must be a string"
            )

        if not isinstance(
            filesystem,
            dict,
        ):
            raise TypeError(
                "filesystem_provenance must be "
                "a dictionary"
            )

        filesystem_provenance = (
            cls._filesystem_provenance_from_dict(
                filesystem
            )
        )

        return cls(
            source_identity=(
                ProviderSourceIdentity(
                    provider_id=provider_id,
                    source_type=(
                        ProviderSourceType(
                            source_type
                        )
                    ),
                    supplied_path=Path(
                        supplied_path
                    ),
                    path=Path(
                        path
                    ),
                    size=size,
                    sha256=digest,
                    filesystem_provenance=(
                        filesystem_provenance
                    ),
                )
            )
        )

    @staticmethod
    def _filesystem_provenance_from_dict(
        data: dict[str, Any],
    ) -> ProviderSourceFilesystemProvenance:
        required_fields = (
            "modified_time_ns",
            "change_time_ns",
            "mode",
            "uid",
            "gid",
            "inode",
            "device",
            "link_count",
            "device_type",
        )

        values: dict[
            str,
            int,
        ] = {}

        for field_name in required_fields:
            try:
                value = data[
                    field_name
                ]

            except KeyError as exc:
                raise ValueError(
                    "filesystem_provenance is "
                    "missing required field: "
                    f"{field_name}"
                ) from exc

            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            values[
                field_name
            ] = value

        optional_values: dict[
            str,
            int | None,
        ] = {}

        for field_name in (
            "block_size",
            "blocks",
            "birth_time_ns",
        ):
            value = data.get(
                field_name
            )

            if (
                value is not None
                and not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be "
                    "an int or None"
                )

            optional_values[
                field_name
            ] = value

        return (
            ProviderSourceFilesystemProvenance(
                modified_time_ns=(
                    values[
                        "modified_time_ns"
                    ]
                ),
                change_time_ns=(
                    values[
                        "change_time_ns"
                    ]
                ),
                mode=values[
                    "mode"
                ],
                uid=values[
                    "uid"
                ],
                gid=values[
                    "gid"
                ],
                inode=values[
                    "inode"
                ],
                device=values[
                    "device"
                ],
                link_count=(
                    values[
                        "link_count"
                    ]
                ),
                device_type=(
                    values[
                        "device_type"
                    ]
                ),
                block_size=(
                    optional_values[
                        "block_size"
                    ]
                ),
                blocks=(
                    optional_values[
                        "blocks"
                    ]
                ),
                birth_time_ns=(
                    optional_values[
                        "birth_time_ns"
                    ]
                ),
            )
        )

    def to_json(
        self,
        *,
        indent: int = 2,
    ) -> str:
        """
        Serialize source state to deterministic JSON.
        """

        return json.dumps(
            self.to_dict(),
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_json(
        cls,
        value: str,
    ) -> WorkspaceSourceState:
        """
        Deserialize current workspace source-state JSON.
        """

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        try:
            data = json.loads(
                value
            )

        except json.JSONDecodeError as exc:
            raise ValueError(
                "invalid workspace source "
                "state JSON"
            ) from exc

        return cls.from_dict(
            data
        )