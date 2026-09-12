from __future__ import annotations

import os
import shutil
import stat

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath

from treeforge.android.boot_image.models import (
    AndroidBootImageCpioEntryInterpretation,
)
from treeforge.android.extraction.cpio.extractor import (
    CpioEntryType,
)
from treeforge.android.bootstrap.planning import (
    AndroidBootstrapEnvironmentPlan,
    AndroidBootstrapEnvironmentPopulationEntry,
)
from treeforge.android.bootstrap.runtime_provider import (
    AndroidBootstrapRuntimeProvider,
)


class AndroidBootstrapEnvironmentRealizationDisposition(
    StrEnum
):
    """
    Physical host-workspace disposition of one exact planned CPIO entry.
    """

    MATERIALIZED = "materialized"
    METADATA_ONLY = "metadata_only"


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentRealizationEntry:
    """
    Realization outcome for one exact planned Bootstrap population entry.

    ``population_entry`` retains the exact Planning object and therefore the
    exact canonical Boot Image / Parsing CPIO identity behind the realization.
    """

    population_entry: AndroidBootstrapEnvironmentPopulationEntry
    disposition: AndroidBootstrapEnvironmentRealizationDisposition
    output_path: Path | None = None

    # SHA-256 of the bytes physically materialized into rootfs.
    content_sha256: str | None = None

    # SHA-256 of the exact canonical CPIO file bytes retained by Planning.
    # For an unsubstituted file this is equal to content_sha256.
    canonical_content_sha256: str | None = None

    # External implementation-provider provenance. These remain None when
    # canonical CPIO bytes were materialized directly.
    runtime_provider_name: str | None = None
    runtime_provider_release: str | None = None
    runtime_provider_content_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.population_entry,
            AndroidBootstrapEnvironmentPopulationEntry,
        ):
            raise TypeError(
                "population_entry must be an "
                "AndroidBootstrapEnvironmentPopulationEntry"
            )

        if not isinstance(
            self.disposition,
            AndroidBootstrapEnvironmentRealizationDisposition,
        ):
            raise TypeError(
                "disposition must be an "
                "AndroidBootstrapEnvironmentRealizationDisposition"
            )

        if (
            self.output_path is not None
            and not isinstance(
                self.output_path,
                Path,
            )
        ):
            raise TypeError(
                "output_path must be a Path or None"
            )

        if (
            self.disposition
            is AndroidBootstrapEnvironmentRealizationDisposition.MATERIALIZED
            and self.output_path is None
        ):
            raise ValueError(
                "materialized realization entry must retain output_path"
            )

        if (
            self.disposition
            is AndroidBootstrapEnvironmentRealizationDisposition.METADATA_ONLY
            and self.output_path is not None
        ):
            raise ValueError(
                "metadata-only realization entry cannot retain output_path"
            )

        for field_name in (
            "content_sha256",
            "canonical_content_sha256",
            "runtime_provider_content_sha256",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is None:
                continue

            if (
                not isinstance(
                    value,
                    str,
                )
                or len(value) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in value
                )
            ):
                raise ValueError(
                    f"{field_name} must be a lowercase SHA-256 digest or None"
                )

        provider_identity_present = (
            self.runtime_provider_name is not None
            or self.runtime_provider_release is not None
            or self.runtime_provider_content_sha256 is not None
        )

        if provider_identity_present:
            if (
                not isinstance(
                    self.runtime_provider_name,
                    str,
                )
                or not self.runtime_provider_name
            ):
                raise ValueError(
                    "provider-backed realization requires runtime_provider_name"
                )

            if (
                not isinstance(
                    self.runtime_provider_release,
                    str,
                )
                or not self.runtime_provider_release
            ):
                raise ValueError(
                    "provider-backed realization requires runtime_provider_release"
                )

            if self.runtime_provider_content_sha256 is None:
                raise ValueError(
                    "provider-backed realization requires provider SHA-256"
                )

            if (
                self.content_sha256
                != self.runtime_provider_content_sha256
            ):
                raise ValueError(
                    "provider-backed realization content SHA-256 must equal "
                    "provider content SHA-256"
                )

            if self.canonical_content_sha256 is None:
                raise ValueError(
                    "provider-backed realization must retain canonical SHA-256"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapEnvironmentRealizationResult:
    """
    First-class Bootstrap Environment Realization boundary.

    Host filesystem state is only an inspectable realization. Canonical CPIO
    metadata remains authoritative through ``plan`` and each exact
    ``population_entry``; later archive construction must not rediscover uid,
    gid, inode, device numbers, or other CPIO metadata from host stat results.
    """

    plan: AndroidBootstrapEnvironmentPlan
    rootfs: Path
    entries: tuple[
        AndroidBootstrapEnvironmentRealizationEntry,
        ...,
    ]

    def __post_init__(self) -> None:
        if not isinstance(
            self.plan,
            AndroidBootstrapEnvironmentPlan,
        ):
            raise TypeError(
                "plan must be an AndroidBootstrapEnvironmentPlan"
            )

        if not isinstance(
            self.rootfs,
            Path,
        ):
            raise TypeError(
                "rootfs must be a Path"
            )

        if not isinstance(
            self.entries,
            tuple,
        ):
            raise TypeError(
                "entries must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidBootstrapEnvironmentRealizationEntry,
            )
            for value
            in self.entries
        ):
            raise TypeError(
                "entries contain an invalid realization entry"
            )

        if self.plan.population is None:
            raise ValueError(
                "Environment Realization requires a resolved population plan"
            )

        expected = self.plan.population.entries

        if len(
            self.entries
        ) != len(
            expected
        ):
            raise ValueError(
                "Environment Realization must account for every selected "
                "population entry exactly once"
            )

        if tuple(
            id(
                value.population_entry
            )
            for value
            in self.entries
        ) != tuple(
            id(
                value
            )
            for value
            in expected
        ):
            raise ValueError(
                "Environment Realization must preserve exact population "
                "order and object identity"
            )

    @property
    def selected_count(self) -> int:
        return len(
            self.entries
        )

    @property
    def materialized_count(self) -> int:
        return sum(
            1
            for value
            in self.entries
            if value.disposition
            is AndroidBootstrapEnvironmentRealizationDisposition.MATERIALIZED
        )

    @property
    def metadata_only_count(self) -> int:
        return sum(
            1
            for value
            in self.entries
            if value.disposition
            is AndroidBootstrapEnvironmentRealizationDisposition.METADATA_ONLY
        )

    @property
    def complete(self) -> bool:
        return (
            self.metadata_only_count == 0
            and self.materialized_count
            == self.selected_count
        )


