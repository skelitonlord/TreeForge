from __future__ import annotations

from treeforge.android.version.model import (
    AndroidSemanticVersionSelection,
    AndroidSemanticVersionSelectionSource,
)
from treeforge.android.version.registry import (
    AndroidSemanticVersionRegistry,
    DEFAULT_ANDROID_SEMANTIC_VERSION_REGISTRY,
)


class AndroidSemanticVersionSelector:
    """
    Select the Android platform semantics used by one Universe run.

    Canonical Android version comes only from reconciled factory-image
    evidence.

    An explicit caller override changes only the selected semantic profile;
    it never rewrites the canonical factory-image conclusion.
    """

    def __init__(
        self,
        *,
        registry: AndroidSemanticVersionRegistry | None = None,
    ) -> None:
        self.registry = (
            registry
            if registry is not None
            else DEFAULT_ANDROID_SEMANTIC_VERSION_REGISTRY
        )

    def select(
        self,
        *,
        conclusions: tuple,
        requested_override: str | None = None,
    ) -> AndroidSemanticVersionSelection:
        candidates = tuple(
            conclusion
            for conclusion
            in conclusions
            if conclusion.fact == "android_version"
        )

        if len(candidates) > 1:
            raise ValueError(
                "canonical property reconciliation produced multiple "
                "android_version conclusions"
            )

        canonical_version = None

        if candidates:
            value = candidates[0].value

            if value is not None:
                if not isinstance(
                    value,
                    str,
                ):
                    raise TypeError(
                        "canonical android_version value must be a string"
                    )

                if not value.strip():
                    raise ValueError(
                        "canonical android_version value must not be empty"
                    )

                canonical_version = value

        if requested_override is not None:
            if (
                not isinstance(
                    requested_override,
                    str,
                )
                or not requested_override.strip()
            ):
                raise ValueError(
                    "requested Android semantic-version override must "
                    "be a non-empty string"
                )

            effective_version = requested_override
            source = (
                AndroidSemanticVersionSelectionSource.OVERRIDE
            )

        else:
            if canonical_version is None:
                raise ValueError(
                    "Android semantic version cannot be selected: "
                    "canonical android_version is unresolved and no "
                    "override was supplied"
                )

            effective_version = canonical_version
            source = (
                AndroidSemanticVersionSelectionSource.CANONICAL
            )

        profile = self.registry.require(
            effective_version
        )

        return AndroidSemanticVersionSelection(
            canonical_version=canonical_version,
            requested_override=requested_override,
            effective_version=effective_version,
            source=source,
            profile=profile,
        )
