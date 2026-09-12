from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
from tempfile import SpooledTemporaryFile
from zipfile import (
    BadZipFile,
    ZipFile,
)

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
)
from treeforge.android.providers.artifact import (
    ProviderArtifact,
)


class SourceArtifactMaterializationError(
    RuntimeError,
):
    """
    Raised when one canonical Discovery artifact cannot be made
    physically accessible by Extraction.
    """


class SourceArtifactMaterializer:
    """
    Materialize one exact Discovery ProviderArtifact into Extraction.

    Discovery remains authoritative for:

    - provider identity;
    - source_name;
    - archive/member provenance;
    - semantic enrichment;
    - content observations.

    Extraction adds only physical materialization and derivation
    evidence.

    ProviderArtifact is never mutated.

    Provider artifacts that identify the canonical physical provider
    source are adopted with SOURCE_ADOPTION.

    Archive members are physically extracted with
    ARCHIVE_MEMBER_EXTRACTION.

    Nested ZIP traversal follows the canonical ProviderArtifact
    source identity:

        factory.zip!/nested.zip!/member
        factory.zip!/nested.zip!/deeper.zip!/member

    No semantic classification or filename guessing is used to
    reconstruct the archive path.
    """

    ARCHIVE_SEPARATOR = "!/"

    COPY_BUFFER_SIZE = (
        1024
        * 1024
    )

    SPOOL_MAX_SIZE = (
        64
        * 1024
        * 1024
    )

    def materialize(
        self,
        artifact: ProviderArtifact,
        *,
        source_path: Path,
        destination: Path,
    ) -> ExtractedArtifact:
        """
        Make one exact ProviderArtifact physically accessible.

        The exact ProviderArtifact object is preserved as the
        ExtractedArtifact source.

        source_path is the physical root provider source, such as
        the original factory-image ZIP.

        destination is the persistent Extraction-owned output path.
        """

        if not isinstance(
            artifact,
            ProviderArtifact,
        ):
            raise TypeError(
                "artifact must be a ProviderArtifact"
            )

        source_path = (
            self._validate_source_path(
                source_path
            )
        )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        components = (
            self._archive_components(
                artifact,
                source_path=source_path,
            )
        )

        if not components:
            #
            # A ProviderArtifact may identify the physical provider source
            # itself. In that case Extraction adopts the canonical source path
            # preserved by ProviderSourceIdentity.
            #
            # This is SOURCE_ADOPTION based on source identity, not a
            # Discovery-owned materialization path.
            #
            if (
                Path(
                    artifact.source_name
                ).name
                == source_path.name
            ):
                return self._adopt(
                    artifact,
                    source_path,
                )

            raise SourceArtifactMaterializationError(
                "provider artifact does not identify "
                "the physical provider source or an "
                "archive member: "
                f"{artifact.source_name}"
            )

        return self._extract_archive_member(
            artifact,
            source_path=source_path,
            components=components,
            destination=destination,
        )

    def _adopt(
        self,
        artifact: ProviderArtifact,
        path: Path,
    ) -> ExtractedArtifact:
        """
        Adopt the canonical physical provider source artifact.
        """

        normalized = (
            self._validate_regular_file(
                path,
                description=(
                    "provider source artifact"
                ),
            )
        )

        digest = (
            self._sha256_file(
                normalized
            )
        )

        return ExtractedArtifact(
            source=artifact,
            path=normalized,
            kind=(
                ExtractionArtifactKind.FILE
            ),
            operation=(
                ExtractionOperation
                .SOURCE_ADOPTION
            ),
            semantic_name=None,
            facts=(
                ExtractionFact(
                    name="provider_id",
                    value=artifact.provider_id,
                ),
                ExtractionFact(
                    name="provider_source_name",
                    value=artifact.source_name,
                ),
                ExtractionFact(
                    name="adopted_existing_path",
                    value=True,
                ),
            ),
            content_sha256=digest,
            size_bytes=(
                normalized.stat().st_size
            ),
        )

    def _extract_archive_member(
        self,
        artifact: ProviderArtifact,
        *,
        source_path: Path,
        components: tuple[
            str,
            ...,
        ],
        destination: Path,
    ) -> ExtractedArtifact:
        """
        Materialize an arbitrarily nested ZIP member.

        Intermediate nested archives use SpooledTemporaryFile so
        they remain temporary implementation details rather than
        becoming false canonical Extraction artifacts.

        Only the requested ProviderArtifact becomes a canonical
        ExtractedArtifact.
        """

        destination = (
            destination.expanduser()
        )

        if destination.exists():
            raise SourceArtifactMaterializationError(
                "source materialization destination "
                "already exists: "
                f"{destination}"
            )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with ZipFile(
                source_path,
                "r",
            ) as root_archive:
                (
                    digest,
                    size_bytes,
                ) = self._extract_from_archive(
                    archive=root_archive,
                    components=components,
                    destination=destination,
                )

        except (
            BadZipFile,
            KeyError,
            OSError,
            RuntimeError,
        ) as error:
            self._remove_partial_destination(
                destination
            )

            raise SourceArtifactMaterializationError(
                "unable to materialize provider archive "
                f"artifact: {artifact.source_name}"
            ) from error

        if not destination.is_file():
            raise SourceArtifactMaterializationError(
                "archive materialization did not produce "
                "a regular file: "
                f"{destination}"
            )

        provenance = (
            artifact.provenance
        )

        facts = [
            ExtractionFact(
                name="provider_id",
                value=artifact.provider_id,
            ),
            ExtractionFact(
                name="provider_source_name",
                value=artifact.source_name,
            ),
            ExtractionFact(
                name="archive_depth",
                value=len(
                    components
                ),
            ),
            ExtractionFact(
                name="archive_member_path",
                value=components[-1],
            ),
        ]

        if (
            provenance.parent_source_name
            is not None
        ):
            facts.append(
                ExtractionFact(
                    name="discovery_parent_source_name",
                    value=(
                        provenance
                        .parent_source_name
                    ),
                )
            )

        if provenance.member_path is not None:
            facts.append(
                ExtractionFact(
                    name="discovery_member_path",
                    value=(
                        provenance.member_path
                    ),
                )
            )

        if (
            provenance.container_depth
            is not None
        ):
            facts.append(
                ExtractionFact(
                    name="discovery_container_depth",
                    value=(
                        provenance.container_depth
                    ),
                )
            )

        return ExtractedArtifact(
            source=artifact,
            path=destination,
            kind=(
                ExtractionArtifactKind.FILE
            ),
            operation=(
                ExtractionOperation
                .ARCHIVE_MEMBER_EXTRACTION
            ),
            semantic_name=None,
            facts=tuple(
                facts
            ),
            content_sha256=digest,
            size_bytes=size_bytes,
        )

    def _extract_from_archive(
        self,
        *,
        archive: ZipFile,
        components: tuple[
            str,
            ...,
        ],
        destination: Path,
    ) -> tuple[
        str,
        int,
    ]:
        """
        Traverse nested ZIP components and stream the final member
        to destination.
        """

        if not components:
            raise SourceArtifactMaterializationError(
                "archive components cannot be empty"
            )

        member_name = (
            components[0]
        )

        try:
            member = archive.getinfo(
                member_name
            )

        except KeyError as error:
            raise SourceArtifactMaterializationError(
                "archive does not contain expected "
                f"member: {member_name}"
            ) from error

        if member.is_dir():
            raise SourceArtifactMaterializationError(
                "provider artifact resolves to an "
                "archive directory rather than a file: "
                f"{member_name}"
            )

        #
        # Final component: stream it directly into persistent
        # Extraction storage while calculating canonical evidence.
        #
        if len(components) == 1:
            digest = sha256()
            size_bytes = 0

            with archive.open(
                member,
                "r",
            ) as source:
                with destination.open(
                    "xb",
                ) as output:
                    while True:
                        block = source.read(
                            self.COPY_BUFFER_SIZE
                        )

                        if not block:
                            break

                        output.write(
                            block
                        )

                        digest.update(
                            block
                        )

                        size_bytes += len(
                            block
                        )

            return (
                digest.hexdigest(),
                size_bytes,
            )

        #
        # Intermediate component: it must itself be a readable ZIP.
        #
        nested = (
            SpooledTemporaryFile(
                max_size=(
                    self.SPOOL_MAX_SIZE
                ),
                mode="w+b",
            )
        )

        try:
            with archive.open(
                member,
                "r",
            ) as source:
                shutil.copyfileobj(
                    source,
                    nested,
                    length=(
                        self.COPY_BUFFER_SIZE
                    ),
                )

            nested.seek(
                0
            )

            try:
                with ZipFile(
                    nested,
                    "r",
                ) as nested_archive:
                    return (
                        self._extract_from_archive(
                            archive=nested_archive,
                            components=(
                                components[1:]
                            ),
                            destination=destination,
                        )
                    )

            except BadZipFile as error:
                raise SourceArtifactMaterializationError(
                    "canonical source identity crosses a "
                    "component that is not a valid ZIP: "
                    f"{member_name}"
                ) from error

        finally:
            nested.close()

    def _archive_components(
        self,
        artifact: ProviderArtifact,
        *,
        source_path: Path,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Decode the exact canonical provider source identity.

        The first source-name component identifies the physical
        root provider source and is not an archive member itself.

        Example:

            tangorpro-factory.zip
                !/ image-tangorpro.zip
                !/ boot.img

        becomes:

            (
                "image-tangorpro.zip",
                "boot.img",
            )
        """

        source_name = (
            artifact.source_name
        )

        pieces = tuple(
            piece
            for piece
            in source_name.split(
                self.ARCHIVE_SEPARATOR
            )
            if piece
        )

        if len(pieces) < 2:
            return ()

        root_identity = (
            pieces[0]
        )

        if (
            Path(root_identity).name
            != source_path.name
        ):
            raise SourceArtifactMaterializationError(
                "provider artifact root source identity "
                "does not match the supplied physical source: "
                f"{root_identity!r} != "
                f"{source_path.name!r}"
            )

        return tuple(
            pieces[1:]
        )

    @staticmethod
    def _validate_source_path(
        source_path: Path,
    ) -> Path:
        if not isinstance(
            source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a pathlib.Path"
            )

        normalized = (
            source_path
            .expanduser()
            .resolve()
        )

        if not normalized.exists():
            raise FileNotFoundError(
                normalized
            )

        if normalized.is_dir():
            raise SourceArtifactMaterializationError(
                "provider source path must be a file: "
                f"{normalized}"
            )

        if not normalized.is_file():
            raise SourceArtifactMaterializationError(
                "provider source path must be a "
                "regular file: "
                f"{normalized}"
            )

        return normalized

    @staticmethod
    def _validate_regular_file(
        path: Path,
        *,
        description: str,
    ) -> Path:
        if not isinstance(
            path,
            Path,
        ):
            raise TypeError(
                f"{description} must be a pathlib.Path"
            )

        normalized = (
            path.expanduser().resolve()
        )

        if not normalized.exists():
            raise SourceArtifactMaterializationError(
                f"{description} does not exist: "
                f"{normalized}"
            )

        if normalized.is_dir():
            raise SourceArtifactMaterializationError(
                f"{description} cannot be a directory: "
                f"{normalized}"
            )

        if not normalized.is_file():
            raise SourceArtifactMaterializationError(
                f"{description} must be a regular file: "
                f"{normalized}"
            )

        return normalized

    @classmethod
    def _sha256_file(
        cls,
        path: Path,
    ) -> str:
        digest = sha256()

        with path.open(
            "rb",
        ) as handle:
            while True:
                block = handle.read(
                    cls.COPY_BUFFER_SIZE
                )

                if not block:
                    break

                digest.update(
                    block
                )

        return digest.hexdigest()

    @staticmethod
    def _remove_partial_destination(
        destination: Path,
    ) -> None:
        try:
            if (
                destination.exists()
                or destination.is_symlink()
            ):
                destination.unlink()

        except OSError:
            #
            # Preserve the original materialization exception.
            #
            pass