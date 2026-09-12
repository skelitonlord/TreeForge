from __future__ import annotations

import tomllib
from pathlib import Path

from treeforge.core.config.config import Config


def load_config(path: Path | None = None) -> Config:
    """Load the TreeForge configuration."""

    config = Config()

    if path is None:
        path = Path("treeforge.toml")

    if not path.exists():
        return config

    with path.open("rb") as fp:
        data = tomllib.load(fp)

    workspace = data.get("workspace", {})
    logging = data.get("logging", {})
    android = data.get("android", {})

    workspace_root = workspace.get(
        "root",
    )

    if workspace_root is not None:
        config.workspace.root = Path(
            workspace_root
    )
    config.logging.level = logging.get(
        "level",
        config.logging.level,
    )

    config.logging.verbose = logging.get(
        "verbose",
        config.logging.verbose,
    )

    config.android.target_version = android.get(
        "target_version",
        config.android.target_version,
    )

    return config