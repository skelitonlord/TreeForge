from __future__ import annotations

from dataclasses import asdict, dataclass
import re


class RepartitionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PartitionGeometry:
    name: str
    device: str
    number: int
    start_sector: int
    size_sectors: int

    @property
    def end_sector(self) -> int:
        return (
            self.start_sector
            + self.size_sectors
        )


@dataclass(frozen=True, slots=True)
class TangorproRepartitionProfile:
    name: str
    product: str
    disk: str
    sector_size_bytes: int
    alignment_bytes: int
    super: PartitionGeometry
    userdata: PartitionGeometry


@dataclass(frozen=True, slots=True)
class RepartitionPlan:
    direction: str

    profile: str
    product: str
    disk: str

    sector_size_bytes: int
    alignment_bytes: int

    requested_super_size_bytes: int
    realized_super_size_bytes: int
    realized_super_size_sectors: int

    current_super_start_sector: int
    current_super_size_sectors: int
    current_super_end_sector: int

    new_super_start_sector: int
    new_super_end_sector: int

    current_userdata_start_sector: int
    current_userdata_size_sectors: int
    current_userdata_end_sector: int

    new_userdata_start_sector: int
    new_userdata_size_sectors: int
    new_userdata_end_sector: int

    super_delta_bytes: int
    userdata_delta_bytes: int

    action: str
    userdata_action: str

    destructive: bool
    device_modified: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


TANGORPRO_PROFILE = TangorproRepartitionProfile(
    name="tangorpro-treeforge-ab-v1",
    product="tangorpro",
    disk="/dev/block/sda",
    sector_size_bytes=512,
    alignment_bytes=1024 * 1024,
    super=PartitionGeometry(
        name="super",
        device="/dev/block/sda25",
        number=25,
        start_sector=1_191_728,
        size_sectors=16_662_528,
    ),
    userdata=PartitionGeometry(
        name="userdata",
        device="/dev/block/sda26",
        number=26,
        start_sector=17_854_256,
        size_sectors=231_714_984,
    ),
)


_SIZE_RE = re.compile(
    r"^\s*"
    r"(?P<value>\d+(?:\.\d+)?)"
    r"\s*"
    r"(?P<unit>B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)"
    r"\s*$",
    re.IGNORECASE,
)


_UNIT_MULTIPLIERS = {
    "b": 1,
    "kb": 1_000,
    "mb": 1_000_000,
    "gb": 1_000_000_000,
    "tb": 1_000_000_000_000,
    "kib": 1024,
    "mib": 1024 ** 2,
    "gib": 1024 ** 3,
    "tib": 1024 ** 4,
}


def parse_size_bytes(
    value: str,
) -> int:
    match = _SIZE_RE.fullmatch(
        value
    )

    if match is None:
        raise RepartitionError(
            "Invalid size. Use a value such as "
            "'10GB', '12GB', or '10GiB'."
        )

    number_text = match.group(
        "value"
    )

    unit = match.group(
        "unit"
    ).lower()

    whole, dot, fraction = (
        number_text.partition(".")
    )

    numerator = int(
        whole
    )

    denominator = 1

    if dot:
        denominator = (
            10 ** len(fraction)
        )

        numerator = (
            numerator * denominator
            + int(fraction)
        )

    multiplier = (
        _UNIT_MULTIPLIERS[
            unit
        ]
    )

    result = (
        numerator * multiplier
        + denominator - 1
    ) // denominator

    if result <= 0:
        raise RepartitionError(
            "Requested super size must "
            "be greater than zero."
        )

    return result


def _align_up(
    value: int,
    alignment: int,
) -> int:
    return (
        (value + alignment - 1)
        // alignment
        * alignment
    )


def _profile_invariants(
    profile: TangorproRepartitionProfile,
) -> None:
    if (
        profile.alignment_bytes
        % profile.sector_size_bytes
        != 0
    ):
        raise RepartitionError(
            "Profile alignment is not "
            "sector aligned."
        )

    if (
        profile.super.end_sector
        != profile.userdata.start_sector
    ):
        raise RepartitionError(
            "Tangorpro profile invariant failed: "
            "super and userdata are not adjacent."
        )


def _treeforge_geometry(
    *,
    requested_super_size: str,
    profile: TangorproRepartitionProfile,
) -> tuple[
    int,
    int,
    int,
    int,
]:
    _profile_invariants(
        profile
    )

    requested_bytes = (
        parse_size_bytes(
            requested_super_size
        )
    )

    realized_bytes = _align_up(
        requested_bytes,
        profile.alignment_bytes,
    )

    if (
        realized_bytes
        % profile.sector_size_bytes
        != 0
    ):
        raise RepartitionError(
            "Realized super size is not "
            "sector aligned."
        )

    realized_sectors = (
        realized_bytes
        // profile.sector_size_bytes
    )

    new_super_end = (
        profile.super.start_sector
        + realized_sectors
    )

    new_userdata_size = (
        profile.userdata.end_sector
        - new_super_end
    )

    minimum_userdata_sectors = (
        profile.alignment_bytes
        // profile.sector_size_bytes
    )

    if (
        new_userdata_size
        < minimum_userdata_sectors
    ):
        raise RepartitionError(
            "Requested super size would leave "
            "less than one alignment unit "
            "for userdata."
        )

    return (
        requested_bytes,
        realized_bytes,
        realized_sectors,
        new_userdata_size,
    )


