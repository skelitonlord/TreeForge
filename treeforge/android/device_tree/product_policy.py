from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.universe.capability import (
    AndroidUniverseDeviceCapability,
    AndroidUniverseDeviceCapabilityConclusion,
    AndroidUniverseDeviceCapabilityStatus,
)
from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)


class AndroidDeviceTreeAppAbiMode(
    StrEnum,
):
    """
    Concrete Android product app-ABI modes supported by Device Tree policy.
    """

    APP_64_BIT_ONLY = "64_bit_only"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeProductPolicy:
    """
    Concrete Android build-product policy derived from canonical Universe
    semantics.

    Universe remains the semantic owner of device facts and capabilities.
    Device Tree owns mapping those canonical semantics to Android build
    product inheritance.
    """

    universe: AndroidDeviceUniverse
    android_version: str
    app_abi_mode: AndroidDeviceTreeAppAbiMode

    base_product_makefiles: tuple[
        str,
        ...,
    ]

    product_brand: str
    product_model: str
    product_manufacturer: str

    cellular_capability: (
        AndroidUniverseDeviceCapabilityConclusion
    )

    virtual_ab_enabled: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        if (
            not isinstance(
                self.android_version,
                str,
            )
            or not self.android_version
        ):
            raise ValueError(
                "android_version must be a non-empty string"
            )

        if not isinstance(
            self.app_abi_mode,
            AndroidDeviceTreeAppAbiMode,
        ):
            raise TypeError(
                "app_abi_mode must be an "
                "AndroidDeviceTreeAppAbiMode"
            )

        if not isinstance(
            self.base_product_makefiles,
            tuple,
        ):
            raise TypeError(
                "base_product_makefiles must be a tuple"
            )

        if not all(
            isinstance(item, str)
            and item
            for item in self.base_product_makefiles
        ):
            raise ValueError(
                "base_product_makefiles must contain only "
                "non-empty strings"
            )

        if len(
            self.base_product_makefiles
        ) != len(
            set(
                self.base_product_makefiles
            )
        ):
            raise ValueError(
                "base_product_makefiles must be unique"
            )

        for field_name, value in (
            ("product_brand", self.product_brand),
            ("product_model", self.product_model),
            ("product_manufacturer", self.product_manufacturer),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.cellular_capability,
            AndroidUniverseDeviceCapabilityConclusion,
        ):
            raise TypeError(
                "cellular_capability must be an "
                "AndroidUniverseDeviceCapabilityConclusion"
            )

        if (
            self.cellular_capability.capability
            is not AndroidUniverseDeviceCapability.CELLULAR
        ):
            raise ValueError(
                "cellular_capability must describe the cellular "
                "device capability"
            )

        if not any(
            conclusion is self.cellular_capability
            for conclusion in self.universe.device_capabilities
        ):
            raise ValueError(
                "cellular_capability must preserve exact "
                "AndroidDeviceUniverse conclusion identity"
            )

        if not isinstance(
            self.virtual_ab_enabled,
            bool,
        ):
            raise TypeError(
                "virtual_ab_enabled must be a bool"
            )


