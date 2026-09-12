from __future__ import annotations

from treeforge.android.discovery.identity import (
    AndroidIdentityInferenceResult,
)
from treeforge.android.discovery.identity_inferer import (
    AndroidIdentityInferer,
)
from treeforge.android.discovery.result import (
    AndroidDiscoveryResult,
)
from treeforge.android.providers.source_type import (
    ProviderSourceType,
)
from treeforge.core.context.context import (
    Context,
)


class AndroidDiscoveryResultBuilder:
    """
    Build the highest canonical immutable Android Discovery aggregate.

    The builder consumes Discovery state that already exists in Context.

    It does not:

    - discover provider artifacts;
    - detect partition layouts;
    - resolve partition inventories;
    - collect filesystem metadata;
    - resolve knowledge modules;
    - select Android-version policy;
    - perform build, kernel, or SEPolicy work.

    ProviderCollection remains the canonical owner of ProviderResult and
    ProviderArtifactInventory objects.

    Identity inference is performed only from provider evidence that Discovery
    has already collected.

    Unknown or conflicting identity evidence is preserved without guessing.
    """

    def __init__(
        self,
        *,
        identity_inferer: (
            AndroidIdentityInferer
            | None
        ) = None,
    ) -> None:
        self.identity_inferer = (
            identity_inferer
            if identity_inferer is not None
            else AndroidIdentityInferer()
        )

        if not isinstance(
            self.identity_inferer,
            AndroidIdentityInferer,
        ):
            raise TypeError(
                "identity_inferer must be an "
                "AndroidIdentityInferer"
            )

    def build(
        self,
        context: Context,
    ) -> AndroidDiscoveryResult:
        if not isinstance(
            context,
            Context,
        ):
            raise TypeError(
                "context must be a Context"
            )

        identity_inference = (
            self._infer_identity(
                context
            )
        )

        return AndroidDiscoveryResult(
            provider_collection=(
                context.provider_collection
            ),
            partition_layout=(
                context.partition_layout
            ),
            identity_inference=(
                identity_inference
            ),
        )

    def _infer_identity(
        self,
        context: Context,
    ) -> AndroidIdentityInferenceResult:
        """
        Infer identity from compatible provider Discovery results.

        Factory-image results currently provide the archive provenance required
        by AndroidIdentityInferer.

        Multiple provider results may contribute evidence.

        A dimension is selected only when every inferred non-None candidate for
        that dimension agrees.

        Conflicting evidence is preserved while the resulting identity remains
        None.
        """

        collection = (
            context.provider_collection
        )

        if collection is None:
            return AndroidIdentityInferenceResult()

        inferences: list[
            AndroidIdentityInferenceResult
        ] = []

        for result in collection:
            if (
                result.source_type
                is not ProviderSourceType.FACTORY_IMAGE
            ):
                continue

            source_identity = (
                result.source_identity
            )

            if source_identity is None:
                continue

            inference = (
                self.identity_inferer.infer(
                    provider_source=(
                        source_identity.path
                    ),
                    inventory=(
                        result.artifact_inventory
                    ),
                )
            )

            inferences.append(
                inference
            )

        if not inferences:
            return AndroidIdentityInferenceResult()

        evidence = tuple(
            item
            for inference in inferences
            for item in inference.evidence
        )

        device_id = self._unique_candidate(
            tuple(
                inference.device_id
                for inference in inferences
                if inference.device_id
                is not None
            )
        )

        board_platform = (
            self._unique_candidate(
                tuple(
                    inference.board_platform
                    for inference in inferences
                    if (
                        inference.board_platform
                        is not None
                    )
                )
            )
        )

        android_version = (
            self._unique_candidate(
                tuple(
                    inference.android_version
                    for inference in inferences
                    if (
                        inference.android_version
                        is not None
                    )
                )
            )
        )

        return AndroidIdentityInferenceResult(
            device_id=device_id,
            board_platform=board_platform,
            android_version=android_version,
            evidence=evidence,
        )

    @staticmethod
    def _unique_candidate(
        candidates: tuple[
            str,
            ...,
        ],
    ) -> str | None:
        """
        Return one unanimously supported identity candidate.

        No candidates means unknown.

        Multiple distinct candidates mean ambiguous and therefore unknown.
        """

        if not candidates:
            return None

        unique = tuple(
            sorted(
                set(
                    candidates
                )
            )
        )

        if len(unique) != 1:
            return None

        return unique[0]