from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.reconstruction_ownership.source.package_identity import (
    AndroidSourcePackageIdentity,
    AndroidSourcePackageIdentityInventory,
)
from treeforge.android.universe.apk import (
    AndroidUniverseApkPackageRequirement,
)


class AndroidApkSourceProviderStatus(StrEnum):
    """
    Source-provider resolution status for one canonical installed APK.

    ABSENT is part of the canonical result vocabulary but is deliberately
    not produced by the first resolver pass.  Failure to find an exact
    source-package candidate is insufficient evidence that source is absent.
    """

    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    ABSENT = "absent"
    UNRESOLVED = "unresolved"


class AndroidApkSourceProviderEvidenceKind(StrEnum):
    """
    Exact evidence used to relate an installed APK to a source build module.
    """

    EXACT_PACKAGE_IDENTITY = "exact_package_identity"

    EXACT_INSTALLED_BASENAME_MODULE_NAME = (
        "exact_installed_basename_module_name"
    )


@dataclass(frozen=True, slots=True)
class AndroidApkSourceProviderCandidate:
    """
    One source package-identity candidate for an installed APK.

    The exact AndroidSourcePackageIdentity object is preserved.  Through
    that object the exact build module and exact source repository identity
    are preserved as well.
    """

    source_identity: AndroidSourcePackageIdentity

    evidence: tuple[
        AndroidApkSourceProviderEvidenceKind,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_identity,
            AndroidSourcePackageIdentity,
        ):
            raise TypeError(
                "source_identity must be an "
                "AndroidSourcePackageIdentity"
            )

        if (
            not isinstance(
                self.evidence,
                tuple,
            )
            or not self.evidence
            or not all(
                isinstance(
                    item,
                    AndroidApkSourceProviderEvidenceKind,
                )
                for item in self.evidence
            )
        ):
            raise TypeError(
                "evidence must be a non-empty tuple of "
                "AndroidApkSourceProviderEvidenceKind values"
            )

        if (
            AndroidApkSourceProviderEvidenceKind
            .EXACT_PACKAGE_IDENTITY
            not in self.evidence
        ):
            raise ValueError(
                "APK source-provider candidates must be "
                "backed by exact package identity"
            )

        expected = tuple(
            sorted(
                set(
                    self.evidence
                ),
                key=lambda item: item.value,
            )
        )

        if self.evidence != expected:
            raise ValueError(
                "candidate evidence must be unique and "
                "deterministically ordered"
            )

    @property
    def module(
        self,
    ):
        return self.source_identity.module


@dataclass(frozen=True, slots=True)
class AndroidApkSourceProviderResolution:
    """
    Conservative source-provider resolution for one canonical installed APK.

    candidates preserves every exact package-identity candidate considered.

    provider is populated only when the available exact evidence identifies
    exactly one source provider.

    This model does not decide Reconstruction Ownership.
    """

    requirement: AndroidUniverseApkPackageRequirement

    status: AndroidApkSourceProviderStatus

    candidates: tuple[
        AndroidApkSourceProviderCandidate,
        ...,
    ] = ()

    provider: AndroidApkSourceProviderCandidate | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseApkPackageRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseApkPackageRequirement"
            )

        if not isinstance(
            self.status,
            AndroidApkSourceProviderStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidApkSourceProviderStatus"
            )

        if (
            not isinstance(
                self.candidates,
                tuple,
            )
            or not all(
                isinstance(
                    candidate,
                    AndroidApkSourceProviderCandidate,
                )
                for candidate in self.candidates
            )
        ):
            raise TypeError(
                "candidates must contain only "
                "AndroidApkSourceProviderCandidate values"
            )

        expected = tuple(
            sorted(
                self.candidates,
                key=lambda candidate: (
                    candidate.module.name,
                    candidate.module.repository.project_path,
                    candidate.module.source_path,
                    candidate.module.source_line,
                    candidate.module.module_type,
                ),
            )
        )

        if self.candidates != expected:
            raise ValueError(
                "candidates must use deterministic ordering"
            )

        if (
            self.provider is not None
            and not isinstance(
                self.provider,
                AndroidApkSourceProviderCandidate,
            )
        ):
            raise TypeError(
                "provider must be an "
                "AndroidApkSourceProviderCandidate or None"
            )

        if (
            self.provider is not None
            and not any(
                self.provider
                is candidate
                for candidate in self.candidates
            )
        ):
            raise ValueError(
                "provider must preserve exact identity from "
                "the candidate population"
            )

        if (
            self.status
            is AndroidApkSourceProviderStatus.RESOLVED
        ):
            if self.provider is None:
                raise ValueError(
                    "RESOLVED provider resolution must "
                    "retain one provider"
                )

        else:
            if self.provider is not None:
                raise ValueError(
                    "only RESOLVED provider resolutions "
                    "may retain a provider"
                )

        if (
            self.status
            is AndroidApkSourceProviderStatus.AMBIGUOUS
            and len(
                self.candidates
            ) < 2
        ):
            raise ValueError(
                "AMBIGUOUS provider resolution requires "
                "multiple candidates"
            )

        if self.status in (
            AndroidApkSourceProviderStatus.ABSENT,
            AndroidApkSourceProviderStatus.UNRESOLVED,
        ):
            if self.candidates:
                raise ValueError(
                    "ABSENT/UNRESOLVED provider resolutions "
                    "must not retain exact candidates"
                )


