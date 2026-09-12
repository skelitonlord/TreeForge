from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.kernel_module import (
    AndroidKernelModuleConfigurationKind,
    AndroidKernelModuleConfigurationLine,
    ParsedAndroidKernelModuleInfoEntry,
)


class AndroidUniverseKernelModuleInfoKind(StrEnum):
    NAME = "name"
    DEPENDS = "depends"
    ALIAS = "alias"
    FIRMWARE = "firmware"
    VERMAGIC = "vermagic"
    PARAMETER = "parm"
    PARAMETER_TYPE = "parmtype"
    SOFTDEP = "softdep"
    LICENSE = "license"
    AUTHOR = "author"
    DESCRIPTION = "description"
    IMPORT_NAMESPACE = "import_ns"
    INTREE = "intree"
    SCMVERSION = "scmversion"
    SRCVERSION = "srcversion"
    VERSION = "version"
    OTHER = "other"
    UNKEYED = "unkeyed"


_STANDARD_MODINFO_KINDS = {
    "name": AndroidUniverseKernelModuleInfoKind.NAME,
    "depends": AndroidUniverseKernelModuleInfoKind.DEPENDS,
    "alias": AndroidUniverseKernelModuleInfoKind.ALIAS,
    "firmware": AndroidUniverseKernelModuleInfoKind.FIRMWARE,
    "vermagic": AndroidUniverseKernelModuleInfoKind.VERMAGIC,
    "parm": AndroidUniverseKernelModuleInfoKind.PARAMETER,
    "parmtype": AndroidUniverseKernelModuleInfoKind.PARAMETER_TYPE,
    "softdep": AndroidUniverseKernelModuleInfoKind.SOFTDEP,
    "license": AndroidUniverseKernelModuleInfoKind.LICENSE,
    "author": AndroidUniverseKernelModuleInfoKind.AUTHOR,
    "description": AndroidUniverseKernelModuleInfoKind.DESCRIPTION,
    "import_ns": AndroidUniverseKernelModuleInfoKind.IMPORT_NAMESPACE,
    "intree": AndroidUniverseKernelModuleInfoKind.INTREE,
    "scmversion": AndroidUniverseKernelModuleInfoKind.SCMVERSION,
    "srcversion": AndroidUniverseKernelModuleInfoKind.SRCVERSION,
    "version": AndroidUniverseKernelModuleInfoKind.VERSION,
}


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleInfoSemantics:
    """
    Semantic classification of one exact .modinfo record.

    The complete parsed key/value remains authoritative. Only exact standard
    keys receive a known semantic family; namespaced or future keys remain
    preserved as OTHER rather than being guessed from suffixes.
    """

    source: ParsedAndroidKernelModuleInfoEntry
    kind: AndroidUniverseKernelModuleInfoKind

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidKernelModuleInfoEntry,
        ):
            raise TypeError(
                "source must be a ParsedAndroidKernelModuleInfoEntry"
            )

        if not isinstance(
            self.kind,
            AndroidUniverseKernelModuleInfoKind,
        ):
            raise TypeError(
                "kind must be an AndroidUniverseKernelModuleInfoKind"
            )

        expected = (
            AndroidUniverseKernelModuleInfoKind.UNKEYED
            if self.source.key is None
            else _STANDARD_MODINFO_KINDS.get(
                self.source.key,
                AndroidUniverseKernelModuleInfoKind.OTHER,
            )
        )

        if self.kind is not expected:
            raise ValueError(
                "modinfo semantic kind must reflect the exact parsed key"
            )

    @property
    def key(
        self,
    ) -> str | None:
        return self.source.key

    @property
    def value(
        self,
    ) -> str | None:
        return self.source.value


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleConfigurationLineSemantics:
    """
    Typed semantic interpretation of one modules.* line.

    ``interpreted=False`` preserves unexpected future grammar without forcing
    Parsing or Universe to discard the source line.
    """

    source: AndroidKernelModuleConfigurationLine
    configuration_kind: AndroidKernelModuleConfigurationKind
    interpreted: bool

    module: str | None = None
    dependencies: tuple[str, ...] = ()
    alias_pattern: str | None = None
    pre_dependencies: tuple[str, ...] = ()
    post_dependencies: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidKernelModuleConfigurationLine,
        ):
            raise TypeError(
                "source must be an AndroidKernelModuleConfigurationLine"
            )

        if not isinstance(
            self.configuration_kind,
            AndroidKernelModuleConfigurationKind,
        ):
            raise TypeError(
                "configuration_kind must be an "
                "AndroidKernelModuleConfigurationKind"
            )

        if not isinstance(
            self.interpreted,
            bool,
        ):
            raise TypeError(
                "interpreted must be a bool"
            )

        if (
            self.module is not None
            and (
                not isinstance(
                    self.module,
                    str,
                )
                or not self.module
            )
        ):
            raise ValueError(
                "module must be a non-empty string or None"
            )

        if (
            self.alias_pattern is not None
            and (
                not isinstance(
                    self.alias_pattern,
                    str,
                )
                or not self.alias_pattern
            )
        ):
            raise ValueError(
                "alias_pattern must be a non-empty string or None"
            )

        for name, values in (
            ("dependencies", self.dependencies),
            ("pre_dependencies", self.pre_dependencies),
            ("post_dependencies", self.post_dependencies),
        ):
            if not isinstance(
                values,
                tuple,
            ) or not all(
                isinstance(
                    value,
                    str,
                )
                and value
                for value in values
            ):
                raise TypeError(
                    f"{name} must contain non-empty strings"
                )
