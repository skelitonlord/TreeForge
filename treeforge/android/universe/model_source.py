from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.parsing.filesystem.source_inventory import (
    AndroidModelSource,
    AndroidModelSourceInventory,
    AndroidModelSourceKind,
)


class AndroidUniverseModelSourceDisposition(
    StrEnum,
):
    """
    Universe ownership status for one exact canonical AndroidModelSource.

    SEMANTIC_OWNER_PRESENT means Universe currently has a dedicated semantic
    owner for this source kind. It does not claim that the corresponding
    family has already passed the current completeness audit.

    UNRESOLVED means Parsing established this as a semantic model source but
    Universe does not yet have the required semantic owner.
    """

    SEMANTIC_OWNER_PRESENT = (
        "semantic_owner_present"
    )

    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseModelSourceRequirement:
    """
    Canonical Universe accounting for one exact Parsing model source.

    Intrinsic source identity, Android-visible path, host path, filesystem
    identity, partition context, and Extraction provenance remain owned by
    the exact upstream AndroidModelSource object.

    Universe adds only semantic ownership accounting.
    """

    source: AndroidModelSource
    parsing_owner: str
    universe_owner: str | None
    disposition: AndroidUniverseModelSourceDisposition

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

        if not isinstance(
            self.parsing_owner,
            str,
        ):
            raise TypeError(
                "parsing_owner must be a string"
            )

        if not self.parsing_owner:
            raise ValueError(
                "parsing_owner must not be empty"
            )

        if (
            self.universe_owner is not None
            and not isinstance(
                self.universe_owner,
                str,
            )
        ):
            raise TypeError(
                "universe_owner must be a string or None"
            )

        if not isinstance(
            self.disposition,
            AndroidUniverseModelSourceDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidUniverseModelSourceDisposition"
            )

        if (
            self.disposition
            is AndroidUniverseModelSourceDisposition
            .SEMANTIC_OWNER_PRESENT
        ):
            if not self.universe_owner:
                raise ValueError(
                    "SEMANTIC_OWNER_PRESENT source must name "
                    "its Universe semantic owner"
                )

        elif self.universe_owner is not None:
            raise ValueError(
                "UNRESOLVED source must not claim a "
                "Universe semantic owner"
            )

    @property
    def identity_key(
        self,
    ):
        return self.source.identity_key


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseModelSourceRequirementInventory:
    """
    Complete Universe ledger for Parsing AndroidModelSourceInventory.

    Every canonical AndroidModelSource must appear exactly once and by exact
    object identity.
    """

    source_inventory: AndroidModelSourceInventory

    requirements: tuple[
        AndroidUniverseModelSourceRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an "
                "AndroidModelSourceInventory"
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
                AndroidUniverseModelSourceRequirement,
            )
            for requirement in self.requirements
        ):
            raise TypeError(
                "requirements must contain only "
                "AndroidUniverseModelSourceRequirement objects"
            )

        expected_by_identity = {
            id(source): source
            for source
            in self.source_inventory.sources
        }

        actual_ids = tuple(
            id(
                requirement.source
            )
            for requirement
            in self.requirements
        )

        if len(
            actual_ids
        ) != len(
            set(
                actual_ids
            )
        ):
            raise ValueError(
                "Universe model-source ledger contains "
                "duplicate canonical source identities"
            )

        if (
            set(
                actual_ids
            )
            != set(
                expected_by_identity
            )
        ):
            missing = (
                set(
                    expected_by_identity
                )
                - set(
                    actual_ids
                )
            )

            extra = (
                set(
                    actual_ids
                )
                - set(
                    expected_by_identity
                )
            )

            raise ValueError(
                "Universe model-source ledger must conserve "
                "every canonical AndroidModelSource exactly once; "
                f"missing={len(missing)}, extra={len(extra)}"
            )

        for requirement in self.requirements:
            canonical = (
                expected_by_identity[
                    id(
                        requirement.source
                    )
                ]
            )

            if requirement.source is not canonical:
                raise ValueError(
                    "Universe model-source ledger must retain "
                    "exact canonical AndroidModelSource identity"
                )

        canonical_order = tuple(
            sorted(
                self.requirements,
                key=lambda requirement: (
                    requirement.source.identity_key
                ),
            )
        )

        if self.requirements != canonical_order:
            raise ValueError(
                "Universe model-source requirements must use "
                "canonical source identity order"
            )

    def partition_root_candidates(
        self,
        partition_name: str,
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        """
        Return Android-visible root candidates canonically evidenced for one
        partition.

        A candidate exists only when a conserved model source belongs to the
        requested partition and its canonical Android-visible path begins
        beneath that same partition root.

        This deliberately does not manufacture aliases such as
        /system/product from partition identity alone.
        """

        if not isinstance(
            partition_name,
            str,
        ):
            raise TypeError(
                "partition_name must be a string"
            )

        if not partition_name:
            raise ValueError(
                "partition_name must not be empty"
            )

        values = set()

        for requirement in self.requirements:
            source = requirement.source

            if (
                source.partition_name
                != partition_name
            ):
                continue

            path = source.android_path

            if path is None:
                continue

            parts = path.parts

            if len(
                parts
            ) < 2:
                continue

            if (
                parts[
                    1
                ]
                != partition_name
            ):
                continue

            values.add(
                PurePosixPath(
                    "/",
                    partition_name,
                )
            )

        return tuple(
            sorted(
                values,
                key=lambda value: (
                    value.as_posix()
                ),
            )
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self.requirements
        )

    @property
    def unresolved(
        self,
    ) -> tuple[
        AndroidUniverseModelSourceRequirement,
        ...,
    ]:
        return tuple(
            requirement
            for requirement
            in self.requirements
            if (
                requirement.disposition
                is AndroidUniverseModelSourceDisposition
                .UNRESOLVED
            )
        )


class AndroidUniverseModelSourceRequirementBuilder:
    """
    Promote every canonical Parsing model source into explicit Universe
    semantic-ownership accounting.

    The policy deliberately covers AndroidModelSourceKind exhaustively.
    Adding a new Parsing source kind therefore requires an explicit Universe
    ownership decision before Universe can complete.
    """

    _POLICY = {
        AndroidModelSourceKind.INIT: (
            "filesystem.init",
            "init",
        ),
        AndroidModelSourceKind.FSTAB: (
            "filesystem.fstab",
            "fstab",
        ),
        AndroidModelSourceKind.UEVENTD: (
            "filesystem.ueventd",
            "ueventd",
        ),
        AndroidModelSourceKind.VINTF: (
            "filesystem.vintf",
            "vintf",
        ),
        AndroidModelSourceKind.PROPERTY: (
            "filesystem.property",
            "property",
        ),
        AndroidModelSourceKind.SELINUX: (
            "filesystem.selinux",
            "selinux",
        ),
        AndroidModelSourceKind.LINKER_CONFIGURATION: (
            "linker",
            "linker",
        ),
        AndroidModelSourceKind.NATIVE_LIBRARY_CONFIGURATION: (
            "native_library",
            "native_library",
        ),
        AndroidModelSourceKind.KERNEL_MODULE_CONFIGURATION: (
            "kernel_module_configuration",
            "kernel_module",
        ),
        AndroidModelSourceKind.ART_RUNTIME: (
            "art_runtime",
            "art_runtime",
        ),
        AndroidModelSourceKind.DEX: (
            "dex",
            "dex",
        ),
        AndroidModelSourceKind.CLASSPATH_CONFIGURATION: (
            "classpath",
            "classpath",
        ),
        AndroidModelSourceKind.ACONFIG_CONFIGURATION: (
            "aconfig",
            "aconfig",
        ),

        AndroidModelSourceKind.INPUT_KEY_LAYOUT: (
            "input",
            "input",
        ),
        AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP: (
            "input",
            "input",
        ),
        AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION: (
            "input",
            "input",
        ),
        AndroidModelSourceKind.FONT: (
            "font",
            "font",
        ),
        AndroidModelSourceKind.JAVA_ARCHIVE: (
            "java_archive",
            "classpath",
        ),
        AndroidModelSourceKind.SHELL_SCRIPT: (
            "shell_script",
            "shell_script",
        ),
        AndroidModelSourceKind.CERTIFICATE: (
            "certificate",
            "certificate",
        ),
        AndroidModelSourceKind.OTA_CERTIFICATE_ARCHIVE: (
            "ota_certificate_archive",
            "certificate",
        ),

        AndroidModelSourceKind.AVB_PUBLIC_KEY: (
            "structured_configuration",
            "structured_configuration",
        ),
        AndroidModelSourceKind.CGROUP_CONFIGURATION: (
            "structured_configuration",
            "structured_configuration",
        ),
        AndroidModelSourceKind.MKE2FS_CONFIGURATION: (
            "structured_configuration",
            "structured_configuration",
        ),
        AndroidModelSourceKind.RECOVERY_WIPE_CONFIGURATION: (
            "structured_configuration",
            "structured_configuration",
        ),
        AndroidModelSourceKind.BLUEPRINT: (
            "structured_configuration",
            "structured_configuration",
        ),
        AndroidModelSourceKind.SENSOR_HAL_CONFIGURATION: (
            "structured_configuration",
            "structured_configuration",
        ),
        AndroidModelSourceKind.SENSOR_REGISTRY_CONFIGURATION: (
            "structured_configuration",
            "structured_configuration",
        ),
    }

    def build(
        self,
        source_inventory: AndroidModelSourceInventory,
    ) -> AndroidUniverseModelSourceRequirementInventory:
        if not isinstance(
            source_inventory,
            AndroidModelSourceInventory,
        ):
            raise TypeError(
                "source_inventory must be an "
                "AndroidModelSourceInventory"
            )

        policy_kinds = set(
            self._POLICY
        )

        enum_kinds = set(
            AndroidModelSourceKind
        )

        if policy_kinds != enum_kinds:
            missing = tuple(
                sorted(
                    kind.value
                    for kind
                    in (
                        enum_kinds
                        - policy_kinds
                    )
                )
            )

            extra = tuple(
                sorted(
                    kind.value
                    for kind
                    in (
                        policy_kinds
                        - enum_kinds
                    )
                )
            )

            raise ValueError(
                "Universe model-source ownership policy "
                "must exactly cover AndroidModelSourceKind; "
                f"missing={missing!r}, extra={extra!r}"
            )

        requirements = []

        for source in source_inventory.sources:
            (
                parsing_owner,
                universe_owner,
            ) = self._POLICY[
                source.kind
            ]

            disposition = (
                AndroidUniverseModelSourceDisposition
                .SEMANTIC_OWNER_PRESENT
                if universe_owner is not None
                else
                AndroidUniverseModelSourceDisposition
                .UNRESOLVED
            )

            requirements.append(
                AndroidUniverseModelSourceRequirement(
                    source=source,
                    parsing_owner=parsing_owner,
                    universe_owner=universe_owner,
                    disposition=disposition,
                )
            )

        requirements.sort(
            key=lambda requirement: (
                requirement.source.identity_key
            )
        )

        return (
            AndroidUniverseModelSourceRequirementInventory(
                source_inventory=source_inventory,
                requirements=tuple(
                    requirements
                ),
            )
        )
