from __future__ import annotations

from enum import StrEnum


class AndroidPropertyScope(StrEnum):
    """
    Explicit Android namespace scope encoded by a property key.

    Scope describes property semantics. It does not describe the artifact,
    partition, or source from which the property declaration was observed.
    """

    SYSTEM = "system"
    SYSTEM_EXT = "system_ext"
    PRODUCT = "product"
    VENDOR = "vendor"
    ODM = "odm"
    ODM_DLKM = "odm_dlkm"