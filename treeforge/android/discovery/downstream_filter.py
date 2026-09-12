from __future__ import annotations

from dataclasses import (
    dataclass,
    replace,
)

from treeforge.android.providers.artifact import (
    ProviderArtifact,
)
from treeforge.android.providers.artifact_inventory import (
    ProviderArtifactInventory,
)
from treeforge.android.providers.collection import (
    ProviderCollection,
)


_BOOT_CHAIN_FIRMWARE_NAMES = frozenset(
    {
        "abl.img",
        "bl1.img",
        "bl2.img",
        "bl31.img",
        "gsa.img",
        "ldfw.img",
        "pbl.img",
        "tzsw.img",
    }
)


@dataclass(
    frozen=True,
    slots=True,
)
class DiscoveryDownstreamFilterResult:
    collection: ProviderCollection

    input_count: int
    forwarded_count: int

    bootloader_removed_count: int
    embedded_controller_removed_count: int

    @property
    def removed_count(
        self,
    ) -> int:
        return (
            self.bootloader_removed_count
            + self.embedded_controller_removed_count
        )


def _is_bootloader_artifact(
    artifact: ProviderArtifact,
) -> bool:
    signatures = {
        observation.signature.value
        for observation
        in artifact.content_observations
    }

    if "fbpk_container" in signatures:
        return True

    return (
        artifact.name.lower()
        in _BOOT_CHAIN_FIRMWARE_NAMES
    )


def _is_embedded_controller_artifact(
    artifact: ProviderArtifact,
) -> bool:
    return (
        artifact.name
        .lower()
        .endswith(
            ".ec.bin"
        )
    )


def filter_discovery_for_downstream(
    collection: ProviderCollection,
) -> DiscoveryDownstreamFilterResult:
    """
    Remove firmware families that are intentionally outside the
    current TreeForge Android device/vendor reconstruction scope.

    The original Discovery collection is immutable and remains intact.
    A new ProviderCollection is returned for downstream stages.

    Currently excluded:

    - platform bootloader / boot-chain firmware;
    - embedded-controller firmware.
    """

    if not isinstance(
        collection,
        ProviderCollection,
    ):
        raise TypeError(
            "collection must be a ProviderCollection"
        )

    input_count = 0
    bootloader_removed_count = 0
    embedded_controller_removed_count = 0

    filtered_results = []

    for result in collection.results:
        forwarded_artifacts = []

        for artifact in (
            result.artifact_inventory
        ):
            input_count += 1

            if _is_bootloader_artifact(
                artifact
            ):
                bootloader_removed_count += 1
                continue

            if _is_embedded_controller_artifact(
                artifact
            ):
                embedded_controller_removed_count += 1
                continue

            forwarded_artifacts.append(
                artifact
            )

        filtered_results.append(
            replace(
                result,
                artifact_inventory=(
                    ProviderArtifactInventory(
                        artifacts=tuple(
                            forwarded_artifacts
                        )
                    )
                ),
            )
        )

    filtered_collection = (
        ProviderCollection(
            results=tuple(
                filtered_results
            )
        )
    )

    forwarded_count = len(
        filtered_collection.artifacts
    )

    removed_count = (
        bootloader_removed_count
        + embedded_controller_removed_count
    )

    if (
        input_count
        != forwarded_count
        + removed_count
    ):
        raise RuntimeError(
            "Discovery downstream filtering accounting "
            "did not close: "
            f"input={input_count}, "
            f"forwarded={forwarded_count}, "
            f"removed={removed_count}"
        )

    return (
        DiscoveryDownstreamFilterResult(
            collection=filtered_collection,
            input_count=input_count,
            forwarded_count=(
                forwarded_count
            ),
            bootloader_removed_count=(
                bootloader_removed_count
            ),
            embedded_controller_removed_count=(
                embedded_controller_removed_count
            ),
        )
    )
