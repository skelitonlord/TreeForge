from __future__ import annotations

from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from treeforge.android.parsing.apex.model import (
    AndroidParsedApex,
)


class AndroidApexManifestParseError(
    ValueError,
):
    """
    Raised when literal APEX manifest metadata cannot be recovered.
    """


class AndroidApexManifestParser:
    """
    Parse literal identity metadata from a canonical extracted APEX container.

    Parsing owns semantic decoding only. Extraction owns container
    materialization and provenance; later stages own interpretation.
    """

    _MANIFEST_PATH = "apex_manifest.pb"
    _NAME_FIELD = 1
    _VERSION_FIELD = 2
    _PROVIDE_NATIVE_LIBS_FIELD = 7
    _REQUIRE_NATIVE_LIBS_FIELD = 8
    _JNI_LIBS_FIELD = 9
    _REQUIRE_SHARED_APEX_LIBS_FIELD = 10
    _PROVIDE_SHARED_APEX_LIBS_FIELD = 11
    _SUPPORTS_REBOOTLESS_UPDATE_FIELD = 13

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedApex:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path

        if not source.is_file():
            raise AndroidApexManifestParseError(
                "APEX source does not exist: "
                f"{source}"
            )

        manifest = self._read_manifest(
            source
        )

        (
            apex_name,
            version,
            provide_native_libs,
            require_native_libs,
            jni_libs,
            require_shared_apex_libs,
            provide_shared_apex_libs,
            provide_shared_apex_libs_present,
            supports_rebootless_update,
            supports_rebootless_update_present,
        ) = self._parse_manifest(
            manifest
        )

        return AndroidParsedApex(
            artifact=artifact,
            apex_name=apex_name,
            version=version,
            provide_native_libs=provide_native_libs,
            require_native_libs=require_native_libs,
            jni_libs=jni_libs,
            require_shared_apex_libs=(
                require_shared_apex_libs
            ),
            provide_shared_apex_libs=(
                provide_shared_apex_libs
            ),
            provide_shared_apex_libs_present=(
                provide_shared_apex_libs_present
            ),
            supports_rebootless_update=(
                supports_rebootless_update
            ),
            supports_rebootless_update_present=(
                supports_rebootless_update_present
            ),
        )

    def _read_manifest(
        self,
        source,
    ) -> bytes:
        try:
            with ZipFile(
                source,
                "r",
            ) as archive:
                try:
                    return archive.read(
                        self._MANIFEST_PATH
                    )
                except KeyError as exc:
                    raise AndroidApexManifestParseError(
                        "APEX does not contain "
                        "apex_manifest.pb"
                    ) from exc

        except BadZipFile as exc:
            raise AndroidApexManifestParseError(
                "APEX source is not a valid ZIP container"
            ) from exc

    def _parse_manifest(
        self,
        payload: bytes,
    ) -> tuple[
        str,
        int,
        tuple[
            str,
            ...,
        ],
        tuple[
            str,
            ...,
        ],
        tuple[
            str,
            ...,
        ],
        tuple[
            str,
            ...,
        ],
        bool,
        bool,
        bool,
        bool,
    ]:
        offset = 0

        apex_name: (
            str
            | None
        ) = None

        version: (
            int
            | None
        ) = None

        provide_native_libs: list[
            str
        ] = []

        require_native_libs: list[
            str
        ] = []

        jni_libs: list[
            str
        ] = []

        require_shared_apex_libs: list[
            str
        ] = []

        provide_shared_apex_libs = False
        provide_shared_apex_libs_present = False

        supports_rebootless_update = False
        supports_rebootless_update_present = False

        while offset < len(
            payload
        ):
            key, offset = (
                self._read_varint(
                    payload,
                    offset,
                )
            )

            field_number = (
                key >> 3
            )

            wire_type = (
                key & 0x07
            )

            if (
                field_number
                == self._NAME_FIELD
                and wire_type == 2
            ):
                raw_name, offset = (
                    self._read_length_delimited(
                        payload,
                        offset,
                    )
                )

                apex_name = self._decode_utf8(
                    raw_name,
                    field_name="name",
                )

                continue

            if (
                field_number
                == self._VERSION_FIELD
                and wire_type == 0
            ):
                version, offset = (
                    self._read_varint(
                        payload,
                        offset,
                    )
                )

                continue

            if (
                field_number
                in {
                    self._PROVIDE_NATIVE_LIBS_FIELD,
                    self._REQUIRE_NATIVE_LIBS_FIELD,
                    self._JNI_LIBS_FIELD,
                    self._REQUIRE_SHARED_APEX_LIBS_FIELD,
                }
                and wire_type == 2
            ):
                raw_value, offset = (
                    self._read_length_delimited(
                        payload,
                        offset,
                    )
                )

                value = self._decode_utf8(
                    raw_value,
                    field_name=(
                        "native-library manifest field"
                    ),
                )

                if (
                    field_number
                    == self._PROVIDE_NATIVE_LIBS_FIELD
                ):
                    provide_native_libs.append(
                        value
                    )

                elif (
                    field_number
                    == self._REQUIRE_NATIVE_LIBS_FIELD
                ):
                    require_native_libs.append(
                        value
                    )

                elif (
                    field_number
                    == self._JNI_LIBS_FIELD
                ):
                    jni_libs.append(
                        value
                    )

                else:
                    require_shared_apex_libs.append(
                        value
                    )

                continue

            if (
                field_number
                == self._PROVIDE_SHARED_APEX_LIBS_FIELD
                and wire_type == 0
            ):
                raw_value, offset = (
                    self._read_varint(
                        payload,
                        offset,
                    )
                )

                if raw_value not in {
                    0,
                    1,
                }:
                    raise AndroidApexManifestParseError(
                        "APEX manifest provideSharedApexLibs "
                        "is not a protobuf bool"
                    )

                provide_shared_apex_libs = bool(
                    raw_value
                )
                provide_shared_apex_libs_present = True

                continue

            if (
                field_number
                == self._SUPPORTS_REBOOTLESS_UPDATE_FIELD
                and wire_type == 0
            ):
                raw_value, offset = (
                    self._read_varint(
                        payload,
                        offset,
                    )
                )

                if raw_value not in {
                    0,
                    1,
                }:
                    raise AndroidApexManifestParseError(
                        "APEX manifest supportsRebootlessUpdate "
                        "is not a protobuf bool"
                    )

                supports_rebootless_update = bool(
                    raw_value
                )
                supports_rebootless_update_present = True

                continue

            offset = self._skip_field(
                payload,
                offset,
                wire_type,
            )

        if apex_name is None:
            raise AndroidApexManifestParseError(
                "APEX manifest does not contain a name"
            )

        if version is None:
            raise AndroidApexManifestParseError(
                "APEX manifest does not contain a version"
            )

        return (
            apex_name,
            version,
            tuple(
                provide_native_libs
            ),
            tuple(
                require_native_libs
            ),
            tuple(
                jni_libs
            ),
            tuple(
                require_shared_apex_libs
            ),
            provide_shared_apex_libs,
            provide_shared_apex_libs_present,
            supports_rebootless_update,
            supports_rebootless_update_present,
        )

    def _decode_utf8(
        self,
        payload: bytes,
        *,
        field_name: str,
    ) -> str:
        try:
            value = payload.decode(
                "utf-8"
            )
        except UnicodeDecodeError as exc:
            raise AndroidApexManifestParseError(
                f"APEX manifest {field_name} "
                "is not valid UTF-8"
            ) from exc

        if not value:
            raise AndroidApexManifestParseError(
                f"APEX manifest {field_name} "
                "must not be empty"
            )

        return value

    def _read_varint(
        self,
        payload: bytes,
        offset: int,
    ) -> tuple[
        int,
        int,
    ]:
        result = 0
        shift = 0

        while True:
            if offset >= len(
                payload
            ):
                raise (
                    AndroidApexManifestParseError(
                        "truncated protobuf varint"
                    )
                )

            byte = payload[
                offset
            ]

            offset += 1

            result |= (
                (byte & 0x7F)
                << shift
            )

            if not (
                byte & 0x80
            ):
                return (
                    result,
                    offset,
                )

            shift += 7

            if shift >= 70:
                raise (
                    AndroidApexManifestParseError(
                        "invalid protobuf varint"
                    )
                )

    def _read_length_delimited(
        self,
        payload: bytes,
        offset: int,
    ) -> tuple[
        bytes,
        int,
    ]:
        length, offset = (
            self._read_varint(
                payload,
                offset,
            )
        )

        end = (
            offset
            + length
        )

        if end > len(
            payload
        ):
            raise (
                AndroidApexManifestParseError(
                    "truncated length-delimited protobuf field"
                )
            )

        return (
            payload[
                offset:end
            ],
            end,
        )

    def _skip_field(
        self,
        payload: bytes,
        offset: int,
        wire_type: int,
    ) -> int:
        if wire_type == 0:
            _, offset = (
                self._read_varint(
                    payload,
                    offset,
                )
            )

            return offset

        if wire_type == 1:
            end = (
                offset
                + 8
            )

        elif wire_type == 2:
            length, offset = (
                self._read_varint(
                    payload,
                    offset,
                )
            )

            end = (
                offset
                + length
            )

        elif wire_type == 5:
            end = (
                offset
                + 4
            )

        else:
            raise (
                AndroidApexManifestParseError(
                    "unsupported protobuf wire type: "
                    f"{wire_type}"
                )
            )

        if end > len(
            payload
        ):
            raise (
                AndroidApexManifestParseError(
                    "truncated protobuf field"
                )
            )

        return end