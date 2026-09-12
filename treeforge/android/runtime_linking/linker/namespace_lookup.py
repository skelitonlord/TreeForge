from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.runtime_linking.linker.effective_configuration import (
    AndroidRuntimeLinkerEffectiveNamespace,
)
from treeforge.android.runtime_linking.linker.expression_resolution import (
    AndroidRuntimeLinkerExpressionResolver,
    AndroidRuntimeLinkerVariableEnvironment,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerNamespaceLookupPolicy:
    """
    Effective filesystem-lookup policy for one linker namespace.

    This is a generic adapter over the three Runtime Linking namespace origins:

    - generated BASE namespace;
    - directly constructed namespace;
    - injected APEX namespace.

    It preserves effective search-path order and the resolved namespace-local
    allowed-library restriction.

    It deliberately excludes permitted_paths. Normal DT_NEEDED lookup uses
    namespace search paths; permitted paths govern path accessibility rather
    than ordinary SONAME search.
    """

    namespace: AndroidRuntimeLinkerEffectiveNamespace

    bitness: int

    search_paths: tuple[
        PurePosixPath,
        ...,
    ]

    allowed_libraries: tuple[
        str,
        ...,
    ]

    has_allowed_library_restriction: bool

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.namespace,
            AndroidRuntimeLinkerEffectiveNamespace,
        ):
            raise TypeError(
                "namespace must be an "
                "AndroidRuntimeLinkerEffectiveNamespace"
            )

        if self.bitness not in {
            32,
            64,
        }:
            raise ValueError(
                "bitness must be 32 or 64"
            )

        if not isinstance(
            self.search_paths,
            tuple,
        ):
            raise TypeError(
                "search_paths must be a tuple"
            )

        if not all(
            isinstance(
                path,
                PurePosixPath,
            )
            for path
            in self.search_paths
        ):
            raise TypeError(
                "search_paths must contain only PurePosixPath values"
            )

        if not all(
            path.is_absolute()
            for path
            in self.search_paths
        ):
            raise ValueError(
                "effective namespace search paths must be absolute"
            )

        if not isinstance(
            self.allowed_libraries,
            tuple,
        ):
            raise TypeError(
                "allowed_libraries must be a tuple"
            )

        if not all(
            isinstance(
                library,
                str,
            )
            and library
            for library
            in self.allowed_libraries
        ):
            raise ValueError(
                "allowed_libraries must contain only non-empty strings"
            )

        if len(
            self.allowed_libraries
        ) != len(
            set(
                self.allowed_libraries
            )
        ):
            raise ValueError(
                "allowed_libraries must be unique"
            )

        if not isinstance(
            self.has_allowed_library_restriction,
            bool,
        ):
            raise TypeError(
                "has_allowed_library_restriction must be a bool"
            )

        if (
            not self.has_allowed_library_restriction
            and self.allowed_libraries
        ):
            raise ValueError(
                "unrestricted lookup policy cannot carry allowed libraries"
            )

    def admits_library(
        self,
        library_name: str,
    ) -> bool:
        """
        Apply the namespace-local allowed-library restriction.

        An empty/nonexistent allowed_libs population means there is no
        namespace-local SONAME restriction.
        """

        if (
            not isinstance(
                library_name,
                str,
            )
            or not library_name
        ):
            raise ValueError(
                "library_name must be a non-empty string"
            )

        if not self.has_allowed_library_restriction:
            return True

        return (
            library_name
            in self.allowed_libraries
        )


