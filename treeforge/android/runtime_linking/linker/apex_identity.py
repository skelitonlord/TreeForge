from __future__ import annotations

from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)


class AndroidRuntimeLinkerApexIdentity:
    """
    Linkerconfig-facing identities derived from canonical APEX identity.

    Universe owns the APEX manifest identity itself. Runtime Linking owns
    names constructed from that identity for linkerconfig.
    """

    @staticmethod
    def _validate(
        requirement: AndroidUniverseApexRequirement,
    ) -> None:
        if not isinstance(
            requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseApexRequirement"
            )

    @classmethod
    def section_name(
        cls,
        requirement: AndroidUniverseApexRequirement,
    ) -> str:
        cls._validate(
            requirement
        )

        return requirement.apex_name

    @classmethod
    def namespace_name(
        cls,
        requirement: AndroidUniverseApexRequirement,
    ) -> str:
        cls._validate(
            requirement
        )

        return requirement.apex_name.replace(
            ".",
            "_",
        )
