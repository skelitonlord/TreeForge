from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import time

import typer

from treeforge.android.host_tools import (
    treeforge_adb_executable,
)

from treeforge.android.recovery.install_set import (
    build_recovery_install_set,
    load_and_verify_recovery_install_set,
)


app = typer.Typer(
    help=(
        "Interact with TreeForge Recovery "
        "from the host."
    )
)


RECOVERY_RECEIVE_READY_PATH = (
    "/dev/"
    "treeforge-recovery-install-set-receive"
)

RECOVERY_INSTALL_SET_MANIFEST_PATH = (
    "/metadata/treeforge/"
    "recovery-install-set.manifest"
)

RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH = (
    "/dev/"
    "treeforge-recovery-install-set-transfer"
)

RECOVERY_STREAM_FIFO_PATH = (
    "/dev/treeforge-recovery-source"
)


def _adb_command(
    *,
    serial: str | None,
) -> list[str]:
    adb = (
        treeforge_adb_executable()
    )

    command = [
        str(adb),
    ]

    if serial:
        command.extend(
            (
                "-s",
                serial,
            )
        )

    return command



def _run_adb(
    args: list[str],
    *,
    serial: str | None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        (
            _adb_command(
                serial=serial
            )
            + args
        ),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    return completed


def _read_receive_state(
    *,
    serial: str | None,
) -> dict[str, str]:
    with tempfile.TemporaryDirectory(
        prefix="treeforge-recovery-"
    ) as temporary:
        destination = (
            Path(temporary)
            / "receive-state"
        )

        completed = _run_adb(
            [
                "pull",
                RECOVERY_RECEIVE_READY_PATH,
                str(destination),
            ],
            serial=serial,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "TreeForge Recovery is not "
                "armed to receive an install set.\n"
                "On the device open:\n"
                "  Flash Options -> "
                "Staged Install Set -> "
                "Enable Receive"
            )

        state = {}

        for raw_line in (
            destination
            .read_text(
                encoding="utf-8"
            )
            .splitlines()
        ):
            if "=" not in raw_line:
                continue

            key, value = raw_line.split(
                "=",
                1,
            )

            state[key] = value

        first_line = (
            destination
            .read_text(
                encoding="utf-8"
            )
            .splitlines()
        )

        if (
            not first_line
            or first_line[0]
            != (
                "treeforge-recovery-"
                "install-set-receive-v1"
            )
        ):
            raise RuntimeError(
                "connected device did not "
                "publish the expected "
                "TreeForge Recovery receive "
                "contract"
            )

        if (
            state.get("ready") != "1"
            or state.get("flashing") != "0"
        ):
            raise RuntimeError(
                "TreeForge Recovery receive "
                "session is not safely armed"
            )

        return state


def _parse_treeforge_state(
    text: str,
    *,
    schema: str,
) -> dict[str, str]:
    lines = text.splitlines()

    if (
        not lines
        or lines[0] != schema
    ):
        raise RuntimeError(
            "connected Recovery published an "
            "unexpected transfer-state schema"
        )

    values = {}

    for line in lines[1:]:
        if "=" not in line:
            continue

        key, value = line.split(
            "=",
            1,
        )

        values[key] = value

    return values


def _transfer_install_set_payloads(
    package,
    *,
    package_path: Path,
    serial: str | None,
) -> None:
    root = package_path.parent

    next_index = 0

    baseline_generation: int | None = None
    active_generation: int | None = None
    initial_state_observed = False

    typer.echo()
    typer.echo(
        "Waiting for on-device payload "
        "verification approval..."
    )
    typer.echo(
        "  Review the staged set, then choose "
        "VERIFY PAYLOADS on the device."
    )

    with tempfile.TemporaryDirectory(
        prefix="treeforge-recovery-transfer-"
    ) as temporary:
        state_path = (
            Path(temporary)
            / "transfer-state"
        )

        while True:
            if state_path.exists():
                state_path.unlink()

            completed = _run_adb(
                [
                    "pull",
                    RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH,
                    str(state_path),
                ],
                serial=serial,
            )

            if (
                completed.returncode != 0
                or not state_path.is_file()
            ):
                if not initial_state_observed:
                    # No transfer state existed when this host command
                    # started. Any later positive generation therefore
                    # belongs to a new device attempt.
                    baseline_generation = 0
                    initial_state_observed = True

                time.sleep(
                    0.25
                )

                continue

            state = _parse_treeforge_state(
                state_path.read_text(
                    encoding="utf-8"
                ),
                schema=(
                    "treeforge-recovery-"
                    "install-set-transfer-v1"
                ),
            )

            state_name = state.get(
                "state"
            )

            try:
                generation = int(
                    state[
                        "generation"
                    ]
                )

            except (
                KeyError,
                ValueError,
            ) as exc:
                raise RuntimeError(
                    "Recovery published malformed "
                    "transfer generation"
                ) from exc

            if generation <= 0:
                raise RuntimeError(
                    "Recovery published invalid "
                    f"transfer generation: {generation}"
                )

            if not initial_state_observed:
                baseline_generation = generation
                initial_state_observed = True

            if active_generation is None:
                if (
                    state_name == "ready"
                    or generation
                        != baseline_generation
                ):
                    active_generation = generation

                else:
                    # This is terminal state left by the previous
                    # attempt. Wait for Recovery to begin a new one.
                    time.sleep(
                        0.25
                    )
                    continue

            elif generation != active_generation:
                if generation > active_generation:
                    active_generation = generation
                    next_index = 0

                else:
                    time.sleep(
                        0.25
                    )
                    continue

            if state_name == "cancelled":
                typer.echo()
                typer.echo(
                    "Recovery payload verification cancelled."
                )
                typer.echo(
                    "  Partition writes: 0"
                )

                return

            if state_name == "error":
                raise RuntimeError(
                    "Recovery rejected payload "
                    "verification: "
                    f"index={state.get('index')} "
                    f"partition={state.get('partition')} "
                    f"stage={state.get('stage')} "
                    f"errno={state.get('errno')}"
                )

            if state_name == "complete":
                try:
                    verified = int(
                        state.get(
                            "verified",
                            "-1",
                        )
                    )

                except ValueError as exc:
                    raise RuntimeError(
                        "Recovery published an invalid "
                        "verified payload count"
                    ) from exc

                if (
                    verified
                    != len(package.images)
                ):
                    raise RuntimeError(
                        "Recovery completed payload "
                        "verification with an unexpected "
                        f"count: {verified}"
                    )

                typer.echo()
                typer.echo(
                    "Recovery payload verification "
                    "complete."
                )
                typer.echo(
                    f"  Verified: {verified} / "
                    f"{len(package.images)}"
                )
                typer.echo(
                    "  Partition writes: 0"
                )

                return

            if state_name != "ready":
                time.sleep(
                    0.25
                )
                continue

            try:
                index = int(
                    state[
                        "index"
                    ]
                )
                expected_bytes = int(
                    state[
                        "bytes"
                    ]
                )

            except (
                KeyError,
                ValueError,
            ) as exc:
                raise RuntimeError(
                    "Recovery published malformed "
                    "READY payload state"
                ) from exc

            if index < next_index:
                # Recovery may still expose the previous READY state
                # briefly while validating the just-completed stream.
                time.sleep(
                    0.10
                )
                continue

            if index != next_index:
                raise RuntimeError(
                    "Recovery requested payloads "
                    "out of order: "
                    f"expected index {next_index}, "
                    f"received {index}"
                )

            if index >= len(
                package.images
            ):
                raise RuntimeError(
                    "Recovery requested an image index "
                    "outside the staged package"
                )

            image = package.images[
                index
            ]

            partition = state.get(
                "partition"
            )

            expected_sha256 = state.get(
                "sha256"
            )

            if (
                partition
                != image.partition_name
                or expected_bytes
                    != image.source_bytes
                or expected_sha256
                    != image.sha256
            ):
                raise RuntimeError(
                    "Recovery payload request does "
                    "not match the verified host package: "
                    f"index={index}"
                )

            source_path = (
                root
                / image.path
            ).resolve()

            try:
                source_path.relative_to(
                    root
                )

            except ValueError as exc:
                raise RuntimeError(
                    "Recovery payload path escaped "
                    "the install-set root"
                ) from exc

            typer.echo()
            typer.echo(
                f"Sending payload "
                f"{index + 1}/"
                f"{len(package.images)}:"
            )
            typer.echo(
                f"  Partition: "
                f"{image.partition_name}"
            )
            typer.echo(
                f"  Format: "
                f"{image.image_format}"
            )
            typer.echo(
                f"  Bytes: "
                f"{image.source_bytes}"
            )

            completed = _run_adb(
                [
                    "push",
                    str(source_path),
                    RECOVERY_STREAM_FIFO_PATH,
                ],
                serial=serial,
            )

            if completed.returncode != 0:
                message = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "unknown adb error"
                )

                raise RuntimeError(
                    "unable to stream Recovery "
                    f"payload {image.partition_name}: "
                    f"{message}"
                )

            next_index += 1


