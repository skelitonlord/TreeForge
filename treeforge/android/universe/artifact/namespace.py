from __future__ import annotations

from pathlib import PurePosixPath

from treeforge.android.universe.apex import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
)


def apex_names_by_container_identity(
    apex_requirements: tuple[
        AndroidUniverseApexRequirement,
        ...,
    ],
) -> dict[
    int,
    str,
]:
    """
    Map exact canonical APEX container identity to runtime APEX name.

    No filename, host-path, partition-name, or package-path inference occurs.
    """

    if not isinstance(
        apex_requirements,
        tuple,
    ):
        raise TypeError(
            "apex_requirements must be a tuple"
        )

    result = {}

    for requirement in apex_requirements:
        if not isinstance(
            requirement,
            AndroidUniverseApexRequirement,
        ):
            raise TypeError(
                "apex_requirements must contain only "
                "AndroidUniverseApexRequirement instances"
            )

        artifact_id = id(
            requirement.artifact
        )

        existing = result.get(
            artifact_id
        )

        if (
            existing is not None
            and existing != requirement.apex_name
        ):
            raise ValueError(
                "one canonical APEX container identity maps to "
                "multiple runtime APEX names"
            )

        result[
            artifact_id
        ] = requirement.apex_name

    return result


def normalize_android_namespace_path(
    path: PurePosixPath,
) -> PurePosixPath:
    """
    Normalize a PurePosixPath lexically without touching the host
    filesystem.
    """

    parts = []

    for part in path.parts:
        if part in {
            "",
            "/",
            ".",
        }:
            continue

        if part == "..":
            if parts:
                parts.pop()

            continue

        parts.append(
            part
        )

    return PurePosixPath(
        "/",
        *parts,
    )


def metadata_android_namespace_paths(
    *,
    inventory_entry,
    metadata_path: str,
    apex_names_by_container_id: dict[
        int,
        str,
    ],
) -> tuple[
    PurePosixPath,
    ...,
]:
    """
    Project canonical Filesystem Metadata into Android-visible namespace
    paths using the same rules as regular artifact requirements.
    """

    path = PurePosixPath(
        metadata_path
    )

    if not path.is_absolute():
        path = (
            PurePosixPath("/")
            / path
        )

    filesystem_artifact = (
        inventory_entry.artifact
    )

    payload = (
        filesystem_artifact.parent
    )

    container = (
        payload.parent
        if payload is not None
        else None
    )

    if container is not None:
        apex_name = (
            apex_names_by_container_id.get(
                id(
                    container
                )
            )
        )

        if apex_name is not None:
            return (
                (
                    PurePosixPath(
                        "/apex"
                    )
                    / apex_name
                    / path.relative_to(
                        "/"
                    )
                ),
            )

    partition_name = (
        inventory_entry.partition_name
    )

    paths = {
        path,
    }

    if partition_name == "system":
        if (
            path
            != PurePosixPath("/system")
            and PurePosixPath("/system")
            not in path.parents
        ):
            paths.add(
                PurePosixPath("/system")
                / path.relative_to("/")
            )

    elif partition_name:
        partition_root = (
            PurePosixPath(
                f"/{partition_name}"
            )
        )

        if (
            path != partition_root
            and partition_root
            not in path.parents
        ):
            paths.add(
                partition_root
                / path.relative_to("/")
            )

        if partition_name in {
            "product",
            "system_ext",
        }:
            system_partition_root = (
                PurePosixPath(
                    f"/system/{partition_name}"
                )
            )

            if (
                path
                != system_partition_root
                and system_partition_root
                not in path.parents
            ):
                paths.add(
                    system_partition_root
                    / path.relative_to("/")
                )

    return tuple(
        sorted(
            paths,
            key=lambda item: (
                item.as_posix()
            ),
        )
    )


def artifact_android_namespace_paths(
    *,
    requirement: AndroidUniverseArtifactRequirement,
    apex_names_by_container_id: dict[
        int,
        str,
    ],
) -> tuple[
    PurePosixPath,
    ...,
]:
    """
    Project one canonical artifact into Android-visible namespace paths.
    """

    return metadata_android_namespace_paths(
        inventory_entry=(
            requirement.inventory_entry
        ),
        metadata_path=(
            requirement.android_path
        ),
        apex_names_by_container_id=(
            apex_names_by_container_id
        ),
    )


def filesystem_projects_to_android_runtime_namespace(
    *,
    inventory_entry,
    apex_names_by_container_id: dict[
        int,
        str,
    ],
) -> bool:
    """
    Return whether one canonical filesystem participates in the Android
    runtime namespace.

    Canonical APEX payload filesystems explicitly project into /apex.

    Canonical init_boot and vendor_boot CPIO filesystems are first-class
    runtime/source domains and therefore participate directly.

    Other filesystems nested beneath another filesystem Extraction/CPIO root
    are descendant/guest filesystems. Their contents remain canonical but do
    not automatically collide with the containing Android runtime namespace.
    """

    filesystem_artifact = (
        inventory_entry.artifact
    )

    payload = (
        filesystem_artifact.parent
    )

    container = (
        payload.parent
        if payload is not None
        else None
    )

    if (
        container is not None
        and id(
            container
        ) in apex_names_by_container_id
    ):
        return True

    #
    # Preserve the existing canonical boot-ramdisk participation rule without
    # importing INIT-owned source-context concepts into Artifact ownership.
    #
    if (
        filesystem_artifact.operation.value
        == "cpio_extraction"
    ):
        ramdisk_cpio = (
            filesystem_artifact.parent
        )

        ramdisk_component = (
            ramdisk_cpio.parent
            if ramdisk_cpio is not None
            else None
        )

        boot_family = (
            ramdisk_component.parent
            if ramdisk_component is not None
            else None
        )

        if (
            boot_family is not None
            and boot_family.semantic_name
            in {
                "init_boot",
                "vendor_boot",
            }
        ):
            return True

    ancestor = (
        filesystem_artifact.parent
    )

    while ancestor is not None:
        if ancestor.operation.value in {
            "filesystem_extraction",
            "cpio_extraction",
        }:
            return False

        ancestor = (
            ancestor.parent
        )

    return True


def artifact_projects_to_android_runtime_namespace(
    *,
    requirement: AndroidUniverseArtifactRequirement,
    apex_names_by_container_id: dict[
        int,
        str,
    ],
) -> bool:
    """
    Return whether one canonical artifact requirement participates in the
    Android runtime namespace.
    """

    if not isinstance(
        requirement,
        AndroidUniverseArtifactRequirement,
    ):
        raise TypeError(
            "requirement must be an "
            "AndroidUniverseArtifactRequirement"
        )

    return filesystem_projects_to_android_runtime_namespace(
        inventory_entry=(
            requirement.inventory_entry
        ),
        apex_names_by_container_id=(
            apex_names_by_container_id
        ),
    )

