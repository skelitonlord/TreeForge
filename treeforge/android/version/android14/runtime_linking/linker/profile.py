"""
Android 14 Linker semantic profile composition.

Only release differences proven against AOSP linkerconfig history belong here.
"""

from treeforge.android.version.android14.runtime_linking.linker.topology import (
    ANDROID_14_BASE_ADDITIONAL_DIRECTORY_ROUTES,
    ANDROID_14_BASE_ADDITIONAL_SECTIONS,
)
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
from treeforge.android.version.model import (
    AndroidLinkerSemanticProfile,
)


ANDROID_14_LINKER_SEMANTIC_PROFILE = AndroidLinkerSemanticProfile(
    # Android 14 BaseContext::SetSystemConfig() replaces prior SYSTEM values.
    system_context_accumulates_configs=False,

    # Android 14 still generates the fuzz BASE section.
    base_additional_sections=(
        ANDROID_14_BASE_ADDITIONAL_SECTIONS
    ),
    base_additional_directory_routes=(
        ANDROID_14_BASE_ADDITIONAL_DIRECTORY_ROUTES
    ),

    # Android 15 added the non-VNDK vendor/product APEX LLNDK sanitizer
    # provider. Android 14 does not emit it.
    apex_non_vndk_vendor_product_sanitizer_variable=None,

    # Namespace semantics below are source-identical between the compared
    # Android 14 and Android 15 linkerconfig revisions.
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

    # Android 14 has only the shared vndk_in_system -> vndk link.
    # Android 15 adds the separate -> default allow-all link.
    vndk_in_system_link_rules=(
        ANDROID_14_15_VNDK_IN_SYSTEM_BASE_LINK_RULES
    ),
    isolated_link_rules=(
        ANDROID_14_15_ISOLATED_LINK_RULES
    ),
    apex_public_jni_visibility_sections=(
        ANDROID_14_15_APEX_PUBLIC_JNI_VISIBILITY_SECTIONS
    ),
)
