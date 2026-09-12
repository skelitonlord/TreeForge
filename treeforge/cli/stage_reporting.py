from __future__ import annotations

from collections import Counter, defaultdict

from treeforge.android.extraction import (
    AndroidExtractionResult,
    ExtractionOperation,
)


def _artifact_origin_image(
    artifact,
) -> str | None:
    """
    Return the canonical originating factory-image member for one Extraction
    artifact.

    Prefer the ExtractedArtifact model's explicit derived property when
    available. The source-based fallback preserves compatibility with
    snapshots/artifacts created before that convenience property existed.
    """

    origin_image = getattr(
        artifact,
        "origin_image",
        None,
    )

    if origin_image:
        return origin_image

    source = artifact.source

    if source is None:
        return None

    kind = getattr(
        source,
        "kind",
        None,
    )

    if (
        kind is None
        or getattr(
            kind,
            "value",
            None,
        ) != "image"
    ):
        return None

    return source.name


def _artifact_label(
    artifact,
) -> str:
    """
    Return the most specific Extraction-owned human-readable artifact identity.

    Prefer an operation-established relative/archive member identity over the
    broader semantic context inherited from the containing partition.
    """

    facts = {
        fact.name: fact.value
        for fact in artifact.facts
    }

    for fact_name in (
        "relative_path",
        "archive_member",
        "archive_member_path",
        "discovery_member_path",
    ):
        value = facts.get(
            fact_name
        )

        if isinstance(
            value,
            str,
        ) and value.strip():
            return value

    if artifact.operation.value == "filesystem_extraction":
        parent = artifact.parent

        if parent is not None:
            return (
                f"{_artifact_label(parent)} filesystem"
            )

    return (
        artifact.semantic_name
        or artifact.path.name
        or str(artifact.path)
    )


def _render_tool_lines(
    artifact,
) -> list[str]:
    tool = artifact.tool

    if tool is None:
        return [
            "      tool: none",
        ]

    lines = [
        f"      tool: {tool.name}",
        (
            "      executable: "
            f"{tool.executable or 'none'}"
        ),
        (
            "      return code: "
            + (
                str(tool.returncode)
                if tool.returncode is not None
                else "none"
            )
        ),
    ]

    if tool.command:
        lines.append(
            "      command: "
            + " ".join(
                tool.command
            )
        )

    if tool.stdout:
        lines.append(
            (
                "      stdout captured: "
                f"{len(tool.stdout)} characters"
            )
        )

    if tool.stderr:
        lines.append(
            (
                "      stderr captured: "
                f"{len(tool.stderr)} characters"
            )
        )

    return lines


def _render_fact_lines(
    artifact,
) -> list[str]:
    if not artifact.facts:
        return [
            "      facts: none",
        ]

    lines = [
        "      facts:",
    ]

    for fact in sorted(
        artifact.facts,
        key=lambda item: item.name,
    ):
        lines.append(
            (
                f"        {fact.name}: "
                f"{fact.value}"
            )
        )

    return lines


