from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from treeforge.android.runtime_linking.model import (
    AndroidRuntimeLinking,
)

from treeforge.android.reconstruction_ownership.artifact.evidence import (
    AndroidReconstructionArtifactEvidenceCollector,
)
from treeforge.android.reconstruction_ownership.artifact.resolver import (
    AndroidReconstructionArtifactOwnershipResolver,
)
from treeforge.android.reconstruction_ownership.model import (
    AndroidReconstructionOwnershipResult,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactDisposition,
    AndroidUniverseArtifactRequirement,
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.shell_script import (
    AndroidUniverseShellScriptReconciliation,
)


@dataclass(frozen=True, slots=True)
class AndroidReconstructionOwnershipStage:
    """
    Resolve canonical source-tree ownership only for families that require it.

    This stage does not:
    - parse or inspect factory images;
    - reinterpret Universe semantics;
    - perform Reconstruction Planning;
    - synthesize source content;
    - choose final filenames or destinations;
    - materialize files.
    """

    def resolve(
        self,
        universe: Any,
        *,
        runtime_linking: AndroidRuntimeLinking | None = None,
    ) -> AndroidReconstructionOwnershipResult:
        if runtime_linking is not None:
            if not isinstance(
                runtime_linking,
                AndroidRuntimeLinking,
            ):
                raise TypeError(
                    "runtime_linking must be an "
                    "AndroidRuntimeLinking or None"
                )

            if runtime_linking.universe is not universe:
                raise ValueError(
                    "Reconstruction Ownership requires Runtime Linking "
                    "to preserve the exact canonical Universe identity"
                )

        requirement_inventory = getattr(
            universe,
            "artifact_requirements",
            None,
        )

        if not isinstance(
            requirement_inventory,
            AndroidUniverseArtifactRequirementInventory,
        ):
            raise TypeError(
                "canonical Universe artifact_requirements "
                "must be an "
                "AndroidUniverseArtifactRequirementInventory"
            )

        requirements = (
            requirement_inventory.requirements
        )

        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "canonical artifact requirement inventory "
                "must preserve requirements as a tuple"
            )

        elf_requirements = getattr(
            universe,
            "elf_requirements",
            None,
        )

        if not isinstance(
            elf_requirements,
            tuple,
        ):
            raise TypeError(
                "canonical Universe elf_requirements "
                "must be a tuple"
            )

        elf_artifact_associations = getattr(
            universe,
            "elf_artifact_associations",
            None,
        )

        if not isinstance(
            elf_artifact_associations,
            tuple,
        ):
            raise TypeError(
                "canonical Universe elf_artifact_associations "
                "must be a tuple"
            )

        kernel_module_elf_associations = getattr(
            universe,
            "kernel_module_elf_associations",
            None,
        )

        if not isinstance(
            kernel_module_elf_associations,
            tuple,
        ):
            raise TypeError(
                "canonical Universe kernel_module_elf_associations "
                "must be a tuple"
            )

        kernel_module_requirement = getattr(
            universe,
            "kernel_module_requirement",
            None,
        )

        classpath_requirement = getattr(
            universe,
            "classpath_requirement",
            None,
        )

        shell_script_reconciliation = getattr(
            universe,
            "shell_script_reconciliation",
            None,
        )

        if not isinstance(
            shell_script_reconciliation,
            AndroidUniverseShellScriptReconciliation,
        ):
            raise TypeError(
                "canonical Universe shell_script_reconciliation "
                "must be an AndroidUniverseShellScriptReconciliation"
            )

        apk_requirement = getattr(
            universe,
            "apk_requirement",
            None,
        )

        apex_requirements = getattr(
            universe,
            "apex_requirements",
            None,
        )

        if not isinstance(
            apex_requirements,
            tuple,
        ):
            raise TypeError(
                "canonical Universe apex_requirements "
                "must be a tuple"
            )

        cross_family_relationships = getattr(
            universe,
            "cross_family_relationships",
            None,
        )

        if not isinstance(
            cross_family_relationships,
            tuple,
        ):
            raise TypeError(
                "canonical Universe cross_family_relationships "
                "must be a tuple"
            )

        artifact_evidence = (
            AndroidReconstructionArtifactEvidenceCollector
            .collect(
                artifacts=requirement_inventory,
                elf_requirements=elf_requirements,
                elf_artifact_associations=(
                    elf_artifact_associations
                ),
                kernel_module_elf_associations=(
                    kernel_module_elf_associations
                ),
                kernel_module_requirement=(
                    kernel_module_requirement
                ),
                classpath_requirement=(
                    classpath_requirement
                ),
                shell_script_reconciliation=(
                    shell_script_reconciliation
                ),
                apk_requirement=(
                    apk_requirement
                ),
                apex_requirements=(
                    apex_requirements
                ),
                runtime_linking=(
                    runtime_linking
                ),
                cross_family_relationships=(
                    cross_family_relationships
                ),
            )
        )

        decisions = []

        for requirement in requirements:
            if not isinstance(
                requirement,
                AndroidUniverseArtifactRequirement,
            ):
                raise TypeError(
                    "Universe artifact_requirements contains "
                    "an invalid requirement"
                )

            if (
                requirement.disposition
                is not AndroidUniverseArtifactDisposition
                .PRESERVE
            ):
                continue

            decisions.append(
                AndroidReconstructionArtifactOwnershipResolver
                .resolve(
                    requirement
                )
            )

        decisions.sort(
            key=lambda decision: (
                decision.requirement_kind,
                decision.source_identity,
            )
        )

        return AndroidReconstructionOwnershipResult(
            decisions=tuple(
                decisions
            ),
            artifact_evidence=(
                artifact_evidence
            ),
        )
