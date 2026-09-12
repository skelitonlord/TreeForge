from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.device_tree.product_policy import (
    AndroidDeviceTreeProductPolicySelector,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeArchitectureBoardConfig:
    """
    Concrete Android BoardConfig architecture policy derived exclusively
    from canonical Android Device Universe conclusions.
    """

    primary_architecture: str
    primary_arch_variant: str
    primary_cpu_variant: str
    primary_cpu_variant_runtime: str
    primary_cpu_abis: tuple[str, ...]

    secondary_architecture: str | None
    secondary_arch_variant: str | None
    secondary_cpu_variant: str | None
    secondary_cpu_variant_runtime: str | None
    secondary_cpu_abis: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("primary_architecture", self.primary_architecture),
            ("primary_arch_variant", self.primary_arch_variant),
            ("primary_cpu_variant", self.primary_cpu_variant),
            (
                "primary_cpu_variant_runtime",
                self.primary_cpu_variant_runtime,
            ),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if (
            not isinstance(self.primary_cpu_abis, tuple)
            or not self.primary_cpu_abis
            or not all(
                isinstance(value, str) and value
                for value in self.primary_cpu_abis
            )
        ):
            raise ValueError(
                "primary_cpu_abis must contain canonical ABI strings"
            )

        secondary_values = (
            (
                "secondary_architecture",
                self.secondary_architecture,
            ),
            (
                "secondary_arch_variant",
                self.secondary_arch_variant,
            ),
            (
                "secondary_cpu_variant",
                self.secondary_cpu_variant,
            ),
            (
                "secondary_cpu_variant_runtime",
                self.secondary_cpu_variant_runtime,
            ),
        )

        for field_name, value in secondary_values:
            if value is None:
                continue

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string or None"
                )

        if not isinstance(
            self.secondary_cpu_abis,
            tuple,
        ):
            raise TypeError(
                "secondary_cpu_abis must be a tuple"
            )

        if not all(
            isinstance(value, str)
            and value
            for value
            in self.secondary_cpu_abis
        ):
            raise ValueError(
                "secondary_cpu_abis must contain canonical ABI strings"
            )

        secondary_details_present = any(
            value is not None
            for value in (
                self.secondary_arch_variant,
                self.secondary_cpu_variant,
                self.secondary_cpu_variant_runtime,
            )
        ) or bool(
            self.secondary_cpu_abis
        )

        if (
            secondary_details_present
            and self.secondary_architecture is None
        ):
            raise ValueError(
                "secondary architecture details require "
                "secondary_architecture"
            )


