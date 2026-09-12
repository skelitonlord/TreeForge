from __future__ import annotations

import io
import shutil
import stat
from enum import StrEnum
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)
from treeforge.core.binary import (
    align_up,
)


class CpioEntryType(
    StrEnum,
):
    """
    Physical CPIO entry type preserved by Extraction.
    """

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    CHARACTER_DEVICE = "character_device"
    BLOCK_DEVICE = "block_device"
    FIFO = "fifo"
    SOCKET = "socket"
    UNKNOWN = "unknown"

@dataclass(
    frozen=True,
    slots=True,
)
class CpioNewcEntry:
    """
    Exact immutable record decoded from one CPIO ``newc`` entry.

    This preserves archive-level evidence exactly as it existed in the CPIO
    container. Later layers may derive normalized filesystem views without
    replacing this source record.
    """

    path: str

    ino: int
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    filesize: int

    devmajor: int
    devminor: int

    rdevmajor: int
    rdevminor: int

    namesize: int
    check: int

    data: bytes

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
                "path cannot be empty"
            )

        for field_name in (
            "ino",
            "mode",
            "uid",
            "gid",
            "nlink",
            "mtime",
            "filesize",
            "devmajor",
            "devminor",
            "rdevmajor",
            "rdevminor",
            "namesize",
            "check",
        ):
            value = getattr(
                self,
                field_name,
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
            ):
                raise TypeError(
                    f"{field_name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative"
                )

        if not isinstance(
            self.data,
            bytes,
        ):
            raise TypeError(
                "data must be bytes"
            )

        if len(
            self.data
        ) != self.filesize:
            raise ValueError(
                "data length must equal filesize"
            )

    @property
    def entry_type(
        self,
    ) -> CpioEntryType:
        file_type = stat.S_IFMT(
            self.mode
        )

        if file_type == stat.S_IFREG:
            return CpioEntryType.FILE

        if file_type == stat.S_IFDIR:
            return CpioEntryType.DIRECTORY

        if file_type == stat.S_IFLNK:
            return CpioEntryType.SYMLINK

        if file_type == stat.S_IFCHR:
            return (
                CpioEntryType
                .CHARACTER_DEVICE
            )

        if file_type == stat.S_IFBLK:
            return (
                CpioEntryType
                .BLOCK_DEVICE
            )

        if file_type == stat.S_IFIFO:
            return CpioEntryType.FIFO

        if file_type == stat.S_IFSOCK:
            return CpioEntryType.SOCKET

        return CpioEntryType.UNKNOWN

    @property
    def symlink_target(
        self,
    ) -> str | None:
        if (
            self.entry_type
            is not CpioEntryType.SYMLINK
        ):
            return None

        return self.data.decode(
            "utf-8",
            errors="surrogateescape",
        )

