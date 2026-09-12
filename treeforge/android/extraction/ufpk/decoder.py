from __future__ import annotations

from pathlib import Path
from struct import unpack_from

from treeforge.android.extraction.ufpk.model import (
    UfpkDescriptor,
    UfpkStructure,
)


class UfpkDecodeError(
    ValueError,
):
    pass


class UfpkDecoder:
    """
    Decode the structurally validated UFPK descriptor chain.

    Recognition is independent of device, vendor, platform, Android version,
    filename, and individual descriptor identity.

    The current evidence-backed physical contract is:

      - outer magic "UFPK" at offset 0
      - descriptor-chain start at 0x54
      - descriptor kind is a literal u32 at +0x00
      - descriptor identity occupies +0x04..+0x1f
      - literal field at +0x28 is preserved
      - next physical boundary is the u32 at +0x30
      - each nonterminal next boundary points to another descriptor
      - the terminal next boundary equals physical EOF aligned to 16 bytes
    """

    MAGIC = b"UFPK"
    FIRST_DESCRIPTOR_OFFSET = 0x54
    DESCRIPTOR_MIN_SIZE = 0x34
    IDENTITY_OFFSET = 0x04
    IDENTITY_SIZE = 0x1C
    FIELD_28_OFFSET = 0x28
    NEXT_OFFSET = 0x30
    ALIGNMENT = 0x10
    MAX_DESCRIPTORS = 256

    def supports(
        self,
        path: Path,
    ) -> bool:
        try:
            self.decode(
                path
            )
        except (
            UfpkDecodeError,
            FileNotFoundError,
            OSError,
        ):
            return False

        return True

    def decode(
        self,
        path: Path,
    ) -> UfpkStructure:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not path.is_file():
            raise UfpkDecodeError(
                f"UFPK path is not a file: {path}"
            )

        data = path.read_bytes()

        if len(data) < (
            self.FIRST_DESCRIPTOR_OFFSET
            + self.DESCRIPTOR_MIN_SIZE
        ):
            raise UfpkDecodeError(
                f"artifact is too small for UFPK: {path}"
            )

        if not data.startswith(
            self.MAGIC
        ):
            raise UfpkDecodeError(
                f"UFPK magic is absent: {path}"
            )

        aligned_end = (
            (
                len(data)
                + self.ALIGNMENT
                - 1
            )
            & ~(
                self.ALIGNMENT
                - 1
            )
        )

        descriptors = []
        visited = set()
        current = (
            self.FIRST_DESCRIPTOR_OFFSET
        )

        for index in range(
            self.MAX_DESCRIPTORS
        ):
            if current in visited:
                raise UfpkDecodeError(
                    "UFPK descriptor chain contains a cycle"
                )

            visited.add(
                current
            )

            if (
                current
                + self.DESCRIPTOR_MIN_SIZE
                > len(data)
            ):
                raise UfpkDecodeError(
                    "UFPK descriptor is truncated: "
                    f"offset=0x{current:x}"
                )

            kind = unpack_from(
                "<I",
                data,
                current,
            )[0]

            if kind == 0:
                raise UfpkDecodeError(
                    "UFPK descriptor kind cannot be zero: "
                    f"offset=0x{current:x}"
                )

            identity_raw = data[
                current
                + self.IDENTITY_OFFSET:
                current
                + self.IDENTITY_OFFSET
                + self.IDENTITY_SIZE
            ]

            identity_bytes = (
                identity_raw
                .split(
                    b"\0",
                    1,
                )[0]
                .rstrip()
            )

            if not identity_bytes:
                raise UfpkDecodeError(
                    "UFPK descriptor identity is empty: "
                    f"offset=0x{current:x}"
                )

            if not all(
                0x20 <= byte < 0x7f
                for byte in identity_bytes
            ):
                raise UfpkDecodeError(
                    "UFPK descriptor identity is not printable ASCII: "
                    f"offset=0x{current:x}"
                )

            identity = (
                identity_bytes.decode(
                    "ascii"
                )
            )

            field_28 = unpack_from(
                "<I",
                data,
                current
                + self.FIELD_28_OFFSET,
            )[0]

            next_offset = unpack_from(
                "<I",
                data,
                current
                + self.NEXT_OFFSET,
            )[0]

            if next_offset <= current:
                raise UfpkDecodeError(
                    "UFPK descriptor next boundary does not advance: "
                    f"offset=0x{current:x}, "
                    f"next=0x{next_offset:x}"
                )

            if next_offset > aligned_end:
                raise UfpkDecodeError(
                    "UFPK descriptor next boundary exceeds aligned EOF: "
                    f"next=0x{next_offset:x}, "
                    f"aligned_eof=0x{aligned_end:x}"
                )

            terminal = (
                next_offset
                == aligned_end
            )

            physical_end = (
                len(data)
                if terminal
                else next_offset
            )

            if physical_end > len(data):
                raise UfpkDecodeError(
                    "UFPK physical descriptor extent exceeds file"
                )

            descriptor = UfpkDescriptor(
                index=index,
                offset=current,
                kind=kind,
                identity_raw=identity_raw,
                identity=identity,
                field_28=field_28,
                next_offset=next_offset,
                physical_end=physical_end,
                physical_size=(
                    physical_end
                    - current
                ),
            )

            descriptors.append(
                descriptor
            )

            if terminal:
                break

            #
            # The chain must land directly on another physically valid
            # descriptor. No filename or vendor identity is consulted.
            #
            if (
                next_offset
                + self.DESCRIPTOR_MIN_SIZE
                > len(data)
            ):
                raise UfpkDecodeError(
                    "UFPK nonterminal next descriptor is truncated"
                )

            next_identity = data[
                next_offset
                + self.IDENTITY_OFFSET:
                next_offset
                + self.IDENTITY_OFFSET
                + self.IDENTITY_SIZE
            ]

            next_identity = (
                next_identity
                .split(
                    b"\0",
                    1,
                )[0]
                .rstrip()
            )

            if (
                not next_identity
                or not all(
                    0x20 <= byte < 0x7f
                    for byte in next_identity
                )
            ):
                raise UfpkDecodeError(
                    "UFPK next boundary does not identify "
                    "another structural descriptor"
                )

            current = next_offset

        else:
            raise UfpkDecodeError(
                "UFPK descriptor chain exceeds safety limit"
            )

        if not descriptors:
            raise UfpkDecodeError(
                "UFPK exposes no descriptors"
            )

        if (
            descriptors[-1].next_offset
            != aligned_end
        ):
            raise UfpkDecodeError(
                "UFPK descriptor chain does not terminate "
                "at aligned physical EOF"
            )

        return UfpkStructure(
            physical_size=len(data),
            aligned_physical_end=aligned_end,
            descriptors=tuple(
                descriptors
            ),
        )