def _manual_partition_target(
    partition: str,
    *,
    active_slot: str,
) -> tuple[str, str]:
    normalized = (
        partition
        .strip()
        .lower()
    )

    if not normalized:
        raise ValueError(
            "partition cannot be empty"
        )

    if active_slot not in {
        "a",
        "b",
    }:
        raise RuntimeError(
            "Recovery active slot is unresolved"
        )

    explicit_slot = None
    canonical = normalized

    if normalized.endswith(
        (
            "_a",
            "_b",
        )
    ):
        explicit_slot = normalized[-1]
        canonical = normalized[:-2]

    if not canonical:
        raise ValueError(
            "partition has no canonical name"
        )

    for value in canonical:
        if not (
            "a" <= value <= "z"
            or "0" <= value <= "9"
            or value == "_"
        ):
            raise ValueError(
                "partition may contain only "
                "lowercase letters, digits, "
                "and underscores"
            )

    target_slot = (
        explicit_slot
        if explicit_slot is not None
        else (
            "b"
            if active_slot == "a"
            else "a"
        )
    )

    if target_slot == active_slot:
        raise RuntimeError(
            "refusing explicit install to "
            f"active slot {active_slot.upper()}"
        )

    return (
        canonical,
        target_slot,
    )


def _stage_install_manifest(
    package,
    *,
    package_path: Path,
    serial: str | None,
) -> None:
    manifest_path = (
        package_path.parent
        / package.recovery_manifest
    )

    completed = _run_adb(
        [
            "push",
            str(manifest_path),
            RECOVERY_INSTALL_SET_MANIFEST_PATH,
        ],
        serial=serial,
    )

    if completed.returncode != 0:
        message = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown adb error"
        )

        raise RuntimeError(
            "unable to stage Recovery "
            f"Install Set manifest: {message}"
        )


