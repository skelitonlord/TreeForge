from __future__ import annotations

from io import BytesIO

from elftools.common.exceptions import (
    ELFError,
)
from elftools.elf.elffile import (
    ELFFile,
)

from treeforge.android.parsing.elf.model import (
    AndroidElfParsingResult,
    ParsedAndroidElf,
)
from treeforge.android.parsing.kernel_module.model import (
    AndroidKernelModuleParsingResult,
    ParsedAndroidKernelModule,
    ParsedAndroidKernelModuleInfoEntry,
)


class AndroidKernelModuleParsingError(
    ValueError,
):
    pass


class AndroidKernelModuleParser:
    """
    Decode intrinsic Linux kernel-module evidence from canonical ELF results.

    Generic ELF structure remains owned by ELF Parsing. This parser consumes
    that already-established population and reads only kernel-module-specific
    data from .ko files.

    Cross-source identity, deployment role, dependency resolution, load order,
    and device-level meaning remain owned by Android Device Universe.
    """

    MODINFO_SECTION = ".modinfo"

    def parse(
        self,
        elf: AndroidElfParsingResult,
    ) -> AndroidKernelModuleParsingResult:
        if not isinstance(
            elf,
            AndroidElfParsingResult,
        ):
            raise TypeError(
                "elf must be an AndroidElfParsingResult"
            )

        candidates = tuple(
            parsed
            for parsed
            in elf.elf_files
            if self._is_kernel_module_candidate(
                parsed
            )
        )

        modules = tuple(
            self._parse_module(
                parsed
            )
            for parsed
            in candidates
        )

        expected_candidate_ids = {
            id(parsed)
            for parsed
            in candidates
        }

        actual_module_ids = {
            id(module.elf)
            for module
            in modules
        }

        if (
            expected_candidate_ids
            != actual_module_ids
        ):
            raise AndroidKernelModuleParsingError(
                "kernel-module Parsing failed to conserve the "
                "complete canonical .ko ELF population"
            )

        if len(
            actual_module_ids
        ) != len(
            modules
        ):
            raise AndroidKernelModuleParsingError(
                "kernel-module Parsing duplicated a canonical "
                "ParsedAndroidElf source"
            )

        return (
            AndroidKernelModuleParsingResult(
                modules=modules,
            )
        )

    @staticmethod
    def _is_kernel_module_candidate(
        parsed: ParsedAndroidElf,
    ) -> bool:
        source = parsed.source

        if not source.is_filesystem_backed:
            return False

        return (
            source.host_path
            .suffix.lower()
            == ".ko"
        )

    def _parse_module(
        self,
        parsed: ParsedAndroidElf,
    ) -> ParsedAndroidKernelModule:
        if parsed.elf_type != "ET_REL":
            raise AndroidKernelModuleParsingError(
                "kernel module candidate is not ET_REL: "
                f"{parsed.source.source_name}:"
                f"{parsed.source.display_path} "
                f"({parsed.elf_type})"
            )

        try:
            content = (
                parsed.source
                .host_path
                .read_bytes()
            )

            elf = ELFFile(
                BytesIO(
                    content
                )
            )

            section = (
                elf.get_section_by_name(
                    self.MODINFO_SECTION
                )
            )

        except (
            ELFError,
            OSError,
            ValueError,
        ) as error:
            raise AndroidKernelModuleParsingError(
                "failed to inspect kernel module "
                f"{parsed.source.source_name}:"
                f"{parsed.source.display_path}: "
                f"{error}"
            ) from error

        if section is None:
            return (
                ParsedAndroidKernelModule(
                    elf=parsed,
                    modinfo_section_offset=None,
                    modinfo_section_size=0,
                    modinfo_entries=(),
                )
            )

        try:
            section_offset = int(
                section.header[
                    "sh_offset"
                ]
            )

            section_size = int(
                section.header[
                    "sh_size"
                ]
            )

            data = section.data()

        except (
            ELFError,
            OSError,
            ValueError,
            KeyError,
        ) as error:
            raise AndroidKernelModuleParsingError(
                "failed to decode .modinfo section for "
                f"{parsed.source.source_name}:"
                f"{parsed.source.display_path}: "
                f"{error}"
            ) from error

        if len(data) != section_size:
            raise AndroidKernelModuleParsingError(
                ".modinfo section size mismatch for "
                f"{parsed.source.source_name}:"
                f"{parsed.source.display_path}: "
                f"header={section_size} decoded={len(data)}"
            )

        entries = (
            self._parse_modinfo_entries(
                data,
                parsed,
            )
        )

        return (
            ParsedAndroidKernelModule(
                elf=parsed,
                modinfo_section_offset=(
                    section_offset
                ),
                modinfo_section_size=(
                    section_size
                ),
                modinfo_entries=entries,
            )
        )

    @staticmethod
    def _parse_modinfo_entries(
        data: bytes,
        parsed: ParsedAndroidElf,
    ) -> tuple[
        ParsedAndroidKernelModuleInfoEntry,
        ...,
    ]:
        entries: list[
            ParsedAndroidKernelModuleInfoEntry
        ] = []

        offset = 0

        while offset < len(data):
            end = data.find(
                b"\x00",
                offset,
            )

            if end < 0:
                end = len(
                    data
                )

            raw_bytes = data[
                offset:end
            ]

            if raw_bytes:
                try:
                    raw = (
                        raw_bytes.decode(
                            "utf-8"
                        )
                    )
                except UnicodeDecodeError as error:
                    raise AndroidKernelModuleParsingError(
                        ".modinfo record is not valid UTF-8 for "
                        f"{parsed.source.source_name}:"
                        f"{parsed.source.display_path} "
                        f"at section byte offset {offset}"
                    ) from error

                key: str | None = None
                value: str | None = None

                if "=" in raw:
                    key, value = raw.split(
                        "=",
                        1,
                    )

                    if not key:
                        key = None
                        value = None

                entries.append(
                    ParsedAndroidKernelModuleInfoEntry(
                        index=len(
                            entries
                        ),
                        byte_offset=offset,
                        raw=raw,
                        key=key,
                        value=value,
                    )
                )

            offset = end + 1

        return tuple(
            entries
        )
