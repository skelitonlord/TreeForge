from __future__ import annotations

from pathlib import Path

from treeforge.workspace.source_state import (
    WorkspaceSourceState,
)
from treeforge.workspace.workspace import (
    Workspace,
)


class WorkspaceSourceStateStore:
    """
    Persist workspace source state beneath one runtime workspace.

    The store owns only file persistence. It does not compare source
    identities or decide whether extraction state may be reused.
    """

    filename = "source.json"

    def __init__(
        self,
        workspace: Workspace,
    ) -> None:
        if not isinstance(
            workspace,
            Workspace,
        ):
            raise TypeError(
                "workspace must be a Workspace"
            )

        self.workspace = workspace
        self.destination = (
            workspace.state
            / self.filename
        )

    def exists(
        self,
    ) -> bool:
        """Return whether persisted source state exists."""

        return self.destination.is_file()

    def save(
        self,
        state: WorkspaceSourceState,
    ) -> Path:
        """
        Persist source state atomically.

        Data is written to a temporary sibling and then replaced so
        interrupted writes do not leave a partial source.json.
        """

        if not isinstance(
            state,
            WorkspaceSourceState,
        ):
            raise TypeError(
                "state must be a WorkspaceSourceState"
            )

        self.workspace.state.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            self.destination.with_suffix(
                ".json.tmp"
            )
        )

        temporary_path.write_text(
            state.to_json()
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(
            self.destination
        )

        return self.destination

    def load(
        self,
    ) -> WorkspaceSourceState | None:
        """
        Load persisted source state.

        Missing state is represented as None rather than an error.
        """

        if not self.destination.exists():
            return None

        if not self.destination.is_file():
            raise ValueError(
                "workspace source state path "
                "must be a file"
            )

        value = self.destination.read_text(
            encoding="utf-8",
        )

        return (
            WorkspaceSourceState.from_json(
                value
            )
        )