from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    AndroidFilesystemParsingResult,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)
from treeforge.android.universe.properties.evidence import (
    AndroidUniversePropertyEvidence,
)
from treeforge.android.universe.properties.model import (
    interpret_android_universe_property,
)


class AndroidUniversePropertyInterpreter:
    """
    Interpret canonical parsed Android properties into Universe evidence.

    Files are never reread or reparsed here.
    """

    def interpret(
        self,
        *,
        parsing: AndroidFilesystemParsingResult,
        source_inventory: AndroidModelSourceInventory,
    ) -> tuple[
        AndroidUniversePropertyEvidence,
        ...,
    ]:
        if not isinstance(
            parsing,
            AndroidFilesystemParsingResult,
        ):
            raise TypeError(
                "parsing must be an "
                "AndroidFilesystemParsingResult"
            )

        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an "
                "AndroidModelSourceInventory"
            )

        property_sources = {
            source.host_path: source
            for source in source_inventory.sources_for(
                AndroidModelSourceKind.PROPERTY
            )
        }

        evidence: list[
            AndroidUniversePropertyEvidence
        ] = []

        for parsed_source in parsing.property_files:
            model_source = property_sources.get(
                parsed_source.source_path
            )

            if model_source is None:
                raise ValueError(
                    "Parsed property source has no canonical "
                    "AndroidModelSource: "
                    f"{parsed_source.source_path}"
                )

            for declaration in (
                parsed_source.declarations
            ):
                fact = (
                    interpret_android_universe_property(
                        declaration.key,
                        declaration.value,
                    )
                )

                if fact is None:
                    continue

                evidence.append(
                    AndroidUniversePropertyEvidence(
                        fact=fact,
                        parsed_source=parsed_source,
                        declaration=declaration,
                        model_source=model_source,
                    )
                )

        return tuple(
            evidence
        )