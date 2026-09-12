from __future__ import annotations

from enum import Enum


class ProviderSourceType(str, Enum):
    """Canonical source categories for TreeForge providers."""

    FACTORY_IMAGE = "factory-image"
    ADB = "adb"
    OTA = "ota"
    DEVICE_TREE = "device-tree"
    BOOT_IMAGE = "boot-image"
    FILESYSTEM = "filesystem"
    CUSTOM = "custom"