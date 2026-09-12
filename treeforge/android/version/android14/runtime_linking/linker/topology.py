"""
Android 14 BASE linkerconfig topology semantics.

Reference implementation:
AOSP system/linkerconfig/contents/configuration/baseconfig.cc
AOSP system/linkerconfig/contents/section/fuzz.cc
AOSP system/linkerconfig/contents/namespace/fuzzdefault.cc
"""

from treeforge.android.version.model import (
    AndroidLinkerSemanticAdditionalSection,
)


ANDROID_14_BASE_ADDITIONAL_SECTIONS = (
    AndroidLinkerSemanticAdditionalSection(
        section_name="fuzz",
        namespace_name="default",
        namespace_isolated=True,
        namespace_visible=False,
        namespace_search_paths=(
            "/data/fuzz/arm/lib",
            "/data/fuzz/arm64/lib",
            "/data/fuzz/x86/lib",
            "/data/fuzz/x86_64/lib",
            "/data/fuzz/riscv64/lib",
        ),
    ),
)


ANDROID_14_BASE_ADDITIONAL_DIRECTORY_ROUTES = (
    (
        "/data/fuzz",
        "fuzz",
    ),
)
