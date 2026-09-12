from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from treeforge.android.extraction.model import (
    ExtractionOperation,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)

if TYPE_CHECKING:
    from treeforge.android.parsing.result import (
        ParsedBootImage,
    )


class AndroidBootstrapRecoveryPartitionDisposition(
    StrEnum
):
    """
    Bootstrap disposition for one canonical recovery partition expectation.

    PHYSICAL_READ_PROBE:
      Canonical Parsing proves a physical boot-family partition and retains
      a non-zero canonical image size. Runtime may compare this expectation
      against sysfs and may later open the matching block target read-only.

    LOGICAL_UNSUPPORTED:
      Canonical Parsing proves that the partition originates inside super.
      The first recovery runtime deliberately does not realize dynamic/logical
      partition targets.

    SIZE_UNRESOLVED:
      Canonical identity exists, but no non-zero canonical image size is
      available. Runtime identity may still be reported, but read-target
      eligibility is withheld.
    """

    PHYSICAL_READ_PROBE = "physical_read_probe"
    LOGICAL_UNSUPPORTED = "logical_unsupported"
    SIZE_UNRESOLVED = "size_unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRecoveryPartitionExpectation:
    """
    One canonical boot-family expectation projected for recovery.

    ``canonical_name`` is the slot-neutral canonical identity used to match
    runtime PARTNAME-derived records.

    ``canonical_image_size_bytes`` is deliberately named as image size rather
    than partition capacity. The canonical size is the exact Extraction artifact size retained at the
    Parsing boundary. Recovery must never interpret this artifact size as
    proof of exact runtime partition capacity.

    For the initial read-only contract, runtime requires only:

      runtime_capacity >= canonical_image_size

    Exact capacity equality must not be inferred from this model.

    Slot policy is also not inferred. Any canonical slot suffixes are retained
    as evidence only; runtime A/B pairing remains derived independently from
    live sysfs.
    """

    canonical_name: str

    source_partition_names: tuple[
        str,
        ...,
    ]

    container_format: str
    container_kind: str

    canonical_image_size_bytes: int | None

    logical: bool

    recorded_slot_suffixes: tuple[
        str,
        ...,
    ]

    source_artifact_paths: tuple[
        str,
        ...,
    ]

    disposition: (
        AndroidBootstrapRecoveryPartitionDisposition
    )

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.canonical_name,
                str,
            )
            or not self.canonical_name
        ):
            raise ValueError(
                "recovery partition canonical_name must be non-empty"
            )

        if "\x00" in self.canonical_name:
            raise ValueError(
                "recovery partition canonical_name cannot contain NUL"
            )

        if (
            not isinstance(
                self.source_partition_names,
                tuple,
            )
            or not self.source_partition_names
            or not all(
                isinstance(value, str)
                and value
                for value
                in self.source_partition_names
            )
        ):
            raise ValueError(
                "source_partition_names must be a non-empty tuple "
                "of non-empty strings"
            )

        if (
            len(
                self.source_partition_names
            )
            != len(
                set(
                    self.source_partition_names
                )
            )
        ):
            raise ValueError(
                "source_partition_names must be unique"
            )

        if (
            not isinstance(
                self.container_format,
                str,
            )
            or not self.container_format
        ):
            raise ValueError(
                "container_format must be non-empty"
            )

        if (
            not isinstance(
                self.container_kind,
                str,
            )
            or not self.container_kind
        ):
            raise ValueError(
                "container_kind must be non-empty"
            )

        if (
            self.canonical_image_size_bytes
            is not None
            and (
                isinstance(
                    self.canonical_image_size_bytes,
                    bool,
                )
                or not isinstance(
                    self.canonical_image_size_bytes,
                    int,
                )
                or self.canonical_image_size_bytes <= 0
            )
        ):
            raise ValueError(
                "canonical_image_size_bytes must be None or positive"
            )

        if not isinstance(
            self.logical,
            bool,
        ):
            raise TypeError(
                "logical must be bool"
            )

        if (
            not isinstance(
                self.recorded_slot_suffixes,
                tuple,
            )
            or not all(
                isinstance(value, str)
                and value.startswith("_")
                and len(value) > 1
                for value
                in self.recorded_slot_suffixes
            )
        ):
            raise ValueError(
                "recorded_slot_suffixes contains an invalid suffix"
            )

        if (
            len(
                self.recorded_slot_suffixes
            )
            != len(
                set(
                    self.recorded_slot_suffixes
                )
            )
        ):
            raise ValueError(
                "recorded_slot_suffixes must be unique"
            )

        if (
            not isinstance(
                self.source_artifact_paths,
                tuple,
            )
            or not self.source_artifact_paths
            or not all(
                isinstance(value, str)
                and value
                for value
                in self.source_artifact_paths
            )
        ):
            raise ValueError(
                "source_artifact_paths must be a non-empty tuple "
                "of non-empty strings"
            )

        if (
            len(
                self.source_artifact_paths
            )
            != len(
                set(
                    self.source_artifact_paths
                )
            )
        ):
            raise ValueError(
                "source_artifact_paths must be unique"
            )

        if not isinstance(
            self.disposition,
            AndroidBootstrapRecoveryPartitionDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootstrapRecoveryPartitionDisposition"
            )

        expected_disposition = (
            AndroidBootstrapRecoveryPartitionDisposition
            .LOGICAL_UNSUPPORTED
            if self.logical
            else (
                AndroidBootstrapRecoveryPartitionDisposition
                .SIZE_UNRESOLVED
                if self.canonical_image_size_bytes
                is None
                else (
                    AndroidBootstrapRecoveryPartitionDisposition
                    .PHYSICAL_READ_PROBE
                )
            )
        )

        if (
            self.disposition
            is not expected_disposition
        ):
            raise ValueError(
                "recovery partition disposition does not match "
                "canonical physical/size evidence"
            )

    @property
    def read_probe_candidate(
        self,
    ) -> bool:
        return (
            self.disposition
            is (
                AndroidBootstrapRecoveryPartitionDisposition
                .PHYSICAL_READ_PROBE
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRecoveryPartitionManifest:
    """
    Bootstrap-owned projection of canonical Parsing evidence for recovery.

    The exact AndroidParsingResult object is retained so construction cannot
    silently detach recovery policy from the canonical Parsing handoff.
    """

    parsing: AndroidParsingResult

    expectations: tuple[
        AndroidBootstrapRecoveryPartitionExpectation,
        ...,
    ]

    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if self.schema_version != 1:
            raise ValueError(
                "unsupported recovery partition manifest schema"
            )

        if not isinstance(
            self.expectations,
            tuple,
        ):
            raise TypeError(
                "expectations must be a tuple"
            )

        if not all(
            isinstance(
                expectation,
                AndroidBootstrapRecoveryPartitionExpectation,
            )
            for expectation
            in self.expectations
        ):
            raise TypeError(
                "manifest expectations contain an invalid value"
            )

        canonical_names = tuple(
            expectation.canonical_name
            for expectation
            in self.expectations
        )

        if (
            len(canonical_names)
            != len(
                set(
                    canonical_names
                )
            )
        ):
            raise ValueError(
                "recovery manifest canonical names must be unique"
            )

    @property
    def expectation_count(
        self,
    ) -> int:
        return len(
            self.expectations
        )

    @property
    def read_probe_candidate_count(
        self,
    ) -> int:
        return sum(
            1
            for expectation
            in self.expectations
            if expectation.read_probe_candidate
        )


class AndroidBootstrapRecoveryPartitionManifestBuilder:
    """
    Project canonical Parsing boot-family identities into recovery.

    No partition-name allowlist exists here.

    Duplicate slot-specific factory entries are collapsed by canonical
    InventoryPartition.base_name only when all structural facts agree.
    Conflicting canonical evidence is rejected rather than guessed.
    """

    @staticmethod
    def _expectation_for_group(
        canonical_name: str,
        images: tuple[
            ParsedBootImage,
            ...,
        ],
    ) -> AndroidBootstrapRecoveryPartitionExpectation:
        if not images:
            raise ValueError(
                "recovery partition group cannot be empty"
            )

        container_formats = {
            image.container_format
            for image
            in images
        }

        if len(container_formats) != 1:
            raise ValueError(
                "canonical recovery partition has conflicting "
                f"container formats: {canonical_name}"
            )

        container_kinds = {
            image.container_kind
            for image
            in images
        }

        if len(container_kinds) != 1:
            raise ValueError(
                "canonical recovery partition has conflicting "
                f"container kinds: {canonical_name}"
            )

        logical_values = {
            any(
                artifact.operation
                is (
                    ExtractionOperation
                    .LOGICAL_PARTITION_EXTRACTION
                )
                for artifact
                in image.partition.artifact.lineage
            )
            for image
            in images
        }

        if len(logical_values) != 1:
            raise ValueError(
                "canonical recovery partition has conflicting "
                f"logical dispositions: {canonical_name}"
            )

        known_sizes = {
            image.partition.artifact.size_bytes
            for image
            in images
            if (
                image.partition.artifact.size_bytes
                is not None
                and image.partition.artifact.size_bytes > 0
            )
        }

        if len(known_sizes) > 1:
            raise ValueError(
                "canonical recovery partition has conflicting "
                f"image sizes: {canonical_name}"
            )

        canonical_image_size_bytes = (
            next(
                iter(
                    known_sizes
                )
            )
            if known_sizes
            else None
        )

        logical = next(
            iter(
                logical_values
            )
        )

        disposition = (
            AndroidBootstrapRecoveryPartitionDisposition
            .LOGICAL_UNSUPPORTED
            if logical
            else (
                AndroidBootstrapRecoveryPartitionDisposition
                .SIZE_UNRESOLVED
                if canonical_image_size_bytes
                is None
                else (
                    AndroidBootstrapRecoveryPartitionDisposition
                    .PHYSICAL_READ_PROBE
                )
            )
        )

        source_partition_names = tuple(
            dict.fromkeys(
                image.partition.name
                for image
                in images
            )
        )

        recorded_slot_suffixes = tuple(
            dict.fromkeys(
                image.partition.slot_suffix
                for image
                in images
                if image.partition.slot_suffix
                is not None
            )
        )

        source_artifact_paths = tuple(
            dict.fromkeys(
                image.partition.artifact.path.as_posix()
                for image
                in images
            )
        )

        return AndroidBootstrapRecoveryPartitionExpectation(
            canonical_name=canonical_name,
            source_partition_names=(
                source_partition_names
            ),
            container_format=next(
                iter(
                    container_formats
                )
            ),
            container_kind=next(
                iter(
                    container_kinds
                )
            ),
            canonical_image_size_bytes=(
                canonical_image_size_bytes
            ),
            logical=logical,
            recorded_slot_suffixes=(
                recorded_slot_suffixes
            ),
            source_artifact_paths=(
                source_artifact_paths
            ),
            disposition=disposition,
        )

    @classmethod
    def build(
        cls,
        parsing: AndroidParsingResult,
    ) -> AndroidBootstrapRecoveryPartitionManifest:
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        groups: dict[
            str,
            list[
                ParsedBootImage
            ],
        ] = {}

        order: list[
            str
        ] = []

        for image in parsing.boot_images:
            partition = image.partition

            canonical_name = (
                partition.base_name
            )

            if canonical_name not in groups:
                groups[
                    canonical_name
                ] = []

                order.append(
                    canonical_name
                )

            groups[
                canonical_name
            ].append(
                image
            )

        expectations = tuple(
            cls._expectation_for_group(
                canonical_name,
                tuple(
                    groups[
                        canonical_name
                    ]
                ),
            )
            for canonical_name
            in order
        )

        manifest = (
            AndroidBootstrapRecoveryPartitionManifest(
                parsing=parsing,
                expectations=expectations,
            )
        )

        represented_partition_ids = {
            id(image.partition)
            for image
            in parsing.boot_images
        }

        grouped_partition_ids = {
            id(image.partition)
            for group
            in groups.values()
            for image
            in group
        }

        if (
            represented_partition_ids
            != grouped_partition_ids
        ):
            raise RuntimeError(
                "recovery manifest projection lost canonical "
                "boot-family partition identity"
            )

        return manifest


def _c_string(
    value: str,
) -> str:
    """
    Render one UTF-8 string as an unambiguous C byte-string literal.
    """

    encoded = value.encode(
        "utf-8",
    )

    pieces = []

    for byte in encoded:
        if byte == 0x22:
            pieces.append(
                r'\"'
            )
        elif byte == 0x5C:
            pieces.append(
                r'\\'
            )
        elif 0x20 <= byte <= 0x7E:
            pieces.append(
                chr(byte)
            )
        else:
            pieces.append(
                f"\\{byte:03o}"
            )

    return (
        '"'
        + "".join(
            pieces
        )
        + '"'
    )


def render_recovery_partition_manifest_c(
    manifest: AndroidBootstrapRecoveryPartitionManifest,
) -> str:
    """
    Render the compact runtime table embedded into treeforge-recovery.

    Host-only path provenance remains outside the executable. Runtime receives
    only the canonical facts needed for identity comparison and read-only
    content verification.
    """

    if not isinstance(
        manifest,
        AndroidBootstrapRecoveryPartitionManifest,
    ):
        raise TypeError(
            "manifest must be an "
            "AndroidBootstrapRecoveryPartitionManifest"
        )

    rows = []

    for expectation in manifest.expectations:
        canonical_hashes = {
            image.partition.artifact.content_sha256
            for image
            in manifest.parsing.boot_images
            if (
                image.partition.base_name
                == expectation.canonical_name
                and image.partition.artifact.content_sha256
            )
        }

        if len(canonical_hashes) > 1:
            raise ValueError(
                "canonical recovery partition has conflicting "
                "Extraction SHA-256 evidence: "
                f"{expectation.canonical_name}"
            )

        canonical_sha256 = (
            next(
                iter(
                    canonical_hashes
                )
            )
            if canonical_hashes
            else None
        )

        if canonical_sha256 is not None:
            if (
                len(canonical_sha256) != 64
                or canonical_sha256.lower()
                    != canonical_sha256
                or any(
                    character not in "0123456789abcdef"
                    for character
                    in canonical_sha256
                )
            ):
                raise ValueError(
                    "canonical recovery partition has invalid "
                    "Extraction SHA-256 evidence: "
                    f"{expectation.canonical_name}"
                )

        rows.append(
            "    {"
            + _c_string(
                expectation.canonical_name
            )
            + ", "
            + _c_string(
                expectation.container_kind
            )
            + ", "
            + _c_string(
                canonical_sha256
                or ""
            )
            + ", "
            + str(
                expectation.canonical_image_size_bytes
                or 0
            )
            + "ULL, "
            + (
                "1"
                if (
                    expectation
                    .canonical_image_size_bytes
                    is not None
                )
                else "0"
            )
            + ", "
            + (
                "1"
                if canonical_sha256
                is not None
                else "0"
            )
            + ", "
            + (
                "1"
                if expectation.logical
                else "0"
            )
            + ", "
            + (
                "1"
                if expectation.read_probe_candidate
                else "0"
            )
            + "},"
        )

    if rows:
        table_rows = "\n".join(
            rows
        )
    else:
        table_rows = (
            '    {0, 0, "", 0ULL, 0, 0, 0, 0},'
        )

    return (
        "struct tf_canonical_partition_expectation {\n"
        "    const char *canonical_name;\n"
        "    const char *container_kind;\n"
        "    const char *canonical_content_sha256;\n"
        "    u64 canonical_image_size_bytes;\n"
        "    int image_size_resolved;\n"
        "    int content_sha256_resolved;\n"
        "    int logical;\n"
        "    int read_probe_candidate;\n"
        "};\n"
        "\n"
        "static const struct "
        "tf_canonical_partition_expectation\n"
        "    tf_canonical_partition_expectations[] = {\n"
        + table_rows
        + "\n"
        "};\n"
        "\n"
        "#define TREEFORGE_RECOVERY_CANONICAL_EXPECTATION_COUNT "
        + str(
            manifest.expectation_count
        )
        + "\n"
    )


__all__ = (
    "AndroidBootstrapRecoveryPartitionDisposition",
    "AndroidBootstrapRecoveryPartitionExpectation",
    "AndroidBootstrapRecoveryPartitionManifest",
    "AndroidBootstrapRecoveryPartitionManifestBuilder",
    "render_recovery_partition_manifest_c",
)
