from __future__ import annotations

from treeforge.android.version.model import (
    AndroidSemanticVersionSelection,
)

from dataclasses import dataclass, field
from pathlib import Path
import logging
from typing import Protocol

from treeforge.android.application.parse_factory_image import (
    ParseFactoryImageRequest,
    ParseFactoryImageResult,
    ParseFactoryImageService,
)
from treeforge.android.application.parsing_snapshot import (
    AndroidParsingSnapshotStore,
)
from treeforge.android.parsing.snapshot import (
    AndroidParsingSnapshot,
)
from treeforge.core.config import (
    load_config,
)
from treeforge.core.context.context import (
    Context,
)
from treeforge.core.knowledge_application import (
    KnowledgeApplicationPolicy,
)
from treeforge.android.universe.model import (
    AndroidDeviceUniverse,
)
from treeforge.android.universe.preflight import (
    AndroidUniversePreflightReport,
)
from treeforge.android.universe.stage import (
    AndroidDeviceUniverseStage,
)
from treeforge.workspace.workspace import (
    Workspace,
)
from treeforge.core.progress import ProgressCallback


logger = logging.getLogger(__name__)


class ParseFactoryImageServiceLike(
    Protocol,
):
    def parse(
        self,
        request: ParseFactoryImageRequest,
    ) -> ParseFactoryImageResult:
        ...


class AndroidDeviceUniverseStageLike(
    Protocol,
):
    def preflight(
        self,
        context,
    ):
        ...

    def execute(
        self,
        context,
    ) -> None:
        ...


@dataclass(
    frozen=True,
    slots=True,
)
class BuildAndroidDeviceUniverseRequest:
    """
    Request the canonical TreeForge pipeline through Device Universe.
    """

    factory_image: Path | None
    workspace: Workspace
    parsing_workspace: Workspace | None = None

    device_id: str | None = None
    board_platform: str | None = None
    android_version: str | None = None
    generic_only: bool = False

    knowledge_application_policy: (
        KnowledgeApplicationPolicy
    ) = field(
        default_factory=KnowledgeApplicationPolicy
    )

    parsing_result: ParseFactoryImageResult | None = None

    parsing_snapshot: AndroidParsingSnapshot | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.knowledge_application_policy,
            KnowledgeApplicationPolicy,
        ):
            raise TypeError(
                "knowledge_application_policy must be a "
                "KnowledgeApplicationPolicy"
            )

        if (
            self.factory_image is not None
            and not isinstance(
                self.factory_image,
                Path,
            )
        ):
            raise TypeError(
                "factory_image must be a Path or None"
            )

        if not isinstance(
            self.workspace,
            Workspace,
        ):
            raise TypeError(
                "workspace must be a Workspace"
            )

        if (
            self.parsing_workspace is not None
            and not isinstance(
                self.parsing_workspace,
                Workspace,
            )
        ):
            raise TypeError(
                "parsing_workspace must be a "
                "Workspace or None"
            )

        if (
            self.device_id is not None
            and not isinstance(
                self.device_id,
                str,
            )
        ):
            raise TypeError(
                "device_id must be a str or None"
            )

        if (
            self.board_platform is not None
            and not isinstance(
                self.board_platform,
                str,
            )
        ):
            raise TypeError(
                "board_platform must be a str or None"
            )

        if (
            self.android_version is not None
            and not isinstance(
                self.android_version,
                str,
            )
        ):
            raise TypeError(
                "android_version must be a str or None"
            )

        if not isinstance(
            self.generic_only,
            bool,
        ):
            raise TypeError(
                "generic_only must be a bool"
            )

        if (
            self.generic_only
            and (
                self.device_id is not None
                or self.board_platform is not None
                or self.android_version is not None
            )
        ):
            raise ValueError(
                "generic_only cannot be combined with "
                "device_id, board_platform, or android_version"
            )



        if (
            self.parsing_result is not None
            and not isinstance(
                self.parsing_result,
                ParseFactoryImageResult,
            )
        ):
            raise TypeError(
                "parsing_result must be a "
                "ParseFactoryImageResult or None"
            )

        if (
            self.parsing_snapshot is not None
            and not isinstance(
                self.parsing_snapshot,
                AndroidParsingSnapshot,
            )
        ):
            raise TypeError(
                "parsing_snapshot must be an "
                "AndroidParsingSnapshot or None"
            )

        if (
            self.parsing_result is not None
            and self.parsing_snapshot is not None
        ):
            raise ValueError(
                "parsing_result and parsing_snapshot "
                "cannot both be supplied"
            )

        if self.parsing_result is not None:
            parsing_request = (
                self.parsing_result.request
            )

            if (
                self.factory_image is not None
                and parsing_request.factory_image
                != self.factory_image
            ):
                raise ValueError(
                    "supplied Parsing result must originate "
                    "from the requested factory image"
                )

            if (
                parsing_request.device_id
                != self.device_id
            ):
                raise ValueError(
                    "supplied Parsing result device_id "
                    "must match the Universe request"
                )

            if (
                parsing_request.android_version
                != self.android_version
            ):
                raise ValueError(
                    "supplied Parsing result android_version "
                    "must match the Universe request"
                )

            if (
                parsing_request.generic_only
                != self.generic_only
            ):
                raise ValueError(
                    "supplied Parsing result generic_only "
                    "must match the Universe request"
                )
