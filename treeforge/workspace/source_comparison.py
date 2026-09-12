from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from treeforge.android.providers.source_identity import (
    ProviderSourceIdentity,
)
from treeforge.workspace.source_state import (
    WorkspaceSourceState,
)


class WorkspaceSourceStatus(
    str,
    Enum,
):
    """
    Classification of persisted workspace source state.
    """

    UNINITIALIZED = "uninitialized"
    MATCH = "match"
    MOVED = "moved"
    CHANGED = "changed"
    MISSING = "missing"


@dataclass(
    frozen=True,
    slots=True,
)
class WorkspaceSourceComparison:
    """
    Immutable comparison between persisted and current source state.
    """

    status: WorkspaceSourceStatus

    previous: WorkspaceSourceState | None

    current: ProviderSourceIdentity | None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.status,
            WorkspaceSourceStatus,
        ):
            raise TypeError(
                "status must be a WorkspaceSourceStatus"
            )

        if (
            self.previous is not None
            and not isinstance(
                self.previous,
                WorkspaceSourceState,
            )
        ):
            raise TypeError(
                "previous must be a "
                "WorkspaceSourceState or None"
            )

        if (
            self.current is not None
            and not isinstance(
                self.current,
                ProviderSourceIdentity,
            )
        ):
            raise TypeError(
                "current must be a "
                "ProviderSourceIdentity or None"
            )

    @property
    def can_reuse_extraction(
        self,
    ) -> bool:
        """
        Return whether extraction derived from the source may be reused.

        Reuse depends on exact source content, not on the particular host
        filesystem instance containing those bytes.
        """

        return self.status in {
            WorkspaceSourceStatus.MATCH,
            WorkspaceSourceStatus.MOVED,
        }


class WorkspaceSourceComparator:
    """
    Compare persisted source state with a current provider source.

    Source-content equivalence is intentionally based only on:

        provider_id
        source_type
        size
        sha256

    Host filesystem provenance is evidence only and never changes source
    equivalence.

    The canonical resolved path is used only to distinguish MATCH from MOVED.
    """

    def compare(
        self,
        previous: WorkspaceSourceState | None,
        current: ProviderSourceIdentity | None,
    ) -> WorkspaceSourceComparison:
        if (
            previous is not None
            and not isinstance(
                previous,
                WorkspaceSourceState,
            )
        ):
            raise TypeError(
                "previous must be a "
                "WorkspaceSourceState or None"
            )

        if (
            current is not None
            and not isinstance(
                current,
                ProviderSourceIdentity,
            )
        ):
            raise TypeError(
                "current must be a "
                "ProviderSourceIdentity or None"
            )

        if previous is None:
            return (
                WorkspaceSourceComparison(
                    status=(
                        WorkspaceSourceStatus
                        .UNINITIALIZED
                    ),
                    previous=None,
                    current=current,
                )
            )

        previous_identity = (
            previous.source_identity
        )

        if current is None:
            return (
                WorkspaceSourceComparison(
                    status=(
                        WorkspaceSourceStatus
                        .MISSING
                    ),
                    previous=previous,
                    current=None,
                )
            )

        if (
            previous_identity.provider_id
            != current.provider_id
            or previous_identity.source_type
            is not current.source_type
        ):
            return (
                WorkspaceSourceComparison(
                    status=(
                        WorkspaceSourceStatus
                        .CHANGED
                    ),
                    previous=previous,
                    current=current,
                )
            )

        if (
            previous_identity.size
            != current.size
            or previous_identity.sha256
            != current.sha256
        ):
            return (
                WorkspaceSourceComparison(
                    status=(
                        WorkspaceSourceStatus
                        .CHANGED
                    ),
                    previous=previous,
                    current=current,
                )
            )

        if (
            previous_identity.path
            != current.path
        ):
            return (
                WorkspaceSourceComparison(
                    status=(
                        WorkspaceSourceStatus
                        .MOVED
                    ),
                    previous=previous,
                    current=current,
                )
            )

        return (
            WorkspaceSourceComparison(
                status=(
                    WorkspaceSourceStatus
                    .MATCH
                ),
                previous=previous,
                current=current,
            )
        )