from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidUniverseKernelCommandLineArgumentKind(
    StrEnum
):
    ASSIGNMENT = "assignment"
    FLAG = "flag"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelCommandLineArgument:
    """
    One ordered semantic kernel command-line argument.

    ``raw`` preserves the exact lexical token, including any quoting or
    escaping present in the source command line.

    ``key`` and ``value`` contain the interpreted token meaning. Repeated
    keys are intentionally permitted and order remains significant.
    """

    index: int
    raw: str

    kind: (
        AndroidUniverseKernelCommandLineArgumentKind
    )

    key: str
    value: str | None

    def __post_init__(
        self,
    ) -> None:
        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
        ):
            raise TypeError(
                "index must be an int"
            )

        if self.index < 0:
            raise ValueError(
                "index cannot be negative"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not self.raw:
            raise ValueError(
                "raw cannot be empty"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseKernelCommandLineArgumentKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidUniverseKernelCommandLineArgumentKind"
            )

        if not isinstance(
            self.key,
            str,
        ):
            raise TypeError(
                "key must be a string"
            )

        if not self.key:
            raise ValueError(
                "key cannot be empty"
            )

        if (
            self.value is not None
            and not isinstance(
                self.value,
                str,
            )
        ):
            raise TypeError(
                "value must be a string or None"
            )

        if (
            self.kind
            == AndroidUniverseKernelCommandLineArgumentKind.FLAG
            and self.value is not None
        ):
            raise ValueError(
                "flag arguments cannot have a value"
            )

        if (
            self.kind
            == AndroidUniverseKernelCommandLineArgumentKind.ASSIGNMENT
            and self.value is None
        ):
            raise ValueError(
                "assignment arguments require a value"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelCommandLineSemantics:
    """
    Semantic interpretation of one literal kernel command line.

    The complete literal source remains authoritative. ``arguments`` adds
    ordered assignment/flag semantics without collapsing repetition.
    """

    literal: str

    arguments: tuple[
        AndroidUniverseKernelCommandLineArgument,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.literal,
            str,
        ):
            raise TypeError(
                "literal must be a string"
            )

        if not isinstance(
            self.arguments,
            tuple,
        ):
            raise TypeError(
                "arguments must be a tuple"
            )

        if not all(
            isinstance(
                argument,
                AndroidUniverseKernelCommandLineArgument,
            )
            for argument in self.arguments
        ):
            raise TypeError(
                "arguments must contain only "
                "AndroidUniverseKernelCommandLineArgument instances"
            )

        expected_indexes = tuple(
            range(
                len(
                    self.arguments
                )
            )
        )

        actual_indexes = tuple(
            argument.index
            for argument in self.arguments
        )

        if (
            actual_indexes
            != expected_indexes
        ):
            raise ValueError(
                "arguments must retain contiguous source order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootAndroidVersion:
    """
    Android OS-version evidence encoded in a boot-family image header.

    The encoded integer and decoded components are both retained. A value of
    zero remains meaningful evidence and must not be treated as absent.
    """

    encoded: int

    major: int
    minor: int
    patch: int

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "encoded",
            "major",
            "minor",
            "patch",
        ):
            value = getattr(
                self,
                field_name,
            )

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
class AndroidUniverseBootconfigDeclaration:
    """
    One ordered bootconfig declaration from canonical Parsing.

    The exact Parsing entry is retained so source order, lexical identity,
    line number, raw spelling, and provenance remain canonical.
    """

    index: int
    source: object

    def __post_init__(
        self,
    ) -> None:
        from treeforge.android.parsing.boot.bootconfig import (
            AndroidBootconfigEntry,
        )

        if (
            isinstance(
                self.index,
                bool,
            )
            or not isinstance(
                self.index,
                int,
            )
        ):
            raise TypeError(
                "index must be an int"
            )

        if self.index < 0:
            raise ValueError(
                "index cannot be negative"
            )

        if not isinstance(
            self.source,
            AndroidBootconfigEntry,
        ):
            raise TypeError(
                "source must be an AndroidBootconfigEntry"
            )

    @property
    def key(
        self,
    ) -> str:
        return self.source.key

    @property
    def value(
        self,
    ) -> str:
        return self.source.value

    @property
    def line_number(
        self,
    ) -> int:
        return self.source.line_number

    @property
    def raw(
        self,
    ) -> str:
        return self.source.raw

    @property
    def scalar_value(
        self,
    ) -> str:
        """
        Return the semantic scalar represented by this exact declaration.

        Bootconfig Parsing preserves literal RHS spelling. Universe removes
        one matching outer quote pair for scalar consumers while retaining
        the exact Parsing declaration through ``source``.
        """

        value = self.value.strip()

        if (
            len(
                value
            ) >= 2
            and value[0] == value[-1]
            and value[0]
            in {
                "'",
                '"',
            }
        ):
            return value[
                1:-1
            ]

        return value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootDeviceSelection:
    """
    One boot-device declaration interpreted from bootconfig.

    ``source`` retains the exact canonical bootconfig declaration. ``devices``
    contains the ordered device identifiers represented by that declaration.
    """

    source: AndroidUniverseBootconfigDeclaration

    devices: tuple[
        str,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseBootconfigDeclaration,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseBootconfigDeclaration"
            )

        if self.source.key not in (
            "androidboot.boot_device",
            "androidboot.boot_devices",
        ):
            raise ValueError(
                "boot-device selection source must be "
                "androidboot.boot_device or "
                "androidboot.boot_devices"
            )

        if not isinstance(
            self.devices,
            tuple,
        ):
            raise TypeError(
                "devices must be a tuple"
            )

        if not self.devices:
            raise ValueError(
                "devices must not be empty"
            )

        if not all(
            isinstance(
                device,
                str,
            )
            and device
            for device
            in self.devices
        ):
            raise ValueError(
                "devices must contain non-empty strings"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseFirstStageModuleLoadingPolicy:
    """
    First-stage kernel-module loading policy derived from bootconfig.
    """

    source: AndroidUniverseBootconfigDeclaration

    parallel: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidUniverseBootconfigDeclaration,
        ):
            raise TypeError(
                "source must be an "
                "AndroidUniverseBootconfigDeclaration"
            )

        if (
            self.source.key
            != "androidboot.load_modules_parallel"
        ):
            raise ValueError(
                "module-loading policy source must be "
                "androidboot.load_modules_parallel"
            )

        if not isinstance(
            self.parallel,
            bool,
        ):
            raise TypeError(
                "parallel must be a bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootconfigSemantics:
    """
    Ordered Universe semantic surface for parsed vendor_boot bootconfig.

    Universe consumes canonical Parsing output and never re-reads or
    reparses the extracted bootconfig payload.
    """

    declarations: tuple[
        AndroidUniverseBootconfigDeclaration,
        ...,
    ] = ()

    unparsed_line_count: int = 0


    boot_device_selections: tuple[
        AndroidUniverseBootDeviceSelection,
        ...,
    ] = ()

    module_loading_policies: tuple[
        AndroidUniverseFirstStageModuleLoadingPolicy,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.declarations,
            tuple,
        ):
            raise TypeError(
                "declarations must be a tuple"
            )

        if not all(
            isinstance(
                declaration,
                AndroidUniverseBootconfigDeclaration,
            )
            for declaration
            in self.declarations
        ):
            raise TypeError(
                "declarations must contain only "
                "AndroidUniverseBootconfigDeclaration instances"
            )

        indexes = tuple(
            declaration.index
            for declaration
            in self.declarations
        )

        if indexes != tuple(
            range(
                len(
                    self.declarations
                )
            )
        ):
            raise ValueError(
                "declarations must retain contiguous source order"
            )

        if (
            isinstance(
                self.unparsed_line_count,
                bool,
            )
            or not isinstance(
                self.unparsed_line_count,
                int,
            )
        ):
            raise TypeError(
                "unparsed_line_count must be an int"
            )

        if self.unparsed_line_count < 0:
            raise ValueError(
                "unparsed_line_count cannot be negative"
            )

        if not isinstance(
            self.boot_device_selections,
            tuple,
        ):
            raise TypeError(
                "boot_device_selections must be a tuple"
            )

        if not all(
            isinstance(
                selection,
                AndroidUniverseBootDeviceSelection,
            )
            for selection
            in self.boot_device_selections
        ):
            raise TypeError(
                "boot_device_selections must contain only "
                "AndroidUniverseBootDeviceSelection instances"
            )

        if not isinstance(
            self.module_loading_policies,
            tuple,
        ):
            raise TypeError(
                "module_loading_policies must be a tuple"
            )

        if not all(
            isinstance(
                policy,
                AndroidUniverseFirstStageModuleLoadingPolicy,
            )
            for policy
            in self.module_loading_policies
        ):
            raise TypeError(
                "module_loading_policies must contain only "
                "AndroidUniverseFirstStageModuleLoadingPolicy "
                "instances"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootSemantics:
    """
    Canonical semantics provided by boot.img.
    """

    header_version: int

    android_version: (
        AndroidUniverseBootAndroidVersion
    )

    boot_name: str

    command_line: (
        AndroidUniverseKernelCommandLineSemantics
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVendorBootSemantics:
    """
    Canonical semantics provided by vendor_boot.img.
    """

    header_version: int

    boot_name: str

    command_line: (
        AndroidUniverseKernelCommandLineSemantics
    )
    bootconfig: (
        AndroidUniverseBootconfigSemantics
        | None
    ) = None
