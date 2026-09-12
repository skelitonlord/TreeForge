from dataclasses import dataclass, field

from treeforge.core.models.base import Model
from treeforge.core.config.android import AndroidConfig
from treeforge.core.config.logging import LoggingConfig
from treeforge.core.config.workspace import WorkspaceConfig


@dataclass
class Config(Model):
    """Global TreeForge configuration."""

    workspace: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    android: AndroidConfig = field(default_factory=AndroidConfig)