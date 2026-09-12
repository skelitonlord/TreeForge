from __future__ import annotations

from pathlib import Path

from treeforge.android.providers.source_identity import ProviderSourceIdentity
from treeforge.android.providers.source_type import ProviderSourceType
from treeforge.workspace.source_comparison import (
    WorkspaceSourceComparator,
    WorkspaceSourceComparison,
)
from treeforge.workspace.source_state import (
    WorkspaceSourceState,
)
from treeforge.workspace.source_state_store import (
    WorkspaceSourceStateStore,
)
from treeforge.workspace.workspace import (
    Workspace,
)


class WorkspaceSourceService:
    """
    Coordinate persistent workspace source identity.

    The service compares one current provider source against the
    previously persisted workspace source state.

    Comparison does not mutate persisted state. Saving the current
    identity is explicit so callers can persist it only after the
    workspace has been successfully accepted or reconciled.
    """

    def __init__(
        self,
        workspace: Workspace,
        *,
        store: WorkspaceSourceStateStore | None = None,
        comparator: WorkspaceSourceComparator | None = None,
    ) -> None:
        if not isinstance(
            workspace,
            Workspace,
        ):
            raise TypeError(
                "workspace must be a Workspace"
            )

        if (
            store is not None
            and not isinstance(
                store,
                WorkspaceSourceStateStore,
            )
        ):
            raise TypeError(
                "store must be a "
                "WorkspaceSourceStateStore or None"
            )

        if (
            comparator is not None
            and not isinstance(
                comparator,
                WorkspaceSourceComparator,
            )
        ):
            raise TypeError(
                "comparator must be a "
                "WorkspaceSourceComparator or None"
            )

        self.workspace = workspace

        self.store = (
            store
            if store is not None
            else WorkspaceSourceStateStore(
                workspace
            )
        )

        self.comparator = (
            comparator
            if comparator is not None
            else WorkspaceSourceComparator()
        )

    def compare_current(
        self,
        path: Path,
        *,
        provider_id: str,
        source_type: ProviderSourceType,
    ) -> WorkspaceSourceComparison:
        """
        Compare one current file-backed source against persisted state.
        """

        current = (
            ProviderSourceIdentity.from_path(
                path,
                provider_id=provider_id,
                source_type=source_type,
            )
        )

        previous = self.store.load()

        return self.comparator.compare(
            previous,
            current,
        )

    def compare_missing(
        self,
    ) -> WorkspaceSourceComparison:
        """
        Compare persisted state when no current source is available.
        """

        previous = self.store.load()

        return self.comparator.compare(
            previous,
            None,
        )

    def save_current(
        self,
        source_identity: ProviderSourceIdentity,
    ) -> Path:
        """
        Persist one accepted current source identity.
        """

        if not isinstance(
            source_identity,
            ProviderSourceIdentity,
        ):
            raise TypeError(
                "source_identity must be a "
                "ProviderSourceIdentity"
            )

        state = WorkspaceSourceState(
            source_identity=source_identity,
        )

        return self.store.save(
            state
        )