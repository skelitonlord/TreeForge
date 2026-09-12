from __future__ import annotations

from treeforge.android.host_provider import (
    AndroidHostProvider,
)
from treeforge.android.host_provider_bundle import (
    ANDROID_15_HOST_PROVIDER_RELEASE,
    AndroidHostProviderBundleLoader,
    android_host_provider_bundle_root,
)
from treeforge.android.host_provider_sync import (
    provider_release_lock_metadata,
    provider_release_record,
)


ANDROID_HOST_PROVIDER_REQUIREMENTS: tuple[
    tuple[
        str,
        tuple[
            str,
            ...,
        ],
    ],
    ...,
] = (
    (
        "avbtool",
        (
            "android-avbtool",
        ),
    ),
    (
        "mkdtimg",
        (
            "android-mkdtimg",
        ),
    ),
    (
        "create_snapshot",
        (),
    ),
    (
        "inspect_cow",
        (),
    ),
    (
        "android-image-tools",
        (
            "android-lpdump",
            "android-lpunpack",
            "android-simg2img",
            "android-mkbootimg",
            "android-unpack-bootimg",
            "android-lpmake",
            "android-make-f2fs",
        ),
    ),
    (
        "aosp-adb",
        (
            "android-adb-host",
        ),
    ),
    (
        "aosp-fastboot",
        (
            "android-fastboot-host",
        ),
    ),
)


# Retained as a compatibility surface for existing setup callers.
BOOTSTRAP_BOOT_IMAGE_HOST_PROVIDERS: tuple[
    tuple[str, str],
    ...,
] = (
    (
        "avbtool",
        "android-avbtool",
    ),
    (
        "mkdtimg",
        "android-mkdtimg",
    ),
)


def _load_required_provider(
    name: str,
    capabilities: tuple[
        str,
        ...,
    ],
) -> AndroidHostProvider:
    provider = (
        AndroidHostProviderBundleLoader.load(
            android_host_provider_bundle_root(
                name=name,
                release=(
                    ANDROID_15_HOST_PROVIDER_RELEASE
                ),
            )
        )
    )

    for capability in capabilities:
        if not provider.supports(
            capability
        ):
            raise RuntimeError(
                f"TreeForge host provider {name!r} "
                "does not expose required capability "
                f"{capability!r}"
            )

        provider.executable_for(
            capability
        )

    return provider


def verify_android_host_providers() -> tuple[
    AndroidHostProvider,
    ...,
]:
    """
    Verify every TreeForge-owned Android host provider.

    Resolution uses the verified local provider cache first. On a cache
    miss, the exact pinned asset is obtained from TreeForge's public
    toolchain releases and verified before use. No AOSP checkout, PATH
    fallback, private source-repository access, or Android build operation
    is consulted.
    """

    return tuple(
        _load_required_provider(
            name,
            capabilities,
        )
        for (
            name,
            capabilities,
        )
        in ANDROID_HOST_PROVIDER_REQUIREMENTS
    )


def verify_bootstrap_boot_image_host_providers() -> tuple[
    AndroidHostProvider,
    ...,
]:
    """
    Compatibility helper for Bootstrap / Boot Image setup verification.
    """

    names = {
        "avbtool",
        "mkdtimg",
        "android-image-tools",
    }

    return tuple(
        provider
        for provider
        in verify_android_host_providers()
        if provider.name
        in names
    )


def main() -> None:
    providers = (
        verify_android_host_providers()
    )

    release_lock = (
        provider_release_lock_metadata()
    )

    print(
        "TreeForge-owned Android host providers:"
    )
    print(
        "  public release repository: "
        f"{release_lock['public_repository']}"
    )
    print(
        "  resolution: verified cache first; "
        "exact pinned public release on cache miss"
    )

    for provider in providers:
        record = provider_release_record(
            provider.name
        )

        print(
            f"  {provider.name}:"
        )
        print(
            f"    release: {provider.release}"
        )
        print(
            "    release tag: "
            f"{record['release_tag']}"
        )
        print(
            "    source commit: "
            f"{record['source_commit']}"
        )
        print(
            "    archive sha256: "
            f"{record['archive_sha256']}"
        )
        print(
            "    platform: "
            f"{provider.platform}/"
            f"{provider.architecture}"
        )
        print(
            f"    executables: {len(provider.executables)}"
        )

        for executable in provider.executables:
            print(
                f"      {executable.name}: "
                f"{executable.path}"
            )
            print(
                "        sha256: "
                f"{executable.content_sha256}"
            )
            print(
                "        capabilities: "
                + ", ".join(
                    executable.capabilities
                )
            )

        print(
            f"    runtime files: {len(provider.runtime_files)}"
        )
        print(
            f"    legal files: {len(provider.legal_files)}"
        )
        print(
            f"    provenance files: "
            f"{len(provider.provenance_files)}"
        )
        print(
            f"    source records: "
            f"{len(provider.provider_sources)}"
        )


if __name__ == "__main__":
    main()


__all__ = (
    "ANDROID_HOST_PROVIDER_REQUIREMENTS",
    "BOOTSTRAP_BOOT_IMAGE_HOST_PROVIDERS",
    "verify_android_host_providers",
    "verify_bootstrap_boot_image_host_providers",
)
