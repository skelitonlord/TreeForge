from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from treeforge.android.universe.dtbo.requirement import (
    AndroidUniverseDtboRequirement,
)
from treeforge.android.universe.dtbo.reconciliation import (
    AndroidUniverseFdtReferenceStatus,
)


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboEntrySignature:
    requirement: AndroidUniverseDtboRequirement
    signature_id: str

    models: tuple[str, ...]
    compatibles: tuple[str, ...]
    external_symbols: tuple[str, ...]
    fragment_target_paths: tuple[str, ...]
    status_values: tuple[str, ...]

    external_reference_count: int
    local_reference_count: int
    fragment_external_count: int
    fragment_path_count: int

    def __post_init__(self) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseDtboRequirement,
        ):
            raise TypeError(
                "requirement must be an AndroidUniverseDtboRequirement"
            )

        if (
            not isinstance(self.signature_id, str)
            or not self.signature_id
        ):
            raise ValueError(
                "signature_id must be a non-empty string"
            )

        for name, values in (
            ("models", self.models),
            ("compatibles", self.compatibles),
            ("external_symbols", self.external_symbols),
            ("fragment_target_paths", self.fragment_target_paths),
            ("status_values", self.status_values),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if not all(
                isinstance(item, str)
                for item in values
            ):
                raise TypeError(
                    f"{name} must contain only strings"
                )

        for name, value in (
            ("external_reference_count", self.external_reference_count),
            ("local_reference_count", self.local_reference_count),
            ("fragment_external_count", self.fragment_external_count),
            ("fragment_path_count", self.fragment_path_count),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboPropertyDelta:
    """
    Exact property-level difference between two canonical DTBO entries.

    The location is identified by absolute node path + property name.
    Raw property bytes remain the authoritative comparison basis.
    """

    node_path: str
    property_name: str
    left_value: bytes | None
    right_value: bytes | None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.node_path, str)
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be an absolute path"
            )

        if (
            not isinstance(self.property_name, str)
            or not self.property_name
        ):
            raise ValueError(
                "property_name must be a non-empty string"
            )

        for name, value in (
            ("left_value", self.left_value),
            ("right_value", self.right_value),
        ):
            if (
                value is not None
                and not isinstance(value, bytes)
            ):
                raise TypeError(
                    f"{name} must be bytes or None"
                )

        if (
            self.left_value is None
            and self.right_value is None
        ):
            raise ValueError(
                "property delta must differ on at least one side"
            )

        if (
            self.left_value is not None
            and self.right_value is not None
            and self.left_value == self.right_value
        ):
            raise ValueError(
                "property delta values must differ"
            )

    @property
    def kind(self) -> str:
        if self.left_value is None:
            return "added"

        if self.right_value is None:
            return "removed"

        return "changed"


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboReferenceDelta:
    """
    One canonical reference relationship present on only one side.
    """

    side: str
    node_path: str
    property_name: str
    byte_offset: int | None
    status: str
    phandle: int | None
    target_path: str | None
    symbol: str | None

    def __post_init__(self) -> None:
        if self.side not in {
            "left_only",
            "right_only",
        }:
            raise ValueError(
                "side must be left_only or right_only"
            )

        if (
            not isinstance(self.node_path, str)
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be absolute"
            )

        if (
            not isinstance(self.property_name, str)
            or not self.property_name
        ):
            raise ValueError(
                "property_name must be non-empty"
            )

        if (
            self.byte_offset is not None
            and (
                isinstance(self.byte_offset, bool)
                or not isinstance(self.byte_offset, int)
                or self.byte_offset < 0
            )
        ):
            raise ValueError(
                "byte_offset must be non-negative or None"
            )

        if (
            not isinstance(self.status, str)
            or not self.status
        ):
            raise ValueError(
                "status must be non-empty"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboEntryDelta:
    """
    Exact semantic delta between two DTBO population entries.

    This records structural FDT differences and canonical Universe reference
    differences without interpreting vendor-specific board revision policy.
    """

    left_index: int
    right_index: int

    left_signature_id: str
    right_signature_id: str

    left_models: tuple[str, ...]
    right_models: tuple[str, ...]

    added_nodes: tuple[str, ...]
    removed_nodes: tuple[str, ...]

    property_deltas: tuple[
        AndroidUniverseDtboPropertyDelta,
        ...,
    ]

    reference_deltas: tuple[
        AndroidUniverseDtboReferenceDelta,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            isinstance(self.left_index, bool)
            or not isinstance(self.left_index, int)
            or self.left_index < 0
        ):
            raise ValueError(
                "left_index must be a non-negative integer"
            )

        if (
            isinstance(self.right_index, bool)
            or not isinstance(self.right_index, int)
            or self.right_index <= self.left_index
        ):
            raise ValueError(
                "right_index must be greater than left_index"
            )

        for name, value in (
            ("left_signature_id", self.left_signature_id),
            ("right_signature_id", self.right_signature_id),
        ):
            if (
                not isinstance(value, str)
                or not value
            ):
                raise ValueError(
                    f"{name} must be non-empty"
                )

        for name, values in (
            ("left_models", self.left_models),
            ("right_models", self.right_models),
            ("added_nodes", self.added_nodes),
            ("removed_nodes", self.removed_nodes),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if not all(
                isinstance(item, str)
                for item in values
            ):
                raise TypeError(
                    f"{name} must contain only strings"
                )

        if not isinstance(
            self.property_deltas,
            tuple,
        ):
            raise TypeError(
                "property_deltas must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboPropertyDelta,
            )
            for item in self.property_deltas
        ):
            raise TypeError(
                "property_deltas contains invalid entries"
            )

        if not isinstance(
            self.reference_deltas,
            tuple,
        ):
            raise TypeError(
                "reference_deltas must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboReferenceDelta,
            )
            for item in self.reference_deltas
        ):
            raise TypeError(
                "reference_deltas contains invalid entries"
            )

    @property
    def same_signature(self) -> bool:
        return (
            self.left_signature_id
            == self.right_signature_id
        )

    @property
    def model_only_difference(self) -> bool:
        return (
            self.left_models
            != self.right_models
            and not self.added_nodes
            and not self.removed_nodes
            and not self.property_deltas
            and not self.reference_deltas
        )


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboVariantPropertyEvidence:
    """
    One property location proven to vary across the DTBO population.

    ``value`` is the exact raw ParsedFdtProperty value for this entry.
    ``None`` means the property is absent in this entry.

    Universe records the distinction without assigning vendor-specific
    semantics to the property name.
    """

    node_path: str
    property_name: str
    value: bytes | None

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.node_path,
                str,
            )
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be an absolute path"
            )

        if (
            not isinstance(
                self.property_name,
                str,
            )
            or not self.property_name
        ):
            raise ValueError(
                "property_name must be a non-empty string"
            )

        if (
            self.value is not None
            and not isinstance(
                self.value,
                bytes,
            )
        ):
            raise TypeError(
                "value must be bytes or None"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboVariantReferenceEvidence:
    """
    One reference relationship that is not invariant across all DTBO entries.
    """

    node_path: str
    property_name: str
    byte_offset: int | None
    status: str
    phandle: int | None
    target_path: str | None
    symbol: str | None

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.node_path,
                str,
            )
            or not self.node_path.startswith("/")
        ):
            raise ValueError(
                "node_path must be an absolute path"
            )

        if (
            not isinstance(
                self.property_name,
                str,
            )
            or not self.property_name
        ):
            raise ValueError(
                "property_name must be a non-empty string"
            )

        if (
            self.byte_offset is not None
            and (
                isinstance(
                    self.byte_offset,
                    bool,
                )
                or not isinstance(
                    self.byte_offset,
                    int,
                )
                or self.byte_offset < 0
            )
        ):
            raise ValueError(
                "byte_offset must be non-negative or None"
            )

        if (
            not isinstance(
                self.status,
                str,
            )
            or not self.status
        ):
            raise ValueError(
                "status must be a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboVariant:
    """
    Canonical DTBO population variant profile.

    The profile is evidence-driven. It records only facts proven to vary
    across the complete DTBO population and preserves the exact owning
    AndroidUniverseDtboRequirement.

    It does not assign lifecycle, chronology, hardware-generation, or
    vendor-specific policy semantics.
    """

    requirement: AndroidUniverseDtboRequirement
    entry_index: int
    signature_id: str
    variant_profile_id: str
    variant_family_id: str

    models: tuple[str, ...]

    properties: tuple[
        AndroidUniverseDtboVariantPropertyEvidence,
        ...,
    ]

    references: tuple[
        AndroidUniverseDtboVariantReferenceEvidence,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseDtboRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseDtboRequirement"
            )

        if (
            isinstance(
                self.entry_index,
                bool,
            )
            or not isinstance(
                self.entry_index,
                int,
            )
            or self.entry_index < 0
        ):
            raise ValueError(
                "entry_index must be a non-negative integer"
            )

        for name, value in (
            (
                "signature_id",
                self.signature_id,
            ),
            (
                "variant_profile_id",
                self.variant_profile_id,
            ),
            (
                "variant_family_id",
                self.variant_family_id,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{name} must be non-empty"
                )

        if not isinstance(
            self.models,
            tuple,
        ):
            raise TypeError(
                "models must be a tuple"
            )

        if not all(
            isinstance(
                item,
                str,
            )
            for item in self.models
        ):
            raise TypeError(
                "models must contain only strings"
            )

        if not isinstance(
            self.properties,
            tuple,
        ):
            raise TypeError(
                "properties must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboVariantPropertyEvidence,
            )
            for item in self.properties
        ):
            raise TypeError(
                "properties contains invalid variant evidence"
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
                AndroidUniverseDtboVariantReferenceEvidence,
            )
            for item in self.references
        ):
            raise TypeError(
                "references contains invalid variant evidence"
            )


