from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseArchitectureKnowledge:
    """
    Optional architecture facts contributed by one resolved knowledge module.

    The fields are generic Android architecture concepts.

    This payload deliberately contains no TARGET_*, PRODUCT_*, BoardConfig,
    device identity, Android-version identity, or platform identity. The
    owning AndroidKnowledgeModule supplies that provenance separately.
    """

    board_platform: str | None = None

    primary_architecture: str | None = None

    primary_arch_variant: str | None = None

    primary_cpu_abi: str | None = None

    primary_cpu_variant: str | None = None

    primary_cpu_variant_runtime: str | None = None

    secondary_architecture: str | None = None

    secondary_arch_variant: str | None = None

    secondary_cpu_abi: str | None = None

    secondary_cpu_abi2: str | None = None

    secondary_cpu_variant: str | None = None

    secondary_cpu_variant_runtime: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "board_platform",
            "primary_architecture",
            "primary_arch_variant",
            "primary_cpu_abi",
            "primary_cpu_variant",
            "primary_cpu_variant_runtime",
            "secondary_architecture",
            "secondary_arch_variant",
            "secondary_cpu_abi",
            "secondary_cpu_abi2",
            "secondary_cpu_variant",
            "secondary_cpu_variant_runtime",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is None:
                continue

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

            if value != value.strip():
                raise ValueError(
                    f"{field_name} must not contain "
                    "surrounding whitespace"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseVintfSelectionKnowledge:
    """
    One VINTF source selection contributed by a resolved knowledge module.

    ``source_path`` identifies the source-tree VINTF document whose semantic
    content is required by this module.

    ``role`` is generic VINTF intent rather than a Make/Build variable name.

    Optional selector fields preserve conditional source-tree alternatives
    without resolving them prematurely inside the knowledge module.
    """

    source_path: str
    role: str

    selector_key: str | None = None
    selector_value: str | None = None
    alternative_group: str | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "source_path",
            "role",
        ):
            value = getattr(
                self,
                field_name,
            )

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

            if value != value.strip():
                raise ValueError(
                    f"{field_name} must not contain "
                    "surrounding whitespace"
                )

        for field_name in (
            "selector_key",
            "selector_value",
            "alternative_group",
        ):
            value = getattr(
                self,
                field_name,
            )

            if value is None:
                continue

            if not isinstance(
                value,
                str,
            ):
                raise TypeError(
                    f"{field_name} must be a string or None"
                )

            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty when present"
                )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseKnowledge:
    """
    Optional Android knowledge contributed to the generic Universe stage.

    This payload may be supplied by resolved device, platform, or OEM
    knowledge modules.

    The generic Universe stage remains identity-agnostic: it consumes resolved
    module contributions rather than importing device-specific implementations
    directly.
    """

    architecture: (
        AndroidUniverseArchitectureKnowledge
        | None
    ) = None

    vintf_selections: tuple[
        AndroidUniverseVintfSelectionKnowledge,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if (
            self.architecture is not None
            and not isinstance(
                self.architecture,
                AndroidUniverseArchitectureKnowledge,
            )
        ):
            raise TypeError(
                "architecture must be an "
                "AndroidUniverseArchitectureKnowledge or None"
            )

        if not isinstance(
            self.vintf_selections,
            tuple,
        ):
            raise TypeError(
                "vintf_selections must be a tuple"
            )

        if not all(
            isinstance(
                item,
                AndroidUniverseVintfSelectionKnowledge,
            )
            for item in self.vintf_selections
        ):
            raise TypeError(
                "vintf_selections must contain only "
                "AndroidUniverseVintfSelectionKnowledge instances"
            )

        canonical_vintf_selections = tuple(
            sorted(
                self.vintf_selections,
                key=lambda item: (
                    item.role,
                    item.source_path,
                    item.selector_key or "",
                    item.selector_value or "",
                    item.alternative_group or "",
                ),
            )
        )

        if (
            self.vintf_selections
            != canonical_vintf_selections
        ):
            raise ValueError(
                "vintf_selections must use canonical order"
            )

        identities = tuple(
            (
                item.role,
                item.source_path,
                item.selector_key,
                item.selector_value,
                item.alternative_group,
            )
            for item in self.vintf_selections
        )

        if len(identities) != len(set(identities)):
            raise ValueError(
                "vintf_selections must be unique"
            )
