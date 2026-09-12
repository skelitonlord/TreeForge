from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.init.model import (
    AndroidInitService,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)
from treeforge.android.universe.init.semantics import (
    AndroidUniverseInitServiceSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitServiceRequirement:
    """
    One canonical service requirement derived from an Android init source.

    The complete parsed service declaration and its source identities are
    retained so Universe interpretation remains additive and lossless.

    Service-option semantics, applicability, cross-source reconciliation,
    and action/service relationships are separate Universe concerns.
    """

    source_path: Path
    android_path: PurePosixPath | None
    filesystem_source: AndroidParserFilesystemSource | None
    service: AndroidInitService
    semantics: AndroidUniverseInitServiceSemantics

    @property
    def name(
        self,
    ) -> str:
        return self.service.name

    @property
    def executable(
        self,
    ) -> str:
        return self.service.executable

    @property
    def arguments(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        return self.service.arguments

    @property
    def requirement_id(
        self,
    ) -> str:
        """
        Return deterministic Universe-local identity for this declaration.

        Source identity and declaration line are retained deliberately:
        same-named declarations from distinct sources must not collapse
        before Universe reconciliation determines their relationship.
        """

        source_identity = (
            android_universe_init_source_identity(
                source_path=self.source_path,
                android_path=self.android_path,
                filesystem_source=self.filesystem_source,
            )
        )

        return (
            f"init-service:{source_identity}:"
            f"{self.service.location.line}"
        )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if (
            self.filesystem_source is not None
            and not isinstance(
                self.filesystem_source,
                AndroidParserFilesystemSource,
            )
        ):
            raise TypeError(
                "filesystem_source must be an "
                "AndroidParserFilesystemSource or None"
            )

        if (
            self.android_path is not None
            and self.filesystem_source is None
        ):
            raise ValueError(
                "filesystem_source is required when "
                "android_path is present"
            )

        if not isinstance(
            self.service,
            AndroidInitService,
        ):
            raise TypeError(
                "service must be an AndroidInitService"
            )

        if not isinstance(
            self.semantics,
            AndroidUniverseInitServiceSemantics,
        ):
            raise TypeError(
                "semantics must be an "
                "AndroidUniverseInitServiceSemantics"
            )
