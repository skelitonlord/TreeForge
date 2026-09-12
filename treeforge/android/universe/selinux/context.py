from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.selinux import (
    AndroidSelinuxContextDeclaration,
    AndroidSelinuxSeappDeclaration,
)


class AndroidUniverseSelinuxContextKind(
    StrEnum,
):
    FILE = "file"
    PROPERTY = "property"
    SERVICE = "service"
    HWSERVICE = "hwservice"
    VNDSERVICE = "vndservice"
    KEYSTORE2_KEY = "keystore2_key"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxContextRequirement:
    """
    One canonical effective SELinux labeling requirement.

    Parsing identity remains attached through ``declaration``. Universe adds
    semantic family identity without changing the original selector/context
    material.
    """

    kind: AndroidUniverseSelinuxContextKind

    declaration: AndroidSelinuxContextDeclaration

    @property
    def selector(
        self,
    ) -> str:
        return self.declaration.selector

    @property
    def context(
        self,
    ) -> str:
        return self.declaration.context

    @property
    def selinux_type(
        self,
    ) -> str | None:
        parts = self.context.split(":")

        if len(parts) < 3:
            return None

        return parts[2]


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxSeappRequirement:
    """
    One canonical seapp_contexts requirement.

    Ordered Parsing fields remain attached exactly. Convenience lookups are
    additive Universe semantics.
    """

    declaration: AndroidSelinuxSeappDeclaration

    @property
    def fields(
        self,
    ) -> tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]:
        return tuple(
            (
                field.name,
                field.value,
            )
            for field
            in self.declaration.fields
        )

    def value(
        self,
        name: str,
    ) -> str | None:
        for field in self.declaration.fields:
            if field.name == name:
                return field.value

        return None

    @property
    def domain(
        self,
    ) -> str | None:
        return self.value(
            "domain"
        )

    @property
    def data_type(
        self,
    ) -> str | None:
        return self.value(
            "type"
        )