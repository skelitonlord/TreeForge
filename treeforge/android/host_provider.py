from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _require_non_empty_string(
    value: object,
    *,
    field_name: str,
) -> str:
    if (
        not isinstance(value, str)
        or not value
    ):
        raise ValueError(
            f"{field_name} must be a non-empty string"
        )

    return value


def _require_sha256(
    value: object,
    *,
    field_name: str,
) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
    ):
        raise ValueError(
            f"{field_name} must be one lowercase SHA-256 hex digest"
        )

    return value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidHostProviderSource:
    """
    Exact upstream provenance for one implementation component.
    """

    platform: str
    platform_release: str
    module: str
    project: str
    revision: str
    source_path: str

    def __post_init__(self) -> None:
        for field_name in (
            "platform",
            "platform_release",
            "module",
            "project",
            "revision",
            "source_path",
        ):
            _require_non_empty_string(
                getattr(
                    self,
                    field_name,
                ),
                field_name=field_name,
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidHostProviderFile:
    """
    One verified non-executable file shipped by a provider.
    """

    relative_path: str
    path: Path
    content_sha256: str

    def __post_init__(self) -> None:
        _require_non_empty_string(
            self.relative_path,
            field_name="relative_path",
        )

        if not isinstance(
            self.path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        _require_sha256(
            self.content_sha256,
            field_name="content_sha256",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidHostProviderExecutable:
    """
    One verified executable and the capabilities it implements.
    """

    name: str
    relative_path: str
    path: Path
    content_sha256: str
    capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_empty_string(
            self.name,
            field_name="name",
        )
        _require_non_empty_string(
            self.relative_path,
            field_name="relative_path",
        )

        if not isinstance(
            self.path,
            Path,
        ):
            raise TypeError(
                "path must be a pathlib.Path"
            )

        _require_sha256(
            self.content_sha256,
            field_name="content_sha256",
        )

        if (
            not isinstance(
                self.capabilities,
                tuple,
            )
            or not self.capabilities
        ):
            raise ValueError(
                "capabilities must be a non-empty tuple"
            )

        for capability in self.capabilities:
            _require_non_empty_string(
                capability,
                field_name="capability",
            )

        if (
            len(self.capabilities)
            != len(
                set(
                    self.capabilities
                )
            )
        ):
            raise ValueError(
                "capabilities must be unique"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidHostProvider:
    """
    One normalized TreeForge-owned Android host-provider bundle.

    A provider can contain one or many executables. Runtime libraries,
    redistribution material, and provenance are verified with the same
    path-confinement and SHA-256 rules as executable content.
    """

    name: str
    release: str
    platform: str
    architecture: str
    root: Path
    executables: tuple[
        AndroidHostProviderExecutable,
        ...,
    ]
    runtime_files: tuple[
        AndroidHostProviderFile,
        ...,
    ]
    legal_files: tuple[
        AndroidHostProviderFile,
        ...,
    ]
    provenance_files: tuple[
        AndroidHostProviderFile,
        ...,
    ]
    provider_sources: tuple[
        AndroidHostProviderSource,
        ...,
    ]

    def __post_init__(self) -> None:
        for field_name in (
            "name",
            "release",
            "platform",
            "architecture",
        ):
            _require_non_empty_string(
                getattr(
                    self,
                    field_name,
                ),
                field_name=field_name,
            )

        if not isinstance(
            self.root,
            Path,
        ):
            raise TypeError(
                "root must be a pathlib.Path"
            )

        if not self.executables:
            raise ValueError(
                "provider must contain at least one executable"
            )

        if not self.legal_files:
            raise ValueError(
                "provider must contain legal material"
            )


        if not self.provider_sources:
            raise ValueError(
                "provider must contain source provenance"
            )

        executable_names = tuple(
            executable.name
            for executable
            in self.executables
        )

        if (
            len(executable_names)
            != len(
                set(
                    executable_names
                )
            )
        ):
            raise ValueError(
                "provider executable names must be unique"
            )

        capabilities = self.capabilities

        if (
            len(capabilities)
            != len(
                set(
                    capabilities
                )
            )
        ):
            raise ValueError(
                "provider capabilities must map to exactly one executable"
            )

    @property
    def capabilities(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            capability
            for executable
            in self.executables
            for capability
            in executable.capabilities
        )

    def supports(
        self,
        capability: str,
    ) -> bool:
        _require_non_empty_string(
            capability,
            field_name="capability",
        )

        return capability in self.capabilities

    def executable_for(
        self,
        capability: str,
    ) -> Path:
        _require_non_empty_string(
            capability,
            field_name="capability",
        )

        matches = tuple(
            executable
            for executable
            in self.executables
            if capability
            in executable.capabilities
        )

        if len(matches) != 1:
            raise KeyError(
                f"provider {self.name!r} does not map capability "
                f"{capability!r} to exactly one executable"
            )

        return matches[0].path

    def executable_named(
        self,
        name: str,
    ) -> Path:
        _require_non_empty_string(
            name,
            field_name="name",
        )

        matches = tuple(
            executable
            for executable
            in self.executables
            if executable.name == name
        )

        if len(matches) != 1:
            raise KeyError(
                f"provider {self.name!r} does not contain exactly "
                f"one executable named {name!r}"
            )

        return matches[0].path

    #
    # Compatibility surfaces for existing single-executable consumers.
    # All providers use schema 2; these properties do not represent a
    # second provider model.
    #
    @property
    def executable(self) -> Path:
        if len(self.executables) != 1:
            raise ValueError(
                f"provider {self.name!r} contains multiple executables; "
                "select by capability or executable name"
            )

        return self.executables[0].path

    @property
    def content_sha256(self) -> str:
        if len(self.executables) != 1:
            raise ValueError(
                f"provider {self.name!r} contains multiple executables; "
                "select the executable explicitly"
            )

        return self.executables[0].content_sha256

    @property
    def provider_source(
        self,
    ) -> AndroidHostProviderSource:
        if len(self.provider_sources) != 1:
            raise ValueError(
                f"provider {self.name!r} contains multiple source records; "
                "inspect provider_sources explicitly"
            )

        return self.provider_sources[0]


__all__ = (
    "AndroidHostProvider",
    "AndroidHostProviderExecutable",
    "AndroidHostProviderFile",
    "AndroidHostProviderSource",
)
