from __future__ import annotations

from dataclasses import dataclass


RECOVERY_RUNTIME_REPORT_PREFIX = (
    "TreeForge recovery: "
)


def _required_string(
    fields: dict[str, str],
    key: str,
    *,
    record: str,
) -> str:
    value = fields.get(key)

    if value is None or not value:
        raise ValueError(
            f"{record} is missing {key!r}"
        )

    return value


def _required_integer(
    fields: dict[str, str],
    key: str,
    *,
    record: str,
) -> int:
    raw = _required_string(
        fields,
        key,
        record=record,
    )

    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(
            f"{record} has invalid integer "
            f"{key!r}: {raw!r}"
        ) from error

    return value


def _required_boolean(
    fields: dict[str, str],
    key: str,
    *,
    record: str,
) -> bool:
    value = _required_integer(
        fields,
        key,
        record=record,
    )

    if value not in {
        0,
        1,
    }:
        raise ValueError(
            f"{record} has invalid boolean "
            f"{key!r}: {value!r}"
        )

    return bool(value)


def _parse_record_fields(
    values: list[str],
    *,
    record: str,
) -> dict[str, str]:
    fields: dict[str, str] = {}

    for value in values:
        if "=" not in value:
            continue

        key, raw = value.split(
            "=",
            1,
        )

        if not key:
            raise ValueError(
                f"{record} contains an empty field name"
            )

        if key in fields:
            raise ValueError(
                f"{record} contains duplicate "
                f"field {key!r}"
            )

        fields[key] = raw

    return fields


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryDeviceFlashTarget:
    target_type: str
    policy: str

    name: str
    canonical_name: str
    slot: str | None

    active: bool
    selectable: bool

    capacity_bytes: int
    allocated: bool

    metadata_slot: int | None
    extents: int

    def __post_init__(self) -> None:
        if self.target_type not in {
            "physical",
            "logical",
        }:
            raise ValueError(
                "unsupported Recovery flash target "
                f"type: {self.target_type!r}"
            )

        if not self.policy:
            raise ValueError(
                "Recovery flash target policy "
                "cannot be empty"
            )

        if not self.name:
            raise ValueError(
                "Recovery flash target name "
                "cannot be empty"
            )

        if not self.canonical_name:
            raise ValueError(
                "Recovery flash target canonical "
                "name cannot be empty"
            )

        if self.slot not in {
            None,
            "a",
            "b",
        }:
            raise ValueError(
                "Recovery flash target slot must "
                "be a, b, or None"
            )

        if self.capacity_bytes < 0:
            raise ValueError(
                "Recovery flash target capacity "
                "cannot be negative"
            )

        if self.extents < 0:
            raise ValueError(
                "Recovery flash target extent "
                "count cannot be negative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class RecoveryDeviceState:
    active_slot: str

    super_found: bool
    lp_resolved: bool
    lp_authoritative_valid: bool
    virtual_ab: bool

    flash_targets: tuple[
        RecoveryDeviceFlashTarget,
        ...,
    ]

    def __post_init__(self) -> None:
        if self.active_slot not in {
            "a",
            "b",
        }:
            raise ValueError(
                "Recovery active slot must be a or b"
            )

        if not isinstance(
            self.flash_targets,
            tuple,
        ):
            raise TypeError(
                "flash_targets must be a tuple"
            )

        if not self.flash_targets:
            raise ValueError(
                "Recovery device state must contain "
                "flash targets"
            )

        names = tuple(
            target.name
            for target in self.flash_targets
        )

        if len(names) != len(set(names)):
            raise ValueError(
                "Recovery device state contains "
                "duplicate flash target names"
            )

        identities = tuple(
            (
                target.canonical_name,
                target.slot,
            )
            for target in self.flash_targets
        )

        if (
            len(identities)
            != len(set(identities))
        ):
            raise ValueError(
                "Recovery device state contains "
                "ambiguous canonical target identities"
            )

    def target_for(
        self,
        *,
        canonical_name: str,
        slot: str,
    ) -> RecoveryDeviceFlashTarget | None:
        if not canonical_name:
            raise ValueError(
                "canonical_name cannot be empty"
            )

        if slot not in {
            "a",
            "b",
        }:
            raise ValueError(
                "slot must be a or b"
            )

        matches = tuple(
            target
            for target in self.flash_targets
            if (
                target.canonical_name
                == canonical_name
                and target.slot == slot
            )
        )

        if len(matches) > 1:
            raise RuntimeError(
                "Recovery device state contains "
                "ambiguous target mapping for "
                f"{canonical_name}_{slot}"
            )

        return (
            matches[0]
            if matches
            else None
        )


def parse_recovery_runtime_report(
    text: str,
) -> RecoveryDeviceState:
    if not isinstance(text, str):
        raise TypeError(
            "text must be a string"
        )

    lp_geometry: dict[str, str] | None = None
    flash_summary: dict[str, str] | None = None

    targets: list[
        RecoveryDeviceFlashTarget
    ] = []

    for raw_line in text.splitlines():
        if not raw_line.startswith(
            RECOVERY_RUNTIME_REPORT_PREFIX
        ):
            continue

        payload = raw_line[
            len(
                RECOVERY_RUNTIME_REPORT_PREFIX
            ):
        ]

        tokens = payload.split()

        if not tokens:
            continue

        record = tokens[0]

        fields = _parse_record_fields(
            tokens[1:],
            record=record,
        )

        if record == "lp_geometry":
            if lp_geometry is not None:
                raise ValueError(
                    "Recovery runtime report contains "
                    "multiple lp_geometry records"
                )

            lp_geometry = fields

        elif record == "flash_targets":
            if flash_summary is not None:
                raise ValueError(
                    "Recovery runtime report contains "
                    "multiple flash_targets records"
                )

            flash_summary = fields

        elif record == "flash_target":
            target_type = _required_string(
                fields,
                "type",
                record=record,
            )

            policy = _required_string(
                fields,
                "policy",
                record=record,
            )

            name = _required_string(
                fields,
                "name",
                record=record,
            )

            canonical_name = _required_string(
                fields,
                "canonical",
                record=record,
            )

            raw_slot = _required_string(
                fields,
                "slot",
                record=record,
            )

            slot = (
                None
                if raw_slot == "-"
                else raw_slot
            )

            metadata_slot_raw = (
                _required_string(
                    fields,
                    "metadata_slot",
                    record=record,
                )
            )

            metadata_slot = (
                None
                if metadata_slot_raw == "-"
                else int(metadata_slot_raw)
            )

            targets.append(
                RecoveryDeviceFlashTarget(
                    target_type=target_type,
                    policy=policy,
                    name=name,
                    canonical_name=(
                        canonical_name
                    ),
                    slot=slot,
                    active=(
                        _required_boolean(
                            fields,
                            "active",
                            record=record,
                        )
                    ),
                    selectable=(
                        _required_boolean(
                            fields,
                            "selectable",
                            record=record,
                        )
                    ),
                    capacity_bytes=(
                        _required_integer(
                            fields,
                            "bytes",
                            record=record,
                        )
                    ),
                    allocated=(
                        _required_boolean(
                            fields,
                            "allocated",
                            record=record,
                        )
                    ),
                    metadata_slot=(
                        metadata_slot
                    ),
                    extents=(
                        _required_integer(
                            fields,
                            "extents",
                            record=record,
                        )
                    ),
                )
            )

    if lp_geometry is None:
        raise ValueError(
            "Recovery runtime report has no "
            "lp_geometry record"
        )

    if flash_summary is None:
        raise ValueError(
            "Recovery runtime report has no "
            "flash_targets record"
        )

    active_slot = _required_string(
        flash_summary,
        "active_slot",
        record="flash_targets",
    )

    return RecoveryDeviceState(
        active_slot=active_slot,
        super_found=(
            _required_boolean(
                lp_geometry,
                "super_found",
                record="lp_geometry",
            )
        ),
        lp_resolved=(
            _required_boolean(
                lp_geometry,
                "resolved",
                record="lp_geometry",
            )
        ),
        lp_authoritative_valid=(
            _required_boolean(
                lp_geometry,
                "authoritative_valid",
                record="lp_geometry",
            )
        ),
        virtual_ab=(
            _required_boolean(
                lp_geometry,
                "virtual_ab",
                record="lp_geometry",
            )
        ),
        flash_targets=tuple(
            targets
        ),
    )


__all__ = (
    "RECOVERY_RUNTIME_REPORT_PREFIX",
    "RecoveryDeviceFlashTarget",
    "RecoveryDeviceState",
    "parse_recovery_runtime_report",
)
