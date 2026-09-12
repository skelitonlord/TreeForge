from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from treeforge.android.properties import (
    AndroidPropertySourceKind,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)


class AndroidDeviceTreeRuntimePropertyPartition(
    StrEnum
):
    """
    Android partition owning one generated build.prop namespace.
    """

    SYSTEM = "system"
    SYSTEM_EXT = "system_ext"
    VENDOR = "vendor"
    ODM = "odm"
    PRODUCT = "product"


_PRODUCT_VARIABLE_BY_PARTITION = {
    AndroidDeviceTreeRuntimePropertyPartition.SYSTEM:
        "PRODUCT_SYSTEM_PROPERTIES",
    AndroidDeviceTreeRuntimePropertyPartition.SYSTEM_EXT:
        "PRODUCT_SYSTEM_EXT_PROPERTIES",
    AndroidDeviceTreeRuntimePropertyPartition.VENDOR:
        "PRODUCT_VENDOR_PROPERTIES",
    AndroidDeviceTreeRuntimePropertyPartition.ODM:
        "PRODUCT_ODM_PROPERTIES",
    AndroidDeviceTreeRuntimePropertyPartition.PRODUCT:
        "PRODUCT_PRODUCT_PROPERTIES",
}


_PARTITION_BY_NAME = {
    partition.value: partition
    for partition
    in AndroidDeviceTreeRuntimePropertyPartition
}


#
# These properties are already projected by another first-class
# TreeForge Device Tree build contract. Re-emitting them here would
# create competing ownership.
#
_OWNED_ELSEWHERE = {
    "ro.product.first_api_level",
    "ro.product.board",
    "ro.board.platform",
    "ro.build.ab_update",
    "ro.vendor.build.ab_ota_partitions",
    "ro.product.ab_ota_partitions",
    "ro.product.cpu.pagesize.max",
    "ro.boot.dynamic_partitions",
}


#
# Literal declarations are normally emitted as optional assignments.
#
# This allows a canonical factory property to fill an absent Android
# product contract without creating a duplicate assignment when the
# selected AOSP base product already owns the same partition/key.
#
# These properties are known device/product contracts whose factory
# declaration must explicitly override lower-priority/default product
# behavior.
#
_NON_OPTIONAL_LITERAL_KEYS = {
    "ro.postinstall.fstab.prefix",
}


_GENERATED_BUILD_IDENTITY_EXACT = {
    "ro.build.id",
    "ro.build.display.id",
    "ro.build.flavor",
    "ro.build.product",
    "ro.build.type",
    "ro.build.tags",
    "ro.build.user",
    "ro.build.host",
    "ro.build.date",
    "ro.build.date.utc",
    "ro.build.fingerprint",
    "ro.build.description",
}


_PRODUCT_IDENTITY_EXACT = {
    "ro.product.brand",
    "ro.product.device",
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.product.name",
}


_GENERATED_PARTITION_BUILD_PREFIXES = (
    "ro.system.build.",
    "ro.system_ext.build.",
    "ro.vendor.build.",
    "ro.odm.build.",
    "ro.product.build.",
    "ro.system_dlkm.build.",
    "ro.vendor_dlkm.build.",
    "ro.odm_dlkm.build.",
    "ro.bootimage.build.",
)


#
# Product/provider composition is not reconstructed merely because a
# factory build.prop declares it.
#
# These namespaces describe optional Google product surfaces such as
# Google Setup Wizard, Assistant/OPA, Google IME, and other GMS-facing
# product integration. They require an actual selected provider and
# therefore do not belong in a GApps-free Device Tree projection.
#
_PROVIDER_COMPOSITION_PREFIXES = (
    "ro.com.google.",
    "ro.opa.",
    "ro.setupwizard.",
    "setupwizard.",
)


def _is_optional_provider_composition_property(
    *,
    key: str,
    value: str,
) -> bool:
    if key.startswith(
        _PROVIDER_COMPOSITION_PREFIXES
    ):
        return True

    #
    # These generic property names become provider-specific through
    # their values.
    #
    if (
        key == "ro.error.receiver.system.apps"
        and "com.google." in value
    ):
        return True

    if (
        key == "ro.atrace.core.services"
        and "com.google." in value
    ):
        return True

    #
    # Pixel camera-extension package bindings are meaningful only if
    # the corresponding Google camera-services provider is selected.
    #
    if (
        key
        in {
            "ro.vendor.camera.extensions.package",
            "ro.vendor.camera.extensions.service",
        }
        and value.startswith("com.google.")
    ):
        return True

    return False


