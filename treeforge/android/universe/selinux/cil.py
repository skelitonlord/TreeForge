from __future__ import annotations

from dataclasses import dataclass

from treeforge.android.parsing.selinux import (
    AndroidSelinuxCilAtom,
    AndroidSelinuxCilExpression,
    AndroidSelinuxCilForm,
    AndroidSelinuxCilList,
)
from treeforge.android.universe.selinux.semantics import (
    AndroidUniverseSelinuxCilSemantics,
    interpret_cil_form_name,
)


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxCilRequirement:
    """
    One canonical SELinux CIL requirement.

    Parsing owns structural S-expression decoding. Universe assigns the
    semantic family while retaining the exact parsed form.
    """

    form: AndroidSelinuxCilForm

    semantics: AndroidUniverseSelinuxCilSemantics

    @property
    def form_name(
        self,
    ) -> str:
        return self.form.name

    @property
    def interpreted(
        self,
    ) -> bool:
        return self.semantics.interpreted

    @property
    def source_line(
        self,
    ) -> int:
        return self.form.source_line

    @property
    def end_line(
        self,
    ) -> int:
        return self.form.end_line

    @property
    def arguments(
        self,
    ) -> tuple[
        AndroidSelinuxCilExpression,
        ...,
    ]:
        return self.form.expression.items[
            1:
        ]


def interpret_cil_form(
    form: AndroidSelinuxCilForm,
) -> AndroidUniverseSelinuxCilRequirement:
    return AndroidUniverseSelinuxCilRequirement(
        form=form,
        semantics=interpret_cil_form_name(
            form.name
        ),
    )


def atom_value(
    expression: AndroidSelinuxCilExpression,
) -> str | None:
    if isinstance(
        expression,
        AndroidSelinuxCilAtom,
    ):
        return expression.value

    return None


def list_values(
    expression: AndroidSelinuxCilExpression,
) -> tuple[
    str,
    ...,
] | None:
    if not isinstance(
        expression,
        AndroidSelinuxCilList,
    ):
        return None

    values = []

    for item in expression.items:
        value = atom_value(
            item
        )

        if value is None:
            return None

        values.append(
            value
        )

    return tuple(
        values
    )