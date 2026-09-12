from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSourceKind,
)
from treeforge.android.parsing.input import (
    AndroidInputLexicalLine,
    AndroidInputLexicalLineKind,
    AndroidInputParsingResult,
    ParsedAndroidInputConfiguration,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)


class AndroidUniverseInputSelectorKind(StrEnum):
    GENERIC = "generic"
    VIRTUAL = "virtual"
    USB_IDENTITY = "usb_identity"
    NAMED = "named"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputSelector:
    """
    Canonical syntactic selector encoded by an Android input filename.

    This is selection metadata only. It does not claim that a matching
    physical input device exists or that the source is active.
    """

    kind: AndroidUniverseInputSelectorKind
    name: str

    vendor_id: int | None = None
    product_id: int | None = None
    version_id: int | None = None

    fallback: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.kind,
            AndroidUniverseInputSelectorKind,
        ):
            raise TypeError(
                "kind must be an AndroidUniverseInputSelectorKind"
            )

        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                "name must be a non-empty string"
            )

        for field_name, value in (
            ("vendor_id", self.vendor_id),
            ("product_id", self.product_id),
            ("version_id", self.version_id),
        ):
            if value is None:
                continue

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{field_name} must be a non-negative integer or None"
                )

        if not isinstance(self.fallback, bool):
            raise TypeError(
                "fallback must be a bool"
            )


