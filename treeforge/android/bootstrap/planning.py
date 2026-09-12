from __future__ import annotations

import lzma

from dataclasses import dataclass, replace
from enum import Enum

from treeforge.android.parsing.result import (
    AndroidParsingResult,
)
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.boot_image.interpretation import (
    AndroidBootImageInterpreter,
)
from treeforge.android.boot_image.models import (
    AndroidBootImageCpioEntryInterpretation,
    AndroidBootImageCpioEntryKind,
    AndroidBootImageRamdiskInterpretation,
)
from treeforge.android.parsing.elf.model import (
    ParsedAndroidElf,
)
from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidInitSource,
    ParsedAndroidSelinuxSource,
    ParsedAndroidVintfSource,
)
from treeforge.android.parsing.init.model import (
    AndroidInitImport,
    AndroidInitService,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)
from treeforge.android.boot_image.result import (
    AndroidBootImageInterpretationResult,
)

from treeforge.android.bootstrap.result import (
    AndroidBootstrapIntakeResult,
)


class AndroidBootstrapEnvironmentRequirementKind(
    StrEnum
):
    """
    Bootstrap-visible role of one exact canonical ramdisk entry.

    This is not yet a physical inclusion decision.
    """

    INIT_BINARY = "init_binary"
    INIT_CONFIGURATION = "init_configuration"
    FSTAB_CONFIGURATION = "fstab_configuration"
    UEVENTD_CONFIGURATION = "ueventd_configuration"

    KERNEL_MODULE = "kernel_module"
    KERNEL_MODULE_CONFIGURATION = (
        "kernel_module_configuration"
    )

    EXECUTABLE = "executable"
    SHARED_LIBRARY = "shared_library"

    STRUCTURAL = "structural"
    RESOURCE = "resource"
    UNCLASSIFIED = "unclassified"


class AndroidBootstrapEnvironmentRequirementDisposition(
    StrEnum
):
    """
    Environment Planning disposition.

    REQUIRED_CANDIDATE:
      Strong canonical evidence that this role participates in a
      bootstrap-capable environment. Exact inclusion is still subject
      to later closure and applicability checks.

    AVAILABLE_CANDIDATE:
      Canonical content that may be required by dependency/runtime
      closure, but is not selected merely because it exists.

    PRESERVED_EVIDENCE:
      Conserved canonical content with no current reason to include it.

    UNRESOLVED:
      Canonical evidence whose role cannot yet be safely classified.
    """

    REQUIRED_CANDIDATE = "required_candidate"
    AVAILABLE_CANDIDATE = "available_candidate"
    PRESERVED_EVIDENCE = "preserved_evidence"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentRequirement:
    """
    One losslessly-accounted canonical ramdisk entry at the Bootstrap
    Environment Planning boundary.
    """

    ramdisk_index: int
    entry: AndroidBootImageCpioEntryInterpretation
    kind: AndroidBootstrapEnvironmentRequirementKind
    disposition: (
        AndroidBootstrapEnvironmentRequirementDisposition
    )

    def __post_init__(self) -> None:
        if (
            isinstance(self.ramdisk_index, bool)
            or not isinstance(
                self.ramdisk_index,
                int,
            )
        ):
            raise TypeError(
                "ramdisk_index must be an int"
            )

        if self.ramdisk_index < 0:
            raise ValueError(
                "ramdisk_index cannot be negative"
            )

        if not isinstance(
            self.entry,
            AndroidBootImageCpioEntryInterpretation,
        ):
            raise TypeError(
                "entry must be an "
                "AndroidBootImageCpioEntryInterpretation"
            )

        if not isinstance(
            self.kind,
            AndroidBootstrapEnvironmentRequirementKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidBootstrapEnvironmentRequirementKind"
            )

        if not isinstance(
            self.disposition,
            AndroidBootstrapEnvironmentRequirementDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootstrapEnvironmentRequirementDisposition"
            )

        if (
            self.kind
            is AndroidBootstrapEnvironmentRequirementKind
            .UNCLASSIFIED
            and self.disposition
            is not AndroidBootstrapEnvironmentRequirementDisposition
            .UNRESOLVED
        ):
            raise ValueError(
                "unclassified Bootstrap environment evidence "
                "must remain unresolved"
            )


class AndroidBootstrapRuntimeSupportResolution(
    StrEnum
):
    """
    Resolution of one canonical Bootstrap runtime-support source
    against exact CPIO entries in one exact ramdisk.
    """

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapVintfBinding:
    """
    Exact selected-ramdisk binding for one canonical Parsing VINTF source.
    """

    source: ParsedAndroidVintfSource
    resolution: AndroidBootstrapRuntimeSupportResolution

    entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    ) = None

    candidates: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidVintfSource,
        ):
            raise TypeError(
                "source must be a ParsedAndroidVintfSource"
            )

        if not isinstance(
            self.resolution,
            AndroidBootstrapRuntimeSupportResolution,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidBootstrapRuntimeSupportResolution"
            )

        if (
            not isinstance(
                self.candidates,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    AndroidBootImageCpioEntryInterpretation,
                )
                for value
                in self.candidates
            )
        ):
            raise TypeError(
                "VINTF candidates must contain only exact "
                "CPIO interpretations"
            )

        if (
            self.resolution
            is AndroidBootstrapRuntimeSupportResolution.RESOLVED
        ):
            if not isinstance(
                self.entry,
                AndroidBootImageCpioEntryInterpretation,
            ):
                raise ValueError(
                    "resolved VINTF binding must retain one exact "
                    "CPIO entry"
                )

            if self.candidates != (
                self.entry,
            ):
                raise ValueError(
                    "resolved VINTF binding must retain exactly "
                    "one candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapRuntimeSupportResolution.UNRESOLVED
        ):
            if (
                self.entry is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved VINTF binding cannot retain candidates"
                )

        else:
            if self.entry is not None:
                raise ValueError(
                    "ambiguous VINTF binding cannot select an entry"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous VINTF binding must retain at least "
                    "two candidates"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapSelinuxBinding:
    """
    Exact selected-ramdisk binding for one canonical Parsing SELinux source.
    """

    source: ParsedAndroidSelinuxSource
    resolution: AndroidBootstrapRuntimeSupportResolution

    entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    ) = None

    candidates: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidSelinuxSource,
        ):
            raise TypeError(
                "source must be a ParsedAndroidSelinuxSource"
            )

        if not isinstance(
            self.resolution,
            AndroidBootstrapRuntimeSupportResolution,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidBootstrapRuntimeSupportResolution"
            )

        if (
            not isinstance(
                self.candidates,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    AndroidBootImageCpioEntryInterpretation,
                )
                for value
                in self.candidates
            )
        ):
            raise TypeError(
                "SELinux candidates must contain only exact "
                "CPIO interpretations"
            )

        if (
            self.resolution
            is AndroidBootstrapRuntimeSupportResolution.RESOLVED
        ):
            if not isinstance(
                self.entry,
                AndroidBootImageCpioEntryInterpretation,
            ):
                raise ValueError(
                    "resolved SELinux binding must retain one exact "
                    "CPIO entry"
                )

            if self.candidates != (
                self.entry,
            ):
                raise ValueError(
                    "resolved SELinux binding must retain exactly "
                    "one candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapRuntimeSupportResolution.UNRESOLVED
        ):
            if (
                self.entry is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved SELinux binding cannot retain candidates"
                )

        else:
            if self.entry is not None:
                raise ValueError(
                    "ambiguous SELinux binding cannot select an entry"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous SELinux binding must retain at least "
                    "two candidates"
                )


class AndroidBootstrapEnvironmentElfResolution(
    StrEnum
):
    """
    Resolution of one canonical ramdisk-local ELF against exact CPIO paths.

    Resolution is constrained to one exact ramdisk filesystem source.
    """

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentSourceBinding:
    """
    Exact CPIO -> canonical AndroidModelSource association already proven by
    Boot Image interpretation.
    """

    entry: AndroidBootImageCpioEntryInterpretation
    source: AndroidModelSource

    def __post_init__(self) -> None:
        if not isinstance(
            self.entry,
            AndroidBootImageCpioEntryInterpretation,
        ):
            raise TypeError(
                "entry must be an "
                "AndroidBootImageCpioEntryInterpretation"
            )

        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            self.entry.associated_source
            is not self.source
        ):
            raise ValueError(
                "Bootstrap source binding must preserve exact "
                "Boot Image associated-source identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentElfBinding:
    """
    Resolution of one exact canonical ParsedAndroidElf to CPIO evidence in
    the same exact ramdisk filesystem.

    No linker namespace or provider semantics are inferred here.
    """

    elf: ParsedAndroidElf
    resolution: AndroidBootstrapEnvironmentElfResolution

    entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    ) = None

    candidates: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "elf must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.resolution,
            AndroidBootstrapEnvironmentElfResolution,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidBootstrapEnvironmentElfResolution"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if not all(
            isinstance(
                candidate,
                AndroidBootImageCpioEntryInterpretation,
            )
            for candidate
            in self.candidates
        ):
            raise TypeError(
                "candidates must contain only "
                "AndroidBootImageCpioEntryInterpretation objects"
            )

        if (
            self.resolution
            is AndroidBootstrapEnvironmentElfResolution.RESOLVED
        ):
            if not isinstance(
                self.entry,
                AndroidBootImageCpioEntryInterpretation,
            ):
                raise ValueError(
                    "resolved ELF binding must retain its exact CPIO entry"
                )

            if self.candidates != (
                self.entry,
            ):
                raise ValueError(
                    "resolved ELF binding must retain exactly "
                    "one candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapEnvironmentElfResolution.UNRESOLVED
        ):
            if self.entry is not None:
                raise ValueError(
                    "unresolved ELF binding cannot select a CPIO entry"
                )

            if self.candidates:
                raise ValueError(
                    "unresolved ELF binding cannot retain candidates"
                )

        else:
            if self.entry is not None:
                raise ValueError(
                    "ambiguous ELF binding cannot select a CPIO entry"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous ELF binding must retain at least "
                    "two CPIO candidates"
                )


class AndroidBootstrapElfDependencyKind(
    StrEnum
):
    INTERPRETER = "interpreter"
    NEEDED = "needed"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapElfDependencyResolution:
    """
    One Bootstrap-local ELF dependency edge.

    Interpreter dependencies resolve by exact canonical Android path.

    DT_NEEDED dependencies resolve first by SONAME and, when duplicate
    providers exist, by exact canonical path-domain affinity. No arbitrary
    provider ordering is used.
    """

    owner: ParsedAndroidElf
    kind: AndroidBootstrapElfDependencyKind
    name: str

    resolution: AndroidBootstrapEnvironmentElfResolution

    provider: (
        AndroidBootstrapEnvironmentElfBinding
        | None
    ) = None

    candidates: tuple[
        AndroidBootstrapEnvironmentElfBinding,
        ...,
    ] = ()

    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.owner,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "owner must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.kind,
            AndroidBootstrapElfDependencyKind,
        ):
            raise TypeError(
                "kind must be an AndroidBootstrapElfDependencyKind"
            )

        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "dependency name must be a non-empty string"
            )

        if not isinstance(
            self.resolution,
            AndroidBootstrapEnvironmentElfResolution,
        ):
            raise TypeError(
                "resolution must be an "
                "AndroidBootstrapEnvironmentElfResolution"
            )

        if (
            not isinstance(
                self.candidates,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    AndroidBootstrapEnvironmentElfBinding,
                )
                for value
                in self.candidates
            )
        ):
            raise TypeError(
                "candidates must contain only ELF bindings"
            )

        if (
            self.resolution
            is AndroidBootstrapEnvironmentElfResolution.RESOLVED
        ):
            if self.provider is None:
                raise ValueError(
                    "resolved dependency must retain a provider"
                )

            if self.candidates != (
                self.provider,
            ):
                raise ValueError(
                    "resolved dependency must retain exactly "
                    "one selected candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapEnvironmentElfResolution.UNRESOLVED
        ):
            if (
                self.provider is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved dependency cannot retain providers"
                )

            if self.reason is None:
                raise ValueError(
                    "unresolved dependency must retain a reason"
                )

        else:
            if self.provider is not None:
                raise ValueError(
                    "ambiguous dependency cannot select a provider"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous dependency must retain at least "
                    "two candidates"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapElfClosure:
    """
    Recursive runtime ELF population required by the selected Bootstrap
    environment.
    """

    ramdisk_index: int

    roots: tuple[
        AndroidBootstrapEnvironmentElfBinding,
        ...,
    ]

    elfs: tuple[
        AndroidBootstrapEnvironmentElfBinding,
        ...,
    ]

    dependencies: tuple[
        AndroidBootstrapElfDependencyResolution,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            isinstance(
                self.ramdisk_index,
                bool,
            )
            or not isinstance(
                self.ramdisk_index,
                int,
            )
            or self.ramdisk_index < 0
        ):
            raise ValueError(
                "ramdisk_index must be a non-negative integer"
            )

        for field_name, values in (
            ("roots", self.roots),
            ("elfs", self.elfs),
        ):
            if (
                not isinstance(
                    values,
                    tuple,
                )
                or not all(
                    isinstance(
                        value,
                        AndroidBootstrapEnvironmentElfBinding,
                    )
                    for value
                    in values
                )
            ):
                raise TypeError(
                    f"{field_name} must contain only ELF bindings"
                )

        if (
            not isinstance(
                self.dependencies,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    AndroidBootstrapElfDependencyResolution,
                )
                for value
                in self.dependencies
            )
        ):
            raise TypeError(
                "dependencies must contain only ELF dependency resolutions"
            )

        elf_ids = tuple(
            id(
                value.elf
            )
            for value
            in self.elfs
        )

        if len(
            elf_ids
        ) != len(
            set(
                elf_ids
            )
        ):
            raise ValueError(
                "ELF closure must not contain duplicate canonical ELFs"
            )

        if any(
            id(
                root.elf
            )
            not in set(
                elf_ids
            )
            for root
            in self.roots
        ):
            raise ValueError(
                "every ELF root must belong to the ELF closure"
            )

    @property
    def resolved_dependency_count(self) -> int:
        return sum(
            1
            for value
            in self.dependencies
            if value.resolution
            is AndroidBootstrapEnvironmentElfResolution.RESOLVED
        )

    @property
    def unresolved_dependency_count(self) -> int:
        return sum(
            1
            for value
            in self.dependencies
            if value.resolution
            is AndroidBootstrapEnvironmentElfResolution.UNRESOLVED
        )

    @property
    def ambiguous_dependency_count(self) -> int:
        return sum(
            1
            for value
            in self.dependencies
            if value.resolution
            is AndroidBootstrapEnvironmentElfResolution.AMBIGUOUS
        )


