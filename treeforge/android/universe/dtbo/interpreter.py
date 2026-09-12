from __future__ import annotations

from treeforge.android.parsing.dtb import (
    AndroidParsedDtboEntry,
)

from treeforge.android.universe.dtbo.requirement import (
    AndroidUniverseDtboRequirement,
)
from treeforge.android.universe.dtbo.semantic import (
    AndroidUniverseFdtSemanticInterpreter,
)
from treeforge.android.universe.dtbo.reconciliation import (
    AndroidUniverseFdtReconciler,
)


class AndroidUniverseDtboInterpreter:
    """
    Promote canonical Parsing-stage DTBO observations into Universe and
    interpret generic intrinsic FDT semantics.

    No DTBO container or FDT bytes are reopened or reparsed here.
    """

    def __init__(
        self,
        semantic_interpreter: (
            AndroidUniverseFdtSemanticInterpreter
            | None
        ) = None,
        reconciler: (
            AndroidUniverseFdtReconciler
            | None
        ) = None,
    ) -> None:
        self.semantic_interpreter = (
            semantic_interpreter
            if semantic_interpreter is not None
            else AndroidUniverseFdtSemanticInterpreter()
        )

        self.reconciler = (
            reconciler
            if reconciler is not None
            else AndroidUniverseFdtReconciler()
        )

    def interpret(
        self,
        parsing: tuple[
            AndroidParsedDtboEntry,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseDtboRequirement,
        ...,
    ]:
        if not isinstance(
            parsing,
            tuple,
        ):
            raise TypeError(
                "parsing must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidParsedDtboEntry,
            )
            for item in parsing
        ):
            raise TypeError(
                "parsing must contain only "
                "AndroidParsedDtboEntry entries"
            )

        requirements = []

        for item in parsing:
            property_observations = (
                self.semantic_interpreter.interpret_tree(
                    item.fdt.root
                )
            )

            requirements.append(
                AndroidUniverseDtboRequirement(
                    source=item,
                    property_observations=(
                        property_observations
                    ),
                    semantics=(
                        self.reconciler.reconcile(
                            overlay=item.overlay,
                            observations=(
                                property_observations
                            ),
                        )
                    ),
                )
            )

        return tuple(requirements)
