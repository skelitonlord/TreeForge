from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.avb import (
    AndroidParsedAvbChainPartitionDescriptor,
    AndroidParsedAvbHashDescriptor,
    AndroidParsedAvbHashtreeDescriptor,
)
from treeforge.android.parsing.result import (
    ParsedBootSignature,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseBootSignatureAvbRequirement:
    """
    Universe AVB interpretation of one canonical boot_signature component.

    ParsedBootSignature remains distinct from ParsedAvbVbmeta. This model
    therefore does not inject boot signatures into the partition/region-backed
    VBMeta requirement population or the existing AVB topology.

    Universe classifies only source-local AVB descriptor semantics already
    decoded by Parsing. Cross-source trust resolution can consume this model
    later without reopening bytes or inventing a partition identity.
    """

    source: ParsedBootSignature

    authentication_descriptors: tuple[
        AndroidParsedAvbHashDescriptor
        | AndroidParsedAvbHashtreeDescriptor,
        ...,
    ]

    chain_descriptors: tuple[
        AndroidParsedAvbChainPartitionDescriptor,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source,
            ParsedBootSignature,
        ):
            raise TypeError(
                "source must be a ParsedBootSignature"
            )

        if not isinstance(
            self.authentication_descriptors,
            tuple,
        ):
            raise TypeError(
                "authentication_descriptors must be a tuple"
            )

        if not all(
            isinstance(
                descriptor,
                (
                    AndroidParsedAvbHashDescriptor,
                    AndroidParsedAvbHashtreeDescriptor,
                ),
            )
            for descriptor
            in self.authentication_descriptors
        ):
            raise TypeError(
                "authentication_descriptors must contain only "
                "AVB hash/hashtree descriptors"
            )

        if not isinstance(
            self.chain_descriptors,
            tuple,
        ):
            raise TypeError(
                "chain_descriptors must be a tuple"
            )

        if not all(
            isinstance(
                descriptor,
                AndroidParsedAvbChainPartitionDescriptor,
            )
            for descriptor
            in self.chain_descriptors
        ):
            raise TypeError(
                "chain_descriptors must contain only "
                "AVB chain-partition descriptors"
            )

        metadata_descriptors = (
            self.source.metadata.descriptors
        )

        for descriptor in (
            self.authentication_descriptors
            + self.chain_descriptors
        ):
            if not any(
                candidate is descriptor
                for candidate
                in metadata_descriptors
            ):
                raise ValueError(
                    "boot-signature AVB requirement must preserve "
                    "exact Parsing descriptor identity"
                )


class AndroidUniverseBootSignatureAvbInterpreter:
    """
    Interpret source-local AVB semantics for canonical boot signatures.

    No AVB bytes are reopened. No partition-backed identity is invented.
    """

    def interpret(
        self,
        sources: tuple[
            ParsedBootSignature,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseBootSignatureAvbRequirement,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                ParsedBootSignature,
            )
            for source
            in sources
        ):
            raise TypeError(
                "sources must contain only ParsedBootSignature instances"
            )

        return tuple(
            self._interpret_source(
                source
            )
            for source
            in sources
        )

    @staticmethod
    def _interpret_source(
        source: ParsedBootSignature,
    ) -> AndroidUniverseBootSignatureAvbRequirement:
        descriptors = (
            source.metadata.descriptors
        )

        authentication_descriptors = tuple(
            descriptor
            for descriptor
            in descriptors
            if isinstance(
                descriptor,
                (
                    AndroidParsedAvbHashDescriptor,
                    AndroidParsedAvbHashtreeDescriptor,
                ),
            )
        )

        chain_descriptors = tuple(
            descriptor
            for descriptor
            in descriptors
            if isinstance(
                descriptor,
                AndroidParsedAvbChainPartitionDescriptor,
            )
        )

        return (
            AndroidUniverseBootSignatureAvbRequirement(
                source=source,
                authentication_descriptors=(
                    authentication_descriptors
                ),
                chain_descriptors=(
                    chain_descriptors
                ),
            )
        )
