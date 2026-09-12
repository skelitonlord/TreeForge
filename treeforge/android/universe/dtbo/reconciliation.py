from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from treeforge.android.parsing.dtb import (
    ParsedDtboOverlayMetadata,
    ParsedFdtNode,
    ParsedFdtProperty,
)

from treeforge.android.universe.dtbo.semantic import (
    AndroidUniverseFdtPropertyObservation,
    AndroidUniverseFdtSemanticKind,
    AndroidUniverseFdtValueKind,
)


class AndroidUniverseFdtReferenceStatus(Enum):
    """
    Resolution state for one authoritative compiled-overlay reference.

    EXTERNAL_SYMBOL
        Parsing's __fixups__ metadata identifies a reference that must be
        satisfied by a symbol in the base device tree.

    RESOLVED_LOCAL
        Parsing's __local_fixups__ metadata identifies a local relocation and
        the referenced phandle resolves to a node inside this overlay.

    UNRESOLVED_LOCAL
        A local relocation is structurally identified but its current phandle
        cannot be matched to a local node.

    FRAGMENT_TARGET_EXTERNAL
        A fragment uses a target cell that is not a local overlay phandle and
        therefore represents a base-tree target.

    FRAGMENT_TARGET_PATH
        A fragment directly names its base-tree destination using target-path.
    """

    EXTERNAL_SYMBOL = auto()
    RESOLVED_LOCAL = auto()
    UNRESOLVED_LOCAL = auto()
    FRAGMENT_TARGET_EXTERNAL = auto()
    FRAGMENT_TARGET_PATH = auto()


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFdtNodeObservation:
    node: ParsedFdtNode
    path: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.node,
            ParsedFdtNode,
        ):
            raise TypeError(
                "node must be a ParsedFdtNode"
            )

        if (
            not isinstance(
                self.path,
                str,
            )
            or not self.path.startswith("/")
        ):
            raise ValueError(
                "path must be absolute"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFdtReferenceObservation:
    """
    Canonical Universe interpretation of one reference location established
    by Parsing's compiled-overlay metadata.

    ``source`` preserves the exact semantic property observation corresponding
    to the referenced FDT property.

    ``byte_offset`` is the byte offset of the phandle cell inside that
    property's raw value when the reference is cell-backed.

    ``symbol`` is populated only for an external __fixups__ reference.

    ``target_path`` is populated for resolved local references and explicit
    target-path fragment destinations.
    """

    source: AndroidUniverseFdtPropertyObservation
    byte_offset: int | None
    phandle: int | None
    status: AndroidUniverseFdtReferenceStatus
    target_path: str | None = None
    symbol: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseFdtPropertyObservation,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseFdtPropertyObservation"
            )

        if self.byte_offset is not None:
            if (
                isinstance(
                    self.byte_offset,
                    bool,
                )
                or not isinstance(
                    self.byte_offset,
                    int,
                )
            ):
                raise TypeError(
                    "byte_offset must be an integer or None"
                )

            if self.byte_offset < 0:
                raise ValueError(
                    "byte_offset cannot be negative"
                )

            if self.byte_offset % 4:
                raise ValueError(
                    "byte_offset must be 4-byte aligned"
                )

        if self.phandle is not None:
            if (
                isinstance(
                    self.phandle,
                    bool,
                )
                or not isinstance(
                    self.phandle,
                    int,
                )
            ):
                raise TypeError(
                    "phandle must be an integer or None"
                )

        if not isinstance(
            self.status,
            AndroidUniverseFdtReferenceStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseFdtReferenceStatus"
            )

        if self.target_path is not None:
            if (
                not isinstance(
                    self.target_path,
                    str,
                )
                or not self.target_path.startswith("/")
            ):
                raise ValueError(
                    "target_path must be an absolute path or None"
                )

        if self.symbol is not None:
            if (
                not isinstance(
                    self.symbol,
                    str,
                )
                or not self.symbol
            ):
                raise ValueError(
                    "symbol must be a non-empty string or None"
                )

        if (
            self.status
            is AndroidUniverseFdtReferenceStatus.EXTERNAL_SYMBOL
            and self.symbol is None
        ):
            raise ValueError(
                "EXTERNAL_SYMBOL reference requires symbol"
            )

        if (
            self.status
            is AndroidUniverseFdtReferenceStatus.FRAGMENT_TARGET_PATH
            and self.target_path is None
        ):
            raise ValueError(
                "FRAGMENT_TARGET_PATH requires target_path"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFdtEntrySemantics:
    nodes: tuple[
        AndroidUniverseFdtNodeObservation,
        ...,
    ]

    references: tuple[
        AndroidUniverseFdtReferenceObservation,
        ...,
    ]

    models: tuple[str, ...]
    compatibles: tuple[str, ...]
    statuses: tuple[str, ...]

    duplicate_phandles: tuple[int, ...]

    external_fixup_count: int
    local_fixup_count: int
    fragment_target_count: int

    def __post_init__(self) -> None:
        if not isinstance(
            self.nodes,
            tuple,
        ):
            raise TypeError(
                "nodes must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFdtNodeObservation,
            )
            for item in self.nodes
        ):
            raise TypeError(
                "nodes must contain only "
                "AndroidUniverseFdtNodeObservation instances"
            )

        if not isinstance(
            self.references,
            tuple,
        ):
            raise TypeError(
                "references must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFdtReferenceObservation,
            )
            for item in self.references
        ):
            raise TypeError(
                "references must contain only "
                "AndroidUniverseFdtReferenceObservation instances"
            )

        for name, values in (
            (
                "models",
                self.models,
            ),
            (
                "compatibles",
                self.compatibles,
            ),
            (
                "statuses",
                self.statuses,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if not all(
                isinstance(
                    item,
                    str,
                )
                for item in values
            ):
                raise TypeError(
                    f"{name} must contain only strings"
                )

        if not isinstance(
            self.duplicate_phandles,
            tuple,
        ):
            raise TypeError(
                "duplicate_phandles must be a tuple"
            )

        if not all(
            isinstance(
                item,
                int,
            )
            for item in self.duplicate_phandles
        ):
            raise TypeError(
                "duplicate_phandles must contain only integers"
            )

        for (
            name,
            value,
        ) in (
            (
                "external_fixup_count",
                self.external_fixup_count,
            ),
            (
                "local_fixup_count",
                self.local_fixup_count,
            ),
            (
                "fragment_target_count",
                self.fragment_target_count,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )


class AndroidUniverseFdtReconciler:
    """
    Reconcile one parsed compiled device-tree overlay.

    Parsing is authoritative for the literal overlay metadata:
      - __fixups__;
      - __local_fixups__;
      - __symbols__;
      - fragment target / target-path declarations.

    Universe consumes those canonical structures to classify reference
    relationships. It does not rediscover or reparse overlay metadata and does
    not guess reference-bearing properties from property names.

    Local phandle declarations remain interpreted from the generic semantic
    property observations because they are intrinsic FDT semantics.
    """

    def reconcile(
        self,
        *,
        overlay: ParsedDtboOverlayMetadata,
        observations: tuple[
            AndroidUniverseFdtPropertyObservation,
            ...,
        ],
    ) -> AndroidUniverseFdtEntrySemantics:
        if not isinstance(
            overlay,
            ParsedDtboOverlayMetadata,
        ):
            raise TypeError(
                "overlay must be a ParsedDtboOverlayMetadata"
            )

        if not isinstance(
            observations,
            tuple,
        ):
            raise TypeError(
                "observations must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseFdtPropertyObservation,
            )
            for item in observations
        ):
            raise TypeError(
                "observations must contain only "
                "AndroidUniverseFdtPropertyObservation instances"
            )

        node_by_path: dict[
            str,
            ParsedFdtNode,
        ] = {}

        observation_by_location: dict[
            tuple[
                str,
                str,
            ],
            AndroidUniverseFdtPropertyObservation,
        ] = {}

        for observation in observations:
            node_by_path.setdefault(
                observation.node_path,
                observation.node,
            )

            key = (
                observation.node_path,
                observation.property_name,
            )

            if key in observation_by_location:
                raise ValueError(
                    "duplicate FDT property observation location: "
                    f"{key[0]}:{key[1]}"
                )

            observation_by_location[
                key
            ] = observation

        node_observations = tuple(
            AndroidUniverseFdtNodeObservation(
                node=node,
                path=path,
            )
            for (
                path,
                node,
            ) in sorted(
                node_by_path.items(),
                key=lambda item: item[0],
            )
        )

        (
            phandle_paths,
            duplicate_phandles,
        ) = self._build_phandle_index(
            observations
        )

        references: list[
            AndroidUniverseFdtReferenceObservation
        ] = []

        references.extend(
            self._external_references(
                overlay=overlay,
                observation_by_location=(
                    observation_by_location
                ),
            )
        )

        references.extend(
            self._local_references(
                overlay=overlay,
                observation_by_location=(
                    observation_by_location
                ),
                phandle_paths=phandle_paths,
            )
        )

        references.extend(
            self._fragment_references(
                overlay=overlay,
                observation_by_location=(
                    observation_by_location
                ),
                phandle_paths=phandle_paths,
            )
        )

        models = tuple(
            string
            for observation in observations
            if (
                observation.semantic_kind
                is AndroidUniverseFdtSemanticKind.MODEL
            )
            for string in observation.strings
        )

        compatibles = tuple(
            string
            for observation in observations
            if (
                observation.semantic_kind
                is AndroidUniverseFdtSemanticKind.COMPATIBLE
            )
            for string in observation.strings
        )

        statuses = tuple(
            string
            for observation in observations
            if (
                observation.semantic_kind
                is AndroidUniverseFdtSemanticKind.STATUS
            )
            for string in observation.strings
        )

        return AndroidUniverseFdtEntrySemantics(
            nodes=node_observations,
            references=tuple(
                references
            ),
            models=models,
            compatibles=compatibles,
            statuses=statuses,
            duplicate_phandles=tuple(
                sorted(
                    duplicate_phandles
                )
            ),
            external_fixup_count=sum(
                len(
                    fixup.locations
                )
                for fixup
                in overlay.external_fixups
            ),
            local_fixup_count=sum(
                len(
                    fixup.byte_offsets
                )
                for fixup
                in overlay.local_fixups
            ),
            fragment_target_count=len(
                overlay.fragment_targets
            ),
        )

    @staticmethod
    def _build_phandle_index(
        observations: tuple[
            AndroidUniverseFdtPropertyObservation,
            ...,
        ],
    ) -> tuple[
        dict[
            int,
            str,
        ],
        set[int],
    ]:
        phandle_paths: dict[
            int,
            str,
        ] = {}

        duplicate_phandles: set[
            int
        ] = set()

        for observation in observations:
            if (
                observation.semantic_kind
                is not AndroidUniverseFdtSemanticKind.PHANDLE
            ):
                continue

            if (
                observation.value_kind
                is not AndroidUniverseFdtValueKind.CELLS
                or len(
                    observation.cells
                )
                != 1
            ):
                continue

            phandle = (
                observation.cells[0]
            )

            existing = (
                phandle_paths.get(
                    phandle
                )
            )

            if existing is None:
                phandle_paths[
                    phandle
                ] = observation.node_path

            elif (
                existing
                != observation.node_path
            ):
                duplicate_phandles.add(
                    phandle
                )

        return (
            phandle_paths,
            duplicate_phandles,
        )

    def _external_references(
        self,
        *,
        overlay: ParsedDtboOverlayMetadata,
        observation_by_location: dict[
            tuple[
                str,
                str,
            ],
            AndroidUniverseFdtPropertyObservation,
        ],
    ) -> tuple[
        AndroidUniverseFdtReferenceObservation,
        ...,
    ]:
        results = []

        for fixup in overlay.external_fixups:
            for location in fixup.locations:
                observation = (
                    self._require_observation(
                        observation_by_location,
                        node_path=(
                            location.node_path
                        ),
                        property_name=(
                            location.property_name
                        ),
                        context=(
                            "external fixup "
                            f"{fixup.symbol!r}"
                        ),
                    )
                )

                phandle = (
                    self._read_u32_at_offset(
                        observation.property,
                        location.byte_offset,
                        context=(
                            "external fixup "
                            f"{fixup.symbol!r}"
                        ),
                    )
                )

                results.append(
                    AndroidUniverseFdtReferenceObservation(
                        source=observation,
                        byte_offset=(
                            location.byte_offset
                        ),
                        phandle=phandle,
                        status=(
                            AndroidUniverseFdtReferenceStatus
                            .EXTERNAL_SYMBOL
                        ),
                        symbol=fixup.symbol,
                    )
                )

        return tuple(
            results
        )

    def _local_references(
        self,
        *,
        overlay: ParsedDtboOverlayMetadata,
        observation_by_location: dict[
            tuple[
                str,
                str,
            ],
            AndroidUniverseFdtPropertyObservation,
        ],
        phandle_paths: dict[
            int,
            str,
        ],
    ) -> tuple[
        AndroidUniverseFdtReferenceObservation,
        ...,
    ]:
        results = []

        for fixup in overlay.local_fixups:
            observation = (
                self._require_observation(
                    observation_by_location,
                    node_path=(
                        fixup.node_path
                    ),
                    property_name=(
                        fixup.property_name
                    ),
                    context=(
                        "local fixup"
                    ),
                )
            )

            for byte_offset in (
                fixup.byte_offsets
            ):
                phandle = (
                    self._read_u32_at_offset(
                        observation.property,
                        byte_offset,
                        context=(
                            "local fixup "
                            f"{fixup.node_path}:"
                            f"{fixup.property_name}"
                        ),
                    )
                )

                target_path = (
                    phandle_paths.get(
                        phandle
                    )
                )

                status = (
                    AndroidUniverseFdtReferenceStatus
                    .RESOLVED_LOCAL
                    if target_path is not None
                    else
                    AndroidUniverseFdtReferenceStatus
                    .UNRESOLVED_LOCAL
                )

                results.append(
                    AndroidUniverseFdtReferenceObservation(
                        source=observation,
                        byte_offset=(
                            byte_offset
                        ),
                        phandle=phandle,
                        status=status,
                        target_path=(
                            target_path
                        ),
                    )
                )

        return tuple(
            results
        )

    def _fragment_references(
        self,
        *,
        overlay: ParsedDtboOverlayMetadata,
        observation_by_location: dict[
            tuple[
                str,
                str,
            ],
            AndroidUniverseFdtPropertyObservation,
        ],
        phandle_paths: dict[
            int,
            str,
        ],
    ) -> tuple[
        AndroidUniverseFdtReferenceObservation,
        ...,
    ]:
        results = []

        for target in (
            overlay.fragment_targets
        ):
            observation = (
                self._require_observation(
                    observation_by_location,
                    node_path=(
                        target.fragment_path
                    ),
                    property_name=(
                        target.target_property.name
                    ),
                    context=(
                        "fragment target"
                    ),
                )
            )

            if (
                target.target_path
                is not None
            ):
                results.append(
                    AndroidUniverseFdtReferenceObservation(
                        source=observation,
                        byte_offset=None,
                        phandle=None,
                        status=(
                            AndroidUniverseFdtReferenceStatus
                            .FRAGMENT_TARGET_PATH
                        ),
                        target_path=(
                            target.target_path
                        ),
                    )
                )
                continue

            phandle = (
                target.target_phandle
            )

            if phandle is None:
                raise ValueError(
                    "fragment target has no "
                    "phandle or path"
                )

            local_path = (
                phandle_paths.get(
                    phandle
                )
            )

            if local_path is not None:
                status = (
                    AndroidUniverseFdtReferenceStatus
                    .RESOLVED_LOCAL
                )
                target_path = (
                    local_path
                )
            else:
                status = (
                    AndroidUniverseFdtReferenceStatus
                    .FRAGMENT_TARGET_EXTERNAL
                )
                target_path = None

            results.append(
                AndroidUniverseFdtReferenceObservation(
                    source=observation,
                    byte_offset=0,
                    phandle=phandle,
                    status=status,
                    target_path=target_path,
                )
            )

        return tuple(
            results
        )

    @staticmethod
    def _require_observation(
        observations: dict[
            tuple[
                str,
                str,
            ],
            AndroidUniverseFdtPropertyObservation,
        ],
        *,
        node_path: str,
        property_name: str,
        context: str,
    ) -> AndroidUniverseFdtPropertyObservation:
        key = (
            node_path,
            property_name,
        )

        observation = (
            observations.get(
                key
            )
        )

        if observation is None:
            raise ValueError(
                f"{context} refers to missing "
                "parsed FDT property: "
                f"{node_path}:{property_name}"
            )

        return observation

    @staticmethod
    def _read_u32_at_offset(
        prop: ParsedFdtProperty,
        byte_offset: int,
        *,
        context: str,
    ) -> int:
        if (
            byte_offset < 0
            or byte_offset % 4
        ):
            raise ValueError(
                f"{context} byte offset must be "
                "non-negative and 4-byte aligned"
            )

        end = (
            byte_offset
            + 4
        )

        if end > len(
            prop.value
        ):
            raise ValueError(
                f"{context} byte offset extends "
                "beyond property value: "
                f"offset={byte_offset}, "
                f"size={len(prop.value)}"
            )

        return int.from_bytes(
            prop.value[
                byte_offset:end
            ],
            byteorder="big",
            signed=False,
        )
