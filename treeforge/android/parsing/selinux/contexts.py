from __future__ import annotations

from pathlib import Path

from treeforge.android.parsing.selinux.model import (
    AndroidSelinuxContextDeclaration,
    AndroidSelinuxSeappDeclaration,
    AndroidSelinuxSeappField,
    AndroidSelinuxUnparsedLine,
)


def parse_context_lines(
    raw: str,
    *,
    source_path: Path,
    file_contexts: bool = False,
) -> tuple[
    tuple[
        AndroidSelinuxContextDeclaration,
        ...,
    ],
    tuple[
        AndroidSelinuxUnparsedLine,
        ...,
    ],
]:
    declarations: list[
        AndroidSelinuxContextDeclaration
    ] = []

    unparsed: list[
        AndroidSelinuxUnparsedLine
    ] = []

    for line_number, raw_line in enumerate(
        raw.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        parts = line.split()

        if len(parts) < 2:
            unparsed.append(
                AndroidSelinuxUnparsedLine(
                    raw=raw_line,
                    source_path=source_path,
                    source_line=line_number,
                )
            )
            continue

        selector = parts[0]

        if (
            file_contexts
            and len(parts) >= 3
            and not parts[1].startswith(
                "u:"
            )
        ):
            selector_fields = (
                parts[1:-1]
            )

            context = parts[-1]

            trailing_fields: tuple[
                str,
                ...,
            ] = ()
        else:
            selector_fields = ()

            context = parts[1]

            trailing_fields = tuple(
                parts[2:]
            )

        declarations.append(
            AndroidSelinuxContextDeclaration(
                selector=selector,
                context=context,
                selector_fields=tuple(
                    selector_fields
                ),
                trailing_fields=trailing_fields,
                raw=raw_line,
                source_path=source_path,
                source_line=line_number,
            )
        )

    return (
        tuple(
            declarations
        ),
        tuple(
            unparsed
        ),
    )


def parse_seapp_lines(
    raw: str,
    *,
    source_path: Path,
) -> tuple[
    tuple[
        AndroidSelinuxSeappDeclaration,
        ...,
    ],
    tuple[
        AndroidSelinuxUnparsedLine,
        ...,
    ],
]:
    declarations: list[
        AndroidSelinuxSeappDeclaration
    ] = []

    unparsed: list[
        AndroidSelinuxUnparsedLine
    ] = []

    for line_number, raw_line in enumerate(
        raw.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
        ):
            continue

        fields: list[
            AndroidSelinuxSeappField
        ] = []

        valid = True

        for token in line.split():
            name, separator, value = (
                token.partition("=")
            )

            if (
                not separator
                or not name
            ):
                valid = False
                break

            fields.append(
                AndroidSelinuxSeappField(
                    name=name,
                    value=value,
                )
            )

        if (
            not valid
            or not fields
        ):
            unparsed.append(
                AndroidSelinuxUnparsedLine(
                    raw=raw_line,
                    source_path=source_path,
                    source_line=line_number,
                )
            )
            continue

        declarations.append(
            AndroidSelinuxSeappDeclaration(
                fields=tuple(
                    fields
                ),
                raw=raw_line,
                source_path=source_path,
                source_line=line_number,
            )
        )

    return (
        tuple(
            declarations
        ),
        tuple(
            unparsed
        ),
    )