@dataclass(
    frozen=True,
    slots=True,
)
class BuildAndroidDeviceUniverseResult:
    """
    Complete production result for a factory image through Device Universe.
    """

    request: BuildAndroidDeviceUniverseRequest
    parsing_snapshot: AndroidParsingSnapshot
    android_semantic_version: AndroidSemanticVersionSelection
    universe: AndroidDeviceUniverse

    parsing_result: ParseFactoryImageResult | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.request,
            BuildAndroidDeviceUniverseRequest,
        ):
            raise TypeError(
                "request must be a "
                "BuildAndroidDeviceUniverseRequest"
            )

        if not isinstance(
            self.parsing_snapshot,
            AndroidParsingSnapshot,
        ):
            raise TypeError(
                "parsing_snapshot must be an "
                "AndroidParsingSnapshot"
            )

        if not isinstance(
            self.android_semantic_version,
            AndroidSemanticVersionSelection,
        ):
            raise TypeError(
                "android_semantic_version must be an "
                "AndroidSemanticVersionSelection"
            )

        if (
            self.parsing_result is not None
            and not isinstance(
                self.parsing_result,
                ParseFactoryImageResult,
            )
        ):
            raise TypeError(
                "parsing_result must be a "
                "ParseFactoryImageResult or None"
            )

        if not isinstance(
            self.universe,
            AndroidDeviceUniverse,
        ):
            raise TypeError(
                "universe must be an AndroidDeviceUniverse"
            )

        if (
            self.universe.parsing
            is not self.parsing_snapshot.parsing
        ):
            raise ValueError(
                "Universe must preserve exact "
                "snapshot AndroidParsingResult identity"
            )

        if (
            self.universe.knowledge_resolution
            is not self.parsing_snapshot.knowledge_resolution
        ):
            raise ValueError(
                "Universe must preserve exact "
                "snapshot knowledge-resolution identity"
            )

        if self.parsing_result is not None:
            context = (
                self.parsing_result.discovery.context
            )

            if (
                context.android_device_universe
                is not self.universe
            ):
                raise ValueError(
                    "live Parsing context must preserve exact "
                    "AndroidDeviceUniverse identity"
                )

            if (
                self.parsing_result.snapshot
                is not self.parsing_snapshot
            ):
                raise ValueError(
                    "live Parsing result must preserve exact "
                    "AndroidParsingSnapshot identity"
                )

        if (
            self.request.parsing_result is not None
            and self.parsing_result
            is not self.request.parsing_result
        ):
            raise ValueError(
                "build result must preserve the exact supplied "
                "ParseFactoryImageResult identity"
            )

        if (
            self.request.parsing_snapshot is not None
            and self.parsing_snapshot
            is not self.request.parsing_snapshot
        ):
            raise ValueError(
                "build result must preserve the exact supplied "
                "AndroidParsingSnapshot identity"
            )
