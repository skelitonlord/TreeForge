from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.host_provider_bundle import (
    ANDROID_15_HOST_PROVIDER_RELEASE,
    AndroidHostProviderBundleLoader,
    android_host_provider_bundle_root,
)


_IMAGE_TOOLS_PROVIDER = (
    "android-image-tools"
)


def _load_image_tools_provider():
    return AndroidHostProviderBundleLoader.load(
        android_host_provider_bundle_root(
            name=(
                _IMAGE_TOOLS_PROVIDER
            ),
            release=(
                ANDROID_15_HOST_PROVIDER_RELEASE
            ),
        )
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidHostTools:
    """
    Resolve Android-derived host tools from TreeForge-owned providers.

    Explicit executable overrides remain available for controlled developer
    and test use. The normal pipeline never consults an AOSP checkout or PATH
    for lpdump, lpunpack, simg2img, lpmake, or make_f2fs.

    debugfs remains a normal operating-system tool.
    """

    lpdump: str | None = None
    lpunpack: str | None = None
    debugfs: str = "debugfs"
    simg2img: str | None = None
    lpmake: str | None = None
    make_f2fs: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.lpdump is None
            or self.lpunpack is None
            or self.simg2img is None
            or self.lpmake is None
            or self.make_f2fs is None
        ):
            provider = (
                _load_image_tools_provider()
            )

            defaults = {
                "lpdump": (
                    "android-lpdump"
                ),
                "lpunpack": (
                    "android-lpunpack"
                ),
                "simg2img": (
                    "android-simg2img"
                ),
                "lpmake": (
                    "android-lpmake"
                ),
                "make_f2fs": (
                    "android-make-f2fs"
                ),
            }

            for field_name, capability in defaults.items():
                if (
                    getattr(
                        self,
                        field_name,
                    )
                    is not None
                ):
                    continue

                object.__setattr__(
                    self,
                    field_name,
                    str(
                        provider.executable_for(
                            capability
                        )
                    ),
                )

        for name in (
            "lpdump",
            "lpunpack",
            "debugfs",
            "simg2img",
            "lpmake",
            "make_f2fs",
        ):
            executable = getattr(
                self,
                name,
            )

            self._validate_executable(
                name=name,
                executable=executable,
            )

    @staticmethod
    def _validate_executable(
        *,
        name: str,
        executable: str | None,
    ) -> None:
        if not isinstance(
            executable,
            str,
        ):
            raise TypeError(
                f"{name} executable must resolve to a string"
            )

        if not executable.strip():
            raise ValueError(
                f"{name} executable must not be empty"
            )

        if executable != executable.strip():
            raise ValueError(
                f"{name} executable must not contain "
                "leading or trailing whitespace"
            )

        if any(
            character
            in executable
            for character
            in (
                "\x00",
                "\n",
                "\r",
            )
        ):
            raise ValueError(
                f"{name} executable contains unsafe characters"
            )
