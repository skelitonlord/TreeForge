from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderArtifactProvenance:
    """
    Immutable discovery provenance for one provider artifact.

    This model preserves all useful source evidence that is authoritatively
    available when an artifact is discovered.

    For archive members, raw ZIP directory-entry metadata is retained without
    interpreting it. Later TreeForge layers may add materialization,
    extraction, format, filesystem, parsing, or derivation provenance without
    replacing this original discovery lineage.

    Discovery provenance describes where an artifact came from and what the
    source container said about it. It does not describe extracted contents.
    """

    # ------------------------------------------------------------------
    # Discovery lineage
    # ------------------------------------------------------------------

    parent_source_name: str | None = None

    member_path: str | None = None

    original_member_path: str | None = None

    container_depth: int = 0

    # ------------------------------------------------------------------
    # Payload size / compression evidence
    # ------------------------------------------------------------------

    size_bytes: int | None = None

    compressed_size_bytes: int | None = None

    compression_method: int | None = None

    crc32: int | None = None

    # ------------------------------------------------------------------
    # ZIP timestamp evidence
    # ------------------------------------------------------------------

    modified_time: (
        tuple[
            int,
            int,
            int,
            int,
            int,
            int,
        ]
        | None
    ) = None

    # ------------------------------------------------------------------
    # ZIP general-purpose / compatibility metadata
    # ------------------------------------------------------------------

    flag_bits: int | None = None

    create_system: int | None = None

    create_version: int | None = None

    extract_version: int | None = None

    volume: int | None = None

    # ------------------------------------------------------------------
    # ZIP attribute evidence
    # ------------------------------------------------------------------

    internal_attributes: int | None = None

    external_attributes: int | None = None

    # ------------------------------------------------------------------
    # Raw ZIP extension evidence
    # ------------------------------------------------------------------

    extra: bytes | None = None

    comment: bytes | None = None

    # ------------------------------------------------------------------
    # Physical container-location evidence
    # ------------------------------------------------------------------

    header_offset: int | None = None

    def __post_init__(
        self,
    ) -> None:
        self._validate_optional_string(
            self.parent_source_name,
            field_name="parent_source_name",
        )

        self._validate_optional_string(
            self.member_path,
            field_name="member_path",
        )

        self._validate_optional_string(
            self.original_member_path,
            field_name="original_member_path",
        )

        self._validate_nonnegative_int(
            self.container_depth,
            field_name="container_depth",
            optional=False,
        )

        for (
            field_name,
            value,
        ) in (
            (
                "size_bytes",
                self.size_bytes,
            ),
            (
                "compressed_size_bytes",
                self.compressed_size_bytes,
            ),
            (
                "compression_method",
                self.compression_method,
            ),
            (
                "crc32",
                self.crc32,
            ),
            (
                "flag_bits",
                self.flag_bits,
            ),
            (
                "create_system",
                self.create_system,
            ),
            (
                "create_version",
                self.create_version,
            ),
            (
                "extract_version",
                self.extract_version,
            ),
            (
                "volume",
                self.volume,
            ),
            (
                "internal_attributes",
                self.internal_attributes,
            ),
            (
                "external_attributes",
                self.external_attributes,
            ),
            (
                "header_offset",
                self.header_offset,
            ),
        ):
            self._validate_nonnegative_int(
                value,
                field_name=field_name,
            )

        if self.modified_time is not None:
            self._validate_modified_time(
                self.modified_time
            )

        for (
            field_name,
            value,
        ) in (
            (
                "extra",
                self.extra,
            ),
            (
                "comment",
                self.comment,
            ),
        ):
            self._validate_optional_bytes(
                value,
                field_name=field_name,
            )

        if (
            self.parent_source_name is None
            and self.container_depth != 0
        ):
            raise ValueError(
                "container_depth must be 0 when "
                "parent_source_name is None"
            )

        if (
            self.parent_source_name is not None
            and self.container_depth == 0
        ):
            raise ValueError(
                "container_depth must be greater than 0 "
                "when parent_source_name is present"
            )

        if (
            self.member_path is None
            and self.original_member_path
            is not None
        ):
            raise ValueError(
                "original_member_path requires "
                "member_path"
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
                f"{field_name} must be a string or None"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )

    @staticmethod
    def _validate_nonnegative_int(
        value: object,
        *,
        field_name: str,
        optional: bool = True,
    ) -> None:
        if value is None:
            if optional:
                return

            raise TypeError(
                f"{field_name} must be an int"
            )

        if not isinstance(
            value,
            int,
        ):
            suffix = (
                " or None"
                if optional
                else ""
            )

            raise TypeError(
                f"{field_name} must be an int"
                f"{suffix}"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )

    @staticmethod
    def _validate_optional_bytes(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if not isinstance(
            value,
            bytes,
        ):
            raise TypeError(
                f"{field_name} must be bytes or None"
            )

    @staticmethod
    def _validate_modified_time(
        value: object,
    ) -> None:
        if not isinstance(
            value,
            tuple,
        ):
            raise TypeError(
                "modified_time must be a tuple or None"
            )

        if len(value) != 6:
            raise ValueError(
                "modified_time must contain exactly "
                "6 integer components"
            )

        if not all(
            isinstance(
                component,
                int,
            )
            for component in value
        ):
            raise TypeError(
                "modified_time components must be integers"
            )

        (
            year,
            month,
            day,
            hour,
            minute,
            second,
        ) = value

        if year < 0:
            raise ValueError(
                "modified_time year must not be negative"
            )

        if not 1 <= month <= 12:
            raise ValueError(
                "modified_time month must be between 1 and 12"
            )

        if not 1 <= day <= 31:
            raise ValueError(
                "modified_time day must be between 1 and 31"
            )

        if not 0 <= hour <= 23:
            raise ValueError(
                "modified_time hour must be between 0 and 23"
            )

        if not 0 <= minute <= 59:
            raise ValueError(
                "modified_time minute must be between 0 and 59"
            )

        if not 0 <= second <= 59:
            raise ValueError(
                "modified_time second must be between 0 and 59"
            )

    @property
    def is_archive_member(
        self,
    ) -> bool:
        """
        Return whether this provenance describes an archive member.
        """

        return (
            self.parent_source_name
            is not None
        )

    @property
    def has_archive_metadata(
        self,
    ) -> bool:
        """
        Return whether any archive-specific evidence is available.
        """

        return any(
            value is not None
            for value in (
                self.member_path,
                self.original_member_path,
                self.size_bytes,
                self.compressed_size_bytes,
                self.compression_method,
                self.crc32,
                self.modified_time,
                self.flag_bits,
                self.create_system,
                self.create_version,
                self.extract_version,
                self.volume,
                self.internal_attributes,
                self.external_attributes,
                self.extra,
                self.comment,
                self.header_offset,
            )
        )

    @property
    def member_name_was_normalized(
        self,
    ) -> bool:
        """
        Return whether the archive library exposed a normalized member name.

        False is returned when original-member evidence is unavailable.
        """

        if (
            self.member_path is None
            or self.original_member_path
            is None
        ):
            return False

        return (
            self.member_path
            != self.original_member_path
        )

    @property
    def compression_ratio(
        self,
    ) -> float | None:
        """
        Return compressed-size / original-size when meaningful.

        This is a derived convenience view only. The authoritative evidence
        remains the two raw size fields.
        """

        if (
            self.size_bytes is None
            or self.compressed_size_bytes
            is None
            or self.size_bytes == 0
        ):
            return None

        return (
            self.compressed_size_bytes
            / self.size_bytes
        )