def _prepare_manual_install_package(
    partition: str,
    image: Path,
    *,
    output: Path,
    serial: str | None,
):
    # Manual mode starts from an explicitly armed receive session,
    # exactly like `treeforge recovery stage`.
    state = _read_receive_state(
        serial=serial
    )

    active_slot = state.get(
        "active_slot"
    )

    canonical, target_slot = (
        _manual_partition_target(
            partition,
            active_slot=active_slot,
        )
    )

    source = (
        image
        .expanduser()
        .resolve()
    )

    if not source.is_file():
        raise FileNotFoundError(
            f"image does not exist: {source}"
        )

    deployment = SimpleNamespace(
        images=(
            SimpleNamespace(
                partition_name=canonical,
                final_path=source,
            ),
        ),
    )

    package_path = (
        build_recovery_install_set(
            deployment,
            output_root=(
                output
                / "recovery"
                / "manual-install"
            ),
            target_slot=target_slot,
            image_set="manual",
        )
    )

    package = (
        load_and_verify_recovery_install_set(
            package_path
        )
    )

    if len(package.images) != 1:
        raise RuntimeError(
            "manual Recovery package did not "
            "contain exactly one image"
        )

    _stage_install_manifest(
        package,
        package_path=package_path,
        serial=serial,
    )

    return (
        package,
        package_path,
        active_slot,
    )


