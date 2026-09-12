from __future__ import annotations

from pathlib import Path
import struct

from treeforge.android.extraction.elf.model import (
    EmbeddedElfRange,
    EmbeddedElfStructure,
)


class EmbeddedElfDecodeError(
    RuntimeError,
):
    """
    Raised when a structurally selected ELF candidate cannot be decoded
    safely.
    """


class EmbeddedElfDecoder:
    """
    Discover physically embedded ELF objects by intrinsic structure.

    This decoder is deliberately container-agnostic.

    It does not know about FBPK, bootloader partition names, devices,
    platforms, Android versions, or firmware roles.

    A four-byte ELF magic occurrence is only a candidate. It becomes a
    physical embedded ELF range only when its ELF header and every referenced
    physical table/segment/section range validate inside the parent file.

    Offset zero is intentionally excluded: a file that is itself an ELF is
    already a directly accessible artifact and must not recursively extract
    itself.
    """

    MAGIC = b"\x7fELF"

    ELFCLASS32 = 1
    ELFCLASS64 = 2

    ELFDATA2LSB = 1
    ELFDATA2MSB = 2

    SHT_NOBITS = 8

    ELF32_HEADER_SIZE = 52
    ELF64_HEADER_SIZE = 64

    ELF32_PROGRAM_HEADER_SIZE = 32
    ELF64_PROGRAM_HEADER_SIZE = 56

    ELF32_SECTION_HEADER_SIZE = 40
    ELF64_SECTION_HEADER_SIZE = 64

    def supports(
        self,
        source: Path,
    ) -> bool:
        return bool(
            self.decode(
                source
            ).ranges
        )

    def decode(
        self,
        source: Path,
    ) -> EmbeddedElfStructure:
        source = self._validate_source(
            source
        )

        data = source.read_bytes()
        image_size = len(
            data
        )

        candidates = self._candidate_offsets(
            data
        )

        decoded: list[
            EmbeddedElfRange
        ] = []

        for offset in candidates:
            candidate = self._decode_candidate(
                data,
                offset,
            )

            if candidate is None:
                continue

            decoded.append(
                candidate
            )

        #
        # ELF index is canonical output identity, not candidate-magic index.
        #
        ranges = tuple(
            EmbeddedElfRange(
                index=index,
                offset_bytes=value.offset_bytes,
                size_bytes=value.size_bytes,
                elf_class=value.elf_class,
                encoding=value.encoding,
                elf_type=value.elf_type,
                machine=value.machine,
                elf_version=value.elf_version,
                entry_point=value.entry_point,
                program_header_offset=(
                    value.program_header_offset
                ),
                program_header_entry_size=(
                    value.program_header_entry_size
                ),
                program_header_count=(
                    value.program_header_count
                ),
                section_header_offset=(
                    value.section_header_offset
                ),
                section_header_entry_size=(
                    value.section_header_entry_size
                ),
                section_header_count=(
                    value.section_header_count
                ),
            )
            for index, value in enumerate(
                sorted(
                    decoded,
                    key=lambda value: (
                        value.offset_bytes
                    ),
                )
            )
        )

        return EmbeddedElfStructure(
            source=source,
            image_size=image_size,
            ranges=ranges,
        )

    @classmethod
    def _candidate_offsets(
        cls,
        data: bytes,
    ) -> tuple[
        int,
        ...,
    ]:
        offsets: list[
            int
        ] = []

        #
        # Start at byte one. Offset zero represents a file that is itself an
        # ELF rather than an ELF embedded within another physical artifact.
        #
        cursor = 1

        while True:
            offset = data.find(
                cls.MAGIC,
                cursor,
            )

            if offset < 0:
                break

            offsets.append(
                offset
            )

            cursor = (
                offset
                + 1
            )

        return tuple(
            offsets
        )

    def _decode_candidate(
        self,
        data: bytes,
        offset: int,
    ) -> EmbeddedElfRange | None:
        if (
            offset < 0
            or offset + 16 > len(data)
        ):
            return None

        ident = data[
            offset:
            offset + 16
        ]

        if ident[:4] != self.MAGIC:
            return None

        elf_class = ident[4]
        encoding = ident[5]
        ident_version = ident[6]

        if elf_class not in {
            self.ELFCLASS32,
            self.ELFCLASS64,
        }:
            return None

        if encoding not in {
            self.ELFDATA2LSB,
            self.ELFDATA2MSB,
        }:
            return None

        if ident_version != 1:
            return None

        endian = (
            "<"
            if encoding == self.ELFDATA2LSB
            else ">"
        )

        try:
            if elf_class == self.ELFCLASS32:
                header_size = (
                    self.ELF32_HEADER_SIZE
                )

                if (
                    offset + header_size
                    > len(data)
                ):
                    return None

                (
                    elf_type,
                    machine,
                    elf_version,
                    entry_point,
                    program_header_offset,
                    section_header_offset,
                    _flags,
                    declared_header_size,
                    program_header_entry_size,
                    program_header_count,
                    section_header_entry_size,
                    section_header_count,
                    _section_name_index,
                ) = struct.unpack_from(
                    f"{endian}HHIIIIIHHHHHH",
                    data,
                    offset + 16,
                )

                expected_program_header_size = (
                    self.ELF32_PROGRAM_HEADER_SIZE
                )

                expected_section_header_size = (
                    self.ELF32_SECTION_HEADER_SIZE
                )

            else:
                header_size = (
                    self.ELF64_HEADER_SIZE
                )

                if (
                    offset + header_size
                    > len(data)
                ):
                    return None

                (
                    elf_type,
                    machine,
                    elf_version,
                    entry_point,
                    program_header_offset,
                    section_header_offset,
                    _flags,
                    declared_header_size,
                    program_header_entry_size,
                    program_header_count,
                    section_header_entry_size,
                    section_header_count,
                    _section_name_index,
                ) = struct.unpack_from(
                    f"{endian}HHIQQQIHHHHHH",
                    data,
                    offset + 16,
                )

                expected_program_header_size = (
                    self.ELF64_PROGRAM_HEADER_SIZE
                )

                expected_section_header_size = (
                    self.ELF64_SECTION_HEADER_SIZE
                )

        except struct.error:
            return None

        if elf_version != 1:
            return None

        if declared_header_size != header_size:
            return None

        if (
            program_header_count > 0
            and program_header_entry_size
            != expected_program_header_size
        ):
            return None

        if (
            section_header_count > 0
            and section_header_entry_size
            != expected_section_header_size
        ):
            return None

        extent = header_size

        if program_header_count:
            program_table_end = (
                program_header_offset
                + (
                    program_header_entry_size
                    * program_header_count
                )
            )

            if not self._relative_range_in_bounds(
                parent_size=len(data),
                base_offset=offset,
                relative_offset=(
                    program_header_offset
                ),
                size=(
                    program_header_entry_size
                    * program_header_count
                ),
            ):
                return None

            extent = max(
                extent,
                program_table_end,
            )

        if section_header_count:
            section_table_end = (
                section_header_offset
                + (
                    section_header_entry_size
                    * section_header_count
                )
            )

            if not self._relative_range_in_bounds(
                parent_size=len(data),
                base_offset=offset,
                relative_offset=(
                    section_header_offset
                ),
                size=(
                    section_header_entry_size
                    * section_header_count
                ),
            ):
                return None

            extent = max(
                extent,
                section_table_end,
            )

        #
        # Every file-backed program segment contributes to the complete
        # physical ELF extent.
        #
        for index in range(
            program_header_count
        ):
            program_offset = (
                offset
                + program_header_offset
                + index
                * program_header_entry_size
            )

            try:
                if elf_class == self.ELFCLASS32:
                    (
                        _p_type,
                        p_offset,
                        _p_vaddr,
                        _p_paddr,
                        p_filesz,
                        _p_memsz,
                        _p_flags,
                        _p_align,
                    ) = struct.unpack_from(
                        f"{endian}IIIIIIII",
                        data,
                        program_offset,
                    )

                else:
                    (
                        _p_type,
                        _p_flags,
                        p_offset,
                        _p_vaddr,
                        _p_paddr,
                        p_filesz,
                        _p_memsz,
                        _p_align,
                    ) = struct.unpack_from(
                        f"{endian}IIQQQQQQ",
                        data,
                        program_offset,
                    )

            except struct.error:
                return None

            if p_filesz:
                if not self._relative_range_in_bounds(
                    parent_size=len(data),
                    base_offset=offset,
                    relative_offset=p_offset,
                    size=p_filesz,
                ):
                    return None

                extent = max(
                    extent,
                    p_offset + p_filesz,
                )

        #
        # Include every physically backed section. SHT_NOBITS describes
        # memory-only data and has no bytes in the ELF file.
        #
        for index in range(
            section_header_count
        ):
            section_offset = (
                offset
                + section_header_offset
                + index
                * section_header_entry_size
            )

            try:
                if elf_class == self.ELFCLASS32:
                    (
                        _sh_name,
                        sh_type,
                        _sh_flags,
                        _sh_addr,
                        sh_offset,
                        sh_size,
                        _sh_link,
                        _sh_info,
                        _sh_addralign,
                        _sh_entsize,
                    ) = struct.unpack_from(
                        f"{endian}IIIIIIIIII",
                        data,
                        section_offset,
                    )

                else:
                    (
                        _sh_name,
                        sh_type,
                        _sh_flags,
                        _sh_addr,
                        sh_offset,
                        sh_size,
                        _sh_link,
                        _sh_info,
                        _sh_addralign,
                        _sh_entsize,
                    ) = struct.unpack_from(
                        f"{endian}IIQQQQIIQQ",
                        data,
                        section_offset,
                    )

            except struct.error:
                return None

            if (
                sh_type != self.SHT_NOBITS
                and sh_size
            ):
                if not self._relative_range_in_bounds(
                    parent_size=len(data),
                    base_offset=offset,
                    relative_offset=sh_offset,
                    size=sh_size,
                ):
                    return None

                extent = max(
                    extent,
                    sh_offset + sh_size,
                )

        if extent <= 0:
            return None

        if offset + extent > len(data):
            return None

        return EmbeddedElfRange(
            index=0,
            offset_bytes=offset,
            size_bytes=extent,
            elf_class=elf_class,
            encoding=encoding,
            elf_type=elf_type,
            machine=machine,
            elf_version=elf_version,
            entry_point=entry_point,
            program_header_offset=(
                program_header_offset
            ),
            program_header_entry_size=(
                program_header_entry_size
            ),
            program_header_count=(
                program_header_count
            ),
            section_header_offset=(
                section_header_offset
            ),
            section_header_entry_size=(
                section_header_entry_size
            ),
            section_header_count=(
                section_header_count
            ),
        )

    @staticmethod
    def _relative_range_in_bounds(
        *,
        parent_size: int,
        base_offset: int,
        relative_offset: int,
        size: int,
    ) -> bool:
        if (
            isinstance(
                relative_offset,
                bool,
            )
            or not isinstance(
                relative_offset,
                int,
            )
            or isinstance(
                size,
                bool,
            )
            or not isinstance(
                size,
                int,
            )
        ):
            return False

        if (
            relative_offset < 0
            or size < 0
        ):
            return False

        absolute_start = (
            base_offset
            + relative_offset
        )

        absolute_end = (
            absolute_start
            + size
        )

        return (
            0 <= absolute_start
            <= absolute_end
            <= parent_size
        )

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> Path:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if not source.is_file():
            raise EmbeddedElfDecodeError(
                "embedded ELF source must be a regular file"
            )

        return source
