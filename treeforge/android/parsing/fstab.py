from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFstabDeclaration:
    """
    One lexically parsed Android fstab declaration.

    Parsing preserves source ordering, exact source-line provenance,
    mount-option ordering, and fs_mgr-flag ordering without interpreting
    their Android semantics.
    """

    device: str
    mount_point: str
    fs_type: str

    mount_options: tuple[
        str,
        ...,
    ] = ()

    fs_mgr_flags: tuple[
        str,
        ...,
    ] = ()

    line_number: int = 1
    raw: str = ""

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            (
                "device",
                self.device,
            ),
            (
                "mount_point",
                self.mount_point,
            ),
            (
                "fs_type",
                self.fs_type,
            ),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.mount_options,
            tuple,
        ):
            raise TypeError(
                "mount_options must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.mount_options
        ):
            raise TypeError(
                "mount_options must contain only strings"
            )

        if not isinstance(
            self.fs_mgr_flags,
            tuple,
        ):
            raise TypeError(
                "fs_mgr_flags must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.fs_mgr_flags
        ):
            raise TypeError(
                "fs_mgr_flags must contain only strings"
            )

        if (
            isinstance(
                self.line_number,
                bool,
            )
            or not isinstance(
                self.line_number,
                int,
            )
        ):
            raise TypeError(
                "line_number must be an integer"
            )

        if self.line_number < 1:
            raise ValueError(
                "line_number must be positive"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFstabUnparsedLine:
    """
    Preserve one meaningful fstab line that could not be represented.
    """

    line_number: int
    raw: str
    reason: str

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.line_number,
                bool,
            )
            or not isinstance(
                self.line_number,
                int,
            )
        ):
            raise TypeError(
                "line_number must be an integer"
            )

        if self.line_number < 1:
            raise ValueError(
                "line_number must be positive"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.reason,
            str,
        ):
            raise TypeError(
                "reason must be a string"
            )

        if not self.reason:
            raise ValueError(
                "reason must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidFstab:
    """
    Immutable lexical interpretation of one Android fstab source.

    Blank lines and comments are valid non-semantic syntax and are omitted.
    Unsupported meaningful lines remain available as unparsed evidence.
    """

    declarations: tuple[
        AndroidFstabDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        AndroidFstabUnparsedLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
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
    def declaration_count(
        self,
    ) -> int:
        return len(
            self.declarations
        )

    @property
    def unparsed_line_count(
        self,
    ) -> int:
        return len(
            self.unparsed_lines
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return not self.declarations


def parse_android_fstab(
    text: str,
) -> ParsedAndroidFstab:
    """
    Lexically parse one Android fstab source.
    """

    if not isinstance(
        text,
        str,
    ):
        raise TypeError(
            "text must be a string"
        )

    return parse_android_fstab_lines(
        text.splitlines()
    )


def parse_android_fstab_lines(
    lines: Iterable[str],
) -> ParsedAndroidFstab:
    """
    Parse Android fstab declarations without semantic interpretation.

    Supported lexical form:

        device mount_point fs_type mount_options [fs_mgr_flags]
    """

    declarations: list[
        AndroidFstabDeclaration
    ] = []

    unparsed_lines: list[
        AndroidFstabUnparsedLine
    ] = []

    for line_number, raw_line in enumerate(
        lines,
        start=1,
    ):
        if not isinstance(
            raw_line,
            str,
        ):
            raise TypeError(
                "fstab lines must be strings"
            )

        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        parts = line.split()

        if len(parts) < 4:
            unparsed_lines.append(
                AndroidFstabUnparsedLine(
                    line_number=line_number,
                    raw=raw_line,
                    reason="too_few_fields",
                )
            )
            continue

        if len(parts) > 5:
            unparsed_lines.append(
                AndroidFstabUnparsedLine(
                    line_number=line_number,
                    raw=raw_line,
                    reason="too_many_fields",
                )
            )
            continue

        mount_options = tuple(
            value
            for value in parts[3].split(",")
            if value
        )

        fs_mgr_flags = (
            tuple(
                value
                for value in parts[4].split(",")
                if value
            )
            if len(parts) == 5
            else ()
        )

        declarations.append(
            AndroidFstabDeclaration(
                device=parts[0],
                mount_point=parts[1],
                fs_type=parts[2],
                mount_options=mount_options,
                fs_mgr_flags=fs_mgr_flags,
                line_number=line_number,
                raw=raw_line,
            )
        )

    return ParsedAndroidFstab(
        declarations=tuple(
            declarations
        ),
        unparsed_lines=tuple(
            unparsed_lines
        ),
    )


def read_android_fstab(
    path: Path,
    *,
    errors: str = "ignore",
) -> ParsedAndroidFstab:
    """
    Read and lexically parse one Android fstab source.
    """

    if not isinstance(
        path,
        Path,
    ):
        raise TypeError(
            "path must be a Path"
        )

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    if not path.is_file():
        raise IsADirectoryError(
            path
        )

    return parse_android_fstab(
        path.read_text(
            encoding="utf-8",
            errors=errors,
        )
    )