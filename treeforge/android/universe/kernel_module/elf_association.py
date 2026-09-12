from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.universe.elf.requirement import (
    AndroidUniverseElfRequirement,
)
from treeforge.android.universe.kernel_module.requirement import (
    AndroidUniverseKernelModuleFileRequirement,
    AndroidUniverseKernelModuleRequirement,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelModuleElfAssociation:
    """
    Exact canonical relationship between one installed kernel-module
    requirement and the canonical ELF requirement representing the same
    physical parsed ELF.

    Parsing object identity is used only inside Universe to establish the
    relationship. Downstream stages consume this association directly and do
    not reopen ParsedAndroidKernelModule / ParsedAndroidElf provenance.
    """

    module_requirement: (
        AndroidUniverseKernelModuleFileRequirement
    )

    elf_requirement: (
        AndroidUniverseElfRequirement
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.module_requirement,
            AndroidUniverseKernelModuleFileRequirement,
        ):
            raise TypeError(
                "module_requirement must be an "
                "AndroidUniverseKernelModuleFileRequirement"
            )

        if not isinstance(
            self.elf_requirement,
            AndroidUniverseElfRequirement,
        ):
            raise TypeError(
                "elf_requirement must be an "
                "AndroidUniverseElfRequirement"
            )

        if (
            self.module_requirement.source.elf
            is not self.elf_requirement.source
        ):
            raise ValueError(
                "kernel-module/ELF association must preserve exact "
                "Parsing ELF identity inside Universe"
            )

    @property
    def association_id(
        self,
    ) -> str:
        return (
            "kernel-module-elf:"
            f"{self.elf_requirement.requirement_id}"
        )


class AndroidUniverseKernelModuleElfAssociationBuilder:
    """
    Promote the exact Parsing kernel-module -> ELF identity relationship into
    a canonical Universe-owned contract.
    """

    @staticmethod
    def build(
        *,
        kernel_module_requirement: (
            AndroidUniverseKernelModuleRequirement
            | None
        ),
        elf_requirements: tuple[
            AndroidUniverseElfRequirement,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseKernelModuleElfAssociation,
        ...,
    ]:
        if not isinstance(
            elf_requirements,
            tuple,
        ) or not all(
            isinstance(
                requirement,
                AndroidUniverseElfRequirement,
            )
            for requirement in elf_requirements
        ):
            raise TypeError(
                "elf_requirements must contain only "
                "AndroidUniverseElfRequirement values"
            )

        if kernel_module_requirement is None:
            return ()

        if not isinstance(
            kernel_module_requirement,
            AndroidUniverseKernelModuleRequirement,
        ):
            raise TypeError(
                "kernel_module_requirement must be an "
                "AndroidUniverseKernelModuleRequirement or None"
            )

        elf_by_parsed_identity = {}

        for requirement in elf_requirements:
            parsed_identity = id(
                requirement.source
            )

            existing = (
                elf_by_parsed_identity.get(
                    parsed_identity
                )
            )

            if (
                existing is not None
                and existing is not requirement
            ):
                raise ValueError(
                    "canonical ELF population contains multiple "
                    "requirements for one exact ParsedAndroidElf"
                )

            elf_by_parsed_identity[
                parsed_identity
            ] = requirement

        associations = []

        for module_requirement in (
            kernel_module_requirement
            .module_requirements
        ):
            elf_requirement = (
                elf_by_parsed_identity.get(
                    id(
                        module_requirement
                        .source
                        .elf
                    )
                )
            )

            if elf_requirement is None:
                raise ValueError(
                    "canonical kernel-module requirement has no exact "
                    "canonical Universe ELF requirement"
                )

            associations.append(
                AndroidUniverseKernelModuleElfAssociation(
                    module_requirement=(
                        module_requirement
                    ),
                    elf_requirement=(
                        elf_requirement
                    ),
                )
            )

        return tuple(
            associations
        )
