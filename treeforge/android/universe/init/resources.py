from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.init.model import (
    AndroidInitServiceOption,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitSocketSemantics:
    """
    Canonical semantic projection of one init ``socket`` declaration.

    Socket type and mode remain literal because Android permits composite
    socket types and mode spellings that should not be normalized here.
    """

    name: str
    socket_type: str
    mode: str
    declaration: AndroidInitServiceOption
    user: str | None = None
    group: str | None = None
    seclabel: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            ("name", self.name),
            ("socket_type", self.socket_type),
            ("mode", self.mode),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        for field_name, value in (
            ("user", self.user),
            ("group", self.group),
            ("seclabel", self.seclabel),
        ):
            if (
                value is not None
                and not isinstance(
                    value,
                    str,
                )
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )

            if value == "":
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "socket":
            raise ValueError(
                "socket declaration must use keyword "
                "'socket'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitFileSemantics:
    """
    Canonical semantic projection of one init ``file`` declaration.

    Paths remain literal so property substitutions and other Android path
    syntax are preserved exactly as parsed.
    """

    path: str
    access: str
    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            ("path", self.path),
            ("access", self.access),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "file":
            raise ValueError(
                "file declaration must use keyword "
                "'file'"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseInitInterfaceSemantics:
    """
    Canonical semantic projection of one init ``interface`` declaration.

    The interface name remains one literal value. Some Android declarations
    contain a fully-qualified interface/instance pair while others use a
    simple service name, so that grammar is intentionally not split here.
    """

    transport: str
    name: str
    declaration: AndroidInitServiceOption

    def __post_init__(
        self,
    ) -> None:
        for field_name, value in (
            ("transport", self.transport),
            ("name", self.name),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if not isinstance(
            self.declaration,
            AndroidInitServiceOption,
        ):
            raise TypeError(
                "declaration must be an "
                "AndroidInitServiceOption"
            )

        if self.declaration.keyword != "interface":
            raise ValueError(
                "interface declaration must use keyword "
                "'interface'"
            )
