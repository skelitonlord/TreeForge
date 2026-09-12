from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigSource:
    """
    Exact canonical source identity for one AVF VM configuration embedded
    inside an APK.

    The filesystem source preserves the physical extracted filesystem and
    Extraction provenance. ``apk_android_path`` preserves the Android-visible
    APK path. ``member_path`` preserves the exact ZIP member containing the
    VM configuration.

    Parsing does not interpret which runtime the configuration describes.
    """

    filesystem_source: AndroidParserFilesystemSource
    apk_android_path: PurePosixPath
    apk_host_path: Path
    member_path: str
    member_index: int

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

        if not isinstance(
            self.member_path,
            str,
        ):
            raise TypeError(
                "member_path must be a string"
            )

        if not self.member_path:
            raise ValueError(
                "member_path must not be empty"
            )

        if self.member_path.startswith(
            "/"
        ):
            raise ValueError(
                "member_path must be APK-relative"
            )

        if (
            isinstance(
                self.member_index,
                bool,
            )
            or not isinstance(
                self.member_index,
                int,
            )
            or self.member_index < 0
        ):
            raise ValueError(
                "member_index must be a non-negative integer"
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
        str,
        int,
    ]:
        return (
            self.source_name,
            self.apk_android_path,
            self.member_path,
            self.member_index,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigOs:
    name: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigTask:
    task_type: str
    command: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.task_type,
            str,
        ):
            raise TypeError(
                "task_type must be a string"
            )

        if not self.task_type:
            raise ValueError(
                "task_type must not be empty"
            )

        if not isinstance(
            self.command,
            str,
        ):
            raise TypeError(
                "command must be a string"
            )

        if not self.command:
            raise ValueError(
                "command must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigApex:
    name: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name:
            raise ValueError(
                "name must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigExtraApk:
    path: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.path,
            str,
        ):
            raise TypeError(
                "path must be a string"
            )

        if not self.path:
            raise ValueError(
                "path must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidAvfVmConfig:
    """
    Literal AVF VM payload configuration recovered from one APK member.

    Parsing preserves the exact raw JSON payload and decodes only intrinsic
    fields. Guest-runtime selection and cross-source reconciliation belong to
    Android Device Universe.
    """

    source: AndroidAvfVmConfigSource
    raw: bytes
    version: int | None
    os: AndroidAvfVmConfigOs
    task: AndroidAvfVmConfigTask

    prefer_staged: bool | None = None

    apexes: tuple[
        AndroidAvfVmConfigApex,
        ...,
    ] = ()

    extra_apks: tuple[
        AndroidAvfVmConfigExtraApk,
        ...,
    ] = ()

    export_tombstones: bool | None = None
    enable_authfs: bool | None = None
    hugepages: bool | None = None

    unknown_fields: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidAvfVmConfigSource,
        ):
            raise TypeError(
                "source must be an AndroidAvfVmConfigSource"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        if (
            self.version is not None
            and (
                isinstance(
                    self.version,
                    bool,
                )
                or not isinstance(
                    self.version,
                    int,
                )
            )
        ):
            raise TypeError(
                "version must be an integer or None"
            )

        if not isinstance(
            self.os,
            AndroidAvfVmConfigOs,
        ):
            raise TypeError(
                "os must be an AndroidAvfVmConfigOs"
            )

        if not isinstance(
            self.task,
            AndroidAvfVmConfigTask,
        ):
            raise TypeError(
                "task must be an AndroidAvfVmConfigTask"
            )

        for name, value in (
            (
                "prefer_staged",
                self.prefer_staged,
            ),
            (
                "export_tombstones",
                self.export_tombstones,
            ),
            (
                "enable_authfs",
                self.enable_authfs,
            ),
            (
                "hugepages",
                self.hugepages,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    bool,
                )
            ):
                raise TypeError(
                    f"{name} must be a bool or None"
                )

        if not isinstance(
            self.apexes,
            tuple,
        ):
            raise TypeError(
                "apexes must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidAvfVmConfigApex,
            )
            for value
            in self.apexes
        ):
            raise TypeError(
                "apexes must contain only "
                "AndroidAvfVmConfigApex entries"
            )

        if not isinstance(
            self.extra_apks,
            tuple,
        ):
            raise TypeError(
                "extra_apks must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidAvfVmConfigExtraApk,
            )
            for value
            in self.extra_apks
        ):
            raise TypeError(
                "extra_apks must contain only "
                "AndroidAvfVmConfigExtraApk entries"
            )

        if not isinstance(
            self.unknown_fields,
            tuple,
        ):
            raise TypeError(
                "unknown_fields must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            for value
            in self.unknown_fields
        ):
            raise ValueError(
                "unknown_fields must contain "
                "non-empty strings"
            )

        if self.unknown_fields != tuple(
            sorted(
                self.unknown_fields
            )
        ):
            raise ValueError(
                "unknown_fields must use canonical order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigCandidateDisposition:
    """
    Explicit disposition for one assets/*.json ZIP member examined for
    intrinsic AVF VM-config structure.
    """

    source: AndroidAvfVmConfigSource
    raw: bytes
    disposition: str
    parsed: ParsedAndroidAvfVmConfig | None = None
    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidAvfVmConfigSource,
        ):
            raise TypeError(
                "source must be an AndroidAvfVmConfigSource"
            )

        if not isinstance(
            self.raw,
            bytes,
        ):
            raise TypeError(
                "raw must be bytes"
            )

        if self.disposition not in {
            "invalid_json",
            "non_object_json",
            "not_vm_config",
            "parsed",
        }:
            raise ValueError(
                "unsupported AVF candidate disposition"
            )

        if self.disposition == "parsed":
            if not isinstance(
                self.parsed,
                ParsedAndroidAvfVmConfig,
            ):
                raise ValueError(
                    "parsed disposition requires "
                    "ParsedAndroidAvfVmConfig"
                )

            if (
                self.parsed.source
                != self.source
            ):
                raise ValueError(
                    "parsed disposition source must match "
                    "parsed configuration source"
                )

            if self.reason is not None:
                raise ValueError(
                    "parsed disposition must not carry a reason"
                )

        else:
            if self.parsed is not None:
                raise ValueError(
                    "non-parsed disposition cannot carry "
                    "ParsedAndroidAvfVmConfig"
                )

            if (
                not isinstance(
                    self.reason,
                    str,
                )
                or not self.reason
            ):
                raise ValueError(
                    "non-parsed disposition requires a reason"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAvfVmConfigParsingResult:
    """
    Canonical deterministic AVF VM configuration population.

    Distinct APK/member observations remain distinct. Cross-config
    reconciliation belongs to Android Device Universe.
    """

    configurations: tuple[
        ParsedAndroidAvfVmConfig,
        ...,
    ] = ()

    candidates: tuple[
        AndroidAvfVmConfigCandidateDisposition,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        if not all(
            isinstance(
                value,
                ParsedAndroidAvfVmConfig,
            )
            for value
            in self.configurations
        ):
            raise TypeError(
                "configurations must contain only "
                "ParsedAndroidAvfVmConfig entries"
            )

        if (
            not isinstance(
                self.candidates,
                tuple,
            )
            or not all(
                isinstance(
                    candidate,
                    AndroidAvfVmConfigCandidateDisposition,
                )
                for candidate
                in self.candidates
            )
        ):
            raise TypeError(
                "candidates must contain only "
                "AndroidAvfVmConfigCandidateDisposition entries"
            )

        canonical_candidates = tuple(
            sorted(
                self.candidates,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if (
            canonical_candidates
            != self.candidates
        ):
            raise ValueError(
                "AVF candidates must use canonical source order"
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
                "AVF candidate identities must be unique"
            )

        parsed_candidate_identities = {
            candidate.source.identity_key
            for candidate
            in self.candidates
            if candidate.disposition == "parsed"
        }

        configuration_identities = {
            value.source.identity_key
            for value
            in self.configurations
        }

        if (
            parsed_candidate_identities
            != configuration_identities
        ):
            raise ValueError(
                "parsed AVF candidate population must exactly "
                "match AVF configuration population"
            )

        canonical = tuple(
            sorted(
                self.configurations,
                key=lambda value: (
                    value.source.identity_key
                ),
            )
        )

        if (
            canonical
            != self.configurations
        ):
            raise ValueError(
                "configurations must use "
                "canonical source order"
            )

        identities = tuple(
            value.source.identity_key
            for value
            in self.configurations
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "AVF VM configuration identities "
                "must be unique"
            )

    @property
    def configuration_count(
        self,
    ) -> int:
        return len(
            self.configurations
        )
