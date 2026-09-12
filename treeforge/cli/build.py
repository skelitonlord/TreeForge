from __future__ import annotations

# TreeForge Build runtime support.
import errno
import fcntl
import hashlib
import json
import pty
import struct
import termios
import sys

import contextlib
import datetime as dt
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import typer

from treeforge.cli.repository_root import AOSP_ROOT, TREEFORGE_ROOT


app = typer.Typer(
    help=(
        "Compose and run Android builds from TreeForge's repo-local "
        "AOSP workspace."
    )
)

VALID_VARIANTS = ("user", "userdebug", "eng")
VALID_KERNEL_SOURCES = (
    "treeforge-release",
    "treeforge-local",
    "treeforge-build",
    "aosp",

    # Compatibility aliases for old saved Build state / scripts.
    "treeforge-output",
    "treeforge",
    "source",
)

KERNEL_PROVIDER_REQUIRED_ARTIFACTS = (
    "Image",
    "dtb.img",
    "dtbo.img",
    "boot.img",
    "vendor_kernel_boot.img",
    "vendor_dlkm.img",
    "system_dlkm.img",
    "vendor_dlkm.modules.load",
    "vendor_dlkm.modules.blocklist",
    "system_dlkm.modules.load",
    "system_dlkm.modules.blocklist",
    "vendor_kernel_boot.modules.load",
)
VALID_GAPPS = ("none", "mindthegapps")
VALID_SIGNING = ("treeforge", "aosp")
VALID_DEVICE_TOOLS = ("treeforge", "aosp")

TREEFORGE_KERNEL_RELEASE_REPOSITORY = os.environ.get(
    "TREEFORGE_KERNEL_RELEASE_REPOSITORY",
    "Skellyaosp/treeforge_kernel",
)

MINDTHEGAPPS_URL = "https://gitlab.com/MindTheGapps/vendor_gapps.git"
MINDTHEGAPPS_BRANCH = "vic"
MINDTHEGAPPS_PIN = "af160b7fba89b2ea23aad432c7d0716e1639f0f9"

AVB_FIELDS = (
    ("vbmeta", "BOARD_AVB_KEY_PATH", "BOARD_AVB_ALGORITHM"),
    ("boot", "BOARD_AVB_BOOT_KEY_PATH", "BOARD_AVB_BOOT_ALGORITHM"),
    ("init_boot", "BOARD_AVB_INIT_BOOT_KEY_PATH", "BOARD_AVB_INIT_BOOT_ALGORITHM"),
    (
        "vbmeta_system",
        "BOARD_AVB_VBMETA_SYSTEM_KEY_PATH",
        "BOARD_AVB_VBMETA_SYSTEM_ALGORITHM",
    ),
    (
        "vbmeta_vendor",
        "BOARD_AVB_VBMETA_VENDOR_KEY_PATH",
        "BOARD_AVB_VBMETA_VENDOR_ALGORITHM",
    ),
)

TREEFORGE_AVB_ALGORITHMS = {
    "vbmeta": "SHA256_RSA4096",
    "boot": "SHA256_RSA2048",
    "init_boot": "SHA256_RSA2048",
    "vbmeta_system": "SHA256_RSA2048",
    "vbmeta_vendor": "SHA256_RSA2048",
}


@dataclass(frozen=True, slots=True)
class LunchTarget:
    raw: str
    product: str
    release: str
    variant: str

    @classmethod
    def parse(cls, value: str) -> "LunchTarget":
        normalized = value.strip()
        parts = normalized.rsplit("-", 2)
        if len(parts) != 3 or parts[2] not in VALID_VARIANTS:
            raise ValueError(
                "lunch target must be PRODUCT-RELEASE-{user,userdebug,eng}: "
                f"{value!r}"
            )
        return cls(
            raw=normalized,
            product=parts[0],
            release=parts[1],
            variant=parts[2],
        )


@dataclass(frozen=True, slots=True)
class TargetProbe:
    lunch: LunchTarget
    device: str
    arch: str
    product_out: str
    values: dict[str, str]


def _run(
    command: list[str],
    *,
    cwd: Path,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=merged,
        text=True,
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def _bash_capture(aosp_root: Path, body: str) -> str:
    try:
        result = _run(
            ["bash", "-lc", body],
            cwd=aosp_root,
            capture=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            "AOSP shell command failed"
            + (f": {detail}" if detail else "")
        ) from exc
    return result.stdout


def _validate_aosp_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"AOSP workspace does not exist: {root}")
    if not (root / "build" / "envsetup.sh").is_file():
        raise RuntimeError(
            f"AOSP workspace is missing build/envsetup.sh: {root}"
        )
    return root


def _reject_source_root_product_outputs(
    aosp_root: Path,
) -> None:
    """
    Refuse to build when an immediate child of the AOSP source root
    looks like PRODUCT_OUT.

    A product-output directory placed directly in the source checkout
    can contain copied Android.bp files. Soong will then discover those
    files as source and may report duplicate modules.

    Normal output roots such as out/, out-*/, and out_* are allowed.
    TreeForge never removes suspicious directories automatically.
    """

    markers = (
        ("build_fingerprint.txt", "file"),
        (".installable_files.previous", "file"),
        ("previous_build_config.mk", "file"),
        ("boot.img", "file"),
        ("symbols", "dir"),
        ("system", "dir"),
        ("recovery", "dir"),
    )

    suspects: list[
        tuple[Path, list[str]]
    ] = []

    try:
        children = sorted(
            aosp_root.iterdir(),
            key=lambda path: path.name,
        )
    except OSError as exc:
        raise RuntimeError(
            f"unable to inspect AOSP root: {aosp_root}"
        ) from exc

    for child in children:
        if not child.is_dir():
            continue

        name = child.name

        if (
            name == "out"
            or name.startswith("out-")
            or name.startswith("out_")
            or name.startswith(".")
        ):
            continue

        #
        # PRODUCT_OUT normally has obj/. Requiring it makes the check
        # conservative enough to avoid confusing ordinary source
        # projects with build output.
        #
        if not (child / "obj").is_dir():
            continue

        found: list[str] = [
            "obj/"
        ]

        for relative, kind in markers:
            candidate = child / relative

            present = (
                candidate.is_file()
                if kind == "file"
                else candidate.is_dir()
            )

            if present:
                suffix = "/" if kind == "dir" else ""
                found.append(
                    relative + suffix
                )

        #
        # obj/ plus two independent product-output markers is enough
        # to identify a source-root contamination candidate.
        #
        if len(found) >= 3:
            suspects.append(
                (child, found)
            )

    if not suspects:
        return

    details = []

    for path, found in suspects:
        details.append(
            "  "
            + str(path)
            + "\n"
            + "    markers: "
            + ", ".join(found)
        )

    raise RuntimeError(
        "AOSP source-root contamination detected.\n"
        "\n"
        "The following directories look like PRODUCT_OUT but live "
        "directly inside the AOSP source checkout:\n"
        + "\n".join(details)
        + "\n\n"
        "Move or remove these build-output directories before building. "
        "AOSP product output belongs under out/target/product/<device> "
        "or another configured OUT_DIR, never directly under the "
        "source root. TreeForge will not delete them automatically."
    )


def _checkout_platform_release(
    aosp_root: Path,
) -> str | None:
    """
    Detect the release config matching the checked-out Android build.

    Example:
        BUILD_ID=BP1A.250505.005.D1
        -> bp1a
    """

    build_id_files = (
        aosp_root
        / "build"
        / "make"
        / "core"
        / "build_id.mk",

        aosp_root
        / "build"
        / "core"
        / "build_id.mk",
    )

    release_root = (
        aosp_root
        / "build"
        / "release"
        / "release_configs"
    )

    pattern = re.compile(
        r"^\s*BUILD_ID\s*:?=\s*"
        r"([A-Za-z0-9]+)"
        r"(?:\.|\s|$)"
    )

    for build_id_file in build_id_files:
        if not build_id_file.is_file():
            continue

        try:
            lines = build_id_file.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError:
            continue

        for raw_line in lines:
            line = raw_line.split("#", 1)[0]

            match = pattern.match(line)

            if match is None:
                continue

            release = (
                match.group(1)
                .lower()
            )

            if (
                release_root
                / f"{release}.textproto"
            ).is_file():
                return release

    return None



