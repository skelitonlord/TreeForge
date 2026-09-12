from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidIdentityKind(
    StrEnum,
):
    """
    Identity dimensions that TreeForge may infer directly from Discovery
    evidence.

    A dimension may remain unknown indefinitely when Discovery has not
    collected evidence sufficient to identify it.
    """

    DEVICE = "device"
    BOARD_PLATFORM = "board_platform"
    ANDROID_VERSION = "android_version"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidIdentityEvidence:
    """
    One immutable piece of source-backed Discovery identity evidence.

    value is the exact identity candidate supported by the evidence.

    source preserves the canonical Discovery source identity that supplied the
    evidence.

    detail provides a human-readable explanation of what the discovered source
    directly established.

    This model does not interpret device/platform relationships, select
    knowledge modules, or apply build policy.
    """

    kind: AndroidIdentityKind

    value: str

    source: str

    detail: str

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidIdentityKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidIdentityKind"
            )

        self._validate_string(
            self.value,
            field_name="value",
        )

        self._validate_string(
            self.source,
            field_name="source",
        )

        self._validate_string(
            self.detail,
            field_name="detail",
        )

    @staticmethod
    def _validate_string(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidIdentityInferenceResult:
    """
    Immutable post-Discovery identity inference result.

    Only identities directly supported by Discovery evidence are represented.

    None means Discovery has not established that identity.

    In particular, this model does not derive:

        device -> platform
        platform -> OEM
        Android version -> version policy

    Those relationships belong to later TreeForge layers.

    evidence preserves every identity observation used during inference,
    including conflicting observations when a unique result cannot be chosen.
    """

    device_id: str | None = None

    board_platform: str | None = None

    android_version: str | None = None

    evidence: tuple[
        AndroidIdentityEvidence,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        self._validate_optional_string(
            self.device_id,
            field_name="device_id",
        )

        self._validate_optional_string(
            self.board_platform,
            field_name="board_platform",
        )

        self._validate_optional_string(
            self.android_version,
            field_name="android_version",
        )

        if not isinstance(
            self.evidence,
            tuple,
        ):
            raise TypeError(
                "evidence must be a tuple"
            )

        for evidence in self.evidence:
            if not isinstance(
                evidence,
                AndroidIdentityEvidence,
            ):
                raise TypeError(
                    "evidence must contain "
                    "AndroidIdentityEvidence instances"
                )

        canonical_evidence = tuple(
            sorted(
                self.evidence,
                key=lambda item: (
                    item.kind.value,
                    item.value,
                    item.source,
                    item.detail,
                ),
            )
        )

        object.__setattr__(
            self,
            "evidence",
            canonical_evidence,
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        """
        Return whether Discovery inferred no identity dimensions.
        """

        return (
            self.device_id is None
            and self.board_platform is None
            and self.android_version is None
        )

    @property
    def has_device_identity(
        self,
    ) -> bool:
        """
        Return whether Discovery established a device identity.
        """

        return self.device_id is not None

    @property
    def has_board_platform(
        self,
    ) -> bool:
        """
        Return whether Discovery established a board/platform identity.
        """

        return self.board_platform is not None

    @property
    def has_android_version(
        self,
    ) -> bool:
        """
        Return whether Discovery established an Android version.
        """

        return (
            self.android_version
            is not None
        )

    def evidence_for(
        self,
        kind: AndroidIdentityKind,
    ) -> tuple[
        AndroidIdentityEvidence,
        ...,
    ]:
        """
        Return all evidence associated with one identity dimension.
        """

        if not isinstance(
            kind,
            AndroidIdentityKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidIdentityKind"
            )

        return tuple(
            evidence
            for evidence in self.evidence
            if evidence.kind is kind
        )

    @staticmethod
    def _validate_optional_string(
        value: object,
        *,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be "
                "a string or None"
            )

        if not value.strip():
            raise ValueError(
                f"{field_name} must not be empty"
            )