from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from shutil import which
import sys

import typer

from treeforge.android.host_provider_sync import (
    provider_release_lock_metadata,
    provider_release_record,
)
from treeforge.setup.host_providers import (
    verify_android_host_providers,
)


app = typer.Typer(
    help=(
        "Verify the Python environment, TreeForge-owned Android "
        "host providers, and system host tools."
    )
)


@dataclass(
    frozen=True,
    slots=True,
)
class EnvironmentCheck:
    name: str
    available: bool
    detail: str
    required: bool = True


_REQUIRED_PYTHON_PACKAGES: tuple[
    tuple[
        str,
        str,
    ],
    ...,
] = (
    (
        "typer",
        "typer",
    ),
    (
        "rich",
        "rich",
    ),
    (
        "pydantic",
        "pydantic",
    ),
    (
        "lxml",
        "lxml",
    ),
    (
        "networkx",
        "networkx",
    ),
    (
        "pyelftools",
        "elftools",
    ),
    (
        "lz4",
        "lz4",
    ),
    (
        "zstandard",
        "zstandard",
    ),
)


def _check_python_runtime() -> EnvironmentCheck:
    version = (
        f"{sys.version_info.major}."
        f"{sys.version_info.minor}."
        f"{sys.version_info.micro}"
    )

    supported = (
        sys.version_info
        >= (
            3,
            11,
        )
    )

    return EnvironmentCheck(
        name="Python runtime",
        available=supported,
        detail=(
            f"Python {version}"
            if supported
            else (
                f"Python {version}; TreeForge requires "
                "Python 3.11 or newer"
            )
        ),
    )


def _check_treeforge_import() -> EnvironmentCheck:
    try:
        available = (
            find_spec(
                "treeforge"
            )
            is not None
        )
    except Exception:
        available = False

    return EnvironmentCheck(
        name="TreeForge package",
        available=available,
        detail=(
            "importable"
            if available
            else "not importable"
        ),
    )


def _check_python_package(
    *,
    display_name: str,
    import_name: str,
) -> EnvironmentCheck:
    try:
        available = (
            find_spec(
                import_name
            )
            is not None
        )
    except Exception:
        available = False

    return EnvironmentCheck(
        name=display_name,
        available=available,
        detail=(
            f"Python import {import_name!r} available"
            if available
            else f"Python import {import_name!r} unavailable"
        ),
    )


def _check_host_tool(
    *,
    name: str,
    executable: str,
    purpose: str,
    required: bool = True,
) -> EnvironmentCheck:
    candidate = Path(
        executable
    )

    if candidate.parent != Path("."):
        available = (
            candidate.is_file()
            and (
                candidate.stat().st_mode
                & 0o111
            )
            != 0
        )

        resolved = (
            str(
                candidate.resolve()
            )
            if available
            else executable
        )
    else:
        found = which(
            executable
        )

        available = (
            found is not None
        )

        resolved = (
            found
            if found is not None
            else executable
        )

    return EnvironmentCheck(
        name=name,
        available=available,
        detail=(
            f"{resolved}; {purpose}"
            if available
            else (
                f"unavailable: {executable}; "
                f"{purpose}"
            )
        ),
        required=required,
    )


def _check_android_providers() -> EnvironmentCheck:
    try:
        providers = (
            verify_android_host_providers()
        )
    except Exception as error:
        return EnvironmentCheck(
            name="Android host providers",
            available=False,
            detail=str(
                error
            ),
        )

    release_lock = (
        provider_release_lock_metadata()
    )

    provider_details = []

    for provider in providers:
        record = provider_release_record(
            provider.name
        )

        provider_details.append(
            f"{provider.name}="
            f"{record['release_tag']}@"
            f"{record['source_commit'][:12]}:"
            f"{len(provider.executables)}exec/"
            f"{len(provider.runtime_files)}runtime/"
            f"{len(provider.legal_files)}legal/"
            f"{len(provider.provenance_files)}provenance"
        )

    detail = (
        "public="
        f"{release_lock['public_repository']}; "
        "cache=verified-first; "
        + ", ".join(
            provider_details
        )
    )

    return EnvironmentCheck(
        name="Android host providers",
        available=True,
        detail=detail,
    )