@dataclass(
    frozen=True,
    slots=True,
)
class BuildAndroidDeviceUniversePreflightResult:
    """
    Diagnostic Universe execution result.

    On a successful preflight, ``result`` is the exact normal production
    BuildAndroidDeviceUniverseResult backed by the Universe assembled during
    preflight. No second Universe execution is required.
    """

    report: AndroidUniversePreflightReport
    result: BuildAndroidDeviceUniverseResult | None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.report,
            AndroidUniversePreflightReport,
        ):
            raise TypeError(
                "report must be an "
                "AndroidUniversePreflightReport"
            )

        if (
            self.result is not None
            and not isinstance(
                self.result,
                BuildAndroidDeviceUniverseResult,
            )
        ):
            raise TypeError(
                "result must be a "
                "BuildAndroidDeviceUniverseResult or None"
            )

        if self.report.is_successful:
            if self.result is None:
                raise ValueError(
                    "successful Universe preflight must "
                    "produce a build result"
                )

            if (
                self.report.universe
                is not self.result.universe
            ):
                raise ValueError(
                    "preflight result must preserve exact "
                    "assembled Universe identity"
                )

        elif self.result is not None:
            raise ValueError(
                "failed Universe preflight must not "
                "produce a build result"
            )


class BuildAndroidDeviceUniverseService:
    """
    Build Android Device Universe from the canonical Parsing handoff.

    A factory image is required only when TreeForge must execute Parsing.
    A supplied Parsing result or Parsing snapshot is a complete canonical
    upstream handoff.
    """

    def __init__(
        self,
        *,
        parsing_service: (
            ParseFactoryImageServiceLike
            | None
        ) = None,
        universe_stage: (
            AndroidDeviceUniverseStageLike
            | None
        ) = None,
        snapshot_store: (
            AndroidParsingSnapshotStore
            | None
        ) = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.progress_callback = progress_callback

        self.parsing_service = (
            parsing_service
            if parsing_service is not None
            else ParseFactoryImageService(
                progress_callback=progress_callback,
            )
        )

        self.universe_stage = (
            universe_stage
            if universe_stage is not None
            else AndroidDeviceUniverseStage(
                progress_callback=progress_callback,
            )
        )

        self.snapshot_store = (
            snapshot_store
            if snapshot_store is not None
            else AndroidParsingSnapshotStore()
        )

    @staticmethod
    def _context_from_snapshot(
        request: BuildAndroidDeviceUniverseRequest,
        snapshot: AndroidParsingSnapshot,
    ) -> Context:
        request.workspace.create()

        return Context(
            requested_android_version=(
                request.android_version
            ),
            workspace=request.workspace,
            config=load_config(),
            input_path=request.factory_image,
            knowledge_resolution=(
                snapshot.knowledge_resolution
            ),
            knowledge_application_policy=(
                request.knowledge_application_policy
            ),
            partition_layout=(
                snapshot.partition_layout
            ),
            filesystem_inventory=(
                snapshot.parsing.filesystem_inventory
            ),
            android_parsing=(
                snapshot.parsing
            ),
        )

    def _resolve_parsing_handoff(
        self,
        request: BuildAndroidDeviceUniverseRequest,
    ) -> tuple[
        AndroidParsingSnapshot,
        ParseFactoryImageResult | None,
        Context,
    ]:
        if request.parsing_result is not None:
            parsing_result = (
                request.parsing_result
            )

            context = (
                parsing_result.discovery.context
            )

            context.knowledge_application_policy = (
                request.knowledge_application_policy
            )

            return (
                parsing_result.snapshot,
                parsing_result,
                context,
            )

        if request.parsing_snapshot is not None:
            snapshot = (
                request.parsing_snapshot
            )

            return (
                snapshot,
                None,
                self._context_from_snapshot(
                    request,
                    snapshot,
                ),
            )

        if request.factory_image is None:
            raise ValueError(
                "factory_image is required when no canonical "
                "Parsing snapshot or Parsing result is supplied"
            )

        parsing_result = (
            self.parsing_service.parse(
                ParseFactoryImageRequest(
                    factory_image=(
                        request.factory_image
                    ),
                    workspace=(
                        request.parsing_workspace
                        if request.parsing_workspace
                        is not None
                        else request.workspace
                    ),
                    device_id=request.device_id,
                    board_platform=(
                        request.board_platform
                    ),
                    android_version=(
                        request.android_version
                    ),
                    generic_only=(
                        request.generic_only
                    ),
                )
            )
        )

        context = (
            parsing_result.discovery.context
        )

        context.knowledge_application_policy = (
            request.knowledge_application_policy
        )

        return (
            parsing_result.snapshot,
            parsing_result,
            context,
        )

    def preflight(
        self,
        request: BuildAndroidDeviceUniverseRequest,
    ) -> BuildAndroidDeviceUniversePreflightResult:
        """
        Parse once, exercise all reachable Universe contracts, and retain the
        exact canonical Universe when all preflight operations succeed.
        """

        if not isinstance(
            request,
            BuildAndroidDeviceUniverseRequest,
        ):
            raise TypeError(
                "request must be a "
                "BuildAndroidDeviceUniverseRequest"
            )

        logger.info(
            "Factory-to-Parsing pipeline: starting "
            "for Universe preflight"
        )

        (
            parsing_snapshot,
            parsing_result,
            context,
        ) = self._resolve_parsing_handoff(
            request
        )

        if (
            context.android_parsing
            is not parsing_snapshot.parsing
        ):
            raise ValueError(
                "Universe preflight must preserve exact "
                "AndroidParsingResult identity"
            )

        if (
            context.knowledge_resolution
            is not parsing_snapshot.knowledge_resolution
        ):
            raise ValueError(
                "Universe preflight must preserve exact "
                "knowledge-resolution identity"
            )

        logger.info(
            "Android Device Universe preflight: starting"
        )

        report = self.universe_stage.preflight(
            context
        )

        if not isinstance(
            report,
            AndroidUniversePreflightReport,
        ):
            raise TypeError(
                "Universe stage preflight must return "
                "AndroidUniversePreflightReport"
            )

        if not report.is_successful:
            return (
                BuildAndroidDeviceUniversePreflightResult(
                    report=report,
                    result=None,
                )
            )

        universe = report.universe

        if not isinstance(
            universe,
            AndroidDeviceUniverse,
        ):
            raise RuntimeError(
                "successful Universe preflight did not "
                "retain AndroidDeviceUniverse"
            )

        if (
            context.android_device_universe
            is not universe
        ):
            raise ValueError(
                "successful Universe preflight must attach "
                "the exact assembled Universe to Context"
            )

        if context.android_semantic_version is None:
            raise RuntimeError(
                "successful Universe preflight did not preserve "
                "Android semantic-version selection"
            )

        result = BuildAndroidDeviceUniverseResult(
            request=request,
            parsing_snapshot=parsing_snapshot,
            android_semantic_version=(
                context.android_semantic_version
            ),
            universe=universe,
            parsing_result=parsing_result,
        )

        logger.info(
            "Android Device Universe preflight: complete"
        )

        return (
            BuildAndroidDeviceUniversePreflightResult(
                report=report,
                result=result,
            )
        )

    def build(
        self,
        request: BuildAndroidDeviceUniverseRequest,
    ) -> BuildAndroidDeviceUniverseResult:
        if not isinstance(
            request,
            BuildAndroidDeviceUniverseRequest,
        ):
            raise TypeError(
                "request must be a "
                "BuildAndroidDeviceUniverseRequest"
            )

        logger.info(
            "Factory-to-Parsing pipeline: starting"
        )

        (
            parsing_snapshot,
            parsing_result,
            context,
        ) = self._resolve_parsing_handoff(
            request
        )

        logger.info(
            "Factory-to-Parsing handoff: complete"
        )

        if (
            context.android_parsing
            is not parsing_snapshot.parsing
        ):
            raise ValueError(
                "Universe build must preserve exact "
                "AndroidParsingResult identity"
            )

        if (
            context.knowledge_resolution
            is not parsing_snapshot.knowledge_resolution
        ):
            raise ValueError(
                "Universe build must preserve exact "
                "knowledge-resolution identity"
            )

        logger.info(
            "Android Device Universe: starting"
        )

        self.universe_stage.execute(
            context
        )

        logger.info(
            "Android Device Universe: complete"
        )

        universe = (
            context.android_device_universe
        )

        if not isinstance(
            universe,
            AndroidDeviceUniverse,
        ):
            raise RuntimeError(
                "Device Universe stage did not produce "
                "AndroidDeviceUniverse"
            )

        if context.android_semantic_version is None:
            raise RuntimeError(
                "Universe build did not preserve Android "
                "semantic-version selection"
            )

        return BuildAndroidDeviceUniverseResult(
            request=request,
            parsing_snapshot=parsing_snapshot,
            android_semantic_version=(
                context.android_semantic_version
            ),
            universe=universe,
            parsing_result=parsing_result,
        )
