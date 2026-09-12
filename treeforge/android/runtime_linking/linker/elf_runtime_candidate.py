from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.runtime_linking.relationships.model import (
    AndroidUniverseLinkerApexActiveRuntimePath,
)
from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.universe.relationships.model import (
    AndroidUniverseLinkerElfConfigurationScope,
    AndroidUniverseLinkerElfContext,
    AndroidUniverseLinkerElfRuntimeFilesystemDisposition,
    AndroidUniverseRelationshipStatus,
)


class AndroidRuntimeLinkerElfRuntimeCandidateStatus(
    StrEnum,
):
    """
    Runtime-path candidacy of one exact canonical ELF requirement.

    ACTIVE means Runtime Linking has an exact client-visible runtime path.

    INAPPLICABLE means the canonical ELF intentionally has no Android
    filesystem path, such as an embedded extraction-only ELF.

    AMBIGUOUS and UNRESOLVED preserve upstream runtime-context or active-APEX
    uncertainty without guessing.
    """

    ACTIVE = "active"
    INAPPLICABLE = "inapplicable"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidRuntimeLinkerElfRuntimeCandidate:
    """
    Runtime-path candidate for one exact canonical ELF requirement.

    This model preserves physical ELF identity and canonical filesystem alias
    evidence while projecting those paths into the already-selected Android
    runtime context.

    It does not:
    - construct linker namespaces;
    - choose a DT_NEEDED provider;
    - treat DT_SONAME as a filesystem alias;
    - infer source-tree ownership;
    - create Reconstruction work.
    """

    elf_requirement: AndroidUniverseElfRequirement
    linker_elf_context: AndroidUniverseLinkerElfContext

    physical_android_path: PurePosixPath | None
    runtime_path: PurePosixPath | None

    physical_basename: str | None
    soname: str | None
    bitness: int

    runtime_alias_paths: tuple[
        PurePosixPath,
        ...,
    ]

    active_apex_runtime_path: (
        AndroidUniverseLinkerApexActiveRuntimePath
        | None
    )

    status: AndroidRuntimeLinkerElfRuntimeCandidateStatus
    reason: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.elf_requirement,
            AndroidUniverseElfRequirement,
        ):
            raise TypeError(
                "elf_requirement must be an "
                "AndroidUniverseElfRequirement"
            )

        if not isinstance(
            self.linker_elf_context,
            AndroidUniverseLinkerElfContext,
        ):
            raise TypeError(
                "linker_elf_context must be an "
                "AndroidUniverseLinkerElfContext"
            )

        if (
            self.linker_elf_context.elf_requirement
            is not self.elf_requirement
        ):
            raise ValueError(
                "linker_elf_context must preserve exact ELF "
                "requirement identity"
            )

        if (
            self.physical_android_path
            is not None
            and not isinstance(
                self.physical_android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "physical_android_path must be a "
                "PurePosixPath or None"
            )

        if (
            self.runtime_path
            is not None
            and not isinstance(
                self.runtime_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "runtime_path must be a PurePosixPath or None"
            )

        for name, value in (
            (
                "physical_android_path",
                self.physical_android_path,
            ),
            (
                "runtime_path",
                self.runtime_path,
            ),
        ):
            if (
                value is not None
                and not value.is_absolute()
            ):
                raise ValueError(
                    f"{name} must be absolute"
                )

        if (
            self.physical_basename
            is not None
            and (
                not isinstance(
                    self.physical_basename,
                    str,
                )
                or not self.physical_basename
            )
        ):
            raise ValueError(
                "physical_basename must be a non-empty "
                "string or None"
            )

        if (
            self.soname
            is not None
            and (
                not isinstance(
                    self.soname,
                    str,
                )
                or not self.soname
            )
        ):
            raise ValueError(
                "soname must be a non-empty string or None"
            )

        if self.soname != self.elf_requirement.soname:
            raise ValueError(
                "soname must preserve exact parsed ELF SONAME"
            )

        if self.bitness != self.elf_requirement.bitness:
            raise ValueError(
                "bitness must preserve exact parsed ELF bitness"
            )

        if self.bitness not in {
            32,
            64,
        }:
            raise ValueError(
                "bitness must be 32 or 64"
            )

        if not isinstance(
            self.runtime_alias_paths,
            tuple,
        ):
            raise TypeError(
                "runtime_alias_paths must be a tuple"
            )

        if not all(
            isinstance(
                value,
                PurePosixPath,
            )
            and value.is_absolute()
            for value
            in self.runtime_alias_paths
        ):
            raise ValueError(
                "runtime_alias_paths must contain only "
                "absolute PurePosixPath values"
            )

        alias_strings = tuple(
            value.as_posix()
            for value
            in self.runtime_alias_paths
        )

        if alias_strings != tuple(
            sorted(
                alias_strings
            )
        ):
            raise ValueError(
                "runtime_alias_paths must use canonical path order"
            )

        if len(
            alias_strings
        ) != len(
            set(
                alias_strings
            )
        ):
            raise ValueError(
                "runtime_alias_paths must be unique"
            )

        if (
            self.active_apex_runtime_path
            is not None
            and not isinstance(
                self.active_apex_runtime_path,
                AndroidUniverseLinkerApexActiveRuntimePath,
            )
        ):
            raise TypeError(
                "active_apex_runtime_path has invalid type"
            )

        if not isinstance(
            self.status,
            AndroidRuntimeLinkerElfRuntimeCandidateStatus,
        ):
            raise TypeError(
                "status has invalid type"
            )

        if (
            self.status
            is AndroidRuntimeLinkerElfRuntimeCandidateStatus.ACTIVE
        ):
            if (
                self.physical_android_path is None
                or self.runtime_path is None
                or self.physical_basename is None
            ):
                raise ValueError(
                    "ACTIVE ELF runtime candidate requires "
                    "physical and runtime path identity"
                )

            if self.reason is not None:
                raise ValueError(
                    "ACTIVE ELF runtime candidate must not "
                    "carry a reason"
                )

        else:
            if self.runtime_path is not None:
                raise ValueError(
                    "non-ACTIVE ELF runtime candidate must not "
                    "select a runtime path"
                )

            if self.runtime_alias_paths:
                raise ValueError(
                    "non-ACTIVE ELF runtime candidate must not "
                    "select runtime aliases"
                )

            if self.active_apex_runtime_path is not None:
                raise ValueError(
                    "non-ACTIVE ELF runtime candidate must not "
                    "select an active APEX runtime path"
                )

            if self.reason is None:
                raise ValueError(
                    "non-ACTIVE ELF runtime candidate requires "
                    "a reason"
                )

    @property
    def candidate_id(
        self,
    ) -> str:
        return (
            "runtime-linker-elf-candidate:"
            f"{self.elf_requirement.requirement_id}"
        )


class AndroidRuntimeLinkerElfRuntimeCandidateBuilder:
    """
    Project canonical ELF filesystem identity into effective runtime paths.

    All Android-version-specific namespace and search-path behavior remains
    outside this component. APEX runtime roots are consumed from the already
    reconciled Runtime Linking active-APEX result.
    """

    @staticmethod
    def _beneath_runtime_root(
        *,
        active_root: PurePosixPath,
        payload_path: PurePosixPath,
    ) -> PurePosixPath:
        if not active_root.is_absolute():
            raise ValueError(
                "active_root must be absolute"
            )

        if not payload_path.is_absolute():
            raise ValueError(
                "payload_path must be absolute"
            )

        relative_parts = tuple(
            part
            for part
            in payload_path.parts
            if part != "/"
        )

        if not relative_parts:
            raise ValueError(
                "payload_path must identify a file"
            )

        return active_root.joinpath(
            *relative_parts
        )

    @classmethod
    def _apex_local_runtime_alias_paths(
        cls,
        *,
        requirement: AndroidUniverseElfRequirement,
        active_paths_by_apex_identity: dict,
    ) -> tuple[
        PurePosixPath,
        ...,
    ]:
        values = []

        for alias in requirement.apex_local_aliases:
            active_path = (
                active_paths_by_apex_identity
                .get(
                    id(
                        alias.client_apex_requirement
                    )
                )
            )

            if active_path is None:
                continue

            if (
                active_path.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
                or active_path.active_root is None
            ):
                continue

            values.append(
                cls._beneath_runtime_root(
                    active_root=(
                        active_path.active_root
                    ),
                    payload_path=(
                        alias.payload_path
                    ),
                )
            )

        return tuple(
            sorted(
                set(
                    values
                ),
                key=lambda value: (
                    value.as_posix()
                ),
            )
        )

    @classmethod
    def build(
        cls,
        *,
        elf_contexts: tuple[
            AndroidUniverseLinkerElfContext,
            ...,
        ],
        apex_active_runtime_paths: tuple[
            AndroidUniverseLinkerApexActiveRuntimePath,
            ...,
        ],
    ) -> tuple[
        AndroidRuntimeLinkerElfRuntimeCandidate,
        ...,
    ]:
        if not isinstance(
            elf_contexts,
            tuple,
        ):
            raise TypeError(
                "elf_contexts must be a tuple"
            )

        if not isinstance(
            apex_active_runtime_paths,
            tuple,
        ):
            raise TypeError(
                "apex_active_runtime_paths must be a tuple"
            )

        active_paths_by_apex_identity = {
            id(
                value.apex_requirement
            ): value
            for value
            in apex_active_runtime_paths
        }

        if len(
            active_paths_by_apex_identity
        ) != len(
            apex_active_runtime_paths
        ):
            raise ValueError(
                "active APEX runtime paths must preserve one "
                "result per exact APEX requirement"
            )

        values = []

        for context in elf_contexts:
            if not isinstance(
                context,
                AndroidUniverseLinkerElfContext,
            ):
                raise TypeError(
                    "elf_contexts contains an invalid object"
                )

            requirement = (
                context.elf_requirement
            )

            physical_android_path = (
                requirement.android_path
            )

            runtime_filesystem_disposition = (
                context.runtime_filesystem_disposition
            )

            # Universe has already established whether this canonical ELF
            # participates in the post-boot linker filesystem.
            if (
                runtime_filesystem_disposition
                is
                AndroidUniverseLinkerElfRuntimeFilesystemDisposition
                .NO_FILESYSTEM_BACKING
            ):
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=None,
                        runtime_path=None,
                        physical_basename=None,
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .INAPPLICABLE
                        ),
                        reason=(
                            "canonical ELF is extraction-backed and has "
                            "no Android filesystem runtime path"
                        ),
                    )
                )
                continue

            if physical_android_path is None:
                raise ValueError(
                    "filesystem-backed ELF must preserve its "
                    "canonical Android path"
                )

            #
            # CPIO/ramdisk applicability is a canonical Universe conclusion.
            # Runtime Linking consumes that conclusion without reopening
            # Extraction provenance.
            #
            if (
                runtime_filesystem_disposition
                is
                AndroidUniverseLinkerElfRuntimeFilesystemDisposition
                .CPIO_INAPPLICABLE
            ):
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=None,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .INAPPLICABLE
                        ),
                        reason=(
                            "canonical ELF belongs to a CPIO-extracted "
                            "boot/ramdisk filesystem and does not participate "
                            "in the post-boot linkerconfig runtime filesystem"
                        ),
                    )
                )
                continue

            if (
                context.status
                is AndroidUniverseRelationshipStatus.AMBIGUOUS
            ):
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=None,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .AMBIGUOUS
                        ),
                        reason=(
                            "canonical Linker/ELF context is ambiguous"
                        ),
                    )
                )
                continue

            if (
                context.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
            ):
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=None,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            "canonical Linker/ELF context is unresolved"
                        ),
                    )
                )
                continue

            if (
                context.configuration_scope
                is AndroidUniverseLinkerElfConfigurationScope.BASE
            ):
                runtime_path = (
                    physical_android_path
                )

                runtime_alias_paths = tuple(
                    sorted(
                        set(
                            tuple(
                                alias.android_path
                                for alias
                                in requirement.filesystem_aliases
                            )
                            + (
                                cls
                                ._apex_local_runtime_alias_paths(
                                    requirement=(
                                        requirement
                                    ),
                                    active_paths_by_apex_identity=(
                                        active_paths_by_apex_identity
                                    ),
                                )
                            )
                        ),
                        key=lambda value: (
                            value.as_posix()
                        ),
                    )
                )

                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=runtime_path,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(
                            runtime_alias_paths
                        ),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .ACTIVE
                        ),
                    )
                )
                continue

            selected_apex = (
                context.selected_apex_requirement
            )

            if selected_apex is None:
                raise ValueError(
                    "resolved APEX Linker/ELF context must "
                    "preserve exact selected APEX identity"
                )

            active_path = (
                active_paths_by_apex_identity
                .get(
                    id(
                        selected_apex
                    )
                )
            )

            if active_path is None:
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=None,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            "resolved APEX Linker/ELF context has no "
                            "Runtime Linking active-path result"
                        ),
                    )
                )
                continue

            if (
                active_path.status
                is AndroidUniverseRelationshipStatus.AMBIGUOUS
            ):
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=None,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .AMBIGUOUS
                        ),
                        reason=(
                            "active APEX runtime path is ambiguous"
                        ),
                    )
                )
                continue

            if (
                active_path.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
                or active_path.active_root is None
            ):
                values.append(
                    AndroidRuntimeLinkerElfRuntimeCandidate(
                        elf_requirement=requirement,
                        linker_elf_context=context,
                        physical_android_path=(
                            physical_android_path
                        ),
                        runtime_path=None,
                        physical_basename=(
                            physical_android_path.name
                        ),
                        soname=requirement.soname,
                        bitness=requirement.bitness,
                        runtime_alias_paths=(),
                        active_apex_runtime_path=None,
                        status=(
                            AndroidRuntimeLinkerElfRuntimeCandidateStatus
                            .UNRESOLVED
                        ),
                        reason=(
                            active_path.unresolved_reason
                            or "active APEX runtime path is unresolved"
                        ),
                    )
                )
                continue

            runtime_path = (
                cls._beneath_runtime_root(
                    active_root=(
                        active_path.active_root
                    ),
                    payload_path=(
                        physical_android_path
                    ),
                )
            )

            runtime_alias_paths = tuple(
                sorted(
                    set(
                        tuple(
                            (
                                cls._beneath_runtime_root(
                                    active_root=(
                                        active_path.active_root
                                    ),
                                    payload_path=(
                                        alias.android_path
                                    ),
                                )
                                if alias.shares_source_filesystem
                                else alias.android_path
                            )
                            for alias
                            in requirement.filesystem_aliases
                        )
                        + (
                            cls
                            ._apex_local_runtime_alias_paths(
                                requirement=(
                                    requirement
                                ),
                                active_paths_by_apex_identity=(
                                    active_paths_by_apex_identity
                                ),
                            )
                        )
                    ),
                    key=lambda value: (
                        value.as_posix()
                    ),
                )
            )

            values.append(
                AndroidRuntimeLinkerElfRuntimeCandidate(
                    elf_requirement=requirement,
                    linker_elf_context=context,
                    physical_android_path=(
                        physical_android_path
                    ),
                    runtime_path=runtime_path,
                    physical_basename=(
                        physical_android_path.name
                    ),
                    soname=requirement.soname,
                    bitness=requirement.bitness,
                    runtime_alias_paths=(
                        runtime_alias_paths
                    ),
                    active_apex_runtime_path=(
                        active_path
                    ),
                    status=(
                        AndroidRuntimeLinkerElfRuntimeCandidateStatus
                        .ACTIVE
                    ),
                )
            )

        result = tuple(
            values
        )

        if len(
            result
        ) != len(
            elf_contexts
        ):
            raise ValueError(
                "ELF runtime candidate coverage must preserve "
                "one result per Linker/ELF context"
            )

        if not all(
            candidate.linker_elf_context
            is context
            for candidate, context
            in zip(
                result,
                elf_contexts,
                strict=True,
            )
        ):
            raise ValueError(
                "ELF runtime candidates must preserve exact "
                "Linker/ELF context identity and order"
            )

        return result
