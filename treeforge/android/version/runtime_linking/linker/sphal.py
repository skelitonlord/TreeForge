"""
Android 14/15 shared Linker SPHAL namespace semantics.

Reference implementation:
AOSP system/linkerconfig/contents/namespace/sphal.cc

Scope:
- Android 14/15 shared BASE-configuration SPHAL namespace link behavior
- APEX-binary configuration behavior is intentionally handled separately
- no device-specific facts
- no factory-image-derived values
- no Reconstruction behavior
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticCondition,
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_SPHAL_LINK_RULES = (
    # Legacy/non-VNDK case.
    #
    # BuildSphalNamespace() uses ctx.GetSystemNamespaceName().
    # System and unrestricted sections use their "default" namespace;
    # all other BASE sections use the dedicated "system" namespace.
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="default",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                library_name="libft2.so",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_NOT_DEFINED,
        ),
        section_names=(
            "system",
            "unrestricted",
        ),
    ),

    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="system",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                library_name="libft2.so",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_NOT_DEFINED,
        ),
        excluded_section_names=(
            "system",
            "unrestricted",
        ),
    ),

    # BASE linker configuration only:
    # system section SPHAL links to RS first.
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="rs",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                library_name="libRS_internal.so",
            ),
        ),
        section_names=(
            "system",
        ),
    ),

    # BASE linker configuration only:
    # with vendor VNDK enabled, SPHAL gets VNDK-SP access.
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_SAMEPROCESS_LIBRARIES_VENDOR",
                fallback="",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_DEFINED,
        ),
        section_names=(
            "system",
        ),
    ),
)
