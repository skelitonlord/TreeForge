from __future__ import annotations

from treeforge.android.parsing.java_archive import (
    AndroidJavaArchiveParsingResult,
    ParsedAndroidJavaArchive,
)

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.parsing.classpath import (
    AndroidClasspathJar,
    AndroidClasspathKind,
    AndroidClasspathParsingResult,
    ParsedAndroidClasspathConfiguration,
)
from treeforge.android.universe.artifact.model import (
    AndroidUniverseArtifactRequirement,
)
from treeforge.android.universe.properties import (
    AndroidUniverseFactConclusion,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseClasspathJarRequirement:
    """
    Canonical Universe requirement for one literal classpaths.proto Jar
    declaration.

    The requirement preserves the exact Parsing configuration and Jar
    identities plus the declaration ordinal within that fragment.

    It interprets only the schema-known classpath enum. SDK applicability,
    fragment merging, installed-artifact resolution, and ART/APEX
    relationships remain separate Universe responsibilities.
    """

    configuration: ParsedAndroidClasspathConfiguration
    declaration_index: int
    source: AndroidClasspathJar

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.configuration,
            ParsedAndroidClasspathConfiguration,
        ):
            raise TypeError(
                "configuration must be a "
                "ParsedAndroidClasspathConfiguration"
            )

        if (
            isinstance(
                self.declaration_index,
                bool,
            )
            or not isinstance(
                self.declaration_index,
                int,
            )
        ):
            raise TypeError(
                "declaration_index must be an integer"
            )

        if self.declaration_index < 0:
            raise ValueError(
                "declaration_index must not be negative"
            )

        if not isinstance(
            self.source,
            AndroidClasspathJar,
        ):
            raise TypeError(
                "source must be an AndroidClasspathJar"
            )

        if self.declaration_index >= len(
            self.configuration.jars
        ):
            raise ValueError(
                "declaration_index exceeds configuration JAR population"
            )

        if (
            self.configuration.jars[
                self.declaration_index
            ]
            is not self.source
        ):
            raise ValueError(
                "source must preserve the exact Parsing JAR identity "
                "at declaration_index"
            )

    @property
    def declared_path(
        self,
    ) -> str:
        return self.source.path

    @property
    def path_present(
        self,
    ) -> bool:
        return self.source.path_present

    @property
    def classpath_value(
        self,
    ) -> int:
        return self.source.classpath_value

    @property
    def classpath_present(
        self,
    ) -> bool:
        return self.source.classpath_present

    @property
    def known_classpath(
        self,
    ) -> AndroidClasspathKind | None:
        return self.source.known_classpath

    @property
    def min_sdk_version(
        self,
    ) -> str:
        return self.source.min_sdk_version

    @property
    def min_sdk_version_present(
        self,
    ) -> bool:
        return self.source.min_sdk_version_present

    @property
    def max_sdk_version(
        self,
    ) -> str:
        return self.source.max_sdk_version

    @property
    def max_sdk_version_present(
        self,
    ) -> bool:
        return self.source.max_sdk_version_present

    @property
    def requirement_id(
        self,
    ) -> str:
        return (
            "classpath-jar:"
            f"{self.configuration.source.identity_key}:"
            f"{self.declaration_index}"
        )


