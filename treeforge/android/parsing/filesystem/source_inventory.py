from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath

from treeforge.android.extraction.model import (
    ExtractedArtifact,
)
from treeforge.android.filesystem.filesystem import (
    Filesystem,
)
from treeforge.android.partition.inventory import (
    InventoryPartition,
)
from treeforge.android.parsing.init import (
    is_android_init_source,
)
from treeforge.android.parsing.shell_script.recognizer import (
    is_android_shell_script,
)
from treeforge.android.properties import (
    AndroidPropertySourceKind,
    classify_android_property_source,
)


class AndroidModelSourceKind(
    StrEnum
):
    """
    Supported Android model source categories.

    Source kinds describe parser families, not semantic subtypes within
    those formats.
    """

    INIT = "init"
    FSTAB = "fstab"
    UEVENTD = "ueventd"
    VINTF = "vintf"
    PROPERTY = "property"
    SELINUX = "selinux"
    LINKER_CONFIGURATION = (
        "linker_configuration"
    )
    NATIVE_LIBRARY_CONFIGURATION = (
        "native_library_configuration"
    )
    KERNEL_MODULE_CONFIGURATION = (
        "kernel_module_configuration"
    )
    ART_RUNTIME = "art_runtime"
    DEX = "dex"
    CLASSPATH_CONFIGURATION = (
        "classpath_configuration"
    )
    ACONFIG_CONFIGURATION = (
        "aconfig_configuration"
    )
    INPUT_KEY_LAYOUT = (
        "input_key_layout"
    )
    INPUT_KEY_CHARACTER_MAP = (
        "input_key_character_map"
    )
    INPUT_DEVICE_CONFIGURATION = (
        "input_device_configuration"
    )
    FONT = "font"
    JAVA_ARCHIVE = "java_archive"
    SHELL_SCRIPT = "shell_script"
    CERTIFICATE = "certificate"
    OTA_CERTIFICATE_ARCHIVE = (
        "ota_certificate_archive"
    )
    AVB_PUBLIC_KEY = "avb_public_key"
    CGROUP_CONFIGURATION = (
        "cgroup_configuration"
    )
    MKE2FS_CONFIGURATION = (
        "mke2fs_configuration"
    )
    RECOVERY_WIPE_CONFIGURATION = (
        "recovery_wipe_configuration"
    )
    BLUEPRINT = "blueprint"
    SENSOR_HAL_CONFIGURATION = (
        "sensor_hal_configuration"
    )
    SENSOR_REGISTRY_CONFIGURATION = (
        "sensor_registry_configuration"
    )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidParserFilesystemSource:
    """
    Associate one parser-ready filesystem root with exact canonical
    Extraction provenance.

    Parser sources are not required to represent partitions. A source may
    originate from a partition filesystem, a boot-family ramdisk, or another
    canonical extracted filesystem introduced later.

    ``source_name`` is the stable parser-facing identity of the physical
    source root.

    ``artifact`` is the exact canonical Extraction artifact whose directory
    is exposed through ``filesystem``.

    ``partition`` is retained only when the source is backed by an exact
    InventoryPartition.
    """

    source_name: str
    artifact: ExtractedArtifact
    filesystem: Filesystem

    views: tuple[
        AndroidFilesystemView,
        ...,
    ]

    partition: InventoryPartition | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_name,
            str,
        ):
            raise TypeError(
                "source_name must be a string"
            )

        if not self.source_name.strip():
            raise ValueError(
                "source_name must not be empty"
            )

        if not isinstance(
            self.artifact,
            ExtractedArtifact,
        ):
            raise TypeError(
                "artifact must be an ExtractedArtifact"
            )

        if not isinstance(
            self.filesystem,
            Filesystem,
        ):
            raise TypeError(
                "filesystem must be a Filesystem"
            )

        if self.filesystem.root != self.artifact.path:
            raise ValueError(
                "filesystem root must match the exact "
                "canonical Extraction artifact path"
            )

        if (
            self.partition is not None
            and not isinstance(
                self.partition,
                InventoryPartition,
            )
        ):
            raise TypeError(
                "partition must be an InventoryPartition "
                "or None"
            )

        if not isinstance(
            self.views,
            tuple,
        ):
            raise TypeError(
                "views must be a tuple"
            )

        if not self.views:
            raise ValueError(
                "views must not be empty"
            )

        if not all(
            isinstance(
                view,
                AndroidFilesystemView,
            )
            for view in self.views
        ):
            raise TypeError(
                "views must contain only "
                "AndroidFilesystemView instances"
            )

        view_prefixes = tuple(
            view.android_prefix
            for view in self.views
        )

        if len(
            view_prefixes
        ) != len(
            set(
                view_prefixes
            )
        ):
            raise ValueError(
                "filesystem view Android prefixes "
                "must be unique"
            )

        for view in self.views:
            try:
                view.filesystem.root.relative_to(
                    self.filesystem.root
                )
            except ValueError as error:
                raise ValueError(
                    "filesystem view root must belong "
                    "to the canonical parser filesystem"
                ) from error

    @property
    def partition_name(
        self,
    ) -> str | None:
        """
        Return the canonical partition name when this source is
        partition-backed.
        """

        if self.partition is None:
            return None

        return self.partition.base_name


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidPartitionFilesystem(
    AndroidParserFilesystemSource
):
    """
    Parser-ready source backed by one exact InventoryPartition.

    This specialization preserves the existing partition-facing application
    contract while Parsing operates on the generalized
    AndroidParserFilesystemSource abstraction.
    """

    partition: InventoryPartition

    def __post_init__(
        self,
    ) -> None:
        super(
            AndroidPartitionFilesystem,
            self,
        ).__post_init__()

        if not isinstance(
            self.partition,
            InventoryPartition,
        ):
            raise TypeError(
                "partition must be an InventoryPartition"
            )

        if (
            self.source_name
            != self.partition.base_name
        ):
            raise ValueError(
                "partition filesystem source_name must "
                "match the canonical partition base name"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidFilesystemView:
    """
    Expose one logical Android namespace view into a physical filesystem.

    ``filesystem`` is rooted at the exact host directory from which parser
    source discovery begins.

    ``android_prefix`` identifies where that filesystem root appears in the
    Android-visible namespace.

    Views never replace or weaken the canonical physical filesystem retained
    by AndroidPartitionFilesystem. They only describe parser-visible namespace
    projections into that filesystem.
    """

    filesystem: Filesystem
    android_prefix: PurePosixPath

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.filesystem,
            Filesystem,
        ):
            raise TypeError(
                "filesystem must be a Filesystem"
            )

        if not isinstance(
            self.android_prefix,
            PurePosixPath,
        ):
            raise TypeError(
                "android_prefix must be a PurePosixPath"
            )

        if not self.android_prefix.is_absolute():
            raise ValueError(
                "android_prefix must be absolute"
            )

    def android_path_for(
        self,
        host_path: Path,
    ) -> PurePosixPath:
        """
        Return the Android-visible path for one host path in this view.
        """

        if not isinstance(
            host_path,
            Path,
        ):
            raise TypeError(
                "host_path must be a Path"
            )

        relative_path = host_path.relative_to(
            self.filesystem.root
        )

        if self.android_prefix == PurePosixPath("/"):
            return PurePosixPath(
                "/"
                + relative_path.as_posix()
            )

        return (
            self.android_prefix
            / PurePosixPath(
                relative_path.as_posix()
            )
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidModelSource:
    """
    Describe one discovered Android configuration source.

    ``android_path`` is the canonical absolute Android-visible path
    projected through the owning AndroidFilesystemView. ``host_path`` is
    the concrete extracted path consumed by existing parsers.

    Physical filesystem-root identity and Extraction provenance remain
    separately preserved by ``filesystem_source``.
    """

    kind: AndroidModelSourceKind
    filesystem_source: AndroidParserFilesystemSource
    android_path: PurePosixPath
    host_path: Path

    @property
    def source_name(
        self,
    ) -> str:
        """
        Return the canonical parser-facing source-root identity.
        """

        return self.filesystem_source.source_name

    @property
    def identity_key(
        self,
    ) -> tuple[
        AndroidModelSourceKind,
        str,
        PurePosixPath,
    ]:
        """
        Return the canonical identity of this model source.

        Source identity is owned by Parsing source inventory and consists of
        the semantic source kind, canonical parser-facing filesystem-root
        identity, and absolute Android-visible path.
        """

        return (
            self.kind,
            self.source_name,
            self.android_path,
        )

    @property
    def partition_name(
        self,
    ) -> str | None:
        """
        Return the partition name when this source is partition-backed.
        """

        return self.filesystem_source.partition_name

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.kind,
            AndroidModelSourceKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidModelSourceKind"
            )

        if not isinstance(
            self.filesystem_source,
            AndroidParserFilesystemSource,
        ):
            raise TypeError(
                "filesystem_source must be an "
                "AndroidParserFilesystemSource"
            )

        if not isinstance(
            self.android_path,
            PurePosixPath,
        ):
            raise TypeError(
                "android_path must be a "
                "PurePosixPath"
            )

        if not self.android_path.is_absolute():
            raise ValueError(
                "android_path must be absolute"
            )

        if str(
            self.android_path
        ) == "/":
            raise ValueError(
                "android_path must identify a file"
            )

        if not isinstance(
            self.host_path,
            Path,
        ):
            raise TypeError(
                "host_path must be a Path"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidModelSourceInventory:
    """
    Immutable deterministic inventory of Android model source files.
    """

    filesystems: tuple[
        AndroidParserFilesystemSource,
        ...,
    ]

    sources: tuple[
        AndroidModelSource,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.filesystems,
            tuple,
        ):
            raise TypeError(
                "filesystems must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidParserFilesystemSource,
            )
            for value in self.filesystems
        ):
            raise TypeError(
                "filesystems must contain only "
                "AndroidParserFilesystemSource "
                "instances"
            )

        source_names = tuple(
            value.source_name
            for value in self.filesystems
        )

        if len(
            source_names
        ) != len(
            set(
                source_names
            )
        ):
            raise ValueError(
                "filesystem source names must be unique"
            )

        if source_names != tuple(
            sorted(
                source_names
            )
        ):
            raise ValueError(
                "filesystems must be in canonical "
                "source-name order"
            )

        if not isinstance(
            self.sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                AndroidModelSource,
            )
            for source in self.sources
        ):
            raise TypeError(
                "sources must contain only "
                "AndroidModelSource instances"
            )

        canonical_sources = tuple(
            sorted(
                self.sources,
                key=self._source_sort_key,
            )
        )

        if self.sources != canonical_sources:
            raise ValueError(
                "sources must be in canonical order"
            )

        source_identities = tuple(
            source.identity_key
            for source in self.sources
        )

        if len(
            source_identities
        ) != len(
            set(
                source_identities
            )
        ):
            raise ValueError(
                "kind/source-root/Android-path "
                "identities must be unique"
            )

        known_source_names = set(
            source_names
        )

        for source in self.sources:
            if (
                source.source_name
                not in known_source_names
            ):
                raise ValueError(
                    "model source must belong to "
                    "the inventory filesystems"
                )

    @staticmethod
    def _source_sort_key(
        source: AndroidModelSource,
    ) -> tuple[
        str,
        str,
        str,
    ]:
        kind, source_name, android_path = (
            source.identity_key
        )

        return (
            kind.value,
            source_name,
            android_path.as_posix(),
        )

    @property
    def source_count(
        self,
    ) -> int:
        """
        Return the total discovered source count.
        """

        return len(
            self.sources
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        """
        Return whether no sources were discovered.
        """

        return not self.sources

    @property
    def partition_names(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Return names of partition-backed parser filesystem sources.
        """

        return tuple(
            value.partition_name
            for value in self.filesystems
            if value.partition_name is not None
        )

    @property
    def source_names(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Return every canonical parser filesystem source name.
        """

        return tuple(
            value.source_name
            for value in self.filesystems
        )

    def sources_for(
        self,
        kind: AndroidModelSourceKind,
    ) -> tuple[
        AndroidModelSource,
        ...,
    ]:
        """
        Return all sources belonging to one category.
        """

        if not isinstance(
            kind,
            AndroidModelSourceKind,
        ):
            raise TypeError(
                "kind must be an "
                "AndroidModelSourceKind"
            )

        return tuple(
            source
            for source in self.sources
            if source.kind is kind
        )

    def host_paths_for(
        self,
        kind: AndroidModelSourceKind,
    ) -> tuple[
        Path,
        ...,
    ]:
        """
        Return parser-ready host paths for one category.
        """

        return tuple(
            source.host_path
            for source in self.sources_for(
                kind
            )
        )


class AndroidModelSourceInventoryBuilder:
    """
    Discover Android configuration sources from extracted filesystems.

    This builder performs source discovery only. It does not parse files,
    build graphs, reconstruct configuration, or modify filesystem contents.
    """

    _PATTERNS: tuple[
        tuple[
            AndroidModelSourceKind,
            tuple[
                str,
                ...,
            ],
        ],
        ...,
    ] = (
        (
            AndroidModelSourceKind.INIT,
            (
                "etc/init/*.rc",
                "etc/init/**/*.rc",
                "init*.rc",
            ),
        ),
        (
            AndroidModelSourceKind.FSTAB,
            (
                "etc/fstab*",
                "fstab*",
                "**/fstab*",
                "**/*.fstab",
            ),
        ),
        (
            AndroidModelSourceKind.UEVENTD,
            (
                "ueventd*.rc",
                "etc/ueventd*.rc",
                "**/ueventd*.rc",
            ),
        ),
        (
            AndroidModelSourceKind.VINTF,
            (
                "etc/vintf/*.xml",
                "etc/vintf/**/*.xml",
                "**/etc/vintf/*.xml",
                "**/etc/vintf/**/*.xml",
            ),
        ),
        (
            AndroidModelSourceKind.LINKER_CONFIGURATION,
            (
                "**/linker.config.pb",
                "**/ld.config.txt",
            ),
        ),
        (
            AndroidModelSourceKind.NATIVE_LIBRARY_CONFIGURATION,
            (
                "**/llndk.libraries.txt",
                "**/llndk.libraries.*.txt",
                "**/public.libraries.txt",
                "**/public.libraries-google.txt",
                "**/sanitizer.libraries.txt",
                "**/vndkcorevariant.libraries.txt",
                "**/vndksp.libraries.*.txt",
                "**/vndkcore.libraries.*.txt",
                "**/vndkprivate.libraries.*.txt",
            ),
        ),
        (
            AndroidModelSourceKind.KERNEL_MODULE_CONFIGURATION,
            (
                "**/modules.dep",
                "**/modules.load",
                "**/modules.alias",
                "**/modules.softdep",
                "**/modules.blocklist",
                "**/modules.options",
                "**/modules.order",
                "**/modules.builtin",
                "**/modules.builtin.modinfo",
            ),
        ),
        (
            AndroidModelSourceKind.ART_RUNTIME,
            (
                "**/*.vdex",
                "**/*.art",
            ),
        ),
        (
            AndroidModelSourceKind.DEX,
            (
                "**/*.dex",
                "**/*.cdex",
            ),
        ),
        (
            AndroidModelSourceKind.CLASSPATH_CONFIGURATION,
            (
                "**/etc/classpaths/bootclasspath.pb",
                "**/etc/classpaths/systemserverclasspath.pb",
            ),
        ),
        (
            AndroidModelSourceKind.ACONFIG_CONFIGURATION,
            (
                "**/etc/aconfig_flags.pb",
            ),
        ),
        (
            AndroidModelSourceKind.INPUT_KEY_LAYOUT,
            (
                "**/usr/keylayout/*.kl",
                "**/usr/keylayout/**/*.kl",
            ),
        ),
        (
            AndroidModelSourceKind.INPUT_KEY_CHARACTER_MAP,
            (
                "**/usr/keychars/*.kcm",
                "**/usr/keychars/**/*.kcm",
            ),
        ),
        (
            AndroidModelSourceKind.INPUT_DEVICE_CONFIGURATION,
            (
                "**/usr/idc/*.idc",
                "**/usr/idc/**/*.idc",
            ),
        ),
        (
            AndroidModelSourceKind.FONT,
            (
                "**/*.ttf",
                "**/*.otf",
                "**/*.ttc",
            ),
        ),
        (
            AndroidModelSourceKind.JAVA_ARCHIVE,
            (
                "**/*.jar",
            ),
        ),
        (
            AndroidModelSourceKind.CERTIFICATE,
            (
                "**/etc/security/cacerts/*",
                "**/etc/security/fsverity/*.der",
                "**/*.crt",
                "**/*.cer",
                "**/*.pem",
            ),
        ),
        (
            AndroidModelSourceKind.OTA_CERTIFICATE_ARCHIVE,
            (
                "**/etc/security/otacerts.zip",
            ),
        ),
        (
            AndroidModelSourceKind.AVB_PUBLIC_KEY,
            (
                "**/*.avbpubkey",
            ),
        ),
        (
            AndroidModelSourceKind.CGROUP_CONFIGURATION,
            (
                "**/cgroups.json",
            ),
        ),
        (
            AndroidModelSourceKind.MKE2FS_CONFIGURATION,
            (
                "**/mke2fs.conf",
                "**/mke2fs.conf.*",
            ),
        ),
        (
            AndroidModelSourceKind.RECOVERY_WIPE_CONFIGURATION,
            (
                "**/recovery.wipe",
            ),
        ),
        (
            AndroidModelSourceKind.BLUEPRINT,
            (
                "**/Android.bp",
            ),
        ),
        (
            AndroidModelSourceKind.SENSOR_HAL_CONFIGURATION,
            (
                "**/etc/sensors/hals.conf",
            ),
        ),
        (
            AndroidModelSourceKind.SENSOR_REGISTRY_CONFIGURATION,
            (
                "**/etc/sensors/registry/*.reg",
                "**/etc/sensors/registry/**/*.reg",
            ),
        ),
        (
            AndroidModelSourceKind.SELINUX,
            (
                "*file_contexts",
                "*property_contexts",
                "*service_contexts",
                "*hwservice_contexts",
                "*vndservice_contexts",
                "*seapp_contexts",
                "*keystore2_key_contexts",
                "etc/selinux/*",
                "etc/selinux/**/*",
                "*.cil",
                "*sepolicy*",
            ),
        ),
    )

    def build(
        self,
        filesystems: tuple[
            AndroidParserFilesystemSource,
            ...,
        ],
    ) -> AndroidModelSourceInventory:
        """
        Discover sources and build one immutable inventory.
        """

        if not isinstance(
            filesystems,
            tuple,
        ):
            raise TypeError(
                "filesystems must be a tuple"
            )

        if not all(
            isinstance(
                value,
                AndroidParserFilesystemSource,
            )
            for value in filesystems
        ):
            raise TypeError(
                "filesystems must contain only "
                "AndroidParserFilesystemSource "
                "instances"
            )

        canonical_filesystems = tuple(
            sorted(
                filesystems,
                key=lambda value: (
                    value.source_name
                ),
            )
        )

        sources: list[
            AndroidModelSource
        ] = []

        seen: set[
            tuple[
                AndroidModelSourceKind,
                str,
                PurePosixPath,
            ]
        ] = set()

        for filesystem_source in (
            canonical_filesystems
        ):
            for view in filesystem_source.views:
                for kind, patterns in self._PATTERNS:
                    for pattern in patterns:
                        matches = sorted(
                            view.filesystem.glob(
                                pattern
                            ),
                            key=lambda path: (
                                path.as_posix()
                            ),
                        )

                        for host_path in matches:
                            if not host_path.is_file():
                                continue

                            android_path = (
                                view.android_path_for(
                                    host_path
                                )
                            )

                            source_identity = (
                                kind,
                                filesystem_source
                                .source_name,
                                android_path,
                            )

                            if source_identity in seen:
                                continue

                            seen.add(
                                source_identity
                            )

                            sources.append(
                                AndroidModelSource(
                                    kind=kind,
                                    filesystem_source=(
                                        filesystem_source
                                    ),
                                    android_path=(
                                        android_path
                                    ),
                                    host_path=host_path,
                                )
                            )

                init_candidates = sorted(
                    view.filesystem.walk(),
                    key=lambda path: (
                        path.as_posix()
                    ),
                )

                for host_path in init_candidates:
                    if not host_path.is_file():
                        continue

                    # Android INIT sources are conventionally exposed either
                    # with the .rc source extension or with the extensionless
                    # _rc source suffix. Keep this boundary cheap so binary
                    # filesystem contents are not passed through the INIT
                    # lexer. The intrinsic recognizer remains authoritative
                    # for actual Android INIT syntax.
                    if not (
                        host_path.suffix.lower() == ".rc"
                        or host_path.name.lower().endswith("_rc")
                    ):
                        continue

                    if not is_android_init_source(
                        host_path
                    ):
                        continue

                    android_path = (
                        view.android_path_for(
                            host_path
                        )
                    )

                    source_identity = (
                        AndroidModelSourceKind.INIT,
                        filesystem_source.source_name,
                        android_path,
                    )

                    if source_identity in seen:
                        continue

                    # Explicit source-domain discovery outranks the broad
                    # intrinsic INIT recognizer. Some Android configuration
                    # languages share lexical top-level forms such as
                    # ``import``; a source already canonically classified as
                    # UEVENTD must therefore not also enter the INIT domain.
                    #
                    # This is identity-based rather than filename-based:
                    # Parsing relies on its own earlier canonical source
                    # classification instead of teaching INIT recognition
                    # about another configuration language.
                    ueventd_identity = (
                        AndroidModelSourceKind.UEVENTD,
                        filesystem_source.source_name,
                        android_path,
                    )

                    if ueventd_identity in seen:
                        continue

                    seen.add(
                        source_identity
                    )

                    sources.append(
                        AndroidModelSource(
                            kind=(
                                AndroidModelSourceKind.INIT
                            ),
                            filesystem_source=(
                                filesystem_source
                            ),
                            android_path=android_path,
                            host_path=host_path,
                        )
                    )

                shell_candidates = sorted(
                    view.filesystem.walk(),
                    key=lambda path: (
                        path.as_posix()
                    ),
                )

                for host_path in shell_candidates:
                    if not host_path.is_file():
                        continue

                    if not is_android_shell_script(
                        host_path
                    ):
                        continue

                    android_path = (
                        view.android_path_for(
                            host_path
                        )
                    )

                    source_identity = (
                        AndroidModelSourceKind.SHELL_SCRIPT,
                        filesystem_source.source_name,
                        android_path,
                    )

                    if source_identity in seen:
                        continue

                    seen.add(
                        source_identity
                    )

                    sources.append(
                        AndroidModelSource(
                            kind=(
                                AndroidModelSourceKind
                                .SHELL_SCRIPT
                            ),
                            filesystem_source=(
                                filesystem_source
                            ),
                            android_path=android_path,
                            host_path=host_path,
                        )
                    )

                property_matches = sorted(
                    view.filesystem.walk(),
                    key=lambda path: (
                        path.as_posix()
                    ),
                )

                for host_path in property_matches:
                    if not host_path.is_file():
                        continue

                    android_path = (
                        view.android_path_for(
                            host_path
                        )
                    )

                    property_kind = (
                        classify_android_property_source(
                            android_path.as_posix()
                        )
                    )

                    if property_kind is None:
                        continue

                    kind = (
                        AndroidModelSourceKind.PROPERTY
                    )

                    source_identity = (
                        kind,
                        filesystem_source
                        .source_name,
                        android_path,
                    )

                    if source_identity in seen:
                        continue

                    seen.add(
                        source_identity
                    )

                    sources.append(
                        AndroidModelSource(
                            kind=kind,
                            filesystem_source=(
                                filesystem_source
                            ),
                            android_path=(
                                android_path
                            ),
                            host_path=host_path,
                        )
                    )

        canonical_sources = tuple(
            sorted(
                sources,
                key=(
                    AndroidModelSourceInventory
                    ._source_sort_key
                ),
            )
        )

        return AndroidModelSourceInventory(
            filesystems=canonical_filesystems,
            sources=canonical_sources,
        )