from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.avf import (
    AndroidAvfVmConfigApex,
    AndroidAvfVmConfigCandidateDisposition,
    AndroidAvfVmConfigExtraApk,
    AndroidAvfVmConfigParsingResult,
    ParsedAndroidAvfVmConfig,
)
from treeforge.android.universe.apex import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAvfApexSelection:
    """
    One APEX selection declared literally by an AVF VM configuration.

    ``candidates`` are matched only by the canonical parsed APEX package name.
    Multiple installed candidates remain explicit; no version or provider is
    selected merely from the VM-config declaration.
    """

    source: AndroidAvfVmConfigApex

    candidates: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidAvfVmConfigApex,
        ):
            raise TypeError(
                "source must be an AndroidAvfVmConfigApex"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseApexRequirement,
            )
            for value
            in self.candidates
        ):
            raise TypeError(
                "candidates must contain only "
                "AndroidUniverseApexRequirement values"
            )

        if not all(
            value.apex_name
            == self.source.name
            for value
            in self.candidates
        ):
            raise ValueError(
                "AVF APEX candidate names must exactly match "
                "the declared canonical APEX name"
            )

    @property
    def resolved(
        self,
    ) -> bool:
        return (
            len(
                self.candidates
            )
            == 1
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAvfExtraApkSelection:
    """
    One absolute guest extra-APK selection from the VM configuration.

    Matching uses only exact canonical installed Android paths.
    """

    source: AndroidAvfVmConfigExtraApk

    candidates: tuple[
        AndroidUniverseArtifactRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidAvfVmConfigExtraApk,
        ):
            raise TypeError(
                "source must be an AndroidAvfVmConfigExtraApk"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseArtifactRequirement,
            )
            for value
            in self.candidates
        ):
            raise TypeError(
                "candidates must contain only "
                "AndroidUniverseArtifactRequirement values"
            )

        if not all(
            value.android_path
            == self.source.path
            for value
            in self.candidates
        ):
            raise ValueError(
                "AVF extra-APK candidates must match the "
                "exact declared Android path"
            )

    @property
    def resolved(
        self,
    ) -> bool:
        return (
            len(
                self.candidates
            )
            == 1
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAvfVmConfigRequirement:
    """
    One canonical AVF VM execution configuration.

    The embedded JSON remains owned by the APK container; ``apk_artifact``
    identifies that exact installed container.

    Guest OS/runtime names, task command, APEX selections, and extra APKs
    remain explicit declarations. No runtime implementation is inferred from
    names alone.
    """

    source: ParsedAndroidAvfVmConfig

    apk_artifact: AndroidUniverseArtifactRequirement

    apex_selections: tuple[
        AndroidUniverseAvfApexSelection,
        ...,
    ]

    extra_apk_selections: tuple[
        AndroidUniverseAvfExtraApkSelection,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidAvfVmConfig,
        ):
            raise TypeError(
                "source must be a ParsedAndroidAvfVmConfig"
            )

        if not isinstance(
            self.apk_artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "apk_artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        if (
            self.apk_artifact.inventory_entry.artifact
            is not self.source.source.filesystem_source.artifact
        ):
            raise ValueError(
                "AVF VM configuration must preserve exact "
                "filesystem Artifact identity"
            )

        if (
            self.apk_artifact.android_path
            != self.source.source.apk_android_path.as_posix()
        ):
            raise ValueError(
                "AVF VM configuration must reconcile to the "
                "exact containing APK Android path"
            )

        if (
            len(
                self.apex_selections
            )
            != len(
                self.source.apexes
            )
        ):
            raise ValueError(
                "AVF APEX selections must conserve complete "
                "Parsing declaration population"
            )

        if not all(
            requirement.source
            is parsed
            for requirement, parsed
            in zip(
                self.apex_selections,
                self.source.apexes,
                strict=True,
            )
        ):
            raise ValueError(
                "AVF APEX selections must preserve exact "
                "Parsing identity and order"
            )

        if (
            len(
                self.extra_apk_selections
            )
            != len(
                self.source.extra_apks
            )
        ):
            raise ValueError(
                "AVF extra APK selections must conserve complete "
                "Parsing declaration population"
            )

        if not all(
            requirement.source
            is parsed
            for requirement, parsed
            in zip(
                self.extra_apk_selections,
                self.source.extra_apks,
                strict=True,
            )
        ):
            raise ValueError(
                "AVF extra APK selections must preserve exact "
                "Parsing identity and order"
            )

    @property
    def guest_runtime_name(
        self,
    ) -> str:
        return self.source.os.name

    @property
    def task_type(
        self,
    ) -> str:
        return self.source.task.task_type

    @property
    def task_command(
        self,
    ) -> str:
        return self.source.task.command

    @property
    def core_runtime_key(
        self,
    ) -> tuple:
        """
        Intrinsic execution contract shared by variant configs.

        prefer_staged and extra_apks are intentionally excluded because they
        describe selection/deployment variants of the same core VM runtime.

        Parent APK identity is applied separately by the family interpreter.
        """

        return (
            self.source.version,
            self.source.os.name,
            self.source.task.task_type,
            self.source.task.command,
            tuple(
                value.name
                for value
                in self.source.apexes
            ),
            self.source.export_tombstones,
            self.source.enable_authfs,
            self.source.hugepages,
            self.source.unknown_fields,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAvfVmConfigFamily:
    """
    Cross-config reconciliation within one exact APK container.

    Members share one core guest execution contract and may differ in staged
    preference and extra-APK composition.
    """

    apk_artifact: AndroidUniverseArtifactRequirement

    core_runtime_key: tuple

    members: tuple[
        AndroidUniverseAvfVmConfigRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        if not self.members:
            raise ValueError(
                "AVF VM config family must contain at least one member"
            )

        if not all(
            member.apk_artifact
            is self.apk_artifact
            for member
            in self.members
        ):
            raise ValueError(
                "AVF VM config family members must share the "
                "exact containing APK Artifact"
            )

        if not all(
            member.core_runtime_key
            == self.core_runtime_key
            for member
            in self.members
        ):
            raise ValueError(
                "AVF VM config family members must share one "
                "exact core runtime contract"
            )

    @property
    def guest_runtime_name(
        self,
    ) -> str:
        return self.members[0].guest_runtime_name


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAvfRequirement:
    """
    Complete Device-Universe semantic ownership of AVF VM-config Parsing.

    Candidate dispositions remain available through ``source`` and are
    preserved exactly. Only candidates positively parsed as VM configs become
    executable VM requirements.
    """

    source: AndroidAvfVmConfigParsingResult

    configurations: tuple[
        AndroidUniverseAvfVmConfigRequirement,
        ...,
    ]

    families: tuple[
        AndroidUniverseAvfVmConfigFamily,
        ...,
    ]

    candidate_dispositions: tuple[
        AndroidAvfVmConfigCandidateDisposition,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidAvfVmConfigParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidAvfVmConfigParsingResult"
            )

        if (
            self.candidate_dispositions
            is not self.source.candidates
        ):
            raise ValueError(
                "AVF requirement must preserve exact canonical "
                "candidate-disposition tuple identity"
            )

        if (
            len(
                self.configurations
            )
            != len(
                self.source.configurations
            )
        ):
            raise ValueError(
                "AVF requirement must conserve complete parsed "
                "VM-configuration population"
            )

        if not all(
            requirement.source
            is parsed
            for requirement, parsed
            in zip(
                self.configurations,
                self.source.configurations,
                strict=True,
            )
        ):
            raise ValueError(
                "AVF requirement must preserve exact parsed "
                "configuration identity and order"
            )

        represented = {
            id(member.source)
            for family
            in self.families
            for member
            in family.members
        }

        expected = {
            id(requirement.source)
            for requirement
            in self.configurations
        }

        if represented != expected:
            raise ValueError(
                "AVF config families must cover every parsed "
                "configuration exactly once"
            )

        member_count = sum(
            len(
                family.members
            )
            for family
            in self.families
        )

        if (
            member_count
            != len(
                self.configurations
            )
        ):
            raise ValueError(
                "AVF config family membership must not duplicate "
                "parsed configurations"
            )


def _apk_artifact_for_config(
    source: ParsedAndroidAvfVmConfig,
    *,
    artifact_requirements: (
        AndroidUniverseArtifactRequirementInventory
    ),
) -> AndroidUniverseArtifactRequirement:
    filesystem_source = (
        source.source.filesystem_source
    )

    try:
        inventory_entry = (
            artifact_requirements
            .source_inventory
            .entry_for_artifact(
                filesystem_source.artifact
            )
        )
    except KeyError as error:
        raise ValueError(
            "AVF config containing APK does not preserve "
            "canonical filesystem Artifact identity: "
            f"{source.source.apk_android_path.as_posix()}"
        ) from error

    metadata_path = (
        inventory_entry
        .filesystem_path_for_materialized_path(
            source.source.apk_host_path
        )
    )

    metadata_entry = (
        inventory_entry
        .result
        .metadata
        .get(
            metadata_path
        )
    )

    if metadata_entry is None:
        raise ValueError(
            "AVF containing APK has no exact canonical "
            "filesystem metadata entry: "
            f"{source.source.apk_android_path.as_posix()}"
        )

    matches = tuple(
        requirement
        for requirement
        in artifact_requirements.requirements
        if (
            requirement.inventory_entry
            is inventory_entry
            and requirement.metadata_entry
            is metadata_entry
        )
    )

    if len(matches) != 1:
        raise ValueError(
            "AVF containing APK must reconcile to exactly one "
            "canonical Artifact requirement: "
            f"{source.source.apk_android_path.as_posix()} "
            f"matches={len(matches)}"
        )

    return matches[0]


class AndroidUniverseAvfInterpreter:
    def interpret(
        self,
        parsing: AndroidAvfVmConfigParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> AndroidUniverseAvfRequirement:
        if not isinstance(
            parsing,
            AndroidAvfVmConfigParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidAvfVmConfigParsingResult"
            )

        configurations = []

        for parsed in parsing.configurations:
            apk_artifact = _apk_artifact_for_config(
                parsed,
                artifact_requirements=artifact_requirements,
            )

            apex_selections = tuple(
                AndroidUniverseAvfApexSelection(
                    source=declared,
                    candidates=tuple(
                        requirement
                        for requirement
                        in apex_requirements
                        if (
                            requirement.apex_name
                            == declared.name
                        )
                    ),
                )
                for declared
                in parsed.apexes
            )

            extra_apk_selections = tuple(
                AndroidUniverseAvfExtraApkSelection(
                    source=declared,
                    candidates=tuple(
                        requirement
                        for requirement
                        in artifact_requirements.requirements
                        if (
                            requirement.android_path
                            == declared.path
                        )
                    ),
                )
                for declared
                in parsed.extra_apks
            )

            configurations.append(
                AndroidUniverseAvfVmConfigRequirement(
                    source=parsed,
                    apk_artifact=apk_artifact,
                    apex_selections=apex_selections,
                    extra_apk_selections=extra_apk_selections,
                )
            )

        configurations = tuple(
            configurations
        )

        grouped = {}

        for requirement in configurations:
            key = (
                id(
                    requirement.apk_artifact
                ),
                requirement.core_runtime_key,
            )

            grouped.setdefault(
                key,
                [],
            ).append(
                requirement
            )

        families = tuple(
            AndroidUniverseAvfVmConfigFamily(
                apk_artifact=members[0].apk_artifact,
                core_runtime_key=(
                    members[0].core_runtime_key
                ),
                members=tuple(
                    sorted(
                        members,
                        key=lambda value: (
                            value.source.source.identity_key
                        ),
                    )
                ),
            )
            for _, members
            in sorted(
                grouped.items(),
                key=lambda item: (
                    item[1][0]
                    .source
                    .source
                    .identity_key
                ),
            )
        )

        return AndroidUniverseAvfRequirement(
            source=parsing,
            configurations=configurations,
            families=families,
            candidate_dispositions=parsing.candidates,
        )