class AndroidUniverseInputKlDeclarationKind(StrEnum):
    KEY = "key"
    AXIS = "axis"
    SENSOR = "sensor"
    LED = "led"
    REQUIRES_KERNEL_CONFIG = "requires_kernel_config"
    UNKNOWN = "unknown"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputKlDeclaration:
    """
    One Universe-interpreted KL declaration.

    ``operands`` preserves the complete non-comment operand sequence so later
    reconstruction never needs to reopen the source. Specialized fields are
    intentionally limited to semantics provable directly from the declaration.
    """

    source_line: AndroidInputLexicalLine
    kind: AndroidUniverseInputKlDeclarationKind
    operands: tuple[str, ...]

    linux_code: str | None = None
    android_symbol: str | None = None
    flags: tuple[str, ...] = ()

    usage_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_line,
            AndroidInputLexicalLine,
        ):
            raise TypeError(
                "source_line must be an AndroidInputLexicalLine"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseInputKlDeclarationKind,
        ):
            raise TypeError(
                "kind must be an AndroidUniverseInputKlDeclarationKind"
            )

        if not isinstance(self.operands, tuple):
            raise TypeError(
                "operands must be a tuple"
            )

        if not all(
            isinstance(value, str)
            for value in self.operands
        ):
            raise TypeError(
                "operands must contain only strings"
            )

        if not isinstance(self.flags, tuple):
            raise TypeError(
                "flags must be a tuple"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputKcmMapping:
    source_line: AndroidInputLexicalLine
    condition: str
    result: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_line,
            AndroidInputLexicalLine,
        ):
            raise TypeError(
                "source_line must be an AndroidInputLexicalLine"
            )

        if not isinstance(self.condition, str) or not self.condition:
            raise ValueError(
                "condition must be a non-empty string"
            )

        if not isinstance(self.result, str):
            raise TypeError(
                "result must be a string"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputKcmKey:
    source_line: AndroidInputLexicalLine
    key_name: str

    mappings: tuple[
        AndroidUniverseInputKcmMapping,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source_line,
            AndroidInputLexicalLine,
        ):
            raise TypeError(
                "source_line must be an AndroidInputLexicalLine"
            )

        if not isinstance(self.key_name, str) or not self.key_name:
            raise ValueError(
                "key_name must be a non-empty string"
            )

        if not isinstance(self.mappings, tuple):
            raise TypeError(
                "mappings must be a tuple"
            )

        if not all(
            isinstance(
                mapping,
                AndroidUniverseInputKcmMapping,
            )
            for mapping in self.mappings
        ):
            raise TypeError(
                "mappings must contain only "
                "AndroidUniverseInputKcmMapping values"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputIdcAssignment:
    """
    One IDC property assignment with conservative scalar interpretation.

    ``raw_value`` is always authoritative. ``value`` is only a literal scalar
    interpretation and does not assign property-specific Android policy.
    """

    source_line: AndroidInputLexicalLine
    key: str
    raw_value: str

    value: bool | int | float | str

    @property
    def namespace(self) -> str:
        return self.key.partition(".")[0]


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputLayoutRelationship:
    """
    Candidate relationship produced by an exact IDC keyboard.layout value.

    Candidate sources are retained exactly. Universe does not choose between
    multiple matching canonical KL sources without stronger applicability
    evidence.
    """

    assignment: AndroidUniverseInputIdcAssignment

    candidates: tuple[
        ParsedAndroidInputConfiguration,
        ...,
    ]

    @property
    def resolved(self) -> bool:
        return len(self.candidates) == 1

    @property
    def ambiguous(self) -> bool:
        return len(self.candidates) > 1


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputConfigurationRequirement:
    source: ParsedAndroidInputConfiguration
    artifact: AndroidUniverseArtifactRequirement
    selector: AndroidUniverseInputSelector

    kl_declarations: tuple[
        AndroidUniverseInputKlDeclaration,
        ...,
    ] = ()

    kcm_type: str | None = None

    kcm_keys: tuple[
        AndroidUniverseInputKcmKey,
        ...,
    ] = ()

    idc_assignments: tuple[
        AndroidUniverseInputIdcAssignment,
        ...,
    ] = ()

    uninterpreted_lines: tuple[
        AndroidInputLexicalLine,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidInputConfiguration,
        ):
            raise TypeError(
                "source must be a ParsedAndroidInputConfiguration"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an AndroidUniverseArtifactRequirement"
            )

        if not isinstance(
            self.selector,
            AndroidUniverseInputSelector,
        ):
            raise TypeError(
                "selector must be an AndroidUniverseInputSelector"
            )
        filesystem_source = (
            self.source.source.filesystem_source
        )

        if (
            self.artifact.inventory_entry.artifact
            is not filesystem_source.artifact
        ):
            raise ValueError(
                "Input requirement must preserve exact Parsing "
                "filesystem artifact identity"
            )

        metadata_entry = (
            self.artifact.inventory_entry
            .metadata_entry_for_materialized_path(
                self.source.source.host_path
            )
        )

        if (
            metadata_entry
            is not self.artifact.metadata_entry
        ):
            raise ValueError(
                "Input requirement must preserve exact canonical "
                "filesystem metadata identity"
            )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInputRequirement:
    source: AndroidInputParsingResult

    configurations: tuple[
        AndroidUniverseInputConfigurationRequirement,
        ...,
    ]

    layout_relationships: tuple[
        AndroidUniverseInputLayoutRelationship,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidInputParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidInputParsingResult"
            )

        if not isinstance(self.configurations, tuple):
            raise TypeError(
                "configurations must be a tuple"
            )

        if len(
            self.configurations
        ) != len(
            self.source.configurations
        ):
            raise ValueError(
                "Input requirement must conserve the complete "
                "Parsing input population"
            )

        if not all(
            requirement.source is parsed
            for requirement, parsed
            in zip(
                self.configurations,
                self.source.configurations,
                strict=True,
            )
        ):
            raise ValueError(
                "Input requirement must preserve exact Parsing "
                "configuration identity and order"
            )


_USB_SELECTOR = re.compile(
    r"^Vendor_([0-9A-Fa-f]{4})"
    r"_Product_([0-9A-Fa-f]{4})"
    r"(?:_Version_([0-9A-Fa-f]{4}))?"
    r"(_fallback)?$"
)


def _selector_for(
    source: ParsedAndroidInputConfiguration,
) -> AndroidUniverseInputSelector:
    stem = source.source.android_path.stem

    if stem == "Generic":
        return AndroidUniverseInputSelector(
            kind=AndroidUniverseInputSelectorKind.GENERIC,
            name=stem,
        )

    if stem == "Virtual":
        return AndroidUniverseInputSelector(
            kind=AndroidUniverseInputSelectorKind.VIRTUAL,
            name=stem,
        )

    match = _USB_SELECTOR.fullmatch(
        stem
    )

    if match is not None:
        vendor, product, version, fallback = (
            match.groups()
        )

        return AndroidUniverseInputSelector(
            kind=(
                AndroidUniverseInputSelectorKind
                .USB_IDENTITY
            ),
            name=stem,
            vendor_id=int(
                vendor,
                16,
            ),
            product_id=int(
                product,
                16,
            ),
            version_id=(
                int(
                    version,
                    16,
                )
                if version is not None
                else None
            ),
            fallback=(
                fallback is not None
            ),
        )

    return AndroidUniverseInputSelector(
        kind=AndroidUniverseInputSelectorKind.NAMED,
        name=stem,
        fallback=stem.endswith(
            "_fallback"
        ),
    )


def _source_tokens(
    line: AndroidInputLexicalLine,
) -> tuple[str, ...]:
    """
    Return semantic tokens before an inline KL/KCM comment.

    Parsing's original line and complete token stream remain retained by the
    source line, so stripping comments here cannot lose canonical evidence.
    """

    content = line.content.partition(
        "#"
    )[0].strip()

    if not content:
        return ()

    return tuple(
        content.split()
    )


def _interpret_kl(
    source: ParsedAndroidInputConfiguration,
) -> tuple[
    tuple[
        AndroidUniverseInputKlDeclaration,
        ...,
    ],
    tuple[
        AndroidInputLexicalLine,
        ...,
    ],
]:
    declarations = []
    uninterpreted = []

    for line in source.lines:
        if (
            line.kind
            not in {
                AndroidInputLexicalLineKind.DECLARATION,
                AndroidInputLexicalLineKind.BLOCK_OPEN,
            }
        ):
            continue

        tokens = _source_tokens(
            line
        )

        if not tokens:
            continue

        keyword = tokens[0]

        try:
            kind = (
                AndroidUniverseInputKlDeclarationKind(
                    keyword
                )
            )
        except ValueError:
            kind = (
                AndroidUniverseInputKlDeclarationKind
                .UNKNOWN
            )

        operands = tuple(
            tokens[1:]
        )

        linux_code = None
        android_symbol = None
        usage_code = None
        flags = ()

        if kind is AndroidUniverseInputKlDeclarationKind.KEY:
            if (
                len(operands) >= 3
                and operands[0] == "usage"
            ):
                usage_code = operands[1]
                android_symbol = operands[2]
                flags = tuple(
                    operands[3:]
                )
            elif len(operands) >= 2:
                linux_code = operands[0]
                android_symbol = operands[1]
                flags = tuple(
                    operands[2:]
                )

        elif kind in {
            AndroidUniverseInputKlDeclarationKind.SENSOR,
            AndroidUniverseInputKlDeclarationKind.LED,
        }:
            if operands:
                linux_code = operands[0]

            if len(operands) >= 2:
                android_symbol = operands[1]

            flags = tuple(
                operands[2:]
            )

        declarations.append(
            AndroidUniverseInputKlDeclaration(
                source_line=line,
                kind=kind,
                operands=operands,
                linux_code=linux_code,
                android_symbol=android_symbol,
                flags=flags,
                usage_code=usage_code,
            )
        )

        if (
            kind
            is AndroidUniverseInputKlDeclarationKind.UNKNOWN
        ):
            uninterpreted.append(
                line
            )

    return (
        tuple(
            declarations
        ),
        tuple(
            uninterpreted
        ),
    )


def _interpret_kcm(
    source: ParsedAndroidInputConfiguration,
) -> tuple[
    str | None,
    tuple[
        AndroidUniverseInputKcmKey,
        ...,
    ],
    tuple[
        AndroidInputLexicalLine,
        ...,
    ],
]:
    keyboard_type = None
    keys = []
    uninterpreted = []

    current_open = None
    current_name = None
    current_mappings = []

    for line in source.lines:
        content = line.content.strip()

        if (
            line.kind
            in {
                AndroidInputLexicalLineKind.BLANK,
                AndroidInputLexicalLineKind.COMMENT,
            }
        ):
            continue

        if (
            line.kind
            is AndroidInputLexicalLineKind.DECLARATION
            and content.startswith(
                "type "
            )
            and current_name is None
        ):
            value = content[
                len("type "):
            ].strip()

            if value:
                keyboard_type = value
                continue

        if (
            line.kind
            is AndroidInputLexicalLineKind.BLOCK_OPEN
        ):
            tokens = _source_tokens(
                line
            )

            if (
                len(tokens) == 3
                and tokens[0] == "key"
                and tokens[2] == "{"
                and current_name is None
            ):
                current_open = line
                current_name = tokens[1]
                current_mappings = []
                continue

        if (
            line.kind
            is AndroidInputLexicalLineKind.BLOCK_CLOSE
            and current_name is not None
        ):
            keys.append(
                AndroidUniverseInputKcmKey(
                    source_line=current_open,
                    key_name=current_name,
                    mappings=tuple(
                        current_mappings
                    ),
                )
            )

            current_open = None
            current_name = None
            current_mappings = []
            continue

        if current_name is not None:
            condition, separator, result = (
                content.partition(":")
            )

            if separator and condition.strip():
                current_mappings.append(
                    AndroidUniverseInputKcmMapping(
                        source_line=line,
                        condition=condition.strip(),
                        result=result.strip(),
                    )
                )
                continue

        uninterpreted.append(
            line
        )

    if current_name is not None:
        raise ValueError(
            "KCM semantic interpretation encountered an "
            "unterminated key block"
        )

    return (
        keyboard_type,
        tuple(
            keys
        ),
        tuple(
            uninterpreted
        ),
    )


def _scalar(
    raw: str,
) -> bool | int | float | str:
    normalized = raw.strip()

    lowered = normalized.lower()

    if lowered == "true":
        return True

    if lowered == "false":
        return False

    try:
        return int(
            normalized,
            0,
        )
    except ValueError:
        pass

    try:
        return float(
            normalized
        )
    except ValueError:
        return raw


def _interpret_idc(
    source: ParsedAndroidInputConfiguration,
) -> tuple[
    tuple[
        AndroidUniverseInputIdcAssignment,
        ...,
    ],
    tuple[
        AndroidInputLexicalLine,
        ...,
    ],
]:
    assignments = []
    uninterpreted = []

    for line in source.lines:
        if (
            line.kind
            in {
                AndroidInputLexicalLineKind.BLANK,
                AndroidInputLexicalLineKind.COMMENT,
            }
        ):
            continue

        if (
            line.kind
            is AndroidInputLexicalLineKind.ASSIGNMENT
            and line.key is not None
            and line.value is not None
        ):
            assignments.append(
                AndroidUniverseInputIdcAssignment(
                    source_line=line,
                    key=line.key,
                    raw_value=line.value,
                    value=_scalar(
                        line.value
                    ),
                )
            )

            continue

        uninterpreted.append(
            line
        )

    return (
        tuple(
            assignments
        ),
        tuple(
            uninterpreted
        ),
    )




def _artifact_for_source(
    source: ParsedAndroidInputConfiguration,
    *,
    artifact_requirements: (
        AndroidUniverseArtifactRequirementInventory
    ),
) -> AndroidUniverseArtifactRequirement:
    """
    Reconcile one parsed Input source to its exact canonical
    filesystem Artifact requirement.

    Final reconciliation uses exact canonical upstream object identity.
    """

    filesystem_source = (
        source.source.filesystem_source
    )

    try:
        inventory_entry = (
            artifact_requirements
            .source_inventory
            .entry_for_artifact(
                filesystem_source.artifact
            )
        )
    except KeyError as error:
        raise ValueError(
            "Input Parsing filesystem source does not preserve a "
            "canonical Filesystem Metadata artifact identity: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()}"
        ) from error

    if (
        inventory_entry.artifact
        is not filesystem_source.artifact
    ):
        raise ValueError(
            "Input filesystem inventory lookup did not preserve "
            "exact Extraction artifact identity"
        )

    try:
        metadata_path = (
            inventory_entry
            .filesystem_path_for_materialized_path(
                source.source.host_path
            )
        )
    except ValueError as error:
        raise ValueError(
            "Input Parsing host path does not belong to its exact "
            "canonical filesystem artifact: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()}"
        ) from error

    metadata_entry = (
        inventory_entry
        .result
        .metadata
        .get(
            metadata_path
        )
    )

    if metadata_entry is None:
        raise ValueError(
            "Input Parsing source does not map to canonical "
            "filesystem metadata: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()} "
            f"-> {metadata_path}"
        )

    matches = tuple(
        requirement
        for requirement
        in artifact_requirements.requirements
        if (
            requirement.inventory_entry
            is inventory_entry
            and requirement.metadata_entry
            is metadata_entry
        )
    )

    if len(matches) != 1:
        raise ValueError(
            "Input Parsing source must reconcile to exactly one "
            "Artifact requirement by exact canonical object identity: "
            f"{source.source.source_name}:"
            f"{source.source.android_path.as_posix()} "
            f"-> {metadata_path} "
            f"matches={len(matches)}"
        )

    return matches[0]

class AndroidUniverseInputInterpreter:
    def interpret(
        self,
        parsing: AndroidInputParsingResult,
        *,
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseInputRequirement:
        if not isinstance(
            parsing,
            AndroidInputParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidInputParsingResult"
            )

        if not isinstance(
            artifact_requirements,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "artifact_requirements must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        requirements = []

        for source in parsing.configurations:
            kl_declarations = ()
            kcm_type = None
            kcm_keys = ()
            idc_assignments = ()
            uninterpreted = ()

            if (
                source.source.kind
                is AndroidModelSourceKind.INPUT_KEY_LAYOUT
            ):
                (
                    kl_declarations,
                    uninterpreted,
                ) = _interpret_kl(
                    source
                )

            elif (
                source.source.kind
                is AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP
            ):
                (
                    kcm_type,
                    kcm_keys,
                    uninterpreted,
                ) = _interpret_kcm(
                    source
                )

            elif (
                source.source.kind
                is AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION
            ):
                (
                    idc_assignments,
                    uninterpreted,
                ) = _interpret_idc(
                    source
                )

            requirements.append(
                AndroidUniverseInputConfigurationRequirement(
                    source=source,
                    artifact=_artifact_for_source(
                        source,
                        artifact_requirements=(
                            artifact_requirements
                        ),
                    ),
                    selector=_selector_for(
                        source
                    ),
                    kl_declarations=(
                        kl_declarations
                    ),
                    kcm_type=kcm_type,
                    kcm_keys=kcm_keys,
                    idc_assignments=(
                        idc_assignments
                    ),
                    uninterpreted_lines=(
                        uninterpreted
                    ),
                )
            )

        requirements = tuple(
            requirements
        )

        key_layouts_by_name = {}

        for requirement in requirements:
            if (
                requirement.source.source.kind
                is not AndroidModelSourceKind.INPUT_KEY_LAYOUT
            ):
                continue

            key_layouts_by_name.setdefault(
                requirement.source.source.android_path.stem,
                [],
            ).append(
                requirement.source
            )

        relationships = []

        for requirement in requirements:
            for assignment in (
                requirement.idc_assignments
            ):
                if assignment.key != "keyboard.layout":
                    continue

                declared_name = (
                    assignment.raw_value.strip()
                )

                relationships.append(
                    AndroidUniverseInputLayoutRelationship(
                        assignment=assignment,
                        candidates=tuple(
                            key_layouts_by_name.get(
                                declared_name,
                                (),
                            )
                        ),
                    )
                )

        return AndroidUniverseInputRequirement(
            source=parsing,
            configurations=requirements,
            layout_relationships=tuple(
                relationships
            ),
        )
