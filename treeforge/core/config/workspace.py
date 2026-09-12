from dataclasses import dataclass
from pathlib import Path

from treeforge.core.models.base import Model


@dataclass
class WorkspaceConfig(Model):
    """Workspace configuration."""

    root: Path = Path.cwd() / "workspace"