@dataclass(frozen=True, slots=True)
class AndroidUniverseDtboPopulationReconciliation:
    entries: tuple[
        AndroidUniverseDtboEntrySignature,
        ...,
    ]

    shared_compatibles: tuple[str, ...]
    varying_compatibles: tuple[str, ...]

    shared_external_symbols: tuple[str, ...]
    varying_external_symbols: tuple[str, ...]

    shared_fragment_target_paths: tuple[str, ...]
    varying_fragment_target_paths: tuple[str, ...]

    shared_status_values: tuple[str, ...]
    varying_status_values: tuple[str, ...]

    signature_groups: tuple[
        tuple[str, tuple[int, ...]],
        ...,
    ]


    entry_deltas: tuple[
        AndroidUniverseDtboEntryDelta,
        ...,
    ]


    variants: tuple[
        AndroidUniverseDtboVariant,
        ...,
    ]

    varying_property_locations: tuple[
        tuple[str, str],
        ...,
    ]

    varying_reference_keys: tuple[
        tuple[
            str,
            str,
            int | None,
            str,
            int | None,
            str | None,
            str | None,
        ],
        ...,
    ]


    variant_family_groups: tuple[
        tuple[
            str,
            tuple[int, ...],
        ],
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(self.entries, tuple):
            raise TypeError("entries must be a tuple")

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboEntrySignature,
            )
            for item in self.entries
        ):
            raise TypeError(
                "entries must contain only "
                "AndroidUniverseDtboEntrySignature instances"
            )

        for name in (
            "shared_compatibles",
            "varying_compatibles",
            "shared_external_symbols",
            "varying_external_symbols",
            "shared_fragment_target_paths",
            "varying_fragment_target_paths",
            "shared_status_values",
            "varying_status_values",
        ):
            values = getattr(self, name)

            if not isinstance(values, tuple):
                raise TypeError(
                    f"{name} must be a tuple"
                )

            if not all(
                isinstance(item, str)
                for item in values
            ):
                raise TypeError(
                    f"{name} must contain only strings"
                )

        if not isinstance(
            self.signature_groups,
            tuple,
        ):
            raise TypeError(
                "signature_groups must be a tuple"
            )


        if not isinstance(
            self.entry_deltas,
            tuple,
        ):
            raise TypeError(
                "entry_deltas must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboEntryDelta,
            )
            for item in self.entry_deltas
        ):
            raise TypeError(
                "entry_deltas must contain only "
                "AndroidUniverseDtboEntryDelta instances"
            )

        expected_delta_count = (
            len(self.entries)
            * (len(self.entries) - 1)
            // 2
        )

        if len(
            self.entry_deltas
        ) != expected_delta_count:
            raise ValueError(
                "entry_deltas must preserve the complete "
                "pairwise DTBO population comparison"
            )


        if not isinstance(
            self.variants,
            tuple,
        ):
            raise TypeError(
                "variants must be a tuple"
            )

        if len(
            self.variants
        ) != len(
            self.entries
        ):
            raise ValueError(
                "variants must preserve the complete "
                "DTBO population"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboVariant,
            )
            for item in self.variants
        ):
            raise TypeError(
                "variants must contain only "
                "AndroidUniverseDtboVariant instances"
            )

        if not all(
            variant.requirement
            is entry.requirement
            for variant, entry
            in zip(
                self.variants,
                self.entries,
                strict=True,
            )
        ):
            raise ValueError(
                "variants must preserve exact DTBO "
                "requirement identity and order"
            )

        if not isinstance(
            self.varying_property_locations,
            tuple,
        ):
            raise TypeError(
                "varying_property_locations must be a tuple"
            )

        if not isinstance(
            self.varying_reference_keys,
            tuple,
        ):
            raise TypeError(
                "varying_reference_keys must be a tuple"
            )


        if not isinstance(
            self.variant_family_groups,
            tuple,
        ):
            raise TypeError(
                "variant_family_groups must be a tuple"
            )

        family_members = []

        for (
            family_id,
            indices,
        ) in self.variant_family_groups:
            if (
                not isinstance(
                    family_id,
                    str,
                )
                or not family_id
            ):
                raise ValueError(
                    "variant family IDs must be non-empty strings"
                )

            if not isinstance(
                indices,
                tuple,
            ):
                raise TypeError(
                    "variant family indices must be a tuple"
                )

            family_members.extend(
                indices
            )

        if tuple(
            sorted(
                family_members
            )
        ) != tuple(
            range(
                len(
                    self.variants
                )
            )
        ):
            raise ValueError(
                "variant_family_groups must preserve the complete "
                "DTBO variant population exactly once"
            )

        for variant in self.variants:
            if not any(
                variant.variant_family_id
                == family_id
                and variant.entry_index
                in indices
                for (
                    family_id,
                    indices,
                ) in self.variant_family_groups
            ):
                raise ValueError(
                    "variant family groups must preserve each "
                    "variant's canonical family identity"
                )


