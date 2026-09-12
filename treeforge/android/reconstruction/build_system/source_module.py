from __future__ import annotations

from treeforge.android.reconstruction_ownership.source.build_model import (
    AndroidSourceBuildModule,
)


def android_reconstruction_source_module_id(
    module: AndroidSourceBuildModule,
) -> str:
    """
    Return the canonical Reconstruction payload identity for one exact
    source build-module declaration.

    Reconstruction does not redefine source-module identity. The identifier
    is derived only from AndroidSourceBuildModule.identity_key, whose exact
    source declaration is owned by Reconstruction Ownership.

    This identity is syntax-neutral with respect to eventual Device Tree
    generation. It does not choose product inclusion, source-tree placement,
    or any generated Make/Soong representation.
    """

    if not isinstance(
        module,
        AndroidSourceBuildModule,
    ):
        raise TypeError(
            "module must be an AndroidSourceBuildModule"
        )

    (
        project_path,
        source_path,
        source_line,
        build_system,
        module_name,
    ) = module.identity_key

    return (
        "source-module:"
        f"{project_path}:"
        f"{source_path}:"
        f"{source_line}:"
        f"{build_system}:"
        f"{module_name}"
    )
