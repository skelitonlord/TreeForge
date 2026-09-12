from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidFstab,
)
from treeforge.android.universe.fstab.model import (
    AndroidUniverseFstabRequirement,
)
from treeforge.android.universe.fstab.semantic_interpreter import (
    AndroidUniverseFstabSemanticInterpreter,
)


class AndroidUniverseFstabInterpreter:
    """
    Interpret lexical Android fstab declarations as Universe requirements.

    Interpretation is additive and lossless: every original declaration,
    source identity, mount option, and fs_mgr flag remains preserved.
    Unknown fs_mgr vocabulary is explicitly retained.
    """

    _BOOLEAN_FLAGS = {
        "logical": "logical",
        "slotselect": "slot_select",
        "slotselect_other": "slot_select_other",
        "first_stage_mount": "first_stage_mount",
        "latemount": "late_mount",
        "wait": "wait",
        "check": "check",
        "formattable": "formattable",
        "quota": "quota",
        "fscompress": "filesystem_compression",
        "metadata_csum": "metadata_checksum",
    }

    _VALUE_FLAGS = {
        "avb": "avb",
        "avb_keys": "avb_keys",
        "avb_hashtree_digest": "avb_hashtree_digest",
        "fileencryption": "file_encryption",
        "metadata_encryption": "metadata_encryption",
        "keydirectory": "key_directory",
        "checkpoint": "checkpoint",
        "voldmanaged": "vold_managed",
        "zramsize": "zram_size",
        "zram_backingdev_size": (
            "zram_backing_device_size"
        ),
        "readahead_size_kb": "readahead_size_kb",
        "reservedsize": "reserved_size",
        "sysfs_path": "sysfs_path",
    }

    def __init__(
        self,
        *,
        semantic_interpreter: (
            AndroidUniverseFstabSemanticInterpreter
            | None
        ) = None,
    ) -> None:
        self.semantic_interpreter = (
            semantic_interpreter
            if semantic_interpreter is not None
            else AndroidUniverseFstabSemanticInterpreter()
        )

    def interpret(
        self,
        sources: tuple[
            ParsedAndroidFstab,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseFstabRequirement,
        ...,
    ]:
        if not isinstance(
            sources,
            tuple,
        ):
            raise TypeError(
                "sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                ParsedAndroidFstab,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only ParsedAndroidFstab"
            )

        requirements = []

        for source in sources:
            for declaration in source.declarations:
                requirements.append(
                    self._interpret_declaration(
                        source=source,
                        declaration=declaration,
                    )
                )

        return tuple(
            requirements
        )

    def _interpret_declaration(
        self,
        *,
        source,
        declaration,
    ) -> AndroidUniverseFstabRequirement:
        values = {}
        unknown = []

        for flag in declaration.fs_mgr_flags:
            boolean_field = (
                self._BOOLEAN_FLAGS.get(
                    flag
                )
            )

            if boolean_field is not None:
                values[
                    boolean_field
                ] = True
                continue

            key, separator, value = (
                flag.partition("=")
            )

            if separator:
                value_field = (
                    self._VALUE_FLAGS.get(
                        key
                    )
                )

                if value_field is not None:
                    values[
                        value_field
                    ] = value
                    continue

            unknown.append(
                flag
            )

        return AndroidUniverseFstabRequirement(
            source_path=source.source_path,
            android_path=source.android_path,
            source_name=(
                source.filesystem_source.source_name
            ),
            declaration=declaration,
            device=declaration.device,
            mount_point=declaration.mount_point,
            filesystem_type=declaration.fs_type,
            mount_options=declaration.mount_options,
            fs_mgr_flags=declaration.fs_mgr_flags,
            device_expression=(
                self.semantic_interpreter.interpret_device(
                    declaration.device
                )
            ),
            interpreted_mount_options=(
                self.semantic_interpreter.interpret_mount_options(
                    declaration.mount_options
                )
            ),
            unknown_fs_mgr_flags=tuple(
                unknown
            ),
            **values,
        )