class AndroidUniverseClasspathJarApplicabilityStatus(
    StrEnum
):
    """
    SDK applicability state of one Classpath Jar declaration.

    INAPPLICABLE means the canonical device SDK is known and lies outside
    the declaration's explicit SDK interval.

    UNRESOLVED preserves declarations whose device SDK or declared SDK
    bounds cannot be interpreted canonically.
    """

    ACTIVE = "active"
    INAPPLICABLE = "inapplicable"
    UNRESOLVED = "unresolved"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseClasspathJarApplicability:
    """
    Canonical SDK-applicability conclusion for one Classpath Jar requirement.

    ``sdk_conclusion`` preserves the exact property-reconciliation conclusion
    used to establish the current device SDK. Parsed integer values are
    derived semantic conveniences; raw declaration values remain owned by
    ``requirement.source``.
    """

    requirement: AndroidUniverseClasspathJarRequirement

    status: AndroidUniverseClasspathJarApplicabilityStatus

    sdk_conclusion: AndroidUniverseFactConclusion | None

    device_sdk: int | None

    minimum_sdk: int | None
    maximum_sdk: int | None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseClasspathJarRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseClasspathJarRequirement"
            )

        if not isinstance(
            self.status,
            AndroidUniverseClasspathJarApplicabilityStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseClasspathJarApplicabilityStatus"
            )

        if (
            self.sdk_conclusion is not None
            and not isinstance(
                self.sdk_conclusion,
                AndroidUniverseFactConclusion,
            )
        ):
            raise TypeError(
                "sdk_conclusion must be an "
                "AndroidUniverseFactConclusion or None"
            )

        if (
            self.sdk_conclusion is not None
            and self.sdk_conclusion.fact != "sdk_level"
        ):
            raise ValueError(
                "sdk_conclusion must describe sdk_level"
            )

        for name in (
            "device_sdk",
            "minimum_sdk",
            "maximum_sdk",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                value is not None
                and (
                    isinstance(
                        value,
                        bool,
                    )
                    or not isinstance(
                        value,
                        int,
                    )
                    or value < 1
                )
            ):
                raise TypeError(
                    f"{name} must be a positive integer or None"
                )

        if (
            not self.requirement.min_sdk_version_present
            and self.minimum_sdk is not None
        ):
            raise ValueError(
                "minimum_sdk must be None when the declaration "
                "has no min_sdk_version field"
            )

        if (
            not self.requirement.max_sdk_version_present
            and self.maximum_sdk is not None
        ):
            raise ValueError(
                "maximum_sdk must be None when the declaration "
                "has no max_sdk_version field"
            )

    @property
    def requirement_id(
        self,
    ) -> str:
        return self.requirement.requirement_id


class AndroidUniverseClasspathFragmentKind(
    StrEnum
):
    """
    Runtime ownership of one classpaths.proto fragment.

    SYSTEM is the canonical /system classpath fragment.
    APEX is a fragment owned by an exact canonical APEX requirement.
    """

    SYSTEM = "system"
    APEX = "apex"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseClasspathEffectiveEntry:
    """
    One declaration admitted into an effective runtime classpath.

    The entry preserves the exact declaration requirement and exact
    applicability conclusion. ``runtime_fragment_path`` is the Android-visible
    fragment path used by derive_classpath ordering semantics.
    """

    requirement: AndroidUniverseClasspathJarRequirement
    applicability: AndroidUniverseClasspathJarApplicability

    fragment_kind: AndroidUniverseClasspathFragmentKind
    runtime_fragment_path: str

    fragment_index: int
    classpath_index: int

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.requirement,
            AndroidUniverseClasspathJarRequirement,
        ):
            raise TypeError(
                "requirement must be an "
                "AndroidUniverseClasspathJarRequirement"
            )

        if not isinstance(
            self.applicability,
            AndroidUniverseClasspathJarApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidUniverseClasspathJarApplicability"
            )

        if self.applicability.requirement is not self.requirement:
            raise ValueError(
                "effective entry applicability must preserve exact "
                "requirement identity"
            )

        if (
            self.applicability.status
            is not AndroidUniverseClasspathJarApplicabilityStatus.ACTIVE
        ):
            raise ValueError(
                "effective classpath entries must be ACTIVE"
            )

        if not isinstance(
            self.fragment_kind,
            AndroidUniverseClasspathFragmentKind,
        ):
            raise TypeError(
                "fragment_kind must be an "
                "AndroidUniverseClasspathFragmentKind"
            )

        if not isinstance(
            self.runtime_fragment_path,
            str,
        ):
            raise TypeError(
                "runtime_fragment_path must be a string"
            )

        if not self.runtime_fragment_path.startswith("/"):
            raise ValueError(
                "runtime_fragment_path must be absolute"
            )

        for name in (
            "fragment_index",
            "classpath_index",
        ):
            value = getattr(
                self,
                name,
            )

            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
            ):
                raise TypeError(
                    f"{name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{name} must not be negative"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseEffectiveClasspath:
    """
    One fully ordered effective runtime classpath population.
    """

    classpath: AndroidClasspathKind

    entries: tuple[
        AndroidUniverseClasspathEffectiveEntry,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.classpath,
            AndroidClasspathKind,
        ):
            raise TypeError(
                "classpath must be an AndroidClasspathKind"
            )

        if self.classpath is AndroidClasspathKind.UNKNOWN:
            raise ValueError(
                "effective classpath cannot use UNKNOWN kind"
            )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                entry,
                AndroidUniverseClasspathEffectiveEntry,
            )
            for entry in self.entries
        ):
            raise TypeError(
                "entries must contain only "
                "AndroidUniverseClasspathEffectiveEntry instances"
            )

        for index, entry in enumerate(
            self.entries
        ):
            if entry.classpath_index != index:
                raise ValueError(
                    "effective entries must preserve contiguous "
                    "classpath_index ordering"
                )

            if (
                entry.requirement.known_classpath
                is not self.classpath
            ):
                raise ValueError(
                    "effective entry classpath kind does not match "
                    "the containing effective classpath"
                )


