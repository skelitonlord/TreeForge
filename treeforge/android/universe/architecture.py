from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.knowledge.model import (
    AndroidKnowledgeModule,
)
from treeforge.android.knowledge.universe import (
    AndroidUniverseArchitectureKnowledge,
)
from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
    AndroidUniverseElfSoongBuildTupleRequirement,
)

class AndroidUniverseArchitectureObservationKind(
    StrEnum
):
    """
    Evidence origin for one generic architecture observation.
    """

    PROPERTY = "property"

    PROPERTY_DERIVED = "property_derived"

    ELF_SOONG = "elf_soong"

    KNOWLEDGE = "knowledge"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArchitectureObservation:
    """
    One exact architecture observation available to Universe.

    Property observations retain the canonical AndroidUniversePropertyEvidence
    object, which in turn preserves the exact Parsing source, declaration,
    model source, partition, extraction artifact, and upstream lineage.

    Knowledge observations retain the exact resolved AndroidKnowledgeModule
    that supplied the architecture payload.

    No provenance is collapsed into strings.
    """

    fact: str

    value: str

    kind: AndroidUniverseArchitectureObservationKind

    property_evidence: (
        AndroidUniversePropertyEvidence
        | None
    ) = None

    property_derivation: str | None = None

    elf_soong_requirement: (
        AndroidUniverseElfSoongBuildTupleRequirement
        | None
    ) = None

    knowledge_module: (
        AndroidKnowledgeModule
        | None
    ) = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.fact,
            str,
        ):
            raise TypeError(
                "fact must be a string"
            )

        if not self.fact.strip():
            raise ValueError(
                "fact must not be empty"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseArchitectureObservationKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseArchitectureObservationKind"
            )

        if (
            self.property_evidence is not None
            and not isinstance(
                self.property_evidence,
                AndroidUniversePropertyEvidence,
            )
        ):
            raise TypeError(
                "property_evidence must be an "
                "AndroidUniversePropertyEvidence or None"
            )

        if (
            self.property_derivation is not None
            and not isinstance(
                self.property_derivation,
                str,
            )
        ):
            raise TypeError(
                "property_derivation must be a string or None"
            )

        if (
            self.elf_soong_requirement is not None
            and not isinstance(
                self.elf_soong_requirement,
                AndroidUniverseElfSoongBuildTupleRequirement,
            )
        ):
            raise TypeError(
                "elf_soong_requirement must be an "
                "AndroidUniverseElfSoongBuildTupleRequirement "
                "or None"
            )

        if (
            self.knowledge_module is not None
            and not isinstance(
                self.knowledge_module,
                AndroidKnowledgeModule,
            )
        ):
            raise TypeError(
                "knowledge_module must be an "
                "AndroidKnowledgeModule or None"
            )

        if (
            self.kind
            is AndroidUniverseArchitectureObservationKind.PROPERTY
        ):
            if self.property_evidence is None:
                raise ValueError(
                    "property architecture observations require "
                    "property_evidence"
                )

            if self.knowledge_module is not None:
                raise ValueError(
                    "property architecture observations must not "
                    "carry knowledge_module"
                )

            if self.property_derivation is not None:
                raise ValueError(
                    "direct property architecture observations must not "
                    "carry property_derivation"
                )

            if self.elf_soong_requirement is not None:
                raise ValueError(
                    "property architecture observations must not "
                    "carry elf_soong_requirement"
                )

            # The semantic architecture fact may intentionally differ
            # from the literal property-derived fact name.
            #
            # Example:
            #
            #   ro.bionic.cpu_variant
            #       -> property fact: primary_cpu_variant
            #       -> architecture fact: primary_cpu_variant_runtime
            #
            # The exact source fact remains preserved inside
            # property_evidence; only the value must remain identical.
            if (
                self.property_evidence.fact.value
                != self.value
            ):
                raise ValueError(
                    "property evidence value must match "
                    "architecture observation value"
                )

            if not self.value:
                raise ValueError(
                    "property architecture observation value "
                    "must not be empty"
                )

        if (
            self.kind
            is (
                AndroidUniverseArchitectureObservationKind
                .PROPERTY_DERIVED
            )
        ):
            if self.property_evidence is None:
                raise ValueError(
                    "derived property architecture observations "
                    "require property_evidence"
                )

            if (
                self.property_derivation is None
                or not self.property_derivation.strip()
            ):
                raise ValueError(
                    "derived property architecture observations "
                    "require property_derivation"
                )

            if self.elf_soong_requirement is not None:
                raise ValueError(
                    "derived property architecture observations "
                    "must not carry elf_soong_requirement"
                )

            if self.knowledge_module is not None:
                raise ValueError(
                    "derived property architecture observations "
                    "must not carry knowledge_module"
                )

            if not self.value:
                raise ValueError(
                    "derived property architecture observation "
                    "value must not be empty"
                )

        if (
            self.kind
            is AndroidUniverseArchitectureObservationKind.ELF_SOONG
        ):
            if self.elf_soong_requirement is None:
                raise ValueError(
                    "ELF/Soong architecture observations require "
                    "elf_soong_requirement"
                )

            if self.property_evidence is not None:
                raise ValueError(
                    "ELF/Soong architecture observations must not "
                    "carry property_evidence"
                )

            if self.property_derivation is not None:
                raise ValueError(
                    "ELF/Soong architecture observations must not "
                    "carry property_derivation"
                )

            if self.knowledge_module is not None:
                raise ValueError(
                    "ELF/Soong architecture observations must not "
                    "carry knowledge_module"
                )

            if not self.value:
                raise ValueError(
                    "ELF/Soong architecture observation value "
                    "must not be empty"
                )

        if (
            self.kind
            is AndroidUniverseArchitectureObservationKind.KNOWLEDGE
        ):
            if not self.value:
                raise ValueError(
                    "knowledge architecture observation value "
                    "must not be empty"
                )

            if self.knowledge_module is None:
                raise ValueError(
                    "knowledge architecture observations require "
                    "knowledge_module"
                )

            if self.property_evidence is not None:
                raise ValueError(
                    "knowledge architecture observations must not "
                    "carry property_evidence"
                )

            if self.property_derivation is not None:
                raise ValueError(
                    "knowledge architecture observations must not "
                    "carry property_derivation"
                )

            if self.elf_soong_requirement is not None:
                raise ValueError(
                    "knowledge architecture observations must not "
                    "carry elf_soong_requirement"
                )

            if self.knowledge_module.universe is None:
                raise ValueError(
                    "knowledge architecture observation module "
                    "must expose Universe knowledge"
                )

            architecture = (
                self.knowledge_module
                .universe
                .architecture
            )

            if architecture is None:
                raise ValueError(
                    "knowledge architecture observation module "
                    "must expose architecture knowledge"
                )

            if (
                getattr(
                    architecture,
                    self.fact,
                    None,
                )
                != self.value
            ):
                raise ValueError(
                    "knowledge module architecture value must "
                    "match architecture observation"
                )

    @property
    def knowledge_module_id(
        self,
    ) -> str | None:
        if self.knowledge_module is None:
            return None

        return self.knowledge_module.module_id


