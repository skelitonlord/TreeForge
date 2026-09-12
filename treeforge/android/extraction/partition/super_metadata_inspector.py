from __future__ import annotations

from pathlib import Path

from treeforge.android.extraction.partition.lpdump import (
    LpdumpError,
    LpdumpRunner,
)
from treeforge.android.extraction.partition.lpdump_parser import (
    LpdumpMetadata,
    LpdumpParseError,
    LpdumpParser,
)


class SuperMetadataInspectorError(RuntimeError):
    """
    Base error raised while inspecting dynamic-partition metadata.
    """


class SuperMetadataExecutionError(
    SuperMetadataInspectorError
):
    """
    Raised when lpdump cannot inspect the supplied super image.
    """


class SuperMetadataParseError(
    SuperMetadataInspectorError
):
    """
    Raised when lpdump output cannot be converted into metadata.
    """


class SuperMetadataInspector:
    """
    Inspect Android dynamic-partition metadata from a super image.

    The inspector composes the lower-level LpdumpRunner and LpdumpParser
    components behind one public API.

    Responsibilities:

    - validate the supplied super image;
    - execute lpdump through LpdumpRunner;
    - parse the captured output through LpdumpParser;
    - translate runner and parser failures into inspector-level errors;
    - return normalized immutable LpdumpMetadata.

    The inspector does not interpret the metadata as a TreeForge partition
    layout. That responsibility belongs to the later normalized-layout layer.
    """

    def __init__(
        self,
        *,
        runner: LpdumpRunner | None = None,
        parser: LpdumpParser | None = None,
    ) -> None:
        """
        Create a super metadata inspector.

        Args:
            runner:
                Optional lpdump runner. Supplying one allows tests and callers
                to control command execution.

            parser:
                Optional lpdump output parser. Supplying one allows tests and
                callers to control parsing behavior.
        """

        self._runner = (
            runner
            if runner is not None
            else LpdumpRunner()
        )

        self._parser = (
            parser
            if parser is not None
            else LpdumpParser()
        )

    @property
    def runner(self) -> LpdumpRunner:
        """
        Return the configured lpdump runner.
        """

        return self._runner

    @property
    def parser(self) -> LpdumpParser:
        """
        Return the configured lpdump parser.
        """

        return self._parser

    def inspect(
        self,
        source: Path,
    ) -> LpdumpMetadata:
        """
        Inspect dynamic-partition metadata from a super image.

        Args:
            source:
                Path to a raw Android super partition image.

        Returns:
            Parsed and normalized logical-partition metadata.

        Raises:
            TypeError:
                If source is not a pathlib.Path.

            FileNotFoundError:
                If source does not exist.

            IsADirectoryError:
                If source is a directory.

            SuperMetadataExecutionError:
                If lpdump cannot inspect the image.

            SuperMetadataParseError:
                If lpdump output cannot be parsed.
        """

        normalized_source = self._validate_source(
            source
        )

        try:
            result = self._runner.inspect(
                normalized_source
            )
        except LpdumpError as error:
            raise SuperMetadataExecutionError(
                f"Unable to inspect super metadata from "
                f"{normalized_source}"
            ) from error
        except Exception as error:
            raise SuperMetadataExecutionError(
                f"Unexpected failure while inspecting super metadata from "
                f"{normalized_source}"
            ) from error

        try:
            return self._parser.parse(
                result.stdout
            )
        except LpdumpParseError as error:
            raise SuperMetadataParseError(
                f"Unable to parse super metadata from "
                f"{normalized_source}"
            ) from error
        except Exception as error:
            raise SuperMetadataParseError(
                f"Unexpected failure while parsing super metadata from "
                f"{normalized_source}"
            ) from error

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> Path:
        """
        Validate the supplied super image before invoking lpdump.
        """

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path"
            )

        if not source.exists():
            raise FileNotFoundError(
                f"Super image source does not exist: "
                f"{source}"
            )

        if source.is_dir():
            raise IsADirectoryError(
                f"Super image source cannot be a directory: "
                f"{source}"
            )

        if not source.is_file():
            raise ValueError(
                f"Super image source must be a regular file: "
                f"{source}"
            )

        return source