_GENERATED_PRODUCT_IDENTITY_PREFIXES = (
    "ro.product.system.",
    "ro.product.system_ext.",
    "ro.product.vendor.",
    "ro.product.odm.",
    "ro.product.product.",
    "ro.product.system_dlkm.",
    "ro.product.vendor_dlkm.",
    "ro.product.odm_dlkm.",
    "ro.system.product.cpu.",
    "ro.system_ext.product.cpu.",
    "ro.vendor.product.cpu.",
    "ro.odm.product.cpu.",
    "ro.product.cpu.",
)


def _is_android_generated_identity(
    key: str,
) -> bool:
    if key in _GENERATED_BUILD_IDENTITY_EXACT:
        return True

    if key in _PRODUCT_IDENTITY_EXACT:
        return True

    if key.startswith(
        "ro.build.version."
    ):
        return True

    if key.startswith(
        _GENERATED_PARTITION_BUILD_PREFIXES
    ):
        return True

    if key.startswith(
        _GENERATED_PRODUCT_IDENTITY_PREFIXES
    ):
        return True

    return False


def _validate_make_property_token(
    *,
    key: str,
    value: str,
) -> None:
    """
    Fail closed rather than silently corrupting Make syntax.

    Factory build.prop values admitted here are expected to be one
    property-list token. More complex escaping can be added explicitly
    when a real device proves it is necessary.
    """

    if not key:
        raise ValueError(
            "runtime property key must not be empty"
        )

    if any(
        character.isspace()
        for character in key
    ):
        raise ValueError(
            "runtime property key cannot contain whitespace: "
            f"{key!r}"
        )

    if any(
        character.isspace()
        for character in value
    ):
        raise ValueError(
            "runtime property value requires unsupported "
            "Make escaping: "
            f"{key}={value!r}"
        )

    for unsafe in (
        "#",
        "\\",
        "$",
    ):
        if unsafe in key or unsafe in value:
            raise ValueError(
                "runtime property requires unsupported "
                "Make escaping: "
                f"{key}={value!r}"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeRuntimePropertyAssignment:
    """
    One factory-derived literal partition build-property assignment.

    Provenance remains attached to the exact Reconstruction
    representation and source declaration.
    """

    partition: AndroidDeviceTreeRuntimePropertyPartition
    key: str
    value: str
    representation_id: str
    source_host_path: str
    source_android_path: str | None
    source_line_number: int
    optional: bool = True

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.partition,
            AndroidDeviceTreeRuntimePropertyPartition,
        ):
            raise TypeError(
                "partition must be an "
                "AndroidDeviceTreeRuntimePropertyPartition"
            )

        for name, value in (
            ("key", self.key),
            (
                "representation_id",
                self.representation_id,
            ),
            (
                "source_host_path",
                self.source_host_path,
            ),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{name} must be a non-empty string"
                )

        if not isinstance(
            self.value,
            str,
        ):
            raise TypeError(
                "value must be a string"
            )

        if (
            self.source_android_path is not None
            and not isinstance(
                self.source_android_path,
                str,
            )
        ):
            raise TypeError(
                "source_android_path must be a string "
                "or None"
            )

        if (
            not isinstance(
                self.source_line_number,
                int,
            )
            or self.source_line_number < 1
        ):
            raise ValueError(
                "source_line_number must be positive"
            )

        if not isinstance(
            self.optional,
            bool,
        ):
            raise TypeError(
                "optional must be a bool"
            )

        _validate_make_property_token(
            key=self.key,
            value=self.value,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidDeviceTreeRuntimePropertyBuildPlan:
    """
    Concrete Android build projection of canonical runtime properties.
    """

    assignments: tuple[
        AndroidDeviceTreeRuntimePropertyAssignment,
        ...,
    ]

    target_screen_density: int | None = None

    #
    # Android 15 permits true, false, or an empty string here.
    #
    target_uses_vulkan: str | None = None

    product_characteristics: str | None = None

    omitted_generated_keys: tuple[str, ...] = ()

    omitted_owned_keys: tuple[str, ...] = ()

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.assignments,
            tuple,
        ):
            raise TypeError(
                "assignments must be a tuple"
            )

        if not all(
            isinstance(
                assignment,
                AndroidDeviceTreeRuntimePropertyAssignment,
            )
            for assignment in self.assignments
        ):
            raise TypeError(
                "assignments contain unsupported values"
            )

        assignment_ids = tuple(
            (
                assignment.partition.value,
                assignment.key,
            )
            for assignment in self.assignments
        )

        if len(
            assignment_ids
        ) != len(
            set(
                assignment_ids
            )
        ):
            raise ValueError(
                "runtime property build plan contains "
                "duplicate partition/key assignments"
            )

        if self.assignments != tuple(
            sorted(
                self.assignments,
                key=lambda assignment: (
                    assignment.partition.value,
                    assignment.key,
                    assignment.value,
                ),
            )
        ):
            raise ValueError(
                "runtime property assignments must use "
                "deterministic ordering"
            )

        if (
            self.target_screen_density is not None
            and (
                not isinstance(
                    self.target_screen_density,
                    int,
                )
                or self.target_screen_density <= 0
            )
        ):
            raise ValueError(
                "target_screen_density must be a "
                "positive integer or None"
            )

        if (
            self.target_uses_vulkan is not None
            and self.target_uses_vulkan
            not in {
                "",
                "true",
                "false",
            }
        ):
            raise ValueError(
                "target_uses_vulkan must be true, false, "
                "empty, or None"
            )

        if (
            self.product_characteristics is not None
            and (
                not isinstance(
                    self.product_characteristics,
                    str,
                )
                or not self.product_characteristics
            )
        ):
            raise ValueError(
                "product_characteristics must be a "
                "non-empty string or None"
            )


