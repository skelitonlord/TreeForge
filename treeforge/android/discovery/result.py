from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.discovery.identity import (
    AndroidIdentityInferenceResult,
)
from treeforge.android.partition import (
    PartitionLayout,
)
from treeforge.android.providers.collection import (
    ProviderCollection,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDiscoveryResult:
    """
    Immutable aggregate of canonical Android Discovery results.

    This model sits above the individual Discovery mechanisms.

    It does not perform Discovery itself.

    Each field retains the highest canonical model already produced by its
    owning Discovery subsystem:

        provider_collection
            provider/source artifact Discovery

        partition_layout
            canonical partition-layout interpretation

        identity_inference
            evidence-backed identity inference derived from Discovery evidence

    Fields are optional where TreeForge supports multiple Discovery entry
    points. A provider-only workflow or partially completed Discovery session
    may legitimately have only a subset available.

    Post-layout partition accessibility, filesystem metadata, materialization,
    extraction, and other downstream state do not belong in this aggregate.

    Android version, device identity, partition state, or any other fact must
    remain absent when Discovery has not established it.
    """

    provider_collection: (
        ProviderCollection
        | None
    ) = None

    partition_layout: (
        PartitionLayout
        | None
    ) = None

    identity_inference: (
        AndroidIdentityInferenceResult
    ) = AndroidIdentityInferenceResult()

    def __post_init__(
        self,
    ) -> None:
        self._validate_optional_type(
            self.provider_collection,
            expected_type=ProviderCollection,
            field_name="provider_collection",
        )

        self._validate_optional_type(
            self.partition_layout,
            expected_type=PartitionLayout,
            field_name="partition_layout",
        )

        if not isinstance(
            self.identity_inference,
            AndroidIdentityInferenceResult,
        ):
            raise TypeError(
                "identity_inference must be an "
                "AndroidIdentityInferenceResult"
            )

    @property
    def has_provider_discovery(
        self,
    ) -> bool:
        return (
            self.provider_collection
            is not None
        )

    @property
    def has_partition_layout(
        self,
    ) -> bool:
        return (
            self.partition_layout
            is not None
        )

    @property
    def has_identity_inference(
        self,
    ) -> bool:
        return (
            not self.identity_inference.is_empty
        )

    @staticmethod
    def _validate_optional_type(
        value: object,
        *,
        expected_type: type,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if not isinstance(
            value,
            expected_type,
        ):
            raise TypeError(
                f"{field_name} must be a "
                f"{expected_type.__name__} or None"
            )