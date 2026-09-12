"""
Android 15 Linker semantic profile composition.

Release-specific Linker behavior is split by upstream linkerconfig
responsibility and composed here.
"""

from treeforge.android.version.runtime_linking.linker.apex import (
    ANDROID_14_15_APEX_PUBLIC_JNI_VISIBILITY_SECTIONS,
)
from treeforge.android.version.runtime_linking.linker.isolated import (
    ANDROID_14_15_ISOLATED_LINK_RULES,
)
from treeforge.android.version.runtime_linking.linker.product import (
    ANDROID_14_15_PRODUCT_LINK_RULES,
)
from treeforge.android.version.runtime_linking.linker.rs import (
    ANDROID_14_15_RS_LINK_RULES,
)
from treeforge.android.version.runtime_linking.linker.sphal import (
    ANDROID_14_15_SPHAL_LINK_RULES,
)
from treeforge.android.version.runtime_linking.linker.vendor import (
    ANDROID_14_15_VENDOR_DEFAULT_LINK_RULES,
)
from treeforge.android.version.runtime_linking.linker.vndk import (
    ANDROID_14_15_VNDK_LINK_RULES,
)
from treeforge.android.version.runtime_linking.linker.vndk_in_system import (
    ANDROID_14_15_VNDK_IN_SYSTEM_ALLOWED_LIBRARIES,
    ANDROID_14_15_VNDK_IN_SYSTEM_BASE_LINK_RULES,
)
from treeforge.android.version.android15.runtime_linking.linker.vndk_in_system import (
    ANDROID_15_VNDK_IN_SYSTEM_ADDITIONAL_LINK_RULES,
)
from treeforge.android.version.model import (
    AndroidLinkerSemanticProfile,
)


ANDROID_15_LINKER_SEMANTIC_PROFILE = (
    AndroidLinkerSemanticProfile(
        system_context_accumulates_configs=True,
        base_additional_sections=(),
        base_additional_directory_routes=(),
        apex_non_vndk_vendor_product_sanitizer_variable=(
            "SANITIZER_LIBRARIES_LLNDK"
        ),
        vendor_default_link_rules=(
            ANDROID_14_15_VENDOR_DEFAULT_LINK_RULES
        ),
        product_link_rules=(
            ANDROID_14_15_PRODUCT_LINK_RULES
        ),
        sphal_link_rules=(
            ANDROID_14_15_SPHAL_LINK_RULES
        ),
        rs_link_rules=(
            ANDROID_14_15_RS_LINK_RULES
        ),
        vndk_link_rules=(
            ANDROID_14_15_VNDK_LINK_RULES
        ),
        vndk_in_system_allowed_libraries=(
            ANDROID_14_15_VNDK_IN_SYSTEM_ALLOWED_LIBRARIES
        ),
        vndk_in_system_link_rules=(
            ANDROID_14_15_VNDK_IN_SYSTEM_BASE_LINK_RULES
            + ANDROID_15_VNDK_IN_SYSTEM_ADDITIONAL_LINK_RULES
        ),
        isolated_link_rules=(
            ANDROID_14_15_ISOLATED_LINK_RULES
        ),
        apex_public_jni_visibility_sections=(
            ANDROID_14_15_APEX_PUBLIC_JNI_VISIBILITY_SECTIONS
        ),
    )
)
