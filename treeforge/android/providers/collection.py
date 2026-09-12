from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.providers.artifact import (
    ProviderArtifact,
)
from treeforge.android.providers.result import (
    ProviderResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderCollection:
    """
    Immutable deterministic collection of provider results.

    ProviderCollection exists specifically to represent results from multiple
    providers as one provider-level boundary.

    It owns only operations that are inherently cross-provider.

    Per-provider artifact queries remain the responsibility of each
    ProviderResult and its ProviderArtifactInventory.

    Duplicate semantic artifacts are intentionally allowed across providers.
    Conflict detection and resolution belong to the provider conflict and
    resolution subsystems.
    """

    results: tuple[
        ProviderResult,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.results,
            tuple,
        ):
            raise TypeError(
                "results must be a tuple"
            )

        for result in self.results:
            if not isinstance(
                result,
                ProviderResult,
            ):
                raise TypeError(
                    "results must contain "
                    "ProviderResult instances"
                )

        provider_ids = tuple(
            result.provider_id
            for result in self.results
        )

        if (
            len(provider_ids)
            != len(set(provider_ids))
        ):
            raise ValueError(
                "collection contains duplicate "
                "provider IDs"
            )

        canonical = tuple(
            sorted(
                self.results,
                key=lambda result: (
                    result.provider_id,
                    result.source_type.value,
                    result.provider_name,
                    result.provider_version,
                ),
            )
        )

        object.__setattr__(
            self,
            "results",
            canonical,
        )

    def __len__(
        self,
    ) -> int:
        """
        Return the number of provider results.
        """

        return len(
            self.results
        )

    def __iter__(
        self,
    ):
        """
        Iterate over provider results in canonical order.
        """

        return iter(
            self.results
        )

    @property
    def artifacts(
        self,
    ) -> tuple[
        ProviderArtifact,
        ...,
    ]:
        """
        Return every artifact from every provider.

        This is intentionally a collection-level operation because it crosses
        provider boundaries.

        Cross-provider duplicates remain intact so the conflict/resolution
        subsystem can reason about them.
        """

        artifacts = tuple(
            artifact
            for result in self.results
            for artifact
            in result.artifact_inventory
        )

        return tuple(
            sorted(
                artifacts,
                key=lambda artifact: (
                    artifact.kind.value,
                    artifact.classification.value,
                    artifact.name,
                    artifact.provider_id,
                    artifact.source_type.value,
                    artifact.source_name,
                ),
            )
        )

    def result_for(
        self,
        provider_id: str,
    ) -> ProviderResult | None:
        """
        Return the result belonging to one provider ID.
        """

        if not isinstance(
            provider_id,
            str,
        ):
            raise TypeError(
                "provider_id must be a string"
            )

        if not provider_id.strip():
            raise ValueError(
                "provider_id must not be empty"
            )

        for result in self.results:
            if (
                result.provider_id
                == provider_id
            ):
                return result

        return None