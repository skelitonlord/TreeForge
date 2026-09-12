from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


class AndroidCertificateEncoding(StrEnum):
    PEM = "pem"
    DER = "der"


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidX509Certificate:
    """
    One exact X.509 certificate recovered from a source or archive member.

    Raw DER is authoritative certificate identity. Decoded ASN.1 fields are
    intrinsic structural evidence only.
    """

    index: int

    raw_der: bytes

    sha256_fingerprint: str
    sha1_fingerprint: str

    serial_number: int

    signature_algorithm_oid: str

    issuer_der: bytes
    subject_der: bytes

    not_before_raw: str
    not_after_raw: str

    subject_public_key_algorithm_oid: str
    subject_public_key_info_sha256: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if (
            not isinstance(self.raw_der, bytes)
            or not self.raw_der
        ):
            raise ValueError(
                "raw_der must be non-empty bytes"
            )

        for field_name, value in (
            (
                "sha256_fingerprint",
                self.sha256_fingerprint,
            ),
            (
                "sha1_fingerprint",
                self.sha1_fingerprint,
            ),
            (
                "signature_algorithm_oid",
                self.signature_algorithm_oid,
            ),
            (
                "not_before_raw",
                self.not_before_raw,
            ),
            (
                "not_after_raw",
                self.not_after_raw,
            ),
            (
                "subject_public_key_algorithm_oid",
                self.subject_public_key_algorithm_oid,
            ),
            (
                "subject_public_key_info_sha256",
                self.subject_public_key_info_sha256,
            ),
        ):
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if (
            isinstance(self.serial_number, bool)
            or not isinstance(self.serial_number, int)
            or self.serial_number < 0
        ):
            raise ValueError(
                "serial_number must be a non-negative integer"
            )

        if (
            not isinstance(self.issuer_der, bytes)
            or not self.issuer_der
        ):
            raise ValueError(
                "issuer_der must be non-empty bytes"
            )

        if (
            not isinstance(self.subject_der, bytes)
            or not self.subject_der
        ):
            raise ValueError(
                "subject_der must be non-empty bytes"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidCertificateSource:
    """
    One canonical filesystem certificate source.

    A source may contain one certificate or an ordered PEM certificate chain.
    """

    source: AndroidModelSource

    raw: bytes
    encoding: AndroidCertificateEncoding

    certificates: tuple[
        ParsedAndroidX509Certificate,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            self.source.kind
            is not AndroidModelSourceKind.CERTIFICATE
        ):
            raise ValueError(
                "source must be a CERTIFICATE source"
            )

        if (
            not isinstance(self.raw, bytes)
            or not self.raw
        ):
            raise ValueError(
                "raw must be non-empty bytes"
            )

        if not isinstance(
            self.encoding,
            AndroidCertificateEncoding,
        ):
            raise TypeError(
                "encoding must be an AndroidCertificateEncoding"
            )

        if (
            not isinstance(self.certificates, tuple)
            or not self.certificates
            or not all(
                isinstance(
                    certificate,
                    ParsedAndroidX509Certificate,
                )
                for certificate in self.certificates
            )
        ):
            raise TypeError(
                "certificates must contain "
                "ParsedAndroidX509Certificate values"
            )

        if tuple(
            certificate.index
            for certificate in self.certificates
        ) != tuple(
            range(
                len(self.certificates)
            )
        ):
            raise ValueError(
                "certificates must preserve canonical source order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidOtaCertificateArchiveMember:
    """
    One exact ZIP member from an OTA certificate archive.
    """

    index: int
    filename: str

    compression_method: int
    crc32: int
    compressed_size: int
    uncompressed_size: int

    sha256: str

    is_directory: bool = False
    certificate_parse_error: str | None = None

    certificates: tuple[
        ParsedAndroidX509Certificate,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("index", self.index),
            (
                "compression_method",
                self.compression_method,
            ),
            ("crc32", self.crc32),
            (
                "compressed_size",
                self.compressed_size,
            ),
            (
                "uncompressed_size",
                self.uncompressed_size,
            ),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer"
                )

        if (
            not isinstance(self.filename, str)
            or not self.filename
        ):
            raise ValueError(
                "filename must be a non-empty string"
            )

        if (
            not isinstance(self.sha256, str)
            or not self.sha256
        ):
            raise ValueError(
                "sha256 must be a non-empty string"
            )

        if not isinstance(
            self.is_directory,
            bool,
        ):
            raise TypeError(
                "is_directory must be a bool"
            )

        if (
            self.certificate_parse_error
            is not None
            and (
                not isinstance(
                    self.certificate_parse_error,
                    str,
                )
                or not self.certificate_parse_error
            )
        ):
            raise ValueError(
                "certificate_parse_error must be None or "
                "a non-empty string"
            )

        if (
            self.is_directory
            and self.certificates
        ):
            raise ValueError(
                "OTA archive directory member cannot contain "
                "parsed certificates"
            )

        if (
            self.is_directory
            and self.certificate_parse_error
            is not None
        ):
            raise ValueError(
                "OTA archive directory member cannot have "
                "a certificate parse error"
            )

        if (
            self.certificates
            and self.certificate_parse_error
            is not None
        ):
            raise ValueError(
                "parsed OTA certificate member cannot also "
                "carry a certificate parse error"
            )

        if (
            not isinstance(self.certificates, tuple)
            or not all(
                isinstance(
                    certificate,
                    ParsedAndroidX509Certificate,
                )
                for certificate in self.certificates
            )
        ):
            raise TypeError(
                "certificates must contain only "
                "ParsedAndroidX509Certificate values"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidOtaCertificateArchive:
    """
    One canonical installed OTA certificate ZIP archive.

    Parsing records exact archive/member identity and any X.509 certificates
    contained within. OTA verification policy remains downstream.
    """

    source: AndroidModelSource
    file_size: int

    members: tuple[
        AndroidOtaCertificateArchiveMember,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            self.source.kind
            is not AndroidModelSourceKind
            .OTA_CERTIFICATE_ARCHIVE
        ):
            raise ValueError(
                "source must be an OTA_CERTIFICATE_ARCHIVE source"
            )

        if (
            isinstance(self.file_size, bool)
            or not isinstance(self.file_size, int)
            or self.file_size < 1
        ):
            raise ValueError(
                "file_size must be a positive integer"
            )

        if (
            not isinstance(self.members, tuple)
            or not self.members
            or not all(
                isinstance(
                    member,
                    AndroidOtaCertificateArchiveMember,
                )
                for member in self.members
            )
        ):
            raise TypeError(
                "members must contain "
                "AndroidOtaCertificateArchiveMember values"
            )

        if tuple(
            member.index
            for member in self.members
        ) != tuple(
            range(
                len(self.members)
            )
        ):
            raise ValueError(
                "OTA archive members must preserve ZIP order"
            )

    @property
    def certificate_count(self) -> int:
        return sum(
            len(
                member.certificates
            )
            for member in self.members
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidCertificateParsingResult:
    """
    Canonical deterministic certificate/security Parsing population.
    """

    sources: tuple[
        ParsedAndroidCertificateSource,
        ...,
    ] = ()

    ota_archives: tuple[
        ParsedAndroidOtaCertificateArchive,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sources, tuple)
            or not all(
                isinstance(
                    value,
                    ParsedAndroidCertificateSource,
                )
                for value in self.sources
            )
        ):
            raise TypeError(
                "sources must contain "
                "ParsedAndroidCertificateSource values"
            )

        if (
            not isinstance(
                self.ota_archives,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    ParsedAndroidOtaCertificateArchive,
                )
                for value in self.ota_archives
            )
        ):
            raise TypeError(
                "ota_archives must contain "
                "ParsedAndroidOtaCertificateArchive values"
            )

        canonical_sources = tuple(
            sorted(
                self.sources,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        canonical_archives = tuple(
            sorted(
                self.ota_archives,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if canonical_sources != self.sources:
            raise ValueError(
                "certificate sources must use canonical source order"
            )

        if canonical_archives != self.ota_archives:
            raise ValueError(
                "OTA certificate archives must use canonical source order"
            )

        certificate_source_object_ids = tuple(
            id(
                value.source
            )
            for value
            in self.sources
        )

        if len(
            certificate_source_object_ids
        ) != len(
            set(
                certificate_source_object_ids
            )
        ):
            raise ValueError(
                "certificate sources must preserve unique canonical "
                "AndroidModelSource object identities"
            )

        ota_source_object_ids = tuple(
            id(
                value.source
            )
            for value
            in self.ota_archives
        )

        if len(
            ota_source_object_ids
        ) != len(
            set(
                ota_source_object_ids
            )
        ):
            raise ValueError(
                "OTA certificate archives must preserve unique canonical "
                "AndroidModelSource object identities"
            )

    @property
    def source_count(self) -> int:
        return len(
            self.sources
        )

    @property
    def ota_archive_count(self) -> int:
        return len(
            self.ota_archives
        )

    @property
    def certificate_count(self) -> int:
        return (
            sum(
                len(
                    source.certificates
                )
                for source in self.sources
            )
            + sum(
                archive.certificate_count
                for archive in self.ota_archives
            )
        )
