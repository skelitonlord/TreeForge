from __future__ import annotations

from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathJarApplicability,
    AndroidUniverseClasspathJarApplicabilityStatus,
    AndroidUniverseClasspathJarRequirement,
)
from treeforge.android.universe.properties import (
    AndroidUniverseConclusionStatus,
    AndroidUniverseFactConclusion,
)


def _parse_sdk_value(
    value: str,
) -> int | None:
    """
    Conservatively interpret one SDK bound.

    Only canonical ASCII decimal API-level strings are currently interpreted.
    Any future symbolic or otherwise unfamiliar representation remains
    unresolved rather than being guessed.
    """

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "SDK value must be a string"
        )

    if (
        not value
        or not value.isascii()
        or not value.isdecimal()
    ):
        return None

    parsed = int(
        value,
        10,
    )

    if parsed < 1:
        return None

    return parsed


class AndroidUniverseClasspathSdkApplicabilityReconciler:
    """
    Reconcile Classpath Jar SDK bounds against the exact canonical device
    ``sdk_level`` property conclusion.

    This does not merge classpath fragments, resolve installed artifacts,
    or infer any SDK value from Knowledge or filesystem state.
    """

    def reconcile(
        self,
        *,
        requirements: tuple[
            AndroidUniverseClasspathJarRequirement,
            ...,
        ],
        property_conclusions: tuple[
            AndroidUniverseFactConclusion,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseClasspathJarApplicability,
        ...,
    ]:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseClasspathJarRequirement,
            )
            for requirement in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseClasspathJarRequirement instances"
            )

        if not isinstance(
            property_conclusions,
            tuple,
        ):
            raise TypeError(
                "property_conclusions must be a tuple"
            )

        if not all(
            isinstance(
                conclusion,
                AndroidUniverseFactConclusion,
            )
            for conclusion in property_conclusions
        ):
            raise TypeError(
                "property_conclusions must contain only "
                "AndroidUniverseFactConclusion instances"
            )

        sdk_conclusions = tuple(
            conclusion
            for conclusion
            in property_conclusions
            if conclusion.fact == "sdk_level"
        )

        if len(
            sdk_conclusions
        ) > 1:
            raise ValueError(
                "canonical property conclusions contain duplicate "
                "sdk_level conclusions"
            )

        sdk_conclusion = (
            sdk_conclusions[0]
            if sdk_conclusions
            else None
        )

        device_sdk = self._device_sdk(
            sdk_conclusion
        )

        return tuple(
            self._reconcile_requirement(
                requirement=requirement,
                sdk_conclusion=sdk_conclusion,
                device_sdk=device_sdk,
            )
            for requirement
            in requirements
        )

    @staticmethod
    def _device_sdk(
        conclusion: AndroidUniverseFactConclusion | None,
    ) -> int | None:
        if conclusion is None:
            return None

        if (
            conclusion.status
            is not AndroidUniverseConclusionStatus.AGREED
        ):
            return None

        if conclusion.value is None:
            return None

        return _parse_sdk_value(
            conclusion.value
        )

    def _reconcile_requirement(
        self,
        *,
        requirement: AndroidUniverseClasspathJarRequirement,
        sdk_conclusion: AndroidUniverseFactConclusion | None,
        device_sdk: int | None,
    ) -> AndroidUniverseClasspathJarApplicability:
        minimum_sdk = (
            _parse_sdk_value(
                requirement.min_sdk_version
            )
            if requirement.min_sdk_version_present
            else None
        )

        maximum_sdk = (
            _parse_sdk_value(
                requirement.max_sdk_version
            )
            if requirement.max_sdk_version_present
            else None
        )

        malformed_minimum = (
            requirement.min_sdk_version_present
            and minimum_sdk is None
        )

        malformed_maximum = (
            requirement.max_sdk_version_present
            and maximum_sdk is None
        )

        invalid_interval = (
            minimum_sdk is not None
            and maximum_sdk is not None
            and minimum_sdk > maximum_sdk
        )

        if (
            device_sdk is None
            or malformed_minimum
            or malformed_maximum
            or invalid_interval
        ):
            status = (
                AndroidUniverseClasspathJarApplicabilityStatus
                .UNRESOLVED
            )

        elif (
            minimum_sdk is not None
            and device_sdk < minimum_sdk
        ):
            status = (
                AndroidUniverseClasspathJarApplicabilityStatus
                .INAPPLICABLE
            )

        elif (
            maximum_sdk is not None
            and device_sdk > maximum_sdk
        ):
            status = (
                AndroidUniverseClasspathJarApplicabilityStatus
                .INAPPLICABLE
            )

        else:
            status = (
                AndroidUniverseClasspathJarApplicabilityStatus
                .ACTIVE
            )

        return AndroidUniverseClasspathJarApplicability(
            requirement=requirement,
            status=status,
            sdk_conclusion=sdk_conclusion,
            device_sdk=device_sdk,
            minimum_sdk=minimum_sdk,
            maximum_sdk=maximum_sdk,
        )
