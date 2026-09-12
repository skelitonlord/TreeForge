"""
Android 14 platform-semantic profile composition.

This package contains Android-release implementation semantics only.

It must not contain:
- device-specific facts,
- factory-image-derived evidence,
- canonical Universe observations,
- Reconstruction ownership/materialization decisions.
"""

from treeforge.android.version.android14.runtime_linking.linker.profile import (
    ANDROID_14_LINKER_SEMANTIC_PROFILE,
)
from treeforge.android.version.model import (
    AndroidSemanticVersionProfile,
)


ANDROID_14_SEMANTIC_VERSION_PROFILE = (
    AndroidSemanticVersionProfile(
        android_version="14",
        linker=ANDROID_14_LINKER_SEMANTIC_PROFILE,
    )
)
