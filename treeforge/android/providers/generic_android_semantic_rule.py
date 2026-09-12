from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.providers.artifact import (
    ProviderArtifactClassification,
)
from treeforge.android.providers.artifact_semantic_rule import (
    ProviderArtifactSemanticRule,
)


@dataclass(
    frozen=True,
    slots=True,
)
class GenericAndroidArtifactSemanticRule(
    ProviderArtifactSemanticRule,
):
    """
    Generic Android artifact semantic knowledge.

    This rule must not contain:

    - OEM-specific names;
    - SoC/platform-specific names;
    - device-specific names;
    - Android-version-specific policy.

    Those belong to knowledge modules resolved after raw Discovery.
    """

    rule_id: str = (
        "generic-android-artifact-semantics"
    )

    _IMAGE_CLASSIFICATIONS = {
        "boot.img": (
            ProviderArtifactClassification.BOOT
        ),
        "init_boot.img": (
            ProviderArtifactClassification.INIT_BOOT
        ),
        "vendor_boot.img": (
            ProviderArtifactClassification.VENDOR_BOOT
        ),
        "vendor_kernel_boot.img": (
            ProviderArtifactClassification
            .VENDOR_KERNEL_BOOT
        ),
        "recovery.img": (
            ProviderArtifactClassification.RECOVERY
        ),

        "system.img": (
            ProviderArtifactClassification.SYSTEM
        ),
        "system_ext.img": (
            ProviderArtifactClassification.SYSTEM_EXT
        ),
        "system_other.img": (
            ProviderArtifactClassification.SYSTEM_OTHER
        ),
        "product.img": (
            ProviderArtifactClassification.PRODUCT
        ),
        "vendor.img": (
            ProviderArtifactClassification.VENDOR
        ),
        "odm.img": (
            ProviderArtifactClassification.ODM
        ),
        "userdata.img": (
            ProviderArtifactClassification.USERDATA
        ),

        "vendor_dlkm.img": (
            ProviderArtifactClassification.VENDOR_DLKM
        ),
        "system_dlkm.img": (
            ProviderArtifactClassification.SYSTEM_DLKM
        ),
        "odm_dlkm.img": (
            ProviderArtifactClassification.ODM_DLKM
        ),

        "super.img": (
            ProviderArtifactClassification.SUPER
        ),
        "super_empty.img": (
            ProviderArtifactClassification.SUPER_EMPTY
        ),

        "dtbo.img": (
            ProviderArtifactClassification.DTBO
        ),

        "vbmeta.img": (
            ProviderArtifactClassification.VBMETA
        ),
        "vbmeta_system.img": (
            ProviderArtifactClassification.VBMETA_SYSTEM
        ),
        "vbmeta_vendor.img": (
            ProviderArtifactClassification.VBMETA_VENDOR
        ),

        "pvmfw.img": (
            ProviderArtifactClassification.PVMFW
        ),
    }

    def classify(
        self,
        source_name: str,
    ) -> ProviderArtifactClassification:
        lower_name = self._normalized_name(
            source_name
        )

        classification = (
            self._IMAGE_CLASSIFICATIONS.get(
                lower_name
            )
        )

        if classification is not None:
            return classification

        if (
            lower_name
            == "android-info.txt"
        ):
            return (
                ProviderArtifactClassification
                .ANDROID_INFO
            )

        if (
            lower_name
            == "fastboot-info.txt"
        ):
            return (
                ProviderArtifactClassification
                .FASTBOOT_INFO
            )

        return (
            ProviderArtifactClassification.UNKNOWN
        )

    @staticmethod
    def _normalized_name(
        source_name: str,
    ) -> str:
        if not isinstance(
            source_name,
            str,
        ):
            raise TypeError(
                "source_name must be a string"
            )

        if not source_name.strip():
            raise ValueError(
                "source_name must not be empty"
            )

        return (
            PurePosixPath(
                source_name
            )
            .name
            .lower()
        )