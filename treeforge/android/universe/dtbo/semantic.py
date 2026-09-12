from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from treeforge.android.parsing.dtb import (
    ParsedFdtNode,
    ParsedFdtProperty,
)


class AndroidUniverseFdtValueKind(Enum):
    EMPTY = auto()
    STRING = auto()
    STRING_LIST = auto()
    CELLS = auto()
    BYTES = auto()


class AndroidUniverseFdtSemanticKind(Enum):
    GENERIC = auto()
    COMPATIBLE = auto()
    MODEL = auto()
    STATUS = auto()
    PHANDLE = auto()
    ADDRESS_CELLS = auto()
    SIZE_CELLS = auto()
    REG = auto()
    RANGES = auto()
    DMA_RANGES = auto()
    INTERRUPTS = auto()
    INTERRUPT_PARENT = auto()
    CLOCKS = auto()
    RESETS = auto()
    POWER_DOMAINS = auto()
    IOMMUS = auto()
    MEMORY_REGION = auto()
    TARGET = auto()
    TARGET_PATH = auto()


_STANDARD_SEMANTICS = {
    "compatible": AndroidUniverseFdtSemanticKind.COMPATIBLE,
    "model": AndroidUniverseFdtSemanticKind.MODEL,
    "status": AndroidUniverseFdtSemanticKind.STATUS,
    "phandle": AndroidUniverseFdtSemanticKind.PHANDLE,
    "linux,phandle": AndroidUniverseFdtSemanticKind.PHANDLE,
    "#address-cells": AndroidUniverseFdtSemanticKind.ADDRESS_CELLS,
    "#size-cells": AndroidUniverseFdtSemanticKind.SIZE_CELLS,
    "reg": AndroidUniverseFdtSemanticKind.REG,
    "ranges": AndroidUniverseFdtSemanticKind.RANGES,
    "dma-ranges": AndroidUniverseFdtSemanticKind.DMA_RANGES,
    "interrupts": AndroidUniverseFdtSemanticKind.INTERRUPTS,
    "interrupt-parent": AndroidUniverseFdtSemanticKind.INTERRUPT_PARENT,
    "clocks": AndroidUniverseFdtSemanticKind.CLOCKS,
    "resets": AndroidUniverseFdtSemanticKind.RESETS,
    "power-domains": AndroidUniverseFdtSemanticKind.POWER_DOMAINS,
    "iommus": AndroidUniverseFdtSemanticKind.IOMMUS,
    "memory-region": AndroidUniverseFdtSemanticKind.MEMORY_REGION,
    "target": AndroidUniverseFdtSemanticKind.TARGET,
    "target-path": AndroidUniverseFdtSemanticKind.TARGET_PATH,
}


@dataclass(frozen=True, slots=True)
class AndroidUniverseFdtPropertyObservation:
    node: ParsedFdtNode
    property: ParsedFdtProperty
    node_path: str
    value_kind: AndroidUniverseFdtValueKind
    semantic_kind: AndroidUniverseFdtSemanticKind
    strings: tuple[str, ...] = ()
    cells: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.node, ParsedFdtNode):
            raise TypeError("node must be a ParsedFdtNode")
        if not isinstance(self.property, ParsedFdtProperty):
            raise TypeError("property must be a ParsedFdtProperty")
        if not isinstance(self.node_path, str):
            raise TypeError("node_path must be a string")
        if not self.node_path.startswith("/"):
            raise ValueError("node_path must be absolute")
        if not isinstance(self.value_kind, AndroidUniverseFdtValueKind):
            raise TypeError("value_kind must be an AndroidUniverseFdtValueKind")
        if not isinstance(self.semantic_kind, AndroidUniverseFdtSemanticKind):
            raise TypeError(
                "semantic_kind must be an AndroidUniverseFdtSemanticKind"
            )
        if not isinstance(self.strings, tuple):
            raise TypeError("strings must be a tuple")
        if not all(isinstance(item, str) for item in self.strings):
            raise TypeError("strings must contain only strings")
        if not isinstance(self.cells, tuple):
            raise TypeError("cells must be a tuple")
        if not all(isinstance(item, int) for item in self.cells):
            raise TypeError("cells must contain only integers")

    @property
    def raw_value(self) -> bytes:
        return self.property.value

    @property
    def property_name(self) -> str:
        return self.property.name


