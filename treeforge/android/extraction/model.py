from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from treeforge.android.providers.artifact import (
    ProviderArtifact,
    ProviderArtifactKind,
)


class ExtractionArtifactKind(
    StrEnum,
):
    """
    Broad physical form of one artifact available through Extraction.

    This describes physical accessibility only. It does not assign Android
    semantic meaning such as partition type, filesystem role, or boot role.
    """

    FILE = "file"
    DIRECTORY = "directory"


class ExtractionOperation(
    StrEnum,
):
    """
    Canonical source-to-artifact operations owned by Extraction.

    Operations record what TreeForge actually did.

    They must never be inferred merely from path equality or inequality.
    """

    SOURCE_ADOPTION = (
        "source_adoption"
    )

    SOURCE_MATERIALIZATION = (
        "source_materialization"
    )

    ARCHIVE_MEMBER_EXTRACTION = (
        "archive_member_extraction"
    )

    LOGICAL_PARTITION_EXTRACTION = (
        "logical_partition_extraction"
    )

    SPARSE_TO_RAW = (
        "sparse_to_raw"
    )

    FILESYSTEM_EXTRACTION = (
        "filesystem_extraction"
    )

    BOOT_COMPONENT_EXTRACTION = (
        "boot_component_extraction"
    )

    AVB_REGION_EXTRACTION = (
        "avb_region_extraction"
    )

    RAMDISK_DECOMPRESSION = (
        "ramdisk_decompression"
    )

    KERNEL_DECOMPRESSION = (
        "kernel_decompression"
    )

    CPIO_EXTRACTION = (
        "cpio_extraction"
    )

    NESTED_ARTIFACT_DISCOVERY = (
        "nested_artifact_discovery"
    )

    APEX_CONTAINER_EXTRACTION = (
        "apex_container_extraction"
    )

    DTBO_ENTRY_EXTRACTION = (
        "dtbo_entry_extraction"
    )

    FDT_MEMBER_EXTRACTION = (
        "fdt_member_extraction"
    )

    FBPK_ENTRY_EXTRACTION = (
        "fbpk_entry_extraction"
    )

    BOOT_FIRMWARE_PAYLOAD_EXTRACTION = (
        "boot_firmware_payload_extraction"
    )

    UFPK_DESCRIPTOR_EXTRACTION = (
        "ufpk_descriptor_extraction"
    )

    SFLB_ENTRY_EXTRACTION = (
        "sflb_entry_extraction"
    )

    SFLB_RESOURCE_DECOMPRESSION = (
        "sflb_resource_decompression"
    )

    EMBEDDED_ELF_EXTRACTION = (
        "embedded_elf_extraction"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class ExtractionFact:
    """
    Immutable fact established while materializing or transforming an artifact.

    Extraction facts are additive derivation evidence. They do not replace
    upstream ProviderArtifact provenance, parent lineage, semantic identity,
    tool evidence, content hashes, or physical-size evidence.

    ``name`` identifies the fact within the producing extraction operation.

    ``value`` contains the exact scalar value observed or established by that
    operation.
    """

    name: str
    value: str | int | bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        normalized_name = (
            self.name.strip()
        )

        if not normalized_name:
            raise ValueError(
                "name cannot be empty"
            )

        object.__setattr__(
            self,
            "name",
            normalized_name,
        )

        if not isinstance(
            self.value,
            (
                str,
                int,
                bool,
            ),
        ):
            raise TypeError(
                "value must be a string, integer, or boolean"
            )
        
@dataclass(
    frozen=True,
    slots=True,
)
class ExtractionToolEvidence:
    """
    Immutable evidence describing the implementation that performed a
    transformation.

    Tool evidence is descriptive provenance. It does not become artifact
    identity.
    """

    name: str
    executable: str | None = None

    command: tuple[
        str,
        ...,
    ] = ()

    returncode: int | None = None

    stdout: str | None = None
    stderr: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name.strip():
            raise ValueError(
                "name cannot be empty"
            )

        if (
            self.executable is not None
            and not isinstance(
                self.executable,
                str,
            )
        ):
            raise TypeError(
                "executable must be a string or None"
            )

        if (
            self.executable is not None
            and not self.executable.strip()
        ):
            raise ValueError(
                "executable cannot be empty"
            )

        if not isinstance(
            self.command,
            tuple,
        ):
            raise TypeError(
                "command must be a tuple"
            )

        for argument in self.command:
            if not isinstance(
                argument,
                str,
            ):
                raise TypeError(
                    "command must contain strings"
                )

        if (
            self.returncode is not None
            and (
                isinstance(
                    self.returncode,
                    bool,
                )
                or not isinstance(
                    self.returncode,
                    int,
                )
            )
        ):
            raise TypeError(
                "returncode must be an int or None"
            )

        for (
            field_name,
            value,
        ) in (
            (
                "stdout",
                self.stdout,
            ),
            (
                "stderr",
                self.stderr,
            ),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class ExtractedArtifact:
    """
    Canonical immutable artifact available through TreeForge Extraction.

    ``source`` preserves the exact Discovery ProviderArtifact when one exists.

    Manual or other provider-agnostic input paths may legitimately have no
    ProviderArtifact. Their extraction lineage remains explicit through their
    artifact path and parent chain.

    ``parent`` preserves the immediate extraction/materialization ancestor.

    ``semantic_name`` records an identity explicitly established by the
    extraction operation or its canonical upstream interpretation.

    Examples include:

        system_a
        vendor_a
        boot
        init_boot
        kernel
        ramdisk

    It must not be populated merely by guessing from a filename.

    ``operation`` records what TreeForge actually did to make this artifact
    available.

    ``SOURCE_ADOPTION`` means the artifact already existed and TreeForge
    adopted that directly accessible artifact into canonical Extraction state
    without claiming to have produced it.

    ``content_sha256`` and ``size_bytes`` contain evidence available after the
    artifact exists.
    """

    source: ProviderArtifact | None

    path: Path

    kind: ExtractionArtifactKind

    operation: ExtractionOperation

    semantic_name: str | None = None

    parent: ExtractedArtifact | None = None

    tool: ExtractionToolEvidence | None = None

    facts: tuple[
        ExtractionFact,
        ...,
    ] = ()

    content_sha256: str | None = None

    size_bytes: int | None = None

    def __post_init__(
        self,
    ) -> None:
        if (
            self.source is not None
            and not isinstance(
                self.source,
                ProviderArtifact,
            )
        ):
            raise TypeError(
                "source must be a ProviderArtifact or None"
            )

        if not isinstance(
            self.path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        if not self.path.exists():
            raise FileNotFoundError(
                "extracted artifact does not exist: "
                f"{self.path}"
            )

        if not isinstance(
            self.kind,
            ExtractionArtifactKind,
        ):
            raise TypeError(
                "kind must be an ExtractionArtifactKind"
            )

        if (
            self.kind
            is ExtractionArtifactKind.FILE
            and not self.path.is_file()
        ):
            raise ValueError(
                "FILE extraction artifact must reference "
                f"a regular file: {self.path}"
            )

        if (
            self.kind
            is ExtractionArtifactKind.DIRECTORY
            and not self.path.is_dir()
        ):
            raise ValueError(
                "DIRECTORY extraction artifact must reference "
                f"a directory: {self.path}"
            )

        if not isinstance(
            self.operation,
            ExtractionOperation,
        ):
            raise TypeError(
                "operation must be an ExtractionOperation"
            )

        if self.semantic_name is not None:
            if not isinstance(
                self.semantic_name,
                str,
            ):
                raise TypeError(
                    "semantic_name must be a string or None"
                )

            if not self.semantic_name.strip():
                raise ValueError(
                    "semantic_name cannot be empty"
                )

        if (
            self.parent is not None
            and not isinstance(
                self.parent,
                ExtractedArtifact,
            )
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact or None"
            )

        if (
            self.parent is not None
            and self.parent.source
            is not self.source
        ):
            raise ValueError(
                "derived extraction artifacts must preserve "
                "the exact ProviderArtifact source identity"
            )

        if (
            self.tool is not None
            and not isinstance(
                self.tool,
                ExtractionToolEvidence,
            )
        ):
            raise TypeError(
                "tool must be ExtractionToolEvidence or None"
            )

        if not isinstance(
            self.facts,
            tuple,
        ):
            raise TypeError(
                "facts must be a tuple"
            )

        fact_names: set[
            str
        ] = set()

        for fact in self.facts:
            if not isinstance(
                fact,
                ExtractionFact,
            ):
                raise TypeError(
                    "facts must contain ExtractionFact instances"
                )

            if fact.name in fact_names:
                raise ValueError(
                    "extraction artifact facts must "
                    "have unique names: "
                    f"{fact.name}"
                )

            fact_names.add(
                fact.name
            )

        if self.content_sha256 is not None:
            if not isinstance(
                self.content_sha256,
                str,
            ):
                raise TypeError(
                    "content_sha256 must be a string or None"
                )

            normalized_hash = (
                self.content_sha256
                .strip()
                .lower()
            )

            if (
                len(normalized_hash) != 64
                or any(
                    character
                    not in "0123456789abcdef"
                    for character
                    in normalized_hash
                )
            ):
                raise ValueError(
                    "content_sha256 must be a 64-character "
                    "hexadecimal SHA-256 digest"
                )

            object.__setattr__(
                self,
                "content_sha256",
                normalized_hash,
            )

        if self.size_bytes is not None:
            if (
                isinstance(
                    self.size_bytes,
                    bool,
                )
                or not isinstance(
                    self.size_bytes,
                    int,
                )
            ):
                raise TypeError(
                    "size_bytes must be an int or None"
                )

            if self.size_bytes < 0:
                raise ValueError(
                    "size_bytes cannot be negative"
                )

    @property
    def origin_image(
        self,
    ) -> str | None:
        """
        Return the exact originating factory-image member name.

        Extraction descendants preserve the exact Discovery ProviderArtifact
        source identity across every derivation edge. Consequently, any
        artifact descended from a discovered image can identify the image
        from which its evidence ultimately originated.

        Examples:

        - boot.img kernel -> boot.img
        - boot.img ramdisk -> boot.img
        - vendor_boot.img ramdisk fragment -> vendor_boot.img
        - dtbo.img DT entry -> dtbo.img
        - super.img logical-partition child -> super.img

        This is lineage evidence only. It does not imply that every derived
        artifact must be copied directly into the rebuilt image; later stages
        determine reconstruction disposition.
        """

        source = self.source

        if source is None:
            return None

        if (
            source.kind
            is not ProviderArtifactKind.IMAGE
        ):
            return None

        return source.name

    @property
    def source_name(
        self,
    ) -> str | None:
        """
        Return the canonical Discovery source identity when one exists.
        """

        if self.source is None:
            return None

        return self.source.source_name

    @property
    def is_derived(
        self,
    ) -> bool:
        """
        Return whether this artifact has an earlier extraction artifact.
        """

        return self.parent is not None

    @property
    def lineage(
        self,
    ) -> tuple[
        ExtractedArtifact,
        ...,
    ]:
        """
        Return extraction lineage from earliest retained artifact to self.

        Discovery provenance remains available through ``source`` and is not
        duplicated into this tuple.
        """

        lineage: list[
            ExtractedArtifact
        ] = []

        current: (
            ExtractedArtifact
            | None
        ) = self

        while current is not None:
            lineage.append(
                current
            )

            current = (
                current.parent
            )

        lineage.reverse()

        return tuple(
            lineage
        )

    def fact(
        self,
        name: str,
    ) -> ExtractionFact | None:
        """
        Return one exact extraction-established derivation fact.
        """

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        normalized_name = (
            name.strip()
        )

        if not normalized_name:
            raise ValueError(
                "name cannot be empty"
            )

        for fact in self.facts:
            if fact.name == normalized_name:
                return fact

        return None