class AndroidUniverseClasspathInstalledJarStatus(
    StrEnum
):
    """
    Installed-artifact resolution for one effective Classpath declaration.
    """

    RESOLVED = "resolved"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseClasspathInstalledJarResolution:
    """
    Resolve one exact effective Classpath entry to canonical installed
    filesystem artifacts.

    Candidate artifacts remain exact AndroidUniverseArtifactRequirement
    identities. No physical file or path is rediscovered here.
    """

    entry: AndroidUniverseClasspathEffectiveEntry

    status: AndroidUniverseClasspathInstalledJarStatus

    matched_artifacts: tuple[
        AndroidUniverseArtifactRequirement,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.entry,
            AndroidUniverseClasspathEffectiveEntry,
        ):
            raise TypeError(
                "entry must be an "
                "AndroidUniverseClasspathEffectiveEntry"
            )

        if not isinstance(
            self.status,
            AndroidUniverseClasspathInstalledJarStatus,
        ):
            raise TypeError(
                "status must be an "
                "AndroidUniverseClasspathInstalledJarStatus"
            )

        if not isinstance(
            self.matched_artifacts,
            tuple,
        ):
            raise TypeError(
                "matched_artifacts must be a tuple"
            )

        if not all(
            isinstance(
                artifact,
                AndroidUniverseArtifactRequirement,
            )
            for artifact
            in self.matched_artifacts
        ):
            raise TypeError(
                "matched_artifacts must contain only "
                "AndroidUniverseArtifactRequirement instances"
            )

        identities = tuple(
            artifact.identity_key
            for artifact
            in self.matched_artifacts
        )

        if len(
            identities
        ) != len(
            set(
                identities
            )
        ):
            raise ValueError(
                "matched_artifacts must contain unique canonical "
                "artifact identities"
            )

        if (
            self.status
            is AndroidUniverseClasspathInstalledJarStatus.RESOLVED
            and len(
                self.matched_artifacts
            ) != 1
        ):
            raise ValueError(
                "RESOLVED installed JAR resolution requires exactly "
                "one matched artifact"
            )

        if (
            self.status
            is AndroidUniverseClasspathInstalledJarStatus.ABSENT
            and self.matched_artifacts
        ):
            raise ValueError(
                "ABSENT installed JAR resolution cannot contain "
                "matched artifacts"
            )

        if (
            self.status
            is AndroidUniverseClasspathInstalledJarStatus.AMBIGUOUS
            and len(
                self.matched_artifacts
            ) < 2
        ):
            raise ValueError(
                "AMBIGUOUS installed JAR resolution requires at least "
                "two matched artifacts"
            )

    @property
    def resolved_artifact(
        self,
    ) -> AndroidUniverseArtifactRequirement | None:
        if (
            self.status
            is not AndroidUniverseClasspathInstalledJarStatus.RESOLVED
        ):
            return None

        return self.matched_artifacts[
            0
        ]



