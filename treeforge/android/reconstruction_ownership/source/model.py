from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AndroidSourceRepositoryKind(StrEnum):
    """
    Structural source-repository category.

    Repository kind describes what sort of source repository this is.
    It does not by itself establish target relevance or ownership.
    """

    AOSP_PLATFORM = "aosp_platform"
    DEVICE_TREE = "device_tree"
    VENDOR_TREE = "vendor_tree"
    KERNEL_TREE = "kernel_tree"
    SEPOLICY_TREE = "sepolicy_tree"
    HARDWARE_TREE = "hardware_tree"
    OTHER_SOURCE = "other_source"
    UNKNOWN = "unknown"


class AndroidSourceRepositoryRelevance(StrEnum):
    """
    Relationship of a repository to the requested target source graph.
    """

    DIRECT = "direct"
    RELATED_ACTIVE = "related_active"
    RELATED_CONDITIONAL = "related_conditional"
    UNRELATED = "unrelated"


class AndroidSourceRelationshipKind(StrEnum):
    """Typed source-tree lineage relationship."""

    PRODUCT_INHERIT = "product_inherit"
    MAKE_INCLUDE = "make_include"
    SOONG_NAMESPACE = "soong_namespace"
    SEPOLICY_INCLUDE = "sepolicy_include"
    COPY_SOURCE = "copy_source"
    DEVICE_REFERENCE = "device_reference"


class AndroidSourceRelationshipApplicability(StrEnum):
    """
    Static applicability of one literal source relationship.

    ACTIVE relationships may expand unconditional lineage.

    CONDITIONAL relationships include:
    - inherit-product-if-exists;
    - -include;
    - relationships nested in unresolved Make conditionals.

    COMMENTED relationships are preserved as evidence only and never
    participate in lineage closure.
    """

    ACTIVE = "active"
    CONDITIONAL = "conditional"
    COMMENTED = "commented"


@dataclass(frozen=True, slots=True)
class AndroidSourceRepository:
    """One source repository from the checkout project inventory."""

    project_path: str
    checkout_path: Path
    kind: AndroidSourceRepositoryKind
    revision: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.project_path,
            str,
        ) or not self.project_path:
            raise ValueError(
                "project_path must be a non-empty string"
            )

        if self.project_path.startswith("/"):
            raise ValueError(
                "project_path must be checkout-relative"
            )

        if ".." in Path(
            self.project_path
        ).parts:
            raise ValueError(
                "project_path must not contain traversal"
            )

        if not isinstance(
            self.checkout_path,
            Path,
        ):
            raise TypeError(
                "checkout_path must be a Path"
            )

        if not isinstance(
            self.kind,
            AndroidSourceRepositoryKind,
        ):
            raise TypeError(
                "kind must be an AndroidSourceRepositoryKind"
            )

        if (
            self.revision is not None
            and (
                not isinstance(
                    self.revision,
                    str,
                )
                or not self.revision
            )
        ):
            raise ValueError(
                "revision must be None or a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class AndroidSourceRepositoryInventory:
    """Deterministic repository inventory for one Android checkout."""

    checkout_root: Path
    repositories: tuple[
        AndroidSourceRepository,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.checkout_root,
            Path,
        ):
            raise TypeError(
                "checkout_root must be a Path"
            )

        if not isinstance(
            self.repositories,
            tuple,
        ):
            raise TypeError(
                "repositories must be a tuple"
            )

        if not all(
            isinstance(
                repository,
                AndroidSourceRepository,
            )
            for repository in self.repositories
        ):
            raise TypeError(
                "repositories contains an invalid model"
            )

        paths = tuple(
            repository.project_path
            for repository in self.repositories
        )

        if len(paths) != len(set(paths)):
            raise ValueError(
                "repository project paths must be unique"
            )

        if paths != tuple(sorted(paths)):
            raise ValueError(
                "repository inventory must use deterministic ordering"
            )

    def repository_for_project(
        self,
        project_path: str,
    ) -> AndroidSourceRepository | None:
        for repository in self.repositories:
            if repository.project_path == project_path:
                return repository

        return None

    def repository_for_source_path(
        self,
        source_path: str,
    ) -> AndroidSourceRepository | None:
        """
        Resolve a checkout-relative source path to its owning project.

        Longest-prefix resolution is intentional because Repo projects
        may be nested below another structural source directory.
        """

        candidates = []

        for repository in self.repositories:
            prefix = repository.project_path

            if (
                source_path == prefix
                or source_path.startswith(
                    prefix + "/"
                )
            ):
                candidates.append(
                    repository
                )

        if not candidates:
            return None

        candidates.sort(
            key=lambda repository: (
                -len(repository.project_path),
                repository.project_path,
            )
        )

        return candidates[0]


@dataclass(frozen=True, slots=True)
class AndroidSourceRepositoryRelationship:
    """One literal source-tree lineage edge or inactive edge candidate."""

    source_project: str
    referenced_path: str
    target_project: str | None

    kind: AndroidSourceRelationshipKind
    applicability: AndroidSourceRelationshipApplicability

    evidence_path: str
    evidence_line: int
    raw_expression: str

    def __post_init__(self) -> None:
        for field_name, value in (
            (
                "source_project",
                self.source_project,
            ),
            (
                "referenced_path",
                self.referenced_path,
            ),
            (
                "evidence_path",
                self.evidence_path,
            ),
            (
                "raw_expression",
                self.raw_expression,
            ),
        ):
            if not isinstance(
                value,
                str,
            ) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if (
            self.target_project is not None
            and (
                not isinstance(
                    self.target_project,
                    str,
                )
                or not self.target_project
            )
        ):
            raise ValueError(
                "target_project must be None or non-empty"
            )

        if not isinstance(
            self.kind,
            AndroidSourceRelationshipKind,
        ):
            raise TypeError(
                "kind must be an AndroidSourceRelationshipKind"
            )

        if not isinstance(
            self.applicability,
            AndroidSourceRelationshipApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidSourceRelationshipApplicability"
            )

        if (
            not isinstance(
                self.evidence_line,
                int,
            )
            or self.evidence_line <= 0
        ):
            raise ValueError(
                "evidence_line must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class AndroidSourceReachedFile:
    """
    One exact source file reached through target source-lineage traversal.

    Applicability describes the strongest exact traversal path that reaches
    the file. ACTIVE supersedes CONDITIONAL.

    This is traversal evidence only. Reaching a Makefile does not imply that
    every declaration inside it is itself active after full Make evaluation.
    """

    source_path: str
    applicability: AndroidSourceRelationshipApplicability

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.source_path,
                str,
            )
            or not self.source_path
        ):
            raise ValueError(
                "source_path must be a non-empty string"
            )

        if self.source_path.startswith(
            "/"
        ):
            raise ValueError(
                "source_path must be checkout-relative"
            )

        if ".." in Path(
            self.source_path
        ).parts:
            raise ValueError(
                "source_path must not contain traversal"
            )

        if not isinstance(
            self.applicability,
            AndroidSourceRelationshipApplicability,
        ):
            raise TypeError(
                "applicability must be an "
                "AndroidSourceRelationshipApplicability"
            )

        if (
            self.applicability
            is AndroidSourceRelationshipApplicability
            .COMMENTED
        ):
            raise ValueError(
                "reached files cannot have COMMENTED applicability"
            )


