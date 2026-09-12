from __future__ import annotations

from dataclasses import dataclass
from treeforge.android.extraction import (
    ExtractedArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParsedApex:
    """
    Literal metadata recovered from one canonical APEX source.

    Parsing records only what the APEX manifest says. Interpretation,
    reconciliation, package ownership, and build-module decisions belong to
    later stages.
    """

    artifact: ExtractedArtifact
    apex_name: str
    version: int

    provide_native_libs: tuple[
        str,
        ...,
    ]

    require_native_libs: tuple[
        str,
        ...,
    ]

    jni_libs: tuple[
        str,
        ...,
    ]

    require_shared_apex_libs: tuple[
        str,
        ...,
    ]

    provide_shared_apex_libs: bool
    provide_shared_apex_libs_present: bool

    supports_rebootless_update: bool
    supports_rebootless_update_present: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.apex_name,
            str,
        ):
            raise TypeError(
                "apex_name must be a str"
            )

        if not self.apex_name:
            raise ValueError(
                "apex_name must not be empty"
            )

        if not isinstance(
            self.version,
            int,
        ):
            raise TypeError(
                "version must be an int"
            )

        if self.version < 0:
            raise ValueError(
                "version must not be negative"
            )


        for field_name, values in (
            (
                "provide_native_libs",
                self.provide_native_libs,
            ),
            (
                "require_native_libs",
                self.require_native_libs,
            ),
            (
                "jni_libs",
                self.jni_libs,
            ),
            (
                "require_shared_apex_libs",
                self.require_shared_apex_libs,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    str,
                )
                and value
                for value in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    "non-empty strings"
                )

        if not isinstance(
            self.provide_shared_apex_libs,
            bool,
        ):
            raise TypeError(
                "provide_shared_apex_libs must be a bool"
            )

        if not isinstance(
            self.provide_shared_apex_libs_present,
            bool,
        ):
            raise TypeError(
                "provide_shared_apex_libs_present must be a bool"
            )

        if not isinstance(
            self.supports_rebootless_update,
            bool,
        ):
            raise TypeError(
                "supports_rebootless_update must be a bool"
            )

        if not isinstance(
            self.supports_rebootless_update_present,
            bool,
        ):
            raise TypeError(
                "supports_rebootless_update_present must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedApexContainer:
    """
    Complete Parsing representation of one canonical logical APEX lineage.

    ``outer_container`` is the canonical discovered APEX/CAPEX artifact.

    ``semantic_container`` is the exact APEX ZIP whose manifest Parsing
    decoded. For an uncompressed APEX it is identical to
    ``outer_container``. For a compressed APEX it is the canonical
    ``original_apex`` Extraction artifact.

    ``payload_artifact`` is the terminal canonical ``apex_payload`` artifact.

    ``lineage_artifacts`` contains every APEX_CONTAINER_EXTRACTION artifact
    between the outer container and the terminal payload, in outer-to-inner
    order.

    No physical APEX/CAPEX discovery or materialization is performed here.
    """

    outer_container: ExtractedArtifact
    semantic_container: ExtractedArtifact
    payload_artifact: ExtractedArtifact

    lineage_artifacts: tuple[
        ExtractedArtifact,
        ...,
    ]

    metadata: AndroidParsedApex

    def __post_init__(
        self,
    ) -> None:
        for field_name, artifact in (
            (
                "outer_container",
                self.outer_container,
            ),
            (
                "semantic_container",
                self.semantic_container,
            ),
            (
                "payload_artifact",
                self.payload_artifact,
            ),
        ):
            if not isinstance(
                artifact,
                ExtractedArtifact,
            ):
                raise TypeError(
                    f"{field_name} must be an ExtractedArtifact"
                )

        if not isinstance(
            self.lineage_artifacts,
            tuple,
        ):
            raise TypeError(
                "lineage_artifacts must be a tuple"
            )

        if not self.lineage_artifacts:
            raise ValueError(
                "APEX lineage must contain at least one "
                "APEX_CONTAINER_EXTRACTION artifact"
            )

        if not all(
            isinstance(
                artifact,
                ExtractedArtifact,
            )
            for artifact
            in self.lineage_artifacts
        ):
            raise TypeError(
                "lineage_artifacts must contain only "
                "ExtractedArtifact instances"
            )

        lineage_ids = tuple(
            id(artifact)
            for artifact
            in self.lineage_artifacts
        )

        if len(
            lineage_ids
        ) != len(
            set(lineage_ids)
        ):
            raise ValueError(
                "APEX lineage contains duplicate canonical "
                "artifact identities"
            )

        if (
            self.payload_artifact
            is not self.lineage_artifacts[-1]
        ):
            raise ValueError(
                "APEX payload must be the terminal lineage artifact"
            )

        if (
            self.payload_artifact.operation.value
            != "apex_container_extraction"
            or self.payload_artifact.semantic_name
            != "apex_payload"
        ):
            raise ValueError(
                "APEX payload artifact must be the canonical "
                "terminal apex_payload extraction"
            )

        expected_parent = (
            self.outer_container
        )

        for artifact in self.lineage_artifacts:
            if artifact.parent is not expected_parent:
                raise ValueError(
                    "APEX lineage does not preserve exact parent identity"
                )

            expected_parent = artifact

        expected_semantic_container = (
            self.payload_artifact.parent
        )

        if (
            self.semantic_container
            is not expected_semantic_container
        ):
            raise ValueError(
                "semantic_container must be the exact parent of "
                "the terminal apex_payload"
            )

        if not isinstance(
            self.metadata,
            AndroidParsedApex,
        ):
            raise TypeError(
                "metadata must be an AndroidParsedApex"
            )

        if (
            self.metadata.artifact
            is not self.semantic_container
        ):
            raise ValueError(
                "APEX metadata must preserve exact semantic "
                "container identity"
            )

