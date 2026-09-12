from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol

from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadata,
)
from treeforge.android.filesystem.metadata.builder import (
    FilesystemMetadataBuilder,
)


class ErofsFilesystemBackendError(RuntimeError):
    """
    Raised when an EROFS filesystem image cannot be processed.
    """


class ErofsRunnerLike(Protocol):
    """
    Minimum runner interface used by the EROFS backend.
    """


class ErofsWalkNodeLike(Protocol):
    """
    Marker interface for nodes yielded by the EROFS walker.
    """


class ErofsWalkerLike(Protocol):
    """
    Walker interface required by the EROFS backend.
    """

    def walk(
        self,
        path: str = "/",
        *,
        include_root: bool = True,
        max_depth: int | None = None,
    ) -> Iterator[ErofsWalkNodeLike]:
        """
        Walk nodes beneath a path inside the EROFS image.
        """


class ErofsMetadataBuilderLike(Protocol):
    """
    Metadata-builder interface required by the EROFS backend.
    """

    def build(
        self,
        *,
        source: Path,
        filesystem_type: str,
        nodes: object,
    ) -> FilesystemMetadata:
        """
        Build normalized filesystem metadata.
        """


RunnerFactory = Callable[
    [Path],
    ErofsRunnerLike,
]

WalkerFactory = Callable[
    [ErofsRunnerLike],
    ErofsWalkerLike,
]

XattrCollectorFactory = Callable[
    [ErofsRunnerLike],
    object,
]

MetadataBuilderFactory = Callable[
    [object],
    ErofsMetadataBuilderLike,
]


