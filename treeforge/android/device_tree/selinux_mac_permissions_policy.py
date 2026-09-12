from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath
from xml.sax.saxutils import escape, quoteattr

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.selinux_derived_source import (
    AndroidDeviceTreeDerivedSelinuxSource,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeMacPermissionsSynthesis:
    """
    Source-equivalent mac_permissions.xml inputs reconstructed from canonical
    factory semantics.

    Platform /system policy remains evidence only.

    For non-system partitions, any complete canonical rule that is
    semantically identical to a canonical platform rule is omitted because
    that semantic population is already supplied by Android platform policy.

    No signer names, certificates, package names, or seinfo values are
    hardcoded.
    """

    sources: tuple[
        AndroidDeviceTreeDerivedSelinuxSource,
        ...,
    ] = ()

    observed_rule_count: int = 0
    platform_rule_count: int = 0
    suppressed_platform_overlap_count: int = 0
    rendered_rule_count: int = 0


class AndroidDeviceTreeMacPermissionsRenderer:
    """
    Reconstruct deterministic Android mac_permissions.xml source inputs.

    Supported source ownership:
      vendor     -> BOARD_VENDOR_SEPOLICY_DIRS
      odm        -> BOARD_ODM_SEPOLICY_DIRS
      product    -> PRODUCT_PRIVATE_SEPOLICY_DIRS
      system_ext -> SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS

    Platform /system mac_permissions remains canonical evidence and defines
    the observed Android platform semantic baseline.

    Semantic subtraction uses complete recursive XML-rule identity. It never
    assumes that a signer, certificate, package, or seinfo value is
    platform-provided merely because of its name.
    """

    _POLICY_SUBDIR_BY_PARTITION = {
        "vendor": ("vendor",),
        "odm": ("odm",),
        "product": ("product", "private"),
        "system_ext": ("system_ext", "private"),
    }

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        identity: AndroidDeviceTreeIdentity,
    ) -> AndroidDeviceTreeMacPermissionsSynthesis:
        from treeforge.android.reconstruction.model import (
            AndroidReconstructionResult,
        )

        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an AndroidReconstructionResult"
            )

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an AndroidDeviceTreeIdentity"
            )

        platform_representations = []
        candidates_by_partition = {}

        for representation in (
            reconstruction.selinux_source_representations
        ):
            if (
                representation.source_kind.value
                != "mac_permissions"
            ):
                continue

            android_path = representation.android_path

            if android_path is None:
                continue

            parts = android_path.parts

            if (
                len(parts) < 5
                or tuple(parts[2:4])
                != ("etc", "selinux")
            ):
                continue

            partition = parts[1]

            if partition == "system":
                platform_representations.append(
                    representation
                )
                continue

            if (
                partition
                not in cls._POLICY_SUBDIR_BY_PARTITION
            ):
                continue

            candidates_by_partition.setdefault(
                partition,
                [],
            ).append(
                representation
            )

        # Canonical platform output defines the observed build-provided
        # semantic baseline. Multiple system observations may contribute
        # baseline rules; semantic identity collapses exact duplicates.
        platform_fingerprints = set()
        platform_rule_count = 0

        for representation in (
            platform_representations
        ):
            requirements = (
                representation
                .mac_permissions_requirements
            )

            platform_rule_count += len(
                requirements
            )

            for requirement in requirements:
                platform_fingerprints.add(
                    cls._fingerprint(
                        requirement.element
                    )
                )

        sources = []
        observed_rule_count = 0
        suppressed_platform_overlap_count = 0
        rendered_rule_count = 0

        for partition in sorted(
            candidates_by_partition
        ):
            representations = (
                candidates_by_partition[
                    partition
                ]
            )

            # Installed mac_permissions output is a merged policy surface.
            # If multiple canonical installed sources map to the same target
            # partition, original source ordering/precedence is not proven.
            if len(representations) != 1:
                continue

            representation = (
                representations[0]
            )

            requirements = (
                representation
                .mac_permissions_requirements
            )

            if not requirements:
                continue

            parsed = (
                representation
                .requirement
                .parsed
            )

            root = (
                parsed.mac_permissions_root
            )

            if root is None or root.name != "policy":
                continue

            observed_rule_count += len(
                requirements
            )

            retained_elements = []

            for requirement in requirements:
                fingerprint = (
                    cls._fingerprint(
                        requirement.element
                    )
                )

                if (
                    fingerprint
                    in platform_fingerprints
                ):
                    suppressed_platform_overlap_count += 1
                    continue

                retained_elements.append(
                    requirement.element
                )

            # An entirely platform-provided installed population does not
            # justify manufacturing an empty device-owned source file.
            if not retained_elements:
                continue

            text = cls._render_policy(
                root,
                tuple(
                    retained_elements
                ),
            )

            destination = (
                PurePosixPath(
                    identity.device_root.as_posix()
                )
                / "sepolicy"
            )

            for component in (
                cls._POLICY_SUBDIR_BY_PARTITION[
                    partition
                ]
            ):
                destination /= component

            destination /= "mac_permissions.xml"

            retained_fingerprints = tuple(
                cls._fingerprint(element)
                for element
                in retained_elements
            )

            identity_seed = "\0".join(
                (
                    representation
                    .requirement
                    .requirement_id,
                    representation
                    .representation_id,
                    destination.as_posix(),
                    sha256(
                        repr(
                            retained_fingerprints
                        ).encode(
                            "utf-8"
                        )
                    ).hexdigest(),
                )
            )

            sources.append(
                AndroidDeviceTreeDerivedSelinuxSource(
                    derived_source_id=(
                        "device-tree-derived-selinux:"
                        + sha256(
                            identity_seed.encode(
                                "utf-8"
                            )
                        ).hexdigest()
                    ),
                    destination=destination,
                    text=text,
                    source_requirement_id=(
                        representation
                        .requirement
                        .requirement_id
                    ),
                    source_representation_id=(
                        representation
                        .representation_id
                    ),
                    contributing_cil_requirement_ids=(),
                )
            )

            rendered_rule_count += len(
                retained_elements
            )

        return AndroidDeviceTreeMacPermissionsSynthesis(
            sources=tuple(
                sorted(
                    sources,
                    key=lambda source: (
                        source.destination.as_posix(),
                        source.source_representation_id,
                    ),
                )
            ),
            observed_rule_count=(
                observed_rule_count
            ),
            platform_rule_count=(
                platform_rule_count
            ),
            suppressed_platform_overlap_count=(
                suppressed_platform_overlap_count
            ),
            rendered_rule_count=(
                rendered_rule_count
            ),
        )

    @classmethod
    def _fingerprint(
        cls,
        element,
    ):
        """
        Return complete semantic XML element identity.

        XML attribute ordering is not semantic, so attributes are sorted.

        Child ordering is retained because policy ordering may be meaningful.

        Formatting-only whitespace text is ignored. Non-whitespace text
        remains part of semantic identity for unknown/future grammar.
        """

        attributes = tuple(
            sorted(
                (
                    attribute.name,
                    attribute.value,
                )
                for attribute
                in element.attributes
            )
        )

        text = element.text

        if not text.strip():
            text = ""

        return (
            element.name,
            attributes,
            text,
            tuple(
                cls._fingerprint(child)
                for child
                in element.children
            ),
        )

    @classmethod
    def _render_policy(
        cls,
        root,
        elements: tuple,
    ) -> str:
        """
        Render deterministic source XML from canonical semantic elements.

        The installed factory XML formatting is not replayed because this is
        a semantic source reconstruction after platform-baseline subtraction.
        """

        root_attributes = "".join(
            " "
            + attribute.name
            + "="
            + quoteattr(
                attribute.value
            )
            for attribute
            in sorted(
                root.attributes,
                key=lambda value: (
                    value.name,
                    value.value,
                ),
            )
        )

        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            f"<{root.name}{root_attributes}>",
        ]

        for element in elements:
            lines.extend(
                cls._render_element(
                    element,
                    level=1,
                )
            )

        lines.append(
            f"</{root.name}>"
        )

        return "\n".join(lines) + "\n"

    @classmethod
    def _render_element(
        cls,
        element,
        *,
        level: int,
    ) -> list[str]:
        indent = "    " * level

        attributes = "".join(
            " "
            + attribute.name
            + "="
            + quoteattr(
                attribute.value
            )
            for attribute
            in sorted(
                element.attributes,
                key=lambda value: (
                    value.name,
                    value.value,
                ),
            )
        )

        meaningful_text = (
            element.text
            if element.text.strip()
            else ""
        )

        if (
            not element.children
            and not meaningful_text
        ):
            return [
                f"{indent}<{element.name}{attributes} />"
            ]

        if not element.children:
            return [
                (
                    f"{indent}"
                    f"<{element.name}{attributes}>"
                    f"{escape(meaningful_text)}"
                    f"</{element.name}>"
                )
            ]

        lines = [
            f"{indent}<{element.name}{attributes}>"
        ]

        if meaningful_text:
            lines.append(
                (
                    "    " * (level + 1)
                    + escape(
                        meaningful_text
                    )
                )
            )

        for child in element.children:
            lines.extend(
                cls._render_element(
                    child,
                    level=level + 1,
                )
            )

        lines.append(
            f"{indent}</{element.name}>"
        )

        return lines


