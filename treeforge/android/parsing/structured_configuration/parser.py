from __future__ import annotations

import json
import re

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)

from treeforge.android.parsing.structured_configuration.model import (
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


_MODULE_START_RE = re.compile(
    r"(?m)^[ \t]*"
    r"(?P<module_type>[A-Za-z_][A-Za-z0-9_]*)"
    r"[ \t]*\{"
)


class AndroidStructuredConfigurationParser:
    """
    Parse literal structured filesystem configuration discovered by the
    canonical AndroidModelSourceInventory.

    This parser performs intrinsic decoding only.
    """

    def parse(
        self,
        inventory: AndroidModelSourceInventory,
    ) -> AndroidStructuredConfigurationParsingResult:
        if not isinstance(
            inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidModelSourceInventory"
            )

        return AndroidStructuredConfigurationParsingResult(
            avb_public_keys=self._parse_group(
                inventory,
                AndroidModelSourceKind.AVB_PUBLIC_KEY,
                self._parse_avb_public_key,
            ),
            cgroup_configurations=self._parse_group(
                inventory,
                AndroidModelSourceKind.CGROUP_CONFIGURATION,
                self._parse_cgroups,
            ),
            mke2fs_configurations=self._parse_group(
                inventory,
                AndroidModelSourceKind.MKE2FS_CONFIGURATION,
                self._parse_mke2fs,
            ),
            recovery_wipe_configurations=self._parse_group(
                inventory,
                AndroidModelSourceKind.RECOVERY_WIPE_CONFIGURATION,
                self._parse_recovery_wipe,
            ),
            blueprints=self._parse_group(
                inventory,
                AndroidModelSourceKind.BLUEPRINT,
                self._parse_blueprint,
            ),
            sensor_hal_configurations=self._parse_group(
                inventory,
                AndroidModelSourceKind.SENSOR_HAL_CONFIGURATION,
                self._parse_sensor_hal_configuration,
            ),
            sensor_registry_configurations=self._parse_group(
                inventory,
                AndroidModelSourceKind.SENSOR_REGISTRY_CONFIGURATION,
                self._parse_sensor_registry_configuration,
            ),
        )

    @staticmethod
    def _parse_group(
        inventory,
        kind,
        parser,
    ):
        return tuple(
            parser(source)
            for source in inventory.sources_for(kind)
        )

    @staticmethod
    def _parse_avb_public_key(
        source: AndroidModelSource,
    ) -> ParsedAndroidAvbPublicKey:
        data = source.host_path.read_bytes()

        if len(data) < 8:
            raise ValueError(
                "AVB public key is shorter than its header"
            )

        key_num_bits = int.from_bytes(
            data[0:4],
            "big",
        )
        n0inv = int.from_bytes(
            data[4:8],
            "big",
        )

        if (
            key_num_bits <= 0
            or key_num_bits % 8 != 0
        ):
            raise ValueError(
                "invalid AVB public-key bit count"
            )

        component_size = (
            key_num_bits // 8
        )

        expected_size = (
            8
            + component_size
            + component_size
        )

        if len(data) != expected_size:
            raise ValueError(
                "standalone AVB public-key size "
                "does not match declared key size"
            )

        return ParsedAndroidAvbPublicKey(
            source=source,
            key_num_bits=key_num_bits,
            n0inv=n0inv,
            modulus=data[
                8:8 + component_size
            ],
            rr=data[
                8 + component_size:
            ],
        )

    @classmethod
    def _parse_cgroups(
        cls,
        source: AndroidModelSource,
    ) -> ParsedAndroidCgroupConfiguration:
        value = json.loads(
            source.host_path.read_text(
                encoding="utf-8"
            )
        )

        scalars = []

        cls._flatten_json(
            value=value,
            path=(),
            result=scalars,
        )

        return ParsedAndroidCgroupConfiguration(
            source=source,
            scalars=tuple(
                sorted(
                    scalars,
                    key=lambda item: item.path,
                )
            ),
        )

    @classmethod
    def _flatten_json(
        cls,
        *,
        value,
        path: tuple[str, ...],
        result: list[
            AndroidStructuredScalar
        ],
    ) -> None:
        if isinstance(value, dict):
            for key in sorted(value):
                cls._flatten_json(
                    value=value[key],
                    path=(*path, str(key)),
                    result=result,
                )
            return

        if isinstance(value, list):
            for index, child in enumerate(value):
                cls._flatten_json(
                    value=child,
                    path=(*path, str(index)),
                    result=result,
                )
            return

        if isinstance(value, bool):
            kind = (
                AndroidStructuredScalarKind.BOOLEAN
            )

        elif isinstance(value, int):
            kind = (
                AndroidStructuredScalarKind.INTEGER
            )

        elif isinstance(value, str):
            kind = (
                AndroidStructuredScalarKind.STRING
            )

        elif value is None:
            kind = (
                AndroidStructuredScalarKind.NULL
            )

        else:
            raise ValueError(
                "unsupported JSON scalar type "
                f"{type(value).__name__}"
            )

        result.append(
            AndroidStructuredScalar(
                path=".".join(path),
                kind=kind,
                value=value,
            )
        )

    @staticmethod
    def _parse_mke2fs(
        source: AndroidModelSource,
    ) -> ParsedAndroidMke2fsConfiguration:
        text = source.host_path.read_text(
            encoding="utf-8"
        )

        section = ""
        scope: list[str] = []
        pending_scope: str | None = None
        entries = []

        for source_line, raw in enumerate(
            text.splitlines(),
            start=1,
        ):
            content = raw.strip()

            if (
                not content
                or content.startswith("#")
            ):
                continue

            if (
                content.startswith("[")
                and content.endswith("]")
            ):
                section = content[1:-1].strip()
                scope = []
                pending_scope = None
                continue

            if content == "}":
                if scope:
                    scope.pop()
                pending_scope = None
                continue

            if content.endswith("= {"):
                name = (
                    content[:-3]
                    .strip()
                )

                if name:
                    scope.append(name)

                pending_scope = None
                continue

            if "=" not in content:
                continue

            key, value = (
                part.strip()
                for part in content.split(
                    "=",
                    1,
                )
            )

            if value == "{":
                if key:
                    scope.append(key)
                continue

            entries.append(
                AndroidMke2fsConfigurationEntry(
                    section=section,
                    scope=tuple(scope),
                    key=key,
                    value=value,
                    source_line=source_line,
                )
            )

        return ParsedAndroidMke2fsConfiguration(
            source=source,
            entries=tuple(entries),
        )

    @staticmethod
    def _parse_recovery_wipe(
        source: AndroidModelSource,
    ) -> ParsedAndroidRecoveryWipeConfiguration:
        entries = []

        for source_line, raw in enumerate(
            source.host_path.read_text(
                encoding="utf-8"
            ).splitlines(),
            start=1,
        ):
            content = raw.strip()

            if (
                not content
                or content.startswith("#")
            ):
                continue

            entries.append(
                AndroidRecoveryWipeEntry(
                    path=content,
                    source_line=source_line,
                )
            )

        return ParsedAndroidRecoveryWipeConfiguration(
            source=source,
            entries=tuple(entries),
        )


    @staticmethod
    def _parse_sensor_hal_configuration(
        source: AndroidModelSource,
    ) -> ParsedAndroidSensorHalConfiguration:
        entries = []

        for source_line, raw in enumerate(
            source.host_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines(),
            start=1,
        ):
            content = raw.split("#", 1)[0].strip()

            if not content:
                continue

            entries.append(
                AndroidSensorHalEntry(
                    module=content,
                    source_line=source_line,
                )
            )

        return ParsedAndroidSensorHalConfiguration(
            source=source,
            entries=tuple(entries),
        )

    @staticmethod
    def _parse_sensor_registry_configuration(
        source: AndroidModelSource,
    ) -> ParsedAndroidSensorRegistryConfiguration:
        records = []
        current_scope = None

        for source_line, raw in enumerate(
            source.host_path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines(),
            start=1,
        ):
            content = raw.strip()

            if (
                not content
                or content.startswith("#")
            ):
                continue

            # Registry node declarations observed in Android factory images
            # use a one-character operation immediately followed by an
            # absolute registry path (for example "+/dev/..."). Preserve
            # the operation literally rather than assigning meaning here.
            if (
                len(content) >= 2
                and content[1] == "/"
            ):
                current_scope = content[1:]

                records.append(
                    AndroidSensorRegistryRecord(
                        kind=(
                            AndroidSensorRegistryRecordKind.NODE
                        ),
                        raw=content,
                        source_line=source_line,
                        node_operator=content[0],
                        node_path=current_scope,
                    )
                )
                continue

            if "=" in content:
                key, value = content.split(
                    "=",
                    1,
                )

                key = key.strip()
                value = value.strip()

                if key:
                    records.append(
                        AndroidSensorRegistryRecord(
                            kind=(
                                AndroidSensorRegistryRecordKind
                                .PROPERTY
                            ),
                            raw=content,
                            source_line=source_line,
                            scope_path=current_scope,
                            key=key,
                            value=value,
                        )
                    )
                    continue

            # Unknown meaningful syntax is canonical evidence too. Retain it
            # instead of silently filtering it.
            records.append(
                AndroidSensorRegistryRecord(
                    kind=(
                        AndroidSensorRegistryRecordKind.LITERAL
                    ),
                    raw=content,
                    source_line=source_line,
                )
            )

        return ParsedAndroidSensorRegistryConfiguration(
            source=source,
            records=tuple(records),
        )

    @classmethod
    def _parse_blueprint(
        cls,
        source: AndroidModelSource,
    ) -> ParsedAndroidBlueprint:
        text = source.host_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        modules = []

        for match in _MODULE_START_RE.finditer(text):
            open_brace = match.end() - 1

            close_brace = cls._matching_brace(
                text,
                open_brace,
            )

            if close_brace is None:
                continue

            body_start = open_brace + 1
            body = text[
                body_start:close_brace
            ]

            properties = (
                cls._literal_properties(
                    body=body,
                    body_start=body_start,
                    full_text=text,
                )
            )

            names = tuple(
                prop.value
                for prop in properties
                if (
                    prop.name == "name"
                    and prop.kind
                    is AndroidBlueprintPropertyKind.STRING
                )
            )

            name = (
                names[0]
                if len(names) == 1
                else None
            )

            modules.append(
                AndroidBlueprintModule(
                    module_type=match.group(
                        "module_type"
                    ),
                    name=name,
                    source_line=(
                        text.count(
                            "\n",
                            0,
                            match.start(),
                        )
                        + 1
                    ),
                    properties=properties,
                )
            )

        return ParsedAndroidBlueprint(
            source=source,
            modules=tuple(modules),
        )

    @classmethod
    def _literal_properties(
        cls,
        *,
        body: str,
        body_start: int,
        full_text: str,
    ) -> tuple[
        AndroidBlueprintProperty,
        ...,
    ]:
        result = []
        index = 0

        while index < len(body):
            index = cls._skip_space_comments(
                body,
                index,
            )

            if index >= len(body):
                break

            start = index

            if not (
                body[index].isalpha()
                or body[index] == "_"
            ):
                index += 1
                continue

            index += 1

            while (
                index < len(body)
                and (
                    body[index].isalnum()
                    or body[index] == "_"
                )
            ):
                index += 1

            name = body[start:index]

            cursor = cls._skip_space_comments(
                body,
                index,
            )

            if (
                cursor >= len(body)
                or body[cursor] != ":"
            ):
                index = cursor
                continue

            cursor = cls._skip_space_comments(
                body,
                cursor + 1,
            )

            parsed = cls._literal_value(
                body,
                cursor,
            )

            if parsed is None:
                index = cls._skip_expression(
                    body,
                    cursor,
                )
                continue

            kind, value, end = parsed

            result.append(
                AndroidBlueprintProperty(
                    name=name,
                    kind=kind,
                    value=value,
                    source_line=(
                        full_text.count(
                            "\n",
                            0,
                            body_start + start,
                        )
                        + 1
                    ),
                )
            )

            index = cls._skip_expression(
                body,
                end,
            )

        return tuple(
            sorted(
                result,
                key=lambda prop: (
                    prop.source_line,
                    prop.name,
                ),
            )
        )

    @classmethod
    def _literal_value(
        cls,
        text: str,
        start: int,
    ):
        if start >= len(text):
            return None

        if text.startswith(
            "true",
            start,
        ):
            return (
                AndroidBlueprintPropertyKind.BOOLEAN,
                True,
                start + 4,
            )

        if text.startswith(
            "false",
            start,
        ):
            return (
                AndroidBlueprintPropertyKind.BOOLEAN,
                False,
                start + 5,
            )

        if text[start] == '"':
            parsed = cls._string(
                text,
                start,
            )

            if parsed is None:
                return None

            value, end = parsed

            return (
                AndroidBlueprintPropertyKind.STRING,
                value,
                end,
            )

        if text[start] != "[":
            return None

        values = []
        index = start + 1

        while True:
            index = cls._skip_space_comments(
                text,
                index,
            )

            if index >= len(text):
                return None

            if text[index] == "]":
                return (
                    AndroidBlueprintPropertyKind.STRING_LIST,
                    tuple(values),
                    index + 1,
                )

            if text[index] != '"':
                return None

            parsed = cls._string(
                text,
                index,
            )

            if parsed is None:
                return None

            value, index = parsed
            values.append(value)

            index = cls._skip_space_comments(
                text,
                index,
            )

            if (
                index < len(text)
                and text[index] == ","
            ):
                index += 1

    @staticmethod
    def _string(
        text: str,
        start: int,
    ):
        if (
            start >= len(text)
            or text[start] != '"'
        ):
            return None

        result = []
        index = start + 1

        while index < len(text):
            char = text[index]

            if char == '"':
                return (
                    "".join(result),
                    index + 1,
                )

            if char == "\\":
                index += 1

                if index >= len(text):
                    return None

                escaped = text[index]

                result.append(
                    {
                        "n": "\n",
                        "r": "\r",
                        "t": "\t",
                    }.get(
                        escaped,
                        escaped,
                    )
                )

                index += 1
                continue

            result.append(char)
            index += 1

        return None

    @staticmethod
    def _skip_space_comments(
        text: str,
        index: int,
    ) -> int:
        while index < len(text):
            if text[index].isspace():
                index += 1
                continue

            if text.startswith(
                "//",
                index,
            ):
                newline = text.find(
                    "\n",
                    index + 2,
                )

                if newline < 0:
                    return len(text)

                index = newline + 1
                continue

            if text.startswith(
                "/*",
                index,
            ):
                end = text.find(
                    "*/",
                    index + 2,
                )

                if end < 0:
                    return len(text)

                index = end + 2
                continue

            break

        return index

    @classmethod
    def _matching_brace(
        cls,
        text: str,
        open_brace: int,
    ) -> int | None:
        depth = 0
        index = open_brace

        while index < len(text):
            if text[index] == '"':
                parsed = cls._string(
                    text,
                    index,
                )

                if parsed is None:
                    return None

                _, index = parsed
                continue

            if text.startswith(
                "//",
                index,
            ):
                newline = text.find(
                    "\n",
                    index + 2,
                )

                if newline < 0:
                    return None

                index = newline + 1
                continue

            if text.startswith(
                "/*",
                index,
            ):
                end = text.find(
                    "*/",
                    index + 2,
                )

                if end < 0:
                    return None

                index = end + 2
                continue

            if text[index] == "{":
                depth += 1

            elif text[index] == "}":
                depth -= 1

                if depth == 0:
                    return index

            index += 1

        return None

    @classmethod
    def _skip_expression(
        cls,
        text: str,
        start: int,
    ) -> int:
        index = start
        square = 0
        curly = 0
        paren = 0

        while index < len(text):
            if text[index] == '"':
                parsed = cls._string(
                    text,
                    index,
                )

                if parsed is None:
                    return len(text)

                _, index = parsed
                continue

            if text.startswith("//", index):
                newline = text.find(
                    "\n",
                    index + 2,
                )

                if newline < 0:
                    return len(text)

                index = newline + 1
                continue

            if text[index] == "[":
                square += 1
            elif text[index] == "]":
                square = max(0, square - 1)
            elif text[index] == "{":
                curly += 1
            elif text[index] == "}":
                if curly == 0:
                    return index
                curly -= 1
            elif text[index] == "(":
                paren += 1
            elif text[index] == ")":
                paren = max(0, paren - 1)
            elif (
                text[index] == ","
                and square == 0
                and curly == 0
                and paren == 0
            ):
                return index + 1

            index += 1

        return index
