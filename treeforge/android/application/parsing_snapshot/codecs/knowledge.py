from __future__ import annotations

from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.discovery.identity import (
    AndroidIdentityEvidence,
    AndroidIdentityInferenceResult,
    AndroidIdentityKind,
)
from treeforge.android.knowledge.model import (
    AndroidKnowledgeCapability,
    AndroidKnowledgeModule,
    AndroidKnowledgeScope,
)
from treeforge.android.knowledge.profile import (
    ResolvedAndroidKnowledgeProfile,
)
from treeforge.android.knowledge.resolution_result import (
    AndroidKnowledgeResolutionResult,
)
from treeforge.android.knowledge.rules.google_factory import (
    GoogleFactoryArtifactSemanticRule,
)
from treeforge.android.knowledge.rules.gs201 import (
    Gs201ArtifactSemanticRule,
)
from treeforge.android.knowledge.rules.tangorpro import (
    TangorproArtifactSemanticRule,
)
from treeforge.android.knowledge.selection import (
    AndroidKnowledgeRootSelection,
    AndroidKnowledgeSelection,
    AndroidKnowledgeSelectionSource,
)
from treeforge.android.knowledge.stages import (
    AndroidExtractionKnowledge,
    AndroidFilesystemMetadataKnowledge,
    AndroidParsingKnowledge,
    AndroidPartitionLayoutKnowledge,
)
from treeforge.android.knowledge.universe import (
    AndroidUniverseArchitectureKnowledge,
    AndroidUniverseKnowledge,
    AndroidUniverseVintfSelectionKnowledge,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)
from treeforge.android.parsing.snapshot.model import (
    AndroidParsingSnapshot,
)
from treeforge.android.partition.layout import (
    PartitionLayout,
)
from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)
from treeforge.android.providers.generic_android_semantic_rule import (
    GenericAndroidArtifactSemanticRule,
)


def _optional_ref(
    encoder: SnapshotGraphEncoder,
    value: object | None,
) -> dict[str, str] | None:
    if value is None:
        return None

    return encoder.ref(
        value
    )


def _decode_optional_ref(
    decoder: SnapshotGraphDecoder,
    value: object,
) -> object | None:
    if value is None:
        return None

    return decoder.ref(
        value
    )


def _refs(
    encoder: SnapshotGraphEncoder,
    values: tuple[object, ...],
) -> list[dict[str, str]]:
    return [
        encoder.ref(
            value
        )
        for value in values
    ]


def _decode_refs(
    decoder: SnapshotGraphDecoder,
    values: object,
) -> tuple[object, ...]:
    if not isinstance(
        values,
        list,
    ):
        raise TypeError(
            "checkpoint references must be a list"
        )

    return tuple(
        decoder.ref(
            value
        )
        for value in values
    )


# ---------------------------------------------------------------------------
# Semantic rules
# ---------------------------------------------------------------------------


