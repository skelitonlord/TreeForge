from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from treeforge.android.universe.elf.alias import (
    AndroidUniverseElfFilesystemAlias,
)
from treeforge.android.universe.elf.apex_local_alias import (
    AndroidUniverseElfApexLocalAlias,
)

from treeforge.android.parsing.elf import (
    AndroidElfClass,
    AndroidElfEndianness,
    ParsedAndroidElf,
)

def android_architecture_for_elf_machine(
    machine: str,
) -> str | None:
    """
    Interpret one canonical ELF machine identity as the corresponding
    Android/Soong architecture token.
    """

    if not isinstance(
        machine,
        str,
    ):
        raise TypeError(
            "machine must be a string"
        )

    return {
        "EM_AARCH64": "arm64",
        "EM_ARM": "arm",
        "EM_X86_64": "x86_64",
        "EM_386": "x86",
        "EM_RISCV": "riscv64",
    }.get(
        machine
    )



class AndroidUniverseElfRole(
    StrEnum,
):
    """
    Device-level semantic role of one parsed ELF object.

    This classification is intentionally structural rather than path-based.
    Artifact Universe remains responsible for installed-artifact taxonomy.
    """

    EXECUTABLE = "executable"
    SHARED_OBJECT = "shared_object"
    OTHER = "other"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfDependencyRequirement:
    """
    One DT_NEEDED dependency declared by an exact parsed ELF object.
    """

    source: ParsedAndroidElf
    name: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.name,
            str,
        ):
            raise TypeError(
                "name must be a string"
            )

        if not self.name.strip():
            raise ValueError(
                "name must not be empty"
            )

        if self.name not in self.source.needed:
            raise ValueError(
                "dependency must be declared by source.needed"
            )

    @property
    def requirement_id(self) -> str:
        source_name, source_path = (
            self.source.source.identity_key
        )

        return (
            "elf-needed:"
            f"{source_name}:"
            f"{source_path}:"
            f"{self.name}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfInterpreterRequirement:
    """
    Runtime interpreter required by one exact parsed ELF object.
    """

    source: ParsedAndroidElf
    path: str

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.path,
            str,
        ):
            raise TypeError(
                "path must be a string"
            )

        if not self.path.strip():
            raise ValueError(
                "path must not be empty"
            )

        if self.source.interpreter != self.path:
            raise ValueError(
                "path must match source.interpreter"
            )

    @property
    def requirement_id(self) -> str:
        source_name, source_path = (
            self.source.source.identity_key
        )

        return (
            "elf-interpreter:"
            f"{source_name}:"
            f"{source_path}:"
            f"{self.path}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfSoongBuildTupleRequirement:
    """
    One embedded Soong build-tuple observation from an exact parsed ELF.

    Parsing owns discovery of the literal string. Universe interprets only
    the stable leading structure:

        android_<architecture>_<arch_variant>_<remainder...>

    The remainder is intentionally preserved without guessing whether its
    first token is a CPU variant, linkage mode, sanitizer mode, module
    variant, or another Soong-local build dimension.

    Device-level architecture reconciliation owns any later conclusion.
    """

    source: ParsedAndroidElf
    literal: str
    domain: tuple[
        str,
        ...,
    ] = ()
    architecture: str = ""
    arch_variant: str = ""
    remainder: tuple[
        str,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.domain,
            tuple,
        ):
            raise TypeError(
                "domain must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            and value
            for value in self.domain
        ):
            raise ValueError(
                "domain must contain only non-empty strings"
            )

        for (
            name,
            value,
        ) in (
            (
                "literal",
                self.literal,
            ),
            (
                "architecture",
                self.architecture,
            ),
            (
                "arch_variant",
                self.arch_variant,
            ),
        ):
            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{name} must be a string"
                )

            if not value.strip():
                raise ValueError(
                    f"{name} must not be empty"
                )

        if (
            self.literal
            not in self.source.soong_intermediate_components
        ):
            raise ValueError(
                "literal must be declared by "
                "source.soong_intermediate_components"
            )

        if not isinstance(
            self.remainder,
            tuple,
        ):
            raise TypeError(
                "remainder must be a tuple"
            )

        if not all(
            isinstance(
                value,
                str,
            )
            for value in self.remainder
        ):
            raise TypeError(
                "remainder must contain only strings"
            )

        expected_prefix = (
            "android_"
            + (
                "_".join(
                    self.domain
                )
                + "_"
                if self.domain
                else ""
            )
            + f"{self.architecture}_"
            + f"{self.arch_variant}"
        )

        if not (
            self.literal
            == expected_prefix
            or self.literal.startswith(
                expected_prefix + "_"
            )
        ):
            raise ValueError(
                "interpreted Soong tuple structure "
                "must match literal prefix"
            )

    @property
    def requirement_id(
        self,
    ) -> str:
        (
            source_name,
            source_path,
        ) = self.source.source.identity_key

        return (
            "elf-soong-build-tuple:"
            f"{source_name}:"
            f"{source_path}:"
            f"{self.literal}"
        )