class AndroidBootstrapEnvironmentRealizationError(
    RuntimeError
):
    """
    Raised when a planned Bootstrap environment cannot be realized exactly.
    """


class AndroidBootstrapEnvironmentRealizer:
    """
    Materialize one exact Bootstrap Environment Planning population.

    This does not:
      - enlarge or reinterpret the planned population;
      - synthesize missing structural parents;
      - recreate preserved Planning entries;
      - infer ownership or metadata from the host filesystem;
      - create active host device nodes, sockets, or FIFOs;
      - construct a boot image;
      - invoke fastboot.
    """

    @staticmethod
    def _relative_path(
        entry: AndroidBootImageCpioEntryInterpretation,
    ) -> PurePosixPath:
        raw = PurePosixPath(
            entry.entry.path
        )

        if raw.is_absolute():
            raise AndroidBootstrapEnvironmentRealizationError(
                "planned CPIO path must be relative: "
                f"{entry.entry.path!r}"
            )

        if ".." in raw.parts:
            raise AndroidBootstrapEnvironmentRealizationError(
                "planned CPIO path contains parent traversal: "
                f"{entry.entry.path!r}"
            )

        parts = tuple(
            part
            for part
            in raw.parts
            if part not in {
                "",
                ".",
            }
        )

        if not parts:
            raise AndroidBootstrapEnvironmentRealizationError(
                "planned CPIO path resolves to an empty path"
            )

        return PurePosixPath(
            *parts
        )

    @staticmethod
    def _replace_rootfs(
        rootfs: Path,
    ) -> None:
        if rootfs.is_symlink():
            rootfs.unlink()
        elif rootfs.is_dir():
            shutil.rmtree(
                rootfs
            )
        elif rootfs.exists():
            rootfs.unlink()

        rootfs.mkdir(
            parents=True,
            exist_ok=False,
        )

    @staticmethod
    def _output_path(
        *,
        rootfs: Path,
        relative_path: PurePosixPath,
    ) -> Path:
        return rootfs.joinpath(
            *relative_path.parts
        )

    @staticmethod
    def _apply_mode(
        path: Path,
        mode: int,
    ) -> None:
        path.chmod(
            stat.S_IMODE(
                mode
            )
        )

    @staticmethod
    def _apply_mtime(
        path: Path,
        mtime: int,
        *,
        follow_symlinks: bool = True,
    ) -> None:
        os.utime(
            path,
            (
                mtime,
                mtime,
            ),
            follow_symlinks=follow_symlinks,
        )

    @staticmethod
    def _require_parent(
        *,
        output: Path,
        rootfs: Path,
    ) -> None:
        parent = output.parent

        if parent == rootfs:
            return

        if parent.is_symlink():
            raise AndroidBootstrapEnvironmentRealizationError(
                "planned entry would traverse a materialized symlink parent: "
                f"{output}"
            )

        if not parent.exists():
            raise AndroidBootstrapEnvironmentRealizationError(
                "planned entry has a missing structural parent: "
                f"{output}"
            )

        if not parent.is_dir():
            raise AndroidBootstrapEnvironmentRealizationError(
                "planned entry parent is not a directory: "
                f"{output}"
            )

    def realize(
        self,
        plan: AndroidBootstrapEnvironmentPlan,
        *,
        rootfs: Path,
        runtime_provider: AndroidBootstrapRuntimeProvider | None = None,
    ) -> AndroidBootstrapEnvironmentRealizationResult:
        if not isinstance(
            plan,
            AndroidBootstrapEnvironmentPlan,
        ):
            raise TypeError(
                "plan must be an AndroidBootstrapEnvironmentPlan"
            )

        if not isinstance(
            rootfs,
            Path,
        ):
            raise TypeError(
                "rootfs must be a Path"
            )

        if (
            runtime_provider is not None
            and not isinstance(
                runtime_provider,
                AndroidBootstrapRuntimeProvider,
            )
        ):
            raise TypeError(
                "runtime_provider must be an "
                "AndroidBootstrapRuntimeProvider or None"
            )

        if plan.population is None:
            raise AndroidBootstrapEnvironmentRealizationError(
                "Environment Planning did not resolve a population"
            )

        population = plan.population.entries

        relative_by_population_id = {
            id(
                value
            ): self._relative_path(
                value.entry
            )
            for value
            in population
        }

        selected_directory_paths = {
            relative_by_population_id[
                id(
                    value
                )
            ]
            for value
            in population
            if value.entry.entry.entry_type
            is CpioEntryType.DIRECTORY
        }

        # Planning must already contain every structural directory required
        # by selected descendants. Root itself is implicit.
        for value in population:
            relative = relative_by_population_id[
                id(
                    value
                )
            ]

            parent = relative.parent

            while parent != PurePosixPath(
                "."
            ):
                if parent not in selected_directory_paths:
                    raise AndroidBootstrapEnvironmentRealizationError(
                        "planned population is missing structural parent "
                        f"{parent} required by {relative}"
                    )

                parent = parent.parent

        self._replace_rootfs(
            rootfs
        )

        # ----------------------------------------------------
        # Pass 1: create selected directories only.
        #
        # Parents are created before children by depth, but final result
        # accounting remains in exact canonical population order.
        # ----------------------------------------------------

        directory_values = tuple(
            value
            for value
            in population
            if value.entry.entry.entry_type
            is CpioEntryType.DIRECTORY
        )

        directory_values = tuple(
            sorted(
                directory_values,
                key=lambda value: (
                    len(
                        relative_by_population_id[
                            id(
                                value
                            )
                        ].parts
                    ),
                    value.entry.index,
                ),
            )
        )

        for value in directory_values:
            relative = relative_by_population_id[
                id(
                    value
                )
            ]

            output = self._output_path(
                rootfs=rootfs,
                relative_path=relative,
            )

            self._require_parent(
                output=output,
                rootfs=rootfs,
            )

            output.mkdir(
                exist_ok=False,
            )

            self._apply_mode(
                output,
                value.entry.entry.mode,
            )

        # ----------------------------------------------------
        # Pass 2: materialize files and symlinks in canonical
        # population order. Host-active special objects remain
        # metadata-only and are explicitly represented below.
        # ----------------------------------------------------

        realized_by_population_id = {}

        for value in population:
            entry = value.entry.entry
            entry_type = entry.entry_type

            relative = relative_by_population_id[
                id(
                    value
                )
            ]

            output = self._output_path(
                rootfs=rootfs,
                relative_path=relative,
            )

            if entry_type is CpioEntryType.DIRECTORY:
                realized_by_population_id[
                    id(
                        value
                    )
                ] = (
                    AndroidBootstrapEnvironmentRealizationEntry(
                        population_entry=value,
                        disposition=(
                            AndroidBootstrapEnvironmentRealizationDisposition
                            .MATERIALIZED
                        ),
                        output_path=output,
                    )
                )

                continue

            if entry_type is CpioEntryType.FILE:
                self._require_parent(
                    output=output,
                    rootfs=rootfs,
                )

                if (
                    output.exists()
                    or output.is_symlink()
                ):
                    raise AndroidBootstrapEnvironmentRealizationError(
                        "planned file collides with an existing rootfs path: "
                        f"{output}"
                    )

                canonical_data = entry.data

                canonical_content_sha256 = sha256(
                    canonical_data
                ).hexdigest()

                materialized_data = canonical_data

                runtime_provider_name = None
                runtime_provider_release = None
                runtime_provider_content_sha256 = None

                canonical_android_path = (
                    PurePosixPath("/")
                    / relative
                )

                provider_file = (
                    runtime_provider.file_for_android_path(
                        canonical_android_path
                    )
                    if runtime_provider is not None
                    else None
                )

                if provider_file is not None:
                    if not provider_file.source_path.is_file():
                        raise AndroidBootstrapEnvironmentRealizationError(
                            "runtime provider file is unavailable for "
                            f"{canonical_android_path}: "
                            f"{provider_file.source_path}"
                        )

                    provider_data = (
                        provider_file
                        .source_path
                        .read_bytes()
                    )

                    actual_provider_sha256 = sha256(
                        provider_data
                    ).hexdigest()

                    if (
                        actual_provider_sha256
                        != provider_file.content_sha256
                    ):
                        raise AndroidBootstrapEnvironmentRealizationError(
                            "runtime provider SHA-256 mismatch for "
                            f"{canonical_android_path}: expected "
                            f"{provider_file.content_sha256}, got "
                            f"{actual_provider_sha256}"
                        )

                    materialized_data = provider_data

                    runtime_provider_name = (
                        runtime_provider.name
                    )

                    runtime_provider_release = (
                        runtime_provider.release
                    )

                    runtime_provider_content_sha256 = (
                        actual_provider_sha256
                    )

                materialized_content_sha256 = sha256(
                    materialized_data
                ).hexdigest()

                output.write_bytes(
                    materialized_data
                )

                # Canonical CPIO metadata remains authoritative even when
                # implementation bytes come from an external provider.
                self._apply_mode(
                    output,
                    entry.mode,
                )

                self._apply_mtime(
                    output,
                    entry.mtime,
                )

                realized_by_population_id[
                    id(
                        value
                    )
                ] = (
                    AndroidBootstrapEnvironmentRealizationEntry(
                        population_entry=value,
                        disposition=(
                            AndroidBootstrapEnvironmentRealizationDisposition
                            .MATERIALIZED
                        ),
                        output_path=output,
                        content_sha256=(
                            materialized_content_sha256
                        ),
                        canonical_content_sha256=(
                            canonical_content_sha256
                        ),
                        runtime_provider_name=(
                            runtime_provider_name
                        ),
                        runtime_provider_release=(
                            runtime_provider_release
                        ),
                        runtime_provider_content_sha256=(
                            runtime_provider_content_sha256
                        ),
                    )
                )

                continue

            if entry_type is CpioEntryType.SYMLINK:
                self._require_parent(
                    output=output,
                    rootfs=rootfs,
                )

                if (
                    output.exists()
                    or output.is_symlink()
                ):
                    raise AndroidBootstrapEnvironmentRealizationError(
                        "planned symlink collides with an existing rootfs "
                        f"path: {output}"
                    )

                target = entry.symlink_target

                if target is None:
                    raise AndroidBootstrapEnvironmentRealizationError(
                        "planned symlink has no canonical target: "
                        f"{entry.path}"
                    )

                output.symlink_to(
                    target
                )

                try:
                    self._apply_mtime(
                        output,
                        entry.mtime,
                        follow_symlinks=False,
                    )
                except (
                    NotImplementedError,
                    OSError,
                ):
                    # Canonical CPIO mtime remains retained by the source
                    # record even where the host cannot set symlink mtime.
                    pass

                realized_by_population_id[
                    id(
                        value
                    )
                ] = (
                    AndroidBootstrapEnvironmentRealizationEntry(
                        population_entry=value,
                        disposition=(
                            AndroidBootstrapEnvironmentRealizationDisposition
                            .MATERIALIZED
                        ),
                        output_path=output,
                    )
                )

                continue

            if entry_type in {
                CpioEntryType.FIFO,
                CpioEntryType.CHARACTER_DEVICE,
                CpioEntryType.BLOCK_DEVICE,
                CpioEntryType.SOCKET,
                CpioEntryType.UNKNOWN,
            }:
                realized_by_population_id[
                    id(
                        value
                    )
                ] = (
                    AndroidBootstrapEnvironmentRealizationEntry(
                        population_entry=value,
                        disposition=(
                            AndroidBootstrapEnvironmentRealizationDisposition
                            .METADATA_ONLY
                        ),
                    )
                )

                continue

            raise AndroidBootstrapEnvironmentRealizationError(
                "unsupported canonical CPIO entry type: "
                f"{entry_type}"
            )

        # Directory mtimes must be applied after their children have been
        # created, otherwise host directory mutation would overwrite them.
        for value in reversed(
            directory_values
        ):
            relative = relative_by_population_id[
                id(
                    value
                )
            ]

            output = self._output_path(
                rootfs=rootfs,
                relative_path=relative,
            )

            self._apply_mtime(
                output,
                value.entry.entry.mtime,
            )

        entries = tuple(
            realized_by_population_id[
                id(
                    value
                )
            ]
            for value
            in population
        )

        return AndroidBootstrapEnvironmentRealizationResult(
            plan=plan,
            rootfs=rootfs,
            entries=entries,
        )


__all__ = (
    "AndroidBootstrapEnvironmentRealizationDisposition",
    "AndroidBootstrapEnvironmentRealizationEntry",
    "AndroidBootstrapEnvironmentRealizationError",
    "AndroidBootstrapEnvironmentRealizationResult",
    "AndroidBootstrapEnvironmentRealizer",
)
