from __future__ import annotations

from treeforge.android.filesystem.inventory import (
    FilesystemMetadataInventory,
)
from treeforge.android.universe.elf.alias import (
    AndroidUniverseElfFilesystemAliasReconciler,
)

from treeforge.android.parsing.elf import (
    AndroidElfParsingResult,
    ParsedAndroidElf,
)

from treeforge.android.universe.elf.requirement import (
    android_architecture_for_elf_machine,
    AndroidUniverseElfDependencyRequirement,
    AndroidUniverseElfInterpreterRequirement,
    AndroidUniverseElfRequirement,
    AndroidUniverseElfRole,
    AndroidUniverseElfSoongBuildTupleRequirement,
    AndroidUniverseElfSoongBuildTupleDisposition,
    AndroidUniverseElfSoongBuildTupleDispositionStatus,
)


class AndroidUniverseElfInterpreter:
    """
    Promote canonical Parsing-stage ELF observations into Universe requirements.

    This interpreter does not reopen or reparse ELF binaries. All literal ELF
    structure remains owned by Parsing.
    """

    def interpret(
        self,
        parsing: AndroidElfParsingResult,
        *,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> tuple[
        AndroidUniverseElfRequirement,
        ...,
    ]:
        if not isinstance(
            parsing,
            AndroidElfParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidElfParsingResult"
            )

        if not isinstance(
            filesystem_inventory,
            FilesystemMetadataInventory,
        ):
            raise TypeError(
                "filesystem_inventory must be a "
                "FilesystemMetadataInventory"
            )

        return tuple(
            self._interpret_elf(
                elf,
                filesystem_inventory=filesystem_inventory,
            )
            for elf in parsing.elf_files
        )

    def _interpret_elf(
        self,
        elf: ParsedAndroidElf,
        *,
        filesystem_inventory: FilesystemMetadataInventory,
    ) -> AndroidUniverseElfRequirement:
        dependencies = tuple(
            AndroidUniverseElfDependencyRequirement(
                source=elf,
                name=name,
            )
            for name in elf.needed
        )

        interpreter_requirement = (
            AndroidUniverseElfInterpreterRequirement(
                source=elf,
                path=elf.interpreter,
            )
            if elf.interpreter is not None
            else None
        )

        soong_build_tuple_requirements_list = []
        soong_build_tuple_dispositions = []

        for literal in elf.soong_intermediate_components:
            (
                requirement,
                unresolved_reason,
            ) = self._interpret_soong_build_tuple(
                elf=elf,
                literal=literal,
            )

            if requirement is not None:
                soong_build_tuple_requirements_list.append(
                    requirement
                )
                soong_build_tuple_dispositions.append(
                    AndroidUniverseElfSoongBuildTupleDisposition(
                        source=elf,
                        literal=literal,
                        status=(
                            AndroidUniverseElfSoongBuildTupleDispositionStatus
                            .BUILD_TUPLE
                        ),
                        requirement=requirement,
                        reason=(
                            "canonical Android/Soong architecture and "
                            "architecture-variant structure interpreted"
                        ),
                    )
                )
            else:
                assert unresolved_reason is not None

                expected_architecture = (
                    android_architecture_for_elf_machine(
                        elf.machine
                    )
                )

                if (
                    expected_architecture is not None
                    and unresolved_reason
                    == (
                        "Soong tuple does not contain the canonical "
                        "architecture token for this ELF machine"
                    )
                ):
                    status = (
                        AndroidUniverseElfSoongBuildTupleDispositionStatus
                        .NON_BUILD_TUPLE
                    )
                    reason = (
                        "component does not contain the canonical "
                        "Android/Soong architecture token for this "
                        "ELF machine and is therefore not a build tuple"
                    )
                else:
                    status = (
                        AndroidUniverseElfSoongBuildTupleDispositionStatus
                        .UNRESOLVED
                    )
                    reason = unresolved_reason

                soong_build_tuple_dispositions.append(
                    AndroidUniverseElfSoongBuildTupleDisposition(
                        source=elf,
                        literal=literal,
                        status=status,
                        requirement=None,
                        reason=reason,
                    )
                )

        soong_build_tuple_requirements = tuple(
            soong_build_tuple_requirements_list
        )

        soong_build_tuple_dispositions = tuple(
            soong_build_tuple_dispositions
        )

        filesystem_aliases = (
            AndroidUniverseElfFilesystemAliasReconciler
            .reconcile(
                elf=elf,
                filesystem_inventory=filesystem_inventory,
            )
        )

        return AndroidUniverseElfRequirement(
            source=elf,
            role=self._role(
                elf
            ),
            dependencies=dependencies,
            interpreter_requirement=(
                interpreter_requirement
            ),
            soong_build_tuple_requirements=(
                soong_build_tuple_requirements
            ),
            soong_build_tuple_dispositions=(
                soong_build_tuple_dispositions
            ),
            filesystem_aliases=(
                filesystem_aliases
            ),
        )

    @classmethod
    def _interpret_soong_build_tuple(
        cls,
        *,
        elf: ParsedAndroidElf,
        literal: str,
    ) -> tuple[
        AndroidUniverseElfSoongBuildTupleRequirement | None,
        str | None,
    ]:
        prefix = "android_"

        if not literal.startswith(
            prefix
        ):
            raise ValueError(
                "Soong build tuple must start with android_"
            )

        tokens = literal[
            len(prefix):
        ].split(
            "_"
        )

        expected_architecture = (
            android_architecture_for_elf_machine(
                elf.machine
            )
        )

        if expected_architecture is None:
            return (
                None,
                "ELF machine has no canonical Android/Soong "
                "architecture interpretation",
            )

        try:
            architecture_index = tokens.index(
                expected_architecture
            )
        except ValueError:
            return (
                None,
                "Soong tuple does not contain the canonical "
                "architecture token for this ELF machine",
            )

        arch_variant_index = (
            architecture_index + 1
        )

        if arch_variant_index >= len(tokens):
            return (
                None,
                "Soong tuple has no architecture-variant token "
                "after its canonical architecture token",
            )

        arch_variant = tokens[
            arch_variant_index
        ]

        if not arch_variant:
            return (
                None,
                "Soong tuple architecture-variant token is empty",
            )

        domain = tuple(
            tokens[
                :architecture_index
            ]
        )

        remainder = tuple(
            tokens[
                arch_variant_index + 1:
            ]
        )

        return (
            AndroidUniverseElfSoongBuildTupleRequirement(
                source=elf,
                literal=literal,
                domain=domain,
                architecture=expected_architecture,
                arch_variant=arch_variant,
                remainder=remainder,
            ),
            None,
        )

    @staticmethod
    def _role(
        elf: ParsedAndroidElf,
    ) -> AndroidUniverseElfRole:
        """
        Interpret literal ELF structure into a device-level runtime role.

        ET_EXEC is directly executable.

        ET_DYN is overloaded by modern Android ELF binaries: shared
        libraries and position-independent executables both use ET_DYN.
        PT_INTERP is canonical structural evidence that an ET_DYN object
        participates as a directly launched executable.

        ET_DYN without PT_INTERP remains structurally a shared object.
        Installed-artifact taxonomy may independently establish a stronger
        Android role, such as the dynamic linker being installed as an
        executable.
        """

        if elf.is_executable:
            return (
                AndroidUniverseElfRole
                .EXECUTABLE
            )

        if elf.is_shared_object:
            if elf.interpreter is not None:
                return (
                    AndroidUniverseElfRole
                    .EXECUTABLE
                )

            return (
                AndroidUniverseElfRole
                .SHARED_OBJECT
            )

        return (
            AndroidUniverseElfRole
            .OTHER
        )
