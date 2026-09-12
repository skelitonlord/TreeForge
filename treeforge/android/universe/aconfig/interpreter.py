from __future__ import annotations

from treeforge.android.parsing.aconfig import (
    AndroidAconfigParsedFlag,
    AndroidAconfigParsingResult,
    AndroidAconfigTracepoint,
    ParsedAndroidAconfigConfiguration,
)
from treeforge.android.universe.aconfig.requirement import (
    AndroidUniverseAconfigConfigurationRequirement,
    AndroidUniverseAconfigFlagRequirement,
    AndroidUniverseAconfigRequirement,
)
from treeforge.android.universe.aconfig.semantics import (
    AndroidUniverseAconfigFlagSemantics,
    AndroidUniverseAconfigTracepointSemantics,
)


class AndroidUniverseAconfigInterpreter:
    """
    Interpret canonical Aconfig Parsing into Universe requirements.

    This pass is deliberately Aconfig-local. Cross-source reconciliation
    and cross-family relationships remain separate Universe work.
    """

    def interpret(
        self,
        parsing: AndroidAconfigParsingResult,
    ) -> AndroidUniverseAconfigRequirement:
        if not isinstance(
            parsing,
            AndroidAconfigParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidAconfigParsingResult"
            )

        configurations = tuple(
            self._interpret_configuration(
                configuration
            )
            for configuration in parsing.configurations
        )

        return AndroidUniverseAconfigRequirement(
            source=parsing,
            configurations=configurations,
        )

    def _interpret_configuration(
        self,
        configuration: ParsedAndroidAconfigConfiguration,
    ) -> AndroidUniverseAconfigConfigurationRequirement:
        return AndroidUniverseAconfigConfigurationRequirement(
            source=configuration,
            flags=tuple(
                self._interpret_flag(
                    flag
                )
                for flag in configuration.flags
            ),
        )

    def _interpret_flag(
        self,
        flag: AndroidAconfigParsedFlag,
    ) -> AndroidUniverseAconfigFlagRequirement:
        state = (
            flag.known_state
            if flag.state_present
            else None
        )

        permission = (
            flag.known_permission
            if flag.permission_present
            else None
        )

        purpose = None

        if (
            flag.metadata_present
            and flag.metadata is not None
            and flag.metadata.purpose_present
        ):
            purpose = flag.metadata.known_purpose

        semantics = AndroidUniverseAconfigFlagSemantics(
            state=state,
            permission=permission,
            purpose=purpose,
            tracepoints=tuple(
                self._interpret_tracepoint(
                    tracepoint
                )
                for tracepoint in flag.tracepoints
            ),
        )

        return AndroidUniverseAconfigFlagRequirement(
            source=flag,
            semantics=semantics,
        )

    @staticmethod
    def _interpret_tracepoint(
        tracepoint: AndroidAconfigTracepoint,
    ) -> AndroidUniverseAconfigTracepointSemantics:
        return AndroidUniverseAconfigTracepointSemantics(
            source=tracepoint,
            state=(
                tracepoint.known_state
                if tracepoint.state_present
                else None
            ),
            permission=(
                tracepoint.known_permission
                if tracepoint.permission_present
                else None
            ),
        )
