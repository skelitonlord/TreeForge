from __future__ import annotations

from enum import StrEnum


class AndroidBootstrapPhase(StrEnum):
    """
    First-class Bootstrap workflow phases.

    Bootstrap owns recovery/bootstrap environment derivation and device
    deployment orchestration. Boot Image remains the owner of boot-family
    image reconstruction, AVB regeneration, signing, and validation.
    """

    INTAKE = "intake"
    ENVIRONMENT_PLANNING = "environment_planning"
    ENVIRONMENT_REALIZATION = "environment_realization"
    DEPLOYMENT_PLANNING = "deployment_planning"
    DEVICE_DEPLOYMENT = "device_deployment"
    HARDWARE_VALIDATION = "hardware_validation"


BOOTSTRAP_PHASE_COUNT = len(
    AndroidBootstrapPhase
)


__all__ = (
    "AndroidBootstrapPhase",
    "BOOTSTRAP_PHASE_COUNT",
)
