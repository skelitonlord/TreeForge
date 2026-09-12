from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil

from treeforge.android.boot_image.realization import (
    AndroidBootImageBootImageRealization,
    AndroidBootImageParentVbmetaRealization,
)
from treeforge.android.boot_image.validation import (
    AndroidBootImageValidationDisposition,
    AndroidBootImageValidationResult,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDeploymentImage:
    """
    One exact deployable Boot Image partition artifact together with the
    exact canonical original image retained by Parsing.

    For a changed deployment:
      final_*    -> validated reconstructed image
      rollback_* -> exact canonical original image

    For a base deployment:
      final_* and rollback_* intentionally identify the same canonical
      bytes. No reconstruction or signing is implied by a base population.
    """

    partition_name: str

    source_kind: str

    final_source_path: Path
    final_path: Path
    final_size_bytes: int
    final_sha256: str

    rollback_source_path: Path
    rollback_path: Path
    rollback_size_bytes: int
    rollback_sha256: str

    rollback_required: bool = True

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
                "partition_name must be a non-empty string"
            )

        if self.source_kind not in {
            "boot_image",
            "parent_vbmeta",
        }:
            raise ValueError(
                "source_kind must be boot_image or parent_vbmeta"
            )

        for (
            field_name,
            path,
        ) in (
            (
                "final_source_path",
                self.final_source_path,
            ),
            (
                "final_path",
                self.final_path,
            ),
            (
                "rollback_source_path",
                self.rollback_source_path,
            ),
            (
                "rollback_path",
                self.rollback_path,
            ),
        ):
            if not isinstance(
                path,
                Path,
            ):
                raise TypeError(
                    f"{field_name} must be a pathlib.Path"
                )

            if not path.is_file():
                raise FileNotFoundError(
                    f"{field_name} is unavailable: {path}"
                )

        for (
            field_name,
            value,
        ) in (
            (
                "final_size_bytes",
                self.final_size_bytes,
            ),
            (
                "rollback_size_bytes",
                self.rollback_size_bytes,
            ),
        ):
            if (
                isinstance(
                    value,
                    bool,
                )
                or not isinstance(
                    value,
                    int,
                )
                or value <= 0
            ):
                raise ValueError(
                    f"{field_name} must be a positive int"
                )

        for (
            field_name,
            value,
        ) in (
            (
                "final_sha256",
                self.final_sha256,
            ),
            (
                "rollback_sha256",
                self.rollback_sha256,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or len(
                    value
                ) != 64
            ):
                raise ValueError(
                    f"{field_name} must be a SHA-256 hex digest"
                )

        if self.rollback_required is not True:
            raise ValueError(
                "changed Boot Image deployment artifacts must "
                "retain an exact rollback image"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageDeploymentPlan:
    """
    Durable post-Validation Boot Image deployment boundary.

    The plan preserves exact Validation identity and contains only complete,
    independently validated partition replacements with exact whole-image
    rollback artifacts.
    """

    validation: AndroidBootImageValidationResult

    images: tuple[
        AndroidBootImageDeploymentImage,
        ...,
    ]

    output_root: Path

    manifest_path: Path

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.validation,
            AndroidBootImageValidationResult,
        ):
            raise TypeError(
                "validation must be an AndroidBootImageValidationResult"
            )

        if (
            self.validation.disposition
            is not
            AndroidBootImageValidationDisposition.PASS
        ):
            raise ValueError(
                "Boot Image Deployment Planning requires "
                "Validation disposition PASS"
            )

        if not isinstance(
            self.images,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageDeploymentImage,
            )
            for value
            in self.images
        ):
            raise TypeError(
                "images contains an invalid deployment image"
            )

        if not isinstance(
            self.output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if not isinstance(
            self.manifest_path,
            Path,
        ):
            raise TypeError(
                "manifest_path must be a pathlib.Path"
            )

        if not self.manifest_path.is_file():
            raise FileNotFoundError(
                "Boot Image deployment manifest is unavailable: "
                f"{self.manifest_path}"
            )

        partition_names = tuple(
            image.partition_name
            for image
            in self.images
        )

        if len(
            partition_names
        ) != len(
            set(
                partition_names
            )
        ):
            raise ValueError(
                "Boot Image Deployment Planning cannot emit "
                "duplicate partition targets"
            )

        if (
            self.validation
            .flashable_chain_applicable
        ):
            if not (
                self.validation
                .flashable_chain_complete
            ):
                raise ValueError(
                    "applicable Boot Image deployment requires a "
                    "complete validated flashable chain"
                )

            if not self.images:
                raise ValueError(
                    "complete changed Boot Image chain produced no "
                    "deployment artifacts"
                )

        elif self.images:
            raise ValueError(
                "non-applicable Boot Image deployment cannot contain "
                "partition replacements"
            )

    @property
    def parsing(
        self,
    ):
        return self.validation.parsing

    @property
    def realization(
        self,
    ):
        return self.validation.realization

    @property
    def image_count(
        self,
    ) -> int:
        return len(
            self.images
        )




@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageBaseDeployment:
    """
    Durable canonical Boot Image population derived directly from Parsing.

    This is not a reconstructed or mutated Deployment Planning result.
    Every image is an exact whole-image artifact retained by the selected
    canonical Parsing snapshot.

    The object exists so already-materialized base images can be reused for
    saving or hardware deployment without rerunning signing, interpretation,
    composition, planning, realization, or validation.
    """

    images: tuple[
        AndroidBootImageDeploymentImage,
        ...,
    ]

    output_root: Path
    manifest_path: Path

    parsing_snapshot_path: Path
    parsing_snapshot_sha256: str

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.images,
                tuple,
            )
            or not self.images
            or not all(
                isinstance(
                    image,
                    AndroidBootImageDeploymentImage,
                )
                for image in self.images
            )
        ):
            raise ValueError(
                "base Boot Image deployment requires at least one "
                "valid deployment image"
            )

        if not isinstance(
            self.output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if not isinstance(
            self.manifest_path,
            Path,
        ):
            raise TypeError(
                "manifest_path must be a pathlib.Path"
            )

        if not self.manifest_path.is_file():
            raise FileNotFoundError(
                "base Boot Image manifest is unavailable: "
                f"{self.manifest_path}"
            )

        if not isinstance(
            self.parsing_snapshot_path,
            Path,
        ):
            raise TypeError(
                "parsing_snapshot_path must be a pathlib.Path"
            )

        if (
            not isinstance(
                self.parsing_snapshot_sha256,
                str,
            )
            or len(
                self.parsing_snapshot_sha256
            ) != 64
        ):
            raise ValueError(
                "parsing_snapshot_sha256 must be a SHA-256 digest"
            )

        names = tuple(
            image.partition_name
            for image in self.images
        )

        if len(names) != len(set(names)):
            raise ValueError(
                "base Boot Image deployment contains duplicate "
                "partition targets"
            )

        for image in self.images:
            if (
                image.final_size_bytes
                != image.rollback_size_bytes
                or image.final_sha256
                != image.rollback_sha256
            ):
                raise ValueError(
                    "base Boot Image deployment final/original "
                    "identity differs for partition "
                    f"{image.partition_name}"
                )

    @property
    def image_count(
        self,
    ) -> int:
        return len(
            self.images
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageReusableDeployment:
    """
    Durable Boot Image deployment reloaded from an already validated
    Deployment Planning manifest.

    This object deliberately does not recreate Validation, Realization,
    Planning, Composition, or Interpretation objects.

    Fresh image generation requires those exact in-memory identities.
    Reuse instead proves the persisted boundary cryptographically:
      - exact Parsing snapshot;
      - optional exact Bootstrap handoff;
      - exact modified partition images;
      - exact canonical original partition images.
    """

    images: tuple[
        AndroidBootImageDeploymentImage,
        ...,
    ]

    output_root: Path
    manifest_path: Path

    parsing_snapshot_path: Path
    parsing_snapshot_sha256: str

    bootstrap_handoff_path: Path | None
    bootstrap_handoff_sha256: str | None

    def __post_init__(self) -> None:
        if not isinstance(
            self.images,
            tuple,
        ) or not all(
            isinstance(
                value,
                AndroidBootImageDeploymentImage,
            )
            for value
            in self.images
        ):
            raise TypeError(
                "images contains an invalid deployment image"
            )

        if not self.images:
            raise ValueError(
                "reusable Boot Image deployment requires at least "
                "one image"
            )

        if not isinstance(
            self.output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if not isinstance(
            self.manifest_path,
            Path,
        ):
            raise TypeError(
                "manifest_path must be a pathlib.Path"
            )

        if not self.manifest_path.is_file():
            raise FileNotFoundError(
                "Boot Image deployment manifest is unavailable: "
                f"{self.manifest_path}"
            )

        if not isinstance(
            self.parsing_snapshot_path,
            Path,
        ):
            raise TypeError(
                "parsing_snapshot_path must be a pathlib.Path"
            )

        if (
            not isinstance(
                self.parsing_snapshot_sha256,
                str,
            )
            or len(
                self.parsing_snapshot_sha256
            ) != 64
        ):
            raise ValueError(
                "parsing_snapshot_sha256 must be a SHA-256 digest"
            )

        if (
            self.bootstrap_handoff_path is None
        ) != (
            self.bootstrap_handoff_sha256 is None
        ):
            raise ValueError(
                "Bootstrap handoff path/hash must either both exist "
                "or both be absent"
            )

        if (
            self.bootstrap_handoff_path
            is not None
            and not isinstance(
                self.bootstrap_handoff_path,
                Path,
            )
        ):
            raise TypeError(
                "bootstrap_handoff_path must be a pathlib.Path or None"
            )

        if (
            self.bootstrap_handoff_sha256
            is not None
            and (
                not isinstance(
                    self.bootstrap_handoff_sha256,
                    str,
                )
                or len(
                    self.bootstrap_handoff_sha256
                ) != 64
            )
        ):
            raise ValueError(
                "bootstrap_handoff_sha256 must be a SHA-256 digest"
            )

        partition_names = tuple(
            image.partition_name
            for image
            in self.images
        )

        if len(
            partition_names
        ) != len(
            set(
                partition_names
            )
        ):
            raise ValueError(
                "reusable Boot Image deployment contains duplicate "
                "partition targets"
            )

    @property
    def image_count(self) -> int:
        return len(
            self.images
        )


class AndroidBootImageDeploymentPlanner:
    """
    Plan exact hardware deployment inputs after Boot Image Validation.

    Responsibilities:
      - consume only Validation PASS;
      - identify every realized changed partition;
      - preserve exact canonical whole-image rollback;
      - copy final/rollback images into a durable deployment workspace;
      - hash and verify all copied bytes;
      - write a machine-readable deployment manifest.

    This phase does not:
      - discover hardware;
      - choose slots;
      - invoke fastboot;
      - reboot a device;
      - perform rollback.
    """

    @staticmethod
    def _file_identity(
        path: Path,
    ) -> tuple[
        int,
        str,
    ]:
        if not path.is_file():
            raise FileNotFoundError(
                "Boot Image deployment artifact is unavailable: "
                f"{path}"
            )

        digest = sha256()

        with path.open(
            "rb"
        ) as handle:
            while True:
                chunk = handle.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(
                    chunk
                )

        return (
            path.stat().st_size,
            digest.hexdigest(),
        )

    @classmethod
    def _copy_exact(
        cls,
        source: Path,
        destination: Path,
    ) -> tuple[
        int,
        str,
    ]:
        source_size, source_digest = (
            cls._file_identity(
                source
            )
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        copied_size, copied_digest = (
            cls._file_identity(
                destination
            )
        )

        if (
            copied_size != source_size
            or copied_digest
            != source_digest
        ):
            raise RuntimeError(
                "Boot Image deployment copy lost exact byte identity: "
                f"{source} -> {destination}"
            )

        return (
            copied_size,
            copied_digest,
        )

    @staticmethod
    def _canonical_partition_for_rebuilt(
        rebuilt: AndroidBootImageBootImageRealization,
    ):
        return (
            rebuilt
            .image_plan
            .composition
            .image
            .image
            .partition
        )

    @staticmethod
    def _canonical_partition_for_parent(
        realized: AndroidBootImageParentVbmetaRealization,
    ):
        return (
            realized
            .rewrite
            .parent_vbmeta
            .partition
        )

    def build(
        self,
        validation: AndroidBootImageValidationResult,
        *,
        output_root: Path,
        parsing_snapshot_path: Path,
        bootstrap_handoff_path: Path | None = None,
    ) -> AndroidBootImageDeploymentPlan:
        if not isinstance(
            validation,
            AndroidBootImageValidationResult,
        ):
            raise TypeError(
                "validation must be an AndroidBootImageValidationResult"
            )

        if not isinstance(
            output_root,
            Path,
        ):
            raise TypeError(
                "output_root must be a pathlib.Path"
            )

        if not isinstance(
            parsing_snapshot_path,
            Path,
        ):
            raise TypeError(
                "parsing_snapshot_path must be a pathlib.Path"
            )

        parsing_snapshot_path = (
            parsing_snapshot_path
            .expanduser()
            .resolve()
        )

        if not parsing_snapshot_path.is_file():
            raise FileNotFoundError(
                "canonical Parsing snapshot is unavailable for "
                "Boot Image Deployment Planning: "
                f"{parsing_snapshot_path}"
            )

        parsing_snapshot_size, parsing_snapshot_sha256 = (
            self._file_identity(
                parsing_snapshot_path
            )
        )

        if parsing_snapshot_size <= 0:
            raise RuntimeError(
                "canonical Parsing snapshot is empty"
            )

        bootstrap_handoff_sha256 = None

        if bootstrap_handoff_path is not None:
            if not isinstance(
                bootstrap_handoff_path,
                Path,
            ):
                raise TypeError(
                    "bootstrap_handoff_path must be a pathlib.Path or None"
                )

            bootstrap_handoff_path = (
                bootstrap_handoff_path
                .expanduser()
                .resolve()
            )

            if not bootstrap_handoff_path.is_file():
                raise FileNotFoundError(
                    "Bootstrap handoff is unavailable for "
                    "Boot Image Deployment Planning: "
                    f"{bootstrap_handoff_path}"
                )

            (
                bootstrap_handoff_size,
                bootstrap_handoff_sha256,
            ) = self._file_identity(
                bootstrap_handoff_path
            )

            if bootstrap_handoff_size <= 0:
                raise RuntimeError(
                    "Bootstrap handoff is empty"
                )

        if (
            validation.disposition
            is not
            AndroidBootImageValidationDisposition.PASS
        ):
            raise RuntimeError(
                "Boot Image Deployment Planning refuses a "
                "non-PASS Validation result"
            )

        realization = (
            validation.realization
        )

        if (
            validation
            .flashable_chain_applicable
            and not (
                validation
                .flashable_chain_complete
            )
        ):
            raise RuntimeError(
                "Boot Image Deployment Planning refuses an "
                "incomplete flashable chain"
            )

        #
        # A no-mutation Boot Image run legitimately has no deployment set.
        #
        if not (
            validation
            .flashable_chain_applicable
        ):
            if output_root.exists():
                shutil.rmtree(
                    output_root
                )

            output_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            manifest_path = (
                output_root
                / "deployment-manifest.json"
            )

            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "parsing_snapshot": {
                            "path": str(
                                parsing_snapshot_path
                            ),
                            "sha256": (
                                parsing_snapshot_sha256
                            ),
                        },
                        "bootstrap_handoff": (
                            {
                                "path": str(
                                    bootstrap_handoff_path
                                ),
                                "sha256": (
                                    bootstrap_handoff_sha256
                                ),
                            }
                            if (
                                bootstrap_handoff_path
                                is not None
                            )
                            else None
                        ),
                        "flashable_chain_applicable": False,
                        "flashable_chain_complete": False,
                        "images": [],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            return AndroidBootImageDeploymentPlan(
                validation=validation,
                images=(),
                output_root=output_root,
                manifest_path=(
                    manifest_path
                ),
            )

        rebuilt_images = tuple(
            realization
            .rebuilt_boot_images
        )

        parent_images = tuple(
            realization
            .parent_vbmeta_realizations
        )

        if not rebuilt_images:
            raise RuntimeError(
                "flashable Boot Image chain contains no rebuilt "
                "boot-family images"
            )

        if any(
            not rebuilt.avb_complete
            for rebuilt
            in rebuilt_images
        ):
            raise RuntimeError(
                "Deployment Planning received a rebuilt image whose "
                "AVB realization is incomplete"
            )

        #
        # Validation must independently account for each final partition
        # artifact before Deployment Planning can expose it to hardware.
        #
        validated_final_paths = {
            value.output_path.resolve()
            for value
            in validation.avb_artifacts
        }

        validated_final_paths.update(
            value.output_path.resolve()
            for value
            in validation.boot_image_structures
        )

        candidates = []

        for rebuilt in (
            rebuilt_images
        ):
            partition = (
                self
                ._canonical_partition_for_rebuilt(
                    rebuilt
                )
            )

            candidates.append(
                (
                    "boot_image",
                    partition,
                    rebuilt.output_path,
                    rebuilt.size_bytes,
                    rebuilt.content_sha256,
                )
            )

        for realized_parent in (
            parent_images
        ):
            partition = (
                self
                ._canonical_partition_for_parent(
                    realized_parent
                )
            )

            candidates.append(
                (
                    "parent_vbmeta",
                    partition,
                    realized_parent.output_path,
                    realized_parent.size_bytes,
                    realized_parent.content_sha256,
                )
            )

        candidate_partition_names = tuple(
            partition.name
            for (
                _,
                partition,
                _,
                _,
                _,
            )
            in candidates
        )

        if len(
            candidate_partition_names
        ) != len(
            set(
                candidate_partition_names
            )
        ):
            raise RuntimeError(
                "Boot Image Deployment Planning resolved duplicate "
                "changed partition identities"
            )

        if output_root.exists():
            shutil.rmtree(
                output_root
            )

        flash_root = (
            output_root
            / "flash"
        )

        rollback_root = (
            output_root
            / "rollback"
        )

        flash_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        rollback_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        deployment_images = []

        for (
            source_kind,
            partition,
            final_source_path,
            expected_final_size,
            expected_final_digest,
        ) in candidates:
            partition_name = (
                partition.name
            )

            if (
                not isinstance(
                    partition_name,
                    str,
                )
                or not partition_name
            ):
                raise RuntimeError(
                    "changed Boot Image partition lost its "
                    "canonical partition name"
                )

            final_source_path = (
                final_source_path.resolve()
            )

            if (
                final_source_path
                not in validated_final_paths
            ):
                raise RuntimeError(
                    "Boot Image Deployment Planning found a final "
                    "partition image not independently covered by "
                    "Validation: "
                    f"{partition_name}: {final_source_path}"
                )

            (
                actual_final_size,
                actual_final_digest,
            ) = self._file_identity(
                final_source_path
            )

            if (
                actual_final_size
                != expected_final_size
                or actual_final_digest
                != expected_final_digest
            ):
                raise RuntimeError(
                    "Boot Image final realization identity changed "
                    "after Validation: "
                    f"{partition_name}"
                )

            rollback_source_path = (
                partition
                .artifact
                .path
                .resolve()
            )

            if not (
                rollback_source_path
                .is_file()
            ):
                raise FileNotFoundError(
                    "canonical whole-image rollback artifact is "
                    "unavailable for "
                    f"{partition_name}: "
                    f"{rollback_source_path}"
                )

            final_path = (
                flash_root
                / f"{partition_name}.img"
            )

            rollback_path = (
                rollback_root
                / f"{partition_name}.img"
            )

            (
                final_size,
                final_digest,
            ) = self._copy_exact(
                final_source_path,
                final_path,
            )

            (
                rollback_size,
                rollback_digest,
            ) = self._copy_exact(
                rollback_source_path,
                rollback_path,
            )

            deployment_images.append(
                AndroidBootImageDeploymentImage(
                    partition_name=(
                        partition_name
                    ),
                    source_kind=(
                        source_kind
                    ),
                    final_source_path=(
                        final_source_path
                    ),
                    final_path=(
                        final_path
                    ),
                    final_size_bytes=(
                        final_size
                    ),
                    final_sha256=(
                        final_digest
                    ),
                    rollback_source_path=(
                        rollback_source_path
                    ),
                    rollback_path=(
                        rollback_path
                    ),
                    rollback_size_bytes=(
                        rollback_size
                    ),
                    rollback_sha256=(
                        rollback_digest
                    ),
                    rollback_required=True,
                )
            )

        images = tuple(
            deployment_images
        )

        expected_partition_names = tuple(
            candidate_partition_names
        )

        actual_partition_names = tuple(
            image.partition_name
            for image
            in images
        )

        if (
            actual_partition_names
            != expected_partition_names
        ):
            raise RuntimeError(
                "Boot Image Deployment Planning lost changed "
                "partition order or identity"
            )

        manifest_path = (
            output_root
            / "deployment-manifest.json"
        )

        manifest = {
            "schema_version": 1,
            "parsing_snapshot": {
                "path": str(
                    parsing_snapshot_path
                ),
                "sha256": (
                    parsing_snapshot_sha256
                ),
            },
            "bootstrap_handoff": (
                {
                    "path": str(
                        bootstrap_handoff_path
                    ),
                    "sha256": (
                        bootstrap_handoff_sha256
                    ),
                }
                if (
                    bootstrap_handoff_path
                    is not None
                )
                else None
            ),
            "flashable_chain_applicable": (
                validation
                .flashable_chain_applicable
            ),
            "flashable_chain_complete": (
                validation
                .flashable_chain_complete
            ),
            "validation_disposition": (
                validation
                .disposition
                .value
            ),
            "images": [
                {
                    "partition_name": (
                        image.partition_name
                    ),
                    "source_kind": (
                        image.source_kind
                    ),
                    "final": {
                        "source_path": str(
                            image.final_source_path
                        ),
                        "path": str(
                            image.final_path
                        ),
                        "size_bytes": (
                            image.final_size_bytes
                        ),
                        "sha256": (
                            image.final_sha256
                        ),
                    },
                    "rollback": {
                        "source_path": str(
                            image.rollback_source_path
                        ),
                        "path": str(
                            image.rollback_path
                        ),
                        "size_bytes": (
                            image.rollback_size_bytes
                        ),
                        "sha256": (
                            image.rollback_sha256
                        ),
                        "required": (
                            image.rollback_required
                        ),
                    },
                }
                for image
                in images
            ],
        }

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return AndroidBootImageDeploymentPlan(
            validation=validation,
            images=images,
            output_root=output_root,
            manifest_path=manifest_path,
        )






def build_base_boot_image_deployment(
    parsing: AndroidParsingResult,
    *,
    parsing_snapshot_path: Path,
    output_root: Path,
) -> AndroidBootImageBaseDeployment:
    """
    Materialize exact canonical boot-family whole images from Parsing.

    No Boot Image reconstruction, AVB signing, mutation, or Validation is
    performed. The selected Parsing snapshot is the authoritative identity
    boundary.
    """

    if not isinstance(
        parsing,
        AndroidParsingResult,
    ):
        raise TypeError(
            "parsing must be an AndroidParsingResult"
        )

    if not isinstance(
        parsing_snapshot_path,
        Path,
    ):
        raise TypeError(
            "parsing_snapshot_path must be a pathlib.Path"
        )

    if not isinstance(
        output_root,
        Path,
    ):
        raise TypeError(
            "output_root must be a pathlib.Path"
        )

    parsing_snapshot_path = (
        parsing_snapshot_path
        .expanduser()
        .resolve()
    )

    if not parsing_snapshot_path.is_file():
        raise FileNotFoundError(
            "canonical Parsing snapshot is unavailable: "
            f"{parsing_snapshot_path}"
        )

    (
        snapshot_size,
        snapshot_sha256,
    ) = (
        AndroidBootImageDeploymentPlanner
        ._file_identity(
            parsing_snapshot_path
        )
    )

    if snapshot_size <= 0:
        raise RuntimeError(
            "canonical Parsing snapshot is empty"
        )

    if not parsing.boot_images:
        raise RuntimeError(
            "canonical Parsing contains no boot-family images"
        )

    partition_names = tuple(
        image.partition.name
        for image
        in parsing.boot_images
    )

    if len(
        partition_names
    ) != len(
        set(
            partition_names
        )
    ):
        raise RuntimeError(
            "canonical Parsing boot-family population contains "
            "duplicate partition names"
        )

    if output_root.exists():
        shutil.rmtree(
            output_root
        )

    image_root = (
        output_root
        / "images"
    )

    image_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    images = []

    for parsed_image in (
        parsing.boot_images
    ):
        partition = (
            parsed_image.partition
        )

        partition_name = (
            partition.name
        )

        source_path = (
            partition
            .artifact
            .path
            .resolve()
        )

        if not source_path.is_file():
            raise FileNotFoundError(
                "canonical whole boot-family image is unavailable: "
                f"{partition_name}: {source_path}"
            )

        destination = (
            image_root
            / f"{partition_name}.img"
        )

        (
            copied_size,
            copied_sha256,
        ) = (
            AndroidBootImageDeploymentPlanner
            ._copy_exact(
                source_path,
                destination,
            )
        )

        #
        # Base final/original are deliberately identical.
        #
        images.append(
            AndroidBootImageDeploymentImage(
                partition_name=(
                    partition_name
                ),
                source_kind="boot_image",
                final_source_path=(
                    source_path
                ),
                final_path=(
                    destination
                ),
                final_size_bytes=(
                    copied_size
                ),
                final_sha256=(
                    copied_sha256
                ),
                rollback_source_path=(
                    source_path
                ),
                rollback_path=(
                    destination
                ),
                rollback_size_bytes=(
                    copied_size
                ),
                rollback_sha256=(
                    copied_sha256
                ),
                rollback_required=True,
            )
        )

    images = tuple(
        images
    )

    manifest_path = (
        output_root
        / "deployment-manifest.json"
    )

    manifest = {
        "schema_version": 1,
        "deployment_kind": "base",
        "parsing_snapshot": {
            "path": str(
                parsing_snapshot_path
            ),
            "sha256": (
                snapshot_sha256
            ),
        },
        "images": [
            {
                "partition_name": (
                    image.partition_name
                ),
                "source_kind": (
                    image.source_kind
                ),
                "canonical": {
                    "source_path": str(
                        image.final_source_path
                    ),
                    "path": str(
                        image.final_path
                    ),
                    "size_bytes": (
                        image.final_size_bytes
                    ),
                    "sha256": (
                        image.final_sha256
                    ),
                },
            }
            for image
            in images
        ],
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return AndroidBootImageBaseDeployment(
        images=images,
        output_root=output_root,
        manifest_path=manifest_path,
        parsing_snapshot_path=(
            parsing_snapshot_path
        ),
        parsing_snapshot_sha256=(
            snapshot_sha256
        ),
    )


def load_base_boot_image_deployment(
    manifest_path: Path,
    *,
    parsing_snapshot_path: Path,
) -> AndroidBootImageBaseDeployment:
    """
    Reload and cryptographically validate an existing canonical base image
    population against the currently selected Parsing snapshot.
    """

    if not isinstance(
        manifest_path,
        Path,
    ):
        raise TypeError(
            "manifest_path must be a pathlib.Path"
        )

    if not isinstance(
        parsing_snapshot_path,
        Path,
    ):
        raise TypeError(
            "parsing_snapshot_path must be a pathlib.Path"
        )

    manifest_path = (
        manifest_path
        .expanduser()
        .resolve()
    )

    parsing_snapshot_path = (
        parsing_snapshot_path
        .expanduser()
        .resolve()
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "base Boot Image deployment manifest is unavailable: "
            f"{manifest_path}"
        )

    if not parsing_snapshot_path.is_file():
        raise FileNotFoundError(
            "canonical Parsing snapshot is unavailable: "
            f"{parsing_snapshot_path}"
        )

    raw = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if raw.get(
        "schema_version"
    ) != 1:
        raise RuntimeError(
            "unsupported base Boot Image manifest schema"
        )

    if raw.get(
        "deployment_kind"
    ) != "base":
        raise RuntimeError(
            "Boot Image manifest is not a base deployment"
        )

    parsing_identity = raw.get(
        "parsing_snapshot"
    )

    if not isinstance(
        parsing_identity,
        dict,
    ):
        raise RuntimeError(
            "base Boot Image manifest lost Parsing snapshot identity"
        )

    actual_snapshot_sha256 = (
        AndroidBootImageDeploymentPlanner
        ._file_identity(
            parsing_snapshot_path
        )[1]
    )

    if (
        actual_snapshot_sha256
        != parsing_identity.get(
            "sha256"
        )
    ):
        raise RuntimeError(
            "base Boot Image deployment belongs to a different "
            "Parsing snapshot"
        )

    raw_images = raw.get(
        "images"
    )

    if (
        not isinstance(
            raw_images,
            list,
        )
        or not raw_images
    ):
        raise RuntimeError(
            "base Boot Image deployment contains no images"
        )

    images = []

    for raw_image in raw_images:
        if not isinstance(
            raw_image,
            dict,
        ):
            raise RuntimeError(
                "invalid base Boot Image image record"
            )

        canonical = raw_image.get(
            "canonical"
        )

        if not isinstance(
            canonical,
            dict,
        ):
            raise RuntimeError(
                "base Boot Image image lost canonical identity"
            )

        path = Path(
            canonical[
                "path"
            ]
        ).resolve()

        source_path = Path(
            canonical[
                "source_path"
            ]
        ).resolve()

        expected_size = (
            canonical[
                "size_bytes"
            ]
        )

        expected_sha256 = (
            canonical[
                "sha256"
            ]
        )

        actual_identity = (
            AndroidBootImageDeploymentPlanner
            ._file_identity(
                path
            )
        )

        if actual_identity != (
            expected_size,
            expected_sha256,
        ):
            raise RuntimeError(
                "base Boot Image artifact failed identity "
                "verification: "
                f"{raw_image.get('partition_name')}"
            )

        source_identity = (
            AndroidBootImageDeploymentPlanner
            ._file_identity(
                source_path
            )
        )

        if source_identity != (
            expected_size,
            expected_sha256,
        ):
            raise RuntimeError(
                "canonical Parsing source changed for base "
                "Boot Image partition "
                f"{raw_image.get('partition_name')}"
            )

        images.append(
            AndroidBootImageDeploymentImage(
                partition_name=(
                    raw_image[
                        "partition_name"
                    ]
                ),
                source_kind=(
                    raw_image[
                        "source_kind"
                    ]
                ),
                final_source_path=(
                    source_path
                ),
                final_path=(
                    path
                ),
                final_size_bytes=(
                    expected_size
                ),
                final_sha256=(
                    expected_sha256
                ),
                rollback_source_path=(
                    source_path
                ),
                rollback_path=(
                    path
                ),
                rollback_size_bytes=(
                    expected_size
                ),
                rollback_sha256=(
                    expected_sha256
                ),
                rollback_required=True,
            )
        )

    return AndroidBootImageBaseDeployment(
        images=tuple(
            images
        ),
        output_root=(
            manifest_path.parent
        ),
        manifest_path=(
            manifest_path
        ),
        parsing_snapshot_path=(
            parsing_snapshot_path
        ),
        parsing_snapshot_sha256=(
            actual_snapshot_sha256
        ),
    )


def load_reusable_boot_image_deployment(
    manifest_path: Path,
    *,
    parsing_snapshot_path: Path,
    bootstrap_handoff_path: Path | None,
) -> AndroidBootImageReusableDeployment:
    """
    Load an already validated Boot Image deployment for hardware reuse.

    Reuse succeeds only when:
      - the manifest was created for the exact selected Parsing snapshot;
      - Bootstrap presence/absence matches the current invocation;
      - if Bootstrap applies, the exact handoff hash matches;
      - every modified image still has its recorded size/hash;
      - every canonical original image still has its recorded size/hash.

    This function never reconstructs a Validation object.
    """

    if not isinstance(
        manifest_path,
        Path,
    ):
        raise TypeError(
            "manifest_path must be a pathlib.Path"
        )

    if not isinstance(
        parsing_snapshot_path,
        Path,
    ):
        raise TypeError(
            "parsing_snapshot_path must be a pathlib.Path"
        )

    manifest_path = (
        manifest_path
        .expanduser()
        .resolve()
    )

    parsing_snapshot_path = (
        parsing_snapshot_path
        .expanduser()
        .resolve()
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Boot Image deployment manifest does not exist: "
            f"{manifest_path}"
        )

    if not parsing_snapshot_path.is_file():
        raise FileNotFoundError(
            "canonical Parsing snapshot does not exist: "
            f"{parsing_snapshot_path}"
        )

    raw = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if raw.get(
        "schema_version"
    ) != 1:
        raise RuntimeError(
            "unsupported Boot Image deployment manifest schema: "
            f"{raw.get('schema_version')!r}"
        )

    manifest_parsing = raw.get(
        "parsing_snapshot"
    )

    if not isinstance(
        manifest_parsing,
        dict,
    ):
        raise RuntimeError(
            "existing Boot Image deployment predates durable "
            "Parsing snapshot identity and cannot be reused"
        )

    actual_parsing_sha256 = (
        AndroidBootImageDeploymentPlanner
        ._file_identity(
            parsing_snapshot_path
        )[1]
    )

    expected_parsing_sha256 = (
        manifest_parsing.get(
            "sha256"
        )
    )

    if (
        actual_parsing_sha256
        != expected_parsing_sha256
    ):
        raise RuntimeError(
            "existing Boot Image deployment belongs to a different "
            "canonical Parsing snapshot"
        )

    manifest_bootstrap = raw.get(
        "bootstrap_handoff"
    )

    if bootstrap_handoff_path is None:
        if manifest_bootstrap is not None:
            raise RuntimeError(
                "existing Boot Image deployment was generated from "
                "a Bootstrap handoff, but this invocation did not "
                "request --bootstrap"
            )

        resolved_bootstrap_path = None
        resolved_bootstrap_sha256 = None

    else:
        bootstrap_handoff_path = (
            bootstrap_handoff_path
            .expanduser()
            .resolve()
        )

        if not bootstrap_handoff_path.is_file():
            raise FileNotFoundError(
                "Bootstrap handoff does not exist: "
                f"{bootstrap_handoff_path}"
            )

        if not isinstance(
            manifest_bootstrap,
            dict,
        ):
            raise RuntimeError(
                "existing Boot Image deployment was not generated "
                "from the requested Bootstrap handoff"
            )

        actual_bootstrap_sha256 = (
            AndroidBootImageDeploymentPlanner
            ._file_identity(
                bootstrap_handoff_path
            )[1]
        )

        expected_bootstrap_sha256 = (
            manifest_bootstrap.get(
                "sha256"
            )
        )

        if (
            actual_bootstrap_sha256
            != expected_bootstrap_sha256
        ):
            raise RuntimeError(
                "existing Boot Image deployment belongs to a different "
                "Bootstrap handoff"
            )

        resolved_bootstrap_path = (
            bootstrap_handoff_path
        )

        resolved_bootstrap_sha256 = (
            actual_bootstrap_sha256
        )

    if not raw.get(
        "flashable_chain_applicable"
    ):
        raise RuntimeError(
            "existing Boot Image deployment has no flashable "
            "changed-image population"
        )

    if not raw.get(
        "flashable_chain_complete"
    ):
        raise RuntimeError(
            "existing Boot Image deployment does not record a "
            "complete flashable chain"
        )

    if raw.get(
        "validation_disposition"
    ) != "pass":
        raise RuntimeError(
            "existing Boot Image deployment was not persisted from "
            "Validation PASS"
        )

    raw_images = raw.get(
        "images"
    )

    if (
        not isinstance(
            raw_images,
            list,
        )
        or not raw_images
    ):
        raise RuntimeError(
            "existing Boot Image deployment contains no images"
        )

    images = []

    for value in raw_images:
        if not isinstance(
            value,
            dict,
        ):
            raise RuntimeError(
                "existing Boot Image deployment contains an invalid "
                "image record"
            )

        final = value.get(
            "final"
        )

        rollback = value.get(
            "rollback"
        )

        if (
            not isinstance(
                final,
                dict,
            )
            or not isinstance(
                rollback,
                dict,
            )
        ):
            raise RuntimeError(
                "existing Boot Image deployment image record is "
                "missing final/rollback identity"
            )

        image = AndroidBootImageDeploymentImage(
            partition_name=(
                value[
                    "partition_name"
                ]
            ),
            source_kind=(
                value[
                    "source_kind"
                ]
            ),
            final_source_path=Path(
                final[
                    "source_path"
                ]
            ),
            final_path=Path(
                final[
                    "path"
                ]
            ),
            final_size_bytes=(
                final[
                    "size_bytes"
                ]
            ),
            final_sha256=(
                final[
                    "sha256"
                ]
            ),
            rollback_source_path=Path(
                rollback[
                    "source_path"
                ]
            ),
            rollback_path=Path(
                rollback[
                    "path"
                ]
            ),
            rollback_size_bytes=(
                rollback[
                    "size_bytes"
                ]
            ),
            rollback_sha256=(
                rollback[
                    "sha256"
                ]
            ),
            rollback_required=(
                rollback[
                    "required"
                ]
            ),
        )

        actual_final = (
            AndroidBootImageDeploymentPlanner
            ._file_identity(
                image.final_path
            )
        )

        if actual_final != (
            image.final_size_bytes,
            image.final_sha256,
        ):
            raise RuntimeError(
                "existing modified Boot Image failed identity "
                "verification: "
                f"{image.partition_name}"
            )

        actual_rollback = (
            AndroidBootImageDeploymentPlanner
            ._file_identity(
                image.rollback_path
            )
        )

        if actual_rollback != (
            image.rollback_size_bytes,
            image.rollback_sha256,
        ):
            raise RuntimeError(
                "existing original Boot Image failed identity "
                "verification: "
                f"{image.partition_name}"
            )

        images.append(
            image
        )

    return AndroidBootImageReusableDeployment(
        images=tuple(
            images
        ),
        output_root=(
            manifest_path.parent
        ),
        manifest_path=(
            manifest_path
        ),
        parsing_snapshot_path=(
            parsing_snapshot_path
        ),
        parsing_snapshot_sha256=(
            actual_parsing_sha256
        ),
        bootstrap_handoff_path=(
            resolved_bootstrap_path
        ),
        bootstrap_handoff_sha256=(
            resolved_bootstrap_sha256
        ),
    )


def export_boot_image_deployment(
    deployment: AndroidBootImageDeploymentPlan,
    *,
    output_root: Path,
) -> Path:
    """
    Export both the validated modified images and their exact canonical
    originals for later manual or TreeForge-driven deployment.
    """

    if not isinstance(
        deployment,
        AndroidBootImageDeploymentPlan,
    ):
        raise TypeError(
            "deployment must be an AndroidBootImageDeploymentPlan"
        )

    if not isinstance(
        output_root,
        Path,
    ):
        raise TypeError(
            "output_root must be a pathlib.Path"
        )

    if output_root.exists():
        shutil.rmtree(
            output_root
        )

    modified_root = (
        output_root
        / "modified"
    )

    original_root = (
        output_root
        / "original"
    )

    modified_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    original_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    exported = []

    for image in deployment.images:
        modified_path = (
            modified_root
            / f"{image.partition_name}.img"
        )

        original_path = (
            original_root
            / f"{image.partition_name}.img"
        )

        modified_size, modified_digest = (
            AndroidBootImageDeploymentPlanner
            ._copy_exact(
                image.final_path,
                modified_path,
            )
        )

        original_size, original_digest = (
            AndroidBootImageDeploymentPlanner
            ._copy_exact(
                image.rollback_path,
                original_path,
            )
        )

        if (
            modified_size
            != image.final_size_bytes
            or modified_digest
            != image.final_sha256
        ):
            raise RuntimeError(
                "exported modified Boot Image lost exact identity: "
                f"{image.partition_name}"
            )

        if (
            original_size
            != image.rollback_size_bytes
            or original_digest
            != image.rollback_sha256
        ):
            raise RuntimeError(
                "exported original Boot Image lost exact identity: "
                f"{image.partition_name}"
            )

        exported.append(
            {
                "partition_name": image.partition_name,
                "modified": {
                    "path": str(modified_path),
                    "size_bytes": modified_size,
                    "sha256": modified_digest,
                },
                "original": {
                    "path": str(original_path),
                    "size_bytes": original_size,
                    "sha256": original_digest,
                },
            }
        )

    manifest_path = (
        output_root
        / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "images": exported,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest_path


__all__ = (
    "AndroidBootImageBaseDeployment",
    "build_base_boot_image_deployment",
    "load_base_boot_image_deployment",
    "AndroidBootImageDeploymentImage",
    "AndroidBootImageDeploymentPlan",
    "AndroidBootImageReusableDeployment",
    "AndroidBootImageDeploymentPlanner",
    "load_reusable_boot_image_deployment",
    "export_boot_image_deployment",
)