def build_repartition_plan(
    *,
    requested_super_size: str = "10GB",
    profile: TangorproRepartitionProfile = TANGORPRO_PROFILE,
) -> RepartitionPlan:
    (
        requested_bytes,
        realized_bytes,
        realized_sectors,
        new_userdata_size,
    ) = _treeforge_geometry(
        requested_super_size=requested_super_size,
        profile=profile,
    )

    sector_size = (
        profile.sector_size_bytes
    )

    new_super_start = (
        profile.super.start_sector
    )

    new_super_end = (
        new_super_start
        + realized_sectors
    )

    userdata_end = (
        profile.userdata.end_sector
    )

    new_userdata_start = (
        new_super_end
    )

    current_super_bytes = (
        profile.super.size_sectors
        * sector_size
    )

    current_userdata_bytes = (
        profile.userdata.size_sectors
        * sector_size
    )

    new_userdata_bytes = (
        new_userdata_size
        * sector_size
    )

    super_delta = (
        realized_bytes
        - current_super_bytes
    )

    userdata_delta = (
        new_userdata_bytes
        - current_userdata_bytes
    )

    if super_delta > 0:
        action = "GROW"

    elif super_delta < 0:
        action = "SHRINK"

    else:
        action = "UNCHANGED"

    return RepartitionPlan(
        direction="forward",
        profile=profile.name,
        product=profile.product,
        disk=profile.disk,
        sector_size_bytes=sector_size,
        alignment_bytes=profile.alignment_bytes,
        requested_super_size_bytes=requested_bytes,
        realized_super_size_bytes=realized_bytes,
        realized_super_size_sectors=realized_sectors,
        current_super_start_sector=profile.super.start_sector,
        current_super_size_sectors=profile.super.size_sectors,
        current_super_end_sector=profile.super.end_sector,
        new_super_start_sector=new_super_start,
        new_super_end_sector=new_super_end,
        current_userdata_start_sector=profile.userdata.start_sector,
        current_userdata_size_sectors=profile.userdata.size_sectors,
        current_userdata_end_sector=userdata_end,
        new_userdata_start_sector=new_userdata_start,
        new_userdata_size_sectors=new_userdata_size,
        new_userdata_end_sector=userdata_end,
        super_delta_bytes=super_delta,
        userdata_delta_bytes=userdata_delta,
        action=action,
        userdata_action="RECREATE",
        destructive=True,
        device_modified=False,
    )


def build_undo_plan(
    *,
    from_super_size: str = "10GB",
    profile: TangorproRepartitionProfile = TANGORPRO_PROFILE,
) -> RepartitionPlan:
    (
        requested_bytes,
        realized_bytes,
        realized_sectors,
        treeforge_userdata_size,
    ) = _treeforge_geometry(
        requested_super_size=from_super_size,
        profile=profile,
    )

    sector_size = (
        profile.sector_size_bytes
    )

    treeforge_super_end = (
        profile.super.start_sector
        + realized_sectors
    )

    stock_super_bytes = (
        profile.super.size_sectors
        * sector_size
    )

    treeforge_userdata_bytes = (
        treeforge_userdata_size
        * sector_size
    )

    stock_userdata_bytes = (
        profile.userdata.size_sectors
        * sector_size
    )

    return RepartitionPlan(
        direction="undo",
        profile=profile.name,
        product=profile.product,
        disk=profile.disk,
        sector_size_bytes=sector_size,
        alignment_bytes=profile.alignment_bytes,
        requested_super_size_bytes=requested_bytes,
        realized_super_size_bytes=stock_super_bytes,
        realized_super_size_sectors=profile.super.size_sectors,
        current_super_start_sector=profile.super.start_sector,
        current_super_size_sectors=realized_sectors,
        current_super_end_sector=treeforge_super_end,
        new_super_start_sector=profile.super.start_sector,
        new_super_end_sector=profile.super.end_sector,
        current_userdata_start_sector=treeforge_super_end,
        current_userdata_size_sectors=treeforge_userdata_size,
        current_userdata_end_sector=profile.userdata.end_sector,
        new_userdata_start_sector=profile.userdata.start_sector,
        new_userdata_size_sectors=profile.userdata.size_sectors,
        new_userdata_end_sector=profile.userdata.end_sector,
        super_delta_bytes=(
            stock_super_bytes
            - realized_bytes
        ),
        userdata_delta_bytes=(
            stock_userdata_bytes
            - treeforge_userdata_bytes
        ),
        action="SHRINK",
        userdata_action="RECREATE",
        destructive=True,
        device_modified=False,
    )
