from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from treeforge.android.version.device_tree.provider_profile import (
    AndroidDeviceTreePlatformProviderProfile,
)


TREEFORGE_AOSP_BRINGUP_DIAGNOSTIC_ASSIGNMENTS = (
    "BUILD_BROKEN_DUP_RULES := true",
    "BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true",
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePlatformDeploymentSuppression:
    kind: str
    installed_android_path: str
    treeforge_identity: str
    provider_evidence: str
    make_entry: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {
            "copy_file",
            "framework_res",
            "selinux_type",
            "selinux_statement",
            "selinux_file_context",
        }:
            raise ValueError(
                "unsupported platform suppression kind: "
                f"{self.kind}"
            )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        for name, value in (
            (
                "treeforge_identity",
                self.treeforge_identity,
            ),
            (
                "provider_evidence",
                self.provider_evidence,
            ),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} must be non-empty"
                )

        if (
            self.kind == "copy_file"
            and (
                not isinstance(
                    self.make_entry,
                    str,
                )
                or not self.make_entry
            )
        ):
            raise ValueError(
                "copy_file suppression requires its exact Make entry"
            )

        if (
            self.kind != "copy_file"
            and self.make_entry is not None
        ):
            raise ValueError(
                "only copy_file suppressions may carry make_entry"
            )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "installed_android_path": (
                self.installed_android_path
            ),
            "treeforge_identity": (
                self.treeforge_identity
            ),
            "provider_evidence": (
                self.provider_evidence
            ),
            "make_entry": self.make_entry,
        }

    @classmethod
    def from_dict(
        cls,
        value: dict[str, Any],
    ) -> "AndroidDeviceTreePlatformDeploymentSuppression":
        return cls(
            kind=str(
                value["kind"]
            ),
            installed_android_path=str(
                value["installed_android_path"]
            ),
            treeforge_identity=str(
                value["treeforge_identity"]
            ),
            provider_evidence=str(
                value["provider_evidence"]
            ),
            make_entry=(
                None
                if value.get("make_entry") is None
                else str(value["make_entry"])
            ),
        )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreePlatformDeploymentPlan:
    device_root: PurePosixPath
    product_name: str

    suppressions: tuple[
        AndroidDeviceTreePlatformDeploymentSuppression,
        ...,
    ]

    build_diagnostic_assignments: tuple[
        str,
        ...,
    ] = ()

    SCHEMA_VERSION = 4

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.device_root,
            PurePosixPath,
        ):
            raise TypeError(
                "device_root must be a PurePosixPath"
            )

        if (
            self.device_root.is_absolute()
            or ".." in self.device_root.parts
        ):
            raise ValueError(
                "device_root must be a safe relative source path"
            )

        if (
            not isinstance(
                self.product_name,
                str,
            )
            or not self.product_name
        ):
            raise ValueError(
                "product_name must be non-empty"
            )

        if (
            not isinstance(
                self.suppressions,
                tuple,
            )
            or not all(
                isinstance(
                    item,
                    AndroidDeviceTreePlatformDeploymentSuppression,
                )
                for item in self.suppressions
            )
        ):
            raise TypeError(
                "suppressions must contain only "
                "AndroidDeviceTreePlatformDeploymentSuppression"
            )

        expected = tuple(
            sorted(
                self.suppressions,
                key=lambda item: (
                    item.kind,
                    item.installed_android_path,
                    item.treeforge_identity,
                    item.provider_evidence,
                ),
            )
        )

        if self.suppressions != expected:
            raise ValueError(
                "platform suppressions must be deterministic"
            )

        identities = tuple(
            (
                item.kind,
                item.installed_android_path,
                item.treeforge_identity,
            )
            for item in self.suppressions
        )

        if len(identities) != len(
            set(identities)
        ):
            raise ValueError(
                "duplicate platform suppression identity"
            )

        if not isinstance(
            self.build_diagnostic_assignments,
            tuple,
        ):
            raise TypeError(
                "build_diagnostic_assignments must be a tuple"
            )

        if (
            self.build_diagnostic_assignments
            != tuple(
                sorted(
                    self.build_diagnostic_assignments
                )
            )
        ):
            raise ValueError(
                "build diagnostic assignments must be "
                "deterministically sorted"
            )

        if len(
            self.build_diagnostic_assignments
        ) != len(
            set(
                self.build_diagnostic_assignments
            )
        ):
            raise ValueError(
                "build diagnostic assignments must be unique"
            )

        approved = set(
            TREEFORGE_AOSP_BRINGUP_DIAGNOSTIC_ASSIGNMENTS
        )

        unexpected = tuple(
            item
            for item
            in self.build_diagnostic_assignments
            if item not in approved
        )

        if unexpected:
            raise ValueError(
                "unsupported AOSP build diagnostic "
                f"assignment(s): {unexpected}"
            )

    @property
    def copy_file_count(self) -> int:
        return sum(
            item.kind == "copy_file"
            for item in self.suppressions
        )

    @property
    def framework_res_count(self) -> int:
        return sum(
            item.kind == "framework_res"
            for item in self.suppressions
        )

    @property
    def selinux_type_count(self) -> int:
        return sum(
            item.kind == "selinux_type"
            for item in self.suppressions
        )

    @property
    def selinux_statement_count(self) -> int:
        return sum(
            item.kind == "selinux_statement"
            for item in self.suppressions
        )

    @property
    def selinux_file_context_count(
        self,
    ) -> int:
        return sum(
            item.kind == "selinux_file_context"
            for item in self.suppressions
        )

    @property
    def suppressed_copy_make_entries(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.make_entry
                for item in self.suppressions
                if (
                    item.kind == "copy_file"
                    and item.make_entry is not None
                )
            )
        )

    @property
    def suppressed_framework_res_modules(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.treeforge_identity
                for item in self.suppressions
                if item.kind == "framework_res"
            )
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "device_root": (
                self.device_root.as_posix()
            ),
            "product_name": self.product_name,
            "copy_file_count": self.copy_file_count,
            "framework_res_count": (
                self.framework_res_count
            ),
            "selinux_type_count": (
                self.selinux_type_count
            ),
            "selinux_statement_count": (
                self.selinux_statement_count
            ),
            "build_diagnostic_count": len(
                self.build_diagnostic_assignments
            ),
            "build_diagnostic_assignments": list(
                self.build_diagnostic_assignments
            ),
            "suppressions": [
                item.to_dict()
                for item in self.suppressions
            ],
        }

    def write_json(
        self,
        path: Path,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            json.dumps(
                self.to_dict(),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load_json(
        cls,
        path: Path,
    ) -> "AndroidDeviceTreePlatformDeploymentPlan":
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if (
            value.get("schema_version")
            != cls.SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported platform deployment schema"
            )

        raw = value.get("suppressions")

        if not isinstance(raw, list):
            raise ValueError(
                "platform suppressions must be a list"
            )

        raw_diagnostics = value.get(
            "build_diagnostic_assignments"
        )

        if not isinstance(
            raw_diagnostics,
            list,
        ):
            raise ValueError(
                "platform build diagnostic assignments "
                "must be a list"
            )

        plan = cls(
            device_root=PurePosixPath(
                str(value["device_root"])
            ),
            product_name=str(
                value["product_name"]
            ),
            suppressions=tuple(
                sorted(
                    (
                        AndroidDeviceTreePlatformDeploymentSuppression
                        .from_dict(item)
                        for item in raw
                    ),
                    key=lambda item: (
                        item.kind,
                        item.installed_android_path,
                        item.treeforge_identity,
                        item.provider_evidence,
                    ),
                )
            ),
            build_diagnostic_assignments=tuple(
                sorted(
                    str(item)
                    for item
                    in raw_diagnostics
                )
            ),
        )

        for key, actual in (
            (
                "copy_file_count",
                plan.copy_file_count,
            ),
            (
                "framework_res_count",
                plan.framework_res_count,
            ),
            (
                "selinux_type_count",
                plan.selinux_type_count,
            ),
            (
                "selinux_statement_count",
                plan.selinux_statement_count,
            ),
            (
                "build_diagnostic_count",
                len(
                    plan.build_diagnostic_assignments
                ),
            ),
        ):
            if value.get(key) != actual:
                raise ValueError(
                    f"platform {key} mismatch"
                )

        return plan



class AndroidDeviceTreePlatformDeploymentPlanner:
    """
    Build platform-provider overlap exclusively from:
      * generated TreeForge Device Tree build declarations; and
      * the selected TreeForge-owned Android platform-provider profile.

    No Android checkout/source/build-output evidence is consulted.
    """

    _COPY_RE = re.compile(
        r"(?m)^\s*"
        r"(?P<src>device/[^\s:]+)"
        r":"
        r"(?P<dst>\$\([^)]+\)/[^\s\\]+)"
        r"\s*\\?\s*$"
    )

    _TARGET_COPY_OUT = {
        "$(TARGET_COPY_OUT_SYSTEM)": "system",
        "$(TARGET_COPY_OUT_VENDOR)": "vendor",
        "$(TARGET_COPY_OUT_PRODUCT)": "product",
        "$(TARGET_COPY_OUT_SYSTEM_EXT)": (
            "system_ext"
        ),
        "$(TARGET_COPY_OUT_ODM)": "odm",
    }

    _MAKE_BLOCK_RE = re.compile(
        r"(?ms)^"
        r"include \$\(CLEAR_VARS\)\n"
        r".*?"
        r"^include \$\(BUILD_PREBUILT\)\n?"
    )

    _MAKE_MODULE_RE = re.compile(
        r"(?m)^"
        r"LOCAL_MODULE\s*:=\s*(\S+)\s*$"
    )

    _MAKE_PATH_RE = re.compile(
        r"(?m)^"
        r"LOCAL_MODULE_PATH\s*:=\s*(\S+)\s*$"
    )

    _MAKE_STEM_RE = re.compile(
        r"(?m)^"
        r"LOCAL_MODULE_STEM\s*:=\s*(\S+)\s*$"
    )

    _SELINUX_POLICY_PATHS = {
        "vendor": (
            "/vendor/etc/selinux/vendor_sepolicy.cil"
        ),
        "system_ext": (
            "/system_ext/etc/selinux/"
            "system_ext_sepolicy.cil"
        ),
        "product": (
            "/product/etc/selinux/product_sepolicy.cil"
        ),
    }

    @classmethod
    def plan(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        device_root: PurePosixPath,
        generated_device_root: Path,
        vendor_makefile_name: str,
        product_name: str,
        build_diagnostic_assignments: tuple[
            str,
            ...,
        ] = (),
    ) -> AndroidDeviceTreePlatformDeploymentPlan:
        if not isinstance(
            provider_profile,
            AndroidDeviceTreePlatformProviderProfile,
        ):
            raise TypeError(
                "provider_profile must be an "
                "AndroidDeviceTreePlatformProviderProfile"
            )

        generated = (
            generated_device_root
            .expanduser()
            .resolve()
        )

        if not generated.is_dir():
            raise ValueError(
                "generated Device Tree root is missing: "
                f"{generated}"
            )

        vendor_path = (
            generated
            / vendor_makefile_name
        )

        android_mk_path = (
            generated
            / "Android.mk"
        )

        if not vendor_path.is_file():
            raise ValueError(
                "generated vendor Makefile is missing: "
                f"{vendor_path}"
            )

        if not android_mk_path.is_file():
            raise ValueError(
                "generated Android.mk is missing"
            )

        evidence = (
            "TreeForge platform-provider profile: "
            + provider_profile.profile_id
        )

        suppressions = []

        copy_provider_paths = set(
            provider_profile.platform_copy_providers
        )

        vendor_text = vendor_path.read_text(
            encoding="utf-8"
        )

        for (
            source,
            destination,
            installed,
        ) in cls._copy_entries(
            vendor_text
        ):
            if installed not in copy_provider_paths:
                continue

            suppressions.append(
                AndroidDeviceTreePlatformDeploymentSuppression(
                    kind="copy_file",
                    installed_android_path=installed,
                    treeforge_identity=source,
                    provider_evidence=evidence,
                    make_entry=(
                        f"{source}:{destination}"
                    ),
                )
            )

        framework_target = (
            "/system/framework/framework-res.apk"
        )

        if (
            framework_target
            in set(
                provider_profile.framework_res_providers
            )
        ):
            framework_modules = (
                cls._generated_framework_res_modules(
                    android_mk_path
                )
            )

            if len(framework_modules) > 1:
                raise ValueError(
                    "generated Device Tree contains multiple "
                    "framework-res prebuilts"
                )

            if framework_modules:
                suppressions.append(
                    AndroidDeviceTreePlatformDeploymentSuppression(
                        kind="framework_res",
                        installed_android_path=(
                            framework_target
                        ),
                        treeforge_identity=(
                            framework_modules[0]
                        ),
                        provider_evidence=evidence,
                    )
                )

        suppressions.extend(
            cls._selinux_type_suppressions(
                provider_profile=(
                    provider_profile
                ),
                generated_device_root=(
                    generated
                ),
            )
        )

        suppressions.extend(
            cls._selinux_statement_suppressions(
                provider_profile=(
                    provider_profile
                ),
                generated_device_root=(
                    generated
                ),
            )
        )

        suppressions.extend(
            cls._selinux_file_context_suppressions(
                provider_profile=provider_profile,
                generated_device_root=generated,
            )
        )

        return AndroidDeviceTreePlatformDeploymentPlan(
            device_root=device_root,
            product_name=product_name,
            suppressions=tuple(
                sorted(
                    suppressions,
                    key=lambda item: (
                        item.kind,
                        item.installed_android_path,
                        item.treeforge_identity,
                        item.provider_evidence,
                    ),
                )
            ),
            build_diagnostic_assignments=(
                build_diagnostic_assignments
            ),
        )

    @classmethod
    def _copy_entries(
        cls,
        text: str,
    ) -> tuple[
        tuple[str, str, str],
        ...,
    ]:
        result = []

        for match in cls._COPY_RE.finditer(
            text
        ):
            source = match.group("src")
            destination = match.group("dst")

            installed = (
                cls._canonical_copy_destination(
                    destination
                )
            )

            if installed is None:
                continue

            result.append(
                (
                    source,
                    destination,
                    installed,
                )
            )

        return tuple(
            sorted(
                result,
                key=lambda item: (
                    item[2],
                    item[0],
                ),
            )
        )

    @classmethod
    def _canonical_copy_destination(
        cls,
        destination: str,
    ) -> str | None:
        for variable, partition in (
            cls._TARGET_COPY_OUT.items()
        ):
            prefix = variable + "/"

            if not destination.startswith(
                prefix
            ):
                continue

            relative = PurePosixPath(
                destination[
                    len(prefix):
                ]
            )

            if (
                relative.is_absolute()
                or ".." in relative.parts
            ):
                return None

            result = (
                PurePosixPath("/")
                / partition
            )

            for part in relative.parts:
                result /= part

            return result.as_posix()

        return None

    @classmethod
    def _generated_framework_res_modules(
        cls,
        path: Path,
    ) -> tuple[str, ...]:
        modules = []

        text = path.read_text(
            encoding="utf-8"
        )

        for match in cls._MAKE_BLOCK_RE.finditer(
            text
        ):
            block = match.group(0)

            module = cls._MAKE_MODULE_RE.search(
                block
            )

            module_path = cls._MAKE_PATH_RE.search(
                block
            )

            stem = cls._MAKE_STEM_RE.search(
                block
            )

            if (
                module is None
                or module_path is None
                or stem is None
            ):
                continue

            if (
                module_path.group(1)
                == "$(TARGET_OUT)/framework"
                and stem.group(1)
                == "framework-res.apk"
            ):
                modules.append(
                    module.group(1)
                )

        return tuple(
            sorted(
                set(modules)
            )
        )

    @classmethod
    def _selinux_file_context_suppressions(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        generated_device_root: Path,
    ) -> tuple[
        AndroidDeviceTreePlatformDeploymentSuppression,
        ...,
    ]:
        evidence = (
            "TreeForge platform-provider profile: "
            f"{provider_profile.profile_id}"
        )

        result = []

        for relative_text, exact_line in (
            provider_profile.selinux_file_context_providers
        ):
            relative = PurePosixPath(relative_text)

            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not relative.parts
                or relative.parts[0] != "sepolicy"
            ):
                raise ValueError(
                    "invalid SELinux file-context provider path: "
                    f"{relative_text!r}"
                )

            path = (
                generated_device_root
                / Path(relative.as_posix())
            )

            if not path.is_file():
                raise ValueError(
                    "SELinux file-context provider source is missing: "
                    f"{relative}"
                )

            matches = sum(
                raw.strip() == exact_line
                for raw in path.read_text(
                    encoding="utf-8"
                ).splitlines()
            )

            if matches != 1:
                raise ValueError(
                    "SELinux file-context provider coverage mismatch: "
                    f"{relative}::{exact_line!r}, count={matches}"
                )

            installed_policy = (
                "/vendor/etc/selinux/vendor_file_contexts"
                if relative
                == PurePosixPath(
                    "sepolicy/vendor/file_contexts"
                )
                else "/" + relative.as_posix()
            )

            result.append(
                AndroidDeviceTreePlatformDeploymentSuppression(
                    kind="selinux_file_context",
                    installed_android_path=installed_policy,
                    treeforge_identity=(
                        relative.as_posix()
                        + "::"
                        + exact_line
                    ),
                    provider_evidence=evidence,
                )
            )

        return tuple(result)

    @staticmethod
    def _selinux_file_context_identity(
        item: AndroidDeviceTreePlatformDeploymentSuppression,
    ) -> tuple[
        PurePosixPath,
        str,
    ]:
        if item.kind != "selinux_file_context":
            raise ValueError(
                "SELinux file-context identity requested for "
                "non-file-context suppression"
            )

        if "::" not in item.treeforge_identity:
            raise ValueError(
                "invalid SELinux file-context suppression identity"
            )

        source, exact_line = (
            item.treeforge_identity.split(
                "::",
                1,
            )
        )

        relative = PurePosixPath(source)

        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not exact_line
        ):
            raise ValueError(
                "invalid SELinux file-context suppression identity"
            )

        return (
            relative,
            exact_line,
        )


    @classmethod
    def _selinux_type_suppressions(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        generated_device_root: Path,
    ) -> tuple[
        AndroidDeviceTreePlatformDeploymentSuppression,
        ...,
    ]:
        evidence = (
            "TreeForge platform-provider profile: "
            + provider_profile.profile_id
        )

        bare_type_re = re.compile(
            r'^\s*type\s+'
            r'([A-Za-z_][A-Za-z0-9_]*)'
            r'\s*;\s*$'
        )

        result = []

        for (
            partition,
            relative_policy_path,
            type_name,
        ) in provider_profile.selinux_type_providers:
            installed_policy = (
                cls._SELINUX_POLICY_PATHS.get(
                    partition
                )
            )

            if installed_policy is None:
                raise ValueError(
                    "unsupported SELinux provider partition: "
                    f"{partition}"
                )

            relative = PurePosixPath(
                relative_policy_path
            )

            if (
                relative.is_absolute()
                or ".." in relative.parts
            ):
                raise ValueError(
                    "unsafe SELinux provider source path: "
                    f"{relative}"
                )

            path = (
                generated_device_root
                / Path(relative.as_posix())
            )

            if not path.is_file():
                continue

            matches = 0

            for line in path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                match = bare_type_re.match(
                    line
                )

                if (
                    match is not None
                    and match.group(1)
                    == type_name
                ):
                    matches += 1

            if matches == 0:
                continue

            if matches != 1:
                raise ValueError(
                    "ambiguous generated SELinux type declaration: "
                    f"{relative}::{type_name}, count={matches}"
                )

            result.append(
                AndroidDeviceTreePlatformDeploymentSuppression(
                    kind="selinux_type",
                    installed_android_path=(
                        installed_policy
                    ),
                    treeforge_identity=(
                        relative.as_posix()
                        + "::"
                        + type_name
                    ),
                    provider_evidence=evidence,
                )
            )

        return tuple(result)

    @classmethod
    def _selinux_statement_suppressions(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        generated_device_root: Path,
    ) -> tuple[
        AndroidDeviceTreePlatformDeploymentSuppression,
        ...,
    ]:
        evidence = (
            "TreeForge platform-provider profile: "
            + provider_profile.profile_id
        )

        result = []

        for (
            partition,
            kind,
            source_type,
            target_type,
            object_class,
            default_type,
            object_name,
        ) in provider_profile.selinux_statement_providers:
            if kind != "type_transition":
                raise ValueError(
                    "unsupported SELinux provider statement kind: "
                    f"{kind}"
                )

            installed_policy = (
                cls._SELINUX_POLICY_PATHS.get(
                    partition
                )
            )

            if installed_policy is None:
                raise ValueError(
                    "unsupported SELinux statement partition: "
                    f"{partition}"
                )

            statement = (
                f"type_transition {source_type} "
                f"{target_type}:{object_class} "
                f"{default_type}"
            )

            if object_name:
                statement += (
                    f' "{object_name}"'
                )

            statement += ";"

            family_root = (
                generated_device_root
                / "sepolicy"
                / partition
            )

            if not family_root.is_dir():
                continue

            occurrences = []

            for path in sorted(
                family_root.rglob("*.te")
            ):
                count = sum(
                    line.strip() == statement
                    for line in path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ).splitlines()
                )

                if count:
                    occurrences.extend(
                        [path] * count
                    )

            if not occurrences:
                continue

            if len(occurrences) != 1:
                raise ValueError(
                    "ambiguous generated SELinux provider statement: "
                    f"{statement}, count={len(occurrences)}"
                )

            relative = PurePosixPath(
                occurrences[0]
                .relative_to(
                    generated_device_root
                )
                .as_posix()
            )

            result.append(
                AndroidDeviceTreePlatformDeploymentSuppression(
                    kind="selinux_statement",
                    installed_android_path=(
                        installed_policy
                    ),
                    treeforge_identity=(
                        relative.as_posix()
                        + "::statement::"
                        + statement
                    ),
                    provider_evidence=evidence,
                )
            )

        return tuple(result)

    @staticmethod
    def _selinux_type_identity(
        item: AndroidDeviceTreePlatformDeploymentSuppression,
    ) -> tuple[
        PurePosixPath,
        str,
    ]:
        if item.kind != "selinux_type":
            raise ValueError(
                "SELinux type identity requested for wrong kind"
            )

        if "::" not in item.treeforge_identity:
            raise ValueError(
                "invalid SELinux type suppression identity"
            )

        source, name = (
            item.treeforge_identity.rsplit(
                "::",
                1,
            )
        )

        relative = PurePosixPath(
            source
        )

        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not name
        ):
            raise ValueError(
                "invalid SELinux type suppression identity"
            )

        return (
            relative,
            name,
        )

    @staticmethod
    def _selinux_statement_identity(
        item: AndroidDeviceTreePlatformDeploymentSuppression,
    ) -> tuple[
        PurePosixPath,
        str,
    ]:
        if item.kind != "selinux_statement":
            raise ValueError(
                "SELinux statement identity requested for wrong kind"
            )

        marker = "::statement::"

        if marker not in item.treeforge_identity:
            raise ValueError(
                "invalid SELinux statement suppression identity"
            )

        source, statement = (
            item.treeforge_identity.split(
                marker,
                1,
            )
        )

        relative = PurePosixPath(
            source
        )

        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not statement
        ):
            raise ValueError(
                "invalid SELinux statement suppression identity"
            )

        return (
            relative,
            statement,
        )


