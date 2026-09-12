from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.format.compression import (
    CompressionFormat,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedKernelConfigDeclaration:
    """
    One literal declaration decoded from an embedded Linux kernel config.

    Parsing preserves lexical evidence only. Device-level interpretation of
    kernel configuration belongs to AndroidDeviceUniverse.
    """

    key: str
    value: str | None
    enabled: bool | None
    line_number: int
    raw: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key:
            raise ValueError("key must be a non-empty string")

        if self.value is not None and not isinstance(self.value, str):
            raise TypeError("value must be a string or None")

        if self.enabled is not None and not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool or None")

        if (
            isinstance(self.line_number, bool)
            or not isinstance(self.line_number, int)
            or self.line_number < 1
        ):
            raise ValueError("line_number must be a positive integer")

        if not isinstance(self.raw, str):
            raise TypeError("raw must be a string")


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedKernelConfigUnparsedLine:
    line_number: int
    raw: str
    reason: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.line_number, bool)
            or not isinstance(self.line_number, int)
            or self.line_number < 1
        ):
            raise ValueError("line_number must be a positive integer")

        if not isinstance(self.raw, str):
            raise TypeError("raw must be a string")

        if not isinstance(self.reason, str) or not self.reason:
            raise ValueError("reason must be a non-empty string")


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedKernelConfig:
    """
    Intrinsic contents of one embedded Linux kernel configuration.
    """

    compression: CompressionFormat
    marker_start_offset: int
    payload_start_offset: int
    marker_end_offset: int

    declarations: tuple[
        ParsedKernelConfigDeclaration,
        ...,
    ] = ()

    unparsed_lines: tuple[
        ParsedKernelConfigUnparsedLine,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.compression, CompressionFormat):
            raise TypeError("compression must be a CompressionFormat")

        for name in (
            "marker_start_offset",
            "payload_start_offset",
            "marker_end_offset",
        ):
            value = getattr(self, name)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer")

        if not isinstance(self.declarations, tuple):
            raise TypeError("declarations must be a tuple")

        if not all(
            isinstance(value, ParsedKernelConfigDeclaration)
            for value in self.declarations
        ):
            raise TypeError(
                "declarations must contain "
                "ParsedKernelConfigDeclaration instances"
            )

        if not isinstance(self.unparsed_lines, tuple):
            raise TypeError("unparsed_lines must be a tuple")

        if not all(
            isinstance(value, ParsedKernelConfigUnparsedLine)
            for value in self.unparsed_lines
        ):
            raise TypeError(
                "unparsed_lines must contain "
                "ParsedKernelConfigUnparsedLine instances"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedKernelImage:
    """
    Intrinsic Parsing result for the exact canonical kernel image.

    Extraction identity and provenance remain authoritative. Parsing records
    only information physically encoded in that kernel image.
    """

    artifact: ExtractedArtifact

    linux_banner: str | None = None
    kernel_release: str | None = None
    config: ParsedKernelConfig | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, ExtractedArtifact):
            raise TypeError("artifact must be an ExtractedArtifact")

        if self.artifact.semantic_name != "kernel_image":
            raise ValueError(
                "kernel Parsing requires semantic_name='kernel_image'"
            )

        if self.linux_banner is not None:
            if not isinstance(self.linux_banner, str):
                raise TypeError("linux_banner must be a string or None")
            if not self.linux_banner:
                raise ValueError("linux_banner cannot be empty")

        if self.kernel_release is not None:
            if not isinstance(self.kernel_release, str):
                raise TypeError("kernel_release must be a string or None")
            if not self.kernel_release:
                raise ValueError("kernel_release cannot be empty")

        if self.config is not None and not isinstance(
            self.config,
            ParsedKernelConfig,
        ):
            raise TypeError("config must be a ParsedKernelConfig or None")

    @property
    def config_count(self) -> int:
        if self.config is None:
            return 0
        return len(self.config.declarations)

    @property
    def unparsed_config_count(self) -> int:
        if self.config is None:
            return 0
        return len(self.config.unparsed_lines)
