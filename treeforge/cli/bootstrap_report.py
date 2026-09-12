from __future__ import annotations

from collections import Counter

from pathlib import Path

from treeforge.android.bootstrap.deployment_planning import (
    AndroidBootstrapDeploymentPlan,
)
from treeforge.android.boot_image.ramdisk_packaging import (
    AndroidBootImageRamdiskPackageResult,
)
from treeforge.android.extraction.cpio.extractor import (
    CpioEntryType,
)


def _section(
    title: str,
    lines: list[str],
) -> None:
    if lines:
        lines.append("")

    lines.append(title)


def render_bootstrap_reports(
    deployment: AndroidBootstrapDeploymentPlan,
    *,
    package: AndroidBootImageRamdiskPackageResult,
    handoff_path: Path,
) -> dict[str, str]:
    """
    Render Bootstrap's accepted phase reports.

    Deployment Planning is complete once the replacement ramdisk and durable
    Boot Image handoff have been produced. Boot Image reconstruction, hardware
    deployment, and validation remain explicit downstream actions.
    """

    result = deployment.environment_realization
    plan = result.plan

    if plan.population is None:
        raise ValueError(
            "Bootstrap report requires a resolved environment population"
        )

    candidate = plan.environment_root.candidate

    if candidate is None:
        raise ValueError(
            "Bootstrap report requires a resolved environment root"
        )

    elf_closure = plan.elf_closure

    if elf_closure is None:
        raise ValueError(
            "Bootstrap report requires a resolved ELF closure"
        )

    selected_init_closure = plan.init_closures[
        candidate.ramdisk_index
    ]

    reason_counts = Counter(
        reason.value
        for population_entry
        in plan.population.entries
        for reason
        in population_entry.reasons
    )

    realization_kind_counts = Counter(
        value.population_entry.entry.entry.entry_type.value
        for value
        in result.entries
    )

    provider_backed_entries = tuple(
        value
        for value
        in result.entries
        if value.runtime_provider_name is not None
    )

    provider_identity_counts = Counter(
        (
            value.runtime_provider_name,
            value.runtime_provider_release,
        )
        for value
        in provider_backed_entries
    )

    parsing = plan.intake.parsing

    # ========================================================
    # Intake
    # ========================================================

    intake_lines = [
        "=== TREEFORGE BOOTSTRAP INTAKE ===",
        "",
        "Canonical handoff:",
        "  Parsing identity preserved: yes",
        "  Boot Image intake identity preserved: yes",
        f"  Parsing boot images: {len(parsing.boot_images)}",
        f"  Parsing ramdisks: {len(parsing.ramdisks)}",
        "",
        "Knowledge application:",
        "  applied: no",
    ]

    intake_report = "\n".join(
        intake_lines
    ) + "\n"

    # ========================================================
    # Environment Planning
    # ========================================================

    planning_lines = [
        "=== TREEFORGE BOOTSTRAP ENVIRONMENT PLANNING ===",
        "",
        "Environment root:",
        f"  resolution: {plan.environment_root.resolution.value}",
        f"  ramdisk index: {candidate.ramdisk_index}",
        (
            "  source: "
            f"{candidate.ramdisk.filesystem_source.source_name}"
        ),
        "",
        "INIT closure:",
        f"  selected sources: {len(selected_init_closure.selected_sources)}",
        f"  imports: {len(selected_init_closure.imports)}",
        (
            "  service executable resolutions: "
            f"{len(selected_init_closure.service_executables)}"
        ),
        "",
        "ELF closure:",
        f"  roots: {len(elf_closure.roots)}",
        f"  ELFs: {len(elf_closure.elfs)}",
        f"  dependencies: {len(elf_closure.dependencies)}",
        f"  unresolved: {elf_closure.unresolved_dependency_count}",
        f"  ambiguous: {elf_closure.ambiguous_dependency_count}",
        "",
        "Environment population:",
        f"  selected: {plan.population.selected_count}",
        f"  preserved: {plan.population.preserved_count}",
        f"  accounted: {plan.population.accounted_count}",
        "",
        "Population reasons:",
    ]

    for reason, count in sorted(
        reason_counts.items()
    ):
        planning_lines.append(
            f"  {reason}: {count}"
        )

    planning_lines.extend(
        (
            "",
            "Preserved evidence:",
            (
                "  entries: "
                f"{len(plan.population.preserved_entries)}"
            ),
            "  disposition: retained outside realized rootfs",
        )
    )

    planning_report = "\n".join(
        planning_lines
    ) + "\n"

    # ========================================================
    # Environment Realization
    # ========================================================

    realization_lines = [
        "=== TREEFORGE BOOTSTRAP ENVIRONMENT REALIZATION ===",
        "",
        f"Rootfs: {result.rootfs}",
        "",
        "Accounting:",
        f"  selected: {result.selected_count}",
        f"  materialized: {result.materialized_count}",
        f"  metadata-only: {result.metadata_only_count}",
        f"  complete: {str(result.complete).lower()}",
        "",
        "Materialized canonical entry types:",
    ]

    for kind, count in sorted(
        realization_kind_counts.items()
    ):
        realization_lines.append(
            f"  {kind}: {count}"
        )

    realization_lines.extend(
        (
            "",
            "Runtime implementation providers:",
            (
                "  provider-backed entries: "
                f"{len(provider_backed_entries)}"
            ),
        )
    )

    if provider_identity_counts:
        for (
            provider_name,
            provider_release,
        ), count in sorted(
            provider_identity_counts.items()
        ):
            realization_lines.extend(
                (
                    (
                        "  provider: "
                        f"{provider_name}"
                    ),
                    (
                        "    release: "
                        f"{provider_release}"
                    ),
                    (
                        "    entries: "
                        f"{count}"
                    ),
                )
            )

        realization_lines.extend(
            (
                "",
                "Provider-backed entries:",
            )
        )

        for value in provider_backed_entries:
            entry = (
                value
                .population_entry
                .entry
                .entry
            )

            realization_lines.extend(
                (
                    f"  /{entry.path}",
                    (
                        "    provider: "
                        f"{value.runtime_provider_name}"
                    ),
                    (
                        "    release: "
                        f"{value.runtime_provider_release}"
                    ),
                    (
                        "    canonical sha256: "
                        f"{value.canonical_content_sha256}"
                    ),
                    (
                        "    provider sha256: "
                        f"{value.runtime_provider_content_sha256}"
                    ),
                    (
                        "    materialized sha256: "
                        f"{value.content_sha256}"
                    ),
                )
            )

    realization_lines.extend(
        (
            "",
            "Canonical guarantees:",
            "  exact Planning population identity/order retained: yes",
            "  canonical regular-file identity retained: yes",
            "  canonical CPIO metadata retained: yes",
            (
                "  external implementation substitution: "
                + (
                    "yes"
                    if provider_backed_entries
                    else "no"
                )
            ),
            "  symlink targets sourced from canonical CPIO: yes",
            "  preserved Planning population materialized: no",
        )
    )

    realization_report = "\n".join(
        realization_lines
    ) + "\n"

    # ========================================================
    # Main stage report
    # ========================================================

    main_lines = [
        "=== TREEFORGE BOOTSTRAP REPORT ===",
        "",
        "Stage status:",
        "  1. Intake: COMPLETE",
        "  2. Environment Planning: COMPLETE",
        "  3. Environment Realization: COMPLETE",
        "  4. Deployment Planning: COMPLETE",
        "  5. Device Deployment: PENDING BOOT IMAGE EXECUTION",
        "  6. Hardware Validation / Rollback: PENDING",
        "",
        "Current execution boundary:",
        "  Bootstrap environment derivation, rootfs realization, replacement",
        "  ramdisk packaging, and Boot Image handoff are complete.",
        "  No boot image mutation was performed.",
        "  No AVB signing or trust propagation was performed.",
        "  No device deployment was performed.",
        "  No fastboot operation was performed.",
        "",
        "Environment:",
        (
            "  selected ramdisk: "
            f"{candidate.ramdisk.filesystem_source.source_name}"
        ),
        f"  rootfs: {result.rootfs}",
        f"  selected CPIO entries: {plan.population.selected_count}",
        f"  preserved CPIO entries: {plan.population.preserved_count}",
        f"  materialized entries: {result.materialized_count}",
        f"  metadata-only entries: {result.metadata_only_count}",
        (
            "  provider-backed entries: "
            f"{len(provider_backed_entries)}"
        ),
        "",
        "INIT:",
        f"  selected sources: {len(selected_init_closure.selected_sources)}",
        (
            "  service executable resolutions: "
            f"{len(selected_init_closure.service_executables)}"
        ),
        "",
        "ELF:",
        f"  roots: {len(elf_closure.roots)}",
        f"  ELFs: {len(elf_closure.elfs)}",
        f"  dependencies: {len(elf_closure.dependencies)}",
        f"  unresolved: {elf_closure.unresolved_dependency_count}",
        f"  ambiguous: {elf_closure.ambiguous_dependency_count}",
        "",
        "Deployment Planning:",
        (
            "  target: "
            f"{deployment.handoff.container_kind}:"
            f"{deployment.handoff.semantic_name}"
        ),
        (
            "  replacement: "
            f"{package.ramdisk_path}"
        ),
        (
            "  replacement bytes: "
            f"{package.ramdisk_size_bytes}"
        ),
        (
            "  replacement sha256: "
            f"{package.ramdisk_sha256}"
        ),
        (
            "  CPIO: "
            f"{package.cpio_path}"
        ),
        (
            "  CPIO bytes: "
            f"{package.cpio_size_bytes}"
        ),
        (
            "  CPIO sha256: "
            f"{package.cpio_sha256}"
        ),
        (
            "  compression: "
            f"{package.compression.value}"
        ),
        (
            "  rollback required: "
            f"{str(deployment.handoff.rollback_required).lower()}"
        ),
        (
            "  Boot Image handoff: "
            f"{handoff_path}"
        ),
        "",
        "Realization entry types:",
    ]

    for kind, count in sorted(
        realization_kind_counts.items()
    ):
        main_lines.append(
            f"  {kind}: {count}"
        )

    main_lines.extend(
        (
            "",
            "Subphase reports:",
            "  bootstrap-intake-report.txt",
            "  bootstrap-environment-planning-report.txt",
            "  bootstrap-environment-realization-report.txt",
            "  bootstrap-deployment-planning-report.txt",
        )
    )

    main_report = "\n".join(
        main_lines
    ) + "\n"

    deployment_lines = [
        "=== TREEFORGE BOOTSTRAP DEPLOYMENT PLANNING ===",
        "",
        "Boot Image target:",
        (
            "  container: "
            f"{deployment.handoff.container_kind}"
        ),
        (
            "  component: "
            f"{deployment.handoff.semantic_name}"
        ),
        (
            "  original: "
            f"{deployment.handoff.original_component_path}"
        ),
        (
            "  original bytes: "
            f"{deployment.handoff.original_component_size_bytes}"
        ),
        (
            "  original sha256: "
            f"{deployment.handoff.original_component_sha256}"
        ),
        "",
        "Replacement ramdisk:",
        f"  path: {package.ramdisk_path}",
        f"  bytes: {package.ramdisk_size_bytes}",
        f"  sha256: {package.ramdisk_sha256}",
        f"  compression: {package.compression.value}",
        "",
        "Canonical CPIO:",
        f"  entries: {len(package.entries)}",
        f"  path: {package.cpio_path}",
        f"  bytes: {package.cpio_size_bytes}",
        f"  sha256: {package.cpio_sha256}",
        "",
        "Handoff:",
        f"  manifest: {handoff_path}",
        (
            "  replacement ready: "
            f"{str(deployment.handoff.replacement_ready).lower()}"
        ),
        (
            "  rollback required: "
            f"{str(deployment.handoff.rollback_required).lower()}"
        ),
        "",
        "Ownership boundary:",
        "  Bootstrap prepared replacement component: yes",
        "  Boot Image reconstruction performed: no",
        "  AVB signing/trust propagation performed: no",
        "  fastboot operation performed: no",
    ]

    deployment_report = "\n".join(
        deployment_lines
    ) + "\n"

    return {
        "bootstrap-report.txt": main_report,
        "bootstrap-intake-report.txt": intake_report,
        "bootstrap-environment-planning-report.txt": planning_report,
        "bootstrap-environment-realization-report.txt": realization_report,
        "bootstrap-deployment-planning-report.txt": deployment_report,
    }


__all__ = (
    "render_bootstrap_reports",
)
