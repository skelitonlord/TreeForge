from __future__ import annotations

import gzip
import re

from treeforge.android.extraction import (
    ExtractedArtifact,
    ExtractionOperation,
)
from treeforge.android.format.compression import (
    CompressionFormat,
    detect_compression,
)
from treeforge.android.parsing.kernel.model import (
    ParsedKernelConfig,
    ParsedKernelConfigDeclaration,
    ParsedKernelConfigUnparsedLine,
    ParsedKernelImage,
)


class AndroidKernelParsingError(
    ValueError,
):
    pass


class AndroidKernelImageParser:
    """
    Decode intrinsic information from one canonical materialized kernel image.

    Physical kernel extraction/decompression remains owned by Extraction.
    Cross-source/device-level interpretation remains owned by Universe.
    """

    IKCONFIG_START = b"IKCFG_ST"
    IKCONFIG_END = b"IKCFG_ED"

    LINUX_BANNER = re.compile(
        rb"Linux version [^\x00\r\n]+"
    )

    NOT_SET = re.compile(
        r"^# (CONFIG_[A-Za-z0-9_]+) is not set$"
    )

    DECLARATION = re.compile(
        r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$"
    )

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> ParsedKernelImage:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if artifact.semantic_name != "kernel_image":
            raise AndroidKernelParsingError(
                "kernel parser requires the canonical "
                "'kernel_image' Extraction artifact"
            )

        if (
            artifact.operation
            is not ExtractionOperation.KERNEL_DECOMPRESSION
        ):
            raise AndroidKernelParsingError(
                "kernel_image must originate from canonical "
                "kernel decompression"
            )

        data = artifact.path.read_bytes()

        banner = self._linux_banner(
            data
        )

        release = None

        if banner is not None:
            prefix = "Linux version "
            remainder = banner[len(prefix):]

            if remainder:
                release = remainder.split(
                    None,
                    1,
                )[0]

        config = self._embedded_config(
            data
        )

        return ParsedKernelImage(
            artifact=artifact,
            linux_banner=banner,
            kernel_release=release,
            config=config,
        )

    def _linux_banner(
        self,
        data: bytes,
    ) -> str | None:
        match = self.LINUX_BANNER.search(
            data
        )

        if match is None:
            return None

        try:
            return match.group(0).decode(
                "ascii"
            )
        except UnicodeDecodeError as error:
            raise AndroidKernelParsingError(
                "Linux version banner is not valid ASCII"
            ) from error

    def _embedded_config(
        self,
        data: bytes,
    ) -> ParsedKernelConfig | None:
        start = data.find(
            self.IKCONFIG_START
        )

        if start < 0:
            return None

        second_start = data.find(
            self.IKCONFIG_START,
            start + len(self.IKCONFIG_START),
        )

        if second_start >= 0:
            raise AndroidKernelParsingError(
                "kernel contains ambiguous IKCONFIG start markers"
            )

        payload_start = (
            start
            + len(self.IKCONFIG_START)
        )

        end = data.find(
            self.IKCONFIG_END,
            payload_start,
        )

        if end < 0:
            raise AndroidKernelParsingError(
                "kernel IKCONFIG start marker has no end marker"
            )

        payload = data[
            payload_start:end
        ]

        compression = detect_compression(
            payload
        )

        if compression is not CompressionFormat.GZIP:
            raise AndroidKernelParsingError(
                "unsupported embedded IKCONFIG compression: "
                f"{compression.value}"
            )

        try:
            config_bytes = gzip.decompress(
                payload
            )
        except OSError as error:
            raise AndroidKernelParsingError(
                "unable to decompress embedded IKCONFIG"
            ) from error

        try:
            text = config_bytes.decode(
                "utf-8"
            )
        except UnicodeDecodeError as error:
            raise AndroidKernelParsingError(
                "embedded IKCONFIG is not UTF-8 text"
            ) from error

        declarations: list[
            ParsedKernelConfigDeclaration
        ] = []

        unparsed: list[
            ParsedKernelConfigUnparsedLine
        ] = []

        for line_number, raw in enumerate(
            text.splitlines(),
            start=1,
        ):
            stripped = raw.strip()

            if not stripped:
                continue

            not_set = self.NOT_SET.fullmatch(
                stripped
            )

            if not_set is not None:
                declarations.append(
                    ParsedKernelConfigDeclaration(
                        key=not_set.group(1),
                        value=None,
                        enabled=False,
                        line_number=line_number,
                        raw=raw,
                    )
                )
                continue

            declaration = self.DECLARATION.fullmatch(
                stripped
            )

            if declaration is not None:
                key = declaration.group(1)
                value = declaration.group(2)

                enabled: bool | None = None

                if value in ("y", "m"):
                    enabled = True
                elif value == "n":
                    enabled = False

                declarations.append(
                    ParsedKernelConfigDeclaration(
                        key=key,
                        value=value,
                        enabled=enabled,
                        line_number=line_number,
                        raw=raw,
                    )
                )
                continue

            if stripped.startswith("#"):
                continue

            unparsed.append(
                ParsedKernelConfigUnparsedLine(
                    line_number=line_number,
                    raw=raw,
                    reason=(
                        "line is neither a CONFIG declaration "
                        "nor '# CONFIG_* is not set'"
                    ),
                )
            )

        return ParsedKernelConfig(
            compression=compression,
            marker_start_offset=start,
            payload_start_offset=payload_start,
            marker_end_offset=end,
            declarations=tuple(
                declarations
            ),
            unparsed_lines=tuple(
                unparsed
            ),
        )
