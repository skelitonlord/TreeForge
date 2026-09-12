from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.aconfig import (
    AndroidAconfigParsedFlag,
    AndroidAconfigParsingResult,
    ParsedAndroidAconfigConfiguration,
)
from treeforge.android.universe.aconfig.semantics import (
    AndroidUniverseAconfigFlagSemantics,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAconfigFlagRequirement:
    """
    One canonical Aconfig flag requirement.

    The exact parsed flag remains attached by identity so raw protobuf
    representation, presence bits, unknown fields, description, bugs,
    metadata, container information, and tracepoint ordering remain
    available without semantic rewriting.
    """

    source: AndroidAconfigParsedFlag
    semantics: AndroidUniverseAconfigFlagSemantics

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidAconfigParsedFlag,
        ):
            raise TypeError(
                "source must be an AndroidAconfigParsedFlag"
            )

        if not isinstance(
            self.semantics,
            AndroidUniverseAconfigFlagSemantics,
        ):
            raise TypeError(
                "semantics must be an "
                "AndroidUniverseAconfigFlagSemantics"
            )

        expected_state = (
            self.source.known_state
            if self.source.state_present
            else None
        )

        if self.semantics.state is not expected_state:
            raise ValueError(
                "flag semantic state must reflect Parsing"
            )

        expected_permission = (
            self.source.known_permission
            if self.source.permission_present
            else None
        )

        if self.semantics.permission is not expected_permission:
            raise ValueError(
                "flag semantic permission must reflect Parsing"
            )

        expected_purpose = None

        if (
            self.source.metadata_present
            and self.source.metadata is not None
            and self.source.metadata.purpose_present
        ):
            expected_purpose = (
                self.source.metadata.known_purpose
            )

        if self.semantics.purpose is not expected_purpose:
            raise ValueError(
                "flag semantic purpose must reflect Parsing"
            )

        if len(
            self.semantics.tracepoints
        ) != len(
            self.source.tracepoints
        ):
            raise ValueError(
                "semantic tracepoint population must match Parsing"
            )

        for parsed, semantic in zip(
            self.source.tracepoints,
            self.semantics.tracepoints,
            strict=True,
        ):
            if semantic.source is not parsed:
                raise ValueError(
                    "semantic tracepoint must preserve exact "
                    "Parsing identity"
                )

    @property
    def canonical_identity(
        self,
    ) -> tuple[str, str] | None:
        """
        Return package/name only when both were explicitly present and
        non-empty. Missing identity components remain unresolved rather
        than being synthesized.
        """

        if (
            not self.source.package_present
            or not self.source.name_present
            or not self.source.package
            or not self.source.name
        ):
            return None

        return (
            self.source.package,
            self.source.name,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAconfigConfigurationRequirement:
    """
    Canonical semantic interpretation of one parsed Aconfig source.
    """

    source: ParsedAndroidAconfigConfiguration

    flags: tuple[
        AndroidUniverseAconfigFlagRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidAconfigConfiguration,
        ):
            raise TypeError(
                "source must be a "
                "ParsedAndroidAconfigConfiguration"
            )

        if not isinstance(
            self.flags,
            tuple,
        ):
            raise TypeError(
                "flags must be a tuple"
            )

        if not all(
            isinstance(
                flag,
                AndroidUniverseAconfigFlagRequirement,
            )
            for flag in self.flags
        ):
            raise TypeError(
                "flags must contain "
                "AndroidUniverseAconfigFlagRequirement"
            )

        if len(
            self.flags
        ) != len(
            self.source.flags
        ):
            raise ValueError(
                "Universe Aconfig flag population must match Parsing"
            )

        for parsed, requirement in zip(
            self.source.flags,
            self.flags,
            strict=True,
        ):
            if requirement.source is not parsed:
                raise ValueError(
                    "Aconfig flag requirement must preserve exact "
                    "Parsing identity"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseAconfigRequirement:
    """
    Canonical Universe interpretation of the complete Aconfig Parsing result.

    Parsing identity remains authoritative while per-source, per-flag, and
    per-tracepoint semantics are exposed for later reconciliation.
    """

    source: AndroidAconfigParsingResult

    configurations: tuple[
        AndroidUniverseAconfigConfigurationRequirement,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidAconfigParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidAconfigParsingResult"
            )

        if not isinstance(
            self.configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        if not all(
            isinstance(
                configuration,
                AndroidUniverseAconfigConfigurationRequirement,
            )
            for configuration in self.configurations
        ):
            raise TypeError(
                "configurations must contain "
                "AndroidUniverseAconfigConfigurationRequirement"
            )

        if len(
            self.configurations
        ) != len(
            self.source.configurations
        ):
            raise ValueError(
                "Universe Aconfig configuration population "
                "must match Parsing"
            )

        for parsed, requirement in zip(
            self.source.configurations,
            self.configurations,
            strict=True,
        ):
            if requirement.source is not parsed:
                raise ValueError(
                    "Aconfig configuration requirement must "
                    "preserve exact Parsing identity"
                )

    @property
    def flags(
        self,
    ) -> tuple[
        AndroidUniverseAconfigFlagRequirement,
        ...,
    ]:
        return tuple(
            flag
            for configuration in self.configurations
            for flag in configuration.flags
        )

    @property
    def tracepoint_count(
        self,
    ) -> int:
        return sum(
            len(
                flag.semantics.tracepoints
            )
            for flag in self.flags
        )
