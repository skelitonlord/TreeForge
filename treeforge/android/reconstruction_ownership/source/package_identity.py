from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from treeforge.android.parsing.apk.axml import (
    AndroidBinaryXmlError,
    AndroidBinaryXmlParser,
)

from treeforge.android.reconstruction_ownership.source.build_model import (
    AndroidSourceBuildModule,
    AndroidSourceBuildModuleInventory,
)


_ANDROID_NAMESPACE = (
    "http://schemas.android.com/apk/res/android"
)

_ANDROID_TARGET_PACKAGE = (
    f"{{{_ANDROID_NAMESPACE}}}targetPackage"
)


class AndroidSourcePackageIdentityOrigin(StrEnum):
    """
    Evidence form from which source package identity is established or sought.
    """

    PACKAGE_NAME_PROPERTY = "package_name_property"
    EXPLICIT_MANIFEST = "explicit_manifest"
    CONVENTIONAL_MANIFEST = "conventional_manifest"
    GENERATED_MANIFEST = "generated_manifest"
    PREBUILT_APK = "prebuilt_apk"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class AndroidSourcePackageIdentity:
    """
    Package-identity evidence for one APK-family source build module.

    package_name is the effective literal package identity TreeForge can prove
    without executing Soong.

    manifest_package_name preserves the literal package declaration from a
    source AndroidManifest.xml when one was directly inspectable.

    overlay_target_package preserves the literal RRO target package when one
    was directly inspectable.

    This object does not prove:
    - target-product consumption;
    - correspondence with an installed APK;
    - source availability for a factory artifact;
    - Reconstruction Ownership.
    """

    module: AndroidSourceBuildModule

    origin: AndroidSourcePackageIdentityOrigin

    package_name: str | None

    manifest_source_path: str | None = None
    manifest_package_name: str | None = None

    overlay_target_package: str | None = None

    prebuilt_apk_source_path: str | None = None

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.module,
            AndroidSourceBuildModule,
        ):
            raise TypeError(
                "module must be an "
                "AndroidSourceBuildModule"
            )

        if not isinstance(
            self.origin,
            AndroidSourcePackageIdentityOrigin,
        ):
            raise TypeError(
                "origin must be an "
                "AndroidSourcePackageIdentityOrigin"
            )

        for (
            field_name,
            value,
        ) in (
            (
                "package_name",
                self.package_name,
            ),
            (
                "manifest_source_path",
                self.manifest_source_path,
            ),
            (
                "manifest_package_name",
                self.manifest_package_name,
            ),
            (
                "overlay_target_package",
                self.overlay_target_package,
            ),
            (
                "prebuilt_apk_source_path",
                self.prebuilt_apk_source_path,
            ),
        ):
            if (
                value is not None
                and (
                    not isinstance(
                        value,
                        str,
                    )
                    or not value
                )
            ):
                raise ValueError(
                    f"{field_name} must be None "
                    "or a non-empty string"
                )

        for path in (
            self.manifest_source_path,
            self.prebuilt_apk_source_path,
        ):
            if path is None:
                continue

            if path.startswith(
                "/"
            ):
                raise ValueError(
                    "source evidence paths must be "
                    "checkout-relative"
                )

            if ".." in path.split(
                "/"
            ):
                raise ValueError(
                    "source evidence paths must not "
                    "contain traversal"
                )

        if (
            self.origin
            is AndroidSourcePackageIdentityOrigin
            .GENERATED_MANIFEST
            and self.manifest_source_path is not None
        ):
            raise ValueError(
                "generated manifest references must "
                "not be represented as filesystem paths"
            )

        if (
            self.origin
            is AndroidSourcePackageIdentityOrigin
            .PREBUILT_APK
            and self.prebuilt_apk_source_path is None
        ):
            raise ValueError(
                "PREBUILT_APK identity must preserve "
                "its source path"
            )

    @property
    def resolved(
        self,
    ) -> bool:
        return (
            self.package_name
            is not None
        )


