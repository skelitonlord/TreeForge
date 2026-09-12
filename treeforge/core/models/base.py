from dataclasses import asdict


class Model:
    """Base class for all TreeForge models."""

    def to_dict(self) -> dict:
        """Convert this model to a dictionary."""
        return asdict(self)