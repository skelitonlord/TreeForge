from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
import os
import json
import platform

from treeforge.android.host_provider import (
    AndroidHostProvider,
    AndroidHostProviderExecutable,
    AndroidHostProviderFile,
    AndroidHostProviderSource,
)


from treeforge.android.host_provider_sync import (
    materialize_android_host_provider,
)

TREEFORGE_ANDROID_HOST_PROVIDER_BUNDLE_SCHEMA = 2

ANDROID_15_HOST_PROVIDER_RELEASE = (
    "android-15.0.0_r36-linux-x86_64"
)


class AndroidHostProviderBundleError(
    RuntimeError
):
    """
    Raised when a TreeForge Android host-provider bundle is invalid.
    """


def _current_host_platform() -> str:
    return platform.system().strip().lower()


def _current_host_architecture() -> str:
    machine = (
        platform.machine()
        .strip()
        .lower()
    )

    return {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(
        machine,
        machine,
    )


def _sha256_file(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


class AndroidHostProviderBundleLoader:
    """
    Load and fully verify one normalized TreeForge Android host provider.
    """

    MANIFEST_NAME = "manifest.json"

    @classmethod
    def load(
        cls,
        root: Path,
        *,
        require_current_host: bool = True,
    ) -> AndroidHostProvider:
        if not isinstance(
            root,
            Path,
        ):
            raise TypeError(
                "root must be a pathlib.Path"
            )

        root = (
            root
            .expanduser()
            .resolve()
        )

        if not root.is_dir():
            raise AndroidHostProviderBundleError(
                "Android host provider root is unavailable: "
                f"{root}"
            )

        manifest_path = (
            root
            / cls.MANIFEST_NAME
        )

        if not manifest_path.is_file():
            raise AndroidHostProviderBundleError(
                "Android host provider manifest is unavailable: "
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
            raise AndroidHostProviderBundleError(
                "unable to read Android host provider manifest: "
                f"{manifest_path}: {error}"
            ) from error

        if not isinstance(
            manifest,
            dict,
        ):
            raise AndroidHostProviderBundleError(
                "Android host provider manifest root must be an object"
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
            != TREEFORGE_ANDROID_HOST_PROVIDER_BUNDLE_SCHEMA
        ):
            raise AndroidHostProviderBundleError(
                "unsupported Android host provider bundle schema: "
                f"{schema!r}"
            )

        def required_string(
            source: dict,
            key: str,
            *,
            context: str,
        ) -> str:
            value = source.get(
                key
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} field {key!r} must be a non-empty string"
                )

            return value

        def required_list(
            source: dict,
            key: str,
            *,
            context: str,
            allow_empty: bool,
        ) -> list:
            value = source.get(
                key
            )

            if not isinstance(
                value,
                list,
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} field {key!r} must be a list"
                )

            if (
                not allow_empty
                and not value
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} field {key!r} must not be empty"
                )

            return value

        name = required_string(
            manifest,
            "name",
            context="manifest",
        )

        release = required_string(
            manifest,
            "release",
            context="manifest",
        )

        host_platform = required_string(
            manifest,
            "platform",
            context="manifest",
        )

        architecture = required_string(
            manifest,
            "architecture",
            context="manifest",
        )

        if root.name != release:
            raise AndroidHostProviderBundleError(
                "Android host provider release does not match "
                f"directory identity: manifest={release!r}, "
                f"directory={root.name!r}"
            )

        if root.parent.name != name:
            raise AndroidHostProviderBundleError(
                "Android host provider name does not match "
                f"directory identity: manifest={name!r}, "
                f"directory={root.parent.name!r}"
            )

        seen_paths: set[str] = set()

        def verify_file_entry(
            raw: object,
            *,
            context: str,
            require_executable: bool,
        ) -> tuple[
            str,
            Path,
            str,
        ]:
            if not isinstance(
                raw,
                dict,
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} must be an object"
                )

            relative_raw = required_string(
                raw,
                "path",
                context=context,
            )

            relative = PurePosixPath(
                relative_raw
            )

            if (
                relative.is_absolute()
                or ".."
                in relative.parts
                or not relative.parts
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} path must remain inside the bundle: "
                    f"{relative_raw!r}"
                )

            normalized_relative = (
                relative.as_posix()
            )

            if normalized_relative in seen_paths:
                raise AndroidHostProviderBundleError(
                    "Android host provider manifest declares "
                    f"duplicate file path: {normalized_relative}"
                )

            seen_paths.add(
                normalized_relative
            )

            expected_sha256 = required_string(
                raw,
                "sha256",
                context=context,
            )

            if (
                len(expected_sha256)
                != 64
                or any(
                    character
                    not in "0123456789abcdef"
                    for character
                    in expected_sha256
                )
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} sha256 must be one lowercase SHA-256 digest"
                )

            unresolved = root.joinpath(
                *relative.parts
            )

            try:
                path = unresolved.resolve(
                    strict=True
                )
            except FileNotFoundError as error:
                raise AndroidHostProviderBundleError(
                    f"{context} is unavailable: {unresolved}"
                ) from error

            try:
                path.relative_to(
                    root
                )
            except ValueError as error:
                raise AndroidHostProviderBundleError(
                    f"{context} escapes bundle root: {path}"
                ) from error

            if not path.is_file():
                raise AndroidHostProviderBundleError(
                    f"{context} is not a regular file: {path}"
                )

            if (
                require_executable
                and (
                    path.stat().st_mode
                    & 0o111
                )
                == 0
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} is not executable: {path}"
                )

            try:
                actual_sha256 = (
                    _sha256_file(
                        path
                    )
                )
            except OSError as error:
                raise AndroidHostProviderBundleError(
                    f"unable to hash {context}: {path}: {error}"
                ) from error

            if (
                actual_sha256
                != expected_sha256
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} SHA-256 mismatch: "
                    f"expected {expected_sha256}, got {actual_sha256}"
                )

            return (
                normalized_relative,
                path,
                actual_sha256,
            )

        raw_executables = required_list(
            manifest,
            "executables",
            context="manifest",
            allow_empty=False,
        )

        executables = []
        executable_names: set[str] = set()
        capabilities_seen: set[str] = set()

        for index, raw in enumerate(
            raw_executables
        ):
            context = (
                f"executables[{index}]"
            )

            if not isinstance(
                raw,
                dict,
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} must be an object"
                )

            executable_name = required_string(
                raw,
                "name",
                context=context,
            )

            if executable_name in executable_names:
                raise AndroidHostProviderBundleError(
                    "Android host provider executable names must be unique: "
                    f"{executable_name!r}"
                )

            executable_names.add(
                executable_name
            )

            raw_capabilities = required_list(
                raw,
                "capabilities",
                context=context,
                allow_empty=False,
            )

            capabilities = []

            for capability_index, capability in enumerate(
                raw_capabilities
            ):
                if (
                    not isinstance(
                        capability,
                        str,
                    )
                    or not capability
                ):
                    raise AndroidHostProviderBundleError(
                        f"{context} capability {capability_index} "
                        "must be a non-empty string"
                    )

                if capability in capabilities_seen:
                    raise AndroidHostProviderBundleError(
                        "Android host provider capability is implemented "
                        f"by multiple executables: {capability!r}"
                    )

                capabilities_seen.add(
                    capability
                )

                capabilities.append(
                    capability
                )

            (
                relative_path,
                path,
                content_sha256,
            ) = verify_file_entry(
                raw,
                context=context,
                require_executable=True,
            )

            executables.append(
                AndroidHostProviderExecutable(
                    name=executable_name,
                    relative_path=relative_path,
                    path=path,
                    content_sha256=content_sha256,
                    capabilities=tuple(
                        capabilities
                    ),
                )
            )

        def load_regular_file_set(
            key: str,
            *,
            allow_empty: bool,
        ) -> tuple[
            AndroidHostProviderFile,
            ...,
        ]:
            raw_entries = required_list(
                manifest,
                key,
                context="manifest",
                allow_empty=allow_empty,
            )

            result = []

            for index, raw in enumerate(
                raw_entries
            ):
                (
                    relative_path,
                    path,
                    content_sha256,
                ) = verify_file_entry(
                    raw,
                    context=f"{key}[{index}]",
                    require_executable=False,
                )

                result.append(
                    AndroidHostProviderFile(
                        relative_path=relative_path,
                        path=path,
                        content_sha256=content_sha256,
                    )
                )

            return tuple(
                result
            )

        runtime_files = (
            load_regular_file_set(
                "runtime_files",
                allow_empty=True,
            )
        )

        legal_files = (
            load_regular_file_set(
                "legal_files",
                allow_empty=False,
            )
        )

        provenance_files = (
            load_regular_file_set(
                "provenance_files",
                allow_empty=True,
            )
        )

        raw_sources = required_list(
            manifest,
            "provider_sources",
            context="manifest",
            allow_empty=False,
        )

        provider_sources = []

        for index, raw_source in enumerate(
            raw_sources
        ):
            context = (
                f"provider_sources[{index}]"
            )

            if not isinstance(
                raw_source,
                dict,
            ):
                raise AndroidHostProviderBundleError(
                    f"{context} must be an object"
                )

            provider_sources.append(
                AndroidHostProviderSource(
                    platform=required_string(
                        raw_source,
                        "platform",
                        context=context,
                    ),
                    platform_release=required_string(
                        raw_source,
                        "platform_release",
                        context=context,
                    ),
                    module=required_string(
                        raw_source,
                        "module",
                        context=context,
                    ),
                    project=required_string(
                        raw_source,
                        "project",
                        context=context,
                    ),
                    revision=required_string(
                        raw_source,
                        "revision",
                        context=context,
                    ),
                    source_path=required_string(
                        raw_source,
                        "source_path",
                        context=context,
                    ),
                )
            )

        if require_current_host:
            current_platform = (
                _current_host_platform()
            )

            current_architecture = (
                _current_host_architecture()
            )

            if (
                host_platform
                != current_platform
            ):
                raise AndroidHostProviderBundleError(
                    "Android host provider platform does not match "
                    f"current host: provider={host_platform!r}, "
                    f"host={current_platform!r}"
                )

            if (
                architecture
                != current_architecture
            ):
                raise AndroidHostProviderBundleError(
                    "Android host provider architecture does not match "
                    f"current host: provider={architecture!r}, "
                    f"host={current_architecture!r}"
                )

        return AndroidHostProvider(
            name=name,
            release=release,
            platform=host_platform,
            architecture=architecture,
            root=root,
            executables=tuple(
                executables
            ),
            runtime_files=runtime_files,
            legal_files=legal_files,
            provenance_files=provenance_files,
            provider_sources=tuple(
                provider_sources
            ),
        )


def android_host_provider_bundle_root(
    *,
    name: str,
    release: str,
) -> Path:
    return materialize_android_host_provider(
        name=name,
        release=release,
    )


__all__ = (
    "ANDROID_15_HOST_PROVIDER_RELEASE",
    "AndroidHostProviderBundleError",
    "AndroidHostProviderBundleLoader",
    "TREEFORGE_ANDROID_HOST_PROVIDER_BUNDLE_SCHEMA",
    "android_host_provider_bundle_root",
)
