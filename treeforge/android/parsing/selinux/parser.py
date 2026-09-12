from __future__ import annotations

from pathlib import Path

from treeforge.android.parsing.selinux.cil import (
    AndroidSelinuxCilParser,
)
from treeforge.android.parsing.selinux.contexts import (
    parse_context_lines,
    parse_seapp_lines,
)
from treeforge.android.parsing.selinux.mac_permissions import (
    AndroidSelinuxMacPermissionsParser,
)
from treeforge.android.parsing.selinux.model import (
    AndroidSelinuxSourceKind,
    AndroidSelinuxTextLine,
    ParsedAndroidSelinuxFile,
)


class AndroidSelinuxParser:
    """
    Parse one SELinux source according to its intrinsic file format.

    No policy reconciliation, type resolution, labeling conclusions, or
    cross-source Android semantics are performed here.
    """

    def __init__(
        self,
        *,
        cil_parser: (
            AndroidSelinuxCilParser
            | None
        ) = None,
        mac_permissions_parser: (
            AndroidSelinuxMacPermissionsParser
            | None
        ) = None,
    ) -> None:
        self.cil_parser = (
            cil_parser
            if cil_parser is not None
            else AndroidSelinuxCilParser()
        )

        self.mac_permissions_parser = (
            mac_permissions_parser
            if mac_permissions_parser
            is not None
            else AndroidSelinuxMacPermissionsParser()
        )

    def parse(
        self,
        source_path: Path,
    ) -> ParsedAndroidSelinuxFile:
        if not isinstance(
            source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not source_path.exists():
            raise FileNotFoundError(
                source_path
            )

        if not source_path.is_file():
            raise IsADirectoryError(
                source_path
            )

        raw_bytes = (
            source_path.read_bytes()
        )

        kind = self.classify(
            source_path
        )

        if (
            kind
            in {
                AndroidSelinuxSourceKind.COMPILED_POLICY,
                AndroidSelinuxSourceKind.OPAQUE,
            }
        ):
            return ParsedAndroidSelinuxFile(
                source_path=source_path,
                kind=kind,
                raw_bytes=raw_bytes,
            )

        raw = raw_bytes.decode(
            "utf-8",
            errors="replace",
        )

        if (
            kind
            is AndroidSelinuxSourceKind.CIL
        ):
            return ParsedAndroidSelinuxFile(
                source_path=source_path,
                kind=kind,
                raw_bytes=raw_bytes,
                raw=raw,
                cil_forms=(
                    self.cil_parser.parse(
                        raw,
                        source_path=source_path,
                    )
                ),
            )

        if (
            kind
            is AndroidSelinuxSourceKind.MAC_PERMISSIONS
        ):
            (
                raw,
                root,
            ) = self.mac_permissions_parser.parse(
                raw_bytes,
                source_path=source_path,
            )

            return ParsedAndroidSelinuxFile(
                source_path=source_path,
                kind=kind,
                raw_bytes=raw_bytes,
                raw=raw,
                mac_permissions_root=root,
            )

        if (
            kind
            is AndroidSelinuxSourceKind.SEAPP_CONTEXTS
        ):
            (
                declarations,
                unparsed,
            ) = parse_seapp_lines(
                raw,
                source_path=source_path,
            )

            return ParsedAndroidSelinuxFile(
                source_path=source_path,
                kind=kind,
                raw_bytes=raw_bytes,
                raw=raw,
                seapp_declarations=declarations,
                unparsed_lines=unparsed,
            )

        if kind in {
            AndroidSelinuxSourceKind.FILE_CONTEXTS,
            AndroidSelinuxSourceKind.PROPERTY_CONTEXTS,
            AndroidSelinuxSourceKind.SERVICE_CONTEXTS,
            AndroidSelinuxSourceKind.HWSERVICE_CONTEXTS,
            AndroidSelinuxSourceKind.VNDSERVICE_CONTEXTS,
            AndroidSelinuxSourceKind.KEYSTORE2_KEY_CONTEXTS,
        }:
            (
                declarations,
                unparsed,
            ) = parse_context_lines(
                raw,
                source_path=source_path,
                file_contexts=(
                    kind
                    is AndroidSelinuxSourceKind.FILE_CONTEXTS
                ),
            )

            return ParsedAndroidSelinuxFile(
                source_path=source_path,
                kind=kind,
                raw_bytes=raw_bytes,
                raw=raw,
                context_declarations=declarations,
                unparsed_lines=unparsed,
            )

        lines = tuple(
            AndroidSelinuxTextLine(
                value=raw_line.strip(),
                raw=raw_line,
                source_path=source_path,
                source_line=line_number,
            )
            for line_number, raw_line
            in enumerate(
                raw.splitlines(),
                start=1,
            )
            if raw_line.strip()
        )

        return ParsedAndroidSelinuxFile(
            source_path=source_path,
            kind=kind,
            raw_bytes=raw_bytes,
            raw=raw,
            text_lines=lines,
        )

    @staticmethod
    def classify(
        source_path: Path,
    ) -> AndroidSelinuxSourceKind:
        name = (
            source_path.name.lower()
        )

        if name.endswith(
            "file_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .FILE_CONTEXTS
            )

        if name.endswith(
            "property_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .PROPERTY_CONTEXTS
            )

        if name.endswith(
            "hwservice_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .HWSERVICE_CONTEXTS
            )

        if name.endswith(
            "vndservice_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .VNDSERVICE_CONTEXTS
            )

        if name.endswith(
            "service_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .SERVICE_CONTEXTS
            )

        if name.endswith(
            "seapp_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .SEAPP_CONTEXTS
            )

        if name.endswith(
            "keystore2_key_contexts"
        ):
            return (
                AndroidSelinuxSourceKind
                .KEYSTORE2_KEY_CONTEXTS
            )

        if name.endswith(
            "mac_permissions.xml"
        ):
            return (
                AndroidSelinuxSourceKind
                .MAC_PERMISSIONS
            )

        if name == "genfs_labels_version.txt":
            return (
                AndroidSelinuxSourceKind
                .GENFS_LABELS_VERSION
            )

        if name.endswith(
            ".cil"
        ):
            return (
                AndroidSelinuxSourceKind
                .CIL
            )

        if (
            "sepolicy_vers" in name
            or name.endswith(
                "_version"
            )
        ):
            return (
                AndroidSelinuxSourceKind
                .POLICY_VERSION
            )

        if (
            "sha256" in name
            or name.endswith(
                ".hash"
            )
        ):
            return (
                AndroidSelinuxSourceKind
                .POLICY_HASH
            )

        if name in {
            "sepolicy",
            "precompiled_sepolicy",
        }:
            return (
                AndroidSelinuxSourceKind
                .COMPILED_POLICY
            )

        try:
            source_path.read_text(
                encoding="utf-8"
            )
        except (
            UnicodeDecodeError,
            OSError,
        ):
            return (
                AndroidSelinuxSourceKind
                .OPAQUE
            )

        return (
            AndroidSelinuxSourceKind
            .OTHER_TEXT
        )


def read_android_selinux(
    source_path: Path,
) -> ParsedAndroidSelinuxFile:
    return AndroidSelinuxParser().parse(
        source_path
    )