def build_extraction_stage_report_lines(
    extraction: AndroidExtractionResult,
) -> list[str]:
    """
    Render the canonical Extraction-owned reporting surface.

    Later CLI commands that traverse Extraction must consume this reporter
    rather than independently reconstructing Extraction reporting.

    This function reports only facts already owned by canonical Extraction.
    It performs no Parsing or downstream interpretation.

    The report intentionally exposes both Extraction content and lineage so
    later audits can determine not merely what was materialized, but which
    exact factory image each fact ultimately came from.
    """

    if not isinstance(
        extraction,
        AndroidExtractionResult,
    ):
        raise TypeError(
            "extraction must be an AndroidExtractionResult"
        )

    artifacts = tuple(
        extraction.artifacts
    )

    operation_counts = Counter(
        artifact.operation.value
        for artifact in artifacts
    )

    with_source = tuple(
        artifact
        for artifact in artifacts
        if artifact.source is not None
    )

    roots = tuple(
        artifact
        for artifact in artifacts
        if artifact.parent is None
    )

    derived = tuple(
        artifact
        for artifact in artifacts
        if artifact.parent is not None
    )

    with_origin_image = tuple(
        artifact
        for artifact in artifacts
        if _artifact_origin_image(
            artifact
        ) is not None
    )

    image_derived = tuple(
        artifact
        for artifact in artifacts
        if (
            artifact.source is not None
            and getattr(
                getattr(
                    artifact.source,
                    "kind",
                    None,
                ),
                "value",
                None,
            )
            == "image"
        )
    )

    missing_origin_image = tuple(
        artifact
        for artifact in image_derived
        if _artifact_origin_image(
            artifact
        ) is None
    )

    broken_parent_source = tuple(
        artifact
        for artifact in derived
        if (
            artifact.parent is not None
            and artifact.parent.source
            is not artifact.source
        )
    )

    parent_not_retained = tuple(
        artifact
        for artifact in derived
        if (
            artifact.parent is not None
            and not any(
                candidate is artifact.parent
                for candidate in artifacts
            )
        )
    )

    source_groups = defaultdict(
        list
    )

    no_origin = []

    for artifact in artifacts:
        origin_image = (
            _artifact_origin_image(
                artifact
            )
        )

        if origin_image is None:
            no_origin.append(
                artifact
            )
            continue

        source_groups[
            origin_image
        ].append(
            artifact
        )

    kernel_images = (
        extraction.artifacts_for_operation(
            ExtractionOperation.KERNEL_DECOMPRESSION
        )
    )

    ufpk_descriptors = (
        extraction.artifacts_for_operation(
            ExtractionOperation.UFPK_DESCRIPTOR_EXTRACTION
        )
    )

    lines: list[str] = [
        "Extraction lineage coverage:",
        (
            "  Total artifacts: "
            f"{len(artifacts)}"
        ),
        (
            "  Artifacts with Discovery source: "
            f"{len(with_source)}"
        ),
        (
            "  Artifacts with factory origin image: "
            f"{len(with_origin_image)}"
        ),
        (
            "  Root extraction artifacts: "
            f"{len(roots)}"
        ),
        (
            "  Derived extraction artifacts: "
            f"{len(derived)}"
        ),
        (
            "  Origin images represented: "
            f"{len(source_groups)}"
        ),
        (
            "  Image-derived artifacts missing factory origin: "
            f"{len(missing_origin_image)}"
        ),
        (
            "  Parent/source identity mismatches: "
            f"{len(broken_parent_source)}"
        ),
        (
            "  Derived artifacts with unretained parent: "
            f"{len(parent_not_retained)}"
        ),
        (
            "  Lineage integrity: "
            + (
                "PASS"
                if (
                    not missing_origin_image
                    and not broken_parent_source
                    and not parent_not_retained
                )
                else "FAIL"
            )
        ),
        "",
        "Extraction operations:",
    ]

    for operation_name in sorted(
        operation_counts
    ):
        lines.append(
            (
                f"  {operation_name}: "
                f"{operation_counts[operation_name]}"
            )
        )

    lines.extend(
        (
            "",
            "Canonical extraction lineage:",
        )
    )

    for origin_image in sorted(
        source_groups
    ):
        group = tuple(
            source_groups[
                origin_image
            ]
        )

        group_operation_counts = Counter(
            artifact.operation.value
            for artifact in group
        )

        lines.extend(
            (
                "",
                (
                    "Factory origin image: "
                    f"{origin_image}"
                ),
                (
                    "  Artifacts: "
                    f"{len(group)}"
                ),
                (
                    "  Root artifacts: "
                    f"{sum(1 for artifact in group if artifact.parent is None)}"
                ),
                (
                    "  Derived artifacts: "
                    f"{sum(1 for artifact in group if artifact.parent is not None)}"
                ),
                "  Operations:",
            )
        )

        for operation_name in sorted(
            group_operation_counts
        ):
            lines.append(
                (
                    f"    {operation_name}: "
                    f"{group_operation_counts[operation_name]}"
                )
            )

        for index, artifact in enumerate(
            group,
            start=1,
        ):
            source = artifact.source
            parent = artifact.parent

            lines.extend(
                (
                    "",
                    (
                        f"  Artifact {index}: "
                        f"{_artifact_label(artifact)}"
                    ),
                    (
                        "    artifact identity: "
                        f"{_artifact_label(artifact)}"
                    ),
                    (
                        "    semantic context: "
                        f"{artifact.semantic_name or 'none'}"
                    ),
                    (
                        "    kind: "
                        f"{artifact.kind.value}"
                    ),
                    (
                        "    operation: "
                        f"{artifact.operation.value}"
                    ),
                    (
                        "    factory origin image: "
                        f"{origin_image}"
                    ),
                    (
                        "    path: "
                        f"{artifact.path}"
                    ),
                    (
                        "    parent: "
                        + (
                            str(parent.path)
                            if parent is not None
                            else "none"
                        )
                    ),
                    (
                        "    parent identity: "
                        + (
                            _artifact_label(
                                parent
                            )
                            if parent is not None
                            else "none"
                        )
                    ),
                    (
                        "    parent semantic context: "
                        + (
                            str(
                                parent.semantic_name
                                or "none"
                            )
                            if parent is not None
                            else "none"
                        )
                    ),
                    (
                        "    source member: "
                        + (
                            source.name
                            if source is not None
                            else "none"
                        )
                    ),
                    (
                        "    Discovery source identity: "
                        + (
                            source.source_name
                            if source is not None
                            else "none"
                        )
                    ),
                    (
                        "    source classification: "
                        + (
                            source.classification.value
                            if source is not None
                            else "none"
                        )
                    ),
                    (
                        "    size bytes: "
                        + (
                            str(artifact.size_bytes)
                            if artifact.size_bytes is not None
                            else "unknown"
                        )
                    ),
                    (
                        "    SHA-256: "
                        f"{artifact.content_sha256 or 'unavailable'}"
                    ),
                    (
                        "    lineage depth: "
                        f"{len(artifact.lineage) - 1}"
                    ),
                    (
                        "    lineage: "
                        + " -> ".join(
                            _artifact_label(
                                ancestor
                            )
                            for ancestor
                            in artifact.lineage
                        )
                    ),
                    (
                        "    parent source identity preserved: "
                        + (
                            str(
                                parent.source
                                is artifact.source
                            )
                            if parent is not None
                            else "n/a"
                        )
                    ),
                )
            )

            lines.extend(
                _render_fact_lines(
                    artifact
                )
            )

            lines.extend(
                _render_tool_lines(
                    artifact
                )
            )

    lines.extend(
        (
            "",
            "Extraction artifacts without image origin:",
            (
                "  Artifacts: "
                f"{len(no_origin)}"
            ),
        )
    )

    for artifact in no_origin:
        source = artifact.source

        lines.extend(
            (
                (
                    "  Artifact: "
                    f"{_artifact_label(artifact)}"
                ),
                (
                    "    path: "
                    f"{artifact.path}"
                ),
                (
                    "    operation: "
                    f"{artifact.operation.value}"
                ),
                (
                    "    source member: "
                    + (
                        source.name
                        if source is not None
                        else "none"
                    )
                ),
                (
                    "    Discovery source identity: "
                    + (
                        source.source_name
                        if source is not None
                        else "none"
                    )
                ),
            )
        )

    #
    # Retain focused legacy sections. These remain useful summaries while
    # canonical lineage above provides complete Extraction visibility.
    #
    lines.extend(
        (
            "",
            "Kernel materialization:",
            (
                "  Decompressed kernel images: "
                f"{len(kernel_images)}"
            ),
        )
    )

    for artifact in kernel_images:
        facts = {
            fact.name: fact.value
            for fact in artifact.facts
        }

        parent = artifact.parent

        lines.extend(
            (
                (
                    "  Kernel image: "
                    f"{artifact.path}"
                ),
                (
                    "    semantic name: "
                    f"{artifact.semantic_name}"
                ),
                (
                    "    factory origin image: "
                    f"{_artifact_origin_image(artifact) or 'none'}"
                ),
                (
                    "    operation: "
                    f"{artifact.operation.value}"
                ),
                (
                    "    source artifact: "
                    + (
                        str(parent.path)
                        if parent is not None
                        else "none"
                    )
                ),
                (
                    "    compression: "
                    f"{facts.get('compression', 'unknown')}"
                ),
                (
                    "    compressed size: "
                    f"{facts.get('compressed_size_bytes', 'unknown')}"
                ),
                (
                    "    decompressed size: "
                    f"{facts.get('decompressed_size_bytes', 'unknown')}"
                ),
                (
                    "    parent identity preserved: "
                    f"{parent is not None}"
                ),
            )
        )

    lines.extend(
        (
            "",
            "UFPK descriptor regions:",
            (
                "  Materialized descriptors: "
                f"{len(ufpk_descriptors)}"
            ),
        )
    )

    for artifact in ufpk_descriptors:
        facts = {
            fact.name: fact.value
            for fact in artifact.facts
        }

        parent = artifact.parent

        descriptor_offset = facts.get(
            "descriptor_offset"
        )

        field_28 = facts.get(
            "field_28"
        )

        next_offset = facts.get(
            "next_offset"
        )

        physical_end = facts.get(
            "physical_end"
        )

        lines.extend(
            (
                (
                    "  Descriptor: "
                    f"{artifact.semantic_name or artifact.path.name}"
                ),
                (
                    "    artifact: "
                    f"{artifact.path}"
                ),
                (
                    "    factory origin image: "
                    f"{_artifact_origin_image(artifact) or 'none'}"
                ),
                (
                    "    parent: "
                    + (
                        str(parent.path)
                        if parent is not None
                        else "none"
                    )
                ),
                (
                    "    operation: "
                    f"{artifact.operation.value}"
                ),
                (
                    "    descriptor index: "
                    f"{facts.get('descriptor_index', 'unknown')}"
                ),
                (
                    "    descriptor kind: "
                    f"{facts.get('descriptor_kind', 'unknown')}"
                ),
                (
                    "    descriptor offset: "
                    + (
                        f"0x{descriptor_offset:x}"
                        if isinstance(
                            descriptor_offset,
                            int,
                        )
                        else "unknown"
                    )
                ),
                (
                    "    field_28: "
                    + (
                        f"0x{field_28:x}"
                        if isinstance(
                            field_28,
                            int,
                        )
                        else "unknown"
                    )
                ),
                (
                    "    next offset: "
                    + (
                        f"0x{next_offset:x}"
                        if isinstance(
                            next_offset,
                            int,
                        )
                        else "unknown"
                    )
                ),
                (
                    "    physical end: "
                    + (
                        f"0x{physical_end:x}"
                        if isinstance(
                            physical_end,
                            int,
                        )
                        else "unknown"
                    )
                ),
                (
                    "    physical size: "
                    f"{artifact.size_bytes}"
                ),
                (
                    "    SHA-256: "
                    f"{artifact.content_sha256 or 'unavailable'}"
                ),
                (
                    "    parent identity preserved: "
                    f"{parent is not None}"
                ),
            )
        )

    return lines



