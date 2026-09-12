"""
Android 14/15 shared Linker RenderScript namespace semantics.

Reference implementations:
AOSP system/linkerconfig/contents/namespace/rs.cc
AOSP system/linkerconfig/modules/context.cc

Scope:
- Android 14/15 shared BASE-configuration RS namespace link behavior
- section-dependent system namespace identity
- no device-specific facts
- no factory-image-derived values
- no Reconstruction behavior
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticCondition,
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_RS_LINK_RULES = (
    # system/unrestricted Context::GetSystemNamespaceName() == "default"
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="default",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="PRIVATE_LLNDK_LIBRARIES_VENDOR",
                fallback="",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_DEFINED,
        ),
        section_names=(
            "system",
            "unrestricted",
        ),
    ),
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

    # Other BASE sections use the dedicated "system" namespace.
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="system",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="PRIVATE_LLNDK_LIBRARIES_VENDOR",
                fallback="",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VENDOR_VNDK_DEFINED,
        ),
        excluded_section_names=(
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
)