class AndroidUniverseDtboPopulationReconciler:
    """
    Reconcile the complete DTBO population across entries.

    This reconciler compares already-interpreted Universe DTBO requirements.
    It does not infer vendor-specific board revision chronology or activation
    policy. Its responsibility is to establish population invariants,
    differences, and semantically identical groups.
    """

    def reconcile(
        self,
        requirements: tuple[
            AndroidUniverseDtboRequirement,
            ...,
        ],
    ) -> AndroidUniverseDtboPopulationReconciliation:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseDtboRequirement,
            )
            for item in requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseDtboRequirement instances"
            )

        entries = tuple(
            self._signature(requirement)
            for requirement in requirements
        )

        compatible_sets = tuple(
            set(entry.compatibles)
            for entry in entries
        )

        symbol_sets = tuple(
            set(entry.external_symbols)
            for entry in entries
        )

        target_path_sets = tuple(
            set(entry.fragment_target_paths)
            for entry in entries
        )

        status_sets = tuple(
            set(entry.status_values)
            for entry in entries
        )

        (
            shared_compatibles,
            varying_compatibles,
        ) = self._shared_and_varying(
            compatible_sets
        )

        (
            shared_external_symbols,
            varying_external_symbols,
        ) = self._shared_and_varying(
            symbol_sets
        )

        (
            shared_fragment_target_paths,
            varying_fragment_target_paths,
        ) = self._shared_and_varying(
            target_path_sets
        )

        (
            shared_status_values,
            varying_status_values,
        ) = self._shared_and_varying(
            status_sets
        )

        groups: dict[
            str,
            list[int],
        ] = {}

        for index, entry in enumerate(entries):
            groups.setdefault(
                entry.signature_id,
                [],
            ).append(index)

        signature_groups = tuple(
            (
                signature_id,
                tuple(indices),
            )
            for (
                signature_id,
                indices,
            ) in sorted(
                groups.items(),
                key=lambda item: item[0],
            )
        )

        entry_deltas = tuple(
            self._delta(
                left_index=left_index,
                right_index=right_index,
                left=entries[left_index],
                right=entries[right_index],
            )
            for left_index
            in range(
                len(entries)
            )
            for right_index
            in range(
                left_index + 1,
                len(entries),
            )
        )

        varying_property_locations = (
            self._varying_property_locations(
                entries
            )
        )

        varying_reference_keys = (
            self._varying_reference_keys(
                entries
            )
        )

        variants = tuple(
            self._variant(
                entry_index=index,
                entry=entry,
                varying_property_locations=(
                    varying_property_locations
                ),
                varying_reference_keys=(
                    varying_reference_keys
                ),
            )
            for index, entry
            in enumerate(entries)
        )

        family_groups: dict[
            str,
            list[int],
        ] = {}

        for variant in variants:
            family_groups.setdefault(
                variant.variant_family_id,
                [],
            ).append(
                variant.entry_index
            )

        variant_family_groups = tuple(
            (
                family_id,
                tuple(
                    indices
                ),
            )
            for (
                family_id,
                indices,
            ) in sorted(
                family_groups.items(),
                key=lambda item: item[0],
            )
        )

        return AndroidUniverseDtboPopulationReconciliation(
            entries=entries,
            shared_compatibles=shared_compatibles,
            varying_compatibles=varying_compatibles,
            shared_external_symbols=shared_external_symbols,
            varying_external_symbols=varying_external_symbols,
            shared_fragment_target_paths=shared_fragment_target_paths,
            varying_fragment_target_paths=varying_fragment_target_paths,
            shared_status_values=shared_status_values,
            varying_status_values=varying_status_values,
            signature_groups=signature_groups,
            entry_deltas=entry_deltas,
            variants=variants,
            varying_property_locations=(
                varying_property_locations
            ),
            varying_reference_keys=(
                varying_reference_keys
            ),
            variant_family_groups=(
                variant_family_groups
            ),
        )

    def _signature(
        self,
        requirement: AndroidUniverseDtboRequirement,
    ) -> AndroidUniverseDtboEntrySignature:
        semantics = requirement.semantics

        external_symbols = tuple(
            sorted(
                {
                    reference.symbol
                    for reference
                    in semantics.references
                    if (
                        reference.status
                        is AndroidUniverseFdtReferenceStatus.EXTERNAL_SYMBOL
                        and reference.symbol is not None
                    )
                }
            )
        )

        fragment_target_paths = tuple(
            sorted(
                {
                    reference.target_path
                    for reference
                    in semantics.references
                    if (
                        reference.status
                        is AndroidUniverseFdtReferenceStatus.FRAGMENT_TARGET_PATH
                        and reference.target_path is not None
                    )
                }
            )
        )

        external_reference_count = sum(
            reference.status
            is AndroidUniverseFdtReferenceStatus.EXTERNAL_SYMBOL
            for reference in semantics.references
        )

        local_reference_count = sum(
            reference.status
            is AndroidUniverseFdtReferenceStatus.RESOLVED_LOCAL
            for reference in semantics.references
        )

        fragment_external_count = sum(
            reference.status
            is AndroidUniverseFdtReferenceStatus.FRAGMENT_TARGET_EXTERNAL
            for reference in semantics.references
        )

        fragment_path_count = sum(
            reference.status
            is AndroidUniverseFdtReferenceStatus.FRAGMENT_TARGET_PATH
            for reference in semantics.references
        )

        models = tuple(
            sorted(
                semantics.models
            )
        )

        compatibles = tuple(
            sorted(
                set(
                    semantics.compatibles
                )
            )
        )

        statuses = tuple(
            sorted(
                set(
                    semantics.statuses
                )
            )
        )

        payload = repr(
            (
                compatibles,
                external_symbols,
                fragment_target_paths,
                statuses,
                external_reference_count,
                local_reference_count,
                fragment_external_count,
                fragment_path_count,
            )
        ).encode(
            "utf-8"
        )

        signature_id = (
            sha256(payload)
            .hexdigest()[:16]
        )

        return AndroidUniverseDtboEntrySignature(
            requirement=requirement,
            signature_id=signature_id,
            models=models,
            compatibles=compatibles,
            external_symbols=external_symbols,
            fragment_target_paths=fragment_target_paths,
            status_values=statuses,
            external_reference_count=external_reference_count,
            local_reference_count=local_reference_count,
            fragment_external_count=fragment_external_count,
            fragment_path_count=fragment_path_count,
        )

    @staticmethod
    def _property_map(
        entry: AndroidUniverseDtboEntrySignature,
    ) -> dict[
        tuple[str, str],
        bytes,
    ]:
        return {
            (
                observation.node_path,
                observation.property_name,
            ): observation.raw_value
            for observation
            in entry.requirement.property_observations
        }

    def _varying_property_locations(
        self,
        entries: tuple[
            AndroidUniverseDtboEntrySignature,
            ...,
        ],
    ) -> tuple[
        tuple[str, str],
        ...,
    ]:
        if not entries:
            return ()

        maps = tuple(
            self._property_map(
                entry
            )
            for entry in entries
        )

        all_locations = set().union(
            *(
                set(mapping)
                for mapping in maps
            )
        )

        varying = []

        for location in sorted(
            all_locations
        ):
            values = tuple(
                mapping.get(
                    location
                )
                for mapping in maps
            )

            if len(
                set(values)
            ) > 1:
                varying.append(
                    location
                )

        return tuple(
            varying
        )

    def _varying_reference_keys(
        self,
        entries: tuple[
            AndroidUniverseDtboEntrySignature,
            ...,
        ],
    ) -> tuple[
        tuple[
            str,
            str,
            int | None,
            str,
            int | None,
            str | None,
            str | None,
        ],
        ...,
    ]:
        if not entries:
            return ()

        populations = tuple(
            {
                self._reference_key(
                    reference
                )
                for reference
                in entry.requirement.semantics.references
            }
            for entry in entries
        )

        all_keys = set().union(
            *populations
        )

        shared_keys = set.intersection(
            *populations
        )

        return tuple(
            sorted(
                all_keys
                - shared_keys,
                key=repr,
            )
        )

    def _variant(
        self,
        *,
        entry_index: int,
        entry: AndroidUniverseDtboEntrySignature,
        varying_property_locations: tuple[
            tuple[str, str],
            ...,
        ],
        varying_reference_keys: tuple[
            tuple[
                str,
                str,
                int | None,
                str,
                int | None,
                str | None,
                str | None,
            ],
            ...,
        ],
    ) -> AndroidUniverseDtboVariant:
        property_map = (
            self._property_map(
                entry
            )
        )

        properties = tuple(
            AndroidUniverseDtboVariantPropertyEvidence(
                node_path=node_path,
                property_name=property_name,
                value=property_map.get(
                    (
                        node_path,
                        property_name,
                    )
                ),
            )
            for (
                node_path,
                property_name,
            ) in varying_property_locations
        )

        entry_reference_keys = {
            self._reference_key(
                reference
            )
            for reference
            in entry.requirement.semantics.references
        }

        references = tuple(
            AndroidUniverseDtboVariantReferenceEvidence(
                node_path=key[0],
                property_name=key[1],
                byte_offset=key[2],
                status=key[3],
                phandle=key[4],
                target_path=key[5],
                symbol=key[6],
            )
            for key in varying_reference_keys
            if key in entry_reference_keys
        )

        payload = repr(
            (
                tuple(
                    (
                        item.node_path,
                        item.property_name,
                        item.value,
                    )
                    for item in properties
                ),
                tuple(
                    (
                        item.node_path,
                        item.property_name,
                        item.byte_offset,
                        item.status,
                        item.phandle,
                        item.target_path,
                        item.symbol,
                    )
                    for item in references
                ),
            )
        ).encode(
            "utf-8"
        )

        variant_profile_id = (
            sha256(
                payload
            )
            .hexdigest()[:16]
        )

        variant_family_payload = repr(
            (
                tuple(
                    (
                        item.node_path,
                        item.property_name,
                        item.value is not None,
                    )
                    for item in properties
                ),
                tuple(
                    (
                        item.node_path,
                        item.property_name,
                        item.byte_offset,
                        item.status,
                        item.phandle,
                        item.target_path,
                        item.symbol,
                    )
                    for item in references
                ),
            )
        ).encode(
            "utf-8"
        )

        variant_family_id = (
            sha256(
                variant_family_payload
            )
            .hexdigest()[:16]
        )

        return AndroidUniverseDtboVariant(
            requirement=entry.requirement,
            entry_index=entry_index,
            signature_id=(
                entry.signature_id
            ),
            variant_profile_id=(
                variant_profile_id
            ),
            variant_family_id=(
                variant_family_id
            ),
            models=entry.models,
            properties=properties,
            references=references,
        )

    def _delta(
        self,
        *,
        left_index: int,
        right_index: int,
        left: AndroidUniverseDtboEntrySignature,
        right: AndroidUniverseDtboEntrySignature,
    ) -> AndroidUniverseDtboEntryDelta:
        left_requirement = (
            left.requirement
        )
        right_requirement = (
            right.requirement
        )

        left_nodes = {
            node.path
            for node
            in left_requirement.semantics.nodes
        }

        right_nodes = {
            node.path
            for node
            in right_requirement.semantics.nodes
        }

        added_nodes = tuple(
            sorted(
                right_nodes
                - left_nodes
            )
        )

        removed_nodes = tuple(
            sorted(
                left_nodes
                - right_nodes
            )
        )

        left_properties = {
            (
                observation.node_path,
                observation.property_name,
            ): observation.raw_value
            for observation
            in left_requirement.property_observations
        }

        right_properties = {
            (
                observation.node_path,
                observation.property_name,
            ): observation.raw_value
            for observation
            in right_requirement.property_observations
        }

        property_deltas = []

        all_property_keys = sorted(
            set(left_properties)
            | set(right_properties)
        )

        for (
            node_path,
            property_name,
        ) in all_property_keys:
            left_value = (
                left_properties.get(
                    (
                        node_path,
                        property_name,
                    )
                )
            )

            right_value = (
                right_properties.get(
                    (
                        node_path,
                        property_name,
                    )
                )
            )

            if left_value == right_value:
                continue

            property_deltas.append(
                AndroidUniverseDtboPropertyDelta(
                    node_path=node_path,
                    property_name=property_name,
                    left_value=left_value,
                    right_value=right_value,
                )
            )

        left_references = {
            self._reference_key(reference)
            for reference
            in left_requirement.semantics.references
        }

        right_references = {
            self._reference_key(reference)
            for reference
            in right_requirement.semantics.references
        }

        reference_deltas = []

        for key in sorted(
            left_references
            - right_references,
            key=repr,
        ):
            reference_deltas.append(
                self._reference_delta(
                    side="left_only",
                    key=key,
                )
            )

        for key in sorted(
            right_references
            - left_references,
            key=repr,
        ):
            reference_deltas.append(
                self._reference_delta(
                    side="right_only",
                    key=key,
                )
            )

        return AndroidUniverseDtboEntryDelta(
            left_index=left_index,
            right_index=right_index,
            left_signature_id=(
                left.signature_id
            ),
            right_signature_id=(
                right.signature_id
            ),
            left_models=left.models,
            right_models=right.models,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            property_deltas=tuple(
                property_deltas
            ),
            reference_deltas=tuple(
                reference_deltas
            ),
        )

    @staticmethod
    def _reference_key(
        reference,
    ) -> tuple[
        str,
        str,
        int | None,
        str,
        int | None,
        str | None,
        str | None,
    ]:
        return (
            reference.source.node_path,
            reference.source.property_name,
            reference.byte_offset,
            reference.status.name,
            reference.phandle,
            reference.target_path,
            reference.symbol,
        )

    @staticmethod
    def _reference_delta(
        *,
        side: str,
        key: tuple[
            str,
            str,
            int | None,
            str,
            int | None,
            str | None,
            str | None,
        ],
    ) -> AndroidUniverseDtboReferenceDelta:
        (
            node_path,
            property_name,
            byte_offset,
            status,
            phandle,
            target_path,
            symbol,
        ) = key

        return AndroidUniverseDtboReferenceDelta(
            side=side,
            node_path=node_path,
            property_name=property_name,
            byte_offset=byte_offset,
            status=status,
            phandle=phandle,
            target_path=target_path,
            symbol=symbol,
        )

    @staticmethod
    def _shared_and_varying(
        populations: tuple[
            set[str],
            ...,
        ],
    ) -> tuple[
        tuple[str, ...],
        tuple[str, ...],
    ]:
        if not populations:
            return (), ()

        shared = set.intersection(
            *populations
        )

        union = set.union(
            *populations
        )

        varying = (
            union
            - shared
        )

        return (
            tuple(
                sorted(shared)
            ),
            tuple(
                sorted(varying)
            ),
        )
