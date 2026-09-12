from __future__ import annotations

from pathlib import Path

from treeforge.android.parsing.result import (
    AndroidParsingResult,
)
from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)

from treeforge.android.bootstrap.intake import (
    AndroidBootstrapIntake,
)
from treeforge.android.bootstrap.models import (
    BOOTSTRAP_PHASE_COUNT,
)
from treeforge.android.bootstrap.result import (
    AndroidBootstrapIntakeResult,
)
from treeforge.android.bootstrap.planning import (
    AndroidBootstrapEnvironmentPlan,
    AndroidBootstrapEnvironmentPlanner,
)
from treeforge.android.bootstrap.realization import (
    AndroidBootstrapEnvironmentRealizationResult,
    AndroidBootstrapEnvironmentRealizer,
)

from treeforge.android.bootstrap.runtime_provider import (
    AndroidBootstrapRuntimeProvider,
)
from treeforge.android.bootstrap.deployment_planning import (
    AndroidBootstrapDeploymentPlan,
    AndroidBootstrapDeploymentPlanner,
)


class AndroidBootstrapPipeline:
    """
    Bootstrap workflow coordinator.

    Intake, Environment Planning, Environment Realization, and Deployment
    Planning are implemented at this boundary.

    Remaining owned phases will be added explicitly:

      5. Device Deployment / Boot Image handoff
      6. Hardware Validation / Rollback

    The pipeline deliberately does not claim those phases are complete yet.
    """

    def __init__(
        self,
        *,
        intake: AndroidBootstrapIntake | None = None,
        environment_planner: (
            AndroidBootstrapEnvironmentPlanner | None
        ) = None,
        environment_realizer: (
            AndroidBootstrapEnvironmentRealizer | None
        ) = None,
        deployment_planner: (
            AndroidBootstrapDeploymentPlanner | None
        ) = None,
    ) -> None:
        self.intake = (
            intake
            if intake is not None
            else AndroidBootstrapIntake()
        )

        if not isinstance(
            self.intake,
            AndroidBootstrapIntake,
        ):
            raise TypeError(
                "intake must be an AndroidBootstrapIntake"
            )

        self.environment_planner = (
            environment_planner
            if environment_planner is not None
            else AndroidBootstrapEnvironmentPlanner()
        )

        if not isinstance(
            self.environment_planner,
            AndroidBootstrapEnvironmentPlanner,
        ):
            raise TypeError(
                "environment_planner must be an "
                "AndroidBootstrapEnvironmentPlanner"
            )

        self.environment_realizer = (
            environment_realizer
            if environment_realizer is not None
            else AndroidBootstrapEnvironmentRealizer()
        )

        if not isinstance(
            self.environment_realizer,
            AndroidBootstrapEnvironmentRealizer,
        ):
            raise TypeError(
                "environment_realizer must be an "
                "AndroidBootstrapEnvironmentRealizer"
            )

        self.deployment_planner = (
            deployment_planner
            if deployment_planner is not None
            else AndroidBootstrapDeploymentPlanner()
        )

        if not isinstance(
            self.deployment_planner,
            AndroidBootstrapDeploymentPlanner,
        ):
            raise TypeError(
                "deployment_planner must be an "
                "AndroidBootstrapDeploymentPlanner"
            )

    @staticmethod
    def _emit_progress(
        progress_callback: ProgressCallback | None,
        *,
        current: int,
        phase_name: str,
        state: ProgressState,
    ) -> None:
        if progress_callback is None:
            return

        progress_callback(
            ProgressEvent(
                stage="Bootstrap",
                state=state,
                current=current,
                total=BOOTSTRAP_PHASE_COUNT,
                subject=phase_name,
                operation=state.value,
            )
        )

    def execute_intake(
        self,
        parsing: AndroidParsingResult,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> AndroidBootstrapIntakeResult:
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        self._emit_progress(
            progress_callback,
            current=0,
            phase_name="Intake",
            state=ProgressState.STARTING,
        )

        result = self.intake.build(
            parsing
        )

        if result.parsing is not parsing:
            raise RuntimeError(
                "Bootstrap Intake lost exact "
                "AndroidParsingResult identity"
            )

        self._emit_progress(
            progress_callback,
            current=1,
            phase_name="Intake",
            state=ProgressState.COMPLETE,
        )

        return result

    def execute_planning(
        self,
        parsing: AndroidParsingResult,
        *,
        progress_callback: ProgressCallback | None = None,
        hardware: str | None = None,
    ) -> AndroidBootstrapEnvironmentPlan:
        intake = self.execute_intake(
            parsing,
            progress_callback=progress_callback,
        )

        self._emit_progress(
            progress_callback,
            current=1,
            phase_name="Environment Planning",
            state=ProgressState.STARTING,
        )

        environment_planner = (
            self.environment_planner
            if hardware is None
            else AndroidBootstrapEnvironmentPlanner(
                hardware=hardware,
            )
        )

        result = environment_planner.build(
            intake
        )

        if result.intake is not intake:
            raise RuntimeError(
                "Bootstrap Environment Planning lost exact "
                "Intake identity"
            )

        if result.boot_image_interpretation.parsing is not parsing:
            raise RuntimeError(
                "Bootstrap Environment Planning lost exact "
                "AndroidParsingResult identity"
            )

        self._emit_progress(
            progress_callback,
            current=2,
            phase_name="Environment Planning",
            state=ProgressState.COMPLETE,
        )

        return result


    def execute_realization(
        self,
        parsing: AndroidParsingResult,
        *,
        rootfs: Path,
        runtime_provider: AndroidBootstrapRuntimeProvider | None = None,
        progress_callback: ProgressCallback | None = None,
        hardware: str | None = None,
    ) -> AndroidBootstrapEnvironmentRealizationResult:
        if not isinstance(
            rootfs,
            Path,
        ):
            raise TypeError(
                "rootfs must be a Path"
            )

        plan = self.execute_planning(
            parsing,
            progress_callback=progress_callback,
            hardware=hardware,
        )

        self._emit_progress(
            progress_callback,
            current=2,
            phase_name="Environment Realization",
            state=ProgressState.STARTING,
        )

        result = self.environment_realizer.realize(
            plan,
            rootfs=rootfs,
            runtime_provider=runtime_provider,
        )

        if result.plan is not plan:
            raise RuntimeError(
                "Bootstrap Environment Realization lost exact "
                "Environment Planning identity"
            )

        if result.plan.intake.parsing is not parsing:
            raise RuntimeError(
                "Bootstrap Environment Realization lost exact "
                "AndroidParsingResult identity"
            )

        self._emit_progress(
            progress_callback,
            current=3,
            phase_name="Environment Realization",
            state=ProgressState.COMPLETE,
        )

        return result


    def execute_deployment_planning(
        self,
        parsing: AndroidParsingResult,
        *,
        rootfs: Path,
        replacement_path: Path,
        runtime_provider: AndroidBootstrapRuntimeProvider | None = None,
        progress_callback: ProgressCallback | None = None,
        hardware: str | None = None,
    ) -> AndroidBootstrapDeploymentPlan:
        if not isinstance(
            replacement_path,
            Path,
        ):
            raise TypeError(
                "replacement_path must be a Path"
            )

        environment_realization = self.execute_realization(
            parsing,
            rootfs=rootfs,
            runtime_provider=runtime_provider,
            progress_callback=progress_callback,
            hardware=hardware,
        )

        self._emit_progress(
            progress_callback,
            current=3,
            phase_name="Deployment Planning",
            state=ProgressState.STARTING,
        )

        result = self.deployment_planner.build(
            environment_realization,
            replacement_path=replacement_path,
        )

        if (
            result.environment_realization
            is not environment_realization
        ):
            raise RuntimeError(
                "Bootstrap Deployment Planning lost exact "
                "Environment Realization identity"
            )

        if result.parsing is not parsing:
            raise RuntimeError(
                "Bootstrap Deployment Planning lost exact "
                "AndroidParsingResult identity"
            )

        self._emit_progress(
            progress_callback,
            current=4,
            phase_name="Deployment Planning",
            state=ProgressState.COMPLETE,
        )

        return result


__all__ = (
    "AndroidBootstrapPipeline",
)
