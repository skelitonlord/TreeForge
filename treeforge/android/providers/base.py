from __future__ import annotations

from abc import (
    ABC,
    abstractmethod,
)
from enum import StrEnum
from typing import TYPE_CHECKING

from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.core.context.context import (
    Context,
)


if TYPE_CHECKING:
    from treeforge.android.providers.artifact_inventory import (
        ProviderArtifactInventory,
    )
    from treeforge.android.providers.result import (
        ProviderResult,
    )
    from treeforge.android.providers.source_identity import (
        ProviderSourceIdentity,
    )


class ProviderCapability(
    StrEnum,
):
    """
    Capability supplied by one Android artifact provider.

    ARTIFACT_DISCOVERY means the provider exposes one canonical exhaustive
    ProviderArtifactInventory.

    Other capabilities should only be added when they represent a genuinely
    distinct provider-level contract.
    """

    ARTIFACT_DISCOVERY = (
        "artifact-discovery"
    )


class Provider(
    ABC,
):
    """
    Base class for Android artifact providers.

    A provider discovers source artifacts and publishes one canonical
    ProviderResult.

    Extraction, parsing, format analysis, partition interpretation, and build
    reconstruction belong to later TreeForge layers.
    """

    provider_id: str = "provider"

    name: str = "Provider"

    description: str = ""

    version: str = "1.0"

    source_type = (
        ProviderSourceType.CUSTOM
    )

    capabilities: tuple[
        ProviderCapability,
        ...,
    ] = ()

    @abstractmethod
    def populate(
        self,
        context: Context,
    ) -> None:
        """
        Populate provider discovery state into the TreeForge context.
        """

        raise NotImplementedError

    def supports(
        self,
        capability: ProviderCapability,
    ) -> bool:
        """
        Return whether this provider supports one capability.
        """

        if not isinstance(
            capability,
            ProviderCapability,
        ):
            raise TypeError(
                "capability must be a "
                "ProviderCapability"
            )

        return (
            capability
            in self.capabilities
        )

    def create_result(
        self,
        *,
        artifact_inventory: (
            ProviderArtifactInventory
        ),
        source_identity: (
            ProviderSourceIdentity
            | None
        ) = None,
        warnings: tuple[
            str,
            ...,
        ] = (),
    ) -> ProviderResult:
        """
        Create the immutable canonical result for this provider.
        """

        from treeforge.android.providers.result import (
            ProviderResult,
        )

        return ProviderResult(
            provider_id=self.provider_id,
            provider_name=self.name,
            provider_version=self.version,
            source_type=self.source_type,
            source_identity=source_identity,
            capabilities=self.capabilities,
            artifact_inventory=(
                artifact_inventory
            ),
            warnings=warnings,
        )