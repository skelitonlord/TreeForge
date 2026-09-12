from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.reconstruction_ownership.source.model import (
    AndroidSourceRepository,
    AndroidSourceRepositoryInventory,
)


class AndroidSourceBuildSystem(StrEnum):
    """
    Build-language family that declares one source module.
    """

    SOONG = "soong"
    MAKE = "make"


class AndroidSourceBuildPropertyKind(StrEnum):
    """
    Literal property-value kind recoverable without evaluating the build
    language.
    """

    STRING = "string"
    BOOLEAN = "boolean"
    STRING_LIST = "string_list"


AndroidSourceBuildPropertyValue = (
    str
    | bool
    | tuple[str, ...]
)


@dataclass(frozen=True, slots=True)
class AndroidSourceBuildProperty:
    """
    One literal property declaration from a source build module.

    Soong nested literal property scopes are flattened into deterministic
    dotted property paths.  For example, a literal leaf declared beneath
    ``multilib.lib64`` is represented as ``multilib.lib64.<leaf>``.

    Only literal leaf values are represented.  The model does not evaluate
    Soong expressions, variables, conditions, selectors, or build semantics.
    """

    name: str
    kind: AndroidSourceBuildPropertyKind
    value: AndroidSourceBuildPropertyValue
    source_line: int

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "property name must be a non-empty string"
            )

        if not isinstance(
            self.kind,
            AndroidSourceBuildPropertyKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidSourceBuildPropertyKind"
            )

        if (
            not isinstance(
                self.source_line,
                int,
            )
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be a positive integer"
            )

        if (
            self.kind
            is AndroidSourceBuildPropertyKind.STRING
        ):
            if not isinstance(
                self.value,
                str,
            ):
                raise TypeError(
                    "STRING property value must be str"
                )

        elif (
            self.kind
            is AndroidSourceBuildPropertyKind.BOOLEAN
        ):
            if not isinstance(
                self.value,
                bool,
            ):
                raise TypeError(
                    "BOOLEAN property value must be bool"
                )

        elif (
            self.kind
            is AndroidSourceBuildPropertyKind.STRING_LIST
        ):
            if (
                not isinstance(
                    self.value,
                    tuple,
                )
                or not all(
                    isinstance(
                        item,
                        str,
                    )
                    for item in self.value
                )
            ):
                raise TypeError(
                    "STRING_LIST property value must "
                    "be tuple[str, ...]"
                )


@dataclass(frozen=True, slots=True)
class AndroidSourceBuildModule:
    """
    One literal build-module declaration from an Android source checkout.

    This is source evidence only.  A build-module declaration does not by
    itself prove target-product consumption, installed-artifact identity,
    source availability, or Reconstruction Ownership.
    """

    name: str
    build_system: AndroidSourceBuildSystem
    module_type: str

    source_path: str
    source_line: int

    repository: AndroidSourceRepository

    properties: tuple[
        AndroidSourceBuildProperty,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "name must be a non-empty string"
            )

        if not isinstance(
            self.build_system,
            AndroidSourceBuildSystem,
        ):
            raise TypeError(
                "build_system must be an "
                "AndroidSourceBuildSystem"
            )

        if (
            not isinstance(
                self.module_type,
                str,
            )
            or not self.module_type
        ):
            raise ValueError(
                "module_type must be a non-empty string"
            )

        if (
            not isinstance(
                self.source_path,
                str,
            )
            or not self.source_path
        ):
            raise ValueError(
                "source_path must be a non-empty string"
            )

        if self.source_path.startswith(
            "/"
        ):
            raise ValueError(
                "source_path must be checkout-relative"
            )

        if ".." in self.source_path.split(
            "/"
        ):
            raise ValueError(
                "source_path must not contain traversal"
            )

        if (
            not isinstance(
                self.source_line,
                int,
            )
            or self.source_line <= 0
        ):
            raise ValueError(
                "source_line must be a positive integer"
            )

        if not isinstance(
            self.repository,
            AndroidSourceRepository,
        ):
            raise TypeError(
                "repository must be an "
                "AndroidSourceRepository"
            )

        if (
            not isinstance(
                self.properties,
                tuple,
            )
            or not all(
                isinstance(
                    prop,
                    AndroidSourceBuildProperty,
                )
                for prop in self.properties
            )
        ):
            raise TypeError(
                "properties must contain only "
                "AndroidSourceBuildProperty values"
            )

        expected_properties = tuple(
            sorted(
                self.properties,
                key=lambda prop: (
                    prop.source_line,
                    prop.name,
                ),
            )
        )

        if (
            self.properties
            != expected_properties
        ):
            raise ValueError(
                "properties must use deterministic "
                "source ordering"
            )

    @property
    def identity_key(
        self,
    ) -> tuple[
        str,
        str,
        int,
        str,
        str,
    ]:
        return (
            self.repository.project_path,
            self.source_path,
            self.source_line,
            self.build_system.value,
            self.name,
        )

    def properties_named(
        self,
        name: str,
    ) -> tuple[
        AndroidSourceBuildProperty,
        ...,
    ]:
        return tuple(
            prop
            for prop in self.properties
            if prop.name == name
        )

    def literal_string(
        self,
        name: str,
    ) -> str | None:
        values = self.properties_named(
            name
        )

        if len(values) != 1:
            return None

        prop = values[0]

        if (
            prop.kind
            is not AndroidSourceBuildPropertyKind.STRING
        ):
            return None

        assert isinstance(
            prop.value,
            str,
        )

        return prop.value

    def literal_boolean(
        self,
        name: str,
    ) -> bool | None:
        values = self.properties_named(
            name
        )

        if len(values) != 1:
            return None

        prop = values[0]

        if (
            prop.kind
            is not AndroidSourceBuildPropertyKind.BOOLEAN
        ):
            return None

        assert isinstance(
            prop.value,
            bool,
        )

        return prop.value

    def literal_string_list(
        self,
        name: str,
    ) -> tuple[str, ...] | None:
        values = self.properties_named(
            name
        )

        if len(values) != 1:
            return None

        prop = values[0]

        if (
            prop.kind
            is not AndroidSourceBuildPropertyKind.STRING_LIST
        ):
            return None

        assert isinstance(
            prop.value,
            tuple,
        )

        return prop.value


