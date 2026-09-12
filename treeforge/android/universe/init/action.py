from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidParserFilesystemSource,
)
from treeforge.android.parsing.init.model import (
    AndroidInitAction,
    AndroidInitCommand,
)
from treeforge.android.universe.init.source_identity import (
    android_universe_init_source_identity,
)
from treeforge.android.universe.init.action_command import (
    AndroidUniverseInitActionCommandRequirement,
)
from treeforge.android.universe.init.action_trigger import (
    AndroidUniverseInitActionTrigger,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitActionRequirement:
    """
    One canonical INIT action requirement.

    The complete parsed action remains attached so trigger text, ordered
    commands, source locations, raw syntax, and future provenance remain
    lossless. Command-specific semantic interpretation is deliberately a
    later Universe concern.
    """

    source_path: Path
    android_path: PurePosixPath | None
    filesystem_source: AndroidParserFilesystemSource | None
    action: AndroidInitAction

    trigger_semantics: AndroidUniverseInitActionTrigger

    command_requirements: tuple[
        AndroidUniverseInitActionCommandRequirement,
        ...,
    ]

    @property
    def trigger(
        self,
    ) -> str:
        return self.action.trigger

    @property
    def commands(
        self,
    ) -> tuple[
        AndroidInitCommand,
        ...,
    ]:
        return self.action.commands

    @property
    def requirement_id(
        self,
    ) -> str:
        source_identity = (
            android_universe_init_source_identity(
                source_path=self.source_path,
                android_path=self.android_path,
                filesystem_source=self.filesystem_source,
            )
        )

        return (
            f"init-action:{source_identity}:"
            f"{self.action.location.line}"
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
            self.action,
            AndroidInitAction,
        ):
            raise TypeError(
                "action must be an AndroidInitAction"
            )

        if not isinstance(
            self.trigger_semantics,
            AndroidUniverseInitActionTrigger,
        ):
            raise TypeError(
                "trigger_semantics must be an "
                "AndroidUniverseInitActionTrigger"
            )

        if self.trigger_semantics.action is not self.action:
            raise ValueError(
                "trigger_semantics must preserve "
                "AndroidInitAction identity"
            )

        if not isinstance(
            self.command_requirements,
            tuple,
        ):
            raise TypeError(
                "command_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseInitActionCommandRequirement,
            )
            for item in self.command_requirements
        ):
            raise TypeError(
                "command_requirements must contain only "
                "AndroidUniverseInitActionCommandRequirement "
                "instances"
            )

        if len(
            self.command_requirements
        ) != len(
            self.action.commands
        ):
            raise ValueError(
                "command_requirements must correspond one-to-one "
                "with action.commands"
            )

        for parsed, requirement in zip(
            self.action.commands,
            self.command_requirements,
            strict=True,
        ):
            if requirement.command is not parsed:
                raise ValueError(
                    "command_requirements must preserve parsed "
                    "AndroidInitCommand identity and ordering"
                )
