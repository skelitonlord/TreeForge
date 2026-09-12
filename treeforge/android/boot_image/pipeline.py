from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from treeforge.core.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressState,
)

from treeforge.android.boot_image.composition import (
    AndroidBootImageComposer,
)
from treeforge.android.boot_image.intake import (
    AndroidBootImageIntake,
)
from treeforge.android.boot_image.planning import (
    AndroidBootImagePlanner,
)
from treeforge.android.boot_image.realization import (
    AndroidBootImageMutationRequest,
    AndroidBootImageRealizationResult,
    AndroidBootImageRealizer,
)
from treeforge.android.boot_image.interpretation import (
    AndroidBootImageInterpreter,
)
from treeforge.android.boot_image.validation import (
    AndroidBootImageValidationResult,
    AndroidBootImageValidator,
)
from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootImageComponentMutationSpec:
    """
    External mutation intent resolved only after Planning exists.

    Realization still receives AndroidBootImageMutationRequest with exact
    AndroidBootImageComponentPlan identity.
    """

    container_kind: str
    semantic_name: str
    replacement_path: Path

    def __post_init__(self) -> None:
        if (
            not isinstance(self.container_kind, str)
            or not self.container_kind
        ):
            raise ValueError(
                "container_kind must be a non-empty string"
            )

        if (
            not isinstance(self.semantic_name, str)
            or not self.semantic_name
        ):
            raise ValueError(
                "semantic_name must be a non-empty string"
            )

        if not isinstance(self.replacement_path, Path):
            raise TypeError(
                "replacement_path must be a pathlib.Path"
            )

        if not self.replacement_path.is_file():
            raise FileNotFoundError(
                "Boot Image mutation replacement does not exist: "
                f"{self.replacement_path}"
            )


