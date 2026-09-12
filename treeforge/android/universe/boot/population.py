from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractedArtifact,
)
from treeforge.android.parsing.boot.vendor_ramdisk_table import (
    ParsedVendorRamdiskTable,
)
from treeforge.android.parsing.dtb import (
    ParsedFdt,
)
from treeforge.android.parsing.ramdisk import (
    ParsedAndroidRamdisk,
)
from treeforge.android.parsing.result import (
    ParsedBootSignature,
)
from treeforge.android.universe.avb.boot_signature import (
    AndroidUniverseBootSignatureAvbRequirement,
)
from treeforge.android.universe.boot.requirement import (
    AndroidUniverseBootRequirement,
)


def _require_exact_component(
    *,
    requirement: AndroidUniverseBootRequirement,
    artifact: ExtractedArtifact,
    semantic_name: str,
) -> None:
    expected = requirement.component_artifact(
        semantic_name
    )

    if expected is not artifact:
        raise ValueError(
            "boot-family reconciliation must preserve exact "
            f"{semantic_name!r} component identity"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootDtbAssociation:
    source: ParsedFdt
    boot_requirement: AndroidUniverseBootRequirement
    component: ExtractedArtifact

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedFdt,
        ):
            raise TypeError(
                "source must be a ParsedFdt"
            )

        if not isinstance(
            self.boot_requirement,
            AndroidUniverseBootRequirement,
        ):
            raise TypeError(
                "boot_requirement must be an "
                "AndroidUniverseBootRequirement"
            )

        if not isinstance(
            self.component,
            ExtractedArtifact,
        ):
            raise TypeError(
                "component must be an ExtractedArtifact"
            )

        if self.source.artifact.parent is not self.component:
            raise ValueError(
                "boot DTB must preserve exact dtb-component parent identity"
            )

        if (
            self.component.parent
            is not self.boot_requirement.partition.artifact
        ):
            raise ValueError(
                "boot DTB component must preserve exact boot-image identity"
            )

        _require_exact_component(
            requirement=self.boot_requirement,
            artifact=self.component,
            semantic_name="dtb",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVendorRamdiskTableAssociation:
    source: ParsedVendorRamdiskTable
    boot_requirement: AndroidUniverseBootRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedVendorRamdiskTable,
        ):
            raise TypeError(
                "source must be a ParsedVendorRamdiskTable"
            )

        if not isinstance(
            self.boot_requirement,
            AndroidUniverseBootRequirement,
        ):
            raise TypeError(
                "boot_requirement must be an "
                "AndroidUniverseBootRequirement"
            )

        if (
            self.source.boot_image_artifact
            is not self.boot_requirement.partition.artifact
        ):
            raise ValueError(
                "vendor ramdisk-table association must preserve "
                "exact boot-image identity"
            )

        _require_exact_component(
            requirement=self.boot_requirement,
            artifact=self.source.artifact,
            semantic_name="vendor_ramdisk_table",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseRamdiskAssociation:
    source: ParsedAndroidRamdisk
    boot_requirement: AndroidUniverseBootRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidRamdisk,
        ):
            raise TypeError(
                "source must be a ParsedAndroidRamdisk"
            )

        if not isinstance(
            self.boot_requirement,
            AndroidUniverseBootRequirement,
        ):
            raise TypeError(
                "boot_requirement must be an "
                "AndroidUniverseBootRequirement"
            )

        if (
            self.source.boot_image_artifact
            is not self.boot_requirement.partition.artifact
        ):
            raise ValueError(
                "ramdisk association must preserve exact "
                "boot-image identity"
            )

        if (
            self.source.ramdisk_component
            not in self.boot_requirement.component_artifacts
        ):
            raise ValueError(
                "ramdisk association must preserve exact canonical "
                "boot component identity"
            )

        if not any(
            candidate is self.source.ramdisk_component
            for candidate
            in self.boot_requirement.component_artifacts
        ):
            raise ValueError(
                "ramdisk component is absent from the exact "
                "Boot requirement"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootSignatureAssociation:
    source: ParsedBootSignature
    boot_requirement: AndroidUniverseBootRequirement
    avb_requirement: AndroidUniverseBootSignatureAvbRequirement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedBootSignature,
        ):
            raise TypeError(
                "source must be a ParsedBootSignature"
            )

        if not isinstance(
            self.boot_requirement,
            AndroidUniverseBootRequirement,
        ):
            raise TypeError(
                "boot_requirement must be an "
                "AndroidUniverseBootRequirement"
            )

        if not isinstance(
            self.avb_requirement,
            AndroidUniverseBootSignatureAvbRequirement,
        ):
            raise TypeError(
                "avb_requirement must be an "
                "AndroidUniverseBootSignatureAvbRequirement"
            )

        if self.avb_requirement.source is not self.source:
            raise ValueError(
                "boot-signature association must preserve exact "
                "AVB semantic requirement source identity"
            )

        if (
            self.source.boot_image_artifact
            is not self.boot_requirement.partition.artifact
        ):
            raise ValueError(
                "boot-signature association must preserve exact "
                "boot-image identity"
            )

        _require_exact_component(
            requirement=self.boot_requirement,
            artifact=self.source.artifact,
            semantic_name="boot_signature",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootPopulationReconciliation:
    boot_dtbs: tuple[
        ParsedFdt,
        ...,
    ]

    vendor_ramdisk_tables: tuple[
        ParsedVendorRamdiskTable,
        ...,
    ]

    ramdisks: tuple[
        ParsedAndroidRamdisk,
        ...,
    ]

    boot_signatures: tuple[
        ParsedBootSignature,
        ...,
    ]

    dtb_associations: tuple[
        AndroidUniverseBootDtbAssociation,
        ...,
    ]

    vendor_ramdisk_table_associations: tuple[
        AndroidUniverseVendorRamdiskTableAssociation,
        ...,
    ]

    ramdisk_associations: tuple[
        AndroidUniverseRamdiskAssociation,
        ...,
    ]

    boot_signature_associations: tuple[
        AndroidUniverseBootSignatureAssociation,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        for (
            source,
            associations,
            source_attribute,
        ) in (
            (
                self.boot_dtbs,
                self.dtb_associations,
                "source",
            ),
            (
                self.vendor_ramdisk_tables,
                self.vendor_ramdisk_table_associations,
                "source",
            ),
            (
                self.ramdisks,
                self.ramdisk_associations,
                "source",
            ),
            (
                self.boot_signatures,
                self.boot_signature_associations,
                "source",
            ),
        ):
            if len(
                source
            ) != len(
                associations
            ):
                raise ValueError(
                    "boot population reconciliation must conserve "
                    "every Parsing source"
                )

            if not all(
                getattr(
                    association,
                    source_attribute,
                )
                is parsed
                for association, parsed
                in zip(
                    associations,
                    source,
                    strict=True,
                )
            ):
                raise ValueError(
                    "boot population reconciliation must preserve "
                    "exact Parsing identity and order"
                )


class AndroidUniverseBootPopulationReconciler:
    def reconcile(
        self,
        *,
        boot_requirements: tuple[
            AndroidUniverseBootRequirement,
            ...,
        ],
        boot_dtbs: tuple[
            ParsedFdt,
            ...,
        ],
        vendor_ramdisk_tables: tuple[
            ParsedVendorRamdiskTable,
            ...,
        ],
        ramdisks: tuple[
            ParsedAndroidRamdisk,
            ...,
        ],
        boot_signatures: tuple[
            ParsedBootSignature,
            ...,
        ],
        boot_signature_avb_requirements: tuple[
            AndroidUniverseBootSignatureAvbRequirement,
            ...,
        ],
    ) -> AndroidUniverseBootPopulationReconciliation:
        by_boot_artifact_id = {
            id(
                requirement.partition.artifact
            ): requirement
            for requirement
            in boot_requirements
        }

        if (
            len(
                by_boot_artifact_id
            )
            != len(
                boot_requirements
            )
        ):
            raise ValueError(
                "Boot requirements contain duplicate boot-image "
                "artifact identity"
            )

        avb_by_source_id = {
            id(
                requirement.source
            ): requirement
            for requirement
            in boot_signature_avb_requirements
        }

        if (
            len(
                avb_by_source_id
            )
            != len(
                boot_signature_avb_requirements
            )
        ):
            raise ValueError(
                "boot-signature AVB requirements contain duplicate "
                "Parsing source identity"
            )

        dtb_associations = []

        for source in boot_dtbs:
            component = source.artifact.parent

            if component is None:
                raise ValueError(
                    "boot DTB has no canonical dtb-component parent"
                )

            boot_image_artifact = (
                component.parent
            )

            if boot_image_artifact is None:
                raise ValueError(
                    "boot DTB component has no canonical "
                    "boot-image parent"
                )

            requirement = (
                by_boot_artifact_id.get(
                    id(
                        boot_image_artifact
                    )
                )
            )

            if requirement is None:
                raise ValueError(
                    "boot DTB has no exact Universe Boot requirement"
                )

            dtb_associations.append(
                AndroidUniverseBootDtbAssociation(
                    source=source,
                    boot_requirement=requirement,
                    component=component,
                )
            )

        vendor_ramdisk_table_associations = []

        for source in vendor_ramdisk_tables:
            requirement = (
                by_boot_artifact_id.get(
                    id(
                        source.boot_image_artifact
                    )
                )
            )

            if requirement is None:
                raise ValueError(
                    "vendor ramdisk table has no exact "
                    "Universe Boot requirement"
                )

            vendor_ramdisk_table_associations.append(
                AndroidUniverseVendorRamdiskTableAssociation(
                    source=source,
                    boot_requirement=requirement,
                )
            )

        ramdisk_associations = []

        for source in ramdisks:
            requirement = (
                by_boot_artifact_id.get(
                    id(
                        source.boot_image_artifact
                    )
                )
            )

            if requirement is None:
                raise ValueError(
                    "ramdisk has no exact Universe Boot requirement"
                )

            ramdisk_associations.append(
                AndroidUniverseRamdiskAssociation(
                    source=source,
                    boot_requirement=requirement,
                )
            )

        boot_signature_associations = []

        for source in boot_signatures:
            requirement = (
                by_boot_artifact_id.get(
                    id(
                        source.boot_image_artifact
                    )
                )
            )

            if requirement is None:
                raise ValueError(
                    "boot signature has no exact "
                    "Universe Boot requirement"
                )

            avb_requirement = (
                avb_by_source_id.get(
                    id(
                        source
                    )
                )
            )

            if avb_requirement is None:
                raise ValueError(
                    "boot signature has no exact "
                    "AVB semantic requirement"
                )

            boot_signature_associations.append(
                AndroidUniverseBootSignatureAssociation(
                    source=source,
                    boot_requirement=requirement,
                    avb_requirement=avb_requirement,
                )
            )

        return AndroidUniverseBootPopulationReconciliation(
            boot_dtbs=boot_dtbs,
            vendor_ramdisk_tables=(
                vendor_ramdisk_tables
            ),
            ramdisks=ramdisks,
            boot_signatures=boot_signatures,
            dtb_associations=tuple(
                dtb_associations
            ),
            vendor_ramdisk_table_associations=tuple(
                vendor_ramdisk_table_associations
            ),
            ramdisk_associations=tuple(
                ramdisk_associations
            ),
            boot_signature_associations=tuple(
                boot_signature_associations
            ),
        )
