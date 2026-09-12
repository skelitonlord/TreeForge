from __future__ import annotations

from pathlib import Path

from treeforge.core.binary import (
    align_up,
    read_uint32_le,
    read_uint64_le,
)
from treeforge.android.extraction.boot.metadata import (
    BootComponentLayout,
    BootContainerKind,
    BootImageStructure,
)


class BootImageStructureDecodeError(
    RuntimeError,
):
    """
    Raised when an ANDROID! boot-family image cannot be structurally decoded.
    """


class BootImageStructureDecoder:
    """
    Decode the physical structure of an Android ANDROID! boot-family image.

    Supported header versions:

    - v0
    - v1
    - v2
    - v3
    - v4

    The declared header version inside the image selects the exact decoder.
    There is no fallback guessing between versions.

    This component owns only structural information required by Extraction:

    - component byte sizes;
    - component byte offsets;
    - page/header layout;
    - image-boundary validation.

    It does not:

    - interpret Android policy;
    - parse extracted ramdisk contents;
    - infer build configuration;
    - depend on later semantic parsing layers.
    """

    BOOT_MAGIC = b"ANDROID!"

    BOOT_MAGIC_SIZE = 8

    #
    # AOSP legacy boot_img_hdr_v0 offsets.
    #
    V0_KERNEL_SIZE_OFFSET = 8
    V0_RAMDISK_SIZE_OFFSET = 16
    V0_SECOND_SIZE_OFFSET = 24
    V0_PAGE_SIZE_OFFSET = 36
    V0_HEADER_VERSION_OFFSET = 40
    V0_OS_VERSION_OFFSET = 44
    V0_CMDLINE_OFFSET = 64
    V0_CMDLINE_SIZE = 512
    V0_EXTRA_CMDLINE_OFFSET = 608
    V0_EXTRA_CMDLINE_SIZE = 1024

    #
    # boot_img_hdr_v0 packed size.
    #
    V0_HEADER_SIZE = 1632

    #
    # boot_img_hdr_v1 extension.
    #
    V1_RECOVERY_DTBO_SIZE_OFFSET = 1632
    V1_RECOVERY_DTBO_OFFSET_OFFSET = 1636
    V1_HEADER_SIZE_OFFSET = 1644

    V1_MINIMUM_HEADER_SIZE = 1648

    #
    # boot_img_hdr_v2 extension.
    #
    V2_DTB_SIZE_OFFSET = 1648

    V2_MINIMUM_HEADER_SIZE = 1660

    #
    # Modern boot_img_hdr_v3 / v4.
    #
    MODERN_KERNEL_SIZE_OFFSET = 8
    MODERN_RAMDISK_SIZE_OFFSET = 12
    MODERN_OS_VERSION_OFFSET = 16
    MODERN_HEADER_SIZE_OFFSET = 20
    MODERN_HEADER_VERSION_OFFSET = 40
    MODERN_CMDLINE_OFFSET = 44
    MODERN_CMDLINE_SIZE = 1536

    V3_STRUCT_SIZE = 1580

    V4_SIGNATURE_SIZE_OFFSET = 1580
    V4_STRUCT_SIZE = 1584

    MODERN_PAGE_SIZE = 4096

    #
    # Android 13+ GKI boot image v4:
    #
    # A zero signature_size header field does not necessarily mean the
    # physical boot-signature area is absent. Android's GKI verification
    # contract defines a trailing 16 KiB boot-signature region in that case.
    #
    # TreeForge still requires physical AVB0 evidence at the expected region
    # start before materializing this implicit form.
    #
    GKI_BOOT_SIGNATURE_SIZE = 16 * 1024
    AVB_VBMETA_MAGIC = b"AVB0"

    #
    # We only need enough bytes to decode every currently supported
    # structural header.
    #
    HEADER_READ_SIZE = 4096

    SUPPORTED_HEADER_VERSIONS = (
        0,
        1,
        2,
        3,
        4,
    )

    def decode(
        self,
        image_path: Path,
        *,
        kind: BootContainerKind,
    ) -> BootImageStructure:
        """
        Decode one ANDROID! boot-family image.

        ``kind`` comes from upstream artifact identity. It does not select the
        binary format version; the image's own declared header_version does.
        """

        image_path = (
            self._validate_image_path(
                image_path
            )
        )

        if not isinstance(
            kind,
            BootContainerKind,
        ):
            raise TypeError(
                "kind must be a BootContainerKind"
            )

        if (
            kind
            is BootContainerKind.VENDOR_BOOT
        ):
            raise ValueError(
                "Vendor boot images use the VNDRBOOT decoder"
            )

        image_size = (
            image_path.stat().st_size
        )

        with image_path.open(
            "rb",
        ) as handle:
            header = handle.read(
                self.HEADER_READ_SIZE
            )

        self._validate_magic(
            header
        )

        header_version = (
            self._detect_header_version(
                header
            )
        )

        if header_version not in (
            self.SUPPORTED_HEADER_VERSIONS
        ):
            raise BootImageStructureDecodeError(
                "Unsupported Android boot header version: "
                f"{header_version}"
            )

        if header_version <= 2:
            return self._decode_legacy(
                header,
                image_size=image_size,
                kind=kind,
                header_version=header_version,
            )

        return self._decode_modern(
            header,
            image_path=image_path,
            image_size=image_size,
            kind=kind,
            header_version=header_version,
        )

    def _detect_header_version(
        self,
        header: bytes,
    ) -> int:
        """
        Read the declared boot header version.

        Both legacy v0-v2 and modern v3-v4 retain header_version at byte
        offset 40, which allows deterministic dispatch before interpreting
        the version-specific remainder of the structure.
        """

        return read_uint32_le(
            header,
            self.V0_HEADER_VERSION_OFFSET,
        )

    def _decode_legacy(
        self,
        header: bytes,
        *,
        image_size: int,
        kind: BootContainerKind,
        header_version: int,
    ) -> BootImageStructure:
        """
        Decode boot header versions 0, 1, and 2.
        """

        page_size = read_uint32_le(
            header,
            self.V0_PAGE_SIZE_OFFSET,
        )

        if page_size <= 0:
            raise BootImageStructureDecodeError(
                "Legacy boot image declares an invalid "
                f"page size: {page_size}"
            )

        kernel_size = read_uint32_le(
            header,
            self.V0_KERNEL_SIZE_OFFSET,
        )

        ramdisk_size = read_uint32_le(
            header,
            self.V0_RAMDISK_SIZE_OFFSET,
        )

        second_size = read_uint32_le(
            header,
            self.V0_SECOND_SIZE_OFFSET,
        )

        os_version_raw = read_uint32_le(
            header,
            self.V0_OS_VERSION_OFFSET,
        )

        #
        # Legacy boot headers store the logical command line across two
        # independently NUL-terminated fixed-width arrays.
        #
        # Decode each field independently before concatenating them. Treating
        # the combined 1536 bytes as one C string would stop at padding in the
        # first field and incorrectly discard a populated extra_cmdline.
        #
        cmdline = (
            self._decode_c_string(
                header[
                    self.V0_CMDLINE_OFFSET:
                    (
                        self.V0_CMDLINE_OFFSET
                        + self.V0_CMDLINE_SIZE
                    )
                ]
            )
            + self._decode_c_string(
                header[
                    self.V0_EXTRA_CMDLINE_OFFSET:
                    (
                        self.V0_EXTRA_CMDLINE_OFFSET
                        + self.V0_EXTRA_CMDLINE_SIZE
                    )
                ]
            )
        )

        kernel_offset = page_size

        ramdisk_offset = align_up(
            kernel_offset
            + kernel_size,
            page_size,
        )

        second_offset = align_up(
            ramdisk_offset
            + ramdisk_size,
            page_size,
        )

        after_second = align_up(
            second_offset
            + second_size,
            page_size,
        )

        recovery_dtbo_size = 0
        recovery_dtbo_offset = 0

        dtb_size = 0
        dtb_offset = 0

        header_size = (
            self.V0_HEADER_SIZE
        )

        if header_version >= 1:
            recovery_dtbo_size = (
                read_uint32_le(
                    header,
                    self.V1_RECOVERY_DTBO_SIZE_OFFSET,
                )
            )

            declared_recovery_offset = (
                read_uint64_le(
                    header,
                    self.V1_RECOVERY_DTBO_OFFSET_OFFSET,
                )
            )

            header_size = read_uint32_le(
                header,
                self.V1_HEADER_SIZE_OFFSET,
            )

            if (
                header_size
                < self.V1_MINIMUM_HEADER_SIZE
            ):
                raise BootImageStructureDecodeError(
                    "boot header v1+ declares an invalid "
                    f"header size: {header_size}"
                )

            if recovery_dtbo_size:
                recovery_dtbo_offset = (
                    declared_recovery_offset
                )

                if (
                    recovery_dtbo_offset
                    < after_second
                ):
                    raise BootImageStructureDecodeError(
                        "recovery DTBO overlaps an earlier "
                        "boot component: "
                        f"offset={recovery_dtbo_offset}, "
                        f"minimum={after_second}"
                    )

        if header_version >= 2:
            dtb_size = read_uint32_le(
                header,
                self.V2_DTB_SIZE_OFFSET,
            )

            if (
                header_size
                < self.V2_MINIMUM_HEADER_SIZE
            ):
                raise BootImageStructureDecodeError(
                    "boot header v2 declares an invalid "
                    f"header size: {header_size}"
                )

            if dtb_size:
                if recovery_dtbo_size:
                    dtb_offset = align_up(
                        recovery_dtbo_offset
                        + recovery_dtbo_size,
                        page_size,
                    )
                else:
                    dtb_offset = (
                        after_second
                    )

        return BootImageStructure(
            kind=kind,
            header_version=header_version,
            header_size=header_size,
            page_size=page_size,
            os_version_raw=os_version_raw,
            cmdline=cmdline,
            kernel=BootComponentLayout(
                offset=kernel_offset,
                size=kernel_size,
            ),
            ramdisk=BootComponentLayout(
                offset=ramdisk_offset,
                size=ramdisk_size,
            ),
            second=BootComponentLayout(
                offset=second_offset,
                size=second_size,
            ),
            recovery_dtbo=(
                BootComponentLayout(
                    offset=(
                        recovery_dtbo_offset
                    ),
                    size=(
                        recovery_dtbo_size
                    ),
                )
            ),
            dtb=BootComponentLayout(
                offset=dtb_offset,
                size=dtb_size,
            ),
            boot_signature=(
                BootComponentLayout(
                    offset=0,
                    size=0,
                )
            ),
            boot_signature_declared_size=0,
            image_size=image_size,
        )

    def _decode_modern(
        self,
        header: bytes,
        *,
        image_path: Path,
        image_size: int,
        kind: BootContainerKind,
        header_version: int,
    ) -> BootImageStructure:
        """
        Decode boot header versions 3 and 4.
        """

        kernel_size = read_uint32_le(
            header,
            self.MODERN_KERNEL_SIZE_OFFSET,
        )

        ramdisk_size = read_uint32_le(
            header,
            self.MODERN_RAMDISK_SIZE_OFFSET,
        )

        os_version_raw = read_uint32_le(
            header,
            self.MODERN_OS_VERSION_OFFSET,
        )

        cmdline = self._decode_c_string(
            header[
                self.MODERN_CMDLINE_OFFSET:
                (
                    self.MODERN_CMDLINE_OFFSET
                    + self.MODERN_CMDLINE_SIZE
                )
            ]
        )

        header_size = read_uint32_le(
            header,
            self.MODERN_HEADER_SIZE_OFFSET,
        )

        minimum_header_size = (
            self.V4_STRUCT_SIZE
            if header_version == 4
            else self.V3_STRUCT_SIZE
        )

        if (
            header_size
            < minimum_header_size
        ):
            raise BootImageStructureDecodeError(
                f"boot header v{header_version} "
                "declares an invalid header size: "
                f"{header_size}"
            )

        page_size = (
            self.MODERN_PAGE_SIZE
        )

        kernel_offset = page_size

        ramdisk_offset = align_up(
            kernel_offset
            + kernel_size,
            page_size,
        )

        after_ramdisk = align_up(
            ramdisk_offset
            + ramdisk_size,
            page_size,
        )

        signature_declared_size = 0
        signature_size = 0
        signature_offset = 0

        if header_version == 4:
            signature_declared_size = (
                read_uint32_le(
                    header,
                    self.V4_SIGNATURE_SIZE_OFFSET,
                )
            )

            if signature_declared_size:
                signature_size = (
                    signature_declared_size
                )

                signature_offset = (
                    after_ramdisk
                )

            elif kind is BootContainerKind.BOOT:
                #
                # Android 13+ certified GKI boot.img keeps the literal
                # signature_size field at zero while retaining a physical
                # 16 KiB boot-signature region after the aligned payload.
                #
                # This implicit form belongs specifically to the generic
                # boot image. init_boot may instead place its partition AVB
                # VBMeta at this same physical boundary, so AVB0 alone must
                # not classify init_boot as carrying a GKI boot signature.
                #
                candidate_end = (
                    after_ramdisk
                    + self.GKI_BOOT_SIGNATURE_SIZE
                )

                if candidate_end <= image_size:
                    with image_path.open(
                        "rb"
                    ) as image:
                        image.seek(
                            after_ramdisk
                        )

                        candidate_magic = (
                            image.read(
                                len(
                                    self.AVB_VBMETA_MAGIC
                                )
                            )
                        )

                    if (
                        candidate_magic
                        == self.AVB_VBMETA_MAGIC
                    ):
                        signature_offset = (
                            after_ramdisk
                        )

                        signature_size = (
                            self.GKI_BOOT_SIGNATURE_SIZE
                        )

        return BootImageStructure(
            kind=kind,
            header_version=header_version,
            header_size=header_size,
            page_size=page_size,
            os_version_raw=os_version_raw,
            cmdline=cmdline,
            kernel=BootComponentLayout(
                offset=kernel_offset,
                size=kernel_size,
            ),
            ramdisk=BootComponentLayout(
                offset=ramdisk_offset,
                size=ramdisk_size,
            ),
            second=BootComponentLayout(
                offset=0,
                size=0,
            ),
            recovery_dtbo=(
                BootComponentLayout(
                    offset=0,
                    size=0,
                )
            ),
            dtb=BootComponentLayout(
                offset=0,
                size=0,
            ),
            boot_signature=(
                BootComponentLayout(
                    offset=signature_offset,
                    size=signature_size,
                )
            ),
            boot_signature_declared_size=(
                signature_declared_size
            ),
            image_size=image_size,
        )

    @staticmethod
    def _decode_c_string(
        value: bytes,
    ) -> str:
        """
        Decode one fixed-width NUL-terminated boot-header string.

        Boot header command lines are byte arrays whose meaningful content
        ends at the first NUL byte. Invalid UTF-8 is preserved losslessly
        through surrogate escapes rather than silently discarded.
        """

        if not isinstance(
            value,
            bytes,
        ):
            raise TypeError(
                "value must be bytes"
            )

        raw = value.split(
            b"\x00",
            1,
        )[0]

        return raw.decode(
            "utf-8",
            errors="surrogateescape",
        )

    def _validate_magic(
        self,
        header: bytes,
    ) -> None:
        if (
            len(header)
            < self.BOOT_MAGIC_SIZE
        ):
            raise BootImageStructureDecodeError(
                "Boot image is too small to contain "
                "ANDROID! magic"
            )

        if (
            header[
                0:
                self.BOOT_MAGIC_SIZE
            ]
            != self.BOOT_MAGIC
        ):
            raise BootImageStructureDecodeError(
                "Invalid Android boot image magic"
            )

    @staticmethod
    def _validate_image_path(
        image_path: Path,
    ) -> Path:
        if not isinstance(
            image_path,
            Path,
        ):
            raise TypeError(
                "image_path must be a pathlib.Path"
            )

        normalized = (
            image_path
            .expanduser()
            .resolve()
        )

        if not normalized.exists():
            raise FileNotFoundError(
                normalized
            )

        if not normalized.is_file():
            raise BootImageStructureDecodeError(
                "boot image must be a regular file: "
                f"{normalized}"
            )

        if (
            normalized.stat().st_size
            <= 0
        ):
            raise BootImageStructureDecodeError(
                "boot image cannot be empty: "
                f"{normalized}"
            )

        return normalized