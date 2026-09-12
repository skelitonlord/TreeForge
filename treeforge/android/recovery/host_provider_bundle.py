from __future__ import annotations

from pathlib import Path

from treeforge.android.host_provider_bundle import (
    AndroidHostProviderBundleError,
    AndroidHostProviderBundleLoader,
    TREEFORGE_ANDROID_HOST_PROVIDER_BUNDLE_SCHEMA,
    android_host_provider_bundle_root,
)


# Recovery compatibility names.
AndroidRecoveryHostProviderBundleError = (
    AndroidHostProviderBundleError
)

AndroidRecoveryHostProviderBundleLoader = (
    AndroidHostProviderBundleLoader
)

TREEFORGE_RECOVERY_HOST_PROVIDER_BUNDLE_SCHEMA = (
    TREEFORGE_ANDROID_HOST_PROVIDER_BUNDLE_SCHEMA
)


def recovery_host_provider_bundle_root(
    *,
    name: str,
    release: str,
) -> Path:
    return android_host_provider_bundle_root(
        name=name,
        release=release,
    )


__all__ = (
    "AndroidRecoveryHostProviderBundleError",
    "AndroidRecoveryHostProviderBundleLoader",
    "TREEFORGE_RECOVERY_HOST_PROVIDER_BUNDLE_SCHEMA",
    "recovery_host_provider_bundle_root",
)
