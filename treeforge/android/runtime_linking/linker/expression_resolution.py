"""
Android linkerconfig variable expansion for Runtime Linking.

This reproduces linkerconfig's library-list variable-loading semantics from
canonical Android Device Universe native-library policy objects plus the
already-selected generated runtime inputs.

It does not read factory files directly and does not perform Section::Resolve().
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.runtime_linking.linker.expression import (
    AndroidRuntimeLinkerLibraryExpression,
)
from treeforge.android.runtime_linking.linker.generated_configuration import (
    AndroidUniverseLinkerGeneratedConfigurationInputs,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
    AndroidUniverseLinkerNativeLibraryPolicyKind,
)


class AndroidRuntimeLinkerVariableStatus(
    StrEnum
):
    DEFINED = "defined"
    UNDEFINED = "undefined"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerVariableValue:
    """
    One linkerconfig Variables entry.

    ``libraries`` is already normalized to Android librarylistloader ordering:
    unique names in lexicographic order.
    """

    name: str
    status: AndroidRuntimeLinkerVariableStatus

    libraries: tuple[
        str,
        ...,
    ] = ()

    sources: tuple[
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.name,
                str,
            )
            or not self.name
        ):
            raise ValueError(
                "name must be a non-empty string"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerVariableStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if not isinstance(
            self.libraries,
            tuple,
        ):
            raise TypeError(
                "libraries must be a tuple"
            )

        if not all(
            isinstance(
                library,
                str,
            )
            and library
            for library
            in self.libraries
        ):
            raise ValueError(
                "libraries must contain only non-empty strings"
            )

        if self.libraries != tuple(
            sorted(
                set(
                    self.libraries
                )
            )
        ):
            raise ValueError(
                "libraries must be unique and lexicographically ordered"
            )

        if not isinstance(
            self.sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
            )
            for source
            in self.sources
        ):
            raise TypeError(
                "sources contains invalid native-library semantics"
            )

        if (
            self.status
            is AndroidRuntimeLinkerVariableStatus.UNDEFINED
            and (
                self.libraries
                or self.sources
            )
        ):
            raise ValueError(
                "undefined variable cannot carry libraries or sources"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerVariableEnvironment:
    """
    Complete known linkerconfig variable environment for one generated
    runtime configuration.
    """

    inputs: AndroidUniverseLinkerGeneratedConfigurationInputs

    variables: tuple[
        AndroidRuntimeLinkerVariableValue,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.inputs,
            AndroidUniverseLinkerGeneratedConfigurationInputs,
        ):
            raise TypeError(
                "inputs has invalid type"
            )

        if not isinstance(
            self.variables,
            tuple,
        ):
            raise TypeError(
                "variables must be a tuple"
            )

        if not all(
            isinstance(
                variable,
                AndroidRuntimeLinkerVariableValue,
            )
            for variable
            in self.variables
        ):
            raise TypeError(
                "variables contains invalid values"
            )

        names = tuple(
            variable.name
            for variable
            in self.variables
        )

        if len(
            names
        ) != len(
            set(
                names
            )
        ):
            raise ValueError(
                "variable environment contains duplicate names"
            )

    def get(
        self,
        name: str,
    ) -> AndroidRuntimeLinkerVariableValue | None:
        for variable in self.variables:
            if variable.name == name:
                return variable

        return None


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerResolvedLibraryExpression:
    """
    Resolution of one typed linker library expression.

    Literal expressions always resolve to their literal value, including
    provider aliases such as ``:vndk``.

    Variable expressions resolve from the environment when defined. If the
    variable is undefined and carries an Android fallback, the fallback is
    split using linkerconfig's colon-separated library-list convention.
    """

    expression: AndroidRuntimeLinkerLibraryExpression

    libraries: tuple[
        str,
        ...,
    ]

    used_fallback: bool

    unresolved_variable: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.expression,
            AndroidRuntimeLinkerLibraryExpression,
        ):
            raise TypeError(
                "expression has invalid type"
            )

        if not isinstance(
            self.libraries,
            tuple,
        ):
            raise TypeError(
                "libraries must be a tuple"
            )

        if not isinstance(
            self.used_fallback,
            bool,
        ):
            raise TypeError(
                "used_fallback must be a bool"
            )

        if (
            self.unresolved_variable is not None
            and (
                not isinstance(
                    self.unresolved_variable,
                    str,
                )
                or not self.unresolved_variable
            )
        ):
            raise ValueError(
                "unresolved_variable must be a non-empty string or None"
            )

        if (
            self.unresolved_variable is not None
            and self.libraries
        ):
            raise ValueError(
                "unresolved variable cannot claim resolved libraries"
            )


class AndroidRuntimeLinkerVariableEnvironmentBuilder:
    """
    Reproduce generator/librarylistloader.cc + variableloader.cc semantics
    from canonical Universe native-library policies.
    """

    @staticmethod
    def _normalized(
        values,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            sorted(
                set(
                    values
                )
            )
        )

    @classmethod
    def _libraries(
        cls,
        configuration: (
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics
            | None
        ),
    ) -> tuple[
        str,
        ...,
    ]:
        if configuration is None:
            return ()

        return cls._normalized(
            declaration.library_name
            for declaration
            in configuration.declarations
        )

    @classmethod
    def _public_libraries(
        cls,
        configuration: (
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics
            | None
        ),
        private_configuration: (
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics
            | None
        ),
    ) -> tuple[
        str,
        ...,
    ]:
        # Android: unavailable primary file => empty.
        if configuration is None:
            return ()

        libraries = set(
            cls._libraries(
                configuration
            )
        )

        # Android: unavailable private file => all primary libraries public.
        if private_configuration is None:
            return cls._normalized(
                libraries
            )

        private = set(
            cls._libraries(
                private_configuration
            )
        )

        return cls._normalized(
            libraries - private
        )

    @classmethod
    def _private_libraries(
        cls,
        configuration: (
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics
            | None
        ),
        private_configuration: (
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics
            | None
        ),
    ) -> tuple[
        str,
        ...,
    ]:
        # Android returns empty if either file is unavailable.
        if (
            configuration is None
            or private_configuration is None
        ):
            return ()

        libraries = set(
            cls._libraries(
                configuration
            )
        )

        private = set(
            cls._libraries(
                private_configuration
            )
        )

        return cls._normalized(
            libraries & private
        )

    @staticmethod
    def _configuration_version(
        configuration: AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
    ) -> str | None:
        """
        Consume Universe-owned native-library configuration version semantics.
        """

        return configuration.version_token

    @classmethod
    def _select(
        cls,
        *,
        configurations: tuple[
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
            ...,
        ],
        kind: AndroidUniverseLinkerNativeLibraryPolicyKind,
        version: str | None = None,
    ) -> (
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics
        | None
    ):
        candidates = tuple(
            configuration
            for configuration
            in configurations
            if configuration.policy_kind is kind
        )

        if version is not None:
            candidates = tuple(
                configuration
                for configuration
                in candidates
                if (
                    cls._configuration_version(
                        configuration
                    )
                    == version
                )
            )
        else:
            candidates = tuple(
                configuration
                for configuration
                in candidates
                if (
                    cls._configuration_version(
                        configuration
                    )
                    is None
                )
            )

        if len(
            candidates
        ) > 1:
            raise ValueError(
                "multiple canonical native-library configurations match "
                f"{kind.value} version {version!r}"
            )

        return (
            None
            if not candidates
            else candidates[
                0
            ]
        )

    @staticmethod
    def _defined(
        *,
        name: str,
        libraries: tuple[
            str,
            ...,
        ],
        sources=(),
    ) -> AndroidRuntimeLinkerVariableValue:
        return AndroidRuntimeLinkerVariableValue(
            name=name,
            status=(
                AndroidRuntimeLinkerVariableStatus.DEFINED
            ),
            libraries=libraries,
            sources=tuple(
                source
                for source
                in sources
                if source is not None
            ),
        )

    @staticmethod
    def _undefined(
        name: str,
    ) -> AndroidRuntimeLinkerVariableValue:
        return AndroidRuntimeLinkerVariableValue(
            name=name,
            status=(
                AndroidRuntimeLinkerVariableStatus.UNDEFINED
            ),
        )

    @classmethod
    def build(
        cls,
        *,
        inputs: AndroidUniverseLinkerGeneratedConfigurationInputs,
    ) -> AndroidRuntimeLinkerVariableEnvironment:
        configurations = (
            inputs
            .runtime_policy
            .native_library_configurations
        )

        system_llndk = cls._select(
            configurations=configurations,
            kind=(
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .LLNDK
            ),
        )

        sanitizer = cls._select(
            configurations=configurations,
            kind=(
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .SANITIZER
            ),
        )

        core_variant = cls._select(
            configurations=configurations,
            kind=(
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VNDK_CORE_VARIANT
            ),
        )

        values = []

        def add(
            value: AndroidRuntimeLinkerVariableValue,
        ) -> None:
            values.append(
                value
            )

        # Always loaded by LoadLibraryListVariables().
        add(
            cls._defined(
                name="SANITIZER_RUNTIME_LIBRARIES",
                libraries=cls._libraries(
                    sanitizer
                ),
                sources=(
                    sanitizer,
                ),
            )
        )

        add(
            cls._defined(
                name="SANITIZER_LIBRARIES_LLNDK",
                libraries=cls._private_libraries(
                    sanitizer,
                    system_llndk,
                ),
                sources=(
                    sanitizer,
                    system_llndk,
                ),
            )
        )

        for partition, version in (
            (
                "VENDOR",
                inputs.vendor_vndk_loader_version,
            ),
            (
                "PRODUCT",
                inputs.product_vndk_version,
            ),
        ):
            if version is None:
                # Canonical property state itself is unresolved.
                for variable_name in (
                    f"LLNDK_LIBRARIES_{partition}",
                    f"PRIVATE_LLNDK_LIBRARIES_{partition}",
                    f"VNDK_SAMEPROCESS_LIBRARIES_{partition}",
                    f"VNDK_CORE_LIBRARIES_{partition}",
                    f"SANITIZER_DEFAULT_{partition}",
                ):
                    add(
                        cls._undefined(
                            variable_name
                        )
                    )

                continue

            if version == "":
                # LoadVndkLibraryListVariables returns immediately.
                add(
                    cls._undefined(
                        f"VNDK_SAMEPROCESS_LIBRARIES_{partition}"
                    )
                )
                add(
                    cls._undefined(
                        f"VNDK_CORE_LIBRARIES_{partition}"
                    )
                )
                add(
                    cls._undefined(
                        f"SANITIZER_DEFAULT_{partition}"
                    )
                )
                add(
                    cls._undefined(
                        f"PRIVATE_LLNDK_LIBRARIES_{partition}"
                    )
                )

                # LoadLlndkLibraryListVariables uses system LLNDK.
                add(
                    cls._defined(
                        name=(
                            f"LLNDK_LIBRARIES_{partition}"
                        ),
                        libraries=cls._libraries(
                            system_llndk
                        ),
                        sources=(
                            system_llndk,
                        ),
                    )
                )

                continue


            vndk_apex_available = any(
                requirement.matches_vndk_version(version)
                for requirement
                in inputs.vndk_apex_requirements
            )

            if not vndk_apex_available:
                # Both Android loaders return before defining any
                # version-specific variables.
                for variable_name in (
                    f"LLNDK_LIBRARIES_{partition}",
                    f"PRIVATE_LLNDK_LIBRARIES_{partition}",
                    f"VNDK_SAMEPROCESS_LIBRARIES_{partition}",
                    f"VNDK_CORE_LIBRARIES_{partition}",
                    f"SANITIZER_DEFAULT_{partition}",
                ):
                    add(
                        cls._undefined(
                            variable_name
                        )
                    )

                if partition == "VENDOR":
                    add(
                        cls._undefined(
                            "VNDK_USING_CORE_VARIANT_LIBRARIES"
                        )
                    )

                continue

            vndk_sp = cls._select(
                configurations=configurations,
                kind=(
                    AndroidUniverseLinkerNativeLibraryPolicyKind
                    .VNDK_SP
                ),
                version=version,
            )

            vndk_core = cls._select(
                configurations=configurations,
                kind=(
                    AndroidUniverseLinkerNativeLibraryPolicyKind
                    .VNDK_CORE
                ),
                version=version,
            )

            vndk_private = cls._select(
                configurations=configurations,
                kind=(
                    AndroidUniverseLinkerNativeLibraryPolicyKind
                    .VNDK_PRIVATE
                ),
                version=version,
            )

            versioned_llndk = cls._select(
                configurations=configurations,
                kind=(
                    AndroidUniverseLinkerNativeLibraryPolicyKind
                    .LLNDK
                ),
                version=version,
            )

            add(
                cls._defined(
                    name=(
                        f"VNDK_SAMEPROCESS_LIBRARIES_{partition}"
                    ),
                    libraries=cls._public_libraries(
                        vndk_sp,
                        vndk_private,
                    ),
                    sources=(
                        vndk_sp,
                        vndk_private,
                    ),
                )
            )

            add(
                cls._defined(
                    name=(
                        f"VNDK_CORE_LIBRARIES_{partition}"
                    ),
                    libraries=cls._public_libraries(
                        vndk_core,
                        vndk_private,
                    ),
                    sources=(
                        vndk_core,
                        vndk_private,
                    ),
                )
            )

            add(
                cls._defined(
                    name=(
                        f"SANITIZER_DEFAULT_{partition}"
                    ),
                    libraries=cls._public_libraries(
                        sanitizer,
                        vndk_core,
                    ),
                    sources=(
                        sanitizer,
                        vndk_core,
                    ),
                )
            )

            add(
                cls._defined(
                    name=(
                        f"LLNDK_LIBRARIES_{partition}"
                    ),
                    libraries=cls._public_libraries(
                        versioned_llndk,
                        vndk_private,
                    ),
                    sources=(
                        versioned_llndk,
                        vndk_private,
                    ),
                )
            )

            add(
                cls._defined(
                    name=(
                        f"PRIVATE_LLNDK_LIBRARIES_{partition}"
                    ),
                    libraries=cls._private_libraries(
                        versioned_llndk,
                        vndk_private,
                    ),
                    sources=(
                        versioned_llndk,
                        vndk_private,
                    ),
                )
            )

            if partition == "VENDOR":
                add(
                    cls._defined(
                        name=(
                            "VNDK_USING_CORE_VARIANT_LIBRARIES"
                        ),
                        libraries=cls._public_libraries(
                            core_variant,
                            vndk_private,
                        ),
                        sources=(
                            core_variant,
                            vndk_private,
                        ),
                    )
                )

        # If the vendor branch did not create this variable at all, preserve
        # Android Variables::GetValue absence explicitly.
        if not any(
            value.name
            == "VNDK_USING_CORE_VARIANT_LIBRARIES"
            for value
            in values
        ):
            add(
                cls._undefined(
                    "VNDK_USING_CORE_VARIANT_LIBRARIES"
                )
            )

        return AndroidRuntimeLinkerVariableEnvironment(
            inputs=inputs,
            variables=tuple(
                values
            ),
        )


class AndroidRuntimeLinkerExpressionResolver:
    """
    Resolve typed linker library expressions against one variable environment.
    """

    @staticmethod
    def _fallback_libraries(
        fallback: str,
    ) -> tuple[
        str,
        ...,
    ]:
        if not fallback:
            return ()

        # Android library-list variables are colon-joined.
        return tuple(
            library
            for library
            in fallback.split(
                ":"
            )
            if library
        )

    @classmethod
    def resolve(
        cls,
        *,
        expression: AndroidRuntimeLinkerLibraryExpression,
        environment: AndroidRuntimeLinkerVariableEnvironment,
    ) -> AndroidRuntimeLinkerResolvedLibraryExpression:
        if expression.library_name is not None:
            return AndroidRuntimeLinkerResolvedLibraryExpression(
                expression=expression,
                libraries=(
                    expression.library_name,
                ),
                used_fallback=False,
            )

        assert expression.variable is not None

        value = environment.get(
            expression.variable
        )

        if (
            value is not None
            and value.status
            is AndroidRuntimeLinkerVariableStatus.DEFINED
        ):
            return AndroidRuntimeLinkerResolvedLibraryExpression(
                expression=expression,
                libraries=value.libraries,
                used_fallback=False,
            )

        if expression.fallback is not None:
            return AndroidRuntimeLinkerResolvedLibraryExpression(
                expression=expression,
                libraries=cls._fallback_libraries(
                    expression.fallback
                ),
                used_fallback=True,
            )

        return AndroidRuntimeLinkerResolvedLibraryExpression(
            expression=expression,
            libraries=(),
            used_fallback=False,
            unresolved_variable=(
                expression.variable
            ),
        )
