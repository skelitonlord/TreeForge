from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.dex.model import (
    AndroidDexSourceKind,
    ParsedAndroidDex,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidApkSource:
    """
    Exact canonical filesystem identity for one installed APK.

    Parsing preserves the canonical parser filesystem source together with
    the Android-visible and host paths. Package/source ownership conclusions
    belong to later stages.
    """

    filesystem_source: AndroidParserFilesystemSource
    apk_android_path: PurePosixPath
    apk_host_path: Path

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "filesystem_source must be an "
                "AndroidParserFilesystemSource"
            )

        if not isinstance(
            self.apk_android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "apk_android_path must be a PurePosixPath"
            )

        if not self.apk_android_path.is_absolute():
            raise ValueError(
                "apk_android_path must be absolute"
            )

        if not isinstance(
            self.apk_host_path,
            Path,
        ):
            raise TypeError(
                "apk_host_path must be a Path"
            )

    @property
    def source_name(
        self,
    ) -> str:
        return self.filesystem_source.source_name

    @property
    def identity_key(
        self,
    ) -> tuple[
        str,
        PurePosixPath,
    ]:
        return (
            self.source_name,
            self.apk_android_path,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidApkArchiveMember:
    """
    One exact APK ZIP central-directory member.

    This is structural container evidence only.  Member semantics such as
    DEX, resources, native libraries, signatures, and package behavior are
    represented separately by their owning Parsing families.
    """

    index: int
    filename: str
    compression_method: int
    crc32: int
    compressed_size: int
    uncompressed_size: int
    external_attributes: int
    is_directory: bool

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
            or self.index < 0
        ):
            raise ValueError(
                "APK archive member index must be a non-negative integer"
            )

        if (
            not isinstance(
                self.filename,
                str,
            )
            or not self.filename
        ):
            raise ValueError(
                "APK archive member filename must be a non-empty string"
            )

        for name in (
            "compression_method",
            "crc32",
            "compressed_size",
            "uncompressed_size",
            "external_attributes",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.is_directory,
            bool,
        ):
            raise TypeError(
                "is_directory must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidApkManifestValue:
    """
    One literal or typed AndroidManifest attribute value.

    ``literal`` is populated only when the manifest itself contains a
    directly recoverable string/bool/integer. Resource references remain
    represented by their exact Android typed-value metadata.
    """

    literal: str | int | bool | None
    data_type: int | None = None
    data: int | None = None
    raw_string: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.literal is not None
            and not isinstance(
                self.literal,
                (
                    str,
                    int,
                    bool,
                ),
            )
        ):
            raise TypeError(
                "literal must be a string, integer, bool, or None"
            )

        if (
            self.data_type is not None
            and (
                isinstance(
                    self.data_type,
                    bool,
                )
                or not isinstance(
                    self.data_type,
                    int,
                )
            )
        ):
            raise TypeError(
                "data_type must be an integer or None"
            )

        if (
            self.data is not None
            and (
                isinstance(
                    self.data,
                    bool,
                )
                or not isinstance(
                    self.data,
                    int,
                )
            )
        ):
            raise TypeError(
                "data must be an integer or None"
            )

        if (
            self.raw_string is not None
            and not isinstance(
                self.raw_string,
                str,
            )
        ):
            raise TypeError(
                "raw_string must be a string or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidApkOverlayManifest:
    target_package: AndroidApkManifestValue | None = None
    priority: AndroidApkManifestValue | None = None
    is_static: AndroidApkManifestValue | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidApk:
    """
    Literal package identity recovered from AndroidManifest.xml.
    """

    source: AndroidApkSource

    members: tuple[
        AndroidApkArchiveMember,
        ...,
    ] = ()

    dex_files: tuple[
        ParsedAndroidDex,
        ...,
    ] = ()

    package_name: AndroidApkManifestValue = None  # type: ignore[assignment]
    version_code: AndroidApkManifestValue | None = None
    version_name: AndroidApkManifestValue | None = None
    overlay: AndroidApkOverlayManifest | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidApkSource,
        ):
            raise TypeError(
                "source must be an AndroidApkSource"
            )

        if (
            not isinstance(
                self.members,
                tuple,
            )
            or not all(
                isinstance(
                    member,
                    AndroidApkArchiveMember,
                )
                for member
                in self.members
            )
        ):
            raise TypeError(
                "members must contain only AndroidApkArchiveMember values"
            )

        expected_member_indexes = tuple(
            range(
                len(
                    self.members
                )
            )
        )

        actual_member_indexes = tuple(
            member.index
            for member
            in self.members
        )

        if (
            actual_member_indexes
            != expected_member_indexes
        ):
            raise ValueError(
                "APK members must preserve exact central-directory order"
            )

        if (
            not isinstance(
                self.dex_files,
                tuple,
            )
            or not all(
                isinstance(
                    dex_file,
                    ParsedAndroidDex,
                )
                for dex_file
                in self.dex_files
            )
        ):
            raise TypeError(
                "dex_files must contain only ParsedAndroidDex values"
            )

        member_by_index = {
            member.index: member
            for member
            in self.members
        }

        seen_dex_identities = set()

        for dex_file in self.dex_files:
            dex_source = dex_file.source

            if (
                dex_source.kind
                is not AndroidDexSourceKind.APK_MEMBER
            ):
                raise ValueError(
                    "APK dex_files must use APK_MEMBER provenance"
                )

            if dex_source.parent is not self.source:
                raise ValueError(
                    "APK DEX must reuse the exact canonical "
                    "AndroidApkSource parent object"
                )

            if (
                dex_source.parent_source_name
                != self.source.source_name
                or dex_source.parent_android_path
                != self.source.apk_android_path
            ):
                raise ValueError(
                    "APK DEX stable parent identity must exactly match "
                    "the canonical APK source"
                )

            if dex_source.member_index is None:
                raise ValueError(
                    "APK DEX source must retain member index"
                )

            member = member_by_index.get(
                dex_source.member_index
            )

            if (
                member is None
                or member.filename
                != dex_source.member_name
            ):
                raise ValueError(
                    "APK DEX source must retain exact central-directory "
                    "member identity"
                )

            if member.is_directory:
                raise ValueError(
                    "APK DEX source cannot reference a directory"
                )

            identity = dex_source.identity_key

            if identity in seen_dex_identities:
                raise ValueError(
                    "APK DEX source identities must be unique"
                )

            seen_dex_identities.add(
                identity
            )

        if not isinstance(
            self.package_name,
            AndroidApkManifestValue,
        ):
            raise TypeError(
                "package_name must be an AndroidApkManifestValue"
            )

        if not isinstance(
            self.package_name.literal,
            str,
        ) or not self.package_name.literal:
            raise ValueError(
                "package_name must preserve a non-empty literal string"
            )

        for name, value in (
            (
                "version_code",
                self.version_code,
            ),
            (
                "version_name",
                self.version_name,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    AndroidApkManifestValue,
                )
            ):
                raise TypeError(
                    f"{name} must be an "
                    "AndroidApkManifestValue or None"
                )

        if (
            self.overlay is not None
            and not isinstance(
                self.overlay,
                AndroidApkOverlayManifest,
            )
        ):
            raise TypeError(
                "overlay must be an "
                "AndroidApkOverlayManifest or None"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidApkCandidateDisposition:
    """
    Complete disposition for one canonical filesystem APK candidate.

    Every regular non-symlink .apk/.apk.gz candidate discovered by Parsing
    must appear exactly once here, regardless of whether it proves to be a
    structurally valid APK package.
    """

    source: AndroidApkSource
    disposition: str
    parsed: ParsedAndroidApk | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidApkSource,
        ):
            raise TypeError(
                "source must be an AndroidApkSource"
            )

        if self.disposition not in {
            "parsed",
            "not_apk",
        }:
            raise ValueError(
                "unsupported APK candidate disposition"
            )

        if self.disposition == "parsed":
            if not isinstance(
                self.parsed,
                ParsedAndroidApk,
            ):
                raise ValueError(
                    "parsed APK disposition requires ParsedAndroidApk"
                )

            if self.parsed.source != self.source:
                raise ValueError(
                    "parsed APK disposition source must match parsed source"
                )

            if self.reason is not None:
                raise ValueError(
                    "parsed APK disposition must not carry a reason"
                )

        else:
            if self.parsed is not None:
                raise ValueError(
                    "not_apk disposition must not contain parsed APK"
                )

            if (
                not isinstance(
                    self.reason,
                    str,
                )
                or not self.reason
            ):
                raise ValueError(
                    "not_apk disposition requires a non-empty reason"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidApkParsingResult:
    packages: tuple[
        ParsedAndroidApk,
        ...,
    ] = ()

    candidates: tuple[
        AndroidApkCandidateDisposition,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.packages,
            tuple,
        ):
            raise TypeError(
                "packages must be a tuple"
            )

        if not all(
            isinstance(
                package,
                ParsedAndroidApk,
            )
            for package
            in self.packages
        ):
            raise TypeError(
                "packages must contain only ParsedAndroidApk values"
            )

        if (
            not isinstance(
                self.candidates,
                tuple,
            )
            or not all(
                isinstance(
                    candidate,
                    AndroidApkCandidateDisposition,
                )
                for candidate
                in self.candidates
            )
        ):
            raise TypeError(
                "candidates must contain only "
                "AndroidApkCandidateDisposition values"
            )

        canonical_candidates = tuple(
            sorted(
                self.candidates,
                key=lambda candidate: (
                    candidate.source.identity_key
                ),
            )
        )

        if canonical_candidates != self.candidates:
            raise ValueError(
                "APK candidates must use canonical source order"
            )

        candidate_identities = tuple(
            candidate.source.identity_key
            for candidate
            in self.candidates
        )

        if len(
            candidate_identities
        ) != len(
            set(
                candidate_identities
            )
        ):
            raise ValueError(
                "APK candidate identities must be unique"
            )

        parsed_candidate_identities = {
            candidate.source.identity_key
            for candidate
            in self.candidates
            if candidate.disposition == "parsed"
        }

        package_identities = {
            package.source.identity_key
            for package
            in self.packages
        }

        if (
            parsed_candidate_identities
            != package_identities
        ):
            raise ValueError(
                "APK parsed-candidate population must exactly match "
                "parsed APK package population"
            )

        canonical = tuple(
            sorted(
                self.packages,
                key=lambda package: (
                    package.source.identity_key
                ),
            )
        )

        if canonical != self.packages:
            raise ValueError(
                "packages must use canonical source order"
            )

        identities = tuple(
            package.source.identity_key
            for package
            in self.packages
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "APK package identities must be unique"
            )

    @property
    def package_count(
        self,
    ) -> int:
        return len(
            self.packages
        )

    @staticmethod
    def _is_dex_member_name(
        filename: str,
    ) -> bool:
        """
        Return whether one APK ZIP member has canonical root-level
        ``classes*.dex`` identity.

        This derives structural discovery from the preserved central
        directory rather than from successfully decoded DEX files. Nested
        entries remain preserved as archive members but are not canonical
        APK DEX entries.
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

    @property
    def member_count(
        self,
    ) -> int:
        return sum(
            len(
                package.members
            )
            for package
            in self.packages
        )

    @property
    def dex_member_count(
        self,
    ) -> int:
        return sum(
            1
            for package
            in self.packages
            for member
            in package.members
            if (
                not member.is_directory
                and self._is_dex_member_name(
                    member.filename
                )
            )
        )

    @property
    def dex_count(
        self,
    ) -> int:
        return sum(
            len(
                package.dex_files
            )
            for package
            in self.packages
        )

    @property
    def unresolved_dex_count(
        self,
    ) -> int:
        return (
            self.dex_member_count
            - self.dex_count
        )

    @property
    def dex_package_count(
        self,
    ) -> int:
        return sum(
            1
            for package
            in self.packages
            if any(
                not member.is_directory
                and self._is_dex_member_name(
                    member.filename
                )
                for member
                in package.members
            )
        )

    @property
    def multidex_package_count(
        self,
    ) -> int:
        return sum(
            1
            for package
            in self.packages
            if sum(
                1
                for member
                in package.members
                if (
                    not member.is_directory
                    and self._is_dex_member_name(
                        member.filename
                    )
                )
            ) > 1
        )
