from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidPropertyFile,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniversePropertySourceRecord:
    """
    Complete Universe preservation of one exact parsed property source.

    Parsing remains authoritative for:
    - declarations;
    - duplicate declaration ordering;
    - unsupported/unparsed lexical material;
    - source path;
    - Android-visible path;
    - filesystem provenance.

    Universe retains the exact ParsedAndroidPropertyFile and exact canonical
    AndroidModelSource so sources remain visible even when they produce zero
    interpreted property facts.
    """

    parsed_source: ParsedAndroidPropertyFile
    model_source: AndroidModelSource

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.parsed_source,
            ParsedAndroidPropertyFile,
        ):
            raise TypeError(
                "parsed_source must be a ParsedAndroidPropertyFile"
            )

        if not isinstance(
            self.model_source,
            AndroidModelSource,
        ):
            raise TypeError(
                "model_source must be an AndroidModelSource"
            )

        if self.parsed_source.source is not self.model_source:
            raise ValueError(
                "property source record must preserve exact canonical "
                "AndroidModelSource identity"
            )

        if (
            self.parsed_source.source_path
            != self.model_source.host_path
        ):
            raise ValueError(
                "property parsed source path must match canonical "
                "model-source host path"
            )

        if (
            self.parsed_source.android_path
            != self.model_source.android_path
        ):
            raise ValueError(
                "property parsed Android path must match canonical "
                "model-source Android path"
            )

        if (
            self.parsed_source.filesystem_source
            is not self.model_source.filesystem_source
        ):
            raise ValueError(
                "property parsed filesystem source must preserve exact "
                "canonical filesystem-source identity"
            )

    @property
    def identity_key(
        self,
    ):
        return self.model_source.identity_key
