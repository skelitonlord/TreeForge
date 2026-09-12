from __future__ import annotations

from pathlib import Path
import re

from treeforge.android.discovery.artifact_content import (
    ProviderArtifactContentReader,
)
from treeforge.android.discovery.identity import (
    AndroidIdentityEvidence,
    AndroidIdentityInferenceResult,
    AndroidIdentityKind,
)
from treeforge.android.providers.artifact import (
    ProviderArtifactClassification,
    ProviderArtifactKind,
)
from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)


class AndroidIdentityInferer:
    """
    Infer Android identity facts from already-discovered provider artifacts.

    This is a post-Discovery analysis layer.

    It does not:

    - discover artifacts;
    - remove artifacts;
    - change artifact kinds;
    - change semantic classifications;
    - resolve knowledge dependencies;
    - select build policy;
    - perform kernel, SEPolicy, or build reconstruction.

    The inferer only produces evidence-backed identity candidates.

    The first supported source is Android factory metadata containing:

        require board=<value>

    The board value is preserved as discovered evidence.

    No OEM/platform/device dependency interpretation occurs here.
    """

    def __init__(
        self,
        *,
        content_reader: (
            ProviderArtifactContentReader
            | None
        ) = None,
    ) -> None:
        self.content_reader = (
            content_reader
            if content_reader is not None
            else ProviderArtifactContentReader()
        )

        if not isinstance(
            self.content_reader,
            ProviderArtifactContentReader,
        ):
            raise TypeError(
                "content_reader must be a "
                "ProviderArtifactContentReader"
            )

    def infer(
        self,
        *,
        provider_source: Path,
        inventory: ProviderArtifactInventory,
    ) -> AndroidIdentityInferenceResult:
        if not isinstance(
            provider_source,
            Path,
        ):
            raise TypeError(
                "provider_source must be a Path"
            )

        if not isinstance(
            inventory,
            ProviderArtifactInventory,
        ):
            raise TypeError(
                "inventory must be a "
                "ProviderArtifactInventory"
            )

        (
            device_id,
            device_evidence,
        ) = self._infer_device(
            provider_source=provider_source,
            inventory=inventory,
        )

        (
            board_platform,
            platform_evidence,
        ) = self._infer_board_platform(
            provider_source=provider_source,
            inventory=inventory,
        )

        return AndroidIdentityInferenceResult(
            device_id=device_id,
            board_platform=board_platform,
            evidence=(
                device_evidence
                + platform_evidence
            ),
        )

    def _infer_device(
        self,
        *,
        provider_source: Path,
        inventory: ProviderArtifactInventory,
    ) -> tuple[
        str | None,
        tuple[
            AndroidIdentityEvidence,
            ...,
        ],
    ]:
        artifacts = (
            inventory
            .artifacts_of_classification(
                ProviderArtifactClassification
                .ANDROID_INFO
            )
        )

        if not artifacts:
            return (
                None,
                (),
            )

        candidates: dict[
            str,
            list[
                AndroidIdentityEvidence
            ],
        ] = {}

        for artifact in artifacts:
            payload = self.content_reader.read(
                provider_source=provider_source,
                artifact=artifact,
            )

            text = payload.decode(
                "utf-8",
                errors="replace",
            )

            boards = self._board_requirements(
                text
            )

            for board in boards:
                evidence = AndroidIdentityEvidence(
                    kind=(
                        AndroidIdentityKind.DEVICE
                    ),
                    value=board,
                    source=artifact.source_name,
                    detail=(
                        "Android factory metadata "
                        "declared requirement "
                        f"board={board}."
                    ),
                )

                candidates.setdefault(
                    board,
                    [],
                ).append(
                    evidence
                )

        if not candidates:
            return (
                None,
                (),
            )

        all_evidence = tuple(
            evidence
            for board in sorted(
                candidates
            )
            for evidence in candidates[
                board
            ]
        )

        if len(candidates) != 1:
            return (
                None,
                all_evidence,
            )

        device_id = next(
            iter(
                candidates
            )
        )

        return (
            device_id,
            all_evidence,
        )

    def _infer_board_platform(
        self,
        *,
        provider_source: Path,
        inventory: ProviderArtifactInventory,
    ) -> tuple[
        str | None,
        tuple[
            AndroidIdentityEvidence,
            ...,
        ],
    ]:
        """
        Infer board/platform identity from direct embedded artifact evidence.

        Only small top-level image artifacts are inspected. Semantic
        classification is not required: an artifact may remain UNKNOWN while
        still supplying identity evidence.

        The accepted evidence form is an exact JSON-style soc_model field:

            "soc_model": "GS201"

        Values are canonicalized to lowercase for TreeForge identity matching.
        Multiple distinct values remain ambiguous rather than being guessed.
        """

        candidates: dict[
            str,
            list[
                AndroidIdentityEvidence
            ],
        ] = {}

        for artifact in inventory.artifacts_of_kind(
            ProviderArtifactKind.IMAGE
        ):
            # Restrict identity inspection to direct members of the factory
            # archive. Nested partition images are not needed for this
            # Discovery-time evidence source.
            if artifact.source_name.count(
                "!/"
            ) != 1:
                continue

            size_bytes = (
                artifact.provenance.size_bytes
            )

            if (
                size_bytes is not None
                and size_bytes > 64 * 1024 * 1024
            ):
                continue

            payload = self.content_reader.read(
                provider_source=provider_source,
                artifact=artifact,
            )

            models = {
                match.group(1)
                .decode(
                    "ascii",
                    errors="strict",
                )
                .strip()
                .lower()
                for match in re.finditer(
                    rb'"soc_model"\s*:\s*"([^"]+)"',
                    payload,
                )
                if match.group(1).strip()
            }

            for model in sorted(
                models
            ):
                evidence = AndroidIdentityEvidence(
                    kind=(
                        AndroidIdentityKind
                        .BOARD_PLATFORM
                    ),
                    value=model,
                    source=artifact.source_name,
                    detail=(
                        "Discovered image contained "
                        "embedded soc_model="
                        f"{model} identity evidence."
                    ),
                )

                candidates.setdefault(
                    model,
                    [],
                ).append(
                    evidence
                )

        if not candidates:
            return (
                None,
                (),
            )

        all_evidence = tuple(
            evidence
            for model in sorted(
                candidates
            )
            for evidence in candidates[
                model
            ]
        )

        if len(candidates) != 1:
            return (
                None,
                all_evidence,
            )

        return (
            next(
                iter(
                    candidates
                )
            ),
            all_evidence,
        )

    @staticmethod
    def _board_requirements(
        text: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Extract exact board requirements from Android factory metadata.

        Unknown directives and unrelated requirements are ignored.

        Multiple identical board requirements collapse deterministically.

        Multiple distinct boards remain distinct so the caller can treat the
        evidence as ambiguous rather than guessing.
        """

        if not isinstance(
            text,
            str,
        ):
            raise TypeError(
                "text must be a string"
            )

        boards: set[
            str
        ] = set()

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith(
                "#"
            ):
                continue

            fields = line.split()

            if (
                len(fields) < 2
                or fields[0] != "require"
            ):
                continue

            for argument in fields[1:]:
                if not argument.startswith(
                    "board="
                ):
                    continue

                board = argument[
                    len(
                        "board="
                    ):
                ].strip()

                if board:
                    boards.add(
                        board
                    )

        return tuple(
            sorted(
                boards
            )
        )