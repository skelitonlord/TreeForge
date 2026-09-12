from __future__ import annotations

from typing import TYPE_CHECKING

from treeforge.android.providers.base import (
    Provider,
    ProviderCapability,
)
from treeforge.android.providers.collection import (
    ProviderCollection,
)
from treeforge.android.providers.result import (
    ProviderResult,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.android.providers.source_identity import (
    ProviderSourceFilesystemProvenance,
    ProviderSourceIdentity,
)

from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
    ProviderArtifactKind,
    ProviderArtifactKindEvidence,
)
from treeforge.android.providers.artifact_classifier import (
    ProviderArtifactClassifier,
)
from treeforge.android.providers.artifact_enricher import (
    ProviderArtifactSemanticEnricher,
)
from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)
from treeforge.android.providers.archive_scanner import (
    ProviderArchiveScanError,
    ProviderArchiveScanner,
)

from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)
from treeforge.android.providers.generic_android_semantic_rule import (
    GenericAndroidArtifactSemanticRule,
)

from treeforge.android.providers.content_inspector import (
    ProviderContentInspector,
)
from treeforge.android.providers.content_observation import (
    ProviderContentObservation,
    ProviderContentObservationConfidence,
    ProviderContentSignature,
)

from treeforge.android.providers.provenance import (
    ProviderArtifactProvenance,
)


if TYPE_CHECKING:
    from treeforge.android.providers.factory import (
        FactoryImageProvider,
    )


def __getattr__(
    name: str,
):
    """
    Lazily expose provider implementations whose dependencies point back into
    higher-level Android knowledge infrastructure.

    FactoryImageProvider performs generic factory-source Discovery only.
    Device-, platform-, OEM-, and Android-version-specific knowledge is applied
    by the post-Discovery application knowledge handoff.

    Importing it eagerly here would make every providers submodule import
    initialize the knowledge registry, creating a circular dependency:

        knowledge
            -> provider semantic contracts
            -> providers package
            -> factory provider
            -> knowledge

    Lazy loading preserves the public providers API without introducing that
    initialization cycle.
    """

    if name == "FactoryImageProvider":
        from treeforge.android.providers.factory import (
            FactoryImageProvider,
        )

        return FactoryImageProvider

    raise AttributeError(
        f"module {__name__!r} "
        f"has no attribute {name!r}"
    )


__all__ = [
    "FactoryImageProvider",
    "GenericAndroidArtifactSemanticRule",
    "Provider",
    "ProviderArchiveScanError",
    "ProviderArchiveScanner",
    "ProviderArtifact",
    "ProviderArtifactClassification",
    "ProviderArtifactClassifier",
    "ProviderArtifactInventory",
    "ProviderArtifactKind",
    "ProviderArtifactKindEvidence",
    "ProviderArtifactProvenance",
    "ProviderArtifactSemanticEnricher",
    "ProviderArtifactSemanticRule",
    "ProviderCapability",
    "ProviderCollection",
    "ProviderContentInspector",
    "ProviderContentObservation",
    "ProviderContentObservationConfidence",
    "ProviderContentSignature",
    "ProviderResult",
    "ProviderSourceFilesystemProvenance",
    "ProviderSourceIdentity",
    "ProviderSourceType",
]