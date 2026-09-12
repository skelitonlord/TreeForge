"""
Android 14/15 shared Linker vendor namespace semantics.

Reference implementation:
AOSP system/linkerconfig/contents/namespace/vendordefault.cc

Scope:
- Android 14/15 shared vendor namespace link behavior only
- no device-specific facts
- no factory-image-derived values
- no Reconstruction behavior
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticCondition,
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_VENDOR_DEFAULT_LINK_RULES = (
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="rs",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                library_name="libRS_internal.so",
            ),
        ),
    ),
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="system",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="SANITIZER_DEFAULT_VENDOR",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_DEFINED,
        ),
    ),
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_SAMEPROCESS_LIBRARIES_VENDOR",
            ),
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_CORE_LIBRARIES_VENDOR",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_DEFINED,
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
            .VENDOR_VNDK_DEFINED,
            AndroidLinkerSemanticCondition
            .VNDK_IN_SYSTEM_NAMESPACE,
        ),
    ),
)
