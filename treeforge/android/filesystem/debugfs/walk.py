from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Protocol

from treeforge.android.filesystem.debugfs.directory import (
    DebugfsDirectoryEntry,
    DebugfsDirectoryParser,
)
from treeforge.android.filesystem.debugfs.stat import (
    DebugfsInodeType,
    DebugfsStat,
    DebugfsStatParser,
)


class DebugfsWalkError(RuntimeError):
    """
    Raised when a debugfs filesystem walk cannot be completed.
    """


class DebugfsWalkRunner(Protocol):
    """
    Minimum runner interface required by DebugfsWalker.
    """

    def list_directory(
        self,
        path: str,
    ) -> str:
        """
        Return raw output from ``debugfs ls -l``.
        """

    def stat(
        self,
        path: str,
    ) -> str:
        """
        Return raw output from ``debugfs stat``.
        """


@dataclass(frozen=True)
class DebugfsWalkNode:
    """
    One filesystem node discovered during a debugfs walk.
    """

    path: PurePosixPath
    name: str
    parent: PurePosixPath | None
    depth: int
    directory_entry: DebugfsDirectoryEntry | None
    stat: DebugfsStat

    @property
    def inode(self) -> int:
        return self.stat.inode

    @property
    def inode_type(self) -> DebugfsInodeType:
        return self.stat.inode_type

    @property
    def is_directory(self) -> bool:
        return self.inode_type is DebugfsInodeType.DIRECTORY

    @property
    def is_regular_file(self) -> bool:
        return self.inode_type is DebugfsInodeType.REGULAR_FILE

    @property
    def is_symlink(self) -> bool:
        return self.inode_type is DebugfsInodeType.SYMLINK


class DebugfsWalker:
    """
    Recursively traverse a filesystem through DebugfsRunner.

    Traversal is:

    - depth-first,
    - deterministic,
    - cycle-safe,
    - and independent of metadata-building logic.
    """

    def __init__(
        self,
        runner: DebugfsWalkRunner,
    ) -> None:
        self._runner = runner

    def walk(
        self,
        path: str | PurePosixPath = "/",
        *,
        include_root: bool = True,
        max_depth: int | None = None,
    ) -> Iterator[DebugfsWalkNode]:
        """
        Walk a filesystem beginning at ``path``.

        Args:
            path:
                Absolute POSIX path inside the image.

            include_root:
                Whether the starting path itself should be yielded.

            max_depth:
                Maximum depth relative to the starting path. A value of zero
                yields only the root when ``include_root`` is true.

        Raises:
            TypeError:
                If an argument has an invalid type.

            ValueError:
                If the path is invalid or max_depth is negative.

            DebugfsWalkError:
                If debugfs output is inconsistent or traversal fails.
        """

        root = self._normalize_path(path)

        if not isinstance(include_root, bool):
            raise TypeError(
                "include_root must be a boolean"
            )

        if max_depth is not None:
            if not isinstance(max_depth, int):
                raise TypeError(
                    "max_depth must be an integer or None"
                )

            if max_depth < 0:
                raise ValueError(
                    "max_depth cannot be negative"
                )

        visited_directories: set[int] = set()

        root_stat = self._load_stat(root)

        root_node = DebugfsWalkNode(
            path=root,
            name=self._name_for_path(root),
            parent=(
                None
                if root == PurePosixPath("/")
                else root.parent
            ),
            depth=0,
            directory_entry=None,
            stat=root_stat,
        )

        if include_root:
            yield root_node

        if not root_node.is_directory:
            return

        if max_depth == 0:
            return

        yield from self._walk_directory(
            root,
            depth=0,
            max_depth=max_depth,
            visited_directories=visited_directories,
        )

    def _walk_directory(
        self,
        path: PurePosixPath,
        *,
        depth: int,
        max_depth: int | None,
        visited_directories: set[int],
    ) -> Iterator[DebugfsWalkNode]:
        directory_stat = self._load_stat(path)

        if directory_stat.inode in visited_directories:
            return

        visited_directories.add(
            directory_stat.inode
        )

        entries = self._load_directory(path)

        for entry in sorted(
            entries,
            key=self._entry_sort_key,
        ):
            if entry.is_dot_entry:
                continue

            child_path = self._join_path(
                path,
                entry.name,
            )

            child_stat = self._load_stat(
                child_path
            )

            child_depth = depth + 1

            node = DebugfsWalkNode(
                path=child_path,
                name=entry.name,
                parent=path,
                depth=child_depth,
                directory_entry=entry,
                stat=child_stat,
            )

            yield node

            if not node.is_directory:
                continue

            if (
                max_depth is not None
                and child_depth >= max_depth
            ):
                continue

            if child_stat.inode in visited_directories:
                continue

            yield from self._walk_directory(
                child_path,
                depth=child_depth,
                max_depth=max_depth,
                visited_directories=visited_directories,
            )

    def _load_stat(
        self,
        path: PurePosixPath,
    ) -> DebugfsStat:
        try:
            output = self._runner.stat(
                str(path)
            )
            return DebugfsStatParser.parse(
                output
            )
        except Exception as error:
            if isinstance(error, DebugfsWalkError):
                raise

            raise DebugfsWalkError(
                f"Unable to stat filesystem path {path}"
            ) from error

    def _load_directory(
        self,
        path: PurePosixPath,
    ) -> tuple[DebugfsDirectoryEntry, ...]:
        try:
            output = self._runner.list_directory(
                str(path)
            )
            return DebugfsDirectoryParser.parse(
                output
            )
        except Exception as error:
            if isinstance(error, DebugfsWalkError):
                raise

            raise DebugfsWalkError(
                f"Unable to list filesystem directory {path}"
            ) from error

    @staticmethod
    def _normalize_path(
        path: str | PurePosixPath,
    ) -> PurePosixPath:
        if not isinstance(
            path,
            (str, PurePosixPath),
        ):
            raise TypeError(
                "walk path must be a string or PurePosixPath"
            )

        if isinstance(path, str):
            if not path.strip():
                raise ValueError(
                    "walk path cannot be empty"
                )

            normalized = PurePosixPath(
                path.strip()
            )
        else:
            normalized = path

        if not normalized.is_absolute():
            raise ValueError(
                "walk path must be absolute"
            )

        if ".." in normalized.parts:
            raise ValueError(
                "walk path cannot contain parent traversal"
            )

        return normalized

    @staticmethod
    def _join_path(
        parent: PurePosixPath,
        name: str,
    ) -> PurePosixPath:
        if not name:
            raise DebugfsWalkError(
                "Directory entry name cannot be empty"
            )

        if "/" in name:
            raise DebugfsWalkError(
                f"Directory entry contains a path separator: {name!r}"
            )

        if name in {".", ".."}:
            raise DebugfsWalkError(
                f"Invalid child entry name: {name!r}"
            )

        return parent / name

    @staticmethod
    def _entry_sort_key(
        entry: DebugfsDirectoryEntry,
    ) -> tuple[str, int]:
        return (
            entry.name,
            entry.inode,
        )

    @staticmethod
    def _name_for_path(
        path: PurePosixPath,
    ) -> str:
        if path == PurePosixPath("/"):
            return "/"

        return path.name