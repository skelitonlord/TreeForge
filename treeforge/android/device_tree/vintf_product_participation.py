from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.device_tree.apk_android_mk import (
    AndroidDeviceTreeApkAndroidMkModule,
)
from treeforge.android.device_tree.vintf_build import (
    AndroidDeviceTreeVintfBuildConfig,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)
from treeforge.android.universe.relationship import (
    AndroidUniverseApplicabilityStatus,
)
from treeforge.android.universe.relationships import (
    AndroidUniverseApkVintfStructuralProviderRelationship,
    AndroidUniverseRelationshipStatus,
)
from treeforge.android.universe.vintf.document import (
    AndroidUniverseVintfDocumentKind,
)
from treeforge.android.universe.vintf.hal import (
    AndroidUniverseVintfHalFormat,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVintfProductSuppression:
    """
    One canonical VINTF fragment omitted from PRODUCT_PACKAGES because every
    semantic declaration in the fragment is an AIDL service structurally
    provided by factory APKs that the selected Device Tree product policy
    does not install.

    Canonical VINTF source/module realization remains unchanged.
    """

    representation_id: str
    module_name: str

    canonical_names: tuple[str, ...]
    provider_representation_ids: tuple[str, ...]
    relationship_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for field_name, value in (
            ("representation_id", self.representation_id),
            ("module_name", self.module_name),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        for field_name, values in (
            ("canonical_names", self.canonical_names),
            (
                "provider_representation_ids",
                self.provider_representation_ids,
            ),
            ("relationship_ids", self.relationship_ids),
        ):
            if not isinstance(values, tuple):
                raise TypeError(
                    f"{field_name} must be a tuple"
                )

            if not values:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

            if not all(
                isinstance(value, str) and value
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain only "
                    "non-empty strings"
                )

            if values != tuple(
                sorted(
                    set(values)
                )
            ):
                raise ValueError(
                    f"{field_name} must be unique and "
                    "deterministically ordered"
                )


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeVintfProductParticipationPlan:
    """
    Device Tree product-participation disposition for generated VINTF
    fragment modules.

    This does not mutate canonical VINTF reconstruction or Android.bp
    realization.
    """

    product_packages: tuple[str, ...]
    suppressions: tuple[
        AndroidDeviceTreeVintfProductSuppression,
        ...,
    ]

    def __post_init__(self) -> None:
        if self.product_packages != tuple(
            sorted(
                set(
                    self.product_packages
                )
            )
        ):
            raise ValueError(
                "product_packages must be unique and "
                "deterministically ordered"
            )

        suppression_ids = tuple(
            suppression.representation_id
            for suppression in self.suppressions
        )

        if len(
            suppression_ids
        ) != len(
            set(
                suppression_ids
            )
        ):
            raise ValueError(
                "VINTF product suppressions must preserve "
                "unique representation identity"
            )


class AndroidDeviceTreeVintfProductParticipationProjector:
    """
    Apply Device Tree product policy to canonical Reconstruction
    APK -> VINTF structural-provider relationships.

    Universe remains authoritative for structural provider semantics.
    Device Tree owns only the decision whether an already-generated VINTF
    module participates in the selected Android product.

    Suppression is deliberately fail-closed. A fragment remains installed
    unless all of the following are true:

    * it is a pure manifest HAL fragment;
    * every HAL is AIDL;
    * every exact AIDL service identity has an ACTIVE, RESOLVED structural
      provider relationship;
    * every provider maps to a canonical generated APK module;
    * none of those provider APK modules participates in the selected product;
    * no other interpreted or uninterpreted VINTF semantic content would be
      lost by omitting the fragment.
    """

    @staticmethod
    def _canonical_aidl_names(
        requirement,
    ) -> tuple[str, ...] | None:
        semantics = requirement.semantics

        if (
            semantics.kind
            is not AndroidUniverseVintfDocumentKind.MANIFEST
        ):
            return None

        if (
            semantics.level is not None
            or semantics.target_level is not None
            or semantics.kernels
            or semantics.sepolicy
            or semantics.system_sdk
            or semantics.avb
            or semantics.uninterpreted_elements
            or semantics.uninterpreted_attributes
        ):
            return None

        canonical_names = []

        for hal in semantics.hals:
            if (
                hal.format
                is not AndroidUniverseVintfHalFormat.AIDL
            ):
                return None

            for interface in hal.interfaces:
                if (
                    interface.name is None
                    or interface.regex_instances
                ):
                    return None

                for instance in interface.instances:
                    if not instance:
                        return None

                    canonical_names.append(
                        f"{hal.name}."
                        f"{interface.name}/"
                        f"{instance}"
                    )

            for fqname in hal.fqnames:
                canonical_name = (
                    fqname
                    if fqname.startswith(
                        hal.name + "."
                    )
                    else (
                        f"{hal.name}."
                        f"{fqname}"
                    )
                )

                if "/" not in canonical_name:
                    return None

                canonical_names.append(
                    canonical_name
                )

        if not canonical_names:
            return None

        return tuple(
            sorted(
                set(
                    canonical_names
                )
            )
        )

    @classmethod
    def project(
        cls,
        *,
        reconstruction: AndroidReconstructionResult,
        config: AndroidDeviceTreeVintfBuildConfig,
        apk_modules: tuple[
            AndroidDeviceTreeApkAndroidMkModule,
            ...,
        ],
        apk_product_packages: tuple[str, ...],
    ) -> AndroidDeviceTreeVintfProductParticipationPlan:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            config,
            AndroidDeviceTreeVintfBuildConfig,
        ):
            raise TypeError(
                "config must be an "
                "AndroidDeviceTreeVintfBuildConfig"
            )

        if not isinstance(apk_modules, tuple):
            raise TypeError(
                "apk_modules must be a tuple"
            )

        if not all(
            isinstance(
                module,
                AndroidDeviceTreeApkAndroidMkModule,
            )
            for module in apk_modules
        ):
            raise TypeError(
                "apk_modules contains an invalid module"
            )

        if not isinstance(
            apk_product_packages,
            tuple,
        ):
            raise TypeError(
                "apk_product_packages must be a tuple"
            )

        build_representation_by_id = {
            representation.representation_id:
            representation
            for representation
            in reconstruction.artifact_build_representations
        }

        if len(
            build_representation_by_id
        ) != len(
            reconstruction.artifact_build_representations
        ):
            raise ValueError(
                "Reconstruction build representations must "
                "preserve unique identity"
            )

        apk_module_by_package_requirement_id = {}

        for module in apk_modules:
            build_representation = (
                build_representation_by_id.get(
                    module.representation_id
                )
            )

            if build_representation is None:
                raise ValueError(
                    "APK module has no exact Reconstruction "
                    "build representation: "
                    f"{module.representation_id}"
                )

            if (
                build_representation.kind
                is not
                AndroidReconstructionBuildRepresentationKind.PACKAGE
            ):
                raise ValueError(
                    "APK module does not preserve PACKAGE "
                    "build representation identity: "
                    f"{module.representation_id}"
                )

            package_requirement_id = (
                build_representation.source_identity
            )

            if (
                package_requirement_id
                in apk_module_by_package_requirement_id
            ):
                raise ValueError(
                    "multiple APK modules map to one canonical "
                    "package requirement: "
                    f"{package_requirement_id}"
                )

            apk_module_by_package_requirement_id[
                package_requirement_id
            ] = module

        apk_module_by_name = {
            module.module_name: module
            for module in apk_modules
        }

        if len(
            apk_module_by_name
        ) != len(
            apk_modules
        ):
            raise ValueError(
                "APK modules must preserve unique module identity"
            )

        unknown_apk_product_packages = (
            set(
                apk_product_packages
            )
            - set(
                apk_module_by_name
            )
        )

        if unknown_apk_product_packages:
            raise ValueError(
                "APK product participation references unknown "
                "generated modules: "
                f"{sorted(unknown_apk_product_packages)!r}"
            )

        vintf_representation_by_id = {
            representation.representation_id:
            representation
            for representation
            in reconstruction.vintf_document_representations
        }

        if len(
            vintf_representation_by_id
        ) != len(
            reconstruction.vintf_document_representations
        ):
            raise ValueError(
                "VINTF Reconstruction representations must "
                "preserve unique identity"
            )

        vintf_source_content_by_id = {
            content.content_id: content
            for content
            in reconstruction.vintf_source_contents
        }

        if len(
            vintf_source_content_by_id
        ) != len(
            reconstruction.vintf_source_contents
        ):
            raise ValueError(
                "VINTF source contents must preserve "
                "unique identity"
            )

        #
        # target representation
        #   -> canonical service identity
        #       -> (provider representation, relationship identity)
        #
        structural_providers = {}

        for composition in (
            reconstruction.composition_relationships
        ):
            relationship = composition.relationship

            if not isinstance(
                relationship,
                AndroidUniverseApkVintfStructuralProviderRelationship,
            ):
                continue

            if (
                relationship.status
                is not AndroidUniverseRelationshipStatus.RESOLVED
            ):
                continue

            if (
                composition.applicability.status
                is not AndroidUniverseApplicabilityStatus.ACTIVE
            ):
                continue

            provider_package_requirement_id = (
                relationship.apk_package.requirement_id
            )

            for target in composition.targets:
                target_representation_id = (
                    target.representation_id
                )

                if target_representation_id is None:
                    continue

                by_name = structural_providers.setdefault(
                    target_representation_id,
                    {},
                )

                by_name.setdefault(
                    relationship.canonical_name,
                    [],
                ).append(
                    (
                        provider_package_requirement_id,
                        relationship.relationship_id,
                    )
                )

        participating_apk_names = set(
            apk_product_packages
        )

        product_packages = []
        suppressions = []

        for module in config.fragment_modules:
            build_representation = (
                build_representation_by_id.get(
                    module.representation_id
                )
            )

            if build_representation is None:
                raise ValueError(
                    "VINTF fragment module has no exact "
                    "Reconstruction build representation: "
                    f"{module.representation_id}"
                )

            if (
                build_representation.kind
                is not
                AndroidReconstructionBuildRepresentationKind
                .VINTF_DOCUMENT
            ):
                raise ValueError(
                    "VINTF fragment module changed canonical "
                    "build role: "
                    f"{module.representation_id}"
                )

            source_content_id = (
                build_representation.source_content_id
            )

            if source_content_id is None:
                raise ValueError(
                    "VINTF fragment build representation "
                    "requires source_content_id: "
                    f"{module.representation_id}"
                )

            source_content = (
                vintf_source_content_by_id.get(
                    source_content_id
                )
            )

            if source_content is None:
                raise ValueError(
                    "VINTF fragment build representation has "
                    "no exact canonical source content: "
                    f"{source_content_id}"
                )

            vintf_representation_id = (
                source_content.representation_id
            )

            representation = (
                vintf_representation_by_id.get(
                    vintf_representation_id
                )
            )

            if representation is None:
                raise ValueError(
                    "VINTF source content has no exact "
                    "canonical VINTF representation: "
                    f"{vintf_representation_id}"
                )

            canonical_names = (
                cls._canonical_aidl_names(
                    representation.requirement
                )
            )

            #
            # Anything other than a pure, completely understood AIDL
            # manifest fragment remains installed.
            #
            if canonical_names is None:
                product_packages.append(
                    module.module_name
                )
                continue

            providers_by_name = (
                structural_providers.get(
                    vintf_representation_id,
                    {},
                )
            )

            provider_representation_ids = set()
            relationship_ids = set()

            suppress = True

            for canonical_name in canonical_names:
                providers = (
                    providers_by_name.get(
                        canonical_name,
                        ()
                    )
                )

                #
                # Partial relationship coverage is never sufficient to
                # suppress an entire VINTF fragment.
                #
                if not providers:
                    suppress = False
                    break

                for (
                    provider_package_requirement_id,
                    relationship_id,
                ) in providers:
                    provider_module = (
                        apk_module_by_package_requirement_id.get(
                            provider_package_requirement_id
                        )
                    )

                    #
                    # Device Tree cannot establish product exclusion for a
                    # provider that does not map to its canonical APK module.
                    #
                    if provider_module is None:
                        suppress = False
                        break

                    #
                    # A participating provider requires its VINTF declaration.
                    #
                    if (
                        provider_module.module_name
                        in participating_apk_names
                    ):
                        suppress = False
                        break

                    provider_representation_ids.add(
                        provider_module.representation_id
                    )
                    relationship_ids.add(
                        relationship_id
                    )

                if not suppress:
                    break

            if not suppress:
                product_packages.append(
                    module.module_name
                )
                continue

            suppressions.append(
                AndroidDeviceTreeVintfProductSuppression(
                    representation_id=(
                        module.representation_id
                    ),
                    module_name=(
                        module.module_name
                    ),
                    canonical_names=(
                        canonical_names
                    ),
                    provider_representation_ids=tuple(
                        sorted(
                            provider_representation_ids
                        )
                    ),
                    relationship_ids=tuple(
                        sorted(
                            relationship_ids
                        )
                    ),
                )
            )

        return AndroidDeviceTreeVintfProductParticipationPlan(
            product_packages=tuple(
                sorted(
                    set(
                        product_packages
                    )
                )
            ),
            suppressions=tuple(
                sorted(
                    suppressions,
                    key=lambda suppression: (
                        suppression.module_name,
                        suppression.representation_id,
                    ),
                )
            ),
        )
