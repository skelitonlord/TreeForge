from __future__ import annotations

from treeforge.android.parsing.linker import (
    ParsedAndroidLinkerConfiguration,
    ParsedAndroidLinkerProtobufConfiguration,
    ParsedAndroidNativeLibraryConfiguration,
)
from treeforge.android.universe.linker.reconciler import (
    AndroidUniverseLinkerNativeLibraryReconciler,
    AndroidUniverseLinkerProtobufReconciler,
    AndroidUniverseLinkerTextConfigurationReconciler,
    AndroidUniverseLinkerRuntimePolicyReconciler,
)
from treeforge.android.universe.linker.requirement import (
    AndroidUniverseLinkerRequirement,
)


class AndroidUniverseLinkerInterpreter:
    """
    Promote canonical linker-policy Parsing into Android Device Universe.

    Intra-Linker ld.config.txt namespace semantics are reconciled here.
    Protobuf policy, native-library policy, and ELF relationships remain
    separate later semantic slices.
    """

    def __init__(
        self,
        text_configuration_reconciler: (
            AndroidUniverseLinkerTextConfigurationReconciler
            | None
        ) = None,
        protobuf_reconciler: (
            AndroidUniverseLinkerProtobufReconciler
            | None
        ) = None,
        native_library_reconciler: (
            AndroidUniverseLinkerNativeLibraryReconciler
            | None
        ) = None,
        runtime_policy_reconciler: (
            AndroidUniverseLinkerRuntimePolicyReconciler
            | None
        ) = None,
    ) -> None:
        self.text_configuration_reconciler = (
            text_configuration_reconciler
            if text_configuration_reconciler is not None
            else AndroidUniverseLinkerTextConfigurationReconciler()
        )


        self.protobuf_reconciler = (
            protobuf_reconciler
            if protobuf_reconciler is not None
            else AndroidUniverseLinkerProtobufReconciler()
        )


        self.native_library_reconciler = (
            native_library_reconciler
            if native_library_reconciler is not None
            else AndroidUniverseLinkerNativeLibraryReconciler()
        )

        self.runtime_policy_reconciler = (
            runtime_policy_reconciler
            if runtime_policy_reconciler is not None
            else AndroidUniverseLinkerRuntimePolicyReconciler()
        )

    def interpret(
        self,
        configurations: tuple[
            ParsedAndroidLinkerConfiguration,
            ...,
        ],
        protobuf_configurations: tuple[
            ParsedAndroidLinkerProtobufConfiguration,
            ...,
        ],
        native_library_configurations: tuple[
            ParsedAndroidNativeLibraryConfiguration,
            ...,
        ],
    ) -> AndroidUniverseLinkerRequirement:
        text_configuration_semantics = (
            self.text_configuration_reconciler
            .reconcile_all(
                configurations
            )
        )


        protobuf_configuration_semantics = (
            self.protobuf_reconciler
            .reconcile_all(
                protobuf_configurations
            )
        )


        native_library_configuration_semantics = (
            self.native_library_reconciler
            .reconcile_all(
                native_library_configurations
            )
        )

        runtime_policies = (
            self.runtime_policy_reconciler
            .reconcile(
                text_configuration_semantics,
                protobuf_configuration_semantics,
                native_library_configuration_semantics,
            )
        )

        return AndroidUniverseLinkerRequirement(
            configurations=configurations,
            protobuf_configurations=protobuf_configurations,
            native_library_configurations=(
                native_library_configurations
            ),
            text_configuration_semantics=(
                text_configuration_semantics
            ),
            protobuf_configuration_semantics=(
                protobuf_configuration_semantics
            ),
            native_library_configuration_semantics=(
                native_library_configuration_semantics
            ),
            runtime_policies=(
                runtime_policies
            ),
        )