@dataclass(frozen=True, slots=True)
class AndroidSourceRepositoryLineage:
    """Resolved repository relevance and preserved relationship evidence."""

    inventory: AndroidSourceRepositoryInventory

    reached_files: tuple[
        AndroidSourceReachedFile,
        ...,
    ]

    relationships: tuple[
        AndroidSourceRepositoryRelationship,
        ...,
    ]

    relevance: tuple[
        tuple[
            str,
            AndroidSourceRepositoryRelevance,
        ],
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.reached_files,
            tuple,
        ):
            raise TypeError(
                "reached_files must be a tuple"
            )

        if not all(
            isinstance(
                reached,
                AndroidSourceReachedFile,
            )
            for reached in self.reached_files
        ):
            raise TypeError(
                "reached_files contains an invalid model"
            )

        reached_paths = tuple(
            reached.source_path
            for reached in self.reached_files
        )

        if (
            len(reached_paths)
            != len(
                set(
                    reached_paths
                )
            )
        ):
            raise ValueError(
                "reached source paths must be unique"
            )

        if (
            reached_paths
            != tuple(
                sorted(
                    reached_paths
                )
            )
        ):
            raise ValueError(
                "reached_files must use deterministic ordering"
            )

        for reached in self.reached_files:
            physical = (
                self.inventory.checkout_root
                / reached.source_path
            )

            if not physical.is_file():
                raise ValueError(
                    "reached file does not exist in checkout: "
                    f"{reached.source_path}"
                )

            if (
                self.inventory.repository_for_source_path(
                    reached.source_path
                )
                is None
            ):
                raise ValueError(
                    "reached file is not owned by a Repo project: "
                    f"{reached.source_path}"
                )

        if not isinstance(
            self.relationships,
            tuple,
        ):
            raise TypeError(
                "relationships must be a tuple"
            )

        if not all(
            isinstance(
                relationship,
                AndroidSourceRepositoryRelationship,
            )
            for relationship in self.relationships
        ):
            raise TypeError(
                "relationships contains an invalid model"
            )

        if not isinstance(
            self.relevance,
            tuple,
        ):
            raise TypeError(
                "relevance must be a tuple"
            )

        keys = tuple(
            project_path
            for project_path, _ in self.relevance
        )

        if len(keys) != len(set(keys)):
            raise ValueError(
                "repository relevance entries must be unique"
            )

        if keys != tuple(sorted(keys)):
            raise ValueError(
                "repository relevance must use deterministic ordering"
            )

        for (
            project_path,
            relevance,
        ) in self.relevance:
            if (
                self.inventory.repository_for_project(
                    project_path
                )
                is None
            ):
                raise ValueError(
                    "repository relevance references an unknown project: "
                    f"{project_path}"
                )

            if not isinstance(
                relevance,
                AndroidSourceRepositoryRelevance,
            ):
                raise TypeError(
                    "repository relevance contains an invalid value"
                )

    def reached_file_for(
        self,
        source_path: str,
    ) -> AndroidSourceReachedFile | None:
        for reached in self.reached_files:
            if reached.source_path == source_path:
                return reached

        return None

    def relevance_for(
        self,
        project_path: str,
    ) -> AndroidSourceRepositoryRelevance:
        for (
            candidate,
            relevance,
        ) in self.relevance:
            if candidate == project_path:
                return relevance

        return AndroidSourceRepositoryRelevance.UNRELATED
