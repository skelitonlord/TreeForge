"""
Android 15-specific vndk_in_system namespace semantic delta.

Android 15 adds an allow-all link from vndk_in_system to the section default
namespace for vendor/product BASE sections.
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_15_VNDK_IN_SYSTEM_ADDITIONAL_LINK_RULES = (
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="default",
        allow_all_shared_libs=True,
        section_names=(
            "vendor",
            "product",
        ),
    ),
)
