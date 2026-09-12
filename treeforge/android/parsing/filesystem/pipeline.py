from __future__ import annotations

from dataclasses import replace
from pathlib import Path, PurePosixPath
from typing import Protocol

from treeforge.android.parsing.fstab import (
    read_android_fstab,
)
from treeforge.android.parsing.init.rc import (
    InitRcParser,
)
from treeforge.android.parsing.ueventd import (
    ParsedAndroidUeventdFile,
    UeventdParser,
)
from treeforge.android.parsing.vintf import (
    ParsedVintfDocument,
    VintfParser,
)
from treeforge.android.parsing.selinux import (
    AndroidSelinuxParser,
    ParsedAndroidSelinuxFile,
)
from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
    AndroidFilesystemParsingResultBuilder,
    ParsedAndroidFstab,
    ParsedAndroidInitSource,
    ParsedAndroidPropertyFile,
    ParsedAndroidSelinuxSource,
    ParsedAndroidUeventd,
    ParsedAndroidVintfSource,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.properties import (
    classify_android_property_source,
    read_android_properties,
)
from treeforge.android.parsing.init import (
    ParsedAndroidInitFile,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


class InitRcParserLike(
    Protocol
):
    def parse(
        self,
        path: Path,
    ) -> ParsedAndroidInitFile:
        ...


class UeventdParserLike(
    Protocol
):
    def parse(
        self,
        path: Path,
    ) -> ParsedAndroidUeventdFile:
        ...


class VintfParserLike(
    Protocol
):
    def parse(
        self,
        source_path: Path,
    ) -> ParsedVintfDocument:
        ...


class SelinuxParserLike(
    Protocol
):
    def parse(
        self,
        source_path: Path,
    ) -> ParsedAndroidSelinuxFile:
        ...


class AndroidFilesystemParsingPipeline:
    """
    Parse extracted Android configuration sources into canonical models.

    Explicit-path extraction preserves host provenance only because no
    partition identity is available. Inventory-backed extraction additionally
    preserves canonical Android-visible absolute paths.
    """

    _OWNED_SOURCE_KINDS = (
        AndroidModelSourceKind.INIT,
        AndroidModelSourceKind.FSTAB,
        AndroidModelSourceKind.UEVENTD,
        AndroidModelSourceKind.VINTF,
        AndroidModelSourceKind.PROPERTY,
        AndroidModelSourceKind.SELINUX,
    )

    def __init__(
        self,
        *,
        init_parser: InitRcParserLike | None = None,
        ueventd_parser: UeventdParserLike | None = None,
        vintf_parser: VintfParserLike | None = None,
        selinux_parser: SelinuxParserLike | None = None,
        result_builder: (
            AndroidFilesystemParsingResultBuilder
            | None
        ) = None,
        progress_callback: (
            ProgressCallback
            | None
        ) = None,
    ) -> None:
        self.init_parser = (
            init_parser
            if init_parser is not None
            else InitRcParser()
        )

        self.ueventd_parser = (
            ueventd_parser
            if ueventd_parser is not None
            else UeventdParser()
        )

        self.vintf_parser = (
            vintf_parser
            if vintf_parser is not None
            else VintfParser()
        )

        self.selinux_parser = (
            selinux_parser
            if selinux_parser is not None
            else AndroidSelinuxParser()
        )

        self.result_builder = (
            result_builder
            if result_builder is not None
            else AndroidFilesystemParsingResultBuilder()
        )

        self.progress_callback = (
            progress_callback
        )

    def extract_inventory(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidFilesystemParsingResult:
        """
        Extract canonical Android models from one source inventory.

        The inventory owns discovery, partition provenance, and canonical
        source ordering. Parsers consume host paths, while the returned
        models retain both host and canonical Android path identities.
        """

        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source in inventory.sources
            if (
                source.kind
                in self._OWNED_SOURCE_KINDS
            )
        )

        total = len(
            sources
        )

        init_files: list[
            ParsedAndroidInitSource
        ] = []

        fstabs: list[
            ParsedAndroidFstab
        ] = []

        ueventd_files: list[
            ParsedAndroidUeventd
        ] = []

        vintf_documents: list[
            ParsedAndroidVintfSource
        ] = []

        property_files: list[
            ParsedAndroidPropertyFile
        ] = []

        selinux_files: list[
            ParsedAndroidSelinuxSource
        ] = []

        for index, source in enumerate(
            sources
        ):
            self._report_progress(
                source=source,
                processed=index,
                total=total,
                state=ProgressState.RUNNING,
            )

            if (
                source.kind
                is AndroidModelSourceKind.INIT
            ):
                init_files.append(
                    self._extract_init(
                        source
                    )
                )

            elif (
                source.kind
                is AndroidModelSourceKind.FSTAB
            ):
                fstabs.append(
                    self._extract_fstab(
                        source
                    )
                )

            elif (
                source.kind
                is AndroidModelSourceKind.UEVENTD
            ):
                ueventd_files.append(
                    self._extract_ueventd(
                        source
                    )
                )

            elif (
                source.kind
                is AndroidModelSourceKind.VINTF
            ):
                vintf_documents.append(
                    self._extract_vintf(
                        source
                    )
                )

            elif (
                source.kind
                is AndroidModelSourceKind.PROPERTY
            ):
                property_files.append(
                    self._extract_property_file(
                        source
                    )
                )

            elif (
                source.kind
                is AndroidModelSourceKind.SELINUX
            ):
                selinux_files.append(
                    self._extract_selinux(
                        source
                    )
                )

            else:
                raise ValueError(
                    "unsupported Android model source kind: "
                    f"{source.kind}"
                )

            completed = (
                index + 1
            )

            self._report_progress(
                source=source,
                processed=completed,
                total=total,
                state=(
                    ProgressState.COMPLETE
                    if completed == total
                    else ProgressState.RUNNING
                ),
            )

        extracted = self.result_builder.build(
            init_files=self._sorted_parsed_sources(
                init_files
            ),
            fstabs=self._sorted_parsed_sources(
                fstabs
            ),
            ueventd_files=self._sorted_parsed_sources(
                ueventd_files
            ),
            vintf_documents=self._sorted_parsed_sources(
                vintf_documents
            ),
            property_files=self._sorted_parsed_sources(
                property_files
            ),
            selinux_sources=self._sorted_parsed_sources(
                selinux_files
            ),
        )

        result = self._attach_inventory_paths(
            extracted,
            inventory,
        )

        parsed_sources = tuple(
            value.source
            for value
            in (
                *result.init_files,
                *result.fstabs,
                *result.ueventd_files,
                *result.vintf_documents,
                *result.property_files,
                *result.selinux_sources,
            )
        )

        if any(
            source is None
            for source
            in parsed_sources
        ):
            raise ValueError(
                "inventory-backed filesystem Parsing must retain "
                "the exact canonical AndroidModelSource object"
            )

        expected_source_ids = {
            id(source)
            for source
            in sources
        }

        actual_source_ids = {
            id(source)
            for source
            in parsed_sources
        }

        if (
            expected_source_ids
            != actual_source_ids
        ):
            raise ValueError(
                "filesystem Parsing failed to conserve every "
                "canonical owned AndroidModelSource exactly once"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed_sources
        ):
            raise ValueError(
                "filesystem Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return result

    def extract(
        self,
        *,
        init_sources: tuple[
            Path,
            ...,
        ] = (),
        fstab_sources: tuple[
            Path,
            ...,
        ] = (),
        ueventd_sources: tuple[
            Path,
            ...,
        ] = (),
        vintf_sources: tuple[
            Path,
            ...,
        ] = (),
        property_sources: tuple[
            Path,
            ...,
        ] = (),
        selinux_sources: tuple[
            Path,
            ...,
        ] = (),
    ) -> AndroidFilesystemParsingResult:
        """
        Parse all supplied sources and return one immutable extraction result.

        Categories execute in canonical order:

            Init
            fstab
            ueventd
            VINTF
            properties

        Sources within each category execute in canonical host-path order.
        Exceptions propagate immediately and later parsers are not executed.
        """

        self._validate_sources(
            init_sources=init_sources,
            fstab_sources=fstab_sources,
            ueventd_sources=ueventd_sources,
            vintf_sources=vintf_sources,
            property_sources=property_sources,
            selinux_sources=selinux_sources,
        )

        canonical_init_sources = (
            self._canonical_sources(
                init_sources
            )
        )

        canonical_fstab_sources = (
            self._canonical_sources(
                fstab_sources
            )
        )

        canonical_ueventd_sources = (
            self._canonical_sources(
                ueventd_sources
            )
        )

        canonical_vintf_sources = (
            self._canonical_sources(
                vintf_sources
            )
        )

        canonical_property_sources = (
            self._canonical_sources(
                property_sources
            )
        )

        canonical_selinux_sources = (
            self._canonical_sources(
                selinux_sources
            )
        )

        init_files = tuple(
            self._extract_init(
                source
            )
            for source
            in canonical_init_sources
        )

        fstabs = tuple(
            self._extract_fstab(
                source
            )
            for source
            in canonical_fstab_sources
        )

        ueventd_files = tuple(
            self._extract_ueventd(
                source
            )
            for source
            in canonical_ueventd_sources
        )

        vintf_documents = tuple(
            self._extract_vintf(
                source
            )
            for source
            in canonical_vintf_sources
        )

        property_files = tuple(
            self._extract_property_file(
                source
            )
            for source
            in canonical_property_sources
        )

        selinux_files = tuple(
            self._extract_selinux(
                source
            )
            for source
            in canonical_selinux_sources
        )

        return self.result_builder.build(
            init_files=init_files,
            fstabs=fstabs,
            ueventd_files=ueventd_files,
            vintf_documents=vintf_documents,
            property_files=property_files,
            selinux_sources=selinux_files,
        )

    def _report_progress(
        self,
        *,
        source: AndroidModelSource,
        processed: int,
        total: int,
        state: ProgressState,
    ) -> None:
        """
        Publish one real filesystem-source Parsing progress event.

        The source inventory owns source identity and canonical ordering.
        Leaf parsers remain responsible only for decoding one source.
        """

        if self.progress_callback is None:
            return

        self.progress_callback(
            ProgressEvent(
                stage="Filesystem Parsing",
                state=state,
                current=processed,
                total=total,
                detail=source.kind.value,
                subject=source.source_name,
                operation="parsing filesystem source",
                item=source.android_path.as_posix(),
                processed=processed,
            )
        )

    @staticmethod
    def _sorted_parsed_sources(
        values,
    ):
        """
        Preserve the existing parsed-result source-path ordering contract.
        """

        return tuple(
            sorted(
                values,
                key=lambda value: (
                    value.source_path.as_posix()
                ),
            )
        )

    def _attach_inventory_paths(
        self,
        extraction: AndroidFilesystemParsingResult,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidFilesystemParsingResult:
        """
        Attach canonical Android paths without changing parsed model identity.

        Host paths remain exact parser provenance. Android paths preserve
        the canonical Android-visible identity established by the
        filesystem source inventory.
        """

        android_paths = {
            source.host_path: source.android_path
            for source in inventory.sources
        }

        missing_paths = tuple(
            source_path
            for source_path in extraction.source_paths
            if source_path not in android_paths
        )

        if missing_paths:
            raise ValueError(
                "extracted source paths must belong "
                "to the source inventory"
            )

        return self.result_builder.build(
            init_files=tuple(
                replace(
                    extracted,
                    android_path=android_paths[
                        extracted.source_path
                    ],
                )
                for extracted
                in extraction.init_files
            ),
            fstabs=tuple(
                replace(
                    extracted,
                    android_path=android_paths[
                        extracted.source_path
                    ],
                )
                for extracted
                in extraction.fstabs
            ),
            ueventd_files=tuple(
                replace(
                    extracted,
                    android_path=android_paths[
                        extracted.source_path
                    ],
                )
                for extracted
                in extraction.ueventd_files
            ),
            vintf_documents=tuple(
                replace(
                    extracted,
                    android_path=android_paths[
                        extracted.source_path
                    ],
                )
                for extracted
                in extraction.vintf_documents
            ),
            property_files=tuple(
                replace(
                    extracted,
                    android_path=android_paths[
                        extracted.source_path
                    ],
                )
                for extracted
                in extraction.property_files
            ),
            selinux_sources=tuple(
                replace(
                    extracted,
                    android_path=android_paths[
                        extracted.source_path
                    ],
                )
                for extracted
                in extraction.selinux_sources
            ),
        )


    def _extract_init(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidInitSource:
        parsed = self.init_parser.parse(
            source.host_path
        )

        if not isinstance(
            parsed,
            ParsedAndroidInitFile,
        ):
            raise TypeError(
                "init parser must return a "
                "ParsedAndroidInitFile"
            )

        return ParsedAndroidInitSource(
            source_path=source.host_path,
            source=source,
            raw=parsed.raw,
            android_path=source.android_path,
            filesystem_source=(
                source.filesystem_source
            ),
            imports=parsed.imports,
            services=parsed.services,
            actions=parsed.actions,
            unparsed_lines=(
                parsed.unparsed_lines
            ),
        )

    def _extract_fstab(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidFstab:
        parsed = read_android_fstab(
            source.host_path,
            errors="strict",
        )

        return ParsedAndroidFstab(
            source_path=source.host_path,
            source=source,
            android_path=source.android_path,
            filesystem_source=(
                source.filesystem_source
            ),
            declarations=(
                parsed.declarations
            ),
            unparsed_lines=(
                parsed.unparsed_lines
            ),
        )

    def _extract_ueventd(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidUeventd:
        parsed = self.ueventd_parser.parse(
            source.host_path
        )

        if not isinstance(
            parsed,
            ParsedAndroidUeventdFile,
        ):
            raise TypeError(
                "ueventd parser must return a "
                "ParsedAndroidUeventdFile"
            )

        return ParsedAndroidUeventd(
            source_path=source.host_path,
            source=source,
            raw=parsed.raw,
            android_path=source.android_path,
            filesystem_source=(
                source.filesystem_source
            ),
            declarations=(
                parsed.declarations
            ),
            unparsed_lines=(
                parsed.unparsed_lines
            ),
        )

    def _extract_vintf(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidVintfSource:
        parsed = self.vintf_parser.parse(
            source.host_path
        )

        if not isinstance(
            parsed,
            ParsedVintfDocument,
        ):
            raise TypeError(
                "VINTF parser must return a "
                "ParsedVintfDocument"
            )

        return ParsedAndroidVintfSource(
            source_path=source.host_path,
            source=source,
            parsed=parsed,
            android_path=source.android_path,
            filesystem_source=(
                source.filesystem_source
            ),
        )

    def _extract_selinux(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidSelinuxSource:
        parsed = self.selinux_parser.parse(
            source.host_path
        )

        if not isinstance(
            parsed,
            ParsedAndroidSelinuxFile,
        ):
            raise TypeError(
                "SELinux parser must return a "
                "ParsedAndroidSelinuxFile"
            )

        return ParsedAndroidSelinuxSource(
            source_path=source.host_path,
            source=source,
            parsed=parsed,
            android_path=source.android_path,
            filesystem_source=(
                source.filesystem_source
            ),
        )

    def _extract_property_file(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidPropertyFile:
        """
        Parse one Android property source while preserving lexical evidence.
        """

        if not source.host_path.exists():
            raise FileNotFoundError(
                source.host_path
            )

        if not source.host_path.is_file():
            raise IsADirectoryError(
                source.host_path
            )

        kind = classify_android_property_source(
            source.host_path.name
        )

        if kind is None:
            raise ValueError(
                "property source path is not a "
                "recognized Android property source: "
                + source.host_path.as_posix()
            )

        parsed = read_android_properties(
            source.host_path,
            errors="strict",
        )

        return ParsedAndroidPropertyFile(
            kind=kind,
            source_path=source.host_path,
            source=source,
            android_path=source.android_path,
            filesystem_source=(
                source.filesystem_source
            ),
            declarations=(
                parsed.declarations
            ),
            unparsed_lines=(
                parsed.unparsed_lines
            ),
        )

    @staticmethod
    def _validate_sources(
        *,
        init_sources: tuple[Path, ...],
        fstab_sources: tuple[Path, ...],
        ueventd_sources: tuple[Path, ...],
        vintf_sources: tuple[Path, ...],
        property_sources: tuple[
            Path,
            ...,
        ],
        selinux_sources: tuple[
            Path,
            ...,
        ],
    ) -> None:
        collections = (
            (
                "init_sources",
                init_sources,
            ),
            (
                "fstab_sources",
                fstab_sources,
            ),
            (
                "ueventd_sources",
                ueventd_sources,
            ),
            (
                "vintf_sources",
                vintf_sources,
            ),
            (
                "property_sources",
                property_sources,
            ),
            (
                "selinux_sources",
                selinux_sources,
            ),
        )

        all_sources: list[
            Path
        ] = []

        for field_name, sources in collections:
            if not isinstance(
                sources,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    source,
                    Path,
                )
                for source in sources
            ):
                raise TypeError(
                    f"{field_name} must contain only Paths"
                )

            all_sources.extend(
                sources
            )

        if len(
            all_sources
        ) != len(
            set(
                all_sources
            )
        ):
            raise ValueError(
                "extraction source paths must be unique"
            )

    @staticmethod
    def _canonical_sources(
        sources: tuple[
            Path,
            ...,
        ],
    ) -> tuple[
        Path,
        ...,
    ]:
        return tuple(
            sorted(
                sources,
                key=lambda source: (
                    source.as_posix()
                ),
            )
        )