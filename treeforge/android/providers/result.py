from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)
from treeforge.android.providers.base import (
    ProviderCapability,
)
from treeforge.android.providers.source_identity import (
    ProviderSourceIdentity,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderResult:
    """
    Immutable canonical result produced by one provider.

    ProviderResult describes one provider execution.

    The authoritative discovered-artifact state is held by
    ProviderArtifactInventory.

    Parsing, extraction, materialization, partition interpretation, and other
    later-stage results do not belong here.
    """

    provider_id: str
    provider_name: str
    provider_version: str

    source_type: ProviderSourceType

    source_identity: (
        ProviderSourceIdentity
        | None
    ) = None

    capabilities: tuple[
        ProviderCapability,
        ...,
    ] = ()

    artifact_inventory: (
        ProviderArtifactInventory
    ) = ProviderArtifactInventory()

    warnings: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        self._validate_identity()
        self._validate_source_type()
        self._validate_source_identity()
        self._validate_capabilities()
        self._validate_artifact_inventory()
        self._validate_warnings()

        canonical_capabilities = tuple(
            sorted(
                self.capabilities,
                key=lambda capability: (
                    capability.value
                ),
            )
        )

        object.__setattr__(
            self,
            "capabilities",
            canonical_capabilities,
        )

    def _validate_identity(
        self,
    ) -> None:
        for (
            field_name,
            value,
        ) in (
            (
                "provider_id",
                self.provider_id,
            ),
            (
                "provider_name",
                self.provider_name,
            ),
            (
                "provider_version",
                self.provider_version,
            ),
        ):
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

    def _validate_source_type(
        self,
    ) -> None:
        if not isinstance(
            self.source_type,
            ProviderSourceType,
        ):
            raise TypeError(
                "source_type must be a "
                "ProviderSourceType"
            )

    def _validate_source_identity(
        self,
    ) -> None:
        if self.source_identity is None:
            return

        if not isinstance(
            self.source_identity,
            ProviderSourceIdentity,
        ):
            raise TypeError(
                "source_identity must be a "
                "ProviderSourceIdentity or None"
            )

        if (
            self.source_identity.provider_id
            != self.provider_id
        ):
            raise ValueError(
                "source_identity provider_id must "
                "match provider_id"
            )

        if (
            self.source_identity.source_type
            is not self.source_type
        ):
            raise ValueError(
                "source_identity source_type must "
                "match source_type"
            )

    def _validate_capabilities(
        self,
    ) -> None:
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
                ProviderCapability,
            ):
                raise TypeError(
                    "capabilities must contain "
                    "ProviderCapability instances"
                )

        if (
            len(
                self.capabilities
            )
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

    def _validate_artifact_inventory(
        self,
    ) -> None:
        if not isinstance(
            self.artifact_inventory,
            ProviderArtifactInventory,
        ):
            raise TypeError(
                "artifact_inventory must be a "
                "ProviderArtifactInventory"
            )

        for artifact in (
            self.artifact_inventory
        ):
            if (
                artifact.provider_id
                != self.provider_id
            ):
                raise ValueError(
                    "provider artifacts must preserve "
                    "the result provider_id"
                )

            if (
                artifact.source_type
                is not self.source_type
            ):
                raise ValueError(
                    "provider artifacts must preserve "
                    "the result source_type"
                )

    def _validate_warnings(
        self,
    ) -> None:
        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise TypeError(
                "warnings must be a tuple"
            )

        for warning in self.warnings:
            if not isinstance(
                warning,
                str,
            ):
                raise TypeError(
                    "warnings must contain strings"
                )

            if not warning.strip():
                raise ValueError(
                    "warnings must not contain "
                    "empty values"
                )

    @property
    def has_warnings(
        self,
    ) -> bool:
        """
        Return whether this provider produced warnings.
        """

        return bool(
            self.warnings
        )

    def supports(
        self,
        capability: ProviderCapability,
    ) -> bool:
        """
        Return whether this provider result declares one capability.
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