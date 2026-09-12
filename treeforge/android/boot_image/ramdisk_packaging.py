from __future__ import annotations

import gzip
import lzma
import struct

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import lz4.block
import lz4.frame
import zstandard

from treeforge.android.extraction.cpio.extractor import (
    CpioNewcDecoder,
    CpioNewcEntry,
)
from treeforge.android.format.compression import (
    CompressionFormat,
    LZ4_LEGACY_MAGIC,
)


LZ4_LEGACY_BLOCK_SIZE = (
    8 * 1024 * 1024
)


class AndroidBootImageRamdiskPackagingError(
    RuntimeError
):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageRamdiskPackageResult:
    """
    Physical replacement ramdisk produced from an exact canonical CPIO
    population.

    ``entries`` retains the exact caller-owned CpioNewcEntry identities and
    order. The host filesystem is never consulted for archive metadata.
    """

    entries: tuple[
        CpioNewcEntry,
        ...,
    ]

    compression: CompressionFormat

    cpio_path: Path
    ramdisk_path: Path

    cpio_size_bytes: int
    ramdisk_size_bytes: int

    cpio_sha256: str
    ramdisk_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                CpioNewcEntry,
            )
            for entry
            in self.entries
        ):
            raise TypeError(
                "entries must contain only CpioNewcEntry"
            )

        if not isinstance(
            self.compression,
            CompressionFormat,
        ):
            raise TypeError(
                "compression must be a CompressionFormat"
            )

        if not isinstance(
            self.cpio_path,
            Path,
        ):
            raise TypeError(
                "cpio_path must be a Path"
            )

        if not isinstance(
            self.ramdisk_path,
            Path,
        ):
            raise TypeError(
                "ramdisk_path must be a Path"
            )


