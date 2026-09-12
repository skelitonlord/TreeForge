"""
Android 14/15 shared Linker VNDK namespace semantics.

Reference implementation:
AOSP system/linkerconfig/contents/namespace/vndk.cc

Scope:
- Android 14/15 shared BASE-configuration VNDK namespace link behavior
- APEX-binary configuration behavior is intentionally handled separately
- search/permitted paths and canonical VNDK runtime values remain generic
- no device-specific facts
- no factory-image-derived values
- no Reconstruction behavior
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticCondition,
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_VNDK_LINK_RULES = (
    # BuildVndkNamespace:
    # non-system/unrestricted BASE sections avoid duplicate loading by
    # linking to the section default namespace instead of adding its lib path.
    #
    # In CreateBaseConfiguration those VNDK namespaces occur in vendor/product.
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="default",
        allow_all_shared_libs=True,
        section_names=(
            "vendor",
            "product",
        ),
    ),

    # Product/vendor sections may reach core-variant VNDK libraries through
    # the dedicated vndk_in_system namespace.
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk_in_system",
        shared_libraries=(
            AndroidLinkerSemanticLibraryExpression(
                variable="VNDK_USING_CORE_VARIANT_LIBRARIES",
            ),
        ),
        conditions=(
            AndroidLinkerSemanticCondition
            .VNDK_IN_SYSTEM_NAMESPACE,
        ),
        section_names=(
            "vendor",
            "product",
        ),
    ),
)
