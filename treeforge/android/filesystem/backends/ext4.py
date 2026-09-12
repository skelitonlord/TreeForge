from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol

from treeforge.android.filesystem.debugfs.runner import (
    DebugfsRunner,
)
from treeforge.android.filesystem.debugfs.walk import (
    DebugfsWalker,
    DebugfsWalkNode,
)
from treeforge.android.filesystem.debugfs.xattr import (
    DebugfsXattrCollector,
)
from treeforge.android.filesystem.metadata.model import (
    FilesystemMetadata,
)
from treeforge.android.filesystem.metadata.builder import (
    FilesystemMetadataBuilder,
    MetadataEntryProgressCallback,
)
from treeforge.android.format.filesystem import (
    FilesystemDetector,
    FilesystemType,
)

class Ext4FilesystemBackendError(RuntimeError):
    """
    Raised when an ext4 filesystem image cannot be processed.
    """


class Ext4RunnerLike(Protocol):
    """
    Image-bound debugfs runner interface used by the ext4 backend.

    The underlying filesystem image is bound when the runner is created.
    Higher-level consumers therefore only supply paths inside that image.
    """

    def stat(
        self,
        path: str,
    ) -> str:
        """Return raw debugfs stat output for one filesystem path."""

    def list_directory(
        self,
        path: str,
    ) -> str:
        """Return raw debugfs directory output for one filesystem path."""

    def list_xattrs(
        self,
        path: str,
    ) -> str:
        """Return raw debugfs extended-attribute listing output."""

    def get_xattr(
        self,
        path: str,
        name: str,
    ) -> str:
        """Return one extended-attribute value as hexadecimal output."""


class Ext4WalkerLike(Protocol):
    """
    Walker interface required by the ext4 backend.
    """

    def walk(
        self,
        path: str = "/",
        *,
        include_root: bool = True,
        max_depth: int | None = None,
    ) -> Iterator[DebugfsWalkNode]:
        """
        Walk nodes beneath an image path.
        """