def _checkout_android_platform_tag(
    aosp_root: Path,
) -> str | None:
    """
    Determine the canonical Android platform/source tag for this checkout.

    This identity is distinct from the lunch release-config identity.

    Example:
        platform tag:         android-15.0.0_r36
        lunch release config: bp1a

    Provider compatibility uses the platform tag.
    Lunch discovery continues to use _checkout_platform_release().
    """

    root = (
        aosp_root
        .expanduser()
        .resolve()
    )

    tag_pattern = re.compile(
        r"^android-\d+\.\d+\.\d+_r\d+$"
    )

    #
    # Canonical repo workspaces keep the manifest repository here.
    # Prefer an exact tag at manifest HEAD when available.
    #
    manifests_git = (
        root
        / ".repo"
        / "manifests.git"
    )

    if manifests_git.is_dir():
        try:
            completed = subprocess.run(
                [
                    "git",
                    f"--git-dir={manifests_git}",
                    "tag",
                    "--points-at",
                    "HEAD",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=15,
            )
        except (
            OSError,
            subprocess.TimeoutExpired,
        ):
            completed = None

        if (
            completed is not None
            and completed.returncode == 0
        ):
            tags = tuple(
                sorted(
                    {
                        line.strip()
                        for line
                        in completed.stdout.splitlines()
                        if tag_pattern.fullmatch(
                            line.strip()
                        )
                    }
                )
            )

            if len(tags) == 1:
                return tags[0]

    #
    # TreeForge/custom manifest repositories may have their own branch
    # at HEAD while including an upstream pinned Android manifest.
    # Follow only the ACTIVE manifest include graph instead of scanning
    # every XML file in the manifest repository.
    #
    repo_root = root / ".repo"
    manifests_root = repo_root / "manifests"

    roots = (
        repo_root / "manifest.xml",
        manifests_root / "default.xml",
    )

    revision_pattern = re.compile(
        r"refs/tags/"
        r"(android-\d+\.\d+\.\d+_r\d+)"
    )

    include_pattern = re.compile(
        r"<include\b[^>]*\bname="
        r"[\"']([^\"']+)[\"']"
    )

    found: set[str] = set()
    visited: set[Path] = set()

    def inspect_manifest(
        path: Path,
    ) -> None:
        candidate = path.resolve()

        if candidate in visited:
            return

        visited.add(candidate)

        if not candidate.is_file():
            return

        try:
            text = candidate.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            return

        for match in revision_pattern.finditer(
            text
        ):
            found.add(
                match.group(1)
            )

        for match in include_pattern.finditer(
            text
        ):
            name = match.group(1)

            included = (
                manifests_root
                / name
            )

            inspect_manifest(
                included
            )

    for manifest in roots:
        inspect_manifest(
            manifest
        )

    if len(found) == 1:
        return next(iter(found))

    return None


def _normalize_discovered_lunch(
    aosp_root: Path,
    target: LunchTarget,
) -> LunchTarget:
    """
    Replace trunk_staging with the release belonging to this checkout.

    This applies only to automatically discovered lunch combinations.
    An explicit --lunch value remains untouched.
    """

    if target.release != "trunk_staging":
        return target

    release = _checkout_platform_release(
        aosp_root
    )

    if release is None:
        return target

    return LunchTarget(
        raw=(
            f"{target.product}-"
            f"{release}-"
            f"{target.variant}"
        ),
        product=target.product,
        release=release,
        variant=target.variant,
    )


def _common_lunch_targets(
    aosp_root: Path,
) -> list[LunchTarget]:
    """
    Discover lunch combinations statically from AndroidProducts.mk.

    AOSP trees commonly register trunk_staging combinations. TreeForge
    translates those to the release config matching the checked-out
    Android build, such as BP1A -> bp1a.

    No dumpvars, list_products, lunch, or Make evaluation occurs here.
    """

    device_root = (
        aosp_root
        / "device"
    )

    if not device_root.is_dir():
        return []

    lunch_pattern = re.compile(
        r"(?<![A-Za-z0-9_.+-])"
        r"([A-Za-z0-9_.+-]+"
        r"-[A-Za-z0-9_.+-]+"
        r"-(?:user|userdebug|eng))"
        r"(?![A-Za-z0-9_.+-])"
    )

    targets: dict[
        str,
        LunchTarget,
    ] = {}

    for products_file in sorted(
        device_root.rglob(
            "AndroidProducts.mk"
        )
    ):
        try:
            content = products_file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        active_content = "\n".join(
            line.split("#", 1)[0]
            for line in content.splitlines()
        )

        for match in lunch_pattern.finditer(
            active_content
        ):
            raw = match.group(1)

            try:
                target = LunchTarget.parse(
                    raw
                )
            except ValueError:
                continue

            target = _normalize_discovered_lunch(
                aosp_root,
                target,
            )

            targets.setdefault(
                target.raw,
                target,
            )

    return [
        targets[name]
        for name in sorted(
            targets
        )
    ]


def _list_products(
    aosp_root: Path,
) -> list[str]:
    """
    Discover products statically beneath aosp/device.

    Explicit lunch registrations are preferred. PRODUCT_NAME
    declarations provide a fallback for products which do not publish
    COMMON_LUNCH_CHOICES.
    """

    device_root = (
        aosp_root
        / "device"
    )

    if not device_root.is_dir():
        return []

    products: set[str] = set()

    for target in _common_lunch_targets(
        aosp_root
    ):
        products.add(
            target.product
        )

    product_pattern = re.compile(
        r"^\s*PRODUCT_NAME\s*:?="
        r"\s*([A-Za-z0-9_.+-]+)"
        r"\s*$",
        re.MULTILINE,
    )

    for makefile in sorted(
        device_root.rglob("*.mk")
    ):
        try:
            text = (
                makefile
                .read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
        except OSError:
            continue

        active_text = "\n".join(
            line.split("#", 1)[0]
            for line in text.splitlines()
        )

        for match in (
            product_pattern
            .finditer(
                active_text
            )
        ):
            products.add(
                match.group(1)
            )

    return sorted(
        products
    )


def _list_releases(
    aosp_root: Path,
    product: str,
) -> list[str]:
    """
    Resolve releases from statically registered lunch targets.

    Products without an explicit registered lunch target can still use
    manual release entry in the interactive build flow.
    """

    return sorted(
        {
            target.release
            for target
            in _common_lunch_targets(
                aosp_root
            )
            if (
                target.product
                == product
            )
        }
    )


def _select_numbered(
    heading: str,
    options: list[tuple[str, str]],
    default: int,
) -> str:
    typer.echo("")
    typer.echo(heading)
    typer.echo("")
    for index, (_, label) in enumerate(options, start=1):
        typer.echo(f"  {index}. {label}")
    typer.echo("")
    raw = typer.prompt("Select", default=str(default)).strip()
    try:
        number = int(raw)
    except ValueError as exc:
        raise typer.BadParameter("selection must be a number") from exc
    if not 1 <= number <= len(options):
        raise typer.BadParameter(
            f"selection must be between 1 and {len(options)}"
        )
    return options[number - 1][0]


def _select_item(
    heading: str,
    values: list[str],
    *,
    default: int = 1,
) -> str:
    if not values:
        raise RuntimeError(f"no values available for {heading}")
    typer.echo("")
    typer.echo(heading)
    typer.echo("")
    for index, value in enumerate(values, start=1):
        typer.echo(f"  {index:4d}. {value}")
    typer.echo("")
    raw = typer.prompt("Select", default=str(default)).strip()
    if raw.isdigit():
        number = int(raw)
        if 1 <= number <= len(values):
            return values[number - 1]
        raise typer.BadParameter(
            f"selection must be between 1 and {len(values)}"
        )
    if raw in values:
        return raw
    raise typer.BadParameter(f"unknown selection: {raw}")


def _select_lunch(
    aosp_root: Path,
) -> LunchTarget:
    """
    Present discovered lunch combinations as a numbered menu.
    """

    discovered = _common_lunch_targets(
        aosp_root
    )

    if discovered:
        choices = [
            target.raw
            for target in discovered
        ]

        choices.append(
            "Other product / release / variant..."
        )

        selected = _select_item(
            "Lunch combinations",
            choices,
            default=1,
        )

        if selected != choices[-1]:
            return LunchTarget.parse(
                selected
            )

    products = _list_products(
        aosp_root
    )

    if not products:
        raise RuntimeError(
            "no buildable products were discovered "
            "under aosp/device"
        )

    product = _select_item(
        "Product",
        products,
        default=1,
    )

    releases = _list_releases(
        aosp_root,
        product,
    )

    if releases:
        release = _select_item(
            f"Release for {product}",
            releases,
            default=1,
        )
    else:
        release = typer.prompt(
            "Release",
            default=(
                _checkout_platform_release(
                    aosp_root
                )
                or "trunk_staging"
            ),
        ).strip()

    variant = _select_item(
        "Build variant",
        list(VALID_VARIANTS),
        default=2,
    )

    return LunchTarget(
        raw=(
            f"{product}-"
            f"{release}-"
            f"{variant}"
        ),
        product=product,
        release=release,
        variant=variant,
    )


def _static_makefiles_for_product(
    aosp_root: Path,
    product_file: Path,
) -> list[Path]:
    """
    Collect static metadata for a selected product.

    Besides ordinary include directives, follow Android product
    inheritance so the planner can resolve the selected product's
    device identity and architecture statically.
    """

    discovered: dict[Path, None] = {}
    queued: set[Path] = set()
    queue: list[Path] = []

    def add_file(path: Path) -> None:
        path = path.resolve()

        if (
            not path.is_file()
            or path in discovered
        ):
            return

        discovered[path] = None

        if path not in queued:
            queue.append(path)
            queued.add(path)

    def add_product_directory(path: Path) -> None:
        parent = path.parent

        if not parent.is_dir():
            return

        for sibling in parent.rglob("*.mk"):
            if sibling.is_file():
                add_file(sibling)

    #
    # Start with all metadata adjacent to the selected product.
    #
    add_product_directory(
        product_file
    )

    include_pattern = re.compile(
        r"^\s*-?include\s+"
        r"([A-Za-z0-9_./+-]+\.mk)"
        r"\s*$",
        re.MULTILINE,
    )

    inherit_pattern = re.compile(
        r"\$\(\s*call\s+"
        r"inherit-product"
        r"(?:-if-exists)?"
        r"\s*,\s*"
        r"([A-Za-z0-9_./+-]+\.mk)"
        r"\s*\)"
    )

    while queue:
        current = queue.pop()

        try:
            text = current.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        active_text = "\n".join(
            line.split("#", 1)[0]
            for line in text.splitlines()
        )

        referenced: set[str] = set()

        for match in include_pattern.finditer(
            active_text
        ):
            referenced.add(
                match.group(1)
            )

        for match in inherit_pattern.finditer(
            active_text
        ):
            referenced.add(
                match.group(1)
            )

        for relative in sorted(referenced):
            included = (
                aosp_root
                / relative
            ).resolve()

            if not included.is_file():
                continue

            add_file(
                included
            )

            #
            # This mirrors the static metadata visibility the planner
            # gets when probing a normal device product directly.
            #
            add_product_directory(
                included
            )

    return sorted(
        discovered
    )


def _static_make_assignments(
    makefiles: list[Path],
) -> dict[str, str]:
    """
    Read simple Make assignments needed by the TreeForge build planner.

    This is metadata discovery only; it is not a Make evaluator.
    """

    wanted = {
        "PRODUCT_DEVICE",
        "TARGET_ARCH",
        "BOARD_PREBUILT_BOOTIMAGE",
    }

    for _, key_field, algorithm_field in AVB_FIELDS:
        wanted.add(key_field)
        wanted.add(algorithm_field)

    assignment = re.compile(
        r"^\s*([A-Za-z0-9_]+)"
        r"\s*(?::=|\?=|=)\s*"
        r"(.+?)\s*$"
    )

    values: dict[str, str] = {}

    for path in makefiles:
        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError:
            continue

        for raw_line in lines:
            line = raw_line.split("#", 1)[0].strip()

            if not line:
                continue

            match = assignment.match(line)

            if match is None:
                continue

            name = match.group(1)

            if name not in wanted:
                continue

            value = match.group(2).strip()

            if "$(" in value or "${" in value:
                continue

            values[name] = value

    return values


def _probe_target(
    aosp_root: Path,
    target: LunchTarget,
) -> TargetProbe:
    """
    Resolve enough target metadata for the interactive build planner
    without invoking lunch, dumpvars, or list_products.

    The actual AOSP build remains responsible for authoritative build
    graph validation once the user confirms the plan.
    """

    product_file = _find_product_makefile(
        aosp_root,
        target.product,
    )

    makefiles = _static_makefiles_for_product(
        aosp_root,
        product_file,
    )

    values = _static_make_assignments(
        makefiles
    )

    device = (
        values.get("PRODUCT_DEVICE", "").strip()
        or product_file.parent.name
    )

    arch = (
        values.get("TARGET_ARCH", "").strip()
        or "unresolved"
    )

    out_root = Path(
        os.environ.get(
            "OUT_DIR",
            str(aosp_root / "out"),
        )
    )

    if not out_root.is_absolute():
        out_root = (
            aosp_root
            / out_root
        ).resolve()

    product_out = (
        out_root
        / "target"
        / "product"
        / device
    )

    values["TREEFORGE_PRODUCT_MAKEFILE"] = str(
        product_file
    )

    values["TREEFORGE_METADATA_FILES"] = ":".join(
        str(path)
        for path in makefiles
    )

    return TargetProbe(
        lunch=target,
        device=device,
        arch=arch,
        product_out=str(product_out),
        values=values,
    )


def _detect_device_tree_signing_default(
    probe: TargetProbe,
) -> tuple[str | None, list[str]]:
    """
    Infer the Device Tree AVB signing provider from its configured key
    paths.

    This identifies the Device Tree default only. treeforge build may
    still override the final artifact signing provider.
    """

    evidence: list[str] = []
    aosp_hits = 0
    treeforge_hits = 0

    for partition, key_field, _ in AVB_FIELDS:
        raw = (
            probe.values
            .get(key_field, "")
            .strip()
        )

        if not raw:
            continue

        normalized = raw.lower()

        evidence.append(
            f"{partition}={raw}"
        )

        if (
            "external/avb/test/data/testkey"
            in normalized
        ):
            aosp_hits += 1
            continue

        if (
            ".treeforge-private" in normalized
            or "device/treeforge/" in normalized
            or "/treeforge/" in normalized
            or normalized.startswith("treeforge/")
        ):
            treeforge_hits += 1

    if (
        treeforge_hits > 0
        and aosp_hits == 0
    ):
        return "treeforge", evidence

    if (
        aosp_hits > 0
        and treeforge_hits == 0
    ):
        return "aosp", evidence

    return None, evidence


def _normalize_choice(
    value: str | None,
    valid: tuple[str, ...],
    option: str,
) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in valid:
        raise typer.BadParameter(
            f"{option} must be one of: {', '.join(valid)}"
        )
    return normalized


def _kernel_root_default() -> Path:
    return TREEFORGE_ROOT.parent / "kernel" / "treeforge_kernel"


def _kernel_profiles(
    kernel_root: Path,
    device: str,
) -> list[str]:
    root = kernel_root / "profiles" / device
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.glob("*.toml"))








def _canonical_kernel_provider(
    value: str,
) -> str:
    return {
        "source": "treeforge-build",
        "treeforge": "treeforge-build",
        "treeforge-output": "treeforge-build",
    }.get(
        value,
        value,
    )




TREEFORGE_KERNEL_PROVIDER_VALUES = frozenset(
    {
        "treeforge-release",
        "treeforge-local",
        "treeforge-build",
    }
)


def _is_treeforge_kernel_provider(
    value: str | None,
) -> bool:
    if value is None:
        return False

    return (
        _canonical_kernel_provider(
            value
        )
        in TREEFORGE_KERNEL_PROVIDER_VALUES
    )



def _treeforge_kernel_build_profiles(
    *,
    kernel_root: Path,
    device: str,
    aosp_release: str | None,
) -> tuple[str, ...]:
    """
    Query the real TreeForge Kernel frontend for usable profiles.

    A profile exists for Android Build only when Kernel exposes at least
    one variant accepted by both build and prebuilts machine paths.
    """

    root = (
        kernel_root
        .expanduser()
        .resolve()
    )

    executable = root / "kernel"

    profiles_root = (
        root
        / "profiles"
        / device
    )

    if not executable.is_file():
        return ()

    if not profiles_root.is_dir():
        return ()

    candidates = tuple(
        sorted(
            {
                path.stem
                for path
                in profiles_root.rglob(
                    "*.toml"
                )
                if path.is_file()
            }
        )
    )

    accepted: list[str] = []

    for profile in candidates:
        try:
            variants = (
                _treeforge_kernel_variants(
                    kernel_root=root,
                    device=device,
                    profile=profile,
                    aosp_release=aosp_release,
                )
            )
        except RuntimeError:
            continue

        if variants:
            accepted.append(
                profile
            )

    return tuple(
        dict.fromkeys(
            accepted
        )
    )




VALID_TREEFORGE_KERNEL_MODES = (
    "aosp",
    "prebuilt",
)




def _kernel_cli_variant_help(
    *,
    kernel_root: Path,
    command: str,
) -> tuple[str, tuple[str, ...]] | None:
    """
    Discover the Kernel machine selector and its advertised values.

    Build supports both the current --source spelling and a possible
    future --variant spelling without owning Kernel's variant policy.
    """

    root = (
        kernel_root
        .expanduser()
        .resolve()
    )

    executable = root / "kernel"

    if not executable.is_file():
        return None

    try:
        completed = subprocess.run(
            [
                str(executable),
                command,
                "--help",
            ],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return None

    if completed.returncode != 0:
        return None

    output = (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    for option in (
        "variant",
        "source",
    ):
        match = re.search(
            rf"--{option}\s+\{{([^}}]+)\}}",
            output,
        )

        if match is None:
            continue

        values = tuple(
            item.strip()
            for item
            in match.group(1).split(",")
            if item.strip()
        )

        if values:
            return (
                f"--{option}",
                values,
            )

    return None


def _treeforge_kernel_variant_contract(
    kernel_root: Path,
) -> dict[str, object]:
    """
    The Android Build side may expose only variants supported by BOTH
    normal Kernel build and AOSP-provider/prebuilts assembly.
    """

    build = _kernel_cli_variant_help(
        kernel_root=kernel_root,
        command="build",
    )

    prebuilts = _kernel_cli_variant_help(
        kernel_root=kernel_root,
        command="prebuilts",
    )

    if build is None:
        raise RuntimeError(
            "TreeForge Kernel build does not expose a "
            "machine-selectable source/variant option"
        )

    if prebuilts is None:
        raise RuntimeError(
            "TreeForge Kernel prebuilts does not expose a "
            "machine-selectable source/variant option"
        )

    build_option, build_values = build
    prebuilts_option, prebuilts_values = prebuilts

    variants = tuple(
        value
        for value in build_values
        if value in prebuilts_values
    )

    if not variants:
        raise RuntimeError(
            "TreeForge Kernel build and prebuilts expose no "
            "common kernel variant"
        )

    return {
        "build_option": build_option,
        "prebuilts_option": prebuilts_option,
        "variants": variants,
    }


def _treeforge_kernel_variants(
    *,
    kernel_root: Path,
    device: str,
    profile: str,
    aosp_release: str | None,
) -> tuple[str, ...]:
    """
    Confirm advertised variants against both Kernel machine interfaces.

    Every command is plan-only. No kernel build, packaging, ADB,
    Fastboot, flash, or temporary boot is allowed here.
    """

    root = (
        kernel_root
        .expanduser()
        .resolve()
    )

    executable = root / "kernel"

    contract = (
        _treeforge_kernel_variant_contract(
            root
        )
    )

    build_option = str(
        contract["build_option"]
    )

    prebuilts_option = str(
        contract["prebuilts_option"]
    )

    advertised = tuple(
        str(value)
        for value
        in contract["variants"]
    )

    accepted: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="treeforge-kernel-capability-"
    ) as temp:
        probe_output = (
            Path(temp)
            / "provider"
        )

        for variant in advertised:
            build_command = [
                str(executable),
                "build",
                "--device",
                device,
                "--profile",
                profile,
                build_option,
                variant,
                "--avb-signing",
                "none",
                "--after-build",
                "none",
                "--non-interactive",
                "--plan-only",
                "--json",
            ]

            prebuilt_command = [
                str(executable),
                "prebuilts",
                "--device",
                device,
                "--profile",
                profile,
                prebuilts_option,
                variant,
                "--output",
                str(probe_output),
                "--plan-only",
                "--json",
            ]

            valid = True

            for command in (
                build_command,
                prebuilt_command,
            ):
                try:
                    completed = subprocess.run(
                        command,
                        cwd=str(root),
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                except (
                    OSError,
                    subprocess.TimeoutExpired,
                ):
                    valid = False
                    break

                if completed.returncode != 0:
                    valid = False
                    break

                try:
                    payload = json.loads(
                        completed.stdout
                    )
                except json.JSONDecodeError:
                    valid = False
                    break

                if not isinstance(
                    payload,
                    dict,
                ):
                    valid = False
                    break

                if (
                    str(
                        payload.get(
                            "device",
                            "",
                        )
                    ).strip()
                    != device
                ):
                    valid = False
                    break

                returned_profile = str(
                    payload.get(
                        "profile",
                        "",
                    )
                ).strip()

                if (
                    returned_profile
                    and returned_profile
                    != profile
                ):
                    valid = False
                    break

                returned_release = str(
                    payload.get(
                        "aosp_release",
                        "",
                    )
                ).strip()

                if (
                    aosp_release
                    and returned_release
                    and returned_release
                    != aosp_release
                ):
                    valid = False
                    break

                returned_variant = str(
                    payload.get(
                        "variant",
                        payload.get(
                            "source_mode",
                            "",
                        ),
                    )
                ).strip()

                if (
                    returned_variant
                    and returned_variant
                    != variant
                ):
                    valid = False
                    break

            if valid:
                accepted.append(
                    variant
                )

    return tuple(
        dict.fromkeys(
            accepted
        )
    )


def _kernel_bundle_variant(
    bundle: dict[str, object],
) -> str | None:
    for key in (
        "variant",
        "source_mode",
    ):
        value = bundle.get(key)

        if (
            isinstance(value, str)
            and value.strip()
        ):
            return value.strip()

    return None



TREEFORGE_KERNEL_INPUT_VALUES = (
    "build",
    "local",
    "release",
)


def _treeforge_kernel_input_menu() -> tuple[tuple[str, str], ...]:
    return (
        (
            "build",
            "Build / assemble TreeForge kernel provider now",
        ),
        (
            "local",
            "Existing local TreeForge kernel provider",
        ),
        (
            "release",
            "Published TreeForge kernel GitHub release",
        ),
        (
            "cancel",
            "Cancel Android build",
        ),
    )


def _treeforge_kernel_variant_menu(
    variants: tuple[str, ...],
) -> tuple[tuple[str, str], ...]:
    labels = {
        "modified": "Modified TreeForge kernel [recommended]",
        "diagnostic": (
            "Diagnostic TreeForge kernel — bring-up instrumentation"
        ),
        "baseline": "Baseline / stock kernel reproduction",
        "stock": "Stock kernel",
    }

    values = [
        (
            variant,
            labels.get(
                variant,
                variant.replace("_", " ").title(),
            ),
        )
        for variant in variants
    ]

    values.append(
        (
            "cancel",
            "Cancel Android build",
        )
    )

    return tuple(values)


def _treeforge_kernel_mode_menu() -> tuple[tuple[str, str], ...]:
    return (
        (
            "aosp",
            "AOSP-built images [recommended] — temporarily project "
            "TreeForge kernel inputs into the canonical AOSP kernel "
            "location and let Android construct every final image",
        ),
        (
            "prebuilt",
            "TreeForge prebuilt images — consume the coherent packaged "
            "TreeForge kernel image family during the Android build",
        ),
        (
            "cancel",
            "Cancel Android build",
        ),
    )




def _kernel_provider_menu(
    *,
    treeforge_available: bool,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Present TreeForge Kernel as one user-facing provider.

    release/local/build remain internal provider mechanisms. The
    integration and artifact-source choices are resolved only after
    TreeForge Kernel is selected.
    """

    values: list[
        tuple[str, str]
    ] = []

    if treeforge_available:
        values.append(
            (
                "treeforge-build",
                "TreeForge Kernel",
            )
        )

    values.extend(
        [
            (
                "aosp",
                "AOSP kernel — use the selected "
                "product's kernel provider",
            ),
            (
                "cancel",
                "Cancel Android build",
            ),
        ]
    )

    return tuple(values)





def _require_treeforge_kernel_capability(
    *,
    provider: str,
    device: str,
    aosp_release: str | None,
    profiles: tuple[str, ...],
) -> None:
    """
    Never silently accept a TreeForge Kernel against an unknown or
    incompatible Android source-platform identity.
    """

    if not _is_treeforge_kernel_provider(
        provider
    ):
        return

    if not aosp_release:
        raise typer.BadParameter(
            "TreeForge Kernel requires an exact Android "
            "platform/source tag for provider compatibility, "
            "but the active AOSP checkout identity could not "
            "be determined from Repo metadata."
        )

    if profiles:
        return

    raise typer.BadParameter(
        "TreeForge Kernel is unavailable for "
        f"device={device!r}, "
        "android_platform="
        f"{aosp_release!r}. "
        "No compatible profile is accepted by "
        "./kernel build."
    )





def _kernel_provider_store_root() -> Path:
    return (
        TREEFORGE_ROOT
        / "treeforge"
        / "data"
        / "kernel"
        / "providers"
    ).resolve()


def _kernel_provider_source_roots(
    provider: str,
) -> tuple[Path, ...]:
    root = _kernel_provider_store_root()

    if provider == "treeforge-local":
        return (
            root / "local",
            root / "github",
        )

    if provider == "treeforge-release":
        return (
            root / "github",
        )

    raise ValueError(
        f"provider has no TreeForge bundle store: {provider}"
    )


def _kernel_release_cache_root() -> Path:
    return (
        TREEFORGE_ROOT
        / "treeforge"
        / "data"
        / "kernel"
        / "cache"
        / "github"
    ).resolve()


def _github_release_command(
    *arguments: str,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("gh")

    if executable is None:
        raise RuntimeError(
            "GitHub CLI (gh) is required for "
            "TreeForge kernel release providers"
        )

    completed = subprocess.run(
        [
            executable,
            *arguments,
        ],
        text=True,
        stdout=(
            subprocess.PIPE
            if capture
            else None
        ),
        stderr=subprocess.PIPE,
        check=False,
    )

    if completed.returncode != 0:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown GitHub CLI failure"
        )

        raise RuntimeError(
            "GitHub kernel provider operation failed: "
            f"{detail}"
        )

    return completed


def _github_kernel_release_catalog(
    *,
    device: str,
) -> tuple[dict[str, object], ...]:
    completed = _github_release_command(
        "release",
        "list",
        "--repo",
        TREEFORGE_KERNEL_RELEASE_REPOSITORY,
        "--limit",
        "100",
        "--json",
        (
            "tagName,name,isDraft,"
            "isPrerelease,publishedAt"
        ),
    )

    try:
        payload = json.loads(
            completed.stdout
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GitHub release catalog returned "
            "invalid JSON"
        ) from exc

    if not isinstance(
        payload,
        list,
    ):
        raise RuntimeError(
            "GitHub release catalog must be a list"
        )

    prefix = f"{device}-"

    values: list[dict[str, object]] = []

    for entry in payload:
        if not isinstance(
            entry,
            dict,
        ):
            continue

        if entry.get("isDraft"):
            continue

        tag = entry.get(
            "tagName"
        )

        if (
            not isinstance(
                tag,
                str,
            )
            or not tag.startswith(prefix)
        ):
            continue

        values.append(entry)

    return tuple(values)


def _select_github_kernel_release(
    *,
    device: str,
    explicit_tag: str | None,
    non_interactive: bool,
) -> str:
    if explicit_tag is not None:
        tag = explicit_tag.strip()

        if not tag:
            raise RuntimeError(
                "kernel release tag cannot be empty"
            )

        return tag

    releases = (
        _github_kernel_release_catalog(
            device=device,
        )
    )

    if not releases:
        raise RuntimeError(
            "no compatible TreeForge kernel "
            "GitHub releases were found for "
            f"{device}"
        )

    if non_interactive:
        raise RuntimeError(
            "--kernel-release-tag is required "
            "with --kernel treeforge-release "
            "in non-interactive mode"
        )

    selected = _select_numbered(
        "TreeForge kernel GitHub releases",
        [
            (
                str(entry["tagName"]),
                (
                    str(entry["tagName"])
                    + (
                        " [prerelease]"
                        if entry.get(
                            "isPrerelease"
                        )
                        else ""
                    )
                    + (
                        " — "
                        + str(entry["name"])
                        if entry.get("name")
                        else ""
                    )
                ),
            )
            for entry in releases
        ],
        1,
    )

    return str(selected)


def _github_release_assets(
    *,
    tag: str,
) -> tuple[str, ...]:
    completed = _github_release_command(
        "release",
        "view",
        tag,
        "--repo",
        TREEFORGE_KERNEL_RELEASE_REPOSITORY,
        "--json",
        "assets",
    )

    try:
        payload = json.loads(
            completed.stdout
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GitHub release asset query returned "
            "invalid JSON"
        ) from exc

    assets = payload.get(
        "assets"
    )

    if not isinstance(
        assets,
        list,
    ):
        raise RuntimeError(
            "GitHub release has no asset list"
        )

    names: list[str] = []

    for entry in assets:
        if not isinstance(
            entry,
            dict,
        ):
            continue

        name = entry.get(
            "name"
        )

        if isinstance(
            name,
            str,
        ):
            names.append(name)

    return tuple(names)


def _download_github_release_asset(
    *,
    tag: str,
    asset: str,
    destination: Path,
) -> Path:
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = destination / asset

    if target.is_file():
        return target

    _github_release_command(
        "release",
        "download",
        tag,
        "--repo",
        TREEFORGE_KERNEL_RELEASE_REPOSITORY,
        "--pattern",
        asset,
        "--dir",
        str(destination),
        capture=False,
    )

    if not target.is_file():
        raise RuntimeError(
            "GitHub release download completed "
            "without expected asset: "
            f"{target}"
        )

    return target


def _release_checksum(
    *,
    checksum_file: Path,
    asset: str,
) -> str:
    for line in checksum_file.read_text().splitlines():
        fields = line.strip().split()

        if len(fields) < 2:
            continue

        digest = fields[0]
        name = fields[-1]

        if name == asset:
            if (
                len(digest) != 64
                or any(
                    character
                    not in "0123456789abcdef"
                    for character in digest
                )
            ):
                raise RuntimeError(
                    "invalid SHA-256 in release "
                    f"checksum file for {asset}"
                )

            return digest

    raise RuntimeError(
        "release checksum file has no digest "
        f"for {asset}"
    )


def _safe_extract_kernel_provider(
    *,
    archive: Path,
    destination: Path,
) -> Path:
    if destination.exists():
        shutil.rmtree(
            destination
        )

    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    root = destination.resolve()

    with tarfile.open(
        archive,
        "r:gz",
    ) as handle:
        members = handle.getmembers()

        for member in members:
            target = (
                root
                / member.name
            ).resolve()

            try:
                target.relative_to(
                    root
                )
            except ValueError as exc:
                raise RuntimeError(
                    "kernel provider archive contains "
                    "an unsafe path: "
                    f"{member.name}"
                ) from exc

        handle.extractall(
            root,
            filter="data",
        )

    provider = root / "provider"

    if not (
        provider
        / "manifest.json"
    ).is_file():
        raise RuntimeError(
            "kernel provider archive did not "
            "contain provider/manifest.json"
        )

    return provider


def _acquire_github_kernel_provider(
    *,
    tag: str,
    device: str,
) -> Path:
    provider_root = (
        _kernel_provider_store_root()
        / "github"
        / tag
    )

    installed_manifest = (
        provider_root
        / "manifest.json"
    )

    # A validated installed provider is the cache hit.
    if installed_manifest.is_file():
        bundle = (
            _load_kernel_provider_bundle(
                manifest_path=installed_manifest,
                device=device,
            )
        )

        return Path(
            bundle["manifest"]
        )

    assets = _github_release_assets(
        tag=tag,
    )

    provider_archives = [
        name
        for name in assets
        if (
            name.startswith(
                "treeforge-kernel-provider-"
            )
            and name.endswith(
                ".tar.gz"
            )
        )
    ]

    if len(provider_archives) != 1:
        raise RuntimeError(
            "TreeForge kernel release must contain "
            "exactly one provider archive; found "
            f"{len(provider_archives)}"
        )

    archive_name = (
        provider_archives[0]
    )

    for required in (
        "SHA256SUMS.release",
        "provenance.json",
    ):
        if required not in assets:
            raise RuntimeError(
                "TreeForge kernel release is missing "
                f"required asset: {required}"
            )

    cache = (
        _kernel_release_cache_root()
        / tag
    )

    archive = (
        _download_github_release_asset(
            tag=tag,
            asset=archive_name,
            destination=cache,
        )
    )

    checksums = (
        _download_github_release_asset(
            tag=tag,
            asset="SHA256SUMS.release",
            destination=cache,
        )
    )

    provenance = (
        _download_github_release_asset(
            tag=tag,
            asset="provenance.json",
            destination=cache,
        )
    )

    expected_sha = _release_checksum(
        checksum_file=checksums,
        asset=archive_name,
    )

    actual_sha = _sha256_file(
        archive
    )

    if actual_sha != expected_sha:
        raise RuntimeError(
            "downloaded kernel provider archive "
            "failed SHA-256 verification: "
            f"expected {expected_sha}, "
            f"found {actual_sha}"
        )

    extraction = (
        cache
        / "extracted"
    )

    extracted_provider = (
        _safe_extract_kernel_provider(
            archive=archive,
            destination=extraction,
        )
    )

    extracted_manifest = (
        extracted_provider
        / "manifest.json"
    )

    # Validate every required provider artifact
    # before publishing it into the local provider store.
    _load_kernel_provider_bundle(
        manifest_path=extracted_manifest,
        device=device,
    )

    temporary_install = (
        provider_root.parent
        / (
            "."
            + provider_root.name
            + ".installing"
        )
    )

    if temporary_install.exists():
        shutil.rmtree(
            temporary_install
        )

    temporary_install.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copytree(
        extracted_provider,
        temporary_install,
    )

    shutil.copy2(
        provenance,
        temporary_install
        / "provenance.json",
    )

    shutil.copy2(
        checksums,
        temporary_install
        / "SHA256SUMS.release",
    )

    if provider_root.exists():
        shutil.rmtree(
            provider_root
        )

    temporary_install.rename(
        provider_root
    )

    installed_manifest = (
        provider_root
        / "manifest.json"
    )

    bundle = (
        _load_kernel_provider_bundle(
            manifest_path=installed_manifest,
            device=device,
        )
    )

    return Path(
        bundle["manifest"]
    )


def _kernel_provider_candidates(
    *,
    provider: str,
    device: str,
) -> tuple[Path, ...]:
    roots = _kernel_provider_source_roots(
        provider
    )

    values: list[Path] = []

    for root in roots:
        if not root.is_dir():
            continue

        for candidate in root.rglob(
            "manifest.json"
        ):
            if not candidate.is_file():
                continue

            try:
                payload = json.loads(
                    candidate.read_text()
                )
            except (
                OSError,
                json.JSONDecodeError,
            ):
                continue

            if payload.get("device") != device:
                continue

            values.append(
                candidate.resolve()
            )

    return tuple(
        sorted(
            set(values),
            key=lambda item: (
                -item.stat().st_mtime_ns,
                item.as_posix(),
            ),
        )
    )


def _sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def _load_kernel_provider_bundle(
    *,
    manifest_path: Path,
    device: str,
) -> dict[str, object]:
    manifest = (
        manifest_path
        .expanduser()
        .resolve()
    )

    if not manifest.is_file():
        raise RuntimeError(
            "kernel provider manifest is unavailable: "
            f"{manifest}"
        )

    try:
        payload = json.loads(
            manifest.read_text()
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "kernel provider manifest is not valid JSON: "
            f"{manifest}"
        ) from exc

    if payload.get("schema") != 1:
        raise RuntimeError(
            "unsupported kernel provider manifest schema: "
            f"{payload.get('schema')!r}"
        )

    if payload.get("device") != device:
        raise RuntimeError(
            "kernel provider device mismatch: "
            f"expected {device}, "
            f"found {payload.get('device')!r}"
        )

    generation = payload.get(
        "generation"
    )

    if (
        not isinstance(
            generation,
            str,
        )
        or not generation
    ):
        raise RuntimeError(
            "kernel provider has no generation identity"
        )

    artifacts = payload.get(
        "artifacts"
    )

    if not isinstance(
        artifacts,
        dict,
    ):
        raise RuntimeError(
            "kernel provider artifacts must be an object"
        )

    root = manifest.parent

    for name in (
        KERNEL_PROVIDER_REQUIRED_ARTIFACTS
    ):
        entry = artifacts.get(name)

        if not isinstance(
            entry,
            dict,
        ):
            raise RuntimeError(
                "kernel provider is missing required "
                f"artifact: {name}"
            )

        relative = entry.get(
            "path"
        )

        expected_size = entry.get(
            "size"
        )

        expected_sha = entry.get(
            "sha256"
        )

        if (
            not isinstance(
                relative,
                str,
            )
            or not relative
        ):
            raise RuntimeError(
                "kernel provider artifact has invalid "
                f"path: {name}"
            )

        artifact = (
            root
            / relative
        ).resolve()

        try:
            artifact.relative_to(
                root.resolve()
            )
        except ValueError as exc:
            raise RuntimeError(
                "kernel provider artifact escapes "
                f"provider root: {name}"
            ) from exc

        if not artifact.is_file():
            raise RuntimeError(
                "kernel provider artifact is unavailable: "
                f"{artifact}"
            )

        actual_size = (
            artifact.stat().st_size
        )

        if actual_size != expected_size:
            raise RuntimeError(
                "kernel provider artifact size mismatch: "
                f"{name}: expected {expected_size}, "
                f"found {actual_size}"
            )

        actual_sha = _sha256_file(
            artifact
        )

        if actual_sha != expected_sha:
            raise RuntimeError(
                "kernel provider artifact SHA-256 mismatch: "
                f"{name}: expected {expected_sha}, "
                f"found {actual_sha}"
            )

    return {
        "manifest": manifest,
        "root": root,
        "generation": generation,
        "android_profile": payload.get(
            "android_profile"
        ),
        "aosp_release": payload.get(
            "aosp_release"
        ),
        "source_mode": payload.get(
            "source_mode"
        ),
        "artifacts": artifacts,
    }


def _select_kernel_provider_bundle(
    *,
    provider: str,
    device: str,
    explicit: Path | None,
    non_interactive: bool,
) -> Path:
    if explicit is not None:
        candidate = (
            explicit
            .expanduser()
            .resolve()
        )

        if candidate.is_dir():
            candidate = (
                candidate
                / "manifest.json"
            )

        _load_kernel_provider_bundle(
            manifest_path=candidate,
            device=device,
        )

        return candidate

    candidates = (
        _kernel_provider_candidates(
            provider=provider,
            device=device,
        )
    )

    if not candidates:
        raise RuntimeError(
            "no compatible "
            f"{provider} kernel provider "
            f"was found for {device}"
        )

    if len(candidates) == 1:
        _load_kernel_provider_bundle(
            manifest_path=candidates[0],
            device=device,
        )
        return candidates[0]

    if non_interactive:
        raise RuntimeError(
            "multiple compatible kernel providers "
            "are available; use "
            "--kernel-provider-path to select one"
        )

    store_root = (
        _kernel_provider_store_root()
    )

    selected = _select_numbered(
        "TreeForge kernel providers",
        [
            (
                candidate.as_posix(),
                candidate.parent
                .relative_to(
                    store_root
                )
                .as_posix(),
            )
            for candidate in candidates
        ],
        1,
    )

    result = Path(
        selected
    ).resolve()

    _load_kernel_provider_bundle(
        manifest_path=result,
        device=device,
    )

    return result


def _factory_boot_candidates(
    *,
    repository_root: Path,
) -> tuple[Path, ...]:
    source_root = (
        repository_root
        / "output"
        / "parsing"
        / "images"
        / "sources"
    )

    if not source_root.is_dir():
        return ()

    return tuple(
        sorted(
            (
                candidate.resolve()
                for candidate
                in source_root.glob("*-boot.img")
                if candidate.is_file()
            ),
            key=lambda item:
            item.as_posix(),
        )
    )





def _select_factory_boot(
    *,
    repository_root: Path,
    non_interactive: bool,
) -> Path:
    """
    Consume the canonical factory boot.img already produced by Parsing.

    Build does not reopen the factory archive, parse reports/state,
    reconstruct provenance, or revalidate Parsing's evidence.
    """

    candidates = _factory_boot_candidates(
        repository_root=repository_root,
    )

    if not candidates:
        raise RuntimeError(
            "no canonical factory boot.img is "
            "available from Parsing"
        )

    if len(candidates) == 1:
        return candidates[0]

    if non_interactive:
        raise RuntimeError(
            "multiple canonical factory boot.img "
            "artifacts are available; selection "
            "is ambiguous in non-interactive mode"
        )

    selected = _select_numbered(
        "Factory boot images",
        [
            (
                candidate.as_posix(),
                candidate.name,
            )
            for candidate in candidates
        ],
        1,
    )

    return Path(selected).resolve()


def _validate_aosp_kernel_provider(
    *,
    aosp_root: Path,
    probe: TargetProbe,
    target: LunchTarget,
) -> Path:
    root = (
        aosp_root
        .expanduser()
        .resolve()
    )

    envsetup = (
        root
        / "build"
        / "envsetup.sh"
    )

    if not envsetup.is_file():
        raise RuntimeError(
            "AOSP envsetup.sh is unavailable: "
            f"{envsetup}"
        )

    environment = os.environ.copy()

    environment[
        "TREEFORGE_BUILD_LUNCH"
    ] = target.raw

    script = (
        'source build/envsetup.sh >/dev/null '
        '&& lunch "$TREEFORGE_BUILD_LUNCH" '
        '>/dev/null '
        '&& get_build_var TARGET_KERNEL_DIR'
    )

    completed = subprocess.run(
        [
            "bash",
            "-c",
            script,
        ],
        cwd=str(root),
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if completed.returncode != 0:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "unknown AOSP build-var error"
        )

        raise RuntimeError(
            "unable to resolve AOSP "
            "TARGET_KERNEL_DIR for "
            f"{target.raw}: {detail}"
        )

    values = [
        line.strip()
        for line
        in completed.stdout.splitlines()
        if line.strip()
    ]

    if not values:
        raise RuntimeError(
            "selected AOSP product does not "
            "resolve TARGET_KERNEL_DIR"
        )

    kernel_dir_value = values[-1]

    kernel_dir = Path(
        kernel_dir_value
    )

    if not kernel_dir.is_absolute():
        kernel_dir = (
            root
            / kernel_dir
        )

    kernel_dir = (
        kernel_dir.resolve()
    )

    if not kernel_dir.is_dir():
        raise RuntimeError(
            "selected AOSP kernel prebuilt "
            "directory is unavailable: "
            f"{kernel_dir}"
        )

    #
    # Google's GS201 configuration prefers a complete prebuilt boot.img
    # when available. Otherwise it consumes the kernel payload from
    # TARGET_KERNEL_DIR and builds boot.img itself.
    #
    candidates = (
        kernel_dir / "boot.img",
        kernel_dir / "Image.lz4",
        kernel_dir / "Image",
        kernel_dir / "kernel",
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise RuntimeError(
        "selected AOSP TARGET_KERNEL_DIR "
        "contains no recognized kernel/boot "
        "prebuilt: "
        f"{kernel_dir}"
    )



def _treeforge_prebuilt_boot(
    *,
    aosp_root: Path,
    device: str,
    explicit: Path | None,
) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()

    candidates = [
        (
            aosp_root
            / "device"
            / "treeforge"
            / device
            / "boot"
            / "prebuilt"
            / "boot.img"
        ),
        (
            TREEFORGE_ROOT
            / "output"
            / "device-tree"
            / "device"
            / "treeforge"
            / device
            / "boot"
            / "prebuilt"
            / "boot.img"
        ),
        (
            TREEFORGE_ROOT
            / "output"
            / "device-tree"
            / "device"
            / "google"
            / device
            / "boot"
            / "prebuilt"
            / "boot.img"
        ),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise RuntimeError(
        "no TreeForge-published prebuilt boot.img was found; "
        "use --boot-image PATH or run the Device Tree/Boot Image stage first"
    )



TREEFORGE_AOSP_KERNEL_REQUIRED_ARTIFACTS = (
    "Image.lz4",
    "dtbo.img",
    "fips140.ko",
    "vendor_kernel_boot.modules.load",
    "vendor_dlkm.modules.load",
    "vendor_dlkm.modules.blocklist",
    "system_dlkm.modules.load",
    "system_dlkm.modules.blocklist",
)


TREEFORGE_AOSP_KERNEL_SUPPRESSED_IMAGES = frozenset(
    {
        "boot.img",
        "boot-user.img",
        "vendor_kernel_boot.img",
        "vendor_dlkm.img",
        "system_dlkm.img",
    }
)


def _load_treeforge_aosp_kernel_provider(
    *,
    manifest_path: Path,
    device: str,
    profile: str,
    aosp_release: str | None,
) -> dict[str, object]:
    """
    Validate the complete TreeForge AOSP kernel-provider contract.

    This contract belongs only to AOSP composition. Normal
    ``./kernel build`` is not required to provide fips140.ko or the
    complete AOSP module population.
    """

    manifest = (
        manifest_path
        .expanduser()
        .resolve()
    )

    if not manifest.is_file():
        raise RuntimeError(
            "TreeForge AOSP kernel provider manifest "
            f"is unavailable: {manifest}"
        )

    try:
        payload = json.loads(
            manifest.read_text(
                encoding="utf-8",
            )
        )
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "TreeForge AOSP kernel provider manifest "
            f"is not valid JSON: {manifest}"
        ) from exc

    if payload.get("schema") != 1:
        raise RuntimeError(
            "unsupported TreeForge AOSP kernel provider "
            f"schema: {payload.get('schema')!r}"
        )

    if (
        payload.get("contract")
        != "treeforge-kernel-provider-v2"
    ):
        raise RuntimeError(
            "TreeForge AOSP integration requires "
            "treeforge-kernel-provider-v2; found "
            f"{payload.get('contract')!r}"
        )

    if payload.get("device") != device:
        raise RuntimeError(
            "TreeForge AOSP kernel provider device "
            f"mismatch: expected {device!r}, found "
            f"{payload.get('device')!r}"
        )

    provider_profile = payload.get(
        "android_profile"
    )

    if provider_profile != profile:
        raise RuntimeError(
            "TreeForge AOSP kernel provider profile "
            f"mismatch: expected {profile!r}, found "
            f"{provider_profile!r}"
        )

    provider_release = payload.get(
        "aosp_release"
    )

    if (
        aosp_release
        and provider_release != aosp_release
    ):
        raise RuntimeError(
            "TreeForge AOSP kernel provider Android "
            f"release mismatch: expected {aosp_release!r}, "
            f"found {provider_release!r}"
        )

    generation = payload.get(
        "generation"
    )

    if (
        not isinstance(
            generation,
            str,
        )
        or not generation
    ):
        raise RuntimeError(
            "TreeForge AOSP kernel provider has no "
            "generation identity"
        )

    artifacts = payload.get(
        "artifacts"
    )

    if not isinstance(
        artifacts,
        dict,
    ):
        raise RuntimeError(
            "TreeForge AOSP kernel provider artifacts "
            "must be an object"
        )

    root = manifest.parent.resolve()

    validated: dict[
        str,
        Path,
    ] = {}

    for name, entry in artifacts.items():
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(entry, dict)
        ):
            raise RuntimeError(
                "TreeForge AOSP kernel provider has "
                "an invalid artifact entry"
            )

        relative = entry.get(
            "path"
        )
        expected_size = entry.get(
            "size"
        )
        expected_sha = entry.get(
            "sha256"
        )

        if (
            not isinstance(relative, str)
            or not relative
        ):
            raise RuntimeError(
                "TreeForge AOSP kernel artifact has "
                f"an invalid path: {name}"
            )

        if (
            not isinstance(expected_size, int)
            or expected_size < 0
        ):
            raise RuntimeError(
                "TreeForge AOSP kernel artifact has "
                f"an invalid size: {name}"
            )

        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
        ):
            raise RuntimeError(
                "TreeForge AOSP kernel artifact has "
                f"an invalid SHA-256: {name}"
            )

        artifact = (
            root
            / relative
        ).resolve()

        try:
            artifact.relative_to(
                root
            )
        except ValueError as exc:
            raise RuntimeError(
                "TreeForge AOSP kernel artifact escapes "
                f"provider root: {name}"
            ) from exc

        if not artifact.is_file():
            raise RuntimeError(
                "TreeForge AOSP kernel artifact is "
                f"unavailable: {artifact}"
            )

        actual_size = (
            artifact.stat().st_size
        )

        if actual_size != expected_size:
            raise RuntimeError(
                "TreeForge AOSP kernel artifact size "
                f"mismatch for {name}: expected "
                f"{expected_size}, found {actual_size}"
            )

        actual_sha = _sha256_file(
            artifact
        )

        if actual_sha != expected_sha:
            raise RuntimeError(
                "TreeForge AOSP kernel artifact SHA-256 "
                f"mismatch for {name}: expected "
                f"{expected_sha}, found {actual_sha}"
            )

        validated[name] = artifact

    for required in (
        TREEFORGE_AOSP_KERNEL_REQUIRED_ARTIFACTS
    ):
        if required not in validated:
            raise RuntimeError(
                "TreeForge AOSP kernel provider is "
                f"incomplete: missing {required}"
            )

    #
    # FIPS is deliberately enforced HERE, not by ordinary ./kernel build.
    #
    if "fips140.ko" not in validated:
        raise RuntimeError(
            "TreeForge AOSP kernel provider is missing "
            "the separately assembled fips140.ko"
        )

    module_names = tuple(
        sorted(
            name
            for name in validated
            if name.endswith(".ko")
        )
    )

    declared_module_count = payload.get(
        "kernel_module_count"
    )

    if (
        not isinstance(
            declared_module_count,
            int,
        )
        or declared_module_count <= 0
    ):
        raise RuntimeError(
            "TreeForge AOSP kernel provider has no valid "
            "kernel_module_count"
        )

    if (
        len(module_names)
        != declared_module_count
    ):
        raise RuntimeError(
            "TreeForge AOSP kernel provider module count "
            f"mismatch: manifest declares "
            f"{declared_module_count}, artifact map contains "
            f"{len(module_names)}"
        )

    return {
        "manifest": manifest,
        "root": root,
        "generation": generation,
        "android_profile": provider_profile,
        "aosp_release": provider_release,
        "source_mode": payload.get(
            "source_mode"
        ),
        "kernel_module_count": (
            declared_module_count
        ),
        "artifacts": artifacts,
        "validated_artifacts": validated,
    }



def _build_treeforge_aosp_kernel_provider(
    *,
    kernel_root: Path,
    device: str,
    profile: str,
    aosp_release: str | None,
    variant: str = "modified",
    variant_option: str | None = None,
) -> dict[str, object]:
    """
    Have Kernel assemble the complete AOSP provider for one variant.

    Provider-only work such as FIPS remains owned by Kernel prebuilts.
    Build consumes and validates the completed provider contract.
    """

    root = (
        kernel_root
        .expanduser()
        .resolve()
    )

    executable = root / "kernel"

    if not executable.is_file():
        raise RuntimeError(
            "TreeForge kernel CLI was not found: "
            f"{executable}"
        )

    if variant_option is None:
        contract = (
            _treeforge_kernel_variant_contract(
                root
            )
        )

        variant_option = str(
            contract[
                "prebuilts_option"
            ]
        )

    if variant_option not in (
        "--source",
        "--variant",
    ):
        raise RuntimeError(
            "unsupported TreeForge Kernel variant selector: "
            f"{variant_option!r}"
        )

    safe_variant = re.sub(
        r"[^A-Za-z0-9_.+-]",
        "_",
        variant,
    )

    provider_base = (
        root
        / "out"
        / "treeforge-aosp-provider"
        / device
        / profile
        / safe_variant
    )

    provider_base.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = (
        provider_base
        / (
            ".building-"
            + str(os.getpid())
        )
    )

    if temporary.exists():
        shutil.rmtree(
            temporary
        )

    command = [
        str(executable),
        "prebuilts",
        "--device",
        device,
        "--profile",
        profile,
        variant_option,
        variant,
        "--output",
        str(temporary),
    ]

    typer.echo("")
    typer.echo(
        "Building TreeForge AOSP kernel provider..."
    )
    typer.echo(
        f"  Kernel variant:     {variant}"
    )
    typer.echo(
        "  Kernel/device dist: normal TreeForge kernel build contract"
    )
    typer.echo(
        "  AOSP-only FIPS:     provider composition contract"
    )

    try:
        subprocess.run(
            command,
            cwd=str(root),
            text=True,
            check=True,
        )

        temporary_bundle = (
            _load_treeforge_aosp_kernel_provider(
                manifest_path=(
                    temporary
                    / "manifest.json"
                ),
                device=device,
                profile=profile,
                aosp_release=aosp_release,
            )
        )

        returned_variant = (
            _kernel_bundle_variant(
                temporary_bundle
            )
        )

        if returned_variant != variant:
            raise RuntimeError(
                "TreeForge kernel provider variant mismatch: "
                f"requested {variant!r}, "
                f"provider reports {returned_variant!r}"
            )

        generation = str(
            temporary_bundle[
                "generation"
            ]
        )

        final = (
            provider_base
            / generation
        )

        if final.exists():
            shutil.rmtree(
                temporary
            )
        else:
            temporary.rename(
                final
            )

        result = (
            _load_treeforge_aosp_kernel_provider(
                manifest_path=(
                    final
                    / "manifest.json"
                ),
                device=device,
                profile=profile,
                aosp_release=aosp_release,
            )
        )

        promoted_variant = (
            _kernel_bundle_variant(
                result
            )
        )

        if promoted_variant != variant:
            raise RuntimeError(
                "promoted TreeForge kernel provider "
                "variant mismatch: "
                f"requested {variant!r}, "
                f"provider reports {promoted_variant!r}"
            )

        return result

    except BaseException:
        if temporary.exists():
            shutil.rmtree(
                temporary,
                ignore_errors=True,
            )

        raise





def _remove_treeforge_path(
    path: Path,
) -> None:
    if (
        path.is_symlink()
        or path.is_file()
    ):
        path.unlink(
            missing_ok=True,
        )
        return

    if path.exists():
        shutil.rmtree(
            path,
        )


def _resolve_aosp_target_kernel_dir(
    *,
    aosp_root: Path,
    target: LunchTarget,
) -> Path:
    body = "\n".join(
        [
            "set -e",
            "source build/envsetup.sh >/dev/null",
            f"lunch {shlex.quote(target.raw)} >/dev/null",
            "get_build_var TARGET_KERNEL_DIR",
        ]
    )

    output = (
        _bash_capture(
            aosp_root,
            body,
        )
        .strip()
        .splitlines()
    )

    if not output:
        raise RuntimeError(
            "AOSP did not resolve TARGET_KERNEL_DIR"
        )

    raw = output[-1].strip()

    if not raw:
        raise RuntimeError(
            "AOSP resolved an empty TARGET_KERNEL_DIR"
        )

    result = Path(
        raw
    )

    if not result.is_absolute():
        result = (
            aosp_root
            / result
        )

    result = result.resolve()

    try:
        result.relative_to(
            aosp_root.resolve()
        )

    except ValueError as exc:
        raise RuntimeError(
            "transitional TreeForge AOSP kernel composition "
            "requires TARGET_KERNEL_DIR to live inside the "
            f"AOSP checkout; found {result}"
        ) from exc

    return result


def _treeforge_google_vendor_board_config(
    *,
    aosp_root: Path,
    device: str,
) -> Path:
    candidates = (
        (
            aosp_root
            / "vendor"
            / "google_devices"
            / device
            / "proprietary"
            / "BoardConfigVendor.mk"
        ),
        (
            aosp_root
            / "vendor"
            / "google_devices"
            / device
            / "BoardConfigPartial.mk"
        ),
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise RuntimeError(
        "TreeForge's transitional Google-AOSP adapter "
        "could not locate the active vendor BoardConfig "
        f"for {device!r}"
    )


def _treeforge_prebuilt_vendor_kernel_boot_core(
    text: str,
) -> str:
    """
    Android 15 has no native BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE
    path. Add one transactionally for TreeForge's explicit prebuilt
    mode. The original build/make/core/Makefile is always restored.
    """

    start_marker = (
        "# vendor kernel boot image\n"
        "ifeq ($(BUILDING_VENDOR_KERNEL_BOOT_IMAGE),true)"
    )

    start = text.find(
        start_marker
    )

    if start < 0:
        raise RuntimeError(
            "Android build core vendor_kernel_boot anchor "
            "was not found"
        )

    end_marker = (
        "endif # BUILDING_VENDOR_KERNEL_BOOT_IMAGE"
    )

    end = text.find(
        end_marker,
        start,
    )

    if end < 0:
        raise RuntimeError(
            "Android build core vendor_kernel_boot end "
            "anchor was not found"
        )

    end += len(
        end_marker
    )

    if (
        end < len(text)
        and text[end] == "\n"
    ):
        end += 1

    original = text[
        start:end
    ]

    replacement = (
        "# vendor kernel boot image\n"
        "# TreeForge temporary prebuilt adapter.\n"
        "ifdef BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE\n"
        "INSTALLED_VENDOR_KERNEL_BOOTIMAGE_TARGET := "
        "$(PRODUCT_OUT)/vendor_kernel_boot.img\n"
        "$(eval $(call copy-one-file,"
        "$(BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE),"
        "$(INSTALLED_VENDOR_KERNEL_BOOTIMAGE_TARGET)))\n"
        "$(call declare-1p-container,"
        "$(INSTALLED_VENDOR_KERNEL_BOOTIMAGE_TARGET),)\n"
        "$(call declare-container-license-deps,"
        "$(INSTALLED_VENDOR_KERNEL_BOOTIMAGE_TARGET),"
        "$(BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE),"
        "$(PRODUCT_OUT)/:/)\n"
        "else\n"
        + original
        + "endif # BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE\n"
    )

    return (
        text[:start]
        + replacement
        + text[end:]
    )


def _validate_projection_artifact(
    *,
    provider_root: Path,
    entry: dict[str, object],
    name: str,
) -> Path:
    relative_value = entry.get(
        "path"
    )

    expected_size = entry.get(
        "size"
    )

    expected_sha = entry.get(
        "sha256"
    )

    if (
        not isinstance(
            relative_value,
            str,
        )
        or not relative_value
    ):
        raise RuntimeError(
            "TreeForge kernel provider artifact has "
            f"an invalid path: {name}"
        )

    if (
        not isinstance(
            expected_size,
            int,
        )
        or expected_size < 0
    ):
        raise RuntimeError(
            "TreeForge kernel provider artifact has "
            f"an invalid size: {name}"
        )

    if (
        not isinstance(
            expected_sha,
            str,
        )
        or len(expected_sha) != 64
    ):
        raise RuntimeError(
            "TreeForge kernel provider artifact has "
            f"an invalid SHA-256: {name}"
        )

    source = (
        provider_root
        / relative_value
    ).resolve()

    try:
        source.relative_to(
            provider_root.resolve()
        )

    except ValueError as exc:
        raise RuntimeError(
            "TreeForge kernel provider artifact escapes "
            f"its provider root: {name}"
        ) from exc

    if not source.is_file():
        raise RuntimeError(
            "TreeForge kernel provider artifact is "
            f"unavailable: {source}"
        )

    if (
        source.stat().st_size
        != expected_size
    ):
        raise RuntimeError(
            "TreeForge kernel provider artifact size "
            f"mismatch: {name}"
        )

    if (
        _sha256_file(
            source
        )
        != expected_sha
    ):
        raise RuntimeError(
            "TreeForge kernel provider artifact SHA-256 "
            f"mismatch: {name}"
        )

    return source


@contextlib.contextmanager
def _temporary_treeforge_aosp_kernel_projection_at(
    *,
    aosp_root: Path,
    target_kernel_dir: Path,
    vendor_board_config: Path,
    core_makefile: Path,
    bundle: dict[str, object],
    mode: str,
    transaction_parent: Path,
) -> Iterator[dict[str, object]]:
    """
    Temporarily replace AOSP's canonical kernel input directory.

    AOSP mode:
      TreeForge provides Image/modules/FIPS/DT inputs.
      Final kernel-family image shortcuts are omitted.
      Android constructs the final images itself.

    Prebuilt mode:
      TreeForge's coherent packaged images are exposed to Android.
      Native BOARD_PREBUILT_* hooks are used where available.
      A temporary Android-15 core hook supplies the missing
      vendor_kernel_boot prebuilt path.

    No post-build image replacement occurs in either mode.
    """

    if mode not in (
        "aosp",
        "prebuilt",
    ):
        raise RuntimeError(
            f"unsupported TreeForge kernel mode: {mode!r}"
        )

    root_value = bundle.get(
        "root"
    )

    generation_value = bundle.get(
        "generation"
    )

    artifacts_value = bundle.get(
        "artifacts"
    )

    if not isinstance(
        root_value,
        Path,
    ):
        raise RuntimeError(
            "TreeForge kernel provider has no root"
        )

    if (
        not isinstance(
            generation_value,
            str,
        )
        or not generation_value
    ):
        raise RuntimeError(
            "TreeForge kernel provider has no generation"
        )

    if not isinstance(
        artifacts_value,
        dict,
    ):
        raise RuntimeError(
            "TreeForge kernel provider has no artifact map"
        )

    target_kernel_dir = (
        target_kernel_dir.resolve()
    )

    vendor_board_config = (
        vendor_board_config.resolve()
    )

    core_makefile = (
        core_makefile.resolve()
    )

    if not vendor_board_config.is_file():
        raise RuntimeError(
            "active vendor BoardConfig is unavailable: "
            f"{vendor_board_config}"
        )

    if not core_makefile.is_file():
        raise RuntimeError(
            "Android build core Makefile is unavailable: "
            f"{core_makefile}"
        )

    transaction_parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    transaction_root = Path(
        tempfile.mkdtemp(
            prefix="kernel-composition-",
            dir=str(
                transaction_parent
            ),
        )
    ).resolve()

    #
    # Keep backup storage outside the AOSP source tree so Soong/Kati
    # cannot discover the original Google kernel source/prebuilt tree
    # while TreeForge's projection is active.
    #
    try:
        transaction_root.relative_to(
            aosp_root.resolve()
        )

    except ValueError:
        pass

    else:
        shutil.rmtree(
            transaction_root,
            ignore_errors=True,
        )
        raise RuntimeError(
            "TreeForge kernel transaction backup must "
            "live outside the AOSP checkout"
        )

    target_existed = (
        target_kernel_dir.exists()
        or target_kernel_dir.is_symlink()
    )

    if target_existed:
        if (
            os.stat(
                target_kernel_dir.parent
            ).st_dev
            != os.stat(
                transaction_root
            ).st_dev
        ):
            shutil.rmtree(
                transaction_root,
                ignore_errors=True,
            )
            raise RuntimeError(
                "TreeForge cannot atomically move the "
                "canonical AOSP kernel directory to its "
                "transaction backup: different filesystems"
            )

    kernel_backup = (
        transaction_root
        / "original-kernel-dir"
    )

    board_backup = (
        transaction_root
        / "BoardConfigVendor.mk"
    )

    core_backup = (
        transaction_root
        / "Makefile"
    )

    shutil.copy2(
        vendor_board_config,
        board_backup,
    )

    shutil.copy2(
        core_makefile,
        core_backup,
    )

    original_board_bytes = (
        vendor_board_config.read_bytes()
    )

    original_core_bytes = (
        core_makefile.read_bytes()
    )

    try:
        if target_existed:
            target_kernel_dir.rename(
                kernel_backup
            )

        target_kernel_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        skip = (
            TREEFORGE_AOSP_KERNEL_SUPPRESSED_IMAGES
            if mode == "aosp"
            else frozenset()
        )

        copied_paths: set[str] = set()

        for name, raw_entry in artifacts_value.items():
            if not isinstance(
                name,
                str,
            ):
                continue

            if not isinstance(
                raw_entry,
                dict,
            ):
                continue

            source_artifact = (
                _validate_projection_artifact(
                    provider_root=root_value,
                    entry=raw_entry,
                    name=name,
                )
            )

            relative_value = raw_entry.get(
                "path"
            )

            assert isinstance(
                relative_value,
                str,
            )

            relative = Path(
                relative_value
            )

            if (
                len(relative.parts) == 1
                and relative.name in skip
            ):
                continue

            relative_text = (
                relative.as_posix()
            )

            if relative_text in copied_paths:
                raise RuntimeError(
                    "duplicate TreeForge kernel provider "
                    f"projection path: {relative_text}"
                )

            copied_paths.add(
                relative_text
            )

            destination = (
                target_kernel_dir
                / relative
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            try:
                os.link(
                    source_artifact,
                    destination,
                )

            except OSError:
                shutil.copy2(
                    source_artifact,
                    destination,
                )

        if mode == "aosp":
            for required in (
                TREEFORGE_AOSP_KERNEL_REQUIRED_ARTIFACTS
            ):
                if not (
                    target_kernel_dir
                    / required
                ).is_file():
                    raise RuntimeError(
                        "TreeForge AOSP source projection "
                        f"is missing {required}"
                    )

            for forbidden in (
                TREEFORGE_AOSP_KERNEL_SUPPRESSED_IMAGES
            ):
                if (
                    target_kernel_dir
                    / forbidden
                ).exists():
                    raise RuntimeError(
                        "TreeForge AOSP-built mode exposed "
                        f"a final image shortcut: {forbidden}"
                    )

        else:
            for required in (
                KERNEL_PROVIDER_REQUIRED_ARTIFACTS
            ):
                if not (
                    target_kernel_dir
                    / required
                ).is_file():
                    raise RuntimeError(
                        "TreeForge prebuilt projection is "
                        f"missing {required}"
                    )

        relative_kernel_dir = (
            target_kernel_dir
            .relative_to(
                aosp_root.resolve()
            )
            .as_posix()
        )

        marker = (
            "\n"
            "# BEGIN TREEFORGE TEMPORARY KERNEL COMPOSITION\n"
        )

        if mode == "aosp":
            override = (
                marker
                + "BOARD_PREBUILT_VENDOR_DLKMIMAGE :=\n"
                + "BOARD_PREBUILT_SYSTEM_DLKMIMAGE :=\n"
                + "BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE :=\n"
                + "# END TREEFORGE TEMPORARY KERNEL COMPOSITION\n"
            )

        else:
            override = (
                marker
                + "BOARD_PREBUILT_VENDOR_DLKMIMAGE := "
                + relative_kernel_dir
                + "/vendor_dlkm.img\n"
                + "BOARD_PREBUILT_SYSTEM_DLKMIMAGE := "
                + relative_kernel_dir
                + "/system_dlkm.img\n"
                + "BOARD_PREBUILT_VENDOR_KERNEL_BOOTIMAGE := "
                + relative_kernel_dir
                + "/vendor_kernel_boot.img\n"
                + "# END TREEFORGE TEMPORARY KERNEL COMPOSITION\n"
            )

        vendor_board_config.write_bytes(
            original_board_bytes
            + override.encode(
                "utf-8",
            )
        )

        if mode == "prebuilt":
            patched_core = (
                _treeforge_prebuilt_vendor_kernel_boot_core(
                    original_core_bytes.decode(
                        "utf-8",
                    )
                )
            )

            core_makefile.write_text(
                patched_core,
                encoding="utf-8",
            )

        yield {
            "mode": mode,
            "generation": generation_value,
            "target_kernel_dir": relative_kernel_dir,
            "absolute_target_kernel_dir": (
                target_kernel_dir
            ),
        }

    finally:
        #
        # File restoration happens even on Python exceptions,
        # Android build failures, and Ctrl-C/KeyboardInterrupt.
        #
        try:
            if board_backup.is_file():
                shutil.copy2(
                    board_backup,
                    vendor_board_config,
                )

            if core_backup.is_file():
                shutil.copy2(
                    core_backup,
                    core_makefile,
                )

        finally:
            try:
                _remove_treeforge_path(
                    target_kernel_dir
                )

                if kernel_backup.exists():
                    kernel_backup.rename(
                        target_kernel_dir
                    )

            finally:
                shutil.rmtree(
                    transaction_root,
                    ignore_errors=True,
                )


@contextlib.contextmanager
def _temporary_treeforge_aosp_kernel_composition(
    *,
    aosp_root: Path,
    target: LunchTarget,
    device: str,
    bundle: dict[str, object],
    mode: str,
) -> Iterator[dict[str, object]]:
    """
    Transitional Google-AOSP integration.

    This adapter is intentionally disposable once TreeForge Device Tree
    becomes the canonical product source.
    """

    target_kernel_dir = (
        _resolve_aosp_target_kernel_dir(
            aosp_root=aosp_root,
            target=target,
        )
    )

    vendor_board_config = (
        _treeforge_google_vendor_board_config(
            aosp_root=aosp_root,
            device=device,
        )
    )

    core_makefile = (
        aosp_root
        / "build"
        / "make"
        / "core"
        / "Makefile"
    ).resolve()

    transaction_parent = (
        TREEFORGE_ROOT
        / ".treeforge"
        / "runtime"
        / "aosp-kernel-transactions"
    )

    with _temporary_treeforge_aosp_kernel_projection_at(
        aosp_root=aosp_root,
        target_kernel_dir=target_kernel_dir,
        vendor_board_config=vendor_board_config,
        core_makefile=core_makefile,
        bundle=bundle,
        mode=mode,
        transaction_parent=transaction_parent,
    ) as runtime:
        yield runtime


def _validate_treeforge_kernel_outputs(
    *,
    product_out: Path,
    bundle: dict[str, object],
    mode: str,
) -> None:
    image_names = (
        "boot.img",
        "vendor_kernel_boot.img",
        "dtbo.img",
        "vendor_dlkm.img",
        "system_dlkm.img",
    )

    artifacts = bundle.get(
        "artifacts"
    )

    root = bundle.get(
        "root"
    )

    if not isinstance(
        artifacts,
        dict,
    ):
        raise RuntimeError(
            "TreeForge kernel output validation has "
            "no provider artifact map"
        )

    if not isinstance(
        root,
        Path,
    ):
        raise RuntimeError(
            "TreeForge kernel output validation has "
            "no provider root"
        )

    for name in image_names:
        output = (
            product_out
            / name
        )

        if not output.is_file():
            raise RuntimeError(
                "AOSP did not produce required kernel-family "
                f"image: {output}"
            )

        if mode != "prebuilt":
            continue

        raw_entry = artifacts.get(
            name
        )

        if not isinstance(
            raw_entry,
            dict,
        ):
            raise RuntimeError(
                "TreeForge prebuilt provider is missing "
                f"{name}"
            )

        source = _validate_projection_artifact(
            provider_root=root,
            entry=raw_entry,
            name=name,
        )

        expected = _sha256_file(
            source
        )

        actual = _sha256_file(
            output
        )

        if actual != expected:
            raise RuntimeError(
                "AOSP prebuilt integration did not preserve "
                f"the exact TreeForge {name}: expected "
                f"{expected}, found {actual}"
            )

    if mode == "aosp":
        typer.echo(
            "AOSP kernel-family construction validated."
        )

    else:
        typer.echo(
            "Exact TreeForge kernel prebuilt family validated."
        )








def _ensure_git_lfs() -> None:
    if shutil.which("git") is None:
        raise RuntimeError("git is required for MindTheGapps")
    if shutil.which("git-lfs") is None:
        raise RuntimeError(
            "MindTheGapps requires git-lfs, but git-lfs is not installed"
        )
    subprocess.run(
        ["git", "lfs", "version"],
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _materialize_mindthegapps(
    aosp_root: Path,
) -> Path:
    """
    Materialize the pinned MindTheGapps provider at vendor/gapps.

    MindTheGapps makefiles use repository-relative vendor/gapps paths,
    so this location is part of the provider integration contract.
    """

    _ensure_git_lfs()

    destination = (
        aosp_root
        / "vendor"
        / "gapps"
    )

    legacy = (
        aosp_root
        / "vendor"
        / "treeforge"
        / "providers"
        / "mindthegapps"
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # Reuse an already-materialized TreeForge checkout rather than
    # downloading several gigabytes again.
    #
    if (
        not destination.exists()
        and (legacy / ".git").is_dir()
    ):
        typer.echo(
            "Relocating existing MindTheGapps checkout "
            "to vendor/gapps..."
        )

        shutil.move(
            str(legacy),
            str(destination),
        )

    if (
        destination.exists()
        and not (destination / ".git").is_dir()
    ):
        raise RuntimeError(
            "vendor/gapps already exists but is not the "
            "MindTheGapps Git checkout"
        )

    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"

    if not (destination / ".git").is_dir():
        subprocess.run(
            [
                "git",
                "clone",
                "--branch",
                MINDTHEGAPPS_BRANCH,
                "--single-branch",
                MINDTHEGAPPS_URL,
                str(destination),
            ],
            env=env,
            text=True,
            check=True,
        )
    else:
        _run(
            [
                "git",
                "fetch",
                "origin",
                MINDTHEGAPPS_BRANCH,
            ],
            cwd=destination,
            env=env,
        )

    probe = subprocess.run(
        [
            "git",
            "cat-file",
            "-e",
            f"{MINDTHEGAPPS_PIN}^{{commit}}",
        ],
        cwd=str(destination),
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if probe.returncode != 0:
        _run(
            [
                "git",
                "fetch",
                "origin",
                MINDTHEGAPPS_PIN,
            ],
            cwd=destination,
            env=env,
        )

    _run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            MINDTHEGAPPS_PIN,
            f"origin/{MINDTHEGAPPS_BRANCH}",
        ],
        cwd=destination,
    )

    _run(
        [
            "git",
            "checkout",
            "--detach",
            MINDTHEGAPPS_PIN,
        ],
        cwd=destination,
    )

    _run(
        [
            "git",
            "lfs",
            "install",
            "--local",
        ],
        cwd=destination,
    )

    _run(
        [
            "git",
            "lfs",
            "pull",
            "origin",
            MINDTHEGAPPS_PIN,
        ],
        cwd=destination,
    )

    _run(
        [
            "git",
            "lfs",
            "fsck",
        ],
        cwd=destination,
    )

    lfs_files = _run(
        [
            "git",
            "lfs",
            "ls-files",
            "-n",
        ],
        cwd=destination,
        capture=True,
    ).stdout.splitlines()

    pointer = (
        b"version "
        b"https://git-lfs.github.com/spec/v1"
    )

    unresolved: list[str] = []

    for raw in lfs_files:
        relative = raw.strip()

        if not relative:
            continue

        path = destination / relative

        if not path.is_file():
            unresolved.append(
                relative
            )
            continue

        with path.open("rb") as stream:
            if stream.read(128).startswith(
                pointer
            ):
                unresolved.append(
                    relative
                )

    if unresolved:
        preview = ", ".join(
            unresolved[:8]
        )

        suffix = (
            ""
            if len(unresolved) <= 8
            else ", ..."
        )

        raise RuntimeError(
            "MindTheGapps LFS materialization "
            "is incomplete: "
            f"{preview}{suffix}"
        )

    return destination


def _find_product_makefile(
    aosp_root: Path,
    product: str,
) -> Path:
    """
    Locate the makefile which declares exactly PRODUCT_NAME=<product>.

    The selected product is resolved directly from PRODUCT_NAME.
    """

    expression = re.compile(
        rf"^\s*PRODUCT_NAME\s*:?=\s*"
        rf"{re.escape(product)}\s*$",
        re.MULTILINE,
    )

    matches: list[Path] = []

    for relative_root in (
        "device",
        "vendor",
    ):
        root = aosp_root / relative_root

        if not root.is_dir():
            continue

        for path in root.rglob("*.mk"):
            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                continue

            active_content = "\n".join(
                line.split("#", 1)[0]
                for line in content.splitlines()
            )

            if expression.search(active_content):
                matches.append(
                    path.resolve()
                )

    if not matches:
        raise RuntimeError(
            "unable to locate product makefile for "
            f"{product!r}"
        )

    matches.sort(
        key=lambda item: (
            len(item.parts),
            item.as_posix(),
        )
    )

    return matches[0]


@contextlib.contextmanager
def _temporary_mindthegapps_inherit(
    *,
    aosp_root: Path,
    probe: TargetProbe,
) -> Iterator[Path]:
    """
    Temporarily add MindTheGapps to the selected product makefile.

    The selected lunch/product identity remains unchanged.

    MindTheGapps documents inline integration as inheriting:

        $GAPPS_PATH/$ARCH/$ARCH-vendor.mk

    TreeForge materializes GAPPS_PATH as vendor/gapps, so an arm64
    product receives:

        $(call inherit-product, vendor/gapps/arm64/arm64-vendor.mk)

    The inherit is inserted immediately after the final existing
    inherit-product line before PRODUCT_NAME and the original product
    makefile bytes are restored when the build leaves this context,
    whether the build succeeds or fails.
    """

    provider = _materialize_mindthegapps(
        aosp_root
    )

    if (
        not probe.arch
        or probe.arch == "unresolved"
    ):
        raise RuntimeError(
            "unable to resolve target architecture for "
            "MindTheGapps integration"
        )

    vendor_mk = (
        provider
        / probe.arch
        / f"{probe.arch}-vendor.mk"
    )

    if not vendor_mk.is_file():
        raise RuntimeError(
            "MindTheGapps has no inline provider makefile for "
            f"TARGET_ARCH={probe.arch!r}: {vendor_mk}"
        )

    product_file = _find_product_makefile(
        aosp_root,
        probe.lunch.product,
    )

    gapps_rel = (
        vendor_mk
        .relative_to(aosp_root)
        .as_posix()
    )

    inherit_line = (
        "$(call inherit-product, "
        f"{gapps_rel})"
    )

    original = product_file.read_bytes()

    try:
        source = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            "selected product makefile is not UTF-8: "
            f"{product_file}"
        ) from exc

    existing = re.search(
        rf"^\s*{re.escape(inherit_line)}\s*$",
        source,
        re.MULTILINE,
    )

    #
    # Respect a pre-existing user/device-tree integration. Since
    # TreeForge did not add it, TreeForge must not remove it.
    #
    if existing is not None:
        typer.echo(
            "MindTheGapps inherit already present: "
            + str(
                product_file.relative_to(
                    aosp_root
                )
            )
        )

        yield product_file
        return

    lines = source.splitlines(
        keepends=True
    )

    product_name_index = None

    product_name_pattern = re.compile(
        r"^\s*PRODUCT_NAME\s*:?="
    )

    for index, line in enumerate(lines):
        active = line.split("#", 1)[0]

        if product_name_pattern.match(active):
            product_name_index = index
            break

    if product_name_index is None:
        raise RuntimeError(
            "selected product makefile has no PRODUCT_NAME: "
            f"{product_file}"
        )

    inherit_pattern = re.compile(
        r"^\s*\$\(\s*call\s+"
        r"inherit-product"
        r"(?:-if-exists)?"
        r"\s*,"
    )

    anchors = []

    for index, line in enumerate(
        lines[:product_name_index]
    ):
        active = line.split("#", 1)[0]

        if inherit_pattern.match(active):
            anchors.append(index)

    if not anchors:
        raise RuntimeError(
            "selected product makefile has no inherit-product "
            "anchor before PRODUCT_NAME: "
            f"{product_file}"
        )

    anchor_index = anchors[-1]

    anchor_line = lines[anchor_index]

    if anchor_line.endswith("\r\n"):
        newline = "\r\n"
    else:
        newline = "\n"

    lines.insert(
        anchor_index + 1,
        inherit_line + newline,
    )

    modified = "".join(lines)

    try:
        product_file.write_text(
            modified,
            encoding="utf-8",
            newline="",
        )

        typer.echo(
            "MindTheGapps product inherit:"
        )
        typer.echo(
            "  "
            + str(
                product_file.relative_to(
                    aosp_root
                )
            )
        )
        typer.echo(
            "  "
            + inherit_line
        )

        yield product_file

    finally:
        product_file.write_bytes(
            original
        )

        typer.echo(
            "Restored product makefile after "
            "MindTheGapps composition."
        )


def _treeforge_avb_key(
    device: str,
    partition: str,
) -> Path:
    root = (
        TREEFORGE_ROOT
        / ".treeforge-private"
        / "keys"
        / "avb"
    )
    matches = [
        path
        for path in root.glob(f"*/{device}/{partition}.pem")
        if path.is_file()
    ]
    if not matches:
        raise RuntimeError(
            "TreeForge AVB key is not provisioned for "
            f"{device}:{partition}"
        )
    matches.sort(
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    return matches[0].resolve()


def _aosp_avb_test_key(
    aosp_root: Path,
    algorithm: str,
) -> Path:
    if "RSA4096" in algorithm:
        filename = "testkey_rsa4096.pem"
    elif "RSA2048" in algorithm:
        filename = "testkey_rsa2048.pem"
    else:
        raise RuntimeError(
            f"unsupported AVB development algorithm: {algorithm!r}"
        )
    path = (
        aosp_root
        / "external"
        / "avb"
        / "test"
        / "data"
        / filename
    )
    if not path.is_file():
        raise RuntimeError(
            f"AOSP AVB development key does not exist: {path}"
        )
    return path.resolve()


def _treeforge_avb_private_key_root(
    device: str,
) -> Path:
    try:
        from treeforge.setup.avb_keys import (
            AVB_BRINGUP_PLATFORM_PROFILE,
        )

        profile = (
            AVB_BRINGUP_PLATFORM_PROFILE
        )

    except (
        ImportError,
        AttributeError,
    ):
        profile = (
            "android-15.0.0_r36"
        )

    base = (
        TREEFORGE_ROOT
        / ".treeforge-private"
        / "keys"
        / "avb"
    )

    candidates = (
        base
        / profile
        / device,
        base
        / device,
    )

    required = (
        "boot.pem",
        "init_boot.pem",
        "vbmeta.pem",
        "vbmeta_system.pem",
        "vbmeta_vendor.pem",
    )

    for root in candidates:
        if all(
            (root / name).is_file()
            for name in required
        ):
            return root.resolve()

    raise RuntimeError(
        "TreeForge AVB signing was selected "
        "but the setup-provisioned key set "
        f"for {device!r} was not found. "
        "Expected the five AVB keys beneath "
        f"{candidates[0]}"
    )


def _rsa_private_key_bits(
    path: Path,
) -> int:
    completed = subprocess.run(
        [
            "openssl",
            "pkey",
            "-in",
            str(path),
            "-text",
            "-noout",
        ],
        text=True,
        capture_output=True,
    )

    if completed.returncode != 0:
        message = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "openssl pkey failed"
        )

        raise RuntimeError(
            f"unable to inspect AVB key {path}: "
            f"{message}"
        )

    match = re.search(
        r"Private-Key:\s*\((\d+)\s+bit",
        completed.stdout,
    )

    if match is None:
        raise RuntimeError(
            "unable to determine RSA key size "
            f"for {path}"
        )

    return int(
        match.group(1),
        10,
    )


def _validate_treeforge_avb_keys(
    root: Path,
) -> None:
    expected = {
        "vbmeta.pem": 4096,
        "boot.pem": 2048,
        "init_boot.pem": 2048,
        "vbmeta_system.pem": 2048,
        "vbmeta_vendor.pem": 2048,
    }

    for name, bits in expected.items():
        path = root / name

        actual = (
            _rsa_private_key_bits(
                path
            )
        )

        if actual != bits:
            raise RuntimeError(
                "TreeForge AVB key-size "
                "mismatch: "
                f"{path} is RSA{actual}; "
                f"expected RSA{bits}"
            )


def _treeforge_build_avb_profile(
    probe: TargetProbe,
):
    """
    Resolve TreeForge's versioned AVB signing policy for this Build.

    Android 15 is the current Build platform. Future platform profiles extend
    the selector rather than adding device-specific key logic here.
    """

    from treeforge.android.version.device_tree.avb_signing import (
        select_android_device_tree_avb_signing_profile,
    )

    device_root = (
        Path("device")
        / "treeforge"
        / probe.device
    )

    return (
        select_android_device_tree_avb_signing_profile(
            "15",
            "treeforge",
            device_root=device_root,
            device_name=probe.device,
        )
    )


def _ensure_treeforge_build_avb_keys(
    probe: TargetProbe,
):
    """
    Ensure every independent key required by the selected signing profile
    exists before Build stages the temporary AOSP signing provider.
    """

    from treeforge.setup.avb_keys import (
        provision_avb_development_keys,
    )

    profile = (
        _treeforge_build_avb_profile(
            probe
        )
    )

    requirements = tuple(
        (
            entry.partition_name,
            entry.algorithm,
        )
        for entry in profile.entries
    )

    keys = (
        provision_avb_development_keys(
            repository_root=(
                TREEFORGE_ROOT
            ),
            device=probe.device,
            profile=(
                profile.reference_tag
            ),
            requirements=requirements,
        )
    )

    key_by_partition = {
        key.partition:
        key.persistent_path
        for key in keys
    }

    expected = {
        entry.partition_name
        for entry in profile.entries
    }

    if (
        set(key_by_partition)
        != expected
    ):
        raise RuntimeError(
            "realized TreeForge AVB key "
            "population does not match "
            "the versioned signing profile; "
            f"expected={sorted(expected)!r}, "
            f"actual={sorted(key_by_partition)!r}"
        )

    return (
        profile,
        key_by_partition,
    )


def _avb_board_variable_prefix(
    partition_name: str,
) -> str:
    if partition_name == "vbmeta":
        return "BOARD_AVB"

    return (
        "BOARD_AVB_"
        + partition_name.upper()
    )


def _avb_info_image(
    *,
    avbtool: Path,
    image: Path,
    cwd: Path,
) -> str:
    completed = subprocess.run(
        [
            str(avbtool),
            "info_image",
            "--image",
            str(image),
        ],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=True,
    )

    return completed.stdout


def _avb_public_key_sha1(
    info: str,
) -> str:
    match = re.search(
        r"Public key \(sha1\):\s*"
        r"([0-9a-fA-F]+)",
        info,
    )

    if match is None:
        raise RuntimeError(
            "AVB image information does not "
            "contain a public-key SHA-1"
        )

    return (
        match.group(1)
        .lower()
    )


def _avb_chain_descriptors(
    info: str,
) -> tuple[
    tuple[str, int, str | None],
    ...,
]:
    """
    Parse only Chain Partition descriptors from avbtool info_image output.

    Returns:
        (partition, rollback_index_location, public_key_sha1)
    """

    descriptors = []
    current: dict[
        str,
        str,
    ] | None = None

    def flush() -> None:
        nonlocal current

        if current is None:
            return

        partition = current.get(
            "Partition Name"
        )

        rollback = current.get(
            "Rollback Index Location"
        )

        if (
            partition is None
            or rollback is None
        ):
            raise RuntimeError(
                "incomplete AVB chain "
                f"descriptor: {current!r}"
            )

        descriptors.append(
            (
                partition,
                int(
                    rollback,
                    10,
                ),
                current.get(
                    "Public key (sha1)"
                ),
            )
        )

        current = None

    for raw_line in info.splitlines():
        stripped = raw_line.strip()

        if stripped.endswith(
            "descriptor:"
        ):
            flush()

            if stripped == (
                "Chain Partition descriptor:"
            ):
                current = {}

            continue

        if (
            current is None
            or ":" not in stripped
        ):
            continue

        key, value = stripped.split(
            ":",
            1,
        )

        current[
            key.strip()
        ] = value.strip()

    flush()

    return tuple(
        descriptors
    )


def _treeforge_build_avb_contract(
    *,
    probe: TargetProbe,
    profile,
) -> tuple[
    dict[str, dict[str, int]],
    dict[str, dict[str, str]],
]:
    """
    Resolve the versioned expected AVB output graph.

    Signing policy is never inferred here from arbitrary image names.
    Unsupported device/profile combinations fail closed.
    """

    if (
        profile.reference_tag
        == "android-15.0.0_r36"
        and probe.device
        == "tangorpro"
    ):
        from treeforge.android.version.android15.device_tree.avb_signing import (
            ANDROID_15_R36_TANGORPRO_AVB_CHAIN_RELATIONSHIPS,
            ANDROID_15_R36_TANGORPRO_AVB_DESCRIPTOR_TYPES,
        )

        chains: dict[
            str,
            dict[str, int],
        ] = {}

        for (
            owner,
            target,
            rollback_location,
        ) in (
            ANDROID_15_R36_TANGORPRO_AVB_CHAIN_RELATIONSHIPS
        ):
            chains.setdefault(
                owner,
                {},
            )[
                target
            ] = rollback_location

        descriptors = {
            owner: {
                partition: kind
                for (
                    partition,
                    kind,
                ) in entries
            }
            for (
                owner,
                entries,
            ) in (
                ANDROID_15_R36_TANGORPRO_AVB_DESCRIPTOR_TYPES
            )
        }

        return (
            chains,
            descriptors,
        )

    raise RuntimeError(
        "TreeForge has no post-build "
        "AVB topology acceptance contract "
        "for "
        f"{profile.reference_tag}/"
        f"{probe.device}"
    )


def _avb_scalar(
    info: str,
    label: str,
) -> str:
    match = re.search(
        (
            r"^"
            + re.escape(label)
            + r":\s*(.+?)\s*$"
        ),
        info,
        re.MULTILINE,
    )

    if match is None:
        raise RuntimeError(
            "AVB image information "
            f"does not contain {label!r}"
        )

    return (
        match.group(1)
        .strip()
    )


def _avb_auth_descriptors(
    info: str,
) -> dict[str, str]:
    """
    Return partition -> descriptor kind for AVB Hash/Hashtree descriptors.
    Property and chain descriptors are deliberately excluded.
    """

    result: dict[
        str,
        str,
    ] = {}

    current_kind: str | None = None
    current_partition: str | None = None

    def flush() -> None:
        nonlocal current_kind
        nonlocal current_partition

        if (
            current_kind is not None
            and current_partition
            is not None
        ):
            previous = result.get(
                current_partition
            )

            if (
                previous is not None
                and previous
                != current_kind
            ):
                raise RuntimeError(
                    "duplicate/conflicting "
                    "AVB descriptor for "
                    f"{current_partition}"
                )

            result[
                current_partition
            ] = current_kind

        current_kind = None
        current_partition = None

    for raw_line in (
        info.splitlines()
    ):
        stripped = raw_line.strip()

        if stripped.endswith(
            "descriptor:"
        ):
            flush()

            lowered = (
                stripped.lower()
            )

            if lowered == (
                "hash descriptor:"
            ):
                current_kind = "hash"

            elif lowered == (
                "hashtree descriptor:"
            ):
                current_kind = (
                    "hashtree"
                )

            continue

        if (
            current_kind
            is None
            or ":" not in stripped
        ):
            continue

        key, value = stripped.split(
            ":",
            1,
        )

        if (
            key.strip()
            == "Partition Name"
        ):
            current_partition = (
                value.strip()
            )

    flush()

    return result


def _build_security_patch_timestamp(
    product_out: Path,
) -> tuple[str, int]:
    """
    Resolve PLATFORM_SECURITY_PATCH_TIMESTAMP from the built system identity.

    Android 15/r36's AVB signing profile uses the platform security-patch
    timestamp as the rollback index.
    """

    candidates = (
        product_out
        / "system"
        / "build.prop",
        product_out
        / "system"
        / "system"
        / "build.prop",
    )

    patch: str | None = None

    for candidate in candidates:
        if not candidate.is_file():
            continue

        for line in candidate.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            if line.startswith(
                "ro.build.version.security_patch="
            ):
                patch = line.split(
                    "=",
                    1,
                )[1].strip()
                break

        if patch is not None:
            break

    if not patch:
        raise RuntimeError(
            "unable to resolve built "
            "ro.build.version.security_patch "
            f"beneath {product_out}"
        )

    try:
        patch_date = (
            dt.date.fromisoformat(
                patch
            )
        )

    except ValueError as exc:
        raise RuntimeError(
            "built security patch is not "
            f"an ISO date: {patch!r}"
        ) from exc

    timestamp = int(
        dt.datetime.combine(
            patch_date,
            dt.time.min,
            tzinfo=dt.timezone.utc,
        ).timestamp()
    )

    return (
        patch,
        timestamp,
    )


def _write_treeforge_avb_report(
    *,
    report_path: Path,
    profile,
    graph: dict,
) -> None:
    lines = [
        "TreeForge AVB Build Acceptance",
        "",
        (
            "Profile: "
            f"{profile.profile_id}"
        ),
        (
            "Reference: "
            f"{profile.reference_tag}"
        ),
        "Provider: TreeForge",
        (
            "Security patch: "
            f"{graph['security_patch']}"
        ),
        (
            "Expected rollback index: "
            f"{graph['expected_rollback_index']}"
        ),
        "",
        "Signing identities",
    ]

    for node in graph[
        "nodes"
    ]:
        lines.append(
            "  "
            f"{node['partition']:<16} "
            f"{node['algorithm']:<16} "
            f"{node['key_sha1']} "
            "PASS"
        )

        lines.append(
            "    rollback index: "
            f"{node['rollback_index']} "
            "PASS"
        )

    lines.extend(
        [
            "",
            "Chain",
        ]
    )

    for chain in graph[
        "chains"
    ]:
        lines.append(
            "  "
            f"{chain['owner']} -> "
            f"{chain['target']} "
            "rollback_location="
            f"{chain['rollback_location']} "
            "key="
            f"{chain['key_sha1']} "
            "PASS"
        )

    lines.extend(
        [
            "",
            "Descriptors",
        ]
    )

    for descriptor in graph[
        "descriptors"
    ]:
        lines.append(
            "  "
            f"{descriptor['owner']} -> "
            f"{descriptor['target']} "
            f"[{descriptor['kind']}] "
            "PASS"
        )

    lines.extend(
        [
            "",
            "Result: PASS",
            (
                "All independent signing "
                "identities, rollback policy, "
                "chain relationships, and "
                "hash/hashtree descriptor "
                "membership match the "
                "versioned TreeForge contract."
            ),
        ]
    )

    _write_report(
        report_path,
        lines,
    )


def _verify_treeforge_avb_graph(
    *,
    aosp_root: Path,
    probe: TargetProbe,
    target: LunchTarget,
    product_out: Path,
) -> dict:
    """
    Verify the exact versioned AVB graph emitted into PRODUCT_OUT.

    Acceptance covers:
      - signing algorithm
      - embedded TreeForge key identity
      - rollback-index value
      - exact chain membership
      - chain rollback-index locations
      - child chain-key binding
      - exact Hash/Hashtree descriptor membership
      - descriptor cryptographic verification by avbtool
    """

    avbtool = _host_tool(
        aosp_root=aosp_root,
        target=target,
        name="avbtool",
    )

    (
        profile,
        key_by_partition,
    ) = (
        _ensure_treeforge_build_avb_keys(
            probe
        )
    )

    (
        expected_chains,
        expected_descriptors,
    ) = (
        _treeforge_build_avb_contract(
            probe=probe,
            profile=profile,
        )
    )

    (
        security_patch,
        expected_rollback_index,
    ) = (
        _build_security_patch_timestamp(
            product_out
        )
    )

    entry_by_partition = {
        entry.partition_name:
        entry
        for entry in profile.entries
    }

    expected_nodes = set(
        entry_by_partition
    )

    if "vbmeta" not in expected_nodes:
        raise RuntimeError(
            "TreeForge AVB profile "
            "does not contain root vbmeta"
        )

    visited: set[str] = set()

    node_results = []
    chain_results = []
    descriptor_results = []

    with tempfile.TemporaryDirectory(
        prefix="treeforge-avb-graph-"
    ) as raw:
        temporary = Path(raw)

        public_keys: dict[
            str,
            Path,
        ] = {}

        public_sha1: dict[
            str,
            str,
        ] = {}

        for partition in sorted(
            expected_nodes
        ):
            key = (
                key_by_partition[
                    partition
                ]
            )

            output = (
                temporary
                / f"{partition}.avbpubkey"
            )

            subprocess.run(
                [
                    str(avbtool),
                    "extract_public_key",
                    "--key",
                    str(key),
                    "--output",
                    str(output),
                ],
                cwd=str(aosp_root),
                text=True,
                check=True,
            )

            public_keys[
                partition
            ] = output

            public_sha1[
                partition
            ] = hashlib.sha1(
                output.read_bytes()
            ).hexdigest()

        def verify_node(
            partition: str,
        ) -> None:
            if partition in visited:
                raise RuntimeError(
                    "AVB signing graph contains "
                    "a cycle or duplicate chained "
                    f"target: {partition}"
                )

            visited.add(
                partition
            )

            entry = (
                entry_by_partition[
                    partition
                ]
            )

            key = (
                key_by_partition[
                    partition
                ]
            )

            image = (
                product_out
                / f"{partition}.img"
            )

            if not image.is_file():
                raise RuntimeError(
                    "required AVB signing-node "
                    f"image is missing: {image}"
                )

            info = _avb_info_image(
                avbtool=avbtool,
                image=image,
                cwd=aosp_root,
            )

            algorithm = (
                _avb_scalar(
                    info,
                    "Algorithm",
                )
            )

            if (
                algorithm
                != entry.algorithm
            ):
                raise RuntimeError(
                    "AVB algorithm mismatch "
                    f"for {partition}: "
                    f"expected={entry.algorithm}, "
                    f"actual={algorithm}"
                )

            actual_key = (
                _avb_public_key_sha1(
                    info
                )
            )

            expected_key = (
                public_sha1[
                    partition
                ]
            )

            if actual_key != expected_key:
                raise RuntimeError(
                    "TreeForge AVB key "
                    "identity mismatch for "
                    f"{partition}: "
                    f"expected={expected_key}, "
                    f"actual={actual_key}"
                )

            rollback_index = int(
                _avb_scalar(
                    info,
                    "Rollback Index",
                ),
                10,
            )

            if (
                rollback_index
                != expected_rollback_index
            ):
                raise RuntimeError(
                    "AVB rollback-index "
                    f"mismatch for {partition}: "
                    f"expected="
                    f"{expected_rollback_index}, "
                    f"actual={rollback_index}"
                )

            actual_descriptor_map = (
                _avb_auth_descriptors(
                    info
                )
            )

            expected_descriptor_map = (
                expected_descriptors.get(
                    partition,
                    {},
                )
            )

            if (
                actual_descriptor_map
                != expected_descriptor_map
            ):
                raise RuntimeError(
                    "AVB Hash/Hashtree "
                    "descriptor topology mismatch "
                    f"for {partition}; "
                    f"expected="
                    f"{expected_descriptor_map!r}, "
                    f"actual="
                    f"{actual_descriptor_map!r}"
                )

            chains = (
                _avb_chain_descriptors(
                    info
                )
            )

            actual_chain_locations: dict[
                str,
                int,
            ] = {}

            descriptor_chain_sha1: dict[
                str,
                str | None,
            ] = {}

            for (
                child,
                rollback_location,
                descriptor_sha1,
            ) in chains:
                if (
                    child
                    in actual_chain_locations
                ):
                    raise RuntimeError(
                        "duplicate AVB chain "
                        f"descriptor: "
                        f"{partition} -> {child}"
                    )

                actual_chain_locations[
                    child
                ] = rollback_location

                descriptor_chain_sha1[
                    child
                ] = (
                    descriptor_sha1.lower()
                    if descriptor_sha1
                    is not None
                    else None
                )

            expected_chain_locations = (
                expected_chains.get(
                    partition,
                    {},
                )
            )

            if (
                actual_chain_locations
                != expected_chain_locations
            ):
                raise RuntimeError(
                    "AVB chain topology/"
                    "rollback-location mismatch "
                    f"for {partition}; "
                    f"expected="
                    f"{expected_chain_locations!r}, "
                    f"actual="
                    f"{actual_chain_locations!r}"
                )

            command = [
                str(avbtool),
                "verify_image",
                "--image",
                str(image),
                "--key",
                str(key),
            ]

            for child in sorted(
                actual_chain_locations
            ):
                if child not in expected_nodes:
                    raise RuntimeError(
                        "AVB graph contains "
                        "an independent chained "
                        "signing node without a "
                        "TreeForge versioned "
                        f"signing entry: {child}"
                    )

                child_sha1 = (
                    public_sha1[
                        child
                    ]
                )

                encoded_child_sha1 = (
                    descriptor_chain_sha1[
                        child
                    ]
                )

                if (
                    encoded_child_sha1
                    is not None
                    and encoded_child_sha1
                    != child_sha1
                ):
                    raise RuntimeError(
                        "AVB chained public-key "
                        "identity mismatch: "
                        f"{partition} -> {child}; "
                        f"expected={child_sha1}, "
                        f"actual="
                        f"{encoded_child_sha1}"
                    )

                rollback_location = (
                    actual_chain_locations[
                        child
                    ]
                )

                command.extend(
                    [
                        "--expected_chain_partition",
                        (
                            f"{child}:"
                            f"{rollback_location}:"
                            f"{public_keys[child]}"
                        ),
                    ]
                )

                chain_results.append(
                    {
                        "owner": partition,
                        "target": child,
                        "rollback_location": (
                            rollback_location
                        ),
                        "key_sha1": (
                            child_sha1
                        ),
                    }
                )

            completed = subprocess.run(
                command,
                cwd=str(product_out),
                text=True,
                capture_output=True,
            )

            if completed.returncode != 0:
                message = (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or (
                        "avbtool verify_image "
                        "failed"
                    )
                )

                raise RuntimeError(
                    "cryptographic AVB "
                    "descriptor verification "
                    f"failed for {partition}: "
                    f"{message}"
                )

            node_results.append(
                {
                    "partition": partition,
                    "algorithm": algorithm,
                    "key_sha1": actual_key,
                    "rollback_index": (
                        rollback_index
                    ),
                }
            )

            for (
                target_name,
                kind,
            ) in sorted(
                actual_descriptor_map.items()
            ):
                descriptor_results.append(
                    {
                        "owner": partition,
                        "target": (
                            target_name
                        ),
                        "kind": kind,
                    }
                )

            for child in sorted(
                actual_chain_locations
            ):
                verify_node(
                    child
                )

        verify_node(
            "vbmeta"
        )

    if visited != expected_nodes:
        raise RuntimeError(
            "TreeForge AVB signing "
            "profile contains unreachable "
            "signing nodes; "
            f"unreachable="
            f"{sorted(expected_nodes - visited)!r}"
        )

    return {
        "security_patch": (
            security_patch
        ),
        "expected_rollback_index": (
            expected_rollback_index
        ),
        "nodes": sorted(
            node_results,
            key=lambda item:
            item["partition"],
        ),
        "chains": sorted(
            chain_results,
            key=lambda item:
            (
                item["owner"],
                item["target"],
            ),
        ),
        "descriptors": sorted(
            descriptor_results,
            key=lambda item:
            (
                item["owner"],
                item["target"],
            ),
        ),
    }



@contextlib.contextmanager
def _temporary_build_avb_provider(
    *,
    aosp_root: Path,
    probe: TargetProbe,
    signing: str,
):
    """
    Temporarily compose the selected TreeForge AVB signing profile into AOSP.

    The partition/key population is profile-driven. Missing persistent keys
    are generated before staging.
    """

    if signing != "treeforge":
        yield
        return

    (
        profile,
        key_by_partition,
    ) = (
        _ensure_treeforge_build_avb_keys(
            probe
        )
    )

    product_file_raw = (
        probe.values.get(
            "TREEFORGE_PRODUCT_MAKEFILE",
            "",
        )
    )

    if not product_file_raw:
        raise RuntimeError(
            "selected product makefile was "
            "not recorded by the target probe"
        )

    product_file = Path(
        product_file_raw
    ).resolve()

    product_root = (
        product_file.parent
    )

    preferred_board_configs = (
        product_root
        / "BoardConfig.mk",
        product_root
        / probe.device
        / "BoardConfig.mk",
    )

    board_config = next(
        (
            candidate
            for candidate
            in preferred_board_configs
            if candidate.is_file()
        ),
        None,
    )

    if board_config is None:
        discovered = sorted(
            (
                candidate.resolve()
                for candidate
                in product_root.rglob(
                    "BoardConfig.mk"
                )
                if candidate.is_file()
            ),
            key=lambda candidate: (
                len(candidate.parts),
                candidate.as_posix(),
            ),
        )

        if len(discovered) == 1:
            board_config = (
                discovered[0]
            )

        elif not discovered:
            raise RuntimeError(
                "no BoardConfig.mk found "
                "beneath selected product root: "
                f"{product_root}"
            )

        else:
            raise RuntimeError(
                "selected product has ambiguous "
                "BoardConfig.mk candidates: "
                f"{discovered!r}"
            )

    safe_device = re.sub(
        r"[^A-Za-z0-9_.+-]",
        "_",
        probe.device,
    )

    provider_root = (
        aosp_root
        / "vendor"
        / "treeforge"
        / "build-signing"
        / safe_device
    )

    if provider_root.exists():
        raise RuntimeError(
            "temporary TreeForge signing "
            "provider already exists: "
            f"{provider_root}"
        )

    avb_root = (
        provider_root
        / "avb"
    )

    avb_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    relative = (
        provider_root
        .relative_to(
            aosp_root
        )
        .as_posix()
    )

    for entry in profile.entries:
        source = (
            key_by_partition[
                entry.partition_name
            ]
        )

        destination = (
            avb_root
            / f"{entry.partition_name}.pem"
        )

        shutil.copy2(
            source,
            destination,
        )

        destination.chmod(
            0o600
        )

    provider_lines = [
        "# Generated temporarily by TreeForge Build.",
        "# Removed automatically after the build.",
        "",
        "BOARD_AVB_ENABLE := true",
        "",
    ]

    for entry in sorted(
        profile.entries,
        key=lambda item:
        item.partition_name,
    ):
        prefix = (
            _avb_board_variable_prefix(
                entry.partition_name
            )
        )

        provider_lines.extend(
            [
                (
                    f"{prefix}_KEY_PATH := "
                    f"{relative}/avb/"
                    f"{entry.partition_name}.pem"
                ),
                (
                    f"{prefix}_ALGORITHM := "
                    f"{entry.algorithm}"
                ),
                "",
            ]
        )

    provider_config = (
        provider_root
        / "BoardConfig.mk"
    )

    provider_config.write_text(
        "\n".join(
            provider_lines
        ),
        encoding="utf-8",
    )

    original = (
        board_config.read_bytes()
    )

    include_line = (
        f"include {relative}/BoardConfig.mk"
    )

    original_text = (
        original.decode(
            "utf-8"
        )
    )

    if include_line in original_text:
        raise RuntimeError(
            "temporary TreeForge AVB "
            "include already exists in "
            f"{board_config}"
        )

    updated = original_text

    if (
        updated
        and not updated.endswith("\n")
    ):
        updated += "\n"

    updated += (
        "\n"
        "# TreeForge temporary AVB build provider.\n"
        f"{include_line}\n"
    )

    board_config.write_text(
        updated,
        encoding="utf-8",
    )

    typer.echo(
        "Composed TreeForge AVB signing "
        "into the selected BoardConfig."
    )

    generated_count = 0

    for entry in sorted(
        profile.entries,
        key=lambda item:
        item.partition_name,
    ):
        key = (
            key_by_partition[
                entry.partition_name
            ]
        )

        typer.echo(
            f"  {entry.partition_name}: "
            f"{relative}/avb/"
            f"{entry.partition_name}.pem "
            f"({entry.algorithm})"
        )

    try:
        yield

    finally:
        board_config.write_bytes(
            original
        )

        shutil.rmtree(
            provider_root,
            ignore_errors=False,
        )

        for parent in (
            provider_root.parent,
            provider_root.parent.parent,
        ):
            try:
                parent.rmdir()
            except OSError:
                break

        typer.echo(
            "Restored BoardConfig after "
            "TreeForge AVB build composition."
        )



def _verify_treeforge_product_avb(
    *,
    aosp_root: Path,
    target: LunchTarget,
    device: str,
    product_out: Path,
    probe: TargetProbe | None = None,
    report_path: Path | None = None,
) -> dict[str, str]:
    """
    Verify the complete built TreeForge AVB acceptance contract.

    Install must only be offered after this succeeds.
    """

    if probe is None:
        probe = _probe_target(
            aosp_root,
            target,
        )

    if probe.device != device:
        raise RuntimeError(
            "AVB verification device "
            "identity mismatch: "
            f"probe={probe.device!r}, "
            f"requested={device!r}"
        )

    profile = (
        _treeforge_build_avb_profile(
            probe
        )
    )

    graph = (
        _verify_treeforge_avb_graph(
            aosp_root=aosp_root,
            probe=probe,
            target=target,
            product_out=product_out,
        )
    )

    verified = {
        node["partition"]:
        node["key_sha1"]
        for node in graph[
            "nodes"
        ]
    }

    expected = {
        entry.partition_name
        for entry in profile.entries
    }

    if set(verified) != expected:
        raise RuntimeError(
            "AVB graph verification "
            "coverage does not match "
            "the TreeForge signing "
            "profile"
        )

    if report_path is not None:
        _write_treeforge_avb_report(
            report_path=report_path,
            profile=profile,
            graph=graph,
        )

    return verified





def _key_profile_id(device: str) -> str:
    return f"android-build-development/{device}"


def _certificate_dir(device: str) -> Path:
    return (
        TREEFORGE_ROOT
        / ".treeforge-private"
        / "keys"
        / "android-build"
        / device
        / "certs"
    )


def _ensure_android_certificate_pair(
    base: Path,
    common_name: str,
) -> None:
    pk8 = base.with_suffix(".pk8")
    x509 = base.with_suffix(".x509.pem")
    if pk8.is_file() and x509.is_file():
        return

    if shutil.which("openssl") is None:
        raise RuntimeError(
            "openssl is required to provision TreeForge build certificates"
        )

    base.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="treeforge-cert-"
    ) as temporary:
        private_pem = Path(temporary) / "private.pem"
        subprocess.run(
            ["openssl", "genrsa", "-out", str(private_pem), "2048"],
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "openssl",
                "req",
                "-new",
                "-x509",
                "-key",
                str(private_pem),
                "-out",
                str(x509),
                "-days",
                "10000",
                "-subj",
                f"/CN={common_name}/O=TreeForge/C=US",
            ],
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "openssl",
                "pkcs8",
                "-in",
                str(private_pem),
                "-topk8",
                "-outform",
                "DER",
                "-out",
                str(pk8),
                "-nocrypt",
            ],
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )

    os.chmod(pk8, 0o600)
    os.chmod(x509, 0o600)


def _ensure_treeforge_build_certs(device: str) -> Path:
    root = _certificate_dir(device)
    labels = (
        "releasekey",
        "platform",
        "shared",
        "media",
        "networkstack",
    )
    for label in labels:
        _ensure_android_certificate_pair(
            root / label,
            f"TreeForge Development {label}",
        )
    return root


def _safe_key_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def _ensure_apex_payload_key(
    *,
    device: str,
    apex_name: str,
) -> Path:
    if shutil.which("openssl") is None:
        raise RuntimeError(
            "openssl is required to provision TreeForge APEX keys"
        )
    root = (
        TREEFORGE_ROOT
        / ".treeforge-private"
        / "keys"
        / "android-build"
        / device
        / "apex"
    )
    root.mkdir(parents=True, exist_ok=True)
    key = root / f"{_safe_key_name(apex_name)}.pem"
    if not key.is_file():
        subprocess.run(
            ["openssl", "genrsa", "-out", str(key), "4096"],
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
        )
        os.chmod(key, 0o600)
    return key


def _metadata_lines(
    target_files: Path,
    member: str,
) -> list[str]:
    with zipfile.ZipFile(target_files) as archive:
        try:
            data = archive.read(member)
        except KeyError:
            return []
    return data.decode("utf-8", errors="replace").splitlines()


def _parse_assignment_tokens(line: str) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        pieces = shlex.split(line, comments=False, posix=True)
    except ValueError:
        return result
    for piece in pieces:
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        result[key] = value
    return result


def _treeforge_signing_arguments(
    *,
    aosp_root: Path,
    target_files: Path,
    device: str,
) -> list[str]:
    certs = _ensure_treeforge_build_certs(device)
    command: list[str] = [
        "-d",
        str(certs),
        "-o",
    ]

    # Map non-standard APK certificate bases to TreeForge development keys.
    seen_key_map: set[str] = set()
    for line in _metadata_lines(target_files, "META/apkcerts.txt"):
        fields = _parse_assignment_tokens(line)
        certificate = fields.get("certificate", "")
        if not certificate or certificate == "PRESIGNED":
            continue
        basename = Path(certificate).name
        if basename in {
            "releasekey",
            "testkey",
            "platform",
            "shared",
            "media",
        }:
            continue
        destination = (
            certs / "networkstack"
            if basename == "networkstack"
            else certs / "releasekey"
        )
        if certificate not in seen_key_map:
            command.extend(
                ["-k", f"{certificate}={destination}"]
            )
            seen_key_map.add(certificate)

    # Re-sign non-presigned APEX payloads and containers.
    for line in _metadata_lines(target_files, "META/apexkeys.txt"):
        fields = _parse_assignment_tokens(line)
        name = fields.get("name", "")
        private_key = fields.get("private_key", "")
        container_key = fields.get("container_private_key", "")
        if not name:
            continue
        if private_key and private_key != "PRESIGNED":
            payload_key = _ensure_apex_payload_key(
                device=device,
                apex_name=name,
            )
            command.extend(
                [
                    "--extra_apex_payload_key",
                    f"{name}={payload_key}",
                ]
            )
        if container_key and container_key != "PRESIGNED":
            command.extend(
                [
                    "--extra_apks",
                    f"{name}={certs / 'releasekey'}",
                ]
            )

    # Force the final AVB profile to the TreeForge development keys.
    flag_names = {
        "vbmeta": "vbmeta",
        "boot": "boot",
        "init_boot": "init_boot",
        "vbmeta_system": "vbmeta_system",
        "vbmeta_vendor": "vbmeta_vendor",
    }
    for partition, prefix in flag_names.items():
        key = _treeforge_avb_key(device, partition)
        algorithm = TREEFORGE_AVB_ALGORITHMS[partition]
        command.extend(
            [
                f"--avb_{prefix}_key",
                str(key),
                f"--avb_{prefix}_algorithm",
                algorithm,
            ]
        )
    return command


def _find_target_files(
    product_out: Path,
) -> Path:
    """
    Resolve the AOSP target-files package deterministically.

    Android 15 places the archive directly beneath:
      PRODUCT_OUT/obj/PACKAGING/target_files_intermediates/
    """

    root = (
        product_out
        / "obj"
        / "PACKAGING"
        / "target_files_intermediates"
    )

    if not root.is_dir():
        raise RuntimeError(
            "target-files intermediates directory "
            f"does not exist: {root}"
        )

    candidates = sorted(
        (
            path
            for path in root.glob(
                "*-target_files.zip"
            )
            if path.is_file()
        ),
        key=lambda path: (
            path.stat().st_mtime_ns,
            path.name,
        ),
        reverse=True,
    )

    if not candidates:
        candidates = sorted(
            (
                path
                for path in root.glob(
                    "*.zip"
                )
                if (
                    path.is_file()
                    and "target_files"
                    in path.name
                )
            ),
            key=lambda path: (
                path.stat().st_mtime_ns,
                path.name,
            ),
            reverse=True,
        )

    if not candidates:
        raise RuntimeError(
            "target-files package was not "
            f"produced under {root}"
        )

    return candidates[0]



def _run_pty_command(
    *,
    command: list[str],
    cwd: Path,
    log_path: Path,
    append: bool = False,
) -> None:
    """
    Run one command with stdout/stderr attached to a PTY.

    AOSP/Ninja therefore retains its native elapsed-time, in-place and
    stacked-job terminal renderer while TreeForge records the same stream.
    """

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master_fd, slave_fd = (
        pty.openpty()
    )

    try:
        terminal_size = (
            shutil.get_terminal_size(
                fallback=(120, 40)
            )
        )

        winsize = struct.pack(
            "HHHH",
            terminal_size.lines,
            terminal_size.columns,
            0,
            0,
        )

        fcntl.ioctl(
            slave_fd,
            termios.TIOCSWINSZ,
            winsize,
        )

        env = os.environ.copy()

        if not env.get("TERM"):
            env["TERM"] = (
                "xterm-256color"
            )

        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
        )

    finally:
        os.close(
            slave_fd
        )

    mode = (
        "ab"
        if append
        else "wb"
    )

    try:
        with log_path.open(
            mode
        ) as log_stream:
            while True:
                try:
                    chunk = os.read(
                        master_fd,
                        65536,
                    )

                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break

                    raise

                if not chunk:
                    break

                log_stream.write(
                    chunk
                )
                log_stream.flush()

                terminal = getattr(
                    sys.stdout,
                    "buffer",
                    None,
                )

                if terminal is not None:
                    terminal.write(
                        chunk
                    )
                    terminal.flush()

                else:
                    sys.stdout.write(
                        chunk.decode(
                            "utf-8",
                            errors="replace",
                        )
                    )
                    sys.stdout.flush()

    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()

        raise

    finally:
        os.close(
            master_fd
        )

    returncode = (
        process.wait()
    )

    if returncode != 0:
        raise subprocess.CalledProcessError(
            returncode,
            command,
        )



def _run_aosp_build(
    *,
    aosp_root: Path,
    target: LunchTarget,
    jobs: int,
    log_path: Path,
    kernel_runtime: dict[str, object] | None = None,
) -> None:
    """
    Build Android normally.

    TreeForge kernel integration, when selected, has already projected
    its inputs into AOSP's canonical TARGET_KERNEL_DIR. No final image
    is replaced after this function runs.
    """

    body_lines = [
        "set -e",
        "set -o pipefail",
        "source build/envsetup.sh",
        f"lunch {shlex.quote(target.raw)}",
    ]

    if kernel_runtime is not None:
        mode = kernel_runtime.get(
            "mode"
        )

        expected_dir = kernel_runtime.get(
            "target_kernel_dir"
        )

        if mode not in (
            "aosp",
            "prebuilt",
        ):
            raise RuntimeError(
                "invalid TreeForge kernel runtime mode: "
                f"{mode!r}"
            )

        if (
            not isinstance(
                expected_dir,
                str,
            )
            or not expected_dir
        ):
            raise RuntimeError(
                "TreeForge kernel runtime has no "
                "TARGET_KERNEL_DIR identity"
            )

        expected_shell = shlex.quote(
            expected_dir
        )

        body_lines.extend(
            [
                (
                    'treeforge_kernel_dir="$('
                    'get_build_var TARGET_KERNEL_DIR'
                    ')"'
                ),
                (
                    'if [ "$treeforge_kernel_dir" != '
                    f'{expected_shell} ]; then '
                    'echo "TreeForge canonical kernel '
                    'projection was not selected" >&2; '
                    'echo "expected: '
                    f'{expected_dir}" >&2; '
                    'echo "actual: $treeforge_kernel_dir" >&2; '
                    "exit 1; fi"
                ),
            ]
        )

        if mode == "aosp":
            body_lines.extend(
                [
                    (
                        'treeforge_prebuilt_boot="$('
                        'get_build_var BOARD_PREBUILT_BOOTIMAGE'
                        ')"'
                    ),
                    (
                        'if [ -n "$treeforge_prebuilt_boot" ]; then '
                        'echo "TreeForge AOSP-built mode still has '
                        'BOARD_PREBUILT_BOOTIMAGE active: '
                        '$treeforge_prebuilt_boot" >&2; '
                        "exit 1; fi"
                    ),
                    (
                        'treeforge_target_no_kernel="$('
                        'get_build_var TARGET_NO_KERNEL'
                        ')"'
                    ),
                    (
                        'if [ "$treeforge_target_no_kernel" = "true" ]; '
                        'then echo "TARGET_NO_KERNEL must be false in '
                        'TreeForge AOSP-built mode" >&2; exit 1; fi'
                    ),
                    (
                        'test -f "$TARGET_KERNEL_DIR/Image.lz4" '
                        '|| { echo "TreeForge Image.lz4 missing" >&2; '
                        "exit 1; }"
                    ),
                    (
                        'test -f "$TARGET_KERNEL_DIR/fips140.ko" '
                        '|| { echo "TreeForge provider-only '
                        'fips140.ko missing" >&2; exit 1; }'
                    ),
                    (
                        'test ! -e "$TARGET_KERNEL_DIR/boot.img" '
                        '|| { echo "TreeForge boot.img prebuilt '
                        'shortcut leaked into AOSP-built mode" >&2; '
                        "exit 1; }"
                    ),
                    (
                        'test ! -e "$TARGET_KERNEL_DIR/'
                        'vendor_kernel_boot.img" '
                        '|| { echo "TreeForge vendor_kernel_boot.img '
                        'shortcut leaked into AOSP-built mode" >&2; '
                        "exit 1; }"
                    ),
                    (
                        'test ! -e "$TARGET_KERNEL_DIR/vendor_dlkm.img" '
                        '|| { echo "TreeForge vendor_dlkm.img shortcut '
                        'leaked into AOSP-built mode" >&2; exit 1; }'
                    ),
                    (
                        'test ! -e "$TARGET_KERNEL_DIR/system_dlkm.img" '
                        '|| { echo "TreeForge system_dlkm.img shortcut '
                        'leaked into AOSP-built mode" >&2; exit 1; }'
                    ),
                ]
            )

        else:
            body_lines.extend(
                [
                    (
                        'test -f "$TARGET_KERNEL_DIR/boot.img" '
                        '|| { echo "TreeForge prebuilt boot.img '
                        'missing" >&2; exit 1; }'
                    ),
                    (
                        'test -f "$TARGET_KERNEL_DIR/'
                        'vendor_kernel_boot.img" '
                        '|| { echo "TreeForge prebuilt '
                        'vendor_kernel_boot.img missing" >&2; exit 1; }'
                    ),
                    (
                        'test -f "$TARGET_KERNEL_DIR/vendor_dlkm.img" '
                        '|| { echo "TreeForge prebuilt vendor_dlkm.img '
                        'missing" >&2; exit 1; }'
                    ),
                    (
                        'test -f "$TARGET_KERNEL_DIR/system_dlkm.img" '
                        '|| { echo "TreeForge prebuilt system_dlkm.img '
                        'missing" >&2; exit 1; }'
                    ),
                ]
            )

    body_lines.append(
        f"m -j{jobs}"
    )

    body = "\n".join(
        body_lines
    )

    _run_pty_command(
        command=[
            "bash",
            "-lc",
            body,
        ],
        cwd=aosp_root,
        log_path=log_path,
        append=False,
    )






def _run_release_artifacts(
    *,
    aosp_root: Path,
    target: LunchTarget,
    jobs: int,
    log_path: Path,
) -> None:
    """
    Optionally generate target-files + otatools after the device build.
    """

    body = "\n".join(
        [
            "set -e",
            "set -o pipefail",
            "source build/envsetup.sh",
            f"lunch {shlex.quote(target.raw)}",
            (
                f"m -j{jobs} "
                "target-files-package "
                "otatools-package"
            ),
        ]
    )

    _run_pty_command(
        command=[
            "bash",
            "-lc",
            body,
        ],
        cwd=aosp_root,
        log_path=log_path,
        append=True,
    )



def _resolve_product_out(
    *,
    aosp_root: Path,
    target: LunchTarget,
) -> Path:
    body = "\n".join(
        [
            "set -e",
            "source build/envsetup.sh >/dev/null",
            f"lunch {shlex.quote(target.raw)} >/dev/null",
            "get_build_var PRODUCT_OUT",
        ]
    )
    raw = _bash_capture(aosp_root, body).strip().splitlines()[-1]
    path = Path(raw)
    if not path.is_absolute():
        path = aosp_root / path
    return path.resolve()


def _host_tool(
    *,
    aosp_root: Path,
    target: LunchTarget,
    name: str,
) -> Path:
    body = "\n".join(
        [
            "set -e",
            "source build/envsetup.sh >/dev/null",
            f"lunch {shlex.quote(target.raw)} >/dev/null",
            "get_build_var HOST_OUT_EXECUTABLES",
        ]
    )
    raw = _bash_capture(aosp_root, body).strip().splitlines()[-1]
    root = Path(raw)
    if not root.is_absolute():
        root = aosp_root / root
    tool = root / name
    if not tool.is_file():
        raise RuntimeError(
            f"AOSP host tool was not produced: {tool}"
        )
    return tool.resolve()


def _sign_treeforge_release(
    *,
    aosp_root: Path,
    target: LunchTarget,
    device: str,
    report_root: Path,
) -> tuple[Path, Path]:
    product_out = _resolve_product_out(
        aosp_root=aosp_root,
        target=target,
    )
    unsigned = _find_target_files(product_out)
    signer = _host_tool(
        aosp_root=aosp_root,
        target=target,
        name="sign_target_files_apks",
    )
    image_tool = _host_tool(
        aosp_root=aosp_root,
        target=target,
        name="img_from_target_files",
    )

    signed = report_root / "signed-target_files.zip"
    images = report_root / "signed-images.zip"

    command = [
        str(signer),
        *_treeforge_signing_arguments(
            aosp_root=aosp_root,
            target_files=unsigned,
            device=device,
        ),
        str(unsigned),
        str(signed),
    ]
    subprocess.run(
        command,
        cwd=str(aosp_root),
        text=True,
        check=True,
    )
    subprocess.run(
        [
            str(image_tool),
            str(signed),
            str(images),
        ],
        cwd=str(aosp_root),
        text=True,
        check=True,
    )
    return signed, images


def _write_report(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


BUILD_SELECTION_SCHEMA_VERSION = 2

BUILD_SELECTION_STATE = (
    TREEFORGE_ROOT
    / ".treeforge"
    / "state"
    / "build-selection.json"
)

VALID_LUNCH_SOURCES = (
    "aosp",
    "treeforge",
)


def _lunch_source_for_target(
    target: LunchTarget,
) -> str:
    if target.product.startswith(
        "treeforge_"
    ):
        return "treeforge"

    return "aosp"


def _normalize_lunch_source(
    value: str | None,
) -> str | None:
    return _normalize_choice(
        value,
        VALID_LUNCH_SOURCES,
        "--lunch-source",
    )


def _lunch_targets_for_source(
    aosp_root: Path,
    source: str,
) -> list[LunchTarget]:
    return [
        target
        for target
        in _common_lunch_targets(
            aosp_root
        )
        if (
            _lunch_source_for_target(
                target
            )
            == source
        )
    ]


def _select_lunch_source(
    aosp_root: Path,
) -> str:
    return _select_numbered(
        "Lunch source",
        [
            (
                "aosp",
                "AOSP "
                f"({len(_lunch_targets_for_source(aosp_root, 'aosp'))} "
                "discovered)",
            ),
            (
                "treeforge",
                "TreeForge "
                f"({len(_lunch_targets_for_source(aosp_root, 'treeforge'))} "
                "discovered)",
            ),
        ],
        1,
    )


def _select_lunch_for_source(
    aosp_root: Path,
    source: str,
) -> LunchTarget:
    discovered = (
        _lunch_targets_for_source(
            aosp_root,
            source,
        )
    )

    label = (
        "TreeForge"
        if source == "treeforge"
        else "AOSP"
    )

    if not discovered:
        raise RuntimeError(
            f"no {label} lunch combinations "
            "were discovered under aosp/device"
        )

    choice = _select_item(
        f"{label} lunch combinations",
        [
            target.raw
            for target in discovered
        ],
        default=1,
    )

    return LunchTarget.parse(
        choice
    )


def _saved_lunch_available(
    *,
    aosp_root: Path,
    source: str,
    raw: str,
) -> bool:
    return any(
        target.raw == raw
        for target
        in _lunch_targets_for_source(
            aosp_root,
            source,
        )
    )


def _load_build_selection(
    path: Path = BUILD_SELECTION_STATE,
) -> dict[str, object] | None:
    if not path.is_file():
        return None

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if not isinstance(
        payload,
        dict,
    ):
        return None

    if payload.get(
        "schema_version"
    ) != BUILD_SELECTION_SCHEMA_VERSION:
        return None

    return payload


def _save_build_selection(
    selection: dict[str, object],
    path: Path = BUILD_SELECTION_STATE,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = dict(
        selection
    )

    payload["schema_version"] = (
        BUILD_SELECTION_SCHEMA_VERSION
    )

    temporary = path.with_name(
        path.name + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )


def _saved_text(
    state: dict[str, object] | None,
    key: str,
) -> str | None:
    if state is None:
        return None

    value = state.get(
        key
    )

    if not isinstance(
        value,
        str,
    ):
        return None

    value = value.strip()

    return value or None


def _saved_choice(
    state: dict[str, object] | None,
    key: str,
    allowed: tuple[str, ...],
) -> str | None:
    value = _saved_text(
        state,
        key,
    )

    if value in allowed:
        return value

    return None


def _saved_bool(
    state: dict[str, object] | None,
    key: str,
) -> bool | None:
    if state is None:
        return None

    value = state.get(
        key
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    return None


def _saved_jobs(
    state: dict[str, object] | None,
) -> int | None:
    if state is None:
        return None

    value = state.get(
        "jobs"
    )

    if (
        isinstance(value, int)
        and value >= 1
    ):
        return value

    return None


def _print_previous_build_selection(
    state: dict[str, object],
) -> None:
    typer.echo("")
    typer.echo(
        "Previous build choices found:"
    )
    typer.echo("")

    rows = (
        (
            "Lunch source",
            state.get(
                "lunch_source",
                "n/a",
            ),
        ),
        (
            "Lunch",
            state.get(
                "lunch",
                "n/a",
            ),
        ),
        (
            "Kernel / boot",
            state.get(
                "kernel",
                "n/a",
            ),
        ),
        (
            "Kernel profile",
            state.get(
                "kernel_profile",
                "n/a",
            )
            or "n/a",
        ),
        (
            "Device tools",
            state.get(
                "device_tools",
                "n/a",
            ),
        ),
        (
            "GApps",
            state.get(
                "gapps",
                "n/a",
            ),
        ),
        (
            "AVB signing",
            state.get(
                "signing",
                "n/a",
            ),
        ),
        (
            "Release artifacts",
            (
                "Yes"
                if state.get(
                    "release_artifacts"
                )
                else "No"
            ),
        ),
        (
            "Release signing",
            (
                "Yes"
                if state.get(
                    "release_signing"
                )
                else "No"
            ),
        ),
        (
            "Jobs",
            state.get(
                "jobs",
                "n/a",
            ),
        ),
    )

    for label, value in rows:
        typer.echo(
            f"  {label + ':':20} {value}"
        )


def _install_handoff_command(
    product_out: Path,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "treeforge",
        "install",
        "--input",
        str(
            product_out.resolve()
        ),
    ]


def _handoff_to_install(
    product_out: Path,
) -> int:
    command = (
        _install_handoff_command(
            product_out
        )
    )

    typer.echo("")
    typer.echo(
        "Handing off to TreeForge Install..."
    )
    typer.echo(
        f"  Input: {product_out.resolve()}"
    )

    completed = subprocess.run(
        command,
        cwd=str(
            TREEFORGE_ROOT
        ),
    )

    if completed.returncode != 0:
        typer.echo(
            "TreeForge Install exited with "
            f"status {completed.returncode}. "
            "The Android build itself remains complete.",
            err=True,
        )

    return completed.returncode


@app.callback(invoke_without_command=True)
def build(
    lunch_source: str | None = typer.Option(
        None,
        "--lunch-source",
        help=(
            "Lunch family: aosp or treeforge. "
            "TreeForge products use treeforge_<device>."
        ),
    ),
    lunch: str | None = typer.Option(
        None,
        "--lunch",
        help=(
            "Explicit PRODUCT-RELEASE-VARIANT "
            "lunch target."
        ),
    ),
    list_lunch: bool = typer.Option(
        False,
        "--list-lunch",
        help=(
            "List discovered lunch combinations."
        ),
    ),
    kernel_source: str | None = typer.Option(
        None,
        "--kernel",
        help=(
            "Kernel provider: treeforge-release, "
            "treeforge-local, treeforge-build, or aosp."
        ),
    ),
    boot_image: Path | None = typer.Option(
        None,
        "--boot-image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help=(
            "Legacy boot.img override. TreeForge "
            "provider bundles use --kernel-provider-path."
        ),
    ),
    kernel_provider_path: Path | None = typer.Option(
        None,
        "--kernel-provider-path",
        exists=True,
        readable=True,
        resolve_path=True,
        help=(
            "TreeForge kernel provider directory or "
            "manifest.json for --kernel treeforge-local "
            "or treeforge-release."
        ),
    ),
    kernel_release_tag: str | None = typer.Option(
        None,
        "--kernel-release-tag",
        help=(
            "Exact TreeForge kernel GitHub release tag "
            "for --kernel treeforge-release."
        ),
    ),
    kernel_root: Path = typer.Option(
        _kernel_root_default(),
        "--kernel-root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "TreeForge custom-kernel repository root."
        ),
    ),
    kernel_profile: str | None = typer.Option(
        None,
        "--kernel-profile",
        help=(
            "TreeForge kernel profile for "
            "--kernel treeforge-build."
        ),
    ),
    kernel_mode: str | None = typer.Option(
        None,
        "--kernel-mode",
        help=(
            "TreeForge Kernel integration mode: "
            "aosp or prebuilt. "
            "Default: aosp."
        ),
    ),
    kernel_input: str | None = typer.Option(
        None,
        "--kernel-input",
        help=(
            "TreeForge Kernel acquisition: "
            "build, local, or release. "
            "Default: build."
        ),
    ),
    kernel_variant: str | None = typer.Option(
        None,
        "--kernel-variant",
        help=(
            "TreeForge Kernel variant. Values are "
            "discovered from ./kernel build/prebuilts."
        ),
    ),
    gapps: str | None = typer.Option(
        None,
        "--gapps",
        help=(
            "Google Apps provider: "
            "none or mindthegapps."
        ),
    ),
    signing: str | None = typer.Option(
        None,
        "--signing",
        help=(
            "AVB build signing provider: "
            "treeforge or aosp."
        ),
    ),
    device_tools: str | None = typer.Option(
        None,
        "--device-tools",
        help=(
            "Host ADB/Fastboot provider: "
            "treeforge or aosp."
        ),
    ),
    release_artifacts: bool | None = typer.Option(
        None,
        "--release-artifacts/--no-release-artifacts",
        help=(
            "Also build target-files and otatools. "
            "Default: no."
        ),
    ),
    release_signing: bool | None = typer.Option(
        None,
        "--release-signing/--no-release-signing",
        help=(
            "Also perform full TreeForge "
            "APK/APEX/OTA release re-signing. "
            "Requires release artifacts."
        ),
    ),
    jobs: int | None = typer.Option(
        None,
        "--jobs",
        "-j",
        min=1,
        help=(
            "Parallel AOSP build jobs. Default: 8."
        ),
    ),
    aosp_root: Path = typer.Option(
        AOSP_ROOT,
        "--aosp-root",
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help=(
            "AOSP checkout root."
        ),
    ),
    plan_only: bool = typer.Option(
        False,
        "--plan-only",
        help=(
            "Print the resolved plan without building."
        ),
    ),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help=(
            "Do not prompt for choices."
        ),
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help=(
            "Skip the Build confirmation only. "
            "Never authorizes installation."
        ),
    ),
) -> None:
    """
    Build Android from TreeForge's repo-local AOSP workspace.
    """

    try:
        root = _validate_aosp_root(
            aosp_root
        )

        requested_source = (
            _normalize_lunch_source(
                lunch_source
            )
        )

        if list_lunch:
            targets = (
                _common_lunch_targets(
                    root
                )
            )

            if requested_source:
                targets = [
                    target
                    for target in targets
                    if (
                        _lunch_source_for_target(
                            target
                        )
                        == requested_source
                    )
                ]

            for target in targets:
                typer.echo(
                    target.raw
                )

            return

        _reject_source_root_product_outputs(
            root
        )

        previous: dict[
            str,
            object,
        ] | None = None

        if not non_interactive:
            candidate = (
                _load_build_selection()
            )

            if candidate is not None:
                saved_root = (
                    _saved_text(
                        candidate,
                        "aosp_root",
                    )
                )

                if (
                    saved_root is None
                    or Path(
                        saved_root
                    ).resolve()
                    == root.resolve()
                ):
                    _print_previous_build_selection(
                        candidate
                    )

                    typer.echo("")

                    if typer.confirm(
                        "Use previous build choices?",
                        default=True,
                    ):
                        previous = candidate

        selected_source = (
            requested_source
        )

        selected_lunch: (
            LunchTarget | None
        ) = None

        if lunch is not None:
            selected_lunch = (
                LunchTarget.parse(
                    lunch
                )
            )

            actual_source = (
                _lunch_source_for_target(
                    selected_lunch
                )
            )

            if (
                selected_source is not None
                and selected_source
                != actual_source
            ):
                raise typer.BadParameter(
                    "--lunch-source does not "
                    "match --lunch"
                )

            selected_source = (
                actual_source
            )

        elif previous is not None:
            saved_raw = (
                _saved_text(
                    previous,
                    "lunch",
                )
            )

            saved_source = (
                _saved_choice(
                    previous,
                    "lunch_source",
                    VALID_LUNCH_SOURCES,
                )
            )

            if (
                saved_raw
                and saved_source
                and (
                    selected_source is None
                    or selected_source
                    == saved_source
                )
                and _saved_lunch_available(
                    aosp_root=root,
                    source=saved_source,
                    raw=saved_raw,
                )
            ):
                selected_lunch = (
                    LunchTarget.parse(
                        saved_raw
                    )
                )

                selected_source = (
                    saved_source
                )

            elif saved_raw:
                typer.echo("")
                typer.echo(
                    "Saved lunch combination is "
                    "no longer available for the "
                    "selected lunch source."
                )

        if selected_lunch is None:
            if non_interactive:
                raise typer.BadParameter(
                    "--lunch is required with "
                    "--non-interactive"
                )

            if selected_source is None:
                selected_source = (
                    _select_lunch_source(
                        root
                    )
                )

            selected_lunch = (
                _select_lunch_for_source(
                    root,
                    selected_source,
                )
            )

        assert selected_source is not None

        probe = _probe_target(
            root,
            selected_lunch,
        )


        android_platform_release = (
            _checkout_android_platform_tag(
                root
            )
        )

        platform_release = (
            _checkout_platform_release(
                root
            )
        )

        treeforge_kernel_profiles = (
            _treeforge_kernel_build_profiles(
                kernel_root=(
                    kernel_root
                    .expanduser()
                    .resolve()
                ),
                device=probe.device,
                aosp_release=(
                    android_platform_release
                ),
            )
        )

        treeforge_kernel_available = bool(
            treeforge_kernel_profiles
        )

        kernel_menu = list(
            _kernel_provider_menu(
                treeforge_available=(
                    treeforge_kernel_available
                ),
            )
        )

        kernel_value = (
            kernel_source
        )

        if (
            kernel_value is None
            and previous is not None
        ):
            kernel_value = (
                _saved_choice(
                    previous,
                    "kernel",
                    VALID_KERNEL_SOURCES,
                )
            )

        selected_kernel = (
            _normalize_choice(
                kernel_value,
                VALID_KERNEL_SOURCES,
                "--kernel",
            )
        )

        if (
            selected_kernel is not None
            and _is_treeforge_kernel_provider(
                selected_kernel
            )
            and not treeforge_kernel_available
        ):
            #
            # An explicit unsupported request is an error.
            #
            # A stale saved choice is discarded so interactive Build
            # can present only the providers currently supported for
            # the selected target.
            #
            if kernel_source is not None:
                _require_treeforge_kernel_capability(
                    provider=selected_kernel,
                    device=probe.device,
                    aosp_release=(
                        android_platform_release
                    ),
                    profiles=(
                        treeforge_kernel_profiles
                    ),
                )

            selected_kernel = None


        if selected_kernel is None:
            if non_interactive:
                raise typer.BadParameter(
                    "--kernel is required with "
                    "--non-interactive"
                )

            selected_kernel = (
                _select_numbered(
                    "Kernel provider",
                    kernel_menu,
                    2,
                )
            )

        if selected_kernel == "cancel":
            typer.echo("")
            typer.echo("Android build cancelled.")
            return

        selected_kernel = (
            _canonical_kernel_provider(
                selected_kernel
            )
        )

        _require_treeforge_kernel_capability(
            provider=selected_kernel,
            device=probe.device,
            aosp_release=(
                android_platform_release
            ),
            profiles=(
                treeforge_kernel_profiles
            ),
        )


        selected_kernel_mode: str | None = None

        if _is_treeforge_kernel_provider(
            selected_kernel
        ):
            selected_kernel_mode = (
                _normalize_choice(
                    kernel_mode,
                    VALID_TREEFORGE_KERNEL_MODES,
                    "--kernel-mode",
                )
            )

            if selected_kernel_mode is None:
                if non_interactive:
                    #
                    # Canonical TreeForge Android composition path.
                    #
                    selected_kernel_mode = "aosp"

                else:
                    selected_kernel_mode = (
                        _select_numbered(
                            "TreeForge kernel integration",
                            list(
                                _treeforge_kernel_mode_menu()
                            ),
                            1,
                        )
                    )

                    if (
                        selected_kernel_mode
                        == "cancel"
                    ):
                        typer.echo(
                            "Android build cancelled."
                        )
                        return

        elif kernel_mode is not None:
            raise typer.BadParameter(
                "--kernel-mode is only valid with "
                "TreeForge Kernel"
            )

        tools_value = device_tools

        if (
            tools_value is None
            and previous is not None
        ):
            tools_value = (
                _saved_choice(
                    previous,
                    "device_tools",
                    VALID_DEVICE_TOOLS,
                )
            )

        selected_device_tools = (
            _normalize_choice(
                tools_value,
                VALID_DEVICE_TOOLS,
                "--device-tools",
            )
        )

        if selected_device_tools is None:
            if non_interactive:
                raise typer.BadParameter(
                    "--device-tools is required "
                    "with --non-interactive"
                )

            selected_device_tools = (
                _select_numbered(
                    "ADB / Fastboot host tools",
                    [
                        (
                            "treeforge",
                            "TreeForge ADB / Fastboot",
                        ),
                        (
                            "aosp",
                            "AOSP-built ADB / Fastboot",
                        ),
                    ],
                    1,
                )
            )

        gapps_value = gapps

        if (
            gapps_value is None
            and previous is not None
        ):
            gapps_value = (
                _saved_choice(
                    previous,
                    "gapps",
                    VALID_GAPPS,
                )
            )

        selected_gapps = (
            _normalize_choice(
                gapps_value,
                VALID_GAPPS,
                "--gapps",
            )
        )

        if selected_gapps is None:
            if non_interactive:
                raise typer.BadParameter(
                    "--gapps is required with "
                    "--non-interactive"
                )

            selected_gapps = (
                _select_numbered(
                    "Google Apps composition",
                    [
                        (
                            "none",
                            "None",
                        ),
                        (
                            "mindthegapps",
                            "MindTheGapps Android 15 "
                            "/ VIC",
                        ),
                    ],
                    1,
                )
            )

        (
            device_tree_signing,
            signing_evidence,
        ) = (
            _detect_device_tree_signing_default(
                probe
            )
        )

        signing_value = signing

        if (
            signing_value is None
            and previous is not None
        ):
            signing_value = (
                _saved_choice(
                    previous,
                    "signing",
                    VALID_SIGNING,
                )
            )

        selected_signing = (
            _normalize_choice(
                signing_value,
                VALID_SIGNING,
                "--signing",
            )
        )

        if selected_signing is None:
            if non_interactive:
                raise typer.BadParameter(
                    "--signing is required with "
                    "--non-interactive"
                )

            treeforge_label = (
                "TreeForge AVB development keys"
            )

            aosp_label = (
                "AOSP AVB development/test keys"
            )

            default_choice = 1

            if device_tree_signing == "treeforge":
                treeforge_label += (
                    "  [Device Tree default]"
                )

            elif device_tree_signing == "aosp":
                aosp_label += (
                    "  [Device Tree default]"
                )
                default_choice = 2

            selected_signing = (
                _select_numbered(
                    "AVB build signing provider",
                    [
                        (
                            "treeforge",
                            treeforge_label,
                        ),
                        (
                            "aosp",
                            aosp_label,
                        ),
                    ],
                    default_choice,
                )
            )

        selected_profile = (
            kernel_profile
        )

        if (
            selected_profile is None
            and previous is not None
        ):
            selected_profile = (
                _saved_text(
                    previous,
                    "kernel_profile",
                )
            )

        if selected_kernel == "treeforge-build":
            profiles = (
                _kernel_profiles(
                    kernel_root
                    .expanduser()
                    .resolve(),
                    probe.device,
                )
            )

            if (
                selected_profile
                and selected_profile
                not in profiles
            ):
                selected_profile = None

            if selected_profile is None:
                if len(profiles) == 1:
                    selected_profile = (
                        profiles[0]
                    )

                elif non_interactive:
                    raise typer.BadParameter(
                        "--kernel-profile is "
                        "required with multiple "
                        "kernel profiles"
                    )

                elif profiles:
                    selected_profile = (
                        _select_item(
                            "TreeForge kernel profiles",
                            profiles,
                        )
                    )

                else:
                    raise RuntimeError(
                        "no TreeForge kernel profile "
                        f"found for {probe.device}"
                    )

        else:
            selected_profile = None


        selected_kernel_input: str | None = None
        selected_kernel_variant: str | None = None

        if selected_kernel == "treeforge-build":
            input_value = kernel_input

            if (
                input_value is None
                and previous is not None
            ):
                input_value = (
                    _saved_choice(
                        previous,
                        "kernel_input",
                        TREEFORGE_KERNEL_INPUT_VALUES,
                    )
                )

            if kernel_provider_path is not None:
                if (
                    input_value is not None
                    and input_value != "local"
                ):
                    raise typer.BadParameter(
                        "--kernel-provider-path requires "
                        "--kernel-input local"
                    )

                input_value = "local"

            if kernel_release_tag is not None:
                if (
                    input_value is not None
                    and input_value != "release"
                ):
                    raise typer.BadParameter(
                        "--kernel-release-tag requires "
                        "--kernel-input release"
                    )

                input_value = "release"

            selected_kernel_input = (
                _normalize_choice(
                    input_value,
                    TREEFORGE_KERNEL_INPUT_VALUES,
                    "--kernel-input",
                )
            )

            if selected_kernel_input is None:
                if non_interactive:
                    selected_kernel_input = "build"

                else:
                    selected_kernel_input = (
                        _select_numbered(
                            "TreeForge kernel input",
                            list(
                                _treeforge_kernel_input_menu()
                            ),
                            1,
                        )
                    )

                    if selected_kernel_input == "cancel":
                        typer.echo("")
                        typer.echo(
                            "Android build cancelled."
                        )
                        return

            requested_variant = kernel_variant

            if (
                requested_variant is None
                and previous is not None
            ):
                requested_variant = (
                    _saved_text(
                        previous,
                        "kernel_variant",
                    )
                )

            if selected_kernel_input == "build":
                assert selected_profile is not None

                available_variants = (
                    _treeforge_kernel_variants(
                        kernel_root=(
                            kernel_root
                            .expanduser()
                            .resolve()
                        ),
                        device=probe.device,
                        profile=selected_profile,
                        aosp_release=android_platform_release,
                    )
                )

                if not available_variants:
                    raise RuntimeError(
                        "TreeForge Kernel exposes no variant "
                        "accepted by both build and prebuilts "
                        f"for {probe.device}/{selected_profile}"
                    )

                if requested_variant is not None:
                    selected_kernel_variant = (
                        _normalize_choice(
                            requested_variant,
                            available_variants,
                            "--kernel-variant",
                        )
                    )

                if selected_kernel_variant is None:
                    if non_interactive:
                        selected_kernel_variant = (
                            "modified"
                            if "modified" in available_variants
                            else available_variants[0]
                        )

                    else:
                        menu = (
                            _treeforge_kernel_variant_menu(
                                available_variants
                            )
                        )

                        default_index = next(
                            (
                                index
                                for index, item
                                in enumerate(
                                    menu,
                                    start=1,
                                )
                                if item[0] == "modified"
                            ),
                            1,
                        )

                        selected_kernel_variant = (
                            _select_numbered(
                                "TreeForge kernel variant",
                                list(menu),
                                default_index,
                            )
                        )

                        if selected_kernel_variant == "cancel":
                            typer.echo("")
                            typer.echo(
                                "Android build cancelled."
                            )
                            return

            elif requested_variant is not None:
                selected_kernel_variant = (
                    requested_variant.strip()
                )

                if not selected_kernel_variant:
                    raise typer.BadParameter(
                        "--kernel-variant cannot be empty"
                    )

        elif (
            kernel_input is not None
            or kernel_variant is not None
            or kernel_provider_path is not None
            or kernel_release_tag is not None
        ):
            raise typer.BadParameter(
                "TreeForge kernel input/provider/variant "
                "options require --kernel treeforge-build"
            )


        selected_release_artifacts = (
            release_artifacts
        )

        if (
            selected_release_artifacts
            is None
            and previous is not None
        ):
            selected_release_artifacts = (
                _saved_bool(
                    previous,
                    "release_artifacts",
                )
            )

        if (
            selected_release_artifacts
            is None
        ):
            if non_interactive:
                selected_release_artifacts = (
                    False
                )

            else:
                typer.echo("")
                selected_release_artifacts = (
                    typer.confirm(
                        "Build release artifacts "
                        "(target-files + otatools)?",
                        default=False,
                    )
                )

        selected_release_signing = (
            release_signing
        )

        if (
            selected_release_signing
            is None
            and previous is not None
        ):
            selected_release_signing = (
                _saved_bool(
                    previous,
                    "release_signing",
                )
            )

        if selected_release_signing:
            selected_release_artifacts = True

        if (
            selected_release_signing
            and selected_signing
            != "treeforge"
        ):
            raise typer.BadParameter(
                "--release-signing requires "
                "--signing treeforge"
            )

        if (
            selected_release_signing
            is None
        ):
            if (
                selected_release_artifacts
                and selected_signing
                == "treeforge"
                and not non_interactive
            ):
                typer.echo("")
                selected_release_signing = (
                    typer.confirm(
                        "Also perform full "
                        "TreeForge APK/APEX/OTA "
                        "release re-signing?",
                        default=False,
                    )
                )

            else:
                selected_release_signing = (
                    False
                )

        resolved_jobs = jobs

        if (
            resolved_jobs is None
            and previous is not None
        ):
            resolved_jobs = (
                _saved_jobs(
                    previous
                )
            )

        if resolved_jobs is None:
            resolved_jobs = 8

        resolved_boot_image = (
            boot_image
        )

        if (
            resolved_boot_image is None
            and previous is not None
            and selected_kernel
            == "treeforge-output"
        ):
            saved_boot = (
                _saved_text(
                    previous,
                    "boot_image",
                )
            )

            if saved_boot:
                candidate = Path(
                    saved_boot
                ).expanduser()

                if candidate.is_file():
                    resolved_boot_image = (
                        candidate.resolve()
                    )

        typer.echo("")
        typer.echo(
            "TreeForge Android Build"
        )
        typer.echo("")
        typer.echo(
            f"  AOSP root:          {root}"
        )
        typer.echo(
            "  Android platform:   "
            + (
                android_platform_release
                or "not detected"
            )
        )
        typer.echo(
            "  Lunch release cfg:  "
            + (
                _checkout_platform_release(
                    root
                )
                or "not detected"
            )
        )
        typer.echo(
            f"  Lunch source:       "
            f"{selected_source}"
        )
        typer.echo(
            f"  Lunch:              "
            f"{selected_lunch.raw}"
        )
        typer.echo(
            f"  Device:             "
            f"{probe.device}"
        )
        typer.echo(
            f"  Architecture:       "
            f"{probe.arch}"
        )
        selected_boot_choice: Path | None = None
        aosp_prebuilt_boot: Path | None = None

        if boot_image is not None:
            raise typer.BadParameter(
                "--boot-image is a retired boot-only override. "
                "Use TreeForge Kernel with --kernel-mode prebuilt "
                "for coherent kernel-family prebuilts."
            )

        selected_kernel_provider: Path | None = None
        selected_kernel_bundle: dict[str, object] | None = None


        if (
            selected_kernel == "treeforge-build"
            and selected_kernel_input == "local"
        ):
            if kernel_release_tag is not None:
                raise typer.BadParameter(
                    "--kernel-release-tag is not valid "
                    "with --kernel-input local"
                )

            selected_kernel_provider = (
                _select_kernel_provider_bundle(
                    provider="treeforge-local",
                    device=probe.device,
                    explicit=kernel_provider_path,
                    non_interactive=non_interactive,
                )
            )

            selected_kernel_bundle = (
                _load_kernel_provider_bundle(
                    manifest_path=selected_kernel_provider,
                    device=probe.device,
                )
            )

        elif (
            selected_kernel == "treeforge-build"
            and selected_kernel_input == "release"
            and not plan_only
        ):
            if kernel_provider_path is not None:
                raise typer.BadParameter(
                    "--kernel-provider-path is not valid "
                    "with --kernel-input release"
                )

            release_tag = (
                _select_github_kernel_release(
                    device=probe.device,
                    explicit_tag=kernel_release_tag,
                    non_interactive=non_interactive,
                )
            )

            selected_kernel_provider = (
                _acquire_github_kernel_provider(
                    tag=release_tag,
                    device=probe.device,
                )
            )

            selected_kernel_bundle = (
                _load_kernel_provider_bundle(
                    manifest_path=selected_kernel_provider,
                    device=probe.device,
                )
            )

        if selected_kernel_bundle is not None:
            bundle_profile = (
                selected_kernel_bundle.get(
                    "android_profile"
                )
            )

            if (
                not isinstance(
                    bundle_profile,
                    str,
                )
                or not bundle_profile
            ):
                raise RuntimeError(
                    "TreeForge kernel provider has no "
                    "Android profile identity"
                )

            if (
                selected_profile is not None
                and bundle_profile != selected_profile
            ):
                raise RuntimeError(
                    "TreeForge kernel provider profile mismatch: "
                    f"selected {selected_profile!r}, "
                    f"provider reports {bundle_profile!r}"
                )

            selected_profile = bundle_profile

            bundle_variant = (
                _kernel_bundle_variant(
                    selected_kernel_bundle
                )
            )

            if bundle_variant is None:
                raise RuntimeError(
                    "TreeForge kernel provider has no "
                    "variant/source provenance"
                )

            if (
                selected_kernel_variant is not None
                and selected_kernel_variant != bundle_variant
            ):
                raise RuntimeError(
                    "TreeForge kernel provider variant mismatch: "
                    f"requested {selected_kernel_variant!r}, "
                    f"provider reports {bundle_variant!r}"
                )

            selected_kernel_variant = bundle_variant

        if selected_kernel in {
            "treeforge-local",
            "treeforge-release",
        }:
            if boot_image is not None:
                raise typer.BadParameter(
                    "--boot-image is not valid with "
                    "TreeForge kernel provider bundles; "
                    "use --kernel-provider-path"
                )

            if selected_kernel == "treeforge-release":
                if kernel_provider_path is not None:
                    raise typer.BadParameter(
                        "--kernel-provider-path cannot "
                        "be combined with "
                        "--kernel treeforge-release; "
                        "use --kernel-release-tag"
                    )

                release_tag = (
                    _select_github_kernel_release(
                        device=probe.device,
                        explicit_tag=kernel_release_tag,
                        non_interactive=non_interactive,
                    )
                )

                selected_kernel_provider = (
                    _acquire_github_kernel_provider(
                        tag=release_tag,
                        device=probe.device,
                    )
                )

            else:
                if kernel_release_tag is not None:
                    raise typer.BadParameter(
                        "--kernel-release-tag is only "
                        "valid with "
                        "--kernel treeforge-release"
                    )

                selected_kernel_provider = (
                    _select_kernel_provider_bundle(
                        provider=selected_kernel,
                        device=probe.device,
                        explicit=kernel_provider_path,
                        non_interactive=non_interactive,
                    )
                )

            selected_kernel_bundle = (
                _load_kernel_provider_bundle(
                    manifest_path=selected_kernel_provider,
                    device=probe.device,
                )
            )

            selected_profile = (
                selected_kernel_bundle.get(
                    "android_profile"
                )
                if isinstance(
                    selected_kernel_bundle.get(
                        "android_profile"
                    ),
                    str,
                )
                else None
            )

            selected_boot_choice = None
            resolved_boot_image = None

        elif selected_kernel == "aosp":
            resolved_boot_image = None
            selected_profile = None

            aosp_prebuilt_boot = (
                _validate_aosp_kernel_provider(
                    aosp_root=root,
                    probe=probe,
                    target=selected_lunch,
                )
            )

        elif selected_kernel == "treeforge-build":
            resolved_boot_image = None

        else:
            raise RuntimeError(
                "unhandled kernel provider: "
                f"{selected_kernel}"
            )

        if (
            selected_kernel == "treeforge-build"
            and selected_kernel_mode == "prebuilt"
            and selected_signing == "treeforge"
        ):
            raise typer.BadParameter(
                "TreeForge custom AVB signing cannot be combined "
                "with exact TreeForge prebuilt kernel images. "
                "Use --kernel-mode aosp so Android constructs and "
                "signs final images with the selected TreeForge keys."
            )

        typer.echo(
            f"  Kernel / boot:      "
            f"{selected_kernel}"
        )

        if selected_kernel_provider is not None:
            typer.echo(
                "  Kernel provider:   "
                f"{selected_kernel_provider}"
            )

        if selected_kernel_bundle is not None:
            typer.echo(
                "  Kernel generation: "
                f"{selected_kernel_bundle['generation']}"
            )

            provider_payload = json.loads(
                Path(
                    selected_kernel_bundle["manifest"]
                ).read_text()
            )

            release_tag = provider_payload.get(
                "release_tag"
            )

            if release_tag:
                typer.echo(
                    "  Kernel release:    "
                    f"{release_tag}"
                )

        if selected_boot_choice is not None:
            typer.echo(
                "  Kernel artifact:   "
                f"{selected_boot_choice}"
            )

        elif aosp_prebuilt_boot is not None:
            typer.echo(
                "  AOSP prebuilt:     "
                f"{aosp_prebuilt_boot}"
            )

        elif selected_kernel == "none":
            typer.echo(
                "  Kernel override:   none"
            )

        if selected_profile:
            typer.echo(
                f"  Kernel profile:     "
                f"{selected_profile}"
            )

        if selected_kernel_input is not None:
            typer.echo(
                "  Kernel input:       "
                f"{selected_kernel_input}"
            )

        if selected_kernel_variant is not None:
            typer.echo(
                "  Kernel variant:     "
                f"{selected_kernel_variant}"
            )

        typer.echo(
            f"  Device tools:       "
            f"{selected_device_tools}"
        )
        typer.echo(
            f"  GApps:              "
            f"{selected_gapps}"
        )
        typer.echo(
            f"  AVB signing:        "
            f"{selected_signing}"
        )
        typer.echo(
            "  Release artifacts:  "
            + (
                "Yes"
                if selected_release_artifacts
                else "No"
            )
        )
        typer.echo(
            "  Release signing:    "
            + (
                "Yes"
                if selected_release_signing
                else "No"
            )
        )
        typer.echo(
            f"  Jobs:               "
            f"{resolved_jobs}"
        )

        if selected_signing == "treeforge":
            typer.echo(
                "  AVB mode:            "
                "keys injected during m"
            )

        if selected_kernel_mode is not None:
            typer.echo(
                "  Kernel integration:  "
                f"{selected_kernel_mode}"
            )

        if plan_only:
            typer.echo("")
            typer.echo(
                "Plan only: no providers were "
                "materialized, no source files "
                "were changed, and no build or "
                "install was started."
            )
            return


        _save_build_selection(
            {
                "aosp_root": str(
                    root.resolve()
                ),
                "lunch_source": (
                    selected_source
                ),
                "lunch": (
                    selected_lunch.raw
                ),
                "kernel": (
                    selected_kernel
                ),
                "kernel_profile": (
                    selected_profile
                ),
                "kernel_mode": (
                    selected_kernel_mode
                ),
                "kernel_input": (
                    selected_kernel_input
                ),
                "kernel_variant": (
                    selected_kernel_variant
                ),
                "device_tools": (
                    selected_device_tools
                ),
                "gapps": (
                    selected_gapps
                ),
                "signing": (
                    selected_signing
                ),
                "release_artifacts": (
                    selected_release_artifacts
                ),
                "release_signing": (
                    selected_release_signing
                ),
                "jobs": (
                    resolved_jobs
                ),
                "boot_image": (
                    str(
                        resolved_boot_image
                    )
                    if (
                        resolved_boot_image
                        is not None
                        and selected_kernel
                        == "treeforge-output"
                    )
                    else None
                ),
                "updated_at": (
                    dt.datetime
                    .now()
                    .astimezone()
                    .isoformat()
                ),
            }
        )

        if (
            not yes
            and not non_interactive
        ):
            typer.echo("")

            if not typer.confirm(
                "Start build?",
                default=True,
            ):
                typer.echo("")
                typer.echo(
                    "Build choices saved."
                )
                return

        if selected_kernel in {
            "treeforge-local",
            "treeforge-release",
        }:
            raise RuntimeError(
                "TreeForge kernel provider bundle selected "
                "and validated, but whole-provider AOSP "
                "materialization is not connected yet. "
                "Refusing the legacy boot.img-only build path."
            )

        run_id = (
            dt.datetime
            .now()
            .astimezone()
            .strftime(
                "%Y%m%d-%H%M%S%z"
            )
        )

        report_root = (
            TREEFORGE_ROOT
            / "output"
            / "build"
            / run_id
        )

        report_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        log_path = (
            report_root
            / "aosp-build.log"
        )

        report_path = (
            report_root
            / "build-report.txt"
        )

        treeforge_kernel_bundle: dict[str, object] | None = None

        kernel_context = (
            contextlib.nullcontext(
                None
            )
        )

        if _is_treeforge_kernel_provider(
            selected_kernel
        ):
            assert selected_profile is not None
            assert selected_kernel_mode is not None

            if selected_kernel_input == "build":
                #
                # Both modes start from the complete Kernel machine
                # provider. AOSP-built mode consumes its raw inputs;
                # prebuilt mode consumes its coherent final images.
                #
                if selected_kernel_variant is None:
                    raise RuntimeError(
                        "TreeForge build-now path has no "
                        "selected kernel variant"
                    )

                treeforge_kernel_bundle = (
                    _build_treeforge_aosp_kernel_provider(
                        kernel_root=(
                            kernel_root
                            .expanduser()
                            .resolve()
                        ),
                        device=probe.device,
                        profile=selected_profile,
                        aosp_release=android_platform_release,
                        variant=selected_kernel_variant,
                    )
                )

                selected_kernel_bundle = (
                    treeforge_kernel_bundle
                )

            else:
                if selected_kernel_bundle is None:
                    raise RuntimeError(
                        "TreeForge kernel provider bundle "
                        "was not resolved"
                    )

                if selected_kernel_mode == "aosp":
                    #
                    # A release/local provider may drive AOSP-built
                    # mode only when it satisfies the complete v2/FIPS
                    # provider contract.
                    #
                    treeforge_kernel_bundle = (
                        _load_treeforge_aosp_kernel_provider(
                            manifest_path=Path(
                                selected_kernel_bundle[
                                    "manifest"
                                ]
                            ),
                            device=probe.device,
                            profile=selected_profile,
                            aosp_release=android_platform_release,
                        )
                    )

                else:
                    treeforge_kernel_bundle = (
                        selected_kernel_bundle
                    )

            kernel_context = (
                _temporary_treeforge_aosp_kernel_composition(
                    aosp_root=root,
                    target=selected_lunch,
                    device=probe.device,
                    bundle=treeforge_kernel_bundle,
                    mode=selected_kernel_mode,
                )
            )

        elif selected_kernel == "aosp":
            #
            # Untouched Google/AOSP control path.
            #
            assert aosp_prebuilt_boot is not None

        else:
            raise RuntimeError(
                "unhandled kernel provider "
                f"during execution: {selected_kernel}"
            )

        if selected_gapps == "mindthegapps":
            gapps_context = (
                _temporary_mindthegapps_inherit(
                    aosp_root=root,
                    probe=probe,
                )
            )

        else:
            gapps_context = (
                contextlib.nullcontext()
            )

        avb_context = (
            _temporary_build_avb_provider(
                aosp_root=root,
                probe=probe,
                signing=selected_signing,
            )
        )

        product_out = Path(
            probe.product_out
        ).resolve()

        android_complete = False
        release_artifacts_complete = False
        release_signing_complete = False

        release_artifact_error: (
            Exception | None
        ) = None

        release_signing_error: (
            Exception | None
        ) = None

        signed_target_files: (
            Path | None
        ) = None

        signed_images: (
            Path | None
        ) = None

        avb_verified: dict[
            str,
            str,
        ] = {}

        _write_report(
            report_path,
            [
                "TreeForge Android Build",
                "",
                f"AOSP root: {root}",
                (
                    "Lunch source: "
                    f"{selected_source}"
                ),
                (
                    "Lunch: "
                    f"{selected_lunch.raw}"
                ),
                f"Device: {probe.device}",
                (
                    "Architecture: "
                    f"{probe.arch}"
                ),
                (
                    "Kernel provider: "
                    f"{selected_kernel}"
                ),
                (
                    "Kernel profile: "
                    f"{selected_profile or 'n/a'}"
                ),
                (
                    "Kernel input: "
                    f"{selected_kernel_input or 'n/a'}"
                ),
                (
                    "Kernel variant: "
                    f"{selected_kernel_variant or 'n/a'}"
                ),
                (
                    "Kernel integration: "
                    f"{selected_kernel_mode or 'n/a'}"
                ),
                (
                    "ADB/Fastboot host tools: "
                    f"{selected_device_tools}"
                ),
                f"GApps: {selected_gapps}",
                (
                    "AVB build signing: "
                    f"{selected_signing}"
                ),
                (
                    "Release artifacts requested: "
                    + (
                        "yes"
                        if selected_release_artifacts
                        else "no"
                    )
                ),
                (
                    "Release signing requested: "
                    + (
                        "yes"
                        if selected_release_signing
                        else "no"
                    )
                ),
                f"Jobs: {resolved_jobs}",
                (
                    "Product output: "
                    f"{product_out}"
                ),
                f"Build log: {log_path}",
            ],
        )

        with gapps_context:
            with kernel_context as treeforge_kernel_runtime:
                with avb_context:
                    typer.echo("")
                    typer.echo(
                        "Building Android..."
                    )
                    typer.echo(
                        f"  Lunch: "
                        f"{selected_lunch.raw}"
                    )
                    typer.echo(
                        f"  Jobs:  "
                        f"{resolved_jobs}"
                    )
                    typer.echo(
                        f"  Log:   "
                        f"{log_path}"
                    )

                    _run_aosp_build(
                        aosp_root=root,
                        target=selected_lunch,
                        jobs=resolved_jobs,
                        log_path=log_path,
                        kernel_runtime=treeforge_kernel_runtime,
                    )

                    if (
                        treeforge_kernel_bundle is not None
                        and selected_kernel_mode is not None
                    ):
                        _validate_treeforge_kernel_outputs(
                            product_out=product_out,
                            bundle=treeforge_kernel_bundle,
                            mode=selected_kernel_mode,
                        )

                    android_complete = True

                    if not product_out.is_dir():
                        raise RuntimeError(
                            "AOSP build completed but "
                            "PRODUCT_OUT is missing: "
                            f"{product_out}"
                        )

                    if selected_signing == "treeforge":
                        typer.echo("")
                        typer.echo(
                            "Verifying TreeForge AVB "
                            "identities in PRODUCT_OUT..."
                        )

                        avb_verified = (
                            _verify_treeforge_product_avb(
                                aosp_root=root,
                                target=selected_lunch,
                                device=probe.device,
                                product_out=product_out,
                                probe=probe,
                                report_path=(report_root / "avb-report.txt"),
                            )
                        )

                        for (
                            partition,
                            identity,
                        ) in avb_verified.items():
                            typer.echo(
                                f"  {partition}: "
                                f"{identity}  PASS"
                            )

                    if selected_release_artifacts:
                        typer.echo("")
                        typer.echo(
                            "Preparing release artifacts..."
                        )
                        typer.echo(
                            "  target-files-package"
                        )
                        typer.echo(
                            "  otatools-package"
                        )

                        try:
                            _run_release_artifacts(
                                aosp_root=root,
                                target=selected_lunch,
                                jobs=resolved_jobs,
                                log_path=log_path,
                            )

                            target_files = (
                                _find_target_files(
                                    product_out
                                )
                            )

                            otatools = (
                                product_out
                                / "otatools.zip"
                            )

                            if not otatools.is_file():
                                raise RuntimeError(
                                    "otatools.zip was not "
                                    f"produced: {otatools}"
                                )

                            release_artifacts_complete = (
                                True
                            )

                            typer.echo(
                                f"  Target-files: "
                                f"{target_files}"
                            )
                            typer.echo(
                                f"  OTA tools:     "
                                f"{otatools}"
                            )

                        except Exception as exc:
                            release_artifact_error = (
                                exc
                            )

                            typer.echo("")
                            typer.echo(
                                "Release artifact phase "
                                f"failed: {exc}",
                                err=True,
                            )
                            typer.echo(
                                "Android PRODUCT_OUT "
                                "remains complete.",
                                err=True,
                            )

                    if (
                        selected_release_signing
                        and release_artifacts_complete
                    ):
                        typer.echo("")
                        typer.echo(
                            "Applying full TreeForge "
                            "APK/APEX/OTA release signing..."
                        )

                        try:
                            (
                                signed_target_files,
                                signed_images,
                            ) = (
                                _sign_treeforge_release(
                                    aosp_root=root,
                                    target=selected_lunch,
                                    device=probe.device,
                                    report_root=report_root,
                                )
                            )

                            release_signing_complete = (
                                True
                            )

                        except Exception as exc:
                            release_signing_error = (
                                exc
                            )

                            typer.echo(
                                "Release signing failed: "
                                f"{exc}",
                                err=True,
                            )
                            typer.echo(
                                "The directly built "
                                "PRODUCT_OUT remains intact.",
                                err=True,
                            )

        with report_path.open(
            "a",
            encoding="utf-8",
        ) as stream:
            stream.write("\n")
            stream.write(
                "Android build: "
                + (
                    "COMPLETE"
                    if android_complete
                    else "FAILED"
                )
                + "\n"
            )

            stream.write(
                "Release artifacts: "
                + (
                    "COMPLETE"
                    if release_artifacts_complete
                    else (
                        "FAILED"
                        if selected_release_artifacts
                        else "SKIPPED"
                    )
                )
                + "\n"
            )

            stream.write(
                "Release signing: "
                + (
                    "COMPLETE"
                    if release_signing_complete
                    else (
                        "FAILED"
                        if selected_release_signing
                        else "SKIPPED"
                    )
                )
                + "\n"
            )

            for (
                partition,
                identity,
            ) in sorted(
                avb_verified.items()
            ):
                stream.write(
                    "AVB identity "
                    f"{partition}: {identity}\n"
                )

            if signed_target_files:
                stream.write(
                    "Signed target-files: "
                    f"{signed_target_files}\n"
                )

            if signed_images:
                stream.write(
                    "Signed images: "
                    f"{signed_images}\n"
                )

        typer.echo("")
        typer.echo(
            "TreeForge Build Summary"
        )
        typer.echo("")
        typer.echo(
            "  Android build:      "
            + (
                "COMPLETE"
                if android_complete
                else "FAILED"
            )
        )
        typer.echo(
            "  AVB signing:        "
            f"{selected_signing}"
        )
        typer.echo(
            "  Release artifacts:  "
            + (
                "COMPLETE"
                if release_artifacts_complete
                else (
                    "FAILED"
                    if selected_release_artifacts
                    else "SKIPPED"
                )
            )
        )
        typer.echo(
            "  Release signing:    "
            + (
                "COMPLETE"
                if release_signing_complete
                else (
                    "FAILED"
                    if selected_release_signing
                    else "SKIPPED"
                )
            )
        )
        typer.echo(
            f"  Output:             "
            f"{product_out}"
        )
        typer.echo(
            f"  Report:             "
            f"{report_path}"
        )
        typer.echo(
            f"  Log:                "
            f"{log_path}"
        )

        install_command = (
            _install_handoff_command(
                product_out
            )
        )

        if non_interactive:
            typer.echo("")
            typer.echo(
                "Install later:"
            )
            typer.echo(
                "  "
                + shlex.join(
                    install_command
                )
            )

        else:
            typer.echo("")

            if typer.confirm(
                "Install this build now?",
                default=True,
            ):
                _handoff_to_install(
                    product_out
                )

            else:
                typer.echo("")
                typer.echo(
                    "Install later:"
                )
                typer.echo(
                    "  "
                    + shlex.join(
                        install_command
                    )
                )

        if release_artifact_error:
            raise typer.Exit(
                code=1
            )

        if release_signing_error:
            raise typer.Exit(
                code=1
            )

    except typer.BadParameter:
        raise

    except typer.Exit:
        raise

    except (
        OSError,
        RuntimeError,
        ValueError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as exc:
        typer.echo(
            f"TreeForge build failed: {exc}",
            err=True,
        )

        raise typer.Exit(
            code=1
        ) from exc

