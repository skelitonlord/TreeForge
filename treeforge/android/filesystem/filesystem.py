from pathlib import Path
import posixpath
import os


class Filesystem:
    """
    Represents an extracted Android filesystem.
    """

    def __init__(
        self,
        root: Path,
    ) -> None:

        self.root = root

    def exists(
        self,
        relative: str,
    ) -> bool:
        return self.resolve(
            relative,
        ).exists()

    def path(
        self,
        relative: str,
    ) -> Path:

        return self._normalize_path(
            relative,
        )
    
    def resolve(
        self,
        relative: str,
    ) -> Path:
        """
        Resolve symlinks using Android filesystem semantics.

        Relative symlink targets are resolved from the symlink's parent.
        Absolute symlink targets are resolved from this filesystem's root,
        not from the host filesystem root.
        """

        normalized = self.path(
            relative,
        )

        pending = list(
            normalized.relative_to(self.root).parts,
        )

        resolved = self.root
        visited: set[Path] = set()

        while pending:
            component = pending.pop(0)
            candidate = resolved / component

            if not candidate.is_symlink():
                resolved = candidate
                continue

            if candidate in visited:
                raise RuntimeError(
                    f"Symlink loop detected: {candidate}",
                )

            visited.add(candidate)

            target = Path(
                os.readlink(candidate),
            )

            if target.is_absolute():
                base = Path()
                target = Path(
                    target.as_posix().lstrip("/"),
                )
            else:
                base = resolved.relative_to(
                    self.root,
                )

            combined = base / target

            if pending:
                combined = combined / Path(
                    *pending,
                )

            normalized = self._normalize_path(
                combined.as_posix(),
            )

            pending = list(
                normalized.relative_to(self.root).parts,
            )

            resolved = self.root

        return resolved

    def glob(
        self,
        pattern: str,
    ):

        return self.root.glob(
            pattern,
        )

    def read_text(
        self,
        relative: str,
        encoding: str = "utf-8",
        errors: str | None = None,
    ) -> str:
        return self.resolve(
            relative,
        ).read_text(
            encoding=encoding,
            errors=errors,
        )

    def is_dir(
        self,
        relative: str,
    ) -> bool:
        return self.resolve(
            relative,
        ).is_dir()
    
    def is_file(
        self,
        relative: str,
    ) -> bool:
        return self.resolve(
            relative,
        ).is_file()

    def read_bytes(
        self,
        relative: str,
    ) -> bytes:
        return self.resolve(
            relative,
        ).read_bytes()

    def iterdir(
        self,
        relative: str,
    ):

        return self.path(
            relative,
        ).iterdir()

    def walk(
        self,
    ):

        for path in self.root.rglob("*"):
            if path.is_file():
                yield path

    def _normalize_path(
        self,
        relative: str,
    ) -> Path:
        """
        Normalize an Android filesystem path relative to this root.

        Leading slashes represent the root of the Android filesystem,
        rather than the host filesystem.
        """

        normalized = posixpath.normpath(
            relative.lstrip("/"),
        )

        if normalized.startswith(".."):
            raise ValueError(
                "Path escapes filesystem root.",
            )

        if normalized == ".":
            return self.root

        return self.root / normalized