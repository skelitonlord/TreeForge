from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class FbpkEntry:
    """
    One structurally decoded FBPK entry record.

    Only fields proven by physical layout are given semantic names.

    ``record_type`` is the raw leading uint32. Real containers have already
    demonstrated values other than 0/1, so it must not be reduced to a
    boolean.

    ``raw_tail`` preserves the exact trailing uint32 values physically
    present in the version-specific entry record.

    ``payload_offset_bytes`` and ``payload_size_bytes`` preserve payload
    coordinates established by the owning version decoder without forcing
    different FBPK versions into one record layout.

    ``flags_value`` is optional because not every proven FBPK layout exposes a
    flags field.
    """

    index: int
    record_offset: int

    record_type: int
    name: str

    raw_tail: tuple[
        int,
        ...,
    ]

    payload_offset_bytes: int
    payload_size_bytes: int

    flags_value: int | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "index",
                self.index,
            ),
            (
                "record_offset",
                self.record_offset,
            ),
            (
                "record_type",
                self.record_type,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not isinstance(
            self.raw_tail,
            tuple,
        ):
            raise TypeError(
                "raw_tail must be a tuple"
            )

        if not self.raw_tail:
            raise ValueError(
                "raw_tail must not be empty"
            )

        for value in self.raw_tail:
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    "raw_tail must contain non-negative integers"
                )

        for field_name, value in (
            (
                "payload_offset_bytes",
                self.payload_offset_bytes,
            ),
            (
                "payload_size_bytes",
                self.payload_size_bytes,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

        if (
            self.flags_value is not None
            and (
                isinstance(
                    self.flags_value,
                    bool,
                )
                or not isinstance(
                    self.flags_value,
                    int,
                )
                or self.flags_value < 0
            )
        ):
            raise ValueError(
                "flags_value must be a non-negative int or None"
            )

    @property
    def payload_offset(
        self,
    ) -> int:
        return self.payload_offset_bytes

    @property
    def payload_size(
        self,
    ) -> int:
        return self.payload_size_bytes

    @property
    def flags(
        self,
    ) -> int | None:
        return self.flags_value

    @property
    def has_payload(
        self,
    ) -> bool:
        return (
            bool(
                self.name
            )
            and self.payload_offset > 0
            and self.payload_size > 0
        )


@dataclass(
    frozen=True,
    slots=True,
)
class FbpkContainerStructure:
    """
    Immutable physical structure of one supported FBPK container.
    """

    version: int
    header_size: int
    entry_size: int

    table_end: int
    image_size: int

    entries: tuple[
        FbpkEntry,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "version",
                self.version,
            ),
            (
                "header_size",
                self.header_size,
            ),
            (
                "entry_size",
                self.entry_size,
            ),
            (
                "table_end",
                self.table_end,
            ),
            (
                "image_size",
                self.image_size,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

        if self.header_size <= 0:
            raise ValueError(
                "header_size must be greater than zero"
            )

        if self.entry_size <= 0:
            raise ValueError(
                "entry_size must be greater than zero"
            )

        if self.image_size <= 0:
            raise ValueError(
                "image_size must be greater than zero"
            )

        if self.table_end > self.image_size:
            raise ValueError(
                "table_end cannot exceed image_size"
            )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                FbpkEntry,
            )
            for entry in self.entries
        ):
            raise TypeError(
                "entries must contain only FbpkEntry instances"
            )

    @property
    def payload_entries(
        self,
    ) -> tuple[
        FbpkEntry,
        ...,
    ]:
        return tuple(
            entry
            for entry in self.entries
            if entry.has_payload
        )