class AndroidDeviceTreeArchitectureBoardConfigRenderer:
    """
    Map canonical Universe architecture conclusions to Android BoardConfig
    TARGET_* syntax.

    No architecture or ABI values are inferred from device names, platform
    names, source-tree layout, or hardcoded device knowledge.
    """

    @classmethod
    def project(
        cls,
        *,
        universe: AndroidDeviceUniverse,
    ) -> AndroidDeviceTreeArchitectureBoardConfig:
        if not isinstance(universe, AndroidDeviceUniverse):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        fact = AndroidDeviceTreeProductPolicySelector._agreed_fact

        def optional_architecture_fact(
            fact_name: str,
        ) -> str | None:
            if universe.architecture is None:
                return None

            conclusion = (
                universe.architecture.conclusion(
                    fact_name
                )
            )

            if conclusion is None:
                return None

            if conclusion.status.value != "agreed":
                return None

            value = conclusion.value

            if value is None:
                return None

            if not isinstance(value, str):
                raise TypeError(
                    "agreed optional architecture fact must "
                    f"be a string: {fact_name}"
                )

            if not value.strip():
                raise ValueError(
                    "agreed optional architecture fact must "
                    f"not be empty: {fact_name}"
                )

            return value

        primary_architecture = fact(
            universe,
            "primary_architecture",
        )
        primary_arch_variant = fact(
            universe,
            "primary_arch_variant",
        )
        primary_cpu_variant = fact(
            universe,
            "primary_cpu_variant",
        )
        primary_cpu_variant_runtime = fact(
            universe,
            "primary_cpu_variant_runtime",
        )

        primary_cpu_abis = (
            fact(
                universe,
                "primary_cpu_abi",
            ),
        )

        secondary_architecture = optional_architecture_fact(
            "secondary_architecture",
        )
        secondary_arch_variant = optional_architecture_fact(
            "secondary_arch_variant",
        )
        secondary_cpu_variant = optional_architecture_fact(
            "secondary_cpu_variant",
        )
        secondary_cpu_variant_runtime = optional_architecture_fact(
            "secondary_cpu_variant_runtime",
        )

        secondary_cpu_abis = tuple(
            value
            for value in (
                optional_architecture_fact(
                    "secondary_cpu_abi",
                ),
                optional_architecture_fact(
                    "secondary_cpu_abi2",
                ),
            )
            if value is not None
        )

        return AndroidDeviceTreeArchitectureBoardConfig(
            primary_architecture=primary_architecture,
            primary_arch_variant=primary_arch_variant,
            primary_cpu_variant=primary_cpu_variant,
            primary_cpu_variant_runtime=(
                primary_cpu_variant_runtime
            ),
            primary_cpu_abis=primary_cpu_abis,
            secondary_architecture=secondary_architecture,
            secondary_arch_variant=secondary_arch_variant,
            secondary_cpu_variant=secondary_cpu_variant,
            secondary_cpu_variant_runtime=(
                secondary_cpu_variant_runtime
            ),
            secondary_cpu_abis=secondary_cpu_abis,
        )

    @staticmethod
    def render(
        config: AndroidDeviceTreeArchitectureBoardConfig,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreeArchitectureBoardConfig,
        ):
            raise TypeError(
                "config must be an "
                "AndroidDeviceTreeArchitectureBoardConfig"
            )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Canonical Android target architecture.",
            "",
            f"TARGET_ARCH := {config.primary_architecture}",
            (
                "TARGET_ARCH_VARIANT := "
                f"{config.primary_arch_variant}"
            ),
            (
                "TARGET_CPU_VARIANT := "
                f"{config.primary_cpu_variant}"
            ),
            (
                "TARGET_CPU_VARIANT_RUNTIME := "
                f"{config.primary_cpu_variant_runtime}"
            ),
            f"TARGET_CPU_ABI := {config.primary_cpu_abis[0]}",
        ]

        if len(config.primary_cpu_abis) > 1:
            lines.append(
                f"TARGET_CPU_ABI2 := {config.primary_cpu_abis[1]}"
            )

        if config.secondary_architecture is not None:
            lines.extend(
                [
                    "",
                    (
                        "TARGET_2ND_ARCH := "
                        f"{config.secondary_architecture}"
                    ),
                ]
            )

            if config.secondary_arch_variant is not None:
                lines.append(
                    "TARGET_2ND_ARCH_VARIANT := "
                    f"{config.secondary_arch_variant}"
                )

            if config.secondary_cpu_variant is not None:
                lines.append(
                    "TARGET_2ND_CPU_VARIANT := "
                    f"{config.secondary_cpu_variant}"
                )

            if (
                config.secondary_cpu_variant_runtime
                is not None
            ):
                lines.append(
                    "TARGET_2ND_CPU_VARIANT_RUNTIME := "
                    f"{config.secondary_cpu_variant_runtime}"
                )

            if config.secondary_cpu_abis:
                lines.append(
                    "TARGET_2ND_CPU_ABI := "
                    f"{config.secondary_cpu_abis[0]}"
                )

            if len(config.secondary_cpu_abis) > 1:
                lines.append(
                    "TARGET_2ND_CPU_ABI2 := "
                    f"{config.secondary_cpu_abis[1]}"
                )

        lines.append("")

        return "\n".join(lines)
