from __future__ import annotations

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidParserFilesystemSource,
)
from treeforge.android.universe.runtime_context.model import (
    AndroidUniverseRuntimeContext,
    AndroidUniverseRuntimeContextKind,
)


class AndroidUniverseRuntimeContextResolver:
    """
    Derive Android runtime boundaries from canonical Extraction provenance.

    This resolver deliberately does not recognize device names, partition
    names, APEX package names, guest/runtime product names, or hardcoded
    filesystem locations.

    A logical partition belongs to a distinct nested runtime only when its
    logical-partition container itself was discovered beneath an already
    materialized filesystem or CPIO root.

    This distinction keeps an ordinary top-level factory ``super`` partition
    set in the ROOT runtime while allowing structurally nested Android
    partition sets to form independent runtime contexts.

    APEX payload extraction alone does not establish a new runtime context.
    Files inside an APEX therefore inherit the context of the Android runtime
    containing that APEX unless their ancestry subsequently crosses a nested
    logical-partition boundary.
    """

    _ENCLOSING_FILESYSTEM_OPERATIONS = frozenset(
        {
            ExtractionOperation.FILESYSTEM_EXTRACTION,
            ExtractionOperation.CPIO_EXTRACTION,
        }
    )

    @classmethod
    def _container_is_nested(
        cls,
        container: ExtractedArtifact,
    ) -> bool:
        ancestor = container.parent

        while ancestor is not None:
            if (
                ancestor.operation
                in cls._ENCLOSING_FILESYSTEM_OPERATIONS
            ):
                return True

            ancestor = ancestor.parent

        return False

    @classmethod
    def resolve_artifact(
        cls,
        artifact: ExtractedArtifact,
    ) -> AndroidUniverseRuntimeContext:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        current: ExtractedArtifact | None = (
            artifact
        )

        while current is not None:
            if (
                current.operation
                is ExtractionOperation
                .LOGICAL_PARTITION_EXTRACTION
            ):
                container = current.parent

                if (
                    container is not None
                    and cls._container_is_nested(
                        container
                    )
                ):
                    return (
                        AndroidUniverseRuntimeContext(
                            kind=(
                                AndroidUniverseRuntimeContextKind
                                .NESTED_PARTITION_SET
                            ),
                            partition_container=container,
                        )
                    )

            current = current.parent

        return AndroidUniverseRuntimeContext(
            kind=(
                AndroidUniverseRuntimeContextKind
                .ROOT
            ),
        )

    @classmethod
    def resolve_filesystem_source(
        cls,
        source: AndroidParserFilesystemSource,
    ) -> AndroidUniverseRuntimeContext:
        if not isinstance(
            source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "source must be an "
                "AndroidParserFilesystemSource"
            )

        return cls.resolve_artifact(
            source.artifact
        )

    @classmethod
    def resolve_model_source(
        cls,
        source: AndroidModelSource,
    ) -> AndroidUniverseRuntimeContext:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        return cls.resolve_filesystem_source(
            source.filesystem_source
        )

    @classmethod
    def resolve_optional_filesystem_source(
        cls,
        source: AndroidParserFilesystemSource | None,
    ) -> AndroidUniverseRuntimeContext:
        """
        Resolve an optional canonical filesystem source into one Android
        runtime context.

        INIT requirements without an attached filesystem source are legacy
        root-runtime observations. Concrete filesystem sources retain their
        exact Extraction-derived runtime identity.
        """

        if source is None:
            return AndroidUniverseRuntimeContext(
                kind=(
                    AndroidUniverseRuntimeContextKind
                    .ROOT
                ),
            )

        return cls.resolve_filesystem_source(
            source
        )


    @staticmethod
    def same_runtime(
        left: AndroidUniverseRuntimeContext,
        right: AndroidUniverseRuntimeContext,
    ) -> bool:
        if not isinstance(
            left,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "left must be an AndroidUniverseRuntimeContext"
            )

        if not isinstance(
            right,
            AndroidUniverseRuntimeContext,
        ):
            raise TypeError(
                "right must be an AndroidUniverseRuntimeContext"
            )

        if left.kind is not right.kind:
            return False

        if left.is_root:
            return True

        return (
            left.partition_container
            is right.partition_container
        )