@dataclass(
    frozen=True,
    slots=True,
)
class CpioExtractionResult:
    """
    Canonical result of physically extracting one CPIO archive.

    Exact CPIO records remain the authoritative metadata evidence produced
    by Extraction. Filesystem-oriented normalization belongs to a later
    interpretation layer.
    """

    artifact: ExtractedArtifact

    entries: tuple[
        CpioNewcEntry,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if (
            self.artifact.operation
            is not ExtractionOperation
            .CPIO_EXTRACTION
        ):
            raise ValueError(
                "artifact must be produced by "
                "CPIO_EXTRACTION"
            )

        if (
            self.artifact.kind
            is not ExtractionArtifactKind
            .DIRECTORY
        ):
            raise ValueError(
                "CPIO extraction artifact must "
                "be a directory"
            )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        for entry in self.entries:
            if not isinstance(
                entry,
                CpioNewcEntry,
            ):
                raise TypeError(
                    "entries must contain "
                    "CpioNewcEntry instances"
                )


class CpioExtractionError(
    RuntimeError,
):
    """
    Raised when a canonical CPIO archive cannot be extracted.
    """


class CpioNewcDecoder:
    """
    Decode Android/Linux CPIO ``newc`` archives.

    The decoder preserves the complete canonical CPIO header
    information required by downstream Extraction consumers.
    """

    MAGIC = b"070701"
    CRC_MAGIC = b"070702"

    HEADER_SIZE = 110

    TRAILER_NAME = (
        "TRAILER!!!"
    )

    def decode(
        self,
        data: bytes,
    ) -> tuple[
        CpioNewcEntry,
        ...,
    ]:
        if not isinstance(
            data,
            bytes,
        ):
            raise TypeError(
                "data must be bytes"
            )

        if not data:
            return ()

        stream = io.BytesIO(
            data
        )

        entries: list[
            CpioNewcEntry
        ] = []

        while True:
            header = self.read_header(
                stream
            )

            path = self.read_name(
                stream,
                header["namesize"],
            )

            if path == self.TRAILER_NAME:
                break

            payload = self.read_file(
                stream,
                header["filesize"],
            )

            entries.append(
                CpioNewcEntry(
                    path=path,
                    ino=header["ino"],
                    mode=header["mode"],
                    uid=header["uid"],
                    gid=header["gid"],
                    nlink=header["nlink"],
                    mtime=header["mtime"],
                    filesize=(
                        header["filesize"]
                    ),
                    devmajor=(
                        header["devmajor"]
                    ),
                    devminor=(
                        header["devminor"]
                    ),
                    rdevmajor=(
                        header["rdevmajor"]
                    ),
                    rdevminor=(
                        header["rdevminor"]
                    ),
                    namesize=(
                        header["namesize"]
                    ),
                    check=header["check"],
                    data=payload,
                )
            )

        return tuple(
            entries
        )

    def read_header(
        self,
        stream: io.BytesIO,
    ) -> dict[
        str,
        int,
    ]:
        if not isinstance(
            stream,
            io.BytesIO,
        ):
            raise TypeError(
                "stream must be a BytesIO"
            )

        header = stream.read(
            self.HEADER_SIZE
        )

        if len(
            header
        ) != self.HEADER_SIZE:
            raise ValueError(
                "Incomplete CPIO header."
            )

        magic = header[
            :6
        ]

        if magic not in (
            self.MAGIC,
            self.CRC_MAGIC,
        ):
            raise ValueError(
                "Invalid CPIO newc magic."
            )

        return {
            "ino": self._read_hex(
                header,
                6,
                14,
            ),
            "mode": self._read_hex(
                header,
                14,
                22,
            ),
            "uid": self._read_hex(
                header,
                22,
                30,
            ),
            "gid": self._read_hex(
                header,
                30,
                38,
            ),
            "nlink": self._read_hex(
                header,
                38,
                46,
            ),
            "mtime": self._read_hex(
                header,
                46,
                54,
            ),
            "filesize": (
                self._read_hex(
                    header,
                    54,
                    62,
                )
            ),
            "devmajor": (
                self._read_hex(
                    header,
                    62,
                    70,
                )
            ),
            "devminor": (
                self._read_hex(
                    header,
                    70,
                    78,
                )
            ),
            "rdevmajor": (
                self._read_hex(
                    header,
                    78,
                    86,
                )
            ),
            "rdevminor": (
                self._read_hex(
                    header,
                    86,
                    94,
                )
            ),
            "namesize": (
                self._read_hex(
                    header,
                    94,
                    102,
                )
            ),
            "check": self._read_hex(
                header,
                102,
                110,
            ),
        }

    def read_name(
        self,
        stream: io.BytesIO,
        namesize: int,
    ) -> str:
        if not isinstance(
            stream,
            io.BytesIO,
        ):
            raise TypeError(
                "stream must be a BytesIO"
            )

        self._validate_non_negative_integer(
            namesize,
            name="namesize",
        )

        name = stream.read(
            namesize
        )

        if len(
            name
        ) != namesize:
            raise ValueError(
                "Incomplete CPIO filename."
            )

        self.align_stream(
            stream,
            self.HEADER_SIZE
            + namesize,
        )

        return (
            name
            .rstrip(
                b"\0"
            )
            .decode(
                "utf-8",
                errors="surrogateescape",
            )
        )

    def read_file(
        self,
        stream: io.BytesIO,
        filesize: int,
    ) -> bytes:
        if not isinstance(
            stream,
            io.BytesIO,
        ):
            raise TypeError(
                "stream must be a BytesIO"
            )

        self._validate_non_negative_integer(
            filesize,
            name="filesize",
        )

        data = stream.read(
            filesize
        )

        if len(
            data
        ) != filesize:
            raise ValueError(
                "Incomplete CPIO file."
            )

        self.align_stream(
            stream,
            filesize,
        )

        return data

    def align_stream(
        self,
        stream: io.BytesIO,
        size: int,
    ) -> None:
        if not isinstance(
            stream,
            io.BytesIO,
        ):
            raise TypeError(
                "stream must be a BytesIO"
            )

        self._validate_non_negative_integer(
            size,
            name="size",
        )

        padding = (
            align_up(
                size,
                4,
            )
            - size
        )

        if padding:
            stream.seek(
                padding,
                io.SEEK_CUR,
            )

    @staticmethod
    def _read_hex(
        header: bytes,
        start: int,
        end: int,
    ) -> int:
        try:
            return int(
                header[
                    start:end
                ],
                16,
            )
        except ValueError as error:
            raise ValueError(
                "Invalid CPIO hexadecimal field."
            ) from error

    @staticmethod
    def _validate_non_negative_integer(
        value: int,
        *,
        name: str,
    ) -> None:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
        ):
            raise TypeError(
                f"{name} must be an integer"
            )

        if value < 0:
            raise ValueError(
                f"{name} must be non-negative"
            )


