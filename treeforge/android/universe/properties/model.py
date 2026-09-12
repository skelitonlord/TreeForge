from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.properties.scope import (
    AndroidPropertyScope,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniversePropertyFact:
    """
    One semantic fact directly stated by an Android property declaration.

    This is interpretation, not reconciliation. It describes only what the
    declaration itself states.

    Source provenance is attached by the Universe evidence layer.
    """

    property_key: str
    fact: str
    value: str
    scope: AndroidPropertyScope | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.property_key,
            str,
        ):
            raise TypeError(
                "property_key must be a string"
            )

        if not self.property_key.strip():
            raise ValueError(
                "property_key must not be empty"
            )

        if not isinstance(
            self.fact,
            str,
        ):
            raise TypeError(
                "fact must be a string"
            )

        if not self.fact.strip():
            raise ValueError(
                "fact must not be empty"
            )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if (
            self.scope is not None
            and not isinstance(
                self.scope,
                AndroidPropertyScope,
            )
        ):
            raise TypeError(
                "scope must be an "
                "AndroidPropertyScope or None"
            )


_PRODUCT_IDENTITY_FACTS = {
    "brand": "product_brand",
    "device": "device_codename",
    "manufacturer": "manufacturer",
    "model": "product_model",
    "name": "product_name",
}


_SCOPED_BUILD_FACTS = {
    "date.utc": "build_date_utc",
    "fingerprint": "build_fingerprint",
    "id": "build_id",
    "tags": "build_tags",
    "type": "build_type",
    "version.incremental": "build_incremental",
    "version.release": "android_version",
    "version.sdk": "sdk_level",
}


_DIRECT_FACTS = {
    "ro.build.version.release": "android_version",
    "ro.build.version.sdk": "sdk_level",
    "ro.build.version.security_patch": "security_patch_level",
    "ro.build.version.incremental": "build_incremental",
    "ro.build.version.codename": "build_codename",
    "ro.build.version.preview_sdk": "preview_sdk_level",
    "ro.build.version.min_supported_target_sdk": (
        "min_supported_target_sdk"
    ),
    "ro.build.id": "build_id",
    "ro.build.fingerprint": "build_fingerprint",
    "ro.build.type": "build_type",
    "ro.build.tags": "build_tags",
    "ro.build.date.utc": "build_date_utc",
    "ro.build.product": "build_product",
    "ro.build.description": "build_description",
    "ro.build.characteristics": "build_characteristics",
    "ro.product.device": "device_codename",
    "ro.product.manufacturer": "manufacturer",
    "ro.product.model": "product_model",
    "ro.product.name": "product_name",
    "ro.product.brand": "product_brand",
    "ro.product.board": "product_board",
    "ro.product.first_api_level": "first_api_level",
    "ro.product.cpu.abi": "primary_cpu_abi",

    # Android supported-application ABI lists.
    #
    # These are semantic list facts even though the current generic property
    # fact representation retains their exact comma-separated string value.
    # An empty value therefore means an explicitly empty ABI list, not missing
    # evidence.
    "ro.product.cpu.abilist": "supported_cpu_abis",
    "ro.product.cpu.abilist32": "supported_32_bit_cpu_abis",
    "ro.product.cpu.abilist64": "supported_64_bit_cpu_abis",
    "ro.vendor.product.cpu.abilist": "supported_cpu_abis",
    "ro.vendor.product.cpu.abilist32": "supported_32_bit_cpu_abis",
    "ro.vendor.product.cpu.abilist64": "supported_64_bit_cpu_abis",

    "ro.board.platform": "board_platform",
    "ro.board.api_level": "board_api_level",
    "ro.board.api_frozen": "board_api_frozen",
    "ro.bionic.arch": "primary_architecture",
    "ro.bionic.cpu_variant": "primary_cpu_variant",
    "ro.bionic.2nd_arch": "secondary_architecture",
    "ro.bionic.2nd_cpu_variant": "secondary_cpu_variant",
    "ro.soc.manufacturer": "soc_manufacturer",
    "ro.soc.model": "soc_model",
    "ro.sf.lcd_density": "screen_density",
    "ro.zygote": "zygote",
    "ro.treble.enabled": "treble_enabled",
    "ro.debuggable": "debuggable",

    # Android linkerconfig runtime inputs.
    #
    # These facts remain absent when the corresponding property declaration
    # is absent. An explicitly present empty value is therefore preserved as
    # a real conclusion and remains distinguishable from property absence.
    "ro.vndk.version": "vendor_vndk_version",
    "ro.product.vndk.version": "product_vndk_version",
    "ro.vndk.lite": "vndk_lite",
    "ro.build.ab_update": "ab_update",
    "ro.boot.dynamic_partitions": "dynamic_partitions",

    # Canonical Virtual A/B runtime contract.
    "ro.virtual_ab.enabled": "virtual_ab_enabled",
    "ro.virtual_ab.compression.enabled": "virtual_ab_compression_enabled",
    "ro.virtual_ab.userspace.snapshots.enabled": "virtual_ab_userspace_snapshots_enabled",
    "ro.virtual_ab.batch_writes": "virtual_ab_batch_writes",
    "ro.virtual_ab.io_uring.enabled": "virtual_ab_io_uring_enabled",
    "ro.virtual_ab.compression.xor.enabled": "virtual_ab_compression_xor_enabled",
    "ro.build.expect.bootloader": "expected_bootloader",
}


def _parse_property_scope(
    value: str,
) -> AndroidPropertyScope | None:
    try:
        return AndroidPropertyScope(
            value
        )
    except ValueError:
        return None


def interpret_android_universe_property(
    key: str,
    value: str,
) -> AndroidUniversePropertyFact | None:
    """
    Interpret one parsed property declaration for Device Universe.

    Unknown declarations remain available in Parsing and are not guessed.
    """

    if not isinstance(
        key,
        str,
    ):
        raise TypeError(
            "key must be a string"
        )

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            "value must be a string"
        )

    normalized_key = key.strip()

    if not normalized_key:
        raise ValueError(
            "key must not be empty"
        )

    direct_fact = _DIRECT_FACTS.get(
        normalized_key
    )

    if direct_fact is not None:
        return AndroidUniversePropertyFact(
            property_key=normalized_key,
            fact=direct_fact,
            value=value,
        )

    parts = normalized_key.split(
        "."
    )

    if (
        len(parts) == 4
        and parts[0] == "ro"
        and parts[1] == "product"
    ):
        scope = _parse_property_scope(
            parts[2]
        )

        if scope is not None:
            fact = _PRODUCT_IDENTITY_FACTS.get(
                parts[3]
            )

            if fact is not None:
                return AndroidUniversePropertyFact(
                    property_key=normalized_key,
                    fact=fact,
                    value=value,
                    scope=scope,
                )

    if (
        len(parts) >= 4
        and parts[0] == "ro"
        and parts[2] == "build"
    ):
        scope = _parse_property_scope(
            parts[1]
        )

        if scope is not None:
            build_field = ".".join(
                parts[3:]
            )

            fact = _SCOPED_BUILD_FACTS.get(
                build_field
            )

            if fact is not None:
                return AndroidUniversePropertyFact(
                    property_key=normalized_key,
                    fact=fact,
                    value=value,
                    scope=scope,
                )

    return None