class AndroidBootstrapEnvironmentPopulationReason(
    StrEnum
):
    """
    Why one exact canonical CPIO entry is selected into the generated
    Bootstrap environment.

    Reasons are additive: one physical entry may satisfy several independent
    requirements while remaining present exactly once in the population.
    """

    ROOT_INIT = "root_init"
    INIT_BINARY = "init_binary"
    INIT_CONFIGURATION = "init_configuration"
    FSTAB_CONFIGURATION = "fstab_configuration"
    UEVENTD_CONFIGURATION = "ueventd_configuration"
    VINTF_MANIFEST = "vintf_manifest"
    SELINUX_RUNTIME = "selinux_runtime"

    INIT_RUNTIME_RESOURCE = "init_runtime_resource"
    INIT_RUNTIME_STRUCTURE = "init_runtime_structure"

    RUNTIME_CONSUMER_EXECUTABLE = "runtime_consumer_executable"
    RUNTIME_CONSUMER_RESOURCE = "runtime_consumer_resource"
    RUNTIME_CONSUMER_SUBTREE = "runtime_consumer_subtree"

    SERVICE_EXECUTABLE = "service_executable"
    SERVICE_SYMLINK = "service_symlink"

    ELF_ROOT = "elf_root"
    ELF_DEPENDENCY = "elf_dependency"
    ELF_INTERPRETER = "elf_interpreter"
    ELF_DYNAMIC_PROVIDER = "elf_dynamic_provider"
    ELF_RUNTIME_RESOURCE = "elf_runtime_resource"

    STRUCTURAL_PARENT = "structural_parent"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentPopulationEntry:
    """
    One exact canonical CPIO entry selected into the Bootstrap environment.
    """

    entry: AndroidBootImageCpioEntryInterpretation

    reasons: tuple[
        AndroidBootstrapEnvironmentPopulationReason,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.entry,
            AndroidBootImageCpioEntryInterpretation,
        ):
            raise TypeError(
                "entry must be an "
                "AndroidBootImageCpioEntryInterpretation"
            )

        if (
            not isinstance(
                self.reasons,
                tuple,
            )
            or not self.reasons
        ):
            raise ValueError(
                "population entry must retain at least one reason"
            )

        if not all(
            isinstance(
                value,
                AndroidBootstrapEnvironmentPopulationReason,
            )
            for value
            in self.reasons
        ):
            raise TypeError(
                "population reasons contain an invalid value"
            )

        if len(
            self.reasons
        ) != len(
            set(
                self.reasons
            )
        ):
            raise ValueError(
                "population entry reasons must not contain duplicates"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentPopulationPlan:
    """
    Exact selected CPIO population for the chosen Bootstrap environment.

    Every selected entry retains original canonical CPIO identity. Every
    non-selected entry from that same ramdisk is retained explicitly as
    preserved evidence.

    No bytes are copied or synthesized here.
    """

    ramdisk_index: int
    ramdisk: AndroidBootImageRamdiskInterpretation

    entries: tuple[
        AndroidBootstrapEnvironmentPopulationEntry,
        ...,
    ]

    preserved_entries: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ]

    def __post_init__(self) -> None:
        if (
            isinstance(
                self.ramdisk_index,
                bool,
            )
            or not isinstance(
                self.ramdisk_index,
                int,
            )
            or self.ramdisk_index < 0
        ):
            raise ValueError(
                "ramdisk_index must be a non-negative integer"
            )

        if not isinstance(
            self.ramdisk,
            AndroidBootImageRamdiskInterpretation,
        ):
            raise TypeError(
                "ramdisk must be an "
                "AndroidBootImageRamdiskInterpretation"
            )

        if (
            not isinstance(
                self.entries,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    AndroidBootstrapEnvironmentPopulationEntry,
                )
                for value
                in self.entries
            )
        ):
            raise TypeError(
                "entries must contain only Bootstrap population entries"
            )

        if (
            not isinstance(
                self.preserved_entries,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    AndroidBootImageCpioEntryInterpretation,
                )
                for value
                in self.preserved_entries
            )
        ):
            raise TypeError(
                "preserved_entries must contain only exact CPIO entries"
            )

        selected_ids = tuple(
            id(
                value.entry
            )
            for value
            in self.entries
        )

        if len(
            selected_ids
        ) != len(
            set(
                selected_ids
            )
        ):
            raise ValueError(
                "selected Bootstrap population must not duplicate "
                "canonical CPIO entries"
            )

        preserved_ids = tuple(
            id(
                value
            )
            for value
            in self.preserved_entries
        )

        if len(
            preserved_ids
        ) != len(
            set(
                preserved_ids
            )
        ):
            raise ValueError(
                "preserved Bootstrap population must not duplicate "
                "canonical CPIO entries"
            )

        if (
            set(
                selected_ids
            )
            & set(
                preserved_ids
            )
        ):
            raise ValueError(
                "CPIO entry cannot be both selected and preserved"
            )

        canonical_ids = tuple(
            id(
                value
            )
            for value
            in self.ramdisk.cpio_entries
        )

        accounted_ids = (
            set(
                selected_ids
            )
            | set(
                preserved_ids
            )
        )

        if accounted_ids != set(
            canonical_ids
        ):
            raise ValueError(
                "Bootstrap population must account for every selected-"
                "ramdisk CPIO entry exactly once"
            )

        canonical_positions = {
            id(entry): index
            for index, entry
            in enumerate(
                self.ramdisk.cpio_entries
            )
        }

        selected_positions = tuple(
            canonical_positions[
                id(value.entry)
            ]
            for value
            in self.entries
        )

        if selected_positions != tuple(
            sorted(
                selected_positions
            )
        ):
            raise ValueError(
                "selected population must preserve canonical CPIO order"
            )

        preserved_positions = tuple(
            canonical_positions[
                id(value)
            ]
            for value
            in self.preserved_entries
        )

        if preserved_positions != tuple(
            sorted(
                preserved_positions
            )
        ):
            raise ValueError(
                "preserved population must preserve canonical CPIO order"
            )

    @property
    def selected_count(self) -> int:
        return len(
            self.entries
        )

    @property
    def preserved_count(self) -> int:
        return len(
            self.preserved_entries
        )

    @property
    def accounted_count(self) -> int:
        return (
            self.selected_count
            + self.preserved_count
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentIdentityIndex:
    """
    Canonical identity bridge for one exact ramdisk.

    This index does not discover or parse anything. It joins already-canonical
    evidence using:
      - exact AndroidParserFilesystemSource identity,
      - exact AndroidModelSource identity,
      - canonical Android-visible paths,
      - exact CPIO interpretation identities.

    Every ramdisk-local canonical ELF receives an explicit resolution.
    """

    ramdisk_index: int
    ramdisk: AndroidBootImageRamdiskInterpretation

    source_bindings: tuple[
        AndroidBootstrapEnvironmentSourceBinding,
        ...,
    ]

    elf_bindings: tuple[
        AndroidBootstrapEnvironmentElfBinding,
        ...,
    ]

    vintf_bindings: tuple[
        AndroidBootstrapVintfBinding,
        ...,
    ] = ()

    selinux_bindings: tuple[
        AndroidBootstrapSelinuxBinding,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            isinstance(
                self.ramdisk_index,
                bool,
            )
            or not isinstance(
                self.ramdisk_index,
                int,
            )
            or self.ramdisk_index < 0
        ):
            raise ValueError(
                "ramdisk_index must be a non-negative integer"
            )

        if not isinstance(
            self.ramdisk,
            AndroidBootImageRamdiskInterpretation,
        ):
            raise TypeError(
                "ramdisk must be an "
                "AndroidBootImageRamdiskInterpretation"
            )

        for field_name, values, expected_type in (
            (
                "source_bindings",
                self.source_bindings,
                AndroidBootstrapEnvironmentSourceBinding,
            ),
            (
                "elf_bindings",
                self.elf_bindings,
                AndroidBootstrapEnvironmentElfBinding,
            ),
            (
                "vintf_bindings",
                self.vintf_bindings,
                AndroidBootstrapVintfBinding,
            ),
            (
                "selinux_bindings",
                self.selinux_bindings,
                AndroidBootstrapSelinuxBinding,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid value"
                )

        cpio_ids = {
            id(entry)
            for entry
            in self.ramdisk.cpio_entries
        }

        expected_source_entries = tuple(
            entry
            for entry
            in self.ramdisk.cpio_entries
            if entry.associated_source is not None
        )

        actual_source_entries = tuple(
            binding.entry
            for binding
            in self.source_bindings
        )

        if tuple(
            id(value)
            for value
            in actual_source_entries
        ) != tuple(
            id(value)
            for value
            in expected_source_entries
        ):
            raise ValueError(
                "Bootstrap identity index must account for every "
                "Boot Image associated-source CPIO entry exactly once "
                "and in canonical order"
            )

        for binding in self.source_bindings:
            if (
                id(binding.entry)
                not in cpio_ids
            ):
                raise ValueError(
                    "source binding entry must belong to the "
                    "exact ramdisk CPIO interpretation"
                )

            if (
                binding.source.filesystem_source
                is not self.ramdisk.filesystem_source
            ):
                raise ValueError(
                    "source binding must preserve exact ramdisk "
                    "filesystem-source identity"
                )

        seen_elf_ids = set()

        for binding in self.elf_bindings:
            if (
                not binding.elf.source.is_filesystem_backed
                or binding.elf.source.filesystem_source
                is not self.ramdisk.filesystem_source
            ):
                raise ValueError(
                    "ELF binding must belong to the exact ramdisk "
                    "filesystem source"
                )

            if id(
                binding.elf
            ) in seen_elf_ids:
                raise ValueError(
                    "canonical ramdisk ELF must not be indexed twice"
                )

            seen_elf_ids.add(
                id(
                    binding.elf
                )
            )

            for candidate in binding.candidates:
                if id(
                    candidate
                ) not in cpio_ids:
                    raise ValueError(
                        "ELF binding candidate must belong to the "
                        "exact ramdisk CPIO interpretation"
                    )

            if binding.entry is not None:
                if id(
                    binding.entry
                ) not in cpio_ids:
                    raise ValueError(
                        "resolved ELF entry must belong to the "
                        "exact ramdisk CPIO interpretation"
                    )

                elf_path = self._normalize_path(
                    binding.elf.source.android_path
                )

                cpio_path = self._normalize_path(
                    binding.entry.entry.path
                )

                if elf_path != cpio_path:
                    raise ValueError(
                        "resolved ELF binding must preserve exact "
                        "canonical Android/CPIO path correspondence"
                    )

        for binding in self.vintf_bindings:
            if (
                binding.source.filesystem_source
                is not self.ramdisk.filesystem_source
            ):
                raise ValueError(
                    "VINTF binding must preserve exact ramdisk "
                    "filesystem-source identity"
                )

            for candidate in binding.candidates:
                if id(
                    candidate
                ) not in cpio_ids:
                    raise ValueError(
                        "VINTF candidate must belong to the exact "
                        "ramdisk CPIO interpretation"
                    )

            if binding.entry is not None:
                if id(
                    binding.entry
                ) not in cpio_ids:
                    raise ValueError(
                        "resolved VINTF entry must belong to the "
                        "exact ramdisk CPIO interpretation"
                    )

                if binding.source.android_path is None:
                    raise ValueError(
                        "resolved VINTF binding requires a canonical "
                        "Android path"
                    )

                if (
                    self._normalize_path(
                        binding.source.android_path
                    )
                    != self._normalize_path(
                        binding.entry.entry.path
                    )
                ):
                    raise ValueError(
                        "resolved VINTF binding must preserve exact "
                        "Android/CPIO path correspondence"
                    )

        for binding in self.selinux_bindings:
            if (
                binding.source.filesystem_source
                is not self.ramdisk.filesystem_source
            ):
                raise ValueError(
                    "SELinux binding must preserve exact ramdisk "
                    "filesystem-source identity"
                )

            for candidate in binding.candidates:
                if id(
                    candidate
                ) not in cpio_ids:
                    raise ValueError(
                        "SELinux candidate must belong to the exact "
                        "ramdisk CPIO interpretation"
                    )

            if binding.entry is not None:
                if id(
                    binding.entry
                ) not in cpio_ids:
                    raise ValueError(
                        "resolved SELinux entry must belong to the "
                        "exact ramdisk CPIO interpretation"
                    )

                if binding.source.android_path is None:
                    raise ValueError(
                        "resolved SELinux binding requires a canonical "
                        "Android path"
                    )

                if (
                    self._normalize_path(
                        binding.source.android_path
                    )
                    != self._normalize_path(
                        binding.entry.entry.path
                    )
                ):
                    raise ValueError(
                        "resolved SELinux binding must preserve exact "
                        "Android/CPIO path correspondence"
                    )

    @staticmethod
    def _normalize_path(
        value,
    ) -> PurePosixPath:
        if hasattr(
            value,
            "as_posix",
        ):
            value = value.as_posix()

        normalized = str(
            value
        ).lstrip(
            "/"
        )

        return PurePosixPath(
            "/"
            + normalized
        )

    @property
    def associated_source_count(self) -> int:
        return len(
            self.source_bindings
        )

    @property
    def elf_count(self) -> int:
        return len(
            self.elf_bindings
        )

    @property
    def vintf_count(self) -> int:
        return len(
            self.vintf_bindings
        )

    @property
    def resolved_vintf_count(self) -> int:
        return sum(
            1
            for binding
            in self.vintf_bindings
            if binding.resolution
            is AndroidBootstrapRuntimeSupportResolution.RESOLVED
        )

    @property
    def unresolved_vintf_count(self) -> int:
        return sum(
            1
            for binding
            in self.vintf_bindings
            if binding.resolution
            is AndroidBootstrapRuntimeSupportResolution.UNRESOLVED
        )

    @property
    def ambiguous_vintf_count(self) -> int:
        return sum(
            1
            for binding
            in self.vintf_bindings
            if binding.resolution
            is AndroidBootstrapRuntimeSupportResolution.AMBIGUOUS
        )

    @property
    def selinux_count(self) -> int:
        return len(
            self.selinux_bindings
        )

    @property
    def resolved_selinux_count(self) -> int:
        return sum(
            1
            for binding
            in self.selinux_bindings
            if binding.resolution
            is AndroidBootstrapRuntimeSupportResolution.RESOLVED
        )

    @property
    def unresolved_selinux_count(self) -> int:
        return sum(
            1
            for binding
            in self.selinux_bindings
            if binding.resolution
            is AndroidBootstrapRuntimeSupportResolution.UNRESOLVED
        )

    @property
    def ambiguous_selinux_count(self) -> int:
        return sum(
            1
            for binding
            in self.selinux_bindings
            if binding.resolution
            is AndroidBootstrapRuntimeSupportResolution.AMBIGUOUS
        )

    @property
    def resolved_elf_count(self) -> int:
        return sum(
            1
            for binding
            in self.elf_bindings
            if binding.resolution
            is AndroidBootstrapEnvironmentElfResolution.RESOLVED
        )

    @property
    def unresolved_elf_count(self) -> int:
        return sum(
            1
            for binding
            in self.elf_bindings
            if binding.resolution
            is AndroidBootstrapEnvironmentElfResolution.UNRESOLVED
        )

    @property
    def ambiguous_elf_count(self) -> int:
        return sum(
            1
            for binding
            in self.elf_bindings
            if binding.resolution
            is AndroidBootstrapEnvironmentElfResolution.AMBIGUOUS
        )


class AndroidBootstrapInitResolution(
    StrEnum
):
    """
    Resolution state for one Bootstrap INIT requirement.
    """

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"


class AndroidBootstrapInitSourceRole(
    StrEnum
):
    """
    Why one canonical INIT source participates in the Bootstrap closure.
    """

    ROOT = "root"
    IMPORTED = "imported"
    DIRECTORY_LOADED = "directory_loaded"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRootInitBinaryResolution:
    """
    Resolve the canonical /init entry against one exact ramdisk.

    The entry may itself be the init executable or a canonical CPIO symlink
    whose target is resolved separately by environment-root selection.
    """

    resolution: AndroidBootstrapInitResolution

    entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    ) = None

    candidates: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.resolution,
            AndroidBootstrapInitResolution,
        ):
            raise TypeError(
                "resolution must be an AndroidBootstrapInitResolution"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if (
            self.resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            if self.entry is None:
                raise ValueError(
                    "resolved root /init must retain its exact CPIO entry"
                )

            if self.candidates != (
                self.entry,
            ):
                raise ValueError(
                    "resolved root /init must retain exactly one candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        ):
            if (
                self.entry is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved root /init cannot select or retain candidates"
                )

        else:
            if self.entry is not None:
                raise ValueError(
                    "ambiguous root /init cannot select a candidate"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous root /init must retain at least two candidates"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapInitSourceSelection:
    """
    One exact canonical ParsedAndroidInitSource selected into INIT closure.
    """

    source: ParsedAndroidInitSource
    role: AndroidBootstrapInitSourceRole

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidInitSource,
        ):
            raise TypeError(
                "source must be a ParsedAndroidInitSource"
            )

        if not isinstance(
            self.role,
            AndroidBootstrapInitSourceRole,
        ):
            raise TypeError(
                "role must be an AndroidBootstrapInitSourceRole"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapInitImportResolution:
    """
    Resolution of one literal canonical INIT import declaration.

    Non-literal property-expanded/glob imports remain unresolved rather than
    being expanded from host state.
    """

    owner: ParsedAndroidInitSource
    declaration: AndroidInitImport
    resolution: AndroidBootstrapInitResolution

    source: ParsedAndroidInitSource | None = None

    candidates: tuple[
        ParsedAndroidInitSource,
        ...,
    ] = ()

    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.owner,
            ParsedAndroidInitSource,
        ):
            raise TypeError(
                "owner must be a ParsedAndroidInitSource"
            )

        if not isinstance(
            self.declaration,
            AndroidInitImport,
        ):
            raise TypeError(
                "declaration must be an AndroidInitImport"
            )

        if not isinstance(
            self.resolution,
            AndroidBootstrapInitResolution,
        ):
            raise TypeError(
                "resolution must be an AndroidBootstrapInitResolution"
            )

        if not isinstance(
            self.candidates,
            tuple,
        ):
            raise TypeError(
                "candidates must be a tuple"
            )

        if (
            self.reason is not None
            and (
                not isinstance(
                    self.reason,
                    str,
                )
                or not self.reason
            )
        ):
            raise ValueError(
                "reason must be a non-empty string or None"
            )

        if (
            self.resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            if not isinstance(
                self.source,
                ParsedAndroidInitSource,
            ):
                raise ValueError(
                    "resolved INIT import must retain its exact source"
                )

            if self.candidates != (
                self.source,
            ):
                raise ValueError(
                    "resolved INIT import must retain exactly one candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        ):
            if (
                self.source is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved INIT import cannot select or retain candidates"
                )

            if self.reason is None:
                raise ValueError(
                    "unresolved INIT import must retain a reason"
                )

        else:
            if self.source is not None:
                raise ValueError(
                    "ambiguous INIT import cannot select a source"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous INIT import must retain at least two candidates"
                )


class AndroidBootstrapInitServiceDisposition(
    Enum,
):
    """
    Bootstrap disposition for one factory INIT service.

    REQUIRED:
        The selected factory service contributes to the minimal Bootstrap
        environment and its executable must resolve.

    EXCLUDED:
        The factory service remains preserved as canonical evidence but is
        deliberately outside the minimal Bootstrap environment.
    """

    REQUIRED = "required"
    EXCLUDED = "excluded"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapInitServiceExecutableResolution:
    """
    Resolve one selected INIT service executable against the exact ramdisk
    CPIO population.

    This establishes local availability only. It does not yet select ELF
    providers, shared libraries, or symlink targets.
    """

    owner: ParsedAndroidInitSource
    service: AndroidInitService
    resolution: AndroidBootstrapInitResolution

    disposition: (
        AndroidBootstrapInitServiceDisposition
    ) = (
        AndroidBootstrapInitServiceDisposition.REQUIRED
    )

    entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    ) = None

    candidates: tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ] = ()

    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.owner,
            ParsedAndroidInitSource,
        ):
            raise TypeError(
                "owner must be a ParsedAndroidInitSource"
            )

        if not isinstance(
            self.service,
            AndroidInitService,
        ):
            raise TypeError(
                "service must be an AndroidInitService"
            )

        if not isinstance(
            self.resolution,
            AndroidBootstrapInitResolution,
        ):
            raise TypeError(
                "resolution must be an AndroidBootstrapInitResolution"
            )

        if not isinstance(
            self.disposition,
            AndroidBootstrapInitServiceDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootstrapInitServiceDisposition"
            )

        if (
            self.disposition
            is AndroidBootstrapInitServiceDisposition.EXCLUDED
        ):
            if (
                self.entry is not None
                or self.candidates
            ):
                raise ValueError(
                    "excluded service executable cannot retain "
                    "a selected provider"
                )

            if (
                self.resolution
                is not AndroidBootstrapInitResolution.UNRESOLVED
            ):
                raise ValueError(
                    "excluded service executable must use an "
                    "UNRESOLVED provider resolution"
                )

            if self.reason is None:
                raise ValueError(
                    "excluded service executable must retain "
                    "an explicit reason"
                )

            return

        if (
            self.resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            if self.entry is None:
                raise ValueError(
                    "resolved service executable must retain its CPIO entry"
                )

            if self.candidates != (
                self.entry,
            ):
                raise ValueError(
                    "resolved service executable must retain "
                    "exactly one candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        ):
            if (
                self.entry is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved service executable cannot retain candidates"
                )

            if self.reason is None:
                raise ValueError(
                    "unresolved service executable must retain a reason"
                )

        else:
            if self.entry is not None:
                raise ValueError(
                    "ambiguous service executable cannot select an entry"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous service executable must retain "
                    "at least two candidates"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapInitClosure:
    """
    Canonical INIT closure for one exact interpreted ramdisk.

    For the globally selected Bootstrap environment root, the closure starts
    from the exact canonical INIT spine proven by environment-root selection.
    Non-selected ramdisks retain no independently invented INIT root.

    Literal INIT imports and explicitly supported Bootstrap property
    substitutions are traversed.

    The selected environment also includes canonical INIT sources loaded by
    Android init from its standard configuration directories. Directory-loaded
    sources remain distinct from explicit imports and may themselves contribute
    additional imports.

    Unsupported property expressions, wildcard expansion, host filesystem
    lookup, and implicit device-specific fallback remain unresolved.
    """

    ramdisk_index: int
    ramdisk: AndroidBootImageRamdiskInterpretation

    root_binary: AndroidBootstrapRootInitBinaryResolution

    root_source_resolution: AndroidBootstrapInitResolution
    root_source: ParsedAndroidInitSource | None = None

    root_source_candidates: tuple[
        ParsedAndroidInitSource,
        ...,
    ] = ()

    selected_sources: tuple[
        AndroidBootstrapInitSourceSelection,
        ...,
    ] = ()

    imports: tuple[
        AndroidBootstrapInitImportResolution,
        ...,
    ] = ()

    service_executables: tuple[
        AndroidBootstrapInitServiceExecutableResolution,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if (
            isinstance(
                self.ramdisk_index,
                bool,
            )
            or not isinstance(
                self.ramdisk_index,
                int,
            )
            or self.ramdisk_index < 0
        ):
            raise ValueError(
                "ramdisk_index must be a non-negative integer"
            )

        if not isinstance(
            self.ramdisk,
            AndroidBootImageRamdiskInterpretation,
        ):
            raise TypeError(
                "ramdisk must be an "
                "AndroidBootImageRamdiskInterpretation"
            )

        if not isinstance(
            self.root_binary,
            AndroidBootstrapRootInitBinaryResolution,
        ):
            raise TypeError(
                "root_binary must be an "
                "AndroidBootstrapRootInitBinaryResolution"
            )

        if not isinstance(
            self.root_source_resolution,
            AndroidBootstrapInitResolution,
        ):
            raise TypeError(
                "root_source_resolution must be an "
                "AndroidBootstrapInitResolution"
            )

        if (
            self.root_source_resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            if not isinstance(
                self.root_source,
                ParsedAndroidInitSource,
            ):
                raise ValueError(
                    "resolved INIT spine must retain its exact canonical source"
                )

            if self.root_source_candidates != (
                self.root_source,
            ):
                raise ValueError(
                    "resolved INIT spine must retain exactly one candidate"
                )

        elif (
            self.root_source_resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        ):
            if (
                self.root_source is not None
                or self.root_source_candidates
            ):
                raise ValueError(
                    "unresolved INIT spine cannot retain candidates"
                )

        else:
            if self.root_source is not None:
                raise ValueError(
                    "ambiguous INIT spine cannot select a source"
                )

            if len(
                self.root_source_candidates
            ) < 2:
                raise ValueError(
                    "ambiguous INIT spine must retain at least two candidates"
                )

        for field_name, values, expected_type in (
            (
                "selected_sources",
                self.selected_sources,
                AndroidBootstrapInitSourceSelection,
            ),
            (
                "imports",
                self.imports,
                AndroidBootstrapInitImportResolution,
            ),
            (
                "service_executables",
                self.service_executables,
                AndroidBootstrapInitServiceExecutableResolution,
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not all(
                isinstance(
                    value,
                    expected_type,
                )
                for value
                in values
            ):
                raise TypeError(
                    f"{field_name} contains an invalid value"
                )

        selected_ids = tuple(
            id(
                value.source
            )
            for value
            in self.selected_sources
        )

        if len(
            selected_ids
        ) != len(
            set(
                selected_ids
            )
        ):
            raise ValueError(
                "INIT closure must not select a canonical source twice"
            )

        ramdisk_init_ids = {
            id(
                value
            )
            for value
            in self.ramdisk.init_files
        }

        if any(
            source_id not in ramdisk_init_ids
            for source_id
            in selected_ids
        ):
            raise ValueError(
                "INIT closure may select only exact canonical INIT sources "
                "belonging to its ramdisk"
            )

        if (
            self.root_source is not None
            and (
                not self.selected_sources
                or self.selected_sources[0].source
                is not self.root_source
                or self.selected_sources[0].role
                is not AndroidBootstrapInitSourceRole.ROOT
            )
        ):
            raise ValueError(
                "resolved INIT spine must be the first selected INIT source"
            )

    @property
    def selected_source_count(self) -> int:
        return len(
            self.selected_sources
        )

    @property
    def imported_source_count(self) -> int:
        return sum(
            1
            for value
            in self.selected_sources
            if value.role
            is AndroidBootstrapInitSourceRole.IMPORTED
        )

    @property
    def directory_loaded_source_count(self) -> int:
        return sum(
            1
            for value
            in self.selected_sources
            if value.role
            is AndroidBootstrapInitSourceRole.DIRECTORY_LOADED
        )

    @property
    def resolved_import_count(self) -> int:
        return sum(
            1
            for value
            in self.imports
            if value.resolution
            is AndroidBootstrapInitResolution.RESOLVED
        )

    @property
    def unresolved_import_count(self) -> int:
        return sum(
            1
            for value
            in self.imports
            if value.resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        )

    @property
    def ambiguous_import_count(self) -> int:
        return sum(
            1
            for value
            in self.imports
            if value.resolution
            is AndroidBootstrapInitResolution.AMBIGUOUS
        )

    @property
    def resolved_service_executable_count(self) -> int:
        return sum(
            1
            for value
            in self.service_executables
            if (
                value.disposition
                is AndroidBootstrapInitServiceDisposition.REQUIRED
                and value.resolution
                is AndroidBootstrapInitResolution.RESOLVED
            )
        )

    @property
    def unresolved_service_executable_count(self) -> int:
        return sum(
            1
            for value
            in self.service_executables
            if (
                value.disposition
                is AndroidBootstrapInitServiceDisposition.REQUIRED
                and value.resolution
                is AndroidBootstrapInitResolution.UNRESOLVED
            )
        )

    @property
    def excluded_service_executable_count(self) -> int:
        return sum(
            1
            for value
            in self.service_executables
            if value.disposition
            is AndroidBootstrapInitServiceDisposition.EXCLUDED
        )

    @property
    def ambiguous_service_executable_count(self) -> int:
        return sum(
            1
            for value
            in self.service_executables
            if (
                value.disposition
                is AndroidBootstrapInitServiceDisposition.REQUIRED
                and value.resolution
                is AndroidBootstrapInitResolution.AMBIGUOUS
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentConfiguration:
    """
    Explicit Bootstrap environment configuration.

    ``hardware`` supplies the Android ``ro.hardware`` value required by
    recovery INIT imports when that value cannot be derived directly from
    canonical factory evidence.

    ``tangorpro`` is the current development default. Any explicitly supplied
    value overrides that default. Keeping the default here, rather than inside
    INIT resolution, provides the permanent device/user configuration seam.
    """

    hardware: str = "tangorpro"

    excluded_init_services: tuple[
        str,
        ...,
    ] = (
        "charger",
    )

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.hardware,
                str,
            )
            or not self.hardware.strip()
        ):
            raise ValueError(
                "Bootstrap hardware must be a non-empty string"
            )

        normalized = self.hardware.strip()

        if normalized != self.hardware:
            object.__setattr__(
                self,
                "hardware",
                normalized,
            )

        if (
            not isinstance(
                self.excluded_init_services,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    str,
                )
                and bool(
                    value.strip()
                )
                for value
                in self.excluded_init_services
            )
        ):
            raise TypeError(
                "excluded_init_services must contain only "
                "non-empty service names"
            )

        normalized_exclusions = tuple(
            value.strip()
            for value
            in self.excluded_init_services
        )

        if len(
            normalized_exclusions
        ) != len(
            set(
                normalized_exclusions
            )
        ):
            raise ValueError(
                "excluded_init_services must not contain duplicates"
            )

        if (
            normalized_exclusions
            != self.excluded_init_services
        ):
            object.__setattr__(
                self,
                "excluded_init_services",
                normalized_exclusions,
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentRootCandidate:
    """
    Capability-derived Bootstrap environment-root candidate.

    A candidate is identified exclusively from canonical ramdisk contents.
    Partition/container names are deliberately not part of the selection
    policy.

    The minimum usable recovery/bootstrap environment requires:
      - one exact /init entry;
      - that /init resolve to one exact init binary in the same ramdisk;
      - one canonical Android recovery INIT spine;
      - at least one canonical fstab;
      - at least one canonical ueventd source.

    Recovery/adbd/fastbootd service observations are retained as supporting
    evidence, not as hard requirements.
    """

    ramdisk_index: int
    ramdisk: AndroidBootImageRamdiskInterpretation

    root_entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    )

    root_target_path: PurePosixPath | None

    init_binary_entry: (
        AndroidBootImageCpioEntryInterpretation
        | None
    )

    init_spine_resolution: AndroidBootstrapInitResolution

    init_spine: ParsedAndroidInitSource | None = None

    init_spine_candidates: tuple[
        ParsedAndroidInitSource,
        ...,
    ] = ()

    recovery_service_count: int = 0
    adb_service_count: int = 0
    fastboot_service_count: int = 0

    eligible: bool = False
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            isinstance(
                self.ramdisk_index,
                bool,
            )
            or not isinstance(
                self.ramdisk_index,
                int,
            )
            or self.ramdisk_index < 0
        ):
            raise ValueError(
                "ramdisk_index must be a non-negative integer"
            )

        if not isinstance(
            self.ramdisk,
            AndroidBootImageRamdiskInterpretation,
        ):
            raise TypeError(
                "ramdisk must be an "
                "AndroidBootImageRamdiskInterpretation"
            )

        if (
            self.root_entry is not None
            and not isinstance(
                self.root_entry,
                AndroidBootImageCpioEntryInterpretation,
            )
        ):
            raise TypeError(
                "root_entry must be an exact CPIO interpretation or None"
            )

        if (
            self.root_target_path is not None
            and not isinstance(
                self.root_target_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "root_target_path must be PurePosixPath or None"
            )

        if (
            self.init_binary_entry is not None
            and not isinstance(
                self.init_binary_entry,
                AndroidBootImageCpioEntryInterpretation,
            )
        ):
            raise TypeError(
                "init_binary_entry must be an exact CPIO "
                "interpretation or None"
            )

        if not isinstance(
            self.init_spine_resolution,
            AndroidBootstrapInitResolution,
        ):
            raise TypeError(
                "init_spine_resolution must be an "
                "AndroidBootstrapInitResolution"
            )

        if not isinstance(
            self.init_spine_candidates,
            tuple,
        ):
            raise TypeError(
                "init_spine_candidates must be a tuple"
            )

        if (
            self.init_spine_resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            if not isinstance(
                self.init_spine,
                ParsedAndroidInitSource,
            ):
                raise ValueError(
                    "resolved INIT spine must retain its exact "
                    "canonical source"
                )

            if self.init_spine_candidates != (
                self.init_spine,
            ):
                raise ValueError(
                    "resolved INIT spine must retain exactly "
                    "one candidate"
                )

        elif (
            self.init_spine_resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        ):
            if (
                self.init_spine is not None
                or self.init_spine_candidates
            ):
                raise ValueError(
                    "unresolved INIT spine cannot retain candidates"
                )

        else:
            if self.init_spine is not None:
                raise ValueError(
                    "ambiguous INIT spine cannot select a source"
                )

            if len(
                self.init_spine_candidates
            ) < 2:
                raise ValueError(
                    "ambiguous INIT spine must retain at least "
                    "two candidates"
                )

        for name, value in (
            (
                "recovery_service_count",
                self.recovery_service_count,
            ),
            (
                "adb_service_count",
                self.adb_service_count,
            ),
            (
                "fastboot_service_count",
                self.fastboot_service_count,
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
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer"
                )

        if not isinstance(
            self.eligible,
            bool,
        ):
            raise TypeError(
                "eligible must be bool"
            )

        if (
            not isinstance(
                self.reasons,
                tuple,
            )
            or not all(
                isinstance(
                    value,
                    str,
                )
                and value
                for value
                in self.reasons
            )
        ):
            raise TypeError(
                "reasons must contain only non-empty strings"
            )

        expected_eligible = (
            self.root_entry is not None
            and self.init_binary_entry is not None
            and (
                self.init_spine_resolution
                is AndroidBootstrapInitResolution.RESOLVED
            )
            and bool(
                self.ramdisk.fstabs
            )
            and bool(
                self.ramdisk.ueventd_files
            )
        )

        if self.eligible is not expected_eligible:
            raise ValueError(
                "eligible must exactly reflect canonical "
                "Bootstrap environment capabilities"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentRootSelection:
    """
    Global environment-root selection across all interpreted boot ramdisks.

    Exactly one capability-complete candidate resolves the environment root.
    Zero remains unresolved. Multiple remain ambiguous.
    """

    resolution: AndroidBootstrapInitResolution

    candidate: (
        AndroidBootstrapEnvironmentRootCandidate
        | None
    ) = None

    candidates: tuple[
        AndroidBootstrapEnvironmentRootCandidate,
        ...,
    ] = ()

    all_candidates: tuple[
        AndroidBootstrapEnvironmentRootCandidate,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.resolution,
            AndroidBootstrapInitResolution,
        ):
            raise TypeError(
                "resolution must be an AndroidBootstrapInitResolution"
            )

        for name, values in (
            (
                "candidates",
                self.candidates,
            ),
            (
                "all_candidates",
                self.all_candidates,
            ),
        ):
            if (
                not isinstance(
                    values,
                    tuple,
                )
                or not all(
                    isinstance(
                        value,
                        AndroidBootstrapEnvironmentRootCandidate,
                    )
                    for value
                    in values
                )
            ):
                raise TypeError(
                    f"{name} must contain only environment-root candidates"
                )

        expected_candidates = tuple(
            value
            for value
            in self.all_candidates
            if value.eligible
        )

        if tuple(
            id(
                value
            )
            for value
            in self.candidates
        ) != tuple(
            id(
                value
            )
            for value
            in expected_candidates
        ):
            raise ValueError(
                "environment-root candidates must exactly preserve "
                "eligible candidate order and identity"
            )

        if (
            self.resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            if self.candidate is None:
                raise ValueError(
                    "resolved environment root must select a candidate"
                )

            if self.candidates != (
                self.candidate,
            ):
                raise ValueError(
                    "resolved environment root must have exactly "
                    "one eligible candidate"
                )

        elif (
            self.resolution
            is AndroidBootstrapInitResolution.UNRESOLVED
        ):
            if (
                self.candidate is not None
                or self.candidates
            ):
                raise ValueError(
                    "unresolved environment root cannot select candidates"
                )

        else:
            if self.candidate is not None:
                raise ValueError(
                    "ambiguous environment root cannot select a candidate"
                )

            if len(
                self.candidates
            ) < 2:
                raise ValueError(
                    "ambiguous environment root must retain at least "
                    "two eligible candidates"
                )



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentPlan:
    """
    First-class Bootstrap Environment Planning boundary.

    The plan conserves the complete Boot Image ramdisk interpretation and
    classifies every exact canonical CPIO entry once. It deliberately does
    not yet select a final initramfs population or materialize any files.
    """

    intake: AndroidBootstrapIntakeResult
    boot_image_interpretation: (
        AndroidBootImageInterpretationResult
    )
    requirements: tuple[
        AndroidBootstrapEnvironmentRequirement,
        ...,
    ]

    identity_indexes: tuple[
        AndroidBootstrapEnvironmentIdentityIndex,
        ...,
    ] = ()

    environment_root: (
        AndroidBootstrapEnvironmentRootSelection
        | None
    ) = None

    init_closures: tuple[
        AndroidBootstrapInitClosure,
        ...,
    ] = ()

    elf_closure: (
        AndroidBootstrapElfClosure
        | None
    ) = None

    population: (
        AndroidBootstrapEnvironmentPopulationPlan
        | None
    ) = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.intake,
            AndroidBootstrapIntakeResult,
        ):
            raise TypeError(
                "intake must be an AndroidBootstrapIntakeResult"
            )

        if not isinstance(
            self.boot_image_interpretation,
            AndroidBootImageInterpretationResult,
        ):
            raise TypeError(
                "boot_image_interpretation must be an "
                "AndroidBootImageInterpretationResult"
            )

        if (
            self.boot_image_interpretation.parsing
            is not self.intake.parsing
        ):
            raise ValueError(
                "Bootstrap Environment Planning must preserve "
                "exact canonical Parsing identity"
            )

        if not isinstance(
            self.requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidBootstrapEnvironmentRequirement,
            )
            for requirement
            in self.requirements
        ):
            raise TypeError(
                "requirements contain an invalid "
                "Bootstrap environment requirement"
            )

        expected_entries = tuple(
            entry
            for ramdisk
            in self.boot_image_interpretation.ramdisks
            for entry
            in ramdisk.cpio_entries
        )

        actual_entries = tuple(
            requirement.entry
            for requirement
            in self.requirements
        )

        if len(
            actual_entries
        ) != len(
            expected_entries
        ):
            raise ValueError(
                "Bootstrap Environment Planning must account "
                "for every canonical ramdisk CPIO entry exactly once"
            )

        if tuple(
            id(value)
            for value
            in actual_entries
        ) != tuple(
            id(value)
            for value
            in expected_entries
        ):
            raise ValueError(
                "Bootstrap Environment Planning must conserve "
                "exact CPIO interpretation order and object identity"
            )

        if not isinstance(
            self.identity_indexes,
            tuple,
        ):
            raise TypeError(
                "identity_indexes must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootstrapEnvironmentIdentityIndex,
            )
            for value
            in self.identity_indexes
        ):
            raise TypeError(
                "identity_indexes contain an invalid "
                "Bootstrap environment identity index"
            )

        if len(
            self.identity_indexes
        ) != len(
            self.boot_image_interpretation.ramdisks
        ):
            raise ValueError(
                "Bootstrap Environment Planning must retain "
                "exactly one identity index per interpreted ramdisk"
            )

        for expected_index, (
            ramdisk,
            identity_index,
        ) in enumerate(
            zip(
                self.boot_image_interpretation.ramdisks,
                self.identity_indexes,
                strict=True,
            )
        ):
            if (
                identity_index.ramdisk_index
                != expected_index
            ):
                raise ValueError(
                    "Bootstrap ramdisk identity indexes must preserve "
                    "canonical ramdisk order"
                )

            if (
                identity_index.ramdisk
                is not ramdisk
            ):
                raise ValueError(
                    "Bootstrap identity index must retain exact "
                    "Boot Image ramdisk interpretation identity"
                )

        if not isinstance(
            self.environment_root,
            AndroidBootstrapEnvironmentRootSelection,
        ):
            raise TypeError(
                "environment_root must be an "
                "AndroidBootstrapEnvironmentRootSelection"
            )

        expected_ramdisk_ids = tuple(
            id(
                ramdisk
            )
            for ramdisk
            in self.boot_image_interpretation.ramdisks
        )

        actual_ramdisk_ids = tuple(
            id(
                candidate.ramdisk
            )
            for candidate
            in self.environment_root.all_candidates
        )

        if actual_ramdisk_ids != expected_ramdisk_ids:
            raise ValueError(
                "Bootstrap environment-root analysis must preserve "
                "every interpreted ramdisk in exact canonical order "
                "and object identity"
            )

        for expected_index, candidate in enumerate(
            self.environment_root.all_candidates
        ):
            if candidate.ramdisk_index != expected_index:
                raise ValueError(
                    "Bootstrap environment-root candidates must "
                    "preserve canonical ramdisk indexes"
                )

        if (
            self.environment_root.resolution
            is AndroidBootstrapInitResolution.RESOLVED
        ):
            selected_environment_candidate = (
                self.environment_root.candidate
            )

            if selected_environment_candidate is None:
                raise ValueError(
                    "resolved Bootstrap environment root must "
                    "retain its selected candidate"
                )

            rooted_closures = tuple(
                closure
                for closure
                in self.init_closures
                if (
                    closure.root_source_resolution
                    is AndroidBootstrapInitResolution.RESOLVED
                )
            )

            if len(
                rooted_closures
            ) != 1:
                raise ValueError(
                    "resolved Bootstrap environment root must "
                    "produce exactly one rooted INIT closure"
                )

            rooted = rooted_closures[0]

            if (
                rooted.ramdisk
                is not selected_environment_candidate.ramdisk
            ):
                raise ValueError(
                    "rooted Bootstrap INIT closure must retain "
                    "the exact selected environment ramdisk"
                )

            if (
                rooted.root_source
                is not selected_environment_candidate.init_spine
            ):
                raise ValueError(
                    "rooted Bootstrap INIT closure must retain "
                    "the exact selected canonical INIT spine"
                )

        if not isinstance(
            self.init_closures,
            tuple,
        ):
            raise TypeError(
                "init_closures must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootstrapInitClosure,
            )
            for value
            in self.init_closures
        ):
            raise TypeError(
                "init_closures contain an invalid INIT closure"
            )

        if len(
            self.init_closures
        ) != len(
            self.boot_image_interpretation.ramdisks
        ):
            raise ValueError(
                "Bootstrap Environment Planning must retain exactly "
                "one INIT closure per interpreted ramdisk"
            )

        for expected_index, (
            ramdisk,
            closure,
        ) in enumerate(
            zip(
                self.boot_image_interpretation.ramdisks,
                self.init_closures,
                strict=True,
            )
        ):
            if closure.ramdisk_index != expected_index:
                raise ValueError(
                    "Bootstrap INIT closures must preserve "
                    "canonical ramdisk order"
                )

            if closure.ramdisk is not ramdisk:
                raise ValueError(
                    "Bootstrap INIT closure must retain exact "
                    "Boot Image ramdisk interpretation identity"
                )

        if self.elf_closure is not None:
            if not isinstance(
                self.elf_closure,
                AndroidBootstrapElfClosure,
            ):
                raise TypeError(
                    "elf_closure must be an AndroidBootstrapElfClosure "
                    "or None"
                )

            if (
                self.environment_root.candidate is None
            ):
                raise ValueError(
                    "ELF closure requires one selected environment root"
                )

            if (
                self.elf_closure.ramdisk_index
                != self.environment_root.candidate.ramdisk_index
            ):
                raise ValueError(
                    "ELF closure must belong to the selected "
                    "environment ramdisk"
                )


        if self.population is not None:
            if not isinstance(
                self.population,
                AndroidBootstrapEnvironmentPopulationPlan,
            ):
                raise TypeError(
                    "population must be an "
                    "AndroidBootstrapEnvironmentPopulationPlan or None"
                )

            selected_candidate = (
                self.environment_root.candidate
            )

            if selected_candidate is None:
                raise ValueError(
                    "Bootstrap population requires a selected "
                    "environment root"
                )

            if (
                self.population.ramdisk_index
                != selected_candidate.ramdisk_index
                or self.population.ramdisk
                is not selected_candidate.ramdisk
            ):
                raise ValueError(
                    "Bootstrap population must retain exact selected "
                    "environment ramdisk identity"
                )

    @property
    def requirement_count(self) -> int:
        return len(
            self.requirements
        )

    @property
    def required_candidate_count(self) -> int:
        return sum(
            1
            for value
            in self.requirements
            if value.disposition
            is AndroidBootstrapEnvironmentRequirementDisposition
            .REQUIRED_CANDIDATE
        )

    @property
    def available_candidate_count(self) -> int:
        return sum(
            1
            for value
            in self.requirements
            if value.disposition
            is AndroidBootstrapEnvironmentRequirementDisposition
            .AVAILABLE_CANDIDATE
        )

    @property
    def preserved_evidence_count(self) -> int:
        return sum(
            1
            for value
            in self.requirements
            if value.disposition
            is AndroidBootstrapEnvironmentRequirementDisposition
            .PRESERVED_EVIDENCE
        )

    @property
    def unresolved_count(self) -> int:
        return sum(
            1
            for value
            in self.requirements
            if value.disposition
            is AndroidBootstrapEnvironmentRequirementDisposition
            .UNRESOLVED
        )


class AndroidBootstrapEnvironmentPlanner:

    def __init__(
        self,
        *,
        hardware: str | None = None,
    ) -> None:
        """
        Configure Bootstrap-owned environment derivation.

        An explicitly supplied hardware value always overrides the development
        default. No canonical Parsing object is mutated.
        """
        self.configuration = (
            AndroidBootstrapEnvironmentConfiguration()
            if hardware is None
            else AndroidBootstrapEnvironmentConfiguration(
                hardware=hardware,
            )
        )

    """
    Derive the initial minimal-environment requirement surface from
    canonical Boot Image ramdisk interpretation.

    This stage performs classification and conservation only.

    It does not:
      - copy the factory ramdisk wholesale,
      - select final executable/library closure,
      - synthesize /init,
      - infer device-specific policy,
      - materialize a CPIO archive,
      - invoke Boot Image realization,
      - invoke fastboot.
    """

    _REQUIRED_KINDS = frozenset(
        (
            AndroidBootImageCpioEntryKind.INIT_BINARY,
            AndroidBootImageCpioEntryKind.INIT_CONFIGURATION,
            AndroidBootImageCpioEntryKind.FSTAB_CONFIGURATION,
            AndroidBootImageCpioEntryKind.UEVENTD_CONFIGURATION,
            AndroidBootImageCpioEntryKind.KERNEL_MODULE,
            AndroidBootImageCpioEntryKind
            .KERNEL_MODULE_CONFIGURATION,
        )
    )

    _AVAILABLE_KINDS = frozenset(
        (
            AndroidBootImageCpioEntryKind.DIRECTORY,
            AndroidBootImageCpioEntryKind.SYMLINK,
            AndroidBootImageCpioEntryKind.CHARACTER_DEVICE,
            AndroidBootImageCpioEntryKind.BLOCK_DEVICE,
            AndroidBootImageCpioEntryKind.FIFO,
            AndroidBootImageCpioEntryKind.SOCKET,
            AndroidBootImageCpioEntryKind.EXECUTABLE,
            AndroidBootImageCpioEntryKind.SHARED_LIBRARY,
        )
    )

    _STRUCTURAL_KINDS = frozenset(
        (
            AndroidBootImageCpioEntryKind.DIRECTORY,
            AndroidBootImageCpioEntryKind.SYMLINK,
            AndroidBootImageCpioEntryKind.CHARACTER_DEVICE,
            AndroidBootImageCpioEntryKind.BLOCK_DEVICE,
            AndroidBootImageCpioEntryKind.FIFO,
            AndroidBootImageCpioEntryKind.SOCKET,
        )
    )

    @classmethod
    def _classify_kind(
        cls,
        entry: AndroidBootImageCpioEntryInterpretation,
    ) -> AndroidBootstrapEnvironmentRequirementKind:
        kind = entry.kind

        mapping = {
            AndroidBootImageCpioEntryKind.INIT_BINARY:
                AndroidBootstrapEnvironmentRequirementKind
                .INIT_BINARY,

            AndroidBootImageCpioEntryKind.INIT_CONFIGURATION:
                AndroidBootstrapEnvironmentRequirementKind
                .INIT_CONFIGURATION,

            AndroidBootImageCpioEntryKind.FSTAB_CONFIGURATION:
                AndroidBootstrapEnvironmentRequirementKind
                .FSTAB_CONFIGURATION,

            AndroidBootImageCpioEntryKind.UEVENTD_CONFIGURATION:
                AndroidBootstrapEnvironmentRequirementKind
                .UEVENTD_CONFIGURATION,

            AndroidBootImageCpioEntryKind.KERNEL_MODULE:
                AndroidBootstrapEnvironmentRequirementKind
                .KERNEL_MODULE,

            AndroidBootImageCpioEntryKind
            .KERNEL_MODULE_CONFIGURATION:
                AndroidBootstrapEnvironmentRequirementKind
                .KERNEL_MODULE_CONFIGURATION,

            AndroidBootImageCpioEntryKind.EXECUTABLE:
                AndroidBootstrapEnvironmentRequirementKind
                .EXECUTABLE,

            AndroidBootImageCpioEntryKind.SHARED_LIBRARY:
                AndroidBootstrapEnvironmentRequirementKind
                .SHARED_LIBRARY,
        }

        if kind in mapping:
            return mapping[kind]

        if kind in cls._STRUCTURAL_KINDS:
            return (
                AndroidBootstrapEnvironmentRequirementKind
                .STRUCTURAL
            )

        if kind is AndroidBootImageCpioEntryKind.OTHER_FILE:
            return (
                AndroidBootstrapEnvironmentRequirementKind
                .RESOURCE
            )

        return (
            AndroidBootstrapEnvironmentRequirementKind
            .UNCLASSIFIED
        )

    @classmethod
    def _classify_disposition(
        cls,
        entry: AndroidBootImageCpioEntryInterpretation,
    ) -> AndroidBootstrapEnvironmentRequirementDisposition:
        if entry.kind in cls._REQUIRED_KINDS:
            return (
                AndroidBootstrapEnvironmentRequirementDisposition
                .REQUIRED_CANDIDATE
            )

        if entry.kind in cls._AVAILABLE_KINDS:
            return (
                AndroidBootstrapEnvironmentRequirementDisposition
                .AVAILABLE_CANDIDATE
            )

        if entry.kind is AndroidBootImageCpioEntryKind.OTHER_FILE:
            return (
                AndroidBootstrapEnvironmentRequirementDisposition
                .PRESERVED_EVIDENCE
            )

        return (
            AndroidBootstrapEnvironmentRequirementDisposition
            .UNRESOLVED
        )

    @staticmethod
    def _normalize_path(
        value,
    ) -> PurePosixPath:
        if hasattr(
            value,
            "as_posix",
        ):
            value = value.as_posix()

        return PurePosixPath(
            "/"
            + str(
                value
            ).lstrip(
                "/"
            )
        )

    def _runtime_support_binding_candidates(
        self,
        *,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        source,
    ) -> tuple[
        AndroidBootImageCpioEntryInterpretation,
        ...,
    ]:
        if source.source is not None:
            exact = tuple(
                entry
                for entry
                in ramdisk.cpio_entries
                if entry.associated_source
                is source.source
            )

            if exact:
                return exact

        if source.android_path is None:
            return ()

        wanted = self._normalize_path(
            source.android_path
        )

        return tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if (
                self._normalize_path(
                    entry.entry.path
                )
                == wanted
            )
        )

    def _vintf_binding(
        self,
        *,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        source: ParsedAndroidVintfSource,
    ) -> AndroidBootstrapVintfBinding:
        candidates = self._runtime_support_binding_candidates(
            ramdisk=ramdisk,
            source=source,
        )

        if len(
            candidates
        ) == 1:
            return AndroidBootstrapVintfBinding(
                source=source,
                resolution=(
                    AndroidBootstrapRuntimeSupportResolution.RESOLVED
                ),
                entry=candidates[0],
                candidates=candidates,
            )

        if not candidates:
            return AndroidBootstrapVintfBinding(
                source=source,
                resolution=(
                    AndroidBootstrapRuntimeSupportResolution.UNRESOLVED
                ),
            )

        return AndroidBootstrapVintfBinding(
            source=source,
            resolution=(
                AndroidBootstrapRuntimeSupportResolution.AMBIGUOUS
            ),
            candidates=candidates,
        )

    def _selinux_binding(
        self,
        *,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        source: ParsedAndroidSelinuxSource,
    ) -> AndroidBootstrapSelinuxBinding:
        candidates = self._runtime_support_binding_candidates(
            ramdisk=ramdisk,
            source=source,
        )

        if len(
            candidates
        ) == 1:
            return AndroidBootstrapSelinuxBinding(
                source=source,
                resolution=(
                    AndroidBootstrapRuntimeSupportResolution.RESOLVED
                ),
                entry=candidates[0],
                candidates=candidates,
            )

        if not candidates:
            return AndroidBootstrapSelinuxBinding(
                source=source,
                resolution=(
                    AndroidBootstrapRuntimeSupportResolution.UNRESOLVED
                ),
            )

        return AndroidBootstrapSelinuxBinding(
            source=source,
            resolution=(
                AndroidBootstrapRuntimeSupportResolution.AMBIGUOUS
            ),
            candidates=candidates,
        )

    def _identity_index(
        self,
        *,
        ramdisk_index: int,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        parsing,
    ) -> AndroidBootstrapEnvironmentIdentityIndex:
        source_bindings = tuple(
            AndroidBootstrapEnvironmentSourceBinding(
                entry=entry,
                source=entry.associated_source,
            )
            for entry
            in ramdisk.cpio_entries
            if entry.associated_source is not None
        )

        local_elfs = tuple(
            elf
            for elf
            in parsing.elf.elf_files
            if (
                elf.source.is_filesystem_backed
                and elf.source.filesystem_source
                is ramdisk.filesystem_source
            )
        )

        elf_bindings = []

        for elf in local_elfs:
            elf_path = self._normalize_path(
                elf.source.android_path
            )

            candidates = tuple(
                entry
                for entry
                in ramdisk.cpio_entries
                if (
                    self._normalize_path(
                        entry.entry.path
                    )
                    == elf_path
                )
            )

            if len(
                candidates
            ) == 1:
                elf_bindings.append(
                    AndroidBootstrapEnvironmentElfBinding(
                        elf=elf,
                        resolution=(
                            AndroidBootstrapEnvironmentElfResolution
                            .RESOLVED
                        ),
                        entry=candidates[0],
                        candidates=candidates,
                    )
                )

            elif not candidates:
                elf_bindings.append(
                    AndroidBootstrapEnvironmentElfBinding(
                        elf=elf,
                        resolution=(
                            AndroidBootstrapEnvironmentElfResolution
                            .UNRESOLVED
                        ),
                        entry=None,
                        candidates=(),
                    )
                )

            else:
                elf_bindings.append(
                    AndroidBootstrapEnvironmentElfBinding(
                        elf=elf,
                        resolution=(
                            AndroidBootstrapEnvironmentElfResolution
                            .AMBIGUOUS
                        ),
                        entry=None,
                        candidates=candidates,
                    )
                )

        local_vintf = tuple(
            source
            for source
            in parsing.filesystem.vintf_documents
            if source.filesystem_source
            is ramdisk.filesystem_source
        )

        vintf_bindings = tuple(
            self._vintf_binding(
                ramdisk=ramdisk,
                source=source,
            )
            for source
            in local_vintf
        )

        local_selinux = tuple(
            source
            for source
            in parsing.filesystem.selinux_sources
            if source.filesystem_source
            is ramdisk.filesystem_source
        )

        selinux_bindings = tuple(
            self._selinux_binding(
                ramdisk=ramdisk,
                source=source,
            )
            for source
            in local_selinux
        )

        return AndroidBootstrapEnvironmentIdentityIndex(
            ramdisk_index=ramdisk_index,
            ramdisk=ramdisk,
            source_bindings=source_bindings,
            elf_bindings=tuple(
                elf_bindings
            ),
            vintf_bindings=vintf_bindings,
            selinux_bindings=selinux_bindings,
        )

    @staticmethod
    def _is_literal_android_path(
        value: str,
    ) -> bool:
        if (
            not isinstance(
                value,
                str,
            )
            or not value.startswith(
                "/"
            )
        ):
            return False

        return not any(
            marker in value
            for marker
            in (
                "$",
                "{",
                "}",
                "*",
                "?",
                "[",
                "]",
            )
        )

    @staticmethod
    def _common_path_prefix_depth(
        left: PurePosixPath,
        right: PurePosixPath,
    ) -> int:
        left_parts = left.parts[
            1:
        ]
        right_parts = right.parts[
            1:
        ]

        count = 0

        for left_part, right_part in zip(
            left_parts,
            right_parts,
        ):
            if left_part != right_part:
                break

            count += 1

        return count

    def _select_elf_provider_by_path_domain(
        self,
        *,
        owner: AndroidBootstrapEnvironmentElfBinding,
        candidates: tuple[
            AndroidBootstrapEnvironmentElfBinding,
            ...,
        ],
    ) -> (
        AndroidBootstrapEnvironmentElfBinding
        | None
    ):
        if not candidates:
            return None

        owner_path = self._normalize_path(
            owner.entry.entry.path
        )

        scored = tuple(
            (
                self._common_path_prefix_depth(
                    owner_path,
                    self._normalize_path(
                        candidate.entry.entry.path
                    ),
                ),
                candidate,
            )
            for candidate
            in candidates
            if candidate.entry is not None
        )

        if not scored:
            return None

        best_depth = max(
            depth
            for depth, _
            in scored
        )

        best = tuple(
            candidate
            for depth, candidate
            in scored
            if depth == best_depth
        )

        if (
            best_depth == 0
            or len(
                best
            ) != 1
        ):
            return None

        return best[0]

    def _root_init_binary(
        self,
        ramdisk: AndroidBootImageRamdiskInterpretation,
    ) -> AndroidBootstrapRootInitBinaryResolution:
        candidates = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if (
                self._normalize_path(
                    entry.entry.path
                )
                == PurePosixPath(
                    "/init"
                )
                and entry.kind
                is AndroidBootImageCpioEntryKind.INIT_BINARY
            )
        )

        if len(
            candidates
        ) == 1:
            return AndroidBootstrapRootInitBinaryResolution(
                resolution=(
                    AndroidBootstrapInitResolution.RESOLVED
                ),
                entry=candidates[0],
                candidates=candidates,
            )

        if not candidates:
            return AndroidBootstrapRootInitBinaryResolution(
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
            )

        return AndroidBootstrapRootInitBinaryResolution(
            resolution=(
                AndroidBootstrapInitResolution.AMBIGUOUS
            ),
            candidates=candidates,
        )

    @staticmethod
    def _unselected_init_source(
    ) -> tuple[
        AndroidBootstrapInitResolution,
        ParsedAndroidInitSource | None,
        tuple[
            ParsedAndroidInitSource,
            ...,
        ],
    ]:
        """
        Non-selected ramdisks do not independently invent an INIT root.

        Environment-root selection owns the canonical INIT spine decision
        across the complete boot-family population.
        """
        return (
            AndroidBootstrapInitResolution.UNRESOLVED,
            None,
            (),
        )

    @staticmethod
    def _canonical_property_value(
        parsing: AndroidParsingResult,
        key: str,
    ) -> str | None:
        """
        Resolve one direct canonical Parsing property only when every
        declaration agrees on one non-empty value.

        Every declaration remains owned by Parsing. Bootstrap consumes the
        concordant value only; it does not collapse or mutate provenance.
        """
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if (
            not isinstance(
                key,
                str,
            )
            or not key
        ):
            raise ValueError(
                "property key must be a non-empty string"
            )

        declarations = tuple(
            declaration
            for property_file
            in parsing.filesystem.property_files
            for declaration
            in property_file.declarations
            if declaration.key == key
        )

        if not declarations:
            return None

        values = tuple(
            dict.fromkeys(
                declaration.value
                for declaration
                in declarations
            )
        )

        if (
            len(
                values
            )
            != 1
            or not values[0]
        ):
            return None

        return values[0]

    def _expand_init_import_path(
        self,
        path: str,
        *,
        board_platform: str | None,
    ) -> str:
        """
        Expand only Bootstrap-owned INIT property bindings.

        ro.hardware is supplied by explicit Bootstrap configuration and
        currently defaults to tangorpro.

        ro.board.platform is consumed only when canonical Parsing property
        declarations reconcile to exactly one value.

        Unsupported or unresolved expressions remain untouched so the
        existing literal resolver continues to classify them explicitly as
        non-literal/unresolved.
        """
        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "INIT import path must be a string"
            )

        expanded = path.replace(
            "${ro.hardware}",
            self.configuration.hardware,
        )

        if board_platform is not None:
            expanded = expanded.replace(
                "${ro.board.platform}",
                board_platform,
            )

        return expanded

    def _resolve_init_import_with_properties(
        self,
        *,
        board_platform: str | None,
        **kwargs,
    ) -> AndroidBootstrapInitImportResolution:
        """
        Apply Bootstrap property bindings before the existing literal INIT
        import resolver.

        The final resolution is rebound to the exact original canonical
        AndroidInitImport declaration so Parsing identity is never replaced
        by the temporary expanded declaration.
        """
        declaration = kwargs.get(
            "declaration"
        )

        if declaration is None:
            raise ValueError(
                "INIT import resolution requires declaration"
            )

        original_declaration = declaration

        expanded_path = (
            self._expand_init_import_path(
                declaration.path,
                board_platform=board_platform,
            )
        )

        if expanded_path != declaration.path:
            kwargs[
                "declaration"
            ] = replace(
                declaration,
                path=expanded_path,
            )

        resolution = self._resolve_init_import(
            **kwargs
        )

        if resolution.declaration is original_declaration:
            return resolution

        return replace(
            resolution,
            declaration=original_declaration,
        )

    def _resolve_init_import(
        self,
        *,
        owner: ParsedAndroidInitSource,
        declaration: AndroidInitImport,
        ramdisk: AndroidBootImageRamdiskInterpretation,
    ) -> AndroidBootstrapInitImportResolution:
        raw_path = declaration.path

        if not self._is_literal_android_path(
            raw_path
        ):
            return AndroidBootstrapInitImportResolution(
                owner=owner,
                declaration=declaration,
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
                reason=(
                    "non_literal_import_path"
                ),
            )

        wanted = self._normalize_path(
            raw_path
        )

        candidates = tuple(
            source
            for source
            in ramdisk.init_files
            if (
                source.android_path is not None
                and self._normalize_path(
                    source.android_path
                )
                == wanted
            )
        )

        if len(
            candidates
        ) == 1:
            return AndroidBootstrapInitImportResolution(
                owner=owner,
                declaration=declaration,
                resolution=(
                    AndroidBootstrapInitResolution.RESOLVED
                ),
                source=candidates[0],
                candidates=candidates,
            )

        if not candidates:
            return AndroidBootstrapInitImportResolution(
                owner=owner,
                declaration=declaration,
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
                reason=(
                    "literal_import_not_present_in_ramdisk"
                ),
            )

        return AndroidBootstrapInitImportResolution(
            owner=owner,
            declaration=declaration,
            resolution=(
                AndroidBootstrapInitResolution.AMBIGUOUS
            ),
            candidates=candidates,
            reason=(
                "multiple_ramdisk_init_sources_match_import"
            ),
        )

    def _resolve_service_executable(
        self,
        *,
        owner: ParsedAndroidInitSource,
        service: AndroidInitService,
        ramdisk: AndroidBootImageRamdiskInterpretation,
    ) -> AndroidBootstrapInitServiceExecutableResolution:
        executable = service.executable

        if (
            service.name
            in self.configuration.excluded_init_services
        ):
            return AndroidBootstrapInitServiceExecutableResolution(
                owner=owner,
                service=service,
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
                disposition=(
                    AndroidBootstrapInitServiceDisposition.EXCLUDED
                ),
                reason=(
                    "excluded_by_bootstrap_environment_policy"
                ),
            )

        if not self._is_literal_android_path(
            executable
        ):
            return AndroidBootstrapInitServiceExecutableResolution(
                owner=owner,
                service=service,
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
                reason=(
                    "non_literal_service_executable_path"
                ),
            )

        wanted = self._normalize_path(
            executable
        )

        candidates = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if (
                self._normalize_path(
                    entry.entry.path
                )
                == wanted
            )
        )

        if len(
            candidates
        ) == 1:
            return AndroidBootstrapInitServiceExecutableResolution(
                owner=owner,
                service=service,
                resolution=(
                    AndroidBootstrapInitResolution.RESOLVED
                ),
                entry=candidates[0],
                candidates=candidates,
            )

        if not candidates:
            return AndroidBootstrapInitServiceExecutableResolution(
                owner=owner,
                service=service,
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
                reason=(
                    "service_executable_not_present_in_ramdisk"
                ),
            )

        return AndroidBootstrapInitServiceExecutableResolution(
            owner=owner,
            service=service,
            resolution=(
                AndroidBootstrapInitResolution.AMBIGUOUS
            ),
            candidates=candidates,
            reason=(
                "multiple_ramdisk_cpio_entries_match_service_executable"
            ),
        )

    def _environment_root_candidate(
        self,
        *,
        ramdisk_index: int,
        ramdisk: AndroidBootImageRamdiskInterpretation,
    ) -> AndroidBootstrapEnvironmentRootCandidate:
        root_matches = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if (
                self._normalize_path(
                    entry.entry.path
                )
                == PurePosixPath(
                    "/init"
                )
            )
        )

        root_entry = (
            root_matches[0]
            if len(
                root_matches
            ) == 1
            else None
        )

        root_target_path = None
        init_binary_entry = None
        reasons = []

        if not root_matches:
            reasons.append(
                "root_init_absent"
            )

        elif len(
            root_matches
        ) > 1:
            reasons.append(
                "root_init_ambiguous"
            )

        elif (
            root_entry.kind
            is AndroidBootImageCpioEntryKind.INIT_BINARY
        ):
            root_target_path = PurePosixPath(
                "/init"
            )
            init_binary_entry = root_entry

        elif (
            root_entry.kind
            is AndroidBootImageCpioEntryKind.SYMLINK
        ):
            try:
                raw_target = (
                    root_entry.entry.data
                    .decode(
                        "utf-8",
                        errors="strict",
                    )
                )
            except UnicodeDecodeError:
                reasons.append(
                    "root_init_symlink_target_not_utf8"
                )
            else:
                if not raw_target.startswith(
                    "/"
                ):
                    reasons.append(
                        "root_init_symlink_target_not_absolute"
                    )
                else:
                    root_target_path = (
                        self._normalize_path(
                            raw_target
                        )
                    )

                    target_matches = tuple(
                        entry
                        for entry
                        in ramdisk.cpio_entries
                        if (
                            self._normalize_path(
                                entry.entry.path
                            )
                            == root_target_path
                            and entry.kind
                            is AndroidBootImageCpioEntryKind.INIT_BINARY
                        )
                    )

                    if len(
                        target_matches
                    ) == 1:
                        init_binary_entry = (
                            target_matches[0]
                        )

                    elif not target_matches:
                        reasons.append(
                            "root_init_symlink_target_missing"
                        )

                    else:
                        reasons.append(
                            "root_init_symlink_target_ambiguous"
                        )

        else:
            reasons.append(
                "root_init_not_binary_or_symlink"
            )

        init_spine_candidates = tuple(
            source
            for source
            in ramdisk.init_files
            if (
                source.android_path is not None
                and self._normalize_path(
                    source.android_path
                )
                == PurePosixPath(
                    "/system/etc/init/hw/init.rc"
                )
            )
        )

        if len(
            init_spine_candidates
        ) == 1:
            init_spine_resolution = (
                AndroidBootstrapInitResolution.RESOLVED
            )
            init_spine = (
                init_spine_candidates[0]
            )

        elif not init_spine_candidates:
            init_spine_resolution = (
                AndroidBootstrapInitResolution.UNRESOLVED
            )
            init_spine = None
            reasons.append(
                "android_init_spine_absent"
            )

        else:
            init_spine_resolution = (
                AndroidBootstrapInitResolution.AMBIGUOUS
            )
            init_spine = None
            reasons.append(
                "android_init_spine_ambiguous"
            )

        if not ramdisk.fstabs:
            reasons.append(
                "fstab_absent"
            )

        if not ramdisk.ueventd_files:
            reasons.append(
                "ueventd_absent"
            )

        services = tuple(
            service
            for source
            in ramdisk.init_files
            for service
            in source.services
        )

        def service_count(
            executable_name: str,
        ) -> int:
            return sum(
                1
                for service
                in services
                if (
                    isinstance(
                        service.executable,
                        str,
                    )
                    and self._normalize_path(
                        service.executable
                    ).name
                    == executable_name
                )
            )

        recovery_service_count = (
            service_count(
                "recovery"
            )
        )

        adb_service_count = (
            service_count(
                "adbd"
            )
        )

        fastboot_service_count = (
            service_count(
                "fastbootd"
            )
        )

        eligible = (
            root_entry is not None
            and init_binary_entry is not None
            and (
                init_spine_resolution
                is AndroidBootstrapInitResolution.RESOLVED
            )
            and bool(
                ramdisk.fstabs
            )
            and bool(
                ramdisk.ueventd_files
            )
        )

        return AndroidBootstrapEnvironmentRootCandidate(
            ramdisk_index=ramdisk_index,
            ramdisk=ramdisk,
            root_entry=root_entry,
            root_target_path=root_target_path,
            init_binary_entry=init_binary_entry,
            init_spine_resolution=(
                init_spine_resolution
            ),
            init_spine=init_spine,
            init_spine_candidates=(
                init_spine_candidates
            ),
            recovery_service_count=(
                recovery_service_count
            ),
            adb_service_count=(
                adb_service_count
            ),
            fastboot_service_count=(
                fastboot_service_count
            ),
            eligible=eligible,
            reasons=tuple(
                reasons
            ),
        )

    def _environment_root_selection(
        self,
        interpretation: AndroidBootImageInterpretationResult,
    ) -> AndroidBootstrapEnvironmentRootSelection:
        all_candidates = tuple(
            self._environment_root_candidate(
                ramdisk_index=ramdisk_index,
                ramdisk=ramdisk,
            )
            for ramdisk_index, ramdisk
            in enumerate(
                interpretation.ramdisks
            )
        )

        candidates = tuple(
            candidate
            for candidate
            in all_candidates
            if candidate.eligible
        )

        if len(
            candidates
        ) == 1:
            return AndroidBootstrapEnvironmentRootSelection(
                resolution=(
                    AndroidBootstrapInitResolution.RESOLVED
                ),
                candidate=candidates[0],
                candidates=candidates,
                all_candidates=all_candidates,
            )

        if not candidates:
            return AndroidBootstrapEnvironmentRootSelection(
                resolution=(
                    AndroidBootstrapInitResolution.UNRESOLVED
                ),
                all_candidates=all_candidates,
            )

        return AndroidBootstrapEnvironmentRootSelection(
            resolution=(
                AndroidBootstrapInitResolution.AMBIGUOUS
            ),
            candidates=candidates,
            all_candidates=all_candidates,
        )

    _STANDARD_INIT_DIRECTORIES = (
        PurePosixPath(
            "/system/etc/init"
        ),
        PurePosixPath(
            "/system_ext/etc/init"
        ),
        PurePosixPath(
            "/vendor/etc/init"
        ),
        PurePosixPath(
            "/odm/etc/init"
        ),
        PurePosixPath(
            "/product/etc/init"
        ),
    )

    @classmethod
    def _is_standard_directory_loaded_init_source(
        cls,
        source: ParsedAndroidInitSource,
    ) -> bool:
        android_path = source.android_path

        if android_path is None:
            return False

        path = cls._normalize_path(
            android_path
        )

        return (
            path.suffix == ".rc"
            and path.parent
            in cls._STANDARD_INIT_DIRECTORIES
        )

    def _init_closure(
        self,
        *,
        ramdisk_index: int,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        environment_candidate: (
            AndroidBootstrapEnvironmentRootCandidate
            | None
        ) = None,
        board_platform: str | None = None,
    ) -> AndroidBootstrapInitClosure:
        if environment_candidate is not None:
            if (
                environment_candidate.ramdisk_index
                != ramdisk_index
            ):
                raise ValueError(
                    "selected Bootstrap environment candidate "
                    "ramdisk index does not match INIT closure"
                )

            if (
                environment_candidate.ramdisk
                is not ramdisk
            ):
                raise ValueError(
                    "selected Bootstrap environment candidate "
                    "must retain exact INIT-closure ramdisk identity"
                )

            if environment_candidate.root_entry is None:
                raise ValueError(
                    "selected Bootstrap environment root must "
                    "retain an exact /init entry"
                )

            if environment_candidate.init_binary_entry is None:
                raise ValueError(
                    "selected Bootstrap environment root must "
                    "retain an exact init-binary target"
                )

            if (
                environment_candidate.init_spine_resolution
                is not AndroidBootstrapInitResolution.RESOLVED
                or environment_candidate.init_spine is None
            ):
                raise ValueError(
                    "selected Bootstrap environment root must "
                    "retain one resolved canonical INIT spine"
                )

            root_binary = (
                AndroidBootstrapRootInitBinaryResolution(
                    resolution=(
                        AndroidBootstrapInitResolution.RESOLVED
                    ),
                    entry=(
                        environment_candidate.root_entry
                    ),
                    candidates=(
                        environment_candidate.root_entry,
                    ),
                )
            )

            root_source_resolution = (
                AndroidBootstrapInitResolution.RESOLVED
            )
            root_source = (
                environment_candidate.init_spine
            )
            root_source_candidates = (
                environment_candidate.init_spine,
            )

        else:
            root_binary = self._root_init_binary(
                ramdisk
            )

            (
                root_source_resolution,
                root_source,
                root_source_candidates,
            ) = self._unselected_init_source()

        selected = []
        import_resolutions = []
        selected_ids = set()

        def select_source(
            source: ParsedAndroidInitSource,
            role: AndroidBootstrapInitSourceRole,
        ) -> bool:
            source_id = id(
                source
            )

            if source_id in selected_ids:
                return False

            selected_ids.add(
                source_id
            )

            selected.append(
                AndroidBootstrapInitSourceSelection(
                    source=source,
                    role=role,
                )
            )

            return True

        def traverse_imports(
            queue: list[
                ParsedAndroidInitSource
            ],
        ) -> None:
            while queue:
                owner = queue.pop(
                    0
                )

                for declaration in owner.imports:
                    resolution = (
                        self._resolve_init_import_with_properties(
                            board_platform=board_platform,
                            owner=owner,
                            declaration=declaration,
                            ramdisk=ramdisk,
                        )
                    )

                    import_resolutions.append(
                        resolution
                    )

                    if (
                        resolution.resolution
                        is not AndroidBootstrapInitResolution.RESOLVED
                        or resolution.source is None
                    ):
                        continue

                    if select_source(
                        resolution.source,
                        AndroidBootstrapInitSourceRole.IMPORTED,
                    ):
                        queue.append(
                            resolution.source
                        )

        if root_source is not None:
            select_source(
                root_source,
                AndroidBootstrapInitSourceRole.ROOT,
            )

            traverse_imports(
                [
                    root_source,
                ]
            )

            directory_queue = []

            for source in ramdisk.init_files:
                if not self._is_standard_directory_loaded_init_source(
                    source
                ):
                    continue

                if select_source(
                    source,
                    AndroidBootstrapInitSourceRole.DIRECTORY_LOADED,
                ):
                    directory_queue.append(
                        source
                    )

            traverse_imports(
                directory_queue
            )

        service_executables = tuple(
            self._resolve_service_executable(
                owner=selection.source,
                service=service,
                ramdisk=ramdisk,
            )
            for selection
            in selected
            for service
            in selection.source.services
        )

        return AndroidBootstrapInitClosure(
            ramdisk_index=ramdisk_index,
            ramdisk=ramdisk,
            root_binary=root_binary,
            root_source_resolution=(
                root_source_resolution
            ),
            root_source=root_source,
            root_source_candidates=(
                root_source_candidates
            ),
            selected_sources=tuple(
                selected
            ),
            imports=tuple(
                import_resolutions
            ),
            service_executables=(
                service_executables
            ),
        )

    def _runtime_consumer_targets(
        self,
        *,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        identity_index: AndroidBootstrapEnvironmentIdentityIndex,
        environment_candidate: AndroidBootstrapEnvironmentRootCandidate,
        init_closure: AndroidBootstrapInitClosure,
    ) -> tuple[
        tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ],
        tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ],
        tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ],
    ]:
        """
        Discover exact ramdisk-local runtime consumers from canonical
        executable payload evidence.

        This is intentionally narrower than arbitrary binary-string
        dependency guessing. Only complete canonical Android paths are
        accepted, with CPIO symlink-prefix aliases resolved back to exact
        canonical entries.

        Returns:
          runtime executables,
          exact runtime resources,
          explicitly referenced resource subtrees.
        """

        by_path = {
            self._normalize_path(
                entry.entry.path
            ): entry
            for entry
            in ramdisk.cpio_entries
        }

        symlink_prefixes = []

        for entry in ramdisk.cpio_entries:
            if (
                entry.kind
                is not AndroidBootImageCpioEntryKind.SYMLINK
            ):
                continue

            link_path = self._normalize_path(
                entry.entry.path
            )

            try:
                raw_target = entry.entry.data.decode(
                    "utf-8",
                    errors="strict",
                )
            except UnicodeDecodeError:
                continue

            target_path = PurePosixPath(
                raw_target
            )

            if not target_path.is_absolute():
                target_path = (
                    link_path.parent
                    / target_path
                )

            normalized_target = self._normalize_path(
                target_path
            )

            target_entry = by_path.get(
                normalized_target
            )

            # Reverse aliasing is valid only for a symlink that aliases
            # an existing canonical directory. This permits namespace
            # aliases such as /etc -> /system/etc without collapsing
            # executable applet symlinks onto their multicall binary.
            if (
                target_entry is None
                or target_entry.kind
                is not AndroidBootImageCpioEntryKind.DIRECTORY
            ):
                continue

            symlink_prefixes.append(
                (
                    link_path,
                    normalized_target,
                )
            )

        def reference_paths(
            canonical_path: PurePosixPath,
        ) -> tuple[
            PurePosixPath,
            ...,
        ]:
            values = [
                canonical_path,
            ]

            for alias_path, target_path in symlink_prefixes:
                try:
                    relative = canonical_path.relative_to(
                        target_path
                    )
                except ValueError:
                    continue

                aliased = self._normalize_path(
                    alias_path
                    / relative
                )

                if aliased not in values:
                    values.append(
                        aliased
                    )

            return tuple(
                values
            )

        def resolve_entry(
            entry: AndroidBootImageCpioEntryInterpretation,
        ) -> AndroidBootImageCpioEntryInterpretation:
            current = entry
            visited = set()

            while (
                current.kind
                is AndroidBootImageCpioEntryKind.SYMLINK
            ):
                current_path = self._normalize_path(
                    current.entry.path
                )

                if current_path in visited:
                    break

                visited.add(
                    current_path
                )

                try:
                    raw_target = current.entry.data.decode(
                        "utf-8",
                        errors="strict",
                    )
                except UnicodeDecodeError:
                    break

                target_path = PurePosixPath(
                    raw_target
                )

                if not target_path.is_absolute():
                    target_path = (
                        current_path.parent
                        / target_path
                    )

                target = by_path.get(
                    self._normalize_path(
                        target_path
                    )
                )

                if target is None:
                    break

                current = target

            return current

        elf_by_entry_id = {
            id(
                binding.entry
            ): binding.elf
            for binding
            in identity_index.elf_bindings
            if (
                binding.resolution
                is AndroidBootstrapEnvironmentElfResolution.RESOLVED
                and binding.entry is not None
            )
        }

        seeds = []

        if environment_candidate.init_binary_entry is not None:
            seed = resolve_entry(
                environment_candidate.init_binary_entry
            )

            if seed.kind in {
                AndroidBootImageCpioEntryKind.INIT_BINARY,
                AndroidBootImageCpioEntryKind.EXECUTABLE,
            }:
                seeds.append(
                    seed
                )

        for service_resolution in init_closure.service_executables:
            if (
                service_resolution.disposition
                is not AndroidBootstrapInitServiceDisposition.REQUIRED
                or service_resolution.entry is None
            ):
                continue

            seed = resolve_entry(
                service_resolution.entry
            )

            if seed.kind not in {
                AndroidBootImageCpioEntryKind.INIT_BINARY,
                AndroidBootImageCpioEntryKind.EXECUTABLE,
            }:
                continue

            if not any(
                seed is existing
                for existing
                in seeds
            ):
                seeds.append(
                    seed
                )

        executable_ids = set()
        resource_ids = set()
        subtree_ids = set()

        queue = list(
            seeds
        )

        while queue:
            consumer = queue.pop(
                0
            )

            consumer_id = id(
                consumer
            )

            if consumer_id in executable_ids:
                continue

            executable_ids.add(
                consumer_id
            )

            payload = consumer.entry.data

            # Runtime-consumer discovery accepts only complete printable
            # strings equal to a canonical or canonical-alias Android path.
            #
            # Raw byte substring matching is intentionally forbidden here:
            # a reference to /system/etc/foo must not establish /system/etc
            # itself as a referenced directory.
            import re

            printable_strings = {
                match.group().decode(
                    "ascii",
                    errors="strict",
                )
                for match
                in re.finditer(
                    rb"[\x20-\x7e]{4,}",
                    payload,
                )
            }

            consumer_elf = elf_by_entry_id.get(
                consumer_id
            )

            interpreter_path = (
                self._normalize_path(
                    consumer_elf.interpreter
                )
                if (
                    consumer_elf is not None
                    and consumer_elf.interpreter is not None
                )
                else None
            )

            for target_path, target in by_path.items():
                candidate_reference_paths = reference_paths(
                    target_path
                )

                matched_path = next(
                    (
                        value
                        for value
                        in candidate_reference_paths
                        if str(
                            value
                        ) in printable_strings
                    ),
                    None,
                )

                if matched_path is None:
                    continue

                if (
                    interpreter_path is not None
                    and target_path
                    == interpreter_path
                ):
                    continue

                if target.kind in {
                    AndroidBootImageCpioEntryKind.INIT_BINARY,
                    AndroidBootImageCpioEntryKind.EXECUTABLE,
                }:
                    if id(
                        target
                    ) not in executable_ids:
                        queue.append(
                            target
                        )

                    continue

                if (
                    target.kind
                    is AndroidBootImageCpioEntryKind.OTHER_FILE
                ):
                    resource_ids.add(
                        id(
                            target
                        )
                    )

                    continue

                if (
                    target.kind
                    is not AndroidBootImageCpioEntryKind.DIRECTORY
                ):
                    continue

                descendants = tuple(
                    entry
                    for entry
                    in ramdisk.cpio_entries
                    if (
                        self._normalize_path(
                            entry.entry.path
                        )
                        != target_path
                        and (
                            target_path
                            in self._normalize_path(
                                entry.entry.path
                            ).parents
                        )
                    )
                )

                payload_descendants = tuple(
                    entry
                    for entry
                    in descendants
                    if entry.kind
                    is not AndroidBootImageCpioEntryKind.DIRECTORY
                )

                if len(
                    payload_descendants
                ) < 2:
                    continue

                if not all(
                    entry.kind
                    is AndroidBootImageCpioEntryKind.OTHER_FILE
                    for entry
                    in payload_descendants
                ):
                    continue

                subtree_ids.add(
                    id(
                        target
                    )
                )

                for descendant in descendants:
                    subtree_ids.add(
                        id(
                            descendant
                        )
                    )

        runtime_executables = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) in executable_ids
            and not any(
                entry is seed
                for seed
                in seeds
            )
        )

        runtime_resources = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) in resource_ids
        )

        runtime_subtree = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) in subtree_ids
        )

        return (
            runtime_executables,
            runtime_resources,
            runtime_subtree,
        )

    def _elf_runtime_extensions(
        self,
        *,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        identity_index: AndroidBootstrapEnvironmentIdentityIndex,
        elf_closure: AndroidBootstrapElfClosure,
    ) -> tuple[
        tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ],
        tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ],
    ]:
        """
        Discover runtime requirements that ordinary DT_NEEDED traversal
        cannot express.

        Returns:
          dynamically referenced canonical ELF providers,
          exact canonical resources reached through directory aliases.
        """

        import re

        by_path = {
            self._normalize_path(
                entry.entry.path
            ): entry
            for entry
            in ramdisk.cpio_entries
        }

        resolved_elf_bindings = tuple(
            binding
            for binding
            in identity_index.elf_bindings
            if (
                binding.resolution
                is AndroidBootstrapEnvironmentElfResolution.RESOLVED
                and binding.entry is not None
            )
        )

        by_soname = {}

        for binding in resolved_elf_bindings:
            soname = binding.elf.soname

            if soname is None:
                continue

            by_soname.setdefault(
                soname,
                [],
            ).append(
                binding
            )

        selected_elf_ids = {
            id(
                binding.elf
            )
            for binding
            in elf_closure.elfs
        }

        # ----------------------------------------------------
        # Canonical directory aliases only.
        # ----------------------------------------------------

        directory_aliases = []

        for entry in ramdisk.cpio_entries:
            if (
                entry.kind
                is not AndroidBootImageCpioEntryKind.SYMLINK
            ):
                continue

            alias_path = self._normalize_path(
                entry.entry.path
            )

            try:
                raw_target = entry.entry.data.decode(
                    "utf-8",
                    errors="strict",
                )
            except UnicodeDecodeError:
                continue

            target_path = PurePosixPath(
                raw_target
            )

            if not target_path.is_absolute():
                target_path = (
                    alias_path.parent
                    / target_path
                )

            target_path = self._normalize_path(
                target_path
            )

            target_entry = by_path.get(
                target_path
            )

            if (
                target_entry is None
                or target_entry.kind
                is not AndroidBootImageCpioEntryKind.DIRECTORY
            ):
                continue

            directory_aliases.append(
                (
                    alias_path,
                    target_path,
                )
            )

        dynamic_provider_ids = set()
        resource_ids = set()

        for owner in elf_closure.elfs:
            if owner.entry is None:
                continue

            printable_strings = {
                match.group().decode(
                    "ascii",
                    errors="strict",
                )
                for match
                in re.finditer(
                    rb"[\x20-\x7e]{4,}",
                    owner.entry.entry.data,
                )
            }

            # ------------------------------------------------
            # Exact SONAME references outside DT_NEEDED.
            # ------------------------------------------------

            needed = set(
                owner.elf.needed
            )

            for soname in printable_strings:
                if (
                    soname in needed
                    or soname not in by_soname
                ):
                    continue

                candidates = tuple(
                    by_soname[
                        soname
                    ]
                )

                if len(
                    candidates
                ) == 1:
                    provider = candidates[0]
                else:
                    provider = (
                        self._select_elf_provider_by_path_domain(
                            owner=owner,
                            candidates=candidates,
                        )
                    )

                if (
                    provider is None
                    or provider.entry is None
                    or id(
                        provider.elf
                    ) in selected_elf_ids
                ):
                    continue

                dynamic_provider_ids.add(
                    id(
                        provider.entry
                    )
                )

            # ------------------------------------------------
            # Exact paths through canonical directory aliases.
            #
            # Example:
            #   canonical: /system/etc/cgroups.json
            #   alias:     /etc/cgroups.json
            # ------------------------------------------------

            for canonical_path, target in by_path.items():
                if (
                    target.kind
                    is not AndroidBootImageCpioEntryKind.OTHER_FILE
                ):
                    continue

                for alias_path, target_directory in directory_aliases:
                    try:
                        relative = canonical_path.relative_to(
                            target_directory
                        )
                    except ValueError:
                        continue

                    aliased_path = self._normalize_path(
                        alias_path
                        / relative
                    )

                    # Only an actual alternate alias is owned here.
                    if aliased_path == canonical_path:
                        continue

                    if str(
                        aliased_path
                    ) not in printable_strings:
                        continue

                    resource_ids.add(
                        id(
                            target
                        )
                    )

        dynamic_providers = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) in dynamic_provider_ids
        )

        resources = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) in resource_ids
        )

        return (
            dynamic_providers,
            resources,
        )

    def _environment_population(
        self,
        *,
        ramdisk_index: int,
        ramdisk: AndroidBootImageRamdiskInterpretation,
        identity_index: AndroidBootstrapEnvironmentIdentityIndex,
        environment_candidate: AndroidBootstrapEnvironmentRootCandidate,
        init_closure: AndroidBootstrapInitClosure,
        elf_closure: AndroidBootstrapElfClosure,
        runtime_consumer_executables: tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ] = (),
        runtime_consumer_resources: tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ] = (),
        runtime_consumer_subtree: tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ] = (),
        dynamic_elf_providers: tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ] = (),
        elf_runtime_resources: tuple[
            AndroidBootImageCpioEntryInterpretation,
            ...,
        ] = (),
    ) -> AndroidBootstrapEnvironmentPopulationPlan:
        if (
            identity_index.ramdisk_index
            != ramdisk_index
            or identity_index.ramdisk
            is not ramdisk
        ):
            raise ValueError(
                "Bootstrap environment population identity index must "
                "belong to the exact selected ramdisk"
            )

        reasons_by_entry_id = {}
        entries_by_id = {}

        def select(
            entry: AndroidBootImageCpioEntryInterpretation,
            reason: AndroidBootstrapEnvironmentPopulationReason,
        ) -> None:
            if not any(
                entry is canonical
                for canonical
                in ramdisk.cpio_entries
            ):
                raise ValueError(
                    "Bootstrap population may select only exact entries "
                    "from the chosen environment ramdisk"
                )

            entry_id = id(
                entry
            )

            entries_by_id[
                entry_id
            ] = entry

            reasons = reasons_by_entry_id.setdefault(
                entry_id,
                [],
            )

            if reason not in reasons:
                reasons.append(
                    reason
                )

        def exact_source_entry(
            source,
        ) -> AndroidBootImageCpioEntryInterpretation:
            model_source = getattr(
                source,
                "source",
                None,
            )

            candidates = tuple(
                entry
                for entry
                in ramdisk.cpio_entries
                if (
                    model_source is not None
                    and entry.associated_source
                    is model_source
                )
            )

            if len(
                candidates
            ) == 1:
                return candidates[0]

            if len(
                candidates
            ) > 1:
                raise ValueError(
                    "canonical model source maps to multiple CPIO entries"
                )

            android_path = getattr(
                source,
                "android_path",
                None,
            )

            if android_path is None:
                raise ValueError(
                    "selected canonical source has neither exact model "
                    "source association nor Android path"
                )

            wanted = self._normalize_path(
                android_path
            )

            candidates = tuple(
                entry
                for entry
                in ramdisk.cpio_entries
                if (
                    self._normalize_path(
                        entry.entry.path
                    )
                    == wanted
                )
            )

            if len(
                candidates
            ) != 1:
                raise ValueError(
                    "selected canonical source must resolve to exactly "
                    "one CPIO entry"
                )

            return candidates[0]

        # ----------------------------------------------------
        # Root /init and its exact resolved init binary.
        # ----------------------------------------------------

        if environment_candidate.root_entry is None:
            raise ValueError(
                "selected environment candidate must retain /init"
            )

        select(
            environment_candidate.root_entry,
            AndroidBootstrapEnvironmentPopulationReason.ROOT_INIT,
        )

        if environment_candidate.init_binary_entry is None:
            raise ValueError(
                "selected environment candidate must retain init binary"
            )

        select(
            environment_candidate.init_binary_entry,
            AndroidBootstrapEnvironmentPopulationReason.INIT_BINARY,
        )

        # ----------------------------------------------------
        # Selected INIT graph only.
        # ----------------------------------------------------

        for selection in init_closure.selected_sources:
            select(
                exact_source_entry(
                    selection.source
                ),
                AndroidBootstrapEnvironmentPopulationReason
                .INIT_CONFIGURATION,
            )

        # ----------------------------------------------------
        # All canonical fstab/ueventd sources belonging to the
        # selected recovery-capable ramdisk.
        #
        # We are selecting the complete config evidence of the
        # chosen environment here; later semantic reduction may
        # derive a smaller generated configuration.
        # ----------------------------------------------------

        for fstab in ramdisk.fstabs:
            select(
                exact_source_entry(
                    fstab
                ),
                AndroidBootstrapEnvironmentPopulationReason
                .FSTAB_CONFIGURATION,
            )

        for ueventd in ramdisk.ueventd_files:
            select(
                exact_source_entry(
                    ueventd
                ),
                AndroidBootstrapEnvironmentPopulationReason
                .UEVENTD_CONFIGURATION,
            )

        # ----------------------------------------------------
        # Canonical VINTF runtime manifest population.
        #
        # Android VINTF manifest fragments are runtime-loaded as
        # a manifest population rather than solely through INIT
        # service/interface references. Bootstrap therefore
        # preserves every exact canonical VINTF source belonging
        # to the selected recovery-capable ramdisk.
        #
        # Exact source -> CPIO identity is already established by
        # the generic Bootstrap identity index.
        # ----------------------------------------------------

        for binding in identity_index.source_bindings:
            if (
                binding.source.kind
                is not AndroidModelSourceKind.VINTF
            ):
                continue

            select(
                binding.entry,
                AndroidBootstrapEnvironmentPopulationReason
                .VINTF_MANIFEST,
            )

        # ----------------------------------------------------
        # Canonical SELinux runtime population.
        #
        # The selected recovery environment carries one compiled
        # policy plus its split labeling/context databases.
        # Bootstrap preserves that exact canonical runtime set.
        #
        # We do not attempt to minimize policy files from lexical
        # declaration matches: Parsing intentionally does not own
        # cross-source SELinux policy interpretation.
        # ----------------------------------------------------

        for binding in identity_index.source_bindings:
            if (
                binding.source.kind
                is not AndroidModelSourceKind.SELINUX
            ):
                continue

            select(
                binding.entry,
                AndroidBootstrapEnvironmentPopulationReason
                .SELINUX_RUNTIME,
            )

        # ----------------------------------------------------
        # Literal non-ELF runtime dependencies referenced by the
        # selected INIT graph.
        #
        # This is command-semantic selection, not blanket absolute-
        # path selection. Paths created by INIT remain runtime
        # products rather than canonical population requirements.
        # ----------------------------------------------------

        cpio_by_path = {
            self._normalize_path(
                entry.entry.path
            ): entry
            for entry
            in ramdisk.cpio_entries
        }

        def select_existing_path(
            value,
            reason: AndroidBootstrapEnvironmentPopulationReason,
        ) -> None:
            if (
                not isinstance(
                    value,
                    str,
                )
                or not self._is_literal_android_path(
                    value
                )
            ):
                return

            entry = cpio_by_path.get(
                self._normalize_path(
                    value
                )
            )

            if entry is None:
                return

            select(
                entry,
                reason,
            )

        for source_selection in init_closure.selected_sources:
            for action in source_selection.source.actions:
                for command in action.commands:
                    keyword = command.keyword
                    arguments = command.arguments

                    if keyword == "copy":
                        if len(
                            arguments
                        ) >= 1:
                            select_existing_path(
                                arguments[0],
                                AndroidBootstrapEnvironmentPopulationReason
                                .INIT_RUNTIME_RESOURCE,
                            )

                        if len(
                            arguments
                        ) >= 2:
                            destination = arguments[1]

                            if self._is_literal_android_path(
                                destination
                            ):
                                destination_parent = (
                                    self._normalize_path(
                                        destination
                                    )
                                    .parent
                                )

                                parent_entry = cpio_by_path.get(
                                    destination_parent
                                )

                                if parent_entry is not None:
                                    select(
                                        parent_entry,
                                        AndroidBootstrapEnvironmentPopulationReason
                                        .INIT_RUNTIME_STRUCTURE,
                                    )

                    elif keyword == "mount":
                        if len(
                            arguments
                        ) >= 3:
                            select_existing_path(
                                arguments[2],
                                AndroidBootstrapEnvironmentPopulationReason
                                .INIT_RUNTIME_STRUCTURE,
                            )

                    elif keyword == "restorecon":
                        for argument in arguments:
                            select_existing_path(
                                argument,
                                AndroidBootstrapEnvironmentPopulationReason
                                .INIT_RUNTIME_STRUCTURE,
                            )

        # ----------------------------------------------------
        # Runtime-consumer closure discovered from exact canonical
        # path evidence embedded in init/service executables.
        #
        # Newly discovered executable consumers also participate as
        # roots of the expanded ELF closure below.
        # ----------------------------------------------------

        for entry in runtime_consumer_executables:
            select(
                entry,
                AndroidBootstrapEnvironmentPopulationReason
                .RUNTIME_CONSUMER_EXECUTABLE,
            )

        for entry in runtime_consumer_resources:
            select(
                entry,
                AndroidBootstrapEnvironmentPopulationReason
                .RUNTIME_CONSUMER_RESOURCE,
            )

        for entry in runtime_consumer_subtree:
            select(
                entry,
                AndroidBootstrapEnvironmentPopulationReason
                .RUNTIME_CONSUMER_SUBTREE,
            )

        # ----------------------------------------------------
        # Post-ELF runtime extension evidence.
        # ----------------------------------------------------

        for entry in dynamic_elf_providers:
            select(
                entry,
                AndroidBootstrapEnvironmentPopulationReason
                .ELF_DYNAMIC_PROVIDER,
            )

        for entry in elf_runtime_resources:
            select(
                entry,
                AndroidBootstrapEnvironmentPopulationReason
                .ELF_RUNTIME_RESOURCE,
            )

        # ----------------------------------------------------
        # Required service CPIO entries. Excluded services do
        # not enter the population.
        # ----------------------------------------------------

        for service_resolution in init_closure.service_executables:
            if (
                service_resolution.disposition
                is not AndroidBootstrapInitServiceDisposition.REQUIRED
                or service_resolution.entry is None
            ):
                continue

            reason = (
                AndroidBootstrapEnvironmentPopulationReason
                .SERVICE_SYMLINK
                if (
                    service_resolution.entry.kind
                    is AndroidBootImageCpioEntryKind.SYMLINK
                )
                else AndroidBootstrapEnvironmentPopulationReason
                .SERVICE_EXECUTABLE
            )

            select(
                service_resolution.entry,
                reason,
            )

        # ----------------------------------------------------
        # Full exact ELF closure.
        # ----------------------------------------------------

        root_elf_ids = {
            id(
                binding.elf
            )
            for binding
            in elf_closure.roots
        }

        for binding in elf_closure.elfs:
            if binding.entry is None:
                raise ValueError(
                    "selected ELF closure contains unresolved CPIO binding"
                )

            select(
                binding.entry,
                (
                    AndroidBootstrapEnvironmentPopulationReason.ELF_ROOT
                    if id(
                        binding.elf
                    ) in root_elf_ids
                    else AndroidBootstrapEnvironmentPopulationReason
                    .ELF_DEPENDENCY
                ),
            )

        for dependency in elf_closure.dependencies:
            if (
                dependency.resolution
                is not AndroidBootstrapEnvironmentElfResolution.RESOLVED
                or dependency.provider is None
                or dependency.provider.entry is None
            ):
                continue

            select(
                dependency.provider.entry,
                (
                    AndroidBootstrapEnvironmentPopulationReason
                    .ELF_INTERPRETER
                    if dependency.kind
                    is AndroidBootstrapElfDependencyKind.INTERPRETER
                    else AndroidBootstrapEnvironmentPopulationReason
                    .ELF_DEPENDENCY
                ),
            )

        # ----------------------------------------------------
        # Preserve exact existing structural parents.
        #
        # We do not synthesize missing directory entries here.
        # ----------------------------------------------------

        directory_by_path = {
            self._normalize_path(
                entry.entry.path
            ): entry
            for entry
            in ramdisk.cpio_entries
            if entry.kind
            is AndroidBootImageCpioEntryKind.DIRECTORY
        }

        initially_selected = tuple(
            entries_by_id.values()
        )

        for entry in initially_selected:
            path = self._normalize_path(
                entry.entry.path
            )

            parent = path.parent

            while parent != PurePosixPath(
                "/"
            ):
                parent_entry = directory_by_path.get(
                    parent
                )

                if parent_entry is not None:
                    select(
                        parent_entry,
                        AndroidBootstrapEnvironmentPopulationReason
                        .STRUCTURAL_PARENT,
                    )

                parent = parent.parent

        # ----------------------------------------------------
        # Emit in exact canonical CPIO order and preserve the
        # selected-ramdisk complement explicitly.
        # ----------------------------------------------------

        population_entries = tuple(
            AndroidBootstrapEnvironmentPopulationEntry(
                entry=entry,
                reasons=tuple(
                    reasons_by_entry_id[
                        id(entry)
                    ]
                ),
            )
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) in entries_by_id
        )

        selected_ids = {
            id(
                value.entry
            )
            for value
            in population_entries
        }

        preserved_entries = tuple(
            entry
            for entry
            in ramdisk.cpio_entries
            if id(
                entry
            ) not in selected_ids
        )

        return AndroidBootstrapEnvironmentPopulationPlan(
            ramdisk_index=ramdisk_index,
            ramdisk=ramdisk,
            entries=population_entries,
            preserved_entries=preserved_entries,
        )

    def _elf_closure(
        self,
        *,
        ramdisk_index: int,
        identity_index: AndroidBootstrapEnvironmentIdentityIndex,
        init_closure: AndroidBootstrapInitClosure,
        environment_candidate: AndroidBootstrapEnvironmentRootCandidate,
        additional_root_paths: tuple[
            PurePosixPath,
            ...,
        ] = (),
    ) -> AndroidBootstrapElfClosure:
        resolved_bindings = tuple(
            binding
            for binding
            in identity_index.elf_bindings
            if (
                binding.resolution
                is AndroidBootstrapEnvironmentElfResolution.RESOLVED
                and binding.entry is not None
            )
        )

        by_path = {
            self._normalize_path(
                binding.entry.entry.path
            ): binding
            for binding
            in resolved_bindings
        }

        by_soname = {}

        for binding in resolved_bindings:
            soname = binding.elf.soname

            if soname is None:
                continue

            by_soname.setdefault(
                soname,
                [],
            ).append(
                binding
            )

        root_paths = []

        init_path = environment_candidate.root_target_path

        if init_path is not None:
            root_paths.append(
                self._normalize_path(
                    init_path
                )
            )

        for service_resolution in init_closure.service_executables:
            if (
                service_resolution.disposition
                is not AndroidBootstrapInitServiceDisposition.REQUIRED
                or service_resolution.entry is None
            ):
                continue

            entry = service_resolution.entry

            path = self._normalize_path(
                entry.entry.path
            )

            if entry.entry.entry_type.value == "symlink":
                try:
                    target = entry.entry.data.decode(
                        "utf-8",
                        errors="strict",
                    )
                except UnicodeDecodeError:
                    continue

                target_path = PurePosixPath(
                    target
                )

                if not target_path.is_absolute():
                    target_path = (
                        path.parent
                        / target_path
                    )

                path = self._normalize_path(
                    target_path
                )

            if path not in root_paths:
                root_paths.append(
                    path
                )

        for additional_path in additional_root_paths:
            path = self._normalize_path(
                additional_path
            )

            if path not in root_paths:
                root_paths.append(
                    path
                )

        roots = tuple(
            by_path[path]
            for path
            in root_paths
            if path in by_path
        )

        queue = list(
            roots
        )

        selected = []
        selected_ids = set()
        dependencies = []

        while queue:
            owner = queue.pop(
                0
            )

            owner_id = id(
                owner.elf
            )

            if owner_id in selected_ids:
                continue

            selected_ids.add(
                owner_id
            )

            selected.append(
                owner
            )

            elf = owner.elf

            if elf.interpreter is not None:
                interpreter_path = self._normalize_path(
                    elf.interpreter
                )

                provider = by_path.get(
                    interpreter_path
                )

                if provider is None:
                    dependencies.append(
                        AndroidBootstrapElfDependencyResolution(
                            owner=elf,
                            kind=(
                                AndroidBootstrapElfDependencyKind
                                .INTERPRETER
                            ),
                            name=elf.interpreter,
                            resolution=(
                                AndroidBootstrapEnvironmentElfResolution
                                .UNRESOLVED
                            ),
                            reason=(
                                "interpreter_not_present_in_environment"
                            ),
                        )
                    )

                else:
                    dependencies.append(
                        AndroidBootstrapElfDependencyResolution(
                            owner=elf,
                            kind=(
                                AndroidBootstrapElfDependencyKind
                                .INTERPRETER
                            ),
                            name=elf.interpreter,
                            resolution=(
                                AndroidBootstrapEnvironmentElfResolution
                                .RESOLVED
                            ),
                            provider=provider,
                            candidates=(
                                provider,
                            ),
                        )
                    )

                    queue.append(
                        provider
                    )

            for needed in elf.needed:
                candidates = tuple(
                    by_soname.get(
                        needed,
                        (),
                    )
                )

                if not candidates:
                    dependencies.append(
                        AndroidBootstrapElfDependencyResolution(
                            owner=elf,
                            kind=(
                                AndroidBootstrapElfDependencyKind.NEEDED
                            ),
                            name=needed,
                            resolution=(
                                AndroidBootstrapEnvironmentElfResolution
                                .UNRESOLVED
                            ),
                            reason=(
                                "soname_not_present_in_environment"
                            ),
                        )
                    )

                    continue

                if len(
                    candidates
                ) == 1:
                    provider = candidates[0]

                else:
                    provider = (
                        self._select_elf_provider_by_path_domain(
                            owner=owner,
                            candidates=candidates,
                        )
                    )

                if provider is None:
                    dependencies.append(
                        AndroidBootstrapElfDependencyResolution(
                            owner=elf,
                            kind=(
                                AndroidBootstrapElfDependencyKind.NEEDED
                            ),
                            name=needed,
                            resolution=(
                                AndroidBootstrapEnvironmentElfResolution
                                .AMBIGUOUS
                            ),
                            candidates=candidates,
                            reason=(
                                "multiple_soname_providers_without_"
                                "unique_path_domain"
                            ),
                        )
                    )

                    continue

                dependencies.append(
                    AndroidBootstrapElfDependencyResolution(
                        owner=elf,
                        kind=(
                            AndroidBootstrapElfDependencyKind.NEEDED
                        ),
                        name=needed,
                        resolution=(
                            AndroidBootstrapEnvironmentElfResolution
                            .RESOLVED
                        ),
                        provider=provider,
                        candidates=(
                            provider,
                        ),
                    )
                )

                queue.append(
                    provider
                )

        return AndroidBootstrapElfClosure(
            ramdisk_index=ramdisk_index,
            roots=roots,
            elfs=tuple(
                selected
            ),
            dependencies=tuple(
                dependencies
            ),
        )


    @staticmethod
    def _elf_virtual_address_bytes(
        elf: ParsedAndroidElf,
        virtual_address: int,
        size: int,
    ) -> bytes | None:
        """
        Read exact file-backed bytes for one ELF virtual-address range.

        This helper interprets only generic ELF64 little-endian PT_LOAD
        mappings. It does not interpret symbols, providers, sensors, or
        architecture-specific instructions.

        Ranges that are malformed, unsupported, not file-backed, or span
        outside one load segment remain unresolved.
        """

        if not isinstance(
            elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "elf must be a ParsedAndroidElf"
            )

        if (
            isinstance(
                virtual_address,
                bool,
            )
            or not isinstance(
                virtual_address,
                int,
            )
            or virtual_address < 0
        ):
            raise ValueError(
                "virtual_address must be a non-negative integer"
            )

        if (
            isinstance(
                size,
                bool,
            )
            or not isinstance(
                size,
                int,
            )
            or size <= 0
        ):
            raise ValueError(
                "size must be a positive integer"
            )

        try:
            content = (
                elf.source
                .host_path
                .read_bytes()
            )
        except OSError:
            return None

        # Minimum ELF64 header size.
        if len(content) < 64:
            return None

        if content[0:4] != b"\x7fELF":
            return None

        # ELFCLASS64.
        if content[4] != 2:
            return None

        # ELFDATA2LSB.
        if content[5] != 1:
            return None

        program_header_offset = int.from_bytes(
            content[32:40],
            byteorder="little",
            signed=False,
        )

        program_header_entry_size = int.from_bytes(
            content[54:56],
            byteorder="little",
            signed=False,
        )

        program_header_count = int.from_bytes(
            content[56:58],
            byteorder="little",
            signed=False,
        )

        # ELF64 program headers are 56 bytes. Larger entry sizes are
        # permitted as long as the standard prefix is present.
        if program_header_entry_size < 56:
            return None

        table_size = (
            program_header_entry_size
            * program_header_count
        )

        table_end = (
            program_header_offset
            + table_size
        )

        if (
            program_header_offset > len(content)
            or table_end > len(content)
        ):
            return None

        requested_end = (
            virtual_address
            + size
        )

        if requested_end < virtual_address:
            return None

        PT_LOAD = 1

        for index in range(
            program_header_count
        ):
            offset = (
                program_header_offset
                + (
                    index
                    * program_header_entry_size
                )
            )

            header = content[
                offset:
                offset + 56
            ]

            if len(header) != 56:
                return None

            program_type = int.from_bytes(
                header[0:4],
                byteorder="little",
                signed=False,
            )

            if program_type != PT_LOAD:
                continue

            file_offset = int.from_bytes(
                header[8:16],
                byteorder="little",
                signed=False,
            )

            segment_virtual_address = int.from_bytes(
                header[16:24],
                byteorder="little",
                signed=False,
            )

            file_size = int.from_bytes(
                header[32:40],
                byteorder="little",
                signed=False,
            )

            segment_file_end = (
                segment_virtual_address
                + file_size
            )

            if (
                virtual_address
                < segment_virtual_address
                or requested_end
                > segment_file_end
            ):
                continue

            relative_offset = (
                virtual_address
                - segment_virtual_address
            )

            requested_file_offset = (
                file_offset
                + relative_offset
            )

            requested_file_end = (
                requested_file_offset
                + size
            )

            if (
                requested_file_offset > len(content)
                or requested_file_end > len(content)
            ):
                return None

            return content[
                requested_file_offset:
                requested_file_end
            ]

        return None

    @staticmethod
    def _aarch64_immediate_u32_return(
        code: bytes,
    ) -> int | None:
        """
        Decode one minimal AArch64 integer-return function.

        Accepted form:

            movz w0, #imm16[, lsl #16]
            ret

        `mov w0, #imm` is the assembler alias normally emitted for
        this MOVZ form when the value is directly representable.

        This primitive is intentionally architecture-only. It has no
        knowledge of sensors, providers, vendors, devices, or semantic
        meaning.

        Any other instruction sequence remains unresolved rather than
        being guessed.
        """

        if not isinstance(
            code,
            bytes,
        ):
            raise TypeError(
                "code must be bytes"
            )

        if len(code) < 8:
            return None

        first = int.from_bytes(
            code[0:4],
            byteorder="little",
            signed=False,
        )

        second = int.from_bytes(
            code[4:8],
            byteorder="little",
            signed=False,
        )

        # RET X30
        if second != 0xD65F03C0:
            return None

        # MOVZ (32-bit), destination W0.
        #
        # sf    = 0
        # opc   = 10
        # fixed = 100101
        # Rd    = 0
        #
        # Mask away hw and imm16 while retaining the opcode and Rd.
        if (
            first
            & 0xFF80001F
        ) != 0x52800000:
            return None

        hw = (
            first
            >> 21
        ) & 0x3

        # 32-bit MOVZ only permits shifts 0 and 16.
        if hw > 1:
            return None

        immediate = (
            first
            >> 5
        ) & 0xFFFF

        return immediate << (
            hw * 16
        )

    @staticmethod
    def _elf_section_entries(
        content: bytes,
    ) -> tuple[
        tuple[
            str,
            int,
            int,
            int,
            int,
            int,
            int,
        ],
        ...,
    ]:
        """
        Decode the standard ELF64 little-endian section table.

        Returned tuple fields are:

            name
            section type
            file offset
            file size
            linked-section index
            entry size
            virtual address

        Unsupported or malformed ELF layouts remain unresolved.
        """

        if not isinstance(
            content,
            bytes,
        ):
            raise TypeError(
                "content must be bytes"
            )

        if (
            len(content) < 64
            or content[:4] != b"\x7fELF"
            or content[4] != 2
            or content[5] != 1
        ):
            return ()

        section_offset = int.from_bytes(
            content[40:48],
            "little",
        )

        section_entry_size = int.from_bytes(
            content[58:60],
            "little",
        )

        section_count = int.from_bytes(
            content[60:62],
            "little",
        )

        string_table_index = int.from_bytes(
            content[62:64],
            "little",
        )

        if (
            section_entry_size < 64
            or section_count == 0
            or string_table_index >= section_count
        ):
            return ()

        table_end = (
            section_offset
            + section_entry_size
            * section_count
        )

        if (
            section_offset > len(content)
            or table_end > len(content)
        ):
            return ()

        raw_entries = []

        for index in range(
            section_count
        ):
            offset = (
                section_offset
                + index
                * section_entry_size
            )

            header = content[
                offset:
                offset + 64
            ]

            if len(header) != 64:
                return ()

            raw_entries.append(
                (
                    int.from_bytes(
                        header[0:4],
                        "little",
                    ),
                    int.from_bytes(
                        header[4:8],
                        "little",
                    ),
                    int.from_bytes(
                        header[24:32],
                        "little",
                    ),
                    int.from_bytes(
                        header[32:40],
                        "little",
                    ),
                    int.from_bytes(
                        header[40:44],
                        "little",
                    ),
                    int.from_bytes(
                        header[56:64],
                        "little",
                    ),
                    int.from_bytes(
                        header[16:24],
                        "little",
                    ),
                )
            )

        (
            _,
            _,
            names_offset,
            names_size,
            _,
            _,
            _,
        ) = raw_entries[
            string_table_index
        ]

        names_end = (
            names_offset
            + names_size
        )

        if (
            names_offset > len(content)
            or names_end > len(content)
        ):
            return ()

        names = content[
            names_offset:
            names_end
        ]

        result = []

        for (
            name_offset,
            section_type,
            file_offset,
            file_size,
            link,
            entry_size,
            virtual_address,
        ) in raw_entries:
            if name_offset >= len(names):
                name = ""
            else:
                end = names.find(
                    b"\x00",
                    name_offset,
                )

                if end < 0:
                    end = len(names)

                name = names[
                    name_offset:end
                ].decode(
                    "utf-8",
                    errors="replace",
                )

            result.append(
                (
                    name,
                    section_type,
                    file_offset,
                    file_size,
                    link,
                    entry_size,
                    virtual_address,
                )
            )

        return tuple(
            result
        )

    @classmethod
    def _elf_named_section_bytes(
        cls,
        content: bytes,
        name: str,
    ) -> bytes | None:
        if not isinstance(
            name,
            str,
        ) or not name:
            raise ValueError(
                "name must be a non-empty string"
            )

        for (
            section_name,
            _,
            offset,
            size,
            _,
            _,
            _,
        ) in cls._elf_section_entries(
            content
        ):
            if section_name != name:
                continue

            end = offset + size

            if (
                offset > len(content)
                or end > len(content)
            ):
                return None

            return content[
                offset:end
            ]

        return None

    @classmethod
    def _elf_symbol_entries(
        cls,
        content: bytes,
    ) -> tuple[
        tuple[
            str,
            int,
            int,
        ],
        ...,
    ]:
        """
        Return intrinsic ELF symbol name, value and size.

        Both SHT_SYMTAB and SHT_DYNSYM are accepted.
        """

        sections = cls._elf_section_entries(
            content
        )

        if not sections:
            return ()

        result = []

        SHT_SYMTAB = 2
        SHT_DYNSYM = 11

        for (
            _,
            section_type,
            offset,
            size,
            link,
            entry_size,
            _,
        ) in sections:
            if section_type not in (
                SHT_SYMTAB,
                SHT_DYNSYM,
            ):
                continue

            if (
                link >= len(sections)
                or entry_size < 24
                or entry_size == 0
            ):
                continue

            (
                _,
                _,
                strings_offset,
                strings_size,
                _,
                _,
                _,
            ) = sections[
                link
            ]

            strings_end = (
                strings_offset
                + strings_size
            )

            symbols_end = (
                offset
                + size
            )

            if (
                strings_end > len(content)
                or symbols_end > len(content)
            ):
                continue

            strings = content[
                strings_offset:
                strings_end
            ]

            count = (
                size
                // entry_size
            )

            for index in range(
                count
            ):
                symbol_offset = (
                    offset
                    + index
                    * entry_size
                )

                symbol = content[
                    symbol_offset:
                    symbol_offset + 24
                ]

                if len(symbol) != 24:
                    continue

                name_offset = int.from_bytes(
                    symbol[0:4],
                    "little",
                )

                value = int.from_bytes(
                    symbol[8:16],
                    "little",
                )

                symbol_size = int.from_bytes(
                    symbol[16:24],
                    "little",
                )

                if (
                    name_offset == 0
                    or name_offset >= len(strings)
                ):
                    continue

                end = strings.find(
                    b"\x00",
                    name_offset,
                )

                if end < 0:
                    continue

                symbol_name = strings[
                    name_offset:end
                ].decode(
                    "utf-8",
                    errors="replace",
                )

                if not symbol_name:
                    continue

                result.append(
                    (
                        symbol_name,
                        value,
                        symbol_size,
                    )
                )

        return tuple(
            result
        )

    @classmethod
    def _elf_gnu_debugdata(
        cls,
        elf: ParsedAndroidElf,
    ) -> bytes | None:
        """
        Recover GNU mini-debug ELF data carried by a canonical ELF.

        The data remains factory evidence: no external debug tree or
        developer-created artifact is consulted.
        """

        if not isinstance(
            elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "elf must be a ParsedAndroidElf"
            )

        try:
            content = (
                elf.source
                .host_path
                .read_bytes()
            )
        except OSError:
            return None

        compressed = (
            cls._elf_named_section_bytes(
                content,
                ".gnu_debugdata",
            )
        )

        if not compressed:
            return None

        try:
            debug_data = lzma.decompress(
                compressed
            )
        except lzma.LZMAError:
            return None

        if (
            len(debug_data) < 64
            or debug_data[:4] != b"\x7fELF"
            or debug_data[4] != 2
            or debug_data[5] != 1
        ):
            return None

        return debug_data

    def build(
        self,
        intake: AndroidBootstrapIntakeResult,
        *,
        interpreter: AndroidBootImageInterpreter | None = None,
    ) -> AndroidBootstrapEnvironmentPlan:
        if not isinstance(
            intake,
            AndroidBootstrapIntakeResult,
        ):
            raise TypeError(
                "intake must be an AndroidBootstrapIntakeResult"
            )

        interpreter = (
            interpreter
            if interpreter is not None
            else AndroidBootImageInterpreter()
        )

        if not isinstance(
            interpreter,
            AndroidBootImageInterpreter,
        ):
            raise TypeError(
                "interpreter must be an AndroidBootImageInterpreter"
            )

        interpretation = interpreter.build(
            intake.boot_image_intake
        )

        if (
            interpretation.parsing
            is not intake.parsing
        ):
            raise RuntimeError(
                "Boot Image Interpretation lost exact Parsing "
                "identity at Bootstrap Environment Planning"
            )

        requirements = []

        identity_indexes = tuple(
            self._identity_index(
                ramdisk_index=ramdisk_index,
                ramdisk=ramdisk,
                parsing=intake.parsing,
            )
            for ramdisk_index, ramdisk
            in enumerate(
                interpretation.ramdisks
            )
        )

        environment_root = (
            self._environment_root_selection(
                interpretation
            )
        )

        board_platform = (
            self._canonical_property_value(
                interpretation.parsing,
                "ro.board.platform",
            )
        )

        selected_environment_candidate = (
            environment_root.candidate
            if (
                environment_root.resolution
                is AndroidBootstrapInitResolution.RESOLVED
            )
            else None
        )

        init_closures = tuple(
            self._init_closure(
                ramdisk_index=ramdisk_index,
                ramdisk=ramdisk,
                environment_candidate=(
                    selected_environment_candidate
                    if (
                        selected_environment_candidate
                        is not None
                        and selected_environment_candidate.ramdisk
                        is ramdisk
                    )
                    else None
                ),
                board_platform=board_platform,
            )
            for ramdisk_index, ramdisk
            in enumerate(
                interpretation.ramdisks
            )
        )

        elf_closure = None

        if selected_environment_candidate is not None:
            selected_index = (
                selected_environment_candidate.ramdisk_index
            )

            (
                runtime_consumer_executables,
                runtime_consumer_resources,
                runtime_consumer_subtree,
            ) = self._runtime_consumer_targets(
                ramdisk=selected_environment_candidate.ramdisk,
                identity_index=identity_indexes[
                    selected_index
                ],
                environment_candidate=(
                    selected_environment_candidate
                ),
                init_closure=init_closures[
                    selected_index
                ],
            )

            additional_elf_roots = list(
                self._normalize_path(
                    entry.entry.path
                )
                for entry
                in runtime_consumer_executables
            )

            dynamic_elf_providers = ()
            elf_runtime_resources = ()

            dynamic_provider_ids = set()
            runtime_resource_ids = set()

            while True:
                elf_closure = self._elf_closure(
                    ramdisk_index=selected_index,
                    identity_index=identity_indexes[
                        selected_index
                    ],
                    init_closure=init_closures[
                        selected_index
                    ],
                    environment_candidate=(
                        selected_environment_candidate
                    ),
                    additional_root_paths=tuple(
                        additional_elf_roots
                    ),
                )

                (
                    discovered_dynamic_providers,
                    discovered_runtime_resources,
                ) = self._elf_runtime_extensions(
                    ramdisk=selected_environment_candidate.ramdisk,
                    identity_index=identity_indexes[
                        selected_index
                    ],
                    elf_closure=elf_closure,
                )

                changed = False

                for entry in discovered_dynamic_providers:
                    entry_id = id(
                        entry
                    )

                    if entry_id in dynamic_provider_ids:
                        continue

                    dynamic_provider_ids.add(
                        entry_id
                    )

                    additional_elf_roots.append(
                        self._normalize_path(
                            entry.entry.path
                        )
                    )

                    changed = True

                for entry in discovered_runtime_resources:
                    runtime_resource_ids.add(
                        id(
                            entry
                        )
                    )

                if not changed:
                    break

            dynamic_elf_providers = tuple(
                entry
                for entry
                in selected_environment_candidate.ramdisk.cpio_entries
                if id(
                    entry
                ) in dynamic_provider_ids
            )

            elf_runtime_resources = tuple(
                entry
                for entry
                in selected_environment_candidate.ramdisk.cpio_entries
                if id(
                    entry
                ) in runtime_resource_ids
            )

        population = None

        if (
            selected_environment_candidate is not None
            and elf_closure is not None
        ):
            selected_index = (
                selected_environment_candidate.ramdisk_index
            )

            population = self._environment_population(
                ramdisk_index=selected_index,
                ramdisk=selected_environment_candidate.ramdisk,
                identity_index=identity_indexes[
                    selected_index
                ],
                environment_candidate=(
                    selected_environment_candidate
                ),
                init_closure=init_closures[
                    selected_index
                ],
                elf_closure=elf_closure,
                runtime_consumer_executables=(
                    runtime_consumer_executables
                ),
                runtime_consumer_resources=(
                    runtime_consumer_resources
                ),
                runtime_consumer_subtree=(
                    runtime_consumer_subtree
                ),
                dynamic_elf_providers=(
                    dynamic_elf_providers
                ),
                elf_runtime_resources=(
                    elf_runtime_resources
                ),
            )

        for ramdisk_index, ramdisk in enumerate(
            interpretation.ramdisks
        ):
            for entry in ramdisk.cpio_entries:
                requirements.append(
                    AndroidBootstrapEnvironmentRequirement(
                        ramdisk_index=ramdisk_index,
                        entry=entry,
                        kind=self._classify_kind(
                            entry
                        ),
                        disposition=(
                            self._classify_disposition(
                                entry
                            )
                        ),
                    )
                )

        return AndroidBootstrapEnvironmentPlan(
            intake=intake,
            boot_image_interpretation=interpretation,
            requirements=tuple(
                requirements
            ),
            identity_indexes=identity_indexes,
            environment_root=environment_root,
            init_closures=init_closures,
            elf_closure=elf_closure,
            population=population,
        )