class _SemanticRuleCodec:
    def __init__(
        self,
        *,
        python_type: type[
            ProviderArtifactSemanticRule
        ],
        type_tag: str,
    ) -> None:
        self.python_type = python_type
        self.type_tag = type_tag

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            self.python_type,
        ):
            raise TypeError(
                "value has the wrong semantic-rule type"
            )

        return {
            "rule_id": value.rule_id,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return self.python_type(
            rule_id=payload[
                "rule_id"
            ],
        )


GENERIC_ANDROID_RULE_CODEC = _SemanticRuleCodec(
    python_type=GenericAndroidArtifactSemanticRule,
    type_tag="android.knowledge.rule.generic_android",
)

GOOGLE_FACTORY_RULE_CODEC = _SemanticRuleCodec(
    python_type=GoogleFactoryArtifactSemanticRule,
    type_tag="android.knowledge.rule.google_factory",
)

GS201_RULE_CODEC = _SemanticRuleCodec(
    python_type=Gs201ArtifactSemanticRule,
    type_tag="android.knowledge.rule.gs201",
)

TANGORPRO_RULE_CODEC = _SemanticRuleCodec(
    python_type=TangorproArtifactSemanticRule,
    type_tag="android.knowledge.rule.tangorpro",
)


# ---------------------------------------------------------------------------
# Discovery identity + selections
# ---------------------------------------------------------------------------


class AndroidKnowledgeSelectionCodec:
    type_tag = "android.knowledge.selection"
    python_type = AndroidKnowledgeSelection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidKnowledgeSelection,
        ):
            raise TypeError(
                "value must be an AndroidKnowledgeSelection"
            )

        return {
            "device_id": value.device_id,
            "board_platform": value.board_platform,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidKnowledgeSelection(
            device_id=payload.get(
                "device_id"
            ),
            board_platform=payload.get(
                "board_platform"
            ),
        )


class AndroidKnowledgeRootSelectionCodec:
    type_tag = "android.knowledge.root_selection"
    python_type = AndroidKnowledgeRootSelection

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidKnowledgeRootSelection,
        ):
            raise TypeError(
                "value must be an "
                "AndroidKnowledgeRootSelection"
            )

        return {
            "module_id": value.module_id,
            "source": value.source.value,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidKnowledgeRootSelection(
            module_id=payload[
                "module_id"
            ],
            source=AndroidKnowledgeSelectionSource(
                payload[
                    "source"
                ]
            ),
        )


class AndroidIdentityInferenceResultCodec:
    type_tag = "android.discovery.identity_inference"
    python_type = AndroidIdentityInferenceResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidIdentityInferenceResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidIdentityInferenceResult"
            )

        return {
            "device_id": value.device_id,
            "board_platform": value.board_platform,
            "android_version": value.android_version,
            "evidence": [
                {
                    "kind": item.kind.value,
                    "value": item.value,
                    "source": item.source,
                    "detail": item.detail,
                }
                for item in value.evidence
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        evidence = payload.get(
            "evidence",
            [],
        )

        if not isinstance(
            evidence,
            list,
        ):
            raise TypeError(
                "identity evidence must be a list"
            )

        return AndroidIdentityInferenceResult(
            device_id=payload.get(
                "device_id"
            ),
            board_platform=payload.get(
                "board_platform"
            ),
            android_version=payload.get(
                "android_version"
            ),
            evidence=tuple(
                AndroidIdentityEvidence(
                    kind=AndroidIdentityKind(
                        item[
                            "kind"
                        ]
                    ),
                    value=item[
                        "value"
                    ],
                    source=item[
                        "source"
                    ],
                    detail=item[
                        "detail"
                    ],
                )
                for item in evidence
            ),
        )


# ---------------------------------------------------------------------------
# Stage knowledge
# ---------------------------------------------------------------------------


class _EmptyKnowledgeCodec:
    def __init__(
        self,
        *,
        python_type: type,
        type_tag: str,
    ) -> None:
        self.python_type = python_type
        self.type_tag = type_tag

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            self.python_type,
        ):
            raise TypeError(
                "value has the wrong knowledge payload type"
            )

        return {}

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        if payload:
            raise ValueError(
                "empty knowledge payload must have no fields"
            )

        return self.python_type()


PARTITION_LAYOUT_KNOWLEDGE_CODEC = _EmptyKnowledgeCodec(
    python_type=AndroidPartitionLayoutKnowledge,
    type_tag="android.knowledge.partition_layout",
)

EXTRACTION_KNOWLEDGE_CODEC = _EmptyKnowledgeCodec(
    python_type=AndroidExtractionKnowledge,
    type_tag="android.knowledge.extraction",
)

FILESYSTEM_METADATA_KNOWLEDGE_CODEC = _EmptyKnowledgeCodec(
    python_type=AndroidFilesystemMetadataKnowledge,
    type_tag="android.knowledge.filesystem_metadata",
)

PARSING_KNOWLEDGE_CODEC = _EmptyKnowledgeCodec(
    python_type=AndroidParsingKnowledge,
    type_tag="android.knowledge.parsing",
)


class AndroidUniverseArchitectureKnowledgeCodec:
    type_tag = "android.knowledge.universe.architecture"
    python_type = AndroidUniverseArchitectureKnowledge

    _FIELDS = (
        "board_platform",
        "primary_architecture",
        "primary_arch_variant",
        "primary_cpu_abi",
        "primary_cpu_variant",
        "primary_cpu_variant_runtime",
        "secondary_architecture",
        "secondary_arch_variant",
        "secondary_cpu_abi",
        "secondary_cpu_abi2",
        "secondary_cpu_variant",
        "secondary_cpu_variant_runtime",
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidUniverseArchitectureKnowledge,
        ):
            raise TypeError(
                "value must be an "
                "AndroidUniverseArchitectureKnowledge"
            )

        return {
            field_name: getattr(
                value,
                field_name,
            )
            for field_name in self._FIELDS
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidUniverseArchitectureKnowledge(
            **{
                field_name: payload.get(
                    field_name
                )
                for field_name in self._FIELDS
            }
        )


class AndroidUniverseVintfSelectionKnowledgeCodec:
    type_tag = "android.knowledge.universe.vintf_selection"
    python_type = AndroidUniverseVintfSelectionKnowledge

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidUniverseVintfSelectionKnowledge,
        ):
            raise TypeError(
                "value must be an "
                "AndroidUniverseVintfSelectionKnowledge"
            )

        return {
            "source_path": value.source_path,
            "role": value.role,
            "selector_key": value.selector_key,
            "selector_value": value.selector_value,
            "alternative_group": value.alternative_group,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidUniverseVintfSelectionKnowledge(
            source_path=payload[
                "source_path"
            ],
            role=payload[
                "role"
            ],
            selector_key=payload.get(
                "selector_key"
            ),
            selector_value=payload.get(
                "selector_value"
            ),
            alternative_group=payload.get(
                "alternative_group"
            ),
        )


class AndroidUniverseKnowledgeCodec:
    type_tag = "android.knowledge.universe"
    python_type = AndroidUniverseKnowledge

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidUniverseKnowledge,
        ):
            raise TypeError(
                "value must be an AndroidUniverseKnowledge"
            )

        return {
            "architecture": _optional_ref(
                encoder,
                value.architecture,
            ),
            "vintf_selections": _refs(
                encoder,
                value.vintf_selections,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        architecture = _decode_optional_ref(
            decoder,
            payload.get(
                "architecture"
            ),
        )

        if (
            architecture is not None
            and not isinstance(
                architecture,
                AndroidUniverseArchitectureKnowledge,
            )
        ):
            raise TypeError(
                "restored architecture knowledge has wrong type"
            )

        selections = _decode_refs(
            decoder,
            payload.get(
                "vintf_selections",
                [],
            ),
        )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfSelectionKnowledge,
            )
            for item in selections
        ):
            raise TypeError(
                "restored VINTF selections have wrong type"
            )

        return AndroidUniverseKnowledge(
            architecture=architecture,
            vintf_selections=selections,
        )


# ---------------------------------------------------------------------------
# Module / profile / resolution / root
# ---------------------------------------------------------------------------


class AndroidKnowledgeModuleCodec:
    type_tag = "android.knowledge.module"
    python_type = AndroidKnowledgeModule

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidKnowledgeModule,
        ):
            raise TypeError(
                "value must be an AndroidKnowledgeModule"
            )

        return {
            "module_id": value.module_id,
            "scope": value.scope.value,
            "dependencies": list(
                value.dependencies
            ),
            "capabilities": [
                item.value
                for item in value.capabilities
            ],
            "discovery_semantic_rules": _refs(
                encoder,
                value.discovery_semantic_rules,
            ),
            "partition_layout": _optional_ref(
                encoder,
                value.partition_layout,
            ),
            "extraction": _optional_ref(
                encoder,
                value.extraction,
            ),
            "filesystem_metadata": _optional_ref(
                encoder,
                value.filesystem_metadata,
            ),
            "parsing": _optional_ref(
                encoder,
                value.parsing,
            ),
            "universe": _optional_ref(
                encoder,
                value.universe,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        rules = _decode_refs(
            decoder,
            payload.get(
                "discovery_semantic_rules",
                [],
            ),
        )

        if not all(
            isinstance(
                rule,
                ProviderArtifactSemanticRule,
            )
            for rule in rules
        ):
            raise TypeError(
                "restored semantic rules have wrong type"
            )

        return AndroidKnowledgeModule(
            module_id=payload[
                "module_id"
            ],
            scope=AndroidKnowledgeScope(
                payload[
                    "scope"
                ]
            ),
            dependencies=tuple(
                payload.get(
                    "dependencies",
                    [],
                )
            ),
            capabilities=tuple(
                AndroidKnowledgeCapability(
                    item
                )
                for item in payload.get(
                    "capabilities",
                    [],
                )
            ),
            discovery_semantic_rules=rules,
            partition_layout=_decode_optional_ref(
                decoder,
                payload.get(
                    "partition_layout"
                ),
            ),
            extraction=_decode_optional_ref(
                decoder,
                payload.get(
                    "extraction"
                ),
            ),
            filesystem_metadata=_decode_optional_ref(
                decoder,
                payload.get(
                    "filesystem_metadata"
                ),
            ),
            parsing=_decode_optional_ref(
                decoder,
                payload.get(
                    "parsing"
                ),
            ),
            universe=_decode_optional_ref(
                decoder,
                payload.get(
                    "universe"
                ),
            ),
        )


class ResolvedAndroidKnowledgeProfileCodec:
    type_tag = "android.knowledge.resolved_profile"
    python_type = ResolvedAndroidKnowledgeProfile

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ResolvedAndroidKnowledgeProfile,
        ):
            raise TypeError(
                "value must be a "
                "ResolvedAndroidKnowledgeProfile"
            )

        return {
            "root_selections": _refs(
                encoder,
                value.root_selections,
            ),
            "modules": _refs(
                encoder,
                value.modules,
            ),
            "discovery_semantic_rules": _refs(
                encoder,
                value.discovery_semantic_rules,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        roots = _decode_refs(
            decoder,
            payload.get(
                "root_selections",
                [],
            ),
        )

        modules = _decode_refs(
            decoder,
            payload.get(
                "modules",
                [],
            ),
        )

        rules = _decode_refs(
            decoder,
            payload.get(
                "discovery_semantic_rules",
                [],
            ),
        )

        if not all(
            isinstance(
                item,
                AndroidKnowledgeRootSelection,
            )
            for item in roots
        ):
            raise TypeError(
                "restored profile roots have wrong type"
            )

        if not all(
            isinstance(
                item,
                AndroidKnowledgeModule,
            )
            for item in modules
        ):
            raise TypeError(
                "restored profile modules have wrong type"
            )

        if not all(
            isinstance(
                item,
                ProviderArtifactSemanticRule,
            )
            for item in rules
        ):
            raise TypeError(
                "restored profile rules have wrong type"
            )

        return ResolvedAndroidKnowledgeProfile(
            root_selections=roots,
            modules=modules,
            discovery_semantic_rules=rules,
        )


class AndroidKnowledgeResolutionResultCodec:
    type_tag = "android.knowledge.resolution_result"
    python_type = AndroidKnowledgeResolutionResult

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidKnowledgeResolutionResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidKnowledgeResolutionResult"
            )

        return {
            "explicit_selection": encoder.ref(
                value.explicit_selection
            ),
            "inferred_identity": encoder.ref(
                value.inferred_identity
            ),
            "root_selections": _refs(
                encoder,
                value.root_selections,
            ),
            "profile": encoder.ref(
                value.profile
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        explicit_selection = decoder.ref(
            payload[
                "explicit_selection"
            ]
        )

        inferred_identity = decoder.ref(
            payload[
                "inferred_identity"
            ]
        )

        root_selections = _decode_refs(
            decoder,
            payload[
                "root_selections"
            ],
        )

        profile = decoder.ref(
            payload[
                "profile"
            ]
        )

        if not isinstance(
            explicit_selection,
            AndroidKnowledgeSelection,
        ):
            raise TypeError(
                "restored explicit selection has wrong type"
            )

        if not isinstance(
            inferred_identity,
            AndroidIdentityInferenceResult,
        ):
            raise TypeError(
                "restored inferred identity has wrong type"
            )

        if not isinstance(
            profile,
            ResolvedAndroidKnowledgeProfile,
        ):
            raise TypeError(
                "restored knowledge profile has wrong type"
            )

        return AndroidKnowledgeResolutionResult(
            explicit_selection=explicit_selection,
            inferred_identity=inferred_identity,
            root_selections=root_selections,
            profile=profile,
        )


class AndroidParsingSnapshotCodec:
    type_tag = "android.parsing_snapshot"
    python_type = AndroidParsingSnapshot

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidParsingSnapshot,
        ):
            raise TypeError(
                "value must be an AndroidParsingSnapshot"
            )

        return {
            "partition_layout": encoder.ref(
                value.partition_layout
            ),
            "parsing": encoder.ref(
                value.parsing
            ),
            "knowledge_resolution": _optional_ref(
                encoder,
                value.knowledge_resolution,
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        partition_layout = decoder.ref(
            payload[
                "partition_layout"
            ]
        )

        parsing = decoder.ref(
            payload[
                "parsing"
            ]
        )

        knowledge_resolution = _decode_optional_ref(
            decoder,
            payload.get(
                "knowledge_resolution"
            ),
        )

        if not isinstance(
            partition_layout,
            PartitionLayout,
        ):
            raise TypeError(
                "restored partition_layout must "
                "be a PartitionLayout"
            )

        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "restored parsing must be an AndroidParsingResult"
            )

        if (
            knowledge_resolution is not None
            and not isinstance(
                knowledge_resolution,
                AndroidKnowledgeResolutionResult,
            )
        ):
            raise TypeError(
                "restored knowledge resolution has wrong type"
            )

        return AndroidParsingSnapshot(
            partition_layout=partition_layout,
            parsing=parsing,
            knowledge_resolution=knowledge_resolution,
        )


KNOWLEDGE_CODECS = (
    GENERIC_ANDROID_RULE_CODEC,
    GOOGLE_FACTORY_RULE_CODEC,
    GS201_RULE_CODEC,
    TANGORPRO_RULE_CODEC,
    AndroidKnowledgeSelectionCodec(),
    AndroidKnowledgeRootSelectionCodec(),
    AndroidIdentityInferenceResultCodec(),
    PARTITION_LAYOUT_KNOWLEDGE_CODEC,
    EXTRACTION_KNOWLEDGE_CODEC,
    FILESYSTEM_METADATA_KNOWLEDGE_CODEC,
    PARSING_KNOWLEDGE_CODEC,
    AndroidUniverseArchitectureKnowledgeCodec(),
    AndroidUniverseVintfSelectionKnowledgeCodec(),
    AndroidUniverseKnowledgeCodec(),
    AndroidKnowledgeModuleCodec(),
    ResolvedAndroidKnowledgeProfileCodec(),
    AndroidKnowledgeResolutionResultCodec(),
    AndroidParsingSnapshotCodec(),
)
