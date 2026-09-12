from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.vintf import (
    ParsedVintfDocument,
)
from treeforge.android.parsing.fstab import (
    AndroidFstabDeclaration,
    AndroidFstabUnparsedLine,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
    AndroidParserFilesystemSource,
)

from treeforge.android.parsing.init import (
    AndroidInitAction,
    AndroidInitImport,
    AndroidInitService,
    AndroidInitUnparsedLine,
)
from treeforge.android.parsing.ueventd import (
    AndroidUeventdDeclaration,
    AndroidUeventdUnparsedLine,
)
from treeforge.android.parsing.selinux import (
    ParsedAndroidSelinuxFile,
)
from treeforge.android.properties import (
    AndroidPropertyDeclaration,
    AndroidPropertySourceKind,
    AndroidPropertyUnparsedLine,
)


def _validate_model_source(
    *,
    source: AndroidModelSource | None,
    expected_kind: AndroidModelSourceKind,
    source_path: Path,
    filesystem_source: AndroidParserFilesystemSource,
    android_path: PurePosixPath | None,
) -> None:
    """
    Validate optional exact canonical source identity.

    ``None`` remains valid for the legacy explicit-path extraction API.
    Inventory-backed Parsing must retain the exact AndroidModelSource object.
    """

    if source is None:
        return

    if not isinstance(
        source,
        AndroidModelSource,
    ):
        raise TypeError(
            "source must be an AndroidModelSource or None"
        )

    if source.kind is not expected_kind:
        raise ValueError(
            "canonical AndroidModelSource kind does not match "
            "the parsed filesystem family"
        )

    if source.host_path != source_path:
        raise ValueError(
            "canonical AndroidModelSource host_path must match "
            "parsed source_path"
        )

    if source.filesystem_source is not filesystem_source:
        raise ValueError(
            "parsed filesystem source must reuse the exact "
            "canonical AndroidParserFilesystemSource object"
        )

    if source.android_path != android_path:
        raise ValueError(
            "canonical AndroidModelSource android_path must match "
            "parsed android_path"
        )