def _extraction_origin_groups(
    extraction: AndroidExtractionResult,
):
    groups = defaultdict(
        list
    )

    for artifact in extraction.artifacts:
        groups[
            _artifact_origin_image(
                artifact
            )
        ].append(
            artifact
        )

    return groups


def _render_extraction_artifact_detail_lines(
    artifact,
    *,
    index: int,
    origin_image: str | None,
) -> list[str]:
    source = artifact.source
    parent = artifact.parent

    lines = [
        (
            f"Artifact {index}: "
            f"{_artifact_label(artifact)}"
        ),
        (
            "  artifact identity: "
            f"{_artifact_label(artifact)}"
        ),
        (
            "  semantic context: "
            f"{artifact.semantic_name or 'none'}"
        ),
        (
            "  kind: "
            f"{artifact.kind.value}"
        ),
        (
            "  operation: "
            f"{artifact.operation.value}"
        ),
        (
            "  factory origin image: "
            f"{origin_image or 'none'}"
        ),
        (
            "  path: "
            f"{artifact.path}"
        ),
        (
            "  parent: "
            + (
                str(parent.path)
                if parent is not None
                else "none"
            )
        ),
        (
            "  parent identity: "
            + (
                _artifact_label(
                    parent
                )
                if parent is not None
                else "none"
            )
        ),
        (
            "  parent semantic context: "
            + (
                str(
                    parent.semantic_name
                    or "none"
                )
                if parent is not None
                else "none"
            )
        ),
        (
            "  source member: "
            + (
                source.name
                if source is not None
                else "none"
            )
        ),
        (
            "  Discovery source identity: "
            + (
                source.source_name
                if source is not None
                else "none"
            )
        ),
        (
            "  source classification: "
            + (
                source.classification.value
                if source is not None
                else "none"
            )
        ),
        (
            "  size bytes: "
            + (
                str(artifact.size_bytes)
                if artifact.size_bytes is not None
                else "unknown"
            )
        ),
        (
            "  SHA-256: "
            f"{artifact.content_sha256 or 'unavailable'}"
        ),
        (
            "  lineage depth: "
            f"{len(artifact.lineage) - 1}"
        ),
        (
            "  lineage: "
            + " -> ".join(
                _artifact_label(
                    ancestor
                )
                for ancestor
                in artifact.lineage
            )
        ),
        (
            "  parent source identity preserved: "
            + (
                str(
                    parent.source
                    is artifact.source
                )
                if parent is not None
                else "n/a"
            )
        ),
    ]

    for line in _render_fact_lines(
        artifact
    ):
        lines.append(
            line[4:]
            if line.startswith("    ")
            else line
        )

    for line in _render_tool_lines(
        artifact
    ):
        lines.append(
            line[4:]
            if line.startswith("    ")
            else line
        )

    return lines


