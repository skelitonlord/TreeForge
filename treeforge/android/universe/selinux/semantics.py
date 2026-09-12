from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AndroidUniverseSelinuxRequirementKind(
    StrEnum
):
    CONTEXT = "context"
    SEAPP = "seapp"
    CIL = "cil"
    COMPILED_POLICY = "compiled_policy"
    AUXILIARY = "auxiliary"


class AndroidUniverseSelinuxCilSemanticKind(
    StrEnum
):
    ACCESS_RULE = "access_rule"
    EXTENDED_ACCESS_RULE = "extended_access_rule"
    TYPE_DECLARATION = "type_declaration"
    TYPE_ATTRIBUTE_DECLARATION = (
        "type_attribute_declaration"
    )
    TYPE_ATTRIBUTE_SET = "type_attribute_set"
    TYPE_ALIAS = "type_alias"
    TYPE_ALIAS_ACTUAL = "type_alias_actual"
    TYPE_TRANSITION = "type_transition"
    ROLE_DECLARATION = "role_declaration"
    ROLE_ATTRIBUTE_DECLARATION = (
        "role_attribute_declaration"
    )
    ROLE_TYPE = "role_type"
    USER_DECLARATION = "user_declaration"
    USER_ROLE = "user_role"
    USER_LEVEL = "user_level"
    USER_RANGE = "user_range"
    CLASS_DECLARATION = "class_declaration"
    CLASS_COMMON = "class_common"
    CLASS_ORDER = "class_order"
    COMMON_DECLARATION = "common_declaration"
    SID_DECLARATION = "sid_declaration"
    SID_CONTEXT = "sid_context"
    SID_ORDER = "sid_order"
    FS_USE = "fs_use"
    GENFS_CONTEXT = "genfs_context"
    POLICY_CAPABILITY = "policy_capability"
    MLS = "mls"
    MLS_CONSTRAINT = "mls_constraint"
    SENSITIVITY_DECLARATION = (
        "sensitivity_declaration"
    )
    SENSITIVITY_CATEGORY = (
        "sensitivity_category"
    )
    SENSITIVITY_ORDER = "sensitivity_order"
    CATEGORY_DECLARATION = (
        "category_declaration"
    )
    CATEGORY_ORDER = "category_order"
    HANDLE_UNKNOWN = "handle_unknown"


_CIL_SEMANTIC_KINDS = {
    "allow": (
        AndroidUniverseSelinuxCilSemanticKind
        .ACCESS_RULE
    ),
    "auditallow": (
        AndroidUniverseSelinuxCilSemanticKind
        .ACCESS_RULE
    ),
    "dontaudit": (
        AndroidUniverseSelinuxCilSemanticKind
        .ACCESS_RULE
    ),
    "neverallow": (
        AndroidUniverseSelinuxCilSemanticKind
        .ACCESS_RULE
    ),
    "allowx": (
        AndroidUniverseSelinuxCilSemanticKind
        .EXTENDED_ACCESS_RULE
    ),
    "dontauditx": (
        AndroidUniverseSelinuxCilSemanticKind
        .EXTENDED_ACCESS_RULE
    ),
    "neverallowx": (
        AndroidUniverseSelinuxCilSemanticKind
        .EXTENDED_ACCESS_RULE
    ),
    "type": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_DECLARATION
    ),
    "typeattribute": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_ATTRIBUTE_DECLARATION
    ),
    "typeattributeset": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_ATTRIBUTE_SET
    ),
    "expandtypeattribute": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_ATTRIBUTE_SET
    ),
    "typealias": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_ALIAS
    ),
    "typealiasactual": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_ALIAS_ACTUAL
    ),
    "typetransition": (
        AndroidUniverseSelinuxCilSemanticKind
        .TYPE_TRANSITION
    ),
    "role": (
        AndroidUniverseSelinuxCilSemanticKind
        .ROLE_DECLARATION
    ),
    "roleattribute": (
        AndroidUniverseSelinuxCilSemanticKind
        .ROLE_ATTRIBUTE_DECLARATION
    ),
    "roletype": (
        AndroidUniverseSelinuxCilSemanticKind
        .ROLE_TYPE
    ),
    "user": (
        AndroidUniverseSelinuxCilSemanticKind
        .USER_DECLARATION
    ),
    "userrole": (
        AndroidUniverseSelinuxCilSemanticKind
        .USER_ROLE
    ),
    "userlevel": (
        AndroidUniverseSelinuxCilSemanticKind
        .USER_LEVEL
    ),
    "userrange": (
        AndroidUniverseSelinuxCilSemanticKind
        .USER_RANGE
    ),
    "class": (
        AndroidUniverseSelinuxCilSemanticKind
        .CLASS_DECLARATION
    ),
    "classcommon": (
        AndroidUniverseSelinuxCilSemanticKind
        .CLASS_COMMON
    ),
    "classorder": (
        AndroidUniverseSelinuxCilSemanticKind
        .CLASS_ORDER
    ),
    "common": (
        AndroidUniverseSelinuxCilSemanticKind
        .COMMON_DECLARATION
    ),
    "sid": (
        AndroidUniverseSelinuxCilSemanticKind
        .SID_DECLARATION
    ),
    "sidcontext": (
        AndroidUniverseSelinuxCilSemanticKind
        .SID_CONTEXT
    ),
    "sidorder": (
        AndroidUniverseSelinuxCilSemanticKind
        .SID_ORDER
    ),
    "fsuse": (
        AndroidUniverseSelinuxCilSemanticKind
        .FS_USE
    ),
    "genfscon": (
        AndroidUniverseSelinuxCilSemanticKind
        .GENFS_CONTEXT
    ),
    "policycap": (
        AndroidUniverseSelinuxCilSemanticKind
        .POLICY_CAPABILITY
    ),
    "mls": (
        AndroidUniverseSelinuxCilSemanticKind
        .MLS
    ),
    "mlsconstrain": (
        AndroidUniverseSelinuxCilSemanticKind
        .MLS_CONSTRAINT
    ),
    "sensitivity": (
        AndroidUniverseSelinuxCilSemanticKind
        .SENSITIVITY_DECLARATION
    ),
    "sensitivitycategory": (
        AndroidUniverseSelinuxCilSemanticKind
        .SENSITIVITY_CATEGORY
    ),
    "sensitivityorder": (
        AndroidUniverseSelinuxCilSemanticKind
        .SENSITIVITY_ORDER
    ),
    "category": (
        AndroidUniverseSelinuxCilSemanticKind
        .CATEGORY_DECLARATION
    ),
    "categoryorder": (
        AndroidUniverseSelinuxCilSemanticKind
        .CATEGORY_ORDER
    ),
    "handleunknown": (
        AndroidUniverseSelinuxCilSemanticKind
        .HANDLE_UNKNOWN
    ),
}


@dataclass(
    frozen=True,
    slots=True,
)
class AndroidUniverseSelinuxCilSemantics:
    form_name: str
    kind: AndroidUniverseSelinuxCilSemanticKind | None

    @property
    def interpreted(
        self,
    ) -> bool:
        return self.kind is not None


def interpret_cil_form_name(
    form_name: str,
) -> AndroidUniverseSelinuxCilSemantics:
    return AndroidUniverseSelinuxCilSemantics(
        form_name=form_name,
        kind=_CIL_SEMANTIC_KINDS.get(
            form_name
        ),
    )