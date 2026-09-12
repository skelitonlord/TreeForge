from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.version.device_tree.vendor_ramdisk_packages import (
    AndroidDeviceTreeVendorRamdiskPackageProvider,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeVendorRamdiskPackage:
    """
    One Android module requested because its corresponding runtime payload was
    observed as an exact canonical vendor_boot ELF.
    """

    module_name: str
    observed_android_path: str
    requirement_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("module_name", self.module_name),
            (
                "observed_android_path",
                self.observed_android_path,
            ),
            (
                "requirement_id",
                self.requirement_id,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        if not self.observed_android_path.startswith(
            "/"
        ):
            raise ValueError(
                "observed_android_path must be absolute"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeVendorRamdiskPackagePlan:
    packages: tuple[
        AndroidDeviceTreeVendorRamdiskPackage,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.packages,
            tuple,
        ):
            raise TypeError(
                "packages must be a tuple"
            )

        expected = tuple(
            sorted(
                self.packages,
                key=lambda item: (
                    item.module_name,
                    item.observed_android_path,
                    item.requirement_id,
                ),
            )
        )

        if self.packages != expected:
            raise ValueError(
                "vendor-ramdisk packages must be "
                "deterministically sorted"
            )

        module_names = tuple(
            item.module_name
            for item
            in self.packages
        )

        observed_paths = tuple(
            item.observed_android_path
            for item
            in self.packages
        )

        if len(module_names) != len(
            set(module_names)
        ):
            raise ValueError(
                "vendor-ramdisk package module names must be unique"
            )

        if len(observed_paths) != len(
            set(observed_paths)
        ):
            raise ValueError(
                "vendor-ramdisk observed paths must be unique"
            )


class AndroidDeviceTreeVendorRamdiskPackageProjector:
    """
    Resolve Android vendor-ramdisk package participation from two independent
    inputs:

      1. canonical factory-derived Universe ELF evidence;
      2. versioned Android module-provider semantics.

    A versioned provider mapping alone can never cause a package request.
    The corresponding exact vendor_boot ELF must actually exist.
    """

    @staticmethod
    def project(
        *,
        universe: AndroidDeviceUniverse,
        providers: tuple[
            AndroidDeviceTreeVendorRamdiskPackageProvider,
            ...,
        ],
    ) -> AndroidDeviceTreeVendorRamdiskPackagePlan:
        if not isinstance(
            universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        if (
            not isinstance(
                providers,
                tuple,
            )
            or not all(
                isinstance(
                    provider,
                    AndroidDeviceTreeVendorRamdiskPackageProvider,
                )
                for provider
                in providers
            )
        ):
            raise TypeError(
                "providers must contain only "
                "AndroidDeviceTreeVendorRamdiskPackageProvider values"
            )

        packages = []

        for provider in providers:
            matches = tuple(
                requirement
                for requirement
                in universe.elf_requirements
                if (
                    requirement
                    .source
                    .source
                    .source_name
                    == "vendor_boot"
                    and (
                        requirement
                        .source
                        .source
                        .android_path
                        == provider.observed_android_path
                    )
                )
            )

            if len(matches) > 1:
                raise ValueError(
                    "canonical vendor_boot ELF identity is ambiguous: "
                    f"{provider.observed_android_path.as_posix()}"
                )

            if not matches:
                continue

            requirement = matches[0]

            packages.append(
                AndroidDeviceTreeVendorRamdiskPackage(
                    module_name=(
                        provider.module_name
                    ),
                    observed_android_path=(
                        provider
                        .observed_android_path
                        .as_posix()
                    ),
                    requirement_id=(
                        requirement.requirement_id
                    ),
                )
            )

        return AndroidDeviceTreeVendorRamdiskPackagePlan(
            packages=tuple(
                sorted(
                    packages,
                    key=lambda item: (
                        item.module_name,
                        item.observed_android_path,
                        item.requirement_id,
                    ),
                )
            )
        )


class AndroidDeviceTreeVendorRamdiskPackageRenderer:
    @staticmethod
    def render_product_config(
        plan: AndroidDeviceTreeVendorRamdiskPackagePlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeVendorRamdiskPackagePlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeVendorRamdiskPackagePlan"
            )

        if not plan.packages:
            return ""

        lines = [
            "# Android vendor-ramdisk runtime providers.",
            "#",
            "# Package participation is factory-evidence-driven;",
            "# module identity comes from versioned Android semantics.",
            "PRODUCT_PACKAGES += \\",
        ]

        for index, package in enumerate(
            plan.packages
        ):
            suffix = (
                " \\"
                if index
                < len(plan.packages) - 1
                else ""
            )

            lines.append(
                "    "
                f"{package.module_name}"
                f"{suffix}"
            )

        return "\n".join(
            lines
        ) + "\n"
