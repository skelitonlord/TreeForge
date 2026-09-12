from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re

from treeforge.android.device_tree.vintf_build import (
    AndroidDeviceTreeVintfBuildConfig,
)
from treeforge.android.version.device_tree.provider_profile import (
    AndroidDeviceTreePlatformProviderProfile,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVintfDeploymentSuppression:
    representation_id: str
    module_name: str
    installed_android_path: str
    provider_module_name: str
    provider_profile_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("representation_id", self.representation_id),
            ("module_name", self.module_name),
            (
                "installed_android_path",
                self.installed_android_path,
            ),
            (
                "provider_module_name",
                self.provider_module_name,
            ),
            (
                "provider_profile_id",
                self.provider_profile_id,
            ),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        if not self.installed_android_path.startswith("/"):
            raise ValueError(
                "installed_android_path must be absolute"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "representation_id": self.representation_id,
            "module_name": self.module_name,
            "installed_android_path": (
                self.installed_android_path
            ),
            "provider_module_name": (
                self.provider_module_name
            ),
            "provider_profile_id": (
                self.provider_profile_id
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value: dict[str, object],
    ) -> "AndroidDeviceTreeVintfDeploymentSuppression":
        return cls(
            representation_id=str(
                value["representation_id"]
            ),
            module_name=str(
                value["module_name"]
            ),
            installed_android_path=str(
                value["installed_android_path"]
            ),
            provider_module_name=str(
                value["provider_module_name"]
            ),
            provider_profile_id=str(
                value["provider_profile_id"]
            ),
        )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVintfDeploymentPlan:
    device_root: PurePosixPath
    suppressions: tuple[
        AndroidDeviceTreeVintfDeploymentSuppression,
        ...,
    ]

    SCHEMA_VERSION = 2

    def __post_init__(self) -> None:
        if not isinstance(
            self.device_root,
            PurePosixPath,
        ):
            raise TypeError(
                "device_root must be PurePosixPath"
            )

        if (
            self.device_root.is_absolute()
            or ".." in self.device_root.parts
        ):
            raise ValueError(
                "device_root must be a safe relative path"
            )

        expected = tuple(
            sorted(
                self.suppressions,
                key=lambda item: (
                    item.installed_android_path,
                    item.module_name,
                    item.representation_id,
                ),
            )
        )

        if self.suppressions != expected:
            raise ValueError(
                "VINTF suppressions must be deterministic"
            )

        for values, label in (
            (
                tuple(
                    item.representation_id
                    for item in self.suppressions
                ),
                "representation IDs",
            ),
            (
                tuple(
                    item.module_name
                    for item in self.suppressions
                ),
                "module names",
            ),
            (
                tuple(
                    item.installed_android_path
                    for item in self.suppressions
                ),
                "installed paths",
            ),
        ):
            if len(values) != len(set(values)):
                raise ValueError(
                    f"VINTF deployment {label} must be unique"
                )

    @property
    def suppressed_module_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            item.module_name
            for item in self.suppressions
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "device_root": self.device_root.as_posix(),
            "suppression_count": len(
                self.suppressions
            ),
            "suppressions": [
                item.to_dict()
                for item in self.suppressions
            ],
        }

    def write_json(self, path: Path) -> None:
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
    ) -> "AndroidDeviceTreeVintfDeploymentPlan":
        raw = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if (
            raw.get("schema_version")
            != cls.SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported VINTF deployment schema"
            )

        items = raw.get("suppressions")

        if not isinstance(items, list):
            raise ValueError(
                "VINTF suppressions must be a list"
            )

        plan = cls(
            device_root=PurePosixPath(
                str(raw["device_root"])
            ),
            suppressions=tuple(
                sorted(
                    (
                        AndroidDeviceTreeVintfDeploymentSuppression
                        .from_dict(item)
                        for item in items
                    ),
                    key=lambda item: (
                        item.installed_android_path,
                        item.module_name,
                        item.representation_id,
                    ),
                )
            ),
        )

        if raw.get("suppression_count") != len(
            plan.suppressions
        ):
            raise ValueError(
                "VINTF suppression count mismatch"
            )

        return plan


