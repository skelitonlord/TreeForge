from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.providers.artifact import (
    ProviderArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PartitionSource:
    """
    Immutable provenance-bearing source for one canonical Android partition.

    The exact Discovery ProviderArtifact is preserved by identity.

    Partition interpretation may add partition-specific facts in later
    canonical models, but it must never replace, normalize, duplicate, or
    discard the Discovery artifact that established the source.

    This allows every downstream partition to remain traceable to:

    - exact provider source identity;
    - provider identity;
    - provider source type;
    - archive/member provenance;
    - structural kind and kind evidence;
    - content observations;
    - semantic classification;
    - current upstream accessible-path bridge, when one exists.

    Additional partition-stage evidence belongs on partition models or later
    derivation models while this source remains unchanged.
    """

    artifact: ProviderArtifact

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ProviderArtifact,
        ):
            raise TypeError(
                "artifact must be a ProviderArtifact"
            )

    @property
    def source_name(
        self,
    ) -> str:
        """
        Return the exact canonical Discovery source identity.
        """

        return self.artifact.source_name