class AndroidDeviceTreeRuntimePropertyBuildProjector:
    """
    Project canonical Reconstruction property declarations into
    Android Device Tree build syntax.

    Only partition-backed build.prop declarations participate in the
    literal PRODUCT_<PARTITION>_PROPERTIES projection.

    default.prop, prop.default, and arbitrary *.prop sources remain
    owned by their original semantic/source mechanisms.
    """

    @staticmethod
    def _resolve_scalar(
        *,
        name: str,
        values: list[str],
    ) -> str | None:
        unique = tuple(
            sorted(
                set(
                    values
                )
            )
        )

        if not unique:
            return None

        if len(unique) != 1:
            raise ValueError(
                "conflicting runtime property build "
                f"contract for {name}: {unique!r}"
            )

        return unique[0]

    @classmethod
    def project(
        cls,
        *,
        reconstruction: AndroidReconstructionResult,
    ) -> AndroidDeviceTreeRuntimePropertyBuildPlan:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        literal_candidates: dict[
            tuple[
                AndroidDeviceTreeRuntimePropertyPartition,
                str,
            ],
            list[
                tuple[
                    str,
                    str,
                    object,
                ]
            ],
        ] = {}

        density_values: list[str] = []
        vulkan_values: list[str] = []
        characteristics_values: list[str] = []

        omitted_generated: set[str] = set()
        omitted_owned: set[str] = set()

        for representation in (
            reconstruction
            .runtime_property_representations
        ):
            requirement = (
                representation.requirement
            )

            for observation in (
                requirement.declaration_observations
            ):
                parsed_source = (
                    observation.parsed_source
                )

                #
                # Literal Android product properties correspond only
                # to partition build.prop declarations.
                #
                if (
                    parsed_source.kind
                    is not AndroidPropertySourceKind.BUILD
                ):
                    continue

                partition_name = (
                    observation
                    .model_source
                    .filesystem_source
                    .partition_name
                )

                partition = (
                    _PARTITION_BY_NAME.get(
                        partition_name
                    )
                )

                if partition is None:
                    continue

                declaration = observation.declaration
                key = declaration.key
                value = declaration.value

                #
                # Known build-derived contracts.
                #
                if key == "ro.sf.lcd_density":
                    density_values.append(
                        value
                    )
                    continue

                if key == "ro.hwui.use_vulkan":
                    vulkan_values.append(
                        value
                    )
                    continue

                if key == "ro.build.characteristics":
                    #
                    # ro.build.characteristics is generated from the
                    # selected Android product policy. The factory
                    # runtime value does not establish the AOSP product
                    # composition contract.
                    #
                    omitted_owned.add(
                        key
                    )
                    continue

                #
                # gs201's postinstall fstab is product-owned. Factory
                # system/build.prop also carries the runtime namespace,
                # but replaying that declaration would incorrectly add
                # the /system producer to the reconstructed AOSP
                # product.
                #
                if (
                    key == "ro.postinstall.fstab.prefix"
                    and partition
                    is not
                    AndroidDeviceTreeRuntimePropertyPartition.PRODUCT
                ):
                    omitted_owned.add(
                        key
                    )
                    continue

                #
                # Optional product/provider composition requires an
                # explicitly selected provider. Factory presence alone
                # does not authorize replay into a pure AOSP product.
                #
                if _is_optional_provider_composition_property(
                    key=key,
                    value=value,
                ):
                    omitted_owned.add(
                        key
                    )
                    continue

                #
                # Android-generated image/product identity must be
                # regenerated by AOSP, never replayed from factory
                # build.prop.
                #
                if _is_android_generated_identity(
                    key
                ):
                    omitted_generated.add(
                        key
                    )
                    continue

                #
                # Another TreeForge Device Tree capability already
                # owns these.
                #
                if key in _OWNED_ELSEWHERE:
                    omitted_owned.add(
                        key
                    )
                    continue

                literal_candidates.setdefault(
                    (
                        partition,
                        key,
                    ),
                    [],
                ).append(
                    (
                        value,
                        representation.representation_id,
                        observation,
                    )
                )

        density_value = cls._resolve_scalar(
            name="ro.sf.lcd_density",
            values=density_values,
        )

        target_screen_density = None

        if density_value is not None:
            try:
                target_screen_density = int(
                    density_value,
                    10,
                )
            except ValueError as error:
                raise ValueError(
                    "ro.sf.lcd_density must be an integer: "
                    f"{density_value!r}"
                ) from error

            if target_screen_density <= 0:
                raise ValueError(
                    "ro.sf.lcd_density must be positive"
                )

        target_uses_vulkan = cls._resolve_scalar(
            name="ro.hwui.use_vulkan",
            values=vulkan_values,
        )

        if (
            target_uses_vulkan is not None
            and target_uses_vulkan
            not in {
                "",
                "true",
                "false",
            }
        ):
            raise ValueError(
                "ro.hwui.use_vulkan has unsupported value: "
                f"{target_uses_vulkan!r}"
            )

        product_characteristics = (
            cls._resolve_scalar(
                name="ro.build.characteristics",
                values=characteristics_values,
            )
        )

        assignments = []

        for (
            partition,
            key,
        ), candidates in sorted(
            literal_candidates.items(),
            key=lambda item: (
                item[0][0].value,
                item[0][1],
            ),
        ):
            distinct_values = tuple(
                sorted(
                    {
                        value
                        for value, _, _
                        in candidates
                    }
                )
            )

            if len(
                distinct_values
            ) != 1:
                raise ValueError(
                    "conflicting static build.prop "
                    "declarations for "
                    f"{partition.value}:{key}: "
                    f"{distinct_values!r}"
                )

            value = distinct_values[0]

            #
            # Choose deterministic exact provenance when identical
            # duplicate declarations exist.
            #
            provenance_candidates = tuple(
                sorted(
                    (
                        (
                            representation_id,
                            observation,
                        )
                        for (
                            candidate_value,
                            representation_id,
                            observation,
                        )
                        in candidates
                        if candidate_value == value
                    ),
                    key=lambda item: (
                        str(
                            item[1]
                            .parsed_source
                            .source_path
                        ),
                        item[1]
                        .declaration
                        .line_number,
                        item[0],
                    ),
                )
            )

            (
                representation_id,
                observation,
            ) = provenance_candidates[0]

            android_path = (
                observation
                .parsed_source
                .android_path
            )

            assignments.append(
                AndroidDeviceTreeRuntimePropertyAssignment(
                    partition=partition,
                    key=key,
                    value=value,
                    representation_id=(
                        representation_id
                    ),
                    source_host_path=str(
                        observation
                        .parsed_source
                        .source_path
                    ),
                    source_android_path=(
                        android_path.as_posix()
                        if android_path is not None
                        else None
                    ),
                    source_line_number=(
                        observation
                        .declaration
                        .line_number
                    ),
                    optional=(
                        key
                        not in
                        _NON_OPTIONAL_LITERAL_KEYS
                    ),
                )
            )

        return AndroidDeviceTreeRuntimePropertyBuildPlan(
            assignments=tuple(
                sorted(
                    assignments,
                    key=lambda assignment: (
                        assignment.partition.value,
                        assignment.key,
                        assignment.value,
                    ),
                )
            ),
            target_screen_density=(
                target_screen_density
            ),
            target_uses_vulkan=(
                target_uses_vulkan
            ),
            product_characteristics=(
                product_characteristics
            ),
            omitted_generated_keys=tuple(
                sorted(
                    omitted_generated
                )
            ),
            omitted_owned_keys=tuple(
                sorted(
                    omitted_owned
                )
            ),
        )


class AndroidDeviceTreeRuntimePropertyBuildRenderer:
    """
    Render one runtime-property build plan into canonical Android
    BoardConfig and product configuration syntax.
    """

    @staticmethod
    def render_board_config(
        plan: AndroidDeviceTreeRuntimePropertyBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeRuntimePropertyBuildPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeRuntimePropertyBuildPlan"
            )

        lines = [
            (
                "# TreeForge-reconstructed Android "
                "property build contracts."
            ),
            "#",
            (
                "# Canonical factory runtime-property "
                "evidence projected into Android build "
                "semantics."
            ),
        ]

        if (
            plan.target_screen_density
            is not None
        ):
            lines.extend(
                [
                    "",
                    (
                        "TARGET_SCREEN_DENSITY := "
                        f"{plan.target_screen_density}"
                    ),
                ]
            )

        if (
            plan.target_uses_vulkan
            is not None
        ):
            lines.extend(
                [
                    "",
                    (
                        "TARGET_USES_VULKAN := "
                        f"{plan.target_uses_vulkan}"
                    ),
                ]
            )

        return (
            "\n".join(
                lines
            ).rstrip()
            + "\n"
        )

    @staticmethod
    def render_product_config(
        plan: AndroidDeviceTreeRuntimePropertyBuildPlan,
    ) -> str:
        if not isinstance(
            plan,
            AndroidDeviceTreeRuntimePropertyBuildPlan,
        ):
            raise TypeError(
                "plan must be an "
                "AndroidDeviceTreeRuntimePropertyBuildPlan"
            )

        lines = [
            (
                "# TreeForge-reconstructed Android "
                "runtime property contracts."
            ),
            "#",
            (
                "# Literal values preserve exact "
                "factory build.prop provenance."
            ),
        ]

        if (
            plan.product_characteristics
            is not None
        ):
            lines.extend(
                [
                    "",
                    (
                        "PRODUCT_CHARACTERISTICS := "
                        f"{plan.product_characteristics}"
                    ),
                ]
            )

        for partition in (
            AndroidDeviceTreeRuntimePropertyPartition
        ):
            assignments = tuple(
                assignment
                for assignment
                in plan.assignments
                if (
                    assignment.partition
                    is partition
                )
            )

            if not assignments:
                continue

            variable = (
                _PRODUCT_VARIABLE_BY_PARTITION[
                    partition
                ]
            )

            lines.extend(
                [
                    "",
                    f"{variable} += \\",
                ]
            )

            for index, assignment in enumerate(
                assignments
            ):
                suffix = (
                    " \\"
                    if index
                    < len(assignments) - 1
                    else ""
                )

                operator = (
                    "?="
                    if assignment.optional
                    else "="
                )

                lines.append(
                    "    "
                    f"{assignment.key}"
                    f"{operator}"
                    f"{assignment.value}"
                    f"{suffix}"
                )

        return (
            "\n".join(
                lines
            ).rstrip()
            + "\n"
        )
