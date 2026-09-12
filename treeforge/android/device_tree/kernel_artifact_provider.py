from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import tomllib


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeKernelArtifact:
    """
    One resolved TreeForge kernel artifact supplied to Device Tree.

    The model is provider-neutral. The current resolver uses a local
    TreeForge kernel workspace. A future GitHub Release provider can
    return the same model without changing Device Tree construction.
    """

    provider: str
    source_mode: str

    profile_id: str
    android_profile: str

    path: Path

    size_bytes: int
    sha256: str

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "provider",
                self.provider,
            ),
            (
                "source_mode",
                self.source_mode,
            ),
            (
                "profile_id",
                self.profile_id,
            ),
            (
                "android_profile",
                self.android_profile,
            ),
            (
                "sha256",
                self.sha256,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if self.source_mode not in {
            "baseline",
            "modified",
        }:
            raise ValueError(
                "source_mode must be baseline or modified"
            )

        if not isinstance(
            self.path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        if (
            isinstance(
                self.size_bytes,
                bool,
            )
            or not isinstance(
                self.size_bytes,
                int,
            )
            or self.size_bytes <= 0
        ):
            raise ValueError(
                "size_bytes must be a positive int"
            )

        if (
            len(self.sha256) != 64
            or any(
                character
                not in "0123456789abcdef"
                for character
                in self.sha256
            )
        ):
            raise ValueError(
                "sha256 must be a lowercase SHA-256 digest"
            )


class AndroidDeviceTreeLocalKernelArtifactProvider:
    """
    Resolve an already-packaged boot.img from a local TreeForge
    kernel workspace.

    This provider never builds a kernel, boots a device, flashes a
    partition, or changes a slot.
    """

    ENVIRONMENT_ROOT = "TREEFORGE_KERNEL_ROOT"

    @classmethod
    def default_kernel_root(
        cls,
    ) -> Path:
        configured = os.environ.get(
            cls.ENVIRONMENT_ROOT
        )

        if configured:
            return (
                Path(configured)
                .expanduser()
                .resolve()
            )

        return (
            Path.home()
            / "development"
            / "kernel"
            / "treeforge_kernel"
        ).resolve()

    @staticmethod
    def file_identity(
        path: Path,
    ) -> tuple[int, str]:
        if not path.is_file():
            raise FileNotFoundError(
                "local TreeForge kernel artifact is unavailable: "
                f"{path}"
            )

        digest = sha256()
        size = 0

        with path.open(
            "rb",
        ) as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                size += len(
                    chunk
                )

                digest.update(
                    chunk
                )

        if size <= 0:
            raise ValueError(
                "local TreeForge kernel artifact is empty: "
                f"{path}"
            )

        return (
            size,
            digest.hexdigest(),
        )

    @classmethod
    def resolve(
        cls,
        *,
        device: str,
        source_mode: str,
        kernel_root: Path | None = None,
    ) -> AndroidDeviceTreeKernelArtifact:
        if (
            not isinstance(
                device,
                str,
            )
            or not device
        ):
            raise ValueError(
                "kernel artifact device must be a non-empty string"
            )

        if source_mode not in {
            "baseline",
            "modified",
        }:
            raise ValueError(
                "kernel artifact source must be baseline or modified"
            )

        root = (
            kernel_root
            .expanduser()
            .resolve()
            if kernel_root is not None
            else cls.default_kernel_root()
        )

        profiles_root = (
            root
            / "profiles"
        )

        if not profiles_root.is_dir():
            raise FileNotFoundError(
                "TreeForge kernel profiles are unavailable: "
                f"{profiles_root}"
            )

        matches = []

        # Profiles are allowed to be grouped by device, so search
        # recursively rather than assuming profiles/*.toml.
        for profile_path in sorted(
            profiles_root.rglob(
                "*.toml"
            ),
            key=lambda candidate: candidate.as_posix(),
        ):
            with profile_path.open(
                "rb",
            ) as handle:
                profile = tomllib.load(
                    handle
                )

            if profile.get(
                "device"
            ) != device:
                continue

            matches.append(
                (
                    profile_path,
                    profile,
                )
            )

        if not matches:
            raise RuntimeError(
                "no local TreeForge kernel profile matches "
                f"device={device!r}"
            )

        if len(matches) != 1:
            candidates = tuple(
                str(
                    profile_path
                    .relative_to(root)
                )
                for profile_path, _
                in matches
            )

            raise RuntimeError(
                "local TreeForge kernel profile selection is "
                "ambiguous; an explicit profile selector will be "
                "required before multiple Android profiles for the "
                "same device can be consumed: "
                f"{candidates!r}"
            )

        profile_path, profile = matches[0]

        profile_id = profile.get(
            "id"
        )

        android_profile = profile.get(
            "android_profile"
        )

        if (
            not isinstance(
                profile_id,
                str,
            )
            or not profile_id
        ):
            raise ValueError(
                f"kernel profile lost id: {profile_path}"
            )

        if (
            not isinstance(
                android_profile,
                str,
            )
            or not android_profile
        ):
            raise ValueError(
                "kernel profile lost android_profile: "
                f"{profile_path}"
            )

        deliverables = profile.get(
            "deliverables",
            [],
        )

        if (
            not isinstance(
                deliverables,
                list,
            )
            or "boot.img"
            not in deliverables
        ):
            raise ValueError(
                "selected kernel profile does not declare "
                f"boot.img as a deliverable: {profile_id}"
            )

        source = profile.get(
            "source",
            {},
        )

        enabled_name = (
            f"{source_mode}_enabled"
        )

        if (
            not isinstance(
                source,
                dict,
            )
            or source.get(
                enabled_name
            )
            is not True
        ):
            raise ValueError(
                "selected kernel profile does not enable "
                f"{source_mode!r}: {profile_id}"
            )

        package = profile.get(
            "package",
            {},
        )

        boot_package = (
            package.get(
                "boot",
                {},
            )
            if isinstance(
                package,
                dict,
            )
            else {}
        )

        if (
            not isinstance(
                boot_package,
                dict,
            )
            or boot_package.get(
                "partition"
            )
            != "boot"
        ):
            raise ValueError(
                "selected kernel profile does not describe "
                f"boot partition packaging: {profile_id}"
            )

        artifact_path = (
            root
            / "out"
            / device
            / android_profile
            / source_mode
            / "package"
            / "boot.img"
        ).resolve()

        size_bytes, digest = (
            cls.file_identity(
                artifact_path
            )
        )

        partition_size = (
            boot_package.get(
                "partition_size"
            )
        )

        if (
            isinstance(
                partition_size,
                int,
            )
            and not isinstance(
                partition_size,
                bool,
            )
            and partition_size > 0
            and size_bytes > partition_size
        ):
            raise ValueError(
                "local TreeForge kernel boot.img exceeds "
                "the declared boot partition size: "
                f"{size_bytes} > {partition_size}"
            )

        return AndroidDeviceTreeKernelArtifact(
            provider="local",
            source_mode=source_mode,
            profile_id=profile_id,
            android_profile=android_profile,
            path=artifact_path,
            size_bytes=size_bytes,
            sha256=digest,
        )