__all__ = (
    "AndroidBootstrapEnvironmentConfiguration",
    "AndroidBootstrapEnvironmentRootCandidate",
    "AndroidBootstrapEnvironmentRootSelection",
    "AndroidBootstrapInitClosure",
    "AndroidBootstrapInitImportResolution",
    "AndroidBootstrapInitResolution",
    "AndroidBootstrapInitServiceDisposition",
    "AndroidBootstrapInitServiceExecutableResolution",
    "AndroidBootstrapInitSourceRole",
    "AndroidBootstrapInitSourceSelection",
    "AndroidBootstrapRootInitBinaryResolution",
    "AndroidBootstrapRuntimeSupportResolution",
    "AndroidBootstrapSelinuxBinding",
    "AndroidBootstrapVintfBinding",
    "AndroidBootstrapElfClosure",
    "AndroidBootstrapElfDependencyKind",
    "AndroidBootstrapElfDependencyResolution",
    "AndroidBootstrapEnvironmentElfBinding",
    "AndroidBootstrapEnvironmentElfResolution",
    "AndroidBootstrapEnvironmentIdentityIndex",
    "AndroidBootstrapEnvironmentPopulationEntry",
    "AndroidBootstrapEnvironmentPopulationPlan",
    "AndroidBootstrapEnvironmentPopulationReason",
    "AndroidBootstrapEnvironmentPlan",
    "AndroidBootstrapEnvironmentPlanner",
    "AndroidBootstrapEnvironmentRequirement",
    "AndroidBootstrapEnvironmentRequirementDisposition",
    "AndroidBootstrapEnvironmentRequirementKind",
    "AndroidBootstrapEnvironmentSourceBinding",
)