class AndroidBootImageNewcWriter:
    """
    Deterministically serialize exact canonical CPIO ``newc`` records.

    Archive entry ordering and metadata come exclusively from CpioNewcEntry.
    """

    MAGIC = b"070701"

    @staticmethod
    def _padding(
        size: int,
    ) -> bytes:
        return b"\x00" * (
            (-size) % 4
        )

    @staticmethod
    def _hex(
        value: int,
    ) -> bytes:
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
            or value > 0xFFFFFFFF
        ):
            raise AndroidBootImageRamdiskPackagingError(
                "CPIO newc field is outside unsigned 32-bit range: "
                f"{value!r}"
            )

        return (
            f"{value:08x}"
            .encode(
                "ascii"
            )
        )

    def _record(
        self,
        *,
        path: str,
        ino: int,
        mode: int,
        uid: int,
        gid: int,
        nlink: int,
        mtime: int,
        data: bytes,
        devmajor: int,
        devminor: int,
        rdevmajor: int,
        rdevminor: int,
        check: int,
    ) -> bytes:
        try:
            name = (
                path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
                + b"\x00"
            )
        except UnicodeEncodeError as error:
            raise AndroidBootImageRamdiskPackagingError(
                f"unable to encode CPIO path: {path!r}"
            ) from error

        fields = (
            ino,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            len(data),
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            len(name),
            check,
        )

        header = (
            self.MAGIC
            + b"".join(
                self._hex(
                    value
                )
                for value
                in fields
            )
        )

        if len(
            header
        ) != CpioNewcDecoder.HEADER_SIZE:
            raise AndroidBootImageRamdiskPackagingError(
                "internal CPIO newc header-size mismatch"
            )

        result = bytearray(
            header
        )

        result.extend(
            name
        )

        result.extend(
            self._padding(
                len(header)
                + len(name)
            )
        )

        result.extend(
            data
        )

        result.extend(
            self._padding(
                len(data)
            )
        )

        return bytes(
            result
        )

    def serialize(
        self,
        entries: tuple[
            CpioNewcEntry,
            ...,
        ],
    ) -> bytes:
        if not isinstance(
            entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        output = bytearray()

        for entry in entries:
            if not isinstance(
                entry,
                CpioNewcEntry,
            ):
                raise TypeError(
                    "entries must contain only CpioNewcEntry"
                )

            encoded_name_size = len(
                entry.path.encode(
                    "utf-8",
                    errors="surrogateescape",
                )
            ) + 1

            if (
                entry.namesize
                != encoded_name_size
            ):
                raise AndroidBootImageRamdiskPackagingError(
                    "canonical CPIO namesize does not match path encoding: "
                    f"{entry.path!r}: "
                    f"canonical={entry.namesize} "
                    f"encoded={encoded_name_size}"
                )

            if (
                entry.filesize
                != len(
                    entry.data
                )
            ):
                raise AndroidBootImageRamdiskPackagingError(
                    "canonical CPIO filesize does not match payload length: "
                    f"{entry.path!r}"
                )

            output.extend(
                self._record(
                    path=entry.path,
                    ino=entry.ino,
                    mode=entry.mode,
                    uid=entry.uid,
                    gid=entry.gid,
                    nlink=entry.nlink,
                    mtime=entry.mtime,
                    data=entry.data,
                    devmajor=entry.devmajor,
                    devminor=entry.devminor,
                    rdevmajor=entry.rdevmajor,
                    rdevminor=entry.rdevminor,
                    check=entry.check,
                )
            )

        #
        # TRAILER!!! is archive structure rather than a canonical filesystem
        # member. It is therefore synthesized by the serializer.
        #
        output.extend(
            self._record(
                path=CpioNewcDecoder.TRAILER_NAME,
                ino=0,
                mode=0,
                uid=0,
                gid=0,
                nlink=1,
                mtime=0,
                data=b"",
                devmajor=0,
                devminor=0,
                rdevmajor=0,
                rdevminor=0,
                check=0,
            )
        )

        return bytes(
            output
        )


class AndroidBootImageRamdiskCompressor:
    """
    Generic inverse of TreeForge's ramdisk CompressionProcessor.

    Compression format is supplied by canonical ramdisk evidence; this class
    never selects a format from partition/device names.
    """

    @staticmethod
    def _compress_lz4_legacy(
        data: bytes,
    ) -> bytes:
        output = bytearray(
            LZ4_LEGACY_MAGIC
        )

        for offset in range(
            0,
            len(data),
            LZ4_LEGACY_BLOCK_SIZE,
        ):
            block = data[
                offset:
                offset
                + LZ4_LEGACY_BLOCK_SIZE
            ]

            compressed = (
                lz4.block.compress(
                    block,
                    store_size=False,
                )
            )

            output.extend(
                struct.pack(
                    "<I",
                    len(
                        compressed
                    ),
                )
            )

            output.extend(
                compressed
            )

        #
        # Explicit end marker accepted by TreeForge's existing legacy-LZ4
        # decompressor.
        #
        output.extend(
            struct.pack(
                "<I",
                0,
            )
        )

        return bytes(
            output
        )

    def compress(
        self,
        data: bytes,
        compression: CompressionFormat,
    ) -> bytes:
        if not isinstance(
            data,
            bytes,
        ):
            raise TypeError(
                "data must be bytes"
            )

        if not isinstance(
            compression,
            CompressionFormat,
        ):
            raise TypeError(
                "compression must be a CompressionFormat"
            )

        if compression is CompressionFormat.NONE:
            return data

        if compression is CompressionFormat.GZIP:
            return gzip.compress(
                data,
                mtime=0,
            )

        if compression is CompressionFormat.LZ4:
            return lz4.frame.compress(
                data,
            )

        if compression is CompressionFormat.LZ4_LEGACY:
            return self._compress_lz4_legacy(
                data
            )

        if compression is CompressionFormat.ZSTD:
            return (
                zstandard
                .ZstdCompressor()
                .compress(
                    data
                )
            )

        if compression is CompressionFormat.LZMA:
            return lzma.compress(
                data,
                format=lzma.FORMAT_ALONE,
            )

        raise AndroidBootImageRamdiskPackagingError(
            "unsupported ramdisk compression format: "
            f"{compression.value}"
        )


class AndroidBootImageRamdiskPackager:
    """
    Produce one replacement ramdisk artifact from canonical CPIO records.
    """

    def __init__(
        self,
        *,
        writer: AndroidBootImageNewcWriter | None = None,
        compressor: AndroidBootImageRamdiskCompressor | None = None,
    ) -> None:
        self.writer = (
            writer
            if writer is not None
            else AndroidBootImageNewcWriter()
        )

        self.compressor = (
            compressor
            if compressor is not None
            else AndroidBootImageRamdiskCompressor()
        )

    @staticmethod
    def _write_exact(
        path: Path,
        data: bytes,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.unlink(
            missing_ok=True
        )

        try:
            path.write_bytes(
                data
            )
        except BaseException:
            path.unlink(
                missing_ok=True
            )
            raise

        if (
            path.stat().st_size
            != len(
                data
            )
        ):
            path.unlink(
                missing_ok=True
            )

            raise AndroidBootImageRamdiskPackagingError(
                f"written artifact size mismatch: {path}"
            )

    def package(
        self,
        entries: tuple[
            CpioNewcEntry,
            ...,
        ],
        *,
        compression: CompressionFormat,
        cpio_path: Path,
        ramdisk_path: Path,
    ) -> AndroidBootImageRamdiskPackageResult:
        if not isinstance(
            entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not entries:
            raise AndroidBootImageRamdiskPackagingError(
                "ramdisk CPIO population cannot be empty"
            )

        if not isinstance(
            cpio_path,
            Path,
        ):
            raise TypeError(
                "cpio_path must be a Path"
            )

        if not isinstance(
            ramdisk_path,
            Path,
        ):
            raise TypeError(
                "ramdisk_path must be a Path"
            )

        cpio_data = self.writer.serialize(
            entries
        )

        #
        # Validate the generated archive using TreeForge's own canonical
        # decoder before compression.
        #
        decoded = (
            CpioNewcDecoder()
            .decode(
                cpio_data
            )
        )

        if len(
            decoded
        ) != len(
            entries
        ):
            raise AndroidBootImageRamdiskPackagingError(
                "generated CPIO did not decode to the exact selected "
                "population size"
            )

        for expected, actual in zip(
            entries,
            decoded,
            strict=True,
        ):
            if actual != expected:
                raise AndroidBootImageRamdiskPackagingError(
                    "generated CPIO round-trip changed canonical entry: "
                    f"{expected.path!r}"
                )

        ramdisk_data = self.compressor.compress(
            cpio_data,
            compression,
        )

        self._write_exact(
            cpio_path,
            cpio_data,
        )

        self._write_exact(
            ramdisk_path,
            ramdisk_data,
        )

        return AndroidBootImageRamdiskPackageResult(
            entries=entries,
            compression=compression,
            cpio_path=cpio_path,
            ramdisk_path=ramdisk_path,
            cpio_size_bytes=len(
                cpio_data
            ),
            ramdisk_size_bytes=len(
                ramdisk_data
            ),
            cpio_sha256=sha256(
                cpio_data
            ).hexdigest(),
            ramdisk_sha256=sha256(
                ramdisk_data
            ).hexdigest(),
        )


__all__ = (
    "AndroidBootImageNewcWriter",
    "AndroidBootImageRamdiskCompressor",
    "AndroidBootImageRamdiskPackageResult",
    "AndroidBootImageRamdiskPackager",
    "AndroidBootImageRamdiskPackagingError",
)
