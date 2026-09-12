"""
Typed Runtime Linking library-expression helpers.

Runtime Linking reuses the same linkerconfig expression representation used
by generated configuration so generated and dynamically constructed
namespaces feed Section::Resolve() through one semantic vocabulary.
"""

from treeforge.android.runtime_linking.linker.generated_configuration import (
    AndroidUniverseLinkerGeneratedLibraryExpression,
    AndroidUniverseLinkerGeneratedNamespaceLinkIntent,
)


AndroidRuntimeLinkerLibraryExpression = (
    AndroidUniverseLinkerGeneratedLibraryExpression
)

AndroidRuntimeLinkerNamespaceLinkIntent = (
    AndroidUniverseLinkerGeneratedNamespaceLinkIntent
)


def literal_library(
    library_name: str,
) -> AndroidRuntimeLinkerLibraryExpression:
    return AndroidRuntimeLinkerLibraryExpression(
        library_name=library_name,
    )


def variable_library(
    variable: str,
    fallback: str | None = None,
) -> AndroidRuntimeLinkerLibraryExpression:
    return AndroidRuntimeLinkerLibraryExpression(
        variable=variable,
        fallback=fallback,
    )


def namespace_link_intent(
    *,
    target_namespace: str,
    shared_libraries: tuple[
        AndroidRuntimeLinkerLibraryExpression,
        ...,
    ] = (),
    allow_all_shared_libs: bool = False,
) -> AndroidRuntimeLinkerNamespaceLinkIntent:
    return AndroidRuntimeLinkerNamespaceLinkIntent(
        target_namespace=target_namespace,
        shared_libraries=shared_libraries,
        allow_all_shared_libs=allow_all_shared_libs,
    )
