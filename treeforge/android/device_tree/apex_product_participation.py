from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.device_tree.apex_android_bp import (
    AndroidDeviceTreeApexAndroidBpModule,
)


#
# Minimum-AOSP product participation is independent from canonical APEX
# reconstruction and from later platform-provider deployment suppression.
#
# Device-owned APEX partitions may participate automatically. Framework-side
# factory APEXes remain fully preserved in the canonical Device Tree but are
# not automatically selected into PRODUCT_PACKAGES.
#
_MINIMUM_AOSP_DEVICE_APEX_PARTITIONS = frozenset(
    {
        "vendor",
        "odm",
    }
)

_MINIMUM_AOSP_FRAMEWORK_APEX_PARTITIONS = frozenset(
    {
        "system",
        "system_ext",
        "product",
    }
)

_MINIMUM_AOSP_KNOWN_APEX_PARTITIONS = (
    _MINIMUM_AOSP_DEVICE_APEX_PARTITIONS
    | _MINIMUM_AOSP_FRAMEWORK_APEX_PARTITIONS
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeApexProductSuppression:
    """
    One canonical APEX module preserved in Device Tree output but omitted
    from PRODUCT_PACKAGES by minimum-AOSP product policy.

    This is product participation only. It does not mutate the canonical APEX
    payload/module realization and does not represent platform-provider
    deployment suppression.
    """

    representation_id: str
    module_name: str
    apex_name: str
    installed_partition: str

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
                "installed_partition",
                self.installed_partition,
            ),
        ):
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeApexProductParticipationPlan:
    """
    Minimum-AOSP PRODUCT_PACKAGES disposition for canonical APEX modules.

    Canonical APEX payloads and Android.bp modules remain unchanged.
    """

    product_packages: tuple[str, ...]
    suppressions: tuple[
        AndroidDeviceTreeApexProductSuppression,
        ...,
    ]

    def __post_init__(self) -> None:
        if self.product_packages != tuple(
            sorted(
                set(
                    self.product_packages
                )
            )
        ):
            raise ValueError(
                "APEX product packages must be unique and "
                "deterministically ordered"
            )

        suppression_ids = tuple(
            item.representation_id
            for item in self.suppressions
        )

        if len(suppression_ids) != len(
            set(
                suppression_ids
            )
        ):
            raise ValueError(
                "APEX product suppressions must preserve "
                "unique representation identity"
            )

        suppression_modules = tuple(
            item.module_name
            for item in self.suppressions
        )

        if len(suppression_modules) != len(
            set(
                suppression_modules
            )
        ):
            raise ValueError(
                "APEX product suppressions must preserve "
                "unique module identity"
            )

        expected_order = tuple(
            sorted(
                self.suppressions,
                key=lambda item: (
                    item.installed_partition,
                    item.module_name,
                    item.representation_id,
                ),
            )
        )

        if self.suppressions != expected_order:
            raise ValueError(
                "APEX product suppressions must be "
                "deterministically ordered"
            )


class AndroidDeviceTreeApexProductParticipationProjector:
    """
    Apply minimum-AOSP product participation to canonical APEX modules.

    Factory-derived canonical APEX ownership remains authoritative.

    Device-owned vendor/odm APEX modules participate automatically.
    Framework-side system/system_ext/product APEX modules remain preserved
    but do not participate automatically.

    Exact platform-provider overlap remains a separate staged-deployment
    concern.
    """

    @classmethod
    def project(
        cls,
        *,
        modules: tuple[
            AndroidDeviceTreeApexAndroidBpModule,
            ...,
        ],
    ) -> AndroidDeviceTreeApexProductParticipationPlan:
        if not isinstance(modules, tuple):
            raise TypeError(
                "modules must be a tuple"
            )

        if not all(
            isinstance(
                module,
                AndroidDeviceTreeApexAndroidBpModule,
            )
            for module in modules
        ):
            raise TypeError(
                "modules must contain only "
                "AndroidDeviceTreeApexAndroidBpModule"
            )

        seen_representation_ids = set()
        seen_module_names = set()

        product_packages = []
        suppressions = []

        for module in sorted(
            modules,
            key=lambda item: (
                item.installed_partition,
                item.module_name,
                item.representation_id,
            ),
        ):
            if (
                module.representation_id
                in seen_representation_ids
            ):
                raise ValueError(
                    "multiple APEX modules claim one "
                    "representation identity: "
                    f"{module.representation_id}"
                )

            if module.module_name in seen_module_names:
                raise ValueError(
                    "multiple APEX modules claim one "
                    "module identity: "
                    f"{module.module_name}"
                )

            seen_representation_ids.add(
                module.representation_id
            )
            seen_module_names.add(
                module.module_name
            )

            if (
                module.installed_partition
                not in _MINIMUM_AOSP_KNOWN_APEX_PARTITIONS
            ):
                raise ValueError(
                    "minimum-AOSP APEX product policy has no "
                    "partition disposition for "
                    f"{module.installed_partition!r}: "
                    f"{module.representation_id}"
                )

            if (
                module.installed_partition
                in _MINIMUM_AOSP_DEVICE_APEX_PARTITIONS
            ):
                product_packages.append(
                    module.module_name
                )
                continue

            suppressions.append(
                AndroidDeviceTreeApexProductSuppression(
                    representation_id=(
                        module.representation_id
                    ),
                    module_name=(
                        module.module_name
                    ),
                    apex_name=(
                        module.apex_name
                    ),
                    installed_partition=(
                        module.installed_partition
                    ),
                )
            )

        return AndroidDeviceTreeApexProductParticipationPlan(
            product_packages=tuple(
                sorted(
                    product_packages
                )
            ),
            suppressions=tuple(
                sorted(
                    suppressions,
                    key=lambda item: (
                        item.installed_partition,
                        item.module_name,
                        item.representation_id,
                    ),
                )
            ),
        )
