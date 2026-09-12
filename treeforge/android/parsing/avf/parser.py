from __future__ import annotations

import json
from json import JSONDecodeError
from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.parsing.avf.model import (
    AndroidAvfVmConfigApex,
    AndroidAvfVmConfigCandidateDisposition,
    AndroidAvfVmConfigExtraApk,
    AndroidAvfVmConfigOs,
    AndroidAvfVmConfigParsingResult,
    AndroidAvfVmConfigSource,
    AndroidAvfVmConfigTask,
    ParsedAndroidAvfVmConfig,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


class AndroidAvfVmConfigParseError(
    ValueError,
):
    """
    Raised when a source positively identified as an AVF VM config cannot
    be represented faithfully.
    """


class AndroidAvfVmConfigParser:
    """
    Discover and literally decode AVF VM payload configurations embedded
    in APK ZIP containers.

    Candidate APK discovery is structural and generic. Parsing examines JSON
    assets and accepts only objects matching the intrinsic AVF VM-config
    shape: an ``os`` object and executable ``task`` object.

    No device, package, OS-name, APEX-name, Android-version, or guest-runtime
    knowledge participates here.
    """

    _KNOWN_FIELDS = frozenset(
        {
            "version",
            "os",
            "task",
            "prefer_staged",
            "apexes",
            "extra_apks",
            "export_tombstones",
            "enable_authfs",
            "hugepages",
        }
    )

    def parse(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> AndroidAvfVmConfigParsingResult:
        if not isinstance(
            filesystems,
            tuple,
        ):
            raise TypeError(
                "filesystems must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidParserFilesystemSource,
            )
            for value
            in filesystems
        ):
            raise TypeError(
                "filesystems must contain only "
                "AndroidParserFilesystemSource entries"
            )

        parsed: list[
            ParsedAndroidAvfVmConfig
        ] = []

        dispositions: list[
            AndroidAvfVmConfigCandidateDisposition
        ] = []

        seen = set()
        seen_apks = set()

        for filesystem_source in sorted(
            filesystems,
            key=lambda value: (
                value.source_name
            ),
        ):
            for view in filesystem_source.views:
                candidates = sorted(
                    view.filesystem.walk(),
                    key=lambda path: (
                        path.as_posix()
                    ),
                )

                for apk_host_path in candidates:
                    if (
                        not apk_host_path.is_file()
                        or apk_host_path.is_symlink()
                        or apk_host_path.suffix.lower()
                        != ".apk"
                    ):
                        continue

                    apk_android_path = (
                        view.android_path_for(
                            apk_host_path
                        )
                    )

                    apk_identity = (
                        filesystem_source.source_name,
                        apk_android_path,
                    )

                    if apk_identity in seen_apks:
                        continue

                    seen_apks.add(
                        apk_identity
                    )

                    (
                        apk_parsed,
                        apk_dispositions,
                    ) = self._parse_apk(
                        filesystem_source=(
                            filesystem_source
                        ),
                        apk_host_path=(
                            apk_host_path
                        ),
                        apk_android_path=(
                            apk_android_path
                        ),
                        seen=seen,
                    )

                    parsed.extend(
                        apk_parsed
                    )

                    dispositions.extend(
                        apk_dispositions
                    )

        return AndroidAvfVmConfigParsingResult(
            configurations=tuple(
                sorted(
                    parsed,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            ),
            candidates=tuple(
                sorted(
                    dispositions,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            ),
        )

    def _parse_apk(
        self,
        *,
        filesystem_source,
        apk_host_path,
        apk_android_path,
        seen: set,
    ) -> tuple[
        tuple[
            ParsedAndroidAvfVmConfig,
            ...,
        ],
        tuple[
            AndroidAvfVmConfigCandidateDisposition,
            ...,
        ],
    ]:
        results: list[
            ParsedAndroidAvfVmConfig
        ] = []

        dispositions: list[
            AndroidAvfVmConfigCandidateDisposition
        ] = []

        try:
            with ZipFile(
                apk_host_path,
                "r",
            ) as archive:
                members = tuple(
                    sorted(
                        (
                            (
                                index,
                                info,
                            )
                            for index, info
                            in enumerate(
                                archive.infolist()
                            )
                            if (
                                not info.is_dir()
                                and info.filename.startswith(
                                    "assets/"
                                )
                                and info.filename.lower().endswith(
                                    ".json"
                                )
                            )
                        ),
                        key=lambda value: (
                            value[1].filename,
                            value[0],
                        ),
                    )
                )

                for (
                    member_index,
                    info,
                ) in members:
                    raw = archive.read(
                        info
                    )

                    source = (
                        AndroidAvfVmConfigSource(
                            filesystem_source=(
                                filesystem_source
                            ),
                            apk_android_path=(
                                apk_android_path
                            ),
                            apk_host_path=(
                                apk_host_path
                            ),
                            member_path=(
                                info.filename
                            ),
                            member_index=(
                                member_index
                            ),
                        )
                    )

                    identity = (
                        source.identity_key
                    )

                    if identity in seen:
                        raise AndroidAvfVmConfigParseError(
                            "duplicate exact AVF candidate identity: "
                            f"{identity!r}"
                        )

                    seen.add(
                        identity
                    )

                    try:
                        text_value = raw.decode(
                            "utf-8"
                        )
                        decoded_value = json.loads(
                            text_value
                        )
                    except (
                        UnicodeDecodeError,
                        JSONDecodeError,
                    ) as error:
                        dispositions.append(
                            AndroidAvfVmConfigCandidateDisposition(
                                source=source,
                                raw=raw,
                                disposition="invalid_json",
                                reason=str(
                                    error
                                ),
                            )
                        )
                        continue

                    if not isinstance(
                        decoded_value,
                        dict,
                    ):
                        dispositions.append(
                            AndroidAvfVmConfigCandidateDisposition(
                                source=source,
                                raw=raw,
                                disposition="non_object_json",
                                reason=(
                                    "JSON root is not an object"
                                ),
                            )
                        )
                        continue

                    if not self._looks_like_vm_config(
                        decoded_value
                    ):
                        dispositions.append(
                            AndroidAvfVmConfigCandidateDisposition(
                                source=source,
                                raw=raw,
                                disposition="not_vm_config",
                                reason=(
                                    "JSON object does not match "
                                    "intrinsic AVF VM-config shape"
                                ),
                            )
                        )
                        continue

                    parsed = self._parse_config(
                        source=source,
                        raw=raw,
                        decoded=decoded_value,
                    )

                    dispositions.append(
                        AndroidAvfVmConfigCandidateDisposition(
                            source=source,
                            raw=raw,
                            disposition="parsed",
                            parsed=parsed,
                        )
                    )

                    results.append(
                        parsed
                    )

        except BadZipFile:
            #
            # APK suffix alone is not positive AVF evidence. APK candidate
            # conservation is owned by the APK parser; AVF candidate
            # conservation begins at structurally accessible assets/*.json
            # ZIP members.
            #
            return (
                (),
                (),
            )

        except OSError as error:
            raise AndroidAvfVmConfigParseError(
                "unable to read APK candidate: "
                f"{apk_host_path}"
            ) from error

        return (
            tuple(
                results
            ),
            tuple(
                dispositions
            ),
        )

    @staticmethod
    def _looks_like_vm_config(
        value: dict,
    ) -> bool:
        os_value = value.get(
            "os"
        )

        task_value = value.get(
            "task"
        )

        return (
            isinstance(
                os_value,
                dict,
            )
            and isinstance(
                os_value.get(
                    "name"
                ),
                str,
            )
            and bool(
                os_value.get(
                    "name"
                )
            )
            and isinstance(
                task_value,
                dict,
            )
            and isinstance(
                task_value.get(
                    "type"
                ),
                str,
            )
            and bool(
                task_value.get(
                    "type"
                )
            )
            and isinstance(
                task_value.get(
                    "command"
                ),
                str,
            )
            and bool(
                task_value.get(
                    "command"
                )
            )
        )

    def _parse_config(
        self,
        *,
        source: AndroidAvfVmConfigSource,
        raw: bytes,
        decoded: dict,
    ) -> ParsedAndroidAvfVmConfig:
        version = decoded.get(
            "version"
        )

        if (
            version is not None
            and (
                isinstance(
                    version,
                    bool,
                )
                or not isinstance(
                    version,
                    int,
                )
            )
        ):
            raise AndroidAvfVmConfigParseError(
                "AVF VM config version must "
                "be an integer"
            )

        os_value = decoded[
            "os"
        ]

        task_value = decoded[
            "task"
        ]

        apexes = self._parse_apexes(
            decoded.get(
                "apexes",
                (),
            )
        )

        extra_apks = self._parse_extra_apks(
            decoded.get(
                "extra_apks",
                (),
            )
        )

        return ParsedAndroidAvfVmConfig(
            source=source,
            raw=raw,
            version=version,
            os=AndroidAvfVmConfigOs(
                name=os_value[
                    "name"
                ],
            ),
            task=AndroidAvfVmConfigTask(
                task_type=task_value[
                    "type"
                ],
                command=task_value[
                    "command"
                ],
            ),
            prefer_staged=(
                self._optional_bool(
                    decoded,
                    "prefer_staged",
                )
            ),
            apexes=apexes,
            extra_apks=extra_apks,
            export_tombstones=(
                self._optional_bool(
                    decoded,
                    "export_tombstones",
                )
            ),
            enable_authfs=(
                self._optional_bool(
                    decoded,
                    "enable_authfs",
                )
            ),
            hugepages=(
                self._optional_bool(
                    decoded,
                    "hugepages",
                )
            ),
            unknown_fields=tuple(
                sorted(
                    key
                    for key
                    in decoded
                    if key not in self._KNOWN_FIELDS
                )
            ),
        )

    @staticmethod
    def _optional_bool(
        decoded: dict,
        name: str,
    ) -> bool | None:
        if name not in decoded:
            return None

        value = decoded[
            name
        ]

        if not isinstance(
            value,
            bool,
        ):
            raise AndroidAvfVmConfigParseError(
                f"{name} must be a JSON bool"
            )

        return value

    @staticmethod
    def _parse_apexes(
        value,
    ) -> tuple[
        AndroidAvfVmConfigApex,
        ...,
    ]:
        if value is None:
            return ()

        if not isinstance(
            value,
            list,
        ):
            raise AndroidAvfVmConfigParseError(
                "apexes must be a JSON array"
            )

        parsed = []

        for entry in value:
            if isinstance(
                entry,
                str,
            ):
                name = entry
            elif isinstance(
                entry,
                dict,
            ):
                name = entry.get(
                    "name"
                )
            else:
                raise AndroidAvfVmConfigParseError(
                    "APEX entry must be a string "
                    "or object"
                )

            if (
                not isinstance(
                    name,
                    str,
                )
                or not name
            ):
                raise AndroidAvfVmConfigParseError(
                    "APEX entry must contain "
                    "a non-empty name"
                )

            parsed.append(
                AndroidAvfVmConfigApex(
                    name=name
                )
            )

        return tuple(
            parsed
        )

    @staticmethod
    def _parse_extra_apks(
        value,
    ) -> tuple[
        AndroidAvfVmConfigExtraApk,
        ...,
    ]:
        if value is None:
            return ()

        if not isinstance(
            value,
            list,
        ):
            raise AndroidAvfVmConfigParseError(
                "extra_apks must be a JSON array"
            )

        parsed = []

        for entry in value:
            if isinstance(
                entry,
                str,
            ):
                path = entry
            elif isinstance(
                entry,
                dict,
            ):
                path = entry.get(
                    "path"
                )
            else:
                raise AndroidAvfVmConfigParseError(
                    "extra APK entry must be "
                    "a string or object"
                )

            if (
                not isinstance(
                    path,
                    str,
                )
                or not path
            ):
                raise AndroidAvfVmConfigParseError(
                    "extra APK entry must contain "
                    "a non-empty path"
                )

            parsed.append(
                AndroidAvfVmConfigExtraApk(
                    path=path
                )
            )

        return tuple(
            parsed
        )