class AndroidDeviceTreeMacPermissionsRealizationPromoter:
    """
    Promote reconstructed mac_permissions.xml source onto the existing
    SELINUX_RUNTIME_OUTPUT realization.

    Canonical requirement identity, Reconstruction representation identity,
    Device Tree realization identity, count, and ordering remain unchanged.
    """

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        synthesis: AndroidDeviceTreeMacPermissionsSynthesis,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> tuple[
        AndroidDeviceTreeBuildRealization,
        ...,
    ]:
        from treeforge.android.reconstruction.model import (
            AndroidReconstructionResult,
        )

        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an AndroidReconstructionResult"
            )

        if not isinstance(
            synthesis,
            AndroidDeviceTreeMacPermissionsSynthesis,
        ):
            raise TypeError(
                "synthesis must be an "
                "AndroidDeviceTreeMacPermissionsSynthesis"
            )

        if not isinstance(
            realizations,
            tuple,
        ):
            raise TypeError(
                "realizations must be a tuple"
            )

        representation_by_id = {
            representation.representation_id:
            representation
            for representation
            in reconstruction.selinux_source_representations
        }

        content_id_by_representation_id = {
            content.representation_id:
            content.content_id
            for content
            in reconstruction.selinux_source_contents
        }

        realization_by_content_id = {}

        for realization in realizations:
            content_id = (
                realization
                .build_representation
                .source_content_id
            )

            if content_id is None:
                continue

            if content_id in realization_by_content_id:
                raise ValueError(
                    "multiple Device Tree realizations identify "
                    "the same SELinux source content"
                )

            realization_by_content_id[
                content_id
            ] = realization

        replacements = {}

        for source in synthesis.sources:
            representation = (
                representation_by_id.get(
                    source.source_representation_id
                )
            )

            if representation is None:
                raise ValueError(
                    "derived mac_permissions source has no matching "
                    "Reconstruction SELinux representation"
                )

            if (
                representation
                .requirement
                .requirement_id
                != source.source_requirement_id
            ):
                raise ValueError(
                    "derived mac_permissions source changed "
                    "canonical requirement identity"
                )

            if (
                representation.source_kind.value
                != "mac_permissions"
            ):
                raise ValueError(
                    "mac_permissions promotion may consume only "
                    "MAC_PERMISSIONS representations"
                )

            content_id = (
                content_id_by_representation_id.get(
                    representation
                    .representation_id
                )
            )

            if content_id is None:
                raise ValueError(
                    "mac_permissions representation has no "
                    "Reconstruction source content"
                )

            existing = (
                realization_by_content_id.get(
                    content_id
                )
            )

            if existing is None:
                raise ValueError(
                    "mac_permissions source content has no "
                    "Device Tree realization"
                )

            if (
                existing
                .build_representation
                .kind
                is not AndroidReconstructionBuildRepresentationKind
                .SELINUX_RUNTIME_OUTPUT
                or existing.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SELINUX_RUNTIME_OUTPUT
                or existing.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .PARTIAL
            ):
                raise ValueError(
                    "mac_permissions promotion expected one PARTIAL "
                    "SELINUX_RUNTIME_OUTPUT realization"
                )

            replacements[
                existing.realization_id
            ] = AndroidDeviceTreeBuildRealization(
                realization_id=(
                    existing.realization_id
                ),
                kind=(
                    AndroidDeviceTreeBuildRealizationKind
                    .SELINUX_POLICY
                ),
                status=(
                    AndroidDeviceTreeBuildRealizationStatus
                    .RESOLVED
                ),
                build_representation=(
                    existing
                    .build_representation
                ),
                source_path=(
                    source.destination
                ),
                module_name=None,
                dependency_realization_ids=(
                    existing
                    .dependency_realization_ids
                ),
                reason=None,
            )

        result = tuple(
            replacements.get(
                realization.realization_id,
                realization,
            )
            for realization
            in realizations
        )

        if tuple(
            realization.representation_id
            for realization in result
        ) != tuple(
            realization.representation_id
            for realization in realizations
        ):
            raise ValueError(
                "mac_permissions promotion changed Device Tree "
                "representation coverage or ordering"
            )

        if len(result) != len(
            realizations
        ):
            raise ValueError(
                "mac_permissions promotion changed realization count"
            )

        return result
