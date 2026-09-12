from __future__ import annotations

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.linker.model import (
    AndroidLinkerConfigurationAssignment,
    AndroidLinkerConfigurationSection,
    AndroidLinkerConfigurationUnparsedLine,
    ParsedAndroidLinkerConfiguration,
)


class AndroidLdConfigParser:
    """
    Lexically parse canonical Android ld.config.txt sources.

    This parser does not interpret namespaces, search paths, permitted paths,
    visibility, links, shared-library allowlists, variables, or runtime
    dependency resolution.
    """

    def parse(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidLinkerConfiguration:
        if not isinstance(
            source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            source.kind
            is not AndroidModelSourceKind
            .LINKER_CONFIGURATION
        ):
            raise ValueError(
                "source must be a linker configuration source"
            )

        if (
            source.android_path.name
            != "ld.config.txt"
        ):
            raise ValueError(
                "source must identify ld.config.txt"
            )

        path = source.host_path

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"linker configuration source is not a file: "
                f"{path}"
            )

        raw = path.read_text(
            encoding="utf-8",
        )

        sections: list[
            AndroidLinkerConfigurationSection
        ] = []

        assignments: list[
            AndroidLinkerConfigurationAssignment
        ] = []

        unparsed_lines: list[
            AndroidLinkerConfigurationUnparsedLine
        ] = []

        for source_line, raw_line in enumerate(
            raw.splitlines(),
            start=1,
        ):
            content, _, _ = raw_line.partition(
                "#"
            )

            content = content.strip()

            if not content:
                continue

            if (
                content.startswith("[")
                and content.endswith("]")
            ):
                name = content[
                    1:-1
                ].strip()

                if name:
                    sections.append(
                        AndroidLinkerConfigurationSection(
                            name=name,
                            raw=raw_line,
                            source_line=source_line,
                        )
                    )
                    continue

            operator = None
            key = ""
            value = ""

            if "+=" in content:
                key, value = content.split(
                    "+=",
                    1,
                )
                operator = "+="

            elif "=" in content:
                key, value = content.split(
                    "=",
                    1,
                )
                operator = "="

            if operator is not None:
                key = key.strip()
                value = value.strip()

                if key:
                    assignments.append(
                        AndroidLinkerConfigurationAssignment(
                            key=key,
                            operator=operator,
                            value=value,
                            raw=raw_line,
                            source_line=source_line,
                        )
                    )
                    continue

            unparsed_lines.append(
                AndroidLinkerConfigurationUnparsedLine(
                    raw=raw_line,
                    content=content,
                    source_line=source_line,
                )
            )

        return ParsedAndroidLinkerConfiguration(
            source=source,
            raw=raw,
            sections=tuple(
                sections
            ),
            assignments=tuple(
                assignments
            ),
            unparsed_lines=tuple(
                unparsed_lines
            ),
        )

    def parse_sources(
        self,
        sources: tuple[
            AndroidModelSource,
            ...,
        ],
    ) -> tuple[
        ParsedAndroidLinkerConfiguration,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                AndroidModelSource,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only AndroidModelSource entries"
            )

        text_sources = tuple(
            source
            for source in sources
            if (
                source.kind
                is AndroidModelSourceKind
                .LINKER_CONFIGURATION
                and source.android_path.name
                == "ld.config.txt"
            )
        )

        parsed = tuple(
            self.parse(
                source
            )
            for source in text_sources
        )

        expected_source_ids = {
            id(source)
            for source
            in text_sources
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
            raise ValueError(
                "ld.config.txt Parsing failed to conserve the "
                "complete selected canonical source population"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed
        ):
            raise ValueError(
                "ld.config.txt Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return tuple(
            sorted(
                parsed,
                key=lambda item: (
                    item.source.source_name,
                    item.source.android_path.as_posix(),
                ),
            )
        )
