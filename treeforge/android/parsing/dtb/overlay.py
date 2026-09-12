from __future__ import annotations

from treeforge.android.parsing.dtb.model import (
    ParsedDtboExternalFixup,
    ParsedDtboExternalFixupLocation,
    ParsedDtboFragmentTarget,
    ParsedDtboLocalFixup,
    ParsedDtboOverlayMetadata,
    ParsedDtboSymbol,
    ParsedFdt,
    ParsedFdtNode,
    ParsedFdtProperty,
)


class DtboOverlayParsingError(
    ValueError,
):
    """
    Raised when compiled-overlay metadata is structurally malformed.
    """


class AndroidDtboOverlayParser:
    """
    Decode literal compiled-device-tree-overlay metadata from ParsedFdt.

    Generic FDT parsing remains owned by AndroidFdtParser. This parser consumes
    that exact immutable ParsedFdt and recognizes only standard compiled-overlay
    structures such as __fixups__, __local_fixups__, __symbols__, and fragment
    target declarations.

    It does not apply the overlay or infer device semantics.
    """

    def parse(
        self,
        fdt: ParsedFdt,
    ) -> ParsedDtboOverlayMetadata:
        if not isinstance(
            fdt,
            ParsedFdt,
        ):
            raise TypeError(
                "fdt must be a ParsedFdt"
            )

        root_children = {
            child.name: child
            for child in fdt.root.children
        }

        external_fixups = (
            self._parse_external_fixups(
                root_children.get(
                    "__fixups__"
                )
            )
        )

        local_fixups = (
            self._parse_local_fixups(
                root_children.get(
                    "__local_fixups__"
                )
            )
        )

        symbols = (
            self._parse_symbols(
                root_children.get(
                    "__symbols__"
                )
            )
        )

        fragment_targets = (
            self._parse_fragment_targets(
                fdt.root
            )
        )

        return ParsedDtboOverlayMetadata(
            fdt=fdt,
            external_fixups=external_fixups,
            local_fixups=local_fixups,
            symbols=symbols,
            fragment_targets=fragment_targets,
        )

    def _parse_external_fixups(
        self,
        node: ParsedFdtNode | None,
    ) -> tuple[
        ParsedDtboExternalFixup,
        ...,
    ]:
        if node is None:
            return ()

        fixups = []

        for prop in node.properties:
            strings = self._decode_string_list(
                prop,
                context=(
                    "DTBO external fixup "
                    f"{prop.name!r}"
                ),
            )

            locations = tuple(
                self._parse_external_location(
                    value,
                    symbol=prop.name,
                )
                for value in strings
            )

            fixups.append(
                ParsedDtboExternalFixup(
                    source=prop,
                    symbol=prop.name,
                    locations=locations,
                )
            )

        return tuple(
            fixups
        )

    def _parse_external_location(
        self,
        value: str,
        *,
        symbol: str,
    ) -> ParsedDtboExternalFixupLocation:
        try:
            node_path, property_name, raw_offset = (
                value.rsplit(
                    ":",
                    2,
                )
            )
        except ValueError as error:
            raise DtboOverlayParsingError(
                "Malformed DTBO external fixup location "
                f"for symbol {symbol!r}: {value!r}"
            ) from error

        if not node_path.startswith("/"):
            raise DtboOverlayParsingError(
                "DTBO external fixup node path must be absolute: "
                f"{value!r}"
            )

        if not property_name:
            raise DtboOverlayParsingError(
                "DTBO external fixup property name cannot be empty"
            )

        try:
            byte_offset = int(
                raw_offset,
                0,
            )
        except ValueError as error:
            raise DtboOverlayParsingError(
                "DTBO external fixup byte offset is invalid: "
                f"{value!r}"
            ) from error

        return ParsedDtboExternalFixupLocation(
            node_path=node_path,
            property_name=property_name,
            byte_offset=byte_offset,
        )

    def _parse_local_fixups(
        self,
        node: ParsedFdtNode | None,
    ) -> tuple[
        ParsedDtboLocalFixup,
        ...,
    ]:
        if node is None:
            return ()

        results = []

        for child in node.children:
            self._walk_local_fixups(
                node=child,
                overlay_path=(
                    f"/{child.name}"
                ),
                results=results,
            )

        return tuple(
            results
        )

    def _walk_local_fixups(
        self,
        *,
        node: ParsedFdtNode,
        overlay_path: str,
        results: list[
            ParsedDtboLocalFixup
        ],
    ) -> None:
        for prop in node.properties:
            offsets = (
                self._decode_u32_cells(
                    prop,
                    context=(
                        "DTBO local fixup "
                        f"{overlay_path}:"
                        f"{prop.name}"
                    ),
                )
            )

            if not offsets:
                raise DtboOverlayParsingError(
                    "DTBO local fixup cannot have an empty offset list"
                )

            if any(
                offset % 4
                for offset in offsets
            ):
                raise DtboOverlayParsingError(
                    "DTBO local fixup offsets must be "
                    "4-byte aligned"
                )

            if len(
                set(
                    offsets
                )
            ) != len(
                offsets
            ):
                raise DtboOverlayParsingError(
                    "DTBO local fixup offsets contain duplicates"
                )

            results.append(
                ParsedDtboLocalFixup(
                    source=prop,
                    node_path=overlay_path,
                    property_name=prop.name,
                    byte_offsets=offsets,
                )
            )

        for child in node.children:
            self._walk_local_fixups(
                node=child,
                overlay_path=(
                    f"{overlay_path}/{child.name}"
                ),
                results=results,
            )

    def _parse_symbols(
        self,
        node: ParsedFdtNode | None,
    ) -> tuple[
        ParsedDtboSymbol,
        ...,
    ]:
        if node is None:
            return ()

        symbols = []

        for prop in node.properties:
            strings = self._decode_string_list(
                prop,
                context=(
                    "DTBO symbol "
                    f"{prop.name!r}"
                ),
            )

            if len(strings) != 1:
                raise DtboOverlayParsingError(
                    "DTBO symbol must contain exactly one path"
                )

            node_path = strings[0]

            if not node_path.startswith("/"):
                raise DtboOverlayParsingError(
                    "DTBO symbol path must be absolute"
                )

            symbols.append(
                ParsedDtboSymbol(
                    source=prop,
                    symbol=prop.name,
                    node_path=node_path,
                )
            )

        return tuple(
            symbols
        )

    def _parse_fragment_targets(
        self,
        root: ParsedFdtNode,
    ) -> tuple[
        ParsedDtboFragmentTarget,
        ...,
    ]:
        targets = []

        for fragment in root.children:
            if not fragment.name.startswith(
                "fragment@"
            ):
                continue

            target = self._property_named(
                fragment,
                "target",
            )
            target_path = self._property_named(
                fragment,
                "target-path",
            )

            if (
                target is not None
                and target_path is not None
            ):
                raise DtboOverlayParsingError(
                    "DTBO fragment declares both "
                    "target and target-path: "
                    f"{fragment.name}"
                )

            fragment_path = (
                f"/{fragment.name}"
            )

            if target is not None:
                cells = self._decode_u32_cells(
                    target,
                    context=(
                        f"{fragment_path}:target"
                    ),
                )

                if len(cells) != 1:
                    raise DtboOverlayParsingError(
                        "DTBO fragment target must contain "
                        "exactly one 32-bit cell"
                    )

                targets.append(
                    ParsedDtboFragmentTarget(
                        fragment=fragment,
                        fragment_path=fragment_path,
                        target_property=target,
                        target_phandle=cells[0],
                    )
                )

            elif target_path is not None:
                strings = self._decode_string_list(
                    target_path,
                    context=(
                        f"{fragment_path}:target-path"
                    ),
                )

                if len(strings) != 1:
                    raise DtboOverlayParsingError(
                        "DTBO fragment target-path must contain "
                        "exactly one path"
                    )

                targets.append(
                    ParsedDtboFragmentTarget(
                        fragment=fragment,
                        fragment_path=fragment_path,
                        target_property=target_path,
                        target_path=strings[0],
                    )
                )

        return tuple(
            targets
        )

    @staticmethod
    def _property_named(
        node: ParsedFdtNode,
        name: str,
    ) -> ParsedFdtProperty | None:
        matches = tuple(
            prop
            for prop in node.properties
            if prop.name == name
        )

        if len(matches) > 1:
            raise DtboOverlayParsingError(
                "DTBO node contains duplicate property "
                f"{name!r}"
            )

        return (
            matches[0]
            if matches
            else None
        )

    @staticmethod
    def _decode_u32_cells(
        prop: ParsedFdtProperty,
        *,
        context: str,
    ) -> tuple[
        int,
        ...,
    ]:
        value = prop.value

        if len(value) % 4:
            raise DtboOverlayParsingError(
                f"{context} is not an array of 32-bit cells"
            )

        return tuple(
            int.from_bytes(
                value[
                    offset:
                    offset + 4
                ],
                byteorder="big",
                signed=False,
            )
            for offset in range(
                0,
                len(value),
                4,
            )
        )

    @staticmethod
    def _decode_string_list(
        prop: ParsedFdtProperty,
        *,
        context: str,
    ) -> tuple[
        str,
        ...,
    ]:
        value = prop.value

        if (
            not value
            or not value.endswith(
                b"\x00"
            )
        ):
            raise DtboOverlayParsingError(
                f"{context} must be NUL-terminated string data"
            )

        raw_parts = value[
            :-1
        ].split(
            b"\x00"
        )

        if any(
            not part
            for part in raw_parts
        ):
            raise DtboOverlayParsingError(
                f"{context} contains an empty string"
            )

        try:
            return tuple(
                part.decode(
                    "utf-8"
                )
                for part in raw_parts
            )
        except UnicodeDecodeError as error:
            raise DtboOverlayParsingError(
                f"{context} is not valid UTF-8"
            ) from error