@dataclass(frozen=True, slots=True)
class AndroidSourceBuildModuleInventory:
    """
    Deterministic source build-module inventory for one Repo checkout.
    """

    repository_inventory: AndroidSourceRepositoryInventory

    build_files: tuple[
        str,
        ...,
    ]

    modules: tuple[
        AndroidSourceBuildModule,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.repository_inventory,
            AndroidSourceRepositoryInventory,
        ):
            raise TypeError(
                "repository_inventory must be an "
                "AndroidSourceRepositoryInventory"
            )

        if not isinstance(
            self.build_files,
            tuple,
        ) or not all(
            isinstance(
                path,
                str,
            )
            and path
            and not path.startswith("/")
            and ".." not in path.split("/")
            for path in self.build_files
        ):
            raise TypeError(
                "build_files must contain only "
                "checkout-relative path strings"
            )

        if self.build_files != tuple(
            sorted(
                set(
                    self.build_files
                )
            )
        ):
            raise ValueError(
                "build_files must be unique and "
                "deterministically ordered"
            )

        if not isinstance(
            self.modules,
            tuple,
        ) or not all(
            isinstance(
                module,
                AndroidSourceBuildModule,
            )
            for module in self.modules
        ):
            raise TypeError(
                "modules must contain only "
                "AndroidSourceBuildModule values"
            )

        expected = tuple(
            sorted(
                self.modules,
                key=lambda module: (
                    module.name,
                    module.repository.project_path,
                    module.source_path,
                    module.source_line,
                    module.build_system.value,
                    module.module_type,
                ),
            )
        )

        if self.modules != expected:
            raise ValueError(
                "modules must use deterministic ordering"
            )

        build_file_set = set(
            self.build_files
        )

        repositories = (
            self.repository_inventory.repositories
        )

        for module in self.modules:
            if (
                module.source_path
                not in build_file_set
            ):
                raise ValueError(
                    "module source_path must belong to "
                    "the indexed build-file population"
                )

            if not any(
                module.repository
                is repository
                for repository in repositories
            ):
                raise ValueError(
                    "module repository must preserve "
                    "exact repository-inventory identity"
                )

            owner = (
                self.repository_inventory
                .repository_for_source_path(
                    module.source_path
                )
            )

            if owner is not module.repository:
                raise ValueError(
                    "module source path must preserve "
                    "exact repository ownership"
                )

    def modules_named(
        self,
        name: str,
    ) -> tuple[
        AndroidSourceBuildModule,
        ...,
    ]:
        return tuple(
            module
            for module in self.modules
            if module.name == name
        )

    def modules_of_type(
        self,
        module_type: str,
    ) -> tuple[
        AndroidSourceBuildModule,
        ...,
    ]:
        return tuple(
            module
            for module in self.modules
            if module.module_type == module_type
        )

    def modules_for_repository(
        self,
        project_path: str,
    ) -> tuple[
        AndroidSourceBuildModule,
        ...,
    ]:
        return tuple(
            module
            for module in self.modules
            if (
                module.repository.project_path
                == project_path
            )
        )