def _validate_android_path(
    android_path: PurePosixPath | None,
) -> None:
    """
    Validate one optional canonical Android path.

    Canonical Android paths are absolute Android-visible paths:

        /init.environ.rc
        /system/etc/init/init.rc
        /vendor/etc/fstab.device
        /vendor/ueventd.rc

    Parser-source provenance and source-root identity are preserved
    separately by ``filesystem_source`` and must not be encoded into
    ``android_path``.
    """

    if (
        android_path is not None
        and not isinstance(
            android_path,
            PurePosixPath,
        )
    ):
        raise TypeError(
            "android_path must be a PurePosixPath or None"
        )

    if android_path is None:
        return

    if not android_path.is_absolute():
        raise ValueError(
            "android_path must be absolute"
        )

    if (
        not android_path.parts
        or str(
            android_path
        ) in {
            "",
            ".",
        }
    ):
        raise ValueError(
            "android_path must identify a file"
        )

    if any(
        part == ".."
        for part in android_path.parts
    ):
        raise ValueError(
            "android_path must not contain "
            "parent traversal"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidInitSource:
    """
    Immutable parsed representation of one Android init source file.

    ``source_path`` preserves the exact parser-facing host path.
    ``android_path`` preserves the canonical absolute Android-visible path.
    Parser-source provenance remains separate in ``filesystem_source``.

    Parsed service and action identities are preserved exactly.
    """

    source_path: Path
    raw: str
    filesystem_source: AndroidParserFilesystemSource
    android_path: PurePosixPath | None = None
    source: AndroidModelSource | None = None

    imports: tuple[
        AndroidInitImport,
        ...,
    ] = ()

    services: tuple[
        AndroidInitService,
        ...,
    ] = ()

    actions: tuple[
        AndroidInitAction,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidInitUnparsedLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        """
        Validate one extracted init source.
        """

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        _validate_android_path(
            self.android_path
        )

        _validate_model_source(
            source=self.source,
            expected_kind=(
                AndroidModelSourceKind.INIT
            ),
            source_path=self.source_path,
            filesystem_source=self.filesystem_source,
            android_path=self.android_path,
        )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.imports,
            tuple,
        ):
            raise TypeError(
                "imports must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidInitImport,
            )
            for value in self.imports
        ):
            raise TypeError(
                "imports must contain only "
                "AndroidInitImport instances"
            )

        if not isinstance(
            self.services,
            tuple,
        ):
            raise TypeError(
                "services must be a tuple"
            )

        if not all(
            isinstance(
                service,
                AndroidInitService,
            )
            for service in self.services
        ):
            raise TypeError(
                "services must contain only "
                "AndroidInitService instances"
            )

        if not isinstance(
            self.actions,
            tuple,
        ):
            raise TypeError(
                "actions must be a tuple"
            )

        if not all(
            isinstance(
                action,
                AndroidInitAction,
            )
            for action in self.actions
        ):
            raise TypeError(
                "actions must contain only "
                "AndroidInitAction instances"
            )


        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                AndroidInitUnparsedLine,
            )
            for line in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidInitUnparsedLine instances"
            )


    @property
    def service_count(
        self,
    ) -> int:
        """
        Return the parsed service count.
        """

        return len(
            self.services
        )

    @property
    def action_count(
        self,
    ) -> int:
        """
        Return the parsed action count.
        """

        return len(
            self.actions
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        """
        Return whether no parsed init models are present.
        """

        return not (
            self.services
            or self.actions
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidFstab:
    """
    Preserve one parsed Android fstab source and both path identities.

    Declaration ordering, exact source lines, and unsupported meaningful
    source material remain attached to the source artifact.
    """

    source_path: Path
    filesystem_source: AndroidParserFilesystemSource

    declarations: tuple[
        AndroidFstabDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidFstabUnparsedLine,
        ...,
    ] = ()

    android_path: PurePosixPath | None = None
    source: AndroidModelSource | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        _validate_android_path(
            self.android_path
        )

        _validate_model_source(
            source=self.source,
            expected_kind=(
                AndroidModelSourceKind.FSTAB
            ),
            source_path=self.source_path,
            filesystem_source=self.filesystem_source,
            android_path=self.android_path,
        )

        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidFstabDeclaration,
            )
            for value in self.declarations
        ):
            raise TypeError(
                "declarations must contain only "
                "AndroidFstabDeclaration instances"
            )

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidFstabUnparsedLine,
            )
            for value in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidFstabUnparsedLine instances"
            )

    @property
    def entry_count(
        self,
    ) -> int:
        return len(
            self.declarations
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not self.declarations


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidUeventd:
    """
    Immutable parsed representation of one Android ueventd source.

    ``source_path`` preserves exact host provenance.
    ``android_path`` preserves the canonical Android-visible absolute path.

    Declaration ordering and unsupported meaningful source evidence are
    preserved exactly from Parsing.
    """

    source_path: Path
    raw: str
    filesystem_source: AndroidParserFilesystemSource

    declarations: tuple[
        AndroidUeventdDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidUeventdUnparsedLine,
        ...,
    ] = ()

    android_path: PurePosixPath | None = None
    source: AndroidModelSource | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        _validate_android_path(
            self.android_path
        )

        _validate_model_source(
            source=self.source,
            expected_kind=(
                AndroidModelSourceKind.UEVENTD
            ),
            source_path=self.source_path,
            filesystem_source=self.filesystem_source,
            android_path=self.android_path,
        )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not all(
            isinstance(
                declaration,
                AndroidUeventdDeclaration.__args__,
            )
            for declaration in self.declarations
        ):
            raise TypeError(
                "declarations must contain only "
                "Android ueventd declaration instances"
            )

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                AndroidUeventdUnparsedLine,
            )
            for line in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidUeventdUnparsedLine instances"
            )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not (
            self.declarations
            or self.unparsed_lines
        )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidVintfSource:
    """
    Preserve one exact parsed VINTF document and both path identities.

    ``source_path`` is host provenance.
    ``android_path`` is the canonical absolute Android-visible path.
    """

    source_path: Path
    parsed: ParsedVintfDocument
    filesystem_source: AndroidParserFilesystemSource
    android_path: PurePosixPath | None = None
    source: AndroidModelSource | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        _validate_android_path(
            self.android_path
        )

        _validate_model_source(
            source=self.source,
            expected_kind=(
                AndroidModelSourceKind.VINTF
            ),
            source_path=self.source_path,
            filesystem_source=self.filesystem_source,
            android_path=self.android_path,
        )

        if not isinstance(
            self.parsed,
            ParsedVintfDocument,
        ):
            raise TypeError(
                "parsed must be a ParsedVintfDocument"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidSelinuxSource:
    """
    Preserve one exact parsed SELinux source and both path identities.
    """

    source_path: Path
    parsed: ParsedAndroidSelinuxFile
    filesystem_source: AndroidParserFilesystemSource
    android_path: PurePosixPath | None = None
    source: AndroidModelSource | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        _validate_android_path(
            self.android_path
        )

        _validate_model_source(
            source=self.source,
            expected_kind=(
                AndroidModelSourceKind.SELINUX
            ),
            source_path=self.source_path,
            filesystem_source=self.filesystem_source,
            android_path=self.android_path,
        )

        if not isinstance(
            self.parsed,
            ParsedAndroidSelinuxFile,
        ):
            raise TypeError(
                "parsed must be a ParsedAndroidSelinuxFile"
            )

        if (
            self.parsed.source_path
            != self.source_path
        ):
            raise ValueError(
                "parsed SELinux source_path must match wrapper source_path"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidPropertyFile:
    """
    Immutable parsed Android property source.

    ``source_path`` preserves exact host provenance.
    ``android_path`` preserves the canonical absolute Android-visible
    location when known.

    ``kind`` describes source-path classification only. Property declaration
    order, duplicate keys, source line identity, and unsupported lexical
    material remain preserved.
    """

    kind: AndroidPropertySourceKind
    source_path: Path
    filesystem_source: AndroidParserFilesystemSource
    android_path: PurePosixPath | None = None
    source: AndroidModelSource | None = None

    declarations: tuple[
        AndroidPropertyDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidPropertyUnparsedLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidPropertySourceKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidPropertySourceKind"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        _validate_android_path(
            self.android_path
        )

        _validate_model_source(
            source=self.source,
            expected_kind=(
                AndroidModelSourceKind.PROPERTY
            ),
            source_path=self.source_path,
            filesystem_source=self.filesystem_source,
            android_path=self.android_path,
        )

        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not all(
            isinstance(
                declaration,
                AndroidPropertyDeclaration,
            )
            for declaration in self.declarations
        ):
            raise TypeError(
                "declarations must contain only "
                "AndroidPropertyDeclaration instances"
            )

        if not isinstance(
            self.unparsed_lines,
            tuple,
        ):
            raise TypeError(
                "unparsed_lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                AndroidPropertyUnparsedLine,
            )
            for line in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain only "
                "AndroidPropertyUnparsedLine instances"
            )

    @property
    def property_count(
        self,
    ) -> int:
        """
        Return the parsed declaration count.
        """

        return len(
            self.declarations
        )

    @property
    def properties(
        self,
    ) -> tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]:
        """
        Return declaration key/value pairs in exact source order.

        This is a projection for consumers that do not yet require
        declaration-level provenance. Duplicate keys remain present.
        """

        return tuple(
            (
                declaration.key,
                declaration.value,
            )
            for declaration in self.declarations
        )

    def values(
        self,
        key: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Return every declaration value for one key in source order.
        """

        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "key must be a string"
            )

        return tuple(
            declaration.value
            for declaration in self.declarations
            if declaration.key == key
        )

    def value(
        self,
        key: str,
    ) -> str | None:
        """
        Return the final declaration value for one key.
        """

        values = self.values(
            key
        )

        if not values:
            return None

        return values[-1]

@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFilesystemParsingResult:
    """
    Immutable aggregate of parsed Android source models.

    Every contained parsed model is retained by exact identity.
    """

    init_files: tuple[
        ParsedAndroidInitSource,
        ...,
    ] = ()

    fstabs: tuple[
        ParsedAndroidFstab,
        ...,
    ] = ()

    ueventd_files: tuple[
        ParsedAndroidUeventd,
        ...,
    ] = ()

    vintf_documents: tuple[
        ParsedAndroidVintfSource,
        ...,
    ] = ()

    property_files: tuple[
        ParsedAndroidPropertyFile,
        ...,
    ] = ()

    selinux_sources: tuple[
        ParsedAndroidSelinuxSource,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        """
        Validate the complete extraction result.
        """

        collections = (
            (
                "init_files",
                self.init_files,
                ParsedAndroidInitSource,
            ),
            (
                "fstabs",
                self.fstabs,
                ParsedAndroidFstab,
            ),
            (
                "ueventd_files",
                self.ueventd_files,
                ParsedAndroidUeventd,
            ),
            (
                "vintf_documents",
                self.vintf_documents,
                ParsedAndroidVintfSource,
            ),
            (
                "property_files",
                self.property_files,
                ParsedAndroidPropertyFile,
            ),
            (
                "selinux_sources",
                self.selinux_sources,
                ParsedAndroidSelinuxSource,
            ),
        )

        for (
            field_name,
            values,
            expected_type,
        ) in collections:
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value in values
            ):
                raise TypeError(
                    f"{field_name} must contain only "
                    f"{expected_type.__name__} instances"
                )

            canonical_paths = tuple(
                value.source_path
                for value in values
            )

            if canonical_paths != tuple(
                sorted(
                    canonical_paths,
                    key=lambda path: (
                        path.as_posix()
                    ),
                )
            ):
                raise ValueError(
                    f"{field_name} must be in "
                    "canonical source-path order"
                )

            if len(
                canonical_paths
            ) != len(
                set(
                    canonical_paths
                )
            ):
                raise ValueError(
                    f"{field_name} source paths "
                    "must be unique"
                )

            android_identities = tuple(
                (
                    value.filesystem_source.source_name,
                    value.android_path,
                )
                for value in values
                if value.android_path is not None
            )

            if len(
                android_identities
            ) != len(
                set(
                    android_identities
                )
            ):
                raise ValueError(
                    f"{field_name} source-root/Android-path "
                    "identities must be unique"
                )

    @property
    def source_paths(
        self,
    ) -> tuple[
        Path,
        ...,
    ]:
        """
        Return every host source path in canonical model-category order.
        """

        return (
            *(
                value.source_path
                for value
                in self.init_files
            ),
            *(
                value.source_path
                for value
                in self.fstabs
            ),
            *(
                value.source_path
                for value
                in self.ueventd_files
            ),
            *(
                value.source_path
                for value
                in self.vintf_documents
            ),
            *(
                value.source_path
                for value
                in self.property_files
            ),
            *(
                value.source_path
                for value
                in self.selinux_sources
            ),
        )

    @property
    def android_paths(
        self,
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        """
        Return every known canonical Android path in category order.
        """

        values = (
            *self.init_files,
            *self.fstabs,
            *self.ueventd_files,
            *self.vintf_documents,
            *self.property_files,
            *self.selinux_sources,
        )

        return tuple(
            value.android_path
            for value in values
            if value.android_path is not None
        )

    @property
    def source_count(
        self,
    ) -> int:
        """
        Return the total extracted source count.
        """

        return len(
            self.source_paths
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        """
        Return whether no Android models were extracted.
        """

        return self.source_count == 0

    @property
    def build_property_files(
        self,
    ) -> tuple[
        ParsedAndroidPropertyFile,
        ...,
    ]:
        """
        Return build-property sources.
        """

        return tuple(
            value
            for value in self.property_files
            if (
                value.kind
                is AndroidPropertySourceKind.BUILD
            )
        )

    @property
    def default_property_files(
        self,
    ) -> tuple[
        ParsedAndroidPropertyFile,
        ...,
    ]:
        """
        Return default-property sources.
        """

        return tuple(
            value
            for value in self.property_files
            if (
                value.kind
                is AndroidPropertySourceKind.DEFAULT
            )
        )

    @property
    def generic_property_files(
        self,
    ) -> tuple[
        ParsedAndroidPropertyFile,
        ...,
    ]:
        """
        Return generic Android property sources.
        """

        return tuple(
            value
            for value in self.property_files
            if (
                value.kind
                is AndroidPropertySourceKind.GENERIC
            )
        )

class AndroidFilesystemParsingResultBuilder:
    """
    Build a deterministic Android model extraction aggregate.
    """

    def build(
        self,
        *,
        init_files: tuple[
            ParsedAndroidInitSource,
            ...,
        ] = (),
        fstabs: tuple[
            ParsedAndroidFstab,
            ...,
        ] = (),
        ueventd_files: tuple[
            ParsedAndroidUeventd,
            ...,
        ] = (),
        vintf_documents: tuple[
            ParsedAndroidVintfSource,
            ...,
        ] = (),
        property_files: tuple[
            ParsedAndroidPropertyFile,
            ...,
        ] = (),
        selinux_sources: tuple[
            ParsedAndroidSelinuxSource,
            ...,
        ] = (),
    ) -> AndroidFilesystemParsingResult:
        """
        Build one canonical immutable extraction result.
        """

        collections = (
            init_files,
            fstabs,
            ueventd_files,
            vintf_documents,
            property_files,
            selinux_sources,
        )

        if not all(
            isinstance(
                values,
                tuple,
            )
            for values in collections
        ):
            raise TypeError(
                "extraction result collections "
                "must be tuples"
            )

        return AndroidFilesystemParsingResult(
            init_files=self._sort(
                init_files
            ),
            fstabs=self._sort(
                fstabs
            ),
            ueventd_files=self._sort(
                ueventd_files
            ),
            vintf_documents=self._sort(
                vintf_documents
            ),
            property_files=self._sort(
                property_files
            ),
            selinux_sources=self._sort(
                selinux_sources
            ),
        )

    @staticmethod
    def _sort(
        values: tuple,
    ) -> tuple:
        """
        Sort extracted models by host source path.
        """

        return tuple(
            sorted(
                values,
                key=lambda value: (
                    value.source_path.as_posix()
                ),
            )
        )