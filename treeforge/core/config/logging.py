from dataclasses import dataclass

from treeforge.core.models.base import Model


@dataclass
class LoggingConfig(Model):
    """Logging configuration."""

    level: str = "INFO"
    verbose: bool = False