def _run_install_transaction(
    package,
    *,
    package_path: Path,
    serial: str | None,
) -> None:
    root = package_path.parent.resolve()

    # Host transports only formats understood by the current
    # Recovery Install Set protocol. Recovery remains authoritative for
    # whether the target is physical/logical and whether that exact
    # format is destructively supported.
    for image in package.images:
        if image.image_format not in {
            "raw",
            "android-sparse",
        }:
            raise RuntimeError(
                "unsupported Recovery install image format: "
                f"{image.partition_name} "
                f"({image.image_format})"
            )

    next_index = 0
    reported_verified: set[int] = set()

    baseline_generation: int | None = None
    active_generation: int | None = None
    initial_state_observed = False

    typer.echo()
    typer.echo(
        "Waiting for Recovery INSTALL SET "
        "authorization..."
    )

    with tempfile.TemporaryDirectory(
        prefix="treeforge-recovery-install-"
    ) as temporary:
        state_path = (
            Path(temporary)
            / "transfer-state"
        )

        while True:
            if state_path.exists():
                state_path.unlink()

            completed = _run_adb(
                [
                    "pull",
                    RECOVERY_INSTALL_SET_TRANSFER_STATE_PATH,
                    str(state_path),
                ],
                serial=serial,
            )

            if (
                completed.returncode != 0
                or not state_path.is_file()
            ):
                if not initial_state_observed:
                    # There was no pre-existing transaction state.
                    baseline_generation = 0
                    initial_state_observed = True

                time.sleep(
                    0.25
                )
                continue

            state = _parse_treeforge_state(
                state_path.read_text(
                    encoding="utf-8"
                ),
                schema=(
                    "treeforge-recovery-"
                    "install-set-transfer-v1"
                ),
            )

            state_name = state.get(
                "state"
            )

            try:
                generation = int(
                    state[
                        "generation"
                    ]
                )

            except (
                KeyError,
                ValueError,
            ) as exc:
                raise RuntimeError(
                    "Recovery published malformed "
                    "install transfer generation"
                ) from exc

            if generation <= 0:
                raise RuntimeError(
                    "Recovery published invalid install "
                    f"transfer generation: {generation}"
                )

            if not initial_state_observed:
                baseline_generation = generation
                initial_state_observed = True

            if active_generation is None:
                if (
                    state_name == "write-ready"
                    or generation
                        != baseline_generation
                ):
                    active_generation = generation

                else:
                    # Ignore the terminal state left by a previous
                    # install/cancel attempt.
                    time.sleep(
                        0.25
                    )
                    continue

            elif generation != active_generation:
                if generation > active_generation:
                    active_generation = generation
                    next_index = 0
                    reported_verified.clear()

                else:
                    time.sleep(
                        0.25
                    )
                    continue

            if state_name == "write-cancelled":
                typer.echo()
                typer.echo(
                    "Recovery install cancelled "
                    "before any partition write."
                )

                return

            if state_name in {
                "write-error",
                "error",
            }:
                raise RuntimeError(
                    "Recovery failed install: "
                    f"index={state.get('index')} "
                    f"partition={state.get('partition')} "
                    f"stage={state.get('stage')} "
                    f"errno={state.get('errno')}"
                )

            if state_name == "write-verified":
                try:
                    index = int(
                        state[
                            "index"
                        ]
                    )

                except (
                    KeyError,
                    ValueError,
                ) as exc:
                    raise RuntimeError(
                        "Recovery published malformed "
                        "write-verified state"
                    ) from exc

                if (
                    index < 0
                    or index >= len(
                        package.images
                    )
                ):
                    raise RuntimeError(
                        "Recovery verified an image "
                        "outside the host package"
                    )

                if index not in reported_verified:
                    reported_verified.add(
                        index
                    )

                    typer.echo()
                    typer.echo(
                        f"Image {index + 1}/"
                        f"{len(package.images)} "
                        "written and readback-verified:"
                    )
                    typer.echo(
                        "  "
                        f"{package.images[index].partition_name}"
                    )

                time.sleep(
                    0.10
                )
                continue

            if state_name == "transaction-complete":
                try:
                    installed = int(
                        state.get(
                            "installed",
                            "-1",
                        )
                    )

                except ValueError as exc:
                    raise RuntimeError(
                        "Recovery published invalid "
                        "installed image count"
                    ) from exc

                if (
                    installed
                        != len(package.images)
                    or next_index
                        != len(package.images)
                ):
                    raise RuntimeError(
                        "Recovery completed with an "
                        "unexpected count: "
                        f"installed={installed}, "
                        f"sent={next_index}, "
                        f"expected={len(package.images)}"
                    )

                typer.echo()
                typer.echo(
                    "Recovery install transaction complete."
                )
                typer.echo(
                    "  Installed and verified: "
                    f"{installed} / "
                    f"{len(package.images)}"
                )
                typer.echo(
                    "  Slot activation: disabled"
                )

                return

            if state_name != "write-ready":
                time.sleep(
                    0.25
                )
                continue

            try:
                index = int(
                    state[
                        "index"
                    ]
                )
                expected_bytes = int(
                    state[
                        "bytes"
                    ]
                )

            except (
                KeyError,
                ValueError,
            ) as exc:
                raise RuntimeError(
                    "Recovery published malformed "
                    "write-ready state"
                ) from exc

            if index < next_index:
                time.sleep(
                    0.10
                )
                continue

            if index != next_index:
                raise RuntimeError(
                    "Recovery requested images "
                    "out of order: "
                    f"expected={next_index}, "
                    f"received={index}"
                )

            if index >= len(
                package.images
            ):
                raise RuntimeError(
                    "Recovery requested an image "
                    "outside the verified package"
                )

            image = package.images[
                index
            ]

            if (
                state.get("partition")
                    != image.partition_name
                or expected_bytes
                    != image.source_bytes
                or state.get("sha256")
                    != image.sha256
            ):
                raise RuntimeError(
                    "Recovery write request does not "
                    "match the verified host package"
                )

            source_path = (
                root
                / image.path
            ).resolve()

            try:
                source_path.relative_to(
                    root
                )

            except ValueError as exc:
                raise RuntimeError(
                    "Recovery image escaped "
                    "install-set root"
                ) from exc

            typer.echo()
            typer.echo(
                f"Sending install image "
                f"{index + 1}/"
                f"{len(package.images)}:"
            )
            typer.echo(
                f"  Partition: "
                f"{image.partition_name}"
            )
            typer.echo(
                f"  Bytes: "
                f"{image.source_bytes}"
            )
            typer.echo(
                f"  SHA-256: "
                f"{image.sha256}"
            )

            completed = _run_adb(
                [
                    "push",
                    str(source_path),
                    RECOVERY_STREAM_FIFO_PATH,
                ],
                serial=serial,
            )

            if completed.returncode != 0:
                message = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "unknown adb error"
                )

                raise RuntimeError(
                    "unable to stream Recovery "
                    f"install image "
                    f"{image.partition_name}: "
                    f"{message}"
                )

            next_index += 1


