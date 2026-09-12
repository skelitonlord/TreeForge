"""
Android 14/15 shared vndk_in_system namespace semantics.

The Android 15-only link to the section default namespace remains in the
Android 15 release profile.
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticLibraryExpression,
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_VNDK_IN_SYSTEM_ALLOWED_LIBRARIES = (
    AndroidLinkerSemanticLibraryExpression(
        variable="VNDK_USING_CORE_VARIANT_LIBRARIES",
    ),
)


ANDROID_14_15_VNDK_IN_SYSTEM_BASE_LINK_RULES = (
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="vndk",
        allow_all_shared_libs=True,
        section_names=(
            "vendor",
            "product",
        ),
    ),
)
