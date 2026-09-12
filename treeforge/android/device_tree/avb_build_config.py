from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.native_boot_build import (
    AndroidDeviceTreeNativeBootBuildPlan,
)
from treeforge.android.parsing.avb.model import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
    AndroidParsedAvbKernelCmdlineDescriptor,
    AndroidParsedAvbPropertyDescriptor,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)

from treeforge.android.version.device_tree.avb_signing import (
    AndroidDeviceTreeAvbSigningProfile,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeAvbExternalKey:
    partition_name: str
    destination: PurePosixPath
    algorithm: str

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.partition_name,
                str,
            )
            or not self.partition_name
        ):
            raise ValueError(
                "partition_name must be non-empty"
            )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if (
            not isinstance(
                self.algorithm,
                str,
            )
            or not self.algorithm
        ):
            raise ValueError(
                "algorithm must be non-empty"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeAvbChainConfig:
    owner_partition_name: str
    target_partition_name: str

    rollback_index_location: int
    target_rollback_index: int
    target_algorithm: str

    key_path: PurePosixPath


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeAvbDescriptorProvider:
    """
    One direct-auth descriptor Android cannot obtain through its normal
    installed-image list.

    TreeForge validates the canonical source bytes now.

    The generated AndroidBoard.mk lets AOSP avbtool produce the temporary
    descriptor-bearing image during the Android build. TreeForge does not
    encode AVB descriptors itself.
    """

    owner_partition_name: str
    partition_name: str

    source_path: Path
    source_destination: PurePosixPath

    image_size: int

    hash_algorithm: str
    salt: bytes
    canonical_digest: bytes

    flags: int

    provider_target: str

    source_is_native_pvmfw: bool = False

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not isinstance(
            self.source_destination,
            PurePosixPath,
        ):
            raise TypeError(
                "source_destination must be a PurePosixPath"
            )

        if (
            isinstance(
                self.image_size,
                bool,
            )
            or not isinstance(
                self.image_size,
                int,
            )
            or self.image_size <= 0
        ):
            raise ValueError(
                "image_size must be a positive int"
            )

        if not isinstance(
            self.salt,
            bytes,
        ):
            raise TypeError(
                "salt must be bytes"
            )

        if not isinstance(
            self.canonical_digest,
            bytes,
        ):
            raise TypeError(
                "canonical_digest must be bytes"
            )

        if self.flags not in {
            0,
            1,
        }:
            raise ValueError(
                "unsupported canonical AVB hash-descriptor flags"
            )

        if (
            not isinstance(
                self.provider_target,
                str,
            )
            or not self.provider_target
        ):
            raise ValueError(
                "provider_target must be non-empty"
            )

        if not isinstance(
            self.source_is_native_pvmfw,
            bool,
        ):
            raise TypeError(
                "source_is_native_pvmfw must be bool"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeAvbNodeConfig:
    partition_name: str
    requirement_id: str

    algorithm: str
    rollback_index: int
    flags: int

    direct_partitions: tuple[
        str,
        ...,
    ]

    android_member_partitions: tuple[
        str,
        ...,
    ]

    explicit_properties: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]

    regenerated_property_keys: tuple[
        str,
        ...,
    ]

    kernel_cmdlines: tuple[
        str,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeAvbBuildPlan:
    device_root: PurePosixPath

    root_partition_name: str
    rollback_index_expression: str

    nodes: tuple[
        AndroidDeviceTreeAvbNodeConfig,
        ...,
    ]

    chains: tuple[
        AndroidDeviceTreeAvbChainConfig,
        ...,
    ]

    external_keys: tuple[
        AndroidDeviceTreeAvbExternalKey,
        ...,
    ]

    descriptor_providers: tuple[
        AndroidDeviceTreeAvbDescriptorProvider,
        ...,
    ]

    source_equivalence_promotion_count: int = 0
    imported_boot_image_vbmeta_count: int = 0
    development_key_count: int = 0
    aosp_checkout_dependency_count: int = 0
    treeforge_image_builder_count: int = 0
    treeforge_vbmeta_encoder_count: int = 0

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.device_root,
            PurePosixPath,
        ):
            raise TypeError(
                "device_root must be a PurePosixPath"
            )

        if (
            not isinstance(self.rollback_index_expression, str)
            or not self.rollback_index_expression
            or self.rollback_index_expression.strip()
            != self.rollback_index_expression
        ):
            raise ValueError(
                "rollback_index_expression must be a normalized "
                "non-empty string"
            )

        for name, values, value_type in (
            (
                "nodes",
                self.nodes,
                AndroidDeviceTreeAvbNodeConfig,
            ),
            (
                "chains",
                self.chains,
                AndroidDeviceTreeAvbChainConfig,
            ),
            (
                "external_keys",
                self.external_keys,
                AndroidDeviceTreeAvbExternalKey,
            ),
            (
                "descriptor_providers",
                self.descriptor_providers,
                AndroidDeviceTreeAvbDescriptorProvider,
            ),
        ):
            if (
                not isinstance(
                    values,
                    tuple,
                )
                or not all(
                    isinstance(
                        value,
                        value_type,
                    )
                    for value in values
                )
            ):
                raise TypeError(
                    f"{name} contains an invalid model"
                )

        for name, value in (
            (
                "source_equivalence_promotion_count",
                self.source_equivalence_promotion_count,
            ),
            (
                "imported_boot_image_vbmeta_count",
                self.imported_boot_image_vbmeta_count,
            ),
            (
                "development_key_count",
                self.development_key_count,
            ),
            (
                "aosp_checkout_dependency_count",
                self.aosp_checkout_dependency_count,
            ),
            (
                "treeforge_image_builder_count",
                self.treeforge_image_builder_count,
            ),
            (
                "treeforge_vbmeta_encoder_count",
                self.treeforge_vbmeta_encoder_count,
            ),
        ):
            if value != 0:
                raise ValueError(
                    f"{name} must remain zero"
                )

    @property
    def board_config_path(
        self,
    ) -> PurePosixPath:
        return (
            self.device_root
            / "avb"
            / "BoardConfig.mk"
        )

    @property
    def android_board_path(
        self,
    ) -> PurePosixPath:
        return (
            self.device_root
            / "AndroidBoard.mk"
        )

    @property
    def static_source_inputs(
        self,
    ) -> tuple[
        AndroidDeviceTreeAvbDescriptorProvider,
        ...,
    ]:
        return tuple(
            item
            for item in self.descriptor_providers
            if not item.source_is_native_pvmfw
        )

    @property
    def complete(
        self,
    ) -> bool:
        return (
            self.root_partition_name == "vbmeta"
            and {
                node.partition_name
                for node in self.nodes
            }
            == {
                "vbmeta",
                "vbmeta_system",
                "vbmeta_vendor",
            }
            and {
                key.partition_name
                for key in self.external_keys
            }
            == {
                "boot",
                "init_boot",
                "vbmeta",
                "vbmeta_system",
                "vbmeta_vendor",
            }
        )

    def node_for_requirement_id(
        self,
        requirement_id: str,
    ) -> AndroidDeviceTreeAvbNodeConfig | None:
        matches = tuple(
            node
            for node in self.nodes
            if (
                node.requirement_id
                == requirement_id
            )
        )

        if len(matches) > 1:
            raise ValueError(
                "duplicate AVB node requirement identity"
            )

        return (
            matches[0]
            if matches
            else None
        )


class AndroidDeviceTreeAvbBuildProjector:
    """
    Map canonical AVB topology onto Android's existing AVB build machinery.

    TreeForge does not:
    - create final VBMeta images;
    - add final AVB footers;
    - encode VBMeta descriptors in Python;
    - infer private signing keys;
    - select development/test keys;
    - inspect an AOSP checkout at generation time.

    AOSP make/avbtool owns those operations during the Android build.
    """

    _ALGORITHMS = {
        0: "NONE",
        1: "SHA256_RSA2048",
        2: "SHA256_RSA4096",
        3: "SHA256_RSA8192",
        4: "SHA512_RSA2048",
        5: "SHA512_RSA4096",
        6: "SHA512_RSA8192",
    }

    _AOSP_AUTOMATIC_DIRECT_PARTITIONS = frozenset(
        {
            "boot",
            "cache",
            "dtbo",
            "init_boot",
            "odm",
            "odm_dlkm",
            "product",
            "recovery",
            "system",
            "system_dlkm",
            "system_ext",
            "system_other",
            "userdata",
            "vendor",
            "vendor_boot",
            "vendor_dlkm",
            "vendor_kernel_boot",
            "pvmfw",
        }
    )

    @classmethod
    def _algorithm(
        cls,
        value: int,
    ) -> str:
        result = (
            cls._ALGORITHMS.get(
                value
            )
        )

        if result is None:
            raise ValueError(
                "unsupported canonical AVB algorithm type: "
                f"{value}"
            )

        return result

    @staticmethod
    def _key_path(
        identity: AndroidDeviceTreeIdentity,
        partition_name: str,
    ) -> PurePosixPath:
        return (
            PurePosixPath(
                identity.device_root.as_posix()
            )
            / "keys"
            / "avb"
            / f"{partition_name}.pem"
        )

    @staticmethod
    def _embedded_target_requirement(
        reconstruction: AndroidReconstructionResult,
        partition_name: str,
    ):
        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        direct = tuple(
            item
            for item in universe.vbmeta_requirements
            if (
                item.partition_name
                == partition_name
            )
        )

        if len(direct) == 1:
            return direct[0]

        compositions = tuple(
            composition
            for composition
            in reconstruction.boot_image_compositions
            if (
                composition
                .requirement
                .partition
                .name
                == partition_name
            )
        )

        if len(compositions) != 1:
            raise ValueError(
                "cannot map AVB chain target to canonical "
                "boot composition: "
                f"{partition_name}"
            )

        composition = (
            compositions[0]
        )

        embedded = tuple(
            item
            for item in universe.vbmeta_requirements
            if (
                item.is_embedded
                and (
                    item.container_artifact
                    is composition.image_artifact
                    or (
                        item
                        .container_artifact
                        .path
                        == composition
                        .image_artifact
                        .path
                    )
                )
            )
        )

        if len(embedded) != 1:
            raise ValueError(
                "AVB chain target must map to exactly one "
                "embedded canonical VBMeta source: "
                f"{partition_name}"
            )

        return embedded[0]

    @classmethod
    def _bootloader_artifact_for_partition(
        cls,
        universe,
        partition_name: str,
        *,
        descriptor: AndroidParsedAvbHashDescriptor,
    ) -> Path | None:
        """
        Resolve one authenticated firmware payload from every canonical
        extraction/provenance surface for the partition.

        Multiple host paths are legitimate when Extraction preserved the same
        firmware bytes through more than one canonical container/provenance
        path, for example FBPK and normalized firmware-payload extraction.

        Host pathname is therefore not firmware identity.

        The parsed AVB hash descriptor is authoritative for the bytes Device
        Tree needs. Every candidate is tested against that descriptor. If
        multiple candidates authenticate successfully, they are equivalent
        for this AVB construction requirement and one deterministic path may
        be used as the materialization source without discarding upstream
        provenance.
        """

        if not isinstance(
            descriptor,
            AndroidParsedAvbHashDescriptor,
        ):
            raise TypeError(
                "descriptor must be an "
                "AndroidParsedAvbHashDescriptor"
            )

        if (
            descriptor.partition_name
            != partition_name
        ):
            raise ValueError(
                "AVB descriptor partition identity does not "
                "match requested firmware partition: "
                f"requested={partition_name!r}, "
                f"descriptor={descriptor.partition_name!r}"
            )

        population = (
            universe.bootloader_population
        )

        if population is None:
            return None

        candidates = []

        for entry in population.entries:
            artifact = (
                entry.source.artifact
            )

            names = set()

            semantic_name = (
                artifact.semantic_name
            )

            if (
                isinstance(
                    semantic_name,
                    str,
                )
                and semantic_name
            ):
                names.add(
                    semantic_name.lower()
                )

                names.add(
                    Path(
                        semantic_name
                    ).stem.lower()
                )

            names.add(
                artifact.path.name.lower()
            )

            names.add(
                artifact.path.stem.lower()
            )

            if (
                partition_name.lower()
                not in names
            ):
                continue

            candidate = (
                artifact.path.resolve()
            )

            if (
                candidate
                not in candidates
            ):
                candidates.append(
                    candidate
                )

        if not candidates:
            return None

        authenticated = []
        rejected = []

        for candidate in candidates:
            try:
                cls._verify_hash_source(
                    source_path=candidate,
                    descriptor=descriptor,
                )

            except ValueError as error:
                rejected.append(
                    (
                        candidate,
                        str(error),
                    )
                )

                continue

            authenticated.append(
                candidate
            )

        if not authenticated:
            rejected_summary = tuple(
                (
                    source.as_posix(),
                    reason,
                )
                for source, reason
                in rejected
            )

            raise ValueError(
                "no canonical extraction candidate reproduces "
                "the parsed AVB descriptor for firmware partition "
                f"{partition_name!r}: "
                f"candidates="
                f"{tuple(path.as_posix() for path in candidates)!r}, "
                f"rejected={rejected_summary!r}"
            )

        #
        # Every surviving source authenticates to the exact same canonical
        # descriptor identity:
        #
        #   partition_name
        #   image_size
        #   hash_algorithm
        #   salt
        #   digest
        #
        # AndroidBoard.mk later consumes only descriptor.image_size bytes,
        # so additional container/footer bytes outside that authenticated
        # extent are intentionally irrelevant to this construction input.
        #
        authenticated = tuple(
            sorted(
                authenticated,
                key=lambda candidate: (
                    candidate.as_posix()
                ),
            )
        )

        return authenticated[0]

    @staticmethod
    def _verify_hash_source(
        *,
        source_path: Path,
        descriptor: AndroidParsedAvbHashDescriptor,
    ) -> None:
        if not source_path.is_file():
            raise ValueError(
                "canonical AVB descriptor source is unavailable: "
                f"{source_path}"
            )

        if (
            source_path.stat().st_size
            < descriptor.image_size
        ):
            raise ValueError(
                "canonical AVB descriptor source is shorter than "
                "descriptor image_size: "
                f"{source_path}"
            )

        try:
            digest = hashlib.new(
                descriptor.hash_algorithm
            )

        except ValueError as error:
            raise ValueError(
                "unsupported canonical AVB hash algorithm: "
                f"{descriptor.hash_algorithm}"
            ) from error

        digest.update(
            descriptor.salt
        )

        remaining = (
            descriptor.image_size
        )

        with source_path.open(
            "rb"
        ) as handle:
            while remaining:
                chunk = handle.read(
                    min(
                        1024 * 1024,
                        remaining,
                    )
                )

                if not chunk:
                    raise ValueError(
                        "canonical AVB descriptor source "
                        "ended unexpectedly"
                    )

                digest.update(
                    chunk
                )

                remaining -= len(
                    chunk
                )

        if (
            digest.digest()
            != descriptor.digest
        ):
            raise ValueError(
                "canonical source bytes do not reproduce "
                "the parsed AVB hash descriptor: "
                f"partition={descriptor.partition_name}, "
                f"source={source_path}"
            )

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
        native_boot_plan: AndroidDeviceTreeNativeBootBuildPlan,
        signing_profile: AndroidDeviceTreeAvbSigningProfile,
    ) -> AndroidDeviceTreeAvbBuildPlan:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        if not isinstance(
            native_boot_plan,
            AndroidDeviceTreeNativeBootBuildPlan,
        ):
            raise TypeError(
                "native_boot_plan must be an "
                "AndroidDeviceTreeNativeBootBuildPlan"
            )

        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        topology = (
            universe.avb_topology
        )

        if topology is None:
            raise ValueError(
                "AVB build projection requires canonical "
                "Universe topology"
            )

        #
        # Universe AVB topology intentionally covers every parsed AVB/VBMeta
        # region. A requirement being partition-backed only means that the
        # region came from a real partition; it does NOT mean Device Tree owns
        # a standalone vbmeta*.img build target for it.
        #
        # Examples such as system, vendor, product, dtbo, vendor_boot,
        # vendor_kernel_boot, and pvmfw are partition-backed because their
        # partitions carry AVB footer/VBMeta regions. Their final descriptors
        # remain owned by those normal Android image builders.
        #
        # Reconstruction has already made the build-ownership decision.
        # Therefore Device Tree must derive its standalone VBMeta node set
        # exclusively from VBMETA_ARTIFACT representations.
        #
        vbmeta_representations = tuple(
            representation
            for representation
            in reconstruction.artifact_build_representations
            if (
                representation.kind
                is AndroidReconstructionBuildRepresentationKind
                .VBMETA_ARTIFACT
            )
        )

        if not vbmeta_representations:
            raise ValueError(
                "Device Tree AVB construction has no "
                "Reconstruction VBMETA_ARTIFACT population"
            )

        vbmeta_requirement_ids = tuple(
            representation.canonical_requirement_id
            for representation
            in vbmeta_representations
        )

        if any(
            requirement_id is None
            for requirement_id
            in vbmeta_requirement_ids
        ):
            raise ValueError(
                "VBMETA_ARTIFACT representations must all retain "
                "canonical requirement identities"
            )

        if len(
            vbmeta_requirement_ids
        ) != len(
            set(
                vbmeta_requirement_ids
            )
        ):
            raise ValueError(
                "VBMETA_ARTIFACT canonical requirement identities "
                "must be unique"
            )

        standalone_vbmeta_requirement_ids = set(
            vbmeta_requirement_ids
        )

        partition_nodes = tuple(
            requirement
            for requirement
            in topology.requirements
            if (
                requirement.requirement_id
                in standalone_vbmeta_requirement_ids
            )
        )

        actual_standalone_ids = {
            requirement.requirement_id
            for requirement
            in partition_nodes
        }

        if (
            actual_standalone_ids
            != standalone_vbmeta_requirement_ids
        ):
            missing = sorted(
                standalone_vbmeta_requirement_ids
                - actual_standalone_ids
            )

            unexpected = sorted(
                actual_standalone_ids
                - standalone_vbmeta_requirement_ids
            )

            raise ValueError(
                "Reconstruction VBMETA_ARTIFACT population does not "
                "map exactly onto canonical Universe VBMeta requirements: "
                f"missing={missing!r}, "
                f"unexpected={unexpected!r}"
            )

        standalone_node_ids = {
            id(requirement)
            for requirement
            in partition_nodes
        }

        #
        # Root/orphan/cycle conclusions from the full Universe graph are
        # meaningful to Device Tree only when they involve one of these
        # Reconstruction-owned standalone VBMeta image targets.
        #
        standalone_orphans = tuple(
            requirement
            for requirement
            in topology.orphan_requirements
            if (
                id(requirement)
                in standalone_node_ids
            )
        )

        standalone_cycles = tuple(
            requirement
            for requirement
            in topology.cycle_requirements
            if (
                id(requirement)
                in standalone_node_ids
            )
        )

        standalone_roots = tuple(
            requirement
            for requirement
            in topology.root_requirements
            if (
                id(requirement)
                in standalone_node_ids
            )
        )

        if standalone_orphans:
            raise ValueError(
                "standalone VBMETA_ARTIFACT topology contains "
                "orphan requirements: "
                f"{tuple(item.requirement_id for item in standalone_orphans)!r}"
            )

        if standalone_cycles:
            raise ValueError(
                "standalone VBMETA_ARTIFACT topology contains a cycle: "
                f"{tuple(item.requirement_id for item in standalone_cycles)!r}"
            )

        if len(
            standalone_roots
        ) != 1:
            raise ValueError(
                "standalone VBMETA_ARTIFACT topology must contain "
                "exactly one root; found "
                f"{len(standalone_roots)}: "
                f"{tuple(item.requirement_id for item in standalone_roots)!r}"
            )

        root = (
            standalone_roots[
                0
            ]
        )

        if root.partition_name != "vbmeta":
            raise ValueError(
                "Android AVB build projection requires "
                "canonical standalone root vbmeta"
            )

        standalone_partition_names = {
            item.partition_name
            for item
            in partition_nodes
        }

        if standalone_partition_names != {
            "vbmeta",
            "vbmeta_system",
            "vbmeta_vendor",
        }:
            raise ValueError(
                "unexpected standalone VBMETA_ARTIFACT population: "
                f"{sorted(standalone_partition_names)!r}"
            )

        auth_by_owner = {
            id(node): []
            for node in partition_nodes
        }

        chains_by_owner = {
            id(node): []
            for node in partition_nodes
        }

        for authentication in (
            topology.authentications
        ):
            if (
                id(authentication.owner)
                in auth_by_owner
            ):
                auth_by_owner[
                    id(authentication.owner)
                ].append(
                    authentication
                )

        for chain in topology.chains:
            if (
                id(chain.owner)
                in chains_by_owner
            ):
                chains_by_owner[
                    id(chain.owner)
                ].append(
                    chain
                )

        signing_by_partition = {
            item.partition_name: item
            for item in signing_profile.entries
        }

        expected_signing_partitions = {
            "boot",
            "init_boot",
            "vbmeta",
            "vbmeta_system",
            "vbmeta_vendor",
        }

        if set(signing_by_partition) != expected_signing_partitions:
            raise ValueError(
                "AVB build-signing profile does not match the "
                "required Android signing population"
            )

        external_keys = {}
        chain_configs = []

        #
        # Partition-backed VBMeta signers.
        #
        for node in partition_nodes:
            partition_name = (
                node.partition_name
            )

            external_keys[
                partition_name
            ] = (
                AndroidDeviceTreeAvbExternalKey(
                    partition_name=(
                        partition_name
                    ),
                    destination=(
                        signing_by_partition[
                            partition_name
                        ].key_path
                    ),
                    algorithm=(
                        signing_by_partition[
                            partition_name
                        ].algorithm
                    ),
                )
            )

        #
        # Canonical chain descriptors.
        #
        for chain in topology.chains:
            owner_partition_name = (
                chain.owner.partition_name
            )

            if owner_partition_name is None:
                continue

            target_name = (
                chain.target_partition_name
            )

            if target_name not in {
                "boot",
                "init_boot",
                "vbmeta_system",
                "vbmeta_vendor",
            }:
                raise ValueError(
                    "unsupported canonical AVB chain target: "
                    f"{target_name}"
                )

            if (
                chain.descriptor.flags
                != 0
            ):
                raise ValueError(
                    "nonzero AVB chain-descriptor flags "
                    "are not supported by the current "
                    "Android build mapping"
                )

            target_requirement = (
                cls
                ._embedded_target_requirement(
                    reconstruction,
                    target_name,
                )
            )

            target_metadata = (
                target_requirement.metadata
            )

            signing_entry = (
                signing_by_partition[
                    target_name
                ]
            )

            key_path = (
                signing_entry.key_path
            )

            if target_name in {
                "boot",
                "init_boot",
            }:
                external_keys[
                    target_name
                ] = (
                    AndroidDeviceTreeAvbExternalKey(
                        partition_name=(
                            target_name
                        ),
                        destination=(
                            key_path
                        ),
                        algorithm=(
                            signing_entry.algorithm
                        ),
                    )
                )

            chain_configs.append(
                AndroidDeviceTreeAvbChainConfig(
                    owner_partition_name=(
                        owner_partition_name
                    ),
                    target_partition_name=(
                        target_name
                    ),
                    rollback_index_location=(
                        chain
                        .descriptor
                        .rollback_index_location
                    ),
                    target_rollback_index=(
                        target_metadata
                        .rollback_index
                    ),
                    target_algorithm=(
                        signing_entry.algorithm
                    ),
                    key_path=(
                        key_path
                    ),
                )
            )

        if set(
            external_keys
        ) != {
            "boot",
            "init_boot",
            "vbmeta",
            "vbmeta_system",
            "vbmeta_vendor",
        }:
            raise ValueError(
                "AVB external signing-key population does not "
                "match canonical chain/signing topology"
            )

        descriptor_providers = []
        nodes = []

        for node in partition_nodes:
            direct = []
            android_members = []

            explicit_properties = []
            regenerated_properties = []
            kernel_cmdlines = []

            owner_authentications = tuple(
                auth_by_owner[
                    id(node)
                ]
            )

            owner_descriptor_ids = {
                id(
                    authentication
                    .descriptor
                )
                for authentication
                in owner_authentications
            }

            owner_chain_ids = {
                id(
                    chain.descriptor
                )
                for chain
                in chains_by_owner[
                    id(node)
                ]
            }

            for descriptor in (
                node.descriptors
            ):
                if isinstance(
                    descriptor,
                    (
                        AndroidParsedAvbHashDescriptor,
                        AndroidParsedAvbHashtreeDescriptor,
                    ),
                ):
                    if (
                        id(descriptor)
                        not in owner_descriptor_ids
                    ):
                        raise ValueError(
                            "VBMeta direct-auth descriptor is "
                            "not represented in canonical topology"
                        )

                    target = (
                        descriptor.partition_name
                    )

                    if not target:
                        raise ValueError(
                            "unnamed AVB direct-auth descriptors "
                            "cannot be mapped to Android build syntax"
                        )

                    direct.append(
                        target
                    )

                    #
                    # Device Tree projects canonical factory AVB evidence
                    # onto the ownership graph of the Android build.
                    #
                    # Standard Android image families are owned by AOSP's
                    # normal AVB image machinery. Child vbmeta nodes list
                    # those images through BOARD_AVB_VBMETA_*.
                    #
                    # Direct-auth factory firmware outside Android's image
                    # build surface remains canonical Reconstruction evidence
                    # but must not be injected into an AOSP-generated vbmeta.
                    #
                    if (
                        target
                        in cls._AOSP_AUTOMATIC_DIRECT_PARTITIONS
                    ):
                        if node.partition_name in {
                            "vbmeta_system",
                            "vbmeta_vendor",
                        }:
                            android_members.append(
                                target
                            )

                        continue

                    # Non-Android firmware ownership is intentionally not
                    # projected into the AOSP build graph. Parsing/Universe/
                    # Reconstruction retain the exact descriptor and payload
                    # evidence independently.
                    continue

                if isinstance(
                    descriptor,
                    AndroidParsedAvbChainPartitionDescriptor,
                ):
                    if (
                        id(descriptor)
                        not in owner_chain_ids
                    ):
                        raise ValueError(
                            "VBMeta chain descriptor is not "
                            "represented in canonical topology"
                        )

                    continue

                if isinstance(
                    descriptor,
                    AndroidParsedAvbPropertyDescriptor,
                ):
                    if (
                        descriptor.key.startswith(
                            "com.android.build."
                        )
                    ):
                        regenerated_properties.append(
                            descriptor.key
                        )

                    else:
                        explicit_properties.append(
                            (
                                descriptor.key,
                                descriptor.value,
                            )
                        )

                    continue

                if isinstance(
                    descriptor,
                    AndroidParsedAvbKernelCmdlineDescriptor,
                ):
                    if descriptor.flags != 0:
                        raise ValueError(
                            "nonzero canonical AVB kernel-cmdline "
                            "flags are not currently representable"
                        )

                    kernel_cmdlines.append(
                        descriptor.kernel_cmdline
                    )

                    continue

                raise ValueError(
                    "Device Tree encountered an unsupported "
                    "canonical AVB descriptor type: "
                    f"{type(descriptor).__name__}"
                )

            nodes.append(
                AndroidDeviceTreeAvbNodeConfig(
                    partition_name=(
                        node.partition_name
                    ),
                    requirement_id=(
                        node.requirement_id
                    ),
                    algorithm=(
                        cls._algorithm(
                            node
                            .metadata
                            .algorithm_type
                        )
                    ),
                    rollback_index=(
                        node
                        .metadata
                        .rollback_index
                    ),
                    flags=(
                        node.metadata.flags
                    ),
                    direct_partitions=tuple(
                        sorted(
                            direct
                        )
                    ),
                    android_member_partitions=tuple(
                        sorted(
                            android_members
                        )
                    ),
                    explicit_properties=tuple(
                        sorted(
                            explicit_properties
                        )
                    ),
                    regenerated_property_keys=tuple(
                        sorted(
                            regenerated_properties
                        )
                    ),
                    kernel_cmdlines=tuple(
                        kernel_cmdlines
                    ),
                )
            )

        provider_ids = tuple(
            (
                item.owner_partition_name,
                item.partition_name,
            )
            for item in descriptor_providers
        )

        if len(
            provider_ids
        ) != len(
            set(
                provider_ids
            )
        ):
            raise ValueError(
                "duplicate AVB descriptor-provider identity"
            )

        result = (
            AndroidDeviceTreeAvbBuildPlan(
                device_root=PurePosixPath(
                    identity.device_root.as_posix()
                ),
                root_partition_name="vbmeta",
                rollback_index_expression=(
                    signing_profile.rollback_index_expression
                ),
                nodes=tuple(
                    sorted(
                        nodes,
                        key=lambda item: (
                            item.partition_name
                        ),
                    )
                ),
                chains=tuple(
                    sorted(
                        chain_configs,
                        key=lambda item: (
                            item.owner_partition_name,
                            item.target_partition_name,
                        ),
                    )
                ),
                external_keys=tuple(
                    sorted(
                        external_keys.values(),
                        key=lambda item: (
                            item.partition_name
                        ),
                    )
                ),
                descriptor_providers=tuple(
                    sorted(
                        descriptor_providers,
                        key=lambda item: (
                            item.owner_partition_name,
                            item.partition_name,
                        ),
                    )
                ),
                source_equivalence_promotion_count=0,
                imported_boot_image_vbmeta_count=0,
                development_key_count=0,
                aosp_checkout_dependency_count=0,
                treeforge_image_builder_count=0,
                treeforge_vbmeta_encoder_count=0,
            )
        )

        if not result.complete:
            raise ValueError(
                "canonical AVB build mapping is incomplete"
            )

        return result


