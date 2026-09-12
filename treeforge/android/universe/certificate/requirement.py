from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import posixpath

from treeforge.android.filesystem.metadata.model import (
    FilesystemEntryType,
    FilesystemMetadataEntry,
    normalize_metadata_path,
)
from treeforge.android.parsing.certificate import (
    AndroidCertificateParsingResult,
    AndroidOtaCertificateArchiveMember,
    ParsedAndroidCertificateSource,
    ParsedAndroidOtaCertificateArchive,
    ParsedAndroidX509Certificate,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


class AndroidUniverseCertificateSourceRole(StrEnum):
    """
    Device-level use role established by canonical Android source semantics.

    This is deliberately not a claim about cryptographic validity.
    """

    CA_TRUST_STORE_MEMBER = "ca_trust_store_member"

    WIFI_CA_TRUST_STORE_MEMBER = (
        "wifi_ca_trust_store_member"
    )

    FSVERITY_VERIFICATION_CERTIFICATE = (
        "fsverity_verification_certificate"
    )

    CERTIFICATE_CHAIN = "certificate_chain"

    OTHER = "other"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCertificateFilesystemBinding:
    """
    Exact filesystem/payload binding for one installed certificate-bearing
    source.

    The logical source node may be a symlink. The Artifact always represents
    the final regular-file payload whose bytes Parsing consumed.
    """

    source_metadata_entry: FilesystemMetadataEntry

    symlink_chain: tuple[
        FilesystemMetadataEntry,
        ...,
    ]

    payload_metadata_entry: FilesystemMetadataEntry

    artifact: AndroidUniverseArtifactRequirement

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "source_metadata_entry must be a "
                "FilesystemMetadataEntry"
            )

        if not isinstance(
            self.symlink_chain,
            tuple,
        ):
            raise TypeError(
                "symlink_chain must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                FilesystemMetadataEntry,
            )
            for entry in self.symlink_chain
        ):
            raise TypeError(
                "symlink_chain must contain only "
                "FilesystemMetadataEntry values"
            )

        if not isinstance(
            self.payload_metadata_entry,
            FilesystemMetadataEntry,
        ):
            raise TypeError(
                "payload_metadata_entry must be a "
                "FilesystemMetadataEntry"
            )

        if (
            self.payload_metadata_entry.entry_type
            is not FilesystemEntryType.FILE
        ):
            raise ValueError(
                "certificate payload must resolve to a "
                "regular filesystem file"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        if (
            self.artifact.metadata_entry
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "certificate Artifact must preserve the exact "
                "resolved regular-file metadata identity"
            )

        if self.symlink_chain:
            if (
                self.symlink_chain[0]
                is not self.source_metadata_entry
            ):
                raise ValueError(
                    "certificate symlink chain must begin with "
                    "the exact logical source metadata entry"
                )

            if not all(
                entry.entry_type
                is FilesystemEntryType.SYMLINK
                for entry in self.symlink_chain
            ):
                raise ValueError(
                    "certificate symlink chain may contain only "
                    "symlink metadata entries"
                )

        elif (
            self.source_metadata_entry
            is not self.payload_metadata_entry
        ):
            raise ValueError(
                "non-symlink certificate source must itself be "
                "the regular-file payload"
            )

    @property
    def is_alias(
        self,
    ) -> bool:
        return bool(
            self.symlink_chain
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCertificateSourceRequirement:
    source: ParsedAndroidCertificateSource

    role: AndroidUniverseCertificateSourceRole

    filesystem: AndroidUniverseCertificateFilesystemBinding

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidCertificateSource,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidCertificateSource"
            )

        if not isinstance(
            self.role,
            AndroidUniverseCertificateSourceRole,
        ):
            raise TypeError(
                "role must be an "
                "AndroidUniverseCertificateSourceRole"
            )

        if not isinstance(
            self.filesystem,
            AndroidUniverseCertificateFilesystemBinding,
        ):
            raise TypeError(
                "filesystem must be an "
                "AndroidUniverseCertificateFilesystemBinding"
            )

        if (
            self.filesystem.artifact.inventory_entry.artifact
            is not self.source.source.filesystem_source.artifact
        ):
            raise ValueError(
                "certificate requirement must preserve exact "
                "Parsing filesystem artifact identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseOtaCertificateArchiveRequirement:
    source: ParsedAndroidOtaCertificateArchive

    filesystem: AndroidUniverseCertificateFilesystemBinding

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidOtaCertificateArchive,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidOtaCertificateArchive"
            )

        if not isinstance(
            self.filesystem,
            AndroidUniverseCertificateFilesystemBinding,
        ):
            raise TypeError(
                "filesystem must be an "
                "AndroidUniverseCertificateFilesystemBinding"
            )

        if (
            self.filesystem.artifact.inventory_entry.artifact
            is not self.source.source.filesystem_source.artifact
        ):
            raise ValueError(
                "OTA certificate archive requirement must "
                "preserve exact Parsing filesystem artifact "
                "identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCertificateOccurrence:
    """
    One exact occurrence of one parsed X.509 certificate.

    It originates either directly from a certificate source or from one exact
    OTA ZIP member.
    """

    certificate: ParsedAndroidX509Certificate

    source_requirement: (
        AndroidUniverseCertificateSourceRequirement
        | None
    ) = None

    ota_archive_requirement: (
        AndroidUniverseOtaCertificateArchiveRequirement
        | None
    ) = None

    ota_member: (
        AndroidOtaCertificateArchiveMember
        | None
    ) = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.certificate,
            ParsedAndroidX509Certificate,
        ):
            raise TypeError(
                "certificate must be a "
                "ParsedAndroidX509Certificate"
            )

        direct = (
            self.source_requirement
            is not None
        )

        archived = (
            self.ota_archive_requirement
            is not None
            or self.ota_member
            is not None
        )

        if direct == archived:
            raise ValueError(
                "certificate occurrence must belong to exactly "
                "one direct source or one OTA archive member"
            )

        if archived:
            if (
                self.ota_archive_requirement
                is None
                or self.ota_member
                is None
            ):
                raise ValueError(
                    "OTA certificate occurrence requires both "
                    "archive and member identity"
                )

            if not any(
                member
                is self.ota_member
                for member
                in self.ota_archive_requirement.source.members
            ):
                raise ValueError(
                    "OTA member must preserve exact canonical "
                    "archive-member identity"
                )

            if not any(
                certificate
                is self.certificate
                for certificate
                in self.ota_member.certificates
            ):
                raise ValueError(
                    "OTA certificate occurrence must preserve "
                    "exact member certificate identity"
                )

        elif not any(
            certificate
            is self.certificate
            for certificate
            in self.source_requirement.source.certificates
        ):
            raise ValueError(
                "direct certificate occurrence must preserve "
                "exact source certificate identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCertificateIdentity:
    """
    One exact X.509 identity, grouped strictly by authoritative raw DER.

    Multiple filesystem or OTA occurrences may represent the same certificate.
    """

    sha256_fingerprint: str

    occurrences: tuple[
        AndroidUniverseCertificateOccurrence,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.sha256_fingerprint,
                str,
            )
            or not self.sha256_fingerprint
        ):
            raise ValueError(
                "sha256_fingerprint must be a non-empty string"
            )

        if (
            not isinstance(
                self.occurrences,
                tuple,
            )
            or not self.occurrences
        ):
            raise ValueError(
                "occurrences must be a non-empty tuple"
            )

        first = (
            self.occurrences[0].certificate
        )

        if (
            first.sha256_fingerprint
            != self.sha256_fingerprint
        ):
            raise ValueError(
                "certificate identity fingerprint mismatch"
            )

        if not all(
            occurrence.certificate.raw_der
            == first.raw_der
            and (
                occurrence.certificate
                .sha256_fingerprint
                == self.sha256_fingerprint
            )
            for occurrence
            in self.occurrences
        ):
            raise ValueError(
                "certificate identity may group only exact "
                "identical DER certificate bytes"
            )

    @property
    def certificate(
        self,
    ) -> ParsedAndroidX509Certificate:
        return self.occurrences[0].certificate


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCertificateIssuerRelationship:
    """
    Structural X.509 issuer relationship.

    Candidates are established only through exact issuer Name DER ==
    candidate subject Name DER.

    This does NOT claim that a certificate signature has been
    cryptographically verified.
    """

    child: AndroidUniverseCertificateIdentity

    issuer_candidates: tuple[
        AndroidUniverseCertificateIdentity,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.child,
            AndroidUniverseCertificateIdentity,
        ):
            raise TypeError(
                "child must be an "
                "AndroidUniverseCertificateIdentity"
            )

        if not isinstance(
            self.issuer_candidates,
            tuple,
        ):
            raise TypeError(
                "issuer_candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                AndroidUniverseCertificateIdentity,
            )
            for candidate
            in self.issuer_candidates
        ):
            raise TypeError(
                "issuer_candidates must contain only "
                "AndroidUniverseCertificateIdentity values"
            )

        issuer_der = (
            self.child.certificate.issuer_der
        )

        if not all(
            candidate.certificate.subject_der
            == issuer_der
            for candidate
            in self.issuer_candidates
        ):
            raise ValueError(
                "issuer candidate subject DER must exactly match "
                "child issuer DER"
            )

    @property
    def self_issued(
        self,
    ) -> bool:
        certificate = (
            self.child.certificate
        )

        return (
            certificate.subject_der
            == certificate.issuer_der
        )

    @property
    def resolved_candidate(
        self,
    ) -> bool:
        return (
            len(
                self.issuer_candidates
            )
            == 1
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseCertificateRequirement:
    source: AndroidCertificateParsingResult

    certificate_sources: tuple[
        AndroidUniverseCertificateSourceRequirement,
        ...,
    ]

    ota_archives: tuple[
        AndroidUniverseOtaCertificateArchiveRequirement,
        ...,
    ]

    identities: tuple[
        AndroidUniverseCertificateIdentity,
        ...,
    ]

    issuer_relationships: tuple[
        AndroidUniverseCertificateIssuerRelationship,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidCertificateParsingResult,
        ):
            raise TypeError(
                "source must be an "
                "AndroidCertificateParsingResult"
            )

        if (
            len(
                self.certificate_sources
            )
            != len(
                self.source.sources
            )
        ):
            raise ValueError(
                "certificate requirement must conserve the "
                "complete direct certificate Parsing population"
            )

        if not all(
            requirement.source
            is parsed
            for requirement, parsed
            in zip(
                self.certificate_sources,
                self.source.sources,
                strict=True,
            )
        ):
            raise ValueError(
                "certificate requirement must preserve exact "
                "direct Parsing source identity and order"
            )

        if (
            len(
                self.ota_archives
            )
            != len(
                self.source.ota_archives
            )
        ):
            raise ValueError(
                "certificate requirement must conserve the "
                "complete OTA archive Parsing population"
            )

        if not all(
            requirement.source
            is parsed
            for requirement, parsed
            in zip(
                self.ota_archives,
                self.source.ota_archives,
                strict=True,
            )
        ):
            raise ValueError(
                "certificate requirement must preserve exact "
                "OTA Parsing source identity and order"
            )


def _certificate_role(
    source: ParsedAndroidCertificateSource,
) -> AndroidUniverseCertificateSourceRole:
    path = (
        source.source.android_path.as_posix()
    )

    filename = (
        source.source.android_path.name
    )

    if (
        "/etc/security/cacerts_wfa/"
        in path
    ):
        return (
            AndroidUniverseCertificateSourceRole
            .WIFI_CA_TRUST_STORE_MEMBER
        )

    if (
        "/etc/security/cacerts/"
        in path
    ):
        return (
            AndroidUniverseCertificateSourceRole
            .CA_TRUST_STORE_MEMBER
        )

    if (
        "/etc/security/fsverity/"
        in path
    ):
        return (
            AndroidUniverseCertificateSourceRole
            .FSVERITY_VERIFICATION_CERTIFICATE
        )

    if filename == "cert-chain.crt":
        return (
            AndroidUniverseCertificateSourceRole
            .CERTIFICATE_CHAIN
        )

    return (
        AndroidUniverseCertificateSourceRole
        .OTHER
    )


def _resolve_payload_metadata(
    source_metadata_entry: FilesystemMetadataEntry,
    *,
    inventory_entry,
) -> tuple[
    tuple[
        FilesystemMetadataEntry,
        ...,
    ],
    FilesystemMetadataEntry,
]:
    current = (
        source_metadata_entry
    )

    chain = []
    seen = set()

    while (
        current.entry_type
        is FilesystemEntryType.SYMLINK
    ):
        if current.path in seen:
            raise ValueError(
                "certificate filesystem symlink loop: "
                f"{current.path}"
            )

        seen.add(
            current.path
        )

        chain.append(
            current
        )

        target = (
            current.symlink_target
        )

        if (
            not isinstance(
                target,
                str,
            )
            or not target
        ):
            raise ValueError(
                "certificate symlink is missing target: "
                f"{current.path}"
            )

        if target.startswith("/"):
            target_path = (
                normalize_metadata_path(
                    target
                )
            )
        else:
            target_path = (
                normalize_metadata_path(
                    posixpath.join(
                        posixpath.dirname(
                            current.path
                        ),
                        target,
                    )
                )
            )

        target_entry = (
            inventory_entry
            .result
            .metadata
            .get(
                target_path
            )
        )

        if target_entry is None:
            raise ValueError(
                "certificate symlink target is absent from "
                "canonical filesystem metadata: "
                f"{current.path} -> {target_path}"
            )

        current = (
            target_entry
        )

    if (
        current.entry_type
        is not FilesystemEntryType.FILE
    ):
        raise ValueError(
            "certificate source resolves to non-file entry: "
            f"{source_metadata_entry.path} -> "
            f"{current.path} "
            f"type={current.entry_type.value}"
        )

    return (
        tuple(
            chain
        ),
        current,
    )


def _filesystem_binding(
    model_source,
    *,
    artifact_requirements: (
        AndroidUniverseArtifactRequirementInventory
    ),
) -> AndroidUniverseCertificateFilesystemBinding:
    filesystem_source = (
        model_source.filesystem_source
    )

    try:
        inventory_entry = (
            artifact_requirements
            .source_inventory
            .entry_for_artifact(
                filesystem_source.artifact
            )
        )
    except KeyError as error:
        raise ValueError(
            "certificate source does not preserve canonical "
            "filesystem Artifact identity: "
            f"{model_source.source_name}:"
            f"{model_source.android_path.as_posix()}"
        ) from error

    if (
        inventory_entry.artifact
        is not filesystem_source.artifact
    ):
        raise ValueError(
            "certificate filesystem inventory lookup must "
            "preserve exact Extraction artifact identity"
        )

    metadata_path = (
        inventory_entry
        .filesystem_path_for_materialized_path(
            model_source.host_path
        )
    )

    source_metadata_entry = (
        inventory_entry
        .result
        .metadata
        .get(
            metadata_path
        )
    )

    if source_metadata_entry is None:
        raise ValueError(
            "certificate source has no canonical filesystem "
            "metadata entry: "
            f"{model_source.source_name}:"
            f"{model_source.android_path.as_posix()} "
            f"-> {metadata_path}"
        )

    (
        symlink_chain,
        payload_metadata_entry,
    ) = _resolve_payload_metadata(
        source_metadata_entry,
        inventory_entry=inventory_entry,
    )

    matches = tuple(
        requirement
        for requirement
        in artifact_requirements.requirements
        if (
            requirement.inventory_entry
            is inventory_entry
            and requirement.metadata_entry
            is payload_metadata_entry
        )
    )

    if len(matches) != 1:
        raise ValueError(
            "certificate payload must reconcile to exactly "
            "one canonical Artifact requirement: "
            f"{model_source.source_name}:"
            f"{model_source.android_path.as_posix()} "
            f"source={source_metadata_entry.path} "
            f"payload={payload_metadata_entry.path} "
            f"matches={len(matches)}"
        )

    return (
        AndroidUniverseCertificateFilesystemBinding(
            source_metadata_entry=(
                source_metadata_entry
            ),
            symlink_chain=(
                symlink_chain
            ),
            payload_metadata_entry=(
                payload_metadata_entry
            ),
            artifact=matches[0],
        )
    )


class AndroidUniverseCertificateInterpreter:
    def interpret(
        self,
        parsing: AndroidCertificateParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseCertificateRequirement:
        if not isinstance(
            parsing,
            AndroidCertificateParsingResult,
        ):
            raise TypeError(
                "parsing must be an "
                "AndroidCertificateParsingResult"
            )

        certificate_sources = tuple(
            AndroidUniverseCertificateSourceRequirement(
                source=source,
                role=_certificate_role(
                    source
                ),
                filesystem=_filesystem_binding(
                    source.source,
                    artifact_requirements=(
                        artifact_requirements
                    ),
                ),
            )
            for source
            in parsing.sources
        )

        ota_archives = tuple(
            AndroidUniverseOtaCertificateArchiveRequirement(
                source=archive,
                filesystem=_filesystem_binding(
                    archive.source,
                    artifact_requirements=(
                        artifact_requirements
                    ),
                ),
            )
            for archive
            in parsing.ota_archives
        )

        occurrences = []

        for requirement in certificate_sources:
            for certificate in (
                requirement.source.certificates
            ):
                occurrences.append(
                    AndroidUniverseCertificateOccurrence(
                        certificate=certificate,
                        source_requirement=(
                            requirement
                        ),
                    )
                )

        for requirement in ota_archives:
            for member in (
                requirement.source.members
            ):
                for certificate in (
                    member.certificates
                ):
                    occurrences.append(
                        AndroidUniverseCertificateOccurrence(
                            certificate=certificate,
                            ota_archive_requirement=(
                                requirement
                            ),
                            ota_member=member,
                        )
                    )

        by_fingerprint = {}

        for occurrence in occurrences:
            fingerprint = (
                occurrence.certificate
                .sha256_fingerprint
            )

            by_fingerprint.setdefault(
                fingerprint,
                [],
            ).append(
                occurrence
            )

        identities = tuple(
            AndroidUniverseCertificateIdentity(
                sha256_fingerprint=(
                    fingerprint
                ),
                occurrences=tuple(
                    grouped
                ),
            )
            for fingerprint, grouped
            in sorted(
                by_fingerprint.items()
            )
        )

        by_subject_der = {}

        for identity in identities:
            by_subject_der.setdefault(
                identity.certificate.subject_der,
                [],
            ).append(
                identity
            )

        issuer_relationships = tuple(
            AndroidUniverseCertificateIssuerRelationship(
                child=identity,
                issuer_candidates=tuple(
                    by_subject_der.get(
                        identity.certificate.issuer_der,
                        (),
                    )
                ),
            )
            for identity
            in identities
        )

        return AndroidUniverseCertificateRequirement(
            source=parsing,
            certificate_sources=(
                certificate_sources
            ),
            ota_archives=ota_archives,
            identities=identities,
            issuer_relationships=(
                issuer_relationships
            ),
        )
