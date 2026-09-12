from __future__ import annotations

import re
import stat
from dataclasses import dataclass
from datetime import datetime

from treeforge.android.filesystem.debugfs.stat import (
    DebugfsInodeType,
)


class DebugfsDirectoryParseError(ValueError):
    """
    Raised when debugfs directory-listing output cannot be parsed.
    """

    def __init__(
        self,
        message: str,
        *,
        line_number: int | None = None,
        line: str | None = None,
    ) -> None:
        self.line_number = line_number
        self.line = line

        details = message

        if line_number is not None:
            details = f"{details} at line {line_number}"

        if line is not None:
            details = f"{details}: {line!r}"

        super().__init__(
            details,
        )


@dataclass(
    frozen=True,
)
class DebugfsDirectoryEntry:
    """
    One entry returned by ``debugfs ls -l``.
    """

    inode: int
    mode: int
    inode_type: DebugfsInodeType
    type_code: int | None
    user_id: int
    group_id: int
    size: int
    modification_time: datetime
    name: str

    @property
    def is_dot_entry(
        self,
    ) -> bool:
        """
        Return whether this is ``.`` or ``..``.
        """

        return self.name in {
            ".",
            "..",
        }

    @property
    def is_directory(
        self,
    ) -> bool:
        """
        Return whether this entry represents a directory.
        """

        return (
            self.inode_type
            is DebugfsInodeType.DIRECTORY
        )

    @property
    def is_regular_file(
        self,
    ) -> bool:
        """
        Return whether this entry represents a regular file.
        """

        return (
            self.inode_type
            is DebugfsInodeType.REGULAR_FILE
        )

    @property
    def is_symlink(
        self,
    ) -> bool:
        """
        Return whether this entry represents a symbolic link.
        """

        return (
            self.inode_type
            is DebugfsInodeType.SYMLINK
        )


