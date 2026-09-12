from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.apex.model import (
    AndroidParsedApex,
    ParsedApexContainer,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContext,
    AndroidUniverseRuntimeContextResolver,
)
from treeforge.android.universe.apex.deployment_context import (
    AndroidUniverseApexDeploymentContext,
    AndroidUniverseApexDeploymentPartition,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseApexRequirement:
    """
    Canonical device requirement derived from one complete parsed APEX lineage.

    ``source`` preserves the exact Parsing-owned ParsedApexContainer.

    Parsing remains authoritative for:
    - outer installed APEX/CAPEX identity;
    - semantic APEX container identity;
    - terminal apex_payload identity;
    - complete Extraction lineage;
    - literal apex_manifest.pb metadata.

    Universe adds runtime/deployment interpretation without reopening or
    reparsing any APEX artifact.
    """

    source: ParsedApexContainer

    runtime_context: AndroidUniverseRuntimeContext

    deployment_context: AndroidUniverseApexDeploymentContext

    @property
    def metadata(
        self,
    ) -> AndroidParsedApex:
        return self.source.metadata

    @property
    def outer_container(
        self,
    ) -> ExtractedArtifact:
        """
        Exact installed/discovered APEX or CAPEX artifact.
        """

        return self.source.outer_container

    @property
    def semantic_container(
        self,
    ) -> ExtractedArtifact:
        """
        Exact APEX ZIP whose manifest supplied semantic metadata.

        For ordinary APEX this is the outer container. For CAPEX this is the
        canonical extracted original_apex.
        """

        return self.source.semantic_container

    @property
    def payload_artifact(
        self,
    ) -> ExtractedArtifact:
        return self.source.payload_artifact

    @property
    def lineage_artifacts(
        self,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        return self.source.lineage_artifacts

    @property
    def artifact(
        self,
    ) -> ExtractedArtifact:
        """
        Canonical semantic APEX-container identity.

        Existing Universe APEX-payload ownership joins use the exact parent of
        apex_payload. ParsedApexContainer establishes that parent as
        semantic_container.
        """

        return self.semantic_container

    @property
    def apex_name(
        self,
    ) -> str:
        return self.metadata.apex_name

    @property
    def version(
        self,
    ) -> int:
        return self.metadata.version

    @property
    def provide_native_libs(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.metadata.provide_native_libs

    @property
    def require_native_libs(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.metadata.require_native_libs

    @property
    def jni_libs(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.metadata.jni_libs

    @property
    def require_shared_apex_libs(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.metadata.require_shared_apex_libs

    @property
    def provide_shared_apex_libs(
        self,
    ) -> bool:
        return self.metadata.provide_shared_apex_libs

    @property
    def provide_shared_apex_libs_present(
        self,
    ) -> bool:
        return (
            self.metadata
            .provide_shared_apex_libs_present
        )

    @property
    def supports_rebootless_update(
        self,
    ) -> bool:
        return (
            self.metadata
            .supports_rebootless_update
        )

    @property
    def supports_rebootless_update_present(
        self,
    ) -> bool:
        return (
            self.metadata
            .supports_rebootless_update_present
        )

    @property
    def deployment_partition(
        self,
    ) -> AndroidUniverseApexDeploymentPartition:
        """
        Canonical literal Android deployment partition.

        Treble-dependent linker classification remains a Runtime Linking
        responsibility.
        """

        return self.deployment_context.partition

    @property
    def is_vndk_apex(
        self,
    ) -> bool:
        """
        Whether this canonical APEX belongs to Android's VNDK APEX family.
        """

        return self.apex_name.startswith(
            "com.android.vndk."
        )

    def matches_vndk_version(
        self,
        version: str,
    ) -> bool:
        """
        Whether this canonical APEX is the exact versioned VNDK APEX.
        """

        if not isinstance(
            version,
            str,
        ):
            raise TypeError(
                "version must be a string"
            )

        return (
            self.apex_name
            == f"com.android.vndk.v{version}"
        )

    def shares_runtime(
        self,
        runtime_context: AndroidUniverseRuntimeContext,
    ) -> bool:
        """
        Whether this APEX belongs to the supplied canonical Android runtime.

        Runtime-context derivation remains Universe-owned; downstream stages
        consume this relationship without invoking the resolver themselves.
        """

        if not isinstance(
            runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        return (
            AndroidUniverseRuntimeContextResolver
            .same_runtime(
                self.runtime_context,
                runtime_context,
            )
        )

    def shares_manifest_name(
        self,
        other: AndroidUniverseApexRequirement,
    ) -> bool:
        """
        Whether two canonical APEX requirements preserve the same
        manifest module identity.
        """

        if not isinstance(
            other,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "other must be an "
                "AndroidUniverseApexRequirement"
            )

        return (
            self.apex_name
            == other.apex_name
        )

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "apex:"
            f"{self.apex_name}:"
            f"{self.version}:"
            f"{self.outer_container.path.as_posix()}:"
            f"{self.semantic_container.path.as_posix()}"
        )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedApexContainer,
        ):
            raise TypeError(
                "source must be a ParsedApexContainer"
            )

        if not isinstance(
            self.runtime_context,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "runtime_context must be an "
                "AndroidUniverseRuntimeContext"
            )

        if not isinstance(
            self.deployment_context,
            AndroidUniverseApexDeploymentContext,
        ):
            raise TypeError(
                "deployment_context must be an "
                "AndroidUniverseApexDeploymentContext"
            )

        if (
            self.artifact
            is not self.payload_artifact.parent
        ):
            raise ValueError(
                "APEX requirement semantic container must remain "
                "the exact parent of the canonical apex_payload"
            )

        if (
            self.metadata
            is not self.source.metadata
        ):
            raise ValueError(
                "APEX requirement must preserve exact Parsing "
                "manifest metadata identity"
            )
