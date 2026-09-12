from __future__ import annotations

from treeforge.android.parsing.filesystem.model import (
    ParsedAndroidVintfSource,
)
from treeforge.android.parsing.vintf import (
    VintfXmlElement,
)
from treeforge.android.universe.vintf.avb import (
    AndroidUniverseVintfAvbRequirement,
)
from treeforge.android.universe.vintf.document import (
    AndroidUniverseVintfDocumentKind,
    AndroidUniverseVintfDocumentSemantics,
    AndroidUniverseVintfDocumentSide,
    AndroidUniverseVintfUninterpretedAttribute,
    AndroidUniverseVintfUninterpretedElement,
)
from treeforge.android.universe.vintf.hal import (
    AndroidUniverseVintfHalFormat,
    AndroidUniverseVintfHalInterface,
    AndroidUniverseVintfHalRequirement,
    AndroidUniverseVintfHalTransport,
)
from treeforge.android.universe.vintf.kernel import (
    AndroidUniverseVintfKernelCondition,
    AndroidUniverseVintfKernelConfigRequirement,
    AndroidUniverseVintfKernelRequirement,
)
from treeforge.android.universe.vintf.requirement import (
    AndroidUniverseVintfDocumentRequirement,
)
from treeforge.android.universe.vintf.sepolicy import (
    AndroidUniverseVintfSepolicyRequirement,
)
from treeforge.android.universe.vintf.system_sdk import (
    AndroidUniverseVintfSystemSdkRequirement,
)