def build_extraction_origin_report_lines(
    extraction: AndroidExtractionResult,
    origin_image: str | None,
) -> list[str]:
    """
    Render one detailed Extraction report for one factory-origin image.
    """

    if not isinstance(
        extraction,
        AndroidExtractionResult,
    ):
        raise TypeError(
            "extraction must be an AndroidExtractionResult"
        )

    group = tuple(
        artifact
        for artifact
        in extraction.artifacts
        if _artifact_origin_image(
            artifact
        ) == origin_image
    )

    operation_counts = Counter(
        artifact.operation.value
        for artifact in group
    )

    roots = tuple(
        artifact
        for artifact in group
        if artifact.parent is None
    )

    derived = tuple(
        artifact
        for artifact in group
        if artifact.parent is not None
    )

    broken_parent_source = tuple(
        artifact
        for artifact in derived
        if (
            artifact.parent is not None
            and artifact.parent.source
            is not artifact.source
        )
    )

    parent_not_retained = tuple(
        artifact
        for artifact in derived
        if (
            artifact.parent is not None
            and not any(
                candidate is artifact.parent
                for candidate
                in extraction.artifacts
            )
        )
    )

    lines: list[str] = [
        "TreeForge Extraction Factory-Origin Report",
        "",
        (
            "Factory origin image: "
            f"{origin_image or 'none'}"
        ),
        (
            "Artifacts: "
            f"{len(group)}"
        ),
        (
            "Root artifacts: "
            f"{len(roots)}"
        ),
        (
            "Derived artifacts: "
            f"{len(derived)}"
        ),
        (
            "Parent/source identity mismatches: "
            f"{len(broken_parent_source)}"
        ),
        (
            "Derived artifacts with unretained parent: "
            f"{len(parent_not_retained)}"
        ),
        (
            "Lineage integrity: "
            + (
                "PASS"
                if (
                    not broken_parent_source
                    and not parent_not_retained
                )
                else "FAIL"
            )
        ),
        "",
        "Operations:",
    ]

    for operation_name in sorted(
        operation_counts
    ):
        lines.append(
            (
                f"  {operation_name}: "
                f"{operation_counts[operation_name]}"
            )
        )

    lines.extend(
        (
            "",
            "Canonical extraction lineage:",
        )
    )

    for index, artifact in enumerate(
        group,
        start=1,
    ):
        lines.append("")

        lines.extend(
            _render_extraction_artifact_detail_lines(
                artifact,
                index=index,
                origin_image=origin_image,
            )
        )

    return lines


