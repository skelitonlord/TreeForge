from __future__ import annotations

from importlib import import_module

import click
import typer
from typer.core import TyperGroup
from typer.main import get_command


class TreeForgeLazyGroup(
    TyperGroup,
):
    """
    Root TreeForge command group with lazy downstream-stage imports.

    Earlier first-class commands must remain usable even when a later stage
    temporarily has an incompatible or incomplete implementation.
    """

    _LAZY_COMMANDS = {
        "universe": (
            "treeforge.cli.universe",
            "app",
            "Build the Android Device Universe.",
        ),
        "runtime-linking": (
            "treeforge.cli.runtime_linking",
            "app",
            "Resolve Android runtime-linking semantics.",
        ),
        "reconstruction": (
            "treeforge.cli.reconstruction",
            "reconstruction",
            "Run TreeForge reconstruction.",
        ),
        "device-tree": (
            "treeforge.cli.device_tree",
            "app",
            "Generate the Android device/vendor tree.",
        ),
        "install": (
            "treeforge.cli.install",
            "app",
            "Install an accepted Android build onto hardware.",
        ),
        "repartition": (
            "treeforge.cli.repartition",
            "app",
            "Plan the tangorpro TreeForge A/B storage layout.",
        ),
    }

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(
            *args,
            **kwargs,
        )

        self._lazy_command_cache: dict[
            str,
            click.Command,
        ] = {}

    def list_commands(
        self,
        ctx: click.Context,
    ) -> list[str]:
        commands = set(
            super().list_commands(
                ctx
            )
        )

        commands.update(
            self._LAZY_COMMANDS
        )

        return sorted(
            commands
        )

    def get_command(
        self,
        ctx: click.Context,
        cmd_name: str,
    ) -> click.Command | None:
        command = super().get_command(
            ctx,
            cmd_name,
        )

        if command is not None:
            return command

        if (
            cmd_name
            not in self._LAZY_COMMANDS
        ):
            return None

        cached = (
            self._lazy_command_cache.get(
                cmd_name
            )
        )

        if cached is not None:
            return cached

        (
            module_name,
            attribute_name,
            _,
        ) = self._LAZY_COMMANDS[
            cmd_name
        ]

        module = import_module(
            module_name
        )

        target = getattr(
            module,
            attribute_name,
        )

        if isinstance(
            target,
            typer.Typer,
        ):
            command = get_command(
                target
            )

        else:
            lazy_app = typer.Typer()

            lazy_app.command(
                name=cmd_name,
            )(
                target
            )

            command = get_command(
                lazy_app
            )

        self._lazy_command_cache[
            cmd_name
        ] = command

        return command

    def format_commands(
        self,
        ctx: click.Context,
        formatter: click.HelpFormatter,
    ) -> None:
        """
        Render root help without importing lazy downstream commands.
        """

        rows: list[
            tuple[
                str,
                str,
            ]
        ] = []

        for name in (
            super().list_commands(
                ctx
            )
        ):
            command = (
                super().get_command(
                    ctx,
                    name,
                )
            )

            if (
                command is None
                or command.hidden
            ):
                continue

            rows.append(
                (
                    name,
                    command.get_short_help_str(),
                )
            )

        for (
            name,
            (
                _,
                _,
                help_text,
            ),
        ) in sorted(
            self._LAZY_COMMANDS.items()
        ):
            rows.append(
                (
                    name,
                    help_text,
                )
            )

        if not rows:
            return

        with formatter.section(
            "Commands"
        ):
            formatter.write_dl(
                rows
            )
