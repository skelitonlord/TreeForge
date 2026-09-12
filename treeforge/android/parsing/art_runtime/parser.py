from __future__ import annotations

from treeforge.android.parsing.art_runtime.image import (
    AndroidArtImageParser,
)
from treeforge.android.parsing.art_runtime.model import (
    AndroidArtRuntimeParsingResult,
)
from treeforge.android.parsing.art_runtime.oat import (
    AndroidOatParser,
)
from treeforge.android.parsing.art_runtime.vdex import (
    AndroidVdexParser,
)
from treeforge.android.parsing.elf.model import (
    AndroidElfParsingResult,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


class AndroidArtRuntimeParser:
    def __init__(
        self,
        *,
        oat_parser: AndroidOatParser | None = None,
        vdex_parser: AndroidVdexParser | None = None,
        image_parser: AndroidArtImageParser | None = None,
    ) -> None:
        self.oat_parser = (
            oat_parser
            if oat_parser is not None
            else AndroidOatParser()
        )

        self.vdex_parser = (
            vdex_parser
            if vdex_parser is not None
            else AndroidVdexParser()
        )

        self.image_parser = (
            image_parser
            if image_parser is not None
            else AndroidArtImageParser()
        )

    def parse(
        self,
        *,
        elf: AndroidElfParsingResult,
        source_inventory: AndroidModelSourceInventory,
    ) -> AndroidArtRuntimeParsingResult:
        oat_files = self.oat_parser.parse(
            elf
        )

        art_runtime_sources = tuple(
            source
            for source
            in source_inventory.sources
            if (
                source.kind
                is AndroidModelSourceKind.ART_RUNTIME
            )
        )

        vdex_files = []
        art_images = []

        for source in art_runtime_sources:
            suffix = (
                source.android_path.suffix.lower()
            )

            if suffix == ".vdex":
                vdex_files.append(
                    self.vdex_parser.parse_source(
                        source
                    )
                )

            elif suffix == ".art":
                art_images.append(
                    self.image_parser.parse_source(
                        source
                    )
                )

            else:
                raise ValueError(
                    "unsupported canonical ART_RUNTIME source "
                    f"suffix: {suffix!r}"
                )

        expected_source_ids = {
            id(source)
            for source
            in art_runtime_sources
        }

        parsed_source_ids = {
            id(value.source)
            for value
            in (
                *vdex_files,
                *art_images,
            )
        }

        if (
            expected_source_ids
            != parsed_source_ids
        ):
            raise ValueError(
                "ART-runtime Parsing failed to conserve every "
                "canonical ART_RUNTIME source exactly once"
            )

        if len(
            parsed_source_ids
        ) != (
            len(
                vdex_files
            )
            + len(
                art_images
            )
        ):
            raise ValueError(
                "ART-runtime Parsing duplicated a canonical "
                "AndroidModelSource"
            )

        return AndroidArtRuntimeParsingResult(
            oat_files=oat_files,
            vdex_files=tuple(
                sorted(
                    vdex_files,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            ),
            art_images=tuple(
                sorted(
                    art_images,
                    key=lambda value: (
                        value.source.identity_key
                    ),
                )
            ),
        )
