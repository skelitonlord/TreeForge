from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.aconfig import (
    AndroidAconfigFlagPermission,
    AndroidAconfigFlagPurpose,
    AndroidAconfigFlagState,
    AndroidAconfigTracepoint,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAconfigTracepointSemantics:
    """
    Canonical semantic view of one parsed Aconfig tracepoint.

    Parsing identity remains authoritative. Presence bits are retained
    separately from normalized enum values so absent fields and unknown
    future enum values are never conflated.
    """

    source: AndroidAconfigTracepoint

    state: AndroidAconfigFlagState | None
    permission: AndroidAconfigFlagPermission | None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidAconfigTracepoint,
        ):
            raise TypeError(
                "source must be an AndroidAconfigTracepoint"
            )

        if (
            self.state is not None
            and not isinstance(
                self.state,
                AndroidAconfigFlagState,
            )
        ):
            raise TypeError(
                "state must be an AndroidAconfigFlagState or None"
            )

        if (
            self.permission is not None
            and not isinstance(
                self.permission,
                AndroidAconfigFlagPermission,
            )
        ):
            raise TypeError(
                "permission must be an "
                "AndroidAconfigFlagPermission or None"
            )

        expected_state = (
            self.source.known_state
            if self.source.state_present
            else None
        )

        if self.state is not expected_state:
            raise ValueError(
                "state must reflect the exact parsed tracepoint state"
            )

        expected_permission = (
            self.source.known_permission
            if self.source.permission_present
            else None
        )

        if self.permission is not expected_permission:
            raise ValueError(
                "permission must reflect the exact parsed "
                "tracepoint permission"
            )

    @property
    def state_present(
        self,
    ) -> bool:
        return self.source.state_present

    @property
    def state_value(
        self,
    ) -> int:
        return self.source.state_value

    @property
    def state_known(
        self,
    ) -> bool:
        return (
            self.source.state_present
            and self.state is not None
        )

    @property
    def permission_present(
        self,
    ) -> bool:
        return self.source.permission_present

    @property
    def permission_value(
        self,
    ) -> int:
        return self.source.permission_value

    @property
    def permission_known(
        self,
    ) -> bool:
        return (
            self.source.permission_present
            and self.permission is not None
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAconfigFlagSemantics:
    """
    Canonical semantic interpretation of one parsed Aconfig flag.

    The source flag remains attached exactly. Universe exposes known
    enum meanings while preserving protobuf presence and raw values
    through that canonical Parsing object.
    """

    state: AndroidAconfigFlagState | None
    permission: AndroidAconfigFlagPermission | None
    purpose: AndroidAconfigFlagPurpose | None

    tracepoints: tuple[
        AndroidUniverseAconfigTracepointSemantics,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            self.state is not None
            and not isinstance(
                self.state,
                AndroidAconfigFlagState,
            )
        ):
            raise TypeError(
                "state must be an AndroidAconfigFlagState or None"
            )

        if (
            self.permission is not None
            and not isinstance(
                self.permission,
                AndroidAconfigFlagPermission,
            )
        ):
            raise TypeError(
                "permission must be an "
                "AndroidAconfigFlagPermission or None"
            )

        if (
            self.purpose is not None
            and not isinstance(
                self.purpose,
                AndroidAconfigFlagPurpose,
            )
        ):
            raise TypeError(
                "purpose must be an AndroidAconfigFlagPurpose or None"
            )

        if not isinstance(
            self.tracepoints,
            tuple,
        ):
            raise TypeError(
                "tracepoints must be a tuple"
            )

        if not all(
            isinstance(
                tracepoint,
                AndroidUniverseAconfigTracepointSemantics,
            )
            for tracepoint in self.tracepoints
        ):
            raise TypeError(
                "tracepoints must contain "
                "AndroidUniverseAconfigTracepointSemantics"
            )
