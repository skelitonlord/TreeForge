from __future__ import annotations

from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.apex_deployment import (
    AndroidDeviceTreeApexDeploymentPlan,
    AndroidDeviceTreeApexDeploymentTransformer,
)
from treeforge.android.device_tree.elf_deployment import (
    AndroidDeviceTreeElfDeploymentPlan,
    AndroidDeviceTreeElfDeploymentTransformer,
)
from treeforge.android.device_tree.vintf_deployment import (
    AndroidDeviceTreeVintfDeploymentPlan,
    AndroidDeviceTreeVintfDeploymentTransformer,
)
from treeforge.android.device_tree.platform_deployment import (
    AndroidDeviceTreePlatformDeploymentPlan,
    AndroidDeviceTreePlatformDeploymentTransformer,
)


class AndroidDeviceTreeDeploymentIdentityVerifier:
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
        apex_plan: AndroidDeviceTreeApexDeploymentPlan,
        elf_plan: AndroidDeviceTreeElfDeploymentPlan,
        vintf_plan: AndroidDeviceTreeVintfDeploymentPlan,
        platform_plan: AndroidDeviceTreePlatformDeploymentPlan,
        vendor_makefile_name: str,
    ) -> tuple[bool, tuple[str, ...]]:
        if len(
            {
                apex_plan.device_root,
                elf_plan.device_root,
                vintf_plan.device_root,
                platform_plan.device_root,
            }
        ) != 1:
            raise ValueError(
                "deployment reconciliation plans "
                "target different device roots"
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

        proprietary_bp = PurePosixPath(
            "proprietary/Android.bp"
        )

        vintf_bp = PurePosixPath(
            "vintf/Android.bp"
        )

        vendor_mk = PurePosixPath(
            vendor_makefile_name
        )

        failures = []

        for relative, generated_path in sorted(
            generated_files.items(),
            key=lambda item: item[0].as_posix(),
        ):
            deployed_path = deployed_files.get(
                relative
            )

            if deployed_path is None:
                failures.append(
                    "missing deployed file: "
                    f"{relative.as_posix()}"
                )
                continue

            if relative == proprietary_bp:
                expected_text = (
                    generated_path.read_text(
                        encoding="utf-8"
                    )
                )

                expected_text = (
                    AndroidDeviceTreeApexDeploymentTransformer
                    .transform_android_bp(
                        expected_text,
                        suppressed_module_names=(
                            apex_plan.suppressed_module_names
                        ),
                    )
                )

                expected_text = (
                    AndroidDeviceTreeElfDeploymentTransformer
                    .transform_android_bp(
                        expected_text,
                        suppressed_module_names=(
                            elf_plan.suppressed_module_names
                        ),
                    )
                )

                expected = expected_text.encode(
                    "utf-8"
                )

            elif relative == vintf_bp:
                expected_text = (
                    generated_path.read_text(
                        encoding="utf-8"
                    )
                )

                expected_text = (
                    AndroidDeviceTreeVintfDeploymentTransformer
                    .transform_android_bp(
                        expected_text,
                        suppressed_module_names=(
                            vintf_plan.suppressed_module_names
                        ),
                    )
                )

                expected = expected_text.encode(
                    "utf-8"
                )

            elif relative == vendor_mk:
                expected_text = (
                    generated_path.read_text(
                        encoding="utf-8"
                    )
                )

                expected_text = (
                    AndroidDeviceTreeApexDeploymentTransformer
                    .transform_vendor_makefile(
                        expected_text,
                        suppressed_module_names=(
                            apex_plan.suppressed_module_names
                        ),
                    )
                )

                expected_text = (
                    AndroidDeviceTreeElfDeploymentTransformer
                    .transform_vendor_makefile(
                        expected_text,
                        suppressed_module_names=(
                            elf_plan.suppressed_module_names
                        ),
                        module_replacements=tuple(
                            (
                                item.module_name,
                                item.provider_module_name,
                            )
                            for item in elf_plan.suppressions
                        ),
                    )
                )

                expected_text = (
                    AndroidDeviceTreeVintfDeploymentTransformer
                    .transform_vendor_makefile(
                        expected_text,
                        suppressed_module_names=(
                            vintf_plan.suppressed_module_names
                        ),
                    )
                )

                expected = expected_text.encode(
                    "utf-8"
                )

            else:
                expected = (
                    generated_path.read_bytes()
                )

            expected = (
                AndroidDeviceTreePlatformDeploymentTransformer
                .transform_expected_bytes(
                    relative=relative,
                    expected=expected,
                    plan=platform_plan,
                    vendor_makefile_name=(
                        vendor_makefile_name
                    ),
                )
            )

            if deployed_path.read_bytes() != expected:
                failures.append(
                    "deployed content differs from "
                    "recorded deployment view: "
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

        return (
            True,
            (
                "recorded platform-provider APEX suppressions: "
                f"{len(apex_plan.suppressions)}",
                "recorded platform-provider ELF suppressions: "
                f"{len(elf_plan.suppressions)}",
                "recorded platform-provider executable suppressions: "
                f"{elf_plan.executable_count}",
                "recorded platform-provider native-library suppressions: "
                f"{elf_plan.native_library_count}",
                "recorded platform-provider VINTF suppressions: "
                f"{len(vintf_plan.suppressions)}",
                "recorded platform-provider build suppressions: "
                f"{len(platform_plan.suppressions)}",
                "recorded platform-provider copy-file suppressions: "
                f"{platform_plan.copy_file_count}",
                "recorded platform-provider framework-res suppressions: "
                f"{platform_plan.framework_res_count}",
            ),
        )
