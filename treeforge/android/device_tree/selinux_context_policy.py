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
class AndroidDeviceTreeContextSynthesis:
    """
    Exact source-equivalent Android SELinux context inputs selected from
    canonical runtime observations.

    Multiple observations may prove one effective source population. Device
    Tree materializes exactly one source file for that population and leaves
    aliases attached to their original canonical evidence identities.
    """

    sources: tuple[
        AndroidDeviceTreeDerivedSelinuxSource,
        ...,
    ] = ()


class AndroidDeviceTreeContextRenderer:
    """
    Recover source-equivalent context files for Android partitions with a
    concrete policy source-directory contract.

    Selection is generic and evidence-driven:

    - platform /system policy is never claimed as device-owned source;
    - empty installed outputs do not manufacture empty source inputs;
    - content already represented by a RESOLVED SELinux realization is not
      duplicated;
    - byte-identical aliases collapse to one effective source population;
    - mounted /partition/etc/selinux observations are preferred;
    - ramdisk-root /partition_<kind> observations are fallback evidence.

    The exact canonical bytes are preserved. Context syntax is not rewritten.
    """

    _SOURCE_KINDS = {
        "file_contexts",
        "property_contexts",
        "service_contexts",
        "hwservice_contexts",
        "vndservice_contexts",
        "keystore2_key_contexts",
    }

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
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
    ) -> AndroidDeviceTreeContextSynthesis:
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

        def content_for(representation):
            content = content_by_representation_id.get(
                representation.representation_id
            )

            if content is None:
                raise ValueError(
                    "SELinux context representation has no matching "
                    "Reconstruction source content: "
                    f"{representation.representation_id}"
                )

            return content

        def signature(representation):
            content = content_for(representation)

            return (
                representation.source_kind.value,
                sha256(content.raw_bytes).hexdigest(),
            )

        # Any exact source population already represented by a RESOLVED
        # SELINUX_POLICY realization must not be regenerated from an alias.
        resolved_signatures = set()

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

            matching_content = tuple(
                content
                for content
                in reconstruction.selinux_source_contents
                if content.content_id == content_id
            )

            if len(matching_content) != 1:
                continue

            representation = representation_by_id.get(
                matching_content[0].representation_id
            )

            if representation is None:
                continue

            if (
                representation.source_kind.value
                not in cls._SOURCE_KINDS
            ):
                continue

            resolved_signatures.add(
                signature(representation)
            )

        candidates = []

        for representation in (
            reconstruction.selinux_source_representations
        ):
            source_kind = (
                representation.source_kind.value
            )

            if source_kind not in cls._SOURCE_KINDS:
                continue

            content = content_for(representation)

            if not content.raw_bytes:
                # An empty installed runtime output proves absence of
                # declarations, not a useful source file to manufacture.
                continue

            if content.status.value == "opaque":
                continue

            content_id = content.content_id
            existing = realization_by_content_id.get(
                content_id
            )

            if existing is None:
                raise ValueError(
                    "SELinux context source content has no "
                    "Device Tree realization"
                )

            if (
                existing.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SELINUX_RUNTIME_OUTPUT
                or existing.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .PARTIAL
            ):
                continue

            current_signature = signature(
                representation
            )

            if current_signature in resolved_signatures:
                # Exact alias of a source population already realized.
                continue

            classified = cls._classify_path(
                representation.android_path,
                source_kind=source_kind,
            )

            if classified is None:
                continue

            partition, mounted = classified

            candidates.append(
                (
                    partition,
                    source_kind,
                    current_signature[1],
                    mounted,
                    representation,
                    content,
                )
            )

        # Group equivalent observations by semantic partition, source family,
        # and exact bytes. This prevents root/mounted aliases from becoming
        # duplicate source claims.
        grouped = {}

        for candidate in candidates:
            (
                partition,
                source_kind,
                digest,
                mounted,
                representation,
                content,
            ) = candidate

            key = (
                partition,
                source_kind,
                digest,
            )

            grouped.setdefault(
                key,
                [],
            ).append(candidate)

        sources = []

        for key in sorted(grouped):
            values = grouped[key]

            # Prefer a mounted partition observation. If there are multiple
            # equal-priority observations, deterministic Android path /
            # representation identity ordering selects one without altering
            # their identical source semantics.
            values = sorted(
                values,
                key=lambda item: (
                    0 if item[3] else 1,
                    (
                        item[4].android_path.as_posix()
                        if item[4].android_path is not None
                        else ""
                    ),
                    item[4].representation_id,
                ),
            )

            (
                partition,
                source_kind,
                digest,
                _mounted,
                representation,
                content,
            ) = values[0]

            try:
                text = content.raw_bytes.decode(
                    "utf-8"
                )
            except UnicodeDecodeError:
                # Text context families must remain partial if canonical
                # source bytes are not valid UTF-8.
                continue

            if not text:
                continue

            if not text.endswith("\n"):
                text += "\n"

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

            destination /= source_kind

            identity_seed = "\0".join(
                (
                    representation.requirement.requirement_id,
                    representation.representation_id,
                    destination.as_posix(),
                    digest,
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
                        representation.representation_id
                    ),
                    contributing_cil_requirement_ids=(),
                )
            )

        return AndroidDeviceTreeContextSynthesis(
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

    @classmethod
    def _classify_path(
        cls,
        android_path,
        *,
        source_kind: str,
    ) -> tuple[str, bool] | None:
        if android_path is None:
            return None

        parts = android_path.parts

        # Normal mounted partition form:
        #
        #   /vendor/etc/selinux/vendor_property_contexts
        #   /product/etc/selinux/product_property_contexts
        #   /system_ext/etc/selinux/system_ext_file_contexts
        #
        if len(parts) >= 5:
            partition = parts[1]

            if (
                partition
                in cls._POLICY_SUBDIR_BY_PARTITION
                and tuple(parts[2:4])
                == ("etc", "selinux")
            ):
                return partition, True

            # /system is platform policy and intentionally excluded.
            if partition == "system":
                return None

        # Ramdisk-root aliases:
        #
        #   /vendor_property_contexts
        #   /odm_property_contexts
        #   /product_service_contexts
        #   /system_ext_file_contexts
        #
        if len(parts) == 2:
            name = parts[1]

            for partition in sorted(
                cls._POLICY_SUBDIR_BY_PARTITION,
                key=len,
                reverse=True,
            ):
                expected = (
                    f"{partition}_{source_kind}"
                )

                if name == expected:
                    return partition, False

            # plat_* is platform policy and intentionally excluded.
            if name == f"plat_{source_kind}":
                return None

        return None


class AndroidDeviceTreeContextRealizationPromoter:
    """
    Promote the selected exact source-equivalent context population while
    retaining every duplicate observation as its own canonical evidence.
    """

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        synthesis: AndroidDeviceTreeContextSynthesis,
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
            AndroidDeviceTreeContextSynthesis,
        ):
            raise TypeError(
                "synthesis must be an AndroidDeviceTreeContextSynthesis"
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

        realization_by_content_id = {}

        for realization in realizations:
            content_id = (
                realization
                .build_representation
                .source_content_id
            )

            if content_id is not None:
                realization_by_content_id[
                    content_id
                ] = realization

        replacements = {}

        for source in synthesis.sources:
            representation = representation_by_id.get(
                source.source_representation_id
            )

            if representation is None:
                raise ValueError(
                    "derived context source has no matching "
                    "Reconstruction SELinux representation"
                )

            if (
                representation.requirement.requirement_id
                != source.source_requirement_id
            ):
                raise ValueError(
                    "derived context source changed canonical "
                    "requirement identity"
                )

            content = content_by_representation_id.get(
                representation.representation_id
            )

            if content is None:
                raise ValueError(
                    "derived context source representation has no "
                    "Reconstruction source content"
                )

            existing = realization_by_content_id.get(
                content.content_id
            )

            if existing is None:
                raise ValueError(
                    "derived context source has no Device Tree realization"
                )

            if (
                existing.build_representation.kind
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
                    "context source promotion expected one PARTIAL "
                    "SELINUX_RUNTIME_OUTPUT realization"
                )

            replacements[
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
                    existing.build_representation
                ),
                source_path=source.destination,
                module_name=None,
                dependency_realization_ids=(
                    existing.dependency_realization_ids
                ),
                reason=None,
            )

        result = tuple(
            replacements.get(
                realization.realization_id,
                realization,
            )
            for realization in realizations
        )

        if tuple(
            realization.representation_id
            for realization in result
        ) != tuple(
            realization.representation_id
            for realization in realizations
        ):
            raise ValueError(
                "context source promotion changed Device Tree "
                "representation coverage or ordering"
            )

        if len(result) != len(realizations):
            raise ValueError(
                "context source promotion changed realization count"
            )

        return result
