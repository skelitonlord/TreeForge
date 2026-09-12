from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from treeforge.android.universe.runtime_property.model import (
    AndroidUniverseRuntimePropertyRequirement,
)


_ANDROID_INIT_PROPERTY_EXPRESSION = re.compile(
    r"\$\{"
    r"(?P<name>[A-Za-z0-9_.-]+)"
    r"(?::-"
    r"(?P<default>[^}]*)"
    r")?"
    r"\}"
)


class AndroidUniverseInitPropertyExpansionStatus(
    StrEnum
):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitPropertyExpansion:
    """
    Canonical result of expanding one Android INIT property expression.

    The literal expression remains first-class. Static declaration evidence is
    retained through the exact runtime-property requirements used to resolve
    referenced keys.
    """

    expression: str

    status: AndroidUniverseInitPropertyExpansionStatus

    expanded_value: str | None

    referenced_properties: tuple[
        str,
        ...,
    ]

    resolved_properties: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]

    property_requirements: tuple[
        AndroidUniverseRuntimePropertyRequirement,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.expression,
                str,
            )
            or not self.expression
        ):
            raise ValueError(
                "expression must be a non-empty string"
            )

        if not isinstance(
            self.status,
            AndroidUniverseInitPropertyExpansionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseInitPropertyExpansionStatus"
            )

        if (
            self.expanded_value is not None
            and not isinstance(
                self.expanded_value,
                str,
            )
        ):
            raise TypeError(
                "expanded_value must be a string or None"
            )

        if not isinstance(
            self.referenced_properties,
            tuple,
        ):
            raise TypeError(
                "referenced_properties must be a tuple"
            )

        if not isinstance(
            self.resolved_properties,
            tuple,
        ):
            raise TypeError(
                "resolved_properties must be a tuple"
            )

        if not isinstance(
            self.property_requirements,
            tuple,
        ):
            raise TypeError(
                "property_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseRuntimePropertyRequirement,
            )
            for item
            in self.property_requirements
        ):
            raise TypeError(
                "property_requirements must contain only "
                "AndroidUniverseRuntimePropertyRequirement "
                "instances"
            )

        if (
            self.status
            is AndroidUniverseInitPropertyExpansionStatus.RESOLVED
        ):
            if self.expanded_value is None:
                raise ValueError(
                    "resolved expansion requires expanded_value"
                )

        elif self.expanded_value is not None:
            raise ValueError(
                "only resolved expansion may have expanded_value"
            )

    @property
    def is_property_expression(
        self,
    ) -> bool:
        return bool(
            self.referenced_properties
        )


class AndroidUniverseInitPropertyExpressionResolver:
    """
    Expand Android INIT ``${property}`` and ``${property:-default}``.

    Only static property declarations are eligible to establish a boot-time
    substitution value. A concrete property is accepted when all non-empty
    declarations agree on one value.

    INIT runtime producers are deliberately not collapsed into one global
    value because runtime state is dynamic.
    """

    def __init__(
        self,
        requirements: tuple[
            AndroidUniverseRuntimePropertyRequirement,
            ...,
        ],
    ) -> None:
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
                AndroidUniverseRuntimePropertyRequirement,
            )
            for requirement
            in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseRuntimePropertyRequirement instances"
            )

        self._requirements = {
            requirement.property_key: requirement
            for requirement
            in requirements
        }

    def expand(
        self,
        expression: str,
    ) -> AndroidUniverseInitPropertyExpansion:
        if (
            not isinstance(
                expression,
                str,
            )
            or not expression
        ):
            raise ValueError(
                "expression must be a non-empty string"
            )

        matches = tuple(
            _ANDROID_INIT_PROPERTY_EXPRESSION.finditer(
                expression
            )
        )

        if not matches:
            return AndroidUniverseInitPropertyExpansion(
                expression=expression,
                status=(
                    AndroidUniverseInitPropertyExpansionStatus
                    .RESOLVED
                ),
                expanded_value=expression,
                referenced_properties=(),
                resolved_properties=(),
                property_requirements=(),
            )

        referenced = []
        resolved = []
        evidence = []

        result = expression
        offset = 0

        output = []

        saw_unresolved = False
        saw_conflict = False

        for match in matches:
            output.append(
                expression[
                    offset:
                    match.start()
                ]
            )

            property_key = (
                match.group(
                    "name"
                )
            )

            default_value = (
                match.group(
                    "default"
                )
            )

            referenced.append(
                property_key
            )

            requirement = (
                self._requirements.get(
                    property_key
                )
            )

            if requirement is not None:
                evidence.append(
                    requirement
                )

                values = tuple(
                    sorted(
                        {
                            observation.declaration.value
                            for observation
                            in requirement.declaration_observations
                            if observation.declaration.value
                        }
                    )
                )

            else:
                values = ()

            if len(values) == 1:
                value = values[0]

            elif len(values) > 1:
                saw_conflict = True
                offset = match.end()
                continue

            elif default_value is not None:
                value = default_value

            else:
                saw_unresolved = True
                offset = match.end()
                continue

            resolved.append(
                (
                    property_key,
                    value,
                )
            )

            output.append(
                value
            )

            offset = match.end()

        if saw_conflict:
            status = (
                AndroidUniverseInitPropertyExpansionStatus
                .CONFLICTING
            )
            expanded_value = None

        elif saw_unresolved:
            status = (
                AndroidUniverseInitPropertyExpansionStatus
                .UNRESOLVED
            )
            expanded_value = None

        else:
            output.append(
                expression[offset:]
            )

            status = (
                AndroidUniverseInitPropertyExpansionStatus
                .RESOLVED
            )

            expanded_value = "".join(
                output
            )

        return AndroidUniverseInitPropertyExpansion(
            expression=expression,
            status=status,
            expanded_value=expanded_value,
            referenced_properties=tuple(
                referenced
            ),
            resolved_properties=tuple(
                resolved
            ),
            property_requirements=tuple(
                sorted(
                    {
                        requirement.property_key: requirement
                        for requirement
                        in evidence
                    }.values(),
                    key=lambda requirement: (
                        requirement.property_key
                    ),
                )
            ),
        )


def android_init_expression_path_pattern(
    expression: str,
) -> re.Pattern[str]:
    """
    Compile one literal INIT import expression into an Android-path matcher.

    Property expressions match exactly one path component fragment and never
    cross ``/`` boundaries.

    Literal text surrounding an expression establishes any finer filename
    boundary. Property values themselves are not restricted by punctuation;
    for example ``${ro.zygote}`` may match both ``zygote64`` and
    ``zygote64_32`` before canonical property expansion selects the active
    source.
    """

    if (
        not isinstance(
            expression,
            str,
        )
        or not expression
    ):
        raise ValueError(
            "expression must be a non-empty string"
        )

    cursor = 0
    pieces = []

    for match in (
        _ANDROID_INIT_PROPERTY_EXPRESSION.finditer(
            expression
        )
    ):
        pieces.append(
            re.escape(
                expression[
                    cursor:
                    match.start()
                ]
            )
        )

        pieces.append(
            r"[^/]+"
        )

        cursor = match.end()

    pieces.append(
        re.escape(
            expression[cursor:]
        )
    )

    return re.compile(
        "^"
        + "".join(
            pieces
        )
        + "$"
    )
