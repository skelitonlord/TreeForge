from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BootContainerKind(
    Enum,
):
    """
    Physical Android boot-family container identity.

    These values describe container structure only. They do not represent
    Android-version policy or higher-level boot semantics.
    """

    BOOT = "boot"
    INIT_BOOT = "init_boot"
    RECOVERY = "recovery"
    PVMFW = "pvmfw"
    VENDOR_BOOT = "vendor_boot"


@dataclass(
    frozen=True,
    slots=True,
)
class BootComponentLayout:
    """
    Physical location of one boot-container component.
    """

    offset: int
    size: int

    def __post_init__(
        self,
    ) -> None:
        self._validate_int(
            self.offset,
            field_name="offset",
        )

        self._validate_int(
            self.size,
            field_name="size",
        )

    @staticmethod
    def _validate_int(
        value: int,
        *,
        field_name: str,
    ) -> None:
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
                f"{field_name} must be an int"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative"
            )

    @property
    def end(
        self,
    ) -> int:
        return (
            self.offset
            + self.size
        )

    @property
    def present(
        self,
    ) -> bool:
        return self.size > 0


@dataclass(
    frozen=True,
    slots=True,
)
class BootImageStructure:
    """
    Immutable physical structure of one ANDROID! boot-family image.

    This model contains only facts required to locate and extract physical
    payloads. Higher-level Android meaning belongs to later layers.

    boot.img, init_boot.img, recovery.img, and other semantically distinct
    artifacts such as pvmfw.img may use the ANDROID! container family.
    ``kind`` retains the semantic identity supplied by
    upstream Discovery/Layout while ``header_version`` selects the exact
    physical structure.
    """

    kind: BootContainerKind

    header_version: int
    header_size: int
    page_size: int

    os_version_raw: int
    cmdline: str

    kernel: BootComponentLayout
    ramdisk: BootComponentLayout
    second: BootComponentLayout
    recovery_dtbo: BootComponentLayout
    dtb: BootComponentLayout
    boot_signature: BootComponentLayout
    boot_signature_declared_size: int

    image_size: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            BootContainerKind,
        ):
            raise TypeError(
                "kind must be a BootContainerKind"
            )

        for (
            field_name,
            value,
        ) in (
            (
                "header_version",
                self.header_version,
            ),
            (
                "header_size",
                self.header_size,
            ),
            (
                "page_size",
                self.page_size,
            ),
            (
                "os_version_raw",
                self.os_version_raw,
            ),
            (
                "boot_signature_declared_size",
                self.boot_signature_declared_size,
            ),
            (
                "image_size",
                self.image_size,
            ),
        ):
            self._validate_int(
                value,
                field_name=field_name,
            )

        if not isinstance(
            self.cmdline,
            str,
        ):
            raise TypeError(
                "cmdline must be a string"
            )

        for (
            field_name,
            component,
        ) in (
            (
                "kernel",
                self.kernel,
            ),
            (
                "ramdisk",
                self.ramdisk,
            ),
            (
                "second",
                self.second,
            ),
            (
                "recovery_dtbo",
                self.recovery_dtbo,
            ),
            (
                "dtb",
                self.dtb,
            ),
            (
                "boot_signature",
                self.boot_signature,
            ),
        ):
            if not isinstance(
                component,
                BootComponentLayout,
            ):
                raise TypeError(
                    f"{field_name} must be a "
                    "BootComponentLayout"
                )

        if self.page_size <= 0:
            raise ValueError(
                "page_size must be greater than zero"
            )

        if self.image_size <= 0:
            raise ValueError(
                "image_size must be greater than zero"
            )

        self._validate_component_ranges()

    def _validate_component_ranges(
        self,
    ) -> None:
        for (
            field_name,
            component,
        ) in (
            (
                "kernel",
                self.kernel,
            ),
            (
                "ramdisk",
                self.ramdisk,
            ),
            (
                "second",
                self.second,
            ),
            (
                "recovery_dtbo",
                self.recovery_dtbo,
            ),
            (
                "dtb",
                self.dtb,
            ),
            (
                "boot_signature",
                self.boot_signature,
            ),
        ):
            if (
                component.present
                and component.end
                > self.image_size
            ):
                raise ValueError(
                    f"{field_name} extends beyond "
                    "boot image: "
                    f"offset={component.offset}, "
                    f"size={component.size}, "
                    f"end={component.end}, "
                    f"image_size={self.image_size}"
                )

    @staticmethod
    def _validate_int(
        value: int,
        *,
        field_name: str,
    ) -> None:
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
                f"{field_name} must be an int"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class VendorRamdiskTableEntry:
    """
    Literal physical vendor_boot v4 ramdisk-table entry.

    The table supplies physical fragment location plus literal type/name and
    board-id fields. Extraction preserves these values without deciding which
    fragment is applicable to a particular runtime device state.
    """

    index: int
    ramdisk_size: int
    ramdisk_offset: int
    ramdisk_type: int
    ramdisk_name: str
    board_id: tuple[int, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("index", self.index),
            ("ramdisk_size", self.ramdisk_size),
            ("ramdisk_offset", self.ramdisk_offset),
            ("ramdisk_type", self.ramdisk_type),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    f"{name} must be an int"
                )

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if not isinstance(
            self.ramdisk_name,
            str,
        ):
            raise TypeError(
                "ramdisk_name must be a string"
            )

        if not isinstance(
            self.board_id,
            tuple,
        ):
            raise TypeError(
                "board_id must be a tuple"
            )

        if len(self.board_id) != 16:
            raise ValueError(
                "board_id must contain exactly 16 words"
            )

        for value in self.board_id:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise TypeError(
                    "board_id values must be ints"
                )

            if value < 0:
                raise ValueError(
                    "board_id values cannot be negative"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class VendorBootImageStructure:
    """
    Immutable physical structure of one VNDRBOOT image.

    Only container facts required for Extraction are represented here.

    Vendor ramdisk-table entry interpretation and bootconfig semantic
    interpretation remain deferred. The physical table/bootconfig regions
    may still be retained when required without interpreting their meaning.
    """

    header_version: int
    header_size: int
    page_size: int

    kernel_addr: int
    ramdisk_addr: int
    tags_addr: int
    dtb_addr: int

    cmdline: str
    name: str

    vendor_ramdisk: BootComponentLayout
    dtb: BootComponentLayout

    vendor_ramdisk_table: BootComponentLayout
    bootconfig: BootComponentLayout

    vendor_ramdisk_table_entry_num: int
    vendor_ramdisk_table_entry_size: int
    vendor_ramdisk_table_entries: tuple[
        VendorRamdiskTableEntry,
        ...,
    ]

    image_size: int

    def __post_init__(
        self,
    ) -> None:
        for (
            field_name,
            value,
        ) in (
            (
                "header_version",
                self.header_version,
            ),
            (
                "header_size",
                self.header_size,
            ),
            (
                "page_size",
                self.page_size,
            ),
            (
                "kernel_addr",
                self.kernel_addr,
            ),
            (
                "ramdisk_addr",
                self.ramdisk_addr,
            ),
            (
                "tags_addr",
                self.tags_addr,
            ),
            (
                "dtb_addr",
                self.dtb_addr,
            ),
            (
                "vendor_ramdisk_table_entry_num",
                self.vendor_ramdisk_table_entry_num,
            ),
            (
                "vendor_ramdisk_table_entry_size",
                self.vendor_ramdisk_table_entry_size,
            ),
            (
                "image_size",
                self.image_size,
            ),
        ):
            self._validate_int(
                value,
                field_name=field_name,
            )

        if not isinstance(
            self.cmdline,
            str,
        ):
            raise TypeError(
                "cmdline must be a string"
            )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not isinstance(
            self.vendor_ramdisk_table_entries,
            tuple,
        ):
            raise TypeError(
                "vendor_ramdisk_table_entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                VendorRamdiskTableEntry,
            )
            for entry
            in self.vendor_ramdisk_table_entries
        ):
            raise TypeError(
                "vendor_ramdisk_table_entries must contain "
                "VendorRamdiskTableEntry instances"
            )

        if (
            len(
                self.vendor_ramdisk_table_entries
            )
            != self.vendor_ramdisk_table_entry_num
        ):
            raise ValueError(
                "vendor ramdisk table entry count does not match "
                "decoded entries"
            )

        for (
            field_name,
            component,
        ) in (
            (
                "vendor_ramdisk",
                self.vendor_ramdisk,
            ),
            (
                "dtb",
                self.dtb,
            ),
            (
                "vendor_ramdisk_table",
                self.vendor_ramdisk_table,
            ),
            (
                "bootconfig",
                self.bootconfig,
            ),
        ):
            if not isinstance(
                component,
                BootComponentLayout,
            ):
                raise TypeError(
                    f"{field_name} must be a "
                    "BootComponentLayout"
                )

        if self.page_size <= 0:
            raise ValueError(
                "page_size must be greater than zero"
            )

        if self.image_size <= 0:
            raise ValueError(
                "image_size must be greater than zero"
            )

        if (
            self.header_version
            not in (
                3,
                4,
            )
        ):
            raise ValueError(
                "VendorBootImageStructure currently "
                "supports header versions 3 and 4"
            )

        if (
            self.header_version == 3
            and (
                self.vendor_ramdisk_table.present
                or self.bootconfig.present
                or self.vendor_ramdisk_table_entry_num
                or self.vendor_ramdisk_table_entry_size
            )
        ):
            raise ValueError(
                "vendor_boot v3 cannot contain "
                "v4 ramdisk-table or bootconfig state"
            )

        self._validate_component_ranges()

    def _validate_component_ranges(
        self,
    ) -> None:
        for (
            field_name,
            component,
        ) in (
            (
                "vendor_ramdisk",
                self.vendor_ramdisk,
            ),
            (
                "dtb",
                self.dtb,
            ),
            (
                "vendor_ramdisk_table",
                self.vendor_ramdisk_table,
            ),
            (
                "bootconfig",
                self.bootconfig,
            ),
        ):
            if (
                component.present
                and component.end
                > self.image_size
            ):
                raise ValueError(
                    f"{field_name} extends beyond "
                    "vendor_boot image: "
                    f"offset={component.offset}, "
                    f"size={component.size}, "
                    f"end={component.end}, "
                    f"image_size={self.image_size}"
                )

    @staticmethod
    def _validate_int(
        value: int,
        *,
        field_name: str,
    ) -> None:
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
                f"{field_name} must be an int"
            )

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative"
            )