class AndroidUniverseArchitectureConclusionStatus(
    StrEnum
):
    """
    Resolution state for one canonical architecture fact.
    """

    UNRESOLVED = "unresolved"

    AGREED = "agreed"

    ABSENT = "absent"

    CONFLICTING = "conflicting"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArchitectureFactConclusion:
    """
    Canonical Universe conclusion for one architecture fact.

    Every observation remains attached. A canonical value exists only when
    every non-empty observation agrees.
    """

    fact: str

    status: AndroidUniverseArchitectureConclusionStatus

    value: str | None

    observations: tuple[
        AndroidUniverseArchitectureObservation,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.fact,
            str,
        ):
            raise TypeError(
                "fact must be a string"
            )

        if not self.fact.strip():
            raise ValueError(
                "fact must not be empty"
            )

        if not isinstance(
            self.status,
            AndroidUniverseArchitectureConclusionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseArchitectureConclusionStatus"
            )

        if (
            self.value is not None
            and not isinstance(
                self.value,
                str,
            )
        ):
            raise TypeError(
                "value must be a string or None"
            )

        if not isinstance(
            self.observations,
            tuple,
        ):
            raise TypeError(
                "observations must be a tuple"
            )

        if not all(
            isinstance(
                observation,
                AndroidUniverseArchitectureObservation,
            )
            for observation in self.observations
        ):
            raise TypeError(
                "observations must contain only "
                "AndroidUniverseArchitectureObservation instances"
            )

        if not all(
            observation.fact
            == self.fact
            for observation
            in self.observations
        ):
            raise ValueError(
                "all architecture observations must match "
                "the conclusion fact"
            )

        if (
            self.status
            is AndroidUniverseArchitectureConclusionStatus.AGREED
        ):
            if not self.value:
                raise ValueError(
                    "agreed architecture conclusion "
                    "must have a value"
                )

        else:
            if self.value is not None:
                raise ValueError(
                    "only agreed architecture conclusions "
                    "may have a value"
                )

    @property
    def distinct_values(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            sorted(
                {
                    observation.value
                    for observation
                    in self.observations
                    if observation.value
                }
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArchitecture:
    """
    Canonical Android architecture owned by Device Universe.

    The model uses generic Android concepts. It deliberately contains no
    TARGET_*, PRODUCT_*, BOARD_*, BoardConfig, device-specific, platform-
    specific, or Android-version-specific names.
    """

    conclusions: tuple[
        AndroidUniverseArchitectureFactConclusion,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.conclusions,
            tuple,
        ):
            raise TypeError(
                "conclusions must be a tuple"
            )

        if not all(
            isinstance(
                conclusion,
                AndroidUniverseArchitectureFactConclusion,
            )
            for conclusion
            in self.conclusions
        ):
            raise TypeError(
                "conclusions must contain only "
                "AndroidUniverseArchitectureFactConclusion instances"
            )

        facts = tuple(
            conclusion.fact
            for conclusion
            in self.conclusions
        )

        if facts != tuple(
            sorted(
                facts
            )
        ):
            raise ValueError(
                "architecture conclusions must be in "
                "canonical fact order"
            )

        if len(
            facts
        ) != len(
            set(
                facts
            )
        ):
            raise ValueError(
                "architecture conclusions must contain "
                "one entry per fact"
            )

    def conclusion(
        self,
        fact: str,
    ) -> (
        AndroidUniverseArchitectureFactConclusion
        | None
    ):
        for conclusion in self.conclusions:
            if conclusion.fact == fact:
                return conclusion

        return None

    def value(
        self,
        fact: str,
    ) -> str | None:
        conclusion = self.conclusion(
            fact
        )

        if (
            conclusion is None
            or conclusion.status
            is not (
                AndroidUniverseArchitectureConclusionStatus
                .AGREED
            )
        ):
            return None

        return conclusion.value

    @property
    def board_platform(
        self,
    ) -> str | None:
        return self.value(
            "board_platform"
        )

    @property
    def primary_architecture(
        self,
    ) -> str | None:
        return self.value(
            "primary_architecture"
        )

    @property
    def primary_arch_variant(
        self,
    ) -> str | None:
        return self.value(
            "primary_arch_variant"
        )

    @property
    def primary_cpu_abi(
        self,
    ) -> str | None:
        return self.value(
            "primary_cpu_abi"
        )

    @property
    def primary_cpu_variant(
        self,
    ) -> str | None:
        return self.value(
            "primary_cpu_variant"
        )

    @property
    def primary_cpu_variant_runtime(
        self,
    ) -> str | None:
        return self.value(
            "primary_cpu_variant_runtime"
        )

    @property
    def secondary_architecture(
        self,
    ) -> str | None:
        return self.value(
            "secondary_architecture"
        )

    @property
    def secondary_arch_variant(
        self,
    ) -> str | None:
        return self.value(
            "secondary_arch_variant"
        )

    @property
    def secondary_cpu_abi(
        self,
    ) -> str | None:
        return self.value(
            "secondary_cpu_abi"
        )

    @property
    def secondary_cpu_abi2(
        self,
    ) -> str | None:
        return self.value(
            "secondary_cpu_abi2"
        )

    @property
    def secondary_cpu_variant(
        self,
    ) -> str | None:
        return self.value(
            "secondary_cpu_variant"
        )

    @property
    def secondary_cpu_variant_runtime(
        self,
    ) -> str | None:
        return self.value(
            "secondary_cpu_variant_runtime"
        )


class AndroidUniverseArchitectureReconciler:
    """
    Reconcile factory/property and resolved knowledge evidence.

    Generic Universe never silently prioritizes a knowledge module over
    factory evidence or vice versa. Agreement produces one canonical value;
    disagreement is preserved as a conflict.
    """

    FACTS = (
        "board_platform",
        "primary_arch_variant",
        "primary_architecture",
        "primary_cpu_abi",
        "primary_cpu_variant",
        "primary_cpu_variant_runtime",
        "secondary_arch_variant",
        "secondary_architecture",
        "secondary_cpu_abi",
        "secondary_cpu_abi2",
        "secondary_cpu_variant",
        "secondary_cpu_variant_runtime",
    )

    PROPERTY_FACT_ALIASES = {
        "board_platform": (
            "board_platform",
        ),
        "primary_architecture": (
            "primary_architecture",
        ),
        "primary_cpu_abi": (
            "primary_cpu_abi",
        ),

        # ro.bionic.cpu_variant is a runtime/device observation.
        "primary_cpu_variant_runtime": (
            "primary_cpu_variant",
        ),

        "secondary_architecture": (
            "secondary_architecture",
        ),

        # ro.bionic.2nd_cpu_variant is likewise runtime/device evidence.
        "secondary_cpu_variant_runtime": (
            "secondary_cpu_variant",
        ),
    }

    def reconcile(
        self,
        *,
        property_evidence: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ] = (),
        knowledge_modules: tuple[
            AndroidKnowledgeModule,
            ...,
        ] = (),
    ) -> AndroidUniverseArchitecture:
        if not isinstance(
            property_evidence,
            tuple,
        ):
            raise TypeError(
                "property_evidence must be a tuple"
            )

        if not all(
            isinstance(
                evidence,
                AndroidUniversePropertyEvidence,
            )
            for evidence
            in property_evidence
        ):
            raise TypeError(
                "property_evidence must contain only "
                "AndroidUniversePropertyEvidence instances"
            )

        if not isinstance(
            elf_requirements,
            tuple,
        ):
            raise TypeError(
                "elf_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            )
            for requirement
            in elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement instances"
            )

        if not isinstance(
            knowledge_modules,
            tuple,
        ):
            raise TypeError(
                "knowledge_modules must be a tuple"
            )

        if not all(
            isinstance(
                module,
                AndroidKnowledgeModule,
            )
            for module
            in knowledge_modules
        ):
            raise TypeError(
                "knowledge_modules must contain only "
                "AndroidKnowledgeModule instances"
            )

        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ] = {
            fact: []
            for fact
            in self.FACTS
        }

        self._add_property_observations(
            observations=observations,
            property_evidence=property_evidence,
        )

        self._add_ordered_abi_observations(
            observations=observations,
            property_evidence=property_evidence,
        )

        self._add_elf_soong_observations(
            observations=observations,
            elf_requirements=elf_requirements,
        )

        self._add_android_arm_semantic_observations(
            observations=observations,
            property_evidence=property_evidence,
            elf_requirements=elf_requirements,
        )

        self._add_knowledge_observations(
            observations=observations,
            knowledge_modules=knowledge_modules,
        )

        return AndroidUniverseArchitecture(
            conclusions=tuple(
                self._reconcile_fact(
                    fact=fact,
                    observations=tuple(
                        sorted(
                            observations[fact],
                            key=self._observation_sort_key,
                        )
                    ),
                )
                for fact
                in self.FACTS
            )
        )

    def _add_property_observations(
        self,
        *,
        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ],
        property_evidence: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
    ) -> None:
        reverse_aliases = {
            source_fact: target_fact
            for target_fact, source_facts
            in self.PROPERTY_FACT_ALIASES.items()
            for source_fact
            in source_facts
        }

        for evidence in property_evidence:
            source_fact = evidence.fact.fact

            target_fact = reverse_aliases.get(
                source_fact
            )

            if target_fact is None:
                continue

            observations[
                target_fact
            ].append(
                AndroidUniverseArchitectureObservation(
                    fact=target_fact,
                    value=evidence.fact.value,
                    kind=(
                        AndroidUniverseArchitectureObservationKind
                        .PROPERTY
                    ),
                    property_evidence=evidence,
                )
            )

    def _add_ordered_abi_observations(
        self,
        *,
        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ],
        property_evidence: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
    ) -> None:
        """
        Derive positional 32-bit ABI facts from the canonical ordered ABI list.

        Android's abilist32 property is ordered. Universe may therefore
        preserve first/second positional semantics without sorting or
        inventing values.
        """

        for evidence in property_evidence:
            if (
                evidence.fact.fact
                != "supported_32_bit_cpu_abis"
            ):
                continue

            values = tuple(
                value.strip()
                for value
                in evidence.fact.value.split(",")
                if value.strip()
            )

            if values:
                observations[
                    "secondary_cpu_abi"
                ].append(
                    AndroidUniverseArchitectureObservation(
                        fact="secondary_cpu_abi",
                        value=values[0],
                        kind=(
                            AndroidUniverseArchitectureObservationKind
                            .PROPERTY_DERIVED
                        ),
                        property_evidence=evidence,
                        property_derivation=(
                            "ordered_32_bit_abi_list:first"
                        ),
                    )
                )

            if len(values) >= 2:
                observations[
                    "secondary_cpu_abi2"
                ].append(
                    AndroidUniverseArchitectureObservation(
                        fact="secondary_cpu_abi2",
                        value=values[1],
                        kind=(
                            AndroidUniverseArchitectureObservationKind
                            .PROPERTY_DERIVED
                        ),
                        property_evidence=evidence,
                        property_derivation=(
                            "ordered_32_bit_abi_list:second"
                        ),
                    )
                )

    @staticmethod
    def _unique_observation_value(
        values: list[
            AndroidUniverseArchitectureObservation
        ],
    ) -> str | None:
        distinct = {
            observation.value
            for observation in values
            if observation.value
        }

        if len(distinct) != 1:
            return None

        return next(
            iter(
                distinct
            )
        )

    @staticmethod
    def _soong_requirements(
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseElfSoongBuildTupleRequirement,
        ...,
    ]:
        return tuple(
            tuple_requirement
            for elf_requirement
            in elf_requirements
            for tuple_requirement
            in (
                elf_requirement
                .soong_build_tuple_requirements
            )
        )

    @staticmethod
    def _append_elf_observation(
        *,
        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ],
        fact: str,
        value: str,
        requirement: (
            AndroidUniverseElfSoongBuildTupleRequirement
        ),
    ) -> None:
        observations[
            fact
        ].append(
            AndroidUniverseArchitectureObservation(
                fact=fact,
                value=value,
                kind=(
                    AndroidUniverseArchitectureObservationKind
                    .ELF_SOONG
                ),
                elf_soong_requirement=requirement,
            )
        )

    def _add_elf_soong_observations(
        self,
        *,
        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ],
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
    ) -> None:
        """
        Reconcile stable Soong tuple dimensions into device architecture facts.

        Rules are deliberately conservative:

        * architecture itself must already be supported by canonical property
          evidence;
        * an architecture variant is accepted directly only when all matching
          Soong tuples agree;
        * if multiple primary variants coexist, runtime CPU-variant evidence
          may select the subset explicitly carrying that same CPU token;
        * a compile-time CPU variant is concluded only when the already-known
          runtime CPU variant is literally present in the matching Soong tuple
          remainder.

        This avoids treating arbitrary remainder tokens as CPU variants.
        """

        tuple_requirements = (
            self._soong_requirements(
                elf_requirements
            )
        )

        primary_architecture = (
            self._unique_observation_value(
                observations[
                    "primary_architecture"
                ]
            )
        )

        secondary_architecture = (
            self._unique_observation_value(
                observations[
                    "secondary_architecture"
                ]
            )
        )

        primary_runtime_variant = (
            self._unique_observation_value(
                observations[
                    "primary_cpu_variant_runtime"
                ]
            )
        )

        secondary_runtime_variant = (
            self._unique_observation_value(
                observations[
                    "secondary_cpu_variant_runtime"
                ]
            )
        )

        def matching(
            architecture: str | None,
        ) -> tuple[
            AndroidUniverseElfSoongBuildTupleRequirement,
            ...,
        ]:
            if architecture is None:
                return ()

            return tuple(
                requirement
                for requirement
                in tuple_requirements
                if (
                    requirement.architecture
                    == architecture
                )
            )

        def add_variant(
            *,
            fact: str,
            architecture: str | None,
            runtime_variant: str | None,
        ) -> str | None:
            requirements = matching(
                architecture
            )

            if not requirements:
                return None

            variants = {
                requirement.arch_variant
                for requirement
                in requirements
                if requirement.arch_variant
            }

            selected = requirements

            if len(variants) != 1:
                if runtime_variant is None:
                    return None

                selected = tuple(
                    requirement
                    for requirement
                    in requirements
                    if runtime_variant
                    in requirement.remainder
                )

                selected_variants = {
                    requirement.arch_variant
                    for requirement
                    in selected
                    if requirement.arch_variant
                }

                if len(selected_variants) != 1:
                    return None

                variants = selected_variants

            value = next(
                iter(
                    variants
                )
            )

            for requirement in selected:
                if (
                    requirement.arch_variant
                    == value
                ):
                    self._append_elf_observation(
                        observations=observations,
                        fact=fact,
                        value=value,
                        requirement=requirement,
                    )

            return value

        primary_arch_variant = add_variant(
            fact="primary_arch_variant",
            architecture=primary_architecture,
            runtime_variant=primary_runtime_variant,
        )

        secondary_arch_variant = add_variant(
            fact="secondary_arch_variant",
            architecture=secondary_architecture,
            runtime_variant=secondary_runtime_variant,
        )

        def add_cpu_variant(
            *,
            fact: str,
            architecture: str | None,
            arch_variant: str | None,
            runtime_variant: str | None,
        ) -> None:
            if (
                architecture is None
                or arch_variant is None
                or runtime_variant is None
            ):
                return

            corroborating = tuple(
                requirement
                for requirement
                in matching(
                    architecture
                )
                if (
                    requirement.arch_variant
                    == arch_variant
                    and runtime_variant
                    in requirement.remainder
                )
            )

            if not corroborating:
                return

            for requirement in corroborating:
                self._append_elf_observation(
                    observations=observations,
                    fact=fact,
                    value=runtime_variant,
                    requirement=requirement,
                )

        add_cpu_variant(
            fact="primary_cpu_variant",
            architecture=primary_architecture,
            arch_variant=primary_arch_variant,
            runtime_variant=primary_runtime_variant,
        )

        add_cpu_variant(
            fact="secondary_cpu_variant",
            architecture=secondary_architecture,
            arch_variant=secondary_arch_variant,
            runtime_variant=secondary_runtime_variant,
        )

    def _add_android_arm_semantic_observations(
        self,
        *,
        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ],
        property_evidence: tuple[
            AndroidUniversePropertyEvidence,
            ...,
        ],
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
    ) -> None:
        """
        Apply generic Android ARM build semantics to already-proven
        canonical secondary-architecture evidence.

        This is not device/platform Knowledge.

        Factory/property evidence must first establish a secondary ARM
        architecture, and parsed ELF evidence must independently prove that
        installed 32-bit ARM objects exist.

        Android's generic ARM build semantics define the application ABI pair
        as armeabi-v7a / armeabi. Android's ARM build configuration also
        defaults an otherwise-unspecified compile-time CPU variant to generic.

        Every conclusion remains attached to the exact canonical property
        evidence that established the secondary architecture.
        """

        secondary_arm_evidence = tuple(
            evidence
            for evidence in property_evidence
            if (
                evidence.fact.fact
                == "secondary_architecture"
                and evidence.fact.value == "arm"
            )
        )

        if not secondary_arm_evidence:
            return

        has_installed_arm_elf = any(
            requirement.android_architecture == "arm"
            and requirement.bitness == 32
            for requirement in elf_requirements
        )

        if not has_installed_arm_elf:
            return

        if not observations[
            "secondary_cpu_abi"
        ]:
            for evidence in secondary_arm_evidence:
                observations[
                    "secondary_cpu_abi"
                ].append(
                    AndroidUniverseArchitectureObservation(
                        fact="secondary_cpu_abi",
                        value="armeabi-v7a",
                        kind=(
                            AndroidUniverseArchitectureObservationKind
                            .PROPERTY_DERIVED
                        ),
                        property_evidence=evidence,
                        property_derivation=(
                            "android_arm_semantics:"
                            "secondary_application_abi:first"
                        ),
                    )
                )

        if not observations[
            "secondary_cpu_abi2"
        ]:
            for evidence in secondary_arm_evidence:
                observations[
                    "secondary_cpu_abi2"
                ].append(
                    AndroidUniverseArchitectureObservation(
                        fact="secondary_cpu_abi2",
                        value="armeabi",
                        kind=(
                            AndroidUniverseArchitectureObservationKind
                            .PROPERTY_DERIVED
                        ),
                        property_evidence=evidence,
                        property_derivation=(
                            "android_arm_semantics:"
                            "secondary_application_abi:second"
                        ),
                    )
                )

        # A concrete compile-time CPU variant always wins. This default is
        # applied only when canonical/ELF reconciliation produced none.
        #
        # Keep this separate from secondary_cpu_variant_runtime:
        # ro.bionic.2nd_cpu_variant may legitimately describe a concrete
        # runtime CPU such as cortex-a53 while the compile-time build variant
        # remains Android's generic default.
        if not observations[
            "secondary_cpu_variant"
        ]:
            for evidence in secondary_arm_evidence:
                observations[
                    "secondary_cpu_variant"
                ].append(
                    AndroidUniverseArchitectureObservation(
                        fact="secondary_cpu_variant",
                        value="generic",
                        kind=(
                            AndroidUniverseArchitectureObservationKind
                            .PROPERTY_DERIVED
                        ),
                        property_evidence=evidence,
                        property_derivation=(
                            "android_arm_semantics:"
                            "missing_cpu_variant_default_generic"
                        ),
                    )
                )

    def _add_knowledge_observations(
        self,
        *,
        observations: dict[
            str,
            list[
                AndroidUniverseArchitectureObservation
            ],
        ],
        knowledge_modules: tuple[
            AndroidKnowledgeModule,
            ...,
        ],
    ) -> None:
        for module in knowledge_modules:
            universe = module.universe

            if universe is None:
                continue

            architecture = universe.architecture

            if architecture is None:
                continue

            for fact in self.FACTS:
                value = getattr(
                    architecture,
                    fact,
                )

                if value is None:
                    continue

                observations[
                    fact
                ].append(
                    AndroidUniverseArchitectureObservation(
                        fact=fact,
                        value=value,
                        kind=(
                            AndroidUniverseArchitectureObservationKind
                            .KNOWLEDGE
                        ),
                        knowledge_module=module,
                    )
                )

    @staticmethod
    def _reconcile_fact(
        *,
        fact: str,
        observations: tuple[
            AndroidUniverseArchitectureObservation,
            ...,
        ],
    ) -> AndroidUniverseArchitectureFactConclusion:
        values = tuple(
            sorted(
                {
                    observation.value
                    for observation
                    in observations
                    if observation.value
                }
            )
        )

        if not values:
            return (
                AndroidUniverseArchitectureFactConclusion(
                    fact=fact,
                    status=(
                        AndroidUniverseArchitectureConclusionStatus
                        .UNRESOLVED
                    ),
                    value=None,
                    observations=observations,
                )
            )

        if len(
            values
        ) == 1:
            return (
                AndroidUniverseArchitectureFactConclusion(
                    fact=fact,
                    status=(
                        AndroidUniverseArchitectureConclusionStatus
                        .AGREED
                    ),
                    value=values[0],
                    observations=observations,
                )
            )

        return (
            AndroidUniverseArchitectureFactConclusion(
                fact=fact,
                status=(
                    AndroidUniverseArchitectureConclusionStatus
                    .CONFLICTING
                ),
                value=None,
                observations=observations,
            )
        )

    @staticmethod
    def _observation_sort_key(
        observation: AndroidUniverseArchitectureObservation,
    ) -> tuple[
        str,
        str,
        str,
        str,
        str,
        str,
    ]:
        property_identity = ""

        if observation.property_evidence is not None:
            property_identity = (
                observation
                .property_evidence
                .model_source
                .android_path
                .as_posix()
            )

        elf_identity = ""
        elf_literal = ""

        if observation.elf_soong_requirement is not None:
            (
                source_name,
                source_path,
            ) = (
                observation
                .elf_soong_requirement
                .source
                .source
                .identity_key
            )

            elf_identity = (
                f"{source_name}:{source_path}"
            )

            elf_literal = (
                observation
                .elf_soong_requirement
                .literal
            )

        return (
            observation.kind.value,
            observation.knowledge_module_id or "",
            property_identity,
            observation.property_derivation or "",
            elf_identity,
            elf_literal + "\0" + observation.value,
        )
