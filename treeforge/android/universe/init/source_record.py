from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitSourceRecord:
    """
    Complete Universe preservation of one exact parsed INIT source.

    The exact ParsedAndroidInitSource remains authoritative for:
    - raw source text;
    - imports;
    - services;
    - actions;
    - unparsed lines;
    - canonical Parsing provenance.

    This record exists even when a source produces zero semantic declaration
    requirements, preventing declaration-empty sources from disappearing from
    Universe.
    """

    parsed_source: ParsedAndroidInitSource
    model_source: AndroidModelSource

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.parsed_source,
            ParsedAndroidInitSource,
        ):
            raise TypeError(
                "parsed_source must be a ParsedAndroidInitSource"
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
                "INIT source record must preserve exact canonical "
                "AndroidModelSource identity"
            )

        if (
            self.parsed_source.source_path
            != self.model_source.host_path
        ):
            raise ValueError(
                "INIT parsed source path must match canonical "
                "model-source host path"
            )

        if (
            self.parsed_source.android_path
            != self.model_source.android_path
        ):
            raise ValueError(
                "INIT parsed Android path must match canonical "
                "model-source Android path"
            )

        if (
            self.parsed_source.filesystem_source
            is not self.model_source.filesystem_source
        ):
            raise ValueError(
                "INIT parsed filesystem source must preserve exact "
                "canonical filesystem-source identity"
            )

    @property
    def source_identity(
        self,
    ) -> str:
        return android_universe_init_source_identity(
            source_path=self.parsed_source.source_path,
            android_path=self.parsed_source.android_path,
            filesystem_source=(
                self.parsed_source.filesystem_source
            ),
        )

    @property
    def identity_key(
        self,
    ):
        return self.model_source.identity_key
