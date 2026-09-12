from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re

from treeforge.android.device_tree.apex_payload_projection import (
    AndroidDeviceTreeApexPayloadProjection,
)
from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
)
from treeforge.android.version.device_tree.provider_profile import (
    AndroidDeviceTreePlatformProviderProfile,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeApexDeploymentSuppression:
    """
    One canonical TreeForge APEX build representation suppressed only in the
    deployed AOSP build view because the selected TreeForge platform profile proves one exact installable
    APEX provider for the same installed APEX identity.
    """

    representation_id: str
    module_name: str
    apex_name: str
    installed_android_path: str

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
                "apex_name",
                self.apex_name,
            ),
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
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

    def to_dict(self) -> dict[str, str]:
        return {
            "representation_id": self.representation_id,
            "module_name": self.module_name,
            "apex_name": self.apex_name,
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
    ) -> "AndroidDeviceTreeApexDeploymentSuppression":
        if not isinstance(value, dict):
            raise TypeError(
                "APEX deployment suppression must be an object"
            )

        return cls(
            representation_id=str(
                value["representation_id"]
            ),
            module_name=str(
                value["module_name"]
            ),
            apex_name=str(
                value["apex_name"]
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
class AndroidDeviceTreeApexDeploymentPlan:
    """
    Exact platform-provider APEX suppression plan for one AOSP deployment.

    This plan is downstream of canonical Device Tree generation. It never
    changes factory-derived projections, realizations, payloads, or canonical
    output/device-tree content.
    """

    device_root: PurePosixPath

    suppressions: tuple[
        AndroidDeviceTreeApexDeploymentSuppression,
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
                AndroidDeviceTreeApexDeploymentSuppression,
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
                    item.module_name,
                    item.representation_id,
                ),
            )
        )

        if self.suppressions != expected:
            raise ValueError(
                "APEX deployment suppressions must be "
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
                "suppressed APEX module names must be unique"
            )

        representation_ids = tuple(
            item.representation_id
            for item in self.suppressions
        )

        if len(representation_ids) != len(
            set(representation_ids)
        ):
            raise ValueError(
                "suppressed APEX representation IDs must be unique"
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
    ) -> "AndroidDeviceTreeApexDeploymentPlan":
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
                "APEX deployment plan must be an object"
            )

        if value.get(
            "schema_version"
        ) != cls.SCHEMA_VERSION:
            raise ValueError(
                "unsupported APEX deployment plan schema"
            )

        raw_suppressions = value.get(
            "suppressions"
        )

        if not isinstance(
            raw_suppressions,
            list,
        ):
            raise ValueError(
                "APEX deployment plan suppressions "
                "must be a list"
            )

        plan = cls(
            device_root=PurePosixPath(
                str(value["device_root"])
            ),
            suppressions=tuple(
                sorted(
                    (
                        AndroidDeviceTreeApexDeploymentSuppression
                        .from_dict(item)
                        for item
                        in raw_suppressions
                    ),
                    key=lambda item: (
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
                "APEX deployment suppression count mismatch"
            )

        return plan


class AndroidDeviceTreeApexDeploymentPlanner:
    """
    Build the Device Tree APEX suppression plan from TreeForge-owned target
    platform-provider semantics.

    No Android source checkout or build output participates in this decision.
    """

    @classmethod
    def plan(
        cls,
        *,
        provider_profile: AndroidDeviceTreePlatformProviderProfile,
        device_root: PurePosixPath,
        projections: tuple[
            AndroidDeviceTreeApexPayloadProjection,
            ...,
        ],
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> AndroidDeviceTreeApexDeploymentPlan:
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
            not isinstance(projections, tuple)
            or not all(
                isinstance(
                    item,
                    AndroidDeviceTreeApexPayloadProjection,
                )
                for item in projections
            )
        ):
            raise TypeError(
                "projections contains an invalid APEX projection"
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
                "realizations contains an invalid build realization"
            )

        #
        # APEX provider ownership is keyed by the canonical activated
        # package identity, not by the provider's installed filename/path.
        #
        # A checkout provider and a TreeForge prebuilt may legitimately use
        # different filenames while still representing the same APEX
        # manifest identity.  In that case the checkout provider owns the
        # canonical APEX identity and the TreeForge prebuilt is suppressed.
        #
        providers: dict[
            str,
            str,
        ] = {}

        for (
            apex_name,
            _installed_android_path,
            provider_module_name,
        ) in provider_profile.apex_providers:
            existing = providers.get(
                apex_name
            )

            if (
                existing is not None
                and existing != provider_module_name
            ):
                raise ValueError(
                    "APEX provider profile contains ambiguous "
                    "providers for canonical APEX identity "
                    f"{apex_name!r}: "
                    f"{existing!r}, "
                    f"{provider_module_name!r}"
                )

            providers[
                apex_name
            ] = provider_module_name

        realization_by_id = {
            item.representation_id: item
            for item in realizations
        }

        if len(realization_by_id) != len(realizations):
            raise ValueError(
                "Device Tree build realization IDs are not unique"
            )

        suppressions = []

        for projection in projections:
            provider_module_name = providers.get(
                projection.requirement.apex_name
            )

            if provider_module_name is None:
                continue

            realization = realization_by_id.get(
                projection.representation_id
            )

            if realization is None:
                raise ValueError(
                    "platform-provided APEX has no Device Tree "
                    "build realization: "
                    f"{projection.representation_id}"
                )

            if realization.kind.value != "apex_module":
                raise ValueError(
                    "platform-provided APEX maps to a non-APEX "
                    "Device Tree realization: "
                    f"{projection.representation_id}"
                )

            if realization.status.value != "resolved":
                raise ValueError(
                    "platform-provided APEX maps to an unresolved "
                    "Device Tree realization: "
                    f"{projection.representation_id}"
                )

            if not realization.module_name:
                raise ValueError(
                    "platform-provided APEX realization has no "
                    "TreeForge module name"
                )

            suppressions.append(
                AndroidDeviceTreeApexDeploymentSuppression(
                    representation_id=(
                        projection.representation_id
                    ),
                    module_name=realization.module_name,
                    apex_name=(
                        projection.requirement.apex_name
                    ),
                    installed_android_path=(
                        projection.installed_android_path
                    ),
                    provider_module_name=(
                        provider_module_name
                    ),
                    provider_profile_id=(
                        provider_profile.profile_id
                    ),
                )
            )

        return AndroidDeviceTreeApexDeploymentPlan(
            device_root=device_root,
            suppressions=tuple(
                sorted(
                    suppressions,
                    key=lambda item: (
                        item.module_name,
                        item.representation_id,
                    ),
                )
            ),
        )



class AndroidDeviceTreeApexDeploymentTransformer:
    """
    Apply the exact APEX suppression plan to a staged AOSP deployment copy.

    Only TreeForge-controlled generated build declarations are altered:
      * proprietary/Android.bp prebuilt_apex blocks
      * <device>-vendor.mk PRODUCT_PACKAGES entries

    Factory APEX payload files remain present and unchanged.
    """

    _APEX_BLOCK_RE = re.compile(
        r"(?ms)^prebuilt_apex \{\n.*?^\}\n(?:\n)?"
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

        transformed = (
            cls._APEX_BLOCK_RE.sub(
                replace,
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
                "APEX deployment Android.bp suppression "
                f"coverage mismatch: {bad}"
            )

        return transformed

    @staticmethod
    def transform_vendor_makefile(
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

        output = []

        for line in text.splitlines(
            keepends=True
        ):
            token = line.strip()

            if token.endswith("\\"):
                token = token[:-1].rstrip()

            if token in targets:
                counts[token] += 1
                continue

            output.append(line)

        # PRODUCT_PACKAGES participation is selected before staged
        # provider deployment. A suppressed APEX may therefore already be
        # absent here. More than one occurrence remains invalid.
        bad = {
            name: count
            for name, count
            in counts.items()
            if count > 1
        }

        if bad:
            raise ValueError(
                "APEX deployment PRODUCT_PACKAGES "
                f"duplicate suppression coverage: {bad}"
            )

        return "".join(output)

    @classmethod
    def apply(
        cls,
        *,
        staged_device_root: Path,
        plan: AndroidDeviceTreeApexDeploymentPlan,
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
            AndroidDeviceTreeApexDeploymentPlan,
        ):
            raise TypeError(
                "plan contains an invalid model"
            )

        if (
            not isinstance(
                vendor_makefile_name,
                str,
            )
            or not vendor_makefile_name
        ):
            raise ValueError(
                "vendor_makefile_name must be non-empty"
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
            / Path(bp_relative.as_posix())
        )

        vendor_path = (
            staged_device_root
            / vendor_makefile_name
        )

        if not bp_path.is_file():
            raise ValueError(
                "staged proprietary Android.bp is missing: "
                f"{bp_path}"
            )

        if not vendor_path.is_file():
            raise ValueError(
                "staged vendor makefile is missing: "
                f"{vendor_path}"
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
                "non-empty APEX deployment plan did not "
                "change proprietary/Android.bp"
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

    @staticmethod
    def _allowed_extra_deployed_file(
        relative: PurePosixPath,
    ) -> bool:
        return (
            len(relative.parts) >= 3
            and relative.parts[0] == "keys"
            and relative.parts[1] == "avb"
            and relative.suffix == ".pem"
        )

    @classmethod
    def compare_deployed_tree(
        cls,
        *,
        generated_device_root: Path,
        deployed_device_root: Path,
        plan: AndroidDeviceTreeApexDeploymentPlan,
        vendor_makefile_name: str,
    ) -> tuple[
        bool,
        tuple[str, ...],
    ]:
        """
        Verify exact deployment identity.

        Every canonical generated file must remain byte-identical except the
        two build files transformed according to the recorded APEX plan.

        Extra deployed files are rejected except external keys/avb/*.pem,
        matching Device Tree's existing downstream AVB-key preservation rule.
        """

        for field_name, path in (
            (
                "generated_device_root",
                generated_device_root,
            ),
            (
                "deployed_device_root",
                deployed_device_root,
            ),
        ):
            if not isinstance(path, Path):
                raise TypeError(
                    f"{field_name} must be a Path"
                )

            if not path.is_dir():
                return (
                    False,
                    (
                        f"{field_name} is missing: {path}",
                    ),
                )

        generated_files = {
            PurePosixPath(
                path.relative_to(
                    generated_device_root
                ).as_posix()
            ): path
            for path
            in generated_device_root.rglob("*")
            if path.is_file()
        }

        deployed_files = {
            PurePosixPath(
                path.relative_to(
                    deployed_device_root
                ).as_posix()
            ): path
            for path
            in deployed_device_root.rglob("*")
            if path.is_file()
        }

        names = (
            plan.suppressed_module_names
        )

        bp_relative = PurePosixPath(
            "proprietary/Android.bp"
        )

        vendor_relative = PurePosixPath(
            vendor_makefile_name
        )

        failures = []

        for relative, generated_path in sorted(
            generated_files.items(),
            key=lambda item: item[0].as_posix(),
        ):
            deployed_path = (
                deployed_files.get(
                    relative
                )
            )

            if deployed_path is None:
                failures.append(
                    "missing deployed file: "
                    f"{relative.as_posix()}"
                )
                continue

            if relative == bp_relative:
                expected = (
                    cls.transform_android_bp(
                        generated_path.read_text(
                            encoding="utf-8"
                        ),
                        suppressed_module_names=names,
                    )
                    .encode("utf-8")
                )

            elif relative == vendor_relative:
                expected = (
                    cls.transform_vendor_makefile(
                        generated_path.read_text(
                            encoding="utf-8"
                        ),
                        suppressed_module_names=names,
                    )
                    .encode("utf-8")
                )

            else:
                expected = (
                    generated_path.read_bytes()
                )

            actual = (
                deployed_path.read_bytes()
            )

            if actual != expected:
                failures.append(
                    "deployed content differs from expected "
                    "deployment view: "
                    f"{relative.as_posix()}"
                )

        for relative in sorted(
            set(deployed_files)
            - set(generated_files),
            key=lambda item: item.as_posix(),
        ):
            if cls._allowed_extra_deployed_file(
                relative
            ):
                continue

            failures.append(
                "unexpected deployed file: "
                f"{relative.as_posix()}"
            )

        if failures:
            return (
                False,
                tuple(failures),
            )

        details = [
            (
                "recorded AOSP APEX suppressions: "
                f"{len(plan.suppressions)}"
            ),
        ]

        details.extend(
            (
                "suppressed: "
                f"{item.module_name} "
                f"({item.apex_name}) -> "
                f"{item.provider_module_name} "
                f"[{item.provider_profile_id}]"
            )
            for item
            in plan.suppressions
        )

        return (
            True,
            tuple(details),
        )