class AndroidUniverseFdtSemanticInterpreter:
    """
    Interpret generic, intrinsic FDT property value shapes and standard
    property names without applying device-, vendor-, SoC-, or binding-specific
    policy.

    Raw Parsing bytes remain canonical evidence.
    """

    def interpret_tree(
        self,
        root: ParsedFdtNode,
    ) -> tuple[AndroidUniverseFdtPropertyObservation, ...]:
        if not isinstance(root, ParsedFdtNode):
            raise TypeError("root must be a ParsedFdtNode")

        observations: list[AndroidUniverseFdtPropertyObservation] = []
        self._walk(
            node=root,
            path="/",
            observations=observations,
        )
        return tuple(observations)

    def _walk(
        self,
        *,
        node: ParsedFdtNode,
        path: str,
        observations: list[AndroidUniverseFdtPropertyObservation],
    ) -> None:
        for prop in node.properties:
            observations.append(
                self.interpret_property(
                    node=node,
                    node_path=path,
                    prop=prop,
                )
            )

        for child in node.children:
            child_path = (
                f"/{child.name}"
                if path == "/"
                else f"{path}/{child.name}"
            )
            self._walk(
                node=child,
                path=child_path,
                observations=observations,
            )

    def interpret_property(
        self,
        *,
        node: ParsedFdtNode,
        node_path: str,
        prop: ParsedFdtProperty,
    ) -> AndroidUniverseFdtPropertyObservation:
        semantic_kind = _STANDARD_SEMANTICS.get(
            prop.name,
            AndroidUniverseFdtSemanticKind.GENERIC,
        )

        value_kind, strings, cells = self._decode_value_shape(
            prop.value
        )

        return AndroidUniverseFdtPropertyObservation(
            node=node,
            property=prop,
            node_path=node_path,
            value_kind=value_kind,
            semantic_kind=semantic_kind,
            strings=strings,
            cells=cells,
        )

    @staticmethod
    def _decode_value_shape(
        value: bytes,
    ) -> tuple[
        AndroidUniverseFdtValueKind,
        tuple[str, ...],
        tuple[int, ...],
    ]:
        if not value:
            return (
                AndroidUniverseFdtValueKind.EMPTY,
                (),
                (),
            )

        strings = (
            AndroidUniverseFdtSemanticInterpreter
            ._decode_nul_strings(value)
        )
        if strings is not None:
            return (
                (
                    AndroidUniverseFdtValueKind.STRING
                    if len(strings) == 1
                    else AndroidUniverseFdtValueKind.STRING_LIST
                ),
                strings,
                (),
            )

        if len(value) % 4 == 0:
            cells = tuple(
                int.from_bytes(
                    value[offset:offset + 4],
                    byteorder="big",
                    signed=False,
                )
                for offset in range(0, len(value), 4)
            )
            return (
                AndroidUniverseFdtValueKind.CELLS,
                (),
                cells,
            )

        return (
            AndroidUniverseFdtValueKind.BYTES,
            (),
            (),
        )

    @staticmethod
    def _decode_nul_strings(
        value: bytes,
    ) -> tuple[str, ...] | None:
        if not value.endswith(b"\x00"):
            return None

        raw_parts = value[:-1].split(b"\x00")
        if not raw_parts or any(not part for part in raw_parts):
            return None

        decoded: list[str] = []

        for part in raw_parts:
            try:
                text = part.decode("utf-8")
            except UnicodeDecodeError:
                return None

            if any(
                ord(character) < 0x20
                or ord(character) == 0x7F
                for character in text
            ):
                return None

            decoded.append(text)

        return tuple(decoded)
