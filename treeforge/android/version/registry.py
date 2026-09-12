from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.version.android14 import (
    ANDROID_14_SEMANTIC_VERSION_PROFILE,
)
from treeforge.android.version.android15 import (
    ANDROID_15_SEMANTIC_VERSION_PROFILE,
)
from treeforge.android.version.model import (
    AndroidSemanticVersionProfile,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidSemanticVersionRegistry:
    """
    Exact registry of Android platform-semantic profiles supported by
    TreeForge.

    Unsupported releases never silently fall back to another Android version.
    """

    profiles: tuple[
        AndroidSemanticVersionProfile,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.profiles,
            tuple,
        ):
            raise TypeError(
                "profiles must be a tuple"
            )

        if not all(
            isinstance(
                profile,
                AndroidSemanticVersionProfile,
            )
            for profile
            in self.profiles
        ):
            raise TypeError(
                "profiles must contain only "
                "AndroidSemanticVersionProfile instances"
            )

        versions = tuple(
            profile.android_version
            for profile
            in self.profiles
        )

        if len(versions) != len(set(versions)):
            raise ValueError(
                "semantic-version profiles must have "
                "unique Android versions"
            )

    def get(
        self,
        android_version: str,
    ) -> AndroidSemanticVersionProfile | None:
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

        return next(
            (
                profile
                for profile
                in self.profiles
                if (
                    profile.android_version
                    == android_version
                )
            ),
            None,
        )

    def require(
        self,
        android_version: str,
    ) -> AndroidSemanticVersionProfile:
        profile = self.get(
            android_version
        )

        if profile is None:
            raise ValueError(
                "unsupported Android semantic version: "
                f"{android_version}"
            )

        return profile


DEFAULT_ANDROID_SEMANTIC_VERSION_REGISTRY = (
    AndroidSemanticVersionRegistry(
        profiles=(
            ANDROID_14_SEMANTIC_VERSION_PROFILE,
            ANDROID_15_SEMANTIC_VERSION_PROFILE,
        )
    )
)
