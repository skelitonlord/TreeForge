from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidSelinuxSource,
)
from treeforge.android.parsing.selinux import (
    AndroidSelinuxSourceKind,
)
from treeforge.android.universe.selinux.cil import (
    interpret_cil_form,
)
from treeforge.android.universe.selinux.context import (
    AndroidUniverseSelinuxContextKind,
    AndroidUniverseSelinuxContextRequirement,
    AndroidUniverseSelinuxSeappRequirement,
)
from treeforge.android.universe.selinux.mac_permissions import (
    AndroidUniverseSelinuxMacPermissionsRequirement,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)


class AndroidUniverseSelinuxInterpreter:
    """
    Promote canonical SELinux Parsing output into Device Universe
    requirements.

    Parsing identity is retained exactly. This interpreter never rereads,
    reparses, or reconstructs policy source files.

    Context-family classification and CIL semantic-family interpretation are
    Universe responsibilities. Cross-source policy reconciliation remains a
    separate Universe concern.
    """

    _CONTEXT_KINDS = {
        AndroidSelinuxSourceKind.FILE_CONTEXTS: (
            AndroidUniverseSelinuxContextKind.FILE
        ),
        AndroidSelinuxSourceKind.PROPERTY_CONTEXTS: (
            AndroidUniverseSelinuxContextKind.PROPERTY
        ),
        AndroidSelinuxSourceKind.SERVICE_CONTEXTS: (
            AndroidUniverseSelinuxContextKind.SERVICE
        ),
        AndroidSelinuxSourceKind.HWSERVICE_CONTEXTS: (
            AndroidUniverseSelinuxContextKind.HWSERVICE
        ),
        AndroidSelinuxSourceKind.VNDSERVICE_CONTEXTS: (
            AndroidUniverseSelinuxContextKind.VNDSERVICE
        ),
        AndroidSelinuxSourceKind.KEYSTORE2_KEY_CONTEXTS: (
            AndroidUniverseSelinuxContextKind.KEYSTORE2_KEY
        ),
    }

    def interpret(
        self,
        sources: tuple[
            ParsedAndroidSelinuxSource,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseSelinuxSourceRequirement,
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
                ParsedAndroidSelinuxSource,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedAndroidSelinuxSource instances"
            )

        return tuple(
            self._interpret_source(
                source
            )
            for source in sources
        )

    def _interpret_source(
        self,
        source: ParsedAndroidSelinuxSource,
    ) -> AndroidUniverseSelinuxSourceRequirement:
        parsed = source.parsed

        context_kind = (
            self._CONTEXT_KINDS.get(
                parsed.kind
            )
        )

        context_requirements = ()

        if context_kind is not None:
            context_requirements = tuple(
                AndroidUniverseSelinuxContextRequirement(
                    kind=context_kind,
                    declaration=declaration,
                )
                for declaration
                in parsed.context_declarations
            )

        seapp_requirements = ()

        if (
            parsed.kind
            is AndroidSelinuxSourceKind.SEAPP_CONTEXTS
        ):
            seapp_requirements = tuple(
                AndroidUniverseSelinuxSeappRequirement(
                    declaration=declaration
                )
                for declaration
                in parsed.seapp_declarations
            )

        mac_permissions_requirements = ()

        if (
            parsed.kind
            is AndroidSelinuxSourceKind.MAC_PERMISSIONS
        ):
            root = (
                parsed.mac_permissions_root
            )

            if root is None:
                raise ValueError(
                    "MAC_PERMISSIONS source must contain "
                    "a parsed XML root"
                )

            if root.name != "policy":
                raise ValueError(
                    "MAC_PERMISSIONS XML root must be "
                    "'policy'"
                )

            mac_permissions_requirements = tuple(
                AndroidUniverseSelinuxMacPermissionsRequirement(
                    element=element
                )
                for element in root.children
            )

        cil_requirements = ()

        if (
            parsed.kind
            is AndroidSelinuxSourceKind.CIL
        ):
            cil_requirements = tuple(
                interpret_cil_form(
                    form
                )
                for form
                in parsed.cil_forms
            )

        return AndroidUniverseSelinuxSourceRequirement(
            source=source,
            context_requirements=(
                context_requirements
            ),
            seapp_requirements=(
                seapp_requirements
            ),
            mac_permissions_requirements=(
                mac_permissions_requirements
            ),
            cil_requirements=(
                cil_requirements
            ),
        )
