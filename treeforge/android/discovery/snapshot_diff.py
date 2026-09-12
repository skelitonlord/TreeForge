from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.discovery.snapshot import (
    AndroidDiscoveryArtifactSnapshot,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryArtifactChange:
    """
    One changed artifact between two Discovery snapshots.

    before and after share the same canonical source_name.

    changed_fields contains only stable Discovery snapshot fields whose values
    differ between the two snapshots.
    """

    before: AndroidDiscoveryArtifactSnapshot

    after: AndroidDiscoveryArtifactSnapshot

    changed_fields: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.before,
            AndroidDiscoveryArtifactSnapshot,
        ):
            raise TypeError(
                "before must be an "
                "AndroidDiscoveryArtifactSnapshot"
            )

        if not isinstance(
            self.after,
            AndroidDiscoveryArtifactSnapshot,
        ):
            raise TypeError(
                "after must be an "
                "AndroidDiscoveryArtifactSnapshot"
            )

        if (
            self.before.source_name
            != self.after.source_name
        ):
            raise ValueError(
                "changed artifacts must preserve "
                "the same source_name"
            )

        if not isinstance(
            self.changed_fields,
            tuple,
        ):
            raise TypeError(
                "changed_fields must be a tuple"
            )

        for field_name in self.changed_fields:
            if not isinstance(
                field_name,
                str,
            ):
                raise TypeError(
                    "changed_fields must contain strings"
                )

            if not field_name.strip():
                raise ValueError(
                    "changed_fields must not contain "
                    "empty values"
                )

        canonical = tuple(
            sorted(
                set(
                    self.changed_fields
                )
            )
        )

        if not canonical:
            raise ValueError(
                "changed_fields must not be empty"
            )

        object.__setattr__(
            self,
            "changed_fields",
            canonical,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoverySnapshotDiff:
    """
    Immutable Discovery-to-Discovery comparison result.

    No interpretation of why a difference occurred is performed here.
    """

    added: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    removed: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    changed: tuple[
        AndroidDiscoveryArtifactChange,
        ...,
    ] = ()

    unchanged: tuple[
        AndroidDiscoveryArtifactSnapshot,
        ...,
    ] = ()

    device_before: str | None = None

    device_after: str | None = None

    android_version_before: str | None = None

    android_version_after: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for (
            field_name,
            values,
            expected_type,
        ) in (
            (
                "added",
                self.added,
                AndroidDiscoveryArtifactSnapshot,
            ),
            (
                "removed",
                self.removed,
                AndroidDiscoveryArtifactSnapshot,
            ),
            (
                "changed",
                self.changed,
                AndroidDiscoveryArtifactChange,
            ),
            (
                "unchanged",
                self.unchanged,
                AndroidDiscoveryArtifactSnapshot,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            for value in values:
                if not isinstance(
                    value,
                    expected_type,
                ):
                    raise TypeError(
                        f"{field_name} contains an "
                        "invalid value"
                    )

        object.__setattr__(
            self,
            "added",
            tuple(
                sorted(
                    self.added,
                    key=lambda artifact: (
                        artifact.source_name
                    ),
                )
            ),
        )

        object.__setattr__(
            self,
            "removed",
            tuple(
                sorted(
                    self.removed,
                    key=lambda artifact: (
                        artifact.source_name
                    ),
                )
            ),
        )

        object.__setattr__(
            self,
            "changed",
            tuple(
                sorted(
                    self.changed,
                    key=lambda change: (
                        change.before.source_name
                    ),
                )
            ),
        )

        object.__setattr__(
            self,
            "unchanged",
            tuple(
                sorted(
                    self.unchanged,
                    key=lambda artifact: (
                        artifact.source_name
                    ),
                )
            ),
        )

    @property
    def added_count(
        self,
    ) -> int:
        return len(
            self.added
        )

    @property
    def removed_count(
        self,
    ) -> int:
        return len(
            self.removed
        )

    @property
    def changed_count(
        self,
    ) -> int:
        return len(
            self.changed
        )

    @property
    def unchanged_count(
        self,
    ) -> int:
        return len(
            self.unchanged
        )

    @property
    def device_changed(
        self,
    ) -> bool:
        return (
            self.device_before
            != self.device_after
        )

    @property
    def android_version_changed(
        self,
    ) -> bool:
        return (
            self.android_version_before
            != self.android_version_after
        )

    @property
    def has_artifact_changes(
        self,
    ) -> bool:
        return bool(
            self.added
            or self.removed
            or self.changed
        )

    @property
    def newly_unknown(
        self,
    ) -> tuple[
        AndroidDiscoveryArtifactChange,
        ...,
    ]:
        """
        Return matching artifacts that changed from known to unknown semantics.
        """

        return tuple(
            change
            for change in self.changed
            if (
                not change.before.is_semantically_unknown
                and change.after.is_semantically_unknown
            )
        )

    @property
    def newly_understood(
        self,
    ) -> tuple[
        AndroidDiscoveryArtifactChange,
        ...,
    ]:
        """
        Return matching artifacts that changed from unknown to known semantics.
        """

        return tuple(
            change
            for change in self.changed
            if (
                change.before.is_semantically_unknown
                and not change.after.is_semantically_unknown
            )
        )