from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.properties.scope import (
    AndroidPropertyScope,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidPropertyFact:
    """
    One direct semantic fact established by an Android property declaration.

    This model describes only what the property itself directly states. It does
    not perform canonical reconciliation, build-property reconstruction,
    Android-version policy, device policy, or provenance modeling.

    Provenance remains owned by the observation/evidence layer that consumes
    this semantic interpretation.
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
    # Values remain exact comma-separated property values. An explicitly
    # empty list is semantically meaningful and must not be discarded.
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
    "ro.build.ab_update": "ab_update",
    "ro.boot.dynamic_partitions": "dynamic_partitions",
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


def interpret_android_property_fact(
    key: str,
    value: str,
) -> AndroidPropertyFact | None:
    """
    Interpret one Android property declaration as a directly observable fact.

    Explicit Android property namespace scope is retained independently from
    the artifact or partition from which the declaration was observed.

    Unknown properties remain uninterpreted rather than being guessed.

    This function is intentionally independent of Android version, device,
    partition, SoC, OEM, build reconstruction, and canonical reconciliation.
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
        return AndroidPropertyFact(
            property_key=normalized_key,
            fact=direct_fact,
            value=value,
        )

    parts = normalized_key.split(
        "."
    )

    # ro.product.<scope>.<identity-field>
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
                return AndroidPropertyFact(
                    property_key=normalized_key,
                    fact=fact,
                    value=value,
                    scope=scope,
                )

    # ro.<scope>.build.<build-field>
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
                return AndroidPropertyFact(
                    property_key=normalized_key,
                    fact=fact,
                    value=value,
                    scope=scope,
                )

    return None

