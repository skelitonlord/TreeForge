from pathlib import Path


class Workspace:
    """Represents a TreeForge workspace."""

    def __init__(
        self,
        root: Path,
    ) -> None:
        self.root = root

        self.cache = root / "cache"
        self.images = root / "images"
        self.reports = root / "reports"
        self.generated = root / "generated"
        self.logs = root / "logs"
        self.state = root / "state"

    def create(self) -> None:
        """Create the workspace directory structure."""

        directories = [
            self.root,
            self.cache,
            self.images,
            self.reports,
            self.generated,
            self.logs,
            self.state,
        ]

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    def prune_empty_managed_directories(
        self,
    ) -> None:
        """
        Remove unused empty standard workspace directories.

        Workspace.create() remains eager for compatibility with existing
        consumers. TreeForge removes only managed directories that remain
        completely empty after execution.

        No file or non-empty directory is ever removed.
        """

        for directory in (
            self.cache,
            self.generated,
            self.state,
            self.reports,
            self.logs,
            self.images,
        ):
            try:
                directory.rmdir()
            except FileNotFoundError:
                continue
            except OSError:
                # Non-empty or otherwise in use: preserve it.
                continue

