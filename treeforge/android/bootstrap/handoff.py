from __future__ import annotations

import json

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


BOOTSTRAP_BOOT_IMAGE_HANDOFF_SCHEMA_VERSION = 1


class AndroidBootstrapHandoffError(
    RuntimeError
):
    pass


def sha256_file(
    path: Path,
) -> str:
    digest = sha256()

    with path.open(
        "rb"
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapBootImageReplacement:
    container_kind: str
    semantic_name: str

    replacement_path: Path
    replacement_size_bytes: int
    replacement_sha256: str

    original_component_path: Path
    original_component_size_bytes: int
    original_component_sha256: str

    cpio_path: Path
    cpio_size_bytes: int
    cpio_sha256: str

    compression: str

    rollback_required: bool

    def validate_artifacts(
        self,
    ) -> None:
        for (
            label,
            path,
            expected_size,
            expected_sha256,
        ) in (
            (
                "replacement",
                self.replacement_path,
                self.replacement_size_bytes,
                self.replacement_sha256,
            ),
            (
                "original component",
                self.original_component_path,
                self.original_component_size_bytes,
                self.original_component_sha256,
            ),
            (
                "CPIO",
                self.cpio_path,
                self.cpio_size_bytes,
                self.cpio_sha256,
            ),
        ):
            if not path.is_file():
                raise AndroidBootstrapHandoffError(
                    f"{label} artifact does not exist: {path}"
                )

            actual_size = (
                path.stat().st_size
            )

            if actual_size != expected_size:
                raise AndroidBootstrapHandoffError(
                    f"{label} artifact size changed: "
                    f"expected {expected_size}, "
                    f"got {actual_size}: {path}"
                )

            actual_sha256 = sha256_file(
                path
            )

            if actual_sha256 != expected_sha256:
                raise AndroidBootstrapHandoffError(
                    f"{label} artifact SHA-256 changed: {path}"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapBootImageHandoffManifest:
    """
    Durable Bootstrap -> Boot Image handoff.

    This carries stable cross-process locators and cryptographic artifact
    evidence. It deliberately carries no AVB private-key selection, signing
    policy, slot selection, fastboot operation, or hardware decision.
    """

    parsing_snapshot_path: Path
    parsing_snapshot_sha256: str

    replacements: tuple[
        AndroidBootstrapBootImageReplacement,
        ...,
    ]

    schema_version: int = (
        BOOTSTRAP_BOOT_IMAGE_HANDOFF_SCHEMA_VERSION
    )

    def __post_init__(
        self,
    ) -> None:
        if (
            self.schema_version
            != BOOTSTRAP_BOOT_IMAGE_HANDOFF_SCHEMA_VERSION
        ):
            raise ValueError(
                "unsupported Bootstrap Boot Image handoff schema: "
                f"{self.schema_version}"
            )

        if not isinstance(
            self.parsing_snapshot_path,
            Path,
        ):
            raise TypeError(
                "parsing_snapshot_path must be a Path"
            )

        if (
            not isinstance(
                self.parsing_snapshot_sha256,
                str,
            )
            or len(
                self.parsing_snapshot_sha256
            ) != 64
        ):
            raise ValueError(
                "parsing_snapshot_sha256 must be a SHA-256 digest"
            )

        if not isinstance(
            self.replacements,
            tuple,
        ):
            raise TypeError(
                "replacements must be a tuple"
            )

        if not self.replacements:
            raise ValueError(
                "Bootstrap Boot Image handoff requires at least one "
                "replacement"
            )

        if not all(
            isinstance(
                value,
                AndroidBootstrapBootImageReplacement,
            )
            for value
            in self.replacements
        ):
            raise TypeError(
                "replacements contain an invalid value"
            )

    def validate_parsing_snapshot(
        self,
        path: Path,
    ) -> None:
        if not path.is_file():
            raise AndroidBootstrapHandoffError(
                f"Parsing snapshot does not exist: {path}"
            )

        actual_sha256 = sha256_file(
            path
        )

        if (
            actual_sha256
            != self.parsing_snapshot_sha256
        ):
            raise AndroidBootstrapHandoffError(
                "Bootstrap handoff belongs to a different canonical "
                "Parsing snapshot"
            )

    def validate_artifacts(
        self,
    ) -> None:
        for replacement in self.replacements:
            replacement.validate_artifacts()

    def write(
        self,
        path: Path,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "schema_version": self.schema_version,
            "parsing_snapshot": {
                "path": str(
                    self.parsing_snapshot_path
                ),
                "sha256": (
                    self.parsing_snapshot_sha256
                ),
            },
            "replacements": [
                {
                    "container_kind": (
                        value.container_kind
                    ),
                    "semantic_name": (
                        value.semantic_name
                    ),
                    "replacement": {
                        "path": str(
                            value.replacement_path
                        ),
                        "size_bytes": (
                            value.replacement_size_bytes
                        ),
                        "sha256": (
                            value.replacement_sha256
                        ),
                    },
                    "original_component": {
                        "path": str(
                            value.original_component_path
                        ),
                        "size_bytes": (
                            value.original_component_size_bytes
                        ),
                        "sha256": (
                            value.original_component_sha256
                        ),
                    },
                    "cpio": {
                        "path": str(
                            value.cpio_path
                        ),
                        "size_bytes": (
                            value.cpio_size_bytes
                        ),
                        "sha256": (
                            value.cpio_sha256
                        ),
                    },
                    "compression": (
                        value.compression
                    ),
                    "rollback_required": (
                        value.rollback_required
                    ),
                }
                for value
                in self.replacements
            ],
        }

        path.write_text(
            json.dumps(
                data,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(
        cls,
        path: Path,
    ) -> AndroidBootstrapBootImageHandoffManifest:
        if not path.is_file():
            raise AndroidBootstrapHandoffError(
                f"Bootstrap Boot Image handoff not found: {path}"
            )

        raw = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        schema_version = raw.get(
            "schema_version"
        )

        if (
            schema_version
            != BOOTSTRAP_BOOT_IMAGE_HANDOFF_SCHEMA_VERSION
        ):
            raise AndroidBootstrapHandoffError(
                "unsupported Bootstrap Boot Image handoff schema: "
                f"{schema_version!r}"
            )

        parsing_snapshot = raw[
            "parsing_snapshot"
        ]

        replacements = tuple(
            AndroidBootstrapBootImageReplacement(
                container_kind=(
                    value[
                        "container_kind"
                    ]
                ),
                semantic_name=(
                    value[
                        "semantic_name"
                    ]
                ),
                replacement_path=Path(
                    value[
                        "replacement"
                    ][
                        "path"
                    ]
                ),
                replacement_size_bytes=(
                    value[
                        "replacement"
                    ][
                        "size_bytes"
                    ]
                ),
                replacement_sha256=(
                    value[
                        "replacement"
                    ][
                        "sha256"
                    ]
                ),
                original_component_path=Path(
                    value[
                        "original_component"
                    ][
                        "path"
                    ]
                ),
                original_component_size_bytes=(
                    value[
                        "original_component"
                    ][
                        "size_bytes"
                    ]
                ),
                original_component_sha256=(
                    value[
                        "original_component"
                    ][
                        "sha256"
                    ]
                ),
                cpio_path=Path(
                    value[
                        "cpio"
                    ][
                        "path"
                    ]
                ),
                cpio_size_bytes=(
                    value[
                        "cpio"
                    ][
                        "size_bytes"
                    ]
                ),
                cpio_sha256=(
                    value[
                        "cpio"
                    ][
                        "sha256"
                    ]
                ),
                compression=(
                    value[
                        "compression"
                    ]
                ),
                rollback_required=(
                    value[
                        "rollback_required"
                    ]
                ),
            )
            for value
            in raw[
                "replacements"
            ]
        )

        return cls(
            schema_version=(
                schema_version
            ),
            parsing_snapshot_path=Path(
                parsing_snapshot[
                    "path"
                ]
            ),
            parsing_snapshot_sha256=(
                parsing_snapshot[
                    "sha256"
                ]
            ),
            replacements=replacements,
        )


__all__ = (
    "BOOTSTRAP_BOOT_IMAGE_HANDOFF_SCHEMA_VERSION",
    "AndroidBootstrapBootImageHandoffManifest",
    "AndroidBootstrapBootImageReplacement",
    "AndroidBootstrapHandoffError",
    "sha256_file",
)
