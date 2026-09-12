from __future__ import annotations

from treeforge.android.version.android15.device_tree.selinux_file_context_providers import (
    ANDROID_15_R36_SELINUX_FILE_CONTEXT_PROVIDERS,
)

from dataclasses import dataclass

from treeforge.android.version.android15.device_tree import (
    ANDROID_15_R36_APEX_PROVIDERS,
    ANDROID_15_R36_DEVICE_TREE_PROVIDER_ANDROID_VERSION,
    ANDROID_15_R36_DEVICE_TREE_PROVIDER_PROFILE_ID,
    ANDROID_15_R36_DEVICE_TREE_PROVIDER_REFERENCE_TAG,
    ANDROID_15_R36_DEVICE_TREE_PROVIDER_RUNTIME_CHECKOUT_DEPENDENCY,
    ANDROID_15_R36_ELF_PROVIDERS,
    ANDROID_15_R36_FRAMEWORK_RES_PROVIDERS,
    ANDROID_15_R36_PLATFORM_COPY_PROVIDERS,
    ANDROID_15_R36_SELINUX_STATEMENT_PROVIDERS,
    ANDROID_15_R36_SELINUX_TYPE_PROVIDERS,
    ANDROID_15_R36_UNRESOLVED_PROVIDER_OVERLAPS,
    ANDROID_15_R36_VINTF_PROVIDERS,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePlatformProviderProfile:
    """
    TreeForge-owned target-platform build-provider semantics.

    This is release/build-baseline data distilled during TreeForge
    development. It is not factory/device Knowledge and never interrogates
    an Android source checkout at runtime.

    Canonical factory ownership remains authoritative. Provider entries only
    prevent a second TreeForge build realization from participating when the
    selected TreeForge platform baseline already supplies the same target
    identity.
    """

    profile_id: str
    android_version: str
    reference_tag: str

    apex_providers: tuple[
        tuple[str, str, str],
        ...,
    ]

    elf_providers: tuple[
        tuple[str, str, str],
        ...,
    ]

    vintf_providers: tuple[
        tuple[str, str, str],
        ...,
    ]

    platform_copy_providers: tuple[
        str,
        ...,
    ]

    framework_res_providers: tuple[
        str,
        ...,
    ]

    selinux_type_providers: tuple[
        tuple[str, str, str],
        ...,
    ]

    selinux_statement_providers: tuple[
        tuple[
            str,
            str,
            str,
            str,
            str,
            str,
            str,
        ],
        ...,
    ]

    selinux_file_context_providers: tuple[
        tuple[str, str],
        ...,
    ]

    unresolved_provider_overlaps: tuple[
        tuple[str, str, str, str],
        ...,
    ]

    runtime_checkout_dependency: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("profile_id", self.profile_id),
            ("android_version", self.android_version),
            ("reference_tag", self.reference_tag),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        if self.runtime_checkout_dependency:
            raise ValueError(
                "Device Tree platform-provider profiles must be "
                "runtime-checkout-independent"
            )

        for name, values in (
            ("apex_providers", self.apex_providers),
            ("elf_providers", self.elf_providers),
            ("vintf_providers", self.vintf_providers),
            (
                "platform_copy_providers",
                self.platform_copy_providers,
            ),
            (
                "framework_res_providers",
                self.framework_res_providers,
            ),
            (
                "selinux_type_providers",
                self.selinux_type_providers,
            ),
            (
                "selinux_statement_providers",
                self.selinux_statement_providers,
            ),
            (
                "unresolved_provider_overlaps",
                self.unresolved_provider_overlaps,
            ),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if values != tuple(sorted(values)):
                raise ValueError(
                    f"{name} must be deterministically sorted"
                )

            if len(values) != len(set(values)):
                raise ValueError(
                    f"{name} must contain unique entries"
                )

        if (
            not isinstance(self.selinux_file_context_providers, tuple)
            or not all(
                isinstance(item, tuple)
                and len(item) == 2
                and all(isinstance(value, str) and value for value in item)
                for item in self.selinux_file_context_providers
            )
        ):
            raise TypeError(
                "selinux_file_context_providers must contain "
                "non-empty (relative_path, exact_line) tuples"
            )

        if self.selinux_file_context_providers != tuple(
            sorted(self.selinux_file_context_providers)
        ):
            raise ValueError(
                "selinux_file_context_providers must be deterministically sorted"
            )

        if len(self.selinux_file_context_providers) != len(
            set(self.selinux_file_context_providers)
        ):
            raise ValueError(
                "selinux_file_context_providers must be unique"
            )


ANDROID_15_R36_DEVICE_TREE_PLATFORM_PROVIDER_PROFILE = (
    AndroidDeviceTreePlatformProviderProfile(
        profile_id=(
            ANDROID_15_R36_DEVICE_TREE_PROVIDER_PROFILE_ID
        ),
        android_version=(
            ANDROID_15_R36_DEVICE_TREE_PROVIDER_ANDROID_VERSION
        ),
        reference_tag=(
            ANDROID_15_R36_DEVICE_TREE_PROVIDER_REFERENCE_TAG
        ),
        apex_providers=(
            ANDROID_15_R36_APEX_PROVIDERS
        ),
        elf_providers=(
            ANDROID_15_R36_ELF_PROVIDERS
        ),
        vintf_providers=(
            ANDROID_15_R36_VINTF_PROVIDERS
        ),
        platform_copy_providers=(
            ANDROID_15_R36_PLATFORM_COPY_PROVIDERS
        ),
        framework_res_providers=(
            ANDROID_15_R36_FRAMEWORK_RES_PROVIDERS
        ),
        selinux_type_providers=(
            ANDROID_15_R36_SELINUX_TYPE_PROVIDERS
        ),
        selinux_statement_providers=(
            ANDROID_15_R36_SELINUX_STATEMENT_PROVIDERS
        ),
        unresolved_provider_overlaps=(
            ANDROID_15_R36_UNRESOLVED_PROVIDER_OVERLAPS
        ),
        runtime_checkout_dependency=(
            ANDROID_15_R36_DEVICE_TREE_PROVIDER_RUNTIME_CHECKOUT_DEPENDENCY
        ),
        selinux_file_context_providers=(
            ANDROID_15_R36_SELINUX_FILE_CONTEXT_PROVIDERS
        ),
    )
)


def select_android_device_tree_provider_profile(
    android_version: str,
) -> AndroidDeviceTreePlatformProviderProfile:
    """
    Select target-build provider semantics from canonical Android version.

    Android 15 currently targets TreeForge's validated r36 platform-manifest
    baseline. Unsupported releases fail explicitly rather than silently using
    another Android release's provider population.
    """

    if (
        not isinstance(android_version, str)
        or not android_version.strip()
    ):
        raise ValueError(
            "android_version must be a non-empty string"
        )

    normalized = android_version.strip()

    if (
        normalized == "15"
        or normalized.startswith("15.")
    ):
        return (
            ANDROID_15_R36_DEVICE_TREE_PLATFORM_PROVIDER_PROFILE
        )

    raise ValueError(
        "TreeForge has no Device Tree platform-provider profile "
        f"for Android {normalized!r}"
    )
