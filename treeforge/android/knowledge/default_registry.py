from __future__ import annotations

from treeforge.android.knowledge.model import (
    AndroidKnowledgeCapability,
    AndroidKnowledgeModule,
    AndroidKnowledgeScope,
)
from treeforge.android.knowledge.registry import (
    AndroidKnowledgeRegistry,
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


GOOGLE_KNOWLEDGE = (
    AndroidKnowledgeModule(
        module_id="oem:google",
        scope=AndroidKnowledgeScope.OEM,
        capabilities=(
            AndroidKnowledgeCapability
            .DISCOVERY_SEMANTICS,
        ),
        discovery_semantic_rules=(
            GoogleFactoryArtifactSemanticRule(),
        ),
    )
)


GS201_KNOWLEDGE = (
    AndroidKnowledgeModule(
        module_id="platform:gs201",
        scope=AndroidKnowledgeScope.PLATFORM,
        dependencies=(
            "oem:google",
        ),
        capabilities=(
            AndroidKnowledgeCapability
            .DISCOVERY_SEMANTICS,
        ),
        discovery_semantic_rules=(
            Gs201ArtifactSemanticRule(),
        ),
    )
)


TANGORPRO_KNOWLEDGE = (
    AndroidKnowledgeModule(
        module_id="device:tangorpro",
        scope=AndroidKnowledgeScope.DEVICE,
        dependencies=(
            "platform:gs201",
        ),
        capabilities=(
            AndroidKnowledgeCapability
            .DISCOVERY_SEMANTICS,
        ),
        discovery_semantic_rules=(
            TangorproArtifactSemanticRule(),
        ),
    )
)




DEFAULT_ANDROID_KNOWLEDGE_REGISTRY = (
    AndroidKnowledgeRegistry(
        modules=(
            GOOGLE_KNOWLEDGE,
            GS201_KNOWLEDGE,
            TANGORPRO_KNOWLEDGE,
        )
    )
)
