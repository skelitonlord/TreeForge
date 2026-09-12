from __future__ import annotations

from pathlib import Path
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile
from zipfile import (
    BadZipFile,
    ZipFile,
    ZipInfo,
)

from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactClassification,
    ProviderArtifactKind,
    ProviderArtifactKindEvidence,
)
from treeforge.android.providers.artifact_classifier import (
    ProviderArtifactClassifier,
)
from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.android.providers.provenance import (
    ProviderArtifactProvenance,
)
from treeforge.android.providers.content_inspector import (
    ProviderContentInspector,
)
from treeforge.android.providers.content_observation import (
    ProviderContentSignature,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


class ProviderArchiveScanError(
    RuntimeError,
):
    """
    Raised when a provider archive cannot be inventoried.
    """


class ProviderArchiveScanner:
    """
    Recursively discover every regular member reachable through ZIP archives.

    Discovery is structural and exhaustive.

    Semantic classification never controls whether an artifact is discovered.

    Every regular archive member becomes exactly one ProviderArtifact,
    including artifacts whose kind or semantic classification is UNKNOWN.

    Any member whose contents form a valid ZIP archive is recursively scanned
    regardless of its filename, extension, or semantic classification.

    The scanner performs discovery only. Persistent materialization, parsing,
    filesystem extraction, image interpretation, and Android-specific
    processing belong to later layers.
    """

    _ZIP_SIGNATURES = (
        b"PK\x03\x04",
        b"PK\x05\x06",
        b"PK\x07\x08",
    )

    _COPY_CHUNK_SIZE = (
        1024 * 1024
    )

    _SPOOL_MEMORY_LIMIT = (
        64 * 1024 * 1024
    )

    def __init__(
        self,
        *,
        classifier: (
            ProviderArtifactClassifier
            | None
        ) = None,
        content_inspector: (
            ProviderContentInspector
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
        progress_stage: str = "Provider Archive Discovery",
    ) -> None:
        self.classifier = (
            classifier
            if classifier is not None
            else ProviderArtifactClassifier()
        )

        self.content_inspector = (
            content_inspector
            if content_inspector is not None
            else ProviderContentInspector()
        )

        self.progress_callback = (
            progress_callback
        )

        self.progress_stage = (
            progress_stage
        )

    def scan(
        self,
        archive_path: Path,
        *,
        provider_id: str,
        source_type: ProviderSourceType,
        parent_source_name: str | None = None,
    ) -> ProviderArtifactInventory:
        """
        Recursively inventory every regular member reachable from one ZIP.

        The root ZIP itself is the discovery source and is not inserted as a
        child artifact.

        Nested source identities are hierarchical:

            factory.zip!/member
            factory.zip!/nested.zip!/member
            factory.zip!/nested.zip!/deeper.zip!/member

        Nested ZIP traversal is based on actual ZIP structure, not filenames.
        """

        self._validate_archive_path(
            archive_path
        )
        self._validate_provider_id(
            provider_id
        )
        self._validate_source_type(
            source_type
        )
        self._validate_parent_source_name(
            parent_source_name
        )

        archive_source_name = (
            parent_source_name
            if parent_source_name
            is not None
            else archive_path.name
        )

        artifacts: list[
            ProviderArtifact
        ] = []

        regular_members_encountered = [0]

        self._report_progress(
            state=ProgressState.STARTING,
            operation="opening factory archive",
            item=archive_path.name,
            subject=archive_source_name,
            processed=0,
        )

        try:
            with ZipFile(
                archive_path,
                "r",
            ) as archive:
                self._scan_archive(
                    archive=archive,
                    archive_source_name=(
                        archive_source_name
                    ),
                    provider_id=provider_id,
                    source_type=source_type,
                    artifacts=artifacts,
                    regular_members_encountered=(
                        regular_members_encountered
                    ),
                )

        except BadZipFile as error:
            raise ProviderArchiveScanError(
                "provider archive is not "
                f"a valid ZIP file: {archive_path}"
            ) from error

        except OSError as error:
            raise ProviderArchiveScanError(
                "unable to read provider archive: "
                f"{archive_path}"
            ) from error

        if (
            regular_members_encountered[0]
            != len(artifacts)
        ):
            raise ProviderArchiveScanError(
                "provider archive discovery accounting "
                "did not close: "
                "regular members encountered="
                f"{regular_members_encountered[0]}, "
                "artifacts emitted="
                f"{len(artifacts)}"
            )

        self._report_progress(
            state=ProgressState.COMPLETE,
            operation="factory archive discovery complete",
            item=archive_path.name,
            subject=archive_source_name,
            processed=len(artifacts),
        )

        return ProviderArtifactInventory(
            artifacts=tuple(
                artifacts
            )
        )

    def _scan_archive(
        self,
        *,
        archive: ZipFile,
        archive_source_name: str,
        provider_id: str,
        source_type: ProviderSourceType,
        artifacts: list[
            ProviderArtifact
        ],
        regular_members_encountered: list[int],
    ) -> None:
        """
        Discover one ZIP level and recursively inspect nested ZIP members.
        """

        for member in archive.infolist():
            if member.is_dir():
                continue

            member_name = (
                member.filename
            )

            if not member_name:
                raise ProviderArchiveScanError(
                    "regular archive member has an empty filename"
                )

            regular_members_encountered[0] += 1

            source_name = (
                self._child_source_name(
                    archive_source_name,
                    member_name,
                )
            )

            self._report_progress(
                state=ProgressState.RUNNING,
                operation="inspecting archive member",
                item=self._basename(
                    member_name
                ),
                subject=self._archive_display_name(
                    archive_source_name
                ),
                processed=len(artifacts),
            )

            content_prefix = (
                self._read_member_prefix(
                    archive=archive,
                    member=member,
                )
            )

            content_observations = (
                self.content_inspector.inspect(
                    content_prefix
                )
            )

            kind = (
                self.classifier.classify_kind(
                    member_name
                )
            )

            if (
                kind
                is ProviderArtifactKind.UNKNOWN
            ):
                kind_evidence = (
                    ProviderArtifactKindEvidence.UNKNOWN
                )
            else:
                kind_evidence = (
                    ProviderArtifactKindEvidence.FILENAME
                )

            (
                content_kind,
                content_kind_is_known,
            ) = self._kind_from_content_observations(
                content_observations
            )

            if content_kind_is_known:
                kind = content_kind

                kind_evidence = (
                    ProviderArtifactKindEvidence.CONTENT
                )

            is_zip_candidate = (
                ProviderContentSignature.ZIP
                in {
                    observation.signature
                    for observation
                    in content_observations
                }
            )

            if is_zip_candidate:
                self._report_progress(
                    state=ProgressState.RUNNING,
                    operation="opening nested archive",
                    item=self._basename(
                        member_name
                    ),
                    subject=self._archive_display_name(
                        archive_source_name
                    ),
                    processed=len(artifacts),
                )

            nested_archive = None

            if is_zip_candidate:
                nested_archive = (
                    self._open_nested_archive(
                        archive=archive,
                        member=member,
                    )
                )

            if nested_archive is not None:
                kind = (
                    ProviderArtifactKind.ARCHIVE
                )

                kind_evidence = (
                    ProviderArtifactKindEvidence.CONTENT
                )

            artifacts.append(
                ProviderArtifact(
                    source_name=source_name,
                    name=(
                        self._basename(
                            member_name
                        )
                    ),
                    content_observations=(
                        content_observations
                    ),
                    kind=kind,
                    classification=(
                        ProviderArtifactClassification.UNKNOWN
                    ),
                    kind_evidence=(
                        kind_evidence
                    ),
                    provider_id=provider_id,
                    source_type=source_type,
                    provenance=(
                        ProviderArtifactProvenance(
                            parent_source_name=(
                                archive_source_name
                            ),
                            member_path=(
                                member.filename
                            ),
                            original_member_path=(
                                member.orig_filename
                            ),
                            container_depth=(
                                self._container_depth(
                                    source_name
                                )
                            ),
                            size_bytes=(
                                member.file_size
                            ),
                            compressed_size_bytes=(
                                member.compress_size
                            ),
                            compression_method=(
                                member.compress_type
                            ),
                            crc32=member.CRC,
                            modified_time=tuple(
                                member.date_time
                            ),
                            flag_bits=(
                                member.flag_bits
                            ),
                            create_system=(
                                member.create_system
                            ),
                            create_version=(
                                member.create_version
                            ),
                            extract_version=(
                                member.extract_version
                            ),
                            volume=(
                                member.volume
                            ),
                            internal_attributes=(
                                member.internal_attr
                            ),
                            external_attributes=(
                                member.external_attr
                            ),
                            extra=bytes(
                                member.extra
                            ),
                            comment=bytes(
                                member.comment
                            ),
                            header_offset=(
                                member.header_offset
                            ),
                        )
                    ),
                )
            )

            self._report_progress(
                state=ProgressState.RUNNING,
                operation="discovered provider artifact",
                item=self._basename(
                    member_name
                ),
                subject=self._archive_display_name(
                    archive_source_name
                ),
                processed=len(artifacts),
            )

            if nested_archive is None:
                continue

            self._report_progress(
                state=ProgressState.RUNNING,
                operation="scanning nested archive",
                item=self._basename(
                    member_name
                ),
                subject=self._archive_display_name(
                    source_name
                ),
                processed=len(artifacts),
            )

            try:
                with nested_archive:
                    self._scan_archive(
                        archive=nested_archive,
                        archive_source_name=(
                            source_name
                        ),
                        provider_id=provider_id,
                        source_type=source_type,
                        artifacts=artifacts,
                        regular_members_encountered=(
                            regular_members_encountered
                        ),
                    )
            except BadZipFile:
                # A signature match alone is not enough to make discovery
                # depend on the object being a valid nested ZIP.
                continue

    def _open_nested_archive(
        self,
        *,
        archive: ZipFile,
        member: ZipInfo,
    ) -> ZipFile | None:
        """
        Return a readable nested ZIP when the member structurally contains one.

        Filename and extension are intentionally ignored.

        A spooled temporary file avoids loading large nested archives entirely
        into memory. Small archives stay in memory; larger ones spill to the
        host temporary directory.
        """

        try:
            with archive.open(
                member,
                "r",
            ) as source:
                temporary = (
                    SpooledTemporaryFile(
                        max_size=(
                            self._SPOOL_MEMORY_LIMIT
                        ),
                        mode="w+b",
                    )
                )

                copyfileobj(
                    source,
                    temporary,
                    length=(
                        self._COPY_CHUNK_SIZE
                    ),
                )

                temporary.seek(
                    0
                )

        except (
            OSError,
            RuntimeError,
        ) as error:
            raise ProviderArchiveScanError(
                "unable to read archive member while "
                "checking for nested ZIP structure: "
                f"{member.filename}"
            ) from error

        try:
            nested = ZipFile(
                temporary,
                "r",
            )

            # Force central-directory access now so an invalid file does not
            # escape as a seemingly valid nested archive.
            nested.infolist()

        except BadZipFile:
            temporary.close()
            return None

        return nested

    def _read_member_prefix(
        self,
        *,
        archive: ZipFile,
        member: ZipInfo,
    ) -> bytes:
        """
        Read only enough member bytes for Discovery content inspection.

        No persistent materialization occurs.
        """

        try:
            with archive.open(
                member,
                "r",
            ) as source:
                return source.read(
                    self.content_inspector
                    .INSPECTION_SIZE
                )

        except (
            OSError,
            RuntimeError,
        ) as error:
            raise ProviderArchiveScanError(
                "unable to inspect archive member: "
                f"{member.filename}"
            ) from error

    @staticmethod
    def _kind_from_content_observations(
        observations,
    ) -> tuple[
        ProviderArtifactKind,
        bool,
    ]:
        """
        Derive only a broad structural kind from byte-level observations.

        This method deliberately does not assign Android semantic
        classification.
        """

        signatures = {
            observation.signature
            for observation
            in observations
        }

        if (
            ProviderContentSignature.ZIP
            in signatures
            or ProviderContentSignature.CPIO_NEWC
            in signatures
            or ProviderContentSignature.CPIO_CRC
            in signatures
        ):
            return (
                ProviderArtifactKind.ARCHIVE,
                True,
            )

        if signatures.intersection(
            {
                ProviderContentSignature
                .FBPK_CONTAINER,
                ProviderContentSignature
                .ANDROID_BOOT_FAMILY,
                ProviderContentSignature
                .ANDROID_VENDOR_BOOT_FAMILY,
                ProviderContentSignature
                .ANDROID_SPARSE,
                ProviderContentSignature
                .ANDROID_VERIFIED_BOOT,
                ProviderContentSignature
                .ANDROID_DT_TABLE,
                ProviderContentSignature
                .ANDROID_LP_METADATA,
                ProviderContentSignature
                .EXT4,
                ProviderContentSignature
                .EROFS,
                ProviderContentSignature
                .DEVICE_TREE_BLOB,
            }
        ):
            return (
                ProviderArtifactKind.IMAGE,
                True,
            )

        if (
            ProviderContentSignature
            .SHEBANG
            in signatures
        ):
            return (
                ProviderArtifactKind.SCRIPT,
                True,
            )

        if signatures.intersection(
            {
                ProviderContentSignature.ELF,
                ProviderContentSignature
                .DOS_EXECUTABLE,
                ProviderContentSignature.GZIP,
                ProviderContentSignature.LZ4,
                ProviderContentSignature
                .LZ4_LEGACY,
                ProviderContentSignature.ZSTD,
                ProviderContentSignature.XZ,
                ProviderContentSignature
                .LZMA_ALONE,
            }
        ):
            return (
                ProviderArtifactKind.BINARY,
                True,
            )

        if (
            ProviderContentSignature
            .TEXT_LIKE
            in signatures
        ):
            return (
                ProviderArtifactKind.TEXT,
                True,
            )

        return (
            ProviderArtifactKind.UNKNOWN,
            False,
        )

    def _report_progress(
        self,
        *,
        state: ProgressState,
        operation: str,
        item: str,
        subject: str,
        processed: int,
    ) -> None:
        if self.progress_callback is None:
            return

        self.progress_callback(
            ProgressEvent(
                stage=self.progress_stage,
                state=state,
                subject=subject,
                operation=operation,
                item=item,
                processed=processed,
            )
        )

    @staticmethod
    def _archive_display_name(
        source_name: str,
    ) -> str:
        if "!/" in source_name:
            return source_name.rsplit(
                "!/",
                1,
            )[1]

        return source_name

    @staticmethod
    def _container_depth(
        source_name: str,
    ) -> int:
        """
        Return the number of archive-container boundaries in a source identity.
        """

        return source_name.count(
            "!/"
        )

    @staticmethod
    def _child_source_name(
        parent_source_name: str,
        member_name: str,
    ) -> str:
        """
        Build one deterministic hierarchical discovery identity.
        """

        normalized_member = (
            member_name.lstrip(
                "/"
            )
        )

        return (
            f"{parent_source_name}"
            f"!/{normalized_member}"
        )

    @staticmethod
    def _basename(
        member_name: str,
    ) -> str:
        """
        Return the final POSIX archive-path component.
        """

        normalized = (
            member_name.rstrip(
                "/"
            )
        )

        if "/" not in normalized:
            return normalized

        return normalized.rsplit(
            "/",
            1,
        )[1]

    @staticmethod
    def _validate_archive_path(
        archive_path: Path,
    ) -> None:
        if not isinstance(
            archive_path,
            Path,
        ):
            raise TypeError(
                "archive_path must be a pathlib.Path"
            )

        if not archive_path.exists():
            raise FileNotFoundError(
                archive_path
            )

        if archive_path.is_dir():
            raise IsADirectoryError(
                archive_path
            )

        if not archive_path.is_file():
            raise ProviderArchiveScanError(
                "archive_path must be a "
                "regular file"
            )

    @staticmethod
    def _validate_provider_id(
        provider_id: str,
    ) -> None:
        if not isinstance(
            provider_id,
            str,
        ):
            raise TypeError(
                "provider_id must be a string"
            )

        if not provider_id.strip():
            raise ValueError(
                "provider_id must not be empty"
            )

    @staticmethod
    def _validate_source_type(
        source_type: ProviderSourceType,
    ) -> None:
        if not isinstance(
            source_type,
            ProviderSourceType,
        ):
            raise TypeError(
                "source_type must be a "
                "ProviderSourceType"
            )

    @staticmethod
    def _validate_parent_source_name(
        parent_source_name: str | None,
    ) -> None:
        if (
            parent_source_name
            is not None
            and not isinstance(
                parent_source_name,
                str,
            )
        ):
            raise TypeError(
                "parent_source_name must be "
                "a string or None"
            )

        if (
            parent_source_name
            is not None
            and not parent_source_name.strip()
        ):
            raise ValueError(
                "parent_source_name must not be empty"
            )