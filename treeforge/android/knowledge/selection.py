from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidKnowledgeSelectionSource(
    StrEnum,
):
    """
    Origin of one selected Knowledge root.
    """

    EXPLICIT = "explicit"
    INFERRED = "inferred"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidKnowledgeRootSelection:
    """
    One resolved top-level Knowledge selection.

    module_id identifies a device/platform/OEM Knowledge registry module.
    """

    module_id: str
    source: AndroidKnowledgeSelectionSource

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.module_id,
            str,
        ):
            raise TypeError(
                "module_id must be a string"
            )

        if not self.module_id.strip():
            raise ValueError(
                "module_id must not be empty"
            )

        if not isinstance(
            self.source,
            AndroidKnowledgeSelectionSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidKnowledgeSelectionSource"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidKnowledgeSelection:
    """
    Requested top-level Android Knowledge identities.

    Android platform version is intentionally not a Knowledge identity.
    """

    device_id: str | None = None
    board_platform: str | None = None

    def __post_init__(
        self,
    ) -> None:
        self._validate_optional_string(
            self.device_id,
            field_name="device_id",
        )

        self._validate_optional_string(
            self.board_platform,
            field_name="board_platform",
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return (
            self.device_id is None
            and self.board_platform is None
        )

    def explicit_roots(
        self,
    ) -> tuple[
        AndroidKnowledgeRootSelection,
        ...,
    ]:
        roots: list[
            AndroidKnowledgeRootSelection
        ] = []

        if self.device_id is not None:
            roots.append(
                AndroidKnowledgeRootSelection(
                    module_id=(
                        f"device:{self.device_id}"
                    ),
                    source=(
                        AndroidKnowledgeSelectionSource
                        .EXPLICIT
                    ),
                )
            )

        if self.board_platform is not None:
            roots.append(
                AndroidKnowledgeRootSelection(
                    module_id=(
                        f"platform:{self.board_platform}"
                    ),
                    source=(
                        AndroidKnowledgeSelectionSource
                        .EXPLICIT
                    ),
                )
            )

        return tuple(
            roots
        )

    @staticmethod
    def _validate_optional_string(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be "
                "a string or None"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )
