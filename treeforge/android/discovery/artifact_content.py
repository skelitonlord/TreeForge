from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.providers.artifact import (
    ProviderArtifact,
)


class ProviderArtifactContentReadError(
    RuntimeError,
):
    """
    Raised when the contents of an already-discovered provider artifact cannot
    be recovered from its original provider source.
    """


class ProviderArtifactContentReader:
    """
    Read bytes for one already-discovered artifact.

    This class does not perform Discovery.

    ProviderArchiveScanner remains responsible for discovering artifacts and
    assigning their canonical source identities.

    This reader consumes those identities afterward so Discovery-adjacent
    analysis can inspect selected artifact contents without permanently
    materializing the provider source.

    Archive identities are expected to have the canonical TreeForge form:

        factory.zip!/member
        factory.zip!/nested.zip!/member
        factory.zip!/nested.zip!/deeper.zip!/member
    """

    _SOURCE_SEPARATOR = "!/"

    def read(
        self,
        *,
        provider_source: Path,
        artifact: ProviderArtifact,
    ) -> bytes:
        if not isinstance(
            provider_source,
            Path,
        ):
            raise TypeError(
                "provider_source must be a Path"
            )

        if not isinstance(
            artifact,
            ProviderArtifact,
        ):
            raise TypeError(
                "artifact must be a ProviderArtifact"
            )

        source = (
            provider_source
            .expanduser()
            .resolve()
        )

        if not source.exists():
            raise FileNotFoundError(
                source
            )

        if not source.is_file():
            raise ValueError(
                "provider_source must be a file"
            )

        member_chain = self._member_chain(
            artifact.source_name
        )

        if not member_chain:
            raise ProviderArtifactContentReadError(
                "artifact source identity does not "
                "contain an archive member"
            )

        try:
            with ZipFile(
                source,
                "r",
            ) as archive:
                return self._read_chain(
                    archive=archive,
                    member_chain=member_chain,
                )

        except BadZipFile as error:
            raise ProviderArtifactContentReadError(
                "provider source is not a readable "
                "ZIP archive"
            ) from error

        except KeyError as error:
            raise ProviderArtifactContentReadError(
                "discovered artifact could not be "
                "recovered from provider source: "
                f"{artifact.source_name}"
            ) from error

        except OSError as error:
            raise ProviderArtifactContentReadError(
                "unable to read discovered artifact: "
                f"{artifact.source_name}"
            ) from error

    def _read_chain(
        self,
        *,
        archive: ZipFile,
        member_chain: tuple[
            str,
            ...,
        ],
    ) -> bytes:
        member_name = member_chain[0]

        payload = archive.read(
            member_name
        )

        if len(member_chain) == 1:
            return payload

        try:
            with ZipFile(
                BytesIO(
                    payload
                ),
                "r",
            ) as nested_archive:
                return self._read_chain(
                    archive=nested_archive,
                    member_chain=(
                        member_chain[1:]
                    ),
                )

        except BadZipFile as error:
            raise ProviderArtifactContentReadError(
                "artifact source identity traverses "
                "a member that is not a valid ZIP: "
                f"{member_name}"
            ) from error

    def _member_chain(
        self,
        source_name: str,
    ) -> tuple[
        str,
        ...,
    ]:
        if not isinstance(
            source_name,
            str,
        ):
            raise TypeError(
                "source_name must be a string"
            )

        if not source_name.strip():
            raise ValueError(
                "source_name must not be empty"
            )

        parts = tuple(
            source_name.split(
                self._SOURCE_SEPARATOR
            )
        )

        if len(parts) < 2:
            return ()

        members = parts[1:]

        if any(
            not member
            for member in members
        ):
            raise ProviderArtifactContentReadError(
                "artifact source identity contains "
                "an empty archive member"
            )

        return members