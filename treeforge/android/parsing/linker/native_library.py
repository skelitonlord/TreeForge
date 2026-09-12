from __future__ import annotations

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)
from treeforge.android.parsing.linker.model import (
    AndroidNativeLibraryConfigurationDeclaration,
    ParsedAndroidNativeLibraryConfiguration,
)


class AndroidNativeLibraryConfigurationParser:
    """
    Parse one canonical Android native-library configuration source.

    This parser performs only lexical decoding. It deliberately does not
    infer linker namespaces, library visibility, ABI policy, VNDK/LLNDK
    semantics, dependency targets, or build-system participation.
    """

    def parse(
        self,
        source: AndroidModelSource,
    ) -> ParsedAndroidNativeLibraryConfiguration:
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
            .NATIVE_LIBRARY_CONFIGURATION
        ):
            raise ValueError(
                "source must be a native-library configuration source"
            )

        path = source.host_path

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"native-library configuration source is not a file: "
                f"{path}"
            )

        raw = path.read_text(
            encoding="utf-8",
        )

        declarations: list[
            AndroidNativeLibraryConfigurationDeclaration
        ] = []

        for line_number, raw_line in enumerate(
            raw.splitlines(),
            start=1,
        ):
            content, _, _ = raw_line.partition(
                "#"
            )

            content = content.strip()

            if not content:
                continue

            declarations.append(
                AndroidNativeLibraryConfigurationDeclaration(
                    raw=raw_line,
                    content=content,
                    tokens=tuple(
                        content.split()
                    ),
                    source_line=line_number,
                )
            )

        return ParsedAndroidNativeLibraryConfiguration(
            source=source,
            raw=raw,
            declarations=tuple(
                declarations
            ),
        )

    def parse_sources(
        self,
        sources: tuple[
            AndroidModelSource,
            ...,
        ],
    ) -> tuple[
        ParsedAndroidNativeLibraryConfiguration,
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

        parsed = tuple(
            self.parse(
                source
            )
            for source in sources
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
            raise ValueError(
                "native-library configuration Parsing failed to "
                "conserve the complete canonical source population"
            )

        if len(
            actual_source_ids
        ) != len(
            parsed
        ):
            raise ValueError(
                "native-library configuration Parsing duplicated "
                "a canonical AndroidModelSource"
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