class AndroidDeviceTreeAvbBuildRenderer:
    @staticmethod
    def _node(
        plan: AndroidDeviceTreeAvbBuildPlan,
        partition_name: str,
    ) -> AndroidDeviceTreeAvbNodeConfig:
        matches = tuple(
            node
            for node in plan.nodes
            if (
                node.partition_name
                == partition_name
            )
        )

        if len(matches) != 1:
            raise ValueError(
                "expected exactly one AVB node: "
                f"{partition_name}"
            )

        return matches[0]

    @staticmethod
    def _chain(
        plan: AndroidDeviceTreeAvbBuildPlan,
        target_partition_name: str,
    ) -> AndroidDeviceTreeAvbChainConfig:
        matches = tuple(
            chain
            for chain in plan.chains
            if (
                chain.target_partition_name
                == target_partition_name
            )
        )

        if len(matches) != 1:
            raise ValueError(
                "expected exactly one AVB chain target: "
                f"{target_partition_name}"
            )

        return matches[0]

    @staticmethod
    def _args_variable(
        partition_name: str,
    ) -> str:
        if partition_name == "vbmeta":
            return (
                "BOARD_AVB_MAKE_VBMETA_IMAGE_ARGS"
            )

        if partition_name == "vbmeta_system":
            return (
                "BOARD_AVB_MAKE_VBMETA_SYSTEM_IMAGE_ARGS"
            )

        if partition_name == "vbmeta_vendor":
            return (
                "BOARD_AVB_MAKE_VBMETA_VENDOR_IMAGE_ARGS"
            )

        raise ValueError(
            "unsupported VBMeta node"
        )

    @classmethod
    def render_board_config(
        cls,
        plan: AndroidDeviceTreeAvbBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeAvbBuildPlan,
        ):
            raise TypeError(
                "plan must be an AndroidDeviceTreeAvbBuildPlan"
            )

        root = cls._node(
            plan,
            "vbmeta",
        )

        system = cls._node(
            plan,
            "vbmeta_system",
        )

        vendor = cls._node(
            plan,
            "vbmeta_vendor",
        )

        key_by_partition = {
            item.partition_name:
            item
            for item in plan.external_keys
        }

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Canonical AVB topology mapped onto Android's normal build.",
            "# TreeForge does not build final VBMeta images.",
            "# Signing provider is selected explicitly by treeforge device-tree.",
            "",
            "BOARD_AVB_ENABLE := true",
            "",
        ]

        #
        # Explicit keys + parse-time guards prevent AOSP's default test-key
        # fallback from ever becoming an accidental TreeForge policy.
        #
        for partition_name in (
            "vbmeta",
            "boot",
            "init_boot",
            "vbmeta_system",
            "vbmeta_vendor",
        ):
            key = (
                key_by_partition[
                    partition_name
                ]
            )

            variable_prefix = (
                "BOARD_AVB"
                if partition_name == "vbmeta"
                else (
                    "BOARD_AVB_"
                    f"{partition_name.upper()}"
                )
            )

            lines.extend(
                [
                    (
                        f"{variable_prefix}_KEY_PATH := "
                        f"{key.destination.as_posix()}"
                    ),
                    (
                        f"{variable_prefix}_ALGORITHM := "
                        f"{key.algorithm}"
                    ),
                    (
                        "ifeq (,$(wildcard "
                        f"$({variable_prefix}_KEY_PATH)"
                        "))"
                    ),
                    (
                        "$(error TreeForge requires external "
                        "AVB private key: "
                        f"$({variable_prefix}_KEY_PATH))"
                    ),
                    "endif",
                    "",
                ]
            )

        lines.extend(
            [
                (
                    "BOARD_AVB_ROLLBACK_INDEX := "
                    f"{plan.rollback_index_expression}"
                ),
                "",
            ]
        )

        for target in (
            "boot",
            "init_boot",
        ):
            chain = cls._chain(
                plan,
                target,
            )

            upper = target.upper()

            lines.extend(
                [
                    (
                        f"BOARD_AVB_{upper}_ROLLBACK_INDEX := "
                        f"{plan.rollback_index_expression}"
                    ),
                    (
                        f"BOARD_AVB_{upper}_ROLLBACK_INDEX_LOCATION := "
                        f"{chain.rollback_index_location}"
                    ),
                    "",
                ]
            )

        for (
            partition_name,
            node,
        ) in (
            (
                "vbmeta_system",
                system,
            ),
            (
                "vbmeta_vendor",
                vendor,
            ),
        ):
            chain = cls._chain(
                plan,
                partition_name,
            )

            upper = (
                partition_name.upper()
            )

            if not (
                node
                .android_member_partitions
            ):
                raise ValueError(
                    "child VBMeta node has no Android-native members: "
                    f"{partition_name}"
                )

            lines.extend(
                [
                    (
                        f"BOARD_AVB_{upper} := "
                        + " ".join(
                            node
                            .android_member_partitions
                        )
                    ),
                    (
                        f"BOARD_AVB_{upper}_ROLLBACK_INDEX := "
                        f"{plan.rollback_index_expression}"
                    ),
                    (
                        f"BOARD_AVB_{upper}_ROLLBACK_INDEX_LOCATION := "
                        f"{chain.rollback_index_location}"
                    ),
                    "",
                ]
            )

        providers_by_owner = {
            node.partition_name: []
            for node in plan.nodes
        }

        for provider in (
            plan.descriptor_providers
        ):
            providers_by_owner[
                provider.owner_partition_name
            ].append(
                provider
            )

        for node in plan.nodes:
            args_variable = (
                cls._args_variable(
                    node.partition_name
                )
            )

            if node.flags:
                lines.append(
                    f"{args_variable} += "
                    f"--flags {node.flags}"
                )

            for key, value in (
                node.explicit_properties
            ):
                escaped = (
                    f"{key}:{value}"
                    .replace(
                        "$",
                        "$$",
                    )
                )

                lines.append(
                    f"{args_variable} += "
                    f"--prop '{escaped}'"
                )

            for cmdline in (
                node.kernel_cmdlines
            ):
                escaped = (
                    cmdline.replace(
                        "$",
                        "$$",
                    )
                )

                lines.append(
                    f"{args_variable} += "
                    f"--kernel_cmdline '{escaped}'"
                )

            for provider in (
                providers_by_owner[
                    node.partition_name
                ]
            ):
                variable_name = (
                    "TREEFORGE_AVB_DESCRIPTOR_"
                    f"{provider.partition_name.upper()}"
                )

                lines.extend(
                    [
                        (
                            f"{variable_name} := "
                            f"{provider.provider_target}"
                        ),
                        (
                            f"{args_variable} += "
                            "--include_descriptors_from_image "
                            f"$({variable_name})"
                        ),
                    ]
                )

            if (
                node.flags
                or node.explicit_properties
                or node.kernel_cmdlines
                or providers_by_owner[
                    node.partition_name
                ]
            ):
                lines.append("")

        return (
            "\n".join(lines)
            .rstrip()
            + "\n"
        )

    @classmethod
    def render_android_board(
        cls,
        plan: AndroidDeviceTreeAvbBuildPlan,
        native_boot_plan: AndroidDeviceTreeNativeBootBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeAvbBuildPlan,
        ):
            raise TypeError(
                "plan must be an AndroidDeviceTreeAvbBuildPlan"
            )

        if not isinstance(
            native_boot_plan,
            AndroidDeviceTreeNativeBootBuildPlan,
        ):
            raise TypeError(
                "native_boot_plan must be an "
                "AndroidDeviceTreeNativeBootBuildPlan"
            )

        lines = [
            "# Generated by TreeForge.",
            "#",
            "# Minimal AVB build glue for Android-owned descriptor inputs.",
            "# Final image construction and descriptor encoding are performed",
            "# by Android build tools / avbtool, not by TreeForge.",
            "",
            "LOCAL_PATH := $(call my-dir)",
            "",
        ]

        providers_by_owner = {
            "vbmeta": [],
            "vbmeta_system": [],
            "vbmeta_vendor": [],
        }

        for provider in (
            plan.descriptor_providers
        ):
            providers_by_owner[
                provider.owner_partition_name
            ].append(
                provider
            )

            variable_name = (
                "TREEFORGE_AVB_DESCRIPTOR_"
                f"{provider.partition_name.upper()}"
            )

            source = (
                provider
                .source_destination
                .as_posix()
            )

            footer_extra = (
                "$(BOARD_AVB_PVMFW_ADD_HASH_FOOTER_ARGS)"
                if provider.partition_name == "pvmfw"
                else ""
            )

            do_not_use_ab = (
                " --do_not_use_ab"
                if provider.flags == 1
                else ""
            )

            lines.extend(
                [
                    (
                        f"$({variable_name}): "
                        f"{source}"
                    ),
                    "\t@mkdir -p $(dir $@)",
                    (
                        "\t@head -c "
                        f"{provider.image_size} "
                        "$< > $@"
                    ),
                    (
                        "\t$(AVBTOOL) add_hash_footer "
                        "--image $@ "
                        "--dynamic_partition_size "
                        f"--partition_name {provider.partition_name} "
                        "--algorithm NONE "
                        f"--hash_algorithm {provider.hash_algorithm} "
                        f"--salt {provider.salt.hex()}"
                        f"{do_not_use_ab} "
                        f"{footer_extra}"
                    ),
                    "",
                ]
            )

        for owner, providers in (
            providers_by_owner.items()
        ):
            if not providers:
                continue

            target = (
                "$(PRODUCT_OUT)/"
                f"{owner}.img"
            )

            dependencies = " ".join(
                (
                    "$(TREEFORGE_AVB_DESCRIPTOR_"
                    f"{provider.partition_name.upper()})"
                )
                for provider in providers
            )

            lines.extend(
                [
                    (
                        f"{target}: "
                        f"{dependencies}"
                    ),
                    "",
                ]
            )

        return (
            "\n".join(lines)
            .rstrip()
            + "\n"
        )
