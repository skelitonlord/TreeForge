from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeSelinuxRuntimeDisposition:
    """
    Final disposition of SELinux runtime/build outputs that do not themselves
    require a new Android source-tree policy file.

    Device Tree keeps every canonical requirement and Reconstruction
    representation identity intact.

    A RESOLVED SELINUX_RUNTIME_OUTPUT means:

      - the installed artifact remains canonical evidence;
      - its Device Tree disposition is known;
      - no additional device-owned source file must be manufactured for that
        particular runtime artifact.

    It does not mean the installed artifact is copied into Android's build as
    SELinux source.
    """

    realizations: tuple[
        AndroidDeviceTreeBuildRealization,
        ...,
    ]

    resolved_counts: tuple[
        tuple[str, int],
        ...,
    ] = ()

    remaining_partial_count: int = 0


class AndroidDeviceTreeSelinuxRuntimeDispositionFinalizer:
    """
    Resolve the non-source remainder of the SELinux realization population.

    Classification precedence is intentional:

      1. compiled policy
      2. empty runtime output
      3. exact alias of an already-realized source population
      4. generated metadata
      5. generated partition CIL / mapping output
      6. Android platform-owned output

    Earlier classes win because one artifact can satisfy more than one
    structural predicate. For example, an empty mapping file is classified as
    empty rather than mapping output, and a byte-identical platform alias is
    classified as an exact alias.

    No device, signer, policy-version, or Android-release value is hardcoded.
    """

    _GENERATED_METADATA_KINDS = {
        "policy_hash",
        "policy_version",
        "genfs_labels_version",
    }

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> AndroidDeviceTreeSelinuxRuntimeDisposition:
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

        content_by_representation_id = {
            content.representation_id:
            content
            for content
            in reconstruction.selinux_source_contents
        }

        content_by_id = {
            content.content_id:
            content
            for content
            in reconstruction.selinux_source_contents
        }

        #
        # Exact semantic/source-equivalent populations that already have a
        # real Android SELinux source realization.
        #
        resolved_policy_digests = set()

        for realization in realizations:
            if (
                realization.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SELINUX_POLICY
                or realization.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            ):
                continue

            content_id = (
                realization
                .build_representation
                .source_content_id
            )

            if content_id is None:
                continue

            content = content_by_id.get(
                content_id
            )

            if content is None:
                continue

            resolved_policy_digests.add(
                sha256(
                    content.raw_bytes
                ).hexdigest()
            )

        replacements = {}
        counts = Counter()

        for realization in realizations:
            if (
                realization.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SELINUX_RUNTIME_OUTPUT
                or realization.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .PARTIAL
            ):
                continue

            build_representation = (
                realization
                .build_representation
            )

            if (
                build_representation.kind
                is not AndroidReconstructionBuildRepresentationKind
                .SELINUX_RUNTIME_OUTPUT
            ):
                continue

            content_id = (
                build_representation
                .source_content_id
            )

            if content_id is None:
                continue

            content = content_by_id.get(
                content_id
            )

            if content is None:
                continue

            representation = (
                representation_by_id.get(
                    content.representation_id
                )
            )

            if representation is None:
                continue

            disposition = cls._classify(
                representation,
                content,
                resolved_policy_digests=(
                    resolved_policy_digests
                ),
            )

            if disposition is None:
                continue

            reason_key, reason = disposition

            counts[reason_key] += 1

            replacements[
                realization.realization_id
            ] = AndroidDeviceTreeBuildRealization(
                realization_id=(
                    realization.realization_id
                ),
                kind=(
                    AndroidDeviceTreeBuildRealizationKind
                    .SELINUX_RUNTIME_OUTPUT
                ),
                status=(
                    AndroidDeviceTreeBuildRealizationStatus
                    .RESOLVED
                ),
                build_representation=(
                    build_representation
                ),
                source_path=(
                    realization.source_path
                ),
                module_name=(
                    realization.module_name
                ),
                dependency_realization_ids=(
                    realization
                    .dependency_realization_ids
                ),
                reason=reason,
            )

        result = tuple(
            replacements.get(
                realization.realization_id,
                realization,
            )
            for realization
            in realizations
        )

        #
        # Coverage and ordering are invariants. This finalizer changes only
        # disposition/status, never canonical realization identity.
        #
        if tuple(
            realization.representation_id
            for realization
            in result
        ) != tuple(
            realization.representation_id
            for realization
            in realizations
        ):
            raise ValueError(
                "SELinux runtime disposition changed Device Tree "
                "representation coverage or ordering"
            )

        if len(result) != len(
            realizations
        ):
            raise ValueError(
                "SELinux runtime disposition changed realization count"
            )

        remaining_partial_count = sum(
            1
            for realization
            in result
            if (
                realization.kind
                is AndroidDeviceTreeBuildRealizationKind
                .SELINUX_RUNTIME_OUTPUT
                and realization.status
                is AndroidDeviceTreeBuildRealizationStatus
                .PARTIAL
            )
        )

        return AndroidDeviceTreeSelinuxRuntimeDisposition(
            realizations=result,
            resolved_counts=tuple(
                sorted(
                    counts.items()
                )
            ),
            remaining_partial_count=(
                remaining_partial_count
            ),
        )

    @classmethod
    def _classify(
        cls,
        representation,
        content,
        *,
        resolved_policy_digests: set[str],
    ) -> tuple[str, str] | None:
        source_kind = (
            representation
            .source_kind
            .value
        )

        android_path = (
            representation.android_path
        )

        #
        # 1. Compiled binary policy is an Android build/runtime result, never
        #    textual device policy source.
        #
        if (
            source_kind
            == "compiled_policy"
            or representation
            .requirement
            .is_compiled_policy
        ):
            return (
                "compiled_policy",
                (
                    "Resolved non-source SELinux output: canonical compiled "
                    "policy is preserved as build/runtime evidence. Android "
                    "policy source compilation owns regeneration; the compiled "
                    "artifact is not admitted as device-tree policy source."
                ),
            )

        #
        # 2. Empty installed outputs prove an empty effective population.
        #    Manufacturing an empty source file is neither necessary nor
        #    semantically stronger evidence.
        #
        if not content.raw_bytes:
            return (
                "empty_output",
                (
                    "Resolved non-source SELinux output: the canonical "
                    "installed artifact is empty. It proves an empty effective "
                    "population and requires no manufactured device-tree "
                    "policy source."
                ),
            )

        digest = sha256(
            content.raw_bytes
        ).hexdigest()

        #
        # 3. Exact aliases are satisfied by an existing Android source policy
        #    population. Keep this observation as separate canonical evidence,
        #    but do not duplicate source.
        #
        if digest in resolved_policy_digests:
            return (
                "exact_source_alias",
                (
                    "Resolved non-source SELinux output: exact canonical bytes "
                    "match a SELinux source population already realized by "
                    "Device Tree. This observation remains independent "
                    "evidence and does not manufacture duplicate policy source."
                ),
            )

        #
        # 4. Hash/version metadata are outputs/evidence of policy generation,
        #    not authored SELinux policy source.
        #
        if (
            source_kind
            in cls._GENERATED_METADATA_KINDS
        ):
            return (
                "generated_metadata",
                (
                    "Resolved non-source SELinux output: canonical policy "
                    "hash/version metadata is generated or validated by the "
                    "Android SELinux build/runtime pipeline. It remains "
                    "evidence and is not device-owned policy source."
                ),
            )

        #
        # 5. Generated CIL surfaces.
        #
        # Compatibility mappings and partition *_sepolicy.cil files are
        # generated effective CIL outputs. plat_pub_versioned.cil is likewise
        # generated platform/vendor interface policy.
        #
        # Do not classify vendor_sepolicy.cil here merely because its name
        # follows *_sepolicy.cil: vendor CIL has a dedicated semantic source
        # synthesis path and must remain a blocker if that synthesis fails.
        #
        if (
            source_kind == "cil"
            and cls._is_generated_cil_output(
                representation
            )
        ):
            return (
                "generated_cil_output",
                (
                    "Resolved non-source SELinux output: canonical effective "
                    "CIL/mapping content is an Android SELinux build output. "
                    "Its semantics remain canonical evidence, while source "
                    "policy is supplied through the already-realized SELinux "
                    "source-policy surfaces."
                ),
            )

        #
        # 6. Platform policy is supplied by Android itself. TreeForge keeps
        #    the factory observation for provenance but must not claim it as
        #    device-owned policy source.
        #
        if cls._is_platform_owned(
            android_path
        ):
            return (
                "platform_owned",
                (
                    "Resolved non-source SELinux output: canonical platform "
                    "SELinux policy is supplied by the Android platform build. "
                    "The factory artifact remains evidence and is intentionally "
                    "not reconstructed as device-owned source."
                ),
            )

        return None

    @classmethod
    def _is_generated_cil_output(
        cls,
        representation,
    ) -> bool:
        path = representation.android_path

        if path is None:
            return False

        parts = path.parts

        if len(parts) < 2:
            return False

        name = parts[-1]

        #
        # Generated platform/vendor compatibility interface.
        #
        if name == "plat_pub_versioned.cil":
            return True

        #
        # Mapping directories are Android-generated compatibility CIL.
        # Empty mappings were already handled by the empty-output class.
        #
        if "mapping" in parts:
            #
            # /system mappings are classified as platform-owned instead of
            # generic partition-generated output, keeping ownership explicit.
            #
            if len(parts) >= 2 and parts[1] == "system":
                return False

            return True

        #
        # Product and system_ext effective partition CIL are generated from
        # their source policy directories. Vendor CIL intentionally has its
        # own semantic synthesizer and is excluded here.
        #
        if len(parts) >= 2:
            partition = parts[1]

            if (
                partition
                in {
                    "product",
                    "system_ext",
                }
                and name
                == f"{partition}_sepolicy.cil"
            ):
                return True

        return False

    @classmethod
    def _is_platform_owned(
        cls,
        android_path,
    ) -> bool:
        if android_path is None:
            return False

        parts = android_path.parts

        #
        # Mounted platform SELinux policy.
        #
        if (
            len(parts) >= 2
            and parts[1] == "system"
        ):
            return True

        #
        # Ramdisk-root platform aliases:
        #   /plat_file_contexts
        #   /plat_property_contexts
        #   ...
        #
        if (
            len(parts) == 2
            and parts[1].startswith(
                "plat_"
            )
        ):
            return True

        return False
