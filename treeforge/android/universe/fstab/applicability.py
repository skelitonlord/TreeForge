from __future__ import annotations

from dataclasses import dataclass
import re

from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
    ParsedAndroidPropertyFile,
)
from treeforge.android.universe.fstab.model import (
    AndroidUniverseFstabRequirement,
)
from treeforge.android.universe.avf.requirement import (
    AndroidUniverseAvfRequirement,
)
from treeforge.android.universe.init.action import (
    AndroidUniverseInitActionRequirement,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityEvidence,
    AndroidUniverseApplicabilityEvidenceKind,
    AndroidUniverseApplicabilityStatus,
    AndroidUniverseRequirementApplicability,
)


_PROPERTY_REFERENCE = re.compile(
    r"\$\{(?P<key>[^}]+)\}"
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFstabApplicabilityObservation:
    """
    Cross-artifact applicability evidence for one fstab requirement.

    This is intentionally an observation rather than a final applicability
    conclusion. Universe reconciliation owns deciding whether the requirement
    is active, conditional, alternative, or unresolved.
    """

    requirement_id: str

    referenced_path_expression: str | None = None
    resolved_path: str | None = None

    selector_key: str | None = None
    selector_value: str | None = None

    evidence: tuple[
        AndroidUniverseApplicabilityEvidence,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement_id,
            str,
        ):
            raise TypeError(
                "requirement_id must be a string"
            )

        if not self.requirement_id:
            raise ValueError(
                "requirement_id must not be empty"
            )

        for field_name, value in (
            (
                "referenced_path_expression",
                self.referenced_path_expression,
            ),
            (
                "resolved_path",
                self.resolved_path,
            ),
            (
                "selector_key",
                self.selector_key,
            ),
            (
                "selector_value",
                self.selector_value,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseApplicabilityEvidence,
            )
            for item in self.evidence
        ):
            raise TypeError(
                "evidence must contain only "
                "AndroidUniverseApplicabilityEvidence"
            )


class AndroidUniverseFstabApplicabilityReconciler:
    """
    Reconcile fstab applicability observations into the generic canonical
    Universe applicability contract.

    Positive runtime references establish ACTIVE requirements.

    Property-substituted fstab references also establish explicit
    alternative groups. Requirements whose canonical Android paths fit the
    same selector expression but are not selected by the observed property
    value are ALTERNATIVE rather than merely lacking evidence.

    Requirements for which Universe cannot establish active, conditional,
    or alternative applicability remain UNRESOLVED. Absence of positive
    evidence is never treated as proof of non-applicability.
    """

    def reconcile(
        self,
        *,
        requirements: tuple[
            AndroidUniverseFstabRequirement,
            ...,
        ],
        observations: tuple[
            AndroidUniverseFstabApplicabilityObservation,
            ...,
        ],
        avf_requirement: (
            AndroidUniverseAvfRequirement
            | None
        ) = None,
    ) -> tuple[
        AndroidUniverseRequirementApplicability,
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
                item,
                AndroidUniverseFstabRequirement,
            )
            for item in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseFstabRequirement instances"
            )

        if not isinstance(
            observations,
            tuple,
        ):
            raise TypeError(
                "observations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFstabApplicabilityObservation,
            )
            for item in observations
        ):
            raise TypeError(
                "observations must contain only "
                "AndroidUniverseFstabApplicabilityObservation "
                "instances"
            )

        if (
            avf_requirement is not None
            and not isinstance(
                avf_requirement,
                AndroidUniverseAvfRequirement,
            )
        ):
            raise TypeError(
                "avf_requirement must be an "
                "AndroidUniverseAvfRequirement or None"
            )

        requirements_by_id = {
            item.requirement_id: item
            for item in requirements
        }

        if len(
            requirements_by_id
        ) != len(
            requirements
        ):
            raise ValueError(
                "requirements must contain unique requirement IDs"
            )

        grouped: dict[
            str,
            list[
                AndroidUniverseFstabApplicabilityObservation
            ],
        ] = {
            requirement_id: []
            for requirement_id in requirements_by_id
        }

        for observation in observations:
            if (
                observation.requirement_id
                not in requirements_by_id
            ):
                raise ValueError(
                    "applicability observation references "
                    "an unknown requirement ID: "
                    f"{observation.requirement_id}"
                )

            grouped[
                observation.requirement_id
            ].append(
                observation
            )

        canonical_observations = {
            requirement_id: tuple(
                sorted(
                    values,
                    key=self._observation_sort_key,
                )
            )
            for requirement_id, values in grouped.items()
        }

        for requirement in requirements:
            if not canonical_observations[
                requirement.requirement_id
            ]:
                raise ValueError(
                    "every fstab requirement must have at least "
                    "one applicability observation: "
                    f"{requirement.requirement_id}"
                )

        selector_groups = (
            self._build_selector_groups(
                requirements=requirements,
                observations=observations,
            )
        )

        conclusions = []

        for requirement in requirements:
            requirement_observations = (
                canonical_observations[
                    requirement.requirement_id
                ]
            )

            positive_observations = tuple(
                observation
                for observation in requirement_observations
                if observation.evidence
            )

            if positive_observations:
                evidence = self._canonical_evidence(
                    evidence=tuple(
                        evidence_item
                        for observation in positive_observations
                        for evidence_item in observation.evidence
                    )
                )

                selector_observations = tuple(
                    observation
                    for observation in positive_observations
                    if (
                        observation.selector_key
                        is not None
                        and observation
                        .referenced_path_expression
                        is not None
                    )
                )

                selector_key = None
                selector_value = None
                alternative_group = None

                if selector_observations:
                    selector_keys = {
                        item.selector_key
                        for item in selector_observations
                    }

                    selector_values = {
                        item.selector_value
                        for item in selector_observations
                    }

                    expressions = {
                        item.referenced_path_expression
                        for item in selector_observations
                    }

                    if len(selector_keys) == 1:
                        selector_key = next(
                            iter(selector_keys)
                        )

                    if len(selector_values) == 1:
                        selector_value = next(
                            iter(selector_values)
                        )

                    if len(expressions) == 1:
                        alternative_group = next(
                            iter(expressions)
                        )

                conclusions.append(
                    AndroidUniverseRequirementApplicability(
                        requirement_id=(
                            requirement.requirement_id
                        ),
                        status=(
                            AndroidUniverseApplicabilityStatus
                            .ACTIVE
                        ),
                        evidence=evidence,
                        alternative_group=(
                            alternative_group
                        ),
                        selector_key=selector_key,
                        selector_value=selector_value,
                    )
                )

                continue

            alternative = (
                self._alternative_for_requirement(
                    requirement=requirement,
                    selector_groups=selector_groups,
                )
            )

            if alternative is not None:
                (
                    alternative_group,
                    selector_key,
                    selector_value,
                    evidence,
                ) = alternative

                conclusions.append(
                    AndroidUniverseRequirementApplicability(
                        requirement_id=(
                            requirement.requirement_id
                        ),
                        status=(
                            AndroidUniverseApplicabilityStatus
                            .ALTERNATIVE
                        ),
                        evidence=evidence,
                        alternative_group=(
                            alternative_group
                        ),
                        selector_key=selector_key,
                        selector_value=selector_value,
                    )
                )

                continue

            conclusions.append(
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        requirement.requirement_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .UNRESOLVED
                    ),
                    evidence=(),
                )
            )

        conclusions = list(
            self._propagate_equivalent_source_applicability(
                requirements=requirements,
                conclusions=tuple(
                    conclusions
                ),
            )
        )

        conclusions = list(
            self._apply_avf_guest_runtime_applicability(
                requirements=requirements,
                conclusions=tuple(
                    conclusions
                ),
                avf_requirement=avf_requirement,
            )
        )

        return tuple(
            sorted(
                conclusions,
                key=lambda item: (
                    item.requirement_id
                ),
            )
        )

    @classmethod
    def _apply_avf_guest_runtime_applicability(
        cls,
        *,
        requirements: tuple[
            AndroidUniverseFstabRequirement,
            ...,
        ],
        conclusions: tuple[
            AndroidUniverseRequirementApplicability,
            ...,
        ],
        avf_requirement: (
            AndroidUniverseAvfRequirement
            | None
        ),
    ) -> tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ]:
        """
        Resolve dedicated guest-runtime Fstab sources from canonical AVF
        runtime identity.

        A source named fstab.<runtime> is an unselected guest alternative
        only when AVF canonically declares that exact guest runtime name.

        The runtime name is not hard-coded here. Already-resolved
        applicability remains authoritative.
        """

        if avf_requirement is None:
            return conclusions

        guest_runtime_names = frozenset(
            family.guest_runtime_name
            for family
            in avf_requirement.families
            if family.guest_runtime_name
        )

        if not guest_runtime_names:
            return conclusions

        requirement_by_id = {
            requirement.requirement_id:
                requirement
            for requirement
            in requirements
        }

        replacements = {}

        for conclusion in conclusions:
            if (
                conclusion.status
                is not AndroidUniverseApplicabilityStatus
                .UNRESOLVED
            ):
                continue

            requirement = requirement_by_id[
                conclusion.requirement_id
            ]

            if requirement.android_path is None:
                continue

            source_name = (
                requirement.android_path.name
            )

            prefix = "fstab."

            if not source_name.startswith(
                prefix
            ):
                continue

            guest_runtime_name = source_name[
                len(
                    prefix
                ):
            ]

            if (
                not guest_runtime_name
                or guest_runtime_name
                not in guest_runtime_names
            ):
                continue

            runtime_path = (
                "/"
                + requirement
                .android_path
                .as_posix()
                .lstrip("/")
            )

            replacements[
                conclusion.requirement_id
            ] = (
                AndroidUniverseRequirementApplicability(
                    requirement_id=(
                        conclusion.requirement_id
                    ),
                    status=(
                        AndroidUniverseApplicabilityStatus
                        .ALTERNATIVE
                    ),
                    evidence=(
                        AndroidUniverseApplicabilityEvidence(
                            kind=(
                                AndroidUniverseApplicabilityEvidenceKind
                                .SOURCE_STRUCTURE
                            ),
                            raw_value=(
                                "canonical AVF guest runtime "
                                f"{guest_runtime_name!r} matches "
                                "dedicated Fstab source "
                                f"{runtime_path}"
                            ),
                            source_path=(
                                requirement.source_path
                            ),
                            android_path=(
                                requirement.android_path
                            ),
                            line_number=(
                                requirement
                                .declaration
                                .line_number
                            ),
                        ),
                    ),
                    alternative_group=(
                        "avf-guest-runtime:"
                        + guest_runtime_name
                    ),
                    selector_key=(
                        "avf.guest_runtime_name"
                    ),
                    selector_value=(
                        guest_runtime_name
                    ),
                )
            )

        return tuple(
            replacements.get(
                conclusion.requirement_id,
                conclusion,
            )
            for conclusion
            in conclusions
        )

    def _propagate_equivalent_source_applicability(
        self,
        *,
        requirements: tuple[
            AndroidUniverseFstabRequirement,
            ...,
        ],
        conclusions: tuple[
            AndroidUniverseRequirementApplicability,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseRequirementApplicability,
        ...,
    ]:
        """
        Propagate an already-proven applicability conclusion across
        semantically equivalent canonical Fstab sources.

        Equivalence is source-wide, not entry-local:

          * declarations must have the same canonical count;
          * declaration order must match;
          * every declaration must have the same parsed semantic payload.

        Source provenance, Android path, host path, comments, and source-line
        identity do not participate in the semantic payload comparison.

        An UNRESOLVED requirement is promoted only when equivalent resolved
        peers expose exactly one compatible applicability fingerprint.

        If equivalent peers disagree, or if no peer is resolved, the
        requirement remains UNRESOLVED.
        """

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not isinstance(
            conclusions,
            tuple,
        ):
            raise TypeError(
                "conclusions must be a tuple"
            )

        requirement_by_id = {
            requirement.requirement_id:
                requirement
            for requirement
            in requirements
        }

        conclusion_by_id = {
            conclusion.requirement_id:
                conclusion
            for conclusion
            in conclusions
        }

        if (
            set(
                requirement_by_id
            )
            != set(
                conclusion_by_id
            )
        ):
            raise ValueError(
                "Fstab applicability equivalence propagation "
                "requires exact requirement/conclusion coverage"
            )

        sources: dict[
            tuple[
                str,
                str,
            ],
            list[
                AndroidUniverseFstabRequirement
            ],
        ] = {}

        for requirement in requirements:
            source_identity = (
                self._source_identity(
                    requirement
                )
            )

            sources.setdefault(
                source_identity,
                [],
            ).append(
                requirement
            )

        canonical_sources = {
            source_identity: tuple(
                sorted(
                    source_requirements,
                    key=lambda requirement: (
                        requirement
                        .declaration
                        .line_number,
                        requirement
                        .requirement_id,
                    ),
                )
            )
            for (
                source_identity,
                source_requirements,
            )
            in sources.items()
        }

        equivalence_groups: dict[
            tuple,
            list[
                tuple[
                    tuple[
                        str,
                        str,
                    ],
                    tuple[
                        AndroidUniverseFstabRequirement,
                        ...,
                    ],
                ]
            ],
        ] = {}

        for (
            source_identity,
            source_requirements,
        ) in canonical_sources.items():
            signature = tuple(
                self._semantic_payload_key(
                    requirement
                )
                for requirement
                in source_requirements
            )

            equivalence_groups.setdefault(
                signature,
                [],
            ).append(
                (
                    source_identity,
                    source_requirements,
                )
            )

        replacements: dict[
            str,
            AndroidUniverseRequirementApplicability,
        ] = {}

        for equivalent_sources in (
            equivalence_groups.values()
        ):
            if len(
                equivalent_sources
            ) < 2:
                continue

            widths = {
                len(
                    source_requirements
                )
                for (
                    _,
                    source_requirements,
                )
                in equivalent_sources
            }

            if len(widths) != 1:
                raise ValueError(
                    "semantically equivalent Fstab sources "
                    "must preserve identical declaration counts"
                )

            width = next(
                iter(
                    widths
                )
            )

            for index in range(
                width
            ):
                peers = tuple(
                    source_requirements[
                        index
                    ]
                    for (
                        _,
                        source_requirements,
                    )
                    in equivalent_sources
                )

                resolved = tuple(
                    (
                        peer,
                        conclusion_by_id[
                            peer.requirement_id
                        ],
                    )
                    for peer in peers
                    if (
                        conclusion_by_id[
                            peer.requirement_id
                        ].status
                        is not AndroidUniverseApplicabilityStatus
                        .UNRESOLVED
                    )
                )

                if not resolved:
                    continue

                fingerprints = {
                    (
                        conclusion.status,
                        conclusion.alternative_group,
                        conclusion.selector_key,
                        conclusion.selector_value,
                    )
                    for (
                        _,
                        conclusion,
                    )
                    in resolved
                }

                #
                # Source equivalence is not permission to choose between
                # conflicting applicability conclusions.
                #
                if len(
                    fingerprints
                ) != 1:
                    continue

                (
                    status,
                    alternative_group,
                    selector_key,
                    selector_value,
                ) = next(
                    iter(
                        fingerprints
                    )
                )

                canonical_resolved = tuple(
                    sorted(
                        resolved,
                        key=lambda item: (
                            item[0]
                            .requirement_id
                        ),
                    )
                )

                for peer in peers:
                    existing = (
                        conclusion_by_id[
                            peer.requirement_id
                        ]
                    )

                    if (
                        existing.status
                        is not AndroidUniverseApplicabilityStatus
                        .UNRESOLVED
                    ):
                        continue

                    inherited_evidence = tuple(
                        evidence
                        for (
                            _,
                            conclusion,
                        )
                        in canonical_resolved
                        for evidence
                        in conclusion.evidence
                    )

                    equivalence_evidence = tuple(
                        AndroidUniverseApplicabilityEvidence(
                            kind=(
                                AndroidUniverseApplicabilityEvidenceKind
                                .SOURCE_EQUIVALENCE
                            ),
                            raw_value=(
                                "semantically equivalent canonical "
                                "Fstab source: "
                                + self._source_identity_text(
                                    resolved_requirement
                                )
                            ),
                            source_path=(
                                resolved_requirement
                                .source_path
                            ),
                            android_path=(
                                resolved_requirement
                                .android_path
                            ),
                            line_number=(
                                resolved_requirement
                                .declaration
                                .line_number
                            ),
                        )
                        for (
                            resolved_requirement,
                            _,
                        )
                        in canonical_resolved
                    )

                    replacements[
                        peer.requirement_id
                    ] = (
                        AndroidUniverseRequirementApplicability(
                            requirement_id=(
                                peer.requirement_id
                            ),
                            status=status,
                            evidence=(
                                self._canonical_evidence(
                                    evidence=(
                                        inherited_evidence
                                        + equivalence_evidence
                                    )
                                )
                            ),
                            alternative_group=(
                                alternative_group
                            ),
                            selector_key=(
                                selector_key
                            ),
                            selector_value=(
                                selector_value
                            ),
                        )
                    )

        return tuple(
            replacements.get(
                conclusion.requirement_id,
                conclusion,
            )
            for conclusion
            in conclusions
        )

    @staticmethod
    def _source_identity(
        requirement: AndroidUniverseFstabRequirement,
    ) -> tuple[
        str,
        str,
    ]:
        path_identity = (
            requirement.android_path.as_posix()
            if requirement.android_path
            is not None
            else requirement.source_path.as_posix()
        )

        return (
            requirement.source_name,
            path_identity,
        )

    @classmethod
    def _source_identity_text(
        cls,
        requirement: AndroidUniverseFstabRequirement,
    ) -> str:
        (
            source_name,
            path_identity,
        ) = cls._source_identity(
            requirement
        )

        return (
            f"{source_name}::"
            f"{path_identity}"
        )

    @staticmethod
    def _semantic_payload_key(
        requirement: AndroidUniverseFstabRequirement,
    ) -> tuple:
        """
        Return source-independent semantic identity for one parsed Fstab
        declaration.

        Raw source provenance and line number are intentionally excluded.
        The complete parsed fields that determine the declaration's Fstab
        behavior remain represented.
        """

        return (
            requirement.device,
            requirement.mount_point,
            requirement.filesystem_type,
            requirement.mount_options,
            requirement.fs_mgr_flags,
        )

    def _build_selector_groups(
        self,
        *,
        requirements: tuple[
            AndroidUniverseFstabRequirement,
            ...,
        ],
        observations: tuple[
            AndroidUniverseFstabApplicabilityObservation,
            ...,
        ],
    ) -> tuple[
        tuple[
            str,
            str,
            re.Pattern[str],
            tuple[
                AndroidUniverseApplicabilityEvidence,
                ...,
            ],
        ],
        ...,
    ]:
        groups = {}

        for observation in observations:
            expression = (
                observation.referenced_path_expression
            )
            selector_key = observation.selector_key

            if (
                expression is None
                or selector_key is None
                or not observation.evidence
            ):
                continue

            pattern = self._selector_pattern(
                expression=expression,
                selector_key=selector_key,
            )

            if pattern is None:
                continue

            group_key = (
                expression,
                selector_key,
            )

            groups.setdefault(
                group_key,
                {
                    "pattern": pattern,
                    "evidence": [],
                },
            )

            groups[
                group_key
            ][
                "evidence"
            ].extend(
                observation.evidence
            )

        return tuple(
            (
                expression,
                selector_key,
                values["pattern"],
                self._canonical_evidence(
                    evidence=tuple(
                        values["evidence"]
                    )
                ),
            )
            for (
                expression,
                selector_key,
            ), values in sorted(
                groups.items()
            )
        )

    def _alternative_for_requirement(
        self,
        *,
        requirement: AndroidUniverseFstabRequirement,
        selector_groups: tuple[
            tuple[
                str,
                str,
                re.Pattern[str],
                tuple[
                    AndroidUniverseApplicabilityEvidence,
                    ...,
                ],
            ],
            ...,
        ],
    ) -> tuple[
        str,
        str,
        str,
        tuple[
            AndroidUniverseApplicabilityEvidence,
            ...,
        ],
    ] | None:
        if requirement.android_path is None:
            return None

        runtime_path = (
            "/"
            + requirement.android_path.as_posix().lstrip("/")
        )

        matches = []

        for (
            expression,
            selector_key,
            pattern,
            evidence,
        ) in selector_groups:
            match = pattern.fullmatch(
                runtime_path
            )

            if match is None:
                continue

            selector_value = match.group(
                "selector_value"
            )

            source_structure_evidence = (
                AndroidUniverseApplicabilityEvidence(
                    kind=(
                        AndroidUniverseApplicabilityEvidenceKind
                        .SOURCE_STRUCTURE
                    ),
                    raw_value=runtime_path,
                    source_path=(
                        requirement.source_path
                    ),
                    android_path=(
                        requirement.android_path
                    ),
                    line_number=(
                        requirement.declaration.line_number
                    ),
                ),
            )

            matches.append(
                (
                    expression,
                    selector_key,
                    selector_value,
                    self._canonical_evidence(
                        evidence=(
                            evidence
                            + source_structure_evidence
                        )
                    ),
                )
            )

        if not matches:
            return None

        if len(matches) > 1:
            # Selector expressions may overlap structurally. For example,
            # "/vendor/etc/fstab.${ro.board.platform}" also matches paths
            # belonging to the more specific
            # "/vendor/etc/fstab.zram.${vendor.zram.size}" family.
            #
            # Prefer a unique selector expression with the greatest amount
            # of literal path structure around its substitution token.
            # Equal-specificity matches remain unresolved rather than
            # guessing which selector family owns the requirement.
            matches_by_specificity = {}

            for match_item in matches:
                (
                    expression,
                    selector_key,
                    selector_value,
                    evidence,
                ) = match_item

                specificity = (
                    self._selector_specificity(
                        expression=expression,
                        selector_key=selector_key,
                    )
                )

                matches_by_specificity.setdefault(
                    specificity,
                    [],
                ).append(
                    match_item
                )

            highest_specificity = max(
                matches_by_specificity
            )

            most_specific_matches = (
                matches_by_specificity[
                    highest_specificity
                ]
            )

            if len(
                most_specific_matches
            ) != 1:
                return None

            return most_specific_matches[0]

        return matches[0]

    @staticmethod
    def _selector_specificity(
        *,
        expression: str,
        selector_key: str,
    ) -> int:
        """
        Return literal-path specificity for one selector expression.

        Only the selector token itself is excluded. A larger value therefore
        means that more of the candidate path is fixed by the expression.

        This is used solely to disambiguate overlapping structural selector
        domains. Equal-specificity matches remain unresolved.
        """

        token = (
            "${"
            + selector_key
            + "}"
        )

        if expression.count(
            token
        ) != 1:
            return -1

        prefix, suffix = expression.split(
            token,
            1,
        )

        return (
            len(prefix)
            + len(suffix)
        )


    @staticmethod
    def _selector_pattern(
        *,
        expression: str,
        selector_key: str,
    ) -> re.Pattern[str] | None:
        token = (
            "${"
            + selector_key
            + "}"
        )

        if expression.count(token) != 1:
            return None

        prefix, suffix = expression.split(
            token,
            1,
        )

        return re.compile(
            "^"
            + re.escape(prefix)
            + r"(?P<selector_value>.+?)"
            + re.escape(suffix)
            + "$"
        )

    @staticmethod
    def _canonical_evidence(
        *,
        evidence: tuple[
            AndroidUniverseApplicabilityEvidence,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseApplicabilityEvidence,
        ...,
    ]:
        unique = {}

        for item in evidence:
            key = (
                item.kind.value,
                (
                    item.android_path.as_posix()
                    if item.android_path is not None
                    else ""
                ),
                (
                    item.source_path.as_posix()
                    if item.source_path is not None
                    else ""
                ),
                item.line_number or 0,
                item.raw_value,
            )

            unique[key] = item

        return tuple(
            unique[key]
            for key in sorted(
                unique
            )
        )

    @staticmethod
    def _observation_sort_key(
        item: AndroidUniverseFstabApplicabilityObservation,
    ) -> tuple:
        return (
            item.resolved_path or "",
            item.referenced_path_expression or "",
            item.selector_key or "",
            item.selector_value or "",
            tuple(
                (
                    evidence.kind.value,
                    (
                        evidence.android_path.as_posix()
                        if evidence.android_path is not None
                        else ""
                    ),
                    (
                        evidence.source_path.as_posix()
                        if evidence.source_path is not None
                        else ""
                    ),
                    evidence.line_number or 0,
                    evidence.raw_value,
                )
                for evidence in item.evidence
            ),
        )


class AndroidUniverseFstabApplicabilityInterpreter:
    """
    Discover cross-artifact evidence about fstab applicability.

    Parsing remains responsible only for literal init/property/fstab decoding.
    This interpreter correlates those already-parsed observations inside the
    Device Universe.

    It does not decide final applicability status.
    """

    _FSTAB_COMMANDS = frozenset(
        {
            "mount_all",
            "swapon_all",
        }
    )

    def interpret(
        self,
        *,
        parsing: AndroidFilesystemParsingResult,
        requirements: tuple[
            AndroidUniverseFstabRequirement,
            ...,
        ],
        init_action_requirements: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseFstabApplicabilityObservation,
        ...,
    ]:
        if not isinstance(
            parsing,
            AndroidFilesystemParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidFilesystemParsingResult"
            )

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFstabRequirement,
            )
            for item in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseFstabRequirement instances"
            )

        if not isinstance(
            init_action_requirements,
            tuple,
        ):
            raise TypeError(
                "init_action_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitActionRequirement,
            )
            for item in init_action_requirements
        ):
            raise TypeError(
                "init_action_requirements must contain only "
                "AndroidUniverseInitActionRequirement instances"
            )

        properties = self._collect_properties(
            parsing.property_files
        )

        references = self._collect_init_references(
            init_action_requirements,
            properties,
        )

        observations = []

        for requirement in requirements:
            requirement_path = (
                requirement.android_path.as_posix()
                if requirement.android_path is not None
                else None
            )

            matched = tuple(
                reference
                for reference in references
                if (
                    requirement_path is not None
                    and reference.resolved_path is not None
                    and (
                        "/"
                        + reference.resolved_path.lstrip("/")
                    )
                    == requirement_path
                )
            )

            if matched:
                for reference in matched:
                    observations.append(
                        AndroidUniverseFstabApplicabilityObservation(
                            requirement_id=(
                                requirement.requirement_id
                            ),
                            referenced_path_expression=(
                                reference
                                .referenced_path_expression
                            ),
                            resolved_path=(
                                reference.resolved_path
                            ),
                            selector_key=(
                                reference.selector_key
                            ),
                            selector_value=(
                                reference.selector_value
                            ),
                            evidence=reference.evidence,
                        )
                    )
            else:
                observations.append(
                    AndroidUniverseFstabApplicabilityObservation(
                        requirement_id=(
                            requirement.requirement_id
                        ),
                    )
                )

        return tuple(
            sorted(
                observations,
                key=lambda item: (
                    item.requirement_id,
                    item.resolved_path or "",
                    item.selector_key or "",
                    item.selector_value or "",
                ),
            )
        )

    def _collect_properties(
        self,
        property_files: tuple[
            ParsedAndroidPropertyFile,
            ...,
        ],
    ) -> dict[
        str,
        tuple[
            tuple[
                str,
                AndroidUniverseApplicabilityEvidence,
            ],
            ...,
        ],
    ]:
        collected: dict[
            str,
            list[
                tuple[
                    str,
                    AndroidUniverseApplicabilityEvidence,
                ]
            ],
        ] = {}

        for source in property_files:
            for declaration in source.declarations:
                evidence = (
                    AndroidUniverseApplicabilityEvidence(
                        kind=(
                            AndroidUniverseApplicabilityEvidenceKind
                            .PROPERTY
                        ),
                        raw_value=declaration.raw,
                        source_path=source.source_path,
                        android_path=source.android_path,
                        line_number=declaration.line_number,
                    )
                )

                collected.setdefault(
                    declaration.key,
                    [],
                ).append(
                    (
                        declaration.value,
                        evidence,
                    )
                )

        return {
            key: tuple(values)
            for key, values in collected.items()
        }

    def _collect_init_references(
        self,
        init_action_requirements: tuple[
            AndroidUniverseInitActionRequirement,
            ...,
        ],
        properties: dict[
            str,
            tuple[
                tuple[
                    str,
                    AndroidUniverseApplicabilityEvidence,
                ],
                ...,
            ],
        ],
    ) -> tuple[
        AndroidUniverseFstabApplicabilityObservation,
        ...,
    ]:
        references = []

        for requirement in init_action_requirements:
            for command in requirement.commands:
                    if (
                        command.keyword
                        not in self._FSTAB_COMMANDS
                    ):
                        continue

                    if not command.arguments:
                        continue

                    path_expression = (
                        command.arguments[0]
                    )

                    init_evidence = (
                        AndroidUniverseApplicabilityEvidence(
                            kind=(
                                AndroidUniverseApplicabilityEvidenceKind
                                .INIT_COMMAND
                            ),
                            raw_value=command.raw,
                            source_path=(
                                requirement.source_path
                            ),
                            android_path=(
                                requirement.android_path
                            ),
                            line_number=(
                                command.location.line
                            ),
                        )
                    )

                    property_match = (
                        _PROPERTY_REFERENCE.search(
                            path_expression
                        )
                    )

                    if property_match is None:
                        references.append(
                            AndroidUniverseFstabApplicabilityObservation(
                                requirement_id=(
                                    "__init_reference__"
                                ),
                                referenced_path_expression=(
                                    path_expression
                                ),
                                resolved_path=path_expression,
                                evidence=(
                                    init_evidence,
                                ),
                            )
                        )

                        continue

                    selector_key = (
                        property_match.group(
                            "key"
                        )
                    )

                    values = properties.get(
                        selector_key,
                        (),
                    )

                    if not values:
                        references.append(
                            AndroidUniverseFstabApplicabilityObservation(
                                requirement_id=(
                                    "__init_reference__"
                                ),
                                referenced_path_expression=(
                                    path_expression
                                ),
                                selector_key=selector_key,
                                evidence=(
                                    init_evidence,
                                ),
                            )
                        )

                        continue

                    for (
                        selector_value,
                        property_evidence,
                    ) in values:
                        resolved_path = (
                            path_expression.replace(
                                property_match.group(0),
                                selector_value,
                            )
                        )

                        references.append(
                            AndroidUniverseFstabApplicabilityObservation(
                                requirement_id=(
                                    "__init_reference__"
                                ),
                                referenced_path_expression=(
                                    path_expression
                                ),
                                resolved_path=resolved_path,
                                selector_key=selector_key,
                                selector_value=selector_value,
                                evidence=(
                                    init_evidence,
                                    property_evidence,
                                ),
                            )
                        )

        return tuple(
            references
        )
