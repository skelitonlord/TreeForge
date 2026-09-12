from __future__ import annotations

import json

from hashlib import sha256
from pathlib import Path, PurePosixPath

from treeforge.android.recovery.runtime_provider import (
    RecoveryRuntimeProvider,
    RecoveryRuntimeProviderFile,
)
from treeforge.android.host_provider_sync import materialize_android_provider
from treeforge.android.host_provider_sync import verify_materialized_android_provider_root


TREEFORGE_RECOVERY_RUNTIME_PROVIDER_BUNDLE_SCHEMA = 1


class RecoveryRuntimeProviderBundleError(
    RuntimeError
):
    """
    Raised when a bundled Recovery runtime provider is invalid.
    """


def recovery_runtime_provider_bundle_root(
    name: str,
    release: str,
) -> Path:
    return materialize_android_provider(
        name=name,
        release=release,
    )


class RecoveryRuntimeProviderBundleLoader:
    """
    Load and verify one TreeForge-bundled Recovery runtime provider.

    The manifest format intentionally follows TreeForge's existing
    runtime-provider schema used by Android Recovery providers so device-runtime
    provider data has one consistent storage convention.

    Recovery owns provider selection and consumption. This loader has
    no Bootstrap dependency and performs no AOSP lookup.
    """

    MANIFEST_NAME = "manifest.json"

    @classmethod
    def load(
        cls,
        root: Path,
    ) -> RecoveryRuntimeProvider:
        if not isinstance(
            root,
            Path,
        ):
            raise TypeError(
                "root must be a Path"
            )

        root = (
            root
            .expanduser()
            .resolve()
        )

        verify_materialized_android_provider_root(
            root
        )

        if not root.is_dir():
            raise RecoveryRuntimeProviderBundleError(
                "runtime provider root is unavailable: "
                f"{root}"
            )

        manifest_path = (
            root
            / cls.MANIFEST_NAME
        )

        if not manifest_path.is_file():
            raise RecoveryRuntimeProviderBundleError(
                "runtime provider manifest is unavailable: "
                f"{manifest_path}"
            )

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as error:
            raise RecoveryRuntimeProviderBundleError(
                "unable to read runtime provider manifest: "
                f"{manifest_path}: {error}"
            ) from error

        if not isinstance(
            manifest,
            dict,
        ):
            raise RecoveryRuntimeProviderBundleError(
                "runtime provider manifest root must be an object"
            )

        schema = manifest.get(
            "schema"
        )

        if (
            isinstance(
                schema,
                bool,
            )
            or schema
            != TREEFORGE_RECOVERY_RUNTIME_PROVIDER_BUNDLE_SCHEMA
        ):
            raise RecoveryRuntimeProviderBundleError(
                "unsupported runtime provider bundle schema: "
                f"{schema!r}"
            )

        def required_string(
            key: str,
        ) -> str:
            value = manifest.get(
                key
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider manifest field "
                    f"{key!r} must be a non-empty string"
                )

            return value

        name = required_string(
            "name"
        )

        release = required_string(
            "release"
        )

        canonical_sdk_level = required_string(
            "canonical_sdk_level"
        )

        architecture = required_string(
            "architecture"
        )

        raw_files = manifest.get(
            "files"
        )

        if (
            not isinstance(
                raw_files,
                list,
            )
            or not raw_files
        ):
            raise RecoveryRuntimeProviderBundleError(
                "runtime provider manifest files must be a "
                "non-empty list"
            )

        provider_files = []

        for index, raw_file in enumerate(
            raw_files
        ):
            if not isinstance(
                raw_file,
                dict,
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider manifest file entry "
                    f"{index} must be an object"
                )

            android_path_raw = raw_file.get(
                "android_path"
            )

            source_relative_raw = raw_file.get(
                "path"
            )

            content_sha256 = raw_file.get(
                "sha256"
            )

            if (
                not isinstance(
                    android_path_raw,
                    str,
                )
                or not android_path_raw
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider file android_path must be "
                    "a non-empty string"
                )

            android_path = PurePosixPath(
                android_path_raw
            )

            if (
                not android_path.is_absolute()
                or ".." in android_path.parts
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider android_path must be an "
                    "absolute Android path without parent traversal: "
                    f"{android_path_raw!r}"
                )

            if (
                not isinstance(
                    source_relative_raw,
                    str,
                )
                or not source_relative_raw
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider file path must be a "
                    "non-empty string"
                )

            source_relative = PurePosixPath(
                source_relative_raw
            )

            if (
                source_relative.is_absolute()
                or ".." in source_relative.parts
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider file path must remain inside "
                    "the provider bundle: "
                    f"{source_relative_raw!r}"
                )

            if (
                not isinstance(
                    content_sha256,
                    str,
                )
                or len(content_sha256) != 64
                or any(
                    character
                    not in "0123456789abcdef"
                    for character in content_sha256
                )
            ):
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider file sha256 must be one "
                    "lowercase SHA-256 digest"
                )

            source_path = root.joinpath(
                *source_relative.parts
            )

            try:
                resolved_source_path = (
                    source_path
                    .resolve(
                        strict=True
                    )
                )
            except FileNotFoundError as error:
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider file is unavailable: "
                    f"{source_path}"
                ) from error

            try:
                resolved_source_path.relative_to(
                    root
                )
            except ValueError as error:
                verify_materialized_android_provider_root(resolved_source_path)

            if not resolved_source_path.is_file():
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider path is not a regular file: "
                    f"{resolved_source_path}"
                )

            try:
                actual_sha256 = sha256(
                    resolved_source_path.read_bytes()
                ).hexdigest()
            except OSError as error:
                raise RecoveryRuntimeProviderBundleError(
                    "unable to read runtime provider file: "
                    f"{resolved_source_path}: {error}"
                ) from error

            if actual_sha256 != content_sha256:
                raise RecoveryRuntimeProviderBundleError(
                    "runtime provider file SHA-256 mismatch for "
                    f"{android_path}: expected {content_sha256}, "
                    f"got {actual_sha256}"
                )

            provider_files.append(
                RecoveryRuntimeProviderFile(
                    android_path=android_path,
                    source_path=resolved_source_path,
                    content_sha256=actual_sha256,
                )
            )

        return RecoveryRuntimeProvider(
            name=name,
            release=release,
            canonical_sdk_level=(
                canonical_sdk_level
            ),
            architecture=architecture,
            files=tuple(
                provider_files
            ),
        )


__all__ = (
    "RecoveryRuntimeProviderBundleError",
    "RecoveryRuntimeProviderBundleLoader",
    "TREEFORGE_RECOVERY_RUNTIME_PROVIDER_BUNDLE_SCHEMA",
    "recovery_runtime_provider_bundle_root",
)