class AndroidBootImagePipeline:
    """
    Boot Image branch pipeline.

    Parsing intake is followed by Boot Image-owned Interpretation,
    Composition, Planning, Realization, and Validation subphases.
    """

    def __init__(
        self,
        *,
        intake: AndroidBootImageIntake | None = None,
        interpreter: AndroidBootImageInterpreter | None = None,
        composer: AndroidBootImageComposer | None = None,
        planner: AndroidBootImagePlanner | None = None,
        realizer: AndroidBootImageRealizer | None = None,
        validator: AndroidBootImageValidator | None = None,
    ) -> None:
        self.intake = (
            intake
            if intake is not None
            else AndroidBootImageIntake()
        )

        self.interpreter = (
            interpreter
            if interpreter is not None
            else AndroidBootImageInterpreter()
        )

        self.composer = (
            composer
            if composer is not None
            else AndroidBootImageComposer()
        )

        self.planner = (
            planner
            if planner is not None
            else AndroidBootImagePlanner()
        )

        self.realizer = (
            realizer
            if realizer is not None
            else AndroidBootImageRealizer()
        )

        self.validator = (
            validator
            if validator is not None
            else AndroidBootImageValidator()
        )

        if not isinstance(
            self.intake,
            AndroidBootImageIntake,
        ):
            raise TypeError(
                "intake must be an AndroidBootImageIntake"
            )

        if not isinstance(
            self.interpreter,
            AndroidBootImageInterpreter,
        ):
            raise TypeError(
                "interpreter must be an AndroidBootImageInterpreter"
            )

        if not isinstance(
            self.composer,
            AndroidBootImageComposer,
        ):
            raise TypeError(
                "composer must be an AndroidBootImageComposer"
            )

        if not isinstance(
            self.planner,
            AndroidBootImagePlanner,
        ):
            raise TypeError(
                "planner must be an AndroidBootImagePlanner"
            )

        if not isinstance(
            self.realizer,
            AndroidBootImageRealizer,
        ):
            raise TypeError(
                "realizer must be an AndroidBootImageRealizer"
            )

        if not isinstance(
            self.validator,
            AndroidBootImageValidator,
        ):
            raise TypeError(
                "validator must be an AndroidBootImageValidator"
            )

    def execute(
        self,
        parsing: AndroidParsingResult,
        *,
        realization_root: Path,
        mutation_requests: tuple[
            AndroidBootImageMutationRequest,
            ...,
        ] = (),
        mutation_specs: tuple[
            AndroidBootImageComponentMutationSpec,
            ...,
        ] = (),
        avb_signing_key: Path | None = None,
        avb_signing_keys: tuple[
            tuple[
                str,
                Path,
            ],
            ...,
        ] = (),
        parent_vbmeta_signing_key: Path | None = None,
        vbmeta_signing_keys: tuple[
            tuple[
                str,
                Path,
            ],
            ...,
        ] = (),
        progress_callback: ProgressCallback | None = None,
    ) -> AndroidBootImageValidationResult:
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        def emit_progress(
            *,
            phase_index: int,
            phase_name: str,
            state: ProgressState,
        ) -> None:
            if progress_callback is None:
                return

            progress_callback(
                ProgressEvent(
                    stage="Boot Image",
                    state=state,
                    current=phase_index,
                    total=6,
                    subject=phase_name,
                    operation=state.value,
                )
            )

        emit_progress(
            phase_index=0,
            phase_name="Intake",
            state=ProgressState.STARTING,
        )

        intake_result = self.intake.build(
            parsing
        )

        emit_progress(
            phase_index=1,
            phase_name="Intake",
            state=ProgressState.COMPLETE,
        )

        emit_progress(
            phase_index=1,
            phase_name="Interpretation",
            state=ProgressState.STARTING,
        )

        interpretation_result = (
            self.interpreter.build(
                intake_result
            )
        )

        if (
            interpretation_result.parsing
            is not parsing
        ):
            raise RuntimeError(
                "Boot Image Interpretation must preserve exact "
                "AndroidParsingResult identity"
            )

        emit_progress(
            phase_index=2,
            phase_name="Interpretation",
            state=ProgressState.COMPLETE,
        )

        emit_progress(
            phase_index=2,
            phase_name="Composition",
            state=ProgressState.STARTING,
        )

        composition_result = self.composer.build(
            interpretation_result
        )

        if (
            composition_result.interpretation
            is not interpretation_result
        ):
            raise RuntimeError(
                "Boot Image Composition must preserve exact "
                "Interpretation result identity"
            )

        if composition_result.parsing is not parsing:
            raise RuntimeError(
                "Boot Image Composition must preserve exact "
                "AndroidParsingResult identity"
            )

        emit_progress(
            phase_index=3,
            phase_name="Composition",
            state=ProgressState.COMPLETE,
        )

        emit_progress(
            phase_index=3,
            phase_name="Planning",
            state=ProgressState.STARTING,
        )

        planning_result = self.planner.build(
            composition_result
        )

        if (
            planning_result.composition
            is not composition_result
        ):
            raise RuntimeError(
                "Boot Image Planning must preserve exact "
                "Composition result identity"
            )

        if planning_result.parsing is not parsing:
            raise RuntimeError(
                "Boot Image Planning must preserve exact "
                "AndroidParsingResult identity"
            )

        if mutation_requests and mutation_specs:
            raise ValueError(
                "use either exact mutation_requests or external "
                "mutation_specs, not both"
            )

        resolved_mutation_requests = mutation_requests

        if mutation_specs:
            resolved = []

            for spec in mutation_specs:
                matches = tuple(
                    plan
                    for image
                    in planning_result.boot_images
                    if image.container_kind == spec.container_kind
                    for plan
                    in image.component_plans
                    if (
                        plan.component.semantic_name
                        == spec.semantic_name
                    )
                )

                if len(matches) != 1:
                    raise ValueError(
                        "Boot Image mutation specification must "
                        "resolve exactly one component plan: "
                        f"{spec.container_kind}:"
                        f"{spec.semantic_name}; "
                        f"found {len(matches)}"
                    )

                resolved.append(
                    AndroidBootImageMutationRequest(
                        target=matches[0],
                        replacement_path=(
                            spec.replacement_path
                        ),
                    )
                )

            if len(
                {id(value.target) for value in resolved}
            ) != len(resolved):
                raise ValueError(
                    "multiple mutation specifications resolved "
                    "to the same component plan"
                )

            resolved_mutation_requests = tuple(
                resolved
            )

        # TREEFORGE_BOOT_MARKER_PIPELINE_V1
        #
        # Identity marking is pipeline-authorized mutation policy, not a
        # Realization inference. Base/untouched images receive no marker.
        # When vendor_boot already has one byte-changing ramdisk mutation,
        # derive a second explicit mutation for the canonical bootconfig.
        #
        # The canonical bootconfig remains an exact byte prefix. TreeForge
        # appends only the three runtime identity entries below.
        #
        marker_augmented_requests = list(
            resolved_mutation_requests
        )

        for image_plan in planning_result.boot_images:
            if image_plan.container_kind != "vendor_boot":
                continue

            image_requests = tuple(
                request
                for request in resolved_mutation_requests
                if any(
                    request.target is plan
                    for plan
                    in image_plan.component_plans
                )
            )

            if not image_requests:
                continue

            explicit_bootconfig_requests = tuple(
                request
                for request in image_requests
                if (
                    request
                    .target
                    .component
                    .semantic_name
                    == "bootconfig"
                )
            )

            if explicit_bootconfig_requests:
                raise ValueError(
                    "vendor_boot bootconfig mutation is reserved for "
                    "the TreeForge runtime identity marker while the "
                    "automatic marker contract is active"
                )

            def file_identity(path: Path) -> tuple[int, str]:
                digest = sha256()

                with path.open("rb") as stream:
                    for chunk in iter(
                        lambda: stream.read(1024 * 1024),
                        b"",
                    ):
                        digest.update(chunk)

                return (
                    path.stat().st_size,
                    digest.hexdigest(),
                )

            changed_requests = []

            for request in image_requests:
                original_path = (
                    request
                    .target
                    .component
                    .artifact
                    .path
                )

                original_identity = file_identity(
                    original_path
                )
                replacement_identity = file_identity(
                    request.replacement_path
                )

                if (
                    original_identity
                    != replacement_identity
                ):
                    changed_requests.append(
                        (
                            request,
                            replacement_identity,
                        )
                    )

            if not changed_requests:
                continue

            if (
                len(changed_requests) != 1
                or (
                    changed_requests[0][0]
                    .target
                    .component
                    .semantic_name
                    != "ramdisk"
                )
            ):
                raise RuntimeError(
                    "automatic TreeForge vendor_boot identity marking "
                    "currently requires exactly one pre-marker changed "
                    "component and it must be the complete ramdisk"
                )

            bootconfig_plans = tuple(
                plan
                for plan
                in image_plan.component_plans
                if (
                    plan.component.semantic_name
                    == "bootconfig"
                )
            )

            if len(bootconfig_plans) != 1:
                raise RuntimeError(
                    "modified vendor_boot requires exactly one canonical "
                    "bootconfig component for TreeForge identity marking; "
                    f"found {len(bootconfig_plans)}"
                )

            bootconfig_plan = bootconfig_plans[0]
            canonical_bootconfig_path = (
                bootconfig_plan
                .component
                .artifact
                .path
            )

            if not canonical_bootconfig_path.is_file():
                raise FileNotFoundError(
                    "canonical vendor_boot bootconfig is unavailable: "
                    f"{canonical_bootconfig_path}"
                )

            canonical_bootconfig = (
                canonical_bootconfig_path
                .read_bytes()
            )

            marker_keys = (
                b"androidboot.treeforge",
                b"androidboot.treeforge.image",
                b"androidboot.treeforge.payload_sha256",
            )

            canonical_lines = (
                canonical_bootconfig
                .splitlines()
            )

            for marker_key in marker_keys:
                prefix = marker_key + b"="

                if any(
                    line.startswith(prefix)
                    for line
                    in canonical_lines
                ):
                    raise RuntimeError(
                        "canonical vendor_boot bootconfig already "
                        "contains a reserved TreeForge marker key: "
                        f"{marker_key.decode('ascii')}"
                    )

            payload_sha256 = (
                changed_requests[0][1][1]
            )

            marker = (
                b"androidboot.treeforge=1\n"
                + (
                    "androidboot.treeforge.image="
                    f"{image_plan.container_kind}\n"
                ).encode("ascii")
                + (
                    "androidboot.treeforge.payload_sha256="
                    f"{payload_sha256}\n"
                ).encode("ascii")
            )

            separator = (
                b""
                if (
                    not canonical_bootconfig
                    or canonical_bootconfig.endswith(
                        b"\n"
                    )
                )
                else b"\n"
            )

            marker_path = (
                realization_root.parent
                / "generated-inputs"
                / "treeforge-marker"
                / (
                    f"{image_plan.container_kind}"
                    ".bootconfig"
                )
            )

            marker_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            marker_path.write_bytes(
                canonical_bootconfig
                + separator
                + marker
            )

            marker_augmented_requests.append(
                AndroidBootImageMutationRequest(
                    target=bootconfig_plan,
                    replacement_path=marker_path,
                )
            )

        resolved_mutation_requests = tuple(
            marker_augmented_requests
        )

        emit_progress(
            phase_index=4,
            phase_name="Planning",
            state=ProgressState.COMPLETE,
        )

        emit_progress(
            phase_index=4,
            phase_name="Realization",
            state=ProgressState.STARTING,
        )

        result = self.realizer.build(
            planning_result,
            output_root=realization_root,
            mutation_requests=(
                resolved_mutation_requests
            ),
            avb_signing_key=avb_signing_key,
            avb_signing_keys=(
                avb_signing_keys
            ),
            parent_vbmeta_signing_key=(
                parent_vbmeta_signing_key
            ),
            vbmeta_signing_keys=(
                vbmeta_signing_keys
            ),
        )

        if result.planning is not planning_result:
            raise RuntimeError(
                "Boot Image Realization must preserve exact "
                "Planning result identity"
            )

        if result.parsing is not parsing:
            raise RuntimeError(
                "Boot Image Realization must preserve exact "
                "AndroidParsingResult identity"
            )

        emit_progress(
            phase_index=5,
            phase_name="Realization",
            state=ProgressState.COMPLETE,
        )

        emit_progress(
            phase_index=5,
            phase_name="Validation",
            state=ProgressState.STARTING,
        )

        validation_result = (
            self.validator.build(
                result,
                )
        )

        if (
            validation_result.realization
            is not result
        ):
            raise RuntimeError(
                "Boot Image Validation must preserve exact "
                "Realization result identity"
            )

        if (
            validation_result.planning
            is not planning_result
        ):
            raise RuntimeError(
                "Boot Image Validation must preserve exact "
                "Planning result identity"
            )

        if (
            validation_result.parsing
            is not parsing
        ):
            raise RuntimeError(
                "Boot Image Validation must preserve exact "
                "AndroidParsingResult identity"
            )

        emit_progress(
            phase_index=6,
            phase_name="Validation",
            state=ProgressState.COMPLETE,
        )

        return validation_result
