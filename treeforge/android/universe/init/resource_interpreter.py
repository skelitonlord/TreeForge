from __future__ import annotations

from treeforge.android.parsing.init.model import (
    AndroidInitService,
)
from treeforge.android.universe.init.resources import (
    AndroidUniverseInitFileSemantics,
    AndroidUniverseInitInterfaceSemantics,
    AndroidUniverseInitSocketSemantics,
)


class AndroidUniverseInitServiceResourceInterpreter:
    """
    Interpret resources and interface contracts owned by one init service.
    """

    def sockets(
        self,
        service: AndroidInitService,
    ) -> tuple[
        AndroidUniverseInitSocketSemantics,
        ...,
    ]:
        self._validate_service(
            service
        )

        results = []

        for declaration in service.options_for(
            "socket"
        ):
            argument_count = len(
                declaration.arguments
            )

            if not 3 <= argument_count <= 6:
                raise ValueError(
                    "expected three through six arguments for "
                    "init service option 'socket' on "
                    f"service {service.name!r}; found "
                    f"{argument_count}"
                )

            results.append(
                AndroidUniverseInitSocketSemantics(
                    name=declaration.arguments[0],
                    socket_type=declaration.arguments[1],
                    mode=declaration.arguments[2],
                    user=(
                        declaration.arguments[3]
                        if argument_count >= 4
                        else None
                    ),
                    group=(
                        declaration.arguments[4]
                        if argument_count >= 5
                        else None
                    ),
                    seclabel=(
                        declaration.arguments[5]
                        if argument_count >= 6
                        else None
                    ),
                    declaration=declaration,
                )
            )

        return tuple(
            results
        )

    def files(
        self,
        service: AndroidInitService,
    ) -> tuple[
        AndroidUniverseInitFileSemantics,
        ...,
    ]:
        self._validate_service(
            service
        )

        results = []

        for declaration in service.options_for(
            "file"
        ):
            if len(
                declaration.arguments
            ) != 2:
                raise ValueError(
                    "expected exactly two arguments for "
                    "init service option 'file' on "
                    f"service {service.name!r}; found "
                    f"{len(declaration.arguments)}"
                )

            results.append(
                AndroidUniverseInitFileSemantics(
                    path=declaration.arguments[0],
                    access=declaration.arguments[1],
                    declaration=declaration,
                )
            )

        return tuple(
            results
        )

    def interfaces(
        self,
        service: AndroidInitService,
    ) -> tuple[
        AndroidUniverseInitInterfaceSemantics,
        ...,
    ]:
        self._validate_service(
            service
        )

        results = []

        for declaration in service.options_for(
            "interface"
        ):
            if len(
                declaration.arguments
            ) != 2:
                raise ValueError(
                    "expected exactly two arguments for "
                    "init service option 'interface' on "
                    f"service {service.name!r}; found "
                    f"{len(declaration.arguments)}"
                )

            results.append(
                AndroidUniverseInitInterfaceSemantics(
                    transport=declaration.arguments[0],
                    name=declaration.arguments[1],
                    declaration=declaration,
                )
            )

        return tuple(
            results
        )

    @staticmethod
    def _validate_service(
        service: AndroidInitService,
    ) -> None:
        if not isinstance(
            service,
            AndroidInitService,
        ):
            raise TypeError(
                "service must be an AndroidInitService"
            )
