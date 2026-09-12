from __future__ import annotations

from pathlib import Path
import re

from treeforge.android.reconstruction_ownership.source.model import (
    AndroidSourceRelationshipApplicability,
    AndroidSourceRelationshipKind,
    AndroidSourceReachedFile,
    AndroidSourceRepositoryInventory,
    AndroidSourceRepositoryLineage,
    AndroidSourceRepositoryRelationship,
    AndroidSourceRepositoryRelevance,
)


_REFERENCE_RE = re.compile(
    r"""
    (?:
        [A-Za-z0-9_.+-]+
        /
    )+
    [A-Za-z0-9_.$()+{}+-]+
    """,
    re.VERBOSE,
)

_CONDITIONAL_START_RE = re.compile(
    r"^\s*(?:ifeq|ifneq|ifdef|ifndef)\b"
)

_CONDITIONAL_END_RE = re.compile(
    r"^\s*endif\b"
)

_TRAVERSABLE_RELATIONSHIPS = frozenset(
    (
        AndroidSourceRelationshipKind.PRODUCT_INHERIT,
        AndroidSourceRelationshipKind.MAKE_INCLUDE,
    )
)


class AndroidSourceRepositoryLineageResolver:
    """
    Resolve target source lineage from exact source-file relationships.

    Repository inventory provides source ownership/project boundaries.
    It does NOT define traversal boundaries.

    Lineage traversal starts from explicit source entrypoints and follows only
    exact literal Make include/inherit relationships whose referenced file can
    be resolved.

    Other relationship families such as Soong namespaces, SELinux directories,
    copy sources, manifests, overlays, and unresolved variable-bearing paths
    remain first-class evidence and may establish repository relevance, but
    they do not authorize recursive scanning of that repository.

    The resolver does not:
    - decide Reconstruction Ownership domains;
    - classify artifacts as proprietary;
    - infer missing source availability;
    - execute Make;
    - evaluate unresolved Make variables.
    """

    @classmethod
    def resolve(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        seed_paths: tuple[str, ...],
    ) -> AndroidSourceRepositoryLineage:
        if not isinstance(
            seed_paths,
            tuple,
        ) or not seed_paths:
            raise ValueError(
                "seed_paths must be a non-empty tuple"
            )

        normalized_seeds = []

        for seed_path in seed_paths:
            normalized = cls._normalize_source_path(
                seed_path
            )

            if normalized is None:
                raise ValueError(
                    "seed path must be a literal checkout-relative path: "
                    f"{seed_path}"
                )

            physical = (
                inventory.checkout_root
                / normalized
            )

            if not physical.is_file():
                raise FileNotFoundError(
                    "source lineage seed does not exist: "
                    f"{normalized}"
                )

            repository = (
                inventory.repository_for_source_path(
                    normalized
                )
            )

            if repository is None:
                raise ValueError(
                    "source lineage seed is not owned by a Repo project: "
                    f"{normalized}"
                )

            normalized_seeds.append(
                normalized
            )

        normalized_seeds = sorted(
            set(normalized_seeds)
        )

        direct_projects = {
            inventory.repository_for_source_path(
                seed
            ).project_path
            for seed in normalized_seeds
        }

        active_related: set[str] = set()
        conditional_related: set[str] = set()

        relationships: list[
            AndroidSourceRepositoryRelationship
        ] = []

        #
        # The same file may be reachable both conditionally and actively.
        # An active reachability path supersedes a conditional one.
        #
        visited: dict[
            str,
            AndroidSourceRelationshipApplicability,
        ] = {}

        queue: list[
            tuple[
                str,
                AndroidSourceRelationshipApplicability,
            ]
        ] = [
            (
                seed,
                AndroidSourceRelationshipApplicability.ACTIVE,
            )
            for seed in normalized_seeds
        ]

        while queue:
            (
                source_path,
                incoming_applicability,
            ) = queue.pop(0)

            previous = visited.get(
                source_path
            )

            if (
                previous
                is AndroidSourceRelationshipApplicability.ACTIVE
            ):
                continue

            if (
                previous
                is AndroidSourceRelationshipApplicability.CONDITIONAL
                and incoming_applicability
                is AndroidSourceRelationshipApplicability.CONDITIONAL
            ):
                continue

            visited[
                source_path
            ] = incoming_applicability

            physical_path = (
                inventory.checkout_root
                / source_path
            )

            repository = (
                inventory.repository_for_source_path(
                    source_path
                )
            )

            if repository is None:
                raise RuntimeError(
                    "reachable source path has no repository owner: "
                    f"{source_path}"
                )

            discovered = (
                cls._relationships_for_make_file(
                    inventory=inventory,
                    source_project=repository.project_path,
                    path=physical_path,
                )
            )

            relationships.extend(
                discovered
            )

            for relationship in discovered:
                if (
                    relationship.applicability
                    is AndroidSourceRelationshipApplicability
                    .COMMENTED
                ):
                    continue

                effective = cls._combine_applicability(
                    incoming=incoming_applicability,
                    edge=relationship.applicability,
                )

                target_project = (
                    relationship.target_project
                )

                if (
                    target_project is not None
                    and target_project not in direct_projects
                ):
                    cls._record_project_relevance(
                        project_path=target_project,
                        applicability=effective,
                        active_related=active_related,
                        conditional_related=conditional_related,
                    )

                #
                # Only include/inherit relationships may expand file
                # traversal. Merely mentioning a project or directory does
                # not grant permission to scan that project's Makefiles.
                #
                if (
                    relationship.kind
                    not in _TRAVERSABLE_RELATIONSHIPS
                ):
                    continue

                traversal_target = (
                    cls._literal_traversal_target(
                        inventory=inventory,
                        referenced_path=(
                            relationship.referenced_path
                        ),
                    )
                )

                if traversal_target is None:
                    continue

                queue.append(
                    (
                        traversal_target,
                        effective,
                    )
                )

        #
        # A relationship may be encountered more than once through different
        # entry paths. Preserve one deterministic copy of identical evidence.
        #
        unique_relationships = {}

        for relationship in relationships:
            key = (
                relationship.source_project,
                relationship.referenced_path,
                relationship.target_project,
                relationship.kind.value,
                relationship.applicability.value,
                relationship.evidence_path,
                relationship.evidence_line,
                relationship.raw_expression,
            )

            unique_relationships[
                key
            ] = relationship

        relationships = list(
            unique_relationships.values()
        )

        relationships.sort(
            key=lambda relationship: (
                relationship.source_project,
                relationship.evidence_path,
                relationship.evidence_line,
                relationship.kind.value,
                relationship.referenced_path,
                relationship.target_project or "",
                relationship.applicability.value,
            )
        )

        relevance = []

        for repository in inventory.repositories:
            project_path = (
                repository.project_path
            )

            if project_path in direct_projects:
                value = (
                    AndroidSourceRepositoryRelevance
                    .DIRECT
                )
            elif project_path in active_related:
                value = (
                    AndroidSourceRepositoryRelevance
                    .RELATED_ACTIVE
                )
            elif project_path in conditional_related:
                value = (
                    AndroidSourceRepositoryRelevance
                    .RELATED_CONDITIONAL
                )
            else:
                value = (
                    AndroidSourceRepositoryRelevance
                    .UNRELATED
                )

            relevance.append(
                (
                    project_path,
                    value,
                )
            )

        relevance.sort(
            key=lambda item: item[0]
        )

        reached_files = tuple(
            AndroidSourceReachedFile(
                source_path=source_path,
                applicability=applicability,
            )
            for source_path, applicability
            in sorted(
                visited.items(),
                key=lambda item: item[0],
            )
        )

        return AndroidSourceRepositoryLineage(
            inventory=inventory,
            reached_files=reached_files,
            relationships=tuple(
                relationships
            ),
            relevance=tuple(
                relevance
            ),
        )

    @staticmethod
    def _record_project_relevance(
        *,
        project_path: str,
        applicability: AndroidSourceRelationshipApplicability,
        active_related: set[str],
        conditional_related: set[str],
    ) -> None:
        if (
            applicability
            is AndroidSourceRelationshipApplicability
            .ACTIVE
        ):
            active_related.add(
                project_path
            )
            conditional_related.discard(
                project_path
            )
            return

        if project_path not in active_related:
            conditional_related.add(
                project_path
            )

    @classmethod
    def _relationships_for_make_file(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        source_project: str,
        path: Path,
    ) -> tuple[
        AndroidSourceRepositoryRelationship,
        ...,
    ]:
        if not path.is_file():
            return ()

        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        logical_statements = []
        buffer = []
        start_line = None
        conditional_depth = 0

        for line_number, raw in enumerate(
            lines,
            start=1,
        ):
            stripped = raw.lstrip()

            if (
                not stripped.startswith("#")
                and _CONDITIONAL_END_RE.match(
                    stripped
                )
            ):
                conditional_depth = max(
                    conditional_depth - 1,
                    0,
                )

            if start_line is None:
                start_line = line_number

            buffer.append(
                raw
            )

            if raw.rstrip().endswith("\\"):
                continue

            logical_statements.append(
                (
                    start_line,
                    tuple(buffer),
                    conditional_depth,
                )
            )

            if (
                not stripped.startswith("#")
                and _CONDITIONAL_START_RE.match(
                    stripped
                )
            ):
                conditional_depth += 1

            buffer = []
            start_line = None

        if buffer:
            logical_statements.append(
                (
                    start_line or len(lines),
                    tuple(buffer),
                    conditional_depth,
                )
            )

        result = []

        for (
            start_line,
            statement_lines,
            conditional_depth,
        ) in logical_statements:
            expression = "\n".join(
                statement_lines
            ).strip()

            if not expression:
                continue

            applicability = (
                cls._statement_applicability(
                    expression=expression,
                    conditional_depth=conditional_depth,
                )
            )

            kind = cls._relationship_kind(
                expression
            )

            if kind is None:
                continue

            references = cls._referenced_paths(
                expression
            )

            evidence_path = (
                path.relative_to(
                    inventory.checkout_root
                ).as_posix()
            )

            for referenced_path in references:
                target_repository = (
                    inventory.repository_for_source_path(
                        referenced_path
                    )
                )

                result.append(
                    AndroidSourceRepositoryRelationship(
                        source_project=source_project,
                        referenced_path=referenced_path,
                        target_project=(
                            None
                            if target_repository is None
                            else target_repository.project_path
                        ),
                        kind=kind,
                        applicability=applicability,
                        evidence_path=evidence_path,
                        evidence_line=start_line,
                        raw_expression=expression,
                    )
                )

        return tuple(
            result
        )

    @staticmethod
    def _statement_applicability(
        *,
        expression: str,
        conditional_depth: int,
    ) -> AndroidSourceRelationshipApplicability:
        stripped = expression.lstrip()

        if stripped.startswith("#"):
            return (
                AndroidSourceRelationshipApplicability
                .COMMENTED
            )

        if (
            "inherit-product-if-exists"
            in expression
            or re.match(
                r"^\s*-include\b",
                expression,
            )
            or conditional_depth > 0
        ):
            return (
                AndroidSourceRelationshipApplicability
                .CONDITIONAL
            )

        return (
            AndroidSourceRelationshipApplicability
            .ACTIVE
        )

    @staticmethod
    def _relationship_kind(
        expression: str,
    ) -> AndroidSourceRelationshipKind | None:
        stripped = expression.lstrip()

        probe = (
            stripped[1:].lstrip()
            if stripped.startswith("#")
            else stripped
        )

        if (
            "inherit-product-if-exists"
            in probe
            or "inherit-product," in probe
        ):
            return (
                AndroidSourceRelationshipKind
                .PRODUCT_INHERIT
            )

        if re.match(
            r"^-?include\s+",
            probe,
        ):
            return (
                AndroidSourceRelationshipKind
                .MAKE_INCLUDE
            )

        if "PRODUCT_SOONG_NAMESPACES" in probe:
            return (
                AndroidSourceRelationshipKind
                .SOONG_NAMESPACE
            )

        if (
            "SEPOLICY_DIRS" in probe
            or "SEPOLICY_DIR" in probe
        ):
            return (
                AndroidSourceRelationshipKind
                .SEPOLICY_INCLUDE
            )

        if "PRODUCT_COPY_FILES" in probe:
            return (
                AndroidSourceRelationshipKind
                .COPY_SOURCE
            )

        if (
            "DEVICE_MANIFEST_FILE" in probe
            or
            "DEVICE_PRODUCT_COMPATIBILITY_MATRIX_FILE"
            in probe
            or "DEVICE_PACKAGE_OVERLAYS" in probe
        ):
            return (
                AndroidSourceRelationshipKind
                .DEVICE_REFERENCE
            )

        return None

    @staticmethod
    def _referenced_paths(
        expression: str,
    ) -> tuple[str, ...]:
        normalized = expression.replace(
            "\\\n",
            " ",
        )

        references = []

        for match in _REFERENCE_RE.finditer(
            normalized
        ):
            candidate = (
                match.group(0)
                .strip()
                .rstrip("\\:,)")
                .lstrip("/")
            )

            if not candidate:
                continue

            references.append(
                candidate
            )

        return tuple(
            sorted(
                set(references)
            )
        )

    @staticmethod
    def _normalize_source_path(
        source_path: str,
    ) -> str | None:
        if (
            not isinstance(
                source_path,
                str,
            )
            or not source_path
        ):
            return None

        if "$" in source_path:
            return None

        candidate = (
            source_path
            .strip()
            .lstrip("/")
            .rstrip("\\:,)")
        )

        if not candidate:
            return None

        parts = Path(
            candidate
        ).parts

        if ".." in parts:
            return None

        return Path(
            *parts
        ).as_posix()

    @classmethod
    def _literal_traversal_target(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        referenced_path: str,
    ) -> str | None:
        """
        Return an exact checkout-relative file that may be traversed.

        Variable-bearing references deliberately remain unresolved. A fixed
        prefix such as device/google_car/ before $(PRODUCT) is useful evidence
        but is not sufficient to choose one concrete build file.
        """

        normalized = cls._normalize_source_path(
            referenced_path
        )

        if normalized is None:
            return None

        physical = (
            inventory.checkout_root
            / normalized
        )

        if not physical.is_file():
            return None

        if (
            inventory.repository_for_source_path(
                normalized
            )
            is None
        ):
            return None

        return normalized

    @staticmethod
    def _combine_applicability(
        *,
        incoming: AndroidSourceRelationshipApplicability,
        edge: AndroidSourceRelationshipApplicability,
    ) -> AndroidSourceRelationshipApplicability:
        if (
            incoming
            is AndroidSourceRelationshipApplicability
            .CONDITIONAL
            or edge
            is AndroidSourceRelationshipApplicability
            .CONDITIONAL
        ):
            return (
                AndroidSourceRelationshipApplicability
                .CONDITIONAL
            )

        return (
            AndroidSourceRelationshipApplicability
            .ACTIVE
        )
