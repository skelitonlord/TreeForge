from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)
from treeforge.android.knowledge.stages import (
    AndroidExtractionKnowledge,
    AndroidFilesystemMetadataKnowledge,
    AndroidParsingKnowledge,
    AndroidPartitionLayoutKnowledge,
)
from treeforge.android.knowledge.universe import (
    AndroidUniverseKnowledge,
)


class AndroidKnowledgeScope(
    StrEnum,
):
    """
    Ownership scope for one TreeForge Android knowledge module.
    """

    OEM = "oem"
    PLATFORM = "platform"
    DEVICE = "device"


class AndroidKnowledgeCapability(
    StrEnum,
):
    """
    Capability supplied by one knowledge module.

    Additional capabilities such as kernel, SEPolicy, build configuration,
    boot reconstruction, or hardware knowledge may be added later without
    changing registry/resolution semantics.
    """

    DISCOVERY_SEMANTICS = (
        "discovery_semantics"
    )

    PARTITION_LAYOUT = "partition_layout"
    EXTRACTION = "extraction"
    FILESYSTEM_METADATA = "filesystem_metadata"
    PARSING = "parsing"
    UNIVERSE = "universe"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidKnowledgeModule:
    """
    Immutable installed TreeForge knowledge module.

    Modules form an explicit dependency graph.

    Dependencies identify broader knowledge that must be loaded before this
    module. For example:

        device:tangorpro
            -> platform:gs201
            -> oem:google

    A module may expose zero or more capabilities.

    Discovery semantic rules operate only after raw Discovery and therefore
    cannot control whether artifacts are discovered.
    """

    module_id: str

    scope: AndroidKnowledgeScope

    dependencies: tuple[
        str,
        ...,
    ] = ()

    capabilities: tuple[
        AndroidKnowledgeCapability,
        ...,
    ] = ()

    discovery_semantic_rules: tuple[
        ProviderArtifactSemanticRule,
        ...,
    ] = ()

    partition_layout: (
        AndroidPartitionLayoutKnowledge
        | None
    ) = None

    extraction: (
        AndroidExtractionKnowledge
        | None
    ) = None

    filesystem_metadata: (
        AndroidFilesystemMetadataKnowledge
        | None
    ) = None

    parsing: (
        AndroidParsingKnowledge
        | None
    ) = None

    universe: AndroidUniverseKnowledge | None = None

    def __post_init__(
        self,
    ) -> None:
        self._validate_string(
            self.module_id,
            field_name="module_id",
        )

        if not isinstance(
            self.scope,
            AndroidKnowledgeScope,
        ):
            raise TypeError(
                "scope must be an "
                "AndroidKnowledgeScope"
            )

        if not isinstance(
            self.dependencies,
            tuple,
        ):
            raise TypeError(
                "dependencies must be a tuple"
            )

        for dependency in self.dependencies:
            self._validate_string(
                dependency,
                field_name="dependency",
            )

        if (
            len(self.dependencies)
            != len(
                set(
                    self.dependencies
                )
            )
        ):
            raise ValueError(
                "dependencies must not contain "
                "duplicates"
            )

        if self.module_id in self.dependencies:
            raise ValueError(
                "module must not depend on itself"
            )

        if not isinstance(
            self.capabilities,
            tuple,
        ):
            raise TypeError(
                "capabilities must be a tuple"
            )

        for capability in self.capabilities:
            if not isinstance(
                capability,
                AndroidKnowledgeCapability,
            ):
                raise TypeError(
                    "capabilities must contain "
                    "AndroidKnowledgeCapability "
                    "instances"
                )

        if (
            len(self.capabilities)
            != len(
                set(
                    self.capabilities
                )
            )
        ):
            raise ValueError(
                "capabilities must not contain "
                "duplicates"
            )

        if not isinstance(
            self.discovery_semantic_rules,
            tuple,
        ):
            raise TypeError(
                "discovery_semantic_rules must "
                "be a tuple"
            )

        for rule in (
            self.discovery_semantic_rules
        ):
            if not isinstance(
                rule,
                ProviderArtifactSemanticRule,
            ):
                raise TypeError(
                    "discovery_semantic_rules must "
                    "contain "
                    "ProviderArtifactSemanticRule "
                    "instances"
                )

        rule_ids = tuple(
            rule.rule_id
            for rule in self.discovery_semantic_rules
        )

        if (
            len(rule_ids)
            != len(
                set(
                    rule_ids
                )
            )
        ):
            raise ValueError(
                "discovery semantic rules must "
                "not contain duplicate rule IDs"
            )

        has_discovery_rules = bool(
            self.discovery_semantic_rules
        )

        declares_discovery = (
            AndroidKnowledgeCapability
            .DISCOVERY_SEMANTICS
            in self.capabilities
        )

        if (
            has_discovery_rules
            and not declares_discovery
        ):
            raise ValueError(
                "modules with discovery semantic "
                "rules must declare the "
                "DISCOVERY_SEMANTICS capability"
            )

        stage_payloads = (
            (
                AndroidKnowledgeCapability.PARTITION_LAYOUT,
                "partition_layout",
                self.partition_layout,
                AndroidPartitionLayoutKnowledge,
            ),
            (
                AndroidKnowledgeCapability.EXTRACTION,
                "extraction",
                self.extraction,
                AndroidExtractionKnowledge,
            ),
            (
                AndroidKnowledgeCapability.FILESYSTEM_METADATA,
                "filesystem_metadata",
                self.filesystem_metadata,
                AndroidFilesystemMetadataKnowledge,
            ),
            (
                AndroidKnowledgeCapability.PARSING,
                "parsing",
                self.parsing,
                AndroidParsingKnowledge,
            ),
            (
                AndroidKnowledgeCapability.UNIVERSE,
                "universe",
                self.universe,
                AndroidUniverseKnowledge,
            ),
        )

        for (
            capability,
            field_name,
            payload,
            payload_type,
        ) in stage_payloads:
            declares_capability = (
                capability
                in self.capabilities
            )

            if (
                payload is not None
                and not isinstance(
                    payload,
                    payload_type,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a "
                    f"{payload_type.__name__} or None"
                )

            if (
                payload is not None
                and not declares_capability
            ):
                raise ValueError(
                    f"modules with {field_name} knowledge "
                    f"must declare the "
                    f"{capability.name} capability"
                )

            if (
                declares_capability
                and payload is None
            ):
                raise ValueError(
                    f"modules declaring {capability.name} "
                    f"must provide {field_name} knowledge"
                )

    def supports(
        self,
        capability: AndroidKnowledgeCapability,
    ) -> bool:
        if not isinstance(
            capability,
            AndroidKnowledgeCapability,
        ):
            raise TypeError(
                "capability must be an "
                "AndroidKnowledgeCapability"
            )

        return (
            capability
            in self.capabilities
        )

    @staticmethod
    def _validate_string(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )