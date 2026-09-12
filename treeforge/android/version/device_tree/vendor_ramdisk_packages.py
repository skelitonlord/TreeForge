from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.version.android15.device_tree.vendor_ramdisk_packages import (
    ANDROID_15_R36_VENDOR_RAMDISK_PACKAGE_PROVIDERS,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeVendorRamdiskPackageProvider:
    """
    Versioned mapping from one canonical vendor_boot runtime payload to the
    Android module that reconstructs it in the primary vendor ramdisk.

    The observed path remains factory evidence. The module name is
    Android-version build-provider semantics.
    """

    observed_android_path: PurePosixPath
    module_name: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.observed_android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "observed_android_path must be a PurePosixPath"
            )

        if not self.observed_android_path.is_absolute():
            raise ValueError(
                "observed_android_path must be absolute"
            )

        if (
            not isinstance(
                self.module_name,
                str,
            )
            or not self.module_name
        ):
            raise ValueError(
                "module_name must be a non-empty string"
            )


def _build_providers(
    values: tuple[
        tuple[str, str],
        ...,
    ],
) -> tuple[
    AndroidDeviceTreeVendorRamdiskPackageProvider,
    ...,
]:
    providers = tuple(
        AndroidDeviceTreeVendorRamdiskPackageProvider(
            observed_android_path=(
                PurePosixPath(
                    observed_android_path
                )
            ),
            module_name=module_name,
        )
        for (
            observed_android_path,
            module_name,
        )
        in values
    )

    expected = tuple(
        sorted(
            providers,
            key=lambda item: (
                item.observed_android_path.as_posix(),
                item.module_name,
            ),
        )
    )

    if providers != expected:
        raise ValueError(
            "vendor-ramdisk package providers must be "
            "deterministically sorted"
        )

    paths = tuple(
        item.observed_android_path
        for item
        in providers
    )

    modules = tuple(
        item.module_name
        for item
        in providers
    )

    if len(paths) != len(set(paths)):
        raise ValueError(
            "vendor-ramdisk provider paths must be unique"
        )

    if len(modules) != len(set(modules)):
        raise ValueError(
            "vendor-ramdisk provider module names must be unique"
        )

    return providers


_ANDROID_15_R36_PROVIDERS = (
    _build_providers(
        ANDROID_15_R36_VENDOR_RAMDISK_PACKAGE_PROVIDERS
    )
)


def select_android_device_tree_vendor_ramdisk_package_providers(
    android_version: str,
) -> tuple[
    AndroidDeviceTreeVendorRamdiskPackageProvider,
    ...,
]:
    """
    Select versioned Android primary-vendor-ramdisk module semantics.

    Selection uses only the already-resolved Android version and TreeForge's
    retained versioned data. It never inspects an Android checkout.
    """

    if (
        not isinstance(
            android_version,
            str,
        )
        or not android_version.strip()
    ):
        raise ValueError(
            "android_version must be a non-empty string"
        )

    normalized = android_version.strip()

    if (
        normalized == "15"
        or normalized.startswith(
            "15."
        )
    ):
        return _ANDROID_15_R36_PROVIDERS

    raise ValueError(
        "TreeForge has no vendor-ramdisk package-provider "
        f"profile for Android {normalized!r}"
    )
