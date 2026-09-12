from __future__ import annotations

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from pathlib import Path

from treeforge.android.parsing.bootloader.model import (
    AndroidParsedUfsDescriptor,
    AndroidParsedUfsDescriptorKind,
)


class AndroidUfsDescriptorParser:
    """
    Parse the literal fixed-size UFSZ / UFSP structures exposed from FBPK.

    Field semantics beyond the observed magic and version scalar remain
    deferred until independently established.
    """

    SIZE = 197

    _KINDS = {
        b"UFSZ": (
            AndroidParsedUfsDescriptorKind
            .UFSZ
        ),
        b"UFSP": (
            AndroidParsedUfsDescriptorKind
            .UFSP
        ),
    }

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedUfsDescriptor:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path

        data = source.read_bytes()

        if len(data) != self.SIZE:
            raise ValueError(
                "UFS descriptor must be exactly "
                f"{self.SIZE} bytes: "
                f"{source} has {len(data)}"
            )

        magic = data[:4]

        try:
            kind = self._KINDS[
                magic
            ]

        except KeyError as error:
            raise ValueError(
                f"unsupported UFS descriptor magic "
                f"{magic!r}: {source}"
            ) from error

        version = int.from_bytes(
            data[
                4:8
            ],
            "little",
        )

        return AndroidParsedUfsDescriptor(
            kind=kind,
            version=version,
            raw_payload=data,
        )
