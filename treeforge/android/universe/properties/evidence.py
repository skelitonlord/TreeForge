from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidPropertyFile,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)
from treeforge.android.parsing.properties import (
    AndroidPropertyDeclaration,
)
from treeforge.android.universe.properties.model import (
    AndroidUniversePropertyFact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniversePropertyEvidence:
    """
    One property-derived Device Universe observation.

    Exact Parsing objects and canonical source objects are retained rather
    than copied into a second provenance representation.
    """

    fact: AndroidUniversePropertyFact
    parsed_source: ParsedAndroidPropertyFile
    declaration: AndroidPropertyDeclaration
    model_source: AndroidModelSource

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.fact,
            AndroidUniversePropertyFact,
        ):
            raise TypeError(
                "fact must be an AndroidUniversePropertyFact"
            )

        if not isinstance(
            self.parsed_source,
            ParsedAndroidPropertyFile,
        ):
            raise TypeError(
                "parsed_source must be a "
                "ParsedAndroidPropertyFile"
            )

        if not isinstance(
            self.declaration,
            AndroidPropertyDeclaration,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidPropertyDeclaration"
            )

        if not isinstance(
            self.model_source,
            AndroidModelSource,
        ):
            raise TypeError(
                "model_source must be an AndroidModelSource"
            )

        if (
            self.parsed_source.source_path
            != self.model_source.host_path
        ):
            raise ValueError(
                "parsed source must match the exact "
                "canonical model source"
            )

        if (
            self.declaration
            not in self.parsed_source.declarations
        ):
            raise ValueError(
                "declaration must belong to parsed_source"
            )

    @property
    def partition(
        self,
    ):
        return (
            self.model_source
            .filesystem_source
            .partition
        )

    @property
    def extraction_artifact(
        self,
    ):
        return (
            self.model_source
            .filesystem_source
            .artifact
        )