class AndroidDeviceTreeVintfDeploymentPlanner:
    """
    Resolve VINTF target-provider overlap exclusively from the selected
    TreeForge platform-provider profile.

    Canonical VINTF provenance/partition ownership remains factory-derived.
    """

    @classmethod
    def plan(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        device_root: PurePosixPath,
        config: AndroidDeviceTreeVintfBuildConfig,
    ) -> AndroidDeviceTreeVintfDeploymentPlan:
        if not isinstance(
            provider_profile,
            AndroidDeviceTreePlatformProviderProfile,
        ):
            raise TypeError(
                "provider_profile must be an "
                "AndroidDeviceTreePlatformProviderProfile"
            )

        if not isinstance(
            config,
            AndroidDeviceTreeVintfBuildConfig,
        ):
            raise TypeError(
                "config must be an AndroidDeviceTreeVintfBuildConfig"
            )

        fragment_by_id = {
            item.representation_id: item
            for item in config.fragment_modules
        }

        if len(fragment_by_id) != len(
            config.fragment_modules
        ):
            raise ValueError(
                "VINTF fragment representation IDs are not unique"
            )

        suppressions = []

        for (
            representation_id,
            installed_android_path,
            provider_module_name,
        ) in provider_profile.vintf_providers:
            fragment = fragment_by_id.get(
                representation_id
            )

            if fragment is None:
                continue

            suppressions.append(
                AndroidDeviceTreeVintfDeploymentSuppression(
                    representation_id=(
                        representation_id
                    ),
                    module_name=(
                        fragment.module_name
                    ),
                    installed_android_path=(
                        installed_android_path
                    ),
                    provider_module_name=(
                        provider_module_name
                    ),
                    provider_profile_id=(
                        provider_profile.profile_id
                    ),
                )
            )

        return AndroidDeviceTreeVintfDeploymentPlan(
            device_root=device_root,
            suppressions=tuple(
                sorted(
                    suppressions,
                    key=lambda item: (
                        item.installed_android_path,
                        item.module_name,
                        item.representation_id,
                    ),
                )
            ),
        )


class AndroidDeviceTreeVintfDeploymentTransformer:
    _BLOCK_RE = re.compile(
        r"(?ms)^vintf_fragment \{\n.*?^\}\n(?:\n)?"
    )

    _NAME_RE = re.compile(
        r'(?m)^\s*name:\s*"([^"]+)",\s*$'
    )

    @classmethod
    def transform_android_bp(
        cls,
        text: str,
        *,
        suppressed_module_names: tuple[str, ...],
    ) -> str:
        targets = set(
            suppressed_module_names
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
            found = cls._NAME_RE.search(
                block
            )

            if found is None:
                return block

            name = found.group(1)

            if name not in targets:
                return block

            counts[name] += 1
            return ""

        result = cls._BLOCK_RE.sub(
            remove,
            text,
        )

        bad = {
            name: count
            for name, count
            in counts.items()
            if count != 1
        }

        if bad:
            raise ValueError(
                "VINTF Android.bp suppression coverage "
                f"mismatch: {bad}"
            )

        return result

    @staticmethod
    def transform_vendor_makefile(
        text: str,
        *,
        suppressed_module_names: tuple[str, ...],
    ) -> str:
        targets = set(
            suppressed_module_names
        )

        if not targets:
            return text

        lines = text.splitlines(
            keepends=True
        )

        counts = {
            name: 0
            for name in targets
        }

        result = []
        index = 0

        while index < len(lines):
            line = lines[index]

            if (
                line.strip()
                != "PRODUCT_PACKAGES += \\"
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

                continued = stripped.endswith(
                    "\\"
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
            name: count
            for name, count
            in counts.items()
            if count != 1
        }

        if bad:
            raise ValueError(
                "VINTF PRODUCT_PACKAGES suppression "
                f"coverage mismatch: {bad}"
            )

        return "".join(result)

    @classmethod
    def apply(
        cls,
        *,
        staged_device_root: Path,
        plan: AndroidDeviceTreeVintfDeploymentPlan,
        vendor_makefile_name: str,
    ) -> tuple[PurePosixPath, ...]:
        names = plan.suppressed_module_names

        if not names:
            return ()

        bp_relative = PurePosixPath(
            "vintf/Android.bp"
        )

        vendor_relative = PurePosixPath(
            vendor_makefile_name
        )

        bp_path = (
            staged_device_root
            / Path(bp_relative.as_posix())
        )

        vendor_path = (
            staged_device_root
            / vendor_makefile_name
        )

        if not bp_path.is_file():
            raise ValueError(
                "staged VINTF Android.bp is missing"
            )

        if not vendor_path.is_file():
            raise ValueError(
                "staged vendor Makefile is missing"
            )

        original_bp = bp_path.read_text(
            encoding="utf-8"
        )

        original_vendor = (
            vendor_path.read_text(
                encoding="utf-8"
            )
        )

        transformed_bp = (
            cls.transform_android_bp(
                original_bp,
                suppressed_module_names=names,
            )
        )

        transformed_vendor = (
            cls.transform_vendor_makefile(
                original_vendor,
                suppressed_module_names=names,
            )
        )

        if transformed_bp == original_bp:
            raise ValueError(
                "non-empty VINTF provider plan did not "
                "change vintf/Android.bp"
            )

        if transformed_vendor == original_vendor:
            raise ValueError(
                "non-empty VINTF provider plan did not "
                "change PRODUCT_PACKAGES"
            )

        bp_path.write_text(
            transformed_bp,
            encoding="utf-8",
        )

        vendor_path.write_text(
            transformed_vendor,
            encoding="utf-8",
        )

        return (
            bp_relative,
            vendor_relative,
        )
