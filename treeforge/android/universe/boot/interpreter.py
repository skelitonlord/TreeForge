from __future__ import annotations

from treeforge.android.parsing.result import (
    ParsedBootImage,
)
from treeforge.android.universe.boot.requirement import (
    AndroidUniverseBootRequirement,
)
from treeforge.android.universe.boot.semantics import (
    AndroidUniverseBootAndroidVersion,
    AndroidUniverseBootconfigDeclaration,
    AndroidUniverseBootconfigSemantics,
    AndroidUniverseBootDeviceSelection,
    AndroidUniverseFirstStageModuleLoadingPolicy,
    AndroidUniverseBootSemantics,
    AndroidUniverseKernelCommandLineArgument,
    AndroidUniverseKernelCommandLineArgumentKind,
    AndroidUniverseKernelCommandLineSemantics,
    AndroidUniverseVendorBootSemantics,
)


class AndroidUniverseBootInterpreter:
    """
    Interpret the complete current boot-family Parsing surface.

    Parsing remains authoritative for binary-header decoding. Universe adds
    device-level requirement classification and ordered kernel command-line
    semantics without re-reading image bytes.
    """

    def interpret(
        self,
        sources: tuple[
            ParsedBootImage,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseBootRequirement,
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
                ParsedBootImage,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedBootImage instances"
            )

        return tuple(
            self._interpret_source(
                source
            )
            for source in sources
        )

    def _interpret_source(
        self,
        source: ParsedBootImage,
    ) -> AndroidUniverseBootRequirement:
        metadata = source.metadata

        if (
            source.container_format
            == "android_boot"
        ):
            return AndroidUniverseBootRequirement(
                source=source,
                semantics=(
                    AndroidUniverseBootSemantics(
                        header_version=(
                            metadata.header_version
                        ),
                        android_version=(
                            AndroidUniverseBootAndroidVersion(
                                encoded=metadata.os_version,
                                major=metadata.android_major,
                                minor=metadata.android_minor,
                                patch=metadata.android_patch,
                            )
                        ),
                        boot_name=metadata.boot_name,
                        command_line=(
                            self._interpret_command_line(
                                metadata.cmdline
                            )
                        ),
                    )
                ),
            )

        if (
            source.container_format
            == "android_vendor_boot"
        ):
            return AndroidUniverseBootRequirement(
                source=source,
                semantics=(
                    AndroidUniverseVendorBootSemantics(
                        header_version=(
                            metadata.header_version
                        ),
                        boot_name=(
                            metadata.boot_name
                        ),
                        command_line=(
                            self._interpret_command_line(
                                metadata.cmdline
                            )
                        ),
                        bootconfig=(
                            self._interpret_bootconfig(
                                source
                            )
                        ),
                    )
                ),
            )

        raise ValueError(
            "unsupported canonical boot container format: "
            f"{source.container_format}"
        )

    @staticmethod
    def _interpret_bootconfig(
        source: ParsedBootImage,
    ) -> AndroidUniverseBootconfigSemantics | None:
        parsed = source.bootconfig

        if parsed is None:
            return None

        declarations = tuple(
            AndroidUniverseBootconfigDeclaration(
                index=index,
                source=entry,
            )
            for index, entry
            in enumerate(
                parsed.entries
            )
        )

        boot_device_selections = tuple(
            AndroidUniverseBootDeviceSelection(
                source=declaration,
                devices=(
                    AndroidUniverseBootInterpreter
                    ._interpret_boot_device_value(
                        declaration.value
                    )
                ),
            )
            for declaration
            in declarations
            if declaration.key in (
                "androidboot.boot_device",
                "androidboot.boot_devices",
            )
        )

        module_loading_policies = tuple(
            AndroidUniverseFirstStageModuleLoadingPolicy(
                source=declaration,
                parallel=(
                    AndroidUniverseBootInterpreter
                    ._interpret_bootconfig_scalar(
                        declaration.value
                    )
                    == "true"
                ),
            )
            for declaration
            in declarations
            if (
                declaration.key
                == "androidboot.load_modules_parallel"
            )
        )

        return AndroidUniverseBootconfigSemantics(
            declarations=declarations,
            unparsed_line_count=len(
                parsed.unparsed_lines
            ),
            boot_device_selections=(
                boot_device_selections
            ),
            module_loading_policies=(
                module_loading_policies
            ),
        )

    @staticmethod
    def _interpret_bootconfig_scalar(
        literal: str,
    ) -> str:
        value = literal.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in (
                "'",
                '"',
            )
        ):
            value = value[
                1:-1
            ]

        return value

    @staticmethod
    def _interpret_boot_device_value(
        literal: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Interpret androidboot.boot_device[s] without splitting commas that
        occur inside quoted bootconfig list elements.
        """

        value = literal.strip()

        if not value:
            raise ValueError(
                "boot-device declaration must not be empty"
            )

        elements: list[
            str
        ] = []

        current: list[
            str
        ] = []

        quote: str | None = None
        escaped = False

        for character in value:
            if escaped:
                current.append(
                    character
                )
                escaped = False
                continue

            if (
                character == "\\"
                and quote == '"'
            ):
                escaped = True
                continue

            if quote is not None:
                if character == quote:
                    quote = None
                    continue

                current.append(
                    character
                )
                continue

            if character in (
                "'",
                '"',
            ):
                quote = character
                continue

            if character == ",":
                element = "".join(
                    current
                ).strip()

                if not element:
                    raise ValueError(
                        "boot-device declaration contains "
                        "an empty list element"
                    )

                elements.append(
                    element
                )

                current = []
                continue

            current.append(
                character
            )

        if escaped:
            raise ValueError(
                "boot-device declaration ends with "
                "an escape character"
            )

        if quote is not None:
            raise ValueError(
                "boot-device declaration contains "
                "an unterminated quote"
            )

        element = "".join(
            current
        ).strip()

        if not element:
            raise ValueError(
                "boot-device declaration contains "
                "an empty list element"
            )

        elements.append(
            element
        )

        return tuple(
            elements
        )


    def _interpret_command_line(
        self,
        literal: str,
    ) -> AndroidUniverseKernelCommandLineSemantics:
        if not isinstance(
            literal,
            str,
        ):
            raise TypeError(
                "literal command line must be a string"
            )

        lexical_tokens = (
            self._tokenize_command_line(
                literal
            )
        )

        arguments = tuple(
            self._interpret_argument(
                index=index,
                raw=raw,
                semantic=semantic,
            )
            for (
                index,
                (
                    raw,
                    semantic,
                ),
            )
            in enumerate(
                lexical_tokens
            )
        )

        return (
            AndroidUniverseKernelCommandLineSemantics(
                literal=literal,
                arguments=arguments,
            )
        )

    @staticmethod
    def _interpret_argument(
        *,
        index: int,
        raw: str,
        semantic: str,
    ) -> AndroidUniverseKernelCommandLineArgument:
        if "=" in semantic:
            key, value = semantic.split(
                "=",
                1,
            )

            if key:
                return (
                    AndroidUniverseKernelCommandLineArgument(
                        index=index,
                        raw=raw,
                        kind=(
                            AndroidUniverseKernelCommandLineArgumentKind.ASSIGNMENT
                        ),
                        key=key,
                        value=value,
                    )
                )

        return (
            AndroidUniverseKernelCommandLineArgument(
                index=index,
                raw=raw,
                kind=(
                    AndroidUniverseKernelCommandLineArgumentKind.FLAG
                ),
                key=semantic,
                value=None,
            )
        )

    @staticmethod
    def _tokenize_command_line(
        literal: str,
    ) -> tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ]:
        """
        Tokenize one kernel command line while preserving raw token spelling.

        The returned pairs are:

            (raw lexical token, interpreted/dequoted token)

        Whitespace separates tokens outside quotes. Single and double quotes
        group whitespace. Backslash escapes the next character outside single
        quotes.

        This deliberately implements only lexical interpretation; parameter
        names themselves remain open-ended device evidence.
        """

        tokens: list[
            tuple[
                str,
                str,
            ]
        ] = []

        length = len(
            literal
        )

        index = 0

        while index < length:
            while (
                index < length
                and literal[index].isspace()
            ):
                index += 1

            if index >= length:
                break

            start = index

            semantic: list[
                str
            ] = []

            quote: str | None = None

            while index < length:
                character = (
                    literal[index]
                )

                if quote is None:
                    if character.isspace():
                        break

                    if character in (
                        "'",
                        '"',
                    ):
                        quote = character
                        index += 1
                        continue

                    if character == "\\":
                        index += 1

                        if index >= length:
                            raise ValueError(
                                "Kernel command line ends "
                                "with an escape character"
                            )

                        semantic.append(
                            literal[index]
                        )

                        index += 1
                        continue

                    semantic.append(
                        character
                    )

                    index += 1
                    continue

                if character == quote:
                    quote = None
                    index += 1
                    continue

                if (
                    character == "\\"
                    and quote == '"'
                ):
                    index += 1

                    if index >= length:
                        raise ValueError(
                            "Kernel command line ends "
                            "with an escape character"
                        )

                    semantic.append(
                        literal[index]
                    )

                    index += 1
                    continue

                semantic.append(
                    character
                )

                index += 1

            if quote is not None:
                raise ValueError(
                    "Kernel command line contains "
                    "an unterminated quote"
                )

            raw = literal[
                start:index
            ]

            semantic_value = "".join(
                semantic
            )

            if not semantic_value:
                raise ValueError(
                    "Kernel command line contains "
                    "an empty argument"
                )

            tokens.append(
                (
                    raw,
                    semantic_value,
                )
            )

        return tuple(
            tokens
        )