class CpioExtractor:
    """
    Physically materialize one canonical CPIO archive.

    Exact CPIO records are retained as canonical Extraction evidence.
    Host materialization never creates character devices, block devices, or
    sockets. Their exact archive records remain preserved even when no unsafe
    host node is created.
    """

    def __init__(
        self,
        *,
        decoder: (
            CpioNewcDecoder
            | None
        ) = None,
    ) -> None:
        self._decoder = (
            decoder
            if decoder is not None
            else CpioNewcDecoder()
        )

    def extract(
        self,
        parent: ExtractedArtifact,
        destination: Path,
    ) -> CpioExtractionResult:
        self._validate_parent(
            parent
        )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(
                    destination
                )
            else:
                destination.unlink()

        destination.mkdir(
            parents=True,
            exist_ok=False,
        )

        try:
            archive_data = (
                parent.path.read_bytes()
            )

            entries = (
                self._decoder.decode(
                    archive_data
                )
            )

            seen_paths: set[
                str
            ] = set()

            duplicate_path_count = 0

            for entry in entries:
                if entry.path in seen_paths:
                    duplicate_path_count += 1
                else:
                    seen_paths.add(
                        entry.path
                    )

            materialized_count = 0
            preserved_only_count = 0

            for entry in entries:
                relative_path = (
                    self._safe_relative_path(
                        entry.path
                    )
                )

                if self._materialize_entry(
                    destination=destination,
                    relative_path=relative_path,
                    entry=entry,
                ):
                    materialized_count += 1
                else:
                    preserved_only_count += 1

            directory_artifact = (
                ExtractedArtifact(
                    source=parent.source,
                    path=destination,
                    kind=(
                        ExtractionArtifactKind
                        .DIRECTORY
                    ),
                    operation=(
                        ExtractionOperation
                        .CPIO_EXTRACTION
                    ),
                    semantic_name=(
                        "ramdisk_root"
                    ),
                    parent=parent,
                    tool=(
                        ExtractionToolEvidence(
                            name=(
                                "treeforge-cpio-newc"
                            ),
                        )
                    ),
                    facts=(
                        ExtractionFact(
                            name="entry_count",
                            value=len(
                                entries
                            ),
                        ),
                        ExtractionFact(
                            name=(
                                "duplicate_path_count"
                            ),
                            value=(
                                duplicate_path_count
                            ),
                        ),
                        ExtractionFact(
                            name=(
                                "materialized_entry_count"
                            ),
                            value=materialized_count,
                        ),
                        ExtractionFact(
                            name=(
                                "preserved_only_entry_count"
                            ),
                            value=(
                                preserved_only_count
                            ),
                        ),
                        ExtractionFact(
                            name=(
                                "archive_size_bytes"
                            ),
                            value=len(
                                archive_data
                            ),
                        ),
                    ),
                    content_sha256=(
                        self._directory_digest(
                            entries
                        )
                    ),
                    size_bytes=(
                        self._materialized_size(
                            destination
                        )
                    ),
                )
            )

            return CpioExtractionResult(
                artifact=directory_artifact,
                entries=entries,
            )

        except BaseException:
            if destination.exists():
                shutil.rmtree(
                    destination
                )

            raise

    @staticmethod
    def _validate_parent(
        parent: ExtractedArtifact,
    ) -> None:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise CpioExtractionError(
                "CPIO parent must be a file"
            )

        if (
            parent.operation
            is not ExtractionOperation
            .RAMDISK_DECOMPRESSION
        ):
            raise CpioExtractionError(
                "CPIO extraction requires a "
                "RAMDISK_DECOMPRESSION artifact"
            )

        if (
            parent.semantic_name
            != "ramdisk_cpio"
        ):
            raise CpioExtractionError(
                "CPIO extraction requires "
                "semantic_name='ramdisk_cpio'"
            )

        if not parent.path.exists():
            raise FileNotFoundError(
                parent.path
            )

        if not parent.path.is_file():
            raise CpioExtractionError(
                "CPIO parent must reference "
                f"a regular file: {parent.path}"
            )

    @staticmethod
    def _safe_relative_path(
        value: str,
    ) -> PurePosixPath:
        path = PurePosixPath(
            value
        )

        if path.is_absolute():
            raise CpioExtractionError(
                "CPIO entry path must be relative: "
                f"{value!r}"
            )

        if ".." in path.parts:
            raise CpioExtractionError(
                "CPIO entry path contains "
                f"parent traversal: {value!r}"
            )

        normalized_parts = tuple(
            part
            for part in path.parts
            if part not in (
                "",
                ".",
            )
        )

        if not normalized_parts:
            raise CpioExtractionError(
                "CPIO entry path is empty"
            )

        return PurePosixPath(
            *normalized_parts
        )

    @classmethod
    def _materialize_entry(
        cls,
        *,
        destination: Path,
        relative_path: PurePosixPath,
        entry: CpioNewcEntry,
    ) -> bool:
        output = destination.joinpath(
            *relative_path.parts
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        entry_type = (
            entry.entry_type
        )

        if (
            entry_type
            is CpioEntryType.DIRECTORY
        ):
            output.mkdir(
                parents=True,
                exist_ok=True,
            )

            cls._apply_permissions(
                output,
                entry.mode,
            )

            return True

        if (
            entry_type
            is CpioEntryType.FILE
        ):
            if output.exists() or output.is_symlink():
                cls._remove_existing_path(
                    output
                )

            output.write_bytes(
                entry.data
            )

            cls._apply_permissions(
                output,
                entry.mode,
            )

            return True

        if (
            entry_type
            is CpioEntryType.SYMLINK
        ):
            if output.exists() or output.is_symlink():
                cls._remove_existing_path(
                    output
                )

            target = (
                entry.symlink_target
            )

            if target is None:
                raise CpioExtractionError(
                    "symlink entry has no target: "
                    f"{entry.path}"
                )

            output.symlink_to(
                target
            )

            return True

        if (
            entry_type
            is CpioEntryType.FIFO
        ):
            #
            # Preserve the entry metadata but avoid creating active host IPC
            # objects in the extraction workspace.
            #
            return False

        if entry_type in (
            CpioEntryType
            .CHARACTER_DEVICE,
            CpioEntryType
            .BLOCK_DEVICE,
            CpioEntryType
            .SOCKET,
            CpioEntryType
            .UNKNOWN,
        ):
            return False

        return False

    @staticmethod
    def _remove_existing_path(
        path: Path,
    ) -> None:
        if path.is_symlink():
            path.unlink()
            return

        if path.is_dir():
            shutil.rmtree(
                path
            )
            return

        path.unlink(
            missing_ok=True
        )

    @staticmethod
    def _apply_permissions(
        path: Path,
        mode: int,
    ) -> None:
        path.chmod(
            stat.S_IMODE(
                mode
            )
        )

    @staticmethod
    def _directory_digest(
        entries: tuple[
            CpioNewcEntry,
            ...,
        ],
    ) -> str:
        """
        Deterministic digest of the exact decoded archive records.

        A directory has no single byte stream, so this digest represents the
        ordered CPIO extraction content rather than host filesystem metadata.
        """

        digest = sha256()

        for entry in entries:
            digest.update(
                entry.path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            )
            digest.update(
                b"\0"
            )

            for value in (
                entry.ino,
                entry.mode,
                entry.uid,
                entry.gid,
                entry.nlink,
                entry.mtime,
                entry.filesize,
                entry.devmajor,
                entry.devminor,
                entry.rdevmajor,
                entry.rdevminor,
                entry.namesize,
                entry.check,
            ):
                digest.update(
                    value.to_bytes(
                        8,
                        byteorder="little",
                        signed=False,
                    )
                )

            digest.update(
                entry.data
            )

        return digest.hexdigest()

    @staticmethod
    def _materialized_size(
        root: Path,
    ) -> int:
        size = 0

        for path in root.rglob(
            "*"
        ):
            if path.is_file() and not path.is_symlink():
                size += (
                    path.stat().st_size
                )

        return size