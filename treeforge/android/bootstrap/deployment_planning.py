from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from treeforge.android.boot_image.composition import (
    AndroidBootImageComposer,
)
from treeforge.android.boot_image.planning import (
    AndroidBootImageBootImagePlan,
    AndroidBootImageComponentPlan,
    AndroidBootImagePlanner,
    AndroidBootImagePlanningResult,
)
from treeforge.android.bootstrap.realization import (
    AndroidBootstrapEnvironmentRealizationResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapBootImageHandoff:
    """
    Stable Bootstrap -> Boot Image component-mutation handoff.

    The exact Boot Image Planning identities are retained separately by
    AndroidBootstrapDeploymentPlan for the live Bootstrap execution.

    These locator fields are intentionally sufficient for a later independent
    Boot Image run to resolve the target again from the same canonical Parsing
    boundary.

    No AVB policy, signing key, provider, slot, transport, or flash decision
    belongs here.
    """

    container_kind: str
    semantic_name: str

    replacement_path: Path

    original_component_path: Path
    original_component_size_bytes: int
    original_component_sha256: str

    rollback_required: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(
                self.container_kind,
                str,
            )
            or not self.container_kind
        ):
            raise ValueError(
                "container_kind must be a non-empty string"
            )

        if (
            not isinstance(
                self.semantic_name,
                str,
            )
            or not self.semantic_name
        ):
            raise ValueError(
                "semantic_name must be a non-empty string"
            )

        if not isinstance(
            self.replacement_path,
            Path,
        ):
            raise TypeError(
                "replacement_path must be a Path"
            )

        if not isinstance(
            self.original_component_path,
            Path,
        ):
            raise TypeError(
                "original_component_path must be a Path"
            )

        if (
            not isinstance(
                self.original_component_size_bytes,
                int,
            )
            or self.original_component_size_bytes < 0
        ):
            raise ValueError(
                "original_component_size_bytes must be a non-negative int"
            )

        if (
            not isinstance(
                self.original_component_sha256,
                str,
            )
            or len(
                self.original_component_sha256
            ) != 64
        ):
            raise ValueError(
                "original_component_sha256 must be a SHA-256 hex digest"
            )

        if not isinstance(
            self.rollback_required,
            bool,
        ):
            raise TypeError(
                "rollback_required must be bool"
            )

    @property
    def replacement_ready(
        self,
    ) -> bool:
        return self.replacement_path.is_file()


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapDeploymentPlan:
    """
    First-class Bootstrap Deployment Planning boundary.

    Bootstrap retains exact live Boot Image Planning identities while also
    producing a stable handoff locator suitable for a later independent
    ``treeforge boot-image --bootstrap`` execution.

    This phase does not package the ramdisk, rebuild an image, select signing
    policy, invoke fastboot, choose a slot, or mutate hardware.
    """

    environment_realization: (
        AndroidBootstrapEnvironmentRealizationResult
    )

    boot_image_planning: AndroidBootImagePlanningResult

    target_image: AndroidBootImageBootImagePlan
    target_component: AndroidBootImageComponentPlan

    handoff: AndroidBootstrapBootImageHandoff

    def __post_init__(self) -> None:
        if not isinstance(
            self.environment_realization,
            AndroidBootstrapEnvironmentRealizationResult,
        ):
            raise TypeError(
                "environment_realization must be an "
                "AndroidBootstrapEnvironmentRealizationResult"
            )

        if not isinstance(
            self.boot_image_planning,
            AndroidBootImagePlanningResult,
        ):
            raise TypeError(
                "boot_image_planning must be an "
                "AndroidBootImagePlanningResult"
            )

        if not isinstance(
            self.target_image,
            AndroidBootImageBootImagePlan,
        ):
            raise TypeError(
                "target_image must be an AndroidBootImageBootImagePlan"
            )

        if not isinstance(
            self.target_component,
            AndroidBootImageComponentPlan,
        ):
            raise TypeError(
                "target_component must be an AndroidBootImageComponentPlan"
            )

        if not isinstance(
            self.handoff,
            AndroidBootstrapBootImageHandoff,
        ):
            raise TypeError(
                "handoff must be an AndroidBootstrapBootImageHandoff"
            )

        parsing = (
            self.environment_realization
            .plan
            .intake
            .parsing
        )

        if (
            self.boot_image_planning.parsing
            is not parsing
        ):
            raise ValueError(
                "Deployment Planning must retain exact canonical "
                "AndroidParsingResult identity"
            )

        if not any(
            image is self.target_image
            for image
            in self.boot_image_planning.boot_images
        ):
            raise ValueError(
                "target_image must belong to the exact Boot Image "
                "Planning result"
            )

        if not any(
            component is self.target_component
            for component
            in self.target_image.component_plans
        ):
            raise ValueError(
                "target_component must belong to the exact target image"
            )

        if (
            self.handoff.container_kind
            != self.target_image.container_kind
        ):
            raise ValueError(
                "handoff container_kind must match the exact target image"
            )

        if (
            self.handoff.semantic_name
            != self.target_component.component.semantic_name
        ):
            raise ValueError(
                "handoff semantic_name must match the exact target component"
            )

        if (
            self.handoff.original_component_path
            != self.target_component.component.artifact.path
        ):
            raise ValueError(
                "handoff original component must match exact target component"
            )

    @property
    def parsing(self):
        return (
            self.environment_realization
            .plan
            .intake
            .parsing
        )


