from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.recovery.runtime_provider_bundle import (
    RecoveryRuntimeProviderBundleLoader,
    recovery_runtime_provider_bundle_root,
)


TREEFORGE_RECOVERY_RUNTIME_STAGING_ROOT = PurePosixPath(
    "/treeforge-recovery-provider"
)

TREEFORGE_RECOVERY_RUNTIME_DESTINATION_ROOT = PurePosixPath(
    "/dev/treeforge-recovery-runtime"
)


_RUNTIME_RELEASE_BY_SDK = {
    "35": "android-15.0.0_r36-arm64",
}

_RUNTIME_PROVIDER_NAMES = (
    "aosp-adbd-recovery",
    "treeforge-vabc-coordinator",
    "aosp-fastbootd",
    "snapuserd_ramdisk",
)


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryRuntimeCompositionFile:
    android_path: PurePosixPath
    source_path: Path
    content_sha256: str
    mode: int
    provider_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.android_path.is_absolute()
            or ".." in self.android_path.parts
        ):
            raise ValueError(
                "Recovery runtime composition android_path must "
                "be absolute without traversal"
            )

        if not self.source_path.is_file():
            raise ValueError(
                "Recovery runtime composition source is unavailable: "
                f"{self.source_path}"
            )

        if (
            not isinstance(self.mode, int)
            or self.mode <= 0
            or self.mode > 0o777
        ):
            raise ValueError(
                "Recovery runtime composition mode is invalid: "
                f"{self.mode!r}"
            )

        if (
            not isinstance(self.provider_names, tuple)
            or not self.provider_names
        ):
            raise ValueError(
                "Recovery runtime composition file requires provider "
                "provenance"
            )

    @property
    def staging_path(self) -> PurePosixPath:
        return (
            TREEFORGE_RECOVERY_RUNTIME_STAGING_ROOT
            / self.android_path.relative_to("/")
        )

    @property
    def destination_path(self) -> PurePosixPath:
        return (
            TREEFORGE_RECOVERY_RUNTIME_DESTINATION_ROOT
            / self.android_path.relative_to("/")
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryRuntimeComposition:
    canonical_sdk_level: str
    architecture: str
    release: str

    providers: tuple[str, ...]

    files: tuple[
        RecoveryRuntimeCompositionFile,
        ...,
    ]

    snapuserd_link_path: PurePosixPath
    snapuserd_link_target: str

    def __post_init__(self) -> None:
        paths = tuple(
            value.android_path
            for value in self.files
        )

        if len(paths) != len(set(paths)):
            raise ValueError(
                "Recovery runtime composition contains duplicate "
                "Android paths"
            )

        required = {
            PurePosixPath("/system/bin/adbd"),
            PurePosixPath("/system/bin/linker64"),
            PurePosixPath("/system/bin/fastbootd"),
            PurePosixPath(
                "/system/bin/treeforge-vabc-coordinator"
            ),
            PurePosixPath(
                "/system/bin/snapuserd_ramdisk"
            ),
        }

        missing = required - set(paths)

        if missing:
            raise ValueError(
                "Recovery runtime composition is missing required "
                "runtime files: "
                + ", ".join(
                    str(value)
                    for value in sorted(
                        missing,
                        key=str,
                    )
                )
            )

        if (
            self.snapuserd_link_path
            in set(paths)
        ):
            raise ValueError(
                "snapuserd symlink path collides with a regular "
                "runtime provider file"
            )


def compose_recovery_runtime(
    *,
    canonical_sdk_level: str,
    architecture: str,
) -> RecoveryRuntimeComposition:
    release = _RUNTIME_RELEASE_BY_SDK.get(
        canonical_sdk_level
    )

    if release is None:
        raise RuntimeError(
            "TreeForge does not bundle a composed Recovery runtime "
            "for canonical Android SDK level "
            f"{canonical_sdk_level!r}"
        )

    providers = []

    for name in _RUNTIME_PROVIDER_NAMES:
        root = (
            recovery_runtime_provider_bundle_root(
                name,
                release,
            )
        )

        provider = (
            RecoveryRuntimeProviderBundleLoader
            .load(
                root
            )
        )

        if (
            provider.canonical_sdk_level
            != canonical_sdk_level
        ):
            raise RuntimeError(
                "Recovery runtime provider SDK mismatch: "
                f"{provider.name}: "
                f"provider={provider.canonical_sdk_level!r}, "
                f"canonical={canonical_sdk_level!r}"
            )

        if provider.architecture != architecture:
            raise RuntimeError(
                "Recovery runtime provider architecture mismatch: "
                f"{provider.name}: "
                f"provider={provider.architecture!r}, "
                f"required={architecture!r}"
            )

        if provider.release != release:
            raise RuntimeError(
                "Recovery runtime provider release mismatch: "
                f"{provider.name}: "
                f"provider={provider.release!r}, "
                f"required={release!r}"
            )

        providers.append(
            provider
        )

    merged = {}

    for provider in providers:
        for provider_file in provider.files:
            mode = (
                provider_file
                .source_path
                .stat()
                .st_mode
                & 0o777
            )

            if mode == 0:
                raise RuntimeError(
                    "Recovery runtime provider file has no usable "
                    "permission bits: "
                    f"{provider_file.source_path}"
                )

            existing = merged.get(
                provider_file.android_path
            )

            if existing is None:
                merged[
                    provider_file.android_path
                ] = {
                    "source_path": (
                        provider_file.source_path
                    ),
                    "content_sha256": (
                        provider_file.content_sha256
                    ),
                    "mode": mode,
                    "providers": [
                        provider.name
                    ],
                }

                continue

            if (
                existing["content_sha256"]
                != provider_file.content_sha256
                or existing["mode"] != mode
            ):
                raise RuntimeError(
                    "Recovery runtime providers disagree on "
                    f"{provider_file.android_path}: "
                    + ", ".join(
                        existing["providers"]
                        + [provider.name]
                    )
                )

            existing["providers"].append(
                provider.name
            )

    files = tuple(
        RecoveryRuntimeCompositionFile(
            android_path=android_path,
            source_path=value["source_path"],
            content_sha256=value["content_sha256"],
            mode=value["mode"],
            provider_names=tuple(
                value["providers"]
            ),
        )
        for android_path, value
        in sorted(
            merged.items(),
            key=lambda item: (
                item[0].as_posix()
            ),
        )
    )

    return RecoveryRuntimeComposition(
        canonical_sdk_level=canonical_sdk_level,
        architecture=architecture,
        release=release,
        providers=tuple(
            provider.name
            for provider in providers
        ),
        files=files,
        snapuserd_link_path=PurePosixPath(
            "/system/bin/snapuserd"
        ),
        snapuserd_link_target=(
            "snapuserd_ramdisk"
        ),
    )


__all__ = (
    "RecoveryRuntimeComposition",
    "RecoveryRuntimeCompositionFile",
    "TREEFORGE_RECOVERY_RUNTIME_DESTINATION_ROOT",
    "TREEFORGE_RECOVERY_RUNTIME_STAGING_ROOT",
    "compose_recovery_runtime",
)
