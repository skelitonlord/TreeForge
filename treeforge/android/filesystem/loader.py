from pathlib import Path

from treeforge.android.filesystem.filesystem import Filesystem


class FilesystemLoader:
    """
    Creates an Android filesystem abstraction from an extracted directory.
    """

    @staticmethod
    def load(
        root: Path,
    ) -> Filesystem:
        """
        Build a Filesystem abstraction rooted at the supplied directory.
        """

        return Filesystem(
            root=root,
        )