class AndroidDeviceTreeProductPolicySelector:
    """
    Map canonical Universe semantics to Android-version-specific product
    policy.

    This selector deliberately does not derive hardware capability from
    packages, VINTF files, raw properties, build flags, or source-tree
    naming. Those conclusions must already exist canonically in Universe.
    """

    _ANDROID_15_NEUTRAL_HANDHELD_PRODUCTS = (
        "$(SRC_TARGET_DIR)/product/core_64_bit_only.mk",
        "$(SRC_TARGET_DIR)/product/handheld_system.mk",
        "$(SRC_TARGET_DIR)/product/handheld_system_ext.mk",
        "$(SRC_TARGET_DIR)/product/handheld_vendor.mk",
        "$(SRC_TARGET_DIR)/product/handheld_product.mk",
    )

    _ANDROID_15_TELEPHONY_PRODUCT = (
        "$(SRC_TARGET_DIR)/product/telephony.mk"
    )

    _ANDROID_15_VIRTUAL_AB_T_BASELINE_PRODUCT = (
        "$(SRC_TARGET_DIR)/product/virtual_ab_ota/"
        "android_t_baseline.mk"
    )

    @classmethod
    def select(
        cls,
        *,
        universe: AndroidDeviceUniverse,
    ) -> AndroidDeviceTreeProductPolicy:
        if not isinstance(
            universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        android_version = cls._agreed_fact(
            universe,
            "android_version",
        )

        if android_version != "15":
            raise ValueError(
                "Device Tree product policy currently supports "
                "Android 15 only: "
                f"android_version={android_version!r}"
            )

        primary_architecture = cls._agreed_fact(
            universe,
            "primary_architecture",
        )

        zygote = cls._agreed_fact(
            universe,
            "zygote",
        )

        supported_cpu_abis = cls._agreed_fact(
            universe,
            "supported_cpu_abis",
        )

        abi_values = cls._abi_values(
            supported_cpu_abis
        )

        if (
            primary_architecture != "arm64"
            or zygote != "zygote64"
            or abi_values != ("arm64-v8a",)
        ):
            raise ValueError(
                "Device Tree cannot yet select a supported "
                "Android 15 app-ABI product policy from canonical "
                "Universe facts: "
                f"primary_architecture={primary_architecture!r}, "
                f"zygote={zygote!r}, "
                f"supported_cpu_abis={supported_cpu_abis!r}"
            )

        product_brand = cls._agreed_fact(
            universe,
            "product_brand",
        )

        product_model = cls._agreed_fact(
            universe,
            "product_model",
        )

        product_manufacturer = cls._agreed_fact(
            universe,
            "manufacturer",
        )

        for fact_name, value in (
            ("product_brand", product_brand),
            ("product_model", product_model),
            ("manufacturer", product_manufacturer),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    "Device Tree cannot realize canonical Android "
                    f"product identity: {fact_name}={value!r}"
                )

        cellular = tuple(
            conclusion
            for conclusion in universe.device_capabilities
            if (
                conclusion.capability
                is AndroidUniverseDeviceCapability.CELLULAR
            )
        )

        if len(cellular) != 1:
            raise ValueError(
                "AndroidDeviceUniverse must contain exactly one "
                "cellular capability conclusion"
            )

        cellular_capability = cellular[0]

        virtual_ab_enabled = (
            cls._strict_boolean_fact(
                universe,
                "virtual_ab_enabled",
            )
        )

        if virtual_ab_enabled:
            #
            # android_t_baseline.mk represents a specific Android
            # Virtual A/B feature contract. Do not select it from the
            # ro.virtual_ab.enabled bit alone: prove that the remaining
            # canonical factory contract agrees with the baseline.
            #
            # A future device with a materially different Virtual A/B
            # contract must fail here and gain explicit generic support
            # rather than silently inheriting behavior from a previously supported device.
            #
            virtual_ab_contract_facts = (
                "virtual_ab_compression_enabled",
                "virtual_ab_userspace_snapshots_enabled",
                "virtual_ab_batch_writes",
                "virtual_ab_io_uring_enabled",
                "virtual_ab_compression_xor_enabled",
            )

            unsupported_virtual_ab = tuple(
                fact_name
                for fact_name
                in virtual_ab_contract_facts
                if not cls._strict_boolean_fact(
                    universe,
                    fact_name,
                )
            )

            if unsupported_virtual_ab:
                raise ValueError(
                    "Android 15 Device Tree does not yet "
                    "support the canonical Virtual A/B "
                    "feature contract: expected the "
                    "T-launch baseline facts to be true, "
                    f"but found false: "
                    f"{unsupported_virtual_ab!r}"
                )

        product_makefiles = list(
            cls._ANDROID_15_NEUTRAL_HANDHELD_PRODUCTS
        )

        if virtual_ab_enabled:
            product_makefiles.append(
                cls
                ._ANDROID_15_VIRTUAL_AB_T_BASELINE_PRODUCT
            )

        if (
            cellular_capability.status
            is AndroidUniverseDeviceCapabilityStatus.PRESENT
        ):
            product_makefiles.append(
                cls._ANDROID_15_TELEPHONY_PRODUCT
            )

        return AndroidDeviceTreeProductPolicy(
            universe=universe,
            android_version=android_version,
            app_abi_mode=(
                AndroidDeviceTreeAppAbiMode.APP_64_BIT_ONLY
            ),
            base_product_makefiles=tuple(
                product_makefiles
            ),
            product_brand=product_brand,
            product_model=product_model,
            product_manufacturer=product_manufacturer,
            cellular_capability=cellular_capability,
            virtual_ab_enabled=virtual_ab_enabled,
        )

    @staticmethod
    def _agreed_fact(
        universe: AndroidDeviceUniverse,
        fact_name: str,
    ) -> object:
        #
        # Architecture owns its reconciled architecture facts as a
        # dedicated canonical semantic surface. Do not merge those
        # conclusions with the general property-conclusion surface,
        # because the same source fact may legitimately be represented
        # in both while preserving different semantic responsibilities.
        #
        if universe.architecture is not None:
            architecture_conclusion = (
                universe.architecture.conclusion(
                    fact_name
                )
            )

            if architecture_conclusion is not None:
                if (
                    architecture_conclusion.status.value
                    != "agreed"
                ):
                    raise ValueError(
                        "Device Tree product policy requires an "
                        "agreed canonical architecture fact: "
                        f"{fact_name}"
                    )

                return architecture_conclusion.value

        matches = tuple(
            conclusion
            for conclusion in universe.conclusions
            if (
                conclusion.fact == fact_name
                and conclusion.status.value == "agreed"
            )
        )

        if len(matches) != 1:
            raise ValueError(
                "Device Tree product policy requires exactly one "
                "agreed canonical Universe fact: "
                f"{fact_name}"
            )

        return matches[0].value

    @classmethod
    def _strict_boolean_fact(
        cls,
        universe: AndroidDeviceUniverse,
        fact_name: str,
    ) -> bool:
        value = cls._agreed_fact(
            universe,
            fact_name,
        )

        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            normalized = value.strip().lower()

            if normalized == "true":
                return True

            if normalized == "false":
                return False

        raise ValueError(
            "Device Tree product policy requires "
            "a canonical boolean Universe fact: "
            f"{fact_name}={value!r}"
        )

    @staticmethod
    def _abi_values(
        value: object,
    ) -> tuple[str, ...]:
        if isinstance(
            value,
            str,
        ):
            return tuple(
                item.strip()
                for item in value.split(",")
                if item.strip()
            )

        if isinstance(
            value,
            tuple,
        ):
            if not all(
                isinstance(item, str)
                and item
                for item in value
            ):
                raise ValueError(
                    "supported_cpu_abis tuple contains "
                    "an invalid ABI value"
                )

            return value

        if isinstance(
            value,
            list,
        ):
            if not all(
                isinstance(item, str)
                and item
                for item in value
            ):
                raise ValueError(
                    "supported_cpu_abis list contains "
                    "an invalid ABI value"
                )

            return tuple(value)

        raise ValueError(
            "supported_cpu_abis has an unsupported canonical "
            f"value type: {type(value).__name__}"
        )
