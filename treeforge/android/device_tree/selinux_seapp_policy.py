from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath

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
class AndroidDeviceTreeSeappSynthesis:
    """
    Exact source-equivalent seapp_contexts inputs recovered from canonical
    installed text.

    Each source preserves one exact Reconstruction SELinux representation.
    No seapp selector semantics are reinterpreted here.
    """

    sources: tuple[
        AndroidDeviceTreeDerivedSelinuxSource,
        ...,
    ] = ()


class AndroidDeviceTreeSeappRenderer:
    """
    Recover source-equivalent seapp_contexts files for Android partitions
    that expose a real source-policy directory contract.

    Supported generic source ownership:
      vendor     -> BOARD_VENDOR_SEPOLICY_DIRS
      odm        -> BOARD_ODM_SEPOLICY_DIRS
      product    -> PRODUCT_PRIVATE_SEPOLICY_DIRS
      system_ext -> SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS

    Platform /system seapp output is intentionally not claimed as
    device-tree-owned source.

    Multiple seapp_contexts runtime sources in the same partition are left
    unpromoted because their original source-directory precedence cannot be
    inferred safely from the merged installed result alone.
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
    ) -> AndroidDeviceTreeSeappSynthesis:
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

        candidates_by_partition = {}

        for representation in (
            reconstruction.selinux_source_representations
        ):
            if representation.source_kind.value != "seapp_contexts":
                continue

            android_path = representation.android_path

            if android_path is None:
                continue

            parts = android_path.parts

            if len(parts) < 4:
                continue

            partition = parts[1]

            if (
                partition
                not in cls._POLICY_SUBDIR_BY_PARTITION
            ):
                # /system platform policy remains runtime evidence.
                continue

            if tuple(parts[2:4]) != ("etc", "selinux"):
                continue

            candidates_by_partition.setdefault(
                partition,
                [],
            ).append(
                representation
            )

        content_by_representation_id = {
            content.representation_id: content
            for content
            in reconstruction.selinux_source_contents
        }

        sources = []

        for partition in sorted(
            candidates_by_partition
        ):
            representations = (
                candidates_by_partition[partition]
            )

            # Source-directory ordering is semantically meaningful for
            # seapp_contexts. Do not manufacture an ordering if more than
            # one installed source maps to the same partition.
            if len(representations) != 1:
                continue

            representation = representations[0]
            requirement = representation.requirement
            parsed = requirement.parsed

            if not representation.seapp_requirements:
                continue

            if parsed.unparsed_lines:
                continue

            content = content_by_representation_id.get(
                representation.representation_id
            )

            if content is None:
                raise ValueError(
                    "canonical seapp_contexts representation has no "
                    "matching Reconstruction source content: "
                    f"{representation.representation_id}"
                )

            if content.status.value == "opaque":
                continue

            try:
                text = content.raw_bytes.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                continue

            if not text:
                continue

            if not text.endswith("\n"):
                text += "\n"

            subdirs = (
                cls._POLICY_SUBDIR_BY_PARTITION[
                    partition
                ]
            )

            destination = (
                PurePosixPath(
                    identity.device_root.as_posix()
                )
                / "sepolicy"
            )

            for subdir in subdirs:
                destination /= subdir

            destination /= "seapp_contexts"

            identity_seed = "\0".join(
                (
                    representation.requirement.requirement_id,
                    representation.representation_id,
                    destination.as_posix(),
                    sha256(content.raw_bytes).hexdigest(),
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
                        requirement.requirement_id
                    ),
                    source_representation_id=(
                        representation.representation_id
                    ),
                    contributing_cil_requirement_ids=(),
                )
            )

        return AndroidDeviceTreeSeappSynthesis(
            sources=tuple(
                sorted(
                    sources,
                    key=lambda source: (
                        source.destination.as_posix(),
                        source.source_representation_id,
                    ),
                )
            )
        )


class AndroidDeviceTreeSeappRealizationPromoter:
    """
    Promote exact source-equivalent seapp_contexts files onto their existing
    Device Tree SELINUX_RUNTIME_OUTPUT realizations.

    No new Reconstruction representation or canonical obligation is created.
    """

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        synthesis: AndroidDeviceTreeSeappSynthesis,
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
            AndroidDeviceTreeSeappSynthesis,
        ):
            raise TypeError(
                "synthesis must be an AndroidDeviceTreeSeappSynthesis"
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

        replacement_by_realization_id = {}

        for source in synthesis.sources:
            representation = representation_by_id.get(
                source.source_representation_id
            )

            if representation is None:
                raise ValueError(
                    "derived seapp_contexts source has no matching "
                    "Reconstruction SELinux representation: "
                    f"{source.source_representation_id}"
                )

            if (
                representation.requirement.requirement_id
                != source.source_requirement_id
            ):
                raise ValueError(
                    "derived seapp_contexts source changed "
                    "canonical requirement identity"
                )

            if (
                representation.source_kind.value
                != "seapp_contexts"
            ):
                raise ValueError(
                    "seapp realization promotion may consume only "
                    "SEAPP_CONTEXTS representations"
                )

            content_id = (
                content_id_by_representation_id.get(
                    representation.representation_id
                )
            )

            if content_id is None:
                raise ValueError(
                    "seapp_contexts representation has no "
                    "Reconstruction source content"
                )

            existing = realization_by_content_id.get(
                content_id
            )

            if existing is None:
                raise ValueError(
                    "seapp_contexts source content has no "
                    "Device Tree realization"
                )

            build_representation = (
                existing.build_representation
            )

            if (
                build_representation.kind
                is not AndroidReconstructionBuildRepresentationKind
                .SELINUX_RUNTIME_OUTPUT
            ):
                raise ValueError(
                    "seapp_contexts promotion expected a "
                    "SELINUX_RUNTIME_OUTPUT Reconstruction representation"
                )

            if (
                existing.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SELINUX_RUNTIME_OUTPUT
                or existing.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .PARTIAL
            ):
                raise ValueError(
                    "seapp_contexts promotion expected one PARTIAL "
                    "SELINUX_RUNTIME_OUTPUT Device Tree realization"
                )

            replacement_by_realization_id[
                existing.realization_id
            ] = AndroidDeviceTreeBuildRealization(
                realization_id=existing.realization_id,
                kind=(
                    AndroidDeviceTreeBuildRealizationKind
                    .SELINUX_POLICY
                ),
                status=(
                    AndroidDeviceTreeBuildRealizationStatus
                    .RESOLVED
                ),
                build_representation=(
                    build_representation
                ),
                source_path=source.destination,
                module_name=None,
                dependency_realization_ids=(
                    existing.dependency_realization_ids
                ),
                reason=None,
            )

        result = tuple(
            replacement_by_realization_id.get(
                realization.realization_id,
                realization,
            )
            for realization in realizations
        )

        before_ids = tuple(
            realization.representation_id
            for realization in realizations
        )

        after_ids = tuple(
            realization.representation_id
            for realization in result
        )

        if before_ids != after_ids:
            raise ValueError(
                "seapp_contexts promotion changed Device Tree "
                "representation coverage or ordering"
            )

        if len(result) != len(realizations):
            raise ValueError(
                "seapp_contexts promotion changed realization count"
            )

        return result