class AndroidDeviceTreePlatformDeploymentTransformer:
    _MAKE_BLOCK_RE = (
        AndroidDeviceTreePlatformDeploymentPlanner
        ._MAKE_BLOCK_RE
    )

    _MAKE_MODULE_RE = (
        AndroidDeviceTreePlatformDeploymentPlanner
        ._MAKE_MODULE_RE
    )

    @classmethod
    def transform_vendor_makefile(
        cls,
        text: str,
        *,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
    ) -> str:
        targets = set(
            plan.suppressed_copy_make_entries
        )

        if not targets:
            return text

        lines = text.splitlines(
            keepends=True
        )

        result = []
        index = 0

        counts = {
            entry: 0
            for entry in targets
        }

        while index < len(lines):
            line = lines[index]

            if (
                line.strip()
                != "PRODUCT_COPY_FILES += \\"
            ):
                result.append(line)
                index += 1
                continue

            header = line
            entries = []
            cursor = index + 1

            while cursor < len(lines):
                raw = lines[cursor]
                stripped = raw.strip()

                if not stripped:
                    break

                continued = (
                    stripped.endswith("\\")
                )

                token = (
                    stripped[:-1].rstrip()
                    if continued
                    else stripped
                )

                entries.append(token)
                cursor += 1

                if not continued:
                    break

            if not any(
                token in targets
                for token in entries
            ):
                result.append(header)
                result.extend(
                    lines[
                        index + 1:
                        cursor
                    ]
                )
                index = cursor
                continue

            retained = []

            for token in entries:
                if token in targets:
                    counts[token] += 1
                else:
                    retained.append(token)

            if retained:
                result.append(header)

                for number, token in enumerate(
                    retained
                ):
                    suffix = (
                        " \\\n"
                        if number
                        < len(retained) - 1
                        else "\n"
                    )

                    result.append(
                        "    "
                        + token
                        + suffix
                    )

            index = cursor

        bad = {
            entry: count
            for entry, count
            in counts.items()
            if count != 1
        }

        if bad:
            raise ValueError(
                "platform PRODUCT_COPY_FILES suppression "
                f"coverage mismatch: {bad}"
            )

        return "".join(result)

    @classmethod
    def transform_android_mk(
        cls,
        text: str,
        *,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
    ) -> str:
        targets = set(
            plan.suppressed_framework_res_modules
        )

        if not targets:
            return text

        counts = {
            name: 0
            for name in targets
        }

        def remove(
            match: re.Match[str],
        ) -> str:
            block = match.group(0)

            module = (
                cls._MAKE_MODULE_RE.search(
                    block
                )
            )

            if module is None:
                return block

            name = module.group(1)

            if name not in targets:
                return block

            counts[name] += 1
            return ""

        result = (
            cls._MAKE_BLOCK_RE.sub(
                remove,
                text,
            )
        )

        bad = {
            name: count
            for name, count
            in counts.items()
            if count != 1
        }

        if bad:
            raise ValueError(
                "framework-res suppression coverage mismatch: "
                f"{bad}"
            )

        return result

    @classmethod
    def transform_selinux_policy(
        cls,
        text: str,
        *,
        relative: PurePosixPath,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
    ) -> str:
        type_names = set()
        statements = set()

        for item in plan.suppressions:
            if item.kind == "selinux_type":
                (
                    source,
                    name,
                ) = (
                    AndroidDeviceTreePlatformDeploymentPlanner
                    ._selinux_type_identity(
                        item
                    )
                )

                if source == relative:
                    type_names.add(name)

            elif item.kind == "selinux_statement":
                (
                    source,
                    statement,
                ) = (
                    AndroidDeviceTreePlatformDeploymentPlanner
                    ._selinux_statement_identity(
                        item
                    )
                )

                if source == relative:
                    statements.add(
                        statement
                    )

        if not type_names and not statements:
            return text

        type_counts = {
            name: 0
            for name in type_names
        }

        statement_counts = {
            statement: 0
            for statement in statements
        }

        declaration_re = re.compile(
            r'^\s*type\s+'
            r'([A-Za-z_][A-Za-z0-9_]*)'
            r'\s*;\s*$'
        )

        output = []

        for line in text.splitlines(
            keepends=True
        ):
            candidate = line.rstrip(
                "\r\n"
            )

            declaration = (
                declaration_re.match(
                    candidate
                )
            )

            if (
                declaration is not None
                and declaration.group(1)
                in type_names
            ):
                type_counts[
                    declaration.group(1)
                ] += 1
                continue

            stripped = candidate.strip()

            if stripped in statements:
                statement_counts[
                    stripped
                ] += 1
                continue

            output.append(line)

        bad_types = {
            name: count
            for name, count
            in type_counts.items()
            if count != 1
        }

        bad_statements = {
            statement: count
            for statement, count
            in statement_counts.items()
            if count != 1
        }

        if bad_types or bad_statements:
            raise ValueError(
                "SELinux provider suppression coverage mismatch: "
                f"types={bad_types}, "
                f"statements={bad_statements}"
            )

        return "".join(output)

    @staticmethod
    def transform_board_config(
        text: str,
        *,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
    ) -> str:
        assignments = (
            plan.build_diagnostic_assignments
        )

        if not assignments:
            return text

        variables = tuple(
            assignment.split(
                " := ",
                1,
            )[0]
            for assignment in assignments
        )

        for variable in variables:
            occurrences = len(
                re.findall(
                    rf"(?m)^\s*"
                    rf"{re.escape(variable)}"
                    rf"\s*[:?+]?=\s*.*$",
                    text,
                )
            )

            if occurrences:
                raise ValueError(
                    "canonical BoardConfig unexpectedly "
                    "already owns deployment-only diagnostic "
                    f"{variable}: occurrences={occurrences}"
                )

        base = text.rstrip(
            "\n"
        )

        return (
            base
            + "\n\n"
            + "# TreeForge AOSP bring-up diagnostics.\n"
            + "# Deployment-only; not canonical Device Tree content.\n"
            + "\n".join(
                assignments
            )
            + "\n"
        )

    @classmethod
    def transform_selinux_file_contexts(
        cls,
        text: str,
        *,
        relative: PurePosixPath,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
    ) -> str:
        targets = set()

        for item in plan.suppressions:
            if item.kind != "selinux_file_context":
                continue

            source, exact_line = (
                AndroidDeviceTreePlatformDeploymentPlanner
                ._selinux_file_context_identity(
                    item
                )
            )

            if source == relative:
                targets.add(exact_line)

        if not targets:
            return text

        counts = {
            line: 0
            for line in targets
        }

        output = []

        for raw in text.splitlines(
            keepends=True
        ):
            candidate = raw.strip()

            if candidate in targets:
                counts[candidate] += 1
                continue

            output.append(raw)

        bad = {
            line: count
            for line, count in counts.items()
            if count != 1
        }

        if bad:
            raise ValueError(
                "SELinux file-context suppression coverage mismatch: "
                f"{bad}"
            )

        return "".join(output)


    @classmethod
    def transform_expected_bytes(
        cls,
        *,
        relative: PurePosixPath,
        expected: bytes,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
        vendor_makefile_name: str,
    ) -> bytes:
        if relative == PurePosixPath(
            "BoardConfig.mk"
        ):
            return (
                cls.transform_board_config(
                    expected.decode(
                        "utf-8"
                    ),
                    plan=plan,
                )
                .encode(
                    "utf-8"
                )
            )

        if relative == PurePosixPath(
            vendor_makefile_name
        ):
            return (
                cls.transform_vendor_makefile(
                    expected.decode("utf-8"),
                    plan=plan,
                )
                .encode("utf-8")
            )

        if relative == PurePosixPath(
            "Android.mk"
        ):
            return (
                cls.transform_android_mk(
                    expected.decode("utf-8"),
                    plan=plan,
                )
                .encode("utf-8")
            )

        if (
            relative.parts
            and relative.parts[0]
            == "sepolicy"
            and relative.suffix == ".te"
        ):
            return (
                cls.transform_selinux_policy(
                    expected.decode("utf-8"),
                    relative=relative,
                    plan=plan,
                )
                .encode("utf-8")
            )

        if (
            relative.parts
            and relative.parts[0] == "sepolicy"
            and relative.name == "file_contexts"
        ):
            return (
                cls.transform_selinux_file_contexts(
                    expected.decode("utf-8"),
                    relative=relative,
                    plan=plan,
                )
                .encode("utf-8")
            )

        return expected

    @classmethod
    def apply(
        cls,
        *,
        staged_device_root: Path,
        plan: AndroidDeviceTreePlatformDeploymentPlan,
        vendor_makefile_name: str,
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        changed = []

        if plan.build_diagnostic_assignments:
            relative = PurePosixPath(
                "BoardConfig.mk"
            )

            path = (
                staged_device_root
                / "BoardConfig.mk"
            )

            if not path.is_file():
                raise ValueError(
                    "staged root BoardConfig.mk is missing"
                )

            original = path.read_text(
                encoding="utf-8"
            )

            transformed = (
                cls.transform_board_config(
                    original,
                    plan=plan,
                )
            )

            if transformed == original:
                raise ValueError(
                    "non-empty AOSP build diagnostic plan "
                    "did not change BoardConfig.mk"
                )

            path.write_text(
                transformed,
                encoding="utf-8",
            )

            changed.append(
                relative
            )

        if plan.copy_file_count:
            relative = PurePosixPath(
                vendor_makefile_name
            )

            path = (
                staged_device_root
                / relative
            )

            original = path.read_text(
                encoding="utf-8"
            )

            transformed = (
                cls.transform_vendor_makefile(
                    original,
                    plan=plan,
                )
            )

            if transformed == original:
                raise ValueError(
                    "platform copy suppression did not "
                    "change vendor Makefile"
                )

            path.write_text(
                transformed,
                encoding="utf-8",
            )

            changed.append(relative)

        if plan.framework_res_count:
            relative = PurePosixPath(
                "Android.mk"
            )

            path = (
                staged_device_root
                / relative
            )

            original = path.read_text(
                encoding="utf-8"
            )

            transformed = (
                cls.transform_android_mk(
                    original,
                    plan=plan,
                )
            )

            if transformed == original:
                raise ValueError(
                    "framework-res suppression did not "
                    "change Android.mk"
                )

            path.write_text(
                transformed,
                encoding="utf-8",
            )

            changed.append(relative)

        selinux_paths = set()

        for item in plan.suppressions:
            if item.kind == "selinux_type":
                relative, _ = (
                    AndroidDeviceTreePlatformDeploymentPlanner
                    ._selinux_type_identity(
                        item
                    )
                )

            elif item.kind == "selinux_statement":
                relative, _ = (
                    AndroidDeviceTreePlatformDeploymentPlanner
                    ._selinux_statement_identity(
                        item
                    )
                )

            else:
                continue

            selinux_paths.add(relative)

        for relative in sorted(
            selinux_paths,
            key=lambda item: (
                item.as_posix()
            ),
        ):
            path = (
                staged_device_root
                / Path(
                    relative.as_posix()
                )
            )

            if not path.is_file():
                raise ValueError(
                    "SELinux deployment source missing: "
                    f"{relative}"
                )

            original = path.read_text(
                encoding="utf-8"
            )

            transformed = (
                cls.transform_selinux_policy(
                    original,
                    relative=relative,
                    plan=plan,
                )
            )

            if transformed == original:
                raise ValueError(
                    "SELinux provider suppression did not "
                    "change source: "
                    f"{relative}"
                )

            path.write_text(
                transformed,
                encoding="utf-8",
            )

            changed.append(relative)

        file_context_paths = set()

        for item in plan.suppressions:
            if item.kind != "selinux_file_context":
                continue

            relative, _ = (
                AndroidDeviceTreePlatformDeploymentPlanner
                ._selinux_file_context_identity(
                    item
                )
            )

            file_context_paths.add(relative)

        for relative in sorted(
            file_context_paths,
            key=lambda item: item.as_posix(),
        ):
            path = (
                staged_device_root
                / Path(relative.as_posix())
            )

            if not path.is_file():
                raise ValueError(
                    "SELinux file-context deployment source missing: "
                    f"{relative}"
                )

            original = path.read_text(
                encoding="utf-8"
            )

            transformed = (
                cls.transform_selinux_file_contexts(
                    original,
                    relative=relative,
                    plan=plan,
                )
            )

            if transformed == original:
                raise ValueError(
                    "SELinux file-context suppression did not "
                    f"change source: {relative}"
                )

            path.write_text(
                transformed,
                encoding="utf-8",
            )

            changed.append(relative)


        return tuple(
            sorted(
                set(changed),
                key=lambda item: (
                    item.as_posix()
                ),
            )
        )
