from __future__ import annotations

from treeforge.android.host_provider import (
    AndroidHostProvider,
    AndroidHostProviderSource,
)


# Recovery compatibility names.
#
# Host-provider identity/validation is Android-wide. Recovery retains these
# names so existing Recovery planning/realization code does not need to
# change merely because provider ownership moved to the common Android layer.
AndroidRecoveryHostProvider = AndroidHostProvider
AndroidRecoveryHostProviderSource = AndroidHostProviderSource


__all__ = (
    "AndroidRecoveryHostProvider",
    "AndroidRecoveryHostProviderSource",
)
