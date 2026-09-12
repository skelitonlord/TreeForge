from __future__ import annotations

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.kernel_module.model import (
    AndroidKernelModuleConfigurationKind,
    AndroidKernelModuleConfigurationLine,
    ParsedAndroidKernelModuleConfiguration,
)


class AndroidKernelModuleConfigurationParsingError(
    ValueError,
):
    pass


class AndroidKernelModuleConfigurationParser:
    """
    Parse literal Linux/Android kernel-module configuration files.

    This parser owns only source decoding and lexical preservation. Dependency
    graphs, module identity reconciliation, runtime load order, aliases,
    softdeps, blocklists, and deployment context belong to Android Device
    Universe.
    """

    _KINDS = {
        kind.value: kind
        for kind
        in AndroidKernelModuleConfigurationKind
    }

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> tuple[
        ParsedAndroidKernelModuleConfiguration,
        ...,
    ]:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an AndroidModelSourceInventory"
            )

        sources = tuple(
            source
            for source
            in inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind
                .KERNEL_MODULE_CONFIGURATION
            )
        )

        parsed = tuple(
            self._parse_source(
                source
            )
            for source
            in sources
        )

        expected_source_ids = {
            id(source)
            for source
            in sources
        }

        actual_source_ids = {
            id(value.source)
            for value
            in parsed
        }

        if (
            expected_source_ids
            != actual_source_ids
        ):
            raise AndroidKernelModuleConfigurationParsingError(
                "kernel-module configuration Parsing failed to "
                "conserve the complete canonical source population"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed
        ):
            raise AndroidKernelModuleConfigurationParsingError(
                "kernel-module configuration Parsing duplicated "
                "a canonical AndroidModelSource"
            )

        return tuple(
            sorted(
                parsed,
                key=lambda value: (
                    value.source.filesystem_source
                    .source_name,
                    value.source.android_path
                    .as_posix(),
                ),
            )
        )

    def _parse_source(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidKernelModuleConfiguration:
        kind = self._KINDS.get(
            source.host_path.name
        )

        if kind is None:
            raise AndroidKernelModuleConfigurationParsingError(
                "unsupported kernel-module configuration source: "
                f"{source.host_path.name}"
            )

        try:
            raw = source.host_path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ) as error:
            raise AndroidKernelModuleConfigurationParsingError(
                "failed to read kernel-module configuration source "
                f"{source.filesystem_source.source_name}:"
                f"{source.android_path.as_posix()}: "
                f"{error}"
            ) from error

        lines: list[
            AndroidKernelModuleConfigurationLine
        ] = []

        for line_number, raw_line in enumerate(
            raw.splitlines(),
            start=1,
        ):
            content = self._meaningful_content(
                raw_line
            )

            if not content:
                continue

            lines.append(
                AndroidKernelModuleConfigurationLine(
                    raw=raw_line,
                    content=content,
                    tokens=tuple(
                        content.split()
                    ),
                    source_line=line_number,
                )
            )

        return (
            ParsedAndroidKernelModuleConfiguration(
                source=source,
                configuration_kind=kind,
                raw=raw,
                lines=tuple(
                    lines
                ),
            )
        )

    @staticmethod
    def _meaningful_content(
        raw_line: str,
    ) -> str:
        #
        # modules.* sources use shell-style '#' comments. Parsing strips only
        # the comment portion for lexical tokens while retaining the complete
        # original line in ``raw``.
        #
        content, _, _ = raw_line.partition(
            "#"
        )

        return content.strip()