class DebugfsDirectoryParser:
    """
    Parse output produced by ``debugfs ls -l``.

    Typical output resembles::

        2  40755 (2)  0  0  4096  1-Jan-2024 00:00 .
        12 100644 (1) 1000 1000 42 2-Jan-2024 14:30 build.prop
    """

    _ENTRY_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<inode>\d+)
        \s+
        (?P<mode>[0-7]+)
        (?:\s+\((?P<type_code>\d+)\))?
        \s+
        (?P<uid>\d+)
        \s+
        (?P<gid>\d+)
        \s+
        (?P<size>\d+)
        \s+
        (?P<date>\d{1,2}-[A-Za-z]{3}-\d{4})
        \s+
        (?P<time>\d{1,2}:\d{2})
        \s+
        (?P<name>.+?)
        \s*$
        """,
        re.VERBOSE,
    )

    _UNUSED_ENTRY_PATTERN = re.compile(
        r"""
        ^\s*
        0
        \s+
        0
        \s+
        \(0\)
        \s+
        0
        \s+
        0
        \s+
        0
        \s*$
        """,
        re.VERBOSE,
    )

    _TIMESTAMP_FORMATS = (
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y %H:%M:%S",
    )

    @classmethod
    def parse(
        cls,
        output: str,
    ) -> tuple[
        DebugfsDirectoryEntry,
        ...,
    ]:
        """
        Parse a complete directory listing.

        Blank lines, debugfs banners, prompts, and unused zero-inode
        directory slots are ignored. Other malformed non-empty lines remain
        parsing errors.
        """

        if not isinstance(
            output,
            str,
        ):
            raise TypeError(
                "debugfs directory output must be a string"
            )

        entries: list[
            DebugfsDirectoryEntry
        ] = []

        for line_number, line in enumerate(
            output.splitlines(),
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            if cls._is_ignorable_line(
                stripped,
            ):
                continue

            if cls._is_unused_entry_line(
                line,
            ):
                continue

            entries.append(
                cls.parse_line(
                    line,
                    line_number=line_number,
                )
            )

        return tuple(
            entries,
        )

    @classmethod
    def parse_line(
        cls,
        line: str,
        *,
        line_number: int | None = None,
    ) -> DebugfsDirectoryEntry:
        """
        Parse one ``debugfs ls -l`` entry.

        This method remains strict. Unused directory slots are filtered only
        by ``parse()`` while processing a complete listing.
        """

        if not isinstance(
            line,
            str,
        ):
            raise TypeError(
                "debugfs directory line must be a string"
            )

        if not line.strip():
            raise DebugfsDirectoryParseError(
                "debugfs directory line cannot be empty",
                line_number=line_number,
                line=line,
            )

        match = cls._ENTRY_PATTERN.match(
            line,
        )

        if match is None:
            raise DebugfsDirectoryParseError(
                "unable to parse debugfs directory entry",
                line_number=line_number,
                line=line,
            )

        mode = cls._parse_mode(
            match.group(
                "mode",
            ),
            line_number=line_number,
            line=line,
        )

        timestamp = cls._parse_timestamp(
            date_text=match.group(
                "date",
            ),
            time_text=match.group(
                "time",
            ),
            line_number=line_number,
            line=line,
        )

        name = match.group(
            "name",
        )

        if not name:
            raise DebugfsDirectoryParseError(
                "debugfs directory entry name cannot be empty",
                line_number=line_number,
                line=line,
            )

        type_code_text = match.group(
            "type_code",
        )

        return DebugfsDirectoryEntry(
            inode=int(
                match.group(
                    "inode",
                ),
                10,
            ),
            mode=mode,
            inode_type=cls._inode_type_from_mode(
                mode,
            ),
            type_code=(
                int(
                    type_code_text,
                    10,
                )
                if type_code_text is not None
                else None
            ),
            user_id=int(
                match.group(
                    "uid",
                ),
                10,
            ),
            group_id=int(
                match.group(
                    "gid",
                ),
                10,
            ),
            size=int(
                match.group(
                    "size",
                ),
                10,
            ),
            modification_time=timestamp,
            name=name,
        )

    @staticmethod
    def _is_ignorable_line(
        line: str,
    ) -> bool:
        """
        Ignore debugfs banners and prompts accidentally included in output.
        """

        normalized = line.lower()

        return (
            normalized.startswith(
                "debugfs ",
            )
            or normalized == "debugfs:"
            or normalized.startswith(
                "debugfs:",
            )
        )

    @classmethod
    def _is_unused_entry_line(
        cls,
        line: str,
    ) -> bool:
        """
        Return whether a line is an unused debugfs directory slot.

        Real ext4 images may cause ``debugfs ls -l`` to emit a zero-inode
        record with no timestamp or filename. It is not a filesystem entry
        and should not abort traversal.
        """

        return (
            cls._UNUSED_ENTRY_PATTERN.match(
                line,
            )
            is not None
        )

    @staticmethod
    def _parse_mode(
        value: str,
        *,
        line_number: int | None,
        line: str,
    ) -> int:
        try:
            return int(
                value,
                8,
            )
        except ValueError as error:
            raise DebugfsDirectoryParseError(
                "invalid octal mode",
                line_number=line_number,
                line=line,
            ) from error

    @classmethod
    def _parse_timestamp(
        cls,
        *,
        date_text: str,
        time_text: str,
        line_number: int | None,
        line: str,
    ) -> datetime:
        value = (
            f"{date_text} "
            f"{time_text}"
        )

        for timestamp_format in cls._TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(
                    value,
                    timestamp_format,
                )
            except ValueError:
                continue

        raise DebugfsDirectoryParseError(
            (
                "unsupported debugfs directory "
                f"timestamp {value!r}"
            ),
            line_number=line_number,
            line=line,
        )

    @staticmethod
    def _inode_type_from_mode(
        mode: int,
    ) -> DebugfsInodeType:
        if stat.S_ISREG(
            mode,
        ):
            return DebugfsInodeType.REGULAR_FILE

        if stat.S_ISDIR(
            mode,
        ):
            return DebugfsInodeType.DIRECTORY

        if stat.S_ISLNK(
            mode,
        ):
            return DebugfsInodeType.SYMLINK

        if stat.S_ISCHR(
            mode,
        ):
            return DebugfsInodeType.CHARACTER_DEVICE

        if stat.S_ISBLK(
            mode,
        ):
            return DebugfsInodeType.BLOCK_DEVICE

        if stat.S_ISFIFO(
            mode,
        ):
            return DebugfsInodeType.FIFO

        if stat.S_ISSOCK(
            mode,
        ):
            return DebugfsInodeType.SOCKET

        return DebugfsInodeType.UNKNOWN