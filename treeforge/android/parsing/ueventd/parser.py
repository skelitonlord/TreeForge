from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.parsing.ueventd.model import (
    AndroidUeventdDeclaration,
    AndroidUeventdDeviceRule,
    AndroidUeventdFirmwareDirectories,
    AndroidUeventdImport,
    AndroidUeventdSocketRcvbufSize,
    AndroidUeventdSubsystem,
    AndroidUeventdSubsystemOption,
    AndroidUeventdSysfsRule,
    AndroidUeventdUnparsedLine,
    ParsedAndroidUeventdFile,
)


@dataclass(
    slots=True,
)
class _SubsystemBuilder:
    name: str
    source_path: Path
    source_line: int

    options: list[
        AndroidUeventdSubsystemOption
    ]

    def build(
        self,
    ) -> AndroidUeventdSubsystem:
        return AndroidUeventdSubsystem(
            name=self.name,
            options=tuple(
                self.options
            ),
            source_path=self.source_path,
            source_line=self.source_line,
        )


class UeventdParser:
    """
    Parse one Android ueventd source without resolving imports or deriving
    runtime semantics.
    """

    def parse(
        self,
        path: Path,
    ) -> ParsedAndroidUeventdFile:
        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"Ueventd source is not a file: {path}"
            )

        raw = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        declarations: list[
            AndroidUeventdDeclaration
        ] = []

        unparsed_lines: list[
            AndroidUeventdUnparsedLine
        ] = []

        subsystem: _SubsystemBuilder | None = None

        for line_number, raw_line in enumerate(
            raw.splitlines(),
            start=1,
        ):
            line = self._normalize_line(
                raw_line
            )

            if not line:
                continue

            is_indented = (
                raw_line[:1].isspace()
            )

            if (
                subsystem is not None
                and is_indented
            ):
                option = self._parse_subsystem_option(
                    line,
                    path=path,
                    line_number=line_number,
                )

                if option is not None:
                    subsystem.options.append(
                        option
                    )
                else:
                    unparsed_lines.append(
                        AndroidUeventdUnparsedLine(
                            raw=raw_line,
                            source_path=path,
                            source_line=line_number,
                        )
                    )

                continue

            if subsystem is not None:
                declarations.append(
                    subsystem.build()
                )
                subsystem = None

            parts = line.split()

            if not parts:
                continue

            keyword = parts[0]

            declaration: (
                AndroidUeventdDeclaration
                | None
            ) = None

            if keyword == "import":
                declaration = self._parse_import(
                    parts,
                    path=path,
                    line_number=line_number,
                )

            elif keyword == "firmware_directories":
                declaration = (
                    self._parse_firmware_directories(
                        parts,
                        path=path,
                        line_number=line_number,
                    )
                )

            elif keyword == "uevent_socket_rcvbuf_size":
                declaration = (
                    self._parse_socket_rcvbuf_size(
                        parts,
                        path=path,
                        line_number=line_number,
                    )
                )

            elif keyword == "subsystem":
                subsystem = self._parse_subsystem(
                    parts,
                    path=path,
                    line_number=line_number,
                )

                if subsystem is not None:
                    continue

            elif keyword.startswith(
                "/dev"
            ):
                declaration = self._parse_device_rule(
                    parts,
                    path=path,
                    line_number=line_number,
                )

            elif keyword.startswith(
                "/sys"
            ):
                declaration = self._parse_sysfs_rule(
                    parts,
                    path=path,
                    line_number=line_number,
                )

            if declaration is not None:
                declarations.append(
                    declaration
                )
                continue

            unparsed_lines.append(
                AndroidUeventdUnparsedLine(
                    raw=raw_line,
                    source_path=path,
                    source_line=line_number,
                )
            )

        if subsystem is not None:
            declarations.append(
                subsystem.build()
            )

        return ParsedAndroidUeventdFile(
            source_path=path,
            raw=raw,
            declarations=tuple(
                declarations
            ),
            unparsed_lines=tuple(
                unparsed_lines
            ),
        )

    @staticmethod
    def _normalize_line(
        raw_line: str,
    ) -> str:
        content, _, _ = raw_line.partition(
            "#"
        )

        return content.strip()

    @staticmethod
    def _parse_import(
        parts: list[str],
        *,
        path: Path,
        line_number: int,
    ) -> AndroidUeventdImport | None:
        if len(parts) != 2:
            return None

        return AndroidUeventdImport(
            path=parts[1],
            source_path=path,
            source_line=line_number,
        )

    @staticmethod
    def _parse_firmware_directories(
        parts: list[str],
        *,
        path: Path,
        line_number: int,
    ) -> AndroidUeventdFirmwareDirectories | None:
        if len(parts) < 2:
            return None

        return AndroidUeventdFirmwareDirectories(
            directories=tuple(
                parts[1:]
            ),
            source_path=path,
            source_line=line_number,
        )

    @staticmethod
    def _parse_socket_rcvbuf_size(
        parts: list[str],
        *,
        path: Path,
        line_number: int,
    ) -> AndroidUeventdSocketRcvbufSize | None:
        if len(parts) != 2:
            return None

        return AndroidUeventdSocketRcvbufSize(
            size=parts[1],
            source_path=path,
            source_line=line_number,
        )

    @staticmethod
    def _parse_subsystem(
        parts: list[str],
        *,
        path: Path,
        line_number: int,
    ) -> _SubsystemBuilder | None:
        if len(parts) != 2:
            return None

        return _SubsystemBuilder(
            name=parts[1],
            source_path=path,
            source_line=line_number,
            options=[],
        )

    @staticmethod
    def _parse_subsystem_option(
        line: str,
        *,
        path: Path,
        line_number: int,
    ) -> AndroidUeventdSubsystemOption | None:
        parts = line.split()

        if len(parts) != 2:
            return None

        return AndroidUeventdSubsystemOption(
            name=parts[0],
            value=parts[1],
            source_path=path,
            source_line=line_number,
        )

    @staticmethod
    def _parse_device_rule(
        parts: list[str],
        *,
        path: Path,
        line_number: int,
    ) -> AndroidUeventdDeviceRule | None:
        if len(parts) != 4:
            return None

        return AndroidUeventdDeviceRule(
            path=parts[0],
            mode=parts[1],
            user=parts[2],
            group=parts[3],
            source_path=path,
            source_line=line_number,
        )

    @staticmethod
    def _parse_sysfs_rule(
        parts: list[str],
        *,
        path: Path,
        line_number: int,
    ) -> AndroidUeventdSysfsRule | None:
        if len(parts) != 5:
            return None

        return AndroidUeventdSysfsRule(
            path=parts[0],
            attribute=parts[1],
            mode=parts[2],
            user=parts[3],
            group=parts[4],
            source_path=path,
            source_line=line_number,
        )


def read_android_ueventd(
    path: Path,
) -> ParsedAndroidUeventdFile:
    """
    Read and parse one Android ueventd source.
    """

    return UeventdParser().parse(
        path
    )