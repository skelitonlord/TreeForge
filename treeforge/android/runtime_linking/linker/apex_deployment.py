from __future__ import annotations

from treeforge.android.universe.apex.deployment_context import (
    AndroidUniverseApexDeploymentPartition,
)
from treeforge.android.universe.apex.requirement import (
    AndroidUniverseApexRequirement,
)


class AndroidRuntimeLinkerApexDeploymentSemantics:
    """
    Linkerconfig interpretation of canonical Universe APEX placement.

    Universe supplies literal deployment partition identity. This layer owns
    only the AOSP linkerconfig grouping that depends on runtime policy such as
    Treble state.
    """

    @staticmethod
    def _validate_requirement(
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
    def is_vendor_partition(
        cls,
        requirement: AndroidUniverseApexRequirement,
    ) -> bool:
        cls._validate_requirement(
            requirement
        )

        return (
            requirement.deployment_partition
            in {
                AndroidUniverseApexDeploymentPartition.VENDOR,
                AndroidUniverseApexDeploymentPartition.ODM,
            }
        )

    @classmethod
    def is_product_partition(
        cls,
        requirement: AndroidUniverseApexRequirement,
    ) -> bool:
        cls._validate_requirement(
            requirement
        )

        return (
            requirement.deployment_partition
            is AndroidUniverseApexDeploymentPartition.PRODUCT
        )

    @classmethod
    def is_system_partition(
        cls,
        requirement: AndroidUniverseApexRequirement,
    ) -> bool:
        cls._validate_requirement(
            requirement
        )

        return (
            requirement.deployment_partition
            in {
                AndroidUniverseApexDeploymentPartition.SYSTEM,
                AndroidUniverseApexDeploymentPartition.SYSTEM_EXT,
            }
        )

    @classmethod
    def is_product_linker_domain(
        cls,
        requirement: AndroidUniverseApexRequirement,
        *,
        treble: bool,
    ) -> bool:
        if not isinstance(
            treble,
            bool,
        ):
            raise TypeError(
                "treble must be a bool"
            )

        return (
            treble
            and cls.is_product_partition(
                requirement
            )
        )

    @classmethod
    def is_system_linker_domain(
        cls,
        requirement: AndroidUniverseApexRequirement,
        *,
        treble: bool,
    ) -> bool:
        if not isinstance(
            treble,
            bool,
        ):
            raise TypeError(
                "treble must be a bool"
            )

        if cls.is_system_partition(
            requirement
        ):
            return True

        return (
            not treble
            and cls.is_product_partition(
                requirement
            )
        )