class AndroidRuntimeLinkerNamespaceLookupPolicyBuilder:
    """
    Construct effective namespace filesystem lookup policy.

    Android linkerconfig's ${LIB} placeholder is expanded from the requesting
    ELF's exact bitness. No partition, device, Android-version, or APEX-root
    knowledge is synthesized here.
    """

    @staticmethod
    def _expand_lib(
        value: str,
        *,
        bitness: int,
    ) -> PurePosixPath:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "namespace search path must be a string"
            )

        if not value:
            raise ValueError(
                "namespace search path must not be empty"
            )

        if bitness == 64:
            library_directory = "lib64"

        elif bitness == 32:
            library_directory = "lib"

        else:
            raise ValueError(
                "bitness must be 32 or 64"
            )

        expanded = value.replace(
            "${LIB}",
            library_directory,
        )

        path = PurePosixPath(
            expanded
        )

        if not path.is_absolute():
            raise ValueError(
                "effective namespace search path must be absolute "
                f"after variable expansion: {expanded!r}"
            )

        return path

    @classmethod
    def _generated_search_paths(
        cls,
        *,
        namespace,
        bitness: int,
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        values = []

        for expression in namespace.search_paths:
            if expression.path is None:
                raise ValueError(
                    "DT_NEEDED lookup cannot consume an unresolved "
                    "generated namespace search path: "
                    f"namespace={namespace.name!r}, "
                    f"variable={expression.variable!r}"
                )

            values.append(
                cls._expand_lib(
                    expression.path.as_posix(),
                    bitness=bitness,
                )
            )

        return tuple(
            values
        )

    @classmethod
    def _string_search_paths(
        cls,
        *,
        values: tuple[
            str,
            ...,
        ],
        bitness: int,
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        return tuple(
            cls._expand_lib(
                value,
                bitness=bitness,
            )
            for value
            in values
        )

    @staticmethod
    def _generated_allowed_libraries(
        *,
        namespace,
        environment: AndroidRuntimeLinkerVariableEnvironment,
    ) -> tuple[
        str,
        ...,
    ]:
        libraries = []

        for expression in namespace.allowed_libs:
            resolved = (
                AndroidRuntimeLinkerExpressionResolver
                .resolve(
                    expression=expression,
                    environment=environment,
                )
            )

            if not resolved.resolved:
                raise ValueError(
                    "DT_NEEDED lookup cannot consume unresolved "
                    "allowed_libs expression: "
                    f"namespace={namespace.name!r}, "
                    f"expression={expression!r}"
                )

            for library in resolved.libraries:
                if library in libraries:
                    continue

                libraries.append(
                    library
                )

        return tuple(
            libraries
        )

    @classmethod
    def build(
        cls,
        *,
        namespace: AndroidRuntimeLinkerEffectiveNamespace,
        bitness: int,
        environment: AndroidRuntimeLinkerVariableEnvironment,
    ) -> AndroidRuntimeLinkerNamespaceLookupPolicy:
        if not isinstance(
            namespace,
            AndroidRuntimeLinkerEffectiveNamespace,
        ):
            raise TypeError(
                "namespace must be an "
                "AndroidRuntimeLinkerEffectiveNamespace"
            )

        if not isinstance(
            environment,
            AndroidRuntimeLinkerVariableEnvironment,
        ):
            raise TypeError(
                "environment must be an "
                "AndroidRuntimeLinkerVariableEnvironment"
            )

        if namespace.generated_namespace is not None:
            generated = (
                namespace.generated_namespace
            )

            search_paths = (
                cls._generated_search_paths(
                    namespace=generated,
                    bitness=bitness,
                )
            )

            # Bionic applies namespace-local allowed_libs only to
            # isolated namespaces. A non-isolated namespace remains
            # unrestricted even if linkerconfig carries an allowed_libs
            # population for that namespace.
            has_allowed_library_restriction = (
                generated.is_isolated
                and bool(
                    generated.allowed_libs
                )
            )

            allowed_libraries = (
                cls._generated_allowed_libraries(
                    namespace=generated,
                    environment=environment,
                )
                if has_allowed_library_restriction
                else ()
            )

        elif namespace.constructed_namespace is not None:
            constructed = (
                namespace.constructed_namespace
            )

            search_paths = (
                cls._string_search_paths(
                    values=constructed.search_paths,
                    bitness=bitness,
                )
            )

            allowed_libraries = ()
            has_allowed_library_restriction = False

        elif namespace.apex_provider is not None:
            search_paths = (
                cls._string_search_paths(
                    values=namespace.apex_search_paths,
                    bitness=bitness,
                )
            )

            allowed_libraries = ()
            has_allowed_library_restriction = False

        else:
            raise AssertionError(
                "effective namespace has no primary origin"
            )

        if len(
            search_paths
        ) != len(
            tuple(
                dict.fromkeys(
                    search_paths
                )
            )
        ):
            raise ValueError(
                "effective namespace contains duplicate search paths: "
                f"namespace={namespace.name!r}, "
                f"bitness={bitness}"
            )

        return (
            AndroidRuntimeLinkerNamespaceLookupPolicy(
                namespace=namespace,
                bitness=bitness,
                search_paths=search_paths,
                allowed_libraries=allowed_libraries,
                has_allowed_library_restriction=(
                    has_allowed_library_restriction
                ),
            )
        )
