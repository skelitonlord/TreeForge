from __future__ import annotations

from pathlib import Path


class LogicalPartitionContainerDetector:
    """
    Cheap structural detector for Android logical-partition containers.

    This detector performs only physical signature recognition. It does not
    parse LP metadata, derive partition names, or establish layout semantics.

    Authoritative metadata validation remains the responsibility of
    SuperMetadataInspector/lpdump.
    """

    LP_METADATA_MAGIC = (
        b"\x67\x44\x6c\x61"
    )

    MAGIC_OFFSETS = (
        0,
        4096,
    )

    @classmethod
    def detect(
        cls,
        source: Path,
    ) -> bool:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.is_file():
            return False

        try:
            with source.open(
                "rb",
            ) as stream:
                for offset in (
                    cls.MAGIC_OFFSETS
                ):
                    stream.seek(
                        offset
                    )

                    if (
                        stream.read(
                            len(
                                cls.LP_METADATA_MAGIC
                            )
                        )
                        == cls.LP_METADATA_MAGIC
                    ):
                        return True

        except OSError:
            return False

        return False
