from __future__ import annotations

from treeforge.android.parsing.classpath import (
    AndroidClasspathParsingResult,
)
from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveParsingResult,
)
from treeforge.android.universe.classpath.applicability import (
    AndroidUniverseClasspathSdkApplicabilityReconciler,
)
from treeforge.android.universe.classpath.installed_jar import (
    AndroidUniverseClasspathInstalledJarReconciler,
)
from treeforge.android.universe.classpath.java_archive import (
    AndroidUniverseJavaArchiveReconciler,
)
from treeforge.android.universe.classpath.assembly import (
    AndroidUniverseClasspathEffectiveAssembler,
)
from treeforge.android.universe.classpath.requirement import (
    AndroidUniverseClasspathJarRequirement,
    AndroidUniverseClasspathRequirement,
)
from treeforge.android.universe.artifact import (
    AndroidUniverseArtifactRequirementInventory,
)
from treeforge.android.universe.apex import (
    AndroidUniverseApexRequirement,
)
from treeforge.android.universe.properties import (
    AndroidUniverseFactConclusion,
)


class AndroidUniverseClasspathInterpreter:
    """
    Interpret Classpath Parsing into canonical declaration requirements and
    coordinate Classpath-owned SDK applicability reconciliation.

    Fragment merging, installed-JAR resolution, and ART/APEX relationships
    remain later Universe responsibilities.
    """

    def __init__(
        self,
        *,
        sdk_applicability_reconciler: (
            AndroidUniverseClasspathSdkApplicabilityReconciler
            | None
        ) = None,
        effective_assembler: (
            AndroidUniverseClasspathEffectiveAssembler
            | None
        ) = None,
    ) -> None:
        self.sdk_applicability_reconciler = (
            sdk_applicability_reconciler
            if sdk_applicability_reconciler is not None
            else AndroidUniverseClasspathSdkApplicabilityReconciler()
        )

        self.effective_assembler = (
            effective_assembler
            if effective_assembler is not None
            else AndroidUniverseClasspathEffectiveAssembler()
        )

        self.installed_jar_reconciler = (
            AndroidUniverseClasspathInstalledJarReconciler()
        )

        self.java_archive_reconciler = (
            AndroidUniverseJavaArchiveReconciler()
        )

    def interpret(
        self,
        parsing: AndroidClasspathParsingResult,
        *,
        java_archives: AndroidJavaArchiveParsingResult,
        property_conclusions: tuple[
            AndroidUniverseFactConclusion,
            ...,
        ],
        apex_requirements: tuple[
            AndroidUniverseApexRequirement,
            ...,
        ],
        artifact_requirements: (
            AndroidUniverseArtifactRequirementInventory
        ),
    ) -> AndroidUniverseClasspathRequirement:
        if not isinstance(
            parsing,
            AndroidClasspathParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidClasspathParsingResult"
            )

        jar_requirements = tuple(
            AndroidUniverseClasspathJarRequirement(
                configuration=configuration,
                declaration_index=declaration_index,
                source=jar,
            )
            for configuration
            in parsing.configurations
            for declaration_index, jar
            in enumerate(
                configuration.jars
            )
        )

        jar_applicability = (
            self.sdk_applicability_reconciler.reconcile(
                requirements=jar_requirements,
                property_conclusions=property_conclusions,
            )
        )

        (
            effective_classpaths,
            effective_unresolved_requirements,
        ) = self.effective_assembler.assemble(
            requirements=jar_requirements,
            applicability=jar_applicability,
            apex_requirements=apex_requirements,
        )

        installed_jar_resolutions = (
            self.installed_jar_reconciler.reconcile(
                effective_classpaths=effective_classpaths,
                artifact_requirements=artifact_requirements,
                apex_requirements=apex_requirements,
            )
        )

        java_archive_reconciliation = (
            self.java_archive_reconciler.reconcile(
                java_archives,
                artifact_requirements=artifact_requirements,
                installed_jar_resolutions=(
                    installed_jar_resolutions
                ),
            )
        )

        return AndroidUniverseClasspathRequirement(
            source=parsing,
            jar_requirements=jar_requirements,
            jar_applicability=jar_applicability,
            effective_classpaths=effective_classpaths,
            effective_unresolved_requirements=(
                effective_unresolved_requirements
            ),
            installed_jar_resolutions=(
                installed_jar_resolutions
            ),
            java_archive_reconciliation=(
                java_archive_reconciliation
            ),
        )
