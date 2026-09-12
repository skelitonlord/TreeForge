from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.kernel import (
    ParsedKernelConfigDeclaration,
    ParsedKernelConfigUnparsedLine,
    ParsedKernelImage,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelConfigRequirement:
    """
    One canonical kernel-config requirement promoted from Parsing.

    Parsing remains authoritative for the literal declaration. Universe owns
    the device-level requirement identity and later reconciliation semantics.
    """

    source: ParsedKernelImage
    declaration: ParsedKernelConfigDeclaration

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedKernelImage,
        ):
            raise TypeError(
                "source must be a ParsedKernelImage"
            )

        if not isinstance(
            self.declaration,
            ParsedKernelConfigDeclaration,
        ):
            raise TypeError(
                "declaration must be a ParsedKernelConfigDeclaration"
            )

        if self.source.config is None:
            raise ValueError(
                "kernel config requirement requires source.config"
            )

        if not any(
            item is self.declaration
            for item in self.source.config.declarations
        ):
            raise ValueError(
                "declaration must preserve exact Parsing config identity"
            )

    @property
    def key(self) -> str:
        return self.declaration.key

    @property
    def value(self) -> str | None:
        return self.declaration.value

    @property
    def enabled(self) -> bool | None:
        return self.declaration.enabled

    @property
    def requirement_id(self) -> str:
        return (
            "kernel-config:"
            f"{self.source.artifact.path.as_posix()}:"
            f"{self.declaration.line_number}:"
            f"{self.declaration.key}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelUnparsedConfigEvidence:
    """
    Preserve one Parsing-stage IKCONFIG line not yet semantically understood.
    """

    source: ParsedKernelImage
    line: ParsedKernelConfigUnparsedLine

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedKernelImage,
        ):
            raise TypeError(
                "source must be a ParsedKernelImage"
            )

        if not isinstance(
            self.line,
            ParsedKernelConfigUnparsedLine,
        ):
            raise TypeError(
                "line must be a ParsedKernelConfigUnparsedLine"
            )

        if self.source.config is None:
            raise ValueError(
                "unparsed kernel config evidence requires source.config"
            )

        if not any(
            item is self.line
            for item in self.source.config.unparsed_lines
        ):
            raise ValueError(
                "line must preserve exact Parsing unparsed-line identity"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKernelRequirement:
    """
    Canonical device-level interpretation boundary for the parsed kernel image.

    No kernel bytes are reopened or reparsed here. Exact Parsing objects remain
    the canonical evidence source.
    """

    source: ParsedKernelImage

    config_requirements: tuple[
        AndroidUniverseKernelConfigRequirement,
        ...,
    ] = ()

    unparsed_config_evidence: tuple[
        AndroidUniverseKernelUnparsedConfigEvidence,
        ...,
    ] = ()

    def __post_init__(self) -> None:
        if not isinstance(
            self.source,
            ParsedKernelImage,
        ):
            raise TypeError(
                "source must be a ParsedKernelImage"
            )

        if not isinstance(
            self.config_requirements,
            tuple,
        ):
            raise TypeError(
                "config_requirements must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseKernelConfigRequirement,
            )
            for item in self.config_requirements
        ):
            raise TypeError(
                "config_requirements must contain only "
                "AndroidUniverseKernelConfigRequirement"
            )

        if not all(
            item.source is self.source
            for item in self.config_requirements
        ):
            raise ValueError(
                "kernel config requirements must preserve exact source identity"
            )

        if not isinstance(
            self.unparsed_config_evidence,
            tuple,
        ):
            raise TypeError(
                "unparsed_config_evidence must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseKernelUnparsedConfigEvidence,
            )
            for item in self.unparsed_config_evidence
        ):
            raise TypeError(
                "unparsed_config_evidence must contain only "
                "AndroidUniverseKernelUnparsedConfigEvidence"
            )

        if not all(
            item.source is self.source
            for item in self.unparsed_config_evidence
        ):
            raise ValueError(
                "kernel unparsed evidence must preserve exact source identity"
            )

        if self.source.config is None:
            if self.config_requirements:
                raise ValueError(
                    "kernel without parsed config cannot have config requirements"
                )

            if self.unparsed_config_evidence:
                raise ValueError(
                    "kernel without parsed config cannot have unparsed evidence"
                )

            return

        expected_declarations = tuple(
            self.source.config.declarations
        )

        actual_declarations = tuple(
            item.declaration
            for item in self.config_requirements
        )

        if len(actual_declarations) != len(expected_declarations):
            raise ValueError(
                "kernel config requirements must preserve complete "
                "Parsing declaration population"
            )

        if not all(
            actual is expected
            for actual, expected
            in zip(
                actual_declarations,
                expected_declarations,
                strict=True,
            )
        ):
            raise ValueError(
                "kernel config requirements must preserve exact "
                "Parsing declaration identity and order"
            )

        expected_unparsed = tuple(
            self.source.config.unparsed_lines
        )

        actual_unparsed = tuple(
            item.line
            for item in self.unparsed_config_evidence
        )

        if len(actual_unparsed) != len(expected_unparsed):
            raise ValueError(
                "kernel unparsed evidence must preserve complete "
                "Parsing unparsed-line population"
            )

        if not all(
            actual is expected
            for actual, expected
            in zip(
                actual_unparsed,
                expected_unparsed,
                strict=True,
            )
        ):
            raise ValueError(
                "kernel unparsed evidence must preserve exact "
                "Parsing line identity and order"
            )

    @property
    def linux_banner(self) -> str | None:
        return self.source.linux_banner

    @property
    def kernel_release(self) -> str | None:
        return self.source.kernel_release

    @property
    def config_count(self) -> int:
        return len(
            self.config_requirements
        )

    @property
    def unparsed_config_count(self) -> int:
        return len(
            self.unparsed_config_evidence
        )

    @property
    def requirement_id(self) -> str:
        return (
            "kernel:"
            f"{self.source.artifact.path.as_posix()}"
        )
