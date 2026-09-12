"""
Android 15 / r36 vendor-ramdisk package-provider semantics.

These mappings translate canonical runtime payload identities observed in
factory vendor_boot into the Android platform modules that reconstruct those
payloads.

They are Android-version build semantics, not device Knowledge.

Runtime Device Tree generation must not inspect an AOSP checkout.
"""

ANDROID_15_R36_VENDOR_RAMDISK_PACKAGE_PROVIDERS = (
    (
        "/first_stage_ramdisk/system/bin/linker64",
        "linker.vendor_ramdisk",
    ),
    (
        "/first_stage_ramdisk/system/bin/resize2fs",
        "resize2fs.vendor_ramdisk",
    ),
    (
        "/first_stage_ramdisk/system/bin/tune2fs",
        "tune2fs.vendor_ramdisk",
    ),
)