def _marker(
    check: EnvironmentCheck,
) -> str:
    return (
        "OK"
        if check.available
        else (
            "MISSING"
            if check.required
            else "OPTIONAL"
        )
    )


def _print_section(
    title: str,
    checks: tuple[
        EnvironmentCheck,
        ...,
    ],
) -> None:
    typer.echo()
    typer.echo(
        title
    )

    for check in checks:
        typer.echo(
            f"[{_marker(check)}] "
            f"{check.name}: "
            f"{check.detail}"
        )


@app.callback(
    invoke_without_command=True,
)
def doctor(
    lpdump: Path | None = typer.Option(
        None,
        "--lpdump",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Optional explicit lpdump override for developer/testing use."
        ),
    ),
    lpunpack: Path | None = typer.Option(
        None,
        "--lpunpack",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Optional explicit lpunpack override for developer/testing use."
        ),
    ),
    debugfs: Path | None = typer.Option(
        None,
        "--debugfs",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Optional explicit debugfs executable."
        ),
    ),
    simg2img: Path | None = typer.Option(
        None,
        "--simg2img",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Optional explicit simg2img override for developer/testing use."
        ),
    ),
) -> None:
    """
    Verify the TreeForge development and generation environment.
    """

    runtime_checks = (
        _check_python_runtime(),
        _check_treeforge_import(),
    )

    package_checks = tuple(
        _check_python_package(
            display_name=display_name,
            import_name=import_name,
        )
        for (
            display_name,
            import_name,
        )
        in _REQUIRED_PYTHON_PACKAGES
    )

    provider_checks = (
        _check_android_providers(),
    )

    system_checks = (
        _check_host_tool(
            name="debugfs",
            executable=(
                str(
                    debugfs
                )
                if debugfs is not None
                else "debugfs"
            ),
            purpose=(
                "Inspects and extracts ext4 filesystem images."
            ),
        ),
    )

    override_checks = []

    for name, value, purpose in (
        (
            "lpdump override",
            lpdump,
            "Explicit Android logical-partition metadata tool override.",
        ),
        (
            "lpunpack override",
            lpunpack,
            "Explicit Android logical-partition extraction tool override.",
        ),
        (
            "simg2img override",
            simg2img,
            "Explicit Android sparse-image conversion tool override.",
        ),
    ):
        if value is None:
            continue

        override_checks.append(
            _check_host_tool(
                name=name,
                executable=str(
                    value
                ),
                purpose=purpose,
            )
        )

    typer.echo(
        "TreeForge Environment Report"
    )

    _print_section(
        "Runtime",
        runtime_checks,
    )

    _print_section(
        "Python Dependencies",
        package_checks,
    )

    _print_section(
        "TreeForge-owned Android Host Providers",
        provider_checks,
    )

    _print_section(
        "System Image Tools",
        system_checks,
    )

    if override_checks:
        _print_section(
            "Explicit Android Tool Overrides",
            tuple(
                override_checks
            ),
        )

    required_checks = (
        runtime_checks
        + package_checks
        + provider_checks
        + system_checks
        + tuple(
            override_checks
        )
    )

    missing = tuple(
        check
        for check
        in required_checks
        if (
            check.required
            and not check.available
        )
    )

    if not missing:
        typer.echo()
        typer.echo(
            "TreeForge environment is ready."
        )
        return

    typer.echo()
    typer.echo(
        "Missing requirements:"
    )

    for check in missing:
        typer.echo(
            f"  - {check.name}: "
            f"{check.detail}"
        )

    if any(
        check.name
        == "debugfs"
        for check
        in missing
    ):
        typer.echo()
        typer.echo(
            "Install debugfs through the e2fsprogs system package."
        )

    raise typer.Exit(
        code=1
    )
