from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from os import stat_result
from pathlib import Path

from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderSourceFilesystemProvenance:
    """
    Immutable host-filesystem provenance for one observed provider source.

    These values describe the particular host filesystem object TreeForge
    observed.

    They are provenance and diagnostic evidence only. They do not determine
    source-content equivalence because copying identical source bytes can
    change these values without changing the source itself.
    """

    modified_time_ns: int
    change_time_ns: int

    mode: int
    uid: int
    gid: int

    inode: int
    device: int
    link_count: int
    device_type: int

    block_size: int | None = None
    blocks: int | None = None
    birth_time_ns: int | None = None

    def __post_init__(
        self,
    ) -> None:
        for (
            field_name,
            value,
        ) in (
            (
                "modified_time_ns",
                self.modified_time_ns,
            ),
            (
                "change_time_ns",
                self.change_time_ns,
            ),
            (
                "mode",
                self.mode,
            ),
            (
                "uid",
                self.uid,
            ),
            (
                "gid",
                self.gid,
            ),
            (
                "inode",
                self.inode,
            ),
            (
                "device",
                self.device,
            ),
            (
                "link_count",
                self.link_count,
            ),
            (
                "device_type",
                self.device_type,
            ),
        ):
            self._validate_nonnegative_int(
                value,
                field_name=field_name,
                optional=False,
            )

        for (
            field_name,
            value,
        ) in (
            (
                "block_size",
                self.block_size,
            ),
            (
                "blocks",
                self.blocks,
            ),
            (
                "birth_time_ns",
                self.birth_time_ns,
            ),
        ):
            self._validate_nonnegative_int(
                value,
                field_name=field_name,
            )

    @classmethod
    def from_stat(
        cls,
        source_stat: stat_result,
    ) -> ProviderSourceFilesystemProvenance:
        """
        Build filesystem provenance from one stat result.

        Platform-specific fields that are unavailable remain None.
        """

        if not isinstance(
            source_stat,
            stat_result,
        ):
            raise TypeError(
                "source_stat must be an os.stat_result"
            )

        birth_time_ns = getattr(
            source_stat,
            "st_birthtime_ns",
            None,
        )

        if birth_time_ns is None:
            birth_time = getattr(
                source_stat,
                "st_birthtime",
                None,
            )

            if birth_time is not None:
                birth_time_ns = int(
                    birth_time
                    * 1_000_000_000
                )

        return cls(
            modified_time_ns=(
                source_stat.st_mtime_ns
            ),
            change_time_ns=(
                source_stat.st_ctime_ns
            ),
            mode=source_stat.st_mode,
            uid=source_stat.st_uid,
            gid=source_stat.st_gid,
            inode=source_stat.st_ino,
            device=source_stat.st_dev,
            link_count=source_stat.st_nlink,
            device_type=source_stat.st_rdev,
            block_size=getattr(
                source_stat,
                "st_blksize",
                None,
            ),
            blocks=getattr(
                source_stat,
                "st_blocks",
                None,
            ),
            birth_time_ns=(
                birth_time_ns
            ),
        )

    @staticmethod
    def _validate_nonnegative_int(
        value: object,
        *,
        field_name: str,
        optional: bool = True,
    ) -> None:
        if value is None:
            if optional:
                return

            raise TypeError(
                f"{field_name} must be an int"
            )

        if not isinstance(
            value,
            int,
        ):
            suffix = (
                " or None"
                if optional
                else ""
            )

            raise TypeError(
                f"{field_name} must be an int"
                f"{suffix}"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} must not be negative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderSourceIdentity:
    """
    Immutable identity and original-source provenance for one provider source.

    Stable content identity consists of:

        provider_id
        source_type
        size
        sha256

    supplied_path preserves the path presented to TreeForge.

    path preserves the canonical resolved host path used to access the source.

    filesystem_provenance preserves host filesystem evidence but is not part
    of source-content equivalence.
    """

    provider_id: str
    source_type: ProviderSourceType

    supplied_path: Path
    path: Path

    size: int
    sha256: str

    filesystem_provenance: ProviderSourceFilesystemProvenance

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.provider_id,
            str,
        ):
            raise TypeError(
                "provider_id must be a string"
            )

        if not self.provider_id.strip():
            raise ValueError(
                "provider_id must not be empty"
            )

        if not isinstance(
            self.source_type,
            ProviderSourceType,
        ):
            raise TypeError(
                "source_type must be a ProviderSourceType"
            )

        if not isinstance(
            self.supplied_path,
            Path,
        ):
            raise TypeError(
                "supplied_path must be a Path"
            )

        if not isinstance(
            self.path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        if not isinstance(
            self.size,
            int,
        ):
            raise TypeError(
                "size must be an integer"
            )

        if self.size < 0:
            raise ValueError(
                "size must not be negative"
            )

        if not isinstance(
            self.sha256,
            str,
        ):
            raise TypeError(
                "sha256 must be a string"
            )

        if len(
            self.sha256
        ) != 64:
            raise ValueError(
                "sha256 must be a 64-character "
                "hexadecimal digest"
            )

        try:
            int(
                self.sha256,
                16,
            )
        except ValueError as exc:
            raise ValueError(
                "sha256 must be a 64-character "
                "hexadecimal digest"
            ) from exc

        object.__setattr__(
            self,
            "sha256",
            self.sha256.lower(),
        )

        if not isinstance(
            self.filesystem_provenance,
            ProviderSourceFilesystemProvenance,
        ):
            raise TypeError(
                "filesystem_provenance must be a "
                "ProviderSourceFilesystemProvenance"
            )

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        provider_id: str,
        source_type: ProviderSourceType,
        progress_callback: ProgressCallback | None = None,
        progress_stage: str = "Provider Source Identity",
        progress_subject: str | None = None,
    ) -> ProviderSourceIdentity:
        """
        Build complete identity and provenance from one file-backed source.

        The file is streamed to avoid loading large factory archives into
        memory.

        TreeForge records filesystem evidence from the same open file
        descriptor used to calculate the content digest and rejects a source
        that changes while it is being hashed.
        """

        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a Path"
            )

        supplied_path = path

        observed_path = (
            path.expanduser()
        )

        if not observed_path.exists():
            raise FileNotFoundError(
                observed_path
            )

        if not observed_path.is_file():
            raise ValueError(
                "source path must be a file"
            )

        resolved_path = (
            observed_path.resolve()
        )

        digest = sha256()

        with resolved_path.open(
            "rb"
        ) as source:
            stat_before = os.fstat(
                source.fileno()
            )

            total_bytes = (
                stat_before.st_size
            )

            processed_bytes = 0

            if progress_callback is not None:
                progress_callback(
                    ProgressEvent(
                        stage=progress_stage,
                        state=ProgressState.STARTING,
                        current=0,
                        total=total_bytes,
                        subject=(
                            progress_subject
                            or resolved_path.name
                        ),
                        operation=(
                            "hashing provider source"
                        ),
                        item=resolved_path.name,
                    )
                )

            while True:
                chunk = source.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

                processed_bytes += len(
                    chunk
                )

                if progress_callback is not None:
                    progress_callback(
                        ProgressEvent(
                            stage=progress_stage,
                            state=ProgressState.RUNNING,
                            current=processed_bytes,
                            total=total_bytes,
                            subject=(
                                progress_subject
                                or resolved_path.name
                            ),
                            operation=(
                                "hashing provider source"
                            ),
                            item=resolved_path.name,
                            processed=processed_bytes,
                        )
                    )

            stat_after = os.fstat(
                source.fileno()
            )

        cls._validate_stable_source(
            stat_before,
            stat_after,
        )

        if progress_callback is not None:
            progress_callback(
                ProgressEvent(
                    stage=progress_stage,
                    state=ProgressState.COMPLETE,
                    current=stat_after.st_size,
                    total=stat_after.st_size,
                    subject=(
                        progress_subject
                        or resolved_path.name
                    ),
                    operation=(
                        "factory source identity established"
                    ),
                    item=resolved_path.name,
                    processed=stat_after.st_size,
                )
            )

        return cls(
            provider_id=provider_id,
            source_type=source_type,
            supplied_path=supplied_path,
            path=resolved_path,
            size=stat_after.st_size,
            sha256=digest.hexdigest(),
            filesystem_provenance=(
                ProviderSourceFilesystemProvenance.from_stat(
                    stat_after
                )
            ),
        )

    @staticmethod
    def _validate_stable_source(
        before: stat_result,
        after: stat_result,
    ) -> None:
        """
        Reject a source whose identity changed while it was being read.
        """

        if not isinstance(
            before,
            stat_result,
        ):
            raise TypeError(
                "before must be an os.stat_result"
            )

        if not isinstance(
            after,
            stat_result,
        ):
            raise TypeError(
                "after must be an os.stat_result"
            )

        if (
            before.st_dev
            != after.st_dev
            or before.st_ino
            != after.st_ino
        ):
            raise RuntimeError(
                "provider source identity changed "
                "while the source was being read"
            )

        if (
            before.st_size
            != after.st_size
            or before.st_mtime_ns
            != after.st_mtime_ns
            or before.st_ctime_ns
            != after.st_ctime_ns
        ):
            raise RuntimeError(
                "provider source contents changed "
                "while the source was being hashed"
            )

    @property
    def content_identity(
        self,
    ) -> tuple[
        str,
        ProviderSourceType,
        int,
        str,
    ]:
        """
        Return the fields defining source-content equivalence.
        """

        return (
            self.provider_id,
            self.source_type,
            self.size,
            self.sha256,
        )

    @property
    def was_path_resolved(
        self,
    ) -> bool:
        """
        Return whether the supplied path differs from the canonical path.
        """

        return (
            self.supplied_path
            != self.path
        )