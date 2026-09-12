from __future__ import annotations

from treeforge.android.extraction import (
    ExtractedArtifact,
)

from treeforge.android.parsing.bootloader.fbpt import (
    AndroidFbptParser,
)
from treeforge.android.parsing.bootloader.model import (
    AndroidParsedBootloaderChild,
)
from treeforge.android.parsing.bootloader.ufs import (
    AndroidUfsDescriptorParser,
)
from treeforge.android.parsing.bootloader.ufpk import (
    AndroidUfpkParser,
)


class AndroidBootloaderChildParser:
    """
    Content-driven parser for structured FBPK child artifacts.

    Classification is determined entirely from observed file magic. Filenames,
    device names, platform names, and Android-version policy are not used.
    """

    def __init__(
        self,
        *,
        fbpt_parser: AndroidFbptParser | None = None,
        ufs_parser: AndroidUfsDescriptorParser | None = None,
        ufpk_parser: AndroidUfpkParser | None = None,
    ) -> None:
        self.fbpt_parser = (
            fbpt_parser
            if fbpt_parser is not None
            else AndroidFbptParser()
        )

        self.ufs_parser = (
            ufs_parser
            if ufs_parser is not None
            else AndroidUfsDescriptorParser()
        )

        self.ufpk_parser = (
            ufpk_parser
            if ufpk_parser is not None
            else AndroidUfpkParser()
        )

    def supports(
        self,
        artifact: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path

        if not source.is_file():
            return False

        with source.open(
            "rb"
        ) as stream:
            magic = stream.read(
                4
            )

        return magic in {
            b"FBPT",
            b"UFSZ",
            b"UFSP",
            b"UFPK",
        }

    def parse(
        self,
        artifact: ExtractedArtifact,
    ) -> AndroidParsedBootloaderChild:
        if not isinstance(
            artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        source = artifact.path

        with source.open(
            "rb"
        ) as stream:
            magic = stream.read(
                4
            )

        if magic == b"FBPT":
            return (
                self.fbpt_parser
                .parse(
                    artifact
                )
            )

        if magic in {
            b"UFSZ",
            b"UFSP",
        }:
            return (
                self.ufs_parser
                .parse(
                    artifact
                )
            )

        if magic == b"UFPK":
            return (
                self.ufpk_parser
                .parse(
                    artifact
                )
            )

        raise ValueError(
            "unsupported structured bootloader "
            f"child magic {magic!r}: {source}"
        )
