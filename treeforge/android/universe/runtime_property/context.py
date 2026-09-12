from __future__ import annotations

from enum import StrEnum

from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextRequirement,
)


class AndroidUniversePropertyContextMatchKind(
    StrEnum
):
    """
    Match mode of one concrete property key against SELinux property_contexts.
    """

    EXACT = "exact"
    PREFIX = "prefix"


def android_property_context_mode(
    requirement: AndroidUniverseSelinuxContextRequirement,
) -> AndroidUniversePropertyContextMatchKind:
    """
    Return the normalized property_contexts selector mode.

    Android property_contexts uses prefix matching for legacy declarations
    without an explicit match operation. Modern declarations may explicitly
    select ``prefix`` or ``exact``. Unknown explicit operations are rejected
    rather than guessed.
    """

    fields = (
        requirement.declaration.trailing_fields
    )

    if not fields:
        # Android's legacy property_contexts grammar treats an entry
        # without an explicit match operation as a prefix match.
        return (
            AndroidUniversePropertyContextMatchKind
            .PREFIX
        )

    mode = fields[0].lower()

    if mode == "exact":
        return (
            AndroidUniversePropertyContextMatchKind
            .EXACT
        )

    if mode == "prefix":
        return (
            AndroidUniversePropertyContextMatchKind
            .PREFIX
        )

    raise ValueError(
        "unsupported property_contexts match operation: "
        f"{fields[0]!r}"
    )


def resolve_android_property_contexts(
    *,
    property_key: str,
    requirements: tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ],
) -> tuple[
    tuple[
        AndroidUniverseSelinuxContextRequirement,
        ...,
    ],
    AndroidUniversePropertyContextMatchKind | None,
]:
    """
    Resolve one concrete property key against canonical property_contexts.

    Exact matches outrank prefix matches. When multiple prefixes match, only
    the longest-prefix requirements remain effective. Duplicate effective
    requirements are preserved as independent provenance.
    """

    if not isinstance(
        property_key,
        str,
    ) or not property_key:
        raise ValueError(
            "property_key must be a non-empty string"
        )

    if not isinstance(
        requirements,
        tuple,
    ):
        raise TypeError(
            "requirements must be a tuple"
        )

    exact_matches = []
    prefix_matches = []

    for requirement in requirements:
        mode = android_property_context_mode(
            requirement
        )

        if (
            mode
            is AndroidUniversePropertyContextMatchKind
            .EXACT
        ):
            if property_key == requirement.selector:
                exact_matches.append(
                    requirement
                )
            continue

        if property_key.startswith(
            requirement.selector
        ):
            prefix_matches.append(
                requirement
            )

    if exact_matches:
        return (
            tuple(
                sorted(
                    exact_matches,
                    key=lambda item: (
                        item.selector,
                        item.context,
                    ),
                )
            ),
            AndroidUniversePropertyContextMatchKind.EXACT,
        )

    if not prefix_matches:
        return (), None

    longest = max(
        len(requirement.selector)
        for requirement in prefix_matches
    )

    effective = tuple(
        sorted(
            (
                requirement
                for requirement in prefix_matches
                if len(requirement.selector) == longest
            ),
            key=lambda item: (
                item.selector,
                item.context,
            ),
        )
    )

    return (
        effective,
        AndroidUniversePropertyContextMatchKind.PREFIX,
    )
