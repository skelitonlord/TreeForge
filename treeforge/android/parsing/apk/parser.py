from __future__ import annotations

from gzip import GzipFile
from io import BytesIO
from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.parsing.apk.axml import (
    AndroidBinaryXmlError,
    AndroidBinaryXmlParser,
)
from treeforge.android.parsing.apk.model import (
    AndroidApkArchiveMember,
    AndroidApkCandidateDisposition,
    AndroidApkManifestValue,
    AndroidApkOverlayManifest,
    AndroidApkParsingResult,
    AndroidApkSource,
    ParsedAndroidApk,
)
from treeforge.android.parsing.dex.model import (
    AndroidDexSource,
    AndroidDexSourceKind,
)
from treeforge.android.parsing.dex.parser import (
    AndroidDexParser,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


class AndroidApkManifestParseError(
    ValueError,
):
    """
    Raised when a structurally identified APK manifest cannot be represented
    faithfully.
    """


class AndroidApkManifestParser:
    """
    Recover literal package identity from installed APK AndroidManifest.xml.

    Discovery is generic and filesystem-backed. Parsing decodes only intrinsic
    manifest facts and does not resolve resources, infer source ownership, or
    consult device/version knowledge.
    """

    _MANIFEST_PATH = "AndroidManifest.xml"

    _ANDROID_NAMESPACE = (
        "http://schemas.android.com/apk/res/android"
    )

    def __init__(
        self,
        *,
        axml_parser: AndroidBinaryXmlParser | None = None,
    ) -> None:
        self.axml_parser = (
            axml_parser
            if axml_parser is not None
            else AndroidBinaryXmlParser()
        )

        self.dex_parser = AndroidDexParser()

    def parse(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> AndroidApkParsingResult:
        if not isinstance(
            filesystems,
            tuple,
        ):
            raise TypeError(
                "filesystems must be a tuple"
            )

        if not all(
            isinstance(
                filesystem,
                AndroidParserFilesystemSource,
            )
            for filesystem
            in filesystems
        ):
            raise TypeError(
                "filesystems must contain only "
                "AndroidParserFilesystemSource entries"
            )

        parsed = []
        dispositions = []

        seen = set()

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
                        or not self._is_apk_candidate(
                            apk_host_path
                        )
                    ):
                        continue

                    apk_android_path = (
                        view.android_path_for(
                            apk_host_path
                        )
                    )

                    identity = (
                        filesystem_source.source_name,
                        apk_android_path,
                    )

                    if identity in seen:
                        continue

                    source = AndroidApkSource(
                        filesystem_source=(
                            filesystem_source
                        ),
                        apk_android_path=(
                            apk_android_path
                        ),
                        apk_host_path=(
                            apk_host_path
                        ),
                    )

                    candidate = self._parse_apk(
                        filesystem_source=(
                            filesystem_source
                        ),
                        apk_host_path=(
                            apk_host_path
                        ),
                        apk_android_path=(
                            apk_android_path
                        ),
                    )

                    seen.add(
                        identity
                    )

                    if candidate is None:
                        dispositions.append(
                            AndroidApkCandidateDisposition(
                                source=source,
                                disposition="not_apk",
                                reason=(
                                    "candidate did not prove to be a "
                                    "structural APK containing "
                                    "AndroidManifest.xml"
                                ),
                            )
                        )
                        continue

                    dispositions.append(
                        AndroidApkCandidateDisposition(
                            source=candidate.source,
                            disposition="parsed",
                            parsed=candidate,
                        )
                    )

                    parsed.append(
                        candidate
                    )

        return AndroidApkParsingResult(
            packages=tuple(
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
        filesystem_source: AndroidParserFilesystemSource,
        apk_host_path,
        apk_android_path,
    ) -> ParsedAndroidApk | None:
        try:
            archive_source = self._apk_archive_source(
                apk_host_path
            )

            with ZipFile(
                archive_source,
                "r",
            ) as archive:
                infos = tuple(
                    archive.infolist()
                )

                members = tuple(
                    AndroidApkArchiveMember(
                        index=index,
                        filename=info.filename,
                        compression_method=info.compress_type,
                        crc32=info.CRC,
                        compressed_size=info.compress_size,
                        uncompressed_size=info.file_size,
                        external_attributes=info.external_attr,
                        is_directory=info.is_dir(),
                    )
                    for index, info
                    in enumerate(
                        infos
                    )
                )

                manifest_info = next(
                    (
                        info
                        for info
                        in infos
                        if info.filename
                        == self._MANIFEST_PATH
                    ),
                    None,
                )

                if manifest_info is None:
                    return None

                raw_manifest = archive.read(
                    manifest_info
                )

                dex_members = tuple(
                    member
                    for member
                    in members
                    if self._is_dex_member(
                        member.filename
                    )
                    and not member.is_directory
                )

                dex_payloads = tuple(
                    (
                        member,
                        archive.read(
                            infos[
                                member.index
                            ]
                        ),
                    )
                    for member
                    in dex_members
                )

        except (
            BadZipFile,
            OSError,
        ) as error:
            # Filename/container suffix alone is not positive APK evidence.
            if isinstance(
                error,
                BadZipFile,
            ):
                return None

            raise AndroidApkManifestParseError(
                "unable to read APK candidate: "
                f"{apk_host_path}"
            ) from error

        if raw_manifest is None:
            return None

        try:
            document = self.axml_parser.parse(
                raw_manifest
            )
        except AndroidBinaryXmlError as error:
            raise AndroidApkManifestParseError(
                "unable to decode AndroidManifest.xml from "
                f"{apk_android_path}: {error}"
            ) from error

        manifest = next(
            (
                element
                for element
                in document.elements
                if element.name == "manifest"
            ),
            None,
        )

        if manifest is None:
            raise AndroidApkManifestParseError(
                "AndroidManifest.xml contains no manifest element"
            )

        package_attribute = self._attribute(
            manifest.attributes,
            name="package",
            namespace=None,
        )

        if (
            package_attribute is None
            or not isinstance(
                package_attribute.literal,
                str,
            )
            or not package_attribute.literal
        ):
            raise AndroidApkManifestParseError(
                "manifest package attribute is not a literal string"
            )

        version_code = self._attribute(
            manifest.attributes,
            name="versionCode",
            namespace=self._ANDROID_NAMESPACE,
        )

        version_name = self._attribute(
            manifest.attributes,
            name="versionName",
            namespace=self._ANDROID_NAMESPACE,
        )

        overlay_element = next(
            (
                element
                for element
                in document.elements
                if element.name == "overlay"
            ),
            None,
        )

        overlay = None

        if overlay_element is not None:
            overlay = AndroidApkOverlayManifest(
                target_package=self._to_value(
                    self._attribute(
                        overlay_element.attributes,
                        name="targetPackage",
                        namespace=self._ANDROID_NAMESPACE,
                    )
                ),
                priority=self._to_value(
                    self._attribute(
                        overlay_element.attributes,
                        name="priority",
                        namespace=self._ANDROID_NAMESPACE,
                    )
                ),
                is_static=self._to_value(
                    self._attribute(
                        overlay_element.attributes,
                        name="isStatic",
                        namespace=self._ANDROID_NAMESPACE,
                    )
                ),
            )

        source = AndroidApkSource(
            filesystem_source=(
                filesystem_source
            ),
            apk_android_path=(
                apk_android_path
            ),
            apk_host_path=(
                apk_host_path
            ),
        )

        dex_files = tuple(
            self.dex_parser.parse(
                payload=payload,
                source=AndroidDexSource(
                    kind=AndroidDexSourceKind.APK_MEMBER,
                    parent=source,
                    parent_source_name=(
                        source.source_name
                    ),
                    parent_android_path=(
                        source.apk_android_path
                    ),
                    member_name=member.filename,
                    member_index=member.index,
                ),
            )
            for member, payload
            in dex_payloads
        )

        return ParsedAndroidApk(
            source=source,
            members=members,
            dex_files=dex_files,
            package_name=self._to_value(
                package_attribute
            ),
            version_code=self._to_value(
                version_code
            ),
            version_name=self._to_value(
                version_name
            ),
            overlay=overlay,
        )

    @staticmethod
    def _is_apk_candidate(
        path,
    ) -> bool:
        name = path.name.lower()

        return (
            name.endswith(".apk")
            or name.endswith(".apk.gz")
        )

    @staticmethod
    def _apk_archive_source(
        apk_host_path,
    ):
        name = (
            apk_host_path.name.lower()
        )

        if name.endswith(
            ".apk.gz"
        ):
            with apk_host_path.open(
                "rb"
            ) as source:
                with GzipFile(
                    fileobj=source,
                    mode="rb",
                ) as compressed:
                    payload = compressed.read()

            return BytesIO(
                payload
            )

        return apk_host_path

    @staticmethod
    def _is_dex_member(
        filename: str,
    ) -> bool:
        """
        Return whether one APK ZIP member is a canonical Android DEX entry.

        Canonical APK multidex entries are root-level ``classes.dex`` and
        ``classesN.dex`` entries where N starts at 2. Nested members remain
        preserved as ZIP-container evidence but are not promoted into the
        APK's canonical DEX population.
        """

        if not isinstance(
            filename,
            str,
        ):
            return False

        if "/" in filename:
            return False

        if filename == "classes.dex":
            return True

        if (
            not filename.startswith(
                "classes"
            )
            or not filename.endswith(
                ".dex"
            )
        ):
            return False

        suffix = filename[
            len(
                "classes"
            ):
            -len(
                ".dex"
            )
        ]

        return (
            bool(
                suffix
            )
            and suffix.isdigit()
            and not suffix.startswith(
                "0"
            )
            and int(
                suffix
            ) >= 2
        )

    @staticmethod
    def _attribute(
        attributes,
        *,
        name: str,
        namespace: str | None,
    ):
        for attribute in attributes:
            if (
                attribute.name == name
                and attribute.namespace == namespace
            ):
                return attribute

        return None

    @staticmethod
    def _to_value(
        attribute,
    ) -> AndroidApkManifestValue | None:
        if attribute is None:
            return None

        return AndroidApkManifestValue(
            literal=attribute.literal,
            data_type=attribute.data_type,
            data=attribute.data,
            raw_string=attribute.raw_string,
        )
