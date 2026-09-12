from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.result import (
    AndroidParsingResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidBootstrapRecoveryUsbIdentity:
    """
    Canonical Recovery USB identity projected from Parsing evidence.

    This model is intentionally independent of the Recovery partition
    manifest.

    The exact AndroidParsingResult object is retained so Recovery USB
    realization cannot silently detach from the canonical Parsing
    handoff.
    """

    parsing: AndroidParsingResult

    vendor_id: str
    adb_product_id: str
    fastboot_product_id: str
    controller: str

    manufacturer: str
    product_model: str

    max_power: str
    adb_configuration: str
    unbind_value: str

    schema_version: int = 1

    @staticmethod
    def _validate_usb_id(
        value: str,
        *,
        field_name: str,
    ) -> None:
        if (
            not isinstance(
                value,
                str,
            )
            or not value
        ):
            raise ValueError(
                f"{field_name} must be a non-empty string"
            )

        if len(value) != 4:
            raise ValueError(
                f"{field_name} must contain exactly four "
                "hexadecimal digits"
            )

        if any(
            character not in "0123456789abcdefABCDEF"
            for character in value
        ):
            raise ValueError(
                f"{field_name} contains a non-hexadecimal digit"
            )

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        if self.schema_version != 1:
            raise ValueError(
                "unsupported Recovery USB identity schema"
            )

        self._validate_usb_id(
            self.vendor_id,
            field_name="vendor_id",
        )

        self._validate_usb_id(
            self.adb_product_id,
            field_name="adb_product_id",
        )

        self._validate_usb_id(
            self.fastboot_product_id,
            field_name="fastboot_product_id",
        )

        if (
            not isinstance(
                self.controller,
                str,
            )
            or not self.controller
        ):
            raise ValueError(
                "controller must be a non-empty string"
            )

        for field_name, value in (
            (
                "manufacturer",
                self.manufacturer,
            ),
            (
                "product_model",
                self.product_model,
            ),
            (
                "max_power",
                self.max_power,
            ),
            (
                "adb_configuration",
                self.adb_configuration,
            ),
            (
                "unbind_value",
                self.unbind_value,
            ),
        ):
            if (
                not isinstance(
                    value,
                    str,
                )
                or not value
            ):
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        for field_name, value in (
            (
                "vendor_id",
                self.vendor_id,
            ),
            (
                "adb_product_id",
                self.adb_product_id,
            ),
            (
                "fastboot_product_id",
                self.fastboot_product_id,
            ),
            (
                "controller",
                self.controller,
            ),
            (
                "manufacturer",
                self.manufacturer,
            ),
            (
                "product_model",
                self.product_model,
            ),
            (
                "max_power",
                self.max_power,
            ),
            (
                "adb_configuration",
                self.adb_configuration,
            ),
            (
                "unbind_value",
                self.unbind_value,
            ),
        ):
            if (
                "\x00" in value
                or "\n" in value
                or "\r" in value
            ):
                raise ValueError(
                    f"{field_name} contains an invalid control "
                    "character"
                )


class AndroidBootstrapRecoveryUsbIdentityBuilder:
    """
    Derive Recovery USB identity strictly from canonical Parsing data.

    No device-name registry or hardcoded USB identity exists here.
    """

    _VENDOR_ID_PROPERTY = (
        "ro.recovery.usb.vid"
    )

    _ADB_PRODUCT_ID_PROPERTY = (
        "ro.recovery.usb.adb.pid"
    )

    _FASTBOOT_PRODUCT_ID_PROPERTY = (
        "ro.recovery.usb.fastboot.pid"
    )

    _CONTROLLER_PROPERTY = (
        "sys.usb.controller"
    )

    _UDC_PATH = (
        "/config/usb_gadget/g1/UDC"
    )

    _MAX_POWER_PATH = (
        "/config/usb_gadget/g1/configs/b.1/MaxPower"
    )

    _ADB_CONFIGURATION_PATH = (
        "/config/usb_gadget/g1/configs/b.1/"
        "strings/0x409/configuration"
    )

    _ADB_CONFIGURATION_TRIGGER_TERMS = (
        "property:sys.usb.config=adb",
        "property:sys.usb.ffs.ready=1",
        "property:sys.usb.configfs=1",
    )

    _UNBIND_TRIGGER_TERMS = (
        "property:sys.usb.config=none",
        "property:sys.usb.configfs=1",
    )

    _PRODUCT_PROPERTY_SOURCE_ORDER = (
        "ro.product.property_source_order"
    )

    _ALLOWED_PRODUCT_PROPERTY_SOURCES = frozenset(
        {
            "odm",
            "product",
            "system_ext",
            "system",
            "vendor",
        }
    )

    _DEFAULT_PRODUCT_PROPERTY_SOURCE_ORDER = (
        "product",
        "odm",
        "vendor",
        "system_ext",
        "system",
    )

    @staticmethod
    def _optional_canonical_property_value(
        parsing: AndroidParsingResult,
        key: str,
    ) -> str | None:
        values = tuple(
            dict.fromkeys(
                declaration.value
                for property_file
                in parsing.filesystem.property_files
                for declaration
                in property_file.declarations
                if (
                    declaration.key == key
                    and declaration.value
                )
            )
        )

        if len(values) > 1:
            raise ValueError(
                "Recovery USB identity requires concordant "
                f"canonical property evidence for {key!r}; "
                f"found {values!r}"
            )

        if not values:
            return None

        return values[0]

    @classmethod
    def _product_property_source_order(
        cls,
        parsing: AndroidParsingResult,
    ) -> tuple[str, ...]:
        configured = (
            cls._optional_canonical_property_value(
                parsing,
                cls._PRODUCT_PROPERTY_SOURCE_ORDER,
            )
        )

        if not configured:
            return (
                cls._DEFAULT_PRODUCT_PROPERTY_SOURCE_ORDER
            )

        sources = tuple(
            configured.split(",")
        )

        if any(
            source
            not in cls._ALLOWED_PRODUCT_PROPERTY_SOURCES
            for source in sources
        ):
            # Android init treats any unexpected source as an
            # invalid configured order and falls back to the
            # default source order.
            return (
                cls._DEFAULT_PRODUCT_PROPERTY_SOURCE_ORDER
            )

        return sources

    @classmethod
    def _derived_product_property_value(
        cls,
        parsing: AndroidParsingResult,
        property_name: str,
    ) -> str:
        base_key = (
            "ro.product."
            + property_name
        )

        explicit = (
            cls._optional_canonical_property_value(
                parsing,
                base_key,
            )
        )

        if explicit:
            return explicit

        for source in (
            cls._product_property_source_order(
                parsing
            )
        ):
            scoped_key = (
                "ro.product."
                + source
                + "."
                + property_name
            )

            value = (
                cls._optional_canonical_property_value(
                    parsing,
                    scoped_key,
                )
            )

            if value:
                return value

        raise ValueError(
            "Recovery USB identity could not derive "
            f"{base_key!r} from canonical Parsing evidence"
        )

    @classmethod
    def _canonical_init_write_value(
        cls,
        parsing: AndroidParsingResult,
        path: str,
        *,
        required_trigger_terms: tuple[str, ...] = (),
    ) -> str:
        values = []

        for source in parsing.filesystem.init_files:
            for action in source.actions:
                trigger = action.trigger or ""

                if any(
                    term not in trigger
                    for term in required_trigger_terms
                ):
                    continue

                for command in action.commands:
                    if (
                        command.keyword == "write"
                        and len(command.arguments) == 2
                        and command.arguments[0] == path
                        and command.arguments[1]
                    ):
                        values.append(
                            command.arguments[1]
                        )

        concordant = tuple(
            dict.fromkeys(values)
        )

        if len(concordant) != 1:
            raise ValueError(
                "Recovery USB identity requires exactly one "
                "concordant canonical INIT write value for "
                f"{path!r}; found {concordant!r}"
            )

        return concordant[0]

    @staticmethod
    def _canonical_property_value(
        parsing: AndroidParsingResult,
        key: str,
    ) -> str:
        declarations = tuple(
            declaration
            for property_file
            in parsing.filesystem.property_files
            for declaration
            in property_file.declarations
            if declaration.key == key
        )

        values = tuple(
            dict.fromkeys(
                declaration.value
                for declaration
                in declarations
                if declaration.value
            )
        )

        if len(values) != 1:
            raise ValueError(
                "Recovery USB identity requires exactly one "
                f"concordant canonical property value for {key!r}; "
                f"found {values!r}"
            )

        return values[0]

    @staticmethod
    def _canonical_init_setprop_value(
        parsing: AndroidParsingResult,
        key: str,
    ) -> str:
        commands = tuple(
            command
            for source
            in parsing.filesystem.init_files
            for action
            in source.actions
            for command
            in action.commands
            if (
                command.keyword == "setprop"
                and len(
                    command.arguments
                ) == 2
                and command.arguments[0] == key
            )
        )

        values = tuple(
            dict.fromkeys(
                command.arguments[1]
                for command in commands
                if command.arguments[1]
            )
        )

        if len(values) != 1:
            raise ValueError(
                "Recovery USB identity requires exactly one "
                "concordant canonical INIT setprop value for "
                f"{key!r}; found {values!r}"
            )

        return values[0]

    @classmethod
    def build(
        cls,
        parsing: AndroidParsingResult,
    ) -> AndroidBootstrapRecoveryUsbIdentity:
        if not isinstance(
            parsing,
            AndroidParsingResult,
        ):
            raise TypeError(
                "parsing must be an AndroidParsingResult"
            )

        identity = (
            AndroidBootstrapRecoveryUsbIdentity(
                parsing=parsing,
                vendor_id=(
                    cls._canonical_property_value(
                        parsing,
                        cls._VENDOR_ID_PROPERTY,
                    )
                ),
                adb_product_id=(
                    cls._canonical_property_value(
                        parsing,
                        cls._ADB_PRODUCT_ID_PROPERTY,
                    )
                ),
                fastboot_product_id=(
                    cls._canonical_property_value(
                        parsing,
                        cls._FASTBOOT_PRODUCT_ID_PROPERTY,
                    )
                ),
                controller=(
                    cls._canonical_init_setprop_value(
                        parsing,
                        cls._CONTROLLER_PROPERTY,
                    )
                ),
                manufacturer=(
                    cls._derived_product_property_value(
                        parsing,
                        "manufacturer",
                    )
                ),
                product_model=(
                    cls._derived_product_property_value(
                        parsing,
                        "model",
                    )
                ),
                max_power=(
                    cls._canonical_init_write_value(
                        parsing,
                        cls._MAX_POWER_PATH,
                    )
                ),
                adb_configuration=(
                    cls._canonical_init_write_value(
                        parsing,
                        cls._ADB_CONFIGURATION_PATH,
                        required_trigger_terms=(
                            cls._ADB_CONFIGURATION_TRIGGER_TERMS
                        ),
                    )
                ),
                unbind_value=(
                    cls._canonical_init_write_value(
                        parsing,
                        cls._UDC_PATH,
                        required_trigger_terms=(
                            cls._UNBIND_TRIGGER_TERMS
                        ),
                    )
                ),
            )
        )

        if identity.parsing is not parsing:
            raise RuntimeError(
                "Recovery USB identity projection lost exact "
                "canonical Parsing identity"
            )

        return identity


def _c_string(
    value: str,
) -> str:
    encoded = value.encode(
        "utf-8",
    )

    pieces = []

    for byte in encoded:
        if byte == 0x22:
            pieces.append(
                r'\"'
            )
        elif byte == 0x5C:
            pieces.append(
                r'\\'
            )
        elif 0x20 <= byte <= 0x7E:
            pieces.append(
                chr(byte)
            )
        else:
            pieces.append(
                f"\\{byte:03o}"
            )

    return (
        '"'
        + "".join(
            pieces
        )
        + '"'
    )


def render_recovery_usb_identity_c(
    identity: AndroidBootstrapRecoveryUsbIdentity,
) -> str:
    """
    Render only the canonical values required by Recovery's
    kernel-facing USB gadget lifecycle.
    """

    if not isinstance(
        identity,
        AndroidBootstrapRecoveryUsbIdentity,
    ):
        raise TypeError(
            "identity must be an "
            "AndroidBootstrapRecoveryUsbIdentity"
        )

    return (
        "#define TREEFORGE_RECOVERY_USB_VENDOR_ID "
        + _c_string(
            "0x" + identity.vendor_id
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_ADB_PRODUCT_ID "
        + _c_string(
            "0x" + identity.adb_product_id
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_FASTBOOT_PRODUCT_ID "
        + _c_string(
            "0x" + identity.fastboot_product_id
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_CONTROLLER "
        + _c_string(
            identity.controller
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_MANUFACTURER "
        + _c_string(
            identity.manufacturer
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_PRODUCT "
        + _c_string(
            identity.product_model
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_MAX_POWER "
        + _c_string(
            identity.max_power
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_ADB_CONFIGURATION "
        + _c_string(
            identity.adb_configuration
        )
        + "\n"
        + "#define TREEFORGE_RECOVERY_USB_UNBIND_VALUE "
        + _c_string(
            identity.unbind_value
        )
        + "\n"
    )


__all__ = (
    "AndroidBootstrapRecoveryUsbIdentity",
    "AndroidBootstrapRecoveryUsbIdentityBuilder",
    "render_recovery_usb_identity_c",
)
