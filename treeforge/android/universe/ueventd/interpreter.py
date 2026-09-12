from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidUeventd,
)
from treeforge.android.parsing.ueventd import (
    AndroidUeventdDeviceRule,
    AndroidUeventdFirmwareDirectories,
    AndroidUeventdImport,
    AndroidUeventdSocketRcvbufSize,
    AndroidUeventdSubsystem,
    AndroidUeventdSubsystemOption,
    AndroidUeventdSysfsRule,
)
from treeforge.android.universe.ueventd.requirement import (
    AndroidUniverseUeventdDeviceRuleRequirement,
    AndroidUniverseUeventdFirmwareDirectoriesRequirement,
    AndroidUniverseUeventdImportRequirement,
    AndroidUniverseUeventdRequirement,
    AndroidUniverseUeventdSocketRcvbufRequirement,
    AndroidUniverseUeventdSubsystemRequirement,
    AndroidUniverseUeventdSysfsRuleRequirement,
)
from treeforge.android.universe.ueventd.semantics import (
    AndroidUniverseUeventdPathSemantics,
    AndroidUniverseUeventdPermissionSemantics,
    AndroidUniverseUeventdSocketBufferSemantics,
    AndroidUniverseUeventdSubsystemOptionSemantics,
)


class AndroidUniverseUeventdInterpreter:
    """
    Promote and semantically interpret canonical ueventd Parsing output.

    Import target resolution and cross-source reconciliation intentionally
    remain separate Universe concerns.
    """

    _SIZE_MULTIPLIERS = {
        "": 1,
        "K": 1024,
        "M": 1024 * 1024,
        "G": 1024 * 1024 * 1024,
    }

    def interpret(
        self,
        sources: tuple[
            ParsedAndroidUeventd,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseUeventdRequirement,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                ParsedAndroidUeventd,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedAndroidUeventd instances"
            )

        requirements: list[
            AndroidUniverseUeventdRequirement
        ] = []

        for source in sources:
            for declaration in source.declarations:
                requirements.append(
                    self._interpret_declaration(
                        source,
                        declaration,
                    )
                )

        return tuple(
            requirements
        )

    def _interpret_declaration(
        self,
        source: ParsedAndroidUeventd,
        declaration,
    ) -> AndroidUniverseUeventdRequirement:
        common = {
            "source_path": source.source_path,
            "android_path": source.android_path,
            "source_name": (
                source.filesystem_source.source_name
            ),
            "declaration": declaration,
        }

        if isinstance(
            declaration,
            AndroidUeventdImport,
        ):
            return AndroidUniverseUeventdImportRequirement(
                **common
            )

        if isinstance(
            declaration,
            AndroidUeventdDeviceRule,
        ):
            return AndroidUniverseUeventdDeviceRuleRequirement(
                **common,
                path_semantics=(
                    self._interpret_path(
                        declaration.path
                    )
                ),
                permission_semantics=(
                    self._interpret_permission(
                        mode=declaration.mode,
                        user=declaration.user,
                        group=declaration.group,
                    )
                ),
            )

        if isinstance(
            declaration,
            AndroidUeventdSysfsRule,
        ):
            return AndroidUniverseUeventdSysfsRuleRequirement(
                **common,
                path_semantics=(
                    self._interpret_path(
                        declaration.path
                    )
                ),
                permission_semantics=(
                    self._interpret_permission(
                        mode=declaration.mode,
                        user=declaration.user,
                        group=declaration.group,
                    )
                ),
            )

        if isinstance(
            declaration,
            AndroidUeventdSubsystem,
        ):
            return AndroidUniverseUeventdSubsystemRequirement(
                **common,
                option_semantics=tuple(
                    self._interpret_subsystem_option(
                        option
                    )
                    for option in declaration.options
                ),
            )

        if isinstance(
            declaration,
            AndroidUeventdFirmwareDirectories,
        ):
            return (
                AndroidUniverseUeventdFirmwareDirectoriesRequirement(
                    **common
                )
            )

        if isinstance(
            declaration,
            AndroidUeventdSocketRcvbufSize,
        ):
            return AndroidUniverseUeventdSocketRcvbufRequirement(
                **common,
                semantics=(
                    self._interpret_socket_buffer(
                        declaration.size
                    )
                ),
            )

        raise TypeError(
            "unsupported Android ueventd declaration: "
            f"{type(declaration).__name__}"
        )

    @staticmethod
    def _interpret_path(
        expression: str,
    ) -> AndroidUniverseUeventdPathSemantics:
        return AndroidUniverseUeventdPathSemantics(
            expression=expression,
            has_wildcards=any(
                marker in expression
                for marker in (
                    "*",
                    "?",
                    "[",
                )
            ),
        )

    @staticmethod
    def _interpret_permission(
        *,
        mode: str,
        user: str,
        group: str,
    ) -> AndroidUniverseUeventdPermissionSemantics:
        return AndroidUniverseUeventdPermissionSemantics(
            literal_mode=mode,
            mode=int(
                mode,
                8,
            ),
            user=user,
            group=group,
        )

    @staticmethod
    def _interpret_subsystem_option(
        option: AndroidUeventdSubsystemOption,
    ) -> AndroidUniverseUeventdSubsystemOptionSemantics:
        if option.name == "devname":
            return AndroidUniverseUeventdSubsystemOptionSemantics(
                option=option,
                interpreted=True,
                devname_strategy=option.value,
            )

        if option.name == "dirname":
            return AndroidUniverseUeventdSubsystemOptionSemantics(
                option=option,
                interpreted=True,
                dirname=PurePosixPath(
                    option.value
                ),
            )

        return AndroidUniverseUeventdSubsystemOptionSemantics(
            option=option,
            interpreted=False,
        )

    def _interpret_socket_buffer(
        self,
        literal: str,
    ) -> AndroidUniverseUeventdSocketBufferSemantics:
        value = literal.strip()

        if not value:
            raise ValueError(
                "uevent socket receive-buffer size must not be empty"
            )

        suffix = (
            value[-1].upper()
            if value[-1].isalpha()
            else ""
        )

        numeric = (
            value[:-1]
            if suffix
            else value
        )

        if suffix not in self._SIZE_MULTIPLIERS:
            raise ValueError(
                "unsupported uevent socket receive-buffer "
                f"size suffix: {suffix!r}"
            )

        size_bytes = (
            int(
                numeric,
                10,
            )
            * self._SIZE_MULTIPLIERS[
                suffix
            ]
        )

        return AndroidUniverseUeventdSocketBufferSemantics(
            literal_size=literal,
            size_bytes=size_bytes,
        )