from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)
from treeforge.android.version.device_tree.provider_profile import (
    AndroidDeviceTreePlatformProviderProfile,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeElfDeploymentSuppression:
    representation_id: str
    module_name: str
    installed_android_path: str
    representation_kind: str

    provider_module_name: str
    provider_profile_id: str

    def __post_init__(self) -> None:
        for field_name, value in (
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "module_name",
                self.module_name,
            ),
            (
                "installed_android_path",
                self.installed_android_path,
            ),
            (
                "representation_kind",
                self.representation_kind,
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
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not self.installed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "installed_android_path must be absolute"
            )

        if self.representation_kind not in {
            "executable",
            "native_library",
        }:
            raise ValueError(
                "unsupported ELF deployment representation kind: "
                f"{self.representation_kind!r}"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "representation_id": (
                self.representation_id
            ),
            "module_name": self.module_name,
            "installed_android_path": (
                self.installed_android_path
            ),
            "representation_kind": (
                self.representation_kind
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
    ) -> "AndroidDeviceTreeElfDeploymentSuppression":
        if not isinstance(value, dict):
            raise TypeError(
                "ELF deployment suppression must be an object"
            )

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
            representation_kind=str(
                value["representation_kind"]
            ),
            provider_module_name=str(
                value["provider_module_name"]
            ),
            provider_profile_id=str(
                value["provider_profile_id"]
            ),
        )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeElfDeploymentPlan:
    device_root: PurePosixPath

    suppressions: tuple[
        AndroidDeviceTreeElfDeploymentSuppression,
        ...,
    ]

    SCHEMA_VERSION = 2

    def __post_init__(self) -> None:
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
                "device_root must be a safe relative path"
            )

        if not isinstance(
            self.suppressions,
            tuple,
        ):
            raise TypeError(
                "suppressions must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidDeviceTreeElfDeploymentSuppression,
            )
            for item in self.suppressions
        ):
            raise TypeError(
                "suppressions contains an invalid model"
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
                "ELF deployment suppressions must be "
                "deterministically sorted"
            )

        module_names = tuple(
            item.module_name
            for item in self.suppressions
        )

        if len(module_names) != len(
            set(module_names)
        ):
            raise ValueError(
                "ELF deployment module names must be unique"
            )

        representation_ids = tuple(
            item.representation_id
            for item in self.suppressions
        )

        if len(representation_ids) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "ELF deployment representation IDs "
                "must be unique"
            )

        installed_paths = tuple(
            item.installed_android_path
            for item in self.suppressions
        )

        if len(installed_paths) != len(
            set(installed_paths)
        ):
            raise ValueError(
                "ELF deployment suppression paths "
                "must be unique"
            )

    @property
    def suppressed_module_names(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            item.module_name
            for item in self.suppressions
        )

    @property
    def executable_count(self) -> int:
        return sum(
            1
            for item in self.suppressions
            if item.representation_kind
            == "executable"
        )

    @property
    def native_library_count(self) -> int:
        return sum(
            1
            for item in self.suppressions
            if item.representation_kind
            == "native_library"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "device_root": self.device_root.as_posix(),
            "suppression_count": len(
                self.suppressions
            ),
            "executable_count": (
                self.executable_count
            ),
            "native_library_count": (
                self.native_library_count
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
        if not isinstance(path, Path):
            raise TypeError(
                "path must be a Path"
            )

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
    ) -> "AndroidDeviceTreeElfDeploymentPlan":
        if not isinstance(path, Path):
            raise TypeError(
                "path must be a Path"
            )

        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(value, dict):
            raise ValueError(
                "ELF deployment plan must be an object"
            )

        if value.get(
            "schema_version"
        ) != cls.SCHEMA_VERSION:
            raise ValueError(
                "unsupported ELF deployment plan schema"
            )

        raw = value.get(
            "suppressions"
        )

        if not isinstance(raw, list):
            raise ValueError(
                "ELF deployment suppressions must be a list"
            )

        plan = cls(
            device_root=PurePosixPath(
                str(value["device_root"])
            ),
            suppressions=tuple(
                sorted(
                    (
                        AndroidDeviceTreeElfDeploymentSuppression
                        .from_dict(item)
                        for item in raw
                    ),
                    key=lambda item: (
                        item.installed_android_path,
                        item.module_name,
                        item.representation_id,
                    ),
                )
            ),
        )

        if value.get(
            "suppression_count"
        ) != len(plan.suppressions):
            raise ValueError(
                "ELF deployment suppression count mismatch"
            )

        if value.get(
            "executable_count"
        ) != plan.executable_count:
            raise ValueError(
                "ELF executable suppression count mismatch"
            )

        if value.get(
            "native_library_count"
        ) != plan.native_library_count:
            raise ValueError(
                "ELF native-library suppression count mismatch"
            )

        return plan


class AndroidDeviceTreeElfDeploymentPlanner:
    """
    Resolve platform-provided ELF overlap from stable Reconstruction/Device
    Tree representation identities.

    No source checkout, Android.bp scan, or target install graph is consulted.
    """

    @classmethod
    def plan(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        device_root: PurePosixPath,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> AndroidDeviceTreeElfDeploymentPlan:
        if not isinstance(
            provider_profile,
            AndroidDeviceTreePlatformProviderProfile,
        ):
            raise TypeError(
                "provider_profile must be an "
                "AndroidDeviceTreePlatformProviderProfile"
            )

        if not isinstance(device_root, PurePosixPath):
            raise TypeError(
                "device_root must be a PurePosixPath"
            )

        if (
            not isinstance(realizations, tuple)
            or not all(
                isinstance(
                    item,
                    AndroidDeviceTreeBuildRealization,
                )
                for item in realizations
            )
        ):
            raise TypeError(
                "realizations contains an invalid model"
            )

        provider_by_id = {
            representation_id: (
                representation_kind,
                provider_module_name,
            )
            for (
                representation_id,
                representation_kind,
                provider_module_name,
            )
            in provider_profile.elf_providers
        }

        if len(provider_by_id) != len(
            provider_profile.elf_providers
        ):
            raise ValueError(
                "ELF provider profile contains duplicate "
                "representation identities"
            )

        suppressions = []

        for realization in realizations:
            provider = provider_by_id.get(
                realization.representation_id
            )

            if provider is None:
                continue

            (
                expected_representation_kind,
                provider_module_name,
            ) = provider

            if (
                realization.status
                is not
                AndroidDeviceTreeBuildRealizationStatus.RESOLVED
            ):
                raise ValueError(
                    "platform-provided ELF realization is not resolved: "
                    f"{realization.representation_id}"
                )

            if (
                realization.kind
                is not
                AndroidDeviceTreeBuildRealizationKind.PREBUILT_MODULE
            ):
                raise ValueError(
                    "platform-provided ELF does not map to "
                    "PREBUILT_MODULE: "
                    f"{realization.representation_id}"
                )

            representation = (
                realization.build_representation
            )

            if (
                representation.kind
                is
                AndroidReconstructionBuildRepresentationKind.EXECUTABLE
            ):
                representation_kind = "executable"

            elif (
                representation.kind
                is
                AndroidReconstructionBuildRepresentationKind.NATIVE_LIBRARY
            ):
                representation_kind = "native_library"

            else:
                raise ValueError(
                    "platform ELF provider maps to non-ELF "
                    "representation: "
                    f"{realization.representation_id}"
                )

            if (
                representation_kind
                != expected_representation_kind
            ):
                raise ValueError(
                    "ELF provider profile kind disagrees with "
                    "canonical Reconstruction: "
                    f"{realization.representation_id}"
                )

            installed_android_path = (
                representation.installed_android_path
            )

            if (
                not isinstance(installed_android_path, str)
                or not installed_android_path.startswith("/")
            ):
                raise ValueError(
                    "platform-provided ELF lacks canonical "
                    "installed Android path: "
                    f"{realization.representation_id}"
                )

            if not realization.module_name:
                raise ValueError(
                    "platform-provided ELF realization has no "
                    "TreeForge module name"
                )

            suppressions.append(
                AndroidDeviceTreeElfDeploymentSuppression(
                    representation_id=(
                        realization.representation_id
                    ),
                    module_name=(
                        realization.module_name
                    ),
                    installed_android_path=(
                        installed_android_path
                    ),
                    representation_kind=(
                        representation_kind
                    ),
                    provider_module_name=(
                        provider_module_name
                    ),
                    provider_profile_id=(
                        provider_profile.profile_id
                    ),
                )
            )

        return AndroidDeviceTreeElfDeploymentPlan(
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



class AndroidDeviceTreeElfDeploymentTransformer:
    """
    Remove only TreeForge ELF build declarations proven to be supplied
    by the selected TreeForge platform-provider profile.

    Canonical factory payload files remain in the deployed proprietary
    directory as evidence/materialized payloads. Only build participation
    is suppressed.
    """

    _ELF_BLOCK_RE = re.compile(
        r"(?ms)^"
        r"(?:cc_prebuilt_binary|cc_prebuilt_library_shared)"
        r" \{\n.*?^\}\n(?:\n)?"
    )

    _MODULE_NAME_RE = re.compile(
        r'(?m)^\s*name:\s*"([^"]+)",\s*$'
    )

    @classmethod
    def transform_android_bp(
        cls,
        text: str,
        *,
        suppressed_module_names: tuple[
            str,
            ...,
        ],
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

        def replace(
            match: re.Match[str],
        ) -> str:
            block = match.group(0)

            name_match = (
                cls._MODULE_NAME_RE.search(
                    block
                )
            )

            if name_match is None:
                return block

            name = name_match.group(1)

            if name not in targets:
                return block

            counts[name] += 1

            return ""

        result = cls._ELF_BLOCK_RE.sub(
            replace,
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
                "ELF deployment Android.bp "
                "suppression coverage mismatch: "
                f"{bad}"
            )

        return result

    @staticmethod
    def transform_vendor_makefile(
        text: str,
        *,
        suppressed_module_names: tuple[
            str,
            ...,
        ],
        module_replacements: tuple[
            tuple[str, str],
            ...,
        ],
    ) -> str:
        """
        Remove matching PRODUCT_PACKAGES entries if the generated product
        happens to name an ELF module explicitly.

        Zero occurrences are valid because installable Soong modules can
        participate without this generated makefile owning the package list.
        More than one occurrence is rejected.
        """

        targets = set(
            suppressed_module_names
        )

        replacements = dict(
            module_replacements
        )

        if len(replacements) != len(
            module_replacements
        ):
            raise ValueError(
                "ELF deployment module replacements contain "
                "duplicate TreeForge module identities"
            )

        if set(replacements) != targets:
            raise ValueError(
                "ELF deployment module replacements must "
                "exactly cover suppressed module identities"
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
        i = 0

        while i < len(lines):
            line = lines[i]

            if (
                line.strip()
                != "PRODUCT_PACKAGES += \\"
            ):
                result.append(line)
                i += 1
                continue

            header = line
            block = []
            j = i + 1

            while j < len(lines):
                raw = lines[j]
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

                block.append(
                    (
                        token,
                        raw,
                    )
                )

                j += 1

                if not continued:
                    break

            matched = any(
                token in targets
                for token, _
                in block
            )

            if not matched:
                result.append(header)

                result.extend(
                    raw
                    for _, raw in block
                )

                i = j
                continue

            retained = []

            for token, raw in block:
                if token in targets:
                    counts[token] += 1
                    replacement = replacements[
                        token
                    ]

                    if replacement not in retained:
                        retained.append(
                            replacement
                        )

                    continue

                if token not in retained:
                    retained.append(token)

            if retained:
                result.append(header)

                for index, token in enumerate(
                    retained
                ):
                    suffix = (
                        " \\\n"
                        if index
                        < len(retained) - 1
                        else "\n"
                    )

                    result.append(
                        "    "
                        + token
                        + suffix
                    )

            i = j

        bad = {
            name: count
            for name, count
            in counts.items()
            if count > 1
        }

        if bad:
            raise ValueError(
                "ELF deployment PRODUCT_PACKAGES "
                "suppression is ambiguous: "
                f"{bad}"
            )

        return "".join(result)

    @classmethod
    def apply(
        cls,
        *,
        staged_device_root: Path,
        plan: AndroidDeviceTreeElfDeploymentPlan,
        vendor_makefile_name: str,
    ) -> tuple[PurePosixPath, ...]:
        if not isinstance(
            staged_device_root,
            Path,
        ):
            raise TypeError(
                "staged_device_root must be a Path"
            )

        if not isinstance(
            plan,
            AndroidDeviceTreeElfDeploymentPlan,
        ):
            raise TypeError(
                "plan contains an invalid model"
            )

        names = (
            plan.suppressed_module_names
        )

        if not names:
            return ()

        bp_relative = PurePosixPath(
            "proprietary/Android.bp"
        )

        vendor_relative = PurePosixPath(
            vendor_makefile_name
        )

        bp_path = (
            staged_device_root
            / Path(
                bp_relative.as_posix()
            )
        )

        vendor_path = (
            staged_device_root
            / vendor_makefile_name
        )

        if not bp_path.is_file():
            raise ValueError(
                "staged proprietary Android.bp "
                f"is missing: {bp_path}"
            )

        if not vendor_path.is_file():
            raise ValueError(
                "staged vendor makefile "
                f"is missing: {vendor_path}"
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
                module_replacements=tuple(
                    (
                        item.module_name,
                        item.provider_module_name,
                    )
                    for item in plan.suppressions
                ),
            )
        )

        if transformed_bp == original_bp:
            raise ValueError(
                "non-empty ELF deployment plan "
                "did not change proprietary/Android.bp"
            )

        bp_path.write_text(
            transformed_bp,
            encoding="utf-8",
        )

        changed = [
            bp_relative,
        ]

        if transformed_vendor != original_vendor:
            vendor_path.write_text(
                transformed_vendor,
                encoding="utf-8",
            )

            changed.append(
                vendor_relative
            )

        return tuple(changed)