class AndroidApkSourceProviderResolver:
    """
    Resolve canonical installed APKs against source package identities.

    First-pass evidence contract:

    1. Exact canonical installed package identity is required.
    2. One exact source package candidate resolves directly.
    3. Multiple exact package candidates resolve only when exactly one
       candidate's build-module name exactly equals the installed APK
       basename.
    4. Multiple remaining candidates are ambiguous.
    5. Zero exact candidates are unresolved, not absent.

    The resolver does not:
    - infer package/module mappings from naming style;
    - strip Google/vendor suffixes from module names;
    - evaluate PRODUCT_PACKAGES;
    - execute Soong or Make;
    - resolve generated manifests or prebuilt APK package identity;
    - infer repository/device relevance;
    - choose an Ownership domain.
    """

    @classmethod
    def resolve(
        cls,
        *,
        requirements: tuple[
            AndroidUniverseApkPackageRequirement,
            ...,
        ],
        source_packages: AndroidSourcePackageIdentityInventory,
    ) -> tuple[
        AndroidApkSourceProviderResolution,
        ...,
    ]:
        if (
            not isinstance(
                requirements,
                tuple,
            )
            or not all(
                isinstance(
                    requirement,
                    AndroidUniverseApkPackageRequirement,
                )
                for requirement in requirements
            )
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseApkPackageRequirement values"
            )

        if not isinstance(
            source_packages,
            AndroidSourcePackageIdentityInventory,
        ):
            raise TypeError(
                "source_packages must be an "
                "AndroidSourcePackageIdentityInventory"
            )

        resolutions = tuple(
            cls._resolve_requirement(
                requirement=requirement,
                source_packages=source_packages,
            )
            for requirement in requirements
        )

        return tuple(
            sorted(
                resolutions,
                key=cls._resolution_sort_key,
            )
        )

    @classmethod
    def _resolve_requirement(
        cls,
        *,
        requirement: AndroidUniverseApkPackageRequirement,
        source_packages: AndroidSourcePackageIdentityInventory,
    ) -> AndroidApkSourceProviderResolution:
        identities = (
            source_packages
            .identities_for_package(
                requirement.package_name
            )
        )

        if not identities:
            return AndroidApkSourceProviderResolution(
                requirement=requirement,
                status=(
                    AndroidApkSourceProviderStatus
                    .UNRESOLVED
                ),
            )

        installed_basename = (
            cls._installed_apk_basename(
                requirement
            )
        )

        candidates = tuple(
            sorted(
                (
                    cls._candidate(
                        identity=identity,
                        installed_basename=(
                            installed_basename
                        ),
                    )
                    for identity in identities
                ),
                key=lambda candidate: (
                    candidate.module.name,
                    candidate.module.repository.project_path,
                    candidate.module.source_path,
                    candidate.module.source_line,
                    candidate.module.module_type,
                ),
            )
        )

        if len(
            candidates
        ) == 1:
            return AndroidApkSourceProviderResolution(
                requirement=requirement,
                status=(
                    AndroidApkSourceProviderStatus
                    .RESOLVED
                ),
                candidates=candidates,
                provider=candidates[0],
            )

        basename_matches = tuple(
            candidate
            for candidate in candidates
            if (
                AndroidApkSourceProviderEvidenceKind
                .EXACT_INSTALLED_BASENAME_MODULE_NAME
                in candidate.evidence
            )
        )

        if len(
            basename_matches
        ) == 1:
            return AndroidApkSourceProviderResolution(
                requirement=requirement,
                status=(
                    AndroidApkSourceProviderStatus
                    .RESOLVED
                ),
                candidates=candidates,
                provider=basename_matches[0],
            )

        return AndroidApkSourceProviderResolution(
            requirement=requirement,
            status=(
                AndroidApkSourceProviderStatus
                .AMBIGUOUS
            ),
            candidates=candidates,
        )

    @staticmethod
    def _candidate(
        *,
        identity: AndroidSourcePackageIdentity,
        installed_basename: str,
    ) -> AndroidApkSourceProviderCandidate:
        evidence = [
            AndroidApkSourceProviderEvidenceKind
            .EXACT_PACKAGE_IDENTITY,
        ]

        if (
            identity.module.name
            == installed_basename
        ):
            evidence.append(
                AndroidApkSourceProviderEvidenceKind
                .EXACT_INSTALLED_BASENAME_MODULE_NAME
            )

        return AndroidApkSourceProviderCandidate(
            source_identity=identity,
            evidence=tuple(
                sorted(
                    evidence,
                    key=lambda item: item.value,
                )
            ),
        )

    @staticmethod
    def _installed_apk_basename(
        requirement: AndroidUniverseApkPackageRequirement,
    ) -> str:
        name = (
            requirement
            .source
            .source
            .apk_android_path
            .name
        )

        if name.endswith(
            ".gz"
        ):
            name = name[
                :-3
            ]

        if name.endswith(
            ".apk"
        ):
            name = name[
                :-4
            ]

        if not name:
            raise ValueError(
                "installed APK path has no usable basename"
            )

        return name

    @staticmethod
    def _resolution_sort_key(
        resolution: AndroidApkSourceProviderResolution,
    ) -> tuple[
        str,
        str,
        str,
    ]:
        requirement = (
            resolution.requirement
        )

        return (
            requirement.package_name,
            (
                requirement
                .source
                .source
                .apk_android_path
                .as_posix()
            ),
            requirement.artifact.requirement_id,
        )
