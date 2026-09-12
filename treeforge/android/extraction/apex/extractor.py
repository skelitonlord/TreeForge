from __future__ import annotations

from pathlib import Path
from shutil import rmtree
from zipfile import BadZipFile, ZipFile

from treeforge.android.extraction.model import (
    ExtractedArtifact,
    ExtractionArtifactKind,
    ExtractionFact,
    ExtractionOperation,
    ExtractionToolEvidence,
)


class ApexContainerExtractionError(
    RuntimeError,
):
    """
    Raised when an APEX container cannot be physically materialized.
    """


class ApexContainerExtractor:
    """
    Materialize the next physical layer of an Android APEX container.

    TreeForge recognizes APEX structurally rather than relying on filename
    suffixes. This is required for compressed APEX containers whose outer
    container exposes an ``original_apex`` member without an ``.apex`` suffix.

    Supported physical transitions are:

        APEX/CAPEX -> apex_payload.img

    or:

        compressed APEX/CAPEX -> original_apex

    The resulting artifact remains part of canonical Extraction lineage and
    may be consumed again by RecursiveExtractionStage.
    """

    _MANIFEST_MEMBER = (
        "apex_manifest.pb"
    )

    _PUBLIC_KEY_MEMBER = (
        "apex_pubkey"
    )

    _PAYLOAD_MEMBER = (
        "apex_payload.img"
    )

    _ORIGINAL_APEX_MEMBER = (
        "original_apex"
    )

    def supports(
        self,
        parent: ExtractedArtifact,
    ) -> bool:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            return False

        try:
            with ZipFile(
                parent.path,
                "r",
            ) as archive:
                members = set(
                    archive.namelist()
                )

        except (
            BadZipFile,
            OSError,
        ):
            return False

        if (
            self._MANIFEST_MEMBER
            not in members
        ):
            return False

        if (
            self._PUBLIC_KEY_MEMBER
            not in members
        ):
            return False

        return (
            self._PAYLOAD_MEMBER
            in members
            or self._ORIGINAL_APEX_MEMBER
            in members
        )

    def extract(
        self,
        parent: ExtractedArtifact,
        destination: Path,
    ) -> ExtractedArtifact:
        if not isinstance(
            parent,
            ExtractedArtifact,
        ):
            raise TypeError(
                "parent must be an ExtractedArtifact"
            )

        if (
            parent.kind
            is not ExtractionArtifactKind.FILE
        ):
            raise ApexContainerExtractionError(
                "APEX extraction parent must be a file"
            )

        if not isinstance(
            destination,
            Path,
        ):
            raise TypeError(
                "destination must be a pathlib.Path"
            )

        if not parent.path.exists():
            raise FileNotFoundError(
                "APEX container does not exist: "
                f"{parent.path}"
            )

        if not parent.path.is_file():
            raise ApexContainerExtractionError(
                "APEX extraction source must be "
                f"a regular file: {parent.path}"
            )

        try:
            with ZipFile(
                parent.path,
                "r",
            ) as archive:
                members = set(
                    archive.namelist()
                )

                if (
                    self._MANIFEST_MEMBER
                    not in members
                    or self._PUBLIC_KEY_MEMBER
                    not in members
                ):
                    raise ApexContainerExtractionError(
                        "source is not a structurally "
                        "recognized APEX container: "
                        f"{parent.path}"
                    )

                if (
                    self._PAYLOAD_MEMBER
                    in members
                ):
                    member = (
                        self._PAYLOAD_MEMBER
                    )

                elif (
                    self._ORIGINAL_APEX_MEMBER
                    in members
                ):
                    member = (
                        self._ORIGINAL_APEX_MEMBER
                    )

                else:
                    raise ApexContainerExtractionError(
                        "APEX container exposes neither "
                        "apex_payload.img nor original_apex: "
                        f"{parent.path}"
                    )

                self._prepare_destination(
                    destination
                )

                with archive.open(
                    member,
                    "r",
                ) as source:
                    with destination.open(
                        "wb",
                    ) as target:
                        while True:
                            chunk = source.read(
                                1024 * 1024
                            )

                            if not chunk:
                                break

                            target.write(
                                chunk
                            )

        except ApexContainerExtractionError:
            self._cleanup_failed_destination(
                destination
            )
            raise

        except (
            BadZipFile,
            KeyError,
            OSError,
        ) as error:
            self._cleanup_failed_destination(
                destination
            )

            raise ApexContainerExtractionError(
                "Unable to extract APEX container: "
                f"{parent.path}"
            ) from error

        if not destination.exists():
            raise ApexContainerExtractionError(
                "APEX extraction did not create "
                f"its destination: {destination}"
            )

        if not destination.is_file():
            raise ApexContainerExtractionError(
                "APEX extraction destination is "
                f"not a regular file: {destination}"
            )

        semantic_name = (
            "apex_payload"
            if member
            == self._PAYLOAD_MEMBER
            else "original_apex"
        )

        return ExtractedArtifact(
            source=parent.source,
            path=destination,
            kind=ExtractionArtifactKind.FILE,
            operation=(
                ExtractionOperation
                .APEX_CONTAINER_EXTRACTION
            ),
            semantic_name=semantic_name,
            parent=parent,
            tool=ExtractionToolEvidence(
                name="python.zipfile",
            ),
            facts=(
                ExtractionFact(
                    name="archive_member",
                    value=member,
                ),
                ExtractionFact(
                    name="container_format",
                    value="apex",
                ),
            ),
        )

    @staticmethod
    def _prepare_destination(
        destination: Path,
    ) -> None:
        if destination.exists():
            if destination.is_dir():
                rmtree(
                    destination
                )
            else:
                destination.unlink()

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _cleanup_failed_destination(
        destination: Path,
    ) -> None:
        try:
            if destination.is_dir():
                rmtree(
                    destination
                )

            elif destination.exists():
                destination.unlink()

        except OSError:
            pass