class AndroidUniverseVintfInterpreter:
    """
    Interpret faithful VINTF Parsing output into canonical Universe
    requirements.

    Known Android semantics are normalized without changing Parsing identity.
    Unknown future XML constructs remain explicit coverage debt.
    """

    _KNOWN_ELEMENTS = frozenset(
        {
            "manifest",
            "compatibility-matrix",
            "hal",
            "name",
            "version",
            "transport",
            "fqname",
            "interface",
            "instance",
            "regex-instance",
            "kernel",
            "config",
            "conditions",
            "key",
            "value",
            "sepolicy",
            "kernel-sepolicy-version",
            "sepolicy-version",
            "system-sdk",
            "avb",
            "vbmeta-version",
        }
    )

    _KNOWN_ATTRIBUTES = {
        "manifest": frozenset(
            {
                "version",
                "type",
                "target-level",
            }
        ),
        "compatibility-matrix": (
            frozenset(
                {
                    "version",
                    "type",
                    "level",
                }
            )
        ),
        "hal": frozenset(
            {
                "format",
                "optional",
                "min-level",
                "max-level",
                "updatable-via-apex",
            }
        ),
        "transport": frozenset(
            {
                "arch",
            }
        ),
        "kernel": frozenset(
            {
                "version",
                "level",
            }
        ),
        "value": frozenset(
            {
                "type",
            }
        ),
    }

    def interpret(
        self,
        sources: tuple[
            ParsedAndroidVintfSource,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseVintfDocumentRequirement,
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
                ParsedAndroidVintfSource,
            )
            for source in sources
        ):
            raise TypeError(
                "sources must contain only "
                "ParsedAndroidVintfSource instances"
            )

        return tuple(
            self._interpret_source(
                source
            )
            for source in sources
        )

    def _interpret_source(
        self,
        source: ParsedAndroidVintfSource,
    ) -> AndroidUniverseVintfDocumentRequirement:
        root = source.parsed.root

        kind = self._document_kind(
            root
        )

        side = self._document_side(
            root
        )

        meta_version = (
            self._required_attribute(
                root,
                "version",
            )
        )

        uninterpreted_elements: list[
            AndroidUniverseVintfUninterpretedElement
        ] = []

        uninterpreted_attributes: list[
            AndroidUniverseVintfUninterpretedAttribute
        ] = []

        self._collect_uninterpreted(
            root,
            elements=(
                uninterpreted_elements
            ),
            attributes=(
                uninterpreted_attributes
            ),
        )

        semantics = (
            AndroidUniverseVintfDocumentSemantics(
                kind=kind,
                side=side,
                meta_version=meta_version,
                level=root.attribute(
                    "level"
                ),
                target_level=(
                    root.attribute(
                        "target-level"
                    )
                ),
                hals=tuple(
                    self._interpret_hal(
                        child
                    )
                    for child
                    in self._children_named(
                        root,
                        "hal",
                    )
                ),
                kernels=tuple(
                    self._interpret_kernel(
                        child
                    )
                    for child
                    in self._children_named(
                        root,
                        "kernel",
                    )
                ),
                sepolicy=tuple(
                    self._interpret_sepolicy(
                        child
                    )
                    for child
                    in self._children_named(
                        root,
                        "sepolicy",
                    )
                ),
                system_sdk=tuple(
                    self._interpret_system_sdk(
                        child
                    )
                    for child
                    in self._children_named(
                        root,
                        "system-sdk",
                    )
                ),
                avb=tuple(
                    self._interpret_avb(
                        child
                    )
                    for child
                    in self._children_named(
                        root,
                        "avb",
                    )
                ),
                uninterpreted_elements=tuple(
                    uninterpreted_elements
                ),
                uninterpreted_attributes=tuple(
                    uninterpreted_attributes
                ),
            )
        )

        return (
            AndroidUniverseVintfDocumentRequirement(
                source=source,
                semantics=semantics,
            )
        )

    def _interpret_hal(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfHalRequirement:
        raw_format = (
            self._required_attribute(
                element,
                "format",
            )
        )

        try:
            hal_format = (
                AndroidUniverseVintfHalFormat(
                    raw_format
                )
            )
        except ValueError as exc:
            raise ValueError(
                "Unsupported VINTF HAL "
                f"format: {raw_format!r}"
            ) from exc

        name = self._required_child_text(
            element,
            "name",
        )

        return AndroidUniverseVintfHalRequirement(
            name=name,
            format=hal_format,
            versions=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "version",
                )
            ),
            interfaces=tuple(
                self._interpret_interface(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "interface",
                )
            ),
            fqnames=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "fqname",
                )
            ),
            transports=tuple(
                self._interpret_transport(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "transport",
                )
            ),
            optional=self._optional_boolean_attribute(
                element,
                "optional",
            ),
            min_level=element.attribute(
                "min-level"
            ),
            max_level=element.attribute(
                "max-level"
            ),
            updatable_via_apex=(
                self._optional_boolean_attribute(
                    element,
                    "updatable-via-apex",
                )
            ),
            element=element,
        )

    def _interpret_interface(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfHalInterface:
        name_element = (
            self._first_child_named(
                element,
                "name",
            )
        )

        name = (
            self._element_text(
                name_element
            )
            if name_element is not None
            else None
        )

        return AndroidUniverseVintfHalInterface(
            name=name,
            instances=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "instance",
                )
            ),
            regex_instances=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "regex-instance",
                )
            ),
            element=element,
        )

    def _interpret_transport(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfHalTransport:
        return AndroidUniverseVintfHalTransport(
            kind=self._element_text(
                element
            ),
            arch=element.attribute(
                "arch"
            ),
            element=element,
        )

    def _interpret_kernel(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfKernelRequirement:
        return AndroidUniverseVintfKernelRequirement(
            version=element.attribute(
                "version"
            ),
            level=element.attribute(
                "level"
            ),
            configs=tuple(
                self._interpret_kernel_config(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "config",
                )
            ),
            conditions=tuple(
                self._interpret_kernel_condition(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "conditions",
                )
            ),
            element=element,
        )

    def _interpret_kernel_condition(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfKernelCondition:
        return AndroidUniverseVintfKernelCondition(
            configs=tuple(
                self._interpret_kernel_config(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "config",
                )
            ),
            element=element,
        )

    def _interpret_kernel_config(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfKernelConfigRequirement:
        key = self._required_child_text(
            element,
            "key",
        )

        value_element = (
            self._required_child(
                element,
                "value",
            )
        )

        value_type = (
            self._required_attribute(
                value_element,
                "type",
            )
        )

        return AndroidUniverseVintfKernelConfigRequirement(
            key=key,
            value=self._element_text(
                value_element
            ),
            value_type=value_type,
            element=element,
        )

    def _interpret_sepolicy(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfSepolicyRequirement:
        kernel_version_element = (
            self._first_child_named(
                element,
                "kernel-sepolicy-version",
            )
        )

        return AndroidUniverseVintfSepolicyRequirement(
            versions=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "version",
                )
            ),
            sepolicy_versions=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "sepolicy-version",
                )
            ),
            kernel_sepolicy_version=(
                self._element_text(
                    kernel_version_element
                )
                if kernel_version_element
                is not None
                else None
            ),
            element=element,
        )

    def _interpret_system_sdk(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfSystemSdkRequirement:
        return AndroidUniverseVintfSystemSdkRequirement(
            versions=tuple(
                self._element_text(
                    child
                )
                for child
                in self._children_named(
                    element,
                    "version",
                )
            ),
            element=element,
        )

    def _interpret_avb(
        self,
        element: VintfXmlElement,
    ) -> AndroidUniverseVintfAvbRequirement:
        version_element = (
            self._first_child_named(
                element,
                "vbmeta-version",
            )
        )

        return AndroidUniverseVintfAvbRequirement(
            vbmeta_version=(
                self._element_text(
                    version_element
                )
                if version_element
                is not None
                else None
            ),
            element=element,
        )

    def _document_kind(
        self,
        root: VintfXmlElement,
    ) -> AndroidUniverseVintfDocumentKind:
        try:
            return AndroidUniverseVintfDocumentKind(
                root.local_name
            )
        except ValueError as exc:
            raise ValueError(
                "Unsupported VINTF root element: "
                f"{root.local_name!r}"
            ) from exc

    def _document_side(
        self,
        root: VintfXmlElement,
    ) -> AndroidUniverseVintfDocumentSide:
        value = self._required_attribute(
            root,
            "type",
        )

        try:
            return AndroidUniverseVintfDocumentSide(
                value
            )
        except ValueError as exc:
            raise ValueError(
                "Unsupported VINTF document type: "
                f"{value!r}"
            ) from exc

    def _collect_uninterpreted(
        self,
        element: VintfXmlElement,
        *,
        elements: list[
            AndroidUniverseVintfUninterpretedElement
        ],
        attributes: list[
            AndroidUniverseVintfUninterpretedAttribute
        ],
    ) -> None:
        local_name = (
            element.local_name
        )

        if (
            local_name
            not in self._KNOWN_ELEMENTS
        ):
            elements.append(
                AndroidUniverseVintfUninterpretedElement(
                    element=element
                )
            )

        known_attributes = (
            self._KNOWN_ATTRIBUTES.get(
                local_name,
                frozenset(),
            )
        )

        for attribute in element.attributes:
            if (
                attribute.name
                not in known_attributes
            ):
                attributes.append(
                    AndroidUniverseVintfUninterpretedAttribute(
                        element=element,
                        attribute=attribute,
                    )
                )

        for child in element.children:
            self._collect_uninterpreted(
                child,
                elements=elements,
                attributes=attributes,
            )

    @staticmethod
    def _children_named(
        element: VintfXmlElement,
        name: str,
    ) -> tuple[
        VintfXmlElement,
        ...,
    ]:
        return tuple(
            child
            for child in element.children
            if child.local_name == name
        )

    @classmethod
    def _first_child_named(
        cls,
        element: VintfXmlElement,
        name: str,
    ) -> VintfXmlElement | None:
        children = cls._children_named(
            element,
            name,
        )

        return (
            children[0]
            if children
            else None
        )

    @classmethod
    def _required_child(
        cls,
        element: VintfXmlElement,
        name: str,
    ) -> VintfXmlElement:
        child = cls._first_child_named(
            element,
            name,
        )

        if child is None:
            raise ValueError(
                "VINTF element "
                f"{element.local_name!r} "
                f"requires child {name!r}"
            )

        return child

    @classmethod
    def _required_child_text(
        cls,
        element: VintfXmlElement,
        name: str,
    ) -> str:
        return cls._element_text(
            cls._required_child(
                element,
                name,
            )
        )

    @staticmethod
    def _required_attribute(
        element: VintfXmlElement,
        name: str,
    ) -> str:
        value = element.attribute(
            name
        )

        if value is None:
            raise ValueError(
                "VINTF element "
                f"{element.local_name!r} "
                f"requires attribute {name!r}"
            )

        return value

    @classmethod
    def _optional_boolean_attribute(
        cls,
        element: VintfXmlElement,
        name: str,
    ) -> bool | None:
        value = element.attribute(
            name
        )

        if value is None:
            return None

        normalized = (
            value.strip().lower()
        )

        if normalized == "true":
            return True

        if normalized == "false":
            return False

        raise ValueError(
            "VINTF boolean attribute "
            f"{name!r} has unsupported "
            f"value {value!r}"
        )

    @staticmethod
    def _element_text(
        element: VintfXmlElement,
    ) -> str:
        if element.text is None:
            raise ValueError(
                "VINTF element "
                f"{element.local_name!r} "
                "requires text"
            )

        value = element.text.strip()

        if not value:
            raise ValueError(
                "VINTF element "
                f"{element.local_name!r} "
                "requires non-empty text"
            )

        return value