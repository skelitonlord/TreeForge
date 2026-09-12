from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess

from treeforge.android.device_tree.apex_deployment import (
    AndroidDeviceTreeApexDeploymentPlan,
    AndroidDeviceTreeApexDeploymentTransformer,
)
from treeforge.android.device_tree.elf_deployment import (
    AndroidDeviceTreeElfDeploymentPlan,
)
from treeforge.android.device_tree.vintf_deployment import (
    AndroidDeviceTreeVintfDeploymentPlan,
)
from treeforge.android.device_tree.platform_deployment import (
    AndroidDeviceTreePlatformDeploymentPlan,
)
from treeforge.android.device_tree.deployment_identity import (
    AndroidDeviceTreeDeploymentIdentityVerifier,
)


class AndroidAospPreflightStatus(
    str,
    Enum,
):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAospPreflightCheck:
    check_id: str
    status: AndroidAospPreflightStatus
    summary: str
    details: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.check_id:
            raise ValueError(
                "check_id must not be empty"
            )

        if not self.summary:
            raise ValueError(
                "summary must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAospPreflightResult:
    aosp_root: Path
    device_root: Path
    generated_device_root: Path
    product: str
    release: str
    variant: str

    checks: tuple[
        AndroidAospPreflightCheck,
        ...,
    ]

    dumpvars_output: str = ""

    @property
    def failed_checks(
        self,
    ) -> tuple[
        AndroidAospPreflightCheck,
        ...,
    ]:
        return tuple(
            check
            for check in self.checks
            if (
                check.status
                is AndroidAospPreflightStatus.FAIL
            )
        )

    @property
    def warning_checks(
        self,
    ) -> tuple[
        AndroidAospPreflightCheck,
        ...,
    ]:
        return tuple(
            check
            for check in self.checks
            if (
                check.status
                is AndroidAospPreflightStatus.WARN
            )
        )

    @property
    def passed(
        self,
    ) -> bool:
        return not self.failed_checks

    def render(
        self,
    ) -> str:
        lines = [
            "TreeForge AOSP Preflight",
            "",
            "=== AOSP PREFLIGHT ===",
            (
                "Status: "
                + (
                    "PASS"
                    if self.passed
                    else "FAIL"
                )
            ),
            (
                "AOSP root: "
                f"{self.aosp_root}"
            ),
            (
                "Generated device root: "
                f"{self.generated_device_root}"
            ),
            (
                "Deployed device root: "
                f"{self.device_root}"
            ),
            (
                "Product: "
                f"{self.product}"
            ),
            (
                "Release: "
                f"{self.release}"
            ),
            (
                "Variant: "
                f"{self.variant}"
            ),
            "",
            (
                "Failed checks: "
                f"{len(self.failed_checks)}"
            ),
            (
                "Warnings: "
                f"{len(self.warning_checks)}"
            ),
            "",
            "Checks:",
        ]

        for check in self.checks:
            lines.append(
                (
                    f"  [{check.status.value}] "
                    f"{check.check_id}: "
                    f"{check.summary}"
                )
            )

            for detail in check.details:
                lines.append(
                    f"    {detail}"
                )

        if self.dumpvars_output:
            lines.extend(
                [
                    "",
                    "=== AOSP DUMPVARS ===",
                    self.dumpvars_output.rstrip(),
                ]
            )

        lines.extend(
            [
                "",
                "=== PREFLIGHT VERDICT ===",
                (
                    "SAFE TO START FULL SOONG: "
                    + (
                        "YES"
                        if self.passed
                        else "NO"
                    )
                ),
                "",
                (
                    "This preflight validates the generated/deployed "
                    "Device Tree and Android product/Make configuration "
                    "without running a full Soong/Ninja generation."
                ),
                (
                    "A PASS substantially reduces avoidable full-build "
                    "failures but cannot prove every Soong mutator, variant, "
                    "Blueprint schema, or dependency-graph condition."
                ),
            ]
        )

        return (
            "\n".join(lines)
            .rstrip()
            + "\n"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAospLegacyTreeCleanupEntry:
    relative_path: Path
    backup_path: Path
    source_path: Path
    backup_present: bool
    source_present_before: bool
    removed: bool
    required_backup: bool


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidAospLegacyTreeCleanupResult:
    entries: tuple[
        AndroidAospLegacyTreeCleanupEntry,
        ...,
    ]

    @property
    def removed(
        self,
    ) -> tuple[
        AndroidAospLegacyTreeCleanupEntry,
        ...,
    ]:
        return tuple(
            entry
            for entry in self.entries
            if entry.removed
        )

    @property
    def retained_unbacked(
        self,
    ) -> tuple[
        AndroidAospLegacyTreeCleanupEntry,
        ...,
    ]:
        return tuple(
            entry
            for entry in self.entries
            if (
                entry.source_present_before
                and not entry.backup_present
                and not entry.removed
            )
        )


#
# Android 15 Pixel/GS lineage used as developer/reference oracle.
#
# The first three have explicitly proven backups from the prior TreeForge
# quarantine/reference operation.
#
_REQUIRED_BACKED_UP_DEVICE_TREES = (
    Path("device/google/tangorpro"),
    Path("device/google/tangorpro-sepolicy"),
    Path("device/google/tangorpro-kernels"),
)

#
# These were also part of the historical Android 15 reference lineage.
#
# They are removed automatically only when TreeForge can prove a matching
# .treeforge-reference backup exists. Otherwise they are retained and the
# AOSP preflight ensures the generated tree does not consume them.
#
_OPTIONAL_BACKED_UP_DEVICE_TREES = (
    Path("device/google/gs-common"),
    Path("device/google/gs101"),
    Path("device/google/gs101-sepolicy"),
    Path("device/google/gs201"),
    Path("device/google/gs201-sepolicy"),
    Path("vendor/google_devices/tangorpro"),
    Path("device/google/akita"),
    Path("device/google/bluejay"),
    Path("device/google/caimito"),
    Path("device/google/comet"),
    Path("device/google/felix"),
    Path("device/google/lynx"),
    Path("device/google/pantah"),
    Path("device/google/raviole"),
    Path("device/google/shusky"),
    Path("device/google/zuma"),
    Path("device/google/zumapro"),
)

# TreeForge now owns device/treeforge/<device>.
# Canonical Google trees remain intact as providers/reference oracles.
_LEGACY_REFERENCE_DEVICE_TREES = ()

#
# Generated TreeForge output must not inherit from old Google device-tree
# implementation trees. These strings are checked in active generated Make/BP
# content regardless of whether the old tree is physically present.
#
_FORBIDDEN_GENERATED_REFERENCE_PREFIXES = (
    "device/google/gs-common/",
    "device/google/gs101/",
    "device/google/gs101-sepolicy/",
    "device/google/gs201/",
    "device/google/gs201-sepolicy/",
    "device/google/tangorpro-sepolicy/",
    "device/google/tangorpro-kernels/",
    "vendor/google_devices/tangorpro/",
    "device/google/akita/",
    "device/google/bluejay/",
    "device/google/caimito/",
    "device/google/comet/",
    "device/google/felix/",
    "device/google/lynx/",
    "device/google/pantah/",
    "device/google/raviole/",
    "device/google/shusky/",
    "device/google/zuma/",
    "device/google/zumapro/",
)

_FINAL_DEVICE_TREE_MARKERS = (
    "Exact Reconstruction identity: True",
    "Android source checkout used for generation: NO",
    "Build realizations: 5144",
    "Resolved realizations: 4035",
    "Closed realizations: 1109",
    "Partial realizations: 0",
    "Partial accounting: PASS",
    "Device Tree freeze readiness: READY",
    "Full Reconstruction realization coverage: PASS",
    "Boot/DTBO/VBMeta realization coverage: PASS",
    "AVB build mapping complete: PASS",
    "AOSP checkout generation dependencies: 0",
    "TreeForge image builders: 0",
    "TreeForge VBMeta encoders: 0",
)

_DUMPVARS = (
    "TARGET_PRODUCT",
    "TARGET_DEVICE",
    "TARGET_BUILD_VARIANT",
    "PRODUCT_OUT",
    "BOARD_BOOT_HEADER_VERSION",
    "BOARD_MKBOOTIMG_ARGS",
    "BOARD_BOOTIMAGE_PARTITION_SIZE",
    "BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE",
    "BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE",
    "BOARD_VENDOR_KERNEL_BOOTIMAGE_PARTITION_SIZE",
    "BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE",
    "BOARD_AVB_ENABLE",
    "BOARD_AVB_ALGORITHM",
    "BOARD_AVB_BOOT_ALGORITHM",
    "BOARD_AVB_INIT_BOOT_ALGORITHM",
    "BOARD_AVB_VBMETA_SYSTEM",
    "BOARD_AVB_VBMETA_VENDOR",
    "PRODUCT_BUILD_BOOT_IMAGE",
    "PRODUCT_BUILD_INIT_BOOT_IMAGE",
    "PRODUCT_BUILD_VENDOR_BOOT_IMAGE",
    "PRODUCT_BUILD_VENDOR_KERNEL_BOOT_IMAGE",
    "PRODUCT_BUILD_PVMFW_IMAGE",
    "PRODUCT_BUILD_VBMETA_IMAGE",
    "PRODUCT_SOURCE_ROOT_DIRS",
)


def _safe_relative(
    value: Path,
) -> None:
    if value.is_absolute():
        raise ValueError(
            f"path must be relative: {value}"
        )

    if ".." in value.parts:
        raise ValueError(
            f"path escapes root: {value}"
        )


def clean_backed_up_legacy_reference_trees(
    *,
    repository_root: Path,
    aosp_root: Path,
) -> AndroidAospLegacyTreeCleanupResult:
    """
    Remove old AOSP device-tree/reference copies only when a backup exists.

    The known tangorpro lineage roots are fail-closed: if one exists in AOSP
    but its previously established .treeforge-reference backup is missing,
    TreeForge refuses to delete it.

    gs-common/gs101/gs201 lineage roots are removed opportunistically only
    when the matching backup actually exists.
    """

    repository_root = (
        repository_root
        .expanduser()
        .resolve()
    )

    aosp_root = (
        aosp_root
        .expanduser()
        .resolve()
    )

    reference_root = (
        repository_root
        / ".treeforge-reference"
    )

    entries = []

    required = set(
        _REQUIRED_BACKED_UP_DEVICE_TREES
    )

    for relative in (
        _LEGACY_REFERENCE_DEVICE_TREES
    ):
        _safe_relative(
            relative
        )

        source = (
            aosp_root
            / relative
        )

        backup = (
            reference_root
            / relative
        )

        source_present = (
            source.exists()
        )

        backup_present = (
            backup.is_dir()
        )

        required_backup = (
            relative in required
        )

        if (
            source_present
            and required_backup
            and not backup_present
        ):
            raise RuntimeError(
                "refusing to remove backed-up legacy "
                "Device Tree because its required backup "
                "is unavailable: "
                f"source={source}, backup={backup}"
            )

        removed = False

        if (
            source_present
            and backup_present
        ):
            resolved_source = (
                source.resolve()
            )

            try:
                resolved_source.relative_to(
                    aosp_root
                )

            except ValueError as error:
                raise RuntimeError(
                    "legacy Device Tree cleanup target "
                    "escaped the AOSP workspace"
                ) from error

            if source.is_symlink():
                source.unlink()

            elif source.is_dir():
                shutil.rmtree(
                    source
                )

            else:
                raise RuntimeError(
                    "legacy Device Tree cleanup target "
                    "is neither a directory nor symlink: "
                    f"{source}"
                )

            removed = True

        entries.append(
            AndroidAospLegacyTreeCleanupEntry(
                relative_path=relative,
                backup_path=backup,
                source_path=source,
                backup_present=(
                    backup_present
                ),
                source_present_before=(
                    source_present
                ),
                removed=removed,
                required_backup=(
                    required_backup
                ),
            )
        )

    return (
        AndroidAospLegacyTreeCleanupResult(
            entries=tuple(
                entries
            )
        )
    )


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def _ignore_manifest_path(
    relative: Path,
) -> bool:
    #
    # Private signing material is an external deployment/build input and is
    # intentionally not part of canonical generated Device Tree identity.
    #
    return (
        len(relative.parts) >= 3
        and relative.parts[0] == "keys"
        and relative.parts[1] == "avb"
        and relative.suffix == ".pem"
    )


def _tree_manifest(
    root: Path,
) -> tuple[
    tuple[
        str,
        str,
        str,
    ],
    ...,
]:
    entries = []

    for path in sorted(
        root.rglob("*"),
        key=lambda item: (
            item.as_posix()
        ),
    ):
        relative = (
            path.relative_to(
                root
            )
        )

        if _ignore_manifest_path(
            relative
        ):
            continue

        if path.is_symlink():
            entries.append(
                (
                    relative.as_posix(),
                    "symlink",
                    os.readlink(path),
                )
            )

        elif path.is_file():
            entries.append(
                (
                    relative.as_posix(),
                    "file",
                    _sha256(path),
                )
            )

    return tuple(
        entries
    )


def _active_text(
    path: Path,
) -> str:
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = []

    for line in text.splitlines():
        stripped = line.lstrip()

        if stripped.startswith(
            "#"
        ):
            continue

        if stripped.startswith(
            "//"
        ):
            continue

        lines.append(
            line
        )

    return "\n".join(
        lines
    )


def _build_text_files(
    root: Path,
):
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if path.name in {
            "Android.bp",
            "Android.mk",
            "AndroidProducts.mk",
            "BoardConfig.mk",
        }:
            yield path
            continue

        if path.suffix in {
            ".mk",
            ".bp",
        }:
            yield path


def _parse_final_device_root(
    report: str,
) -> Path:
    match = re.search(
        r"^Device root:\s+(.+)$",
        report,
        re.MULTILINE,
    )

    if match is None:
        raise ValueError(
            "final Device Tree report has no Device root"
        )

    result = Path(
        match.group(1).strip()
    )

    _safe_relative(
        result
    )

    return result


def _parse_final_device_name(
    report: str,
) -> str:
    match = re.search(
        r"^Source-tree device:\s+(\S+)$",
        report,
        re.MULTILINE,
    )

    if match is None:
        raise ValueError(
            "final Device Tree report has no source-tree device"
        )

    return match.group(1)


def _literal_make_paths(
    root: Path,
) -> tuple[
    tuple[
        str,
        Path,
        str,
    ],
    ...,
]:
    """
    Return literal AOSP-relative paths directly referenced by generated Make.

    Variable-containing expressions remain Android-owned and are intentionally
    not guessed here.
    """

    references = []

    include_re = re.compile(
        r"^\s*include\s+([^\s#]+)",
        re.MULTILINE,
    )

    optional_include_re = re.compile(
        r"^\s*-include\s+([^\s#]+)",
        re.MULTILINE,
    )

    inherit_re = re.compile(
        r"\$\(\s*call\s+inherit-product\s*,\s*([^)]+)\)"
    )

    optional_inherit_re = re.compile(
        r"\$\(\s*call\s+inherit-product-if-exists\s*,\s*([^)]+)\)"
    )

    copy_source_re = re.compile(
        r"(?m)^\s*"
        r"([A-Za-z0-9_.+\-/]+)"
        r":\$\("
    )

    for file_path in (
        _build_text_files(
            root
        )
    ):
        text = _active_text(
            file_path
        )

        for kind, regex in (
            (
                "include",
                include_re,
            ),
            (
                "optional-include",
                optional_include_re,
            ),
            (
                "inherit-product",
                inherit_re,
            ),
            (
                "optional-inherit-product",
                optional_inherit_re,
            ),
            (
                "copy-source",
                copy_source_re,
            ),
        ):
            for match in regex.finditer(
                text
            ):
                raw = (
                    match.group(1)
                    .strip()
                    .rstrip("\\")
                    .strip()
                )

                if not raw:
                    continue

                if "$(" in raw:
                    continue

                candidate = Path(
                    raw
                )

                if candidate.is_absolute():
                    continue

                if ".." in candidate.parts:
                    continue

                references.append(
                    (
                        kind,
                        file_path,
                        candidate,
                    )
                )

    return tuple(
        references
    )




def _strip_blueprint_comments(
    text: str,
) -> str:
    """
    Strip active Blueprint comments while preserving comment-looking
    characters inside quoted strings.
    """

    result: list[str] = []

    index = 0
    length = len(text)

    in_string = False
    escaped = False

    while index < length:
        char = text[index]

        if in_string:
            result.append(
                char
            )

            if escaped:
                escaped = False

            elif char == "\\":
                escaped = True

            elif char == '"':
                in_string = False

            index += 1
            continue

        if char == '"':
            in_string = True

            result.append(
                char
            )

            index += 1
            continue

        if (
            char == "/"
            and index + 1 < length
        ):
            following = text[
                index + 1
            ]

            if following == "/":
                index += 2

                while (
                    index < length
                    and text[index] != "\n"
                ):
                    index += 1

                if index < length:
                    result.append(
                        "\n"
                    )

                    index += 1

                continue

            if following == "*":
                index += 2

                while (
                    index + 1 < length
                    and not (
                        text[index] == "*"
                        and text[index + 1] == "/"
                    )
                ):
                    if text[index] == "\n":
                        result.append(
                            "\n"
                        )

                    index += 1

                if index + 1 < length:
                    index += 2

                continue

        result.append(
            char
        )

        index += 1

    return "".join(
        result
    )


def _blueprint_balanced_brace_body(
    text: str,
    opening_brace: int,
) -> str:
    """
    Return one balanced Blueprint {...} body.
    """

    depth = 0
    index = opening_brace

    in_string = False
    escaped = False

    while index < len(text):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False

            elif char == "\\":
                escaped = True

            elif char == '"':
                in_string = False

            index += 1
            continue

        if char == '"':
            in_string = True

            index += 1
            continue

        if char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return text[
                    opening_brace + 1:
                    index
                ]

        index += 1

    raise ValueError(
        "unterminated Blueprint brace block"
    )


def _blueprint_soong_namespace(
    path: Path,
) -> tuple[
    bool,
    tuple[str, ...],
]:
    """
    Return:

      (
        declares_soong_namespace,
        literal_namespace_imports,
      )
    """

    try:
        source = path.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:
        return (
            False,
            (),
        )

    active = (
        _strip_blueprint_comments(
            source
        )
    )

    declaration_pattern = re.compile(
        r"\bsoong_namespace\s*\{"
    )

    imports_pattern = re.compile(
        r"\bimports\s*:\s*\["
        r"(?P<body>.*?)"
        r"\]",
        re.DOTALL,
    )

    quoted_pattern = re.compile(
        r'"([^"]+)"'
    )

    declarations = tuple(
        declaration_pattern.finditer(
            active
        )
    )

    if not declarations:
        return (
            False,
            (),
        )

    imports: set[str] = set()

    for declaration in declarations:
        opening_brace = active.find(
            "{",
            declaration.start(),
            declaration.end(),
        )

        if opening_brace < 0:
            continue

        body = (
            _blueprint_balanced_brace_body(
                active,
                opening_brace,
            )
        )

        for imports_match in (
            imports_pattern.finditer(
                body
            )
        ):
            for value in (
                quoted_pattern.findall(
                    imports_match.group(
                        "body"
                    )
                )
            ):
                normalized = (
                    value
                    .strip()
                    .strip("/")
                )

                if normalized:
                    imports.add(
                        normalized
                    )

    return (
        True,
        tuple(
            sorted(
                imports
            )
        ),
    )


def _source_root_dir_allowed(
    path: str,
    source_root_dirs: tuple[str, ...],
) -> bool:
    """
    Mirror Blueprint SourceRootDirs.SourceRootDirAllowed.

    Rules are prefix matches. A leading '-' excludes a prefix.
    Longest/more-specific rules take precedence.
    No matching rule means the path is allowed.
    """

    rules = sorted(
        source_root_dirs,
        key=len,
    )

    for raw_rule in reversed(
        rules
    ):
        if not raw_rule:
            continue

        excluded = (
            raw_rule.startswith(
                "-"
            )
        )

        prefix = (
            raw_rule[1:]
            if excluded
            else raw_rule
        )

        if not prefix:
            continue

        if path.startswith(
            prefix
        ):
            return not excluded

    return True


def _dumpvars_assignment(
    output: str,
    variable: str,
) -> str | None:
    """
    Read one shell-style assignment emitted by --dumpvars-mode.
    """

    prefix = (
        variable
        + "="
    )

    for line in output.splitlines():
        if not line.startswith(
            prefix
        ):
            continue

        value = line[
            len(prefix):
        ].strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {
                "'",
                '"',
            }
        ):
            value = value[
                1:-1
            ]

        return value

    return None


def _aosp_android_bp_paths(
    aosp_root: Path,
    *,
    source_root_dirs: tuple[str, ...] = (),
) -> tuple[Path, ...]:
    """
    Enumerate Android.bp files visible to the selected product.

    Filesystem metadata/build-output trees are excluded first.

    PRODUCT_SOURCE_ROOT_DIRS is then applied using the same longest-prefix
    allow/deny behavior used by Blueprint.
    """

    paths: list[Path] = []

    for current_root, directories, files in os.walk(
        aosp_root
    ):
        directories[:] = [
            directory
            for directory in directories
            if directory not in {
                ".git",
                ".repo",
                "out",
            }
        ]

        if "Android.bp" not in files:
            continue

        path = (
            Path(
                current_root
            )
            / "Android.bp"
        )

        relative = (
            path.relative_to(
                aosp_root
            ).as_posix()
        )

        if not _source_root_dir_allowed(
            relative,
            source_root_dirs,
        ):
            continue

        paths.append(
            path
        )

    return tuple(
        sorted(
            paths,
            key=lambda path: (
                path.relative_to(
                    aosp_root
                ).as_posix()
            ),
        )
    )



def _aosp_soong_namespace_integrity(
    aosp_root: Path,
    *,
    source_root_dirs: tuple[str, ...] = (),
) -> tuple[
    int,
    int,
    int,
    tuple[str, ...],
]:
    """
    Validate literal Soong namespace imports in the selected product's
    Blueprint universe.

    Returns:

      (
        selected_android_bp_count,
        declared_namespace_count,
        import_edge_count,
        missing_import_edges,
      )
    """

    android_bp_paths = (
        _aosp_android_bp_paths(
            aosp_root,
            source_root_dirs=(
                source_root_dirs
            ),
        )
    )

    declared_namespaces: set[str] = set()

    import_edges: list[
        tuple[
            str,
            str,
        ]
    ] = []

    for path in android_bp_paths:
        declares, imports = (
            _blueprint_soong_namespace(
                path
            )
        )

        source_file = (
            path.relative_to(
                aosp_root
            ).as_posix()
        )

        if declares:
            namespace = (
                path.parent
                .relative_to(
                    aosp_root
                )
                .as_posix()
            )

            if namespace == ".":
                namespace = ""

            declared_namespaces.add(
                namespace
            )

        for imported in imports:
            import_edges.append(
                (
                    source_file,
                    imported,
                )
            )

    missing = tuple(
        sorted(
            f"{source_file} -> {target}"
            for source_file, target in import_edges
            if target not in declared_namespaces
        )
    )

    return (
        len(
            android_bp_paths
        ),
        len(
            declared_namespaces
        ),
        len(
            import_edges
        ),
        missing,
    )




def _bp_module_names(
    path: Path,
) -> tuple[str, ...]:
    """
    Lightweight top-level Blueprint module-name census.

    This is intentionally not a replacement for Soong parsing. It only catches
    obvious duplicate module identities in TreeForge-generated Android.bp.
    """

    names = []

    module_depth = None
    depth = 0

    string_re = re.compile(
        r'"(?:\\.|[^"\\])*"'
    )

    for raw_line in (
        path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        .splitlines()
    ):
        stripped = (
            raw_line.strip()
        )

        if (
            not stripped
            or stripped.startswith(
                "//"
            )
        ):
            continue

        sanitized = (
            string_re.sub(
                '""',
                raw_line,
            )
        )

        if (
            depth == 0
            and re.match(
                r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*\{",
                sanitized,
            )
        ):
            module_depth = 1

        if (
            module_depth == 1
            and depth == 1
        ):
            name_match = re.match(
                r'^\s*name\s*:\s*"([^"]+)"\s*,?\s*$',
                raw_line,
            )

            if name_match:
                names.append(
                    name_match.group(1)
                )

        depth += (
            sanitized.count(
                "{"
            )
            - sanitized.count(
                "}"
            )
        )

        if depth == 0:
            module_depth = None

    return tuple(
        names
    )


def _generated_module_names(
    root: Path,
) -> dict[
    str,
    list[str],
]:
    result: dict[
        str,
        list[str],
    ] = {}

    mk_re = re.compile(
        r"(?m)^\s*LOCAL_MODULE\s*:?=\s*([^\s#]+)"
    )

    for path in root.rglob(
        "Android.bp"
    ):
        for name in _bp_module_names(
            path
        ):
            result.setdefault(
                name,
                [],
            ).append(
                path.relative_to(
                    root
                ).as_posix()
            )

    for path in root.rglob(
        "Android.mk"
    ):
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        for match in mk_re.finditer(
            text
        ):
            name = match.group(1)

            result.setdefault(
                name,
                [],
            ).append(
                path.relative_to(
                    root
                ).as_posix()
            )

    return result


class AndroidAospPreflight:
    """
    Cheap downstream validation before a full Soong/Ninja generation.

    This validator may inspect the AOSP checkout because it is explicitly
    downstream of the frozen Device Tree stage.

    It never mutates Reconstruction or Device Tree semantics.
    """

    def run(
        self,
        *,
        repository_root: Path,
        output_root: Path,
        aosp_root: Path,
        product: str | None = None,
        release: str = "bp1a",
        variant: str = "userdebug",
        run_dumpvars: bool = True,
    ) -> AndroidAospPreflightResult:
        repository_root = (
            repository_root
            .expanduser()
            .resolve()
        )

        output_root = (
            output_root
            .expanduser()
            .resolve()
        )

        aosp_root = (
            aosp_root
            .expanduser()
            .resolve()
        )

        report_path = (
            output_root
            / "device-tree"
            / "work"
            / "device-tree-report.txt"
        )

        checks = []

        if not report_path.is_file():
            checks.append(
                AndroidAospPreflightCheck(
                    check_id="device-tree-report",
                    status=(
                        AndroidAospPreflightStatus.FAIL
                    ),
                    summary=(
                        "final Device Tree report is missing"
                    ),
                    details=(
                        str(
                            report_path
                        ),
                    ),
                )
            )

            return AndroidAospPreflightResult(
                aosp_root=aosp_root,
                device_root=Path(),
                generated_device_root=Path(),
                product=(
                    product
                    if product is not None
                    else "<unknown>"
                ),
                release=release,
                variant=variant,
                checks=tuple(
                    checks
                ),
            )

        report = report_path.read_text(
            encoding="utf-8"
        )

        missing_markers = tuple(
            marker
            for marker
            in _FINAL_DEVICE_TREE_MARKERS
            if marker not in report
        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="frozen-device-tree",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if not missing_markers
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "frozen Device Tree acceptance contract is present"
                    if not missing_markers
                    else (
                        "final Device Tree report does not match "
                        "the accepted freeze contract"
                    )
                ),
                details=missing_markers,
            )
        )

        try:
            device_relative = (
                _parse_final_device_root(
                    report
                )
            )

            device_name = (
                _parse_final_device_name(
                    report
                )
            )

        except ValueError as error:
            checks.append(
                AndroidAospPreflightCheck(
                    check_id="device-tree-identity",
                    status=(
                        AndroidAospPreflightStatus.FAIL
                    ),
                    summary=str(
                        error
                    ),
                )
            )

            return AndroidAospPreflightResult(
                aosp_root=aosp_root,
                device_root=Path(),
                generated_device_root=Path(),
                product=(
                    product
                    if product is not None
                    else "<unknown>"
                ),
                release=release,
                variant=variant,
                checks=tuple(
                    checks
                ),
            )

        resolved_product = (
            product
            if product is not None
            else f"aosp_{device_name}"
        )

        generated_device_root = (
            output_root
            / "device-tree"
            / device_relative
        )

        deployed_device_root = (
            aosp_root
            / device_relative
        )

        required_aosp_paths = (
            aosp_root
            / "build"
            / "soong"
            / "soong_ui.bash",
            aosp_root
            / "build"
            / "envsetup.sh",
            aosp_root
            / "build"
            / "make"
            / "core",
        )

        missing_aosp = tuple(
            str(path)
            for path in required_aosp_paths
            if not path.exists()
        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="aosp-workspace",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if (
                        aosp_root.is_dir()
                        and not missing_aosp
                    )
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "AOSP workspace/build entrypoints are present"
                    if (
                        aosp_root.is_dir()
                        and not missing_aosp
                    )
                    else "AOSP workspace is incomplete"
                ),
                details=missing_aosp,
            )
        )

        required_generated = (
            generated_device_root
            / "AndroidProducts.mk",
            generated_device_root
            / "BoardConfig.mk",
            generated_device_root
            / f"{resolved_product}.mk",
            generated_device_root
            / "device.mk",
            generated_device_root
            / f"{device_name}-vendor.mk",
            generated_device_root
            / "AndroidBoard.mk",
        )

        missing_generated = tuple(
            str(
                path.relative_to(
                    generated_device_root
                )
            )
            for path in required_generated
            if not path.is_file()
        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="generated-product-spine",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if (
                        generated_device_root.is_dir()
                        and not missing_generated
                    )
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "generated Android product spine is complete"
                    if not missing_generated
                    else (
                        "generated Android product spine "
                        "is incomplete"
                    )
                ),
                details=missing_generated,
            )
        )

        if (
            generated_device_root.is_dir()
            and deployed_device_root.is_dir()
        ):
            apex_deployment_report_path = (
                output_root
                / "device-tree"
                / "work"
                / "platform-provider-apex-plan.json"
            )

            elf_deployment_report_path = (
                output_root
                / "device-tree"
                / "work"
                / "platform-provider-elf-plan.json"
            )

            vintf_deployment_report_path = (
                output_root
                / "device-tree"
                / "work"
                / "platform-provider-vintf-plan.json"
            )

            platform_deployment_report_path = (
                output_root
                / "device-tree"
                / "work"
                / "platform-provider-build-plan.json"
            )

            if (
                apex_deployment_report_path.is_file()
                and elf_deployment_report_path.is_file()
                and vintf_deployment_report_path.is_file()
                and platform_deployment_report_path.is_file()
            ):
                try:
                    apex_deployment_plan = (
                        AndroidDeviceTreeApexDeploymentPlan
                        .load_json(
                            apex_deployment_report_path
                        )
                    )

                    elf_deployment_plan = (
                        AndroidDeviceTreeElfDeploymentPlan
                        .load_json(
                            elf_deployment_report_path
                        )
                    )

                    vintf_deployment_plan = (
                        AndroidDeviceTreeVintfDeploymentPlan
                        .load_json(
                            vintf_deployment_report_path
                        )
                    )

                    platform_deployment_plan = (
                        AndroidDeviceTreePlatformDeploymentPlan
                        .load_json(
                            platform_deployment_report_path
                        )
                    )

                    (
                        manifests_equal,
                        deployment_identity_details,
                    ) = (
                        AndroidDeviceTreeDeploymentIdentityVerifier
                        .compare_deployed_tree(
                            generated_device_root=(
                                generated_device_root
                            ),
                            deployed_device_root=(
                                deployed_device_root
                            ),
                            apex_plan=(
                                apex_deployment_plan
                            ),
                            elf_plan=(
                                elf_deployment_plan
                            ),
                            vintf_plan=(
                                vintf_deployment_plan
                            ),
                            vendor_makefile_name=(
                                f"{device_name}-vendor.mk"
                            ),
                                                platform_plan=(
                            platform_deployment_plan
                        ),
)
                    )

                except (
                    OSError,
                    ValueError,
                    TypeError,
                ) as error:
                    manifests_equal = False
                    deployment_identity_details = (
                        (
                            "invalid APEX deployment "
                            "reconciliation: "
                            f"{error}"
                        ),
                    )

                deployment_identity_summary = (
                    (
                        "deployed Device Tree matches frozen "
                        "generated output plus the recorded "
                        "AOSP deployment reconciliation"
                    )
                    if manifests_equal
                    else (
                        "deployed Device Tree differs from "
                        "the canonical generated output or "
                        "its recorded AOSP deployment "
                        "reconciliation"
                    )
                )

                deployment_identity_details = (
                    (
                        "APEX platform-provider plan: "
                        f"{apex_deployment_report_path}"
                    ),
                    (
                        "ELF platform-provider plan: "
                        f"{elf_deployment_report_path}"
                    ),
                    (
                        "VINTF platform-provider plan: "
                        f"{vintf_deployment_report_path}"
                    ),
                    (
                        "Platform-provider build plan: "
                        f"{platform_deployment_report_path}"
                    ),
                    *deployment_identity_details,
                )

            else:
                generated_manifest = (
                    _tree_manifest(
                        generated_device_root
                    )
                )

                deployed_manifest = (
                    _tree_manifest(
                        deployed_device_root
                    )
                )

                manifests_equal = (
                    generated_manifest
                    == deployed_manifest
                )

                deployment_identity_summary = (
                    (
                        "deployed Device Tree matches frozen "
                        "generated output"
                    )
                    if manifests_equal
                    else (
                        "deployed Device Tree differs from "
                        "frozen generated output"
                    )
                )

                deployment_identity_details = (
                    (
                        "No complete AOSP deployment reconciliation "
                        "report set is present."
                    ),
                )

            checks.append(
                AndroidAospPreflightCheck(
                    check_id="deployment-identity",
                    status=(
                        AndroidAospPreflightStatus.PASS
                        if manifests_equal
                        else AndroidAospPreflightStatus.FAIL
                    ),
                    summary=(
                        deployment_identity_summary
                    ),
                    details=(
                        deployment_identity_details
                    ),
                )
            )

        else:
            checks.append(
                AndroidAospPreflightCheck(
                    check_id="deployment-identity",
                    status=(
                        AndroidAospPreflightStatus.FAIL
                    ),
                    summary=(
                        "generated Device Tree has not been "
                        "deployed into AOSP"
                    ),
                    details=(
                        str(
                            deployed_device_root
                        ),
                    ),
                )
            )

        #
        # If a legacy tree has a proven backup, it should not remain beside
        # the TreeForge tree where Android could accidentally consume it.
        #
        reference_root = (
            repository_root
            / ".treeforge-reference"
        )

        legacy_reintroduced = []

        retained_without_backup = []

        for relative in (
            _LEGACY_REFERENCE_DEVICE_TREES
        ):
            #
            # Current tangorpro destination is expected to exist because it is
            # now the TreeForge-generated tree. Deployment identity above
            # proves what it is.
            #
            if relative == device_relative:
                continue

            source = (
                aosp_root
                / relative
            )

            backup = (
                reference_root
                / relative
            )

            if (
                source.exists()
                and backup.is_dir()
            ):
                legacy_reintroduced.append(
                    relative.as_posix()
                )

            elif (
                source.exists()
                and not backup.is_dir()
            ):
                retained_without_backup.append(
                    relative.as_posix()
                )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="legacy-reference-isolation",
                status=(
                    AndroidAospPreflightStatus.FAIL
                    if legacy_reintroduced
                    else (
                        AndroidAospPreflightStatus.WARN
                        if retained_without_backup
                        else AndroidAospPreflightStatus.PASS
                    )
                ),
                summary=(
                    "backed-up legacy Android device trees are isolated"
                    if not legacy_reintroduced
                    else (
                        "backed-up legacy device trees were "
                        "reintroduced into AOSP"
                    )
                ),
                details=(
                    tuple(
                        (
                            "reintroduced backed-up tree: "
                            + item
                        )
                        for item
                        in legacy_reintroduced
                    )
                    + tuple(
                        (
                            "retained because no matching backup "
                            "is proven: "
                            + item
                        )
                        for item
                        in retained_without_backup
                    )
                ),
            )
        )

        forbidden_hits = []

        if generated_device_root.is_dir():
            for build_file in (
                _build_text_files(
                    generated_device_root
                )
            ):
                active = (
                    _active_text(
                        build_file
                    )
                )

                for prefix in (
                    _FORBIDDEN_GENERATED_REFERENCE_PREFIXES
                ):
                    if prefix in active:
                        forbidden_hits.append(
                            (
                                build_file
                                .relative_to(
                                    generated_device_root
                                )
                                .as_posix()
                                + ": "
                                + prefix
                            )
                        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="legacy-reference-dependencies",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if not forbidden_hits
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "generated tree has no dependency on "
                    "old Google device-tree lineage"
                    if not forbidden_hits
                    else (
                        "generated tree still references old "
                        "Google device-tree lineage"
                    )
                ),
                details=tuple(
                    sorted(
                        forbidden_hits
                    )
                ),
            )
        )

        missing_required_paths = []
        optional_missing_paths = []

        if deployed_device_root.is_dir():
            for (
                kind,
                source_file,
                relative,
            ) in _literal_make_paths(
                deployed_device_root
            ):
                candidate = (
                    aosp_root
                    / relative
                )

                if candidate.exists():
                    continue

                detail = (
                    source_file
                    .relative_to(
                        deployed_device_root
                    )
                    .as_posix()
                    + ": "
                    + kind
                    + " -> "
                    + relative.as_posix()
                )

                if kind.startswith(
                    "optional-"
                ):
                    optional_missing_paths.append(
                        detail
                    )

                else:
                    missing_required_paths.append(
                        detail
                    )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="literal-make-paths",
                status=(
                    AndroidAospPreflightStatus.FAIL
                    if missing_required_paths
                    else (
                        AndroidAospPreflightStatus.WARN
                        if optional_missing_paths
                        else AndroidAospPreflightStatus.PASS
                    )
                ),
                summary=(
                    "literal generated Make references resolve in AOSP"
                    if not missing_required_paths
                    else (
                        "generated Make contains unresolved "
                        "literal required paths"
                    )
                ),
                details=(
                    tuple(
                        sorted(
                            missing_required_paths
                        )
                    )
                    + tuple(
                        (
                            "optional: "
                            + item
                        )
                        for item
                        in sorted(
                            optional_missing_paths
                        )
                    )
                ),
            )
        )

        structural_text = ""

        if deployed_device_root.is_dir():
            structural_text = "\n".join(
                _active_text(
                    path
                )
                for path in (
                    _build_text_files(
                        deployed_device_root
                    )
                )
            )

        structural_requirements = (
            "PRODUCT_BUILD_VENDOR_BOOT_IMAGE := true",
            "PRODUCT_BUILD_VENDOR_KERNEL_BOOT_IMAGE := true",
            "PRODUCT_BUILD_PVMFW_IMAGE := false",
            "PRODUCT_BUILD_VBMETA_IMAGE := true",
            "BOARD_AVB_ENABLE := true",
            "BOARD_MKBOOTIMG_ARGS += --header_version",
            "BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE :=",
            "BOARD_VENDOR_RAMDISK_FRAGMENTS",
            "BOARD_BOOTCONFIG +=",
            "BOARD_PREBUILT_DTBIMAGE_DIR",
        )

        structural_forbidden = (
            "BOARD_BOOTCONFIG_FILE",
            "BOARD_PREBUILT_VENDOR_BOOTIMAGE",
            "BOARD_CUSTOMIMAGES_PARTITION_LIST",
            "external/avb/test/data/testkey",
            "avb_testkey_rsa",
        )

        missing_structure = tuple(
            item
            for item
            in structural_requirements
            if item not in structural_text
        )

        forbidden_structure = tuple(
            item
            for item
            in structural_forbidden
            if item in structural_text
        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="construction-policy",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if (
                        not missing_structure
                        and not forbidden_structure
                    )
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "Android-native image/AVB construction policy is intact"
                    if (
                        not missing_structure
                        and not forbidden_structure
                    )
                    else (
                        "Android-native construction policy "
                        "does not match frozen Device Tree"
                    )
                ),
                details=(
                    tuple(
                        (
                            "missing: "
                            + item
                        )
                        for item
                        in missing_structure
                    )
                    + tuple(
                        (
                            "forbidden: "
                            + item
                        )
                        for item
                        in forbidden_structure
                    )
                ),
            )
        )

        key_re = re.compile(
            r"(?m)^\s*"
            r"(BOARD_AVB(?:_[A-Z0-9_]+)?_KEY_PATH)"
            r"\s*:=\s*(\S+)\s*$"
        )

        key_entries = {}

        for match in key_re.finditer(
            structural_text
        ):
            key_entries[
                match.group(1)
            ] = match.group(2)

        missing_keys = []
        bad_keys = []

        for variable, value in sorted(
            key_entries.items()
        ):
            if (
                "testkey" in value.lower()
                or "external/avb/test" in value.lower()
            ):
                bad_keys.append(
                    f"{variable} -> {value}"
                )

                continue

            if "$(" in value:
                bad_keys.append(
                    (
                        f"{variable} uses unresolved "
                        f"variable expression: {value}"
                    )
                )

                continue

            key_path = (
                aosp_root
                / value
            )

            if not key_path.is_file():
                missing_keys.append(
                    f"{variable} -> {value}"
                )

        expected_key_count = 5

        key_count_ok = (
            len(
                key_entries
            )
            == expected_key_count
        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="external-avb-keys",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if (
                        key_count_ok
                        and not missing_keys
                        and not bad_keys
                    )
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "all five explicit external AVB signing keys are available"
                    if (
                        key_count_ok
                        and not missing_keys
                        and not bad_keys
                    )
                    else (
                        "external AVB signing-key contract "
                        "is not build-ready"
                    )
                ),
                details=(
                    (
                        (
                            "key declarations: "
                            f"{len(key_entries)} "
                            f"(expected {expected_key_count})"
                        ),
                    )
                    + tuple(
                        (
                            "missing: "
                            + item
                        )
                        for item
                        in missing_keys
                    )
                    + tuple(
                        (
                            "invalid: "
                            + item
                        )
                        for item
                        in bad_keys
                    )
                ),
            )
        )

        if generated_device_root.is_dir():
            module_names = (
                _generated_module_names(
                    generated_device_root
                )
            )

            duplicates = tuple(
                (
                    name,
                    tuple(
                        owners
                    ),
                )
                for name, owners
                in sorted(
                    module_names.items()
                )
                if len(owners) > 1
            )

        else:
            duplicates = ()

        checks.append(
            AndroidAospPreflightCheck(
                check_id="generated-module-identity",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if not duplicates
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    "no obvious duplicate generated module names"
                    if not duplicates
                    else (
                        "generated Device Tree contains duplicate "
                        "Android module identities"
                    )
                ),
                details=tuple(
                    (
                        f"{name}: "
                        + ", ".join(
                            owners
                        )
                    )
                    for name, owners
                    in duplicates
                ),
            )
        )

        missing_dependency_override = (
            os.environ.get(
                "SOONG_ALLOW_MISSING_DEPENDENCIES",
                "",
            )
            .strip()
            .lower()
        )

        override_enabled = (
            missing_dependency_override
            in {
                "1",
                "true",
                "yes",
                "y",
            }
        )

        checks.append(
            AndroidAospPreflightCheck(
                check_id="missing-dependency-policy",
                status=(
                    AndroidAospPreflightStatus.FAIL
                    if override_enabled
                    else AndroidAospPreflightStatus.PASS
                ),
                summary=(
                    "missing-dependency escape hatch is disabled"
                    if not override_enabled
                    else (
                        "SOONG_ALLOW_MISSING_DEPENDENCIES "
                        "is enabled"
                    )
                ),
            )
        )

        source_root_product_makefile = (
            generated_device_root
            / f"{resolved_product}.mk"
        )

        source_root_product_text = (
            _active_text(
                source_root_product_makefile
            )
            if source_root_product_makefile.is_file()
            else ""
        )

        generated_source_root = (
            deployed_device_root
            .relative_to(
                aosp_root
            )
            .as_posix()
        )

        required_source_root_rules = ()

        source_root_assignment_present = (
            "PRODUCT_SOURCE_ROOT_DIRS +="
            in source_root_product_text
        )

        missing_source_root_rules = tuple(
            rule
            for rule
            in required_source_root_rules
            if rule not in source_root_product_text
        )

        source_root_policy_ok = not source_root_assignment_present

        checks.append(
            AndroidAospPreflightCheck(
                check_id="product-source-root-policy",
                status=(
                    AndroidAospPreflightStatus.PASS
                    if source_root_policy_ok
                    else AndroidAospPreflightStatus.FAIL
                ),
                summary=(
                    (
                        "generated product declares "
                        "the required TreeForge Soong source-root policy"
                    )
                    if source_root_policy_ok
                    else (
                        "generated product is missing its "
                        "required TreeForge Soong source-root policy"
                    )
                ),
                details=(
                    (
                        "assignment: "
                        + (
                            "present"
                            if source_root_assignment_present
                            else "missing"
                        )
                    ),
                )
                + tuple(
                    (
                        "required rule: "
                        f"{rule}"
                    )
                    for rule
                    in required_source_root_rules
                )
                + tuple(
                    (
                        "missing rule: "
                        f"{rule}"
                    )
                    for rule
                    in missing_source_root_rules
                ),
            )
        )

        static_failed = any(
            check.status
            is AndroidAospPreflightStatus.FAIL
            for check in checks
        )

        dumpvars_output = ""

        if not run_dumpvars:
            checks.append(
                AndroidAospPreflightCheck(
                    check_id="aosp-dumpvars",
                    status=(
                        AndroidAospPreflightStatus.SKIP
                    ),
                    summary=(
                        "AOSP dumpvars validation was explicitly skipped"
                    ),
                )
            )

        elif static_failed:
            checks.append(
                AndroidAospPreflightCheck(
                    check_id="aosp-dumpvars",
                    status=(
                        AndroidAospPreflightStatus.SKIP
                    ),
                    summary=(
                        "AOSP dumpvars was skipped because "
                        "static preflight blockers remain"
                    ),
                )
            )

        else:
            soong_ui = (
                aosp_root
                / "build"
                / "soong"
                / "soong_ui.bash"
            )

            env = os.environ.copy()

            env.update(
                {
                    "ANDROID_BUILD_TOP": str(
                        aosp_root
                    ),
                    "TOP": str(
                        aosp_root
                    ),
                    "TARGET_PRODUCT": (
                        resolved_product
                    ),
                    "TARGET_RELEASE": release,
                    "TARGET_BUILD_VARIANT": (
                        variant
                    ),
                }
            )

            command = [
                str(
                    soong_ui
                ),
                "--dumpvars-mode",
                (
                    "--vars="
                    + " ".join(
                        _DUMPVARS
                    )
                ),
            ]

            try:
                completed = (
                    subprocess.run(
                        command,
                        cwd=aosp_root,
                        env=env,
                        stdout=(
                            subprocess.PIPE
                        ),
                        stderr=(
                            subprocess.PIPE
                        ),
                        text=True,
                        timeout=180,
                        check=False,
                    )
                )

            except subprocess.TimeoutExpired:
                checks.append(
                    AndroidAospPreflightCheck(
                        check_id="aosp-dumpvars",
                        status=(
                            AndroidAospPreflightStatus.FAIL
                        ),
                        summary=(
                            "AOSP dumpvars exceeded the "
                            "preflight execution cap"
                        ),
                    )
                )

            else:
                dumpvars_output = (
                    completed.stdout
                )

                if completed.stderr:
                    dumpvars_output += (
                        "\n"
                        "=== STDERR ===\n"
                        + completed.stderr
                    )

                product_ok = (
                    "TARGET_PRODUCT="
                    in completed.stdout
                    and resolved_product
                    in completed.stdout
                )

                device_ok = (
                    "TARGET_DEVICE="
                    in completed.stdout
                    and device_name
                    in completed.stdout
                )

                dumpvars_ok = (
                    completed.returncode == 0
                    and product_ok
                    and device_ok
                )

                details = []

                if completed.returncode != 0:
                    details.append(
                        (
                            "return code: "
                            f"{completed.returncode}"
                        )
                    )

                if not product_ok:
                    details.append(
                        (
                            "TARGET_PRODUCT did not resolve "
                            f"to {resolved_product}"
                        )
                    )

                if not device_ok:
                    details.append(
                        (
                            "TARGET_DEVICE did not resolve "
                            f"to {device_name}"
                        )
                    )

                checks.append(
                    AndroidAospPreflightCheck(
                        check_id="aosp-dumpvars",
                        status=(
                            AndroidAospPreflightStatus.PASS
                            if dumpvars_ok
                            else AndroidAospPreflightStatus.FAIL
                        ),
                        summary=(
                            "AOSP product/BoardConfig Make evaluation passed"
                            if dumpvars_ok
                            else (
                                "AOSP product/BoardConfig Make "
                                "evaluation failed"
                            )
                        ),
                        details=tuple(
                            details
                        ),
                    )
                )

        dumpvars_check = next(
            (
                check
                for check in reversed(
                    checks
                )
                if (
                    check.check_id
                    == "aosp-dumpvars"
                )
            ),
            None,
        )

        if (
            dumpvars_check is not None
            and dumpvars_check.status
            is AndroidAospPreflightStatus.PASS
        ):
            source_root_dirs_value = (
                _dumpvars_assignment(
                    dumpvars_output,
                    "PRODUCT_SOURCE_ROOT_DIRS",
                )
            )

            if source_root_dirs_value is None:
                checks.append(
                    AndroidAospPreflightCheck(
                        check_id="soong-namespace-integrity",
                        status=(
                            AndroidAospPreflightStatus.FAIL
                        ),
                        summary=(
                            "AOSP dumpvars did not expose "
                            "PRODUCT_SOURCE_ROOT_DIRS"
                        ),
                    )
                )

            else:
                source_root_dirs = tuple(
                    source_root_dirs_value.split()
                )

                (
                    selected_bp_count,
                    namespace_count,
                    namespace_edge_count,
                    missing_namespace_imports,
                ) = (
                    _aosp_soong_namespace_integrity(
                        aosp_root,
                        source_root_dirs=(
                            source_root_dirs
                        ),
                    )
                )

                namespace_details = [
                    (
                        "PRODUCT_SOURCE_ROOT_DIRS: "
                        + (
                            source_root_dirs_value
                            if source_root_dirs_value
                            else "<empty>"
                        )
                    ),
                    (
                        "selected Android.bp files: "
                        f"{selected_bp_count}"
                    ),
                    (
                        "declared namespaces: "
                        f"{namespace_count}"
                    ),
                    (
                        "namespace import edges: "
                        f"{namespace_edge_count}"
                    ),
                    (
                        "missing imported namespaces: "
                        f"{len(missing_namespace_imports)}"
                    ),
                ]

                namespace_details.extend(
                    missing_namespace_imports[:100]
                )

                if len(
                    missing_namespace_imports
                ) > 100:
                    namespace_details.append(
                        (
                            "... "
                            f"{len(missing_namespace_imports) - 100} "
                            "additional missing namespace imports omitted"
                        )
                    )

                checks.append(
                    AndroidAospPreflightCheck(
                        check_id="soong-namespace-integrity",
                        status=(
                            AndroidAospPreflightStatus.FAIL
                            if missing_namespace_imports
                            else AndroidAospPreflightStatus.PASS
                        ),
                        summary=(
                            (
                                "all product-selected AOSP Soong "
                                "namespace imports resolve"
                            )
                            if not missing_namespace_imports
                            else (
                                "product-selected AOSP contains "
                                "unresolved Soong namespace imports"
                            )
                        ),
                        details=tuple(
                            namespace_details
                        ),
                    )
                )

        else:
            checks.append(
                AndroidAospPreflightCheck(
                    check_id="soong-namespace-integrity",
                    status=(
                        AndroidAospPreflightStatus.SKIP
                    ),
                    summary=(
                        "Soong namespace validation was skipped "
                        "because successful AOSP dumpvars output "
                        "is required for PRODUCT_SOURCE_ROOT_DIRS"
                    ),
                )
            )

        return AndroidAospPreflightResult(
            aosp_root=aosp_root,
            device_root=(
                deployed_device_root
            ),
            generated_device_root=(
                generated_device_root
            ),
            product=resolved_product,
            release=release,
            variant=variant,
            checks=tuple(
                checks
            ),
            dumpvars_output=(
                dumpvars_output
            ),
        )
