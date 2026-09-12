"""
Android 14/15 shared Linker isolated-default namespace semantics.

Reference implementation:
AOSP system/linkerconfig/contents/namespace/isolateddefault.cc

Scope:
- Android 14/15 shared BASE-configuration isolated namespace link behavior
- no device-specific facts
- no factory-image-derived values
- no Reconstruction behavior
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticNamespaceLinkRule,
)


ANDROID_14_15_ISOLATED_LINK_RULES = (
    AndroidLinkerSemanticNamespaceLinkRule(
        target_namespace="system",
        allow_all_shared_libs=True,
        section_names=(
            "isolated",
        ),
    ),
)
