"""
TreeForge-owned Android 15 / r36 Device Tree AVB build-signing semantics.

These are target-build facts distilled from the hardware-proven canonical
Android 15 r36 build. This module is runtime self-contained and MUST NOT
inspect an AOSP checkout.
"""

ANDROID_15_R36_AVB_SIGNING_REFERENCE_TAG = "android-15.0.0_r36"

ANDROID_15_R36_AVB_ROLLBACK_INDEX_EXPRESSION = (
    "$(PLATFORM_SECURITY_PATCH_TIMESTAMP)"
)

ANDROID_15_R36_AVB_SIGNING_ALGORITHMS = (
    ("boot", "SHA256_RSA2048"),
    ("init_boot", "SHA256_RSA2048"),
    ("vbmeta", "SHA256_RSA4096"),
    ("vbmeta_system", "SHA256_RSA2048"),
    ("vbmeta_vendor", "SHA256_RSA2048"),
)

ANDROID_15_R36_AOSP_AVB_KEY_PATHS = (
    ("boot", "external/avb/test/data/testkey_rsa2048.pem"),
    ("init_boot", "external/avb/test/data/testkey_rsa2048.pem"),
    ("vbmeta", "external/avb/test/data/testkey_rsa4096.pem"),
    ("vbmeta_system", "external/avb/test/data/testkey_rsa2048.pem"),
    ("vbmeta_vendor", "external/avb/test/data/testkey_rsa2048.pem"),
)


# ---------------------------------------------------------------------
# Tangorpro Android 15 / r36 AVB acceptance contract.
#
# These are hardware-proven/reconstruction-proven relationships.
# Signing algorithms remain defined above. This section defines the
# expected output graph that Build must verify after AOSP finishes.
# ---------------------------------------------------------------------

ANDROID_15_R36_TANGORPRO_AVB_CHAIN_RELATIONSHIPS = (
    ("vbmeta", "boot", 2),
    ("vbmeta", "init_boot", 4),
    ("vbmeta", "vbmeta_system", 1),
    ("vbmeta", "vbmeta_vendor", 3),
)


ANDROID_15_R36_TANGORPRO_AVB_DESCRIPTOR_TYPES = (
    (
        "boot",
        (
            ("boot", "hash"),
        ),
    ),
    (
        "init_boot",
        (
            ("init_boot", "hash"),
        ),
    ),
    (
        "vbmeta",
        (
            ("abl", "hash"),
            ("bl1", "hash"),
            ("bl2", "hash"),
            ("bl31", "hash"),
            ("dtbo", "hash"),
            ("gsa", "hash"),
            ("ldfw", "hash"),
            ("pbl", "hash"),
            ("tzsw", "hash"),
            ("vendor_boot", "hash"),
            ("vendor_kernel_boot", "hash"),
            ("vendor_dlkm", "hashtree"),
        ),
    ),
    (
        "vbmeta_system",
        (
            ("pvmfw", "hash"),
            ("product", "hashtree"),
            ("system", "hashtree"),
            ("system_dlkm", "hashtree"),
            ("system_ext", "hashtree"),
        ),
    ),
    (
        "vbmeta_vendor",
        (
            ("vendor", "hashtree"),
        ),
    ),
)
