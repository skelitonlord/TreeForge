from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.structured_configuration import (
    AndroidStructuredConfigurationParsingResult,
    ParsedAndroidAvbPublicKey,
    ParsedAndroidBlueprint,
    ParsedAndroidCgroupConfiguration,
    ParsedAndroidMke2fsConfiguration,
    ParsedAndroidRecoveryWipeConfiguration,
    ParsedAndroidSensorHalConfiguration,
    ParsedAndroidSensorRegistryConfiguration,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


class AndroidUniverseStructuredConfigurationRole(StrEnum):
    AVB_PUBLIC_KEY = "avb_public_key"
    PROCESS_RESOURCE_CONTROL = "process_resource_control"
    FILESYSTEM_CONSTRUCTION = "filesystem_construction"
    RECOVERY_WIPE_POLICY = "recovery_wipe_policy"
    BUILD_DEFINITION = "build_definition"
    SENSOR_HAL_COMPOSITION = "sensor_hal_composition"
    SENSOR_REGISTRY = "sensor_registry"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAvbPublicKeyRequirement:
    source: ParsedAndroidAvbPublicKey
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .AVB_PUBLIC_KEY
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCgroupConfigurationRequirement:
    source: ParsedAndroidCgroupConfiguration
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .PROCESS_RESOURCE_CONTROL
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseMke2fsConfigurationRequirement:
    source: ParsedAndroidMke2fsConfiguration
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .FILESYSTEM_CONSTRUCTION
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRecoveryWipeConfigurationRequirement:
    source: ParsedAndroidRecoveryWipeConfiguration
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .RECOVERY_WIPE_POLICY
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBlueprintRequirement:
    source: ParsedAndroidBlueprint
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .BUILD_DEFINITION
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSensorHalConfigurationRequirement:
    source: ParsedAndroidSensorHalConfiguration
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .SENSOR_HAL_COMPOSITION
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSensorRegistryConfigurationRequirement:
    source: ParsedAndroidSensorRegistryConfiguration
    artifact: AndroidUniverseArtifactRequirement

    @property
    def role(
        self,
    ) -> AndroidUniverseStructuredConfigurationRole:
        return (
            AndroidUniverseStructuredConfigurationRole
            .SENSOR_REGISTRY
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseStructuredConfigurationRequirement:
    """
    Device-level semantic decomposition of the canonical Parsing
    structured-configuration population.

    Each family remains independently typed so later stages can assign
    Reconstruction Ownership and Planning decisions without rediscovering
    configuration kind from filenames or paths.
    """

    source: AndroidStructuredConfigurationParsingResult

    avb_public_keys: tuple[
        AndroidUniverseAvbPublicKeyRequirement,
        ...,
    ]

    cgroup_configurations: tuple[
        AndroidUniverseCgroupConfigurationRequirement,
        ...,
    ]

    mke2fs_configurations: tuple[
        AndroidUniverseMke2fsConfigurationRequirement,
        ...,
    ]

    recovery_wipe_configurations: tuple[
        AndroidUniverseRecoveryWipeConfigurationRequirement,
        ...,
    ]

    blueprints: tuple[
        AndroidUniverseBlueprintRequirement,
        ...,
    ]

    sensor_hal_configurations: tuple[
        AndroidUniverseSensorHalConfigurationRequirement,
        ...,
    ]

    sensor_registry_configurations: tuple[
        AndroidUniverseSensorRegistryConfigurationRequirement,
        ...,
    ]

    def __post_init__(self) -> None:
        groups = (
            (
                self.avb_public_keys,
                self.source.avb_public_keys,
                "AVB public keys",
            ),
            (
                self.cgroup_configurations,
                self.source.cgroup_configurations,
                "cgroup configurations",
            ),
            (
                self.mke2fs_configurations,
                self.source.mke2fs_configurations,
                "mke2fs configurations",
            ),
            (
                self.recovery_wipe_configurations,
                self.source.recovery_wipe_configurations,
                "recovery wipe configurations",
            ),
            (
                self.blueprints,
                self.source.blueprints,
                "Blueprint configurations",
            ),
            (
                self.sensor_hal_configurations,
                self.source.sensor_hal_configurations,
                "sensor HAL configurations",
            ),
            (
                self.sensor_registry_configurations,
                self.source.sensor_registry_configurations,
                "sensor registry configurations",
            ),
        )

        for requirements, parsed_values, label in groups:
            if len(requirements) != len(parsed_values):
                raise ValueError(
                    f"{label} must conserve complete Parsing population"
                )

            if not all(
                requirement.source is parsed
                for requirement, parsed
                in zip(
                    requirements,
                    parsed_values,
                    strict=True,
                )
            ):
                raise ValueError(
                    f"{label} must preserve exact Parsing identity and order"
                )


def _artifact_for_source(
    parsed,
    *,
    artifact_requirements: (
        AndroidUniverseArtifactRequirementInventory
    ),
) -> AndroidUniverseArtifactRequirement:
    source = parsed.source
    filesystem_source = source.filesystem_source

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
            "structured configuration source does not preserve "
            "canonical filesystem artifact identity: "
            f"{source.source_name}:"
            f"{source.android_path.as_posix()}"
        ) from error

    if (
        inventory_entry.artifact
        is not filesystem_source.artifact
    ):
        raise ValueError(
            "structured configuration filesystem lookup must "
            "preserve exact Extraction artifact identity"
        )

    metadata_path = (
        inventory_entry
        .filesystem_path_for_materialized_path(
            source.host_path
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
            "structured configuration source has no canonical "
            "filesystem metadata entry: "
            f"{source.source_name}:"
            f"{source.android_path.as_posix()}"
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
            "structured configuration source must reconcile "
            "to exactly one canonical Artifact requirement: "
            f"{source.source_name}:"
            f"{source.android_path.as_posix()} "
            f"matches={len(matches)}"
        )

    return matches[0]


class AndroidUniverseStructuredConfigurationInterpreter:
    def interpret(
        self,
        parsing: AndroidStructuredConfigurationParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseStructuredConfigurationRequirement:
        return AndroidUniverseStructuredConfigurationRequirement(
            source=parsing,

            avb_public_keys=tuple(
                AndroidUniverseAvbPublicKeyRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.avb_public_keys
            ),

            cgroup_configurations=tuple(
                AndroidUniverseCgroupConfigurationRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.cgroup_configurations
            ),

            mke2fs_configurations=tuple(
                AndroidUniverseMke2fsConfigurationRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.mke2fs_configurations
            ),

            recovery_wipe_configurations=tuple(
                AndroidUniverseRecoveryWipeConfigurationRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.recovery_wipe_configurations
            ),

            blueprints=tuple(
                AndroidUniverseBlueprintRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.blueprints
            ),

            sensor_hal_configurations=tuple(
                AndroidUniverseSensorHalConfigurationRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.sensor_hal_configurations
            ),

            sensor_registry_configurations=tuple(
                AndroidUniverseSensorRegistryConfigurationRequirement(
                    source=value,
                    artifact=_artifact_for_source(
                        value,
                        artifact_requirements=artifact_requirements,
                    ),
                )
                for value in parsing.sensor_registry_configurations
            ),
        )