class AndroidBootstrapDeploymentPlanningError(
    RuntimeError
):
    """
    Raised when Bootstrap cannot derive one exact Boot Image handoff target.
    """


class AndroidBootstrapDeploymentPlanner:
    """
    Derive the Bootstrap -> Boot Image handoff.

    Target resolution is by exact canonical ramdisk component artifact
    identity. Container names are outputs of that resolution, never device
    policy inputs.
    """

    def __init__(
        self,
        *,
        composer: AndroidBootImageComposer | None = None,
        planner: AndroidBootImagePlanner | None = None,
    ) -> None:
        self.composer = (
            composer
            if composer is not None
            else AndroidBootImageComposer()
        )

        if not isinstance(
            self.composer,
            AndroidBootImageComposer,
        ):
            raise TypeError(
                "composer must be an AndroidBootImageComposer"
            )

        self.planner = (
            planner
            if planner is not None
            else AndroidBootImagePlanner()
        )

        if not isinstance(
            self.planner,
            AndroidBootImagePlanner,
        ):
            raise TypeError(
                "planner must be an AndroidBootImagePlanner"
            )

    @staticmethod
    def _sha256_file(
        path: Path,
    ) -> str:
        digest = sha256()

        with path.open(
            "rb"
        ) as handle:
            for chunk in iter(
                lambda: handle.read(
                    1024 * 1024
                ),
                b"",
            ):
                digest.update(
                    chunk
                )

        return digest.hexdigest()

    def build(
        self,
        environment_realization: (
            AndroidBootstrapEnvironmentRealizationResult
        ),
        *,
        replacement_path: Path,
    ) -> AndroidBootstrapDeploymentPlan:
        if not isinstance(
            environment_realization,
            AndroidBootstrapEnvironmentRealizationResult,
        ):
            raise TypeError(
                "environment_realization must be an "
                "AndroidBootstrapEnvironmentRealizationResult"
            )

        if not isinstance(
            replacement_path,
            Path,
        ):
            raise TypeError(
                "replacement_path must be a Path"
            )

        environment_plan = (
            environment_realization.plan
        )

        candidate = (
            environment_plan
            .environment_root
            .candidate
        )

        if candidate is None:
            raise AndroidBootstrapDeploymentPlanningError(
                "Bootstrap environment root did not resolve"
            )

        interpretation = (
            environment_plan
            .boot_image_interpretation
        )

        composition = self.composer.build(
            interpretation
        )

        if (
            composition.interpretation
            is not interpretation
        ):
            raise RuntimeError(
                "Bootstrap Deployment Planning lost exact Boot Image "
                "Interpretation identity"
            )

        boot_image_planning = self.planner.build(
            composition
        )

        if (
            boot_image_planning.composition
            is not composition
        ):
            raise RuntimeError(
                "Bootstrap Deployment Planning lost exact Boot Image "
                "Composition identity"
            )

        parsing = (
            environment_plan
            .intake
            .parsing
        )

        if (
            boot_image_planning.parsing
            is not parsing
        ):
            raise RuntimeError(
                "Bootstrap Deployment Planning lost exact "
                "AndroidParsingResult identity"
            )

        selected_component_artifact = (
            candidate
            .ramdisk
            .ramdisk
            .ramdisk_component
        )

        matches = tuple(
            (
                image,
                component
            )
            for image
            in boot_image_planning.boot_images
            for component
            in image.component_plans
            if (
                component
                .component
                .artifact
                is selected_component_artifact
            )
        )

        if len(
            matches
        ) != 1:
            raise AndroidBootstrapDeploymentPlanningError(
                "Bootstrap-selected ramdisk must resolve exactly one "
                "Boot Image component plan; "
                f"found {len(matches)}"
            )

        (
            target_image,
            target_component,
        ) = matches[0]

        original_component_path = (
            target_component
            .component
            .artifact
            .path
        )

        if not original_component_path.is_file():
            raise AndroidBootstrapDeploymentPlanningError(
                "canonical original target component is not materialized: "
                f"{original_component_path}"
            )

        handoff = AndroidBootstrapBootImageHandoff(
            container_kind=(
                target_image.container_kind
            ),
            semantic_name=(
                target_component
                .component
                .semantic_name
            ),
            replacement_path=(
                replacement_path
            ),
            original_component_path=(
                original_component_path
            ),
            original_component_size_bytes=(
                original_component_path
                .stat()
                .st_size
            ),
            original_component_sha256=(
                self._sha256_file(
                    original_component_path
                )
            ),
            rollback_required=True,
        )

        result = AndroidBootstrapDeploymentPlan(
            environment_realization=(
                environment_realization
            ),
            boot_image_planning=(
                boot_image_planning
            ),
            target_image=(
                target_image
            ),
            target_component=(
                target_component
            ),
            handoff=(
                handoff
            ),
        )

        if (
            result.environment_realization
            is not environment_realization
        ):
            raise RuntimeError(
                "Deployment Planning lost exact Environment Realization "
                "identity"
            )

        return result


__all__ = (
    "AndroidBootstrapBootImageHandoff",
    "AndroidBootstrapDeploymentPlan",
    "AndroidBootstrapDeploymentPlanner",
    "AndroidBootstrapDeploymentPlanningError",
)
