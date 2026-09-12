from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.elf.model import (
    AndroidElfParsingResult,
    ParsedAndroidElf,
)
from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceKind,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidKernelModuleInfoEntry:
    """
    One literal NUL-delimited record from a kernel module .modinfo section.

    Parsing preserves the encoded record and its location. Interpretation of
    fields such as name, depends, alias, firmware, vermagic, parm, and
    parmtype belongs to Android Device Universe.
    """

    index: int
    byte_offset: int
    raw: str
    key: str | None = None
    value: str | None = None

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
            or self.index < 0
        ):
            raise ValueError(
                "index must be a non-negative integer"
            )

        if (
            isinstance(
                self.byte_offset,
                bool,
            )
            or not isinstance(
                self.byte_offset,
                int,
            )
            or self.byte_offset < 0
        ):
            raise ValueError(
                "byte_offset must be a non-negative integer"
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
                "raw must not be empty"
            )

        if (
            self.key is None
            and self.value is not None
        ):
            raise ValueError(
                "value requires a key"
            )

        if self.key is not None:
            if not isinstance(
                self.key,
                str,
            ):
                raise TypeError(
                    "key must be a string or None"
                )

            if not self.key:
                raise ValueError(
                    "key must not be empty"
                )

            if not isinstance(
                self.value,
                str,
            ):
                raise TypeError(
                    "keyed modinfo entry value must be a string"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidKernelModule:
    """
    Intrinsic Parsing result for one exact canonical kernel-module ELF.

    The ParsedAndroidElf object remains the authoritative source identity and
    generic ELF observation. This model adds only Linux kernel-module evidence
    encoded in that same physical file.
    """

    elf: ParsedAndroidElf
    modinfo_section_offset: int | None
    modinfo_section_size: int
    modinfo_entries: tuple[
        ParsedAndroidKernelModuleInfoEntry,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.elf,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "elf must be a ParsedAndroidElf"
            )

        if not (
            self.elf.source
            .is_filesystem_backed
        ):
            raise ValueError(
                "kernel module must use a filesystem-backed ELF source"
            )

        if (
            self.elf.source.host_path
            .suffix.lower()
            != ".ko"
        ):
            raise ValueError(
                "kernel module source must use the .ko suffix"
            )

        if (
            self.elf.elf_type
            != "ET_REL"
        ):
            raise ValueError(
                "kernel module ELF must be ET_REL"
            )

        if (
            self.modinfo_section_offset
            is not None
        ):
            if (
                isinstance(
                    self.modinfo_section_offset,
                    bool,
                )
                or not isinstance(
                    self.modinfo_section_offset,
                    int,
                )
                or self.modinfo_section_offset < 0
            ):
                raise ValueError(
                    "modinfo_section_offset must be "
                    "a non-negative integer or None"
                )

        if (
            isinstance(
                self.modinfo_section_size,
                bool,
            )
            or not isinstance(
                self.modinfo_section_size,
                int,
            )
            or self.modinfo_section_size < 0
        ):
            raise ValueError(
                "modinfo_section_size must be a non-negative integer"
            )

        if (
            self.modinfo_section_offset
            is None
            and self.modinfo_section_size != 0
        ):
            raise ValueError(
                "missing .modinfo section must have size zero"
            )

        if not isinstance(
            self.modinfo_entries,
            tuple,
        ):
            raise TypeError(
                "modinfo_entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                ParsedAndroidKernelModuleInfoEntry,
            )
            for entry
            in self.modinfo_entries
        ):
            raise TypeError(
                "modinfo_entries must contain only "
                "ParsedAndroidKernelModuleInfoEntry instances"
            )

        indexes = tuple(
            entry.index
            for entry
            in self.modinfo_entries
        )

        if indexes != tuple(
            range(
                len(
                    self.modinfo_entries
                )
            )
        ):
            raise ValueError(
                "modinfo_entries must use contiguous canonical indexes"
            )

        offsets = tuple(
            entry.byte_offset
            for entry
            in self.modinfo_entries
        )

        if offsets != tuple(
            sorted(
                offsets
            )
        ):
            raise ValueError(
                "modinfo_entries must use byte-offset order"
            )

    @property
    def source_name(
        self,
    ) -> str:
        return (
            self.elf.source
            .source_name
        )

    @property
    def android_path(
        self,
    ):
        return (
            self.elf.source
            .android_path
        )

    @property
    def modinfo_count(
        self,
    ) -> int:
        return len(
            self.modinfo_entries
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidKernelModuleParsingResult:
    """
    Complete deterministic kernel-module population observed by Parsing.

    Distinct canonical source/path observations remain distinct even when
    their payload bytes are identical. Cross-source reconciliation belongs to
    Android Device Universe.
    """

    modules: tuple[
        ParsedAndroidKernelModule,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.modules,
            tuple,
        ):
            raise TypeError(
                "modules must be a tuple"
            )

        if not all(
            isinstance(
                module,
                ParsedAndroidKernelModule,
            )
            for module
            in self.modules
        ):
            raise TypeError(
                "modules must contain only "
                "ParsedAndroidKernelModule instances"
            )

        canonical = tuple(
            sorted(
                self.modules,
                key=lambda module: (
                    module.elf.source
                    .identity_key
                ),
            )
        )

        if canonical != self.modules:
            raise ValueError(
                "modules must use canonical ELF source order"
            )

        identities = tuple(
            module.elf.source
            .identity_key
            for module
            in self.modules
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "modules must not contain duplicate canonical sources"
            )

        elf_object_ids = tuple(
            id(
                module.elf
            )
            for module
            in self.modules
        )

        if len(
            elf_object_ids
        ) != len(
            set(
                elf_object_ids
            )
        ):
            raise ValueError(
                "modules must preserve unique canonical "
                "ParsedAndroidElf object identities"
            )

    @property
    def count(
        self,
    ) -> int:
        return len(
            self.modules
        )

    @property
    def modinfo_entry_count(
        self,
    ) -> int:
        return sum(
            module.modinfo_count
            for module
            in self.modules
        )

    @property
    def modules_with_modinfo_count(
        self,
    ) -> int:
        return sum(
            1
            for module
            in self.modules
            if module.modinfo_section_offset
            is not None
        )


class AndroidKernelModuleConfigurationKind(
    StrEnum
):
    DEP = "modules.dep"
    LOAD = "modules.load"
    ALIAS = "modules.alias"
    SOFTDEP = "modules.softdep"
    BLOCKLIST = "modules.blocklist"
    OPTIONS = "modules.options"
    ORDER = "modules.order"
    BUILTIN = "modules.builtin"
    BUILTIN_MODINFO = "modules.builtin.modinfo"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidKernelModuleConfigurationLine:
    """
    One literal meaningful line from a modules.* configuration source.

    Parsing performs only lexical decomposition. The meaning of dependencies,
    aliases, load sequence, soft dependencies, blocklists, and options belongs
    to Android Device Universe.
    """

    raw: str
    content: str
    tokens: tuple[str, ...]
    source_line: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.content,
            str,
        ):
            raise TypeError(
                "content must be a string"
            )

        if not self.content:
            raise ValueError(
                "content must not be empty"
            )

        if not isinstance(
            self.tokens,
            tuple,
        ):
            raise TypeError(
                "tokens must be a tuple"
            )

        if not self.tokens:
            raise ValueError(
                "tokens must not be empty"
            )

        if not all(
            isinstance(
                token,
                str,
            )
            and token
            for token
            in self.tokens
        ):
            raise ValueError(
                "tokens must contain non-empty strings"
            )

        if (
            isinstance(
                self.source_line,
                bool,
            )
            or not isinstance(
                self.source_line,
                int,
            )
            or self.source_line < 1
        ):
            raise ValueError(
                "source_line must be a positive integer"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedAndroidKernelModuleConfiguration:
    """
    Literal Parsing result for one exact canonical modules.* source.
    """

    source: AndroidModelSource
    configuration_kind: AndroidKernelModuleConfigurationKind
    raw: str
    lines: tuple[
        AndroidKernelModuleConfigurationLine,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidModelSource,
        ):
            raise TypeError(
                "source must be an AndroidModelSource"
            )

        if (
            self.source.kind
            is not AndroidModelSourceKind
            .KERNEL_MODULE_CONFIGURATION
        ):
            raise ValueError(
                "kernel-module configuration source must use "
                "KERNEL_MODULE_CONFIGURATION kind"
            )

        if not isinstance(
            self.configuration_kind,
            AndroidKernelModuleConfigurationKind,
        ):
            raise TypeError(
                "configuration_kind must be an "
                "AndroidKernelModuleConfigurationKind"
            )

        if (
            self.source.host_path.name
            != self.configuration_kind.value
        ):
            raise ValueError(
                "configuration kind must match the canonical source filename"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.lines,
            tuple,
        ):
            raise TypeError(
                "lines must be a tuple"
            )

        if not all(
            isinstance(
                line,
                AndroidKernelModuleConfigurationLine,
            )
            for line
            in self.lines
        ):
            raise TypeError(
                "lines must contain only "
                "AndroidKernelModuleConfigurationLine instances"
            )

        source_lines = tuple(
            line.source_line
            for line
            in self.lines
        )

        if source_lines != tuple(
            sorted(
                source_lines
            )
        ):
            raise ValueError(
                "configuration lines must use source-line order"
            )

    @property
    def line_count(
        self,
    ) -> int:
        return len(
            self.lines
        )

