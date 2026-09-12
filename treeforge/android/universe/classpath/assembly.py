from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.extraction import (
    ExtractionOperation,
)
from treeforge.android.parsing.classpath import (
    AndroidClasspathKind,
)
from treeforge.android.universe.apex import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathEffectiveEntry,
    AndroidUniverseClasspathFragmentKind,
    AndroidUniverseClasspathJarApplicability,
    AndroidUniverseClasspathJarApplicabilityStatus,
    AndroidUniverseClasspathJarRequirement,
    AndroidUniverseEffectiveClasspath,
)


@dataclass(
    frozen=True,
    slots=True,
)
class _ResolvedClasspathFragment:
    """
    Internal canonical runtime identity for one classpaths.proto fragment.
    """

    configuration_id: int
    kind: AndroidUniverseClasspathFragmentKind
    runtime_path: str
    apex_name: str | None


class AndroidUniverseClasspathEffectiveAssembler:
    """
    Assemble effective Android runtime classpaths.

    Ordering follows derive_classpath fragment semantics:

    bootclasspath family:
      1. com.android.art APEX fragment
      2. /system fragment
      3. remaining APEX fragments by runtime path

    systemserverclasspath family:
      1. /system fragment
      2. APEX fragments by runtime path

    Declaration order inside each fragment remains exactly as Parsing
    preserved it.

    APEX ownership is resolved only through exact Extraction artifact identity
    against canonical AndroidUniverseApexRequirement entries.
    """

    _BOOT_KINDS = {
        AndroidClasspathKind.BOOTCLASSPATH,
        AndroidClasspathKind.DEX2OATBOOTCLASSPATH,
    }

    _SYSTEMSERVER_KINDS = {
        AndroidClasspathKind.SYSTEMSERVERCLASSPATH,
        AndroidClasspathKind.STANDALONE_SYSTEMSERVER_JARS,
    }

    _KNOWN_EFFECTIVE_KINDS = (
        AndroidClasspathKind.BOOTCLASSPATH,
        AndroidClasspathKind.DEX2OATBOOTCLASSPATH,
        AndroidClasspathKind.SYSTEMSERVERCLASSPATH,
        AndroidClasspathKind.STANDALONE_SYSTEMSERVER_JARS,
    )

    def assemble(
        self,
        *,
        requirements: tuple[
            AndroidUniverseClasspathJarRequirement,
            ...,
        ],
        applicability: tuple[
            AndroidUniverseClasspathJarApplicability,
            ...,
        ],
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> tuple[
        tuple[
            AndroidUniverseEffectiveClasspath,
            ...,
        ],
        tuple[
            AndroidUniverseClasspathJarRequirement,
            ...,
        ],
    ]:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        if not isinstance(
            applicability,
            tuple,
        ):
            raise TypeError(
                "applicability must be a tuple"
            )

        if len(
            requirements
        ) != len(
            applicability
        ):
            raise ValueError(
                "applicability must cover every Classpath requirement"
            )

        for requirement, result in zip(
            requirements,
            applicability,
            strict=True,
        ):
            if result.requirement is not requirement:
                raise ValueError(
                    "applicability must preserve exact requirement "
                    "identity and ordering"
                )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "apex_requirements must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseApexRequirement,
            )
            for value in apex_requirements
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        fragment_cache: dict[
            int,
            _ResolvedClasspathFragment | None,
        ] = {}

        unresolved: list[
            AndroidUniverseClasspathJarRequirement
        ] = []

        active_known: list[
            tuple[
                AndroidUniverseClasspathJarRequirement,
                AndroidUniverseClasspathJarApplicability,
                _ResolvedClasspathFragment,
            ]
        ] = []

        for requirement, result in zip(
            requirements,
            applicability,
            strict=True,
        ):
            if (
                result.status
                is AndroidUniverseClasspathJarApplicabilityStatus
                .INAPPLICABLE
            ):
                continue

            if (
                result.status
                is AndroidUniverseClasspathJarApplicabilityStatus
                .UNRESOLVED
            ):
                unresolved.append(
                    requirement
                )
                continue

            kind = requirement.known_classpath

            if (
                kind is None
                or kind is AndroidClasspathKind.UNKNOWN
            ):
                unresolved.append(
                    requirement
                )
                continue

            configuration_id = id(
                requirement.configuration
            )

            if configuration_id not in fragment_cache:
                fragment_cache[
                    configuration_id
                ] = self._resolve_fragment(
                    requirement=requirement,
                    apex_requirements=apex_requirements,
                )

            fragment = fragment_cache[
                configuration_id
            ]

            if fragment is None:
                unresolved.append(
                    requirement
                )
                continue

            active_known.append(
                (
                    requirement,
                    result,
                    fragment,
                )
            )

        effective = tuple(
            self._assemble_kind(
                classpath=kind,
                population=tuple(
                    value
                    for value in active_known
                    if value[0].known_classpath is kind
                ),
            )
            for kind in self._KNOWN_EFFECTIVE_KINDS
        )

        return (
            effective,
            tuple(
                unresolved
            ),
        )

    def _resolve_fragment(
        self,
        *,
        requirement: AndroidUniverseClasspathJarRequirement,
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
    ) -> _ResolvedClasspathFragment | None:
        configuration = (
            requirement.configuration
        )

        source = configuration.source

        filesystem_artifact = (
            source.filesystem_source.artifact
        )

        payload = (
            filesystem_artifact.parent
        )

        if (
            payload is not None
            and payload.operation
            is ExtractionOperation.APEX_CONTAINER_EXTRACTION
            and payload.semantic_name == "apex_payload"
        ):
            container = payload.parent

            if container is None:
                return None

            matches = tuple(
                apex
                for apex in apex_requirements
                if apex.artifact is container
            )

            if len(
                matches
            ) != 1:
                return None

            apex = matches[0]

            fragment_name = (
                source.android_path.name
            )

            if fragment_name not in {
                "bootclasspath.pb",
                "systemserverclasspath.pb",
            }:
                return None

            runtime_path = (
                f"/apex/{apex.apex_name}"
                f"/etc/classpaths/{fragment_name}"
            )

            return _ResolvedClasspathFragment(
                configuration_id=id(
                    configuration
                ),
                kind=(
                    AndroidUniverseClasspathFragmentKind
                    .APEX
                ),
                runtime_path=runtime_path,
                apex_name=apex.apex_name,
            )

        #
        # Non-APEX classpath fragments are accepted only when Parsing has
        # already projected the exact canonical /system runtime path.
        #
        android_path = (
            source.android_path.as_posix()
        )

        if android_path in {
            "/system/etc/classpaths/bootclasspath.pb",
            "/system/etc/classpaths/systemserverclasspath.pb",
        }:
            return _ResolvedClasspathFragment(
                configuration_id=id(
                    configuration
                ),
                kind=(
                    AndroidUniverseClasspathFragmentKind
                    .SYSTEM
                ),
                runtime_path=android_path,
                apex_name=None,
            )

        return None

    def _assemble_kind(
        self,
        *,
        classpath: AndroidClasspathKind,
        population: tuple[
            tuple[
                AndroidUniverseClasspathJarRequirement,
                AndroidUniverseClasspathJarApplicability,
                _ResolvedClasspathFragment,
            ],
            ...,
        ],
    ) -> AndroidUniverseEffectiveClasspath:
        fragment_groups: dict[
            int,
            list[
                tuple[
                    AndroidUniverseClasspathJarRequirement,
                    AndroidUniverseClasspathJarApplicability,
                    _ResolvedClasspathFragment,
                ]
            ],
        ] = {}

        for value in population:
            fragment_groups.setdefault(
                value[2].configuration_id,
                [],
            ).append(
                value
            )

        ordered_groups = tuple(
            sorted(
                fragment_groups.values(),
                key=lambda group: (
                    self._fragment_order_key(
                        classpath=classpath,
                        fragment=group[0][2],
                    )
                ),
            )
        )

        entries: list[
            AndroidUniverseClasspathEffectiveEntry
        ] = []

        for fragment_index, group in enumerate(
            ordered_groups
        ):
            #
            # requirements were originally emitted in canonical Parsing
            # declaration order, and filtering above preserves that order.
            #
            for requirement, result, fragment in group:
                entries.append(
                    AndroidUniverseClasspathEffectiveEntry(
                        requirement=requirement,
                        applicability=result,
                        fragment_kind=fragment.kind,
                        runtime_fragment_path=(
                            fragment.runtime_path
                        ),
                        fragment_index=fragment_index,
                        classpath_index=len(
                            entries
                        ),
                    )
                )

        return AndroidUniverseEffectiveClasspath(
            classpath=classpath,
            entries=tuple(
                entries
            ),
        )

    def _fragment_order_key(
        self,
        *,
        classpath: AndroidClasspathKind,
        fragment: _ResolvedClasspathFragment,
    ) -> tuple[
        int,
        str,
    ]:
        if classpath in self._BOOT_KINDS:
            if (
                fragment.kind
                is AndroidUniverseClasspathFragmentKind.APEX
                and fragment.apex_name
                == "com.android.art"
            ):
                return (
                    0,
                    fragment.runtime_path,
                )

            if (
                fragment.kind
                is AndroidUniverseClasspathFragmentKind.SYSTEM
            ):
                return (
                    1,
                    fragment.runtime_path,
                )

            return (
                2,
                fragment.runtime_path,
            )

        if classpath in self._SYSTEMSERVER_KINDS:
            if (
                fragment.kind
                is AndroidUniverseClasspathFragmentKind.SYSTEM
            ):
                return (
                    0,
                    fragment.runtime_path,
                )

            return (
                1,
                fragment.runtime_path,
            )

        raise ValueError(
            "unsupported effective Classpath kind"
        )
