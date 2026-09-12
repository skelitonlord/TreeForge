from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from treeforge.android.extraction.boot.metadata import (
    BootComponentLayout,
    BootImageStructure,
    VendorBootImageStructure,
)
from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class BootImageExtractionError(
    RuntimeError,
):
    """
    Raised when a boot-family image component cannot be materialized.
    """


class BootImageExtractor:
    """
    Materialize physical components from Extraction-owned boot structures.

    Structural container interpretation is performed by Extraction decoders.

    This extractor consumes immutable physical structure and materializes every
    currently modeled physical region without performing higher-level semantic
    interpretation.

    Every produced component preserves:

    - exact Discovery source identity;
    - exact Extraction parent identity;
    - container/header evidence;
    - component offset and size;
    - SHA-256;
    - physical size.
    """

    HASH_CHUNK_SIZE = (
        1024 * 1024
    )

    def extract_boot(
        self,
        parent: ExtractedArtifact,
        structure: BootImageStructure,
        destination_root: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Extract all physically present regions from boot.img.
        """

        return self.extract_android_boot(
            parent,
            structure,
            destination_root,
        )

    def extract_init_boot(
        self,
        parent: ExtractedArtifact,
        structure: BootImageStructure,
        destination_root: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Extract all physically present regions from init_boot.img.

        Modern init_boot normally contains only a ramdisk, but Extraction does
        not hard-code that assumption. The decoded structure remains
        authoritative.
        """

        return self.extract_android_boot(
            parent,
            structure,
            destination_root,
        )

    def extract_recovery(
        self,
        parent: ExtractedArtifact,
        structure: BootImageStructure,
        destination_root: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Extract all physically present regions from an ANDROID! recovery image.
        """

        return self.extract_android_boot(
            parent,
            structure,
            destination_root,
        )

    def extract_vendor_boot(
        self,
        parent: ExtractedArtifact,
        structure: VendorBootImageStructure,
        destination_root: Path,
        *,
        container_kind: str = "vendor_boot",
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Extract all physically modeled regions from vendor_boot.img.

        For v4 this includes the raw vendor ramdisk table and bootconfig
        regions. Their higher-level semantic interpretation is intentionally
        deferred.
        """

        self._validate_parent(
            parent
        )

        self._validate_destination_root(
            destination_root
        )

        if not isinstance(
            container_kind,
            str,
        ):
            raise TypeError(
                "container_kind must be a string"
            )

        container_kind = (
            container_kind.strip()
        )

        if not container_kind:
            raise ValueError(
                "container_kind cannot be empty"
            )

        if not isinstance(
            structure,
            VendorBootImageStructure,
        ):
            raise TypeError(
                "structure must be a VendorBootImageStructure"
            )

        artifacts: list[
            ExtractedArtifact
        ] = []

        self._append_component(
            artifacts,
            parent=parent,
            destination_root=destination_root,
            semantic_name="ramdisk",
            layout=structure.vendor_ramdisk,
            header_version=(
                structure.header_version
            ),
            header_size=(
                structure.header_size
            ),
            page_size=(
                structure.page_size
            ),
            container_kind=container_kind,
        )

        self._append_component(
            artifacts,
            parent=parent,
            destination_root=destination_root,
            semantic_name="dtb",
            layout=structure.dtb,
            header_version=(
                structure.header_version
            ),
            header_size=(
                structure.header_size
            ),
            page_size=(
                structure.page_size
            ),
            container_kind=container_kind,
        )

        self._append_component(
            artifacts,
            parent=parent,
            destination_root=destination_root,
            semantic_name=(
                "vendor_ramdisk_table"
            ),
            layout=(
                structure
                .vendor_ramdisk_table
            ),
            header_version=(
                structure.header_version
            ),
            header_size=(
                structure.header_size
            ),
            page_size=(
                structure.page_size
            ),
            container_kind=container_kind,
            extra_facts=(
                ExtractionFact(
                    name=(
                        "table_entry_count"
                    ),
                    value=(
                        structure
                        .vendor_ramdisk_table_entry_num
                    ),
                ),
                ExtractionFact(
                    name=(
                        "table_entry_size_bytes"
                    ),
                    value=(
                        structure
                        .vendor_ramdisk_table_entry_size
                    ),
                ),
            ),
        )

        self._append_component(
            artifacts,
            parent=parent,
            destination_root=destination_root,
            semantic_name="bootconfig",
            layout=structure.bootconfig,
            header_version=(
                structure.header_version
            ),
            header_size=(
                structure.header_size
            ),
            page_size=(
                structure.page_size
            ),
            container_kind=container_kind,
        )

        return tuple(
            artifacts
        )

    def extract_android_boot(
        self,
        parent: ExtractedArtifact,
        structure: BootImageStructure,
        destination_root: Path,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Extract every physically present region from one decoded ANDROID!
        boot-family container.

        The BootImageStructure kind preserves the exact upstream container
        identity while the extraction mechanism remains format-generic.
        """

        self._validate_parent(
            parent
        )

        self._validate_destination_root(
            destination_root
        )

        if not isinstance(
            structure,
            BootImageStructure,
        ):
            raise TypeError(
                "structure must be a BootImageStructure"
            )

        artifacts: list[
            ExtractedArtifact
        ] = []

        container_kind = (
            structure.kind.value
        )

        for (
            semantic_name,
            layout,
        ) in (
            (
                "kernel",
                structure.kernel,
            ),
            (
                "ramdisk",
                structure.ramdisk,
            ),
            (
                "second",
                structure.second,
            ),
            (
                "recovery_dtbo",
                structure.recovery_dtbo,
            ),
            (
                "dtb",
                structure.dtb,
            ),
            (
                "boot_signature",
                structure.boot_signature,
            ),
        ):
            self._append_component(
                artifacts,
                parent=parent,
                destination_root=(
                    destination_root
                ),
                semantic_name=(
                    semantic_name
                ),
                layout=layout,
                header_version=(
                    structure.header_version
                ),
                header_size=(
                    structure.header_size
                ),
                page_size=(
                    structure.page_size
                ),
                container_kind=(
                    container_kind
                ),
            )

        return tuple(
            artifacts
        )

    def _append_component(
        self,
        artifacts: list[
            ExtractedArtifact
        ],
        *,
        parent: ExtractedArtifact,
        destination_root: Path,
        semantic_name: str,
        layout: BootComponentLayout,
        header_version: int,
        header_size: int,
        page_size: int,
        container_kind: str,
        extra_facts: tuple[
            ExtractionFact,
            ...,
        ] = (),
    ) -> None:
        if not isinstance(
            layout,
            BootComponentLayout,
        ):
            raise TypeError(
                "layout must be a BootComponentLayout"
            )

        if not layout.present:
            return

        artifacts.append(
            self._extract_component(
                parent=parent,
                destination=(
                    destination_root
                    / semantic_name
                ),
                semantic_name=(
                    semantic_name
                ),
                offset=layout.offset,
                size=layout.size,
                structural_facts=(
                    ExtractionFact(
                        name="container_kind",
                        value=container_kind,
                    ),
                    ExtractionFact(
                        name="header_version",
                        value=header_version,
                    ),
                    ExtractionFact(
                        name="header_size_bytes",
                        value=header_size,
                    ),
                    ExtractionFact(
                        name="page_size_bytes",
                        value=page_size,
                    ),
                    *extra_facts,
                ),
            )
        )

    def _extract_component(
        self,
        *,
        parent: ExtractedArtifact,
        destination: Path,
        semantic_name: str,
        offset: int,
        size: int,
        structural_facts: tuple[
            ExtractionFact,
            ...,
        ] = (),
    ) -> ExtractedArtifact:
        if (
            not isinstance(
                offset,
                int,
            )
            or isinstance(
                offset,
                bool,
            )
        ):
            raise TypeError(
                "offset must be an integer"
            )

        if (
            not isinstance(
                size,
                int,
            )
            or isinstance(
                size,
                bool,
            )
        ):
            raise TypeError(
                "size must be an integer"
            )

        if offset < 0:
            raise ValueError(
                "offset must not be negative"
            )

        if size <= 0:
            raise ValueError(
                "size must be greater than zero"
            )

        if not isinstance(
            structural_facts,
            tuple,
        ):
            raise TypeError(
                "structural_facts must be a tuple"
            )

        for fact in structural_facts:
            if not isinstance(
                fact,
                ExtractionFact,
            ):
                raise TypeError(
                    "structural_facts must contain "
                    "ExtractionFact instances"
                )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination.unlink(
            missing_ok=True
        )

        try:
            with parent.path.open(
                "rb"
            ) as source:
                source.seek(
                    offset
                )

                remaining = size

                with destination.open(
                    "wb"
                ) as output:
                    while remaining:
                        chunk = source.read(
                            min(
                                self.HASH_CHUNK_SIZE,
                                remaining,
                            )
                        )

                        if not chunk:
                            raise (
                                BootImageExtractionError(
                                    "Boot component ended before "
                                    "its declared size: "
                                    f"{parent.path} "
                                    f"{semantic_name}"
                                )
                            )

                        output.write(
                            chunk
                        )

                        remaining -= len(
                            chunk
                        )

        except BaseException:
            destination.unlink(
                missing_ok=True
            )

            raise

        actual_size = (
            destination.stat().st_size
        )

        if actual_size != size:
            destination.unlink(
                missing_ok=True
            )

            raise BootImageExtractionError(
                "Boot component size mismatch for "
                f"{semantic_name}: "
                f"expected {size}, "
                f"got {actual_size}"
            )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=(
                ExtractionArtifactKind.FILE
            ),
            operation=(
                ExtractionOperation
                .BOOT_COMPONENT_EXTRACTION
            ),
            semantic_name=semantic_name,
            parent=parent,
            facts=(
                ExtractionFact(
                    name="offset_bytes",
                    value=offset,
                ),
                ExtractionFact(
                    name="declared_size_bytes",
                    value=size,
                ),
                *structural_facts,
            ),
            tool=ExtractionToolEvidence(
                name="treeforge-boot-container",
            ),
            content_sha256=(
                self._sha256_file(
                    destination
                )
            ),
            size_bytes=actual_size,
        )

    @staticmethod
    def _validate_parent(
        parent: ExtractedArtifact,
    ) -> None:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise BootImageExtractionError(
                "boot extraction parent must be a file"
            )

        if not parent.path.exists():
            raise FileNotFoundError(
                f"boot image does not exist: "
                f"{parent.path}"
            )

        if not parent.path.is_file():
            raise BootImageExtractionError(
                "boot extraction parent must be "
                f"a regular file: {parent.path}"
            )

    @staticmethod
    def _validate_destination_root(
        destination_root: Path,
    ) -> None:
        if not isinstance(
            destination_root,
            Path,
        ):
            raise TypeError(
                "destination_root must be a pathlib.Path"
            )

        if (
            destination_root.exists()
            and not destination_root.is_dir()
        ):
            raise NotADirectoryError(
                destination_root
            )

    @classmethod
    def _sha256_file(
        cls,
        path: Path,
    ) -> str:
        digest = sha256()

        with path.open(
            "rb"
        ) as stream:
            while True:
                chunk = stream.read(
                    cls.HASH_CHUNK_SIZE
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return digest.hexdigest()