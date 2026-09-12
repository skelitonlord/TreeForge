from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import re
import xml.sax
from xml.sax.handler import ContentHandler

from treeforge.android.parsing.selinux.model import (
    AndroidSelinuxMacPermissionsAttribute,
    AndroidSelinuxMacPermissionsElement,
)


_XML_ENCODING_PATTERN = re.compile(
    br"<\?xml[^>]*\bencoding\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


def decode_mac_permissions_xml(
    raw_bytes: bytes,
) -> str:
    """
    Decode one XML document according to its declared XML encoding.

    Exact bytes remain canonical independently of this decoded observation.
    """

    if not isinstance(raw_bytes, bytes):
        raise TypeError(
            "raw_bytes must be bytes"
        )

    probe = raw_bytes[:512]

    match = _XML_ENCODING_PATTERN.search(
        probe
    )

    if match is not None:
        encoding = (
            match.group(1)
            .decode(
                "ascii",
                errors="strict",
            )
        )
    elif raw_bytes.startswith(
        b"\xef\xbb\xbf"
    ):
        encoding = "utf-8-sig"
    else:
        encoding = "utf-8"

    return raw_bytes.decode(
        encoding,
        errors="strict",
    )


@dataclass(slots=True)
class _MutableElement:
    name: str
    attributes: tuple[
        AndroidSelinuxMacPermissionsAttribute,
        ...
    ]
    source_path: Path
    source_line: int

    children: list[
        AndroidSelinuxMacPermissionsElement
    ]
    text_parts: list[str]


class _MacPermissionsHandler(
    ContentHandler,
):
    def __init__(
        self,
        *,
        source_path: Path,
    ) -> None:
        super().__init__()

        self.source_path = source_path
        self.locator = None

        self.stack: list[
            _MutableElement
        ] = []

        self.root: (
            AndroidSelinuxMacPermissionsElement
            | None
        ) = None

    def setDocumentLocator(
        self,
        locator,
    ) -> None:
        self.locator = locator

    def startElement(
        self,
        name,
        attrs,
    ) -> None:
        source_line = (
            self.locator.getLineNumber()
            if self.locator is not None
            else 0
        )

        attributes = tuple(
            AndroidSelinuxMacPermissionsAttribute(
                name=attribute_name,
                value=attrs.getValue(
                    attribute_name
                ),
            )
            for attribute_name
            in attrs.getNames()
        )

        self.stack.append(
            _MutableElement(
                name=name,
                attributes=attributes,
                source_path=self.source_path,
                source_line=source_line,
                children=[],
                text_parts=[],
            )
        )

    def characters(
        self,
        content,
    ) -> None:
        if not self.stack:
            if content.strip():
                raise ValueError(
                    "mac_permissions XML contains "
                    "character data outside root"
                )
            return

        self.stack[-1].text_parts.append(
            content
        )

    def endElement(
        self,
        name,
    ) -> None:
        if not self.stack:
            raise ValueError(
                "mac_permissions XML element stack "
                "underflow"
            )

        current = self.stack.pop()

        if current.name != name:
            raise ValueError(
                "mac_permissions XML closing element "
                "does not match opening element"
            )

        element = (
            AndroidSelinuxMacPermissionsElement(
                name=current.name,
                attributes=current.attributes,
                children=tuple(
                    current.children
                ),
                text="".join(
                    current.text_parts
                ),
                source_path=(
                    current.source_path
                ),
                source_line=(
                    current.source_line
                ),
            )
        )

        if self.stack:
            self.stack[-1].children.append(
                element
            )
            return

        if self.root is not None:
            raise ValueError(
                "mac_permissions XML contains "
                "multiple root elements"
            )

        self.root = element


class AndroidSelinuxMacPermissionsParser:
    """
    Parse the intrinsic XML structure of mac_permissions.xml.

    Parsing owns only structure and literal values. It does not decide
    source ownership, baseline subtraction, build destination, or whether
    signatures originally came from keys.conf.
    """

    def parse(
        self,
        raw_bytes: bytes,
        *,
        source_path: Path,
    ) -> tuple[
        str,
        AndroidSelinuxMacPermissionsElement,
    ]:
        if not isinstance(
            raw_bytes,
            bytes,
        ):
            raise TypeError(
                "raw_bytes must be bytes"
            )

        if not isinstance(
            source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        raw = decode_mac_permissions_xml(
            raw_bytes
        )

        handler = _MacPermissionsHandler(
            source_path=source_path
        )

        parser = xml.sax.make_parser()

        try:
            parser.setFeature(
                xml.sax.handler
                .feature_external_ges,
                False,
            )
        except (
            xml.sax.SAXNotRecognizedException,
            xml.sax.SAXNotSupportedException,
        ):
            pass

        try:
            parser.setFeature(
                xml.sax.handler
                .feature_external_pes,
                False,
            )
        except (
            xml.sax.SAXNotRecognizedException,
            xml.sax.SAXNotSupportedException,
        ):
            pass

        parser.setContentHandler(
            handler
        )

        parser.parse(
            io.BytesIO(raw_bytes)
        )

        if handler.stack:
            raise ValueError(
                "mac_permissions XML ended with "
                "unclosed elements"
            )

        if handler.root is None:
            raise ValueError(
                "mac_permissions XML must contain "
                "one root element"
            )

        return raw, handler.root