@dataclass(frozen=True, slots=True)
class AndroidSourcePackageIdentityInventory:
    """
    Deterministic package-identity evidence for APK-family source modules.
    """

    module_inventory: AndroidSourceBuildModuleInventory

    identities: tuple[
        AndroidSourcePackageIdentity,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.module_inventory,
            AndroidSourceBuildModuleInventory,
        ):
            raise TypeError(
                "module_inventory must be an "
                "AndroidSourceBuildModuleInventory"
            )

        if (
            not isinstance(
                self.identities,
                tuple,
            )
            or not all(
                isinstance(
                    identity,
                    AndroidSourcePackageIdentity,
                )
                for identity in self.identities
            )
        ):
            raise TypeError(
                "identities must contain only "
                "AndroidSourcePackageIdentity values"
            )

        expected = tuple(
            sorted(
                self.identities,
                key=lambda identity: (
                    identity.module.name,
                    identity.module.repository.project_path,
                    identity.module.source_path,
                    identity.module.source_line,
                    identity.module.module_type,
                ),
            )
        )

        if self.identities != expected:
            raise ValueError(
                "identities must use deterministic ordering"
            )

        modules = (
            self.module_inventory.modules
        )

        module_ids = {
            id(module)
            for module in modules
        }

        seen = set()

        for identity in self.identities:
            if (
                id(identity.module)
                not in module_ids
            ):
                raise ValueError(
                    "package identity must preserve "
                    "exact module-inventory identity"
                )

            module_id = id(
                identity.module
            )

            if module_id in seen:
                raise ValueError(
                    "each source module may have at "
                    "most one package-identity record"
                )

            seen.add(
                module_id
            )

    def identities_for_package(
        self,
        package_name: str,
    ) -> tuple[
        AndroidSourcePackageIdentity,
        ...,
    ]:
        return tuple(
            identity
            for identity in self.identities
            if (
                identity.package_name
                == package_name
            )
        )

    @property
    def resolved_identities(
        self,
    ) -> tuple[
        AndroidSourcePackageIdentity,
        ...,
    ]:
        return tuple(
            identity
            for identity in self.identities
            if identity.resolved
        )

    @property
    def unresolved_identities(
        self,
    ) -> tuple[
        AndroidSourcePackageIdentity,
        ...,
    ]:
        return tuple(
            identity
            for identity in self.identities
            if not identity.resolved
        )


