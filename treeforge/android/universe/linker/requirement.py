from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.linker import (
    ParsedAndroidLinkerConfiguration,
    ParsedAndroidLinkerProtobufConfiguration,
    ParsedAndroidNativeLibraryConfiguration,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
    AndroidUniverseLinkerProtobufConfigurationSemantics,
    AndroidUniverseLinkerTextConfigurationSemantics,
    AndroidUniverseLinkerRuntimePolicy,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseLinkerRequirement:
    """
    Canonical Universe representation of Android runtime linker policy inputs.

    Parsing identities remain exact.

    ``text_configuration_semantics`` contains intra-Linker semantic
    reconstruction of ld.config.txt namespace structure.

    Protobuf policy, native-library policy reconciliation, variable/runtime
    path expansion, and ELF dependency resolution remain later Universe work.
    """

    configurations: tuple[
        ParsedAndroidLinkerConfiguration,
        ...,
    ]
    protobuf_configurations: tuple[
        ParsedAndroidLinkerProtobufConfiguration,
        ...,
    ]
    native_library_configurations: tuple[
        ParsedAndroidNativeLibraryConfiguration,
        ...,
    ]

    text_configuration_semantics: tuple[
        AndroidUniverseLinkerTextConfigurationSemantics,
        ...,
    ]

    protobuf_configuration_semantics: tuple[
        AndroidUniverseLinkerProtobufConfigurationSemantics,
        ...,
    ]

    native_library_configuration_semantics: tuple[
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
        ...,
    ]

    runtime_policies: tuple[
        AndroidUniverseLinkerRuntimePolicy,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        if not isinstance(
            self.protobuf_configurations,
            tuple,
        ):
            raise TypeError(
                "protobuf_configurations must be a tuple"
            )

        if not isinstance(
            self.native_library_configurations,
            tuple,
        ):
            raise TypeError(
                "native_library_configurations must be a tuple"
            )

        if not isinstance(
            self.text_configuration_semantics,
            tuple,
        ):
            raise TypeError(
                "text_configuration_semantics must be a tuple"
            )


        if not isinstance(
            self.protobuf_configuration_semantics,
            tuple,
        ):
            raise TypeError(
                "protobuf_configuration_semantics must be a tuple"
            )


        if not isinstance(
            self.native_library_configuration_semantics,
            tuple,
        ):
            raise TypeError(
                "native_library_configuration_semantics must be a tuple"
            )

        if not isinstance(
            self.runtime_policies,
            tuple,
        ):
            raise TypeError(
                "runtime_policies must be a tuple"
            )

        if not all(
            isinstance(
                policy,
                AndroidUniverseLinkerRuntimePolicy,
            )
            for policy in self.runtime_policies
        ):
            raise TypeError(
                "runtime_policies must contain only "
                "AndroidUniverseLinkerRuntimePolicy instances"
            )

        if not all(
            isinstance(
                item,
                ParsedAndroidLinkerConfiguration,
            )
            for item in self.configurations
        ):
            raise TypeError(
                "configurations must contain only "
                "ParsedAndroidLinkerConfiguration instances"
            )

        if not all(
            isinstance(
                item,
                ParsedAndroidLinkerProtobufConfiguration,
            )
            for item in self.protobuf_configurations
        ):
            raise TypeError(
                "protobuf_configurations must contain only "
                "ParsedAndroidLinkerProtobufConfiguration instances"
            )

        if not all(
            isinstance(
                item,
                ParsedAndroidNativeLibraryConfiguration,
            )
            for item in self.native_library_configurations
        ):
            raise TypeError(
                "native_library_configurations must contain only "
                "ParsedAndroidNativeLibraryConfiguration instances"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerTextConfigurationSemantics,
            )
            for item in self.text_configuration_semantics
        ):
            raise TypeError(
                "text_configuration_semantics must contain only "
                "AndroidUniverseLinkerTextConfigurationSemantics instances"
            )

        if len(
            self.text_configuration_semantics
        ) != len(
            self.configurations
        ):
            raise ValueError(
                "every parsed linker text configuration must have exactly "
                "one semantic interpretation"
            )


        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerProtobufConfigurationSemantics,
            )
            for item
            in self.protobuf_configuration_semantics
        ):
            raise TypeError(
                "protobuf_configuration_semantics must contain only "
                "AndroidUniverseLinkerProtobufConfigurationSemantics "
                "instances"
            )

        if len(
            self.protobuf_configuration_semantics
        ) != len(
            self.protobuf_configurations
        ):
            raise ValueError(
                "every parsed linker protobuf configuration must have "
                "exactly one semantic interpretation"
            )

        for (
            configuration,
            semantics,
        ) in zip(
            self.protobuf_configurations,
            self.protobuf_configuration_semantics,
            strict=True,
        ):
            if semantics.source is not configuration:
                raise ValueError(
                    "Linker protobuf semantics must preserve exact Parsing "
                    "configuration identity and order"
                )


        if not all(
            isinstance(
                item,
                AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
            )
            for item
            in self.native_library_configuration_semantics
        ):
            raise TypeError(
                "native_library_configuration_semantics must contain only "
                "AndroidUniverseLinkerNativeLibraryConfigurationSemantics "
                "instances"
            )

        if len(
            self.native_library_configuration_semantics
        ) != len(
            self.native_library_configurations
        ):
            raise ValueError(
                "every parsed native-library configuration must have "
                "exactly one semantic interpretation"
            )

        for (
            configuration,
            semantics,
        ) in zip(
            self.native_library_configurations,
            self.native_library_configuration_semantics,
            strict=True,
        ):
            if semantics.source is not configuration:
                raise ValueError(
                    "native-library semantics must preserve exact Parsing "
                    "configuration identity and order"
                )

        for (
            configuration,
            semantics,
        ) in zip(
            self.configurations,
            self.text_configuration_semantics,
            strict=True,
        ):
            if semantics.source is not configuration:
                raise ValueError(
                    "Linker text semantics must preserve exact Parsing "
                    "configuration identity and order"
                )
