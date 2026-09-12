from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from treeforge.android.version.android15.device_tree.avb_signing import (
    ANDROID_15_R36_AOSP_AVB_KEY_PATHS,
    ANDROID_15_R36_AVB_ROLLBACK_INDEX_EXPRESSION,
    ANDROID_15_R36_AVB_SIGNING_ALGORITHMS,
    ANDROID_15_R36_AVB_SIGNING_REFERENCE_TAG,
)


_REQUIRED_PARTITIONS = frozenset(
    {
        "boot",
        "init_boot",
        "vbmeta",
        "vbmeta_system",
        "vbmeta_vendor",
    }
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeAvbSigningEntry:
    partition_name: str
    algorithm: str
    key_path: PurePosixPath
    persistent_source: PurePosixPath | None = None


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeAvbSigningProfile:
    profile_id: str
    provider: str
    reference_tag: str
    rollback_index_expression: str
    entries: tuple[AndroidDeviceTreeAvbSigningEntry, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.rollback_index_expression, str)
            or not self.rollback_index_expression
            or self.rollback_index_expression.strip()
            != self.rollback_index_expression
        ):
            raise ValueError(
                "rollback_index_expression must be a normalized "
                "non-empty string"
            )

        if self.provider not in {"treeforge", "aosp"}:
            raise ValueError(
                f"unsupported Device Tree AVB signing provider: {self.provider!r}"
            )

        partitions = {
            item.partition_name
            for item in self.entries
        }

        if partitions != _REQUIRED_PARTITIONS:
            raise ValueError(
                "Device Tree AVB signing profile has an unexpected "
                f"partition population: {sorted(partitions)!r}"
            )

    def entry(self, partition_name: str) -> AndroidDeviceTreeAvbSigningEntry:
        matches = tuple(
            item
            for item in self.entries
            if item.partition_name == partition_name
        )

        if len(matches) != 1:
            raise ValueError(
                "expected exactly one AVB signing entry for "
                f"{partition_name!r}"
            )

        return matches[0]


def select_android_device_tree_avb_signing_profile(
    android_version: str,
    provider: str,
    *,
    device_root: Path | PurePosixPath,
    device_name: str,
) -> AndroidDeviceTreeAvbSigningProfile:
    if not isinstance(android_version, str) or not android_version.strip():
        raise ValueError("android_version must be non-empty")

    normalized_version = android_version.strip()

    if not (
        normalized_version == "15"
        or normalized_version.startswith("15.")
    ):
        raise ValueError(
            "TreeForge has no Device Tree AVB signing profile for "
            f"Android {normalized_version!r}"
        )

    normalized_provider = provider.strip().lower()

    if normalized_provider not in {"treeforge", "aosp"}:
        raise ValueError(
            "--avb-signing must be 'treeforge' or 'aosp'"
        )

    device_root = PurePosixPath(device_root.as_posix())
    algorithms = dict(ANDROID_15_R36_AVB_SIGNING_ALGORITHMS)

    entries = []

    if normalized_provider == "aosp":
        key_paths = dict(ANDROID_15_R36_AOSP_AVB_KEY_PATHS)

        for partition_name in sorted(_REQUIRED_PARTITIONS):
            entries.append(
                AndroidDeviceTreeAvbSigningEntry(
                    partition_name=partition_name,
                    algorithm=algorithms[partition_name],
                    key_path=PurePosixPath(key_paths[partition_name]),
                    persistent_source=None,
                )
            )

        profile_id = (
            f"{ANDROID_15_R36_AVB_SIGNING_REFERENCE_TAG}/"
            "aosp-development-test-keys"
        )

    else:
        persistent_root = (
            PurePosixPath(".treeforge-private")
            / "keys"
            / "avb"
            / ANDROID_15_R36_AVB_SIGNING_REFERENCE_TAG
            / device_name
        )

        generated_key_root = (
            device_root
            / "keys"
            / "avb"
        )

        for partition_name in sorted(_REQUIRED_PARTITIONS):
            entries.append(
                AndroidDeviceTreeAvbSigningEntry(
                    partition_name=partition_name,
                    algorithm=algorithms[partition_name],
                    key_path=(
                        generated_key_root
                        / f"{partition_name}.pem"
                    ),
                    persistent_source=(
                        persistent_root
                        / f"{partition_name}.pem"
                    ),
                )
            )

        profile_id = (
            f"{ANDROID_15_R36_AVB_SIGNING_REFERENCE_TAG}/"
            "treeforge-development-keys"
        )

    return AndroidDeviceTreeAvbSigningProfile(
        profile_id=profile_id,
        provider=normalized_provider,
        reference_tag=ANDROID_15_R36_AVB_SIGNING_REFERENCE_TAG,
        rollback_index_expression=(
            ANDROID_15_R36_AVB_ROLLBACK_INDEX_EXPRESSION
        ),
        entries=tuple(entries),
    )
