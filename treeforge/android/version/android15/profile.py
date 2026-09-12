"""
Android 15 platform-semantic profile composition.

This package contains Android-release implementation semantics only.

It must not contain:
- device-specific facts,
- factory-image-derived evidence,
- canonical Universe observations,
- Reconstruction ownership/materialization decisions.

Stage/family-specific Android 15 semantics are composed here into the
top-level AndroidSemanticVersionProfile.
"""

from treeforge.android.version.android15.runtime_linking.linker.profile import (
    ANDROID_15_LINKER_SEMANTIC_PROFILE,
)
from treeforge.android.version.model import (
    AndroidSemanticVersionProfile,
)


ANDROID_15_SEMANTIC_VERSION_PROFILE = (
    AndroidSemanticVersionProfile(
        android_version="15",
        linker=ANDROID_15_LINKER_SEMANTIC_PROFILE,
    )
)
