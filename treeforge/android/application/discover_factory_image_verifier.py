from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.application.discover_factory_image import (
    DiscoverFactoryImageResult,
)
from treeforge.android.discovery import (
    AndroidDiscoverySnapshotBuilder,
    AndroidDiscoverySnapshotComparator,
)


class DiscoverFactoryImageVerificationStatus(
    StrEnum,
):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(
    frozen=True,
    slots=True,
)
class DiscoverFactoryImageVerificationCheck:
    """
    One immutable verification result for a Discovery invariant.
    """

    check_id: str
    description: str
    status: DiscoverFactoryImageVerificationStatus
    detail: str

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "check_id",
                self.check_id,
            ),
            (
                "description",
                self.description,
            ),
            (
                "detail",
                self.detail,
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

        if not isinstance(
            self.status,
            DiscoverFactoryImageVerificationStatus,
        ):
            raise TypeError(
                "status must be a "
                "DiscoverFactoryImageVerificationStatus"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class DiscoverFactoryImageVerification:
    """
    Immutable aggregate of Discovery verification checks.
    """

    checks: tuple[
        DiscoverFactoryImageVerificationCheck,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.checks,
            tuple,
        ):
            raise TypeError(
                "checks must be a tuple"
            )

        for check in self.checks:
            if not isinstance(
                check,
                DiscoverFactoryImageVerificationCheck,
            ):
                raise TypeError(
                    "checks must contain "
                    "DiscoverFactoryImageVerificationCheck "
                    "instances"
                )

        check_ids = tuple(
            check.check_id
            for check in self.checks
        )

        if len(
            check_ids
        ) != len(
            set(
                check_ids
            )
        ):
            raise ValueError(
                "verification checks must not "
                "contain duplicate check IDs"
            )

    @property
    def passed_count(
        self,
    ) -> int:
        return sum(
            check.status
            is DiscoverFactoryImageVerificationStatus.PASS
            for check in self.checks
        )

    @property
    def failed_count(
        self,
    ) -> int:
        return sum(
            check.status
            is DiscoverFactoryImageVerificationStatus.FAIL
            for check in self.checks
        )

    @property
    def skipped_count(
        self,
    ) -> int:
        return sum(
            check.status
            is DiscoverFactoryImageVerificationStatus.SKIP
            for check in self.checks
        )

    @property
    def passed(
        self,
    ) -> bool:
        return (
            self.failed_count
            == 0
        )


class DiscoverFactoryImageVerifier:
    """
    Verify architectural invariants of one completed factory-image Discovery.

    This verifier does not perform Discovery again.

    It consumes the canonical result already produced by
    DiscoverFactoryImageService.

    Generic-only verification checks the raw Discovery contract.

    Knowledge-enriched verification additionally confirms that the resolved
    root/profile state is internally coherent.
    """

    def verify(
        self,
        result: DiscoverFactoryImageResult,
    ) -> DiscoverFactoryImageVerification:
        if not isinstance(
            result,
            DiscoverFactoryImageResult,
        ):
            raise TypeError(
                "result must be a "
                "DiscoverFactoryImageResult"
            )

        checks: list[
            DiscoverFactoryImageVerificationCheck
        ] = []

        discovery = result.discovery

        collection = (
            discovery.provider_collection
        )

        checks.append(
            self._check(
                check_id="provider-collection",
                description=(
                    "Provider Discovery produced a "
                    "canonical provider collection."
                ),
                passed=(
                    collection is not None
                ),
                pass_detail=(
                    "Provider collection is present."
                ),
                fail_detail=(
                    "Provider collection is missing."
                ),
            )
        )

        if collection is not None:
            checks.append(
                self._check(
                    check_id="provider-count",
                    description=(
                        "Factory Discovery produced exactly "
                        "one factory provider result."
                    ),
                    passed=(
                        len(collection)
                        == 1
                    ),
                    pass_detail=(
                        "Exactly one provider result is present."
                    ),
                    fail_detail=(
                        "Unexpected provider-result count: "
                        f"{len(collection)}."
                    ),
                )
            )

            factory_result = (
                collection.result_for(
                    "factory-image"
                )
            )

            checks.append(
                self._check(
                    check_id="factory-provider-result",
                    description=(
                        "Canonical factory-image provider "
                        "result is present."
                    ),
                    passed=(
                        factory_result is not None
                    ),
                    pass_detail=(
                        "factory-image provider result is present."
                    ),
                    fail_detail=(
                        "factory-image provider result is missing."
                    ),
                )
            )

            if factory_result is not None:
                inventory = (
                    factory_result.artifact_inventory
                )

                checks.append(
                    self._check(
                        check_id="artifact-count-consistency",
                        description=(
                            "Known and unknown artifact counts "
                            "equal the total inventory size."
                        ),
                        passed=(
                            inventory.known_count
                            + inventory.unknown_count
                            == len(inventory)
                        ),
                        pass_detail=(
                            "Artifact counts are internally consistent."
                        ),
                        fail_detail=(
                            "Artifact counts are inconsistent."
                        ),
                    )
                )

        checks.append(
            self._check(
                check_id="identity-result",
                description=(
                    "Discovery identity inference is "
                    "structurally valid."
                ),
                passed=(
                    discovery.identity_inference
                    is not None
                ),
                pass_detail=(
                    "Identity inference result is present."
                ),
                fail_detail=(
                    "Identity inference result is missing."
                ),
            )
        )

        snapshot = (
            AndroidDiscoverySnapshotBuilder()
            .build(
                discovery
            )
        )

        self_diff = (
            AndroidDiscoverySnapshotComparator()
            .compare(
                before=snapshot,
                after=snapshot,
            )
        )

        checks.append(
            self._check(
                check_id="snapshot-self-comparison",
                description=(
                    "Canonical Discovery snapshot is stable "
                    "when compared with itself."
                ),
                passed=(
                    self_diff.added_count == 0
                    and self_diff.removed_count == 0
                    and self_diff.changed_count == 0
                    and (
                        self_diff.unchanged_count
                        == snapshot.artifact_count
                    )
                    and not self_diff.device_changed
                    and not self_diff.android_version_changed
                ),
                pass_detail=(
                    "Self-comparison produced no changes."
                ),
                fail_detail=(
                    "Self-comparison detected unexpected changes."
                ),
            )
        )

        if result.request.generic_only:
            checks.append(
                DiscoverFactoryImageVerificationCheck(
                    check_id="knowledge-resolution",
                    description=(
                        "Knowledge resolution is not applied "
                        "during generic-only Discovery."
                    ),
                    status=(
                        DiscoverFactoryImageVerificationStatus.PASS
                        if result.knowledge_resolution is None
                        else DiscoverFactoryImageVerificationStatus.FAIL
                    ),
                    detail=(
                        "Knowledge resolution is absent."
                        if result.knowledge_resolution is None
                        else (
                            "Knowledge resolution unexpectedly "
                            "exists in generic-only mode."
                        )
                    ),
                )
            )

            checks.append(
                DiscoverFactoryImageVerificationCheck(
                    check_id="knowledge-enrichment",
                    description=(
                        "Knowledge enrichment checks are not "
                        "required during generic-only Discovery."
                    ),
                    status=(
                        DiscoverFactoryImageVerificationStatus.SKIP
                    ),
                    detail=(
                        "Generic-only mode intentionally skips "
                        "knowledge specialization."
                    ),
                )
            )

            return DiscoverFactoryImageVerification(
                checks=tuple(
                    checks
                )
            )

        resolution = (
            result.knowledge_resolution
        )

        checks.append(
            self._check(
                check_id="knowledge-resolution",
                description=(
                    "Knowledge-enriched Discovery produced "
                    "a canonical resolution result."
                ),
                passed=(
                    resolution is not None
                ),
                pass_detail=(
                    "Knowledge resolution is present."
                ),
                fail_detail=(
                    "Knowledge resolution is missing."
                ),
            )
        )

        if resolution is not None:
            root_ids = tuple(
                root.module_id
                for root in (
                    resolution.root_selections
                )
            )

            checks.append(
                self._check(
                    check_id="knowledge-root-consistency",
                    description=(
                        "Resolved profile roots match the "
                        "canonical root selections."
                    ),
                    passed=(
                        root_ids
                        == resolution.profile.roots
                    ),
                    pass_detail=(
                        "Knowledge roots and resolved profile agree."
                    ),
                    fail_detail=(
                        "Knowledge roots and resolved profile disagree."
                    ),
                )
            )

            explicit = (
                result.request
            )

            inferred = (
                discovery.identity_inference
            )

            device_root = next(
                (
                    root
                    for root in (
                        resolution.root_selections
                    )
                    if root.module_id.startswith(
                        "device:"
                    )
                ),
                None,
            )

            expected_device = (
                explicit.device_id
                if explicit.device_id is not None
                else inferred.device_id
            )

            selected_device_id = (
                None
                if device_root is None
                else device_root.module_id[
                    len("device:"):
                ]
            )

            checks.append(
                self._check(
                    check_id="device-selection-precedence",
                    description=(
                        "Available device Knowledge selection obeys "
                        "explicit > inferred > absent."
                    ),
                    passed=(
                        device_root is None
                        or (
                            expected_device is not None
                            and selected_device_id
                            == expected_device
                        )
                    ),
                    pass_detail=(
                        "Available device Knowledge selection "
                        "is consistent with canonical identity."
                    ),
                    fail_detail=(
                        "Selected device Knowledge conflicts "
                        "with canonical device identity."
                    ),
                )
            )

            version_root = next(
                (
                    root
                    for root in (
                        resolution.root_selections
                    )
                    if root.module_id.startswith(
                        "android:"
                    )
                ),
                None,
            )

            expected_android_version = (
                explicit.android_version
                if explicit.android_version is not None
                else inferred.android_version
            )

            checks.append(
                self._check(
                    check_id="android-version-selection-precedence",
                    description=(
                        "Android-version selection obeys "
                        "explicit > inferred > absent."
                    ),
                    passed=(
                        (
                            expected_android_version is None
                            and version_root is None
                        )
                        or (
                            expected_android_version is not None
                            and version_root is not None
                            and (
                                version_root.module_id
                                == (
                                    "android:"
                                    f"{expected_android_version}"
                                )
                            )
                        )
                    ),
                    pass_detail=(
                        "Android-version selection precedence is correct."
                    ),
                    fail_detail=(
                        "Android-version selection precedence "
                        "is inconsistent."
                    ),
                )
            )

        return DiscoverFactoryImageVerification(
            checks=tuple(
                checks
            )
        )

    @staticmethod
    def _check(
        *,
        check_id: str,
        description: str,
        passed: bool,
        pass_detail: str,
        fail_detail: str,
    ) -> DiscoverFactoryImageVerificationCheck:
        return DiscoverFactoryImageVerificationCheck(
            check_id=check_id,
            description=description,
            status=(
                DiscoverFactoryImageVerificationStatus.PASS
                if passed
                else DiscoverFactoryImageVerificationStatus.FAIL
            ),
            detail=(
                pass_detail
                if passed
                else fail_detail
            ),
        )