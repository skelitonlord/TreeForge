from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.parsing.certificate.model import (
    AndroidCertificateEncoding,
    AndroidCertificateParsingResult,
    AndroidOtaCertificateArchiveMember,
    ParsedAndroidCertificateSource,
    ParsedAndroidOtaCertificateArchive,
    ParsedAndroidX509Certificate,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


class AndroidCertificateParsingError(ValueError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class _Tlv:
    tag: int
    start: int
    content_start: int
    content_end: int
    end: int


_PEM_CERTIFICATE = re.compile(
    rb"-----BEGIN CERTIFICATE-----\s*"
    rb"([A-Za-z0-9+/=\r\n\t ]+?)"
    rb"\s*-----END CERTIFICATE-----"
)


def _read_tlv(
    data: bytes,
    offset: int,
) -> _Tlv:
    if (
        offset < 0
        or offset >= len(data)
    ):
        raise AndroidCertificateParsingError(
            "truncated ASN.1 tag"
        )

    start = offset
    tag = data[offset]
    offset += 1

    if offset >= len(data):
        raise AndroidCertificateParsingError(
            "truncated ASN.1 length"
        )

    first_length = data[offset]
    offset += 1

    if (
        first_length
        & 0x80
    ) == 0:
        length = first_length
    else:
        length_octets = (
            first_length
            & 0x7F
        )

        if (
            length_octets == 0
            or length_octets > 4
            or offset + length_octets
            > len(data)
        ):
            raise AndroidCertificateParsingError(
                "unsupported ASN.1 length"
            )

        length = int.from_bytes(
            data[
                offset:
                offset + length_octets
            ],
            "big",
        )

        offset += length_octets

    content_start = offset
    content_end = (
        content_start
        + length
    )

    if content_end > len(data):
        raise AndroidCertificateParsingError(
            "truncated ASN.1 content"
        )

    return _Tlv(
        tag=tag,
        start=start,
        content_start=content_start,
        content_end=content_end,
        end=content_end,
    )


def _decode_oid(
    encoded: bytes,
) -> str:
    if not encoded:
        raise AndroidCertificateParsingError(
            "empty ASN.1 OID"
        )

    first = encoded[0]

    if first < 40:
        values = [
            0,
            first,
        ]
    elif first < 80:
        values = [
            1,
            first - 40,
        ]
    else:
        values = [
            2,
            first - 80,
        ]

    value = 0

    for byte in encoded[1:]:
        value = (
            value << 7
        ) | (
            byte & 0x7F
        )

        if (
            byte
            & 0x80
        ) == 0:
            values.append(
                value
            )
            value = 0

    if value != 0:
        raise AndroidCertificateParsingError(
            "truncated ASN.1 OID"
        )

    return ".".join(
        str(
            item
        )
        for item in values
    )


def _algorithm_oid(
    data: bytes,
    sequence: _Tlv,
) -> str:
    if sequence.tag != 0x30:
        raise AndroidCertificateParsingError(
            "AlgorithmIdentifier is not a SEQUENCE"
        )

    oid = _read_tlv(
        data,
        sequence.content_start,
    )

    if oid.tag != 0x06:
        raise AndroidCertificateParsingError(
            "AlgorithmIdentifier contains no OID"
        )

    return _decode_oid(
        data[
            oid.content_start:
            oid.content_end
        ]
    )


def _parse_der_certificate(
    raw_der: bytes,
    *,
    index: int,
) -> ParsedAndroidX509Certificate:
    outer = _read_tlv(
        raw_der,
        0,
    )

    if (
        outer.tag != 0x30
        or outer.end != len(raw_der)
    ):
        raise AndroidCertificateParsingError(
            "X.509 certificate is not one canonical DER SEQUENCE"
        )

    tbs = _read_tlv(
        raw_der,
        outer.content_start,
    )

    if tbs.tag != 0x30:
        raise AndroidCertificateParsingError(
            "X.509 TBSCertificate is not a SEQUENCE"
        )

    cursor = tbs.content_start

    first = _read_tlv(
        raw_der,
        cursor,
    )

    if first.tag == 0xA0:
        cursor = first.end

    serial = _read_tlv(
        raw_der,
        cursor,
    )

    if serial.tag != 0x02:
        raise AndroidCertificateParsingError(
            "X.509 certificate contains no serial INTEGER"
        )

    serial_number = int.from_bytes(
        raw_der[
            serial.content_start:
            serial.content_end
        ],
        "big",
        signed=False,
    )

    cursor = serial.end

    signature_algorithm = _read_tlv(
        raw_der,
        cursor,
    )

    signature_algorithm_oid = (
        _algorithm_oid(
            raw_der,
            signature_algorithm,
        )
    )

    cursor = signature_algorithm.end

    issuer = _read_tlv(
        raw_der,
        cursor,
    )

    if issuer.tag != 0x30:
        raise AndroidCertificateParsingError(
            "X.509 issuer Name is not a SEQUENCE"
        )

    issuer_der = raw_der[
        issuer.start:
        issuer.end
    ]

    cursor = issuer.end

    validity = _read_tlv(
        raw_der,
        cursor,
    )

    if validity.tag != 0x30:
        raise AndroidCertificateParsingError(
            "X.509 validity is not a SEQUENCE"
        )

    not_before = _read_tlv(
        raw_der,
        validity.content_start,
    )

    not_after = _read_tlv(
        raw_der,
        not_before.end,
    )

    if (
        not_before.tag
        not in {
            0x17,
            0x18,
        }
        or not_after.tag
        not in {
            0x17,
            0x18,
        }
    ):
        raise AndroidCertificateParsingError(
            "X.509 validity contains unsupported time encoding"
        )

    try:
        not_before_raw = raw_der[
            not_before.content_start:
            not_before.content_end
        ].decode(
            "ascii"
        )

        not_after_raw = raw_der[
            not_after.content_start:
            not_after.content_end
        ].decode(
            "ascii"
        )
    except UnicodeDecodeError as error:
        raise AndroidCertificateParsingError(
            "X.509 validity time is not ASCII"
        ) from error

    cursor = validity.end

    subject = _read_tlv(
        raw_der,
        cursor,
    )

    if subject.tag != 0x30:
        raise AndroidCertificateParsingError(
            "X.509 subject Name is not a SEQUENCE"
        )

    subject_der = raw_der[
        subject.start:
        subject.end
    ]

    cursor = subject.end

    spki = _read_tlv(
        raw_der,
        cursor,
    )

    if spki.tag != 0x30:
        raise AndroidCertificateParsingError(
            "X.509 SubjectPublicKeyInfo is not a SEQUENCE"
        )

    spki_algorithm = _read_tlv(
        raw_der,
        spki.content_start,
    )

    spki_algorithm_oid = (
        _algorithm_oid(
            raw_der,
            spki_algorithm,
        )
    )

    spki_der = raw_der[
        spki.start:
        spki.end
    ]

    return ParsedAndroidX509Certificate(
        index=index,
        raw_der=raw_der,
        sha256_fingerprint=(
            hashlib.sha256(
                raw_der
            ).hexdigest()
        ),
        sha1_fingerprint=(
            hashlib.sha1(
                raw_der
            ).hexdigest()
        ),
        serial_number=serial_number,
        signature_algorithm_oid=(
            signature_algorithm_oid
        ),
        issuer_der=issuer_der,
        subject_der=subject_der,
        not_before_raw=(
            not_before_raw
        ),
        not_after_raw=(
            not_after_raw
        ),
        subject_public_key_algorithm_oid=(
            spki_algorithm_oid
        ),
        subject_public_key_info_sha256=(
            hashlib.sha256(
                spki_der
            ).hexdigest()
        ),
    )


def _decode_certificates(
    raw: bytes,
) -> tuple[
    AndroidCertificateEncoding,
    tuple[
        ParsedAndroidX509Certificate,
        ...,
    ],
]:
    matches = tuple(
        _PEM_CERTIFICATE.finditer(
            raw
        )
    )

    if matches:
        certificates = []

        for index, match in enumerate(
            matches
        ):
            payload = re.sub(
                rb"\s+",
                b"",
                match.group(1),
            )

            try:
                raw_der = base64.b64decode(
                    payload,
                    validate=True,
                )
            except ValueError as error:
                raise AndroidCertificateParsingError(
                    "invalid PEM certificate base64"
                ) from error

            certificates.append(
                _parse_der_certificate(
                    raw_der,
                    index=index,
                )
            )

        return (
            AndroidCertificateEncoding.PEM,
            tuple(
                certificates
            ),
        )

    return (
        AndroidCertificateEncoding.DER,
        (
            _parse_der_certificate(
                raw,
                index=0,
            ),
        ),
    )


class AndroidCertificateParser:
    """
    Parse intrinsic X.509 and OTA certificate-container evidence.

    Parsing never infers trust policy, signing ownership, private keys,
    update authorization, or source-tree realization.
    """

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidCertificateParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        certificate_sources = tuple(
            source
            for source
            in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.CERTIFICATE
            )
        )

        ota_archive_sources = tuple(
            source
            for source
            in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .OTA_CERTIFICATE_ARCHIVE
            )
        )

        sources = tuple(
            self._parse_certificate_source(
                source
            )
            for source
            in certificate_sources
        )

        ota_archives = tuple(
            self._parse_ota_archive(
                source
            )
            for source
            in ota_archive_sources
        )

        expected_certificate_source_ids = {
            id(source)
            for source
            in certificate_sources
        }

        actual_certificate_source_ids = {
            id(parsed.source)
            for parsed
            in sources
        }

        if (
            expected_certificate_source_ids
            != actual_certificate_source_ids
        ):
            raise AndroidCertificateParsingError(
                "certificate Parsing failed to conserve the "
                "complete canonical CERTIFICATE source population"
            )

        if len(
            actual_certificate_source_ids
        ) != len(
            sources
        ):
            raise AndroidCertificateParsingError(
                "certificate Parsing duplicated a canonical "
                "CERTIFICATE AndroidModelSource"
            )

        expected_ota_source_ids = {
            id(source)
            for source
            in ota_archive_sources
        }

        actual_ota_source_ids = {
            id(parsed.source)
            for parsed
            in ota_archives
        }

        if (
            expected_ota_source_ids
            != actual_ota_source_ids
        ):
            raise AndroidCertificateParsingError(
                "certificate Parsing failed to conserve the "
                "complete canonical OTA_CERTIFICATE_ARCHIVE "
                "source population"
            )

        if len(
            actual_ota_source_ids
        ) != len(
            ota_archives
        ):
            raise AndroidCertificateParsingError(
                "certificate Parsing duplicated a canonical "
                "OTA_CERTIFICATE_ARCHIVE AndroidModelSource"
            )

        return AndroidCertificateParsingResult(
            sources=tuple(
                sorted(
                    sources,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            ),
            ota_archives=tuple(
                sorted(
                    ota_archives,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            ),
        )

    @staticmethod
    def _parse_certificate_source(
        source: AndroidModelSource,
    ) -> ParsedAndroidCertificateSource:
        try:
            raw = (
                source.host_path.read_bytes()
            )
        except OSError as error:
            raise AndroidCertificateParsingError(
                "unable to read certificate source "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        try:
            encoding, certificates = (
                _decode_certificates(
                    raw
                )
            )
        except AndroidCertificateParsingError as error:
            raise AndroidCertificateParsingError(
                "unable to parse certificate source "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        return ParsedAndroidCertificateSource(
            source=source,
            raw=raw,
            encoding=encoding,
            certificates=certificates,
        )

    @staticmethod
    def _parse_ota_archive(
        source: AndroidModelSource,
    ) -> ParsedAndroidOtaCertificateArchive:
        try:
            file_size = (
                source.host_path.stat().st_size
            )

            with ZipFile(
                source.host_path,
                "r",
            ) as archive:
                members = []

                for index, info in enumerate(
                    archive.infolist()
                ):
                    is_directory = (
                        info.is_dir()
                    )

                    raw = (
                        b""
                        if is_directory
                        else archive.read(
                            info
                        )
                    )

                    certificates = ()
                    certificate_parse_error = None

                    if not is_directory:
                        try:
                            _, certificates = (
                                _decode_certificates(
                                    raw
                                )
                            )
                        except AndroidCertificateParsingError as error:
                            certificate_parse_error = str(
                                error
                            )

                    members.append(
                        AndroidOtaCertificateArchiveMember(
                            index=index,
                            filename=(
                                info.filename
                            ),
                            compression_method=(
                                info.compress_type
                            ),
                            crc32=info.CRC,
                            compressed_size=(
                                info.compress_size
                            ),
                            uncompressed_size=(
                                info.file_size
                            ),
                            sha256=(
                                hashlib.sha256(
                                    raw
                                ).hexdigest()
                            ),
                            is_directory=(
                                is_directory
                            ),
                            certificate_parse_error=(
                                certificate_parse_error
                            ),
                            certificates=(
                                certificates
                            ),
                        )
                    )

        except (
            OSError,
            BadZipFile,
            KeyError,
        ) as error:
            raise AndroidCertificateParsingError(
                "unable to parse OTA certificate archive "
                f"{source.source_name}:"
                f"{source.android_path}: {error}"
            ) from error

        if not members:
            raise AndroidCertificateParsingError(
                "OTA certificate archive contains no members"
            )

        return ParsedAndroidOtaCertificateArchive(
            source=source,
            file_size=file_size,
            members=tuple(
                members
            ),
        )
