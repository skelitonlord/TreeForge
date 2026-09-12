from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree


@dataclass(
    frozen=True,
    slots=True,
)
class VintfXmlAttribute:
    """
    One XML attribute exactly as exposed by the XML parser.
    """

    name: str
    value: str


@dataclass(
    frozen=True,
    slots=True,
)
class VintfXmlElement:
    """
    Immutable lexical representation of one VINTF XML element.

    Child ordering, attribute ordering, text, tail text, namespaces, and
    unknown elements are preserved without Android semantic interpretation.
    """

    tag: str

    attributes: tuple[
        VintfXmlAttribute,
        ...,
    ] = ()

    text: str | None = None
    tail: str | None = None

    children: tuple[
        "VintfXmlElement",
        ...,
    ] = ()

    def attribute(
        self,
        name: str,
    ) -> str | None:
        """
        Return the exact value of the first matching attribute.
        """

        for attribute in self.attributes:
            if attribute.name == name:
                return attribute.value

        return None

    @property
    def local_name(
        self,
    ) -> str:
        """
        Return the local XML tag name without interpreting its namespace.
        """

        return self.tag.rsplit(
            "}",
            1,
        )[-1]


@dataclass(
    frozen=True,
    slots=True,
)
class ParsedVintfDocument:
    """
    Faithful immutable representation of one VINTF XML source.

    Parsing establishes XML structure only. Android VINTF semantics are
    intentionally interpreted by a later stage.
    """

    source_path: Path
    raw: str
    root: VintfXmlElement

    def __post_init__(
        self,
    ) -> None:
        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not isinstance(
            self.raw,
            str,
        ):
            raise TypeError(
                "raw must be a string"
            )

        if not isinstance(
            self.root,
            VintfXmlElement,
        ):
            raise TypeError(
                "root must be a VintfXmlElement"
            )


class VintfParser:
    """
    Parse one VINTF XML source into faithful immutable XML syntax.

    Parsing validates that the source is readable XML but does not interpret
    manifest types, matrix types, HAL formats, compatibility requirements, or
    other Android VINTF semantics.
    """

    def parse(
        self,
        source_path: Path,
    ) -> ParsedVintfDocument:
        source_path = Path(
            source_path
        )

        self._validate_source(
            source_path
        )

        raw = source_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        try:
            root = ElementTree.fromstring(
                raw
            )
        except ElementTree.ParseError as exc:
            raise ValueError(
                "Invalid VINTF XML in "
                f"{source_path}: {exc}"
            ) from exc

        return ParsedVintfDocument(
            source_path=source_path,
            raw=raw,
            root=self._convert_element(
                root
            ),
        )

    @staticmethod
    def _validate_source(
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                source_path
            )

        if not source_path.is_file():
            raise ValueError(
                "VINTF source must be a file: "
                f"{source_path}"
            )

    def _convert_element(
        self,
        element: ElementTree.Element,
    ) -> VintfXmlElement:
        return VintfXmlElement(
            tag=element.tag,
            attributes=tuple(
                VintfXmlAttribute(
                    name=name,
                    value=value,
                )
                for name, value
                in element.attrib.items()
            ),
            text=element.text,
            tail=element.tail,
            children=tuple(
                self._convert_element(
                    child
                )
                for child in element
            ),
        )


def read_android_vintf(
    source_path: Path,
) -> ParsedVintfDocument:
    """
    Read and parse one Android VINTF XML source.
    """

    return VintfParser().parse(
        source_path
    )