class AndroidSourcePackageIdentityIndexer:
    """
    Recover literal package identity for APK-family source build modules.

    This indexer does not execute Soong, resolve generated modules, inspect
    nested architecture-specific properties, or correlate source modules with
    installed factory artifacts.
    """

    _MODULE_TYPES = frozenset(
        (
            "android_app",
            "android_app_import",
            "runtime_resource_overlay",
        )
    )

    @classmethod
    def index(
        cls,
        inventory: AndroidSourceBuildModuleInventory,
    ) -> AndroidSourcePackageIdentityInventory:
        if not isinstance(
            inventory,
            AndroidSourceBuildModuleInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidSourceBuildModuleInventory"
            )

        result = []

        for module in inventory.modules:
            if (
                module.module_type
                not in cls._MODULE_TYPES
            ):
                continue

            result.append(
                cls._identity_for_module(
                    inventory=inventory,
                    module=module,
                )
            )

        identities = tuple(
            sorted(
                result,
                key=lambda identity: (
                    identity.module.name,
                    identity.module.repository.project_path,
                    identity.module.source_path,
                    identity.module.source_line,
                    identity.module.module_type,
                ),
            )
        )

        return AndroidSourcePackageIdentityInventory(
            module_inventory=inventory,
            identities=identities,
        )

    @classmethod
    def _identity_for_module(
        cls,
        *,
        inventory: AndroidSourceBuildModuleInventory,
        module: AndroidSourceBuildModule,
    ) -> AndroidSourcePackageIdentity:
        if (
            module.module_type
            == "android_app_import"
        ):
            return cls._prebuilt_identity(
                inventory=inventory,
                module=module,
            )

        package_override = (
            module.literal_string(
                "package_name"
            )
        )

        manifest_property = (
            module.literal_string(
                "manifest"
            )
        )

        if (
            manifest_property is not None
            and manifest_property.startswith(
                ":"
            )
        ):
            return AndroidSourcePackageIdentity(
                module=module,
                origin=(
                    AndroidSourcePackageIdentityOrigin
                    .PACKAGE_NAME_PROPERTY
                    if package_override is not None
                    else AndroidSourcePackageIdentityOrigin
                    .GENERATED_MANIFEST
                ),
                package_name=package_override,
            )

        if manifest_property is not None:
            manifest_path = (
                cls._module_relative_source_path(
                    module=module,
                    child=manifest_property,
                )
            )

            manifest_values = (
                cls._manifest_values(
                    inventory=inventory,
                    module=module,
                    source_path=manifest_path,
                )
                if manifest_path is not None
                else (
                    None,
                    None,
                )
            )

            (
                manifest_package,
                overlay_target,
            ) = manifest_values

            return AndroidSourcePackageIdentity(
                module=module,
                origin=(
                    AndroidSourcePackageIdentityOrigin
                    .PACKAGE_NAME_PROPERTY
                    if package_override is not None
                    else AndroidSourcePackageIdentityOrigin
                    .EXPLICIT_MANIFEST
                ),
                package_name=(
                    package_override
                    if package_override is not None
                    else manifest_package
                ),
                manifest_source_path=manifest_path,
                manifest_package_name=manifest_package,
                overlay_target_package=overlay_target,
            )

        conventional = (
            cls._module_relative_source_path(
                module=module,
                child="AndroidManifest.xml",
            )
        )

        if conventional is not None:
            physical = (
                inventory
                .repository_inventory
                .checkout_root
                / conventional
            )

            if physical.is_file():
                (
                    manifest_package,
                    overlay_target,
                ) = cls._manifest_values(
                    inventory=inventory,
                    module=module,
                    source_path=conventional,
                )

                return AndroidSourcePackageIdentity(
                    module=module,
                    origin=(
                        AndroidSourcePackageIdentityOrigin
                        .PACKAGE_NAME_PROPERTY
                        if package_override is not None
                        else AndroidSourcePackageIdentityOrigin
                        .CONVENTIONAL_MANIFEST
                    ),
                    package_name=(
                        package_override
                        if package_override is not None
                        else manifest_package
                    ),
                    manifest_source_path=conventional,
                    manifest_package_name=manifest_package,
                    overlay_target_package=overlay_target,
                )

        if package_override is not None:
            return AndroidSourcePackageIdentity(
                module=module,
                origin=(
                    AndroidSourcePackageIdentityOrigin
                    .PACKAGE_NAME_PROPERTY
                ),
                package_name=package_override,
            )

        return AndroidSourcePackageIdentity(
            module=module,
            origin=(
                AndroidSourcePackageIdentityOrigin
                .NONE
            ),
            package_name=None,
        )

    @classmethod
    def _prebuilt_identity(
        cls,
        *,
        inventory: AndroidSourceBuildModuleInventory,
        module: AndroidSourceBuildModule,
    ) -> AndroidSourcePackageIdentity:
        apk = module.literal_string(
            "apk"
        )

        if apk is None:
            return AndroidSourcePackageIdentity(
                module=module,
                origin=(
                    AndroidSourcePackageIdentityOrigin
                    .NONE
                ),
                package_name=None,
            )

        source_path = (
            cls._module_relative_source_path(
                module=module,
                child=apk,
            )
        )

        if source_path is None:
            return AndroidSourcePackageIdentity(
                module=module,
                origin=(
                    AndroidSourcePackageIdentityOrigin
                    .NONE
                ),
                package_name=None,
            )

        package_name = (
            cls._prebuilt_apk_package_name(
                inventory=inventory,
                module=module,
                source_path=source_path,
            )
        )

        return AndroidSourcePackageIdentity(
            module=module,
            origin=(
                AndroidSourcePackageIdentityOrigin
                .PREBUILT_APK
            ),
            package_name=package_name,
            prebuilt_apk_source_path=source_path,
        )

    @classmethod
    def _prebuilt_apk_package_name(
        cls,
        *,
        inventory: AndroidSourceBuildModuleInventory,
        module: AndroidSourceBuildModule,
        source_path: str,
    ) -> str | None:
        """
        Recover literal package identity from an exact source prebuilt APK.

        The APK itself remains source-side evidence.  This helper reuses only
        TreeForge's generic Android binary-XML decoder and does not construct
        factory Parsing models or reinterpret the source APK as an installed
        factory artifact.
        """

        owner = (
            inventory
            .repository_inventory
            .repository_for_source_path(
                source_path
            )
        )

        if owner is not module.repository:
            return None

        physical = (
            inventory
            .repository_inventory
            .checkout_root
            / source_path
        )

        if not physical.is_file():
            return None

        try:
            with ZipFile(
                physical,
                "r",
            ) as archive:
                try:
                    raw_manifest = archive.read(
                        "AndroidManifest.xml"
                    )
                except KeyError:
                    return None

        except (
            BadZipFile,
            OSError,
        ):
            return None

        try:
            document = (
                AndroidBinaryXmlParser()
                .parse(
                    raw_manifest
                )
            )

        except AndroidBinaryXmlError:
            return None

        manifest = next(
            (
                element
                for element in document.elements
                if element.name == "manifest"
            ),
            None,
        )

        if manifest is None:
            return None

        package_attribute = next(
            (
                attribute
                for attribute in manifest.attributes
                if (
                    attribute.name == "package"
                    and attribute.namespace is None
                )
            ),
            None,
        )

        if (
            package_attribute is None
            or not isinstance(
                package_attribute.literal,
                str,
            )
            or not package_attribute.literal
        ):
            return None

        return package_attribute.literal

    @classmethod
    def _manifest_values(
        cls,
        *,
        inventory: AndroidSourceBuildModuleInventory,
        module: AndroidSourceBuildModule,
        source_path: str,
    ) -> tuple[
        str | None,
        str | None,
    ]:
        owner = (
            inventory
            .repository_inventory
            .repository_for_source_path(
                source_path
            )
        )

        if owner is not module.repository:
            return (
                None,
                None,
            )

        physical = (
            inventory
            .repository_inventory
            .checkout_root
            / source_path
        )

        if not physical.is_file():
            return (
                None,
                None,
            )

        try:
            root = ElementTree.parse(
                physical
            ).getroot()
        except (
            ElementTree.ParseError,
            OSError,
        ):
            return (
                None,
                None,
            )

        manifest_package = (
            cls._literal_manifest_value(
                root.attrib.get(
                    "package"
                )
            )
        )

        overlay_target = None

        for child in root:
            if cls._local_name(
                child.tag
            ) != "overlay":
                continue

            overlay_target = (
                cls._literal_manifest_value(
                    child.attrib.get(
                        _ANDROID_TARGET_PACKAGE
                    )
                )
            )

            if overlay_target is not None:
                break

        return (
            manifest_package,
            overlay_target,
        )

    @staticmethod
    def _module_relative_source_path(
        *,
        module: AndroidSourceBuildModule,
        child: str,
    ) -> str | None:
        if (
            not isinstance(
                child,
                str,
            )
            or not child
            or child.startswith(
                "/"
            )
            or child.startswith(
                ":"
            )
        ):
            return None

        module_directory = (
            PurePosixPath(
                module.source_path
            ).parent
        )

        candidate = (
            module_directory
            / child
        )

        parts = []

        for part in candidate.parts:
            if part in (
                "",
                ".",
            ):
                continue

            if part == "..":
                if not parts:
                    return None

                parts.pop()
                continue

            parts.append(
                part
            )

        if not parts:
            return None

        return PurePosixPath(
            *parts
        ).as_posix()

    @staticmethod
    def _literal_manifest_value(
        value: str | None,
    ) -> str | None:
        if (
            not isinstance(
                value,
                str,
            )
            or not value
        ):
            return None

        if (
            "${" in value
            or "$(" in value
        ):
            return None

        return value

    @staticmethod
    def _local_name(
        tag: str,
    ) -> str:
        return tag.rsplit(
            "}",
            1,
        )[-1]