@app.command(
    "install",
)
def install(
    partition: str | None = typer.Argument(
        None,
        help=(
            "Optional partition for an explicit "
            "single-image install."
        ),
    ),
    image: Path | None = typer.Argument(
        None,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help=(
            "Optional image for an explicit "
            "single-image install."
        ),
    ),
    install_set: Path | None = typer.Option(
        None,
        "--install-set",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help=(
            "Optional Recovery Install Set. "
            "Cannot be combined with PARTITION IMAGE."
        ),
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. "
            "Defaults to ./output."
        ),
    ),
    serial: str | None = typer.Option(
        None,
        "--serial",
        help=(
            "Optional explicit ADB serial."
        ),
    ),
) -> None:
    """
    Install through TreeForge Recovery.

    No arguments:
        install the staged Recovery Install Set.

    PARTITION IMAGE:
        construct and install a temporary one-image
        Recovery Install Set.
    """

    has_partition = (
        partition is not None
    )

    has_image = (
        image is not None
    )

    if has_partition != has_image:
        typer.echo(
            "PARTITION and IMAGE must either "
            "both be supplied or both be omitted.",
            err=True,
        )

        raise typer.Exit(
            code=2
        )

    manual_mode = (
        has_partition
        and has_image
    )

    if (
        manual_mode
        and install_set is not None
    ):
        typer.echo(
            "--install-set cannot be combined "
            "with PARTITION IMAGE.",
            err=True,
        )

        raise typer.Exit(
            code=2
        )

    typer.echo(
        "TreeForge Recovery Install"
    )

    if manual_mode:
        typer.echo()
        typer.echo(
            "Mode: explicit single image"
        )

        try:
            (
                package,
                package_path,
                active_slot,
            ) = _prepare_manual_install_package(
                partition,
                image,
                output=output,
                serial=serial,
            )

        except Exception as error:
            typer.echo(
                f"Unable to prepare manual "
                f"install: {error}",
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

        typer.echo(
            f"  Active slot: "
            f"{active_slot.upper()}"
        )
        typer.echo(
            f"  Target slot: "
            f"{package.target_slot.upper()}"
        )
        typer.echo(
            f"  Partition: "
            f"{package.images[0].partition_name}"
        )
        typer.echo(
            f"  Image: {image}"
        )

        typer.echo()
        typer.echo(
            "On the device:"
        )
        typer.echo(
            "  1. Press Volume Down to CHECK PACKAGE"
        )
        typer.echo(
            "  2. Select VERIFY PAYLOADS"
        )
        typer.echo(
            "  3. Select YES - VERIFY PAYLOADS"
        )

        try:
            _transfer_install_set_payloads(
                package,
                package_path=package_path,
                serial=serial,
            )

        except KeyboardInterrupt:
            typer.echo()
            typer.echo(
                "Recovery install interrupted.",
                err=True,
            )

            raise typer.Exit(
                code=130
            )

        except Exception as error:
            typer.echo(
                f"Payload verification failed: "
                f"{error}",
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

        typer.echo()
        typer.echo(
            "Payload verified."
        )
        typer.echo(
            "On the device:"
        )
        typer.echo(
            "  1. Press Power to return"
        )
        typer.echo(
            "  2. Select INSTALL SET"
        )
        typer.echo(
            "  3. Confirm YES - INSTALL SET"
        )

    else:
        typer.echo()
        typer.echo(
            "Mode: staged install set"
        )

        package_path = (
            install_set
            if install_set is not None
            else (
                output
                / "boot-image"
                / "deployment"
                / "recovery"
                / "install-set.json"
            )
        )

        package_path = (
            package_path
            .expanduser()
            .resolve()
        )

        try:
            package = (
                load_and_verify_recovery_install_set(
                    package_path
                )
            )

        except Exception as error:
            typer.echo(
                "Install Set verification failed: "
                f"{error}",
                err=True,
            )

            raise typer.Exit(
                code=1
            ) from error

        typer.echo(
            "Install Set verified."
        )
        typer.echo(
            f"  Target slot: "
            f"{package.target_slot.upper()}"
        )
        typer.echo(
            f"  Images: "
            f"{len(package.images)}"
        )

    typer.echo()
    typer.echo(
        "Current writer:"
    )
    typer.echo(
        "  physical RAW"
    )
    typer.echo(
        "  stream SHA-256 verification"
    )
    typer.echo(
        "  independent readback verification"
    )
    typer.echo(
        "  sparse/logical writes: disabled"
    )
    typer.echo(
        "  slot activation: disabled"
    )

    try:
        _run_install_transaction(
            package,
            package_path=package_path,
            serial=serial,
        )

    except KeyboardInterrupt:
        typer.echo()
        typer.echo(
            "Recovery install interrupted by host.",
            err=True,
        )

        raise typer.Exit(
            code=130
        )

    except Exception as error:
        typer.echo()
        typer.echo(
            f"Recovery install failed: {error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error


@app.command(
    "stage",
)
def stage(
    install_set: Path | None = typer.Option(
        None,
        "--install-set",
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
        help=(
            "Optional explicit Recovery "
            "Install Set package. Defaults to "
            "OUTPUT/boot-image/deployment/"
            "recovery/install-set.json."
        ),
    ),
    output: Path = typer.Option(
        Path("./output"),
        "--output",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge output root. "
            "Defaults to ./output."
        ),
    ),
    serial: str | None = typer.Option(
        None,
        "--serial",
        help=(
            "Optional explicit ADB serial."
        ),
    ),
) -> None:
    """
    Stage the latest Boot Image Recovery
    Install Set to an armed TreeForge Recovery.
    """

    package_path = (
        install_set
        if install_set is not None
        else (
            output
            / "boot-image"
            / "deployment"
            / "recovery"
            / "install-set.json"
        )
    )

    package_path = (
        package_path
        .expanduser()
        .resolve()
    )

    typer.echo(
        "TreeForge Recovery Stage"
    )

    typer.echo()
    typer.echo(
        "Verifying Recovery Install Set..."
    )

    try:
        package = (
            load_and_verify_recovery_install_set(
                package_path
            )
        )

    except Exception as error:
        typer.echo(
            f"Install Set verification failed: "
            f"{error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo(
        f"  Image set: "
        f"{package.image_set}"
    )
    typer.echo(
        f"  Target slot: "
        f"{package.target_slot.upper()}"
    )
    typer.echo(
        f"  Images: "
        f"{len(package.images)}"
    )

    typer.echo()
    typer.echo(
        "Checking Recovery receive state..."
    )

    try:
        state = _read_receive_state(
            serial=serial
        )

    except Exception as error:
        typer.echo(
            str(error),
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    active_slot = state.get(
        "active_slot"
    )

    typer.echo(
        "  Recovery active slot: "
        f"{active_slot or '<unknown>'}"
    )

    if active_slot not in {
        "a",
        "b",
    }:
        typer.echo(
            "Recovery did not report a "
            "resolved active slot.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    if (
        active_slot
        == package.target_slot
    ):
        typer.echo(
            "Refusing to stage package: "
            "its target slot is currently "
            "active.",
            err=True,
        )

        raise typer.Exit(
            code=1
        )

    manifest_path = (
        package_path.parent
        / package.recovery_manifest
    )

    typer.echo()
    typer.echo(
        "Staging Recovery package metadata..."
    )

    completed = _run_adb(
        [
            "push",
            str(manifest_path),
            (
                RECOVERY_INSTALL_SET_MANIFEST_PATH
            ),
        ],
        serial=serial,
    )

    if completed.returncode != 0:
        typer.echo(
            "Unable to stage Recovery "
            "Install Set manifest.",
            err=True,
        )

        if completed.stderr.strip():
            typer.echo(
                completed.stderr.strip(),
                err=True,
            )

        raise typer.Exit(
            code=1
        )

    typer.echo()
    typer.echo(
        "Recovery Install Set metadata staged."
    )

    typer.echo(
        "  Target slot: "
        f"{package.target_slot.upper()}"
    )

    for image in package.images:
        typer.echo(
            "  "
            f"{image.partition_name}: "
            f"{image.image_format}, "
            f"{image.source_bytes} bytes, "
            f"expanded "
            f"{image.expanded_bytes} bytes"
        )

    typer.echo()
    typer.echo(
        "On the device:"
    )
    typer.echo(
        "  1. Press Volume Down to CHECK PACKAGE"
    )
    typer.echo(
        "  2. Select VERIFY PAYLOADS"
    )
    typer.echo(
        "  3. Select YES - VERIFY PAYLOADS"
    )

    try:
        _transfer_install_set_payloads(
            package,
            package_path=package_path,
            serial=serial,
        )

    except KeyboardInterrupt:
        typer.echo()
        typer.echo(
            "Recovery staging interrupted by host.",
            err=True,
        )

        raise typer.Exit(
            code=130
        )

    except Exception as error:
        typer.echo()
        typer.echo(
            f"Payload transfer failed: {error}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from error

    typer.echo()
    typer.echo(
        "Recovery Install Set payloads verified."
    )
    typer.echo(
        "No partition writes were requested."
    )

    typer.echo()
    typer.echo(
        "Next:"
    )
    typer.echo(
        "  1. On the device press Power to "
        "return to the staged-set summary"
    )
    typer.echo(
        "  2. Select INSTALL SET"
    )
    typer.echo(
        "  3. When Recovery prompts for the host, run:"
    )
    typer.echo(
        "       treeforge recovery install"
    )
