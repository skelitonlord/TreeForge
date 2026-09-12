from __future__ import annotations

import base64
from typing import Any

from treeforge.android.persistence.decoder import (
    SnapshotGraphDecoder,
)
from treeforge.android.persistence.encoder import (
    SnapshotGraphEncoder,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
)
from treeforge.android.parsing.structured_configuration import (
    AndroidBlueprintModule,
    AndroidBlueprintProperty,
    AndroidBlueprintPropertyKind,
    AndroidMke2fsConfigurationEntry,
    AndroidRecoveryWipeEntry,
    AndroidSensorHalEntry,
    AndroidSensorRegistryRecord,
    AndroidSensorRegistryRecordKind,
    AndroidStructuredConfigurationParsingResult,
    AndroidStructuredScalar,
    AndroidStructuredScalarKind,
    ParsedAndroidAvbPublicKey,
    ParsedAndroidBlueprint,
    ParsedAndroidCgroupConfiguration,
    ParsedAndroidMke2fsConfiguration,
    ParsedAndroidRecoveryWipeConfiguration,
    ParsedAndroidSensorHalConfiguration,
    ParsedAndroidSensorRegistryConfiguration,
)


def _encode_bytes(
    value: bytes,
) -> str:
    if not isinstance(
        value,
        bytes,
    ):
        raise TypeError(
            "value must be bytes"
        )

    return base64.b64encode(
        value
    ).decode(
        "ascii"
    )


def _decode_bytes(
    value: object,
    *,
    field_name: str,
) -> bytes:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string"
        )

    try:
        return base64.b64decode(
            value.encode("ascii"),
            validate=True,
        )
    except Exception as error:
        raise ValueError(
            f"{field_name} is not valid base64"
        ) from error


def _decode_source(
    payload: dict[str, Any],
    decoder: SnapshotGraphDecoder,
) -> AndroidModelSource:
    source = decoder.ref(
        payload["source"]
    )

    if not isinstance(
        source,
        AndroidModelSource,
    ):
        raise TypeError(
            "restored structured configuration source "
            "must be an AndroidModelSource"
        )

    return source