class Ext4MetadataBuilderLike(Protocol):
    """
    Metadata-builder interface required by the ext4 backend.
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


class _ImageBoundDebugfsRunner:
    """
    Bind a low-level DebugfsRunner to one filesystem image.

    DebugfsRunner deliberately accepts an image for every command:

        runner.stat(image, path)

    DebugfsWalker and DebugfsXattrCollector operate on one image and expect:

        runner.stat(path)
        runner.list_directory(path)
        runner.list_xattrs(path)
        runner.get_xattr(path, name)

    This adapter connects those two interfaces without changing either
    reusable component.
    """

    def __init__(
        self,
        image: Path,
        *,
        runner: DebugfsRunner | None = None,
    ) -> None:
        self._image = self._validate_image(
            image,
        )

        self._runner = (
            runner
            if runner is not None
            else DebugfsRunner()
        )

    @property
    def image(
        self,
    ) -> Path:
        """Return the bound filesystem image."""

        return self._image

    @property
    def runner(
        self,
    ) -> DebugfsRunner:
        """Return the underlying low-level debugfs runner."""

        return self._runner

    def stat(
        self,
        path: str,
    ) -> str:
        """Run debugfs stat against the bound image."""

        return self._runner.stat(
            self._image,
            path,
        )

    def list_directory(
        self,
        path: str,
    ) -> str:
        """Run a detailed directory listing against the bound image."""

        return self._runner.list_directory(
            self._image,
            path,
        )

    def list_xattrs(
        self,
        path: str,
    ) -> str:
        """List extended attributes for a path in the bound image."""

        normalized_path = self._validate_filesystem_path(
            path,
        )

        return self._runner.run(
            self._image,
            (
                "ea_list "
                f"{self._runner.quote_argument(normalized_path)}"
            ),
        )

    def get_xattr(
        self,
        path: str,
        name: str,
    ) -> str:
        """Read one extended attribute from the bound image."""

        normalized_path = self._validate_filesystem_path(
            path,
        )

        normalized_name = self._validate_xattr_name(
            name,
        )

        return self._runner.run(
            self._image,
            (
                "ea_get -x "
                f"{self._runner.quote_argument(normalized_path)} "
                f"{self._runner.quote_argument(normalized_name)}"
            ),
        )

    @staticmethod
    def _validate_image(
        image: Path,
    ) -> Path:
        """Validate the image bound to the adapter."""

        if not isinstance(
            image,
            Path,
        ):
            raise TypeError(
                "image must be a pathlib.Path"
            )

        if not image.exists():
            raise FileNotFoundError(
                f"Debugfs image does not exist: {image}"
            )

        if image.is_dir():
            raise IsADirectoryError(
                f"Debugfs image cannot be a directory: {image}"
            )

        if not image.is_file():
            raise ValueError(
                f"Debugfs image must be a regular file: {image}"
            )

        return image

    @staticmethod
    def _validate_filesystem_path(
        path: str,
    ) -> str:
        """Validate a path used in a debugfs request."""

        if not isinstance(
            path,
            str,
        ):
            raise TypeError(
                "debugfs filesystem path must be a string"
            )

        normalized = path.strip()

        if not normalized:
            raise ValueError(
                "debugfs filesystem path cannot be empty"
            )

        if "\x00" in normalized:
            raise ValueError(
                "debugfs filesystem path cannot contain null bytes"
            )

        if (
            "\n" in normalized
            or "\r" in normalized
        ):
            raise ValueError(
                "debugfs filesystem path cannot contain newlines"
            )

        return normalized

    @staticmethod
    def _validate_xattr_name(
        name: str,
    ) -> str:
        """Validate one extended-attribute name."""

        if not isinstance(
            name,
            str,
        ):
            raise TypeError(
                "xattr name must be a string"
            )

        normalized = name.strip()

        if not normalized:
            raise ValueError(
                "xattr name cannot be empty"
            )

        if "\x00" in normalized:
            raise ValueError(
                "xattr name cannot contain null bytes"
            )

        if (
            "\n" in normalized
            or "\r" in normalized
        ):
            raise ValueError(
                "xattr name cannot contain newlines"
            )

        return normalized


RunnerFactory = Callable[
    [Path],
    Ext4RunnerLike,
]

WalkerFactory = Callable[
    [Ext4RunnerLike],
    Ext4WalkerLike,
]

XattrCollectorFactory = Callable[
    [Ext4RunnerLike],
    object,
]

MetadataBuilderFactory = Callable[
    [object],
    Ext4MetadataBuilderLike,
]


class Ext4FilesystemBackend:
    """
    Read metadata from an ext4 filesystem image.

    This class coordinates the low-level debugfs runner, deterministic
    filesystem walker, extended-attribute collector, and normalized metadata
    builder.

    A runner created for one collection operation is bound to the supplied
    image. That gives the walker and xattr collector a simple path-oriented
    interface while preserving DebugfsRunner as a reusable low-level command
    executor.
    """

    filesystem_type = "ext4"


    def __init__(
        self,
        *,
        runner_factory: RunnerFactory | None = None,
        walker_factory: WalkerFactory | None = None,
        xattr_collector_factory: (
            XattrCollectorFactory
            | None
        ) = None,
        metadata_builder_factory: (
            MetadataBuilderFactory
            | None
        ) = None,
        progress_callback: (
            MetadataEntryProgressCallback
            | None
        ) = None,
    ) -> None:
        self._runner_factory = (
            runner_factory
            if runner_factory is not None
            else self._create_runner
        )

        self._walker_factory = (
            walker_factory
            if walker_factory is not None
            else DebugfsWalker
        )

        self._xattr_collector_factory = (
            xattr_collector_factory
            if xattr_collector_factory is not None
            else DebugfsXattrCollector
        )

        self._progress_callback = progress_callback

        self._metadata_builder_factory = (
            metadata_builder_factory
            if metadata_builder_factory is not None
            else self._create_metadata_builder
        )


    def supports(
        self,
        source: Path,
    ) -> bool:
        """
        Return whether source is a raw ext4 filesystem image.
        """

        try:
            return (
                FilesystemDetector.detect(
                    Path(
                        source
                    )
                )
                is FilesystemType.EXT4
            )
        except (
            FileNotFoundError,
            OSError,
        ):
            return False

    def collect_metadata(
        self,
        source: Path,
        *,
        root: str = "/",
        include_root: bool = True,
        max_depth: int | None = None,
    ) -> FilesystemMetadata:
        """
        Collect normalized metadata from an ext4 image.

        Args:
            source:
                Raw ext4 filesystem image.

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

            Ext4FilesystemBackendError:
                If backend construction or metadata collection fails.
        """

        image = self._validate_source(
            source,
        )

        normalized_root = self._validate_root(
            root,
        )

        normalized_include_root = (
            self._validate_include_root(
                include_root,
            )
        )

        normalized_max_depth = (
            self._validate_max_depth(
                max_depth,
            )
        )

        try:
            runner = self._runner_factory(
                image,
            )
        except Exception as error:
            raise Ext4FilesystemBackendError(
                f"Unable to create debugfs runner for {image}"
            ) from error

        try:
            walker = self._walker_factory(
                runner,
            )
        except Exception as error:
            raise Ext4FilesystemBackendError(
                f"Unable to create filesystem walker for {image}"
            ) from error

        try:
            xattr_collector = (
                self._xattr_collector_factory(
                    runner,
                )
            )
        except Exception as error:
            raise Ext4FilesystemBackendError(
                "Unable to create extended-attribute collector "
                f"for {image}"
            ) from error

        try:
            builder = self._metadata_builder_factory(
                xattr_collector,
            )
        except Exception as error:
            raise Ext4FilesystemBackendError(
                f"Unable to create metadata builder for {image}"
            ) from error

        try:
            nodes = walker.walk(
                normalized_root,
                include_root=(
                    normalized_include_root
                ),
                max_depth=(
                    normalized_max_depth
                ),
            )

            return builder.build(
                source=image,
                filesystem_type=self.filesystem_type,
                nodes=nodes,
            )
        except Ext4FilesystemBackendError:
            raise
        except Exception as error:
            raise Ext4FilesystemBackendError(
                f"Unable to collect ext4 metadata from {image}"
            ) from error

    @staticmethod
    def _create_runner(
        source: Path,
    ) -> Ext4RunnerLike:
        """
        Construct a production image-bound debugfs runner.
        """

        return _ImageBoundDebugfsRunner(
            source,
        )

    def _create_metadata_builder(
        self,
        xattr_collector: object,
    ) -> FilesystemMetadataBuilder:
        """Construct the normalized metadata builder."""

        return FilesystemMetadataBuilder(
            xattr_collector=xattr_collector,
            progress_callback=self._progress_callback,
        )

    @staticmethod
    def _validate_source(
        source: Path,
    ) -> Path:
        """Validate the raw ext4 image."""

        if not isinstance(
            source,
            Path,
        ):
            raise TypeError(
                "source must be a pathlib.Path."
            )

        if not source.exists():
            raise FileNotFoundError(
                f"Ext4 image does not exist: {source}"
            )

        if source.is_dir():
            raise IsADirectoryError(
                f"Ext4 image cannot be a directory: {source}"
            )

        if not source.is_file():
            raise ValueError(
                f"Ext4 image must be a regular file: {source}"
            )

        return source

    @staticmethod
    def _validate_root(
        root: str,
    ) -> str:
        """Validate the traversal root."""

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
        """Validate the include-root option."""

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
        """Validate the optional traversal depth."""

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