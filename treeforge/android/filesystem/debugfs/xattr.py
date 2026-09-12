from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Protocol


class DebugfsXattrError(RuntimeError):
    """
    Base error for debugfs extended-attribute operations.
    """


class DebugfsXattrParseError(DebugfsXattrError, ValueError):
    """
    Raised when extended-attribute output cannot be parsed.
    """


class DebugfsXattrRunner(Protocol):
    """
    Minimum runner interface required by DebugfsXattrCollector.
    """

    def list_xattrs(
        self,
        path: str,
    ) -> str:
        """
        Return raw output from ``debugfs ea_list``.
        """

    def get_xattr(
        self,
        path: str,
        name: str,
    ) -> str:
        """
        Return hexadecimal output from ``debugfs ea_get -x``.
        """


@dataclass(frozen=True)
class DebugfsXattrListing:
    """
    One extended attribute discovered by ``ea_list``.
    """

    name: str
    declared_size: int | None
    displayed_value: str | None


@dataclass(frozen=True)
class DebugfsXattrs:
    """
    Immutable extended attributes collected for one filesystem path.
    """

    path: PurePosixPath
    values: Mapping[str, bytes]

    def __post_init__(self) -> None:
        normalized = {
            name: bytes(value)
            for name, value in self.values.items()
        }

        object.__setattr__(
            self,
            "values",
            MappingProxyType(normalized),
        )

    def get(
        self,
        name: str,
    ) -> bytes | None:
        return self.values.get(name)

    @property
    def selinux_context(self) -> str | None:
        """
        Return the decoded Android SELinux context when present.
        """

        value = self.get("security.selinux")

        if value is None:
            return None

        return value.rstrip(b"\x00").decode(
            "utf-8",
            errors="strict",
        )

    @property
    def capabilities(self) -> bytes | None:
        """
        Return the raw Linux capability xattr.
        """

        return self.get("security.capability")


class DebugfsXattrListParser:
    """
    Parse output produced by ``debugfs ea_list``.

    Accepted forms include:

        security.selinux (27) = "u:object_r:system_file:s0"
        security.capability (20) = 0x01000002...
        user.comment = "example"
        trusted.overlay.opaque
    """

    _ENTRY_PATTERN = re.compile(
        r"""
        ^\s*
        (?P<name>
            (?:user|trusted|security|system)\.
            [^\s=(]+
        )
        (?:\s+\((?P<size>\d+)\))?
        (?:\s*=\s*(?P<value>.*?))?
        \s*$
        """,
        re.VERBOSE,
    )

    @classmethod
    def parse(
        cls,
        output: str,
    ) -> tuple[DebugfsXattrListing, ...]:
        if not isinstance(output, str):
            raise TypeError(
                "debugfs xattr listing output must be a string"
            )

        listings: list[DebugfsXattrListing] = []

        for line_number, line in enumerate(
            output.splitlines(),
            start=1,
        ):
            stripped = line.strip()

            if not stripped:
                continue

            if cls._is_ignorable_line(stripped):
                continue

            match = cls._ENTRY_PATTERN.match(line)

            if match is None:
                raise DebugfsXattrParseError(
                    "Unable to parse debugfs xattr listing "
                    f"at line {line_number}: {line!r}"
                )

            value = match.group("value")

            listings.append(
                DebugfsXattrListing(
                    name=match.group("name"),
                    declared_size=(
                        int(match.group("size"), 10)
                        if match.group("size") is not None
                        else None
                    ),
                    displayed_value=(
                        value.strip()
                        if value is not None
                        else None
                    ),
                )
            )

        return tuple(listings)

    @staticmethod
    def _is_ignorable_line(
        line: str,
    ) -> bool:
        normalized = line.lower().rstrip(":")

        return (
            normalized.startswith("debugfs ")
            or normalized == "debugfs"
            or normalized == "extended attributes"
            or normalized == "no extended attributes"
        )


class DebugfsXattrValueParser:
    """
    Parse hexadecimal output produced by ``debugfs ea_get -x``.
    """

    _HEX_VALUE_PATTERN = re.compile(
        r"""
        (?:
            ^|
            =
        )
        \s*
        (?P<hex>
            (?:
                0[xX][0-9A-Fa-f\s]*
                |
                (?:[0-9A-Fa-f]{2}(?:\s+[0-9A-Fa-f]{2})*)
            )
        )
        \s*$
        """,
        re.VERBOSE,
    )

    @classmethod
    def parse(
        cls,
        output: str,
    ) -> bytes:
        if not isinstance(output, str):
            raise TypeError(
                "debugfs xattr value output must be a string"
            )

        stripped = output.strip()

        if not stripped:
            return b""

        match = cls._HEX_VALUE_PATTERN.search(stripped)

        if match is None:
            raise DebugfsXattrParseError(
                "Unable to parse hexadecimal debugfs xattr value"
            )

        hexadecimal = match.group("hex")

        if hexadecimal.lower().startswith("0x"):
            hexadecimal = hexadecimal[2:]

        hexadecimal = re.sub(
            r"\s+",
            "",
            hexadecimal,
        )

        if len(hexadecimal) % 2 != 0:
            raise DebugfsXattrParseError(
                "Hexadecimal xattr value must contain complete bytes"
            )

        try:
            return bytes.fromhex(hexadecimal)
        except ValueError as error:
            raise DebugfsXattrParseError(
                "Invalid hexadecimal xattr value"
            ) from error


class DebugfsXattrCollector:
    """
    Collect all extended attributes associated with a filesystem path.
    """

    def __init__(
        self,
        runner: DebugfsXattrRunner,
    ) -> None:
        self._runner = runner

    def collect(
        self,
        path: str | PurePosixPath,
    ) -> DebugfsXattrs:
        normalized_path = self._normalize_path(path)

        try:
            listing_output = self._runner.list_xattrs(
                str(normalized_path)
            )
        except Exception as error:
            raise DebugfsXattrError(
                f"Unable to list xattrs for {normalized_path}"
            ) from error

        listings = DebugfsXattrListParser.parse(
            listing_output
        )

        values: dict[str, bytes] = {}

        for listing in listings:
            try:
                value_output = self._runner.get_xattr(
                    str(normalized_path),
                    listing.name,
                )
            except Exception as error:
                raise DebugfsXattrError(
                    "Unable to read xattr "
                    f"{listing.name!r} for {normalized_path}"
                ) from error

            value = DebugfsXattrValueParser.parse(
                value_output
            )

            if (
                listing.declared_size is not None
                and len(value) != listing.declared_size
            ):
                raise DebugfsXattrParseError(
                    f"Xattr {listing.name!r} declares "
                    f"{listing.declared_size} bytes but returned "
                    f"{len(value)} bytes"
                )

            values[listing.name] = value

        return DebugfsXattrs(
            path=normalized_path,
            values=values,
        )

    @staticmethod
    def _normalize_path(
        path: str | PurePosixPath,
    ) -> PurePosixPath:
        if not isinstance(
            path,
            (str, PurePosixPath),
        ):
            raise TypeError(
                "xattr path must be a string or PurePosixPath"
            )

        if isinstance(path, str):
            if not path.strip():
                raise ValueError(
                    "xattr path cannot be empty"
                )

            normalized = PurePosixPath(
                path.strip()
            )
        else:
            normalized = path

        if not normalized.is_absolute():
            raise ValueError(
                "xattr path must be absolute"
            )

        if ".." in normalized.parts:
            raise ValueError(
                "xattr path cannot contain parent traversal"
            )

        return normalized