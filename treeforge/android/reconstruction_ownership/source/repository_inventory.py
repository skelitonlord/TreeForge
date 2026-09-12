from __future__ import annotations

from pathlib import Path
import subprocess

from treeforge.android.reconstruction_ownership.source.model import (
    AndroidSourceRepository,
    AndroidSourceRepositoryInventory,
    AndroidSourceRepositoryKind,
)


class AndroidSourceRepositoryInventoryBuilder:
    """
    Build a checkout repository inventory from Repo's canonical project list.

    This does not infer target relevance.  It records physical source project
    boundaries so later source evidence cannot accidentally cross from generic
    platform source into device/vendor-specific repositories.
    """

    @staticmethod
    def build(
        checkout_root: Path,
    ) -> AndroidSourceRepositoryInventory:
        checkout_root = Path(
            checkout_root
        ).expanduser().resolve()

        project_list = (
            checkout_root
            / ".repo"
            / "project.list"
        )

        if not project_list.is_file():
            raise FileNotFoundError(
                "Android source checkout does not contain "
                ".repo/project.list"
            )

        repositories = []

        for raw in project_list.read_text(
            encoding="utf-8",
        ).splitlines():
            project_path = raw.strip()

            if not project_path:
                continue

            source_path = (
                checkout_root
                / project_path
            )

            revision = (
                AndroidSourceRepositoryInventoryBuilder
                ._revision_for(
                    checkout_root=checkout_root,
                    project_path=project_path,
                )
            )

            repositories.append(
                AndroidSourceRepository(
                    project_path=project_path,
                    checkout_path=source_path,
                    kind=(
                        AndroidSourceRepositoryInventoryBuilder
                        ._classify_project(
                            project_path
                        )
                    ),
                    revision=revision,
                )
            )

        repositories.sort(
            key=lambda repository: (
                repository.project_path
            )
        )

        return AndroidSourceRepositoryInventory(
            checkout_root=checkout_root,
            repositories=tuple(
                repositories
            ),
        )

    @staticmethod
    def _revision_for(
        *,
        checkout_root: Path,
        project_path: str,
    ) -> str | None:
        git_dir = (
            checkout_root
            / ".repo"
            / "projects"
            / f"{project_path}.git"
        )

        if not git_dir.is_dir():
            return None

        completed = subprocess.run(
            (
                "git",
                f"--git-dir={git_dir}",
                "rev-parse",
                "HEAD",
            ),
            check=False,
            capture_output=True,
            text=True,
        )

        if completed.returncode != 0:
            return None

        revision = completed.stdout.strip()

        return revision or None

    @staticmethod
    def _classify_project(
        project_path: str,
    ) -> AndroidSourceRepositoryKind:
        parts = tuple(
            part
            for part in project_path.split("/")
            if part
        )

        lowered = project_path.lower()

        if (
            "-sepolicy" in lowered
            or lowered.endswith("/sepolicy")
            or "pixel-sepolicy" in lowered
        ):
            return AndroidSourceRepositoryKind.SEPOLICY_TREE

        if (
            project_path.startswith("kernel/")
            or "-kernel/" in lowered
            or "-kernels/" in lowered
            or lowered.endswith("-kernel")
        ):
            return AndroidSourceRepositoryKind.KERNEL_TREE

        if project_path.startswith("device/"):
            return AndroidSourceRepositoryKind.DEVICE_TREE

        if project_path.startswith("vendor/"):
            return AndroidSourceRepositoryKind.VENDOR_TREE

        if project_path.startswith("hardware/"):
            return AndroidSourceRepositoryKind.HARDWARE_TREE

        if not parts:
            return AndroidSourceRepositoryKind.UNKNOWN

        #
        # Remaining Repo projects are structurally part of the Android
        # source checkout.  Target relevance is still resolved separately.
        #
        return AndroidSourceRepositoryKind.AOSP_PLATFORM