class ParsedAndroidAvbPublicKeyCodec:
    type_tag = (
        "android.structured_configuration."
        "avb_public_key"
    )
    python_type = ParsedAndroidAvbPublicKey

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidAvbPublicKey,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidAvbPublicKey"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "key_num_bits": (
                value.key_num_bits
            ),
            "n0inv": value.n0inv,
            "modulus": _encode_bytes(
                value.modulus
            ),
            "rr": _encode_bytes(
                value.rr
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return ParsedAndroidAvbPublicKey(
            source=_decode_source(
                payload,
                decoder,
            ),
            key_num_bits=payload[
                "key_num_bits"
            ],
            n0inv=payload["n0inv"],
            modulus=_decode_bytes(
                payload["modulus"],
                field_name="modulus",
            ),
            rr=_decode_bytes(
                payload["rr"],
                field_name="rr",
            ),
        )


class AndroidStructuredScalarCodec:
    type_tag = (
        "android.structured_configuration."
        "scalar"
    )
    python_type = AndroidStructuredScalar

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidStructuredScalar,
        ):
            raise TypeError(
                "value must be an "
                "AndroidStructuredScalar"
            )

        return {
            "path": value.path,
            "kind": value.kind.value,
            "value": value.value,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidStructuredScalar(
            path=payload["path"],
            kind=(
                AndroidStructuredScalarKind(
                    payload["kind"]
                )
            ),
            value=payload["value"],
        )


class ParsedAndroidCgroupConfigurationCodec:
    type_tag = (
        "android.structured_configuration."
        "cgroup"
    )
    python_type = (
        ParsedAndroidCgroupConfiguration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidCgroupConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidCgroupConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "scalars": [
                encoder.ref(item)
                for item in value.scalars
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        scalars = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "scalars",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidStructuredScalar,
            )
            for value in scalars
        ):
            raise TypeError(
                "restored cgroup configuration "
                "contains invalid scalars"
            )

        return ParsedAndroidCgroupConfiguration(
            source=_decode_source(
                payload,
                decoder,
            ),
            scalars=scalars,
        )


class AndroidMke2fsConfigurationEntryCodec:
    type_tag = (
        "android.structured_configuration."
        "mke2fs_entry"
    )
    python_type = (
        AndroidMke2fsConfigurationEntry
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidMke2fsConfigurationEntry,
        ):
            raise TypeError(
                "value must be an "
                "AndroidMke2fsConfigurationEntry"
            )

        return {
            "section": value.section,
            "scope": list(
                value.scope
            ),
            "key": value.key,
            "value": value.value,
            "source_line": (
                value.source_line
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        scope = payload.get(
            "scope",
            [],
        )

        if (
            not isinstance(scope, list)
            or not all(
                isinstance(value, str)
                for value in scope
            )
        ):
            raise TypeError(
                "restored mke2fs scope "
                "must be list[str]"
            )

        return AndroidMke2fsConfigurationEntry(
            section=payload["section"],
            scope=tuple(scope),
            key=payload["key"],
            value=payload["value"],
            source_line=payload[
                "source_line"
            ],
        )


class ParsedAndroidMke2fsConfigurationCodec:
    type_tag = (
        "android.structured_configuration."
        "mke2fs"
    )
    python_type = (
        ParsedAndroidMke2fsConfiguration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidMke2fsConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidMke2fsConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "entries": [
                encoder.ref(item)
                for item in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        entries = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "entries",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidMke2fsConfigurationEntry,
            )
            for value in entries
        ):
            raise TypeError(
                "restored mke2fs configuration "
                "contains invalid entries"
            )

        return ParsedAndroidMke2fsConfiguration(
            source=_decode_source(
                payload,
                decoder,
            ),
            entries=entries,
        )


class AndroidRecoveryWipeEntryCodec:
    type_tag = (
        "android.structured_configuration."
        "recovery_wipe_entry"
    )
    python_type = AndroidRecoveryWipeEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidRecoveryWipeEntry,
        ):
            raise TypeError(
                "value must be an "
                "AndroidRecoveryWipeEntry"
            )

        return {
            "path": value.path,
            "source_line": (
                value.source_line
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidRecoveryWipeEntry(
            path=payload["path"],
            source_line=payload[
                "source_line"
            ],
        )


class ParsedAndroidRecoveryWipeConfigurationCodec:
    type_tag = (
        "android.structured_configuration."
        "recovery_wipe"
    )
    python_type = (
        ParsedAndroidRecoveryWipeConfiguration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidRecoveryWipeConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidRecoveryWipeConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "entries": [
                encoder.ref(item)
                for item in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        entries = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "entries",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidRecoveryWipeEntry,
            )
            for value in entries
        ):
            raise TypeError(
                "restored recovery wipe "
                "configuration contains "
                "invalid entries"
            )

        return (
            ParsedAndroidRecoveryWipeConfiguration(
                source=_decode_source(
                    payload,
                    decoder,
                ),
                entries=entries,
            )
        )


class AndroidBlueprintPropertyCodec:
    type_tag = (
        "android.structured_configuration."
        "blueprint_property"
    )
    python_type = AndroidBlueprintProperty

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidBlueprintProperty,
        ):
            raise TypeError(
                "value must be an "
                "AndroidBlueprintProperty"
            )

        raw_value = value.value

        if isinstance(
            raw_value,
            tuple,
        ):
            raw_value = list(
                raw_value
            )

        return {
            "name": value.name,
            "kind": value.kind.value,
            "value": raw_value,
            "source_line": (
                value.source_line
            ),
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        kind = AndroidBlueprintPropertyKind(
            payload["kind"]
        )

        value = payload["value"]

        if (
            kind
            is AndroidBlueprintPropertyKind
            .STRING_LIST
        ):
            if (
                not isinstance(value, list)
                or not all(
                    isinstance(item, str)
                    for item in value
                )
            ):
                raise TypeError(
                    "restored Blueprint "
                    "STRING_LIST value must "
                    "be list[str]"
                )

            value = tuple(value)

        return AndroidBlueprintProperty(
            name=payload["name"],
            kind=kind,
            value=value,
            source_line=payload[
                "source_line"
            ],
        )


class AndroidBlueprintModuleCodec:
    type_tag = (
        "android.structured_configuration."
        "blueprint_module"
    )
    python_type = AndroidBlueprintModule

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidBlueprintModule,
        ):
            raise TypeError(
                "value must be an "
                "AndroidBlueprintModule"
            )

        return {
            "module_type": (
                value.module_type
            ),
            "name": value.name,
            "source_line": (
                value.source_line
            ),
            "properties": [
                encoder.ref(item)
                for item
                in value.properties
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        properties = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "properties",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidBlueprintProperty,
            )
            for value in properties
        ):
            raise TypeError(
                "restored Blueprint module "
                "contains invalid properties"
            )

        return AndroidBlueprintModule(
            module_type=payload[
                "module_type"
            ],
            name=payload.get(
                "name"
            ),
            source_line=payload[
                "source_line"
            ],
            properties=properties,
        )


class ParsedAndroidBlueprintCodec:
    type_tag = (
        "android.structured_configuration."
        "blueprint"
    )
    python_type = ParsedAndroidBlueprint

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidBlueprint,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidBlueprint"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "modules": [
                encoder.ref(item)
                for item
                in value.modules
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        modules = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "modules",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidBlueprintModule,
            )
            for value in modules
        ):
            raise TypeError(
                "restored Blueprint contains "
                "invalid modules"
            )

        return ParsedAndroidBlueprint(
            source=_decode_source(
                payload,
                decoder,
            ),
            modules=modules,
        )



class AndroidSensorHalEntryCodec:
    type_tag = (
        "android.structured_configuration."
        "sensor_hal_entry"
    )
    python_type = AndroidSensorHalEntry

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidSensorHalEntry,
        ):
            raise TypeError(
                "value must be an "
                "AndroidSensorHalEntry"
            )

        return {
            "module": value.module,
            "source_line": value.source_line,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidSensorHalEntry(
            module=payload["module"],
            source_line=payload[
                "source_line"
            ],
        )


class ParsedAndroidSensorHalConfigurationCodec:
    type_tag = (
        "android.structured_configuration."
        "sensor_hal"
    )
    python_type = (
        ParsedAndroidSensorHalConfiguration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidSensorHalConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidSensorHalConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "entries": [
                encoder.ref(item)
                for item in value.entries
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        entries = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "entries",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidSensorHalEntry,
            )
            for value in entries
        ):
            raise TypeError(
                "restored sensor HAL configuration "
                "contains invalid entries"
            )

        return ParsedAndroidSensorHalConfiguration(
            source=_decode_source(
                payload,
                decoder,
            ),
            entries=entries,
        )


class AndroidSensorRegistryRecordCodec:
    type_tag = (
        "android.structured_configuration."
        "sensor_registry_record"
    )
    python_type = AndroidSensorRegistryRecord

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidSensorRegistryRecord,
        ):
            raise TypeError(
                "value must be an "
                "AndroidSensorRegistryRecord"
            )

        return {
            "kind": value.kind.value,
            "raw": value.raw,
            "source_line": value.source_line,
            "node_operator": (
                value.node_operator
            ),
            "node_path": value.node_path,
            "scope_path": value.scope_path,
            "key": value.key,
            "value": value.value,
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        return AndroidSensorRegistryRecord(
            kind=(
                AndroidSensorRegistryRecordKind(
                    payload["kind"]
                )
            ),
            raw=payload["raw"],
            source_line=payload[
                "source_line"
            ],
            node_operator=payload.get(
                "node_operator"
            ),
            node_path=payload.get(
                "node_path"
            ),
            scope_path=payload.get(
                "scope_path"
            ),
            key=payload.get(
                "key"
            ),
            value=payload.get(
                "value"
            ),
        )


class ParsedAndroidSensorRegistryConfigurationCodec:
    type_tag = (
        "android.structured_configuration."
        "sensor_registry"
    )
    python_type = (
        ParsedAndroidSensorRegistryConfiguration
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            ParsedAndroidSensorRegistryConfiguration,
        ):
            raise TypeError(
                "value must be a "
                "ParsedAndroidSensorRegistryConfiguration"
            )

        return {
            "source": encoder.ref(
                value.source
            ),
            "records": [
                encoder.ref(item)
                for item in value.records
            ],
        }

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        records = tuple(
            decoder.ref(ref)
            for ref
            in payload.get(
                "records",
                [],
            )
        )

        if not all(
            isinstance(
                value,
                AndroidSensorRegistryRecord,
            )
            for value in records
        ):
            raise TypeError(
                "restored sensor registry configuration "
                "contains invalid records"
            )

        return (
            ParsedAndroidSensorRegistryConfiguration(
                source=_decode_source(
                    payload,
                    decoder,
                ),
                records=records,
            )
        )


class AndroidStructuredConfigurationParsingResultCodec:
    type_tag = (
        "android.structured_configuration."
        "result"
    )
    python_type = (
        AndroidStructuredConfigurationParsingResult
    )

    def encode(
        self,
        value: object,
        encoder: SnapshotGraphEncoder,
    ) -> dict[str, Any]:
        if not isinstance(
            value,
            AndroidStructuredConfigurationParsingResult,
        ):
            raise TypeError(
                "value must be an "
                "AndroidStructuredConfigurationParsingResult"
            )

        return {
            "avb_public_keys": [
                encoder.ref(item)
                for item
                in value.avb_public_keys
            ],
            "cgroup_configurations": [
                encoder.ref(item)
                for item
                in value.cgroup_configurations
            ],
            "mke2fs_configurations": [
                encoder.ref(item)
                for item
                in value.mke2fs_configurations
            ],
            "recovery_wipe_configurations": [
                encoder.ref(item)
                for item
                in value.recovery_wipe_configurations
            ],
            "blueprints": [
                encoder.ref(item)
                for item
                in value.blueprints
            ],
            "sensor_hal_configurations": [
                encoder.ref(item)
                for item
                in value.sensor_hal_configurations
            ],
            "sensor_registry_configurations": [
                encoder.ref(item)
                for item
                in value.sensor_registry_configurations
            ],
        }

    @staticmethod
    def _refs(
        payload: dict[str, Any],
        name: str,
        decoder: SnapshotGraphDecoder,
    ) -> tuple[object, ...]:
        refs = payload.get(
            name,
            [],
        )

        if not isinstance(
            refs,
            list,
        ):
            raise TypeError(
                f"{name} must be a list"
            )

        return tuple(
            decoder.ref(ref)
            for ref in refs
        )

    def decode(
        self,
        payload: dict[str, Any],
        decoder: SnapshotGraphDecoder,
    ) -> object:
        avb_public_keys = self._refs(
            payload,
            "avb_public_keys",
            decoder,
        )
        cgroup_configurations = self._refs(
            payload,
            "cgroup_configurations",
            decoder,
        )
        mke2fs_configurations = self._refs(
            payload,
            "mke2fs_configurations",
            decoder,
        )
        recovery_wipe_configurations = (
            self._refs(
                payload,
                "recovery_wipe_configurations",
                decoder,
            )
        )
        blueprints = self._refs(
            payload,
            "blueprints",
            decoder,
        )
        sensor_hal_configurations = self._refs(
            payload,
            "sensor_hal_configurations",
            decoder,
        )
        sensor_registry_configurations = self._refs(
            payload,
            "sensor_registry_configurations",
            decoder,
        )

        checks = (
            (
                avb_public_keys,
                ParsedAndroidAvbPublicKey,
                "avb_public_keys",
            ),
            (
                cgroup_configurations,
                ParsedAndroidCgroupConfiguration,
                "cgroup_configurations",
            ),
            (
                mke2fs_configurations,
                ParsedAndroidMke2fsConfiguration,
                "mke2fs_configurations",
            ),
            (
                recovery_wipe_configurations,
                ParsedAndroidRecoveryWipeConfiguration,
                "recovery_wipe_configurations",
            ),
            (
                blueprints,
                ParsedAndroidBlueprint,
                "blueprints",
            ),
            (
                sensor_hal_configurations,
                ParsedAndroidSensorHalConfiguration,
                "sensor_hal_configurations",
            ),
            (
                sensor_registry_configurations,
                ParsedAndroidSensorRegistryConfiguration,
                "sensor_registry_configurations",
            ),
        )

        for values, expected_type, name in checks:
            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value in values
            ):
                raise TypeError(
                    "restored structured "
                    f"configuration {name} "
                    "contains invalid values"
                )

        return (
            AndroidStructuredConfigurationParsingResult(
                avb_public_keys=(
                    avb_public_keys
                ),
                cgroup_configurations=(
                    cgroup_configurations
                ),
                mke2fs_configurations=(
                    mke2fs_configurations
                ),
                recovery_wipe_configurations=(
                    recovery_wipe_configurations
                ),
                blueprints=blueprints,
                sensor_hal_configurations=(
                    sensor_hal_configurations
                ),
                sensor_registry_configurations=(
                    sensor_registry_configurations
                ),
            )
        )


STRUCTURED_CONFIGURATION_CODECS = (
    ParsedAndroidAvbPublicKeyCodec(),
    AndroidStructuredScalarCodec(),
    ParsedAndroidCgroupConfigurationCodec(),
    AndroidMke2fsConfigurationEntryCodec(),
    ParsedAndroidMke2fsConfigurationCodec(),
    AndroidRecoveryWipeEntryCodec(),
    ParsedAndroidRecoveryWipeConfigurationCodec(),
    AndroidBlueprintPropertyCodec(),
    AndroidBlueprintModuleCodec(),
    ParsedAndroidBlueprintCodec(),
    AndroidSensorHalEntryCodec(),
    ParsedAndroidSensorHalConfigurationCodec(),
    AndroidSensorRegistryRecordCodec(),
    ParsedAndroidSensorRegistryConfigurationCodec(),
    AndroidStructuredConfigurationParsingResultCodec(),
)