class ErofsFilesystemBackend:
    """
    Read metadata from an EROFS filesystem image.

    This class coordinates the lower-level EROFS runner, walker, extended
    attribute collector, and metadata builder.

    Concrete production implementations of the runner, walker, and xattr
    collector will be added in later milestones. Injectable factories allow
    the backend contract and manager routing to be tested first.
    """

    filesystem_type = "erofs"

    def __init__(
        self,
        *,
        runner_factory: RunnerFactory | None = None,
        walker_factory: WalkerFactory | None = None,
        xattr_collector_factory: XattrCollectorFactory | None = None,
        metadata_builder_factory: MetadataBuilderFactory | None = None,
    ) -> None:
        self._runner_factory = (
            runner_factory
            if runner_factory is not None
            else self._create_runner
        )

        self._walker_factory = (
            walker_factory
            if walker_factory is not None
            else self._create_walker
        )

        self._xattr_collector_factory = (
            xattr_collector_factory
            if xattr_collector_factory is not None
            else self._create_xattr_collector
        )

        self._metadata_builder_factory = (
            metadata_builder_factory
            if metadata_builder_factory is not None
            else self._create_metadata_builder
        )

    def collect_metadata(
        self,
        source: Path,
        *,
        root: str = "/",
        include_root: bool = True,
        max_depth: int | None = None,
    ) -> FilesystemMetadata:
        """
        Collect normalized metadata from an EROFS image.

        Args:
            source:
                Raw EROFS filesystem image.

            root:
                Absolute path inside the image at which traversal begins.

            include_root:
                Whether the traversal root should be represented in metadata.

            max_depth:
                Optional maximum traversal depth relative to ``root``.

        Returns:
            Normalized filesystem metadata.

        Raises:
            TypeError:
                If an argument has an invalid type.

            ValueError:
                If an argument contains an invalid value.

            FileNotFoundError:
                If the source image does not exist.

            IsADirectoryError:
                If the source path is a directory.

            ErofsFilesystemBackendError:
                If backend construction or metadata collection fails.
        """

        image = self._validate_source(
            source
        )

        normalized_root = self._validate_root(
            root
        )

        normalized_include_root = (
            self._validate_include_root(
                include_root
            )
        )

        normalized_max_depth = (
            self._validate_max_depth(
                max_depth
            )
        )

        try:
            runner = self._runner_factory(
                image
            )
        except Exception as error:
            raise ErofsFilesystemBackendError(
                f"Unable to create EROFS runner for {image}"
            ) from error

        try:
            walker = self._walker_factory(
                runner
            )
        except Exception as error:
            raise ErofsFilesystemBackendError(
                f"Unable to create EROFS walker for {image}"
            ) from error

        try:
            xattr_collector = (
                self._xattr_collector_factory(
                    runner
                )
            )
        except Exception as error:
            raise ErofsFilesystemBackendError(
                "Unable to create EROFS extended-attribute "
                f"collector for {image}"
            ) from error

        try:
            builder = self._metadata_builder_factory(
                xattr_collector
            )
        except Exception as error:
            raise ErofsFilesystemBackendError(
                f"Unable to create metadata builder for {image}"
            ) from error

        try:
            nodes = walker.walk(
                normalized_root,
                include_root=normalized_include_root,
                max_depth=normalized_max_depth,
            )

            return builder.build(
                source=image,
                filesystem_type=self.filesystem_type,
                nodes=nodes,
            )
        except ErofsFilesystemBackendError:
            raise
        except Exception as error:
            raise ErofsFilesystemBackendError(
                f"Unable to collect EROFS metadata from {image}"
            ) from error

    @staticmethod
    def _create_runner(
        source: Path,
    ) -> ErofsRunnerLike:
        """
        Construct the production EROFS runner.

        The concrete runner will be added in the next EROFS milestone.
        """

        raise ErofsFilesystemBackendError(
            "EROFS runner is not implemented yet."
        )

    @staticmethod
    def _create_walker(
        runner: ErofsRunnerLike,
    ) -> ErofsWalkerLike:
        """
        Construct the production EROFS walker.
        """

        raise ErofsFilesystemBackendError(
            "EROFS walker is not implemented yet."
        )

    @staticmethod
    def _create_xattr_collector(
        runner: ErofsRunnerLike,
    ) -> object:
        """
        Construct the production EROFS xattr collector.
        """

        raise ErofsFilesystemBackendError(
            "EROFS xattr collector is not implemented yet."
        )

    @staticmethod
    def _create_metadata_builder(
        xattr_collector: object,
    ) -> FilesystemMetadataBuilder:
        """
        Construct the common normalized metadata builder.
        """

        return FilesystemMetadataBuilder(
            xattr_collector=xattr_collector,
        )

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> Path:
        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path."
            )

        if not source.exists():
            raise FileNotFoundError(
                f"EROFS image does not exist: {source}"
            )

        if source.is_dir():
            raise IsADirectoryError(
                f"EROFS image cannot be a directory: {source}"
            )

        if not source.is_file():
            raise ValueError(
                f"EROFS image must be a regular file: {source}"
            )

        return source

    @staticmethod
    def _validate_root(
        root: str,
    ) -> str:
        if not isinstance(
            root,
            str,
        ):
            raise TypeError(
                "root must be a string."
            )

        normalized = root.strip()

        if not normalized:
            raise ValueError(
                "root cannot be empty."
            )

        if not normalized.startswith("/"):
            raise ValueError(
                "root must be an absolute filesystem path."
            )

        if "\x00" in normalized:
            raise ValueError(
                "root cannot contain null bytes."
            )

        if (
            "\n" in normalized
            or "\r" in normalized
        ):
            raise ValueError(
                "root cannot contain newlines."
            )

        return normalized

    @staticmethod
    def _validate_include_root(
        include_root: bool,
    ) -> bool:
        if not isinstance(
            include_root,
            bool,
        ):
            raise TypeError(
                "include_root must be a boolean."
            )

        return include_root

    @staticmethod
    def _validate_max_depth(
        max_depth: int | None,
    ) -> int | None:
        if max_depth is None:
            return None

        if (
            isinstance(
                max_depth,
                bool,
            )
            or not isinstance(
                max_depth,
                int,
            )
        ):
            raise TypeError(
                "max_depth must be an integer or None."
            )

        if max_depth < 0:
            raise ValueError(
                "max_depth cannot be negative."
            )

        return max_depth