def build_extraction_stage_summary_lines(
    extraction: AndroidExtractionResult,
    *,
    detailed_report_paths: dict[
        str | None,
        str,
    ] | None = None,
) -> list[str]:
    """
    Render concise overall Extraction accounting and per-origin summaries.
    """

    if not isinstance(
        extraction,
        AndroidExtractionResult,
    ):
        raise TypeError(
            "extraction must be an AndroidExtractionResult"
        )

    if detailed_report_paths is None:
        detailed_report_paths = {}

    artifacts = tuple(
        extraction.artifacts
    )

    operation_counts = Counter(
        artifact.operation.value
        for artifact in artifacts
    )

    roots = tuple(
        artifact
        for artifact in artifacts
        if artifact.parent is None
    )

    derived = tuple(
        artifact
        for artifact in artifacts
        if artifact.parent is not None
    )

    with_source = tuple(
        artifact
        for artifact in artifacts
        if artifact.source is not None
    )

    with_origin = tuple(
        artifact
        for artifact in artifacts
        if _artifact_origin_image(
            artifact
        ) is not None
    )

    missing_origin = tuple(
        artifact
        for artifact in artifacts
        if (
            artifact.source is not None
            and getattr(
                getattr(
                    artifact.source,
                    "kind",
                    None,
                ),
                "value",
                None,
            )
            == "image"
            and _artifact_origin_image(
                artifact
            )
            is None
        )
    )

    broken_parent_source = tuple(
        artifact
        for artifact in derived
        if (
            artifact.parent is not None
            and artifact.parent.source
            is not artifact.source
        )
    )

    parent_not_retained = tuple(
        artifact
        for artifact in derived
        if (
            artifact.parent is not None
            and not any(
                candidate is artifact.parent
                for candidate
                in artifacts
            )
        )
    )

    groups = _extraction_origin_groups(
        extraction
    )

    lines: list[str] = [
        "Extraction lineage coverage:",
        (
            "  Total artifacts: "
            f"{len(artifacts)}"
        ),
        (
            "  Artifacts with Discovery source: "
            f"{len(with_source)}"
        ),
        (
            "  Artifacts with factory origin image: "
            f"{len(with_origin)}"
        ),
        (
            "  Root extraction artifacts: "
            f"{len(roots)}"
        ),
        (
            "  Derived extraction artifacts: "
            f"{len(derived)}"
        ),
        (
            "  Origin images represented: "
            f"{len([key for key in groups if key is not None])}"
        ),
        (
            "  Image-derived artifacts missing factory origin: "
            f"{len(missing_origin)}"
        ),
        (
            "  Parent/source identity mismatches: "
            f"{len(broken_parent_source)}"
        ),
        (
            "  Derived artifacts with unretained parent: "
            f"{len(parent_not_retained)}"
        ),
        (
            "  Lineage integrity: "
            + (
                "PASS"
                if (
                    not missing_origin
                    and not broken_parent_source
                    and not parent_not_retained
                )
                else "FAIL"
            )
        ),
        "",
        "Extraction operations:",
    ]

    for operation_name in sorted(
        operation_counts
    ):
        lines.append(
            (
                f"  {operation_name}: "
                f"{operation_counts[operation_name]}"
            )
        )

    lines.extend(
        (
            "",
            "Factory origin images:",
        )
    )

    ordered_keys = sorted(
        origin
        for origin in groups
        if origin is not None
    )

    if None in groups:
        ordered_keys.append(
            None
        )

    for origin_image in ordered_keys:
        group = tuple(
            groups[
                origin_image
            ]
        )

        group_operation_counts = Counter(
            artifact.operation.value
            for artifact in group
        )

        lines.extend(
            (
                "",
                (
                    f"{origin_image or 'no factory origin'}:"
                ),
                (
                    "  Artifacts: "
                    f"{len(group)}"
                ),
                (
                    "  Root artifacts: "
                    f"{sum(1 for artifact in group if artifact.parent is None)}"
                ),
                (
                    "  Derived artifacts: "
                    f"{sum(1 for artifact in group if artifact.parent is not None)}"
                ),
                "  Operations:",
            )
        )

        for operation_name in sorted(
            group_operation_counts
        ):
            lines.append(
                (
                    f"    {operation_name}: "
                    f"{group_operation_counts[operation_name]}"
                )
            )

        report_path = (
            detailed_report_paths.get(
                origin_image
            )
        )

        if report_path is not None:
            lines.extend(
                (
                    "  Detailed report:",
                    f"    {report_path}",
                )
            )

    return lines
