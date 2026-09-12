from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DebugfsStatParseError(ValueError):
    """
    Raised when required information cannot be parsed from debugfs stat output.
    """


class DebugfsInodeType(StrEnum):
    REGULAR_FILE = "regular_file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    CHARACTER_DEVICE = "character_device"
    BLOCK_DEVICE = "block_device"
    FIFO = "fifo"
    SOCKET = "socket"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DebugfsStat:
    """
    Structured representation of one debugfs stat response.
    """

    inode: int
    inode_type: DebugfsInodeType
    mode: int
    flags: int | None
    generation: int | None
    version: int | None
    user_id: int
    group_id: int
    size: int
    links: int
    block_count: int | None
    access_time: datetime | None
    change_time: datetime | None
    modification_time: datetime | None
    creation_time: datetime | None
    extra_isize: int | None
    checksum: str | None
    symlink_target: str | None


class DebugfsStatParser:
    """
    Parse output produced by the debugfs ``stat`` command.
    """

    _HEADER_PATTERN = re.compile(
        r"""
        Inode:\s*(?P<inode>\d+)
        \s+Type:\s*(?P<inode_type>.+?)
        \s+Mode:\s*(?P<mode>[0-7]+)
        (?:\s+Flags:\s*(?P<flags>0x[0-9a-fA-F]+|\d+))?
        \s*$
        """,
        re.VERBOSE,
    )

    _OWNER_PATTERN = re.compile(
        r"""
        User:\s*(?P<uid>\d+)
        \s+Group:\s*(?P<gid>\d+)
        \s+Project:\s*(?P<project>\d+)
        \s+Size:\s*(?P<size>\d+)
        """,
        re.VERBOSE,
    )

    _OWNER_WITHOUT_PROJECT_PATTERN = re.compile(
        r"""
        User:\s*(?P<uid>\d+)
        \s+Group:\s*(?P<gid>\d+)
        \s+Size:\s*(?P<size>\d+)
        """,
        re.VERBOSE,
    )

    _GENERATION_PATTERN = re.compile(
        r"Generation:\s*(?P<generation>\d+)"
    )

    _VERSION_PATTERN = re.compile(
        r"""
        Version:\s*
        (?P<version>
            0x[0-9a-fA-F]+:[0-9a-fA-F]+
            |
            0x[0-9a-fA-F]+
            |
            \d+
        )
        """,
        re.VERBOSE,
    )

    _LINK_PATTERN = re.compile(
        r"""
        Links:\s*(?P<links>\d+)
        \s+Blockcount:\s*(?P<block_count>\d+)
        """,
        re.VERBOSE,
    )

    _LINKS_ONLY_PATTERN = re.compile(
        r"""
        Links:\s*(?P<links>\d+)
        """,
        re.VERBOSE,
    )

    _EXTRA_ISIZE_PATTERN = re.compile(
        r"Size of extra inode fields:\s*(?P<extra_isize>\d+)"
    )

    _CHECKSUM_PATTERN = re.compile(
        r"Checksum:\s*(?P<checksum>0x[0-9a-fA-F]+|[0-9a-fA-F]+)"
    )

    _FAST_LINK_DEST_PATTERN = re.compile(
        r"Fast\s+link\s+dest:\s*\"(?P<target>.*)\"\s*$"
    )

    _TIMESTAMP_PATTERN = re.compile(
        r"""
        ^(?P<label>atime|ctime|mtime|crtime):
        \s*
        (?:
            0x[0-9a-fA-F]+:[0-9a-fA-F]+
            \s+--
            \s+
        )?
        (?P<timestamp>.+?)
        \s*$
        """,
        re.VERBOSE,
    )

    _TYPE_MAP = {
        "regular": DebugfsInodeType.REGULAR_FILE,
        "regular file": DebugfsInodeType.REGULAR_FILE,
        "directory": DebugfsInodeType.DIRECTORY,
        "symlink": DebugfsInodeType.SYMLINK,
        "symbolic link": DebugfsInodeType.SYMLINK,
        "character special": DebugfsInodeType.CHARACTER_DEVICE,
        "character device": DebugfsInodeType.CHARACTER_DEVICE,
        "block special": DebugfsInodeType.BLOCK_DEVICE,
        "block device": DebugfsInodeType.BLOCK_DEVICE,
        "fifo": DebugfsInodeType.FIFO,
        "socket": DebugfsInodeType.SOCKET,
    }

    _TIME_FORMATS = (
        "%a %b %d %H:%M:%S %Y",
        "%a %b %d %H:%M:%S.%f %Y",
    )

    @classmethod
    def parse(
        cls,
        output: str,
    ) -> DebugfsStat:
        if not isinstance(output, str):
            raise TypeError(
                "debugfs stat output must be a string"
            )

        if not output.strip():
            raise DebugfsStatParseError(
                "debugfs stat output cannot be empty"
            )

        lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        header = cls._find_match(
            lines,
            cls._HEADER_PATTERN,
            "inode header",
        )

        generation_match = cls._find_optional_match(
            lines,
            cls._GENERATION_PATTERN,
        )

        version_match = cls._find_optional_match(
            lines,
            cls._VERSION_PATTERN,
        )

        owner = cls._find_optional_match(
            lines,
            cls._OWNER_PATTERN,
        )

        if owner is None:
            owner = cls._find_match(
                lines,
                cls._OWNER_WITHOUT_PROJECT_PATTERN,
                "owner and size",
            )

        link_data = cls._find_optional_match(
            lines,
            cls._LINK_PATTERN,
        )

        if link_data is None:
            links_only = cls._find_match(
                lines,
                cls._LINKS_ONLY_PATTERN,
                "link count",
            )
            links = cls._parse_decimal(
                links_only.group("links"),
            )
            block_count = None
        else:
            links = cls._parse_decimal(
                link_data.group("links"),
            )
            block_count = cls._parse_decimal(
                link_data.group("block_count"),
            )

        timestamps = cls._parse_timestamps(
            lines,
        )

        extra_isize_match = cls._find_optional_match(
            lines,
            cls._EXTRA_ISIZE_PATTERN,
        )
        checksum_match = cls._find_optional_match(
            lines,
            cls._CHECKSUM_PATTERN,
        )

        symlink_target_match = (
            cls._find_optional_match(
                lines,
                cls._FAST_LINK_DEST_PATTERN,
            )
        )

        return DebugfsStat(
            inode=cls._parse_decimal(
                header.group("inode"),
            ),
            inode_type=cls._parse_inode_type(
                header.group("inode_type"),
            ),
            mode=cls._parse_octal(
                header.group("mode"),
            ),
            flags=cls._parse_optional_integer(
                header.group("flags"),
            ),
            generation=(
                cls._parse_decimal(
                    generation_match.group("generation"),
                )
                if generation_match is not None
                else None
            ),
            version=(
                cls._parse_optional_version(
                    version_match.group("version"),
                )
                if version_match is not None
                else None
            ),
            user_id=cls._parse_decimal(
                owner.group("uid"),
            ),
            group_id=cls._parse_decimal(
                owner.group("gid"),
            ),
            size=cls._parse_decimal(
                owner.group("size"),
            ),
            links=links,
            block_count=block_count,
            access_time=timestamps.get("atime"),
            change_time=timestamps.get("ctime"),
            modification_time=timestamps.get("mtime"),
            creation_time=timestamps.get("crtime"),
            extra_isize=(
                cls._parse_decimal(
                    extra_isize_match.group("extra_isize"),
                )
                if extra_isize_match is not None
                else None
            ),
            checksum=(
                checksum_match.group("checksum")
                if checksum_match is not None
                else None
            ),
            symlink_target=(
                symlink_target_match.group(
                    "target"
                )
                if symlink_target_match is not None
                else None
            ),
        )

    @classmethod
    def _parse_inode_type(
        cls,
        value: str,
    ) -> DebugfsInodeType:
        normalized = " ".join(
            value.strip().lower().split()
        )

        return cls._TYPE_MAP.get(
            normalized,
            DebugfsInodeType.UNKNOWN,
        )

    @classmethod
    def _parse_timestamps(
        cls,
        lines: list[str],
    ) -> dict[str, datetime | None]:
        timestamps: dict[str, datetime | None] = {
            "atime": None,
            "ctime": None,
            "mtime": None,
            "crtime": None,
        }

        for line in lines:
            match = cls._TIMESTAMP_PATTERN.match(
                line,
            )

            if match is None:
                continue

            timestamps[match.group("label")] = (
                cls._parse_timestamp(
                    match.group("timestamp"),
                )
            )

        return timestamps

    @classmethod
    def _parse_timestamp(
        cls,
        value: str,
    ) -> datetime:
        normalized = " ".join(
            value.strip().split()
        )

        for time_format in cls._TIME_FORMATS:
            try:
                return datetime.strptime(
                    normalized,
                    time_format,
                )
            except ValueError:
                continue

        raise DebugfsStatParseError(
            f"Unsupported debugfs timestamp: {value}"
        )

    @staticmethod
    def _parse_decimal(
        value: str,
    ) -> int:
        return int(
            value,
            10,
        )

    @staticmethod
    def _parse_octal(
        value: str,
    ) -> int:
        return int(
            value,
            8,
        )

    @staticmethod
    def _parse_optional_integer(
        value: str | None,
    ) -> int | None:
        if value is None:
            return None

        return int(
            value,
            0,
        )

    @staticmethod
    def _find_match(
        lines: list[str],
        pattern: re.Pattern[str],
        description: str,
    ) -> re.Match[str]:
        match = DebugfsStatParser._find_optional_match(
            lines,
            pattern,
        )

        if match is None:
            raise DebugfsStatParseError(
                f"Unable to parse debugfs {description}"
            )

        return match

    @staticmethod
    def _find_optional_match(
        lines: list[str],
        pattern: re.Pattern[str],
    ) -> re.Match[str] | None:
        for line in lines:
            match = pattern.search(
                line,
            )

            if match is not None:
                return match

        return None

    @staticmethod
    def _parse_optional_version(
        value: str | None,
    ) -> int | None:
        if value is None:
            return None

        if ":" not in value:
            return int(
                value,
                0,
            )

        high_text, low_text = value.split(
            ":",
            maxsplit=1,
        )

        high = int(
            high_text,
            0,
        )
        low = int(
            low_text,
            16,
        )

        return (high << 32) | low