class AndroidUniverseElfSoongBuildTupleDispositionStatus(
    StrEnum,
):
    BUILD_TUPLE = "build_tuple"
    NON_BUILD_TUPLE = "non_build_tuple"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfSoongBuildTupleDisposition:
    """
    Explicit Universe disposition for one exact Parsing Soong-intermediate
    component.

    Every source.soong_intermediate_components literal receives exactly one
    disposition. Universe classifies each literal as a real Android/Soong
    build tuple, a proven non-build-tuple component, or unresolved.
    """

    source: ParsedAndroidElf
    literal: str
    status: AndroidUniverseElfSoongBuildTupleDispositionStatus
    requirement: (
        AndroidUniverseElfSoongBuildTupleRequirement
        | None
    ) = None
    reason: str = ""

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElf"
            )

        if (
            not isinstance(
                self.literal,
                str,
            )
            or not self.literal
        ):
            raise ValueError(
                "literal must be a non-empty string"
            )

        if (
            self.literal
            not in self.source.soong_intermediate_components
        ):
            raise ValueError(
                "literal must belong to source.soong_intermediate_components"
            )

        if not isinstance(
            self.status,
            AndroidUniverseElfSoongBuildTupleDispositionStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseElfSoongBuildTupleDispositionStatus"
            )

        if (
            not isinstance(
                self.reason,
                str,
            )
            or not self.reason.strip()
        ):
            raise ValueError(
                "Soong intermediate-component disposition requires a reason"
            )

        if (
            self.status
            is AndroidUniverseElfSoongBuildTupleDispositionStatus
            .BUILD_TUPLE
        ):
            if not isinstance(
                self.requirement,
                AndroidUniverseElfSoongBuildTupleRequirement,
            ):
                raise ValueError(
                    "build-tuple disposition requires its "
                    "semantic requirement"
                )

            if (
                self.requirement.source
                is not self.source
                or self.requirement.literal
                != self.literal
            ):
                raise ValueError(
                    "build-tuple disposition must retain exact "
                    "source/literal identity"
                )

        elif self.requirement is not None:
            raise ValueError(
                "non-build-tuple and unresolved dispositions "
                "must not carry a semantic requirement"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseElfRequirement:
    """
    Canonical device-level requirement derived from one parsed ELF object.

    Parsing remains authoritative for literal ELF decoding. Universe promotes
    that exact observation into device semantics while preserving the original
    ParsedAndroidElf object as evidence.
    """

    source: ParsedAndroidElf
    role: AndroidUniverseElfRole
    dependencies: tuple[
        AndroidUniverseElfDependencyRequirement,
        ...,
    ] = ()
    interpreter_requirement: (
        AndroidUniverseElfInterpreterRequirement
        | None
    ) = None
    soong_build_tuple_requirements: tuple[
        AndroidUniverseElfSoongBuildTupleRequirement,
        ...,
    ] = ()

    soong_build_tuple_dispositions: tuple[
        AndroidUniverseElfSoongBuildTupleDisposition,
        ...,
    ] = ()

    filesystem_aliases: tuple[
        AndroidUniverseElfFilesystemAlias,
        ...,
    ] = ()

    apex_local_aliases: tuple[
        AndroidUniverseElfApexLocalAlias,
        ...,
    ] = ()

    @property
    def identity_key(
        self,
    ):
        """
        Return the canonical ELF source identity.

        Parsing remains the provenance owner, while downstream stages consume
        this Universe-level identity rather than reopening Parsing models.
        """

        return self.source.source.identity_key

    def owns_dependency(
        self,
        dependency: AndroidUniverseElfDependencyRequirement,
    ) -> bool:
        """
        Whether one canonical DT_NEEDED requirement belongs to this exact ELF.
        """

        if not isinstance(
            dependency,
            AndroidUniverseElfDependencyRequirement,
        ):
            raise TypeError(
                "dependency must be an "
                "AndroidUniverseElfDependencyRequirement"
            )

        return (
            dependency.source
            is self.source
        )

    @property
    def identity_key(
        self,
    ):
        """
        Return the canonical ELF source identity.

        Parsing remains the provenance owner, while downstream stages consume
        this Universe-level identity rather than reopening Parsing models.
        """

        return self.source.source.identity_key

    def owns_dependency(
        self,
        dependency: AndroidUniverseElfDependencyRequirement,
    ) -> bool:
        """
        Whether one canonical DT_NEEDED requirement belongs to this exact ELF.
        """

        if not isinstance(
            dependency,
            AndroidUniverseElfDependencyRequirement,
        ):
            raise TypeError(
                "dependency must be an "
                "AndroidUniverseElfDependencyRequirement"
            )

        return (
            dependency.source
            is self.source
        )

    @property
    def android_path(
        self,
    ) -> PurePosixPath | None:
        """
        Canonical Android-visible physical path, when filesystem-backed.
        """

        return self.source.source.android_path

    @property
    def is_filesystem_backed(
        self,
    ) -> bool:
        return self.source.source.is_filesystem_backed

    @property
    def soname(
        self,
    ) -> str | None:
        return self.source.soname

    @property
    def bitness(
        self,
    ) -> int:
        return self.source.bitness

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidElf,
        ):
            raise TypeError(
                "source must be a ParsedAndroidElf"
            )

        if not isinstance(
            self.role,
            AndroidUniverseElfRole,
        ):
            raise TypeError(
                "role must be an AndroidUniverseElfRole"
            )

        if not isinstance(
            self.filesystem_aliases,
            tuple,
        ):
            raise TypeError(
                "filesystem_aliases must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseElfFilesystemAlias,
            )
            for value
            in self.filesystem_aliases
        ):
            raise TypeError(
                "filesystem_aliases must contain only "
                "AndroidUniverseElfFilesystemAlias values"
            )

        if not all(
            value.source
            is self.source
            for value
            in self.filesystem_aliases
        ):
            raise ValueError(
                "filesystem aliases must preserve exact parsed ELF identity"
            )

        alias_paths = tuple(
            value.android_path.as_posix()
            for value
            in self.filesystem_aliases
        )

        if alias_paths != tuple(
            sorted(
                alias_paths
            )
        ):
            raise ValueError(
                "filesystem aliases must use canonical Android-path order"
            )

        if len(
            alias_paths
        ) != len(
            set(
                alias_paths
            )
        ):
            raise ValueError(
                "filesystem aliases must have unique Android-visible paths"
            )

        if not isinstance(
            self.apex_local_aliases,
            tuple,
        ):
            raise TypeError(
                "apex_local_aliases must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseElfApexLocalAlias,
            )
            for value
            in self.apex_local_aliases
        ):
            raise TypeError(
                "apex_local_aliases must contain only "
                "AndroidUniverseElfApexLocalAlias values"
            )

        if not all(
            value.source is self.source
            for value
            in self.apex_local_aliases
        ):
            raise ValueError(
                "APEX-local aliases must preserve exact "
                "parsed ELF identity"
            )

        apex_alias_keys = tuple(
            (
                value.client_apex_requirement.apex_name,
                value.payload_path.as_posix(),
                value.target_android_path.as_posix(),
            )
            for value
            in self.apex_local_aliases
        )

        if apex_alias_keys != tuple(
            sorted(
                apex_alias_keys
            )
        ):
            raise ValueError(
                "APEX-local aliases must use canonical order"
            )

        if len(
            tuple(
                (
                    id(value.client_apex_requirement),
                    value.payload_path,
                )
                for value
                in self.apex_local_aliases
            )
        ) != len(
            set(
                (
                    id(value.client_apex_requirement),
                    value.payload_path,
                )
                for value
                in self.apex_local_aliases
            )
        ):
            raise ValueError(
                "APEX-local aliases must be unique per exact "
                "client APEX and payload path"
            )

        if not isinstance(
            self.dependencies,
            tuple,
        ):
            raise TypeError(
                "dependencies must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseElfDependencyRequirement,
            )
            for value in self.dependencies
        ):
            raise TypeError(
                "dependencies must contain only "
                "AndroidUniverseElfDependencyRequirement"
            )

        if not all(
            value.source is self.source
            for value in self.dependencies
        ):
            raise ValueError(
                "dependency requirements must preserve exact source identity"
            )

        expected_dependencies = tuple(
            self.source.needed
        )

        actual_dependencies = tuple(
            value.name
            for value in self.dependencies
        )

        if (
            actual_dependencies
            != expected_dependencies
        ):
            raise ValueError(
                "dependencies must exactly preserve source.needed order"
            )

        if (
            self.interpreter_requirement
            is not None
            and not isinstance(
                self.interpreter_requirement,
                AndroidUniverseElfInterpreterRequirement,
            )
        ):
            raise TypeError(
                "interpreter_requirement must be an "
                "AndroidUniverseElfInterpreterRequirement or None"
            )

        if self.source.interpreter is None:
            if self.interpreter_requirement is not None:
                raise ValueError(
                    "ELF without an interpreter cannot have an "
                    "interpreter requirement"
                )
        else:
            if self.interpreter_requirement is None:
                raise ValueError(
                    "ELF interpreter must produce an interpreter requirement"
                )

            if (
                self.interpreter_requirement.source
                is not self.source
            ):
                raise ValueError(
                    "interpreter requirement must preserve exact source identity"
                )

        if not isinstance(
            self.soong_build_tuple_requirements,
            tuple,
        ):
            raise TypeError(
                "soong_build_tuple_requirements "
                "must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseElfSoongBuildTupleRequirement,
            )
            for value
            in self.soong_build_tuple_requirements
        ):
            raise TypeError(
                "soong_build_tuple_requirements must contain "
                "only AndroidUniverseElfSoongBuildTupleRequirement"
            )

        if not all(
            value.source is self.source
            for value
            in self.soong_build_tuple_requirements
        ):
            raise ValueError(
                "Soong build-tuple requirements must preserve "
                "exact source identity"
            )

        source_soong_literals = tuple(
            self.source.soong_intermediate_components
        )

        actual_soong_literals = tuple(
            value.literal
            for value
            in self.soong_build_tuple_requirements
        )

        source_positions = {
            literal: index
            for index, literal
            in enumerate(
                source_soong_literals
            )
        }

        if not all(
            literal in source_positions
            for literal
            in actual_soong_literals
        ):
            raise ValueError(
                "Soong build-tuple requirements must reference "
                "only source.soong_intermediate_components literals"
            )

        actual_positions = tuple(
            source_positions[
                literal
            ]
            for literal
            in actual_soong_literals
        )

        if actual_positions != tuple(
            sorted(
                actual_positions
            )
        ):
            raise ValueError(
                "Soong build-tuple requirements must preserve "
                "source.soong_intermediate_components relative order"
            )

        if not isinstance(
            self.soong_build_tuple_dispositions,
            tuple,
        ):
            raise TypeError(
                "soong_build_tuple_dispositions must be a tuple"
            )

        if not all(
            isinstance(
                disposition,
                AndroidUniverseElfSoongBuildTupleDisposition,
            )
            for disposition
            in self.soong_build_tuple_dispositions
        ):
            raise TypeError(
                "soong_build_tuple_dispositions must contain only "
                "AndroidUniverseElfSoongBuildTupleDisposition values"
            )

        disposition_literals = tuple(
            disposition.literal
            for disposition
            in self.soong_build_tuple_dispositions
        )

        if (
            disposition_literals
            != source_soong_literals
        ):
            raise ValueError(
                "Soong tuple dispositions must cover every "
                "source.soong_intermediate_components literal exactly once "
                "and preserve exact order"
            )

        if not all(
            disposition.source is self.source
            for disposition
            in self.soong_build_tuple_dispositions
        ):
            raise ValueError(
                "Soong tuple dispositions must preserve exact "
                "ParsedAndroidElf identity"
            )

        interpreted_from_dispositions = tuple(
            disposition.requirement
            for disposition
            in self.soong_build_tuple_dispositions
            if disposition.requirement is not None
        )

        if (
            interpreted_from_dispositions
            != self.soong_build_tuple_requirements
        ):
            raise ValueError(
                "build-tuple dispositions must exactly "
                "match soong_build_tuple_requirements"
            )

    @property
    def elf_class(
        self,
    ) -> AndroidElfClass:
        return self.source.elf_class

    @property
    def bitness(
        self,
    ) -> int:
        return self.source.bitness

    @property
    def endianness(
        self,
    ) -> AndroidElfEndianness:
        return self.source.endianness

    @property
    def machine(
        self,
    ) -> str:
        return self.source.machine

    @property
    def elf_type(
        self,
    ) -> str:
        return self.source.elf_type

    @property
    def android_architecture(
        self,
    ) -> str | None:
        """
        Canonical Android/Soong architecture token for this ELF.

        Parsing owns the literal ELF machine identity. Universe owns
        interpretation of that identity into Android architecture
        semantics. Downstream stages must consume this conclusion rather
        than independently reinterpret ELF bitness or machine values.
        """

        return android_architecture_for_elf_machine(
            self.machine
        )

    @property
    def soname(
        self,
    ) -> str | None:
        return self.source.soname

    @property
    def requirement_id(self) -> str:
        source_name, source_path = (
            self.source.source.identity_key
        )

        return (
            "elf:"
            f"{source_name}:"
            f"{source_path}"
        )
