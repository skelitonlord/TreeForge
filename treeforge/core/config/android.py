from dataclasses import dataclass

from treeforge.core.models.base import Model


@dataclass
class AndroidConfig(Model):
    """Android-specific configuration."""

    target_version: int = 16