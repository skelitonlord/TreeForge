from __future__ import annotations

from pathlib import Path

from treeforge.android.host_provider import (
    AndroidHostProvider,
)
from treeforge.android.host_provider_bundle import (
    ANDROID_15_HOST_PROVIDER_RELEASE,
    AndroidHostProviderBundleLoader,
    android_host_provider_bundle_root,
)


ANDROID_ADB_HOST_CAPABILITY = (
    "android-adb-host"
)

ANDROID_FASTBOOT_HOST_CAPABILITY = (
    "android-fastboot-host"
)

AOSP_ADB_PROVIDER_NAME = "aosp-adb"
AOSP_FASTBOOT_PROVIDER_NAME = "aosp-fastboot"


ANDROID_HOST_TOOL_PROVIDER_REGISTRY: dict[
    str,
    dict[str, str],
] = {
    ANDROID_15_HOST_PROVIDER_RELEASE: {
        ANDROID_ADB_HOST_CAPABILITY: (
            AOSP_ADB_PROVIDER_NAME
        ),
        ANDROID_FASTBOOT_HOST_CAPABILITY: (
            AOSP_FASTBOOT_PROVIDER_NAME
        ),
    },
}


def _provider_for_capability(
    capability: str,
    *,
    release: str = (
        ANDROID_15_HOST_PROVIDER_RELEASE
    ),
) -> AndroidHostProvider:
    providers = (
        ANDROID_HOST_TOOL_PROVIDER_REGISTRY.get(
            release
        )
    )

    if providers is None:
        raise RuntimeError(
            "TreeForge has no Android host-tool provider "
            f"registry for release {release!r}"
        )

    provider_name = providers.get(capability)

    if provider_name is None:
        raise RuntimeError(
            "TreeForge has no Android host-tool provider "
            f"for capability {capability!r} in release "
            f"{release!r}"
        )

    provider = AndroidHostProviderBundleLoader.load(
        android_host_provider_bundle_root(
            name=provider_name,
            release=release,
        )
    )

    if not provider.supports(capability):
        raise RuntimeError(
            f"Android host provider {provider_name!r} "
            "does not expose expected capability "
            f"{capability!r}"
        )

    return provider


def treeforge_host_tool_executable(
    capability: str,
    *,
    release: str = (
        ANDROID_15_HOST_PROVIDER_RELEASE
    ),
) -> Path:
    return (
        _provider_for_capability(
            capability,
            release=release,
        )
        .executable_for(capability)
    )


def treeforge_adb_executable(
    *,
    release: str = (
        ANDROID_15_HOST_PROVIDER_RELEASE
    ),
) -> Path:
    return treeforge_host_tool_executable(
        ANDROID_ADB_HOST_CAPABILITY,
        release=release,
    )


def treeforge_fastboot_executable(
    *,
    release: str = (
        ANDROID_15_HOST_PROVIDER_RELEASE
    ),
) -> Path:
    return treeforge_host_tool_executable(
        ANDROID_FASTBOOT_HOST_CAPABILITY,
        release=release,
    )


__all__ = (
    "ANDROID_ADB_HOST_CAPABILITY",
    "ANDROID_FASTBOOT_HOST_CAPABILITY",
    "ANDROID_HOST_TOOL_PROVIDER_REGISTRY",
    "AOSP_ADB_PROVIDER_NAME",
    "AOSP_FASTBOOT_PROVIDER_NAME",
    "treeforge_adb_executable",
    "treeforge_fastboot_executable",
    "treeforge_host_tool_executable",
)
