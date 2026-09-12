"""
Android 14/15 shared Linker product namespace semantics.

Reference implementation:
AOSP system/linkerconfig/contents/namespace/productdefault.cc

Scope:
- Android 14/15 shared product namespace link behavior only
- no device-specific facts
- no factory-image-derived values
- no Reconstruction behavior
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticCondition,
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_PRODUCT_LINK_RULES = (
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="system",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="SANITIZER_DEFAULT_PRODUCT",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .PRODUCT_VNDK_DEFINED,
        ),
    ),
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk_product",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_SAMEPROCESS_LIBRARIES_PRODUCT",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .PRODUCT_VNDK_DEFINED,
        ),
        section_names=(
            "system",
            "unrestricted",
        ),
    ),
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_SAMEPROCESS_LIBRARIES_PRODUCT",
            ),
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_CORE_LIBRARIES_PRODUCT",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .PRODUCT_VNDK_DEFINED,
        ),
        excluded_section_names=(
            "system",
            "unrestricted",
        ),
    ),
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk_in_system",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_USING_CORE_VARIANT_LIBRARIES",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .PRODUCT_VNDK_DEFINED,
            AndroidLinkerSemanticCondition
            .VNDK_IN_SYSTEM_NAMESPACE,
        ),
        excluded_section_names=(
            "system",
            "unrestricted",
        ),
    ),
)