@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseJavaArchiveAssociation:
    source: ParsedAndroidJavaArchive
    artifact: AndroidUniverseArtifactRequirement
    classpath_resolutions: tuple[
        AndroidUniverseClasspathInstalledJarResolution,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedAndroidJavaArchive,
        ):
            raise TypeError(
                "source must be a ParsedAndroidJavaArchive"
            )

        if not isinstance(
            self.artifact,
            AndroidUniverseArtifactRequirement,
        ):
            raise TypeError(
                "artifact must be an "
                "AndroidUniverseArtifactRequirement"
            )

        if not isinstance(
            self.classpath_resolutions,
            tuple,
        ):
            raise TypeError(
                "classpath_resolutions must be a tuple"
            )

        for resolution in self.classpath_resolutions:
            if not isinstance(
                resolution,
                AndroidUniverseClasspathInstalledJarResolution,
            ):
                raise TypeError(
                    "classpath_resolutions must contain only "
                    "installed-JAR resolutions"
                )

            if not any(
                candidate is self.artifact
                for candidate
                in resolution.matched_artifacts
            ):
                raise ValueError(
                    "Java archive resolution does not preserve "
                    "exact Artifact requirement identity"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseJavaArchiveReconciliation:
    source: AndroidJavaArchiveParsingResult
    associations: tuple[
        AndroidUniverseJavaArchiveAssociation,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            AndroidJavaArchiveParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidJavaArchiveParsingResult"
            )

        if len(
            self.associations
        ) != len(
            self.source.archives
        ):
            raise ValueError(
                "Java archive reconciliation must conserve every "
                "Parsing Java archive"
            )

        if not all(
            association.source is archive
            for association, archive
            in zip(
                self.associations,
                self.source.archives,
                strict=True,
            )
        ):
            raise ValueError(
                "Java archive reconciliation must preserve exact "
                "Parsing identity and order"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseClasspathRequirement:
    """
    Canonical Universe Classpath requirement.

    ``source`` preserves the complete canonical Parsing result.
    ``jar_requirements`` provides one semantic identity for every literal
    Jar declaration without merging fragments or deduplicating paths.

    ``jar_applicability`` contains one SDK-applicability conclusion for every
    declaration in identical canonical order.
    """

    source: AndroidClasspathParsingResult

    jar_requirements: tuple[
        AndroidUniverseClasspathJarRequirement,
        ...,
    ]

    jar_applicability: tuple[
        AndroidUniverseClasspathJarApplicability,
        ...,
    ]

    effective_classpaths: tuple[
        AndroidUniverseEffectiveClasspath,
        ...,
    ]

    effective_unresolved_requirements: tuple[
        AndroidUniverseClasspathJarRequirement,
        ...,
    ]

    installed_jar_resolutions: tuple[
        AndroidUniverseClasspathInstalledJarResolution,
        ...,
    ]

    java_archive_reconciliation: (
        AndroidUniverseJavaArchiveReconciliation
    )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            AndroidClasspathParsingResult,
        ):
            raise TypeError(
                "source must be an AndroidClasspathParsingResult"
            )

        if not isinstance(
            self.java_archive_reconciliation,
            AndroidUniverseJavaArchiveReconciliation,
        ):
            raise TypeError(
                "java_archive_reconciliation must be an "
                "AndroidUniverseJavaArchiveReconciliation"
            )

        if not isinstance(
            self.jar_requirements,
            tuple,
        ):
            raise TypeError(
                "jar_requirements must be a tuple"
            )

        if not all(
            isinstance(
                requirement,
                AndroidUniverseClasspathJarRequirement,
            )
            for requirement in self.jar_requirements
        ):
            raise TypeError(
                "jar_requirements must contain only "
                "AndroidUniverseClasspathJarRequirement instances"
            )

        expected = tuple(
            (
                configuration,
                declaration_index,
                jar,
            )
            for configuration
            in self.source.configurations
            for declaration_index, jar
            in enumerate(
                configuration.jars
            )
        )

        actual = tuple(
            (
                requirement.configuration,
                requirement.declaration_index,
                requirement.source,
            )
            for requirement
            in self.jar_requirements
        )

        if len(
            actual
        ) != len(
            expected
        ):
            raise ValueError(
                "jar_requirements must cover every Parsing JAR "
                "declaration exactly once"
            )

        for actual_item, expected_item in zip(
            actual,
            expected,
            strict=True,
        ):
            actual_configuration, actual_index, actual_jar = (
                actual_item
            )
            expected_configuration, expected_index, expected_jar = (
                expected_item
            )

            if (
                actual_configuration
                is not expected_configuration
                or actual_index != expected_index
                or actual_jar is not expected_jar
            ):
                raise ValueError(
                    "jar_requirements must preserve exact canonical "
                    "Parsing declaration order and identity"
                )

        requirement_ids = tuple(
            requirement.requirement_id
            for requirement
            in self.jar_requirements
        )

        if len(
            requirement_ids
        ) != len(
            set(
                requirement_ids
            )
        ):
            raise ValueError(
                "jar_requirements must contain unique requirement identities"
            )

        if not isinstance(
            self.jar_applicability,
            tuple,
        ):
            raise TypeError(
                "jar_applicability must be a tuple"
            )

        if not all(
            isinstance(
                applicability,
                AndroidUniverseClasspathJarApplicability,
            )
            for applicability in self.jar_applicability
        ):
            raise TypeError(
                "jar_applicability must contain only "
                "AndroidUniverseClasspathJarApplicability instances"
            )

        if len(
            self.jar_applicability
        ) != len(
            self.jar_requirements
        ):
            raise ValueError(
                "jar_applicability must cover every JAR requirement "
                "exactly once"
            )

        for requirement, applicability in zip(
            self.jar_requirements,
            self.jar_applicability,
            strict=True,
        ):
            if applicability.requirement is not requirement:
                raise ValueError(
                    "jar_applicability must preserve exact canonical "
                    "JAR requirement identity and ordering"
                )

        if not isinstance(
            self.effective_classpaths,
            tuple,
        ):
            raise TypeError(
                "effective_classpaths must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseEffectiveClasspath,
            )
            for value in self.effective_classpaths
        ):
            raise TypeError(
                "effective_classpaths must contain only "
                "AndroidUniverseEffectiveClasspath instances"
            )

        effective_kinds = tuple(
            value.classpath
            for value in self.effective_classpaths
        )

        if len(
            effective_kinds
        ) != len(
            set(
                effective_kinds
            )
        ):
            raise ValueError(
                "effective_classpaths must contain unique "
                "classpath kinds"
            )

        if not isinstance(
            self.effective_unresolved_requirements,
            tuple,
        ):
            raise TypeError(
                "effective_unresolved_requirements must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidUniverseClasspathJarRequirement,
            )
            for value in self.effective_unresolved_requirements
        ):
            raise TypeError(
                "effective_unresolved_requirements must contain only "
                "AndroidUniverseClasspathJarRequirement instances"
            )

        canonical_requirement_ids = {
            id(
                value
            )
            for value in self.jar_requirements
        }

        for unresolved in self.effective_unresolved_requirements:
            if id(
                unresolved
            ) not in canonical_requirement_ids:
                raise ValueError(
                    "effective unresolved requirement must preserve "
                    "canonical JAR requirement identity"
                )

        effective_requirement_ids = {
            id(
                entry.requirement
            )
            for classpath in self.effective_classpaths
            for entry in classpath.entries
        }

        unresolved_requirement_ids = {
            id(
                value
            )
            for value in self.effective_unresolved_requirements
        }

        if (
            effective_requirement_ids
            & unresolved_requirement_ids
        ):
            raise ValueError(
                "effective and unresolved requirement populations "
                "must not overlap"
            )

        if not isinstance(
            self.installed_jar_resolutions,
            tuple,
        ):
            raise TypeError(
                "installed_jar_resolutions must be a tuple"
            )

        if not all(
            isinstance(
                resolution,
                AndroidUniverseClasspathInstalledJarResolution,
            )
            for resolution
            in self.installed_jar_resolutions
        ):
            raise TypeError(
                "installed_jar_resolutions must contain only "
                "AndroidUniverseClasspathInstalledJarResolution "
                "instances"
            )

        effective_entries = tuple(
            entry
            for effective
            in self.effective_classpaths
            for entry
            in effective.entries
        )

        if len(
            self.installed_jar_resolutions
        ) != len(
            effective_entries
        ):
            raise ValueError(
                "installed JAR reconciliation must cover every "
                "effective Classpath entry exactly once"
            )

        for entry, resolution in zip(
            effective_entries,
            self.installed_jar_resolutions,
            strict=True,
        ):
            if resolution.entry is not entry:
                raise ValueError(
                    "installed JAR reconciliation must preserve exact "
                    "effective-entry identity and canonical ordering"
                )

    @property
    def source_count(
        self,
    ) -> int:
        return self.source.source_count

    @property
    def jar_count(
        self,
    ) -> int:
        return len(
            self.jar_requirements
        )
