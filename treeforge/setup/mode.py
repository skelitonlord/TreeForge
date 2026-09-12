from __future__ import annotations

from enum import Enum
import os
from pathlib import Path
import subprocess


class InstallationCapabilityError(RuntimeError):
    """Raised when the active install mode lacks a required capability."""

    def __init__(
        self,
        *,
        current_mode: "InstallationMode",
        required_mode: "InstallationMode",
        capability: str,
    ) -> None:
        self.current_mode = current_mode
        self.required_mode = required_mode
        self.capability = capability

        super().__init__(
            f"{capability} requires TreeForge "
            f"{required_mode.display_name} mode or higher; "
            f"current mode is {current_mode.display_name}."
        )


class InstallationMode(str, Enum):
    """
    Describe the supported TreeForge installation capability tiers.

    The tiers are cumulative:

    User
        Existing-tree and downstream/consumer functionality.

    Maintainer
        User capabilities plus new-device reconstruction and bring-up.

    Developer
        Maintainer capabilities plus TreeForge project-development tooling.
    """

    USER = "user"
    MAINTAINER = "maintainer"
    DEVELOPER = "developer"

    @property
    def rank(self) -> int:
        return {
            InstallationMode.USER: 0,
            InstallationMode.MAINTAINER: 1,
            InstallationMode.DEVELOPER: 2,
        }[self]

    @property
    def display_name(self) -> str:
        return self.value.capitalize()


def installation_mode_file() -> Path:
    override = os.environ.get(
        "TREEFORGE_MODE_FILE"
    )

    if override:
        return Path(
            override
        ).expanduser()

    config_home = Path(
        os.environ.get(
            "XDG_CONFIG_HOME",
            Path.home() / ".config",
        )
    ).expanduser()

    return (
        config_home
        / "treeforge"
        / "install-mode"
    )


def parse_installation_mode(
    value: str,
) -> InstallationMode:
    normalized = value.strip().lower()

    try:
        return InstallationMode(
            normalized
        )
    except ValueError as exc:
        expected = ", ".join(
            mode.value
            for mode in InstallationMode
        )

        raise ValueError(
            f"Unsupported TreeForge installation mode "
            f"{value!r}. Expected one of: {expected}."
        ) from exc


def _legacy_mode_from_repository(
    repository_root: Path,
) -> InstallationMode:
    """
    Migrate installations created by the former two-mode installer.

    Old Development mode tracked the ``development`` branch and installed
    the full contributor environment. Preserve that capability as
    Developer when no explicit mode has been persisted yet.
    """

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repository_root),
                "branch",
                "--show-current",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
    ):
        return InstallationMode.USER

    branch = result.stdout.strip()

    if branch == "development":
        return InstallationMode.DEVELOPER

    return InstallationMode.USER


def read_installation_mode(
    *,
    repository_root: Path | None = None,
) -> InstallationMode:
    mode_file = installation_mode_file()

    if mode_file.is_file():
        value = mode_file.read_text(
            encoding="utf-8"
        ).strip()

        try:
            return parse_installation_mode(
                value
            )
        except ValueError:
            # Invalid persisted state must never silently grant a higher
            # TreeForge capability tier.
            return InstallationMode.USER

    if repository_root is not None:
        return _legacy_mode_from_repository(
            repository_root
        )

    return InstallationMode.USER


def write_installation_mode(
    mode: InstallationMode,
) -> Path:
    mode_file = installation_mode_file()

    mode_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mode_file.write_text(
        f"{mode.value}\n",
        encoding="utf-8",
    )

    return mode_file


def supports_bringup(
    mode: InstallationMode,
) -> bool:
    return mode.rank >= InstallationMode.MAINTAINER.rank


def supports_maintenance(
    mode: InstallationMode,
) -> bool:
    return mode.rank >= InstallationMode.DEVELOPER.rank



def require_bringup_mode(
    *,
    repository_root: Path | None = None,
) -> InstallationMode:
    """
    Require the capability tier that owns factory-image reconstruction
    and new-device bring-up.
    """

    mode = read_installation_mode(
        repository_root=repository_root,
    )

    if not supports_bringup(mode):
        raise InstallationCapabilityError(
            current_mode=mode,
            required_mode=InstallationMode.MAINTAINER,
            capability="New-device bring-up",
        )

    return mode


# ---------------------------------------------------------------------------
# Installation-mode semantic schema
# ---------------------------------------------------------------------------
#
# Schema 1:
#   user -> developer -> maintainer
#
# Schema 2:
#   user -> maintainer -> developer
#
# The persisted words did not change, but their capability meanings did.
# Existing schema-1 installations must therefore be translated once rather
# than silently reinterpreted.
#
_TREEFORGE_INSTALL_MODE_SCHEMA_VERSION = 2

_treeforge_schema1_read_installation_mode = (
    read_installation_mode
)

_treeforge_schema1_write_installation_mode = (
    write_installation_mode
)


def _treeforge_installation_mode_schema_file() -> Path:
    mode_path = Path(
        installation_mode_file()
    )

    return mode_path.with_name(
        "install-mode-schema"
    )


def _treeforge_migrate_installation_mode_semantics() -> None:
    mode_path = Path(
        installation_mode_file()
    )

    schema_path = (
        _treeforge_installation_mode_schema_file()
    )

    if not mode_path.is_file():
        return

    if schema_path.is_file():
        schema = (
            schema_path
            .read_text(
                encoding="utf-8"
            )
            .strip()
        )

        if schema == str(
            _TREEFORGE_INSTALL_MODE_SCHEMA_VERSION
        ):
            return

    raw = (
        mode_path
        .read_text(
            encoding="utf-8"
        )
        .strip()
    )

    migration = {
        "user": "user",
        "developer": "maintainer",
        "maintainer": "developer",
    }

    migrated = migration.get(
        raw
    )

    if migrated is None:
        return

    mode_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mode_path.write_text(
        migrated + "\n",
        encoding="utf-8",
    )

    schema_path.write_text(
        (
            str(
                _TREEFORGE_INSTALL_MODE_SCHEMA_VERSION
            )
            + "\n"
        ),
        encoding="utf-8",
    )


def read_installation_mode(
    *args,
    **kwargs,
):
    _treeforge_migrate_installation_mode_semantics()

    return (
        _treeforge_schema1_read_installation_mode(
            *args,
            **kwargs,
        )
    )


def write_installation_mode(
    mode,
    *args,
    **kwargs,
):
    result = (
        _treeforge_schema1_write_installation_mode(
            mode,
            *args,
            **kwargs,
        )
    )

    schema_path = (
        _treeforge_installation_mode_schema_file()
    )

    schema_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    schema_path.write_text(
        (
            str(
                _TREEFORGE_INSTALL_MODE_SCHEMA_VERSION
            )
            + "\n"
        ),
        encoding="utf-8",
    )

    return result

